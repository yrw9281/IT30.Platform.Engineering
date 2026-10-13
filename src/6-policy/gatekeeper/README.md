# Gatekeeper 政策範例

以下三份 YAML 對應 [Day 29](../../../doc/zh-tw/D29.md)，每份依序包含一份 `ConstraintTemplate` 與一份 Constraint：

| 檔案 | 檢查內容 | 範例模式 |
| --- | --- | --- |
| `k8sdeploymentnoprivileged.yaml` | Deployment 的一般容器與 init container 不可啟用 privileged | `deny` |
| `k8sdeploymentrequiredlimits.yaml` | Deployment 的一般容器與 init container 必須設定 CPU／memory limits | `dryrun` |
| `k8smicroserviceimagepolicy.yaml` | Microservice 必須使用固定 Todo API repository 與 SHA-256 digest 格式 | `warn` |

使用前需要已安裝 Gatekeeper。每組都要先建立 Template，等產生的 Constraint CRD 就緒，再提交 Constraint；不要假設一次提交整份多文件 YAML，就能避開 CRD 尚未就緒的問題。privileged 的 `deny` 示範正式拒絕模式，首次導入仍應改用 `dryrun` 盤點。

所有 Constraint 都限定 `todo` Namespace。image 規則涵蓋其中所有 `Microservice`，但固定為 `ghcr.io/yrw9281/it30-todo-api`，不是多服務通用的允許清單。limits 只檢查存在且非空，不解析數量、設定最大值或管理 Namespace 預算。image 只檢查格式，不掃描漏洞或驗證建置來源。這些範例未涵蓋直接建立的 Pod。

`todo-required-limits-exception.yaml` 是 limits Constraint 的替代設定，不是第四條政策。它修改同名的 `todo-required-limits`，以 `match.labelSelector` 排除 `Deployment.metadata.labels.app=todo-api` 的資源；其他 label 值或沒有 `app` label 的 Deployment 仍符合檢查範圍。它不排除 privileged 等其他 Constraint，也不是依資源名稱排除，能修改該 label 的提交者同樣能符合例外條件。不要將它與原本的 limits Constraint 當成兩份獨立設定同時管理。

Rego 使用傳統 v0 語法，與 `targets[].rego` 格式搭配；OPA 1.x 的離線測試需要 `--v0-compatible`，測試程式已帶入這個選項。離線測試不代表已完成 Gatekeeper 的 CRD、audit、admission、執行模式或平台錯誤回饋整合；本目錄沒有安裝流程，也沒有叢集拒絕的實測結果。

## 離線驗證

需要 Python 3、PyYAML 與 OPA CLI。可在已有依賴的 Python 環境執行：

```bash
python3 -m unittest discover -s src/6-policy/gatekeeper/tests -p 'test_*.py'
```

若 OPA 不在 `PATH`，以 `OPA` 環境變數指定執行檔。測試從 Template 擷取 Rego，驗證 privileged、缺少／空值 limits、image 來源與 digest 格式，以及文章 YAML 與來源一致。

切成 `deny` 前，仍需在測試叢集確認正常請求能通過、違規請求會被拒絕且訊息清楚，再核對 Argo CD／Operator 的回饋位置。

參考：[ConstraintTemplate](https://open-policy-agent.github.io/gatekeeper/website/docs/constrainttemplates/)、[執行模式](https://open-policy-agent.github.io/gatekeeper/website/docs/violations/)。
