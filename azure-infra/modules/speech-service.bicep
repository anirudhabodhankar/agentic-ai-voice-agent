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

output info object = {
  region: region
  endpoint: speechService.properties.endpoint
}


