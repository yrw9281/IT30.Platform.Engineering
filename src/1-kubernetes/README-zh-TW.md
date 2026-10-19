# Kubernetes 部署與 Microservice 合約

對應 Day 03–05、Day 15 與 Day 18。以下指令都從 repository 根目錄執行。

| 目錄 | 用途 |
| --- | --- |
| `kind/` | 使用本機 image 的 Deployment、Service、Ingress |
| `ghcr/` | 使用 GHCR image 的同一組 Todo 工作負載 |
| `crd/` | Microservice CRD、合法輸入與 schema 拒絕案例 |

`kind/` 與 `ghcr/` 管理同名資源，擇一使用。啟用 Operator 後，不要再用這兩組 manifest 覆寫它管理的 Todo API。

## 本機 image 與 Kind

先依 [應用程式說明](../0-todo-microservices/README.md) 建置三個 image，再載入已存在的 Kind 叢集：

```bash
kubectl config current-context
kind load docker-image todo-api:0.1.0 todo-bff:0.1.0 todo-web:0.1.0
kubectl apply -k src/1-kubernetes/kind
kubectl get deployment,service,ingress -n todo
```

Ingress 使用 `nginx` IngressClass，將 `todo.localhost` 的 `/api` 導向 BFF，其餘路徑導向網頁。叢集必須另外安裝 NGINX Ingress Controller；沒有 controller 時，可先透過 Service 存取：

```bash
kubectl port-forward service/todo-bff 8080:8080 -n todo
```

在另一個終端機執行 `curl --fail http://127.0.0.1:8080/api/todos`。

## GHCR image

`ghcr/` 目前使用 `:0.1.0` tag，不是 digest promotion。先確認三個 image 已發布且可由叢集拉取：

```bash
kubectl apply -k src/1-kubernetes/ghcr
kubectl rollout status deployment/todo-api -n todo
kubectl rollout status deployment/todo-bff -n todo
kubectl rollout status deployment/web -n todo
```

若 package 為 private，需要 Namespace 內的唯讀 image pull Secret。使用只具備目標 package `read:packages` 的憑證，不要使用 CI 的短期 `GITHUB_TOKEN`。例如在 Bash 中以隱藏輸入建立 Secret：

```bash
set -euo pipefail
read -r -s -p 'GHCR read token: ' GHCR_TOKEN
printf '\n'
test -n "$GHCR_TOKEN"
kubectl create secret docker-registry ghcr-pull-secret -n todo \
  --docker-server=ghcr.io --docker-username=yrw9281 \
  --docker-password="$GHCR_TOKEN"
unset GHCR_TOKEN
```

這個命令會把 token 暫時放入 kubectl 的程序參數，只適合可信任的工作站；共用主機應使用既有的 Secret 管理流程。不要開啟 shell tracing，也不要把 Secret 內容寫入 Git。接著在需要拉取 private image 的 Deployment `spec.template.spec` 加上：

```yaml
imagePullSecrets:
  - name: ghcr-pull-secret
```

## Microservice CRD

`crd/microservice-crd.yaml` 是唯一的 CRD 定義，API 為 `platform.example.io/v1alpha1`，範圍是 Namespace。輸入只有 `spec.image` 與 `spec.port`，沒有 `env` 或 Secret 引用。

目前版本已要求根層的 `spec` 必填，也包含 Day 22 的 `status.conditions`，不同於 Day 05／18 展示的早期 schema。升級既有叢集前，先查詢所有 CR，確認都有非空 image 與 `1–65535` 的整數 port；新增 required 欄位不會修復舊資料：

```bash
kubectl get microservices -A -o yaml
```

首次安裝前確認目標叢集與已存在的 `todo` Namespace。下列安裝會寫入叢集，需要 CRD 管理權限：

```bash
kubectl config current-context
kubectl get namespace todo
kubectl apply -f src/1-kubernetes/crd/microservice-crd.yaml
kubectl wait --for=condition=Established crd/microservices.platform.example.io --timeout=60s
```

安裝後可用 server-side dry-run 檢查輸入，不儲存 CR：

```bash
kubectl apply --server-side --dry-run=server \
  -f src/1-kubernetes/crd/todo-api.yaml \
  -f src/1-kubernetes/crd/web.yaml
kubectl apply --server-side --dry-run=server \
  -f src/1-kubernetes/crd/invalid-todo-api.yaml
```

最後一個案例的 port 是 `65536`，預期被拒絕。dry-run 通過不代表 image 存在或工作負載就緒。`web.yaml` 只用來檢查 schema；Web image 不符合目前 Operator 的 Todo API probes，不要交給它部署。

實際提交 `todo-api.yaml` 與部署 Operator 的步驟見 [IDP 說明](../4-idp/README.md)。CR 本身不會建立 Deployment；刪除已由 Operator 管理的 CR，則會連帶回收它擁有的工作負載。
