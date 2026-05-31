"""
Slot generation service for doctors.
Implements FR-DS-01, FR-DS-02: Auto-generate slots with overlap detection.
"""

from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from .models import DoctorSlot


def generate_doctor_slots(doctor, slot_date, start_time, end_time, duration):
    """
    Generate doctor slots for a given date and time range.
    
    Args:
        doctor: Doctor instance
        slot_date: Date for slots
        start_time: Start time (datetime.time)
        end_time: End time (datetime.time)
        duration: Slot duration in minutes (30 or 60)
    
    Returns:
        List of created DoctorSlot instances
    
    Raises:
        ValueError: If no slots could be generated
    """
    
    # Convert times to datetime for calculation
    current_time = datetime.combine(slot_date, start_time)
    end_datetime = datetime.combine(slot_date, end_time)
    
    slots_to_create = []
    
    # Generate slot times
    while current_time < end_datetime:
        slot_end_time = current_time + timedelta(minutes=duration)
        
        # Don't create slot if it extends beyond end_time
        if slot_end_time > end_datetime:
            break
        
        slots_to_create.append({
            'doctor': doctor,
            'slot_date': slot_date,
            'start_time': current_time.time(),
            'end_time': slot_end_time.time(),
            'duration': duration,
            'status': DoctorSlot.Status.AVAILABLE
        })
        
        current_time = slot_end_time
    
    if not slots_to_create:
        raise ValueError("No slots could be generated with the given parameters")
    
    # Create slots, skipping overlaps instead of failing
    created_slots = []
    skipped_count = 0
    
    with transaction.atomic():
        for slot_data in slots_to_create:
            # Check for overlaps with existing slots
            overlapping = DoctorSlot.objects.filter(
                doctor=doctor,
                slot_date=slot_date,
                start_time__lt=slot_data['end_time'],
                end_time__gt=slot_data['start_time']
            ).exists()
            
            if overlapping:
                # Skip this slot instead of failing
                skipped_count += 1
                continue
            
            # Create the slot
            slot = DoctorSlot.objects.create(**slot_data)
            created_slots.append(slot)
    
    # If no slots were created, raise an error
    if not created_slots:
        raise ValueError(
            f"All {len(slots_to_create)} slots already exist for this time range. "
            f"No new slots were created."
        )
    
    return created_slots


def check_slot_overlap(doctor, slot_date, start_time, end_time, exclude_slot_id=None):
    """
    Check if a slot overlaps with existing slots.
    
    Args:
        doctor: Doctor instance
        slot_date: Date to check
        start_time: Start time
        end_time: End time
        exclude_slot_id: Optional slot ID to exclude from check (for updates)
    
    Returns:
        bool: True if overlap exists, False otherwise
    """
    
    queryset = DoctorSlot.objects.filter(
        doctor=doctor,
        slot_date=slot_date,
        start_time__lt=end_time,
        end_time__gt=start_time
    )
    
    if exclude_slot_id:
        queryset = queryset.exclude(id=exclude_slot_id)
    
    return queryset.exists()
