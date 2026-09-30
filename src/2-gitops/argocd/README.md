# Argo CD GitOps 範例

此目錄定義 Argo CD 的 `AppProject` 與 `Application`。`todo` Application 會讀取本 repository 的 `src/1-kubernetes/kind`，將 Todo 的 Kubernetes 資源同步到 `todo` Namespace。

`microservice-health.yaml` 是尚未套用的 `argocd-cm` 自訂 health 範例，不包含在此目錄的 `kustomization.yaml`。現有 CRD 尚無 `status.conditions`，也沒有 Operator 寫入狀態；必須先完成這兩項，並將 health key 併入既有的 `argocd-cm`，不可直接用範例覆蓋整份 ConfigMap。現有 `todo` Application 也尚未讀取 `Microservice`。

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
