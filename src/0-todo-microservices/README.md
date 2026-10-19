[English](README.md) | [繁體中文](README-zh-TW.md)

# Todo microservices

`Todo.Api` stores todos, `Todo.Bff` forwards API requests, and `WebApp` serves the web frontend. The API stores data in process memory, with no database; restarting it loses the todos.

Run all commands below from the repository root.

## Run locally

You need Docker and Docker Compose:

```bash
docker compose -f src/0-todo-microservices/docker-compose.yml up --build
```

Open `http://localhost:8081` to add, complete, and delete todos. The BFF is available at `http://localhost:8080`. Compose disables OTel export, so you do not need a Collector.

## Build images for Kubernetes

```bash
docker build -t todo-api:0.1.0 src/0-todo-microservices/Todo.Api
docker build -t todo-bff:0.1.0 src/0-todo-microservices/Todo.Bff
docker build -t todo-web:0.1.0 src/0-todo-microservices/WebApp
```

See the [Kubernetes guide](../1-kubernetes/README.md) for deployment instructions. Both .NET 8 projects include OpenTelemetry instrumentation; the deployment manifests supply the in-cluster OTLP configuration.

## CI and image publishing

The [Day 14](../../doc/zh-tw/D14.md) workflow, `.github/workflows/todo-ci.yaml`, runs restore, test, and build for the API and BFF on pull requests. There is no unit test project, so `dotnet test` can succeed without testing application behavior.

The [Day 15-16](../../doc/zh-tw/D15.md) workflow, `.github/workflows/todo-image.yaml`, runs on `todo-api-v*` or `todo-bff-v*` tags. It publishes the tagged service and outputs its GHCR image digest. Propose a release by putting that digest in a configuration pull request; this workflow does not update GitOps configuration or deploy to the cluster.
