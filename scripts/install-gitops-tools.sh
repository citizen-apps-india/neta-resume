#!/usr/bin/env sh
set -eu

destination=${1:-/usr/local/bin}
temporary_directory=$(mktemp -d)
trap 'rm -rf "${temporary_directory}"' EXIT

case "$(uname -s)" in
  Linux) neta_platform=linux ;;
  Darwin) neta_platform=darwin ;;
  *) echo "unsupported operating system: $(uname -s)" >&2; exit 1 ;;
esac

case "$(uname -m)" in
  x86_64) neta_architecture=amd64 ;;
  arm64 | aarch64) neta_architecture=arm64 ;;
  *) echo "unsupported architecture: $(uname -m)" >&2; exit 1 ;;
esac

neta_target=${neta_platform}-${neta_architecture}
helm_archive=helm-v4.2.3-${neta_target}.tar.gz
kustomize_archive=kustomize_v5.8.1_${neta_platform}_${neta_architecture}.tar.gz
kubeconform_archive=kubeconform-${neta_target}.tar.gz

case "${neta_target}" in
  linux-amd64)
    helm_checksum=e9b88b4ee95b18c706839c28d3a0220e5bc470e9cd9262410c90793c45ff8b7c
    kustomize_checksum=029a7f0f4e1932c52a0476cf02a0fd855c0bb85694b82c338fc648dcb53a819d
    kubeconform_checksum=9bc2bffbf71f261128533edaf912153948b7ff238f9a531ae6d34466ec287883
    ;;
  linux-arm64)
    helm_checksum=21abd9354d39b2cd79a8d76be6912cd137a983cbf997193503fb8a6a6e2f2785
    kustomize_checksum=0953ea3e476f66d6ddfcd911d750f5167b9365aa9491b2326398e289fef2c142
    kubeconform_checksum=1f53fc8e81258197a35e8603054162a5af1de8c5af13746c71ab680d9534ed87
    ;;
  darwin-amd64)
    helm_checksum=ff3ac86755a45f3422473bc1200776aac0fe04c5766abe6ca66699f7b564b23b
    kustomize_checksum=ee7cf0c1e3592aa7bb66ba82b359933a95e7f2e0b36e5f53ed0a4535b017f2f8
    kubeconform_checksum=71dbc87ac9f24099a62b93570e65aa06312ba6ac8aea63b7f86e9d999edf5a92
    ;;
  darwin-arm64)
    helm_checksum=048ecf5ad3160f83d918f9fe945238d2132b079640f7b106175331c25f242c64
    kustomize_checksum=8886f8a78474e608cc81234f729fda188a9767da23e28925802f00ece2bab288
    kubeconform_checksum=f84f4dfbebf4a6b0b230385fa065a39ea35e02608c2b50d025dcf64775a69d67
    ;;
esac

verify_checksum() {
  expected_checksum=$1
  archive_path=$2
  if command -v sha256sum >/dev/null 2>&1; then
    echo "${expected_checksum}  ${archive_path}" | sha256sum -c -
  else
    actual_checksum=$(shasum -a 256 "${archive_path}" | awk '{print $1}')
    if [ "${actual_checksum}" != "${expected_checksum}" ]; then
      echo "checksum mismatch for ${archive_path}" >&2
      exit 1
    fi
  fi
}

mkdir -p "${destination}"

curl -fsSL -o "${temporary_directory}/${helm_archive}" \
  "https://get.helm.sh/${helm_archive}"
verify_checksum "${helm_checksum}" "${temporary_directory}/${helm_archive}"
tar -xzf "${temporary_directory}/${helm_archive}" -C "${temporary_directory}"
install -m 0755 "${temporary_directory}/${neta_target}/helm" "${destination}/helm"

curl -fsSL -o "${temporary_directory}/${kustomize_archive}" \
  "https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2Fv5.8.1/${kustomize_archive}"
verify_checksum "${kustomize_checksum}" "${temporary_directory}/${kustomize_archive}"
tar -xzf "${temporary_directory}/${kustomize_archive}" -C "${temporary_directory}"
install -m 0755 "${temporary_directory}/kustomize" "${destination}/kustomize"

curl -fsSL -o "${temporary_directory}/${kubeconform_archive}" \
  "https://github.com/yannh/kubeconform/releases/download/v0.8.0/${kubeconform_archive}"
verify_checksum "${kubeconform_checksum}" "${temporary_directory}/${kubeconform_archive}"
tar -xzf "${temporary_directory}/${kubeconform_archive}" -C "${temporary_directory}"
install -m 0755 "${temporary_directory}/kubeconform" "${destination}/kubeconform"
