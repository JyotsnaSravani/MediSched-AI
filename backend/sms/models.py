from django.db import models
from django.utils import timezone


class SMSLog(models.Model):
    """Log of all SMS messages sent"""
    
    class MessageType(models.TextChoices):
        APPOINTMENT_REMINDER = 'APPOINTMENT_REMINDER', 'Appointment Reminder'
        APPOINTMENT_CONFIRMATION = 'APPOINTMENT_CONFIRMATION', 'Appointment Confirmation'
        APPOINTMENT_CANCELLED = 'APPOINTMENT_CANCELLED', 'Appointment Cancelled'
        GENERAL = 'GENERAL', 'General Message'
    
    class Status(models.TextChoices):
        QUEUED = 'QUEUED', 'Queued'
        SENT = 'SENT', 'Sent'
        DELIVERED = 'DELIVERED', 'Delivered'
        FAILED = 'FAILED', 'Failed'
    
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='sms_logs'
    )
    
    appointment = models.ForeignKey(
        'scheduling.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sms_logs'
    )
    
    message_type = models.CharField(
        max_length=30,
        choices=MessageType.choices,
        default=MessageType.GENERAL
    )
    
    message_body = models.TextField(help_text="SMS message content")
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED
    )
    
    twilio_sid = models.CharField(max_length=100, null=True, blank=True)
    
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    error_message = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'sms_logs'
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"SMS to {self.patient.full_name} - {self.status}"
