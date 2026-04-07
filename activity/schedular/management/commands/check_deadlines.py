from django.core.management.base import BaseCommand
from django.utils import timezone
from activity.schedular.models import Task, Projects, Notification
from datetime import timedelta
from activity.schedular.signals import send_websocket_notification

class Command(BaseCommand):
    help = 'Check for critical deadlines and send notifications'

    def handle(self, *args, **kwargs):
        now = timezone.now().date()
        tomorrow = now + timedelta(days=1)
        three_days = now + timedelta(days=3)

        # 1. Check Tasks due tomorrow (Urgent)
        urgent_tasks = Task.objects.filter(due_date=tomorrow, status__in=['PENDING', 'IN_PROGRESS'])
        for task in urgent_tasks:
            self.notify_assignees(task, "Task Due Tomorrow", f"Task '{task.title}' is due tomorrow!")

        # 2. Check Projects due in 3 days
        upcoming_projects = Projects.objects.filter(due_date=three_days, status='ACTIVE')
        for project in upcoming_projects:
            if project.project_lead:
                self.create_notification(
                    user=project.project_lead,
                    title="Project Deadline Approaching",
                    message=f"Project '{project.name}' is due in 3 days.",
                    ref_type='project',
                    ref_id=project.id
                )

        self.stdout.write(self.style.SUCCESS('Checked deadlines successfully'))

    def notify_assignees(self, task, title, message):
        for assignee in task.assignees.all():
            self.create_notification(assignee.user, title, message, 'task', task.id)

    def create_notification(self, user, title, message, ref_type, ref_id):
        # Avoid duplicate notifications for the same thing content on the same day
        # (Simple check: if notification with same title/user exists today)
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if Notification.objects.filter(user=user, title=title, reference_id=ref_id, created_at__gte=today_start).exists():
            return

        notification = Notification.objects.create(
            user=user,
            notification_type='TASK_UPDATED', # or custom type
            title=title,
            message=message,
            reference_type=ref_type,
            reference_id=ref_id
        )
        
        send_websocket_notification(user.id, {
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.notification_type,
            'reference_type': notification.reference_type,
            'reference_id': notification.reference_id,
            'created_at': str(notification.created_at),
        })
