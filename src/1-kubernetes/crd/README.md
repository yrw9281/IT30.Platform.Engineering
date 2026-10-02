# Microservice 合約範例

`microservice-crd.yaml` 是 `Microservice` 的唯一 CRD 定義，版本為 `platform.example.io/v1alpha1`，範圍為 Namespace。輸入仍只有 `spec.image` 與 `spec.port`，沒有 `env`。目前的 schema 已包含 Day 22 使用的 `status.conditions`；處理 CR 的程式與執行環境放在 [Operator 目錄](../../4-idp/operator/README.md)。

Day 05／Day 18 的歷史合約只有初版 `status`，根層也沒有要求 `spec` 必填。目前補上 `required: [spec]`，避免移除整個 `spec` 時繞過 `image`／`port` 的必填檢查。`conditions` 是 Day 22 的擴充，不代表 Day 20 observer 會檢查健康：Day 20 只寫 `Accepted`，Day 21 寫 `ResourcesApplied`／`Failed`，Day 22 才寫 `Ready`／`Stalled` conditions。

| 檔案 | 用途 |
| --- | --- |
| [microservice-crd.yaml](microservice-crd.yaml) | 完整資源型別與 schema |
| [todo-api.yaml](todo-api.yaml) | `todo` Namespace 的合法輸入，使用 tag 與 port `8080` |
| [web.yaml](web.yaml) | 僅供 schema 檢查；Web image 不符合此 Operator 的 Todo API probes，不可當作可運作的部署範例 |
| [invalid-todo-api.yaml](invalid-todo-api.yaml) | 僅供 schema 拒絕測試；port `65536` |

## 檢查完整 CRD 定義

在此目錄執行：

```bash
kubectl apply --dry-run=server -f microservice-crd.yaml
```

這會將 CRD 定義交給 API Server 檢查，但不安裝資源型別，也不能據此宣稱範例 CR 已通過驗證。

## 檢查 CR 輸入

需要已安裝上述 CRD、存在的 `todo` Namespace，以及在該 Namespace 提交 `Microservice` 的權限。先確認前置條件：

```bash
kubectl get crd microservices.platform.example.io
kubectl get namespace todo
```

任一步驟回傳 `NotFound` 或權限錯誤時，先處理前置條件，不要繼續把失敗解讀成 schema 驗證結果。若 CRD 尚未安裝，請管理者在核准的測試環境依完整定義安裝；安裝是實際寫入叢集的操作，不包含在這組 dry-run 檢查內。

合法輸入應通過，且不儲存 CR：

```bash
kubectl apply --server-side --dry-run=server -f todo-api.yaml
```

非法輸入應回傳非零 exit code，並指出 `spec.port` 超過 `65535`：

```bash
kubectl apply --server-side --dry-run=server -f invalid-todo-api.yaml
```

也可複製合法範例，每次只改一個欄位：port `1` 與 `65535` 應通過，`0`、`65536` 或字串 `"8080"` 應拒絕；空 image、保留 `spec` 但移除 `image` 或 `port`、移除整個 `spec` 都應拒絕。這項回歸檢查針對 API 輸入；CRD 的 `minLength: 1` 仍接受空白字串，Operator 會另外拒絕它。

這些是既有 schema 的預期結果。server-side dry-run 不會建立工作負載，也不會驗證 image 能否拉取或服務是否就緒。

## 實際安裝與所有權

以下會寫入叢集，與上面的 dry-run 不同。需管理者核准，並使用已存在的 `todo` Namespace，不建立 `todo-dev`：

```bash
kubectl config current-context
kubectl get namespace todo
kubectl apply -f microservice-crd.yaml
kubectl wait --for=condition=Established crd/microservices.platform.example.io --timeout=60s
kubectl apply -f todo-api.yaml
```

升級既有 CRD 前，先檢查舊 CR 的 `spec` 是否符合新合約；Operator 的 Day 22 部署腳本會檢查所有 Namespace 的既有 CR 輸入。新增 required 欄位不會自動修復已儲存的 CR。

CR 存在不等於工作負載被接管。Day 21／Day 22 只管理 `ownerReferences` 指向目前 CR UID 的資源；同名但未被擁有的 Deployment／Service 會回報所有權衝突，不會自動 adoption。沿用既有 Todo API 時，先依 Operator README 明確執行 adoption，再啟用資源管理。

刪除已接管的 CR 會讓 Kubernetes garbage collection 刪除它擁有的 Deployment／Service，包括原本的 Todo API；不要把刪除正式 CR 當作清理範例的步驟。測試 CR 應在 Operator 運作時刪除，讓 Kopf timer 的 finalizer 正常移除，不要批次清除 finalizers。
