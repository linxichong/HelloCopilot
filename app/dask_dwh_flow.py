from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx
from prefect import flow, get_run_logger, task

from app.config import get_settings
from app.dwh_flow import _extract_records, _parse_decimal, _record_status


@dataclass(frozen=True)
class DaskClusterConfig:
    """Dask 本地或远程执行时使用的运行参数。"""

    scheduler_address: str | None = None
    local_workers: int = 2
    threads_per_worker: int = 1
    memory_limit: str = "512MiB"


def _record_amount(record: dict[str, Any]) -> Decimal:
    return _parse_decimal(record.get("amount") or record.get("total")) or Decimal("0")


def _normalize_for_analytics(record: dict[str, Any]) -> dict[str, Any]:
    """只保留后续分析聚合需要的字段。"""

    return {
        "status": _record_status(record) or "unknown",
        "amount": _record_amount(record),
    }


def _partition_summary(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """先汇总一个 Dask 分区，后面再把所有分区结果合并。"""

    rows = list(records)
    status_counts = Counter(row["status"] for row in rows)
    amount_total = sum((row["amount"] for row in rows), Decimal("0"))
    return {
        "record_count": len(rows),
        "status_counts": dict(status_counts),
        "amount_total": amount_total,
    }


def _merge_summaries(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """合并两个 Dask 分区产出的局部汇总结果。"""

    status_counts = Counter(left.get("status_counts", {}))
    status_counts.update(right.get("status_counts", {}))
    return {
        "record_count": left.get("record_count", 0) + right.get("record_count", 0),
        "status_counts": dict(status_counts),
        "amount_total": left.get("amount_total", Decimal("0")) + right.get("amount_total", Decimal("0")),
    }


def _json_ready_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """把 Decimal 转成字符串，方便 Prefect 序列化 flow 结果。"""

    return {
        "record_count": int(summary.get("record_count", 0)),
        "status_counts": dict(summary.get("status_counts", {})),
        "amount_total": str(summary.get("amount_total", Decimal("0"))),
    }


@task(retries=3, retry_delay_seconds=10)
def fetch_records_for_dask(source_url: str) -> list[dict[str, Any]]:
    """Prefect task：从外部 API 拉取 JSON 记录。"""

    response = httpx.get(source_url, timeout=30.0)
    response.raise_for_status()
    return _extract_records(response.json())


@task
def amplify_records_for_learning(records: list[dict[str, Any]], scale_factor: int) -> list[dict[str, Any]]:
    """放大小型公开 API 数据集，便于观察 Dask 分区计算效果。"""

    if scale_factor < 1:
        raise ValueError("scale_factor must be >= 1")
    if scale_factor == 1:
        return records

    expanded: list[dict[str, Any]] = []
    for batch_number in range(scale_factor):
        for record in records:
            expanded_record = dict(record)
            original_id = record.get("id") or record.get("external_id") or record.get("uuid") or len(expanded)
            expanded_record["id"] = f"{original_id}-{batch_number}"
            expanded.append(expanded_record)
    return expanded


@task
def summarize_records_with_dask(
    records: list[dict[str, Any]],
    npartitions: int = 8,
    scheduler_address: str | None = None,
    local_workers: int = 2,
    threads_per_worker: int = 1,
    memory_limit: str = "512MiB",
) -> dict[str, Any]:
    """Prefect task：构建 Dask 计算图，并执行并行聚合。"""

    if npartitions < 1:
        raise ValueError("npartitions must be >= 1")

    # 在 task 内部导入 Dask，避免普通 API 代码和轻量测试在 import 阶段
    # 就加载分布式计算相关依赖。
    import dask.bag as dbag

    client = None
    if scheduler_address:
        # 传入远程 scheduler 地址后，同一个 flow 就可以扩展到 Dask 集群运行。
        from distributed import Client

        client = Client(scheduler_address)

    try:
        # Dask Bag 适合处理 JSON 风格的 Python 字典。每个分区先独立汇总，
        # 再把较小的局部汇总结果 reduce 成最终结果。
        bag = dbag.from_sequence(records, npartitions=npartitions)
        summary_graph = (
            bag.map(_normalize_for_analytics).map_partitions(lambda partition: [_partition_summary(partition)]).fold(_merge_summaries)
        )
        if client is None:
            # threaded scheduler 让本地演示和 CI 更简单。真正接入 Dask 集群时，
            # 传入 scheduler_address，让 distributed scheduler 执行计算。
            summary = summary_graph.compute(
                scheduler="threads",
                num_workers=max(1, local_workers * threads_per_worker),
            )
        else:
            summary = summary_graph.compute()
        return _json_ready_summary(summary)
    finally:
        if client is not None:
            client.close()


@flow(name="dask-prefect-dwh-summary")
def dask_prefect_dwh_summary(
    source_url: str | None = None,
    scale_factor: int = 1,
    npartitions: int = 8,
    scheduler_address: str | None = None,
    local_workers: int = 2,
    threads_per_worker: int = 1,
    memory_limit: str = "512MiB",
) -> dict[str, Any]:
    """用 Prefect 拉取和编排数据，用 Dask 处理数据，并返回 DWH 指标。"""

    settings = get_settings()
    resolved_source_url = source_url or settings.external_source_api_url
    if not resolved_source_url:
        raise ValueError("Set EXTERNAL_SOURCE_API_URL or pass source_url to the flow")

    logger = get_run_logger()
    records = fetch_records_for_dask(resolved_source_url)
    expanded_records = amplify_records_for_learning(records, scale_factor)
    summary = summarize_records_with_dask(
        expanded_records,
        npartitions=npartitions,
        scheduler_address=scheduler_address,
        local_workers=local_workers,
        threads_per_worker=threads_per_worker,
        memory_limit=memory_limit,
    )
    logger.info("Dask summary: %s", summary)
    return summary


if __name__ == "__main__":
    dask_prefect_dwh_summary()
