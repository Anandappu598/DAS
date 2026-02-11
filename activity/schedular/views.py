from django.shortcuts import render
from rest_framework import generics, status, viewsets, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import (LoginSerializers, SignupWithOTPSerializer, VerifySignupOTPSerializer,
                          ForgotPasswordSerializer, ResetPasswordSerializer, ProjectSerializer, ApprovalRequestSerializer,
                          ApprovalResponseSerializer, TaskSerializer, TaskAssigneeSerializer, SubTaskSerializer, QuickNoteSerializer,
                          CatalogSerializer, TodayPlanSerializer, ActivityLogSerializer, 
                          PendingSerializer, DaySessionSerializer, TeamInstructionSerializer, UserSerializer, UserPreferenceSerializer, NotificationSerializer)
from .utils import (create_otp_record, send_password_reset_confirmation, send_password_reset_otp, 
                    send_signup_otp_to_admin, send_account_approval_email, verify_otp)
from .models import (User, Projects, ApprovalRequest, ApprovalResponse, Task, TaskAssignee, SubTask, QuickNote, 
                     Catalog, TodayPlan, ActivityLog, Pending, DaySession, TeamInstruction, Notification)
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .permissions import IsAdmin, IsEmployee, IsManager, IsTeamLead
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, timedelta

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
            user = User.objects.get(pk=pk)
            return Response({
                'id': user.id,
                'name': user.email.split('@')[0].replace('.', ' ').title(),
                'email': user.email,
                'role': user.role,
                'role_display': user.get_role_display(),
                'department': user.department.name if user.department else None,
                'department_id': user.department.id if user.department else None,
                'phone_number': user.phone_number or '',
                'is_active': user.is_active
            })
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


class ProjectViewSet(viewsets.ModelViewSet):
      permission_classes = [IsAuthenticated]
      serializer_class = ProjectSerializer
      queryset = Projects.objects.all()
      filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
      filterset_fields = ['status', 'handled_by', 'created_by', 'project_lead']
      search_fields = ['name', 'description']
      ordering_fields = ['start_date', 'due_date', 'created_date', 'name']
      
      def perform_create(self, serializer):
          """Override create to add approval logic"""
          user = self.request.user
          project = serializer.save(created_by=user)
          
          # If ADMIN, auto-approve the project
          if user.role == 'ADMIN':
              project.is_approved = True
              project.save()
          else:
              # For non-admin users (EMPLOYEE, MANAGER, TEAMLEAD), require approval
              project.is_approved = False
              project.save()
              ApprovalRequest.objects.create(
                  reference_type='PROJECT',
                  reference_id=project.id,
                  approval_type='CREATION',
                  requested_by=user,
                  request_data=serializer.data
              )
      
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
          if user.role not in ['ADMIN', 'MANAGER', 'TEAMLEAD'] and user != project.created_by:
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
          
          # Check if there's already a pending completion request
          existing_request = ApprovalRequest.objects.filter(
              reference_type='PROJECT',
              reference_id=project.id,
              approval_type='COMPLETION',
              status='PENDING'
          ).first()
          
          if existing_request:
              return Response(
                  {"error": "There is already a pending completion request for this project"},
                  status=status.HTTP_400_BAD_REQUEST
              )
          
          # Set completed date
          completion_date = request.data.get('completed_date', timezone.now().date())
          project.completed_date = completion_date
          project.save()
          
          # If user is ADMIN, approve immediately
          if user.role == 'ADMIN':
              project.status = 'COMPLETED'
              project.save()
              return Response({
                  "message": "Project marked as completed (auto-approved for admin)",
                  "project": ProjectSerializer(project).data
              })
          
          # Otherwise, create approval request
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
                        project.completed_date = timezone.now().date()
                        project.save()
                    # If rejected, project stays in current status
                    
            except Projects.DoesNotExist:
                pass
        
        elif approval_request.reference_type == 'TASK':
            try:
                task = Task.objects.get(id=approval_request.reference_id)
                
                if approval_request.approval_type == 'CREATION':
                    if action == 'APPROVED':
                        # Task is already created, just mark it as approved if needed
                        # Could add an is_approved field to Task model if needed
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
                    # If rejected, task stays in current status
                    
            except Task.DoesNotExist:
                pass
        
        return Response({
            "message": f"Approval request {action.lower()} successfully",
            "response": ApprovalResponseSerializer(response).data
        }, status=status.HTTP_201_CREATED)
    
class TaskViewSet(viewsets.ModelViewSet):
    """ViewSet for managing tasks"""
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer
    queryset = Task.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['priority', 'status', 'project', 'due_date', 'start_date']
    search_fields = ['title', 'project__name']
    ordering_fields = ['created_at', 'due_date', 'start_date', 'priority']
    
    def get_queryset(self):
        """Filter tasks based on user permissions"""
        user = self.request.user
        if user.role == 'ADMIN':
            return Task.objects.all()
        else:
            from django.db import models
            # Return tasks assigned to the user or created for their projects
            return Task.objects.filter(
                models.Q(assignees__user=user) | 
                models.Q(project__created_by=user)
            ).distinct()
    
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
        
        # Check if user has permission to request completion
        is_assigned = TaskAssignee.objects.filter(task=task, user=user).exists()
        is_project_owner = task.project.created_by == user
        
        if user.role not in ['ADMIN', 'MANAGER', 'TEAMLEAD'] and not is_assigned and not is_project_owner:
            return Response(
                {"error": "You don't have permission to request completion for this task"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if task is already completed
        if task.status == 'DONE':
            return Response(
                {"error": "Task is already completed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if there's already a pending completion request
        existing_request = ApprovalRequest.objects.filter(
            reference_type='TASK',
            reference_id=task.id,
            approval_type='COMPLETION',
            status='PENDING'
        ).first()
        
        if existing_request:
            return Response(
                {"error": "There is already a pending completion request for this task"},
                status=status.HTTP_400_BAD_REQUEST
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
        
        # Otherwise, create approval request
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
        
class SubTaskViewSet(viewsets.ModelViewSet):
    """ViewSet for managing subtasks"""
    permission_classes = [IsAuthenticated]
    serializer_class = SubTaskSerializer
    queryset = SubTask.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['task', 'status', 'due_date']
    search_fields = ['title', 'task__title']
    ordering_fields = ['created_at', 'due_date']
    
    def get_queryset(self):
        """Filter subtasks based on user permissions"""
        user = self.request.user
        if user.role == 'ADMIN':
            return SubTask.objects.all()
        else:
            from django.db import models
            # Return subtasks for tasks assigned to the user or created for their projects
            return SubTask.objects.filter(
                models.Q(task__assignees__user=user) | 
                models.Q(task__project__created_by=user)
            ).distinct()
    
    @action(detail=True, methods=['patch'])
    def toggle_completion(self, request, pk=None):
        """Toggle subtask completion status (for checkbox functionality)"""
        subtask = self.get_object()
        
        # Toggle between DONE and PENDING
        if subtask.status == 'DONE':
            subtask.status = 'PENDING'
            subtask.completed_at = None
        else:
            subtask.status = 'DONE'
            from django.utils import timezone
            subtask.completed_at = timezone.now().date()
        
        subtask.save()
        
        # Return updated subtask data along with parent task's new progress
        serializer = SubTaskSerializer(subtask)
        return Response({
            'subtask': serializer.data,
            'parent_task_progress': subtask.task.calculate_progress()
        })

class QuickNoteViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = QuickNoteSerializer
    queryset = QuickNote.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user']
    search_fields = ['note_text', 'user__email']
    ordering_fields = ['created_at']
    
    def get_queryset(self):
        """Each user can only view their own quick notes"""
        return QuickNote.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Automatically set the user to the current user"""
        serializer.save(user=self.request.user)

class PendingViewSet(viewsets.ModelViewSet):
    """ViewSet for managing pending tasks"""
    permission_classes = [IsAuthenticated]
    serializer_class = PendingSerializer
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
        """Get current user's pending tasks"""
        pending = self.get_queryset().filter(user=request.user, status='PENDING')
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
    permission_classes = [IsAuthenticated]
    serializer_class = CatalogSerializer
    queryset = Catalog.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['catalog_type', 'user', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    
    def get_queryset(self):
        """Filter catalog based on user permissions"""
        user = self.request.user
        if user.role == 'ADMIN':
            return Catalog.objects.all()
        return Catalog.objects.filter(models.Q(user=user) | models.Q(is_active=True))
    
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
    permission_classes = [IsAuthenticated]
    serializer_class = TodayPlanSerializer
    queryset = TodayPlan.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['plan_date', 'status', 'catalog_item__catalog_type']
    search_fields = ['catalog_item__name', 'notes']
    ordering_fields = ['plan_date', 'order_index', 'scheduled_start_time']
    
    def get_queryset(self):
        """Filter today's plan based on user permissions"""
        user = self.request.user
        if user.role == 'ADMIN':
            return TodayPlan.objects.all()
        elif user.role in ['MANAGER', 'TEAMLEAD']:
            return TodayPlan.objects.filter(
                models.Q(user=user) | 
                models.Q(user__department=user.department)
            ).distinct()
        else:
            return TodayPlan.objects.filter(user=user)
    
    def perform_create(self, serializer):
        """Set the user field to current user when creating"""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's plan for current user"""
        today = timezone.now().date()
        plans = TodayPlan.objects.filter(user=request.user, plan_date=today).order_by('order_index')
        serializer = self.get_serializer(plans, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add_from_catalog(self, request):
        """Drag and drop item from catalog to today's plan"""
        catalog_id = request.data.get('catalog_id')
        plan_date = request.data.get('plan_date', timezone.now().date())
        scheduled_start_time = request.data.get('scheduled_start_time')
        scheduled_end_time = request.data.get('scheduled_end_time')
        planned_duration_minutes = request.data.get('planned_duration_minutes')
        
        if not all([catalog_id, scheduled_start_time, scheduled_end_time]):
            return Response(
                {"error": "catalog_id, scheduled_start_time, and scheduled_end_time are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            catalog_item = Catalog.objects.get(id=catalog_id)
        except Catalog.DoesNotExist:
            return Response({"error": "Catalog item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Calculate order_index
        last_plan = TodayPlan.objects.filter(user=request.user, plan_date=plan_date).order_by('-order_index').first()
        order_index = (last_plan.order_index + 1) if last_plan else 0
        
        # Calculate duration if not provided
        if not planned_duration_minutes:
            start = datetime.strptime(scheduled_start_time, '%H:%M:%S').time()
            end = datetime.strptime(scheduled_end_time, '%H:%M:%S').time()
            start_dt = datetime.combine(timezone.now().date(), start)
            end_dt = datetime.combine(timezone.now().date(), end)
            planned_duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
        
        today_plan = TodayPlan.objects.create(
            user=request.user,
            catalog_item=catalog_item,
            plan_date=plan_date,
            scheduled_start_time=scheduled_start_time,
            scheduled_end_time=scheduled_end_time,
            planned_duration_minutes=planned_duration_minutes,
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
        today_plan = self.get_object()
        
        # Check if there's already an active activity log
        active_log = ActivityLog.objects.filter(
            user=request.user, 
            status='IN_PROGRESS'
        ).first()
        
        if active_log:
            return Response(
                {"error": "You already have an active task in progress. Please stop it first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create activity log
        activity_log = ActivityLog.objects.create(
            today_plan=today_plan,
            user=request.user
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
        
        # Get start of week (Monday)
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        plans = TodayPlan.objects.filter(
            user=request.user,
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
        
        today = timezone.now().date()
        year = int(request.query_params.get('year', today.year))
        month = int(request.query_params.get('month', today.month))
        
        # Get first and last day of month
        first_day = datetime(year, month, 1).date()
        last_day_num = monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num).date()
        
        plans = TodayPlan.objects.filter(
            user=request.user,
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
    queryset = ActivityLog.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'is_task_completed']
    search_fields = ['work_notes', 'today_plan__catalog_item__name']
    ordering_fields = ['created_at', 'actual_start_time', 'hours_worked']
    
    def get_queryset(self):
        """Filter activity logs based on user permissions"""
        user = self.request.user
        if user.role == 'ADMIN':
            return ActivityLog.objects.all()
        elif user.role in ['MANAGER', 'TEAMLEAD']:
            return ActivityLog.objects.filter(
                models.Q(user=user) | 
                models.Q(user__department=user.department)
            ).distinct()
        else:
            return ActivityLog.objects.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get currently active activity log"""
        active_log = ActivityLog.objects.filter(user=request.user, status='IN_PROGRESS').first()
        if not active_log:
            return Response({"message": "No active task"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(active_log)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Stop the activity log (click stop button)"""
        activity_log = self.get_object()
        
        if activity_log.status != 'IN_PROGRESS':
            return Response(
                {"error": "This activity is not in progress"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        is_completed = request.data.get('is_completed', False)
        work_notes = request.data.get('work_notes', '')
        minutes_left = request.data.get('minutes_left', 0)
        
        # Update activity log
        activity_log.actual_end_time = timezone.now()
        activity_log.work_notes = work_notes
        activity_log.is_task_completed = is_completed
        activity_log.status = 'COMPLETED' if is_completed else 'STOPPED'
        activity_log.calculate_time_worked()
        
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
        logs = ActivityLog.objects.filter(user=request.user).order_by('-created_at')
        
        # Optional date filtering
        date = request.query_params.get('date')
        if date:
            logs = logs.filter(actual_start_time__date=date)
        
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
        """Get list of members for a specific project"""
        project_id = request.query_params.get('project_id')
        
        if not project_id:
            return Response(
                {"error": "project_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            project = Projects.objects.get(id=project_id)
        except Projects.DoesNotExist:
            return Response(
                {"error": "Project not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get all users assigned to tasks in this project
        from django.db.models import Q
        project_members = User.objects.filter(
            Q(assigned_tasks__task__project=project) |
            Q(created_projects=project) |
            Q(id=project.project_lead_id) |
            Q(id=project.handled_by_id)
        ).distinct()
        
        members_data = [
            {
                "id": user.id,
                "email": user.email,
                "role": user.role
            }
            for user in project_members
        ]
        
        return Response({
            "project_id": project.id,
            "project_name": project.name,
            "members": members_data
        })


class DashboardViewSet(viewsets.GenericViewSet):
    """ViewSet for admin dashboard APIs"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get dashboard statistics for cards"""
        user = request.user
        
        # PROJECT PORTFOLIO
        if user.role == 'ADMIN':
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
    
    @action(detail=False, methods=['get'])
    def team_activity_status(self, request):
        """Get team activity status - daily capacity tracking"""
        user = request.user
        today = timezone.now().date()
        daily_capacity_hours = 9  # Target: 9 hours per day
        
        # Get all users in the team
        if user.role == 'ADMIN':
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
    
    @action(detail=False, methods=['get'])
    def users_for_stats(self, request):
        """Get list of users for project work stats dropdown"""
        user = request.user
        
        # Get users based on role permissions
        if user.role == 'ADMIN':
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
                'name': u.email.split('@')[0].replace('.', ' ').title(),
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
    
    @action(detail=False, methods=['get'])
    def project_work_stats(self, request):
        """Get project work stats - completion percentage by projects handled by user"""
        user = request.user
        target_user_id = request.query_params.get('user_id', user.id)
        
        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Permission check - all roles can view their own stats, 
        # ADMIN/MANAGER/TEAMLEAD can view others based on department
        if target_user.id != user.id:
            if user.role == 'ADMIN':
                # Admin can view anyone
                pass
            elif user.role in ['MANAGER', 'TEAMLEAD']:
                # Manager/TeamLead can only view members from their department
                if target_user.department != user.department:
                    return Response(
                        {'error': 'You can only view members from your department'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                # Employees can only view their own stats
                return Response(
                    {'error': 'You do not have permission to view other users statistics'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Get all projects handled by the target user
        projects = Projects.objects.filter(handled_by=target_user).prefetch_related('tasks')
        
        if projects.count() == 0:
            return Response({
                'user': {
                    'id': target_user.id,
                    'email': target_user.email,
                    'name': target_user.email.split('@')[0].replace('.', ' ').title(),
                    'role': target_user.role,
                    'department': target_user.department.name if target_user.department else None
                },
                'total_percentage': 100,
                'message': 'No projects handled by this user.',
                'projects': []
            })
        
        # Calculate statistics for each project
        project_data = []
        total_tasks_all_projects = 0
        total_completed_tasks_all_projects = 0
        
        for project in projects:
            # Get all tasks for this project
            project_tasks = project.tasks.all()
            total_tasks = project_tasks.count()
            
            if total_tasks > 0:
                # Count completed tasks
                completed_tasks = project_tasks.filter(status='DONE').count()
                
                # Calculate completion percentage
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
                    'working_hours': project.working_hours
                })
        
        # Calculate overall completion percentage
        overall_percentage = 100
        if total_tasks_all_projects > 0:
            overall_percentage = round((total_completed_tasks_all_projects / total_tasks_all_projects) * 100)
        
        return Response({
            'user': {
                'id': target_user.id,
                'email': target_user.email,
                'name': target_user.email.split('@')[0].replace('.', ' ').title(),
                'role': target_user.role,
                'department': target_user.department.name if target_user.department else None
            },
            'overall_completion_percentage': overall_percentage,
            'total_projects': projects.count(),
            'total_tasks': total_tasks_all_projects,
            'completed_tasks': total_completed_tasks_all_projects,
            'pending_tasks': total_tasks_all_projects - total_completed_tasks_all_projects,
            'projects': project_data
        })


class TeamOverviewViewSet(viewsets.GenericViewSet):
    """ViewSet for team overview and monitoring"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def team_members(self, request):
        """Get all team members with their statistics"""
        user = request.user
        today = timezone.now().date()
        
        # Get team members based on role
        if user.role == 'ADMIN':
            team_members = User.objects.filter(is_active=True).exclude(id=user.id)
        elif user.role in ['MANAGER', 'TEAMLEAD']:
            team_members = User.objects.filter(
                department=user.department,
                is_active=True
            ).exclude(id=user.id)
        else:
            # Regular employees can only see themselves
            team_members = User.objects.filter(id=user.id)
        
        members_data = []
        
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
            
            members_data.append({
                'id': member.id,
                'email': member.email,
                'name': member.email.split('@')[0].replace('.', ' ').title(),  # Simple name extraction
                'role': member.role,
                'department': department_name,
                'active_tasks': active_tasks,
                'completed_tasks': completed_tasks,
                'workload_intensity': workload_intensity,
                'current_focus': current_focus,
                'phone_number': member.phone_number or ''
            })
        
        return Response({
            'count': len(members_data),
            'members': members_data
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


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing notifications"""
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
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
