[English](README.md) | [繁體中文](README-zh-TW.md)

# Backstage 與 Microservice Operator

Day 17–27 的範例以 Backstage 提供服務目錄、設定表單與 Kubernetes 查詢；Operator 讀取 `Microservice`，管理 Todo API 的 Deployment／Service 並回報狀態。指令皆從儲存庫根目錄執行，僅適用已核准的測試叢集。

## 檔案與教學階段

| 位置 | 用途 |
| --- | --- |
| `operator/day20/handlers.py` | create、spec update、resume，只記錄輸入並寫 `Accepted` |
| `operator/day21/handlers.py`、`operator/resources.py` | 資源建立、更新與定期補回，寫 `ResourcesApplied`／`Failed` |
| `operator/handlers.py`、`operator/resources.py` | Day 22 檢查新版副本、Pod 與 EndpointSlice 是否就緒，並回報 conditions |
| `operator/k8s/` | Operator 的 ServiceAccount、RBAC 與 Deployment |
| `backstage/app/` | Backstage 前後端原始碼與建置設定 |
| `backstage/catalog-info.yaml` | Todo API、BFF、Web 的 Catalog 定義 |
| `backstage/todo-api-dev/` | Day 23 預覽模板、Day 24 PR 模板與共用的 YAML 範本 |
| `backstage/k8s/`、`backstage/k8s-pr/` | 預覽部署與啟用 GitHub PR 的 overlay |

## 部署 Operator

先確認 context、既有 `todo` Namespace 與 [CRD](../1-kubernetes/README-zh-TW.md)。升級 CRD 前，請檢查所有 Namespace 的 CR，先修正不符合新 schema 的資料。

```bash
kubectl config current-context
kubectl get namespace todo
kubectl get crd microservices.platform.example.io
```

Day 20 不管理工作負載，可先部署它：

```bash
kubectl create configmap microservice-operator-code -n todo \
  --from-file=handlers.py=src/4-idp/operator/day20/handlers.py \
  --from-file=requirements.txt=src/4-idp/operator/requirements.txt \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f src/4-idp/operator/k8s/rbac.yaml \
  -f src/4-idp/operator/k8s/deployment.yaml
kubectl rollout restart deployment/microservice-operator -n todo
kubectl rollout status deployment/microservice-operator -n todo --timeout=300s
kubectl apply -f src/1-kubernetes/crd/todo-api.yaml
kubectl logs deployment/microservice-operator -n todo -c operator
```

確認 `Accepted` 與本次操作的日誌。port 修改演練僅適用 Day 20；後續版本會修改正在執行的工作負載。

### 切換到 Day 21／22

首次交由 Operator 管理前，先停止 Argo CD 或其他 controller 管理既有的 Todo API Deployment／Service，再移除這兩個資源，由 Operator 重建。請安排服務中斷與 API 記憶體資料遺失，並避免 Argo CD 的 prune／selfHeal 干擾移交。若仍有外部管理的同名資源，Operator 會回報衝突。

Day 21 使用以下 ConfigMap：

```bash
kubectl create configmap microservice-operator-code -n todo \
  --from-file=handlers.py=src/4-idp/operator/day21/handlers.py \
  --from-file=resources.py=src/4-idp/operator/resources.py \
  --from-file=requirements.txt=src/4-idp/operator/requirements.txt \
  --dry-run=client -o yaml | kubectl apply -f -
```

Day 22 改用以下 ConfigMap，並先依 Kubernetes README 確認 CRD 已支援 conditions：

```bash
kubectl create configmap microservice-operator-code -n todo \
  --from-file=handlers.py=src/4-idp/operator/handlers.py \
  --from-file=resources.py=src/4-idp/operator/resources.py \
  --from-file=requirements.txt=src/4-idp/operator/requirements.txt \
  --dry-run=client -o yaml | kubectl apply -f -
```

選定一個階段後，套用部署設定並重啟，才會載入新的程式：

```bash
kubectl apply -f src/4-idp/operator/k8s/rbac.yaml \
  -f src/4-idp/operator/k8s/deployment.yaml
kubectl rollout restart deployment/microservice-operator -n todo
kubectl rollout status deployment/microservice-operator -n todo --timeout=300s
kubectl get microservice todo-api -n todo -o yaml
```

Day 21 提交資源設定後就回報 `ResourcesApplied`，不檢查就緒狀態。Day 22 須先確認 CR 的 `metadata.generation`、`status.observedGeneration` 與 conditions 的 `observedGeneration` 一致，再判讀 `Ready`／`Stalled`；只等 `Ready=True` 可能讀到舊結果。Todo API 的健康狀態也須與 Operator 程序探針分開確認。

`operator/operator-repair-check.yaml` 是 D21 的短暫資源補回案例。執行前確認同名 CR、Deployment、Service 都不存在；刪除測試 Service 後，確認新 UID，再讓 Operator 保持運作並刪除測試 CR。刪除正式 CR 也會回收它擁有的工作負載，不要直接清除 Kopf timer 的 finalizer。

Operator 以單副本、`Recreate` 與 `--namespace=todo --standalone` 執行，沒有高可用性。程式由 ConfigMap 掛載，依賴由 init container 每次啟動時從 PyPI 安裝；正式部署應將兩者打包進 image。Role 授權涵蓋整個 `todo`，程式內的所有權檢查無法提供逐服務的 RBAC 隔離。

## 建置 Backstage

需要 Node.js 22 或 24、Corepack，以及支援 BuildKit 與 Buildx 的 Docker。`app/` 使用 Yarn 4，執行用的 image 使用 Node 24。推送前請登入 GHCR，確認具備目標 package 的寫入權限。服務目錄以 `backstage/catalog-info.yaml` 為準，建置前複製到 image 讀取的位置：

```bash
cp src/4-idp/backstage/catalog-info.yaml src/4-idp/backstage/app/examples/entities.yaml
cd src/4-idp/backstage/app
corepack yarn install --immutable
corepack yarn tsc
corepack yarn build:backend
corepack yarn build-image
docker push ghcr.io/yrw9281/it30-idp-backstage:demo
cd ../../../..
```

請保留 `packages/app` 與 `packages/backend`，兩者都是必要原始碼。image 內的 `app-config.yaml` 改變時須重新建置，只重啟不會更新設定。一般網路環境不需要企業代理 CA，請維持 TLS 驗證。

## 設定 Kubernetes 查詢連線

先透過核准流程建立 `backstage` Namespace，並沿用既有的 `todo`。以下 RBAC 授予 reader 指定種類的唯讀權限，不包含 Secret 或 Microservice：

```bash
kubectl config current-context
kubectl get namespace backstage
kubectl get namespace todo
kubectl apply -f src/4-idp/backstage/k8s/rbac-reader.yaml
```

在 Bash 中執行以下區塊，以目前 context 的 API URL、CA 和一小時 ServiceAccount token 建立連線 Secret。Backstage Pod 必須能連到這個 API URL；遠端工作站使用的 localhost 位址通常不適用。不要啟用 shell tracing：

```bash
set -euo pipefail
api_url=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
ca_data=$(kubectl config view --raw --flatten --minify \
  -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')
token=$(kubectl create token backstage-k8s-reader -n todo --duration=1h)
test -n "$api_url" && test -n "$ca_data" && test -n "$token"
printf 'apiUrl=%s\ncaData=%s\ntoken=%s\n' "$api_url" "$ca_data" "$token" |
  kubectl create secret generic backstage-k8s-conn -n backstage \
    --from-env-file=/dev/stdin --dry-run=client -o json |
  kubectl apply --server-side --field-manager=backstage-connection -f -
unset api_url ca_data token
```

token 效期由 API Server 決定，Secret 不會自動續期。更新連線 Secret 後，須重啟 Backstage 以重新讀取環境變數。遇到 `Unauthorized` 查 token，遇到 `Forbidden` 查 RBAC；排查時仍應使用唯讀身分並維持 TLS 驗證。

## 載入 Day 23 預覽模板

預設只註冊產生 YAML 的模板，不注入 GitHub token，也不修改 Git 或 Kubernetes 工作負載：

```bash
kubectl create configmap backstage-todo-templates -n backstage \
  --from-file=app-config.templates.yaml=src/4-idp/backstage/k8s/app-config.templates.yaml \
  --from-file=preview-template.yaml=src/4-idp/backstage/todo-api-dev/preview-template.yaml \
  --from-file=template.yaml=src/4-idp/backstage/todo-api-dev/template.yaml \
  --from-file=microservice.yaml=src/4-idp/backstage/todo-api-dev/skeleton/microservice.yaml \
  --from-file=kustomization.yaml=src/4-idp/backstage/todo-api-dev/skeleton/kustomization.yaml \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -k src/4-idp/backstage/k8s
kubectl rollout restart deployment/backstage -n backstage
kubectl rollout status deployment/backstage -n backstage --timeout=180s
```

模板以唯讀 `subPath` 掛載，更新 ConfigMap 後要重啟 Pod。這也避免將整個 projected volume 的時間戳 symlink 暴露給 Backstage 的安全路徑檢查。

## 啟用 Day 24 的 GitHub PR

示範採 Guest 登入與 allow-all permission policy，只能透過可信任的 loopback port-forward 使用；取得寫入憑證時更不能公開。正式入口需要登入與模板／action 授權。

準備只允許 `yrw9281/IT30.Platform.Engineering` 的 fine-grained PAT，授予 Contents 與 Pull requests 的讀寫權，設定效期，並確認使用者已有 repository 權限。不要將 token 放進表單、Git 或瀏覽器。在 Bash 中隱藏輸入：

```bash
set -euo pipefail
read -r -s -p 'GitHub token: ' github_token
printf '\n'
test -n "$github_token"
printf 'token=%s\n' "$github_token" |
  kubectl create secret generic backstage-github -n backstage \
    --from-env-file=/dev/stdin --dry-run=client -o json |
  kubectl apply --server-side --field-manager=backstage-github -f -
unset github_token
```

重新執行上一節的 ConfigMap 命令，但將第一個 `--from-file` 的來源改為 `src/4-idp/backstage/k8s-pr/app-config.templates.yaml`，其餘檔案相同。接著使用 PR overlay：

```bash
kubectl apply -k src/4-idp/backstage/k8s-pr
kubectl rollout restart deployment/backstage -n backstage
kubectl rollout status deployment/backstage -n backstage --timeout=180s
```

此模式保留 D23 預覽並加入 D24 PR 模板。PR 模板只收集 digest，建立分支並向 `main` 的 `src/5-config/apps/todo-api/overlays/dev` 提出變更，不會合併。Git 端仍須設定檢查、人工審查與分支保護，並核對 image 是否來自受信任的 CI。

停用時重新執行完整的預覽模式部署，確認新的 Deployment 不再注入 `GITHUB_TOKEN`，並撤銷不再使用的 PAT。token 輪替後也要重啟 Pod。

## 開啟入口與查詢狀態

```bash
kubectl port-forward service/backstage 7007:7007 -n backstage --address=127.0.0.1
```

開啟 `http://localhost:7007`，與 `app-config.production.yaml` 的 base URL 一致，再以 Guest 登入。Create 頁面選 D23 預覽或 D24 PR 模板，填入 Todo API CI 產出的 64 位小寫十六進位 digest，不含 `sha256:`。

Catalog 的 Kubernetes 檢視在 `todo` 中以 `app=todo-api` 等 selector 查詢資源的 labels，不顯示 Microservice conditions，也不記錄 PR、CI 或交付事件歷史。`owner: todo` 記錄負責團隊，不授予存取權。`skipMetricsLookup: true` 關閉 Kubernetes Metrics API 查詢，不影響 Grafana。

Backstage 的 SQLite 存在容器本機，容器重建或換版會遺失任務歷史。PR 用來提出變更，合併後是否部署，由 [Argo CD 的設定來源](../2-gitops/README-zh-TW.md)決定。
