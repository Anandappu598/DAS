from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'login', views.LoginViewSet, basename='login')
router.register(r'signup', views.SignupViewSet, basename='signup')
router.register(r'verify-signup', views.VerifySignupViewSet, basename='verify-signup')
router.register(r'forgot-password', views.ForgotPasswordViewSet, basename='forgot-password')
router.register(r'reset-password', views.ResetPasswordViewSet, basename='reset-password')
router.register(r'projects', views.ProjectViewSet, basename='projects')
router.register(r'approval-requests', views.ApprovalRequestViewSet, basename='approval-requests')
router.register(r'approval-responses', views.ApprovalResponseViewSet, basename='approval-responses')
router.register(r'tasks', views.TaskViewSet, basename='tasks')
router.register(r'task-assignees', views.TaskAssigneeViewSet, basename='task-assignees')
router.register(r'sub-tasks', views.SubTaskViewSet, basename='sub-tasks')
router.register(r'quick-notes', views.QuickNoteViewSet, basename='quick-notes')
router.register(r'catalog', views.CatalogViewSet, basename='catalog')
router.register(r'pending', views.PendingViewSet, basename='pending')

# Workflow endpoints
router.register(r'today-plan', views.TodayPlanViewSet, basename='today-plan')
router.register(r'activity-log', views.ActivityLogViewSet, basename='activity-log')
router.register(r'day-session', views.DaySessionViewSet, basename='day-session')

urlpatterns = [
    path('', include(router.urls)),
]
