targetScope = 'subscription'

param prefix string
param region string = 'South India'  // Default region for all resources if not specified
param region_openai string = 'South India'  // Default region for OpenAI if not specified
param region_speech string = 'centralindia'  // Default region for Speech if not specified

var resourceGroupName = '${prefix}-rg'

// Create the resource group
resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: region
}

module aiSearch './modules/ai-search.bicep' = {
  name: 'aiSearchDeployment'
  scope: rg
  params: {
    prefix: prefix
    region: region
  }
}

module speechService './modules/speech-service.bicep' = {
  name: 'speechServiceDeployment'
  scope: rg
  params: {
    prefix: prefix
    region: region_speech
  }
}

module cosmosDb './modules/cosmos-db.bicep' = {
  name: 'cosmosDbDeployment'
  scope: rg
  params: {
    prefix: prefix
    region: region
  }
}

module openAi './modules/openai.bicep' = {
  name: 'openAiDeployment'
  scope: rg
  params: {
    prefix: prefix
    region: region_openai
  }
}

module appInsights './modules/app-insights.bicep' = {
  name: 'appInsightsDeployment'
  scope: rg
  params: {
    prefix: prefix
    region: region
  }
}

module containerApp './modules/container-app.bicep' = {
  name: 'containerAppDeployment'
  scope: rg
  params: {
    prefix: prefix
    region: region_openai
  }
}

module redis './modules/redis.bicep' = {
  name: 'redisDeployment'
  scope: rg
  params: {
    prefix: prefix
    region: region
  }
}
