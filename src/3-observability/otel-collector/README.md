# OpenTelemetry Collector Gateway

這組 manifest 在 `observability` Namespace 部署一個 OpenTelemetry Collector Gateway。它接收 OTLP/gRPC（`4317`）與 OTLP/HTTP（`4318`）的 Metrics、Logs 和 Traces，依序執行記憶體限制、補上 `platform.name=todo-platform`、移除列出的敏感 attributes、批次處理，最後依 signal 交給不同 exporter：

- Metrics 透過 Prometheus exporter 暴露在 `8889`，由 Prometheus scrape。
- Logs 以 OTLP/HTTP 傳送到 Loki。
- Traces 以 OTLP/HTTP 傳送到 Tempo。
- `debug` exporter 仍保留在三條 pipeline，方便在開發環境檢查資料。

Prometheus、Loki 與 Tempo 必須先部署，否則 logs 與 traces exporter 無法送出資料。這組設定的 backend endpoint 對應 Grafana observability stack 的 Service。

## 部署

```bash
kubectl apply -k src/3-observability/otel-collector
kubectl rollout status deployment/otel-collector -n observability
kubectl get deployment,service -n observability
```

服務在叢集內的 OTLP endpoint 為：

```text
otel-collector.observability.svc:4317  # OTLP/gRPC
http://otel-collector.observability.svc:4318  # OTLP/HTTP
otel-collector.observability.svc:8889  # Prometheus scrape
```

## 驗證 Collector 健康狀態

```bash
kubectl port-forward deployment/otel-collector 13133:13133 -n observability
curl --fail http://127.0.0.1:13133/
```

## 送入測試 Trace

安裝官方的 `telemetrygen` 後，將一筆測試 Trace 送往 Collector：

```bash
go install github.com/open-telemetry/opentelemetry-collector-contrib/cmd/telemetrygen@latest
$(go env GOPATH)/bin/telemetrygen traces \
  --otlp-insecure \
  --otlp-endpoint otel-collector.observability.svc:4317 \
  --service todo-api \
  --traces 1
```

在叢集外執行測試時，先開啟 gRPC port-forward，並將 endpoint 改為 `127.0.0.1:4317`：

```bash
kubectl port-forward service/otel-collector 4317:4317 -n observability
$(go env GOPATH)/bin/telemetrygen traces \
  --otlp-insecure \
  --otlp-endpoint 127.0.0.1:4317 \
  --service todo-api \
  --traces 1
```

Collector log 應出現由 `debug` exporter 輸出的 Trace，並包含 `platform.name: todo-platform`：

```bash
kubectl logs deployment/otel-collector -n observability
```

目前的驗證工具不會替 Trace 加入 `enduser.id`。若要驗證敏感欄位移除，請使用支援自訂 attributes 的 SDK 或測試工具送入該欄位，再確認 `debug` exporter 的輸出不含它。

## 驗證 manifest 與 Collector 設定

先渲染 Kubernetes manifest：

```bash
kubectl kustomize src/3-observability/otel-collector
```

以 client-side dry run 檢查 Kubernetes 資源結構：

```bash
kubectl kustomize src/3-observability/otel-collector > /tmp/otel-collector.yaml
kubectl apply --dry-run=client -f /tmp/otel-collector.yaml
rm /tmp/otel-collector.yaml
```

最後用與 Deployment 相同版本的 Collector 驗證設定檔：

```bash
sed -n '/^  config.yaml: |/,$p' \
  src/3-observability/otel-collector/otel-collector-config.yaml |
  sed '1d;s/^    //' > /tmp/otel-collector-config.yaml

docker run --rm \
  -v /tmp/otel-collector-config.yaml:/conf/config.yaml:ro \
  otel/opentelemetry-collector:0.161.0 \
  validate --config=/conf/config.yaml

rm /tmp/otel-collector-config.yaml
```
