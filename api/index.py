import os
import sys

# Add root directory to sys.path so Django can locate modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AntTipid.settings')

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()
