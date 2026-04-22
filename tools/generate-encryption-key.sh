#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_DIR="${1:-$SCRIPT_DIR/../secrets}"

PRIVATE_OUT="$SECRETS_DIR/private_encryption.key"
PUBLIC_OUT="$SECRETS_DIR/placeholder_jwe_encryption.pub"

mkdir -p "$SECRETS_DIR"

if [ ! -f "$PRIVATE_OUT" ] || [ ! -f "$PUBLIC_OUT" ]; then
    echo "Generating encryption key pair..."
    openssl genrsa -out "$PRIVATE_OUT" 2048
    openssl rsa -in "$PRIVATE_OUT" -pubout -out "$PUBLIC_OUT"
    echo "  Generated: $PRIVATE_OUT"
    echo "  Generated: $PUBLIC_OUT"
else
    echo "  Encryption keys already exist"
fi
