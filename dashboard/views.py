from django.shortcuts import render


def dashboard_view(request):
    """Render the main AntTipid dashboard."""
    context = {
        'active_nav': 'dashboard',
    }
    return render(request, 'dashboard/index.html', context)


def transactions_view(request):
    """Render the transactions history view."""
    context = {
        'active_nav': 'transactions',
    }
    return render(request, 'dashboard/transactions.html', context)
