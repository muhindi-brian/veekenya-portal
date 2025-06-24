from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile

class Command(BaseCommand):
    help = 'Creates UserProfile objects for users that do not have them'

    def handle(self, *args, **options):
        users_without_profile = []
        for user in User.objects.all():
            try:
                # Try to access the profile
                user.profile
            except UserProfile.DoesNotExist:
                # Create profile if it doesn't exist
                UserProfile.objects.create(user=user)
                users_without_profile.append(user.username)
        
        if users_without_profile:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created profiles for users: {", ".join(users_without_profile)}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('All users already have profiles')
            ) 