#!/bin/zsh

# switch macos silicon into emulated x86 mode with .zshrc alias command
# x86

# make sure you are authenticated in github
# gh auth login

# make sure you are authenticated to azure
# az login

# update azure function core tools if needed
# brew tap azure/functions
# brew install azure-functions-core-tools@4
# if upgrading on a machine that has 2.x or 3.x installed:
# brew link --overwrite azure-functions-core-tools@4

# Variables - customize as needed
RESOURCE_GROUP_NAME="devintaccounting"
LOCATION="germanywestcentral"
STORAGE_ACCOUNT_NAME="devintaccounting"
FUNCTION_APP_NAME="devintaccountingftools"
GITHUB_REPO_NAME="devintaccountingftools"
GITHUB_USER="devintev"
PYTHON_VERSION="3.11"
KEYVAULT_NAME="devintaccountingkeys"
COSMOSDB_ACCOUNT_NAME="devintaccountingdb"
PLAN_NAME="ASP-devintaccounting-8f76"

# Step 1: Check if Resource Group exists
if ! az group show --name $RESOURCE_GROUP_NAME &>/dev/null; then
    az group create --name $RESOURCE_GROUP_NAME --location $LOCATION
else
    echo "Resource Group $RESOURCE_GROUP_NAME already exists."
fi

# Step 2: Check if Storage Account exists
if ! az storage account show --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME &>/dev/null; then
    az storage account create --name $STORAGE_ACCOUNT_NAME --location $LOCATION --resource-group $RESOURCE_GROUP_NAME --sku Standard_LRS
else
    echo "Storage Account $STORAGE_ACCOUNT_NAME already exists."
fi

# Step 3: Create a new Consumption Plan in the same resource group if Function App does not exist and no plan is available
if ! az functionapp show --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP_NAME &>/dev/null; then
    if ! az functionapp plan show --name $PLAN_NAME --resource-group $RESOURCE_GROUP_NAME &>/dev/null; then
        az functionapp plan create --name $PLAN_NAME --resource-group $RESOURCE_GROUP_NAME --location $LOCATION --sku Y1 --is-linux
    else
        echo "Using existing Consumption Plan $PLAN_NAME in Resource Group $RESOURCE_GROUP_NAME."
    fi
else
    echo "Function App $FUNCTION_APP_NAME already exists. Skipping plan creation."
fi
else
    echo "Using existing Consumption Plan $PLAN_NAME in Resource Group $RESOURCE_GROUP_NAME."
fi

# Step 4: Create Azure Function App if it doesn't exist
attempts=0
max_attempts=5

while [ $attempts -lt $max_attempts ]; do
    if ! az functionapp show --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP_NAME &>/dev/null; then
        if az functionapp create \
            --resource-group $RESOURCE_GROUP_NAME \
            --plan $PLAN_NAME \
            --runtime python \
            --runtime-version $PYTHON_VERSION \
            --functions-version 4 \
            --name $FUNCTION_APP_NAME \
            --storage-account $STORAGE_ACCOUNT_NAME \
            --os-type Linux; then
            break
        else
            echo "Create operation is in progress or failed. Retrying in 30 seconds..."
            sleep 30
            attempts=$((attempts + 1))
        fi
    else
        echo "Function App $FUNCTION_APP_NAME already exists."
        break
    fi

done

if [ $attempts -eq $max_attempts ]; then
    echo "Failed to create Azure Function App after $max_attempts attempts."
    exit 1
fi

# Step 5: Assign Managed Identity to Function App
az functionapp identity assign --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP_NAME

# Step 6: Get Managed Identity Principal ID
PRINCIPAL_ID=$(az functionapp identity show --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP_NAME --query principalId --output tsv)

# Step 7: Check if Key Vault exists
if ! az keyvault show --name $KEYVAULT_NAME --resource-group $RESOURCE_GROUP_NAME &>/dev/null; then
    az keyvault create --name $KEYVAULT_NAME --resource-group $RESOURCE_GROUP_NAME --location $LOCATION
else
    echo "Key Vault $KEYVAULT_NAME already exists."
fi

# Step 8: Grant Function App access to Key Vault
az keyvault set-policy --name $KEYVAULT_NAME --object-id $PRINCIPAL_ID --secret-permissions get list

# Step 9: Check if Cosmos DB Account exists
if ! az cosmosdb show --name $COSMOSDB_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME &>/dev/null; then
    az cosmosdb create --name $COSMOSDB_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --locations regionName=$LOCATION
else
    echo "Cosmos DB Account $COSMOSDB_ACCOUNT_NAME already exists."
fi

# Step 10: Grant Function App access to Cosmos DB
COSMOSDB_CONNECTION_STRING=$(az cosmosdb keys list --name $COSMOSDB_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --type connection-strings --query connectionStrings[0].connectionString --output tsv)
az functionapp config appsettings set --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP_NAME --settings "CosmosDBConnectionString=$COSMOSDB_CONNECTION_STRING"

# Step 11: Grant Function App access to Storage Account
STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --query [0].value --output tsv)

if [ -z "$STORAGE_ACCOUNT_KEY" ]; then
  echo "Failed to retrieve Storage Account Key. Exiting..."
  exit 1
fi

az functionapp config appsettings set --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP_NAME --settings "AzureWebJobsStorage=$STORAGE_ACCOUNT_KEY"

# Verify if AzureWebJobsStorage was set successfully
AZUREWEBJOBS_STORAGE=$(az functionapp config appsettings list --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP_NAME --query "[?name=='AzureWebJobsStorage'].value" --output tsv)
if [ -z "$AZUREWEBJOBS_STORAGE" ]; then
  echo "AzureWebJobsStorage could not be set. Exiting..."
  exit 1
else
  echo "AzureWebJobsStorage set successfully."
fi
