[English](README.md) | [繁體中文](README-zh-TW.md)

# Gatekeeper policy examples

The three policy YAML files in `gatekeeper/` correspond to [Day 29](../../doc/zh-tw/D29.md). Each contains a `ConstraintTemplate` followed by a Constraint:

| File | Check | Example enforcement mode |
| --- | --- | --- |
| `k8sdeploymentnoprivileged.yaml` | Regular and init containers in Deployments must not enable privileged mode | `deny` |
| `k8sdeploymentrequiredlimits.yaml` | Regular and init containers in Deployments must specify CPU and memory limits | `dryrun` |
| `k8smicroserviceimagepolicy.yaml` | Microservices must use the fixed Todo API repository and SHA-256 digest format | `warn` |

Install Gatekeeper, then create each Template and wait for its generated Constraint CRD before submitting the Constraint. Split these steps even though they share a YAML file. The privileged policy demonstrates rejection with `deny`; use `dryrun` first to assess an existing environment.

All Constraints apply only to `todo`. The image rule checks every `Microservice` in that namespace against the single repository `ghcr.io/yrw9281/it30-todo-api` and its digest format. It cannot serve as a multi-service allowlist, scan vulnerabilities, or verify build provenance. The limits policy requires nonempty values without parsing quantities, imposing maximums, or managing namespace budgets. Directly created Pods are outside these policies' scope.

`todo-required-limits-exception.yaml` replaces the original `todo-required-limits` Constraint. Use one version at a time. Its `match.labelSelector` excludes `Deployment.metadata.labels.app=todo-api`; other values and missing `app` labels remain in scope. The exception applies only to limits and matches by label, not resource name. Anyone able to change that label can qualify for it; other Constraints, including the privileged policy, still apply.

The Rego uses legacy v0 syntax in `targets[].rego`; offline evaluation with OPA 1.x requires `--v0-compatible`. This directory provides policy examples, without Gatekeeper installation steps or recorded cluster rejection results. CRD creation, audit, admission, enforcement modes, and platform error feedback still need integration checks.

Before switching to `deny`, test both valid and invalid requests in a test cluster. Confirm rejections have clear messages and can be traced in Argo CD or Operator logs.

References: [ConstraintTemplate](https://open-policy-agent.github.io/gatekeeper/website/docs/constrainttemplates/), [enforcement modes](https://open-policy-agent.github.io/gatekeeper/website/docs/violations/).
