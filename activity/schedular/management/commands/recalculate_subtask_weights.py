from django.core.management.base import BaseCommand
from schedular.models import Task


class Command(BaseCommand):
    help = 'Recalculate subtask weights for all tasks'

    def handle(self, *args, **options):
        tasks = Task.objects.all()
        total_tasks = tasks.count()
        updated_count = 0

        self.stdout.write(self.style.WARNING(f'Found {total_tasks} tasks'))
        
        for task in tasks:
            subtasks_count = task.subtasks.count()
            if subtasks_count > 0:
                self.stdout.write(f'Processing task "{task.title}" with {subtasks_count} subtasks...')
                task.recalculate_subtask_weights()
                updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully recalculated weights for {updated_count} tasks'
            )
        )
