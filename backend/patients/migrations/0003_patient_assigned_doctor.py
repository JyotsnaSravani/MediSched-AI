# Generated migration for adding assigned_doctor field

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('doctors', '0001_initial'),
        ('patients', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='assigned_doctor',
            field=models.ForeignKey(
                blank=True,
                help_text='Primary doctor assigned to this patient',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_patients',
                to='doctors.doctor'
            ),
        ),
    ]
