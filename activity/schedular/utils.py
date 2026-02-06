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
