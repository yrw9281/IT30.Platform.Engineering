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

### 第五階段：用 Backstage 串起 IDP 的交付路徑（Day 17 - Day 24）

以 Backstage 作為開發者入口，透過 Git review 與 Argo CD 交付 `Microservice` 資源；Operator 管理工作負載，再讓開發者查詢部署狀態。Backstage 不取代 GitOps controller 或 Operator，也不預設提供逐筆交付事件歷史。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 17** | 從 Backstage 到 Kubernetes：IDP 的控制流程 | 用 Todo 服務解釋 IDP 與 Backstage 的分工：開發者透過入口提出需求，經 Git PR、Argo CD、`Microservice` 與 Operator 部署，再查看目前狀態；標明尚未串接的環節。 |
| **Day 18** | 設計 `Microservice` CRD：把 Kubernetes 設定收進平台合約 | 以現有 CRD 的 Image、Port 合約為起點，規劃環境變數與狀態欄位，區分已存在的 schema 與尚未實作的擴充。 |
| **Day 19** | Operator 模式與 Kopf：怎麼處理 CRD 事件 | 說明為何選擇 Python 框架 Kopf，以及 create、spec 變更、child 資源漂移和狀態回報如何觸發處理。 |
| **Day 20** | 從 `Microservice` 到 Deployment：Operator 應建立哪些資源 | 對照現有 Todo manifest，說明 Operator 將 `Microservice` 轉成 Deployment、Service 與 OTel 預設所需的欄位合約與驗證條件；尚無 Operator 時不宣稱已產生資源。 |
| **Day 21** | 用 Backstage Software Templates 收集服務設定 | 介紹 Software Catalog 與 Software Templates 的不同責任，將開發者輸入轉成受控的 `Microservice` 設定；以來源檔與可驗證結果區分範例和規劃。 |
| **Day 22** | 用 Backstage 提出 GitOps 設定 Pull Request | 說明模板如何提出 Git 變更，並在設定儲存庫執行獨立的 YAML／CRD schema 檢查與審查；不把 PR 建立誤認為部署完成。 |
| **Day 23** | 讓 Argo CD 判斷 `Microservice` 是否健康 | 以 `Microservice.status.conditions` 和 generation 設計自訂 Health Check，區分 Synced、Progressing、Healthy 與 Degraded，不依賴自製狀態資料庫。 |
| **Day 24** | 在 Backstage 查看服務與 Kubernetes 部署狀態 | 說明 Catalog 服務身分與 Kubernetes plugin 的資源關聯、可查看的現況和無法自動得到的 Git review／交付事件時間線。 |

### 第六階段：安全與流量策略（Day 25 - Day 29）

隨著自動化與自服務程度提高，用權限、Policy 與流量控制理解人為失誤與越權存取的邊界。本階段以概念、決策條件與驗收情境為主，不宣稱 RBAC、Gatekeeper 或 Istio 已在本平台安裝驗證。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 25** | Kubernetes RBAC 與 Namespace 能隔離什麼 | 用 Todo 服務情境說明 Namespace、ServiceAccount、Role／RoleBinding 的權限邊界及預期允許／拒絕，區分概念與已驗證設定。 |
| **Day 26** | Policy as Code：OPA Gatekeeper 怎麼檢查資源 | 說明 Admission、ConstraintTemplate／Constraint、audit 與 dryrun／deny 的不同角色，以及未安裝時的限制。 |
| **Day 27** | 用 Gatekeeper 辨識高風險工作負載設定 | 分析 resource limits、privileged container 與 image 來源的違規情境與修正方向，不宣稱已實作 Rego 或測得拒絕結果。 |
| **Day 28** | Istio Sidecar 如何改變微服務流量 | 說明 Sidecar 與控制平面如何處理流量及導入成本，不把 mesh 描述成已安裝的基礎設施。 |
| **Day 29** | mTLS 與 AuthorizationPolicy 各擋什麼 | 比較工作負載身分、傳輸加密及服務間授權，討論允許／拒絕情境和導入限制，不把政策規劃說成已生效。 |

### 第七階段：回顧（Day 30）

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 30** | **30 篇後：把微服務交付流程變成平台** | 區分既有 Kubernetes、可觀測性、CI 範例與尚未串接的 IDP／安全／Service Mesh 設計，整理結合 AI 輔助開發時可繼續探索的方向。 |

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
| 19 | Operator Reconcile 流程 | Custom Resource event、Kopf handler、資源比對與 status 更新。 |
| 20 | Operator 資源展開結果 | 一個 `Microservice` 如何展開為 Deployment、Service、OTel 設定與運行狀態。 |
| 21 | Backstage 服務輸入流程 | Software Catalog 的服務身分、Software Template 的參數、產生 `Microservice` YAML 與輸入限制。 |
| 22 | GitOps Pull Request 防呆流程 | Backstage 模板建立 branch/PR、設定儲存庫執行 schema validation、review/merge 與錯誤回饋。 |
| 23 | Argo CD Health 判斷流程 | 自訂 health check 如何從 CRD status 判斷服務的 Progressing、Healthy 或 Degraded。 |
| 24 | 服務與部署狀態查詢 | Backstage Catalog 與 Kubernetes plugin 如何關聯服務、Deployment/Pod 的現況；區分可查詢狀態與未實作的完整事件時間線。 |
| 25 | Namespace 多租戶與 RBAC 邊界圖 | Team Namespace、ServiceAccount、Role、RoleBinding 及跨 Namespace 存取的預期拒絕；標示僅為設計。 |
| 26 | OPA Gatekeeper Admission 流程圖 | API request、Gatekeeper、ConstraintTemplate、Constraint、audit 與預期 allow/deny 分支；不使用實測截圖。 |
| 27 | Policy 風險情境對照圖 | 缺少 resource limits、privileged container、非核准 image 三種輸入與預期修正，不假造拒絕輸出。 |
| 28 | Istio Sidecar 流量圖 | Ingress、Envoy sidecar、服務流量與平台控制面的方向及責任；標明未導入。 |
| 29 | mTLS 與 AuthorizationPolicy 邊界圖 | 雙向 TLS、workload 身分與白名單授權的概念流向；標明尚無測試結果。 |
| 30 | 完成版平台演進地圖 | Day 01 平台藍圖的完成版本，並標示可持續演進的 AI、成本、可靠性與開發者體驗方向。 |