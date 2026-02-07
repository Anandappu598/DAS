from django.shortcuts import render
from rest_framework import generics, status, viewsets, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import (LoginSerializers, SignupWithOTPSerializer, VerifySignupOTPSerializer,
                          ForgotPasswordSerializer, ResetPasswordSerializer, ProjectSerializer, ApprovalRequestSerializer,
                          ApprovalResponseSerializer, TaskSerializer, TaskAssigneeSerializer, SubTaskSerializer, QuickNoteSerializer,
                          CatalogSerializer, TodayPlanSerializer, ActivityLogSerializer, 
                          PendingSerializer, DaySessionSerializer)
from .utils import (create_otp_record, send_password_reset_confirmation, send_password_reset_otp, 
                    send_signup_otp_to_admin, send_account_approval_email, verify_otp)
from .models import (User, Projects, ApprovalRequest, ApprovalResponse, Task, TaskAssignee, SubTask, QuickNote, 
                     Catalog, TodayPlan, ActivityLog, Pending, DaySession)
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .permissions import IsAdmin, IsEmployee, IsManager, IsTeamLead
from django.db import models
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
