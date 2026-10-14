# 在乾淨 Cluster 建立完整平台

請準備一個**乾淨、可連線的 Kubernetes Cluster**，依序安裝 Todo、Argo CD、OpenTelemetry、Backstage 與 Gatekeeper。部署設定、必要的程式碼與 image 建置來源都在這份目錄內。

乾淨 Cluster 可以已有 CNI、CoreDNS 等 Kubernetes 基礎元件，但不應已有本平台使用的 Namespace、CRD、Argo CD、Ingress Controller、Gatekeeper 或 Todo 工作負載。以下指令不處理既有平台的升級、接管或遷移，也不會刪除叢集中的資源。

## 目錄與管理責任

| 目錄 | 內容與唯一管理來源 |
| --- | --- |
| `foundation/` | 四個 Namespace 與 `Microservice` CRD |
| `bootstrap/` | 固定版本的 Argo CD、NGINX Ingress Controller、Gatekeeper；各自只保存一份官方安裝 manifest |
| `observability/` | Collector、Prometheus、Loki、Tempo、Grafana、datasource 與 dashboard |
| `operator/` | Kopf handler、資源展開、健康回報、RBAC 與 Deployment；Kustomize 產生程式碼 ConfigMap |
| `backstage/` | Catalog、單一 PR 模板、Kubernetes 唯讀權限、Deployment 與可獨立建置的最小 Backstage App |
| `config/runtime/` | BFF、Web、Ingress，交給 `todo-full-runtime` Application 管理 |
| `config/todo-api/` | 唯一一筆 Todo API `Microservice`，交給 `todo-full-api` Application 管理 |
| `gitops/` | AppProject 與產生上述兩個 Application 的 ApplicationSet |
| `policy/` | 三個 ConstraintTemplate 與三個 Constraint，安裝時分兩階段 |
| `services/` | Todo API、BFF、Web 的原始碼與 Dockerfile |
| `ci/` | GitHub Actions workflow；須放到 GitHub 指定的位置才會執行 |

Todo API 的 Deployment／Service 由 Operator 建立，不另寫進 Git。BFF 與 Web 由 Argo CD 同步原生資源；兩個 controller 不會管理同一份 Todo API Deployment。

Namespace 只在 `foundation/` 宣告；`ingress-nginx` 與 `gatekeeper-system` 由各自的官方 manifest 建立。ConfigMap generator 保留名稱 hash，修改程式碼或 Backstage 設定後重新 `apply -k`，會更新 Pod template；舊 hash ConfigMap 不會自動刪除。

## 開始前

準備可存取該 Cluster 的 kubeconfig、管理者權限，以及含 Kustomize 的 `kubectl`。叢集需能存取 GHCR、Docker Hub、`registry.k8s.io`、`quay.io` 與 PyPI，Argo CD 需能讀取 GitHub；Operator init container 會安裝固定版本的 Kopf／Kubernetes client。建立 Cluster 的方式不限定。

先確認 context 指向這個乾淨 Cluster，Node 全部為 `Ready`；context 不正確或有 Node 尚未就緒時，先處理再繼續：

```bash
kubectl config current-context
kubectl cluster-info
kubectl get nodes
```

這份設定供測試叢集使用，平台 Pod 帶有 control-plane 的 `NoSchedule` toleration，可使用 worker 與 control-plane 的剩餘容量，但不移除節點 taint。共用設定在 `bootstrap/scheduling/`；Operator 產生的 Todo API Pod 也帶有同樣的 toleration。正式環境應使用足夠的專用 worker，移除各 Kustomization 的 scheduling component 與 Operator 內對應設定。Node 為 `Ready` 不代表還有容量，若 Pod 停在 `Pending`，請查看 `kubectl describe pod` 的排程事件。

預設使用本 repository 的 `main`：

- Argo CD 讀取 `src-full/config/runtime` 與 `src-full/config/todo-api`。
- Backstage PR 只寫入 `src-full/config/todo-api`。
- image 使用 `ghcr.io/yrw9281/it30-todo-*`，Backstage 使用 `it30-idp-backstage:demo`。

**先將這份目錄提交並推送到 `main`，再啟用 GitOps。** Argo CD 讀取遠端 Git，不讀本機工作目錄。改用 fork 時，須一併修改 `gitops/project.yaml`、`gitops/applicationset.yaml`、`backstage/templates/template.yaml` 的 repository 設定。若也換 image repository，還須修改 workload image、模板 skeleton、image policy 與 CI 的檢查／發佈目的地。

預設 image 必須可由叢集匿名拉取；私有 package 需自行提供 image pull credential。Operator 產生的 Pod 沒有 `imagePullSecrets`，可在 `todo` 的 `default` ServiceAccount 設定；BFF／Web 也使用它。Backstage 使用自己的 `backstage` ServiceAccount，需另行授權。不要將 registry credential 提交 Git。

## 安裝順序

所有指令從 `src-full/` 執行。不使用 `kubectl apply -R -f .`：目錄裡有 Kustomize 設定、Backstage Catalog／Template、應用程式設定與 workflow，它們不是 Kubernetes API 資源。CRD 與 webhook 也必須先完成註冊，才能提交依賴它們的資源，因此沒有將所有階段塞進一份根目錄 Kustomization。

### 1. 建立 Namespace 與 CRD

```bash
cd src-full
kubectl config current-context
kubectl apply --server-side -k foundation
kubectl wait --for=condition=Established \
  crd/microservices.platform.example.io --timeout=120s
```

### 2. 安裝 controller

Argo CD 與 Gatekeeper 的 CRD 較大，使用 server-side apply，避免超過 client-side apply 的 annotation 大小限制。

Argo CD 的 Redis 保留官方版本 `7.2.7-alpine`，改從 Docker Hub 拉取，避免環境無法連線至 ECR Public。Ingress 的 admission Job 完成後保留 10 分鐘，讓下方的 `kubectl wait` 能確認結果；官方預設立即清除 Job，可能在查詢前就已不存在。

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

先提交 Template，等 Gatekeeper 產生對應的 CRD，再提交 Constraint。

```bash
kubectl apply --server-side -k policy/templates
kubectl wait --for=create \
  crd/k8sdeploymentnoprivileged.constraints.gatekeeper.sh \
  crd/k8sdeploymentrequiredlimits.constraints.gatekeeper.sh \
  crd/k8smicroserviceimagepolicy.constraints.gatekeeper.sh --timeout=180s
kubectl wait --for=condition=Established \
  crd/k8sdeploymentnoprivileged.constraints.gatekeeper.sh \
  crd/k8sdeploymentrequiredlimits.constraints.gatekeeper.sh \
  crd/k8smicroserviceimagepolicy.constraints.gatekeeper.sh --timeout=180s
kubectl apply --server-side -k policy/constraints
```

政策只匹配 `todo` Namespace：privileged 為 `deny`、limits 為 `dryrun`、image 來源／digest 為 `warn`。只有 privileged 會拒絕違規請求；limits 用於 audit 盤點，image 違規則回傳警告。需要強制拒絕時，修改 `policy/constraints/constraints.yaml` 的 `enforcementAction`，確認允許／拒絕結果後再重新套用。

政策檢查的是 Deployment 或 Microservice，不涵蓋直接提交的 Pod、StatefulSet 等其他 workload。官方 Gatekeeper validation webhook 的 `failurePolicy: Ignore` 在 webhook 無法連線時會放行，不是 fail-closed 的生產權限邊界。

### 4. 提供必要憑證

Grafana 密碼與 GitHub token 不寫進 manifest。以下指令從終端機輸入，值不出現在 shell history；不要開啟 `set -x`。PAT 只授權這個 repository 的 Contents／Pull requests 讀寫，不給 workflow、叢集或組織管理權限。GitHub repository 必須允許建立 PR。

```bash
set -euo pipefail
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
```

Backstage Kubernetes plugin 使用 Pod 的 in-cluster ServiceAccount 與 CA，不需要手動準備 Kubernetes token。RoleBinding 只允許它唯讀查詢 `todo`，不允許讀取 Secret 或寫入 workload。

若 Git repository 是私有的，Argo CD 也需要讀取權限。以下從剛建立的 Secret 讀取 PAT，直接送入 Argo CD 的 repository Secret，不在終端機顯示 token：

```bash
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
kubectl wait --for=create \
  application/todo-full-runtime application/todo-full-api -n argocd --timeout=300s
kubectl get applications -n argocd
kubectl wait --for=jsonpath='{.status.sync.status}'=Synced \
  application/todo-full-runtime application/todo-full-api -n argocd --timeout=300s
kubectl wait --for=jsonpath='{.status.health.status}'=Healthy \
  application/todo-full-runtime application/todo-full-api -n argocd --timeout=300s
kubectl get microservice todo-api -n todo -o yaml
kubectl get deployment,service,ingress -n todo
```

同步失敗時查看 Application 的 conditions、source path 與 revision；健康失敗時查看 CR generation、conditions、Operator log 與 Pod event。`Synced` 不代表 image 拉取成功，可用以下指令定位問題：

```bash
kubectl describe applicationset todo-full -n argocd
kubectl describe application todo-full-runtime -n argocd
kubectl describe application todo-full-api -n argocd
kubectl logs deployment/microservice-operator -n todo --tail=100
kubectl get pods -n todo
kubectl get events -n todo --sort-by=.metadata.creationTimestamp
```

ApplicationSet 沒有啟用自動 prune，也保留刪除 ApplicationSet 時的資源。這是避免誤刪教學環境的設定，**不等於自動清理**；移除 CR 會透過 owner references 刪除 Todo API 的子資源，應另外 review 刪除操作。

## 操作入口與資料流

各入口預設只提供 ClusterIP／NodePort，不公開 Backstage Guest 入口：

```bash
kubectl port-forward -n ingress-nginx service/ingress-nginx-controller 8080:80
# 在另一個終端機；瀏覽器可開啟 http://todo.localhost:8080
curl --fail -H 'Host: todo.localhost' http://127.0.0.1:8080/api/todos

kubectl port-forward -n observability service/grafana 3000:3000
kubectl port-forward -n backstage service/backstage 7007:7007
kubectl port-forward -n argocd service/argocd-server 8443:443
```

Port-forward 各自在不同終端機執行。Grafana 用 `admin` 與剛設定的密碼登入；Backstage 使用 `http://localhost:7007`，避免與其 base URL 不一致；Argo CD 使用 `https://localhost:8443`，初始 admin 密碼需由具權限者讀取 `argocd-initial-admin-secret`，不要將輸出貼到公開紀錄。

Todo 流量為 Browser → Ingress → BFF → Todo API。API 與 BFF 將 OTLP 送到 Collector，Metrics 由 Prometheus scrape，Logs 送 Loki，Traces 送 Tempo；Grafana 已載入 dashboard 與 Trace-to-Logs 關聯。Collector 保留 `debug` exporter，僅適合受控教學環境。

Backstage 的 `Create` 只有正式換版模板。填入 API CI 產出的 64 位 digest（不含 `sha256:`），模板提出 PR，review／merge 後由 Argo CD 同步 CR，再由 Operator 建立／更新工作負載。Catalog 的 Kubernetes 頁面查詢 `app=todo-api` 等 label，不查詢 Microservice conditions，也不保存交付事件時間線。

## CI 與重新建置 image

GitHub 只會執行 `.github/workflows/` 裡的 workflow；`ci/platform.yaml` 是唯一保存的安裝來源，不能靠 Kubernetes apply 啟用它。從 repository 根目錄執行：

```bash
mkdir -p .github/workflows
cp src-full/ci/platform.yaml .github/workflows/platform-full.yaml
```

將 workflow 與 `src-full/` 一起提交，再為 `main` 設定 required checks 與人工 review。Workflow 檢查渲染、資源唯一性、CRD schema、Todo API 的固定合約／repository／digest，建置兩個 .NET 專案與四個 image；PR 只建置，不推送。

`platform-v*` tag 或手動執行會推送 API、BFF、Web、Backstage image，並在 job summary 輸出 digest。Workflow 不修改部署設定、不自動合併 PR；image digest 對應的 CI 身分／來源與是否允許 promotion 仍需 review，不是只驗證格式就算供應鏈驗證完成。

已發布的初始 image 可直接用來啟動教學環境。要由這份來源重新建置，可以使用：

```bash
docker build -t ghcr.io/yrw9281/it30-todo-api:full src-full/services/Todo.Api
docker build -t ghcr.io/yrw9281/it30-todo-bff:full src-full/services/Todo.Bff
docker build -t ghcr.io/yrw9281/it30-todo-web:full src-full/services/WebApp
docker build -t ghcr.io/yrw9281/it30-idp-backstage:full src-full/backstage/app
```

這組建置指令從 repository 根目錄執行。自行登入 GHCR 並推送後，以實際 digest 更新 API CR，更新 BFF／Web 的 Git 設定與 Backstage Deployment 的 image。不要把不存在的 digest 填進 CR。Backstage Dockerfile 內含安裝、型別檢查與 backend／frontend 打包，不需要先在本機安裝 `node_modules` 或準備 bundle。

如果企業 HTTPS proxy 使用自有 CA，且主機的系統 CA bundle 已信任它，可在 Backstage 建置時傳入 BuildKit secret。不將 CA 加進 repository 或 runtime image，也不關閉 TLS 驗證：

```bash
docker build --secret id=build-ca,src=/etc/ssl/certs/ca-certificates.crt \
  -t ghcr.io/yrw9281/it30-idp-backstage:full src-full/backstage/app
```

## 版本與限制

`bootstrap/*/install.yaml` 是下列 Apache-2.0 專案的官方 manifest 快照，沒有另存一套 Helm chart 或渲染副本。升級時替換同一份快照並重新檢查既有 patch；不要同時用 Helm 與這份 manifest 管理同名 controller。

| 元件 | 版本 | 原始來源 |
| --- | --- | --- |
| Argo CD | `v3.1.8` | [manifest](https://github.com/argoproj/argo-cd/blob/v3.1.8/manifests/install.yaml)、[LICENSE](https://github.com/argoproj/argo-cd/blob/v3.1.8/LICENSE) |
| ingress-nginx | `controller-v1.14.1` | [bare-metal manifest](https://github.com/kubernetes/ingress-nginx/blob/controller-v1.14.1/deploy/static/provider/baremetal/deploy.yaml)、[LICENSE](https://github.com/kubernetes/ingress-nginx/blob/controller-v1.14.1/LICENSE) |
| Gatekeeper | `v3.20.1` | [manifest](https://github.com/open-policy-agent/gatekeeper/blob/v3.20.1/deploy/gatekeeper.yaml)、[LICENSE](https://github.com/open-policy-agent/gatekeeper/blob/v3.20.1/LICENSE) |

`ingress-nginx` 專案[已宣布於 2026 年 3 月退休](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)，這份快照只供受控教學環境使用；新生產平台應評估受維護的替代方案。

Argo CD 官方安裝帶有廣泛的叢集存取權。AppProject 限制此處 Application 的來源與目標，不代表 Argo CD ServiceAccount 已達 Namespace 級最小權限，也不代表完整團隊隔離。

Todo API 的兩個副本各自保存記憶體型資料，彼此不共享，換版／重啟會遺失；因此 Pod／endpoint 就緒不保證 Todo 操作的資料一致性。Observability 與 Backstage SQLite 使用 `emptyDir`，重建 Pod 會失去遙測、Catalog／task 資料；Catalog 與模板會從宣告重新載入，但過去 task 紀錄不會恢復。

Backstage 保留 Guest 登入與 allow-all permission policy，只能在受控的本機入口操作。Catalog 的 owner／label 不是使用者授權；正式部署必須補上身分驗證、細分權限、持久化、TLS、備份與 image pull／Git credential 管理。

Gatekeeper 拒絕原生 workload 時，錯誤會出現在 Operator log 與重試，不會自動整理成完整的 Backstage 交付歷史。Argo CD health patch 會檢查外層與 condition 的 generation，仍只能根據目前 CR status 判斷。整條 PR → merge → sync → rollout 與政策允許／拒絕結果，必須在實際叢集逐段驗證，不能只用 YAML 渲染成功宣稱端到端部署成功。
