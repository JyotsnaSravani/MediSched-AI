"""
Celery tasks for AI calling system.
Sprint 3 - Implements FR-AC-01 (3-attempt escalation)
"""

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, acks_late=True)
def call_patient(self, patient_id, appointment_id=None, call_type='GENERAL', attempt=1):
    """
    Initiate AI outbound call to patient with 3-attempt escalation.
    
    Implements FR-AC-01: 3-attempt escalation with 2-hour intervals.
    
    Args:
        patient_id: Patient ID to call
        appointment_id: Optional appointment ID
        call_type: Type of call (APPOINTMENT_REMINDER, SLOT_OFFER, etc.)
        attempt: Current attempt number (1, 2, or 3)
    """
    from patients.models import Patient
    from scheduling.models import Appointment
    from .models import CallLog, ManualCallbackTask
    
    try:
        # Get patient
        patient = Patient.objects.get(id=patient_id)
        appointment = None
        if appointment_id:
            appointment = Appointment.objects.get(id=appointment_id)
        
        logger.info(f"Initiating call to {patient.full_name} (Attempt {attempt})")
        
        # Create call log
        call_log = CallLog.objects.create(
            patient=patient,
            appointment=appointment,
            call_type=call_type,
            attempt_number=attempt,
            outcome=CallLog.Outcome.NO_ANSWER  # Default, will be updated by webhook
        )
        
        # Check if Twilio is configured
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            logger.warning("Twilio not configured - simulating call")
            call_log.twilio_call_sid = f"SIMULATED_{call_log.id}"
            call_log.mark_completed(
                outcome=CallLog.Outcome.NO_ANSWER,
                duration=0
            )
            
            # Schedule next attempt or create manual task
            _handle_no_answer(patient_id, appointment_id, call_type, attempt)
            return {
                'status': 'simulated',
                'call_log_id': call_log.id,
                'message': 'Twilio not configured - call simulated'
            }
        
        # Initialize Twilio client
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Check if we should use conversational AI or simple TwiML
        use_conversational_ai = getattr(settings, 'USE_CONVERSATIONAL_AI', True)
        
        # Initiate call
        try:
            if use_conversational_ai and settings.SITE_URL and 'localhost' not in settings.SITE_URL:
                # Use conversational AI with webhooks (requires public URL)
                from django.urls import reverse
                webhook_url = f"{settings.SITE_URL}{reverse('calling:twiml-conversational')}?call_type={call_type}&patient_id={patient_id}&call_log_id={call_log.id}"
                status_callback_url = f"{settings.SITE_URL}{reverse('calling:status-callback')}"
                
                logger.info(f"Using conversational AI with webhook: {webhook_url}")
                
                call = client.calls.create(
                    to=patient.phone_number,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    url=webhook_url,
                    status_callback=status_callback_url,
                    status_callback_event=['completed'],
                    record=True,  # RECORDING ENABLED
                    recording_status_callback=f"{settings.SITE_URL}{reverse('calling:recording-callback')}"
                )
            else:
                # Use simple inline TwiML (no webhooks needed - for testing)
                from twilio.twiml.voice_response import VoiceResponse
                from django.urls import reverse
                
                logger.info("Using simple TwiML (no conversational AI)")
                
                response = VoiceResponse()
                response.say(
                    f"Hello {patient.full_name}. This is an automated test call from MediSched AI. "
                    "Thank you for your time. Goodbye.",
                    voice='Polly.Joanna',
                    language='en-US'
                )
                response.hangup()
                
                twiml_str = str(response)
                
                # Build callback URLs
                status_callback_url = f"{settings.SITE_URL}{reverse('calling:status-callback')}"
                recording_callback_url = f"{settings.SITE_URL}{reverse('calling:recording-callback')}"
                
                call = client.calls.create(
                    to=patient.phone_number,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    twiml=twiml_str,
                    record=True,  # RECORDING ENABLED
                    status_callback=status_callback_url,
                    status_callback_event=['completed'],
                    recording_status_callback=recording_callback_url
                )
            
            # Update call log with Twilio SID
            call_log.twilio_call_sid = call.sid
            call_log.save()
            
            logger.info(f"Call initiated successfully: {call.sid}")
            
            return {
                'status': 'success',
                'call_log_id': call_log.id,
                'twilio_call_sid': call.sid,
                'attempt': attempt
            }
            
        except Exception as twilio_error:
            error_message = str(twilio_error)
            logger.error(f"Twilio API error: {error_message}")
            
            # Check for trial account restriction (Error 21219)
            if "unverified" in error_message.lower() or "21219" in error_message:
                call_log.outcome = CallLog.Outcome.FAILED
                call_log.notes = f"Trial account restriction: {patient.phone_number} is not verified. Please upgrade Twilio account or verify this number in Twilio console."
                call_log.completed_at = timezone.now()
                call_log.save()
                
                return {
                    'status': 'error',
                    'call_log_id': call_log.id,
                    'message': f'Twilio trial account restriction: {patient.phone_number} is not verified. Please upgrade your Twilio account to call unverified numbers, or verify this number at https://console.twilio.com/us1/develop/phone-numbers/manage/verified'
                }
            
            # Check for invalid phone number (Error 21211)
            elif "21211" in error_message or "invalid" in error_message.lower():
                call_log.outcome = CallLog.Outcome.FAILED
                call_log.notes = f"Invalid phone number format: {patient.phone_number}. Must be E.164 format (+country code + number)."
                call_log.completed_at = timezone.now()
                call_log.save()
                
                return {
                    'status': 'error',
                    'call_log_id': call_log.id,
                    'message': f'Invalid phone number format: {patient.phone_number}. Phone numbers must be in E.164 format (e.g., +19175551234)'
                }
            
            # Check for authentication error (Error 20003)
            elif "20003" in error_message or "authenticate" in error_message.lower():
                call_log.outcome = CallLog.Outcome.FAILED
                call_log.notes = "Twilio authentication failed. Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env file."
                call_log.completed_at = timezone.now()
                call_log.save()
                
                return {
                    'status': 'error',
                    'call_log_id': call_log.id,
                    'message': 'Twilio authentication failed. Please check your Twilio credentials in the .env file.'
                }
            
            # Generic Twilio error
            else:
                call_log.outcome = CallLog.Outcome.FAILED
                call_log.notes = f"Twilio error: {error_message}"
                call_log.completed_at = timezone.now()
                call_log.save()
                
                return {
                    'status': 'error',
                    'call_log_id': call_log.id,
                    'message': f'Failed to initiate call: {error_message}'
                }
        
    except Patient.DoesNotExist:
        logger.error(f"Patient {patient_id} not found")
        return {'status': 'error', 'message': 'Patient not found'}
    
    except Appointment.DoesNotExist:
        logger.error(f"Appointment {appointment_id} not found")
        return {'status': 'error', 'message': 'Appointment not found'}
    
    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}")
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


def _handle_no_answer(patient_id, appointment_id, call_type, current_attempt):
    """
    Handle no-answer scenario with escalation logic.
    
    Attempt 1 → Schedule Attempt 2 (+2 hours)
    Attempt 2 → Schedule Attempt 3 (+2 hours)
    Attempt 3 → Create ManualCallbackTask
    """
    from .models import ManualCallbackTask
    from patients.models import Patient
    from scheduling.models import Appointment
    
    if current_attempt < 3:
        # Schedule next attempt in 2 hours
        next_attempt = current_attempt + 1
        eta = timezone.now() + timedelta(hours=2)
        
        logger.info(f"Scheduling attempt {next_attempt} for patient {patient_id} at {eta}")
        
        call_patient.apply_async(
            args=[patient_id, appointment_id, call_type, next_attempt],
            eta=eta
        )
    else:
        # All 3 attempts failed - create manual callback task
        logger.warning(f"All 3 attempts failed for patient {patient_id} - creating manual callback task")
        
        patient = Patient.objects.get(id=patient_id)
        appointment = None
        if appointment_id:
            appointment = Appointment.objects.get(id=appointment_id)
        
        ManualCallbackTask.objects.create(
            patient=patient,
            appointment=appointment,
            reason=f"3 AI call attempts failed (Call Type: {call_type})",
            notes=f"Patient did not answer after 3 attempts. Last attempt at {timezone.now()}"
        )


@shared_task
def process_call_status(call_sid, call_status, call_duration, recording_url=None):
    """
    Process call status callback from Twilio.
    Updates call log with final status and duration.
    """
    from .models import CallLog
    
    try:
        call_log = CallLog.objects.get(twilio_call_sid=call_sid)
        
        # Map Twilio status to our outcome
        outcome_mapping = {
            'completed': CallLog.Outcome.COMPLETED,
            'busy': CallLog.Outcome.BUSY,
            'no-answer': CallLog.Outcome.NO_ANSWER,
            'failed': CallLog.Outcome.FAILED,
            'canceled': CallLog.Outcome.FAILED,
        }
        
        outcome = outcome_mapping.get(call_status, CallLog.Outcome.FAILED)
        
        call_log.mark_completed(
            outcome=outcome,
            duration=call_duration,
            recording_url=recording_url
        )
        
        logger.info(f"Call {call_sid} completed with status {call_status}")
        
        # If recording available, trigger transcription
        if recording_url:
            from transcriptions.tasks import transcribe_call
            transcribe_call.delay(call_log.id)
        
        # Handle no-answer escalation
        if outcome == CallLog.Outcome.NO_ANSWER:
            _handle_no_answer(
                call_log.patient.id,
                call_log.appointment.id if call_log.appointment else None,
                call_log.call_type,
                call_log.attempt_number
            )
        
        return {'status': 'success', 'call_log_id': call_log.id}
        
    except CallLog.DoesNotExist:
        logger.error(f"CallLog not found for Twilio SID: {call_sid}")
        return {'status': 'error', 'message': 'CallLog not found'}
    
    except Exception as e:
        logger.error(f"Error processing call status: {str(e)}")
        return {'status': 'error', 'message': str(e)}
