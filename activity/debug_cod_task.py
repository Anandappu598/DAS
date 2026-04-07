import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity.settings')
django.setup()

from schedular.models import Task, ApprovalRequest, User

# Search for the "COD" task specifically
try:
    task = Task.objects.get(id=67)
    print(f"TASK DETAILED INFO:")
    print(f"  ID: {task.id}")
    print(f"  Title: {task.title}")
    print(f"  Status: {task.status}")
    print(f"  Approval Status: {task.approval_status}")
    
    # All approval requests linked to this task
    print(f"\nALL APPROVAL REQUESTS FOR THIS TASK:")
    reqs = ApprovalRequest.objects.filter(reference_id=task.id, reference_type='TASK')
    if not reqs.exists():
        print("  NONE FOUND (reference_id=67, reference_type='TASK')")
    else:
        for idx, req in enumerate(reqs):
            print(f"  {idx+1}. REQ ID: {req.id}")
            print(f"     Type: {req.approval_type}")
            print(f"     Status: {req.status}")
            print(f"     By: {req.requested_by.email}")
            print(f"     At: {req.created_at}")

    # Check for approval requests where reference_type might be different?
    print(f"\nSEARCHING FOR ANY PENDING TASK COMPLETIONS IN SYSTEM:")
    all_pending = ApprovalRequest.objects.filter(approval_type='COMPLETION', status='PENDING')
    for p in all_pending:
        print(f"  System Pending: ID {p.id}, RefType {p.reference_type}, RefID {p.reference_id}")

except Task.DoesNotExist:
    print("Task 67 not found!")
