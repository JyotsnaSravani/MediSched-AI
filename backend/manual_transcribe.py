"""
Manually trigger transcription for pending calls
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from calling.models import CallLog
from transcriptions.tasks import transcribe_call

# Get all calls with pending transcription
pending_calls = CallLog.objects.filter(
    transcription_status=CallLog.TranscriptionStatus.PENDING,
    twilio_recording_url__isnull=False
).order_by('-initiated_at')[:10]

print(f"\n{'='*70}")
print(f"Found {pending_calls.count()} calls with pending transcription")
print(f"{'='*70}\n")

for call in pending_calls:
    print(f"Call #{call.id}:")
    print(f"  Patient: {call.patient.full_name}")
    print(f"  Duration: {call.duration}s")
    print(f"  Recording: {call.twilio_recording_url[:50]}...")
    print(f"  Status: {call.transcription_status}")
    
    try:
        # Call transcription directly (not via Celery)
        result = transcribe_call(call.id)
        print(f"  ✅ Result: {result}")
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
    
    print()

print(f"{'='*70}\n")
