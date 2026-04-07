"""
Custom serializer fields for timezone handling
"""
from rest_framework import serializers
from django.utils import timezone
import pytz


class LocalDateTimeField(serializers.DateTimeField):
    """
    Custom DateTimeField that returns datetime in the local timezone (Asia/Kolkata)
    instead of UTC
    """
    def to_representation(self, value):
        """
        Convert UTC datetime to local timezone before serialization
        """
        if value is None:
            return None
        
        # Ensure the datetime is timezone-aware
        if timezone.is_naive(value):
            value = timezone.make_aware(value)
        
        # Convert to local timezone (from settings.TIME_ZONE)
        local_tz = pytz.timezone('Asia/Kolkata')
        local_time = value.astimezone(local_tz)
        
        # Return in ISO format with timezone
        return local_time.isoformat()
