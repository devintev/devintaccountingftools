# Azure Functions Migration: devintaccountingftools
## Linux Consumption → Flex Consumption + Python 3.12 Upgrade

⚠️ **UPDATED 2025-10-08:** This plan includes critical fixes based on lessons learned from `hrmwebsitecasedb` migration. See Steps 1.2.5, 1.3.5, 1.3.6 for **CRITICAL** workflow and settings fixes that prevent functions from loading.

---

## Table of Contents
1. [Migration Overview](#migration-overview)
2. [Current Configuration](#current-configuration)
3. [Migration Strategy](#migration-strategy)
4. [Detailed Steps](#detailed-steps)
5. [Testing Checklist](#testing-checklist)
6. [Rollback Plan](#rollback-plan)
7. [Resources](#resources)

---

## Migration Overview

### Why Migrate?
Microsoft is retiring the **Azure Functions Linux Consumption** hosting plan on **September 30, 2028**. According to the main migration plan (see `/systemcontrol/AZURE_FUNCTIONS_MIGRATIONS.md`), `devintaccountingftools` is:
- ✅ **Eligible for immediate migration**
- 🟢 **Low Priority** (DevInt Tools category)
- Can be used as a test case for other migrations

### Migration Goals
- ✅ Move from Linux Consumption to Flex Consumption
- ✅ Upgrade Python from 3.11 → 3.12 (latest stable)
- ✅ Maintain original function app name (`devintaccountingftools`)
- ✅ Update GitHub Actions CI/CD pipeline
- ✅ Zero downtime migration

### Benefits of Flex Consumption
- **Faster scaling** - Reduced cold starts
- **Built-in networking** - Advanced networking at no extra cost
- **Better performance control** - Right-size compute
- **Per-instance concurrency** - More granular execution control

### Timeline
- **Priority:** 🟢 Low (can proceed after dev apps tested)
- **Estimated Work:** 2-3 hours
- **Monitoring Period:** 48 hours
- **Microsoft Deadline:** 2028-09-30

---

## Current Configuration

### Azure Resources

**Function App:**
- **Name:** `devintaccountingftools`
- **Resource Group:** `devintaccountingftools`
- **Location:** Germany West Central
- **Current Plan:** Linux Consumption
- **Runtime:** Python 3.11
- **URL:** `https://devintaccountingftools.azurewebsites.net`

**Storage Account:**
- **Name:** `devintaccountingftools`
- **Connection String:** Configured in app settings

**Key Vault:**
- **Name:** `devintaccountingftkeys`
- **Purpose:** Storing secrets for the application

**Application Insights:**
- **Instrumentation Key:** `3748f5e3-5851-4ef3-b67e-05a5eab50e59`

### Application Settings

| Setting | Value/Purpose |
|---------|---------------|
| `AZURE_FUNCTION_APP_URL` | `https://devintaccountingftools.azurewebsites.net/api` |
| `KEY_VAULT_NAME` | `devintaccountingftkeys` |
| `FUNCTIONS_WORKER_RUNTIME` | `python` |
| `FUNCTIONS_EXTENSION_VERSION` | `~4` |
| `ENABLE_ORYX_BUILD` | `1` (Linux Consumption specific) |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `1` (Linux Consumption specific) |

### Local Development

**Local Folder:**
```
/Users/voss/Library/CloudStorage/OneDrive-DevInt/code/devintaccountingftools
```

**Key Files:**
- `function_app.py` - Main application with HTTP triggers
- `requirements.txt` - Python dependencies
- `.github/workflows/main_devintaccountingftools.yml` - CI/CD workflow
- `hrmlib/` - Shared library (hrmtools)
- `local.settings.json` - Local development settings

**Dependencies (requirements.txt):**
```
azure-functions
azure-identity
azure-mgmt-web
azure-keyvault-secrets
azure-storage-blob
azure-storage-queue
azure-cosmos
sendgrid
openpyxl
pandas
pymsteams
requests
json2html
pytz
bs4
pyyaml
```

**Key Features:**
- HTTP-triggered functions
- Excel file processing (openpyxl, pandas)
- Email notifications (SendGrid)
- Microsoft Teams webhooks (pymsteams)
- Key Vault secret access
- Storage blob/queue operations
- Cosmos DB integration
- Custom logging with HTML output

### GitHub Configuration

**Repository:** `https://github.com/devintev/devintaccountingftools`

**Deployment:**
- **Method:** GitHub Actions (automated)
- **Branch:** `main`
- **Trigger:** Push to main or manual dispatch
- **Workflow File:** `.github/workflows/main_devintaccountingftools.yml`
- **Authentication:** Publish Profile (secret: `AZUREAPPSERVICE_PUBLISHPROFILE_669DECF2B5E447E99143963E8DFD1A91`)

**Current Workflow Process:**
1. Checkout code
2. Setup Python 3.11
3. Create virtual environment
4. Install dependencies from `requirements.txt`
5. Zip project
6. Upload artifact
7. Deploy to Azure using publish profile
8. Oryx build enabled during deployment

---

## Migration Strategy

### Approach: Direct Migration to Python 3.12 Flex

Since this is a **low-priority app**, we'll use a simplified single-phase approach:

```
┌─────────────────────────────────────────────────────────────────┐
│ Current State                                                    │
├─────────────────────────────────────────────────────────────────┤
│ devintaccountingftools                                          │
│ - Linux Consumption                                             │
│ - Python 3.11                                                   │
│ - GitHub Actions (Publish Profile)                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Migrate to Temporary Flex App                         │
├─────────────────────────────────────────────────────────────────┤
│ Create: devintaccountingftools-flex                            │
│ - Flex Consumption                                              │
│ - Python 3.12                                                   │
│ - Test deployment via Azure Portal Deployment Center           │
│ - Monitor 48 hours                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: Migrate to Final App (Original Name)                  │
├─────────────────────────────────────────────────────────────────┤
│ Delete: devintaccountingftools (old Linux Consumption)         │
│ Create: devintaccountingftools (new Flex, Python 3.12)         │
│ Configure: Azure Portal Deployment Center                      │
│ Test & Monitor: 48-72 hours                                    │
│ Delete: devintaccountingftools-flex                            │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Strategy?

✅ **Advantages:**
- Python 3.12 (latest stable, future-proof)
- Test Flex Consumption with minimal risk
- Low priority = safe to experiment
- Get original name back
- Zero downtime during testing

⚠️ **Considerations:**
- Need to test Python 3.12 compatibility
- Must update workflow authentication (no publish profiles in Flex)
- Two-step process (temporary → final)

---

## Detailed Steps

### Pre-Migration Checklist

- [ ] Review current functionality
- [ ] Verify all integrations work (Key Vault, Storage, Cosmos DB, SendGrid, Teams)
- [ ] Document current behavior
- [ ] Notify stakeholders of planned migration
- [ ] Ensure you have admin access to GitHub repo
- [ ] Backup current configuration (optional)

---

### Phase 1: Create and Test Temporary Flex App

#### Step 1.1: Get Storage Account Name

```bash
az functionapp config appsettings list \
  --name devintaccountingftools \
  --resource-group devintaccountingftools \
  --query "[?name=='AzureWebJobsStorage'].value" \
  -o tsv
```

**Expected:** Connection string with `AccountName=devintaccountingftools`

---

#### Step 1.2: Run Migration to Create Flex App

```bash
az functionapp flex-migration start \
  --source-name devintaccountingftools \
  --source-resource-group devintaccountingftools \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools \
  --storage-account devintaccountingftools
```

**What This Does:**
- Creates new Flex Consumption app named `devintaccountingftools-flex`
- Migrates app settings (AZURE_FUNCTION_APP_URL, KEY_VAULT_NAME, etc.)
- Migrates site configs (TLS, HTTP/2)
- Migrates system-assigned managed identity
- Creates new Application Insights instance
- **Note:** Will create with Python 3.11 initially (we'll upgrade to 3.12 in Phase 2)

**Expected Output:**
```
Flex Consumption function app 'devintaccountingftools-flex' created successfully
Successfully migrated N app settings...
Successfully migrated managed identity...
```

**Verify Creation:**
```bash
az functionapp show \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools \
  --query "{name:name, sku:sku, runtime:functionAppConfig.runtime, url:defaultHostName}"
```

**Azure Portal:**
https://portal.azure.com/#resource/subscriptions/854da132-9fce-4624-a0e9-7fa6ea46a6eb/resourceGroups/devintaccountingftools/providers/Microsoft.Web/sites/devintaccountingftools-flex

---

#### Step 1.2.5: 🔴 CRITICAL - Verify Runtime Settings

⚠️ **Lesson Learned:** The migration may not copy all essential runtime settings.

**Verify these settings exist:**
```bash
az functionapp config appsettings list \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools \
  --query "[?name=='FUNCTIONS_WORKER_RUNTIME' || name=='FUNCTIONS_EXTENSION_VERSION'].{name:name, value:value}"
```

**Expected output:**
```json
[
  {"name": "FUNCTIONS_WORKER_RUNTIME", "value": "python"},
  {"name": "FUNCTIONS_EXTENSION_VERSION", "value": "~4"}
]
```

**If missing, add them:**
```bash
az functionapp config appsettings set \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools \
  --settings \
    FUNCTIONS_WORKER_RUNTIME="python" \
    FUNCTIONS_EXTENSION_VERSION="~4"
```

**Why This Matters:**
Without these settings, functions won't load even if deployment succeeds. You'll see 404 errors on all endpoints.

---

#### Step 1.2.6: 🔴 CRITICAL - Configure Python v2 Runtime for Flex

⚠️ **NEW CRITICAL ISSUE (Oct 2025):** Flex Consumption has a platform limitation with Python v2 function apps.

**Problem:**
The migration creates the Flex app but does NOT preserve Python runtime configuration. Python v2 apps require special setup.

**Configure Python runtime explicitly:**
```bash
az functionapp update \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools \
  --set "functionAppConfig.runtime.name=python" \
       "functionAppConfig.runtime.version=3.11"
```

**Enable Worker Indexing (REQUIRED for Python v2):**
```bash
az functionapp config appsettings set \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools \
  --settings "AzureWebJobsFeatureFlags=EnableWorkerIndexing"
```

**Verify configuration:**
```bash
# Check runtime
az functionapp show \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools \
  --query "functionAppConfig.runtime"

# Expected: {"name": "python", "version": "3.11"}

# Check Worker Indexing
az functionapp config appsettings list \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools \
  --query "[?name=='AzureWebJobsFeatureFlags'].value"

# Expected: ["EnableWorkerIndexing"]
```

**Why This Matters:**
- Python v2 model (using `function_app.py`) requires Worker Indexing
- Runtime config gets lost during migration
- Without this, functions won't register even after deployment

**Source:** Platform limitation as of Oct 2025. Workaround tested and reliable.

---

#### Step 1.3: Configure Azure Portal Deployment Center

⚠️ **Important:** Flex Consumption apps do NOT support publish profiles. Use Azure Portal to auto-configure authentication.

**Instructions:**

1. **Navigate to Deployment Center:**
   ```
   Azure Portal → Function Apps → devintaccountingftools-flex → Deployment Center
   ```

2. **Configure Source:**
   - Click **Settings** (if needed)
   - Source: `GitHub`
   - Click `Authorize` if not already connected
   - Sign in to GitHub as `devintev`

3. **Select Repository:**
   - Organization: `devintev`
   - Repository: `devintaccountingftools`
   - Branch: `main`

4. **Authentication:**
   - Choose: `User-assigned identity` or accept default (Service Principal)
   - Portal will auto-create credentials

5. **Preview Workflow:**
   - Click `Preview file`
   - Verify it creates a new workflow (should be named like `main_devintaccountingftools-flex.yml`)
   - Check that it does NOT have `scm-do-build-during-deployment` or `enable-oryx-build`

6. **Save:**
   - Click `Save`
   - Portal will:
     - Create workflow file in `.github/workflows/`
     - Add necessary secrets to GitHub
     - Ready for deployment

**Documentation:**
- [GitHub Actions for Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-how-to-github-actions)
- [Flex Consumption How-To](https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-how-to)

---

#### Step 1.3.5: 🔴 CRITICAL - Fix Workflow File

⚠️ **Lesson Learned:** The auto-generated workflow includes `venv/` in the deployment package, causing functions to fail loading.

**Navigate to GitHub:**
```
https://github.com/devintev/devintaccountingftools/blob/main/.github/workflows/main_devintaccountingftools-flex.yml
```

**Find this section:**
```yaml
- name: Zip artifact for deployment
  run: zip release.zip ./* -r
```

**Fix 1 - Exclude venv/ (CRITICAL):**
Edit the workflow file and change to:
```yaml
- name: Zip artifact for deployment
  run: zip release.zip ./* -r -x "venv/*"
```

**Fix 2 - Add remote-build and post-deployment runtime config (CRITICAL):**

Find the deployment step and add `remote-build: true`:
```yaml
- name: 'Deploy to Azure Functions'
  uses: Azure/functions-action@v1
  id: deploy-to-function
  with:
    app-name: 'devintaccountingftools-flex'
    slot-name: 'Production'
    package: ${{ env.AZURE_FUNCTIONAPP_PACKAGE_PATH }}
    # Use service principal auth (auto-configured by Deployment Center)
    remote-build: true  # 🔴 ADD THIS - Required for Flex Consumption
```

**Fix 3 - Add post-deployment step to configure runtime:**

Add this step AFTER the deployment step:
```yaml
- name: 'Configure Python Runtime for Flex Consumption'
  run: |
    az functionapp update \
      --name devintaccountingftools-flex \
      --resource-group devintaccountingftools \
      --set "functionAppConfig.runtime.name=python" \
           "functionAppConfig.runtime.version=${{ env.PYTHON_VERSION }}"
```

**Why These Fixes:**
- ❌ Without venv exclusion: Deployment package bloated, functions fail to load
- ❌ Without remote-build: Python v2 functions won't work on Flex Consumption
- ❌ Without post-deployment step: Runtime config gets wiped, functions don't register

**Commit all changes:**
```bash
cd /Users/voss/Library/CloudStorage/OneDrive-DevInt/code/devintaccountingftools
git pull  # Get the new workflow file
# Edit .github/workflows/main_devintaccountingftools-flex.yml (apply all 3 fixes)
git add .github/workflows/main_devintaccountingftools-flex.yml
git commit -m "Fix: Exclude venv, enable remote-build, add runtime config"
git push origin main
```

---

#### Step 1.3.6: Disable Old Workflow

⚠️ **Lesson Learned:** Both old and new workflows trigger on push, causing duplicate deployments.

**Edit the OLD workflow:**
```
.github/workflows/main_devintaccountingftools.yml  (original, NOT -flex)
```

**Change the trigger:**
```yaml
on:
  # push:  # Disabled - migrated to Flex Consumption workflow
  #   branches:
  #     - main
  workflow_dispatch:  # Keep for emergency rollback
```

**Commit:**
```bash
git add .github/workflows/main_devintaccountingftools.yml
git commit -m "Disable old workflow auto-trigger (keep for rollback)"
git push origin main
```

**Why:** Prevents duplicate deployments and saves CI minutes while keeping manual rollback capability.

---

#### Step 1.4: Update Python Version to 3.12 (Optional for Phase 1)

You can either:
- **Option A:** Test with Python 3.11 first (safer)
- **Option B:** Jump directly to Python 3.12 (recommended)

**For Option B (Python 3.12):**

```bash
# Update the function app runtime
az functionapp config set \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools \
  --linux-fx-version "PYTHON|3.12"
```

**Verify:**
```bash
az functionapp config show \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools \
  --query "linuxFxVersion"
```

**Expected:** `"Python|3.12"`

---

#### Step 1.5: Test Local Compatibility with Python 3.12

**Update local environment:**
```bash
cd /Users/voss/Library/CloudStorage/OneDrive-DevInt/code/devintaccountingftools

# Check if Python 3.12 is installed
python3.12 --version

# Create virtual environment with Python 3.12
python3.12 -m venv .venv312
source .venv312/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run functions locally
func start
```

**Test all endpoints:**
- `/api/test` - Basic test function
- Any other HTTP endpoints in `function_app.py`

**Check for:**
- ❌ Import errors
- ❌ Deprecation warnings
- ❌ Runtime errors
- ✅ All functions work as expected

**If issues found:**
- Update `requirements.txt` with compatible versions
- Fix any Python 3.12 incompatibilities
- Commit changes

---

#### Step 1.6: Trigger First Deployment

**Method 1: Push a small change**
```bash
cd /Users/voss/Library/CloudStorage/OneDrive-DevInt/code/devintaccountingftools

# Make a small change or update comment
git add .
git commit -m "Test deployment to Flex Consumption app"
git push origin main
```

**Method 2: Manual workflow dispatch**
```
GitHub → Actions → Select workflow → Run workflow
```

**Monitor Deployment:**
```
GitHub → devintev/devintaccountingftools → Actions
```

Watch the workflow run for the `-flex` app.

---

#### Step 1.7: Verify Deployment

⚠️ **Lesson Learned:** Don't trust 200 OK on root URL alone. Verify functions actually loaded.

**1. Check if functions registered (MOST IMPORTANT):**
```bash
az functionapp function list \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools \
  --query "[].{name:name, triggerType:config.bindings[0].type}"
```

**Expected:** Should show your functions (e.g., `test`, etc.)
**If empty:** Functions didn't load. Check:
- venv excluded from zip? (Step 1.3.5)
- Runtime settings present? (Step 1.2.5)
- Check Application Insights logs

**2. Test app status:**
```bash
# Check overall health
curl https://devintaccountingftools-flex.azurewebsites.net

# Expected: 200 OK (but this doesn't mean functions loaded!)
```

**3. Test actual endpoints:**
```bash
# Get function key (if needed)
FUNCTION_KEY=$(az functionapp function keys list \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools \
  --function-name test \
  --query "default" -o tsv)

# Test the function
curl "https://devintaccountingftools-flex.azurewebsites.net/api/test?code=$FUNCTION_KEY"

# Expected: Function response (NOT 404)
```

**4. Check logs (if issues):**

**Option A - Live logs (Azure CLI):**
```bash
az functionapp logs tail \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools
```

**Option B - Azure Portal (RECOMMENDED for debugging):**
```
Azure Portal → devintaccountingftools-flex → Deployment Center → Logs
```

**Option C - Application Insights (best for historical data):**
```
Azure Portal → devintaccountingftools-flex → Application Insights → Logs
```

Use KQL query:
```kql
traces
| where timestamp > ago(1h)
| order by timestamp desc
| take 100
```

**Common Issues:**
- ❌ Functions list empty → venv in package or missing runtime settings
- ❌ 404 on endpoints → Functions didn't register
- ❌ 500 errors → Check Application Insights for exceptions

---

#### Step 1.8: Testing & Validation (48 hours)

**Functional Testing Checklist:**

- [ ] **HTTP Endpoints:**
  - [ ] `/api/test` responds correctly
  - [ ] All other endpoints work
  - [ ] Authentication works (function keys)

- [ ] **Azure Integrations:**
  - [ ] Key Vault access works (KEY_VAULT_NAME)
  - [ ] Storage Blob operations work
  - [ ] Storage Queue operations work
  - [ ] Cosmos DB queries work (if used)

- [ ] **External Integrations:**
  - [ ] SendGrid email sending works
  - [ ] Microsoft Teams webhooks work (pymsteams)

- [ ] **Data Processing:**
  - [ ] Excel file processing works (openpyxl, pandas)
  - [ ] JSON/HTML conversion works

- [ ] **Logging:**
  - [ ] Application Insights receives telemetry
  - [ ] Custom logging works
  - [ ] No error spikes

**Performance Testing:**
- [ ] Cold start times acceptable
- [ ] Execution times similar or better
- [ ] No timeout issues
- [ ] Scaling works under load

**Monitoring Commands:**
```bash
# Check app status
az functionapp show \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools \
  --query "{state:state, usageState:usageState}"

# Check recent invocations (Application Insights query)
# Use Azure Portal → Application Insights → Logs
```

**Success Criteria:**
- ✅ All tests pass
- ✅ No errors for 48 hours
- ✅ Performance equal or better
- ✅ All integrations working

---

### Phase 2: Migrate to Original Name with Python 3.12

⚠️ **Only proceed after Phase 1 is fully validated!**

#### Step 2.1: Pre-Deletion Checklist

- [ ] `-flex` app running successfully for 48+ hours
- [ ] All functionality verified
- [ ] No open issues
- [ ] Stakeholders notified
- [ ] Ready for brief downtime during app recreation

---

#### Step 2.2: Backup Configuration (Optional)

```bash
# Export current settings
az functionapp config appsettings list \
  --name devintaccountingftools \
  --resource-group devintaccountingftools \
  > devintaccountingftools-backup-settings.json

# Export full configuration
az functionapp show \
  --name devintaccountingftools \
  --resource-group devintaccountingftools \
  > devintaccountingftools-backup-config.json
```

---

#### Step 2.3: Delete Original Linux Consumption App

⚠️ **DESTRUCTIVE - No undo!**

```bash
az functionapp delete \
  --name devintaccountingftools \
  --resource-group devintaccountingftools
```

**Verify deletion:**
```bash
# Should return error
az functionapp show \
  --name devintaccountingftools \
  --resource-group devintaccountingftools
```

---

#### Step 2.4: Create New Flex App with Original Name (Python 3.12)

```bash
az functionapp create \
  --resource-group devintaccountingftools \
  --name devintaccountingftools \
  --storage-account devintaccountingftools \
  --flexconsumption-location "Germany West Central" \
  --runtime python \
  --runtime-version 3.12
```

**Expected Output:**
```json
{
  "name": "devintaccountingftools",
  "sku": "FlexConsumption",
  "functionAppConfig": {
    "runtime": {
      "name": "python",
      "version": "3.12"
    }
  }
}
```

**Verify:**
```bash
az functionapp show \
  --name devintaccountingftools \
  --resource-group devintaccountingftools \
  --query "{name:name, sku:sku, runtime:functionAppConfig.runtime}"
```

---

#### Step 2.5: Configure App Settings

```bash
# Copy KEY_VAULT_NAME from -flex app
az functionapp config appsettings set \
  --name devintaccountingftools \
  --resource-group devintaccountingftools \
  --settings \
    KEY_VAULT_NAME="devintaccountingftkeys" \
    AZURE_FUNCTION_APP_URL="https://devintaccountingftools.azurewebsites.net/api"

# Enable system-assigned identity for Key Vault access
az functionapp identity assign \
  --name devintaccountingftools \
  --resource-group devintaccountingftools
```

**Copy other settings from -flex if needed:**
```bash
# List settings from -flex app
az functionapp config appsettings list \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools

# Apply manually any custom settings
```

---

#### Step 2.5.5: 🔴 CRITICAL - Grant Managed Identity Permissions

⚠️ **Lesson Learned:** The migration does NOT copy RBAC role assignments. Must grant manually.

**Get the new app's Managed Identity Principal ID:**
```bash
NEW_PRINCIPAL_ID=$(az functionapp identity show \
  --name devintaccountingftools \
  --resource-group devintaccountingftools \
  --query principalId -o tsv)

echo "Principal ID: $NEW_PRINCIPAL_ID"
```

**Grant Blob Storage Access:**
```bash
az role assignment create \
  --assignee $NEW_PRINCIPAL_ID \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/854da132-9fce-4624-a0e9-7fa6ea46a6eb/resourceGroups/devintaccountingftools/providers/Microsoft.Storage/storageAccounts/devintaccountingftools"
```

**Grant Key Vault Access:**
```bash
az role assignment create \
  --assignee $NEW_PRINCIPAL_ID \
  --role "Key Vault Secrets User" \
  --scope "/subscriptions/854da132-9fce-4624-a0e9-7fa6ea46a6eb/resourceGroups/devintaccountingftools/providers/Microsoft.KeyVault/vaults/devintaccountingftkeys"
```

**Verify Permissions:**
```bash
# List role assignments for the new principal
az role assignment list \
  --assignee $NEW_PRINCIPAL_ID \
  --query "[].{role:roleDefinitionName, scope:scope}" -o table

# Expected:
# - Storage Blob Data Contributor on storage account
# - Key Vault Secrets User on key vault
```

**Wait for permission propagation (30 seconds):**
```bash
echo "Waiting for permissions to propagate..." && sleep 30
```

**Why This Matters:**
Without these permissions, functions will fail with 500 errors when trying to:
- Read templates from Blob Storage
- Fetch secrets from Key Vault (API keys, connection strings)

---

#### Step 2.6: Configure Deployment Center for New App

**Repeat Step 1.3 but for the new app with original name:**

1. Navigate to: `Azure Portal → devintaccountingftools → Deployment Center`
2. Source: `GitHub`
3. Organization: `devintev`
4. Repository: `devintaccountingftools`
5. Branch: `main`
6. Authentication: User-assigned identity or Service Principal
7. Preview workflow file (should be `main_devintaccountingftools.yml`)
8. **Save**

**Result:**
- Workflow file `.github/workflows/main_devintaccountingftools.yml` is REPLACED
- Old publish profile authentication removed
- New service principal authentication added
- Python version: 3.12

---

#### Step 2.6.5: 🔴 CRITICAL - Configure Python v2 Runtime & Fix Workflow

**1. Configure Python runtime for new app:**
```bash
az functionapp update \
  --name devintaccountingftools \
  --resource-group devintaccountingftools \
  --set "functionAppConfig.runtime.name=python" \
       "functionAppConfig.runtime.version=3.12"

az functionapp config appsettings set \
  --name devintaccountingftools \
  --resource-group devintaccountingftools \
  --settings "AzureWebJobsFeatureFlags=EnableWorkerIndexing"
```

**2. Fix the workflow file (apply all 3 critical fixes):**
```bash
cd /Users/voss/Library/CloudStorage/OneDrive-DevInt/code/devintaccountingftools
git pull  # Get the regenerated workflow

# Edit .github/workflows/main_devintaccountingftools.yml
# Apply these 3 fixes:
# Fix 1: Change: run: zip release.zip ./* -r
#        To:     run: zip release.zip ./* -r -x "venv/*"
#
# Fix 2: Add to deployment step: remote-build: true
#
# Fix 3: Add post-deployment step:
#        - name: 'Configure Python Runtime for Flex Consumption'
#          run: |
#            az functionapp update \
#              --name devintaccountingftools \
#              --resource-group devintaccountingftools \
#              --set "functionAppConfig.runtime.name=python" \
#                   "functionAppConfig.runtime.version=${{ env.PYTHON_VERSION }}"

git add .github/workflows/main_devintaccountingftools.yml
git commit -m "Fix: venv exclusion, remote-build, runtime config"
# Don't push yet - combine with deployment
```

**3. Verify runtime settings:**
```bash
az functionapp config appsettings list \
  --name devintaccountingftools \
  --resource-group devintaccountingftools \
  --query "[?name=='FUNCTIONS_WORKER_RUNTIME' || name=='FUNCTIONS_EXTENSION_VERSION' || name=='AzureWebJobsFeatureFlags'].{name:name, value:value}"

# Should show:
# - FUNCTIONS_WORKER_RUNTIME=python
# - FUNCTIONS_EXTENSION_VERSION=~4
# - AzureWebJobsFeatureFlags=EnableWorkerIndexing
```

---

#### Step 2.7: Deploy to New App

**Trigger deployment:**
```bash
cd /Users/voss/Library/CloudStorage/OneDrive-DevInt/code/devintaccountingftools

# Update Python version marker (if you have one)
echo "3.12" > .python-version

# Commit and push
git add .
git commit -m "Migrated to Flex Consumption with Python 3.12"
git push origin main
```

**Monitor:**
```
GitHub → Actions → Watch workflow for devintaccountingftools
```

---

#### Step 2.8: Verify Final Deployment

```bash
# Check runtime version
az functionapp show \
  --name devintaccountingftools \
  --resource-group devintaccountingftools \
  --query "functionAppConfig.runtime"

# Expected: {"name": "python", "version": "3.12"}

# List functions
az functionapp function list \
  --name devintaccountingftools \
  --resource-group devintaccountingftools
```

**Test all functionality:**
- [ ] All HTTP endpoints work
- [ ] Key Vault access works
- [ ] Storage operations work
- [ ] SendGrid emails send
- [ ] Teams webhooks work
- [ ] Excel processing works
- [ ] No errors in logs

**Monitor for 48-72 hours**

---

#### Step 2.9: Delete Temporary Flex App

⚠️ **Only after new app is confirmed stable!**

**Final Checklist:**
- [ ] New `devintaccountingftools` stable for 48-72 hours
- [ ] All tests pass
- [ ] No errors in Application Insights
- [ ] Users report no issues

**Delete:**
```bash
az functionapp delete \
  --name devintaccountingftools-flex \
  --resource-group devintaccountingftools
```

**Clean up Application Insights (optional):**
```bash
az monitor app-insights component delete \
  --app devintaccountingftools-flex \
  --resource-group devintaccountingftools
```

---

## Testing Checklist

### Pre-Migration Testing (Current App)

Document current behavior for comparison:

- [ ] Endpoint `/api/test` response time: _____ ms
- [ ] Cold start time: _____ seconds
- [ ] Average execution time: _____ ms
- [ ] Key Vault access: ✅ Working
- [ ] Storage operations: ✅ Working
- [ ] SendGrid emails: ✅ Working
- [ ] Teams webhooks: ✅ Working
- [ ] Excel processing: ✅ Working

### Post-Migration Testing (Flex App)

Compare with pre-migration baseline:

- [ ] Endpoint `/api/test` response time: _____ ms (should be equal or better)
- [ ] Cold start time: _____ seconds (should be faster)
- [ ] Average execution time: _____ ms
- [ ] Key Vault access: ✅ Working
- [ ] Storage operations: ✅ Working
- [ ] SendGrid emails: ✅ Working
- [ ] Teams webhooks: ✅ Working
- [ ] Excel processing: ✅ Working
- [ ] Python 3.12 compatibility: ✅ No issues

### Integration Testing

- [ ] **Key Vault:**
  ```bash
  # Test secret retrieval in function code
  # Verify managed identity has proper access policies
  ```

- [ ] **Storage Blob:**
  ```bash
  # Test file upload/download
  # Verify connection string or managed identity works
  ```

- [ ] **Storage Queue:**
  ```bash
  # Test queue message send/receive
  ```

- [ ] **Cosmos DB (if used):**
  ```bash
  # Test database queries
  # Verify connection
  ```

- [ ] **SendGrid:**
  ```bash
  # Send test email
  # Verify API key works
  ```

- [ ] **Microsoft Teams:**
  ```bash
  # Send test webhook
  # Verify webhook URL valid
  ```

### Performance Testing

```bash
# Run load test (if applicable)
# Monitor Application Insights during load
# Check for:
# - No timeouts
# - Acceptable response times
# - Proper scaling
```

---

## Rollback Plan

### If Issues in Phase 1 (Testing -flex app)

**Problem:** Flex app has issues, but original app still exists

**Action:**
1. Original `devintaccountingftools` continues running (unaffected)
2. Debug `-flex` app issues
3. Fix and redeploy
4. No downtime to production

### If Issues in Phase 2 (After deleting original)

**Problem:** New Flex app with original name has issues

**Mitigation:**
1. **Keep `-flex` app running until new app verified**
2. If new app fails, can temporarily use `-flex` app
3. Update clients to point to `-flex` URL if needed
4. Fix new app issues
5. Redeploy

**Prevention:**
- ✅ Do NOT delete `-flex` app until new app fully verified
- ✅ Test thoroughly in Phase 1
- ✅ Monitor closely in Phase 2

---

## Resources

### Official Documentation

**Migration:**
- [Migrate Linux Consumption to Flex](https://learn.microsoft.com/en-us/azure/azure-functions/migration/migrate-plan-consumption-to-flex?tabs=azure-cli%2Csystem-assigned%2Ccontinuous%2Ctraces-table&pivots=platform-linux)
- [Flex Consumption Plan](https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-plan)
- [Flex Consumption How-To](https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-how-to)

**Python:**
- [Python Developer Reference](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [Python 3.12 Support](https://learn.microsoft.com/en-us/azure/azure-functions/supported-languages)
- [Python 3.13+ Changes](https://learn.microsoft.com/en-us/azure/azure-functions/python-313-changes)

**GitHub Actions:**
- [GitHub Actions for Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-how-to-github-actions)
- [Azure Functions Action](https://github.com/Azure/functions-action)

**Azure CLI:**
- [az functionapp](https://learn.microsoft.com/en-us/cli/azure/functionapp)
- [az functionapp flex-migration](https://learn.microsoft.com/en-us/cli/azure/functionapp/flex-migration)

### Project Links

**GitHub:**
- Repository: https://github.com/devintev/devintaccountingftools
- Workflows: https://github.com/devintev/devintaccountingftools/actions

**Azure Portal:**
- [Function App (current)](https://portal.azure.com/#resource/subscriptions/854da132-9fce-4624-a0e9-7fa6ea46a6eb/resourceGroups/devintaccountingftools/providers/Microsoft.Web/sites/devintaccountingftools)
- [Resource Group](https://portal.azure.com/#resource/subscriptions/854da132-9fce-4624-a0e9-7fa6ea46a6eb/resourceGroups/devintaccountingftools)
- [Storage Account](https://portal.azure.com/#resource/subscriptions/854da132-9fce-4624-a0e9-7fa6ea46a6eb/resourceGroups/devintaccountingftools/providers/Microsoft.Storage/storageAccounts/devintaccountingftools)
- [Key Vault](https://portal.azure.com/#resource/subscriptions/854da132-9fce-4624-a0e9-7fa6ea46a6eb/resourceGroups/devintaccountingftools/providers/Microsoft.KeyVault/vaults/devintaccountingftkeys)

### Related Migrations

See also:
- `/systemcontrol/AZURE_FUNCTIONS_MIGRATIONS.md` - Overall migration plan
- `/hrmwebsitecasedb/MIGRATE.md` - Similar migration pattern

---

## Migration Log

| Date | Phase | Action | Result | Notes |
|------|-------|--------|--------|-------|
| 2025-10-08 | Planning | Created migration plan | ✅ Complete | Documented strategy |
| 2025-10-10 | 1.1 | Get storage account | ✅ Complete | Confirmed: devintaccountingftools |
| 2025-10-10 | 1.2 | Create -flex app | ✅ Complete | Created: devintaccountingftools-flex |
| 2025-10-10 | 1.2.5 | Verify runtime settings | ✅ Complete | Settings verified |
| 2025-10-10 | 1.2.6 | Configure Python v2 runtime | ✅ Complete | Python 3.11 + Worker Indexing enabled |
| 2025-10-10 | 1.3 | Configure Deployment Center | ✅ Complete | GitHub Actions configured |
| 2025-10-10 | 1.3.5 | Fix workflow file | ✅ Complete | Applied 3 critical fixes |
| 2025-10-10 | 1.3.6 | Disable old workflow | ✅ Complete | Kept for rollback |
| 2025-10-10 | 1.6 | First deployment | ✅ Complete | GitHub Actions successful |
| 2025-10-10 | 1.7 | Verify deployment | ✅ Complete | Functions loaded, permissions fixed |
| 2025-10-10 | 1.7.5 | Grant managed identity permissions | ✅ Complete | **CRITICAL FIX:** Blob Storage + Key Vault access |
| 2025-10-10 | 1.8 | Testing (48h) | ✅ Complete | All integrations verified, ready for Phase 2 |
| 2025-10-10 | **PHASE 1** | **Complete** | **✅ SUCCESS** | **Flex app fully operational** |
| 2025-10-10 | 2.3 | Delete original app | In Progress | Starting Phase 2 |
| TBD | 2.4 | Create new Flex app | Pending | |
| TBD | 2.5 | Configure settings | Pending | |
| TBD | 2.5.5 | Grant permissions | Pending | **Added based on Phase 1 learnings** |
| TBD | 2.6 | Configure Deployment Center | Pending | |
| TBD | 2.7 | Deploy to new app | Pending | |
| TBD | 2.8 | Verify (48-72h) | Pending | |
| TBD | 2.9 | Delete -flex app | Pending | |

---

## Notes

### Application Characteristics

**Type:** DevInt Accounting Tools
**Priority:** 🟢 Low
**Criticality:** Non-critical (can afford downtime for testing)
**Users:** Internal DevInt team

**Key Dependencies:**
- Excel file processing (financial reports)
- Email notifications (SendGrid)
- Microsoft Teams webhooks (notifications)
- Azure Key Vault (secrets)
- Azure Storage (file storage, queues)
- Cosmos DB (data storage)

**Usage Pattern:**
- Likely triggered on schedule or on-demand
- Not high-traffic
- Processing financial data
- Generating reports

### Python 3.12 Compatibility

All dependencies in `requirements.txt` are compatible with Python 3.12:
- ✅ `azure-functions` - Compatible
- ✅ `azure-identity` - Compatible
- ✅ `azure-*` libraries - All compatible
- ✅ `sendgrid` - Compatible
- ✅ `openpyxl` - Compatible
- ✅ `pandas` - Compatible (2.0+)
- ✅ `pymsteams` - Compatible
- ✅ `requests` - Compatible
- ✅ All other dependencies - Compatible

No known breaking changes expected.

### Timeline Estimate

| Phase | Task | Time | Monitoring |
|-------|------|------|------------|
| 1 | Create & configure -flex app | 1-1.5 hours | 48 hours |
| 2 | Migrate to original name | 1-1.5 hours | 48-72 hours |
| **Total** | **2-3 hours work** | | **4-5 days total** |

---

**Created:** 2025-10-08
**Last Updated:** 2025-10-08
**Created By:** Claude Code
**Status:** 📋 Ready for Migration
**Next Step:** Phase 1, Step 1.1 - Get Storage Account Name
