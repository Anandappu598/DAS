"""
SSO Views for DAS - Handles Single Sign-On from HRM
"""

from django.shortcuts import redirect
from django.contrib.auth import login, logout
from django.views import View
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import UntypedToken, RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings
from .models import User, Employee
import requests
import jwt
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class SSOLoginView(View):
    """
    SSO Login endpoint for DAS
    Validates JWT token from HRM and creates/updates user
    
    URL: /api/sso-login/?token=<jwt_token>
    Method: GET
    
    Flow:
    1. Get token from query params
    2. Validate JWT token
    3. Call HRM API to check employee active status
    4. Create or update User and Employee in DAS
    5. Login user and redirect to dashboard
    """
    
    def get(self, request):
        try:
            # Get token from query params
            token = request.GET.get('token')
            
            if not token:
                return HttpResponse(
                    "SSO token is required. Please login through HRM.",
                    status=400
                )
            
            # Validate and decode JWT token
            try:
                # Decode token using shared secret
                decoded_token = jwt.decode(
                    token,
                    settings.SSO_SHARED_SECRET,
                    algorithms=['HS256']
                )
                
                logger.info(f"SSO Login attempt for email: {decoded_token.get('email')}")
                
            except jwt.ExpiredSignatureError:
                return HttpResponse(
                    "SSO token has expired. Please login again through HRM.",
                    status=401
                )
            except jwt.InvalidTokenError as e:
                logger.error(f"Invalid SSO token: {str(e)}")
                return HttpResponse(
                    "Invalid SSO token. Please login through HRM.",
                    status=401
                )
            
            # Extract minimal employee details from token
            email = decoded_token.get('email')
            name = decoded_token.get('name')
            employee_id = decoded_token.get('employee_id', '')
            designation = decoded_token.get('designation', '')
            hrm_role = decoded_token.get('hrm_role', '')
            token_is_active = decoded_token.get('is_active', True)
            last_modified = decoded_token.get('last_modified', '')
            sync_required = decoded_token.get('sync_required', False)
            
            if not email:
                return HttpResponse(
                    "Invalid token: Email not found.",
                    status=400
                )
            
            # Map HRM role to DAS role
            das_role = self.map_das_role(designation or hrm_role)
            
            # Call HRM API to verify employee active status
            hrm_status = self.check_employee_status_from_hrm(email)
            
            # Determine if employee is active
            is_active = hrm_status.get('is_active', False) if hrm_status else token_is_active
            
            # Get or create User (DAS authentication + role)
            user, user_created = User.objects.get_or_create(
                email=email,
                defaults={
                    'role': das_role,
                    'is_active': is_active,
                    'phone_number': '',
                }
            )
            
            # Update user if exists
            if not user_created:
                user.role = das_role
                user.is_active = is_active
                user.save()
            
            # Check if full employee sync is needed
            needs_full_sync = False
            employee_exists = False
            
            try:
                employee = Employee.objects.get(user=user)
                employee_exists = True
                
                # Check if employee data is outdated (older than 24 hours)
                from datetime import timedelta
                from django.utils import timezone
                
                if employee.last_synced_at < timezone.now() - timedelta(hours=24):
                    needs_full_sync = True
                    logger.info(f"Employee data outdated for {email}, triggering full sync")
                else:
                    # Just update is_active status
                    employee.is_active = is_active
                    employee.save(update_fields=['is_active'])
                    logger.info(f"Employee data is fresh for {email}, skipping full sync")
                    
            except Employee.DoesNotExist:
                needs_full_sync = True
                logger.info(f"First time login for {email}, triggering full sync")
            
            # Perform full sync if needed
            if needs_full_sync or sync_required:
                logger.info(f"Fetching full employee details from HRM for {email}")
                full_employee_data = self.fetch_full_employee_data(email)
                
                if full_employee_data:
                    # Update employee profile with complete data
                    self.sync_employee_profile(user, full_employee_data, is_active)
                else:
                    # Fallback: Create minimal employee record
                    Employee.objects.update_or_create(
                        user=user,
                        defaults={
                            'name': name,
                            'email': email,
                            'employee_id': employee_id,
                            'designation': designation,
                            'hrm_role': hrm_role,
                            'is_active': is_active,
                        }
                    )
            
            # Handle inactive users
            if not is_active:
                user.is_active = False
                user.save()
                logger.warning(f"Inactive employee attempted SSO login: {email}")
                return redirect('/inactive-user/')
            
            # Sync all employees if admin is logging in
            if das_role == 'ADMIN':
                logger.info(f"Admin login detected, triggering full employee sync")
                try:
                    sync_result = self.sync_all_employees_from_hrm()
                    if sync_result:
                        logger.info(f"Employee sync completed: {sync_result.get('created', 0)} created, {sync_result.get('updated', 0)} updated")
                except Exception as sync_error:
                    logger.error(f"Employee sync failed during admin login: {str(sync_error)}")
                    # Don't block login even if sync fails
            
            # Login user (for session-based auth if needed)
            login(request, user, backend='schedular.backends.EmailBackend')
            
            # Generate JWT tokens for Flutter app
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            logger.info(f"SSO login successful for: {email}")
            
            # Build Flutter app URL with SSO parameters - use configured URL from settings
            flutter_url = getattr(settings, 'DAS_FRONTEND_URL', 'http://localhost:63105/')
            # flutter_url = getattr(settings, 'DAS_FRONTEND_URL', 'https://das.meridahr.com/')
            params = {
                'sso_token': access_token,
                'refresh_token': refresh_token,
                'user_id': str(user.id),
                'user_email': email,
                'user_role': user.role,
            }
            
            # Add theme preference if available
            if hasattr(user, 'theme_preference') and user.theme_preference:
                params['theme_preference'] = user.theme_preference
            
            # Redirect to Flutter app with SSO tokens
            redirect_url = f"{flutter_url}?{urlencode(params)}"
            return redirect(redirect_url)
            
        except Exception as e:
            logger.error(f"SSO Login Error: {str(e)}")
            return HttpResponse(
                f"SSO login failed: {str(e)}",
                status=500
            )
    
    def check_employee_status_from_hrm(self, email):
        """
        Call HRM API to check employee active status
        Returns: dict with is_active status or None on error
        """
        try:
            # HRM API endpoint - use configured URL from settings
            # hrm_base_url = getattr(settings, 'HRM_BASE_URL', 'https://hrmbackendapi.meridahr.com')
            # hrm_api_url = f"{hrm_base_url}/root/api/check-employee-status/{email}/"
            hrm_api_url = getattr(settings, 'HRM_API_URL', 'http://localhost:8001/root/api/check-employee-status/{email}/')
            
            response = requests.get(hrm_api_url, timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"HRM API returned status {response.status_code} for {email}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Failed to call HRM API: {str(e)}")
            return None
    
    def fetch_full_employee_data(self, email):
        """
        Fetch complete employee details from HRM API
        Returns: dict with full employee data or None on error
        """
        try:
            # HRM API endpoint with full_details parameter - use configured URL from settings
            # hrm_base_url = getattr(settings, 'HRM_BASE_URL', 'https://hrmbackendapi.meridahr.com/')
            hrm_base_url = getattr(settings, 'HRM_BASE_URL', 'http://localhost:8001/')
            hrm_api_url = f"{hrm_base_url}/root/api/check-employee-status/{email}/?full_details=true"
            
            response = requests.get(hrm_api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('employee_details', None)
            else:
                logger.warning(f"Failed to fetch full employee details for {email}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Failed to fetch full employee data from HRM: {str(e)}")
            return None
    
    def sync_employee_profile(self, user, employee_data, is_active):
        """
        Sync employee profile with complete data from HRM
        """
        from datetime import datetime
        
        def parse_date(date_str):
            if date_str:
                try:
                    return datetime.fromisoformat(date_str).date()
                except:
                    return None
            return None
        
        # Prepare employee defaults
        employee_defaults = {
            'name': employee_data.get('name', ''),
            'email': employee_data.get('email', ''),
            'phone': employee_data.get('phone', ''),
            'secondary_phone': employee_data.get('secondary_phone', ''),
            'secondary_email': employee_data.get('secondary_email', ''),
            'address': employee_data.get('address', ''),
            'city': employee_data.get('city', ''),
            'state': employee_data.get('state', ''),
            'pincode': employee_data.get('pincode', ''),
            'role': employee_data.get('hrm_role') or employee_data.get('employment_type', ''),
            'department': employee_data.get('department', ''),
            'employment_type': employee_data.get('employment_type', ''),
            'designation': employee_data.get('designation', ''),
            'position': employee_data.get('position', ''),
            'work_location': employee_data.get('work_location', ''),
            'hrm_role': employee_data.get('hrm_role', ''),
            'reporting_manager_id': employee_data.get('reporting_manager_id', ''),
            'reporting_manager_name': employee_data.get('reporting_manager_name', ''),
            'date_of_joining': parse_date(employee_data.get('date_of_joining')),
            'date_of_birth': parse_date(employee_data.get('date_of_birth')),
            'probation_status': employee_data.get('probation_status', ''),
            'probation_from': parse_date(employee_data.get('probation_from')),
            'probation_to': parse_date(employee_data.get('probation_to')),
            'internship_from': parse_date(employee_data.get('internship_from')),
            'internship_to': parse_date(employee_data.get('internship_to')),
            'is_active': is_active,
            'employee_status': employee_data.get('employee_status', 'active'),
            'profile_verification': employee_data.get('profile_verification', ''),
            'employee_id': employee_data.get('employee_id', ''),
        }
        
        # Update or create employee profile
        Employee.objects.update_or_create(
            user=user,
            defaults=employee_defaults
        )
        
        # Sync phone number to User table
        if employee_data.get('phone'):
            user.phone_number = employee_data.get('phone')
            user.save(update_fields=['phone_number'])
        
        logger.info(f"Employee profile synced successfully for {user.email}")
    
    def sync_all_employees_from_hrm(self):
        """
        Sync all active employees from HRM to DAS
        Called when admin logs in
        Returns dict with sync results
        """
        import secrets
        from django.utils import timezone
        
        # Get HRM URL from settings
        # hrm_url = getattr(settings, 'HRM_BASE_URL', 'https://hrmbackendapi.meridahr.com/')
        hrm_url = getattr(settings, 'HRM_BASE_URL', 'http://localhost:8001/')
        hrm_api_url = f"{hrm_url}/root/api/check-employee-status/{email}/"
        
        try:
            # Fetch all active employees from HRM
            response = requests.get(
                f'{hrm_url}/root/api/employees-active/',
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f'Failed to fetch employees from HRM. Status: {response.status_code}')
                return None
            
            data = response.json()
            employees = data.get('employees', [])
            
            if not employees:
                return {'created': 0, 'updated': 0, 'total': 0}
            
            created_count = 0
            updated_count = 0
            
            for emp_data in employees:
                try:
                    email = emp_data.get('email')
                    
                    if not email:
                        continue
                    
                    # Map HRM designation to DAS role
                    das_role = self.map_das_role(emp_data.get('designation', ''))
                    
                    # Create or update User
                    user, created = User.objects.update_or_create(
                        email=email,
                        defaults={
                            'hrm_employee_id': emp_data.get('employee_Id'),
                            'employee_name': emp_data.get('full_name'),
                            'employee_type': emp_data.get('Employeement_Type'),
                            'designation': emp_data.get('designation'),
                            'hrm_department': emp_data.get('department'),
                            'role': das_role,
                            'location': emp_data.get('work_location'),
                            'date_of_joining': emp_data.get('hired_date'),
                            'is_active_in_hrm': True,
                            'last_sync_time': timezone.now(),
                            'is_active': True,
                        }
                    )
                    
                    # Set password for new users
                    if created:
                        random_password = secrets.token_urlsafe(16)
                        user.set_password(random_password)
                        user.save()
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    # Create or update Employee profile
                    def parse_date(date_str):
                        if date_str:
                            try:
                                from datetime import datetime
                                return datetime.fromisoformat(date_str).date()
                            except:
                                return None
                        return None
                    
                    Employee.objects.update_or_create(
                        user=user,
                        defaults={
                            'name': emp_data.get('full_name', ''),
                            'email': emp_data.get('email', ''),
                            'phone': emp_data.get('phone', ''),
                            'role': emp_data.get('designation', ''),
                            'department': emp_data.get('department', ''),
                            'employment_type': emp_data.get('Employeement_Type', ''),
                            'designation': emp_data.get('designation', ''),
                            'work_location': emp_data.get('work_location', ''),
                            'date_of_joining': parse_date(emp_data.get('hired_date')),
                            'date_of_birth': parse_date(emp_data.get('date_of_birth')),
                            'is_active': True,
                            'employee_status': 'active',
                            'employee_id': emp_data.get('employee_Id', ''),
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"Error syncing employee {emp_data.get('email', 'unknown')}: {str(e)}")
                    continue
            
            return {
                'created': created_count,
                'updated': updated_count,
                'total': len(employees)
            }
            
        except requests.exceptions.Timeout:
            logger.error('HRM service timeout during employee sync')
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to connect to HRM service: {str(e)}')
            return None
        except Exception as e:
            logger.error(f'Unexpected error during employee sync: {str(e)}')
            return None
    
    def map_das_role(self, hrm_role):
        """
        Map HRM role/employment type to DAS role
        HRM Roles: Admin, HR, Employee, Recruiter, intern, permanent, Trainee, Consultant
        DAS Roles: ADMIN, MANAGER, TEAMLEAD, EMPLOYEE
        """
        role_mapping = {
            # HRM Designation -> DAS Role
            'Admin': 'ADMIN',
            'HR': 'MANAGER',
            'Recruiter': 'EMPLOYEE',
            'Employee': 'EMPLOYEE',
            # HRM Employment Type -> DAS Role
            'intern': 'EMPLOYEE',
            'permanent': 'EMPLOYEE',
            'Trainee': 'EMPLOYEE',
            'Consultant': 'EMPLOYEE',
        }
        
        # Default to EMPLOYEE if role not found
        return role_mapping.get(hrm_role, 'EMPLOYEE')


class InactiveUserView(View):
    """
    View for inactive users
    Displays message that user account is inactive
    """
    
    def get(self, request):
        # Logout inactive user
        if request.user.is_authenticated:
            logout(request)
        
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Account Inactive</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 500px;
                }
                h1 {
                    color: #e74c3c;
                    margin-bottom: 20px;
                }
                p {
                    color: #555;
                    font-size: 16px;
                    line-height: 1.6;
                }
                .icon {
                    font-size: 64px;
                    margin-bottom: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">⚠️</div>
                <h1>Account Inactive</h1>
                <p>Your employee account has been deactivated.</p>
                <p>Please contact your HR administrator for assistance.</p>
                <p>All projects and data are currently hidden.</p>
            </div>
        </body>
        </html>
        """
        
        return HttpResponse(html_content)
