#!/usr/bin/env python3
from ApiHandler import ApiHandler
from datetime import datetime, timedelta
import json
import requests
from requests.auth import HTTPBasicAuth
from rich.console import Console
from rich.table import Table

class ReceiptsHandler(ApiHandler):
    """Handler for the BuchhaltungsButler receipts API with enhanced error handling and filtering"""
    
    def __init__(self, api_key, api_secret, api_client):
        """Initialize with API credentials"""
        super().__init__(api_key, api_secret, api_client)
        self.endpoint = "/receipts/get"
        self.max_retries = 3
        # Debug modes will be set by the main function
        self.debug_mode = False  
        self.enhanced_logging = False
        
    def get_by_date_range(self, date_from, date_to, limit=500, list_direction='inbound'):
        """
        Get receipts in a specific date range with enhanced error handling and fallback.
        
        Args:
            date_from (str): Start date in YYYY-MM-DD format
            date_to (str): End date in YYYY-MM-DD format
            limit (int): Number of receipts to retrieve (max 500)
            list_direction (str): Either 'inbound' (Eingangsbelege) or 'outbound' (Ausgangsbelege)
            
        Returns:
            dict: The API response containing receipt data
        """
        if not self.is_valid:
            return {
                'success': False,
                'message': 'Missing API credentials',
                'data': []
            }
        
        # Storage for successful API response
        result = None
        
        # Log the direction for debugging
        print(f"=== Fetching {list_direction} receipts for date range {date_from} to {date_to} ===")
        
        # Implement a retry approach with progressive fallbacks
        for attempt in range(1, self.max_retries + 1):
            try:
                # Base request data - required fields are api_key and list_direction
                data = {
                    'api_key': self.api_key,
                    'list_direction': list_direction,
                    'limit': limit,
                    'order': json.dumps({"date": "DESC"})  # Get the most recent receipts
                }
                
                # First attempt: Try with date filters
                if attempt == 1 and date_from and date_to:
                    data['date_from'] = date_from
                    data['date_to'] = date_to
                    print(f"Attempt {attempt}: Fetching {list_direction} receipts with date range {date_from} to {date_to}")
                
                # Second attempt: Try without date filters, using full limit
                elif attempt == 2:
                    data['limit'] = 500  # Use maximum allowed limit
                    print(f"Attempt {attempt}: Fetching {list_direction} receipts without date filtering (limit: {data['limit']})")
                
                # Third attempt: Try with minimal parameters
                elif attempt == 3:
                    # Simplify the order parameter
                    data = {
                        'api_key': self.api_key,
                        'list_direction': list_direction,
                        'limit': 100  # Reduce limit to minimize chance of timeout
                    }
                    print(f"Attempt {attempt}: Fetching {list_direction} receipts with minimal parameters (limit: {data['limit']})")
                
                # Make the request
                url = f"{self.base_url}{self.endpoint}"
                auth = HTTPBasicAuth(self.api_client, self.api_secret)
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json',
                    'X-API-Version': '1.8.1'
                }
                
                # Print full request details for debugging
                if self.enhanced_logging:
                    print(f"Request URL: {url}")
                    print(f"Request data: {data}")
                
                # Increased timeout for potentially slow endpoint
                timeout = 20 if attempt < 3 else 10
                
                # Make the request with headers and timeout
                response = requests.post(url, data=data, headers=headers, auth=auth, timeout=timeout)
                
                # Check if request was successful
                if response.status_code == 200:
                    try:
                        result = response.json()
                        
                        # Check if the response is actually valid JSON with expected structure
                        if 'success' in result and result['success'] and 'data' in result:
                            print(f"Successfully retrieved {len(result['data'])} {list_direction} receipts on attempt {attempt}")
                            
                            # If we retrieved receipts without date filtering, apply client-side filtering
                            if attempt > 1 and date_from and date_to:
                                # Manual date filtering
                                filtered_data = self._filter_by_date_range(result['data'], date_from, date_to)
                                result['data'] = filtered_data
                                result['rows'] = len(filtered_data)
                                result['client_filtered'] = True  # Flag that client-side filtering was applied
                                print(f"Applied client-side filtering: {result['rows']} {list_direction} receipts in date range")
                            
                            # Check if we actually have data in the response
                            if len(result['data']) == 0:
                                print(f"WARNING: Retrieved 0 {list_direction} receipts after filtering")
                                
                                # Check first few receipts in unfiltered data if available
                                if 'unfiltered_data' not in result and attempt > 1 and len(result.get('data', [])) == 0:
                                    print(f"No {list_direction} receipts found in date range. Checking raw response data...")
                            
                            return result
                        else:
                            print(f"API returned success=False or missing data on attempt {attempt}")
                            # Debug the actual response 
                            print(f"Response content: {json.dumps(result, indent=2)[:500]}...")
                            # Continue to next attempt if we didn't get valid data
                    except json.JSONDecodeError:
                        print(f"Failed to parse JSON response on attempt {attempt}")
                        # Check if this is an HTML response
                        if '<!DOCTYPE html>' in response.text or '<html' in response.text:
                            print("Received HTML instead of JSON - API may be experiencing issues")
                else:
                    print(f"Error with {list_direction} receipts API on attempt {attempt}: {response.status_code}")
                    # Check if this is an HTML response
                    if '<!DOCTYPE html>' in response.text or '<html' in response.text:
                        print("Received HTML instead of JSON - API may be experiencing issues")
                    else:
                        # Print the first 100 characters of the response to help diagnose the issue
                        print(f"Response preview: {response.text[:500]}...")
            
            except requests.exceptions.Timeout:
                print(f"Timeout after {timeout} seconds on attempt {attempt}")
            except requests.exceptions.ConnectionError:
                print(f"Connection error on attempt {attempt}")
            except requests.exceptions.RequestException as e:
                print(f"Request exception on attempt {attempt}: {e}")
            except Exception as e:
                print(f"Unexpected exception on attempt {attempt}: {e}")
        
        # If we reach here, all attempts failed
        print(f"All attempts to fetch {list_direction} receipts failed")
        
        # Return empty result structure for graceful degradation
        return {
            'success': False,
            'error_code': 999,
            'message': f"Failed to retrieve {list_direction} receipts after multiple attempts",
            'rows': 0,
            'data': []
        }
    
    def get_latest(self, limit=5, list_direction='inbound'):
        """
        Get the latest receipts from the BB accounting system with enhanced error handling.
        
        Args:
            limit (int): Number of receipts to retrieve (max 500)
            list_direction (str): Either 'inbound' (Eingangsbelege) or 'outbound' (Ausgangsbelege)
            
        Returns:
            dict: The API response containing receipt data
        """
        if not self.is_valid:
            return {
                'success': False,
                'message': 'Missing API credentials',
                'data': []
            }
        
        # Implement a retry approach
        max_retries = 2
        for attempt in range(1, max_retries + 1):
            try:
                # Request data - required fields are api_key and list_direction
                data = {
                    'api_key': self.api_key,
                    'list_direction': list_direction,
                    'limit': min(100, limit * 5) if attempt == 1 else min(500, limit * 10),  # Fetch more to sort client-side
                    'order': json.dumps({"date": "DESC"})  # Get the most recent receipts
                }
                
                # Second attempt: Try with minimal parameters
                if attempt == 2:
                    # Simplify request to minimum required parameters
                    data = {
                        'api_key': self.api_key,
                        'list_direction': list_direction,
                        'limit': min(100, limit * 5)  # Reduce limit to minimize chance of timeout, but fetch extra for sorting
                    }
                    print(f"Retry attempt with minimal parameters (limit: {data['limit']})")
                
                # Make the request
                url = f"{self.base_url}{self.endpoint}"
                auth = HTTPBasicAuth(self.api_client, self.api_secret)
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json',
                    'X-API-Version': '1.8.1'
                }
                
                # Timeout settings
                timeout = 20 if attempt == 1 else 10
                
                # Make the request with headers and timeout
                response = requests.post(url, data=data, headers=headers, auth=auth, timeout=timeout)
                
                # Check if request was successful
                if response.status_code == 200:
                    try:
                        result = response.json()
                        
                        # Check if the response is actually valid JSON with expected structure
                        if 'success' in result and result['success'] and 'data' in result:
                            print(f"Successfully retrieved {len(result['data'])} receipts")
                            
                            # Sort receipts by date, newest first (in case API sort didn't work)
                            if result['data']:
                                try:
                                    # Sort by date descending (newest first)
                                    sorted_data = sorted(
                                        result['data'],
                                        key=lambda x: x.get('date', '0000-00-00 00:00:00'),
                                        reverse=True
                                    )
                                    
                                    # Take only the requested limit
                                    result['data'] = sorted_data[:limit]
                                    print(f"Sorted by date and limited to {limit} most recent receipts")
                                except Exception as e:
                                    print(f"Error sorting receipts by date: {e}")
                            
                            return result
                        else:
                            print(f"API returned success=False or missing data on attempt {attempt}")
                    except json.JSONDecodeError:
                        print(f"Failed to parse JSON response on attempt {attempt}")
                        # Check if this is an HTML response
                        if '<!DOCTYPE html>' in response.text or '<html' in response.text:
                            print("Received HTML instead of JSON - API may be experiencing issues")
                else:
                    print(f"Error with receipts API on attempt {attempt}: {response.status_code}")
                    # Check if this is an HTML response
                    if '<!DOCTYPE html>' in response.text or '<html' in response.text:
                        print("Received HTML instead of JSON - API may be experiencing issues")
                    else:
                        # Print the first 100 characters of the response to help diagnose the issue
                        print(f"Response preview: {response.text[:100]}...")
            
            except requests.exceptions.Timeout:
                print(f"Timeout after {timeout} seconds on attempt {attempt}")
            except requests.exceptions.ConnectionError:
                print(f"Connection error on attempt {attempt}")
            except requests.exceptions.RequestException as e:
                print(f"Request exception on attempt {attempt}: {e}")
            except Exception as e:
                print(f"Unexpected exception on attempt {attempt}: {e}")
        
        # If we reach here, all attempts failed
        print("All attempts to fetch receipts failed")
        
        # Return an empty result structure for graceful degradation
        return {
            'success': False,
            'error_code': 999,
            'message': "Failed to retrieve receipts after multiple attempts",
            'rows': 0,
            'data': []
        }
    
    def _filter_by_date_range(self, receipts, date_from, date_to):
        """
        Filter receipts by date range (client-side filtering)
        
        Args:
            receipts (list): List of receipt dictionaries
            date_from (str): Start date in YYYY-MM-DD format
            date_to (str): End date in YYYY-MM-DD format
            
        Returns:
            list: Filtered list of receipts
        """
        try:
            # Convert date strings to datetime objects
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            
            # Add one day to to_date to make the comparison inclusive
            to_date = to_date + timedelta(days=1)
            
            filtered_receipts = []
            for receipt in receipts:
                receipt_date_str = receipt.get('date')
                if receipt_date_str:
                    try:
                        # Parse the receipt date string
                        receipt_date = datetime.strptime(receipt_date_str, '%Y-%m-%d')
                        # Include receipt if date is within range
                        if from_date <= receipt_date < to_date:
                            filtered_receipts.append(receipt)
                    except (ValueError, TypeError):
                        # If date parsing fails, skip this receipt
                        pass
            
            return filtered_receipts
        except Exception as e:
            print(f"Error in client-side date filtering: {e}")
            # Return original list if filtering fails
            return receipts
    
    def create_table(self, receipts_data):
        """
        Create a Rich table for receipts
        
        Args:
            receipts_data (list): List of receipt dictionaries
            
        Returns:
            rich.table.Table: Table object for display
        """
        table = Table(title="Receipts")
        
        # Add columns
        table.add_column("ID", style="cyan")
        table.add_column("Filename", style="green")
        table.add_column("Type", style="blue")
        table.add_column("Date", style="yellow")
        table.add_column("Counterparty", style="magenta")
        table.add_column("Invoice #", style="blue")
        table.add_column("Amount", justify="right", style="red")
        table.add_column("Due Date", style="yellow")
        
        # Add rows
        for receipt in receipts_data:
            table.add_row(
                str(receipt.get('id_by_customer', '')),
                str(receipt.get('filename', '')),
                str(receipt.get('type', '')),
                str(receipt.get('date', '')),
                str(receipt.get('counterparty', '')),
                str(receipt.get('invoicenumber', '')),
                str(receipt.get('amount', '')),
                str(receipt.get('due_date', ''))
            )
        
        return table