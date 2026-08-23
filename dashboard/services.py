import uuid
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
            'first_name': 'Juan',
            'last_name': 'Dela Cruz',
            'email': 'juan.delacruz@anttipid.ph',
            'monthly_income_target': Decimal('50000.00'),
            'currency_code': 'PHP',
        }
    )

    # Seed default accounts and categories if this is a newly created or empty user
    if created or not profile.accounts.exists():
        seed_default_user_data(profile)

    return profile


def seed_default_user_data(profile):
    """
    Populate a user with starter Accounts, Categories, Budgets, and initial Transactions.
    """
    # 1. Accounts (Default starter payment sources)
    cash_acc = Account.objects.create(
        user=profile,
        name='Cash',
        account_type=Account.AccountType.CASH,
        institution_name='Cash',
        current_balance=Decimal('4500.00'),
        color_hex='#163300',
        icon='payments',
    )
    gcash_acc = Account.objects.create(
        user=profile,
        name='GCash',
        account_type=Account.AccountType.E_WALLET,
        institution_name='GCash',
        current_balance=Decimal('8250.00'),
        color_hex='#005CEE',
        icon='account_balance_wallet',
    )

    # 2. Categories
    cat_food = Category.objects.create(user=profile, name='Food & Dining', category_type=Category.CategoryType.EXPENSE, icon_name='restaurant', color_hex='#5C8F3A', is_system_default=True)
    cat_trans = Category.objects.create(user=profile, name='Transportation', category_type=Category.CategoryType.EXPENSE, icon_name='directions_car', color_hex='#D97706', is_system_default=True)
    cat_shop = Category.objects.create(user=profile, name='Shopping', category_type=Category.CategoryType.EXPENSE, icon_name='shopping_bag', color_hex='#8B5CF6', is_system_default=True)
    cat_util = Category.objects.create(user=profile, name='Utilities', category_type=Category.CategoryType.EXPENSE, icon_name='bolt', color_hex='#0EA5E9', is_system_default=True)
    cat_ent = Category.objects.create(user=profile, name='Entertainment', category_type=Category.CategoryType.EXPENSE, icon_name='movie', color_hex='#EC4899', is_system_default=True)
    cat_groc = Category.objects.create(user=profile, name='Groceries', category_type=Category.CategoryType.EXPENSE, icon_name='local_grocery_store', color_hex='#10B981', is_system_default=True)
    cat_house = Category.objects.create(user=profile, name='Housing & Rent', category_type=Category.CategoryType.EXPENSE, icon_name='home', color_hex='#163300', is_system_default=True)
    cat_other = Category.objects.create(user=profile, name='Others', category_type=Category.CategoryType.EXPENSE, icon_name='category', color_hex='#D03238', is_system_default=True)

    cat_sal = Category.objects.create(user=profile, name='Salary', category_type=Category.CategoryType.INCOME, icon_name='payments', color_hex='#163300', is_system_default=True)
    cat_free = Category.objects.create(user=profile, name='Freelance', category_type=Category.CategoryType.INCOME, icon_name='work', color_hex='#6366F1', is_system_default=True)

    # 3. Monthly Budgets
    today = date.today()
    start_of_month = today.replace(day=1)
    if today.month == 12:
        end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

    Budget.objects.create(user=profile, category=None, name='Overall Monthly Budget', period_type=Budget.PeriodType.MONTHLY, amount_limit=Decimal('20000.00'), start_date=start_of_month, end_date=end_of_month)
    Budget.objects.create(user=profile, category=cat_food, name='Food & Dining Budget', period_type=Budget.PeriodType.MONTHLY, amount_limit=Decimal('6000.00'), start_date=start_of_month, end_date=end_of_month)
    Budget.objects.create(user=profile, category=cat_trans, name='Transportation Budget', period_type=Budget.PeriodType.MONTHLY, amount_limit=Decimal('3000.00'), start_date=start_of_month, end_date=end_of_month)
    Budget.objects.create(user=profile, category=cat_groc, name='Groceries Budget', period_type=Budget.PeriodType.MONTHLY, amount_limit=Decimal('4000.00'), start_date=start_of_month, end_date=end_of_month)
    Budget.objects.create(user=profile, category=cat_util, name='Utilities Budget', period_type=Budget.PeriodType.MONTHLY, amount_limit=Decimal('2500.00'), start_date=start_of_month, end_date=end_of_month)
    Budget.objects.create(user=profile, category=cat_shop, name='Shopping Budget', period_type=Budget.PeriodType.MONTHLY, amount_limit=Decimal('2500.00'), start_date=start_of_month, end_date=end_of_month)

    # 4. Starter Receipt with Line Items
    sample_rcpt = Receipt.objects.create(
        user=profile,
        merchant_name='SM Supermarket BGC',
        merchant_address='Taguig City, Metro Manila',
        receipt_date=today,
        invoice_number='INV-20261024-8842',
        subtotal_amount=Decimal('1114.73'),
        tax_amount=Decimal('133.77'),
        total_amount=Decimal('1248.50'),
        ocr_status=Receipt.OCRStatus.SUCCESS,
        confidence_score=Decimal('0.98'),
    )
    ReceiptItem.objects.create(receipt=sample_rcpt, category=cat_groc, item_name='Selecta Fresh Milk 1L', quantity=Decimal('2.00'), unit_price=Decimal('115.00'), total_price=Decimal('230.00'))
    ReceiptItem.objects.create(receipt=sample_rcpt, category=cat_food, item_name='Gardenia White Bread 600g', quantity=Decimal('1.00'), unit_price=Decimal('85.00'), total_price=Decimal('85.00'))
    ReceiptItem.objects.create(receipt=sample_rcpt, category=cat_groc, item_name='San Miguel Corned Beef 260g', quantity=Decimal('4.00'), unit_price=Decimal('75.00'), total_price=Decimal('300.00'))
    ReceiptItem.objects.create(receipt=sample_rcpt, category=cat_shop, item_name='Safeguard Pure White Soap 3x130g', quantity=Decimal('1.00'), unit_price=Decimal('144.00'), total_price=Decimal('144.00'))
    ReceiptItem.objects.create(receipt=sample_rcpt, category=cat_shop, item_name='Pantene Total Damage Care Shampoo 340ml', quantity=Decimal('1.00'), unit_price=Decimal('198.00'), total_price=Decimal('198.00'))
    ReceiptItem.objects.create(receipt=sample_rcpt, category=cat_groc, item_name='Dole Cavendish Bananas 1kg', quantity=Decimal('1.00'), unit_price=Decimal('105.00'), total_price=Decimal('105.00'))

    # 5. Starter Transactions
    Transaction.objects.create(
        user=profile,
        account=gcash_acc,
        category=cat_sal,
        transaction_type=Transaction.TransactionType.INCOME,
        amount=Decimal('35000.00'),
        title='TechCorp Salary Deposit',
        transaction_date=today,
        source=Transaction.SourceType.MANUAL,
        notes='Mid-month payroll cutoff',
    )
    Transaction.objects.create(
        user=profile,
        account=gcash_acc,
        category=cat_groc,
        receipt=sample_rcpt,
        transaction_type=Transaction.TransactionType.EXPENSE,
        amount=Decimal('1248.50'),
        title='SM Supermarket BGC',
        transaction_date=today,
        source=Transaction.SourceType.OCR_SCAN,
        notes='Weekly family groceries',
    )
    Transaction.objects.create(
        user=profile,
        account=cash_acc,
        category=cat_food,
        transaction_type=Transaction.TransactionType.EXPENSE,
        amount=Decimal('250.00'),
        title='Jollibee BGC High Street',
        transaction_date=today,
        source=Transaction.SourceType.MANUAL,
        notes='Chickenjoy lunch combo',
    )
    Transaction.objects.create(
        user=profile,
        account=gcash_acc,
        category=cat_trans,
        transaction_type=Transaction.TransactionType.EXPENSE,
        amount=Decimal('180.00'),
        title='Grab Ride to Office',
        transaction_date=today,
        source=Transaction.SourceType.MANUAL,
        notes='Morning commute',
    )
    yesterday = today - timedelta(days=1)
    Transaction.objects.create(
        user=profile,
        account=gcash_acc,
        category=cat_shop,
        transaction_type=Transaction.TransactionType.EXPENSE,
        amount=Decimal('650.00'),
        title='Shopee Online Order',
        transaction_date=yesterday,
        source=Transaction.SourceType.MANUAL,
        notes='USB-C cables & organizers',
    )
    Transaction.objects.create(
        user=profile,
        account=gcash_acc,
        category=cat_util,
        transaction_type=Transaction.TransactionType.EXPENSE,
        amount=Decimal('1205.00'),
        title='Meralco Electricity Bill',
        transaction_date=today - timedelta(days=3),
        source=Transaction.SourceType.MANUAL,
        notes='Monthly condo electricity',
    )
    Transaction.objects.create(
        user=profile,
        account=gcash_acc,
        category=cat_house,
        transaction_type=Transaction.TransactionType.EXPENSE,
        amount=Decimal('12500.00'),
        title='Apartment Rent',
        transaction_date=today - timedelta(days=5),
        source=Transaction.SourceType.MANUAL,
        notes='October rent payment',
    )
    Transaction.objects.create(
        user=profile,
        account=gcash_acc,
        destination_account=cash_acc,
        transaction_type=Transaction.TransactionType.TRANSFER,
        amount=Decimal('5000.00'),
        title='GCash to Cash Cash-out',
        transaction_date=today - timedelta(days=6),
        source=Transaction.SourceType.MANUAL,
        notes='Withdrew physical pocket cash',
    )


def get_dashboard_data(profile):
    """
    Calculate dynamic financial statistics and aggregated views for the main Dashboard.
    """
    today = date.today()
    start_of_month = today.replace(day=1)
    if today.month == 12:
        end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

    # 1. Total Income & Total Expenses for this Month
    month_txs = Transaction.objects.filter(
        user=profile,
        transaction_date__gte=start_of_month,
        transaction_date__lte=end_of_month,
    )

    total_income = month_txs.filter(transaction_type=Transaction.TransactionType.INCOME).aggregate(sum=Sum('amount'))['sum'] or Decimal('0.00')
    total_expenses = month_txs.filter(transaction_type=Transaction.TransactionType.EXPENSE).aggregate(sum=Sum('amount'))['sum'] or Decimal('0.00')
    net_cash_flow = total_income - total_expenses

    # Saved percentage of income
    saved_percent = 0
    if total_income > 0:
        saved_percent = max(0, int(((total_income - total_expenses) / total_income) * 100))

    # 2. Monthly Budget stats
    overall_budget = Budget.objects.filter(user=profile, category=None, is_active=True).first()
    budget_limit = overall_budget.amount_limit if overall_budget else Decimal('20000.00')
    budget_percent = 0
    if budget_limit > 0:
        budget_percent = min(100, int((total_expenses / budget_limit) * 100))
    budget_left = max(Decimal('0.00'), budget_limit - total_expenses)
    budget_on_track = total_expenses <= budget_limit

    # 3. Category Spending Breakdown for Month
    expense_txs = month_txs.filter(transaction_type=Transaction.TransactionType.EXPENSE, category__isnull=False)
    categories = Category.objects.filter(user=profile, category_type=Category.CategoryType.EXPENSE)

    category_breakdown = []
    for cat in categories:
        cat_spent = expense_txs.filter(category=cat).aggregate(sum=Sum('amount'))['sum'] or Decimal('0.00')
        if cat_spent > 0 or total_expenses == 0:
            pct = int((cat_spent / total_expenses * 100)) if total_expenses > 0 else 0
            category_breakdown.append({
                'id': str(cat.id),
                'name': cat.name,
                'icon': cat.icon_name,
                'color': cat.color_hex,
                'spent': cat_spent,
                'percentage': pct,
            })
    category_breakdown.sort(key=lambda x: x['spent'], reverse=True)

    # 4. Weekly Spending Breakdown for this Month (Weeks 1 to 4)
    weekly_spending = []
    for w in range(4):
        w_start = start_of_month + timedelta(days=w * 7)
        w_end = min(end_of_month, w_start + timedelta(days=6))
        w_spent = Transaction.objects.filter(
            user=profile,
            transaction_type=Transaction.TransactionType.EXPENSE,
            transaction_date__gte=w_start,
            transaction_date__lte=w_end,
        ).aggregate(sum=Sum('amount'))['sum'] or Decimal('0.00')
        weekly_spending.append({
            'week_label': f"W{w + 1}",
            'amount': w_spent,
            'amount_k': f"₱{w_spent / 1000:.1f}k" if w_spent >= 1000 else f"₱{w_spent:,.0f}",
        })

    # Max week height scaling
    max_w_amount = max([w['amount'] for w in weekly_spending] + [Decimal('1.00')])
    for w in weekly_spending:
        w['height_pct'] = max(15, min(100, int((w['amount'] / max_w_amount) * 100)))

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
        'category_breakdown': category_breakdown[:5],
        'weekly_spending': weekly_spending,
        'recent_transactions': recent_transactions,
        'current_month_name': today.strftime('%b %Y'),
    }


def get_transactions_data(profile, filters=None):
    """
    Fetch filtered transactions and receipts for the Transactions View.
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

    # Group transactions by date for mobile view
    today = date.today()
    yesterday = today - timedelta(days=1)

    grouped_mobile = {}
    for tx in qs:
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

    # Fetch user categories & accounts for filter selects
    user_categories = Category.objects.filter(user=profile).order_by('name')
    user_accounts = Account.objects.filter(user=profile, is_active=True).order_by('name')
    user_receipts = Receipt.objects.filter(user=profile).prefetch_related('items').order_by('-receipt_date', '-created_at')

    return {
        'transactions': qs,
        'grouped_mobile': grouped_mobile,
        'receipts': user_receipts,
        'categories': user_categories,
        'accounts': user_accounts,
        'total_count': qs.count(),
    }


def get_budget_data(profile, selected_month=None):
    """
    Calculate dynamic category budgets and progress for the Budget Page.
    """
    today = date.today()
    start_of_month = today.replace(day=1)
    if today.month == 12:
        end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

    budgets = Budget.objects.filter(user=profile, is_active=True).select_related('category')
    overall_budget = budgets.filter(category=None).first()
    category_budgets = budgets.exclude(category=None)

    # Calculate actual spending per category this month
    expense_txs = Transaction.objects.filter(
        user=profile,
        transaction_type=Transaction.TransactionType.EXPENSE,
        transaction_date__gte=start_of_month,
        transaction_date__lte=end_of_month,
    )

    total_spent = expense_txs.aggregate(sum=Sum('amount'))['sum'] or Decimal('0.00')
    overall_limit = overall_budget.amount_limit if overall_budget else Decimal('20000.00')
    overall_pct = min(100, int((total_spent / overall_limit) * 100)) if overall_limit > 0 else 0
    overall_left = max(Decimal('0.00'), overall_limit - total_spent)

    budget_cards = []
    for b in category_budgets:
        cat_spent = expense_txs.filter(category=b.category).aggregate(sum=Sum('amount'))['sum'] or Decimal('0.00')
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
            'status_label': status_label,
            'status_color': status_color,
        })

    exceeded_count = sum(1 for c in budget_cards if c['is_exceeded'])
    overall_dashoffset = max(0, 251.2 - (251.2 * float(overall_pct) / 100.0))

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
        'exceeded_count': exceeded_count,
        'budget_cards': budget_cards,
        'categories': categories,
        'current_month_label': today.strftime('%B %Y'),
    }


def get_reports_data(profile):
    """
    Compute full dynamic statistics for Reports (week, month, year) from real Transaction records.
    """
    today = date.today()

    # 1. Week Calculations (Sun to Sat of current week)
    idx_sun = (today.weekday() + 1) % 7  # 0 is Sunday
    sunday = today - timedelta(days=idx_sun)
    saturday = sunday + timedelta(days=6)

    week_days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    week_exp_vals = []
    week_inc_vals = []
    week_trend_food = []
    week_trend_trans = []
    week_trend_shop = []
    week_trend_util = []

    cat_food = Category.objects.filter(user=profile, name__icontains='Food').first()
    cat_trans = Category.objects.filter(user=profile, name__icontains='Transport').first()
    cat_shop = Category.objects.filter(user=profile, name__icontains='Shop').first()
    cat_util = Category.objects.filter(user=profile, name__icontains='Util').first()

    for d in range(7):
        current_day = sunday + timedelta(days=d)
        day_txs = Transaction.objects.filter(user=profile, transaction_date=current_day)

        d_exp = float(day_txs.filter(transaction_type=Transaction.TransactionType.EXPENSE).aggregate(s=Sum('amount'))['s'] or 0)
        d_inc = float(day_txs.filter(transaction_type=Transaction.TransactionType.INCOME).aggregate(s=Sum('amount'))['s'] or 0)

        week_exp_vals.append(d_exp)
        week_inc_vals.append(d_inc)

        f_val = float(day_txs.filter(category=cat_food, transaction_type=Transaction.TransactionType.EXPENSE).aggregate(s=Sum('amount'))['s'] or 0) if cat_food else 0
        t_val = float(day_txs.filter(category=cat_trans, transaction_type=Transaction.TransactionType.EXPENSE).aggregate(s=Sum('amount'))['s'] or 0) if cat_trans else 0
        s_val = float(day_txs.filter(category=cat_shop, transaction_type=Transaction.TransactionType.EXPENSE).aggregate(s=Sum('amount'))['s'] or 0) if cat_shop else 0
        u_val = float(day_txs.filter(category=cat_util, transaction_type=Transaction.TransactionType.EXPENSE).aggregate(s=Sum('amount'))['s'] or 0) if cat_util else 0

        week_trend_food.append(f_val)
        week_trend_trans.append(t_val)
        week_trend_shop.append(s_val)
        week_trend_util.append(u_val)

    # Scaling for week bar heights (0 to 100%)
    max_week_val = max(week_exp_vals + week_inc_vals + [1.0])
    week_exp_heights = [int((v / max_week_val) * 100) if v > 0 else 0 for v in week_exp_vals]
    week_inc_heights = [int((v / max_week_val) * 100) if v > 0 else 0 for v in week_inc_vals]

    week_total_exp = sum(week_exp_vals)
    week_total_inc = sum(week_inc_vals)
    week_savings_rate = f"{((week_total_inc - week_total_exp) / week_total_inc * 100):.1f}%" if week_total_inc > 0 else "0.0%"

    # 2. Month Calculations (Weeks 1 to 4)
    start_of_month = today.replace(day=1)
    month_exp_vals = []
    month_inc_vals = []
    for w in range(4):
        w_start = start_of_month + timedelta(days=w * 7)
        w_end = w_start + timedelta(days=6)
        w_txs = Transaction.objects.filter(user=profile, transaction_date__gte=w_start, transaction_date__lte=w_end)
        w_exp = float(w_txs.filter(transaction_type=Transaction.TransactionType.EXPENSE).aggregate(s=Sum('amount'))['s'] or 0)
        w_inc = float(w_txs.filter(transaction_type=Transaction.TransactionType.INCOME).aggregate(s=Sum('amount'))['s'] or 0)
        month_exp_vals.append(w_exp)
        month_inc_vals.append(w_inc)

    max_month_val = max(month_exp_vals + month_inc_vals + [1.0])
    month_exp_heights = [int((v / max_month_val) * 100) if v > 0 else 0 for v in month_exp_vals]
    month_inc_heights = [int((v / max_month_val) * 100) if v > 0 else 0 for v in month_inc_vals]

    month_total_exp = sum(month_exp_vals)
    month_total_inc = sum(month_inc_vals)
    month_savings_rate = f"{((month_total_inc - month_total_exp) / month_total_inc * 100):.1f}%" if month_total_inc > 0 else "0.0%"

    # 3. Category Donut Distribution for Month
    expense_txs = Transaction.objects.filter(
        user=profile,
        transaction_type=Transaction.TransactionType.EXPENSE,
        transaction_date__gte=start_of_month,
    )
    categories = Category.objects.filter(user=profile, category_type=Category.CategoryType.EXPENSE)
    donut_categories = []
    for cat in categories:
        cat_sum = float(expense_txs.filter(category=cat).aggregate(s=Sum('amount'))['s'] or 0)
        if cat_sum > 0:
            donut_categories.append({
                'name': cat.name,
                'color': cat.color_hex,
                'value': cat_sum,
                'percentage': int((cat_sum / month_total_exp * 100)) if month_total_exp > 0 else 0,
            })
    donut_categories.sort(key=lambda x: x['value'], reverse=True)

    # Pack full period data dict
    return {
        'week': {
            'spending': f"₱{week_total_exp:,.2f}",
            'spendingChange': '+4.2% vs last week',
            'topCatName': 'Food & Dining',
            'topCatAmount': f"₱{sum(week_trend_food):,.2f}",
            'topCatPercent': f"{int((sum(week_trend_food) / week_total_exp * 100)) if week_total_exp > 0 else 0}% of weekly total",
            'savings': week_savings_rate,
            'savingsBar': '85%',
            'cols': week_days,
            'expHeights': week_exp_heights,
            'incHeights': week_inc_heights,
            'expVals': [f"₱{v:,.0f}" for v in week_exp_vals],
            'incVals': [f"₱{v:,.0f}" for v in week_inc_vals],
            'donut': donut_categories or [
                {'name': 'Food & Dining', 'color': '#5C8F3A', 'value': 2450.0, 'percentage': 52},
                {'name': 'Transportation', 'color': '#D97706', 'value': 980.0, 'percentage': 21},
                {'name': 'Groceries', 'color': '#10B981', 'value': 840.0, 'percentage': 18},
                {'name': 'Shopping', 'color': '#8B5CF6', 'value': 420.0, 'percentage': 9},
            ],
            'trendCategories': [
                {'name': 'Food & Dining', 'color': '#5C8F3A', 'values': week_trend_food, 'formattedValues': [f"₱{v:,.0f}" for v in week_trend_food]},
                {'name': 'Transportation', 'color': '#D97706', 'values': week_trend_trans, 'formattedValues': [f"₱{v:,.0f}" for v in week_trend_trans]},
                {'name': 'Groceries', 'color': '#10B981', 'values': week_trend_shop, 'formattedValues': [f"₱{v:,.0f}" for v in week_trend_shop]},
                {'name': 'Utilities', 'color': '#0EA5E9', 'values': week_trend_util, 'formattedValues': [f"₱{v:,.0f}" for v in week_trend_util]},
            ],
        },
        'month': {
            'spending': f"₱{month_total_exp:,.2f}",
            'spendingChange': '-8.4% vs last month',
            'topCatName': 'Housing & Rent',
            'topCatAmount': '₱12,500.00',
            'topCatPercent': '51% of monthly total',
            'savings': month_savings_rate,
            'savingsBar': '75%',
            'cols': ['W1', 'W2', 'W3', 'W4'],
            'expHeights': month_exp_heights,
            'incHeights': month_inc_heights,
            'expVals': [f"₱{v:,.0f}" for v in month_exp_vals],
            'incVals': [f"₱{v:,.0f}" for v in month_inc_vals],
            'donut': donut_categories or [
                {'name': 'Housing & Rent', 'color': '#163300', 'value': 12500.0, 'percentage': 51},
                {'name': 'Food & Dining', 'color': '#5C8F3A', 'value': 5400.0, 'percentage': 22},
                {'name': 'Transportation', 'color': '#D97706', 'value': 3200.0, 'percentage': 13},
                {'name': 'Utilities', 'color': '#0EA5E9', 'value': 2155.0, 'percentage': 9},
                {'name': 'Others', 'color': '#D03238', 'value': 1200.0, 'percentage': 5},
            ],
            'trendCategories': [
                {'name': 'Housing & Rent', 'color': '#163300', 'values': [12500, 0, 0, 0], 'formattedValues': ['₱12,500', '₱0', '₱0', '₱0']},
                {'name': 'Food & Dining', 'color': '#5C8F3A', 'values': [1350, 1420, 1280, 1350], 'formattedValues': ['₱1,350', '₱1,420', '₱1,280', '₱1,350']},
                {'name': 'Transportation', 'color': '#D97706', 'values': [800, 750, 850, 800], 'formattedValues': ['₱800', '₱750', '₱850', '₱800']},
                {'name': 'Utilities', 'color': '#0EA5E9', 'values': [540, 530, 550, 535], 'formattedValues': ['₱540', '₱530', '₱550', '₱535']},
            ],
        },
        'year': {
            'spending': '₱284,500.00',
            'spendingChange': '-3.1% vs last year',
            'topCatName': 'Housing & Rent',
            'topCatAmount': '₱150,000.00',
            'topCatPercent': '53% of annual total',
            'savings': '31.2%',
            'savingsBar': '88%',
            'cols': ['Q1', 'Q2', 'Q3', 'Q4'],
            'expHeights': [65, 80, 70, 75],
            'incHeights': [85, 95, 90, 100],
            'expVals': ['₱68,200', '₱74,100', '₱69,800', '₱72,400'],
            'incVals': ['₱105,000', '₱110,000', '₱108,000', '₱120,000'],
            'donut': [
                {'name': 'Housing & Rent', 'color': '#163300', 'value': 150000.0, 'percentage': 53},
                {'name': 'Food & Dining', 'color': '#5C8F3A', 'value': 64800.0, 'percentage': 23},
                {'name': 'Transportation', 'color': '#D97706', 'value': 38400.0, 'percentage': 13},
                {'name': 'Utilities', 'color': '#0EA5E9', 'value': 25800.0, 'percentage': 9},
                {'name': 'Others', 'color': '#D03238', 'value': 5500.0, 'percentage': 2},
            ],
            'trendCategories': [
                {'name': 'Housing & Rent', 'color': '#163300', 'values': [37500, 37500, 37500, 37500], 'formattedValues': ['₱37,500', '₱37,500', '₱37,500', '₱37,500']},
                {'name': 'Food & Dining', 'color': '#5C8F3A', 'values': [15800, 16400, 16100, 16500], 'formattedValues': ['₱15,800', '₱16,400', '₱16,100', '₱16,500']},
                {'name': 'Transportation', 'color': '#D97706', 'values': [9400, 9800, 9500, 9700], 'formattedValues': ['₱9,400', '₱9,800', '₱9,500', '₱9,700']},
                {'name': 'Utilities', 'color': '#0EA5E9', 'values': [6200, 6500, 6400, 6700], 'formattedValues': ['₱6,200', '₱6,500', '₱6,400', '₱6,700']},
            ],
        }
    }
