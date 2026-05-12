from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from prefect import flow, get_run_logger, task
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import DwhExternalRecordFact, ExternalRawRecord


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = payload.get("data") or payload.get("items") or payload.get("records") or []
    else:
        records = []

    if not isinstance(records, list):
        raise ValueError("External payload must be a list or contain a list in data/items/records")

    return [record for record in records if isinstance(record, dict)]


def _record_id(record: dict[str, Any]) -> str:
    value = record.get("id") or record.get("external_id") or record.get("uuid")
    if value is None:
        raise ValueError(f"External record is missing id/external_id/uuid: {record}")
    return str(value)


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid decimal value: {value}") from exc


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    raise ValueError(f"Invalid datetime value: {value}")


def _record_status(record: dict[str, Any]) -> str | None:
    status = record.get("status")
    if status is not None:
        return str(status)
    completed = record.get("completed")
    if isinstance(completed, bool):
        return "done" if completed else "open"
    return None


def _find_raw(
    session: Session,
    source_system: str,
    external_id: str,
) -> ExternalRawRecord | None:
    statement = select(ExternalRawRecord).where(
        ExternalRawRecord.source_system == source_system,
        ExternalRawRecord.external_id == external_id,
    )
    return session.scalars(statement).one_or_none()


def _find_fact(
    session: Session,
    source_system: str,
    external_id: str,
) -> DwhExternalRecordFact | None:
    statement = select(DwhExternalRecordFact).where(
        DwhExternalRecordFact.source_system == source_system,
        DwhExternalRecordFact.external_id == external_id,
    )
    return session.scalars(statement).one_or_none()


@task(retries=3, retry_delay_seconds=10)
def fetch_external_records(source_url: str) -> list[dict[str, Any]]:
    response = httpx.get(source_url, timeout=30.0)
    response.raise_for_status()
    return _extract_records(response.json())


@task
def load_raw_records(records: list[dict[str, Any]], source_system: str) -> int:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        for record in records:
            external_id = _record_id(record)
            raw_record = _find_raw(session, source_system, external_id)
            if raw_record is None:
                session.add(
                    ExternalRawRecord(
                        source_system=source_system,
                        external_id=external_id,
                        payload=record,
                        ingested_at=now,
                    )
                )
            else:
                raw_record.payload = record
                raw_record.ingested_at = now
        session.commit()
    return len(records)


@task
def transform_and_load_facts(records: list[dict[str, Any]], source_system: str) -> int:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        for record in records:
            external_id = _record_id(record)
            fact = _find_fact(session, source_system, external_id)
            if fact is None:
                fact = DwhExternalRecordFact(source_system=source_system, external_id=external_id)
                session.add(fact)

            fact.name = record.get("name") or record.get("title")
            fact.status = _record_status(record)
            fact.amount = _parse_decimal(record.get("amount") or record.get("total"))
            fact.occurred_at = _parse_datetime(record.get("occurred_at") or record.get("created_at"))
            fact.loaded_at = now
        session.commit()
    return len(records)


@flow(name="external-api-to-dwh")
def external_api_to_dwh(
    source_url: str | None = None,
    source_system: str | None = None,
) -> dict[str, int]:
    settings = get_settings()
    resolved_source_url = source_url or settings.external_source_api_url
    resolved_source_system = source_system or settings.external_source_system
    if not resolved_source_url:
        raise ValueError("Set EXTERNAL_SOURCE_API_URL or pass source_url to the flow")

    logger = get_run_logger()
    records = fetch_external_records(resolved_source_url)
    raw_count = load_raw_records(records, resolved_source_system)
    fact_count = transform_and_load_facts(records, resolved_source_system)
    logger.info("Loaded %s raw records and %s fact records", raw_count, fact_count)
    return {"raw_records": raw_count, "fact_records": fact_count}


if __name__ == "__main__":
    external_api_to_dwh()
