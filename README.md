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
│       ├── V6__add_age_to_items.sql
│       └── V7__add_name2_to_items.sql
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── Dockerfile
├── .dockerignore
├── argocd/
│   ├── app-dev.yaml
│   ├── app-prod.yaml
│   └── app-authentik-dev.example.yaml
├── authentik/
│   └── dev/
│       └── values.example.yaml
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
kubectl port-forward --address 0.0.0.0 service/hello-copilot 8000:80 -n study-dev
# 或者对于本番环境：
# kubectl port-forward --address 0.0.0.0 service/hello-copilot 8000:80 -n study-prod
```

然后打开：

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/health

注意：

- 开发环境使用 `emptyDir` 存储，数据仅在 Pod 存活期间保留。
- 本番环境使用 PVC 存储，数据会在 Pod 重建时保留。
- `flyway-configmap.yaml` 是给 Argo CD 同步用的生成产物，由 `scripts/generate-flyway-configmaps.sh` 从 `db/migration/*.sql` 生成，不要手动编辑 ConfigMap 里的 SQL；新增 migration 时只维护 `db/migration` 下的 SQL 文件。
- CI/CD 会在部署提交里重新生成并提交 `flyway-configmap.yaml`，避免手工维护生成内容。
- `flyway-migrate` 在 Argo CD 中作为 `PreSync` hook 运行，每次 Argo CD sync 前会重新创建并执行；迁移失败时会停止后续部署。
- 如果绕过 Argo CD 直接用 `kubectl apply`，Kubernetes Job 不会自动重复执行，需要先删除旧 Job 再应用相应的 `k8s/dev/flyway-job.yaml` 或 `k8s/prod/flyway-job.yaml`。

## Argo CD

访问 Argo CD UI：

```bash
kubectl -n argocd port-forward --address 0.0.0.0 service/argocd-server 8080:443
```

然后打开：

- https://127.0.0.1:8080

注意这里是 `https`，不是 `http`。

如果在 WSL 里启动 port-forward，但 Windows 浏览器不能直接访问 `127.0.0.1`，可以查看 WSL IP：

```bash
hostname -I
```

假设输出是 `172.21.91.143`，Windows 浏览器打开：

- https://172.21.91.143:8080

如果 `8080` 被占用，可以换成本地其他端口：

```bash
kubectl -n argocd port-forward --address 0.0.0.0 service/argocd-server 8081:443
```

然后打开：

- https://172.21.91.143:8081

应用当前项目的 Argo CD Application：

```bash
kubectl apply -f argocd/app-dev.yaml
kubectl apply -f argocd/app-prod.yaml
```

### 使用 Authentik 登录 Argo CD

本地 Kind/WSL 环境里，OIDC 地址需要同时被 Windows 浏览器和集群内的 Argo CD 访问到。建议同时启动两个 port-forward，并使用 WSL IP 作为访问地址：

```bash
kubectl -n authentik port-forward --address 0.0.0.0 service/authentik-server 9000:80
kubectl -n argocd port-forward --address 0.0.0.0 service/argocd-server 8080:443
hostname -I
```

假设 WSL IP 是 `172.21.91.143`，下面示例使用：

- Authentik URL：`http://172.21.91.143:9000`
- Argo CD URL：`https://172.21.91.143:8080`

在 Authentik Admin interface 中创建 Argo CD 的应用：

1. 进入 `Directory` -> `Groups`，创建 `ArgoCD Admins`，并把你的用户加入该组。
2. 可选：创建 `ArgoCD Viewers`，用于只读用户。
3. 进入 `Applications` -> `Applications`，创建新应用。
4. Provider type 选择 `OAuth2/OpenID Connect`。
5. Application 名称填写 `Argo CD`，slug 建议填写 `argocd`。
6. Redirect URI 添加：

```text
https://172.21.91.143:8080/api/dex/callback
https://localhost:8085/auth/callback
```

创建完成后，记录 Authentik 生成的：

- Client ID
- Client Secret
- Application slug，例如 `argocd`

把 Authentik client secret 写入 Argo CD：

```bash
AUTHENTIK_CLIENT_SECRET="替换成 Authentik 里的 Client Secret"
AUTHENTIK_CLIENT_SECRET_B64="$(printf '%s' "$AUTHENTIK_CLIENT_SECRET" | base64 -w 0)"

kubectl -n argocd patch secret argocd-secret \
  --type merge \
  -p "{\"data\":{\"dex.authentik.clientSecret\":\"${AUTHENTIK_CLIENT_SECRET_B64}\"}}"
```

配置 Argo CD 使用 Authentik：

```bash
ARGOCD_URL="https://172.21.91.143:8080"
AUTHENTIK_ISSUER="http://172.21.91.143:9000/application/o/argocd/"
AUTHENTIK_CLIENT_ID="替换成 Authentik 里的 Client ID"

kubectl -n argocd patch cm argocd-cm \
  --type merge \
  -p "{
    \"data\": {
      \"url\": \"${ARGOCD_URL}\",
      \"dex.config\": \"connectors:\\n- type: oidc\\n  id: authentik\\n  name: authentik\\n  config:\\n    issuer: ${AUTHENTIK_ISSUER}\\n    clientID: ${AUTHENTIK_CLIENT_ID}\\n    clientSecret: \\$dex.authentik.clientSecret\\n    insecureEnableGroups: true\\n    scopes:\\n    - openid\\n    - profile\\n    - email\\n    - groups\\n\"
    }
  }"
```

配置 Argo CD RBAC，把 Authentik 组映射到 Argo CD 角色：

```bash
kubectl -n argocd patch cm argocd-rbac-cm \
  --type merge \
  -p '{
    "data": {
      "policy.csv": "g, ArgoCd Admins, role:admin\ng, ArgoCD Admins, role:admin\ng, ArgoCd Viewers, role:readonly\ng, ArgoCD Viewers, role:readonly\n",
      "scopes": "[groups]"
    }
  }'
```

重启 Argo CD Dex 和 server：

```bash
kubectl -n argocd rollout restart deployment/argocd-dex-server
kubectl -n argocd rollout restart deployment/argocd-server
kubectl -n argocd rollout status deployment/argocd-dex-server
kubectl -n argocd rollout status deployment/argocd-server
```

重新打开 Argo CD：

- https://172.21.91.143:8080

登录页会出现 `LOG IN VIA AUTHENTIK`，点击后会跳转到 Authentik 登录。

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
kubectl -n argo port-forward --address 0.0.0.0 service/argo-server 2746:2746
```

然后打开：

- https://localhost:2746

### 使用 Authentik 登录 Argo Workflows

Argo Workflows UI 也可以接入 Authentik SSO。为了让 Authentik 用户门户里单独显示 `Argo Workflows`，建议为它创建独立的 Authentik Application / Provider：

- Application 名称：`Argo Workflows`
- Slug：`argo-workflows`
- Provider type：`OAuth2/OpenID Connect`
- Launch URL：`https://172.21.91.143:2746`
- Redirect URI：

```text
https://172.21.91.143:2746/oauth2/callback
```

这里的 `172.21.91.143` 替换成当前 WSL IP：

```bash
hostname -I
```

准备 Argo Workflows SSO Secret：

```bash
cp argo-workflows/dev/sso-secret.example.yaml argo-workflows/dev/sso-secret.yaml
```

把 `Argo Workflows` Provider 的 `Client ID` 和 `Client Secret` 填入 `argo-workflows/dev/sso-secret.yaml`，然后应用：

```bash
kubectl apply -f argo-workflows/dev/sso-secret.yaml
kubectl apply -f argo-workflows/dev/sso-rbac.yaml
```

配置 Argo Workflows SSO：

```bash
kubectl -n argo patch cm workflow-controller-configmap \
  --type merge \
  -p '{
    "data": {
      "sso": "issuer: http://172.21.91.143:9000/application/o/argo-workflows/\nclientId:\n  name: argo-workflows-sso\n  key: client-id\nclientSecret:\n  name: argo-workflows-sso\n  key: client-secret\nredirectUrl: https://172.21.91.143:2746/oauth2/callback\nscopes:\n- groups\n- email\n- profile\nrbac:\n  enabled: true\n"
    }
  }'
```

把 Argo Server 切换到 SSO 模式：

```bash
kubectl -n argo patch deployment argo-server \
  --type json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/args","value":["server","--auth-mode=sso"]}]'

kubectl -n argo rollout status deployment/argo-server
```

重新启动 UI：

```bash
kubectl -n argo port-forward --address 0.0.0.0 service/argo-server 2746:2746
```

然后打开：

- https://172.21.91.143:2746

页面会跳转到 Authentik 登录。登录用户需要属于 `ArgoCd Admins` 或 `ArgoCD Admins` 组，才会映射到 `argo-server` ServiceAccount 的权限。

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
kubectl -n argo-events port-forward --address 0.0.0.0 service/hello-copilot-github-webhook-eventsource-svc 12000:12000

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

## Authentik

Authentik 可以作为这个学习项目里的统一登录和 OIDC Provider。后续可以把 Argo CD、Argo Workflows UI 或 FastAPI 接到 Authentik 上做单点登录。

官方 Kubernetes 安装推荐使用 Helm chart。本项目提供了学习用的 values 模板：

```bash
cp authentik/dev/values.example.yaml authentik/dev/values.yaml
```

生成 `secret_key` 和数据库密码：

```bash
openssl rand 60 | base64 -w 0
openssl rand 36 | base64 -w 0
```

把生成的值填入 `authentik/dev/values.yaml` 里的：

- `authentik.secret_key`
- `authentik.postgresql.password`
- `postgresql.auth.password`

安装 Authentik：

```bash
helm repo add authentik https://charts.goauthentik.io
helm repo update
helm upgrade --install authentik authentik/authentik \
  -n authentik \
  --create-namespace \
  -f authentik/dev/values.yaml
```

等待组件启动：

```bash
kubectl -n authentik get pods
kubectl -n authentik rollout status deployment/authentik-server
kubectl -n authentik rollout status deployment/authentik-worker
```

本地访问：

```bash
kubectl -n authentik port-forward --address 0.0.0.0 service/authentik-server 9000:80
```

然后打开：

- http://127.0.0.1:9000/if/flow/initial-setup/

首次进入这个地址时设置默认 `akadmin` 用户的密码。注意 URL 最后需要保留 `/`。

如果希望用 Argo CD 管理 Authentik，可以参考 `argocd/app-authentik-dev.example.yaml`。这个文件只是示例，不要直接使用里面的 `CHANGE_ME` 值。

### 使用 Authentik 保护 FastAPI

FastAPI 已支持校验 Authentik 签发的 JWT。`/health` 保持公开，`/me` 和 `/items` 相关接口会在启用认证后要求请求带 Bearer token。

在 Authentik 中为 API 创建独立 Application / Provider：

- Application 名称：`HelloCopilot API`
- Slug：`hello-copilot-api`
- Provider type：`OAuth2/OpenID Connect`
- Launch URL：`http://172.21.91.143:8000/docs`

记录该 Provider 的：

- Client ID
- Issuer：`http://172.21.91.143:9000/application/o/hello-copilot-api/`

本地 `.env` 示例：

```env
AUTH_ENABLED=true
AUTH_ISSUER=http://172.21.91.143:9000/application/o/hello-copilot-api/
AUTH_AUDIENCE=<HelloCopilot API Provider 的 Client ID>
AUTH_REQUIRED_GROUPS=App Users,ArgoCd Admins
```

如果只是学习 JWT 签名和 issuer 校验，可以先留空 `AUTH_AUDIENCE`；填入 Client ID 后会额外校验 token 的 audience。

在 Kind 开发环境启用：

```bash
kubectl -n study-dev set env deployment/hello-copilot-app \
  AUTH_ENABLED=true \
  AUTH_ISSUER=http://172.21.91.143:9000/application/o/hello-copilot-api/ \
  AUTH_AUDIENCE=<HelloCopilot API Provider 的 Client ID> \
  AUTH_REQUIRED_GROUPS="App Users,ArgoCd Admins"

kubectl -n study-dev rollout status deployment/hello-copilot-app
```

访问 API：

```bash
kubectl port-forward --address 0.0.0.0 service/hello-copilot 8000:80 -n study-dev
```

公开接口：

```bash
curl http://172.21.91.143:8000/health
```

受保护接口：

```bash
curl http://172.21.91.143:8000/me \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

没有 token 访问 `/me` 或 `/items` 会返回 `401`；用户不在 `AUTH_REQUIRED_GROUPS` 中会返回 `403`。
