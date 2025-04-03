#PowerShell -ExecutionPolicy Bypass -File "deploy.ps1" -prefix "vpa-test" -region "South India" -region_openai "South India" -region_speech "centralindia"
# PowerShell script to deploy Bicep templates to Azure

param(
    [string]$prefix = "vpa",
    [string]$region = "South India",
    [string]$region_openai = "South India",
    [string]$region_speech = "centralindia"
)

# Login to Azure
az login

# Set the subscription (optional)
# az account set --subscription "Your Subscription Name"

# Deploy the Bicep templates
$deployment = az deployment sub create `
    --location $region `
    --template-file ../main.bicep `
    --parameters prefix=$prefix region=$region region_openai=$region_openai region_speech=$region_speech `
    --query "properties.outputs" -o json | ConvertFrom-Json

Write-Host "Deployment completed for prefix: $prefix in region: $region"

# Generate local .env file
Write-Host "Generating local .env file..."

$resourceGroupName = "$prefix-rg"
$envFilePath = "../../server/.env2"

# Define your Redis resource name and resource group name
$redisResourceName = "$prefix-redis"
$aiseearchResourceName = "$prefix-search"
$cosmosDbResourceName = "$prefix-cosmosdb"
$openAiResourceName = "$prefix-openai"
$speechResourceName = "$prefix-speech"
$appInsightsResourceName = "$prefix-appinsights"
$containerResourceName = "$prefix-app"

# Get the Redis resource details
$redisResource = az resource show --resource-group $resourceGroupName --name $redisResourceName --resource-type "Microsoft.Cache/Redis"
$aiseearchResource = az resource show --resource-group $resourceGroupName --name $aiseearchResourceName --resource-type "Microsoft.Search/searchServices"
$cosmosDbResource = az resource show --resource-group $resourceGroupName --name $cosmosDbResourceName --resource-type "Microsoft.DocumentDB/databaseAccounts"
$openAiResource = az resource show --resource-group $resourceGroupName --name $openAiResourceName --resource-type "Microsoft.CognitiveServices/accounts"
$speechResource = az resource show --resource-group $resourceGroupName --name $speechResourceName --resource-type "Microsoft.CognitiveServices/accounts"
$appInsightsResource = az resource show --resource-group $resourceGroupName --name $appInsightsResourceName --resource-type "Microsoft.Insights/components"
$containerResource = az resource show --resource-group $resourceGroupName --name $containerResourceName --resource-type "Microsoft.App/containerApps"


######################################   Redis  ######################################
# Parse the JSON output to get the hostname
$redisHostName = ($redisResource | ConvertFrom-Json).properties.hostName
Write-Output "Redis Hostname: $redisHostName"
$redisPort = ($redisResource | ConvertFrom-Json).properties.sslPort
Write-Output "Redis Port: $redisPort"
$redisSslPort = ($redisResource | ConvertFrom-Json).properties.sslPort
Write-Output "Redis SSL Port: $redisSslPort"

# Get the access keys
$redisKeys = az redis list-keys --resource-group $resourceGroupName --name $redisResourceName | ConvertFrom-Json

# Print the keys
# Write-Output "Primary Key: $($redisKeys.primaryKey)"
# Write-Output "Secondary Key: $($redisKeys.secondaryKey)"

######################################   Azure AI Search  ######################################
$searchEndpoint = ($aiseearchResource | ConvertFrom-Json).name

Write-Output "Search Endpoint: https://$searchEndpoint.search.windows.net"
# Get the access keys
$searchKeys = az search admin-key show --resource-group $resourceGroupName --service-name $aiseearchResourceName | ConvertFrom-Json

# Print the keys
# Write-Output "Primary Key: $($searchKeys.primaryKey)"
# Write-Output "Secondary Key: $($searchKeys.secondaryKey)"

#######################################   Cosmos DB  ######################################
$cosmosDbHostName = ($cosmosDbResource | ConvertFrom-Json).properties.documentEndpoint
Write-Output "Cosmos DB Hostname: $cosmosDbHostName"

$cosmosDbKeys = az cosmosdb keys list --resource-group $resourceGroupName --name $cosmosDbResourceName --type keys --output json | ConvertFrom-Json
# Print the keys
# Write-Output "Primary Key: $($cosmosDbKeys.primaryMasterKey)"
# Write-Output "Secondary Key: $($cosmosDbKeys.secondaryMasterKey)"

#######################################   OpenAI  ######################################
$openAiHostName = ($openAiResource | ConvertFrom-Json).properties.endpoint
Write-Output "OpenAI Hostname: $openAiHostName"
$openAiKeys = az cognitiveservices account keys list --name $openAiResourceName --resource-group $resourceGroupName | ConvertFrom-Json
# Print the keys
# Write-Output "Primary Key: $($openAiKeys.key1)"
# Write-Output "Secondary Key: $($openAiKeys.key2)"

#######################################   Speech  ######################################
$speechHostName = ($speechResource | ConvertFrom-Json).location
Write-Output "Speech Hostname: $speechHostName"
$speechKeys = az cognitiveservices account keys list --name $speechResourceName --resource-group $resourceGroupName | ConvertFrom-Json
# Print the keys
# Write-Output "Primary Key: $($speechKeys.key1)"
# Write-Output "Secondary Key: $($speechKeys.key2)"

#######################################   Application Insights  ######################################
$appInsightsHostName = ($appInsightsResource | ConvertFrom-Json).properties.ApplicationId
$appInsightsConnectionString = ($appInsightsResource | ConvertFrom-Json).properties.ConnectionString
Write-Output "App Insights Hostname: $appInsightsHostName"
# Write-Output "App Insights ConnectionString: $appInsightsConnectionString"


#########################################   Container  ######################################
$containerHostName = ($containerResource | ConvertFrom-Json).properties.configuration.ingress.fqdn
Write-Output "Container Hostname: $containerHostName"


$envContent = @"

AZURE_OPENAI_API_KEY="$($openAiKeys.key1)"
AZURE_OPENAI_ENDPOINT="$openAiHostName"
AZURE_OPENAI_DEPLOYMENT="gpt-4o"
AZURE_OPENAI_EMBEDDING_DEPLOYMENT="text-embedding-ada-002"

AZURE_AI_SEARCH_ENDPOINT="https://$searchEndpoint.search.windows.net"
AZURE_AI_SEARCH_KEY="$($searchKeys.primaryKey)"
AZURE_AI_SEARCH_INDEX_DOC="doc-index"
AZURE_AI_SEARCH_INDEX_TOOL="tool-index"

COSMOS_DB_ENDPOINT="$cosmosDbHostName"
COSMOS_DB_KEY="$($cosmosDbKeys.primaryMasterKey)"
COSMOS_DB_NAME="demodb"
COSMOS_DB_CONTAINER_DEVICES="devices"
COSMOS_DB_CONTAINER_TRANSACTIONS="transactions"
COSMOS_DB_CONTAINER_NOTIFICATIONS="notifications"
COSMOS_DB_CONTAINER_TICKETS="tickets"
COSMOS_DB_CONTAINER_PLANS="plans"
COSMOS_DB_CONTAINER_KHATABOOK="khatabook"

REDIS_HOST="$redisHostName"
REDIS_PORT='$redisPort'
REDIS_KEY="$($redisKeys.primaryKey)"

AZURE_TTS_REGION="$region_speech"
AZURE_TTS_API_KEY="$($speechKeys.key1)"
AUTO_DETECT_SOURCE_LANGUAGE_CONFIG="en-IN,hi-IN"
AZURE_TTS_SYNTHESIS_VOICE_NAME="hi-IN-AartiNeural"

APPLICATIONINSIGHTS_CONNECTION_STRING="$appInsightsConnectionString"
AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED=True

#App Config
IS_SINGLE_APP="False"
# SERVER_URL="https://$containerHostName/voice_chat_stream"
# SERVER_URL_WS="wss://$containerHostName/ws/voice_chat_stream_socket"
SERVER_URL="http://localhost:8000/voice_chat_stream"
SERVER_URL_WS="ws://localhost:8000/ws/voice_chat_stream_socket"

AUDIO_INPUT_FORMAT="amr"
MAX_MESSAGE_HISTORY=-6 #multiple of 2. one user and one assistant message 
SESSION_TIMOUT=60	#In seconds
"@

# Write to .env file
$envContent | Out-File -FilePath $envFilePath -Encoding utf8

Write-Host "Local .env file created at: $envFilePath"


# Update Cosmos DB settings
Write-Host "Updating Cosmos DB settings..."
$updateScriptPath = Join-Path -Path $PSScriptRoot -ChildPath "update_cosmos_db.ps1"
& $updateScriptPath -prefix $prefix

Write-Host "Deployment and configuration completed successfully."
