"""
HubSpot to Duda Page Creation Lambda Function
Triggers when Deal property changes to "Ready for Published"
Creates 10 or 50 SEO-optimized pages in Duda via Dynamic Content Manager
"""

import json
import os
import logging
import time
from datetime import datetime
from typing import Dict, List

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Import custom modules
from hubspot_client import HubSpotClient
from duda_client import DudaClient
from content_generator import ContentGenerator
from config import Config


class HubSpotDudaIntegration:
    """Main integration class for HubSpot contact to Duda DCM creation"""
    
    def __init__(self):
        """Initialize clients and configuration"""
        self.config = Config()
        self.hubspot = HubSpotClient(self.config.HUBSPOT_API_KEY)
        self.duda = DudaClient(self.config.DUDA_API_USER, self.config.DUDA_API_PASS)
        self.content_gen = ContentGenerator(self.config.OPENAI_API_KEY)
    
    def process_contact_update(self, contact_id: str, deal_id: str = None) -> Dict:
        """
        Process a contact update from HubSpot
        
        Args:
            contact_id: HubSpot contact ID
            deal_id: HubSpot deal ID (optional)
            
        Returns:
            Processing result dictionary
        """
        try:
            logger.info(f"Processing contact {contact_id}")
            
            # Use provided deal_id if available, otherwise fetch from contact associations
            if deal_id:
                logger.info(f"Using provided deal ID from webhook: {deal_id}")
                current_deal_id = deal_id
            else:
                logger.info(f"No deal ID provided, fetching associated deals for contact {contact_id}")
                deals = self.hubspot.get_contact_associations(contact_id, 'deals')
                
                if not deals:
                    logger.warning(f"No associated deals found for contact {contact_id}")
                    return {
                        'statusCode': 400,
                        'body': json.dumps({'error': 'No associated deals found'})
                    }
                
                current_deal_id = deals[0]['id']
                logger.info(f"Found associated deal: {current_deal_id}")
            
            # Fetch deal to get website_status, duda_site_code, and deal type
            deal = self.hubspot.get_deal(current_deal_id, properties=['website_status', 'duda_site_code', 'dealtype'])
            deal_props = deal.get('properties', {})
            website_status = deal_props.get('website_status', '')
            duda_site_code = deal_props.get('duda_site_code', '')
            deal_type = deal_props.get('dealtype', '')
            
            logger.info(f"Deal website_status: {website_status}")
            logger.info(f"Deal duda_site_code: {duda_site_code}")
            logger.info(f"Deal type: {deal_type}")
            
            # Only proceed if website_status is "Ready for Published"
            if website_status != "Ready for Published":
                logger.info(f"Skipping - website_status is '{website_status}', not 'Ready for Published'")
                return {
                    'statusCode': 200,
                    'body': json.dumps({'message': 'Skipped - status not Ready for Published'})
                }
            
            logger.info(f"Website status is Ready for Published - proceeding with page creation")
            
            if not duda_site_code:
                logger.warning(f"No Duda site code found on deal {current_deal_id}")
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'No Duda site code on deal'})
                }
            
            logger.info(f"Duda site code: {duda_site_code}")
            
            # Fetch contact properties - include city/state for location generation
            contact_properties_to_fetch = [
                'industry_1', 'company_name', 'associated_form_id',
                'city', 'state'
            ]
            # Also include manual location fields as fallback
            contact_properties_to_fetch.extend([f'location_{i}' for i in range(1, 101)])
            
            logger.info(f"Fetching contact properties")
            contact = self.hubspot.get_contact(contact_id, properties=contact_properties_to_fetch)
            contact_props = contact.get('properties', {})
            logger.info(f"Retrieved contact properties")
            
            # Form configuration (kept for backwards compatibility but not actively used)
            
            # Extract industry and company name
            industry = contact_props.get('industry_1', '')
            company_name = contact_props.get('company_name', '')
            
            # Get city and state from contact
            city = contact_props.get('city', '')
            state = contact_props.get('state', '')
            base_city = f"{city}, {state}" if city and state else ""
            
            # Determine number of pages based on deal type
            # Priority order matters - check most specific patterns first
            # 100 pages: Dominate tier
            # 50 pages: Boost tier, "50 Local Landing Pages" packages, "Power Pages" packages
            # 10 pages: Discover tier, "10 Landing Pages" packages, "Add on Landing Pages"
            num_pages = 10  # Default
            if deal_type:
                deal_type_lower = str(deal_type).lower()
                logger.info(f"Evaluating deal type: '{deal_type}'")

                # 100 pages: Dominate tier
                if 'dominate' in deal_type_lower:
                    num_pages = 100
                    logger.info(f"Deal type contains 'dominate' - setting to 100 pages")

                # 50 pages: Boost tier
                elif 'boost' in deal_type_lower:
                    num_pages = 50
                    logger.info(f"Deal type contains 'boost' - setting to 50 pages")

                # 50 pages: 50 Local Landing Pages packages
                elif '50 local landing pages' in deal_type_lower:
                    num_pages = 50
                    logger.info(f"Deal type contains '50 local landing pages' - setting to 50 pages")

                # 50 pages: Power Pages packages (Starter Plus Power Pages, ZING Power Pages, Discover/Power Pages, etc.)
                elif 'power pages' in deal_type_lower:
                    num_pages = 50
                    logger.info(f"Deal type contains 'power pages' - setting to 50 pages")

                # 10 pages: Discover tier (checked after power pages since "Discover/Power Pages" should be 50)
                elif 'discover' in deal_type_lower:
                    num_pages = 10
                    logger.info(f"Deal type contains 'discover' - setting to 10 pages")

                # 10 pages: 10 Landing Pages packages
                elif '10 landing pages' in deal_type_lower:
                    num_pages = 10
                    logger.info(f"Deal type contains '10 landing pages' - setting to 10 pages")

                # 10 pages: Add on Landing Pages
                elif 'add on landing pages' in deal_type_lower:
                    num_pages = 10
                    logger.info(f"Deal type contains 'add on landing pages' - setting to 10 pages")

                else:
                    logger.info(f"Deal type '{deal_type}' doesn't match known patterns, defaulting to 10 pages")
            else:
                logger.info("No deal type provided, defaulting to 10 pages")
            
            logger.info(f"Base city: {base_city}, Num pages: {num_pages}")
            
            if not industry:
                logger.warning(f"Missing industry for contact {contact_id}")
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Missing industry'})
                }
            
            # Generate locations if city/state are provided, otherwise try to fetch manual locations
            locations = []
            
            if base_city and city and state:
                logger.info(f"Generating {num_pages} locations near {base_city}")
                try:
                    locations = self.content_gen.generate_locations(
                        base_city=base_city,
                        num_locations=num_pages,
                        service_type=industry
                    )
                    logger.info(f"Generated {len(locations)} locations: {locations[:3]}...")
                except Exception as e:
                    logger.error(f"Failed to generate locations: {str(e)}")
                    return {
                        'statusCode': 400,
                        'body': json.dumps({'error': f'Failed to generate locations: {str(e)}'})
                    }
            else:
                # Fallback: check for manually entered locations
                logger.info("No city/state provided, checking for manually entered locations")
                for i in range(1, num_pages + 1):
                    loc = contact_props.get(f'location_{i}', '')
                    if loc:
                        locations.append(loc)
                
                if not locations:
                    logger.warning(f"No locations found (neither generated nor manual)")
                    return {
                        'statusCode': 400,
                        'body': json.dumps({'error': 'No city/state provided and no manual locations found'})
                    }
            
            if not locations:
                logger.warning(f"No locations available for contact {contact_id}")
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'No locations available'})
                }
            
            logger.info(f"Industry: {industry}, Total locations: {len(locations)}")
            
            # Create DCM rows
            logger.info(f"Creating DCM rows for {len(locations)} locations")
            pages_created = self.create_pages(
                duda_site_code=duda_site_code,
                industry=industry,
                locations=locations,
                company_name=company_name,
                contact_id=contact_id
            )
            
            logger.info(f"Successfully created {len(pages_created)} pages")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Pages created successfully',
                    'pages_created': len(pages_created),
                    'contact_id': contact_id
                })
            }
            
        except Exception as e:
            logger.error(f"Error processing contact: {str(e)}", exc_info=True)
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
    
    def create_pages(self, duda_site_code: str, industry: str, locations: List[str],
                     company_name: str, contact_id: str) -> List[Dict]:
        """
        Create Dynamic Content Manager rows for each location

        Args:
            duda_site_code: Unique Duda site identifier
            industry: Industry type
            locations: List of locations
            company_name: Company name for context
            contact_id: HubSpot contact ID for tracking

        Returns:
            List of created content row information
        """
        created_pages = []
        failed_batches = []
        batch_size = self.config.DUDA_BATCH_SIZE

        try:
            logger.info(f"Creating Dynamic Content Manager rows for {len(locations)} locations")
            logger.info(f"Using batch size of {batch_size} rows per API call")

            # Build all rows first
            rows = []

            for i, location in enumerate(locations):
                # Create page URL slug - remove commas and special characters
                clean_location = location.lower().replace(', ', '-').replace(',', '').replace(' ', '-')
                page_url = f"best-{industry.lower().replace(' ', '-')}-{clean_location}"
                page_title = f"Best {industry} in {location}"

                # Generate content
                logger.info(f"Generating content for location {i+1}/{len(locations)}: {location}")
                content = self.content_gen.generate_content(
                    service=industry,
                    location=location,
                    company_name=company_name,
                    keywords=[industry.lower(), location.lower()]
                )

                # Build row for this location
                row = {
                    "page_item_url": page_url,
                    "data": {
                        "Location Name": page_title,
                        "Location Description": content
                    }
                }
                rows.append(row)
                logger.info(f"Row {i+1} built for {page_url}")

            # Send rows in batches to avoid payload limits
            total_batches = (len(rows) + batch_size - 1) // batch_size
            logger.info(f"Sending {len(rows)} rows in {total_batches} batches")

            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(rows))
                batch_rows = rows[start_idx:end_idx]

                logger.info(f"Sending batch {batch_num + 1}/{total_batches} (rows {start_idx + 1}-{end_idx})")

                try:
                    result = self.duda.create_dcm_rows(
                        site_name=duda_site_code,
                        collection_name="Location",
                        rows=batch_rows
                    )

                    logger.info(f"Batch {batch_num + 1} response: {json.dumps(result)}")

                    # Track successfully created pages from this batch
                    for row in batch_rows:
                        created_pages.append({
                            'url': row['page_item_url'],
                            'heading': row['data']['Location Name'],
                            'description_preview': row['data']['Location Description'][:100]
                        })

                    logger.info(f"Batch {batch_num + 1} completed: {len(batch_rows)} rows created")

                except Exception as batch_error:
                    logger.error(f"Batch {batch_num + 1} failed: {str(batch_error)}")
                    failed_batches.append({
                        'batch_num': batch_num + 1,
                        'start_idx': start_idx,
                        'end_idx': end_idx,
                        'error': str(batch_error),
                        'rows': [r['page_item_url'] for r in batch_rows]
                    })

                # Add delay between batches to avoid rate limiting
                if batch_num < total_batches - 1:
                    delay = self.config.API_CALL_DELAY
                    logger.info(f"Waiting {delay}s before next batch...")
                    time.sleep(delay)

            # Summary
            if failed_batches:
                logger.warning(f"Completed with errors: {len(created_pages)} pages created, {len(failed_batches)} batches failed")
                logger.warning(f"Failed batches: {json.dumps(failed_batches)}")
            else:
                logger.info(f"Successfully created all {len(created_pages)} Dynamic Content rows")

        except Exception as e:
            logger.error(f"Failed to create DCM rows: {str(e)}")
            raise

        return created_pages


def lambda_handler(event, context):
    """
    Lambda handler for webhook events
    
    Args:
        event: Lambda event from API Gateway
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        logger.info(f"Received event: {json.dumps(event)[:300]}")
        
        # Parse body - HubSpot sends an array of events
        if isinstance(event.get('body'), str):
            body = json.loads(event['body']) if event['body'] else []
        else:
            body = event.get('body', [])
        
        logger.info(f"Body: {json.dumps(body)[:300]}")
        
        # Extract the first event
        if isinstance(body, list) and len(body) > 0:
            webhook_event = body[0]
        else:
            webhook_event = body if isinstance(body, dict) else {}
        
        logger.info(f"Webhook event: {json.dumps(webhook_event)[:300]}")
        
        # Get objectId (which is the deal ID in this case)
        object_id = webhook_event.get('objectId')
        subscription_type = webhook_event.get('subscriptionType', '')
        
        logger.info(f"objectId: {object_id}, subscriptionType: {subscription_type}")
        
        if not object_id:
            raise ValueError("No objectId found in webhook")
        
        # If this is a deal.propertyChange, get the associated contact
        if 'deal' in subscription_type:
            logger.info(f"Deal webhook detected, fetching associated contact for deal {object_id}")
            
            # Initialize HubSpot client to get deal's contact
            config = Config()
            hubspot = HubSpotClient(config.HUBSPOT_API_KEY)
            
            # Get deal associations to find contact
            deal_associations = hubspot.get_deal_associations(object_id, 'contacts')
            
            if not deal_associations:
                raise ValueError(f"No associated contacts found for deal {object_id}")
            
            contact_id = deal_associations[0]['id']
            deal_id = object_id
            logger.info(f"Found associated contact: {contact_id}")
        else:
            # If it's a contact webhook, use objectId directly
            contact_id = object_id
            deal_id = None
            logger.info(f"Contact webhook detected, using objectId as contact_id: {contact_id}")
        
        logger.info(f"Processing webhook for contact: {contact_id}, deal: {deal_id}")
        
        # Process the contact
        integration = HubSpotDudaIntegration()
        result = integration.process_contact_update(contact_id, deal_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Lambda error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
