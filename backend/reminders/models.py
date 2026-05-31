"""
Reminder models for automated reminder system.
Sprint 4 - Implements FR-RM-01 through FR-RM-04
"""

from django.db import models
from django.utils import timezone


class ReminderLog(models.Model):
    """
    Reminder log model - tracks all automated reminders sent to patients.
    Implements FR-RM-01 (24-hour reminders) and FR-RM-02 (multi-channel delivery).
    """
    
    class Channel(models.TextChoices):
        SMS = 'SMS', 'SMS'
        EMAIL = 'EMAIL', 'Email'
        BOTH = 'BOTH', 'Both'
    
    class DeliveryStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        DELIVERED = 'DELIVERED', 'Delivered'
        FAILED = 'FAILED', 'Failed'
        RETRY = 'RETRY', 'Retry'
    
    class ReminderType(models.TextChoices):
        BOOKING_CONFIRMATION = 'BOOKING_CONFIRMATION', 'Booking Confirmation'
        REMINDER_24H = 'REMINDER_24H', '24-Hour Reminder'
        REMINDER_1H = 'REMINDER_1H', '1-Hour Reminder'
        CANCELLATION = 'CANCELLATION', 'Cancellation'
        RESCHEDULING = 'RESCHEDULING', 'Rescheduling'
    
    # Core relationships
    appointment = models.ForeignKey(
        'scheduling.Appointment',
        on_delete=models.CASCADE,
        related_name='reminders',
        help_text="Appointment for this reminder"
    )
    
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='reminders',
        help_text="Patient receiving the reminder"
    )
    
    # Reminder details
    reminder_type = models.CharField(
        max_length=30,
        choices=ReminderType.choices,
        default=ReminderType.REMINDER_24H,
        help_text="Type of reminder"
    )
    
    channel = models.CharField(
        max_length=10,
        choices=Channel.choices,
        default=Channel.SMS,
        help_text="Delivery channel"
    )
    
    delivery_status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        help_text="Delivery status"
    )
    
    # Message content
    message_text = models.TextField(
        help_text="Message content sent to patient"
    )
    
    # Delivery tracking
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the reminder was sent"
    )
    
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the reminder was delivered"
    )
    
    # External service tracking
    twilio_message_sid = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Twilio message SID (for SMS)"
    )
    
    email_message_id = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Email service message ID"
    )
    
    # Retry tracking
    retry_count = models.IntegerField(
        default=0,
        help_text="Number of retry attempts"
    )
    
    last_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the last retry was attempted"
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if delivery failed"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the reminder was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the reminder was last updated"
    )
    
    class Meta:
        db_table = 'reminder_logs'
        verbose_name = 'Reminder Log'
        verbose_name_plural = 'Reminder Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['appointment', '-created_at']),
            models.Index(fields=['patient', '-created_at']),
            models.Index(fields=['delivery_status']),
            models.Index(fields=['reminder_type']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.reminder_type} for {self.patient.full_name} - {self.delivery_status}"
    
    def mark_sent(self, message_sid=None, email_id=None):
        """Mark reminder as sent."""
        self.delivery_status = self.DeliveryStatus.SENT
        self.sent_at = timezone.now()
        if message_sid:
            self.twilio_message_sid = message_sid
        if email_id:
            self.email_message_id = email_id
        self.save()
    
    def mark_delivered(self):
        """Mark reminder as delivered."""
        self.delivery_status = self.DeliveryStatus.DELIVERED
        self.delivered_at = timezone.now()
        self.save()
    
    def mark_failed(self, error_message):
        """Mark reminder as failed."""
        self.delivery_status = self.DeliveryStatus.FAILED
        self.error_message = error_message
        self.save()
    
    def increment_retry(self):
        """Increment retry count."""
        self.retry_count += 1
        self.last_retry_at = timezone.now()
        self.delivery_status = self.DeliveryStatus.RETRY
        self.save()
