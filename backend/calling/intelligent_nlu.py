"""
Intelligent Natural Language Understanding for Healthcare AI
Handles intent detection, entity extraction, and context management
"""

import re
from datetime import datetime, timedelta
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class ConversationContext:
    """Manages conversation context and memory"""
    
    def __init__(self):
        self.patient_name = None
        self.mentioned_date = None
        self.mentioned_time = None
        self.mentioned_doctor = None
        self.last_intent = None
        self.last_appointment = None
        self.conversation_history = []
    
    def add_message(self, speaker, text):
        """Add message to conversation history"""
        self.conversation_history.append({
            'speaker': speaker,
            'text': text,
            'timestamp': datetime.now()
        })
    
    def get_recent_context(self, n=3):
        """Get last n messages for context"""
        return self.conversation_history[-n:]


class IntentDetector:
    """Detects patient intent from natural language"""
    
    # Intent patterns with keywords
    INTENT_PATTERNS = {
        'check_appointment': [
            r'\b(do i have|check|what|when|my appointment|existing|already booked|booking)\b',
            r'\b(appointment.*tomorrow|appointment.*today|appointment.*next)\b',
            r'\b(confirm|confirmed|scheduled)\b'
        ],
        'book_appointment': [
            r'\b(book|schedule|make|need|want).*\b(appointment|booking|slot)\b',
            r'\b(appointment|booking).*\b(book|schedule|make)\b',
            r'\b(can i|i want to|i need to).*\b(book|schedule)\b'
        ],
        'cancel_appointment': [
            r'\b(cancel|delete|remove).*\b(appointment|booking)\b',
            r'\b(don\'t want|no longer need).*\b(appointment)\b',
            r'\b(cancel|cancellation)\b'
        ],
        'reschedule_appointment': [
            r'\b(change|reschedule|move|shift).*\b(appointment|booking|timing|time)\b',
            r'\b(different time|another time|new time)\b',
            r'\b(can i change|want to change)\b'
        ],
        'doctor_availability': [
            r'\b(doctor|dr).*\b(available|free|timing|schedule)\b',
            r'\b(which doctor|any doctor|specific doctor)\b',
            r'\b(same doctor|previous doctor|last doctor)\b'
        ],
        'slot_availability': [
            r'\b(any slot|slot available|available|free slot|opening)\b',
            r'\b(slots.*today|slots.*tomorrow|slots.*available)\b',
            r'\b(do you have|is there).*\b(slot|time|appointment)\b'
        ],
        'hospital_timings': [
            r'\b(hospital|clinic|office).*\b(timing|hours|open|close)\b',
            r'\b(what time|when).*\b(open|close)\b',
            r'\b(working hours|business hours)\b'
        ],
        'waiting_time': [
            r'\b(how long|waiting|wait time|how much time)\b',
            r'\b(queue|line|delay)\b'
        ],
        'scan_test_booking': [
            r'\b(scan|test|lab|x-ray|mri|ct scan|blood test)\b',
            r'\b(diagnostic|pathology|radiology)\b'
        ],
        'department_info': [
            r'\b(department|cardiology|neurology|orthopedic|pediatric)\b',
            r'\b(specialist|specialization)\b'
        ],
        'location_info': [
            r'\b(where|location|address|directions|how to reach)\b',
            r'\b(parking|entrance)\b'
        ],
        'cost_insurance': [
            r'\b(cost|price|fee|charge|payment)\b',
            r'\b(insurance|coverage|claim)\b'
        ],
        'general_inquiry': [
            r'\b(what|how|when|where|who|which)\b',
            r'\b(information|details|tell me)\b'
        ]
    }
    
    def detect_intent(self, text, context=None):
        """
        Detect intent from patient's text
        Returns: (intent, confidence, entities)
        """
        text_lower = text.lower()
        
        # Check each intent pattern
        intent_scores = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    score += 1
            if score > 0:
                intent_scores[intent] = score
        
        # Get highest scoring intent
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = intent_scores[best_intent] / len(self.INTENT_PATTERNS[best_intent])
            
            # Extract entities
            entities = self.extract_entities(text, context)
            
            return best_intent, confidence, entities
        
        # Default to general inquiry
        return 'general_inquiry', 0.5, {}
    
    def extract_entities(self, text, context=None):
        """Extract entities like date, time, doctor name, etc."""
        entities = {}
        text_lower = text.lower()
        
        # Extract date
        date_entity = self._extract_date(text_lower)
        if date_entity:
            entities['date'] = date_entity
        
        # Extract time
        time_entity = self._extract_time(text_lower)
        if time_entity:
            entities['time'] = time_entity
        
        # Extract doctor reference
        if re.search(r'\b(same doctor|previous doctor|last doctor|dr\.|doctor)\b', text_lower):
            entities['doctor_reference'] = 'previous'
        
        # Extract confirmation/negation
        if re.search(r'\b(yes|yeah|sure|okay|ok|correct|right)\b', text_lower):
            entities['confirmation'] = True
        elif re.search(r'\b(no|nope|not|don\'t|cancel)\b', text_lower):
            entities['confirmation'] = False
        
        return entities
    
    def _extract_date(self, text):
        """Extract date from text"""
        today = timezone.now().date()
        
        # Relative dates
        if 'today' in text:
            return today
        elif 'tomorrow' in text:
            return today + timedelta(days=1)
        elif 'day after tomorrow' in text:
            return today + timedelta(days=2)
        elif 'yesterday' in text:
            return today - timedelta(days=1)
        
        # Day names
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day in enumerate(day_names):
            if day in text:
                current_weekday = today.weekday()
                days_ahead = i - current_weekday
                if days_ahead <= 0:
                    days_ahead += 7
                return today + timedelta(days=days_ahead)
        
        # Specific dates (e.g., "21 May", "May 21")
        date_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([a-z]+)', text)
        if date_match:
            try:
                day = int(date_match.group(1))
                month_str = date_match.group(2)
                month_map = {
                    'jan': 1, 'january': 1, 'feb': 2, 'february': 2,
                    'mar': 3, 'march': 3, 'apr': 4, 'april': 4,
                    'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
                    'aug': 8, 'august': 8, 'sep': 9, 'september': 9,
                    'oct': 10, 'october': 10, 'nov': 11, 'november': 11,
                    'dec': 12, 'december': 12
                }
                month = month_map.get(month_str, today.month)
                year = today.year
                from datetime import date
                return date(year, month, day)
            except:
                pass
        
        return None
    
    def _extract_time(self, text):
        """Extract time from text"""
        # Specific times (e.g., "10 AM", "2:30 PM")
        time_match = re.search(r'(\d{1,2})[:.]?(\d{2})?\s*(am|pm|a\.m\.|p\.m\.)?', text)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            am_pm = time_match.group(3) if time_match.group(3) else ''
            
            if 'pm' in am_pm.lower() and hour < 12:
                hour += 12
            elif hour < 8 and not am_pm:  # Assume PM for early hours without AM/PM
                hour += 12
            
            return {'hour': hour, 'minute': minute}
        
        # General time periods
        if 'morning' in text:
            return {'period': 'morning'}
        elif 'afternoon' in text:
            return {'period': 'afternoon'}
        elif 'evening' in text:
            return {'period': 'evening'}
        
        return None


class ResponseGenerator:
    """Generates natural, conversational responses"""
    
    @staticmethod
    def generate_response(intent, entities, data, context):
        """Generate natural response based on intent and data"""
        
        if intent == 'check_appointment':
            return ResponseGenerator._check_appointment_response(data, context)
        elif intent == 'book_appointment':
            return ResponseGenerator._book_appointment_response(entities, data, context)
        elif intent == 'cancel_appointment':
            return ResponseGenerator._cancel_appointment_response(data, context)
        elif intent == 'reschedule_appointment':
            return ResponseGenerator._reschedule_appointment_response(entities, data, context)
        elif intent == 'slot_availability':
            return ResponseGenerator._slot_availability_response(entities, data, context)
        elif intent == 'hospital_timings':
            return "We're open Monday through Friday, 9 AM to 5 PM. Is there anything else I can help you with?"
        elif intent == 'waiting_time':
            return "Usually around 15 to 20 minutes depending on appointments. Would you like to book a slot?"
        else:
            return "I'd be happy to help! Could you tell me a bit more about what you need?"
    
    @staticmethod
    def _check_appointment_response(appointments, context):
        """Generate response for checking appointments"""
        if not appointments:
            return "I don't see any upcoming appointments for you. Would you like to book one?"
        
        if len(appointments) == 1:
            appt = appointments[0]
            date_str = appt.slot.slot_date.strftime('%A, %B %d')
            time_str = appt.slot.start_time.strftime('%I:%M %p')
            doctor_name = appt.slot.doctor.full_name.split()[-1]
            return f"Yes, you have an appointment with Dr. {doctor_name} on {date_str} at {time_str}. Is there anything else you need?"
        else:
            response = f"You have {len(appointments)} upcoming appointments. "
            for appt in appointments[:2]:  # Show first 2
                date_str = appt.slot.slot_date.strftime('%B %d')
                time_str = appt.slot.start_time.strftime('%I:%M %p')
                doctor_name = appt.slot.doctor.full_name.split()[-1]
                response += f"One with Dr. {doctor_name} on {date_str} at {time_str}. "
            return response + "Would you like more details?"
    
    @staticmethod
    def _book_appointment_response(entities, slots, context):
        """Generate response for booking"""
        if 'date' in entities and 'time' in entities:
            return "Perfect! Let me book that for you..."
        elif 'date' in entities:
            return "Great! What time would work best for you?"
        elif 'time' in entities:
            return "Perfect! What date would work best for you?"
        else:
            return "I'd be happy to help you book an appointment! What date and time work for you?"
    
    @staticmethod
    def _cancel_appointment_response(appointments, context):
        """Generate response for cancellation"""
        if not appointments:
            return "I don't see any upcoming appointments to cancel. Is there anything else I can help with?"
        
        if len(appointments) == 1:
            return "I can cancel your appointment. Just to confirm, would you like to cancel your appointment on {date}?"
        else:
            return "You have multiple appointments. Which one would you like to cancel?"
    
    @staticmethod
    def _reschedule_appointment_response(entities, slots, context):
        """Generate response for rescheduling"""
        if 'date' in entities or 'time' in entities:
            return "Sure! Let me find available slots for you..."
        else:
            return "I can help you reschedule. Would you prefer morning or afternoon?"
    
    @staticmethod
    def _slot_availability_response(entities, slots, context):
        """Generate response for slot availability"""
        if not slots:
            return "I'm sorry, we're fully booked for that time. Would you like to try a different date or time?"
        
        if len(slots) == 1:
            slot = slots[0]
            date_str = slot.slot_date.strftime('%A, %B %d')
            time_str = slot.start_time.strftime('%I:%M %p')
            return f"Yes, we have availability on {date_str} at {time_str}. Would you like me to book that for you?"
        else:
            response = f"Yes, we have {len(slots)} slots available. "
            for slot in slots[:3]:
                time_str = slot.start_time.strftime('%I:%M %p')
                response += f"{time_str}, "
            return response.rstrip(', ') + ". Which time works best for you?"
