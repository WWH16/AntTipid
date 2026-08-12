from django.conf import settings


def clerk_settings(request):
    """Expose Clerk publishable key to all Django templates."""
    return {
        'clerk_publishable_key': getattr(settings, 'CLERK_PUBLISHABLE_KEY', ''),
    }
