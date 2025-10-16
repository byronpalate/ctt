# coding=latin-1
import calendar
import json
import random
import string
from datetime import datetime, timedelta, date
from django.utils import timezone

from django.contrib.auth import authenticate, logout, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models.aggregates import Sum
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render


from decorators import secure_module, last_access, db_selector
from settings import ALUMNOS_GROUP_ID, SEXO_FEMENINO, SEXO_MASCULINO, CONTACTO_EMAIL, ENVIO_CORREO_INICIO_SESION,\
    PIE_PAGINA_CREATIVE_COMMON_LICENCE, CHEQUEAR_CORREO, PROFESORES_GROUP_ID, EMPLEADORES_GRUPO_ID, TIPO_PERIODO_GRADO,\
NOTIFICACION_DEUDA, ACTUALIZAR_FOTO_PROFESOR, ACTUALIZAR_FOTO_ADMINISTRATIVOS, ARCHIVO_TIPO_PUBLICO, ACTUALIZAR_FOTO_ALUMNOS
from ctt.forms import PersonaForm, CambioClaveForm, CargarFotoForm, CambioPerfilForm, CambioCoordinacionForm, \
    CambioPeriodoForm, CambioClaveSimpleForm,FormTerminos
from ctt.funciones import generar_nombre, log, fechatope, ok_json, bad_json, url_back, generar_clave, \
    convertir_fecha
from ctt.models import Persona, Periodo, FotoPersona, Noticia, Profesor, Inscripcion, Archivo,  GruposModulos, mi_institucion, \
Persona, Incidencia, PerfilUsuario, Modulo, Encuesta, Matricula, DatoTransferenciaDeposito, years_ago, Materia, Actividad,\
    InscripcionFlags, Reporte

from ctt.tasks import send_mail


from django.db.models import Prefetch


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',').first()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# AUTENTIFICA EL USUARIO
# @db_selector
@transaction.atomic()
def login_user(request):
    global ex
    if request.method == 'POST':

        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'login':
                try:
                    client_address = get_client_ip(request)
                    browser = request.POST['navegador']
                    os = request.POST['os']
                    screensize = request.POST['screensize']
                    user = authenticate(username=request.POST['user'], password=request.POST['pass'])
                    if user is not None:
                        if not user.is_active:
                            return bad_json(mensaje=u'Login fallido, usuario no activo.')
                        else:
                            if Persona.objects.filter(usuario=user).exists():
                                persona = Persona.objects.filter(usuario=user).first()
                                perfilprincipal = persona.perfilusuario_principal()
                                if perfilprincipal:
                                    request.session['persona'] = persona
                                    request.session['ultimo_acceso'] = datetime.now()
                                    request.session['alertanoticias'] = False
                                    request.session['perfiles'] = persona.mis_perfilesusuarios()
                                    request.session['coordinaciones'] = coordinaciones = persona.lista_coordinaciones()
                                    request.session['coordinacionseleccionada'] = coordinacion = coordinaciones.first() if coordinaciones else None
                                    request.session['carreras'] = carreras = persona.lista_carreras_coordinacion(coordinacion) if coordinacion else None
                                    request.session['carreraseleccionada'] = carreras.first() if carreras else None
                                    login(request, user)
                                    log(u'Login con exito: %s - %s - %s - %s' % (persona, browser, os, client_address), request, "add")
                                    if ENVIO_CORREO_INICIO_SESION:
                                        send_mail(subject='Login exitoso CTT.',
                                                  html_template='emails/loginexito.html',
                                                  data={'bs': browser, 'ip': client_address, 'os': os, 'screensize': screensize},
                                                  recipient_list=[persona])
                                    request.session['perfilprincipal'] = perfilprincipal
                                    if perfilprincipal.es_profesor():
                                        profesor = perfilprincipal.profesor
                                        da = profesor.datos_habilitacion()
                                        da.habilitado = False
                                        da.clavegenerada = generar_clave(4)
                                        da.save(request)
                                    if perfilprincipal.es_estudiante():
                                        perfilprincipal.establecer_estudiante_principal()
                                    return ok_json({"sessionid": request.session.session_key})
                                else:
                                    return bad_json(mensaje=u'Login fallido, no existen perfiles activos.')
                            else:
                                log(u'Login fallido, no existe el usuario: %s' % request.POST['user'], request, "add")
                                return bad_json(mensaje=u'Login fallido, no existe el usuario.')
                    else:
                        if Persona.objects.filter(usuario__username=request.POST.get('user', '').lower()).exists():
                            persona = Persona.objects.filter(usuario__username=((request.POST['user']).lower())).first()
                            if ENVIO_CORREO_INICIO_SESION:
                                send_mail(subject='Login fallido CTT.',
                                          html_template='emails/loginfallido.html',
                                          data={'bs': browser, 'ip': client_address, 'os': os, 'screensize': screensize},
                                          recipient_list=[persona])
                        return bad_json(mensaje=u'Login fallido, credenciales incorrectas.')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(mensaje=u'Login fallido, Error en el sistema.')

            if action == 'cambioclave':
                try:
                    form = CambioClaveForm(request.POST)
                    if form.is_valid():
                        persona = request.session['persona']
                        usuario = persona.usuario
                        if form.cleaned_data['nueva'] == form.cleaned_data['anterior']:
                            return bad_json(mensaje=u"No puede volver a utilizar su clave anterior, por favor Ingrese otra.")
                        if not usuario.check_password(form.cleaned_data['anterior']):
                            return bad_json(mensaje=u"Clave anterior no coincide.")
                        usuario.set_password(form.cleaned_data['nueva'])
                        usuario.save()
                        persona.clave_cambiada()
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(mensaje=u"No puedo cambiar la clave.")

        return bad_json(error=0)
    else:
        data = {"title": u"Login", "background": random.randint(1, 6)}
        data['request'] = request
        hoy = datetime.now().date()
        # data['noticias'] = Noticia.objects.filter(desde__lte=hoy, hasta__gte=hoy, imagen__isnull=True, tipo__in=[1, 2], estado=2).order_by('-desde', 'id').using(request.session['db_name'])[0:5]
        data['noticias'] = Noticia.objects.filter(desde__lte=hoy, hasta__gte=hoy, imagen__isnull=True, tipo__in=[1, 2], estado=2).order_by('-desde', 'id')
        data['noticiasgraficas'] = Noticia.objects.filter(desde__lte=hoy, hasta__gte=hoy, imagen__isnull=False, tipo__in=[1, 2], estado=2).order_by('-desde', 'id')
        data['currenttime'] = datetime.now()
        data['institucion'] = mi_institucion()
        data['contacto_email'] = CONTACTO_EMAIL
        request.session['alertanoticias'] = True
        return render(request, "login.html", data)


# CIERRA LA SESSION DEL USUARIO
def logout_user(request):
    global ex
    if request.method == 'POST':
        try:
            logout(request)
            return ok_json()
        except:
            return bad_json(error=1)
    else:
        logout(request)
        return HttpResponseRedirect("/")


# ADICIONA LOS DATOS DEL USUARIO A LA SESSION
def adduserdata(request, data):
    # ADICIONA EL USUARIO A LA SESSION
    if 'persona' not in request.session:
        if not request.user.is_authenticated():
            raise Exception('Usuario no autentificado en el sistema')
        request.session['persona'] = Persona.objects.get(usuario=request.user)
    else:
        request.session['persona'] = Persona.objects.get(pk=request.session['persona'].id)
    data['persona'] = request.session['persona']
    data['session_key'] = request.session.session_key
    data['check_session'] = True
    persona = data['persona']
    request.session['ultimo_acceso'] = datetime.now()
    if request.method == 'GET':
        if 'screenwidth' in request.GET:
            request.session['screenwidth'] = request.GET['screenwidth']
        else:
            if 'screenwidth' not in request.session:
                request.session['screenwidth'] = 800
        data['screenwidth'] = request.session['screenwidth']
        if 'ret' in request.GET:
            data['ret'] = request.GET['ret']
        if 'mensj' in request.GET:
            data['mensj'] = request.GET['info']
        if 'info' in request.GET:
            data['info'] = request.GET['info']
    else:
        if 'screenwidth' in request.POST:
            request.session['screenwidth'] = request.POST['screenwidth']
        else:
            if 'screenwidth' not in request.session:
                request.session['screenwidth'] = 800
    data['currenttime'] = datetime.now()
    data['sessionclientid'] = request.session.session_key
    data['remoteaddr'] = get_client_ip(request)
    data['pie_pagina_creative_common_licence'] = PIE_PAGINA_CREATIVE_COMMON_LICENCE
    data['chequear_correo'] = CHEQUEAR_CORREO
    if 'alertanoticias' not in request.session:
        request.session['alertanoticias'] = False
    if 'periodos_todos' not in request.session:
        request.session['periodos_todos'] = Periodo.objects.all()
    if 'info' in request.session:
        data['info'] = request.session['info']
        del request.session['info']
    data['periodos_todos'] = periodos = request.session['periodos_todos']
    if 'perfilprincipal' not in request.session:
        request.session['perfilprincipal'] = persona.perfilusuario_principal()
    else:
        request.session['perfilprincipal'] = PerfilUsuario.objects.get(pk=request.session['perfilprincipal'].id)
    data['perfilprincipal'] = perfilprincipal = request.session['perfilprincipal']
    if 'grupos_usuarios' not in request.session:
        if perfilprincipal.es_profesor():
            request.session['grupos_usuarios'] = request.user.groups.filter(id=PROFESORES_GROUP_ID)
        elif perfilprincipal.es_estudiante():
            request.session['grupos_usuarios'] = request.user.groups.filter(id=ALUMNOS_GROUP_ID)
        elif perfilprincipal.es_empleador():
            request.session['grupos_usuarios'] = request.user.groups.filter(id=EMPLEADORES_GRUPO_ID)
        else:
            request.session['grupos_usuarios'] = request.user.groups.exclude(id__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID])
    data['grupos_usuarios'] = request.session['grupos_usuarios']
    if perfilprincipal.es_estudiante():
        inscripcion = perfilprincipal.inscripcion
        matricula = inscripcion.matricula()
        if inscripcion.tiene_deuda_vencida():
            data['notificar_deuda'] = NOTIFICACION_DEUDA if inscripcion.mis_flag().notificardeuda else False
            if 'notificar_deuda' not in request.session:
                request.session['notificar_deuda'] = False
        if matricula:
            periodo = matricula.nivel.periodo
            request.session['periodo'] = periodo
            data['periodos'] = [matricula.nivel.periodo]
        else:
            ultimamatricula = inscripcion.ultima_matricula()
            if ultimamatricula:
                periodo = ultimamatricula.nivel.periodo
                request.session['periodo'] = periodo
                data['periodos'] = [ultimamatricula.nivel.periodo]
            else:
                data['periodos'] = None
        if data['periodos']:
            request.session['periodo'] = data['periodos'].first()
        else:
            request.session['periodo'] = None
    elif perfilprincipal.es_empleador():
        pass
    else:
        data['periodos'] = periodos
        if 'coordinaciones' in request.session:
            data['coordinaciones'] = request.session['coordinaciones']
        else:
            data['coordinaciones'] = None
        if 'coordinacionid' in request.GET:
            request.session['coordinacionseleccionada'] = coordinacion = request.session['coordinaciones'].get(id=int(request.GET['coordinacionid']))
            request.session['carreras'] = carreras = persona.lista_carreras_coordinacion(coordinacion)
            request.session['carreraseleccionada'] = carrera = carreras.first() if carreras else None
        else:
            if 'coordinacionseleccionada' in request.session:
                coordinacion = request.session['coordinacionseleccionada']
            else:
                coordinacion = None
        if 'carreras' in request.session:
            data['carreras'] = request.session['carreras']
        else:
            data['carreras'] = None
        try:
            if 'carreraid' in request.GET:
                request.session['carreraseleccionada'] = carrera = request.session['carreras'].get(
                    id=int(request.GET['carreraid']))
            else:
                carrera = request.session['carreraseleccionada']
        except:
            request.session['carreras'] = carreras = persona.lista_carreras_coordinacion(coordinacion)
            request.session['carreraseleccionada'] = carrera = carreras.first() if carreras else None
        data['coordinacionseleccionada'] = coordinacion
        data['carreraseleccionada'] = carrera
    if 'periodo' not in request.session:
        if Periodo.objects.filter(tipo=TIPO_PERIODO_GRADO, inicio__lte=datetime.now().date(), activo=True, fin__gte=datetime.now().date()).exists():
            request.session['periodo'] = Periodo.objects.filter(tipo=TIPO_PERIODO_GRADO, activo=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date()).first()
        elif Periodo.objects.filter(tipo=TIPO_PERIODO_GRADO, activo=True, fin__lte=datetime.now().date()).exists():
            request.session['periodo'] = Periodo.objects.filter(tipo=TIPO_PERIODO_GRADO, activo=True, fin__lte=datetime.now().date()).first()
        else:
            request.session['periodo'] = Periodo.objects.filter(tipo=TIPO_PERIODO_GRADO, activo=True).order_by('-fin').first()
    else:
        if request.session['periodo']:
            request.session['periodo'] = Periodo.objects.get(pk=request.session['periodo'].id)
    data['periodo'] = request.session['periodo']
    data['institucion'] = request.session['institucion'] = mi_institucion()
    if 'ruta' not in request.session:
        request.session['ruta'] = [['/', 'Inicio']]
    rutalista = request.session['ruta']
    if request.path:
        if Modulo.objects.filter(url=request.path[1:]).exists():
            modulo = Modulo.objects.filter(url=request.path[1:]).first()
            url = ['/' + modulo.url, modulo.nombre]
            if rutalista.count(url) <= 0:
                if rutalista.__len__() >= 8:
                    b = rutalista[1]
                    rutalista.remove(b)
                    rutalista.append(url)
                else:
                    rutalista.append(url)
            request.session['ruta'] = rutalista
    data["ruta"] = rutalista
    data['permite_modificar'] = True
    data['puede_ver_botoncancelar'] = True
    data['puede_ver_botonsalir'] = False
    if request.path[1:]:
        if Archivo.objects.filter(modulo=request.path[1:]).exists():
            data['archivoayuda'] = Archivo.objects.filter(modulo=request.path[1:]).first()


# PANEL PRINCIPAL DEL SISTEMA
@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def panel(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

        return bad_json(error=0)
    else:
        try:
            data['title'] = u'Bienvenidos a CTT'
            periodo = request.session['periodo']
            hoy = datetime.now()
            # ESTUDIANTES
            perfilprincipal = request.session['perfilprincipal']
            if 'paginador' in request.session:
                del request.session['paginador']
            if perfilprincipal.es_estudiante():
                data['inscripcion'] = inscripcion = perfilprincipal.inscripcion
                data['reporte_0'] = obtener_reporte('ficha_preinscripcion')
                data['imprimirficha'] = (datetime(inscripcion.fecha.year, inscripcion.fecha.month, inscripcion.fecha.day, 0, 0, 0) + timedelta(days=30)).date() > datetime.now().date()
                data['ofertasdisponibles'] = inscripcion.tiene_ofertas_disponibles()
                data['entrevistaspendientes'] = inscripcion.tiene_entrevistas_pendientes()
                data['proceso'] = None
                data['es_profesor'] = False
                data['necesita_evaluarse'] = False
                data['incidencias'] = []

                misgrupos = GruposModulos.objects.filter(grupo__id=ALUMNOS_GROUP_ID).distinct()
                modulos_activos = Prefetch('modulos', queryset=Modulo.objects.filter(activo=True).order_by('nombre'), to_attr='modulos_activos')
                data['grupos_con_mods'] = (misgrupos.order_by('grupo__name').prefetch_related(modulos_activos))
                grupos = persona.usuario.groups.filter(id__in=[ALUMNOS_GROUP_ID])

                if periodo:
                    matricula = inscripcion.matricula_periodo(periodo)
                    data['proceso'] = proceso = periodo.proceso_evaluativo()
                    data['procesodocente'] = procesodocente = periodo.proceso_evaluativo_docente()
                    data['necesita_evaluar'] = False
                    tiene_deuda = inscripcion.tiene_deuda_vencida()
                    tiene_notificacion = inscripcion.mis_flag().notificardeuda
                    evaluar = True
                    if tiene_notificacion and tiene_deuda:
                        evaluar = False

                data['datosincompletos'] = persona.datos_incompletos()
                data['hojavidallena'] = False if persona.hojavida_llena() else True
                # NOTICIAS Y AVISOS DEL DIA
                data['noticias'] = Noticia.objects.filter(desde__lte=hoy, hasta__gte=hoy, imagen=None, tipo__in=[1, 2, 4], estado=2).order_by('-desde', 'id')[0:5]
                data['noticiasgraficas'] = Noticia.objects.filter(desde__lte=hoy, hasta__gte=hoy, imagen__isnull=False, tipo__in=[1, 2, 4], estado=2).order_by('-desde', 'id')
                encuestas = encuesta(grupos, persona)
                if encuestas:
                    return HttpResponseRedirect('/com_responderencuestas?action=responder&id=' + str(encuestas.first().id))
            elif perfilprincipal.es_empleador():
                data['empleador'] = empleador = perfilprincipal.empleador
                data['proceso'] = None
                data['es_profesor'] = False
                data['necesita_evaluarse'] = False
                data['incidencias'] = []
                misgrupos = GruposModulos.objects.filter(grupo__id=EMPLEADORES_GRUPO_ID).distinct()
                modulos_activos = Prefetch('modulos', queryset=Modulo.objects.filter(activo=True).order_by('nombre'), to_attr='modulos_activos')
                data['grupos_con_mods'] = (misgrupos.order_by('grupo__name').prefetch_related(modulos_activos))
                grupos = persona.usuario.groups.filter(id__in=[EMPLEADORES_GRUPO_ID])
                data['datosincompletos'] = persona.datos_incompletos()
                data['hojavidallena'] = False
                # NOTICIAS Y AVISOS DEL DIA
                data['noticias'] = []
                data['noticiasgraficas'] = []
                encuestas = encuesta(grupos, persona)
                if encuestas:
                    return HttpResponseRedirect('/com_responderencuestas?action=responder&id=' + str(encuestas.first().id))
            elif perfilprincipal.es_profesor():
                misgrupos = GruposModulos.objects.filter(grupo__id=PROFESORES_GROUP_ID).distinct()
                modulos_activos = Prefetch('modulos', queryset=Modulo.objects.filter(activo=True).order_by('nombre'), to_attr='modulos_activos')
                data['grupos_con_mods'] = (misgrupos.order_by('grupo__name').prefetch_related(modulos_activos))
                grupos = persona.usuario.groups.filter(id__in=[PROFESORES_GROUP_ID])
                profesor = perfilprincipal.profesor
                data['es_profesor'] = True
                data['necesita_evaluarse'] = False
                # data['proceso'] = proceso = periodo.proceso_evaluativo()
                data['proceso'] = None
                data['materias_sin_planificacion'] = Materia.objects.filter(Q(planificacionmateria__isnull=True) | Q(planificacionmateria__aprobado=False), profesormateria__profesor=profesor, profesormateria__principal=True, cerrado=False).exists()
                data['solicitud_notas'] = Materia.objects.filter(solicitudingresonotasatraso__fechalimite__gte=datetime.now().date(), profesormateria__profesor=profesor, profesormateria__principal=True, solicitudingresonotasatraso__estado=2).distinct()

                # NOTICIAS Y AVISOS DEL DIA
                data['noticias'] = Noticia.objects.filter(desde__lte=hoy, hasta__gte=hoy, imagen=None, tipo__in=[1, 2, 5], estado=2).order_by('-desde', 'id')[0:5]
                data['noticiasgraficas'] = Noticia.objects.filter(desde__lte=hoy, hasta__gte=hoy, imagen__isnull=False, tipo__in=[1, 2, 5], estado=2).order_by('-desde', 'id')
                encuestas = encuesta(grupos, persona)
                if encuestas:
                    return HttpResponseRedirect('/com_responderencuestas?action=responder&id=' + str(encuestas.first().id))
            else:
                misgrupos = GruposModulos.objects.filter(grupo__in=persona.usuario.groups.exclude(id__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID, EMPLEADORES_GRUPO_ID])).distinct()
                modulos_activos = Prefetch('modulos', queryset=Modulo.objects.filter(activo=True).order_by('nombre'), to_attr='modulos_activos')
                data['grupos_con_mods'] = (misgrupos.order_by('grupo__name').prefetch_related(modulos_activos))
                grupos = persona.usuario.groups.exclude(id__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID])
                if persona.es_administrador():
                    data['incidencias'] = Incidencia.objects.filter(cerrada=False).order_by('-lecciongrupo__fecha')[:25]
                else:
                    data['incidencias'] = Incidencia.objects.filter(cerrada=False, tipo__responsabletipoincidencia__responsable=persona).order_by('-lecciongrupo__fecha')[:25]
                # NOTICIAS Y AVISOS DEL DIA
                data['noticias'] = Noticia.objects.filter(desde__lte=hoy, hasta__gte=hoy, imagen=None, tipo__in=[1, 2, 3], estado=2).order_by('-desde', 'id')[0:5]
                data['noticiasgraficas'] = Noticia.objects.filter(desde__lte=hoy, hasta__gte=hoy, imagen__isnull=False, tipo__in=[1, 2, 3], estado=2).order_by('-desde', 'id')
                if perfilprincipal.es_administrativo():
                    administrativo = perfilprincipal.administrativo
                encuestas = encuesta(grupos, persona)
                if encuestas:
                    return HttpResponseRedirect('/com_responderencuestas?action=responder&id=' + str(encuestas.first().id))
            data['grupos'] = misgrupos
            # LISTADO DE ESTUDIANTES Y PROFESORES QUE ESTAN DE CUMPLEAAÑOS
            data['ins_cumple'] = Inscripcion.objects.filter(persona__nacimiento__day=hoy.day, persona__nacimiento__month=hoy.month, matricula__nivel__fin__gte=hoy).distinct()
            data['prof_cumple'] = Profesor.objects.filter(persona__nacimiento__day=hoy.day, persona__nacimiento__month=hoy.month, activo=True, profesormateria__materia__nivel__fin__gte=hoy).distinct()
            data['actividades'] =  actividades = Actividad.objects.filter(inicio__lte=hoy, fin__gte=hoy)
            # MODULO DE BIBLIOTECA
            data['institucion'] = mi_institucion()
            data['tienefacturasvencidas'] = False
            data['tienefacturaspendientes'] = False
            data['notificadofacturasvencidas'] = False
            data['archivos'] = Archivo.objects.filter(Q(tipo__id=ARCHIVO_TIPO_PUBLICO) | Q(grupo__in=grupos),  interfaz=True).distinct()
            if 'info' in request.GET:
                data['info'] = request.GET['info']
            data['alertanoticias'] = request.session['alertanoticias']
            request.session['alertanoticias'] = True
            if perfilprincipal.es_estudiante():
                if inscripcion.egresado_set.exists() and not persona.seg_graduado   :
                    return HttpResponseRedirect('/alu_seggraduados')
                data['reporte_0'] = obtener_reporte('carnet')
                data['actualizar_foto'] = ACTUALIZAR_FOTO_ALUMNOS
                if persona.tiene_deuda_vencida():
                    inscripcionflag = InscripcionFlags.objects.filter(inscripcion_id=perfilprincipal.inscripcion.id).first()
                    if inscripcionflag.notificardeuda:
                        request.session['notificar_deuda'] = NOTIFICACION_DEUDA
                        data['notificar_deuda'] = NOTIFICACION_DEUDA
                    else:
                        request.session['notificar_deuda'] = False
                        data['notificar_deuda'] = False
                else:
                    request.session['notificar_deuda'] = False
                    data['notificar_deuda'] = False


            if perfilprincipal.es_administrativo():

                # data['reporte_1'] = obtener_reporte('carnet_admin')
                data['reporte_1'] = None
                data['actualizar_foto'] = ACTUALIZAR_FOTO_ADMINISTRATIVOS
                if persona.tiene_deuda_vencida():
                    request.session['notificar_deuda'] = False
                    data['notificar_deuda'] = False

            if perfilprincipal.es_profesor():
                data['actualizar_foto'] = ACTUALIZAR_FOTO_PROFESOR
                data['reporte_2'] = obtener_reporte('carnet_profesor')
                request.session['notificar_deuda'] = False
                data['notificar_deuda'] = False


            return render(request, "panel.html", data)
        except Exception as ex:
            return HttpResponseRedirect('/logout')


def encuesta(grupo, persona):
    return Encuesta.objects.filter(Q(grupos__in=grupo) | Q(personaencuesta__persona=persona), obligatoria=True, activa=True).exclude(respuestaencuesta__persona=persona).distinct()

# DATOS DE LA CUENTA
@login_required(login_url='/login')
@last_access
@transaction.atomic()
def account(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodoactualizaciondatos = None
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'cargarfoto':
                try:
                    form = CargarFotoForm(request.POST, request.FILES)
                    if form.is_valid():
                        foto = persona.foto()
                        newfile = request.FILES['foto']
                        newfile._name = generar_nombre("foto_", newfile._name)
                        if foto:
                            foto.foto = newfile
                        else:
                            foto = FotoPersona(persona=persona,
                                               foto=newfile)
                        foto.save(request)
                        make_thumb_picture(persona)
                        make_thumb_fotopersona(persona)
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(mensaje=u"La imagen seleccionada no cumple los requisitos, de tamaño o formato o hubo un error al guardar fichero.")

            if action == 'aceptar':
                try:
                    tipoacuer=TipoTerminosAcuerdos.objects.get(pk=request.POST['idter'])
                    form = FormTerminos(request.POST, request.FILES)
                    if form.is_valid():
                        if not AceptacionTerminosAcuerdos.objects.filter(persona=persona, tipoacuerdo=tipoacuer):
                            terminos = AceptacionTerminosAcuerdos(persona=persona,
                                                                  tipoacuerdo=tipoacuer,
                                                                  fechaaceptacion=datetime.now())
                            terminos.save()

                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json()


            if action == 'actualizar':
                try:
                    form = PersonaForm(request.POST,request.FILES)
                    if form.is_valid():
                        persona.nacimiento = form.cleaned_data['nacimiento']
                        persona.sexo = form.cleaned_data['sexo']
                        persona.nacionalidad = form.cleaned_data['nacionalidad']
                        persona.paisnac = form.cleaned_data['paisnac']
                        persona.provincianac = form.cleaned_data['provincianac']
                        persona.cantonnac = form.cleaned_data['cantonnac']
                        persona.parroquianac = form.cleaned_data['parroquianac']
                        persona.pais = form.cleaned_data['pais']
                        persona.provincia = form.cleaned_data['provincia']
                        persona.canton = form.cleaned_data['canton']
                        persona.parroquia = form.cleaned_data['parroquia']
                        persona.sector = form.cleaned_data['sector']
                        persona.direccion = form.cleaned_data['direccion']
                        persona.direccion2 = form.cleaned_data['direccion2']
                        persona.referencia = form.cleaned_data['referencia']
                        persona.num_direccion = form.cleaned_data['num_direccion']
                        persona.telefono = form.cleaned_data['telefono']
                        persona.telefono_conv = form.cleaned_data['telefono_conv']
                        persona.email = form.cleaned_data['email']
                        persona.blog = form.cleaned_data['blog']
                        persona.twitter = form.cleaned_data['twitter']
                        persona.sangre = form.cleaned_data['sangre']
                        # persona.tipolicencia = form.cleaned_data['tipolicencia']
                        persona.estadocivil = form.cleaned_data['estadocivil']
                        persona.save(request)
                        perfil = persona.mi_perfil()
                        perfil.raza = form.cleaned_data['etnia']
                        perfil.nacionalidadindigena = form.cleaned_data['nacionalidadindigena']
                        perfil.save(request)
                        datosextension = persona.datos_extension()
                        datosextension.telefonoemergencia = form.cleaned_data['telefonoemergencia']
                        datosextension.contactoemergencia = form.cleaned_data['contactoemergencia']
                        datosextension.relacioncontactoemergencia = form.cleaned_data['relacioncontactoemergencia']
                        datosextension.emailcontactoemergencia = form.cleaned_data['emailcontactoemergencia']
                        datosextension.save(request)
                        request.session['persona'] = persona
                        perfilprincipal = request.session['perfilprincipal']
                        if perfilprincipal.es_estudiante():
                            inscripcion = perfilprincipal.inscripcion
                            inscripcion.proyectodevida = form.cleaned_data['proyectodevida']
                            inscripcion.save(request)
                            if DATOS_INTEGRADORES and periodoactualizaciondatos:
                                periodoactualizaciondatos.confirmar_datos(inscripcion, personales=True)
                        if perfilprincipal.es_profesor():
                            profesor = perfilprincipal.profesor
                            profesor.nivelescalafon = form.cleaned_data['nivelescalafon']
                            profesor.dedicacion = form.cleaned_data['dedicacion']
                            profesor.orcid = form.cleaned_data['orcid']
                            profesor.perfilgs = form.cleaned_data['perfilgs']
                            profesor.perfilacademia = form.cleaned_data['perfilacademia']
                            profesor.perfilscopus = form.cleaned_data['perfilscopus']
                            profesor.perfilmendeley = form.cleaned_data['perfilmendeley']
                            profesor.perfilresearchgate = form.cleaned_data['perfilresearchgate']
                            profesor.indicehautor = form.cleaned_data['indicehautor']
                            profesor.nivel_ingles = form.cleaned_data['nivel_ingles']
                            profesor.save(request)
                            cedula = persona.cedula_doc()
                            newfile = request.FILES["documentoidentificacion"]
                            newfile._name = generar_nombre("documentoidentificacion", newfile._name)
                            if cedula:
                                cedula.cedula = newfile
                                cedula.save(request)
                            else:
                                cedula = CedulaPersona(persona=persona, cedula=newfile)
                                cedula.save(request)
                            perfil = profesor.persona.mi_perfil_docente()
                            perfil.raza = form.cleaned_data['etnia']
                            perfil.nacionalidadindigena = form.cleaned_data['nacionalidadindigena']
                            perfil.tienediscapacidad = form.cleaned_data['tienediscapacidad']
                            perfil.tipodiscapacidad = form.cleaned_data['tipodiscapacidad']
                            perfil.porcientodiscapacidad = form.cleaned_data['porcientodiscapacidad']
                            perfil.carnetdiscapacidad = form.cleaned_data['carnetdiscapacidad']
                            perfil.save(request)
                            if DATOS_INTEGRADORES and periodoactualizaciondatos:
                                periodoactualizaciondatos.confirmar_datos_profesor(profesor, personales=True)
                        if perfilprincipal.es_administrativo():
                            administrativo = perfilprincipal.administrativo
                            if DATOS_INTEGRADORES and periodoactualizaciondatos:
                                periodoactualizaciondatos.confirmar_datos_administrativo(administrativo, personales=True)
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'cargarfoto':
                try:
                    data['title'] = u"Cargar foto"
                    form = CargarFotoForm()
                    data['form'] = form
                    return render(request, "cargarfoto.html", data)
                except Exception as ex:
                    pass

            if action == 'aceptar':
                try:
                    data['title'] = u'Terminos y Condiciones'
                    data['termino'] = TipoTerminosAcuerdos.objects.get(pk=request.GET['id'])
                    form = FormTerminos()
                    data['form'] = form
                    return render(request, "adm_terminosycondiciones/aceptar.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Modificar datos de cuenta'
                personasession = request.session['persona']
                persona = Persona.objects.get(pk=personasession.id)
                perfil = persona.mi_perfil()
                personaextension = persona.datos_extension()
                data['title'] = u'Modificar datos de cuenta'
                form = PersonaForm(initial={'nombre1': persona.nombre1,
                                            'nombre2': persona.nombre2,
                                            'apellido1': persona.apellido1,
                                            'apellido2': persona.apellido2,
                                            'cedula': persona.cedula,
                                            'pasaporte': persona.pasaporte,
                                            'nacimiento': persona.nacimiento,
                                            'nacionalidad': persona.nacionalidad,
                                            'paisnac': persona.paisnac,
                                            'provincianac': persona.provincianac,
                                            'cantonnac': persona.cantonnac,
                                            'parroquianac': persona.parroquianac,
                                            'sexo': persona.sexo,
                                            'pais': persona.pais,
                                            'provincia': persona.provincia,
                                            'canton': persona.canton,
                                            'parroquia': persona.parroquia,
                                            'sector': persona.sector,
                                            'direccion': persona.direccion,
                                            'direccion2': persona.direccion2,
                                            'referencia': persona.referencia,
                                            'num_direccion': persona.num_direccion,
                                            'telefono': persona.telefono,
                                            'libretamilitar': persona.libretamilitar,
                                            'telefono_conv': persona.telefono_conv,
                                            'email': persona.email,
                                            'blog': persona.blog,
                                            'twitter': persona.twitter,
                                            'emailinst': persona.emailinst,
                                            'etnia': perfil.raza,
                                            'nacionalidadindigena': perfil.nacionalidadindigena,
                                            'estadocivil': persona.estadocivil,
                                            'sangre': persona.sangre,
                                            "contactoemergencia": personaextension.contactoemergencia,
                                            "relacioncontactoemergencia": personaextension.relacioncontactoemergencia,
                                            "emailcontactoemergencia": personaextension.emailcontactoemergencia,
                                            "telefonoemergencia": personaextension.telefonoemergencia,
                                            "tipolicencia": persona.tipolicencia})
                form.editar(persona)
                if not perfilprincipal.profesor:
                    form.sin_emailinst()
                    form.del_campos_docente()
                else:
                    form.es_docente(perfilprincipal.profesor)
                form.solo_estudiante(perfilprincipal)
                data['form'] = form
                data['subircurriculum'] = not persona.es_estudiante()
                data['persona'] = persona
                data['nacionalidad_indigena_id'] = NACIONALIDAD_INDIGENA_ID
                data['email_domain'] = EMAIL_DOMAIN
                data['email_domain_estudiante'] = EMAIL_DOMAIN_ESTUDIANTES
                data['pais_ecuador_id'] = PAIS_ECUADOR_ID
                if perfilprincipal.es_estudiante() and DATOS_INTEGRADORES:
                    inscripcion = perfilprincipal.inscripcion
                if perfilprincipal.es_profesor() and persona.profesor().validoth:
                    data['permite_modificar'] = False
                return render(request, "account.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')

# CAMBIO CLAVES
@login_required(login_url='/login')
@last_access
@transaction.atomic()
def passwd(request):
    global ex
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'changepass':
                try:
                    form = CambioClaveForm(request.POST)
                    if form.is_valid():
                        persona = request.session['persona']
                        usuario = persona.usuario
                        if form.cleaned_data['nueva'] == form.cleaned_data['anterior']:
                            return bad_json(mensaje=u"No puede volver a utilizar su clave anterior, por favor ingrese otra.")
                        if not usuario.check_password(form.cleaned_data['anterior']):
                            return bad_json(mensaje=u"Clave anterior no coincide.")
                        usuario.set_password(form.cleaned_data['nueva'])
                        usuario.save()
                        persona.clave_cambiada()
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(mensaje=u"No puedo cambiar la clave.")

        return bad_json(error=0)
    else:
        try:
            data = {}
            adduserdata(request, data)
            data['title'] = u'Cambio de clave'
            data['form'] = CambioClaveSimpleForm()
            persona = data['persona']
            data['cambio_clave_obligatorio'] = persona.necesita_cambiar_clave()
            data['puede_ver_botoncancelar'] = False if persona.necesita_cambiar_clave() else True
            data['puede_ver_botonsalir'] = False if not persona.necesita_cambiar_clave() else True
            return render(request, "changepass.html", data)
        except Exception as ex:
            return HttpResponseRedirect('/')


# CAMBIO DE USUARIO
@login_required(login_url='/login')
@transaction.atomic()
def changeuser(request):
    try:
        if request.method == 'POST':
            try:
                global ex
                data = {}
                adduserdata(request, data)
                persona = data['persona']
                if not persona.usuario.is_superuser:
                    return bad_json(error=4)
                user = User.objects.get(pk=request.POST['id'])
                if not user.is_active:
                    return bad_json(mensaje=u'El usuario se encuenta desactivado.')
                nuevapersona = Persona.objects.get(usuario__id=user.id)
                perfilpersona = nuevapersona.perfilusuario_principal()
                if not perfilpersona:
                    return bad_json(mensaje=u'El usuario no tiene perfiles activos.')
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                log(u'%s - entro como este usuario: %s' % (persona, user), request, "add")
                logout(request)
                login(request, user)
                request.session['persona'] = nuevapersona
                request.session['alertanoticias'] = False
                request.session['perfiles'] = nuevapersona.lista_perfiles()
                request.session['perfilprincipal'] = perfilpersona
                request.session['coordinaciones'] = coordinaciones = nuevapersona.lista_coordinaciones()
                request.session['coordinacionseleccionada'] = coordinacion = coordinaciones.first() if coordinaciones else None
                request.session['carreras'] = carreras = nuevapersona.lista_carreras_coordinacion(coordinacion) if coordinacion else None
                request.session['carreraseleccionada'] = carreras.first() if carreras else None
                request.session['ruta'] = [['/', 'Inicio']]
                return ok_json({"sessionid": request.session.session_key})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json()
        else:
            return HttpResponseRedirect('/')
    except Exception as ex:
        pass


# CAMBIO DE USUARIO
@login_required(login_url='/login')
def changeuserdu(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = data['persona']
    if request.method == 'POST':
        try:
            form = CambioPerfilForm(request.POST)
            if form.is_valid():
                perfilprincipal = form.cleaned_data['perfil']
                if not persona.perfilusuario_set.filter(id=perfilprincipal.id).exists():
                    return bad_json(error=6)
                if perfilprincipal.activo():
                    del request.session['periodo']
                    del request.session['grupos_usuarios']
                    request.session['perfilprincipal'] = perfilprincipal
                    request.session['ruta'] = [['/', 'Inicio']]
                    if 'url_obligatoria' in request.session:
                        del request.session['url_obligatoria']
                    if perfilprincipal.es_estudiante():
                        perfilprincipal.establecer_estudiante_principal()
                    else:
                        request.session['coordinaciones'] = coordinaciones = persona.lista_coordinaciones()
                        request.session['coordinacionseleccionada'] = coordinacion = coordinaciones.first() if coordinaciones else None
                        request.session['carreras'] = carreras = persona.lista_carreras_coordinacion(coordinacion) if coordinacion else None
                        request.session['carreraseleccionada'] = carreras.first() if carreras else None
                return ok_json()
            else:
                return bad_json(error=6)
        except Exception as ex:
            transaction.set_rollback(True)
            return bad_json(mensaje=u"No se puede cambiar de clave.")

        return bad_json(error=0)
    else:
        try:
            data['title'] = u'Cambio de perfil'
            form = CambioPerfilForm(initial={'perfil': request.session['perfilprincipal']},
                                    )
            form.perfilpersona(persona)
            data['form'] = form
            return render(request, "changeperfil.html", data)
        except Exception as ex:
            return HttpResponseRedirect('/')

# CAMBIO DE COORDINACION
@login_required(login_url='/login')
def cambiocoordinacion(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = data['persona']
    if request.method == 'POST':
        try:
            form = CambioCoordinacionForm(request.POST)
            if form.is_valid():
                request.session['coordinacionseleccionada'] = coordinacion = form.cleaned_data['coordinacion']
                request.session['carreras'] = carreras = persona.lista_carreras_coordinacion(coordinacion)
                request.session['carreraseleccionada'] = carreras.first() if carreras else None
                if 'carreraid' in request.session:
                    del request.session['carreraid']
                if 'nivelmallaid' in request.session:
                    del request.session['nivelmallaid']
                if 'paralelomateriaid' in request.session:
                    del request.session['paralelomateriaid']
                return ok_json()
            else:
                return bad_json(error=6)
        except Exception as ex:
            transaction.set_rollback(True)
            return bad_json(mensaje=u"No se puede cambiar de coordinación.")
    else:
        try:
            data['title'] = u'Cambio de coordinación'
            form = CambioCoordinacionForm(initial={'coordinacion': request.session['coordinacionseleccionada']})
            form.mis_coordinaciones(persona)
            data['form'] = form
            data['path'] = request.GET['path']
            return render(request, "changecoordinacion.html", data)
        except Exception as ex:
            return HttpResponseRedirect('/')

# CAMBIO DE PERIODO
@login_required(login_url='/login')
def cambioperiodo(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = data['persona']
    if request.method == 'POST':
        try:
            form = CambioPeriodoForm(request.POST)
            if form.is_valid():
                request.session['periodo'] = form.cleaned_data['periodo']
                return ok_json()
            else:
                return bad_json(error=6)
        except Exception as ex:
            transaction.set_rollback(True)
            return bad_json(mensaje=u"No se puede cambiar de periodo.")
    else:
        try:
            docente=False
            perfilprincipal = request.session['perfilprincipal']
            if perfilprincipal.es_profesor():
                docente = True
            data['title'] = u'Cambio de periodo'
            form = CambioPeriodoForm(initial={'periodo': request.session['periodo']})
            form.es_docente(docente)
            data['form'] = form
            data['path'] = request.GET['path']
            return render(request, "changeperiodo.html", data)
        except Exception as ex:
            return HttpResponseRedirect('/')

# ADMISIONES


def total_seguimiento_dia(fecha,persona):
    return SeguimientoPreInscrito.objects.filter(fecha=fecha,operador=persona).distinct().count()


def total_seguimiento_rango(inicio, fin, persona):
    return SeguimientoPreInscrito.objects.filter(fecha__gte=inicio, fecha__lte=fin,operador=persona).distinct().count()


# METODOS PARA VER PAGOS Y FORMAS DE PAGOS DEL DIA, ADEMAS DATOS ESTADISTICOS Y ACADEMICOS GENERALES
def total_efectivo_dia(fecha):
    return null_to_numeric(Pago.objects.filter(sesion__fecha=fecha, efectivo=True, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)


def total_efectivo_rango(inicio, fin):
    return null_to_numeric(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, efectivo=True, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)


def total_efectivo_mes():
    hoy = datetime.now().date()
    ultimodia = calendar.monthrange(hoy.year, hoy.month)[1]
    inicio = date(hoy.year, hoy.month, 1)
    fin = date(hoy.year, hoy.month, ultimodia)
    return null_to_numeric(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, efectivo=True, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)


def cantidad_facturas_dia(fecha):
    return Factura.objects.filter(pagos__fecha=fecha, valida=True).distinct().count()


def cantidad_facturas_rango(inicio, fin):
    return Factura.objects.filter(pagos__fecha__gte=inicio, pagos__fecha__lte=fin, valida=True).distinct().count()


def cantidad_recibopagos_dia(fecha):
    return ReciboPago.objects.filter(pagos__fecha=fecha, valido=True).distinct().count()


def cantidad_recibopagos_rango(inicio, fin):
    return ReciboPago.objects.filter(pagos__fecha__gte=inicio, pagos__fecha__lte=fin, valido=True).distinct().count()


def cantidad_cheques_dia(fecha):
    return DatoCheque.objects.filter(fecha=fecha, valido=True).distinct().count()


def cantidad_cheques_rango(inicio, fin):
    return DatoCheque.objects.filter(fecha__gte=inicio, fecha__lte=fin, valido=True).distinct().count()


def total_cheques_dia(fecha):
    return null_to_numeric(Pago.objects.filter(pagocheque__isnull=False, fecha=fecha, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)


def total_cheques_rango(inicio, fin):
    return null_to_numeric(Pago.objects.filter(pagocheque__isnull=False, fecha__gte=inicio, fecha__lte=fin, valido=True).aggregate(valor=Sum('valor'))['valor'],2)


def cantidad_tarjetas_dia(fecha):
    return DatoTarjeta.objects.filter(fecha=fecha, pagotarjeta__pagos__valido=True).distinct().count()


def cantidad_tarjetas_rango(inicio, fin):
    return DatoTarjeta.objects.filter(fecha__gte=inicio, fecha__lte=fin, pagotarjeta__pagos__valido=True).distinct().count()


def total_tarjetas_dia(fecha):
    return null_to_numeric(Pago.objects.filter(pagotarjeta__isnull=False, fecha=fecha, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)


def total_tarjetas_rango(inicio, fin):
    return null_to_numeric(Pago.objects.filter(pagotarjeta__isnull=False, fecha__gte=inicio, fecha__lte=fin, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)


def cantidad_depositos_dia(fecha):
    return DatoTransferenciaDeposito.objects.filter(fecha=fecha, deposito=True, pagotransferenciadeposito__pagos__valido=True).distinct().count()


def cantidad_depositos_rango(inicio, fin):
    return DatoTransferenciaDeposito.objects.filter(fecha__gte=inicio, fecha__lte=fin, deposito=True, pagotransferenciadeposito__pagos__valido=True).distinct().count()


def total_depositos_dia(fecha):
    return null_to_numeric(Pago.objects.filter(pagotransferenciadeposito__isnull=False, fecha=fecha, pagotransferenciadeposito__datotransferenciadeposito__deposito=True, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)


def total_depositos_rango(inicio, fin):
    return null_to_numeric(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, pagotransferenciadeposito__datotransferenciadeposito__deposito=True, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)


def cantidad_transferencias_dia(fecha):
    return DatoTransferenciaDeposito.objects.filter(fecha=fecha, deposito=False, pagotransferenciadeposito__pagos__valido=True).distinct().count()


def cantidad_transferencias_rango(inicio, fin):
    return DatoTransferenciaDeposito.objects.filter(fecha__gte=inicio, fecha__lte=fin, deposito=False, pagotransferenciadeposito__pagos__valido=True).distinct().count()


def total_transferencias_dia(fecha):
    return null_to_numeric(Pago.objects.filter(pagotransferenciadeposito__isnull=False, fecha=fecha, pagotransferenciadeposito__datotransferenciadeposito__deposito=False, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)


def total_transferencias_rango(inicio, fin):
    return null_to_numeric(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, pagotransferenciadeposito__datotransferenciadeposito__deposito=False, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)


def cantidad_notasdecredito_dia(fecha):
    return PagoNotaCredito.objects.filter(pagos__fecha=fecha).distinct().count()


def total_recibocaja_dia(fecha):
    return null_to_numeric(Pago.objects.filter(fecha=fecha, pagorecibocajainstitucion__isnull=False, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)


def total_recibocaja_rango(inicio, fin):
    return null_to_numeric(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, pagorecibocajainstitucion__isnull=False, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)


def cantidad_recibocaja_dia(fecha):
    return ReciboCajaInstitucion.objects.filter(fecha=fecha).distinct().count()


def cantidad_recibocaja_rango(inicio, fin):
    return ReciboCajaInstitucion.objects.filter(fecha__gte=inicio, fecha__lte=fin).distinct().count()


def total_notadecredito_dia(fecha):
    return null_to_numeric(Pago.objects.filter(fecha=fecha, pagonotacredito__isnull=False, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)


def total_dia(fecha):
    return null_to_numeric(total_efectivo_dia(fecha) + total_cheques_dia(fecha) + total_depositos_dia(fecha) + total_transferencias_dia(fecha) + total_tarjetas_dia(fecha) + total_recibocaja_dia(fecha), 2)


def total_rango(inicio, fin):
    return null_to_numeric(total_efectivo_rango(inicio, fin) + total_cheques_rango(inicio, fin) + total_depositos_rango(inicio, fin) + total_transferencias_rango(inicio, fin) + total_tarjetas_rango(inicio, fin) + total_recibocaja_rango(inicio, fin), 2)


def facturas_total_fecha(fecha):
    return Factura.objects.filter(pagos__fecha=fecha).distinct().count()


def pagos_total_fecha(fecha):
    return null_to_numeric(Pago.objects.filter(fecha=fecha, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)


def cantidad_facturas_total_fechas(inicio, fin):
    return Factura.objects.filter(fecha__gte=inicio, fecha__lte=fin).distinct().count()


def total_pagos_rango_fechas(inicio, fin):
    return null_to_numeric(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)


# DATOS ACADEMICOS Y ADMINISTRATIVOS
def total_matriculados(periodo):
    return Matricula.objects.filter(nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_mujeres(periodo):
    return Matricula.objects.filter(inscripcion__persona__sexo=SEXO_FEMENINO, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_hombres(periodo):
    return Matricula.objects.filter(inscripcion__persona__sexo=SEXO_MASCULINO, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def cantidad_matriculados_beca(periodo):
    return Matricula.objects.filter(becado=True, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def porciento_matriculados_beca(periodo):
    if total_matriculados(periodo):
        return null_to_numeric((cantidad_matriculados_beca(periodo) / float(total_matriculados(periodo))) * 100.0, 2)
    return 0


def cantidad_matriculados_discapacidad(periodo):
    return Matricula.objects.filter(inscripcion__persona__perfilinscripcion__tienediscapacidad=True, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()


def porciento_matriculados_discapacidad(periodo):
    if total_matriculados(periodo):
        return null_to_numeric((cantidad_matriculados_discapacidad(periodo) / float(total_matriculados(periodo))) * 100.0, 2)
    return 0


# MATRICULADOS POR RANGO DE EDADES
def total_matriculados_menor_30(periodo):
    year30 = years_ago(30, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__nacimiento__gte=year30, inscripcion__persona__nacimiento__lte=datetime.now().date(), nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_menor_30_hombres(periodo):
    year30 = years_ago(30, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=2, inscripcion__persona__nacimiento__gte=year30, inscripcion__persona__nacimiento__lte=datetime.now().date(), nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_menor_30_mujeres(periodo):
    year30 = years_ago(30, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=1, inscripcion__persona__nacimiento__gte=year30, inscripcion__persona__nacimiento__lte=datetime.now().date(), nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_31_40(periodo):
    year40 = years_ago(40, datetime.now())
    year31 = years_ago(31, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__nacimiento__gte=year40, inscripcion__persona__nacimiento__lte=year31, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_31_40_hombres(periodo):
    year40 = years_ago(40, datetime.now())
    year31 = years_ago(31, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=2, inscripcion__persona__nacimiento__gte=year40, inscripcion__persona__nacimiento__lte=year31, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_17_20_hombres(periodo):
    year20 = years_ago(20, datetime.now())
    year17 = years_ago(17, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=2, inscripcion__persona__nacimiento__gte=year20, inscripcion__persona__nacimiento__lte=year17, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_17_20_mujeres(periodo):
    year20 = years_ago(20, datetime.now())
    year17 = years_ago(17, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=1, inscripcion__persona__nacimiento__gte=year20, inscripcion__persona__nacimiento__lte=year17, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_21_25_hombres(periodo):
    year25 = years_ago(25, datetime.now())
    year21 = years_ago(20, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=2, inscripcion__persona__nacimiento__gte=year25, inscripcion__persona__nacimiento__lte=year21, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_21_25_mujeres(periodo):
    year25 = years_ago(25, datetime.now())
    year21 = years_ago(20, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=1, inscripcion__persona__nacimiento__gte=year25, inscripcion__persona__nacimiento__lte=year21, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_26_30_hombres(periodo):
    year30 = years_ago(30, datetime.now())
    year26 = years_ago(25, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=2, inscripcion__persona__nacimiento__gte=year30, inscripcion__persona__nacimiento__lte=year26, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_26_30_mujeres(periodo):
    year30 = years_ago(30, datetime.now())
    year26 = years_ago(25, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=1, inscripcion__persona__nacimiento__gte=year30, inscripcion__persona__nacimiento__lte=year26, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_31_35_hombres(periodo):
    year35 = years_ago(35, datetime.now())
    year31 = years_ago(30, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=2, inscripcion__persona__nacimiento__gte=year35, inscripcion__persona__nacimiento__lte=year31, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_31_35_mujeres(periodo):
    year35 = years_ago(35, datetime.now())
    year31 = years_ago(30, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=1, inscripcion__persona__nacimiento__gte=year35, inscripcion__persona__nacimiento__lte=year31, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_36_40_hombres(periodo):
    year40 = years_ago(40, datetime.now())
    year36 = years_ago(35, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=2, inscripcion__persona__nacimiento__gte=year40, inscripcion__persona__nacimiento__lte=year36, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_36_40_mujeres(periodo):
    year40 = years_ago(40, datetime.now())
    year36 = years_ago(35, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=1, inscripcion__persona__nacimiento__gte=year40, inscripcion__persona__nacimiento__lte=year36, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_41_45_hombres(periodo):
    year45 = years_ago(45, datetime.now())
    year41 = years_ago(40, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=2, inscripcion__persona__nacimiento__gte=year45, inscripcion__persona__nacimiento__lte=year41, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_41_45_mujeres(periodo):
    year45 = years_ago(45, datetime.now())
    year41 = years_ago(40, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=1, inscripcion__persona__nacimiento__gte=year45, inscripcion__persona__nacimiento__lte=year41, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_46_50_hombres(periodo):
    year50 = years_ago(50, datetime.now())
    year46 = years_ago(45, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=2, inscripcion__persona__nacimiento__gte=year50, inscripcion__persona__nacimiento__lte=year46, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_46_50_mujeres(periodo):
    year50 = years_ago(50, datetime.now())
    year46 = years_ago(45, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=1, inscripcion__persona__nacimiento__gte=year50, inscripcion__persona__nacimiento__lte=year46, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_51_55_hombres(periodo):
    year55 = years_ago(55, datetime.now())
    year51 = years_ago(50, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=2, inscripcion__persona__nacimiento__gte=year55, inscripcion__persona__nacimiento__lte=year51, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_51_55_mujeres(periodo):
    year55 = years_ago(55, datetime.now())
    year51 = years_ago(50, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=1, inscripcion__persona__nacimiento__gte=year55, inscripcion__persona__nacimiento__lte=year51, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_56_60_hombres(periodo):
    year60 = years_ago(60, datetime.now())
    year56 = years_ago(55, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=6, inscripcion__persona__nacimiento__gte=year60, inscripcion__persona__nacimiento__lte=year56, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_56_60_mujeres(periodo):
    year60 = years_ago(60, datetime.now())
    year56 = years_ago(55, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=1, inscripcion__persona__nacimiento__gte=year60, inscripcion__persona__nacimiento__lte=year56, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_31_40_mujeres(periodo):
    year40 = years_ago(40, datetime.now())
    year31 = years_ago(31, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=1, inscripcion__persona__nacimiento__gte=year40, inscripcion__persona__nacimiento__lte=year31, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_41_50(periodo):
    year50 = years_ago(50, datetime.now())
    year41 = years_ago(41, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__nacimiento__gte=year50, inscripcion__persona__nacimiento__lte=year41, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_41_50_hombres(periodo):
    year50 = years_ago(50, datetime.now())
    year41 = years_ago(41, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=2, inscripcion__persona__nacimiento__gte=year50, inscripcion__persona__nacimiento__lte=year41, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_41_50_mujeres(periodo):
    year50 = years_ago(50, datetime.now())
    year41 = years_ago(41, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=1, inscripcion__persona__nacimiento__gte=year50, inscripcion__persona__nacimiento__lte=year41, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_51_60(periodo):
    year60 = years_ago(60, datetime.now())
    year51 = years_ago(51, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__nacimiento__gte=year60, inscripcion__persona__nacimiento__lte=year51, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_51_60_hombres(periodo):
    year60 = years_ago(60, datetime.now())
    year51 = years_ago(51, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=2, inscripcion__persona__nacimiento__gte=year60, inscripcion__persona__nacimiento__lte=year51, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_51_60_mujeres(periodo):
    year60 = years_ago(60, datetime.now())
    year51 = years_ago(51, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=1, inscripcion__persona__nacimiento__gte=year60, inscripcion__persona__nacimiento__lte=year51, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_mayor_61(periodo):
    year61 = years_ago(61, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__nacimiento__lte=year61, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_mayor_61_hombres(periodo):
    year61 = years_ago(61, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=2, inscripcion__persona__nacimiento__lte=year61, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def total_matriculados_mayor_61_mujeres(periodo):
    year61 = years_ago(61, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__sexo=1, inscripcion__persona__nacimiento__lte=year61, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).count()


def materias_abiertas(asignatura, inscripcion, nivel, estudiante=False):
    global ex
    try:
        hoy = datetime.now().date()
        malla = inscripcion.mi_malla()
        materiasabiertas = []
        am = inscripcion.asignatura_en_asignaturamalla(asignatura)
        mm = malla.modulomalla_set.filter(asignatura=asignatura)
        if inscripcion.mi_nivel().nivel.id == NIVEL_MALLA_CERO:
            materiasabiertas = Materia.objects.filter(asignaturamalla__nivelmalla__id=NIVEL_MALLA_CERO, nivel__sesion=inscripcion.sesion, fin__gte=hoy, nivel__sede=nivel.sede, nivel__modalidad=inscripcion.modalidad, nivel__cerrado=False, asignatura=asignatura, nivel__periodo=nivel.periodo).distinct().order_by('paralelomateria')
        else:
            if am:
                if estudiante:
                    materiasabiertas = Materia.objects.filter(Q(materiascompartidas__sede=inscripcion.sede, materiascompartidas__carrera=inscripcion.carrera, materiascompartidas__modalidad=inscripcion.modalidad, materiascompartidas__materiaotracarreramodalidadsede__asignatura=asignatura, rectora=True) | Q(asignaturamalla=am, nivel=nivel) | Q(materiascompartidas__sede=inscripcion.sede, materiascompartidas__carrera=inscripcion.carrera, materiascompartidas__modalidad=inscripcion.modalidad, asignatura=asignatura, rectora=True), fin__gte=hoy, nivel__cerrado=False, nivel__periodo=nivel.periodo, nivel__modalidad=inscripcion.modalidad).distinct().order_by('paralelomateria')
                else:
                    materiasabiertas = Materia.objects.filter(Q(materiascompartidas__sede=inscripcion.sede, materiascompartidas__carrera=inscripcion.carrera, materiascompartidas__modalidad=inscripcion.modalidad, materiascompartidas__materiaotracarreramodalidadsede__asignatura=asignatura, rectora=True) | Q(asignaturamalla=am, nivel=nivel) | Q(materiascompartidas__sede=inscripcion.sede, materiascompartidas__carrera=inscripcion.carrera, materiascompartidas__modalidad=inscripcion.modalidad, asignatura=asignatura, rectora=True), fin__gte=hoy, nivel__cerrado=False, nivel__periodo=nivel.periodo).distinct().order_by('paralelomateria')
            mm = inscripcion.asignatura_en_modulomalla(asignatura)
            if mm:
                if estudiante:
                    materiasabiertas = Materia.objects.filter(Q(materiascompartidas__sede=inscripcion.sede, materiascompartidas__carrera=inscripcion.carrera, materiascompartidas__modalidad=inscripcion.modalidad, materiascompartidas__materiaotracarreramodalidadsede__asignatura=asignatura, rectora=True) |
                                                              Q(modulomalla=mm, nivel=nivel) |
                                                              Q(materiascompartidas__sede=inscripcion.sede, materiascompartidas__carrera=inscripcion.carrera, materiascompartidas__modalidad=inscripcion.modalidad, asignatura=asignatura, rectora=True),
                                                              fin__gte=hoy,
                                                              nivel__modalidad=inscripcion.modalidad,
                                                              nivel__cerrado=False,
                                                              nivel__periodo=nivel.periodo, cerrado=False).distinct().order_by('paralelomateria')
                else:
                    materiasabiertas = Materia.objects.filter(Q(materiascompartidas__sede=inscripcion.sede, materiascompartidas__carrera=inscripcion.carrera, materiascompartidas__modalidad=inscripcion.modalidad, materiascompartidas__materiaotracarreramodalidadsede__asignatura=asignatura, rectora=True) |
                                                              Q(modulomalla=mm, nivel=nivel) |
                                                              Q(materiascompartidas__sede=inscripcion.sede, materiascompartidas__carrera=inscripcion.carrera, materiascompartidas__modalidad=inscripcion.modalidad, asignatura=asignatura, rectora=True),
                                                              fin__gte=hoy, nivel__cerrado=False,
                                                              nivel__periodo=nivel.periodo, cerrado=False).distinct().order_by('paralelomateria')
        materias = []
        for materia in materiasabiertas:
            adicionar = False
            verificacupocompartido = False
            if materia.asignaturamalla == am and am:
                adicionar = True
            elif materia.modulomalla == mm and mm:
                adicionar = True
            elif materia.rectora and materia.materiascompartidas_set.filter(sede=inscripcion.sede,carrera=inscripcion.carrera,modalidad=inscripcion.modalidad).exists():
                adicionar = True
                verificacupocompartido = True
            if adicionar:
                if materia.capacidad_disponible_inscripcion(inscripcion) <= 0:
                    adicionar = False
            if adicionar:
                coordinacion = materia.nivel.nivellibrecoordinacion_set.all().first().coordinacion.alias
                mat = {'nombre': materia.asignatura.__str__(), 'nivel': materia.asignaturamalla.nivelmalla.__str__() if materia.asignaturamalla else "", 'sede': materia.nivel.sede.__str__(), 'profesor': materia.profesor_principal().persona.__str__() if materia.profesor_principal() else 'SIN DEFINIR', 'horario': "<br>".join(x for x in materia.clases_informacion()), 'id': materia.id, 'inicio': materia.inicio.strftime("%d-%m-%Y"), 'session': materia.nivel.sesion.__str__(), 'fin': materia.fin.strftime("%d-%m-%Y"), 'paralelo': materia.paralelomateria.__str__(), 'idparalelo': (materia.paralelomateria.id if materia.paralelomateria else ''), 'identificacion': materia.identificacion, 'coordcarrera': '%s - %s' % (coordinacion, materia.nivel), 'carrera': materia.carrera.alias, 'cupo': materia.capacidad_disponible(), 'matriculados': materia.cantidad_matriculas_materia(), 'nivelparalelo': materia.nivel.paralelo, 'modulonivelmalla': materia.modulonivelmalla.__str__() if materia.modulonivelmalla else '', 'intensivo': 'INTENSIVO' if materia.intensivo else '' }
                materias.append(mat)
        return {"idd": asignatura.id, "asignatura": asignatura.__str__(), "abiertas": materiasabiertas.__len__(), "disponibles": materias.__len__(), "materias": materias}
    except Exception as ex:
        return bad_json(error=3)


def materias_abiertas_secretaria(request):
    global ex
    try:
        asignatura = Asignatura.objects.get(pk=request.POST['ida'])
        inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
        hoy = datetime.now().date()
        nivel = Nivel.objects.get(pk=request.POST['nivel'])
        paralelo = []
        if 'paralelos' in request.POST:
            paralelo = json.loads(request.POST['paralelos'])
        # MATERIAS SEGUN INSTITUTOS
        if inscripcion.mi_nivel().nivel.id == NIVEL_MALLA_CERO:
            materiasabiertas = Materia.objects.filter(asignaturamalla__nivelmalla__id=NIVEL_MALLA_CERO, nivel__sesion=inscripcion.sesion, fin__gte=hoy, nivel__sede=nivel.sede, nivel__cerrado=False, asignatura=asignatura, nivel__periodo=nivel.periodo).distinct().order_by('paralelomateria')
        else:
            malla = inscripcion.mi_malla()
            materiasabiertas = []
            if malla.asignaturamalla_set.filter(asignatura=asignatura).exists():
                am = malla.asignaturamalla_set.filter(asignatura=asignatura)
                materiasabiertas = Materia.objects.filter(asignaturamalla__in=am, fin__gte=hoy, nivel__sede=nivel.sede, nivel__cerrado=False, asignatura=asignatura, nivel__periodo=nivel.periodo).distinct().order_by('paralelomateria')
                if not materiasabiertas:
                    materiasabiertas = Materia.objects.filter(rectora=True, carrerascomunes__id__in=[inscripcion.carrera.id], fin__gte=hoy, nivel__sede=nivel.sede, nivel__cerrado=False, asignatura=asignatura, nivel__periodo=nivel.periodo).distinct().order_by('paralelomateria')
                if not materiasabiertas:
                    materiasabiertas = Materia.objects.filter(rectora=True, materiaotracarreramodalidadsede__carrera__id=inscripcion.carrera.id, materiaotracarreramodalidadsede__asignatura=asignatura, fin__gte=hoy, nivel__sede=nivel.sede, nivel__cerrado=False, nivel__periodo=nivel.periodo).distinct().order_by('paralelomateria')
            if malla.modulomalla_set.filter(asignatura=asignatura).exists():
                mm = malla.modulomalla_set.filter(asignatura=asignatura)
                materiasabiertas = Materia.objects.filter(modulomalla__in=mm, fin__gte=hoy, nivel__sede=nivel.sede, nivel__cerrado=False, asignatura=asignatura, nivel__periodo=nivel.periodo).distinct().order_by('paralelomateria')
                if not materiasabiertas:
                    materiasabiertas = Materia.objects.filter(rectora=True, carrerascomunes__id__in=[inscripcion.carrera.id], fin__gte=hoy, nivel__sede=nivel.sede, nivel__cerrado=False, asignatura=asignatura, nivel__periodo=nivel.periodo).distinct().order_by('paralelomateria')
        materias = {}
        for materia in materiasabiertas:
            if materia.asignaturamalla:
                carrera = materia.asignaturamalla.malla.carrera.alias
            elif materia.modulomalla:
                carrera = materia.modulomalla.malla.carrera.alias
            else:
                carrera = materia.nivel.carrera.alias
            coordinacion = materia.nivel.nivellibrecoordinacion_set.all().first().coordinacion.alias
            mat = {}
            if materia.capacidad_disponible() > 0:
                mat[materia.id] = {'nombre': u"%s" % materia.asignatura.nombre, 'nivel': u"%s" % materia.nivel.nivelmalla.nombre if materia.nivel.nivelmalla else u"", 'sede': u"%s - %s" % (materia.nivel.sede.nombre, materia.nivel.modalidad.nombre), 'profesor': u"%s" % (materia.profesor_principal().persona.nombre_completo() if materia.profesor_principal() else u'SIN DEFINIR'), 'horario': "<br>".join(x for x in materia.clases_informacion()), 'id': materia.id, 'inicio': materia.inicio.strftime("%d-%m-%Y"), 'session': u"%s" % materia.nivel.sesion.nombre, 'fin': materia.fin.strftime("%d-%m-%Y"), 'paralelo': u"%s" % (materia.paralelomateria.nombre if materia.paralelomateria else u''), 'idparalelo': (materia.paralelomateria.id if materia.paralelomateria else ''), 'identificacion': materia.identificacion, 'coordcarrera': coordinacion, 'carrera': carrera, 'cupo': materia.capacidad_disponible(), 'matriculados': materia.cantidad_matriculas_materia()}
                materias.update(mat)
        return ok_json({"idd": asignatura.id, "asignatura": "%s" % asignatura.nombre, "abiertas": materiasabiertas.__len__(), "disponibles": materias.__len__(), "materias": materias})
    except Exception as ex:
        return bad_json(error=3)


def conflicto_materias_seleccionadas(materias):
    if CHEQUEAR_CONFLICTO_HORARIO:
        clasesmaterias = Clase.objects.filter(Q(materia__cerrado=False) | Q(materiacurso__cerrada=False), materia__in=materias, activo=True).order_by('dia')
        clasesverificadas = []
        for clase in clasesmaterias:
            clasesverificadas.append(clase.id)
            if clasesmaterias.filter(
                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.termina, inicio__lte=clase.inicio, fin__gte=clase.fin) |
                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.termina, inicio__gte=clase.inicio, fin__lte=clase.fin) |
                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.termina, inicio__lte=clase.inicio, fin__lte=clase.fin, fin__gte=clase.inicio) |
                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.termina, inicio__gte=clase.inicio, inicio__lte=clase.fin, fin__gte=clase.fin) |

                    Q(turno__comienza__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__lte=clase.inicio, fin__gte=clase.fin) |
                    Q(turno__comienza__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__gte=clase.inicio, fin__lte=clase.fin) |
                    Q(turno__comienza__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__lte=clase.inicio, fin__lte=clase.fin, fin__gte=clase.inicio) |
                    Q(turno__comienza__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__gte=clase.inicio, inicio__lte=clase.fin, fin__gte=clase.fin) |

                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__lte=clase.inicio, fin__gte=clase.fin) |
                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__gte=clase.inicio, fin__lte=clase.fin) |
                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__lte=clase.inicio, fin__lte=clase.fin, fin__gte=clase.inicio) |
                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__gte=clase.inicio, inicio__lte=clase.fin, fin__gte=clase.fin) |

                    Q(turno__comienza__gte=clase.turno.comienza, turno__comienza__lte=clase.turno.termina, turno__termina__gte=clase.turno.termina, inicio__lte=clase.inicio, fin__gte=clase.fin) |
                    Q(turno__comienza__gte=clase.turno.comienza, turno__comienza__lte=clase.turno.termina, turno__termina__gte=clase.turno.termina, inicio__gte=clase.inicio, fin__lte=clase.fin) |
                    Q(turno__comienza__gte=clase.turno.comienza, turno__comienza__lte=clase.turno.termina, turno__termina__gte=clase.turno.termina, inicio__lte=clase.inicio, fin__lte=clase.fin, fin__gte=clase.inicio) |
                    Q(turno__comienza__gte=clase.turno.comienza, turno__comienza__lte=clase.turno.termina, turno__termina__gte=clase.turno.termina, inicio__gte=clase.inicio, inicio__lte=clase.fin, fin__gte=clase.fin)
                    , dia=clase.dia).exclude(id__in=clasesverificadas).exists():
                conflicto = clasesmaterias.filter(
                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.termina, inicio__lte=clase.inicio, fin__gte=clase.fin) |
                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.termina, inicio__gte=clase.inicio, fin__lte=clase.fin) |
                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.termina, inicio__lte=clase.inicio, fin__lte=clase.fin, fin__gte=clase.inicio) |
                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.termina, inicio__gte=clase.inicio, inicio__lte=clase.fin, fin__gte=clase.fin) |

                    Q(turno__comienza__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__lte=clase.inicio, fin__gte=clase.fin) |
                    Q(turno__comienza__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__gte=clase.inicio, fin__lte=clase.fin) |
                    Q(turno__comienza__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__lte=clase.inicio, fin__lte=clase.fin, fin__gte=clase.inicio) |
                    Q(turno__comienza__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__gte=clase.inicio, inicio__lte=clase.fin, fin__gte=clase.fin) |

                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__lte=clase.inicio, fin__gte=clase.fin) |
                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__gte=clase.inicio, fin__lte=clase.fin) |
                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__lte=clase.inicio, fin__lte=clase.fin, fin__gte=clase.inicio) |
                    Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.comienza, turno__termina__lte=clase.turno.termina, inicio__gte=clase.inicio, inicio__lte=clase.fin, fin__gte=clase.fin) |

                    Q(turno__comienza__gte=clase.turno.comienza, turno__comienza__lte=clase.turno.termina, turno__termina__gte=clase.turno.termina, inicio__lte=clase.inicio, fin__gte=clase.fin) |
                    Q(turno__comienza__gte=clase.turno.comienza, turno__comienza__lte=clase.turno.termina, turno__termina__gte=clase.turno.termina, inicio__gte=clase.inicio, fin__lte=clase.fin) |
                    Q(turno__comienza__gte=clase.turno.comienza, turno__comienza__lte=clase.turno.termina, turno__termina__gte=clase.turno.termina, inicio__lte=clase.inicio, fin__lte=clase.fin, fin__gte=clase.inicio) |
                    Q(turno__comienza__gte=clase.turno.comienza, turno__comienza__lte=clase.turno.termina, turno__termina__gte=clase.turno.termina, inicio__gte=clase.inicio, inicio__lte=clase.fin, fin__gte=clase.fin)
                    , dia=clase.dia).exclude(id__in=clasesverificadas).first()
                return u"conflicto de horario: %s y %s el dia: %s" % (clase.materia, conflicto.materia,  conflicto.dia.__str__())
    return u""


def calcular_costo(request):
    global ex
    try:
        from ctt.adm_calculofinanzas import costo_matricula
        inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
        nivel = Nivel.objects.get(pk=request.POST['idn'])
        fecha = datetime.now().date()
        if 'f' in request.POST:
            fecha = convertir_fecha(request.POST['f'])
        mismaterias = json.loads(request.POST['materias'])
        valor = costo_matricula(inscripcion=inscripcion, asignaturas=mismaterias, nivel=nivel, fecha=fecha)
        return ok_json({"valor": valor})
    except Exception as ex:
        return bad_json(error=3)


def matricular(request, estudiante=False, generarrubros=True):
    global ex
    try:
        inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
        mismaterias = json.loads(request.POST['materias'])
        if not estudiante:
            chkprorroga = request.POST['chkprorroga']
            if request.POST['selprorroga'] != '0':
                cargoinstitucion = CargoInstitucion.objects.get(pk=request.POST['selprorroga'])
        else:
            chkprorroga = False
        if 'fechamat' in request.POST:
            fechamatricula = convertir_fecha(request.POST['fechamat'])
        else:
            fechamatricula = datetime.now().date()
        if 'resolucion' in request.POST:
            resolucion = request.POST['resolucion']
        else:
            resolucion = ''
        seleccion = []
        for m in mismaterias:
            seleccion.append(int(m['ids']))
        materias = Materia.objects.filter(id__in=seleccion)
        # CAPACIDAD LIMITE DE CUPO
        for materia in materias:
            if materia.capacidad_disponible_inscripcion(inscripcion) <= 0:
                return bad_json(mensaje=u"Capacidad limite de la materia: %s, seleccione otra." % materia.asignatura.nombre, extradata={"reload": True})
        nivel = Nivel.objects.get(pk=request.POST['nivel'])
        # PERDIDA DE CARRERA POR 4TA MATRICULA
        if inscripcion.tiene_perdida_carrera():
            return bad_json(mensaje=u"Su límite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para mas información.")
        # MATRICULA FUERA DE FECHAS
        if fechamatricula > nivel.fechatopematriculaes:
            return bad_json(mensaje=u"No puede matricular fuera de fechas.")
        # MATRICULA
        if not inscripcion.matriculado():
            matricula = Matricula(inscripcion=inscripcion,
                                  nivel=nivel,
                                  becado=False,
                                  porcientobeca=0,
                                  fecha=fechamatricula,
                                  hora=datetime.now().time(),
                                  fechatope=fechatope(fechamatricula, inscripcion),
                                  nivelmalla=inscripcion.mi_nivel().nivel,
                                  personamatriculo=request.session['persona'],
                                  resolucionconsejo=resolucion)
            matricula.save(request)
            inscripcion.actualiza_fecha_inicio_carrera()
            inscripcion.permitematriculacondeuda = False
            inscripcion.save()
            for materia in materias:
                idrepresenta = 0
                for m in mismaterias:
                    if int(m['ids']) == materia.id:
                        idrepresenta = m['idm']
                        break
                representa = Asignatura.objects.get(pk=idrepresenta)
                matriculas = matricula.inscripcion.historicorecordacademico_set.filter(noaplica=False, convalidacion=False, homologada=False, asignatura=representa, fecha__lt=materia.nivel.fin).count() + 1
                malla = inscripcion.mi_malla()
                itinerario = inscripcion.mi_itinerario()
                am = None
                mm = None
                horas = materia.horas
                creditos = materia.creditos
                if malla.asignaturamalla_set.filter(Q(itinerario__isnull=True) | Q(itinerario=itinerario), asignatura=representa).exists():
                    am = malla.asignaturamalla_set.filter(Q(itinerario__isnull=True) | Q(itinerario=itinerario), asignatura=representa).first()
                    horas = am.horas
                    creditos = am.creditos
                elif malla.modulomalla_set.filter(asignatura=representa).exists():
                    mm = malla.modulomalla_set.filter(asignatura=representa).first()
                    horas = mm.horas
                    creditos = mm.creditos
                sinasistencia = False
                verificahorario = True
                for m in mismaterias:
                    if representa.id == int(m['idm']):
                        if not estudiante:
                            if m['sinasistencia']:
                                sinasistencia = True
                                verificahorario = False
                if matricula.inscripcion.modalidad.id == 3:
                    sinasistencia = True
                materiaasignada = MateriaAsignada(matricula=matricula,
                                                  materia=materia,
                                                  fechaasignacion=materia.inicio,
                                                  asignaturamalla=am,
                                                  modulomalla=mm,
                                                  asignaturareal=representa,
                                                  horas=horas,
                                                  creditos=creditos,
                                                  notafinal=0,
                                                  asistenciafinal=0,
                                                  sinasistencia=sinasistencia,
                                                  verificahorario=verificahorario,
                                                  cerrado=False,
                                                  matriculas=matriculas,
                                                  observaciones='',
                                                  estado_id=NOTA_ESTADO_EN_CURSO)
                materiaasignada.save(request)
                materiaasignada.asistencias()
                materiaasignada.evaluacion()
                materiaasignada.save(request)
                log(u'Materia seleccionada matricula: %s' % materiaasignada, request, "add")
            matricula.save(request)
            matricula.actualiza_tipo_inscripcion()
            matricula.inscripcion.actualiza_tipo_inscripcion()
            matricula.inscripcion.actualiza_gratuidad()
            if chkprorroga == u'true':
                comentario = request.POST['comprorroga']
                matricula.generar_solicitud_prorroga(cargoinstitucion, inscripcion, comentario)
            if generarrubros:
                matricula.calcular_rubros_matricula()
            if estudiante:
                send_mail(subject='Automatricula.',
                          html_template='emails/matricula.html',
                          data={'matricula': matricula},
                          recipient_list=[inscripcion.persona])
                log(u'Automatricula estudiante: %s' % matricula, request, "add")
            else:
                send_mail(subject='Matricula por secretaria.',
                          html_template='emails/matricula.html',
                          data={'matricula': matricula},
                          recipient_list=[inscripcion.persona])
                log(u'Matricula secretaria: %s' % matricula, request, "add")
            return ok_json({"mensaje": nivel.mensaje})
        else:
            transaction.set_rollback(True)
            return bad_json({"reload": True, "mensaje": u"Ya se encuentra matriculado."})
    except Exception as ex:
        transaction.set_rollback(True)
        return bad_json(mensaje=u"Hubieron errores en la matriculación.")


def prematricular(request):
    global ex
    try:
        inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
        mismaterias = request.POST['materias']
        periodo = Periodo.objects.get(pk=request.POST['pid'])
        seleccion = []
        for m in mismaterias.replace('[', '').replace('"', '').replace(']', '').split(','):
            seleccion.append(int(m))
        materias = Asignatura.objects.filter(id__in=seleccion)
        # PERDIDA DE CARRERA POR 4TA MATRICULA
        if inscripcion.tiene_perdida_carrera():
            return bad_json(mensaje=u"Tiene límite de matriculas (4ta matricula).")
        # MATRICULA
        if not inscripcion.prematricula_set.filter(periodo=periodo).exists():
            prematricula = PreMatricula(inscripcion=inscripcion,
                                        periodo=periodo,
                                        fecha=datetime.now().date(),
                                        hora=datetime.now().time())
            prematricula.save(request)
            prematricula.asignaturas = materias
            log(u'Prematricula de asignaturas: %s' % prematricula, request, "add")
            return ok_json()
        else:
            transaction.set_rollback(True)
            return bad_json(mensaje=u"Ya se encuentra prematriculado.")
    except Exception as ex:
        transaction.set_rollback(True)
        return bad_json(mensaje=u"Hubieron errores en la prematriculación.")


# FUNCIONES COMUNES
def actualizar_nota(request, materiaasignada=None, sel=None, valor=None, rapido=False):
    perfil = request.session['perfilprincipal']
    if perfil.es_estudiante():
        datos = {"result": "bad"}
    else:
        if not materiaasignada:
            materiaasignada = MateriaAsignada.objects.get(pk=request.POST['maid'])
        if not sel:
            sel = request.POST['sel']
        datos = {"result": "ok"}
        modeloevaluativo = materiaasignada.materia.modeloevaluativo
        campomodelo = modeloevaluativo.campo(sel)
        try:
            if not valor:
                valor = null_to_numeric(float(request.POST['val']), campomodelo.decimales)
            if valor >= campomodelo.notamaxima:
                valor = campomodelo.notamaxima
            elif valor <= campomodelo.notaminima:
                valor = campomodelo.notaminima
        except:
            valor = campomodelo.notaminima
        campo = materiaasignada.campo(sel)
        campo.valor = valor
        campo.save(request)
        if not rapido:
            local_scope = {}
            exec(modeloevaluativo.logicamodelo, globals(), local_scope)
            calculo_modelo_evaluativo = local_scope['calculo_modelo_evaluativo']
            calculo_modelo_evaluativo(materiaasignada)

            #
            # exec(modeloevaluativo.logicamodelo)
            # # FUNCION DIMAMICA
            # calculo_modelo_evaluativo(materiaasignada)
            materiaasignada.notafinal = null_to_numeric(materiaasignada.notafinal, modeloevaluativo.notafinaldecimales)
            if materiaasignada.notafinal > modeloevaluativo.notamaxima:
                materiaasignada.notafinal = modeloevaluativo.notamaxima
            materiaasignada.save(request)
            camposdependientes = []
            encurso = True
            if EvaluacionGenerica.objects.filter(Q(detallemodeloevaluativo__determinaestadofinal=True) |
                                                 Q(detallemodeloevaluativo__actualizaestado=True), valor__gt=0, materiaasignada=materiaasignada).exists():
                encurso = False
            if not encurso:
                materiaasignada.actualiza_estado()
            else:
                materiaasignada.estado_id = NOTA_ESTADO_EN_CURSO
                materiaasignada.save(request)
            datos['dependientes'] = camposdependientes
            campo = materiaasignada.campo(sel)
            datos['valor'] = campo.valor
            datos['valores'] = [[x.detallemodeloevaluativo.nombre, x.valor, x.detallemodeloevaluativo.dependiente, x.detallemodeloevaluativo.decimales] for x in EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada)]
            log(u'Ingreso de notas: %s - %s- %s - %s' % (materiaasignada.matricula.inscripcion.persona, materiaasignada.materia.asignatura, sel, str(campo.valor)), request, "add")
            datos['nota_final'] = materiaasignada.notafinal
            datos['valida_asistencia'] = materiaasignada.materia.nivel.periodo.valida_asistencia
            datos['estado'] = materiaasignada.estado.nombre
            datos['estadoid'] = materiaasignada.estado.id
            materiaasignada.matricula.save()
    return datos


# FUNCIONES COMUNES
def actualizar_nota_curso(request, materiaasignada=None, sel=None, valor=None):
    perfil = request.session['perfilprincipal']
    if perfil.es_estudiante():
        datos = {"result": "bad"}
    else:
        if not materiaasignada:
            materiaasignada = MateriaAsignadaCurso.objects.get(pk=request.POST['maid'])
        if not sel:
            sel = request.POST['sel']
        datos = {"result": "ok"}
        modeloevaluativo = materiaasignada.materia.curso.modeloevaluativo
        campomodelo = modeloevaluativo.campo(sel)
        try:
            if not valor:
                valor = null_to_numeric(float(request.POST['val']), campomodelo.decimales)
            if valor >= campomodelo.notamaxima:
                valor = campomodelo.notamaxima
            elif valor <= campomodelo.notaminima:
                valor = campomodelo.notaminima
        except:
            valor = campomodelo.notaminima
        campo = materiaasignada.campo(sel)
        campo.valor = valor
        campo.save(request)
        local_scope = {}
        exec(modeloevaluativo.logicamodelo, globals(), local_scope)
        # FUNCION DIMAMICA
        calculo_modelo_evaluativo = local_scope['calculo_modelo_evaluativo']
        calculo_modelo_evaluativo(materiaasignada)
        materiaasignada.notafinal = null_to_numeric(materiaasignada.notafinal, modeloevaluativo.notafinaldecimales)
        if materiaasignada.notafinal > modeloevaluativo.notamaxima:
            materiaasignada.notafinal = modeloevaluativo.notamaxima
        materiaasignada.save(request)
        camposdependientes = []
        encurso = True
        for campomodelo in modeloevaluativo.campos():
            if campomodelo.dependiente:
                camposdependientes.append((campomodelo.htmlid(), materiaasignada.valor_nombre_campo(campomodelo.nombre), campomodelo.decimales))
            if campomodelo.actualizaestado and materiaasignada.valor_nombre_campo(campomodelo.nombre) > 0:
                encurso = False
        if not encurso:
            materiaasignada.actualiza_estado()
        else:
            materiaasignada.estado_id = NOTA_ESTADO_EN_CURSO
            materiaasignada.save(request)
        datos['dependientes'] = camposdependientes
        campo = materiaasignada.campo(sel)
        datos['valor'] = campo.valor
        log(u'Ingreso de notas: %s - %s- %s - %s' % (materiaasignada.matricula.inscripcion.persona, materiaasignada.materia.asignatura, sel, str(campo.valor)), request, "add")
        datos['nota_final'] = materiaasignada.notafinal
        datos['estado'] = materiaasignada.estado.nombre
        datos['estadoid'] = materiaasignada.estado.id
    return datos


def justificar_asistencia(request, asistencialeccion=None):
    datos = {}
    if not asistencialeccion:
        asistencialeccion = AsistenciaLeccion.objects.get(pk=request.POST['id'])
    if not JustificacionAusenciaAsistenciaLeccion.objects.filter(asistencialeccion=asistencialeccion).exists():
        asistencialeccion.asistio = True
        asistencialeccion.save(request)
        justificacionausenciaasistencialeccion = JustificacionAusenciaAsistenciaLeccion(asistencialeccion=asistencialeccion,
                                                                                        porcientojustificado=PORCIENTO_RECUPERACION_FALTAS,
                                                                                        motivo=request.POST['motivo'],
                                                                                        fecha=datetime.now().date(),
                                                                                        persona=request.session['persona'])
        justificacionausenciaasistencialeccion.save(request)
    materiaasignada = asistencialeccion.materiaasignada
    materiaasignada.save(actualiza=True)
    materiaasignada.actualiza_estado()
    datos['materiaasignada'] = materiaasignada.id
    datos['porcientoasist'] = str(materiaasignada.asistenciafinal)
    datos['porcientorequerido'] = materiaasignada.porciento_requerido()
    log(u'Justifico asistencia: %s - %s - %s' % (materiaasignada.materia.asignatura.nombre, asistencialeccion.materiaasignada.matricula.inscripcion.persona.nombre_completo(), asistencialeccion.leccion.fecha.strftime("%Y-%m-%d")), request, "edit")
    return datos


def justificar_asistencia_practica(request, asistencialeccion=None):
    datos = {}
    if not asistencialeccion:
        asistencialeccion = AsistenciaLeccionPractica.objects.get(pk=request.POST['id'])
    if not JustificacionAusenciaAsistenciaLeccionPractica.objects.filter(asistencialeccionpractica=asistencialeccion).exists():
        asistencialeccion.asistio = True
        asistencialeccion.save(request)
        justificacionausenciaasistencialeccion = JustificacionAusenciaAsistenciaLeccionPractica(asistencialeccionpractica=asistencialeccion,
                                                                                                porcientojustificado=PORCIENTO_RECUPERACION_FALTAS,
                                                                                                motivo=request.POST['motivo'],
                                                                                                fecha=datetime.now().date(),
                                                                                                persona=request.session['persona'])
        justificacionausenciaasistencialeccion.save(request)
    materiaasignadagrupopracticas = asistencialeccion.materiaasignadagrupopracticas
    materiaasignadagrupopracticas.save(request)
    datos['materiaasignada'] = materiaasignadagrupopracticas
    datos['porcientoasist'] = str(materiaasignadagrupopracticas.asistenciafinal)
    datos['porcientorequerido'] = materiaasignadagrupopracticas.porciento_requerido()
    log(u'Asistencia en clase: %s - %s - %s' % (materiaasignadagrupopracticas.materiaasignada.materia.asignatura.nombre, asistencialeccion.materiaasignadagrupopracticas.materiaasignada.matricula.inscripcion.persona.nombre_completo(),asistencialeccion.leccionpractica.fecha.strftime("%Y-%m-%d")), request, "edit")
    return datos


def actualizar_asistencia(request):
    datos = {"result": "ok"}
    asistencialeccion = AsistenciaLeccion.objects.get(pk=request.POST['id'])
    if not asistencialeccion.leccion.leccion_grupo().abierta:
        if LIMITE_HORAS_JUSTIFICAR:
            if asistencialeccion.leccion.fecha < datetime.now().date() - timedelta(hours=CANTIDAD_HORAS_JUSTIFICACION_ASISTENCIAS):
                return bad_json(mensaje=u"Las faltas menores a %s hora(s) no pueden ser justificadas." % CANTIDAD_HORAS_JUSTIFICACION_ASISTENCIAS)
    asistencialeccion.asistio = request.POST['val'] == 'true'
    asistencialeccion.save(request)
    materiaasignada = asistencialeccion.materiaasignada
    materiaasignada.save(request)
    materiaasignada.actualiza_estado()
    datos['materiaasignada'] = materiaasignada
    datos['porcientoasist'] = str(materiaasignada.asistenciafinal)
    datos['porcientorequerido'] = materiaasignada.porciento_requerido()
    log(u'Asistencia en clase: %s - %s - %s' % (materiaasignada.materia.asignatura.nombre, asistencialeccion.materiaasignada.matricula.inscripcion.persona.nombre_completo(), asistencialeccion.leccion.fecha.strftime("%Y-%m-%d")), request, "edit")
    return datos


def actualizar_asistencia_practica(request):
    datos = {"result": "ok"}
    asistencialeccion = AsistenciaLeccionPractica.objects.get(pk=request.POST['id'])
    asistencialeccion.asistio = request.POST['val'] == 'true'
    asistencialeccion.save(request)
    materiaasignadagrupopracticas = asistencialeccion.materiaasignadagrupopracticas
    materiaasignadagrupopracticas.save(request)
    datos['materiaasignada'] = materiaasignadagrupopracticas
    datos['porcientoasist'] = str(materiaasignadagrupopracticas.asistenciafinal)
    datos['porcientorequerido'] = materiaasignadagrupopracticas.porciento_requerido()
    log(u'Asistencia en clase: %s - %s - %s' % (materiaasignadagrupopracticas.materiaasignada.materia.asignatura.nombre, asistencialeccion.materiaasignadagrupopracticas.materiaasignada.matricula.inscripcion.persona.nombre_completo(), asistencialeccion.leccionpractica.fecha.strftime("%Y-%m-%d")), request, "edit")
    return datos


def actualizar_contenido(request):
    perfil = request.session['perfilprincipal']
    if perfil.es_estudiante():
        datos = {"result": "bad"}
    else:
        datos = {"result": "ok"}
        lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
        lecciongrupo.contenido = request.POST['val']
        lecciongrupo.save(request)
        log(u'Modifico contenido de leccion: %s' % lecciongrupo, request, "edit")
    return datos


def actualizar_estrategiasmetodologicas(request):
    perfil = request.session['perfilprincipal']
    if perfil.es_estudiante():
        datos = {"result": "bad"}
    else:
        datos = {"result": "ok"}
        lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
        lecciongrupo.estrategiasmetodologicas = request.POST['val']
        lecciongrupo.save(request)
    return datos


def obtener_reporte(nombre):
    return Reporte.objects.filter(nombre=nombre).first() if Reporte.objects.filter(nombre=nombre).exists() else None


def ficha_socioeconomica(persona):
    if not persona.fichasocioeconomicainec_set.exists():
        fichasocioecon = FichaSocioeconomicaINEC(persona=persona)
        fichasocioecon.save()
    else:
        fichasocioecon = persona.fichasocioeconomicainec_set.all().first()
    return fichasocioecon


def valor_total_deudores_activos_30dias():
    hoy = datetime.now().date()
    fechavence = hoy - timedelta(days=30)
    return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy, fechavence__gte=fechavence).aggregate(valor=Sum('saldo'))['valor'], 2)


def valor_total_apagar_activos_30dias():
    hoy = datetime.now().date()
    fechavence = (datetime.now() + timedelta(days=30)).date()
    return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__gt=hoy, fechavence__lte=fechavence).aggregate(valor=Sum('saldo'))['valor'], 2)


def valor_total_deudores_activos_31_90dias():
    hoy = (datetime.now() - timedelta(days=31)).date()
    fechavence = (datetime.now() - timedelta(days=90)).date()
    return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lte=hoy, fechavence__gte=fechavence).aggregate(valor=Sum('saldo'))['valor'], 2)


def valor_total_apagar_activos_31_90dias():
    hoy = (datetime.now() + timedelta(days=31)).date()
    fechavence = (datetime.now() + timedelta(days=90)).date()
    return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__gte=hoy, fechavence__lte=fechavence).aggregate(valor=Sum('saldo'))['valor'], 2)


def valor_total_deudores_activos_mas_90dias():
    hoy = (datetime.now() - timedelta(days=91)).date()
    return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lte=hoy).aggregate(valor=Sum('saldo'))['valor'], 2)


def valor_total_apagar_activos_mas_90dias():
    hoy = (datetime.now() + timedelta(days=91)).date()
    return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__gte=hoy).aggregate(valor=Sum('saldo'))['valor'], 2)


def valor_deudores_activos_total():
    return valor_total_deudores_activos_30dias() + valor_total_deudores_activos_31_90dias() + valor_total_deudores_activos_mas_90dias()


def valor_apagar_activos_total():
    return valor_total_apagar_activos_30dias() + valor_total_apagar_activos_31_90dias() + valor_total_apagar_activos_mas_90dias()


def valor_deudas_activos_total():
    return valor_deudores_activos_total() + valor_apagar_activos_total()


def cantidad_total_deudores():
    return Inscripcion.objects.filter(rubro__fechavence__lt=datetime.now().date(), rubro__cancelado=False).distinct().count()


def cantidad_total_apagar():
    return Inscripcion.objects.filter(rubro__fechavence__gt=datetime.now().date(), rubro__cancelado=False).distinct().count()


def valor_total_deudores_activos_sede(sede):
    hoy = datetime.now().date()
    return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy, inscripcion__sede=sede).exclude(inscripcion__modalidad__id=3).aggregate(valor=Sum('saldo'))['valor'], 2)


def valor_total_deudores_activos_modalidad(modalidad):
    hoy = datetime.now().date()
    return null_to_numeric(Rubro.objects.filter(cancelado=False, pasivo=False, fechavence__lt=hoy, inscripcion__modalidad=modalidad).aggregate(valor=Sum('saldo'))['valor'], 2)


def nivel_matriculacion(inscripcion):
    opcionnivelfinal = None
    minivel = inscripcion.mi_nivel().nivel
    niveles = Nivel.objects.filter(nivellibrecoordinacion__coordinacion=inscripcion.coordinacion, modalidad=inscripcion.modalidad, sesion=inscripcion.sesion, sede=inscripcion.sede, cerrado=False, fin__gt=datetime.now().date(), periodo__matriculacionactiva=True)
    nivelessincronograma2 = Nivel.objects.filter(nivelestudiantesmatricula__isnull=True, nivellibrecoordinacion__coordinacion=inscripcion.coordinacion, modalidad=inscripcion.modalidad, sesion=inscripcion.sesion, sede=inscripcion.sede, cerrado=False, fin__gt=datetime.now().date(), periodo__matriculacionactiva=True)
    nivelessincronograma = nivelessincronograma2.filter(materia__carrera=inscripcion.carrera).distinct()
    if nivelessincronograma.count() >= 1:
        opcionnivelfinal = nivelessincronograma.first()
    for opcionnivel in niveles:
        if opcionnivel.nivelestudiantesmatricula_set.exists():
            for nivelmatricula in opcionnivel.nivelestudiantesmatricula_set.all():
                if nivelmatricula.carrera and nivelmatricula.nivelmalla and nivelmatricula.modalidad:
                    if nivelmatricula.nivelmalla == minivel and nivelmatricula.modalidad == inscripcion.modalidad and nivelmatricula.carrera == inscripcion.carrera:
                        opcionnivelfinal = opcionnivel
                        break
                elif nivelmatricula.carrera and nivelmatricula.nivelmalla and not nivelmatricula.modalidad:
                    if nivelmatricula.nivelmalla == minivel and nivelmatricula.carrera == inscripcion.carrera:
                        opcionnivelfinal = opcionnivel
                        break
                elif nivelmatricula.carrera and not nivelmatricula.nivelmalla and nivelmatricula.modalidad:
                    if nivelmatricula.carrera == inscripcion.carrera and nivelmatricula.modalidad == inscripcion.modalidad:
                        opcionnivelfinal = opcionnivel
                        break
                elif nivelmatricula.carrera and not nivelmatricula.nivelmalla and not nivelmatricula.modalidad:
                    if nivelmatricula.carrera == inscripcion.carrera:
                        opcionnivelfinal = opcionnivel
                        break
    return opcionnivelfinal


def existe_periodo_actualizacion_datos(tipo):
    fecha = datetime.now().date()
    if tipo == 1:
        return PeriodoActualizacionDatos.objects.filter(inicio__lte=fecha, fin__gte=fecha, paraalumnos=True).exists()
    elif tipo == 2:
        return PeriodoActualizacionDatos.objects.filter(inicio__lte=fecha, fin__gte=fecha, activo=True, paraprofesores=True).exists()
    else:
        return PeriodoActualizacionDatos.objects.filter(inicio__lte=fecha, fin__gte=fecha, activo=True, paraadministrativos=True).exists()


def periodo_actualizacion_datos(tipo):
    if existe_periodo_actualizacion_datos(tipo):
        fecha = datetime.now().date()
        if tipo == 1:
            return PeriodoActualizacionDatos.objects.filter(inicio__lte=fecha, fin__gte=fecha, paraalumnos=True).first()
        elif tipo == 2:
            return PeriodoActualizacionDatos.objects.filter(inicio__lte=fecha, fin__gte=fecha, activo=True, paraprofesores=True).first()
        else:
            return PeriodoActualizacionDatos.objects.filter(inicio__lte=fecha, fin__gte=fecha, activo=True, paraadministrativos=True).first()
    return None


def total_profesores_periodo(periodo):
    return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__periodo=periodo).distinct().count()


def total_docentes_tiempo_completo(periodo):
    return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__periodo=periodo, profesordistributivohoras__dedicacion__id=TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID).distinct().count()


def total_docentes_medio_tiempo(periodo):
    return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__periodo=periodo, profesordistributivohoras__dedicacion__id=TIEMPO_DEDICACION_MEDIO_TIEMPO_ID).distinct().count()


def total_docentes_tiempo_parcial(periodo):
    return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__periodo=periodo, profesordistributivohoras__dedicacion__id=TIEMPO_DEDICACION_PARCIAL_ID).distinct().count()


def existen_cajas_automaticas():
    return LugarRecaudacion.objects.filter(activo=True, automatico=True).exists()


def cartera_general_posgrado():
    hoy = datetime.now().date()
    return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy, pasivo=False, inscripcion__carrera__posgrado=True).aggregate(valor=Sum('saldo'))['valor'], 2)


def cierre_cajas_automaticas(fecha):
    if SesionCaja.objects.filter(caja__automatico=True, abierta=True, fecha__lt=fecha).exists():
        sc = SesionCaja.objects.filter(caja__automatico=True, abierta=True, fecha__lt=fecha).first()
        fecha = sc.fecha
        hora = sc.hora
        if sc.pago_set.exists():
            ultimopago = sc.pago_set.all().order_by('-fecha').first()
            hora = ultimopago.fecha_creacion.time()
        cierre = CierreSesionCaja(sesion=sc,
                                  tarjeta=null_to_numeric(Pago.objects.filter(pagotarjeta__isnull=False, sesion=sc, valido=True).aggregate(valor=Sum('valor'))['valor'], 2),
                                  total=null_to_numeric(Pago.objects.filter(pagotarjeta__isnull=False, sesion=sc, valido=True).aggregate(valor=Sum('valor'))['valor'], 2),
                                  fecha=fecha,
                                  hora=hora)
        cierre.save()
        sc.abierta = False
        sc.save()


def session_caja_automatica(fecha):
    cierre_cajas_automaticas(fecha)
    sc = None
    if existen_cajas_automaticas():
        lr = LugarRecaudacion.objects.filter(activo=True, automatico=True).first()
        if lr.sesioncaja_set.filter(fecha=fecha, abierta=True).exists():
            sc = lr.sesioncaja_set.filter(fecha=fecha, abierta=True).first()
        else:
            sc = SesionCaja(caja=lr,
                            fecha=fecha,
                            hora=datetime.now().time())
            sc.save()
    return sc


def fechas_semana(fecha):
    fecha_inicio = fecha
    diasemana = fecha.isoweekday()
    if diasemana != 1:
        fecha_inicio = fecha - timedelta(days=fecha.isoweekday() - 1)
    fecha_fin = fecha_inicio + timedelta(days=6)
    return [fecha_inicio, fecha_fin]


def rango_fechas(desde, hasta):
    from dateutil.relativedelta import relativedelta
    return [desde + relativedelta(days=days) for days in range((hasta - desde).days + 1)]


def tiene_url_obligatoria(request):
    if 'url_obligatoria' in request.session:
        lista = request.session['url_obligatoria']
        if len(lista) > 0:
            return True
    return False


def primera_url_obligatoria(request):
    if tiene_url_obligatoria(request):
        urls = request.session['url_obligatoria']
        return urls.first()
    return None


def add_url_obligatoria(request, url):
    if 'url_obligatoria' in request.session:
        lista = request.session['url_obligatoria']
        if url not in lista:
            lista.append(url)
    else:
        request.session['url_obligatoria'] = ['%s' % url, ]


def del_url_obligatoria(request, url):
    if 'url_obligatoria' in request.session:
        lista = request.session['url_obligatoria']
        try:
            lista.remove(url)
        except:
            pass
