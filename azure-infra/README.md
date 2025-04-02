# azure-infra

This project is designed to deploy various Azure resources using Bicep templates for the Vendor PA application. It includes modules for Redis Cache, Azure AI Search, Application Insights, Speech Service, Cosmos DB, OpenAI resources, and Container Apps. The project automates the deployment of infrastructure and performs necessary post-deployment configuration.

## Project Structure

- **main.bicep**: The main Bicep template that orchestrates the deployment of all resources. It takes parameters like prefix and region to create appropriately named resources.
  
- **parameters/**: Contains parameter files for different environments.
  - **dev.parameters.json**: Parameter values for the development environment.

- **modules/**: Contains individual Bicep modules for each resource.
  - **redis.bicep**: Configuration for deploying an Azure Redis Cache instance.
  - **ai-search.bicep**: Configuration for deploying an Azure AI Search resource.
  - **app-insights.bicep**: Configuration for deploying an Application Insights resource.
  - **speech-service.bicep**: Configuration for deploying an Azure Speech Service resource.
  - **cosmos-db.bicep**: Configuration for deploying an Azure Cosmos DB resource.
  - **openai.bicep**: Configuration for deploying an OpenAI resource, including models GPT-4o and text-embedding-ada-002.
  - **container-app.bicep**: Configuration for deploying an Azure Container App.

- **scripts/**: Contains scripts for deployment and configuration.
  - **deploy.ps1**: PowerShell script to deploy the Bicep templates to Azure and perform post-deployment configuration.
  - **update_cosmos_db.ps1**: Script to update Cosmos DB authentication and network settings after deployment.

- **.github/workflows/**: Contains GitHub Actions workflow configuration for automating deployments.
  - **deploy.yml**: Workflow configuration for deploying the Bicep templates.

- **.gitignore**: Specifies files and directories to be ignored by Git.

## Deployment Process

The deployment process includes:
1. Provisioning all Azure resources
2. Retrieving connection strings and keys from deployed resources
3. Generating the server environment configuration file
4. Updating specific Cosmos DB settings
5. Running data ingestion scripts for the database and search indexes

## Deployment Instructions

1. **Prerequisites**:
   - Azure CLI installed and configured
   - PowerShell 5.1 or later
   - Python 3.8 or later
   - Access to an Azure subscription

2. **Deploying the Infrastructure**:
   - Navigate to the project directory
   - Use the PowerShell script to deploy the resources:
     ```
     PowerShell -ExecutionPolicy Bypass -File "scripts/deploy.ps1" -prefix "vpa-test" -region "South India" -region_openai "South India" -region_speech "centralindia"
     ```
   - Parameters:
     - `prefix`: Resource name prefix (default: "vpa")
     - `region`: Primary region for deployment (default: "South India")
     - `region_openai`: Region for OpenAI resources (default: "South India")
     - `region_speech`: Region for Speech Service (default: "centralindia")

3. **Post-Deployment**:
   The script automatically:
   - Creates environment configuration in `server/.env2`
   - Updates Cosmos DB settings
   - Runs data ingestion scripts

## GitHub Actions

- The project includes a GitHub Actions workflow that automatically deploys the infrastructure when changes are pushed to the repository.
- The workflow can be customized in the `.github/workflows/deploy.yml` file.

## Notes

- Make sure the server directory exists at the expected location (two levels up from the scripts directory)
- The deployment creates a resource group named `{prefix}-rg` containing all deployed resources
- For local development, the script configures environment variables to connect to cloud resources