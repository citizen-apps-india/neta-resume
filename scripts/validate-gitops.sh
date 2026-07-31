#!/usr/bin/env sh
set -eu

for required_tool in helm kustomize kubeconform; do
  if ! command -v "${required_tool}" >/dev/null 2>&1; then
    echo "${required_tool} is required; run scripts/install-gitops-tools.sh first" >&2
    exit 1
  fi
done

temporary_directory=$(mktemp -d)
trap 'rm -rf "${temporary_directory}"' EXIT

kustomize build deploy/k8s/overlays/production >"${temporary_directory}/workloads.yaml"
kustomize build deploy/k8s/secrets/overlays/production >"${temporary_directory}/secrets.yaml"
kustomize build deploy/argocd/production >"${temporary_directory}/argocd.yaml"

helm template neta-dagster dagster \
  --repo https://dagster-io.github.io/helm \
  --version 1.13.16 \
  --namespace neta-production \
  --values deploy/argocd/values/dagster-production.yaml \
  >"${temporary_directory}/dagster.yaml"

for rendered in \
  workloads.yaml \
  secrets.yaml \
  argocd.yaml \
  dagster.yaml; do
  kubeconform \
    -strict \
    -summary \
    -ignore-missing-schemas \
    -kubernetes-version 1.36.0 \
    "${temporary_directory}/${rendered}"
done
