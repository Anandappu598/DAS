from django.contrib import admin
from .models import User, OTPVerification, Projects, ApprovalRequest, ApprovalResponse, Task, TaskAssignee,QuickNote,Course,Routine

# Register your models here.
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'role', 'is_active', 'phone_number')
    list_filter = ('role', 'is_active')
    search_fields = ('email', 'phone_number')

@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('email', 'otp', 'otp_type', 'created_at', 'expires_at', 'is_verified')
    list_filter = ('otp_type', 'is_verified')
    search_fields = ('email',)

@admin.register(Projects)
class ProjectsAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'start_date', 'due_date', 'duration', 'handled_by', 'created_by')
    list_filter = ('status',)
    search_fields = ('name', 'description')

@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ('reference_type', 'approval_type', 'requested_by', 'status', 'created_at')
    list_filter = ('reference_type', 'approval_type', 'status', 'created_at')
    search_fields = ('requested_by__email',)
    readonly_fields = ('created_at',)

@admin.register(ApprovalResponse)
class ApprovalResponseAdmin(admin.ModelAdmin):
    list_display = ('approval_request', 'action', 'reviewed_by', 'reviewed_at')
    list_filter = ('action', 'reviewed_at')
    search_fields = ('reviewed_by__email', 'approval_request__requested_by__email')
    readonly_fields = ('reviewed_at',)
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'priority', 'status', 'due_date', 'completed_at', 'created_at')
    list_filter = ('priority', 'status', 'created_at')
    search_fields = ('title', 'project__name')
    readonly_fields = ('created_at',)

@admin.register(TaskAssignee)
class TaskAssigneeAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'role', 'assigned_at')
    list_filter = ('role', 'assigned_at')
    search_fields = ('task__title', 'user__email')
    readonly_fields = ('assigned_at',)

@admin.register(QuickNote)
class QuickNoteAdmin(admin.ModelAdmin):
    list_display = ('title','created_at')
    list_filter = ('title',)
    search_fields = ('title',)
    readonly_fields = ('created_at',)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display  = ('course_name','description','created_at')
    list_filter = ('course_name',)
    search_fields = ('course_name',)
    readonly_fields = ('created_at',)
