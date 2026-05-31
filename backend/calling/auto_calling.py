"""
Automatic AI Calling System
Automatically calls patients based on appointment schedules
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_appointment_reminders():
    """
    Automatically call patients with appointments in the next 24 hours.
    Runs every hour via Celery Beat.
    """
    from scheduling.models import Appointment
    from .models import CallLog
    from .tasks import call_patient
    
    # Get appointments in next 24 hours that are confirmed
    now = timezone.now()
    tomorrow = now + timedelta(hours=24)
    
    appointments = Appointment.objects.filter(
        status=Appointment.Status.CONFIRMED,
        slot__slot_date__gte=now.date(),
        slot__slot_date__lte=tomorrow.date()
    ).select_related('patient', 'slot', 'slot__doctor')
    
    logger.info(f"Found {appointments.count()} appointments in next 24 hours")
    
    for appointment in appointments:
        # Check if we already called for this appointment
        existing_calls = CallLog.objects.filter(
            patient=appointment.patient,
            appointment=appointment,
            call_type=CallLog.CallType.APPOINTMENT_REMINDER
        ).count()
        
        if existing_calls == 0:
            # No reminder sent yet, initiate call
            logger.info(f"Initiating reminder call for appointment {appointment.id}")
            
            try:
                call_patient.delay(
                    patient_id=appointment.patient.id,
                    appointment_id=appointment.id,
                    call_type=CallLog.CallType.APPOINTMENT_REMINDER,
                    attempt=1
                )
                logger.info(f"Reminder call queued for patient {appointment.patient.full_name}")
            except Exception as e:
                logger.error(f"Failed to queue reminder call: {e}")
        else:
            logger.debug(f"Reminder already sent for appointment {appointment.id}")
    
    return {
        'appointments_checked': appointments.count(),
        'timestamp': now.isoformat()
    }


@shared_task
def send_appointment_confirmations():
    """
    Automatically call patients with appointments in 2-7 days for confirmation.
    Runs daily via Celery Beat.
    """
    from scheduling.models import Appointment
    from .models import CallLog
    from .tasks import call_patient
    
    # Get appointments 2-7 days out
    now = timezone.now()
    start_date = (now + timedelta(days=2)).date()
    end_date = (now + timedelta(days=7)).date()
    
    appointments = Appointment.objects.filter(
        status=Appointment.Status.CONFIRMED,
        slot__slot_date__gte=start_date,
        slot__slot_date__lte=end_date
    ).select_related('patient', 'slot', 'slot__doctor')
    
    logger.info(f"Found {appointments.count()} appointments for confirmation (2-7 days out)")
    
    for appointment in appointments:
        # Check if we already sent confirmation call
        existing_calls = CallLog.objects.filter(
            patient=appointment.patient,
            appointment=appointment,
            call_type=CallLog.CallType.APPOINTMENT_REMINDER
        ).count()
        
        if existing_calls == 0:
            logger.info(f"Initiating confirmation call for appointment {appointment.id}")
            
            try:
                call_patient.delay(
                    patient_id=appointment.patient.id,
                    appointment_id=appointment.id,
                    call_type=CallLog.CallType.APPOINTMENT_REMINDER,
                    attempt=1
                )
                logger.info(f"Confirmation call queued for patient {appointment.patient.full_name}")
            except Exception as e:
                logger.error(f"Failed to queue confirmation call: {e}")
    
    return {
        'appointments_checked': appointments.count(),
        'timestamp': now.isoformat()
    }


@shared_task
def send_follow_up_calls():
    """
    Automatically call patients 1 day after completed appointments.
    Runs daily via Celery Beat.
    """
    from scheduling.models import Appointment
    from .models import CallLog
    from .tasks import call_patient
    
    # Get appointments completed yesterday
    yesterday = (timezone.now() - timedelta(days=1)).date()
    
    appointments = Appointment.objects.filter(
        status=Appointment.Status.COMPLETED,
        slot__slot_date=yesterday
    ).select_related('patient', 'slot', 'slot__doctor')
    
    logger.info(f"Found {appointments.count()} completed appointments for follow-up")
    
    for appointment in appointments:
        # Check if we already sent follow-up call
        existing_calls = CallLog.objects.filter(
            patient=appointment.patient,
            appointment=appointment,
            call_type=CallLog.CallType.FOLLOW_UP
        ).count()
        
        if existing_calls == 0:
            logger.info(f"Initiating follow-up call for appointment {appointment.id}")
            
            try:
                call_patient.delay(
                    patient_id=appointment.patient.id,
                    appointment_id=appointment.id,
                    call_type=CallLog.CallType.FOLLOW_UP,
                    attempt=1
                )
                logger.info(f"Follow-up call queued for patient {appointment.patient.full_name}")
            except Exception as e:
                logger.error(f"Failed to queue follow-up call: {e}")
    
    return {
        'appointments_checked': appointments.count(),
        'timestamp': timezone.now().isoformat()
    }


@shared_task
def offer_slots_to_waitlist():
    """
    Automatically call patients on waitlist when slots become available.
    Runs every 30 minutes via Celery Beat.
    """
    from doctors.models import DoctorSlot
    from patients.models import Patient
    from .models import CallLog
    from .tasks import call_patient
    
    # Get available slots in next 7 days
    now = timezone.now()
    end_date = (now + timedelta(days=7)).date()
    
    available_slots = DoctorSlot.objects.filter(
        status='AVAILABLE',
        slot_date__gte=now.date(),
        slot_date__lte=end_date
    ).select_related('doctor').order_by('slot_date', 'start_time')[:10]
    
    if not available_slots:
        logger.info("No available slots to offer")
        return {'slots_offered': 0}
    
    # Get patients who haven't been called recently
    recent_cutoff = now - timedelta(days=7)
    
    # Get patients without upcoming appointments
    from scheduling.models import Appointment
    patients_with_appointments = Appointment.objects.filter(
        status=Appointment.Status.CONFIRMED,
        slot__slot_date__gte=now.date()
    ).values_list('patient_id', flat=True)
    
    patients = Patient.objects.exclude(
        id__in=patients_with_appointments
    ).exclude(
        call_logs__call_type=CallLog.CallType.SLOT_OFFER,
        call_logs__initiated_at__gte=recent_cutoff
    )[:5]  # Limit to 5 patients per run
    
    calls_initiated = 0
    
    for patient in patients:
        logger.info(f"Offering slots to patient {patient.full_name}")
        
        try:
            call_patient.delay(
                patient_id=patient.id,
                appointment_id=None,
                call_type=CallLog.CallType.SLOT_OFFER,
                attempt=1
            )
            calls_initiated += 1
            logger.info(f"Slot offer call queued for patient {patient.full_name}")
        except Exception as e:
            logger.error(f"Failed to queue slot offer call: {e}")
    
    return {
        'available_slots': available_slots.count(),
        'calls_initiated': calls_initiated,
        'timestamp': now.isoformat()
    }


@shared_task
def cleanup_old_call_logs():
    """
    Archive or delete old call logs (older than 90 days).
    Runs weekly via Celery Beat.
    """
    from .models import CallLog
    
    cutoff_date = timezone.now() - timedelta(days=90)
    
    old_logs = CallLog.objects.filter(
        initiated_at__lt=cutoff_date
    )
    
    count = old_logs.count()
    logger.info(f"Found {count} call logs older than 90 days")
    
    # For now, just log. In production, you might archive to S3 or delete
    # old_logs.delete()
    
    return {
        'old_logs_found': count,
        'action': 'logged_only',
        'timestamp': timezone.now().isoformat()
    }

