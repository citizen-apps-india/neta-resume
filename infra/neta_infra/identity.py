"""EC2 node and Kubernetes workload identities."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

NODE_MANAGED_POLICIES = (
    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly",
    "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
)


@dataclass(frozen=True, slots=True)
class NodeRoles:
    system: aws.iam.Role
    karpenter: aws.iam.Role


def _ec2_assume_role_policy() -> str:
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
    )


def _create_node_role(resource_name: str, role_name: str, tags: dict[str, str]) -> aws.iam.Role:
    role = aws.iam.Role(
        resource_name,
        name=role_name,
        assume_role_policy=_ec2_assume_role_policy(),
        tags=tags,
    )
    for index, policy_arn in enumerate(NODE_MANAGED_POLICIES):
        aws.iam.RolePolicyAttachment(
            f"{resource_name}-policy-{index}",
            role=role.name,
            policy_arn=policy_arn,
        )
    return role


def create_node_roles(cluster_name: str, tags: dict[str, str]) -> NodeRoles:
    return NodeRoles(
        system=_create_node_role("system-node-role", f"{cluster_name}-system-node", tags),
        karpenter=_create_node_role(
            "karpenter-node-role",
            f"{cluster_name}-karpenter-node",
            tags,
        ),
    )


def irsa_assume_role_policy(
    oidc_provider_arn: pulumi.Input[str],
    oidc_provider_url: pulumi.Input[str],
    *,
    namespace: str,
    service_account: str,
) -> pulumi.Output[str]:
    return pulumi.Output.all(oidc_provider_arn, oidc_provider_url).apply(
        lambda values: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Federated": values[0]},
                        "Action": "sts:AssumeRoleWithWebIdentity",
                        "Condition": {
                            "StringEquals": {
                                f"{values[1]}:aud": "sts.amazonaws.com",
                                f"{values[1]}:sub": (
                                    f"system:serviceaccount:{namespace}:{service_account}"
                                ),
                            }
                        },
                    }
                ],
            }
        )
    )


def create_irsa_role(
    resource_name: str,
    role_name: str,
    oidc_provider_arn: pulumi.Input[str],
    oidc_provider_url: pulumi.Input[str],
    *,
    namespace: str,
    service_account: str,
    policy: pulumi.Input[str],
    tags: dict[str, str],
) -> aws.iam.Role:
    role = aws.iam.Role(
        resource_name,
        name=role_name,
        assume_role_policy=irsa_assume_role_policy(
            oidc_provider_arn,
            oidc_provider_url,
            namespace=namespace,
            service_account=service_account,
        ),
        tags=tags,
    )
    aws.iam.RolePolicy(
        f"{resource_name}-policy",
        role=role.name,
        policy=policy,
    )
    return role


def pod_identity_assume_role_policy(
    *,
    cluster_name: str,
    namespace: str,
    service_account: str,
) -> str:
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowEksAuthToAssumeRoleForPodIdentity",
                    "Effect": "Allow",
                    "Principal": {"Service": "pods.eks.amazonaws.com"},
                    "Action": ["sts:AssumeRole", "sts:TagSession"],
                    "Condition": {
                        "StringEquals": {
                            "aws:RequestTag/eks-cluster-name": cluster_name,
                            "aws:RequestTag/kubernetes-namespace": namespace,
                            "aws:RequestTag/kubernetes-service-account": service_account,
                        }
                    },
                }
            ],
        }
    )


def create_pod_identity_role(
    resource_name: str,
    role_name: str,
    *,
    cluster_name: str,
    namespace: str,
    service_account: str,
    policy: pulumi.Input[str],
    tags: dict[str, str],
) -> aws.iam.Role:
    role = aws.iam.Role(
        resource_name,
        name=role_name,
        assume_role_policy=pod_identity_assume_role_policy(
            cluster_name=cluster_name,
            namespace=namespace,
            service_account=service_account,
        ),
        tags=tags,
    )
    aws.iam.RolePolicy(
        f"{resource_name}-policy",
        role=role.name,
        policy=policy,
    )
    return role
