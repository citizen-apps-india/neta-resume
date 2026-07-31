"""One-time state, encryption, and preview-only GitHub OIDC bootstrap.

This stack is separate because an S3 backend cannot create the bucket that stores its own state.
Apply it once with a local backend and an administrator's short-lived AWS SSO session. Production
updates remain human-run until an observed least-privilege apply policy has been reviewed.
"""

from __future__ import annotations

import json

import pulumi
import pulumi_aws as aws

config = pulumi.Config()
region = aws.config.region or "ap-south-1"
repository = config.get("githubRepository") or "citizen-apps-india/neta-resume"
github_environment = config.get("githubEnvironment") or "production"
caller = aws.get_caller_identity()
partition = aws.get_partition().partition
account_id = caller.account_id
common_tags = {
    "Project": "citizen-apps-india",
    "Application": "neta-resume",
    "Environment": "production",
    "ManagedBy": "pulumi-bootstrap",
}
protected = pulumi.ResourceOptions(protect=True)

project_boundary = aws.resourcegroups.Group(
    "project-boundary",
    name="citizen-apps-india",
    description=(
        "Tag based AWS project boundary for Citizen Apps India. "
        "resource lifecycle remains managed by Pulumi stacks"
    ),
    resource_query=aws.resourcegroups.GroupResourceQueryArgs(
        type="TAG_FILTERS_1_0",
        query=json.dumps(
            {
                "ResourceTypeFilters": ["AWS::AllSupported"],
                "TagFilters": [{"Key": "Project", "Values": ["citizen-apps-india"]}],
            }
        ),
    ),
    tags=common_tags,
    opts=protected,
)

state_key = aws.kms.Key(
    "pulumi-state-key",
    description="Pulumi production state encryption",
    enable_key_rotation=True,
    deletion_window_in_days=30,
    tags=common_tags,
    opts=protected,
)
aws.kms.Alias(
    "pulumi-state-key-alias",
    name="alias/neta-resume-pulumi-state",
    target_key_id=state_key.key_id,
    opts=protected,
)

state_bucket_name = f"neta-resume-{account_id}-pulumi-state"
state_bucket = aws.s3.Bucket(
    "pulumi-state",
    bucket=state_bucket_name,
    force_destroy=False,
    tags={**common_tags, "DataClassification": "infrastructure-state"},
    opts=protected,
)
aws.s3.BucketOwnershipControls(
    "pulumi-state-ownership",
    bucket=state_bucket.id,
    rule=aws.s3.BucketOwnershipControlsRuleArgs(object_ownership="BucketOwnerEnforced"),
    opts=protected,
)
aws.s3.BucketPublicAccessBlock(
    "pulumi-state-public-access",
    bucket=state_bucket.id,
    block_public_acls=True,
    block_public_policy=True,
    ignore_public_acls=True,
    restrict_public_buckets=True,
    opts=protected,
)
aws.s3.BucketVersioning(
    "pulumi-state-versioning",
    bucket=state_bucket.id,
    versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(status="Enabled"),
    opts=protected,
)
aws.s3.BucketServerSideEncryptionConfiguration(
    "pulumi-state-encryption",
    bucket=state_bucket.id,
    rules=[
        aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
            bucket_key_enabled=True,
            apply_server_side_encryption_by_default=(
                aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
                    sse_algorithm="aws:kms",
                    kms_master_key_id=state_key.arn,
                )
            ),
        )
    ],
    opts=protected,
)
aws.s3.BucketPolicy(
    "pulumi-state-policy",
    bucket=state_bucket.id,
    policy=state_bucket.arn.apply(
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
    opts=protected,
)

github_oidc = aws.iam.OpenIdConnectProvider(
    "github-actions-oidc",
    url="https://token.actions.githubusercontent.com",
    client_id_lists=["sts.amazonaws.com"],
    tags=common_tags,
    opts=protected,
)
preview_role = aws.iam.Role(
    "github-preview-role",
    name="neta-prod-pulumi-preview",
    max_session_duration=3600,
    assume_role_policy=github_oidc.arn.apply(
        lambda oidc_arn: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Federated": oidc_arn},
                        "Action": "sts:AssumeRoleWithWebIdentity",
                        "Condition": {
                            "StringEquals": {
                                "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                                "token.actions.githubusercontent.com:sub": (
                                    f"repo:{repository}:environment:{github_environment}"
                                ),
                            }
                        },
                    }
                ],
            }
        )
    ),
    tags=common_tags,
    opts=protected,
)
aws.iam.RolePolicyAttachment(
    "github-preview-view-access",
    role=preview_role.name,
    policy_arn="arn:aws:iam::aws:policy/job-function/ViewOnlyAccess",
    opts=protected,
)

state_bucket_arn = f"arn:{partition}:s3:::{state_bucket_name}"
state_access_policy = state_key.arn.apply(
    lambda state_key_arn: json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PulumiStateLockingAndCheckpoints",
                    "Effect": "Allow",
                    "Action": [
                        "s3:DeleteObject",
                        "s3:GetBucketLocation",
                        "s3:GetObject",
                        "s3:ListBucket",
                        "s3:PutObject",
                    ],
                    "Resource": [state_bucket_arn, f"{state_bucket_arn}/*"],
                },
                {
                    "Sid": "PulumiStateEncryption",
                    "Effect": "Allow",
                    "Action": [
                        "kms:Decrypt",
                        "kms:DescribeKey",
                        "kms:Encrypt",
                        "kms:GenerateDataKey",
                    ],
                    "Resource": state_key_arn,
                },
            ],
        }
    )
)
aws.iam.RolePolicy(
    "github-preview-state-access",
    name="neta-prod-pulumi-preview-state",
    role=preview_role.name,
    policy=state_access_policy,
    opts=protected,
)

pulumi.export("stateBackendUrl", f"s3://{state_bucket_name}")
pulumi.export(
    "secretsProviderUrl",
    f"awskms://alias/neta-resume-pulumi-state?region={region}",
)
pulumi.export("previewRoleArn", preview_role.arn)
pulumi.export("projectBoundaryArn", project_boundary.arn)
pulumi.export("awsRegion", region)
