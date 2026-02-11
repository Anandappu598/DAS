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
    progress = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ('created_at',)
    
    def get_assignees_list(self, obj):
        assignees = TaskAssignee.objects.filter(task=obj)
        return TaskAssigneeSerializer(assignees, many=True).data
    
    def get_progress(self, obj):
        return obj.calculate_progress()

class TaskAssigneeSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    
    class Meta:
        model = TaskAssignee
        fields = '__all__'
        read_only_fields = ('assigned_at',)

class SubTaskSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source='task.title', read_only=True)
    is_completed = serializers.SerializerMethodField()
    
    class Meta:
        model = SubTask
        fields = '__all__'
        read_only_fields = ('created_at',)
    
    def get_is_completed(self, obj):
        return obj.status == 'DONE'


class TaskDetailSerializer(serializers.ModelSerializer):
    """Detailed task serializer with subtasks for project detail view"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    assignees_list = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    subtasks = SubTaskSerializer(many=True, read_only=True)
    
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ('created_at',)
    
    def get_assignees_list(self, obj):
        assignees = TaskAssignee.objects.filter(task=obj)
        return TaskAssigneeSerializer(assignees, many=True).data
    
    def get_progress(self, obj):
        return obj.calculate_progress()


class ProjectDetailSerializer(serializers.ModelSerializer):
    """Detailed project serializer with tasks and subtasks"""
    tasks = TaskDetailSerializer(many=True, read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    handled_by_email = serializers.EmailField(source='handled_by.email', read_only=True)
    project_lead_email = serializers.EmailField(source='project_lead.email', read_only=True)
    overall_progress = serializers.SerializerMethodField()
    
    class Meta:
        model = Projects
        fields = '__all__'
    
    def get_overall_progress(self, obj):
        """Calculate overall project progress based on all tasks"""
        tasks = obj.tasks.all()
        if not tasks.exists():
            return 0
        
        total_progress = sum(task.calculate_progress() for task in tasks)
        return round(total_progress / tasks.count())

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

class GanttAssigneeSerializer(serializers.ModelSerializer):
    """Serializer for assignees in Gantt chart view"""
    id = serializers.IntegerField(source='user.id', read_only=True)
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    role = serializers.CharField(read_only=True)
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = TaskAssignee
        fields = ['id', 'name', 'email', 'role', 'profile_picture']
    
    def get_name(self, obj):
        """Get full name or email if name not available"""
        return obj.user.email.split('@')[0].replace('.', ' ').title()
    
    def get_profile_picture(self, obj):
        """Get profile picture URL if exists"""
        return None


class GanttTaskSerializer(serializers.ModelSerializer):
    """Serializer for tasks in Gantt chart view"""
    assignees = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    duration_days = serializers.SerializerMethodField()
    overdue_days = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    bar_color = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'start_date', 'due_date', 'status', 
            'priority', 'assignees', 'is_overdue', 'duration_days',
            'overdue_days', 'progress', 'bar_color', 'completed_at'
        ]
    
    def get_assignees(self, obj):
        """Get all assignees for the task"""
        assignees = TaskAssignee.objects.filter(task=obj)
        return GanttAssigneeSerializer(assignees, many=True).data
    
    def get_is_overdue(self, obj):
        """Check if task is overdue"""
        from django.utils import timezone
        if obj.status == 'DONE':
            return False
        return obj.due_date < timezone.now().date()
    
    def get_duration_days(self, obj):
        """Calculate task duration in days"""
        if obj.start_date:
            return (obj.due_date - obj.start_date).days
        return 0
    
    def get_overdue_days(self, obj):
        """Calculate how many days overdue (if applicable)"""
        from django.utils import timezone
        if obj.status == 'DONE' or obj.due_date >= timezone.now().date():
            return 0
        return (timezone.now().date() - obj.due_date).days
    
    def get_progress(self, obj):
        """Get task progress percentage"""
        return obj.calculate_progress()
    
    def get_bar_color(self, obj):
        """Determine bar color based on status and deadline"""
        from django.utils import timezone
        
        if obj.status == 'DONE':
            return 'green'
        elif obj.due_date < timezone.now().date():
            return 'red'
        elif obj.status == 'IN_PROGRESS':
            return 'blue'
        else:
            return 'gray'


class GridViewTaskSerializer(serializers.ModelSerializer):
    """Serializer for tasks in the project grid view"""
    assignees = GanttAssigneeSerializer(many=True, source='taskassignee_set')
    progress = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'assignees', 'start_date', 'due_date', 
            'progress', 'status', 'status_display'
        ]

    def get_progress(self, obj):
        return obj.calculate_progress()

    def get_status_display(self, obj):
        from django.utils import timezone
        if obj.status == 'DONE':
            return f"Completed on {obj.completed_at.strftime('%b %d')}"
        
        now = timezone.now().date()
        if obj.due_date < now:
            overdue_days = (now - obj.due_date).days
            return f"Delayed ({overdue_days}d)"
        
        return obj.get_status_display()


class TaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating standard tasks with assignees and milestones"""
    assignees = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of user IDs to assign to this task"
    )
    milestones = serializers.ListField(
        child=serializers.DictField(),
        write_only=True, 
        required=False,
        help_text="List of milestone objects with 'title' and 'progress_weight'"
    )
    
    class Meta:
        model = Task
        fields = [
            'title', 'priority', 'start_date', 'due_date', 
            'github_link', 'figma_link', 'assignees', 'milestones'
        ]
    
    def create(self, validated_data):
        assignees_data = validated_data.pop('assignees', [])
        milestones_data = validated_data.pop('milestones', [])
        
        # Create the standard task
        task = Task.objects.create(task_type='STANDARD', **validated_data)
        
        # Create task assignees
        for user_id in assignees_data:
            try:
                user = User.objects.get(id=user_id)
                TaskAssignee.objects.create(
                    task=task,
                    user=user,
                    role='DEV'
                )
            except User.DoesNotExist:
                continue
        
        # Create milestones (as subtasks)
        for milestone in milestones_data:
            if 'title' in milestone:
                SubTask.objects.create(
                    task=task,
                    title=milestone['title'],
                    progress_weight=milestone.get('progress_weight', 25),
                    due_date=task.due_date
                )
        
        return task


class RecurringTaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating recurring tasks with recurrence pattern"""
    assignees = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    milestones = serializers.ListField(
        child=serializers.DictField(),
        write_only=True, 
        required=False
    )
    
    class Meta:
        model = Task
        fields = [
            'title', 'priority', 'start_date', 'next_occurrence', 
            'recurrence_pattern', 'assignees', 'milestones'
        ]
    
    def create(self, validated_data):
        assignees_data = validated_data.pop('assignees', [])
        milestones_data = validated_data.pop('milestones', [])
        
        # Create the recurring task
        task = Task.objects.create(
            task_type='RECURRING', 
            due_date=validated_data['next_occurrence'],  # Set due_date to next_occurrence
            **validated_data
        )
        
        # Create task assignees
        for user_id in assignees_data:
            try:
                user = User.objects.get(id=user_id)
                TaskAssignee.objects.create(task=task, user=user, role='DEV')
            except User.DoesNotExist:
                continue
        
        # Create milestones
        for milestone in milestones_data:
            if 'title' in milestone:
                SubTask.objects.create(
                    task=task,
                    title=milestone['title'],
                    progress_weight=milestone.get('progress_weight', 25),
                    due_date=task.due_date
                )
        
        return task


class RoutineTaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating routine tasks (no milestones, no GitHub/Figma)"""
    assignees = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Task
        fields = ['title', 'priority', 'start_date', 'due_date', 'assignees']
    
    def create(self, validated_data):
        assignees_data = validated_data.pop('assignees', [])
        
        # Create the routine task
        task = Task.objects.create(task_type='ROUTINE', **validated_data)
        
        # Create task assignees
        for user_id in assignees_data:
            try:
                user = User.objects.get(id=user_id)
                TaskAssignee.objects.create(task=task, user=user, role='DEV')
            except User.DoesNotExist:
                continue
        
        return task
class ProjectWorkStatsSerializer(serializers.Serializer):
    """Serializer for project work statistics response"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()
    total_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    completion_percentage = serializers.IntegerField()
    start_date = serializers.DateField()
    due_date = serializers.DateField()
    working_hours = serializers.IntegerField()
