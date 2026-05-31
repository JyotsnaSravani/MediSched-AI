"""
Manually transcribe all pending call logs.
Run this if automatic transcription isn't working.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from calling.models import CallLog
from transcriptions.tasks import transcribe_call

def transcribe_pending_calls():
    """Find and transcribe all pending call logs."""
    
    print("=" * 70)
    print("🔍 FINDING PENDING TRANSCRIPTIONS")
    print("=" * 70)
    print()
    
    # Find all call logs with recordings but pending transcription
    pending_logs = CallLog.objects.filter(
        transcription_status=CallLog.TranscriptionStatus.PENDING,
        twilio_recording_url__isnull=False
    ).exclude(twilio_recording_url='')
    
    if not pending_logs.exists():
        print("✅ No pending transcriptions found!")
        print()
        
        # Check for failed transcriptions
        failed_logs = CallLog.objects.filter(
            transcription_status=CallLog.TranscriptionStatus.FAILED,
            twilio_recording_url__isnull=False
        ).exclude(twilio_recording_url='')
        
        if failed_logs.exists():
            print(f"⚠️  Found {failed_logs.count()} failed transcription(s)")
            print("Would you like to retry them? (Run with --retry-failed)")
        
        return
    
    print(f"Found {pending_logs.count()} pending transcription(s)")
    print()
    
    for log in pending_logs:
        print(f"📞 Call Log #{log.id}")
        print(f"   Patient: {log.patient.full_name}")
        print(f"   Date: {log.initiated_at}")
        print(f"   Recording: {log.twilio_recording_url[:50]}...")
        print(f"   Status: {log.transcription_status}")
        print()
        print("   Transcribing...")
        
        try:
            result = transcribe_call(log.id)
            
            if result['status'] == 'success':
                print(f"   ✅ SUCCESS! Transcription ID: {result['transcription_id']}")
                print(f"   Word count: {result['word_count']}")
            elif result['status'] == 'simulated':
                print(f"   ⚠️  SIMULATED (OpenAI not configured)")
            else:
                print(f"   ❌ FAILED: {result.get('message', 'Unknown error')}")
        
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
        
        print()
    
    print("=" * 70)
    print("✅ TRANSCRIPTION COMPLETE")
    print("=" * 70)
    print()
    print("Check the Call Logs page to view transcriptions!")
    print()


if __name__ == '__main__':
    import sys
    
    if '--retry-failed' in sys.argv:
        # Retry failed transcriptions
        failed_logs = CallLog.objects.filter(
            transcription_status=CallLog.TranscriptionStatus.FAILED,
            twilio_recording_url__isnull=False
        ).exclude(twilio_recording_url='')
        
        print(f"Retrying {failed_logs.count()} failed transcription(s)...")
        
        for log in failed_logs:
            log.transcription_status = CallLog.TranscriptionStatus.PENDING
            log.save()
        
        transcribe_pending_calls()
    else:
        transcribe_pending_calls()
