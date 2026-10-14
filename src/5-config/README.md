# Todo API 的 GitOps 設定

這裡是 Day 24 的 Backstage 模板提出 PR 時使用的目標目錄。`apps/todo-api/overlays/dev/` 保存 `Microservice` 與 `kustomization.yaml`，Dev 沿用既有的 `todo` Namespace，不另外建立環境。

`microservice.yaml` 指定 image digest 與 port `8080`。換版時只修改 `spec.image`，不順便改服務名稱、Namespace 或 port；digest 應來自 Todo API 的受信任 CI 輸出，不能只檢查格式。

從 repository 根目錄可先查看 Kustomize 產物：

```bash
kubectl kustomize src/5-config/apps/todo-api/overlays/dev
```

渲染成功不代表 Kubernetes schema、image 來源檢查或 rollout 已通過。設定 PR 仍需要獨立檢查、review 與分支保護。

[Argo CD](../2-gitops/README.md) 的 `todo-config.yaml` 可讀取本 repository 的 `main` 與這個目錄。啟用前須完成 CRD／Operator 部署與工作負載管理權移交；原生資源的 `todo.yaml` 不讀取這裡。建立或合併 PR 本身不會執行部署，Argo CD 同步 CR 後才由 Operator 處理工作負載。
