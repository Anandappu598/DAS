import logging
from django.contrib.auth import get_user_model, logout
from django.shortcuts import redirect
from django.urls import resolve
import requests
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)
User = get_user_model()

# AUTHENTICATION ENABLED: Anonymous user patching not needed
# def patch_anonymous_user():
#     """Add required attributes to AnonymousUser for development"""
#     if not hasattr(AnonymousUser, 'role'):
#         AnonymousUser.id = -1  # Fake ID for anonymous users in development
#         AnonymousUser.role = 'ADMIN'
#         AnonymousUser.department = None
#         AnonymousUser.phone_number = None
#         AnonymousUser.theme_preference = 'auto'
#         AnonymousUser.is_active = True
# 
# # Apply patch when module loads
# patch_anonymous_user()

class ImpersonationMiddleware:
    """
    Middleware that allows an ADMIN user to impersonate another user safely
    by providing an 'X-Impersonate-User' HTTP header.
    It overrides request.user for the duration of the request so that
    endpoints natively return the impersonated user's data.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # We need to ensure that the user authenticates first.
        # However, DRF's authentication happens in the View, not in the Middleware by default (unless utilizing session auth).
        # Since we use JWTAuthentication, request.user here is AnonymousUser before the view processes it.
        # But wait, DRF processes authentication in the view. So we CANNOT override request.user in middleware reliably 
        # before DRF overrides it back using the JWT token!
        # This is a critical realization. DRF will overwrite request.user during `perform_authentication()`.
        # So we should actually implement this as a Custom Authentication class or in the views!
        return self.get_response(request)


class EmployeeStatusCheckMiddleware:
    """
    Middleware to verify employee active status with HRM on every authenticated request
    
    Flow:
    1. Check if user is authenticated
    2. Skip check for certain URLs (admin, SSO login, inactive page)
    3. Verify employee status with HRM API
    4. If inactive: set user.is_active = False, logout, redirect to /inactive-user/
    5. If active: continue with request
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs to skip middleware check
        self.exempt_urls = [
            '/admin/',
            '/api/sso-login/',
            '/inactive-user/',
            '/api/login/',
            '/api/signup/',
            '/api/verify-signup/',
            '/api/forgot-password/',
            '/api/reset-password/',
        ]
    
    def __call__(self, request):
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Skip check for exempt URLs
            if not self.should_check_status(request.path):
                return self.get_response(request)
            
            # Check employee status from HRM
            email = request.user.email
            
            try:
                is_active = self.check_employee_status_from_hrm(email)
                
                # If employee is inactive
                if is_active is False:
                    logger.warning(f"Inactive employee detected: {email}")
                    
                    # Update user status
                    request.user.is_active = False
                    request.user.save()
                    
                    # Update employee profile if exists
                    if hasattr(request.user, 'employee_profile'):
                        request.user.employee_profile.is_active = False
                        request.user.employee_profile.save()
                    
                    # Logout user
                    logout(request)
                    
                    # Redirect to inactive page
                    return redirect('/inactive-user/')
                
            except Exception as e:
                # Log error but continue with request
                # Don't block legitimate users due to API failures
                logger.error(f"Error checking employee status: {str(e)}")
        
        response = self.get_response(request)
        return response
    
    def should_check_status(self, path):
        """
        Check if the path should trigger employee status verification
        """
        for exempt_url in self.exempt_urls:
            if path.startswith(exempt_url):
                return False
        return True
    
    def check_employee_status_from_hrm(self, email):
        """
        Call HRM API to verify employee active status
        Returns: True if active, False if inactive, None on error
        """
        try:
            # HRM API endpoint
            hrm_api_url = f"http://localhost:8001/api/check-employee-status/{email}/"
            # hrm_api_url = f"https://hrm.meridahr.com/api/check-employee-status/{email}/"
            
            response = requests.get(hrm_api_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('is_active', None)
            elif response.status_code == 404:
                # Employee not found in HRM
                logger.warning(f"Employee not found in HRM: {email}")
                return False
            else:
                logger.warning(f"HRM API returned status {response.status_code} for {email}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Failed to call HRM API: {str(e)}")
            return None
