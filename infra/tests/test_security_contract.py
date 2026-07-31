from __future__ import annotations

from pathlib import Path

import yaml

INFRA_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = INFRA_ROOT.parent


def _read(relative_path: str) -> str:
    return (REPOSITORY_ROOT / relative_path).read_text()


def test_bootstrap_role_is_preview_only() -> None:
    bootstrap = _read("infra/bootstrap/__main__.py")

    assert "neta-prod-pulumi-preview" in bootstrap
    assert "environment:{github_environment}" in bootstrap
    assert "ViewOnlyAccess" in bootstrap
    assert "github-deploy" not in bootstrap
    assert "AdministratorAccess" not in bootstrap
    assert "iam:*" not in bootstrap


def test_bootstrap_creates_a_tag_based_project_boundary() -> None:
    bootstrap = _read("infra/bootstrap/__main__.py")
    settings = _read("infra/neta_infra/settings.py")

    assert "aws.resourcegroups.Group(" in bootstrap
    assert 'name="citizen-apps-india"' in bootstrap
    assert 'type="TAG_FILTERS_1_0"' in bootstrap
    assert '"ResourceTypeFilters": ["AWS::AllSupported"]' in bootstrap
    assert '{"Key": "Project", "Values": ["citizen-apps-india"]}' in bootstrap
    assert '"Project": "citizen-apps-india"' in bootstrap
    assert '"Project": "citizen-apps-india"' in settings
    assert '"Application": "neta-resume"' in bootstrap
    assert '"Application": "neta-resume"' in settings


def test_state_is_protected_versioned_and_kms_encrypted() -> None:
    bootstrap = _read("infra/bootstrap/__main__.py")

    assert "protect=True" in bootstrap
    assert 'status="Enabled"' in bootstrap
    assert 'sse_algorithm="aws:kms"' in bootstrap
    assert "block_public_policy=True" in bootstrap
    assert "force_destroy=False" in bootstrap
    assert "BucketV2" not in bootstrap
    assert "BucketVersioningV2" not in bootstrap
    assert "BucketServerSideEncryptionConfigurationV2" not in bootstrap


def test_production_data_stores_have_deletion_guards() -> None:
    data = _read("infra/neta_infra/data.py")

    assert "manage_master_user_password=True" in data
    assert "multi_az=True" in data
    assert "publicly_accessible=False" in data
    assert "skip_final_snapshot=False" in data
    assert "deletion_protection=settings.protect_data" in data
    assert "max_allocated_storage=settings.database_max_storage_gb" in data
    assert "force_destroy=False" in data
    assert 'engine_version="18.4"' in data
    assert 'family="postgres18"' in data
    assert 'value="receipt,authentication,authorization"' in data
    assert 'name="log_connections", value="1"' not in data
    assert "BucketV2" not in data
    assert "BucketVersioningV2" not in data
    assert "BucketServerSideEncryptionConfigurationV2" not in data


def test_prod_stack_has_no_committed_secret_values() -> None:
    stack = yaml.safe_load(_read("infra/Pulumi.prod.yaml"))
    config = stack["config"]

    assert config
    assert not any(isinstance(value, dict) and "secure" in value for value in config.values())
    forbidden_names = ("password", "secret", "token", "accesskey")
    assert not any(any(name in key.lower() for name in forbidden_names) for key in config)


def test_stack_requires_operator_cidrs_instead_of_committing_a_public_default() -> None:
    settings = _read("infra/neta_infra/settings.py")
    cluster = _read("infra/neta_infra/cluster.py")
    stack = _read("infra/Pulumi.prod.yaml")

    assert 'require_object("clusterPublicAccessCidrs")' in settings
    assert "settings.cluster_public_access_cidrs" in cluster
    assert "0.0.0.0/0" not in cluster
    assert "clusterPublicAccessCidrs:" not in stack


def test_prod_network_uses_two_nat_gateways_and_an_s3_endpoint() -> None:
    network = _read("infra/neta_infra/network.py")

    assert "NatGatewayStrategy.ONE_PER_AZ" in network
    assert "VpcEndpointStrategy.AUTO" in network
    assert 'service_name="s3"' in network
    assert "SubnetType.ISOLATED" in network


def test_eks_uses_latest_compatible_managed_addons() -> None:
    cluster = _read("infra/neta_infra/cluster.py")

    assert "bootstrap_self_managed_addons=False" in cluster
    assert "use_default_vpc_cni=True" in cluster
    assert "KubeProxyAddonOptionsArgs(enabled=False)" in cluster
    assert "CoreDnsAddonOptionsArgs(enabled=False)" in cluster
    assert "get_addon_version_output" in cluster
    assert "most_recent=True" in cluster
    assert 'managed_addon("vpc-cni"' in cluster
    assert 'managed_addon("kube-proxy"' in cluster
    assert 'managed_addon("coredns"' in cluster
    assert '"eks-pod-identity-agent"' in cluster


def test_eks_uses_api_access_entries_without_legacy_aws_auth_or_irsa() -> None:
    cluster = _read("infra/neta_infra/cluster.py")
    addons = _read("infra/neta_infra/addons.py")

    assert "authentication_mode=eks.AuthenticationMode.API" in cluster
    assert "API_AND_CONFIG_MAP" not in cluster
    assert "instance_roles=" not in cluster
    assert "create_oidc_provider=False" in cluster
    assert "aws.eks.AccessEntry(" in cluster
    assert 'type="EC2_LINUX"' in cluster
    assert "principal_arn=node_roles.karpenter.arn" in cluster
    assert "depends_on=[karpenter, kubernetes.karpenter_node_access]" in addons


def test_argocd_uses_the_eks_managed_capability_with_identity_center() -> None:
    gitops = _read("infra/neta_infra/gitops.py")
    stack = _read("infra/Pulumi.prod.yaml")

    assert "aws.eks.Capability(" in gitops
    assert 'type="ARGOCD"' in gitops
    assert '"capabilities.eks.amazonaws.com"' in gitops
    assert '"sts:TagSession"' in gitops
    assert 'delete_propagation_policy="RETAIN"' in gitops
    assert 'chart="argo-cd"' not in gitops
    assert "argocdChartVersion" not in stack
    assert "AmazonEKSClusterAdminPolicy" not in gitops
    assert "rbac_role_mappings=[" in gitops
    assert 'role="VIEWER"' in gitops
    assert 'role="ADMIN"' not in gitops
    assert 'role="EDITOR"' not in gitops
    assert 'type="SSO_GROUP"' in gitops
    assert "id=settings.argocd_platform_admin_group_id" in gitops
    assert 'require("argocdPlatformAdminGroupId")' in _read("infra/neta_infra/settings.py")
    assert "argocdPlatformAdminGroupId:" not in stack
    assert "AmazonEKSViewPolicy" in gitops
    assert "AmazonEKSAdminPolicy" in gitops
    assert 'namespaces=["neta-production"]' in gitops


def test_argocd_project_grants_only_bounded_platform_operations() -> None:
    gitops = _read("infra/neta_infra/gitops.py")

    assert 'kind="AppProject"' in gitops
    assert '"sourceNamespaces": ["argocd"]' in gitops
    assert '"clusterResourceBlacklist": [{"group": "*", "kind": "*"}]' in gitops
    assert '"name": "platform-operator"' in gitops
    assert "applications, get" in gitops
    assert "applications, sync" in gitops
    assert "logs, get" in gitops
    assert "clusters, get" in gitops
    assert "applications, delete" not in gitops
    assert "applications, update" not in gitops
    assert "applications, action" not in gitops
    assert "exec, " not in gitops


def test_managed_argocd_registers_the_local_cluster_by_arn() -> None:
    gitops = _read("infra/neta_infra/gitops.py")

    assert '"argocd.argoproj.io/secret-type": "cluster"' in gitops
    assert '"server": kubernetes.cluster.eks_cluster.arn' in gitops
    assert '"name": "neta-production"' in gitops
    assert "https://kubernetes.default.svc" not in gitops


def test_cluster_operators_are_pulumi_owned_and_version_pinned() -> None:
    addons = _read("infra/neta_infra/addons.py")
    settings = _read("infra/neta_infra/settings.py")

    assert 'chart="external-secrets"' in addons
    assert 'chart="karpenter-crd"' in addons
    assert 'chart="karpenter"' in addons
    assert "skip_crds=True" in addons
    assert 'kind="EC2NodeClass"' in addons
    assert 'kind="NodePool"' in addons
    assert '"consolidationPolicy": "WhenEmptyOrUnderutilized"' in addons
    assert '"neta.dev/workload-tier": "application"' in addons
    assert 'require("karpenterAmiAlias")' in settings
    assert 'r"al2023@v\\d{8}"' in settings
    assert "al2023@latest" not in addons


def test_workloads_use_scoped_eks_pod_identities() -> None:
    identity = _read("infra/neta_infra/identity.py")
    workloads = _read("infra/neta_infra/workload_identity.py")
    karpenter = _read("infra/neta_infra/karpenter.py")

    assert '"pods.eks.amazonaws.com"' in identity
    assert '"aws:RequestTag/eks-cluster-name"' in identity
    assert '"aws:RequestTag/kubernetes-namespace"' in identity
    assert '"aws:RequestTag/kubernetes-service-account"' in identity
    assert workloads.count("aws.eks.PodIdentityAssociation(") == 2
    assert 'namespace="neta-production"' in workloads
    assert 'namespace="external-secrets"' in workloads
    assert "aws.eks.PodIdentityAssociation(" in karpenter
    assert "AssumeRoleWithWebIdentity" not in workloads
    assert "eks.amazonaws.com/role-arn" not in workloads


def test_production_namespace_is_pulumi_protected_and_account_values_are_not_in_git() -> None:
    addons = _read("infra/neta_infra/addons.py")

    assert '"name": "neta-production"' in addons
    assert "protect=settings.protect_data" in addons
    assert '"NETA_RAW_S3_BUCKET": data.evidence_bucket.bucket' in addons
    assert '"externalName": data.database.address' in addons


def test_karpenter_policy_matches_current_scoping_contract() -> None:
    karpenter = _read("infra/neta_infra/karpenter.py")

    assert "Karpenter 1.14.x" in karpenter
    assert "AllowUnscopedInstanceProfileListAction" in karpenter
    assert "arc-zonal-shift:ResourceIdentifier" in karpenter
    assert 'instance-profile/*"' in karpenter
