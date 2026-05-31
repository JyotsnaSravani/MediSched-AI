"""
Update Twilio phone number webhook URL
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from twilio.rest import Client

print("═══════════════════════════════════════════════════════════════")
print("              UPDATE TWILIO WEBHOOK URL")
print("═══════════════════════════════════════════════════════════════")
print()

# Initialize Twilio client
client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

# Get the phone number
phone_numbers = client.incoming_phone_numbers.list(
    phone_number=settings.TWILIO_PHONE_NUMBER
)

if not phone_numbers:
    print(f"✗ Phone number {settings.TWILIO_PHONE_NUMBER} not found!")
    exit(1)

phone_number = phone_numbers[0]

print("CURRENT CONFIGURATION:")
print(f"  Phone Number: {phone_number.phone_number}")
print(f"  Voice URL: {phone_number.voice_url}")
print(f"  Voice Method: {phone_number.voice_method}")
print(f"  Status Callback: {phone_number.status_callback}")
print()

# New webhook URLs
new_voice_url = f"{settings.SITE_URL}/api/v1/calling/twiml-conversational/"
new_status_callback = f"{settings.SITE_URL}/api/v1/calling/status-callback/"

print("NEW CONFIGURATION:")
print(f"  Voice URL: {new_voice_url}")
print(f"  Voice Method: POST")
print(f"  Status Callback: {new_status_callback}")
print()

# Update the phone number
print("Updating...")
try:
    phone_number.update(
        voice_url=new_voice_url,
        voice_method='POST',
        status_callback=new_status_callback,
        status_callback_method='POST'
    )
    print()
    print("✓ WEBHOOK URL UPDATED SUCCESSFULLY!")
    print()
    print("You can now make test calls!")
    
except Exception as e:
    print(f"✗ Error updating webhook: {e}")

print()
print("═══════════════════════════════════════════════════════════════")
