#!/usr/bin/env python3
import json
import os
import pathlib
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel

class BackupService:
    """Service to backup BuchhaltungsButler data"""
    
    def __init__(self, transactions_handler, postings_handler, receipts_handler, console=None):
        """
        Initialize with API handlers and console
        
        Args:
            transactions_handler: Handler for transactions API
            postings_handler: Handler for postings API
            receipts_handler: Handler for receipts API
            console (optional): Rich console for output
        """
        self.transactions_handler = transactions_handler
        self.postings_handler = postings_handler
        self.receipts_handler = receipts_handler
        self.console = console or Console()
        
    def create_backup(self, days_backup=10, backup_include=None):
        """
        Backup data from BuchhaltungsButler for the specified number of days.
        
        Args:
            days_backup (int): Number of days to backup (default: 10)
            backup_include (dict): Dictionary specifying which data types to include in the backup
                                 (default: {"transactions": True, "postings": True, "receipts": True})
            
        Returns:
            str: Path to the created backup file
        """
        # Set default backup_include if not provided
        if backup_include is None:
            backup_include = {"transactions": True, "postings": True, "receipts": True}
        
        today = datetime.now()
        date_to = today.strftime('%Y-%m-%d')
        date_from = (today - timedelta(days=days_backup)).strftime('%Y-%m-%d')
        
        self.console.print(f"\n[bold cyan]Backing up data from {date_from} to {date_to} ({days_backup} days)[/]")
        
        # Prepare the backup status object to track API success/failure
        backup_status = {
            "transactions": {"success": False, "message": "Not attempted"},
            "postings": {"success": False, "message": "Not attempted"},
            "receipts_inbound": {"success": False, "message": "Not attempted"},
            "receipts_outbound": {"success": False, "message": "Not attempted"}
        }
        
        # Initialize with empty data
        transactions = {'success': False, 'data': []}
        postings = {'success': False, 'data': []}
        inbound_receipts = {'success': False, 'data': []}
        outbound_receipts = {'success': False, 'data': []}
        
        # Get transactions if enabled
        if backup_include.get('transactions', True):
            self.console.print("[bold cyan]Fetching transactions...[/]")
            transactions = self.transactions_handler.get_by_date_range(date_from, date_to)
            if transactions and transactions.get('success'):
                backup_status["transactions"] = {"success": True, "count": len(transactions.get('data', []))}
                self.console.print(f"[green]Successfully retrieved {len(transactions.get('data', []))} transactions[/]")
            else:
                backup_status["transactions"] = {"success": False, "message": "Failed to retrieve transactions"}
                self.console.print("[bold red]Failed to retrieve transactions - continuing with empty transactions data[/]")
                transactions = {'success': False, 'data': []}
        else:
            backup_status["transactions"] = {"success": False, "message": "Transactions backup disabled"}
            self.console.print("[cyan]Transactions backup disabled - skipping[/]")
        
        # Get postings if enabled
        if backup_include.get('postings', True):
            self.console.print("[bold cyan]Fetching postings...[/]")
            postings = self.postings_handler.get_by_date_range(date_from, date_to)
            if postings and postings.get('success'):
                backup_status["postings"] = {"success": True, "count": len(postings.get('data', []))}
                self.console.print(f"[green]Successfully retrieved {len(postings.get('data', []))} postings[/]")
            else:
                backup_status["postings"] = {"success": False, "message": "Failed to retrieve postings"}
                self.console.print("[bold red]Failed to retrieve postings - continuing with empty postings data[/]")
                postings = {'success': False, 'data': []}
        else:
            backup_status["postings"] = {"success": False, "message": "Postings backup disabled"}
            self.console.print("[cyan]Postings backup disabled - skipping[/]")
        
        # Get receipts if enabled
        if backup_include.get('receipts', True):
            # Get inbound receipts with enhanced error handling
            self.console.print("[bold cyan]Fetching inbound receipts...[/]")
            inbound_receipts = self.receipts_handler.get_by_date_range(date_from, date_to, limit=500, list_direction='inbound')
            
            # Check if we got valid data with our enhanced functions (they now always return a structured response)
            if inbound_receipts and inbound_receipts.get('success'):
                backup_status["receipts_inbound"] = {"success": True, "count": len(inbound_receipts.get('data', []))}
                self.console.print(f"[green]Successfully retrieved {len(inbound_receipts.get('data', []))} inbound receipts[/]")
                
                # Store receipt counts by type for diagnostics
                if inbound_receipts.get('data'):
                    # Count receipts by type
                    inbound_types = {}
                    for receipt in inbound_receipts.get('data', []):
                        receipt_type = receipt.get('type', 'unknown')
                        if receipt_type in inbound_types:
                            inbound_types[receipt_type] += 1
                        else:
                            inbound_types[receipt_type] = 1
                    
                    if inbound_types:
                        backup_status["receipts_inbound"]["types"] = inbound_types
                        self.console.print(f"[green]Inbound receipt types: {inbound_types}[/]")
                
                # Note if client-side filtering was applied
                if inbound_receipts.get('client_filtered'):
                    self.console.print("[yellow]Note: Client-side date filtering was applied to inbound receipts[/]")
                    backup_status["receipts_inbound"]["note"] = "Client-side date filtering was applied"
                    
                # If we have zero receipts, make additional diagnostics
                if len(inbound_receipts.get('data', [])) == 0:
                    self.console.print("[bold yellow]WARNING: Retrieved 0 inbound receipts. Attempting unfiltered fetch for diagnostics.[/]")
                    
                    # Make an additional diagnostics call
                    try:
                        diagnostics_receipts = self.receipts_handler.get_latest(limit=10, list_direction='inbound')
                        if diagnostics_receipts and diagnostics_receipts.get('success') and diagnostics_receipts.get('data'):
                            self.console.print(f"[green]Found {len(diagnostics_receipts.get('data', []))} inbound receipts in diagnostics fetch.[/]")
                            backup_status["receipts_inbound"]["diagnostics"] = True
                            backup_status["receipts_inbound"]["diagnostics_count"] = len(diagnostics_receipts.get('data', []))
                        else:
                            self.console.print("[yellow]Diagnostics fetch also found no inbound receipts.[/]")
                    except Exception as e:
                        self.console.print(f"[yellow]Error in diagnostics fetch: {e}[/]")
            else:
                backup_status["receipts_inbound"] = {
                    "success": False, 
                    "message": inbound_receipts.get('message', "Failed to retrieve inbound receipts")
                }
                self.console.print("[bold red]Unable to fetch inbound receipts - continuing with empty inbound receipts data[/]")
            
            # Get outbound receipts with enhanced error handling
            self.console.print("[bold cyan]Fetching outbound receipts...[/]")
            outbound_receipts = self.receipts_handler.get_by_date_range(date_from, date_to, limit=500, list_direction='outbound')
            
            # Check if we got valid data
            if outbound_receipts and outbound_receipts.get('success'):
                backup_status["receipts_outbound"] = {"success": True, "count": len(outbound_receipts.get('data', []))}
                self.console.print(f"[green]Successfully retrieved {len(outbound_receipts.get('data', []))} outbound receipts[/]")
                
                # Store receipt counts by type for diagnostics
                if outbound_receipts.get('data'):
                    # Count receipts by type
                    outbound_types = {}
                    for receipt in outbound_receipts.get('data', []):
                        receipt_type = receipt.get('type', 'unknown')
                        if receipt_type in outbound_types:
                            outbound_types[receipt_type] += 1
                        else:
                            outbound_types[receipt_type] = 1
                    
                    if outbound_types:
                        backup_status["receipts_outbound"]["types"] = outbound_types
                        self.console.print(f"[green]Outbound receipt types: {outbound_types}[/]")
                
                # Note if client-side filtering was applied
                if outbound_receipts.get('client_filtered'):
                    self.console.print("[yellow]Note: Client-side date filtering was applied to outbound receipts[/]")
                    backup_status["receipts_outbound"]["note"] = "Client-side date filtering was applied"
            else:
                backup_status["receipts_outbound"] = {
                    "success": False, 
                    "message": outbound_receipts.get('message', "Failed to retrieve outbound receipts")
                }
                self.console.print("[bold red]Unable to fetch outbound receipts - continuing with empty outbound receipts data[/]")
        else:
            backup_status["receipts_inbound"] = {"success": False, "message": "Receipts backup disabled"}
            backup_status["receipts_outbound"] = {"success": False, "message": "Receipts backup disabled"}
            self.console.print("[cyan]Receipts backup disabled - skipping[/]")
        
        # Prepare receipts data
        receipts_data = {
            "inbound": inbound_receipts.get('data', []) if inbound_receipts and inbound_receipts.get('success') else [],
            "outbound": outbound_receipts.get('data', []) if outbound_receipts and outbound_receipts.get('success') else []
        }
        
        # Create backup data object with enhanced metadata
        backup_data = {
            "metadata": {
                "backup_date": today.strftime('%Y-%m-%d %H:%M:%S'),
                "date_range": {
                    "from": date_from,
                    "to": date_to
                },
                "days_backup": days_backup,
                "backup_include": backup_include,
                "notes": "Some data may be missing if API endpoints were unavailable",
                "api_status": backup_status
            },
            "transactions": transactions.get('data', []) if transactions and transactions.get('success') else [],
            "postings": postings.get('data', []) if postings and postings.get('success') else [],
            "receipts": receipts_data
        }
        
        # Create backups directory if it doesn't exist
        backups_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        pathlib.Path(backups_dir).mkdir(parents=True, exist_ok=True)
        
        # Create backup filename with date and time
        timestamp = today.strftime('%Y-%m-%d_%H-%M-%S')
        backup_filename = f"bb_backup_{timestamp}_{days_backup}days.json"
        backup_path = os.path.join(backups_dir, backup_filename)
        
        # Write backup data to file
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        self.console.print(f"[bold green]Backup saved to: {backup_path}[/]")
        
        # Summary of backed up data with status indicators
        self.console.print("\n[bold cyan]Backup Summary:[/]")
        
        transaction_status = "[bold green]✓[/]" if backup_status["transactions"].get("success") else "[bold red]✗[/]"
        posting_status = "[bold green]✓[/]" if backup_status["postings"].get("success") else "[bold red]✗[/]"
        inbound_status = "[bold green]✓[/]" if backup_status["receipts_inbound"].get("success") else "[bold red]✗[/]"
        outbound_status = "[bold green]✓[/]" if backup_status["receipts_outbound"].get("success") else "[bold red]✗[/]"
        
        self.console.print(f"Transactions: {transaction_status} [bold green]{len(backup_data['transactions'])}[/]")
        self.console.print(f"Postings: {posting_status} [bold green]{len(backup_data['postings'])}[/]")
        self.console.print(f"Inbound Receipts: {inbound_status} [bold green]{len(backup_data['receipts']['inbound'])}[/]")
        self.console.print(f"Outbound Receipts: {outbound_status} [bold green]{len(backup_data['receipts']['outbound'])}[/]")
        
        # Overall backup status
        if all(status.get("success") for status in backup_status.values()):
            self.console.print("\n[bold green]Backup completed successfully with all data![/]")
        else:
            self.console.print("\n[bold yellow]Backup completed with some missing data.[/]")
            # List missing data
            missing = [k for k, v in backup_status.items() if not v.get("success")]
            if missing:
                self.console.print(f"[yellow]Missing data: {', '.join(missing)}[/]")
        
        return backup_path