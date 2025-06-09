"""
Scraper factory for creating and managing different job portal scrapers.

This module provides a factory pattern for creating scraper instances based on
platform type or URL analysis. It handles scraper registration, configuration
validation, and automatic platform detection.

Features:
- Factory pattern for scraper creation
- Automatic platform detection from URLs
- Scraper registration and management
- Configuration validation
- Platform-specific optimizations
"""

import logging
import re
from typing import Dict, Any, Optional, Type, List
from urllib.parse import urlparse
from abc import ABC

from app.services.scrapers.base_scraper import BaseScraper
from app.services.scrapers.linkedin_scraper import LinkedInScraper
from app.services.scrapers.indeed_scraper import IndeedScraper
from app.services.scrapers.custom_scraper import CustomScraper
from app.core.exceptions import ScrapingError

logger = logging.getLogger(__name__)


class ScraperFactory:
    """
    Factory class for creating and managing job portal scrapers.
    
    This factory provides a centralized way to create scrapers for different
    job portals, with automatic platform detection and configuration management.
    """
    
    # Registry of available scrapers
    _scrapers: Dict[str, Type[BaseScraper]] = {
        'linkedin': LinkedInScraper,
        'indeed': IndeedScraper,
        'custom': CustomScraper
    }
    
    # URL patterns for automatic platform detection
    _url_patterns = {
        'linkedin': [
            r'.*linkedin\.com.*',
            r'.*linkedin\..*'
        ],
        'indeed': [
            r'.*indeed\.com.*',
            r'.*indeed\..*'
        ]
    }
    
    # Default configurations for each platform
    _default_configs = {
        'linkedin': {
            'rate_limit': 2.0,
            'use_selenium': False,
            'max_retries': 3
        },
        'indeed': {
            'rate_limit': 1.5,
            'use_selenium': False,
            'max_retries': 3
        },
        'custom': {
            'rate_limit': 2.0,
            'use_selenium': False,
            'max_retries': 3
        }
    }
    
    @classmethod
    def get_scraper(cls, platform: str, config: Optional[Dict[str, Any]] = None) -> BaseScraper:
        """
        Get a scraper instance for the specified platform.
        
        Args:
            platform: Platform name (linkedin, indeed, custom)
            config: Optional configuration dictionary
            
        Returns:
            Configured scraper instance
            
        Raises:
            ValueError: If platform is not supported
            ScrapingError: If scraper initialization fails
        """
        platform = platform.lower()
        
        if platform not in cls._scrapers:
            available = ', '.join(cls._scrapers.keys())
            raise ValueError(f"Unsupported platform: {platform}. Available: {available}")
        
        try:
            scraper_class = cls._scrapers[platform]
            
            # Merge default config with provided config
            final_config = cls._default_configs.get(platform, {}).copy()
            if config:
                final_config.update(config)
            
            # Create scraper instance
            if platform == 'custom':
                if not config:
                    raise ValueError("Custom scraper requires configuration")
                return scraper_class(config)
            else:
                scraper = scraper_class()
                # Apply configuration to existing scraper
                for key, value in final_config.items():
                    if hasattr(scraper, key):
                        setattr(scraper, key, value)
                return scraper
                
        except Exception as e:
            logger.error(f"Failed to create {platform} scraper: {str(e)}")
            raise ScrapingError(f"Failed to initialize {platform} scraper: {str(e)}")
    
    @classmethod
    def get_scraper_by_url(cls, url: str, config: Optional[Dict[str, Any]] = None) -> BaseScraper:
        """
        Get a scraper instance based on URL analysis.
        
        Args:
            url: URL to analyze for platform detection
            config: Optional configuration dictionary
            
        Returns:
            Appropriate scraper instance
        """
        platform = cls.detect_platform(url)
        
        if platform == 'custom':
            # For custom platforms, create config from URL if not provided
            if not config:
                config = cls._create_config_from_url(url)
        
        return cls.get_scraper(platform, config)
    
    @classmethod
    def detect_platform(cls, url: str) -> str:
        """
        Detect the platform type from a URL.
        
        Args:
            url: URL to analyze
            
        Returns:
            Platform name (linkedin, indeed, or custom)
        """
        url = url.lower()
        
        for platform, patterns in cls._url_patterns.items():
            for pattern in patterns:
                if re.match(pattern, url):
                    logger.info(f"Detected platform: {platform} for URL: {url}")
                    return platform
        
        logger.info(f"No specific platform detected for URL: {url}, using custom scraper")
        return 'custom'
    
    @classmethod
    def _create_config_from_url(cls, url: str) -> Dict[str, Any]:
        """
        Create a basic configuration for custom scraper from URL.
        
        Args:
            url: URL to create config from
            
        Returns:
            Basic configuration dictionary
        """
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Create basic configuration with common selectors
        config = {
            'base_url': base_url,
            'selectors': {
                'job_cards': '.job, .job-card, .posting, .listing',
                'job_title': '.title, .job-title, h2, h3',
                'company': '.company, .company-name, .employer',
                'location': '.location, .job-location, .city',
                'job_link': 'a[href*="job"], a[href*="position"]',
                'salary': '.salary, .pay, .compensation, .wage'
            },
            'search_params': {
                'path': '/jobs',
                'keywords_param': 'q',
                'location_param': 'location'
            },
            'pagination': {
                'next_button': '.next, .pagination-next, [data-next]',
                'page_param': 'page',
                'max_pages': 5
            }
        }
        
        return config
    
    @classmethod
    def register_scraper(cls, platform: str, scraper_class: Type[BaseScraper],
                        url_patterns: Optional[List[str]] = None,
                        default_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Register a new scraper type with the factory.
        
        Args:
            platform: Platform name
            scraper_class: Scraper class to register
            url_patterns: Optional URL patterns for automatic detection
            default_config: Optional default configuration
        """
        if not issubclass(scraper_class, BaseScraper):
            raise ValueError("Scraper class must inherit from BaseScraper")
        
        cls._scrapers[platform.lower()] = scraper_class
        
        if url_patterns:
            cls._url_patterns[platform.lower()] = url_patterns
        
        if default_config:
            cls._default_configs[platform.lower()] = default_config
        
        logger.info(f"Registered scraper for platform: {platform}")
    
    @classmethod
    def get_available_scrapers(cls) -> List[str]:
        """
        Get list of available scraper platforms.
        
        Returns:
            List of platform names
        """
        return list(cls._scrapers.keys())
    
    @classmethod
    def validate_scraper_config(cls, config: Dict[str, Any]) -> bool:
        """
        Validate scraper configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required fields for custom scraper
            if 'base_url' not in config:
                logger.error("Missing required field: base_url")
                return False
            
            if 'selectors' not in config:
                logger.error("Missing required field: selectors")
                return False
            
            selectors = config['selectors']
            required_selectors = ['job_title', 'company', 'location']
            
            for selector in required_selectors:
                if selector not in selectors:
                    logger.error(f"Missing required selector: {selector}")
                    return False
            
            # Validate URL
            parsed_url = urlparse(config['base_url'])
            if not parsed_url.scheme or not parsed_url.netloc:
                logger.error(f"Invalid base_url: {config['base_url']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating config: {str(e)}")
            return False
    
    @classmethod
    def create_scraper_pool(cls, platforms: List[str], 
                           configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, BaseScraper]:
        """
        Create a pool of scrapers for multiple platforms.
        
        Args:
            platforms: List of platform names
            configs: Optional configurations for each platform
            
        Returns:
            Dictionary mapping platform names to scraper instances
        """
        scraper_pool = {}
        configs = configs or {}
        
        for platform in platforms:
            try:
                config = configs.get(platform)
                scraper = cls.get_scraper(platform, config)
                scraper_pool[platform] = scraper
                logger.info(f"Added {platform} scraper to pool")
            except Exception as e:
                logger.error(f"Failed to create {platform} scraper: {str(e)}")
        
        return scraper_pool
    
    @classmethod
    def get_scraper_for_job_search(cls, search_criteria: Dict[str, Any]) -> List[BaseScraper]:
        """
        Get appropriate scrapers based on job search criteria.
        
        Args:
            search_criteria: Search criteria including platforms preference
            
        Returns:
            List of appropriate scraper instances
        """
        scrapers = []
        
        # Check if specific platforms are requested
        preferred_platforms = search_criteria.get('platforms', ['linkedin', 'indeed'])
        
        for platform in preferred_platforms:
            try:
                scraper = cls.get_scraper(platform)
                scrapers.append(scraper)
            except Exception as e:
                logger.warning(f"Could not create {platform} scraper: {str(e)}")
        
        # If no scrapers created, add default ones
        if not scrapers:
            try:
                scrapers.append(cls.get_scraper('linkedin'))
            except:
                pass
            
            try:
                scrapers.append(cls.get_scraper('indeed'))
            except:
                pass
        
        return scrapers
    
    @classmethod
    def test_scraper_connectivity(cls, platform: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Test connectivity and basic functionality of a scraper.
        
        Args:
            platform: Platform to test
            config: Optional configuration
            
        Returns:
            Test results dictionary
        """
        test_results = {
            'platform': platform,
            'success': False,
            'error': None,
            'response_time': None,
            'features_working': {}
        }
        
        try:
            import time
            start_time = time.time()
            
            # Create scraper
            scraper = cls.get_scraper(platform, config)
            
            # Test basic functionality
            if hasattr(scraper, 'build_search_url'):
                test_url = scraper.build_search_url("test")
                test_results['features_working']['url_building'] = bool(test_url)
            
            # Test page fetching (if not rate-limited)
            if platform == 'custom' and config:
                # For custom scrapers, test the selectors
                if hasattr(scraper, 'test_selectors'):
                    selector_results = scraper.test_selectors()
                    test_results['features_working']['selectors'] = 'error' not in selector_results
            
            test_results['response_time'] = time.time() - start_time
            test_results['success'] = True
            
        except Exception as e:
            test_results['error'] = str(e)
            logger.error(f"Scraper connectivity test failed for {platform}: {str(e)}")
        
        return test_results
    
    @classmethod
    def get_optimal_scraper_config(cls, platform: str, job_volume: str = "medium") -> Dict[str, Any]:
        """
        Get optimized configuration for a platform based on expected job volume.
        
        Args:
            platform: Platform name
            job_volume: Expected volume (low, medium, high)
            
        Returns:
            Optimized configuration dictionary
        """
        base_config = cls._default_configs.get(platform, {}).copy()
        
        # Adjust settings based on volume
        if job_volume == "low":
            base_config['rate_limit'] = base_config.get('rate_limit', 2.0) * 0.5
            base_config['max_retries'] = 5
        elif job_volume == "high":
            base_config['rate_limit'] = base_config.get('rate_limit', 2.0) * 2
            base_config['max_retries'] = 2
            base_config['use_selenium'] = False  # Faster without selenium
        
        return base_config