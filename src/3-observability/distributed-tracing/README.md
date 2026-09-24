# Distributed tracing 範例

這份範例透過 `todo-bff` 轉送 Todo API 請求。BFF 的 ASP.NET Core instrumentation 建立 HTTP server span；它以 `HttpClient` 呼叫 `todo-api` 時，會帶上 W3C `traceparent` header。`todo-api` 擷取該 header，建立同一條 Trace 中的 server span。

兩個服務都會將 Trace 匯出到 OpenTelemetry Collector：

```text
http://otel-collector.observability.svc:4317
```

## 建置與載入 Kind

先部署 OpenTelemetry Collector，再建置兩個 application image 並載入 Kind：

```bash
kubectl apply -k src/3-observability/otel-collector

docker build -t todo-api:0.1.0 src/0-todo-microservices/Todo.Api
docker build -t todo-bff:0.1.0 src/0-todo-microservices/Todo.Bff
kind load docker-image todo-api:0.1.0 todo-bff:0.1.0

kubectl apply -k src/1-kubernetes/kind
kubectl rollout status deployment/todo-api -n todo
kubectl rollout status deployment/todo-bff -n todo
```

## 驗證 Trace Context

將 BFF service 轉送到本機，並用固定的 Trace ID 發出 Create Todo 請求：

```bash
kubectl port-forward service/todo-bff 8080:8080 -n todo
```

```bash
curl --fail \
  -H 'content-type: application/json' \
  -H 'traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01' \
  --data '{"title":"trace-test"}' \
  http://127.0.0.1:8080/api/todos
```

查看 Collector log：

```bash
kubectl logs deployment/otel-collector -n observability
```

`debug` exporter 的輸出應可找到同一個 `Trace ID` `4bf92f3577b34da6a3ce929d0e0e4736`，以及 `todo-bff` 和 `todo-api` 的 span。這個範例的 Todo 資料保存在記憶體中，因此目前不會產生資料庫 span。
