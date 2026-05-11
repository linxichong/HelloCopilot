# 01. 本地开发

这一章用于在不进入 Kubernetes 的情况下理解应用本身：FastAPI、PostgreSQL、Flyway migration 和测试。

## 启动数据库和迁移

```bash
docker compose up -d db flyway
```

`db` 会启动 PostgreSQL，`flyway` 会执行 `db/migration/*.sql`。

## 启动 API

Linux / WSL:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
uvicorn app.main:app --reload
```

访问：

- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health
- 存活检查：http://127.0.0.1:8000/live
- 就绪检查：http://127.0.0.1:8000/ready

## 示例接口

PowerShell:

```powershell
curl -X POST http://127.0.0.1:8000/items `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"demo item\",\"description\":\"created from api\"}"

curl http://127.0.0.1:8000/items
```

Bash:

```bash
curl -X POST http://127.0.0.1:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name":"demo item","description":"created from api"}'

curl http://127.0.0.1:8000/items
```

## 运行测试

```bash
python -m compileall app tests
pytest
```

测试覆盖：

- 健康检查
- liveness / readiness 检查
- item 创建/查询/404
- 认证关闭/开启行为
- Authentik claims/group 解析
- SQLAlchemy model 和 Pydantic schema
