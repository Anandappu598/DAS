from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny

User = get_user_model()

# DEVELOPMENT: Custom AnonymousUser with required attributes
class DevelopmentAnonymousUser:
    """Anonymous user for development - has all attributes needed"""
    is_authenticated = False
    id = None
    email = 'anonymous@development.local'
    role = 'ADMIN'  # Treat as admin in dev
    department = None
    phone_number = None
    theme_preference = 'auto'
    is_active = True
    
    def __str__(self):
        return 'AnonymousUser (Development)'

class ImpersonationJWTAuthentication(JWTAuthentication):
    """
    Extends simplejwt JWTAuthentication to allow 'ADMIN' users to impersonate
    other users via the X-Impersonate-User header.
    """
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        
        user, token = result
        
        # Check if user is an ADMIN or MANAGER attempting to impersonate
        if user.role in ['ADMIN', 'MANAGER']:
            impersonate_id = request.headers.get('X-Impersonate-User')
            if impersonate_id:
                try:
                    target_user = User.objects.get(id=impersonate_id)
                    # We return the target_user but keep the original token
                    # We can also attach the original admin/manager user to the request for logging
                    request.admin_user = user 
                    request.is_impersonated = True
                    return target_user, token
                except User.DoesNotExist:
                    pass
                    
        return user, token
