import uuid
import colorsys
from decimal import Decimal
from datetime import date, datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Q
from django.conf import settings
from .models import (
    UserProfile,
    Account,
    Category,
    Transaction,
    Receipt,
    ReceiptItem,
    Budget,
    RecurringRule,
)


def generate_dynamic_color(index):
    """Dynamically generate distinct, visually appealing hex colors using golden-ratio HSL distribution."""
    golden_ratio_conjugate = 0.618033988749895
    hue = (index * golden_ratio_conjugate) % 1.0
    r, g, b = colorsys.hls_to_rgb(hue, 0.45, 0.68)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def get_current_user_profile(request):
    """
    Retrieve or create the UserProfile for the current authenticated Clerk user,
    or fallback to dev preview user in DEBUG mode.
    """
    clerk_id = getattr(request, 'clerk_user_id', None)
    if not clerk_id:
        if settings.DEBUG:
            clerk_id = 'user_dev_preview_default'
        else:
            return None

    profile, created = UserProfile.objects.get_or_create(
        clerk_user_id=clerk_id,
        defaults={
            'first_name': '',
            'last_name': '',
            'email': '',
            'monthly_income_target': Decimal('0.00'),
        }
    )

    # Seed default accounts and categories if this is a newly created or empty user
    if created or not profile.accounts.exists():
        seed_default_user_data(profile)

    return profile


def seed_default_user_data(profile):
    """
    Populate a user with starter Accounts / Payment Methods (Cash, GCash).
    Categories and Budgets start 100% empty so the user can create their own.
    """
    # Default starter payment sources
    Account.objects.create(
        user=profile,
        name='Cash',
        account_type=Account.AccountType.CASH,
        institution_name='Cash',
        color_hex='#163300',
        icon='payments',
    )
    Account.objects.create(
        user=profile,
        name='GCash',
        account_type=Account.AccountType.E_WALLET,
        institution_name='GCash',
        color_hex='#005CEE',
        icon='account_balance_wallet',
    )


def get_dashboard_data(profile):
    """
    Calculate dynamic financial statistics and aggregated views for the main Dashboard.
    Optimized to eliminate N+1 queries by combining aggregates and performing GROUP BY operations.
    """
    today = date.today()
    start_of_month = today.replace(day=1)
    if today.month == 12:
        end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

    # 1. Combined Total Income & Total Expenses in a single query
    month_txs = Transaction.objects.filter(
        user=profile,
        transaction_date__gte=start_of_month,
        transaction_date__lte=end_of_month,
    )

    totals = month_txs.aggregate(
        total_income=Sum('amount', filter=Q(transaction_type=Transaction.TransactionType.INCOME)),
        total_expenses=Sum('amount', filter=Q(transaction_type=Transaction.TransactionType.EXPENSE))
    )
    total_income = totals['total_income'] or Decimal('0.00')
    total_expenses = totals['total_expenses'] or Decimal('0.00')
    net_cash_flow = total_income - total_expenses

    # Saved percentage of income
    saved_percent = 0
    if total_income > 0:
        saved_percent = max(0, int(((total_income - total_expenses) / total_income) * 100))

    # 2. Monthly Budget stats
    overall_budget = Budget.objects.filter(user=profile, category=None, is_active=True).first()
    has_custom_overall = bool(overall_budget and overall_budget.amount_limit > 0)
    if has_custom_overall:
        budget_limit = overall_budget.amount_limit
    else:
        # Fallback to total sum of category budget limits
        cat_sum = Budget.objects.filter(user=profile, is_active=True).exclude(category=None).aggregate(sum=Sum('amount_limit'))['sum'] or Decimal('0.00')
        budget_limit = cat_sum

    budget_percent = 0
    if budget_limit > 0:
        budget_percent = min(100, int((total_expenses / budget_limit) * 100))
    budget_left = max(Decimal('0.00'), budget_limit - total_expenses)
    budget_on_track = (total_expenses <= budget_limit) if budget_limit > 0 else True

    # 3. Category Spending Breakdown for Month (Single DB GROUP BY Query)
    category_breakdown = []
    if total_expenses > 0:
        cat_sums = month_txs.filter(
            transaction_type=Transaction.TransactionType.EXPENSE,
            category__isnull=False
        ).values(
            'category_id',
            'category__name',
            'category__icon_name',
            'category__color_hex'
        ).annotate(
            spent=Sum('amount')
        ).order_by('-spent')

        for item in cat_sums:
            cat_spent = item['spent'] or Decimal('0.00')
            pct = int((cat_spent / total_expenses * 100))
            category_breakdown.append({
                'id': str(item['category_id']),
                'name': item['category__name'],
                'icon': item['category__icon_name'] or 'category',
                'color': item['category__color_hex'] or '#5C8F3A',
                'spent': cat_spent,
                'percentage': pct,
            })

    # 4. Weekly Spending Breakdown for this Month (Weeks 1 to 4) - Single in-memory aggregate pass over month_txs
    expense_tx_dates = list(month_txs.filter(
        transaction_type=Transaction.TransactionType.EXPENSE
    ).values('transaction_date', 'amount'))

    weekly_totals = [Decimal('0.00')] * 4
    for tx in expense_tx_dates:
        tx_date = tx['transaction_date']
        amt = tx['amount']
        day_offset = (tx_date - start_of_month).days
        w_idx = min(3, max(0, day_offset // 7))
        weekly_totals[w_idx] += amt

    weekly_spending = []
    for w in range(4):
        w_spent = weekly_totals[w]
        weekly_spending.append({
            'week_label': f"W{w + 1}",
            'amount': w_spent,
            'amount_k': f"₱{w_spent / 1000:.1f}k" if w_spent >= 1000 else f"₱{w_spent:,.0f}",
        })

    max_w_amount = max([w['amount'] for w in weekly_spending] + [Decimal('0')])
    for w in weekly_spending:
        w['height_pct'] = int((w['amount'] / max_w_amount) * 100) if max_w_amount > 0 else 0

    # 5. Recent 5 Transactions
    recent_transactions = Transaction.objects.filter(user=profile).select_related('account', 'category', 'receipt').order_by('-transaction_date', '-created_at')[:5]

    return {
        'net_cash_flow': net_cash_flow,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'saved_percent': saved_percent,
        'budget_limit': budget_limit,
        'budget_spent': total_expenses,
        'budget_left': budget_left,
        'budget_percent': budget_percent,
        'budget_on_track': budget_on_track,
        'has_custom_overall': has_custom_overall,
        'category_breakdown': category_breakdown[:5],
        'weekly_spending': weekly_spending,
        'recent_transactions': recent_transactions,
        'current_month_name': today.strftime('%b %Y'),
    }


def get_transactions_data(profile, filters=None):
    """
    Fetch filtered transactions and receipts for the Transactions View.
    Optimized to load query results once into memory to eliminate redundant SQL COUNT and evaluation calls.
    """
    filters = filters or {}
    qs = Transaction.objects.filter(user=profile).select_related('account', 'destination_account', 'category', 'receipt').order_by('-transaction_date', '-created_at')

    # Filter by search query
    query = filters.get('q', '').strip()
    if query:
        qs = qs.filter(Q(title__icontains=query) | Q(notes__icontains=query) | Q(category__name__icontains=query) | Q(account__name__icontains=query))

    # Filter by transaction type
    tx_type = filters.get('type', '').strip().upper()
    if tx_type in ('EXPENSE', 'INCOME', 'TRANSFER'):
        qs = qs.filter(transaction_type=tx_type)

    # Filter by category
    cat_id = filters.get('category', '').strip()
    if cat_id:
        qs = qs.filter(category_id=cat_id)

    # Filter by account
    acc_id = filters.get('account', '').strip()
    if acc_id:
        qs = qs.filter(Q(account_id=acc_id) | Q(destination_account_id=acc_id))

    # Filter by source (manual vs receipt)
    source = filters.get('source', '').strip().upper()
    if source in ('MANUAL', 'OCR_SCAN', 'RECURRING'):
        qs = qs.filter(source=source)

    # Fetch list once into memory
    transactions_list = list(qs)
    total_count = len(transactions_list)

    # Group transactions by date for mobile view
    today = date.today()
    yesterday = today - timedelta(days=1)

    grouped_mobile = {}
    for tx in transactions_list:
        t_date = tx.transaction_date
        if t_date == today:
            group_key = f"Today • {t_date.strftime('%b %d, %Y')}"
        elif t_date == yesterday:
            group_key = f"Yesterday • {t_date.strftime('%b %d, %Y')}"
        else:
            group_key = t_date.strftime('%A • %b %d, %Y')

        if group_key not in grouped_mobile:
            grouped_mobile[group_key] = []
        grouped_mobile[group_key].append(tx)

    user_categories = Category.objects.filter(user=profile).order_by('name')
    user_accounts = Account.objects.filter(user=profile, is_active=True).order_by('name')
    user_receipts = Receipt.objects.filter(user=profile).prefetch_related('items').order_by('-receipt_date', '-created_at')

    return {
        'transactions': transactions_list,
        'grouped_mobile': grouped_mobile,
        'receipts': user_receipts,
        'categories': user_categories,
        'accounts': user_accounts,
        'total_count': total_count,
    }


def get_budget_data(profile, selected_month=None):
    """
    Calculate dynamic category budgets and progress for the Budget Page for the selected month.
    Optimized with single-query category aggregate mapping to eliminate N+1 queries.
    """
    today = date.today()
    today_start_of_month = today.replace(day=1)

    target_date = today
    if selected_month:
        try:
            target_date = datetime.strptime(str(selected_month).strip(), '%Y-%m').date()
        except Exception:
            target_date = today

    start_of_month = target_date.replace(day=1)
    if target_date.month == 12:
        end_of_month = target_date.replace(year=target_date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_of_month = target_date.replace(month=target_date.month + 1, day=1) - timedelta(days=1)

    is_current_month = (start_of_month >= today_start_of_month)
    next_month_date = (start_of_month + timedelta(days=32)).replace(day=1)
    prev_month_date = (start_of_month - timedelta(days=1)).replace(day=1)

    has_next_month = (next_month_date <= today_start_of_month)
    next_month_str = next_month_date.strftime('%Y-%m')
    prev_month_str = prev_month_date.strftime('%Y-%m')

    earliest_tx = Transaction.objects.filter(user=profile).order_by('transaction_date').first()
    if earliest_tx and earliest_tx.transaction_date:
        earliest_month = earliest_tx.transaction_date.replace(day=1)
        has_prev_month = (start_of_month > earliest_month)
    else:
        has_prev_month = (start_of_month > (today_start_of_month - timedelta(days=90)).replace(day=1))

    budgets = list(Budget.objects.filter(user=profile, is_active=True).select_related('category'))
    overall_budget = next((b for b in budgets if b.category_id is None), None)
    category_budgets = [b for b in budgets if b.category_id is not None]

    expense_txs = Transaction.objects.filter(
        user=profile,
        transaction_type=Transaction.TransactionType.EXPENSE,
        transaction_date__gte=start_of_month,
        transaction_date__lte=end_of_month,
    )

    total_spent = expense_txs.aggregate(sum=Sum('amount'))['sum'] or Decimal('0.00')

    # Build category spent map in a single GROUP BY query
    cat_spent_map = dict(
        expense_txs.filter(category__isnull=False)
        .values('category_id')
        .annotate(spent=Sum('amount'))
        .values_list('category_id', 'spent')
    )

    has_custom_overall = bool(overall_budget and overall_budget.amount_limit > 0)
    if has_custom_overall:
        overall_limit = overall_budget.amount_limit
    else:
        overall_limit = sum(b.amount_limit for b in category_budgets)

    if overall_limit > 0:
        actual_pct_val = float((total_spent / overall_limit) * 100)
        overall_pct = min(100, int(actual_pct_val))
    else:
        actual_pct_val = 0.0
        overall_pct = 0

    overall_left = max(Decimal('0.00'), overall_limit - total_spent)
    is_over_limit = (total_spent > overall_limit) if overall_limit > 0 else False
    is_warning_limit = (actual_pct_val >= 80) and not is_over_limit and (overall_limit > 0)

    if overall_limit == 0:
        overall_status_label = 'No Limit Set'
        overall_status_color = 'neutral'
        overall_stroke_color = '#94A3B8'
        overall_badge_bg = 'bg-slate-100 text-slate-700 border-slate-300'
        overall_badge_text = 'text-slate-700'
    elif is_over_limit:
        overall_status_label = 'Over Budget'
        overall_status_color = 'expense'
        overall_stroke_color = '#EF4444'
        overall_badge_bg = 'bg-expense/15 text-expense border-expense/30'
        overall_badge_text = 'text-expense'
    elif is_warning_limit:
        overall_status_label = 'Nearing Limit'
        overall_status_color = 'warning'
        overall_stroke_color = '#F59E0B'
        overall_badge_bg = 'bg-warning/20 text-warning-deep border-warning/40'
        overall_badge_text = 'text-warning-deep'
    else:
        overall_status_label = 'On Track'
        overall_status_color = 'positive'
        overall_stroke_color = '#10B981'
        overall_badge_bg = 'bg-primary-pale text-positive-deep border-positive/30'
        overall_badge_text = 'text-positive-deep'

    capped_pct = min(100.0, actual_pct_val)
    overall_dashoffset = max(0.0, 238.76 - (238.76 * capped_pct / 100.0))

    budget_cards = []
    for b in category_budgets:
        cat_spent = cat_spent_map.get(b.category_id, Decimal('0.00'))
        pct = min(100, int((cat_spent / b.amount_limit) * 100)) if b.amount_limit > 0 else 0
        left = b.amount_limit - cat_spent
        is_over = cat_spent > b.amount_limit
        is_warning = pct >= b.warning_threshold_pct and not is_over

        if is_over:
            status_label = 'Over Budget'
            status_color = 'negative'
        elif is_warning:
            status_label = 'Nearing Limit'
            status_color = 'warning'
        else:
            status_label = 'On Track'
            status_color = 'positive'

        budget_cards.append({
            'id': str(b.id),
            'name': b.category.name if b.category else b.name,
            'category_name': b.category.name if b.category else 'General',
            'category_id': str(b.category.id) if b.category else '',
            'icon_name': b.category.icon_name if b.category else 'category',
            'icon': b.category.icon_name if b.category else 'category',
            'color': b.category.color_hex if b.category else '#5C8F3A',
            'limit': b.amount_limit,
            'spent': cat_spent,
            'left': abs(left),
            'percentage': pct,
            'is_over': is_over,
            'is_exceeded': is_over,
            'is_warning': is_warning,
            'is_unbudgeted': False,
            'status_label': status_label,
            'status_color': status_color,
        })

    budgeted_cat_ids = set(b.category_id for b in category_budgets if b.category_id)
    unbudgeted_categories = Category.objects.filter(user=profile, category_type=Category.CategoryType.EXPENSE).exclude(id__in=budgeted_cat_ids)

    for cat in unbudgeted_categories:
        cat_spent = cat_spent_map.get(cat.id, Decimal('0.00'))
        budget_cards.append({
            'id': f"unbudgeted-{cat.id}",
            'name': cat.name,
            'category_name': cat.name,
            'category_id': str(cat.id),
            'icon_name': cat.icon_name or 'category',
            'icon': cat.icon_name or 'category',
            'color': cat.color_hex or '#5C8F3A',
            'limit': None,
            'spent': cat_spent,
            'left': Decimal('0.00'),
            'percentage': 0,
            'is_over': False,
            'is_exceeded': False,
            'is_warning': False,
            'is_unbudgeted': True,
            'status_label': 'Tracking Only (No Limit)',
            'status_color': 'neutral',
        })

    exceeded_count = sum(1 for c in budget_cards if c['is_exceeded'])
    warning_count = sum(1 for c in budget_cards if c['is_warning'])

    categories = Category.objects.filter(user=profile, category_type=Category.CategoryType.EXPENSE).order_by('name')

    return {
        'overall_limit': overall_limit,
        'total_limit': overall_limit,
        'overall_spent': total_spent,
        'total_spent': total_spent,
        'overall_left': overall_left,
        'overall_remaining': overall_left,
        'overall_pct': overall_pct,
        'overall_percentage': overall_pct,
        'overall_dashoffset': f"{overall_dashoffset:.1f}",
        'overall_stroke_color': overall_stroke_color,
        'overall_status_label': overall_status_label,
        'overall_badge_bg': overall_badge_bg,
        'overall_badge_text': overall_badge_text,
        'has_custom_overall': has_custom_overall,
        'is_over_limit': is_over_limit,
        'is_warning_limit': is_warning_limit,
        'exceeded_count': exceeded_count,
        'warning_count': warning_count,
        'budget_cards': budget_cards,
        'categories': categories,
        'current_month_label': target_date.strftime('%B %Y'),
        'current_month_str': target_date.strftime('%Y-%m'),
        'is_current_month': is_current_month,
        'has_next_month': has_next_month,
        'has_prev_month': has_prev_month,
        'next_month_str': next_month_str,
        'prev_month_str': prev_month_str,
    }


def get_reports_data(profile):
    """
    Compute 100% dynamic statistics for Reports (week, month, year) strictly from database Transaction records.
    Optimized with single-pass in-memory processing to eliminate 100+ redundant SQL queries.
    """
    if not profile:
        return {}

    today = date.today()

    def get_period_stats(cols, col_ranges, period_start, period_end, prev_start, prev_end, period_label):
        # Fetch period transactions once into memory
        period_txs_list = list(Transaction.objects.filter(
            user=profile,
            transaction_date__gte=period_start,
            transaction_date__lte=period_end,
        ).values('transaction_date', 'transaction_type', 'amount', 'category_id', 'category__name', 'category__icon_name', 'category__color_hex'))

        total_exp = sum(float(tx['amount']) for tx in period_txs_list if tx['transaction_type'] == Transaction.TransactionType.EXPENSE)
        total_inc = sum(float(tx['amount']) for tx in period_txs_list if tx['transaction_type'] == Transaction.TransactionType.INCOME)

        # Previous period comparison (1 DB query)
        prev_exp = float(Transaction.objects.filter(
            user=profile,
            transaction_date__gte=prev_start,
            transaction_date__lte=prev_end,
            transaction_type=Transaction.TransactionType.EXPENSE,
        ).aggregate(s=Sum('amount'))['s'] or 0)

        if prev_exp > 0:
            pct_diff = ((total_exp - prev_exp) / prev_exp) * 100
            diff_sign = '+' if pct_diff > 0 else ''
            spending_change = f"{diff_sign}{pct_diff:.1f}% vs previous period"
        elif total_exp > 0:
            spending_change = "+100% vs previous period"
        else:
            spending_change = "0% vs previous period"

        # Savings Rate
        if total_inc > 0:
            raw_savings = max(0.0, ((total_inc - total_exp) / total_inc) * 100)
            savings_str = f"{raw_savings:.1f}%"
            savings_bar = f"{min(100, int(raw_savings))}%"
        else:
            savings_str = "0.0%"
            savings_bar = "0%"

        # Column breakdown (In-memory pass over period_txs_list)
        exp_vals = []
        inc_vals = []
        for r_start, r_end in col_ranges:
            e = sum(float(tx['amount']) for tx in period_txs_list if tx['transaction_type'] == Transaction.TransactionType.EXPENSE and r_start <= tx['transaction_date'] <= r_end)
            i = sum(float(tx['amount']) for tx in period_txs_list if tx['transaction_type'] == Transaction.TransactionType.INCOME and r_start <= tx['transaction_date'] <= r_end)
            exp_vals.append(e)
            inc_vals.append(i)

        max_bar = max(exp_vals + inc_vals + [1.0])
        exp_heights = [int((v / max_bar) * 100) if v > 0 else 0 for v in exp_vals]
        inc_heights = [int((v / max_bar) * 100) if v > 0 else 0 for v in inc_vals]

        # Y-axis ticks
        if total_exp == 0 and total_inc == 0:
            y_ticks = ["₱0", "₱0", "₱0", "₱0"]
        else:
            y_step = max_bar / 3.0
            y_ticks = [
                f"₱{max_bar:,.0f}" if max_bar < 1000 else f"₱{max_bar/1000:,.1f}k",
                f"₱{y_step*2:,.0f}" if y_step*2 < 1000 else f"₱{(y_step*2)/1000:,.1f}k",
                f"₱{y_step:,.0f}" if y_step < 1000 else f"₱{y_step/1000:,.1f}k",
                "₱0"
            ]

        # Category Donut Distribution (In-memory aggregation)
        cat_spending_map = {}
        cat_info_map = {}
        uncat_sum = 0.0

        for tx in period_txs_list:
            if tx['transaction_type'] == Transaction.TransactionType.EXPENSE:
                cat_id = tx['category_id']
                amt = float(tx['amount'])
                if cat_id:
                    cat_spending_map[cat_id] = cat_spending_map.get(cat_id, 0.0) + amt
                    if cat_id not in cat_info_map:
                        cat_info_map[cat_id] = {
                            'name': tx['category__name'],
                            'icon': tx['category__icon_name'] or 'category',
                            'color': tx['category__color_hex'] or '#163300',
                        }
                else:
                    uncat_sum += amt

        donut = []
        for cat_id, c_sum in cat_spending_map.items():
            if c_sum > 0:
                info = cat_info_map[cat_id]
                donut.append({
                    'id': cat_id,
                    'name': info['name'],
                    'color': info['color'],
                    'icon': info['icon'],
                    'value': c_sum,
                    'percentage': round((c_sum / total_exp * 100), 1) if total_exp > 0 else 0,
                    'amount': f"₱{c_sum:,.2f}"
                })

        if uncat_sum > 0:
            donut.append({
                'id': None,
                'name': 'Uncategorized',
                'color': '#868685',
                'icon': 'category',
                'value': uncat_sum,
                'percentage': round((uncat_sum / total_exp * 100), 1) if total_exp > 0 else 0,
                'amount': f"₱{uncat_sum:,.2f}"
            })

        donut.sort(key=lambda x: x['value'], reverse=True)

        used_colors = set()
        for idx, d in enumerate(donut):
            if d['name'] == 'Uncategorized':
                d['color'] = '#868685'
            else:
                c = d.get('color')
                if not c or c in used_colors or (c in ('#163300', '#5C8F3A') and len(donut) > 1):
                    c = generate_dynamic_color(idx)
                d['color'] = c
                used_colors.add(c)

        donut_color_map = {d['name']: d['color'] for d in donut}

        # Top Category KPI
        if donut:
            top_cat = donut[0]
            top_cat_name = top_cat['name']
            top_cat_icon = top_cat.get('icon', 'category')
            top_cat_amount = top_cat['amount']
            top_cat_percent = f"{top_cat['percentage']}% of total"
        else:
            top_cat_name = "—"
            top_cat_icon = "category"
            top_cat_amount = "₱0.00"
            top_cat_percent = "0% of total"

        # Multi-category Trends (Top 4 categories by spend computed in memory)
        trend_categories = []
        top_cats = donut[:4]

        for idx, cat_item in enumerate(top_cats):
            cat_id = cat_item.get('id')
            cat_name = cat_item['name']
            cat_vals = []
            for r_start, r_end in col_ranges:
                if cat_id is not None:
                    c_val = sum(float(tx['amount']) for tx in period_txs_list if tx['category_id'] == cat_id and tx['transaction_type'] == Transaction.TransactionType.EXPENSE and r_start <= tx['transaction_date'] <= r_end)
                else:
                    c_val = sum(float(tx['amount']) for tx in period_txs_list if tx['category_id'] is None and tx['transaction_type'] == Transaction.TransactionType.EXPENSE and r_start <= tx['transaction_date'] <= r_end)
                cat_vals.append(c_val)
            
            c_tot = sum(cat_vals)
            cat_color = cat_item['color']
            trend_categories.append({
                'name': cat_name,
                'icon': cat_item.get('icon', 'category'),
                'color': cat_color,
                'gradId': f"grad-trend-{idx}",
                'values': cat_vals,
                'formattedValues': [f"₱{v:,.0f}" for v in cat_vals],
                'total': f"₱{c_tot:,.2f}",
                'percentage': int((c_tot / total_exp * 100)) if total_exp > 0 else 0,
                'isExpenseUp': True,
                'iconBg': f"bg-surface-container text-deep-forest"
            })

        # Trend Max Y and Y-Ticks
        trend_all_vals = [v for tc in trend_categories for v in tc['values']]
        max_trend_y = max(trend_all_vals + [1.0])
        if total_exp == 0 or not trend_all_vals or max_trend_y <= 1.0:
            max_trend_y = 1.0
            trend_y_ticks = ["₱0", "₱0", "₱0", "₱0"]
        else:
            trend_step = max_trend_y / 3.0
            trend_y_ticks = [
                f"₱{max_trend_y:,.0f}" if max_trend_y < 1000 else f"₱{max_trend_y/1000:,.1f}k",
                f"₱{trend_step*2:,.0f}" if trend_step*2 < 1000 else f"₱{(trend_step*2)/1000:,.1f}k",
                f"₱{trend_step:,.0f}" if trend_step < 1000 else f"₱{trend_step/1000:,.1f}k",
                "₱0"
            ]

        # Dynamic Insights
        insights = {
            'all': f"Total spending for {period_label} is ₱{total_exp:,.2f} with ₱{total_inc:,.2f} income recorded." if total_exp > 0 or total_inc > 0 else f"No spending recorded for {period_label} yet."
        }
        for idx, tc in enumerate(trend_categories):
            insights[idx] = f"{tc['name']} total spend is {tc['total']} ({tc['percentage']}% of {period_label})."

        return {
            'spending': f"₱{total_exp:,.2f}",
            'total': f"₱{total_exp:,.2f}",
            'spendingChange': spending_change,
            'totalSub': spending_change,
            'topCatName': top_cat_name,
            'topCatIcon': top_cat_icon,
            'topCatAmount': top_cat_amount,
            'topCatPercent': top_cat_percent,
            'highest': top_cat_name,
            'highestIcon': top_cat_icon,
            'highestSub': f"{top_cat_amount} ({top_cat_percent})",
            'savings': savings_str,
            'savingsBar': savings_bar,
            'chartSubtext': f"Breakdown for {period_label}",
            'cols': cols,
            'yTicks': y_ticks,
            'expHeights': exp_heights,
            'incHeights': inc_heights,
            'expVals': [f"₱{v:,.0f}" for v in exp_vals],
            'incVals': [f"₱{v:,.0f}" for v in inc_vals],
            'donutTotal': f"₱{total_exp:,.2f}",
            'donutPeriod': period_label,
            'donut': donut,
            'categories': [{'name': d['name'], 'pct': d['percentage'], 'amount': d['amount'], 'color': d['color'], 'value': d['value']} for d in donut],
            'trendPeriod': period_label,
            'trendSubtext': f"Spending trajectory for {period_label}",
            'trendYTicks': trend_y_ticks,
            'trendMaxY': max_trend_y,
            'trendCategories': trend_categories,
            'insights': insights,
        }

    # 1. Week (Sun to Sat)
    idx_sun = (today.weekday() + 1) % 7
    week_start = today - timedelta(days=idx_sun)
    week_end = week_start + timedelta(days=6)
    prev_week_start = week_start - timedelta(days=7)
    prev_week_end = week_start - timedelta(days=1)
    week_cols = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    week_ranges = [(week_start + timedelta(days=d), week_start + timedelta(days=d)) for d in range(7)]

    # 2. Month (Weeks 1 to 4)
    month_start = today.replace(day=1)
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    
    month_cols = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
    month_ranges = [
        (month_start, month_start + timedelta(days=6)),
        (month_start + timedelta(days=7), month_start + timedelta(days=13)),
        (month_start + timedelta(days=14), month_start + timedelta(days=20)),
        (month_start + timedelta(days=21), month_end),
    ]

    # 3. Year (Q1, Q2, Q3, Q4)
    year_start = date(today.year, 1, 1)
    year_end = date(today.year, 12, 31)
    prev_year_start = date(today.year - 1, 1, 1)
    prev_year_end = date(today.year - 1, 12, 31)
    year_cols = ['Q1', 'Q2', 'Q3', 'Q4']
    year_ranges = [
        (date(today.year, 1, 1), date(today.year, 3, 31)),
        (date(today.year, 4, 1), date(today.year, 6, 30)),
        (date(today.year, 7, 1), date(today.year, 9, 30)),
        (date(today.year, 10, 1), date(today.year, 12, 31)),
    ]

    return {
        'week': get_period_stats(week_cols, week_ranges, week_start, week_end, prev_week_start, prev_week_end, 'This Week'),
        'month': get_period_stats(month_cols, month_ranges, month_start, month_end, prev_month_start, prev_month_end, today.strftime('%B %Y')),
        'year': get_period_stats(year_cols, year_ranges, year_start, year_end, prev_year_start, prev_year_end, f"{today.year} Year"),
    }
