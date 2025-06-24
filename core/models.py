from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import json

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('staff', 'Staff'),
        ('teacher', 'Teacher'),
        ('sponsor', 'Sponsor'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_users')
    created_at = models.DateTimeField(default=timezone.now)
    modified_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    # Additional profile fields
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    bio = models.TextField(blank=True)
    
    # Account deletion request
    deletion_requested = models.DateTimeField(null=True, blank=True)
    deletion_reason = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.role}"

    class Meta:
        permissions = [
            ("can_manage_users", "Can manage system users"),
        ]

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile for every new User."""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile when the User is saved."""
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)

class Child(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    full_name = models.CharField(max_length=200)
    birth_date = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    village = models.CharField(max_length=100)
    school = models.CharField(max_length=200)
    education_level = models.CharField(max_length=100)
    health_notes = models.TextField(blank=True)
    date_added = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.full_name

class Sponsor(models.Model):
    full_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    joined_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.full_name

class Sponsorship(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='sponsorships')
    sponsor = models.ForeignKey(Sponsor, on_delete=models.CASCADE, related_name='sponsorships')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.sponsor} sponsoring {self.child}"

class Donation(models.Model):
    sponsor = models.ForeignKey(Sponsor, on_delete=models.CASCADE, related_name='donations')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_received = models.DateField()
    purpose = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.sponsor} - ${self.amount} on {self.date_received}"

    class Meta:
        ordering = ['-date_received']

class AuditLog(models.Model):
    ACTION_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('profile_update', 'Profile Update'),
        ('password_change', 'Password Change'),
        ('settings_change', 'Settings Change'),
        ('data_export', 'Data Export'),
        ('deletion_request', 'Deletion Request'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    action_detail = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, default='success')
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.user} - {self.action_type} - {self.timestamp}"

class DataAccessLog(models.Model):
    OPERATION_TYPES = [
        ('read', 'Read'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('export', 'Export'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='data_access_logs')
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES)
    data_model = models.CharField(max_length=100)  # The model being accessed
    record_id = models.CharField(max_length=100)   # ID of the record being accessed
    timestamp = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    accessed_fields = models.JSONField(default=dict)  # Fields that were accessed/modified
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.user} - {self.operation_type} - {self.data_model} - {self.timestamp}"

class ComplianceReport(models.Model):
    REPORT_TYPES = [
        ('data_access', 'Data Access Report'),
        ('user_activity', 'User Activity Report'),
        ('security', 'Security Report'),
        ('privacy', 'Privacy Compliance Report'),
    ]

    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    generated_at = models.DateTimeField(default=timezone.now)
    report_period_start = models.DateTimeField()
    report_period_end = models.DateTimeField()
    report_data = models.JSONField()
    summary = models.TextField()
    
    class Meta:
        ordering = ['-generated_at']
        
    def __str__(self):
        return f"{self.report_type} - {self.generated_at}"
