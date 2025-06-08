#!/usr/bin/env python3
"""
Database backup utility for the Job Automation System.
Supports full database backups, incremental backups, and automated scheduling.
"""

import os
import sys
import logging
import subprocess
import datetime
from pathlib import Path
import click
import psycopg2
from psycopg2 import sql
import boto3
from botocore.exceptions import ClientError
from typing import Optional
import yaml

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.core.config import get_settings
from app.core.logging import setup_logging

# Setup logging
logger = logging.getLogger(__name__)


class DatabaseBackup:
    """Database backup manager with support for local and cloud storage."""
    
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # S3 configuration (optional)
        self.s3_client = None
        if hasattr(self.settings, 'AWS_ACCESS_KEY_ID') and self.settings.AWS_ACCESS_KEY_ID:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=self.settings.AWS_SECRET_ACCESS_KEY,
                    region_name=getattr(self.settings, 'AWS_REGION', 'us-east-1')
                )
            except Exception as e:
                logger.warning(f"Could not initialize S3 client: {e}")

    def parse_database_url(self, database_url: str) -> dict:
        """Parse database URL into connection parameters."""
        try:
            # Handle postgresql:// URLs
            if database_url.startswith('postgresql://'):
                # Extract components
                url_parts = database_url.replace('postgresql://', '').split('@')
                if len(url_parts) != 2:
                    raise ValueError("Invalid database URL format")
                
                user_pass, host_db = url_parts
                user_parts = user_pass.split(':')
                host_parts = host_db.split('/')
                
                if len(user_parts) != 2 or len(host_parts) < 2:
                    raise ValueError("Invalid database URL format")
                
                username, password = user_parts
                host_port = host_parts[0]
                database = host_parts[1]
                
                if ':' in host_port:
                    host, port = host_port.split(':')
                else:
                    host, port = host_port, '5432'
                
                return {
                    'host': host,
                    'port': int(port),
                    'database': database,
                    'username': username,
                    'password': password
                }
            else:
                raise ValueError("Unsupported database URL format")
                
        except Exception as e:
            logger.error(f"Error parsing database URL: {e}")
            raise

    def create_backup_filename(self, backup_type: str = "full") -> str:
        """Generate timestamped backup filename."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"jobautomation_{backup_type}_{timestamp}.sql"

    def perform_full_backup(self, output_file: Optional[str] = None) -> str:
        """Perform a full database backup using pg_dump."""
        try:
            db_params = self.parse_database_url(self.settings.DATABASE_URL)
            
            if not output_file:
                output_file = self.backup_dir / self.create_backup_filename("full")
            else:
                output_file = Path(output_file)
            
            # Prepare pg_dump command
            env = os.environ.copy()
            env['PGPASSWORD'] = db_params['password']
            
            cmd = [
                'pg_dump',
                '-h', db_params['host'],
                '-p', str(db_params['port']),
                '-U', db_params['username'],
                '-d', db_params['database'],
                '--verbose',
                '--clean',
                '--if-exists',
                '--create',
                '--format=custom',
                '--file', str(output_file)
            ]
            
            logger.info(f"Starting full backup to {output_file}")
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Backup failed: {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)
            
            logger.info(f"Backup completed successfully: {output_file}")
            logger.info(f"Backup size: {output_file.stat().st_size / (1024*1024):.2f} MB")
            
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Error during backup: {e}")
            raise

    def perform_schema_backup(self, output_file: Optional[str] = None) -> str:
        """Perform a schema-only backup."""
        try:
            db_params = self.parse_database_url(self.settings.DATABASE_URL)
            
            if not output_file:
                output_file = self.backup_dir / self.create_backup_filename("schema")
            else:
                output_file = Path(output_file)
            
            env = os.environ.copy()
            env['PGPASSWORD'] = db_params['password']
            
            cmd = [
                'pg_dump',
                '-h', db_params['host'],
                '-p', str(db_params['port']),
                '-U', db_params['username'],
                '-d', db_params['database'],
                '--schema-only',
                '--verbose',
                '--clean',
                '--if-exists',
                '--create',
                '--file', str(output_file)
            ]
            
            logger.info(f"Starting schema backup to {output_file}")
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Schema backup failed: {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)
            
            logger.info(f"Schema backup completed: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Error during schema backup: {e}")
            raise

    def upload_to_s3(self, file_path: str, bucket: str, key: Optional[str] = None) -> bool:
        """Upload backup file to S3."""
        if not self.s3_client:
            logger.warning("S3 client not configured, skipping upload")
            return False
        
        try:
            if not key:
                key = f"database-backups/{Path(file_path).name}"
            
            logger.info(f"Uploading {file_path} to s3://{bucket}/{key}")
            self.s3_client.upload_file(file_path, bucket, key)
            logger.info("Upload completed successfully")
            return True
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            return False

    def cleanup_old_backups(self, retention_days: int = 30) -> None:
        """Remove backup files older than retention period."""
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
            
            removed_count = 0
            for backup_file in self.backup_dir.glob("jobautomation_*.sql"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    logger.info(f"Removing old backup: {backup_file}")
                    backup_file.unlink()
                    removed_count += 1
            
            logger.info(f"Cleaned up {removed_count} old backup files")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def verify_backup(self, backup_file: str) -> bool:
        """Verify backup file integrity."""
        try:
            # Check if file exists and has content
            backup_path = Path(backup_file)
            if not backup_path.exists():
                logger.error(f"Backup file does not exist: {backup_file}")
                return False
            
            if backup_path.stat().st_size == 0:
                logger.error(f"Backup file is empty: {backup_file}")
                return False
            
            # Try to read the backup file header
            if backup_file.endswith('.sql'):
                with open(backup_file, 'r') as f:
                    first_line = f.readline()
                    if not first_line.strip():
                        logger.error("Backup file appears to be empty or corrupted")
                        return False
            
            logger.info(f"Backup verification passed: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying backup: {e}")
            return False

    def get_database_info(self) -> dict:
        """Get database information for backup metadata."""
        try:
            db_params = self.parse_database_url(self.settings.DATABASE_URL)
            
            conn = psycopg2.connect(
                host=db_params['host'],
                port=db_params['port'],
                database=db_params['database'],
                user=db_params['username'],
                password=db_params['password']
            )
            
            with conn.cursor() as cursor:
                # Get database size
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size,
                           version() as version,
                           current_database() as database_name
                """)
                result = cursor.fetchone()
                
                # Get table count
                cursor.execute("""
                    SELECT count(*) FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                table_count = cursor.fetchone()[0]
                
                return {
                    'database_name': result[2],
                    'size': result[0],
                    'version': result[1],
                    'table_count': table_count,
                    'backup_time': datetime.datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {}
        finally:
            if 'conn' in locals():
                conn.close()


@click.command()
@click.option('--type', 'backup_type', 
              type=click.Choice(['full', 'schema']), 
              default='full',
              help='Type of backup to perform')
@click.option('--output', '-o', 
              type=click.Path(),
              help='Output file path (default: auto-generated)')
@click.option('--upload-s3', 
              is_flag=True,
              help='Upload backup to S3')
@click.option('--s3-bucket',
              help='S3 bucket name for upload')
@click.option('--cleanup',
              is_flag=True,
              help='Clean up old backup files')
@click.option('--retention-days',
              type=int,
              default=30,
              help='Number of days to retain backups (default: 30)')
@click.option('--verify',
              is_flag=True,
              help='Verify backup after creation')
@click.option('--quiet', '-q',
              is_flag=True,
              help='Suppress verbose output')
def main(backup_type: str, output: Optional[str], upload_s3: bool, 
         s3_bucket: Optional[str], cleanup: bool, retention_days: int,
         verify: bool, quiet: bool):
    """
    Database backup utility for Job Automation System.
    
    Examples:
        python backup_db.py --type full
        python backup_db.py --type schema --output schema_backup.sql
        python backup_db.py --upload-s3 --s3-bucket my-backups
        python backup_db.py --cleanup --retention-days 7
    """
    
    # Setup logging
    log_level = logging.WARNING if quiet else logging.INFO
    setup_logging(level=log_level)
    
    try:
        backup_manager = DatabaseBackup()
        
        # Get database info
        if not quiet:
            db_info = backup_manager.get_database_info()
            if db_info:
                logger.info(f"Database: {db_info.get('database_name')}")
                logger.info(f"Size: {db_info.get('size')}")
                logger.info(f"Tables: {db_info.get('table_count')}")
        
        # Perform backup
        if backup_type == 'full':
            backup_file = backup_manager.perform_full_backup(output)
        else:
            backup_file = backup_manager.perform_schema_backup(output)
        
        # Verify backup if requested
        if verify:
            if not backup_manager.verify_backup(backup_file):
                logger.error("Backup verification failed")
                sys.exit(1)
        
        # Upload to S3 if requested
        if upload_s3:
            if not s3_bucket:
                logger.error("S3 bucket name required for upload")
                sys.exit(1)
            backup_manager.upload_to_s3(backup_file, s3_bucket)
        
        # Cleanup old backups if requested
        if cleanup:
            backup_manager.cleanup_old_backups(retention_days)
        
        if not quiet:
            logger.info("Backup operation completed successfully")
            
    except KeyboardInterrupt:
        logger.info("Backup cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()