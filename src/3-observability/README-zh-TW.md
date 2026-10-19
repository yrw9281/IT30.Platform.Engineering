[English](README.md) | [繁體中文](README-zh-TW.md)

# OpenTelemetry 與 Grafana

對應 Day 09–13。`otel-collector/` 包含 Collector Gateway，`grafana/` 包含 Prometheus、Loki、Tempo、Grafana 與儀表板。跨服務追蹤的程式碼在 [Todo API 與 BFF](../0-todo-microservices/README-zh-TW.md)。

以下指令皆從儲存庫根目錄執行。

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

Collector 透過 `4317` 接收 OTLP/gRPC、透過 `4318` 接收 OTLP/HTTP，再依序限制記憶體、補上 `platform.name=todo-platform`、移除設定中列出的敏感屬性，最後批次匯出。指標由 Prometheus 每 15 秒從 `8889` 擷取，日誌送往 Loki，追蹤送往 Tempo。儲存後端尚未就緒時，對應 exporter 可能回報連線錯誤。

三條資料管線也使用 `debug` exporter，供受控開發環境查看資料；儲存與查詢仍由後端負責。token、Authorization header 與 Todo 內容應在應用程式端排除，不要送入遙測資料。

## 驗證跨服務 Trace Context

依 [Kubernetes 說明](../1-kubernetes/README-zh-TW.md) 部署 BFF 與 API，確認它們的 OTLP endpoint 指向 `http://otel-collector.observability.svc:4317`。轉送 BFF Service：

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

預期同一條 Trace 包含 BFF 接收請求、HTTP 呼叫、API 接收請求的 spans，以及 `todo.create`。資料存在記憶體中，因此不會有資料庫 span。

若只想確認 Collector 程序是否回應，可在另一個終端機執行 `kubectl port-forward deployment/otel-collector 13133:13133 -n observability`，再執行 `curl --fail http://127.0.0.1:13133/`。health endpoint 成功不代表資料已送到最終 backend。

## 在 Grafana 查詢

```bash
kubectl port-forward service/grafana 3000:3000 -n observability
```

開啟 `http://127.0.0.1:3000`，以開發環境帳密 `admin`／`admin` 登入。`Todo service overview` 儀表板包含請求速率、p95 延遲、延遲熱圖、5xx 比例與應用程式日誌，可依服務與路由篩選。請等待至少一次指標擷取；請求太少時，p95 可能暫時沒有資料，沒有 5xx 序列也不一定是查詢失敗。

Grafana Explore 的 Tempo datasource 可使用以下 TraceQL：

```traceql
{ resource.service.name = "todo-api" }
```

Tempo 的 Trace-to-Logs 連到 Loki，Loki 的 TraceID 衍生欄位則連回 Trace。要查到相關資料，服務屬性、trace ID 與日誌必須能互相對應。

各元件皆為單一副本並使用 `emptyDir`，Pod 重建會遺失資料與 Grafana 本機設定。正式環境須另行規劃持久化、高可用性、帳號管理、備份與資料保留政策；本範例也未提供對外 Ingress。
