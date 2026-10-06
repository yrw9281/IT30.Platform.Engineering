# Microservice Operator：三個教學階段

CRD 與 CR 範例統一放在 [CRD 目錄](../../1-kubernetes/crd/README.md)。這裡只保存 Python、依賴、測試與 Operator 本身的 RBAC／Deployment，不再保存另一份 Todo CR。

| 階段 | handler | 行為 |
| --- | --- | --- |
| Day 20 | `day20/handlers.py` | 接收 create、spec update、resume，記錄 log 並寫 `Accepted`；不管理工作負載 |
| Day 21 | `day21/handlers.py` + `resources.py` | 建立／更新已擁有的 Deployment、Service，每 10 秒檢查一次；寫 `ResourcesApplied` 或 `Failed` |
| Day 22 | `handlers.py` + `resources.py` | 加入 Pod、Deployment rollout、EndpointSlice 健康檢查與 `Ready`／`Stalled` conditions |

Day 21 只 import `Json`、`InvalidSpec`、`OwnershipConflict`、`check_owner`、`contains`、`desired_resources`，可搭配只含這些函式與必要常數的教學版 `resources.py`。不 import 完整 handler，避免註冊 Day 22 行為。`ResourcesApplied` 只表示資源設定已寫入，不代表 image 可拉取、Pod Ready 或 Service 有可用 endpoint。從完整版本切回 Day 21 時，狀態會清除舊 conditions，避免留下過期的 `Ready`。

原本的 observer `day19` 已改名 `day20`；原本完整的 `day20` 現為 `day22`。腳本拒絕 `day19`，選 `day20` 時也會明確提示行為已改變。省略參數時預設 `day22`，會真的啟用資源管理，不是只做觀察。

## 安全的執行順序

這些步驟會寫入叢集。使用已有的 `todo` Namespace，先檢查 kubeconfig 與權限。腳本不建立 Namespace；缺少 CRD 時會停止並顯示安裝指令。不要為了重跑教學另外建立一組常駐 Todo API。

從本目錄執行：

```bash
kubectl config current-context
kubectl get namespace todo
kubectl apply -f ../../1-kubernetes/crd/microservice-crd.yaml
kubectl wait --for=condition=Established crd/microservices.platform.example.io --timeout=60s
bash deploy.sh day20
kubectl apply -f ../../1-kubernetes/crd/todo-api.yaml
kubectl logs deployment/microservice-operator -n todo -c operator
kubectl get microservice todo-api -n todo -o yaml
```

canonical CRD 包含最新的 schema，但 observer 仍只寫 `Accepted`。升級舊 CRD 前可用 `kubectl get microservices -A -o json | python3 validate_crs.py` 檢查既有輸入；這只讀取資料，不修改 CR。它檢查 `spec`、image、port，不取代 API Server 的完整 schema／admission 驗證。

### Day 21：由 Operator 建立資源

D21 文章採用重新建立工作負載的方式。啟用前，確認 `todo/todo-api` CR 已存在、同名 Deployment／Service 不存在，且沒有 Argo CD 或其他 controller 繼續建立或修改這兩個資源。移除舊工作負載會中斷服務，並遺失 Todo 程序記憶體中的資料，應先確認可以移除並備份需要保留的資料。

```bash
bash deploy.sh day21
kubectl get microservice todo-api -n todo -o yaml
kubectl get deployment,service todo-api -n todo -o yaml
```

### 可選：接管既有 Todo API

若要保留既有 Deployment／Service，可使用一次性的 `adopt.py`，這不是 D21 文章的必要步驟。使用 Python 3.12 環境並安裝 `requirements.txt`，先解除其他 controller 對原本子資源的管理，但保留資源；不能讓 Argo CD 與 Operator 同時管理同一組 Deployment／Service。`adopt.py` 會拒絕帶有 Argo CD tracking annotation／label 的資源，但無法證明所有其他外部控制器都已停用。

```bash
python -m pip install -r requirements.txt
python adopt.py
bash deploy.sh day21
kubectl get microservice todo-api -n todo -o yaml
kubectl get deployment,service todo-api -n todo -o yaml
```

`adopt.py` 只接管既有 `todo/todo-api`：預先檢查兩個資源、Deployment selector、Service 類型與 ownership，再保留 resourceVersion 替換 ownerReferences；不重建 Deployment，也不變更 Service ClusterIP。兩次 API 寫入不是 transaction；若第二次失敗，修復原因後重跑，不要刪除原本資源。Operator 本身不會自動 adoption，同名外部資源會回報 `Failed` 並記錄原因。

保留原有 `app=todo-api` selector，新增 UID label 以關聯 Pod；預設兩個 replicas、CPU request `25m`、memory request `128Mi`，與既有部署一致。新增的工作負載只適用 Todo API 的 `/health/ready`、`/health/live` 和 OTel 預設，不是通用 Web Operator。

### Day 22：健康狀態

```bash
bash deploy.sh day22
kubectl get microservice todo-api -n todo -o yaml
kubectl logs deployment/microservice-operator -n todo -c operator
```

此階段先檢查所有 Namespace 的既有 CR 輸入，再套用 canonical CRD 的 required `spec` 與 conditions schema；執行者需要相應的讀取與 CRD 更新權限。`Ready` 要求 Deployment 已觀察目前版本、更新副本全部就緒，且 EndpointSlice 有屬於目標 image Pod 的 ready endpoint。Pod image 錯誤或 rollout 超時會寫 `Stalled`；`observedGeneration` 用來區分舊狀態與本次設定。

等待程式可以自動核對 CR、status 與 condition 的 generation，避免 `kubectl wait --for=condition=Ready` 立即讀到上一版 `Ready=True`。D22 正文聚焦健康判斷、狀態產生與處理流程，只保留一個狀態查詢指令；以下演練與等待程式留在本文件：

```bash
python3 wait-current.py Ready
# 錯誤 image 演練時，改等目前 generation 的 Stalled=True
python3 wait-current.py Stalled
```

程式只需 Python 標準函式庫與可用的 `kubectl`。預設查詢 `todo/todo-api`，等待期間 spec 或 CR UID 再次變更會明確失敗，也不把正在刪除的資源當成 Ready；逾時會列出最後的 status，API 錯誤也不會當成尚未就緒而忽略。

### 使用 CI digest 驗證更新

以下使用已確認來源的 CI image reference，不要求從 container runtime 擷取 digest。只在可接受服務中斷與 Todo 記憶體資料遺失的測試環境執行；先確認目前 generation 的 `Ready=True`。若已有服務合約的 `todo-api.yaml`，在同一個終端機先保存原 image 和資源 UID：

```bash
original_image=$(kubectl get microservice todo-api -n todo -o jsonpath='{.spec.image}')
deployment_uid=$(kubectl get deployment todo-api -n todo -o jsonpath='{.metadata.uid}')
service_uid=$(kubectl get service todo-api -n todo -o jsonpath='{.metadata.uid}')
```

任一查詢失敗或原 image 為空時，停止並排查，不要繼續演練。將 `todo-api.yaml` 的 `spec.image` 改成 CI 產出的 Todo API 完整 digest reference，包含 image repository、`@sha256:` 與 64 位小寫十六進位 digest，其餘欄位不變。採用前核對 GHCR package 與受信任 CI run，reference 必須與目前不同才會觸發設定更新。以下會直接修改測試叢集，不是 Git PR／Argo CD 路徑的整合驗證；等待可使用本目錄的 `wait-current.py`：

```bash
kubectl apply -f todo-api.yaml
python3 wait-current.py Ready
kubectl get deployment todo-api -n todo \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
test "$(kubectl get microservice todo-api -n todo -o jsonpath='{.spec.image}')" = "$(kubectl get deployment todo-api -n todo -o jsonpath='{.spec.template.spec.containers[0].image}')"
test "$deployment_uid" = "$(kubectl get deployment todo-api -n todo -o jsonpath='{.metadata.uid}')"
test "$service_uid" = "$(kubectl get service todo-api -n todo -o jsonpath='{.metadata.uid}')"
```

也可以手動查詢 CR generation、status 的 observed generation 與 conditions。要確認它們對應本次提交，不能只看到舊的 `Ready=True` 就繼續：

```bash
kubectl get microservice todo-api -n todo \
  -o jsonpath='{.metadata.generation}{"\n"}{.status.observedGeneration}{"\n"}{.status.conditions}{"\n"}'
```

若要演練錯誤 image，先保留同一個終端機的 `original_image`，確認 `operator-missing-image` tag 確實不存在，再執行：

```bash
kubectl patch microservice todo-api -n todo --type=merge \
  -p '{"spec":{"image":"ghcr.io/yrw9281/it30-todo-api:operator-missing-image"}}'
kubectl get microservice todo-api -n todo -o yaml
kubectl get deployment,pods -n todo -l app=todo-api
```

核對本次 generation 的 `Ready=False`、`Stalled=True`，以及 `ErrImagePull` 或 `ImagePullBackOff` 原因；可使用 `python3 wait-current.py Stalled`。舊副本可能仍可用，不能因此認定新版就緒。若等待期間 CR 換版或重建，停止並核對新需求。無論等待成功或失敗，都要還原：

```bash
kubectl patch microservice todo-api -n todo --type=merge \
  -p "{\"spec\":{\"image\":\"$original_image\"}}"
```

任一命令失敗都應先排查。還原後核對目前 generation 的 `Ready=True`，也還原本機 YAML；沒有 CI digest 時可略過更新，直接沿用已就緒版本測試失敗與恢復。原有 `tests/check_rollout.sh` 則保留 Pod `imageID` 擷取方式，供完整叢集測試使用，不取代 CI 來源檢查。

資源補回測試沿用 D21 的暫時 CR：刪除測試 Service 後，比對補回前後的 UID，並確認同一版 CR 最後回報 `Ready=True`。不要刪除正式 Todo Service，也不要覆寫已存在的測試 CR。重啟測試要查看新 Operator Pod 的 resume log，不能只看重啟前留下的 `Ready`。測試結束後，讓 Operator 保持運作，再刪除暫時 CR 並等待受管資源正常清理。

## 執行限制與刪除行為

- Operator 以 `--namespace=todo --standalone` 執行，單副本、`Recreate`；沒有 leader election 或 HA，請勿增加 replicas。
- Namespace `Role` 允許對整個 `todo` 內相應資源操作，不是只授權 `todo-api`，程式的 ownership 檢查也不是 RBAC 隔離。
- 程式透過 ConfigMap 掛載；部署腳本會重啟 Pod 載入程式。initContainer 每次啟動從 PyPI 安裝釘選依賴，仍依賴外部網路與未釘選的 transitive dependencies。正式環境應建置可重現的 Operator image。
- Operator Pod 的 `/healthz` 只證明 Kopf 程序可回應，不是 Todo API 的 `Ready`。
- Kopf timer 使用 finalizer。刪除測試 CR 時要讓 Operator 保持運作，等待正常清理；不要任意移除 finalizers。刪除正式 `todo-api` CR 會連帶 garbage-collect 已接管的原本 Deployment／Service。
- Backstage Dev Template 與 Catalog 都沿用 `todo`，不另外建立環境；`repo-config`、模板的 Git PR 與對應 CR Argo CD Application 仍未串接。

## 本機驗證與叢集測試

```bash
PYTHONPATH=. python -m unittest discover -s tests -p 'test_*.py' -v
bash -n deploy.sh
```

`tests/check_cluster.py` 是會寫入叢集的驗證，不是單元測試：會更新正式 Todo CR 的 image、建立短暫 CR、刪除測試 Service、重啟 Operator，並在結束時還原原始 image。它先拒絕已存在的測試名稱；仍只應在核准的維護時段執行。測試涵蓋 UID 保留、image 失敗、timer 補回、所有權衝突、garbage collection，以及重啟後的新 resume log，避免把重啟前的 `Ready` 當作恢復證據。

其中 digest 與錯誤 image 測試會呼叫 `tests/check_rollout.sh`，使用 shell 擷取 runtime digest 及 patch；腳本用 EXIT trap 還原原 image。`imageID` 沒有可用的 `@sha256:` 格式時會明確失敗，不自行猜測 digest。

```bash
python3 tests/check_cluster.py
```

`tests/test_articles.py` 比對 D20 的 handler 與部署節錄、D21 的資源管理流程、完整的 `read_child`／`check_owner`／`ensure` 函式與錯誤處理節錄，以及 D22 的 `health`、`make_status` 與 handler 呼叫片段。D22 另檢查 conditions 表、回報 generation 與 schema，並確認正文只保留一個狀態查詢指令。它也檢查操作指令、shell 語法，並保留 D20／D22 不超過 150 行的限制；D21 展開函式教學，不再套用這個行數限制。三篇文章均不使用折疊區塊。文章只展示本日相關的函式、關鍵片段與觀察方式，不提供從零安裝完整 Operator 的全部檔案，也不依賴未公開的 repository 連結；來源行為仍由其他單元測試驗證。

若需要重跑事件與資源管理兩個中間階段，可執行下列叢集測試。它會切換 Operator 版本，以短暫 CR 檢查 create／spec update／resume、`ResourcesApplied`、Service 補回及 owner 衝突，最後恢復完整 Operator；期間不修改正式 Todo CR 的 spec，但會短暫停用健康觀察：

```bash
python3 tests/check_stages_cluster.py
```
