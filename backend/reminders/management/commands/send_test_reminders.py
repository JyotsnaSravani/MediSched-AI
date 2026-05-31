from django.core.management.base import BaseCommand
from reminders.models import ReminderLog
from scheduling.models import Appointment
from patients.models import Patient


class Command(BaseCommand):
    help = 'Send test reminders to populate the reminders page'

    def handle(self, *args, **options):
        self.stdout.write("📧 Creating test reminders...\n")
        
        # Get some patients
        patients = Patient.objects.all()[:5]
        
        if not patients:
            self.stdout.write(self.style.ERROR("No patients found!"))
            return
        
        count = 0
        for patient in patients:
            # Create a test reminder
            reminder = ReminderLog.objects.create(
                patient=patient,
                reminder_type=ReminderLog.ReminderType.APPOINTMENT_REMINDER,
                channel=ReminderLog.Channel.EMAIL,
                delivery_status=ReminderLog.DeliveryStatus.SENT,
                message_text=f"Test reminder for {patient.full_name}"
            )
            count += 1
            self.stdout.write(f"✅ Created reminder for {patient.full_name}")
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Created {count} test reminders!"))
        self.stdout.write("View them at: http://localhost:3000/reminders-corporate.html")
