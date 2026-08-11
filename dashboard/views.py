import os
import json
import base64
import urllib.request
import urllib.error
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


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


def receipt_detail_view(request):
    """Render the receipt details view."""
    context = {
        'active_nav': 'transactions',
    }
    return render(request, 'dashboard/receipt_detail.html', context)


def add_transaction_view(request):
    """Render the manual transaction entry screen."""
    context = {
        'active_nav': 'add_transaction',
    }
    return render(request, 'dashboard/add_transaction.html', context)


def scan_receipt_view(request):
    """Render the AI Receipt Scanner & Editor screen."""
    context = {
        'active_nav': 'scan_receipt',
        'has_gemini_key': bool(os.getenv('GEMINI_API_KEY')),
    }
    return render(request, 'dashboard/scan_receipt.html', context)


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

    # Check uploaded file first, safely handling body size limits
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

    # If Gemini API key is configured and image provided, invoke Google GenAI SDK
    if gemini_key and (image_base64 or 'image_bytes' in locals()):
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=gemini_key)
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
            import traceback
            print("Gemini OCR Exception:", e)
            traceback.print_exc()
            return JsonResponse({'error': f'Gemini OCR failed: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Failed to process receipt image with Gemini API'}, status=400)
