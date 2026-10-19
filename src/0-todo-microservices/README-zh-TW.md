[English](README.md) | [繁體中文](README-zh-TW.md)

# Todo 微服務

`Todo.Api` 保存待辦事項，`Todo.Bff` 轉送 API 請求，`WebApp` 提供網頁。API 沒有資料庫，待辦事項存在程序記憶體中，重啟後就會消失。

以下指令皆從儲存庫根目錄執行。

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

部署步驟見 [Kubernetes 說明](../1-kubernetes/README-zh-TW.md)。兩個 .NET 8 專案已加入 OpenTelemetry，OTLP 連線設定由部署 manifest 提供。

## CI 與 image 發布

[Day 14](../../doc/zh-tw/D14.md) 的 `.github/workflows/todo-ci.yaml` 在 PR 中對 API 與 BFF 執行 restore、test、build。目前沒有單元測試專案，`dotnet test` 即使成功，也沒有測試應用程式功能。

[Day 15–16](../../doc/zh-tw/D15.md) 的 `.github/workflows/todo-image.yaml` 由 `todo-api-v*` 或 `todo-bff-v*` tag 觸發，發布對應服務並輸出 GHCR image digest。換版時，將該 digest 放進設定 PR；這個 workflow 不更新 GitOps 設定，也不直接部署叢集。
