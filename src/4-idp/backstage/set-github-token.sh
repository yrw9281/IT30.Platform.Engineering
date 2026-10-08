#!/usr/bin/env bash
set +x
set -euo pipefail

kubectl config current-context
kubectl get namespace backstage
read -rsp 'GitHub token: ' github_token
printf '\n' >&2
if [ -z "$github_token" ]; then
  echo "GitHub token must not be empty." >&2
  exit 1
fi

printf '%s' "$github_token" |
  kubectl create secret generic backstage-github -n backstage \
    --from-file=token=/dev/stdin --dry-run=client -o json |
  kubectl apply --server-side --field-manager=backstage-github -f -
unset github_token
