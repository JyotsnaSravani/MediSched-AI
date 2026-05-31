"""
Doctor model for doctor profiles and slot management.
Implements FR-DM-01 through FR-DM-03 and FR-DS-01 through FR-DS-08.
"""

from django.db import models
from django.core.validators import RegexValidator


class Doctor(models.Model):
    """
    Doctor model - profiles managed by Admin, slots managed by Doctor/Admin.
    """
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
    
    # Basic Information (FR-DM-01)
    full_name = models.CharField(
        max_length=200,
        help_text="Doctor's full name"
    )
    
    specialization = models.CharField(
        max_length=200,
        help_text="Medical specialization (e.g., Radiology, Pathology)"
    )
    
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(
        validators=[phone_validator],
        max_length=17,
        help_text="Contact phone number"
    )
    
    email = models.EmailField(
        help_text="Contact email address"
    )
    
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Active doctors appear in scheduling"
    )
    
    # Link to User account (for doctor login)
    user = models.OneToOneField(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='doctor_profile',
        help_text="User account for doctor login"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'doctors'
        verbose_name = 'Doctor'
        verbose_name_plural = 'Doctors'
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['specialization']),
        ]
    
    def __str__(self):
        return f"Dr. {self.full_name} ({self.specialization})"


class DoctorSlot(models.Model):
    """
    Doctor availability slots for appointment scheduling.
    Implements FR-DS-01 through FR-DS-08.
    """
    
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        BOOKED = 'BOOKED', 'Booked'
        BLOCKED = 'BLOCKED', 'Blocked'
    
    class Duration(models.IntegerChoices):
        THIRTY_MIN = 30, '30 minutes'
        SIXTY_MIN = 60, '60 minutes'
    
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='slots',
        help_text="Doctor for this slot"
    )
    
    slot_date = models.DateField(
        help_text="Date of the slot"
    )
    
    start_time = models.TimeField(
        help_text="Start time of the slot"
    )
    
    end_time = models.TimeField(
        help_text="End time of the slot"
    )
    
    duration = models.IntegerField(
        choices=Duration.choices,
        default=Duration.THIRTY_MIN,
        help_text="Slot duration in minutes"
    )
    
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.AVAILABLE,
        help_text="Slot availability status"
    )
    
    # Booking information (populated when status = BOOKED)
    booked_patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booked_slots',
        help_text="Patient who booked this slot"
    )
    
    booked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when slot was booked"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'doctor_slots'
        verbose_name = 'Doctor Slot'
        verbose_name_plural = 'Doctor Slots'
        ordering = ['slot_date', 'start_time']
        unique_together = [['doctor', 'slot_date', 'start_time']]
        indexes = [
            models.Index(fields=['doctor', 'slot_date', 'status']),
            models.Index(fields=['slot_date', 'status']),
            models.Index(fields=['booked_patient']),
        ]
    
    def __str__(self):
        return f"{self.doctor.full_name} - {self.slot_date} {self.start_time} ({self.get_status_display()})"
