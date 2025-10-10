#!/usr/bin/env python3
from ApiHandler import ApiHandler
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table

class TransactionsHandler(ApiHandler):
    """Handler for the BuchhaltungsButler transactions API"""
    
    def __init__(self, api_key, api_secret, api_client):
        """Initialize with API credentials"""
        super().__init__(api_key, api_secret, api_client)
        self.endpoint = "/transactions/get"
        
    def get_by_date_range(self, date_from, date_to, limit=500):
        """
        Get transactions in a specific date range.
        
        Args:
            date_from (str): Start date in YYYY-MM-DD format
            date_to (str): End date in YYYY-MM-DD format
            limit (int): Number of transactions to retrieve (max 500)
            
        Returns:
            dict: The API response containing transaction data
        """
        # Request data
        data = {
            'api_key': self.api_key,
            'limit': limit,
            'date_from': date_from,
            'date_to': date_to
        }
        
        # Make the request
        return self._make_request(self.endpoint, data)
        
    def get_latest(self, limit=5):
        """
        Get the latest transactions from the BB accounting system.
        
        Args:
            limit (int): Number of transactions to retrieve (max 500)
            
        Returns:
            dict: The API response containing transaction data
        """
        # Request data
        data = {
            'api_key': self.api_key,
            'limit': limit
        }
        
        # Make the request
        return self._make_request(self.endpoint, data)
    
    def create_table(self, transactions_data):
        """
        Create a Rich table for transactions
        
        Args:
            transactions_data (list): List of transaction dictionaries
            
        Returns:
            rich.table.Table: Table object for display
        """
        table = Table(title="Transactions")
        
        # Add columns
        table.add_column("ID", style="cyan")
        table.add_column("From/To", style="green")
        table.add_column("Amount", justify="right", style="magenta")
        table.add_column("Booking Date", style="yellow")
        table.add_column("Purpose", style="blue")
        
        # Add rows
        for transaction in transactions_data:
            table.add_row(
                str(transaction.get('id_by_customer', '')),
                str(transaction.get('to_from', '')),
                str(transaction.get('amount', '')),
                str(transaction.get('booking_date', '')),
                str(transaction.get('purpose', ''))
            )
        
        return table