"""
View transcriptions with full text.
"""

import sys
import os
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from transcriptions.models import Transcription

def main():
    print("\n" + "="*80)
    print("  TRANSCRIPTIONS")
    print("="*80)
    
    transcriptions = Transcription.objects.select_related(
        'call_log', 'call_log__patient', 'appointment'
    ).order_by('-created_at')
    
    total = transcriptions.count()
    print(f"\nTotal Transcriptions: {total}\n")
    
    if total == 0:
        print("No transcriptions found.")
        return
    
    # Show first 5 transcriptions
    for i, t in enumerate(transcriptions[:5], 1):
        print("="*80)
        print(f"Transcription #{i}")
        print("="*80)
        print(f"ID: {t.id}")
        print(f"Patient: {t.patient.full_name}")
        print(f"Phone: {t.patient.phone_number}")
        print(f"Call Date: {t.call_log.initiated_at}")
        print(f"Call Type: {t.call_log.call_type}")
        print(f"Call Outcome: {t.call_log.outcome}")
        print(f"Duration: {t.call_log.duration or 0}s")
        
        if t.appointment:
            print(f"Appointment: {t.appointment.slot.slot_date} at {t.appointment.slot.start_time}")
        
        print(f"\nStatus: {t.status}")
        print(f"Word Count: {t.word_count}")
        print(f"Created: {t.created_at}")
        
        if t.is_edited:
            print(f"Edited by: {t.last_edited_by.email}")
            print(f"Edited at: {t.last_edited_at}")
        
        print(f"\n📝 TRANSCRIPTION TEXT:")
        print("-" * 80)
        print(t.text)
        print("-" * 80)
        print()
    
    if total > 5:
        print(f"\n... and {total - 5} more transcriptions")
    
    print("="*80)
    print("\n💡 Access transcriptions via API:")
    print("   GET http://localhost:8000/api/v1/transcriptions/")
    print("   (Requires authentication)")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
