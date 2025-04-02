param prefix string
param region string

resource aiSearch 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: '${prefix}-search'
  location: region
  sku: {
    name: 'basic'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'Enabled'
    networkRuleSet: {
      ipRules: []
      bypass: 'None'
    }
    encryptionWithCmk: {
      enforcement: 'Unspecified'
    }
    disableLocalAuth: false
    authOptions: {
      apiKeyOnly: {}
    }
    disabledDataExfiltrationOptions: []
    semanticSearch: 'disabled'
  }
}

output info object = {
  endpoint: 'https://${aiSearch.name}.search.windows.net'
}
