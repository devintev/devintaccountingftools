# BuchhaltungsButler API Integration

This project contains tools for interacting with the BuchhaltungsButler accounting API. It allows for fetching transaction, posting, and receipt data, displaying it in a formatted way, and creating backups of the data.

## Getting Started

The script requires the following:

1. Python 3.6 or later
2. Required libraries: `requests`, `python-dotenv`, `rich`
3. API credentials stored in `~/.auth/devint-tools.env` file:
   ```
   Buchhaltungsbutler_API_KEY=your_api_key
   Buchhaltungsbutler_API_SECRET=your_api_secret
   Buchhaltungsbutler_API_CLIENT=your_api_client
   ```

## Running the Script

```
python bookings_backup.py
```

## Features

- Fetches and displays the latest transactions, postings, and receipts
- Creates date-range based backups of all data
- Resilient error handling, especially for the receipts API which can be unstable
- Rich console output with tables and formatted JSON

## Code Structure

This codebase follows a modular, object-oriented approach:

- `ApiHandler.py` - Base class for all API handlers
- `TransactionsHandler.py` - Handler for transactions API
- `PostingsHandler.py` - Handler for postings API
- `ReceiptsHandler.py` - Handler for receipts API with enhanced error handling
- `BackupService.py` - Service for creating backups
- `DisplayService.py` - Service for displaying data
- `bookings_backup.py` - Main script that orchestrates the handlers and services
- `config.json` - Configuration file for backup parameters

## Configuration Options

Edit `config.json` to customize the behavior:
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

- `days_backup`: Number of days to include in the backup (default: 30)
- `debug_mode`: Enable debug output (default: false)
- `receipts_enhanced_logging`: Enable detailed logging for receipts API (default: false)
- `backup_include`: Control which data types are included in the backup
  - `transactions`: Whether to include transactions in the backup (default: true)
  - `postings`: Whether to include postings in the backup (default: true)
  - `receipts`: Whether to include receipts in the backup (default: true)
- `printout_include`: Control which data types are displayed in the console output
  - `transactions`: Whether to display transactions in the console (default: true)
  - `postings`: Whether to display postings in the console (default: true)
  - `receipts`: Whether to display receipts in the console (default: true)

## Known Issues and Workarounds

1. **BuchhaltungsButler Receipts API Instability**: 
   - The receipts API sometimes returns 500 errors when using date filters
   - Solution: The code implements a progressive fallback mechanism:
     1. First tries with date filters
     2. If that fails, fetches without date filters and applies client-side filtering
     3. As a last resort, tries with minimal parameters to at least get some data
   
2. **Data Sorting Issues**:
   - API sometimes doesn't correctly sort receipts by date, despite the order parameter
   - Solution: Client-side sorting is applied to ensure most recent data is displayed

3. **Empty Inbound Receipts**:
   - When creating backups for recent date ranges, inbound receipts might be empty
   - Cause: This is often legitimate as there might be no inbound receipts in that period
   - Diagnostics: The backup includes additional metadata to help diagnose this situation

## API Endpoints

### Transactions (`/transactions/get`)
- Retrieves bank transactions
- Max limit: 500

### Postings (`/postings/get`)
- Retrieves accounting postings
- Max limit: 1000

### Receipts (`/receipts/get`)
- Retrieves receipts (invoices, etc.)
- Max limit: 500
- Parameters include `list_direction` which can be 'inbound' or 'outbound'

## Error Handling

The code implements robust error handling:
- Multiple retry attempts with different strategies
- Client-side filtering when server-side filtering fails
- Graceful degradation when APIs are partially unavailable
- Detailed error information in logs and console output