# 03. Argo CD GitOps 部署

这一章用于学习 Argo CD Application、自动同步、PreSync hook 和 GitOps 工作流。

## 访问 Argo CD UI

```bash
kubectl -n argocd port-forward --address 0.0.0.0 service/argocd-server 8080:443
```

打开：

- https://127.0.0.1:8080

注意是 `https`，不是 `http`。

如果在 WSL 里启动 port-forward，但 Windows 浏览器不能直接访问 `127.0.0.1`，先查看 WSL IP：

```bash
hostname -I
```

假设输出是 `172.21.91.143`，Windows 浏览器打开：

- https://172.21.91.143:8080

如果 `8080` 被占用：

```bash
kubectl -n argocd port-forward --address 0.0.0.0 service/argocd-server 8081:443
```

然后打开：

- https://172.21.91.143:8081

## 应用本项目

```bash
kubectl apply -f argocd/app-dev.yaml
kubectl apply -f argocd/app-prod.yaml
```

dev 应用路径是：

```text
k8s/dev
```

prod 应用路径是：

```text
k8s/prod
```

Argo CD 会识别目录里的 `kustomization.yaml` 并渲染 overlay。

## 查看状态

```bash
kubectl -n argocd get application hello-copilot-dev
kubectl -n argocd get application hello-copilot-dev -o yaml
```

如果使用 Argo CD CLI：

```bash
argocd app get hello-copilot-dev
argocd app sync hello-copilot-dev
argocd app wait hello-copilot-dev --health --sync
```

## GitOps 行为

- 代码和 manifest 以 GitHub 为准。
- CI 更新 `k8s/dev/kustomization.yaml` 里的镜像 tag。
- Argo CD 同步 GitHub 中的 `k8s/dev`。
- Flyway ConfigMap 和 Job 作为 `PreSync` hook 先执行。
- 迁移失败时，后续 app 部署会停止。

## 注意

如果绕过 Argo CD 直接 `kubectl apply -k`，Kubernetes Job 不会自动重复执行。需要先删除旧 Job 再重新应用 overlay：

```bash
kubectl -n study-dev delete job flyway-migrate
kubectl apply -k k8s/dev
```
