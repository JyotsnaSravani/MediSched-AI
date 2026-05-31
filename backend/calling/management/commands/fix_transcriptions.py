"""
Management command to fix existing transcriptions with speech recognition errors.
Run: python manage.py fix_transcriptions
"""

from django.core.management.base import BaseCommand
from calling.models import CallLog
from calling.transcription_fixer import fix_transcription


class Command(BaseCommand):
    help = 'Fix speech recognition errors in existing call transcriptions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without actually fixing',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get all call logs with notes (transcriptions)
        call_logs = CallLog.objects.filter(notes__isnull=False).exclude(notes='')
        
        total_count = call_logs.count()
        fixed_count = 0
        
        self.stdout.write(f"\nFound {total_count} call logs with transcriptions\n")
        self.stdout.write("=" * 80)
        
        for call_log in call_logs:
            # Get patient and doctor names for context
            patient_name = call_log.patient.full_name if call_log.patient else None
            doctor_name = None
            if call_log.appointment and call_log.appointment.slot:
                doctor_name = call_log.appointment.slot.doctor.full_name
            
            # Fix transcription
            original_notes = call_log.notes
            fixed_notes = fix_transcription(original_notes, patient_name=patient_name, doctor_name=doctor_name)
            
            # Check if anything changed
            if original_notes != fixed_notes:
                fixed_count += 1
                
                self.stdout.write(f"\n\nCall Log ID: {call_log.id}")
                self.stdout.write(f"Patient: {patient_name}")
                self.stdout.write(f"Doctor: {doctor_name}")
                self.stdout.write(f"\nORIGINAL:")
                self.stdout.write(self.style.ERROR(original_notes[:200] + "..." if len(original_notes) > 200 else original_notes))
                self.stdout.write(f"\nFIXED:")
                self.stdout.write(self.style.SUCCESS(fixed_notes[:200] + "..." if len(fixed_notes) > 200 else fixed_notes))
                self.stdout.write("-" * 80)
                
                if not dry_run:
                    call_log.notes = fixed_notes
                    call_log.save()
        
        self.stdout.write("\n" + "=" * 80)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\nDRY RUN: Would fix {fixed_count} out of {total_count} transcriptions')
            )
            self.stdout.write(
                self.style.WARNING('Run without --dry-run to apply fixes')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully fixed {fixed_count} out of {total_count} transcriptions')
            )
