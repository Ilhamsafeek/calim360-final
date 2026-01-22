# =====================================================
# FILE: app/services/workflow_email_service.py
# Comprehensive Workflow Email Notification Service
# Handles all workflow-related email notifications
# =====================================================

import logging
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.email import send_email_smtp

logger = logging.getLogger(__name__)

class WorkflowEmailService:
    """Service for sending workflow-related email notifications"""
    
    @staticmethod
    def send_internal_review_request(
        db: Session,
        contract_id: int,
        contract_number: str,
        contract_title: str,
        reviewer_emails: list,
        initiator_name: str
    ) -> bool:
        """Send email when contract is submitted for internal review"""
        try:
            contract_url = f"https://calim360.com/contract/edit/{contract_id}?action=review"
            
            for email in reviewer_emails:
                # Get reviewer name
                user_query = text("""
                    SELECT CONCAT(first_name, ' ', last_name) as full_name
                    FROM users
                    WHERE email = :email
                """)
                user = db.execute(user_query, {"email": email}).fetchone()
                reviewer_name = user.full_name if user else "Team Member"
                
                subject = f"📋 Internal Review Required - {contract_number}"
                
                html_body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                        <div style="background: linear-gradient(135deg, #1a5f7a 0%, #159895 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                            <h2 style="margin: 0;">📋 Internal Review Request</h2>
                        </div>
                        
                        <div style="padding: 30px; background: #f9f9f9;">
                            <p style="font-size: 16px; margin-bottom: 10px;">Hello <strong>{reviewer_name}</strong>,</p>
                            
                            <p><strong>{initiator_name}</strong> has submitted a contract for your internal review.</p>
                            
                            <div style="background: white; padding: 20px; border-left: 4px solid #1a5f7a; margin: 20px 0; border-radius: 4px;">
                                <p style="margin: 5px 0;"><strong>Contract Number:</strong> {contract_number}</p>
                                <p style="margin: 5px 0;"><strong>Contract Title:</strong> {contract_title}</p>
                                <p style="margin: 5px 0;"><strong>Requested by:</strong> {initiator_name}</p>
                                <p style="margin: 5px 0;"><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                            </div>
                            
                            <p style="margin: 25px 0;">Please review the contract and provide your feedback.</p>
                            
                            <center>
                                <a href="{contract_url}" style="display: inline-block; background: #1a5f7a; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                                    Review Contract →
                                </a>
                            </center>
                        </div>
                        
                        <div style="background: #f0f0f0; padding: 15px; text-align: center; color: #666; font-size: 12px; border-radius: 0 0 8px 8px;">
                            <p style="margin: 5px 0;"><strong>CALIM 360</strong> - Smart Contract Lifecycle Management</p>
                            <p style="margin: 5px 0;">© {datetime.now().year} CALIM 360. All rights reserved.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                send_email_smtp(email, subject, html_body)
                logger.info(f"✉️ Internal review email sent to {email}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending internal review emails: {str(e)}")
            return False
    
    
    @staticmethod
    def send_workflow_step_notification(
        db: Session,
        contract_id: int,
        contract_number: str,
        contract_title: str,
        assignee_email: str,
        assignee_name: str,
        step_name: str,
        step_type: str,
        workflow_name: str,
        previous_approver_name: str = None
    ) -> bool:
        """Send email when workflow moves to next person"""
        try:
            contract_url = f"https://calim360.com/contract/edit/{contract_id}?action=approve"
            
            # Determine action text based on step type
            action_text = {
                'reviewer': 'review',
                'approver': 'approve',
                'e_sign_authority': 'sign',
                'counter_party': 'review'
            }.get(step_type, 'review')
            
            subject = f"⏭️ Your Action Required - {contract_number}"
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <div style="background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                        <h2 style="margin: 0;">⏭️ Workflow Action Required</h2>
                    </div>
                    
                    <div style="padding: 30px; background: #f9f9f9;">
                        <p style="font-size: 16px; margin-bottom: 10px;">Hello <strong>{assignee_name}</strong>,</p>
                        
                        <p>The contract workflow has progressed to your step. Your {action_text} is now required.</p>
                        
                        {"<p><em>" + previous_approver_name + " has completed their review.</em></p>" if previous_approver_name else ""}
                        
                        <div style="background: white; padding: 20px; border-left: 4px solid #f39c12; margin: 20px 0; border-radius: 4px;">
                            <p style="margin: 5px 0;"><strong>Contract Number:</strong> {contract_number}</p>
                            <p style="margin: 5px 0;"><strong>Contract Title:</strong> {contract_title}</p>
                            <p style="margin: 5px 0;"><strong>Workflow:</strong> {workflow_name}</p>
                            <p style="margin: 5px 0;"><strong>Your Role:</strong> {step_name}</p>
                            <p style="margin: 5px 0;"><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                        </div>
                        
                        <center>
                            <a href="{contract_url}" style="display: inline-block; background: #f39c12; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                                {action_text.title()} Contract →
                            </a>
                        </center>
                    </div>
                    
                    <div style="background: #f0f0f0; padding: 15px; text-align: center; color: #666; font-size: 12px; border-radius: 0 0 8px 8px;">
                        <p style="margin: 5px 0;"><strong>CALIM 360</strong> - Smart Contract Lifecycle Management</p>
                        <p style="margin: 5px 0;">© {datetime.now().year} CALIM 360. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            send_email_smtp(assignee_email, subject, html_body)
            logger.info(f"✉️ Workflow step notification sent to {assignee_email}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending workflow step notification: {str(e)}")
            return False
    
    
    @staticmethod
    def send_internal_review_completed(
        db: Session,
        contract_id: int,
        contract_number: str,
        contract_title: str,
        creator_email: str,
        creator_name: str
    ) -> bool:
        """Send email when internal review is completed"""
        try:
            contract_url = f"https://calim360.com/contract/edit/{contract_id}"
            
            subject = f"✅ Internal Review Completed - {contract_number}"
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <div style="background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                        <h2 style="margin: 0;">✅ Internal Review Completed</h2>
                    </div>
                    
                    <div style="padding: 30px; background: #f9f9f9;">
                        <p style="font-size: 16px; margin-bottom: 10px;">Hello <strong>{creator_name}</strong>,</p>
                        
                        <p>Great news! The internal review for your contract has been completed successfully.</p>
                        
                        <div style="background: white; padding: 20px; border-left: 4px solid #27ae60; margin: 20px 0; border-radius: 4px;">
                            <p style="margin: 5px 0;"><strong>Contract Number:</strong> {contract_number}</p>
                            <p style="margin: 5px 0;"><strong>Contract Title:</strong> {contract_title}</p>
                            <p style="margin: 5px 0;"><strong>Status:</strong> Review Completed</p>
                            <p style="margin: 5px 0;"><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                        </div>
                        
                        <p>You can now proceed with the next steps in the contract lifecycle.</p>
                        
                        <center>
                            <a href="{contract_url}" style="display: inline-block; background: #27ae60; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                                View Contract →
                            </a>
                        </center>
                    </div>
                    
                    <div style="background: #f0f0f0; padding: 15px; text-align: center; color: #666; font-size: 12px; border-radius: 0 0 8px 8px;">
                        <p style="margin: 5px 0;"><strong>CALIM 360</strong> - Smart Contract Lifecycle Management</p>
                        <p style="margin: 5px 0;">© {datetime.now().year} CALIM 360. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            send_email_smtp(creator_email, subject, html_body)
            logger.info(f"✉️ Internal review completion email sent to {creator_email}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending review completion email: {str(e)}")
            return False
    
    
    @staticmethod
    def send_counterparty_review_completed(
        db: Session,
        contract_id: int,
        contract_number: str,
        contract_title: str,
        party_b_lead_email: str,
        party_b_lead_name: str
    ) -> bool:
        """Send email when counter-party internal review is completed"""
        try:
            contract_url = f"https://calim360.com/contract/edit/{contract_id}"
            
            subject = f"✅ Counter-Party Review Completed - {contract_number}"
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <div style="background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                        <h2 style="margin: 0;">✅ Counter-Party Review Completed</h2>
                    </div>
                    
                    <div style="padding: 30px; background: #f9f9f9;">
                        <p style="font-size: 16px; margin-bottom: 10px;">Hello <strong>{party_b_lead_name}</strong>,</p>
                        
                        <p>The counter-party internal review has been completed successfully.</p>
                        
                        <div style="background: white; padding: 20px; border-left: 4px solid #3498db; margin: 20px 0; border-radius: 4px;">
                            <p style="margin: 5px 0;"><strong>Contract Number:</strong> {contract_number}</p>
                            <p style="margin: 5px 0;"><strong>Contract Title:</strong> {contract_title}</p>
                            <p style="margin: 5px 0;"><strong>Status:</strong> Counter-Party Review Completed</p>
                            <p style="margin: 5px 0;"><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                        </div>
                        
                        <p>The contract can now move forward to the next stage.</p>
                        
                        <center>
                            <a href="{contract_url}" style="display: inline-block; background: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                                View Contract →
                            </a>
                        </center>
                    </div>
                    
                    <div style="background: #f0f0f0; padding: 15px; text-align: center; color: #666; font-size: 12px; border-radius: 0 0 8px 8px;">
                        <p style="margin: 5px 0;"><strong>CALIM 360</strong> - Smart Contract Lifecycle Management</p>
                        <p style="margin: 5px 0;">© {datetime.now().year} CALIM 360. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            send_email_smtp(party_b_lead_email, subject, html_body)
            logger.info(f"✉️ Counter-party review completion email sent to {party_b_lead_email}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending counterparty review completion email: {str(e)}")
            return False
    
    
    @staticmethod
    def send_contract_sent_for_signature(
        db: Session,
        contract_id: int,
        contract_number: str,
        contract_title: str,
        esign_authority_email: str,
        esign_authority_name: str,
        party_type: str = "Party A"
    ) -> bool:
        """Send email when contract is sent for e-signature"""
        try:
            contract_url = f"https://calim360.com/contract/edit/{contract_id}?action=sign"
            
            subject = f"🖊️ Contract Ready for Signature - {contract_number}"
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <div style="background: linear-gradient(135deg, #8e44ad 0%, #9b59b6 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                        <h2 style="margin: 0;">🖊️ E-Signature Required</h2>
                    </div>
                    
                    <div style="padding: 30px; background: #f9f9f9;">
                        <p style="font-size: 16px; margin-bottom: 10px;">Hello <strong>{esign_authority_name}</strong>,</p>
                        
                        <p>A contract is ready for your electronic signature as <strong>{party_type}</strong> signatory authority.</p>
                        
                        <div style="background: white; padding: 20px; border-left: 4px solid #8e44ad; margin: 20px 0; border-radius: 4px;">
                            <p style="margin: 5px 0;"><strong>Contract Number:</strong> {contract_number}</p>
                            <p style="margin: 5px 0;"><strong>Contract Title:</strong> {contract_title}</p>
                            <p style="margin: 5px 0;"><strong>Your Role:</strong> {party_type} E-Sign Authority</p>
                            <p style="margin: 5px 0;"><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                        </div>
                        
                        <div style="background: #fff3cd; border-left: 4px solid #f0ad4e; padding: 15px; margin: 20px 0; border-radius: 6px;">
                            <strong style="color: #856404;">⚠️ Important:</strong>
                            <p style="margin: 5px 0 0 0;">Please review the contract thoroughly before signing. Your signature will be legally binding.</p>
                        </div>
                        
                        <center>
                            <a href="{contract_url}" style="display: inline-block; background: #8e44ad; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                                Review & Sign Contract →
                            </a>
                        </center>
                    </div>
                    
                    <div style="background: #f0f0f0; padding: 15px; text-align: center; color: #666; font-size: 12px; border-radius: 0 0 8px 8px;">
                        <p style="margin: 5px 0;"><strong>CALIM 360</strong> - Smart Contract Lifecycle Management</p>
                        <p style="margin: 5px 0;">© {datetime.now().year} CALIM 360. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            send_email_smtp(esign_authority_email, subject, html_body)
            logger.info(f"✉️ E-signature notification sent to {esign_authority_email}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending e-signature email: {str(e)}")
            return False
    
    
    @staticmethod
    def send_approval_rejection_notification(
        db: Session,
        contract_id: int,
        contract_number: str,
        contract_title: str,
        recipient_email: str,
        recipient_name: str,
        rejector_name: str,
        rejection_reason: str,
        request_type: str
    ) -> bool:
        """Send email when workflow step is rejected"""
        try:
            contract_url = f"https://calim360.com/contract/edit/{contract_id}"
            
            stage_names = {
                'internal_review': 'Internal Review',
                'counterparty_internal_review': 'Counter-Party Internal Review',
                'approval': 'Approval Workflow'
            }
            stage_name = stage_names.get(request_type, 'Workflow')
            
            subject = f"❌ Contract Rejected - {contract_number}"
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <div style="background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                        <h2 style="margin: 0;">❌ Contract Rejected</h2>
                    </div>
                    
                    <div style="padding: 30px; background: #f9f9f9;">
                        <p style="font-size: 16px; margin-bottom: 10px;">Hello <strong>{recipient_name}</strong>,</p>
                        
                        <p>A contract has been rejected during the <strong>{stage_name}</strong> stage.</p>
                        
                        <div style="background: white; padding: 20px; border-left: 4px solid #e74c3c; margin: 20px 0; border-radius: 4px;">
                            <p style="margin: 5px 0;"><strong>Contract Number:</strong> {contract_number}</p>
                            <p style="margin: 5px 0;"><strong>Contract Title:</strong> {contract_title}</p>
                            <p style="margin: 5px 0;"><strong>Rejected By:</strong> {rejector_name}</p>
                            <p style="margin: 5px 0;"><strong>Stage:</strong> {stage_name}</p>
                            <p style="margin: 5px 0;"><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                        </div>
                        
                        <div style="background: #ffe5e5; border-left: 4px solid #e74c3c; padding: 15px; margin: 20px 0; border-radius: 6px;">
                            <strong style="color: #c0392b;">Rejection Reason:</strong>
                            <p style="margin: 10px 0 0 0; color: #555;">{rejection_reason if rejection_reason else 'No reason provided'}</p>
                        </div>
                        
                        <p>Please review the feedback and make necessary changes before resubmitting.</p>
                        
                        <center>
                            <a href="{contract_url}" style="display: inline-block; background: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                                View Contract →
                            </a>
                        </center>
                    </div>
                    
                    <div style="background: #f0f0f0; padding: 15px; text-align: center; color: #666; font-size: 12px; border-radius: 0 0 8px 8px;">
                        <p style="margin: 5px 0;"><strong>CALIM 360</strong> - Smart Contract Lifecycle Management</p>
                        <p style="margin: 5px 0;">© {datetime.now().year} CALIM 360. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            send_email_smtp(recipient_email, subject, html_body)
            logger.info(f"✉️ Rejection notification sent to {recipient_email}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending rejection notification: {str(e)}")
            return False


    @staticmethod
    def send_approval_completed_notification(
        db: Session,
        contract_id: int,
        contract_number: str,
        contract_title: str,
        creator_email: str,
        creator_name: str
    ) -> bool:
        """Send email when approval workflow is completed"""
        try:
            contract_url = f"https://calim360.com/contract/edit/{contract_id}"
            
            subject = f"✅ Approval Workflow Completed - {contract_number}"
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <div style="background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                        <h2 style="margin: 0;">✅ Approval Workflow Completed</h2>
                    </div>
                    
                    <div style="padding: 30px; background: #f9f9f9;">
                        <p style="font-size: 16px; margin-bottom: 10px;">Hello <strong>{creator_name}</strong>,</p>
                        
                        <p>Excellent news! The approval workflow for your contract has been completed successfully.</p>
                        
                        <div style="background: white; padding: 20px; border-left: 4px solid #27ae60; margin: 20px 0; border-radius: 4px;">
                            <p style="margin: 5px 0;"><strong>Contract Number:</strong> {contract_number}</p>
                            <p style="margin: 5px 0;"><strong>Contract Title:</strong> {contract_title}</p>
                            <p style="margin: 5px 0;"><strong>Status:</strong> Approval Completed</p>
                            <p style="margin: 5px 0;"><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                        </div>
                        
                        <p>The contract can now proceed to execution and signature.</p>
                        
                        <center>
                            <a href="{contract_url}" style="display: inline-block; background: #27ae60; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                                View Contract →
                            </a>
                        </center>
                    </div>
                    
                    <div style="background: #f0f0f0; padding: 15px; text-align: center; color: #666; font-size: 12px; border-radius: 0 0 8px 8px;">
                        <p style="margin: 5px 0;"><strong>CALIM 360</strong> - Smart Contract Lifecycle Management</p>
                        <p style="margin: 5px 0;">© {datetime.now().year} CALIM 360. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            send_email_smtp(creator_email, subject, html_body)
            logger.info(f"✉️ Approval completion email sent to {creator_email}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending approval completion email: {str(e)}")
            return False