"""Non-secret production stack configuration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from ipaddress import ip_network

import pulumi
import pulumi_aws as aws


@dataclass(frozen=True, slots=True)
class InfraSettings:
    region: str
    cluster_name: str
    kubernetes_version: str
    vpc_cidr: str
    availability_zone_count: int
    system_node_instance_types: tuple[str, ...]
    system_node_count: int
    cluster_public_access_cidrs: tuple[str, ...]
    database_instance_class: str
    database_allocated_storage_gb: int
    database_max_storage_gb: int
    database_backup_retention_days: int
    argocd_identity_center_instance_arn: str
    argocd_identity_center_region: str
    external_operator_chart_version: str
    karpenter_chart_version: str
    karpenter_ami_alias: str
    repository_url: str
    protect_data: bool

    @classmethod
    def load(cls) -> InfraSettings:
        config = pulumi.Config()
        region = aws.config.region or "ap-south-1"
        instance_types = config.get_object("systemNodeInstanceTypes") or ["t4g.medium"]
        if not isinstance(instance_types, list) or not all(
            isinstance(value, str) and value for value in instance_types
        ):
            raise ValueError("systemNodeInstanceTypes must be a non-empty list of instance types")
        access_cidrs = config.require_object("clusterPublicAccessCidrs")
        if not isinstance(access_cidrs, list) or not access_cidrs:
            raise ValueError("clusterPublicAccessCidrs must be a non-empty list of trusted CIDRs")
        validated_access_cidrs: list[str] = []
        for value in access_cidrs:
            if not isinstance(value, str):
                raise ValueError("clusterPublicAccessCidrs values must be CIDR strings")
            network = ip_network(value, strict=False)
            if network.prefixlen == 0:
                message = "clusterPublicAccessCidrs cannot expose the EKS API to the internet"
                raise ValueError(message)
            validated_access_cidrs.append(str(network))
        return cls(
            region=region,
            cluster_name=config.get("clusterName") or "neta-prod",
            kubernetes_version=config.get("kubernetesVersion") or "1.36",
            vpc_cidr=config.get("vpcCidr") or "10.42.0.0/16",
            availability_zone_count=config.get_int("availabilityZoneCount") or 2,
            system_node_instance_types=tuple(instance_types),
            system_node_count=config.get_int("systemNodeCount") or 2,
            cluster_public_access_cidrs=tuple(validated_access_cidrs),
            database_instance_class=config.get("databaseInstanceClass") or "db.t4g.medium",
            database_allocated_storage_gb=config.get_int("databaseAllocatedStorageGb") or 100,
            database_max_storage_gb=config.get_int("databaseMaxStorageGb") or 1000,
            database_backup_retention_days=config.get_int("databaseBackupRetentionDays") or 14,
            argocd_identity_center_instance_arn=_identity_center_instance_arn(config),
            argocd_identity_center_region=_identity_center_region(config),
            external_operator_chart_version=(config.get("externalOperatorChartVersion") or "2.8.0"),
            karpenter_chart_version=config.get("karpenterChartVersion") or "1.14.0",
            karpenter_ami_alias=_karpenter_ami_alias(config),
            repository_url=(
                config.get("repositoryUrl")
                or "https://github.com/citizen-apps-india/neta-resume.git"
            ),
            protect_data=config.get_bool("protectData") is not False,
        )

    @property
    def common_tags(self) -> dict[str, str]:
        return {
            "Project": "citizen-apps-india",
            "Application": "neta-resume",
            "Environment": "production",
            "ManagedBy": "pulumi",
        }


def _identity_center_instance_arn(config: pulumi.Config) -> str:
    instance_arn = config.require("argocdIdentityCenterInstanceArn")
    if not re.fullmatch(r"arn:[^:]+:sso:::instance/ssoins-[A-Za-z0-9-]+", instance_arn):
        raise ValueError("argocdIdentityCenterInstanceArn must be an IAM Identity Center ARN")
    return instance_arn


def _identity_center_region(config: pulumi.Config) -> str:
    region = config.require("argocdIdentityCenterRegion")
    if not re.fullmatch(r"[a-z]{2}(?:-gov)?-[a-z]+-\d", region):
        raise ValueError("argocdIdentityCenterRegion must be an AWS region")
    return region


def _karpenter_ami_alias(config: pulumi.Config) -> str:
    alias = config.require("karpenterAmiAlias")
    if not re.fullmatch(r"al2023@v\d{8}", alias):
        raise ValueError("karpenterAmiAlias must pin an AL2023 release such as al2023@v20260101")
    return alias
