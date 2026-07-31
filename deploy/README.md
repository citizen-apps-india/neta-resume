# Production Kubernetes and GitOps deployment

This directory contains the production-only application manifests. Infrastructure and privileged
cluster operators are declared in `infra/`; neither layer has been applied to AWS yet. The existing
GitHub Actions ingestion schedules remain authoritative until the production cutover is explicitly
approved.

## Ownership boundary

Pulumi owns resources that require account-specific values or cluster-wide privileges:

- the EKS Managed Argo CD Capability and its minimal capability role;
- the production AppProject because its role contains an account-specific Identity Center group ID;
- the protected `neta-production` namespace and Pod Security labels;
- the Karpenter and External Secrets Operator Helm releases and CRDs;
- the Karpenter `EC2NodeClass` and bounded, consolidating `NodePool`;
- EKS Pod Identity associations for Karpenter, External Secrets, and ingestion;
- the RDS `ExternalName` Service and the non-secret S3 platform ConfigMap.

Argo CD receives cluster-wide read access and `AmazonEKSAdminPolicy` scoped only to
`neta-production`. It cannot create cluster-scoped resources through the Neta AppProject.

## Reconciliation order

The managed root application creates three manually gated child applications:

1. `neta-production-secrets` materialises runtime PostgreSQL secrets from AWS Secrets Manager.
2. `neta-production-workloads` runs the forward-only schema, seed, and manifest reconciliation hook,
   then rolls out the private FastAPI control service.
3. `neta-production-dagster` installs the pinned Dagster chart, daemon, webserver, and Neta user-code
   deployment. Each ingestion execution is a Kubernetes Job.

Argo CD reconciles deployments; Dagster schedules and executes data pipelines. PostgreSQL control
state remains authoritative for pause, frequency, retry, and manual run requests.

## Deployment gates

`SET_BY_IMAGE_PROMOTION` remains intentionally unresolved. Before the first manual sync, a reviewed
pull request must replace it with immutable control and orchestration image digests and the matching
Git commit SHA. Account-specific bucket names, RDS endpoints, IAM role ARNs, and credentials are never
committed; Pulumi and EKS Pod Identity supply them.

The AWS Secrets Manager object `neta/production/runtime` must be populated through the audited database
bootstrap procedure with:

- `NETA_MIGRATE_DATABASE_URL`: owner/DDL psycopg DSN;
- `NETA_DATABASE_URL`: ingestion write-role psycopg DSN;
- `NETA_BACKEND_DATABASE_URL`: control-runtime asyncpg DSN;
- `DAGSTER_POSTGRES_PASSWORD`: password for Dagster's separate metadata database and role.

The production overlay permits PostgreSQL egress only within the configured `10.42.0.0/16` VPC.
Changing the Pulumi VPC CIDR therefore requires the matching manifest patch in the same reviewed change.

Automated sync is intentionally absent. It can be enabled only after image promotion, database restore
verification, a successful manual production sync, health review, and ingestion parity against the
still-running GitHub Actions schedule.

## Identity boundaries

- External Secrets uses an EKS Pod Identity role that reads only `neta/production/runtime` and its KMS
  key.
- `neta-ingestion` uses a separate Pod Identity role scoped to `production/raw/*` in the evidence bucket.
- Karpenter uses a service-account-scoped Pod Identity role and tag-scoped EC2/IAM permissions.
- `neta-dagster` has namespaced Kubernetes permissions to launch Jobs but no AWS data role.
- `neta-control` and the deployment reconciler do not receive Kubernetes API tokens.
- The Identity Center `platform-admins` group receives only global Argo CD `VIEWER` access. Its
  `platform-operator` project role can inspect and sync `neta-production` Applications, read their
  logs, and resolve the registered cluster name; it cannot edit or delete Application definitions,
  invoke resource actions, access pod shells, administer Argo CD, or target another project.
- The group ID is supplied through the private Pulumi stack configuration as
  `argocdPlatformAdminGroupId`. It must never be committed to this public repository.

No secret value, static AWS access key, kubeconfig, OIDC token, or account-specific role ARN belongs in
Git.

## Validation

The validation path renders every Kustomize overlay and the pinned Dagster chart, then checks known
objects against Kubernetes 1.36 schemas:

```bash
scripts/install-gitops-tools.sh /a/writable/bin
PATH="/a/writable/bin:$PATH" scripts/validate-gitops.sh
uv run pytest -q tests/test_gitops_manifests.py
```

The installer supports Linux and macOS on AMD64 and ARM64 and verifies all downloaded archives with
pinned SHA-256 checksums. `kubeconform` ignores only custom resources whose upstream schemas are not
published; source-policy tests separately enforce Argo scope, Pod Security, NetworkPolicy defaults,
Pod Identity, version parity, and the absence of native Secret objects.

## Bootstrap only after approval

Prerequisites are EKS Kubernetes 1.36, the EKS Managed Argo CD Capability, AWS Identity Center, the EKS
Pod Identity Agent, PostgreSQL 18, and the Pulumi-owned platform operators. Pulumi creates the cluster
registration Secret and root Application; `deploy/argocd/bootstrap/root-application.yaml` is retained
only as a reviewable break-glass equivalent.

The first sync remains manual. Database migrations are forward-only; application rollback never
reverses schema migrations. RDS point-in-time restore and final-snapshot procedures must be verified
before cutover because there is intentionally no staging environment.
