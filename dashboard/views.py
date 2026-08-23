import os
import json
import base64
from decimal import Decimal
from datetime import datetime, date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction as db_transaction

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
from .services import (
    get_current_user_profile,
    get_dashboard_data,
    get_transactions_data,
    get_budget_data,
    get_reports_data,
)


def landing_view(request):
    """Render the AntTipid Landing Page."""
    context = {
        'active_nav': 'landing',
    }
    return render(request, 'dashboard/landing.html', context)


def dashboard_view(request):
    """Render the main AntTipid dashboard with live database stats."""
    profile = get_current_user_profile(request)
    data = get_dashboard_data(profile) if profile else {}

    context = {
        'active_nav': 'dashboard',
        'profile': profile,
        **data,
    }
    return render(request, 'dashboard/index.html', context)


def transactions_view(request):
    """Render the transactions history view with database data and filtering."""
    profile = get_current_user_profile(request)
    data = get_transactions_data(profile, request.GET) if profile else {}

    context = {
        'active_nav': 'transactions',
        'profile': profile,
        'selected_type': request.GET.get('type', ''),
        'selected_category': request.GET.get('category', ''),
        'search_query': request.GET.get('q', ''),
        **data,
    }
    return render(request, 'dashboard/transactions.html', context)


def budget_view(request):
    """Render the budget view with live spending against category targets."""
    profile = get_current_user_profile(request)
    data = get_budget_data(profile) if profile else {}

    context = {
        'active_nav': 'budgets',
        'profile': profile,
        **data,
    }
    return render(request, 'dashboard/budget.html', context)


def reports_view(request):
    """Render the financial reports and insights view backed by database calculations."""
    profile = get_current_user_profile(request)
    period_data = get_reports_data(profile) if profile else {}

    context = {
        'active_nav': 'reports',
        'profile': profile,
        'period_data_json': json.dumps(period_data),
    }
    return render(request, 'dashboard/reports.html', context)


def receipt_detail_view(request, pk=None):
    """Render the receipt details view with database line items."""
    profile = get_current_user_profile(request)
    receipt = None
    if pk:
        receipt = get_object_or_404(Receipt, id=pk, user=profile)
    elif profile:
        receipt = Receipt.objects.filter(user=profile).prefetch_related('items').first()

    context = {
        'active_nav': 'transactions',
        'profile': profile,
        'receipt': receipt,
        'items': receipt.items.all() if receipt else [],
    }
    return render(request, 'dashboard/receipt_detail.html', context)


def add_transaction_view(request):
    """Render and process the manual transaction entry screen."""
    profile = get_current_user_profile(request)

    if request.method == 'POST':
        try:
            amount_str = request.POST.get('amount', '0').replace('₱', '').replace(',', '').strip()
            amount = Decimal(amount_str)
            title = request.POST.get('title', '').strip() or 'Untitled Transaction'
            tx_type = request.POST.get('type', 'expense').upper()
            category_name = request.POST.get('category', '').strip()
            account_name = request.POST.get('account', 'Cash Wallet').strip()
            tx_date_str = request.POST.get('date', '').strip()
            notes = request.POST.get('notes', '').strip()

            tx_date = datetime.strptime(tx_date_str, '%Y-%m-%d').date() if tx_date_str else date.today()

            # Resolve Account
            account = Account.objects.filter(user=profile, name__icontains=account_name.split()[0]).first()
            if not account:
                account = Account.objects.filter(user=profile, account_type=Account.AccountType.CASH).first()

            # Resolve Category
            category = None
            if category_name:
                category = Category.objects.filter(user=profile, name__icontains=category_name).first()

            with db_transaction.atomic():
                tx = Transaction.objects.create(
                    user=profile,
                    account=account,
                    category=category,
                    transaction_type=tx_type if tx_type in ('EXPENSE', 'INCOME', 'TRANSFER') else 'EXPENSE',
                    amount=amount,
                    title=title,
                    transaction_date=tx_date,
                    notes=notes,
                    source=Transaction.SourceType.MANUAL,
                )

                # Update balance
                if tx.transaction_type == Transaction.TransactionType.EXPENSE:
                    account.current_balance -= amount
                elif tx.transaction_type == Transaction.TransactionType.INCOME:
                    account.current_balance += amount
                account.save(update_fields=['current_balance', 'updated_at'])

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'id': str(tx.id)})
            return redirect('transactions')

        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': str(e)}, status=400)

    categories = Category.objects.filter(user=profile).order_by('name') if profile else []
    accounts = Account.objects.filter(user=profile, is_active=True).order_by('name') if profile else []

    context = {
        'active_nav': 'add_transaction',
        'profile': profile,
        'categories': categories,
        'accounts': accounts,
    }
    return render(request, 'dashboard/add_transaction.html', context)


def scan_receipt_view(request):
    """Render the AI Receipt Scanner & Editor screen."""
    context = {
        'active_nav': 'scan_receipt',
        'has_gemini_key': bool(os.getenv('GEMINI_API_KEY')),
    }
    return render(request, 'dashboard/scan_receipt.html', context)


# ═══════════════════════════════════════════════════════════════════════════════
# JSON API ENDPOINTS FOR CLIENT-SIDE ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_POST
def api_create_transaction(request):
    """API endpoint to create a new manual transaction."""
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        amount = Decimal(str(data.get('amount', 0)))
        title = data.get('title', '').strip() or 'Untitled Transaction'
        tx_type = data.get('type', 'expense').upper()
        category_name = data.get('category', '').strip()
        account_name = data.get('account', 'Cash Wallet').strip()
        tx_date_str = data.get('date', '').strip()
        notes = data.get('notes', '').strip()

        tx_date = datetime.strptime(tx_date_str, '%Y-%m-%d').date() if tx_date_str else date.today()

        account = Account.objects.filter(user=profile, name__icontains=account_name.split()[0]).first()
        if not account:
            account = Account.objects.filter(user=profile, account_type=Account.AccountType.CASH).first()

        category = Category.objects.filter(user=profile, name__icontains=category_name).first() if category_name else None

        with db_transaction.atomic():
            tx = Transaction.objects.create(
                user=profile,
                account=account,
                category=category,
                transaction_type=tx_type if tx_type in ('EXPENSE', 'INCOME', 'TRANSFER') else 'EXPENSE',
                amount=amount,
                title=title,
                transaction_date=tx_date,
                notes=notes,
                source=Transaction.SourceType.MANUAL,
            )

            if tx.transaction_type == Transaction.TransactionType.EXPENSE:
                account.current_balance -= amount
            elif tx.transaction_type == Transaction.TransactionType.INCOME:
                account.current_balance += amount
            account.save(update_fields=['current_balance', 'updated_at'])

        return JsonResponse({'success': True, 'id': str(tx.id)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def api_update_transaction(request, pk):
    """API endpoint to update an existing transaction."""
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    tx = get_object_or_404(Transaction, id=pk, user=profile)

    try:
        data = json.loads(request.body.decode('utf-8'))
        if 'amount' in data:
            new_amount = Decimal(str(data['amount']))
            # Adjust account balance difference
            diff = new_amount - tx.amount
            if tx.transaction_type == Transaction.TransactionType.EXPENSE:
                tx.account.current_balance -= diff
            elif tx.transaction_type == Transaction.TransactionType.INCOME:
                tx.account.current_balance += diff
            tx.account.save(update_fields=['current_balance', 'updated_at'])
            tx.amount = new_amount

        if 'title' in data:
            tx.title = data['title'].strip()
        if 'notes' in data:
            tx.notes = data['notes'].strip()
        if 'date' in data and data['date']:
            tx.transaction_date = datetime.strptime(data['date'], '%Y-%m-%d').date()

        if 'category' in data and data['category']:
            cat = Category.objects.filter(user=profile, name__icontains=data['category']).first()
            if cat:
                tx.category = cat

        if 'account' in data and data['account']:
            acc = Account.objects.filter(user=profile, name__icontains=data['account'].split()[0]).first()
            if acc and acc != tx.account:
                tx.account = acc

        tx.save()
        return JsonResponse({'success': True, 'id': str(tx.id)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def api_delete_transaction(request, pk):
    """API endpoint to delete a transaction."""
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    tx = get_object_or_404(Transaction, id=pk, user=profile)

    with db_transaction.atomic():
        # Revert account balance
        if tx.transaction_type == Transaction.TransactionType.EXPENSE:
            tx.account.current_balance += tx.amount
        elif tx.transaction_type == Transaction.TransactionType.INCOME:
            tx.account.current_balance -= tx.amount
        tx.account.save(update_fields=['current_balance', 'updated_at'])

        tx.delete()

    return JsonResponse({'success': True})


@csrf_exempt
@require_POST
def api_save_budget(request):
    """API endpoint to create or update category budget limits."""
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        category_id = data.get('category_id')
        category_name = data.get('category')
        amount_limit = Decimal(str(data.get('amount_limit') or data.get('amount') or 0))

        today = date.today()
        start_of_month = today.replace(day=1)
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        category_icon = data.get('icon') or data.get('icon_name') or 'category'
        category_color = data.get('color') or data.get('color_hex') or '#5C8F3A'

        if category_id:
            category = Category.objects.filter(id=category_id, user=profile).first()
            if category and (data.get('icon') or data.get('color')):
                if data.get('icon'):
                    category.icon_name = data.get('icon')
                if data.get('color'):
                    category.color_hex = data.get('color')
                category.save()
        elif category_name:
            category = Category.objects.filter(name__iexact=category_name, user=profile).first()
            if not category:
                category = Category.objects.create(
                    user=profile,
                    name=category_name,
                    category_type=Category.CategoryType.EXPENSE,
                    icon_name=category_icon,
                    color_hex=category_color
                )
            elif data.get('icon') or data.get('color'):
                if data.get('icon'):
                    category.icon_name = data.get('icon')
                if data.get('color'):
                    category.color_hex = data.get('color')
                category.save()
        else:
            category = None

        budget, created = Budget.objects.update_or_create(
            user=profile,
            category=category,
            period_type=Budget.PeriodType.MONTHLY,
            defaults={
                'name': f"{category.name} Budget" if category else 'Overall Monthly Budget',
                'amount_limit': amount_limit,
                'start_date': start_of_month,
                'end_date': end_of_month,
                'is_active': True,
            }
        )

        return JsonResponse({'success': True, 'id': str(budget.id)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def api_update_receipt_items(request, pk):
    """API endpoint to update line items for a receipt."""
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    receipt = get_object_or_404(Receipt, id=pk, user=profile)

    try:
        data = json.loads(request.body.decode('utf-8'))
        items_data = data.get('items', [])

        with db_transaction.atomic():
            receipt.items.all().delete()
            new_total = Decimal('0.00')

            for item in items_data:
                item_name = (item.get('name') or item.get('description') or '').strip() or 'Item'
                qty = Decimal(str(item.get('qty', 1)))
                unit_price = Decimal(str(item.get('price') or item.get('unitPrice') or 0))
                total_price = qty * unit_price
                new_total += total_price

                ReceiptItem.objects.create(
                    receipt=receipt,
                    item_name=item_name,
                    quantity=qty,
                    unit_price=unit_price,
                    total_price=total_price,
                )

            receipt.total_amount = new_total
            receipt.ocr_status = Receipt.OCRStatus.EDITED
            receipt.save(update_fields=['total_amount', 'ocr_status', 'updated_at'])

            # If linked transaction exists, update its amount too
            if hasattr(receipt, 'linked_transaction') and receipt.linked_transaction:
                tx = receipt.linked_transaction
                tx.amount = new_total
                tx.save(update_fields=['amount', 'updated_at'])

        return JsonResponse({'success': True, 'total': float(new_total)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def api_delete_receipt(request, pk):
    """API endpoint to delete a scanned receipt."""
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    receipt = get_object_or_404(Receipt, id=pk, user=profile)
    receipt.delete()
    return JsonResponse({'success': True})


@csrf_exempt
def api_scan_receipt_view(request):
    """
    API Endpoint for processing receipt images with Gemini API OCR.
    Receives image upload or sample request, calls Gemini Vision API,
    and returns itemized JSON.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    gemini_key = os.getenv('GEMINI_API_KEY')
    image_base64 = None
    mime_type = 'image/jpeg'

    if request.FILES.get('receipt_image'):
        uploaded_file = request.FILES['receipt_image']
        image_bytes = uploaded_file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        if uploaded_file.content_type:
            mime_type = uploaded_file.content_type
    else:
        try:
            raw_body = request.body
            if raw_body:
                payload = json.loads(raw_body)
                raw_data = payload.get('image_data', '')
                if ',' in raw_data:
                    header, raw_data = raw_data.split(',', 1)
                    if 'png' in header:
                        mime_type = 'image/png'
                    elif 'webp' in header:
                        mime_type = 'image/webp'
                image_base64 = raw_data
        except Exception:
            pass

    if gemini_key and (image_base64 or 'image_bytes' in locals()):
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=gemini_key,
                http_options=types.HttpOptions(timeout=20_000),
            )
            prompt_text = (
                "You are an expert receipt OCR assistant for a Philippine personal finance app (AntTipid). "
                "Analyze this receipt image and return ONLY a valid JSON object matching this exact schema without markdown wrap:\n"
                "{\n"
                '  "merchant": "Store Name",\n'
                '  "date": "YYYY-MM-DD",\n'
                '  "time": "HH:MM",\n'
                '  "category": "Groceries",\n'
                '  "payment_method": "Cash | GCash | Maya | Credit Card | Debit Card | Bank Transfer",\n'
                '  "subtotal": 0.00,\n'
                '  "tax": 0.00,\n'
                '  "total": 0.00,\n'
                '  "cash_tendered": 0.00,\n'
                '  "change": 0.00,\n'
                '  "items": [\n'
                '    {"description": "Item description", "quantity": 1, "price": 0.00}\n'
                '  ]\n'
                "}\n"
                "Important guidelines:\n"
                "1. Total/Grand Total: Read the exact grand total printed on the receipt.\n"
                "2. Tax: Do NOT calculate or guess tax on your own. Only extract tax if it is explicitly printed on the receipt image; otherwise return 0.00.\n"
                "3. Cash & Change: If payment method is Cash, extract the cash tendered / amount paid and change stated on the receipt; otherwise return 0.00 for both.\n"
                "Category must be one of: Groceries, Dining, Transportation, Utilities, Shopping, Healthcare, Entertainment, Services, Other."
            )

            raw_bytes = image_bytes if 'image_bytes' in locals() else base64.b64decode(image_base64)

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[
                    types.Part.from_bytes(
                        data=raw_bytes,
                        mime_type=mime_type
                    ),
                    prompt_text
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )

            raw_text = response.text.strip()
            if raw_text.startswith('```'):
                raw_text = raw_text.split('```')[1]
                if raw_text.startswith('json'):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()

            extracted = json.loads(raw_text)
            extracted['source'] = 'gemini_api'
            return JsonResponse(extracted)
        except Exception as e:
            return JsonResponse({'error': f'Gemini OCR failed: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Failed to process receipt image with Gemini API'}, status=400)
