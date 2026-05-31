"""
Transcribe calls IMMEDIATELY (synchronous - no Celery needed).
This runs transcriptions directly without background tasks.
"""

import sys
import os
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from calling.models import CallLog
from transcriptions.models import Transcription
from django.conf import settings
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def transcribe_call_sync(call_log_id):
    """
    Transcribe a call synchronously (no Celery).
    """
    try:
        call_log = CallLog.objects.get(id=call_log_id)
        
        # Check if recording exists
        if not call_log.twilio_recording_url:
            logger.warning(f"No recording for call {call_log_id}")
            call_log.transcription_status = CallLog.TranscriptionStatus.NO_RECORDING
            call_log.save()
            return {'status': 'no_recording'}
        
        # Update status
        call_log.transcription_status = CallLog.TranscriptionStatus.IN_PROGRESS
        call_log.save()
        
        logger.info(f"Transcribing call {call_log_id}...")
        
        # Check OpenAI API key
        if not settings.OPENAI_API_KEY:
            logger.warning("OpenAI not configured - creating simulated transcription")
            
            transcription = Transcription.objects.create(
                call_log=call_log,
                appointment=call_log.appointment,
                text=f"[SIMULATED] Call with {call_log.patient.full_name}. "
                     f"Duration: {call_log.duration or 0} seconds. "
                     f"Type: {call_log.call_type}. "
                     f"Outcome: {call_log.outcome}.",
                status=Transcription.Status.COMPLETED,
                whisper_model='simulated'
            )
            
            call_log.transcription_status = CallLog.TranscriptionStatus.COMPLETED
            call_log.save()
            
            return {
                'status': 'simulated',
                'transcription_id': transcription.id,
                'text': transcription.text
            }
        
        # Download recording from Twilio
        logger.info("Downloading recording from Twilio...")
        recording_response = requests.get(
            call_log.twilio_recording_url,
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            timeout=30
        )
        recording_response.raise_for_status()
        
        audio_content = recording_response.content
        logger.info(f"Downloaded {len(audio_content)} bytes")
        
        # Call OpenAI Whisper API
        logger.info("Calling OpenAI Whisper API...")
        
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Create temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
            temp_audio.write(audio_content)
            temp_audio_path = temp_audio.name
        
        try:
            # Transcribe
            with open(temp_audio_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
            
            transcription_text = transcript.text
            logger.info(f"Transcription completed: {len(transcription_text)} characters")
            
            # Create transcription record
            transcription = Transcription.objects.create(
                call_log=call_log,
                appointment=call_log.appointment,
                text=transcription_text,
                status=Transcription.Status.COMPLETED,
                whisper_model='whisper-1'
            )
            
            # Update call log
            call_log.transcription_status = CallLog.TranscriptionStatus.COMPLETED
            call_log.save()
            
            return {
                'status': 'success',
                'transcription_id': transcription.id,
                'text': transcription_text,
                'word_count': transcription.word_count
            }
            
        finally:
            # Cleanup
            import os
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
    
    except Exception as e:
        logger.error(f"Error transcribing call {call_log_id}: {str(e)}")
        
        try:
            call_log = CallLog.objects.get(id=call_log_id)
            call_log.transcription_status = CallLog.TranscriptionStatus.FAILED
            call_log.save()
        except:
            pass
        
        return {'status': 'error', 'message': str(e)}

def main():
    print("\n" + "="*80)
    print("  IMMEDIATE TRANSCRIPTION (No Celery Required)")
    print("="*80)
    
    # Get calls needing transcription
    calls_to_transcribe = CallLog.objects.filter(
        transcription_status__in=['PENDING', 'FAILED']
    ).exclude(
        twilio_recording_url__isnull=True
    ).exclude(
        twilio_recording_url=''
    ).order_by('-initiated_at')
    
    total = calls_to_transcribe.count()
    
    if total == 0:
        print("\n✅ No calls need transcription")
        print("="*80 + "\n")
        return
    
    print(f"\n📝 Found {total} calls to transcribe")
    print("⚠️  This will transcribe calls one by one (may take time)")
    
    # Ask for confirmation
    response = input(f"\nTranscribe all {total} calls? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    print("\n" + "="*80)
    
    success_count = 0
    error_count = 0
    simulated_count = 0
    
    for i, call in enumerate(calls_to_transcribe, 1):
        print(f"\n{i}/{total}. Call ID {call.id} - {call.patient.full_name}")
        print(f"   Date: {call.initiated_at}")
        print(f"   Duration: {call.duration or 0}s")
        
        result = transcribe_call_sync(call.id)
        
        if result['status'] == 'success':
            print(f"   ✅ Transcribed: {result['word_count']} words")
            print(f"   Text: {result['text'][:100]}...")
            success_count += 1
        elif result['status'] == 'simulated':
            print(f"   ⚠️  Simulated (OpenAI not configured)")
            print(f"   Text: {result['text'][:100]}...")
            simulated_count += 1
        else:
            print(f"   ❌ Error: {result.get('message', 'Unknown error')}")
            error_count += 1
    
    print("\n" + "="*80)
    print("  SUMMARY")
    print("="*80)
    print(f"\n✅ Successfully transcribed: {success_count}")
    if simulated_count > 0:
        print(f"⚠️  Simulated: {simulated_count}")
    if error_count > 0:
        print(f"❌ Errors: {error_count}")
    
    print("\n💡 Check transcriptions:")
    print("   python check_transcription_status.py")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
