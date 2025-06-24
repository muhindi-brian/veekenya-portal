from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

class UserManagementForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES)
    is_active = forms.BooleanField(required=False, initial=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'password1', 'password2', 'is_active')

    def save(self, commit=True, created_by=None):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Update the profile that was created by the signal
            profile = user.profile
            profile.role = self.cleaned_data['role']
            profile.created_by = created_by
            profile.is_active = self.cleaned_data['is_active']
            profile.save()
        return user

class UserEditForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES)
    is_active = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['role'].initial = self.instance.profile.role
            self.fields['is_active'].initial = self.instance.profile.is_active

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            user.profile.role = self.cleaned_data['role']
            user.profile.is_active = self.cleaned_data['is_active']
            user.profile.save()
        return user 