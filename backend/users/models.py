"""
User model with role-based access control.
Supports 4 roles: Admin, Staff, Doctor, Read-Only
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    Adds role field for RBAC (FR-UA-01).
    """
    
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        STAFF = 'STAFF', 'Staff'
        DOCTOR = 'DOCTOR', 'Doctor'
        READONLY = 'READONLY', 'Read-Only'
    
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STAFF,
        help_text="User role for access control"
    )
    
    # Override username to use email as the primary identifier
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    @property
    def is_admin(self):
        """Check if user has Admin role."""
        return self.role == self.Role.ADMIN
    
    @property
    def is_staff_role(self):
        """Check if user has Staff role."""
        return self.role == self.Role.STAFF
    
    @property
    def is_doctor(self):
        """Check if user has Doctor role."""
        return self.role == self.Role.DOCTOR
    
    @property
    def is_readonly(self):
        """Check if user has Read-Only role."""
        return self.role == self.Role.READONLY
