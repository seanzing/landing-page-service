#!/usr/bin/env python3
"""
One-off landing page generation template.

USAGE:
1. Copy this file: cp oneoff_template.py oneoff_yoursite.py
2. Fill in the configuration section below
3. Run: python scripts/oneoff_yoursite.py

CONFIGURATION OPTIONS:
- SITE_CODE: Duda site code (required)
- INDUSTRY: Business type/service (required)
- COLLECTION_NAME: DCM collection name (default: "Location")

For auto-generated locations:
- BASE_LOCATION: Central city, e.g. "Iowa City, Iowa"
- NUM_PAGES: Number of pages to generate (e.g. 50)

For manual locations:
- LOCATIONS: List of specific cities (leave BASE_LOCATION empty)
"""
import sys
import time
import logging
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'lambda'))
sys.path.insert(0, str(project_root / 'scripts'))

from setup_env import setup
setup()

from config import Config
from content_generator import ContentGenerator
from duda_client import DudaClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION - Edit these values
# =============================================================================

SITE_CODE = ""          # e.g. "2d659bec"
INDUSTRY = ""           # e.g. "Painting and Wall Coverings"
COLLECTION_NAME = "Location"

# Option 1: Auto-generate locations near a base city
BASE_LOCATION = ""      # e.g. "Iowa City, Iowa"
NUM_PAGES = 50          # Number of pages to generate

# Option 2: Manually specify locations (leave BASE_LOCATION empty to use this)
LOCATIONS = [
    # "Atlanta, Georgia",
    # "Alpharetta, Georgia",
    # "Marietta, Georgia",
]

# =============================================================================
# END CONFIGURATION
# =============================================================================


def create_slug(location: str) -> str:
    """Create URL-friendly slug from location name"""
    slug = location.lower()
    slug = slug.replace(", ", "-").replace(" ", "-")
    slug = ''.join(c for c in slug if c.isalnum() or c == '-')
    slug = '-'.join(filter(None, slug.split('-')))
    return slug


def main():
    # Validate configuration
    if not SITE_CODE:
        print("ERROR: SITE_CODE is required. Edit the configuration section.")
        return False
    if not INDUSTRY:
        print("ERROR: INDUSTRY is required. Edit the configuration section.")
        return False
    if not BASE_LOCATION and not LOCATIONS:
        print("ERROR: Either BASE_LOCATION or LOCATIONS must be set.")
        return False

    use_manual_locations = bool(LOCATIONS) and not BASE_LOCATION

    print("=" * 60)
    print("One-Off Landing Page Generation")
    print("=" * 60)
    print(f"Site Code:    {SITE_CODE}")
    print(f"Industry:     {INDUSTRY}")
    if use_manual_locations:
        print(f"Mode:         Manual locations ({len(LOCATIONS)} specified)")
    else:
        print(f"Base Location: {BASE_LOCATION}")
        print(f"Pages to Create: {NUM_PAGES}")
    print("=" * 60)

    # Initialize config
    config = Config()
    if not config.validate():
        print("ERROR: Missing required configuration. Check your .env file.")
        return False

    # Initialize clients
    content_gen = ContentGenerator(config.OPENAI_API_KEY, config.OPENAI_MODEL)
    duda = DudaClient(config.DUDA_API_USER, config.DUDA_API_PASS)

    # Get locations (manual or auto-generated)
    if use_manual_locations:
        locations = LOCATIONS
        print(f"\nUsing {len(locations)} manually specified locations:")
        for i, loc in enumerate(locations, 1):
            print(f"  {i}. {loc}")
    else:
        print(f"\n[1/4] Generating {NUM_PAGES} locations near {BASE_LOCATION}...")
        try:
            locations = content_gen.generate_locations(
                base_city=BASE_LOCATION,
                num_locations=NUM_PAGES,
                service_type=INDUSTRY
            )
            print(f"      Generated {len(locations)} unique locations")
            for i, loc in enumerate(locations[:5], 1):
                print(f"      {i}. {loc}")
            if len(locations) > 5:
                print(f"      ... and {len(locations) - 5} more")
        except Exception as e:
            print(f"ERROR generating locations: {e}")
            return False

    step_offset = 0 if use_manual_locations else 1
    total_steps = 3 if use_manual_locations else 4

    # Generate content for each location
    print(f"\n[{1 + step_offset}/{total_steps}] Generating content for {len(locations)} pages...")
    rows = []
    for i, location in enumerate(locations, 1):
        try:
            content = content_gen.generate_content(
                service=INDUSTRY,
                location=location,
                tone=config.CONTENT_TONE,
                length=config.CONTENT_LENGTH
            )

            slug = create_slug(location)
            heading = f"{INDUSTRY} in {location}"

            row = {
                "page_item_url": slug,
                "data": {
                    "Location Name": heading,
                    "Location Description": content
                }
            }
            rows.append(row)

            print(f"      [{i}/{len(locations)}] {location}")
            time.sleep(config.API_CALL_DELAY)

        except Exception as e:
            logger.error(f"Failed to generate content for {location}: {e}")
            print(f"      [{i}/{len(locations)}] FAILED: {location} - {e}")

    print(f"      Generated content for {len(rows)} pages")

    # Create DCM rows in Duda
    print(f"\n[{2 + step_offset}/{total_steps}] Creating pages in Duda site {SITE_CODE}...")
    try:
        batch_size = config.DUDA_BATCH_SIZE
        total_batches = (len(rows) + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(rows))
            batch = rows[start_idx:end_idx]

            print(f"      Sending batch {batch_num + 1}/{total_batches} ({len(batch)} rows)...")
            result = duda.create_dcm_rows(SITE_CODE, COLLECTION_NAME, batch)
            logger.info(f"Batch {batch_num + 1} result: {result}")
            time.sleep(1)

        print(f"      Successfully created {len(rows)} pages")

    except Exception as e:
        print(f"ERROR creating DCM rows: {e}")
        return False

    # Publish site
    print(f"\n[{3 + step_offset}/{total_steps}] Publishing site {SITE_CODE}...")
    try:
        duda.publish_site(SITE_CODE)
        print(f"      Site published successfully")
    except Exception as e:
        print(f"WARNING: Failed to publish site: {e}")
        print("      You may need to publish manually in Duda")

    print("\n" + "=" * 60)
    print("COMPLETE!")
    print(f"Created {len(rows)} landing pages for {INDUSTRY}")
    if use_manual_locations:
        print(f"Locations: {len(LOCATIONS)} manual")
    else:
        print(f"Base location: {BASE_LOCATION}")
    print(f"Site: {SITE_CODE}")
    print("=" * 60)

    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
