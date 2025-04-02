param prefix string
param region string

resource redisCache 'Microsoft.Cache/Redis@2024-11-01' = {
  name:  '${prefix}-redis'
  location: region
  properties: {
    redisVersion: '6.0'
    sku: {
      name: 'Standard'
      family: 'C'
      capacity: 0
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    redisConfiguration: {
      'aad-enabled': 'true'
      'maxmemory-reserved': '30'
      'maxfragmentationmemory-reserved': '30'
      'maxmemory-delta': '30'
    }
    updateChannel: 'Stable'
    disableAccessKeyAuthentication: false
  }
}

output info object = {
  host: '${redisCache.name}.redis.cache.windows.net'
  port: '6380'
}
