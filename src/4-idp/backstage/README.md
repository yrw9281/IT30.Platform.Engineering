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
bash ../deploy-templates.sh
```

`yarn build-image` loads `ghcr.io/yrw9281/it30-idp-backstage:demo` into the local Docker engine. It does not push the image or change the cluster.

`todo-api-dev/template.yaml` proposes configuration changes to `yrw9281/IT30.Platform.Engineering`, targeting `main` and `src/5-config/apps/todo-api/overlays/dev`. The first PR creates `microservice.yaml` and `kustomization.yaml` in that directory; subsequent image updates should change only the digest. The directory does not need to exist beforehand, but the repository and target branch do. The template limits input to a digest and targets the existing `todo` namespace; it does **not** verify the digest against a CI run or authorize the person submitting it. Dev names the environment's purpose, not a separate namespace.

The [Kopf Operator](../operator/README.md) manages the adopted Todo API in the existing `todo` namespace and reports conditions. The Template and Catalog target that same namespace. Argo CD still reads `src/1-kubernetes/kind`, not the new configuration directory, so creating or merging a PR does not deploy its digest. A future Application can read the same repository, `main` and the new directory; resource ownership must be handed off before enabling synchronization. Do not delete native manifests while the existing Application's `prune`/`selfHeal` can affect the Operator's workloads.

Run the local structure check with `ruby src/4-idp/backstage/check-template.rb`. This parses the Backstage YAML, substitutes a test digest and checks the resulting `Microservice` resource, including its `todo` namespace and agreement with the Catalog lookup. It also checks that both previews use the same inputs and only run `fetch:template` and `debug:log`, and uses `kubectl kustomize` to verify both deployment modes without contacting the cluster. This is not a test of the actual Backstage renderer or a GitHub write.

### D23 and D24 screenshot previews

Two templates are registered for safe UI demonstrations:

| Template title | Purpose | Result |
| --- | --- | --- |
| Todo API Dev Config Preview (D23) | Collect a digest and render the Todo files | Actual YAML in step logs |
| Todo API Dev PR Input Preview (D24) | Render the files and display the intended PR inputs | Destination/branch/path in logs and task output; no PR |

By default, the canonical `todo-api-dev/template.yaml` is mounted but **not** registered, and no `GITHUB_TOKEN` is injected. Neither preview calls a GitHub action or writes to Kubernetes. No GitHub credentials are needed.

From the repository root, install or update the previews in an existing Backstage deployment:

```bash
ruby src/4-idp/backstage/check-template.rb
bash src/4-idp/backstage/deploy-templates.sh
```

The helper displays the current Kubernetes context, creates the template ConfigMap, applies the Deployment/Service and restarts Backstage. The existing connection Secret must already exist. `app-config.templates.yaml` retains the example Catalog, organization and original sample template locations while adding the two preview locations. No image rebuild is needed for changes to these mounted files. Running the helper **without** `--enable-pr` selects preview-only mode, including after a previous PR-enabled deployment.

Each file uses a read-only `subPath` mount. Mounting the whole projected ConfigMap directory exposes Kubernetes' `..timestamp` symlinks, which Backstage's safe-path check rejects when fetching the skeleton. `subPath` files do not update inside a running container; rerun the deployment helper after editing a template or skeleton.

After the rollout, start a new port-forward and keep its terminal open:

```bash
kubectl port-forward -n backstage service/backstage 7007:7007 --address=127.0.0.1
```

Open `http://127.0.0.1:7007`, sign in as Guest and open **Create**. If the cluster workstation is remote, forward port 7007 through VS Code first.

For D23, choose the settings preview and capture its digest form. Enter a short value such as `abc`, try to continue and capture the validation error. Then replace it with the 64 lowercase hex characters from a Todo image digest, without `sha256:`, and create the preview task. Open the `Inspect rendered files (no deployment)` step's logs and capture `microservice.yaml`, including the image, service name, namespace and port.

For D24, choose the PR-input preview, submit the same digest and capture the `Preview PR inputs (no PR created)` step's logs. Include the planned action, `repoUrl`, `branchName`, `targetBranchName` and `targetPath`. The task output also displays the destination and explicitly states that no PR was created. These screenshots demonstrate the proposed inputs, **not** a GitHub PR, successful checks, review or merge.

The integration check below authenticates as Guest in memory, exercises Backstage's actual dry-run renderer and rejects malformed/extra input. It then creates two safe preview tasks to verify the mounted files are readable and the logs contain the rendered image and intended destination. It does not print or persist the guest token.

```bash
ruby src/4-idp/backstage/check-preview.rb
```

An optional first argument supplies the digest to render. The default is a synthetic 64-character value for rendering tests; it does not establish that an image exists. Use a real Todo digest for article screenshots. Task history uses the demo's Pod-local SQLite database and is lost on restart.

### Enable real D24 Pull Requests

This is an explicit opt-in mode. It keeps both preview templates and registers **Todo API Dev Config Pull Request (D24)** (`todo-api-dev-image`). Unlike the PR-input preview, this template calls GitHub and creates a branch/PR; it does not merge the PR or write to Kubernetes.

The demo still uses Guest login and an allow-all permission policy. Restrict it to a trusted loopback port-forward while a write credential is available. Any user allowed to execute GitHub actions can potentially use the backend credential, including through the original sample template. Do not expose this configuration publicly; production use requires authentication and action/template authorization.

1. Create a fine-grained GitHub PAT whose resource owner is `yrw9281`, with access only to `IT30.Platform.Engineering` and repository permissions **Contents: Read and write** and **Pull requests: Read and write**. The token owner must already have appropriate repository access. Set an expiration date and complete any required organization approval. Confirm that `main` exists and configure required review/branch protection before treating merged changes as approved configuration. The current CLI account may not have access to this repository; its login is separate from the PAT used by Backstage.
2. From the repository root, write the PAT to Kubernetes using hidden input:

   ```bash
   bash src/4-idp/backstage/set-github-token.sh
   ```

   The helper creates or updates `backstage/backstage-github` with a `token` key using server-side apply. It does not print the value, store it in a file, or add a client-side last-applied annotation. Do not enable shell tracing or commit Secret contents.
3. Enable and deploy the real PR template:

   ```bash
   ruby src/4-idp/backstage/check-template.rb &&
   bash src/4-idp/backstage/deploy-templates.sh --enable-pr
   ```

   The helper checks that the Secret's `token` key is nonempty before changing the ConfigMap or Deployment. `k8s-pr/` adds `GITHUB_TOKEN` through `secretKeyRef`; the existing `integrations.github` configuration and GitHub Scaffolder backend module consume it. The PR-mode Catalog configuration adds the real template without removing the original locations or previews. No image rebuild, Git commit or push is required to load these local Template definitions.
4. Stop the previous port-forward with Ctrl+C if it is still running, then start a new one:

   ```bash
   kubectl port-forward -n backstage service/backstage 7007:7007 --address=127.0.0.1
   ```

5. Open `http://127.0.0.1:7007`, sign in as Guest and select **Create → Todo API Dev Config Pull Request (D24)**. Enter the 64 lowercase hex characters from a Todo CI image digest, without `sha256:`. Review the form and submit it. This operation performs a real GitHub write.
6. Open **Review the config change** in the completed task. Confirm the repository, base branch `main`, head branch `backstage/todo-api/dev/<digest>` and the two files under `src/5-config/apps/todo-api/overlays/dev`. Capture the task's PR link and GitHub's **Files changed** view for D24. Do not merge just to obtain a screenshot: configuration checks and required reviews are separate setup, and Argo CD is not connected to this directory.

If GitHub returns an authentication/access error, check PAT expiration, repository selection, owner permissions and organization approval. For a branch error, verify `main` and any existing proposal branch/PR for the same digest before retrying. The fixed PR description does not attach CI provenance. The existing application CI is not a replacement for independent YAML/CRD/image-source validation; those configuration checks have not been implemented by this setup.

To rotate the credential, rerun `set-github-token.sh` and `deploy-templates.sh --enable-pr`; environment variables only refresh in a new Pod. To disable this mode, run `deploy-templates.sh` without the flag and revoke the PAT in GitHub when it is no longer needed. Restarts lose the demo's task history, but an already-created GitHub PR remains in GitHub. These helpers do not create an Argo CD Application or enable deployment.
