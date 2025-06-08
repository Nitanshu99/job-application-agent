#!/usr/bin/env python3
"""
Admin user creation utility for the Job Automation System.
Creates admin users with appropriate permissions and profile setup.
"""

import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional
import click
from getpass import getpass
import re

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.core.config import get_settings
from app.core.security import get_password_hash, verify_password
from app.core.logging import setup_logging
from app.models.user import User
from app.models import Base

# Setup logging
logger = logging.getLogger(__name__)


class AdminUserManager:
    """Manager for creating and managing admin users."""
    
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        
        # Create async engine and session
        self.engine = create_async_engine(
            self.settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'),
            echo=False
        )
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def create_tables(self):
        """Create database tables if they don't exist."""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise

    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def validate_password(self, password: str) -> tuple[bool, str]:
        """Validate password strength."""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, "Password is valid"

    async def user_exists(self, email: str) -> bool:
        """Check if user with email already exists."""
        try:
            async with self.async_session() as session:
                stmt = select(User).where(User.email == email)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                return user is not None
        except Exception as e:
            logger.error(f"Error checking user existence: {e}")
            return False

    async def create_admin_user(self, email: str, password: str, 
                              first_name: str, last_name: str,
                              phone: Optional[str] = None,
                              force: bool = False) -> User:
        """Create a new admin user."""
        try:
            # Validate inputs
            if not self.validate_email(email):
                raise ValueError("Invalid email format")
            
            is_valid, msg = self.validate_password(password)
            if not is_valid:
                raise ValueError(msg)
            
            # Check if user already exists
            if await self.user_exists(email):
                if not force:
                    raise ValueError(f"User with email {email} already exists")
                else:
                    logger.warning(f"User {email} exists but force flag is set")
            
            # Create user
            async with self.async_session() as session:
                # Hash password
                hashed_password = get_password_hash(password)
                
                # Create user object
                admin_user = User(
                    email=email,
                    hashed_password=hashed_password,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    is_active=True,
                    is_superuser=True,  # Admin user
                    is_verified=True,
                    profile_completed=True
                )
                
                session.add(admin_user)
                await session.commit()
                await session.refresh(admin_user)
                
                logger.info(f"Admin user created successfully: {email}")
                return admin_user
                
        except Exception as e:
            logger.error(f"Error creating admin user: {e}")
            raise

    async def update_user_password(self, email: str, new_password: str) -> bool:
        """Update password for existing user."""
        try:
            # Validate password
            is_valid, msg = self.validate_password(new_password)
            if not is_valid:
                raise ValueError(msg)
            
            async with self.async_session() as session:
                stmt = select(User).where(User.email == email)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                if not user:
                    raise ValueError(f"User {email} not found")
                
                # Update password
                user.hashed_password = get_password_hash(new_password)
                await session.commit()
                
                logger.info(f"Password updated for user: {email}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            raise

    async def promote_to_admin(self, email: str) -> bool:
        """Promote existing user to admin."""
        try:
            async with self.async_session() as session:
                stmt = select(User).where(User.email == email)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                if not user:
                    raise ValueError(f"User {email} not found")
                
                # Promote to admin
                user.is_superuser = True
                user.is_verified = True
                user.is_active = True
                await session.commit()
                
                logger.info(f"User promoted to admin: {email}")
                return True
                
        except Exception as e:
            logger.error(f"Error promoting user: {e}")
            raise

    async def list_admin_users(self) -> list[User]:
        """List all admin users."""
        try:
            async with self.async_session() as session:
                stmt = select(User).where(User.is_superuser == True)
                result = await session.execute(stmt)
                users = result.scalars().all()
                return list(users)
                
        except Exception as e:
            logger.error(f"Error listing admin users: {e}")
            return []

    async def revoke_admin(self, email: str) -> bool:
        """Revoke admin privileges from user."""
        try:
            async with self.async_session() as session:
                stmt = select(User).where(User.email == email)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                if not user:
                    raise ValueError(f"User {email} not found")
                
                # Revoke admin privileges
                user.is_superuser = False
                await session.commit()
                
                logger.info(f"Admin privileges revoked for user: {email}")
                return True
                
        except Exception as e:
            logger.error(f"Error revoking admin: {e}")
            raise

    async def close(self):
        """Close database connections."""
        await self.engine.dispose()


def prompt_user_details() -> dict:
    """Interactive prompt for user details."""
    print("\n=== Admin User Creation ===")
    
    while True:
        email = input("Email: ").strip()
        if not email:
            print("Email is required")
            continue
        
        manager = AdminUserManager()
        if not manager.validate_email(email):
            print("Invalid email format")
            continue
        break
    
    first_name = input("First Name: ").strip()
    last_name = input("Last Name: ").strip()
    phone = input("Phone (optional): ").strip() or None
    
    while True:
        password = getpass("Password: ")
        if not password:
            print("Password is required")
            continue
        
        manager = AdminUserManager()
        is_valid, msg = manager.validate_password(password)
        if not is_valid:
            print(f"Password validation failed: {msg}")
            continue
        
        confirm_password = getpass("Confirm Password: ")
        if password != confirm_password:
            print("Passwords do not match")
            continue
        break
    
    return {
        'email': email,
        'password': password,
        'first_name': first_name,
        'last_name': last_name,
        'phone': phone
    }


@click.group()
def cli():
    """Admin user management for Job Automation System."""
    pass


@cli.command()
@click.option('--email', '-e', prompt=True, help='Admin email address')
@click.option('--first-name', '-f', prompt=True, help='First name')
@click.option('--last-name', '-l', prompt=True, help='Last name')
@click.option('--phone', '-p', help='Phone number (optional)')
@click.option('--password', hide_input=True, confirmation_prompt=True, 
              help='Admin password')
@click.option('--force', is_flag=True, 
              help='Force creation even if user exists')
@click.option('--interactive', '-i', is_flag=True,
              help='Interactive mode with prompts')
def create(email: str, first_name: str, last_name: str, 
          phone: Optional[str], password: str, force: bool, interactive: bool):
    """Create a new admin user."""
    
    async def _create():
        manager = AdminUserManager()
        
        try:
            # Setup database
            await manager.create_tables()
            
            # Use interactive mode if requested
            if interactive:
                user_details = prompt_user_details()
                email = user_details['email']
                password = user_details['password']
                first_name = user_details['first_name']
                last_name = user_details['last_name']
                phone = user_details['phone']
            
            # Create admin user
            user = await manager.create_admin_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                force=force
            )
            
            print(f"\n✅ Admin user created successfully!")
            print(f"Email: {user.email}")
            print(f"Name: {user.first_name} {user.last_name}")
            print(f"ID: {user.id}")
            print(f"Created: {user.created_at}")
            
        except Exception as e:
            print(f"\n❌ Error creating admin user: {e}")
            sys.exit(1)
        finally:
            await manager.close()
    
    # Setup logging
    setup_logging(level=logging.INFO)
    
    # Run async function
    asyncio.run(_create())


@cli.command()
@click.option('--email', '-e', prompt=True, help='User email address')
@click.option('--password', hide_input=True, confirmation_prompt=True,
              help='New password')
def change_password(email: str, password: str):
    """Change password for existing user."""
    
    async def _change_password():
        manager = AdminUserManager()
        
        try:
            await manager.update_user_password(email, password)
            print(f"\n✅ Password updated successfully for {email}")
            
        except Exception as e:
            print(f"\n❌ Error updating password: {e}")
            sys.exit(1)
        finally:
            await manager.close()
    
    setup_logging(level=logging.INFO)
    asyncio.run(_change_password())


@cli.command()
@click.option('--email', '-e', prompt=True, help='User email address')
def promote(email: str):
    """Promote existing user to admin."""
    
    async def _promote():
        manager = AdminUserManager()
        
        try:
            await manager.promote_to_admin(email)
            print(f"\n✅ User {email} promoted to admin successfully")
            
        except Exception as e:
            print(f"\n❌ Error promoting user: {e}")
            sys.exit(1)
        finally:
            await manager.close()
    
    setup_logging(level=logging.INFO)
    asyncio.run(_promote())


@cli.command()
@click.option('--email', '-e', prompt=True, help='Admin email address')
def revoke(email: str):
    """Revoke admin privileges from user."""
    
    async def _revoke():
        manager = AdminUserManager()
        
        try:
            await manager.revoke_admin(email)
            print(f"\n✅ Admin privileges revoked for {email}")
            
        except Exception as e:
            print(f"\n❌ Error revoking admin: {e}")
            sys.exit(1)
        finally:
            await manager.close()
    
    setup_logging(level=logging.INFO)
    asyncio.run(_revoke())


@cli.command()
def list_admins():
    """List all admin users."""
    
    async def _list():
        manager = AdminUserManager()
        
        try:
            users = await manager.list_admin_users()
            
            if not users:
                print("\n📝 No admin users found")
                return
            
            print(f"\n📋 Admin Users ({len(users)} found):")
            print("-" * 80)
            print(f"{'ID':<8} {'EMAIL':<30} {'NAME':<25} {'CREATED':<20}")
            print("-" * 80)
            
            for user in users:
                name = f"{user.first_name} {user.last_name}".strip()
                created = user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "N/A"
                print(f"{user.id:<8} {user.email:<30} {name:<25} {created:<20}")
            
        except Exception as e:
            print(f"\n❌ Error listing admin users: {e}")
            sys.exit(1)
        finally:
            await manager.close()
    
    setup_logging(level=logging.WARNING)
    asyncio.run(_list())


if __name__ == "__main__":
    cli()