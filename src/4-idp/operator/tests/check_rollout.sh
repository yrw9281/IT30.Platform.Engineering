#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 wait-current.py Ready
original_image=$(kubectl get microservice todo-api -n todo -o jsonpath='{.spec.image}')
deployment_uid=$(kubectl get deployment todo-api -n todo -o jsonpath='{.metadata.uid}')
service_uid=$(kubectl get service todo-api -n todo -o jsonpath='{.metadata.uid}')
cr_uid=$(kubectl get microservice todo-api -n todo -o jsonpath='{.metadata.uid}')
image_id=$(kubectl get pods -n todo \
  -l "platform.example.io/microservice-uid=$cr_uid" \
  -o jsonpath='{.items[0].status.containerStatuses[0].imageID}')
printf '%s\n' "$image_id"

restore() {
  kubectl patch microservice todo-api -n todo --type=merge \
    -p "{\"spec\":{\"image\":\"$original_image\"}}"
  python3 wait-current.py Ready
}
trap restore EXIT

digest=$(printf '%s\n' "$image_id" | sed -n 's/.*@sha256:\([0-9a-f]\{64\}\)$/\1/p')
if [ "${#digest}" -ne 64 ]; then
  printf '%s\n' "imageID has no usable SHA-256 digest" >&2
  exit 1
fi
digest_image="ghcr.io/yrw9281/it30-todo-api@sha256:$digest"
kubectl patch microservice todo-api -n todo --type=merge \
  -p "{\"spec\":{\"image\":\"$digest_image\"}}"
python3 wait-current.py Ready

test "$digest_image" = "$(kubectl get deployment todo-api -n todo -o jsonpath='{.spec.template.spec.containers[0].image}')"
test "$deployment_uid" = "$(kubectl get deployment todo-api -n todo -o jsonpath='{.metadata.uid}')"
test "$service_uid" = "$(kubectl get service todo-api -n todo -o jsonpath='{.metadata.uid}')"
printf '%s\n' "PASS: digest reference applied; Deployment and Service UIDs preserved"

kubectl patch microservice todo-api -n todo --type=merge \
  -p '{"spec":{"image":"ghcr.io/yrw9281/it30-todo-api:operator-missing-image"}}'
python3 wait-current.py Stalled
test "$(kubectl get microservice todo-api -n todo -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')" = False
reason=$(kubectl get microservice todo-api -n todo -o jsonpath='{.status.conditions[?(@.type=="Stalled")].reason}')
case "$reason" in
  ErrImagePull|ImagePullBackOff) ;;
  *) printf 'Unexpected failure reason: %s\n' "$reason" >&2; exit 1 ;;
esac
test "$(kubectl get deployment todo-api -n todo -o jsonpath='{.status.availableReplicas}')" -ge 2
printf '%s\n' "PASS: failed image is not Ready; previous replicas remain available"
