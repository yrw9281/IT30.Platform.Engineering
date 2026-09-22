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

### 第三階段：可觀測性（Day 10 - Day 14）

服務上線後，需要能查看狀態、定位問題，並使用一致的遙測資料格式。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 10** | Metrics、Logs、Traces：可觀測性怎麼用 | 釐清 Monitoring（警報）與 Observability（探究未知）的差異，以及三種遙測資料的關係。 |
| **Day 11** | OpenTelemetry 的資料格式與元件 | 說明 OTel API、SDK 規範，以及跨語言、跨工具的遙測資料如何標準化。 |
| **Day 12** | 部署與設定 OpenTelemetry Collector | 實作 Receiver、Processor、Exporter 管道，處理資料的過濾、脫敏、批次與轉發。 |
| **Day 13** | 用 Distributed Tracing 找出微服務的瓶頸 | 實作跨服務的 Trace Context 注入與傳遞，排查 API 呼叫鏈路與資料庫慢查詢。 |
| **Day 14** | 在 Grafana 查看 Prometheus、Loki 與 Trace 資料 | 串聯 Trace-to-Metrics 與 Trace-to-Logs，讓開發團隊能查看服務健康狀態。 |

### 第四階段：CI 與 GitOps 的交界（Day 15 - Day 17）

釐清開發端與 GitOps 端如何交接，並分開 CI 與 CD 的責任。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 15** | 用 GitHub Actions 建立 CI 工作流程 | 設計具備快取與自動化單元測試的 CI Workflow，確認程式碼品質。 |
| **Day 16** | 在 CI 建置 Docker Image，並管理 Tag | 在 CI 中自動建置容器，並比較 Git SHA 與 Semantic Versioning 的 Image Tag 策略。 |
| **Day 17** | CI 完成後，怎麼把 Image 更新交給 GitOps | 釐清 CI（Build & Test）與 CD（Deploy）的分界，並說明 CI 如何更新 GitOps 設定儲存庫。 |

### 第五階段：打造 IDP（Day 18 - Day 25）

從 Web UI 建立資源、交給 Kubernetes 部署，再把狀態回傳到平台。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 18** | 從 Portal 到 Kubernetes：IDP 的控制流程 | 說明 IDP Portal 產生 YAML、寫入 Git、由 Argo CD 部署、經 Operator 展開資源，再由 Webhook 更新資料庫的流程。 |
| **Day 19** | 設計 `Microservice` CRD：把 Kubernetes 設定收進平台合約 | 隱藏 Kubernetes 底層細節，設計 `Microservice` CRD Schema，只開放 Image、Port、環境變數等核心欄位。 |
| **Day 20** | Operator 模式與 Kopf：怎麼處理 CRD 事件 | 說明平台工程中為何選擇 Python 框架 Kopf，以及它如何攔截 CRD 事件。 |
| **Day 21** | 用 Kopf 將 `Microservice` CRD 建成 Deployment | 撰寫 Python 邏輯：當叢集建立 `Microservice` CRD 時，產生對應的 Deployment、Service 與 OTel 設定。 |
| **Day 22** | IDP API：從表單產生 YAML 並寫入 GitOps 儲存庫 | 實作 Backend API，接收前端表單、渲染 `Microservice` CRD YAML，並透過 Git API 寫入設定儲存庫。 |
| **Day 23** | IDP API：用 Pull Request 與 Schema 檢查 YAML | 在自動提交前導入 Pull Request 與 YAML Schema 靜態檢查，避免不符合格式的資料流入。 |
| **Day 24** | 設定 Argo CD Health Check 與 Notification | 設定 Argo CD 自訂 Health 狀態，根據自製 CRD 底下的 Pod 啟動狀態判斷服務是否健康。 |
| **Day 25** | 用 Webhook 把 Kubernetes 狀態回傳 IDP 資料庫 | 實作 Argo CD Notification Webhook；服務從 `Deploying` 變為 `Healthy` 時，同步更新 IDP 資料庫。 |

### 第六階段：安全與流量策略（Day 26 - Day 30）

隨著自動化與自服務程度提高，用權限、Policy 與流量控制降低人為失誤與越權存取。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 26** | 用 Kubernetes RBAC 與 Namespace 隔離團隊權限 | 讓 IDP 產出的服務在同一個 Kubernetes 叢集中受到權限邊界限制，避免跨團隊越權。 |
| **Day 27** | Policy as Code：OPA Gatekeeper 怎麼檢查資源 | 介紹 Open Policy Agent（OPA），並說明 Admission Controller 為何能在資源進入叢集前執行安全檢查。 |
| **Day 28** | 用 Rego 阻擋高風險 YAML | 實作規則，要求資源限制、阻擋特權容器，並限制映像檔只能從核准的 GHCR repository 拉取。 |
| **Day 29** | Istio 怎麼管理微服務流量 | 導入 Istio Service Mesh，說明 Sidecar 如何接管微服務進出流量。 |
| **Day 30** | 設定 mTLS 與 AuthorizationPolicy | 實作服務間的自動流量加密與授權策略，限制只有白名單服務能互相通訊。 |

### 第七階段：回顧（Day 31）

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 31** | **30 篇後：把微服務交付流程變成平台** | 回顧從 Kubernetes 到 IDP 與 Service Mesh 的實作，並整理結合 AI 輔助開發時可繼續探索的方向。 |

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
| 10 | Metrics、Logs、Traces 黃金三角 | 同一服務與請求如何以三種 telemetry signal 互相定位。 |
| 11 | OpenTelemetry 全貌 | Application SDK、OTel Collector、telemetry backend 與標準化資料流。 |
| 12 | OpenTelemetry Collector pipeline | Receiver、Processor、Exporter 的處理順序，以及過濾、脫敏、批次與轉送。 |
| 13 | 跨服務 Trace Context | 入口請求、服務呼叫、資料庫 span 與 trace ID 的傳遞路徑。 |
| 14 | Observability 平台整合 | Prometheus、Loki、Tracing backend、Grafana，以及 trace-to-logs／metrics 的跳轉關係。 |
| 15 | CI Pipeline | Commit/PR、lint、test、build、artifact 或 image 與失敗回饋。 |
| 16 | Container Image 建置與版本流 | Source commit、tag 策略、GHCR 與 immutable image digest。 |
| 17 | CI 與 GitOps 職責交界 | CI 更新 image reference、PR/Git review、Argo CD 拉取變更及部署的完整流程。 |
| 18 | IDP 黃金路徑總架構 | Portal、API、Git、Argo CD、`Microservice` CRD、Operator、Kubernetes、webhook 與資料庫的控制與回饋流。 |
| 19 | `Microservice` CRD 合約邊界 | 開發者可填的簡化 spec、平台隱藏的 Kubernetes 細節與 status 回報。 |
| 20 | Operator Reconcile 流程 | Custom Resource event、Kopf handler、資源比對與 status 更新。 |
| 21 | Operator 資源展開結果 | 一個 `Microservice` 如何展開為 Deployment、Service、OTel 設定與運行狀態。 |
| 22 | IDP API 產 YAML 並寫入 Git | Portal 表單、API 驗證、YAML render、Git API 與 Argo CD 同步。 |
| 23 | GitOps Pull Request 防呆流程 | Branch、schema validation、Pull Request、review/merge 與錯誤回饋。 |
| 24 | Argo CD Health 判斷流程 | 自訂 health check 如何從 CRD status 判斷服務的 Progressing、Healthy 或 Degraded。 |
| 25 | 狀態反饋閉環 | Argo CD Notification webhook、IDP API、資料庫與 Portal 狀態更新的事件方向。 |
| 26 | Namespace 多租戶與 RBAC 邊界 | Team namespace、ServiceAccount、Role、RoleBinding 與跨 namespace 存取拒絕。 |
| 27 | OPA Gatekeeper Admission 流程 | Kubernetes API request、Gatekeeper、ConstraintTemplate、Constraint 與 allow/deny 結果。 |
| 28 | Policy 違規與拒絕案例 | 缺少 resource limits、privileged container、非核准 GHCR image 的請求與拒絕訊息。 |
| 29 | Istio Sidecar 流量管控 | Ingress、Envoy sidecar、服務流量與平台控制面的責任邊界。 |
| 30 | mTLS 與 AuthorizationPolicy | 雙向 TLS 加密、身分驗證，以及白名單服務允許／拒絕的流向。 |
| 31 | 完成版平台演進地圖 | Day 01 平台藍圖的完成版本，並標示可持續演進的 AI、成本、可靠性與開發者體驗方向。 |