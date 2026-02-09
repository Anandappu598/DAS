from django.contrib import admin
from .models import (User, OTPVerification, Projects, ApprovalRequest, ApprovalResponse, 
                     Task, TaskAssignee, QuickNote, SubTask, Catalog, Department, 
                     Pending, TodayPlan, ActivityLog, DaySession, TeamInstruction, Notification)

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

@admin.register(TeamInstruction)
class TeamInstructionAdmin(admin.ModelAdmin):
    list_display = ('subject', 'project', 'sent_by', 'sent_at', 'get_recipient_count')
    list_filter = ('project', 'sent_at', 'sent_by')
    search_fields = ('subject', 'instructions', 'project__name', 'sent_by__email')
    filter_horizontal = ('recipients',)
    readonly_fields = ('sent_at',)
    
    def get_recipient_count(self, obj):
        return obj.recipients.count()
    get_recipient_count.short_description = 'Recipients'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__email')
    readonly_fields = ('created_at',)
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Admins see all, others see only their notifications
        if request.user.role != 'ADMIN':
            return qs.filter(user=request.user)
        return qs

@admin.register(QuickNote)
class QuickNoteAdmin(admin.ModelAdmin):
    list_display = ('user','note_text','created_at')
    list_filter = ('user','created_at')
    search_fields = ('note_text','user__email')
    readonly_fields = ('created_at',)

@admin.register(Catalog)
class CatalogAdmin(admin.ModelAdmin):
    list_display = ('name', 'catalog_type', 'user', 'is_active', 'created_at')
    list_filter = ('catalog_type', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'user__email')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Pending)
class PendingAdmin(admin.ModelAdmin):
    list_display = ('user', 'today_plan', 'original_plan_date', 'replanned_date', 'status', 'minutes_left')
    list_filter = ('status', 'original_plan_date', 'replanned_date')
    search_fields = ('user__email', 'today_plan__catalog_item__name', 'reason')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at',)

@admin.register(SubTask)
class SubTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'task', 'status', 'due_date', 'completed_at', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'task__title')
    readonly_fields = ('created_at',)

@admin.register(TodayPlan)
class TodayPlanAdmin(admin.ModelAdmin):
    list_display = ('user', 'catalog_item', 'plan_date', 'scheduled_start_time', 'scheduled_end_time', 'status', 'order_index')
    list_filter = ('status', 'plan_date', 'created_at')
    search_fields = ('user__email', 'catalog_item__name', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['plan_date', 'order_index']

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'today_plan', 'status', 'actual_start_time', 'actual_end_time', 'hours_worked', 'is_task_completed')
    list_filter = ('status', 'is_task_completed', 'actual_start_time')
    search_fields = ('user__email', 'today_plan__catalog_item__name', 'work_notes')
    readonly_fields = ('created_at', 'updated_at', 'hours_worked', 'minutes_worked')
    ordering = ['-actual_start_time']

@admin.register(DaySession)
class DaySessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_date', 'started_at', 'ended_at', 'is_active')
    list_filter = ('is_active', 'session_date')
    search_fields = ('user__email',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-session_date']
