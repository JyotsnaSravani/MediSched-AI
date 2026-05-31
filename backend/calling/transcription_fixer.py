"""
Transcription Fixer - Post-process transcriptions to fix common speech recognition errors
"""

import re
from typing import Dict, List


class TranscriptionFixer:
    """
    Fix common speech recognition errors in transcriptions.
    Corrects patient names, doctor names, company name, and times.
    """
    
    # Common misheard company names
    COMPANY_NAME_FIXES = {
        'mediscan': 'MediSched',
        'medi scan': 'MediSched',
        'medi-scan': 'MediSched',
        'medisked': 'MediSched',
        'medi sked': 'MediSched',
        'medi-sked': 'MediSched',
        'medicare': 'MediSched',
        'mediscale': 'MediSched',
        'mediscope': 'MediSched',
    }
    
    # Common doctor name prefixes that get misheard
    DOCTOR_PREFIX_FIXES = {
        'dr ': 'Dr. ',
        'dr.': 'Dr. ',
        'doctor ': 'Dr. ',
    }
    
    def __init__(self, patient_name: str = None, doctor_name: str = None):
        """
        Initialize fixer with patient and doctor names for context-aware fixing.
        
        Args:
            patient_name: Full patient name (e.g., "Teja")
            doctor_name: Full doctor name (e.g., "David Kim")
        """
        self.patient_name = patient_name
        self.doctor_name = doctor_name
        
        # Build patient name variations for fuzzy matching
        self.patient_variations = self._build_name_variations(patient_name) if patient_name else []
        
        # Build doctor name variations
        self.doctor_variations = self._build_name_variations(doctor_name) if doctor_name else []
        self.doctor_last_name = doctor_name.split()[-1] if doctor_name else None
    
    def _build_name_variations(self, name: str) -> List[str]:
        """
        Build common misheard variations of a name.
        
        Examples:
            "Teja" -> ["teha", "taja", "teja", "tejah"]
            "Kim" -> ["kim", "kem", "kym"]
        """
        if not name:
            return []
        
        variations = [name.lower()]
        
        # Common vowel substitutions
        vowel_subs = {
            'a': ['e', 'ah'],
            'e': ['a', 'eh'],
            'i': ['e', 'y'],
            'o': ['u', 'oh'],
            'u': ['o', 'oo'],
        }
        
        for char, subs in vowel_subs.items():
            if char in name.lower():
                for sub in subs:
                    variations.append(name.lower().replace(char, sub))
        
        # Add version with 'h' at end (common mishearing)
        variations.append(name.lower() + 'h')
        
        return list(set(variations))
    
    def fix_company_name(self, text: str) -> str:
        """Fix company name in transcription."""
        text_lower = text.lower()
        
        for wrong, correct in self.COMPANY_NAME_FIXES.items():
            # Case-insensitive replacement
            pattern = re.compile(re.escape(wrong), re.IGNORECASE)
            text = pattern.sub(correct, text)
        
        return text
    
    def fix_patient_name(self, text: str) -> str:
        """Fix patient name in transcription using fuzzy matching."""
        if not self.patient_name or not self.patient_variations:
            return text
        
        text_lower = text.lower()
        
        # Check if any variation appears in text
        for variation in self.patient_variations:
            if variation in text_lower:
                # Replace with correct name (case-insensitive)
                pattern = re.compile(r'\b' + re.escape(variation) + r'\b', re.IGNORECASE)
                text = pattern.sub(self.patient_name, text)
                break
        
        return text
    
    def fix_doctor_name(self, text: str) -> str:
        """Fix doctor name in transcription."""
        if not self.doctor_name:
            return text
        
        # Fix doctor prefix first
        text_lower = text.lower()
        for wrong, correct in self.DOCTOR_PREFIX_FIXES.items():
            text = re.sub(r'\b' + re.escape(wrong), correct, text, flags=re.IGNORECASE)
        
        # Fix doctor last name using variations
        if self.doctor_last_name:
            doctor_variations = self._build_name_variations(self.doctor_last_name)
            
            for variation in doctor_variations:
                if variation in text_lower:
                    # Replace with correct last name
                    pattern = re.compile(r'\b' + re.escape(variation) + r'\b', re.IGNORECASE)
                    text = pattern.sub(self.doctor_last_name, text)
                    break
        
        return text
    
    def fix_time_format(self, text: str) -> str:
        """
        Fix time format in transcription.
        Converts "02:01 AM" to "2:01 AM" (remove leading zero)
        Converts "9 AM" to "9:00 AM" (add minutes if missing)
        """
        # Fix leading zeros in hours (02:01 AM -> 2:01 AM)
        text = re.sub(r'\b0(\d):(\d{2})\s*(AM|PM|am|pm)', r'\1:\2 \3', text)
        
        # Add :00 to times without minutes (9 AM -> 9:00 AM)
        text = re.sub(r'\b(\d{1,2})\s+(AM|PM|am|pm)\b', r'\1:00 \2', text)
        
        # Standardize AM/PM to uppercase
        text = re.sub(r'\b(\d{1,2}):(\d{2})\s*am\b', r'\1:\2 AM', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(\d{1,2}):(\d{2})\s*pm\b', r'\1:\2 PM', text, flags=re.IGNORECASE)
        
        return text
    
    def fix_all(self, text: str) -> str:
        """
        Apply all fixes to transcription text.
        
        Args:
            text: Original transcription text
            
        Returns:
            Fixed transcription text
        """
        if not text:
            return text
        
        # Apply fixes in order
        text = self.fix_company_name(text)
        text = self.fix_patient_name(text)
        text = self.fix_doctor_name(text)
        text = self.fix_time_format(text)
        
        return text


def fix_transcription(text: str, patient_name: str = None, doctor_name: str = None) -> str:
    """
    Convenience function to fix transcription text.
    
    Args:
        text: Original transcription text
        patient_name: Patient's full name for context
        doctor_name: Doctor's full name for context
        
    Returns:
        Fixed transcription text
    """
    fixer = TranscriptionFixer(patient_name=patient_name, doctor_name=doctor_name)
    return fixer.fix_all(text)
