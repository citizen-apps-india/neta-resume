"""Composition root for the production AWS platform."""

from __future__ import annotations

from dataclasses import dataclass

import pulumi_aws as aws

from neta_infra.addons import PlatformAddons, create_platform_addons
from neta_infra.cluster import KubernetesCluster, create_cluster
from neta_infra.data import DataLayer, create_data_layer
from neta_infra.gitops import GitOpsBootstrap, create_gitops_bootstrap
from neta_infra.identity import NodeRoles, create_node_roles
from neta_infra.karpenter import KarpenterInfrastructure, create_karpenter_infrastructure
from neta_infra.network import Network, create_network
from neta_infra.settings import InfraSettings
from neta_infra.workload_identity import WorkloadRoles, create_workload_roles


@dataclass(frozen=True, slots=True)
class Platform:
    settings: InfraSettings
    network: Network
    node_roles: NodeRoles
    kubernetes: KubernetesCluster
    data: DataLayer
    workloads: WorkloadRoles
    karpenter: KarpenterInfrastructure
    addons: PlatformAddons
    gitops: GitOpsBootstrap


def build_platform() -> Platform:
    settings = InfraSettings.load()
    caller = aws.get_caller_identity()
    partition = aws.get_partition()

    network = create_network(settings)
    node_roles = create_node_roles(settings.cluster_name, settings.common_tags)
    kubernetes = create_cluster(settings, network, node_roles)
    data = create_data_layer(settings, caller.account_id, network, kubernetes)
    workloads = create_workload_roles(settings, kubernetes, data)
    karpenter = create_karpenter_infrastructure(
        settings,
        caller.account_id,
        partition.partition,
        kubernetes,
        node_roles,
    )
    addons = create_platform_addons(
        settings,
        kubernetes,
        data,
        workloads,
        karpenter,
        node_roles,
    )
    gitops = create_gitops_bootstrap(settings, kubernetes, addons)
    return Platform(
        settings=settings,
        network=network,
        node_roles=node_roles,
        kubernetes=kubernetes,
        data=data,
        workloads=workloads,
        karpenter=karpenter,
        addons=addons,
        gitops=gitops,
    )
