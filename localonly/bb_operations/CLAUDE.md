# Context Information for Claude

## Project Overview

This repository contains a modular tool to interact with the BuchhaltungsButler accounting system API. The system allows for fetching and backing up transaction, posting, and receipt data with resilient error handling.

## Project Structure

The project is organized with a modular, object-oriented approach:

1. `bookings_backup.py` - Main script that orchestrates the API handlers and services
2. `ApiHandler.py` - Base class for all API handlers with common functionality
3. `TransactionsHandler.py` - Handler for transactions API endpoints
4. `PostingsHandler.py` - Handler for postings API endpoints
5. `ReceiptsHandler.py` - Handler for receipts API endpoints with advanced error handling
6. `BackupService.py` - Service to create backups using the API handlers
7. `DisplayService.py` - Service to display data using the Rich library
8. `BB_README.md` - Documentation for the BuchhaltungsButler API integration
9. `config.json` - Configuration file that includes settings like backup period

## Key Components

### ApiHandler Base Class

The base class that all specific handlers inherit from:
- Manages API credentials and authentication
- Provides common HTTP request functionality
- Implements basic error handling
- Centralizes URL configuration

### Specialized Handlers

Each endpoint has a dedicated handler class:

#### TransactionsHandler
- Handles the `/transactions/get` endpoint
- Provides methods for date-range and latest transactions
- Creates formatted tables for display

#### PostingsHandler
- Handles the `/postings/get` endpoint
- Provides methods for date-range and latest postings
- Creates formatted tables for display

#### ReceiptsHandler
- Handles the `/receipts/get` endpoint
- Implements advanced error handling with multiple retry attempts
- Provides client-side date filtering when API filtering fails
- Handles both inbound and outbound receipts
- Creates formatted tables for display

### Service Classes

#### BackupService
- Coordinates backup operations across all handlers
- Creates structured backup files with metadata
- Maintains backup operation even when some API components fail
- Provides detailed status and reporting

#### DisplayService
- Formats and displays data using the Rich library
- Creates tables and JSON views
- Implements error handling for display operations

## API Authentication

- Uses HTTP Basic Auth with the format `<Api Client>:<Api Secret>`
- Requires an API Key parameter for each request
- Uses the API version 1.8.1
- Base URL: https://app.buchhaltungsbutler.de/api/v1

Environment file structure (located at `~/.auth/devint-tools.env`):
```
Buchhaltungsbutler_API_KEY=your_api_key
Buchhaltungsbutler_API_SECRET=your_api_secret
Buchhaltungsbutler_API_CLIENT=your_api_client
```

Configuration options (located in `config.json`):
```json
{
    "days_backup": 30,
    "debug_mode": false,
    "receipts_enhanced_logging": false,
    "backup_include": {
        "transactions": true,
        "postings": true,
        "receipts": true
    },
    "printout_include": {
        "transactions": true,
        "postings": true,
        "receipts": true
    }
}
```

- `days_backup`: Number of days to include in the backup
- `debug_mode`: Enable debug output
- `receipts_enhanced_logging`: Enable detailed logging for receipts API
- `backup_include`: Control which data types are included in the backup
- `printout_include`: Control which data types are displayed in the console output

## Requirements

The script requires these Python packages:
- `requests` - For making HTTP requests to the API
- `python-dotenv` - For loading environment variables from `.env` files
- `rich` - For displaying formatted tables and colored output

## Running the Script

To run the script:
```bash
python bookings_backup.py
```

The script will:
1. Load API credentials and configuration
2. Create a backup of your accounting data for the configured time period
3. Display sample data from each endpoint (transactions, postings, receipts)

## Important Notes

1. The receipts API is particularly prone to 500 errors, which requires special handling
2. Client-side date filtering is used when API date filtering fails
3. Backups include detailed API status information in the metadata
4. The script will create backups even when some API components fail
5. The API has rate limits, so be careful with the number of requests
6. Keep the API credentials secure and never commit them to the repository
7. The maximum limit for transactions and receipts is 500, while for postings it is 1000
8. When making changes to the script, maintain the modular structure
9. The config.json file allows configuring how many days of data to back up, debug mode, and enhanced logging

## Known Issues and Fixes

1. **Receipts Display Issue**: 
   - Problem: The receipts display was showing the first/oldest receipts instead of the most recent ones
   - Fix: Enhanced the `get_latest` method to request more receipts than needed, sort them by date in descending order, and then take only the requested limit

2. **Empty Inbound Receipts in Backup**:
   - Problem: Recent backups might show zero inbound receipts even when the API returns data
   - Cause: The inbound receipts returned by the API are sometimes very old (e.g., from 2022), so when filtering by recent dates (e.g., last 30 days), no receipts match the criteria
   - Fix: Added diagnostics to verify this is not an API failure but expected behavior based on the data available
   - Note: The backup file's metadata now includes receipt type counts and diagnostics information

3. **API Sorting Unreliability**:
   - Problem: The API's `order` parameter doesn't consistently sort data as expected
   - Fix: Implemented client-side sorting to ensure reliable sorting of data by date

4. **Receipts API Error Handling**:
   - Problem: The receipts API frequently returns 500 errors when using date filters
   - Fix: Added tiered fallback approach that progressively simplifies requests until successful

## Error Handling Approaches

The system uses several advanced error handling techniques:
1. Multiple retry attempts with different strategies
2. Progressive fallback to simpler requests
3. Client-side filtering when server-side filtering fails
4. Detailed error reporting and logging
5. Graceful degradation (continuing with partial data)
6. Structured error responses with consistent format

## Backup Structure

Backups are saved as JSON files with the following structure:

```json
{
  "metadata": {
    "backup_date": "2023-01-15 14:30:45",
    "date_range": {
      "from": "2023-01-05",
      "to": "2023-01-15"
    },
    "days_backup": 10,
    "notes": "Some data may be missing if API endpoints were unavailable",
    "api_status": {
      "transactions": {"success": true, "count": 25},
      "postings": {"success": true, "count": 30},
      "receipts_inbound": {"success": true, "count": 15},
      "receipts_outbound": {"success": true, "count": 5}
    }
  },
  "transactions": [...],
  "postings": [...],
  "receipts": {
    "inbound": [...],
    "outbound": [...]
  }
}
```