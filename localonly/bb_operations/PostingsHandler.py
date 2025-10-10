#!/usr/bin/env python3
from ApiHandler import ApiHandler
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table

class PostingsHandler(ApiHandler):
    """Handler for the BuchhaltungsButler postings API"""
    
    def __init__(self, api_key, api_secret, api_client):
        """Initialize with API credentials"""
        super().__init__(api_key, api_secret, api_client)
        self.endpoint = "/postings/get"
        
    def get_by_date_range(self, date_from, date_to, limit=1000):
        """
        Get postings in a specific date range.
        
        Args:
            date_from (str): Start date in YYYY-MM-DD format
            date_to (str): End date in YYYY-MM-DD format
            limit (int): Number of postings to retrieve (max 1000)
            
        Returns:
            dict: The API response containing posting data
        """
        # Request data
        data = {
            'api_key': self.api_key,
            'date_from': date_from,
            'date_to': date_to,
            'limit': limit,
            'order': 'date DESC'  # Get the most recent postings
        }
        
        # Make the request
        return self._make_request(self.endpoint, data)
        
    def get_latest(self, limit=5):
        """
        Get the latest postings from the BB accounting system.
        
        Args:
            limit (int): Number of postings to retrieve (max 1000)
            
        Returns:
            dict: The API response containing posting data
        """
        # Calculate date range (last 12 months)
        today = datetime.now()
        date_to = today.strftime('%Y-%m-%d')
        date_from = (today - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # Request data
        data = {
            'api_key': self.api_key,
            'date_from': date_from,
            'date_to': date_to,
            'limit': limit,
            'order': 'date DESC'  # Get the most recent postings
        }
        
        # Make the request
        return self._make_request(self.endpoint, data)
    
    def create_table(self, postings_data):
        """
        Create a Rich table for postings
        
        Args:
            postings_data (list): List of posting dictionaries
            
        Returns:
            rich.table.Table: Table object for display
        """
        table = Table(title="Postings")
        
        # Add columns
        table.add_column("ID", style="cyan")
        table.add_column("Date", style="yellow")
        table.add_column("Text", style="green")
        table.add_column("Amount", justify="right", style="magenta")
        table.add_column("VAT", justify="right")
        table.add_column("Debit Acc", justify="right")
        table.add_column("Credit Acc", justify="right")
        table.add_column("Receipt", style="blue")
        
        # Add rows
        for posting in postings_data:
            receipt_info = ""
            if posting.get('receipts_assigned_ids_by_customer'):
                receipt_info = f"{posting.get('receipts_assigned_types', '')}: {posting.get('receipts_assigned_invoice_numbers', '')}"
                
            table.add_row(
                str(posting.get('id_by_customer', '')),
                str(posting.get('date', '')),
                str(posting.get('postingtext', '')),
                f"{posting.get('amount', '')} {posting.get('currency', '')}",
                f"{posting.get('vat', '')}%",
                str(posting.get('debit_postingaccount_number', '')),
                str(posting.get('credit_postingaccount_number', '')),
                receipt_info
            )
        
        return table