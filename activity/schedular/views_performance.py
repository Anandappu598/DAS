from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import datetime, timedelta, date
from .models import TodayPlan, ActivityLog, User
from .serializers_performance import (
    DailyPerformanceSerializer,
    WeeklyComparisonSerializer,
    MonthlyComparisonSerializer
)


class DailyPerformanceView(APIView):
    """
    GET: /api/daily-performance/{date}/
    
    Get planned vs achieved work for a specific date.
    Returns:
    - Planned tasks summary
    - Actual work summary
    - Comparison metrics
    - Detailed task breakdown
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, date_str=None):
        user = request.user
        
        # Parse date or use today
        try:
            if date_str:
                performance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                performance_date = date.today()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all today plans for this date
        today_plans = TodayPlan.objects.filter(
            user=user,
            plan_date=performance_date
        ).prefetch_related('activity_logs', 'catalog_item')
        
        # Get all activity logs for this date
        activity_logs = ActivityLog.objects.filter(
            user=user,
            today_plan__plan_date=performance_date
        ).prefetch_related('today_plan')
        
        # Prepare data for serializer
        serializer_data = {
            'date': performance_date,
            'user': user,
            'today_plans': list(today_plans),
            'activity_logs': list(activity_logs)
        }
        
        # Initialize serializer with the data context
        serializer = DailyPerformanceSerializer(serializer_data)
        
        # Get all serialized data
        response_data = serializer.data
        
        return Response({
            'date': str(performance_date),
            'user': user.email,
            'planned_summary': response_data.get('planned_summary', {}),
            'actual_summary': response_data.get('actual_summary', {}),
            'metrics': response_data.get('metrics', {}),
            'tasks': response_data.get('tasks', [])
        }, status=status.HTTP_200_OK)


class DateRangePerformanceView(APIView):
    """
    GET: /api/daily-performance/range/{start_date}/{end_date}/
    
    Get planned vs achieved work for a date range.
    Returns daily breakdown with comparison.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, start_date, end_date):
        user = request.user
        
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate date range
        if start > end:
            return Response(
                {'error': 'Start date must be before end date'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        days_data = []
        current_date = start
        
        while current_date <= end:
            # Get today plans
            today_plans = TodayPlan.objects.filter(
                user=user,
                plan_date=current_date
            ).prefetch_related('activity_logs')
            
            # Get activity logs
            activity_logs = ActivityLog.objects.filter(
                user=user,
                today_plan__plan_date=current_date
            )
            
            # Calculate metrics for this day
            planned_minutes = sum(plan.planned_duration_minutes for plan in today_plans)
            actual_minutes = sum(log.minutes_worked for log in activity_logs) if activity_logs else 0
            completed = sum(1 for plan in today_plans if plan.status == 'COMPLETED')
            
            days_data.append({
                'date': str(current_date),
                'planned_hours': round(planned_minutes / 60, 2),
                'actual_hours': round(actual_minutes / 60, 2),
                'total_tasks': today_plans.count(),
                'completed_tasks': completed,
                'completion_rate': round((completed / today_plans.count() * 100), 2) if today_plans.count() > 0 else 0,
                'efficiency': round((actual_minutes / planned_minutes * 100), 2) if planned_minutes > 0 else 0
            })
            
            current_date += timedelta(days=1)
        
        # Calculate totals
        total_planned = sum(day['planned_hours'] for day in days_data)
        total_actual = sum(day['actual_hours'] for day in days_data)
        total_completed = sum(day['completed_tasks'] for day in days_data)
        total_tasks = sum(day['total_tasks'] for day in days_data)
        
        return Response({
            'period': {
                'start_date': start,
                'end_date': end,
                'days': (end - start).days + 1
            },
            'user': user.email,
            'daily_breakdown': days_data,
            'totals': {
                'total_planned_hours': round(total_planned, 2),
                'total_actual_hours': round(total_actual, 2),
                'total_tasks': total_tasks,
                'total_completed': total_completed,
                'completion_rate': round((total_completed / total_tasks * 100), 2) if total_tasks > 0 else 0,
                'average_daily_planned': round(total_planned / len(days_data), 2),
                'average_daily_actual': round(total_actual / len(days_data), 2)
            }
        }, status=status.HTTP_200_OK)


class WeeklyComparisonView(APIView):
    """
    GET: /api/weekly-comparison/{year}/{week}/
    
    Get planned vs achieved work for a specific week.
    Returns daily breakdown with weekly summary.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, year=None, week=None):
        user = request.user
        
        # Use current week if not specified
        today = date.today()
        if not year or not week:
            iso_calendar = today.isocalendar()
            year = iso_calendar[0]
            week = iso_calendar[1]
        
        try:
            year = int(year)
            week = int(week)
        except (TypeError, ValueError):
            return Response(
                {'error': 'Invalid year or week number'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate week start and end
        jan4 = date(year, 1, 4)
        week_start = jan4 - timedelta(days=jan4.weekday())
        week_start = week_start + timedelta(weeks=week - 1)
        week_end = week_start + timedelta(days=6)
        
        # Get data for the week
        daily_data = {}
        
        for day_offset in range(7):
            current_date = week_start + timedelta(days=day_offset)
            
            today_plans = TodayPlan.objects.filter(
                user=user,
                plan_date=current_date
            ).prefetch_related('activity_logs')
            
            activity_logs = ActivityLog.objects.filter(
                user=user,
                today_plan__plan_date=current_date
            )
            
            planned_minutes = sum(plan.planned_duration_minutes for plan in today_plans)
            actual_minutes = sum(log.minutes_worked for log in activity_logs) if activity_logs else 0
            completed = sum(1 for plan in today_plans if plan.status == 'COMPLETED')
            
            daily_data[str(current_date)] = {
                'planned_hours': round(planned_minutes / 60, 2),
                'actual_hours': round(actual_minutes / 60, 2),
                'total_tasks': today_plans.count(),
                'completed_tasks': completed,
                'completion_rate': round((completed / today_plans.count() * 100), 2) if today_plans.count() > 0 else 0,
                'efficiency': round((actual_minutes / planned_minutes * 100), 2) if planned_minutes > 0 else 0
            }
        
        # Prepare data for serializer
        data = {
            'week_start': week_start,
            'week_end': week_end,
            'user': user,
            'daily_data': daily_data
        }
        
        serializer = WeeklyComparisonSerializer(data)
        
        return Response({
            'week': {
                'year': year,
                'week_number': week,
                'start_date': week_start,
                'end_date': week_end
            },
            'user': user.email,
            'daily_breakdown': serializer.data.get('daily_breakdown'),
            'weekly_totals': serializer.data.get('weekly_totals'),
            'weekly_metrics': serializer.data.get('weekly_metrics')
        }, status=status.HTTP_200_OK)


class MonthlyComparisonView(APIView):
    """
    GET: /api/monthly-comparison/{year}/{month}/
    
    Get planned vs achieved work for a specific month.
    Returns weekly breakdown with monthly summary.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, year=None, month=None):
        user = request.user
        
        # Use current month if not specified
        today = date.today()
        if not year or not month:
            year = today.year
            month = today.month
        
        try:
            year = int(year)
            month = int(month)
        except (TypeError, ValueError):
            return Response(
                {'error': 'Invalid year or month number'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate month
        if month < 1 or month > 12:
            return Response(
                {'error': 'Month must be between 1 and 12'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all days in the month
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
        
        month_start = date(year, month, 1)
        
        # Group by weeks
        weekly_data = {}
        current_date = month_start
        week_number = 1
        
        while current_date <= month_end:
            # Get start of week
            week_start = current_date - timedelta(days=current_date.weekday())
            week_end = week_start + timedelta(days=6)
            
            # Ensure week stays within month
            week_end = min(week_end, month_end)
            
            week_key = f"Week {week_number}"
            
            # Get data for this week (only days in current month)
            today_plans = TodayPlan.objects.filter(
                user=user,
                plan_date__range=[max(week_start, month_start), week_end],
                plan_date__month=month,
                plan_date__year=year
            ).prefetch_related('activity_logs')
            
            activity_logs = ActivityLog.objects.filter(
                user=user,
                today_plan__plan_date__range=[max(week_start, month_start), week_end],
                today_plan__plan_date__month=month,
                today_plan__plan_date__year=year
            )
            
            planned_minutes = sum(plan.planned_duration_minutes for plan in today_plans)
            actual_minutes = sum(log.minutes_worked for log in activity_logs) if activity_logs else 0
            completed = sum(1 for plan in today_plans if plan.status == 'COMPLETED')
            
            weekly_data[week_key] = {
                'planned_hours': round(planned_minutes / 60, 2),
                'actual_hours': round(actual_minutes / 60, 2),
                'total_tasks': today_plans.count(),
                'completed_tasks': completed,
                'completion_rate': round((completed / today_plans.count() * 100), 2) if today_plans.count() > 0 else 0,
                'efficiency': round((actual_minutes / planned_minutes * 100), 2) if planned_minutes > 0 else 0
            }
            
            week_number += 1
            current_date = week_end + timedelta(days=1)
        
        # Prepare data for serializer
        data = {
            'month': month,
            'year': year,
            'user': user,
            'weekly_data': weekly_data
        }
        
        serializer = MonthlyComparisonSerializer(data)
        
        return Response({
            'month': {
                'year': year,
                'month': month,
                'start_date': month_start,
                'end_date': month_end
            },
            'user': user.email,
            'weekly_breakdown': serializer.data.get('weekly_breakdown'),
            'monthly_totals': serializer.data.get('monthly_totals'),
            'monthly_metrics': serializer.data.get('monthly_metrics')
        }, status=status.HTTP_200_OK)


class PerformanceDashboardView(APIView):
    """
    GET: /api/performance-dashboard/
    
    Get comprehensive dashboard data with:
    - Today's performance
    - This week's performance
    - This month's performance
    - Key metrics and insights
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        today = date.today()
        
        # Today's data
        today_plans = TodayPlan.objects.filter(
            user=user,
            plan_date=today
        ).prefetch_related('activity_logs')
        
        today_activity = ActivityLog.objects.filter(
            user=user,
            today_plan__plan_date=today
        )
        
        # This week's data
        iso_calendar = today.isocalendar()
        jan4 = date(today.year, 1, 4)
        week_start = jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=iso_calendar[1] - 1)
        week_end = week_start + timedelta(days=6)
        
        week_plans = TodayPlan.objects.filter(
            user=user,
            plan_date__range=[week_start, week_end]
        ).prefetch_related('activity_logs')
        
        week_activity = ActivityLog.objects.filter(
            user=user,
            today_plan__plan_date__range=[week_start, week_end]
        )
        
        # This month's data
        month_start = date(today.year, today.month, 1)
        if today.month == 12:
            month_end = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(today.year, today.month + 1, 1) - timedelta(days=1)
        
        month_plans = TodayPlan.objects.filter(
            user=user,
            plan_date__range=[month_start, month_end]
        ).prefetch_related('activity_logs')
        
        month_activity = ActivityLog.objects.filter(
            user=user,
            today_plan__plan_date__range=[month_start, month_end]
        )
        
        # Helper function to calculate metrics
        def calculate_metrics(plans, activities):
            planned_mins = sum(p.planned_duration_minutes for p in plans)
            actual_mins = sum(a.minutes_worked for a in activities) if activities else 0
            completed = sum(1 for p in plans if p.status == 'COMPLETED')
            completed_rate = round((completed / plans.count() * 100), 2) if plans.count() > 0 else 0
            efficiency = round((actual_mins / planned_mins * 100), 2) if planned_mins > 0 else 0
            
            return {
                'planned_hours': round(planned_mins / 60, 2),
                'actual_hours': round(actual_mins / 60, 2),
                'completed_tasks': completed,
                'total_tasks': plans.count(),
                'completion_rate': completed_rate,
                'efficiency': efficiency
            }
        
        return Response({
            'user': user.email,
            'today': {
                **calculate_metrics(today_plans, today_activity),
                'date': today
            },
            'this_week': {
                **calculate_metrics(week_plans, week_activity),
                'start_date': week_start,
                'end_date': week_end
            },
            'this_month': {
                **calculate_metrics(month_plans, month_activity),
                'start_date': month_start,
                'end_date': month_end
            },
            'key_insights': {
                'status': 'On Track' if calculate_metrics(today_plans, today_activity)['completion_rate'] >= 75 else 'Behind Schedule',
                'avg_daily_efficiency_week': round(sum(
                    (sum(ActivityLog.objects.filter(user=user, today_plan__plan_date=week_start + timedelta(days=i)).values_list('minutes_worked', flat=True)) 
                    / (sum(TodayPlan.objects.filter(user=user, plan_date=week_start + timedelta(days=i)).values_list('planned_duration_minutes', flat=True)) or 1) * 100)
                    for i in range(7)
                ) / 7, 2),
                'pending_tasks': sum(1 for p in week_plans if p.status in ['PLANNED', 'STARTED']),
                'overdue_tasks': sum(1 for p in week_plans if p.plan_date < today and p.status != 'COMPLETED')
            }
        }, status=status.HTTP_200_OK)
