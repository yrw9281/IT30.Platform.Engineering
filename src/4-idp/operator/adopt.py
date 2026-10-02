"""Explicit, one-time adoption of the existing Todo API; never called by Kopf."""
from copy import deepcopy

from kubernetes import client, config

from resources import check_owner, desired_resources


def adopt() -> None:
    config.load_kube_config()
    api = client.ApiClient()
    apps, core = client.AppsV1Api(api), client.CoreV1Api(api)
    cr = client.CustomObjectsApi(api).get_namespaced_custom_object(
        "platform.example.io", "v1alpha1", "todo", "microservices", "todo-api")
    desired, _ = desired_resources(cr)
    deployment = api.sanitize_for_serialization(apps.read_namespaced_deployment("todo-api", "todo"))
    service = api.sanitize_for_serialization(core.read_namespaced_service("todo-api", "todo"))
    if deployment["spec"]["selector"] != desired["spec"]["selector"]:
        raise ValueError("Existing Deployment selector differs; adoption would require replacement")
    if service["spec"].get("type") != "ClusterIP":
        raise ValueError("This example only adopts a ClusterIP Service")
    for resource in (deployment, service):
        if resource["metadata"].get("deletionTimestamp"):
            raise ValueError("Cannot adopt a resource that is being deleted")
        if resource["metadata"].get("ownerReferences"):
            check_owner(resource, cr)
        annotations = resource["metadata"].get("annotations", {})
        labels = resource["metadata"].get("labels", {})
        if ("argocd.argoproj.io/tracking-id" in annotations
                or "argocd.argoproj.io/instance" in labels):
            raise ValueError("Remove these children from Argo CD management before adoption")
    for resource, replace in ((deployment, apps.replace_namespaced_deployment),
                              (service, core.replace_namespaced_service)):
        resource["metadata"]["ownerReferences"] = deepcopy(desired["metadata"]["ownerReferences"])
        resource.pop("status", None)
        replace("todo-api", "todo", resource, _request_timeout=(5, 20))
        print(f'Adopted {resource["kind"]}/todo-api in todo')


if __name__ == "__main__":
    adopt()
