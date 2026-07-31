"""Pulumi-owned cluster operators and account-specific platform configuration."""

from __future__ import annotations

from dataclasses import dataclass

import pulumi
import pulumi_kubernetes as k8s

from neta_infra.cluster import KubernetesCluster
from neta_infra.data import DataLayer
from neta_infra.identity import NodeRoles
from neta_infra.karpenter import KarpenterInfrastructure
from neta_infra.settings import InfraSettings
from neta_infra.workload_identity import WorkloadRoles


@dataclass(frozen=True, slots=True)
class PlatformAddons:
    provider: k8s.Provider
    namespace: k8s.core.v1.Namespace
    platform_config: k8s.core.v1.ConfigMap
    database_service: k8s.core.v1.Service
    external_secrets: k8s.helm.v3.Release
    karpenter_crds: k8s.helm.v3.Release
    karpenter: k8s.helm.v3.Release
    node_class: k8s.apiextensions.CustomResource
    node_pool: k8s.apiextensions.CustomResource


def _release_options(
    provider: k8s.Provider,
    depends_on: list[pulumi.Resource],
) -> pulumi.ResourceOptions:
    return pulumi.ResourceOptions(provider=provider, depends_on=depends_on)


def create_platform_addons(
    settings: InfraSettings,
    kubernetes: KubernetesCluster,
    data: DataLayer,
    workloads: WorkloadRoles,
    karpenter_infrastructure: KarpenterInfrastructure,
    node_roles: NodeRoles,
) -> PlatformAddons:
    system_node_selector = {
        "kubernetes.io/os": "linux",
        "neta.dev/workload-tier": "system",
    }
    restricted_pod_security = {
        "runAsNonRoot": True,
        "runAsUser": 65532,
        "runAsGroup": 65532,
        "fsGroup": 65532,
        "seccompProfile": {"type": "RuntimeDefault"},
    }
    restricted_container_security = {
        "allowPrivilegeEscalation": False,
        "readOnlyRootFilesystem": True,
        "capabilities": {"drop": ["ALL"]},
    }
    provider = k8s.Provider(
        "platform-kubernetes",
        kubeconfig=kubernetes.cluster.kubeconfig_json,
        enable_server_side_apply=True,
    )
    namespace = k8s.core.v1.Namespace(
        "production-namespace",
        metadata={
            "name": "neta-production",
            "labels": {
                "app.kubernetes.io/part-of": "neta-resume",
                "environment": "production",
                "pod-security.kubernetes.io/enforce": "restricted",
                "pod-security.kubernetes.io/enforce-version": "latest",
                "pod-security.kubernetes.io/audit": "restricted",
                "pod-security.kubernetes.io/audit-version": "latest",
                "pod-security.kubernetes.io/warn": "restricted",
                "pod-security.kubernetes.io/warn-version": "latest",
            },
        },
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=[kubernetes.system_nodes],
            protect=settings.protect_data,
        ),
    )
    platform_config = k8s.core.v1.ConfigMap(
        "production-platform-config",
        metadata={"name": "neta-platform", "namespace": "neta-production"},
        data={
            "NETA_RAW_S3_BUCKET": data.evidence_bucket.bucket,
            "NETA_RAW_S3_REGION": settings.region,
            "NETA_RAW_S3_PREFIX": "production/raw",
        },
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[namespace]),
    )
    database_service = k8s.core.v1.Service(
        "production-database-service",
        metadata={"name": "neta-postgresql", "namespace": "neta-production"},
        spec={
            "type": "ExternalName",
            "externalName": data.database.address,
            "ports": [{"name": "postgresql", "port": 5432, "protocol": "TCP"}],
        },
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[namespace]),
    )

    external_secrets = k8s.helm.v3.Release(
        "external-secrets",
        name="external-secrets",
        namespace="external-secrets",
        create_namespace=True,
        chart="external-secrets",
        version=settings.external_operator_chart_version,
        repository_opts=k8s.helm.v3.RepositoryOptsArgs(
            repo="https://charts.external-secrets.io",
        ),
        atomic=True,
        cleanup_on_fail=True,
        max_history=5,
        timeout=900,
        values={
            "installCRDs": True,
            "replicaCount": 2,
            "leaderElect": True,
            "serviceAccount": {"create": True, "name": "external-secrets"},
            "nodeSelector": system_node_selector,
            "podSecurityContext": restricted_pod_security,
            "securityContext": restricted_container_security,
            "resources": {
                "requests": {"cpu": "50m", "memory": "96Mi"},
                "limits": {"cpu": "500m", "memory": "384Mi"},
            },
            "webhook": {
                "replicaCount": 2,
                "nodeSelector": system_node_selector,
                "podSecurityContext": restricted_pod_security,
                "securityContext": restricted_container_security,
                "resources": {
                    "requests": {"cpu": "25m", "memory": "64Mi"},
                    "limits": {"cpu": "250m", "memory": "256Mi"},
                },
            },
            "certController": {
                "replicaCount": 2,
                "nodeSelector": system_node_selector,
                "podSecurityContext": restricted_pod_security,
                "securityContext": restricted_container_security,
                "resources": {
                    "requests": {"cpu": "25m", "memory": "64Mi"},
                    "limits": {"cpu": "250m", "memory": "256Mi"},
                },
            },
        },
        opts=_release_options(
            provider,
            [kubernetes.system_nodes, workloads.secrets_reader_identity],
        ),
    )

    karpenter_crds = k8s.helm.v3.Release(
        "karpenter-crds",
        name="karpenter-crd",
        namespace="kube-system",
        chart="oci://public.ecr.aws/karpenter/karpenter-crd",
        version=settings.karpenter_chart_version,
        atomic=True,
        cleanup_on_fail=True,
        max_history=5,
        timeout=900,
        opts=_release_options(provider, [kubernetes.system_nodes]),
    )
    karpenter = k8s.helm.v3.Release(
        "karpenter",
        name="karpenter",
        namespace="kube-system",
        chart="oci://public.ecr.aws/karpenter/karpenter",
        version=settings.karpenter_chart_version,
        skip_crds=True,
        atomic=True,
        cleanup_on_fail=True,
        max_history=5,
        timeout=900,
        values={
            "replicas": 2,
            "serviceAccount": {"create": True, "name": "karpenter"},
            "nodeSelector": system_node_selector,
            "controller": {
                "resources": {
                    "requests": {"cpu": "250m", "memory": "512Mi"},
                    "limits": {"cpu": "1", "memory": "1Gi"},
                }
            },
            "settings": {
                "clusterName": settings.cluster_name,
                "eksControlPlane": True,
                "interruptionQueue": karpenter_infrastructure.interruption_queue.name,
                "preferencePolicy": "Respect",
                "minValuesPolicy": "BestEffort",
            },
        },
        opts=_release_options(
            provider,
            [karpenter_crds, karpenter_infrastructure.controller_identity],
        ),
    )

    node_class = k8s.apiextensions.CustomResource(
        "general-node-class",
        api_version="karpenter.k8s.aws/v1",
        kind="EC2NodeClass",
        metadata={"name": "general"},
        spec={
            "amiFamily": "AL2023",
            "role": node_roles.karpenter.name,
            "amiSelectorTerms": [{"alias": settings.karpenter_ami_alias}],
            "subnetSelectorTerms": [{"tags": {"karpenter.sh/discovery": settings.cluster_name}}],
            "securityGroupSelectorTerms": [
                {"tags": {"karpenter.sh/discovery": settings.cluster_name}}
            ],
            "metadataOptions": {
                "httpEndpoint": "enabled",
                "httpProtocolIPv6": "disabled",
                "httpPutResponseHopLimit": 1,
                "httpTokens": "required",
            },
            "blockDeviceMappings": [
                {
                    "deviceName": "/dev/xvda",
                    "ebs": {
                        "volumeSize": "50Gi",
                        "volumeType": "gp3",
                        "encrypted": True,
                        "kmsKeyID": kubernetes.encryption_key.arn,
                        "deleteOnTermination": True,
                    },
                }
            ],
            "tags": {**settings.common_tags, "ManagedBy": "karpenter"},
        },
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=[karpenter, kubernetes.karpenter_node_access],
        ),
    )
    node_pool = k8s.apiextensions.CustomResource(
        "general-node-pool",
        api_version="karpenter.sh/v1",
        kind="NodePool",
        metadata={"name": "general"},
        spec={
            "weight": 50,
            "template": {
                "metadata": {
                    "labels": {
                        "neta.dev/workload-tier": "application",
                        "app.kubernetes.io/part-of": "neta-resume",
                    }
                },
                "spec": {
                    "nodeClassRef": {
                        "group": "karpenter.k8s.aws",
                        "kind": "EC2NodeClass",
                        "name": "general",
                    },
                    "expireAfter": "720h",
                    "terminationGracePeriod": "1h",
                    "requirements": [
                        {
                            "key": "kubernetes.io/arch",
                            "operator": "In",
                            "values": ["amd64"],
                        },
                        {
                            "key": "kubernetes.io/os",
                            "operator": "In",
                            "values": ["linux"],
                        },
                        {
                            "key": "karpenter.sh/capacity-type",
                            "operator": "In",
                            "values": ["spot", "on-demand"],
                        },
                        {
                            "key": "karpenter.k8s.aws/instance-category",
                            "operator": "In",
                            "values": ["c", "m", "r"],
                            "minValues": 2,
                        },
                        {
                            "key": "karpenter.k8s.aws/instance-generation",
                            "operator": "Gt",
                            "values": ["5"],
                        },
                        {
                            "key": "karpenter.k8s.aws/instance-size",
                            "operator": "In",
                            "values": ["medium", "large", "xlarge", "2xlarge"],
                        },
                    ],
                },
            },
            "limits": {"cpu": "64", "memory": "128Gi"},
            "disruption": {
                "consolidationPolicy": "WhenEmptyOrUnderutilized",
                "consolidateAfter": "5m",
                "budgets": [{"nodes": "20%"}],
            },
        },
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[node_class]),
    )
    return PlatformAddons(
        provider=provider,
        namespace=namespace,
        platform_config=platform_config,
        database_service=database_service,
        external_secrets=external_secrets,
        karpenter_crds=karpenter_crds,
        karpenter=karpenter,
        node_class=node_class,
        node_pool=node_pool,
    )
