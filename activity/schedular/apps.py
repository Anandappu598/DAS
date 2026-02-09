from django.apps import AppConfig


class SchedularConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'schedular'    
    def ready(self):
        """Import signals when app is ready"""
        import schedular.signals