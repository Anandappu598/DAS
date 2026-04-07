import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity.settings')
django.setup()

from schedular.models import Task, ApprovalRequest

# Fix Task 67 (COD)
try:
    task = Task.objects.get(id=67)
    print(f"Fixing Task: {task.title} (ID: 67)")
    print(f"  Old Status: {task.status}, Old Approval Status: {task.approval_status}")
    
    # Since it was rejected (Req 69), it should be IN_PROGRESS and REJECTED
    task.status = 'IN_PROGRESS'
    task.approval_status = 'REJECTED'
    task.save()
    
    print(f"  New Status: {task.status}, New Approval Status: {task.approval_status}")
    print("Task 67 fixed successfully.")
    
except Task.DoesNotExist:
    print("Task 67 not found!")

# Optional: Clean up any other orphaned "pending_completion" tasks
orphans = Task.objects.filter(approval_status='pending_completion').exclude(
    id__in=ApprovalRequest.objects.filter(
        reference_type='TASK', 
        approval_type='COMPLETION', 
        status='PENDING'
    ).values_list('reference_id', flat=True)
)

if orphans.exists():
    print(f"\nFound {orphans.count()} other orphaned 'pending_completion' tasks. Fixing them...")
    for t in orphans:
        print(f" - Fixing Task {t.id}: {t.title}")
        t.approval_status = 'REJECTED' # Best guess: if no pending req, treat as rejected/rework
        t.status = 'IN_PROGRESS'
        t.save()
else:
    print("\nNo other orphaned 'pending_completion' tasks found.")
