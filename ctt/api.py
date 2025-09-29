# coding=utf-8

from datetime import datetime, timedelta

from django.db import transaction
from django.forms.models import model_to_dict
from django.http.response import JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from django.utils.encoding import smart_str
from django.views.decorators.csrf import csrf_exempt


from settings import MATRICULA_REGULAR_ID, MATRICULA_EXTRAORDINARIA_ID, PROFESORES_GROUP_ID, ALUMNOS_GROUP_ID, \
    EMPLEADORES_GRUPO_ID, ARCHIVO_TIPO_GENERAL, EMAIL_INSTITUCIONAL_AUTOMATICO_ESTUDIANTES
from ctt.finanzas import convertir_fecha
from ctt.funciones import remover_caracteres_especiales, ok_json, bad_json, generar_nombre, consulta_datos, generar_usuario, generar_email, remover_tildes
from ctt.models import *
from ctt.tasks import send_mail
import json


def login_required_inside(request):
    if 'persona' not in request.session:
        return Exception('Login required.')


@csrf_exempt
@transaction.atomic()
def view(request):
    global ex
    if request.method == 'POST':

        if 'a' in request.POST:
            action = request.POST['a']

            for api in Api.objects.filter(tipo=2, activo=True):
                if api.nombrecorto == action and api.key == request.POST['key']:
                    try:
                        globales = {"__builtins__": __builtins__}
                        locales = {}
                        exec(api.logicaapi, globales, locales)
                        resultado = locales['datosapi'](request)
                        return ok_json(data=resultado)
                    except Exception as ex:
                        return bad_json(error=ex)

            if action == 'nivelestitulacion':
                try:
                    login_required_inside(request)
                    niveltitulacion = NivelTitulacion.objects.get(pk=request.POST['id'])
                    lista = []
                    for detalleniveltitulacion in niveltitulacion.detalleniveltitulacion_set.all():
                        lista.append([detalleniveltitulacion.id, detalleniveltitulacion.nombre])
                    return ok_json({'lista': lista})
                except:
                    return bad_json(error=3)

            if action == 'datosexternospersona':
                try:
                    login_required_inside(request)
                    datosdevuletos = consulta_datos(request.POST['cedula'])
                    return ok_json(data=datosdevuletos)
                except:
                    return bad_json(error=3)

            if action == 'nivelestitulacion':
                try:
                    login_required_inside(request)
                    niveltitulacion = NivelTitulacion.objects.get(pk=request.POST['id'])
                    lista = []
                    for detalleniveltitulacion in niveltitulacion.detalleniveltitulacion_set.all():
                        lista.append([detalleniveltitulacion.id, detalleniveltitulacion.nombre])
                    return ok_json({'lista': lista})
                except:
                    return bad_json(error=3)

            if action == 'areasconocimientounesco':
                try:
                    login_required_inside(request)
                    areaconocimientounesco = AreaConocimientoUnesco.objects.get(pk=request.POST['id'])
                    lista = []
                    for subareaconocimientounesco in areaconocimientounesco.subareaconocimientounesco_set.all():
                        lista.append([subareaconocimientounesco.id, subareaconocimientounesco.nombre])
                    return ok_json({'lista': lista})
                except:
                    return bad_json(error=3)

            if action == 'areaaplicacionpasantia_subarea':
                try:
                    login_required_inside(request)
                    areaaplicacion = AreaAplicacionPasantia.objects.get(pk=request.POST['id'])
                    lista = []
                    for subareaconocimientounesco in areaaplicacion.subareaconocimientounesco_set.all():
                        lista.append([subareaconocimientounesco.id, subareaconocimientounesco.nombre])
                    return ok_json({'lista': lista})
                except:
                    return bad_json(error=3)

            if action == 'sublineainvestigacion':
                try:
                    login_required_inside(request)
                    linea = LineaInvestigacion.objects.get(pk=request.POST['id'])
                    lista = []
                    for sublinea in linea.sublineainvestigacion_set.all():
                        lista.append([sublinea.id, sublinea.nombre])
                    return ok_json({'lista': lista})
                except:
                    return bad_json(error=3)

            if action == 'cantones':
                try:
                    provincia = Provincia.objects.get(pk=request.POST['id'])
                    lista = []
                    for canton in provincia.canton_set.all():
                        lista.append([canton.id, canton.nombre])
                    return ok_json({'lista': lista})
                except:
                    return bad_json(error=3)

            if action == 'parroquias':
                try:
                    canton = Canton.objects.get(pk=request.POST['id'])
                    lista = []
                    for parroquia in canton.parroquia_set.all():
                        lista.append([parroquia.id, parroquia.nombre])
                    return ok_json({'lista': lista})
                except:
                    return bad_json(error=3)

            if action == 'coordinacionespersona':
                try:
                    login_required_inside(request)
                    persona = request.session['persona']
                    sede = Sede.objects.get(pk=int(request.POST['id']))
                    lista = []
                    for coordinacion in persona.lista_coordinaciones().filter(sede=sede,estado=True):
                        lista.append([coordinacion.id, coordinacion.nombre])
                    return ok_json({'lista': lista})
                except:
                    return bad_json(error=3)

            if action == 'sesionessede':
                try:
                    login_required_inside(request)
                    sede = Sede.objects.get(pk=int(request.POST['id']))
                    lista = []
                    for sesion in sede.sesion_set.all():
                        lista.append([sesion.id, sesion.nombre])
                    return ok_json({'lista': lista})
                except:
                    return bad_json(error=3)

            if action == 'carrerascoordinacion':
                try:
                    login_required_inside(request)
                    coordinacion = Coordinacion.objects.get(pk=int(request.POST['id']))
                    lista = []
                    for carrera in coordinacion.carrera.all():
                        lista.append([carrera.id, carrera.__str__()])
                    return ok_json({'lista': lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'carrerasmalla':
                try:
                    login_required_inside(request)
                    carrera = Carrera.objects.get(pk=int(request.POST['idcarrera']))
                    modalidad = Modalidad.objects.get(pk=int(request.POST['idmodalidad']))
                    lista = []
                    for malla in Malla.objects.filter(carrera=carrera, modalidad=modalidad,aprobado=True):
                        lista.append([malla.id, malla.__str__()])
                    return ok_json({'lista': lista})
                except:
                    return bad_json(error=3)

            if action == 'checkmail':
                try:
                    login_required_inside(request)
                    if 'persona' in request.session:
                        persona = request.session['persona']
                        return ok_json({'mensajes': persona.tiene_mensajes()})
                    return ok_json({'tienemensaje': False})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'chequeardeuda':
                try:
                    login_required_inside(request)
                    if 'persona' in request.session:
                        persona = request.session['persona']
                        return ok_json({'deudas': persona.tiene_deuda_vencida()})
                    return ok_json({'tienedeuda': False})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'checksession':
                try:
                    login_required_inside(request)
                    from settings import TIEMPO_CIERRE_SESION
                    nuevasesion = False
                    fa = datetime.now()
                    if 'ultimo_acceso' in request.session:
                        fa = request.session['ultimo_acceso']
                    else:
                        nuevasesion = True
                    if not nuevasesion:
                        if TIEMPO_CIERRE_SESION:
                            if (fa + timedelta(seconds=TIEMPO_CIERRE_SESION)) < datetime.now():
                                nuevasesion = True
                    soportedisponible = PersonalSoporte.objects.filter(disponible=True).exists()
                    tiket = None
                    if soportedisponible:
                        if SolicitudSoporte.objects.filter(persona=request.session['persona'], estado__in=[1, 2]).exists():
                            tiket = SolicitudSoporte.objects.filter(persona=request.session['persona'], estado__in=[1, 2])[0]
                    return ok_json({'nuevasesion': nuevasesion, 'soporte': soportedisponible, 'ticket': True if tiket else False, 'numero': tiket.numero if tiket else 0})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'closeticket':
                try:
                    login_required_inside(request)
                    if SolicitudSoporte.objects.filter(persona=request.session['persona'], estado=1).exists():
                        s = SolicitudSoporte.objects.filter(persona=request.session['persona'], estado=1)[0]
                        for solicitud in SolicitudSoporte.objects.filter(numero__gt=s.numero):
                            solicitud.numero -= 1
                            solicitud.save()
                        s.estado = 4
                        s.numero = 0
                        s.solucion = 'CANCELADO POR USUARIO'
                        s.save()
                    return ok_json()
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'checkticket':
                try:
                    login_required_inside(request)
                    activo = False
                    json_content = ''
                    nuevo = False
                    if SolicitudSoporte.objects.filter(persona=request.session['persona'], estado__in=[1, 2]).exists():
                        s = SolicitudSoporte.objects.filter(persona=request.session['persona'], estado__in=[1, 2])[0]
                        activo = s.personalsoporte != None
                        if s.estado == 2:
                            if s.mensajesoporte_set.filter(personalsoporte__isnull=False, impreso=False).exists():
                                mensaje = s.mensajesoporte_set.filter(personalsoporte__isnull=False, impreso=False).order_by('fechamensaje')[0]
                                mensaje.impreso = True
                                mensaje.save()
                                data = {}
                                data['mensaje'] = mensaje
                                template = get_template("adm_soporte/mensajesoporte.html")
                                json_content = template.render(data)
                                nuevo = True
                    return ok_json(data={'numero': s.numero if s else 0, 'activo': activo, 'nuevo': nuevo, 'html': json_content})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'sendmensajeclientsuport':
                try:
                    login_required_inside(request)
                    json_content = ''
                    if SolicitudSoporte.objects.filter(persona=request.session['persona'], estado__in=[1, 2]).exists():
                        s = SolicitudSoporte.objects.filter(persona=request.session['persona'], estado__in=[1, 2])[0]
                        mensaje = MensajeSoporte(solicitudsoporte=s,
                                                 persona=request.session['persona'],
                                                 descripcion=request.POST['mensaje'],
                                                 fechamensaje=datetime.now())
                        mensaje.save()
                        data = {}
                        data['mensaje'] = mensaje
                        template = get_template("adm_soporte/mensajepersona.html")
                        json_content = template.render(data)
                    return ok_json(data={'html':json_content})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'openticket':
                try:
                    login_required_inside(request)
                    proximo = 0
                    if PersonalSoporte.objects.filter(disponible=True).exists():
                        s = SolicitudSoporte(persona=request.session['persona'],
                                             tiposoporte_id=int(request.POST['tipo']),
                                             descripcion=request.POST['descripcion'],
                                             fecharegistro=datetime.now().date(),
                                             fechainiciosolicitud=datetime.now())
                        s.save()
                        numerounico = False
                        while not numerounico:
                            proximo = int(null_to_numeric(SolicitudSoporte.objects.aggregate(valor=Max('numero'))['valor'], 0)) + 1
                            s.numero = proximo
                            s.save()
                            if SolicitudSoporte.objects.filter(numero=proximo).count() == 1:
                                numerounico = True
                    return ok_json(data={'numero': proximo})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'data':
                try:
                    login_required_inside(request)
                    m = request.POST['model']
                    q = ''
                    if 'q' in request.POST:
                        q = request.POST['q'].upper().strip()
                    datos = busqueda_datos(m, q, request.session['perfilprincipal'])
                    return ok_json({"data": datos})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'integrantegrupo':
                try:
                    login_required_inside(request)
                    grupo = request.POST['grupo']
                    data = {}
                    json_content = ''
                    grupoid = 1
                    perfil = request.session['perfilprincipal']
                    if perfil.administrativo:
                        if grupo == 'ADMINISTRATIVOS':
                            datagrupos = []
                            for grupo in Group.objects.exclude(id__in=[PROFESORES_GROUP_ID, ALUMNOS_GROUP_ID, EMPLEADORES_GRUPO_ID]).distinct():
                                integrantes = []
                                for integrante in Persona.objects.filter(usuario__groups=grupo, perfilusuario__administrativo__isnull=False, perfilusuario__administrativo__activo=True).distinct():
                                    integrantes.append({'id': integrante.id, 'nombre': integrante.nombre_completo()})
                                datagrupos.append({'grupo': grupo.name, 'integrantes': integrantes, 'orden': grupoid})
                                grupoid += 1
                            data['datos'] = datagrupos
                            template = get_template("mailbox/integrantesgrupo.html")
                            json_content = template.render(data)
                        if grupo == 'PROFESORES':
                            datagrupos = []
                            for grupo in Group.objects.filter(id=PROFESORES_GROUP_ID).distinct():
                                integrantes = []
                                for integrante in Persona.objects.filter(usuario__groups=grupo, perfilusuario__profesor__isnull=False, perfilusuario__profesor__activo=True, perfilusuario__profesor__coordinacion__sede=perfil.administrativo.sede).distinct():
                                    integrantes.append({'id': integrante.id, 'nombre': integrante.nombre_completo()})
                                datagrupos.append({'grupo': grupo.name, 'integrantes': integrantes, 'orden': grupoid})
                                grupoid += 1
                            data['datos'] = datagrupos
                            template = get_template("mailbox/integrantesgrupo.html")
                            json_content = template.render(data)
                    if perfil.profesor:
                        if grupo == 'ADMINISTRATIVOS':
                            datagrupos = []
                            for grupo in Group.objects.exclude(id__in=[PROFESORES_GROUP_ID, ALUMNOS_GROUP_ID, EMPLEADORES_GRUPO_ID]).distinct():
                                integrantes = []
                                for integrante in Persona.objects.filter(usuario__groups=grupo, perfilusuario__administrativo__isnull=False, perfilusuario__administrativo__activo=True).distinct():
                                    integrantes.append({'id': integrante.id, 'nombre': integrante.nombre_completo()})
                                datagrupos.append({'grupo': grupo.name, 'integrantes': integrantes, 'orden': grupoid})
                                grupoid += 1
                            data['datos'] = datagrupos
                            template = get_template("mailbox/integrantesgrupo.html")
                            json_content = template.render(data)
                        if grupo == 'PROFESORES':
                            datagrupos = []
                            for grupo in Group.objects.filter(id=PROFESORES_GROUP_ID).distinct():
                                integrantes = []
                                for integrante in Persona.objects.filter(usuario__groups=grupo, perfilusuario__profesor__isnull=False, perfilusuario__profesor__activo=True, perfilusuario__profesor__coordinacion__sede=perfil.profesor.coordinacion.sede).distinct():
                                    integrantes.append({'id': integrante.id, 'nombre': integrante.nombre_completo()})
                                datagrupos.append({'grupo': grupo.name, 'integrantes': integrantes, 'orden': grupoid})
                                grupoid += 1
                            data['datos'] = datagrupos
                            template = get_template("mailbox/integrantesgrupo.html")
                            json_content = template.render(data)
                        if grupo == 'ESTUDIANTES':
                            datagrupos = []
                            for grupo in Materia.objects.filter(profesormateria__profesor=perfil.profesor, profesormateria__principal=True, cerrado=False).distinct():
                                integrantes = []
                                for integrante in Persona.objects.filter(inscripcion__matricula__materiaasignada__materia=grupo).distinct():
                                    integrantes.append({'id': integrante.id, 'nombre': integrante.nombre_completo()})
                                datagrupos.append({'grupo': grupo.__str__(), 'integrantes': integrantes, 'orden': grupoid})
                                grupoid += 1
                            for grupo in MateriaCursoEscuelaComplementaria.objects.filter(profesor=perfil.profesor, cerrada=False).distinct():
                                integrantes = []
                                for integrante in Persona.objects.filter(inscripcion__matriculacursoescuelacomplementaria__materiaasignadacurso__materia=grupo).distinct():
                                    integrantes.append({'id': integrante.id, 'nombre': integrante.nombre_completo()})
                                datagrupos.append({'grupo': grupo.__str__(), 'integrantes': integrantes, 'orden': grupoid})
                                grupoid += 1
                            for grupo in PreProyectoGrado.objects.filter(proyectogrado__isnull=False, proyectogrado__estado=1, tutorpreproyecto__profesor=perfil.profesor, tutorpreproyecto__principal=True).distinct():
                                integrantes = []
                                for integrante in grupo.inscripciones.all():
                                    integrantes.append({'id': integrante.persona.id, 'nombre': integrante.persona.nombre_completo()})
                                datagrupos.append({'grupo': 'ALUMNOS DE PROYECTO', 'integrantes': integrantes, 'orden': grupoid})
                                grupoid += 1
                            integrantes = []
                            datagrupos.append({'grupo': 'TUTORIADOS', 'integrantes': integrantes, 'orden': grupoid})
                            grupoid += 1
                            data['datos'] = datagrupos
                            template = get_template("mailbox/integrantesgrupo.html")
                            json_content = template.render(data)
                    if perfil.inscripcion:
                        if grupo == 'PROFESORES':
                            datagrupos = []
                            for grupo in Materia.objects.filter(materiaasignada__matricula__inscripcion=perfil.inscripcion, nivel__cerrado=False).distinct():
                                integrantes = []
                                for integrante in Persona.objects.filter(profesor__profesormateria__materia=grupo).distinct():
                                    integrantes.append({'id': integrante.id, 'nombre': integrante.nombre_completo()})
                                datagrupos.append({'grupo': grupo.__str__(), 'integrantes': integrantes, 'orden': grupoid})
                                grupoid += 1
                            for grupo in MateriaCursoEscuelaComplementaria.objects.filter(materiaasignadacurso__inscripcion__inscripcion=perfil.inscripcion, cerrada=False).distinct():
                                integrantes = []
                                integrantes.append({'id': grupo.profesor.persona.id, 'nombre': grupo.profesor.persona.nombre_completo()})
                                datagrupos.append({'grupo': grupo.__str__(), 'integrantes': integrantes, 'orden': grupoid})
                                grupoid += 1
                            for grupo in PreProyectoGrado.objects.filter(inscripciones=perfil.inscripcion, proyectogrado__isnull=False,proyectogrado__estado=1).distinct():
                                integrantes = []
                                for integrante in grupo.tutorpreproyecto_set.filter(principal=True):
                                    integrantes.append({'id': integrante.profesor.persona.id, 'nombre': integrante.profesor.persona.nombre_completo()})
                                datagrupos.append({'grupo': 'TUTOR DE PROYECTO', 'integrantes': integrantes, 'orden': grupoid})
                                grupoid += 1
                            integrantes = []
                            datagrupos.append({'grupo': 'TUTORES', 'integrantes': integrantes, 'orden': grupoid})
                            grupoid += 1
                            data['datos'] = datagrupos
                            template = get_template("mailbox/integrantesgrupo.html")
                            json_content = template.render(data)
                        if grupo == 'ESTUDIANTES':
                            datagrupos = []
                            for grupo in Materia.objects.filter(materiaasignada__matricula__inscripcion=perfil.inscripcion, nivel__cerrado=False).distinct():
                                integrantes = []
                                for integrante in Persona.objects.filter(inscripcion__matricula__materiaasignada__materia=grupo).distinct():
                                    integrantes.append({'id': integrante.id, 'nombre': integrante.nombre_completo()})
                                datagrupos.append({'grupo': grupo.__str__(), 'integrantes': integrantes, 'orden': grupoid})
                                grupoid += 1
                            data['datos'] = datagrupos
                            template = get_template("mailbox/integrantesgrupo.html")
                            json_content = template.render(data)
                        if grupo == 'ADMINISTRATIVOS':
                            datagrupos = []
                            for grupo in Group.objects.exclude(id__in=[PROFESORES_GROUP_ID, ALUMNOS_GROUP_ID, EMPLEADORES_GRUPO_ID]).distinct():
                                integrantes = []
                                for integrante in Persona.objects.filter(usuario__groups=grupo, perfilusuario__administrativo__isnull=False, perfilusuario__administrativo__activo=True).distinct():
                                    integrantes.append({'id': integrante.id, 'nombre': integrante.nombre_completo()})
                                datagrupos.append({'grupo': grupo.name, 'integrantes': integrantes, 'orden': grupoid})
                                grupoid += 1
                            data['datos'] = datagrupos
                            template = get_template("mailbox/integrantesgrupo.html")
                            json_content = template.render(data)
                    return ok_json(data={"html": json_content})
                except Exception as ex:
                    return bad_json(transaction, error=3)

            if action == 'sendmensaje':
                try:
                    login_required_inside(request)
                    destinatarios = json.loads(request.POST['lista_items1'])
                    files = []
                    for file in request.FILES:
                        newfile = request.FILES[file]
                        newfile._name = generar_nombre("adjunto_", newfile._name)
                        archivo = Archivo(nombre=newfile._name,
                                          fecha=datetime.now(),
                                          archivo=newfile,
                                          tipo_id=ARCHIVO_TIPO_GENERAL)
                        archivo.save()
                        files.append(archivo)
                    send_mail(subject=request.POST['asuntonuevomensaje'],
                              contenido=request.POST['contenidonuevomensaje'],
                              recipient_list=Persona.objects.filter(id__in=[int(x['id']) for x in destinatarios]).distinct(),
                              attachtment=files,
                              persona=request.session['persona'])
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'sedeadmision':
                try:
                    login_required_inside(request)
                    lista = []
                    for sede in Sede.objects.filter(detallefechapreinscripcion__activo=True,
                                                    detallefechapreinscripcion__fechapreinscripcion__fechainicio__lte=datetime.now().date(),
                                                    detallefechapreinscripcion__fechapreinscripcion__fechafin__gte=datetime.now().date(),
                                                    detallefechapreinscripcion__fechapreinscripcion__activo=True).distinct():
                        lista.append([sede.id, sede.nombre])
                    return ok_json({'lista': lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'carrerasadmision':
                try:
                    login_required_inside(request)
                    sede = Sede.objects.get(pk=request.POST['id'])
                    lista = []
                    for carrera in Carrera.objects.filter(detallefechapreinscripcion__activo=True,
                                                          detallefechapreinscripcion__fechapreinscripcion__fechainicio__lte=datetime.now().date(),
                                                          detallefechapreinscripcion__fechapreinscripcion__fechafin__gte=datetime.now().date(),
                                                          detallefechapreinscripcion__fechapreinscripcion__activo=True,
                                                          detallefechapreinscripcion__sede=sede).distinct():
                        lista.append([carrera.id, carrera.nombre_completo()])
                    return ok_json({'lista': lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'modalidadadmision':
                try:
                    login_required_inside(request)
                    sede = Sede.objects.get(pk=request.POST['id'])
                    lista = []
                    for modalidad in Modalidad.objects.filter(detallefechapreinscripcion__activo=True,
                                                              detallefechapreinscripcion__fechapreinscripcion__fechainicio__lte=datetime.now().date(),
                                                              detallefechapreinscripcion__fechapreinscripcion__fechafin__gte=datetime.now().date(),
                                                              detallefechapreinscripcion__fechapreinscripcion__activo=True,
                                                              detallefechapreinscripcion__sede=sede).distinct():
                        lista.append([modalidad.id, modalidad.nombre])
                    return ok_json({'lista': lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'mallaadmision':
                try:
                    login_required_inside(request)
                    sede = Sede.objects.get(pk=request.POST['id'])
                    lista = []
                    for malla in Malla.objects.filter(detallefechapreinscripcion__activo=True,
                                                      detallefechapreinscripcion__fechapreinscripcion__fechainicio__lte=datetime.now().date(),
                                                      detallefechapreinscripcion__fechapreinscripcion__fechafin__gte=datetime.now().date(),
                                                      detallefechapreinscripcion__fechapreinscripcion__activo=True,
                                                      detallefechapreinscripcion__sede=sede).distinct():
                        lista.append([malla.id, malla.nombre])
                    return ok_json({'lista': lista})
                except Exception as ex:
                    return bad_json(error=3)

            return bad_json(error=0)
    else:
        if 'a' in request.GET:
            action = request.GET['a']

            for api in Api.objects.filter(tipo=1, activo=True):
                if api.nombrecorto == action and api.key == request.GET['key']:
                    try:
                        globales = {"__builtins__": __builtins__}
                        locales = {}
                        exec(api.logicaapi, globales, locales)
                        resultado = locales['datosapi'](request)
                        return ok_json(data=resultado)
                    except Exception as ex:
                        return bad_json(error=ex)

            if action == 'consulta_requerimientos':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikey != request.GET['key']:
                            return bad_json(error=4)
                    qs = RequerimientoMesaAyuda.objects.select_related(
                        "personacrea", "personaencargada", "personaasigna", "campus", "tipo", "tipo__problema"
                    ).all().order_by("-id")

                    items = []
                    for r in qs:
                        items.append({
                            "id": r.id,
                            "fecharequerimiento": r.fecharequerimiento.isoformat() if r.fecharequerimiento else None,
                            "personacrea": str(r.personacrea) if r.personacrea_id else None,
                            "personaasigna": str(r.personaasigna) if r.personaasigna_id else None,
                            "personaencargada": str(r.personaencargada) if r.personaencargada_id else None,
                            "campus_id": r.campus_id,
                            "campus": str(r.campus) if r.campus_id else None,
                            "tipo_id": r.tipo_id,
                            "tipo": str(r.tipo) if r.tipo_id else None,
                            "problema_id": getattr(r.tipo, "problema_id", None) if r.tipo_id else None,
                            "problema": str(getattr(r.tipo, "problema", "")) if r.tipo_id else None,
                            "descripcion": r.descripcion or "",
                            "emailsolicitante": r.emailsolicitante or "",
                            "gravedad": getattr(r, "get_gravedad_display", lambda: None)(),
                            "estadodesarrolloprocesos": getattr(r, "get_estadodesarrolloprocesos_display",
                                                                lambda: None)(),
                            "estadorequerimiento": getattr(r, "get_estadorequerimiento_display", lambda: None)(),
                            "avance": r.avance,
                            "fechaasigna": r.fechaasigna.isoformat() if r.fechaasigna else None,
                            "horainicio": r.horainicio.isoformat() if r.horainicio else None,
                            "fechainicio": r.fechainicio.isoformat() if r.fechainicio else None,
                            "horafin": r.horafin.isoformat() if r.horafin else None,
                            "fechafin": r.fechafin.isoformat() if r.fechafin else None,
                        })

                    # Solo lista, sin envoltorios
                    return JsonResponse(items, safe=False)

                except Exception as e:
                    return JsonResponse({"error": str(e)}, status=500)

            if action == 'mensaje':
                try:
                    login_required_inside(request)
                    data = {}
                    ids = request.GET['ids'].split(',')
                    try:
                        data['destinatarios'] = Persona.objects.filter(id__in=[int(x) for x in ids]).distinct()
                    except Exception as ex:
                        pass
                    data['gruposcontacto'] = []
                    if request.session['perfilprincipal'].administrativo:
                        data['gruposcontacto'] = ['ADMINISTRATIVOS', 'PROFESORES']
                    if request.session['perfilprincipal'].profesor:
                        data['gruposcontacto'] = ['ADMINISTRATIVOS', 'PROFESORES', 'ESTUDIANTES']
                    if request.session['perfilprincipal'].inscripcion:
                        data['gruposcontacto'] = ['ADMINISTRATIVOS', 'PROFESORES', 'ESTUDIANTES']
                    return render(request, "nuevomensaje.html", data)
                except Exception as ex:
                    return bad_json(transaction, error=3)

            if action == 'printusers':
                try:
                    cajeros = []
                    lugaresrecaudacion = LugarRecaudacion.objects.all()
                    for caja in lugaresrecaudacion:
                        if caja.persona not in cajeros:
                            cajeros.append(caja.persona)
                    usuarios = []
                    for cajero in cajeros:
                        usuarios.append({'id': cajero.usuario.id, 'username': cajero.usuario.username, 'fullname': cajero.nombre_completo()})
                    return ok_json(usuarios, simple=True, safe=False)
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'printstart':
                try:
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'printdoc':
                try:
                    import unicodedata
                    docs = []
                    for i in Impresion.objects.filter(usuario__id=request.GET['usuario'], impresa=False)[:5]:
                        try:
                            texto = i.contenido.replace("\\", "")
                            contenido = texto.encode('utf-8', 'replace')
                            if len(contenido) > 0:
                                docs.append(json.loads(contenido, strict=False))
                        except Exception as ex:
                            pass
                    return ok_json(docs, simple=True, safe=False)
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'printdone':
                try:
                    impresion = Impresion.objects.get(pk=request.GET['id'])
                    impresion.impresa = True
                    impresion.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=3, ex=ex)

            if action == 'cajas':
                try:
                    return ok_json([model_to_dict(x) for x in LugarRecaudacion.objects.all().order_by('id')], simple=True)
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'cajasdisponibles':
                try:
                    login_required_inside(request)
                    cajas = {}
                    for c in LugarRecaudacion.objects.all():
                        r = {"id": c.id, "caja": remover_caracteres_especiales(c.nombre), "persona": remover_caracteres_especiales(c.persona.nombre_completo()), "puntoventa": c.puntodeventa.numeracion()}
                        cajas.update({"id_" + str(c.id): r})
                    return ok_json(cajas)
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'carreras':
                try:
                    login_required_inside(request)
                    carreras = {}
                    for c in Carrera.objects.all():
                        r = {'id': c.id, 'nombre': u"%s" % c, 'posgrado': c.tipogrado.id == CUARTO_NIVEL_TITULACION_ID }
                        carreras.update({"id_" + str(c.id): r})
                    return ok_json(carreras)
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'especies':
                try:
                    login_required_inside(request)
                    especies = {}
                    for e in TipoEspecieValorada.objects.all():
                        r = {'id': e.id, 'nombre': u"%s" % e }
                        especies.update({"id_" + str(e.id): r})
                    return ok_json(especies)
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'tiposcurso':
                try:
                    login_required_inside(request)
                    tipos = {}
                    for t in TipoCostoCurso.objects.all():
                        r = {'id': t.id, 'nombre': u"%s" % t }
                        tipos.update({"id_" + str(t.id): r})
                    return ok_json(tipos)
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'centrosapoyo':
                try:
                    login_required_inside(request)
                    centro = {}
                    for c in CentroApoyo.objects.all():
                        r = {'id': c.id, 'nombre': c.nombre }
                        centro.update({"id_" + str(c.id): r})
                    return ok_json(centro)
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'modalidades':
                try:
                    login_required_inside(request)
                    modalidades = {}
                    for c in Modalidad.objects.all():
                        r = {'id': c.id, 'nombre': c.nombre}
                        modalidades.update({"id_" + str(c.id): r})
                    return ok_json(modalidades)
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'tipootrosrubros':
                try:
                    login_required_inside(request)
                    tipos = {}
                    for c in TipoOtroRubro.objects.all():
                        r = {'id': c.id, 'nombre': c.nombre, 'precio': c.precio}
                        tipos.update({"id_" + str(c.id): r})
                    return ok_json(tipos)
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'aulas':
                try:
                    login_required_inside(request)
                    lista = []
                    for x in Aula.objects.all():
                        d = model_to_dict(x)
                        d['sede'] = x.sede.nombre.encode("ascii", "ignore")
                        d['tipo'] = x.tipo.nombre.encode("ascii", "ignore")
                        lista.append(d)
                    return ok_json({"total": Aula.objects.all().count(), "aulas": lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'datosfacturacion':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikey != request.GET['key']:
                            return bad_json(error=4)
                    return ok_json(exportacion_datos_facturacion(fecha=convertir_fecha(request.GET['fecha'])))
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'datospersonal':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikey != request.GET['key']:
                            return bad_json(error=4)
                    datos = exportacion_datos_persona()
                    return ok_json(datos)
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'datosrecibopago':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikey != request.GET['key']:
                            return bad_json(error=4)
                    return ok_json(exportacion_datos_recibopago(fecha=convertir_fecha(request.GET['fecha'])))
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'datosvales':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikey != request.GET['key']:
                            return bad_json(error=4)
                    return ok_json(exportacion_datos_vales_caja(fecha=convertir_fecha(request.GET['fecha'])))
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'notascredito':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikey != request.GET['key']:
                            return bad_json(error=4)
                    return ok_json(exportacion_datos_notacredito(convertir_fecha(request.GET['fecha'])))
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'factura':
                try:
                    factura = Factura.objects.get(pk=request.GET['id'])
                    factura.impresa = True
                    factura.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'periodos':
                try:
                    login_required_inside(request)
                    lista = []
                    for x in Periodo.objects.all():
                        r = {'id': x.id, 'nombre': x.nombre, 'inicio': x.inicio.strftime("%d-%m-%Y"), 'fin': x.fin.strftime("%d-%m-%Y") }
                        lista.append(r)
                    return ok_json({"periodos": lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'moodles':
                try:
                    login_required_inside(request)
                    lista = []
                    for x in Moodle.objects.all():
                        r = {'id': x.id, 'nombre': x.nombre, 'url': x.urlnotas}
                        lista.append(r)
                    return ok_json({"moodles": lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'sedes':
                try:
                    login_required_inside(request)
                    lista = []
                    for x in Sede.objects.all():
                        r = {'id': x.id, 'nombre': x.nombre}
                        lista.append(r)
                    return ok_json({"sedes": lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'coordinaciones':
                try:
                    login_required_inside(request)
                    lista = []
                    for x in Coordinacion.objects.all():
                        r = {'id': x.id, 'nombre': x.nombre, 'idsede': x.sede_id}
                        lista.append(r)
                    return ok_json({"coordinaciones": lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'docentes':
                try:
                    login_required_inside(request)
                    lista = []
                    sede = Sede.objects.get(pk=int(request.GET['idsede']))
                    for x in Profesor.objects.filter(coordinacion__sede=sede):
                        r = {'id': x.id, 'nombre1': x.persona.nombre1, 'nombre2': x.persona.nombre2, 'apellido1': x.persona.apellido1, 'apellido2': x.persona.apellido2, 'cedula': x.persona.cedula, 'pasaporte': x.persona.pasaporte, 'emailinst': x.persona.emailinst, 'email': x.persona.email, 'movil': x.persona.telefono}
                        lista.append(r)
                    return ok_json({"docentes": lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'distributivodocente':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikey != request.GET['key']:
                            return bad_json(error=4)
                    lista = []
                    fechainicio = convertir_fecha(request.GET['fi'])
                    fechafin = convertir_fecha(request.GET['ff'])
                    for profesor in Profesor.objects.filter(Q(profesordistributivohoras__periodo__inicio__gte=fechainicio, profesordistributivohoras__periodo__inicio__lte=fechafin) | Q(profesordistributivohoras__periodo__fin__gte=fechainicio, profesordistributivohoras__periodo__fin__lte=fechafin) | Q(profesordistributivohoras__periodo__inicio__lte=fechainicio, profesordistributivohoras__periodo__fin__gte=fechafin) | Q(profesordistributivohoras__periodo__inicio__gte=fechainicio, profesordistributivohoras__periodo__fin__lte=fechafin), Q(profesordistributivohoras__horasdocencia__gt=0) | Q(profesordistributivohoras__horasinvestigacion__gt=0) | Q(profesordistributivohoras__horasgestion__gt=0)).distinct():
                        distributivo_periodo = {}
                        total_clases = null_to_numeric(Turno.objects.filter(lecciongrupo__fecha__gte=fechainicio, lecciongrupo__fecha__lte=fechafin, lecciongrupo__profesor=profesor).aggregate(valor=Sum('horas'))['valor'], 1)
                        total_actividades = null_to_numeric(ActividadDetalleDistributivo.objects.filter(fecha__gte=fechainicio, fecha__lte=fechafin, criterio__distributivo__profesor=profesor).aggregate(valor=Sum('horas'))['valor'], 1)
                        for distributivo in ProfesorDistributivoHoras.objects.filter(Q(periodo__inicio__gte=fechainicio, periodo__inicio__lte=fechafin) | Q(periodo__fin__gte=fechainicio, periodo__fin__lte=fechafin) | Q(periodo__inicio__lte=fechainicio, periodo__fin__gte=fechafin) | Q(periodo__inicio__gte=fechainicio, periodo__fin__lte=fechafin), Q(horasdocencia__gt=0) | Q(horasinvestigacion__gt=0) | Q(horasgestion__gt=0), profesor=profesor).distinct():
                            lista_resumen_modalidad = []
                            lista_carreras = []
                            lista_materias_malla = Materia.objects.filter(asignaturamalla__isnull=False, profesormateria__profesor=profesor).distinct().values_list('asignaturamalla__id', flat=True)
                            lista_materias_modulo = Materia.objects.filter(modulomalla__isnull=False, profesormateria__profesor=profesor).distinct().values_list('modulomalla__id', flat=True)
                            for carrera in Carrera.objects.filter(Q(malla__asignaturamalla__id__in=lista_materias_malla) | Q(malla__modulomalla__id__in=lista_materias_modulo)).distinct():
                                lista_modalidades = []
                                for modalidad in Modalidad.objects.filter(Q(malla__asignaturamalla__id__in=lista_materias_malla) | Q(malla__modulomalla__id__in=lista_materias_modulo)).distinct():
                                    if {'id': modalidad.id, 'nombre': modalidad.nombre} not in lista_modalidades:
                                        lista_modalidades.append({'id': modalidad.id, 'nombre': modalidad.nombre})
                                lista_carreras.append({'id': carrera.id, 'nombre': carrera.nombre, 'modalidades': lista_modalidades})
                            for d in distributivo.resumenmodalidad_set.all():
                                lista_resumen_modalidad.append({'modid': d.modalidad.id, 'nombremod': d.modalidad.nombre, 'carreraid': d.carrera.id, 'carreranombre': d.carrera.nombre, 'porciento': d.porciento})
                            distributivo_periodo = {'horastotales': null_to_numeric(distributivo.horasdocencia + distributivo.horasgestion + distributivo.horasinvestigacion, 1), 'horasdocencia': distributivo.horasdocencia, 'horasgestion': distributivo.horasgestion, 'horasinvestigacion': distributivo.horasinvestigacion, 'lista_carreras': lista_carreras, 'lista_resumen': lista_resumen_modalidad}
                        datoprofesor = {'profesor': profesor.persona.nombre_completo(), 'identificacion': profesor.persona.identificacion(), 'distributivo': distributivo_periodo, 'ejecucion_horas_clases': total_clases, 'ejecucion_horas_otras_actividades': total_actividades}
                        lista.append(datoprofesor)
                    return ok_json({"docentes": lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'distributivoperiodo':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikey != request.GET['key']:
                            return bad_json(error=4)
                    lista = []
                    periodo = request.GET['p']
                    for profesor in Profesor.objects.filter(Q(profesordistributivohoras__periodo__id=periodo), Q(profesordistributivohoras__horasdocencia__gt=0) | Q(profesordistributivohoras__horasinvestigacion__gt=0) | Q(profesordistributivohoras__horasgestion__gt=0)).distinct().exclude(id__in=[985, 2089, 1391, 1508]).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombre1', 'persona__nombre2'):
                        # for profesor in Profesor.objects.filter(Q(profesordistributivohoras__periodo__id=periodo),
                        #                                         Q(profesordistributivohoras__horasdocencia__gt=0) |
                        #                                         Q(profesordistributivohoras__horasinvestigacion__gt=0) |
                        #                                         Q(profesordistributivohoras__horasgestion__gt=0),
                        #                                         persona__id__in=[69798,69799,69815,69820,69822,69821,69816,69817,69818,69819,69903,69904,69906,69905,69909,65271,65270,65274,67113]).distinct().order_by('persona__apellido1', 'persona__apellido2', 'persona__nombre1', 'persona__nombre2'):
                        for distributivo in ProfesorDistributivoHoras.objects.filter(Q(periodo=periodo), Q(horasdocencia__gt=0) | Q(horasinvestigacion__gt=0) | Q(horasgestion__gt=0), profesor=profesor, verificacionth=True, dedicacion_id=3).distinct():
                            # for distributivo in ProfesorDistributivoHoras.objects.filter(Q(periodo=periodo), Q(horasdocencia__gt=0) | Q(horasinvestigacion__gt=0) | Q(horasgestion__gt=0), profesor=profesor, verificacionth=True, dedicacion_id=4).distinct():
                            materiainicio = None
                            materiafin = None
                            materiainiciopractica = None
                            materiafinpractica = None
                            if Materia.objects.filter(profesormateria__profesor=profesor, nivel__periodo_id=periodo).exists():
                                materiainicio = Materia.objects.filter(profesormateria__profesor=profesor, nivel__periodo_id=periodo).order_by('inicio')[0]
                            if Materia.objects.filter(profesormateria__profesor=profesor, nivel__periodo_id=periodo).exists():
                                materiafin = Materia.objects.filter(profesormateria__profesor=profesor, nivel__periodo_id=periodo).order_by('-fin')[0]
                            if Materia.objects.filter(grupospracticas__profesormateriapracticas__profesor=profesor, nivel__periodo_id=periodo).exists():
                                materiainiciopractica = Materia.objects.filter(grupospracticas__profesormateriapracticas__profesor=profesor, nivel__periodo_id=periodo).order_by('inicio')[0]
                            if Materia.objects.filter(grupospracticas__profesormateriapracticas__profesor=profesor, nivel__periodo_id=periodo).exists():
                                materiafinpractica = Materia.objects.filter(grupospracticas__profesormateriapracticas__profesor=profesor, nivel__periodo_id=periodo).order_by('-fin')[0]
                            if distributivo.carrera and distributivo.modalidad:
                                if distributivo.carrera.mencion:
                                    nombrecarrera = distributivo.carrera.nombre + " CON MENCION EN " + distributivo.carrera.mencion
                                else:
                                    nombrecarrera = distributivo.carrera.nombre if distributivo.carrera.nombre != '' else ''
                            if profesor.persona.mis_datosbancarios():
                                banco = profesor.persona.mis_datosbancarios().banco.codigo_banco()
                                nombrebanco = profesor.persona.mis_datosbancarios().banco.nombre
                                tipocuenta = profesor.persona.mis_datosbancarios().tipocuenta.nombre
                                numerocuenta = profesor.persona.mis_datosbancarios().numero
                            else:
                                banco = 0
                                nombrebanco = ''
                                tipocuenta = ''
                                numerocuenta = ''
                            datoprofesor = {'periodo': distributivo.periodo.nombre,
                                            'idperiodo': distributivo.periodo.id,
                                            'pais': profesor.persona.pais.nombre,
                                            'canton': profesor.persona.canton.nombre if profesor.persona.canton else '',
                                            'parroquia': profesor.persona.parroquia.nombre if profesor.persona.parroquia else '',
                                            'contrato': distributivo.codigocontrato,
                                            'profesor': profesor.persona.nombre_completo(),
                                            'identificacion': profesor.persona.identificacion(),
                                            'tipoidentificacion': profesor.persona.tipo_identificacion(),
                                            'nombres': profesor.persona.nombres_completos(),
                                            'apellido1': profesor.persona.apellido1,
                                            'apellido2': profesor.persona.apellido2,
                                            'email': profesor.persona.emailinst,
                                            'direccion': profesor.persona.mi_direccion(),
                                            'provincia': profesor.persona.provincia.nombre if profesor.persona.provincia else '',
                                            'banco': banco,
                                            'nombrebanco': nombrebanco,
                                            'tipocuenta': tipocuenta,
                                            'numerocuenta': numerocuenta,
                                            'facultad': distributivo.coordinacion.nombre if distributivo.coordinacion.nombre !='' else '',
                                            'idfacultad': distributivo.coordinacion.id if distributivo.coordinacion.nombre !='' else 0,
                                            'carrera': nombrecarrera,
                                            'idcarrera': distributivo.carrera.id if distributivo.carrera.id != None else 0,
                                            'modalidad': distributivo.modalidad.nombre if distributivo.modalidad.nombre !='' else '',
                                            'idmodalidad': distributivo.modalidad.id if distributivo.modalidad.nombre != None else 0,
                                            'tiempo': distributivo.dedicacion.nombre if distributivo.dedicacion.nombre != '' else '',
                                            'inicio': materiainiciopractica.inicio.strftime("%d-%m-%Y") if materiainiciopractica else materiainicio.inicio.strftime("%d-%m-%Y"),
                                            'fin': materiafinpractica.fin.strftime("%d-%m-%Y") if materiafinpractica else materiafin.fin.strftime("%d-%m-%Y")}
                            lista.append(datoprofesor)
                    return ok_json({"docentes": lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'alumnosmatriculados':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikey != request.GET['key']:
                            return bad_json(error=4)
                    fecha = convertir_fecha(request.GET['f'])
                    datos = {}
                    totalm = Matricula.objects.filter(fecha__lte=fecha, nivel__fin__gte=fecha).distinct().count()
                    for sede in Sede.objects.all():
                        datosm = {}
                        for modalidad in Modalidad.objects.all():
                            datosc = {}
                            for carrera in Carrera.objects.all():
                                cantidad = Matricula.objects.filter(fecha__lte=fecha, nivel__fin__gte=fecha, inscripcion__carrera=carrera, inscripcion__sede=sede, inscripcion__modalidad=modalidad).distinct().count()
                                datosmt = {"nombre": u"%s" % carrera, "datos": cantidad, "POSTG": carrera.posgrado}
                                datosc.update({carrera.id: datosmt})
                            datosm.update({modalidad.id: {"nombre": modalidad.nombre, "datos": datosc}})
                        datos.update({sede.id: {"nombre": sede.nombre, "datos": datosm}})
                    return ok_json({"datos": datos, "total": totalm})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'distribucion':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikey != request.GET['key']:
                            return bad_json(error=4)
                    periodo = request.GET['p']
                    cont = 1
                    datos = {}
                    totalr = ResumenModalidadCriterio.objects.filter(distributivo__periodo_id=periodo, distributivo__profesor__dependenciauti=True).distinct().count()
                    for resumen in ResumenModalidadCriterio.objects.filter(distributivo__periodo_id=periodo, distributivo__profesor__dependenciauti=True):
                        docente = resumen.distributivo.profesor.persona
                        dato = {"identificacion": u"%s" % docente.cedula, "docente": u"%s" % docente.nombre_completo(), "ceco": u"%s %s %s" % (resumen.sede, resumen.modalidad, resumen.carrera),"POSTG": resumen.carrera.posgrado, "porciento": resumen.porciento}
                        datos.update({cont: dato})
                        cont+=1
                    return ok_json({"datos": datos, "total": totalr})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'niveles':
                try:
                    login_required_inside(request)
                    lista = []
                    periodo = Periodo.objects.get(pk=int(request.GET['idperiodo']))
                    for x in Nivel.objects.filter(periodo=periodo):
                        r = {'id': x.id, 'nombre': x.paralelo, 'idcoordinacion': x.coordinacion().id }
                        lista.append(r)
                    return ok_json({"niveles": lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'materiasnivelcarrera':
                try:
                    login_required_inside(request)
                    lista = []
                    carrera = Carrera.objects.get(pk=int(request.GET['idcarrera']))
                    nivel = Nivel.objects.get(pk=int(request.GET['idnivel']))
                    for x in Materia.objects.filter(Q(asignaturamalla__malla__carrera=carrera) | Q(modulomalla__malla__carrera=carrera), nivel=nivel):
                        listadocentes = []
                        for j in x.profesormateria_set.all():
                            r1 = {'id': j.profesor.id, 'nombre1': j.profesor.persona.nombre1, 'nombre2': j.profesor.persona.nombre2, 'apellido1': j.profesor.persona.apellido1, 'apellido2': j.profesor.persona.apellido2, 'cedula': j.profesor.persona.cedula, 'pasaporte': j.profesor.persona.pasaporte, 'emailinst': j.profesor.persona.emailinst, 'email': j.profesor.persona.email, 'movil': j.profesor.persona.telefono}
                            listadocentes.append(r1)
                        listacampos = []
                        for m in x.modeloevaluativo.detallemodeloevaluativo_set.filter(dependiente=False):
                            r2 = {'id': m.id, 'nombrecampo': m.nombre }
                            listacampos.append(r2)
                        r = {'id': x.id, 'nombre': x.asignatura.nombre, 'horas': x.horas, 'creditos': x.creditos, 'docentes': listadocentes, 'modeloevaluativo': listacampos}
                        lista.append(r)
                    return ok_json({"niveles": lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'estudiante':
                try:
                    login_required_inside(request)
                    identificacion = request.GET['identificacion']
                    if not identificacion:
                        raise Exception
                    if not Persona.objects.filter(Q(cedula=identificacion) | Q(pasaporte=identificacion)).exists():
                        raise Exception
                    persona = Persona.objects.filter(Q(cedula=request.GET['identificacion']) | Q(pasaporte=request.GET['identificacion']))[0]
                    for x in persona.inscripcion_set.all():
                        listacarreras = []
                        r = {'sede':x.sede.nombre,'facultad':x.coordinacion.nombre, 'carrera': x.carrera.nombre, 'modalidad': x.modalidad.nombre,'idperiodo': x.periodo.nombre}
                        listacarreras.append(r)
                    return ok_json({"estudiante": persona.id, 'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1, 'apellido2': persona.apellido2, 'cedula': persona.cedula, 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email, 'movil': persona.telefono, 'carreras': listacarreras})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'estudiantemooc':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikeymooc != request.GET['key']:
                            return bad_json(error=4)
                    identificacion = request.GET['identificacion']
                    curso = request.GET['curso']
                    if not identificacion:
                        raise Exception
                    if not Persona.objects.filter(Q(cedula=identificacion) | Q(pasaporte=identificacion)).exists():
                        raise Exception
                    persona = Persona.objects.filter(Q(cedula=request.GET['identificacion']) | Q(pasaporte=request.GET['identificacion']))[0]
                    coordinacion=Coordinacion.objects.get(id=28)
                    if Inscripcion.objects.filter(persona=persona, coordinacion=coordinacion).exists():
                        i = Inscripcion.objects.get(persona=persona, coordinacion=coordinacion)
                        if curso == 'A':
                            r = Rubro.objects.filter(inscripcion=i, nombre="CURSO: NORMAS APA", rubronotadebito__isnull=True)[0]
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                        if curso == 'B':
                            r = Rubro.objects.get(inscripcion=i, nombre="CURSO: MS. EXCEL ONLINE", rubronotadebito__isnull=True)
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                        if curso == 'C':
                            r = Rubro.objects.get(inscripcion=i, nombre="CURSO: MOOC - INGLES A1", rubronotadebito__isnull=True)
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                        if curso == 'D':
                            r = Rubro.objects.get(inscripcion=i, nombre="CURSO: MOOC - FRANCES A1", rubronotadebito__isnull=True)
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                        if curso == 'E':
                            r = Rubro.objects.filter(inscripcion_id=i,nombre='CURSO: EXCEL BASICO', rubronotadebito__isnull=True)[0]
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                        if curso == 'F':
                            r = Rubro.objects.get(inscripcion=i, nombre="CURSO: GESTION DE REFERENCIAS CON HERRAMIENTAS INFORMATICAS", rubronotadebito__isnull=True)
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                        if curso == 'G':
                            r = Rubro.objects.get(inscripcion=i, nombre="CURSO: DISEÑO GRAFICO PARA REDES SOCIALES", rubronotadebito__isnull=True)
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                        if curso == 'H':
                            r = Rubro.objects.get(inscripcion=i, nombre="CURSO: DISEÑO DE MATERIAL DIDACTICO INTERACTIVO", rubronotadebito__isnull=True)
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                        if curso == 'I':
                            r = Rubro.objects.get(inscripcion=i, nombre="CURSO: GEORREFERENCIACION DE DATOS A TRAVES DE EXCEL Y ORANGE", rubronotadebito__isnull=True)
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                        if curso == 'J':
                            r = Rubro.objects.get(inscripcion=i, nombre="CURSO: ESCRITURA DE ARTICULOS CIENTIFICOS", rubronotadebito__isnull=True)
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                        if curso == 'K':
                            r = Rubro.objects.get(inscripcion=i, nombre="CURSO: GENERO Y DDHH", rubronotadebito__isnull=True)
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                        if curso == 'L':
                            r = Rubro.objects.get(inscripcion=i, nombre="CURSO: ESTIMULACION TEMPRANA", rubronotadebito__isnull=True)
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                        if curso == 'M':
                            r = Rubro.objects.get(inscripcion=i, nombre="CURSO: INTERVENCION PSICOLOGICA DEL DUELO", rubronotadebito__isnull=True)
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                        if curso == 'N':
                            r = Rubro.objects.filter(inscripcion_id=i, nombre="CURSO: NARRATIVAS DIGITALES COMO ESTRATEGIAS DIDACTICAS", rubronotadebito__isnull=True)[0]
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                        if curso == 'O':
                            r = Rubro.objects.filter(inscripcion_id=i,nombre='CURSO: RECUPERACION PSICOPEDAGOGICA MEDIANTE EL USO DE TITI APP', rubronotadebito__isnull=True)[0]
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                        if curso == 'P':
                            r = Rubro.objects.filter(inscripcion_id=i,nombre='	CURSO: ANALISIS DE REDES SOCIALES A TRAVES DE EXCEL Y GEPHI', rubronotadebito__isnull=True)[0]
                            return ok_json(
                                {'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1,
                                 'apellido2': persona.apellido2, 'cedula': persona.cedula,
                                 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email,
                                 'usuario': persona.usuario.username, 'cancelado': True if r.cancelado else False})
                    else:
                        return bad_json(error=3)
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'adpersona':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikeymooc != request.GET['key']:
                            return bad_json(error=4)
                    identificacion = request.GET['identificacion']
                    if not identificacion:
                        raise Exception
                    if not Persona.objects.filter(Q(cedula=identificacion) | Q(pasaporte=identificacion)).exists():
                        raise Exception
                    persona = Persona.objects.filter(Q(cedula=request.GET['identificacion']) | Q(pasaporte=request.GET['identificacion']))[0]
                    departamento = ''
                    if persona.es_estudiante():
                        departamento = 'usuarios'
                    else:
                        if persona.es_administrativo():
                            departamento = ''
                            if persona.es_profesor():
                                departamento = 'docentes'
                    return ok_json({'nombre1': persona.nombre1,
                                    'nombre2': persona.nombre2,
                                    'apellido1': persona.apellido1,
                                    'apellido2': persona.apellido2,
                                    'identificacion': persona.cedula if persona.cedula != '' else persona.pasaporte,
                                    'usuario': persona.usuario.username,
                                    'correo': persona.emailinst,
                                    'compania': 'compania',
                                    'departamento': departamento,
                                    'titulo': 'titulo',
                                    'contrasenia': 'contrasenia',
                                    'telefono': persona.telefono,
                                    'portal': 'CTT;',
                                    'estado': 1})
                    return bad_json(error=3)
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'matriculadosmateria':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikeymooc != request.GET['key']:
                            return bad_json(error=4)
                    lista = []
                    materia = Materia.objects.get(pk=int(request.GET['idmateria']))
                    for x in materia.materiaasignada_set.all():
                        r1 = {'id': x.id, 'nombre1': x.matricula.inscripcion.persona.nombre1, 'nombre2': x.matricula.inscripcion.persona.nombre2, 'apellido1': x.matricula.inscripcion.persona.apellido1, 'apellido2': x.matricula.inscripcion.persona.apellido2, 'cedula': x.matricula.inscripcion.persona.cedula, 'pasaporte': x.matricula.inscripcion.persona.pasaporte, 'emailinst': x.matricula.inscripcion.persona.emailinst, 'email': x.matricula.inscripcion.persona.email, 'movil': x.matricula.inscripcion.persona.telefono, 'centroinformacion': x.matricula.inscripcion.centroinformacion.nombre if x.matricula.inscripcion.centroinformacion else '', 'centroinformacion': x.matricula.inscripcion.persona.ciudad.nombre if x.matricula.inscripcion.persona.ciudad else '', }
                        lista.append(r1)
                    return ok_json({"matriculadosmaterias": lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'resumenmatriculas':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikeymooc != request.GET['key']:
                            return bad_json(error=4)
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikey != request.GET['key']:
                            return bad_json(error=4)
                    lista = []
                    for sede in Sede.objects.filter(coordinacion__carrera__inscripcion__matricula__cerrada=False).distinct():
                        for carrera in  Carrera.objects.filter(inscripcion__matricula__cerrada=False, inscripcion__sede=sede).distinct():
                            for modalidad in Modalidad.objects.filter(inscripcion__matricula__cerrada=False, inscripcion__carrera=carrera, inscripcion__sede=sede).distinct():
                                elemento = {'idc': carrera.id, 'carrera': carrera.nombre_completo(), 'idm': modalidad.nombre, 'cantidad': carrera.cantidad_matriculados_modalidad_sede(modalidad, sede), 'sede': sede.id, 'nombresede': sede.nombre}
                            lista.append(elemento)
                    return ok_json({"resumenmatriculas": lista, "total": total_matriculas_activas()})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'facturaspendientes':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikey != request.GET['key']:
                            return bad_json(error=4)
                    return ok_json(exportacion_datos_facturacion(pendientes=True))
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'cuentasxcobrar':
                try:
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikeymooc != request.GET['key']:
                            return bad_json(error=4)
                    from ctt.models import mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikey != request.GET['key']:
                            return bad_json(error=4)
                    lista = []
                    for x in Factura.objects.filter(pagada=False, valida=True):
                        inscripcion = None
                        if not inscripcion:
                            inscripcion = x.rubronotadebito_set.all()[0].rubro.inscripcion
                        rub = []
                        for pago in x.pagos.all():
                            otro = 0
                            otrorub = None
                            if pago.rubro.es_otro():
                                otrorub = pago.rubro.rubrootro_set.all()[0]
                                otro = otrorub.tipo_id
                            otromat = 0
                            if pago.rubro.es_otromatricula():
                                rubrootromatricula = pago.rubro.rubrootromatricula_set.all()[0]
                                otromat = rubrootromatricula.tipo
                            descripcion = pago.rubro.nombre
                            datorub = {'RU': pago.rubro.id,
                                       'TIP': pago.rubro.tipo_exp(),
                                       'OTRO_ID': otro,
                                       'OTROMAT_ID': otromat,
                                       'OTRO_DES': otrorub.tipo.nombre if otrorub else '',
                                       'DES': smart_str(descripcion),
                                       'VAL': pago.valor}
                            rub.append(datorub)
                        r1 = {'ID': x.id,
                              'FACTURA': x.numero,
                              'VALIDA': x.valida,
                              'NOMBRE': smart_str(x.nombre),
                              'DIRECCION': smart_str(x.direccion),
                              'CORREO': smart_str(x.email),
                              'CLAVEACCESO': smart_str(x.claveacceso),
                              'TELEFONO': smart_str(x.telefono),
                              'IDC': smart_str(x.identificacion),
                              'TI': smart_str(x.tipo_identificacion()),
                              'ST': x.subtotal,
                              'IVA': x.iva,
                              'TT': x.total,
                              'PAGADO': x.total_pagado(),
                              'MOD': smart_str(inscripcion.modalidad.id),
                              'CAR': inscripcion.carrera.id,
                              'CORREOINST': smart_str(inscripcion.persona.emailinst),
                              'CORREOPRIV': smart_str(inscripcion.persona.email),
                              'RUB': rub,}
                        lista.append(r1)
                    return ok_json({"FACTURAS": lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'codigosfacturacion':
                try:
                    from ctt.models import TipoOtroRubro, mi_institucion
                    institucion = mi_institucion()
                    if institucion.apikey:
                        if institucion.apikey != request.GET['key']:
                            return bad_json(error=4)
                    tipos = []
                    subtipo = []
                    item = {"TIPO": "INS", "NOMBRE": "INSCRIPCION", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    for t in TipoMatricula.objects.all():
                        if t.id == 1:
                            subtipo.append({"SUBTIPO": "RG", "NOMBRE": "MATRICULA REGULAR"})
                        elif t.id == 2:
                            subtipo.append({"SUBTIPO": "ES", "NOMBRE": "MATRICULA ESPECIAL"})
                        elif t.id == 3:
                            subtipo.append({"SUBTIPO": "EX", "NOMBRE": "MATRICULA EXTRAORDINARIA"})
                    item = {"TIPO": "MAT", "NOMBRE": "MATRICULA", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    item = {"TIPO": "OTM", "NOMBRE": "OTROS MATRICULA", 'SUB': subtipo}
                    tipos.append(item)
                    for rotm in RubroOtroMatricula.objects.distinct('descripcion', 'tipo').order_by('tipo'):
                        subtipo.append({"SUBTIPO": str(rotm.tipo), "NOMBRE": rotm.descripcion})
                    subtipo = []
                    item = {"TIPO": "MAR", "NOMBRE": "MATERIA", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    item = {"TIPO": "DER", "NOMBRE": "DERECHO", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    item = {"TIPO": "SOL", "NOMBRE": "SOLICITUD", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    for e in TipoOtroRubro.objects.all():
                        subtipo.append({"SUBTIPO": str(e.id), "NOMBRE": e.nombre})
                    item = {"TIPO": "OTR", "NOMBRE": "OTROS RUBROS", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    item = {"TIPO": "ESP", "NOMBRE": "ESPECIE VALORADA", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    item = {"TIPO": "CUO", "NOMBRE": "ARANCELES", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    item = {"TIPO": "AGR", "NOMBRE": "AGREGACION", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    item = {"TIPO": "ANT", "NOMBRE": "ANTICIPADO", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    item = {"TIPO": "NDB", "NOMBRE": "NOTA DEBITO", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    item = {"TIPO": "ACT", "NOMBRE": "ACTIVIDAD EXTRA CURRICULAR", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    item = {"TIPO": "CUR", "NOMBRE": "CURSO", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    item = {"TIPO": "CURT", "NOMBRE": "CURSO TITULACION", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    item = {"TIPO": "CURI", "NOMBRE": "CURSO INGLES", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    item = {"TIPO": "CURF", "NOMBRE": "CURSO FORMACION CONTINUA", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    item = {"TIPO": "CURV", "NOMBRE": "CURSO EDUCACION VIRTUAL", 'SUB': subtipo}
                    tipos.append(item)
                    subtipo = []
                    return ok_json(data={'datos': tipos})
                except Exception as ex:
                    return bad_json(error=3)

            # if action == 'estudiantecrm':
            #     try:
            #         login_required_inside(request)
            #         identificacion = request.GET['identificacion']
            #         if not identificacion:
            #             raise Exception
            #         if not Persona.objects.filter(Q(cedula=identificacion) | Q(pasaporte=identificacion)).exists():
            #             raise Exception
            #         persona = Persona.objects.filter(Q(cedula=request.GET['identificacion']) | Q(pasaporte=request.GET['identificacion']))[0]
            #         for x in persona.inscripcion_set.all():
            #             listacarreras = []
            #             r = {'sede':x.sede.nombre,'facultad':x.coordinacion.nombre, 'carrera': x.carrera.nombre, 'modalidad': x.modalidad.nombre,'idperiodo': x.periodo.nombre}
            #             listacarreras.append(r)
            #         return ok_json({"estudiante": persona.id, 'nombre1': persona.nombre1, 'nombre2': persona.nombre2, 'apellido1': persona.apellido1, 'apellido2': persona.apellido2, 'cedula': persona.cedula, 'pasaporte': persona.pasaporte, 'emailinst': persona.emailinst, 'email': persona.email, 'movil': persona.telefono, 'saldo': persona.adeuda_a_la_fecha(), 'carreras': listacarreras})
            #     except Exception as ex:
            #         return bad_json(error=3)
            return ok_json({'CTT': 'U. Indoamérica (C) Todos los derechos reservados'})


def exportacion_datos_notacredito(fecha):
    data = {}
    nc = []
    for notacredito in NotaCredito.objects.filter(fecha=fecha):
        datosnotacredito = {'NC_ID': notacredito.id,
                            'NC_FECHA': notacredito.fecha.strftime("%d-%m-%Y"),
                            'NC_VALOR': notacredito.valorinicial}
        nc.append(datosnotacredito)
        data.update({'NC': nc})
    return data


def exportacion_datos_vales_caja(fecha=None):
    data = {}
    vales = []
    for vale in ValeCaja.objects.filter(sesion__fecha=fecha).order_by('id'):
        datosvale = {'ID': vale.id,
                     'VAL': vale.valor,
                     'TT': 'EG' if vale.tipooperacion == 1 else 'IN',
                     'CAJ': vale.sesion.caja.persona.identificacion(),
                     'EST': vale.sesion.caja.puntodeventa.establecimiento,
                     'CONCEP': smart_str(vale.concepto),
                     'IDRECIB': smart_str(vale.recibe.identificacion()),
                     'RECIB': smart_str(vale.recibe.nombre_completo()),
                     'AUTOR': smart_str(vale.responsable.nombre_completo()),
                     'IDAUTOR': smart_str(vale.responsable.identificacion()),
                     'PUN': vale.sesion.caja.puntodeventa.puntoventa}
        vales.append(datosvale)
    data.update({'VALES': vales})
    return data


def exportacion_datos_facturacion(fecha=None, pendientes=False):
    try:
        data = {}
        facturas = []
        if pendientes:
            facturasprocesar = Factura.objects.filter(estado=1).order_by('id')
        else:
            facturasprocesar = Factura.objects.filter(fecha=fecha).order_by('id')
        for factura in facturasprocesar:
            try:
                inscripcion = None
                rub = []
                for pago in factura.pagos.all():
                    try:
                        if not inscripcion and pago.rubro.inscripcion:
                            inscripcion = pago.rubro.inscripcion
                        tipomatri = "NA"
                        cuota = "NA"
                        subtipo = "NA"
                        if pago.rubro.es_matricula():
                            matricula = pago.rubro.matricula()
                            if matricula.tipomatricula.id == MATRICULA_REGULAR_ID:
                                tipomatri = "RG"
                                subtipo = "RG"
                            elif matricula.tipomatricula.id == MATRICULA_EXTRAORDINARIA_ID:
                                if pago.rubro.es_otromatricula():
                                    tipomatri = "EX"
                                    subtipo = "EX"
                                else:
                                    tipomatri = "RG"
                                    subtipo = "RG"
                            else:
                                if pago.rubro.es_otromatricula():
                                    tipomatri = "ES"
                                    subtipo = "ES"
                                else:
                                    tipomatri = "RG"
                                    subtipo = "RG"
                        elif pago.rubro.es_cuota():
                            tipocuota = pago.rubro.rubrocuota_set.all()[0]
                            cuota = str(tipocuota.cuota).zfill(2)
                        if pago.rubro.es_cuota() or pago.rubro.es_agregacion():
                            subtipo = "NA"
                        otro = 0
                        otrorub = None
                        if pago.rubro.es_otro():
                            otrorub = pago.rubro.rubrootro_set.all()[0]
                            otro = otrorub.tipo_id
                            subtipo = str(otrorub.tipo_id)
                        otromat = 0
                        if pago.rubro.es_otromatricula():
                            rubrootromatricula = pago.rubro.rubrootromatricula_set.all()[0]
                            otromat = rubrootromatricula.tipo
                            subtipo = str(rubrootromatricula.tipo)
                        descripcion = pago.rubro.nombre
                        datorub = {'RU': pago.rubro.id,
                                   'TIP': pago.rubro.tipo_exp(),
                                   'SUBTIP': subtipo,
                                   'TIPR': pago.rubro.tipo_exp_rel(),
                                   'OTRO_ID': otro,
                                   'OTROMAT_ID': otromat,
                                   'OTRO_DES': otrorub.tipo.nombre if otrorub else '',
                                   'MAT_TIP': tipomatri,
                                   'CUO_NUM': cuota,
                                   'DES': smart_str(descripcion),
                                   'VAL': pago.valor,
                                   'DE': pago.descuento,
                                   'ST': pago.rubro.valor,
                                   'IVA': pago.rubro.valoriva,
                                   'TT': pago.rubro.valortotal,
                                   'PER': pago.rubro.periodo.nombre if pago.rubro.periodo else ''}
                        rub.append(datorub)
                    except Exception as ex:
                        pass
                pag = []
                for pago in factura.pagos.all():
                    try:
                        datopag = {}
                        if pago.es_tarjeta():
                            relacionado = pago.relacionado()
                            padre = relacionado.padre()
                            datopag = {'PG': pago.id,
                                       'TIP': pago.tipo_exp(),
                                       'P_RID': padre.id,
                                       'P_TTID': padre.tipo.id,
                                       'P_TTN': padre.tipo.nombre,
                                       'P_TTEM': padre.tipoemisortarjeta.nombre if padre.tipoemisortarjeta else 'NA',
                                       'P_TTBID': padre.banco.id,
                                       'P_TTBIDN': padre.banco.nombre,
                                       'P_TTVO': padre.referencia,
                                       'P_LOTE': padre.lote,
                                       'VAL_REL': padre.valor,
                                       'DE': pago.descuento,
                                       'VAL': pago.valor,
                                       'P_PROC': padre.procesadorpago_id,
                                       'P_DIFE': padre.diferido.difiere if padre.procesadorpago_id == 1 else False,
                                       'P_INTR': padre.diferido.intereses if padre.procesadorpago_id == 1 else False,
                                       'P_NCUO': padre.diferido.valordatafast if padre.procesadorpago_id == 1 else 0,
                                       'P_DIFN': padre.diferido.nombre if padre.procesadorpago_id == 1 else 'PAGO PAYPHONE'}
                        if pago.es_cheque():
                            relacionado = pago.relacionado()
                            padre = relacionado.padre()
                            datopag = {'PG': pago.id,
                                       'TIP': pago.tipo_exp(),
                                       'P_RID': padre.id,
                                       'P_TCHBID': padre.banco.id,
                                       'P_TCHBIDN': padre.banco.nombre,
                                       'P_TCHFE': padre.fechacobro.strftime("%d-%m-%Y"),
                                       'P_TCHNO': padre.numero,
                                       'VAL_REL': padre.valor,
                                       'DE': pago.descuento,
                                       'VAL': pago.valor}
                        if pago.es_transferencia():
                            relacionado = pago.relacionado()
                            padre = relacionado.padre()
                            datopag = {'PG': pago.id,
                                       'TIP': pago.tipo_exp(),
                                       'P_RID': padre.id,
                                       'P_TTDCID': padre.cuentabanco.id,
                                       'P_TTDCIDN': padre.cuentabanco.numero,
                                       'P_TTDRE': padre.referencia,
                                       'P_TTDFE': padre.fechabanco.strftime("%d-%m-%Y"),
                                       'P_TTDDEP': False,
                                       'VAL_REL': padre.valor,
                                       'DE': pago.descuento,
                                       'VAL': pago.valor}
                        if pago.es_deposito():
                            relacionado = pago.relacionado()
                            padre = relacionado.padre()
                            datopag = {'PG': pago.id,
                                       'TIP': pago.tipo_exp(),
                                       'P_RID': padre.id,
                                       'P_TTDCID': padre.cuentabanco.id,
                                       'P_TTDCIDN': padre.cuentabanco.numero,
                                       'P_TTDRE': padre.referencia,
                                       'P_TTDFE': padre.fechabanco.strftime("%d-%m-%Y"),
                                       'P_TTDDEP': True,
                                       'VAL_REL': padre.valor,
                                       'DE': pago.descuento,
                                       'VAL': pago.valor}
                        if pago.es_notadecredito():
                            relacionado = pago.relacionado()
                            padre = relacionado.padre()
                            datopag = {'PG': pago.id,
                                       'TIP': pago.tipo_exp(),
                                       'P_RID': padre.id,
                                       'P_NCID': padre.id,
                                       'VAL_REL': padre.valorinicial,
                                       'DE': pago.descuento,
                                       'VAL': pago.valor}
                        if pago.es_recibocajainst():
                            relacionado = pago.relacionado()
                            padre = relacionado.padre()
                            datopag = {'PG': pago.id,
                                       'TIP': pago.tipo_exp(),
                                       'P_RID': padre.id,
                                       'P_NCID': padre.id,
                                       'VAL_REL': padre.valorinicial,
                                       'DE': pago.descuento,
                                       'VAL': pago.valor}
                        if pago.efectivo:
                            datopag = {'PG': pago.id,
                                       'TIP': pago.tipo_exp(),
                                       'DE': pago.descuento,
                                       'VAL': pago.valor}
                        pag.append(datopag)
                    except Exception as ex:
                        pass
                datosfactura = {'ID': factura.id,
                                'NUMERO': factura.numero,
                                'VALIDA': factura.valida,
                                'NOMBRE': smart_str(factura.nombre),
                                'PERSONA': smart_str(inscripcion.persona.nombre_completo()),
                                'PERSONAID': smart_str(inscripcion.persona.identificacion()),
                                'PERSONATIPOID': smart_str(inscripcion.persona.tipo_identificacion()),
                                'DIRECCION': smart_str(factura.direccion),
                                'CORREO': smart_str(factura.email),
                                'CLAVEACCESO': factura.claveacceso,
                                'CORREOINST': inscripcion.persona.emailinst,
                                'CORREOPRIV': inscripcion.persona.email,
                                'TELEFONO': factura.telefono,
                                'TELEFONOESTCONV': inscripcion.persona.telefono_conv,
                                'TELEFONOESTMOV': inscripcion.persona.telefono,
                                'IDSEDE': inscripcion.sede.nombre,
                                'IDC': factura.identificacion,
                                'TI': factura.tipo_identificacion(),
                                'ST': factura.subtotal,
                                'IVA': factura.iva,
                                'TT': factura.total,
                                'DE': factura.descuento,
                                'PAGADA':  factura.pagada,
                                'CREDITO':  factura.es_credito(),
                                'RUB': rub,
                                'PAG': pag,
                                'MOD': inscripcion.modalidad.id,
                                'IID': inscripcion.id,
                                'CAJ': factura.sesion.caja.persona.identificacion(),
                                'CAR': inscripcion.carrera.id,
                                'CAP': inscripcion.centroinformacion.centroapoyo.id if inscripcion.centroinformacion else 0,
                                'POSTG': inscripcion.carrera.tipogrado.id == CUARTO_NIVEL_TITULACION_ID,
                                'NIV': inscripcion.mi_nivel().nivel.id,
                                'NIVMAX': inscripcion.mi_malla().nivelesregulares,
                                }
                facturas.append(datosfactura)
            except Exception as ex:
                pass
        data.update({'FACTURAS': facturas})
        return data
    except Exception as ex:
        return bad_json(error=3)


def exportacion_datos_recibopago(fecha=None):
    try:
        data = {}
        recibos = []
        for recibopago in ReciboPago.objects.filter(fecha=fecha, pagos__isnull=False).order_by('id'):
            inscripcion = None
            rub = []
            for pago in recibopago.pagos.all():
                if not inscripcion and pago.rubro.inscripcion:
                    inscripcion = pago.rubro.inscripcion
                tipomatri = "NA"
                cuota = "NA"
                otro = 0
                otrorub = None
                if pago.rubro.es_otro():
                    otrorub = pago.rubro.rubrootro_set.all()[0]
                    otro = otrorub.tipo_id
                otromat = 0
                if pago.rubro.es_otromatricula():
                    rubrootromatricula = pago.rubro.rubrootromatricula_set.all()[0]
                    otromat = rubrootromatricula.tipo
                descripcion = pago.rubro.nombre if pago.rubro else ''
                factura = ''
                nd = pago.rubro.notadebito()
                datorub = {'RU': pago.rubro.id,
                           'TIP': pago.rubro.tipo_exp(),
                           'TIPR': pago.rubro.tipo_exp_rel(),
                           'FACT': nd.factura.numero if nd.factura else 'NA',
                           'FACTNOMBRE': nd.factura.nombre if nd.factura else 'NA',
                           'FACTDIREC': nd.factura.direccion if nd.factura else 'NA',
                           'FACTTELF': nd.factura.telefono if nd.factura else 'NA',
                           'FACTEMAIL': nd.factura.email if nd.factura else 'NA',
                           'FECHFACT': nd.factura.fecha.strftime("%d-%m-%Y") if nd.factura else 'NA',
                           'IDENTFACT': nd.factura.identificacion if nd.factura else 'NA',
                           'TIPIDENTFACT': nd.factura.tipo_identificacion() if nd.factura else 'NA',
                           'CARR_ID': pago.rubro.inscripcion.carrera.id,
                           'MODA_ID': pago.rubro.inscripcion.modalidad.id,
                           'OTRO_ID': otro,
                           'OTROMAT_ID': otromat,
                           'OTRO_DES': otrorub.tipo.nombre if otrorub else '',
                           'MAT_TIP': tipomatri,
                           'CUO_NUM': cuota,
                           'DES': smart_str(descripcion),
                           'VAL': pago.valor,
                           'DE': pago.descuento}
                rub.append(datorub)
            pag = []
            for pago in recibopago.pagos.all():
                datopag = {}
                if pago.es_tarjeta():
                    relacionado = pago.relacionado()
                    padre = relacionado.padre()
                    datopag = {'PG': pago.id,
                               'TIP': pago.tipo_exp(),
                               'P_RID': padre.id,
                               'P_TTID': padre.tipo.id,
                               'P_TTN': padre.tipo.nombre,
                               'P_TTEM': padre.tipoemisortarjeta.nombre if padre.tipoemisortarjeta else 'NA',
                               'P_TTBID': padre.banco.id,
                               'P_TTBIDN': padre.banco.nombre,
                               'P_TTVO': padre.referencia,
                               'P_LOTE': padre.lote,
                               'VAL_REL': padre.valor,
                               'ID_RUBRO': pago.rubro.id,
                               'DE': pago.descuento,
                               'VAL': pago.valor,
                               'P_PROC': padre.procesadorpago_id,
                               'P_DIFE': padre.diferido.difiere if padre.procesadorpago_id==1 else False,
                               'P_INTR': padre.diferido.intereses if padre.procesadorpago_id==1 else False,
                               'P_NCUO': padre.diferido.valordatafast if padre.procesadorpago_id==1 else 0,
                               'P_DIFN': padre.diferido.nombre if padre.procesadorpago_id==1 else 'PAGO PAYPHONE'}
                if pago.es_cheque():
                    relacionado = pago.relacionado()
                    padre = relacionado.padre()
                    datopag = {'PG': pago.id,
                               'TIP': pago.tipo_exp(),
                               'P_RID': padre.id,
                               'P_TCHBID': padre.banco.id,
                               'P_TCHBIDN': padre.banco.nombre,
                               'P_TCHFE': padre.fechacobro.strftime("%d-%m-%Y"),
                               'P_TCHNO': padre.numero,
                               'VAL_REL': padre.valor,
                               'ID_RUBRO': pago.rubro.id,
                               'DE': pago.descuento,
                               'VAL': pago.valor}
                if pago.es_transferencia():
                    relacionado = pago.relacionado()
                    padre = relacionado.padre()
                    datopag = {'PG': pago.id,
                               'TIP': pago.tipo_exp(),
                               'P_RID': padre.id,
                               'P_TTDCID': padre.cuentabanco.id,
                               'P_TTDCIDN': padre.cuentabanco.numero,
                               'P_TTDRE': padre.referencia,
                               'P_TTDFE': padre.fechabanco.strftime("%d-%m-%Y"),
                               'P_TTDDEP': False,
                               'VAL_REL': padre.valor,
                               'ID_RUBRO': pago.rubro.id,
                               'DE': pago.descuento,
                               'VAL': pago.valor}
                if pago.es_deposito():
                    relacionado = pago.relacionado()
                    padre = relacionado.padre()
                    datopag = {'PG': pago.id,
                               'TIP': pago.tipo_exp(),
                               'P_RID': padre.id,
                               'P_TTDCID': padre.cuentabanco.id,
                               'P_TTDCIDN': padre.cuentabanco.numero,
                               'P_TTDRE': padre.referencia,
                               'P_TTDFE': padre.fechabanco.strftime("%d-%m-%Y"),
                               'P_TTDDEP': True,
                               'VAL_REL': padre.valor,
                               'ID_RUBRO': pago.rubro.id,
                               'DE': pago.descuento,
                               'VAL': pago.valor}
                if pago.es_notadecredito():
                    relacionado = pago.relacionado()
                    padre = relacionado.padre()
                    datopag = {'PG': pago.id,
                               'TIP': pago.tipo_exp(),
                               'P_RID': padre.id,
                               'P_NCID': padre.id,
                               'VAL_REL': padre.valorinicial,
                               'ID_RUBRO': pago.rubro.id,
                               'DE': pago.descuento,
                               'VAL': pago.valor}
                if pago.es_recibocajainst():
                    relacionado = pago.relacionado()
                    padre = relacionado.padre()
                    datopag = {'PG': pago.id,
                               'TIP': pago.tipo_exp(),
                               'P_RID': padre.id,
                               'P_NCID': padre.id,
                               'VAL_REL': padre.valorinicial,
                               'ID_RUBRO': pago.rubro.id,
                               'DE': pago.descuento,
                               'DE': pago.descuento,
                               'VAL': pago.valor}
                if pago.efectivo:
                    datopag = {'PG': pago.id,
                               'TIP': pago.tipo_exp(),
                               'DE': pago.descuento,
                               'ID_RUBRO': pago.rubro.id,
                               'VAL': pago.valor}
                pag.append(datopag)
            datosrecibopago = {'ID': recibopago.id,
                               'NUMERO': recibopago.numero,
                               'VALIDA': recibopago.valido,
                               'NOMBRE': smart_str(inscripcion.persona.nombre_completo()),
                               'PERSONA': smart_str(inscripcion.persona.nombre_completo()),
                               'PERSONAID': smart_str(inscripcion.persona.identificacion()),
                               'PERSONATIPOID': smart_str(inscripcion.persona.tipo_identificacion()),
                               'DIRECCION': '',
                               'CORREO': '',
                               'CLAVEACCESO': '',
                               'CORREOINST': inscripcion.persona.emailinst,
                               'CORREOPRIV': inscripcion.persona.email,
                               'TELEFONO': '',
                               'TELEFONOESTCONV': inscripcion.persona.telefono_conv,
                               'TELEFONOESTMOV': inscripcion.persona.telefono,
                               'IDSEDE': inscripcion.sede.nombre,
                               'IDC': '',
                               'TI': '',
                               'ST': recibopago.subtotal,
                               'IVA': recibopago.iva,
                               'TT': recibopago.total,
                               'RUB': rub,
                               'PAG': pag,
                               'MOD': inscripcion.modalidad.id,
                               'IID': inscripcion.id,
                               'CAJ': recibopago.sesion.caja.persona.identificacion(),
                               'CAR': inscripcion.carrera.id,
                               'CAP': inscripcion.centroinformacion.centroapoyo.id if inscripcion.centroinformacion else 0,
                               'POSTG': inscripcion.carrera.tipogrado.id == CUARTO_NIVEL_TITULACION_ID,
                               'NIV': inscripcion.mi_nivel().nivel.id,
                               'NIVMAX': inscripcion.mi_malla().nivelesregulares,
                               }
            recibos.append(datosrecibopago)
        data.update({'RECIBOS': recibos})
        return data
    except Exception as ex:
        pass


def busqueda_datos(m, q='', perfilusuario=None):
    sp = m.split(':')
    if len(sp[0].split('.')) > 1:
        app = sp[0].split('.')[0]
        modelo = sp[0].split('.')[1]
        exec(u"from %s.models import %s" % (app, modelo))
        model = eval(modelo)
    else:
        exec(u"from ctt.models import %s" % sp[0])
        model = eval(sp[0])
    q = q.upper().strip()
    funcion = 'model.flexbox_query(q'
    if len(sp) > 1:
        if len(sp[1]) > 0:
            funcion += ', filtro=sp[1]'
        if len(sp[2]) > 0:
            funcion += ', exclude=sp[2]'
        if len(sp[3]) > 0:
            if perfilusuario:
                if perfilusuario.es_estudiante():
                    sp[3] = '10'
            funcion += ', cantidad=sp[3]'
    funcion += ')'
    query = eval(funcion)
    return [{"id": x.id, "name": x.flexbox_repr(), 'alias': x.flexbox_alias() if hasattr(x, 'flexbox_alias') else []} for x in query]


def exportacion_datos_persona():
    data = {}
    lista = []
    for p in Persona.objects.filter(Q(administrativo__isnull=False) | Q(profesor__isnull=False)).distinct():
        print(p)
        try:
            datosdocente = {}
            if p.es_profesor():
                profesor = p.profesor()
                datosdocente = {'coordinacion': profesor.coordinacion.nombre if profesor.coordinacion else '',
                                'dedicacion': profesor.dedicacion.nombre if profesor.dedicacion else '',
                                'activo': profesor.activo,
                                'categoria': profesor.categoria.nombre if profesor.categoria else ''}
            datosadministrativo = {}
            if p.es_administrativo():
                administrativo = p.administrativo()
                datosadministrativo = {'sede': administrativo.sede.nombre if administrativo.sede else '',
                                       'activo': administrativo.activo}
            estudios=[]
            for estudio in p.estudiopersona_set.filter(cursando=False):
                try:
                    if estudio.superior:
                        datosestudios={'superior':estudio.superior,
                                       'institucion': estudio.institucioneducacionsuperior.nombre if estudio.institucioneducacionsuperior else '',
                                       'titulo': estudio.titulo,
                                       'niveltitulacion': estudio.niveltitulacion.nombre,
                                       'detalleniveltitulacion': estudio.detalleniveltitulacion.nombre if estudio.detalleniveltitulacion else '',
                                       'registro': estudio.registro,
                                       'fecharegistro': estudio.fecharegistro.strftime("%d-%m-%Y") if estudio.fecharegistro else ''}
                    else:
                        datosestudios = {'superior': estudio.superior,
                                         'institucion': estudio.institucioneducacionbasica.nombre,
                                         'especialidad': estudio.especialidadeducacionbasica.nombre,
                                         'fechagraduado': estudio.fechagraduacion.strftime("%d-%m-%Y") if estudio.fechagraduacion else ''}
                    estudios.append(datosestudios)
                except Exception as e:
                    pass
            historialaboral = []
            for trabajo in p.trabajopersona_set.all():
                try:
                    datostrabajo = {'institucionactual': trabajo.institucionactual,
                                    'empresa': trabajo.empresa,
                                    'cargo': trabajo.cargo.nombre if trabajo.cargo else '',
                                    'ocupacion': trabajo.ocupacion,
                                    'departamento': trabajo.departamento,
                                    'telefono': trabajo.telefono,
                                    'fecha': trabajo.fecha.strftime("%d-%m-%Y") if trabajo.fecha else '',
                                    'fechafin': trabajo.fechafin.strftime("%d-%m-%Y") if trabajo.fechafin else '',
                                    'contrato': trabajo.contrato,
                                    'concursomerito': trabajo.concursomerito}
                    historialaboral.append(datostrabajo)
                except Exception as e:
                    pass
            publicaciones = []
            for publicacion in p.publicacionpersona_set.all():
                try:
                    datospublicacion = {'revista': publicacion.revista.nombre,
                                        'fecha': publicacion.fecha.strftime("%d-%m-%Y") if publicacion.fecha else '',
                                        'isbn': publicacion.isbn,
                                        'url': publicacion.url,
                                        'nombre':publicacion.nombre}
                    publicaciones.append(datospublicacion)
                except Exception as e:
                    pass
            cursos = []
            for curso in p.cursopersona_set.all():
                try:
                    datoscurso = {'tipocurso': curso.tipocurso.nombre,
                                  'nombre':curso.nombre,
                                  'institucioneducacionsuperior':curso.educacionsuperior,
                                  'institucion':curso.institucion.nombre if curso.institucion else curso.institucionformacion,
                                  'fechainicio': curso.fecha_inicio.strftime("%d-%m-%Y") if curso.fecha_inicio else '',
                                  'fechafin': curso.fecha_fin.strftime("%d-%m-%Y") if curso.fecha_fin else ''}
                except Exception as e:
                    pass
                cursos.append(datoscurso)

            datos = {'nombre1': p.nombre1,
                     'nombre2': p.nombre2,
                     'apellido1': p.apellido1,
                     'apellido2': p.apellido2,
                     'cedula': p.cedula,
                     'pasaporte': p.pasaporte,
                     'sexo': p.sexo.nombre  if p.sexo else '',
                     'nacimiento': p.nacimiento.strftime("%d-%m-%Y"),
                     'direccion': p.direccion,
                     'email':p.email,
                     'emailinst':p.emailinst,
                     'esprofesor': p.profesor_set.exists(),
                     'datosdocente': datosdocente,
                     'datosadministrativo': datosadministrativo,
                     'esadminitrativo': p.administrativo_set.exists(),
                     'provincia': p.provincia.nombre if p.provincia else '',
                     'canton': p.canton.nombre  if p.canton else '',
                     'parroquia': p.parroquia.nombre  if p.parroquia else '',
                     'estudios': estudios,
                     'historialaboral': historialaboral,
                     'publicaciones': publicaciones,
                     'cursos': cursos,
                     }
            lista.append(datos)
        except Exception as e:
            pass
    data.update({'PERSONAS': lista})
    return data


def VerificarAPI(request):
    api_key = request.POST.get('api_key')
    if not api_key:
        return True,'Se requiere una API KEY para las transacciones, recargue la página.'
    try:
        api_key_obj = APIKey.objects.get(key=api_key)
        if api_key_obj.expires_at < datetime.now():
            return True,"Su API KEY expiro, recargue la página."
    except APIKey.DoesNotExist:
        return True,"API KEY corrupta, recargue la página."

    return False, None  # No error