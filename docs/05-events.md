# 05. Argo Events 自动触发

这一章用于学习 GitHub webhook 如何触发 Argo Workflows。

`argo-events/dev` 目录提供了 GitHub push webhook 触发 CI/CD Workflow 的配置：

- `eventbus.yaml`：Argo Events 的默认 EventBus。
- `eventsource.yaml`：接收 GitHub Webhook 的 HTTP 入口，路径是 `/github`。
- `sensor.yaml`：过滤 `linxichong/HelloCopilot` 的 `master` push，并创建 CI/CD Workflow。
- `rbac.yaml`：允许 Sensor 在 `study-dev` 创建 Workflow。

## 安装 Argo Events

```bash
kubectl create namespace argo-events
kubectl apply -n argo-events -f https://raw.githubusercontent.com/argoproj/argo-events/stable/manifests/install.yaml
kubectl -n argo-events rollout status deployment/controller-manager
```

## 应用触发配置

```bash
kubectl apply -f argo-events/dev/eventbus.yaml
kubectl apply -f argo-events/dev/rbac.yaml
kubectl apply -f argo-events/dev/eventsource.yaml
kubectl apply -f argo-events/dev/sensor.yaml
```

## 本地测试 webhook

```bash
kubectl -n argo-events port-forward --address 0.0.0.0 service/hello-copilot-github-webhook-eventsource-svc 12000:12000
```

另开一个终端：

```bash
curl -X POST http://127.0.0.1:12000/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -d '{"ref":"refs/heads/master","repository":{"full_name":"linxichong/HelloCopilot"},"head_commit":{"author":{"name":"wukai"}}}'
```

## GitHub 真正触发

Kind 本地集群没有公网入口，需要用 ngrok 或 cloudflared tunnel 暴露 EventSource：

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
