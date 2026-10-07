#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

kubectl config current-context
kubectl get namespace backstage
kubectl create configmap backstage-todo-templates -n backstage \
  --from-file=app-config.templates.yaml="$root/k8s/app-config.templates.yaml" \
  --from-file=preview-template.yaml="$root/todo-api-dev/preview-template.yaml" \
  --from-file=pr-preview-template.yaml="$root/todo-api-dev/pr-preview-template.yaml" \
  --from-file=microservice.yaml="$root/todo-api-dev/skeleton/microservice.yaml" \
  --from-file=kustomization.yaml="$root/todo-api-dev/skeleton/kustomization.yaml" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f "$root/k8s/deployment.yaml"
kubectl rollout restart deployment/backstage -n backstage
kubectl rollout status deployment/backstage -n backstage --timeout=180s
