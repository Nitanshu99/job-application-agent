#!/usr/bin/env python3
"""
System health check utility for the Job Automation System.
Monitors all services including database, Redis, LLM models, and API endpoints.
"""

import sys
import asyncio
import logging
import time
import json
import docker
from pathlib import Path
from typing import Dict, List, Optional, Any
import click
import httpx
import psycopg2
import redis
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.core.config import get_settings
from app.core.logging import setup_logging

# Setup logging
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    """Service health information."""
    name: str
    status: HealthStatus
    response_time: float
    message: str
    details: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.details is None:
            self.details = {}


class HealthChecker:
    """Comprehensive health checker for all system components."""
    
    def __init__(self, settings=None, timeout: int = 10):
        self.settings = settings or get_settings()
        self.timeout = timeout
        self.docker_client = None
        
        # Try to initialize Docker client
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"Could not connect to Docker: {e}")

    async def check_database(self) -> ServiceHealth:
        """Check PostgreSQL database health."""
        start_time = time.time()
        
        try:
            # Parse database URL
            db_url = self.settings.DATABASE_URL
            if db_url.startswith('postgresql://'):
                # Extract connection parameters
                url_parts = db_url.replace('postgresql://', '').split('@')
                user_pass, host_db = url_parts
                username, password = user_pass.split(':')
                host_port, database = host_db.split('/')
                
                if ':' in host_port:
                    host, port = host_port.split(':')
                else:
                    host, port = host_port, 5432
                
                # Test connection
                conn = psycopg2.connect(
                    host=host,
                    port=int(port),
                    database=database,
                    user=username,
                    password=password,
                    connect_timeout=self.timeout
                )
                
                # Test query
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version(), current_database(), NOW()")
                    result = cursor.fetchone()
                    
                    # Get additional stats
                    cursor.execute("""
                        SELECT 
                            pg_database_size(current_database()) as db_size,
                            (SELECT count(*) FROM information_schema.tables 
                             WHERE table_schema = 'public') as table_count
                    """)
                    stats = cursor.fetchone()
                
                conn.close()
                
                response_time = time.time() - start_time
                
                return ServiceHealth(
                    name="PostgreSQL Database",
                    status=HealthStatus.HEALTHY,
                    response_time=response_time,
                    message="Database connection successful",
                    details={
                        "version": result[0].split(' ')[1],
                        "database": result[1],
                        "size_bytes": stats[0],
                        "table_count": stats[1],
                        "timestamp": result[2].isoformat()
                    }
                )
            
        except Exception as e:
            response_time = time.time() - start_time
            return ServiceHealth(
                name="PostgreSQL Database",
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message=f"Database connection failed: {str(e)}"
            )

    async def check_redis(self) -> ServiceHealth:
        """Check Redis cache health."""
        start_time = time.time()
        
        try:
            # Parse Redis URL
            redis_url = self.settings.REDIS_URL
            r = redis.from_url(redis_url, socket_timeout=self.timeout)
            
            # Test connection
            ping_result = r.ping()
            
            # Get Redis info
            info = r.info()
            
            # Test set/get operation
            test_key = "health_check_test"
            test_value = f"test_{int(time.time())}"
            r.set(test_key, test_value, ex=60)  # Expire in 60 seconds
            retrieved_value = r.get(test_key)
            
            if retrieved_value.decode() != test_value:
                raise Exception("Redis set/get test failed")
            
            # Clean up test key
            r.delete(test_key)
            
            response_time = time.time() - start_time
            
            return ServiceHealth(
                name="Redis Cache",
                status=HealthStatus.HEALTHY,
                response_time=response_time,
                message="Redis connection successful",
                details={
                    "version": info.get("redis_version"),
                    "mode": info.get("redis_mode"),
                    "used_memory": info.get("used_memory"),
                    "used_memory_human": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "uptime_in_seconds": info.get("uptime_in_seconds")
                }
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return ServiceHealth(
                name="Redis Cache",
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message=f"Redis connection failed: {str(e)}"
            )

    async def check_model_service(self, service_name: str, url: str) -> ServiceHealth:
        """Check LLM model service health."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Check health endpoint
                response = await client.get(f"{url}/health")
                
                if response.status_code == 200:
                    health_data = response.json()
                    
                    # Test model inference if available
                    test_response = None
                    try:
                        test_payload = {
                            "text": "Hello, this is a health check test.",
                            "max_length": 50
                        }
                        test_response = await client.post(
                            f"{url}/generate", 
                            json=test_payload,
                            timeout=30
                        )
                    except Exception as e:
                        logger.warning(f"Model inference test failed for {service_name}: {e}")
                    
                    response_time = time.time() - start_time
                    
                    status = HealthStatus.HEALTHY
                    if test_response and test_response.status_code != 200:
                        status = HealthStatus.DEGRADED
                    
                    return ServiceHealth(
                        name=f"{service_name} Model Service",
                        status=status,
                        response_time=response_time,
                        message="Model service responding",
                        details={
                            **health_data,
                            "inference_test": test_response.status_code if test_response else None
                        }
                    )
                else:
                    response_time = time.time() - start_time
                    return ServiceHealth(
                        name=f"{service_name} Model Service",
                        status=HealthStatus.UNHEALTHY,
                        response_time=response_time,
                        message=f"HTTP {response.status_code}: {response.text}"
                    )
                    
        except Exception as e:
            response_time = time.time() - start_time
            return ServiceHealth(
                name=f"{service_name} Model Service",
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message=f"Service connection failed: {str(e)}"
            )

    async def check_api_service(self) -> ServiceHealth:
        """Check main API service health."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Check health endpoint
                response = await client.get("http://localhost:8000/health")
                
                if response.status_code == 200:
                    health_data = response.json()
                    
                    # Check specific endpoints
                    endpoints_to_check = [
                        "/docs",
                        "/api/v1/auth/health",
                        "/api/v1/users/health"
                    ]
                    
                    endpoint_results = {}
                    for endpoint in endpoints_to_check:
                        try:
                            ep_response = await client.get(f"http://localhost:8000{endpoint}")
                            endpoint_results[endpoint] = ep_response.status_code
                        except Exception as e:
                            endpoint_results[endpoint] = f"Error: {str(e)}"
                    
                    response_time = time.time() - start_time
                    
                    return ServiceHealth(
                        name="API Service",
                        status=HealthStatus.HEALTHY,
                        response_time=response_time,
                        message="API service responding",
                        details={
                            **health_data,
                            "endpoints": endpoint_results
                        }
                    )
                else:
                    response_time = time.time() - start_time
                    return ServiceHealth(
                        name="API Service",
                        status=HealthStatus.UNHEALTHY,
                        response_time=response_time,
                        message=f"HTTP {response.status_code}: {response.text}"
                    )
                    
        except Exception as e:
            response_time = time.time() - start_time
            return ServiceHealth(
                name="API Service",
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message=f"API connection failed: {str(e)}"
            )

    async def check_frontend_service(self) -> ServiceHealth:
        """Check frontend service health."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get("http://localhost:3000")
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    return ServiceHealth(
                        name="Frontend Service",
                        status=HealthStatus.HEALTHY,
                        response_time=response_time,
                        message="Frontend responding",
                        details={
                            "status_code": response.status_code,
                            "content_length": len(response.content)
                        }
                    )
                else:
                    return ServiceHealth(
                        name="Frontend Service",
                        status=HealthStatus.DEGRADED,
                        response_time=response_time,
                        message=f"HTTP {response.status_code}"
                    )
                    
        except Exception as e:
            response_time = time.time() - start_time
            return ServiceHealth(
                name="Frontend Service",
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message=f"Frontend connection failed: {str(e)}"
            )

    def check_docker_containers(self) -> List[ServiceHealth]:
        """Check Docker container health."""
        containers_health = []
        
        if not self.docker_client:
            return [ServiceHealth(
                name="Docker",
                status=HealthStatus.UNKNOWN,
                response_time=0,
                message="Docker client not available"
            )]
        
        try:
            # Expected containers
            expected_containers = [
                "jobautomation_api",
                "jobautomation_frontend", 
                "jobautomation_db",
                "jobautomation_redis",
                "jobautomation_phi3-service",
                "jobautomation_gemma-service",
                "jobautomation_mistral-service"
            ]
            
            containers = self.docker_client.containers.list(all=True)
            container_dict = {c.name: c for c in containers}
            
            for expected_name in expected_containers:
                if expected_name in container_dict:
                    container = container_dict[expected_name]
                    
                    status = HealthStatus.HEALTHY if container.status == "running" else HealthStatus.UNHEALTHY
                    
                    containers_health.append(ServiceHealth(
                        name=f"Container: {expected_name}",
                        status=status,
                        response_time=0,
                        message=f"Status: {container.status}",
                        details={
                            "image": container.image.tags[0] if container.image.tags else "unknown",
                            "created": container.attrs.get("Created"),
                            "status": container.status,
                            "ports": container.ports
                        }
                    ))
                else:
                    containers_health.append(ServiceHealth(
                        name=f"Container: {expected_name}",
                        status=HealthStatus.UNHEALTHY,
                        response_time=0,
                        message="Container not found"
                    ))
                    
        except Exception as e:
            containers_health.append(ServiceHealth(
                name="Docker Containers",
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"Error checking containers: {str(e)}"
            ))
        
        return containers_health

    async def check_all_services(self) -> Dict[str, ServiceHealth]:
        """Check health of all services."""
        logger.info("Starting comprehensive health check...")
        
        health_results = {}
        
        # Database check
        logger.info("Checking database...")
        health_results["database"] = await self.check_database()
        
        # Redis check
        logger.info("Checking Redis...")
        health_results["redis"] = await self.check_redis()
        
        # API service check
        logger.info("Checking API service...")
        health_results["api"] = await self.check_api_service()
        
        # Frontend service check
        logger.info("Checking frontend...")
        health_results["frontend"] = await self.check_frontend_service()
        
        # Model services check
        model_services = [
            ("Phi-3", self.settings.PHI3_SERVICE_URL),
            ("Gemma", self.settings.GEMMA_SERVICE_URL),
            ("Mistral", self.settings.MISTRAL_SERVICE_URL)
        ]
        
        for model_name, model_url in model_services:
            logger.info(f"Checking {model_name} model service...")
            health_results[f"model_{model_name.lower()}"] = await self.check_model_service(
                model_name, model_url
            )
        
        # Docker containers check
        logger.info("Checking Docker containers...")
        container_health = self.check_docker_containers()
        for i, container in enumerate(container_health):
            health_results[f"container_{i}"] = container
        
        return health_results

    def generate_health_report(self, health_results: Dict[str, ServiceHealth]) -> Dict[str, Any]:
        """Generate comprehensive health report."""
        total_services = len(health_results)
        healthy_count = sum(1 for h in health_results.values() if h.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for h in health_results.values() if h.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for h in health_results.values() if h.status == HealthStatus.UNHEALTHY)
        
        # Determine overall system health
        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status.value,
            "summary": {
                "total_services": total_services,
                "healthy": healthy_count,
                "degraded": degraded_count,
                "unhealthy": unhealthy_count,
                "uptime_percentage": (healthy_count / total_services) * 100 if total_services > 0 else 0
            },
            "services": {
                name: {
                    "status": health.status.value,
                    "response_time": health.response_time,
                    "message": health.message,
                    "details": health.details,
                    "timestamp": health.timestamp.isoformat()
                }
                for name, health in health_results.items()
            }
        }


def print_health_status(health_results: Dict[str, ServiceHealth], detailed: bool = False):
    """Print formatted health status."""
    
    # Status icons
    status_icons = {
        HealthStatus.HEALTHY: "✅",
        HealthStatus.DEGRADED: "⚠️",
        HealthStatus.UNHEALTHY: "❌",
        HealthStatus.UNKNOWN: "❓"
    }
    
    print("\n" + "="*80)
    print("🏥 SYSTEM HEALTH CHECK REPORT")
    print("="*80)
    
    # Summary
    total_services = len(health_results)
    healthy_count = sum(1 for h in health_results.values() if h.status == HealthStatus.HEALTHY)
    degraded_count = sum(1 for h in health_results.values() if h.status == HealthStatus.DEGRADED)
    unhealthy_count = sum(1 for h in health_results.values() if h.status == HealthStatus.UNHEALTHY)
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total Services: {total_services}")
    print(f"   ✅ Healthy: {healthy_count}")
    print(f"   ⚠️  Degraded: {degraded_count}")
    print(f"   ❌ Unhealthy: {unhealthy_count}")
    print(f"   📈 Uptime: {(healthy_count / total_services) * 100:.1f}%" if total_services > 0 else "   📈 Uptime: 0%")
    
    print(f"\n🔍 SERVICE STATUS:")
    print("-" * 80)
    
    # Service details
    for name, health in health_results.items():
        icon = status_icons.get(health.status, "❓")
        response_time_str = f"{health.response_time:.3f}s" if health.response_time > 0 else "N/A"
        
        print(f"{icon} {health.name:<35} {health.status.value.upper():<12} {response_time_str:<8} {health.message}")
        
        if detailed and health.details:
            for key, value in health.details.items():
                print(f"     {key}: {value}")
            print()


@click.command()
@click.option('--detailed', '-d', is_flag=True, help='Show detailed service information')
@click.option('--json-output', '-j', is_flag=True, help='Output results in JSON format')
@click.option('--timeout', '-t', default=10, help='Timeout for health checks (seconds)')
@click.option('--continuous', '-c', is_flag=True, help='Run continuous health monitoring')
@click.option('--interval', '-i', default=30, help='Interval for continuous monitoring (seconds)')
@click.option('--output-file', '-o', type=click.Path(), help='Save results to file')
@click.option('--quiet', '-q', is_flag=True, help='Suppress verbose output')
def main(detailed: bool, json_output: bool, timeout: int, continuous: bool, 
         interval: int, output_file: Optional[str], quiet: bool):
    """
    Comprehensive health check for Job Automation System.
    
    Examples:
        python health_check.py
        python health_check.py --detailed
        python health_check.py --json-output --output-file health.json
        python health_check.py --continuous --interval 60
    """
    
    # Setup logging
    log_level = logging.WARNING if quiet else logging.INFO
    setup_logging(level=log_level)
    
    async def run_health_check():
        """Run a single health check."""
        checker = HealthChecker(timeout=timeout)
        
        try:
            health_results = await checker.check_all_services()
            
            if json_output:
                report = checker.generate_health_report(health_results)
                
                if output_file:
                    with open(output_file, 'w') as f:
                        json.dump(report, f, indent=2)
                    if not quiet:
                        print(f"Health report saved to {output_file}")
                else:
                    print(json.dumps(report, indent=2))
            else:
                print_health_status(health_results, detailed)
                
                if output_file:
                    report = checker.generate_health_report(health_results)
                    with open(output_file, 'w') as f:
                        json.dump(report, f, indent=2)
                    if not quiet:
                        print(f"\nHealth report also saved to {output_file}")
            
            # Exit with error code if any services are unhealthy
            unhealthy_count = sum(1 for h in health_results.values() if h.status == HealthStatus.UNHEALTHY)
            return unhealthy_count == 0
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def continuous_monitoring():
        """Run continuous health monitoring."""
        if not quiet:
            print(f"🔄 Starting continuous health monitoring (interval: {interval}s)")
            print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                success = await run_health_check()
                
                if not success and not quiet:
                    print("\n⚠️  Issues detected in system health!")
                
                if not quiet:
                    print(f"\n⏰ Next check in {interval} seconds...")
                
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            if not quiet:
                print("\n\n👋 Health monitoring stopped by user")
    
    try:
        if continuous:
            asyncio.run(continuous_monitoring())
        else:
            success = asyncio.run(run_health_check())
            if not success:
                sys.exit(1)
                
    except KeyboardInterrupt:
        if not quiet:
            print("\n\n👋 Health check cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Health check error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()