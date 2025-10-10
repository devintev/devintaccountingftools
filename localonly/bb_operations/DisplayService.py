#!/usr/bin/env python3
import json
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON
from rich.table import Table

class DisplayService:
    """Service to display BuchhaltungsButler data in rich format"""
    
    def __init__(self, console=None, printout_include=None):
        """
        Initialize with Rich console
        
        Args:
            console (optional): Rich console for output
            printout_include (dict, optional): Dictionary specifying which data types to display
                                             (default: {"transactions": True, "postings": True, "receipts": True})
        """
        self.console = console or Console()
        self.printout_include = printout_include or {"transactions": True, "postings": True, "receipts": True}
    
    def display_json(self, data, title):
        """
        Display raw JSON data in a panel
        
        Args:
            data: Data to display as JSON
            title: Title for the panel
        """
        json_str = json.dumps(data, indent=2)
        self.console.print(Panel(JSON(json_str), title=title))
    
    def display_transactions(self, transactions_handler):
        """
        Display transactions data
        
        Args:
            transactions_handler: Handler for transactions API
        """
        # Skip if transactions display is disabled
        if not self.printout_include.get('transactions', True):
            self.console.print("[cyan]Transactions display disabled - skipping[/]")
            return
            
        self.console.rule("[bold blue]TRANSACTIONS[/]")
        self.console.print("\n[bold cyan]Fetching the latest 5 transactions...[/]")
        transactions = transactions_handler.get_latest()
        
        if transactions and transactions.get('success'):
            # Print the number of transactions retrieved
            self.console.print(f"Retrieved [bold green]{transactions.get('rows', len(transactions.get('data', [])))}[/] transactions")
            
            # Display transactions in a table
            if transactions['data']:
                self.console.print(transactions_handler.create_table(transactions['data']))
                
                # Show raw JSON for first transaction
                self.console.print("\nShowing raw transaction data:")
                self.display_json(transactions['data'][0], "Sample Transaction (Raw JSON)")
            else:
                self.console.print("[yellow]No transaction data available[/]")
        else:
            self.console.print("[bold red]Failed to retrieve transactions[/]")
            error_message = transactions.get('message', 'Unknown error') if transactions else 'Unknown error'
            self.console.print(f"[yellow]Error: {error_message}[/]")
    
    def display_postings(self, postings_handler):
        """
        Display postings data
        
        Args:
            postings_handler: Handler for postings API
        """
        # Skip if postings display is disabled
        if not self.printout_include.get('postings', True):
            self.console.print("[cyan]Postings display disabled - skipping[/]")
            return
            
        self.console.rule("[bold blue]POSTINGS[/]")
        self.console.print("\n[bold cyan]Fetching the latest 5 postings...[/]")
        postings = postings_handler.get_latest()
        
        if postings and postings.get('success'):
            # Print the number of postings retrieved
            self.console.print(f"Retrieved [bold green]{postings.get('rows', len(postings.get('data', [])))}[/] postings")
            
            # Display postings in a table
            if postings['data']:
                self.console.print(postings_handler.create_table(postings['data']))
                
                # Show raw JSON for first posting
                self.console.print("\nShowing raw posting data:")
                self.display_json(postings['data'][0], "Sample Posting (Raw JSON)")
            else:
                self.console.print("[yellow]No posting data available[/]")
        else:
            self.console.print("[bold red]Failed to retrieve postings[/]")
            error_message = postings.get('message', 'Unknown error') if postings else 'Unknown error'
            self.console.print(f"[yellow]Error: {error_message}[/]")
    
    def display_receipts(self, receipts_handler):
        """
        Display receipts data (both inbound and outbound)
        
        Args:
            receipts_handler: Handler for receipts API
        """
        # Skip if receipts display is disabled
        if not self.printout_include.get('receipts', True):
            self.console.print("[cyan]Receipts display disabled - skipping[/]")
            return
            
        self.console.rule("[bold blue]RECEIPTS[/]")
        self.console.print("\n[bold cyan]Fetching the latest 5 receipts...[/]")
        
        # Display inbound receipts
        self._display_receipts_by_direction(receipts_handler, 'inbound')
        
        # Display outbound receipts
        self._display_receipts_by_direction(receipts_handler, 'outbound')
    
    def _display_receipts_by_direction(self, receipts_handler, list_direction):
        """
        Display receipts data for a specific direction
        
        Args:
            receipts_handler: Handler for receipts API
            list_direction: Either 'inbound' or 'outbound'
        """
        direction_label = list_direction.upper()
        self.console.print(f"\n[bold cyan]{direction_label} RECEIPTS:[/]")
        
        try:
            receipts = receipts_handler.get_latest(limit=5, list_direction=list_direction)
            
            if receipts and receipts.get('success'):
                # Print the number of receipts retrieved
                receipts_count = len(receipts.get('data', []))
                self.console.print(f"Retrieved [bold green]{receipts_count}[/] {list_direction} receipts")
                
                # Display receipts in a table
                if receipts.get('data'):
                    self.console.print(receipts_handler.create_table(receipts['data']))
                    
                    # Show raw JSON for first receipt
                    if receipts_count > 0:
                        self.console.print("\nShowing raw receipt data:")
                        self.display_json(receipts['data'][0], f"Sample {direction_label} Receipt (Raw JSON)")
                else:
                    self.console.print(f"[yellow]No {list_direction} receipt data available[/]")
            else:
                self.console.print(f"[bold red]Failed to retrieve {list_direction} receipts[/]")
                error_message = receipts.get('message', 'Unknown error') if receipts else 'Unknown error'
                self.console.print(f"[yellow]Error: {error_message}[/]")
                
                # Display status panel with help information if inbound (only once)
                if list_direction == 'inbound':
                    status_panel = Panel(
                        "[yellow]BuchhaltungsButler API Troubleshooting:[/]\n\n"
                        "1. The receipts API endpoint may be temporarily unavailable\n"
                        "2. The API may be experiencing high load\n"
                        "3. Your network connection may be experiencing issues\n"
                        "4. The API credentials may need to be refreshed\n\n"
                        "[green]For backup operations, the script will continue with empty receipts data[/]",
                        title="API Status Information",
                        border_style="red"
                    )
                    self.console.print(status_panel)
        except Exception as e:
            self.console.print(f"[bold red]Error in receipts display: {e}[/]")
            self.console.print(f"[yellow]Continuing without displaying {list_direction} receipts...[/]")