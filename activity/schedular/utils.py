from django.core.mail import send_mail
from django.conf import settings
from .models import OTPVerification
from django.utils import timezone
import random


def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))


def create_otp_record(email, otp_type, user_data=None):
    # Generate OTP
    otp = generate_otp()
    
    # Delete any previous OTP for this email and type
    OTPVerification.objects.filter(
        email=email,
        otp_type=otp_type
    ).delete()
    
    # Create new OTP record
    otp_record = OTPVerification.objects.create(
        email=email,
        otp=otp,
        otp_type=otp_type,
        user_data=user_data
    )
    
    return otp_record


def send_signup_otp_to_admin(email, role, otp):
    """
    Send signup OTP to admin email
    
    Args:
        email: User's email
        role: User's role
        otp: The generated OTP
    
    Returns:
        Boolean indicating success
    """
    try:
        send_mail(
            subject='New Student Signup Request',
            message=f"""
            New signup request received:
            
            Email: {email}
            Role: {role}
            
            OTP for approval: {otp}
            
            This OTP will expire in 10 minutes.
            """,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=False,
        )
        return True
    except Exception as e:
        raise Exception(f"Failed to send email to admin: {str(e)}")


def send_account_approval_email(email):
    """
    Send account approval confirmation to user
    
    Args:
        email: User's email
    
    Returns:
        Boolean indicating success
    """
    try:
        send_mail(
            subject='Account Approved',
            message=f"""
            Dear User,
            
            Your account has been approved by the admin.
            You can now login with your email and password.
            
            Email: {email}
            
            Welcome to our platform!
            """,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send confirmation email: {e}")
        return False


def send_password_reset_otp(email, otp):
    """
    Send password reset OTP to user's email
    
    Args:
        email: User's email
        otp: The generated OTP
    
    Returns:
        Boolean indicating success
    """
    try:
        send_mail(
            subject='Password Reset OTP',
            message=f"""
            You requested to reset your password.
            
            Your OTP is: {otp}
            
            This OTP will expire in 10 minutes.
            
            If you didn't request this, please ignore this email.
            """,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")


def send_password_reset_confirmation(email):
    """
    Send password reset confirmation to user
    
    Args:
        email: User's email
    
    Returns:
        Boolean indicating success
    """
    try:
        send_mail(
            subject='Password Reset Successful',
            message=f"""
            Your password has been reset successfully.
            
            You can now login with your new password.
            
            If you didn't make this change, please contact support immediately.
            """,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send confirmation email: {e}")
        return False


def send_team_instruction_email(recipient_email, recipient_name, subject, instructions, project_name, sent_by_name):
    """
    Send team instruction email to selected team member
    
    Args:
        recipient_email: Recipient's email address
        recipient_name: Recipient's name
        subject: Instruction subject
        instructions: Instruction content/body
        project_name: Name of the project
        sent_by_name: Name of the person who sent the instruction
    
    Returns:
        Boolean indicating success
    """
    try:
        email_subject = f"New Team Instruction: {subject}"
        email_body = f"""
Dear {recipient_name},

You have received a new team instruction for the project: {project_name}

Subject: {subject}

Instructions:
{instructions}

Sent by: {sent_by_name}

Please review and take necessary action.

---
This is an automated email from the DAS Project Management System.
Please do not reply to this email.
        """
        
        send_mail(
            subject=email_subject,
            message=email_body,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[recipient_email],
            fail_silently=True,  # Don't crash if email fails
        )
        print(f"✅ Team instruction email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"⚠️ Failed to send team instruction email to {recipient_email}: {e}")
        return False


def verify_otp(email, otp, otp_type):
    """
    Verify OTP and return the OTP record if valid
    
    Args:
        email: User's email
        otp: The OTP to verify
        otp_type: 'signup' or 'forgot_password'
    
    Returns:
        OTPVerification object if valid, None otherwise
    """
    try:
        otp_record = OTPVerification.objects.get(
            email=email,
            otp=otp,
            otp_type=otp_type,
            is_verified=False
        )
        
        if otp_record.is_valid():
            return otp_record
        else:
            return None
            
    except OTPVerification.DoesNotExist:
        return None
