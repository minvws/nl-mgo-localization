#!/bin/bash

SCRIPT_DIR="$(dirname "$0")"
PRIVATE_OUT="$SCRIPT_DIR/../secrets/private_signing.pem"
PUBLIC_OUT="$SCRIPT_DIR/../secrets/public_signing.pem"

openssl ecparam -genkey -name prime256v1 -out $PRIVATE_OUT
openssl ec -in $PRIVATE_OUT -pubout -out $PUBLIC_OUT
