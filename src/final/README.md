[English](README.md) | [繁體中文](README-zh-TW.md)

# Build the complete platform on a clean cluster

This directory contains the code, image build sources, and configuration for installing Todo, Argo CD, OpenTelemetry, Backstage, and Gatekeeper on a clean, reachable Kubernetes cluster. Follow the installation order below.

A clean cluster may already have Kubernetes infrastructure such as a CNI and CoreDNS, but should not have this platform's namespaces, CRD, Argo CD, Ingress Controller, Gatekeeper, or Todo workloads. These instructions do not upgrade, adopt, or migrate an existing platform, and do not delete cluster resources.

## Directories and ownership

| Directory | Contents |
| --- | --- |
| `foundation/` | Four namespaces and the `Microservice` CRD |
| `bootstrap/` | Pinned Argo CD, NGINX Ingress Controller, and Gatekeeper installations |
| `observability/` | Collector, Prometheus, Loki, Tempo, Grafana, datasources, and dashboard |
| `operator/` | Kopf handlers, resource generation, health reporting, RBAC, and Deployment; Kustomize generates the code ConfigMap |
| `backstage/` | Catalog, one PR template, read-only Kubernetes permissions, Deployment, and a minimal independently buildable Backstage app |
| `config/runtime/` | BFF, Web, and Ingress, managed by the `todo-full-runtime` Application |
| `config/todo-api/` | The single Todo API `Microservice`, managed by the `todo-full-api` Application |
| `gitops/` | AppProject and an ApplicationSet that generates those two Applications |
| `policy/` | Three ConstraintTemplates and three Constraints, installed in two stages |
| `services/` | Todo API, BFF, and Web source code and Dockerfiles |
| `ci/` | GitHub Actions workflow; it runs only after being placed in GitHub's required location |

The Operator owns Todo API's Deployment and Service, which are not separately declared in Git. Argo CD manages the native BFF and Web resources.

Platform namespaces are declared only in `foundation/`; the official installation manifests create `ingress-nginx` and `gatekeeper-system`. ConfigMap generators retain name hashes. After editing code or Backstage configuration, rerun `apply -k` to update the Pod template. Old hashed ConfigMaps are not automatically deleted.

## Prerequisites

You need a kubeconfig with administrator access, Bash or Zsh, and `kubectl` with Kustomize support. Keep `kubectl` within one minor version of the API server; for Kubernetes `1.30`, use `kubectl 1.29` through `1.31`. The cluster needs access to GHCR, Docker Hub, `registry.k8s.io`, `quay.io`, `public.ecr.aws`, and PyPI. Argo CD reads GitHub, and the Operator init container installs pinned Kopf and Kubernetes client versions from PyPI. Any cluster creation method is acceptable.

Confirm the context points to the clean cluster and every Node is `Ready` before continuing:

```bash
kubectl config current-context
kubectl version
kubectl cluster-info
kubectl get nodes
```

For test clusters, platform Pods tolerate the control-plane `NoSchedule` taint so they can use spare capacity on workers and control-plane nodes without changing taints. The shared settings are in `bootstrap/scheduling/`; Operator-generated Todo API Pods use the same toleration. For production, provision dedicated workers and remove the scheduling components and corresponding Operator setting. Even on a `Ready` Node, a Pod may be `Pending` due to capacity; inspect scheduling events with `kubectl describe pod`.

Defaults use this repository's `main` branch:

- Argo CD reads `src/final/config/runtime` and `src/final/config/todo-api`.
- Backstage PRs write only to `src/final/config/todo-api`.
- Application images use `ghcr.io/yrw9281/it30-todo-*`; Backstage uses `it30-idp-backstage:demo`.

Argo CD reads remote Git, so commit and push this directory to `main` before enabling GitOps. For a fork, update the repository settings in `gitops/project.yaml`, `gitops/applicationset.yaml`, and `backstage/templates/template.yaml`. Changing image repositories also requires updates to workload images, the template skeleton, image policy, and CI validation and publishing destinations.

The cluster must be able to pull the default images anonymously. For private packages, configure pull credentials on the `default` ServiceAccount in `todo`, used by Todo API, BFF, and Web; Operator-generated Pods do not declare `imagePullSecrets`. Authorize Backstage's separate `backstage` ServiceAccount as well. Keep registry credentials out of Git.

## Installation order

Run the following steps in order from `src/final/`, allowing CRDs and webhooks to become ready before applying dependent resources. Do not use `kubectl apply -R -f .`: this directory also contains configuration files and templates that cannot be submitted directly to the Kubernetes API.

### 1. Create namespaces and the CRD

```bash
cd src/final
kubectl config current-context
kubectl apply --server-side -k foundation
kubectl wait --for=condition=Established \
  crd/microservices.platform.example.io --timeout=120s
```

### 2. Install controllers

Argo CD and Gatekeeper have large CRDs. Use server-side apply to avoid the annotation size limit of client-side apply.

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

Ingress uses the official bare-metal NodePort Service and does not need a cloud LoadBalancer. Later steps access Todo with port-forwarding, so you do not need to configure node host ports.

### 3. Register policies

Submit Templates first. Wait for Gatekeeper to report creation and for the corresponding CRDs to become established, then submit Constraints. The JSONPath wait avoids relying on `--for=create`, which older `kubectl` versions do not support.

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

Policies match only `todo`: the privileged policy rejects violations with `deny`, limits are audited with `dryrun`, and image source/digest violations return `warn` warnings. To enforce the latter two, change `enforcementAction` in `policy/constraints/constraints.yaml` after testing allowed and rejected cases, then reapply.

Policies inspect Deployments or Microservices; directly submitted Pods, StatefulSets, and other workloads are outside their scope. The official Gatekeeper validation webhook uses `failurePolicy: Ignore`, so requests pass if it is unreachable. Account for this fail-open behavior in production access controls.

### 4. Supply credentials

Create the Grafana password and GitHub token as Secrets using hidden input in Bash or Zsh. Values stay out of manifests and shell history; keep `set -x` off. Parentheses confine error-handling options to a subshell, leaving your terminal and VS Code shell integration unchanged. Give the PAT only read/write Contents and Pull requests permissions for this repository, with no workflow, cluster, or organization administration access. The repository must allow PR creation.

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

To correct a value, repeat that Secret's commands; `kubectl apply` updates it in place. After rotating the PAT, reload Backstage's environment with `kubectl rollout restart deployment/backstage -n backstage` and repeat the copy below if Argo CD shares it. Grafana uses its Secret only to initialize the administrator password; change an initialized password through Grafana.

The Backstage Kubernetes plugin uses its Pod's in-cluster ServiceAccount and CA without a manually prepared token. Its RoleBinding allows read-only queries in `todo`, excluding Secrets and workload writes.

For a private Git repository, Argo CD also needs read access. The following reads the PAT from the Secret you just created and pipes it directly into an Argo CD repository Secret without printing it:

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

The tutorial can share this repository-scoped PAT. For production, provide separate read-only Git credentials for Argo CD and PR-writing credentials for Backstage.

### 5. Install observability, the Operator, and Backstage

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

### 6. Let GitOps create Todo

Confirm the new configuration is on remote `main` before creating the ApplicationSet. Do not also maintain the same resources with `kubectl apply -k config/...`.

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

Wait for each stage: `ResourcesUpToDate` confirms the Applications were created or updated, `Synced` confirms their configuration matches Git, and `Healthy` reports workload health. A synchronized configuration can still have image pull failures. For sync errors, inspect Application conditions, source paths, and revisions; for health errors, inspect CR generation and conditions, Operator logs, and Pod events:

```bash
kubectl describe applicationset todo-full -n argocd
kubectl describe application todo-full-runtime -n argocd
kubectl describe application todo-full-api -n argocd
kubectl logs deployment/microservice-operator -n todo --tail=100
kubectl get pods -n todo
kubectl get events -n todo --sort-by=.metadata.creationTimestamp
```

If conditions show `authentication required` or `Repository not found`, check the repository URL, PAT repository authorization, and the Argo CD repository Secret from step 4. GitHub also returns "not found" for unauthorized private repositories. After updating credentials, request a fresh Git read:

```bash
kubectl annotate application todo-full-runtime todo-full-api -n argocd \
  argocd.argoproj.io/refresh=hard --overwrite
```

The ApplicationSet disables automatic pruning and preserves resources on deletion to avoid accidental cleanup. Review removals explicitly: deleting the CR still garbage-collects Todo API child resources through owner references.

## Access points and data flow

Services default to ClusterIP or NodePort. Do not publicly expose Backstage's Guest entry point:

```bash
kubectl port-forward -n ingress-nginx service/ingress-nginx-controller 8080:80
# In another terminal; the browser can use http://todo.localhost:8080
curl --noproxy '*' --fail --max-time 15 \
  -H 'Host: todo.localhost' http://127.0.0.1:8080/api/todos

kubectl port-forward -n observability service/grafana 3000:3000
kubectl port-forward -n backstage service/backstage 7007:7007
kubectl port-forward -n argocd service/argocd-server 8443:443
kubectl port-forward -n observability service/prometheus 9090:9090
```

Run each port-forward in a separate terminal, bound only to local addresses. Restart it if its terminal closes or the selected Pod is replaced. Sign in to Grafana with `admin` and the password you set. Use `http://localhost:7007` for Backstage to match its base URL. Argo CD uses `https://localhost:8443`; acknowledge the tutorial's self-signed certificate in your browser. Prometheus uses `http://localhost:9090`. Query Loki and Tempo through Grafana Explore; neither has a separate frontend here.

If `kubectl` runs on a remote host, `localhost` refers to that host. In VS Code's Ports panel, forward `8080`, `3000`, `7007`, `8443`, and `9090` to your own computer, keeping the same local port numbers, especially Backstage's `7007`. Do not bind to `0.0.0.0` to expose the Guest entry point.

Authorized users can read login passwords in their own terminal. Do not paste the output into public records:

```bash
kubectl get secret grafana-admin -n observability \
  -o jsonpath='{.data.password}' | base64 --decode; printf '\n'
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath='{.data.password}' | base64 --decode; printf '\n'
```

Todo traffic follows Browser → Ingress → BFF → Todo API. The API and BFF send OTLP to the Collector. Prometheus scrapes metrics, Loki receives logs, and Tempo receives traces. Grafana provisions the dashboard and Trace-to-Logs correlation. The Collector retains a `debug` exporter for controlled tutorial environments only.

Add todos, mark them complete, and refresh the list to generate traffic, then open Grafana's `Todo service overview` dashboard. Allow one or two minutes for SDK export, Prometheus scraping, and initial `rate` charts. If charts remain empty, keep the Prometheus port-forward running and check HTTP metrics for both services from another terminal:

```bash
curl --noproxy '*' --fail --max-time 15 --get \
  --data-urlencode 'query=sum by (service_name) (http_server_request_duration_seconds_count{service_name=~"todo-api|todo-bff"})' \
  http://127.0.0.1:9090/api/v1/query
```

The response should have `status: success`, with both `service_name: todo-api` and `todo-bff` in `data.result`. A successful response with an empty result does not confirm telemetry delivery. In Explore, select Loki and query `{service_name="todo-api"}`. Select Tempo to query traces, then use Trace-to-Logs to confirm the same trace ID links API and BFF spans to API logs.

In Backstage's `Create` template, enter a new 64-character digest from API CI, without `sha256:`, to propose an image-update PR. The image must be published and pullable, and the digest must differ from the current value. After review and merge, Argo CD synchronizes the CR and the Operator updates workloads. Check that the Application's `.status.sync.revision` matches the merged commit, and that the Microservice's `status.observedGeneration` and Ready condition's `observedGeneration` both match `metadata.generation`, before accepting `Ready=True`. These checks distinguish the new rollout from an old Healthy result.

## CI and rebuilding images

Copy `ci/platform.yaml` into `.github/workflows/` for GitHub Actions to run it. From the repository root:

```bash
mkdir -p .github/workflows
cp src/final/ci/platform.yaml .github/workflows/platform-full.yaml
```

Commit the workflow with `src/final/` and require checks and human review on `main`. It checks rendering, duplicate resources, the CRD schema, and Todo API's fixed settings, image repository, and digest. It also builds two .NET projects and four images; PR builds do not push images.

A `platform-v*` tag or manual run pushes API, BFF, Web, and Backstage images and records digests in the job summary. Select `main` for manual runs: the ref name becomes an image tag, which cannot contain `/`. The workflow leaves deployment changes and PR merges to reviewers, who must verify each image's CI identity, source, and approval for deployment.

The published initial images can start the tutorial environment. To rebuild from this source:

```bash
docker build -t ghcr.io/yrw9281/it30-todo-api:full src/final/services/Todo.Api
docker build -t ghcr.io/yrw9281/it30-todo-bff:full src/final/services/Todo.Bff
docker build -t ghcr.io/yrw9281/it30-todo-web:full src/final/services/WebApp
docker build -t ghcr.io/yrw9281/it30-idp-backstage:full src/final/backstage/app
```

Run these builds from the repository root with BuildKit enabled and access to Microsoft Container Registry, NuGet, Debian package sources, and the npm registry. Log in to GHCR, push the images, and update the API CR with the published digest, BFF/Web Git configuration, and Backstage Deployment image. The Backstage Dockerfile handles dependency installation, type-checking, and backend/frontend packaging, without local `node_modules` or a prebuilt bundle.

Ordinary network environments need no extra CA. If API/BFF `dotnet restore` fails with `NU1301`, first check whether the build container can reach NuGet. An untrusted corporate HTTPS proxy CA can also cause this error. Handle trust in that environment's build base or CI configuration; do not disable TLS verification.

The Backstage Dockerfile also supports an optional `build-ca` secret. If your corporate HTTPS proxy uses a private CA already trusted by the host's system CA bundle, use the following. Outside Linux, replace the path with your actual PEM bundle. The CA is not added to the repository or runtime image:

```bash
docker build --secret id=build-ca,src=/etc/ssl/certs/ca-certificates.crt \
  -t ghcr.io/yrw9281/it30-idp-backstage:full src/final/backstage/app
```

## Versions and limitations

`bootstrap/*/install.yaml` contains official installation manifests from the following Apache-2.0 projects. To upgrade, replace them with the target version and check that existing patches still apply. Do not manage the same controllers with both Helm and these manifests.

| Component | Version | Original source |
| --- | --- | --- |
| Argo CD | `v3.1.8` | [manifest](https://github.com/argoproj/argo-cd/blob/v3.1.8/manifests/install.yaml), [LICENSE](https://github.com/argoproj/argo-cd/blob/v3.1.8/LICENSE) |
| ingress-nginx | `controller-v1.14.1` | [bare-metal manifest](https://github.com/kubernetes/ingress-nginx/blob/controller-v1.14.1/deploy/static/provider/baremetal/deploy.yaml), [LICENSE](https://github.com/kubernetes/ingress-nginx/blob/controller-v1.14.1/LICENSE) |
| Gatekeeper | `v3.20.1` | [manifest](https://github.com/open-policy-agent/gatekeeper/blob/v3.20.1/deploy/gatekeeper.yaml), [LICENSE](https://github.com/open-policy-agent/gatekeeper/blob/v3.20.1/LICENSE) |

The `ingress-nginx` project [announced its retirement in March 2026](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/). This snapshot is only for controlled tutorial environments. Evaluate a maintained alternative for a new production platform.

The official Argo CD installation grants broad cluster access. AppProject restricts Application sources and destinations, but the Argo CD ServiceAccount still needs separate namespace-level permission restrictions for team isolation.

Todo API runs one replica and loses its in-memory data on updates and restarts. Keep it at one replica until shared storage is added; otherwise, reads and updates can reach a Pod without the todo you created. The BFF runs two replicas.

Observability and Backstage SQLite use `emptyDir`. Recreating Pods loses telemetry, Catalog data, and task history. Catalog entries and templates reload from declarations, but old task history does not return.

Backstage retains Guest sign-in and an allow-all permission policy. Use it only through a controlled local entry point. Catalog owners and labels are not user authorization. Production needs authentication, fine-grained permissions, persistence, TLS, backups, and image pull/Git credential management.

The Catalog's Kubernetes page queries current resource state using labels such as `app=todo-api`. It does not query Microservice conditions or provide complete delivery history. If Gatekeeper rejects a native workload created or updated by the Operator, inspect Operator logs and retries.

The Argo CD health patch checks top-level and condition generations using the current CR status. Verify the full PR → merge → sync → rollout sequence and policy allow/reject behavior in a real cluster; YAML rendering alone cannot check them.
