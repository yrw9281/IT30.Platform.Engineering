[English](README.md) | [繁體中文](README-zh-TW.md)

# Backstage and the Microservice Operator

The Day 17-27 examples use Backstage for the Catalog, configuration forms, and Kubernetes queries. The Operator reads `Microservice` resources, manages Todo API's Deployment and Service, and reports status. Run commands from the repository root against an approved test cluster.

## Files and tutorial stages

| Location | Purpose |
| --- | --- |
| `operator/day20/handlers.py` | Create, spec update, and resume handlers that only log input and write `Accepted` |
| `operator/day21/handlers.py`, `operator/resources.py` | Resource creation, updates, and periodic repair; writes `ResourcesApplied` / `Failed` |
| `operator/handlers.py`, `operator/resources.py` | Full Day 22 implementation with rollout, Pod, EndpointSlice, and condition checks |
| `operator/k8s/` | Operator ServiceAccount, RBAC, and Deployment |
| `backstage/app/` | Backstage frontend, backend, and build configuration |
| `backstage/catalog-info.yaml` | Catalog definitions for Todo API, BFF, and Web |
| `backstage/todo-api-dev/` | Day 23 configuration preview, Day 24 PR template, and shared skeleton |
| `backstage/k8s/`, `backstage/k8s-pr/` | Preview deployment and GitHub PR overlay |

## Deploy the Operator

Check the context, existing `todo` namespace, and [CRD](../1-kubernetes/README.md). Before upgrading the CRD, inspect CRs across all namespaces and repair any data that would fail the new schema.

```bash
kubectl config current-context
kubectl get namespace todo
kubectl get crd microservices.platform.example.io
```

The Day 20 version does not manage workloads, so you can deploy it first:

```bash
kubectl create configmap microservice-operator-code -n todo \
  --from-file=handlers.py=src/4-idp/operator/day20/handlers.py \
  --from-file=requirements.txt=src/4-idp/operator/requirements.txt \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f src/4-idp/operator/k8s/rbac.yaml \
  -f src/4-idp/operator/k8s/deployment.yaml
kubectl rollout restart deployment/microservice-operator -n todo
kubectl rollout status deployment/microservice-operator -n todo --timeout=300s
kubectl apply -f src/1-kubernetes/crd/todo-api.yaml
kubectl logs deployment/microservice-operator -n todo -c operator
```

Confirm `Accepted` and the operation's logs. Use the Day 20 port-change exercise only with this version; later versions change the running workload.

### Switch to Day 21 or 22

To let the Operator manage workloads, first stop Argo CD or other controllers from managing the existing Todo API Deployment and Service. Remove those two resources so the Operator can recreate them. Plan for downtime and loss of API in-memory data, and keep Argo CD pruning and self-healing from interfering during the transfer. The Operator reports a conflict if externally owned resources with the same names remain.

For Day 21, use this ConfigMap:

```bash
kubectl create configmap microservice-operator-code -n todo \
  --from-file=handlers.py=src/4-idp/operator/day21/handlers.py \
  --from-file=resources.py=src/4-idp/operator/resources.py \
  --from-file=requirements.txt=src/4-idp/operator/requirements.txt \
  --dry-run=client -o yaml | kubectl apply -f -
```

For Day 22, use this ConfigMap instead, after confirming condition support in the CRD as described in the Kubernetes README:

```bash
kubectl create configmap microservice-operator-code -n todo \
  --from-file=handlers.py=src/4-idp/operator/handlers.py \
  --from-file=resources.py=src/4-idp/operator/resources.py \
  --from-file=requirements.txt=src/4-idp/operator/requirements.txt \
  --dry-run=client -o yaml | kubectl apply -f -
```

After choosing a stage, apply the deployment configuration and restart to load the new code:

```bash
kubectl apply -f src/4-idp/operator/k8s/rbac.yaml \
  -f src/4-idp/operator/k8s/deployment.yaml
kubectl rollout restart deployment/microservice-operator -n todo
kubectl rollout status deployment/microservice-operator -n todo --timeout=300s
kubectl get microservice todo-api -n todo -o yaml
```

Day 21 reports `ResourcesApplied` after submitting resource configuration, without checking readiness. For Day 22, compare the CR's `metadata.generation`, `status.observedGeneration`, and each condition's `observedGeneration` before reading `Ready` / `Stalled`. Waiting only for `Ready=True` can return an old result. Check Todo API health separately from the Operator's process probe.

`operator/operator-repair-check.yaml` is a temporary Day 21 resource-repair example. Before using it, ensure no CR, Deployment, or Service with its name exists. After deleting the test Service, confirm its replacement has a new UID. Keep the Operator running while deleting the test CR. Deleting a real CR also garbage-collects its workloads; do not manually remove the Kopf timer finalizer.

The Operator runs one replica with `Recreate` and `--namespace=todo --standalone`, without HA. It mounts code from a ConfigMap and installs dependencies from PyPI on each startup; production should package both in an image. Its Role covers all of `todo`, so ownership checks in the code do not isolate services through RBAC.

## Build Backstage

Use Node.js 22 or 24, Corepack, and Docker with BuildKit and Buildx. `app/` uses Yarn 4; the runtime image uses Node 24. Before pushing, log in to GHCR with write access to the target package. Maintain Catalog entries in `backstage/catalog-info.yaml` and copy them into the image's source before building:

```bash
cp src/4-idp/backstage/catalog-info.yaml src/4-idp/backstage/app/examples/entities.yaml
cd src/4-idp/backstage/app
corepack yarn install --immutable
corepack yarn tsc
corepack yarn build:backend
corepack yarn build-image
docker push ghcr.io/yrw9281/it30-idp-backstage:demo
cd ../../../..
```

Keep `packages/app` and `packages/backend`: they contain required source code. Changes to the image's `app-config.yaml` require a rebuild, not just a restart. A normal public-network build needs no corporate proxy CA; keep TLS verification enabled.

## Configure Kubernetes queries

Create the `backstage` namespace through your approved process and reuse the existing `todo` namespace. This RBAC grants the reader read-only access to specified resource kinds, excluding Secrets and Microservices:

```bash
kubectl config current-context
kubectl get namespace backstage
kubectl get namespace todo
kubectl apply -f src/4-idp/backstage/k8s/rbac-reader.yaml
```

Run the following in Bash to create a connection Secret from the current context's API URL, CA, and a one-hour ServiceAccount token. The Backstage Pod must be able to reach that URL; a localhost address used by a remote workstation usually will not work. Do not enable shell tracing:

```bash
set -euo pipefail
api_url=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
ca_data=$(kubectl config view --raw --flatten --minify \
  -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')
token=$(kubectl create token backstage-k8s-reader -n todo --duration=1h)
test -n "$api_url" && test -n "$ca_data" && test -n "$token"
printf 'apiUrl=%s\ncaData=%s\ntoken=%s\n' "$api_url" "$ca_data" "$token" |
  kubectl create secret generic backstage-k8s-conn -n backstage \
    --from-env-file=/dev/stdin --dry-run=client -o json |
  kubectl apply --server-side --field-manager=backstage-connection -f -
unset api_url ca_data token
```

The API server controls the token's lifetime; the Secret does not renew it. Restart Backstage after updating the connection Secret to reload its environment variables. Investigate `Unauthorized` as a token issue and `Forbidden` as an RBAC issue. Keep the read-only identity and TLS verification while troubleshooting.

## Load the Day 23 preview template

The default setup registers only the YAML preview template. It does not inject a GitHub token or modify Git or Kubernetes workloads:

```bash
kubectl create configmap backstage-todo-templates -n backstage \
  --from-file=app-config.templates.yaml=src/4-idp/backstage/k8s/app-config.templates.yaml \
  --from-file=preview-template.yaml=src/4-idp/backstage/todo-api-dev/preview-template.yaml \
  --from-file=template.yaml=src/4-idp/backstage/todo-api-dev/template.yaml \
  --from-file=microservice.yaml=src/4-idp/backstage/todo-api-dev/skeleton/microservice.yaml \
  --from-file=kustomization.yaml=src/4-idp/backstage/todo-api-dev/skeleton/kustomization.yaml \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -k src/4-idp/backstage/k8s
kubectl rollout restart deployment/backstage -n backstage
kubectl rollout status deployment/backstage -n backstage --timeout=180s
```

Templates use read-only `subPath` mounts. Restart the Pod after updating the ConfigMap. This also keeps projected-volume timestamp symlinks out of Backstage's safe-path checks.

## Enable GitHub PRs for Day 24

The demo uses Guest sign-in and an allow-all permission policy. Access it only through trusted loopback port-forwarding, especially once it has write credentials. A production entry point needs authentication and template/action authorization.

Prepare a fine-grained PAT restricted to `yrw9281/IT30.Platform.Engineering`, with read/write Contents and Pull requests permissions and an expiration date. Confirm the user already has repository access. Do not put the token in a form, Git, or the browser. Enter it using hidden input in Bash:

```bash
set -euo pipefail
read -r -s -p 'GitHub token: ' github_token
printf '\n'
test -n "$github_token"
printf 'token=%s\n' "$github_token" |
  kubectl create secret generic backstage-github -n backstage \
    --from-env-file=/dev/stdin --dry-run=client -o json |
  kubectl apply --server-side --field-manager=backstage-github -f -
unset github_token
```

Repeat the previous section's ConfigMap command, changing only the first `--from-file` source to `src/4-idp/backstage/k8s-pr/app-config.templates.yaml`. Keep the remaining files unchanged, then use the PR overlay:

```bash
kubectl apply -k src/4-idp/backstage/k8s-pr
kubectl rollout restart deployment/backstage -n backstage
kubectl rollout status deployment/backstage -n backstage --timeout=180s
```

This mode registers the Day 24 PR template alongside the Day 23 preview. The PR template collects only a digest, creates a branch, and proposes a change to `main` at `src/5-config/apps/todo-api/overlays/dev`; it does not merge it. Configure Git-side validation, review, and branch protection, including a check that the image came from trusted CI.

To disable PR creation, repeat the full preview-mode deployment, confirm the new Deployment no longer injects `GITHUB_TOKEN`, and revoke the unused PAT. Restart the Pod after token rotation as well.

## Open Backstage and inspect status

```bash
kubectl port-forward service/backstage 7007:7007 -n backstage --address=127.0.0.1
```

Open `http://localhost:7007`, matching the base URL in `app-config.production.yaml`, and sign in as Guest. On the Create page, choose the Day 23 preview or Day 24 PR template. Enter the 64 lowercase hexadecimal characters from Todo API CI's digest without the `sha256:` prefix.

The Catalog's Kubernetes view queries resource labels in `todo` using selectors such as `app=todo-api`. It shows neither Microservice conditions nor a history of PRs, CI runs, or delivery events. `owner: todo` records ownership without granting access. `skipMetricsLookup: true` disables Kubernetes Metrics API queries; Grafana is unaffected.

Backstage's container-local SQLite loses task history when the container is recreated or updated. A PR submits a proposal; the [Argo CD source configuration](../2-gitops/README.md) determines whether the merged change is deployed.
