from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator

import pulumi.runtime as runtime
import pytest
from pulumi.runtime import MockCallArgs, MockResourceArgs, Mocks

from neta_infra.settings import InfraSettings


class InfraMocks(Mocks):
    def call(self, args: MockCallArgs) -> tuple[dict[str, object], None]:
        return {}, None

    def new_resource(self, args: MockResourceArgs) -> tuple[str, dict[str, object]]:
        return f"{args.name}-id", args.inputs


@pytest.fixture(scope="session", autouse=True)
def pulumi_runtime() -> Iterator[None]:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    runtime.set_mocks(InfraMocks(), project="neta-resume-infra", stack="prod", preview=True)
    loop.run_until_complete(asyncio.sleep(0))
    yield
    loop.run_until_complete(asyncio.sleep(0))
    loop.close()


@pytest.fixture(autouse=True)
def configure_pulumi() -> None:
    runtime.set_all_config({})


def _set_access_cidrs(*cidrs: str) -> None:
    runtime.set_all_config(
        {
            "neta-resume-infra:clusterPublicAccessCidrs": json.dumps(list(cidrs)),
            "neta-resume-infra:argocdIdentityCenterInstanceArn": (
                "arn:aws:sso:::instance/ssoins-1234567890abcdef"
            ),
            "neta-resume-infra:argocdIdentityCenterRegion": "ap-south-1",
            "neta-resume-infra:argocdPlatformAdminGroupId": (
                "1234567890-12345678-1234-1234-1234-123456789abc"
            ),
            "neta-resume-infra:karpenterAmiAlias": "al2023@v20260715",
        }
    )


def test_settings_require_an_explicit_eks_access_boundary() -> None:
    with pytest.raises(Exception, match="clusterPublicAccessCidrs"):
        InfraSettings.load()


def test_settings_require_identity_center_for_managed_argocd() -> None:
    runtime.set_all_config(
        {
            "neta-resume-infra:clusterPublicAccessCidrs": json.dumps(["203.0.113.7/32"]),
        }
    )

    with pytest.raises(Exception, match="argocdIdentityCenterInstanceArn"):
        InfraSettings.load()


def test_settings_require_platform_admin_group_for_managed_argocd() -> None:
    runtime.set_all_config(
        {
            "neta-resume-infra:clusterPublicAccessCidrs": json.dumps(["203.0.113.7/32"]),
            "neta-resume-infra:argocdIdentityCenterInstanceArn": (
                "arn:aws:sso:::instance/ssoins-1234567890abcdef"
            ),
            "neta-resume-infra:argocdIdentityCenterRegion": "ap-south-1",
        }
    )

    with pytest.raises(Exception, match="argocdPlatformAdminGroupId"):
        InfraSettings.load()


def test_settings_reject_invalid_identity_center_group_id() -> None:
    _set_access_cidrs("203.0.113.7/32")
    runtime.set_config("neta-resume-infra:argocdPlatformAdminGroupId", "platform-admins")

    with pytest.raises(ValueError, match="IAM Identity Center group ID"):
        InfraSettings.load()


@pytest.mark.parametrize("cidr", ["0.0.0.0/0", "::/0"])
def test_settings_reject_public_eks_api_access(cidr: str) -> None:
    _set_access_cidrs(cidr)

    with pytest.raises(ValueError, match="cannot expose"):
        InfraSettings.load()


def test_settings_normalize_trusted_eks_access_cidrs() -> None:
    _set_access_cidrs("203.0.113.7/32", "2001:db8::9/128")

    settings = InfraSettings.load()

    assert settings.cluster_public_access_cidrs == (
        "203.0.113.7/32",
        "2001:db8::9/128",
    )
    assert settings.cluster_name == "neta-prod"
    assert settings.kubernetes_version == "1.36"
    assert settings.argocd_identity_center_instance_arn.endswith("ssoins-1234567890abcdef")
    assert settings.argocd_identity_center_region == "ap-south-1"
    assert settings.argocd_platform_admin_group_id.startswith("1234567890-")
    assert settings.external_operator_chart_version == "2.8.0"
    assert settings.karpenter_chart_version == "1.14.0"
    assert settings.karpenter_ami_alias == "al2023@v20260715"
    assert settings.protect_data is True
    assert settings.system_node_count == 2
