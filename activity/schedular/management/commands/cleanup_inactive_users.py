"""
Management command to delete DAS users who are not present in HRM
This removes users who were previously synced but are no longer active in HRM
Usage: python manage.py cleanup_inactive_users [--dry-run] [--hrm-url URL]
"""
from django.core.management.base import BaseCommand
from django.db import transaction
import requests
from schedular.models import User, Employee


class Command(BaseCommand):
    help = 'Delete DAS users who are not present in the HRM active employee list'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hrm-url',
            type=str,
            default='http://localhost:8000',
            help='HRM server URL (default: http://localhost:8000)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        hrm_url = options['hrm_url']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        self.stdout.write(self.style.WARNING(f'Starting cleanup of inactive users from {hrm_url}...'))
        
        try:
            # Fetch all active employees from HRM
            response = requests.get(f'{hrm_url}/api/employees-active/', timeout=30)
            
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f'Failed to fetch employees from HRM. Status: {response.status_code}'))
                return
            
            data = response.json()
            hrm_employees = data.get('employees', [])
            
            self.stdout.write(self.style.SUCCESS(f'Found {len(hrm_employees)} active employees in HRM'))
            
            # Extract HRM employee emails as a set for efficient lookup
            hrm_emails = {emp.get('email').lower() for emp in hrm_employees if emp.get('email')}
            
            self.stdout.write(f'Valid HRM emails: {len(hrm_emails)}')
            
            # Get all users from DAS
            das_users = User.objects.all()
            total_das_users = das_users.count()
            
            self.stdout.write(f'Total DAS users: {total_das_users}')
            
            # Identify users to delete (users in DAS but not in HRM)
            users_to_delete = []
            for user in das_users:
                if user.email.lower() not in hrm_emails:
                    users_to_delete.append(user)
            
            if not users_to_delete:
                self.stdout.write(self.style.SUCCESS('✓ No users to delete. All DAS users exist in HRM.'))
                return
            
            # Display users that will be deleted
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('=' * 70))
            self.stdout.write(self.style.WARNING(f'Found {len(users_to_delete)} users to delete:'))
            self.stdout.write(self.style.WARNING('=' * 70))
            
            for user in users_to_delete:
                employee_info = ''
                try:
                    emp = user.employee_profile
                    employee_info = f' | Employee ID: {emp.employee_id} | Name: {emp.name}'
                except Employee.DoesNotExist:
                    employee_info = ' | No employee profile'
                
                self.stdout.write(f'  • {user.email}{employee_info}')
            
            self.stdout.write(self.style.WARNING('=' * 70))
            
            # Confirm deletion if not dry run
            if dry_run:
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('DRY RUN complete - No changes made'))
                return
            
            # Perform deletion
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('⚠ Starting deletion...'))
            
            deleted_count = 0
            error_count = 0
            
            # Delete each user individually (CASCADE will handle related records)
            for user in users_to_delete:
                try:
                    email = user.email
                    user_id = user.id
                    
                    # Delete user in its own transaction
                    # Related records (projects, tasks, notifications, etc.) will be cascade deleted
                    with transaction.atomic():
                        user.delete()
                    
                    deleted_count += 1
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Deleted: {email} (ID: {user_id})'))
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(f'  ✗ Error deleting {user.email}: {str(e)}'))
            
            # Summary
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.SUCCESS('Cleanup completed!'))
            self.stdout.write(self.style.SUCCESS(f'  Successfully deleted: {deleted_count} users'))
            if error_count > 0:
                self.stdout.write(self.style.ERROR(f'  Errors: {error_count}'))
            self.stdout.write(self.style.SUCCESS(f'  Remaining DAS users: {User.objects.count()}'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            
        except requests.exceptions.Timeout:
            self.stdout.write(self.style.ERROR('Request to HRM timed out'))
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Failed to connect to HRM: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Unexpected error: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
