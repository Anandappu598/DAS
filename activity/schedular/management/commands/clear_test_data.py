from django.core.management.base import BaseCommand
from schedular.models import (
    Department, User, Projects, ApprovalRequest, ApprovalResponse,
    Task, TaskAssignee, SubTask, TeamInstruction, Notification,
    StickyNote, Catalog, TodayPlan, ActivityLog, Pending, DaySession,
    OTPVerification
)


class Command(BaseCommand):
    help = 'Clear ONLY test data added by populate_data (keeps original data)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Clearing ONLY populate_data test data...'))
        
        # List of test user emails created by populate_data
        test_emails = [
            'admin@company.com',
            'manager1@company.com',
            'manager2@company.com',
            'teamlead1@company.com',
            'teamlead2@company.com',
            'emp1@company.com',
            'emp2@company.com',
            'emp3@company.com',
            'emp4@company.com',
            'emp5@company.com',
        ]
        
        # Test department names
        test_departments = [
            'Engineering', 'Product Management', 'Design', 'Marketing',
            'Sales', 'Human Resources', 'Finance', 'Customer Support'
        ]
        
        # Delete test OTP verifications
        test_otp_emails = ['newuser1@company.com', 'newuser2@company.com', 'passwordreset@company.com']
        deleted_otps = OTPVerification.objects.filter(email__in=test_otp_emails).delete()
        self.stdout.write(f'Deleted {deleted_otps[0]} test OTP records')
        
        # Delete data associated with test users
        test_users = User.objects.filter(email__in=test_emails)
        
        # Delete notifications for test users
        deleted_notifications = Notification.objects.filter(user__in=test_users).delete()
        self.stdout.write(f'Deleted {deleted_notifications[0]} test notifications')
        
        # Delete team instructions sent by or to test users
        deleted_instructions = TeamInstruction.objects.filter(
            sent_by__in=test_users
        ).delete()
        self.stdout.write(f'Deleted {deleted_instructions[0]} test team instructions')
        
        # Delete projects created by test users
        test_projects = Projects.objects.filter(created_by__in=test_users)
        
        # Delete related data for test projects
        deleted_tasks = Task.objects.filter(project__in=test_projects).delete()
        self.stdout.write(f'Deleted {deleted_tasks[0]} test tasks and related data')
        
        deleted_approvals = ApprovalRequest.objects.filter(project__in=test_projects).delete()
        self.stdout.write(f'Deleted {deleted_approvals[0]} test approval requests')
        
        # Delete test projects
        deleted_projects = test_projects.delete()
        self.stdout.write(f'Deleted {deleted_projects[0]} test projects')
        
        # Delete test users
        deleted_users = test_users.delete()
        self.stdout.write(f'Deleted {deleted_users[0]} test users')
        
        # Delete test departments (only if they have no other users)
        for dept_name in test_departments:
            try:
                dept = Department.objects.get(name=dept_name)
                if dept.user_set.count() == 0:  # No users left in this department
                    dept.delete()
                    self.stdout.write(f'Deleted empty test department: {dept_name}')
            except Department.DoesNotExist:
                pass
        
        self.stdout.write(self.style.SUCCESS('✅ Test data from populate_data cleared!'))
        self.stdout.write(self.style.SUCCESS('Original data (if any) has been preserved.'))
