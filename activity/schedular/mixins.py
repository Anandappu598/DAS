from django.db.models import Q
from .models import User

class RoleBasedQuerySetMixin:
    """
    Mixin to filter querysets based on user role.
    This ensures users only see data they are permitted to see.
    """
    
    def get_queryset_for_role(self, queryset, user):
        # Admin sees everything
        if user.role == 'ADMIN':
            return queryset
        
        # Managers see everything in their hierarchy
        if user.role == 'MANAGER':
            subordinates = user.get_all_subordinates()
            # Assuming 'user', 'created_by', 'assigned_to', or similar fields exist on the model
            # This is a generic fallback, but specific mixins below act better
            if hasattr(queryset.model, 'user'):
                return queryset.filter(Q(user=user) | Q(user__in=subordinates))
            elif hasattr(queryset.model, 'created_by'):
                return queryset.filter(Q(created_by=user) | Q(created_by__in=subordinates))
            return queryset

        # Team Leads see their team's data
        if user.role == 'TEAMLEAD':
            team_members = user.get_team_members()
            if hasattr(queryset.model, 'user'):
                return queryset.filter(Q(user=user) | Q(user__in=team_members))
            elif hasattr(queryset.model, 'created_by'):
                 return queryset.filter(Q(created_by=user) | Q(created_by__in=team_members))
            return queryset
            
        # Employees see only their own data
        if user.role == 'EMPLOYEE':
            if hasattr(queryset.model, 'user'):
                return queryset.filter(user=user)
            elif hasattr(queryset.model, 'created_by'):
                return queryset.filter(created_by=user)
                
        return queryset.none()  # Default deny

class ProjectQuerySetMixin(RoleBasedQuerySetMixin):
    """Specific filtering for Projects"""
    
    def get_queryset(self):
        # Ensure we call the parent get_queryset if it exists to preserve logic
        queryset = super().get_queryset() if hasattr(super(), 'get_queryset') else self.queryset
        user = self.request.user
        
        if not user.is_authenticated:
            return queryset.none()
        
        # Check if this is for planner catalog - restrict to assigned items only
        for_planner = self.request.query_params.get('for_planner', '').lower() == 'true'
        
        # Date filtering logic for dashboard/analytics
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date and end_date:
            # A project is active during the interval if it starts before interval ends AND ends after interval starts
            queryset = queryset.filter(
                due_date__gte=start_date,
                start_date__lte=end_date
            )
        elif start_date:
            queryset = queryset.filter(due_date__gte=start_date)
        elif end_date:
            queryset = queryset.filter(start_date__lte=end_date)
            
        if for_planner:
            # For planner catalog: ALL users (including ADMIN) only see projects where they have assigned tasks
            return queryset.filter(
                Q(project_lead=user) |
                Q(handled_by=user) |
                Q(tasks__assignees__user=user)
            ).distinct()
        
        # Normal behavior: Admin sees all for dashboard/management
        if user.role == 'ADMIN':
            return queryset
            
        if user.role == 'MANAGER':
            # Manager sees projects where they are lead, handled_by, or created_by
            # OR projects where the lead/handler is one of their subordinates
            subordinates = user.get_all_subordinates()
            return queryset.filter(
                Q(project_lead=user) | 
                Q(handled_by=user) | 
                Q(created_by=user) |
                Q(project_lead__in=subordinates) |
                Q(handled_by__in=subordinates) |
                Q(created_by__in=subordinates)
            ).distinct()
            
        if user.role == 'TEAMLEAD':
            # Team Lead sees projects where they are involved
            # OR projects where their direct reports are involved
            team_members = user.get_team_members()
            return queryset.filter(
                Q(project_lead=user) | 
                Q(handled_by=user) | 
                Q(created_by=user) |
                Q(project_lead__in=team_members) |
                Q(handled_by__in=team_members) |
                Q(created_by__in=team_members) |
                # Also include projects where specific TASKS are assigned to team
                Q(tasks__assignees__user__in=team_members)
            ).distinct()
            
        if user.role == 'EMPLOYEE':
            # Employee only sees projects assigned to them directly (if any)
            # OR projects containing tasks assigned to them
            return queryset.filter(
                Q(project_lead=user) |
                Q(handled_by=user) |
                Q(assignees=user) |
                Q(tasks__assignees__user=user)
            ).distinct()
            
        return queryset.none()

class TaskQuerySetMixin(RoleBasedQuerySetMixin):
    """Specific filtering for Tasks"""
    
    def get_queryset(self):
        queryset = super().get_queryset() if hasattr(super(), 'get_queryset') else self.queryset
        user = self.request.user
        
        if not user.is_authenticated:
            return queryset.none()
        
        # Date filtering logic for tasks: inclusion if due date falls within range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date and end_date:
            queryset = queryset.filter(due_date__range=[start_date, end_date])
        elif start_date:
            queryset = queryset.filter(due_date__gte=start_date)
        elif end_date:
            queryset = queryset.filter(due_date__lte=end_date)

        # Check if this is for planner catalog - restrict to assigned tasks only
        for_planner = self.request.query_params.get('for_planner', '').lower() == 'true'
        
        if for_planner:
            # For planner catalog: ALL users (including ADMIN) only see tasks assigned to them
            return queryset.filter(
                assignees__user=user
            ).distinct()
        
        # Normal behavior: Admin sees all for dashboard/management
        if user.role == 'ADMIN':
            return queryset
            
        if user.role == 'MANAGER':
            subordinates = user.get_all_subordinates()
            return queryset.filter(
                Q(assignees__user=user) |
                Q(project__project_lead=user) |
                Q(project__handled_by=user) |
                Q(assignees__user__in=subordinates) |
                Q(project__project_lead__in=subordinates)
            ).distinct()
            
        if user.role == 'TEAMLEAD':
            team_members = user.get_team_members()
            return queryset.filter(
                Q(assignees__user=user) |
                Q(project__project_lead=user) |
                Q(assignees__user__in=team_members)
            ).distinct()
            
        if user.role == 'EMPLOYEE':
            # Employees only see tasks assigned to them Or the task in the project that assigned to them
            return queryset.filter(
                Q(assignees__user=user) | 
                Q(project__assignees=user) |
                Q(project__project_lead=user) |
                Q(project__handled_by=user)
            ).distinct()
            
        return queryset.none()

