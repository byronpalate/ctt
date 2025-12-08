#!/usr/bin/env python

import sys
import os

from django.contrib.postgres.aggregates.general import StringAgg
from django.db.models.expressions import F, Case, When, Value, Func
from django.forms.fields import CharField
from django.utils.timezone import now

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

your_djangoproject_home = os.path.split(SITE_ROOT)[0]

sys.path.append(your_djangoproject_home)
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import django
from django.db import connection, transaction

django.setup()
from datetime import datetime, timedelta
from ctt.models import *
from django.contrib.admin.models import LogEntry
from settings import *
from ctt.funciones import *

# MI ID PERSONA: 46868
# # MI INSCRIPCION: 58710


cliente=Cliente.objects.get(pk=36)

send_mail(subject='Registro completo CTT Indoamerica.',
          html_template='emails/registrook.html',
          data={'cliente': cliente},
          recipient_list=[cliente.persona],
          correos=cliente.correo_de_envio())

print('ok')