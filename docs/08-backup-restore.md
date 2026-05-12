# 08. pgBackRest 备份与还原

这一章用于学习 pgBackRest 的物理备份与还原流程。

当前项目仍使用 Zalando Postgres Operator / Spilo / Patroni 管理主从集群。Zalando 原生推荐的物理备份路线是 WAL-E/WAL-G；pgBackRest 更常见于 Crunchy Postgres Operator。这里采用学习版集成方式：在每个 Spilo Pod 中追加一个 `pgbackrest` sidecar，并挂载独立的 pgBackRest repo PVC。

## 资源设计

- `hello-copilot-postgres-pgbackrest`：pgBackRest 配置。
- `hello-copilot-postgres-pgbackrest-repo`：pgBackRest repo PVC，默认 `2Gi`。
- `pgbackrest` sidecar：运行在 Postgres Pod 内，能访问 Spilo 的 PostgreSQL data directory。
- `/var/run/postgresql`：Postgres 和 pgBackRest sidecar 共享的 Unix socket 目录。
- `hello-copilot` 是 pgBackRest stanza 名称。

配置文件在 `k8s/base/postgres-pgbackrest-configmap.yaml`。

> 注意：当前配置关闭了 `archive-check`，用于 Kind 学习环境的手动演练。生产环境要做 PITR，应该让 PostgreSQL 主机侧配置 pgBackRest `archive-push`，或改用 Zalando 原生 WAL-G 备份方案。

## 查看 Sidecar

```bash
kubectl -n study-dev get pods -l application=spilo -L spilo-role
kubectl -n study-dev get pvc hello-copilot-postgres-pgbackrest-repo
kubectl -n study-dev describe postgresql hello-copilot-postgres
```

找到当前主库 Pod：

```bash
MASTER_POD=$(kubectl -n study-dev get pod -l application=spilo,spilo-role=master -o jsonpath='{.items[0].metadata.name}')
echo "$MASTER_POD"
```

查看 pgBackRest 版本：

```bash
kubectl -n study-dev exec "$MASTER_POD" -c pgbackrest -- pgbackrest version
```

## 创建 Stanza

```bash
kubectl -n study-dev exec "$MASTER_POD" -c pgbackrest -- sh -lc '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  pgbackrest --stanza=hello-copilot --pg1-user="$POSTGRES_USER" stanza-create
'
```

检查 repo：

```bash
kubectl -n study-dev exec "$MASTER_POD" -c pgbackrest -- pgbackrest --stanza=hello-copilot info
```

## 手动全量备份

```bash
kubectl -n study-dev exec "$MASTER_POD" -c pgbackrest -- sh -lc '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  pgbackrest --stanza=hello-copilot --pg1-user="$POSTGRES_USER" --type=full backup
'
```

再次查看备份信息：

```bash
kubectl -n study-dev exec "$MASTER_POD" -c pgbackrest -- pgbackrest --stanza=hello-copilot info
```

## 还原原则

pgBackRest 的物理还原会重写 PostgreSQL data directory，不能在 Patroni 正常运行时直接对主库 Pod 执行。

学习环境建议使用下面两种方式之一：

1. 新建一个临时恢复集群，把 pgBackRest repo PVC 的内容复制过去，在临时集群中执行 restore 后验证数据。
2. 进入维护窗口，停止应用写入，停止 Postgres 集群，清空目标 data directory，再执行 `pgbackrest restore`。

还原命令形态如下，只能在 PostgreSQL 已停止、目标 data directory 可安全重写时执行：

```bash
pgbackrest --stanza=hello-copilot restore
```

恢复后重新启动 Postgres，再用下面命令验证：

```bash
kubectl -n study-dev run restore-check --rm -i --restart=Never \
  --image=postgres:16-alpine \
  --env PGPASSWORD="$(kubectl -n study-dev get secret test.hello-copilot-postgres.credentials.postgresql.acid.zalan.do -o jsonpath='{.data.password}' | base64 -d)" \
  -- psql -h hello-copilot-postgres-proxy -p 5432 -U test -d hello_copilot -c "select count(*) from items;"
```

## 生产建议

如果目标是生产级 pgBackRest 备份/PITR，优先考虑：

- 使用 Crunchy Postgres Operator，它原生集成 pgBackRest。
- 或维护自定义 Spilo 镜像，把 pgBackRest 安装进 PostgreSQL 容器，并配置 `archive_command` / `restore_command`。
- 如果继续使用 Zalando Postgres Operator，优先走它原生支持的 WAL-G 备份与恢复链路。
