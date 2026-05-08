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
│       ├── V3__add_price2_to_items.sql
│       ├── V4__drop_price2_from_items.sql
│       ├── V5__drop_price_from_items.sql
│       └── V6__add_age_to_items.sql
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── Dockerfile
├── .dockerignore
├── argocd/
│   ├── app-dev.yaml
│   └── app-prod.yaml
├── argo-events/
│   └── dev/
│       ├── eventbus.yaml
│       ├── eventsource.yaml
│       ├── rbac.yaml
│       └── sensor.yaml
├── argo-workflows/
│   └── dev/
│       ├── cicd-rbac.yaml
│       ├── cicd-secrets.example.yaml
│       ├── cicd-workflow-template.yaml
│       └── run-cicd-workflow.yaml
└── k8s/
    ├── dev/
    │   ├── app-deployment.yaml
    │   ├── app-service.yaml
    │   ├── flyway-configmap.yaml
    │   ├── flyway-job.yaml
    │   ├── namespace.yaml
    │   ├── postgres-deployment.yaml
    │   ├── postgres-secret.yaml
    │   └── postgres-service.yaml
    └── prod/
        ├── app-deployment.yaml
        ├── app-service.yaml
        ├── flyway-configmap.yaml
        ├── flyway-job.yaml
        ├── namespace.yaml
        ├── postgres-deployment.yaml
        ├── postgres-pvc.yaml
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

如果你想用 Kind 学习 Kubernetes，可以按下面步骤部署项目。

### 开发环境（study-dev）

```bash
kind create cluster --name hellocopilot
docker build -t hellocopilot:local .
kind load docker-image hellocopilot:local --name hellocopilot
sh scripts/generate-flyway-configmaps.sh
kubectl apply -f k8s/dev/namespace.yaml
kubectl apply -f k8s/dev/postgres-secret.yaml
kubectl apply -f k8s/dev/postgres-service.yaml
kubectl apply -f k8s/dev/postgres-deployment.yaml
kubectl apply -f k8s/dev/flyway-configmap.yaml
kubectl apply -f k8s/dev/flyway-job.yaml
kubectl apply -f k8s/dev/app-service.yaml
kubectl apply -f k8s/dev/app-deployment.yaml
```

### 本番环境（study-prod）

```bash
sh scripts/generate-flyway-configmaps.sh
kubectl apply -f k8s/prod/namespace.yaml
kubectl apply -f k8s/prod/postgres-secret.yaml
kubectl apply -f k8s/prod/postgres-pvc.yaml
kubectl apply -f k8s/prod/postgres-service.yaml
kubectl apply -f k8s/prod/postgres-deployment.yaml
kubectl apply -f k8s/prod/flyway-configmap.yaml
kubectl apply -f k8s/prod/flyway-job.yaml
kubectl apply -f k8s/prod/app-service.yaml
kubectl apply -f k8s/prod/app-deployment.yaml
```

等待 PostgreSQL 和 Flyway 迁移完成后，使用端口转发访问服务：

```bash
kubectl port-forward service/hello-copilot 8000:80 -n study-dev
# 或者对于本番环境：
# kubectl port-forward service/hello-copilot 8000:80 -n study-prod
```

然后打开：

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/health

注意：

- 开发环境使用 `emptyDir` 存储，数据仅在 Pod 存活期间保留。
- 本番环境使用 PVC 存储，数据会在 Pod 重建时保留。
- `flyway-configmap.yaml` 由 `scripts/generate-flyway-configmaps.sh` 从 `db/migration/*.sql` 生成，不要手动编辑 ConfigMap 里的 SQL。
- `flyway-migrate` 在 Argo CD 中作为 `PreSync` hook 运行，每次 Argo CD sync 前会重新创建并执行；迁移失败时会停止后续部署。
- 如果绕过 Argo CD 直接用 `kubectl apply`，Kubernetes Job 不会自动重复执行，需要先删除旧 Job 再应用相应的 `k8s/dev/flyway-job.yaml` 或 `k8s/prod/flyway-job.yaml`。

## Argo Workflows

### 安装控制器

先在集群里安装 Argo Workflows 的 CRD、controller 和 UI。下面版本号可以按需要替换为 GitHub Releases 上的正式版本：

```bash
ARGO_WORKFLOWS_VERSION="v4.0.4"
kubectl create namespace argo
kubectl apply --server-side -f "https://github.com/argoproj/argo-workflows/releases/download/${ARGO_WORKFLOWS_VERSION}/install.yaml"
```

访问 Argo Workflows UI：

```bash
kubectl -n argo port-forward service/argo-server 2746:2746
```

然后打开：

- https://localhost:2746

### CI/CD 流程

`argo-workflows/dev/cicd-workflow-template.yaml` 提供了一个学习用 CI/CD 工作流：

1. 从 GitHub 拉取代码。
2. 安装依赖并执行测试命令。
3. 使用 Kaniko 构建镜像并推送到 GHCR。
4. 修改 `k8s/dev/app-deployment.yaml` 中的镜像 tag。
5. 将 manifest 变更提交并 push 回 GitHub。
6. 调用 Argo CD 同步 `hello-copilot-dev`。

需要先准备 Secret。复制 `argo-workflows/dev/cicd-secrets.example.yaml`，填入真实值后应用：

```bash
kubectl apply -f argo-workflows/dev/cicd-secrets.yaml
```

注意不要提交包含真实 token 的 `cicd-secrets.yaml`。

GitHub token 至少需要：

- Repository contents: read/write，用于把更新后的 manifest push 回 GitHub。
- Packages: read/write，用于把镜像 push 到 GHCR。

应用 CI/CD 模板：

```bash
kubectl apply -f argo-workflows/dev/cicd-rbac.yaml
kubectl apply -f argo-workflows/dev/cicd-workflow-template.yaml
```

手动触发一次：

```bash
kubectl create -f argo-workflows/dev/run-cicd-workflow.yaml
kubectl get workflows -n study-dev
```

这个模板默认使用：

- GitHub 仓库：`linxichong/HelloCopilot`
- 分支：`master`
- 镜像仓库：`ghcr.io/linxichong/hellocopilot`
- Argo CD 应用：`hello-copilot-dev`

如果要做到“代码 push 后自动触发 Argo Workflow”，还需要安装 Argo Events，并把 GitHub webhook 接到这个 WorkflowTemplate。更简单的生产实践是：GitHub Actions 负责测试、构建、推镜像和更新 manifest，Argo CD 负责自动同步部署。

## Argo Events 自动触发

`argo-events/dev` 目录提供了 GitHub push webhook 触发 CI/CD Workflow 的配置：

- `eventbus.yaml`：Argo Events 的默认 EventBus。
- `eventsource.yaml`：接收 GitHub Webhook 的 HTTP 入口，路径是 `/github`。
- `sensor.yaml`：过滤 `linxichong/HelloCopilot` 的 `master` push，并创建 CI/CD Workflow。
- `rbac.yaml`：允许 Sensor 在 `study-dev` 创建 Workflow。

安装 Argo Events：

```bash
kubectl create namespace argo-events
kubectl apply -n argo-events -f https://raw.githubusercontent.com/argoproj/argo-events/stable/manifests/install.yaml
kubectl -n argo-events rollout status deployment/controller-manager
```

应用触发配置：

```bash
kubectl apply -f argo-events/dev/eventbus.yaml
kubectl apply -f argo-events/dev/rbac.yaml
kubectl apply -f argo-events/dev/eventsource.yaml
kubectl apply -f argo-events/dev/sensor.yaml
```

本地测试 webhook：

```bash
kubectl -n argo-events port-forward service/hello-copilot-github-webhook-eventsource-svc 12000:12000

curl -X POST http://127.0.0.1:12000/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -d '{"ref":"refs/heads/master","repository":{"full_name":"linxichong/HelloCopilot"},"head_commit":{"author":{"name":"wukai"}}}'
```

GitHub 真正自动触发时，需要把 EventSource 暴露成公网地址。Kind 本地集群可以用 ngrok 或 cloudflared tunnel：

```bash
kubectl -n argo-events port-forward --address 0.0.0.0 service/hello-copilot-github-webhook-eventsource-svc 12000:12000
```

然后将公网地址配置到 GitHub Webhook：

```text
Payload URL: https://<your-public-tunnel>/github
Content type: application/json
Events: Just the push event
```

Sensor 已经过滤掉 `hello-copilot-bot` 提交的 manifest commit，避免 CI/CD 工作流 push 回 GitHub 后再次触发自己。
