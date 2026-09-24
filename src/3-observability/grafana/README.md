# Grafana observability stack

這組 manifest 在 `observability` Namespace 部署 Prometheus、Loki、Tempo 和 Grafana，供 Todo 範例查詢 OpenTelemetry 資料。

- OpenTelemetry Collector 將 metrics 暴露在 `:8889`，Prometheus 每 15 秒抓取一次。
- Collector 以 OTLP/HTTP 將 logs 傳到 Loki 的 `/otlp`，並將 traces 傳到 Tempo。
- Grafana provisioning 預先建立三個 datasource，並載入 `Todo service overview` dashboard。

這是單一副本的開發環境。Prometheus、Loki、Tempo 和 Grafana 都使用 `emptyDir`，Pod 重建後歷史資料與 Grafana 本機設定會消失。Grafana 的預設帳密是 `admin`／`admin`，只可在受控的本機或測試叢集使用。

## 部署

先部署 Collector，再部署這組元件：

```bash
kubectl apply -k src/3-observability/otel-collector
kubectl apply -k src/3-observability/grafana

kubectl rollout status deployment/prometheus -n observability
kubectl rollout status deployment/loki -n observability
kubectl rollout status deployment/tempo -n observability
kubectl rollout status deployment/grafana -n observability
```

在叢集外開啟 Grafana：

```bash
http://grafana.10.124.2.77.sslip.io
```

以 `admin`／`admin` 登入後，從 Dashboards 開啟 `Todo service overview`。這個入口由 Istio Gateway 提供，沒有 TLS 或額外的存取控制；僅限受控測試網路。若要讓其他網路使用，必須先設定 TLS、身分驗證與非預設的管理者密碼。

若只需要在執行 `kubectl` 的本機查看，可以改用 port-forward：

```bash
kubectl port-forward service/grafana 3000:3000 -n observability
```

接著開啟 `http://127.0.0.1:3000`。

## 建立資料並確認 dashboard

部署 `todo-bff` 和 `todo-api` 後，用 BFF 建立幾筆 Todo：

```bash
kubectl port-forward service/todo-bff 8080:8080 -n todo
```

```bash
for title in trace-one trace-two trace-three; do
  curl --fail \
    -H 'content-type: application/json' \
    --data "{\"title\":\"$title\"}" \
    http://127.0.0.1:8080/api/todos
done
```

等待一個 Prometheus scrape interval 後，dashboard 的 service 下拉選單應出現 `todo-bff` 與 `todo-api`。選擇其中一個服務後，可看到 request rate、p95 latency、5xx ratio 與 application logs。

Tempo datasource 會收到相同請求的 Trace。從 Grafana 左側的 Explore 選擇 Tempo，使用 TraceQL 查詢：

```traceql
{ resource.service.name = "todo-api" }
```

目前 Todo 資料存在記憶體，沒有資料庫 span。Loki 收到的 log 由 `todo-api` 的 `Todo created.` 事件產生；沒有將 Todo title、`Authorization` header 或使用者資料寫入 log。

## 驗證 manifest 與設定檔

```bash
kubectl kustomize src/3-observability/grafana > /tmp/grafana.yaml
kubectl apply --dry-run=client -f /tmp/grafana.yaml
rm /tmp/grafana.yaml

jq empty src/3-observability/grafana/todo-service-overview.json
```
