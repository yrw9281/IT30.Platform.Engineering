# Argo CD GitOps 範例

此目錄定義 Argo CD 的 `AppProject` 與 `Application`。`todo` Application 會讀取本 repository 的 `src/1-kubernetes/kind`，將 Todo 的 Kubernetes 資源同步到 `todo` Namespace。

`microservice-health.yaml` 是尚未套用的 `argocd-cm` 自訂 health 範例，不包含在此目錄的 `kustomization.yaml`。[canonical CRD](../../1-kubernetes/crd/microservice-crd.yaml) 已定義 `status.conditions`，[Kopf Operator](../../4-idp/operator/README.md) 的 Day 22 完整版本也會寫入狀態；仍須將 health key 併入既有的 `argocd-cm`，不可直接用範例覆蓋整份 ConfigMap。現有 `todo` Application 尚未讀取 `Microservice`，規劃中的 `repo-config`／`todo-dev` Template 與 Application 也尚未串接；Operator 範例只使用既有的 `todo` Namespace，不建立 `todo-dev`。啟用 adoption 前，須先避免此 Application 繼續管理同一組 Deployment／Service。

先安裝 Argo CD：

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm upgrade --install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace
```

再套用 GitOps 資源並確認同步與健康狀態：

```bash
kubectl apply -k src/2-gitops/argocd
argocd app get todo --refresh
argocd app wait todo --sync --health --timeout 300
kubectl get application todo -n argocd
```
