#!/usr/bin/env python3
import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime, timedelta

class ApiHandler:
    """Base class for all BuchhaltungsButler API handlers"""
    
    def __init__(self, api_key, api_secret, api_client):
        """
        Initialize with API credentials
        
        Args:
            api_key (str): The BuchhaltungsButler API key
            api_secret (str): The BuchhaltungsButler API secret
            api_client (str): The BuchhaltungsButler API client ID
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_client = api_client
        self.base_url = "https://app.buchhaltungsbutler.de/api/v1"
        self.timeout_seconds = 20
        
        # Validate credentials
        self.is_valid = all([self.api_key, self.api_secret, self.api_client])
        
    def _make_request(self, endpoint, data, timeout=None):
        """
        Make an API request with proper error handling
        
        Args:
            endpoint (str): API endpoint (like '/transactions/get')
            data (dict): Request data parameters
            timeout (int, optional): Custom timeout in seconds
            
        Returns:
            dict: API response or error information
        """
        if not self.is_valid:
            return {
                'success': False,
                'message': 'Missing API credentials',
                'data': []
            }
        
        # Use provided timeout or default
        timeout = timeout or self.timeout_seconds
        url = f"{self.base_url}{endpoint}"
        
        # Set up Basic Auth header (Client:Secret)
        auth = HTTPBasicAuth(self.api_client, self.api_secret)
        
        # Set headers with API version
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'X-API-Version': '1.8.1'
        }
        
        try:
            # Make the request with headers and timeout
            response = requests.post(url, data=data, headers=headers, auth=auth, timeout=timeout)
            
            # Check if request was successful
            if response.status_code == 200:
                try:
                    result = response.json()
                    return result
                except json.JSONDecodeError:
                    if '<!DOCTYPE html>' in response.text or '<html' in response.text:
                        return {
                            'success': False,
                            'message': 'Received HTML instead of JSON - API may be experiencing issues',
                            'data': []
                        }
                    return {
                        'success': False,
                        'message': f'Failed to parse JSON response',
                        'data': []
                    }
            else:
                # Check if this is an HTML response
                if '<!DOCTYPE html>' in response.text or '<html' in response.text:
                    return {
                        'success': False,
                        'message': f'Received HTML instead of JSON - API returned status {response.status_code}',
                        'data': []
                    }
                
                return {
                    'success': False,
                    'message': f'API error: {response.status_code}',
                    'data': []
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'message': f'Timeout after {timeout} seconds',
                'data': []
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': 'Connection error',
                'data': []
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}',
                'data': []
            }
            
    def get_date_range(self, days_back=10):
        """
        Generate a date range from today back a specified number of days
        
        Args:
            days_back (int): Number of days to go back
            
        Returns:
            tuple: (date_from, date_to) in 'YYYY-MM-DD' format
        """
        today = datetime.now()
        date_to = today.strftime('%Y-%m-%d')
        date_from = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
        return date_from, date_to