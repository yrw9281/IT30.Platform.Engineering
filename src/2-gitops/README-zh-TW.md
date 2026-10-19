[English](README.md) | [繁體中文](README-zh-TW.md)

# Argo CD GitOps 範例

Day 07 與 Day 25 的設定放在 `argocd/`，指令皆從儲存庫根目錄執行。Todo API 的管理方式請擇一使用：`todo.yaml` 同步原生資源；`todo-config.yaml` 同步 `Microservice`，由 Operator 管理 Deployment 與 Service。不可同時啟用兩者。

`microservice-health.yaml` 需在 `argocd/kustomization.yaml` 之外單獨套用，將健康檢查加入 `argocd-cm`。它讀取 [canonical CRD](../1-kubernetes/crd/microservice-crd.yaml) 定義、由 Day 22 [Kopf Operator](../4-idp/README-zh-TW.md) 寫入的 `status.conditions`。請用下方的 server-side apply 保留其他管理者的 ConfigMap 欄位，避免以 `replace` 覆蓋整份設定。若由 Helm 管理，也要將健康檢查寫入 Helm 設定來源。模板、Operator 與 Catalog 皆沿用 `todo` Namespace。

`todo.yaml` 開啟 `selfHeal` 與 `prune`，並設定刪除受管資源的 finalizer，直接從 Git 移除 Todo API 的 Deployment／Service 可能刪除正在執行的工作負載。移交方式見 [IDP 說明](../4-idp/README-zh-TW.md#切換到-day-2122)：Operator 會拒絕既有同名資源，切換時須安排服務中斷。若改用獨立設定儲存庫，還要修改 `AppProject.sourceRepos` 與 Application 來源，不能只靠相同的 Namespace 串接。

Argo CD 讀取遠端 Git，不讀取本機檔案。啟用前請確認來源路徑與變更已推送到 `main`；使用 fork 時，同步修改 AppProject、Application 與 Backstage 模板的 repository 設定。

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

等待逾時時，查看 Application 與 CR 的 conditions，以及 Pod 事件。`Synced` 之後仍要確認新版是否就緒，並比對 Git 的 digest、CR 的 `spec.image`、Deployment 與 Pod 的 image，再擷取畫面。CR conditions 須直接查詢，Backstage 的 Kubernetes 檢視不會顯示。

在兩個終端機分別執行：

```bash
kubectl port-forward -n argocd service/argocd-server 8080:80 --address=127.0.0.1
```

```bash
kubectl port-forward -n backstage service/backstage 7007:7007 --address=127.0.0.1
```

Argo CD 若設定 `server.insecure: true`，使用 HTTP，否則使用 HTTPS。只有另外設定 `server.rootpath` 與 `server.basehref` 為 `/argocd` 的安裝，才使用 `/argocd/` 路徑；本目錄的 Application manifests 不設定這些 server 選項。以預設安裝為例，開啟 `https://localhost:8080/`，確認教學環境的自簽憑證後登入，選擇 `todo-config`。Backstage 開啟 `http://localhost:7007/catalog/default/component/todo-api/kubernetes`。Guest 示範僅限受控的 loopback 連線。

## 原生資源範例

以下流程讀取 `src/1-kubernetes/kind`，不要在 Operator 已管理 Todo API 時套用。

需要 Helm 與 `kubectl`。先依 [Kubernetes 說明](../1-kubernetes/README-zh-TW.md)準備所有可排程節點都能使用的本機 image 與 Ingress Controller；Argo CD 不會建置或載入 image。再安裝 Argo CD：

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

執行上面的 `argocd` 指令前，須先安裝 CLI 並登入對應的 Argo CD server。也可改用：

```bash
kubectl wait -n argocd application/todo \
  --for=jsonpath='{.status.sync.status}'=Synced --timeout=300s
kubectl wait -n argocd application/todo \
  --for=jsonpath='{.status.health.status}'=Healthy --timeout=300s
```
