# Generated migration for ActivityLog model updates

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedular', '0020_alter_subtask_progress_weight'),
    ]

    operations = [
        migrations.AddField(
            model_name='activitylog',
            name='user_start_time',
            field=models.DateTimeField(blank=True, help_text='User-specified start time when completing', null=True),
        ),
        migrations.AddField(
            model_name='activitylog',
            name='user_end_time',
            field=models.DateTimeField(blank=True, help_text='User-specified end time when completing', null=True),
        ),
        migrations.AddField(
            model_name='activitylog',
            name='extra_hours',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Additional hours worked beyond planned time', max_digits=5),
        ),
    ]
