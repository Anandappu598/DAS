from rest_framework import serializers
from .models import (User, Projects, ApprovalRequest, ApprovalResponse, Task, TaskAssignee,
                     SubTask, QuickNote, Catalog, TodayPlan, ActivityLog, 
                     Pending, DaySession, TeamInstruction, Notification)
from django.contrib.auth import authenticate


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'role', 'department', 'department_name', 'is_active', 'phone_number', 'theme_preference']
        read_only_fields = ['id']


class UserPreferenceSerializer(serializers.Serializer):
    """Serializer for updating user preferences"""
    theme_preference = serializers.ChoiceField(
        choices=['light', 'dark', 'auto'],
        required=True
    )


class SignupWithOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default='EMPLOYEE')
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists")
        return value

class VerifySignupOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    
class LoginSerializers(serializers.Serializer):
      email = serializers.EmailField()
      password = serializers.CharField(write_only=True)


      def validate(self, data):
         user = authenticate(email=data["email"], password=data["password"])
         if not user:
            raise serializers.ValidationError("Invalid email or password")
         data["user"] = user
         return data
      
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=6)

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projects
        fields = '__all__'

class ApprovalRequestSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.EmailField(source='requested_by.email', read_only=True)
    
    class Meta:
        model = ApprovalRequest
        fields = '__all__'
        read_only_fields = ('requested_by', 'status', 'created_at')

class ApprovalResponseSerializer(serializers.ModelSerializer):
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)
    approval_request_details = ApprovalRequestSerializer(source='approval_request', read_only=True)
    
    class Meta:
        model = ApprovalResponse
        fields = '__all__'
        read_only_fields = ('reviewed_by', 'reviewed_at')
class TaskSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    assignees_list = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ('created_at',)
    
    def get_assignees_list(self, obj):
        assignees = TaskAssignee.objects.filter(task=obj)
        return TaskAssigneeSerializer(assignees, many=True).data

class TaskAssigneeSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    
    class Meta:
        model = TaskAssignee
        fields = '__all__'
        read_only_fields = ('assigned_at',)

class SubTaskSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source='task.title', read_only=True)
    
    class Meta:
        model = SubTask
        fields = '__all__'
        read_only_fields = ('created_at',)

class QuickNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickNote
        fields = '__all__'
        read_only_fields = ('created_at',)

class CatalogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)
    task_title = serializers.CharField(source='task.title', read_only=True, allow_null=True)
    instructor_email = serializers.EmailField(source='instructor.email', read_only=True, allow_null=True)
    
    class Meta:
        model = Catalog
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class TodayPlanSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    catalog_item_details = CatalogSerializer(source='catalog_item', read_only=True)
    catalog_name = serializers.CharField(source='catalog_item.name', read_only=True)
    catalog_type = serializers.CharField(source='catalog_item.catalog_type', read_only=True)
    
    class Meta:
        model = TodayPlan
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ActivityLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    today_plan_details = TodayPlanSerializer(source='today_plan', read_only=True)
    catalog_name = serializers.CharField(source='today_plan.catalog_item.name', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'hours_worked', 'minutes_worked')


class PendingSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    today_plan_details = TodayPlanSerializer(source='today_plan', read_only=True)
    catalog_name = serializers.CharField(source='today_plan.catalog_item.name', read_only=True)
    
    class Meta:
        model = Pending
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class DaySessionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = DaySession
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class TeamInstructionSerializer(serializers.ModelSerializer):
    sent_by_email = serializers.EmailField(source='sent_by.email', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    recipient_emails = serializers.SerializerMethodField()
    recipient_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TeamInstruction
        fields = '__all__'
        read_only_fields = ('sent_by', 'sent_at')
    
    def get_recipient_emails(self, obj):
        return [user.email for user in obj.recipients.all()]
    
    def get_recipient_count(self, obj):
        return obj.recipients.count()

class NotificationSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('user', 'created_at')
    
    def get_time_ago(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return "just now"
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff < timedelta(days=7):
            days = diff.days
            return f"{days} day{'s' if days > 1 else ''} ago"
        else:
            return obj.created_at.strftime('%b %d, %Y')