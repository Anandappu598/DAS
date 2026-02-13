from django.db import models
from django.contrib.auth.models import AbstractBaseUser,BaseUserManager
from django.utils import timezone
from datetime import timedelta
import random
import uuid
# Create your models here.
class UserManager(BaseUserManager):
   def create_user(self, email, password=None,role = 'EMPLOYEE'):
      if not email:
         raise ValueError("Users must have an email address")
      user = self.model(email=self.normalize_email(email), role=role)
      user.set_password(password)
      user.save(using=self._db)
      return user
   def create_superuser(self, email, password):
      return self.create_user(email=email, password=password, role="ADMIN")
   
class User(AbstractBaseUser):
   ROLE_CHOICES = (
      ('ADMIN', 'Admin'),
      ('EMPLOYEE', 'Employee'),
      ('MANAGER', 'Manager'),
      ('TEAMLEAD', 'Team Lead')
   )
   
   THEME_CHOICES = (
      ('light', 'Light Mode'),
      ('dark', 'Dark Mode'),
      ('auto', 'Auto/System Default')
   )
   
   email = models.EmailField(max_length=255, unique=True)
   role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='EMPLOYEE')
   department = models.ForeignKey('Department',on_delete=models.CASCADE,related_name='department',null=True,blank=True)
   is_active = models.BooleanField(default=True)
   phone_number = models.CharField(max_length=15, blank=True, null=True)
   theme_preference = models.CharField(max_length=10, choices=THEME_CHOICES, default='auto')

   objects = UserManager()

   USERNAME_FIELD = 'email'
   REQUIRED_FIELDS = []

   def __str__(self):
      return self.email
   
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
   
class OTPVerification(models.Model):
    OTP_TYPE_CHOICES = (
        ('signup', 'Signup'),
        ('forgot_password', 'Forgot Password'),
    )
    
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    otp_type = models.CharField(max_length=20, choices=OTP_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    user_data = models.JSONField(null=True, blank=True)  # To store signup data temporarily
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_otp():
        return str(random.randint(100000, 999999))
    
    def is_valid(self):
        return not self.is_verified and timezone.now() < self.expires_at
    
    def __str__(self):
        return f"{self.email} - {self.otp_type} - {self.otp}"


class Projects(models.Model):
    status_choice = (
         ('ACTIVE', 'ACTIVE'),
         ('COMPLETED', 'COMPLETED'),
         ('ON HOLD', 'ON HOLD'),
    )
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=50,choices=status_choice)
    project_lead = models.ForeignKey(User,on_delete= models.CASCADE,related_name='project_lead',null = True,blank=True)
    start_date = models.DateField()
    due_date = models.DateField()
    description = models.TextField()
    working_hours = models.IntegerField()
    create_date = models.DateTimeField(auto_now_add=True)
    duration = models.IntegerField()
    completed_date = models.DateField(null=True,blank=True)
    handled_by = models.ForeignKey(User,on_delete= models.CASCADE,related_name='handled_by',null = False,blank=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects', null=True, blank=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class ApprovalRequest(models.Model):
    """Model for users to request approvals"""
    
    REFERENCE_TYPE_CHOICES = (
        ('PROJECT', 'Project'),
        ('TASK', 'Task'),
    )
    
    APPROVAL_TYPE_CHOICES = (
        ('CREATION', 'Creation'),
        ('COMPLETION', 'Completion'),
        ('MODIFICATION', 'Modification'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    
    reference_type = models.CharField(max_length=20, choices=REFERENCE_TYPE_CHOICES)
    reference_id = models.IntegerField()
    approval_type = models.CharField(max_length=20, choices=APPROVAL_TYPE_CHOICES)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approval_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    request_data = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.reference_type} - {self.approval_type} by {self.requested_by.email} - {self.status}"


class ApprovalResponse(models.Model):
    """Model for admin to approve/reject requests"""
    
    ACTION_CHOICES = (
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected')
    )
    
    approval_request = models.OneToOneField(ApprovalRequest, on_delete=models.CASCADE, related_name='response')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    reviewed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approval_responses')
    reviewed_at = models.DateTimeField(auto_now_add=True)
    rejection_reason = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-reviewed_at']
    
    def __str__(self):
        return f"{self.action} by {self.reviewed_by.email} on {self.reviewed_at}"
    
    def save(self, *args, **kwargs):
        """Update the approval request status when response is created"""
        self.approval_request.status = self.action
        self.approval_request.save()
        super().save(*args, **kwargs)

class Task(models.Model):
    """Model for tasks created after project approval"""
    
    PRIORITY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('DONE', 'Done'),
    )
    
    TASK_TYPE_CHOICES = (
        ('STANDARD', 'Standard'),
        ('RECURRING', 'Recurring'),
        ('ROUTINE', 'Routine'),
    )
    
    RECURRENCE_PATTERN_CHOICES = (
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    )
    
    title = models.CharField(max_length=150)
    project = models.ForeignKey(Projects, on_delete=models.CASCADE, related_name='tasks')
    project_lead = models.ForeignKey(User,on_delete=models.CASCADE,null=True,blank=True)
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, default='STANDARD')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    
    next_occurrence = models.DateField(null=True, blank=True, help_text='For recurring tasks')
    recurrence_pattern = models.CharField(max_length=20, choices=RECURRENCE_PATTERN_CHOICES, null=True, blank=True)
    github_link = models.URLField(null=True, blank=True, help_text='GitHub repository or issue link')
    figma_link = models.URLField(null=True, blank=True, help_text='Figma design link')
    completed_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.project.name}"
    
    def calculate_progress(self):
        """Calculate task progress based on completed subtasks and their weights"""
        subtasks = self.subtasks.all()
        if not subtasks.exists():
            return 0
        
        total_weight = sum(subtask.progress_weight for subtask in subtasks)
        if total_weight == 0:
            return 0
        
        completed_weight = sum(
            subtask.progress_weight for subtask in subtasks 
            if subtask.status == 'DONE'
        )
        
        return round((completed_weight / total_weight) * 100)
    
    def regenerate_recurring_task(self):
        """Regenerate a new instance of this recurring task"""
        if self.task_type != 'RECURRING' or not self.recurrence_pattern:
            return None
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        # Calculate next occurrence based on pattern
        if self.recurrence_pattern == 'DAILY':
            next_occurrence = self.next_occurrence + timedelta(days=1)
        elif self.recurrence_pattern == 'WEEKLY':
            next_occurrence = self.next_occurrence + timedelta(weeks=1)
        elif self.recurrence_pattern == 'MONTHLY':
            next_occurrence = self.next_occurrence + relativedelta(months=1)
        elif self.recurrence_pattern == 'YEARLY':
            next_occurrence = self.next_occurrence + relativedelta(years=1)
        else:
            return None
        
        # Create new task instance
        new_task = Task.objects.create(
            title=self.title,
            project=self.project,
            task_type='RECURRING',
            priority=self.priority,
            start_date=next_occurrence,
            due_date=next_occurrence,
            next_occurrence=next_occurrence,
            recurrence_pattern=self.recurrence_pattern
        )
        
        # Copy assignees
        for assignee in self.assignees.all():
            TaskAssignee.objects.create(
                task=new_task,
                user=assignee.user,
                role=assignee.role
            )
        
        # Copy milestones (subtasks)
        for subtask in self.subtasks.all():
            SubTask.objects.create(
                task=new_task,
                title=subtask.title,
                progress_weight=subtask.progress_weight,
                due_date=next_occurrence
            )
        
        return new_task


class TaskAssignee(models.Model):
    """Model for assigning tasks to users with roles"""
    
    ROLE_CHOICES = (
        ('LEAD', 'Lead'),
        ('DEV', 'Developer'),
        ('BACKEND', 'Backend'),
    )
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='assignees')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_tasks')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('task', 'user')
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.task.title} ({self.role})"
    
class SubTask(models.Model):
    """Model for subtasks under a main task"""
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('DONE', 'Done'),
    )
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='subtasks')
    title = models.CharField(max_length=150)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    progress_weight = models.IntegerField(default=25, help_text='Weight of this subtask in percentage (e.g., 25 for 25%)')
    due_date = models.DateField()
    completed_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.task.title}"


class TeamInstruction(models.Model):
    """Model for sending instructions to team members on a project"""
    
    project = models.ForeignKey(Projects, on_delete=models.CASCADE, related_name='team_instructions')
    recipients = models.ManyToManyField(User, related_name='received_instructions')
    subject = models.CharField(max_length=200)
    instructions = models.TextField()
    sent_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_instructions')
    sent_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.subject} - {self.project.name} by {self.sent_by.email}"


class Notification(models.Model):
    """Model for user notifications"""
    
    NOTIFICATION_TYPES = (
        ('PROJECT_CREATED', 'Project Created'),
        ('PROJECT_APPROVED', 'Project Approved'),
        ('PROJECT_REJECTED', 'Project Rejected'),
        ('TASK_CREATED', 'Task Created'),
        ('TASK_ASSIGNED', 'Task Assigned'),
        ('TASK_COMPLETED', 'Task Completed'),
        ('TASK_UPDATED', 'Task Updated'),
        ('APPROVAL_REQUESTED', 'Approval Requested'),
        ('APPROVAL_APPROVED', 'Approval Approved'),
        ('APPROVAL_REJECTED', 'Approval Rejected'),
        ('INSTRUCTION_RECEIVED', 'Instruction Received'),
        ('SUBTASK_COMPLETED', 'SubTask Completed'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    reference_type = models.CharField(max_length=20, null=True, blank=True)  # 'project', 'task', etc.
    reference_id = models.IntegerField(null=True, blank=True)  # ID of related object
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"

    
class QuickNote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quick_notes')
    note_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Note by {self.user.email} at {self.created_at.strftime("%Y-%m-%d %H:%M:%S")}'

class Catalog(models.Model):
    """Master catalog containing all work items (Projects, Tasks, Courses, Routines)"""
    CATALOG_TYPE_CHOICES = (
        ('PROJECT', 'Project'),
        ('TASK', 'Task'),
        ('COURSE', 'Course'),
        ('ROUTINE', 'Routine'),
        ('CUSTOM', 'Custom Work')
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='catalog_items', null=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    catalog_type = models.CharField(max_length=20, choices=CATALOG_TYPE_CHOICES)
    
    # References to existing models (optional)
    project = models.ForeignKey(Projects, on_delete=models.CASCADE, null=True, blank=True, related_name='catalog_items')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name='catalog_items')
    
    # For courses and routines
    estimated_hours = models.DecimalField(max_digits=7, decimal_places=2, default=1.0)
    progress_percentage = models.IntegerField(default=0, help_text="Progress percentage (0-100)")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.catalog_type}: {self.name}"
    
    def calculate_progress(self):
        """Calculate progress based on linked task or project"""
        if self.task:
            if self.task.status == 'DONE':
                self.progress_percentage = 100
            elif self.task.status == 'IN_PROGRESS':
                # Calculate based on subtasks if available
                subtasks = self.task.subtasks.all()
                if subtasks.count() > 0:
                    completed = subtasks.filter(status='DONE').count()
                    self.progress_percentage = int((completed / subtasks.count()) * 100)
                else:
                    self.progress_percentage = 50  # Default for in-progress
            else:
                self.progress_percentage = 0
        elif self.project:
            tasks = self.project.tasks.all()
            if tasks.count() > 0:
                completed = tasks.filter(status='DONE').count()
                self.progress_percentage = int((completed / tasks.count()) * 100)
            else:
                self.progress_percentage = 0
        self.save()
        return self.progress_percentage


class TodayPlan(models.Model):
    """Daily plan - items dragged from catalog with scheduled times"""
    STATUS_CHOICES = (
        ('PLANNED', 'Planned'),
        ('STARTED', 'Started'),
        ('IN_ACTIVITY', 'In Activity Log'),
        ('COMPLETED', 'Completed'),
        ('MOVED_TO_PENDING', 'Moved to Pending')
    )
    
    QUADRANT_CHOICES = (
        ('Q1', 'Q1: Do First (Urgent & Important)'),
        ('Q2', 'Q2: Schedule (Important, Not Urgent)'),
        ('Q3', 'Q3: Delegate (Urgent, Not Important)'),
        ('Q4', 'Q4: Eliminate (Not Urgent, Not Important)'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='today_plans')
    catalog_item = models.ForeignKey(Catalog, on_delete=models.CASCADE, related_name='planned_items')
    
    plan_date = models.DateField()
    scheduled_start_time = models.TimeField()
    scheduled_end_time = models.TimeField()
    planned_duration_minutes = models.IntegerField(help_text="Planned duration in minutes")
    
    quadrant = models.CharField(max_length=2, choices=QUADRANT_CHOICES, default='Q2', help_text="Eisenhower Matrix quadrant")
    order_index = models.IntegerField(default=0, help_text="Order in today's plan")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')
    
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['plan_date', 'order_index']
        unique_together = ['user', 'plan_date', 'order_index']
    
    def __str__(self):
        return f"{self.user.email} - {self.catalog_item.name} on {self.plan_date}"


class ActivityLog(models.Model):
    """Tracks actual work time when user clicks arrow on today's plan item"""
    STATUS_CHOICES = (
        ('IN_PROGRESS', 'In Progress'),
        ('STOPPED', 'Stopped'),
        ('COMPLETED', 'Completed')
    )
    
    today_plan = models.ForeignKey(TodayPlan, on_delete=models.CASCADE, related_name='activity_logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    
    actual_start_time = models.DateTimeField(auto_now_add=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    
    # Calculated fields
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Hours worked")
    minutes_worked = models.IntegerField(default=0, help_text="Total minutes worked")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    
    # Progress tracking
    work_notes = models.TextField(blank=True, null=True, help_text="Notes about the work done")
    is_task_completed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.today_plan.catalog_item.name} - {self.status}"
    
    def calculate_time_worked(self):
        """Calculate time worked when stopped"""
        if self.actual_end_time:
            delta = self.actual_end_time - self.actual_start_time
            self.minutes_worked = int(delta.total_seconds() / 60)
            self.hours_worked = round(self.minutes_worked / 60, 2)
            self.save()


class Pending(models.Model):
    """Tasks moved to pending when stopped but not completed"""
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('REPLANNED', 'Replanned'),
        ('CANCELLED', 'Cancelled')
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pending_tasks')
    today_plan = models.ForeignKey(TodayPlan, on_delete=models.CASCADE, related_name='pending_items')
    activity_log = models.ForeignKey(ActivityLog, on_delete=models.SET_NULL, null=True, blank=True, related_name='pending_items')
    
    original_plan_date = models.DateField()
    replanned_date = models.DateField(null=True, blank=True)
    
    minutes_left = models.IntegerField(default=0, help_text="Estimated minutes left to complete")
    reason = models.TextField(blank=True, null=True, help_text="Reason for not completing")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.today_plan.catalog_item.name} - {self.status}"



class DaySession(models.Model):
    """Tracks when user starts/ends their work day"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='day_sessions')
    session_date = models.DateField()
    
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-session_date']
        unique_together = ['user', 'session_date']
    
    def __str__(self):
        return f"{self.user.email} - {self.session_date} - {'Active' if self.is_active else 'Ended'}"
