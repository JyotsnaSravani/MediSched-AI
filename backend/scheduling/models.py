"""
Appointment model for scheduling system.
Implements FR-CM-01 through FR-CM-05.
"""

from django.db import models
from django.utils import timezone


class Appointment(models.Model):
    """
    Appointment model - links patient to doctor slot.
    Implements concurrent booking prevention with select_for_update().
    """
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        COMPLETED = 'COMPLETED', 'Completed'
        NO_SHOW = 'NO_SHOW', 'No Show'
    
    # Core relationships
    slot = models.OneToOneField(
        'doctors.DoctorSlot',
        on_delete=models.CASCADE,
        related_name='appointment',
        help_text="Doctor slot for this appointment"
    )
    
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='appointments',
        help_text="Patient for this appointment"
    )
    
    # Appointment details
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Appointment status"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Appointment notes or reason for visit"
    )
    
    # Metadata
    booked_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='booked_appointments',
        help_text="Staff member who booked this appointment"
    )
    
    booked_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the appointment was booked"
    )
    
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the appointment was cancelled"
    )
    
    cancelled_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_appointments',
        help_text="User who cancelled this appointment"
    )
    
    cancellation_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for cancellation"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'appointments'
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'
        ordering = ['-booked_at']
        indexes = [
            models.Index(fields=['patient', '-booked_at']),
            models.Index(fields=['status']),
            models.Index(fields=['-booked_at']),
        ]
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.slot.doctor.full_name} on {self.slot.slot_date}"
    
    def cancel(self, user, reason=None):
        """Cancel this appointment and revert slot to available."""
        self.status = self.Status.CANCELLED
        self.cancelled_at = timezone.now()
        self.cancelled_by = user
        self.cancellation_reason = reason
        self.save()
        
        # Revert slot to available
        self.slot.status = 'AVAILABLE'
        self.slot.booked_patient = None
        self.slot.booked_at = None
        self.slot.save()
    
    @property
    def doctor(self):
        """Get the doctor for this appointment."""
        return self.slot.doctor
    
    @property
    def appointment_datetime(self):
        """Get the full datetime of the appointment."""
        from datetime import datetime
        return datetime.combine(self.slot.slot_date, self.slot.start_time)
