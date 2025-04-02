param prefix string
param region string


resource log_workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-appinsights-log-workspace'
  location: region
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      legacy: 0
      searchVersion: 1
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    workspaceCapping: {
      dailyQuotaGb: json('-1')
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource appInsights 'microsoft.insights/components@2020-02-02' = {
  name: '${prefix}-appinsights'
  location: region
  kind: 'web'
  properties: {
    Application_Type: 'web'
    Flow_Type: 'Redfield'
    Request_Source: 'IbizaAIExtension'
    RetentionInDays: 90
    WorkspaceResourceId: log_workspace.id
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

output connectionString string = appInsights.properties.ConnectionString
output instrumentationKey string = appInsights.properties.InstrumentationKey
output info object = {
  connectionString: appInsights.properties.ConnectionString
  instrumentationKey: appInsights.properties.InstrumentationKey
}
