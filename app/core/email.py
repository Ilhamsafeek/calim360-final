"""
Email Utilities for Smart CLM
File: app/core/email.py
Handles email verification and notifications with fallback for missing config
"""

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from typing import List, Optional
import os
import logging

logger = logging.getLogger(__name__)

# Check if email credentials are configured
EMAIL_CONFIGURED = all([
    os.getenv("MAIL_USERNAME"),
    os.getenv("MAIL_PASSWORD")
])

# Email configuration (only if credentials are available)
conf = None
fm = None

if EMAIL_CONFIGURED:
    try:
        conf = ConnectionConfig(
            MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
            MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
            MAIL_FROM=os.getenv("MAIL_FROM", "noreply@smartclm.com"),
            MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
            MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )
        fm = FastMail(conf)
        logger.info(" Email service configured successfully")
    except Exception as e:
        logger.warning(f" Email configuration failed: {str(e)}")
        EMAIL_CONFIGURED = False
else:
    logger.warning(" Email credentials not found in environment. Email features will be simulated.")

async def send_verification_email(email: str, first_name: str, verification_link: str):
    """
    Send email verification link to newly registered user
    Link expires in 24 hours
    If email is not configured, logs the verification link instead
    """
    
    if not EMAIL_CONFIGURED or fm is None:
        # Simulate email sending for development
        logger.info("=" * 70)
        logger.info("📧 EMAIL SIMULATION (No SMTP configured)")
        logger.info("=" * 70)
        logger.info(f"To: {email}")
        logger.info(f"Subject: Verify Your Smart CLM Account")
        logger.info(f"")
        logger.info(f"Hello {first_name},")
        logger.info(f"")
        logger.info(f"Please verify your email by clicking this link:")
        logger.info(f"🔗 {verification_link}")
        logger.info(f"")
        logger.info(f"This link expires in 24 hours.")
        logger.info("=" * 70)
        return {
            "status": "simulated",
            "message": "Email simulation logged to console"
        }
    
    # Send actual email if configured
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                line-height: 1.6; 
                color: #333; 
                margin: 0;
                padding: 0;
            }}
            .container {{ 
                max-width: 600px; 
                margin: 0 auto; 
                padding: 20px; 
            }}
            .header {{ 
                background: linear-gradient(135deg, #2762cb 0%, #73B4E0 100%); 
                color: white; 
                padding: 30px; 
                text-align: center; 
                border-radius: 8px 8px 0 0; 
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
            }}
            .content {{ 
                background: #f8f9fa; 
                padding: 30px; 
                border-radius: 0 0 8px 8px; 
            }}
            .button {{ 
                display: inline-block; 
                padding: 14px 35px; 
                background: #2762cb; 
                color: white !important; 
                text-decoration: none; 
                border-radius: 5px; 
                margin: 20px 0;
                font-weight: bold;
                font-size: 16px;
            }}
            .button:hover {{
                background: #1e4fa0;
            }}
            .footer {{ 
                text-align: center; 
                margin-top: 20px; 
                color: #666; 
                font-size: 12px; 
                padding: 20px;
            }}
            .warning {{ 
                background: #fff3cd; 
                border-left: 4px solid #856404; 
                padding: 15px; 
                margin: 20px 0;
                border-radius: 4px;
            }}
            .warning strong {{
                color: #856404;
            }}
            .link-text {{
                word-break: break-all; 
                color: #2762cb;
                background: #e9ecef;
                padding: 10px;
                border-radius: 4px;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to Smart CLM!</h1>
            </div>
            <div class="content">
                <h2 style="color: #2762cb;">Hello {first_name},</h2>
                <p style="font-size: 16px;">Thank you for registering with Smart CLM - your intelligent Contract Lifecycle Management solution.</p>
                
                <p>To complete your registration and activate your account, please verify your email address by clicking the button below:</p>
                
                <center>
                    <a href="{verification_link}" class="button">Verify Email Address</a>
                </center>
                
                <div class="warning">
                    <strong> Important:</strong> This verification link will expire in 24 hours for security purposes.
                </div>
                
                <p>If the button doesn't work, copy and paste this link into your browser:</p>
                <p class="link-text">{verification_link}</p>
                
                <p style="margin-top: 30px;">If you didn't create this account, please ignore this email.</p>
                
                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>The Smart CLM Team</strong>
                </p>
            </div>
            <div class="footer">
                <p>&copy; 2025 Smart CLM. All rights reserved.</p>
                <p>This is an automated email. Please do not reply.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        message = MessageSchema(
            subject="Verify Your Smart CLM Account",
            recipients=[email],
            body=html_content,
            subtype="html"
        )
        
        await fm.send_message(message)
        logger.info(f" Verification email sent to {email}")
        return {
            "status": "sent",
            "message": "Email sent successfully"
        }
    except Exception as e:
        logger.error(f" Failed to send verification email to {email}: {str(e)}")
        # Fall back to console logging
        logger.info("=" * 70)
        logger.info("📧 EMAIL FALLBACK (SMTP failed)")
        logger.info("=" * 70)
        logger.info(f"To: {email}")
        logger.info(f"Verification Link: {verification_link}")
        logger.info("=" * 70)
        return {
            "status": "fallback",
            "message": "Email sending failed, logged to console"
        }

async def send_password_reset_email(email: str, first_name: str, reset_link: str):
    """
    Send password reset link
    """
    if not EMAIL_CONFIGURED or fm is None:
        logger.info("=" * 70)
        logger.info("📧 PASSWORD RESET EMAIL SIMULATION")
        logger.info("=" * 70)
        logger.info(f"To: {email}")
        logger.info(f"Reset Link: {reset_link}")
        logger.info("=" * 70)
        return
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #2762cb 0%, #73B4E0 100%); 
                       color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
            .button {{ display: inline-block; padding: 12px 30px; background: #2762cb; 
                      color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>
            <div class="content">
                <h2>Hello {first_name},</h2>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                <center>
                    <a href="{reset_link}" class="button">Reset Password</a>
                </center>
                <p>This link will expire in 1 hour for security purposes.</p>
                <p>If you didn't request this reset, please ignore this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        message = MessageSchema(
            subject="Reset Your Smart CLM Password",
            recipients=[email],
            body=html_content,
            subtype="html"
        )
        await fm.send_message(message)
        logger.info(f" Password reset email sent to {email}")
    except Exception as e:
        logger.error(f" Failed to send password reset email: {str(e)}")

async def send_welcome_email(email: str, first_name: str):
    """
    Send welcome email after successful verification
    """
    if not EMAIL_CONFIGURED or fm is None:
        logger.info(f"📧 WELCOME EMAIL SIMULATION for {email}")
        return
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #2762cb 0%, #73B4E0 100%); 
                       color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to Smart CLM! 🎉</h1>
            </div>
            <div class="content">
                <h2>Hello {first_name},</h2>
                <p>Your account has been successfully verified and activated!</p>
                <p>You can now access all features of Smart CLM to manage your contracts efficiently.</p>
                <p>Get started by logging in to your dashboard.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        message = MessageSchema(
            subject="Welcome to Smart CLM!",
            recipients=[email],
            body=html_content,
            subtype="html"
        )
        await fm.send_message(message)
        logger.info(f" Welcome email sent to {email}")
    except Exception as e:
        logger.error(f" Failed to send welcome email: {str(e)}")