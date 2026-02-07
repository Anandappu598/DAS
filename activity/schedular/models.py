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
      ('TEAMLEAD', 'Team Lead'),
   )
   email = models.EmailField(max_length=255, unique=True)
   role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='EMPLOYEE')
   department = models.ForeignKey('Department',on_delete=models.CASCADE,related_name='department',null=True,blank=True)
   is_active = models.BooleanField(default=True)
   phone_number = models.CharField(max_length=15, blank=True, null=True)

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
        ('REJECTED', 'Rejected'),
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
    
    title = models.CharField(max_length=150)
    project = models.ForeignKey(Projects, on_delete=models.CASCADE, related_name='tasks')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    completed_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.project.name}"


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
    due_date = models.DateField()
    completed_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.task.title}"
    
class QuickNote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quick_notes')
    note_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Note by {self.user.email} at {self.created_at.strftime("%Y-%m-%d %H:%M:%S")}'

class Catalog(models.Model):
    catalog_choices = (
        ('COURSE', 'course'),
        ('ROUTINE','routine'),
        ('WORK','work')
    )
    name = models.CharField(max_length=100)
    description = models.TextField()
    catalog_type = models.CharField(max_length=20,choices=catalog_choices)
    created_at = models.DateTimeField(auto_now_add=True)
    instructors = models.ForeignKey(User,on_delete=models.CASCADE,related_name='instructors',null=True,blank=True)

class DailyActivity(models.Model):
    status_choices = (
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    )
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name='daily_activities')
    project = models.ForeignKey(Projects,on_delete=models.CASCADE,related_name='project_activities')
    task = models.ForeignKey(Task,on_delete = models.CASCADE,related_name= 'task_activities')
    title = models.CharField(max_length=150)
    work_date = models.DateField()
    planned_hours = models.IntegerField()
    spending_hours = models.IntegerField()
    started_working_hours = models.TimeField()
    ending_working_hours = models.TimeField()
    status = models.CharField(max_length=20,choices=status_choices,default='PENDING')   
    description = models.TextField()
    remarks = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
