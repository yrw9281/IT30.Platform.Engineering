[English](README.md) | [繁體中文](README-zh-TW.md)

# IT30.Platform.Engineering

Code and articles for the 2026 iThome Ironman Challenge series, ["Microservices built. What next? The golden path to platform engineering"（寫完微服務然後呢？走向平台工程的黃金路徑）](https://ithelp.ithome.com.tw/users/20168953/ironman/9797).

This series continues [IT30.Todo.Microservices](https://github.com/yrw9281/IT30.Todo.Microservices), which covered DDD, Clean Architecture, and microservices with .NET. It uses a small Todo application to explain Kubernetes deployment, GitOps, and an Internal Developer Platform (IDP) built with Backstage.

## Project overview

The examples cover:

- Kubernetes resources, Helm, Kustomize, and custom resource definitions (CRDs).
- GitOps synchronization with Argo CD and ApplicationSet.
- Metrics, logs, and distributed traces with OpenTelemetry and Grafana.
- GitHub Actions for application builds and container image publishing to GitHub Container Registry (GHCR).
- Backstage Catalog, Software Templates, and Kubernetes resource queries.
- A Python/Kopf Operator that turns a `Microservice` resource into a Deployment and Service, then reports rollout health.
- Kubernetes RBAC and OPA Gatekeeper policies for resource configuration.

The sample has a web frontend, a .NET 8 / ASP.NET Core backend for frontend (BFF), and a Todo API. It stores data in memory, without the earlier series' database or messaging infrastructure.

## Architecture

![Delivery workflow from Backstage through Git and Argo CD to Kubernetes](doc/assets/day-17-backstage-to-kubernetes-flow.png)

A Backstage template opens a GitHub pull request to update the Todo API image. After review and merge, Argo CD synchronizes the `Microservice` resource from Git. The Operator creates or updates its Deployment and Service, then reports health for the current resource generation. Backstage shows the service catalog and Kubernetes resources; it neither deploys workloads directly nor records the full delivery history.

Application traffic follows `Browser → Ingress → BFF → Todo API`. The API and BFF send telemetry to the OpenTelemetry Collector. Prometheus, Loki, and Tempo store metrics, logs, and traces for querying in Grafana.

![Todo web application](doc/assets/day-30-todo-web.png)

![Grafana Todo service overview dashboard](doc/assets/day-30-grafana-service-overview.png)

## Getting started

### Run the Todo application locally

Install Git, Docker, and Docker Compose, then run:

```bash
git clone https://github.com/yrw9281/IT30.Platform.Engineering.git
cd IT30.Platform.Engineering
docker compose -f src/0-todo-microservices/docker-compose.yml up -d --build
docker compose -f src/0-todo-microservices/docker-compose.yml ps
```

Open <http://localhost:8081> to add, complete, and delete todos. The BFF is available at <http://localhost:8080>. This Compose setup disables OpenTelemetry export and does not install the platform components.

To stop the application:

```bash
docker compose -f src/0-todo-microservices/docker-compose.yml down
```

Todo data is stored in the API process and disappears when that process restarts.

### Deploy the platform to Kubernetes

Use the [complete platform installation guide](src/final/README.md) for a clean, reachable Kubernetes cluster. It includes the application, Argo CD, an Ingress controller, the observability stack, the Operator, Backstage, and Gatekeeper.

You need a kubeconfig with administrator access and `kubectl` with Kustomize support. Follow the guide's installation and credential steps. Push local changes before synchronization: Argo CD reads remote Git. For a fork, update the repository and image references.

Each guide has English and Traditional Chinese versions linked at the top. Choose either the numbered chapter examples or `src/final/`; do not apply both to the same resources.

## Repository layout

| Path | Contents |
| --- | --- |
| [`doc/en/`](doc/en/) | The 30 articles in English |
| [`doc/zh-tw/`](doc/zh-tw/) | The 30 articles in Traditional Chinese |
| [`doc/assets/`](doc/assets/) | Architecture diagrams and screenshots |
| [`src/0-todo-microservices/`](src/0-todo-microservices/README.md) | Todo API, BFF, web frontend, and Docker Compose |
| [`src/1-kubernetes/`](src/1-kubernetes/README.md) | Kubernetes manifests, Kustomize, and the CRD |
| [`src/2-gitops/`](src/2-gitops/README.md) | Argo CD Applications and custom health checks |
| [`src/3-observability/`](src/3-observability/README.md) | OpenTelemetry Collector and Grafana stack |
| [`src/4-idp/`](src/4-idp/README.md) | Backstage, templates, Operator, and RBAC |
| [`src/5-config/`](src/5-config/README.md) | Chapter examples of Todo API GitOps configuration |
| [`src/6-policy/`](src/6-policy/README.md) | Gatekeeper policy examples |
| [`src/final/`](src/final/README.md) | Self-contained platform setup for a clean cluster |
| [`.github/workflows/`](.github/workflows/) | Chapter CI and image publishing workflows |
| [`outline.md`](outline.md) | Series outline |

## Documentation

Start with [Day 01: Why platform engineering after microservices?](doc/en/D01.md), or use these entry points:

| Days | Topic | First article |
| --- | --- | --- |
| 01-05 | Introduction and Kubernetes deployment fundamentals | [Day 01](doc/en/D01.md) |
| 06-08 | GitOps with Argo CD | [Day 06](doc/en/D06.md) |
| 09-13 | Observability | [Day 09](doc/en/D09.md) |
| 14-16 | CI and the GitOps handoff | [Day 14](doc/en/D14.md) |
| 17-26 | Backstage and the Microservice Operator | [Day 17](doc/en/D17.md) |
| 27-29 | API access and resource policies | [Day 27](doc/en/D27.md) |
| 30 | Todo API image update walkthrough and series review | [Day 30](doc/en/D30.md) |

For the preceding application architecture series, see [IT30.Todo.Microservices](https://github.com/yrw9281/IT30.Todo.Microservices) and its [2024 iThome articles](https://ithelp.ithome.com.tw/users/20168953/ironman/7881).

## Demo scope and limitations

Use these examples in a controlled learning environment:

- The Todo API uses single-replica, in-memory storage. The final setup also uses ephemeral storage for observability data and Backstage SQLite.
- Backstage uses Guest sign-in and an allow-all permission policy. Keep its entry point on loopback; production requires authentication, authorization, TLS, and persistent storage.
- Gatekeeper policies have limited resource coverage and use different enforcement modes. Their presence does not establish complete tenant isolation or supply-chain verification.
- Git synchronization, current-generation rollout health, and application behavior require separate checks. Rendering manifests or merging a PR does not prove a successful deployment.
- The final setup includes a pinned ingress-nginx snapshot for the tutorial. The project retired in March 2026; choose a maintained alternative for new production platforms.

See the [installation guide's version and limitation notes](src/final/README.md#versions-and-limitations) for versions, credentials, and deployment limits.

## Acknowledgements

Thanks to iThome for organizing the Ironman Challenge and to the readers following the series.
