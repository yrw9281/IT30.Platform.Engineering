#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

stage=${1:-day22}
crd=../../1-kubernetes/crd/microservice-crd.yaml
case "$stage" in
  day20)
    echo "day20 is now the observer only (historical full day20 is now day22)." >&2
    code=(--from-file=handlers.py=day20/handlers.py) ;;
  day21) code=(--from-file=handlers.py=day21/handlers.py --from-file=resources.py) ;;
  day22) code=(--from-file=handlers.py --from-file=resources.py) ;;
  day19) echo "day19 was renamed to day20 (observer); choose explicitly." >&2; exit 1 ;;
  *) echo "Usage: bash deploy.sh [day20|day21|day22] (default: day22)" >&2; exit 1 ;;
esac

kubectl config current-context
kubectl get namespace todo
if ! kubectl get crd microservices.platform.example.io; then
  echo "CRD unavailable. Check access; an administrator can install it with:" >&2
  echo "kubectl apply -f $crd" >&2
  echo "kubectl wait --for=condition=Established crd/microservices.platform.example.io --timeout=60s" >&2
  exit 1
fi
if [ "$stage" = day22 ]; then
  kubectl get microservices -A -o json | python3 validate_crs.py
  kubectl apply -f "$crd"
  kubectl wait --for=condition=Established crd/microservices.platform.example.io --timeout=60s
fi
kubectl create configmap microservice-operator-code -n todo \
  "${code[@]}" --from-file=requirements.txt --dry-run=client -o yaml \
  | kubectl apply -f -
kubectl apply -f k8s/rbac.yaml -f k8s/deployment.yaml
kubectl rollout restart deployment/microservice-operator -n todo
kubectl rollout status deployment/microservice-operator -n todo --timeout=300s
