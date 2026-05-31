# Generated migration for adding PENDING status to appointments

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointment',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pending'),
                    ('CONFIRMED', 'Confirmed'),
                    ('CANCELLED', 'Cancelled'),
                    ('COMPLETED', 'Completed'),
                    ('NO_SHOW', 'No Show')
                ],
                default='PENDING',
                help_text='Appointment status',
                max_length=20
            ),
        ),
    ]
