from django.shortcuts import render
from rest_framework import generics, status, viewsets, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from .serializers import (LoginSerializers, SignupWithOTPSerializer, VerifySignupOTPSerializer,
                          ForgotPasswordSerializer, ResetPasswordSerializer, ProjectSerializer, ApprovalRequestSerializer,
                          ApprovalResponseSerializer, TaskSerializer, TaskAssigneeSerializer, SubTaskSerializer, StickyNoteSerializer,
                          CatalogSerializer, TodayPlanSerializer, ActivityLogSerializer, 
                          PendingSerializer, DaySessionSerializer, TeamInstructionSerializer, UserSerializer, UserPreferenceSerializer, NotificationSerializer,
                          ProjectLineChartDataSerializer, TaskLineChartDataSerializer, CompletionChartDataSerializer,
                          DailyPlannerSerializer, ProjectDashboardSerializer, ProjectAnalyticsSerializer, DailyTrendSerializer)
from .utils import (create_otp_record, send_password_reset_confirmation, send_password_reset_otp, 
                    send_signup_otp_to_admin, send_account_approval_email, verify_otp)
from .models import (User, Projects, ApprovalRequest, ApprovalResponse, Task, TaskAssignee, SubTask, StickyNote, 
                     Catalog, TodayPlan, ActivityLog, Pending, DaySession, TeamInstruction, Notification, Employee, DailyPlanner)
from .mixins import ProjectQuerySetMixin, TaskQuerySetMixin
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .permissions import IsAdmin, IsEmployee, IsManager, IsTeamLead
from django.db import models, transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import requests
import secrets

# Development helper: Safe user role access
def get_user_role(user, default='ADMIN'):
    """Get user role safely, handling AnonymousUser during development"""
    if user.is_authenticated:
        return getattr(user, 'role', default)
    # For development with disabled auth, treat anonymous as ADMIN
    return default

# Create your views here.

class LoginViewSet(viewsets.GenericViewSet):
    serializer_class = LoginSerializers
    
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": user.id,
            "role": user.role,
            "email": user.email,
            "theme_preference": user.theme_preference
        })
    

class SignupViewSet(viewsets.GenericViewSet):
    serializer_class = SignupWithOTPSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_record = create_otp_record(
            email=serializer.validated_data['email'],
            otp_type='signup',
            user_data=serializer.validated_data
        )
        send_signup_otp_to_admin(
            email=serializer.validated_data['email'],
            role=serializer.validated_data['role'],
            otp=otp_record.otp
        )
        return Response({
            "message": "Signup request sent to admin. Please get the OTP from admin and enter it to complete signup.",
            "email": serializer.validated_data['email']
        })

    
class VerifySignupViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = VerifySignupOTPSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_record = verify_otp(serializer.validated_data['email'], serializer.validated_data['otp'], 'signup')
        if not otp_record:
            return Response({"error": "Invalid or expired OTP. Please request a new signup."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark OTP as verified first to prevent duplicate user creation
        otp_record.is_verified = True
        otp_record.save()
        
        # Now create the user
        user_data = otp_record.user_data
        user = User.objects.create_user(
            email=user_data['email'],
            password=user_data['password'], role=user_data.get('role', 'EMPLOYEE')
        )
        send_account_approval_email(user_data['email'])
        return Response({
            "message": "Signup completed successfully! You can now login with your credentials.",
            "email": user_data['email'],
            "role": user_data.get('role', 'EMPLOYEE')
        }, status=status.HTTP_201_CREATED)
    

class ForgotPasswordViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_record = create_otp_record(email=serializer.validated_data['email'], otp_type='forgot_password')
        send_password_reset_otp(serializer.validated_data['email'], otp_record.otp)
        return Response({"message": "OTP sent to email"})

class ResetPasswordViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_record = verify_otp(serializer.validated_data['email'], serializer.validated_data['otp'], 'forgot_password')
        if not otp_record:
            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.get(email=serializer.validated_data['email'])
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        otp_record.is_verified = True
        otp_record.save()
        send_password_reset_confirmation(user.email)
        return Response({"message": "Password reset successful"})


class UserPreferencesViewSet(viewsets.GenericViewSet):
    """ViewSet for managing user preferences like theme"""
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile and preferences"""
        user = request.user
        if not user.is_authenticated:
            return Response({'detail': 'Not authenticated'}, status=401)
        return Response({
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'department': user.department.name if user.department else None,
            'department_id': user.department.id if user.department else None,
            'phone_number': user.phone_number or '',
            'theme_preference': user.theme_preference
        })
    
    @action(detail=True, methods=['get'], url_path='profile')
    def user_profile(self, request, pk=None):
        """Get specific user profile by ID"""
        try:
            user = User.objects.select_related('employee_profile').get(pk=pk)
            
            # Build response with user data
            response_data = {
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'role_display': user.get_role_display(),
                'department': user.department.name if user.department else None,
                'department_id': user.department.id if user.department else None,
                'phone_number': user.phone_number or '',
                'is_active': user.is_active
            }
            
            # Add employee data if available
            if hasattr(user, 'employee_profile') and user.employee_profile:
                emp = user.employee_profile
                response_data.update({
                    'name': emp.name if emp.name else user.email.split('@')[0].replace('.', ' ').title(),
                    'employee_id': emp.employee_id or '',
                    'designation': emp.designation or '',
                    'department': emp.department or response_data['department']
                })
            else:
                # Fallback if no employee profile
                response_data['name'] = user.email.split('@')[0].replace( '.', ' ').title()
            
            return Response(response_data)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['patch'])
    def theme(self, request):
        """Update theme preference"""
        serializer = UserPreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.theme_preference = serializer.validated_data['theme_preference']
        user.save(update_fields=['theme_preference'])
        
        return Response({
            "message": "Theme preference updated",
            "theme_preference": user.theme_preference
        })


class ProjectViewSet(ProjectQuerySetMixin, viewsets.ModelViewSet):
      serializer_class = ProjectSerializer
      queryset = Projects.objects.all() # Base queryset, overridden by mixin
      
      filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
      filterset_fields = ['status', 'handled_by', 'created_by', 'project_lead']
      search_fields = ['name', 'description']
      ordering_fields = ['start_date', 'due_date', 'create_date', 'name']
      ordering = ['-create_date']

      def get_queryset(self):
          # SSO: Check if user is active
          # If user is inactive, return empty queryset (hide all projects)
          if not self.request.user.is_active:
              from django.shortcuts import redirect
              return Projects.objects.none()
          
          queryset = super().get_queryset()
          
          # Handle 'my projects' filter (where user is creator or assignee)
          if self.request.query_params.get('filter') == 'my':
              user = self.request.user
              
              # Allow Admin to filter by specific user_id
              if user.role == 'ADMIN' and self.request.query_params.get('user_id'):
                  try:
                      user_id = self.request.query_params.get('user_id')
                      user = User.objects.get(id=user_id)
                  except User.DoesNotExist:
                      pass # Fallback to request.user if not found

              # Filter projects where user is creator, lead, handled_by, or assigned to any task
              queryset = queryset.filter(
                  models.Q(created_by=user) | 
                  models.Q(assignees=user) |
                  models.Q(project_lead=user) | 
                  models.Q(handled_by=user) |
                  models.Q(tasks__assignees__user=user)
              ).distinct()
          
          return queryset

      def list(self, request, *args, **kwargs):
          # Override list to handle 'all_projects' param to disable pagination
          queryset = self.filter_queryset(self.get_queryset())

          if request.query_params.get('all_projects') == 'true':
              serializer = self.get_serializer(queryset, many=True)
              return Response(serializer.data)

          page = self.paginate_queryset(queryset)
          if page is not None:
              serializer = self.get_serializer(page, many=True)
              return self.get_paginated_response(serializer.data)

          serializer = self.get_serializer(queryset, many=True)
          return Response(serializer.data)

      def get_serializer_class(self):
          if self.action in ['list', 'retrieve', 'create_with_tasks']:
              from .serializers import ProjectDetailSerializer
              return ProjectDetailSerializer
          return ProjectSerializer
      
      def perform_create(self, serializer):
          """Override create to add approval logic"""
          user = self.request.user
          
          # Handle unauthenticated users (AllowAny testing)
          if not user or not user.is_authenticated:
              project = serializer.save()
              project.is_approved = True
              project.save()
              return
          
          with transaction.atomic():
              project = serializer.save(created_by=user)
              
              if user.role == 'ADMIN':
                  # Admin projects are auto-approved
                  project.is_approved = True
                  project.save()
              else:
                  # Non-admin: requires admin approval
                  project.is_approved = False
                  project.save()
                  
                  approval_req = ApprovalRequest.objects.create(
                      reference_type='PROJECT',
                      reference_id=project.id,
                      approval_type='CREATION',
                      requested_by=user,
                      request_data={
                          'project_name': project.name,
                          'description': project.description,
                          'requested_by': user.email,
                      }
                  )
              # WebSocket notification to admins is handled by the
              # approval_request_notification signal in signals.py automatically

      @action(detail=False, methods=['post'], url_path='create-with-tasks')
      def create_with_tasks(self, request):
          """Create a project with tasks, assignees, and milestones in one call.
          
          POST /api/projects/create-with-tasks/
          Body: {
              "name": "Project Name",
              "description": "...",
              "project_lead": 1,       // user ID (optional)
              "deadline": "2026-03-15", // optional
              "tasks": [
                  {
                      "name": "Task 1",
                      "priority": "High",
                      "start_date": "2026-02-13",
                      "end_date": "2026-02-20",
                      "assignees": [1, 2],   // user IDs
                      "milestones": ["Design Approved", "API Done"]
                  }
              ]
          }
          """
          from .serializers import ProjectCreateWithTasksSerializer, ProjectDetailSerializer
          serializer = ProjectCreateWithTasksSerializer(data=request.data, context={'request': request})
          if serializer.is_valid():
              with transaction.atomic():
                  user = request.user
                  # Ensure created_by is set
                  project = serializer.save(created_by=user if user.is_authenticated else None)
                  
                  # Handle approval logic - REQUIRE APPROVAL FOR ALL (Including ADMIN)
                  if not user.is_authenticated:
                      project.is_approved = True
                      project.save()
                  elif user.role == 'ADMIN':
                      # Admin projects are auto-approved
                      project.is_approved = True
                      project.save()
                  else:
                      # Non-admin: requires admin approval
                      project.is_approved = False
                      project.save()
                      
                      ApprovalRequest.objects.create(
                          reference_type='PROJECT',
                          reference_id=project.id,
                          approval_type='CREATION',
                          requested_by=user,
                          request_data={
                              'project_name': project.name,
                              'description': project.description,
                              'requested_by': user.email,
                          }
                      )
                      
                      # ALSO SYNC INDIVIDUAL TASKS WITH APPROVAL WORKFLOW
                      created_tasks = getattr(project, '_created_tasks', [])
                      for task in created_tasks:
                          task.status = 'PENDING_APPROVAL'
                          task.save()
                          
                          # Use a simpler request data for initial project tasks
                          ApprovalRequest.objects.create(
                              reference_type='TASK',
                              reference_id=task.id,
                              approval_type='CREATION',
                              requested_by=user,
                              request_data={
                                  'title': task.title,
                                  'project': project.name,
                                  'is_initial_task': True
                              }
                          )
                  # WebSocket notification to admins is handled by the
                  # approval_request_notification signal in signals.py automatically

              # Return full project detail
              detail_serializer = ProjectDetailSerializer(project)
              return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
          
          return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
      
      def _repair_limbo_tasks(self, project):
          """Helper to detect and fix tasks in a limbo state (pending approval with no request)"""
          tasks_in_limbo = project.tasks.filter(
              models.Q(approval_status='pending_completion') | 
              models.Q(status='PENDING_APPROVAL')
          )
          
          from .models import ApprovalRequest, Notification
          
          for task in tasks_in_limbo:
              # Check if an active ApprovalRequest exists
              has_request = ApprovalRequest.objects.filter(
                  reference_type='TASK',
                  reference_id=task.id,
                  status='PENDING'
              ).exists()
              
              if not has_request:
                  # This task is in limbo!
                  pending_subtasks_count = task.subtasks.exclude(status='DONE').count()
                  
                  if pending_subtasks_count > 0:
                      # Fix A: Task has 0% or partial milestones, move it back to TASK BUCKET
                      # This fixes the 'drfg' issue by moving it from Approval to Todo
                      task.status = 'PENDING'
                      task.approval_status = None
                      task.save()
                  else:
                      # Fix B: Task is actually complete, create the missing approval request
                      # This ensures Admin finally sees a valid completion request
                      with transaction.atomic():
                          task.status = 'PENDING_APPROVAL'
                          task.approval_status = 'pending_completion'
                          task.save()
                          
                          ApprovalRequest.objects.create(
                              reference_type='TASK',
                              reference_id=task.id,
                              approval_type='COMPLETION',
                              requested_by=task.project.created_by or User.objects.filter(role='ADMIN').first(),
                              request_data={
                                  'task_title': task.title,
                                  'project': project.name,
                                  'completed_date': str(timezone.now().date())
                              }
                          )

      @action(detail=True, methods=['get'], url_path='detail-view')
      def detail_view(self, request, pk=None):
          """Get detailed project information with tasks and subtasks"""
          from .serializers import ProjectDetailSerializer
          project = self.get_object()
          
          # SELF-HEALING: fix any tasks caught in Approval limbo before returning data
          self._repair_limbo_tasks(project)
          
          serializer = ProjectDetailSerializer(project)
          return Response(serializer.data)
      
      @action(detail=True, methods=['get'], url_path='gantt-view')
      def gantt_view(self, request, pk=None):
          """Get Gantt chart data for project tasks with timeline and assignees"""
          from .serializers import GanttTaskSerializer
          project = self.get_object()
          
          # Get all tasks for the project ordered by start_date
          tasks = project.tasks.all().order_by('start_date', 'due_date')
          
          # Serialize tasks with Gantt chart specific data
          serializer = GanttTaskSerializer(tasks, many=True)
          
          # Get project date range for timeline context
          task_dates = tasks.values_list('start_date', 'due_date')
          start_dates = [d[0] for d in task_dates if d[0]]
          due_dates = [d[1] for d in task_dates if d[1]]
          
          timeline_start = min(start_dates) if start_dates else None
          timeline_end = max(due_dates) if due_dates else None
          
          return Response({
              'project_id': project.id,
              'project_name': project.name,
              'timeline_start': timeline_start,
              'timeline_end': timeline_end,
              'tasks': serializer.data
          })
      
      @action(detail=True, methods=['get'], url_path='grid-view')
      def grid_view(self, request, pk=None):
          """Get task data for the project grid view"""
          from .serializers import GridViewTaskSerializer
          project = self.get_object()
          tasks = project.tasks.all().order_by('created_at')
          serializer = GridViewTaskSerializer(tasks, many=True)
          return Response(serializer.data)
      
      @action(detail=True, methods=['post'])
      def create_task(self, request, pk=None):
          """Create a new standard task for this project"""
          from .serializers import TaskCreateSerializer, TaskDetailSerializer
          project = self.get_object()
          
          serializer = TaskCreateSerializer(data=request.data)
          if serializer.is_valid():
              with transaction.atomic():
                  task = serializer.save(project=project)
                  
                  user = request.user
                  # REQUIRE APPROVAL FOR ALL NON-ADMIN ROLES
                  if user.role != 'ADMIN':
                      task.status = 'PENDING_APPROVAL'
                      task.save()
                      ApprovalRequest.objects.create(
                          reference_type='TASK',
                          reference_id=task.id,
                          approval_type='CREATION',
                          requested_by=user,
                          request_data=serializer.data
                      )
  
              response_serializer = TaskDetailSerializer(task)
              return Response(response_serializer.data, status=status.HTTP_201_CREATED)
          
          return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

      @action(detail=True, methods=['post'])
      def create_recurring_task(self, request, pk=None):
          """Create a new recurring task for this project"""
          from .serializers import RecurringTaskCreateSerializer, TaskDetailSerializer
          project = self.get_object()
          
          serializer = RecurringTaskCreateSerializer(data=request.data)
          if serializer.is_valid():
              with transaction.atomic():
                  task = serializer.save(project=project)

                  user = request.user
                  # REQUIRE APPROVAL FOR ALL NON-ADMIN ROLES
                  if user.role != 'ADMIN':
                      task.status = 'PENDING_APPROVAL'
                      task.save()
                      ApprovalRequest.objects.create(
                          reference_type='TASK',
                          reference_id=task.id,
                          approval_type='CREATION',
                          requested_by=user,
                          request_data=serializer.data
                      )

              response_serializer = TaskDetailSerializer(task)
              return Response(response_serializer.data, status=status.HTTP_201_CREATED)
          
          return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

      @action(detail=True, methods=['get'])
      def dashboard(self, request, pk=None):
          """GET /api/projects/{id}/dashboard/ - KPI summary for planned vs achieved"""
          project = self.get_object()
          
          planned_total = project.get_planned_hours_total()
          achieved_total = project.get_achieved_hours()
          
          data = {
              "planned_hours_budget": float(project.working_hours),
              "planned_hours_total": float(planned_total),
              "achieved_hours": float(achieved_total),
              "remaining_hours": float(max(0, planned_total - achieved_total)),
              "completion_percentage": round((achieved_total / planned_total * 100) if planned_total > 0 else 0, 2),
              "task_stats": {
                  "total": project.tasks.count(),
                  "completed": project.tasks.filter(status='DONE').count(),
                  "pending": project.tasks.exclude(status='DONE').count()
              }
          }
          return Response(data)

      @action(detail=True, methods=['get'])
      def analytics(self, request, pk=None):
          """GET /api/projects/{id}/analytics/ - Data for Bar charts"""
          project = self.get_object()
          tasks = project.tasks.all()
          
          data = []
          for task in tasks:
              data.append({
                  "task_name": task.title,
                  "planned": float(task.planned_hours),
                  "achieved": float(task.get_achieved_hours())
              })
          
          return Response(data)

      @action(detail=True, methods=['post'])
      def create_routine_task(self, request, pk=None):
          """Create a new routine task for this project"""
          from .serializers import RoutineTaskCreateSerializer, TaskDetailSerializer
          project = self.get_object()
          
          serializer = RoutineTaskCreateSerializer(data=request.data)
          if serializer.is_valid():
              with transaction.atomic():
                  task = serializer.save(project=project)
  
                  user = request.user
                  # REQUIRE APPROVAL FOR ALL NON-ADMIN ROLES
                  if user.role != 'ADMIN':
                      task.status = 'PENDING_APPROVAL'
                      task.save()
                      ApprovalRequest.objects.create(
                          reference_type='TASK',
                          reference_id=task.id,
                          approval_type='CREATION',
                          requested_by=user,
                          request_data=serializer.data
                      )
  
              response_serializer = TaskDetailSerializer(task)
              return Response(response_serializer.data, status=status.HTTP_201_CREATED)
          
          return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

      @action(detail=True, methods=['post'])
      def request_completion(self, request, pk=None):
          """Request approval for project completion"""
          project = self.get_object()
          user = request.user
          
          # Check if user has permission to request completion
          if (not user.is_authenticated or user.role not in ['ADMIN', 'MANAGER', 'TEAMLEAD', 'EMPLOYEE']) and user != project.created_by:
              return Response(
                  {"error": "You don't have permission to request completion for this project"},
                  status=status.HTTP_403_FORBIDDEN
              )
          
          # Check if project is already completed
          if project.status == 'COMPLETED':
              return Response(
                  {"error": "Project is already completed"},
                  status=status.HTTP_400_BAD_REQUEST
              )
          
          # Check if all tasks are completed
          pending_tasks_count = project.tasks.exclude(status='DONE').count()
          if pending_tasks_count > 0:
              return Response(
                  {"error": f"Cannot complete project. There are {pending_tasks_count} pending tasks remaining."},
                  status=status.HTTP_400_BAD_REQUEST
              )
          
          # Check if there's already a pending completion request
          existing_request = ApprovalRequest.objects.filter(
              reference_type='PROJECT',
              reference_id=project.id,
              approval_type='COMPLETION',
              status='PENDING'
          ).first()
          
          if existing_request:
              return Response(
                  {"message": "There is already a pending completion request for this project"},
                  status=status.HTTP_200_OK
              )
          
          # Set completed date
          completion_date = request.data.get('completed_date', timezone.now().date())
          project.completed_date = completion_date
          project.save()
          
          # If user is ADMIN, approve immediately
          if user.role == 'ADMIN':
              project.status = 'COMPLETED'
              project.approval_status = 'approved'
              project.save()
              
              # Notify Project Lead about completion (WebSocket)
              try:
                  if project.project_lead:
                      from .signals import send_websocket_notification
                      lead = project.project_lead
                      notif = Notification.objects.create(
                          user=lead,
                          notification_type='PROJECT_COMPLETED',
                          title='Project Completed',
                          message=f'Admin marked project "{project.name}" as completed.',
                          reference_type='project',
                          reference_id=project.id
                      )
                      send_websocket_notification(lead.id, {
                          'id': notif.id,
                          'title': notif.title,
                          'message': notif.message,
                          'type': notif.notification_type,
                          'reference_type': notif.reference_type,
                          'reference_id': notif.reference_id,
                          'created_at': str(notif.created_at),
                      })
              except Exception as e:
                  print(f"WebSocket notification error (completion): {e}")

              return Response({
                  "message": "Project marked as completed (auto-approved for admin)",
                  "project": ProjectSerializer(project).data
              })
          
          with transaction.atomic():
              # Otherwise, create approval request
              project.approval_status = 'pending_completion'
              project.save()
              
              approval_request = ApprovalRequest.objects.create(
                  reference_type='PROJECT',
                  reference_id=project.id,
                  approval_type='COMPLETION',
                  requested_by=user,
                  request_data={
                      'project_name': project.name,
                      'completed_date': str(completion_date)
                  }
              )
              
              return Response({
                  "message": "Project completion request submitted for approval",
                  "approval_request_id": approval_request.id
              }, status=status.HTTP_201_CREATED)

      @action(detail=True, methods=['post'])
      def approve_completion(self, request, pk=None):
          """Admin action to approve a project completion request"""
          project = self.get_object()
          user = request.user
          
          if user.role != 'ADMIN':
              return Response(
                  {"error": "Only admins can approve project completions"},
                  status=status.HTTP_403_FORBIDDEN
              )
              
          with transaction.atomic():
              # Check for milestones requirement
              pending_tasks = project.tasks.exclude(status='DONE').count()
              if pending_tasks > 0:
                  return Response(
                      {"error": f"Cannot approve completion. Project has {pending_tasks} pending tasks."},
                      status=status.HTTP_400_BAD_REQUEST
                  )

              project.status = 'COMPLETED'
              project.approval_status = 'approved'
              project.completed_date = timezone.now().date()
              project.save()
              
              # Update associated ApprovalRequest
              ApprovalRequest.objects.filter(
                  reference_type='PROJECT',
                  reference_id=project.id,
                  approval_type='COMPLETION',
                  status='PENDING'
              ).update(status='APPROVED', approved_by=user, approved_at=timezone.now())

          return Response({
              "message": "Project completion approved",
              "project": ProjectSerializer(project).data
          })

      @action(detail=True, methods=['post'])
      def reject_completion(self, request, pk=None):
          """Admin action to reject a project completion request"""
          project = self.get_object()
          user = request.user
          reason = request.data.get('reason', 'No reason provided')
          
          if user.role != 'ADMIN':
              return Response(
                  {"error": "Only admins can reject project completions"},
                  status=status.HTTP_403_FORBIDDEN
              )
              
          with transaction.atomic():
              project.status = 'ACTIVE'
              project.approval_status = 'rejected'
              project.rejection_reason = reason
              project.save()
              
              # Update associated ApprovalRequest
              ApprovalRequest.objects.filter(
                  reference_type='PROJECT',
                  reference_id=project.id,
                  approval_type='COMPLETION',
                  status='PENDING'
              ).update(status='REJECTED', reason=reason)

          return Response({"message": "Project completion rejected"})


class ApprovalRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for users to create and view approval requests"""
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = ApprovalRequestSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['reference_type', 'approval_type', 'status', 'requested_by']
    search_fields = ['requested_by__email']
    ordering_fields = ['created_at']
    
    def get_queryset(self):
        """Filter approvals based on user role"""
        user = self.request.user
        if not user.is_authenticated:
            return ApprovalRequest.objects.none()
        if user.role == 'ADMIN':
            return ApprovalRequest.objects.all()
        return ApprovalRequest.objects.filter(requested_by=user)
    
    def perform_create(self, serializer):
        """Set the requested_by field to current user"""
        serializer.save(requested_by=self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a request and update related entities"""
        approval = self.get_object()
        
        if approval.status != 'PENDING':
            return Response(
                {"error": "This request is not pending approval"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if approval.reference_type == 'PROJECT' and approval.approval_type == 'COMPLETION':
            project = Projects.objects.get(id=approval.reference_id)
            pending_tasks_count = project.tasks.exclude(status='DONE').count()
            if pending_tasks_count > 0:
                return Response(
                    {"error": f"Cannot approve project closure. There are {pending_tasks_count} pending tasks remaining."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        approval.status = 'APPROVED'
        approval.save()
        
        # Update related project/task based on approval type
        try:
            item_name = ''
            notif_title = ''
            notif_message = ''

            if approval.reference_type == 'PROJECT':
                project = Projects.objects.get(id=approval.reference_id)
                item_name = project.name
                if approval.approval_type == 'CREATION':
                    project.is_approved = True
                    project.save()
                    notif_title = 'Project Approved ✓'
                    notif_message = (
                        f'Your project "{item_name}" has been approved and is now live. '
                        f'You can start working on it!'
                    )
                elif approval.approval_type == 'COMPLETION':
                    project.status = 'COMPLETED'
                    project.approval_status = 'APPROVED'
                    project.completed_date = timezone.now().date()
                    project.save()
                    notif_title = 'Project Closed ✓'
                    notif_message = (
                        f'Admin has confirmed closure of project "{item_name}". '
                        f'The project is now marked as Completed.'
                    )

            elif approval.reference_type == 'TASK':
                task = Task.objects.get(id=approval.reference_id)
                item_name = task.title
                if approval.approval_type == 'CREATION':
                    # Task creation approved — move to active state
                    # DO NOT set approval_status='APPROVED' here!
                    # 'APPROVED' approval_status means COMPLETION approved (completed bucket).
                    # For creation approval, keep approval_status as null so the task
                    # stays in the Task Bucket for milestone work.
                    if task.status == 'PENDING_APPROVAL':
                        task.status = 'PENDING'
                        task.save()
                    notif_title = 'Task Approved ✓'
                    notif_message = (
                        f'Your task "{item_name}" has been approved. '
                        f'It is now active and ready to be worked on.'
                    )
                elif approval.approval_type == 'COMPLETION':
                    task.status = 'DONE'
                    task.approval_status = 'APPROVED'
                    task.completed_at = timezone.now().date()
                    task.save()
                    # Handle recurring task regeneration
                    if task.task_type == 'RECURRING':
                        task.regenerate_recurring_task()
                    notif_title = 'Task Completed ✓'
                    notif_message = (
                        f'Admin has confirmed completion of task "{item_name}". '
                        f'Great work!'
                    )

            # Fallback
            if not notif_title:
                notif_title = 'Approval Request Approved'
                notif_message = (
                    f'Your {approval.approval_type.lower()} request for '
                    f'{approval.reference_type.lower()} "{item_name or approval.reference_id}" has been approved.'
                )

            # Send notification to requester
            notif = Notification.objects.create(
                user=approval.requested_by,
                notification_type='APPROVAL_APPROVED',
                title=notif_title,
                message=notif_message,
                reference_type=approval.reference_type.lower(),
                reference_id=approval.reference_id
            )
            # Push real-time WebSocket notification to the requester
            try:
                from .signals import send_websocket_notification
                send_websocket_notification(approval.requested_by.id, {
                    'id': notif.id,
                    'title': notif.title,
                    'message': notif.message,
                    'type': notif.notification_type,
                    'reference_type': notif.reference_type,
                    'reference_id': notif.reference_id,
                    'created_at': str(notif.created_at),
                })
            except Exception as ws_err:
                print(f"WebSocket push error (approve): {ws_err}")
            
        except Exception as e:
            print(f"Error handling approval side effects: {e}")
            
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a request"""
        approval = self.get_object()
        reason = request.data.get('reason', 'No reason provided')
        
        if approval.status != 'PENDING':
            return Response(
                {"error": "This request is not pending approval"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        approval.status = 'REJECTED'
        approval.save()
        
        # Handle rejection side effects
        try:
            item_name = ''
            notif_title = ''
            notif_message = ''

            if approval.reference_type == 'PROJECT':
                project = Projects.objects.get(id=approval.reference_id)
                item_name = project.name
                if approval.approval_type == 'CREATION':
                    # Delete rejected project creations
                    project.delete()
                    notif_title = 'Project Request Not Approved'
                    notif_message = (
                        f'Your request to create the project "{item_name}" was not approved. '
                        f'The project has been removed. You may create a new project if needed.'
                    )
                elif approval.approval_type == 'COMPLETION':
                    # Reset approval status — project stays open for rework
                    project.approval_status = 'REJECTED'
                    project.status = 'ACTIVE'
                    project.rejection_reason = reason
                    project.save()
                    
                    # Also reset all project tasks and milestones
                    tasks = project.tasks.all()
                    tasks.update(status='IN_PROGRESS', approval_status=None, completed_at=None)
                    SubTask.objects.filter(task__in=tasks, status='DONE').update(
                        status='PENDING', 
                        completed_at=None
                    )
                    notif_title = 'Project Kept Open'
                    notif_message = (
                        f'Admin reviewed your closure request for project "{item_name}" and decided to keep it open. '
                        f'Please continue working and resubmit when ready.'
                    )

            elif approval.reference_type == 'TASK':
                task = Task.objects.get(id=approval.reference_id)
                item_name = task.title
                if approval.approval_type == 'CREATION':
                    # Delete rejected task creations
                    task.delete()
                    notif_title = 'Task Request Not Approved'
                    notif_message = (
                        f'Your request to create task "{item_name}" was not approved. '
                        f'The task has been removed. You may create a new task if needed.'
                    )
                elif approval.approval_type == 'COMPLETION':
                    # Reset task status to PENDING (Task Bucket) and clear approval flags
                    task.status = 'PENDING'
                    task.approval_status = 'REJECTED'
                    task.rejection_reason = reason
                    task.completed_at = None
                    task.save()
                        
                    # Reset subtasks for this specific task
                    task.subtasks.filter(status='DONE').update(
                        status='PENDING', 
                        completed_at=None
                    )
                    notif_title = 'Task Completion Not Confirmed'
                    notif_message = (
                        f'Admin did not confirm completion of task "{item_name}". '
                        f'The task has been set back to In Progress. Please review and resubmit when done.'
                    )

            # Fallback for unknown types
            if not notif_title:
                notif_title = 'Approval Request Rejected'
                notif_message = (
                    f'Your {approval.approval_type.lower()} request for '
                    f'{approval.reference_type.lower()} "{item_name or approval.reference_id}" has been rejected.'
                )

            # Send notification to requester
            notif = Notification.objects.create(
                user=approval.requested_by,
                notification_type='APPROVAL_REJECTED',
                title=notif_title,
                message=notif_message,
                reference_type=approval.reference_type.lower(),
                reference_id=approval.reference_id
            )
            # Push real-time WebSocket notification to the requester
            try:
                from .signals import send_websocket_notification
                send_websocket_notification(approval.requested_by.id, {
                    'id': notif.id,
                    'title': notif.title,
                    'message': notif.message,
                    'type': notif.notification_type,
                    'reference_type': notif.reference_type,
                    'reference_id': notif.reference_id,
                    'created_at': str(notif.created_at),
                })
            except Exception as ws_err:
                print(f"WebSocket push error (reject): {ws_err}")
            
        except Exception as e:
            print(f"Error handling rejection side effects: {e}")
            
        return Response({'status': 'rejected'})
    
    @action(detail=False, methods=['get'])
    def new_projects(self, request):
        """Get pending approval requests for new projects"""
        approvals = ApprovalRequest.objects.filter(
            reference_type='PROJECT',
            approval_type='CREATION',
            status='PENDING'
        ).select_related('requested_by').order_by('-created_at')
        
        # Only admins can see all pending requests
        if request.user.role != 'ADMIN':
            approvals = approvals.filter(requested_by=request.user)
        
        # Get detailed project information
        items = []
        for approval in approvals:
            try:
                project = Projects.objects.get(id=approval.reference_id)
                items.append({
                    'approval_id': approval.id,
                    'project_id': project.id,
                    'project_name': project.name,
                    'description': project.description,
                    'status': project.status,
                    'start_date': project.start_date,
                    'due_date': project.due_date,
                    'duration': project.duration,
                    'working_hours': project.working_hours,
                    'project_lead': project.project_lead.email if project.project_lead else None,
                    'handled_by': project.handled_by.email,
                    'requested_by': approval.requested_by.email,
                    'requested_at': approval.created_at,
                    'request_data': approval.request_data
                })
            except Projects.DoesNotExist:
                pass
        
        return Response({
            'count': len(items),
            'requests': items
        })
    
    @action(detail=False, methods=['get'])
    def project_closures(self, request):
        """Get pending approval requests for project completions"""
        approvals = ApprovalRequest.objects.filter(
            reference_type='PROJECT',
            approval_type='COMPLETION',
            status='PENDING'
        ).select_related('requested_by').order_by('-created_at')
        
        if request.user.role != 'ADMIN':
            approvals = approvals.filter(requested_by=request.user)
        
        items = []
        for approval in approvals:
            try:
                project = Projects.objects.get(id=approval.reference_id)
                items.append({
                    'approval_id': approval.id,
                    'project_id': project.id,
                    'project_name': project.name,
                    'description': project.description,
                    'current_status': project.status,
                    'start_date': project.start_date,
                    'due_date': project.due_date,
                    'completion_request_date': project.completed_date,
                    'project_lead': project.project_lead.email if project.project_lead else None,
                    'handled_by': project.handled_by.email,
                    'requested_by': approval.requested_by.email,
                    'requested_at': approval.created_at,
                    'request_data': approval.request_data
                })
            except Projects.DoesNotExist:
                pass
        
        return Response({
            'count': len(items),
            'requests': items
        })
    
    @action(detail=False, methods=['get'])
    def new_tasks(self, request):
        """Get pending approval requests for new tasks"""
        approvals = ApprovalRequest.objects.filter(
            reference_type='TASK',
            approval_type='CREATION',
            status='PENDING'
        ).select_related('requested_by').order_by('-created_at')
        
        if request.user.role != 'ADMIN':
            approvals = approvals.filter(requested_by=request.user)
        
        items = []
        for approval in approvals:
            try:
                task = Task.objects.get(id=approval.reference_id)
                items.append({
                    'approval_id': approval.id,
                    'task_id': task.id,
                    'task_title': task.title,
                    'project': task.project.name,
                    'project_id': task.project.id,
                    'priority': task.priority,
                    'status': task.status,
                    'start_date': task.start_date,
                    'due_date': task.due_date,
                    'requested_by': approval.requested_by.email,
                    'requested_at': approval.created_at,
                    'assignees': [
                        {'email': assignee.user.email, 'role': assignee.role}
                        for assignee in task.assignees.all()
                    ],
                    'request_data': approval.request_data
                })
            except Task.DoesNotExist:
                pass
        
        return Response({
            'count': len(items),
            'requests': items
        })
    
    @action(detail=False, methods=['get'])
    def task_completions(self, request):
        """Get pending approval requests for task completions"""
        approvals = ApprovalRequest.objects.filter(
            reference_type='TASK',
            approval_type='COMPLETION',
            status='PENDING'
        ).select_related('requested_by').order_by('-created_at')
        
        if request.user.role != 'ADMIN':
            approvals = approvals.filter(requested_by=request.user)
        
        items = []
        for approval in approvals:
            try:
                task = Task.objects.get(id=approval.reference_id)
                items.append({
                    'approval_id': approval.id,
                    'task_id': task.id,
                    'task_title': task.title,
                    'project': task.project.name,
                    'project_id': task.project.id,
                    'priority': task.priority,
                    'current_status': task.status,
                    'start_date': task.start_date,
                    'due_date': task.due_date,
                    'completion_request_date': task.completed_at,
                    'requested_by': approval.requested_by.email,
                    'requested_at': approval.created_at,
                    'assignees': [
                        {'email': assignee.user.email, 'role': assignee.role}
                        for assignee in task.assignees.all()
                    ],
                    'request_data': approval.request_data
                })
            except Task.DoesNotExist:
                pass
        
        return Response({
            'count': len(items),
            'requests': items
        })
    
    @action(detail=False, methods=['get'])
    def my_pending_requests(self, request):
        """Get all pending requests made by the current user"""
        approvals = ApprovalRequest.objects.filter(
            requested_by=request.user,
            status='PENDING'
        ).order_by('-created_at')
        
        serializer = self.get_serializer(approvals, many=True)
        return Response({
            'count': approvals.count(),
            'requests': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary count of pending approvals by category"""
        # Senior Defense: Self-heal any orphaned states before calculating summary
        self._cleanup_orphaned_approvals()

        base_query = ApprovalRequest.objects.filter(status='PENDING')
        
        # Only admins see all pending; others see only their own
        if request.user.role != 'ADMIN':
            base_query = base_query.filter(requested_by=request.user)
        
        summary = {
            'new_projects': base_query.filter(
                reference_type='PROJECT',
                approval_type='CREATION'
            ).count(),
            'project_closures': base_query.filter(
                reference_type='PROJECT',
                approval_type='COMPLETION'
            ).count(),
            'new_tasks': base_query.filter(
                reference_type='TASK',
                approval_type='CREATION'
            ).count(),
            'task_completions': base_query.filter(
                reference_type='TASK',
                approval_type='COMPLETION'
            ).count(),
            'total_pending': base_query.count()
        }
        
        return Response(summary)

    def _cleanup_orphaned_approvals(self):
        """
        Self-healing mechanism: Find tasks/projects in 'pending_completion' 
        but without a PENDING ApprovalRequest, and reset them.
        """
        try:
            with transaction.atomic():
                # 1. Check Tasks
                orphaned_tasks = Task.objects.filter(
                    approval_status='pending_completion'
                ).exclude(
                    id__in=ApprovalRequest.objects.filter(
                        reference_type='TASK', 
                        approval_type='COMPLETION', 
                        status='PENDING'
                    ).values_list('reference_id', flat=True)
                )
                
                if orphaned_tasks.exists():
                    print(f"Self-healing: Fixed {orphaned_tasks.count()} orphaned task completion states.")
                    orphaned_tasks.update(
                        status='IN_PROGRESS', 
                        approval_status='REJECTED'
                    )

                # 2. Check Projects
                orphaned_projects = Projects.objects.filter(
                    approval_status='pending_completion'
                ).exclude(
                    id__in=ApprovalRequest.objects.filter(
                        reference_type='PROJECT', 
                        approval_type='COMPLETION', 
                        status='PENDING'
                    ).values_list('reference_id', flat=True)
                )
                
                if orphaned_projects.exists():
                    print(f"Self-healing: Fixed {orphaned_projects.count()} orphaned project completion states.")
                    orphaned_projects.update(
                        status='ACTIVE', 
                        approval_status='REJECTED'
                    )
        except Exception as e:
            print(f"Self-healing error: {e}")


class ApprovalResponseViewSet(viewsets.ModelViewSet):
    """ViewSet for admin to approve/reject requests"""
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = ApprovalResponseSerializer
    pagination_class = None
    queryset = ApprovalResponse.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action', 'reviewed_by', 'approval_request']
    search_fields = ['reviewed_by__email', 'approval_request__requested_by__email']
    ordering_fields = ['reviewed_at']
    
    def get_queryset(self):
        """Only admins can view approval responses"""
        user = self.request.user
        if not user.is_authenticated:
            return ApprovalResponse.objects.none()
        if user.role == 'ADMIN':
            return ApprovalResponse.objects.all()
        return ApprovalResponse.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Create approval response (Admin only)"""
        if not request.user.is_authenticated or request.user.role != 'ADMIN':
            return Response(
                {"error": "Only admins can approve/reject requests"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if approval request exists
        approval_request_id = request.data.get('approval_request')
        try:
            approval_request = ApprovalRequest.objects.get(id=approval_request_id)
        except ApprovalRequest.DoesNotExist:
            return Response(
                {"error": "Approval request not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already responded
        if hasattr(approval_request, 'response'):
            return Response(
                {"error": "This approval request has already been reviewed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if pending
        if approval_request.status != 'PENDING':
            return Response(
                {"error": "This approval request is not pending"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.save(reviewed_by=request.user)
        
        # Update related project/task based on approval type and action
        action = response.action
        
        if approval_request.reference_type == 'PROJECT':
            try:
                project = Projects.objects.get(id=approval_request.reference_id)
                
                if approval_request.approval_type == 'CREATION':
                    if action == 'APPROVED':
                        project.is_approved = True
                        project.save()
                    elif action == 'REJECTED':
                        # Delete rejected project creations
                        project.delete()
                        
                elif approval_request.approval_type == 'COMPLETION':
                    if action == 'APPROVED':
                        project.status = 'COMPLETED'
                        project.approval_status = 'APPROVED'
                        project.completed_date = timezone.now().date()
                        project.save()
                    elif action == 'REJECTED':
                        # If rejected, set status to REJECTED so frontend can enable resubmission
                        project.approval_status = 'REJECTED'
                        project.status = 'ACTIVE'
                        project.rejection_reason = response.rejection_reason
                        project.save()
                        
                        # Reset all tasks to IN_PROGRESS so they can be worked on again
                        tasks = project.tasks.all()
                        tasks.update(status='IN_PROGRESS', approval_status='REJECTED', completed_at=None)
                        
                        # Reset all completed subtasks (milestones) across the whole project
                        from .models import SubTask
                        SubTask.objects.filter(task__in=tasks, status='DONE').update(
                            status='PENDING', 
                            completed_at=None
                        )
                    
            except Projects.DoesNotExist:
                pass
        
        elif approval_request.reference_type == 'TASK':
            try:
                task = Task.objects.get(id=approval_request.reference_id)
                
                if approval_request.approval_type == 'CREATION':
                    if action == 'APPROVED':
                        # Task creation approved - ensure status reflects correctly
                        if task.status == 'PENDING_APPROVAL':
                            task.status = 'PENDING'
                            task.approval_status = 'APPROVED'
                            task.save()
                    elif action == 'REJECTED':
                        # Delete rejected task creations
                        task.delete()
                        
                elif approval_request.approval_type == 'COMPLETION':
                    if action == 'APPROVED':
                        with transaction.atomic():
                            task.status = 'DONE'
                            task.approval_status = 'APPROVED'
                            task.completed_at = timezone.now().date()
                            task.save()
                            
                            # Handle recurring task regeneration
                            if task.task_type == 'RECURRING':
                                task.regenerate_recurring_task()
                    elif action == 'REJECTED':
                        with transaction.atomic():
                            # If rejected, task goes back to IN_PROGRESS and we reset all completed subtasks
                            task.status = 'IN_PROGRESS'
                            task.approval_status = 'REJECTED'
                            task.rejection_reason = response.rejection_reason
                            task.completed_at = None
                            task.save()
                            
                            # Reset subtasks so they can be re-completed
                            task.subtasks.filter(status='DONE').update(
                                status='PENDING', 
                                completed_at=None
                            )
                        task.subtasks.filter(status='DONE').update(
                            status='PENDING', 
                            completed_at=None
                        )
                    
            except Task.DoesNotExist:
                pass

        # Send notification to requester
        try:
            notification_title = f"{approval_request.get_approval_type_display()} Request {action.title()}"
            notification_message = f"Your request for {approval_request.get_approval_type_display().lower()} of {approval_request.reference_type.lower()} (ID: {approval_request.reference_id}) has been {action.lower()}."
            
            if response.rejection_reason:
                notification_message += f"\nReason: {response.rejection_reason}"
            
            notif_type = 'APPROVAL_APPROVED' if action == 'APPROVED' else 'APPROVAL_REJECTED'
            
            from .signals import send_websocket_notification
            send_websocket_notification(approval_request.requested_by.id, {
                'id': approval_request.id,
                'title': notification_title,
                'message': notification_message,
                'type': notif_type,
                'reference_type': approval_request.reference_type,
                'reference_id': approval_request.reference_id,
                'created_at': str(timezone.now()),
            })
        except Exception as e:
            print(f"Failed to send websocket sync: {e}")
        
        return Response({
            "message": f"Approval request {action.lower()} successfully",
            "response": ApprovalResponseSerializer(response).data
        }, status=status.HTTP_201_CREATED)
    
class TaskViewSet(TaskQuerySetMixin, viewsets.ModelViewSet):
    """ViewSet for managing tasks"""
    serializer_class = TaskSerializer
    pagination_class = None
    queryset = Task.objects.all() # Base default
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['priority', 'status', 'project', 'due_date', 'start_date']
    search_fields = ['title', 'project__name']
    ordering_fields = ['created_at', 'due_date', 'start_date', 'priority']
    
    
    def _cleanup_stuck_tasks(self, queryset):
        """Detect and fix tasks incorrectly in Approval or Completed buckets (incomplete milestones)"""
        # We search specifically for tasks that are in a 'pending approval' state OR incorrectly 'DONE'
        stuck_tasks = queryset.filter(
            models.Q(approval_status='pending_completion') | 
            models.Q(status='PENDING_APPROVAL') |
            models.Q(status='DONE')
        )
        
        from .models import ApprovalRequest
        for task in stuck_tasks:
            # Check for incomplete milestones
            # If even one milestone is not finished, this task shouldn't be in Approval or Completed
            if task.subtasks.exclude(status='DONE').exists():
                # Force repair: revert to PENDING (Task Bucket)
                task.status = 'PENDING'
                task.approval_status = None
                task.completed_at = None
                task.save()
                
                # Also cancel any associated approval request to clean up the Admin view
                ApprovalRequest.objects.filter(
                    reference_id=task.id,
                    reference_type='TASK',
                    status='PENDING'
                ).update(status='CANCELED')

    def get_queryset(self):
        # Call the Mixin's get_queryset (or the base one)
        return super().get_queryset()

    
    def perform_create(self, serializer):
        """Override create to add approval logic for tasks"""
        user = self.request.user
        user_role = get_user_role(user)  # Safe access to user role
        with transaction.atomic():
            task = serializer.save()
            
            # If ADMIN or no auth (dev mode), auto-approve the task
            if user_role == 'ADMIN':
                # Task is auto-approved, no approval request needed
                pass
            elif user.is_authenticated:
                # For authenticated EMPLOYEE, MANAGER, TEAMLEAD require approval
                task.status = 'PENDING_APPROVAL'
                task.save()
                
                ApprovalRequest.objects.create(
                    reference_type='TASK',
                    reference_id=task.id,
                    approval_type='CREATION',
                    requested_by=user,
                    request_data=serializer.data
                )
    
    @action(detail=True, methods=['post'])
    def request_completion(self, request, pk=None):
        """Request approval for task completion"""
        task = self.get_object()
        user = request.user
        
        # Check if task is already completed
        if task.status == 'DONE':
            return Response(
                {"message": "Task is already completed"},
                status=status.HTTP_200_OK
            )
        
        # Check if all milestones (subtasks) are completed
        pending_subtasks_count = task.subtasks.exclude(status='DONE').count()
        if pending_subtasks_count > 0:
            return Response(
                {"error": f"Cannot complete task. There are {pending_subtasks_count} pending milestones remaining."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if there's already a pending completion request
        existing_request = ApprovalRequest.objects.filter(
            reference_type='TASK',
            reference_id=task.id,
            approval_type='COMPLETION',
            status='PENDING'
        ).first()
        
        if existing_request and user.role != 'ADMIN':
            return Response(
                {"message": "There is already a pending completion request for this task"},
                status=status.HTTP_200_OK
            )
        
        # Set completed date
        completion_date = request.data.get('completed_date', timezone.now().date())
        task.completed_at = completion_date
        task.save()
        
        # If user is ADMIN, approve immediately
        if user.role == 'ADMIN':
            task.status = 'DONE'
            task.approval_status = 'approved'
            task.save()
            
            # Handle recurring task regeneration
            new_task_data = None
            if task.task_type == 'RECURRING':
                new_task = task.regenerate_recurring_task()
                if new_task:
                    new_task_data = TaskSerializer(new_task).data
            
            # If there was a pending request, update it
            if existing_request:
                existing_request.status = 'APPROVED'
                existing_request.approved_by = user
                existing_request.approved_at = timezone.now()
                existing_request.save()

            return Response({
                "message": "Task marked as completed (auto-approved for admin)",
                "task": TaskSerializer(task).data,
                "new_recurring_task": new_task_data
            })
        
        with transaction.atomic():
            # For non-admin: set status to PENDING_APPROVAL
            task.status = 'PENDING_APPROVAL'
            task.approval_status = 'pending_completion'
            task.save()
            
            # Create approval request
            approval_request = ApprovalRequest.objects.create(
                reference_type='TASK',
                reference_id=task.id,
                approval_type='COMPLETION',
                requested_by=user,
                request_data={
                    'task_title': task.title,
                    'project': task.project.name,
                    'completed_date': str(completion_date)
                }
            )
        
        # Send WebSocket notification to all admins
        try:
            from .signals import send_websocket_notification
            admins = User.objects.filter(role='ADMIN')
            for admin in admins:
                notification = Notification.objects.create(
                    user=admin,
                    notification_type='APPROVAL_REQUESTED',
                    title='Task Completion Request',
                    message=f'{user.email} requested to mark task "{task.title}" as completed.',
                    reference_type='task',
                    reference_id=task.id
                )
                send_websocket_notification(admin.id, {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'type': notification.notification_type,
                    'reference_type': notification.reference_type,
                    'reference_id': notification.reference_id,
                    'created_at': str(notification.created_at),
                })
        except Exception as e:
            print(f"WebSocket notification error in request_completion: {e}")
        
        return Response({
            "message": "Task completion request submitted for approval",
            "approval_request_id": approval_request.id
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def approve_completion(self, request, pk=None):
        """Admin action to approve a task completion request"""
        task = self.get_object()
        user = request.user
        
        if user.role != 'ADMIN':
            return Response(
                {"error": "Only admins can approve task completions"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        with transaction.atomic():
            task.status = 'DONE'
            task.approval_status = 'approved'
            task.completed_at = timezone.now().date()
            task.save()
            
            # Handle recurring task regeneration
            new_task_data = None
            if task.task_type == 'RECURRING':
                new_task = task.regenerate_recurring_task()
                if new_task:
                    new_task_data = TaskSerializer(new_task).data
                
            # Update the associated ApprovalRequest
            ApprovalRequest.objects.filter(
                reference_type='TASK',
                reference_id=task.id,
                approval_type='COMPLETION',
                status='PENDING'
            ).update(status='APPROVED', approved_by=user, approved_at=timezone.now())

        return Response({
            "message": "Task completion approved",
            "task": TaskSerializer(task).data,
            "new_recurring_task": new_task_data
        })

    @action(detail=True, methods=['post'])
    def reject_completion(self, request, pk=None):
        """Admin action to reject a task completion request"""
        task = self.get_object()
        user = request.user
        reason = request.data.get('reason', 'No reason provided')
        
        if user.role != 'ADMIN':
            return Response(
                {"error": "Only admins can reject task completions"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        with transaction.atomic():
            task.status = 'PENDING'
            task.approval_status = 'rejected'
            task.rejection_reason = reason
            task.save()
            
            # Update associated ApprovalRequest
            ApprovalRequest.objects.filter(
                reference_type='TASK',
                reference_id=task.id,
                approval_type='COMPLETION',
                status='PENDING'
            ).update(status='REJECTED', reason=reason)

        return Response({"message": "Task completion rejected"})

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """Reopen a completed task, resetting its status and milestones"""
        task = self.get_object()
        reason = request.data.get('reason', 'No reason provided')
        
        with transaction.atomic():
            # Update task status
            task.status = 'PENDING'
            task.approval_status = 'rejected'
            task.rejection_reason = reason
            task.completed_at = None
            task.save()
            
            # Reset all subtasks (milestones)
            task.subtasks.all().update(status='PENDING', completed_at=None)
            
            # --- Project De-completion Logic ---
            # If the parent project was completed or waiting for completion, reset it back to ACTIVE
            project = task.project
            # COMPLETED status means the project card shows "Completed"
            # REJECTED approval_status with ACTIVE status ensures it shows "Request Completion" button
            current_status = project.status.lower()
            current_approval = (project.approval_status or "").lower()
            
            if current_status == 'completed' or current_approval == 'pending_completion':
                project.status = 'active'
                project.approval_status = 'rejected' # Signify it was sent back for work
                project.save()
            
        return Response({
            "message": "Task reopened successfully and project set to active",
            "task": TaskSerializer(task).data,
            "project_status": project.status
        })


class TaskAssigneeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing task assignments"""
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = TaskAssigneeSerializer
    queryset = TaskAssignee.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['task', 'user', 'role']
    search_fields = ['task__title', 'user__email']
    ordering_fields = ['assigned_at']
    
    def get_queryset(self):
        """Filter task assignees based on user permissions"""
        user = self.request.user
        if user.role == 'ADMIN':
            return TaskAssignee.objects.all()
        else:
            # Return assignments for the user
            return TaskAssignee.objects.filter(user=user)


# ===== PLANNER CATALOG ENDPOINTS =====
# Dedicated endpoints for Planner Catalog that always show only assigned items

class CatalogProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Planner Catalog projects - shows only projects assigned to the user.
    This endpoint is separate from ProjectViewSet to prevent Dashboard changes 
    from affecting the Planner Catalog feature.
    """
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = ProjectSerializer
    queryset = Projects.objects.all()
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'handled_by', 'created_by', 'project_lead']
    search_fields = ['name', 'description']
    ordering_fields = ['start_date', 'due_date', 'create_date', 'name']
    ordering = ['-create_date']

    def get_queryset(self):
        """Show all active projects for the catalog - visible to all users"""
        # For ALL users, show all active projects in the catalog
        return Projects.objects.filter(status='ACTIVE').distinct()
    
    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            from .serializers import ProjectDetailSerializer
            return ProjectDetailSerializer
        return ProjectSerializer


class CatalogTaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Planner Catalog tasks - shows only tasks assigned to the user.
    This endpoint is separate from TaskViewSet to prevent Dashboard changes 
    from affecting the Planner Catalog feature.
    """
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = TaskSerializer
    pagination_class = None
    queryset = Task.objects.all()
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['priority', 'status', 'project', 'due_date', 'start_date']
    search_fields = ['title', 'project__name']
    ordering_fields = ['created_at', 'due_date', 'start_date', 'priority']
    
    def get_queryset(self):
        """Show all active tasks for the catalog - visible to all users"""
        # For ALL users, show all tasks that are not 'DONE'
        return Task.objects.exclude(status='DONE').distinct()


class SubTaskViewSet(viewsets.ModelViewSet):
    """ViewSet for managing subtasks"""
    permission_classes = [AllowAny]  # Allow unauthenticated access
    serializer_class = SubTaskSerializer
    pagination_class = None
    queryset = SubTask.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['task', 'status', 'due_date']
    search_fields = ['title', 'task__title']
    ordering_fields = ['created_at', 'due_date']
    
    def get_queryset(self):
        """Filter subtasks based on user permissions"""
        user = self.request.user
        # Allow unauthenticated users to access all subtasks (for AllowAny permission)
        if not user.is_authenticated:
            return SubTask.objects.all()
        if user.role == 'ADMIN':
            return SubTask.objects.all()
        else:
            from django.db import models
            # Return subtasks for tasks assigned to the user or if they are assigned to the parent project
            return SubTask.objects.filter(
                models.Q(task__assignees__user=user) | 
                models.Q(task__project__created_by=user) |
                models.Q(task__project__assignees=user) |
                models.Q(task__project__handled_by=user) |
                models.Q(task__project__project_lead=user)
            ).distinct()
    
    @action(detail=True, methods=['patch'])
    def toggle_completion(self, request, pk=None):
        """Toggle subtask completion status (for checkbox functionality)"""
        subtask = self.get_object()
        task = subtask.task
        
        # Bi-directional toggle: Allow unchecking for rework
        if subtask.status == 'DONE':
            subtask.status = 'PENDING'
            subtask.completed_at = None
            subtask.completed_by = None
            subtask.save()
            
            # Recalculate progress for parent task
            progress = task.calculate_progress()
            
            # If parent task was DONE or PENDING_APPROVAL, revert it to IN_PROGRESS
            # because it no longer qualifies for completion approval
            if task.status in ['DONE', 'PENDING_APPROVAL']:
                task.status = 'IN_PROGRESS'
                task.approval_status = None # Reset approval status when task is reverted for rework
                task.completed_at = None
                task.save()
            
            serializer = SubTaskSerializer(subtask)
            return Response({
                'subtask': serializer.data,
                'parent_task_progress': progress
            })
            
        # Standard marking as DONE
        subtask.status = 'DONE'
        from django.utils import timezone
        subtask.completed_at = timezone.now().date()
        subtask.completed_by = request.user
        subtask.save()
        
        # Calculate progress
        progress = subtask.task.calculate_progress()
        
        # Check for auto-completion triggering
        task = subtask.task
        if progress == 100 and task.status != 'DONE':
            user = request.user
            
            # Use specific timezone for consistency
            from django.utils import timezone
            current_date = timezone.now().date()
            
            # If ADMIN, auto-complete
            if user.role == 'ADMIN':
                task.status = 'DONE'
                task.completed_at = current_date
                task.save()
                
                # Handle recurring task regeneration
                if task.task_type == 'RECURRING':
                    task.regenerate_recurring_task()
                    
            else:
                # Check for existing pending request
                existing_request = ApprovalRequest.objects.filter(
                    reference_type='TASK',
                    reference_id=task.id,
                    approval_type='COMPLETION',
                    status='PENDING'
                ).exists()
                
                if not existing_request:
                    with transaction.atomic():
                        ApprovalRequest.objects.create(
                            reference_type='TASK',
                            reference_id=task.id,
                            approval_type='COMPLETION',
                            requested_by=user,
                            request_data={
                                'task_title': task.title,
                                'project': task.project.name,
                                'completed_date': str(current_date),
                                'auto_triggered': True
                            }
                        )
                        # Update status to indicate pending approval
                        task.status = 'PENDING_APPROVAL'
                        task.approval_status = 'pending_completion'
                        task.save()
                    
                    # Send WebSocket notification to all admins
                    try:
                        from .signals import send_websocket_notification
                        admins = User.objects.filter(role='ADMIN')
                        for admin in admins:
                            notification = Notification.objects.create(
                                user=admin,
                                notification_type='APPROVAL_REQUESTED',
                                title='Task Completion Request',
                                message=f'{user.email} completed all subtasks for task "{task.title}". Pending your approval.',
                                reference_type='task',
                                reference_id=task.id
                            )
                            send_websocket_notification(admin.id, {
                                'id': notification.id,
                                'title': notification.title,
                                'message': notification.message,
                                'type': notification.notification_type,
                                'reference_type': notification.reference_type,
                                'reference_id': notification.reference_id,
                                'created_at': str(notification.created_at),
                            })
                    except Exception as e:
                        print(f"WebSocket notification error in toggle_completion: {e}")

        # Return updated subtask data along with parent task's new progress
        serializer = SubTaskSerializer(subtask)
        return Response({
            'subtask': serializer.data,
            'parent_task_progress': progress
        })


class PendingViewSet(viewsets.ModelViewSet):
    """ViewSet for managing pending tasks"""
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = PendingSerializer
    pagination_class = None
    queryset = Pending.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'status', 'original_plan_date', 'replanned_date']
    search_fields = ['today_plan__catalog_item__name', 'reason']
    ordering_fields = ['created_at', 'original_plan_date', 'replanned_date']
    
    def get_queryset(self):
        """Filter pending tasks based on user permissions"""
        user = self.request.user
        queryset = Pending.objects.all()
        target_user_id = self.request.query_params.get('user_id')
        
        # If target_user_id is provided, check if the current user has permission to view it
        if target_user_id:
            # Admins can see any pending items
            if user.role == 'ADMIN':
                queryset = queryset.filter(user__id=target_user_id)
            # Managers and TeamLeads can see items for users in their department
            elif user.role in ['MANAGER', 'TEAMLEAD']:
                queryset = queryset.filter(user__id=target_user_id)
            # Standard users can only ever see their own, even if they pass a different ID
            else:
                queryset = queryset.filter(user=user)
        else:
            # Default to the current logged-in user's pending tasks
            queryset = queryset.filter(user=user)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def my_pending(self, request):
        """Get current user's (or specified user's) pending tasks, optionally filtered by date"""
        date_param = request.query_params.get('date')
        user_id_param = request.query_params.get('user_id')
        
        target_user = request.user
        if user_id_param:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                requested_user = User.objects.get(id=user_id_param)
                # Check permissions
                if request.user.role == 'ADMIN' or (request.user.role in ['MANAGER', 'TEAMLEAD'] and getattr(requested_user, 'department', None) == getattr(request.user, 'department', None)):
                    target_user = requested_user
            except User.DoesNotExist:
                pass
        
        # Auto-move past incomplete plans to pending
        import pytz
        from datetime import datetime
        kolkata_tz = pytz.timezone('Asia/Kolkata')
        today = datetime.now(kolkata_tz).date()
        
        # Find all past TodayPlans that aren't COMPLETED, MOVED_TO_PENDING, or CANCELLED
        past_plans = TodayPlan.objects.filter(
            user=target_user,
            plan_date__lt=today
        ).exclude(status__in=['COMPLETED', 'MOVED_TO_PENDING', 'CANCELLED'])
        
        for plan in past_plans:
            # Check if pending already exists to avoid duplicates
            if not Pending.objects.filter(today_plan=plan).exists():
                Pending.objects.create(
                    user=target_user,
                    today_plan=plan,
                    original_plan_date=plan.plan_date,
                    minutes_left=plan.planned_duration_minutes,
                    reason="Not completed on planned date",
                    status='PENDING'
                )
            
            # Update plan status
            plan.status = 'MOVED_TO_PENDING'
            plan.save()
        
        pending = self.get_queryset().filter(user=target_user, status='PENDING')
        
        # Filter by original_plan_date if date parameter is provided
        if date_param:
            pending = pending.filter(original_plan_date=date_param)
        
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)
    
    
    @action(detail=True, methods=['post'])
    def replan(self, request, pk=None):
        """Replan a pending task to a new date"""
        pending_task = self.get_object()
        new_date = request.data.get('replanned_date')
        
        if not new_date: 
            return Response(
                {"error": "replanned_date is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        pending_task.replanned_date = new_date
        pending_task.status = 'REPLANNED'
        pending_task.save()
        
        return Response({
            "message": "Task replanned successfully",
            "pending": PendingSerializer(pending_task).data
        })


class CatalogViewSet(viewsets.ModelViewSet):
    """ViewSet for managing catalog items"""
    permission_classes = [AllowAny]  # Temporarily allow unauthenticated access for testing
    serializer_class = CatalogSerializer
    pagination_class = None
    queryset = Catalog.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['catalog_type', 'user', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    
    def get_queryset(self):
        """Show all active catalog items - visible to all users"""
        # All users see all active catalog items
        return Catalog.objects.filter(is_active=True).distinct()
    
    def perform_create(self, serializer):
        """Set the user field to current user when creating"""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_catalog(self, request):
        """Get current user's catalog items"""
        catalog = Catalog.objects.filter(user=request.user, is_active=True)
        serializer = self.get_serializer(catalog, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get catalog items by type"""
        catalog_type = request.query_params.get('type')
        if not catalog_type:
            return Response(
                {"error": "type parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        catalog = self.get_queryset().filter(catalog_type=catalog_type.upper())
        serializer = self.get_serializer(catalog, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update progress percentage for a catalog item"""
        catalog = self.get_object()
        
        # If linked to task/project, calculate automatically
        if catalog.task or catalog.project:
            progress = catalog.calculate_progress()
            return Response({
                "message": "Progress calculated automatically",
                "progress_percentage": progress
            })
        
        # For manual items (courses, routines, custom), allow manual update
        progress = request.data.get('progress_percentage')
        if progress is None:
            return Response(
                {"error": "progress_percentage is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            progress = int(progress)
            if not 0 <= progress <= 100:
                raise ValueError()
        except (ValueError, TypeError):
            return Response(
                {"error": "progress_percentage must be an integer between 0 and 100"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        catalog.progress_percentage = progress
        catalog.save()
        
        return Response({
            "message": "Progress updated successfully",
            "progress_percentage": catalog.progress_percentage
        })
    
    @action(detail=False, methods=['post'])
    def refresh_all_progress(self, request):
        """Refresh progress for all catalog items linked to tasks/projects"""
        catalogs = Catalog.objects.filter(user=request.user).filter(
            models.Q(task__isnull=False) | models.Q(project__isnull=False)
        )
        
        updated_count = 0
        for catalog in catalogs:
            catalog.calculate_progress()
            updated_count += 1
        
        return Response({
            "message": f"Progress refreshed for {updated_count} catalog items",
            "count": updated_count
        })


# ===== WORKFLOW VIEWSETS =====

class TodayPlanViewSet(viewsets.ModelViewSet):
    """ViewSet for managing today's plan - drag & drop items from catalog"""
    permission_classes = [AllowAny]  # Temporarily allow unauthenticated access for testing
    serializer_class = TodayPlanSerializer
    pagination_class = None
    queryset = TodayPlan.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['plan_date', 'status', 'catalog_item__catalog_type']
    search_fields = ['catalog_item__name', 'notes']
    ordering_fields = ['plan_date', 'order_index', 'scheduled_start_time']
    
    def get_queryset(self):
        """Filter today's plan based on user permissions.
        Admin can pass ?user_id=<id> to view any employee's plan.
        """
        user = self.request.user
        queryset = TodayPlan.objects.all()

        if user.is_authenticated:
            target_user_id = self.request.query_params.get('user_id')
            if target_user_id:
                if user.role == 'ADMIN':
                    queryset = queryset.filter(user__id=target_user_id)
                elif user.role in ['MANAGER', 'TEAMLEAD']:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    try:
                        requested_user = User.objects.get(id=target_user_id)
                        if getattr(requested_user, 'department', None) == getattr(user, 'department', None):
                            queryset = queryset.filter(user__id=target_user_id)
                        else:
                            queryset = queryset.filter(user=user)
                    except User.DoesNotExist:
                        queryset = queryset.filter(user=user)
                else:
                    queryset = queryset.filter(user=user)
            else:
                queryset = queryset.filter(user=user)
        
        # Date filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        date = self.request.query_params.get('date') # Specific day
        
        if start_date and end_date:
            queryset = queryset.filter(plan_date__range=[start_date, end_date])
        elif date:
            queryset = queryset.filter(plan_date=date)
            
        # exclude unplanned items from the main list (they show up in Activity Log only)
        # BUT: Allow them to be retrieved by PK (e.g., when moving to activity log)
        if self.action != 'retrieve' and 'pk' not in self.kwargs:
            queryset = queryset.filter(is_unplanned=False)
            
        return queryset

    
    def perform_create(self, serializer):
        """Set the user field and auto-fill missing fields when creating"""
        user = self.request.user if self.request.user.is_authenticated else User.objects.first()
        
        # Get plan_date from request
        plan_date = self.request.data.get('plan_date', timezone.now().date())
        if isinstance(plan_date, str):
            from datetime import datetime
            plan_date = datetime.strptime(plan_date, '%Y-%m-%d').date()
        
        # Calculate order_index
        last_plan = TodayPlan.objects.filter(user=user, plan_date=plan_date).order_by('-order_index').first()
        order_index = (last_plan.order_index + 1) if last_plan else 0
        
        # Get scheduled times from request (if explicitly provided)
        scheduled_start_time = self.request.data.get('scheduled_start_time')
        scheduled_end_time = self.request.data.get('scheduled_end_time')
        
        # Never auto-generate times - times remain null until set in activity log
        # Build the save kwargs
        save_kwargs = {
            'user': user,
            'order_index': order_index,
        }
        
        # Only include times if they are explicitly provided
        if scheduled_start_time:
            save_kwargs['scheduled_start_time'] = scheduled_start_time
        if scheduled_end_time:
            save_kwargs['scheduled_end_time'] = scheduled_end_time
        
        serializer.save(**save_kwargs)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's plan for current user"""
        today = timezone.now().date()
        
        # Handle anonymous users
        if request.user.is_authenticated:
            user = request.user
        else:
            # For testing: get first user if not authenticated
            user = User.objects.first()
        
        if not user:
            return Response([], status=status.HTTP_200_OK)
        
        plans = TodayPlan.objects.filter(user=user, plan_date=today).order_by('order_index')
        serializer = self.get_serializer(plans, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add_custom(self, request):
        """Add a custom task to today's plan (not from catalog)"""
        title = request.data.get('title')
        plan_date = request.data.get('plan_date', timezone.now().date())
        
        # Convert plan_date string to date object if needed
        if isinstance(plan_date, str):
            from datetime import datetime as dt
            plan_date = dt.strptime(plan_date, '%Y-%m-%d').date()
            
        scheduled_start_time = request.data.get('scheduled_start_time')
        scheduled_end_time = request.data.get('scheduled_start_time') # Type in original request? usually start/end
        # The frontend sends 'scheduled_start_time' but maybe not end time?
        # Let's check the request data from the frontend service:
        # 'scheduled_start_time': scheduledStartTime
        
        scheduled_end_time = request.data.get('scheduled_end_time')

        planned_duration_minutes = request.data.get('planned_duration_minutes')
        quadrant = request.data.get('quadrant', 'inbox')
        notes = request.data.get('description', '') # Map description to notes or custom_description
        
        if not title:
            return Response(
                {"error": "Title is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get user (handle anonymous)
        if request.user.is_authenticated:
            user = request.user
            target_user_id = request.data.get('user_id')
            if target_user_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    requested_user = User.objects.get(id=target_user_id)
                    if user.role == 'ADMIN' or getattr(requested_user, 'department', None) == getattr(user, 'department', None):
                        user = requested_user
                except User.DoesNotExist:
                    pass
        else:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.first()
             
        if not user:
            return Response({"error": "No user available"}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate order_index
        last_plan = TodayPlan.objects.filter(user=user, plan_date=plan_date).order_by('-order_index').first()
        order_index = (last_plan.order_index + 1) if last_plan else 0
        
        # Calculate duration/times if needed (similar logic to add_from_catalog)
        if not planned_duration_minutes:
            planned_duration_minutes = 30 # Default for custom tasks?
            
        # Generate default scheduled times if not provided
        if not scheduled_start_time:
             # Find the last planned item's end time, or use current time
            now = timezone.now()
            if last_plan and last_plan.scheduled_end_time:
                # Start after the last planned item
                start_dt = datetime.combine(now.date(), last_plan.scheduled_end_time)
            else:
                # Start at the next hour boundary
                start_dt = now.replace(minute=0, second=0, microsecond=0)
                if now.minute > 0:
                    start_dt = start_dt + timedelta(hours=1)
            
            scheduled_start_time = start_dt.time()
            
        # Calculate end time based on duration
        if not scheduled_end_time and scheduled_start_time:
             # Check if scheduled_start_time is string or time object
             if isinstance(scheduled_start_time, str):
                 # Try parsing with seconds first, then without
                 try:
                     start = datetime.strptime(scheduled_start_time, '%H:%M:%S').time()
                 except ValueError:
                     # If no seconds, parse as HH:MM and add :00
                     start = datetime.strptime(scheduled_start_time, '%H:%M').time()
             else:
                 start = scheduled_start_time
                 
             start_dt = datetime.combine(timezone.now().date(), start)
             end_dt = start_dt + timedelta(minutes=int(planned_duration_minutes))
             scheduled_end_time = end_dt.time()

        today_plan = TodayPlan.objects.create(
            user=user,
            custom_title=title, # Use custom_title for non-catalog items
            custom_description=notes,
            plan_date=plan_date,
            scheduled_start_time=scheduled_start_time,
            scheduled_end_time=scheduled_end_time,
            planned_duration_minutes=planned_duration_minutes,
            quadrant=quadrant if quadrant != 'inbox' else 'Q2', # Default inbox to Q2 if not specified
            order_index=order_index,
            notes=notes,
            is_unplanned=request.data.get('is_unplanned', False)
        )
        
        return Response({
            "message": "Custom task added successfully",
            "plan": TodayPlanSerializer(today_plan).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def add_from_catalog(self, request):
        """Drag and drop item from catalog to today's plan"""
        catalog_id = request.data.get('catalog_id')
        plan_date = request.data.get('plan_date', timezone.now().date())
        
        # Convert plan_date string to date object if needed
        if isinstance(plan_date, str):
            from datetime import datetime as dt
            plan_date = dt.strptime(plan_date, '%Y-%m-%d').date()
        
        scheduled_start_time = request.data.get('scheduled_start_time')
        scheduled_end_time = request.data.get('scheduled_end_time')
        planned_duration_minutes = request.data.get('planned_duration_minutes')
        quadrant = request.data.get('quadrant', 'Q2')
        
        if not catalog_id:
            return Response(
                {"error": "catalog_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            catalog_item = Catalog.objects.get(id=catalog_id)
        except Catalog.DoesNotExist:
            return Response({"error": "Catalog item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Get user (handle anonymous)
        if request.user.is_authenticated:
            user = request.user
            target_user_id = request.data.get('user_id')
            if target_user_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    requested_user = User.objects.get(id=target_user_id)
                    if user.role == 'ADMIN' or getattr(requested_user, 'department', None) == getattr(user, 'department', None):
                        user = requested_user
                except User.DoesNotExist:
                    pass
        else:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            # For testing: fallback to catalog item's user or first user
            user = catalog_item.user if hasattr(catalog_item, 'user') and catalog_item.user else User.objects.first()
        
        if not user:
            return Response({"error": "No user available"}, status=status.HTTP_400_BAD_REQUEST)
            
        # Calculate order_index
        last_plan = TodayPlan.objects.filter(user=user, plan_date=plan_date).order_by('-order_index').first()
        order_index = (last_plan.order_index + 1) if last_plan else 0
        
        # Calculate duration if not provided
        if not planned_duration_minutes:
            if scheduled_start_time and scheduled_end_time:
                start = datetime.strptime(scheduled_start_time, '%H:%M:%S').time()
                end = datetime.strptime(scheduled_end_time, '%H:%M:%S').time()
                start_dt = datetime.combine(timezone.now().date(), start)
                end_dt = datetime.combine(timezone.now().date(), end)
                planned_duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
            else:
                # Use estimated hours from catalog
                planned_duration_minutes = int(float(catalog_item.estimated_hours) * 60)
        
        # Generate default scheduled times if not provided
        if not scheduled_start_time or not scheduled_end_time:
            # Find the last planned item's end time, or use current time
            now = timezone.now()
            if last_plan and last_plan.scheduled_end_time:
                # Start after the last planned item
                start_dt = datetime.combine(now.date(), last_plan.scheduled_end_time)
            else:
                # Start at the next hour boundary
                start_dt = now.replace(minute=0, second=0, microsecond=0)
                if now.minute > 0:
                    start_dt = start_dt + timedelta(hours=1)
            
            # Calculate end time based on duration
            end_dt = start_dt + timedelta(minutes=planned_duration_minutes)
            
            scheduled_start_time = start_dt.time()
            scheduled_end_time = end_dt.time()
        
        today_plan = TodayPlan.objects.create(
            user=user,
            catalog_item=catalog_item,
            plan_date=plan_date,
            scheduled_start_time=scheduled_start_time,
            scheduled_end_time=scheduled_end_time,
            planned_duration_minutes=planned_duration_minutes,
            quadrant=quadrant,
            order_index=order_index,
            notes=request.data.get('notes', ''),
            is_unplanned=request.data.get('is_unplanned', False)
        )
        
        return Response({
            "message": "Item added to today's plan successfully",
            "plan": TodayPlanSerializer(today_plan).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def move_to_activity_log(self, request, pk=None):
        """Move plan item to activity log (click arrow button)"""
        from datetime import datetime
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo
        
        today_plan = self.get_object()
        
        # Get user (the ActivityLog must belong to the same user as the TodayPlan)
        user = today_plan.user
        
        # Check if there's already an active activity log
        active_log = ActivityLog.objects.filter(
            user=user, 
            status='IN_PROGRESS'
        ).first()
        
        if active_log:
            return Response(
                {"error": "You already have an active task in progress. Please stop it first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get current time in Asia/Kolkata timezone
        try:
            kolkata_tz = ZoneInfo('Asia/Kolkata')
        except Exception:
            kolkata_tz = timezone.get_current_timezone()
        
        current_local_time = timezone.now().astimezone(kolkata_tz)
        
        # Create activity log with explicit local start time
        activity_log = ActivityLog.objects.create(
            today_plan=today_plan,
            user=user,
            actual_start_time=current_local_time
        )
        
        # Update today plan status
        today_plan.status = 'IN_ACTIVITY'
        today_plan.save()
        
        return Response({
            "message": "Activity started successfully",
            "activity_log": ActivityLogSerializer(activity_log).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def by_quadrant(self, request):
        """Get today's plan grouped by Eisenhower Matrix quadrant"""
        today = timezone.now().date()
        plan_date = request.query_params.get('date', today)
        
        plans = TodayPlan.objects.filter(
            user=request.user, 
            plan_date=plan_date
        ).select_related('catalog_item').order_by('quadrant', 'order_index')
        
        # Group by quadrant
        quadrants = {
            'Q1': [],
            'Q2': [],
            'Q3': [],
            'Q4': []
        }
        
        total_minutes = 0
        
        for plan in plans:
            serialized = TodayPlanSerializer(plan).data
            quadrants[plan.quadrant].append(serialized)
            total_minutes += plan.planned_duration_minutes
        
        total_hours = total_minutes // 60
        remaining_minutes = total_minutes % 60
        
        return Response({
            'date': plan_date,
            'total_duration': f"{total_hours}h {remaining_minutes}m",
            'total_minutes': total_minutes,
            'quadrants': {
                'Q1': {
                    'label': 'DO FIRST (URGENT & IMPORTANT)',
                    'items': quadrants['Q1']
                },
                'Q2': {
                    'label': 'SCHEDULE (IMPORTANT, NOT URGENT)',
                    'items': quadrants['Q2']
                },
                'Q3': {
                    'label': 'DELEGATE (URGENT, NOT IMPORTANT)',
                    'items': quadrants['Q3']
                },
                'Q4': {
                    'label': 'ELIMINATE (NOT URGENT, NOT IMPORTANT)',
                    'items': quadrants['Q4']
                }
            }
        })
    
    @action(detail=False, methods=['get'])
    def week_view(self, request):
        """Get week view of plans"""
        from datetime import timedelta
        
        # Handle anonymous users
        if request.user.is_authenticated:
            user = request.user
        else:
            user = User.objects.first()
        
        if not user:
            return Response({'week_start': None, 'week_end': None, 'days': []}, status=status.HTTP_200_OK)
        
        # Accept custom start_date or default to current week
        start_date_str = request.query_params.get('start_date')
        if start_date_str:
            start_of_week = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            today = timezone.now().date()
            start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        plans = TodayPlan.objects.filter(
            user=user,
            plan_date__gte=start_of_week,
            plan_date__lte=end_of_week
        ).select_related('catalog_item').order_by('plan_date', 'order_index')
        
        # Group by date
        week_data = {}
        for i in range(7):
            date = start_of_week + timedelta(days=i)
            week_data[str(date)] = {
                'date': date,
                'day_name': date.strftime('%A'),
                'items': [],
                'total_minutes': 0
            }
        
        for plan in plans:
            date_key = str(plan.plan_date)
            if date_key in week_data:
                week_data[date_key]['items'].append(TodayPlanSerializer(plan).data)
                week_data[date_key]['total_minutes'] += plan.planned_duration_minutes
        
        # Convert to list and add formatted time
        week_list = []
        for date_str, data in week_data.items():
            hours = data['total_minutes'] // 60
            minutes = data['total_minutes'] % 60
            data['total_duration'] = f"{hours}h {minutes}m"
            week_list.append(data)
        
        return Response({
            'week_start': start_of_week,
            'week_end': end_of_week,
            'days': week_list
        })
    
    @action(detail=False, methods=['get'])
    def month_view(self, request):
        """Get month view of plans"""
        from datetime import timedelta
        from calendar import monthrange
        
        # Handle anonymous users
        if request.user.is_authenticated:
            user = request.user
        else:
            user = User.objects.first()
        
        if not user:
            return Response({'year': 0, 'month': 0, 'month_name': '', 'days': []}, status=status.HTTP_200_OK)
        
        today = timezone.now().date()
        year = int(request.query_params.get('year', today.year))
        month = int(request.query_params.get('month', today.month))
        
        # Get first and last day of month
        first_day = datetime(year, month, 1).date()
        last_day_num = monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num).date()
        
        plans = TodayPlan.objects.filter(
            user=user,
            plan_date__gte=first_day,
            plan_date__lte=last_day
        ).select_related('catalog_item').order_by('plan_date', 'order_index')
        
        # Group by date
        month_data = {}
        for day_num in range(1, last_day_num + 1):
            date = datetime(year, month, day_num).date()
            month_data[str(date)] = {
                'date': date,
                'day': day_num,
                'items': [],
                'total_minutes': 0
            }
        
        for plan in plans:
            date_key = str(plan.plan_date)
            if date_key in month_data:
                month_data[date_key]['items'].append(TodayPlanSerializer(plan).data)
                month_data[date_key]['total_minutes'] += plan.planned_duration_minutes
        
        # Convert to list
        month_list = []
        for date_str, data in month_data.items():
            hours = data['total_minutes'] // 60
            minutes = data['total_minutes'] % 60
            data['total_duration'] = f"{hours}h {minutes}m"
            month_list.append(data)
        
        return Response({
            'year': year,
            'month': month,
            'month_name': first_day.strftime('%B'),
            'days': month_list
        })
    
    @action(detail=False, methods=['post'])
    def update_quadrant(self, request):
        """Update quadrant for a plan item (drag and drop between quadrants)"""
        plan_id = request.data.get('plan_id')
        new_quadrant = request.data.get('quadrant')
        
        if not plan_id or not new_quadrant:
            return Response(
                {"error": "plan_id and quadrant are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_quadrant not in ['Q1', 'Q2', 'Q3', 'Q4']:
            return Response(
                {"error": "Invalid quadrant. Must be Q1, Q2, Q3, or Q4"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            plan = TodayPlan.objects.get(id=plan_id, user=request.user)
            plan.quadrant = new_quadrant
            plan.save()
            
            return Response({
                "message": "Quadrant updated successfully",
                "plan": TodayPlanSerializer(plan).data
            })
        except TodayPlan.DoesNotExist:
            return Response(
                {"error": "Plan not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Reorder today's plan items"""
        items = request.data.get('items', [])  # List of {id, order_index}
        
        for item in items:
            try:
                plan = TodayPlan.objects.get(id=item['id'], user=request.user)
                plan.order_index = item['order_index']
                plan.save()
            except TodayPlan.DoesNotExist:
                pass
        
        return Response({"message": "Plan reordered successfully"})


class ActivityLogViewSet(viewsets.ModelViewSet):
    """ViewSet for managing activity logs - actual work tracking"""
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = ActivityLogSerializer
    pagination_class = None
    queryset = ActivityLog.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'is_task_completed']
    search_fields = ['work_notes', 'today_plan__catalog_item__name']
    ordering_fields = ['created_at', 'actual_start_time', 'hours_worked']
    
    def get_queryset(self):
        """Filter activity logs based on user permissions"""
        user = self.request.user
        queryset = ActivityLog.objects.all()
        target_user_id = self.request.query_params.get('user_id')
        
        # Handle anonymous users (id = -1 in dev mode)
        if not user.is_authenticated or user.id == -1:
            # In dev mode with ADMIN role, return all activity logs
            if getattr(user, 'role', None) == 'ADMIN':
                return queryset
            else:
                return queryset.none()
        
        if target_user_id:
            if user.role == 'ADMIN':
                queryset = queryset.filter(user__id=target_user_id)
            elif user.role in ['MANAGER', 'TEAMLEAD']:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    requested_user = User.objects.get(id=target_user_id)
                    if getattr(requested_user, 'department', None) == getattr(user, 'department', None):
                        queryset = queryset.filter(user__id=target_user_id)
                    else:
                        queryset = queryset.filter(user=user)
                except User.DoesNotExist:
                    queryset = queryset.filter(user=user)
            else:
                queryset = queryset.filter(user=user)
        else:
            queryset = queryset.filter(user=user)
            
        # Date filtering - always include IN_PROGRESS tasks so they can be stopped
        date_param = self.request.query_params.get('date')
        if date_param:
            queryset = queryset.filter(
                models.Q(today_plan__plan_date=date_param) | models.Q(status='IN_PROGRESS')
            )
            
        return queryset
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get currently active activity log"""
        active_log = ActivityLog.objects.filter(user=request.user, status='IN_PROGRESS').first()
        if not active_log:
            return Response({"message": "No active task"}, status=status.HTTP_200_OK)
        
        serializer = self.get_serializer(active_log)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Stop the activity log (click stop button)"""
        from datetime import datetime
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo
        
        activity_log = self.get_object()
        
        if activity_log.status != 'IN_PROGRESS':
            return Response(
                {"error": "This activity is not in progress"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        is_completed = request.data.get('is_completed', False)
        work_notes = request.data.get('work_notes', '')
        minutes_left = request.data.get('minutes_left', 0)
        extra_minutes = request.data.get('extra_minutes') or 0
        
        # Get custom start and end times if provided
        start_time_str = request.data.get('start_time', '').strip()
        end_time_str = request.data.get('end_time', '').strip()
        
        # Define timezone
        try:
            kolkata_tz = ZoneInfo('Asia/Kolkata')
        except Exception:
            # Fallback if ZoneInfo fails (e.g. windows without tzdata), use UTC or server time
            kolkata_tz = timezone.get_current_timezone()

        current_kolkata_time = timezone.now().astimezone(kolkata_tz)
        today_kolkata = current_kolkata_time.date()
        
        # Update start time if provided
        if start_time_str:
            try:
                # Try parsing with AM/PM format first, then 24-hour format
                start_time_obj = None
                for fmt in ['%I:%M %p', '%H:%M']:
                    try:
                        start_time_obj = datetime.strptime(start_time_str, fmt).time()
                        break
                    except ValueError:
                        continue
                
                if start_time_obj:
                    # Use existing start date in local timezone if available, otherwise use today
                    # This ensures we use the logical day the user intended
                    if activity_log.actual_start_time:
                        base_date = activity_log.actual_start_time.astimezone(kolkata_tz).date()
                    else:
                        base_date = today_kolkata
                    
                    # Create timezone-aware datetime
                    res_start_dt = datetime.combine(base_date, start_time_obj).replace(tzinfo=kolkata_tz)
                    activity_log.actual_start_time = res_start_dt
            except (ValueError, TypeError) as e:
                print(f"Error parsing start time: {e}")
        
        # Update end time if provided, otherwise use current Kolkata time
        if end_time_str:
            try:
                # Try parsing with AM/PM format first, then 24-hour format
                end_time_obj = None
                for fmt in ['%I:%M %p', '%H:%M']:
                    try:
                        end_time_obj = datetime.strptime(end_time_str, fmt).time()
                        break
                    except ValueError:
                        continue
                
                if end_time_obj:
                    # Use the same base date as start time
                    start_local = activity_log.actual_start_time.astimezone(kolkata_tz)
                    log_date = start_local.date()
                    
                    res_end_dt = datetime.combine(log_date, end_time_obj).replace(tzinfo=kolkata_tz)
                    
                    # If end time is earlier than start time, it means it spanned across midnight
                    if res_end_dt < activity_log.actual_start_time:
                        from datetime import timedelta
                        res_end_dt += timedelta(days=1)
                        
                    activity_log.actual_end_time = res_end_dt
                else:
                    activity_log.actual_end_time = current_kolkata_time
            except (ValueError, TypeError) as e:
                print(f"Error parsing end time: {e}")
                activity_log.actual_end_time = current_kolkata_time
        else:
            activity_log.actual_end_time = current_kolkata_time
        
        # Update activity log
        activity_log.work_notes = work_notes
        activity_log.is_task_completed = is_completed
        activity_log.status = 'COMPLETED' if is_completed else 'PENDING'
        activity_log.extra_minutes = extra_minutes
        activity_log.calculate_time_worked()
        activity_log.save()
        
        # Update today's plan
        today_plan = activity_log.today_plan
        
        if is_completed:
            today_plan.status = 'COMPLETED'
            today_plan.save()
            
            return Response({
                "message": "Task completed successfully!",
                "activity_log": ActivityLogSerializer(activity_log).data
            })
        else:
            # Move to pending
            reason = request.data.get('reason', 'Task not completed in time')
            
            pending_task = Pending.objects.create(
                user=request.user,
                today_plan=today_plan,
                activity_log=activity_log,
                original_plan_date=today_plan.plan_date,
                minutes_left=minutes_left,
                extra_minutes=extra_minutes,
                reason=reason
            )
            
            today_plan.status = 'MOVED_TO_PENDING'
            today_plan.save()
            
            return Response({
                "message": "Task moved to pending. Please replan or complete it later.",
                "activity_log": ActivityLogSerializer(activity_log).data,
                "pending": PendingSerializer(pending_task).data
            })
    
    @action(detail=False, methods=['get'])
    def my_logs(self, request):
        """Get current user's activity logs"""
        # Optional date filtering
        date = request.query_params.get('date')
        
        if date:
            # If date specified, get logs for that today_plan__plan_date
            # We use today_plan__plan_date to avoid issues with tasks starting after midnight
            logs = ActivityLog.objects.filter(
                models.Q(user=request.user, today_plan__plan_date=date) |
                models.Q(user=request.user, status='IN_PROGRESS')
            ).distinct().order_by('-actual_start_time')
        else:
            # No date filter - get all logs
            logs = ActivityLog.objects.filter(user=request.user).order_by('-created_at')
        
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get activity statistics"""
        from django.db.models import Sum, Avg, Count
        
        logs = self.get_queryset().filter(user=request.user)
        
        # Optional date range filtering
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date and end_date:
            logs = logs.filter(
                actual_start_time__date__gte=start_date,
                actual_start_time__date__lte=end_date
            )
        
        stats = logs.aggregate(
            total_tasks=Count('id'),
            total_hours=Sum('hours_worked'),
            total_minutes=Sum('minutes_worked'),
            avg_hours_per_task=Avg('hours_worked'),
            completed_tasks=Count('id', filter=models.Q(is_task_completed=True)),
            incomplete_tasks=Count('id', filter=models.Q(is_task_completed=False))
        )
        
        return Response(stats)


class DaySessionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing day sessions - Start/End Day"""
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = DaySessionSerializer
    pagination_class = None
    queryset = DaySession.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['session_date', 'is_active']
    ordering_fields = ['session_date', 'started_at']
    
    def get_queryset(self):
        """Filter day sessions based on user"""
        user = self.request.user
        queryset = DaySession.objects.all()
        target_user_id = self.request.query_params.get('user_id')
        
        if target_user_id:
            if user.role == 'ADMIN':
                queryset = queryset.filter(user__id=target_user_id)
            elif user.role in ['MANAGER', 'TEAMLEAD']:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    requested_user = User.objects.get(id=target_user_id)
                    if getattr(requested_user, 'department', None) == getattr(user, 'department', None):
                        queryset = queryset.filter(user__id=target_user_id)
                    else:
                        queryset = queryset.filter(user=user)
                except User.DoesNotExist:
                    queryset = queryset.filter(user=user)
            else:
                queryset = queryset.filter(user=user)
        else:
            queryset = queryset.filter(user=user)
            
        return queryset
    
    @action(detail=False, methods=['post'])
    def start_day(self, request):
        """Start the work day"""
        today = timezone.now().date()
        
        # Check if day is already started
        existing_session = DaySession.objects.filter(
            user=request.user,
            session_date=today,
            is_active=True
        ).first()
        
        if existing_session:
            return Response(
                {"error": "Day already started", "session": DaySessionSerializer(existing_session).data},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if there are planned items for today
        plans_count = TodayPlan.objects.filter(user=request.user, plan_date=today).count()
        
        if plans_count == 0:
            return Response(
                {"error": "No items in today's plan. Please add items before starting the day."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create or update session
        session, created = DaySession.objects.get_or_create(
            user=request.user,
            session_date=today,
            defaults={'started_at': timezone.now(), 'is_active': True}
        )
        
        if not created:
            session.started_at = timezone.now()
            session.is_active = True
            session.save()
        
        return Response({
            "message": "Day started successfully! Let's make it productive!",
            "session": DaySessionSerializer(session).data,
            "plans_count": plans_count
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def end_day(self, request):
        """End the work day"""
        today = timezone.now().date()
        
        session = DaySession.objects.filter(
            user=request.user,
            session_date=today,
            is_active=True
        ).first()
        
        if not session:
            return Response(
                {"error": "No active day session found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check for active activity logs
        active_logs = ActivityLog.objects.filter(user=request.user, status='IN_PROGRESS').count()
        
        if active_logs > 0:
            return Response(
                {"error": "Please stop all active tasks before ending the day"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.ended_at = timezone.now()
        session.is_active = False
        session.save()
        
        # Get summary
        completed_count = TodayPlan.objects.filter(
            user=request.user, 
            plan_date=today, 
            status='COMPLETED'
        ).count()
        
        pending_count = TodayPlan.objects.filter(
            user=request.user, 
            plan_date=today, 
            status='MOVED_TO_PENDING'
        ).count()
        
        total_hours = ActivityLog.objects.filter(
            user=request.user,
            actual_start_time__date=today
        ).aggregate(total=Sum('hours_worked'))['total'] or 0
        
        return Response({
            "message": "Day ended successfully! Great work!",
            "session": DaySessionSerializer(session).data,
            "summary": {
                "completed_tasks": completed_count,
                "pending_tasks": pending_count,
                "total_hours_worked": total_hours
            }
        })
    
    @action(detail=False, methods=['get'])
    def current_session(self, request):
        """Get current active session"""
        today = timezone.now().date()
        session = DaySession.objects.filter(
            user=request.user,
            session_date=today
        ).first()
        
        if not session:
            return Response({"message": "No session for today"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(session)
        return Response(serializer.data)

class TeamInstructionViewSet(viewsets.ModelViewSet):
    """ViewSet for sending team instructions"""
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = TeamInstructionSerializer
    pagination_class = None
    queryset = TeamInstruction.objects.all()
    
    def get_queryset(self):
        """Filter instructions based on user permissions"""
        user = self.request.user
        if user.role == 'ADMIN':
            return TeamInstruction.objects.all()
        else:
            # Users can see instructions they sent or received
            return TeamInstruction.objects.filter(
                models.Q(sent_by=user) | models.Q(recipients=user)
            ).distinct()
    
    def perform_create(self, serializer):
        """Set sent_by to current user"""
        serializer.save(sent_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def project_members(self, request):
        """Get list of all active team members for project assignment"""
        project_id = request.query_params.get('project_id')
        print(f"=== project_members called with project_id: {project_id} ===")
        
        if not project_id:
            # If no project_id, return all active users (for new project creation)
            all_users = User.objects.filter(is_active=True).distinct()
            print(f"No project_id, returning {all_users.count()} active users")
            
            members_data = [
                {
                    "id": user.id,
                    "email": user.email,
                    "name": user.employee_name if user.employee_name else user.email.split('@')[0].replace('.', ' ').title(),
                    "role": user.role
                }
                for user in all_users
            ]
            
            return Response({
                "project_id": None,
                "project_name": "General / No Project",
                "members": members_data
            })
        
        try:
            project = Projects.objects.get(id=project_id)
            print(f"Found project: {project.name}")
        except Projects.DoesNotExist:
            print(f"Project {project_id} not found")
            return Response(
                {"error": "Project not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get all users assigned to tasks in this project
        from django.db.models import Q
        project_specific_members = User.objects.filter(
            Q(assigned_tasks__task__project=project) |
            Q(created_projects=project) |
            Q(id=project.project_lead_id) |
            Q(id=project.handled_by_id)
        ).distinct()
        print(f"Project-specific members: {project_specific_members.count()}")
        for user in project_specific_members:
            print(f"  - {user.email} ({user.role})")
        
        # Always include all ADMIN and MANAGER role users
        admin_manager_users = User.objects.filter(
            Q(role='ADMIN') | Q(role='MANAGER')
        ).distinct()
        print(f"ADMIN/MANAGER users: {admin_manager_users.count()}")
        
        # Combine both querysets and remove duplicates
        all_members = (project_specific_members | admin_manager_users).distinct()
        print(f"Total combined members: {all_members.count()}")
        
        members_data = [
            {
                "id": user.id,
                "email": user.email,
                "name": user.employee_name if user.employee_name else user.email.split('@')[0].replace('.', ' ').title(),
                "role": user.role
            }
            for user in all_members
        ]
        
        return Response({
            "project_id": project.id,
            "project_name": project.name,
            "members": members_data
        })


class DashboardViewSet(viewsets.GenericViewSet):
    """ViewSet for admin dashboard APIs"""
    permission_classes = [AllowAny]  # Temporarily allow unauthenticated access for testing
    serializer_class = None  # Not used - all endpoints are custom actions
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get dashboard statistics for cards"""
        user = request.user
        
        # PROJECT PORTFOLIO
        if not user or not user.is_authenticated or user.role == 'ADMIN':
            projects = Projects.objects.all()
        else:
            projects = Projects.objects.filter(
                models.Q(created_by=user) | 
                models.Q(project_lead=user) | 
                models.Q(handled_by=user)
            ).distinct()
        
        project_stats = {
            'total': projects.count(),
            'active': projects.filter(status='ACTIVE').count(),
            'done': projects.filter(status='COMPLETED').count()
        }
        
        # TIMELINE HEALTH
        today = timezone.now().date()
        timeline_stats = {
            'total': projects.count(),
            'on_track': projects.filter(due_date__gte=today, status='ACTIVE').count(),
            'overdue': projects.filter(due_date__lt=today, status__in=['ACTIVE', 'ON HOLD']).count()
        }
        
        # TASK EFFICIENCY
        if not user or not user.is_authenticated or user.role == 'ADMIN':
            tasks = Task.objects.all()
        else:
            tasks = Task.objects.filter(
                models.Q(assignees__user=user) | 
                models.Q(project__created_by=user)
            ).distinct()
        
        task_stats = {
            'total': tasks.count(),
            'completed': tasks.filter(status='DONE').count(),
            'pending': tasks.filter(status='PENDING').count()
        }
        
        # CRITICAL ATTENTION
        critical_tasks = tasks.filter(priority='CRITICAL').count()
        rejected_approvals = ApprovalRequest.objects.filter(status='REJECTED').count()
        
        critical_stats = {
            'total': critical_tasks + rejected_approvals,
            'critical': critical_tasks,
            'rejected': rejected_approvals
        }
        
        return Response({
            'project_portfolio': project_stats,
            'timeline_health': timeline_stats,
            'task_efficiency': task_stats,
            'critical_attention': critical_stats
        })
    
    @action(detail=False, methods=['get'])
    def critical_attention(self, request):
        """Get critical attention items - overdue tasks"""
        user = request.user
        today = timezone.now().date()
        
        # Get overdue tasks
        if not user or not user.is_authenticated or user.role == 'ADMIN':
            tasks = Task.objects.filter(
                due_date__lt=today,
                status__in=['PENDING', 'IN_PROGRESS']
            ).select_related('project').prefetch_related('assignees__user')
        else:
            tasks = Task.objects.filter(
                due_date__lt=today,
                status__in=['PENDING', 'IN_PROGRESS']
            ).filter(
                models.Q(assignees__user=user) | 
                models.Q(project__created_by=user)
            ).distinct().select_related('project').prefetch_related('assignees__user')
        
        critical_items = []
        for task in tasks:
            days_overdue = (today - task.due_date).days
            assignees = [
                {'email': assignee.user.email, 'role': assignee.role}
                for assignee in task.assignees.all()
            ]
            
            critical_items.append({
                'id': task.id,
                'title': task.title,
                'project': task.project.name,
                'assignees': assignees,
                'due_date': task.due_date,
                'days_overdue': days_overdue,
                'priority': task.priority,
                'status': task.status
            })
        
        # Sort by days overdue (descending)
        critical_items.sort(key=lambda x: x['days_overdue'], reverse=True)
        
        return Response({
            'count': len(critical_items),
            'items': critical_items
        })
    
    @action(detail=False, methods=['get'], url_path='team-activity-status')
    def team_activity_status(self, request):
        """Get team activity status - daily capacity tracking"""
        user = request.user
        today = timezone.now().date()
        daily_capacity_hours = 9  # Target: 9 hours per day
        
        # Get all users in the team
        if not user or not user.is_authenticated:
            users = User.objects.filter(is_active=True)
        elif user.role == 'ADMIN':
            users = User.objects.filter(is_active=True)
        elif user.role in ['MANAGER', 'TEAMLEAD'] and user.department:
            users = User.objects.filter(department=user.department, is_active=True)
        else:
            users = User.objects.filter(id=user.id)
        
        # Calculate hours worked today for each user
        filled_users = 0
        not_filled_users = 0
        user_details = []
        
        for u in users:
            hours_today = ActivityLog.objects.filter(
                user=u,
                actual_start_time__date=today
            ).aggregate(total=Sum('hours_worked'))['total'] or 0
            
            is_filled = hours_today >= daily_capacity_hours
            
            if is_filled:
                filled_users += 1
            else:
                not_filled_users += 1
            
            user_details.append({
                'email': u.email,
                'name': u.employee_name if u.employee_name else u.email.split('@')[0].replace('.', ' ').title(),
                'role': u.role,
                'hours_worked': float(hours_today),
                'is_filled': is_filled,
                'percentage': min(100, round((float(hours_today) / daily_capacity_hours) * 100, 2))
            })
        
        return Response({
            'daily_capacity_target': daily_capacity_hours,
            'total_users': users.count(),
            'filled': filled_users,
            'not_filled': not_filled_users,
            'filled_percentage': round((filled_users / users.count() * 100), 2) if users.count() > 0 else 0,
            'not_filled_percentage': round((not_filled_users / users.count() * 100), 2) if users.count() > 0 else 0,
            'users': user_details
        })

    @action(detail=False, methods=['get'], url_path='users-for-stats')
    def users_for_stats(self, request):
        """Get list of users for project work stats dropdown"""
        user = request.user
        
        # Permission logic for users list
        if not user or not user.is_authenticated:
            users = User.objects.filter(is_active=True)
        elif user.role == 'ADMIN':
            users = User.objects.filter(is_active=True)
        elif user.role in ['MANAGER', 'TEAMLEAD'] and user.department:
            users = User.objects.filter(department=user.department, is_active=True)
        else:
            users = User.objects.filter(id=user.id, is_active=True)
        
        user_list = []
        for u in users:
            # For each user, count projects they are involved in
            assigned_task_ids = TaskAssignee.objects.filter(user=u).values_list('task_id', flat=True)
            projects_count = Projects.objects.filter(
                models.Q(tasks__id__in=assigned_task_ids) | 
                models.Q(project_lead=u) | 
                models.Q(handled_by=u)
            ).distinct().count()
            
            user_list.append({
                'id': u.id,
                'email': u.email,
                'name': u.employee_name if u.employee_name else u.email.split('@')[0].replace('.', ' ').title(),
                'role': u.role,
                'department': u.department.name if u.department else None,
                'projects_count': projects_count
            })
        
        user_list.sort(key=lambda x: x['name'])
        return Response({'users': user_list})

    @action(detail=False, methods=['get'], url_path='project-work-stats')
    def project_work_stats(self, request):
        """Get detailed project work stats for donut chart and KPIs"""
        user = request.user
        target_user_id = request.query_params.get('user_id')
        project_id_filter = request.query_params.get('project_id')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        # Date parsing
        start_date = None
        end_date = None
        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pass

        # User resolution
        if target_user_id == 'null' or target_user_id == '':
            target_user_id = None
            
        if not target_user_id and (not user or not user.is_authenticated):
             return Response({'error': 'user_id required'}, status=400)
        
        target_user_id = target_user_id or user.id
        try:
            target_user = User.objects.get(id=target_user_id)
        except (User.DoesNotExist, ValueError):
            return Response({'error': 'User not found'}, status=404)

        # GET ALL PROJECTS FOR DROPDOWN
        # This includes any project the user is Lead, Handled by, Author, or has an Assigned Task
        assigned_task_ids = TaskAssignee.objects.filter(user=target_user).values_list('task_id', flat=True)
        all_user_projects = Projects.objects.filter(
            models.Q(tasks__id__in=assigned_task_ids) | 
            models.Q(project_lead=target_user) | 
            models.Q(handled_by=target_user) |
            models.Q(created_by=target_user) |
            models.Q(assignees=target_user)
        ).distinct()

        all_projects_list = [
            {'id': p.id, 'name': p.name} for p in all_user_projects
        ]

        # FILTER PROJECTS FOR ACTUAL STATS
        stats_projects = all_user_projects
        if project_id_filter and project_id_filter != 'null' and project_id_filter != '':
            stats_projects = stats_projects.filter(id=project_id_filter)

        project_results = []
        total_planned_hours = 0.0
        total_achieved_hours = 0.0
        total_tasks_count = 0
        total_completed_count = 0

        for project in stats_projects:
            # Smart task filtering:
            # - Leads, Handles, and Authors see the WHOLE project's tasks
            # - Other assignees see only their SPECIFIC assigned tasks
            # - Project-level assignees (with no specific tasks yet) see the whole project too
            
            user_tasks_qs = Task.objects.filter(project=project)
            
            is_responsible_for_project = (
                project.project_lead == target_user or 
                project.handled_by == target_user or 
                project.created_by == target_user or
                project.assignees.filter(id=target_user.id).exists()
            )
            
            if not is_responsible_for_project:
                # Regular worker: filter to their specific tasks
                user_tasks_qs = user_tasks_qs.filter(assignees__user=target_user).distinct()
            
            user_tasks_qs = user_tasks_qs.distinct()

            # Apply date filters if provided
            if start_date:
                user_tasks_qs = user_tasks_qs.filter(start_date__gte=start_date)
            if end_date:
                user_tasks_qs = user_tasks_qs.filter(due_date__lte=end_date)

            # Materialise queryset once
            tasks_list = list(user_tasks_qs)
            total_tasks_ct = len(tasks_list)
            if total_tasks_ct == 0:
                continue

            # Planned hours: sum of task.planned_hours (DB field set at creation)
            p_planned = sum(float(t.planned_hours or 0) for t in tasks_list)

            # Achieved hours: sum of actual ActivityLog time for DONE tasks
            p_achieved = sum(t.get_achieved_hours() for t in tasks_list)

            total_planned_hours += p_planned
            total_achieved_hours += p_achieved

            completed_tasks = sum(1 for t in tasks_list if t.status == 'DONE')
            total_tasks_count += total_tasks_ct
            total_completed_count += completed_tasks

            # Per-task breakdown for donut chart segments
            tasks_data = [
                {
                    'id': t.id,
                    'title': t.title,
                    'planned_hours': float(t.planned_hours or 0),
                    'achieved_hours': float(t.get_achieved_hours()),
                    'status': t.status,
                }
                for t in tasks_list
            ]

            project_results.append({
                'id': project.id,
                'name': project.name,
                'planned_hours': p_planned,
                'achieved_hours': p_achieved,
                'project_budget_hours': float(project.working_hours or 0),
                'total_tasks': total_tasks_ct,
                'completed_tasks': completed_tasks,
                'completion_percentage': round((completed_tasks / total_tasks_ct) * 100),
                'tasks': tasks_data,
            })

        return Response({
            'user': {
                'id': target_user.id,
                'name': target_user.name
            },
            'all_projects': all_projects_list,
            'projects': project_results,
            'total_planned_hours': total_planned_hours,
            'total_achieved_hours': total_achieved_hours,
            'total_tasks_count': total_tasks_count,
            'completed_tasks_count': total_completed_count,
            'overall_completion_percentage': round(
                (total_achieved_hours / total_planned_hours * 100)
                if total_planned_hours > 0 else 0
            ),
        })


class TeamOverviewViewSet(viewsets.GenericViewSet):
    """ViewSet for team overview and monitoring"""
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = None  # Not used - all endpoints are custom actions
    
    @action(detail=False, methods=['get'])
    def team_members(self, request):
        """Get all team members with their statistics based on hierarchy
        
        Query Parameters:
            - all_users: If 'true', returns all active users (for project assignments)
        """
        # When an admin is impersonating an employee, request.user is the employee.
        # We must use the original admin user for role-based filtering on this endpoint.
        user = getattr(request, 'admin_user', None) or request.user
        today = timezone.now().date()
        
        # Check if all_users parameter is set (for project assignments)
        all_users_param = request.query_params.get('all_users', '').lower() == 'true'
        
        # Get team members based on role and hierarchy
        if all_users_param:
            # For project assignments, show all active users to everyone
            team_members = User.objects.filter(is_active=True)
        elif user.role == 'ADMIN':
            # Admin can see everyone
            team_members = User.objects.filter(is_active=True)
        elif user.role == 'MANAGER':
            # Manager can see all team leads and their members, plus unassigned employees
            team_leads = User.objects.filter(role='TEAMLEAD', is_active=True)
            employees_under_leads = User.objects.filter(team_lead__in=team_leads, is_active=True)
            unassigned_employees = User.objects.filter(
                role='EMPLOYEE', 
                team_lead__isnull=True, 
                is_active=True
            )
            team_members = (team_leads | employees_under_leads | unassigned_employees).distinct()
        elif user.role == 'TEAMLEAD':
            # Team lead can only see their direct team members
            team_members = User.objects.filter(team_lead=user, is_active=True) | User.objects.filter(id=user.id)
        else:
            # Regular employees can only see themselves (for team overview)
            team_members = User.objects.filter(id=user.id)
        
        members_data = []
        
        # If all_users param is set, return basic user info only (for project assignments)
        if all_users_param:
            for member in team_members:
                members_data.append({
                    'id': member.id,
                    'email': member.email,
                    'name': member.employee_name if member.employee_name else member.email.split('@')[0].replace('.', ' ').title(),
                    'role': member.role,
                    'department': member.department.name if member.department else "Unassigned",
                })
            
            return Response({
                'count': len(members_data),
                'members': members_data
            })
        
        # Otherwise, return full statistics for team overview
        for member in team_members:
            # Get task statistics
            assigned_tasks = TaskAssignee.objects.filter(user=member)
            active_tasks = assigned_tasks.filter(
                task__status__in=['PENDING', 'IN_PROGRESS']
            ).count()
            completed_tasks = assigned_tasks.filter(
                task__status='DONE'
            ).count()
            
            # Calculate workload intensity (based on today's plan)
            todays_plan = TodayPlan.objects.filter(
                user=member,
                plan_date=today
            )
            total_planned_minutes = todays_plan.aggregate(
                total=Sum('planned_duration_minutes')
            )['total'] or 0
            
            # Workload intensity: percentage of 8-hour workday (480 minutes)
            workload_intensity = min(100, int((total_planned_minutes / 480) * 100))
            
            # Calculate current focus (hours logged today / daily target)
            daily_target_hours = 9
            hours_logged_today = ActivityLog.objects.filter(
                user=member,
                actual_start_time__date=today
            ).aggregate(total=Sum('hours_worked'))['total'] or 0
            
            current_focus = min(100, int((float(hours_logged_today) / daily_target_hours) * 100))
            
            # Get department name
            department_name = member.department.name if member.department else "Unassigned"
            
            # Get team lead info
            team_lead_email = member.team_lead.email if member.team_lead else None
            team_lead_name = member.team_lead.employee_name if (member.team_lead and member.team_lead.employee_name) else (member.team_lead.email.split('@')[0] if member.team_lead else None)
            
            members_data.append({
                'id': member.id,
                'email': member.email,
                'name': member.employee_name if member.employee_name else member.email.split('@')[0].replace('.', ' ').title(),
                'role': member.role,
                'department': department_name,
                'team_lead_id': member.team_lead_id,
                'team_lead_email': team_lead_email,
                'team_lead_name': team_lead_name,
                'active_tasks': active_tasks,
                'completed_tasks': completed_tasks,
                'workload_intensity': workload_intensity,
                'current_focus': current_focus,
                'phone_number': member.phone_number or ''
            })
        
        # Pagination
        total_count = len(members_data)
        try:
            page = max(1, int(request.query_params.get('page', 1)))
            page_size = max(1, min(50, int(request.query_params.get('page_size', 10))))
        except (ValueError, TypeError):
            page = 1
            page_size = 10
        
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_members = members_data[start:end]
        
        # Calculate dynamic team stats
        total_active_tasks = sum(m['active_tasks'] for m in members_data)
        total_completed_tasks = sum(m['completed_tasks'] for m in members_data)
        total_tasks = total_active_tasks + total_completed_tasks
        completion_rate = int((total_completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
        
        from datetime import timedelta
        start_of_week = today - timedelta(days=today.weekday())
        tasks_this_week = TaskAssignee.objects.filter(
            user__in=team_members,
            task__created_at__date__gte=start_of_week
        ).values('task').distinct().count()
        
        active_projects = TaskAssignee.objects.filter(
            user__in=team_members,
            task__status__in=['PENDING', 'IN_PROGRESS']
        ).values('task__project').distinct().count()

        return Response({
            'count': len(paginated_members),
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'members': paginated_members,
            'team_stats': {
                'active_projects': active_projects,
                'tasks_this_week': tasks_this_week,
                'completion_rate': completion_rate
            }
        })
    
    @action(detail=False, methods=['get'])
    def member_dashboard(self, request):
        """Get detailed dashboard for a specific team member"""
        member_id = request.query_params.get('member_id')
        
        if not member_id:
            return Response(
                {"error": "member_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        
        # Check permissions
        try:
            member = User.objects.get(id=member_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Member not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify access rights
        if user.role not in ['ADMIN', 'MANAGER', 'TEAMLEAD']:
            if member.id != user.id:
                return Response(
                    {"error": "You don't have permission to view this member's dashboard"},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif user.role in ['MANAGER', 'TEAMLEAD']:
            if member.department != user.department:
                return Response(
                    {"error": "You can only view members from your department"},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        today = timezone.now().date()
        
        # Member basic info
        member_info = {
            'id': member.id,
            'email': member.email,
            'name': member.email.split('@')[0].replace('.', ' ').title(),
            'role': member.role,
            'department': member.department.name if member.department else "Unassigned",
            'phone_number': member.phone_number or ''
        }
        
        # Task statistics
        assigned_tasks = TaskAssignee.objects.filter(user=member).select_related('task', 'task__project')
        
        active_tasks_details = []
        for assignee in assigned_tasks.filter(task__status__in=['PENDING', 'IN_PROGRESS']):
            active_tasks_details.append({
                'id': assignee.task.id,
                'title': assignee.task.title,
                'project': assignee.task.project.name,
                'priority': assignee.task.priority,
                'status': assignee.task.status,
                'due_date': assignee.task.due_date,
                'role': assignee.role
            })
        
        completed_tasks_details = []
        for assignee in assigned_tasks.filter(task__status='DONE'):
            completed_tasks_details.append({
                'id': assignee.task.id,
                'title': assignee.task.title,
                'project': assignee.task.project.name,
                'priority': assignee.task.priority,
                'completed_at': assignee.task.completed_at,
                'role': assignee.role
            })
        
        # Today's plan
        todays_plan = TodayPlan.objects.filter(
            user=member,
            plan_date=today
        ).select_related('catalog_item').order_by('order_index')
        
        plan_items = []
        total_planned_minutes = 0
        for plan in todays_plan:
            plan_items.append({
                'id': plan.id,
                'name': plan.catalog_item.name,
                'type': plan.catalog_item.catalog_type,
                'quadrant': plan.quadrant,
                'scheduled_start': plan.scheduled_start_time,
                'scheduled_end': plan.scheduled_end_time,
                'duration_minutes': plan.planned_duration_minutes,
                'status': plan.status
            })
            total_planned_minutes += plan.planned_duration_minutes
        
        # Activity logs for today
        activity_logs = ActivityLog.objects.filter(
            user=member,
            actual_start_time__date=today
        ).select_related('today_plan__catalog_item')
        
        activity_summary = []
        total_hours_logged = 0
        for log in activity_logs:
            activity_summary.append({
                'id': log.id,
                'task_name': log.today_plan.catalog_item.name,
                'start_time': log.actual_start_time,
                'end_time': log.actual_end_time,
                'hours_worked': float(log.hours_worked),
                'status': log.status,
                'is_completed': log.is_task_completed
            })
            total_hours_logged += float(log.hours_worked)
        
        # Calculate metrics
        workload_intensity = min(100, int((total_planned_minutes / 480) * 100))
        current_focus = min(100, int((total_hours_logged / 9) * 100))
        
        # Pending tasks
        pending_tasks = Pending.objects.filter(
            user=member,
            status='PENDING'
        ).select_related('today_plan__catalog_item')
        
        pending_items = []
        for pending in pending_tasks:
            pending_items.append({
                'id': pending.id,
                'task_name': pending.today_plan.catalog_item.name,
                'original_date': pending.original_plan_date,
                'replanned_date': pending.replanned_date,
                'reason': pending.reason,
                'minutes_left': pending.minutes_left
            })
        
        return Response({
            'member': member_info,
            'statistics': {
                'active_tasks': len(active_tasks_details),
                'completed_tasks': len(completed_tasks_details),
                'workload_intensity': workload_intensity,
                'current_focus': current_focus,
                'total_hours_logged_today': round(total_hours_logged, 2),
                'pending_tasks': len(pending_items)
            },
            'active_tasks': active_tasks_details,
            'completed_tasks': completed_tasks_details,
            'todays_plan': plan_items,
            'activity_logs': activity_summary,
            'pending_tasks': pending_items
        })
    
    @action(detail=False, methods=['get'])
    def department_stats(self, request):
        """Get statistics by department"""
        user = request.user
        
        if user.role not in ['ADMIN', 'MANAGER', 'TEAMLEAD']:
            return Response(
                {"error": "Only admins, managers, and team leads can view department statistics"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all departments or just user's department
        if user.role == 'ADMIN':
            from .models import Department
            departments = Department.objects.all()
        else:
            from .models import Department
            departments = Department.objects.filter(id=user.department_id)
        
        dept_stats = []
        
        for dept in departments:
            members = User.objects.filter(department=dept, is_active=True)
            member_count = members.count()
            
            if member_count == 0:
                continue
            
            # Calculate aggregate statistics
            total_active_tasks = 0
            total_completed_tasks = 0
            total_workload = 0
            total_focus = 0
            
            today = timezone.now().date()
            
            for member in members:
                # Active tasks
                active = TaskAssignee.objects.filter(
                    user=member,
                    task__status__in=['PENDING', 'IN_PROGRESS']
                ).count()
                total_active_tasks += active
                
                # Completed tasks
                completed = TaskAssignee.objects.filter(
                    user=member,
                    task__status='DONE'
                ).count()
                total_completed_tasks += completed
                
                # Workload
                planned_minutes = TodayPlan.objects.filter(
                    user=member,
                    plan_date=today
                ).aggregate(total=Sum('planned_duration_minutes'))['total'] or 0
                total_workload += min(100, int((planned_minutes / 480) * 100))
                
                # Focus
                hours_logged = ActivityLog.objects.filter(
                    user=member,
                    actual_start_time__date=today
                ).aggregate(total=Sum('hours_worked'))['total'] or 0
                total_focus += min(100, int((float(hours_logged) / 9) * 100))
            
            dept_stats.append({
                'department': dept.name,
                'member_count': member_count,
                'total_active_tasks': total_active_tasks,
                'total_completed_tasks': total_completed_tasks,
                'avg_workload_intensity': round(total_workload / member_count, 2) if member_count > 0 else 0,
                'avg_current_focus': round(total_focus / member_count, 2) if member_count > 0 else 0
            })
        
        return Response({
            'count': len(dept_stats),
            'departments': dept_stats
        })
    
    @action(detail=False, methods=['post'])
    def assign_team_lead(self, request):
        """Assign or update team lead for employees (Admin/Manager only)"""
        user = request.user
        
        # Check permissions
        if user.role not in ['ADMIN', 'MANAGER']:
            return Response(
                {"error": "Only Admins and Managers can assign team leads"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        employee_id = request.data.get('employee_id')
        team_lead_id = request.data.get('team_lead_id')  # Can be None to unassign
        
        if not employee_id:
            return Response(
                {"error": "employee_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            employee = User.objects.get(id=employee_id)
        except User.objects.DoesNotExist:
            return Response(
                {"error": "Employee not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate team lead if provided
        team_lead = None
        if team_lead_id:
            try:
                team_lead = User.objects.get(id=team_lead_id)
                if team_lead.role != 'TEAMLEAD':
                    return Response(
                        {"error": "Selected user is not a Team Lead"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except User.DoesNotExist:
                return Response(
                    {"error": "Team Lead not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Update assignment
        employee.team_lead = team_lead
        employee.save()
        
        action_message = f"assigned to {team_lead.email}" if team_lead else "unassigned from team lead"
        
        return Response({
            "message": f"Employee {employee.email} {action_message}",
            "employee": {
                "id": employee.id,
                "email": employee.email,
                "team_lead_id": employee.team_lead_id,
                "team_lead_email": employee.team_lead.email if employee.team_lead else None
            }
        })
    
    @action(detail=False, methods=['post'])
    def bulk_assign_team_lead(self, request):
        """Bulk assign team lead to multiple employees (Admin/Manager only)"""
        user = request.user
        
        # Check permissions
        if user.role not in ['ADMIN', 'MANAGER']:
            return Response(
                {"error": "Only Admins and Managers can assign team leads"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        employee_ids = request.data.get('employee_ids', [])
        team_lead_id = request.data.get('team_lead_id')  # Can be None to unassign
        
        if not employee_ids:
            return Response(
                {"error": "employee_ids array is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate team lead if provided
        team_lead = None
        if team_lead_id:
            try:
                team_lead = User.objects.get(id=team_lead_id)
                if team_lead.role != 'TEAMLEAD':
                    return Response(
                        {"error": "Selected user is not a Team Lead"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except User.DoesNotExist:
                return Response(
                    {"error": "Team Lead not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Update all employees
        employees = User.objects.filter(id__in=employee_ids)
        updated_count = employees.update(team_lead=team_lead)
        
        action_message = f"assigned to {team_lead.email}" if team_lead else "unassigned from team leads"
        
        return Response({
            "message": f"{updated_count} employees {action_message}",
            "updated_count": updated_count
        })
    
    @action(detail=False, methods=['get'])
    def get_team_leads(self, request):
        """Get all available team leads"""
        team_leads = User.objects.filter(role='TEAMLEAD', is_active=True)
        
        team_leads_data = [
            {
                'id': tl.id,
                'email': tl.email,
                'name': tl.email.split('@')[0],
                'department': tl.department.name if tl.department else None,
                'team_member_count': tl.team_members.filter(is_active=True).count()
            }
            for tl in team_leads
        ]
        
        return Response({
            'count': len(team_leads_data),
            'team_leads': team_leads_data
        })
    
    @action(detail=False, methods=['get'])
    def get_my_team(self, request):
        """Get team members for the current team lead"""
        user = request.user
        
        if user.role != 'TEAMLEAD':
            return Response(
                {"error": "Only Team Leads can access this endpoint"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        team_members = User.objects.filter(team_lead=user, is_active=True)
        
        members_data = [
            {
                'id': member.id,
                'email': member.email,
                'name': member.email.split('@')[0],
                'role': member.role,
                'department': member.department.name if member.department else None,
                'phone_number': member.phone_number or ''
            }
            for member in team_members
        ]
        
        return Response({
            'count': len(members_data),
            'team_members': members_data
        })


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing notifications"""
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = NotificationSerializer
    pagination_class = None
    queryset = Notification.objects.all()
    
    def get_queryset(self):
        """Filter notifications for current user"""
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get all unread notifications"""
        unread_notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        )
        serializer = self.get_serializer(unread_notifications, many=True)
        return Response({
            'count': unread_notifications.count(),
            'notifications': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        return Response({'count': count})
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'notification marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read""" 
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)
        return Response({'status': 'all notifications marked as read'})
    
    @action(detail=False, methods=['delete'])
    def delete_read(self, request):
        """Delete all read notifications"""
        deleted_count = Notification.objects.filter(
            user=request.user,
            is_read=True
        ).delete()[0]
        return Response({'status': f'{deleted_count} read notifications deleted'})



class StickyNoteViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = StickyNoteSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        # Admin can view any employee's notes via ?user_id=<id>
        if user.role == 'ADMIN':
            target_user_id = self.request.query_params.get('user_id')
            if target_user_id:
                return StickyNote.objects.filter(user__id=target_user_id)
        return StickyNote.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AutoLoginView(viewsets.GenericViewSet):
    """
    Auto-login endpoint for HRM-DAS integration.
    Validates temporary code from HRM and authenticates user.
    """
    permission_classes = [AllowAny]
    serializer_class = None  # Not used - all endpoints are custom actions
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        Auto-login flow:
        1. Receive code and email from HRM redirect
        2. Validate code with HRM API
        3. Get employee data from HRM
        4. Create/update User and Employee in DAS
        5. Generate JWT token
        6. Return token for auto-authentication
        """
        code = request.data.get('code')
        email = request.data.get('email')
        
        if not code or not email:
            return Response({
                'error': 'Code and email are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Call HRM API to validate code and get employee data
            # Use configured HRM URL from settings (supports both dev and production)
            hrm_url = getattr(settings, 'HRM_BASE_URL', 'http://localhost:8001')
            # hrm_url = getattr(settings, 'HRM_BASE_URL', 'https://hrmbackendapi.meridahr.com')
            
            # Remove trailing slash if present to avoid double slash in URL
            if hrm_url.endswith('/'):
                hrm_url = hrm_url[:-1]
            
            # Log the validation request
            print(f"[DAS AutoLogin] Validating code: code={code[:10]}..., email={email}")
            print(f"[DAS AutoLogin] Calling HRM at: {hrm_url}/api/validate-das-code/")
            
            # Use requests with basic headers to prevent 403 blocks from strict servers
            headers = {'Content-Type': 'application/json', 'User-Agent': 'DAS-Backend/1.0'}
            
            # Validate code with HRM
            # Disable SSL verification for development to avoid certification errors
            verify_ssl = getattr(settings, 'VERIFY_SSL_HRM', True)
            
            response = requests.post(
                f'{hrm_url}/api/validate-das-code/',
                json={'code': code, 'email': email},
                headers=headers,
                timeout=30,
                verify=verify_ssl
            )
            
            # Log the response
            print(f"[DAS AutoLogin] HRM Response Status: {response.status_code}")
            print(f"[DAS AutoLogin] HRM Response Body: {response.text[:500]}")
            
            if response.status_code != 200:
                error_data = response.json()
                print(f"[DAS AutoLogin] Validation failed: {error_data}")
                return Response({
                    'error': error_data.get('error', 'Code validation failed')
                }, status=response.status_code)
            
            validation_result = response.json()
            
            if not validation_result.get('valid'):
                print(f"[DAS AutoLogin] Validation returned invalid: {validation_result.get('error')}")
                return Response({
                    'error': validation_result.get('error', 'Invalid code')
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            employee_data = validation_result.get('employee')
            
            if not employee_data:
                print(f"[DAS AutoLogin] No employee data in response")
                return Response({
                    'error': 'Employee data not found in validation response'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            print(f"[DAS AutoLogin] Validation successful: employee={employee_data.get('full_name')}")
            
            # Map HRM designation to DAS role
            hrm_designation = employee_data.get('designation')
            das_role = 'EMPLOYEE'  # Default role
            
            if hrm_designation == 'Admin':
                das_role = 'ADMIN'
            elif hrm_designation == 'HR':
                das_role = 'MANAGER'
            elif hrm_designation in ['Employee', 'Recruiter']:
                das_role = 'EMPLOYEE'
            
            # Create or update User in DAS
            user, created = User.objects.update_or_create(
                email=email,
                defaults={
                    'hrm_employee_id': employee_data.get('employee_Id'),
                    'employee_name': employee_data.get('full_name'),
                    'employee_type': employee_data.get('Employeement_Type'),
                    'designation': hrm_designation,
                    'role': das_role,  # Map designation to role
                    'location': employee_data.get('work_location'),
                    'date_of_joining': employee_data.get('hired_date'),
                    'is_active_in_hrm': True,
                    'last_sync_time': timezone.now(),
                    'is_active': True,
                }
            )
            
            # Set password for new users (they won't use it since auto-login)
            if created:
                random_password = secrets.token_urlsafe(16)
                user.set_password(random_password)
                user.save()
            
            # Create or update Employee profile in DAS
            Employee.objects.update_or_create(
                user=user,
                defaults={
                    'hrm_employee_id': employee_data.get('employee_Id'),
                    'is_active_in_hrm': True,
                }
            )
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            print(f"[DAS AutoLogin] JWT tokens created for user: {user.email}")
            
            return Response({
                'success': True,
                'message': 'Auto-login successful',
                'user_id': user.id,
                'email': user.email,
                'name': user.employee_name,
                'role': user.role,
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'is_new_user': created,
            }, status=status.HTTP_200_OK)
            
        except requests.exceptions.Timeout:
            return Response({
                'error': 'HRM service timeout - please try again'
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)
        except requests.exceptions.RequestException as e:
            return Response({
                'error': f'Failed to connect to HRM service: {str(e)}'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


# ─── Project Working Hours Report ─────────────────────────────────────────────

class ProjectWorkingHoursViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access

    def list(self, request):
        user_id = request.query_params.get('employeeId', request.user.id)
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')

        if not start_date or not end_date:
            return Response({"error": "startDate and endDate are required"}, status=400)

        # Filter activity logs for the user and date range
        logs = ActivityLog.objects.filter(
            user_id=user_id,
            today_plan__plan_date__range=[start_date, end_date]
        ).select_related('today_plan__catalog_item__project', 'today_plan__catalog_item__task__project')

        project_hours = {}
        total_minutes = 0

        for log in logs:
            project = None
            if log.today_plan.catalog_item:
                if log.today_plan.catalog_item.project:
                    project = log.today_plan.catalog_item.project
                elif log.today_plan.catalog_item.task and log.today_plan.catalog_item.task.project:
                    project = log.today_plan.catalog_item.task.project

            if project:
                p_id = project.id
                if p_id not in project_hours:
                    project_hours[p_id] = {
                        "id": p_id,
                        "name": project.name,
                        "minutes": 0,
                    }
                project_hours[p_id]["minutes"] += log.minutes_worked
                total_minutes += log.minutes_worked

        # Format for response
        projects_data = []
        for p_id, data in project_hours.items():
            percentage = (data["minutes"] / total_minutes * 100) if total_minutes > 0 else 0
            projects_data.append({
                "id": data["id"],
                "name": data["name"],
                "hours": round(data["minutes"] / 60, 2),
                "minutes": data["minutes"],
                "percentage": round(percentage, 1)
            })

        return Response({
            "total_hours": round(total_minutes / 60, 2),
            "total_minutes": total_minutes,
            "projects": projects_data
        })

    @action(detail=True, methods=['get'])
    def drilldown(self, request, pk=None):
        user_id = request.query_params.get('employeeId', request.user.id)
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')

        logs = ActivityLog.objects.filter(
            user_id=user_id,
            today_plan__plan_date__range=[start_date, end_date]
        ).filter(
            models.Q(today_plan__catalog_item__project_id=pk) |
            models.Q(today_plan__catalog_item__task__project_id=pk)
        ).select_related('today_plan__catalog_item__task', 'today_plan__catalog_item__project')

        task_breakdown = {}
        for log in logs:
            task = None
            if log.today_plan.catalog_item:
                if log.today_plan.catalog_item.task:
                    task = log.today_plan.catalog_item.task
            
            task_id = task.id if task else 0
            task_title = task.title if task else (log.today_plan.catalog_item.name if log.today_plan.catalog_item else "Direct Project Work")
            
            if task_id not in task_breakdown:
                task_breakdown[task_id] = {
                    "id": task_id,
                    "title": task_title,
                    "minutes": 0,
                    "completion_percentage": task.calculate_progress() if task else 100,
                    "subtasks": []
                }
                if task:
                    for st in task.subtasks.all():
                        task_breakdown[task_id]["subtasks"].append({
                            "id": st.id,
                            "title": st.title,
                            "status": st.status,
                            "weight": st.progress_weight
                        })
            
            task_breakdown[task_id]["minutes"] += log.minutes_worked

        return Response(list(task_breakdown.values()))



# ─── Team Activity Status ───────────────────────────────────────────────────────

class TeamActivityStatusViewSet(viewsets.GenericViewSet):
    """
    GET /api/team-activity-status/today/
    Query param: date (dd-mm-yyyy), defaults to today. Target: 9h = 540 min.
    """
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = None  # Not used - all endpoints are custom actions
    DAILY_TARGET_MINUTES = 540

    @action(detail=False, methods=['get'])
    def today(self, request):
        date_str = request.query_params.get('date')
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%d-%m-%Y').date()
            except ValueError:
                target_date = timezone.localdate()
        else:
            target_date = timezone.localdate()

        user = request.user
        if user.role == 'ADMIN':
            team_users = list(User.objects.filter(is_active=True))
        else:
            subordinates = user.get_all_subordinates()
            team_users = list(User.objects.filter(id__in=[u.id for u in subordinates], is_active=True))

        filled = []
        not_filled = []

        for member in team_users:
            day_minutes = ActivityLog.objects.filter(
                user=member,
                actual_start_time__date=target_date,
                status='COMPLETED'
            ).aggregate(total=models.Sum('minutes_worked'))['total'] or 0

            hours = int(day_minutes) // 60
            minutes = int(day_minutes) % 60
            entry = {
                'user_id': member.id,
                'name': member.employee_name or member.email.split('@')[0],
                'email': member.email,
                'total_minutes': day_minutes,
                'display': f'{hours}h {minutes:02d}m',
            }
            if day_minutes >= self.DAILY_TARGET_MINUTES:
                filled.append(entry)
            else:
                not_filled.append(entry)

        total = len(filled) + len(not_filled)
        filled_pct = round(len(filled) / total * 100) if total > 0 else 0

        return Response({
            'date': target_date.strftime('%d-%m-%Y'),
            'daily_target_hours': 9,
            'total_users': total,
            'filled': {'count': len(filled), 'percentage': filled_pct, 'users': filled},
            'not_filled': {'count': len(not_filled), 'percentage': 100 - filled_pct, 'users': not_filled},
        })


# ─── HRM Employee Sync ViewSet ────────────────────────────────────────────────

class SyncHRMEmployeesViewSet(viewsets.GenericViewSet):
    """
    Sync all active employees from HRM to DAS
    POST /api/sync-hrm-employees/sync/
    """
    permission_classes = [IsAuthenticated, IsAdmin]  # Only admins can trigger sync
    serializer_class = None  # Not used - all endpoints are custom actions
    
    @action(detail=False, methods=['post'])
    def sync(self, request):
        """
        Fetch all active employees from HRM and create/update DAS users
        """
        # Get HRM URL from settings or request
        from django.conf import settings
        # hrm_url = getattr(settings, 'HRM_BASE_URL', 'https://hrmbackendapi.meridahr.com/')
        hrm_url = getattr(settings, 'HRM_BASE_URL', 'https://localhost:8001')
        
        try:
            # Fetch all active employees from HRM
            response = requests.get(
                f'{hrm_url}/root/api/employees-active/',
                timeout=30
            )
            
            if response.status_code != 200:
                return Response({
                    'success': False,
                    'error': f'Failed to fetch employees from HRM. Status: {response.status_code}'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            data = response.json()
            employees = data.get('employees', [])
            
            if not employees:
                return Response({
                    'success': True,
                    'message': 'No active employees found in HRM',
                    'created': 0,
                    'updated': 0
                })
            
            created_count = 0
            updated_count = 0
            error_count = 0
            errors = []
            
            for emp_data in employees:
                try:
                    email = emp_data.get('email')
                    
                    if not email:
                        continue
                    
                    # Map HRM designation to DAS role
                    hrm_designation = emp_data.get('designation')
                    das_role = 'EMPLOYEE'  # Default role
                    
                    if hrm_designation == 'Admin':
                        das_role = 'ADMIN'
                    elif hrm_designation == 'HR':
                        das_role = 'MANAGER'
                    elif hrm_designation in ['Employee', 'Recruiter']:
                        das_role = 'EMPLOYEE'
                    
                    # Create or update User
                    user, created = User.objects.update_or_create(
                        email=email,
                        defaults={
                            'hrm_employee_id': emp_data.get('employee_Id'),
                            'employee_name': emp_data.get('full_name'),
                            'employee_type': emp_data.get('Employeement_Type'),
                            'designation': hrm_designation,
                            'hrm_department': emp_data.get('department'),
                            'role': das_role,
                            'location': emp_data.get('work_location'),
                            'date_of_joining': emp_data.get('hired_date'),
                            'is_active_in_hrm': True,
                            'last_sync_time': timezone.now(),
                            'is_active': True,
                        }
                    )
                    
                    # Set password for new users (they'll need to reset it)
                    if created:
                        random_password = secrets.token_urlsafe(16)
                        user.set_password(random_password)
                        user.save()
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    # Create or update Employee profile (detailed employee information)
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
                    error_count += 1
                    errors.append({
                        'email': emp_data.get('email', 'unknown'),
                        'error': str(e)
                    })
            
            return Response({
                'success': True,
                'message': f'Sync completed successfully',
                'total_employees': len(employees),
                'created': created_count,
                'updated': updated_count,
                'errors': error_count,
                'error_details': errors if errors else None,
                'sync_time': timezone.now().isoformat()
            })
            
        except requests.exceptions.Timeout:
            return Response({
                'success': False,
                'error': 'HRM service timeout - please try again'
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)
        except requests.exceptions.RequestException as e:
            return Response({
                'success': False,
                'error': f'Failed to connect to HRM service: {str(e)}'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Unexpected error during sync: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─── Planner Catalog ViewSets ────────────────────────────────────────────────
# These endpoints are specifically for the Planner Catalog feature
# They ALWAYS return only items assigned to the logged-in user
# This keeps catalog separate from Dashboard (which shows all team items for admin)

class CatalogProjectViewSet(viewsets.ModelViewSet):
    """
    Dedicated endpoint for Planner Catalog - Returns only projects assigned to the logged-in user
    GET /api/catalog-projects/
    
    This is separate from /api/projects/ which is used by Dashboard and shows all team projects to admin.
    """
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = ProjectSerializer
    queryset = Projects.objects.all()
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'handled_by', 'created_by', 'project_lead']
    search_fields = ['name', 'description']
    ordering_fields = ['start_date', 'due_date', 'create_date', 'name']
    ordering = ['-create_date']
    
    def get_queryset(self):
        """
        Return projects for the planner catalog.
        ADMIN/MANAGER/TEAMLEAD: See all active projects.
        EMPLOYEE: See only projects where they are assigned.
        """
        user = self.request.user
        
        # Admin, Manager, TeamLead see all active projects
        if user.role in ['ADMIN', 'MANAGER', 'TEAMLEAD']:
            return Projects.objects.all().distinct()
        
        # Employees see only their assigned projects
        return Projects.objects.filter(
            models.Q(created_by=user) | 
            models.Q(project_lead=user) | 
            models.Q(handled_by=user) |
            models.Q(tasks__assignees__user=user)
        ).distinct()
    
    def list(self, request, *args, **kwargs):
        """Override list to handle pagination"""
        queryset = self.filter_queryset(self.get_queryset())

        if request.query_params.get('all_projects') == 'true':
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CatalogTaskViewSet(viewsets.ModelViewSet):
    """
    Dedicated endpoint for Planner Catalog - Returns only tasks assigned to the logged-in user
    GET /api/catalog-tasks/
    
    This is separate from /api/tasks/ which is used by Dashboard and shows all team tasks to admin.
    """
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = TaskSerializer
    pagination_class = None
    queryset = Task.objects.all()
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['priority', 'status', 'project', 'due_date', 'start_date']
    search_fields = ['title', 'project__name']
    ordering_fields = ['created_at', 'due_date', 'start_date', 'priority']
    
    def get_queryset(self):
        """
        Return tasks for the planner catalog.
        ADMIN/MANAGER/TEAMLEAD: See all active tasks.
        EMPLOYEE: See only tasks where they are assigned.
        """
        user = self.request.user
        
        # Admin, Manager, TeamLead see all active tasks
        if user.role in ['ADMIN', 'MANAGER', 'TEAMLEAD']:
            return Task.objects.exclude(status='DONE').distinct()
        
        # Employees see only their assigned tasks
        return Task.objects.filter(assignees__user=user).exclude(status='DONE').distinct()


class HoursCompletionLineChartViewSet(viewsets.ViewSet):
    """
    ViewSet for monthly hours completion trend data.
    Shows: Total achieved hours worked per month.
    """
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    
    def list(self, request):
        user = request.user
        year = request.query_params.get('year')
        try:
            year = int(year) if year else timezone.now().year
        except (ValueError, TypeError):
            year = timezone.now().year
            
        filter_type = request.query_params.get('filter', 'my') # 'my' or 'team'
        
        # Base queryset for ActivityLog
        from .models import ActivityLog
        queryset = ActivityLog.objects.all()
        
        if filter_type == 'team' and user.role in ['ADMIN', 'MANAGER', 'TEAMLEAD']:
            # For team, we might want to filter by managed users - but for now show all accessible
            pass
        else:
            # Default to current user
            queryset = queryset.filter(user=user)
            
        months_data = []
        import calendar
        from django.db.models import Sum
        
        for month in range(1, 13):
            month_name = calendar.month_name[month][:3]
            start_date = datetime(year, month, 1).date()
            _, last_day = calendar.monthrange(year, month)
            end_date = datetime(year, month, last_day).date()
            
            monthly_hours = queryset.filter(
                date__range=(start_date, end_date)
            ).aggregate(total=Sum('hours_worked'))['total'] or 0
            
            months_data.append({
                "month": month_name,
                "achieved": float(monthly_hours),
                "planned": 0.0 # Planned per month is complex, using achieved for baseline perfection
            })
            
        return Response(months_data)

class ProjectCompletionLineChartViewSet(viewsets.ViewSet):
    """
    ViewSet for project completion line chart data.
    Shows: Number of projects completed per month
    Filters based on user role:
    - ADMIN: All projects
    - MANAGER: Projects within their hierarchy
    - TEAMLEAD: Projects for their team members
    - EMPLOYEE: Only their projects
    """
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    
    def list(self, request):
        """
        Returns line chart data for project completions grouped by month.
        Query params:
        - months: Number of months to show (default: 12)
        - start_date: Start date in ISO format (default: 12 months ago)
        - end_date: End date in ISO format (default: today)
        - user_id: Filter by specific user (for admin/team lead viewing others)
        """
        user = request.user
        
        # Get query parameters
        months_param = request.query_params.get('months', 12)
        try:
            months_param = int(months_param)
        except (ValueError, TypeError):
            months_param = 12
        
        start_date_param = request.query_params.get('start_date')
        end_date_param = request.query_params.get('end_date')
        user_id_param = request.query_params.get('user_id')
        
        # Set date range
        today = timezone.now().date()
        if end_date_param:
            try:
                end_date = datetime.fromisoformat(end_date_param).date()
            except (ValueError, TypeError):
                end_date = today
        else:
            end_date = today
        
        if start_date_param:
            try:
                start_date = datetime.fromisoformat(start_date_param).date()
            except (ValueError, TypeError):
                start_date = end_date - timedelta(days=30*months_param)
        else:
            start_date = end_date - timedelta(days=30*months_param)
        
        from django.db.models.functions import Coalesce, Cast
        from django.db.models import DateField
        
        # Base queryset for completed projects
        queryset = Projects.objects.filter(status='COMPLETED')
        
        # Filter by date range using completed_date (with fallback to create_date for visibility)
        # Use Cast and output_field to avoid "mixed types: DateField, DateTimeField" error
        queryset = queryset.annotate(
            actual_completion_date=Coalesce(
                'completed_date', 
                Cast('create_date', DateField()),
                output_field=DateField()
            )
        ).filter(
            actual_completion_date__gte=start_date,
            actual_completion_date__lte=end_date
        )
        
        filter_param = request.query_params.get('filter')
        
        # Apply role-based filtering
        if filter_param == 'my':
            # 'my' filter: only show projects explicitly created/led/handled by user
            queryset = queryset.filter(
                Q(created_by=user) | 
                Q(project_lead=user) | 
                Q(handled_by=user) |
                Q(assignees=user) |
                Q(tasks__assignees__user=user)
            ).distinct()
        elif user.role == 'ADMIN':
            # Admin sees all projects
            pass
        elif user.role == 'MANAGER':
            # Manager sees projects where they or their subordinates are involved
            subordinates = user.get_all_subordinates()
            queryset = queryset.filter(
                Q(project_lead=user) |
                Q(handled_by=user) |
                Q(created_by=user) |
                Q(project_lead__in=subordinates) |
                Q(handled_by__in=subordinates) |
                Q(created_by__in=subordinates)
            ).distinct()
        elif user.role == 'TEAMLEAD':
            # Team Lead sees projects for their team members
            team_members = user.get_team_members()
            queryset = queryset.filter(
                Q(project_lead=user) |
                Q(handled_by=user) |
                Q(created_by=user) |
                Q(project_lead__in=team_members) |
                Q(handled_by__in=team_members) |
                Q(created_by__in=team_members)
            ).distinct()
        else:  # EMPLOYEE
            # Employee sees only their own projects
            queryset = queryset.filter(
                Q(project_lead=user) |
                Q(handled_by=user) |
                Q(created_by=user) |
                Q(assignees=user) |
                Q(tasks__assignees__user=user)
            ).distinct()
        
        # Group by month and count completions
        completion_data = []
        current_date = start_date
        
        while current_date <= end_date:
            month_start = current_date.replace(day=1)
            if current_date.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
            
            count = queryset.filter(
                actual_completion_date__gte=month_start,
                actual_completion_date__lte=month_end
            ).count()
            
            completion_data.append({
                'month': month_start.strftime('%Y-%b'),
                'count': count,
                'month_year': month_start.strftime('%B %Y'),
            })
            
            # Move to next month
            current_date = month_end + timedelta(days=1)
        
        total_completed = queryset.count()
        
        response_data = {
            'user_role': user.role,
            'department': user.hrm_department if user.role == 'EMPLOYEE' else None,
            'data': completion_data,
            'total_completed': total_completed,
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            }
        }
        
        return Response(response_data)


class TaskCompletionLineChartViewSet(viewsets.ViewSet):
    """
    ViewSet for task completion line chart data.
    Shows: Number of tasks completed per month
    Filters based on user role:
    - ADMIN: All tasks
    - MANAGER: Tasks within their hierarchy
    - TEAMLEAD: Tasks for their team members
    - EMPLOYEE: Only their tasks
    """
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    
    def list(self, request):
        """
        Returns line chart data for task completions grouped by month.
        Query params:
        - months: Number of months to show (default: 12)
        - start_date: Start date in ISO format (default: 12 months ago)
        - end_date: End date in ISO format (default: today)
        """
        user = request.user
        
        # Get query parameters
        months_param = request.query_params.get('months', 12)
        try:
            months_param = int(months_param)
        except (ValueError, TypeError):
            months_param = 12
        
        start_date_param = request.query_params.get('start_date')
        end_date_param = request.query_params.get('end_date')
        
        # Set date range
        today = timezone.now().date()
        if end_date_param:
            try:
                end_date = datetime.fromisoformat(end_date_param).date()
            except (ValueError, TypeError):
                end_date = today
        else:
            end_date = today
        
        if start_date_param:
            try:
                start_date = datetime.fromisoformat(start_date_param).date()
            except (ValueError, TypeError):
                start_date = end_date - timedelta(days=30*months_param)
        else:
            start_date = end_date - timedelta(days=30*months_param)
        
        from django.db.models.functions import Coalesce, Cast
        from django.db.models import DateField

        # Base queryset for completed tasks
        queryset = Task.objects.filter(status='DONE')

        # Filter by date range using completed_at (with fallback to created_at for visibility)
        # Use Cast and output_field to avoid "mixed types: DateField, DateTimeField" error
        queryset = queryset.annotate(
            actual_completion_date=Coalesce(
                'completed_at', 
                Cast('created_at', DateField()),
                output_field=DateField()
            )
        ).filter(
            actual_completion_date__gte=start_date,
            actual_completion_date__lte=end_date
        )
        
        filter_param = request.query_params.get('filter')
        
        # Apply role-based filtering
        if filter_param == 'my':
            # Match DashboardViewSet.statistics "Task Efficiency" logic
            queryset = queryset.filter(
                Q(assignees__user=user) | 
                Q(project__created_by=user)
            ).distinct()
        elif user.role == 'ADMIN':
            # Admin sees all tasks
            pass
        elif user.role == 'MANAGER':
            # Manager sees tasks where they or their subordinates are involved
            subordinates = user.get_all_subordinates()
            queryset = queryset.filter(
                Q(project_lead=user) |
                Q(assignees__user=user) |
                Q(project_lead__in=subordinates) |
                Q(assignees__user__in=subordinates)
            ).distinct()
        elif user.role == 'TEAMLEAD':
            # Team Lead sees tasks for their team members
            team_members = user.get_team_members()
            queryset = queryset.filter(
                Q(project_lead=user) |
                Q(assignees__user=user) |
                Q(project_lead__in=team_members) |
                Q(assignees__user__in=team_members)
            ).distinct()
        else:  # EMPLOYEE
            # Employee sees only their own tasks
            queryset = queryset.filter(
                Q(project_lead=user) |
                Q(assignees__user=user)
            ).distinct()
        
        # Group by month and count completions
        completion_data = []
        current_date = start_date
        
        while current_date <= end_date:
            month_start = current_date.replace(day=1)
            if current_date.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
            
            count = queryset.filter(
                actual_completion_date__gte=month_start,
                actual_completion_date__lte=month_end
            ).count()
            
            completion_data.append({
                'month': month_start.strftime('%Y-%b'),
                'count': count,
                'month_year': month_start.strftime('%B %Y'),
            })
            
            # Move to next month
            current_date = month_end + timedelta(days=1)
        
        total_completed = queryset.count()
        
        response_data = {
            'user_role': user.role,
            'department': user.hrm_department if user.role == 'EMPLOYEE' else None,
            'data': completion_data,
            'total_completed': total_completed,
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            }
        }
        
        return Response(response_data)




class DailyPlannerViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access
    serializer_class = DailyPlannerSerializer
    queryset = DailyPlanner.objects.all()

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def today(self, request):
        today = timezone.localdate()
        plan, created = DailyPlanner.objects.get_or_create(
            user=request.user, 
            date=today,
            defaults={'planned_hours': 8.0}
        )
        serializer = self.get_serializer(plan)
        return Response(serializer.data)

class AnalyticsViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]  # DEVELOPMENT: Allow unauthenticated access

    @action(detail=False, methods=['get'], url_path='daily')
    def daily_analytics(self, request):
        """GET /api/analytics/daily/?user_id=&days=30"""
        user_id = request.query_params.get('user_id', request.user.id)
        days = int(request.query_params.get('days', 30))
        
        end_date = timezone.localdate()
        start_date = end_date - timedelta(days=days)
        
        # Get daily plans for the trend
        plans = DailyPlanner.objects.filter(
            user_id=user_id,
            date__range=[start_date, end_date]
        ).order_by('date')
        
        data = []
        for plan in plans:
            data.append({
                "date": plan.date,
                "planned": plan.planned_hours,
                "achieved": plan.actual_hours
            })
            
        return Response(data)
    
    @action(detail=True, methods=['get'], url_path='project-bars')
    def project_bars(self, request, pk=None):
        """GET /api/analytics/{project_id}/project-bars/"""
        try:
            project = Projects.objects.get(pk=pk)
            tasks = project.tasks.all()
            
            data = []
            for task in tasks:
                data.append({
                    "task_name": task.title,
                    "planned": float(task.planned_hours),
                    "achieved": float(task.get_achieved_hours())
                })
            
            return Response(data)
        except Projects.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)


class ProjectAnalyticsViewSet(viewsets.GenericViewSet):
    """
    Project Analytics with multi-level filtering for admin dashboard.
    
    Supports 5 filtering scenarios:
    1. View All (no filters)
    2. Select Project Only
    3. Select Employee Only
    4. Select Project → Then Employee (cascading)
    5. Select Employee → Then Project (cascading)
    """
    # Disable all DRF generic machinery - custom actions build their own responses
    queryset = Task.objects.all()
    filter_backends = []

    def get_achieved_hours_for_task(self, task):
        """Calculate total achieved hours from ActivityLog for a specific task"""
        from django.db.models import Sum
        total = ActivityLog.objects.filter(
            today_plan__catalog_item__task=task,
            status='COMPLETED'
        ).aggregate(total=Sum('hours_worked'))['total'] or 0.0
        return float(total)

    def get_task_planned_hours(self, task):
        """Get planned hours for a task"""
        return float(task.planned_hours or 0.0)

    @action(detail=False, methods=['get'], url_path='tasks')
    def tasks_analytics(self, request):
        """
        Get tasks with planned/achieved hours and multi-level filtering.
        
        Query Parameters:
        - project_id: Filter by specific project
        - employee_id: Filter by specific employee
        - Both: Get employee's tasks in that project
        
        Returns:
        - List of tasks with planned/achieved hours
        - Assignee information for each task
        """
        project_id = request.query_params.get('project_id')
        employee_id = request.query_params.get('employee_id')
        
        # Start with all tasks in active projects
        tasks_qs = Task.objects.filter(project__status='ACTIVE')
        
        # Apply project filter if provided
        if project_id:
            tasks_qs = tasks_qs.filter(project_id=project_id)
        
        # Apply employee filter if provided
        if employee_id:
            tasks_qs = tasks_qs.filter(assignees__user_id=employee_id).distinct()
        
        tasks_list = []
        for task in tasks_qs:
            planned_hours = self.get_task_planned_hours(task)
            achieved_hours = self.get_achieved_hours_for_task(task)
            
            # Get assignees for this task
            assignees = []
            for assignee in task.assignees.all():
                assignees.append({
                    'id': assignee.user.id,
                    'email': assignee.user.email,
                    'role': assignee.role
                })
            
            tasks_list.append({
                'id': task.id,
                'title': task.title,
                'project_id': task.project_id,
                'project_name': task.project.name,
                'status': task.status,
                'priority': task.priority,
                'planned_hours': planned_hours,
                'achieved_hours': achieved_hours,
                'progress': min(100, int((achieved_hours / planned_hours * 100) if planned_hours > 0 else 0)),
                'start_date': task.start_date,
                'due_date': task.due_date,
                'assignees': assignees,
            })
        
        return Response({
            'count': len(tasks_list),
            'results': tasks_list,
            'filters': {
                'project_id': project_id,
                'employee_id': employee_id
            }
        })

    @action(detail=False, methods=['get'], url_path='hours')
    def hours(self, request):
        """
        Get project/employee hours with task breakdown - optimized for doughnut chart visualization.
        Flexible filtering: project only, employee only, or both.
        
        This endpoint is specifically designed for doughnut chart rendering with:
        - Center value: Total planned hours (and achieved hours)
        - Slices: Individual task hours in different colors
        
        Query Parameters (at least one required):
        - project_id: Optional. The project to filter by
        - employee_id: Optional. The employee to filter by
        
        Examples:
        1. GET /api/project-analytics/hours/?project_id=58
           → All tasks in project 58
        
        2. GET /api/project-analytics/hours/?employee_id=50
           → All tasks assigned to employee 50 (across all projects)
        
        3. GET /api/project-analytics/hours/?project_id=58&employee_id=50
           → Tasks assigned to employee 50 in project 58
        
        Returns:
        {
            "project": null or {"id": 58, "name": "My Project", "planned_hours": 100},
            "employee": null or {"id": 50, "name": "John Doe", "email": "john@example.com"},
            "tasks": [
                {
                    "id": 1,
                    "name": "Task 1",
                    "project_id": 58,
                    "project_name": "My Project",
                    "planned_hours": 30,
                    "achieved_hours": 25
                },
                ...
            ],
            "totals": {
                "planned_hours": 100,
                "achieved_hours": 75
            },
            "filter": {
                "project_id": 58,
                "employee_id": null
            }
        }
        """
        project_id = request.query_params.get('project_id')
        employee_id = request.query_params.get('employee_id')
        
        # At least one filter is required
        if not project_id and not employee_id:
            return Response(
                {'error': 'At least one of project_id or employee_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Fetch project if provided
        project = None
        project_data = None
        if project_id:
            try:
                project = Projects.objects.get(id=project_id)
                project_data = {
                    'id': project.id,
                    'name': project.name,
                    'planned_hours': float(project.planned_hours or 0.0)
                }
            except Projects.DoesNotExist:
                return Response(
                    {'error': 'Project not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Fetch employee if provided
        employee = None
        employee_data = None
        if employee_id:
            try:
                employee = User.objects.get(id=employee_id)
                employee_data = {
                    'id': employee.id,
                    'name': employee.name,  # Uses the name property (employee_name or email)
                    'email': employee.email
                }
            except User.DoesNotExist:
                return Response(
                    {'error': 'Employee not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Build tasks queryset based on filters
        if project_id and employee_id:
            # Both filters: tasks in project assigned to employee
            tasks_qs = project.tasks.filter(assignees__user_id=employee_id).distinct()
        elif project_id:
            # Project only: all tasks in project
            tasks_qs = project.tasks.all()
        else:
            # Employee only: all tasks assigned to employee (across all projects)
            tasks_qs = Task.objects.filter(assignees__user_id=employee_id).distinct()
        
        # Build tasks data with project info
        tasks_data = []
        total_planned = 0.0
        total_achieved = 0.0
        
        for task in tasks_qs:
            planned_hours = float(task.planned_hours or 0.0)
            achieved_hours = self.get_achieved_hours_for_task(task)
            
            total_planned += planned_hours
            total_achieved += achieved_hours
            
            tasks_data.append({
                'id': task.id,
                'name': task.title,
                'project_id': task.project_id,
                'project_name': task.project.name,
                'planned_hours': planned_hours,
                'achieved_hours': achieved_hours
            })
        
        return Response({
            'project': project_data,
            'employee': employee_data,
            'tasks': tasks_data,
            'totals': {
                'planned_hours': total_planned,
                'achieved_hours': total_achieved
            },
            'filter': {
                'project_id': project_id,
                'employee_id': employee_id
            }
        })

    @action(detail=False, methods=['get'], url_path='employees-for-project')
    def employees_for_project(self, request):
        """
        Get all employees assigned to a specific project (for dropdown filtering).
        
        Query Parameters:
        - project_id: Required. The project to get employees for
        
        Returns:
        - List of employees assigned to the project with task counts
        """
        project_id = request.query_params.get('project_id')
        
        if not project_id:
            return Response(
                {'error': 'project_id query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            project = Projects.objects.get(id=project_id, status='ACTIVE')
        except Projects.DoesNotExist:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get unique employees assigned to tasks in this project
        employees_data = []
        employee_ids_seen = set()
        
        for task in project.tasks.all():
            for assignee in task.assignees.all():
                if assignee.user_id not in employee_ids_seen:
                    # Count tasks for this employee in this project
                    employee_tasks = Task.objects.filter(
                        project=project,
                        assignees__user=assignee.user
                    ).count()
                    
                    employees_data.append({
                        'id': assignee.user.id,
                        'email': assignee.user.email,
                        'name': assignee.user.employee_name or assignee.user.email.split('@')[0],
                        'role': assignee.user.role,
                        'task_count': employee_tasks,
                    })
                    employee_ids_seen.add(assignee.user_id)
        
        return Response({
            'count': len(employees_data),
            'project_id': project_id,
            'project_name': project.name,
            'results': employees_data
        })

    @action(detail=False, methods=['get'], url_path='projects-for-employee')
    def projects_for_employee(self, request):
        """
        Get all projects assigned to a specific employee (for dropdown filtering).
        
        Query Parameters:
        - employee_id: Required. The employee to get projects for
        
        Returns:
        - List of projects assigned to the employee with task counts
        """
        employee_id = request.query_params.get('employee_id')
        
        if not employee_id:
            return Response(
                {'error': 'employee_id query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            employee = User.objects.get(id=employee_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Employee not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get unique projects where employee has assigned tasks
        projects_data = []
        project_ids_seen = set()
        
        for task_assignee in TaskAssignee.objects.filter(user=employee):
            task = task_assignee.task
            project = task.project
            
            if project.id not in project_ids_seen and project.status == 'ACTIVE':
                # Count tasks for this employee in this project
                employee_tasks = Task.objects.filter(
                    project=project,
                    assignees__user=employee
                ).count()
                
                projects_data.append({
                    'id': project.id,
                    'name': project.name,
                    'status': project.status,
                    'start_date': project.start_date,
                    'due_date': project.due_date,
                    'task_count': employee_tasks,
                    'project_lead': project.project_lead.email if project.project_lead else None,
                })
                project_ids_seen.add(project.id)
        
        return Response({
            'count': len(projects_data),
            'employee_id': employee_id,
            'employee_email': employee.email,
            'results': projects_data
        })
