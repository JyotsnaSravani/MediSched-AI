# Generated migration to fix outcome field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calling', '0003_alter_calllog_outcome'),
    ]

    operations = [
        migrations.AlterField(
            model_name='calllog',
            name='outcome',
            field=models.CharField(
                blank=True,
                choices=[
                    ('ANSWERED', 'Answered'),
                    ('NO_ANSWER', 'No Answer'),
                    ('BUSY', 'Busy'),
                    ('FAILED', 'Failed'),
                    ('VOICEMAIL', 'Voicemail'),
                    ('COMPLETED', 'Completed'),
                ],
                help_text='Call outcome',
                max_length=20,
                null=True,
            ),
        ),
    ]
