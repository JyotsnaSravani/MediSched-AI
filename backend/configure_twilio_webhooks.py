"""
Configure Twilio phone number with proper webhook URLs
"""

import os
from decouple import config
from twilio.rest import Client

print("=" * 80)
print("CONFIGURING TWILIO WEBHOOKS")
print("=" * 80)
print()

# Load Twilio credentials
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER')
SITE_URL = config('SITE_URL')

print(f"Twilio Account SID: {TWILIO_ACCOUNT_SID}")
print(f"Twilio Phone Number: {TWILIO_PHONE_NUMBER}")
print(f"Site URL: {SITE_URL}")
print()

# Initialize Twilio client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Define webhook URLs
voice_url = f"{SITE_URL}/api/v1/calling/twiml-conversational/"
status_callback_url = f"{SITE_URL}/api/v1/calling/status-callback/"
recording_callback_url = f"{SITE_URL}/api/v1/calling/recording-callback/"

print("Webhook URLs:")
print(f"  Voice URL: {voice_url}")
print(f"  Status Callback: {status_callback_url}")
print(f"  Recording Callback: {recording_callback_url}")
print()

try:
    # Get all phone numbers
    print("Fetching phone numbers...")
    phone_numbers = client.incoming_phone_numbers.list()
    
    # Find our phone number
    target_number = None
    for number in phone_numbers:
        if number.phone_number == TWILIO_PHONE_NUMBER:
            target_number = number
            break
    
    if not target_number:
        print(f"❌ Phone number {TWILIO_PHONE_NUMBER} not found in account")
        print()
        print("Available phone numbers:")
        for number in phone_numbers:
            print(f"  - {number.phone_number} (SID: {number.sid})")
        exit(1)
    
    print(f"✅ Found phone number: {target_number.phone_number}")
    print(f"   SID: {target_number.sid}")
    print()
    
    print("Current Configuration:")
    print(f"  Voice URL: {target_number.voice_url or 'NOT SET'}")
    print(f"  Status Callback: {target_number.status_callback or 'NOT SET'}")
    print()
    
    # Update the phone number configuration
    print("Updating phone number configuration...")
    updated_number = client.incoming_phone_numbers(target_number.sid).update(
        voice_url=voice_url,
        voice_method='POST',
        status_callback=status_callback_url,
        status_callback_method='POST'
    )
    
    print("✅ Phone number updated successfully!")
    print()
    
    print("New Configuration:")
    print(f"  Voice URL: {updated_number.voice_url}")
    print(f"  Voice Method: {updated_number.voice_method}")
    print(f"  Status Callback: {updated_number.status_callback}")
    print(f"  Status Callback Method: {updated_number.status_callback_method}")
    print()
    
    print("=" * 80)
    print("IMPORTANT NOTES")
    print("=" * 80)
    print()
    print("1. Status Callback URL is now configured")
    print("2. Future calls will automatically update Outcome and Duration")
    print("3. Recording callback is handled separately in TwiML")
    print()
    print("✅ Configuration complete!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
