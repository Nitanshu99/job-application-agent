"""
Unit tests for web scraping services.

Tests job scraping from various portals including LinkedIn, Indeed, and custom sites.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from bs4 import BeautifulSoup
import requests
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By

from app.services.scrapers.base_scraper import BaseScraper
from app.services.scrapers.linkedin_scraper import LinkedInScraper
from app.services.scrapers.indeed_scraper import IndeedScraper
from app.services.scrapers.custom_scraper import CustomScraper
from app.services.scrapers.scraper_factory import ScraperFactory
from app.core.exceptions import ScrapingError, RateLimitError


class TestBaseScraper:
    """Test suite for BaseScraper class."""

    @pytest.fixture
    def base_scraper(self):
        """Create BaseScraper instance for testing."""
        return BaseScraper(base_url="https://example.com")

    @pytest.fixture
    def mock_html_content(self):
        """Mock HTML content for testing."""
        return """
        <html>
            <body>
                <div class="job-card">
                    <h3 class="job-title">Software Engineer</h3>
                    <p class="company">TechCorp</p>
                    <span class="location">San Francisco, CA</span>
                    <a href="/job/123" class="job-link">View Job</a>
                </div>
            </body>
        </html>
        """

    def test_init_base_scraper(self, base_scraper):
        """Test BaseScraper initialization."""
        assert base_scraper.base_url == "https://example.com"
        assert base_scraper.rate_limit == 1.0  # Default rate limit
        assert base_scraper.headers is not None

    @patch('requests.get')
    def test_fetch_page_success(self, mock_get, base_scraper, mock_html_content):
        """Test successful page fetching."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html_content
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Call method
        result = base_scraper.fetch_page("https://example.com/jobs")
        
        # Assertions
        assert result == mock_html_content
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_fetch_page_404_error(self, mock_get, base_scraper):
        """Test page fetching with 404 error."""
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.RequestException("404 Not Found")
        mock_get.return_value = mock_response
        
        # Should raise ScrapingError
        with pytest.raises(ScrapingError):
            base_scraper.fetch_page("https://example.com/nonexistent")

    @patch('requests.get')
    def test_fetch_page_rate_limit(self, mock_get, base_scraper):
        """Test page fetching with rate limit response."""
        # Mock rate limit response
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.RequestException("Too Many Requests")
        mock_get.return_value = mock_response
        
        # Should raise RateLimitError
        with pytest.raises(RateLimitError):
            base_scraper.fetch_page("https://example.com/jobs")

    def test_parse_html(self, base_scraper, mock_html_content):
        """Test HTML parsing."""
        soup = base_scraper.parse_html(mock_html_content)
        
        assert isinstance(soup, BeautifulSoup)
        assert soup.find('h3', class_='job-title').text == "Software Engineer"

    def test_extract_text_content(self, base_scraper):
        """Test text extraction from HTML elements."""
        html = '<div class="test">Hello <span>World</span>!</div>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.find('div')
        
        text = base_scraper.extract_text(element)
        assert text == "Hello World!"

    def test_extract_text_with_none(self, base_scraper):
        """Test text extraction with None element."""
        text = base_scraper.extract_text(None)
        assert text == ""

    def test_clean_url(self, base_scraper):
        """Test URL cleaning and normalization."""
        # Test relative URL
        relative_url = "/job/123"
        cleaned = base_scraper.clean_url(relative_url)
        assert cleaned == "https://example.com/job/123"
        
        # Test absolute URL
        absolute_url = "https://other.com/job/456"
        cleaned = base_scraper.clean_url(absolute_url)
        assert cleaned == "https://other.com/job/456"

    @patch('time.sleep')
    def test_rate_limiting(self, mock_sleep, base_scraper):
        """Test rate limiting functionality."""
        base_scraper.rate_limit = 2.0  # 2 second delay
        
        base_scraper.apply_rate_limit()
        
        mock_sleep.assert_called_once_with(2.0)


class TestLinkedInScraper:
    """Test suite for LinkedInScraper class."""

    @pytest.fixture
    def linkedin_scraper(self):
        """Create LinkedInScraper instance for testing."""
        return LinkedInScraper()

    @pytest.fixture
    def linkedin_job_html(self):
        """Mock LinkedIn job listing HTML."""
        return """
        <div class="base-card relative w-full hover:no-underline">
            <h3 class="base-search-card__title">Senior Software Engineer</h3>
            <h4 class="base-search-card__subtitle">TechCorp</h4>
            <span class="job-search-card__location">San Francisco, CA</span>
            <a href="/jobs/view/123456789" class="base-card__full-link"></a>
            <time datetime="2024-01-15">2024-01-15</time>
        </div>
        """

    @patch('app.services.scrapers.linkedin_scraper.LinkedInScraper.fetch_page')
    def test_scrape_jobs_success(self, mock_fetch, linkedin_scraper, linkedin_job_html):
        """Test successful LinkedIn job scraping."""
        # Mock page content
        mock_fetch.return_value = f"<html><body>{linkedin_job_html}</body></html>"
        
        # Call scraping method
        jobs = linkedin_scraper.scrape_jobs("python developer", location="San Francisco", limit=1)
        
        # Assertions
        assert len(jobs) == 1
        job = jobs[0]
        assert job["title"] == "Senior Software Engineer"
        assert job["company"] == "TechCorp"
        assert job["location"] == "San Francisco, CA"
        assert "linkedin.com" in job["url"]

    def test_parse_job_card(self, linkedin_scraper, linkedin_job_html):
        """Test parsing individual LinkedIn job card."""
        soup = BeautifulSoup(linkedin_job_html, 'html.parser')
        job_card = soup.find('div', class_='base-card')
        
        job_data = linkedin_scraper.parse_job_card(job_card)
        
        assert job_data["title"] == "Senior Software Engineer"
        assert job_data["company"] == "TechCorp"
        assert job_data["location"] == "San Francisco, CA"

    @patch('selenium.webdriver.Chrome')
    def test_scrape_with_selenium(self, mock_chrome_class, linkedin_scraper):
        """Test scraping with Selenium for dynamic content."""
        # Mock WebDriver
        mock_driver = MagicMock()
        mock_chrome_class.return_value = mock_driver
        
        # Mock page source
        mock_driver.page_source = "<html><body>Dynamic content</body></html>"
        
        # Mock elements
        mock_element = MagicMock()
        mock_element.text = "Senior Developer"
        mock_driver.find_elements.return_value = [mock_element]
        
        linkedin_scraper.use_selenium = True
        result = linkedin_scraper.scrape_jobs_dynamic("python", limit=1)
        
        assert len(result) >= 0  # Should not error
        mock_driver.quit.assert_called_once()

    def test_build_search_url(self, linkedin_scraper):
        """Test LinkedIn search URL building."""
        url = linkedin_scraper.build_search_url("python developer", "San Francisco")
        
        assert "linkedin.com/jobs/search" in url
        assert "keywords=python%20developer" in url
        assert "location=San%20Francisco" in url

    def test_extract_job_id(self, linkedin_scraper):
        """Test extracting job ID from LinkedIn URL."""
        url = "https://www.linkedin.com/jobs/view/123456789"
        job_id = linkedin_scraper.extract_job_id(url)
        
        assert job_id == "123456789"

    @patch('app.services.scrapers.linkedin_scraper.LinkedInScraper.fetch_page')
    def test_get_job_details(self, mock_fetch, linkedin_scraper):
        """Test getting detailed job information."""
        job_detail_html = """
        <div class="description__text">
            <p>We are looking for a senior software engineer...</p>
            <ul>
                <li>5+ years experience</li>
                <li>Python expertise</li>
            </ul>
        </div>
        """
        mock_fetch.return_value = f"<html><body>{job_detail_html}</body></html>"
        
        details = linkedin_scraper.get_job_details("123456789")
        
        assert "We are looking for" in details["description"]
        assert len(details["requirements"]) >= 0


class TestIndeedScraper:
    """Test suite for IndeedScraper class."""

    @pytest.fixture
    def indeed_scraper(self):
        """Create IndeedScraper instance for testing."""
        return IndeedScraper()

    @pytest.fixture
    def indeed_job_html(self):
        """Mock Indeed job listing HTML."""
        return """
        <div class="job_seen_beacon">
            <h2 class="jobTitle">
                <a href="/viewjob?jk=abc123" data-jk="abc123">
                    <span title="Python Developer">Python Developer</span>
                </a>
            </h2>
            <span class="companyName">DataCorp</span>
            <div class="companyLocation">Austin, TX</div>
            <div class="salary-snippet">$80,000 - $120,000 a year</div>
            <div class="summary">Build scalable data pipelines...</div>
        </div>
        """

    @patch('app.services.scrapers.indeed_scraper.IndeedScraper.fetch_page')
    def test_scrape_indeed_jobs(self, mock_fetch, indeed_scraper, indeed_job_html):
        """Test scraping jobs from Indeed."""
        mock_fetch.return_value = f"<html><body>{indeed_job_html}</body></html>"
        
        jobs = indeed_scraper.scrape_jobs("python", location="Austin", limit=1)
        
        assert len(jobs) == 1
        job = jobs[0]
        assert job["title"] == "Python Developer"
        assert job["company"] == "DataCorp"
        assert job["location"] == "Austin, TX"

    def test_parse_salary(self, indeed_scraper):
        """Test salary parsing from Indeed format."""
        # Test yearly range
        salary_text = "$80,000 - $120,000 a year"
        min_sal, max_sal = indeed_scraper.parse_salary(salary_text)
        assert min_sal == 80000
        assert max_sal == 120000
        
        # Test hourly rate
        hourly_text = "$25 - $35 an hour"
        min_sal, max_sal = indeed_scraper.parse_salary(hourly_text)
        assert min_sal == 52000  # Approximate yearly conversion
        assert max_sal == 72800

    def test_build_indeed_search_url(self, indeed_scraper):
        """Test Indeed search URL building."""
        url = indeed_scraper.build_search_url("data scientist", "New York")
        
        assert "indeed.com/jobs" in url
        assert "q=data%20scientist" in url
        assert "l=New%20York" in url

    def test_extract_job_key(self, indeed_scraper):
        """Test extracting job key from Indeed URL."""
        url = "/viewjob?jk=abc123&from=serp"
        job_key = indeed_scraper.extract_job_key(url)
        
        assert job_key == "abc123"


class TestCustomScraper:
    """Test suite for CustomScraper class."""

    @pytest.fixture
    def custom_scraper(self):
        """Create CustomScraper instance for testing."""
        config = {
            "base_url": "https://careers.example.com",
            "selectors": {
                "job_title": ".job-title",
                "company": ".company-name",
                "location": ".job-location",
                "job_link": ".job-link"
            },
            "pagination": {
                "next_button": ".next-page",
                "page_param": "page"
            }
        }
        return CustomScraper(config)

    @pytest.fixture
    def custom_job_html(self):
        """Mock custom site job listing HTML."""
        return """
        <div class="job-listing">
            <h2 class="job-title">Full Stack Developer</h2>
            <div class="company-name">StartupXYZ</div>
            <span class="job-location">Remote</span>
            <a href="/careers/job/456" class="job-link">Apply Now</a>
            <div class="job-summary">Join our engineering team...</div>
        </div>
        """

    @patch('app.services.scrapers.custom_scraper.CustomScraper.fetch_page')
    def test_scrape_custom_site(self, mock_fetch, custom_scraper, custom_job_html):
        """Test scraping from custom company website."""
        mock_fetch.return_value = f"<html><body>{custom_job_html}</body></html>"
        
        jobs = custom_scraper.scrape_jobs(limit=1)
        
        assert len(jobs) == 1
        job = jobs[0]
        assert job["title"] == "Full Stack Developer"
        assert job["company"] == "StartupXYZ"
        assert job["location"] == "Remote"

    def test_apply_selectors(self, custom_scraper, custom_job_html):
        """Test applying CSS selectors to extract job data."""
        soup = BeautifulSoup(custom_job_html, 'html.parser')
        
        job_data = custom_scraper.apply_selectors(soup)
        
        assert job_data["job_title"] == "Full Stack Developer"
        assert job_data["company"] == "StartupXYZ"
        assert job_data["location"] == "Remote"

    def test_handle_pagination(self, custom_scraper):
        """Test pagination handling for multi-page results."""
        with patch.object(custom_scraper, 'fetch_page') as mock_fetch:
            # Mock first page with next button
            page1_html = """
            <div class="job-listing">Job 1</div>
            <a href="/careers?page=2" class="next-page">Next</a>
            """
            
            # Mock second page without next button
            page2_html = """
            <div class="job-listing">Job 2</div>
            """
            
            mock_fetch.side_effect = [page1_html, page2_html]
            
            pages = custom_scraper.get_all_pages()
            
            assert len(pages) == 2
            assert mock_fetch.call_count == 2

    def test_validate_config(self, custom_scraper):
        """Test configuration validation."""
        # Valid config should not raise
        custom_scraper.validate_config()
        
        # Invalid config should raise
        invalid_scraper = CustomScraper({})
        with pytest.raises(ValueError):
            invalid_scraper.validate_config()


class TestScraperFactory:
    """Test suite for ScraperFactory class."""

    def test_get_linkedin_scraper(self):
        """Test getting LinkedIn scraper from factory."""
        scraper = ScraperFactory.get_scraper("linkedin")
        
        assert isinstance(scraper, LinkedInScraper)

    def test_get_indeed_scraper(self):
        """Test getting Indeed scraper from factory."""
        scraper = ScraperFactory.get_scraper("indeed")
        
        assert isinstance(scraper, IndeedScraper)

    def test_get_custom_scraper(self):
        """Test getting custom scraper from factory."""
        config = {
            "base_url": "https://example.com",
            "selectors": {"job_title": ".title"}
        }
        
        scraper = ScraperFactory.get_scraper("custom", config=config)
        
        assert isinstance(scraper, CustomScraper)

    def test_get_scraper_by_url(self):
        """Test getting scraper based on URL."""
        # LinkedIn URL
        linkedin_scraper = ScraperFactory.get_scraper_by_url("https://www.linkedin.com/jobs")
        assert isinstance(linkedin_scraper, LinkedInScraper)
        
        # Indeed URL
        indeed_scraper = ScraperFactory.get_scraper_by_url("https://www.indeed.com/jobs")
        assert isinstance(indeed_scraper, IndeedScraper)
        
        # Custom URL
        custom_scraper = ScraperFactory.get_scraper_by_url("https://careers.company.com")
        assert isinstance(custom_scraper, CustomScraper)

    def test_get_unknown_scraper(self):
        """Test getting unknown scraper type."""
        with pytest.raises(ValueError):
            ScraperFactory.get_scraper("unknown_platform")

    def test_register_custom_scraper(self):
        """Test registering new scraper type."""
        class TestScraper(BaseScraper):
            def scrape_jobs(self, *args, **kwargs):
                return []
        
        ScraperFactory.register_scraper("test_platform", TestScraper)
        
        scraper = ScraperFactory.get_scraper("test_platform")
        assert isinstance(scraper, TestScraper)

    def test_get_available_scrapers(self):
        """Test getting list of available scrapers."""
        scrapers = ScraperFactory.get_available_scrapers()
        
        assert "linkedin" in scrapers
        assert "indeed" in scrapers
        assert "custom" in scrapers

    def test_scraper_config_validation(self):
        """Test scraper configuration validation."""
        # Valid config
        valid_config = {
            "base_url": "https://example.com",
            "selectors": {"job_title": ".title"},
            "rate_limit": 1.0
        }
        
        is_valid = ScraperFactory.validate_scraper_config(valid_config)
        assert is_valid is True
        
        # Invalid config - missing required fields
        invalid_config = {"base_url": "https://example.com"}
        
        is_valid = ScraperFactory.validate_scraper_config(invalid_config)
        assert is_valid is False


class TestScrapingIntegration:
    """Integration tests for scraping workflow."""

    @pytest.fixture
    def mock_scrapers(self):
        """Mock all scrapers for integration testing."""
        linkedin_mock = MagicMock()
        linkedin_mock.scrape_jobs.return_value = [
            {"title": "Python Dev", "company": "LinkedIn Corp", "source": "linkedin"}
        ]
        
        indeed_mock = MagicMock()
        indeed_mock.scrape_jobs.return_value = [
            {"title": "JS Dev", "company": "Indeed Inc", "source": "indeed"}
        ]
        
        return {"linkedin": linkedin_mock, "indeed": indeed_mock}

    def test_multi_platform_scraping(self, mock_scrapers):
        """Test scraping from multiple platforms simultaneously."""
        with patch.object(ScraperFactory, 'get_scraper') as mock_get:
            def side_effect(platform):
                return mock_scrapers[platform]
            
            mock_get.side_effect = side_effect
            
            # Simulate scraping from multiple platforms
            platforms = ["linkedin", "indeed"]
            all_jobs = []
            
            for platform in platforms:
                scraper = ScraperFactory.get_scraper(platform)
                jobs = scraper.scrape_jobs("developer", limit=10)
                all_jobs.extend(jobs)
            
            assert len(all_jobs) == 2
            assert any(job["source"] == "linkedin" for job in all_jobs)
            assert any(job["source"] == "indeed" for job in all_jobs)

    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_rate_limiting_across_requests(self, mock_sleep):
        """Test that rate limiting is properly applied across multiple requests."""
        scraper = BaseScraper("https://example.com")
        scraper.rate_limit = 0.5
        
        # Make multiple requests
        for _ in range(3):
            scraper.apply_rate_limit()
        
        # Should have called sleep 3 times
        assert mock_sleep.call_count == 3

    def test_error_handling_in_scraping_pipeline(self):
        """Test error handling throughout scraping pipeline."""
        with patch('requests.get') as mock_get:
            # First request succeeds, second fails
            mock_get.side_effect = [
                MagicMock(status_code=200, text="<html>Success</html>"),
                requests.RequestException("Network error")
            ]
            
            scraper = BaseScraper("https://example.com")
            
            # First request should succeed
            result1 = scraper.fetch_page("https://example.com/page1")
            assert "Success" in result1
            
            # Second request should raise error
            with pytest.raises(ScrapingError):
                scraper.fetch_page("https://example.com/page2")
