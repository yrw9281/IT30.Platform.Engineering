# Backstage example boundary

`catalog-info.yaml` describes the existing `todo-api` Deployment in the `todo` namespace using its current `app=todo-api` label. The Kubernetes plugin, cluster connection, Catalog and owner entity must be configured separately. The Catalog owner is metadata, not authorization.

## Working demo deployment (`app/`, `k8s/`)

`app/` is a real, scaffolded Backstage application (Node 22 + Yarn, created with `@backstage/create-app`) with the Kubernetes plugin enabled, built into the image `ghcr.io/yrw9281/it30-idp-backstage:demo` and deployed to the `backstage` namespace on the shared cluster. It has been verified end-to-end:

- `catalog-info.yaml` is synced into `app/examples/entities.yaml` via `app/sync-catalog.sh` before each build, so the demo's Catalog shows the same `todo-api` Component defined above (single source of truth stays in `catalog-info.yaml`).
- `k8s/rbac-reader.yaml` grants a dedicated `backstage-k8s-reader` ServiceAccount read-only access (pods, services, configmaps, deployments, replicasets, statefulsets, daemonsets, jobs, cronjobs, resourcequotas) scoped to the `todo` namespace only.
- `k8s/deployment.yaml` runs the image in the `backstage` namespace, reading the Kubernetes plugin's cluster token/CA from the `backstage-k8s-conn` Secret (not committed — created directly on the cluster from the ServiceAccount token).
- Confirmed via `kubectl port-forward svc/backstage 7007` + the Backstage REST API: `GET /api/catalog/entities` returns `todo-api`, and `POST /api/kubernetes/resources/workloads/query` with `{"entityRef": "component:default/todo-api"}` returns live Pods/ReplicaSets from the `todo` namespace.

### Known limitations (demo only, not production-ready)

- Uses `better-sqlite3` instead of Postgres for the Catalog database (see commented-out Postgres config in `app/app-config.production.yaml`) — state is lost if the pod restarts.
- Auth is guest-only (`dangerouslyAllowOutsideDevelopment: true`) — no real identity/login.
- The Kubernetes plugin's label-selector annotation matches each object's own `metadata.labels`. The `todo-api` `Deployment` and `Service` objects currently carry no labels of their own (only the Pods, inherited via the ReplicaSet template, do), so only Pods/ReplicaSets show up in the plugin response — Deployments/Services do not, even though RBAC permits reading them. Fixing this would mean adding matching labels to those manifests in `src/1-kubernetes/`.
- No ingress is configured; access is via `kubectl port-forward` only, to avoid touching the shared cluster's ingress/Gateway resources used by other learners.
- `app/Dockerfile.local-build` and `app/corp-ca-bundle.pem` are gitignored, workstation-only build helpers (inject a corporate TLS-interception CA during `yarn install` so the image can build on this network). The tracked `app/packages/backend/Dockerfile` from the Backstage scaffold is untouched.

### Rebuilding and redeploying

```bash
cd app
./sync-catalog.sh                      # refresh examples/entities.yaml from ../catalog-info.yaml
yarn tsc && yarn build:backend
docker buildx build -f Dockerfile.local-build -t ghcr.io/yrw9281/it30-idp-backstage:demo --load .
docker push ghcr.io/yrw9281/it30-idp-backstage:demo
kubectl -n backstage rollout restart deployment/backstage
```

`todo-api-dev/template.yaml` is a staged Software Template example for updating the planned `repo-config` repository. It limits input to an image digest and fixes the service, Git destination and namespace; it does **not** verify the digest against a CI run or authorize the person submitting it. The GitHub Scaffolder module, Git credentials, protected branch and config checks must be configured before use.

`repo-config`, its Dev overlay, the Argo CD application for it and the Kopf Operator do not exist yet. Do not run the PR action against a real repository until those dependencies and review rules are in place. Rendering the skeleton does not deploy anything.

Run the local structure/render check with `ruby src/4-idp/backstage/check-template.rb`. This parses the Backstage YAML, substitutes a test digest and checks the resulting `Microservice` resource. It does not execute Backstage, open a PR or contact a Kubernetes cluster.
