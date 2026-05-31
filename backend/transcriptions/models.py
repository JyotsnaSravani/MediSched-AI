"""
Transcription models for call transcription system.
Sprint 3 - Implements FR-CD-01 through FR-CD-06
"""

from django.db import models
from django.utils import timezone


class Transcription(models.Model):
    """
    Transcription model - stores call transcriptions from Whisper API.
    Implements FR-CD-01 (auto-transcription) and FR-CD-02 (staff editing).
    """
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
    
    # Core relationships (1:1 with CallLog)
    call_log = models.OneToOneField(
        'calling.CallLog',
        on_delete=models.CASCADE,
        related_name='transcription',
        help_text="Call log for this transcription"
    )
    
    appointment = models.ForeignKey(
        'scheduling.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transcriptions',
        help_text="Related appointment (auto-tagged)"
    )
    
    # Transcription content
    text = models.TextField(
        help_text="Transcribed text from call recording"
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Transcription status"
    )
    
    # Whisper API metadata
    whisper_model = models.CharField(
        max_length=50,
        default='whisper-1',
        help_text="Whisper model used for transcription"
    )
    
    confidence_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Transcription confidence score (if available)"
    )
    
    # Editing tracking
    is_edited = models.BooleanField(
        default=False,
        help_text="Whether transcription has been edited by staff"
    )
    
    last_edited_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edited_transcriptions',
        help_text="Staff member who last edited this transcription"
    )
    
    last_edited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the transcription was last edited"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the transcription was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the transcription was last updated"
    )
    
    class Meta:
        db_table = 'transcriptions'
        verbose_name = 'Transcription'
        verbose_name_plural = 'Transcriptions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['call_log']),
            models.Index(fields=['appointment']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        patient_name = self.call_log.patient.full_name
        return f"Transcription for {patient_name} - {self.status}"
    
    def update_text(self, new_text, user):
        """Update transcription text and track editor."""
        self.text = new_text
        self.is_edited = True
        self.last_edited_by = user
        self.last_edited_at = timezone.now()
        self.save()
    
    @property
    def patient(self):
        """Get patient from call log."""
        return self.call_log.patient
    
    @property
    def word_count(self):
        """Get word count of transcription."""
        return len(self.text.split())
