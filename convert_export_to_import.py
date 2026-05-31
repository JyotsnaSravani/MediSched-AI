"""
Convert exported patient CSV to import format.
This allows you to export patients, modify them, and re-import.
"""

import csv
import sys
from datetime import datetime

def convert_csv(input_file, output_file):
    """
    Convert exported CSV format to import format.
    
    Export format:
    ID,Name,Phone,Email,Age,Gender,Date of Birth,Assigned Doctor,Registered
    
    Import format:
    Full Name,Phone Number,Email,Date of Birth,Gender,Assigned Doctor ID,Address,Medical Notes,Referring Doctor
    """
    
    # Read exported CSV
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Filter out empty rows
    rows = [row for row in rows if row.get('Name') and row.get('Phone')]
    
    if not rows:
        print("❌ No valid patient data found in CSV")
        return
    
    # Convert to import format
    import_rows = []
    for row in rows:
        # Parse phone number (handle scientific notation)
        phone = row['Phone'].strip()
        if 'E+' in phone or 'e+' in phone:
            # Convert scientific notation to regular number
            phone = str(int(float(phone)))
        
        # Add country code if missing
        if not phone.startswith('+'):
            phone = '+91' + phone  # Default to India country code
        
        # Parse date of birth (convert from DD-MM-YYYY to YYYY-MM-DD)
        dob = row['Date of Birth'].strip()
        try:
            if '-' in dob:
                parts = dob.split('-')
                if len(parts[0]) == 2:  # DD-MM-YYYY format
                    dob = f"{parts[2]}-{parts[1]}-{parts[0]}"
        except:
            print(f"⚠️  Warning: Invalid date format for {row['Name']}: {dob}")
            continue
        
        # Parse gender (capitalize)
        gender = row['Gender'].strip().upper()
        if gender not in ['MALE', 'FEMALE', 'OTHER']:
            print(f"⚠️  Warning: Invalid gender for {row['Name']}: {gender}")
            continue
        
        # Extract doctor ID from "Dr. Name" format
        # You'll need to manually add the doctor ID
        assigned_doctor = row['Assigned Doctor'].strip()
        doctor_id = ''  # Will need to be filled manually or looked up
        
        import_rows.append({
            'Full Name': row['Name'].strip(),
            'Phone Number': phone,
            'Email': row['Email'].strip() if row.get('Email') else '',
            'Date of Birth': dob,
            'Gender': gender,
            'Assigned Doctor ID': doctor_id,  # NEEDS TO BE FILLED
            'Address': '',
            'Medical Notes': '',
            'Referring Doctor': ''
        })
    
    # Write import CSV
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['Full Name', 'Phone Number', 'Email', 'Date of Birth', 'Gender', 
                     'Assigned Doctor ID', 'Address', 'Medical Notes', 'Referring Doctor']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(import_rows)
    
    print(f"✅ Converted {len(import_rows)} patients")
    print(f"📄 Output file: {output_file}")
    print("\n⚠️  IMPORTANT: You must fill in 'Assigned Doctor ID' column before importing!")
    print("   Available Doctor IDs:")
    print("   - 4: Dr. Emily Rodriguez")
    print("   - 5: Dr. David Kim")
    print("   - 6: Dr. Sarah Johnson")
    print("   - 7: Dr. Michael Chen")
    print("   - 8: Dr. Lisa Anderson")
    print("   - 9: Dr. James Wilson")
    print("   - 10: Dr. Maria Garcia")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python convert_export_to_import.py <input_csv> <output_csv>")
        print("Example: python convert_export_to_import.py patients-2026-05-29.csv patients_import_ready.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    convert_csv(input_file, output_file)
