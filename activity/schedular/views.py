from django.shortcuts import render
from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import (LoginSerializers, SignupWithOTPSerializer, VerifySignupOTPSerializer,
                          ForgotPasswordSerializer,ResetPasswordSerializer,ProjectSerializer,ApprovalRequestSerializer,
                          ApprovalResponseSerializer,TaskSerializer,TaskAssigneeSerializer,SubTaskSerializer,QuickNoteSerializer,
                          CourseSerializer,RoutineSerializer)
from .utils import (create_otp_record, send_password_reset_confirmation, send_password_reset_otp, send_signup_otp_to_admin,send_account_approval_email, verify_otp,
    send_password_reset_otp, send_password_reset_confirmation, verify_otp)
from .models import User,Projects,ApprovalRequest,ApprovalResponse,Task,TaskAssignee,SubTask,QuickNote,Course,Routine
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .permissions import IsAdmin,IsEmployee,IsManager,IsTeamLead

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
    def get_queryset(self):
        """Filter quick notes based on user permissions"""
        user = self.request.user
        if user.role == 'ADMIN':
            return QuickNote.objects.all()
        else:
            # Return quick notes created by the user
            return QuickNote.objects.filter(created_by=user)
        
    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [IsAdmin]
        else:
            return[IsAuthenticated()]
        
class CourseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CourseSerializer
    queryset = Course.objects.all()

    def get_queryset(self):
        """Filter courses based on user permissions"""
        user = self.request.user
        if user.role == 'ADMIN':
            return Course.objects.all()
        else:
            # Return courses created by the user
            return Course.objects.filter(created_by=user)

class RoutineViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RoutineSerializer
    queryset = Routine.objects.all()

    def get_queryset(self):

        user = self.request.user
        if user.role == 'ADMIN':
            return Routine.objects.all()
        else:
            return Routine.objects.filter(created_by=user)
        