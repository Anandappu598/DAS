from django.contrib import admin
from .models import (User, OTPVerification, Projects, ApprovalRequest, ApprovalResponse, 
                     Task, TaskAssignee, QuickNote, SubTask, Catalog, DailyActivity, Department)

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
    list_display = ('user','note_text','created_at')
    list_filter = ('user','created_at')
    search_fields = ('note_text','user__email')
    readonly_fields = ('created_at',)

@admin.register(SubTask)
class SubTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'task', 'status', 'due_date', 'completed_at', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'task__title')
    readonly_fields = ('created_at',)

@admin.register(Catalog)
class CatalogAdmin(admin.ModelAdmin):
    list_display = ('name', 'catalog_type', 'instructors', 'created_at')
    list_filter = ('catalog_type', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)

@admin.register(DailyActivity)
class DailyActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'project', 'task', 'work_date', 'status', 'planned_hours', 'spending_hours')
    list_filter = ('status', 'work_date', 'created_at')
    search_fields = ('title', 'description', 'user__email', 'project__name', 'task__title')
    readonly_fields = ('created_at',)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name',)
    readonly_fields = ('created_at',)

