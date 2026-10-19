[English](README.md) | [繁體中文](README-zh-TW.md)

# Argo CD GitOps examples

These Day 07 and 25 examples live in `argocd/`. Run commands from the repository root. Choose one way to manage Todo API: `todo.yaml` synchronizes native resources, while `todo-config.yaml` synchronizes a `Microservice` whose Deployment and Service belong to the Operator. Do not use both at once.

Apply `microservice-health.yaml` separately from `argocd/kustomization.yaml` to add the health check to `argocd-cm`. It reads `status.conditions`, defined by the [canonical CRD](../1-kubernetes/crd/microservice-crd.yaml) and written by the Day 22 [Kopf Operator](../4-idp/README.md). Use server-side apply below to preserve other managers' ConfigMap fields; avoid `replace`. If Helm manages the ConfigMap, also put the health check in its configuration source. The templates, Operator, and Catalog reuse the `todo` namespace.

The Application in `todo.yaml` enables `selfHeal` and `prune`, with a finalizer that deletes managed resources. Removing the Todo API Deployment or Service from Git can therefore delete the running workload. Follow the [IDP guide](../4-idp/README.md#switch-to-day-21-or-22) when transferring ownership: the Operator rejects existing resources with the same names, and the transition requires downtime. For a separate configuration repository, update `AppProject.sourceRepos` and the Application source; matching namespaces alone will not connect them.

Argo CD reads remote Git, not local files. Ensure the source paths and changes are pushed to `main` before enabling synchronization. For a fork, update the repository settings in the AppProject, Applications, and Backstage template.

## Days 25-26: synchronize the CR and inspect deployment status

`todo-config.yaml` reads this repository's `main` branch at `src/5-config/apps/todo-api/overlays/dev`. Its AppProject permits only `platform.example.io/Microservice` resources in `todo`. Automatic synchronization enables `selfHeal`, but not `prune`. The Application has no finalizer that deletes managed resources.

First ensure Argo CD, the CRD, and the Operator are ready, and no other Application manages the Todo API Deployment or Service. For a private repository, configure read-only HTTPS credentials in Argo CD. The repository Secret can be scoped with `project: todo-config`. Do not commit tokens or reuse Backstage's PR-writing credentials.

```bash
kubectl config current-context
kubectl apply --server-side --field-manager=todo-microservice-health \
  -f src/2-gitops/argocd/microservice-health.yaml
kubectl apply -f src/2-gitops/argocd/todo-config.yaml
kubectl wait -n argocd application/todo-config \
  --for=jsonpath='{.status.sync.status}'=Synced --timeout=180s
kubectl wait -n argocd application/todo-config \
  --for=jsonpath='{.status.health.status}'=Healthy --timeout=180s
kubectl get microservice todo-api -n todo -o yaml
kubectl get deployment,pods,svc -n todo -l app=todo-api
```

On timeout, inspect Application and CR conditions and Pod events. After `Synced`, check rollout health and compare the Git digest, CR `spec.image`, Deployment image, and Pod image before capturing results. Read CR conditions directly; Backstage's Kubernetes view does not show them.

Run these commands in separate terminals:

```bash
kubectl port-forward -n argocd service/argocd-server 8080:80 --address=127.0.0.1
```

```bash
kubectl port-forward -n backstage service/backstage 7007:7007 --address=127.0.0.1
```

Use HTTP if Argo CD has `server.insecure: true`; otherwise use HTTPS. Use the `/argocd/` path only if your installation separately sets `server.rootpath` and `server.basehref` to `/argocd`. The Application manifests here do not configure those server options. For a default installation, open `https://localhost:8080/`, acknowledge the tutorial's self-signed certificate, sign in, and select `todo-config`. Open Backstage at `http://localhost:7007/catalog/default/component/todo-api/kubernetes`. Keep the Guest demo on a controlled loopback connection.

## Native-resource example

This workflow reads `src/1-kubernetes/kind`. Do not apply it once the Operator manages Todo API.

You need Helm and `kubectl`. Follow the [Kubernetes guide](../1-kubernetes/README.md) to prepare local images on every schedulable node and an Ingress Controller. Argo CD does not build or load images. Then install Argo CD:

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm upgrade --install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace
```

Apply the GitOps resources and check synchronization and health:

```bash
kubectl apply -k src/2-gitops/argocd
argocd app get todo --refresh
argocd app wait todo --sync --health --timeout 300
kubectl get application todo -n argocd
```

Install the `argocd` CLI and log in to the server before using those commands. Alternatively, use:

```bash
kubectl wait -n argocd application/todo \
  --for=jsonpath='{.status.sync.status}'=Synced --timeout=300s
kubectl wait -n argocd application/todo \
  --for=jsonpath='{.status.health.status}'=Healthy --timeout=300s
```
