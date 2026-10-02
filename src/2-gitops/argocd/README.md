# Argo CD GitOps 範例

此目錄定義 Argo CD 的 `AppProject` 與 `Application`。`todo` Application 會讀取本 repository 的 `src/1-kubernetes/kind`，將 Todo 的 Kubernetes 資源同步到 `todo` Namespace。

`microservice-health.yaml` 是尚未套用的 `argocd-cm` 自訂 health 範例，不包含在此目錄的 `kustomization.yaml`。[canonical CRD](../../1-kubernetes/crd/microservice-crd.yaml) 已定義 `status.conditions`，[Kopf Operator](../../4-idp/operator/README.md) 的 Day 22 完整版本也會寫入狀態；仍須將 health key 併入既有的 `argocd-cm`，不可直接用範例覆蓋整份 ConfigMap。現有 `todo` Application 尚未讀取 `Microservice`，規劃中的 `repo-config`、Backstage Dev Template 與 CR Application 也尚未串接；模板、Operator 與 Catalog 都使用既有的 `todo` Namespace，不另外建立環境。啟用 adoption 前，須先避免此 Application 繼續管理同一組 Deployment／Service。

此 Application 開啟 `selfHeal` 與 `prune`。移交資源時，不能直接從 Git 移除 Todo API 的 Deployment／Service，任由 prune 刪除要保留的工作負載；應先安排保留資源的管理權移交，再讓 Argo CD 同步 CR、Operator 管理 child resources。規劃中的 `repo-config` 也需要對應的 `AppProject.sourceRepos` 與 CR 同步來源設定，Namespace 相同不代表 GitOps 已接通。

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
