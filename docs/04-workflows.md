# 04. Argo Workflows CI/CD

这一章用于学习用 Argo Workflows 跑 CI/CD：测试、构建镜像、更新 manifest、触发 Argo CD。

## 安装控制器

下面版本号可以按需要替换为 Argo Workflows GitHub Releases 上的正式版本。

```bash
ARGO_WORKFLOWS_VERSION="v4.0.4"
kubectl create namespace argo
kubectl apply --server-side -f "https://github.com/argoproj/argo-workflows/releases/download/${ARGO_WORKFLOWS_VERSION}/install.yaml"
```

访问 UI：

```bash
kubectl -n argo port-forward --address 0.0.0.0 service/argo-server 2746:2746
```

打开：

- https://localhost:2746

## CI/CD 流程

`argo-workflows/dev/cicd-workflow-template.yaml` 提供学习用 CI/CD 工作流：

1. 从 GitHub 拉取代码。
2. 安装测试依赖并执行测试。
3. 使用 Kaniko 构建镜像并推送到 GHCR。
4. 修改 `k8s/dev/kustomization.yaml` 中的镜像 tag。
5. 将 manifest 变更提交并 push 回 GitHub。
6. 调用 Argo CD 同步 `hello-copilot-dev`。

## 准备 Secret

复制示例文件：

```bash
cp argo-workflows/dev/cicd-secrets.example.yaml argo-workflows/dev/cicd-secrets.yaml
```

填入真实值后应用：

```bash
kubectl apply -f argo-workflows/dev/cicd-secrets.yaml
```

不要提交包含真实 token 的 `cicd-secrets.yaml`。

GitHub token 至少需要：

- Repository contents: read/write，用于把更新后的 manifest push 回 GitHub。
- Packages: read/write，用于把镜像 push 到 GHCR。

## 应用模板

```bash
kubectl apply -f argo-workflows/dev/cicd-rbac.yaml
kubectl apply -f argo-workflows/dev/cicd-workflow-template.yaml
```

## 手动触发

```bash
kubectl create -f argo-workflows/dev/run-cicd-workflow.yaml
kubectl get workflows -n study-dev
```

查看步骤 Pod：

```bash
kubectl -n study-dev get pods -l workflows.argoproj.io/workflow=<workflow-name>
```

查看某一步日志：

```bash
kubectl -n study-dev logs pod/<pod-name> -c main
```

## 默认参数

WorkflowTemplate 默认使用：

- GitHub 仓库：`linxichong/HelloCopilot`
- 分支：`master`
- 镜像仓库：`ghcr.io/linxichong/hellocopilot`
- Argo CD 应用：`hello-copilot-dev`
