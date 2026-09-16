# Kubernetes 基礎範例

範例只有兩個 container：提供待辦事項 API 的 `todo-api`，以及反向代理 API 並提供 HTML 的 `web`。資料存在 API process 的記憶體中，Pod 重建後會消失；這是為了把焦點放在 Kubernetes 的資源關係，不是資料庫部署範例。

先在 `src/0-todo-microservices` 建置 image：

```bash
docker build -t todo-api:0.1.0 Todo.Api
docker build -t todo-web:0.1.0 WebApp
docker compose up --build
```

開啟 `http://localhost:8081` 後，可以新增、完成與刪除待辦事項。

使用 Kind 時，將本機 image 載入叢集，再套用 manifest：

```bash
kind load docker-image todo-api:0.1.0 todo-web:0.1.0
kubectl apply -k src/1-kubernetes
kubectl get deployment,service,ingress -n todo
```

manifest 預設使用 `nginx` IngressClass 與 `todo.localhost`。如果叢集未安裝 Ingress Controller，仍可用下列方式確認 API：

```bash
kubectl port-forward service/todo-api 8080:8080 -n todo
curl http://127.0.0.1:8080/api/todos
```
