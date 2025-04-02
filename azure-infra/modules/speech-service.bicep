param prefix string
param region string

// -${uniqueString(resourceGroup().id)}
resource speechService 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${prefix}-speech'
  location: region
  sku: {
    name: 'S0'
  }
  kind: 'SpeechServices'
  identity: {
    type: 'None'
  }
  properties: {
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
    publicNetworkAccess: 'Enabled'
    // restore: true 
  }
}

// Get the API key
// resource speechKey 'Microsoft.CognitiveServices/accounts/listKeys@2023-05-01' existing = {
//   parent: speechService
//   name: 'current'
// }

output region string = region
// output key string = speechKey.listKeys().key1
output endpoint string = speechService.properties.endpoint
output info object = {
  region: region
  // key: speechKey.listKeys().key1
  endpoint: speechService.properties.endpoint
}


