# Backstage 與 Microservice Operator

對應 Day 17–27。Backstage 提供 Catalog、設定表單與 Kubernetes 查詢；Operator 接收 `Microservice`，管理 Todo API 的 Deployment／Service 並回報狀態。以下指令都從 repository 根目錄執行，且只適用已核准的測試叢集。

## 檔案與教學階段

| 位置 | 用途 |
| --- | --- |
| `operator/day20/handlers.py` | create、spec update、resume，只記錄輸入並寫 `Accepted` |
| `operator/day21/handlers.py`、`operator/resources.py` | 資源建立、更新與定期補回，寫 `ResourcesApplied`／`Failed` |
| `operator/handlers.py`、`operator/resources.py` | Day 22 完整版本，加入新版 rollout、Pod、EndpointSlice 與 conditions |
| `operator/k8s/` | Operator 的 ServiceAccount、RBAC 與 Deployment |
| `backstage/app/` | Backstage 前後端原始碼與建置設定 |
| `backstage/catalog-info.yaml` | Todo API、BFF、Web 的 Catalog 定義 |
| `backstage/todo-api-dev/` | Day 23 設定預覽、Day 24 真正建立 PR 的模板與共同 skeleton |
| `backstage/k8s/`、`backstage/k8s-pr/` | 預覽部署與啟用 GitHub PR 的 overlay |

## 部署 Operator

先確認 context、既有 `todo` Namespace 與 [CRD](../1-kubernetes/README.md)。升級既有 CRD 前，需要讀取所有 Namespace 的 CR，確認舊輸入符合新合約；不要直接收緊 schema 後才修資料。

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

確認 `Accepted` 與本次操作的 log。Day 20 的 port 修改演練只適用這個版本；資源管理版本會真的修改工作負載。

### 切換到 Day 21／22

首次啟用資源管理前，先解除 Argo CD 或其他 controller 對既有 Todo API Deployment／Service 的管理，再移除這兩個舊資源，由 Operator 重新建立。這會中斷服務並遺失 API 記憶體資料，需先確認可接受；不要任由 Argo CD 的 prune／selfHeal 在移交期間刪除或補回資源。範例不會自動接管同名外部資源，遇到衝突會回報失敗。

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

Day 21 的 `ResourcesApplied` 只表示資源設定已提交。Day 22 要比對 CR 的 `metadata.generation`、`status.observedGeneration` 與 conditions 的 `observedGeneration`，一致後再判讀 `Ready`／`Stalled`；只等 `Ready=True` 可能讀到上一版的結果。程序 health probe 也不能代替 Todo API 的健康判斷。

`operator/operator-repair-check.yaml` 是 D21 的短暫資源補回案例。執行前確認同名 CR、Deployment、Service 都不存在；刪除測試 Service 後，確認新 UID，再讓 Operator 保持運作並刪除測試 CR。刪除正式 CR 也會回收它擁有的工作負載，不要直接清除 Kopf timer 的 finalizer。

Operator 單副本、`Recreate`，以 `--namespace=todo --standalone` 執行，沒有 HA。它透過 ConfigMap 掛載程式，init container 每次啟動從 PyPI 安裝依賴；正式部署應將程式與依賴建進 image。Role 的授權涵蓋整個 `todo`，程式的所有權檢查不是逐服務 RBAC 隔離。

## 建置 Backstage

需要 Node.js 22 或 24、Corepack 與 Docker。`app/` 使用 Yarn 4，runtime image 使用 Node 24。Catalog 的 canonical 定義在 `backstage/catalog-info.yaml`；修改後，建置前複製到 image 讀取的位置：

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

`packages/app` 與 `packages/backend` 是必要原始碼，不是依賴快取。image 內的 `app-config.yaml` 改變時要重新建置；只重啟舊 image 不會更新它。公共建置不需要企業代理 CA，也不要停用 TLS 驗證。

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

API Server 決定 token 的實際效期；存進 Secret 不會自動續期。更新連線 Secret 後，重啟 Backstage 才會重新讀取環境變數。`Unauthorized` 要查 token，`Forbidden` 要查 RBAC；不要用管理員憑證或跳過 TLS 驗證來掩蓋錯誤。

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

## 啟用 Day 24 真正的 GitHub PR

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

此模式同時保留 D23 預覽並註冊 D24 PR 模板；後者會實際建立分支與 PR，不會合併。目的地固定為 `main` 與 `src/5-config/apps/todo-api/overlays/dev`，只收集 digest。格式正確不代表 image 來自受信任 CI，Git 端的設定檢查、review 與分支保護仍需另外設定。

停用時重新執行完整的預覽模式部署，確認新的 Deployment 不再注入 `GITHUB_TOKEN`，並撤銷不再使用的 PAT。token 輪替後也要重啟 Pod。

## 開啟入口與查詢狀態

```bash
kubectl port-forward service/backstage 7007:7007 -n backstage --address=127.0.0.1
```

開啟 `http://127.0.0.1:7007`，以 Guest 登入。Create 頁面選 D23 預覽或 D24 PR 模板，填入 Todo API CI 產出的 64 位小寫十六進位 digest，不含 `sha256:`。

Catalog 的 Kubernetes 檢視使用 `todo` Namespace 與 `app=todo-api` 等 selector 查詢各資源自己的 labels。它不自動顯示 Microservice conditions，也沒有逐筆 PR、CI 或交付事件歷史；`owner: todo` 只是 metadata，不是授權。`skipMetricsLookup: true` 表示不查詢 Kubernetes Metrics API，不影響 Grafana。

Backstage 使用 Pod 本機 SQLite，重啟會遺失任務歷史。PR 建立成功只代表提案已送出；是否部署取決於 [Argo CD 的設定來源](../2-gitops/README.md)，同名 Namespace 不代表交付流程已接通。
