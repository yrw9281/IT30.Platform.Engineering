[English](README.md) | [繁體中文](README-zh-TW.md)

# IT30.Platform.Engineering

這個儲存庫收錄 2026 iThome 鐵人賽系列[「寫完微服務然後呢？走向平台工程的黃金路徑」](https://ithelp.ithome.com.tw/users/20168953/ironman/9797)的程式碼與文章。

系列承接 [IT30.Todo.Microservices](https://github.com/yrw9281/IT30.Todo.Microservices)。前一系列用 .NET 探討 DDD、Clean Architecture 與微服務；這次以簡化的 Todo 應用程式為例，練習 Kubernetes 部署、GitOps，以及用 Backstage 建立內部開發者平台（Internal Developer Platform，IDP）。

## 專案介紹

範例涵蓋：

- Kubernetes 資源、Helm、Kustomize 與自訂資源定義（CRD）。
- Argo CD 與 ApplicationSet 的 GitOps 同步。
- 使用 OpenTelemetry 與 Grafana 查詢指標、日誌及分散式追蹤。
- 使用 GitHub Actions 建置應用程式，將容器 image 發布到 GitHub Container Registry（GHCR）。
- Backstage Catalog、Software Templates 與 Kubernetes 資源查詢。
- 使用 Python／Kopf 撰寫 Operator，將 `Microservice` 資源轉成 Deployment 與 Service，並回報新版就緒狀態。
- Kubernetes RBAC 與 OPA Gatekeeper 資源設定政策。

範例包含網頁前端、以 .NET 8／ASP.NET Core 撰寫的 Backend for Frontend（BFF）與 Todo API。資料儲存在記憶體中，沒有沿用前一系列的資料庫與訊息佇列。

## 架構

![從 Backstage 經 Git、Argo CD 到 Kubernetes 的交付流程](doc/assets/day-17-backstage-to-kubernetes-flow.png)

Backstage 模板會建立 Todo API image 換版的 GitHub Pull Request。審查並合併後，Argo CD 從 Git 同步 `Microservice` 資源，Operator 再建立或更新 Deployment 與 Service，回報目前資源 generation 的健康狀態。Backstage 提供服務目錄與 Kubernetes 資源查詢，不直接部署工作負載，也不記錄完整的交付歷史。

應用程式的請求路徑是 `Browser → Ingress → BFF → Todo API`。API 與 BFF 將遙測資料送到 OpenTelemetry Collector，由 Prometheus、Loki、Tempo 分別儲存指標、日誌與追蹤，再透過 Grafana 查詢。

![Todo 網頁](doc/assets/day-30-todo-web.png)

![Grafana 的 Todo service overview 儀表板](doc/assets/day-30-grafana-service-overview.png)

## 開始使用

### 在本機啟動 Todo

安裝 Git、Docker 與 Docker Compose 後，執行：

```bash
git clone https://github.com/yrw9281/IT30.Platform.Engineering.git
cd IT30.Platform.Engineering
docker compose -f src/0-todo-microservices/docker-compose.yml up -d --build
docker compose -f src/0-todo-microservices/docker-compose.yml ps
```

開啟 <http://localhost:8081>，即可新增、完成與刪除待辦事項。BFF 位於 <http://localhost:8080>。這份 Compose 設定關閉 OpenTelemetry 匯出，不會安裝平台元件。

停止應用程式：

```bash
docker compose -f src/0-todo-microservices/docker-compose.yml down
```

Todo 資料存在 API 程序的記憶體中，程序重啟後就會消失。

### 在 Kubernetes 部署平台

請準備乾淨、可連線的 Kubernetes 叢集，依照[完整平台安裝指南](src/final/README-zh-TW.md)部署。內容包含應用程式、Argo CD、Ingress Controller、可觀測性元件、Operator、Backstage 與 Gatekeeper。

你需要具管理者權限的 kubeconfig，以及支援 Kustomize 的 `kubectl`。請依指南安裝並設定憑證。Argo CD 讀取遠端 Git，同步前必須先推送本機變更；使用 fork 時，也要修改儲存庫與 image 的參照。

各份指南頂端皆可切換英文與繁體中文。編號章節範例與 `src/final/` 請擇一使用，勿同時套用到同一組資源。

## 儲存庫結構

| 路徑 | 內容 |
| --- | --- |
| [`doc/en/`](doc/en/) | 30 篇英文文章 |
| [`doc/zh-tw/`](doc/zh-tw/) | 30 篇繁體中文文章 |
| [`doc/assets/`](doc/assets/) | 架構圖與操作截圖 |
| [`src/0-todo-microservices/`](src/0-todo-microservices/README-zh-TW.md) | Todo API、BFF、網頁前端與 Docker Compose |
| [`src/1-kubernetes/`](src/1-kubernetes/README-zh-TW.md) | Kubernetes manifests、Kustomize 與 CRD |
| [`src/2-gitops/`](src/2-gitops/README-zh-TW.md) | Argo CD Application 與自訂健康檢查 |
| [`src/3-observability/`](src/3-observability/README-zh-TW.md) | OpenTelemetry Collector 與 Grafana 觀測元件 |
| [`src/4-idp/`](src/4-idp/README-zh-TW.md) | Backstage、模板、Operator 與 RBAC |
| [`src/5-config/`](src/5-config/README-zh-TW.md) | 章節範例使用的 Todo API GitOps 設定 |
| [`src/6-policy/`](src/6-policy/README-zh-TW.md) | Gatekeeper 政策範例 |
| [`src/final/`](src/final/README-zh-TW.md) | 適用乾淨叢集的獨立平台安裝設定 |
| [`.github/workflows/`](.github/workflows/) | 章節使用的 CI 與 image 發布工作流程 |
| [`outline.md`](outline.md) | 系列大綱 |

## 系列文章

可以從 [Day 01：微服務寫完後，為什麼還需要平台工程](doc/zh-tw/D01.md)開始，或依主題閱讀：

| 天數 | 主題 | 起始文章 |
| --- | --- | --- |
| 01–05 | 序言與 Kubernetes 部署基礎 | [Day 01](doc/zh-tw/D01.md) |
| 06–08 | Argo CD 與 GitOps | [Day 06](doc/zh-tw/D06.md) |
| 09–13 | 可觀測性 | [Day 09](doc/zh-tw/D09.md) |
| 14–16 | CI 與 GitOps 的交接 | [Day 14](doc/zh-tw/D14.md) |
| 17–26 | Backstage 與 Microservice Operator | [Day 17](doc/zh-tw/D17.md) |
| 27–29 | API 權限與資源政策 | [Day 27](doc/zh-tw/D27.md) |
| 30 | Todo API 換版操作與系列回顧 | [Day 30](doc/zh-tw/D30.md) |

前一系列的應用架構實作可參考 [IT30.Todo.Microservices](https://github.com/yrw9281/IT30.Todo.Microservices) 與 [2024 iThome 系列文章](https://ithelp.ithome.com.tw/users/20168953/ironman/7881)。

## 示範範圍與限制

請在受控的學習環境使用這些範例：

- Todo API 使用單副本的記憶體儲存；完整平台範例的可觀測性資料與 Backstage SQLite 也使用暫存儲存空間。
- Backstage 使用 Guest 登入與 allow-all permission policy，入口應限制在本機 loopback。正式環境需要身分驗證、授權、TLS 與持久化儲存。
- Gatekeeper 政策只涵蓋部分資源，並採用不同執行模式。安裝政策不代表已完成租戶隔離或供應鏈驗證。
- Git 同步、目前 generation 的新版就緒狀態與應用程式功能需要分別確認。渲染 manifest 或合併 PR，都不能單獨證明部署成功。
- 完整平台範例保留固定版本的 ingress-nginx 快照供教學使用。該專案已於 2026 年 3 月退休，新的正式平台應選擇仍受維護的替代方案。

元件版本、憑證與部署限制，請見[安裝指南的版本與限制](src/final/README-zh-TW.md#版本與限制)。

## 感謝

謝謝 iThome 舉辦鐵人賽，也謝謝一路跟著閱讀與實作的讀者。
