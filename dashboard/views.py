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


def budget_view(request):
    """Render the budget view."""
    context = {
        'active_nav': 'budgets',
    }
    return render(request, 'dashboard/budget.html', context)


def reports_view(request):
    """Render the financial reports and insights view."""
    context = {
        'active_nav': 'reports',
    }
    return render(request, 'dashboard/reports.html', context)
