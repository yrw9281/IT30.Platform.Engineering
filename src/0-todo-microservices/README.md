# Todo 微服務

這裡是系列使用的應用程式來源：`Todo.Api` 保存待辦事項，`Todo.Bff` 轉送 API 請求，`WebApp` 提供網頁。API 資料存在程序記憶體中，重啟後會消失，沒有資料庫。

以下指令都從 repository 根目錄執行。

## 在本機啟動

需要 Docker 與 Docker Compose：

```bash
docker compose -f src/0-todo-microservices/docker-compose.yml up --build
```

開啟 `http://localhost:8081`，可新增、完成與刪除待辦事項；BFF 位於 `http://localhost:8080`。Compose 關閉 OTel 匯出，不需要先安裝 Collector。

## 建置 Kubernetes 使用的 image

```bash
docker build -t todo-api:0.1.0 src/0-todo-microservices/Todo.Api
docker build -t todo-bff:0.1.0 src/0-todo-microservices/Todo.Bff
docker build -t todo-web:0.1.0 src/0-todo-microservices/WebApp
```

部署步驟見 [Kubernetes 說明](../1-kubernetes/README.md)。兩個 .NET 8 專案已加入 OpenTelemetry instrumentation，叢集內的 OTLP 設定由部署 manifest 提供。

## CI 與 image 發布

[Day 14](../../doc/zh-tw/D14.md) 的 PR 檢查位於 `.github/workflows/todo-ci.yaml`，對 API 與 BFF 執行 restore、test、build。目前沒有 unit test project，`dotnet test` 成功不代表功能已經過測試。

[Day 15–16](../../doc/zh-tw/D15.md) 的 `.github/workflows/todo-image.yaml` 由 `todo-api-v*` 或 `todo-bff-v*` tag 觸發，只發布對應服務，並輸出 GHCR image digest。它不更新 GitOps 設定，也不直接部署叢集。正式換版應使用 CI 產出的 digest，再透過設定 PR 交付。
