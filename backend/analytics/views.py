"""
Views for analytics app.
Sprint 4 - Implements FR-AN-01 through FR-AN-04
"""

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import StreamingHttpResponse
from django.db.models import Count, Q, Avg, F
from django.utils import timezone
from datetime import timedelta
import csv
import io

from users.permissions import IsAdminOrStaff
from scheduling.models import Appointment
from doctors.models import DoctorSlot
from calling.models import CallLog
from reminders.models import ReminderLog

import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def dashboard_stats(request):
    """
    Get dashboard statistics.
    Implements FR-AN-01 (utilization, call success, no-shows, per-doctor stats).
    
    GET /api/v1/analytics/dashboard/
    """
    # Date range filters
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    # Default to last 30 days
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    if not end_date:
        end_date = timezone.now().date()
    
    # Appointment statistics
    appointments = Appointment.objects.filter(
        slot__slot_date__gte=start_date,
        slot__slot_date__lte=end_date
    )
    
    appointment_stats = appointments.aggregate(
        total=Count('id'),
        confirmed=Count('id', filter=Q(status=Appointment.Status.CONFIRMED)),
        completed=Count('id', filter=Q(status=Appointment.Status.COMPLETED)),
        cancelled=Count('id', filter=Q(status=Appointment.Status.CANCELLED)),
        no_shows=Count('id', filter=Q(status=Appointment.Status.NO_SHOW))
    )
    
    # Calculate no-show rate
    total_appointments = appointment_stats['total']
    no_show_rate = 0
    if total_appointments > 0:
        no_show_rate = (appointment_stats['no_shows'] / total_appointments) * 100
    
    # Slot utilization
    slots = DoctorSlot.objects.filter(
        slot_date__gte=start_date,
        slot_date__lte=end_date
    )
    
    slot_stats = slots.aggregate(
        total=Count('id'),
        booked=Count('id', filter=Q(status='BOOKED')),
        available=Count('id', filter=Q(status='AVAILABLE')),
        blocked=Count('id', filter=Q(status='BLOCKED'))
    )
    
    # Calculate utilization rate
    total_slots = slot_stats['total']
    utilization_rate = 0
    if total_slots > 0:
        utilization_rate = (slot_stats['booked'] / total_slots) * 100
    
    # Call statistics
    calls = CallLog.objects.filter(
        initiated_at__gte=start_date,
        initiated_at__lte=end_date
    )
    
    call_stats = calls.aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(outcome=CallLog.Outcome.COMPLETED)),
        answered=Count('id', filter=Q(outcome=CallLog.Outcome.ANSWERED)),
        no_answer=Count('id', filter=Q(outcome=CallLog.Outcome.NO_ANSWER)),
        failed=Count('id', filter=Q(outcome=CallLog.Outcome.FAILED))
    )
    
    # Calculate call success rate
    total_calls = call_stats['total']
    call_success_rate = 0
    if total_calls > 0:
        successful_calls = call_stats['completed'] + call_stats['answered']
        call_success_rate = (successful_calls / total_calls) * 100
    
    # Reminder statistics
    reminders = ReminderLog.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    reminder_stats = reminders.aggregate(
        total=Count('id'),
        sent=Count('id', filter=Q(delivery_status=ReminderLog.DeliveryStatus.SENT)),
        delivered=Count('id', filter=Q(delivery_status=ReminderLog.DeliveryStatus.DELIVERED)),
        failed=Count('id', filter=Q(delivery_status=ReminderLog.DeliveryStatus.FAILED))
    )
    
    # Per-doctor statistics
    from doctors.models import Doctor
    doctors = Doctor.objects.filter(status='ACTIVE')
    
    doctor_stats = []
    for doctor in doctors:
        doctor_appointments = appointments.filter(slot__doctor=doctor)
        doctor_slots = slots.filter(doctor=doctor)
        
        doc_stats = {
            'doctor_id': doctor.id,
            'doctor_name': doctor.full_name,
            'total_slots': doctor_slots.count(),
            'booked_slots': doctor_slots.filter(status='BOOKED').count(),
            'total_appointments': doctor_appointments.count(),
            'completed_appointments': doctor_appointments.filter(status=Appointment.Status.COMPLETED).count(),
            'no_shows': doctor_appointments.filter(status=Appointment.Status.NO_SHOW).count(),
        }
        
        # Calculate doctor utilization
        if doc_stats['total_slots'] > 0:
            doc_stats['utilization_rate'] = (doc_stats['booked_slots'] / doc_stats['total_slots']) * 100
        else:
            doc_stats['utilization_rate'] = 0
        
        doctor_stats.append(doc_stats)
    
    # Sort by utilization rate
    doctor_stats.sort(key=lambda x: x['utilization_rate'], reverse=True)
    
    return Response({
        'date_range': {
            'start_date': start_date,
            'end_date': end_date
        },
        'appointments': {
            **appointment_stats,
            'no_show_rate': round(no_show_rate, 2)
        },
        'slots': {
            **slot_stats,
            'utilization_rate': round(utilization_rate, 2)
        },
        'calls': {
            **call_stats,
            'success_rate': round(call_success_rate, 2)
        },
        'reminders': reminder_stats,
        'doctors': doctor_stats
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def export_appointments_csv(request):
    """
    Export appointments to CSV.
    Implements FR-AN-03 (CSV export with StreamingHttpResponse).
    
    GET /api/v1/analytics/export/appointments/
    """
    # Date range filters
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    status_filter = request.query_params.get('status')
    
    # Build query
    appointments = Appointment.objects.select_related(
        'patient',
        'slot',
        'slot__doctor',
        'booked_by'
    ).all()
    
    if start_date:
        appointments = appointments.filter(slot__slot_date__gte=start_date)
    if end_date:
        appointments = appointments.filter(slot__slot_date__lte=end_date)
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    
    # Create CSV
    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Appointment ID',
            'Patient Name',
            'Patient Phone',
            'Doctor Name',
            'Date',
            'Time',
            'Status',
            'Booked By',
            'Booked At',
            'Notes'
        ])
        
        # Write data
        for appointment in appointments:
            writer.writerow([
                appointment.id,
                appointment.patient.full_name,
                appointment.patient.phone_number,
                appointment.slot.doctor.full_name,
                appointment.slot.slot_date,
                appointment.slot.start_time,
                appointment.status,
                appointment.booked_by.email if appointment.booked_by else 'N/A',
                appointment.booked_at.strftime('%Y-%m-%d %H:%M:%S'),
                appointment.notes or ''
            ])
            
            # Yield chunk
            data = output.getvalue()
            output.truncate(0)
            output.seek(0)
            yield data
    
    # Create streaming response
    response = StreamingHttpResponse(
        generate_csv(),
        content_type='text/csv'
    )
    response['Content-Disposition'] = f'attachment; filename="appointments_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def export_call_logs_csv(request):
    """
    Export call logs to CSV.
    
    GET /api/v1/analytics/export/call-logs/
    """
    # Date range filters
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    # Build query
    call_logs = CallLog.objects.select_related('patient', 'appointment').all()
    
    if start_date:
        call_logs = call_logs.filter(initiated_at__gte=start_date)
    if end_date:
        call_logs = call_logs.filter(initiated_at__lte=end_date)
    
    # Create CSV
    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Call ID',
            'Patient Name',
            'Patient Phone',
            'Call Type',
            'Attempt Number',
            'Outcome',
            'Duration (seconds)',
            'Transcription Status',
            'Initiated At',
            'Completed At'
        ])
        
        # Write data
        for call in call_logs:
            writer.writerow([
                call.id,
                call.patient.full_name,
                call.patient.phone_number,
                call.call_type,
                call.attempt_number,
                call.outcome,
                call.duration or 0,
                call.transcription_status,
                call.initiated_at.strftime('%Y-%m-%d %H:%M:%S'),
                call.completed_at.strftime('%Y-%m-%d %H:%M:%S') if call.completed_at else 'N/A'
            ])
            
            # Yield chunk
            data = output.getvalue()
            output.truncate(0)
            output.seek(0)
            yield data
    
    # Create streaming response
    response = StreamingHttpResponse(
        generate_csv(),
        content_type='text/csv'
    )
    response['Content-Disposition'] = f'attachment; filename="call_logs_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def trends_data(request):
    """
    Get trends data for charts.
    
    GET /api/v1/analytics/trends/
    """
    # Get last 30 days of data
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Daily appointment counts
    from django.db.models.functions import TruncDate
    
    daily_appointments = Appointment.objects.filter(
        slot__slot_date__gte=start_date,
        slot__slot_date__lte=end_date
    ).annotate(
        date=TruncDate('slot__slot_date')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Daily call counts
    daily_calls = CallLog.objects.filter(
        initiated_at__gte=start_date,
        initiated_at__lte=end_date
    ).annotate(
        date=TruncDate('initiated_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    return Response({
        'appointments': list(daily_appointments),
        'calls': list(daily_calls)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def export_patients_csv(request):
    """
    Export patients to CSV.
    
    GET /api/v1/analytics/export/patients/
    """
    from patients.models import Patient
    
    patients = Patient.objects.select_related('assigned_doctor').all()
    
    # Create CSV
    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Patient ID',
            'Full Name',
            'Phone Number',
            'Email',
            'Date of Birth',
            'Gender',
            'Assigned Doctor',
            'Created At'
        ])
        
        # Write data
        for patient in patients:
            writer.writerow([
                patient.id,
                patient.full_name,
                patient.phone_number,
                patient.email or 'N/A',
                patient.date_of_birth,
                patient.get_gender_display(),
                patient.assigned_doctor.full_name if patient.assigned_doctor else 'N/A',
                patient.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
            
            # Yield chunk
            data = output.getvalue()
            output.truncate(0)
            output.seek(0)
            yield data
    
    # Create streaming response
    response = StreamingHttpResponse(
        generate_csv(),
        content_type='text/csv'
    )
    response['Content-Disposition'] = f'attachment; filename="patients_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def export_doctors_csv(request):
    """
    Export doctors to CSV.
    
    GET /api/v1/analytics/export/doctors/
    """
    from doctors.models import Doctor
    
    doctors = Doctor.objects.all()
    
    # Create CSV
    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Doctor ID',
            'Full Name',
            'Specialization',
            'Phone Number',
            'Email',
            'Status',
            'Created At'
        ])
        
        # Write data
        for doctor in doctors:
            writer.writerow([
                doctor.id,
                doctor.full_name,
                doctor.specialization,
                doctor.phone_number,
                doctor.email,
                doctor.get_status_display(),
                doctor.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
            
            # Yield chunk
            data = output.getvalue()
            output.truncate(0)
            output.seek(0)
            yield data
    
    # Create streaming response
    response = StreamingHttpResponse(
        generate_csv(),
        content_type='text/csv'
    )
    response['Content-Disposition'] = f'attachment; filename="doctors_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def export_all_data_csv(request):
    """
    Export all data summary to CSV.
    
    GET /api/v1/analytics/export/all/
    """
    from patients.models import Patient
    from doctors.models import Doctor
    
    # Get stats
    stats = dashboard_stats(request).data
    
    # Create CSV
    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write summary header
        writer.writerow(['MediSched AI - Data Export Summary'])
        writer.writerow(['Generated:', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        
        # Appointment Statistics
        writer.writerow(['APPOINTMENT STATISTICS'])
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Total Appointments', stats['appointments']['total']])
        writer.writerow(['Confirmed', stats['appointments']['confirmed']])
        writer.writerow(['Completed', stats['appointments']['completed']])
        writer.writerow(['Cancelled', stats['appointments']['cancelled']])
        writer.writerow(['No Shows', stats['appointments']['no_shows']])
        writer.writerow(['No Show Rate (%)', stats['appointments']['no_show_rate']])
        writer.writerow([])
        
        # Slot Statistics
        writer.writerow(['SLOT STATISTICS'])
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Total Slots', stats['slots']['total']])
        writer.writerow(['Booked', stats['slots']['booked']])
        writer.writerow(['Available', stats['slots']['available']])
        writer.writerow(['Blocked', stats['slots']['blocked']])
        writer.writerow(['Utilization Rate (%)', stats['slots']['utilization_rate']])
        writer.writerow([])
        
        # Call Statistics
        writer.writerow(['CALL STATISTICS'])
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Total Calls', stats['calls']['total']])
        writer.writerow(['Completed', stats['calls']['completed']])
        writer.writerow(['Answered', stats['calls']['answered']])
        writer.writerow(['No Answer', stats['calls']['no_answer']])
        writer.writerow(['Failed', stats['calls']['failed']])
        writer.writerow(['Success Rate (%)', stats['calls']['success_rate']])
        writer.writerow([])
        
        # Doctor Statistics
        writer.writerow(['DOCTOR PERFORMANCE'])
        writer.writerow(['Doctor Name', 'Total Slots', 'Booked Slots', 'Appointments', 'Completed', 'No Shows', 'Utilization (%)'])
        for doc in stats['doctors']:
            writer.writerow([
                doc['doctor_name'],
                doc['total_slots'],
                doc['booked_slots'],
                doc['total_appointments'],
                doc['completed_appointments'],
                doc['no_shows'],
                round(doc['utilization_rate'], 2)
            ])
        
        # Yield chunk
        data = output.getvalue()
        output.truncate(0)
        output.seek(0)
        yield data
    
    # Create streaming response
    response = StreamingHttpResponse(
        generate_csv(),
        content_type='text/csv'
    )
    response['Content-Disposition'] = f'attachment; filename="medisched_summary_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    return response
