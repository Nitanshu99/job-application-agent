"""
Base scraper class providing common functionality for web scraping services.

This module contains the base scraper class that all specific scrapers inherit from.
It provides common functionality like HTTP requests, rate limiting, HTML parsing,
and error handling.

Features:
- HTTP request handling with retry logic
- Rate limiting to prevent being blocked
- HTML parsing with BeautifulSoup
- Error handling and custom exceptions
- URL normalization and cleaning
- Text extraction utilities
"""

import logging
import time
import re
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
import asyncio
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from app.core.exceptions import ScrapingError, RateLimitError

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Base class for all web scrapers providing common functionality.
    
    This class handles HTTP requests, rate limiting, HTML parsing, and provides
    utility methods that all scrapers can use. Specific scrapers should inherit
    from this class and implement the abstract methods.
    """
    
    def __init__(self, base_url: str, rate_limit: float = 1.0):
        """
        Initialize the base scraper.
        
        Args:
            base_url: Base URL for the website being scraped
            rate_limit: Delay in seconds between requests (default: 1.0)
        """
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.last_request_time = 0
        
        # Common headers to appear more like a real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session.headers.update(self.headers)
        
        # Selenium WebDriver (initialized when needed)
        self.driver = None
        self.use_selenium = False
    
    def apply_rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def fetch_page(self, url: str, params: Optional[Dict] = None, retries: int = 3) -> str:
        """
        Fetch a web page with error handling and retries.
        
        Args:
            url: URL to fetch
            params: Optional query parameters
            retries: Number of retry attempts (default: 3)
            
        Returns:
            HTML content of the page
            
        Raises:
            ScrapingError: If the page cannot be fetched
            RateLimitError: If rate limited by the server
        """
        self.apply_rate_limit()
        
        for attempt in range(retries):
            try:
                logger.debug(f"Fetching URL: {url} (attempt {attempt + 1})")
                
                response = self.session.get(url, params=params, timeout=30)
                
                # Handle rate limiting
                if response.status_code == 429:
                    raise RateLimitError(f"Rate limited when fetching {url}")
                
                # Handle other HTTP errors
                response.raise_for_status()
                
                logger.debug(f"Successfully fetched {url}")
                return response.text
                
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1})")
                if attempt == retries - 1:
                    raise ScrapingError(f"Timeout after {retries} attempts: {url}")
                    
            except requests.exceptions.RequestException as e:
                if "429" in str(e):
                    raise RateLimitError(f"Rate limited when fetching {url}")
                logger.error(f"Request error fetching {url}: {str(e)}")
                if attempt == retries - 1:
                    raise ScrapingError(f"Failed to fetch {url}: {str(e)}")
            
            # Exponential backoff for retries
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                logger.debug(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        raise ScrapingError(f"Failed to fetch {url} after {retries} attempts")
    
    def parse_html(self, html_content: str) -> BeautifulSoup:
        """
        Parse HTML content using BeautifulSoup.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            BeautifulSoup object for parsing
        """
        return BeautifulSoup(html_content, 'html.parser')
    
    def extract_text(self, element: Optional[Union[Tag, str]]) -> str:
        """
        Extract and clean text from a BeautifulSoup element.
        
        Args:
            element: BeautifulSoup element or string
            
        Returns:
            Cleaned text content
        """
        if element is None:
            return ""
        
        if isinstance(element, str):
            text = element
        else:
            text = element.get_text() if hasattr(element, 'get_text') else str(element)
        
        # Clean up whitespace and special characters
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def clean_url(self, url: str) -> str:
        """
        Clean and normalize a URL.
        
        Args:
            url: URL to clean
            
        Returns:
            Cleaned absolute URL
        """
        if not url:
            return ""
        
        # Handle relative URLs
        if url.startswith('/'):
            return urljoin(self.base_url, url)
        
        # Handle URLs that start with protocol
        if url.startswith(('http://', 'https://')):
            return url
        
        # Handle URLs without protocol
        if not url.startswith(('http://', 'https://')):
            return urljoin(self.base_url, url)
        
        return url
    
    def extract_number(self, text: str) -> Optional[int]:
        """
        Extract a number from text string.
        
        Args:
            text: Text containing a number
            
        Returns:
            Extracted number or None if not found
        """
        if not text:
            return None
        
        # Remove common formatting (commas, dollar signs, etc.)
        cleaned = re.sub(r'[^\d]', '', text)
        
        try:
            return int(cleaned) if cleaned else None
        except ValueError:
            return None
    
    def init_selenium(self) -> webdriver.Chrome:
        """
        Initialize Selenium WebDriver for dynamic content.
        
        Returns:
            Chrome WebDriver instance
        """
        if self.driver:
            return self.driver
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-agent={self.headers['User-Agent']}")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            return self.driver
        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {str(e)}")
            raise ScrapingError(f"Failed to initialize WebDriver: {str(e)}")
    
    def fetch_page_selenium(self, url: str) -> str:
        """
        Fetch a page using Selenium for dynamic content.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content after JavaScript execution
        """
        if not self.driver:
            self.init_selenium()
        
        try:
            logger.debug(f"Fetching with Selenium: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            return self.driver.page_source
            
        except TimeoutException:
            raise ScrapingError(f"Timeout loading page with Selenium: {url}")
        except WebDriverException as e:
            raise ScrapingError(f"Selenium error loading {url}: {str(e)}")
    
    def close_selenium(self) -> None:
        """Close Selenium WebDriver if it's open."""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {str(e)}")
    
    def build_url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Build a URL with the base URL and optional parameters.
        
        Args:
            path: URL path to append
            params: Optional query parameters
            
        Returns:
            Complete URL
        """
        url = urljoin(self.base_url, path)
        
        if params:
            # Filter out None values
            filtered_params = {k: v for k, v in params.items() if v is not None}
            if filtered_params:
                url += '?' + urlencode(filtered_params)
        
        return url
    
    @abstractmethod
    def scrape_jobs(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """
        Abstract method to scrape jobs. Must be implemented by subclasses.
        
        Returns:
            List of job dictionaries
        """
        pass
    
    def validate_job_data(self, job: Dict[str, Any]) -> bool:
        """
        Validate that a job dictionary contains required fields.
        
        Args:
            job: Job dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['title', 'company', 'location']
        
        for field in required_fields:
            if not job.get(field):
                logger.warning(f"Job missing required field: {field}")
                return False
        
        return True
    
    def normalize_job_data(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize job data to a standard format.
        
        Args:
            job: Raw job data
            
        Returns:
            Normalized job data
        """
        normalized = {
            'title': self.extract_text(job.get('title', '')),
            'company': self.extract_text(job.get('company', '')),
            'location': self.extract_text(job.get('location', '')),
            'description': self.extract_text(job.get('description', '')),
            'url': self.clean_url(job.get('url', '')),
            'salary_min': job.get('salary_min'),
            'salary_max': job.get('salary_max'),
            'job_type': job.get('job_type', 'full-time'),
            'requirements': job.get('requirements', []),
            'posted_date': job.get('posted_date'),
            'source': job.get('source', self.base_url)
        }
        
        return normalized
    
    def __del__(self):
        """Cleanup when the scraper is destroyed."""
        self.close_selenium()