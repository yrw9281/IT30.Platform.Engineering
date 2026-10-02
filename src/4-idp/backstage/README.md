# Backstage example boundary

`catalog-info.yaml` describes the existing `todo-api` Deployment in the `todo` namespace using its current `app=todo-api` label. The Kubernetes plugin, cluster connection, Catalog and owner entity must be configured separately. The Catalog owner is metadata, not authorization.

## Working demo deployment (`app/`, `k8s/`)

`app/` is a real, scaffolded Backstage application (Node 22 + Yarn, created with `@backstage/create-app`) with the Kubernetes plugin enabled, built into the image `ghcr.io/yrw9281/it30-idp-backstage:demo` and deployed to the `backstage` namespace on the shared cluster. It has been verified end-to-end:

- `catalog-info.yaml` is synced into `app/examples/entities.yaml` via `app/sync-catalog.sh` before each build, so the demo's Catalog shows the same `todo-api` Component defined above (single source of truth stays in `catalog-info.yaml`).
- `k8s/rbac-reader.yaml` grants a dedicated `backstage-k8s-reader` ServiceAccount read-only access (pods, services, configmaps, deployments, replicasets, statefulsets, daemonsets, jobs, cronjobs, resourcequotas) scoped to the `todo` namespace only.
- `k8s/deployment.yaml` runs the image in the `backstage` namespace. The Kubernetes plugin reads its API URL, ServiceAccount token and CA data from the `backstage-k8s-conn` Secret. None of these values belongs in Git.
- Confirmed via `kubectl port-forward svc/backstage 7007` + the Backstage REST API: `GET /api/catalog/entities` returns `todo-api`, and `POST /api/kubernetes/resources/workloads/query` with `{"entityRef": "component:default/todo-api"}` returns live Pods/ReplicaSets from the `todo` namespace.

### Known limitations (demo only, not production-ready)

- Uses `better-sqlite3` instead of Postgres for the Catalog database (see commented-out Postgres config in `app/app-config.production.yaml`). State is lost if the pod restarts.
- Auth is guest-only (`dangerouslyAllowOutsideDevelopment: true`), with no real identity/login.
- The Kubernetes plugin's label-selector annotation matches each object's own `metadata.labels`. The original manifests only labeled Pods; the Operator now also labels its adopted `todo-api` Deployment and Service with `app=todo-api`. They can match the Catalog selector, but this does not itself verify the plugin response or grant access to `Microservice` conditions; the reader Role still does not include that custom resource.
- No ingress is configured; access is via `kubectl port-forward` only, to avoid touching the shared cluster's ingress/Gateway resources used by other learners.
- `app/Dockerfile.local-build` and `app/corp-ca-bundle.pem` are optional, gitignored helpers for workstations behind a corporate TLS-inspection proxy. They supply the proxy's CA during dependency installation, not the Kubernetes API's CA. The public build uses `app/Dockerfile` and does not need these helpers.

### Kubernetes connection and read permissions

`app/app-config.yaml` uses `${K8S_API_URL}`, `${K8S_BACKSTAGE_TOKEN}` and `${K8S_BACKSTAGE_CA_DATA}`. A usable Kubernetes connection requires all three values. Do not replace the URL with a fake endpoint or disable TLS verification to make missing configuration appear to work.

| Secret key | Container environment variable | Purpose |
| --- | --- | --- |
| `apiUrl` | `K8S_API_URL` | Reachable Kubernetes API URL |
| `token` | `K8S_BACKSTAGE_TOKEN` | Token issued for `todo/backstage-k8s-reader` |
| `caData` | `K8S_BACKSTAGE_CA_DATA` | Base64-encoded CA certificate data for that API |

The Secret is named `backstage-k8s-conn` and lives in the `backstage` namespace because the Backstage Pod consumes it there. The reader ServiceAccount lives in `todo`; its Role and RoleBinding grant read access only within `todo`. ServiceAccount location alone does not restrict a token's permissions or audience.

The plugin keeps `skipMetricsLookup: true`. The Role allows workload queries but does not grant `metrics.k8s.io` access. This setting does not affect the application's OpenTelemetry data or Grafana dashboards.

#### Create or refresh the connection Secret

Run these commands from the `backstage/` directory using a kubeconfig for the cluster Backstage will query. Inspect `kubectl config current-context` before any write. The credentials need permission to apply the reader RBAC, request its token, and manage Secrets in `backstage`.

```bash
kubectl config current-context
kubectl get namespace todo
kubectl get namespace backstage
kubectl apply -f k8s/rbac-reader.yaml
```

If either Namespace is missing, create it through your approved deployment process before continuing. The commands below use the current context's API URL and CA. Backstage must be able to reach that URL from its Pod. For a same-cluster connection, `https://kubernetes.default.svc` is an option when the API certificate and network configuration support it.

Run the following block in a separate Bash shell. It creates private temporary files, requests a one-hour token, and writes the Secret without displaying its values or storing them in a client-side last-applied annotation. Do not enable shell tracing (`set -x`) while handling credentials.

```bash
set -euo pipefail
umask 077
connection_dir=$(mktemp -d)
trap 'rm -f "$connection_dir/apiUrl" "$connection_dir/token" "$connection_dir/caData"; rmdir "$connection_dir"' EXIT

api_url=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
ca_data=$(kubectl config view --raw --flatten --minify \
  -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')
if [ -z "$api_url" ] || [ -z "$ca_data" ]; then
  echo "The current context must provide an API URL and CA certificate." >&2
  exit 1
fi

token=$(kubectl create token backstage-k8s-reader -n todo --duration=1h)
if [ -z "$token" ]; then
  echo "Kubernetes returned an empty ServiceAccount token." >&2
  exit 1
fi

printf '%s' "$api_url" > "$connection_dir/apiUrl"
printf '%s' "$token" > "$connection_dir/token"
printf '%s' "$ca_data" > "$connection_dir/caData"
kubectl create secret generic backstage-k8s-conn -n backstage \
  --from-file=apiUrl="$connection_dir/apiUrl" \
  --from-file=token="$connection_dir/token" \
  --from-file=caData="$connection_dir/caData" \
  --dry-run=client -o json \
  | kubectl apply --server-side --field-manager=backstage-connection -f -
```

The API Server decides the token's actual lifetime and may adjust the requested duration. Copying it into an `Opaque` Secret does not renew it. For this manual demo, refresh the Secret before the token expires and restart Backstage after the new values are written:

```bash
kubectl rollout restart deployment/backstage -n backstage
kubectl rollout status deployment/backstage -n backstage --timeout=180s
```

Secret-backed environment variables do not update in an existing container. An expired token can stop Kubernetes queries even while Backstage's health endpoint remains ready. Do not use this manual refresh procedure as a production rotation mechanism.

If the Secret or a required key is absent, the Pod can report `CreateContainerConfigError`. Check the Pod events and the Secret's key names without printing credentials:

```bash
kubectl describe deployment backstage -n backstage
kubectl get pods -n backstage -l app=backstage
kubectl get secret backstage-k8s-conn -n backstage \
  -o go-template='{{range $key, $value := .data}}{{$key}}{{"\n"}}{{end}}'
```

Use `kubectl describe pod` with the affected Pod's name to inspect its events. If Kubernetes queries report `Unauthorized`, check the token's validity; for `Forbidden`, check RBAC. Certificate errors require the correct CA and API hostname, not a bypass of TLS verification.

### Rebuilding and redeploying

The Dockerfile copies `app-config.yaml` into the image. Rebuild and publish the image when that file changes; restarting a Pod with an old image does not replace its bundled configuration. Use Node 24 for the host build to match the runtime image, and create or refresh the connection Secret before applying the Deployment.

`app/Dockerfile` installs production dependencies in a build stage and copies the application into a separate runtime stage. It does not install a corporate CA or set `NODE_EXTRA_CA_CERTS`. Its Dockerfile-specific ignore file excludes local credentials, certificates and the corporate build helper from the build context without changing the helper's own ignore rules. Use a network that can reach the public package registries without that corporate CA; do not disable TLS verification.

```bash
cd app
./sync-catalog.sh                      # refresh examples/entities.yaml from ../catalog-info.yaml
yarn tsc && yarn build:backend
yarn build-image
docker push ghcr.io/yrw9281/it30-idp-backstage:demo
kubectl apply -f ../k8s/deployment.yaml
kubectl -n backstage rollout restart deployment/backstage
kubectl rollout status deployment/backstage -n backstage --timeout=180s
```

`yarn build-image` loads `ghcr.io/yrw9281/it30-idp-backstage:demo` into the local Docker engine. It does not push the image or change the cluster.

`todo-api-dev/template.yaml` is a staged Software Template example for updating the planned `repo-config` repository. It limits input to an image digest and fixes the service, Git destination and namespace; it does **not** verify the digest against a CI run or authorize the person submitting it. The GitHub Scaffolder module, Git credentials, protected branch and config checks must be configured before use.

The [Kopf Operator](../operator/README.md) now manages the adopted Todo API in the existing `todo` namespace and reports conditions. The planned `repo-config`, its Dev overlay and the Argo CD application for it remain unconnected to the Template. These Operator examples do not create a `todo-dev` namespace. Do not run the PR action against a real repository until those dependencies and review rules are in place. Rendering the skeleton does not deploy anything.

Run the local structure/render check with `ruby src/4-idp/backstage/check-template.rb`. This parses the Backstage YAML, substitutes a test digest and checks the resulting `Microservice` resource. It does not execute Backstage, open a PR or contact a Kubernetes cluster.
