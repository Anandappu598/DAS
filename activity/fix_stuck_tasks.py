import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'activity.settings'
django.setup()

from schedular.models import Task, SubTask

# Find tasks with approval_status='APPROVED' or 'approved' but incomplete milestones
stuck_tasks = Task.objects.filter(approval_status__iexact='approved')
fixed = 0
for task in stuck_tasks:
    pending = task.subtasks.exclude(status='DONE').count()
    total = task.subtasks.count()
    if total > 0 and pending > 0:
        # Has incomplete milestones - reset to task bucket
        task.approval_status = None
        task.status = 'PENDING'
        task.completed_at = None
        task.save()
        fixed += 1
        print(f'FIXED: Task {task.id} "{task.title}" ({pending}/{total} milestones pending) -> back to TASK BUCKET')
    else:
        print(f'OK: Task {task.id} "{task.title}" (all milestones done or no milestones)')

print(f'\nTotal fixed: {fixed}')
