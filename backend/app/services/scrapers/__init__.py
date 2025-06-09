"""
Scrapers package for job automation system.

This package contains web scraping modules for extracting job postings from
various job portals including LinkedIn, Indeed, and custom company websites.

Usage:
    from app.services.scrapers import ScraperFactory
    
    # Get a scraper for a specific platform
    linkedin_scraper = ScraperFactory.get_scraper('linkedin')
    indeed_scraper = ScraperFactory.get_scraper('indeed')
    
    # Get scraper based on URL
    scraper = ScraperFactory.get_scraper_by_url('https://jobs.example.com')
    
    # Scrape jobs
    jobs = linkedin_scraper.scrape_jobs('python developer', location='San Francisco')
"""

import logging
from typing import Dict, Any, Optional, List

# Import scraper classes
from .base_scraper import BaseScraper
from .linkedin_scraper import LinkedInScraper
from .indeed_scraper import IndeedScraper
from .custom_scraper import CustomScraper
from .scraper_factory import ScraperFactory

logger = logging.getLogger(__name__)

# Package metadata
__version__ = "1.0.0"
__author__ = "Job Automation System"
__description__ = "Web scraping modules for job portals"

# Export main classes
__all__ = [
    "BaseScraper",
    "LinkedInScraper", 
    "IndeedScraper",
    "CustomScraper",
    "ScraperFactory",
    "create_scraper",
    "get_supported_platforms",
    "validate_scraper_config"
]


def create_scraper(platform: str, config: Optional[Dict[str, Any]] = None) -> BaseScraper:
    """
    Convenience function to create a scraper instance.
    
    Args:
        platform: Platform name (linkedin, indeed, custom)
        config: Optional configuration dictionary
        
    Returns:
        Configured scraper instance
    """
    return ScraperFactory.get_scraper(platform, config)


def get_supported_platforms() -> List[str]:
    """
    Get list of supported scraping platforms.
    
    Returns:
        List of platform names
    """
    return ScraperFactory.get_available_scrapers()


def validate_scraper_config(config: Dict[str, Any]) -> bool:
    """
    Validate scraper configuration.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    return ScraperFactory.validate_scraper_config(config)


# Example configurations for common platforms
EXAMPLE_CONFIGS = {
    'greenhouse': {
        'base_url': 'https://boards.greenhouse.io',
        'selectors': {
            'job_cards': '.opening',
            'job_title': '.opening a',
            'company': '.company-name',
            'location': '.location',
            'job_link': '.opening a'
        },
        'search_params': {
            'path': '/embed/job_board',
            'keywords_param': 'q'
        }
    },
    'lever': {
        'base_url': 'https://jobs.lever.co',
        'selectors': {
            'job_cards': '.posting',
            'job_title': '.posting-name h5',
            'company': '.posting-company',
            'location': '.posting-categories .location',
            'job_link': 'a.posting-btn-submit'
        },
        'search_params': {
            'path': '/postings'
        }
    },
    'workday': {
        'base_url': '',  # Varies by company
        'selectors': {
            'job_cards': '[data-automation-id="jobPostingItem"]',
            'job_title': '[data-automation-id="jobPostingTitle"]',
            'company': '[data-automation-id="jobPostingCompany"]', 
            'location': '[data-automation-id="jobPostingLocation"]',
            'job_link': '[data-automation-id="jobPostingTitle"] a'
        },
        'search_params': {
            'path': '/jobs',
            'keywords_param': 'q'
        }
    }
}


def create_custom_scraper_config(base_url: str, 
                                job_card_selector: str = '.job',
                                title_selector: str = '.title',
                                company_selector: str = '.company', 
                                location_selector: str = '.location') -> Dict[str, Any]:
    """
    Create a basic custom scraper configuration.
    
    Args:
        base_url: Base URL of the job portal
        job_card_selector: CSS selector for job cards
        title_selector: CSS selector for job titles
        company_selector: CSS selector for company names
        location_selector: CSS selector for job locations
        
    Returns:
        Configuration dictionary for custom scraper
    """
    return {
        'base_url': base_url,
        'selectors': {
            'job_cards': job_card_selector,
            'job_title': title_selector,
            'company': company_selector,
            'location': location_selector,
            'job_link': 'a[href*="job"], a[href*="position"]'
        },
        'search_params': {
            'path': '/jobs',
            'keywords_param': 'q',
            'location_param': 'location'
        }
    }


def get_example_config(platform: str) -> Optional[Dict[str, Any]]:
    """
    Get example configuration for common ATS platforms.
    
    Args:
        platform: Platform name (greenhouse, lever, workday)
        
    Returns:
        Example configuration or None if not available
    """
    return EXAMPLE_CONFIGS.get(platform.lower())


# Initialize logging for the scrapers package
def setup_logging(level: str = "INFO") -> None:
    """
    Setup logging for the scrapers package.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    # Configure logger for scrapers package
    scrapers_logger = logging.getLogger('app.services.scrapers')
    scrapers_logger.setLevel(numeric_level)
    
    # Add handler if none exists
    if not scrapers_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        scrapers_logger.addHandler(handler)


# Quick start example
def quick_start_example():
    """
    Example of how to use the scrapers package.
    
    This function demonstrates basic usage patterns for the scrapers.
    """
    print("=== Job Scrapers Quick Start ===")
    
    # 1. List supported platforms
    platforms = get_supported_platforms()
    print(f"Supported platforms: {', '.join(platforms)}")
    
    # 2. Create LinkedIn scraper
    try:
        linkedin_scraper = create_scraper('linkedin')
        print("✓ LinkedIn scraper created successfully")
        
        # Test URL building
        test_url = linkedin_scraper.build_search_url('python developer', 'San Francisco')
        print(f"Sample LinkedIn URL: {test_url}")
        
    except Exception as e:
        print(f"✗ Failed to create LinkedIn scraper: {e}")
    
    # 3. Create Indeed scraper
    try:
        indeed_scraper = create_scraper('indeed')
        print("✓ Indeed scraper created successfully")
        
        # Test URL building
        test_url = indeed_scraper.build_search_url('data scientist', 'New York')
        print(f"Sample Indeed URL: {test_url}")
        
    except Exception as e:
        print(f"✗ Failed to create Indeed scraper: {e}")
    
    # 4. Create custom scraper
    try:
        custom_config = create_custom_scraper_config(
            base_url='https://careers.example.com',
            job_card_selector='.job-listing',
            title_selector='.job-title',
            company_selector='.company-name',
            location_selector='.job-location'
        )
        
        custom_scraper = create_scraper('custom', custom_config)
        print("✓ Custom scraper created successfully")
        
    except Exception as e:
        print(f"✗ Failed to create custom scraper: {e}")
    
    # 5. Auto-detect platform from URL
    try:
        auto_scraper = ScraperFactory.get_scraper_by_url('https://www.linkedin.com/jobs')
        print("✓ Auto-detected LinkedIn from URL")
        
    except Exception as e:
        print(f"✗ Failed to auto-detect scraper: {e}")
    
    print("\n=== Ready to scrape jobs! ===")


if __name__ == "__main__":
    # Run quick start example if module is executed directly
    setup_logging("INFO")
    quick_start_example()