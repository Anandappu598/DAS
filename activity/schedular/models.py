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
   team_lead = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='team_members', help_text='Team Lead for this user')
   is_active = models.BooleanField(default=True)
   phone_number = models.CharField(max_length=15, blank=True, null=True)
   theme_preference = models.CharField(max_length=10, choices=THEME_CHOICES, default='auto')
   
   # HRM Sync Fields
   hrm_employee_id = models.CharField(max_length=100, null=True, blank=True, help_text='Employee ID from HRM system')
   last_sync_time = models.DateTimeField(null=True, blank=True, help_text='Last time employee data was synced from HRM')
   
   # Employee Data from HRM (stored for quick access)
   employee_name = models.CharField(max_length=300, blank=True, null=True, help_text='Full name from HRM')
   employee_type = models.CharField(max_length=100, blank=True, null=True, help_text='Employment type: intern, permanent, Trainee, Consultant')
   designation = models.CharField(max_length=100, blank=True, null=True, help_text='Job designation from HRM')
   hrm_department = models.CharField(max_length=200, blank=True, null=True, help_text='Department name from HRM')
   location = models.CharField(max_length=200, blank=True, null=True, help_text='Work location')
   date_of_joining = models.DateField(null=True, blank=True, help_text='Date employee joined')
   
   # Active status in HRM (source of truth)
   is_active_in_hrm = models.BooleanField(default=True, help_text='Active status from HRM system')

   objects = UserManager()

   USERNAME_FIELD = 'email'
   REQUIRED_FIELDS = []

   def __str__(self):
      return self.email
   
   def get_team_members(self):
      """Get all direct team members under this user (if they are a team lead)"""
      return self.team_members.filter(is_active=True)
   
   @property
   def is_admin(self):
      return self.role == 'ADMIN'
   
   @property
   def is_manager(self):
      return self.role == 'MANAGER'
   
   @property
   def is_team_lead(self):
      return self.role == 'TEAMLEAD'
   
   @property
   def is_employee(self):
      return self.role == 'EMPLOYEE'

   def get_team_members(self):
      """Get all direct team members under this user (if they are a team lead)"""
      return self.team_members.filter(is_active=True)
   
   # Helper properties to access HRM employee data
   @property
   def name(self):
      """Get employee name - Returns employee_name field or email as fallback"""
      if self.employee_name:
         return self.employee_name
      return self.email.split('@')[0].replace('.', ' ').title()
   
   @property
   def full_name(self):
      """Get employee name from HRM data"""
      return self.name  # Use the name property
   
   @property
   def employee_id(self):
      """Get employee ID from HRM data"""
      return self.hrm_employee_id or None
   
   @property
   def employee_designation(self):
      """Get HRM designation"""
      return self.designation or None
   
   @property
   def employee_department(self):
      """Get HRM department"""
      return self.hrm_department or None
   
   def sync_from_employee_profile(self):
      """Sync basic fields from HRM Employee profile to User"""
      try:
         emp = self.employee_profile
         self.phone_number = emp.phone or self.phone_number
         self.is_active = emp.is_active
         self.save(update_fields=['phone_number', 'is_active'])
      except Employee.DoesNotExist:
         pass
   
   def get_all_subordinates(self):
      """Get all subordinates recursively based on hierarchy"""
      if self.role == 'ADMIN':
          return User.objects.all()
      
      subordinates = set()
      
      # Direct reports
      direct_reports = self.team_members.filter(is_active=True)
      subordinates.update(direct_reports)
      
      # Recursive for deeper levels (e.g., Manager -> TL -> Employee)
      for report in direct_reports:
          subordinates.update(report.get_all_subordinates())
          
      # If Manager, ensuring we catch Team Leads even if not directly assigned 
      # (Fallback for existing logic if Managers manage ALL Team Leads)
      if self.role == 'MANAGER':
         # OPTIONAL: If strict hierarchy is enforced via team_lead field, remove this.
         # Based on user req "Manager... Can view only data within their managerial scope",
         # if that scope is defined by the team_lead field, strict recursion is enough.
         # However, to be safe with current data, we might want to keep the broad check 
         # OR rely strictly on the `team_lead` link. 
         # Let's stick to strict hierarchy to meet the "RBAC" requirement accurately.
         pass

      return list(subordinates)
    
   def get_all_descendants(self):
      """Alias for get_all_subordinates for clarity"""
      return self.get_all_subordinates()
   
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    """
    Employee model for SSO integration with HRM
    Stores complete employee details synced from HRM system
    HRM is the source of truth for all employee data
    """
    # Link to User (authentication)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    
    # Basic Information (from HRM EmployeeInformation)
    employee_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    name = models.CharField(max_length=300, blank=True, null=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=100, blank=True, null=True)  # Keep for backward compatibility
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)  # Keep for backward compatibility
    department = models.CharField(max_length=1000, blank=True, null=True)  # Keep for backward compatibility
    
    # Additional Contact
    secondary_phone = models.CharField(max_length=15, blank=True, null=True)
    secondary_email = models.CharField(max_length=200, blank=True, null=True)
    
    # Extended Address Information
    city = models.CharField(max_length=1000, blank=True, null=True)
    state = models.CharField(max_length=1000, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    
    # Employment Information
    employment_type = models.CharField(max_length=100, blank=True, null=True)  # intern, permanent, Trainee, Consultant
    designation = models.CharField(max_length=100, blank=True, null=True)  # HRM Designation (Admin, HR, Employee, Recruiter)
    position = models.CharField(max_length=200, blank=True, null=True)  # Position name from DesignationModel
    work_location = models.CharField(max_length=1000, blank=True, null=True)
    
    # HRM Role Hierarchy
    hrm_role = models.CharField(max_length=100, blank=True, null=True)  # Original HRM role
    reporting_manager_id = models.CharField(max_length=100, blank=True, null=True)  # Employee ID of reporting manager
    reporting_manager_name = models.CharField(max_length=300, blank=True, null=True)
    
    # Dates
    date_of_joining = models.DateField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Probation/Internship
    probation_status = models.CharField(max_length=100, blank=True, null=True)
    probation_from = models.DateField(null=True, blank=True)
    probation_to = models.DateField(null=True, blank=True)
    internship_from = models.DateField(null=True, blank=True)
    internship_to = models.DateField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    employee_status = models.CharField(max_length=100, default='active')  # active, in_active, Resigned
    profile_verification = models.CharField(max_length=100, blank=True, null=True)
    
    # HRM Sync Fields
    hrm_employee_id = models.CharField(max_length=100, null=True, blank=True, help_text='Employee ID from HRM system (for linking)')
    is_active_in_hrm = models.BooleanField(default=True, help_text='Active status from HRM (source of truth)')
    
    # Sync Tracking
    last_synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.employee_id})"
    
    class Meta:
        db_table = 'employee'
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
        ordering = ['-created_at']
   
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
    planned_hours = models.FloatField(default=0.0)
    create_date = models.DateTimeField(auto_now_add=True)
    duration = models.IntegerField()
    completed_date = models.DateField(null=True,blank=True)
    handled_by = models.ForeignKey(User,on_delete= models.CASCADE,related_name='handled_by',null = False,blank=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects', null=True, blank=True)
    is_approved = models.BooleanField(default=False)

    approval_status = models.CharField(max_length=50, null=True, blank=True, help_text='Current approval status: PENDING_COMPLETION, etc.')
    rejection_reason = models.TextField(null=True, blank=True)
    assignees = models.ManyToManyField(User, related_name='assigned_projects', blank=True)

    def get_planned_hours_total(self):
        """Sum of planned hours for all tasks in this project"""
        return self.tasks.aggregate(total=models.Sum('planned_hours'))['total'] or 0.0

    def get_achieved_hours(self):
        """Sum of achieved hours for all COMPLETED tasks in this project"""
        # Sum achieved hours from tasks
        return sum(task.get_achieved_hours() for task in self.tasks.all())

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
        ('PENDING_APPROVAL', 'Pending Approval'),
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
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, default='STANDARD')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    planned_hours = models.FloatField(default=0.0)

    def clean(self):
        """Ensure task planned hours don't exceed project planned_hours budget"""
        if self.planned_hours > 0 and self.project.planned_hours > 0:
            total_planned = self.project.tasks.exclude(id=self.id).aggregate(
                total=models.Sum('planned_hours')
            )['total'] or 0
            
            if total_planned + self.planned_hours > self.project.planned_hours:
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    f"Total planned hours ({total_planned + self.planned_hours}) "
                    f"exceed project planned hours budget ({self.project.planned_hours})"
                )
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    next_occurrence = models.DateField(null=True, blank=True, help_text='For recurring tasks')
    recurrence_pattern = models.CharField(max_length=20, choices=RECURRENCE_PATTERN_CHOICES, null=True, blank=True)
    github_link = models.URLField(null=True, blank=True, help_text='GitHub repository or issue link')
    figma_link = models.URLField(null=True, blank=True, help_text='Figma design link')
    approval_status = models.CharField(max_length=50, null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    completed_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.project.name}"

    def get_achieved_hours(self, start_date=None, end_date=None):
        """Calculate total achieved hours from activity logs for this task"""
        # Removed DONE check to allow progressive progress tracking
        # To find activity logs for this task, we go via TodayPlan -> Catalog -> Task
        qs = ActivityLog.objects.filter(today_plan__catalog_item__task=self)
        
        if start_date:
            qs = qs.filter(actual_start_time__date__gte=start_date)
        if end_date:
            qs = qs.filter(actual_start_time__date__lte=end_date)
            
        total_achieved = qs.aggregate(
            total=models.Sum('hours_worked')
        )['total'] or 0
        
        return float(total_achieved)
    
    def calculate_progress(self):
        """Calculate task progress dynamically based on count of subtasks (100/N)"""
        subtasks = self.subtasks.all()
        count = subtasks.count()
        if count == 0:
            # If no subtasks, check if task itself is done (fallback)
            return 100 if self.status == 'DONE' else 0
        
        completed_count = subtasks.filter(status='DONE').count()
        return round((completed_count / count) * 100)
    
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
    completed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_subtasks')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.task.title}"


class TeamInstruction(models.Model):
    """Model for sending instructions to team members on a project"""
    
    project = models.ForeignKey(Projects, on_delete=models.CASCADE, related_name='team_instructions', null=True, blank=True)
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
    catalog_type = models.CharField(max_length=50) # Removed choices restriction to allow dynamic categories
    
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
    catalog_item = models.ForeignKey(Catalog, on_delete=models.CASCADE, related_name='planned_items', null=True, blank=True)
    
    # For custom tasks (when catalog_item is null)
    custom_title = models.CharField(max_length=255, blank=True, null=True, help_text="Title for custom tasks")
    custom_description = models.TextField(blank=True, null=True, help_text="Description for custom tasks")
    
    plan_date = models.DateField()
    scheduled_start_time = models.TimeField(null=True, blank=True, help_text="Can be set later in activity log")
    scheduled_end_time = models.TimeField(null=True, blank=True, help_text="Can be set later in activity log")
    planned_duration_minutes = models.IntegerField(help_text="Planned duration in minutes")
    
    quadrant = models.CharField(max_length=2, choices=QUADRANT_CHOICES, default='Q2', help_text="Eisenhower Matrix quadrant")
    order_index = models.IntegerField(default=0, help_text="Order in today's plan")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')
    
    is_unplanned = models.BooleanField(default=False, help_text="True if this was an unplanned addition to the daily plan")
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['plan_date', 'order_index']
        unique_together = ['user', 'plan_date', 'order_index']
    
    def __str__(self):
        task_name = self.catalog_item.name if self.catalog_item else self.custom_title
        return f"{self.user.email} - {task_name} on {self.plan_date}"


class ActivityLog(models.Model):
    """Tracks actual work time when user clicks arrow on today's plan item"""
    STATUS_CHOICES = (
        ('IN_PROGRESS', 'In Progress'),
        ('STOPPED', 'Stopped'),
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed')
    )
    
    today_plan = models.ForeignKey(TodayPlan, on_delete=models.CASCADE, related_name='activity_logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    
    actual_start_time = models.DateTimeField()
    actual_end_time = models.DateTimeField(null=True, blank=True)
    
    # Calculated fields
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Hours worked")
    minutes_worked = models.IntegerField(default=0, help_text="Total minutes worked")
    extra_minutes = models.IntegerField(default=0, help_text="Extra minutes worked beyond planned time")
    
    # Mark if this work was planned or unplanned
    is_unplanned = models.BooleanField(default=False, help_text="True if this work was on an unplanned task")
    
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
    extra_minutes = models.IntegerField(default=0, help_text="Extra minutes worked beyond planned time")
    reason = models.TextField(blank=True, null=True, help_text="Reason for not completing")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

class DailyPlanner(models.Model):
    """Tracks daily planned hours and targets for users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_plans')
    date = models.DateField()
    planned_hours = models.FloatField(default=8.0)
    actual_hours = models.FloatField(default=0.0)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.email} - {self.date} - {self.planned_hours}h"



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


class StickyNote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sticky_notes')
    content = models.TextField(blank=True)
    color = models.CharField(max_length=20, default='0xFFFEF3C7') # Store as 0xAARRGGBB hex string
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.email} - Note {self.id}"
