# Argo CD GitOps 範例

此目錄定義 Argo CD 的 `AppProject` 與 `Application`。`todo` Application 會讀取本 repository 的 `src/1-kubernetes/kind`，將 Todo 的 Kubernetes 資源同步到 `todo` Namespace。

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
