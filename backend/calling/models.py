"""
Calling models for AI outbound calling system.
Sprint 3 - Implements FR-AC-01 through FR-AC-08
"""

from django.db import models
from django.utils import timezone


class CallLog(models.Model):
    """
    Call log model - tracks all AI outbound calls with attempt tracking.
    Implements FR-AC-01 (3-attempt escalation) and FR-AC-02 (call logging).
    """
    
    class CallType(models.TextChoices):
        APPOINTMENT_REMINDER = 'APPOINTMENT_REMINDER', 'Appointment Reminder'
        APPOINTMENT_CONFIRMATION = 'APPOINTMENT_CONFIRMATION', 'Appointment Confirmation'
        SLOT_OFFER = 'SLOT_OFFER', 'Slot Offer'
        FOLLOW_UP = 'FOLLOW_UP', 'Follow Up'
        GENERAL = 'GENERAL', 'General'
    
    class Outcome(models.TextChoices):
        ANSWERED = 'ANSWERED', 'Answered'
        NO_ANSWER = 'NO_ANSWER', 'No Answer'
        BUSY = 'BUSY', 'Busy'
        FAILED = 'FAILED', 'Failed'
        VOICEMAIL = 'VOICEMAIL', 'Voicemail'
        COMPLETED = 'COMPLETED', 'Completed'
    
    class TranscriptionStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        NO_RECORDING = 'NO_RECORDING', 'No Recording'
    
    # Core relationships
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='call_logs',
        help_text="Patient who was called"
    )
    
    appointment = models.ForeignKey(
        'scheduling.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='call_logs',
        help_text="Related appointment (if applicable)"
    )
    
    # Call details
    call_type = models.CharField(
        max_length=30,
        choices=CallType.choices,
        default=CallType.GENERAL,
        help_text="Type of call"
    )
    
    attempt_number = models.IntegerField(
        default=1,
        help_text="Attempt number (1, 2, or 3)"
    )
    
    outcome = models.CharField(
        max_length=20,
        choices=Outcome.choices,
        null=True,
        blank=True,
        help_text="Call outcome"
    )
    
    # Twilio integration
    twilio_call_sid = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text="Twilio call SID"
    )
    
    twilio_recording_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL to call recording"
    )
    
    duration = models.IntegerField(
        null=True,
        blank=True,
        help_text="Call duration in seconds"
    )
    
    # Transcription tracking
    transcription_status = models.CharField(
        max_length=20,
        choices=TranscriptionStatus.choices,
        default=TranscriptionStatus.NO_RECORDING,
        help_text="Transcription status"
    )
    
    # Metadata
    initiated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the call was initiated"
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the call completed"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about the call"
    )
    
    class Meta:
        db_table = 'call_logs'
        verbose_name = 'Call Log'
        verbose_name_plural = 'Call Logs'
        ordering = ['-initiated_at']
        indexes = [
            models.Index(fields=['patient', '-initiated_at']),
            models.Index(fields=['appointment']),
            models.Index(fields=['outcome']),
            models.Index(fields=['transcription_status']),
            models.Index(fields=['-initiated_at']),
        ]
    
    def __str__(self):
        return f"Call to {self.patient.full_name} - Attempt {self.attempt_number} - {self.outcome}"
    
    def mark_completed(self, outcome, duration=None, recording_url=None):
        """Mark call as completed with outcome."""
        self.outcome = outcome
        self.completed_at = timezone.now()
        self.duration = duration
        self.twilio_recording_url = recording_url
        
        # Set transcription status based on recording
        if recording_url:
            self.transcription_status = self.TranscriptionStatus.PENDING
        else:
            self.transcription_status = self.TranscriptionStatus.NO_RECORDING
        
        self.save()


class ManualCallbackTask(models.Model):
    """
    Manual callback task - created when all 3 AI call attempts fail.
    Implements FR-AC-03 (manual callback escalation).
    """
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    # Core relationships
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='manual_callback_tasks',
        help_text="Patient to call back"
    )
    
    appointment = models.ForeignKey(
        'scheduling.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manual_callback_tasks',
        help_text="Related appointment (if applicable)"
    )
    
    # Task details
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Task status"
    )
    
    reason = models.TextField(
        help_text="Reason for manual callback (e.g., '3 AI call attempts failed')"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes for staff"
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_callback_tasks',
        help_text="Staff member assigned to this task"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the task was created"
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the task was completed"
    )
    
    completed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_callback_tasks',
        help_text="Staff member who completed this task"
    )
    
    class Meta:
        db_table = 'manual_callback_tasks'
        verbose_name = 'Manual Callback Task'
        verbose_name_plural = 'Manual Callback Tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Manual callback for {self.patient.full_name} - {self.status}"
    
    def mark_completed(self, user, notes=None):
        """Mark task as completed."""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.completed_by = user
        if notes:
            self.notes = notes
        self.save()
