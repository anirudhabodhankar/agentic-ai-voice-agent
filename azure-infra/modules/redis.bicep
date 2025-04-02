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

// // Get the primary key
// resource redisKey 'Microsoft.Cache/Redis/listKeys@2023-04-01' existing = {
//   parent: redisCache
//   name: 'default'
// }

output host string = '${redisCache.name}.redis.cache.windows.net'
output port string = '6380'
// output key string = redisKey.listKeys().primaryKey
output info object = {
  host: '${redisCache.name}.redis.cache.windows.net'
  port: '6380'
  // key: redisKey.listKeys().primaryKey
}
