# Backstage example boundary

`catalog-info.yaml` describes the existing `todo-api` Deployment in the `todo` namespace using its current `app=todo-api` label. The Kubernetes plugin, cluster connection, Catalog and owner entity must be configured separately. The Catalog owner is metadata, not authorization.

`todo-api-dev/template.yaml` is a staged Software Template example for updating the planned `repo-config` repository. It limits input to an image digest and fixes the service, Git destination and namespace; it does **not** verify the digest against a CI run or authorize the person submitting it. The GitHub Scaffolder module, Git credentials, protected branch and config checks must be configured before use.

`repo-config`, its Dev overlay, the Argo CD application for it and the Kopf Operator do not exist yet. Do not run the PR action against a real repository until those dependencies and review rules are in place. Rendering the skeleton does not deploy anything.

Run the local structure/render check with `ruby src/4-idp/backstage/check-template.rb`. This parses the Backstage YAML, substitutes a test digest and checks the resulting `Microservice` resource. It does not execute Backstage, open a PR or contact a Kubernetes cluster.
