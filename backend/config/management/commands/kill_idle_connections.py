"""
Management command to kill idle PostgreSQL connections.
Run this to clear stuck connections: python manage.py kill_idle_connections
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Kill idle PostgreSQL connections to free up connection slots'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Kill all idle connections except current one
            cursor.execute("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND pid <> pg_backend_pid()
                  AND state = 'idle'
                  AND state_change < current_timestamp - INTERVAL '5 minutes';
            """)
            
            result = cursor.fetchall()
            killed_count = sum(1 for row in result if row[0])
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully killed {killed_count} idle connections')
            )
            
            # Show current connection count
            cursor.execute("""
                SELECT count(*) 
                FROM pg_stat_activity 
                WHERE datname = current_database();
            """)
            
            current_connections = cursor.fetchone()[0]
            self.stdout.write(
                self.style.WARNING(f'Current active connections: {current_connections}')
            )
