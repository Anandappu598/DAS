
import os
import django
import sys

# Setup Django
sys.path.append('c:/flutter_apps/MERIDA PROJECTS/HRM_DAS 1/DAS_Backend/activity')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity.settings')
django.setup()

from schedular.models import User, Projects, Task, TaskAssignee
from django.db.models import Q

def check_all_data():
    admins = User.objects.filter(role='ADMIN')
    print(f"Total Admins: {admins.count()}")
    for admin in admins:
        print(f"Admin: {admin.email} (ID: {admin.id})")
        
        # My Projects logic
        my_projects = Projects.objects.filter(
            Q(created_by=admin) | 
            Q(assignees=admin) |
            Q(project_lead=admin) | 
            Q(handled_by=admin) |
            Q(tasks__assignees__user=admin)
        ).distinct()
        
        print(f"\n--- MY PROJECTS (Total: {my_projects.count()}) ---")
        completed_my_projects = my_projects.filter(status='COMPLETED')
        print(f"COMPLETED MY PROJECTS: {completed_my_projects.count()}")
        for p in completed_my_projects:
            print(f"- {p.name} (Completed: {p.completed_date})")

        # Total Projects (if Admin)
        total_projects = Projects.objects.all()
        print(f"\n--- ALL PROJECTS (Total: {total_projects.count()}) ---")
        completed_total = total_projects.filter(status='COMPLETED')
        print(f"COMPLETED ALL PROJECTS: {completed_total.count()}")
        for p in completed_total:
            print(f"- {p.name} (Completed: {p.completed_date})")

        # Task Efficiency check
        my_tasks = Task.objects.filter(
            Q(assignees__user=admin) | 
            Q(project__created_by=admin)
        ).distinct()
        print(f"\n--- MY TASKS (Total: {my_tasks.count()}) ---")
        print(f"DONE MY TASKS: {my_tasks.filter(status='DONE').count()}")
        for t in my_tasks.filter(status='DONE'):
             print(f"- {t.title} (Completed: {t.completed_at})")

if __name__ == "__main__":
    check_all_data()
