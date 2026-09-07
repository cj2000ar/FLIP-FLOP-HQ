#!/bin/bash
# Generate self-signed certificates for FlipFlop API (dev/test only)
# For production: Use Let's Encrypt + certbot

set -e

CERT_DIR="certs"
CERT_NAME="flipflop-api"
DAYS_VALID=365

echo "=========================================="
echo "Generating Self-Signed Certificate"
echo "=========================================="
echo "Validity: $DAYS_VALID days"
echo "Output: $CERT_DIR/"

# Create cert directory
mkdir -p "$CERT_DIR"

# Generate private key
echo "Generating private key..."
openssl genrsa -out "$CERT_DIR/$CERT_NAME.key" 2048

# Generate certificate
echo "Generating certificate..."
openssl req -new -x509 \
    -key "$CERT_DIR/$CERT_NAME.key" \
    -out "$CERT_DIR/$CERT_NAME.crt" \
    -days "$DAYS_VALID" \
    -subj "/C=US/ST=CA/L=San Francisco/O=FlipFlop/CN=flipflop-api.local"

echo ""
echo "Certificate generated successfully!"
echo ""
echo "Files:"
echo "  Private Key: $CERT_DIR/$CERT_NAME.key"
echo "  Certificate: $CERT_DIR/$CERT_NAME.crt"
echo ""
echo "⚠️  WARNING: Self-signed certificate"
echo "   - Use for dev/test only"
echo "   - Browsers will warn about untrusted certificate"
echo "   - For production: Use Let's Encrypt (see DEPLOYMENT.md)"
echo ""
echo "Test HTTPS connection:"
echo "  curl -k https://localhost:443/health"
echo "  (use -k to ignore certificate warning)"
