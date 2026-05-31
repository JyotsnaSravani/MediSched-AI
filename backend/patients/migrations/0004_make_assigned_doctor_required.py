# Generated migration to make assigned_doctor required

from django.db import migrations, models
import django.db.models.deletion


def assign_default_doctor(apps, schema_editor):
    """Assign a default doctor to all patients without one."""
    Patient = apps.get_model('patients', 'Patient')
    Doctor = apps.get_model('doctors', 'Doctor')
    
    # Get the first available doctor
    default_doctor = Doctor.objects.first()
    
    if default_doctor:
        # Update all patients without an assigned doctor
        patients_without_doctor = Patient.objects.filter(assigned_doctor__isnull=True)
        count = patients_without_doctor.update(assigned_doctor=default_doctor)
        print(f"Assigned Dr. {default_doctor.full_name} to {count} patients")
    else:
        print("Warning: No doctors found in database. Please create a doctor first.")


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0003_patient_assigned_doctor'),
        ('doctors', '0002_initial'),
    ]

    operations = [
        # Step 1: Assign default doctor to existing patients
        migrations.RunPython(assign_default_doctor, reverse_code=migrations.RunPython.noop),
        
        # Step 2: Make the field required
        migrations.AlterField(
            model_name='patient',
            name='assigned_doctor',
            field=models.ForeignKey(
                help_text='Primary doctor assigned to this patient (Required)',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='assigned_patients',
                to='doctors.doctor'
            ),
        ),
    ]
