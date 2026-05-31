"""
Patient model for centralized patient registry.
Implements FR-PM-01 through FR-PM-08.
"""

from django.db import models
from django.core.validators import RegexValidator


class Patient(models.Model):
    """
    Patient model - centralized registry managed by staff.
    Stores patient information for scheduling and AI calling.
    """
    
    class Gender(models.TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'
        OTHER = 'OTHER', 'Other'
    
    # Required fields (FR-PM-01, FR-PM-03)
    full_name = models.CharField(
        max_length=200,
        verbose_name='Full name *',
        help_text="Patient's full name"
    )
    
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(
        validators=[phone_validator],
        max_length=17,
        unique=True,
        verbose_name='Phone number *',
        help_text="Primary contact number for AI calls and SMS"
    )
    
    date_of_birth = models.DateField(
        verbose_name='Date of birth *',
        help_text="Patient's date of birth"
    )
    
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        verbose_name='Gender *',
        help_text="Patient's gender"
    )
    
    # Optional fields (FR-PM-02)
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email for appointment reminders"
    )
    
    address = models.TextField(
        blank=True,
        null=True,
        help_text="Patient's address"
    )
    
    medical_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Medical history, reason for visit, prior notes"
    )
    
    referring_doctor = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Name of referring physician"
    )
    
    # Assigned doctor for primary care (REQUIRED)
    assigned_doctor = models.ForeignKey(
        'doctors.Doctor',
        on_delete=models.PROTECT,  # Changed to PROTECT since it's required
        null=False,  # Required field
        blank=False,  # Required field
        related_name='assigned_patients',
        verbose_name='Assigned doctor *',  # Add asterisk in verbose_name
        help_text="Primary doctor assigned to this patient (Required)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_patients',
        help_text="Staff member who created this record"
    )
    
    class Meta:
        db_table = 'patients'
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['full_name']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"
    
    @property
    def age(self) -> int:
        """Calculate patient's age from date of birth."""
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
