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
    
    def generate_locations(self, base_city: str, num_locations: int, 
                          service_type: str = "") -> List[str]:
        """
        Generate a list of nearby locations for a given city (within 60 mile radius)
        
        Args:
            base_city: The city to generate locations around (e.g., "Denver, CO")
            num_locations: Number of locations to generate (10 or 50)
            service_type: Optional service type for context (e.g., "electrician")
            
        Returns:
            List of location names within 60 miles of base_city
        """
        try:
            logger.info(f"Generating {num_locations} locations within 60 miles of {base_city}")
            
            prompt = f"""Generate a list of exactly {num_locations} nearby cities, towns, and neighborhoods around {base_city}.

CRITICAL CONSTRAINT: ALL locations must be within a 60 mile radius of {base_city}. Do NOT include locations further than 60 miles away.
            
Requirements:
- Return ONLY a valid JSON array of location names
- Each location MUST be a real place within 60 miles of {base_city}
- Include nearby cities, suburbs, and neighborhoods
- Prioritize closer locations first (within 30 miles when possible)
- Format: ["Location 1", "Location 2", ...]
- Do NOT include {base_city} itself
- Include the state/region (e.g., "Boulder, CO" not just "Boulder")
- No explanations, markdown, or extra text - just the JSON array
- VERIFY: Every location must be within 60 miles of {base_city}

Example format for {base_city}:
["Aurora, CO", "Boulder, CO", "Broomfield, CO", "Castle Rock, CO", "Colorado Springs, CO"]"""

            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates lists of nearby cities and towns. You MUST enforce the 60 mile radius constraint strictly. Do not include locations outside the radius."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            locations_text = response.choices[0].message.content.strip()
            logger.info(f"Raw LLM response: {locations_text[:200]}")
            
            # Parse JSON response
            try:
                locations = json.loads(locations_text)
                if not isinstance(locations, list):
                    raise ValueError("Response is not a list")
                
                # Ensure we have exactly the right number
                locations = locations[:num_locations]
                logger.info(f"Generated {len(locations)} locations within 60 miles of {base_city}: {locations[:3]}...")
                return locations
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {locations_text}")
                raise ValueError(f"Failed to parse location list: {str(e)}")
            
        except Exception as e:
            logger.error(f"Failed to generate locations: {str(e)}")
            raise
    
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
