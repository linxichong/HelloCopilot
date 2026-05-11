# 07. 常见问题与排障

这一章收集学习过程中最常见的故障现象和排查命令。

## port-forward 断开

现象：

```text
failed to find sandbox ... in store: not found
error: lost connection to pod
```

常见原因是 CI/Argo CD 滚动更新时旧 Pod 被删除，原来的 port-forward 还连着旧 Pod。

重新转发 Service：

```bash
kubectl -n study-dev port-forward --address 0.0.0.0 service/hello-copilot 8000:80
```

## Argo CD SSO 报 Dex 连接失败

现象：

```text
failed to query provider "https://.../api/dex"
connect: connection refused
```

先看 Dex：

```bash
kubectl -n argocd get pods,svc,deploy
kubectl -n argocd logs deployment/argocd-dex-server --tail=120
```

如果日志里看到访问 Authentik 失败，通常是 Authentik port-forward 没开，或者 WSL IP 变了。

保持 Authentik port-forward：

```bash
kubectl -n authentik port-forward --address 0.0.0.0 service/authentik-server 9000:80
```

重启 Argo CD Dex 和 server：

```bash
kubectl -n argocd rollout restart deployment/argocd-dex-server
kubectl -n argocd rollout restart deployment/argocd-server
```

## Argo Workflows UI port-forward 失败

现象：

```text
connect: connection refused
error: lost connection to pod
```

先看 `argo-server`：

```bash
kubectl -n argo get pods,svc,deploy
kubectl -n argo logs deployment/argo-server --tail=120
```

如果启用了 SSO，`argo-server` 启动时需要访问 Authentik issuer。确保 Authentik 的 9000 port-forward 正在运行。

## CI 最后一步等待 Argo CD 超时

现象：

```text
timed out waiting for app "hello-copilot-dev" match desired state
```

看 Argo CD 应用：

```bash
kubectl -n argocd get application hello-copilot-dev -o yaml
```

看 dev 资源状态：

```bash
kubectl -n study-dev get pods,deploy,statefulset,svc,pvc,job
kubectl -n study-dev get events --sort-by=.lastTimestamp
```

如果某个 Pod CrashLoopBackOff，查看日志：

```bash
kubectl -n study-dev logs pod/<pod-name> --previous
```

## Postgres 权限错误

现象：

```text
chmod: /var/run/postgresql: Operation not permitted
chown: /var/lib/postgresql/data: Operation not permitted
```

原因通常是对官方 Postgres 镜像过度收紧了 Linux capabilities。官方镜像启动时会调整数据目录权限，不能简单 `capabilities.drop: [ALL]`。

当前项目保留：

```yaml
securityContext:
  allowPrivilegeEscalation: false
```

但没有对 Postgres 容器设置 `drop: [ALL]`。

## Kustomize 渲染检查

```bash
kubectl kustomize k8s/dev
kubectl kustomize k8s/prod
```

client dry-run：

```bash
kubectl apply -k k8s/dev --dry-run=client
kubectl apply -k k8s/prod --dry-run=client
```

server dry-run：

```bash
kubectl apply -k k8s/dev --dry-run=server
```

## 查看 CI 日志

列出 Workflow：

```bash
kubectl -n study-dev get workflows --sort-by=.metadata.creationTimestamp
```

列出某次 Workflow 的 Pod：

```bash
kubectl -n study-dev get pods -l workflows.argoproj.io/workflow=<workflow-name>
```

查看步骤日志：

```bash
kubectl -n study-dev logs pod/<pod-name> -c main
```

## 查看 StatefulSet 和 PVC

```bash
kubectl -n study-dev get statefulset,pvc,pod -l app=hello-copilot-postgres
kubectl -n study-dev describe statefulset hello-copilot-postgres
kubectl -n study-dev describe pvc postgres-data-hello-copilot-postgres-0
```
