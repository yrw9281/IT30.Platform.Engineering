# Microservice 合約範例

`microservice-crd.yaml` 定義 Namespace 範圍的 `Microservice`，版本為 `platform.example.io/v1alpha1`。目前只有 `spec.image`、`spec.port` 與初版 `status`，沒有 `env`、`conditions` 或處理這個資源的 Operator。

| 檔案 | 用途 |
| --- | --- |
| [microservice-crd.yaml](microservice-crd.yaml) | 完整資源型別與 schema |
| [todo-api.yaml](todo-api.yaml) | `todo` Namespace 的合法輸入，使用 tag 與 port `8080` |
| [web.yaml](web.yaml) | 相同合約的 Web 服務範例 |
| [invalid-todo-api.yaml](invalid-todo-api.yaml) | port `65536`，預期被 schema 拒絕 |

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

也可複製合法範例，每次只改一個欄位：port `1` 與 `65535` 應通過，`0`、`65536` 或字串 `"8080"` 應拒絕；空 image、保留 `spec` 但移除 `image` 或 `port` 也應拒絕。根層目前沒有要求 `spec` 必填，因此移除整個 `spec` 不會因這條 schema 規則被拒絕。

這些是既有 schema 的預期結果。server-side dry-run 不會建立工作負載，也不會驗證 image 能否拉取或服務是否就緒。
