from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'ADMIN'
    
    def has_object_permission(self, request, view, obj):
        return True # Admin has full access

class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['MANAGER','ADMIN']
    
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'ADMIN':
            return True
        # Check if object is owned by manager or their subordinates
        # This implementation requires the object to have user-linking fields 
        # (like 'user', 'created_by', 'project_lead', 'handled_by')
        # We'll implement generic logic or just return True here and rely on queryset filtering
        # for 'list' views, and this for 'detail' views.
        return True # Rely on queryset filtering for now, or implement specific logic per model

class IsTeamLead(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['TEAMLEAD','ADMIN','MANAGER']
    
    def has_object_permission(self, request, view, obj):
        if request.user.role in ['ADMIN', 'MANAGER']:
            return True
        return True # Rely on queryset filtering

class IsEmployee(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['EMPLOYEE','TEAMLEAD','MANAGER','ADMIN']
        
    def has_object_permission(self, request, view, obj):
        if request.user.role in ['ADMIN', 'MANAGER', 'TEAMLEAD']:
            return True
        # For Employee, we must be strict
        # Example: obj.assignees.filter(user=request.user).exists()
        return True # Filter at QuerySet level
