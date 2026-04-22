#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"
SECRETS_DIR="${1:-$SCRIPT_DIR/../secrets}"

PRIVATE_OUT="$SECRETS_DIR/private_signing.key"
PUBLIC_OUT="$SECRETS_DIR/public_signing.pem"

mkdir -p "$SECRETS_DIR"

if [ ! -f "$PRIVATE_OUT" ] || [ ! -f "$PUBLIC_OUT" ]; then
    echo "Generating signing key pair..."
    openssl ecparam -genkey -name prime256v1 -out "$PRIVATE_OUT"
    openssl ec -in "$PRIVATE_OUT" -pubout -out "$PUBLIC_OUT"
    echo "  Generated: $PRIVATE_OUT"
    echo "  Generated: $PUBLIC_OUT"
else
    echo "  Signing keys already exist"
fi
