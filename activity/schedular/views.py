from django.shortcuts import render
from rest_framework import generics, status, viewsets, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import (LoginSerializers, PendingSerializer, SignupWithOTPSerializer, VerifySignupOTPSerializer,
                          ForgotPasswordSerializer,ResetPasswordSerializer,ProjectSerializer,ApprovalRequestSerializer,
                          ApprovalResponseSerializer,TaskSerializer,TaskAssigneeSerializer,SubTaskSerializer,QuickNoteSerializer,
                          CatalogSerializer,PendingSerializer,DailyActivitySerializer)
from .utils import (create_otp_record, send_password_reset_confirmation, send_password_reset_otp, send_signup_otp_to_admin,send_account_approval_email, verify_otp,
    send_password_reset_otp, send_password_reset_confirmation, verify_otp)
from .models import (User,Projects,ApprovalRequest,ApprovalResponse,Task,TaskAssignee,SubTask,QuickNote,Catalog,Pending,
Catalog,DailyActivity)
from .utils import (create_otp_record, send_password_reset_confirmation, send_password_reset_otp, 
                    send_signup_otp_to_admin, send_account_approval_email, verify_otp)
from .models import User,Projects,ApprovalRequest,ApprovalResponse,Task,TaskAssignee,SubTask,QuickNote,Catalog,DailyActivity
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .permissions import IsAdmin,IsEmployee,IsManager,IsTeamLead
from django.db import models

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
            "email": user.email
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
        
        # Update related project if needed
        action = response.action
        if approval_request.reference_type == 'PROJECT':
            try:
                project = Projects.objects.get(id=approval_request.reference_id)
                if action == 'APPROVED':
                    project.is_approved = True
                    project.save()
                elif action == 'REJECTED' and approval_request.approval_type == 'CREATION':
                    # Optionally delete rejected project creations
                    project.delete()
            except Projects.DoesNotExist:
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

class QuickNoteViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = QuickNoteSerializer
    queryset = QuickNote.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user']
    search_fields = ['note_text', 'user__email']
    ordering_fields = ['created_at']
    def get_queryset(self):
        """Filter quick notes based on user permissions"""
        user = self.request.user
        if user.role == 'ADMIN':
            return QuickNote.objects.all()
        else:
            # Return quick notes created by the user
            return QuickNote.objects.filter(user=user)
        
    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [IsAdmin]
        return [permission() for permission in self.permission_classes]
        
class CatalogViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CatalogSerializer
    queryset = Catalog.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['course', 'routine']
    search_fields = ['course', 'routine']
    ordering_fields = ['created_at']

class PendingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PendingSerializer
    queryset = Pending.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user_id', 'Daily_task_id', 'status']
    search_fields = ['user_id__email', 'Daily_task_id__title']
    ordering_fields = ['original_plan_date', 'Replanned_date']
    filterset_fields = ['catalog_type', 'instructors']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at']

class DailyActivityViewSet(viewsets.ModelViewSet):
    """ViewSet for managing daily activities"""
    permission_classes = [IsAuthenticated]
    serializer_class = DailyActivitySerializer
    queryset = DailyActivity.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'project', 'task', 'status', 'work_date']
    search_fields = ['title', 'description', 'remarks', 'user__email', 'project__name', 'task__title']
    ordering_fields = ['created_at', 'work_date', 'planned_hours', 'spending_hours']
    
    def get_queryset(self):
        """Filter daily activities based on user permissions"""
        user = self.request.user
        if user.role == 'ADMIN':
            return DailyActivity.objects.all()
        elif user.role in ['MANAGER', 'TEAMLEAD']:
            # Managers and Team Leads can see activities from their department or projects they lead
            from django.db import models
            return DailyActivity.objects.filter(
                models.Q(user=user) | 
                models.Q(user__department=user.department) |
                models.Q(project__project_lead=user)
            ).distinct()
        else:
            # Employees can only see their own activities
            return DailyActivity.objects.filter(user=user)
    
    def perform_create(self, serializer):
        """Set the user field to current user when creating"""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'], url_path='my-activities')
    def my_activities(self, request):
        """Get all activities for the current user"""
        activities = DailyActivity.objects.filter(user=request.user)
        serializer = self.get_serializer(activities, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='by-date')
    def by_date(self, request):
        """Get activities filtered by date range"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {"error": "Both start_date and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        activities = self.get_queryset().filter(
            work_date__gte=start_date,
            work_date__lte=end_date
        )
        serializer = self.get_serializer(activities, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='by-project/(?P<project_id>[^/.]+)')
    def by_project(self, request, project_id=None):
        """Get all activities for a specific project"""
        activities = self.get_queryset().filter(project_id=project_id)
        serializer = self.get_serializer(activities, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='by-task/(?P<task_id>[^/.]+)')
    def by_task(self, request, task_id=None):
        """Get all activities for a specific task"""
        activities = self.get_queryset().filter(task_id=task_id)
        serializer = self.get_serializer(activities, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get statistics about daily activities"""
        from django.db.models import Sum, Avg, Count
        
        activities = self.get_queryset()
        stats = activities.aggregate(
            total_activities=Count('id'),
            total_planned_hours=Sum('planned_hours'),
            total_spending_hours=Sum('spending_hours'),
            avg_planned_hours=Avg('planned_hours'),
            avg_spending_hours=Avg('spending_hours'),
            pending_count=Count('id', filter=models.Q(status='PENDING')),
            in_progress_count=Count('id', filter=models.Q(status='IN_PROGRESS')),
            completed_count=Count('id', filter=models.Q(status='COMPLETED'))
        )
        
        return Response(stats)
