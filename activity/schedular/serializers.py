from rest_framework import serializers
from .models import (User, Projects, ApprovalRequest, ApprovalResponse, Task, TaskAssignee,
                     SubTask, StickyNote, Catalog, TodayPlan, ActivityLog, 
                     Pending, DaySession, TeamInstruction, Notification, DailyPlanner)
from django.contrib.auth import authenticate
from .fields import LocalDateTimeField


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with HRM employee data"""
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    team_lead_email = serializers.EmailField(source='team_lead.email', read_only=True, allow_null=True)
    team_lead_name = serializers.SerializerMethodField()
    
    # Employee fields from HRM (via employee_profile)
    name = serializers.SerializerMethodField()
    employee_id = serializers.SerializerMethodField()
    designation = serializers.SerializerMethodField()
    position = serializers.SerializerMethodField()
    employee_department = serializers.SerializerMethodField()
    work_location = serializers.SerializerMethodField()
    date_of_joining = serializers.SerializerMethodField()
    employment_type = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'role', 'department', 'department_name', 
            'team_lead', 'team_lead_email', 'team_lead_name', 
            'is_active', 'phone_number', 'theme_preference',
            # HRM Employee fields
            'name', 'employee_id', 'designation', 'position', 
            'employee_department', 'work_location', 'date_of_joining', 
            'employment_type'
        ]
        read_only_fields = ['id']
    
    def get_team_lead_name(self, obj):
        if obj.team_lead:
            return obj.team_lead.employee_name or obj.team_lead.email.split('@')[0]
        return None
    
    def get_name(self, obj):
        """Get name from employee_name field (populated during HRM sync)"""
        return obj.employee_name or obj.email.split('@')[0].replace('.', ' ').title()
    
    def get_employee_id(self, obj):
        """Get employee ID from HRM"""
        return obj.hrm_employee_id
    
    def get_designation(self, obj):
        """Get designation from HRM"""
        return obj.designation
    
    def get_position(self, obj):
        """Get position from HRM"""
        try:
            return obj.employee_profile.position
        except:
            return None
    
    def get_employee_department(self, obj):
        """Get department from HRM (not DAS department)"""
        return obj.hrm_department
    
    def get_work_location(self, obj):
        """Get work location from HRM"""
        return obj.location
    
    def get_date_of_joining(self, obj):
        """Get date of joining from HRM"""
        doj = obj.date_of_joining
        return doj.isoformat() if doj else None
    
    def get_employment_type(self, obj):
        """Get employment type from HRM"""
        return obj.employee_type


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

class ProjectAssigneeSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'avatar_url']

    def get_name(self, obj):
        return obj.employee_name or obj.email.split('@')[0].replace('.', ' ').title()

    def get_avatar_url(self, obj):
        return None


class ProjectSerializer(serializers.ModelSerializer):
    project_assignees = serializers.SerializerMethodField()

    class Meta:
        model = Projects
        fields = '__all__'

    def get_project_assignees(self, obj):
        # Gather all related users at the project level
        users = set(obj.assignees.all())
        if getattr(obj, 'project_lead', None):
            users.add(obj.project_lead)
        if getattr(obj, 'handled_by', None):
            users.add(obj.handled_by)
            
        return [
            {
                'id': a.id,
                'email': a.email,
                'name': a.employee_name or a.email.split('@')[0].replace('.', ' ').title(),
                'avatar_url': None,
                'role': a.role,
            }
            for a in users
        ]


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
    subtasks = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ('created_at',)
    
    def get_assignees_list(self, obj):
        assignees = TaskAssignee.objects.filter(task=obj)
        return TaskAssigneeSerializer(assignees, many=True).data
    
    def get_progress(self, obj):
        return obj.calculate_progress()
    
    def get_subtasks(self, obj):
        from .serializers import SubTaskSerializer
        subtasks = obj.subtasks.all()
        return SubTaskSerializer(subtasks, many=True).data

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
    progress_weight = serializers.SerializerMethodField()
    completed_by_name = serializers.SerializerMethodField()
    completed_by_avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = SubTask
        fields = '__all__'
        read_only_fields = ('created_at',)
    
    def get_is_completed(self, obj):
        return obj.status == 'DONE'

    def get_progress_weight(self, obj):
        """Calculate dynamic weight: 100 / total_subtasks"""
        try:
            total_subtasks = obj.task.subtasks.count()
            if total_subtasks == 0:
                return 0
            return round(100 / total_subtasks)
        except Exception:
            return 0

    def get_completed_by_name(self, obj):
        if obj.completed_by:
            return obj.completed_by.employee_name or obj.completed_by.email.split('@')[0].replace('.', ' ').title()
        return None

    def get_completed_by_avatar(self, obj):
        if obj.completed_by:
            # We don't have a real avatar URL in the model yet, so we generate a consistent one
            name = obj.completed_by.employee_name or obj.completed_by.email.split('@')[0]
            colors = ['0D8ABC', '6D28D9', 'EC4899', '10B981', 'F59E0B', '6366F1', 'EF4444', '8B5CF6']
            color_index = hash(name) % len(colors)
            return f"https://ui-avatars.com/api/?name={name.replace(' ', '+')}&background={colors[color_index]}&color=fff"
        return None


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
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True, allow_null=True)
    handled_by_email = serializers.EmailField(source='handled_by.email', read_only=True, allow_null=True)
    project_lead_email = serializers.EmailField(source='project_lead.email', read_only=True, allow_null=True)
    overall_progress = serializers.SerializerMethodField()
    project_assignees = serializers.SerializerMethodField()
    
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

    def get_project_assignees(self, obj):
        """Gather all related users at the project level (same as ProjectSerializer)"""
        users = set(obj.assignees.all())
        if getattr(obj, 'project_lead', None):
            users.add(obj.project_lead)
        if getattr(obj, 'handled_by', None):
            users.add(obj.handled_by)
        return [
            {
                'id': a.id,
                'email': a.email,
                'name': a.employee_name or a.email.split('@')[0].replace('.', ' ').title(),
                'avatar_url': None,
                'role': a.role,
            }
            for a in users
        ]


class CatalogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)
    task_title = serializers.CharField(source='task.title', read_only=True, allow_null=True)
    instructor_email = serializers.EmailField(source='instructor.email', read_only=True, allow_null=True)
    created_at = LocalDateTimeField(read_only=True)
    updated_at = LocalDateTimeField(read_only=True)
    
    class Meta:
        model = Catalog
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class TodayPlanSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    catalog_item_details = CatalogSerializer(source='catalog_item', read_only=True, allow_null=True)
    catalog_name = serializers.SerializerMethodField()
    catalog_type = serializers.SerializerMethodField()
    # Only apply LocalDateTimeField to DateTimeField, not TimeField
    created_at = LocalDateTimeField(read_only=True)
    updated_at = LocalDateTimeField(read_only=True)
    
    class Meta:
        model = TodayPlan
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'user')
        extra_kwargs = {
            'scheduled_start_time': {'required': False, 'allow_null': True},
            'scheduled_end_time': {'required': False, 'allow_null': True},
            'catalog_item': {'required': False, 'allow_null': True},
        }
    
    def get_catalog_name(self, obj):
        """Return catalog name or custom title"""
        return obj.catalog_item.name if obj.catalog_item else obj.custom_title
    
    def get_catalog_type(self, obj):
        """Return catalog type or 'CUSTOM' for custom tasks"""
        return obj.catalog_item.catalog_type if obj.catalog_item else 'CUSTOM'


class ActivityLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    today_plan = TodayPlanSerializer(read_only=True)  # Nest full today plan details
    # Use custom timezone field for datetime fields
    actual_start_time = LocalDateTimeField(read_only=True)
    actual_end_time = LocalDateTimeField(read_only=True)
    created_at = LocalDateTimeField(read_only=True)
    updated_at = LocalDateTimeField(read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'hours_worked', 'minutes_worked')


class PendingSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    today_plan_details = TodayPlanSerializer(source='today_plan', read_only=True)
    catalog_name = serializers.SerializerMethodField()
    created_at = LocalDateTimeField(read_only=True)
    updated_at = LocalDateTimeField(read_only=True)
    
    class Meta:
        model = Pending
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def get_catalog_name(self, obj):
        if obj.today_plan.catalog_item:
            return obj.today_plan.catalog_item.name
        return obj.today_plan.custom_title


class DaySessionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    day_start_time = LocalDateTimeField(read_only=True)
    day_end_time = LocalDateTimeField(required=False, allow_null=True)
    created_at = LocalDateTimeField(read_only=True)
    updated_at = LocalDateTimeField(read_only=True)
    
    class Meta:
        model = DaySession
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class TeamInstructionSerializer(serializers.ModelSerializer):
    sent_by_email = serializers.EmailField(source='sent_by.email', read_only=True)
    project_name = serializers.SerializerMethodField()
    recipient_emails = serializers.SerializerMethodField()
    recipient_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TeamInstruction
        fields = '__all__'
        read_only_fields = ('sent_by', 'sent_at')
    
    def get_project_name(self, obj):
        return obj.project.name if obj.project else "General"
    
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
class ProjectCreateWithTasksSerializer(serializers.Serializer):
    """Simplified serializer for creating a project with tasks from the frontend modal.
    
    Accepts only the fields the frontend collects:
    - Project: name, description, project_lead, deadline, planned_hours
    - Tasks: list of {name, priority, start_date, end_date, planned_hours, assignees[], milestones[]}
    
    Validation: Sum of task planned_hours must NOT exceed project planned_hours
    """
    # Project fields
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, default='')
    deadline = serializers.DateField(required=False, allow_null=True)
    planned_hours = serializers.FloatField(required=False, default=0.0, help_text="Total planned hours budget for the project")
    assignees = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=[],
        help_text="List of User IDs assigned to the project"
    )
    
    # Tasks array
    tasks = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=[],
        help_text="List of task objects with: name, priority, start_date, end_date, planned_hours, assignees (user IDs), milestones (title strings)"
    )
    
    def validate(self, data):
        """Validate that sum of task planned_hours does not exceed project planned_hours"""
        project_planned_hours = data.get('planned_hours', 0.0)
        tasks_data = data.get('tasks', [])
        
        # Calculate total task planned hours
        total_task_hours = 0.0
        for task in tasks_data:
            task_hours = float(task.get('planned_hours', 0.0))
            total_task_hours += task_hours
        
        # Validate constraint
        if project_planned_hours > 0 and total_task_hours > project_planned_hours:
            raise serializers.ValidationError(
                f"Total task planned hours ({total_task_hours}) exceeds project planned hours ({project_planned_hours}). "
                f"Please adjust task hours or increase project budget."
            )
        
        return data
    
    def create(self, validated_data):
        from datetime import date, timedelta
        tasks_data = validated_data.pop('tasks', [])
        deadline = validated_data.pop('deadline', None)
        

        
        # Set smart defaults for required model fields
        today = date.today()
        due = deadline or (today + timedelta(days=30))
        duration_days = (due - today).days if due > today else 1
        
        # handled_by: use first admin, or first active user
        handled_by = None
        if not handled_by:
            handled_by = User.objects.filter(role='ADMIN', is_active=True).first()
        if not handled_by:
            handled_by = User.objects.filter(is_active=True).first()
        
        project = Projects.objects.create(
            name=validated_data['name'],
            description=validated_data.get('description', ''),
            project_lead=None,
            start_date=today,
            due_date=due,
            status='ACTIVE',
            working_hours=8,
            planned_hours=validated_data.get('planned_hours', 0.0),
            duration=duration_days,
            handled_by=handled_by,
            is_approved=False,  # Default to False, view will handle approval logic based on user role
        )
        
        # Add project assignees
        project_assignee_ids = validated_data.get('assignees', [])
        if project_assignee_ids:
            project.assignees.set(project_assignee_ids)
            

        
        # Create tasks
        created_tasks = []
        for t in tasks_data:
            task_name = t.get('name', t.get('title', 'Untitled Task'))
            # Map frontend priority (Low/Medium/High) to backend (LOW/MEDIUM/HIGH)
            raw_priority = t.get('priority', 'Medium')
            priority = raw_priority.upper() if raw_priority else 'MEDIUM'
            if priority not in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'):
                priority = 'MEDIUM'
            
            # Parse dates
            start_date = t.get('start_date') or t.get('startDate')
            end_date = t.get('end_date') or t.get('endDate') or t.get('due_date')
            
            if isinstance(start_date, str):
                try:
                    start_date = date.fromisoformat(start_date)
                except (ValueError, TypeError):
                    start_date = today
            
            if isinstance(end_date, str):
                try:
                    end_date = date.fromisoformat(end_date)
                except (ValueError, TypeError):
                    end_date = due
            
            task = Task.objects.create(
                title=task_name,
                project=project,
                task_type='STANDARD',
                priority=priority,
                start_date=start_date or today,
                due_date=end_date or due,
                planned_hours=float(t.get('planned_hours', 0.0)),  # Set task planned hours
            )
            
            # Create assignees
            assignee_ids = t.get('assignees', [])
            for uid in assignee_ids:
                try:
                    uid_int = int(uid) if not isinstance(uid, int) else uid
                    user = User.objects.get(id=uid_int)
                    TaskAssignee.objects.create(task=task, user=user, role='DEV')
                except (User.DoesNotExist, ValueError, TypeError):
                    continue
            
            # Create milestones (subtasks) - frontend sends string titles
            milestones = t.get('milestones', [])
            for m in milestones:
                title = m if isinstance(m, str) else m.get('title', str(m))
                weight = 25 if isinstance(m, str) else m.get('progress_weight', 25)
                SubTask.objects.create(
                    task=task,
                    title=title,
                    progress_weight=weight,
                    due_date=task.due_date,
                )
            
            created_tasks.append(task)
        
        # Attach tasks to project object for response
        project._created_tasks = created_tasks
        return project


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


class StickyNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = StickyNote
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')


class CompletionChartDataSerializer(serializers.Serializer):
    """Serializer for completion chart data - shows completed count by month"""
    month = serializers.CharField(help_text="Month in format 'YYYY-MMM', e.g., '2026-Jan'")
    count = serializers.IntegerField(help_text="Number of items completed in this month")
    month_year = serializers.CharField(help_text="Full month-year label for display")
    
    
class ProjectLineChartDataSerializer(serializers.Serializer):
    """Serializer for project completion line chart data"""
    department = serializers.CharField(allow_null=True, help_text="Department name or team")
    data = CompletionChartDataSerializer(many=True, help_text="Monthly completion data")
    total_completed = serializers.IntegerField(help_text="Total completed projects in date range")
    
    
class TaskLineChartDataSerializer(serializers.Serializer):
    """Serializer for task completion line chart data"""
    department = serializers.CharField(allow_null=True, help_text="Department name or team")
    data = CompletionChartDataSerializer(many=True, help_text="Monthly completion data")
    total_completed = serializers.IntegerField(help_text="Total completed tasks in date range")
class DailyPlannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyPlanner
        fields = '__all__'

class ProjectDashboardSerializer(serializers.Serializer):
    planned_hours_budget = serializers.FloatField()
    planned_hours_total = serializers.FloatField()
    achieved_hours = serializers.FloatField()
    remaining_hours = serializers.FloatField()
    completion_percentage = serializers.FloatField()
    task_stats = serializers.DictField()

class ProjectAnalyticsSerializer(serializers.Serializer):
    task_name = serializers.CharField()
    planned = serializers.FloatField()
    achieved = serializers.FloatField()

class DailyTrendSerializer(serializers.Serializer):
    date = serializers.DateField()
    planned = serializers.FloatField()
    achieved = serializers.FloatField()
