from rest_framework import serializers
from .models import Pending, User, Projects, ApprovalRequest, ApprovalResponse, Task, TaskAssignee,SubTask,QuickNote,Catalog
from .models import User, Projects, ApprovalRequest, ApprovalResponse, Task, TaskAssignee,SubTask,QuickNote,Catalog,DailyActivity
from django.contrib.auth import authenticate


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
    class Meta:
        model = Catalog
        fields = '__all__'
        read_only_fields = ('created_at',)

class PendingSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user_id.email', read_only=True)
    task_title = serializers.CharField(source='Daily_task_id.title', read_only=True)
    
    class Meta:
        model = Pending
        fields = '__all__'
class DailyActivitySerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    
    class Meta:
        model = DailyActivity
        fields = '__all__'
        read_only_fields = ('created_at',)

