from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (ProjectWorkingHoursViewSet, TeamActivityStatusViewSet, SyncHRMEmployeesViewSet,
                    CatalogProjectViewSet, CatalogTaskViewSet, ProjectCompletionLineChartViewSet, 
                    TaskCompletionLineChartViewSet, HoursCompletionLineChartViewSet, ProjectAnalyticsViewSet)
from .sso_views import SSOLoginView, InactiveUserView

router = DefaultRouter()

# ===============================================
# Authentication - Both SSO and Direct Login Enabled
# SSO: For web frontend via HRM redirect
# Direct Login: For Flutter mobile/desktop app
# Auto-Login: For HRM-DAS integration via temporary code
# ===============================================
router.register(r'login', views.LoginViewSet, basename='login')
router.register(r'auto-login', views.AutoLoginView, basename='auto-login')
router.register(r'signup', views.SignupViewSet, basename='signup')
router.register(r'verify-signup', views.VerifySignupViewSet, basename='verify-signup')
router.register(r'forgot-password', views.ForgotPasswordViewSet, basename='forgot-password')
router.register(r'reset-password', views.ResetPasswordViewSet, basename='reset-password')

router.register(r'user-preferences', views.UserPreferencesViewSet, basename='user-preferences')
router.register(r'projects', views.ProjectViewSet, basename='projects')
router.register(r'approval-requests', views.ApprovalRequestViewSet, basename='approval-requests')
router.register(r'approval-responses', views.ApprovalResponseViewSet, basename='approval-responses')
router.register(r'tasks', views.TaskViewSet, basename='tasks')
router.register(r'task-assignees', views.TaskAssigneeViewSet, basename='task-assignees')
router.register(r'sub-tasks', views.SubTaskViewSet, basename='sub-tasks')

# Planner Catalog endpoints - separate from Dashboard to prevent cross-contamination
router.register(r'catalog-projects', views.CatalogProjectViewSet, basename='catalog-projects')
router.register(r'catalog-tasks', views.CatalogTaskViewSet, basename='catalog-tasks')

router.register(r'team-instructions', views.TeamInstructionViewSet, basename='team-instructions')
router.register(r'notifications', views.NotificationViewSet, basename='notifications')
router.register(r'sticky-notes', views.StickyNoteViewSet, basename='sticky-notes')
router.register(r'catalog', views.CatalogViewSet, basename='catalog')
router.register(r'pending', views.PendingViewSet, basename='pending')

# Workflow endpoints
router.register(r'today-plan', views.TodayPlanViewSet, basename='today-plan')
router.register(r'activity-log', views.ActivityLogViewSet, basename='activity-log')
router.register(r'day-session', views.DaySessionViewSet, basename='day-session')

# Dashboard endpoints
router.register(r'dashboard', views.DashboardViewSet, basename='dashboard')

# Team overview endpoints
router.register(r'team-overview', views.TeamOverviewViewSet, basename='team-overview')

# Working hours & activity status
router.register(r'project-working-hours', ProjectWorkingHoursViewSet, basename='project-working-hours')
router.register(r'team-activity-status', TeamActivityStatusViewSet, basename='team-activity-status')

# HRM Sync endpoints
router.register(r'sync-hrm-employees', SyncHRMEmployeesViewSet, basename='sync-hrm-employees')

# Line Chart endpoints - Project and Task completion analytics
router.register(r'project-completion-chart', ProjectCompletionLineChartViewSet, basename='project-completion-chart')
router.register(r'task-completion-chart', TaskCompletionLineChartViewSet, basename='task-completion-chart')
router.register(r'hours-completion-chart', HoursCompletionLineChartViewSet, basename='hours-completion-chart')
router.register(r'daily-planner', views.DailyPlannerViewSet, basename='daily-planner')
router.register(r'analytics', views.AnalyticsViewSet, basename='analytics')
router.register(r'project-analytics', ProjectAnalyticsViewSet, basename='project-analytics')

urlpatterns = [
    # SSO Routes
    path('sso-login/', SSOLoginView.as_view(), name='sso-login'),
    path('inactive-user/', InactiveUserView.as_view(), name='inactive-user'),
    
    # API Routes
    path('', include(router.urls)),
]
