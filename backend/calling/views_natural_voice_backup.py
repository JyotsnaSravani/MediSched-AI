"""
Natural Voice Calling Views - Working Version
Uses Twilio Speech Recognition (no WebSocket, no GPT-4o-mini)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from .models import CallLog, ManualCallbackTask
from .serializers import (
    CallLogSerializer,
    InitiateCallSerializer,
    ManualCallbackTaskSerializer,
    CompleteCallbackTaskSerializer
)
from .tasks import call_patient, process_call_status
from users.permissions import IsAdminOrStaff

import logging

logger = logging.getLogger(__name__)


# Copy all the ViewSet classes from the old file...
# (CallLogViewSet, ManualCallbackTaskViewSet)


@csrf_exempt
@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def twiml_conversational(request):
    """
    Natural Voice Conversations using Twilio Speech Recognition.
    No WebSocket needed - works through Ngrok free tier!
    """
    from twilio.twiml.voice_response import VoiceResponse, Gather
    from patients.models import Patient
    from scheduling.models import Appointment
    
    # Get parameters
    call_type = request.GET.get('call_type', 'GENERAL')
    patient_id = request.GET.get('patient_id')
    call_log_id = request.GET.get('call_log_id')
    
    # Get speech result from Twilio
    speech_result = request.POST.get('SpeechResult', '').lower()
    
    try:
        patient = Patient.objects.get(id=patient_id)
        appointment = None
        
        # Get appointment if needed
        if call_type in ['APPOINTMENT_REMINDER', 'APPOINTMENT_CONFIRMATION', 'FOLLOW_UP']:
            try:
                call_log = CallLog.objects.get(id=call_log_id)
                appointment = call_log.appointment
            except:
                pass
        
        response = VoiceResponse()
        first_name = patient.full_name.split()[0]
        
        # If speech result exists, handle it
        if speech_result:
            logger.info(f"Patient said: {speech_result}")
            return handle_speech_input(request, patient, speech_result, call_type, appointment, call_log_id)
        
        # Initial greeting - Professional and clear
        gather = response.gather(
            input='speech',
            action=f'/api/v1/calling/twiml-conversational/?patient_id={patient_id}&call_log_id={call_log_id}&call_type={call_type}',
            method='POST',
            timeout=5,
            speech_timeout='auto',
            language='en-US'
        )
        gather.say(
            f"Hello, this is MediSched AI. I'm calling regarding your appointment consultation. Would you like to book an appointment now?",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say("I didn't hear a response. Please call us back. Thank you!", voice='Polly.Joanna')
        response.hangup()
        
        logger.info(f"Natural voice call initiated for patient {patient_id}")
        return HttpResponse(str(response), content_type='text/xml')
        
    except Patient.DoesNotExist:
        logger.error(f"Patient {patient_id} not found")
        response = VoiceResponse()
        response.say(
            "We're sorry, we couldn't find your information. Please call our office directly.",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
        
    except Exception as e:
        logger.error(f"Error in TwiML webhook: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        response = VoiceResponse()
        response.say(
            "We're sorry, we're experiencing technical difficulties. Please call our office directly. Goodbye.",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')


def handle_speech_input(request, patient, speech_text, call_type, appointment=None, call_log_id=None):
    """Handle natural voice input from patient."""
    from twilio.twiml.voice_response import VoiceResponse, Gather
    from doctors.models import DoctorSlot, Doctor
    from scheduling.models import Appointment as AppointmentModel
    from django.utils import timezone
    from datetime import timedelta
    
    response = VoiceResponse()
    first_name = patient.full_name.split()[0]
    
    # Get action parameter to track conversation state
    action = request.GET.get('action', '')
    
    # Detect intent from speech - NATURAL and SHORT
    if any(word in speech_text for word in ['book', 'schedule', 'appointment', 'make', 'need', 'trouble', 'help', 'sick', 'pain']):
        # Book appointment intent - Ask for preferred date (SHORT)
        gather = response.gather(
            input='speech',
            action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=get_date',
            method='POST',
            timeout=3,
            speech_timeout='auto',
            language='en-US'
        )
        
        # Handle emotional statements naturally
        if any(word in speech_text for word in ['trouble', 'sick', 'pain', 'emergency', 'urgent']):
            gather.say(
                f"I'm sorry to hear that. What day works for you?",
                voice='Polly.Joanna',
                language='en-US'
            )
        else:
            gather.say(
                f"Sure! What day works?",
                voice='Polly.Joanna',
                language='en-US'
            )
        response.say("Didn't catch that. Call back!", voice='Polly.Joanna')
    
    elif action == 'get_date':
        # Patient provided a date - Ask for time preference (SHORT)
        gather = response.gather(
            input='speech',
            action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=get_time&preferred_date={speech_text}',
            method='POST',
            timeout=3,
            speech_timeout='auto',
            language='en-US'
        )
        gather.say(
            f"Got it. What time?",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say("Didn't catch that. Call back!", voice='Polly.Joanna')
    
    elif action == 'get_time':
        # Patient provided time - Find and book slot
        preferred_date = request.GET.get('preferred_date', '')
        
        try:
            # Get doctor (assigned or first available)
            doctor = patient.assigned_doctor
            if not doctor:
                doctor = Doctor.objects.filter(status='ACTIVE').first()
            
            if not doctor:
                response.say(
                    "Sorry, no doctors available. Call the office!",
                    voice='Polly.Joanna',
                    language='en-US'
                )
            else:
                # Parse time preference
                time_preference = 'any'
                if any(word in speech_text for word in ['morning', 'am']):
                    time_preference = 'morning'
                elif any(word in speech_text for word in ['afternoon', 'pm', '2', '3', '4']):
                    time_preference = 'afternoon'
                elif any(word in speech_text for word in ['evening', 'night', '5', '6']):
                    time_preference = 'evening'
                
                # Get available slots
                today = timezone.now().date()
                next_week = today + timedelta(days=7)
                
                slots_query = DoctorSlot.objects.filter(
                    doctor=doctor,
                    slot_date__gte=today,
                    slot_date__lte=next_week,
                    status='AVAILABLE'
                )
                
                # Filter by time preference
                if time_preference == 'morning':
                    slots_query = slots_query.filter(start_time__hour__lt=12)
                elif time_preference == 'afternoon':
                    slots_query = slots_query.filter(start_time__hour__gte=12, start_time__hour__lt=17)
                elif time_preference == 'evening':
                    slots_query = slots_query.filter(start_time__hour__gte=17)
                
                slots = slots_query.order_by('slot_date', 'start_time')[:3]
                
                if slots:
                    # Book the first available slot
                    slot = slots[0]
                    
                    # Book the slot
                    slot.status = 'BOOKED'
                    slot.booked_patient = patient
                    slot.booked_at = timezone.now()
                    slot.save()
                    
                    # Create appointment
                    appt = AppointmentModel.objects.create(
                        slot=slot,
                        patient=patient,
                        status='CONFIRMED',
                        notes=f'Booked via AI call - Preferred: {preferred_date} {speech_text}'
                    )
                    
                    # Confirm booking - SHORT and natural
                    response.say(
                        f"Done! {slot.slot_date.strftime('%A %B %d')} at {slot.start_time.strftime('%I:%M %p')}. See you then!",
                        voice='Polly.Joanna',
                        language='en-US'
                    )
                    
                    # Send SMS confirmation
                    try:
                        from reminders.models import ReminderLog
                        from reminders.tasks import _send_sms
                        
                        msg = (
                            f"Appointment confirmed! Dr. {doctor.full_name.split()[-1]} on "
                            f"{slot.slot_date.strftime('%b %d')} at {slot.start_time.strftime('%I:%M %p')}. "
                            f"See you then!"
                        )
                        
                        reminder = ReminderLog.objects.create(
                            appointment=appt,
                            patient=patient,
                            reminder_type=ReminderLog.ReminderType.BOOKING_CONFIRMATION,
                            channel=ReminderLog.Channel.SMS,
                            message_text=msg
                        )
                        
                        if _send_sms(patient.phone_number, msg, reminder):
                            reminder.mark_sent()
                    except Exception as e:
                        logger.error(f"SMS error: {e}")
                else:
                    response.say(
                        f"Sorry, no {time_preference} slots next week. Call the office!",
                        voice='Polly.Joanna',
                        language='en-US'
                    )
        except Exception as e:
            logger.error(f"Booking error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            response.say(
                "Sorry, had trouble booking. Call the office!",
                voice='Polly.Joanna',
                language='en-US'
            )
    
    elif any(word in speech_text for word in ['check', 'what', 'when', 'my appointment', 'existing']):
        # Check appointments intent - SHORT
        appointments = AppointmentModel.objects.filter(
            patient=patient,
            status='CONFIRMED',
            slot__slot_date__gte=timezone.now().date()
        ).order_by('slot__slot_date', 'slot__start_time')[:3]
        
        if appointments:
            appt = appointments[0]  # Just tell them the next one
            response.say(
                f"{appt.slot.slot_date.strftime('%A %B %d')} at {appt.slot.start_time.strftime('%I:%M %p')}.",
                voice='Polly.Joanna',
                language='en-US'
            )
        else:
            response.say(
                "No appointments. Want to book one?",
                voice='Polly.Joanna',
                language='en-US'
            )
    
    elif any(word in speech_text for word in ['confirm', 'yes', 'yeah', 'sure', 'okay', 'ok']):
        # Confirmation intent - SHORT
        if call_type == 'APPOINTMENT_REMINDER' and appointment:
            appointment.status = 'CONFIRMED'
            appointment.save()
            response.say(
                f"Great! {appointment.slot.slot_date.strftime('%B %d')} at {appointment.slot.start_time.strftime('%I:%M %p')}. See you!",
                voice='Polly.Joanna',
                language='en-US'
            )
        else:
            response.say(
                "Anything else?",
                voice='Polly.Joanna',
                language='en-US'
            )
    
    elif any(word in speech_text for word in ['cancel', 'reschedule', 'change', 'move']):
        # Cancel/reschedule intent - SHORT
        response.say(
            "Call the office to reschedule. Thanks!",
            voice='Polly.Joanna',
            language='en-US'
        )
    
    elif any(word in speech_text for word in ['office', 'speak', 'talk', 'person', 'human', 'staff']):
        # Speak with office intent - SHORT
        response.say(
            "Call us during business hours. Thanks!",
            voice='Polly.Joanna',
            language='en-US'
        )
    
    else:
        # Didn't understand - SHORT
        response.say(
            "Sorry, didn't get that. Try again?",
            voice='Polly.Joanna',
            language='en-US'
        )
    
    response.hangup()
    return HttpResponse(str(response), content_type='text/xml')


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def status_callback(request):
    """Twilio status callback."""
    call_sid = request.POST.get('CallSid')
    call_status = request.POST.get('CallStatus')
    call_duration = request.POST.get('CallDuration', 0)
    
    logger.info(f"Status callback: {call_sid} - {call_status} - {call_duration}s")
    
    process_call_status.delay(
        call_sid=call_sid,
        call_status=call_status,
        call_duration=int(call_duration)
    )
    
    return HttpResponse('OK', status=200)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def recording_callback(request):
    """Twilio recording callback."""
    call_sid = request.POST.get('CallSid')
    recording_url = request.POST.get('RecordingUrl')
    
    logger.info(f"Recording callback: {call_sid} - {recording_url}")
    
    try:
        call_log = CallLog.objects.get(twilio_call_sid=call_sid)
        call_log.twilio_recording_url = recording_url
        call_log.transcription_status = CallLog.TranscriptionStatus.PENDING
        call_log.save()
        
        from transcriptions.tasks import transcribe_call
        transcribe_call.delay(call_log.id)
        
    except CallLog.DoesNotExist:
        logger.error(f"CallLog not found for SID: {call_sid}")
    
    return HttpResponse('OK', status=200)
