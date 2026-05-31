"""
Script to manually trigger transcriptions for CallLog records
that have recording URLs but no transcription records.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from calling.models import CallLog
from transcriptions.models import Transcription


def trigger_transcriptions():
    """Trigger transcriptions for calls with recordings"""
    
    print("=" * 80)
    print("TRIGGERING TRANSCRIPTIONS FOR CALLS WITH RECORDINGS")
    print("=" * 80)
    print()
    
    # Find calls that have recordings but no transcription
    calls_needing_transcription = CallLog.objects.filter(
        twilio_recording_url__isnull=False,
        transcription__isnull=True  # No transcription record exists
    ).order_by('initiated_at')
    
    count = calls_needing_transcription.count()
    
    if count == 0:
        print("✅ No calls need transcription!")
        print("   All calls with recordings already have transcriptions.")
        return
    
    print(f"Found {count} calls with recordings that need transcription")
    print()
    
    # Show sample
    print("Sample calls:")
    for call in calls_needing_transcription[:5]:
        print(f"  • ID {call.id}: {call.patient.full_name} - {call.call_type} - {call.outcome}")
    
    if count > 5:
        print(f"  ... and {count - 5} more")
    
    print()
    
    # Ask for confirmation
    response = input("Do you want to trigger transcriptions for these calls? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("\n❌ Cancelled by user")
        return
    
    print()
    print("-" * 80)
    print("Triggering transcriptions...")
    print("-" * 80)
    print()
    
    success_count = 0
    error_count = 0
    
    for call in calls_needing_transcription:
        print(f"Processing CallLog ID {call.id} ({call.patient.full_name})...")
        
        try:
            # Try to use Celery task
            try:
                from transcriptions.tasks import transcribe_call
                
                # Update status to PENDING
                call.transcription_status = CallLog.TranscriptionStatus.PENDING
                call.save()
                
                # Queue transcription task
                transcribe_call.delay(call.id)
                
                print(f"  ✅ Transcription task queued (Celery)")
                success_count += 1
                
            except Exception as celery_error:
                # Celery not available - run synchronously
                print(f"  ⚠️  Celery not available, running synchronously...")
                
                from transcriptions.tasks import transcribe_call as transcribe_call_func
                
                # Update status
                call.transcription_status = CallLog.TranscriptionStatus.IN_PROGRESS
                call.save()
                
                # Run transcription synchronously
                result = transcribe_call_func(call.id)
                
                if result.get('status') in ['success', 'simulated']:
                    print(f"  ✅ Transcription completed: {result.get('message', 'Success')}")
                    success_count += 1
                else:
                    print(f"  ❌ Transcription failed: {result.get('message', 'Unknown error')}")
                    error_count += 1
        
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            error_count += 1
        
        print()
    
    print("-" * 80)
    print(f"✅ Successfully triggered: {success_count}")
    if error_count > 0:
        print(f"❌ Errors: {error_count}")
    print()
    
    # Show transcription status
    print("Current transcription status:")
    
    transcription_count = Transcription.objects.count()
    pending_count = CallLog.objects.filter(
        transcription_status=CallLog.TranscriptionStatus.PENDING
    ).count()
    in_progress_count = CallLog.objects.filter(
        transcription_status=CallLog.TranscriptionStatus.IN_PROGRESS
    ).count()
    completed_count = CallLog.objects.filter(
        transcription_status=CallLog.TranscriptionStatus.COMPLETED
    ).count()
    
    print(f"  • Transcription records: {transcription_count}")
    print(f"  • Pending: {pending_count}")
    print(f"  • In Progress: {in_progress_count}")
    print(f"  • Completed: {completed_count}")
    print()
    
    print("=" * 80)


if __name__ == '__main__':
    trigger_transcriptions()
