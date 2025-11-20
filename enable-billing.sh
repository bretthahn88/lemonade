#!/bin/bash

# Enable Billing Helper Script

set -e

# Check if gcloud is installed and set GCLOUD variable
if command -v gcloud &> /dev/null; then
    GCLOUD="gcloud"
elif [ -f "$HOME/google-cloud-sdk/bin/gcloud" ]; then
    GCLOUD="$HOME/google-cloud-sdk/bin/gcloud"
else
    echo "Error: gcloud CLI is not installed"
    exit 1
fi

# Get current project
PROJECT_ID=$($GCLOUD config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    echo "No active GCP project set."
    echo "Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "=========================================="
echo "Enable Billing for Project: $PROJECT_ID"
echo "=========================================="
echo ""

# Check if billing is already enabled
if $GCLOUD billing projects describe $PROJECT_ID --format='value(billingEnabled)' 2>/dev/null | grep -q "True"; then
    echo "✓ Billing is already enabled for this project!"
    exit 0
fi

echo "Billing is not enabled for this project."
echo ""
echo "IMPORTANT: New Google Cloud users get \$300 in FREE CREDITS!"
echo ""
echo "Opening billing setup page in your browser..."
echo ""
echo "Manual link (if browser doesn't open):"
echo "https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
echo ""

# Try to open browser
if command -v xdg-open &> /dev/null; then
    xdg-open "https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID" &
elif command -v open &> /dev/null; then
    open "https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID" &
fi

echo "=========================================="
echo "Steps to enable billing:"
echo "=========================================="
echo ""
echo "1. Sign in to the Google Cloud Console (should open automatically)"
echo ""
echo "2. If you don't have a billing account:"
echo "   - Click 'CREATE BILLING ACCOUNT'"
echo "   - Enter your payment information"
echo "   - New users get \$300 FREE for 90 days!"
echo ""
echo "3. If you already have a billing account:"
echo "   - Select it from the dropdown"
echo "   - Click 'SET ACCOUNT'"
echo ""
echo "4. Wait for confirmation message"
echo ""
echo "5. Come back here and run:"
echo "   ./setup-gcp-auto.sh"
echo ""
echo "=========================================="
echo ""

# Wait and check periodically
echo "Waiting for billing to be enabled..."
echo "(This script will check every 10 seconds)"
echo "Press Ctrl+C to stop waiting and check manually later"
echo ""

COUNTER=0
while true; do
    sleep 10
    COUNTER=$((COUNTER + 10))

    if $GCLOUD billing projects describe $PROJECT_ID --format='value(billingEnabled)' 2>/dev/null | grep -q "True"; then
        echo ""
        echo "=========================================="
        echo "✓ SUCCESS! Billing is now enabled!"
        echo "=========================================="
        echo ""
        echo "You can now run:"
        echo "  ./setup-gcp-auto.sh"
        echo ""
        exit 0
    fi

    echo "Still waiting... ($COUNTER seconds elapsed)"

    if [ $COUNTER -eq 300 ]; then
        echo ""
        echo "Timed out after 5 minutes."
        echo "Please check the console and try running setup again."
        exit 1
    fi
done
