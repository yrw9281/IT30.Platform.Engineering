[English](README.md) | [繁體中文](README-zh-TW.md)

# Kubernetes deployment and the Microservice CRD

This directory covers Days 03-05, Day 15, and Day 18. Run all commands below from the repository root.

| Directory | Purpose |
| --- | --- |
| `kind/` | Deployments, Services, and Ingress using local images |
| `ghcr/` | The same Todo workloads using GHCR images |
| `crd/` | The Microservice CRD, valid inputs, and a schema rejection example |

Choose either `kind/` or `ghcr/`; they manage resources with the same names. Once the Operator manages Todo API, stop applying these manifests to its resources.

Both sets default to two Todo API replicas with separate in-memory data. A read or update can reach a Pod that does not have the todo you just created. Before using the application, set `spec.replicas` to `1` in the selected directory's `todo-api.yaml`. Scaling out requires shared storage. If Argo CD manages the workload, push the change to Git; `kubectl scale` alone will not persist it.

## Local images with Kind

You need Docker, Kind, `kubectl`, and an existing Kind cluster. Build the three images using the [application guide](../0-todo-microservices/README.md), then load them into the cluster:

```bash
kubectl config current-context
kind load docker-image todo-api:0.1.0 todo-bff:0.1.0 todo-web:0.1.0
kubectl apply -k src/1-kubernetes/kind
kubectl get deployment,service,ingress -n todo
```

`kind load` defaults to the cluster named `kind`. For another cluster name, add `--name <cluster-name>` and ensure the `kubectl` context points to that cluster.

The Ingress uses the `nginx` IngressClass. It routes `/api` on `todo.localhost` to the BFF and other paths to the web frontend. Install an NGINX Ingress Controller separately. Without a controller, you can access the BFF through its Service:

```bash
kubectl port-forward service/todo-bff 8080:8080 -n todo
```

In another terminal, run `curl --fail http://127.0.0.1:8080/api/todos`.

## GHCR images

`ghcr/` uses the mutable `:0.1.0` tag rather than a pinned digest. All three images must be published and pullable. For private packages, complete the namespace, Secret, and Deployment setup below before running these deployment commands:

```bash
kubectl apply -k src/1-kubernetes/ghcr
kubectl rollout status deployment/todo-api -n todo
kubectl rollout status deployment/todo-bff -n todo
kubectl rollout status deployment/web -n todo
```

For private packages, first create the `todo` namespace through your approved process, then create a read-only image pull Secret in it. Use credentials with `read:packages` access only to the target packages, not the short-lived CI `GITHUB_TOKEN`. For example, create the Secret using hidden input in Bash:

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

This command temporarily puts the token in `kubectl` process arguments. Use it only on a trusted workstation; on shared hosts, use your existing Secret management process. Do not enable shell tracing or commit Secret contents to Git. Add the following under `spec.template.spec` of each Deployment that needs to pull a private image:

```yaml
imagePullSecrets:
  - name: ghcr-pull-secret
```

## Microservice CRD

The chapter examples share `crd/microservice-crd.yaml`, which defines the namespaced API `platform.example.io/v1alpha1`. It accepts only `spec.image` and `spec.port`, with no `env` fields or Secret references. Use the separate CRD snapshot in `src/final/` only with that deployment setup.

The schema requires a top-level `spec` and includes Day 22's `status.conditions`; Days 05 and 18 show earlier schemas. Before upgrading, check every CR for a nonempty image and an integer port in `1–65535`. Repair incompatible data before adding required fields:

```bash
kubectl get microservices -A -o yaml
```

Before the first installation, confirm the target cluster and the existing `todo` namespace. The following commands write to the cluster and require CRD administration permissions:

```bash
kubectl config current-context
kubectl get namespace todo
kubectl apply -f src/1-kubernetes/crd/microservice-crd.yaml
kubectl wait --for=condition=Established crd/microservices.platform.example.io --timeout=60s
```

After installation, use server-side dry-run to validate inputs without storing CRs:

```bash
kubectl apply --server-side --dry-run=server \
  -f src/1-kubernetes/crd/todo-api.yaml \
  -f src/1-kubernetes/crd/web.yaml
kubectl apply --server-side --dry-run=server \
  -f src/1-kubernetes/crd/invalid-todo-api.yaml
```

The last example uses port `65536` and should be rejected. Passing dry-run does not prove that an image exists or a workload is ready. `web.yaml` is only a schema example: the web image does not support the current Operator's Todo API probes, so do not deploy it with that Operator.

See the [IDP guide](../4-idp/README.md) for submitting `todo-api.yaml` and deploying the Operator. A CR alone does not create a Deployment. Deleting a CR managed by the Operator also garbage-collects the workloads it owns.
