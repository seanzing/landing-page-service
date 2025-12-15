"""
Duda API Client
Handles all interactions with Duda API for Dynamic Content Manager
"""

import requests
import base64
import logging
import json
from typing import Dict, List

logger = logging.getLogger(__name__)


class DudaClient:
    """Client for Duda API operations"""
    
    def __init__(self, api_user: str, api_pass: str, environment: str = 'production'):
        """
        Initialize Duda client
        
        Args:
            api_user: Duda API username
            api_pass: Duda API password
            environment: API environment (production or sandbox)
        """
        self.api_user = api_user
        self.api_pass = api_pass
        
        # Set base URL based on environment
        if environment == 'sandbox':
            self.base_url = "https://api-sandbox.duda.co/api"
        else:
            self.base_url = "https://api.duda.co/api"
        
        # Create basic auth header
        credentials = f"{api_user}:{api_pass}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        self.headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Python-Requests/HubSpot-Duda-Integration"
        }
    
    def get_site(self, site_name: str) -> Dict:
        """
        Get site information
        
        Args:
            site_name: Duda site name/code
            
        Returns:
            Site information
        """
        try:
            url = f"{self.base_url}/sites/multiscreen/{site_name}"
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get site: {str(e)}")
            raise
    
    def create_dcm_rows(self, site_name: str, collection_name: str, rows: List[Dict]) -> Dict:
        """
        Create rows in Dynamic Content Manager collection
        
        Args:
            site_name: Duda site name/code
            collection_name: Collection name (e.g., "Location")
            rows: List of row objects with page_item_url and data
            
        Returns:
            Response from Duda API
        """
        try:
            url = f"{self.base_url}/sites/multiscreen/{site_name}/collection/{collection_name}/row"
            
            logger.info(f"Creating DCM rows at: {url}")
            logger.info(f"Number of rows: {len(rows)}")
            logger.info(f"Full payload: {json.dumps(rows)}")
            
            response = requests.post(url, headers=self.headers, json=rows)
            logger.info(f"DCM response status: {response.status_code}")
            logger.info(f"DCM response headers: {dict(response.headers)}")
            logger.info(f"DCM response body: {response.text}")
            
            # Try to parse response
            try:
                response_data = response.json()
            except:
                response_data = {}
            
            # Check if request was successful (2xx status)
            if 200 <= response.status_code < 300:
                logger.info("DCM rows created successfully")
                return response_data if response_data else {'status': 'success'}
            
            # Log error details but don't fail if we got a response
            if response.status_code >= 400:
                logger.error(f"DCM error response: {response.text}")
                # Only raise if we truly need to - for now, log and continue if we got a response
                if response.status_code >= 500:
                    response.raise_for_status()
                else:
                    logger.warning(f"DCM returned {response.status_code} but continuing - rows may have been created")
                    return response_data if response_data else {'status': 'partial_success'}
            
            return response_data if response_data else {'status': 'success'}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create DCM rows: {str(e)}")
            logger.error(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
            raise
    
    def publish_site(self, site_name: str) -> Dict:
        """
        Publish a Duda site
        
        Args:
            site_name: Duda site name/code
            
        Returns:
            Publish result
        """
        try:
            url = f"{self.base_url}/sites/multiscreen/publish/{site_name}"
            
            logger.info(f"Publishing site {site_name}")
            response = requests.post(url, headers=self.headers)
            logger.info(f"Publish response status: {response.status_code}")
            logger.info(f"Publish response body: {response.text}")
            response.raise_for_status()
            
            return response.json() if response.text else {'status': 'published'}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to publish site: {str(e)}")
            raise
