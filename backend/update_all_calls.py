"""
Complete Call Update Script
Updates Outcome, Duration, and Transcription for all calls
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from calling.models import CallLog
from transcriptions.models import Transcription
from django.conf import settings
from twilio.rest import Client

def update_all_calls():
    """Update outcome, duration, and transcription for all incomplete calls."""
    
    print("=" * 70)
    print("🔄 UPDATING ALL CALL DATA")
    print("=" * 70)
    print()
    
    # Find calls that need updates
    incomplete_logs = CallLog.objects.filter(
        twilio_call_sid__isnull=False
    ).exclude(twilio_call_sid='').order_by('-initiated_at')[:10]
    
    if not incomplete_logs.exists():
        print("✅ No calls found!")
        return
    
    print(f"Found {incomplete_logs.count()} recent call(s)")
    print()
    
    # Check Twilio credentials
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        print("❌ Twilio credentials not configured")
        return
    
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    # Check OpenAI credentials
    has_openai = bool(settings.OPENAI_API_KEY)
    
    for log in incomplete_logs:
        print(f"📞 Call Log #{log.id}")
        print(f"   Patient: {log.patient.full_name}")
        print(f"   Date: {log.initiated_at}")
        print(f"   Twilio SID: {log.twilio_call_sid}")
        print()
        
        # Step 1: Update Outcome & Duration
        print("   [1/3] Updating outcome and duration...")
        try:
            call = client.calls(log.twilio_call_sid).fetch()
            
            outcome_mapping = {
                'completed': CallLog.Outcome.COMPLETED,
                'busy': CallLog.Outcome.BUSY,
                'no-answer': CallLog.Outcome.NO_ANSWER,
                'failed': CallLog.Outcome.FAILED,
                'canceled': CallLog.Outcome.FAILED,
            }
            
            outcome = outcome_mapping.get(call.status, CallLog.Outcome.FAILED)
            duration = int(call.duration) if call.duration else 0
            
            # Update if needed
            if log.outcome != outcome or log.duration != duration:
                log.mark_completed(outcome=outcome, duration=duration)
                print(f"   ✅ Outcome: {outcome}")
                print(f"   ✅ Duration: {duration} seconds")
            else:
                print(f"   ℹ️  Already up to date (Outcome: {outcome}, Duration: {duration}s)")
            
        except Exception as e:
            print(f"   ❌ Error updating status: {str(e)}")
        
        print()
        
        # Step 2: Get Recording URL
        print("   [2/3] Checking for recording...")
        try:
            if not log.twilio_recording_url:
                # Try to get recording from Twilio
                recordings = client.recordings.list(call_sid=log.twilio_call_sid, limit=1)
                if recordings:
                    recording_url = f"https://api.twilio.com{recordings[0].uri.replace('.json', '')}"
                    log.twilio_recording_url = recording_url
                    log.save()
                    print(f"   ✅ Recording URL found and saved")
                else:
                    print(f"   ⚠️  No recording available yet")
            else:
                print(f"   ℹ️  Recording URL already saved")
        except Exception as e:
            print(f"   ⚠️  Could not fetch recording: {str(e)}")
        
        print()
        
        # Step 3: Create Transcription
        print("   [3/3] Processing transcription...")
        
        # Check if transcription already exists
        existing_transcription = Transcription.objects.filter(call_log=log).first()
        
        if existing_transcription:
            print(f"   ℹ️  Transcription already exists (ID: {existing_transcription.id})")
            print(f"   Status: {existing_transcription.status}")
            print(f"   Word count: {existing_transcription.word_count}")
        elif not log.twilio_recording_url:
            print(f"   ⚠️  No recording URL - cannot transcribe")
            log.transcription_status = CallLog.TranscriptionStatus.NO_RECORDING
            log.save()
        elif not has_openai:
            print(f"   ⚠️  OpenAI API key not configured")
        else:
            # Create transcription
            try:
                from transcriptions.tasks import transcribe_call
                
                log.transcription_status = CallLog.TranscriptionStatus.IN_PROGRESS
                log.save()
                
                result = transcribe_call(log.id)
                
                if result['status'] == 'success':
                    print(f"   ✅ Transcription created!")
                    print(f"   Transcription ID: {result['transcription_id']}")
                    print(f"   Word count: {result['word_count']}")
                elif result['status'] == 'simulated':
                    print(f"   ⚠️  Simulated transcription (OpenAI not configured)")
                else:
                    print(f"   ❌ Transcription failed: {result.get('message', 'Unknown error')}")
                    
            except Exception as e:
                print(f"   ❌ Error creating transcription: {str(e)}")
                log.transcription_status = CallLog.TranscriptionStatus.FAILED
                log.save()
        
        print()
        print("-" * 70)
        print()
    
    print("=" * 70)
    print("✅ UPDATE COMPLETE")
    print("=" * 70)
    print()
    print("Check the Call Logs page to view updated data!")
    print()


if __name__ == '__main__':
    update_all_calls()
