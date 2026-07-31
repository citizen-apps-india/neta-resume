"""Least-privilege identities used by External Secrets and ingestion run pods."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

from neta_infra.cluster import KubernetesCluster
from neta_infra.data import DataLayer
from neta_infra.identity import create_pod_identity_role
from neta_infra.settings import InfraSettings


@dataclass(frozen=True, slots=True)
class WorkloadRoles:
    secrets_reader: aws.iam.Role
    evidence_writer: aws.iam.Role
    secrets_reader_identity: aws.eks.PodIdentityAssociation
    evidence_writer_identity: aws.eks.PodIdentityAssociation


def create_workload_roles(
    settings: InfraSettings,
    kubernetes: KubernetesCluster,
    data: DataLayer,
) -> WorkloadRoles:
    secrets_policy = pulumi.Output.all(
        data.runtime_secret.arn,
        kubernetes.encryption_key.arn,
    ).apply(
        lambda values: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "secretsmanager:DescribeSecret",
                            "secretsmanager:GetSecretValue",
                        ],
                        "Resource": values[0],
                    },
                    {
                        "Effect": "Allow",
                        "Action": "kms:Decrypt",
                        "Resource": values[1],
                        "Condition": {
                            "StringEquals": {
                                "kms:ViaService": f"secretsmanager.{settings.region}.amazonaws.com"
                            }
                        },
                    },
                ],
            }
        )
    )
    secrets_reader = create_pod_identity_role(
        "secrets-reader-role",
        f"{settings.cluster_name}-secrets-reader",
        cluster_name=settings.cluster_name,
        namespace="external-secrets",
        service_account="external-secrets",
        policy=secrets_policy,
        tags=settings.common_tags,
    )
    secrets_reader_identity = aws.eks.PodIdentityAssociation(
        "secrets-reader-pod-identity",
        cluster_name=kubernetes.cluster.eks_cluster.name,
        namespace="external-secrets",
        service_account="external-secrets",
        role_arn=secrets_reader.arn,
        tags=settings.common_tags,
        opts=pulumi.ResourceOptions(depends_on=[kubernetes.pod_identity_agent]),
    )

    evidence_policy = pulumi.Output.all(
        data.evidence_bucket.arn,
        kubernetes.encryption_key.arn,
    ).apply(
        lambda values: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                        "Resource": values[0],
                        "Condition": {"StringLike": {"s3:prefix": ["production/raw/*"]}},
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:AbortMultipartUpload",
                            "s3:GetObject",
                            "s3:ListMultipartUploadParts",
                            "s3:PutObject",
                        ],
                        "Resource": f"{values[0]}/production/raw/*",
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "kms:Decrypt",
                            "kms:Encrypt",
                            "kms:GenerateDataKey",
                        ],
                        "Resource": values[1],
                        "Condition": {
                            "StringEquals": {
                                "kms:ViaService": f"s3.{settings.region}.amazonaws.com"
                            }
                        },
                    },
                ],
            }
        )
    )
    evidence_writer = create_pod_identity_role(
        "evidence-writer-role",
        f"{settings.cluster_name}-evidence-writer",
        cluster_name=settings.cluster_name,
        namespace="neta-production",
        service_account="neta-ingestion",
        policy=evidence_policy,
        tags=settings.common_tags,
    )
    evidence_writer_identity = aws.eks.PodIdentityAssociation(
        "evidence-writer-pod-identity",
        cluster_name=kubernetes.cluster.eks_cluster.name,
        namespace="neta-production",
        service_account="neta-ingestion",
        role_arn=evidence_writer.arn,
        tags=settings.common_tags,
        opts=pulumi.ResourceOptions(depends_on=[kubernetes.pod_identity_agent]),
    )
    return WorkloadRoles(
        secrets_reader=secrets_reader,
        evidence_writer=evidence_writer,
        secrets_reader_identity=secrets_reader_identity,
        evidence_writer_identity=evidence_writer_identity,
    )
