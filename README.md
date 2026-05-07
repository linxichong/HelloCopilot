# HelloCopilot

一个简单的 Python Web 项目，使用 FastAPI + PostgreSQL + Flyway。

## 目录结构

```text
.
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   └── schemas.py
├── db/
│   └── migration/
│       ├── V1__create_items.sql
│       ├── V2__add_price_to_items.sql
│       └── V3__add_price2_to_items.sql
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── Dockerfile
├── .dockerignore
└── k8s/
    ├── app-deployment.yaml
    ├── app-service.yaml
    ├── flyway-configmap.yaml
    ├── flyway-job.yaml
    ├── postgres-deployment.yaml
    ├── postgres-secret.yaml
    └── postgres-service.yaml
```

## 启动 PostgreSQL 和执行 Flyway 迁移

```powershell
docker compose up -d db flyway
```

## 启动 Web 服务

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

访问：

- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health

## 示例接口

```powershell
curl -X POST http://127.0.0.1:8000/items `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"demo item\",\"description\":\"created from api\"}"

curl http://127.0.0.1:8000/items
```

## Kubernetes / Kind 部署

如果你想用 Kind 学习 Kubernetes，可以按下面步骤部署项目：

```bash
kind create cluster --name hellocopilot
docker build -t hellocopilot:local .
kind load docker-image hellocopilot:local --name hellocopilot
kubectl apply -f k8s/postgres-secret.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/flyway-configmap.yaml
kubectl apply -f k8s/flyway-job.yaml
kubectl apply -f k8s/app-service.yaml
kubectl apply -f k8s/app-deployment.yaml
```

等待 PostgreSQL 和 Flyway 迁移完成后，使用端口转发访问服务：

```bash
kubectl port-forward service/hello-copilot 8000:80
```

然后打开：

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/health

注意：

- `postgres` 在 Kind 中使用 `emptyDir` 存储，因此数据是临时的。
- 如果需要重新执行迁移，可以删除旧 Job 后重新应用 `k8s/flyway-job.yaml`。
