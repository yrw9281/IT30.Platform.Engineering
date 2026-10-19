[English](README.md) | [繁體中文](README-zh-TW.md)

# Gatekeeper 政策範例

`gatekeeper/` 的三份 YAML 對應 [Day 29](../../doc/zh-tw/D29.md)，每份依序包含一份 `ConstraintTemplate` 與一份 Constraint：

| 檔案 | 檢查內容 | 範例模式 |
| --- | --- | --- |
| `k8sdeploymentnoprivileged.yaml` | Deployment 的一般容器與 init container 不可啟用 privileged | `deny` |
| `k8sdeploymentrequiredlimits.yaml` | Deployment 的一般容器與 init container 必須設定 CPU／memory limits | `dryrun` |
| `k8smicroserviceimagepolicy.yaml` | Microservice 必須使用固定 Todo API repository 與 SHA-256 digest 格式 | `warn` |

安裝 Gatekeeper 後，先建立各 Template，等產生的 Constraint CRD 就緒，再提交 Constraint。即使兩者放在同一份 YAML，也要分開執行。privileged 政策以 `deny` 示範拒絕請求；導入既有環境時，請先用 `dryrun` 盤點。

所有 Constraint 都僅套用於 `todo`。image 規則檢查其中每個 `Microservice`，僅接受 `ghcr.io/yrw9281/it30-todo-api` 與指定的 digest 格式，不能作為多服務的允許清單，也不掃描漏洞或驗證建置來源。limits 只要求欄位存在且非空，不解析數量、設定上限或管理 Namespace 預算。直接建立的 Pod 不在檢查範圍內。

`todo-required-limits-exception.yaml` 會替換原本的 `todo-required-limits` Constraint，兩份設定請擇一使用。它透過 `match.labelSelector` 排除 `Deployment.metadata.labels.app=todo-api`；其他值或沒有 `app` label 的 Deployment 仍會受檢查。這個例外只適用 limits，依 label 判斷而非資源名稱，能修改該 label 的人也能符合例外。privileged 等其他 Constraint 不受影響。

`targets[].rego` 使用傳統 v0 語法，以 OPA 1.x 離線評估時需要 `--v0-compatible`。本目錄提供政策範例，未附 Gatekeeper 安裝步驟或叢集拒絕的實測結果；CRD 建立、audit、admission、執行模式與平台錯誤回饋仍待整合驗證。

切成 `deny` 前，請在測試叢集分別送出正常與違規請求，確認拒絕訊息清楚，並能從 Argo CD 或 Operator 日誌追查原因。

參考：[ConstraintTemplate](https://open-policy-agent.github.io/gatekeeper/website/docs/constrainttemplates/)、[執行模式](https://open-policy-agent.github.io/gatekeeper/website/docs/violations/)。
