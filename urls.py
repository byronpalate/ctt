"""
URL configuration for sga_2023 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static


from ctt import commonviews, inscripciones, matriculas, fecha_evaluaciones, adm_periodos, pro_horarios, pro_asistencias, pro_planificacion, \
    adm_mallas, pro_aperturaclase, alu_automatricula, pro_clases, alu_finanzas, alu_notas, pro_evaluaciones, alu_asistencias, alu_horarios, \
    alu_cursoscomplementarios, adm_caja, alu_materias, finanzas, adm_facturas, printdoc, adm_recibopago, adm_notacredito, adm_valecaja, adm_recibo_caja, \
    adm_transferencias, adm_depositos, adm_tecnologicouniversidad, adm_depositoinscripcion, adm_carreras, api, mailbox, adm_coordinaciones, \
    adm_institucion, adm_colegios, adm_cursoscomplementarios, adm_evaluaciones, niveles, administrativos, adm_asignaturas, adm_modelosevaluativos, docentes, \
    adm_calculofinanzas, adm_pagosnivel, servicios, gestion_servicios

from ctt import commonviews, inscripciones, matriculas, fecha_evaluaciones, adm_periodos, pro_horarios, pro_asistencias, \
    pro_planificacion, \
    adm_mallas, pro_aperturaclase, alu_automatricula, pro_clases, alu_finanzas, alu_notas, pro_evaluaciones, \
    alu_asistencias, alu_horarios, \
    alu_cursoscomplementarios, adm_caja, alu_materias, finanzas, adm_facturas, printdoc, adm_recibopago, \
    adm_notacredito, adm_valecaja, adm_recibo_caja, \
    adm_transferencias, adm_depositos, adm_tecnologicouniversidad, adm_depositoinscripcion, adm_carreras, api, mailbox, \
    adm_coordinaciones, \
    adm_institucion, adm_colegios, adm_cursoscomplementarios, adm_evaluaciones, niveles, administrativos, \
    adm_asignaturas, adm_modelosevaluativos, docentes, \
    adm_calculofinanzas, adm_pagosnivel, adm_cliente

import django.views.static

urlpatterns = [

    path('admin/', admin.site.urls),
    path('', commonviews.panel),
    path('login', commonviews.login_user),
    path('logout', commonviews.logout_user),
    path('cu', commonviews.changeuser),
    path('cudu', commonviews.changeuserdu),
    path('cambiocoordinacion', commonviews.cambiocoordinacion),
    path('cambioperiodo', commonviews.cambioperiodo),
    path('account', commonviews.account),
    path('pass', commonviews.passwd),

    # path('adm_generacionbancos', adm_generacionbancos.view),
    # INSCRIPCIONES Y MATRICULAS d
    path('inscripciones', inscripciones.view),
    path('matriculas', matriculas.view),

    path('fecha_evaluaciones', fecha_evaluaciones.view),
    path('adm_periodos', adm_periodos.view),
    path('administrativos', administrativos.view),
    path('docentes', docentes.view),
    # PROFESORES
    path('pro_clases', pro_clases.view),
    path('pro_horarios', pro_horarios.view),
    path('pro_asistencias', pro_asistencias.view),
    path('pro_evaluaciones', pro_evaluaciones.view),


    path('pro_planificacion', pro_planificacion.view),



    path('pro_aperturaclase', pro_aperturaclase.view),


    path('alu_automatricula', alu_automatricula.view),
    path('alu_asistencias', alu_asistencias.view),

    path('alu_horarios', alu_horarios.view),

    path('alu_materias', alu_materias.view),
    path('alu_notas', alu_notas.view),

    path('alu_finanzas', alu_finanzas.view),

    path('adm_asignaturas', adm_asignaturas.view),
    path('adm_mallas', adm_mallas.view),
    path('adm_carreras', adm_carreras.view),
    path('adm_coordinaciones', adm_coordinaciones.view),


    path('alu_cursoscomplementarios', alu_cursoscomplementarios.view),




    path('adm_caja', adm_caja.view),
    path('finanzas', finanzas.view),
    path('adm_facturas', adm_facturas.view),
    path('adm_recibopago', adm_recibopago.view),
    path('adm_notacredito', adm_notacredito.view),
    path('adm_valecaja', adm_valecaja.view),
    path('adm_recibo_caja', adm_recibo_caja.view),
    path('adm_transferencias', adm_transferencias.view),
    path('adm_depositos', adm_depositos.view),
    path('adm_depositoinscripcion', adm_depositoinscripcion.view),
    path('adm_modelosevaluativos', adm_modelosevaluativos.view),


    # GESTION DE EVALUACION DE DOCENTES
    # API FOR THIRD PARTY APPS
    path('api', api.view),
    # ESTADISTICAS Y GRAFICOS
    # BIBLIOTECA

    # IMPRESION NEW STYLE
    # path(r'^print/(^<referencia>.+)/(^<idd>\d+)', printdoc.view),
    # url(r'^print/(?P<referencia>.+)/(?P<idd>\d+)$', 'ctt.printdoc.view'),
    path('print/<str:referencia>/<int:idd>', printdoc.view, name='printdoc-view'),

    # ESTUDIANTES CON BECA ASIGNADA (BECARIOS)

    # CALENDARIO DE ACTIVIDADES

    # CARRERAS
    path('adm_carreras', adm_carreras.view),
    # VINCULACION

    # PASANTIAS DE ESTUDIANTES

    path('mailbox', mailbox.view),
    # BOLSA LABORAL

    path('adm_institucion', adm_institucion.view),

    path('adm_cursoscomplementarios', adm_cursoscomplementarios.view),



    # COLEGIOS E INSTITUCIONES
    path('adm_colegios', adm_colegios.view),
    path('adm_tecnologicouniversidad', adm_tecnologicouniversidad.view),
    path('niveles', niveles.view),
    # PROYECTO INVESTIGACION



    #BECA EMERGENTE
    # path('personalprorrogafinanciamiento', personalprorrogafinanciamiento.view),
    # EVALUADORES

    # EXAMEN DE ORIENTACION PROFESIONAL



    path('adm_evaluaciones', adm_evaluaciones.view),
    path('adm_pagosnivel', adm_pagosnivel.view),
    path('adm_cliente', adm_cliente.view),
    path('servicios', servicios.view),
    path('gestion_servicios', gestion_servicios.view),



    # INVESTIGACION MEDICINA

    # LABORATORIOS


]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)