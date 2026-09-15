# iThome 2026 鐵人賽

## Theme

Title: **寫完微服務然後呢？走向平台工程的黃金路徑**
Description: 從 K8s、GitOps 到 Observability，打造 Internal Developer Platform (IDP) 實現全自動維運閉環，鋪平微服務交付之路。

## Outline

### 第零階段：序言

我有一前篇系列文：

```plaintext
DDD? Clean Architecture? Microservices? 帶你用.NET實作打造一個現代化微服務！ 系列
打造微服務非常複雜，其中許多技術都值得深入探討。但我想做點不一樣的，從系統架構層級剖析整個現代化微服務，並透過簡單的案例帶你一步步實作。
```

這是上一系列的[結尾文](https://github.com/yrw9281/IT30.Todo.Microservices/blob/main/doc/pages/D30/D30.md)，可承接。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 01** | **序言與開始** | 介紹平台工程的核心價值，並介紹後續一到六階段，不需要提文章內容與標題，可以從上一系列來起頭。 |

### 第一階段：序言與現代基礎設施 (Day 01 - Day 05)

從鳥瞰全局開始，接著建立 K8s 核心認知，為後續的自動化與自定義資源 (CRD) 鋪路。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 02** | K8s 核心心智模型：宣告式 API 與控制迴路 (Reconcile Loop) | 直切 K8s 的靈魂：「期望狀態 vs 實際狀態」的收斂機制。理解控制器模式，這是後續理解 GitOps 與 Operator 的根基。 |
| **Day 03** | 應用程式交付解構：Deployment、Service 到 Ingress 的流量骨架 | 以實際的微服務為例，拆解開發者如果要上線一個服務，究竟需要組合哪些基礎的 YAML 資源。 |
| **Day 04** | 彈性配置管理：Helm 與 Kustomize 實戰與選型 | 解決純靜態 YAML 的痛點，介紹如何針對不同環境（Dev/Staging/Prod）進行參數化與動態渲染。 |
| **Day 05** | K8s 擴充性基石：CRD (Custom Resource Definition) 簡介 | 探討如何擴充 K8s 的 API 讓其認識「非原生資源」，為第五階段打造專屬平台合約埋下伏筆。 |

### 第二階段：GitOps 與 ArgoCD 部署閉環 (Day 06 - Day 09)

將基礎設施與部署狀態完全交由 Git 仲裁，建立自動同步機制。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 06** | GitOps 哲學解析：以 Git 作為單一真實來源 (Single Source of Truth) | 對比傳統 Push-based CI 腳本與 Pull-based 架構的差異，探討權限隔離與災難還原的優勢。 |
| **Day 07** | ArgoCD 實戰入門：宣告式持續交付引擎架構與部署 | 部署 ArgoCD，解析 Application 資源，實作將 Git 儲存庫中的 YAML 變更自動同步至叢集。 |
| **Day 08** | 大規模多環境管理：ArgoCD ApplicationSet 動態生成 | 運用 Git/List Generator 動態產生 Application，解決微服務與多叢集環境暴增時，手動維護 YAML 的痛點。 |
| **Day 09** | 現代化進階發布：結合 Argo Rollouts 實現 Canary 金絲雀部署 | 告別單純滾動更新，展示如何透過流量比例控制與自動化指標判斷，實現安全的漸進式發布。 |

### 第三階段：可觀測性與 OTel 中樞神經 (Day 10 - Day 14)

服務上線後必須具備透明度，在此建立統一的遙測標準與視覺化面板。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 10** | 可觀測性 (O11y) 概論：從 Metrics、Logs 到 Traces 的黃金三角 | 釐清 Monitoring (警報) 與 Observability (探究未知) 的本質差異，定義三大支柱的關聯。 |
| **Day 11** | 終結供應商鎖定：OpenTelemetry (OTel) 統一標準與架構全解 | 剖析 OTel API、SDK 規範，探討跨語言、跨工具遙測資料標準化的核心價值。 |
| **Day 12** | 遙測資料轉運站：部署與配置 OpenTelemetry Collector | 實戰 Receiver、Processor、Exporter 管道，處理資料的過濾、脫敏、批次聚合與統一轉發。 |
| **Day 13** | 分散式追蹤 (Distributed Tracing)：微服務跨節點瓶頸定位實戰 | 實作跨服務 Trace Context 的注入與傳遞，視覺化排查 API 呼叫鏈路與資料庫慢查詢。 |
| **Day 14** | 統一聯動儀表板：整合 Prometheus、Loki 與 Grafana | 串聯 Trace-to-Metrics 與 Trace-to-Logs，打造一套開發團隊一眼看懂服務健康度的綜合監控面板。 |

### 第四階段：CI 工作流與架構銜接 (Day 15 - Day 17)

確立開發端到 GitOps 端的橋樑，確保 CI 與 CD 職責分離。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 15** | GitHub Actions 基礎：現代化 CI 工作流與 Pipeline 設計 | 設計乾淨且具備快取、自動化單元測試的 CI Workflow，確保程式碼品質。 |
| **Day 16** | 自動化建置與推送：Docker Image 封裝與 Tag 版本管理策略 | 在 CI 中自動化容器編譯，探討基於 Git SHA 或 Semantic Versioning 的 Image Tagging 最佳實踐。 |
| **Day 17** | CI 與 GitOps 的交響樂：職責分離與自動化銜接機制 | 釐清 CI (Build & Test) 與 CD (Deploy) 的嚴格分界，探討 CI 打包完成後，如何透過程式碼自動更新 GitOps 配置庫。 |

### 第五階段：IDP 實戰 - 抽象化合約與狀態反饋閉環 (Day 18 - Day 25)

本系列最硬核精華：親手打造一套從 Web UI 到 K8s 底層再回傳狀態的完整平台工程系統。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 18** | 平台工程架構藍圖：鋪設黃金路徑與 IDP 控制流設計 | 確立架構圖：IDP Portal 產 YAML → Git → ArgoCD 部署 → Operator 展開資源 → ArgoCD Webhook 更新 DB。 |
| **Day 19** | 定義團隊的基礎設施合約：設計專屬 App Spec (CRD) | 隱藏 K8s 底層複雜度，設計一個 `Microservice` 的 CRD Schema，僅開放 Image、Port、環境變數等核心欄位。 |
| **Day 20** | K8s 內的翻譯官：介紹 Operator 模式與輕量級框架 Kopf | 解釋為何在平台工程中避免手寫沉重的 Go Operator，並介紹 Python 框架 Kopf 如何優雅攔截 CRD 事件。 |
| **Day 21** | 自製 Operator 實戰：利用 Kopf 將 CRD 展開為 Deployment | 撰寫 Python 邏輯：當叢集建立 `Microservice` CRD 時，背後自動運算並長出對應的 Deployment、Service 與 OTel 設定。 |
| **Day 22** | IDP 後端開發 (一)：API 自動生成 YAML 並提交 GitOps 儲存庫 | 實作 Backend API：接收前端表單，渲染成 `Microservice` CRD YAML，並透過 Git API 寫入配置庫 (Config Repo)。 |
| **Day 23** | IDP 後端開發 (二)：自動化 Pull Request 與配置防呆校驗 | 強化提交流程：在自動 Commit 時導入 PR 機制，並進行初步的 YAML Schema 靜態檢查，防止毒資料流入。 |
| **Day 24** | 狀態反饋閉環 (一)：配置 ArgoCD Health Checks 與 Notifications | 不依賴 CI 輪詢！透過配置 ArgoCD 自訂 Health 狀態，讓其精準感知自製 CRD 底下的 Pod 是否順利啟動。 |
| **Day 25** | 狀態反饋閉環 (二)：透過 Webhook 將 K8s 狀態打回 IDP DB | 實戰 ArgoCD Notifications 發送 Webhook：當服務從 `Deploying` 變為 `Healthy` 時，同步更新 IDP 資料庫，完成全鏈路閉環。 |

### 第六階段：平台級安全防禦與策略治理 (Day 26 - Day 30)

隨著自動化與自服務程度提高，透過架構與策略（Policy）來防堵人為失誤與惡意存取。

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 26** | 平台安全基石：K8s RBAC 與 Namespace 多租戶隔離機制 | 確保 IDP 產出的服務，在同一個 K8s 叢集中受到嚴格的權限邊界限制，防止跨團隊越權。 |
| **Day 27** | 政策即程式碼 (Policy as Code)：OPA Gatekeeper 架構解析 | 介紹 Open Policy Agent (OPA) 概念，探討為何需要動態准入控制器 (Admission Controller) 來把關叢集安全。 |
| **Day 28** | OPA 實戰：撰寫 Rego 規則動態阻擋高風險 YAML | 實作自定義防護網：強制要求資源限制 (Limits)、阻擋特權容器 (Privileged)、限制只能從私有 Image Registry 拉取映像檔。 |
| **Day 29** | 零信任網格 (一)：Istio 架構與無侵入式流量管控 | 導入 Istio Service Mesh，解析 Sidecar 模式如何接管微服務進出流量，為平台加上統一的安全代理。 |
| **Day 30** | 零信任網格 (二)：mTLS 雙向加密與 AuthorizationPolicy 實戰 | 實作服務間的自動流量加密，並設定授權策略，確保只有特定的白名單服務彼此可以互相溝通。 |

### 第七階段：總結與未來展望 (Day 31)

| 天數 | 文章標題 | 內容核心描述 |
| --- | --- | --- |
| **Day 31** | **31 天總結：平台工程的完備圖譜與持續演進之路** | 串聯回顧從 K8s 底層到全自動 IDP 閉環與 Security Mesh 的旅程，並分享未來結合 AI 輔助開發的平台演進趨勢。 |

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
| 09 | Canary 發布生命週期 | Rollout、Stable/Canary ReplicaSet、流量比例、分析結果與 promotion／rollback。 |
| 10 | Metrics、Logs、Traces 黃金三角 | 同一服務與請求如何以三種 telemetry signal 互相定位。 |
| 11 | OpenTelemetry 全貌 | Application SDK、OTel Collector、telemetry backend 與標準化資料流。 |
| 12 | OpenTelemetry Collector pipeline | Receiver、Processor、Exporter 的處理順序，以及過濾、脫敏、批次與轉送。 |
| 13 | 跨服務 Trace Context | 入口請求、服務呼叫、資料庫 span 與 trace ID 的傳遞路徑。 |
| 14 | Observability 平台整合 | Prometheus、Loki、Tracing backend、Grafana，以及 trace-to-logs／metrics 的跳轉關係。 |
| 15 | CI Pipeline | Commit/PR、lint、test、build、artifact 或 image 與失敗回饋。 |
| 16 | Container Image 建置與版本流 | Source commit、tag 策略、container registry 與 immutable image digest。 |
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
| 28 | Policy 違規與拒絕案例 | 缺少 resource limits、privileged container、非私有 registry image 的請求與拒絕訊息。 |
| 29 | Istio Sidecar 流量管控 | Ingress、Envoy sidecar、服務流量與平台控制面的責任邊界。 |
| 30 | mTLS 與 AuthorizationPolicy | 雙向 TLS 加密、身分驗證，以及白名單服務允許／拒絕的流向。 |
| 31 | 完成版平台演進地圖 | Day 01 平台藍圖的完成版本，並標示可持續演進的 AI、成本、可靠性與開發者體驗方向。 |