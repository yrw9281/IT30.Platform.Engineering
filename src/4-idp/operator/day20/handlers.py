import kopf


@kopf.on.startup()
def configure(settings, **_):
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage()
    settings.persistence.diffbase_storage = kopf.AnnotationsDiffBaseStorage()
    settings.execution.max_workers = 1
    settings.posting.enabled = False
    settings.scanning.disabled = True


@kopf.on.create("platform.example.io", "v1alpha1", "microservices")
@kopf.on.update("platform.example.io", "v1alpha1", "microservices", field="spec")
@kopf.on.resume("platform.example.io", "v1alpha1", "microservices")
def accept(name, namespace, spec, logger, patch, **_):
    logger.info("Accepted %s/%s: image=%s port=%s", namespace, name,
                spec.get("image"), spec.get("port"))
    patch.status["phase"] = "Accepted"
