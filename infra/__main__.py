"""Pulumi program for the single production environment."""

import pulumi

from neta_infra.platform import build_platform

platform = build_platform()

pulumi.export("region", platform.settings.region)
pulumi.export("clusterName", platform.settings.cluster_name)
pulumi.export("clusterEndpoint", platform.kubernetes.cluster.eks_cluster.endpoint)
pulumi.export("evidenceBucket", platform.data.evidence_bucket.bucket)
pulumi.export("databaseAddress", platform.data.database.address)
pulumi.export("runtimeSecretArn", platform.data.runtime_secret.arn)
pulumi.export("secretsReaderRoleArn", platform.workloads.secrets_reader.arn)
pulumi.export("evidenceWriterRoleArn", platform.workloads.evidence_writer.arn)
pulumi.export("karpenterControllerRoleArn", platform.karpenter.controller_role.arn)
pulumi.export("karpenterNodeRoleName", platform.node_roles.karpenter.name)
pulumi.export("karpenterInterruptionQueue", platform.karpenter.interruption_queue.name)
pulumi.export("argocdCapabilityArn", platform.gitops.capability.arn)
pulumi.export("argocdCapabilityRoleArn", platform.gitops.capability_role.arn)
