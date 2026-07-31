"""EKS control plane and the small, fixed system node pool."""

from __future__ import annotations

from dataclasses import dataclass

import pulumi
import pulumi_aws as aws
import pulumi_eks as eks

from neta_infra.identity import NodeRoles
from neta_infra.network import Network
from neta_infra.settings import InfraSettings


@dataclass(frozen=True, slots=True)
class KubernetesCluster:
    cluster: eks.Cluster
    system_nodes: eks.ManagedNodeGroup
    karpenter_node_access: aws.eks.AccessEntry
    core_addons: tuple[aws.eks.Addon, ...]
    pod_identity_agent: aws.eks.Addon
    encryption_key: aws.kms.Key


def create_cluster(
    settings: InfraSettings,
    network: Network,
    node_roles: NodeRoles,
) -> KubernetesCluster:
    encryption_key = aws.kms.Key(
        "platform-data-key",
        description="Neta Resume production EKS, RDS, S3, and Secrets Manager key",
        enable_key_rotation=True,
        deletion_window_in_days=30,
        tags=settings.common_tags,
        opts=pulumi.ResourceOptions(protect=settings.protect_data),
    )
    aws.kms.Alias(
        "platform-data-key-alias",
        name="alias/neta-resume-production",
        target_key_id=encryption_key.key_id,
    )

    cluster = eks.Cluster(
        "production-cluster",
        name=settings.cluster_name,
        version=settings.kubernetes_version,
        vpc_id=network.vpc.vpc_id,
        private_subnet_ids=network.vpc.private_subnet_ids,
        public_subnet_ids=network.vpc.public_subnet_ids,
        node_subnet_ids=network.vpc.private_subnet_ids,
        skip_default_node_group=True,
        bootstrap_self_managed_addons=False,
        # "Use default" tells the component not to create its opinionated CNI
        # resource. EKS bootstrap is disabled above; our managed add-on below
        # is therefore the only VPC CNI owner.
        use_default_vpc_cni=True,
        kube_proxy_addon_options=eks.KubeProxyAddonOptionsArgs(enabled=False),
        coredns_addon_options=eks.CoreDnsAddonOptionsArgs(enabled=False),
        create_instance_role=False,
        create_oidc_provider=False,
        authentication_mode=eks.AuthenticationMode.API,
        endpoint_private_access=True,
        endpoint_public_access=True,
        public_access_cidrs=list(settings.cluster_public_access_cidrs),
        enabled_cluster_log_types=["api", "audit", "authenticator", "controllerManager"],
        encryption_config_key_arn=encryption_key.arn,
        deletion_protection=settings.protect_data,
        node_associate_public_ip_address=False,
        node_root_volume_encrypted=True,
        cluster_security_group_tags={
            **settings.common_tags,
            "karpenter.sh/discovery": settings.cluster_name,
        },
        node_security_group_tags={
            **settings.common_tags,
            "karpenter.sh/discovery": settings.cluster_name,
        },
        tags=settings.common_tags,
    )

    # EKS creates the access entry for its managed node group. Karpenter nodes
    # are self-managed, so their role must be registered explicitly.
    karpenter_node_access = aws.eks.AccessEntry(
        "karpenter-node-access",
        cluster_name=cluster.eks_cluster.name,
        principal_arn=node_roles.karpenter.arn,
        type="EC2_LINUX",
        tags=settings.common_tags,
        opts=pulumi.ResourceOptions(depends_on=[cluster.eks_cluster]),
    )

    def managed_addon(addon_name: str, *, depends_on: list[pulumi.Resource]) -> aws.eks.Addon:
        latest_version = aws.eks.get_addon_version_output(
            addon_name=addon_name,
            kubernetes_version=settings.kubernetes_version,
            most_recent=True,
            region=settings.region,
        ).version
        return aws.eks.Addon(
            f"managed-addon-{addon_name}",
            cluster_name=cluster.eks_cluster.name,
            addon_name=addon_name,
            addon_version=latest_version,
            resolve_conflicts_on_create="OVERWRITE",
            resolve_conflicts_on_update="OVERWRITE",
            tags=settings.common_tags,
            opts=pulumi.ResourceOptions(depends_on=depends_on),
        )

    vpc_cni = managed_addon("vpc-cni", depends_on=[cluster.eks_cluster])
    kube_proxy = managed_addon("kube-proxy", depends_on=[cluster.eks_cluster])

    system_nodes = eks.ManagedNodeGroup(
        "system-nodes",
        cluster=cluster,
        node_group_name=f"{settings.cluster_name}-system",
        node_role=node_roles.system,
        subnet_ids=network.vpc.private_subnet_ids,
        instance_types=list(settings.system_node_instance_types),
        capacity_type="ON_DEMAND",
        ami_type="AL2023_ARM_64_STANDARD",
        operating_system=eks.OperatingSystem.AL2023,
        disk_size=40,
        enable_imd_sv2=True,
        scaling_config=aws.eks.NodeGroupScalingConfigArgs(
            min_size=settings.system_node_count,
            desired_size=settings.system_node_count,
            max_size=settings.system_node_count,
        ),
        labels={
            "neta.dev/workload-tier": "system",
            # Kubelets cannot self-assign arbitrary labels in the reserved
            # kubernetes.io namespace. Keep node identity under our domain.
            "neta.dev/part-of": "neta-resume",
        },
        tags=settings.common_tags,
        opts=pulumi.ResourceOptions(depends_on=[vpc_cni, kube_proxy]),
    )
    core_dns = managed_addon("coredns", depends_on=[system_nodes])
    pod_identity_agent = managed_addon(
        "eks-pod-identity-agent",
        depends_on=[system_nodes],
    )
    return KubernetesCluster(
        cluster=cluster,
        system_nodes=system_nodes,
        karpenter_node_access=karpenter_node_access,
        core_addons=(vpc_cni, kube_proxy, core_dns, pod_identity_agent),
        pod_identity_agent=pod_identity_agent,
        encryption_key=encryption_key,
    )
