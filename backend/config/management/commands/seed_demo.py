"""
Management command to seed demo data for MediSched AI.
Creates doctors, patients, and slots for demonstration.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from users.models import User
from doctors.models import Doctor, DoctorSlot
from patients.models import Patient
from scheduling.models import Appointment


class Command(BaseCommand):
    help = 'Seed demo data for MediSched AI'

    def handle(self, *args, **options):
        self.stdout.write('Seeding demo data...')
        
        # Create admin user if not exists
        admin_user, created = User.objects.get_or_create(
            email='test@test.com',
            defaults={
                'username': 'test',
                'first_name': 'Test',
                'last_name': 'User',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True
            }
        )
        if created:
            admin_user.set_password('Test@123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('✓ Created admin user'))
        else:
            # Update password for existing user
            admin_user.set_password('Test@123')
            admin_user.is_active = True
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('✓ Updated admin user password'))
            self.stdout.write(self.style.SUCCESS('✓ Updated admin user password'))
        
        # Create doctors
        doctors_data = [
            {'name': 'Sarah Johnson', 'spec': 'Radiology', 'phone': '+1234567890', 'email': 'sarah.j@medisched.com'},
            {'name': 'Michael Chen', 'spec': 'Pathology', 'phone': '+1234567891', 'email': 'michael.c@medisched.com'},
            {'name': 'Emily Rodriguez', 'spec': 'Cardiology', 'phone': '+1234567892', 'email': 'emily.r@medisched.com'},
            {'name': 'David Kim', 'spec': 'Neurology', 'phone': '+1234567893', 'email': 'david.k@medisched.com'},
            {'name': 'Lisa Anderson', 'spec': 'Orthopedics', 'phone': '+1234567894', 'email': 'lisa.a@medisched.com'},
        ]
        
        doctors = []
        for doc_data in doctors_data:
            doctor, created = Doctor.objects.get_or_create(
                email=doc_data['email'],
                defaults={
                    'full_name': doc_data['name'],
                    'specialization': doc_data['spec'],
                    'phone_number': doc_data['phone'],
                    'status': 'ACTIVE'
                }
            )
            doctors.append(doctor)
            if created:
                self.stdout.write(f'✓ Created doctor: {doctor.full_name}')
        
        # Create patients
        patients_data = [
            {'name': 'John Smith', 'phone': '+1555000001', 'dob': '1980-05-15', 'gender': 'MALE', 'email': 'john.smith@email.com'},
            {'name': 'Mary Williams', 'phone': '+1555000002', 'dob': '1975-08-22', 'gender': 'FEMALE', 'email': 'mary.w@email.com'},
            {'name': 'Robert Brown', 'phone': '+1555000003', 'dob': '1990-03-10', 'gender': 'MALE', 'email': 'robert.b@email.com'},
            {'name': 'Jennifer Davis', 'phone': '+1555000004', 'dob': '1985-11-30', 'gender': 'FEMALE', 'email': 'jennifer.d@email.com'},
            {'name': 'James Wilson', 'phone': '+1555000005', 'dob': '1978-07-18', 'gender': 'MALE', 'email': 'james.w@email.com'},
        ]
        
        patients = []
        for index, pat_data in enumerate(patients_data):
            assigned_doctor = doctors[index % len(doctors)]
            patient, created = Patient.objects.get_or_create(
                phone_number=pat_data['phone'],
                defaults={
                    'full_name': pat_data['name'],
                    'date_of_birth': pat_data['dob'],
                    'gender': pat_data['gender'],
                    'email': pat_data['email'],
                    'assigned_doctor': assigned_doctor,
                    'created_by': admin_user
                }
            )
            if not created and not patient.assigned_doctor_id:
                patient.assigned_doctor = assigned_doctor
                patient.save(update_fields=['assigned_doctor'])
            patients.append(patient)
            if created:
                self.stdout.write(f'✓ Created patient: {patient.full_name}')
        
        # Create slots for next 3 days
        today = datetime.now().date()
        slots_created = 0
        
        for day_offset in range(3):
            slot_date = today + timedelta(days=day_offset)
            
            for doctor in doctors[:3]:  # First 3 doctors
                # Morning slots (9 AM - 12 PM)
                start_time = datetime.strptime('09:00', '%H:%M').time()
                end_time = datetime.strptime('12:00', '%H:%M').time()
                
                current_time = datetime.combine(slot_date, start_time)
                end_datetime = datetime.combine(slot_date, end_time)
                
                while current_time < end_datetime:
                    slot_end = current_time + timedelta(minutes=30)
                    
                    slot, created = DoctorSlot.objects.get_or_create(
                        doctor=doctor,
                        slot_date=slot_date,
                        start_time=current_time.time(),
                        defaults={
                            'end_time': slot_end.time(),
                            'duration': 30,
                            'status': 'AVAILABLE'
                        }
                    )
                    
                    if created:
                        slots_created += 1
                    
                    current_time = slot_end
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created {slots_created} slots'))
        
        # Book some sample appointments
        available_slots = DoctorSlot.objects.filter(status='AVAILABLE')[:5]
        appointments_created = 0
        
        for i, slot in enumerate(available_slots):
            if i < len(patients):
                slot.status = 'BOOKED'
                slot.booked_patient = patients[i]
                slot.booked_at = timezone.now()
                slot.save()
                
                Appointment.objects.create(
                    slot=slot,
                    patient=patients[i],
                    notes='Regular checkup',
                    booked_by=admin_user,
                    status='CONFIRMED'
                )
                appointments_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created {appointments_created} appointments'))
        
        # Block some slots
        available_slots = DoctorSlot.objects.filter(status='AVAILABLE')[:3]
        for slot in available_slots:
            slot.status = 'BLOCKED'
            slot.save()
        
        self.stdout.write(self.style.SUCCESS(f'✓ Blocked 3 slots'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Demo data seeded successfully!'))
        self.stdout.write(f'\nSummary:')
        self.stdout.write(f'  - Doctors: {Doctor.objects.count()}')
        self.stdout.write(f'  - Patients: {Patient.objects.count()}')
        self.stdout.write(f'  - Slots: {DoctorSlot.objects.count()}')
        self.stdout.write(f'  - Appointments: {Appointment.objects.count()}')
