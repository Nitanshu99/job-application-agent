"""
Notification service for job automation system.

This service handles various types of notifications including email notifications,
real-time alerts, application status updates, and system notifications.
It provides comprehensive notification management with delivery tracking
and user preference management.

Features:
- Email notifications with templates
- Real-time notification system
- Application status notifications
- System alerts and warnings
- User notification preferences
- Delivery tracking and retry mechanisms
"""

import logging
import asyncio
import smtplib
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from email.mime.base import MimeBase
from email import encoders
import json

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.application import Application
from app.models.job import Job
from app.utils.text_processing import clean_text
from app.utils.validation import validate_email

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing all types of notifications."""
    
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.email_user = settings.EMAIL_USER
        self.email_password = settings.EMAIL_PASSWORD
        self.notifications_enabled = settings.ENABLE_NOTIFICATIONS
        
        # Notification templates
        self.email_templates = {
            "application_submitted": self._get_application_submitted_template(),
            "application_status_update": self._get_status_update_template(),
            "job_match_found": self._get_job_match_template(),
            "weekly_summary": self._get_weekly_summary_template(),
            "system_alert": self._get_system_alert_template(),
            "duplicate_application": self._get_duplicate_alert_template(),
            "document_generated": self._get_document_generated_template()
        }
    
    async def send_application_submitted_notification(
        self,
        user_id: int,
        application_id: int,
        job_title: str,
        company: str,
        db: Session = None
    ) -> bool:
        """
        Send notification when an application is submitted.
        
        Args:
            user_id: ID of the user
            application_id: ID of the application
            job_title: Title of the job
            company: Company name
            db: Database session
            
        Returns:
            True if notification sent successfully
        """
        try:
            if not self.notifications_enabled:
                return True
            
            if not db:
                db = next(get_db())
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User {user_id} not found for notification")
                return False
            
            # Check user notification preferences
            if not self._should_send_notification(user, "application_submitted"):
                return True
            
            # Prepare notification data
            notification_data = {
                "user_name": f"{user.first_name} {user.last_name}",
                "job_title": job_title,
                "company": company,
                "application_id": application_id,
                "submitted_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "dashboard_url": f"{settings.FRONTEND_URL}/applications/{application_id}"
            }
            
            # Send email notification
            email_sent = await self._send_email_notification(
                user.email,
                "Application Submitted Successfully",
                "application_submitted",
                notification_data
            )
            
            # Log notification
            await self._log_notification(
                user_id=user_id,
                notification_type="application_submitted",
                recipient_email=user.email,
                success=email_sent,
                metadata=notification_data,
                db=db
            )
            
            logger.info(f"Application submitted notification sent to user {user_id}")
            return email_sent
            
        except Exception as e:
            logger.error(f"Failed to send application submitted notification: {str(e)}")
            return False
    
    async def send_status_update_notification(
        self,
        user_id: int,
        application_id: int,
        old_status: str,
        new_status: str,
        company: str,
        job_title: str,
        notes: Optional[str] = None,
        db: Session = None
    ) -> bool:
        """
        Send notification when application status changes.
        
        Args:
            user_id: ID of the user
            application_id: ID of the application
            old_status: Previous status
            new_status: New status
            company: Company name
            job_title: Job title
            notes: Optional notes about the change
            db: Database session
            
        Returns:
            True if notification sent successfully
        """
        try:
            if not self.notifications_enabled:
                return True
            
            if not db:
                db = next(get_db())
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Check if this status change warrants a notification
            if not self._should_notify_status_change(old_status, new_status):
                return True
            
            # Check user preferences
            if not self._should_send_notification(user, "application_status_update"):
                return True
            
            # Prepare notification data
            notification_data = {
                "user_name": f"{user.first_name} {user.last_name}",
                "job_title": job_title,
                "company": company,
                "old_status": self._format_status(old_status),
                "new_status": self._format_status(new_status),
                "status_emoji": self._get_status_emoji(new_status),
                "notes": notes or "",
                "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "application_url": f"{settings.FRONTEND_URL}/applications/{application_id}"
            }
            
            # Customize subject based on status
            subject = self._get_status_subject(new_status, company)
            
            # Send email notification
            email_sent = await self._send_email_notification(
                user.email,
                subject,
                "application_status_update",
                notification_data
            )
            
            # Log notification
            await self._log_notification(
                user_id=user_id,
                notification_type="application_status_update",
                recipient_email=user.email,
                success=email_sent,
                metadata=notification_data,
                db=db
            )
            
            logger.info(f"Status update notification sent for application {application_id}")
            return email_sent
            
        except Exception as e:
            logger.error(f"Failed to send status update notification: {str(e)}")
            return False
    
    async def send_job_match_notification(
        self,
        user_id: int,
        job_matches: List[Dict[str, Any]],
        db: Session = None
    ) -> bool:
        """
        Send notification about new job matches.
        
        Args:
            user_id: ID of the user
            job_matches: List of matching jobs
            db: Database session
            
        Returns:
            True if notification sent successfully
        """
        try:
            if not self.notifications_enabled or not job_matches:
                return True
            
            if not db:
                db = next(get_db())
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            if not self._should_send_notification(user, "job_match_found"):
                return True
            
            # Prepare job matches data
            formatted_matches = []
            for match in job_matches[:5]:  # Limit to top 5 matches
                formatted_matches.append({
                    "title": match.get("job_title", "Unknown"),
                    "company": match.get("company", "Unknown"),
                    "location": match.get("location", "Not specified"),
                    "relevance_score": f"{match.get('relevance_score', 0) * 100:.0f}%",
                    "url": match.get("url", "")
                })
            
            notification_data = {
                "user_name": f"{user.first_name} {user.last_name}",
                "match_count": len(job_matches),
                "top_matches": formatted_matches,
                "dashboard_url": f"{settings.FRONTEND_URL}/jobs/matches",
                "search_date": datetime.utcnow().strftime("%Y-%m-%d")
            }
            
            email_sent = await self._send_email_notification(
                user.email,
                f"🎯 {len(job_matches)} New Job Matches Found!",
                "job_match_found",
                notification_data
            )
            
            await self._log_notification(
                user_id=user_id,
                notification_type="job_match_found",
                recipient_email=user.email,
                success=email_sent,
                metadata=notification_data,
                db=db
            )
            
            logger.info(f"Job match notification sent to user {user_id} for {len(job_matches)} matches")
            return email_sent
            
        except Exception as e:
            logger.error(f"Failed to send job match notification: {str(e)}")
            return False
    
    async def send_weekly_summary(
        self,
        user_id: int,
        summary_data: Dict[str, Any],
        db: Session = None
    ) -> bool:
        """
        Send weekly application summary to user.
        
        Args:
            user_id: ID of the user
            summary_data: Summary statistics and data
            db: Database session
            
        Returns:
            True if notification sent successfully
        """
        try:
            if not self.notifications_enabled:
                return True
            
            if not db:
                db = next(get_db())
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            if not self._should_send_notification(user, "weekly_summary"):
                return True
            
            # Format summary data
            notification_data = {
                "user_name": f"{user.first_name} {user.last_name}",
                "week_start": summary_data.get("week_start", ""),
                "week_end": summary_data.get("week_end", ""),
                "applications_submitted": summary_data.get("applications_count", 0),
                "responses_received": summary_data.get("responses_count", 0),
                "interviews_scheduled": summary_data.get("interviews_count", 0),
                "top_companies": summary_data.get("top_companies", []),
                "response_rate": f"{summary_data.get('response_rate', 0):.1f}%",
                "achievements": summary_data.get("achievements", []),
                "recommendations": summary_data.get("recommendations", []),
                "dashboard_url": f"{settings.FRONTEND_URL}/analytics"
            }
            
            email_sent = await self._send_email_notification(
                user.email,
                f"📊 Your Weekly Job Search Summary",
                "weekly_summary",
                notification_data
            )
            
            await self._log_notification(
                user_id=user_id,
                notification_type="weekly_summary",
                recipient_email=user.email,
                success=email_sent,
                metadata=notification_data,
                db=db
            )
            
            logger.info(f"Weekly summary sent to user {user_id}")
            return email_sent
            
        except Exception as e:
            logger.error(f"Failed to send weekly summary: {str(e)}")
            return False
    
    async def send_system_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "info",
        user_ids: Optional[List[int]] = None,
        db: Session = None
    ) -> Dict[str, int]:
        """
        Send system alerts to users.
        
        Args:
            alert_type: Type of alert
            message: Alert message
            severity: Severity level (info, warning, error)
            user_ids: Optional list of specific user IDs
            db: Database session
            
        Returns:
            Dictionary with send statistics
        """
        try:
            if not self.notifications_enabled:
                return {"sent": 0, "failed": 0}
            
            if not db:
                db = next(get_db())
            
            # Get target users
            if user_ids:
                users = db.query(User).filter(User.id.in_(user_ids)).all()
            else:
                users = db.query(User).filter(User.is_active == True).all()
            
            sent_count = 0
            failed_count = 0
            
            for user in users:
                try:
                    notification_data = {
                        "user_name": f"{user.first_name} {user.last_name}",
                        "alert_type": alert_type,
                        "message": message,
                        "severity": severity,
                        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                        "severity_emoji": self._get_severity_emoji(severity)
                    }
                    
                    subject = f"System Alert: {alert_type}"
                    if severity == "error":
                        subject = f"🚨 {subject}"
                    elif severity == "warning":
                        subject = f"⚠️ {subject}"
                    
                    email_sent = await self._send_email_notification(
                        user.email,
                        subject,
                        "system_alert",
                        notification_data
                    )
                    
                    if email_sent:
                        sent_count += 1
                    else:
                        failed_count += 1
                    
                    await self._log_notification(
                        user_id=user.id,
                        notification_type="system_alert",
                        recipient_email=user.email,
                        success=email_sent,
                        metadata=notification_data,
                        db=db
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to send alert to user {user.id}: {str(e)}")
                    failed_count += 1
            
            logger.info(f"System alert sent: {sent_count} successful, {failed_count} failed")
            return {"sent": sent_count, "failed": failed_count}
            
        except Exception as e:
            logger.error(f"Failed to send system alerts: {str(e)}")
            return {"sent": 0, "failed": 0}
    
    async def send_duplicate_application_alert(
        self,
        user_id: int,
        job_title: str,
        company: str,
        similar_application: Dict[str, Any],
        db: Session = None
    ) -> bool:
        """Send alert about potential duplicate application."""
        try:
            if not self.notifications_enabled:
                return True
            
            if not db:
                db = next(get_db())
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            notification_data = {
                "user_name": f"{user.first_name} {user.last_name}",
                "job_title": job_title,
                "company": company,
                "similar_job": similar_application.get("job_title", ""),
                "similar_company": similar_application.get("company", ""),
                "applied_date": similar_application.get("applied_at", ""),
                "similarity_score": f"{similar_application.get('similarity_score', 0) * 100:.0f}%"
            }
            
            email_sent = await self._send_email_notification(
                user.email,
                "⚠️ Potential Duplicate Application Detected",
                "duplicate_application",
                notification_data
            )
            
            await self._log_notification(
                user_id=user_id,
                notification_type="duplicate_application",
                recipient_email=user.email,
                success=email_sent,
                metadata=notification_data,
                db=db
            )
            
            return email_sent
            
        except Exception as e:
            logger.error(f"Failed to send duplicate alert: {str(e)}")
            return False
    
    async def update_notification_preferences(
        self,
        user_id: int,
        preferences: Dict[str, bool],
        db: Session = None
    ) -> bool:
        """Update user notification preferences."""
        try:
            if not db:
                db = next(get_db())
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Update user notification preferences
            if not user.notification_preferences:
                user.notification_preferences = {}
            
            user.notification_preferences.update(preferences)
            db.commit()
            
            logger.info(f"Updated notification preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update notification preferences: {str(e)}")
            if db:
                db.rollback()
            return False
    
    # Private helper methods
    
    async def _send_email_notification(
        self,
        recipient_email: str,
        subject: str,
        template_name: str,
        data: Dict[str, Any]
    ) -> bool:
        """Send email notification using template."""
        try:
            if not validate_email(recipient_email):
                logger.error(f"Invalid email address: {recipient_email}")
                return False
            
            # Get template and format content
            template = self.email_templates.get(template_name)
            if not template:
                logger.error(f"Template not found: {template_name}")
                return False
            
            # Format email content
            html_content = template["html"].format(**data)
            text_content = template["text"].format(**data)
            
            # Create email message
            msg = MimeMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_user
            msg["To"] = recipient_email
            
            # Attach text and HTML content
            text_part = MimeText(text_content, "plain")
            html_part = MimeText(html_content, "html")
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            logger.debug(f"Email sent successfully to {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False
    
    async def _log_notification(
        self,
        user_id: int,
        notification_type: str,
        recipient_email: str,
        success: bool,
        metadata: Dict[str, Any],
        db: Session
    ) -> None:
        """Log notification attempt for tracking."""
        try:
            # This would typically log to a notifications table
            # For now, just log to application logs
            log_data = {
                "user_id": user_id,
                "type": notification_type,
                "recipient": recipient_email,
                "success": success,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata
            }
            
            logger.info(f"Notification logged: {json.dumps(log_data)}")
            
        except Exception as e:
            logger.error(f"Failed to log notification: {str(e)}")
    
    def _should_send_notification(self, user: User, notification_type: str) -> bool:
        """Check if user wants to receive this type of notification."""
        if not user.notification_preferences:
            return True  # Default to sending notifications
        
        return user.notification_preferences.get(notification_type, True)
    
    def _should_notify_status_change(self, old_status: str, new_status: str) -> bool:
        """Determine if status change warrants notification."""
        # Don't notify for minor status changes
        if old_status == new_status:
            return False
        
        # Always notify for important status changes
        important_statuses = [
            "interview", "offer", "hired", "rejected", "withdrawn"
        ]
        
        return any(status in new_status.lower() for status in important_statuses)
    
    def _format_status(self, status: str) -> str:
        """Format status for display."""
        return status.replace("_", " ").title()
    
    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for status."""
        status_lower = status.lower()
        if "offer" in status_lower or "hired" in status_lower:
            return "🎉"
        elif "interview" in status_lower:
            return "📞"
        elif "reject" in status_lower:
            return "❌"
        elif "withdrawn" in status_lower:
            return "🚫"
        else:
            return "📧"
    
    def _get_severity_emoji(self, severity: str) -> str:
        """Get emoji for alert severity."""
        if severity == "error":
            return "🚨"
        elif severity == "warning":
            return "⚠️"
        else:
            return "ℹ️"
    
    def _get_status_subject(self, status: str, company: str) -> str:
        """Generate appropriate subject for status update."""
        status_lower = status.lower()
        if "offer" in status_lower:
            return f"🎉 Job Offer from {company}!"
        elif "interview" in status_lower:
            return f"📞 Interview Scheduled with {company}"
        elif "reject" in status_lower:
            return f"Application Update from {company}"
        else:
            return f"Application Status Update - {company}"
    
    # Email template methods
    
    def _get_application_submitted_template(self) -> Dict[str, str]:
        """Get application submitted email template."""
        return {
            "html": """
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>✅ Application Submitted Successfully!</h2>
                <p>Hi {user_name},</p>
                <p>Your application has been successfully submitted for the following position:</p>
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>Position:</strong> {job_title}<br>
                    <strong>Company:</strong> {company}<br>
                    <strong>Submitted:</strong> {submitted_at}<br>
                    <strong>Application ID:</strong> {application_id}
                </div>
                <p>You can track your application status in your <a href="{dashboard_url}">dashboard</a>.</p>
                <p>Good luck with your application!</p>
                <hr>
                <p style="font-size: 12px; color: #666;">
                    This is an automated message from your Job Automation System.
                </p>
            </body>
            </html>
            """,
            "text": """
            Application Submitted Successfully!
            
            Hi {user_name},
            
            Your application has been successfully submitted for:
            Position: {job_title}
            Company: {company}
            Submitted: {submitted_at}
            Application ID: {application_id}
            
            Track your application: {dashboard_url}
            
            Good luck!
            """
        }
    
    def _get_status_update_template(self) -> Dict[str, str]:
        """Get status update email template."""
        return {
            "html": """
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>{status_emoji} Application Status Update</h2>
                <p>Hi {user_name},</p>
                <p>There's an update on your application:</p>
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>Position:</strong> {job_title}<br>
                    <strong>Company:</strong> {company}<br>
                    <strong>Status:</strong> {old_status} → <strong style="color: #0066cc;">{new_status}</strong><br>
                    <strong>Updated:</strong> {updated_at}
                    {notes}
                </div>
                <p><a href="{application_url}" style="background-color: #0066cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Application Details</a></p>
                <hr>
                <p style="font-size: 12px; color: #666;">
                    This is an automated message from your Job Automation System.
                </p>
            </body>
            </html>
            """,
            "text": """
            Application Status Update
            
            Hi {user_name},
            
            Your application status has been updated:
            Position: {job_title}
            Company: {company}
            Status: {old_status} → {new_status}
            Updated: {updated_at}
            
            {notes}
            
            View details: {application_url}
            """
        }
    
    def _get_job_match_template(self) -> Dict[str, str]:
        """Get job match notification template."""
        return {
            "html": """
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>🎯 New Job Matches Found!</h2>
                <p>Hi {user_name},</p>
                <p>We found {match_count} new job opportunities that match your profile:</p>
                <div style="margin: 20px 0;">
                    {top_matches}
                </div>
                <p><a href="{dashboard_url}" style="background-color: #0066cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View All Matches</a></p>
                <hr>
                <p style="font-size: 12px; color: #666;">
                    Found on {search_date} | Job Automation System
                </p>
            </body>
            </html>
            """,
            "text": """
            New Job Matches Found!
            
            Hi {user_name},
            
            We found {match_count} new opportunities for you.
            
            View all matches: {dashboard_url}
            
            Found on {search_date}
            """
        }
    
    def _get_weekly_summary_template(self) -> Dict[str, str]:
        """Get weekly summary email template."""
        return {
            "html": """
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>📊 Your Weekly Job Search Summary</h2>
                <p>Hi {user_name},</p>
                <p>Here's your job search activity for {week_start} - {week_end}:</p>
                <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3>📈 This Week's Stats</h3>
                    <ul>
                        <li><strong>{applications_submitted}</strong> applications submitted</li>
                        <li><strong>{responses_received}</strong> responses received</li>
                        <li><strong>{interviews_scheduled}</strong> interviews scheduled</li>
                        <li><strong>{response_rate}</strong> response rate</li>
                    </ul>
                </div>
                <p><a href="{dashboard_url}" style="background-color: #0066cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Full Analytics</a></p>
                <hr>
                <p style="font-size: 12px; color: #666;">
                    Weekly summary from your Job Automation System
                </p>
            </body>
            </html>
            """,
            "text": """
            Weekly Job Search Summary
            
            Hi {user_name},
            
            Week: {week_start} - {week_end}
            
            Stats:
            - {applications_submitted} applications submitted
            - {responses_received} responses received  
            - {interviews_scheduled} interviews scheduled
            - {response_rate} response rate
            
            View analytics: {dashboard_url}
            """
        }
    
    def _get_system_alert_template(self) -> Dict[str, str]:
        """Get system alert email template."""
        return {
            "html": """
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>{severity_emoji} System Alert: {alert_type}</h2>
                <p>Hi {user_name},</p>
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>Alert Type:</strong> {alert_type}<br>
                    <strong>Severity:</strong> {severity}<br>
                    <strong>Time:</strong> {timestamp}<br><br>
                    <strong>Message:</strong><br>
                    {message}
                </div>
                <hr>
                <p style="font-size: 12px; color: #666;">
                    System alert from your Job Automation System
                </p>
            </body>
            </html>
            """,
            "text": """
            System Alert: {alert_type}
            
            Hi {user_name},
            
            Alert: {alert_type}
            Severity: {severity}
            Time: {timestamp}
            
            Message: {message}
            """
        }
    
    def _get_duplicate_alert_template(self) -> Dict[str, str]:
        """Get duplicate application alert template."""
        return {
            "html": """
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>⚠️ Potential Duplicate Application Detected</h2>
                <p>Hi {user_name},</p>
                <p>We detected that you may have already applied to a similar position:</p>
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                    <strong>Current Application:</strong><br>
                    {job_title} at {company}<br><br>
                    <strong>Similar Previous Application:</strong><br>
                    {similar_job} at {similar_company}<br>
                    Applied on: {applied_date}<br>
                    Similarity: {similarity_score}
                </div>
                <p>Please review your applications to avoid duplicates.</p>
                <hr>
                <p style="font-size: 12px; color: #666;">
                    Duplicate detection from your Job Automation System
                </p>
            </body>
            </html>
            """,
            "text": """
            Potential Duplicate Application Detected
            
            Hi {user_name},
            
            You may have already applied to a similar position:
            
            Current: {job_title} at {company}
            Previous: {similar_job} at {similar_company}
            Applied: {applied_date}
            Similarity: {similarity_score}
            
            Please review to avoid duplicates.
            """
        }
    
    def _get_document_generated_template(self) -> Dict[str, str]:
        """Get document generated email template."""
        return {
            "html": """
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>📝 Document Generated Successfully</h2>
                <p>Hi {user_name},</p>
                <p>Your {document_type} has been generated for:</p>
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>Position:</strong> {job_title}<br>
                    <strong>Company:</strong> {company}<br>
                    <strong>Document Type:</strong> {document_type}<br>
                    <strong>Template:</strong> {template}<br>
                    <strong>Generated:</strong> {generated_at}
                </div>
                <p><a href="{document_url}" style="background-color: #0066cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Document</a></p>
                <hr>
                <p style="font-size: 12px; color: #666;">
                    Document notification from your Job Automation System
                </p>
            </body>
            </html>
            """,
            "text": """
            Document Generated Successfully
            
            Hi {user_name},
            
            Your {document_type} has been generated:
            Position: {job_title}
            Company: {company}
            Type: {document_type}
            Template: {template}
            Generated: {generated_at}
            
            View document: {document_url}
            """
        }