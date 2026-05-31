"""
Django admin configuration for Patient model.
"""

from django.contrib import admin
from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """
    Admin interface for Patient model.
    """
    
    list_display = [
        'full_name', 'phone_number', 'date_of_birth', 'gender',
        'assigned_doctor', 'email', 'created_at', 'created_by'
    ]
    list_filter = ['gender', 'assigned_doctor', 'created_at']
    search_fields = ['full_name', 'phone_number', 'email', 'medical_notes']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Required Information', {
            'fields': ('full_name', 'phone_number', 'date_of_birth', 'gender', 'assigned_doctor'),
            'description': 'All fields marked with * are required.'
        }),
        ('Optional Information', {
            'fields': ('email', 'address', 'medical_notes', 'referring_doctor')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    class Media:
        css = {
            'all': ('admin/css/patient_admin.css',)
        }
        js = ('admin/js/patient_admin.js',)
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Customize the form to ensure all required fields have asterisks.
        """
        form = super().get_form(request, obj, **kwargs)
        
        # Ensure all required fields are marked as required and have asterisks
        required_fields = {
            'full_name': 'Full name *',
            'phone_number': 'Phone number *',
            'date_of_birth': 'Date of birth *',
            'gender': 'Gender *',
            'assigned_doctor': 'Assigned doctor *'
        }
        
        for field_name, label_with_asterisk in required_fields.items():
            if field_name in form.base_fields:
                field = form.base_fields[field_name]
                field.required = True
                field.widget.attrs['required'] = 'required'
                # Force the label with asterisk
                field.label = label_with_asterisk
        
        return form
