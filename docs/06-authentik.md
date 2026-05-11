# 06. Authentik 单点登录与 API 认证

这一章用于学习 Authentik 作为 OIDC Provider，保护 Argo CD、Argo Workflows 和 FastAPI。

## 安装 Authentik

官方 Kubernetes 安装推荐使用 Helm chart。本项目提供学习用 values 模板：

```bash
cp authentik/dev/values.example.yaml authentik/dev/values.yaml
```

生成 `secret_key` 和数据库密码：

```bash
openssl rand 60 | base64 -w 0
openssl rand 36 | base64 -w 0
```

把生成的值填入 `authentik/dev/values.yaml`：

- `authentik.secret_key`
- `authentik.postgresql.password`
- `postgresql.auth.password`

安装：

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

打开：

- http://127.0.0.1:9000/if/flow/initial-setup/

首次进入这个地址时设置默认 `akadmin` 用户密码。URL 最后需要保留 `/`。

## Argo CD 使用 Authentik 登录

本地 Kind/WSL 环境里，OIDC 地址需要同时被 Windows 浏览器和集群内的 Argo CD 访问到。建议同时启动两个 port-forward，并使用 WSL IP：

```bash
kubectl -n authentik port-forward --address 0.0.0.0 service/authentik-server 9000:80
kubectl -n argocd port-forward --address 0.0.0.0 service/argocd-server 8080:443
hostname -I
```

假设 WSL IP 是 `172.21.91.143`：

- Authentik URL：`http://172.21.91.143:9000`
- Argo CD URL：`https://172.21.91.143:8080`

在 Authentik Admin interface 中创建应用：

1. 进入 `Directory` -> `Groups`，创建 `ArgoCD Admins`，并把你的用户加入该组。
2. 可选：创建 `ArgoCD Viewers`。
3. 进入 `Applications` -> `Applications`，创建新应用。
4. Provider type 选择 `OAuth2/OpenID Connect`。
5. Application 名称填写 `Argo CD`，slug 建议填写 `argocd`。
6. Redirect URI 添加：

```text
https://172.21.91.143:8080/api/dex/callback
https://localhost:8085/auth/callback
```

记录：

- Client ID
- Client Secret
- Application slug，例如 `argocd`

写入 Argo CD secret：

```bash
AUTHENTIK_CLIENT_SECRET="替换成 Authentik 里的 Client Secret"
AUTHENTIK_CLIENT_SECRET_B64="$(printf '%s' "$AUTHENTIK_CLIENT_SECRET" | base64 -w 0)"

kubectl -n argocd patch secret argocd-secret \
  --type merge \
  -p "{\"data\":{\"dex.authentik.clientSecret\":\"${AUTHENTIK_CLIENT_SECRET_B64}\"}}"
```

配置 Argo CD：

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

配置 RBAC：

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

重启 Dex 和 server：

```bash
kubectl -n argocd rollout restart deployment/argocd-dex-server
kubectl -n argocd rollout restart deployment/argocd-server
kubectl -n argocd rollout status deployment/argocd-dex-server
kubectl -n argocd rollout status deployment/argocd-server
```

## Argo Workflows 使用 Authentik 登录

创建独立的 Authentik Application / Provider：

- Application 名称：`Argo Workflows`
- Slug：`argo-workflows`
- Provider type：`OAuth2/OpenID Connect`
- Launch URL：`https://172.21.91.143:2746`
- Redirect URI：`https://172.21.91.143:2746/oauth2/callback`

准备 Secret：

```bash
cp argo-workflows/dev/sso-secret.example.yaml argo-workflows/dev/sso-secret.yaml
kubectl apply -f argo-workflows/dev/sso-secret.yaml
kubectl apply -f argo-workflows/dev/sso-rbac.yaml
```

配置 SSO：

```bash
kubectl -n argo patch cm workflow-controller-configmap \
  --type merge \
  -p '{
    "data": {
      "sso": "issuer: http://172.21.91.143:9000/application/o/argo-workflows/\nclientId:\n  name: argo-workflows-sso\n  key: client-id\nclientSecret:\n  name: argo-workflows-sso\n  key: client-secret\nredirectUrl: https://172.21.91.143:2746/oauth2/callback\nscopes:\n- groups\n- email\n- profile\nrbac:\n  enabled: true\n"
    }
  }'
```

切换 Argo Server 到 SSO 模式：

```bash
kubectl -n argo patch deployment argo-server \
  --type json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/args","value":["server","--auth-mode=sso"]}]'

kubectl -n argo rollout status deployment/argo-server
```

## 使用 Authentik 保护 FastAPI

FastAPI 已支持校验 Authentik 签发的 JWT。`/health`、`/live`、`/ready` 保持公开，`/me` 和 `/items` 相关接口会在启用认证后要求请求带 Bearer token。

在 Authentik 中为 API 创建独立 Application / Provider：

- Application 名称：`HelloCopilot API`
- Slug：`hello-copilot-api`
- Provider type：`OAuth2/OpenID Connect`
- Launch URL：`http://172.21.91.143:8000/docs`

本地 `.env` 示例：

```env
AUTH_ENABLED=true
AUTH_ISSUER=http://172.21.91.143:9000/application/o/hello-copilot-api/
AUTH_AUDIENCE=<HelloCopilot API Provider 的 Client ID>
AUTH_REQUIRED_GROUPS=App Users,ArgoCd Admins
```

在 Kind dev 环境启用：

```bash
kubectl -n study-dev set env deployment/hello-copilot-app \
  AUTH_ENABLED=true \
  AUTH_ISSUER=http://172.21.91.143:9000/application/o/hello-copilot-api/ \
  AUTH_AUDIENCE=<HelloCopilot API Provider 的 Client ID> \
  AUTH_REQUIRED_GROUPS="App Users,ArgoCd Admins"

kubectl -n study-dev rollout status deployment/hello-copilot-app
```

访问：

```bash
curl http://172.21.91.143:8000/health
curl http://172.21.91.143:8000/live
curl http://172.21.91.143:8000/ready

curl http://172.21.91.143:8000/me \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```
