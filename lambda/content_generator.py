"""
Content Generator using OpenAI API
Generates SEO-optimized content and locations for service pages
"""

import openai
import logging
import json
from typing import List, Optional, Dict
import re
import time

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Generate SEO-optimized content and locations using OpenAI API"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        """
        Initialize content generator
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-3.5-turbo for cost efficiency)
        """
        self.api_key = api_key
        self.model = model
        openai.api_key = api_key
    
    @staticmethod
    def _normalize_location(loc: str) -> str:
        """
        Normalize a location string to "City Name, ST" format.

        Handles common formats:
            "denver co"       -> "Denver, CO"
            "denver, co"      -> "Denver, CO"
            "  boulder, co  " -> "Boulder, CO"
            "castle rock, colorado" -> "Castle Rock, Colorado"

        Args:
            loc: Raw location string

        Returns:
            Normalized location string
        """
        loc = loc.strip()
        if not loc:
            return loc

        # Split on comma if present, otherwise split on last whitespace token
        if "," in loc:
            parts = [p.strip() for p in loc.split(",", 1)]
        else:
            tokens = loc.rsplit(None, 1)
            if len(tokens) == 2:
                parts = tokens
            else:
                return loc.title()

        city = parts[0].title()
        state = parts[1]

        # Uppercase state if it looks like an abbreviation (1-2 chars)
        if len(state) <= 2:
            state = state.upper()
        else:
            state = state.title()

        return f"{city}, {state}"

    def generate_locations(self, base_city: str, num_locations: int,
                          service_type: str = "",
                          priority_locations: Optional[List[str]] = None) -> List[str]:
        """
        Generate a list of unique nearby locations for a given city

        Args:
            base_city: The city to generate locations around (e.g., "Denver, CO")
            num_locations: Number of locations to generate (10, 50, or 100)
            service_type: Optional service type for context (e.g., "electrician")
            priority_locations: Optional list of must-include locations that appear
                first in the result. Remaining slots are filled with auto-generated
                locations.

        Returns:
            List of unique location names near base_city
        """
        # Normalize and deduplicate priority locations
        if priority_locations:
            seen = set()
            normalized_priorities = []
            for loc in priority_locations:
                norm = self._normalize_location(loc)
                if norm.lower() not in seen and norm:
                    seen.add(norm.lower())
                    normalized_priorities.append(norm)
            priority_locations = normalized_priorities
        else:
            priority_locations = []

        # If priority locations already fill the request, return early
        if len(priority_locations) >= num_locations:
            logger.info(
                f"Priority locations ({len(priority_locations)}) fill all "
                f"{num_locations} slots — skipping GPT location generation"
            )
            return priority_locations[:num_locations]

        remaining = num_locations - len(priority_locations)

        try:
            logger.info(f"Generating {remaining} locations near {base_city}"
                        f" (+ {len(priority_locations)} priority)")

            # Request extra locations to account for potential duplicates
            request_count = min(remaining + 20, remaining * 2)

            exclude_block = ""
            if priority_locations:
                exclude_list = ", ".join(priority_locations)
                exclude_block = f"\n5. Do NOT include any of these already-selected locations: {exclude_list}"

            prompt = f"""Generate a list of exactly {request_count} UNIQUE nearby locations around {base_city}.

CRITICAL REQUIREMENTS:
1. EVERY location must be UNIQUE - no duplicates allowed
2. Each location must be a real, verifiable place
3. Include the state abbreviation (e.g., "Boulder, CO" not just "Boulder")
4. Do NOT include {base_city} itself{exclude_block}

LOCATION PRIORITY (use this order to fill the list):
1. First: Cities and towns within 30 miles of {base_city}
2. Then: Suburbs and unincorporated communities within 45 miles
3. Then: Neighborhoods and districts within {base_city} metro area (e.g., "Westside San Antonio, TX", "North Austin, TX")
4. Then: Cities and towns within 60 miles
5. If still needed: Extend to 75 miles to ensure {request_count} unique locations

For rural areas with few nearby cities, include:
- Named neighborhoods (e.g., "Downtown {base_city.split(',')[0]}")
- Nearby unincorporated communities
- Census-designated places (CDPs)
- Well-known subdivisions or areas

FORMAT: Return ONLY a valid JSON array, no explanations:
["City1, ST", "City2, ST", "Neighborhood Name, ST", ...]

VERIFY before responding:
- All {request_count} locations are UNIQUE
- No location appears twice
- All locations are real places"""

            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a geographic expert that generates comprehensive lists of unique locations. You have extensive knowledge of cities, towns, neighborhoods, suburbs, and communities across the United States. You NEVER return duplicate locations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,  # Lower temperature for more consistent results
                max_tokens=4000   # More tokens for larger lists
            )

            locations_text = response.choices[0].message.content.strip()
            logger.info(f"Raw LLM response: {locations_text[:300]}")

            # Strip markdown code fences if present
            if locations_text.startswith("```"):
                # Remove opening fence (```json or ```)
                locations_text = re.sub(r'^```(?:json)?\s*\n?', '', locations_text)
                # Remove closing fence
                locations_text = re.sub(r'\n?```\s*$', '', locations_text)
                locations_text = locations_text.strip()
                logger.info(f"Stripped markdown fences, cleaned text: {locations_text[:100]}...")

            # Parse JSON response
            try:
                locations = json.loads(locations_text)
                if not isinstance(locations, list):
                    raise ValueError("Response is not a list")

                # Deduplicate while preserving order, also excluding priority locations
                priority_normalized = {p.lower() for p in priority_locations}
                seen = set(priority_normalized)
                unique_locations = []
                for loc in locations:
                    loc_normalized = loc.strip().lower()
                    if loc_normalized not in seen and loc.strip():
                        seen.add(loc_normalized)
                        unique_locations.append(loc.strip())

                logger.info(f"After deduplication: {len(unique_locations)} generated locations")

                # If we don't have enough, try to generate more
                all_so_far = priority_locations + unique_locations
                if len(unique_locations) < remaining:
                    logger.warning(f"Only got {len(unique_locations)} unique locations, need {remaining}. Attempting to generate more...")
                    additional = self._generate_additional_locations(
                        base_city,
                        remaining - len(unique_locations),
                        all_so_far
                    )
                    unique_locations.extend(additional)

                # Combine: priority first, then generated, trim to exact count
                final_locations = priority_locations + unique_locations
                final_locations = final_locations[:num_locations]
                logger.info(f"Final location count: {len(final_locations)} "
                            f"({len(priority_locations)} priority + "
                            f"{len(final_locations) - len(priority_locations)} generated)")
                logger.info(f"Sample locations: {final_locations[:5]}...")

                return final_locations

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {locations_text}")
                raise ValueError(f"Failed to parse location list: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to generate locations: {str(e)}")
            raise

    def _generate_additional_locations(self, base_city: str, needed: int,
                                       existing: List[str]) -> List[str]:
        """
        Generate additional unique locations when initial generation falls short

        Args:
            base_city: The base city
            needed: Number of additional locations needed
            existing: List of already generated locations to avoid duplicates

        Returns:
            List of additional unique locations
        """
        try:
            existing_str = ", ".join(existing[:20])  # Show some existing to avoid

            prompt = f"""I need {needed} MORE unique locations near {base_city}.

ALREADY HAVE (do NOT repeat these): {existing_str}

Generate {needed} DIFFERENT locations I don't have yet. Include:
- Neighborhoods within cities (e.g., "Midtown Atlanta, GA")
- Small communities and CDPs
- Extend radius up to 100 miles if needed

Return ONLY a JSON array: ["Location1, ST", "Location2, ST", ...]"""

            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Generate unique locations not in the existing list."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=2000
            )

            locations_text = response.choices[0].message.content.strip()
            locations = json.loads(locations_text)

            # Deduplicate against existing
            existing_normalized = {loc.strip().lower() for loc in existing}
            additional = []
            for loc in locations:
                loc_normalized = loc.strip().lower()
                if loc_normalized not in existing_normalized and loc.strip():
                    existing_normalized.add(loc_normalized)
                    additional.append(loc.strip())

            logger.info(f"Generated {len(additional)} additional unique locations")
            return additional[:needed]

        except Exception as e:
            logger.error(f"Failed to generate additional locations: {str(e)}")
            return []
    
    def generate_content(self, service: str, location: str, 
                        company_name: Optional[str] = None,
                        keywords: Optional[List[str]] = None,
                        tone: str = "professional",
                        length: str = "3-4 sentences") -> str:
        """
        Generate SEO-optimized content for a service page
        
        Args:
            service: Service or industry type
            location: Service location
            company_name: Optional company name for context
            keywords: Optional list of SEO keywords to include
            tone: Writing tone (professional, casual, etc.)
            length: Content length specification
            
        Returns:
            Generated content text
        """
        try:
            # Build the prompt
            prompt = self._build_prompt(
                service, location, company_name, keywords, tone, length
            )
            
            # Generate content
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert SEO content writer creating location-based service pages. Focus on local SEO, user intent, and natural keyword integration."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=150,
                temperature=0.7,
                n=1
            )
            
            content = response.choices[0].message.content.strip()
            
            # Post-process the content
            content = self._post_process_content(content, service, location, keywords)
            
            # Validate content
            if not self.validate_content(content):
                logger.warning("Generated content failed validation, using fallback")
                return self._generate_fallback_content(service, location, company_name)
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to generate content: {str(e)}")
            # Fallback to template-based content
            return self._generate_fallback_content(service, location, company_name)
    
    def _build_prompt(self, service: str, location: str, 
                     company_name: Optional[str], keywords: Optional[List[str]],
                     tone: str, length: str) -> str:
        """
        Build the prompt for content generation
        
        Args:
            service: Service or industry type
            location: Service location
            company_name: Optional company name
            keywords: Optional SEO keywords
            tone: Writing tone
            length: Content length
            
        Returns:
            Formatted prompt
        """
        prompt_parts = [
            f"Write {length} of {tone} content for a service page about {service} in {location}.",
            "The content should:",
            "- Be informative and engaging",
            "- Focus on local service benefits",
            "- Use natural language that appeals to potential customers",
            "- Avoid promotional language or calls-to-action",
            "- Be suitable for a paragraph below a heading"
        ]
        
        if keywords:
            keyword_list = ", ".join(keywords[:3])
            prompt_parts.append(f"- Naturally incorporate these keywords where appropriate: {keyword_list}")
        
        if company_name:
            prompt_parts.append(f"- You may reference {company_name} as the service provider if it fits naturally")
        
        prompt_parts.append("\nGenerate only the paragraph content, no heading or formatting:")
        
        return "\n".join(prompt_parts)
    
    def _post_process_content(self, content: str, service: str, 
                             location: str, keywords: Optional[List[str]]) -> str:
        """
        Post-process generated content for quality and SEO
        
        Args:
            content: Generated content
            service: Service type
            location: Service location
            keywords: SEO keywords
            
        Returns:
            Processed content
        """
        # Remove any unwanted formatting
        content = re.sub(r'[*_#]', '', content)
        content = re.sub(r'\n+', ' ', content)
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        # Ensure the content mentions the service and location at least once
        service_lower = service.lower()
        location_lower = location.lower()
        
        if service_lower not in content.lower():
            content = f"{content} Our {service} services are designed to meet your specific needs."
        
        if location_lower not in content.lower():
            content = f"{content} Serving the {location} area with dedication and expertise."
        
        # Ensure content is within reasonable length
        sentences = content.split('.')
        if len(sentences) > 5:
            content = '. '.join(sentences[:4]) + '.'
        
        return content
    
    def _generate_fallback_content(self, service: str, location: str, 
                                  company_name: Optional[str] = None) -> str:
        """
        Generate fallback content using templates
        
        Args:
            service: Service type
            location: Service location
            company_name: Optional company name
            
        Returns:
            Template-based content
        """
        templates = [
            f"Finding reliable {service} in {location} requires expertise and local knowledge. "
            f"Our experienced professionals understand the unique needs of the {location} area and deliver "
            f"solutions tailored to your specific requirements. With a commitment to quality and customer "
            f"satisfaction, we ensure every project meets the highest standards.",
            
            f"When it comes to {service} in {location}, quality and reliability matter most. "
            f"Our team brings years of experience serving the {location} community with professional "
            f"services that exceed expectations. We combine industry best practices with local insights "
            f"to deliver results that last.",
            
            f"Professional {service} services in {location} designed to meet your needs. "
            f"We understand that every client has unique requirements, which is why we offer customized "
            f"solutions backed by expertise and dedication. Our {location} team is committed to "
            f"delivering exceptional results on time and within budget."
        ]
        
        template_index = hash(f"{service}{location}") % len(templates)
        content = templates[template_index]
        
        if company_name:
            content = content.replace("Our", f"{company_name}'s")
            content = content.replace("We ", f"At {company_name}, we ")
        
        return content
    
    def generate_seo_metadata(self, service: str, location: str, 
                             heading: str) -> Dict:
        """
        Generate SEO metadata for the page
        
        Args:
            service: Service type
            location: Service location
            heading: Page heading
            
        Returns:
            Dictionary with SEO title and description
        """
        try:
            seo_title = f"{heading} | Professional Services"
            if len(seo_title) > 60:
                seo_title = f"{service} in {location} | Expert Services"
            
            meta_description = (
                f"Looking for {service.lower()} in {location}? "
                f"Discover professional services with experienced experts. "
                f"Quality results guaranteed. Contact us today."
            )
            
            if len(meta_description) > 160:
                meta_description = meta_description[:157] + "..."
            
            keywords = [
                service.lower(),
                location.lower(),
                f"{service.lower()} {location.lower()}",
                f"best {service.lower()}",
                f"{location.lower()} {service.lower()} services"
            ]
            
            return {
                "title": seo_title,
                "description": meta_description,
                "keywords": keywords
            }
            
        except Exception as e:
            logger.error(f"Failed to generate SEO metadata: {str(e)}")
            return {
                "title": heading,
                "description": f"Professional {service} services in {location}",
                "keywords": [service.lower(), location.lower()]
            }
    
    def validate_content(self, content: str) -> bool:
        """
        Validate generated content for quality
        
        Args:
            content: Content to validate
            
        Returns:
            True if content passes validation
        """
        if len(content) < 50:
            return False
        
        if not content.endswith('.'):
            return False
        
        suspicious_patterns = [
            r'\[.*?\]',
            r'INSERT.*?HERE',
            r'TODO',
            r'Lorem ipsum',
            r'Contact us at \d{3}',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False
        
        return True
    
    def batch_generate(self, variations: List[Dict], delay: float = 1.0) -> List[Dict]:
        """
        Generate content for multiple page variations
        
        Args:
            variations: List of variation dictionaries
            delay: Delay between API calls to avoid rate limits
            
        Returns:
            List of variations with generated content
        """
        results = []
        
        for variation in variations:
            try:
                content = self.generate_content(
                    service=variation['service_variant'],
                    location=variation['location_variant'],
                    keywords=variation.get('keywords', [])
                )
                
                seo_metadata = self.generate_seo_metadata(
                    service=variation['service_variant'],
                    location=variation['location_variant'],
                    heading=variation['heading']
                )
                
                variation['content'] = content
                variation['seo_metadata'] = seo_metadata
                results.append(variation)
                
                time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Failed to generate content for variation: {str(e)}")
                variation['content'] = self._generate_fallback_content(
                    variation['service_variant'],
                    variation['location_variant']
                )
                results.append(variation)
        
        return results
