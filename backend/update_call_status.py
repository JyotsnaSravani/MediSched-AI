"""
Update call status and duration from Twilio for calls with missing data.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from calling.models import CallLog
from django.conf import settings
from twilio.rest import Client

def update_call_statuses():
    """Update call logs with missing outcome/duration from Twilio."""
    
    print("=" * 70)
    print("🔍 UPDATING CALL STATUSES FROM TWILIO")
    print("=" * 70)
    print()
    
    # Find calls with NO_ANSWER outcome or missing duration
    incomplete_logs = CallLog.objects.filter(
        twilio_call_sid__isnull=False,
        completed_at__isnull=True
    ).exclude(twilio_call_sid='')
    
    if not incomplete_logs.exists():
        print("✅ All call logs are up to date!")
        return
    
    print(f"Found {incomplete_logs.count()} call(s) with incomplete data")
    print()
    
    # Initialize Twilio client
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        print("❌ Twilio credentials not configured")
        return
    
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    for log in incomplete_logs:
        print(f"📞 Call Log #{log.id}")
        print(f"   Patient: {log.patient.full_name}")
        print(f"   Twilio SID: {log.twilio_call_sid}")
        print(f"   Current Outcome: {log.outcome}")
        print(f"   Current Duration: {log.duration}")
        print()
        
        try:
            # Fetch call details from Twilio
            call = client.calls(log.twilio_call_sid).fetch()
            
            print(f"   Twilio Status: {call.status}")
            print(f"   Twilio Duration: {call.duration} seconds")
            
            # Map Twilio status to our outcome
            outcome_mapping = {
                'completed': CallLog.Outcome.COMPLETED,
                'busy': CallLog.Outcome.BUSY,
                'no-answer': CallLog.Outcome.NO_ANSWER,
                'failed': CallLog.Outcome.FAILED,
                'canceled': CallLog.Outcome.FAILED,
            }
            
            outcome = outcome_mapping.get(call.status, CallLog.Outcome.FAILED)
            duration = int(call.duration) if call.duration else 0
            
            # Update call log
            log.mark_completed(
                outcome=outcome,
                duration=duration
            )
            
            print(f"   ✅ UPDATED!")
            print(f"   New Outcome: {outcome}")
            print(f"   New Duration: {duration} seconds")
            
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
        
        print()
    
    print("=" * 70)
    print("✅ UPDATE COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    update_call_statuses()
