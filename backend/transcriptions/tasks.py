"""
Celery tasks for call transcription system.
Sprint 3 - Implements FR-CD-01 (auto-transcription with Whisper API)
"""

from celery import shared_task
from django.conf import settings
import logging
import requests

logger = logging.getLogger(__name__)


def _transcribe_call_sync(call_log_id):
    """
    Synchronous version of transcribe_call using OpenAI Whisper API.
    """
    from calling.models import CallLog
    from .models import Transcription
    from openai import OpenAI
    import tempfile
    
    try:
        # Get call log
        call_log = CallLog.objects.get(id=call_log_id)
        
        # Check if recording URL exists
        if not call_log.twilio_recording_url:
            logger.warning(f"No recording URL for call log {call_log_id}")
            call_log.transcription_status = CallLog.TranscriptionStatus.NO_RECORDING
            call_log.save()
            return {'status': 'no_recording', 'call_log_id': call_log_id}
        
        # Update status to in progress
        call_log.transcription_status = CallLog.TranscriptionStatus.IN_PROGRESS
        call_log.save()
        
        logger.info(f"Starting Whisper transcription for call log {call_log_id}")
        
        # Download the recording from Twilio
        recording_url = call_log.twilio_recording_url
        
        # Add .mp3 extension if not present
        if not recording_url.endswith('.mp3'):
            recording_url += '.mp3'
        
        logger.info(f"Downloading recording from: {recording_url}")
        
        # Download the audio file
        response = requests.get(recording_url, auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN))
        
        if response.status_code != 200:
            raise Exception(f"Failed to download recording: HTTP {response.status_code}")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
            temp_audio.write(response.content)
            temp_audio_path = temp_audio.name
        
        logger.info(f"Audio file saved to: {temp_audio_path}")
        
        try:
            # Transcribe using OpenAI Whisper
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            logger.info("Sending audio to Whisper API...")
            
            with open(temp_audio_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            logger.info(f"Whisper transcription completed: {len(transcript)} characters")
            
            # Build formatted transcription
            transcription_text = ""
            
            # Add header
            transcription_text += f"Call Transcription\n"
            transcription_text += f"==================\n"
            transcription_text += f"Patient: {call_log.patient.full_name}\n"
            transcription_text += f"Phone: {call_log.patient.phone_number}\n"
            transcription_text += f"Date: {call_log.initiated_at.strftime('%B %d, %Y at %I:%M %p')}\n"
            transcription_text += f"Duration: {call_log.duration or 0} seconds\n"
            transcription_text += f"Outcome: {call_log.outcome}\n"
            transcription_text += f"\nTranscription (Whisper AI):\n"
            transcription_text += f"---------------------------\n"
            transcription_text += transcript
            transcription_text += f"\n\n---------------------------\n"
            transcription_text += f"Recording URL: {call_log.twilio_recording_url}\n"
            
            # Create transcription
            transcription = Transcription.objects.create(
                call_log=call_log,
                appointment=call_log.appointment,
                text=transcription_text,
                status=Transcription.Status.COMPLETED,
                whisper_model='whisper-1'
            )
            
            call_log.transcription_status = CallLog.TranscriptionStatus.COMPLETED
            call_log.save()
            
            logger.info(f"Transcription saved: ID {transcription.id}")
            
            return {
                'status': 'success',
                'transcription_id': transcription.id,
                'message': 'Transcription completed using Whisper API'
            }
            
        finally:
            # Clean up temporary file
            import os
            try:
                os.unlink(temp_audio_path)
                logger.info(f"Temporary audio file deleted: {temp_audio_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {e}")
        
    except CallLog.DoesNotExist:
        logger.error(f"CallLog {call_log_id} not found")
        return {'status': 'error', 'message': 'CallLog not found'}
    
    except Exception as e:
        logger.error(f"Error transcribing call: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Update status to failed
        try:
            call_log = CallLog.objects.get(id=call_log_id)
            call_log.transcription_status = CallLog.TranscriptionStatus.FAILED
            call_log.save()
        except Exception as save_err:
            logger.error(f"Failed to update transcription status: {save_err}")
            pass
        
        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True, max_retries=3, acks_late=True)
def transcribe_call(self, call_log_id):
    """
    Transcribe call recording using OpenAI Whisper API.
    
    Implements FR-CD-01: Auto-transcription of call recordings.
    
    Args:
        call_log_id: CallLog ID to transcribe
    """
    # Use the synchronous version
    return _transcribe_call_sync(call_log_id)
