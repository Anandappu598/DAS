from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import (
    Task, Projects, ApprovalRequest, ApprovalResponse, 
    TeamInstruction, SubTask, Notification, User, TaskAssignee
)


def send_websocket_notification(user_id, notification_data):
    """Helper function to send notification via WebSocket"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_{user_id}',
        {
            'type': 'notification_message',
            'notification': notification_data
        }
    )


def send_unread_count_update(user_id, count):
    """Helper function to send unread count update via WebSocket"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_{user_id}',
        {
            'type': 'unread_count_update',
            'count': count
        }
    )


@receiver(post_save, sender=Projects)
def project_created_notification(sender, instance, created, **kwargs):
    """Send notification when project is created"""
    if created:
        # Notify project lead if assigned
        if instance.project_lead:
            notification = Notification.objects.create(
                user=instance.project_lead,
                notification_type='PROJECT_CREATED',
                title='New Project Assigned',
                message=f'You have been assigned as lead for project: {instance.name}',
                reference_type='project',
                reference_id=instance.id
            )
            
            send_websocket_notification(instance.project_lead.id, {
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.notification_type,
                'reference_type': notification.reference_type,
                'reference_id': notification.reference_id,
                'created_at': str(notification.created_at),
            })
        
        # Notify admins if created by non-admin
        if instance.created_by and instance.created_by.role != 'ADMIN':
            admins = User.objects.filter(role='ADMIN')
            for admin in admins:
                notification = Notification.objects.create(
                    user=admin,
                    notification_type='APPROVAL_REQUESTED',
                    title='New Project Needs Approval',
                    message=f'{instance.created_by.email} created project: {instance.name}',
                    reference_type='project',
                    reference_id=instance.id
                )
                
                send_websocket_notification(admin.id, {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'type': notification.notification_type,
                    'reference_type': notification.reference_type,
                    'reference_id': notification.reference_id,
                    'created_at': str(notification.created_at),
                })


@receiver(post_save, sender=Task)
def task_status_notification(sender, instance, created, **kwargs):
    """Send notification when task is created or status changes"""
    if created:
        # Notify project lead about new task
        if instance.project.project_lead:
            notification = Notification.objects.create(
                user=instance.project.project_lead,
                notification_type='TASK_CREATED',
                title='New Task Created',
                message=f'Task "{instance.title}" created for project: {instance.project.name}',
                reference_type='task',
                reference_id=instance.id
            )
            
            send_websocket_notification(instance.project.project_lead.id, {
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.notification_type,
                'reference_type': notification.reference_type,
                'reference_id': notification.reference_id,
                'created_at': str(notification.created_at),
            })
    else:
        # Check if status changed to DONE
        try:
            old_instance = Task.objects.get(pk=instance.pk)
            if old_instance.status != 'DONE' and instance.status == 'DONE':
                # Notify project lead
                if instance.project.project_lead:
                    notification = Notification.objects.create(
                        user=instance.project.project_lead,
                        notification_type='TASK_COMPLETED',
                        title='Task Completed',
                        message=f'Task "{instance.title}" has been completed',
                        reference_type='task',
                        reference_id=instance.id
                    )
                    
                    send_websocket_notification(instance.project.project_lead.id, {
                        'id': notification.id,
                        'title': notification.title,
                        'message': notification.message,
                        'type': notification.notification_type,
                        'reference_type': notification.reference_type,
                        'reference_id': notification.reference_id,
                        'created_at': str(notification.created_at),
                    })
        except Task.DoesNotExist:
            pass


@receiver(post_save, sender=TaskAssignee)
def task_assignee_notification(sender, instance, created, **kwargs):
    """Send notification when user is assigned to a task"""
    if created:
        notification = Notification.objects.create(
            user=instance.user,
            notification_type='TASK_ASSIGNED',
            title='Task Assigned to You',
            message=f'You have been assigned to task "{instance.task.title}" as {instance.role}',
            reference_type='task',
            reference_id=instance.task.id
        )
        
        send_websocket_notification(instance.user.id, {
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.notification_type,
            'reference_type': notification.reference_type,
            'reference_id': notification.reference_id,
            'created_at': str(notification.created_at),
        })


@receiver(post_save, sender=ApprovalRequest)
def approval_request_notification(sender, instance, created, **kwargs):
    """Send notification to admins when approval request is created"""
    if created:
        # Notify all admins about the new approval request
        admins = User.objects.filter(role='ADMIN')
        for admin in admins:
            notification = Notification.objects.create(
                user=admin,
                notification_type='APPROVAL_REQUESTED',
                title='New Approval Request',
                message=f'{instance.requested_by.email} requested approval for {instance.reference_type}',
                reference_type='approval',
                reference_id=instance.id
            )
            
            send_websocket_notification(admin.id, {
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.notification_type,
                'reference_type': notification.reference_type,
                'reference_id': notification.reference_id,
                'created_at': str(notification.created_at),
            })


@receiver(post_save, sender=ApprovalResponse)
def approval_response_notification(sender, instance, created, **kwargs):
    """Send notification when approval request is approved/rejected"""
    if created:
        requester = instance.approval_request.requested_by
        
        notification_type = 'APPROVAL_APPROVED' if instance.action == 'APPROVED' else 'APPROVAL_REJECTED'
        title = 'Approval Request Approved' if instance.action == 'APPROVED' else 'Approval Request Rejected'
        
        notification = Notification.objects.create(
            user=requester,
            notification_type=notification_type,
            title=title,
            message=f'Your approval request has been {instance.action.lower()}. Comments: {instance.rejection_reason or "None"}',
            reference_type='approval',
            reference_id=instance.id
        )
        
        send_websocket_notification(requester.id, {
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.notification_type,
            'reference_type': notification.reference_type,
            'reference_id': notification.reference_id,
            'created_at': str(notification.created_at),
        })


@receiver(m2m_changed, sender=TeamInstruction.recipients.through)
def team_instruction_notification(sender, instance, action, pk_set, **kwargs):
    """Send notification when team instruction is sent to recipients"""
    if action == 'post_add':  # After recipients are added
        for user_id in pk_set:
            try:
                user = User.objects.get(id=user_id)
                notification = Notification.objects.create(
                    user=user,
                    notification_type='INSTRUCTION_RECEIVED',
                    title='New Team Instruction',
                    message=f'Subject: {instance.subject}',
                    reference_type='instruction',
                    reference_id=instance.id
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
            except User.DoesNotExist:
                pass


@receiver(post_save, sender=SubTask)
def subtask_notification(sender, instance, created, **kwargs):
    """Send notification when subtask is completed"""
    if not created:
        try:
            old_instance = SubTask.objects.get(pk=instance.pk)
            if old_instance.status != 'DONE' and instance.status == 'DONE':
                # Notify task assignees about subtask completion
                assignees = instance.task.assignees.all()
                for assignee in assignees:
                    notification = Notification.objects.create(
                        user=assignee.user,
                        notification_type='SUBTASK_COMPLETED',
                        title='SubTask Completed',
                        message=f'SubTask "{instance.title}" for task "{instance.task.title}" has been completed',
                        reference_type='subtask',
                        reference_id=instance.id
                    )
                    
                    send_websocket_notification(assignee.user.id, {
                        'id': notification.id,
                        'title': notification.title,
                        'message': notification.message,
                        'type': notification.notification_type,
                        'reference_type': notification.reference_type,
                        'reference_id': notification.reference_id,
                        'created_at': str(notification.created_at),
                    })
        except SubTask.DoesNotExist:
            pass


# Custom notification for task assignment
def notify_task_assignment(task, user):
    """Manual notification for task assignment"""
    notification = Notification.objects.create(
        user=user,
        notification_type='TASK_ASSIGNED',
        title='Task Assigned to You',
        message=f'You have been assigned to task: {task.title}',
        reference_type='task',
        reference_id=task.id
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


@receiver(post_save, sender=SubTask)
def recalculate_weights_on_subtask_create(sender, instance, created, **kwargs):
    """Automatically recalculate subtask weights when a subtask is created"""
    if created:
        # Use a flag to prevent infinite recursion
        if not hasattr(instance, '_recalculating_weights'):
            instance._recalculating_weights = True
            # Recalculate weights for all subtasks of this task
            instance.task.recalculate_subtask_weights()
            delattr(instance, '_recalculating_weights')


from django.db.models.signals import post_delete

@receiver(post_delete, sender=SubTask)
def recalculate_weights_on_subtask_delete(sender, instance, **kwargs):
    """Automatically recalculate subtask weights when a subtask is deleted"""
    try:
        # Recalculate weights for remaining subtasks of this task
        instance.task.recalculate_subtask_weights()
    except Exception:
        # Task might be deleted, ignore
        pass
