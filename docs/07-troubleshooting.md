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

## Postgres Operator 未安装

现象：

```text
no matches for kind "postgresql" in version "acid.zalan.do/v1"
```

说明集群里还没有安装 Zalando Postgres Operator 或 CRD。先安装 operator，再部署本项目：

```bash
kubectl get crd postgresqls.acid.zalan.do
kubectl -n postgres-operator get pods,deploy
```

## Postgres 主从状态

Zalando Operator 使用 Spilo + Patroni 管理数据库实例。查看当前主库和副本：

```bash
kubectl -n study-dev get pods -l application=spilo -L spilo-role
kubectl -n study-dev get svc hello-copilot-postgres hello-copilot-postgres-repl
kubectl -n study-dev describe postgresql hello-copilot-postgres
```

`spilo-role=master` 是当前读写主库，`spilo-role=replica` 是只读副本。应用和 Flyway 默认连接 `hello-copilot-postgres`，也就是主库 Service。

## HAProxy 状态

HAProxy 负责主从路由。PgBouncer 和 Flyway 通过 `hello-copilot-postgres-proxy:5432` 连接写库。只读连接可以使用 `hello-copilot-postgres-proxy:5433`。

```bash
kubectl -n study-dev get deploy,svc hello-copilot-postgres-haproxy hello-copilot-postgres-proxy
kubectl -n study-dev logs deployment/hello-copilot-postgres-haproxy --tail=120
kubectl -n study-dev port-forward service/hello-copilot-postgres-proxy 8404:8404
```

然后打开 HAProxy stats：

```text
http://127.0.0.1:8404/stats
```

## PgBouncer 状态

应用默认通过 `hello-copilot-postgres-pgbouncer:6432` 连接数据库，PgBouncer 再连接 HAProxy 写入口。

```bash
kubectl -n study-dev get deploy,svc hello-copilot-postgres-pgbouncer
kubectl -n study-dev logs deployment/hello-copilot-postgres-pgbouncer --tail=120
```

进入临时 PostgreSQL 客户端查看 PgBouncer 连接池：

```bash
kubectl -n study-dev run pgbouncer-check --rm -i --restart=Never \
  --image=postgres:16-alpine \
  --env PGPASSWORD="$(kubectl -n study-dev get secret test.hello-copilot-postgres.credentials.postgresql.acid.zalan.do -o jsonpath='{.data.password}' | base64 -d)" \
  -- psql -h hello-copilot-postgres-pgbouncer -p 6432 -U test -d pgbouncer -c "SHOW POOLS;"
```

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

## 查看数据库 StatefulSet 和 PVC

```bash
kubectl -n study-dev get statefulset,pvc,pod -l cluster-name=hello-copilot-postgres
kubectl -n study-dev get pods -l application=spilo -L spilo-role
kubectl -n study-dev describe statefulset hello-copilot-postgres
```
