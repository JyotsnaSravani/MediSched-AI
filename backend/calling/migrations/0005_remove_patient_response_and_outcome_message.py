# Generated migration to remove patient_response and outcome_message columns
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('calling', '0004_alter_calllog_outcome'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE call_logs DROP COLUMN IF EXISTS patient_response;",
            reverse_sql="ALTER TABLE call_logs ADD COLUMN patient_response VARCHAR(255);",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE call_logs DROP COLUMN IF EXISTS outcome_message;",
            reverse_sql="ALTER TABLE call_logs ADD COLUMN outcome_message TEXT;",
        ),
    ]
