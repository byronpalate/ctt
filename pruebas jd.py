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
from django.db import models
from django.contrib.auth.models import Group
from django.conf import settings


class TipoSolicitudSecretariaDocente(models.Model):
    nombre = models.CharField(max_length=250)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    grupos = models.ManyToManyField(
        Group,
        blank=True,
        related_name='tipos_solicitud_secretaria_docente'
    )

    class Meta:
        verbose_name = 'Tipo de Solicitud Secretaría Docente'
        verbose_name_plural = 'Tipos de Solicitud Secretaría Docente'

    def __str__(self):
        return self.nombre


class SolicitudSecretariaDocente(models.Model):
    tipo = models.ForeignKey(
        TipoSolicitudSecretariaDocente,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='solicitudes_secretaria_docente'
    )

    # tus demás campos aquí...

    class Meta:
        verbose_name = 'Solicitud Secretaría Docente'
        verbose_name_plural = 'Solicitudes Secretaría Docente'

    def __str__(self):
        return f'Solicitud #{self.id}'