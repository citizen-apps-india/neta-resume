"""AWS-managed Argo CD capability and the single GitOps root application."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pulumi
import pulumi_aws as aws
import pulumi_kubernetes as k8s

from neta_infra.addons import PlatformAddons
from neta_infra.cluster import KubernetesCluster
from neta_infra.settings import InfraSettings


@dataclass(frozen=True, slots=True)
class GitOpsBootstrap:
    provider: k8s.Provider
    capability_role: aws.iam.Role
    capability: aws.eks.Capability
    cluster_view_access: aws.eks.AccessPolicyAssociation
    production_namespace_access: aws.eks.AccessPolicyAssociation
    cluster_registration: k8s.core.v1.Secret
    production_project: k8s.apiextensions.CustomResource
    root_application: k8s.apiextensions.CustomResource


def _capability_assume_role_policy() -> str:
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "capabilities.eks.amazonaws.com"},
                    "Action": ["sts:AssumeRole", "sts:TagSession"],
                }
            ],
        }
    )


def create_gitops_bootstrap(
    settings: InfraSettings,
    kubernetes: KubernetesCluster,
    addons: PlatformAddons,
) -> GitOpsBootstrap:
    provider = addons.provider
    capability_role = aws.iam.Role(
        "argocd-capability-role",
        name=f"{settings.cluster_name}-argocd-capability",
        assume_role_policy=_capability_assume_role_policy(),
        description="Amazon EKS managed Argo CD capability role",
        tags=settings.common_tags,
    )
    capability = aws.eks.Capability(
        "argocd-capability",
        cluster_name=kubernetes.cluster.eks_cluster.name,
        capability_name="argocd",
        type="ARGOCD",
        role_arn=capability_role.arn,
        delete_propagation_policy="RETAIN",
        configuration=aws.eks.CapabilityConfigurationArgs(
            argo_cd=aws.eks.CapabilityConfigurationArgoCdArgs(
                namespace="argocd",
                aws_idc=aws.eks.CapabilityConfigurationArgoCdAwsIdcArgs(
                    idc_instance_arn=settings.argocd_identity_center_instance_arn,
                    idc_region=settings.argocd_identity_center_region,
                ),
                rbac_role_mappings=[
                    aws.eks.CapabilityConfigurationArgoCdRbacRoleMappingArgs(
                        role="VIEWER",
                        identities=[
                            aws.eks.CapabilityConfigurationArgoCdRbacRoleMappingIdentityArgs(
                                id=settings.argocd_platform_admin_group_id,
                                type="SSO_GROUP",
                            )
                        ],
                    )
                ],
            )
        ),
        tags=settings.common_tags,
        opts=pulumi.ResourceOptions(
            depends_on=[kubernetes.cluster.eks_cluster],
            protect=settings.protect_data,
        ),
    )
    cluster_view_access = aws.eks.AccessPolicyAssociation(
        "argocd-cluster-view-access",
        cluster_name=kubernetes.cluster.eks_cluster.name,
        principal_arn=capability_role.arn,
        policy_arn="arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy",
        access_scope=aws.eks.AccessPolicyAssociationAccessScopeArgs(type="cluster"),
        opts=pulumi.ResourceOptions(depends_on=[capability]),
    )
    production_namespace_access = aws.eks.AccessPolicyAssociation(
        "argocd-production-namespace-access",
        cluster_name=kubernetes.cluster.eks_cluster.name,
        principal_arn=capability_role.arn,
        policy_arn="arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy",
        access_scope=aws.eks.AccessPolicyAssociationAccessScopeArgs(
            type="namespace",
            namespaces=["neta-production"],
        ),
        opts=pulumi.ResourceOptions(depends_on=[capability]),
    )

    # The managed capability does not automatically register its own EKS cluster as a target.
    cluster_registration = k8s.core.v1.Secret(
        "argocd-production-cluster",
        metadata={
            "name": "neta-production-cluster",
            "namespace": "argocd",
            "labels": {"argocd.argoproj.io/secret-type": "cluster"},
        },
        string_data={
            "name": "neta-production",
            "server": kubernetes.cluster.eks_cluster.arn,
            "project": "default",
        },
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[capability]),
    )

    # Identity Center requires immutable group IDs in AppProject roles. Pulumi owns this
    # account-specific authorization boundary so the ID never enters the public GitOps tree.
    production_project = k8s.apiextensions.CustomResource(
        "neta-production-project",
        api_version="argoproj.io/v1alpha1",
        kind="AppProject",
        metadata={"name": "neta-production", "namespace": "argocd"},
        spec={
            "description": (
                "Production control plane, ingestion workloads, and data pipeline services."
            ),
            "sourceNamespaces": ["argocd"],
            "sourceRepos": [
                "https://dagster-io.github.io/helm",
                settings.repository_url,
            ],
            "destinations": [{"namespace": "neta-production", "name": "neta-production"}],
            "clusterResourceBlacklist": [{"group": "*", "kind": "*"}],
            "namespaceResourceWhitelist": [{"group": "*", "kind": "*"}],
            "orphanedResources": {"warn": True},
            "roles": [
                {
                    "name": "platform-operator",
                    "description": "Sync and inspect Neta production applications.",
                    "policies": [
                        (
                            "p, proj:neta-production:platform-operator, applications, get, "
                            "neta-production/*, allow"
                        ),
                        (
                            "p, proj:neta-production:platform-operator, applications, sync, "
                            "neta-production/*, allow"
                        ),
                        (
                            "p, proj:neta-production:platform-operator, logs, get, "
                            "neta-production/*, allow"
                        ),
                        ("p, proj:neta-production:platform-operator, clusters, get, *, allow"),
                    ],
                    "groups": [settings.argocd_platform_admin_group_id],
                }
            ],
        },
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=[capability, cluster_registration],
        ),
    )

    root_application = k8s.apiextensions.CustomResource(
        "production-root-application",
        api_version="argoproj.io/v1alpha1",
        kind="Application",
        metadata={"name": "neta-production-root", "namespace": "argocd"},
        spec={
            "project": "default",
            "source": {
                "repoURL": settings.repository_url,
                "targetRevision": "main",
                "path": "deploy/argocd/production",
            },
            "destination": {
                "name": "neta-production",
                "namespace": "argocd",
            },
            "revisionHistoryLimit": 10,
            "syncPolicy": {
                "syncOptions": [
                    "ServerSideApply=true",
                    "ApplyOutOfSyncOnly=true",
                    "PruneLast=true",
                ]
            },
        },
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=[
                capability,
                cluster_view_access,
                production_namespace_access,
                cluster_registration,
                production_project,
                addons.external_secrets,
                addons.node_pool,
                addons.platform_config,
                addons.database_service,
            ],
        ),
    )
    return GitOpsBootstrap(
        provider=provider,
        capability_role=capability_role,
        capability=capability,
        cluster_view_access=cluster_view_access,
        production_namespace_access=production_namespace_access,
        cluster_registration=cluster_registration,
        production_project=production_project,
        root_application=root_application,
    )
