from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from activity.schedular.models import User, Projects, Task, SubTask, TaskAssignee

class Command(BaseCommand):
    help = 'Seeds database with initial Project, Task, and Subtasks for every user if they do not exist'

    def handle(self, *args, **kwargs):
        users = User.objects.all()
        self.stdout.write(f"Found {users.count()} users. Starting seeding process...")

        for user in users:
            self.seed_for_user(user)

        self.stdout.write(self.style.SUCCESS('Successfully seeded data for all users'))

    def seed_for_user(self, user):
        # 1. Ensure User has at least one Project (lead or handled by)
        # Check if user leads or handles any project
        project = Projects.objects.filter(project_lead=user).first() or \
                  Projects.objects.filter(handled_by=user).first() or \
                  Projects.objects.filter(created_by=user).first()

        if not project:
            self.stdout.write(f"Creating 'Onboarding Project' for {user.email}")
            project = Projects.objects.create(
                name=f"Onboarding - {user.email.split('@')[0]}",
                status='ACTIVE',
                project_lead=user,
                handled_by=user,
                created_by=user,
                start_date=timezone.now().date(),
                due_date=timezone.now().date() + timedelta(days=30),
                description="Welcome to your new workspace! This project contains tasks to help you get started.",
                working_hours=40,
                duration=30,
                is_approved=True
            )
        else:
            self.stdout.write(f"User {user.email} already has project: {project.name}")

        # 2. Ensure Project has at least one Task
        task = Task.objects.filter(project=project).first()
        
        if not task:
            self.stdout.write(f"  Creating 'Setup Workspace' task for {user.email}")
            task = Task.objects.create(
                title="Setup Workspace",
                project=project,
                project_lead=user,
                task_type='STANDARD',
                priority='HIGH',
                status='IN_PROGRESS',
                start_date=timezone.now().date(),
                due_date=timezone.now().date() + timedelta(days=7),
            )
            # Assign user to task
            TaskAssignee.objects.get_or_create(
                task=task,
                user=user,
                defaults={'role': 'LEAD'}
            )
        else:
             self.stdout.write(f"  Project {project.name} already has task: {task.title}")

        # 3. Ensure Task has 3-4 Subtasks
        subtask_count = SubTask.objects.filter(task=task).count()
        
        if subtask_count < 3:
            needed = random.randint(3, 4) - subtask_count
            self.stdout.write(f"  Creating {needed} subtasks for task: {task.title}")
            
            subtask_titles = [
                "Complete Profile Information",
                "Review Documentation",
                "Configure Notification Settings",
                "Join Team Channel"
            ]
            
            # Filter out existing titles to avoid duplicates if possible
            existing_titles = set(SubTask.objects.filter(task=task).values_list('title', flat=True))
            available_titles = [t for t in subtask_titles if t not in existing_titles]
            
            # If we ran out of unique titles, generate generic ones
            while len(available_titles) < needed:
                available_titles.append(f"Subtask {subtask_count + len(available_titles) + 1}")

            for i in range(needed):
                title = available_titles[i]
                SubTask.objects.create(
                    task=task,
                    title=title,
                    status='PENDING',
                    progress_weight=25,
                    due_date=task.due_date
                )
        else:
            self.stdout.write(f"  Task {task.title} already has {subtask_count} subtasks")
