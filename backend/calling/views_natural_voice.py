"""
Natural Voice Calling Views - MediSched AI Flow
Follows exact conversation flow with proper greeting, slot checking, and patient questions
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


def add_conversation_turn(call_log_id, speaker, message):
    """Add a conversation turn to the call log notes for transcription."""
    try:
        from .transcription_fixer import fix_transcription
        
        call_log = CallLog.objects.get(id=call_log_id)
        
        # Get patient and doctor names for context-aware fixing
        patient_name = call_log.patient.full_name if call_log.patient else None
        doctor_name = None
        if call_log.appointment and call_log.appointment.slot:
            doctor_name = call_log.appointment.slot.doctor.full_name
        
        # Fix transcription errors
        fixed_message = fix_transcription(message, patient_name=patient_name, doctor_name=doctor_name)
        
        if not call_log.notes:
            call_log.notes = ""
        call_log.notes += f"\n{speaker}: {fixed_message}"
        call_log.save()
    except Exception as e:
        logger.warning(f"Failed to add conversation turn: {e}")
        pass


@csrf_exempt
@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def twiml_conversational(request):
    """
    Natural Voice Conversations using Twilio Speech Recognition.
    Follows MediSched AI conversation flow.
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
            except CallLog.DoesNotExist:
                logger.warning(f"CallLog {call_log_id} not found")
                pass
        
        response = VoiceResponse()
        first_name = patient.full_name.split()[0]
        
        # If speech result exists, handle it
        if speech_result:
            logger.info(f"Patient said: {speech_result}")
            # Capture patient's response
            add_conversation_turn(call_log_id, "Patient", speech_result)
            return handle_speech_input(request, patient, speech_result, call_type, appointment, call_log_id)
        
        # Initial greeting - Natural, friendly greeting with patient name
        ai_message = f"Hi {first_name}! This is MediSched AI calling. I can help you book an appointment today. Would you like to schedule one?"
        add_conversation_turn(call_log_id, "AI", ai_message)
        
        # Get doctor name for speech hints
        doctor_name = patient.assigned_doctor.full_name if patient.assigned_doctor else ""
        doctor_last_name = doctor_name.split()[-1] if doctor_name else ""
        
        # Build speech hints with patient name, doctor name, and company name
        speech_hints = f'{first_name}, {doctor_last_name}, MediSched, yes, no, appointment, book, schedule'
        
        gather = response.gather(
            input='speech',
            action=f'/api/v1/calling/twiml-conversational/?patient_id={patient_id}&call_log_id={call_log_id}&call_type={call_type}',
            method='POST',
            timeout=8,  # Increased from 5 to 8 seconds
            speech_timeout='auto',
            language='en-US',
            hints=speech_hints  # Dynamic hints with patient and doctor names
        )
        gather.say(
            ai_message,
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
            "Sorry, we couldn't find your information in our system. Give our office a call and we'll get you sorted.",
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
            "Oops, we're having some technical issues. Please call our office and we'll help you out. Sorry about that!",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')


def handle_speech_input(request, patient, speech_text, call_type, appointment=None, call_log_id=None):
    """Handle natural voice input from patient - Following exact MediSched AI conversation flow."""
    from twilio.twiml.voice_response import VoiceResponse, Gather
    from doctors.models import DoctorSlot, Doctor
    from scheduling.models import Appointment as AppointmentModel
    from django.utils import timezone
    from datetime import timedelta, datetime
    import re
    
    response = VoiceResponse()
    first_name = patient.full_name.split()[0]
    
    # Get action parameter to track conversation state
    action = request.GET.get('action', '')
    
    # PATIENT QUESTIONS FLOW - Handle first
    if any(word in speech_text for word in ['document', 'documents', 'bring', 'carry', 'need to bring']):
        response.say(
            "Sure! Just bring any previous medical reports, prescriptions, and a valid ID. That's all you need.",
            voice='Polly.Joanna',
            language='en-US'
        )
        # Ask if anything else
        gather = response.gather(
            input='speech',
            action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=anything_else',
            method='POST',
            timeout=5,
            speech_timeout='auto',
            language='en-US'
        )
        gather.say(
            "Anything else I can help with?",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say("Alright, have a great day!", voice='Polly.Joanna')
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
    
    elif any(word in speech_text for word in ['fee', 'fees', 'cost', 'charge', 'price', 'consultation fee']):
        response.say(
            "The consultation fee is 500 rupees.",
            voice='Polly.Joanna',
            language='en-US'
        )
        # Ask if anything else
        gather = response.gather(
            input='speech',
            action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=anything_else',
            method='POST',
            timeout=5,
            speech_timeout='auto',
            language='en-US'
        )
        gather.say(
            "Anything else you'd like to know?",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say("Alright, have a great day!", voice='Polly.Joanna')
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
    
    elif any(word in speech_text for word in ['reschedule', 'cancel', 'change appointment', 'modify']) and action == 'anything_else':
        # They're asking about rescheduling after booking
        response.say(
            "Yes, absolutely! You can reschedule or cancel anytime before your appointment.",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say(
            "Alright, have a great day!",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
    
    # BOOKING FLOW
    if any(word in speech_text for word in ['yes', 'yeah', 'sure', 'okay', 'book', 'appointment']) and action == '':
        # Patient wants to book - Ask for date and time
        gather = response.gather(
            input='speech',
            action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=get_datetime',
            method='POST',
            timeout=8,  # Increased from 5 to 8 seconds
            speech_timeout='auto',
            language='en-US',
            hints='tomorrow, today, Monday, Tuesday, Wednesday, Thursday, Friday, morning, afternoon, evening'
        )
        gather.say(
            "Great! What date and time works best for you?",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say("Sorry, I didn't catch that. Call us back anytime!", voice='Polly.Joanna')
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
    
    elif action == 'get_datetime':
        # Patient provided date and time - Check availability
        response.say(
            "Let me check that for you.",
            voice='Polly.Joanna',
            language='en-US'
        )
        
        return check_and_book_slot(request, patient, speech_text, call_log_id, call_type, response)
    
    elif action == 'confirm_booking':
        # Patient confirmed - Book the slot
        return confirm_booking(request, patient, speech_text, call_log_id, call_type, response)
    
    elif action == 'select_alternative':
        # Patient selected an alternative slot
        return select_alternative_slot(request, patient, speech_text, call_log_id, call_type, response)
    
    elif action == 'anything_else':
        # Patient answered "anything else" question
        if any(word in speech_text for word in ['no', 'nope', 'nothing', 'that\'s all', 'all good']):
            response.say(
                "Perfect! Have a great day!",
                voice='Polly.Joanna',
                language='en-US'
            )
            response.hangup()
            return HttpResponse(str(response), content_type='text/xml')
        else:
            # They have another question - ask what they need help with
            gather = response.gather(
                input='speech',
                action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}',
                method='POST',
                timeout=8,
                speech_timeout='auto',
                language='en-US',
                hints='appointment, documents, fees, location, hours, reschedule, cancel'
            )
            gather.say(
                "Sure! What do you need help with?",
                voice='Polly.Joanna',
                language='en-US'
            )
            response.say("Give us a call back anytime!", voice='Polly.Joanna')
            response.hangup()
            return HttpResponse(str(response), content_type='text/xml')
    
    else:
        # Didn't understand
        response.say(
            "Sorry, I didn't quite get that. Give us a call at the office and we'll help you out.",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say("Take care!", voice='Polly.Joanna')
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')


def parse_date_from_speech(speech_text):
    """Parse date from speech text with improved parsing."""
    from datetime import timedelta, datetime
    from django.utils import timezone
    import re
    
    today = timezone.now().date()
    
    # Try to parse specific dates like "25th of May", "May 25", "25 May 2026"
    # Pattern 1: "25th of May 2026" or "25th May 2026"
    date_pattern1 = r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([a-zA-Z]+)\s*,?\s*(\d{4})?'
    match = re.search(date_pattern1, speech_text, re.IGNORECASE)
    
    if match:
        day = int(match.group(1))
        month_str = match.group(2).lower()
        year = int(match.group(3)) if match.group(3) else today.year
        
        # Month name to number mapping
        months = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        
        month = months.get(month_str, today.month)
        
        try:
            parsed_date = datetime(year, month, day).date()
            
            # CRITICAL: Prevent booking past dates
            if parsed_date < today:
                logger.warning(f"Parsed date {parsed_date} is in the past, using tomorrow instead")
                parsed_date = today + timedelta(days=1)
            
            logger.info(f"Parsed date: {parsed_date} from speech: {speech_text}")
            return parsed_date
        except ValueError:
            logger.error(f"Invalid date: {day}/{month}/{year}")
    
    # Pattern 2: "May 25" or "May 25th"
    date_pattern2 = r'([a-zA-Z]+)\s+(\d{1,2})(?:st|nd|rd|th)?'
    match = re.search(date_pattern2, speech_text, re.IGNORECASE)
    
    if match:
        month_str = match.group(1).lower()
        day = int(match.group(2))
        year = today.year
        
        months = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        
        month = months.get(month_str, today.month)
        
        try:
            parsed_date = datetime(year, month, day).date()
            
            # CRITICAL: Prevent booking past dates
            if parsed_date < today:
                logger.warning(f"Parsed date {parsed_date} is in the past, using tomorrow instead")
                parsed_date = today + timedelta(days=1)
            
            logger.info(f"Parsed date: {parsed_date} from speech: {speech_text}")
            return parsed_date
        except ValueError:
            logger.error(f"Invalid date: {day}/{month}/{year}")
    
    # Relative dates
    if 'tomorrow' in speech_text:
        return today + timedelta(days=1)
    elif 'today' in speech_text:
        return today
    elif 'day after tomorrow' in speech_text:
        return today + timedelta(days=2)
    
    # Day names - ALWAYS return NEXT occurrence (never past)
    elif 'monday' in speech_text:
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    elif 'tuesday' in speech_text:
        days_ahead = 1 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    elif 'wednesday' in speech_text:
        days_ahead = 2 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    elif 'thursday' in speech_text:
        days_ahead = 3 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    elif 'friday' in speech_text:
        days_ahead = 4 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    elif 'saturday' in speech_text:
        days_ahead = 5 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    elif 'sunday' in speech_text:
        days_ahead = 6 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    else:
        # Default to tomorrow if can't parse
        logger.warning(f"Could not parse date from: {speech_text}, defaulting to tomorrow")
        return today + timedelta(days=1)


def parse_time_from_speech(speech_text):
    """Parse time (hour) from speech text with improved parsing."""
    import re
    
    # Try to parse specific times like "11 AM", "11:00 AM", "11:30 AM"
    # Pattern: "11 AM" or "11:00 AM" or "11:30 AM"
    time_pattern = r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?'
    matches = list(re.finditer(time_pattern, speech_text, re.IGNORECASE))
    
    # PRIORITY 1: Find matches WITH AM/PM indicators (most reliable)
    matches_with_ampm = []
    for match in matches:
        hour = int(match.group(1))
        am_pm = match.group(3)
        if am_pm and 1 <= hour <= 12:  # Valid 12-hour format with AM/PM
            matches_with_ampm.append(match)
    
    if matches_with_ampm:
        # Use the LAST match with AM/PM (time usually comes after date)
        match = matches_with_ampm[-1]
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        am_pm = match.group(3).lower().replace('.', '')  # Remove dots from "p.m." or "a.m."
        
        # Convert to 24-hour format
        if 'pm' in am_pm and hour != 12:
            hour += 12
        elif 'am' in am_pm and hour == 12:
            hour = 0
        
        logger.info(f"Parsed time: {hour}:{minute:02d} from speech: {speech_text} (matched with AM/PM)")
        return hour
    
    # PRIORITY 2: Find matches without AM/PM but valid hours (1-12 or 13-23)
    valid_matches = []
    for match in matches:
        hour = int(match.group(1))
        am_pm = match.group(3)
        # Only consider if no AM/PM and hour is reasonable (1-12 for ambiguous, 13-23 for clear PM)
        if not am_pm and (1 <= hour <= 12 or 13 <= hour <= 23):
            valid_matches.append(match)
    
    if valid_matches:
        # Use the LAST valid match (time usually comes after date)
        match = valid_matches[-1]
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        
        # If hour is 1-12, use smart context-based interpretation
        if 1 <= hour <= 12:
            speech_lower = speech_text.lower()
            # Explicit PM indicators
            if any(word in speech_lower for word in ['afternoon', 'evening', 'night', 'pm']):
                hour += 12 if hour != 12 else 0
            # Explicit AM indicators
            elif any(word in speech_lower for word in ['morning', 'am']):
                pass  # Keep as-is
            # Smart default: Business hours are typically PM for 1-5, AM for 6-12
            elif 1 <= hour <= 5:
                hour += 12  # Assume PM for 1-5 (13:00-17:00)
            # 6-8 could be morning or evening, default to morning
            # 9-12 are clearly morning hours
        
        logger.info(f"Parsed time: {hour}:{minute:02d} from speech: {speech_text} (matched without AM/PM)")
        return hour
    
    # PRIORITY 3: Fallback to keyword matching
    speech_lower = speech_text.lower()
    if '11 am' in speech_lower or '11am' in speech_lower or 'eleven am' in speech_lower or '11:00 am' in speech_lower or '11 a.m.' in speech_lower or '11:00 a.m.' in speech_lower:
        return 11
    elif '10 am' in speech_lower or '10am' in speech_lower or 'ten am' in speech_lower or '10:00 am' in speech_lower or '10 a.m.' in speech_lower or '10:00 a.m.' in speech_lower:
        return 10
    elif '9 am' in speech_lower or '9am' in speech_lower or 'nine am' in speech_lower or '9:00 am' in speech_lower or '9 a.m.' in speech_lower or '9:00 a.m.' in speech_lower:
        return 9
    elif '5 pm' in speech_lower or '5pm' in speech_lower or 'five pm' in speech_lower or '5:00 pm' in speech_lower or '5 p.m.' in speech_lower or '5:00 p.m.' in speech_lower:
        return 17
    elif '3 pm' in speech_lower or '3pm' in speech_lower or 'three pm' in speech_lower or '3:00 pm' in speech_lower or '3 p.m.' in speech_lower or '3:00 p.m.' in speech_lower:
        return 15
    elif '2 pm' in speech_lower or '2pm' in speech_lower or 'two pm' in speech_lower or '2:00 pm' in speech_lower or '2 p.m.' in speech_lower or '2:00 p.m.' in speech_lower:
        return 14
    elif '4 pm' in speech_lower or '4pm' in speech_lower or 'four pm' in speech_lower or '4:00 pm' in speech_lower or '4 p.m.' in speech_lower or '4:00 p.m.' in speech_lower:
        return 16
    elif '12 pm' in speech_lower or '12pm' in speech_lower or 'twelve pm' in speech_lower or '12:00 pm' in speech_lower or '12 p.m.' in speech_lower or 'noon' in speech_lower:
        return 12
    elif 'morning' in speech_lower:
        return 10  # Default morning time
    elif 'afternoon' in speech_lower:
        return 14  # Default afternoon time
    elif 'evening' in speech_lower:
        return 17  # Default evening time
    else:
        logger.warning(f"Could not parse time from: {speech_text}, defaulting to 10 AM")
        return 10  # Default time


def check_and_book_slot(request, patient, speech_text, call_log_id, call_type, response):
    """Check slot availability and offer alternatives if not available."""
    from twilio.twiml.voice_response import Gather
    from doctors.models import DoctorSlot, Doctor
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        # Parse date and time
        parsed_date = parse_date_from_speech(speech_text)
        parsed_time_hour = parse_time_from_speech(speech_text)
        
        # Validate hour is in valid range (0-23)
        if not (0 <= parsed_time_hour <= 23):
            logger.error(f"Invalid hour parsed: {parsed_time_hour}, defaulting to 10 AM")
            parsed_time_hour = 10  # Default to 10 AM
        
        # Create exact time object (hour:00:00)
        from datetime import time as time_obj
        try:
            parsed_time = time_obj(parsed_time_hour, 0, 0)
            logger.info(f"✓ Created time object: {parsed_time} from hour: {parsed_time_hour}")
        except ValueError as e:
            logger.error(f"Error creating time object: {e}, using 10:00 AM")
            parsed_time = time_obj(10, 0, 0)
            parsed_time_hour = 10
        
        logger.info(f"PARSED FROM SPEECH: date={parsed_date}, time={parsed_time}, hour={parsed_time_hour}, speech='{speech_text}'")
        
        # Get assigned doctor - ONLY book with assigned doctor
        doctor = patient.assigned_doctor
        if not doctor:
            response.say(
                "Hmm, looks like you don't have a doctor assigned yet. Give our office a quick call and we'll get that sorted for you.",
                voice='Polly.Joanna',
                language='en-US'
            )
            response.say("Take care!", voice='Polly.Joanna')
            response.hangup()
            return HttpResponse(str(response), content_type='text/xml')
        
        # Check if requested slot is available - Try EXACT time first
        logger.info(f"SLOT SEARCH QUERY: doctor_id={doctor.id}, doctor_name={doctor.full_name}, date={parsed_date}, time={parsed_time}, time_type={type(parsed_time)}")
        
        requested_slot = DoctorSlot.objects.filter(
            doctor=doctor,
            slot_date=parsed_date,
            start_time=parsed_time,  # Exact time match
            status='AVAILABLE'
        ).select_related('doctor').first()
        
        # If exact match not found, try finding nearest slot within 30 minutes
        if not requested_slot:
            from datetime import datetime, timedelta
            
            # Create datetime for time arithmetic
            base_datetime = datetime.combine(parsed_date, parsed_time)
            time_min = (base_datetime - timedelta(minutes=15)).time()
            time_max = (base_datetime + timedelta(minutes=15)).time()
            
            logger.info(f"Exact time not found, searching nearest slot between {time_min} and {time_max}")
            
            requested_slot = DoctorSlot.objects.filter(
                doctor=doctor,
                slot_date=parsed_date,
                start_time__gte=time_min,
                start_time__lte=time_max,
                status='AVAILABLE'
            ).select_related('doctor').order_by('start_time').first()
            
            if requested_slot:
                logger.info(f"Found nearest slot at {requested_slot.start_time}")
        
        # Debug: Check all slots for this doctor on this date
        all_slots_on_date = DoctorSlot.objects.filter(
            doctor=doctor,
            slot_date=parsed_date
        ).values_list('start_time', 'status')
        logger.info(f"All slots for {doctor.full_name} on {parsed_date}: {list(all_slots_on_date)}")
        
        logger.info(f"Slot search result: doctor={doctor.full_name}, date={parsed_date}, time={parsed_time}, found={'Yes' if requested_slot else 'No'}")
        
        if requested_slot:
            # SLOT IS AVAILABLE - Ask for confirmation
            gather = response.gather(
                input='speech',
                action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=confirm_booking&slot_id={requested_slot.id}',
                method='POST',
                timeout=8,  # Increased from 5 to 8 seconds - give patient more time
                speech_timeout='auto',
                language='en-US',
                hints='yes, yeah, okay, sure, confirm, book it'  # Help recognition
            )
            display_hour = parsed_time_hour if parsed_time_hour <= 12 else parsed_time_hour - 12
            am_pm = 'AM' if parsed_time_hour < 12 else 'PM'
            day_name = parsed_date.strftime('%A')
            gather.say(
                f"Good news! {day_name} at {display_hour} {am_pm} is available with Dr. {doctor.full_name.split()[-1]}. Should I book it for you?",
                voice='Polly.Joanna',
                language='en-US'
            )
            response.say("Sorry, didn't catch that. Call us back anytime!", voice='Polly.Joanna')
            response.hangup()
            return HttpResponse(str(response), content_type='text/xml')
        else:
            # SLOT NOT AVAILABLE - Offer alternatives from ASSIGNED DOCTOR ONLY
            logger.warning(f"No slot found for assigned doctor {doctor.full_name} on {parsed_date} at {parsed_time}, offering alternatives")
            today = timezone.now().date()
            alternative_slots = DoctorSlot.objects.filter(
                doctor=doctor,  # Only assigned doctor
                slot_date__gte=today,
                slot_date__lte=today + timedelta(days=7),
                status='AVAILABLE'
            ).select_related('doctor').order_by('slot_date', 'start_time')[:3]
            
            if alternative_slots:
                response.say(
                    "That slot's taken, but I've got some other options for you:",
                    voice='Polly.Joanna',
                    language='en-US'
                )
                
                # List alternatives from assigned doctor only
                for slot in alternative_slots:
                    hour = slot.start_time.hour
                    display_hour = hour if hour <= 12 else hour - 12
                    am_pm = 'AM' if hour < 12 else 'PM'
                    response.say(
                        f"{slot.slot_date.strftime('%A')} at {display_hour} {am_pm}",
                        voice='Polly.Joanna',
                        language='en-US'
                    )
                
                # Ask which option they prefer
                gather = response.gather(
                    input='speech',
                    action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=select_alternative',
                    method='POST',
                    timeout=8,  # Increased from 5 to 8 seconds
                    speech_timeout='auto',
                    language='en-US',
                    hints='yes, first, second, third, Tuesday, Wednesday, Thursday, morning, afternoon'
                )
                gather.say(
                    "Which one works for you?",
                    voice='Polly.Joanna',
                    language='en-US'
                )
                response.say("Didn't catch that. Call us back anytime!", voice='Polly.Joanna')
            else:
                response.say(
                    f"Sorry, Dr. {doctor.full_name.split()[-1]} is fully booked this week. Give our office a call and we'll find something that works.",
                    voice='Polly.Joanna',
                    language='en-US'
                )
                response.say("Take care!", voice='Polly.Joanna')
            
            response.hangup()
            return HttpResponse(str(response), content_type='text/xml')
            
    except Exception as e:
        logger.error(f"Error checking availability: {e}")
        import traceback
        logger.error(traceback.format_exc())
        response.say(
            "Oops, I'm having trouble checking that. Give our office a call and they'll help you out.",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say("Take care!", voice='Polly.Joanna')
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')


def confirm_booking(request, patient, speech_text, call_log_id, call_type, response):
    """Confirm and book the selected slot."""
    from twilio.twiml.voice_response import Gather
    from doctors.models import DoctorSlot
    from scheduling.models import Appointment as AppointmentModel
    from django.utils import timezone
    
    slot_id = request.GET.get('slot_id')
    
    if any(word in speech_text for word in ['yes', 'yeah', 'sure', 'okay', 'confirm']):
        try:
            slot = DoctorSlot.objects.get(id=slot_id, status='AVAILABLE')
            
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
                notes=f'Booked via AI call'
            )
            
            # Confirm booking
            hour = slot.start_time.hour
            display_hour = hour if hour <= 12 else hour - 12
            am_pm = 'AM' if hour < 12 else 'PM'
            doctor_name = slot.doctor.full_name.split()[-1]
            
            response.say(
                f"Perfect! You're all set for {slot.slot_date.strftime('%A')} at {display_hour} {am_pm} with Dr. {doctor_name}.",
                voice='Polly.Joanna',
                language='en-US'
            )
            
            # Send SMS and Email confirmation
            try:
                from reminders.models import ReminderLog
                from reminders.tasks import _send_sms, _send_email
                
                msg = (
                    f"Appointment confirmed! {slot.slot_date.strftime('%A, %b %d')} at "
                    f"{display_hour}:{slot.start_time.strftime('%M')} {am_pm} with Dr. {slot.doctor.full_name}. See you then!"
                )
                
                # Determine channel based on patient contact info
                has_phone = bool(patient.phone_number)
                has_email = bool(patient.email)
                
                if has_phone and has_email:
                    channel = ReminderLog.Channel.BOTH
                elif has_email:
                    channel = ReminderLog.Channel.EMAIL
                else:
                    channel = ReminderLog.Channel.SMS
                
                reminder = ReminderLog.objects.create(
                    appointment=appt,
                    patient=patient,
                    reminder_type=ReminderLog.ReminderType.BOOKING_CONFIRMATION,
                    channel=channel,
                    message_text=msg
                )
                
                # Send SMS if phone number available
                sms_success = False
                if has_phone:
                    sms_success = _send_sms(patient.phone_number, msg, reminder)
                
                # Send Email if email available
                email_success = False
                if has_email:
                    email_success = _send_email(
                        patient.email,
                        "Appointment Confirmation - MediSched AI",
                        msg,
                        reminder
                    )
                
                # Mark as sent if either succeeded
                if sms_success or email_success:
                    reminder.mark_sent()
                    logger.info(f"Booking confirmation sent: SMS={sms_success}, Email={email_success}")
            except Exception as e:
                logger.error(f"Confirmation error: {e}")
            
            # Ask if anything else
            gather = response.gather(
                input='speech',
                action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=anything_else',
                method='POST',
                timeout=5,
                speech_timeout='auto',
                language='en-US'
            )
            gather.say(
                "Anything else I can help with?",
                voice='Polly.Joanna',
                language='en-US'
            )
            response.say("Alright, have a great day!", voice='Polly.Joanna')
            response.hangup()
            return HttpResponse(str(response), content_type='text/xml')
            
        except DoctorSlot.DoesNotExist:
            response.say(
                "Oh no, someone just grabbed that slot. Give us a call and we'll find you another one.",
                voice='Polly.Joanna',
                language='en-US'
            )
            response.say("Take care!", voice='Polly.Joanna')
            response.hangup()
            return HttpResponse(str(response), content_type='text/xml')
    else:
        response.say(
            "No worries! Call us back whenever you're ready.",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say("Take care!", voice='Polly.Joanna')
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')


def select_alternative_slot(request, patient, speech_text, call_log_id, call_type, response):
    """Book the alternative slot selected by patient - ONLY FROM ASSIGNED DOCTOR."""
    from twilio.twiml.voice_response import Gather
    from doctors.models import DoctorSlot, Doctor
    from scheduling.models import Appointment as AppointmentModel
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        # Get assigned doctor
        doctor = patient.assigned_doctor
        if not doctor:
            response.say(
                "Hmm, looks like you don't have a doctor assigned yet. Give our office a call and we'll sort that out.",
                voice='Polly.Joanna',
                language='en-US'
            )
            response.say("Take care!", voice='Polly.Joanna')
            response.hangup()
            return HttpResponse(str(response), content_type='text/xml')
        
        # Check if patient is just confirming the first option (e.g., "yes", "first one", "that one", "give it", "book it")
        confirmation_phrases = ['yes', 'yeah', 'sure', 'okay', 'first', 'that one', 'give it', 'book it', 'no need']
        is_simple_confirmation = any(phrase in speech_text.lower() for phrase in confirmation_phrases)
        
        # If simple confirmation, book the FIRST available slot from assigned doctor
        if is_simple_confirmation and len(speech_text.split()) <= 5:
            logger.info(f"Patient confirmed first alternative slot with: '{speech_text}'")
            today = timezone.now().date()
            selected_slot = DoctorSlot.objects.filter(
                doctor=doctor,
                slot_date__gte=today,
                slot_date__lte=today + timedelta(days=7),
                status='AVAILABLE'
            ).select_related('doctor').order_by('slot_date', 'start_time').first()
        else:
            # Parse their selection (they specified a date/time)
            parsed_date = parse_date_from_speech(speech_text)
            parsed_time_hour = parse_time_from_speech(speech_text)
            
            # Create exact time object
            from datetime import time as time_obj
            parsed_time = time_obj(parsed_time_hour, 0, 0)
            
            logger.info(f"Alternative selection - Parsed date: {parsed_date}, time: {parsed_time}")
            
            # Find the slot from ASSIGNED DOCTOR ONLY with EXACT time
            selected_slot = DoctorSlot.objects.filter(
                doctor=doctor,  # Only assigned doctor
                slot_date=parsed_date,
                start_time=parsed_time,  # Exact time match
                status='AVAILABLE'
            ).select_related('doctor').first()
        
        if selected_slot:
            # Book the slot
            selected_slot.status = 'BOOKED'
            selected_slot.booked_patient = patient
            selected_slot.booked_at = timezone.now()
            selected_slot.save()
            
            # Create appointment
            appt = AppointmentModel.objects.create(
                slot=selected_slot,
                patient=patient,
                status='CONFIRMED',
                notes=f'Booked via AI call - Alternative slot'
            )
            
            # Confirm booking with doctor name
            hour = selected_slot.start_time.hour
            display_hour = hour if hour <= 12 else hour - 12
            am_pm = 'AM' if hour < 12 else 'PM'
            doctor_name = selected_slot.doctor.full_name.split()[-1]
            
            response.say(
                f"Awesome! You're all set for {selected_slot.slot_date.strftime('%A')} at {display_hour} {am_pm} with Dr. {doctor_name}.",
                voice='Polly.Joanna',
                language='en-US'
            )
            
            # Send SMS and Email confirmation
            try:
                from reminders.models import ReminderLog
                from reminders.tasks import _send_sms, _send_email
                
                msg = (
                    f"Appointment confirmed! {selected_slot.slot_date.strftime('%A, %b %d')} at "
                    f"{display_hour}:{selected_slot.start_time.strftime('%M')} {am_pm} with Dr. {selected_slot.doctor.full_name}. See you then!"
                )
                
                # Determine channel based on patient contact info
                has_phone = bool(patient.phone_number)
                has_email = bool(patient.email)
                
                if has_phone and has_email:
                    channel = ReminderLog.Channel.BOTH
                elif has_email:
                    channel = ReminderLog.Channel.EMAIL
                else:
                    channel = ReminderLog.Channel.SMS
                
                reminder = ReminderLog.objects.create(
                    appointment=appt,
                    patient=patient,
                    reminder_type=ReminderLog.ReminderType.BOOKING_CONFIRMATION,
                    channel=channel,
                    message_text=msg
                )
                
                # Send SMS if phone number available
                sms_success = False
                if has_phone:
                    sms_success = _send_sms(patient.phone_number, msg, reminder)
                
                # Send Email if email available
                email_success = False
                if has_email:
                    email_success = _send_email(
                        patient.email,
                        "Appointment Confirmation - MediSched AI",
                        msg,
                        reminder
                    )
                
                # Mark as sent if either succeeded
                if sms_success or email_success:
                    reminder.mark_sent()
                    logger.info(f"Booking confirmation sent: SMS={sms_success}, Email={email_success}")
            except Exception as e:
                logger.error(f"Confirmation error: {e}")
            
            # Ask if anything else
            gather = response.gather(
                input='speech',
                action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=anything_else',
                method='POST',
                timeout=5,
                speech_timeout='auto',
                language='en-US'
            )
            gather.say(
                "Anything else I can help with?",
                voice='Polly.Joanna',
                language='en-US'
            )
            response.say("Alright, have a great day!", voice='Polly.Joanna')
            response.hangup()
            return HttpResponse(str(response), content_type='text/xml')
        else:
            response.say(
                "I'm sorry, I couldn't find that slot. Please call our office for assistance.",
                voice='Polly.Joanna',
                language='en-US'
            )
            response.say("Thank you for choosing MediSched AI. Have a great day!", voice='Polly.Joanna')
            response.hangup()
            return HttpResponse(str(response), content_type='text/xml')
            
    except Exception as e:
        logger.error(f"Error selecting alternative: {e}")
        import traceback
        logger.error(traceback.format_exc())
        response.say(
            "I'm sorry, I had trouble booking that slot. Please call our office.",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say("Thank you for choosing MediSched AI. Have a great day!", voice='Polly.Joanna')
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
    
    # Always use synchronous processing (Celery not running)
    logger.info(f"Processing status callback synchronously for {call_sid}")
    from .tasks import process_call_status as process_call_status_sync
    process_call_status_sync(
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
        
        # Always use synchronous processing (Celery not running)
        logger.info(f"Processing transcription synchronously for call log {call_log.id}")
        from transcriptions.tasks import _transcribe_call_sync
        _transcribe_call_sync(call_log.id)
        
    except CallLog.DoesNotExist:
        logger.error(f"CallLog not found for SID: {call_sid}")
    except Exception as e:
        logger.error(f"Error in recording callback: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    return HttpResponse('OK', status=200)
