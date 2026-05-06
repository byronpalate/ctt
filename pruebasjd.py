#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

# Full path and name to your csv file
# from django.db.backends.oracle.base import to_unicode


import os
import django

# Especifica la configuración de Django predeterminada de tu proyecto.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

# Prepara el entorno de Django.
django.setup()


from ctt.commonviews import *


from ctt.models import *

from django.apps import apps

from django.contrib.auth.models import Permission

# Obtener todos los permisos
from django.contrib.auth.models import User

from decimal import Decimal
from django.db import transaction
from ctt.models import TipoServicio, ServicioCatalogo


from decimal import Decimal
from django.db import transaction
from ctt.models import TipoServicio, ServicioCatalogo
#
# # Códigos de tipo de cobro:
# # 1 = POR_ITEM (por ensayo / pieza / muestra / paquete)
# # 2 = POR_HORA (por hora)
#
# SERVICIOS_DATA = [
#     # =========================
#     # LABORATORIO DE MATERIALES (por ítem)
#     # =========================
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Gravedad específica para el suelo",
#      1, "8.50", ""),
#
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Gravedad específica para el cemento (densidad de cemento hidráulico)",
#      1, "22.00", ""),
#
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Extracción de núcleos de hormigón",
#      1, "45.00", ""),
#
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Extracción de núcleos de asfalto",
#      1, "45.00", ""),
#
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Abrasión de materiales pétreos",
#      1, "40.00", ""),
#
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Resistencia a la compresión de cilindros de hormigón",
#      1, "5.50", ""),
#
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Determinación del límite líquido (método de Casagrande)",
#      1, "10.00", ""),
#
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Determinación del límite plástico (método de Casagrande)",
#      1, "6.00", ""),
#
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Contenido de humedad del suelo",
#      1, "3.00", ""),
#
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Consistencia o asentamiento de hormigón",
#      1, "3.00", ""),
#
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Porcentaje de aire en hormigón fresco",
#      1, "25.00", ""),
#
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Ensayo de flexión de vigas",
#      1, "14.00", ""),
#
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Ensayo a compresión de cubos de mortero",
#      1, "5.20", ""),
#
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Granulometría de suelos",
#      1, "15.00", ""),
#
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Granulometría de áridos",
#      1, "20.00", ""),
#
#     ("LAB_MAT", "Laboratorio de Materiales",
#      "Toma de muestra de cilindros de hormigón",
#      1, "6.00", ""),
#
#     # =====================
#     # LABORATORIO DE AUDIO (por hora)
#     # =====================
#     ("LAB_AUDIO", "Laboratorio de Audio",
#      "Alquiler de cabina de audio por hora (incluye 4 micrófonos, 2 mesas, 4 sillas, 2 auriculares, luces, entrega de archivos sin editar)",
#      2, "20.00", "Precio por hora"),
#
#     ("LAB_AUDIO", "Laboratorio de Audio",
#      "Alquiler de cabina de audio por hora (incluye 4 micrófonos, 2 mesas, 4 sillas, 2 auriculares, luces, cámara de video y trípode, entrega de archivos sin editar)",
#      2, "35.00", "Precio por hora"),
#
#     ("LAB_AUDIO", "Laboratorio de Audio",
#      "Alquiler de set fotográfico por hora (incluye trípode, luces, pantalla verde, blanca y negra, entrega de archivos sin editar)",
#      2, "20.00", "Precio por hora"),
#
#     ("LAB_AUDIO", "Laboratorio de Audio",
#      "Alquiler de set de video por hora (incluye trípode, luces, pantalla verde, blanca y negra, entrega de archivos sin editar)",
#      2, "20.00", "Precio por hora"),
#
#     ("LAB_AUDIO", "Laboratorio de Audio",
#      "Cámara extra",
#      2, "15.00", "Precio por hora"),
#
#     # =============================
#     # LABORATORIO DE EMPRENDIMIENTO (paquete, pero igual es ÍTEM)
#     # =============================
#     ("LAB_EMP", "Laboratorio de Emprendimiento",
#      "Alquiler de espacio de Laboratorio de Emprendimiento (1–2 horas, capacidad 32 personas, 32 sillas, 16 mesas ejecutivas, pantalla táctil, parqueadero)",
#      1, "100.00", "Paquete 1–2 horas (se usa cantidad = 1)"),
#
#     # ================================
#     # LABORATORIO DE FABRICACIÓN DIGITAL (por hora)
#     # ================================
#     ("LAB_FAB", "Laboratorio de Fabricación Digital",
#      "Bambula",
#      2, "1.25", "Precio por hora"),
#
#     ("LAB_FAB", "Laboratorio de Fabricación Digital",
#      "Corte láser Fusion",
#      2, "0.35", "Precio por hora"),
#
#     ("LAB_FAB", "Laboratorio de Fabricación Digital",
#      "Impresora 3D (1 filamento)",
#      2, "5.00", "Precio por hora"),
#
#     ("LAB_FAB", "Laboratorio de Fabricación Digital",
#      "Impresora 3D (4 filamentos)",
#      2, "5.00", "Precio por hora"),
#
#     ("LAB_FAB", "Laboratorio de Fabricación Digital",
#      "CNC ShopBot",
#      2, "20.00", "Precio por hora"),
#
#     ("LAB_FAB", "Laboratorio de Fabricación Digital",
#      "CNC Monopad",
#      2, "15.00", "Precio por hora"),
#
#     ("LAB_FAB", "Laboratorio de Fabricación Digital",
#      "Cortadora de vinil",
#      2, "20.00", "Precio por hora"),
#
#     ("LAB_FAB", "Laboratorio de Fabricación Digital",
#      "CNC Tormach",
#      2, "30.00", "Precio por hora"),
#
#     ("LAB_FAB", "Laboratorio de Fabricación Digital",
#      "Torno",
#      2, "20.00", "Precio por hora"),
#
#     ("LAB_FAB", "Laboratorio de Fabricación Digital",
#      "Máquina de coser digital",
#      2, "10.00", "Precio por hora"),
#
#     ("LAB_FAB", "Laboratorio de Fabricación Digital",
#      "Bordadora digital",
#      2, "8.00", "Precio por hora"),
#
#     # ===============
#     # SALÓN ÁGORA (por hora)
#     # ===============
#     ("AGORA", "Salón Ágora",
#      "Alquiler de espacio de Ágora (capacidad 70 personas, pantalla LED 3.84 x 1.22 m, 2 micrófonos parlantes, parqueadero, 1–2 horas)",
#      2, "200.00", "Precio por hora"),
# ]
#
#
# @transaction.atomic
# def seed_servicios_externos():
#     """
#     Borra los servicios de estos laboratorios y del Ágora
#     y los vuelve a crear según SERVICIOS_DATA.
#     """
#     codigos = ["LAB_MAT", "LAB_AUDIO", "LAB_EMP", "LAB_FAB", "AGORA"]
#
#     print("Borrando servicios existentes de LAB_MAT/LAB_AUDIO/LAB_EMP/LAB_FAB/AGORA...")
#     ServicioCatalogo.objects.filter(tipo_servicio__codigo__in=codigos).delete()
#     TipoServicio.objects.filter(codigo__in=codigos).delete()
#
#     tipos_cache = {}
#
#     for lab_cod, lab_nombre, serv_nombre, tipo_cobro, precio, obs in SERVICIOS_DATA:
#         ts = tipos_cache.get(lab_cod)
#         if ts is None:
#             ts = TipoServicio.objects.create(
#                 codigo=lab_cod,
#                 nombre=lab_nombre,
#                 descripcion=""
#             )
#             tipos_cache[lab_cod] = ts
#
#         ServicioCatalogo.objects.create(
#             tipo_servicio=ts,
#             nombre=serv_nombre,
#             tipo_cobro=tipo_cobro,
#             precio_base=Decimal(precio),
#             observacion=obs,
#         )
#
#     print("✔ Catálogo de servicios externos cargado correctamente.")
#
# seed_servicios_externos()


matricula = Matricula.objects.get(pk=4)
matricula.delete()