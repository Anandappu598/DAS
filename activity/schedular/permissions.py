from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
   def has_permission(self, request, view):
      return request.user.is_authenticated and request.user.role == 'ADMIN'
   
class IsManager(BasePermission):
   def has_permission(self, request, view):
      return request.user.is_authenticated and request.user.role in ['MANAGER','ADMIN']
   
class IsTeamLead(BasePermission):
   def has_permission(self, request, view):
      return request.user.is_authenticated and request.user.role in ['TEAMLEAD','ADMIN','MANAGER']
   
class IsEmployee(BasePermission):
   def has_permission(self, request, view):
      return request.user.is_authenticated and request.user.role in ['EMPLOYEE','TEAMLEAD','MANAGER','ADMIN']