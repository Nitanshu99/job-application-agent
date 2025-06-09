"""
Indeed Jobs scraper for extracting job postings from Indeed.

This module provides specialized scraping functionality for Indeed's job portal,
handling their specific HTML structure, pagination, and job detail extraction.

Features:
- Indeed job search and listing scraping
- Salary parsing and normalization
- Location and keyword-based search
- Job detail page extraction
- Sponsored vs organic job filtering
"""

import logging
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, urlparse, parse_qs
from datetime import datetime, timedelta
import time

from app.services.scrapers.base_scraper import BaseScraper
from app.core.exceptions import ScrapingError

logger = logging.getLogger(__name__)


class IndeedScraper(BaseScraper):
    """
    Scraper for Indeed Jobs portal.
    
    Handles Indeed's job search, job listing extraction, and detailed job information.
    Includes salary parsing and job type categorization specific to Indeed's format.
    """
    
    def __init__(self):
        super().__init__(base_url="https://www.indeed.com", rate_limit=1.5)
        
        # Indeed-specific selectors
        self.selectors = {
            'job_cards': '.job_seen_beacon',
            'job_title': '.jobTitle a span[title]',
            'job_title_alt': '.jobTitle a[data-jk]',
            'company': '.companyName',
            'location': '.companyLocation',
            'salary': '.salary-snippet',
            'summary': '.summary',
            'job_link': '.jobTitle a',
            'sponsored': '.sponsoredJob',
            'posted_date': '.date',
            'next_page': 'a[data-testid="pagination-page-next"]'
        }
        
        # Salary conversion rates (hourly to yearly approximation)
        self.hourly_to_yearly = 2080  # 40 hours/week * 52 weeks
    
    def build_search_url(self, keywords: str, location: str = "", radius: int = 25,
                        job_type: str = "", salary_min: int = None, start: int = 0) -> str:
        """
        Build Indeed job search URL with parameters.
        
        Args:
            keywords: Search keywords
            location: Job location
            radius: Search radius in miles
            job_type: Type of job
            salary_min: Minimum salary filter  
            start: Starting position for pagination
            
        Returns:
            Complete search URL
        """
        params = {
            'q': keywords,
            'l': location,
            'radius': radius,
            'start': start,
            'sort': 'date'  # Sort by date posted
        }
        
        # Add job type filter
        if job_type:
            params['jt'] = self._map_job_type(job_type)
        
        # Add salary filter
        if salary_min:
            params['salary'] = f"${salary_min}+"
        
        # Filter out empty parameters
        params = {k: v for k, v in params.items() if v}
        
        base_url = f"{self.base_url}/jobs"
        return f"{base_url}?{urlencode(params)}"
    
    def _map_job_type(self, job_type: str) -> str:
        """Map job type to Indeed's filter values."""
        mapping = {
            'full-time': 'fulltime',
            'part-time': 'parttime',
            'contract': 'contract',
            'temporary': 'temporary',
            'internship': 'internship'
        }
        return mapping.get(job_type.lower(), '')
    
    def scrape_jobs(self, keywords: str, location: str = "", limit: int = 20,
                   job_type: str = "", salary_min: int = None, 
                   include_sponsored: bool = True) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Indeed job search.
        
        Args:
            keywords: Search keywords
            location: Job location filter
            limit: Maximum number of jobs to scrape
            job_type: Type of job filter
            salary_min: Minimum salary filter
            include_sponsored: Whether to include sponsored jobs
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        start = 0
        jobs_per_page = 15  # Indeed shows ~15 jobs per page
        
        try:
            while len(jobs) < limit:
                search_url = self.build_search_url(
                    keywords=keywords,
                    location=location,
                    job_type=job_type,
                    salary_min=salary_min,
                    start=start
                )
                
                logger.info(f"Scraping Indeed jobs page {(start // jobs_per_page) + 1}: {search_url}")
                
                html_content = self.fetch_page(search_url)
                soup = self.parse_html(html_content)
                
                job_cards = soup.select(self.selectors['job_cards'])
                
                if not job_cards:
                    logger.warning("No job cards found on this page")
                    break
                
                for card in job_cards:
                    if len(jobs) >= limit:
                        break
                    
                    # Skip sponsored jobs if not wanted
                    if not include_sponsored and card.select_one(self.selectors['sponsored']):
                        continue
                    
                    job_data = self.parse_job_card(card)
                    if job_data and self.validate_job_data(job_data):
                        jobs.append(self.normalize_job_data(job_data))
                
                start += jobs_per_page
                
                # Check if there's a next page
                if not soup.select_one(self.selectors['next_page']):
                    break
                
                # Respect rate limiting
                time.sleep(self.rate_limit)
        
        except Exception as e:
            logger.error(f"Error scraping Indeed jobs: {str(e)}")
            raise ScrapingError(f"Failed to scrape Indeed jobs: {str(e)}")
        
        logger.info(f"Successfully scraped {len(jobs)} jobs from Indeed")
        return jobs
    
    def parse_job_card(self, card) -> Optional[Dict[str, Any]]:
        """
        Parse individual job card from Indeed search results.
        
        Args:
            card: BeautifulSoup element representing a job card
            
        Returns:
            Job data dictionary or None if parsing fails
        """
        try:
            # Extract job title
            title_elem = card.select_one(self.selectors['job_title'])
            if not title_elem:
                title_elem = card.select_one(self.selectors['job_title_alt'])
            
            # Extract company
            company_elem = card.select_one(self.selectors['company'])
            
            # Extract location
            location_elem = card.select_one(self.selectors['location'])
            
            if not all([title_elem, company_elem, location_elem]):
                logger.warning("Missing required elements in job card")
                return None
            
            # Extract job URL and key
            job_url = ""
            job_key = ""
            link_elem = card.select_one(self.selectors['job_link'])
            if link_elem and link_elem.get('href'):
                job_url = self.clean_url(link_elem['href'])
                job_key = self.extract_job_key(job_url)
            
            # Extract salary information
            salary_elem = card.select_one(self.selectors['salary'])
            salary_min, salary_max = self.parse_salary(
                self.extract_text(salary_elem) if salary_elem else ""
            )
            
            # Extract job summary
            summary_elem = card.select_one(self.selectors['summary'])
            summary = self.extract_text(summary_elem) if summary_elem else ""
            
            # Check if sponsored
            is_sponsored = bool(card.select_one(self.selectors['sponsored']))
            
            # Extract posted date
            date_elem = card.select_one(self.selectors['posted_date'])
            posted_date = self.parse_posted_date(
                self.extract_text(date_elem) if date_elem else ""
            )
            
            job_data = {
                'title': self.extract_text(title_elem),
                'company': self.extract_text(company_elem),
                'location': self.extract_text(location_elem),
                'url': job_url,
                'job_key': job_key,
                'salary_min': salary_min,
                'salary_max': salary_max,
                'description': summary,
                'posted_date': posted_date,
                'is_sponsored': is_sponsored,
                'source': 'indeed'
            }
            
            return job_data
            
        except Exception as e:
            logger.error(f"Error parsing job card: {str(e)}")
            return None
    
    def extract_job_key(self, job_url: str) -> str:
        """
        Extract job key from Indeed job URL.
        
        Args:
            job_url: Indeed job URL
            
        Returns:
            Job key string
        """
        # Indeed job URLs typically look like:
        # https://www.indeed.com/viewjob?jk=abc123def456
        match = re.search(r'[?&]jk=([^&]+)', job_url)
        return match.group(1) if match else ""
    
    def parse_salary(self, salary_text: str) -> tuple[Optional[int], Optional[int]]:
        """
        Parse salary information from Indeed format.
        
        Args:
            salary_text: Raw salary text from Indeed
            
        Returns:
            Tuple of (min_salary, max_salary) in yearly amounts
        """
        if not salary_text:
            return None, None
        
        # Clean the text
        salary_text = salary_text.lower().replace(',', '').replace('$', '')
        
        # Look for salary ranges
        range_match = re.search(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', salary_text)
        
        if range_match:
            min_val = float(range_match.group(1))
            max_val = float(range_match.group(2))
            
            # Convert hourly to yearly if needed
            if 'hour' in salary_text:
                min_val = int(min_val * self.hourly_to_yearly)
                max_val = int(max_val * self.hourly_to_yearly)
            elif 'month' in salary_text:
                min_val = int(min_val * 12)
                max_val = int(max_val * 12)
            else:
                min_val = int(min_val)
                max_val = int(max_val)
            
            return min_val, max_val
        
        # Look for single salary value
        single_match = re.search(r'(\d+(?:\.\d+)?)', salary_text)
        
        if single_match:
            val = float(single_match.group(1))
            
            # Convert to yearly if needed
            if 'hour' in salary_text:
                val = int(val * self.hourly_to_yearly)
            elif 'month' in salary_text:
                val = int(val * 12)
            else:
                val = int(val)
            
            # For single values, estimate a range
            return val, int(val * 1.2)  # 20% higher for max
        
        return None, None
    
    def parse_posted_date(self, date_text: str) -> Optional[datetime]:
        """
        Parse posted date from Indeed format.
        
        Args:
            date_text: Raw date text from Indeed
            
        Returns:
            Parsed datetime or None
        """
        if not date_text:
            return None
        
        date_text = date_text.lower().strip()
        now = datetime.now()
        
        # Today, yesterday, etc.
        if 'today' in date_text or 'just posted' in date_text:
            return now
        elif 'yesterday' in date_text:
            return now - timedelta(days=1)
        
        # "X days ago" format
        days_match = re.search(r'(\d+)\s*days?\s*ago', date_text)
        if days_match:
            days = int(days_match.group(1))
            return now - timedelta(days=days)
        
        # "X weeks ago" format
        weeks_match = re.search(r'(\d+)\s*weeks?\s*ago', date_text)
        if weeks_match:
            weeks = int(weeks_match.group(1))
            return now - timedelta(weeks=weeks)
        
        return None
    
    def get_job_details(self, job_key: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific job.
        
        Args:
            job_key: Indeed job key
            
        Returns:
            Detailed job information
        """
        job_url = f"{self.base_url}/viewjob?jk={job_key}"
        
        try:
            html_content = self.fetch_page(job_url)
            soup = self.parse_html(html_content)
            
            # Extract full job description
            description_elem = soup.select_one('.jobsearch-jobDescriptionText')
            description = self.extract_text(description_elem) if description_elem else ""
            
            # Extract company information
            company_info = {}
            company_section = soup.select_one('.jobsearch-CompanyInfoContainer')
            if company_section:
                company_info = self._parse_company_info(company_section)
            
            # Extract additional job details
            details = {
                'description': description,
                'company_info': company_info,
                'detailed_url': job_url
            }
            
            return details
            
        except Exception as e:
            logger.error(f"Error getting job details for {job_key}: {str(e)}")
            return {}
    
    def _parse_company_info(self, company_section) -> Dict[str, Any]:
        """Parse company information from job detail page."""
        info = {}
        
        try:
            # Company size
            size_elem = company_section.select_one('[data-testid="company-size"]')
            if size_elem:
                info['size'] = self.extract_text(size_elem)
            
            # Company rating
            rating_elem = company_section.select_one('.ratingsDisplay')
            if rating_elem:
                rating_text = self.extract_text(rating_elem)
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    info['rating'] = float(rating_match.group(1))
            
            # Industry
            industry_elem = company_section.select_one('[data-testid="company-industry"]')
            if industry_elem:
                info['industry'] = self.extract_text(industry_elem)
        
        except Exception as e:
            logger.warning(f"Error parsing company info: {str(e)}")
        
        return info
    
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
        search_url = self.build_search_url(f"company:{company_name}", limit=limit)
        
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
    
    def get_salary_trends(self, job_title: str, location: str = "") -> Dict[str, Any]:
        """
        Get salary trend information for a job title.
        
        Args:
            job_title: Job title to analyze
            location: Optional location filter
            
        Returns:
            Salary trend data
        """
        jobs = self.scrape_jobs(job_title, location=location, limit=50)
        
        salaries = []
        for job in jobs:
            if job.get('salary_min') and job.get('salary_max'):
                avg_salary = (job['salary_min'] + job['salary_max']) / 2
                salaries.append(avg_salary)
        
        if not salaries:
            return {}
        
        return {
            'average_salary': sum(salaries) / len(salaries),
            'min_salary': min(salaries),
            'max_salary': max(salaries),
            'median_salary': sorted(salaries)[len(salaries) // 2],
            'total_jobs_analyzed': len(salaries)
        }