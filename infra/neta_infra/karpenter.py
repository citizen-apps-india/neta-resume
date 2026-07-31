"""AWS resources and controller identity for Karpenter 1.14.x."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pulumi
import pulumi_aws as aws

from neta_infra.cluster import KubernetesCluster
from neta_infra.identity import NodeRoles, create_pod_identity_role
from neta_infra.settings import InfraSettings


@dataclass(frozen=True, slots=True)
class KarpenterInfrastructure:
    controller_role: aws.iam.Role
    controller_identity: aws.eks.PodIdentityAssociation
    interruption_queue: aws.sqs.Queue


def _policy_document(statements: list[dict[str, Any]]) -> str:
    return json.dumps({"Version": "2012-10-17", "Statement": statements})


def _attach_policy(
    resource_name: str,
    role: aws.iam.Role,
    policy_name: str,
    policy: pulumi.Input[str],
    tags: dict[str, str],
) -> None:
    managed_policy = aws.iam.Policy(
        resource_name,
        name=policy_name,
        policy=policy,
        tags=tags,
    )
    aws.iam.RolePolicyAttachment(
        f"{resource_name}-attachment",
        role=role.name,
        policy_arn=managed_policy.arn,
    )


def _create_interruption_events(
    settings: InfraSettings,
    queue: aws.sqs.Queue,
) -> None:
    queue_policy = queue.arn.apply(
        lambda queue_arn: _policy_document(
            [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": ["events.amazonaws.com", "sqs.amazonaws.com"]},
                    "Action": "sqs:SendMessage",
                    "Resource": queue_arn,
                },
                {
                    "Sid": "DenyHTTP",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "sqs:*",
                    "Resource": queue_arn,
                    "Condition": {"Bool": {"aws:SecureTransport": "false"}},
                },
            ]
        )
    )
    aws.sqs.QueuePolicy(
        "karpenter-interruption-queue-policy",
        queue_url=queue.url,
        policy=queue_policy,
    )

    event_patterns = {
        "scheduled-change": {
            "source": ["aws.health"],
            "detail-type": ["AWS Health Event"],
        },
        "spot-interruption": {
            "source": ["aws.ec2"],
            "detail-type": ["EC2 Spot Instance Interruption Warning"],
        },
        "rebalance": {
            "source": ["aws.ec2"],
            "detail-type": ["EC2 Instance Rebalance Recommendation"],
        },
        "instance-state-change": {
            "source": ["aws.ec2"],
            "detail-type": ["EC2 Instance State-change Notification"],
        },
        "capacity-reservation-interruption": {
            "source": ["aws.ec2"],
            "detail-type": ["EC2 Capacity Reservation Instance Interruption Warning"],
        },
    }
    for event_name, event_pattern in event_patterns.items():
        rule = aws.cloudwatch.EventRule(
            f"karpenter-{event_name}",
            name=f"{settings.cluster_name}-karpenter-{event_name}",
            event_pattern=json.dumps(event_pattern),
            tags=settings.common_tags,
        )
        aws.cloudwatch.EventTarget(
            f"karpenter-{event_name}-target",
            rule=rule.name,
            arn=queue.arn,
            target_id="KarpenterInterruptionQueueTarget",
        )


def create_karpenter_infrastructure(
    settings: InfraSettings,
    account_id: str,
    partition: str,
    kubernetes: KubernetesCluster,
    node_roles: NodeRoles,
) -> KarpenterInfrastructure:
    queue = aws.sqs.Queue(
        "karpenter-interruption-queue",
        name=settings.cluster_name,
        message_retention_seconds=300,
        sqs_managed_sse_enabled=True,
        tags=settings.common_tags,
    )
    _create_interruption_events(settings, queue)

    controller_role = create_pod_identity_role(
        "karpenter-controller-role",
        f"{settings.cluster_name}-karpenter-controller",
        cluster_name=settings.cluster_name,
        namespace="kube-system",
        service_account="karpenter",
        policy=_policy_document(
            [
                {
                    "Effect": "Allow",
                    "Action": "eks:DescribeCluster",
                    "Resource": (
                        f"arn:{partition}:eks:{settings.region}:{account_id}:cluster/"
                        f"{settings.cluster_name}"
                    ),
                }
            ]
        ),
        tags=settings.common_tags,
    )

    region = settings.region
    cluster_name = settings.cluster_name
    ec2_account_prefix = f"arn:{partition}:ec2:{region}:{account_id}"
    ec2_public_prefix = f"arn:{partition}:ec2:{region}:"
    cluster_tag = f"kubernetes.io/cluster/{cluster_name}"

    node_lifecycle = _policy_document(
        [
            {
                "Sid": "AllowScopedEC2InstanceAccessActions",
                "Effect": "Allow",
                "Resource": [
                    f"{ec2_public_prefix}:image/*",
                    f"{ec2_public_prefix}:snapshot/*",
                    f"{ec2_account_prefix}:security-group/*",
                    f"{ec2_account_prefix}:subnet/*",
                    f"{ec2_account_prefix}:capacity-reservation/*",
                    f"{ec2_account_prefix}:placement-group/*",
                ],
                "Action": ["ec2:RunInstances", "ec2:CreateFleet"],
            },
            {
                "Sid": "AllowScopedEC2LaunchTemplateAccessActions",
                "Effect": "Allow",
                "Resource": f"{ec2_account_prefix}:launch-template/*",
                "Action": ["ec2:RunInstances", "ec2:CreateFleet"],
                "Condition": {
                    "StringEquals": {f"aws:ResourceTag/{cluster_tag}": "owned"},
                    "StringLike": {"aws:ResourceTag/karpenter.sh/nodepool": "*"},
                },
            },
            {
                "Sid": "AllowScopedEC2InstanceActionsWithTags",
                "Effect": "Allow",
                "Resource": [
                    f"{ec2_account_prefix}:fleet/*",
                    f"{ec2_account_prefix}:instance/*",
                    f"{ec2_account_prefix}:volume/*",
                    f"{ec2_account_prefix}:network-interface/*",
                    f"{ec2_account_prefix}:launch-template/*",
                    f"{ec2_account_prefix}:spot-instances-request/*",
                ],
                "Action": [
                    "ec2:RunInstances",
                    "ec2:CreateFleet",
                    "ec2:CreateLaunchTemplate",
                ],
                "Condition": {
                    "StringEquals": {
                        f"aws:RequestTag/{cluster_tag}": "owned",
                        "aws:RequestTag/eks:eks-cluster-name": cluster_name,
                    },
                    "StringLike": {"aws:RequestTag/karpenter.sh/nodepool": "*"},
                },
            },
            {
                "Sid": "AllowScopedResourceCreationTagging",
                "Effect": "Allow",
                "Resource": [
                    f"{ec2_account_prefix}:fleet/*",
                    f"{ec2_account_prefix}:instance/*",
                    f"{ec2_account_prefix}:volume/*",
                    f"{ec2_account_prefix}:network-interface/*",
                    f"{ec2_account_prefix}:launch-template/*",
                    f"{ec2_account_prefix}:spot-instances-request/*",
                ],
                "Action": "ec2:CreateTags",
                "Condition": {
                    "StringEquals": {
                        f"aws:RequestTag/{cluster_tag}": "owned",
                        "aws:RequestTag/eks:eks-cluster-name": cluster_name,
                        "ec2:CreateAction": [
                            "RunInstances",
                            "CreateFleet",
                            "CreateLaunchTemplate",
                        ],
                    },
                    "StringLike": {"aws:RequestTag/karpenter.sh/nodepool": "*"},
                },
            },
            {
                "Sid": "AllowScopedResourceTagging",
                "Effect": "Allow",
                "Resource": f"{ec2_account_prefix}:instance/*",
                "Action": "ec2:CreateTags",
                "Condition": {
                    "StringEquals": {f"aws:ResourceTag/{cluster_tag}": "owned"},
                    "StringLike": {"aws:ResourceTag/karpenter.sh/nodepool": "*"},
                    "StringEqualsIfExists": {"aws:RequestTag/eks:eks-cluster-name": cluster_name},
                    "ForAllValues:StringEquals": {
                        "aws:TagKeys": [
                            "eks:eks-cluster-name",
                            "karpenter.sh/nodeclaim",
                            "Name",
                        ]
                    },
                },
            },
            {
                "Sid": "AllowScopedDeletion",
                "Effect": "Allow",
                "Resource": [
                    f"{ec2_account_prefix}:instance/*",
                    f"{ec2_account_prefix}:launch-template/*",
                ],
                "Action": ["ec2:TerminateInstances", "ec2:DeleteLaunchTemplate"],
                "Condition": {
                    "StringEquals": {f"aws:ResourceTag/{cluster_tag}": "owned"},
                    "StringLike": {"aws:ResourceTag/karpenter.sh/nodepool": "*"},
                },
            },
        ]
    )
    _attach_policy(
        "karpenter-node-lifecycle-policy",
        controller_role,
        f"{cluster_name}-karpenter-node-lifecycle",
        node_lifecycle,
        settings.common_tags,
    )

    iam_integration = node_roles.karpenter.arn.apply(
        lambda node_role_arn: _policy_document(
            [
                {
                    "Sid": "AllowPassingInstanceRole",
                    "Effect": "Allow",
                    "Resource": node_role_arn,
                    "Action": "iam:PassRole",
                    "Condition": {
                        "StringEquals": {
                            "iam:PassedToService": ["ec2.amazonaws.com", "ec2.amazonaws.com.cn"]
                        }
                    },
                },
                {
                    "Sid": "AllowScopedInstanceProfileCreationActions",
                    "Effect": "Allow",
                    "Resource": f"arn:{partition}:iam::{account_id}:instance-profile/*",
                    "Action": "iam:CreateInstanceProfile",
                    "Condition": {
                        "StringEquals": {
                            f"aws:RequestTag/{cluster_tag}": "owned",
                            "aws:RequestTag/eks:eks-cluster-name": cluster_name,
                            "aws:RequestTag/topology.kubernetes.io/region": region,
                        },
                        "StringLike": {"aws:RequestTag/karpenter.k8s.aws/ec2nodeclass": "*"},
                    },
                },
                {
                    "Sid": "AllowScopedInstanceProfileTagActions",
                    "Effect": "Allow",
                    "Resource": f"arn:{partition}:iam::{account_id}:instance-profile/*",
                    "Action": "iam:TagInstanceProfile",
                    "Condition": {
                        "StringEquals": {
                            f"aws:ResourceTag/{cluster_tag}": "owned",
                            "aws:ResourceTag/topology.kubernetes.io/region": region,
                            f"aws:RequestTag/{cluster_tag}": "owned",
                            "aws:RequestTag/eks:eks-cluster-name": cluster_name,
                            "aws:RequestTag/topology.kubernetes.io/region": region,
                        },
                        "StringLike": {
                            "aws:ResourceTag/karpenter.k8s.aws/ec2nodeclass": "*",
                            "aws:RequestTag/karpenter.k8s.aws/ec2nodeclass": "*",
                        },
                    },
                },
                {
                    "Sid": "AllowScopedInstanceProfileActions",
                    "Effect": "Allow",
                    "Resource": f"arn:{partition}:iam::{account_id}:instance-profile/*",
                    "Action": [
                        "iam:AddRoleToInstanceProfile",
                        "iam:RemoveRoleFromInstanceProfile",
                        "iam:DeleteInstanceProfile",
                    ],
                    "Condition": {
                        "StringEquals": {
                            f"aws:ResourceTag/{cluster_tag}": "owned",
                            "aws:ResourceTag/topology.kubernetes.io/region": region,
                        },
                        "StringLike": {"aws:ResourceTag/karpenter.k8s.aws/ec2nodeclass": "*"},
                    },
                },
            ]
        )
    )
    _attach_policy(
        "karpenter-iam-integration-policy",
        controller_role,
        f"{cluster_name}-karpenter-iam-integration",
        iam_integration,
        settings.common_tags,
    )

    queue_policy = queue.arn.apply(
        lambda queue_arn: _policy_document(
            [
                {
                    "Sid": "AllowInterruptionQueueActions",
                    "Effect": "Allow",
                    "Resource": queue_arn,
                    "Action": ["sqs:DeleteMessage", "sqs:GetQueueUrl", "sqs:ReceiveMessage"],
                }
            ]
        )
    )
    _attach_policy(
        "karpenter-interruption-policy",
        controller_role,
        f"{cluster_name}-karpenter-interruption",
        queue_policy,
        settings.common_tags,
    )

    zonal_shift_policy = _policy_document(
        [
            {
                "Sid": "AllowZonalShiftStatusReadOnly",
                "Effect": "Allow",
                "Resource": "*",
                "Action": "arc-zonal-shift:GetManagedResource",
                "Condition": {
                    "StringEquals": {
                        "arc-zonal-shift:ResourceIdentifier": (
                            f"arn:{partition}:eks:{region}:{account_id}:cluster/{cluster_name}"
                        )
                    }
                },
            }
        ]
    )
    _attach_policy(
        "karpenter-zonal-shift-policy",
        controller_role,
        f"{cluster_name}-karpenter-zonal-shift",
        zonal_shift_policy,
        settings.common_tags,
    )

    discovery_policy = _policy_document(
        [
            {
                "Sid": "AllowRegionalReadActions",
                "Effect": "Allow",
                "Resource": "*",
                "Action": [
                    "ec2:DescribeCapacityReservations",
                    "ec2:DescribeImages",
                    "ec2:DescribeInstances",
                    "ec2:DescribeInstanceStatus",
                    "ec2:DescribeInstanceTypeOfferings",
                    "ec2:DescribeInstanceTypes",
                    "ec2:DescribeLaunchTemplates",
                    "ec2:DescribePlacementGroups",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeSpotPriceHistory",
                    "ec2:DescribeSubnets",
                ],
                "Condition": {"StringEquals": {"aws:RequestedRegion": region}},
            },
            {
                "Sid": "AllowSSMReadActions",
                "Effect": "Allow",
                "Resource": f"arn:{partition}:ssm:{region}::parameter/aws/service/*",
                "Action": "ssm:GetParameter",
            },
            {
                "Sid": "AllowPricingReadActions",
                "Effect": "Allow",
                "Resource": "*",
                "Action": "pricing:GetProducts",
            },
            {
                "Sid": "AllowUnscopedInstanceProfileListAction",
                "Effect": "Allow",
                "Resource": "*",
                "Action": "iam:ListInstanceProfiles",
            },
            {
                "Sid": "AllowInstanceProfileReadActions",
                "Effect": "Allow",
                "Resource": f"arn:{partition}:iam::{account_id}:instance-profile/*",
                "Action": "iam:GetInstanceProfile",
            },
        ]
    )
    _attach_policy(
        "karpenter-resource-discovery-policy",
        controller_role,
        f"{cluster_name}-karpenter-resource-discovery",
        discovery_policy,
        settings.common_tags,
    )

    controller_identity = aws.eks.PodIdentityAssociation(
        "karpenter-controller-pod-identity",
        cluster_name=kubernetes.cluster.eks_cluster.name,
        namespace="kube-system",
        service_account="karpenter",
        role_arn=controller_role.arn,
        tags=settings.common_tags,
        opts=pulumi.ResourceOptions(depends_on=[kubernetes.pod_identity_agent]),
    )

    return KarpenterInfrastructure(
        controller_role=controller_role,
        controller_identity=controller_identity,
        interruption_queue=queue,
    )
