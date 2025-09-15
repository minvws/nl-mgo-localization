#!/bin/bash

SCRIPT_DIR="$(dirname "$0")"
SECRETS_DIR="${1:-$SCRIPT_DIR/../secrets}"

PRIVATE_OUT="$SECRETS_DIR/private_signing.pem"
PUBLIC_OUT="$SECRETS_DIR/public_signing.pem"

openssl ecparam -genkey -name prime256v1 -out $PRIVATE_OUT
openssl ec -in $PRIVATE_OUT -pubout -out $PUBLIC_OUT
