param prefix string
param region string

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts@2024-12-01-preview' = {
  name: '${prefix}-cosmosdb'
  location: region
  tags: {
    'hidden-workload-type': 'Learning'
    defaultExperience: 'Core (SQL)'
    'hidden-cosmos-mmspecial': ''
  }
  kind: 'GlobalDocumentDB'
  identity: {
    type: 'None'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    isVirtualNetworkFilterEnabled: false
    virtualNetworkRules: []
    disableKeyBasedMetadataWriteAccess: false
    enableFreeTier: false
    enableAnalyticalStorage: false
    analyticalStorageConfiguration: {
      schemaType: 'WellDefined'
    }
    databaseAccountOfferType: 'Standard'
    enableMaterializedViews: false
    capacityMode: 'Serverless'
    defaultIdentity: 'FirstPartyIdentity'
    networkAclBypass: 'None'
    disableLocalAuth: false
    enablePartitionMerge: false
    enablePerRegionPerPartitionAutoscale: false
    enableBurstCapacity: false
    enablePriorityBasedExecution: false
    minimalTlsVersion: 'Tls12'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
      maxIntervalInSeconds: 5
      maxStalenessPrefix: 100
    }
    locations: [
      {
        locationName: region
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    cors: []
    capabilities: []
    ipRules: []
    backupPolicy: {
      type: 'Periodic'
      periodicModeProperties: {
        backupIntervalInMinutes: 240
        backupRetentionIntervalInHours: 8
        backupStorageRedundancy: 'Geo'
      }
    }
    networkAclBypassResourceIds: []
    diagnosticLogSettings: {
      enableFullTextQuery: 'None'
    }
    capacity: {
      totalThroughputLimit: 4000
    }
  }
}

resource databaseAccounts_cosmosdb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-12-01-preview' = {
  parent: cosmosDb
  name: 'demodb'
  properties: {
    resource: {
      id: 'demodb'
    }
  }
}

// // Get the primary key
// resource cosmosDbKey 'Microsoft.DocumentDB/databaseAccounts/listKeys@2023-04-15' existing = {
//   parent: cosmosDb
//   name: 'default'
// }

output endpoint string = cosmosDb.properties.documentEndpoint
// output key string = cosmosDbKey.listKeys().primaryMasterKey
output info object = {
  endpoint: cosmosDb.properties.documentEndpoint
  // key: cosmosDbKey.listKeys().primaryMasterKey
}
