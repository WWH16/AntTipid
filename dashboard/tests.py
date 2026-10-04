from decimal import Decimal
from datetime import date

from django.test import TestCase

from .models import UserProfile, Account, Category, Transaction, Budget
from .services import get_dashboard_data


class DashboardMoneyTest(TestCase):
    def test_over_budget_figures_are_not_capped(self):
        user = UserProfile.objects.create(clerk_user_id='u1')
        cash = Account.objects.create(user=user, name='Cash')
        food = Category.objects.create(user=user, name='Food')
        Budget.objects.create(user=user, name='Monthly', amount_limit=Decimal('1000'))
        Transaction.objects.create(user=user, account=cash, category=food, amount=Decimal('1500'),
                                   title='Jollibee', transaction_date=date.today())

        data = get_dashboard_data(user)

        self.assertEqual(data['budget_percent'], 100)          # bar width is capped
        self.assertEqual(data['budget_percent_actual'], 150)   # displayed figure is not
        self.assertEqual(data['budget_over'], Decimal('500'))
        self.assertEqual(data['budget_left'], Decimal('0'))
        self.assertEqual(data['net_cash_flow_abs'], Decimal('1500'))
