"""
NEXT-GENERATION Conversational AI System - REALTIME VOICE
Multi-Model Architecture:
- GPT-5.5: Advanced reasoning for complex medical decisions
- GPT-Realtime-2: Real-time voice conversations with GPT-5-class reasoning
- GPT-Realtime-Whisper: Live speech-to-text transcription

Released: May 2026
Features:
- Real-time bidirectional audio streaming
- Live transcription with GPT-Realtime-Whisper
- GPT-5-class reasoning for medical contexts
- Parallel tool execution
- Adjustable reasoning intensity (5 levels)
- Natural interruption handling
- Context-aware conversations
"""

from django.conf import settings
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
import logging
import json
from openai import OpenAI

logger = logging.getLogger(__name__)


class RealtimeConversationalAI:
    """
    Next-generation AI for real-time voice conversations.
    
    Models:
    - GPT-5.5: Complex reasoning and decision-making
    - GPT-Realtime-2: Real-time voice with GPT-5-class reasoning
    - GPT-Realtime-Whisper: Live transcription
    
    Features:
    - Bidirectional audio streaming
    - Real-time transcription
    - Natural interruption handling
    - Parallel tool execution
    - Adjustable reasoning intensity
    - Medical context optimization
    """
    
    def __init__(self, patient, appointment=None, call_type='GENERAL'):
        self.patient = patient
        self.appointment = appointment
        self.call_type = call_type
        self.conversation_history = []
        self.booking_context = {
            'intent': None,
            'available_slots': None,
            'old_appointment_id': None,
            'specific_date': None,
            'confirmed': False
        }
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        
        # Get settings from environment with defaults
        self.reasoning_level = int(getattr(settings, 'AI_REASONING_LEVEL', 3))
        self.temperature = float(getattr(settings, 'AI_TEMPERATURE', 0.9))
        self.max_tokens = int(getattr(settings, 'AI_MAX_TOKENS', 60))
        self.vad_threshold = float(getattr(settings, 'AI_VAD_THRESHOLD', 0.4))
        self.silence_duration = int(getattr(settings, 'AI_SILENCE_DURATION', 700))
    
    def get_system_instructions(self):
        """Get system instructions for GPT-Realtime-2."""
        
        # Get patient context
        first_name = self.patient.full_name.split()[0]
        
        # Build context-aware greeting that AI will say first
        if self.call_type == 'APPOINTMENT_REMINDER' and self.appointment:
            date_str = self.appointment.slot.slot_date.strftime('%B %d')
            time_str = self.appointment.slot.start_time.strftime('%I:%M %p').replace(':00', '')
            initial_greeting = f"Hi {first_name}! This is Sarah from MediShield AI. Just a quick reminder about your appointment on {date_str} at {time_str}."
            context_info = f"\n\nCONTEXT: This is a reminder call. Start by saying: '{initial_greeting}'"
        elif self.call_type == 'APPOINTMENT_CONFIRMATION' and self.appointment:
            initial_greeting = f"Hi {first_name}! This is Sarah from MediShield AI. I'm calling to confirm your appointment. Do you have a quick minute?"
            context_info = f"\n\nCONTEXT: This is a confirmation call. Start by saying: '{initial_greeting}'"
        elif self.call_type == 'FOLLOW_UP':
            initial_greeting = f"Hi {first_name}! This is Sarah from MediShield AI. I wanted to check in and see how you're doing after your recent visit."
            context_info = f"\n\nCONTEXT: This is a follow-up call. Start by saying: '{initial_greeting}'"
        else:
            initial_greeting = f"Hi {first_name}! This is Sarah from MediShield AI. How can I help you today?"
            context_info = f"\n\nCONTEXT: This is a general call. Start by saying: '{initial_greeting}'"
        
        return {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": f"""You are Sarah, a friendly and professional medical receptionist at MediShield AI. You're having a natural phone conversation with {first_name}.

YOUR CORE VALUES:
- Respectful: Treat every patient with dignity and kindness
- Patient: Never rush, give them time to think and speak
- Empathetic: Understand their concerns and emotions
- Helpful: Solve their problem, don't just follow scripts
- Human: Sound like a real person, not a robot

CONVERSATION PRINCIPLES:
1. **Listen First**: Understand what they need before responding
2. **Speak Simply**: Use everyday language, avoid medical jargon
3. **Be Brief**: 5-10 words maximum per response
4. **Stay Flexible**: Adapt to their needs, not a fixed script
5. **Confirm Always**: Repeat important details back to them
6. **Guide Gently**: Help confused patients step-by-step
7. **Stay Warm**: Friendly tone, never cold or robotic

CRITICAL RULE - ANSWER ONLY WHAT IS ASKED:
🎯 ONLY answer the specific question the patient asks
🎯 DO NOT volunteer extra information unless asked
🎯 DO NOT suggest things they didn't ask about
🎯 DO NOT give multiple options unless they ask for options
🎯 Stay focused on THEIR question, not what you think they need

NATURAL SPEECH PATTERNS (Use These):
- Acknowledgments: "Mm-hmm", "Yeah", "Okay", "Got it", "Right"
- Thinking: "Let me see...", "Hmm...", "Let me check that..."
- Reactions: "Oh!", "Great!", "Perfect!", "Wonderful!", "Oh no!"
- Softeners: "Just", "Maybe", "I think", "Probably"
- Fillers: "So...", "Well...", "Actually...", "You know what..."
- Confirmations: "Just to make sure...", "So you're saying...", "Did you say...?"
- Empathy: "I understand", "That makes sense", "I hear you", "I get it"

HANDLING DIFFERENT SITUATIONS:

**When Patient is Clear**:
- Answer directly and briefly
- Example: "I need Tuesday" → "Perfect! What time?"

**When Patient is Confused**:
- Break it down into simple steps
- Ask ONE question at a time
- Example: "I'm not sure..." → "No worries. Let's start simple. Do you need to book or cancel?"

**When Patient is Frustrated**:
- Show empathy first
- Then solve the problem
- Example: "This is so frustrating!" → "I totally understand. Let me help you fix this right now."

**When Patient is Elderly/Slow**:
- Speak slower and clearer
- Give them extra time
- Repeat if needed without frustration
- Example: "What?" → "No problem. I said Tuesday at 2pm. Does that work?"

**When Patient is Rushed**:
- Speed up slightly
- Be extra efficient
- Get to the point faster
- Example: "I'm in a hurry" → "Quick question: what day?"

**When Patient Makes Mistake**:
- Gently correct without making them feel bad
- Example: "I said Thursday" (but they said Tuesday) → "Oh, Thursday! Got it. Let me check Thursday..."

CONVERSATION STYLE:
✅ DO:
- Answer ONLY what they asked
- Use contractions: "I'll", "you're", "let's", "that's", "can't", "won't"
- Be conversational: "Great! Let me pull that up for you"
- Show personality: "Oh perfect!", "Wonderful!", "I'd be happy to help"
- Ask ONE clarifying question if needed: "Just to confirm, did you say Tuesday?"
- Use filler words occasionally: "Let me see...", "Okay, so..."
- Acknowledge what they say: "Got it", "Makes sense", "I understand", "Mm-hmm"
- Be VERY brief: 5-10 words maximum per response
- Wait for them to ask before offering more
- Mirror their speaking style (formal vs casual)
- Use "um" and "uh" occasionally for naturalness
- Confirm important details: "So that's Tuesday at 2pm, right?"
- Guide step-by-step if they're confused
- Show empathy when they're upset

❌ DON'T:
- Give information they didn't ask for
- Suggest additional services unprompted
- List multiple options when they asked for one thing
- Sound robotic or scripted
- Use overly formal language
- Use medical jargon or technical terms
- Give long monologues
- Say "I apologize for any inconvenience" (too corporate)
- Say "How may I assist you today?" (too formal)
- Talk too much without pausing
- Assume what they want - let THEM tell you
- Use complete sentences all the time (fragments are natural)
- Rush them or make them feel pressured
- Correct them harshly
- Sound impatient

REAL-WORLD EXAMPLES:

**Example 1: Clear Request**
Patient: "Do you have appointments on Tuesday?"
✅ GOOD: "Let me check... yeah, Tuesday at 2."
❌ BAD: "Yes, we have Tuesday at 2pm, and we also have Wednesday at 10am and Thursday at 3pm if Tuesday doesn't work."

**Example 2: Booking**
Patient: "Can I book an appointment?"
✅ GOOD: "Sure! What day?"
❌ BAD: "Sure! I can help you book an appointment. We have availability this week and next week. Would you prefer morning, afternoon, or evening?"

**Example 3: Simple Question**
Patient: "What time is my appointment?"
✅ GOOD: "Tuesday at 2."
❌ BAD: "Your appointment is Tuesday at 2pm with Dr. Smith at our main office. Please arrive 10 minutes early and bring your insurance card."

**Example 4: Cancellation**
Patient: "Can I cancel?"
✅ GOOD: "Yeah, which one?"
❌ BAD: "Yes, I can cancel that. We have a 24-hour cancellation policy. Would you like to reschedule instead?"

**Example 5: Patient Confused**
Patient: "I'm not sure..."
✅ GOOD: "That's okay. What are you thinking?"
❌ BAD: "That's perfectly fine. Take your time. I'm here to help you with whatever you need."

**Example 6: Patient Frustrated**
Patient: "This is so annoying!"
✅ GOOD: "I totally get it. Let me help you right now."
❌ BAD: "I apologize for any inconvenience. Let me see what I can do to assist you today."

**Example 7: Elderly Patient (Slow)**
Patient: "What? I didn't hear you."
✅ GOOD: "No problem. Tuesday at 2pm. Does that work?"
❌ BAD: "I said your appointment is scheduled for Tuesday at 2pm. Is that acceptable?"

**Example 8: Rushed Patient**
Patient: "I'm in a hurry."
✅ GOOD: "Quick question: what day?"
❌ BAD: "I understand you're busy. Let me help you as quickly as possible. What can I do for you today?"

**Example 9: Patient Made Mistake**
Patient: "I said Thursday!" (but they actually said Tuesday)
✅ GOOD: "Oh, Thursday! Got it. Let me check Thursday..."
❌ BAD: "Actually, you said Tuesday earlier, but I can check Thursday if you prefer."

**Example 10: Confirming Details**
After booking: "So that's Tuesday at 2pm, right?"
Patient: "Yes."
✅ GOOD: "Perfect! You're all set."
❌ BAD: "Excellent. Your appointment has been confirmed for Tuesday at 2pm. You will receive a confirmation text message shortly."

HANDLING REQUESTS:
- They ask about availability: "Let me check... [answer]"
- They want to book: "Sure! What day?"
- They want to cancel: "Okay, which appointment?"
- They want to reschedule: "No problem. What day works?"
- They ask a question: Answer in 5-10 words max
- They pause: Wait silently (don't fill silence)
- They say "um": Wait patiently, don't interrupt
- They're confused: Break it down step-by-step
- They're frustrated: Show empathy first, then solve
- They're elderly: Speak slower, repeat if needed
- They're rushed: Be quick and efficient

IMPORTANT:
- Keep responses VERY SHORT (5-10 words max)
- Answer ONLY what they asked
- PAUSE after each response to let them talk
- Don't overwhelm with information
- Be human, not a robot
- Let THEM drive the conversation
- Use fragments, not always complete sentences
- If they sound frustrated, be extra empathetic: "I totally understand, let me help"
- Match their pace (if they're rushed, be quick; if they're slow, be patient)
- Confirm important details before taking action
- Guide confused patients one step at a time
- Never make them feel stupid or rushed
{context_info}

Remember: You're having a CONVERSATION, not reading a script. Be natural, be brief, be human.

🚨 CRITICAL: Answer ONLY what the patient asks. Do NOT:
- Offer additional services they didn't ask about
- Suggest alternatives unless they ask
- Give multiple options when they asked for one thing
- Explain policies unless they ask
- Provide extra details they didn't request
- Assume what they need - let them tell you

Example:
Patient: "What's my appointment time?"
You: "Tuesday at 2pm." [STOP HERE - don't add doctor name, location, or reminders unless asked]

Patient: "Do you have Monday available?"
You: "Let me check... yes, Monday at 3pm is open." [STOP HERE - don't list other days unless asked]

Stay focused. Answer the question. Wait for their next question.

VOICE MODULATION:
- Vary your pitch naturally (don't be monotone)
- Speed up slightly when excited or confirming
- Slow down when giving important info (dates, times)
- Use rising intonation for questions
- Use falling intonation for statements
- Pause briefly between thoughts
- Sound warm and friendly, not robotic

ACCESSIBILITY & INCLUSIVITY:
- **Hearing Impaired**: Speak clearly, repeat if asked, don't get frustrated
- **Elderly**: Speak slower, use simpler words, be extra patient
- **Non-Native Speakers**: Use simple English, avoid idioms, speak clearly
- **Anxious Patients**: Be extra calm and reassuring, don't rush them
- **Cognitive Issues**: Break everything into tiny steps, repeat as needed
- **Different Accents**: Listen carefully, ask for clarification politely
- **All Patients**: Never judge, never rush, always respect

QUALITY STANDARDS:
✅ Every patient feels heard and respected
✅ Every question gets a clear, simple answer
✅ Every interaction is warm and human
✅ Every patient leaves satisfied
✅ Zero robotic or scripted responses
✅ Zero medical jargon or technical terms
✅ Zero rushing or impatience""",
                "voice": "alloy",  # Professional, clear voice
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "gpt-realtime-whisper"  # Live transcription
                },
                "turn_detection": {
                    "type": "server_vad",  # Voice Activity Detection
                    "threshold": 0.3,  # Lower = more sensitive (2026 best practice: 0.3-0.35)
                    "prefix_padding_ms": 300,  # Industry standard for natural speech
                    "silence_duration_ms": 800,  # Optimal for natural pauses (2026: 700-900ms)
                    "create_response": True  # Auto-create response when turn ends
                },
                "tools": self.get_available_tools(),
                "tool_choice": "auto",
                "temperature": 0.95,  # Higher for maximum naturalness (2026 best practice)
                "max_response_output_tokens": 40,  # Very short for natural back-and-forth
                "reasoning_effort": self.get_reasoning_effort(),
                "response_format": {
                    "type": "text"  # Natural text responses
                },
                "turn_detection": None  # Disable automatic turn detection initially to allow greeting
            }
        }
        
        # Note: After sending this config, the consumer should trigger the initial greeting
    
    def get_reasoning_effort(self):
        """Get reasoning effort level (1-5)."""
        # Map reasoning level to effort
        efforts = {
            1: "low",      # Fast, simple responses
            2: "medium",   # Balanced
            3: "medium",   # Default
            4: "high",     # Complex reasoning
            5: "high"      # Maximum reasoning
        }
        return efforts.get(self.reasoning_level, "medium")
    
    def get_available_tools(self):
        """Define tools available to GPT-Realtime-2."""
        return [
            {
                "type": "function",
                "name": "get_available_slots",
                "description": "Get available appointment slots for the patient's assigned doctor",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "specific_date": {
                            "type": "string",
                            "description": "Specific date in YYYY-MM-DD format (optional)"
                        },
                        "days_ahead": {
                            "type": "integer",
                            "description": "Number of days to look ahead (default: 7)"
                        },
                        "time_preference": {
                            "type": "string",
                            "enum": ["morning", "afternoon", "evening", "any"],
                            "description": "Preferred time of day"
                        }
                    }
                }
            },
            {
                "type": "function",
                "name": "book_appointment",
                "description": "Book an appointment for the patient",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "slot_id": {
                            "type": "integer",
                            "description": "ID of the slot to book"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Additional notes about the appointment"
                        }
                    },
                    "required": ["slot_id"]
                }
            },
            {
                "type": "function",
                "name": "cancel_appointment",
                "description": "Cancel an existing appointment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "appointment_id": {
                            "type": "integer",
                            "description": "ID of the appointment to cancel"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for cancellation"
                        }
                    },
                    "required": ["appointment_id"]
                }
            },
            {
                "type": "function",
                "name": "get_patient_appointments",
                "description": "Get patient's upcoming appointments",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    
    def execute_tool(self, tool_name, arguments):
        """Execute a tool call from GPT-Realtime-2."""
        try:
            if tool_name == "get_available_slots":
                return self._get_available_slots(**arguments)
            elif tool_name == "book_appointment":
                return self._book_appointment(**arguments)
            elif tool_name == "cancel_appointment":
                return self._cancel_appointment(**arguments)
            elif tool_name == "get_patient_appointments":
                return self._get_patient_appointments()
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"error": str(e)}
    
    def _get_available_slots(self, specific_date=None, days_ahead=7, time_preference="any"):
        """Get available slots (tool implementation)."""
        from doctors.models import DoctorSlot
        from datetime import datetime, timedelta
        
        try:
            assigned_doctor = self.patient.assigned_doctor
            if not assigned_doctor:
                return {"error": "No assigned doctor", "slots": []}
            
            today = datetime.now().date()
            
            if specific_date:
                from datetime import datetime as dt
                start_date = end_date = dt.fromisoformat(specific_date).date()
            else:
                start_date = today
                end_date = today + timedelta(days=days_ahead)
            
            slots = DoctorSlot.objects.filter(
                doctor=assigned_doctor,
                slot_date__gte=start_date,
                slot_date__lte=end_date,
                status='AVAILABLE'
            ).select_related('doctor').order_by('slot_date', 'start_time')
            
            # Filter by time preference
            if time_preference != "any":
                time_filters = {
                    "morning": (0, 12),
                    "afternoon": (12, 17),
                    "evening": (17, 24)
                }
                start_hour, end_hour = time_filters.get(time_preference, (0, 24))
                slots = slots.filter(
                    start_time__hour__gte=start_hour,
                    start_time__hour__lt=end_hour
                )
            
            slot_list = []
            for slot in slots[:10]:  # Limit to 10 slots
                slot_list.append({
                    'id': slot.id,
                    'doctor_name': slot.doctor.full_name,
                    'date': slot.slot_date.isoformat(),
                    'time': slot.start_time.strftime('%I:%M %p'),
                    'date_formatted': slot.slot_date.strftime('%A, %B %d'),
                    'time_formatted': slot.start_time.strftime('%I:%M %p')
                })
            
            return {
                "success": True,
                "slots": slot_list,
                "count": len(slot_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting slots: {e}")
            return {"error": str(e), "slots": []}
    
    def _book_appointment(self, slot_id, notes=''):
        """Book appointment (tool implementation)."""
        from doctors.models import DoctorSlot
        from scheduling.models import Appointment
        from django.db import transaction
        from django.utils import timezone
        
        try:
            with transaction.atomic():
                slot = DoctorSlot.objects.select_for_update().get(pk=slot_id)
                
                if slot.status != 'AVAILABLE':
                    return {
                        'success': False,
                        'message': "That slot is no longer available"
                    }
                
                # Book slot
                slot.status = 'BOOKED'
                slot.booked_patient = self.patient
                slot.booked_at = timezone.now()
                slot.save()
                
                # Create appointment
                appointment = Appointment.objects.create(
                    slot=slot,
                    patient=self.patient,
                    notes=notes,
                    status='CONFIRMED'
                )
                
                # Send SMS confirmation
                try:
                    from reminders.models import ReminderLog
                    from reminders.tasks import _send_sms
                    
                    msg = (
                        f"Confirmed! Dr. {slot.doctor.full_name.split()[-1]} on "
                        f"{slot.slot_date.strftime('%b %d')} at {slot.start_time.strftime('%I:%M %p')}. "
                        f"See you then!"
                    )
                    
                    reminder = ReminderLog.objects.create(
                        appointment=appointment,
                        patient=self.patient,
                        reminder_type=ReminderLog.ReminderType.BOOKING_CONFIRMATION,
                        channel=ReminderLog.Channel.SMS,
                        message_text=msg
                    )
                    
                    if _send_sms(self.patient.phone_number, msg, reminder):
                        reminder.mark_sent()
                except Exception as e:
                    logger.error(f"SMS error: {e}")
                
                return {
                    'success': True,
                    'message': f"Appointment booked for {slot.slot_date.strftime('%A, %B %d')} at {slot.start_time.strftime('%I:%M %p')}",
                    'appointment_id': appointment.id,
                    'date': slot.slot_date.isoformat(),
                    'time': slot.start_time.strftime('%I:%M %p')
                }
                
        except Exception as e:
            logger.error(f"Booking error: {e}")
            return {
                'success': False,
                'message': "Unable to book appointment. Please try again."
            }
    
    def _cancel_appointment(self, appointment_id, reason='Patient requested'):
        """Cancel appointment (tool implementation)."""
        from scheduling.models import Appointment
        from django.utils import timezone
        
        try:
            appointment = Appointment.objects.get(pk=appointment_id)
            appointment.status = 'CANCELLED'
            appointment.cancelled_at = timezone.now()
            appointment.cancellation_reason = reason
            appointment.save()
            
            slot = appointment.slot
            slot.status = 'AVAILABLE'
            slot.booked_patient = None
            slot.booked_at = None
            slot.save()
            
            return {
                'success': True,
                'message': "Appointment cancelled successfully"
            }
        except Exception as e:
            logger.error(f"Cancel error: {e}")
            return {
                'success': False,
                'message': "Unable to cancel appointment"
            }
    
    def _get_patient_appointments(self):
        """Get patient appointments (tool implementation)."""
        from scheduling.models import Appointment
        
        try:
            appointments = Appointment.objects.filter(
                patient=self.patient,
                status='CONFIRMED'
            ).select_related('slot', 'slot__doctor').order_by('slot__slot_date', 'slot__start_time')[:5]
            
            appt_list = []
            for appt in appointments:
                appt_list.append({
                    'id': appt.id,
                    'doctor': appt.slot.doctor.full_name,
                    'date': appt.slot.slot_date.isoformat(),
                    'time': appt.slot.start_time.strftime('%I:%M %p'),
                    'date_formatted': appt.slot.slot_date.strftime('%A, %B %d'),
                    'time_formatted': appt.slot.start_time.strftime('%I:%M %p')
                })
            
            return {
                'success': True,
                'appointments': appt_list,
                'count': len(appt_list)
            }
        except Exception as e:
            logger.error(f"Error getting appointments: {e}")
            return {
                'success': False,
                'appointments': [],
                'error': str(e)
            }
    
    def use_gpt_5_5_reasoning(self, complex_query):
        """
        Use GPT-5.5 for complex medical reasoning.
        This is used for difficult decisions that require deep thinking.
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-5.5",  # Latest GPT-5.5 model (April 2026)
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical AI assistant helping with complex healthcare decisions. Provide clear, accurate, professional guidance."
                    },
                    {
                        "role": "user",
                        "content": complex_query
                    }
                ],
                max_completion_tokens=200,  # GPT-5.5 uses max_completion_tokens
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"GPT-5.5 error: {e}")
            return "I'm having trouble processing that complex request. Let me connect you with our staff."


# TwiML Generation for Realtime API
def generate_realtime_twiml(patient, appointment=None, call_type='GENERAL', call_log_id=None):
    """
    Generate TwiML for GPT-Realtime-2 streaming.
    Uses WebSocket streaming for bidirectional audio.
    """
    response = VoiceResponse()
    
    # Connect to GPT-Realtime-2 via WebSocket FIRST (before any Say)
    connect = Connect()
    
    # CRITICAL: Set very long timeout to prevent automatic disconnection
    # This allows calls to last as long as needed for natural conversations
    connect.timeout = 7200  # 2 hours timeout (was 1 hour, now doubled)
    
    # Build WebSocket URL
    ws_url = f'wss://{settings.SITE_URL.replace("https://", "").replace("http://", "")}/ws/realtime-ai/?patient_id={patient.id}&call_log_id={call_log_id}'
    
    stream = connect.stream(
        url=ws_url,
        track='both_tracks'  # Send and receive audio
    )
    
    # Add custom parameters
    stream.parameter(name='patient_id', value=str(patient.id))
    stream.parameter(name='call_log_id', value=str(call_log_id))
    stream.parameter(name='call_type', value=call_type)
    
    # Get patient name for greeting
    first_name = patient.full_name.split()[0]
    stream.parameter(name='patient_name', value=first_name)
    
    # Add appointment info if available
    if appointment:
        stream.parameter(name='appointment_date', value=str(appointment.slot.slot_date))
        stream.parameter(name='appointment_time', value=str(appointment.slot.start_time))
    
    response.append(connect)
    
    logger.info(f"Generated TwiML with WebSocket URL: {ws_url}")
    
    return str(response)


def create_realtime_session_config(patient, appointment=None, call_type='GENERAL'):
    """
    Create configuration for GPT-Realtime-2 session.
    """
    ai = RealtimeConversationalAI(patient, appointment, call_type)
    return ai.get_system_instructions()
