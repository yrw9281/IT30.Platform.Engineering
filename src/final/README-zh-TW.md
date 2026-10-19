[English](README.md) | [繁體中文](README-zh-TW.md)

# 在乾淨 Cluster 建立完整平台

本目錄包含在乾淨、可連線的 Kubernetes 叢集上安裝 Todo、Argo CD、OpenTelemetry、Backstage 與 Gatekeeper 所需的程式碼、image 建置來源與設定。請依下方順序安裝。

乾淨叢集可以已有 CNI、CoreDNS 等 Kubernetes 基礎元件，但不應已有本平台的 Namespace、CRD、Argo CD、Ingress Controller、Gatekeeper 或 Todo 工作負載。以下指令不處理既有平台的升級、接管或遷移，也不會刪除叢集資源。

## 目錄與管理責任

| 目錄 | 內容 |
| --- | --- |
| `foundation/` | 四個 Namespace 與 `Microservice` CRD |
| `bootstrap/` | 固定版本的 Argo CD、NGINX Ingress Controller、Gatekeeper |
| `observability/` | Collector、Prometheus、Loki、Tempo、Grafana、datasource 與 dashboard |
| `operator/` | Kopf handler、Deployment／Service 產生邏輯、健康回報、RBAC 與部署設定；Kustomize 產生程式碼 ConfigMap |
| `backstage/` | 服務目錄、單一 PR 模板、Kubernetes 唯讀權限、Deployment 與可獨立建置的 Backstage App |
| `config/runtime/` | BFF、Web、Ingress，交給 `todo-full-runtime` Application 管理 |
| `config/todo-api/` | 唯一一筆 Todo API `Microservice`，交給 `todo-full-api` Application 管理 |
| `gitops/` | AppProject 與產生上述兩個 Application 的 ApplicationSet |
| `policy/` | 三個 ConstraintTemplate 與三個 Constraint，安裝時分兩階段 |
| `services/` | Todo API、BFF、Web 的原始碼與 Dockerfile |
| `ci/` | GitHub Actions workflow；須放到 GitHub 指定的位置才會執行 |

Todo API 的 Deployment／Service 由 Operator 管理，不另寫進 Git；BFF 與 Web 的原生資源由 Argo CD 管理。

Namespace 只在 `foundation/` 宣告；`ingress-nginx` 與 `gatekeeper-system` 由各自的官方 manifest 建立。ConfigMap generator 保留名稱 hash，修改程式碼或 Backstage 設定後重新 `apply -k`，會更新 Pod template；舊 hash ConfigMap 不會自動刪除。

## 開始前

需要具管理者權限的 kubeconfig、Bash 或 Zsh，以及支援 Kustomize 的 `kubectl`。`kubectl` 與 API Server 的次版本差距須在一版以內；例如 Kubernetes `1.30` 使用 `kubectl 1.29` 至 `1.31`。叢集需能連到 GHCR、Docker Hub、`registry.k8s.io`、`quay.io`、`public.ecr.aws` 與 PyPI。Argo CD 需能讀取 GitHub，Operator 的 init container 會從 PyPI 安裝固定版本的 Kopf 與 Kubernetes client。叢集建立方式不限。

繼續前，請確認 context 指向這個乾淨叢集，且所有 Node 都是 `Ready`：

```bash
kubectl config current-context
kubectl version
kubectl cluster-info
kubectl get nodes
```

為了使用測試叢集的剩餘容量，平台 Pod 設有 control-plane 的 `NoSchedule` toleration，可排程到 worker 與 control-plane，不會移除節點 taint。共用設定在 `bootstrap/scheduling/`，Operator 產生的 Todo API Pod 也使用相同設定。正式環境應準備專用 worker，移除各 Kustomization 的排程元件與 Operator 對應設定。即使 Node 為 `Ready`，Pod 仍可能因容量不足停在 `Pending`，請用 `kubectl describe pod` 查看排程事件。

預設使用本儲存庫的 `main`：

- Argo CD 讀取 `src/final/config/runtime` 與 `src/final/config/todo-api`。
- Backstage PR 只寫入 `src/final/config/todo-api`。
- image 使用 `ghcr.io/yrw9281/it30-todo-*`，Backstage 使用 `it30-idp-backstage:demo`。

Argo CD 讀取遠端 Git，啟用 GitOps 前請先將本目錄提交並推送到 `main`。使用 fork 時，須修改 `gitops/project.yaml`、`gitops/applicationset.yaml`、`backstage/templates/template.yaml` 的儲存庫設定。若更換 image repository，也要更新工作負載的 image、模板產生的 YAML、image 政策與 CI 的檢查及發布目的地。

叢集必須能匿名拉取預設 image。若使用私有 package，請在 Todo API、BFF 與 Web 共用的 `todo` Namespace `default` ServiceAccount 設定拉取憑證；Operator 產生的 Pod 未宣告 `imagePullSecrets`。Backstage 的 `backstage` ServiceAccount 須另外授權，憑證不要提交 Git。

## 安裝順序

以下指令從 `src/final/` 依序執行，讓 CRD 與 webhook 先就緒，再套用依賴它們的資源。不要使用 `kubectl apply -R -f .`，因為目錄內也包含不能直接提交給 Kubernetes API 的設定檔與模板。

### 1. 建立 Namespace 與 CRD

```bash
cd src/final
kubectl config current-context
kubectl apply --server-side -k foundation
kubectl wait --for=condition=Established \
  crd/microservices.platform.example.io --timeout=120s
```

### 2. 安裝 controller

Argo CD 與 Gatekeeper 的 CRD 較大，使用 server-side apply，避免超過 client-side apply 的 annotation 大小限制。

```bash
kubectl apply --server-side -k bootstrap/argocd
kubectl wait --for=condition=Established \
  crd/applications.argoproj.io crd/applicationsets.argoproj.io \
  crd/appprojects.argoproj.io --timeout=120s
kubectl rollout status statefulset/argocd-application-controller -n argocd --timeout=300s
kubectl rollout status deployment/argocd-applicationset-controller -n argocd --timeout=300s
kubectl rollout status deployment/argocd-repo-server -n argocd --timeout=300s
kubectl rollout status deployment/argocd-server -n argocd --timeout=300s
kubectl rollout status deployment/argocd-redis -n argocd --timeout=300s

kubectl apply --server-side -k bootstrap/ingress
kubectl wait --for=condition=Complete job/ingress-nginx-admission-create \
  job/ingress-nginx-admission-patch -n ingress-nginx --timeout=300s
kubectl rollout status deployment/ingress-nginx-controller -n ingress-nginx --timeout=300s

kubectl apply --server-side -k bootstrap/gatekeeper
kubectl wait --for=condition=Established \
  crd/constrainttemplates.templates.gatekeeper.sh --timeout=120s
kubectl rollout status deployment/gatekeeper-controller-manager -n gatekeeper-system --timeout=300s
kubectl rollout status deployment/gatekeeper-audit -n gatekeeper-system --timeout=300s
```

Ingress 使用官方 bare-metal 的 NodePort Service，不需要雲端 LoadBalancer。後續以 port-forward 開啟 Todo，不需要另外設定 Node 的 host port。

### 3. 註冊政策

先提交 Template，等 Gatekeeper 回報建立完成、對應的 CRD 就緒，再提交 Constraint。這裡使用 JSONPath 等待狀態，避免依賴舊版 `kubectl` 不支援的 `--for=create`。

```bash
kubectl apply --server-side -k policy/templates
kubectl wait --for=jsonpath='{.status.created}'=true \
  constrainttemplate/k8sdeploymentnoprivileged \
  constrainttemplate/k8sdeploymentrequiredlimits \
  constrainttemplate/k8smicroserviceimagepolicy --timeout=180s
kubectl wait --for=condition=Established \
  crd/k8sdeploymentnoprivileged.constraints.gatekeeper.sh \
  crd/k8sdeploymentrequiredlimits.constraints.gatekeeper.sh \
  crd/k8smicroserviceimagepolicy.constraints.gatekeeper.sh --timeout=180s
kubectl apply --server-side -k policy/constraints
```

政策僅套用於 `todo`：privileged 使用 `deny` 拒絕違規請求，limits 使用 `dryrun` 盤點，image 來源／digest 違規則以 `warn` 回傳警告。若要強制拒絕後兩者，請先測試允許與拒絕案例，再修改 `policy/constraints/constraints.yaml` 的 `enforcementAction` 並重新套用。

政策只檢查 Deployment 或 Microservice，直接提交的 Pod、StatefulSet 等工作負載不在範圍內。官方 Gatekeeper validation webhook 使用 `failurePolicy: Ignore`，無法連線時會放行；正式環境的存取控制須考慮這項限制。

### 4. 提供必要憑證

以下在 Bash 或 Zsh 隱藏輸入 Grafana 密碼與 GitHub token，建立 Secret，不將值寫入 manifest 或 shell history；請勿開啟 `set -x`。括號將錯誤處理設定限制在子 shell，不改變終端機或 VS Code shell integration。PAT 僅授予本儲存庫 Contents／Pull requests 讀寫權，不給 workflow、叢集或組織管理權限。儲存庫須允許建立 PR。

```bash
(
set -eo pipefail
printf 'Grafana admin password: '
read -r -s GRAFANA_PASSWORD
printf '\n'
test -n "$GRAFANA_PASSWORD"
printf %s "$GRAFANA_PASSWORD" | kubectl create secret generic grafana-admin \
  -n observability --from-file=password=/dev/stdin \
  --dry-run=client -o yaml | kubectl apply -f -
unset GRAFANA_PASSWORD

printf 'GitHub PAT: '
read -r -s GITHUB_PAT
printf '\n'
test -n "$GITHUB_PAT"
printf %s "$GITHUB_PAT" | kubectl create secret generic backstage-github \
  -n backstage --from-file=token=/dev/stdin \
  --dry-run=client -o yaml | kubectl apply -f -
unset GITHUB_PAT
)
```

輸入錯誤時，重跑該 Secret 的指令即可，`kubectl apply` 會直接更新。輪替 PAT 後，請執行 `kubectl rollout restart deployment/backstage -n backstage` 重新載入環境變數；若 Argo CD 共用該 PAT，也要重跑下方的複製指令。Grafana 的 Secret 僅用於初始化管理員密碼，初始化後請透過 Grafana 修改密碼。

Backstage Kubernetes plugin 使用 Pod 的 in-cluster ServiceAccount 與 CA，不需要手動準備 Kubernetes token。RoleBinding 只允許它唯讀查詢 `todo`，不允許讀取 Secret 或寫入 workload。

若 Git repository 是私有的，Argo CD 也需要讀取權限。以下從剛建立的 Secret 讀取 PAT，直接送入 Argo CD 的 repository Secret，不在終端機顯示 token：

```bash
(
set -eo pipefail
kubectl get secret backstage-github -n backstage -o jsonpath='{.data.token}' |
  base64 --decode |
  kubectl create secret generic todo-full-repository -n argocd \
    --from-literal=type=git \
    --from-literal=url=https://github.com/yrw9281/IT30.Platform.Engineering.git \
    --from-literal=username=x-access-token \
    --from-file=password=/dev/stdin \
    --dry-run=client -o yaml | kubectl apply -f -
kubectl label secret todo-full-repository -n argocd \
  argocd.argoproj.io/secret-type=repository --overwrite
)
```

教學環境可共用這個限定 repository 的 PAT；正式環境應分開提供 Argo CD 唯讀 Git 憑證與 Backstage 的 PR 寫入憑證。

### 5. 安裝可觀測性、Operator 與 Backstage

```bash
kubectl apply -k observability
kubectl apply -k operator
kubectl apply -k backstage

kubectl rollout status deployment/otel-collector -n observability --timeout=300s
kubectl rollout status deployment/prometheus -n observability --timeout=300s
kubectl rollout status deployment/loki -n observability --timeout=300s
kubectl rollout status deployment/tempo -n observability --timeout=300s
kubectl rollout status deployment/grafana -n observability --timeout=300s
kubectl rollout status deployment/microservice-operator -n todo --timeout=300s
kubectl rollout status deployment/backstage -n backstage --timeout=300s
```

### 6. 交給 GitOps 建立 Todo

確認新的設定已存在遠端 `main`，再建立 ApplicationSet。不要再以 `kubectl apply -k config/...` 維護同一組資源。

```bash
kubectl apply -k gitops
kubectl wait --for=condition=ResourcesUpToDate \
  applicationset/todo-full -n argocd --timeout=300s
kubectl get applications -n argocd
kubectl wait --for=jsonpath='{.status.sync.status}'=Synced \
  application/todo-full-runtime application/todo-full-api -n argocd --timeout=300s
kubectl wait --for=jsonpath='{.status.health.status}'=Healthy \
  application/todo-full-runtime application/todo-full-api -n argocd --timeout=300s
kubectl get microservice todo-api -n todo -o yaml
kubectl get deployment,service,ingress -n todo
```

請分別等待三個狀態：`ResourcesUpToDate` 確認 Application 已建立或更新，`Synced` 確認設定與 Git 一致，`Healthy` 回報工作負載健康。設定同步後仍可能發生 image 拉取失敗。同步錯誤請查 Application 的 conditions、來源路徑與 revision；健康錯誤請查 CR generation、conditions、Operator 日誌與 Pod 事件：

```bash
kubectl describe applicationset todo-full -n argocd
kubectl describe application todo-full-runtime -n argocd
kubectl describe application todo-full-api -n argocd
kubectl logs deployment/microservice-operator -n todo --tail=100
kubectl get pods -n todo
kubectl get events -n todo --sort-by=.metadata.creationTimestamp
```

若 conditions 顯示 `authentication required` 或 `Repository not found`，先確認 repository URL、PAT 的 repository 授權與第 4 節的 Argo CD repository Secret；GitHub 對未授權的私有 repository 也會回傳「找不到」。更新憑證後，可要求 Argo CD 重新讀取 Git：

```bash
kubectl annotate application todo-full-runtime todo-full-api -n argocd \
  argocd.argoproj.io/refresh=hard --overwrite
```

ApplicationSet 關閉自動 prune，刪除時也會保留資源，以避免誤清教學環境。移除操作須另行審查：刪除 CR 仍會透過 owner references 回收 Todo API 的子資源。

## 操作入口與資料流

各入口預設只提供 ClusterIP／NodePort，不公開 Backstage Guest 入口：

```bash
kubectl port-forward -n ingress-nginx service/ingress-nginx-controller 8080:80
# 在另一個終端機；瀏覽器可開啟 http://todo.localhost:8080
curl --noproxy '*' --fail --max-time 15 \
  -H 'Host: todo.localhost' http://127.0.0.1:8080/api/todos

kubectl port-forward -n observability service/grafana 3000:3000
kubectl port-forward -n backstage service/backstage 7007:7007
kubectl port-forward -n argocd service/argocd-server 8443:443
kubectl port-forward -n observability service/prometheus 9090:9090
```

Port-forward 各自在不同終端機執行，只綁定本機位址；終端機關閉或所選 Pod 被替換時，需重新執行。Grafana 用 `admin` 與剛設定的密碼登入；Backstage 使用 `http://localhost:7007`，避免與其 base URL 不一致；Argo CD 使用 `https://localhost:8443`，教學環境的自簽憑證需要在瀏覽器確認。Prometheus 使用 `http://localhost:9090`。Loki 與 Tempo 的查詢入口在 Grafana Explore，不另提供前端。

若 `kubectl` 執行在遠端主機，這些 `localhost` 指向遠端。可在 VS Code 的 Ports 面板將 `8080`、`3000`、`7007`、`8443`、`9090` 轉發到自己的電腦，並保留相同的本機 port，尤其 Backstage 的 `7007`。不要改成綁定 `0.0.0.0` 來公開 Guest 入口。

具權限者可在自己的終端機讀取登入密碼；不要將輸出貼到公開紀錄：

```bash
kubectl get secret grafana-admin -n observability \
  -o jsonpath='{.data.password}' | base64 --decode; printf '\n'
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath='{.data.password}' | base64 --decode; printf '\n'
```

Todo 流量為 Browser → Ingress → BFF → Todo API。API 與 BFF 將 OTLP 送到 Collector，Metrics 由 Prometheus scrape，Logs 送 Loki，Traces 送 Tempo；Grafana 已載入 dashboard 與 Trace-to-Logs 關聯。Collector 保留 `debug` exporter，僅適合受控教學環境。

新增待辦、勾選完成並重新整理列表以產生流量，再開啟 Grafana 的 `Todo service overview` 儀表板。SDK 匯出、Prometheus 擷取與初次顯示 `rate` 圖表可能需要一至兩分鐘。若圖表持續空白，請保持 Prometheus port-forward，從另一個終端機確認 API 與 BFF 的 HTTP 指標：

```bash
curl --noproxy '*' --fail --max-time 15 --get \
  --data-urlencode 'query=sum by (service_name) (http_server_request_duration_seconds_count{service_name=~"todo-api|todo-bff"})' \
  http://127.0.0.1:9090/api/v1/query
```

回應應為 `status: success`，且 `data.result` 同時包含 `service_name: todo-api` 與 `todo-bff`；只有 `success` 而結果為空，還不能確認遙測資料已送達。在 Explore 選擇 Loki，以 `{service_name="todo-api"}` 查詢日誌；選擇 Tempo 查詢追蹤，並透過 Trace-to-Logs 查看相關日誌，確認同一個 trace ID 能對應到 API 與 BFF 的 spans 及 API 日誌。

在 Backstage 的 `Create` 模板填入 API CI 產出的新 64 位 digest（不含 `sha256:`），提出換版 PR。image 須已發布且可由叢集拉取，digest 也須與目前值不同。審查並合併後，Argo CD 同步 CR，Operator 更新工作負載。請確認 Application 的 `.status.sync.revision` 對應合併後的 commit，Microservice 的 `status.observedGeneration` 與 Ready condition 的 `observedGeneration` 都等於 `metadata.generation`，再確認 Ready 為 `True`，避免把舊的 Healthy 結果當成本次換版結果。

## CI 與重新建置 image

將 `ci/platform.yaml` 複製到 `.github/workflows/`，GitHub Actions 才會執行。從 repository 根目錄執行：

```bash
mkdir -p .github/workflows
cp src/final/ci/platform.yaml .github/workflows/platform-full.yaml
```

將 workflow 與 `src/final/` 一起提交，並在 `main` 要求檢查通過與人工審查。Workflow 會檢查渲染、重複資源、CRD schema，以及 Todo API 的固定設定、image repository 與 digest，再建置兩個 .NET 專案與四個 image；PR 建置不推送 image。

`platform-v*` tag 或手動執行會推送 API、BFF、Web、Backstage image，並在 job summary 記錄 digest。手動執行請選 `main`，因為 ref 名稱會直接成為 image tag，不能包含 `/`。部署設定與 PR 合併仍由審查者處理，並核對各 image 的 CI 身分、來源及部署核准。

已發布的初始 image 可直接用來啟動教學環境。要由這份來源重新建置，可以使用：

```bash
docker build -t ghcr.io/yrw9281/it30-todo-api:full src/final/services/Todo.Api
docker build -t ghcr.io/yrw9281/it30-todo-bff:full src/final/services/Todo.Bff
docker build -t ghcr.io/yrw9281/it30-todo-web:full src/final/services/WebApp
docker build -t ghcr.io/yrw9281/it30-idp-backstage:full src/final/backstage/app
```

從儲存庫根目錄執行建置，需要啟用 BuildKit，並能連到 Microsoft Container Registry、NuGet、Debian 套件來源與 npm registry。登入 GHCR 並推送後，以已發布的 digest 更新 API CR，再更新 BFF／Web 的 Git 設定與 Backstage Deployment image。Backstage Dockerfile 會安裝依賴、檢查型別並打包前後端，不需要本機的 `node_modules` 或預先建好的 bundle。

一般網路環境不需要額外提供 CA。若 API／BFF 建置在 `dotnet restore` 出現 `NU1301`，請先確認建置容器能連到 NuGet；企業 HTTPS proxy 的自有 CA 未受容器信任，也可能造成這個錯誤，應由該環境的建置基底或 CI 設定處理，不應關閉 TLS 驗證。

Backstage Dockerfile 另有選用的 `build-ca` secret 支援。若企業 HTTPS proxy 使用自有 CA，且主機的系統 CA bundle 已信任它，可使用下列指令；Linux 以外的系統請替換為實際的 PEM bundle 路徑。不將 CA 加進 repository 或 runtime image：

```bash
docker build --secret id=build-ca,src=/etc/ssl/certs/ca-certificates.crt \
  -t ghcr.io/yrw9281/it30-idp-backstage:full src/final/backstage/app
```

## 版本與限制

`bootstrap/*/install.yaml` 保存下列 Apache-2.0 專案的官方安裝 manifest。升級時替換為目標版本，並檢查既有 patch 是否仍適用；不要同時用 Helm 與這份 manifest 管理同名 controller。

| 元件 | 版本 | 原始來源 |
| --- | --- | --- |
| Argo CD | `v3.1.8` | [manifest](https://github.com/argoproj/argo-cd/blob/v3.1.8/manifests/install.yaml)、[LICENSE](https://github.com/argoproj/argo-cd/blob/v3.1.8/LICENSE) |
| ingress-nginx | `controller-v1.14.1` | [bare-metal manifest](https://github.com/kubernetes/ingress-nginx/blob/controller-v1.14.1/deploy/static/provider/baremetal/deploy.yaml)、[LICENSE](https://github.com/kubernetes/ingress-nginx/blob/controller-v1.14.1/LICENSE) |
| Gatekeeper | `v3.20.1` | [manifest](https://github.com/open-policy-agent/gatekeeper/blob/v3.20.1/deploy/gatekeeper.yaml)、[LICENSE](https://github.com/open-policy-agent/gatekeeper/blob/v3.20.1/LICENSE) |

`ingress-nginx` 專案[已宣布於 2026 年 3 月退休](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)，這份快照只供受控教學環境使用；新生產平台應評估受維護的替代方案。

Argo CD 官方安裝帶有廣泛的叢集存取權。AppProject 限制 Application 的來源與目標；若要隔離團隊，仍須另外限制 Argo CD ServiceAccount 的 Namespace 權限。

Todo API 以單副本執行，換版或重啟會遺失記憶體資料。加入共享儲存前請維持單副本，否則查詢與更新可能落到沒有該筆待辦事項的 Pod。BFF 則執行兩個副本。

可觀測性元件與 Backstage SQLite 使用 `emptyDir`，Pod 重建會遺失遙測、Catalog 資料與任務歷史。Catalog 項目及模板會從宣告重新載入，過去的任務歷史則不會恢復。

Backstage 保留 Guest 登入與 allow-all permission policy，只能在受控的本機入口操作。Catalog 的 owner／label 不是使用者授權；正式部署必須補上身分驗證、細分權限、持久化、TLS、備份與 image pull／Git credential 管理。

Backstage Catalog 的 Kubernetes 頁面依 `app=todo-api` 等 label 查詢資源現況，不查詢 Microservice conditions，也不提供完整交付歷史。Gatekeeper 拒絕 Operator 建立／更新的原生 workload 時，需查看 Operator log 與重試情況。

Argo CD 健康檢查會比對外層與 condition 的 generation，判斷依據是目前 CR status。完整的 PR → merge → sync → rollout 流程與政策允許／拒絕結果，須在實際叢集驗證，無法只靠 YAML 渲染確認。
