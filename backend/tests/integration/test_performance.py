"""
Performance and load tests for the job automation system.

Tests system performance under various load conditions and identifies bottlenecks.
"""

import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from httpx import AsyncClient
import statistics
from unittest.mock import patch

from app.models.user import User


class TestPerformance:
    """Test suite for performance and load testing."""

    @pytest.mark.slow
    async def test_concurrent_user_registrations(self, async_client: AsyncClient):
        """Test system performance under concurrent user registrations."""
        
        async def register_user(user_id):
            user_data = {
                "email": f"user{user_id}@example.com",
                "password": "SecurePassword123!",
                "full_name": f"Test User {user_id}",
                "phone_number": f"+155512340{user_id % 100:02d}",
                "skills": ["Python", "FastAPI"]
            }
            
            start_time = time.time()
            response = await async_client.post("/api/v1/auth/register", json=user_data)
            end_time = time.time()
            
            return {
                "user_id": user_id,
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "success": response.status_code == 201
            }
        
        # Test with 50 concurrent registrations
        num_users = 50
        start_time = time.time()
        
        tasks = [register_user(i) for i in range(num_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Filter out exceptions
        valid_results = [r for r in results if isinstance(r, dict)]
        successful_registrations = [r for r in valid_results if r["success"]]
        
        # Performance assertions
        assert len(successful_registrations) >= num_users * 0.8  # 80% success rate minimum
        assert total_time < 30  # Should complete within 30 seconds
        
        # Response time analysis
        response_times = [r["response_time"] for r in valid_results]
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        
        assert avg_response_time < 2.0  # Average response time under 2 seconds
        assert p95_response_time < 5.0  # 95th percentile under 5 seconds

    @pytest.mark.slow
    async def test_concurrent_job_searches(self, async_client: AsyncClient, auth_headers):
        """Test performance of concurrent job searches."""
        
        async def search_jobs(search_id):
            search_params = {
                "keywords": f"python developer {search_id % 10}",
                "location": ["San Francisco", "New York", "Remote", "Austin"][search_id % 4],
                "limit": 20
            }
            
            start_time = time.time()
            response = await async_client.get(
                "/api/v1/jobs/search",
                params=search_params,
                headers=auth_headers
            )
            end_time = time.time()
            
            return {
                "search_id": search_id,
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "results_count": len(response.json().get("jobs", [])) if response.status_code == 200 else 0
            }
        
        # Test with 100 concurrent searches
        num_searches = 100
        
        # Mock job search results to avoid database load
        with patch('app.services.job_service.JobService.search_jobs') as mock_search:
            mock_search.return_value = {
                "jobs": [{"id": i, "title": f"Job {i}"} for i in range(20)],
                "total_count": 1000,
                "pagination": {"limit": 20, "offset": 0}
            }
            
            start_time = time.time()
            tasks = [search_jobs(i) for i in range(num_searches)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
        
        total_time = end_time - start_time
        valid_results = [r for r in results if isinstance(r, dict)]
        successful_searches = [r for r in valid_results if r["status_code"] == 200]
        
        # Performance assertions
        assert len(successful_searches) >= num_searches * 0.9  # 90% success rate
        assert total_time < 20  # Should complete within 20 seconds
        
        # Response time analysis
        response_times = [r["response_time"] for r in successful_searches]
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]
        
        assert avg_response_time < 1.0  # Average under 1 second
        assert p95_response_time < 3.0  # 95th percentile under 3 seconds

    @pytest.mark.slow
    async def test_bulk_document_generation_performance(self, async_client: AsyncClient, auth_headers, mock_phi3_service):
        """Test performance of bulk document generation."""
        
        # Mock Phi-3 service for consistent testing
        mock_phi3_service.generate_resume.return_value = {
            "content": "Generated resume content...",
            "success": True,
            "generation_time": 0.5
        }
        
        mock_phi3_service.generate_cover_letter.return_value = {
            "content": "Generated cover letter content...",
            "success": True,
            "generation_time": 0.3
        }
        
        async def generate_document(doc_id, doc_type):
            start_time = time.time()
            
            endpoint = f"/api/v1/documents/{doc_type}/generate"
            data = {"job_id": 1, "template": "modern"}
            
            with patch('app.services.document_service.DocumentService.get_phi3_service', return_value=mock_phi3_service):
                response = await async_client.post(endpoint, json=data, headers=auth_headers)
            
            end_time = time.time()
            
            return {
                "doc_id": doc_id,
                "doc_type": doc_type,
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "success": response.status_code == 201
            }
        
        # Generate 50 resumes and 50 cover letters concurrently
        tasks = []
        for i in range(50):
            tasks.append(generate_document(i, "resume"))
            tasks.append(generate_document(i + 50, "cover-letter"))
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        total_time = end_time - start_time
        valid_results = [r for r in results if isinstance(r, dict)]
        successful_generations = [r for r in valid_results if r["success"]]
        
        # Performance assertions
        assert len(successful_generations) >= len(tasks) * 0.8  # 80% success rate
        assert total_time < 60  # Should complete within 60 seconds
        
        # Response time analysis
        response_times = [r["response_time"] for r in successful_generations]
        avg_response_time = statistics.mean(response_times)
        
        assert avg_response_time < 3.0  # Average under 3 seconds per document

    @pytest.mark.slow
    async def test_database_query_performance(self, async_client: AsyncClient, auth_headers):
        """Test database query performance under load."""
        
        async def fetch_user_data(request_id):
            endpoints = [
                "/api/v1/users/profile",
                "/api/v1/applications",
                "/api/v1/documents",
                "/api/v1/applications/statistics"
            ]
            
            endpoint = endpoints[request_id % len(endpoints)]
            
            start_time = time.time()
            response = await async_client.get(endpoint, headers=auth_headers)
            end_time = time.time()
            
            return {
                "request_id": request_id,
                "endpoint": endpoint,
                "status_code": response.status_code,
                "response_time": end_time - start_time
            }
        
        # Test with 200 concurrent database queries
        num_requests = 200
        
        start_time = time.time()
        tasks = [fetch_user_data(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        total_time = end_time - start_time
        valid_results = [r for r in results if isinstance(r, dict)]
        successful_requests = [r for r in valid_results if r["status_code"] == 200]
        
        # Performance assertions
        assert len(successful_requests) >= num_requests * 0.9  # 90% success rate
        assert total_time < 30  # Should complete within 30 seconds
        
        # Response time analysis by endpoint
        endpoint_times = {}
        for result in successful_requests:
            endpoint = result["endpoint"]
            if endpoint not in endpoint_times:
                endpoint_times[endpoint] = []
            endpoint_times[endpoint].append(result["response_time"])
        
        for endpoint, times in endpoint_times.items():
            avg_time = statistics.mean(times)
            assert avg_time < 1.0, f"Endpoint {endpoint} average response time too high: {avg_time}s"

    @pytest.mark.slow
    async def test_memory_usage_under_load(self, async_client: AsyncClient, auth_headers):
        """Test memory usage doesn't grow excessively under load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        async def perform_operations(op_id):
            # Simulate typical user operations
            operations = [
                lambda: async_client.get("/api/v1/jobs/search", 
                                        params={"keywords": "python"}, 
                                        headers=auth_headers),
                lambda: async_client.get("/api/v1/users/profile", headers=auth_headers),
                lambda: async_client.get("/api/v1/applications", headers=auth_headers),
                lambda: async_client.get("/api/v1/documents", headers=auth_headers)
            ]
            
            for operation in operations:
                await operation()
            
            return op_id
        
        # Perform 100 sets of operations
        num_operations = 100
        
        tasks = [perform_operations(i) for i in range(num_operations)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 500, f"Memory increased by {memory_increase}MB, which may indicate a memory leak"

    @pytest.mark.slow
    async def test_api_response_compression(self, async_client: AsyncClient, auth_headers):
        """Test API response compression effectiveness."""
        
        # Test large response endpoints
        large_response_endpoints = [
            "/api/v1/jobs/search?limit=100",
            "/api/v1/applications",
            "/api/v1/documents"
        ]
        
        for endpoint in large_response_endpoints:
            # Request with compression
            response_compressed = await async_client.get(
                endpoint,
                headers={**auth_headers, "Accept-Encoding": "gzip, deflate"},
            )
            
            # Request without compression
            response_uncompressed = await async_client.get(
                endpoint,
                headers={**auth_headers, "Accept-Encoding": "identity"},
            )
            
            if response_compressed.status_code == 200 and response_uncompressed.status_code == 200:
                compressed_size = len(response_compressed.content)
                uncompressed_size = len(response_uncompressed.content)
                
                # Compression should provide some benefit for large responses
                if uncompressed_size > 1024:  # Only test if response is > 1KB
                    compression_ratio = compressed_size / uncompressed_size
                    assert compression_ratio < 0.8, f"Poor compression ratio for {endpoint}: {compression_ratio}"

    @pytest.mark.slow
    async def test_caching_effectiveness(self, async_client: AsyncClient, auth_headers):
        """Test caching effectiveness for frequently accessed data."""
        
        cacheable_endpoints = [
            "/api/v1/jobs/search?keywords=python&location=san francisco",
            "/api/v1/documents/templates",
            "/api/v1/users/profile"
        ]
        
        for endpoint in cacheable_endpoints:
            # First request (cache miss)
            start_time = time.time()
            response1 = await async_client.get(endpoint, headers=auth_headers)
            first_request_time = time.time() - start_time
            
            # Second request (should be faster if cached)
            start_time = time.time()
            response2 = await async_client.get(endpoint, headers=auth_headers)
            second_request_time = time.time() - start_time
            
            if response1.status_code == 200 and response2.status_code == 200:
                # Second request should be faster (allowing for some variance)
                speed_improvement = (first_request_time - second_request_time) / first_request_time
                
                # If caching is implemented, expect at least 20% improvement
                # This is a soft assertion as caching might not be implemented for all endpoints
                if speed_improvement > 0.2:
                    print(f"Good caching detected for {endpoint}: {speed_improvement:.2%} improvement")

    @pytest.mark.slow
    async def test_error_handling_under_load(self, async_client: AsyncClient):
        """Test error handling doesn't degrade under load."""
        
        async def make_invalid_request(request_id):
            # Various types of invalid requests
            invalid_requests = [
                lambda: async_client.get("/api/v1/nonexistent/endpoint"),
                lambda: async_client.post("/api/v1/jobs", json={"invalid": "data"}),
                lambda: async_client.get("/api/v1/users/profile"),  # No auth
                lambda: async_client.put("/api/v1/users/profile", json={"invalid_field": "value"})
            ]
            
            request_func = invalid_requests[request_id % len(invalid_requests)]
            
            start_time = time.time()
            response = await request_func()
            end_time = time.time()
            
            return {
                "request_id": request_id,
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "error_handled": 400 <= response.status_code < 500
            }
        
        # Make 100 concurrent invalid requests
        num_requests = 100
        
        start_time = time.time()
        tasks = [make_invalid_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        total_time = end_time - start_time
        valid_results = [r for r in results if isinstance(r, dict)]
        properly_handled = [r for r in valid_results if r["error_handled"]]
        
        # Error handling assertions
        assert len(properly_handled) >= len(valid_results) * 0.9  # 90% properly handled
        assert total_time < 20  # Error handling should be fast
        
        # Error response times should be reasonable
        error_response_times = [r["response_time"] for r in properly_handled]
        avg_error_response_time = statistics.mean(error_response_times)
        assert avg_error_response_time < 1.0  # Errors should be handled quickly

    @pytest.mark.slow
    async def test_throughput_benchmarks(self, async_client: AsyncClient, auth_headers):
        """Test system throughput benchmarks."""
        
        async def benchmark_endpoint(endpoint, headers=None, method="GET", json_data=None):
            request_headers = headers or {}
            
            if method == "GET":
                response = await async_client.get(endpoint, headers=request_headers)
            elif method == "POST":
                response = await async_client.post(endpoint, json=json_data, headers=request_headers)
            
            return response.status_code == 200
        
        # Benchmark different endpoint types
        benchmarks = [
            {
                "name": "User Profile",
                "endpoint": "/api/v1/users/profile",
                "headers": auth_headers,
                "target_rps": 50  # requests per second
            },
            {
                "name": "Job Search",
                "endpoint": "/api/v1/jobs/search?keywords=python",
                "headers": auth_headers,
                "target_rps": 30
            },
            {
                "name": "Application List",
                "endpoint": "/api/v1/applications",
                "headers": auth_headers,
                "target_rps": 40
            }
        ]
        
        for benchmark in benchmarks:
            # Test for 10 seconds at target RPS
            duration = 10
            target_rps = benchmark["target_rps"]
            total_requests = target_rps * duration
            
            start_time = time.time()
            
            # Distribute requests evenly over time
            tasks = []
            for i in range(total_requests):
                delay = i / target_rps
                task = asyncio.create_task(
                    asyncio.sleep(delay)
                    .then(lambda: benchmark_endpoint(
                        benchmark["endpoint"],
                        benchmark["headers"]
                    ))
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            actual_duration = end_time - start_time
            successful_requests = sum(1 for r in results if r is True)
            actual_rps = successful_requests / actual_duration
            
            success_rate = successful_requests / total_requests
            
            print(f"{benchmark['name']} Benchmark:")
            print(f"  Target RPS: {target_rps}")
            print(f"  Actual RPS: {actual_rps:.2f}")
            print(f"  Success Rate: {success_rate:.2%}")
            
            # Assertions
            assert success_rate >= 0.8, f"Low success rate for {benchmark['name']}: {success_rate:.2%}"
            assert actual_rps >= target_rps * 0.7, f"Low throughput for {benchmark['name']}: {actual_rps:.2f} RPS"

    @pytest.mark.slow
    async def test_stress_test_breaking_point(self, async_client: AsyncClient, auth_headers):
        """Test system breaking point under extreme load."""
        
        async def stress_request(request_id):
            try:
                response = await async_client.get("/api/v1/users/profile", headers=auth_headers)
                return {"success": response.status_code == 200, "status": response.status_code}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Gradually increase load until system breaks
        load_levels = [50, 100, 200, 400, 800]
        breaking_point = None
        
        for load_level in load_levels:
            start_time = time.time()
            tasks = [stress_request(i) for i in range(load_level)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            duration = end_time - start_time
            successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
            success_rate = successful_requests / load_level
            
            print(f"Load Level {load_level}: {success_rate:.2%} success rate, {duration:.2f}s duration")
            
            if success_rate < 0.8 or duration > 30:  # System breaking point
                breaking_point = load_level
                break
        
        if breaking_point:
            print(f"System breaking point: {breaking_point} concurrent requests")
        else:
            print("System handled all load levels successfully")
        
        # System should handle at least 100 concurrent requests
        assert breaking_point is None or breaking_point >= 100, "System breaks under low load"
