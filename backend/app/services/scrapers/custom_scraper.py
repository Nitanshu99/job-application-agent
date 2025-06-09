"""
Custom scraper for any job portal with configurable selectors.

This module provides a flexible scraper that can be configured to work with
any job portal by providing CSS selectors and pagination configuration.

Features:
- Configurable CSS selectors for job extraction
- Flexible pagination handling
- Custom field mapping
- URL pattern matching
- Form handling for search
"""

import logging
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlencode, urlparse
import time

from app.services.scrapers.base_scraper import BaseScraper
from app.core.exceptions import ScrapingError

logger = logging.getLogger(__name__)


class CustomScraper(BaseScraper):
    """
    Configurable scraper for custom job portals.
    
    This scraper can be configured with CSS selectors and pagination settings
    to work with any job portal. It provides maximum flexibility for scraping
    different sites with varying HTML structures.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize custom scraper with configuration.
        
        Args:
            config: Configuration dictionary containing selectors and settings
        """
        base_url = config.get('base_url', '')
        rate_limit = config.get('rate_limit', 2.0)
        super().__init__(base_url=base_url, rate_limit=rate_limit)
        
        self.config = config
        self.selectors = config.get('selectors', {})
        self.pagination = config.get('pagination', {})
        self.search_params = config.get('search_params', {})
        self.field_mapping = config.get('field_mapping', {})
        
        # Validate configuration
        self.validate_config()
    
    def validate_config(self) -> None:
        """
        Validate that the configuration contains required fields.
        
        Raises:
            ValueError: If configuration is invalid
        """
        required_fields = ['base_url', 'selectors']
        required_selectors = ['job_title', 'company', 'location']
        
        # Check required top-level fields
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")
        
        # Check required selectors
        for selector in required_selectors:
            if selector not in self.selectors:
                raise ValueError(f"Missing required selector: {selector}")
        
        # Validate URLs
        if not self.base_url:
            raise ValueError("base_url cannot be empty")
    
    def build_search_url(self, keywords: str = "", location: str = "", **kwargs) -> str:
        """
        Build search URL based on configuration.
        
        Args:
            keywords: Search keywords
            location: Job location
            **kwargs: Additional search parameters
            
        Returns:
            Complete search URL
        """
        search_path = self.search_params.get('path', '/jobs')
        
        # Build parameters based on configuration
        params = {}
        
        # Map common parameters
        if keywords and 'keywords_param' in self.search_params:
            params[self.search_params['keywords_param']] = keywords
        
        if location and 'location_param' in self.search_params:
            params[self.search_params['location_param']] = location
        
        # Add any additional configured parameters
        default_params = self.search_params.get('default_params', {})
        params.update(default_params)
        
        # Add any extra parameters passed in
        for key, value in kwargs.items():
            if key in self.search_params.get('allowed_params', []):
                params[key] = value
        
        # Build URL
        base_search_url = urljoin(self.base_url, search_path)
        
        if params:
            return f"{base_search_url}?{urlencode(params)}"
        else:
            return base_search_url
    
    def scrape_jobs(self, keywords: str = "", location: str = "", limit: int = 20,
                   **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape jobs from the custom portal.
        
        Args:
            keywords: Search keywords
            location: Job location filter
            limit: Maximum number of jobs to scrape
            **kwargs: Additional search parameters
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        try:
            # Get all pages if pagination is configured
            if self.pagination:
                jobs = self._scrape_with_pagination(keywords, location, limit, **kwargs)
            else:
                # Single page scraping
                search_url = self.build_search_url(keywords, location, **kwargs)
                jobs = self._scrape_single_page(search_url, limit)
        
        except Exception as e:
            logger.error(f"Error scraping custom portal: {str(e)}")
            raise ScrapingError(f"Failed to scrape custom portal: {str(e)}")
        
        logger.info(f"Successfully scraped {len(jobs)} jobs from custom portal")
        return jobs
    
    def _scrape_with_pagination(self, keywords: str, location: str, limit: int,
                               **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape jobs with pagination support.
        
        Args:
            keywords: Search keywords
            location: Job location
            limit: Maximum number of jobs
            **kwargs: Additional parameters
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        page = self.pagination.get('start_page', 1)
        max_pages = self.pagination.get('max_pages', 10)
        
        while len(jobs) < limit and page <= max_pages:
            # Build URL for current page
            page_kwargs = kwargs.copy()
            page_param = self.pagination.get('page_param', 'page')
            page_kwargs[page_param] = page
            
            search_url = self.build_search_url(keywords, location, **page_kwargs)
            
            logger.info(f"Scraping page {page}: {search_url}")
            
            page_jobs = self._scrape_single_page(search_url, limit - len(jobs))
            
            if not page_jobs:
                logger.info("No more jobs found, stopping pagination")
                break
            
            jobs.extend(page_jobs)
            page += 1
            
            # Check for next page indicator if configured
            if self.pagination.get('next_button'):
                # This would require checking the current page for next button
                # Implementation depends on specific site structure
                pass
            
            time.sleep(self.rate_limit)
        
        return jobs
    
    def _scrape_single_page(self, url: str, limit: int) -> List[Dict[str, Any]]:
        """
        Scrape jobs from a single page.
        
        Args:
            url: URL to scrape
            limit: Maximum number of jobs
            
        Returns:
            List of job dictionaries
        """
        html_content = self.fetch_page(url)
        soup = self.parse_html(html_content)
        
        jobs = []
        
        # Get job container selector
        job_container = self.selectors.get('job_container', '')
        
        if job_container:
            job_elements = soup.select(job_container)
        else:
            # If no container, try to find individual job cards
            job_cards_selector = self.selectors.get('job_cards', '.job')
            job_elements = soup.select(job_cards_selector)
        
        for element in job_elements[:limit]:
            job_data = self.apply_selectors(element)
            if job_data and self.validate_job_data(job_data):
                normalized_job = self.normalize_job_data(job_data)
                jobs.append(normalized_job)
        
        return jobs
    
    def apply_selectors(self, element) -> Optional[Dict[str, Any]]:
        """
        Apply configured selectors to extract job data from an element.
        
        Args:
            element: BeautifulSoup element (job card or container)
            
        Returns:
            Job data dictionary or None if extraction fails
        """
        job_data = {}
        
        try:
            # Apply each configured selector
            for field, selector in self.selectors.items():
                if field in ['job_container', 'job_cards']:
                    continue  # Skip container selectors
                
                # Find element using selector
                if isinstance(selector, str):
                    field_element = element.select_one(selector)
                    value = self.extract_text(field_element) if field_element else ""
                elif isinstance(selector, dict):
                    # Advanced selector with attribute extraction
                    field_element = element.select_one(selector['selector'])
                    if field_element:
                        if 'attribute' in selector:
                            value = field_element.get(selector['attribute'], '')
                        else:
                            value = self.extract_text(field_element)
                    else:
                        value = ""
                else:
                    value = ""
                
                # Apply field mapping if configured
                mapped_field = self.field_mapping.get(field, field)
                job_data[mapped_field] = value
            
            # Post-process specific fields
            job_data = self._post_process_job_data(job_data, element)
            
            return job_data
            
        except Exception as e:
            logger.error(f"Error applying selectors: {str(e)}")
            return None
    
    def _post_process_job_data(self, job_data: Dict[str, Any], element) -> Dict[str, Any]:
        """
        Post-process extracted job data for normalization.
        
        Args:
            job_data: Raw extracted job data
            element: Source element for additional processing
            
        Returns:
            Processed job data
        """
        # Clean and normalize URLs
        if 'job_link' in job_data:
            job_data['url'] = self.clean_url(job_data['job_link'])
        elif 'url' in job_data:
            job_data['url'] = self.clean_url(job_data['url'])
        
        # Extract salary information if present
        if 'salary' in job_data:
            salary_text = job_data['salary']
            min_sal, max_sal = self._parse_salary_custom(salary_text)
            job_data['salary_min'] = min_sal
            job_data['salary_max'] = max_sal
        
        # Parse job type if present
        if 'job_type' in job_data:
            job_data['job_type'] = self._normalize_job_type(job_data['job_type'])
        
        # Add source
        job_data['source'] = 'custom'
        
        return job_data
    
    def _parse_salary_custom(self, salary_text: str) -> tuple[Optional[int], Optional[int]]:
        """
        Parse salary from custom format.
        
        Args:
            salary_text: Raw salary text
            
        Returns:
            Tuple of (min_salary, max_salary)
        """
        if not salary_text:
            return None, None
        
        # Remove common formatting
        cleaned = re.sub(r'[^\d\-k.,]', '', salary_text.lower())
        
        # Look for ranges (e.g., "50k-70k", "50,000-70,000")
        range_match = re.search(r'(\d+(?:[.,]\d+)?)\s*k?\s*-\s*(\d+(?:[.,]\d+)?)\s*k?', cleaned)
        
        if range_match:
            min_val = float(range_match.group(1).replace(',', ''))
            max_val = float(range_match.group(2).replace(',', ''))
            
            # Convert k notation
            if 'k' in salary_text.lower():
                min_val *= 1000
                max_val *= 1000
            
            return int(min_val), int(max_val)
        
        # Look for single values
        single_match = re.search(r'(\d+(?:[.,]\d+)?)\s*k?', cleaned)
        
        if single_match:
            val = float(single_match.group(1).replace(',', ''))
            
            # Convert k notation
            if 'k' in salary_text.lower():
                val *= 1000
            
            # Estimate range for single value
            return int(val), int(val * 1.2)
        
        return None, None
    
    def _normalize_job_type(self, job_type: str) -> str:
        """
        Normalize job type to standard values.
        
        Args:
            job_type: Raw job type string
            
        Returns:
            Normalized job type
        """
        job_type = job_type.lower().strip()
        
        type_mapping = {
            'full time': 'full-time',
            'fulltime': 'full-time',
            'full-time': 'full-time',
            'part time': 'part-time',
            'parttime': 'part-time',
            'part-time': 'part-time',
            'contract': 'contract',
            'temporary': 'temporary',
            'temp': 'temporary',
            'internship': 'internship',
            'intern': 'internship'
        }
        
        return type_mapping.get(job_type, 'full-time')
    
    def get_all_pages(self) -> List[str]:
        """
        Get HTML content from all pages if pagination is configured.
        
        Returns:
            List of HTML content from all pages
        """
        if not self.pagination:
            return []
        
        pages = []
        current_url = self.build_search_url()
        
        while current_url and len(pages) < self.pagination.get('max_pages', 10):
            html_content = self.fetch_page(current_url)
            pages.append(html_content)
            
            # Find next page URL
            soup = self.parse_html(html_content)
            next_button = self.pagination.get('next_button')
            
            if next_button:
                next_elem = soup.select_one(next_button)
                if next_elem and next_elem.get('href'):
                    current_url = self.clean_url(next_elem['href'])
                else:
                    break
            else:
                break
            
            time.sleep(self.rate_limit)
        
        return pages
    
    def test_selectors(self, test_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Test configured selectors on a page to verify they work.
        
        Args:
            test_url: Optional URL to test, defaults to base search URL
            
        Returns:
            Test results with found elements and extracted data
        """
        if not test_url:
            test_url = self.build_search_url()
        
        try:
            html_content = self.fetch_page(test_url)
            soup = self.parse_html(html_content)
            
            results = {
                'url_tested': test_url,
                'selectors_found': {},
                'sample_jobs': []
            }
            
            # Test each selector
            for field, selector in self.selectors.items():
                if isinstance(selector, str):
                    elements = soup.select(selector)
                    results['selectors_found'][field] = {
                        'selector': selector,
                        'elements_found': len(elements),
                        'sample_text': self.extract_text(elements[0]) if elements else None
                    }
            
            # Try to extract a few sample jobs
            job_cards_selector = self.selectors.get('job_cards', '.job')
            job_elements = soup.select(job_cards_selector)[:3]
            
            for element in job_elements:
                job_data = self.apply_selectors(element)
                if job_data:
                    results['sample_jobs'].append(job_data)
            
            return results
            
        except Exception as e:
            logger.error(f"Error testing selectors: {str(e)}")
            return {'error': str(e)}
    
    @classmethod
    def create_from_url(cls, url: str, auto_detect: bool = True) -> 'CustomScraper':
        """
        Create a custom scraper by analyzing a job portal URL.
        
        Args:
            url: URL of the job portal to analyze
            auto_detect: Whether to attempt automatic selector detection
            
        Returns:
            CustomScraper instance with detected configuration
        """
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        config = {
            'base_url': base_url,
            'selectors': {
                'job_title': '.job-title, .title, h3, h2',
                'company': '.company, .company-name, .employer',
                'location': '.location, .job-location, .city',
                'job_link': 'a[href*="job"]',
                'salary': '.salary, .pay, .compensation'
            },
            'search_params': {
                'path': '/jobs',
                'keywords_param': 'q',
                'location_param': 'location'
            }
        }
        
        return cls(config)