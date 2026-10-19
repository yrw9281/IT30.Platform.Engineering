[English](README.md) | [繁體中文](README-zh-TW.md)

# Kubernetes 部署與 Microservice CRD

對應 Day 03–05、Day 15 與 Day 18。以下指令皆從儲存庫根目錄執行。

| 目錄 | 用途 |
| --- | --- |
| `kind/` | 使用本機 image 的 Deployment、Service、Ingress |
| `ghcr/` | 使用 GHCR image 的同一組 Todo 工作負載 |
| `crd/` | Microservice CRD、合法輸入與 schema 拒絕案例 |

`kind/` 與 `ghcr/` 管理同名資源，擇一使用。啟用 Operator 後，不要再用這兩組 manifest 覆寫它管理的 Todo API。

兩組設定都預設執行兩個 Todo API 副本，各 Pod 的記憶體資料不共享，查詢或更新時可能找不到剛新增的待辦事項。使用前，請將選用目錄中 `todo-api.yaml` 的 `spec.replicas` 改為 `1`；擴展副本前須先導入共享儲存。若由 Argo CD 管理，請將變更推送到 Git，只執行 `kubectl scale` 不會保留設定。

## 本機 image 與 Kind

需要 Docker、Kind、`kubectl` 與已存在的 Kind 叢集。先依 [應用程式說明](../0-todo-microservices/README-zh-TW.md) 建置三個 image，再載入叢集：

```bash
kubectl config current-context
kind load docker-image todo-api:0.1.0 todo-bff:0.1.0 todo-web:0.1.0
kubectl apply -k src/1-kubernetes/kind
kubectl get deployment,service,ingress -n todo
```

`kind load` 預設使用名稱為 `kind` 的叢集；使用其他名稱時，加入 `--name <cluster-name>`，並確認 `kubectl` context 指向同一個叢集。

Ingress 使用 `nginx` IngressClass，將 `todo.localhost` 的 `/api` 導向 BFF，其餘路徑導向網頁。叢集必須另外安裝 NGINX Ingress Controller；沒有 controller 時，可先透過 Service 存取：

```bash
kubectl port-forward service/todo-bff 8080:8080 -n todo
```

在另一個終端機執行 `curl --fail http://127.0.0.1:8080/api/todos`。

## GHCR image

`ghcr/` 使用可變動的 `:0.1.0` tag，未以 digest 固定版本。三個 image 都必須已發布且可由叢集拉取。私有 package 請先完成下方的 Namespace、Secret 與 Deployment 設定，再執行部署：

```bash
kubectl apply -k src/1-kubernetes/ghcr
kubectl rollout status deployment/todo-api -n todo
kubectl rollout status deployment/todo-bff -n todo
kubectl rollout status deployment/web -n todo
```

私有 package 需要 `todo` Namespace 中的唯讀拉取憑證。請先依核准流程建立 Namespace，再使用只有目標 package `read:packages` 權限的憑證建立 Secret，不要使用 CI 的短期 `GITHUB_TOKEN`。以下在 Bash 中隱藏輸入：

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

章節範例共用 `crd/microservice-crd.yaml`，定義 Namespace 範圍的 `platform.example.io/v1alpha1` API。輸入只有 `spec.image` 與 `spec.port`，沒有 `env` 或 Secret 引用。`src/final/` 另有 CRD 快照，僅搭配該目錄的部署設定使用。

目前 schema 要求根層的 `spec` 必填，並包含 Day 22 的 `status.conditions`；Day 05／18 展示的是早期版本。升級前，請查詢所有 CR，確認 image 非空、port 為 `1–65535` 的整數，先修正不符的資料再加入必填限制：

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

實際提交 `todo-api.yaml` 與部署 Operator 的步驟見 [IDP 說明](../4-idp/README-zh-TW.md)。CR 本身不會建立 Deployment；刪除已由 Operator 管理的 CR，則會連帶回收它擁有的工作負載。
