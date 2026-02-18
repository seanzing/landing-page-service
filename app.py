"""
Landing Page Service API
FastAPI wrapper for generating SEO-optimized landing pages in Duda.
Deployed on Railway, called by the onboarding platform.
"""

import sys
import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# Add lambda directory to path so we can import existing modules
sys.path.insert(0, str(Path(__file__).parent / "lambda"))

from config import Config
from content_generator import ContentGenerator
from duda_client import DudaClient
from hubspot_client import HubSpotClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Landing Page Service")


# --- Request models ---

class WebhookEvent(BaseModel):
    """HubSpot webhook payload (forwarded from onboarding platform or direct)."""
    objectId: Optional[str] = None
    subscriptionType: Optional[str] = ""
    # Allow the caller to pass contact/deal IDs directly
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None


class OneOffRequest(BaseModel):
    """Direct landing page generation request (replaces one-off scripts)."""
    site_code: str
    industry: str
    base_location: str
    num_pages: int = 50
    collection_name: str = "Location"


# --- Health check ---

@app.get("/")
def health():
    return {"status": "ok", "service": "landing-page-service"}


# --- HubSpot webhook endpoint (mirrors Lambda handler) ---

@app.post("/webhook")
def handle_webhook(events: list[WebhookEvent]):
    """Process HubSpot webhook events — same logic as the Lambda handler."""
    from lambda_function import HubSpotDudaIntegration

    if not events:
        raise HTTPException(status_code=400, detail="Empty event list")

    event = events[0]
    config = Config()

    # If caller passed contact_id/deal_id directly, use those
    if event.contact_id:
        contact_id = event.contact_id
        deal_id = event.deal_id
    elif event.objectId:
        # Resolve from HubSpot like the Lambda does
        subscription_type = event.subscriptionType or ""
        if "deal" in subscription_type:
            hubspot = HubSpotClient(config.HUBSPOT_API_KEY)
            deal_associations = hubspot.get_deal_associations(event.objectId, "contacts")
            if not deal_associations:
                raise HTTPException(status_code=400, detail=f"No contacts for deal {event.objectId}")
            contact_id = deal_associations[0]["id"]
            deal_id = event.objectId
        else:
            contact_id = event.objectId
            deal_id = None
    else:
        raise HTTPException(status_code=400, detail="No objectId or contact_id provided")

    logger.info(f"Processing webhook for contact={contact_id}, deal={deal_id}")
    integration = HubSpotDudaIntegration()
    result = integration.process_contact_update(contact_id, deal_id)
    return json.loads(result["body"]) if isinstance(result.get("body"), str) else result


# --- One-off / direct generation endpoint ---

@app.post("/generate")
def generate_pages(req: OneOffRequest):
    """Generate landing pages directly — used by the onboarding platform."""
    import time

    config = Config()
    if not config.validate():
        raise HTTPException(status_code=500, detail="Missing required configuration")

    content_gen = ContentGenerator(config.OPENAI_API_KEY, config.OPENAI_MODEL)
    duda = DudaClient(config.DUDA_API_USER, config.DUDA_API_PASS)

    # Generate locations
    logger.info(f"Generating {req.num_pages} locations near {req.base_location}")
    try:
        locations = content_gen.generate_locations(
            base_city=req.base_location,
            num_locations=req.num_pages,
            service_type=req.industry,
        )
    except Exception as e:
        logger.error(f"Location generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate locations: {e}")

    # Generate content and build rows
    rows = []
    for i, location in enumerate(locations, 1):
        try:
            content = content_gen.generate_content(
                service=req.industry,
                location=location,
                tone=config.CONTENT_TONE,
                length=config.CONTENT_LENGTH,
            )
            slug = location.lower().replace(", ", "-").replace(" ", "-")
            slug = "".join(c for c in slug if c.isalnum() or c == "-")
            slug = "-".join(filter(None, slug.split("-")))

            rows.append({
                "page_item_url": slug,
                "data": {
                    "Location Name": f"{req.industry} in {location}",
                    "Location Description": content,
                },
            })
            logger.info(f"[{i}/{len(locations)}] {location}")
            time.sleep(config.API_CALL_DELAY)
        except Exception as e:
            logger.error(f"Failed content for {location}: {e}")

    # Send to Duda in batches
    batch_size = config.DUDA_BATCH_SIZE
    total_batches = (len(rows) + batch_size - 1) // batch_size

    for batch_num in range(total_batches):
        start = batch_num * batch_size
        end = min(start + batch_size, len(rows))
        batch = rows[start:end]
        try:
            duda.create_dcm_rows(req.site_code, req.collection_name, batch)
            logger.info(f"Batch {batch_num + 1}/{total_batches} sent ({len(batch)} rows)")
        except Exception as e:
            logger.error(f"Batch {batch_num + 1} failed: {e}")
            raise HTTPException(status_code=500, detail=f"Duda batch {batch_num + 1} failed: {e}")
        time.sleep(1)

    # Publish
    try:
        duda.publish_site(req.site_code)
    except Exception as e:
        logger.warning(f"Publish failed (may need manual publish): {e}")

    return {
        "status": "success",
        "pages_created": len(rows),
        "site_code": req.site_code,
        "locations": [r["data"]["Location Name"] for r in rows],
    }
