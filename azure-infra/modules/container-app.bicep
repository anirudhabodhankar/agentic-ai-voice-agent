param prefix string
param region string

resource managedEnvironments_container_app 'Microsoft.App/managedEnvironments@2024-10-02-preview' = {
  name: '${prefix}-app-managed-env'
  location: region
  properties: {
    zoneRedundant: false
    kedaConfiguration: {}
    daprConfiguration: {}
    customDomainConfiguration: {}
    workloadProfiles: [
      {
        workloadProfileType: 'Consumption'
        name: 'Consumption'
        enableFips: false
      }
      {
        workloadProfileType: 'D4'
        name: 'wp-one'
        enableFips: false
        minimumCount: 0
        maximumCount: 1
      }
    ]
    peerAuthentication: {
      mtls: {
        enabled: false
      }
    }
    peerTrafficConfiguration: {
      encryption: {
        enabled: false
      }
    }
    publicNetworkAccess: 'Enabled'
  }
}

resource container_app 'Microsoft.App/containerapps@2024-10-02-preview' = {
  name: '${prefix}-app'
  location: region
  kind: 'containerapps'
  identity: {
    type: 'None'
  }
  properties: {
    managedEnvironmentId: managedEnvironments_container_app.id
    environmentId: managedEnvironments_container_app.id
    workloadProfileName: 'wp-one'
    configuration: {
      
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        exposedPort: 0
        transport: 'Auto'
        traffic: [
          {
            weight: 100
            latestRevision: true
          }
        ]
        allowInsecure: false
        stickySessions: {
          affinity: 'none'
        }
      }
     
      identitySettings: []
      maxInactiveRevisions: 100
    }
    template: {
      containers: [
        {

          name: '${prefix}-container'
          image: 'python:3.11-slim'
          resources: {
            cpu: 2
            memory: '8Gi'
          }
          probes: []
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
        cooldownPeriod: 7200
        pollingInterval: 30
        rules: [
          {
            name: 'http-scaler'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
      volumes: []
    }
  }
}

output containerAppId string = container_app.id
output containerAppName string = container_app.name

output info object = {
  appid: container_app.id
  appName: container_app.name
  appUrl: 'https://${container_app.properties.configuration.ingress.fqdn}'
}
