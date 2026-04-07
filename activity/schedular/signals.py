from django.db.models.signals import post_save, m2m_changed
from django.db import transaction

from django.dispatch import receiver
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import (
    Task, Projects, ApprovalRequest, ApprovalResponse, 
    TeamInstruction, SubTask, Notification, User, TaskAssignee,
    StickyNote, Catalog, TodayPlan, ActivityLog, Department, Pending, DaySession
)
from .utils import send_team_instruction_email


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


def send_to_role(role, notification_data):
    """Broadcast notification to all users with a specific role"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_role_{role}',
        {
            'type': 'notification_message',
            'notification': notification_data
        }
    )


def send_to_department(dept_id, notification_data):
    """Broadcast notification to all users in a specific department"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_dept_{dept_id}',
        {
            'type': 'notification_message',
            'notification': notification_data
        }
    )


@receiver(post_save, sender=Projects)
def project_notification(sender, instance, created, **kwargs):
    """Send notification when project is created or updated"""
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
            
            try:
                send_websocket_notification(instance.project_lead.id, {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'type': notification.notification_type,
                    'reference_type': notification.reference_type,
                    'reference_id': notification.reference_id,
                    'created_at': str(notification.created_at),
                })
            except Exception as e:
                print(f"WebSocket notification error in signal: {e}")
        
        # Broadcast creation to all admins
        try:
            send_to_role('ADMIN', {
                'id': f"proj_new_{instance.id}",
                'title': 'New Project Created',
                'message': f'{instance.created_by.email if instance.created_by else "A user"} created project: {instance.name}',
                'type': 'PROJECT_CREATED',
                'reference_type': 'project',
                'reference_id': instance.id,
                'created_at': str(timezone.now()),
            })
        except Exception as e:
            print(f"WebSocket broadcast error in signal: {e}")
    else:
        # Notify relevants on update
        notif_data = {
            'id': f"proj_upd_{instance.id}",
            'title': 'Project Updated',
            'message': f'Project "{instance.name}" has been updated.',
            'type': 'PROJECT_UPDATED',
            'reference_type': 'project',
            'reference_id': instance.id,
            'created_at': str(timezone.now()),
        }
        
        # Notify lead
        if instance.project_lead:
            send_websocket_notification(instance.project_lead.id, notif_data)
        
        # Notify admins
        send_to_role('ADMIN', notif_data)


@receiver(post_save, sender=Task)
def task_status_notification(sender, instance, created, **kwargs):
    """Send notification when task is created or status changes"""
    if created:
        def notify_creation():
            # Refresh instance to get subtasks created in the same transaction
            try:
                task = Task.objects.get(pk=instance.pk)
                subtasks = task.subtasks.all()
                milestone_list = ", ".join([st.title for st in subtasks])
                
                message = f'New task "{task.title}" has been created for project: {task.project.name}.'
                if milestone_list:
                    message += f'\nMilestones: {milestone_list}'
                
                # Notify project lead
                if task.project.project_lead:
                    notification = Notification.objects.create(
                        user=task.project.project_lead,
                        notification_type='TASK_CREATED',
                        title='New Task Created',
                        message=message,
                        reference_type='task',
                        reference_id=task.id
                    )
                    
                    send_websocket_notification(task.project.project_lead.id, {
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
            except Exception as e:
                print(f"Error in deferred task notification: {e}")

        # Use on_commit to ensure subtasks (milestones) are available
        transaction.on_commit(notify_creation)
    else:
        # Check if significant fields changed (status, priority, due_date)
        # We can't easily check 'old' values in post_save without a trick, 
        # but we can at least avoid notifying on EVERY save if we wanted to.
        # For now, let's just make the message more concise.
        
        notif_data = {
            'id': f"task_upd_{instance.id}",
            'title': 'Task Updated',
            'message': f'Task "{instance.title}" in project "{instance.project.name}" has been updated to {instance.status}.',
            'type': 'TASK_UPDATED',
            'reference_type': 'task',
            'reference_id': instance.id,
            'created_at': str(timezone.now()),
        }
        
        # Notify lead
        if instance.project.project_lead:
            send_websocket_notification(instance.project.project_lead.id, notif_data)
            
        # Notify all assignees
        for assignee in instance.assignees.all():
            send_websocket_notification(assignee.user.id, notif_data)


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
        
        try:
            send_websocket_notification(instance.user.id, {
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.notification_type,
                'reference_type': notification.reference_type,
                'reference_id': notification.reference_id,
                'created_at': str(notification.created_at),
            })
        except Exception as e:
            print(f"WebSocket notification error in signal: {e}")


@receiver(post_save, sender=ApprovalRequest)
def approval_request_notification(sender, instance, created, **kwargs):
    """Send notification to admins when approval request is created"""
    if created:
        # Determine specific message based on approval type
        title = 'New Approval Request'
        message = f'{instance.requested_by.email} requested approval for {instance.reference_type}'
        
        if instance.approval_type == 'CREATION':
            title = f'New {instance.reference_type.title()} Creation'
            if instance.reference_type == 'PROJECT':
                try:
                    project = Projects.objects.get(id=instance.reference_id)
                    message = f'{instance.requested_by.email} created new project "{project.name}" pending approval.'
                except Projects.DoesNotExist:
                    pass
            elif instance.reference_type == 'TASK':
                try:
                    task = Task.objects.get(id=instance.reference_id)
                    message = f'{instance.requested_by.email} created new task "{task.title}" pending approval.'
                except Task.DoesNotExist:
                    pass
        elif instance.approval_type == 'COMPLETION':
            title = f'{instance.reference_type.title()} Completion Request'
            if instance.reference_type == 'PROJECT':
                try:
                    project = Projects.objects.get(id=instance.reference_id)
                    message = f'{instance.requested_by.email} requested to mark project "{project.name}" as completed.'
                except Projects.DoesNotExist:
                    pass
        
        # Notify all approvers about the new approval request
        approvers = User.objects.filter(role__in=['ADMIN', 'MANAGER', 'TEAMLEAD'])
        for admin in approvers:
            notification = Notification.objects.create(
                user=admin,
                notification_type='APPROVAL_REQUESTED',
                title=title,
                message=message,
                reference_type='approval',
                reference_id=instance.id
            )
            
            try:
                send_websocket_notification(admin.id, {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'type': notification.notification_type,
                    'reference_type': notification.reference_type,
                    'reference_id': notification.reference_id,
                    'created_at': str(notification.created_at),
                })
            except Exception as e:
                print(f"WebSocket notification error in signal: {e}")


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
            reference_type=instance.approval_request.reference_type.lower(),
            reference_id=instance.approval_request.reference_id
        )
        
        # WebSocket notification moved carefully to the end of views.py (ApprovalResponseViewSet)
        # to guarantee the frontend syncs ONLY AFTER all task and subtask DB instances have completely updated.


@receiver(m2m_changed, sender=TeamInstruction.recipients.through)
def team_instruction_notification(sender, instance, action, pk_set, **kwargs):
    """Send notification when team instruction is sent to recipients"""
    if action == 'post_add':  # After recipients are added
        for user_id in pk_set:
            try:
                user = User.objects.get(id=user_id)
                
                # Create in-app notification
                notification = Notification.objects.create(
                    user=user,
                    notification_type='INSTRUCTION_RECEIVED',
                    title='New Team Instruction',
                    message=f'Subject: {instance.subject}',
                    reference_type='instruction',
                    reference_id=instance.id
                )
                
                # Send WebSocket notification (real-time)
                try:
                    send_websocket_notification(user.id, {
                        'id': notification.id,
                        'title': notification.title,
                        'message': notification.message,
                        'type': notification.notification_type,
                        'reference_type': notification.reference_type,
                        'reference_id': notification.reference_id,
                        'created_at': str(notification.created_at),
                    })
                except Exception as e:
                    print(f"WebSocket notification error in signal: {e}")
                
                # Send Email notification
                recipient_name = user.email.split('@')[0].replace('.', ' ').title()
                try:
                    if hasattr(user, 'employee_profile') and user.employee_profile:
                        recipient_name = user.employee_profile.name
                except:
                    pass
                
                sent_by_name = instance.sent_by.email.split('@')[0].replace('.', ' ').title()
                try:
                    if hasattr(instance.sent_by, 'employee_profile') and instance.sent_by.employee_profile:
                        sent_by_name = instance.sent_by.employee_profile.name
                except:
                    pass
                
                send_team_instruction_email(
                    recipient_email=user.email,
                    recipient_name=recipient_name,
                    subject=instance.subject,
                    instructions=instance.instructions,
                    project_name=instance.project.name if instance.project else "General",
                    sent_by_name=sent_by_name
                )
                
            except User.DoesNotExist:
                pass


@receiver(post_save, sender=SubTask)
def subtask_notification(sender, instance, created, **kwargs):
    """Send notification when subtask is created or completed"""
    from datetime import timedelta
    if created:
        # Avoid sending redundant individual notifications if the parent task was JUST created
        # (The Task creation notification will handle including these milestones)
        if timezone.now() - instance.task.created_at < timedelta(seconds=5):
            return

        # Notify task assignees about new subtask
        notif_data = {
            'id': f"subtask_new_{instance.id}",
            'title': 'New Milestone Added',
            'message': f'New milestone "{instance.title}" added to task "{instance.task.title}".',
            'type': 'SUBTASK_CREATED',
            'reference_type': 'subtask',
            'reference_id': instance.id,
            'created_at': str(timezone.now()),
        }
        for assignee in instance.task.assignees.all():
            send_websocket_notification(assignee.user.id, notif_data)
    else:
        try:
            old_instance = SubTask.objects.get(pk=instance.pk)
            if old_instance.status != 'DONE' and instance.status == 'DONE':
                # Notify task assignees about subtask completion
                notif_data = {
                    'id': f"subtask_done_{instance.id}",
                    'title': 'SubTask Completed',
                    'message': f'SubTask "{instance.title}" for task "{instance.task.title}" has been completed',
                    'type': 'SUBTASK_COMPLETED',
                    'reference_type': 'subtask',
                    'reference_id': instance.id,
                    'created_at': str(timezone.now()),
                }
                for assignee in instance.task.assignees.all():
                    send_websocket_notification(assignee.user.id, notif_data)
                
                # Check if all subtasks are completed logic (existing comment)
                pass
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

@receiver(post_save, sender=StickyNote)
def sticky_note_notification(sender, instance, created, **kwargs):
    """Only notify on new shared sticky notes, not personal ones or updates"""
    # Personal notes don't need notifications — skip to reduce noise
    pass


@receiver(post_save, sender=Catalog)
def catalog_notification(sender, instance, created, **kwargs):
    """Send notification only when a new catalog item is created"""
    if not created:
        return  # Skip updates to reduce noise
    
    notif_data = {
        'id': f"cat_new_{instance.id}",
        'title': 'New Activity Added to Catalog',
        'message': f'"{instance.name}" has been added to your activity catalog.',
        'type': 'CATALOG_UPDATED',
        'reference_type': 'catalog',
        'reference_id': instance.id,
        'created_at': str(timezone.now()),
    }
    if instance.user:
        send_websocket_notification(instance.user.id, notif_data)


@receiver(post_save, sender=TodayPlan)
def today_plan_notification(sender, instance, created, **kwargs):
    """Notify only on meaningful plan events, not every minor update"""
    if not created:
        return  # Skip updates — they happen frequently with reordering, etc.
    
    # Get a meaningful task name
    task_name = instance.catalog_item.name if instance.catalog_item else instance.custom_title or 'a task'
    
    notif_data = {
        'id': f"plan_new_{instance.id}",
        'title': 'Task Added to Today\'s Plan',
        'message': f'"{task_name}" has been added to your plan for {instance.plan_date}.',
        'type': 'TODAY_PLAN_UPDATED',
        'reference_type': 'today_plan',
        'reference_id': instance.id,
        'created_at': str(timezone.now()),
    }
    if instance.user:
        send_websocket_notification(instance.user.id, notif_data)


@receiver(post_save, sender=ActivityLog)
def activity_log_notification(sender, instance, created, **kwargs):
    """Smart notification for activity log — detect unplanned starts, completions, etc."""
    # Get meaningful task name
    task_name = 'a task'
    is_unplanned = False
    try:
        plan = instance.today_plan
        if plan:
            task_name = plan.catalog_item.name if plan.catalog_item else plan.custom_title or 'a task'
            # Detect unplanned tasks
            custom_title = plan.custom_title or ''
            description = plan.description or ''
            notes = plan.notes or ''
            if 'Unplanned' in custom_title or 'Unplanned' in description or 'Unplanned' in notes:
                is_unplanned = True
                task_name = task_name.replace('[Unplanned] ', '')
    except Exception:
        pass
    
    if created:
        # Task started
        if is_unplanned:
            notif_data = {
                'id': f"act_unplanned_{instance.id}",
                'title': '⚡ Unplanned Work Started',
                'message': f'You started working on "{task_name}" without planning it first.',
                'type': 'ACTIVITY_UNPLANNED',
                'reference_type': 'activity_log',
                'reference_id': instance.id,
                'created_at': str(timezone.now()),
            }
        else:
            notif_data = {
                'id': f"act_started_{instance.id}",
                'title': 'Work Started',
                'message': f'You started working on "{task_name}". Stay focused!',
                'type': 'ACTIVITY_STARTED',
                'reference_type': 'activity_log',
                'reference_id': instance.id,
                'created_at': str(timezone.now()),
            }
        
        if instance.user:
            send_websocket_notification(instance.user.id, notif_data)
    else:
        # Activity updated (stopped/completed)
        if instance.status == 'COMPLETED' and instance.is_task_completed:
            notif_data = {
                'id': f"act_done_{instance.id}",
                'title': '✅ Task Completed',
                'message': f'Great job! You completed "{task_name}".',
                'type': 'ACTIVITY_COMPLETED',
                'reference_type': 'activity_log',
                'reference_id': instance.id,
                'created_at': str(timezone.now()),
            }
            if instance.user:
                send_websocket_notification(instance.user.id, notif_data)
        elif instance.status == 'PENDING':
            # Don't send — the Pending signal will handle this
            pass


@receiver(post_save, sender=Department)
def department_notification(sender, instance, created, **kwargs):
    """Broadcast notification when department is created"""
    if not created:
        return  # Skip updates to reduce noise
    
    notif_data = {
        'id': f"dept_new_{instance.id}",
        'title': 'New Department Created',
        'message': f'Department "{instance.name}" has been created.',
        'type': 'DEPARTMENT_UPDATED',
        'reference_type': 'department',
        'reference_id': instance.id,
        'created_at': str(timezone.now()),
    }
    send_to_role('ADMIN', notif_data)


@receiver(post_save, sender=User)
def user_profile_notification(sender, instance, created, **kwargs):
    """Notify user of role/department changes only"""
    if not created:
        notif_data = {
            'id': f"user_upd_{instance.id}",
            'title': 'Profile Updated',
            'message': 'Your profile or role has been updated by an administrator.',
            'type': 'USER_UPDATED',
            'reference_type': 'user',
            'reference_id': instance.id,
            'created_at': str(timezone.now()),
        }
        send_websocket_notification(instance.id, notif_data)


@receiver(post_save, sender=Pending)
def pending_item_notification(sender, instance, created, **kwargs):
    """Notify owner with meaningful message when item is moved to pending"""
    if not created:
        return  # Only notify on creation

    # Get meaningful task name
    task_name = 'a task'
    try:
        plan = instance.today_plan
        if plan:
            task_name = plan.catalog_item.name if plan.catalog_item else plan.custom_title or 'a task'
            task_name = task_name.replace('[Unplanned] ', '')
    except Exception:
        pass

    mins_left = instance.minutes_left or 0
    
    notif_data = {
        'id': f"pend_new_{instance.id}",
        'title': '⏸ Task Moved to Pending',
        'message': f'"{task_name}" has been paused with {mins_left} min remaining. Don\'t forget to reschedule it!',
        'type': 'PENDING_UPDATED',
        'reference_type': 'pending',
        'reference_id': instance.id,
        'created_at': str(timezone.now()),
    }
    if instance.user:
        send_websocket_notification(instance.user.id, notif_data)


@receiver(post_save, sender=DaySession)
def day_session_notification(sender, instance, created, **kwargs):
    """Notify relevant parties of work day session start/end"""
    if instance.is_active:
        title = '🟢 Work Day Started'
        message = f'Your work session for {instance.session_date} has started. Have a productive day!'
    else:
        title = '🔴 Work Day Ended'
        message = f'Your work session for {instance.session_date} has ended. Great work today!'
    
    notif_data = {
        'id': f"session_{instance.id}",
        'title': title,
        'message': message,
        'type': 'SESSION_UPDATED',
        'reference_type': 'day_session',
        'reference_id': instance.id,
        'created_at': str(timezone.now()),
    }
    # Notify user
    send_websocket_notification(instance.user.id, notif_data)
    
    # Notify admins/managers when an employee starts/ends their day
    if instance.user.role == 'EMPLOYEE':
        user_name = instance.user.email.split('@')[0].replace('.', ' ').title()
        try:
            if hasattr(instance.user, 'employee_profile') and instance.user.employee_profile:
                user_name = instance.user.employee_profile.name
        except Exception:
            pass

        if instance.is_active:
            admin_msg = f'{user_name} started their work day.'
        else:
            admin_msg = f'{user_name} ended their work day.'

        admin_data = {
            'id': f"session_admin_{instance.id}",
            'title': f'Team Update: {user_name}',
            'message': admin_msg,
            'type': 'SESSION_UPDATED',
            'reference_type': 'day_session',
            'reference_id': instance.id,
            'created_at': str(timezone.now()),
        }
        send_to_role('ADMIN', admin_data)
        
        # Also notify the user's manager/team lead
        try:
            if instance.user.department:
                managers = User.objects.filter(
                    role__in=['MANAGER', 'TEAMLEAD'],
                    department=instance.user.department
                ).exclude(id=instance.user.id)
                for mgr in managers:
                    send_websocket_notification(mgr.id, admin_data)
        except Exception:
            pass

