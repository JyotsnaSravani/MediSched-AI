"""
Celery tasks for automated reminder system.
Sprint 4 - Implements FR-RM-01 through FR-RM-04
"""

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def check_upcoming_reminders():
    """
    Celery Beat task - Check for appointments in next 24 hours and 1 hour and send reminders.
    Implements FR-RM-01 (24-hour and 1-hour reminder window).
    Runs every 15 minutes via Celery Beat.
    """
    from scheduling.models import Appointment
    from .models import ReminderLog
    
    now = timezone.now()
    
    # Check for 24-hour reminders
    reminder_24h_start = now + timedelta(hours=23)
    reminder_24h_end = now + timedelta(hours=25)
    
    appointments_24h = Appointment.objects.filter(
        status=Appointment.Status.CONFIRMED,
        slot__slot_date__gte=reminder_24h_start.date(),
        slot__slot_date__lte=reminder_24h_end.date()
    ).select_related('patient', 'slot', 'slot__doctor')
    
    reminders_24h_sent = 0
    
    for appointment in appointments_24h:
        # Check if 24-hour reminder already sent
        existing_reminder = ReminderLog.objects.filter(
            appointment=appointment,
            reminder_type=ReminderLog.ReminderType.REMINDER_24H
        ).exists()
        
        if not existing_reminder:
            # Send 24-hour reminder
            send_24h_reminder.delay(appointment.id)
            reminders_24h_sent += 1
    
    # Check for 1-hour reminders
    reminder_1h_start = now + timedelta(minutes=50)
    reminder_1h_end = now + timedelta(minutes=70)
    
    appointments_1h = Appointment.objects.filter(
        status=Appointment.Status.CONFIRMED,
        slot__slot_date=now.date()
    ).select_related('patient', 'slot', 'slot__doctor')
    
    reminders_1h_sent = 0
    
    for appointment in appointments_1h:
        # Calculate appointment datetime
        from datetime import datetime, time
        appointment_datetime = datetime.combine(
            appointment.slot.slot_date,
            appointment.slot.start_time
        )
        appointment_datetime = timezone.make_aware(appointment_datetime)
        
        # Check if appointment is in 1-hour window
        if reminder_1h_start <= appointment_datetime <= reminder_1h_end:
            # Check if 1-hour reminder already sent
            existing_reminder = ReminderLog.objects.filter(
                appointment=appointment,
                reminder_type=ReminderLog.ReminderType.REMINDER_1H
            ).exists()
            
            if not existing_reminder:
                # Send 1-hour reminder
                send_1h_reminder.delay(appointment.id)
                reminders_1h_sent += 1
    
    logger.info(f"Checked upcoming appointments: {reminders_24h_sent} 24h reminders, {reminders_1h_sent} 1h reminders queued")
    
    return {
        'status': 'success',
        'reminders_24h_queued': reminders_24h_sent,
        'reminders_1h_queued': reminders_1h_sent,
        'checked_at': now.isoformat()
    }


@shared_task(bind=True, max_retries=1, acks_late=True)
def send_24h_reminder(self, appointment_id):
    """
    Send 24-hour reminder to patient.
    Implements FR-RM-02 (multi-channel delivery) and FR-RM-03 (retry logic).
    
    Args:
        appointment_id: Appointment ID to send reminder for
    """
    from scheduling.models import Appointment
    from .models import ReminderLog
    
    try:
        appointment = Appointment.objects.select_related(
            'patient', 'slot', 'slot__doctor'
        ).get(id=appointment_id)
        
        patient = appointment.patient
        slot = appointment.slot
        doctor = slot.doctor
        
        # Create message text
        message_text = (
            f"Reminder: You have an appointment with Dr. {doctor.full_name} "
            f"tomorrow at {slot.start_time.strftime('%I:%M %p')}. "
            f"Please arrive 10 minutes early. "
            f"To cancel or reschedule, call us at [CLINIC_PHONE]."
        )
        
        # Create reminder log
        reminder = ReminderLog.objects.create(
            appointment=appointment,
            patient=patient,
            reminder_type=ReminderLog.ReminderType.REMINDER_24H,
            channel=ReminderLog.Channel.SMS,  # Default to SMS
            message_text=message_text
        )
        
        # Send SMS
        sms_success = _send_sms(patient.phone_number, message_text, reminder)
        
        # Send Email (if email available)
        email_success = False
        if patient.email:
            email_success = _send_email(
                patient.email,
                f"Appointment Reminder - {slot.slot_date}",
                message_text,
                reminder
            )
        
        # Update reminder status
        if sms_success or email_success:
            reminder.mark_sent()
            logger.info(f"24h reminder sent for appointment {appointment_id}")
            return {
                'status': 'success',
                'reminder_id': reminder.id,
                'sms_sent': sms_success,
                'email_sent': email_success
            }
        else:
            raise Exception("Failed to send reminder via any channel")
        
    except Appointment.DoesNotExist:
        logger.error(f"Appointment {appointment_id} not found")
        return {'status': 'error', 'message': 'Appointment not found'}
    
    except Exception as e:
        logger.error(f"Error sending 24h reminder: {str(e)}")
        
        # Retry logic (FR-RM-03: 1 retry after 15 minutes)
        if self.request.retries < self.max_retries:
            try:
                reminder.increment_retry()
            except Exception as retry_err:
                logger.error(f"Failed to increment retry: {retry_err}")
                pass
            raise self.retry(exc=e, countdown=900)  # 15 minutes
        else:
            # Mark as failed after retry
            try:
                reminder.mark_failed(str(e))
            except Exception as mark_err:
                logger.error(f"Failed to mark as failed: {mark_err}")
                pass
            return {'status': 'error', 'message': str(e)}


@shared_task(bind=True, max_retries=1, acks_late=True)
def send_1h_reminder(self, appointment_id):
    """
    Send 1-hour reminder to patient.
    Implements FR-RM-02 (multi-channel delivery) and FR-RM-03 (retry logic).
    
    Args:
        appointment_id: Appointment ID to send reminder for
    """
    from scheduling.models import Appointment
    from .models import ReminderLog
    
    try:
        appointment = Appointment.objects.select_related(
            'patient', 'slot', 'slot__doctor'
        ).get(id=appointment_id)
        
        patient = appointment.patient
        slot = appointment.slot
        doctor = slot.doctor
        
        # Create message text
        message_text = (
            f"Reminder: Your appointment with Dr. {doctor.full_name} "
            f"is in 1 hour at {slot.start_time.strftime('%I:%M %p')}. "
            f"Please arrive 10 minutes early. See you soon!"
        )
        
        # Create reminder log
        reminder = ReminderLog.objects.create(
            appointment=appointment,
            patient=patient,
            reminder_type=ReminderLog.ReminderType.REMINDER_1H,
            channel=ReminderLog.Channel.SMS,  # Default to SMS
            message_text=message_text
        )
        
        # Send SMS
        sms_success = _send_sms(patient.phone_number, message_text, reminder)
        
        # Send Email (if email available)
        email_success = False
        if patient.email:
            email_success = _send_email(
                patient.email,
                f"Appointment in 1 Hour - {slot.slot_date}",
                message_text,
                reminder
            )
        
        # Update reminder status
        if sms_success or email_success:
            reminder.mark_sent()
            logger.info(f"1h reminder sent for appointment {appointment_id}")
            return {
                'status': 'success',
                'reminder_id': reminder.id,
                'sms_sent': sms_success,
                'email_sent': email_success
            }
        else:
            raise Exception("Failed to send reminder via any channel")
        
    except Appointment.DoesNotExist:
        logger.error(f"Appointment {appointment_id} not found")
        return {'status': 'error', 'message': 'Appointment not found'}
    
    except Exception as e:
        logger.error(f"Error sending 1h reminder: {str(e)}")
        
        # Retry logic (FR-RM-03: 1 retry after 5 minutes for 1h reminder)
        if self.request.retries < self.max_retries:
            try:
                reminder.increment_retry()
            except Exception as retry_err:
                logger.error(f"Failed to increment retry: {retry_err}")
                pass
            raise self.retry(exc=e, countdown=300)  # 5 minutes
        else:
            # Mark as failed after retry
            try:
                reminder.mark_failed(str(e))
            except Exception as mark_err:
                logger.error(f"Failed to mark as failed: {mark_err}")
                pass
            return {'status': 'error', 'message': str(e)}


@shared_task
def send_booking_confirmation(appointment_id):
    """
    Send booking confirmation immediately after appointment is booked.
    Implements FR-RM-04 (immediate confirmation).
    
    Args:
        appointment_id: Appointment ID to send confirmation for
    """
    from scheduling.models import Appointment
    from .models import ReminderLog
    
    try:
        appointment = Appointment.objects.select_related(
            'patient', 'slot', 'slot__doctor'
        ).get(id=appointment_id)
        
        patient = appointment.patient
        slot = appointment.slot
        doctor = slot.doctor
        
        # Create message text
        message_text = (
            f"Appointment Confirmed! "
            f"Dr. {doctor.full_name} on {slot.slot_date.strftime('%B %d, %Y')} "
            f"at {slot.start_time.strftime('%I:%M %p')}. "
            f"We look forward to seeing you!"
        )
        
        # Create reminder log
        reminder = ReminderLog.objects.create(
            appointment=appointment,
            patient=patient,
            reminder_type=ReminderLog.ReminderType.BOOKING_CONFIRMATION,
            channel=ReminderLog.Channel.SMS,
            message_text=message_text
        )
        
        # Send SMS
        sms_success = _send_sms(patient.phone_number, message_text, reminder)
        
        # Send Email
        email_success = False
        if patient.email:
            email_success = _send_email(
                patient.email,
                "Appointment Confirmation",
                message_text,
                reminder
            )
        
        if sms_success or email_success:
            reminder.mark_sent()
            logger.info(f"Booking confirmation sent for appointment {appointment_id}")
        
        return {
            'status': 'success',
            'reminder_id': reminder.id,
            'sms_sent': sms_success,
            'email_sent': email_success
        }
        
    except Exception as e:
        logger.error(f"Error sending booking confirmation: {str(e)}")
        return {'status': 'error', 'message': str(e)}


def _send_sms(phone_number, message, reminder):
    """
    Send SMS via Twilio.
    Returns True if successful, False otherwise.
    """
    # Check if Twilio is configured
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("Twilio not configured - simulating SMS")
        reminder.twilio_message_sid = f"SIMULATED_SMS_{reminder.id}"
        reminder.save()
        return True
    
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        message_obj = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        
        reminder.twilio_message_sid = message_obj.sid
        reminder.save()
        
        logger.info(f"SMS sent: {message_obj.sid}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")
        return False


def _send_email(email, subject, message, reminder):
    """
    Send email via Django email backend.
    Returns True if successful, False otherwise.
    """
    from django.core.mail import send_mail
    
    try:
        # Check if email is configured
        if not settings.EMAIL_HOST_USER:
            logger.warning("Email not configured - simulating email")
            reminder.email_message_id = f"SIMULATED_EMAIL_{reminder.id}"
            reminder.save()
            return True
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
        
        reminder.email_message_id = f"EMAIL_{reminder.id}"
        reminder.save()
        
        logger.info(f"Email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False
