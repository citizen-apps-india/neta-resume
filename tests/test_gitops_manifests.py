"""Static deployment-policy tests that run without a Kubernetes cluster."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parents[1]
DEPLOY = ROOT / "deploy"


def _documents(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [
            document
            for document in yaml.safe_load_all(stream)
            if isinstance(document, dict)
        ]


def _yaml_documents(directory: Path) -> list[dict[str, Any]]:
    return [
        document for path in directory.rglob("*.yaml") for document in _documents(path)
    ]


def _application(name: str) -> dict[str, Any]:
    applications = {
        document["metadata"]["name"]: document
        for document in _yaml_documents(DEPLOY / "argocd" / "production")
        if document.get("kind") == "Application"
    }
    return applications[name]


def test_kustomize_references_are_local_and_exist() -> None:
    for kustomization_path in DEPLOY.rglob("kustomization.yaml"):
        kustomization = _documents(kustomization_path)[0]
        references: list[str] = list(kustomization.get("resources", []))
        references.extend(
            patch["path"]
            for patch in kustomization.get("patches", [])
            if isinstance(patch, dict) and "path" in patch
        )
        for reference in references:
            target = (kustomization_path.parent / reference).resolve()
            assert target.is_relative_to(ROOT)
            assert target.exists(), f"missing Kustomize reference: {target}"


def test_gitops_sources_contain_no_native_secret_values() -> None:
    documents = _yaml_documents(DEPLOY)
    assert all(document.get("kind") != "Secret" for document in documents)
    rendered_text = "\n".join(path.read_text() for path in DEPLOY.rglob("*.yaml"))
    assert not re.search(r"postgres(?:ql)?(?:\+\w+)?://[^\s]+:[^\s]+@", rendered_text)
    assert "BEGIN PRIVATE KEY" not in rendered_text


def test_control_and_reconciler_are_restricted_and_bounded() -> None:
    workload_documents = _yaml_documents(DEPLOY / "k8s" / "base")
    workloads = [
        document
        for document in workload_documents
        if document.get("kind") in {"Deployment", "Job"}
    ]
    assert {workload["kind"] for workload in workloads} == {"Deployment", "Job"}
    for workload in workloads:
        pod_spec = (
            workload["spec"]["template"]["spec"]
            if workload["kind"] == "Deployment"
            else workload["spec"]["template"]["spec"]
        )
        assert pod_spec["automountServiceAccountToken"] is False
        assert pod_spec["securityContext"]["runAsNonRoot"] is True
        assert pod_spec["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault"
        for container in pod_spec["containers"]:
            security = container["securityContext"]
            assert security["allowPrivilegeEscalation"] is False
            assert security["readOnlyRootFilesystem"] is True
            assert security["capabilities"]["drop"] == ["ALL"]
            assert set(container["resources"]) == {"requests", "limits"}
            assert not container["image"].endswith(":latest")
    deployment = next(item for item in workloads if item["kind"] == "Deployment")
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert {"startupProbe", "readinessProbe", "livenessProbe"} <= set(container)


def test_namespace_and_network_default_to_restricted() -> None:
    overlay = _documents(
        DEPLOY / "k8s" / "overlays" / "production" / "kustomization.yaml"
    )[0]
    assert overlay["namespace"] == "neta-production"
    policies = {
        document["metadata"]["name"]: document
        for document in _yaml_documents(DEPLOY / "k8s" / "base")
        if document.get("kind") == "NetworkPolicy"
    }
    assert {
        "default-deny",
        "allow-dns-egress",
        "allow-same-namespace",
        "allow-postgres-egress",
        "allow-ingestion-http-egress",
    } <= policies.keys()
    assert policies["default-deny"]["spec"]["policyTypes"] == ["Ingress", "Egress"]
    postgres_patch = _documents(
        DEPLOY / "k8s" / "overlays" / "production" / "network-postgres-patch.yaml"
    )[0]
    postgres_egress = postgres_patch["spec"]["egress"][0]["to"]
    assert {target["ipBlock"]["cidr"] for target in postgres_egress} == {"10.42.0.0/16"}
    stack = yaml.safe_load((ROOT / "infra" / "Pulumi.prod.yaml").read_text())
    assert stack["config"]["neta-resume-infra:vpcCidr"] == "10.42.0.0/16"


def test_external_secrets_use_pod_identity_without_static_aws_keys() -> None:
    store = _documents(
        DEPLOY / "k8s" / "secrets" / "overlays" / "production" / "secret-store.yaml"
    )[0]
    aws = store["spec"]["provider"]["aws"]
    assert aws["service"] == "SecretsManager"
    assert "auth" not in aws
    external_secrets = [
        document
        for document in _yaml_documents(DEPLOY / "k8s" / "secrets" / "base")
        if document.get("kind") == "ExternalSecret"
    ]
    target_keys = {
        item["secretKey"]
        for external_secret in external_secrets
        for item in external_secret["spec"]["data"]
    }
    assert target_keys == {
        "NETA_DATABASE_URL",
        "NETA_BACKEND_DATABASE_URL",
        "NETA_MIGRATE_DATABASE_URL",
        "postgresql-password",
    }


def test_argo_children_are_pinned_scoped_and_bootstrap_gated() -> None:
    children = [
        document
        for document in _yaml_documents(DEPLOY / "argocd" / "production")
        if document.get("kind") == "Application"
    ]
    assert len(children) == 3
    assert all(application["spec"]["project"] != "default" for application in children)
    for application in children:
        assert "automated" not in application["spec"]["syncPolicy"]
        assert (
            "CreateNamespace=true"
            not in application["spec"]["syncPolicy"]["syncOptions"]
        )
        assert application["spec"]["destination"]["name"] == "neta-production"
        assert application["spec"]["destination"]["namespace"] == "neta-production"
        sources = application["spec"].get("sources") or [application["spec"]["source"]]
        for source in sources:
            assert source["targetRevision"] != "HEAD"
    assert not any(
        application["metadata"]["name"] == "neta-external-secrets"
        for application in children
    )

    # The AppProject contains an account-specific Identity Center group ID and is Pulumi-owned.
    assert not any(
        document.get("kind") == "AppProject"
        for document in _yaml_documents(DEPLOY / "argocd" / "production")
    )


def test_dagster_chart_matches_runtime_and_uses_kubernetes_jobs() -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    dagster_version = next(
        package["version"]
        for package in lock["package"]
        if package["name"] == "dagster"
    )
    application = _application("neta-production-dagster")
    assert application["spec"]["sources"][0]["targetRevision"] == dagster_version

    values = _documents(DEPLOY / "argocd" / "values" / "dagster-production.yaml")[0]
    assert values["postgresql"]["enabled"] is False
    assert values["runLauncher"]["type"] == "K8sRunLauncher"
    deployment = values["dagster-user-deployments"]["deployments"][0]
    user_service_account = values["dagster-user-deployments"]["serviceAccount"]
    assert user_service_account["name"] == "neta-ingestion"
    assert user_service_account["annotations"] == {}
    assert values["serviceAccount"]["annotations"] == {}
    assert deployment["image"]["tag"] != "latest"
    environment = {
        item["name"]: item.get("value", item.get("valueFrom"))
        for item in deployment["env"]
    }
    assert environment["NETA_RAW_STORE_BACKEND"] == "s3"
    assert (
        environment["NETA_RAW_S3_BUCKET"]["configMapKeyRef"]["name"] == "neta-platform"
    )
    assert environment["NETA_RAW_S3_PREFIX"] == "production/raw"
    assert values["runLauncher"]["config"]["k8sRunLauncher"]["jobNamespace"] == (
        "neta-production"
    )
    assert values["telemetry"]["enabled"] is False
    assert values["ingress"]["enabled"] is False


def test_deployment_tree_is_production_only() -> None:
    rendered_text = "\n".join(path.read_text() for path in DEPLOY.rglob("*.yaml"))

    assert "neta-staging" not in rendered_text
    assert "staging/runtime" not in rendered_text
    assert not (DEPLOY / "argocd" / "staging").exists()
    assert not (DEPLOY / "k8s" / "overlays" / "staging").exists()
    assert not (DEPLOY / "k8s" / "secrets" / "overlays" / "staging").exists()
