"""Durable evidence storage and production PostgreSQL."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

from neta_infra.cluster import KubernetesCluster
from neta_infra.network import Network
from neta_infra.settings import InfraSettings


@dataclass(frozen=True, slots=True)
class DataLayer:
    evidence_bucket: aws.s3.Bucket
    runtime_secret: aws.secretsmanager.Secret
    database: aws.rds.Instance


def create_data_layer(
    settings: InfraSettings,
    account_id: str,
    network: Network,
    kubernetes: KubernetesCluster,
) -> DataLayer:
    bucket = aws.s3.Bucket(
        "raw-evidence",
        bucket=f"neta-resume-{account_id}-production-evidence",
        force_destroy=False,
        tags={**settings.common_tags, "DataClassification": "public-source-evidence"},
        opts=pulumi.ResourceOptions(protect=settings.protect_data),
    )
    aws.s3.BucketOwnershipControls(
        "raw-evidence-ownership",
        bucket=bucket.id,
        rule=aws.s3.BucketOwnershipControlsRuleArgs(
            object_ownership="BucketOwnerEnforced",
        ),
    )
    aws.s3.BucketPublicAccessBlock(
        "raw-evidence-public-access",
        bucket=bucket.id,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True,
    )
    aws.s3.BucketVersioning(
        "raw-evidence-versioning",
        bucket=bucket.id,
        versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(
            status="Enabled",
        ),
    )
    aws.s3.BucketServerSideEncryptionConfiguration(
        "raw-evidence-encryption",
        bucket=bucket.id,
        rules=[
            aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
                bucket_key_enabled=True,
                apply_server_side_encryption_by_default=(
                    aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
                        sse_algorithm="aws:kms",
                        kms_master_key_id=kubernetes.encryption_key.arn,
                    )
                ),
            )
        ],
    )
    aws.s3.BucketPolicy(
        "raw-evidence-policy",
        bucket=bucket.id,
        policy=bucket.arn.apply(
            lambda bucket_arn: json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "DenyInsecureTransport",
                            "Effect": "Deny",
                            "Principal": "*",
                            "Action": "s3:*",
                            "Resource": [bucket_arn, f"{bucket_arn}/*"],
                            "Condition": {"Bool": {"aws:SecureTransport": "false"}},
                        }
                    ],
                }
            )
        ),
    )

    runtime_secret = aws.secretsmanager.Secret(
        "runtime-secret",
        name="neta/production/runtime",
        description=(
            "Runtime DSNs for migration, ingestion, control API, and Dagster metadata; "
            "populated only by the audited database bootstrap procedure"
        ),
        kms_key_id=kubernetes.encryption_key.arn,
        recovery_window_in_days=30,
        tags=settings.common_tags,
        opts=pulumi.ResourceOptions(protect=settings.protect_data),
    )

    database_subnets = aws.rds.SubnetGroup(
        "database-subnets",
        name=f"{settings.cluster_name}-database",
        subnet_ids=network.vpc.isolated_subnet_ids,
        tags=settings.common_tags,
    )
    database_security_group = aws.ec2.SecurityGroup(
        "database-security-group",
        name=f"{settings.cluster_name}-postgresql",
        description="PostgreSQL access from EKS nodes only",
        vpc_id=network.vpc.vpc_id,
        ingress=[],
        egress=[],
        revoke_rules_on_delete=True,
        tags=settings.common_tags,
    )
    aws.ec2.SecurityGroupRule(
        "database-from-eks",
        type="ingress",
        security_group_id=database_security_group.id,
        source_security_group_id=kubernetes.cluster.node_security_group_id,
        protocol="tcp",
        from_port=5432,
        to_port=5432,
        description="PostgreSQL from EKS system and Karpenter nodes",
    )
    parameter_group = aws.rds.ParameterGroup(
        "database-parameters",
        name=f"{settings.cluster_name}-postgres18",
        family="postgres18",
        parameters=[
            aws.rds.ParameterGroupParameterArgs(name="rds.force_ssl", value="1"),
            aws.rds.ParameterGroupParameterArgs(
                name="log_connections",
                value="receipt,authentication,authorization",
            ),
            aws.rds.ParameterGroupParameterArgs(name="log_disconnections", value="1"),
        ],
        tags=settings.common_tags,
    )
    monitoring_role = aws.iam.Role(
        "database-monitoring-role",
        name=f"{settings.cluster_name}-rds-monitoring",
        assume_role_policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "monitoring.rds.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ),
        tags=settings.common_tags,
    )
    aws.iam.RolePolicyAttachment(
        "database-monitoring-policy",
        role=monitoring_role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole",
    )

    database = aws.rds.Instance(
        "postgresql",
        identifier=f"{settings.cluster_name}-postgresql",
        engine="postgres",
        engine_version="18.4",
        instance_class=settings.database_instance_class,
        db_name="neta",
        username="neta_admin",
        manage_master_user_password=True,
        master_user_secret_kms_key_id=kubernetes.encryption_key.arn,
        port=5432,
        multi_az=True,
        publicly_accessible=False,
        db_subnet_group_name=database_subnets.name,
        vpc_security_group_ids=[database_security_group.id],
        parameter_group_name=parameter_group.name,
        allocated_storage=settings.database_allocated_storage_gb,
        max_allocated_storage=settings.database_max_storage_gb,
        storage_type="gp3",
        storage_encrypted=True,
        kms_key_id=kubernetes.encryption_key.arn,
        backup_retention_period=settings.database_backup_retention_days,
        backup_window="18:30-19:30",
        maintenance_window="sun:19:30-sun:20:30",
        auto_minor_version_upgrade=True,
        allow_major_version_upgrade=False,
        apply_immediately=False,
        copy_tags_to_snapshot=True,
        delete_automated_backups=False,
        deletion_protection=settings.protect_data,
        skip_final_snapshot=False,
        final_snapshot_identifier=f"{settings.cluster_name}-postgresql-final",
        enabled_cloudwatch_logs_exports=["postgresql", "upgrade"],
        monitoring_interval=60,
        monitoring_role_arn=monitoring_role.arn,
        performance_insights_enabled=True,
        performance_insights_kms_key_id=kubernetes.encryption_key.arn,
        performance_insights_retention_period=7,
        iam_database_authentication_enabled=True,
        tags={**settings.common_tags, "DataClassification": "application-database"},
        opts=pulumi.ResourceOptions(protect=settings.protect_data),
    )
    return DataLayer(
        evidence_bucket=bucket,
        runtime_secret=runtime_secret,
        database=database,
    )
