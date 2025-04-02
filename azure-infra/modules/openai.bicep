param prefix string
param region string

param accounts_name string = '${prefix}-openai-2025'

//az cognitiveservices account purge --name vpa-testopenai --resource-group vpa-test-rg --location "South India"

resource openAI 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${prefix}-openai'
  location: region
  sku: {
    name: 'S0'
  }
  kind: 'OpenAI'
  properties: {
    apiProperties: {}
    customSubDomainName: accounts_name
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
    publicNetworkAccess: 'Enabled'
    // restore: true 
  }
}

resource accounts_gpt_4o 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAI
  name: 'gpt-4o'
  sku: {
    name: 'GlobalStandard'
    capacity: 100
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-08-06'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
}

resource accounts_gpt_4o_mini 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAI
  name: 'gpt-4o-mini'
  dependsOn: [
    accounts_gpt_4o // Make this deployment wait for the first one to complete
  ]
  sku: {
    name: 'GlobalStandard'
    capacity: 100
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-mini'
      version: '2024-07-18'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
}

resource accounts_text_embedding_ada_002 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAI
  name: 'text-embedding-ada-002'
  dependsOn: [
    accounts_gpt_4o_mini // Make this deployment wait for the second one to complete
  ]
  sku: {
    name: 'Standard'
    capacity: 100
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-ada-002'
      version: '2'
    }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
}

// // Get API key
// resource openAIKey 'Microsoft.CognitiveServices/accounts/listKeys@2023-05-01' existing = {
//   parent: openAI
//   name: 'current'
// }

output endpoint string = openAI.properties.endpoint
// output key string = openAIKey.listKeys().key1
output info object = {
  endpoint: openAI.properties.endpoint
  // key: openAIKey.listKeys().key1
}
