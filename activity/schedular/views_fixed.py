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
                          PendingSerializer, DaySessionSerializer, TeamInstructionSerializer, UserSerializer, UserPreferenceSerializer, NotificationSerializer)
from .utils import (create_otp_record, send_password_reset_confirmation, send_password_reset_otp, 
                    send_signup_otp_to_admin, send_account_approval_email, verify_otp)
from .models import (User, Projects, ApprovalRequest, ApprovalResponse, Task, TaskAssignee, SubTask, StickyNote, 
                     Catalog, TodayPlan, ActivityLog, Pending, DaySession, TeamInstruction, Notification, Employee)
from .mixins import ProjectQuerySetMixin, TaskQuerySetMixin
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .permissions import IsAdmin, IsEmployee, IsManager, IsTeamLead
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, timedelta
import requests
import secrets

# Create your views here.

class LoginViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
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
    permission_classes = [AllowAny]
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
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile and preferences"""
        user = request.user
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
      permission_classes = [IsAuthenticated]
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
                  # WebSocket notification to admins is handled by the
                  # approval_request_notification signal in signals.py automatically

              # Return full project detail
              detail_serializer = ProjectDetailSerializer(project)
              return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
          
          return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
      
      @action(detail=True, methods=['get'], url_path='detail-view')
      def detail_view(self, request, pk=None):
          """Get detailed project information with tasks and subtasks"""
          from .serializers import ProjectDetailSerializer
          project = self.get_object()
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
          from .serializers import TaskCreateSerializer
          project = self.get_object()
          
          serializer = TaskCreateSerializer(data=request.data)
          if serializer.is_valid():
              task = serializer.save(project=project)
              
              user = request.user
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

              from .serializers import TaskDetailSerializer
              response_serializer = TaskDetailSerializer(task)
              return Response(response_serializer.data, status=status.HTTP_201_CREATED)
          
          return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
      
      @action(detail=True, methods=['post'])
      def create_recurring_task(self, request, pk=None):
          """Create a new recurring task for this project"""
          from .serializers import RecurringTaskCreateSerializer
          project = self.get_object()
          
          serializer = RecurringTaskCreateSerializer(data=request.data)
          if serializer.is_valid():
              task = serializer.save(project=project)

              user = request.user
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

              from .serializers import TaskDetailSerializer
              response_serializer = TaskDetailSerializer(task)
              return Response(response_serializer.data, status=status.HTTP_201_CREATED)
          
          return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
      
      @action(detail=True, methods=['post'])
      def create_routine_task(self, request, pk=None):
          """Create a new routine task for this project"""
          from .serializers import RoutineTaskCreateSerializer
          project = self.get_object()
          
          serializer = RoutineTaskCreateSerializer(data=request.data)
          if serializer.is_valid():
              task = serializer.save(project=project)

              user = request.user
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

              from .serializers import TaskDetailSerializer
              response_serializer = TaskDetailSerializer(task)
              return Response(response_serializer.data, status=status.HTTP_201_CREATED)
          
          return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
      
      @action(detail=True, methods=['post'])
      def request_completion(self, request, pk=None):
          """Request approval for project completion"""
          project = self.get_object()
          user = request.user
          
          # Check if user has permission to request completion
          # Allow employees to request completion as well
          if user.role not in ['ADMIN', 'MANAGER', 'TEAMLEAD', 'EMPLOYEE'] and user != project.created_by:
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
          
          # Check if all tasks are completed before allowing project completion
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


class ApprovalRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for users to create and view approval requests"""
    permission_classes = [IsAuthenticated]
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
                    notif_title = 'Project Approved âœ“'
                    notif_message = (
                        f'Your project "{item_name}" has been approved and is now live. '
                        f'You can start working on it!'
                    )
                elif approval.approval_type == 'COMPLETION':
                    project.status = 'COMPLETED'
                    project.approval_status = 'APPROVED'
                    project.completed_date = timezone.now().date()
                    project.save()
                    notif_title = 'Project Closed âœ“'
                    notif_message = (
                        f'Admin has confirmed closure of project "{item_name}". '
                        f'The project is now marked as Completed.'
                    )

            elif approval.reference_type == 'TASK':
                task = Task.objects.get(id=approval.reference_id)
                item_name = task.title
                if approval.approval_type == 'CREATION':
                    # Task creation approved
                    if task.status == 'PENDING_APPROVAL':
                        task.status = 'PENDING'
                        task.approval_status = 'APPROVED'
                        task.save()
                    notif_title = 'Task Approved âœ“'
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
                    notif_title = 'Task Completed âœ“'
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
                    project.save()
                    
                    # Also reset all project tasks and milestones
                    tasks = project.tasks.all()
                    tasks.update(status='IN_PROGRESS', approval_status='REJECTED', completed_at=None)
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
                    if task.status == 'PENDING_APPROVAL':
                        task.status = 'IN_PROGRESS'
                        task.approval_status = 'REJECTED'
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


class ApprovalResponseViewSet(viewsets.ModelViewSet):
    """ViewSet for admin to approve/reject requests"""
    permission_classes = [IsAuthenticated]
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
                        # Reset all tasks so they can be worked on again
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
                        # Task is already created, just mark it as approved if needed
                        pass
                    elif action == 'REJECTED':
                        # Delete rejected task creations
                        task.delete()
                        
                elif approval_request.approval_type == 'COMPLETION':
                    if action == 'APPROVED':
                        task.status = 'DONE'
                        task.completed_at = timezone.now().date()
                        task.save()
                        
                        # Handle recurring task regeneration
                        if task.task_type == 'RECURRING':
                            task.regenerate_recurring_task()
                    elif action == 'REJECTED':
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
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer
    pagination_class = None
    queryset = Task.objects.all() # Base default
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['priority', 'status', 'project', 'due_date', 'start_date']
    search_fields = ['title', 'project__name']
    ordering_fields = ['created_at', 'due_date', 'start_date', 'priority']
    
    # get_queryset is now handled by the Mixin

    
    def perform_create(self, serializer):
        """Override create to add approval logic for tasks"""
        user = self.request.user
        task = serializer.save()
        
        # If ADMIN, auto-approve the task
        if user.role == 'ADMIN':
            # Task is auto-approved, no approval request needed
            pass
        else:
            # For EMPLOYEE, MANAGER, and TEAMLEAD, require approval
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
        
        # Object-level permissions are already handled by get_queryset() (TaskQuerySetMixin)
        # Any user who can view this task is part of its project and authorized to request completion.
        
        # Check if task is already completed
        if task.status == 'DONE':
            return Response(
                {"message": "Task is already completed"},
                status=status.HTTP_200_OK
            )
        
        # Check if there's already a pending completion request
        existing_request = ApprovalRequest.objects.filter(
            reference_type='TASK',
            reference_id=task.id,
            approval_type='COMPLETION',
            status='PENDING'
        ).first()
        
        # If user is ADMIN and there's already a pending request, cancel it and auto-approve
        if user.role == 'ADMIN' and existing_request:
            existing_request.status = 'APPROVED'
            existing_request.approved_by = user
            existing_request.approved_at = timezone.now()
            existing_request.save()
            
            task.status = 'DONE'
            completion_date = request.data.get('completed_date', timezone.now().date())
            task.completed_at = completion_date
            task.save()
            
            # Handle recurring task regeneration
            if task.task_type == 'RECURRING':
                new_task = task.regenerate_recurring_task()
                if new_task:
                    return Response({
                        "message": "Task marked as completed and regenerated (auto-approved for admin)",
                        "task": TaskSerializer(task).data,
                        "new_recurring_task": TaskSerializer(new_task).data
                    })
            
            return Response({
                "message": "Task marked as completed (auto-approved for admin)",
                "task": TaskSerializer(task).data
            })
        
        if existing_request:
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
            task.save()
            
            # Handle recurring task regeneration
            if task.task_type == 'RECURRING':
                new_task = task.regenerate_recurring_task()
                if new_task:
                    return Response({
                        "message": "Task marked as completed and regenerated (auto-approved for admin)",
                        "task": TaskSerializer(task).data,
                        "new_recurring_task": TaskSerializer(new_task).data
                    })
            
            return Response({
                "message": "Task marked as completed (auto-approved for admin)",
                "task": TaskSerializer(task).data
            })
        
        # For non-admin: set status to PENDING_APPROVAL so UI reflects correctly
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


class TaskAssigneeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing task assignments"""
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectSerializer
    queryset = Projects.objects.all()
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'handled_by', 'created_by', 'project_lead']
    search_fields = ['name', 'description']
    ordering_fields = ['start_date', 'due_date', 'create_date', 'name']
    ordering = ['-create_date']

    def get_queryset(self):
        """Always filter to projects where user is assigned - regardless of role"""
        user = self.request.user
        
        # Check if user is active
        if not user.is_active:
            return Projects.objects.none()
        
        # For ALL users (including ADMIN), show only assigned projects
        # User is considered assigned if they are assigned to any task in the project
        queryset = Projects.objects.filter(
            models.Q(tasks__assignees__user=user)
        ).distinct()
        
        return queryset
    
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
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer
    pagination_class = None
    queryset = Task.objects.all()
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['priority', 'status', 'project', 'due_date', 'start_date']
    search_fields = ['title', 'project__name']
    ordering_fields = ['created_at', 'due_date', 'start_date', 'priority']
    
    def get_queryset(self):
        """Always filter to tasks where user is assigned - regardless of role"""
        user = self.request.user
        
        # Check if user is active
        if not user.is_active:
            return Task.objects.none()
        
        # For ALL users (including ADMIN), show only assigned tasks
        queryset = Task.objects.filter(
            models.Q(assignees__user=user)
        ).distinct()
        
        return queryset


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
        
        # One-way: once DONE, cannot be unchecked
        if subtask.status == 'DONE':
            return Response(
                {"error": "Completed milestones cannot be unchecked."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        subtask.status = 'DONE'
        from django.utils import timezone
        subtask.completed_at = timezone.now().date()
        
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
    permission_classes = [IsAuthenticated]
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
        if user.role == 'ADMIN':
            return Pending.objects.all()
        elif user.role in ['MANAGER', 'TEAMLEAD']:
            return Pending.objects.filter(
                models.Q(user=user) | 
                models.Q(user__department=user.department)
            ).distinct()
        else:
            return Pending.objects.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def my_pending(self, request):
        """Get current user's pending tasks, optionally filtered by date"""
        date_param = request.query_params.get('date')
        
        pending = self.get_queryset().filter(user=request.user, status='PENDING')
        
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
        """Filter catalog based on user permissions and task assignments"""
        user = self.request.user
        # Handle anonymous users (when authentication is bypassed)
        if not user.is_authenticated:
            return Catalog.objects.filter(is_active=True)
        
        # All users (including ADMIN) only see catalog items assigned to them
        # 1. Catalog items they created (courses, routines, custom)
        # 2. Tasks assigned to them
        # 3. Projects where they have at least one assigned task
        return Catalog.objects.filter(
            models.Q(user=user) |  # Catalog items created by the user
            models.Q(task__assignees__user=user) |  # Tasks assigned to the user
            models.Q(project__tasks__assignees__user=user)  # Projects where they have assigned tasks
        ).distinct()
    
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

        # Handle anonymous users (when authentication is bypassed)
        if user.is_authenticated:
            if user.role == 'ADMIN':
                # Admin can optionally filter by a specific user
                target_user_id = self.request.query_params.get('user_id')
                if target_user_id:
                    queryset = queryset.filter(user__id=target_user_id)
                # else: admin sees all plans (no filter)
            elif user.role in ['MANAGER', 'TEAMLEAD']:
                queryset = queryset.filter(
                    models.Q(user=user) | 
                    models.Q(user__department=user.department)
                ).distinct()
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
        else:
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
            notes=notes
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
        else:
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
            notes=request.data.get('notes', '')
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
        
        # Get user (handle anonymous)
        user = request.user if request.user.is_authenticated else today_plan.user
        
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
    permission_classes = [IsAuthenticated]
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
        
        if user.role == 'ADMIN':
            queryset = ActivityLog.objects.all()
        elif user.role in ['MANAGER', 'TEAMLEAD']:
            queryset = ActivityLog.objects.filter(
                models.Q(user=user) | 
                models.Q(user__department=user.department)
            ).distinct()
        else:
            queryset = ActivityLog.objects.filter(user=user)
            
        # Date filtering
        date_param = self.request.query_params.get('date')
        if date_param:
            queryset = queryset.filter(actual_start_time__date=date_param)
            
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
                    # Use existing start date if available, otherwise use today
                    # This preserves the date for tasks that started yesterday
                    base_date = activity_log.actual_start_time.date() if activity_log.actual_start_time else today_kolkata
                    
                    # Create timezone-aware datetime using replace
                    naive_dt = datetime.combine(base_date, start_time_obj)
                    activity_log.actual_start_time = naive_dt.replace(tzinfo=kolkata_tz)
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
                    # Create timezone-aware datetime using replace
                    naive_dt = datetime.combine(today_kolkata, end_time_obj)
                    activity_log.actual_end_time = naive_dt.replace(tzinfo=kolkata_tz)
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
            # If date specified, get logs for that date PLUS any IN_PROGRESS logs (regardless of date)
            logs = ActivityLog.objects.filter(
                models.Q(user=request.user, actual_start_time__date=date) |
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
    permission_classes = [IsAuthenticated]
    serializer_class = DaySessionSerializer
    pagination_class = None
    queryset = DaySession.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['session_date', 'is_active']
    ordering_fields = ['session_date', 'started_at']
    
    def get_queryset(self):
        """Filter day sessions based on user"""
        user = self.request.user
        if user.role == 'ADMIN':
            return DaySession.objects.all()
        return DaySession.objects.filter(user=user)
    
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
    permission_classes = [IsAuthenticated]
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
        if user.role == 'ADMIN':
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
        if user.role == 'ADMIN':
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
        elif user.role in ['MANAGER', 'TEAMLEAD']:
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
        
        # Handle unauthenticated users - return all active users for testing
        if not user or not user.is_authenticated:
            users = User.objects.filter(is_active=True)
        elif user.role == 'ADMIN':
            # Admin can see all active users
            users = User.objects.filter(is_active=True)
        elif user.role in ['MANAGER', 'TEAMLEAD']:
            # Manager/TeamLead can see users from their department
            users = User.objects.filter(
                department=user.department,
                is_active=True
            )
        else:
            # Regular employees can only see themselves
            users = User.objects.filter(id=user.id, is_active=True)
        
        user_list = []
        for u in users:
            # Count projects handled by each user
            projects_count = Projects.objects.filter(handled_by=u).count()
            
            user_list.append({
                'id': u.id,
                'email': u.email,
                'name': u.employee_name if u.employee_name else u.email.split('@')[0].replace('.', ' ').title(),
                'role': u.role,
                'role_display': u.get_role_display(),
                'department': u.department.name if u.department else None,
                'projects_count': projects_count
            })
        
        # Sort by name
        user_list.sort(key=lambda x: x['name'])
        
        return Response({
            'count': len(user_list),
            'users': user_list
        })
    
    @action(detail=False, methods=['get'], url_path='project-work-stats')
    def project_work_stats(self, request):
        """Get project work stats - completion percentage by tasks assigned to the user per project"""
        user = request.user
        target_user_id = request.query_params.get('user_id')
        
        # Handle unauthenticated users
        if not user or not user.is_authenticated:
            if not target_user_id:
                return Response({'error': 'user_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            target_user_id = target_user_id or user.id
        
        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Permission check
        if not user or not user.is_authenticated:
            pass  # Allow unauthenticated access for testing
        elif target_user.id != user.id:
            if user.role == 'ADMIN':
                pass
            elif user.role in ['MANAGER', 'TEAMLEAD']:
                if target_user.department != user.department:
                    return Response(
                        {'error': 'You can only view members from your department'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                return Response(
                    {'error': 'You do not have permission to view other users statistics'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Find all projects where the user has at least one assigned task (via TaskAssignee)
        # This is correct: employee contribution = tasks assigned to them, grouped by project
        assigned_task_ids = TaskAssignee.objects.filter(user=target_user).values_list('task_id', flat=True)
        
        if not assigned_task_ids:
            return Response({
                'user': {
                    'id': target_user.id,
                    'name': target_user.name,
                    'email': target_user.email,
                    'role': target_user.role,
                    'department': target_user.department.name if target_user.department else None
                },
                'overall_completion_percentage': 0,
                'total_projects': 0,
                'total_tasks': 0,
                'completed_tasks': 0,
                'pending_tasks': 0,
                'message': 'No tasks assigned to this user.',
                'projects': []
            })
        
        # Get distinct projects that have tasks assigned to this user
        projects = Projects.objects.filter(tasks__id__in=assigned_task_ids).distinct().prefetch_related('tasks')
        
        # Calculate statistics per project (only for assigned tasks)
        project_data = []
        total_tasks_all_projects = 0
        total_completed_tasks_all_projects = 0
        
        for project in projects:
            # Only consider tasks within this project that are assigned to this specific user
            user_task_ids_in_project = TaskAssignee.objects.filter(
                task__project=project,
                user=target_user
            ).values_list('task_id', flat=True)
            
            user_tasks_in_project = Task.objects.filter(id__in=user_task_ids_in_project)
            total_tasks = user_tasks_in_project.count()
            
            if total_tasks == 0:
                continue
            
            # A task is "completed" if its status is DONE
            completed_tasks = user_tasks_in_project.filter(status='DONE').count()
            
            # Also compute milestone (subtask) progress per assigned task
            tasks_detail = []
            for task in user_tasks_in_project:
                subtasks = task.subtasks.all()
                total_subtasks = subtasks.count()
                completed_subtasks = subtasks.filter(status='DONE').count()
                
                # Milestone-weighted progress (if subtasks exist, use them; else use task status)
                if total_subtasks > 0:
                    milestone_progress = round((completed_subtasks / total_subtasks) * 100)
                else:
                    milestone_progress = 100 if task.status == 'DONE' else (50 if task.status == 'IN_PROGRESS' else 0)
                
                tasks_detail.append({
                    'task_id': task.id,
                    'task_title': task.title,
                    'status': task.status,
                    'total_milestones': total_subtasks,
                    'completed_milestones': completed_subtasks,
                    'milestone_progress': milestone_progress,
                })
            
            # Contribution % = proportion of user's assigned tasks that are DONE in this project
            completion_percentage = round((completed_tasks / total_tasks) * 100)
            
            # Accumulate for overall stats
            total_tasks_all_projects += total_tasks
            total_completed_tasks_all_projects += completed_tasks
            
            project_data.append({
                'id': project.id,
                'name': project.name,
                'status': project.status,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'pending_tasks': total_tasks - completed_tasks,
                'completion_percentage': completion_percentage,
                'start_date': project.start_date,
                'due_date': project.due_date,
                'working_hours': project.working_hours,
                'tasks': tasks_detail,
            })
        
        # Sort projects by contribution percentage desc
        project_data.sort(key=lambda x: x['completion_percentage'], reverse=True)
        
        # Calculate overall contribution percentage across all assigned tasks
        overall_percentage = 0
        if total_tasks_all_projects > 0:
            overall_percentage = round((total_completed_tasks_all_projects / total_tasks_all_projects) * 100)
        
        return Response({
            'user': {
                'id': target_user.id,
                'name': target_user.name,
                'email': target_user.email,
                'role': target_user.role,
                'department': target_user.department.name if target_user.department else None
            },
            'overall_completion_percentage': overall_percentage,
            'total_projects': len(project_data),
            'total_tasks': total_tasks_all_projects,
            'completed_tasks': total_completed_tasks_all_projects,
            'pending_tasks': total_tasks_all_projects - total_completed_tasks_all_projects,
            'projects': project_data
        })



class TeamOverviewViewSet(viewsets.GenericViewSet):
    """ViewSet for team overview and monitoring"""
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
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


# â”€â”€â”€ Project Working Hours Report â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ProjectWorkingHoursViewSet(viewsets.GenericViewSet):


# â”€â”€â”€ Team Activity Status â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TeamActivityStatusViewSet(viewsets.GenericViewSet):
    """
    GET /api/team-activity-status/today/
    Query param: date (dd-mm-yyyy), defaults to today. Target: 9h = 540 min.
    """
    permission_classes = [IsAuthenticated]
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


# â”€â”€â”€ HRM Employee Sync ViewSet â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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


# â”€â”€â”€ Planner Catalog ViewSets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# These endpoints are specifically for the Planner Catalog feature
# They ALWAYS return only items assigned to the logged-in user
# This keeps catalog separate from Dashboard (which shows all team items for admin)

class CatalogProjectViewSet(viewsets.ModelViewSet):
    """
    Dedicated endpoint for Planner Catalog - Returns only projects assigned to the logged-in user
    GET /api/catalog-projects/
    
    This is separate from /api/projects/ which is used by Dashboard and shows all team projects to admin.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectSerializer
    queryset = Projects.objects.all()
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'handled_by', 'created_by', 'project_lead']
    search_fields = ['name', 'description']
    ordering_fields = ['start_date', 'due_date', 'create_date', 'name']
    ordering = ['-create_date']
    
    def get_queryset(self):
        """
        Return only projects where the current user is assigned.
        This applies to ALL users including ADMIN.
        """
        user = self.request.user
        
        # Return only projects where user is creator, lead, handled_by, or assigned to any task
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
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer
    pagination_class = None
    queryset = Task.objects.all()
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['priority', 'status', 'project', 'due_date', 'start_date']
    search_fields = ['title', 'project__name']
    ordering_fields = ['created_at', 'due_date', 'start_date', 'priority']
    
    def get_queryset(self):
        """
        Return only tasks where the current user is assigned.
        This applies to ALL users including ADMIN.
        """
        user = self.request.user
        
        # Return only tasks where user is an assignee
        return Task.objects.filter(assignees__user=user).distinct()


