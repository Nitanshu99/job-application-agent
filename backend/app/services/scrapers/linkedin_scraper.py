"""
LinkedIn Jobs scraper for extracting job postings from LinkedIn.

This module provides specialized scraping functionality for LinkedIn's job portal,
handling their specific HTML structure, pagination, and job detail extraction.

Features:
- LinkedIn job search and listing scraping
- Job detail page extraction
- Location and keyword-based search
- Dynamic content loading with Selenium
- Rate limiting and error handling
"""

import logging
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, urlparse, parse_qs
from datetime import datetime, timedelta
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from app.services.scrapers.base_scraper import BaseScraper
from app.core.exceptions import ScrapingError

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """
    Scraper for LinkedIn Jobs portal.
    
    Handles LinkedIn's job search, job listing extraction, and detailed job information.
    Supports both requests-based scraping for basic listings and Selenium for dynamic content.
    """
    
    def __init__(self):
        super().__init__(base_url="https://www.linkedin.com", rate_limit=2.0)
        
        # LinkedIn-specific selectors
        self.selectors = {
            'job_cards': '.base-card',
            'job_title': '.base-search-card__title',
            'company': '.base-search-card__subtitle',
            'location': '.job-search-card__location',
            'job_link': '.base-card__full-link',
            'posted_date': 'time',
            'description': '.description__text',
            'requirements': '.description__text ul li',
            'next_page': '.artdeco-pagination__button--next'
        }
        
        # Common job types mapping
        self.job_type_mapping = {
            'full-time': 'full-time',
            'part-time': 'part-time',
            'contract': 'contract',
            'internship': 'internship',
            'temporary': 'temporary'
        }
    
    def build_search_url(self, keywords: str, location: str = "", job_type: str = "", 
                        experience_level: str = "", salary_min: int = None) -> str:
        """
        Build LinkedIn job search URL with parameters.
        
        Args:
            keywords: Search keywords
            location: Job location
            job_type: Type of job (full-time, part-time, etc.)
            experience_level: Experience level (entry, mid, senior)
            salary_min: Minimum salary filter
            
        Returns:
            Complete search URL
        """
        params = {
            'keywords': keywords,
            'location': location,
            'f_TPR': 'r86400',  # Last 24 hours
            'f_E': self._map_experience_level(experience_level),
            'f_JT': self._map_job_type(job_type),
            'start': 0
        }
        
        # Filter out empty parameters
        params = {k: v for k, v in params.items() if v}
        
        base_url = f"{self.base_url}/jobs/search"
        return f"{base_url}?{urlencode(params)}"
    
    def _map_experience_level(self, level: str) -> str:
        """Map experience level to LinkedIn's filter values."""
        mapping = {
            'internship': '1',
            'entry': '2', 
            'associate': '3',
            'mid': '4',
            'senior': '5',
            'director': '6',
            'executive': '7'
        }
        return mapping.get(level.lower(), '')
    
    def _map_job_type(self, job_type: str) -> str:
        """Map job type to LinkedIn's filter values."""
        mapping = {
            'full-time': 'F',
            'part-time': 'P',
            'contract': 'C',
            'temporary': 'T',
            'internship': 'I',
            'volunteer': 'V'
        }
        return mapping.get(job_type.lower(), '')
    
    def scrape_jobs(self, keywords: str, location: str = "", limit: int = 20,
                   job_type: str = "", experience_level: str = "") -> List[Dict[str, Any]]:
        """
        Scrape jobs from LinkedIn job search.
        
        Args:
            keywords: Search keywords
            location: Job location filter
            limit: Maximum number of jobs to scrape
            job_type: Type of job filter
            experience_level: Experience level filter
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        page = 0
        jobs_per_page = 25  # LinkedIn shows ~25 jobs per page
        
        try:
            while len(jobs) < limit:
                search_url = self.build_search_url(
                    keywords=keywords,
                    location=location,
                    job_type=job_type,
                    experience_level=experience_level
                )
                
                # Add pagination
                if page > 0:
                    search_url += f"&start={page * jobs_per_page}"
                
                logger.info(f"Scraping LinkedIn jobs page {page + 1}: {search_url}")
                
                html_content = self.fetch_page(search_url)
                soup = self.parse_html(html_content)
                
                job_cards = soup.select(self.selectors['job_cards'])
                
                if not job_cards:
                    logger.warning("No job cards found on this page")
                    break
                
                for card in job_cards:
                    if len(jobs) >= limit:
                        break
                    
                    job_data = self.parse_job_card(card)
                    if job_data and self.validate_job_data(job_data):
                        jobs.append(self.normalize_job_data(job_data))
                
                page += 1
                
                # Check if there's a next page
                if not soup.select(self.selectors['next_page']):
                    break
                
                # Respect rate limiting
                time.sleep(self.rate_limit)
        
        except Exception as e:
            logger.error(f"Error scraping LinkedIn jobs: {str(e)}")
            raise ScrapingError(f"Failed to scrape LinkedIn jobs: {str(e)}")
        
        logger.info(f"Successfully scraped {len(jobs)} jobs from LinkedIn")
        return jobs
    
    def parse_job_card(self, card) -> Optional[Dict[str, Any]]:
        """
        Parse individual job card from LinkedIn search results.
        
        Args:
            card: BeautifulSoup element representing a job card
            
        Returns:
            Job data dictionary or None if parsing fails
        """
        try:
            # Extract basic information
            title_elem = card.select_one(self.selectors['job_title'])
            company_elem = card.select_one(self.selectors['company'])
            location_elem = card.select_one(self.selectors['location'])
            link_elem = card.select_one(self.selectors['job_link'])
            date_elem = card.select_one(self.selectors['posted_date'])
            
            if not all([title_elem, company_elem, location_elem]):
                logger.warning("Missing required elements in job card")
                return None
            
            # Extract job URL and ID
            job_url = ""
            job_id = ""
            if link_elem and link_elem.get('href'):
                job_url = self.clean_url(link_elem['href'])
                job_id = self.extract_job_id(job_url)
            
            # Parse posted date
            posted_date = None
            if date_elem and date_elem.get('datetime'):
                try:
                    posted_date = datetime.fromisoformat(date_elem['datetime'].replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Could not parse date: {date_elem.get('datetime')}")
            
            job_data = {
                'title': self.extract_text(title_elem),
                'company': self.extract_text(company_elem),
                'location': self.extract_text(location_elem),
                'url': job_url,
                'job_id': job_id,
                'posted_date': posted_date,
                'source': 'linkedin'
            }
            
            return job_data
            
        except Exception as e:
            logger.error(f"Error parsing job card: {str(e)}")
            return None
    
    def extract_job_id(self, job_url: str) -> str:
        """
        Extract job ID from LinkedIn job URL.
        
        Args:
            job_url: LinkedIn job URL
            
        Returns:
            Job ID string
        """
        # LinkedIn job URLs typically look like:
        # https://www.linkedin.com/jobs/view/123456789
        match = re.search(r'/jobs/view/(\d+)', job_url)
        return match.group(1) if match else ""
    
    def get_job_details(self, job_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific job.
        
        Args:
            job_id: LinkedIn job ID
            
        Returns:
            Detailed job information
        """
        job_url = f"{self.base_url}/jobs/view/{job_id}"
        
        try:
            html_content = self.fetch_page(job_url)
            soup = self.parse_html(html_content)
            
            # Extract detailed description
            description_elem = soup.select_one(self.selectors['description'])
            description = self.extract_text(description_elem) if description_elem else ""
            
            # Extract requirements from list items
            requirements = []
            req_elements = soup.select(self.selectors['requirements'])
            for req_elem in req_elements:
                req_text = self.extract_text(req_elem)
                if req_text:
                    requirements.append(req_text)
            
            # Extract additional details
            details = {
                'description': description,
                'requirements': requirements,
                'detailed_url': job_url
            }
            
            return details
            
        except Exception as e:
            logger.error(f"Error getting job details for {job_id}: {str(e)}")
            return {}
    
    def scrape_jobs_dynamic(self, keywords: str, location: str = "", limit: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape jobs using Selenium for dynamic content.
        
        Args:
            keywords: Search keywords
            location: Job location
            limit: Maximum number of jobs
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        try:
            # Initialize Selenium
            driver = self.init_selenium()
            
            search_url = self.build_search_url(keywords, location)
            logger.info(f"Loading LinkedIn with Selenium: {search_url}")
            
            driver.get(search_url)
            
            # Wait for job cards to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['job_cards']))
            )
            
            # Scroll to load more jobs
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            while len(jobs) < limit:
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for new content to load
                time.sleep(2)
                
                # Check if new content loaded
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                
                # Parse currently loaded jobs
                soup = self.parse_html(driver.page_source)
                job_cards = soup.select(self.selectors['job_cards'])
                
                for card in job_cards[len(jobs):]:  # Only process new cards
                    if len(jobs) >= limit:
                        break
                    
                    job_data = self.parse_job_card(card)
                    if job_data and self.validate_job_data(job_data):
                        jobs.append(self.normalize_job_data(job_data))
            
        except TimeoutException:
            logger.error("Timeout waiting for LinkedIn page to load")
            raise ScrapingError("Timeout loading LinkedIn page")
        except Exception as e:
            logger.error(f"Error in dynamic scraping: {str(e)}")
            raise ScrapingError(f"Dynamic scraping failed: {str(e)}")
        finally:
            self.close_selenium()
        
        logger.info(f"Successfully scraped {len(jobs)} jobs with Selenium")
        return jobs
    
    def search_by_company(self, company_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for jobs at a specific company.
        
        Args:
            company_name: Name of the company
            limit: Maximum number of jobs
            
        Returns:
            List of job dictionaries
        """
        # Use company-specific search
        search_url = f"{self.base_url}/jobs/search?f_C={company_name}"
        
        try:
            html_content = self.fetch_page(search_url)
            soup = self.parse_html(html_content)
            
            jobs = []
            job_cards = soup.select(self.selectors['job_cards'])
            
            for card in job_cards[:limit]:
                job_data = self.parse_job_card(card)
                if job_data and self.validate_job_data(job_data):
                    jobs.append(self.normalize_job_data(job_data))
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error searching jobs by company {company_name}: {str(e)}")
            raise ScrapingError(f"Company search failed: {str(e)}")
    
    def get_trending_jobs(self, location: str = "", limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get trending/popular jobs from LinkedIn.
        
        Args:
            location: Optional location filter
            limit: Maximum number of jobs
            
        Returns:
            List of trending job dictionaries
        """
        params = {
            'sortBy': 'DD',  # Date posted (most recent)
            'f_TPR': 'r86400',  # Last 24 hours
        }
        
        if location:
            params['location'] = location
        
        search_url = f"{self.base_url}/jobs/search?{urlencode(params)}"
        
        return self.scrape_jobs("", location=location, limit=limit)