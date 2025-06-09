"""Authentication endpoints for the job automation system."""

from datetime import timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token, UserLogin, PasswordReset, PasswordResetRequest

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    """
    Register a new user account.
    
    :param user_data: User registration data
    :type user_data: UserCreate
    :param db: Database session
    :type db: Session
    :return: Created user information
    :rtype: UserResponse
    :raises HTTPException: If email is already registered
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse.from_orm(db_user)


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    """
    Login and receive access token.
    
    :param form_data: OAuth2 form data with username and password
    :type form_data: OAuth2PasswordRequestForm
    :param db: Database session
    :type db: Session
    :return: Access token and token type
    :rtype: Token
    :raises HTTPException: If credentials are incorrect
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/login/json", response_model=Token)
async def login_json(user_login: UserLogin, db: Session = Depends(get_db)) -> Token:
    """
    Login with JSON payload and receive access token.
    
    :param user_login: User login credentials
    :type user_login: UserLogin
    :param db: Database session
    :type db: Session
    :return: Access token and token type
    :rtype: Token
    :raises HTTPException: If credentials are incorrect
    """
    user = authenticate_user(db, user_login.email, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_active_user)) -> Token:
    """
    Refresh access token for authenticated user.
    
    :param current_user: Currently authenticated user
    :type current_user: User
    :return: New access token
    :rtype: Token
    """
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.email}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/verify-token")
async def verify_token(current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """
    Verify if the current token is valid.
    
    :param current_user: Currently authenticated user
    :type current_user: User
    :return: Token validation result
    :rtype: Dict[str, Any]
    """
    return {"valid": True, "user_id": current_user.id, "email": current_user.email}


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)) -> Dict[str, str]:
    """
    Logout user (token invalidation would be handled client-side).
    
    :param current_user: Currently authenticated user
    :type current_user: User
    :return: Logout confirmation message
    :rtype: Dict[str, str]
    """
    return {"message": "Successfully logged out"}


@router.post("/request-password-reset")
async def request_password_reset(
    request: PasswordResetRequest, 
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Request password reset email.
    
    :param request: Password reset request data
    :type request: PasswordResetRequest
    :param db: Database session
    :type db: Session
    :return: Reset request confirmation message
    :rtype: Dict[str, str]
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Don't reveal if email exists for security
        return {"message": "If the email exists, a password reset link has been sent"}
    
    # Generate reset token (implement token generation logic)
    reset_token = create_access_token(
        data={"sub": user.email, "type": "password_reset"},
        expires_delta=timedelta(minutes=30)
    )
    
    # TODO: Send email with reset token
    # await send_password_reset_email(user.email, reset_token)
    
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Reset password using reset token.
    
    :param reset_data: Password reset data with token and new password
    :type reset_data: PasswordReset
    :param db: Database session
    :type db: Session
    :return: Reset confirmation message
    :rtype: Dict[str, str]
    :raises HTTPException: If token is invalid or expired
    """
    try:
        # Verify reset token (implement token verification)
        # payload = verify_token(reset_data.token)
        # email = payload.get("sub")
        # token_type = payload.get("type")
        
        # if token_type != "password_reset":
        #     raise HTTPException(status_code=400, detail="Invalid token type")
        
        # For now, simple implementation
        user = db.query(User).filter(User.email == reset_data.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update password
        user.hashed_password = get_password_hash(reset_data.new_password)
        db.commit()
        
        return {"message": "Password reset successfully"}
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    """
    Get current authenticated user information.
    
    :param current_user: Currently authenticated user
    :type current_user: User
    :return: Current user information
    :rtype: UserResponse
    """
    return UserResponse.from_orm(current_user)