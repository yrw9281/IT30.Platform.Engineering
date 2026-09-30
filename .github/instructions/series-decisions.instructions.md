# iThome 2026 系列決策（持久記錄）

修改系列文章前先讀 `outline.md` 與目標篇前後文章；本檔記錄已確認的選型，不取代大綱或實際 `src/`。

## 已確認

- 保留內部開發者平台（Internal Developer Platform，IDP）作為交付能力的總稱。D17 用 Todo 服務交付情境解釋；Backstage 是開發者入口，不等同於 IDP、Argo CD 或 Operator。
- 導入 Backstage 的 Software Catalog 與 Software Templates，優先取代原規劃自製的 Portal UI、非必要的專屬 API、交付狀態資料庫與 webhook 時間線。Backstage 不會自動提供完整交付事件歷史；模板、Git 權限與 Kubernetes plugin 都需要安裝與設定。
- 保留 `Microservice` CRD、Kopf Operator、Git Pull Request 與 Argo CD。D17 說明整體控制流程；D18–20 處理 CRD 與 Operator；D21–22 改以 Backstage 表單／模板與 Git PR 為核心；D23 保留 CR health；D24 聚焦服務與部署狀態查詢，誠實交代與事件時間線的差距。
- D16 的範圍是 release tag 觸發 CI、產出 image digest，以及以受審查的 Git 設定變更交接 GitOps。`repo-config` 僅是規劃中的設定來源；Kustomize overlay 非必要。現有 release workflow 沒有更新 config PR；Argo CD 的 `Application` 讀取 `src/1-kubernetes/kind`，沒有同步 `Microservice`。
- D01–15 已發布，除非指出直接誤導新方向的具體位置與理由，不回頭修改。D16 發布前須區分現有實作與規劃，避免承諾尚未完成的自動部署。
- 既有 `src/1-kubernetes/crd/microservice-crd.yaml` 定義 `image`、`port` 與初版 `status`；env、conditions、Kopf、Backstage、獨立設定儲存庫與自動更新 PR 均未實作。撰寫前以實際檔案再次核對，不要把規劃片段當作可運作範例。
- 維持 Day 01–30 的編號與篇數；新實作篇的可複製範例需有 `src/` 對應來源。未提供視覺素材時留下 `TODO(assets)`，不宣稱有圖或測試結果。
- 作者已確認 D25–29 **全部改為概念教學**。D25 說明 Namespace／RBAC 的權限邊界與預期 allow/deny；D26–27 解釋 Gatekeeper 的 admission 及三種風險案例；D28–29 說明 Istio sidecar、mTLS 和授權的作用、取捨與導入限制。沒有來源檔或叢集測試時，不保留可複製 YAML、Rego 或指令，也不宣稱政策已落地。

## 後續修稿注意

- D25 草稿原以自製 Portal 接收交付狀態為前提，與 D24 的 Backstage 資源現況不符；修訂時銜接 Catalog／Kubernetes plugin 的查詢邊界，不引入虛構的 webhook 時間線。
