from rest_framework import serializers
from .models import TodayPlan, ActivityLog, User, DailyPlanner
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime


class TaskDetailSerializer(serializers.ModelSerializer):
    """Detailed task information with activity logs"""
    task_name = serializers.SerializerMethodField()
    activity_count = serializers.SerializerMethodField()
    total_worked_minutes = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = TodayPlan
        fields = [
            'id', 'task_name', 'planned_duration_minutes', 'quadrant',
            'status', 'status_display', 'is_unplanned', 'activity_count',
            'total_worked_minutes', 'notes'
        ]
    
    def get_task_name(self, obj):
        if obj.catalog_item:
            return obj.catalog_item.name
        return obj.custom_title or "Untitled Task"
    
    def get_activity_count(self, obj):
        return obj.activity_logs.count()
    
    def get_total_worked_minutes(self, obj):
        total = obj.activity_logs.aggregate(Sum('minutes_worked'))['minutes_worked__sum'] or 0
        return total
    
    def get_status_display(self, obj):
        return obj.get_status_display()


class DailyPerformanceSerializer(serializers.Serializer):
    """Daily planned vs achieved analysis"""
    date = serializers.DateField()
    user = serializers.StringRelatedField()
    
    # Planned Tasks Summary
    planned_summary = serializers.SerializerMethodField()
    
    # Actual Work Summary
    actual_summary = serializers.SerializerMethodField()
    
    # Comparison Metrics
    metrics = serializers.SerializerMethodField()
    
    # Detailed Tasks
    tasks = serializers.SerializerMethodField()
    
    def get_planned_summary(self, data):
        """Get planned tasks information with detailed breakdown"""
        today_plans = data.get('today_plans', [])
        activity_logs = data.get('activity_logs', [])
        user = data.get('user')
        date = data.get('date')
        
        # Get DailyPlanner data for this day
        daily_planner = None
        daily_plan_hours = None
        try:
            daily_planner = DailyPlanner.objects.get(user=user, date=date)
            daily_plan_hours = daily_planner.planned_hours
        except DailyPlanner.DoesNotExist:
            # If no daily planner entry, calculate from tasks
            daily_plan_hours = None
        
        # Separate planned and unplanned tasks based on ActivityLog.is_unplanned
        # A task is considered unplanned if it has an activity log marked as unplanned
        activity_log_dict = {log.today_plan_id: log.is_unplanned for log in activity_logs}
        
        planned_tasks_list = [plan for plan in today_plans if activity_log_dict.get(plan.id, False) == False]
        unplanned_tasks_list = [plan for plan in today_plans if activity_log_dict.get(plan.id, False) == True]
        
        # Calculate minutes
        planned_minutes = sum(plan.planned_duration_minutes for plan in planned_tasks_list)
        unplanned_minutes = sum(plan.planned_duration_minutes for plan in unplanned_tasks_list)
        total_minutes = planned_minutes + unplanned_minutes
        
        # Build detailed task lists
        def build_task_details(tasks):
            return [
                {
                    'id': task.id,
                    'name': task.catalog_item.name if task.catalog_item else task.custom_title,
                    'planned_minutes': task.planned_duration_minutes,
                    'planned_hours': round(task.planned_duration_minutes / 60, 2),
                    'status': task.status,
                    'quadrant': task.quadrant,
                    'notes': task.notes
                }
                for task in tasks
            ]
        
        quadrant_breakdown = {}
        for quad_code, quad_name in TodayPlan.QUADRANT_CHOICES:
            count = sum(1 for plan in today_plans if plan.quadrant == quad_code)
            minutes = sum(plan.planned_duration_minutes for plan in today_plans if plan.quadrant == quad_code)
            quadrant_breakdown[quad_code] = {
                'name': quad_name,
                'count': count,
                'planned_minutes': minutes
            }
        
        status_breakdown = {}
        for status_code, status_name in TodayPlan.STATUS_CHOICES:
            count = sum(1 for plan in today_plans if plan.status == status_code)
            status_breakdown[status_code] = {
                'name': status_name,
                'count': count
            }
        
        return {
            'daily_plan': {
                'date': str(date),
                'planned_hours': daily_plan_hours,  # Total hours set in daily planner
                'has_daily_planner': daily_planner is not None
            },
            
            'total_tasks': len(today_plans),
            'total_planned_hours': round(total_minutes / 60, 2),
            'total_planned_minutes': total_minutes,
            
            'planned_tasks': {
                'count': len(planned_tasks_list),
                'total_hours': round(planned_minutes / 60, 2),
                'total_minutes': planned_minutes,
                'tasks': build_task_details(planned_tasks_list)
            },
            
            'unplanned_tasks': {
                'count': len(unplanned_tasks_list),
                'total_hours': round(unplanned_minutes / 60, 2),
                'total_minutes': unplanned_minutes,
                'tasks': build_task_details(unplanned_tasks_list)
            },
            
            'quadrant_breakdown': quadrant_breakdown,
            'status_breakdown': status_breakdown
        }
    
    def get_actual_summary(self, data):
        """Get actual work information with detailed breakdown by planned/unplanned"""
        today_plans = data.get('today_plans', [])
        activity_logs = data.get('activity_logs', [])
        
        # Separate activity logs based on is_unplanned flag
        planned_activity_logs = [log for log in activity_logs if not log.is_unplanned]
        unplanned_activity_logs = [log for log in activity_logs if log.is_unplanned]
        
        # Get the TodayPlan IDs for planned and unplanned work
        planned_plan_ids = set(log.today_plan_id for log in planned_activity_logs)
        unplanned_plan_ids = set(log.today_plan_id for log in unplanned_activity_logs)
        
        # Get corresponding today_plans
        planned_plans = [plan for plan in today_plans if plan.id in planned_plan_ids]
        unplanned_plans = [plan for plan in today_plans if plan.id in unplanned_plan_ids]
        
        # Calculate for planned tasks
        planned_minutes_worked = sum(log.minutes_worked for log in planned_activity_logs)
        planned_hours_worked = round(planned_minutes_worked / 60, 2)
        
        # Calculate for unplanned tasks
        unplanned_minutes_worked = sum(log.minutes_worked for log in unplanned_activity_logs)
        unplanned_hours_worked = round(unplanned_minutes_worked / 60, 2)
        
        # Calculate totals
        total_minutes_worked = planned_minutes_worked + unplanned_minutes_worked
        total_hours_worked = round(total_minutes_worked / 60, 2)
        extra_minutes = sum(log.extra_minutes for log in activity_logs) if activity_logs else 0
        
        # Count completed tasks
        completed_tasks = sum(1 for plan in today_plans if plan.status == 'COMPLETED')
        not_started_tasks = sum(1 for plan in today_plans if plan.status == 'PLANNED')
        in_progress_tasks = sum(1 for plan in today_plans if plan.status in ['STARTED', 'IN_ACTIVITY'])
        
        # Build detailed task lists with actual work
        def build_actual_task_details(tasks, logs):
            result = []
            for task in tasks:
                task_logs = [log for log in logs if log.today_plan == task]
                total_worked_minutes = sum(log.minutes_worked for log in task_logs)
                
                result.append({
                    'id': task.id,
                    'name': task.catalog_item.name if task.catalog_item else task.custom_title,
                    'planned_minutes': task.planned_duration_minutes,
                    'planned_hours': round(task.planned_duration_minutes / 60, 2),
                    'actual_minutes': total_worked_minutes,
                    'actual_hours': round(total_worked_minutes / 60, 2),
                    'status': task.status,
                    'activity_sessions': len(task_logs),
                    'completed': task.status == 'COMPLETED'
                })
            return result
        
        return {
            'total_hours_worked': total_hours_worked,
            'total_minutes_worked': total_minutes_worked,
            'extra_minutes_worked': extra_minutes,
            'extra_hours_worked': round(extra_minutes / 60, 2),
            
            'planned_work': {
                'count': len(planned_plans),
                'total_hours': planned_hours_worked,
                'total_minutes': planned_minutes_worked,
                'tasks': build_actual_task_details(planned_plans, planned_activity_logs)
            },
            
            'unplanned_work': {
                'count': len(unplanned_plans),
                'total_hours': unplanned_hours_worked,
                'total_minutes': unplanned_minutes_worked,
                'tasks': build_actual_task_details(unplanned_plans, unplanned_activity_logs)
            },
            
            'completed_tasks': completed_tasks,
            'in_progress_tasks': in_progress_tasks,
            'not_started_tasks': not_started_tasks,
            'total_activity_logs': len(activity_logs)
        }
    
    def get_metrics(self, data):
        """Calculate comparison metrics"""
        today_plans = data.get('today_plans', [])
        activity_logs = data.get('activity_logs', [])
        
        planned_summary = self.get_planned_summary(data)
        actual_summary = self.get_actual_summary(data)
        
        # Calculate percentages
        total_tasks = planned_summary['total_tasks']
        completed_tasks = actual_summary['completed_tasks']
        task_completion_rate = round((completed_tasks / total_tasks * 100), 2) if total_tasks > 0 else 0
        
        # Time efficiency: (actual hours / planned hours) * 100
        planned_hours = planned_summary['total_planned_hours']
        actual_hours = actual_summary['total_hours_worked']
        time_efficiency = round((actual_hours / planned_hours * 100), 2) if planned_hours > 0 else 0
        
        # Difference in hours
        hour_difference = actual_hours - planned_hours
        
        # Planned vs Unplanned ratio
        planned_only = planned_summary.get('planned_tasks', {}).get('count', 0)
        unplanned = planned_summary.get('unplanned_tasks', {}).get('count', 0)
        
        return {
            'task_completion_rate': task_completion_rate,
            'time_efficiency_percentage': time_efficiency,
            'hour_difference': round(hour_difference, 2),
            'minute_difference': int(hour_difference * 60),
            'planned_vs_actual': {
                'planned': round(planned_hours, 2),
                'actual': round(actual_hours, 2),
                'difference': round(hour_difference, 2)
            },
            'task_breakdown': {
                'total': total_tasks,
                'completed': completed_tasks,
                'in_progress': actual_summary['in_progress_tasks'],
                'not_started': actual_summary['not_started_tasks'],
                'planned': planned_only,
                'unplanned': unplanned
            },
            'status': 'On Track' if task_completion_rate >= 75 else 'Behind Schedule' if task_completion_rate >= 50 else 'Needs Attention'
        }
    
    def get_tasks(self, data):
        """Get detailed task list"""
        today_plans = data.get('today_plans', [])
        activity_logs = data.get('activity_logs', [])
        activity_log_dict = {log.today_plan_id: log.is_unplanned for log in activity_logs}
        
        tasks_data = []
        for plan in today_plans:
            task_info = {
                'id': plan.id,
                'name': plan.catalog_item.name if plan.catalog_item else plan.custom_title,
                'planned_minutes': plan.planned_duration_minutes,
                'planned_hours': round(plan.planned_duration_minutes / 60, 2),
                'quadrant': plan.quadrant,
                'status': plan.status,
                'is_unplanned': activity_log_dict.get(plan.id, False),
                'activity_logs_count': plan.activity_logs.count(),
                'total_worked_minutes': sum(log.minutes_worked for log in plan.activity_logs.all()),
                'activities': []
            }
            
            # Add activity log details
            for activity in plan.activity_logs.all():
                task_info['activities'].append({
                    'id': activity.id,
                    'minutes_worked': activity.minutes_worked,
                    'hours_worked': activity.hours_worked,
                    'status': activity.status,
                    'start_time': activity.actual_start_time,
                    'end_time': activity.actual_end_time,
                    'completed': activity.is_task_completed
                })
            
            tasks_data.append(task_info)
        
        return tasks_data


class WeeklyComparisonSerializer(serializers.Serializer):
    """Weekly planned vs achieved comparison"""
    week_start = serializers.DateField()
    week_end = serializers.DateField()
    user = serializers.StringRelatedField()
    
    daily_breakdown = serializers.SerializerMethodField()
    weekly_totals = serializers.SerializerMethodField()
    weekly_metrics = serializers.SerializerMethodField()
    
    def get_daily_breakdown(self, data):
        """Daily breakdown for the week"""
        daily_data = data.get('daily_data', {})
        
        breakdown = []
        for date_str, day_info in daily_data.items():
            breakdown.append({
                'date': date_str,
                'planned_hours': day_info.get('planned_hours', 0),
                'actual_hours': day_info.get('actual_hours', 0),
                'completion_rate': day_info.get('completion_rate', 0),
                'efficiency': day_info.get('efficiency', 0)
            })
        
        return breakdown
    
    def get_weekly_totals(self, data):
        """Weekly aggregated totals"""
        daily_data = data.get('daily_data', {})
        
        total_planned = sum(day.get('planned_hours', 0) for day in daily_data.values())
        total_actual = sum(day.get('actual_hours', 0) for day in daily_data.values())
        total_completed = sum(day.get('completed_tasks', 0) for day in daily_data.values())
        total_tasks = sum(day.get('total_tasks', 0) for day in daily_data.values())
        
        return {
            'total_planned_hours': round(total_planned, 2),
            'total_actual_hours': round(total_actual, 2),
            'total_completed_tasks': total_completed,
            'total_tasks': total_tasks,
            'weekly_completion_rate': round((total_completed / total_tasks * 100), 2) if total_tasks > 0 else 0
        }
    
    def get_weekly_metrics(self, data):
        """Weekly performance metrics"""
        totals = self.get_weekly_totals(data)
        
        planned = totals['total_planned_hours']
        actual = totals['total_actual_hours']
        
        return {
            'average_daily_planned': round(planned / 7, 2),
            'average_daily_actual': round(actual / 7, 2),
            'weekly_efficiency': round((actual / planned * 100), 2) if planned > 0 else 0,
            'total_extra_hours': round(max(0, actual - planned), 2)
        }


class MonthlyComparisonSerializer(serializers.Serializer):
    """Monthly planned vs achieved comparison"""
    month = serializers.IntegerField()
    year = serializers.IntegerField()
    user = serializers.StringRelatedField()
    
    weekly_breakdown = serializers.SerializerMethodField()
    monthly_totals = serializers.SerializerMethodField()
    monthly_metrics = serializers.SerializerMethodField()
    
    def get_weekly_breakdown(self, data):
        """Weekly breakdown within the month"""
        weekly_data = data.get('weekly_data', {})
        
        breakdown = []
        for week_key, week_info in weekly_data.items():
            breakdown.append({
                'week': week_key,
                'planned_hours': round(week_info.get('planned_hours', 0), 2),
                'actual_hours': round(week_info.get('actual_hours', 0), 2),
                'completion_rate': round(week_info.get('completion_rate', 0), 2)
            })
        
        return breakdown
    
    def get_monthly_totals(self, data):
        """Monthly aggregated totals"""
        weekly_data = data.get('weekly_data', {})
        
        total_planned = sum(week.get('planned_hours', 0) for week in weekly_data.values())
        total_actual = sum(week.get('actual_hours', 0) for week in weekly_data.values())
        total_completed = sum(week.get('completed_tasks', 0) for week in weekly_data.values())
        total_tasks = sum(week.get('total_tasks', 0) for week in weekly_data.values())
        
        return {
            'total_planned_hours': round(total_planned, 2),
            'total_actual_hours': round(total_actual, 2),
            'total_completed_tasks': total_completed,
            'total_tasks': total_tasks,
            'monthly_completion_rate': round((total_completed / total_tasks * 100), 2) if total_tasks > 0 else 0
        }
    
    def get_monthly_metrics(self, data):
        """Monthly performance metrics"""
        totals = self.get_monthly_totals(data)
        
        planned = totals['total_planned_hours']
        actual = totals['total_actual_hours']
        
        return {
            'average_daily_planned': round(planned / 30, 2),
            'average_daily_actual': round(actual / 30, 2),
            'monthly_efficiency': round((actual / planned * 100), 2) if planned > 0 else 0,
            'total_extra_hours': round(max(0, actual - planned), 2)
        }
