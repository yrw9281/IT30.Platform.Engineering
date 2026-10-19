[English](README.md) | [繁體中文](README-zh-TW.md)

# Todo API GitOps configuration

The Day 24 Backstage template targets `apps/todo-api/overlays/dev/` when creating a pull request. It contains the `Microservice` and `kustomization.yaml` for Dev in the existing `todo` namespace.

`microservice.yaml` specifies an image digest and port `8080`. Update only `spec.image`, keeping the service name, namespace, and port unchanged. Use a digest from trusted Todo API CI output and verify its source during review.

Preview the Kustomize output from the repository root:

```bash
kubectl kustomize src/5-config/apps/todo-api/overlays/dev
```

Rendering checks only the generated YAML. Validate the Kubernetes schema and image source in separate PR checks, require review and branch protection, and check rollout status after deployment.

The [Argo CD](../2-gitops/README.md) Application in `todo-config.yaml` reads this directory from `main`; the native-resource `todo.yaml` reads a different source. Before enabling synchronization, deploy the CRD and Operator and transfer workload ownership. After a PR is merged, Argo CD must synchronize the CR before the Operator can update workloads.
