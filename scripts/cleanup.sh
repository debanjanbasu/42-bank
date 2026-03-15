#!/bin/bash
# 42-Bank Post-Hackathon Cleanup Script
# Deletes all Azure resources to avoid charges

set -e

echo "⚠️  42-Bank Cleanup Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This will delete ALL 42-Bank Azure resources:"
echo "  - Container Apps"
echo "  - Cosmos DB"
echo "  - Storage Account"
echo "  - Log Analytics"
echo "  - Application Insights"
echo ""
echo "💰 This will stop all charges!"
echo ""

read -p "Are you sure you want to proceed? (y/N) " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "❌ Cleanup cancelled"
    exit 0
fi

echo ""
echo "🗑️  Deleting resource group '42-bank'..."
az group delete --name 42-bank --yes --no-wait

echo ""
echo "✅ Cleanup initiated!"
echo ""
echo "Note: Resource deletion may take a few minutes."
echo "You can check status with:"
echo "  az group deployment list --resource-group 42-bank"
echo ""
echo "Thank you for using 42-Bank! 🚀"
