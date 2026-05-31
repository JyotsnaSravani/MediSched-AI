"""
Trigger transcriptions for all calls with recordings.
"""

import sys
import os
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from calling.models import CallLog
from transcriptions.tasks import transcribe_call

def main():
    print("\n" + "="*80)
    print("  TRIGGERING TRANSCRIPTIONS")
    print("="*80)
    
    # Get calls needing transcription
    calls_to_transcribe = CallLog.objects.filter(
        transcription_status__in=['PENDING', 'FAILED']
    ).exclude(
        twilio_recording_url__isnull=True
    ).exclude(
        twilio_recording_url=''
    )
    
    total = calls_to_transcribe.count()
    
    if total == 0:
        print("\n✅ No calls need transcription")
        print("="*80 + "\n")
        return
    
    print(f"\n📝 Found {total} calls to transcribe\n")
    
    success_count = 0
    error_count = 0
    
    for i, call in enumerate(calls_to_transcribe, 1):
        try:
            print(f"{i}/{total}. Call ID {call.id} - {call.patient.full_name}")
            print(f"   Recording: {call.twilio_recording_url[:60]}...")
            
            # Trigger transcription task
            result = transcribe_call.delay(call.id)
            
            print(f"   ✅ Task queued: {result.id}")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            error_count += 1
    
    print("\n" + "="*80)
    print("  SUMMARY")
    print("="*80)
    print(f"\n✅ Successfully queued: {success_count}")
    if error_count > 0:
        print(f"❌ Errors: {error_count}")
    
    print("\n💡 Transcriptions are being processed in the background")
    print("   Check status with: python check_transcription_status.py")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
