from django.shortcuts import render


def dashboard_view(request):
    """Render the main AntTipid dashboard."""
    context = {
        'active_nav': 'dashboard',
    }
    return render(request, 'dashboard/index.html', context)
