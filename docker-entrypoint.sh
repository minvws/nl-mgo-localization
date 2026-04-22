#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_DIR="${SCRIPT_DIR}/secrets"

mkdir -p "${SECRETS_DIR}"

if [[ ! -w "${SECRETS_DIR}" ]]; then
    echo "ERROR: ${SECRETS_DIR} is not writable by $(whoami) ($(id -u):$(id -g))."
    echo "Current ownership: $(stat -c '%u:%g %A' "${SECRETS_DIR}")"
    echo "Fix on host: sudo chown -R $(id -u):$(id -g) secrets"
    exit 1
fi

echo "Checking for signing and encryption keys..."

for script in generate-sign-key.sh generate-encryption-key.sh; do
    "$SCRIPT_DIR/tools/$script" "${SECRETS_DIR}"
done

echo "Signing and encryption keys ready."
echo ""

exec "$@"
