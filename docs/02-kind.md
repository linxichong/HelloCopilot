# 02. Kind / Kubernetes 部署

这一章用于学习 Kubernetes 基础部署、Kustomize overlay、StatefulSet、PVC 和 Job。

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

## K8s 资源设计

- 公共资源在 `k8s/base`。
- dev/prod 环境差异在 `k8s/dev/kustomization.yaml` 和 `k8s/prod/kustomization.yaml`。
- PostgreSQL 使用 StatefulSet。
- StatefulSet 通过 `volumeClaimTemplates` 自动创建 PVC。
- `hello-copilot-postgres-headless` 是 StatefulSet 使用的 headless Service。
- `hello-copilot-postgres` 是 app 和 Flyway 访问数据库的普通 ClusterIP Service。
- Flyway Job 在 Argo CD 中作为 `PreSync` hook 运行。

## 常用查看命令

```bash
kubectl -n study-dev get pods
kubectl -n study-dev get deploy,statefulset,svc,pvc,job
kubectl -n study-dev logs statefulset/hello-copilot-postgres
kubectl -n study-dev describe pod <pod-name>
```
