# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**devintaccountingftools** is an Azure Functions Python application that automates financial reporting for DevInt. It fetches accounting data from Buchhaltungsbuttler (German bookkeeping service), processes it, generates Excel-based financial reports, and distributes them via email and Microsoft Teams.

**Key Purpose:** Automated financial report generation and distribution based on accounting data from external bookkeeping system.

## Architecture

### Application Type
- **Platform:** Azure Functions (Python v2 model)
- **Runtime:** Python 3.11 (migrating to 3.12 - see MIGRATE.md)
- **Hosting:** Linux Consumption Plan (migrating to Flex Consumption)
- **Entry Point:** [function_app.py](function_app.py) with HTTP-triggered functions

### Core Components

1. **HTTP Functions** ([function_app.py](function_app.py))
   - `/api/test` - Test endpoint with full report generation workflow
   - `/api/reportrequest` - Report generation triggered by HTTP request with selectors

2. **Main Library** ([hrmlib/hrmtools.py](hrmlib/hrmtools.py)) - ~3,500 lines
   - `DevIntConnector` - Central orchestrator class for all accounting operations
   - `SecretsAndSettingsManager` - Azure Key Vault integration for secrets
   - `HTMLListHandler` - Custom logging handler for HTML-formatted logs
   - `BytesIOWrapper` - Helper for Excel file streaming

3. **Configuration** ([hrmlib/devint_settings.yaml](hrmlib/devint_settings.yaml))
   - Chart of accounts (SKR49 German accounting standard)
   - Cost location mappings
   - Azure resource names (Blob Storage containers, Cosmos DB)
   - Secret names for Key Vault access

### Data Flow

```
HTTP Request (with selectors)
    ↓
SecretsAndSettingsManager (loads secrets from Key Vault)
    ↓
DevIntConnector.setup() (builds Azure clients)
    ↓
read_instruction_files() (loads templates from Blob Storage)
    ↓
get_all_bb_posts() (fetches bookings from Buchhaltungsbuttler API)
    ↓
get_all_bb_accounts() (fetches account master data)
    ↓
read_expected_bookings() (loads expected bookings from Blob Storage)
    ↓
build_reports() (generates Excel workbooks with openpyxl)
    ↓
send_reports() (distributes via SendGrid email & MS Teams webhooks)
    ↓
HTML Response (with logs and status)
```

### External Dependencies

**APIs:**
- **Buchhaltungsbuttler** - External bookkeeping service API (posts/accounts endpoints)
- **SendGrid** - Email delivery
- **MS Teams Webhooks** - Notification delivery (via pymsteams)

**Azure Services:**
- **Key Vault** (`devintaccountingftkeys`) - Secret storage
- **Blob Storage** (`devintaccountingftools`) - Template and report storage
  - Containers: `templates`, `financialplanning`, `financialreports`, `workingtimereports`, `wccinvoicing`, `odinvoicing`
- **Cosmos DB** (`devintaccountingdb`) - Working hours data
- **Application Insights** - Telemetry and logging

## Development Commands

### Local Development

**Setup:**
```bash
# Create and activate virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
```

**Run locally:**
```bash
# Requires local.settings.json with Azure connection strings
func start
```

**Test endpoints:**
```bash
# Test function (example with selectors)
curl "http://localhost:7071/api/test?coordination=1&norman=1"

# Report request
curl "http://localhost:7071/api/reportrequest?devtest=1"
```

### Testing

No automated test suite currently exists. Manual testing via HTTP requests with different selector combinations.

**Available selectors** (query parameters):
- `coordination=1` - Coordination reports
- `norman=1` - Norman-specific reports
- `devtest=1` - Development/test reports
- `administration=1` - Administration reports
- `documentation=1` - Documentation reports
- `erapurnamasari=1` - Erapurnamasari-specific reports

### Deployment

**Automated deployment via GitHub Actions:**
- Workflow: [.github/workflows/main_devintaccountingftools.yml](.github/workflows/main_devintaccountingftools.yml)
- Trigger: Push to `main` branch or manual dispatch
- Process: Build → Zip → Deploy to Azure Functions using publish profile

**Manual deployment:**
```bash
func azure functionapp publish devintaccountingftools
```

## Key Implementation Details

### Report Generation Process

1. **Data Collection:**
   - `get_all_bb_posts()` - Paginated API calls to fetch bookings (date range: 2021-01-01 to 2039-12-31)
   - `get_all_bb_accounts()` - Fetch chart of accounts with SKR49 account numbers
   - `read_expected_bookings()` - Load expected/planned bookings from Blob Storage Excel files
   - `read_instruction_files()` - Load time slots, chart of accounts mappings, report schemas, distribution lists

2. **Report Building:**
   - `build_reports()` - Core method that generates Excel workbooks
   - Uses openpyxl to create multi-sheet workbooks
   - Methods like `fill_bookings_to_sheet()`, `fill_listings_sheet()`, `fill_personnel_bookings_to_sheet()`
   - Complex Excel formula generation via `build_group_summation_formula()`
   - Styling with fonts, fills, borders defined in settings

3. **Distribution:**
   - `send_reports()` - Filters recipients by selector conditions
   - SendGrid for email attachments
   - MS Teams webhooks for notifications
   - Uploads reports to Blob Storage (`financialreports` container)

### Secrets Management

All secrets stored in Azure Key Vault (`devintaccountingftkeys`):
- `bb-api-key` - Buchhaltungsbuttler API key
- `bb-authorization` - Buchhaltungsbuttler auth header
- `bb-cookie` - Buchhaltungsbuttler session cookie
- `sendgrid-api-key` - SendGrid API key
- `devintaccounting-cosmos-db-key` - Cosmos DB access key
- `teams-webhook-keegan` - MS Teams webhook URL
- `reportrequest-backlink` - Backlink URL for reports

Access via `SecretsAndSettingsManager` using Azure Managed Identity (system-assigned).

### HTML Response Generation

Functions return HTML pages, not JSON:
- Templates in [assets/](assets/) directory (`main.template.html`, `styles.css`, `includes.js`)
- Custom logging via `HTMLListHandler` generates HTML-formatted logs
- Template placeholders replaced via `replace_and_format_html_template()`

### Excel Column Management

Helper method `_colchar()` converts column numbers to Excel letters (A, B, ... Z, AA, AB, ...).

## Common Tasks

### Adding a New Report Type

1. Update [hrmlib/devint_settings.yaml](hrmlib/devint_settings.yaml) with new report schema
2. Add corresponding template to Blob Storage (`templates` container)
3. Update distribution list in instruction files
4. Add selector logic in [function_app.py](function_app.py) if needed
5. Test with appropriate query parameters

### Modifying Chart of Accounts

Edit account mappings in [hrmlib/devint_settings.yaml](hrmlib/devint_settings.yaml):
- `skr49_payroll_clearing_accounts` - Clearing accounts
- `skr49_payroll_liabilities_accounts` - Liability accounts
- `skr49_personnel_expenses_non_profit` - Expense accounts
- `skr49_personnel_expenses_vat_exempt_purpose` - VAT-exempt expenses

### Debugging Report Generation

1. Check Application Insights logs in Azure Portal
2. Use HTML log output in function response (includes debug-level logs)
3. Verify Blob Storage access and template availability
4. Check Buchhaltungsbuttler API connectivity
5. Validate selector conditions in HTTP request

### Migration to Flex Consumption

See [MIGRATE.md](MIGRATE.md) for detailed migration plan including:
- Python 3.11 → 3.12 upgrade
- Linux Consumption → Flex Consumption hosting plan
- GitHub Actions workflow updates (critical fixes for venv exclusion, remote-build)
- Runtime configuration requirements for Python v2 model

## Important Notes

- **Large codebase:** [hrmlib/hrmtools.py](hrmlib/hrmtools.py) is 3,490 lines - use grep/search for specific methods
- **German accounting:** Uses SKR49 chart of accounts standard
- **No automated tests:** All testing is manual via HTTP requests
- **Dependency graph:** Top of [hrmlib/hrmtools.py](hrmlib/hrmtools.py) contains detailed dependency map
- **Local files excluded:** `localonly/` directory contains local Excel files and notebooks, excluded from git
- **Logging is verbose:** Debug-level logging throughout for troubleshooting complex report generation

## Project Structure

```
devintaccountingftools/
├── function_app.py              # Azure Functions entry point (HTTP triggers)
├── requirements.txt             # Python dependencies
├── host.json                    # Functions host configuration
├── local.settings.json          # Local development settings (gitignored)
├── MIGRATE.md                   # Azure Functions migration plan (3.11→3.12, Consumption→Flex)
├── hrmlib/                      # Main library code
│   ├── hrmtools.py             # Core logic (~3,500 lines)
│   └── devint_settings.yaml    # Configuration (accounts, containers, secrets)
├── assets/                      # HTML templates and CSS
│   ├── main.template.html
│   ├── styles.css
│   └── includes.js
├── .github/workflows/           # CI/CD
│   └── main_devintaccountingftools.yml
└── localonly/                   # Local files (Excel, notebooks) - gitignored
```
