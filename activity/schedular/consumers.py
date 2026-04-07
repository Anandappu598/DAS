import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]
        
        # Try to authenticate with token in query string if anonymous
        if self.user.is_anonymous:
            try:
                query_string = self.scope['query_string'].decode()
                params = parse_qs(query_string)
                token = params.get('token', [None])[0]
                
                if token:
                    access_token = AccessToken(token)
                    user_id = access_token['user_id']
                    self.user = await database_sync_to_async(User.objects.get)(id=user_id)
            except (InvalidToken, TokenError, User.DoesNotExist):
                await self.close()
                return
        
        # Reject connection if still unauthenticated
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Individual group
        self.group_name = f'notifications_{self.user.id}'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Role-based group (ADMIN, MANAGER, etc.)
        self.role_group_name = f'notifications_role_{self.user.role}'
        await self.channel_layer.group_add(
            self.role_group_name,
            self.channel_name
        )

        # Department-based group if available
        self.dept_group_name = None
        if hasattr(self.user, 'department') and self.user.department:
            self.dept_group_name = f'notifications_dept_{self.user.department.id}'
            await self.channel_layer.group_add(
                self.dept_group_name,
                self.channel_name
            )
        
        # Accept the WebSocket connection
        await self.accept()
        
        # Send initial unread count when user connects
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave all groups
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        
        if hasattr(self, 'role_group_name'):
            await self.channel_layer.group_discard(
                self.role_group_name,
                self.channel_name
            )
            
        if hasattr(self, 'dept_group_name') and self.dept_group_name:
            await self.channel_layer.group_discard(
                self.dept_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle messages received from WebSocket"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'mark_read':
                # Mark notification as read
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_notification_read(notification_id)
                    await self.send(text_data=json.dumps({
                        'type': 'marked_read',
                        'notification_id': notification_id
                    }))
            
            elif action == 'get_unread_count':
                # Send current unread count
                unread_count = await self.get_unread_count()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': unread_count
                }))
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    async def notification_message(self, event):
        """Receive notification from group and send to WebSocket"""
        # Send notification to WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))
    
    async def unread_count_update(self, event):
        """Send updated unread count to WebSocket client"""
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': event['count']
        }))
    
    @database_sync_to_async
    def get_unread_count(self):
        """Get count of unread notifications for the user"""
        from .models import Notification
        return Notification.objects.filter(
            user=self.user,
            is_read=False
        ).count()
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read"""
        from .models import Notification
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=self.user
            )
            notification.is_read = True
            notification.save()
            return True
        except Notification.DoesNotExist:
            return False
