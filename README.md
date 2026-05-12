# HelloCopilot

一个用于学习 Kubernetes / GitOps / CI/CD / SSO 的 FastAPI 示例项目。

技术栈：

- FastAPI + SQLAlchemy
- PostgreSQL + Flyway
- Zalando Postgres Operator / Patroni
- Prefect ETL / DWH pipeline
- Docker Compose
- Kubernetes + Kustomize
- Argo CD
- Argo Workflows
- Argo Events
- Authentik / OIDC

## 学习路径

建议按下面顺序阅读和实践：

1. [本地开发：FastAPI、PostgreSQL、Flyway](docs/01-local.md)
2. [Kind / Kubernetes 部署](docs/02-kind.md)
3. [Argo CD GitOps 部署](docs/03-argocd.md)
4. [Argo Workflows CI/CD](docs/04-workflows.md)
5. [Argo Events 自动触发](docs/05-events.md)
6. [Authentik 单点登录与 API 认证](docs/06-authentik.md)
7. [常见问题与排障](docs/07-troubleshooting.md)
8. [pgBackRest 备份与还原](docs/08-backup-restore.md)

## 目录结构

```text
.
├── app/                         # FastAPI 应用
├── db/migration/                # Flyway SQL migration
├── k8s/
│   ├── base/                    # Kustomize 公共资源
│   ├── dev/                     # study-dev overlay
│   └── prod/                    # study-prod overlay
├── argocd/                      # Argo CD Application
├── argo-workflows/dev/          # CI/CD WorkflowTemplate
├── argo-events/dev/             # GitHub webhook 触发配置
├── authentik/dev/               # Authentik Helm values 示例
├── tests/                       # pytest 测试
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── requirements-dev.txt
```

## 快速命令

本地启动数据库和迁移：

```bash
docker compose up -d db flyway
```

本地运行 API：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

运行测试：

```bash
python -m compileall app tests
pytest
```

运行 Prefect 数据入仓 flow：

```bash
export EXTERNAL_SOURCE_API_URL=https://example.com/api/records
export EXTERNAL_SOURCE_SYSTEM=external_api
python -m app.dwh_flow
```

该 flow 会从外部 JSON API 拉取记录，先落到 `external_raw_records` 原始层，再转换写入 `dwh_external_record_facts` 分析事实表。API 返回值可以是数组，也可以是包含 `data`、`items` 或 `records` 数组的对象。

学习测试可以直接使用 JSONPlaceholder，它是一个免注册的公开 fake REST API：

```bash
export EXTERNAL_SOURCE_API_URL=https://jsonplaceholder.typicode.com/todos
export EXTERNAL_SOURCE_SYSTEM=jsonplaceholder_todos
python -m app.dwh_flow
```

`/todos` 会返回 200 条任务数据，flow 会把 `id` 当成外部 ID、`title` 映射到 `name`，并把 `completed` 映射成 `done` / `open`。

部署到 Kind dev 环境：

```bash
sh scripts/generate-flyway-configmaps.sh
kubectl apply -k k8s/dev
```

访问 API：

```bash
kubectl -n study-dev port-forward --address 0.0.0.0 service/hello-copilot 8000:80
```

然后打开：

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/live
- http://127.0.0.1:8000/ready

## 当前 K8s 设计

- `k8s/base` 放公共资源。
- `k8s/dev` 和 `k8s/prod` 使用 Kustomize overlay 管理环境差异。
- PostgreSQL 使用 Zalando Postgres Operator 创建 Patroni 主从集群。
- `hello-copilot-postgres` 是主库读写 Service，`hello-copilot-postgres-repl` 是只读副本 Service。
- `hello-copilot-postgres-proxy` 是 HAProxy 入口，`5432` 转发写库，`5433` 转发只读副本。
- `hello-copilot-postgres-pgbouncer` 是应用侧连接池入口，应用默认连接它的 `6432` 端口，再由 PgBouncer 转发到 HAProxy 写入口。
- `pgbackrest` sidecar 和 `hello-copilot-postgres-pgbackrest-repo` PVC 用于学习 pgBackRest 物理备份与还原。
- Flyway Job 作为 Argo CD `PreSync` hook 执行。
- Kubernetes liveness probe 使用 `/live`，readiness probe 使用 `/ready` 检查数据库连通性。
- CI 构建镜像后更新 `k8s/dev/kustomization.yaml` 中的镜像 tag。
