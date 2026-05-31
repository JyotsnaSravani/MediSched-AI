"""
Automatic Call Update Service
Runs in background and automatically updates calls every 30 seconds
"""

import os
import sys
import django
import time
from datetime import datetime, timedelta

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from calling.models import CallLog
from transcriptions.models import Transcription
from django.conf import settings
from django.utils import timezone
from twilio.rest import Client

def update_recent_calls():
    """Update calls from the last 10 minutes."""
    
    # Find calls from last 10 minutes that might need updates
    ten_minutes_ago = timezone.now() - timedelta(minutes=10)
    
    recent_calls = CallLog.objects.filter(
        initiated_at__gte=ten_minutes_ago,
        twilio_call_sid__isnull=False
    ).exclude(twilio_call_sid='')
    
    if not recent_calls.exists():
        return 0
    
    # Check Twilio credentials
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        print("❌ Twilio credentials not configured")
        return 0
    
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    updated_count = 0
    
    for log in recent_calls:
        try:
            # Get call status from Twilio
            call = client.calls(log.twilio_call_sid).fetch()
            
            # Only update if call is completed
            if call.status not in ['completed', 'busy', 'no-answer', 'failed', 'canceled']:
                continue
            
            # Map status to outcome
            outcome_mapping = {
                'completed': CallLog.Outcome.COMPLETED,
                'busy': CallLog.Outcome.BUSY,
                'no-answer': CallLog.Outcome.NO_ANSWER,
                'failed': CallLog.Outcome.FAILED,
                'canceled': CallLog.Outcome.FAILED,
            }
            
            outcome = outcome_mapping.get(call.status, CallLog.Outcome.FAILED)
            duration = int(call.duration) if call.duration else 0
            
            # Update outcome and duration if needed
            needs_update = False
            if log.outcome != outcome or log.duration != duration or not log.completed_at:
                log.mark_completed(outcome=outcome, duration=duration)
                needs_update = True
                print(f"✅ Updated Call #{log.id}: {outcome}, {duration}s")
            
            # Get recording URL if not present
            if not log.twilio_recording_url:
                recordings = client.recordings.list(call_sid=log.twilio_call_sid, limit=1)
                if recordings:
                    recording_url = f"https://api.twilio.com{recordings[0].uri.replace('.json', '')}"
                    log.twilio_recording_url = recording_url
                    log.save()
                    needs_update = True
                    print(f"✅ Recording URL saved for Call #{log.id}")
            
            # Create transcription if needed
            if log.twilio_recording_url and not Transcription.objects.filter(call_log=log).exists():
                if log.transcription_status != CallLog.TranscriptionStatus.IN_PROGRESS:
                    try:
                        from transcriptions.tasks import transcribe_call
                        log.transcription_status = CallLog.TranscriptionStatus.IN_PROGRESS
                        log.save()
                        
                        result = transcribe_call(log.id)
                        
                        if result['status'] == 'success':
                            print(f"✅ Transcription created for Call #{log.id}")
                            needs_update = True
                    except Exception as e:
                        print(f"⚠️  Transcription error for Call #{log.id}: {str(e)}")
                        log.transcription_status = CallLog.TranscriptionStatus.FAILED
                        log.save()
            
            if needs_update:
                updated_count += 1
                
        except Exception as e:
            print(f"⚠️  Error updating Call #{log.id}: {str(e)}")
    
    return updated_count


def main():
    """Main loop - runs every 30 seconds."""
    
    print("=" * 70)
    print("🔄 AUTOMATIC CALL UPDATE SERVICE")
    print("=" * 70)
    print()
    print("This service automatically updates:")
    print("  • Outcome (COMPLETED, NO_ANSWER, etc.)")
    print("  • Duration (in seconds)")
    print("  • Transcription (full conversation text)")
    print()
    print("Checking for updates every 30 seconds...")
    print("Press Ctrl+C to stop")
    print()
    print("-" * 70)
    print()
    
    check_count = 0
    
    try:
        while True:
            check_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            print(f"[{timestamp}] Check #{check_count}: Looking for calls to update...")
            
            updated = update_recent_calls()
            
            if updated > 0:
                print(f"[{timestamp}] ✅ Updated {updated} call(s)")
            else:
                print(f"[{timestamp}] ℹ️  No updates needed")
            
            print()
            
            # Wait 30 seconds before next check
            time.sleep(30)
            
    except KeyboardInterrupt:
        print()
        print("-" * 70)
        print()
        print("🛑 Service stopped by user")
        print()
        print("=" * 70)
        print("✅ AUTOMATIC UPDATE SERVICE STOPPED")
        print("=" * 70)


if __name__ == '__main__':
    main()
