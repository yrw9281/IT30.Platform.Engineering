# iThome 2026 鐵人賽

## Theme

Title: **微服務寫完後，怎麼用平台工程改善交付流程**
Description: 從 K8s、GitOps 到 Observability，建立 Internal Developer Platform（IDP），讓服務能部署、回報狀態並持續維護。

## Outline

### 第零階段：序言

我有一前篇系列文： [Repo](https://github.com/yrw9281/IT30.Todo.Microservices)

```plaintext
DDD? Clean Architecture? Microservices? 帶你用.NET實作打造一個現代化微服務！ 系列
打造微服務非常複雜，其中許多技術都值得深入探討。但我想做點不一樣的，從系統架構層級剖析整個現代化微服務，並透過簡單的案例帶你一步步實作。
```

這是上一系列的[結尾文](https://github.com/yrw9281/IT30.Todo.Microservices/blob/main/doc/pages/D30/D30.md)，可承接。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 01** | **微服務寫完後：為什麼還需要平台工程** | 介紹平台工程的核心價值與後續階段，可從上一系列的微服務實作延伸。 |

### 第一階段：Kubernetes 與部署基礎（Day 01 - Day 05）

先理解 K8s 的運作方式，以及部署一個服務需要哪些資源；後續才會用到自訂資源（CRD）。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 02** | Kubernetes 為什麼能維持期望狀態：宣告式 API 與 Reconcile Loop | 說明「期望狀態」與「實際狀態」如何收斂，並理解後續 GitOps 與 Operator 都會用到的控制器模式。 |
| **Day 03** | 部署一個服務時，Deployment、Service 與 Ingress 各做什麼 | 以實際微服務為例，拆解服務上線需要組合哪些基礎 YAML 資源。 |
| **Day 04** | Helm 與 Kustomize：怎麼管理不同環境的設定 | 處理靜態 YAML 的限制，介紹如何為 Dev、Staging 與 Prod 進行參數化與渲染。 |
| **Day 05** | CRD 是什麼：讓 Kubernetes 認識自訂資源 | 說明如何擴充 Kubernetes API，讓它認識非原生資源，並為後續的專屬平台合約做準備。 |

### 第二階段：GitOps 部署（Day 06 - Day 08）

用 Git 保存基礎設施與部署狀態，並建立自動同步機制。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 06** | GitOps 怎麼用 Git 管理部署狀態 | 對比 Push-based CI 腳本與 Pull-based 架構，說明權限隔離與災難還原的差異。 |
| **Day 07** | 用 Argo CD 將 Git 的 YAML 同步到 Kubernetes | 部署 Argo CD，解析 `Application` 資源，並將 Git 儲存庫中的 YAML 變更自動同步至叢集。 |
| **Day 08** | 用 Argo CD ApplicationSet 管理多個服務與環境 | 運用 Git 與 List Generator 產生 `Application`，減少微服務與多叢集環境中的手動 YAML 維護。 |

### 第三階段：可觀測性（Day 09 - Day 13）

服務上線後，需要能查看狀態、定位問題，並使用一致的遙測資料格式。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 09** | Metrics、Logs、Traces：可觀測性怎麼用 | 釐清 Monitoring（警報）與 Observability（探究未知）的差異，以及三種遙測資料的關係。 |
| **Day 10** | OpenTelemetry 的資料格式與元件 | 說明 OTel API、SDK 規範，以及跨語言、跨工具的遙測資料如何標準化。 |
| **Day 11** | 部署與設定 OpenTelemetry Collector | 實作 Receiver、Processor、Exporter 管道，處理資料的過濾、脫敏、批次與轉發。 |
| **Day 12** | 用 Distributed Tracing 找出微服務的瓶頸 | 實作跨服務的 Trace Context 注入與傳遞，排查 API 呼叫鏈路與資料庫慢查詢。 |
| **Day 13** | 在 Grafana 查看 Prometheus、Loki 與 Trace 資料 | 串聯 Trace-to-Metrics 與 Trace-to-Logs，讓開發團隊能查看服務健康狀態。 |

### 第四階段：CI 與 GitOps 的交界（Day 14 - Day 16）

釐清開發端與 GitOps 端如何交接，並分開 CI 與 CD 的責任。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 14** | 用 GitHub Actions 建立 CI 工作流程 | 設計具備快取與自動化單元測試的 CI Workflow，確認程式碼品質。 |
| **Day 15** | 在 CI 建置 Docker Image，並管理 Tag | 在 CI 中自動建置容器，並比較 Git SHA 與 Semantic Versioning 的 Image Tag 策略。 |
| **Day 16** | CI 完成後，怎麼把 Image 更新交給 GitOps | 釐清 CI（Build & Test）與 CD（Deploy）的分界，並說明 CI 如何更新 GitOps 設定儲存庫。 |

### 第五階段：用 Backstage 串起 IDP 的交付路徑（Day 17 - Day 26）

以 Backstage 作為開發者入口，透過 Git review 與 Argo CD 交付 `Microservice` 資源；Operator 管理工作負載，再讓開發者查詢部署狀態。Dev 沿用既有的 `todo` Namespace，模板、Operator 與 Catalog 都以同一個環境為目標，不另外建立常駐環境。Backstage 不取代 GitOps controller 或 Operator，也不預設提供逐筆交付事件歷史。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 17** | 從 Backstage 到 Kubernetes：IDP 的控制流程 | 用 Todo 服務解釋 IDP 與 Backstage 的分工：開發者透過入口提出需求，經 Git PR、Argo CD、`Microservice` 與 Operator 部署，再查看目前狀態；標明尚未串接的環節。 |
| **Day 18** | 設計 `Microservice` CRD：把 Kubernetes 設定收進平台合約 | 以現有 CRD 的 Image、Port 合約為起點，規劃環境變數與狀態欄位，區分已存在的 schema 與尚未實作的擴充。 |
| **Day 19** | Operator 與 Kopf：從服務合約到控制迴路 | 合併事件處理與資源合約的概念，以 Todo API 說明 Kopf handler、重試、所有權、平台預設與狀態回報的分工，銜接 CRD 與實作。 |
| **Day 20** | 用 Kopf 接收 `Microservice` 事件並部署 Operator | 在既有 `todo` Namespace 部署單一副本的 Kopf Operator，實作 create、spec update 與 resume handler，以 log 和 `Accepted` 狀態確認事件處理；此步尚不管理工作負載。 |
| **Day 21** | 讓 Operator 管理 Todo API 的 Deployment 與 Service | 將 CR 轉成工作負載與 OTel 預設，操作前確認既有同名 Deployment／Service 已移除，由 Operator 重新建立 Todo API，實作建立／更新、所有權檢查與定期補回；`ResourcesApplied` 只代表設定已提交，不宣稱健康。 |
| **Day 22** | 讓 Operator 回報新版是否就緒 | 擴充 CRD conditions，實作 rollout、Pod 與 Service endpoint 的健康判斷、generation 防護與 Ready／Stalled 回報；驗證 digest 更新、錯誤 image、資源補回和重啟恢復。 |
| **Day 23** | 用 Backstage Software Templates 收集服務設定 | 介紹 Software Catalog 與 Software Templates 的不同責任，將開發者輸入轉成受控的 `Microservice` 設定；模板沿用既有 `todo` Namespace，Git PR 與 CR GitOps 仍未串接。 |
| **Day 24** | 用 Backstage 提出 GitOps 設定 Pull Request | 說明模板如何提出 Git 變更，並在設定儲存庫執行獨立的 YAML／CRD schema 檢查與審查；不把 PR 建立誤認為部署完成。 |
| **Day 25** | 讓 Argo CD 判斷 `Microservice` 是否健康 | 以 Operator 已回報的 conditions 和 generation 設計自訂 Health Check，區分 Synced、Progressing、Healthy 與 Degraded；Argo CD 整合仍待驗證。 |
| **Day 26** | 在 Backstage 查看服務與 Kubernetes 部署狀態 | 說明 Catalog 服務身分與 Kubernetes plugin 的資源關聯、可查看的現況和無法自動得到的 Git review／交付事件時間線。 |

### 第六階段：API 權限與資源政策（Day 27 - Day 29）

隨著自動化與自服務程度提高，先介紹 Namespace／RBAC 的 API 權限，再用兩篇概念文說明 Gatekeeper 的政策機制與交付整合。沿用 Todo API 的交付情境，區分誰能提交資源、設定是否符合規則，以及遭拒後如何回饋。既有 Operator／Backstage 只有有限的 RBAC，Gatekeeper 政策仍未實作或取得叢集測試結果，不宣稱完整團隊隔離。系列範圍調整為交付權限與資源政策，不再安排 Day 01 原先預告的服務間流量與 mTLS 教學；Day 01 保留已發布內容。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 27** | Kubernetes RBAC 與 Namespace 能隔離什麼 | 以 Todo API、Operator、Argo CD 與 Backstage 的不同身分，簡介 Namespace、ServiceAccount、Role／RoleBinding 與最小權限；區分 API 授權、網路隔離和資源預算。 |
| **Day 28** | Gatekeeper 如何檢查 Kubernetes 資源設定 | 說明 Admission、OPA 與 Gatekeeper 的分工，以及 ConstraintTemplate／Constraint 的邏輯、參數與範圍；以 privileged 情境解釋預期允許／拒絕、工作負載與 Pod 的檢查邊界，不提供未實作的 Rego 或拒絕結果。 |
| **Day 29** | 把 Gatekeeper 政策放進平台交付流程 | 延伸 limits、image 來源與 digest，說明 audit、dryrun／warn／deny 與例外的檢查範圍；沿著 Argo CD 同步 CR、Operator 建立工作負載的路徑定位政策拒絕與回饋缺口，不宣稱整合已完成。 |

### 第七階段：成果展示與回顧（Day 30）

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 30** | **平台工程系列回顧** | 依第一至第六階段的順序，以短段落與截圖回顧 Kubernetes 部署、GitOps、可觀測性、CI 交接、Backstage／Operator 與 API 權限／資源政策，再保留思考問題、感謝與 GitHub Repo 連結。沿用現有截圖，缺少畫面留下 TODO，簡短交代端到端交付與政策整合仍待驗證，不展開成果矩陣或演進計畫。 |

## 視覺素材規劃

圖片、架構圖、流程圖與操作截圖由使用者另行繪製或截取，並存放於 `assets/`。撰寫對應文章時，若素材尚未提供，請在正文預定圖片位置加入 `<!-- TODO(assets): 補上 ... -->`，不可建立假圖片連結。

| Day | 建議素材 | 應呈現的內容 |
| --- | --- | --- |
| 01 | 系列全貌與最終平台藍圖 | 各階段學習路徑，以及 Developer、Git、CI、GitOps、Kubernetes、Observability、Security 與 IDP 的最終關係。 |
| 02 | Kubernetes Reconcile Loop | 使用者宣告期望狀態、API Server、Controller、實際狀態與持續收斂的方向。 |
| 03 | 應用交付與流量骨架 | 外部請求經 Ingress、Service 至 Deployment／Pod 的流向，以及各資源責任。 |
| 04 | Helm 與 Kustomize 配置流程 | Chart Values 與 Base/Overlay 如何產出不同環境的 Kubernetes manifests。 |
| 05 | CRD 擴充 Kubernetes API | CRD、Custom Resource、Controller／Operator 與原生資源之間的關係。 |
| 06 | Push-based CI 與 Pull-based GitOps 對照 | 兩種部署模式的變更方向、權限邊界與 Git 作為單一真實來源的位置。 |
| 07 | Argo CD 架構與同步流程 | Git repository、Application、Argo CD、Kubernetes cluster 與 sync／health 狀態。 |
| 08 | ApplicationSet 生成流程 | Git/List Generator 輸入、template，以及產生多環境或多叢集 Application 的結果。 |
| 09 | Metrics、Logs、Traces 黃金三角 | 同一服務與請求如何以三種 telemetry signal 互相定位。 |
| 10 | OpenTelemetry 全貌 | Application SDK、OTel Collector、telemetry backend 與標準化資料流。 |
| 11 | OpenTelemetry Collector pipeline | Receiver、Processor、Exporter 的處理順序，以及過濾、脫敏、批次與轉送。 |
| 12 | 跨服務 Trace Context | 入口請求、服務呼叫、資料庫 span 與 trace ID 的傳遞路徑。 |
| 13 | Observability 平台整合 | Prometheus、Loki、Tracing backend、Grafana，以及 trace-to-logs／metrics 的跳轉關係。 |
| 14 | CI Pipeline | Commit/PR、lint、test、build、artifact 或 image 與失敗回饋。 |
| 15 | Container Image 建置與版本流 | Source commit、tag 策略、GHCR 與 immutable image digest。 |
| 16 | CI 與 GitOps 職責交界 | CI 更新 image reference、PR/Git review、Argo CD 拉取變更及部署的完整流程。 |
| 17 | IDP 黃金路徑總架構 | Backstage 入口、Git PR、Argo CD、`Microservice` CR、Operator、Kubernetes 與查詢狀態的方向；標示未實作邊界。 |
| 18 | `Microservice` CRD 合約邊界 | 開發者可填的簡化 spec、平台隱藏的 Kubernetes 細節與 status 回報。 |
| 19 | Operator 控制迴路與責任 | CR 事件或定期檢查、Kopf handler、資源合約與狀態回報的關係；先用 Mermaid 說明設計。 |
| 20 | Kopf 事件處理流程 | create、spec update、resume 到 log 與 `Accepted` 的方向；補上 Operator Pod 與 CR 狀態畫面。 |
| 21 | Operator 資源展開與所有權 | CR、Deployment、Service、Pod 與 OTel 的關係；標示既有資源接管與同名衝突的邊界。 |
| 22 | 新版 rollout 與健康回報 | CR／Deployment generation、Pod 與 EndpointSlice 的觀察流程，以及錯誤 image 的 Ready／Stalled 畫面。 |
| 23 | Backstage 服務輸入流程 | Software Catalog 的服務身分、Software Template 的參數、產生 `Microservice` YAML 與輸入限制。 |
| 24 | GitOps Pull Request 防呆流程 | Backstage 模板建立 branch/PR、設定儲存庫執行 schema validation、review/merge 與錯誤回饋。 |
| 25 | Argo CD Health 判斷流程 | 自訂 health check 如何從 CRD status 判斷服務的 Progressing、Healthy 或 Degraded。 |
| 26 | 服務與部署狀態查詢 | Backstage Catalog 與 Kubernetes plugin 如何關聯資源現況；區分已運作的查詢設定與未實作的完整事件時間線。 |
| 27 | Namespace 與 RBAC 權限邊界 | 工作負載、Operator、Argo CD 與 Backstage 查詢身分的不同權限；完整團隊隔離仍為設計。 |
| 28 | Gatekeeper Admission 與資源檢查邊界 | API 授權、Template、Constraint、admission 與拒絕回饋的關係，標示 CR、Deployment 與 Pod 為不同 API 請求；不使用實測拒絕畫面。 |
| 29 | 政策導入與交付錯誤回饋 | audit 盤點、執行模式與修正流程，以及 Argo CD 提交 CR、Operator 提交 Deployment、ReplicaSet 建立 Pod 各層的拒絕位置；標示尚未完成的回饋整合。 |
| 30 | 各階段成果截圖 | 依系列階段安排畫面，沿用 Grafana dashboard／Trace、GHCR image、Operator Ready 與 Backstage PR 截圖；待補 Todo 功能、Argo CD 同步／健康與 Backstage 部署查詢畫面。Gatekeeper 允許／拒絕截圖須待叢集驗證後補上，不另製成果地圖，也不以各環節的截圖宣稱已完成端到端交付。 |