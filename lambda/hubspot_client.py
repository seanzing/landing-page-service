"""
HubSpot API Client
Handles interactions with HubSpot API for deal and contact information
"""

import requests
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class HubSpotClient:
    """Client for HubSpot API operations"""
    
    def __init__(self, api_key: str):
        """
        Initialize HubSpot client
        
        Args:
            api_key: HubSpot API key
        """
        self.api_key = api_key
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_deal(self, deal_id: str, properties: Optional[List[str]] = None) -> Dict:
        """
        Get deal information from HubSpot
        
        Args:
            deal_id: HubSpot deal ID
            properties: List of properties to retrieve
            
        Returns:
            Deal data dictionary
        """
        try:
            url = f"{self.base_url}/crm/v3/objects/deals/{deal_id}"
            
            params = {}
            if properties:
                params['properties'] = properties
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get deal {deal_id}: {str(e)}")
            raise
    
    def get_contact(self, contact_id: str, properties: Optional[List[str]] = None) -> Dict:
        """
        Get contact information with custom properties
        
        Args:
            contact_id: HubSpot contact ID
            properties: List of custom properties to retrieve
            
        Returns:
            Contact data dictionary
        """
        try:
            url = f"{self.base_url}/crm/v3/objects/contacts/{contact_id}"
            
            params = {}
            if properties:
                params['properties'] = properties
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get contact {contact_id}: {str(e)}")
            raise
    
    def get_contact_associations(self, contact_id: str, association_type: str = 'deals') -> List[Dict]:
        """
        Get associated objects for a contact
        
        Args:
            contact_id: HubSpot contact ID
            association_type: Type of association (deals, companies, etc.)
            
        Returns:
            List of associated objects
        """
        try:
            url = f"{self.base_url}/crm/v3/objects/contacts/{contact_id}/associations/{association_type}"
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json().get('results', [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get contact associations: {str(e)}")
            raise
    
    def get_deal_associations(self, deal_id: str, association_type: str = 'contacts') -> List[Dict]:
        """
        Get associated objects for a deal
        
        Args:
            deal_id: HubSpot deal ID
            association_type: Type of association (contacts, companies, etc.)
            
        Returns:
            List of associated objects
        """
        try:
            url = f"{self.base_url}/crm/v3/objects/deals/{deal_id}/associations/{association_type}"
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json().get('results', [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get deal associations: {str(e)}")
            raise
