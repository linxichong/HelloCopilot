# 02. Kind / Kubernetes 部署

这一章用于学习 Kubernetes 基础部署、Kustomize overlay、Zalando Postgres Operator / Patroni、PVC 和 Job。

## 创建 Kind 集群

```bash
kind create cluster --name hellocopilot
```

## 构建并加载镜像

```bash
docker build -t hellocopilot:local .
kind load docker-image hellocopilot:local --name hellocopilot
```

dev 环境默认使用 GHCR 镜像。如果你希望在 Kind 里使用本地镜像，可以修改 `k8s/dev/kustomization.yaml` 的 `images` 配置。

## 生成 Flyway ConfigMap

```bash
sh scripts/generate-flyway-configmaps.sh
```

`flyway-configmap.yaml` 是生成产物，不要手动编辑 ConfigMap 里的 SQL。新增 migration 时只维护 `db/migration/*.sql`。

## 安装 Zalando Postgres Operator

数据库由 Zalando Postgres Operator 创建和管理，底层使用 Patroni 做主从复制和故障切换。先在集群里安装 operator，再部署本项目的 `postgresql` CR。

Helm 安装示例：

```bash
helm repo add postgres-operator-charts https://opensource.zalando.com/postgres-operator/charts/postgres-operator
helm repo update
helm upgrade --install postgres-operator postgres-operator-charts/postgres-operator \
  --namespace postgres-operator \
  --create-namespace \
  --set configKubernetes.enable_pod_antiaffinity=true \
  --set configKubernetes.pod_antiaffinity_preferred_during_scheduling=true
```

`pod_antiaffinity_preferred_during_scheduling=true` 对单节点 Kind 很重要：它会尽量把主库和副本分散到不同节点，但在只有一个节点时仍允许两个 Pod 调度成功。

## 部署 dev 环境

```bash
kubectl apply -k k8s/dev
```

## 部署 prod 环境

```bash
kubectl apply -k k8s/prod
```

## 访问 API

```bash
kubectl -n study-dev port-forward --address 0.0.0.0 service/hello-copilot 8000:80
```

然后打开：

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/live
- http://127.0.0.1:8000/ready

## K8s 资源设计

- 公共资源在 `k8s/base`。
- dev/prod 环境差异在 `k8s/dev/kustomization.yaml` 和 `k8s/prod/kustomization.yaml`。
- PostgreSQL 使用 Zalando Postgres Operator 的 `postgresql.acid.zalan.do` CR。
- `k8s/base/postgres-cluster.yaml` 声明 2 个实例：1 个主库和 1 个副本，由 Patroni 管理复制与故障切换。
- `hello-copilot-postgres` 是 app 和 Flyway 访问数据库的读写 Service，指向当前主库。
- `hello-copilot-postgres-repl` 是只读副本 Service，后续读查询或 BI 工具可以连接它。
- `hello-copilot-postgres-proxy` 是 HAProxy Service，`5432` 是写入口，`5433` 是只读入口。
- HAProxy stats 暴露在 `hello-copilot-postgres-proxy:8404/stats`。
- `hello-copilot-postgres-pgbouncer` 是应用侧数据库连接池，应用默认连接它的 `6432` 端口。PgBouncer 使用 transaction pooling，后端再连接 HAProxy 写入口。
- Flyway 仍直接连接 HAProxy 写入口，避免迁移任务和应用连接池互相影响。
- `pgbackrest` sidecar 和 `hello-copilot-postgres-pgbackrest-repo` PVC 用于学习 pgBackRest 物理备份；详细命令见 [pgBackRest 备份与还原](08-backup-restore.md)。
- `test.hello-copilot-postgres.credentials.postgresql.acid.zalan.do` 是 operator 自动生成的数据库用户 Secret。
- Flyway Job 在 Argo CD 中作为 `PreSync` hook 运行。
- app 的 liveness probe 使用 `/live`，只检查进程是否存活。
- app 的 readiness probe 使用 `/ready`，会执行数据库连通性检查。

## 常用查看命令

```bash
kubectl -n study-dev get pods
kubectl -n study-dev get postgresql,deploy,statefulset,svc,pvc,job
kubectl -n study-dev get pods -l application=spilo -L spilo-role
kubectl -n study-dev get deploy,svc hello-copilot-postgres-haproxy hello-copilot-postgres-proxy
kubectl -n study-dev get deploy,svc hello-copilot-postgres-pgbouncer
kubectl -n study-dev get pvc hello-copilot-postgres-pgbackrest-repo
kubectl -n study-dev get secret test.hello-copilot-postgres.credentials.postgresql.acid.zalan.do
kubectl -n study-dev describe pod <pod-name>
```
