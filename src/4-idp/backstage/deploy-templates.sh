#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
catalog_config="$root/k8s/app-config.templates.yaml"
deployment_dir="$root/k8s"
if [ "$#" -eq 1 ] && [ "$1" = "--enable-pr" ]; then
  catalog_config="$root/k8s-pr/app-config.templates.yaml"
  deployment_dir="$root/k8s-pr"
elif [ "$#" -ne 0 ]; then
  echo "Usage: bash deploy-templates.sh [--enable-pr]" >&2
  exit 1
fi

kubectl config current-context
kubectl get namespace backstage
if [ "$deployment_dir" = "$root/k8s-pr" ]; then
  token_size="$(kubectl get secret backstage-github -n backstage \
    -o go-template='{{len (index .data "token")}}')"
  if [ "$token_size" -eq 0 ]; then
    echo "backstage-github must contain a nonempty token key." >&2
    exit 1
  fi
  echo "Enabling real GitHub PR creation. Restrict access to this guest-only demo."
fi
kubectl create configmap backstage-todo-templates -n backstage \
  --from-file=app-config.templates.yaml="$catalog_config" \
  --from-file=preview-template.yaml="$root/todo-api-dev/preview-template.yaml" \
  --from-file=pr-preview-template.yaml="$root/todo-api-dev/pr-preview-template.yaml" \
  --from-file=template.yaml="$root/todo-api-dev/template.yaml" \
  --from-file=microservice.yaml="$root/todo-api-dev/skeleton/microservice.yaml" \
  --from-file=kustomization.yaml="$root/todo-api-dev/skeleton/kustomization.yaml" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -k "$deployment_dir"
kubectl rollout restart deployment/backstage -n backstage
kubectl rollout status deployment/backstage -n backstage --timeout=180s
