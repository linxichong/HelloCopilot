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
├── argocd/
│   ├── app-dev.yaml
│   └── app-prod.yaml
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
- 如果需要重新执行迁移，可以删除旧 Job 后重新应用相应的 `k8s/dev/flyway-job.yaml` 或 `k8s/prod/flyway-job.yaml`。

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
