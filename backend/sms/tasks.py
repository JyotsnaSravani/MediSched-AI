"""Celery tasks for SMS messaging"""

from celery import shared_task
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_sms(patient_id, message_body, message_type='GENERAL', appointment_id=None):
    """
    Send SMS message to patient via Twilio
    """
    from patients.models import Patient
    from scheduling.models import Appointment
    from .models import SMSLog
    
    try:
        patient = Patient.objects.get(id=patient_id)
        appointment = None
        if appointment_id:
            appointment = Appointment.objects.get(id=appointment_id)
        
        # Create SMS log
        sms_log = SMSLog.objects.create(
            patient=patient,
            appointment=appointment,
            message_type=message_type,
            message_body=message_body,
            status=SMSLog.Status.QUEUED
        )
        
        # Check if Twilio is configured
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            logger.warning("Twilio not configured - SMS simulated")
            sms_log.status = SMSLog.Status.FAILED
            sms_log.error_message = "Twilio not configured"
            sms_log.save()
            return {'status': 'error', 'message': 'Twilio not configured'}
        
        # Send SMS via Twilio
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        message = client.messages.create(
            body=message_body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=patient.phone_number
        )
        
        # Update SMS log
        sms_log.twilio_sid = message.sid
        sms_log.status = SMSLog.Status.SENT
        sms_log.save()
        
        logger.info(f"SMS sent to {patient.full_name}: {message.sid}")
        
        return {
            'status': 'success',
            'sms_log_id': sms_log.id,
            'twilio_sid': message.sid
        }
        
    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")
        if 'sms_log' in locals():
            sms_log.status = SMSLog.Status.FAILED
            sms_log.error_message = str(e)
            sms_log.save()
        return {'status': 'error', 'message': str(e)}
