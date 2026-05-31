"""
Custom middleware for MediSched AI
"""

from django.db import connection
from django.core.signals import request_finished
from django.dispatch import receiver


class DatabaseConnectionMiddleware:
    """
    Middleware to aggressively close database connections after each request.
    Prevents "too many clients already" PostgreSQL error.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Close database connection after each request
        if connection.connection is not None:
            connection.close()
        
        return response


@receiver(request_finished)
def close_db_connection(sender, **kwargs):
    """
    Signal handler to close database connections when request finishes.
    Extra safety net to prevent connection leaks.
    """
    if connection.connection is not None:
        connection.close()
