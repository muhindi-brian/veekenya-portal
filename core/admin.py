from django.contrib import admin
from .models import Child, Sponsor, Sponsorship, Donation

@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'birth_date', 'gender', 'village', 'school', 'education_level')
    search_fields = ('full_name', 'village', 'school')
    list_filter = ('gender', 'education_level')

@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'country', 'joined_date')
    search_fields = ('full_name', 'email', 'country')
    list_filter = ('country',)

@admin.register(Sponsorship)
class SponsorshipAdmin(admin.ModelAdmin):
    list_display = ('child', 'sponsor', 'start_date', 'end_date')
    search_fields = ('child__full_name', 'sponsor__full_name')
    list_filter = ('start_date', 'end_date')

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('sponsor', 'amount', 'date_received', 'purpose')
    search_fields = ('sponsor__full_name', 'purpose')
    list_filter = ('date_received',)
