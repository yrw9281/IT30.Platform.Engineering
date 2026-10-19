# OpenTelemetry 與 Grafana

對應 Day 09–13。`otel-collector/` 保存 Collector Gateway，`grafana/` 保存 Prometheus、Loki、Tempo、Grafana 與 dashboard。跨服務追蹤的程式碼在 [Todo API 與 BFF](../0-todo-microservices/README.md)，沒有另一組 tracing 應用程式。

以下指令都從 repository 根目錄執行。

## 部署觀測元件

```bash
kubectl config current-context
kubectl apply -k src/3-observability/otel-collector
kubectl apply -k src/3-observability/grafana
kubectl rollout status deployment/otel-collector -n observability
kubectl rollout status deployment/prometheus -n observability
kubectl rollout status deployment/loki -n observability
kubectl rollout status deployment/tempo -n observability
kubectl rollout status deployment/grafana -n observability
```

Collector 接收 OTLP/gRPC `4317` 與 OTLP/HTTP `4318`，依序執行記憶體限制、補上 `platform.name=todo-platform`、移除列出的敏感 attributes，再批次匯出。Metrics 暴露在 `8889`，由 Prometheus 每 15 秒 scrape；Logs 送往 Loki，Traces 送往 Tempo。backend 尚未就緒時，對應 exporter 可能回報連線錯誤。

三條 pipeline 都保留 `debug` exporter，供受控開發環境查看處理過的資料。它不能取代 backend，也不代表應用程式可以先把 token、Authorization header 或 Todo 內容送進 telemetry。

## 驗證跨服務 Trace Context

依 [Kubernetes 說明](../1-kubernetes/README.md) 部署 BFF 與 API，確認它們的 OTLP endpoint 指向 `http://otel-collector.observability.svc:4317`。轉送 BFF Service：

```bash
kubectl port-forward service/todo-bff 8080:8080 -n todo
```

在另一個終端機送出指定 Trace ID 的請求：

```bash
curl --fail \
  -H 'content-type: application/json' \
  -H 'traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01' \
  --data '{"title":"trace-test"}' \
  http://127.0.0.1:8080/api/todos
kubectl logs deployment/otel-collector -n observability
```

預期同一條 Trace 中有 BFF server span、HTTP client span、API server span 與 `todo.create`。資料保存在記憶體中，因此沒有 database span。

若只想確認 Collector 程序是否回應，可以另外轉送 Deployment 的 `13133` port，再執行 `curl --fail http://127.0.0.1:13133/`。health endpoint 成功不代表資料已送到最終 backend。

## 在 Grafana 查詢

```bash
kubectl port-forward service/grafana 3000:3000 -n observability
```

開啟 `http://127.0.0.1:3000`，以開發環境帳密 `admin`／`admin` 登入。`Todo service overview` dashboard 已保存 request rate、p95、延遲 heatmap、5xx ratio 與 application logs；以 service 與 route 篩選，並等待至少一個 scrape interval。少量請求不一定能立即計算 p95，沒有 5xx 序列也不代表查詢失敗。

Grafana Explore 的 Tempo datasource 可使用以下 TraceQL：

```traceql
{ resource.service.name = "todo-api" }
```

Tempo 的 Trace-to-Logs 連到 Loki；Loki 的 TraceID derived field 則可從 log 返回 Trace。關聯是否查得到，取決於實際送出的服務 attributes、trace ID 與 log。

這組元件都是單一副本，使用 `emptyDir`；Pod 重建會遺失資料與 Grafana 本機設定。它沒有正式環境所需的持久化、HA、帳號治理、備份與 retention 設計，也沒有對外 Ingress。
