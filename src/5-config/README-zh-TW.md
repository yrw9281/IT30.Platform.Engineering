[English](README.md) | [繁體中文](README-zh-TW.md)

# Todo API 的 GitOps 設定

Day 24 的 Backstage 模板會對 `apps/todo-api/overlays/dev/` 提出設定 PR。這裡保存 Dev 的 `Microservice` 與 `kustomization.yaml`，沿用既有的 `todo` Namespace。

`microservice.yaml` 指定 image digest 與 port `8080`。換版時只修改 `spec.image`，保留服務名稱、Namespace 與 port。請使用受信任的 Todo API CI 輸出，並在審查時核對 digest 來源。

從儲存庫根目錄預覽 Kustomize 輸出：

```bash
kubectl kustomize src/5-config/apps/todo-api/overlays/dev
```

渲染只產生 YAML。Kubernetes schema 與 image 來源須另設 PR 檢查，搭配人工審查及分支保護，部署後再確認新版是否就緒。

[Argo CD](../2-gitops/README-zh-TW.md) 的 `todo-config.yaml` 從 `main` 讀取這個目錄；原生資源的 `todo.yaml` 使用其他來源。啟用同步前，須部署 CRD 與 Operator，並完成工作負載管理權移交。PR 合併後，要等 Argo CD 同步 CR，Operator 才會更新工作負載。
