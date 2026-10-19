[English](README.md) | [繁體中文](README-zh-TW.md)

# OpenTelemetry and Grafana

For Days 09-13, `otel-collector/` contains the Collector gateway and `grafana/` contains Prometheus, Loki, Tempo, Grafana, and the dashboard. The [Todo API and BFF](../0-todo-microservices/README.md) include the cross-service tracing code.

Run all commands below from the repository root.

## Deploy the observability components

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

The Collector accepts OTLP/gRPC on `4317` and OTLP/HTTP on `4318`. It applies a memory limiter, adds `platform.name=todo-platform`, removes the listed sensitive attributes, and batches exports. Metrics are exposed on `8889` for Prometheus to scrape every 15 seconds. Logs go to Loki and traces to Tempo. Exporters may report connection errors while their backends are starting.

All three pipelines also use a `debug` exporter for local inspection. Keep it in controlled development environments and retain the backends for storage and queries. Exclude tokens, Authorization headers, and Todo contents at the application source.

## Verify cross-service trace context

Deploy the BFF and API using the [Kubernetes guide](../1-kubernetes/README.md). Ensure their OTLP endpoint is `http://otel-collector.observability.svc:4317`, then forward the BFF Service:

```bash
kubectl port-forward service/todo-bff 8080:8080 -n todo
```

In another terminal, send a request with a known trace ID:

```bash
curl --fail \
  -H 'content-type: application/json' \
  -H 'traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01' \
  --data '{"title":"trace-test"}' \
  http://127.0.0.1:8080/api/todos
kubectl logs deployment/otel-collector -n observability
```

Expect the same trace to contain a BFF server span, an HTTP client span, an API server span, and `todo.create`. There is no database span because data is stored in memory.

To check only whether the Collector process responds, run `kubectl port-forward deployment/otel-collector 13133:13133 -n observability` in another terminal, then run `curl --fail http://127.0.0.1:13133/`. A successful health endpoint does not prove data reached its final backend.

## Query Grafana

```bash
kubectl port-forward service/grafana 3000:3000 -n observability
```

Open `http://127.0.0.1:3000` and sign in with the development credentials `admin` / `admin`. The provisioned `Todo service overview` dashboard includes request rate, p95, a latency heatmap, 5xx ratio, and application logs. Filter by service and route, and allow at least one scrape interval. A small number of requests may not immediately produce p95 values; an absent 5xx series does not necessarily mean a query failed.

In Grafana Explore, select the Tempo datasource and use this TraceQL query:

```traceql
{ resource.service.name = "todo-api" }
```

Tempo's Trace-to-Logs links to Loki, and Loki's TraceID derived field links back to a trace. These correlations depend on the actual service attributes, trace IDs, and logs received.

Each component runs as one replica with `emptyDir` storage; recreating Pods loses data and local Grafana settings. Production use requires persistence, HA, account management, backups, and a retention policy. No external Ingress is included.
