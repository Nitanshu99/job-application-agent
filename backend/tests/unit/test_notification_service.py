"""
Unit tests for notification service functionality.

Tests email notifications, push notifications, and notification management.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.services.notification_service import NotificationService
from app.models.user import User
from app.models.application import Application
from app.models.job import Job
from app.core.exceptions import NotificationError


class TestNotificationService:
    """Test suite for NotificationService class."""

    @pytest.fixture
    def notification_service(self):
        """Create NotificationService instance for testing."""
        return NotificationService(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="test@example.com",
            password="test_password"
        )

    @pytest.fixture
    def sample_user(self):
        """Sample user for notification testing."""
        return {
            "id": 1,
            "email": "user@example.com",
            "full_name": "Test User",
            "notification_preferences": {
                "email_notifications": True,
                "push_notifications": True,
                "job_alerts": True,
                "application_updates": True
            }
        }

    @pytest.fixture
    def sample_job(self):
        """Sample job for notification testing."""
        return {
            "id": 1,
            "title": "Senior Software Engineer",
            "company": "TechCorp",
            "location": "San Francisco, CA",
            "url": "https://techcorp.com/jobs/senior-engineer"
        }

    @pytest.fixture
    def sample_application(self):
        """Sample application for notification testing."""
        return {
            "id": 1,
            "job_id": 1,
            "user_id": 1,
            "status": "pending",
            "applied_at": datetime.now(),
            "job": {
                "title": "Senior Software Engineer",
                "company": "TechCorp"
            }
        }

    @patch('smtplib.SMTP')
    async def test_send_email_success(self, mock_smtp, notification_service, sample_user):
        """Test successful email sending."""
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Call service method
        result = await notification_service.send_email(
            to_email=sample_user["email"],
            subject="Test Email",
            body="This is a test email",
            html_body="<p>This is a test email</p>"
        )
        
        # Assertions
        assert result["success"] is True
        assert "message_id" in result
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()

    @patch('smtplib.SMTP')
    async def test_send_email_smtp_error(self, mock_smtp, notification_service, sample_user):
        """Test email sending with SMTP error."""
        # Mock SMTP error
        mock_smtp.side_effect = smtplib.SMTPException("SMTP server error")
        
        # Should raise NotificationError
        with pytest.raises(NotificationError):
            await notification_service.send_email(
                to_email=sample_user["email"],
                subject="Test Email",
                body="Test body"
            )

    async def test_send_welcome_email(self, notification_service, sample_user):
        """Test sending welcome email to new user."""
        with patch.object(notification_service, 'send_email') as mock_send:
            mock_send.return_value = {"success": True, "message_id": "12345"}
            
            result = await notification_service.send_welcome_email(
                sample_user["email"],
                sample_user["full_name"]
            )
            
            # Assertions
            assert result["success"] is True
            mock_send.assert_called_once()
            
            # Check email content
            call_args = mock_send.call_args
            assert sample_user["email"] in call_args[1]["to_email"]
            assert "Welcome" in call_args[1]["subject"]
            assert sample_user["full_name"] in call_args[1]["body"]

    async def test_send_job_alert_email(self, notification_service, sample_user, sample_job):
        """Test sending job alert email."""
        matching_jobs = [sample_job]
        
        with patch.object(notification_service, 'send_email') as mock_send:
            mock_send.return_value = {"success": True, "message_id": "alert123"}
            
            result = await notification_service.send_job_alert_email(
                sample_user["email"],
                sample_user["full_name"],
                matching_jobs,
                alert_name="Python Developer Alert"
            )
            
            # Assertions
            assert result["success"] is True
            mock_send.assert_called_once()
            
            # Check email content
            call_args = mock_send.call_args
            assert "Job Alert" in call_args[1]["subject"]
            assert sample_job["title"] in call_args[1]["body"]
            assert sample_job["company"] in call_args[1]["body"]

    async def test_send_application_confirmation(self, notification_service, sample_user, sample_application):
        """Test sending application confirmation email."""
        with patch.object(notification_service, 'send_email') as mock_send:
            mock_send.return_value = {"success": True, "message_id": "confirm123"}
            
            result = await notification_service.send_application_confirmation(
                sample_user["email"],
                sample_user["full_name"],
                sample_application
            )
            
            # Assertions
            assert result["success"] is True
            mock_send.assert_called_once()
            
            # Check email content
            call_args = mock_send.call_args
            assert "Application Submitted" in call_args[1]["subject"]
            assert sample_application["job"]["title"] in call_args[1]["body"]

    async def test_send_application_status_update(self, notification_service, sample_user, sample_application):
        """Test sending application status update email."""
        sample_application["status"] = "interview_scheduled"
        
        with patch.object(notification_service, 'send_email') as mock_send:
            mock_send.return_value = {"success": True, "message_id": "status123"}
            
            result = await notification_service.send_application_status_update(
                sample_user["email"],
                sample_user["full_name"],
                sample_application,
                old_status="pending",
                new_status="interview_scheduled"
            )
            
            # Assertions
            assert result["success"] is True
            mock_send.assert_called_once()
            
            # Check email content
            call_args = mock_send.call_args
            assert "Application Update" in call_args[1]["subject"]
            assert "interview_scheduled" in call_args[1]["body"]

    async def test_send_follow_up_reminder(self, notification_service, sample_user, sample_application):
        """Test sending follow-up reminder email."""
        with patch.object(notification_service, 'send_email') as mock_send:
            mock_send.return_value = {"success": True, "message_id": "reminder123"}
            
            result = await notification_service.send_follow_up_reminder(
                sample_user["email"],
                sample_user["full_name"],
                sample_application,
                follow_up_date=datetime.now() + timedelta(days=1)
            )
            
            # Assertions
            assert result["success"] is True
            mock_send.assert_called_once()
            
            # Check email content
            call_args = mock_send.call_args
            assert "Follow-up Reminder" in call_args[1]["subject"]

    async def test_send_password_reset_email(self, notification_service, sample_user):
        """Test sending password reset email."""
        reset_token = "reset_token_12345"
        
        with patch.object(notification_service, 'send_email') as mock_send:
            mock_send.return_value = {"success": True, "message_id": "reset123"}
            
            result = await notification_service.send_password_reset_email(
                sample_user["email"],
                sample_user["full_name"],
                reset_token
            )
            
            # Assertions
            assert result["success"] is True
            mock_send.assert_called_once()
            
            # Check email content
            call_args = mock_send.call_args
            assert "Password Reset" in call_args[1]["subject"]
            assert reset_token in call_args[1]["body"]

    @patch('requests.post')
    async def test_send_push_notification(self, mock_post, notification_service, sample_user):
        """Test sending push notification."""
        # Mock successful push notification response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "id": "push123"}
        mock_post.return_value = mock_response
        
        # Call service method
        result = await notification_service.send_push_notification(
            user_id=sample_user["id"],
            title="New Job Match",
            body="Found a job that matches your criteria",
            data={"job_id": 1, "type": "job_match"}
        )
        
        # Assertions
        assert result["success"] is True
        mock_post.assert_called_once()

    @patch('requests.post')
    async def test_send_push_notification_error(self, mock_post, notification_service, sample_user):
        """Test push notification with service error."""
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid token"}
        mock_post.return_value = mock_response
        
        # Should raise NotificationError
        with pytest.raises(NotificationError):
            await notification_service.send_push_notification(
                user_id=sample_user["id"],
                title="Test Notification",
                body="Test body"
            )

    async def test_check_user_notification_preferences(self, notification_service, sample_user):
        """Test checking user notification preferences."""
        # User has notifications enabled
        can_send_email = notification_service.can_send_email_notification(
            sample_user,
            notification_type="job_alerts"
        )
        assert can_send_email is True
        
        can_send_push = notification_service.can_send_push_notification(
            sample_user,
            notification_type="application_updates"
        )
        assert can_send_push is True
        
        # Test with disabled notifications
        sample_user["notification_preferences"]["email_notifications"] = False
        can_send_email_disabled = notification_service.can_send_email_notification(
            sample_user,
            notification_type="job_alerts"
        )
        assert can_send_email_disabled is False

    async def test_batch_send_job_alerts(self, notification_service):
        """Test sending job alerts to multiple users."""
        users_and_jobs = [
            {
                "user": {"email": "user1@example.com", "full_name": "User 1"},
                "jobs": [{"title": "Job 1", "company": "Company 1"}],
                "alert_name": "Alert 1"
            },
            {
                "user": {"email": "user2@example.com", "full_name": "User 2"},
                "jobs": [{"title": "Job 2", "company": "Company 2"}],
                "alert_name": "Alert 2"
            }
        ]
        
        with patch.object(notification_service, 'send_job_alert_email') as mock_send:
            mock_send.return_value = {"success": True}
            
            results = await notification_service.batch_send_job_alerts(users_and_jobs)
            
            # Should send to all users
            assert len(results) == 2
            assert mock_send.call_count == 2
            assert all(result["success"] for result in results)

    async def test_schedule_notification(self, notification_service, sample_user):
        """Test scheduling future notification."""
        scheduled_time = datetime.now() + timedelta(hours=24)
        
        with patch.object(notification_service, 'add_to_schedule') as mock_schedule:
            mock_schedule.return_value = {"task_id": "scheduled123"}
            
            result = await notification_service.schedule_notification(
                user_id=sample_user["id"],
                notification_type="follow_up_reminder",
                scheduled_time=scheduled_time,
                data={"application_id": 1}
            )
            
            # Assertions
            assert "task_id" in result
            mock_schedule.assert_called_once()

    async def test_cancel_scheduled_notification(self, notification_service):
        """Test canceling scheduled notification."""
        task_id = "scheduled123"
        
        with patch.object(notification_service, 'cancel_scheduled_task') as mock_cancel:
            mock_cancel.return_value = {"success": True}
            
            result = await notification_service.cancel_scheduled_notification(task_id)
            
            # Assertions
            assert result["success"] is True
            mock_cancel.assert_called_once_with(task_id)

    async def test_get_notification_history(self, notification_service, sample_user):
        """Test getting notification history for user."""
        mock_history = [
            {
                "id": 1,
                "type": "email",
                "subject": "Welcome Email",
                "sent_at": datetime.now(),
                "status": "delivered"
            },
            {
                "id": 2,
                "type": "push",
                "title": "Job Alert",
                "sent_at": datetime.now(),
                "status": "delivered"
            }
        ]
        
        with patch.object(notification_service, 'get_user_notification_history') as mock_history_getter:
            mock_history_getter.return_value = mock_history
            
            history = await notification_service.get_notification_history(
                sample_user["id"],
                limit=10,
                offset=0
            )
            
            # Assertions
            assert len(history) == 2
            assert history[0]["type"] == "email"
            assert history[1]["type"] == "push"

    async def test_create_email_template(self, notification_service):
        """Test creating email template."""
        template_data = {
            "name": "job_alert_template",
            "subject": "New Job Alert: {alert_name}",
            "body": "Hello {user_name}, we found {job_count} new jobs matching your criteria.",
            "html_body": "<p>Hello {user_name}, we found <strong>{job_count}</strong> new jobs.</p>"
        }
        
        template = notification_service.create_email_template(**template_data)
        
        # Assertions
        assert template["name"] == "job_alert_template"
        assert "{alert_name}" in template["subject"]
        assert "{user_name}" in template["body"]

    async def test_render_email_template(self, notification_service):
        """Test rendering email template with data."""
        template = {
            "subject": "Welcome {user_name}!",
            "body": "Hello {user_name}, welcome to our platform. You have {feature_count} features available.",
            "html_body": "<h1>Welcome {user_name}!</h1><p>You have {feature_count} features.</p>"
        }
        
        template_data = {
            "user_name": "John Doe",
            "feature_count": 5
        }
        
        rendered = notification_service.render_email_template(template, template_data)
        
        # Assertions
        assert rendered["subject"] == "Welcome John Doe!"
        assert "Hello John Doe" in rendered["body"]
        assert "<h1>Welcome John Doe!</h1>" in rendered["html_body"]
        assert "5 features" in rendered["body"]

    async def test_notification_rate_limiting(self, notification_service, sample_user):
        """Test notification rate limiting."""
        # Mock rate limit storage
        with patch.object(notification_service, 'is_rate_limited') as mock_rate_check:
            with patch.object(notification_service, 'update_rate_limit') as mock_rate_update:
                
                # First notification should go through
                mock_rate_check.return_value = False
                
                with patch.object(notification_service, 'send_email') as mock_send:
                    mock_send.return_value = {"success": True}
                    
                    result1 = await notification_service.send_email_with_rate_limit(
                        sample_user["email"],
                        "Test Subject",
                        "Test Body",
                        rate_limit_key=f"user_{sample_user['id']}_email"
                    )
                    
                    assert result1["success"] is True
                    mock_rate_update.assert_called_once()
                
                # Second notification within rate limit should be blocked
                mock_rate_check.return_value = True
                
                result2 = await notification_service.send_email_with_rate_limit(
                    sample_user["email"],
                    "Test Subject 2",
                    "Test Body 2",
                    rate_limit_key=f"user_{sample_user['id']}_email"
                )
                
                assert result2["success"] is False
                assert "rate limited" in result2["error"].lower()

    async def test_notification_preferences_update(self, notification_service, sample_user):
        """Test updating user notification preferences."""
        new_preferences = {
            "email_notifications": False,
            "push_notifications": True,
            "job_alerts": True,
            "application_updates": False,
            "marketing_emails": False
        }
        
        with patch.object(notification_service, 'update_user_preferences') as mock_update:
            mock_update.return_value = {"success": True, "preferences": new_preferences}
            
            result = await notification_service.update_notification_preferences(
                sample_user["id"],
                new_preferences
            )
            
            # Assertions
            assert result["success"] is True
            assert result["preferences"]["email_notifications"] is False
            assert result["preferences"]["push_notifications"] is True

    async def test_notification_delivery_tracking(self, notification_service, sample_user):
        """Test tracking notification delivery status."""
        notification_id = "notif_12345"
        
        # Mock delivery status check
        with patch.object(notification_service, 'check_delivery_status') as mock_check:
            mock_check.return_value = {
                "notification_id": notification_id,
                "status": "delivered",
                "delivered_at": datetime.now().isoformat(),
                "bounce_reason": None
            }
            
            status = await notification_service.get_delivery_status(notification_id)
            
            # Assertions
            assert status["status"] == "delivered"
            assert status["notification_id"] == notification_id
            assert status["bounce_reason"] is None

    async def test_notification_unsubscribe(self, notification_service, sample_user):
        """Test unsubscribe functionality."""
        unsubscribe_token = "unsubscribe_token_12345"
        
        with patch.object(notification_service, 'process_unsubscribe') as mock_unsubscribe:
            mock_unsubscribe.return_value = {
                "success": True,
                "user_id": sample_user["id"],
                "unsubscribed_from": ["job_alerts", "marketing_emails"]
            }
            
            result = await notification_service.process_unsubscribe_request(
                unsubscribe_token,
                notification_types=["job_alerts"]
            )
            
            # Assertions
            assert result["success"] is True
            assert "job_alerts" in result["unsubscribed_from"]

    async def test_notification_analytics(self, notification_service):
        """Test notification analytics and metrics."""
        date_range = {
            "start_date": datetime.now() - timedelta(days=30),
            "end_date": datetime.now()
        }
        
        mock_analytics = {
            "total_sent": 1000,
            "delivered": 950,
            "bounced": 30,
            "opened": 400,
            "clicked": 150,
            "delivery_rate": 0.95,
            "open_rate": 0.42,
            "click_rate": 0.15,
            "by_type": {
                "job_alerts": 600,
                "application_updates": 300,
                "welcome_emails": 100
            }
        }
        
        with patch.object(notification_service, 'get_analytics_data') as mock_analytics_getter:
            mock_analytics_getter.return_value = mock_analytics
            
            analytics = await notification_service.get_notification_analytics(**date_range)
            
            # Assertions
            assert analytics["total_sent"] == 1000
            assert analytics["delivery_rate"] == 0.95
            assert analytics["open_rate"] == 0.42
            assert "job_alerts" in analytics["by_type"]
