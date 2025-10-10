#!/usr/bin/env python3
from dotenv import dotenv_values
import os
import json
from datetime import datetime, timedelta
from rich.console import Console
from rich.rule import Rule

# Import our service handlers
from TransactionsHandler import TransactionsHandler
from PostingsHandler import PostingsHandler
from ReceiptsHandler import ReceiptsHandler
from BackupService import BackupService
from DisplayService import DisplayService

def load_api_credentials():
    """Load API credentials from the environment file"""
    # Subfolder of home directory
    env_file_path = os.path.join(
        os.path.expanduser('~'), '.auth', 'devint-tools.env')
    print(f"Looking for env file at: {env_file_path}")

    BB_API_KEY_VAR = 'Buchhaltungsbutler_API_KEY'
    BB_API_SECRET_VAR = 'Buchhaltungsbutler_API_SECRET'
    BB_API_CLIENT_VAR = 'Buchhaltungsbutler_API_CLIENT'

    # Load values from env file without setting environment variables
    env_values = dotenv_values(env_file_path)

    # Get API credentials from env file
    bb_api_key = env_values.get(BB_API_KEY_VAR)
    bb_api_secret = env_values.get(BB_API_SECRET_VAR)
    bb_api_client = env_values.get(BB_API_CLIENT_VAR)

    print(f"API Key loaded: {'Yes' if bb_api_key else 'No'}")
    print(f"API Secret loaded: {'Yes' if bb_api_secret else 'No'}")
    print(f"API Client loaded: {'Yes' if bb_api_client else 'No'}")
    
    return bb_api_key, bb_api_secret, bb_api_client

def load_config():
    """Load configuration from config.json file"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config file: {e}")
        # Default configuration
        return {
            "days_backup": 10,
            "debug_mode": False,
            "receipts_enhanced_logging": False,
            "backup_include": {
                "transactions": True,
                "postings": True,
                "receipts": True
            },
            "printout_include": {
                "transactions": True,
                "postings": True,
                "receipts": True
            }
        }

def main():
    """Main function to run the BuchhaltungsButler API client"""
    # Initialize Rich console
    console = Console()
    console.rule("[bold blue]BuchhaltungsButler API Client[/]")
    
    # Load configuration
    config = load_config()
    days_backup = config.get('days_backup', 10)
    debug_mode = config.get('debug_mode', False)
    receipts_enhanced_logging = config.get('receipts_enhanced_logging', False)
    backup_include = config.get('backup_include', {"transactions": True, "postings": True, "receipts": True})
    printout_include = config.get('printout_include', {"transactions": True, "postings": True, "receipts": True})
    
    if debug_mode:
        console.print("[bold yellow]Debug mode enabled[/]")
    
    # Load API credentials
    api_key, api_secret, api_client = load_api_credentials()
    if not all([api_key, api_secret, api_client]):
        console.print("[bold red]Error: Missing API credentials. Please check your environment file.[/]")
        return
    
    # Initialize handlers
    transactions_handler = TransactionsHandler(api_key, api_secret, api_client)
    postings_handler = PostingsHandler(api_key, api_secret, api_client)
    
    # Initialize receipts handler with debug info
    receipts_handler = ReceiptsHandler(api_key, api_secret, api_client)
    receipts_handler.debug_mode = debug_mode
    receipts_handler.enhanced_logging = receipts_enhanced_logging
    
    if debug_mode:
        console.print(f"Configured handlers with debug_mode={debug_mode}")
    
    # Initialize services
    backup_service = BackupService(transactions_handler, postings_handler, receipts_handler, console)
    display_service = DisplayService(console, printout_include)
    
    # Display configuration
    console.print(f"[cyan]Configuration:[/]")
    console.print(f"Days to backup: [bold cyan]{days_backup}[/]")
    console.print(f"Debug mode: [bold {'green' if debug_mode else 'red'}]{debug_mode}[/]")
    console.print(f"Receipts enhanced logging: [bold {'green' if receipts_enhanced_logging else 'red'}]{receipts_enhanced_logging}[/]")
    
    # Display what will be backed up and displayed
    console.print(f"[cyan]Backup include:[/]")
    for item, enabled in backup_include.items():
        console.print(f"{item}: [bold {'green' if enabled else 'red'}]{enabled}[/]")
    
    console.print(f"[cyan]Printout include:[/]")
    for item, enabled in printout_include.items():
        console.print(f"{item}: [bold {'green' if enabled else 'red'}]{enabled}[/]")
    
    # Run backup
    console.rule("[bold blue]DATA BACKUP[/]")
    backup_path = backup_service.create_backup(days_backup, backup_include)
    
    # Display data
    console.rule("[bold blue]DATA DISPLAY[/]")
    display_service.display_transactions(transactions_handler)
    display_service.display_postings(postings_handler)
    display_service.display_receipts(receipts_handler)

if __name__ == "__main__":
    main()