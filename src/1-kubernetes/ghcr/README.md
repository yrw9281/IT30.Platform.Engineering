# GHCR manifests

這組 manifest 使用 GitHub Container Registry（GHCR）的 container image，不需要將本機 image 載入 Kind。它部署 `todo-api`、`todo-bff` 與 `web` 到 `todo` Namespace，並使用 `nginx` IngressClass 將 `todo.localhost` 的 `/api` 導向 BFF，其餘路徑導向前端。

## 發布 image

在 GitHub 建立 Personal Access Token（classic），授予 `write:packages` 權限，然後登入 GHCR。若 package 已連結 repository，`GITHUB_TOKEN` 也可在 GitHub Actions 中發布 image。

```bash
export CR_PAT=******
echo "$CR_PAT" | docker login ghcr.io -u yrw9281 --password-stdin

docker build -t ghcr.io/yrw9281/it30-todo-api:0.1.0 ../0-todo-microservices/Todo.Api
docker build -t ghcr.io/yrw9281/it30-todo-bff:0.1.0 ../0-todo-microservices/Todo.Bff
docker build -t ghcr.io/yrw9281/it30-todo-web:0.1.0 ../0-todo-microservices/WebApp
docker push ghcr.io/yrw9281/it30-todo-api:0.1.0
docker push ghcr.io/yrw9281/it30-todo-bff:0.1.0
docker push ghcr.io/yrw9281/it30-todo-web:0.1.0
```

第一次發布後，在 GitHub package settings 將兩個 package 設為 public，叢集便能直接拉取 image。

## 部署

```bash
kubectl apply -k src/1-kubernetes/ghcr
kubectl rollout status deployment/todo-api -n todo
kubectl rollout status deployment/todo-bff -n todo
kubectl rollout status deployment/web -n todo
kubectl get deployment,service,ingress -n todo
```

若 package 維持 private，先以具備 `read:packages` 權限的 token 建立 Secret：

```bash
kubectl create namespace todo
kubectl -n todo create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=yrw9281 \
  --docker-password='******'
```

接著在兩個 Deployment 的 `spec.template.spec` 加入：

```yaml
imagePullSecrets:
  - name: ghcr-pull-secret
```

若沒有 NGINX Ingress Controller，可先用 port-forward 驗證 API：

```bash
kubectl port-forward service/todo-api 8080:8080 -n todo
curl http://127.0.0.1:8080/api/todos
```
