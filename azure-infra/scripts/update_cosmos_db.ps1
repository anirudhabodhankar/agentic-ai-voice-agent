# PowerShell script to update Cosmos DB settings
# Usage: PowerShell -ExecutionPolicy Bypass -File "update_cosmos_db.ps1" -prefix "vpa-test"

param(
    [string]$prefix = "vpa"
)

# Set resource names based on prefix
$resourceGroupName = "$prefix-rg"
$cosmosDbResourceName = "$prefix-cosmosdb"

Write-Host "Updating Cosmos DB '$cosmosDbResourceName' in resource group '$resourceGroupName'..."

# Update Cosmos DB to disable local authentication
Write-Host "Disabling local authentication..."
az resource update --resource-group $resourceGroupName --name $cosmosDbResourceName --resource-type "Microsoft.DocumentDB/databaseAccounts" --set properties.disableLocalAuth=false

# Update Cosmos DB to enable public network access
Write-Host "Enabling public network access..."
az resource update --resource-group $resourceGroupName --name $cosmosDbResourceName --resource-type "Microsoft.DocumentDB/databaseAccounts" --set properties.publicNetworkAccess="Enabled"

Write-Host "Cosmos DB update completed successfully."