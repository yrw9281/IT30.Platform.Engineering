# Argo CD GitOps 範例

對應 Day 07 與 Day 25。設定放在 `argocd/`，以下指令都從 repository 根目錄執行。`todo.yaml` 直接同步原生資源；`todo-config.yaml` 只同步 `Microservice`，由 Operator 管理它的 Deployment 與 Service。兩者不可同時管理 Todo API 的工作負載。

`microservice-health.yaml` 提供 `argocd-cm` 自訂 health，不包含在 `argocd/kustomization.yaml`。[canonical CRD](../1-kubernetes/crd/microservice-crd.yaml) 已定義 `status.conditions`，[Kopf Operator](../4-idp/README.md) 的 Day 22 完整版本也會寫入狀態。使用下方的 server-side apply 將 health key 加入既有 ConfigMap，保留其他管理者的設定；不要使用 `replace` 覆蓋整份 ConfigMap。若 ConfigMap 由 Helm 管理，也要將 health 設定納入 Helm 的設定來源。模板、Operator 與 Catalog 都使用既有的 `todo` Namespace，不另外建立環境。

此 Application 開啟 `selfHeal` 與 `prune`。移交資源時，不能直接從 Git 移除 Todo API 的 Deployment／Service，任由 prune 刪除要保留的工作負載；應先安排保留資源的管理權移交，再讓 Argo CD 同步 CR、Operator 管理 child resources。規劃中的 `repo-config` 也需要對應的 `AppProject.sourceRepos` 與 CR 同步來源設定，Namespace 相同不代表 GitOps 已接通。

## D25–D26：同步 CR 與查詢部署結果

`todo-config.yaml` 使用本 repository 的 `main` 與 `src/5-config/apps/todo-api/overlays/dev`，AppProject 只允許在 `todo` 同步 `platform.example.io/Microservice`。自動同步開啟 `selfHeal`，但不開啟 `prune`，Application 也不使用刪除受管資源的 finalizer。

先確認 Argo CD、CRD 與 Operator 已就緒，且沒有其他 Application 管理 Todo API 的 Deployment／Service。私有 repository 需在 Argo CD 設定 HTTPS 唯讀憑證；repository Secret 可限定 `project: todo-config`，不要將 token 寫入 Git，也不要共用 Backstage 的 PR 寫入憑證。

```bash
kubectl config current-context
kubectl apply --server-side --field-manager=todo-microservice-health \
  -f src/2-gitops/argocd/microservice-health.yaml
kubectl apply -f src/2-gitops/argocd/todo-config.yaml
kubectl wait -n argocd application/todo-config \
  --for=jsonpath='{.status.sync.status}'=Synced --timeout=180s
kubectl wait -n argocd application/todo-config \
  --for=jsonpath='{.status.health.status}'=Healthy --timeout=180s
kubectl get microservice todo-api -n todo -o yaml
kubectl get deployment,pods,svc -n todo -l app=todo-api
```

等待逾時時，查看 Application conditions、CR conditions 與 Pod events，不要將 `Synced` 當成 rollout 已成功。確認 Git 的 digest、CR 的 `spec.image`、Deployment 與 Pod 的 image 一致後，再擷取 Argo CD 與 Backstage 畫面。Backstage 的 Kubernetes 檢視不會直接顯示 CR conditions。

在兩個終端機分別執行：

```bash
kubectl port-forward -n argocd service/argocd-server 8080:80 --address=127.0.0.1
```

```bash
kubectl port-forward -n backstage service/backstage 7007:7007 --address=127.0.0.1
```

Argo CD 若設定 `server.insecure: true`，使用 HTTP，否則使用 HTTPS。這個示範叢集的 `server.rootpath` 與 `server.basehref` 為 `/argocd`，開啟 `http://localhost:8080/argocd/`，登入後選擇 `todo-config`；沒有設定子路徑的安裝則省略 `/argocd`。Backstage 開啟 `http://localhost:7007/catalog/default/component/todo-api/kubernetes`。Guest 示範僅限受控的 loopback 連線。

## 原生資源範例

以下流程讀取 `src/1-kubernetes/kind`，不要在 Operator 已管理 Todo API 時套用。

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
