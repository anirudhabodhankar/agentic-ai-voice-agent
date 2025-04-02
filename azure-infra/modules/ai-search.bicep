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

// // Get the admin key
// resource searchServiceKey 'Microsoft.Search/searchServices/listAdminKeys@2023-11-01' existing = {
//   parent: aiSearch
//   name: 'current'
// }

output endpoint string = 'https://${aiSearch.name}.search.windows.net'
// output key string = searchServiceKey.listKeys().primaryKey
output info object = {
  endpoint: 'https://${aiSearch.name}.search.windows.net'
  // key: searchServiceKey.listKeys().primaryKey
}
