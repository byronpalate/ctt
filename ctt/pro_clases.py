# coding=utf-8
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from decorators import inhouse_check, secure_module, last_access
from settings import ARCHIVO_TIPO_DEBERES, NOTIFICACION_DEBERES, CLASES_HORARIO_ESTRICTO, VER_FOTO_LECCION, \
    CLASES_APERTURA_DESPUES, ASISTENCIA_EN_GRUPO, TIPO_DOCENTE_TEORIA, VER_DEUDA_LECCION, \
    CLASES_CONTINUAS_AUTOMATICAS, CALCULO_ASISTENCIA_CLASE
from ctt.commonviews import adduserdata, actualizar_contenido, actualizar_asistencia
from ctt.forms import ArchivoDeberForm, ContenidoAcademicoForm
from ctt.funciones import generar_nombre, convertir_fecha, log, url_back, ok_json, bad_json, empty_json
from ctt.models import Clase, Leccion, AsistenciaLeccion, ActualizacionAsistencia, EvaluacionLeccion, Turno, Aula, LeccionGrupo, Materia, \
    TipoIncidencia, Incidencia, Archivo, \
    SolicitudAperturaClase, PlanificacionMateria, ClasesTallerPlanificacionMateria, SubTipoincidencia
from ctt.tasks import send_mail


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    profesor = perfilprincipal.profesor

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'nuevaleccion':
                try:
                    solicitada = False
                    fecha = datetime.now().date()
                    if LeccionGrupo.objects.filter(profesor=profesor, abierta=True).exists():
                        return bad_json(mensaje=u"Existe una clase abierta.")
                    if 'solicitud' in request.POST:
                        solicitud = SolicitudAperturaClase.objects.get(pk=request.POST['solicitud'])
                        solicitada = True
                        solicitud.aperturada = True
                        solicitud.save(request)
                        clases = Clase.objects.filter(turno=solicitud.turno, dia=solicitud.fecha.isoweekday(),
                                                      activo=True, inicio__lte=solicitud.fecha,
                                                      fin__gte=solicitud.fecha,
                                                      materia__profesormateria__principal=True,
                                                      materia__profesormateria__profesor=solicitud.profesor).distinct()
                        if not clases:
                            transaction.set_rollback(True)
                            return bad_json(mensaje=u"No existe horario para esta solicitud.")
                        fecha = solicitud.fecha
                    else:
                        if 'fecha' in request.POST:
                            fecha = convertir_fecha(request.POST['fecha'])
                        clases = Clase.objects.filter(id__in=[int(x) for x in request.POST['clases'].split(',')])
                        cla = clases[0]
                        if not cla.materia.carrera.posgrado:
                            if cla.materia.nivel.modalidad.id in [1, 2]:
                                if cla.materia.asignatura_id not in [4311, 4312, 4313, 4316, 4317, 4318, 4319, 4320]:
                                    if not inhouse_check(request):
                                        transaction.set_rollback(True)
                                        return bad_json(mensaje=u"No puede abrir clases fuera de la institución.")
                    for clase in clases:
                        if fecha < clase.inicio or fecha > datetime.now().date():
                            transaction.set_rollback(True)
                            return bad_json(mensaje=u"No puede abrir una clase con fecha mayor a la actual o menor que la del horario.")
                        if clase.materia:
                            if not clase.materia.tiene_planificacion_aprobada():
                                transaction.set_rollback(True)
                                return bad_json(mensaje=u"No tiene Planificacion aprobada")
                    turno = Turno.objects.get(pk=clases[0].turno.id)
                    aula = Aula.objects.get(pk=clases[0].aula.id)
                    dia = clases[0].dia
                    ids = []
                    if LeccionGrupo.objects.filter(profesor=profesor, turno=turno, fecha=fecha).exists():
                        transaction.set_rollback(True)
                        return bad_json(mensaje=u"Existe una clase registrada en esa fecha en el turno seleccionado.")
                    lecciongrupo = LeccionGrupo(profesor=profesor,
                                                turno=turno,
                                                aula=aula,
                                                dia=dia,
                                                fecha=fecha,
                                                horaentrada=datetime.now().time(),
                                                abierta=True,
                                                solicitada=solicitada,
                                                contenido='SIN CONTENIDO',
                                                estrategiasmetodologicas='SIN CONTENIDO',
                                                observaciones='SIN OBSERVACIONES')
                    lecciongrupo.save(request)
                    if ClasesTallerPlanificacionMateria.objects.filter(tallerplanificacionmateria__planificacionmateria__materia__in=[x.materia for x in clases], fecha=lecciongrupo.fecha).exists():
                        clase = ClasesTallerPlanificacionMateria.objects.filter(tallerplanificacionmateria__planificacionmateria__materia__in=[x.materia for x in clases], fecha=lecciongrupo.fecha)[0]
                        lecciongrupo.clasestallerplanificacionmateria = clase
                        lecciongrupo.save(request)
                    for clase in clases:
                        leccion = Leccion(clase=clase,
                                          fecha=lecciongrupo.fecha,
                                          horaentrada=lecciongrupo.horaentrada,
                                          abierta=True,
                                          contenido=lecciongrupo.contenido,
                                          estrategiasmetodologicas=lecciongrupo.estrategiasmetodologicas,
                                          observaciones=lecciongrupo.observaciones)
                        leccion.save(request)
                        lecciongrupo.lecciones.add(leccion)
                        if clase.materia:
                            if not CALCULO_ASISTENCIA_CLASE:
                                if not ActualizacionAsistencia.objects.filter(materia=clase.materia).exists():
                                    actualizar = ActualizacionAsistencia(materia=clase.materia)
                                    actualizar.save(request)
                            for asignada in clase.materia.materiaasignada_set.all():
                                asistencialeccion = AsistenciaLeccion(leccion=leccion, materiaasignada=asignada, asistio=False)
                                asistencialeccion.save(request)
                                if CALCULO_ASISTENCIA_CLASE:
                                    asignada.save(actualiza=True)
                                    asignada.actualiza_estado()
                            ids.append(leccion.id)
                        if clase.materiacurso:
                            if not CALCULO_ASISTENCIA_CLASE:
                                if not ActualizacionAsistencia.objects.filter(materiacurso=clase.materiacurso).exists():
                                    actualizar = ActualizacionAsistencia(materiacurso=clase.materiacurso)
                                    actualizar.save(request)
                            for asignada in clase.materiacurso.materiaasignadacurso_set.all():
                                asistencialeccion = AsistenciaLeccion(leccion=leccion, materiaasignadacurso=asignada, asistio=False)
                                asistencialeccion.save()
                                if CALCULO_ASISTENCIA_CLASE:
                                    asignada.save(actualiza=True)
                                    asignada.actualiza_estado()
                            ids.append(leccion.id)
                    lecciongrupo.save(request)
                    return ok_json({"lg": lecciongrupo.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'asistencia':
                try:
                    result = actualizar_asistencia(request)
                    result['materiaasignada'] = request.POST['id']
                    return empty_json(result)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'checheaasistencia':
                try:
                    lg = LeccionGrupo.objects.get(pk=request.POST['id'])
                    lista = []
                    if lg.actualizarasistencias:
                        for asistencia in AsistenciaLeccion.objects.filter(leccion__lecciongrupo=lg):
                            porciento = 0
                            porcientorequerido = False
                            if asistencia.materiaasignada:
                                porciento = asistencia.materiaasignada.asistenciafinal
                                porcientorequerido = asistencia.materiaasignada.porciento_requerido()
                            elif asistencia.materiaasignadacurso:
                                porciento = asistencia.materiaasignadacurso.asistenciafinal
                                porcientorequerido = asistencia.materiaasignadacurso.porciento_requerido()
                            elif asistencia.materiaasignadatitulacion:
                                porciento = asistencia.materiaasignadatitulacion.asistenciafinal
                                porcientorequerido = asistencia.materiaasignadatitulacion.porciento_requerido()
                            lista.append([asistencia.id, porciento, porcientorequerido, asistencia.asistio])
                        lg.actualizarasistencias = False
                        lg.save()
                    return ok_json({'actualizar': lg.actualizarasistencias, 'lista': lista})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'asistenciagrupo':
                try:
                    lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                    asistieron = [int(x) for x in request.POST['lista'].split(',')]
                    for asistencia in AsistenciaLeccion.objects.filter(leccion__lecciongrupo=lecciongrupo):
                        if asistencia.puede_tomar_asistencia():
                            if asistencia.asistio != (asistencia.id in asistieron):
                                asistencia.asistio = (asistencia.id in asistieron)
                                asistencia.save(request)
                                asistencia.materiaasignada.save(request)
                        else:
                            asistencia.asistio = False
                            asistencia.save(request)
                            asistencia.materiaasignada.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'asistenciageneral':
                try:
                    lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                    for leccion in lecciongrupo.lecciones.all():
                        for asistencia in leccion.asistencialeccion_set.all():
                            if asistencia.puede_tomar_asistencia():
                                asistencia.asistio = True
                            else:
                                asistencia.asistio = False
                            asistencia.save(request)
                            asistencia.materiaasignada.save(actualiza=True)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addincidencia':
                try:
                    lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['lecciongrupo'])
                    tipo = TipoIncidencia.objects.get(pk=request.POST['tipo'])
                    subtipo = SubTipoincidencia.objects.get(pk=request.POST['subtipo'])
                    if request.POST['asis'] == '':
                        asistencia = None
                    else:
                        asistencia = AsistenciaLeccion.objects.get(pk=request.POST['asis'])
                    incidencia = Incidencia(lecciongrupo=lecciongrupo,
                                            tipo=tipo,
                                            subtipo=subtipo,
                                            contenido=request.POST['contenido'],
                                            cerrada=False,
                                            sede=lecciongrupo.profesor.coordinacion.sede,
                                            asistencialeccion=asistencia)
                    incidencia.save(request)
                    incidencia.mail_nuevo(periodo)
                    log(u'Adiciono incidencia en clase: %s' % incidencia, request, "add")
                    return ok_json({"tipo": tipo.nombre, "contenido": incidencia.contenido})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'evaluar':
                try:
                    valor = float(request.POST['val'])
                    asistencialeccion = AsistenciaLeccion.objects.get(pk=request.POST['id'])
                    evaluacionleccion = EvaluacionLeccion(leccion=asistencialeccion.leccion,
                                                          materiaasignada=asistencialeccion.materiaasignada,
                                                          evaluacion=valor)
                    evaluacionleccion.save(request)
                    return ok_json({"evalid": evaluacionleccion.id, "promedio": int(asistencialeccion.promedio_evaluacion())})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == "borrarevaluacion":
                try:
                    asistencialeccion = AsistenciaLeccion.objects.get(pk=request.POST['asisid'])
                    evaluacion = EvaluacionLeccion.objects.get(pk=request.POST['evalid'])
                    evaluacion.delete()
                    return ok_json({"promedio": int(asistencialeccion.promedio_evaluacion())})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'contenido':
                try:
                    result = actualizar_contenido(request)
                    return empty_json(result)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'verificarcontinuaabierta':
                try:
                    lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                    otraslecciones = LeccionGrupo.objects.filter(profesor=lecciongrupo.profesor, abierta=True).exclude(id=lecciongrupo.id)
                    otrasleccionesid = 0
                    if otraslecciones:
                        otrasleccionesid = otraslecciones[0].id
                    return ok_json({"abierta": lecciongrupo.abierta, "otras": otrasleccionesid})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'observaciones':
                try:
                    lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                    lecciongrupo.observaciones = request.POST['val']
                    lecciongrupo.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'estrategiasmetodologicas':
                try:
                    lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                    lecciongrupo.estrategiasmetodologicas = request.POST['val']
                    lecciongrupo.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'cerrar':
                try:
                    lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                    if not lecciongrupo.contenido:
                        return bad_json(mensaje=u'No existe contenido académico.')
                    if lecciongrupo.abierta:
                        lecciongrupo.abierta = False
                        lecciongrupo.horasalida = datetime.now().time()
                        lecciongrupo.save(request)
                        for leccion in lecciongrupo.lecciones.all():
                            leccion.abierta = False
                            leccion.horasalida = datetime.now().time()
                            leccion.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'proximaclase':
                try:
                    lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                    nuevalecciongrupo = None
                    if not lecciongrupo.contenido:
                        return bad_json(mensaje=u'No existe contenido académico.')
                    if lecciongrupo.abierta:
                        lecciongrupo.abierta = False
                        lecciongrupo.horasalida = datetime.now().time()
                        lecciongrupo.save(request)
                        for leccion in lecciongrupo.lecciones.all():
                            leccion.abierta = False
                            leccion.horasalida = datetime.now().time()
                            leccion.save(request)
                        if not LeccionGrupo.objects.filter(profesor=lecciongrupo.profesor, fecha=lecciongrupo.fecha, abierta=True).exists():
                            print("TIENE CONTINUIDAD\r")
                            hoy = lecciongrupo.fecha
                            minutos_maximos = (datetime(lecciongrupo.fecha.year, lecciongrupo.fecha.month, lecciongrupo.fecha.day, lecciongrupo.turno.termina.hour, lecciongrupo.turno.termina.minute, 0) + timedelta(minutes=CLASES_APERTURA_DESPUES)).time()
                            if lecciongrupo.lecciones.filter(clase__materia__isnull=False).exists():
                                materias = [x.clase.materia.id for x in lecciongrupo.lecciones.all()]
                                claseshorario = Clase.objects.filter(activo=True, dia=lecciongrupo.dia, materia__id__in=materias, materia__profesormateria__profesor=lecciongrupo.profesor, materia__profesormateria__tipoprofesor__id=TIPO_DOCENTE_TEORIA, materia__profesormateria__principal=True, inicio__lte=hoy, fin__gte=hoy, turno__comienza__gte=lecciongrupo.turno.termina, turno__comienza__lte=minutos_maximos).distinct()
                                if claseshorario:
                                    turno = claseshorario[0].turno
                                    aula = claseshorario[0].aula
                                    claseshorario = claseshorario.filter(turno=turno, aula=aula)
                                    if LeccionGrupo.objects.filter(profesor=lecciongrupo.profesor,turno=turno,fecha=lecciongrupo.fecha).exists():
                                        transaction.set_rollback(True)
                                        return bad_json(mensaje=u'Ya existe una clase registrada para el próximo turno.')
                                    nuevalecciongrupo = LeccionGrupo(profesor=lecciongrupo.profesor,
                                                                     turno=turno,
                                                                     aula=aula,
                                                                     dia=lecciongrupo.dia,
                                                                     clasestallerplanificacionmateria=lecciongrupo.clasestallerplanificacionmateria,
                                                                     fecha=lecciongrupo.fecha,
                                                                     horaentrada=turno.comienza,
                                                                     abierta=True,
                                                                     automatica=True,
                                                                     contenido=lecciongrupo.contenido,
                                                                     estrategiasmetodologicas=lecciongrupo.estrategiasmetodologicas,
                                                                     observaciones='SIN OBSERVACIONES')
                                    nuevalecciongrupo.save()
                                    for clase in claseshorario:
                                        leccion = Leccion(clase=clase,
                                                          fecha=nuevalecciongrupo.fecha,
                                                          horaentrada=turno.comienza,
                                                          abierta=True,
                                                          contenido='',
                                                          observaciones='')
                                        leccion.save()
                                        nuevalecciongrupo.lecciones.add(leccion)
                                        for asistencias in AsistenciaLeccion.objects.filter(leccion=lecciongrupo.lecciones.filter(clase__materia=clase.materia)[0]):
                                            asistencialeccion = AsistenciaLeccion(leccion=leccion,
                                                                                  materiaasignada=asistencias.materiaasignada,
                                                                                  asistio=asistencias.asistio)
                                            asistencialeccion.save()
                                            materiaasignada = asistencialeccion.materiaasignada
                                            materiaasignada.save(actualiza=True)
                                            materiaasignada.actualiza_estado()
                                    nuevalecciongrupo.save()
                    return ok_json({'id': nuevalecciongrupo.id if nuevalecciongrupo else 0})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'adddeberes':
                try:
                    form = ArchivoDeberForm(request.POST, request.FILES)
                    if form.is_valid():
                        lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['lecciongrupo'])
                        lecciones = lecciongrupo.mis_leciones()
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("deber_", newfile._name)
                        for leccion in lecciones:
                            archivo = Archivo(observaciones=form.cleaned_data['observaciones'],
                                              materia=leccion.clase.materia,
                                              lecciongrupo=lecciongrupo,
                                              fecha=datetime.now(),
                                              archivo=newfile,
                                              tipo_id=ARCHIVO_TIPO_DEBERES)
                            archivo.save(request)
                            if NOTIFICACION_DEBERES:
                                for asignadomateria in leccion.clase.materia.materiaasignada_set.all():
                                    send_mail(subject='Nuevo deber en clase.',
                                              html_template='emails/deber.html',
                                              attachtment=[archivo],
                                              data={'nombrearchivo': archivo.nombre, 'f': lecciongrupo.fecha, 'd': leccion.clase.materia.profesor_actual()},
                                              recipient_list=[asignadomateria.matricula.inscripcion.persona])
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'contenidoacademico':
                try:
                    form = ContenidoAcademicoForm(request.POST)
                    if form.is_valid():
                        lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                        lecciones = lecciongrupo.lecciones.all()
                        tiene_programacion = PlanificacionMateria.objects.filter(materia__in=[x.clase.materia for x in lecciones]).exists()
                        if not tiene_programacion:
                            lecciongrupo.contenido = form.cleaned_data['contenido']
                            lecciongrupo.estrategiasmetodologicas = form.cleaned_data['estrategiasmetodologicas']
                            lecciongrupo.observaciones = form.cleaned_data['observaciones']
                        else:
                            lecciongrupo.clasestallerplanificacionmateria = form.cleaned_data['clasestallerplanificacionmateria']
                        lecciongrupo.save(request)
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'updatefecha':
                try:
                    lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                    fecha = convertir_fecha(request.POST['fecha'])
                    for leccion in lecciongrupo.lecciones.all():
                        if fecha > leccion.clase.fin or fecha < leccion.clase.inicio:
                            return bad_json(mensaje=u"Fecha incorrecta.")
                    lecciongrupo.fecha = fecha
                    lecciongrupo.save(request)
                    for leccion in lecciongrupo.lecciones.all():
                        leccion.fecha = fecha
                        leccion.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delleccion':
                try:
                    lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                    for leccion in lecciongrupo.mis_leciones():
                        if leccion.clase.materia:
                            materia = leccion.clase.materia
                            leccion.delete()
                            for materiaasignada in materia.materiaasignada_set.all():
                                materiaasignada.save(actualiza=True)
                                materiaasignada.actualiza_estado()
                        else:
                            materia = leccion.clase.materiacurso
                            leccion.delete()
                            for materiaasignada in materia.materiaasignadacurso_set.all():
                                materiaasignada.save(actualiza=True)
                                materiaasignada.actualiza_estado()
                    if SolicitudAperturaClase.objects.filter(profesor=lecciongrupo.profesor, fecha=lecciongrupo.fecha,  turno=lecciongrupo.turno).exists():
                        solicitud = SolicitudAperturaClase.objects.filter(profesor=lecciongrupo.profesor, fecha=lecciongrupo.fecha,  turno=lecciongrupo.turno)[0]
                        solicitud.aperturada = False
                        solicitud.estado = 1
                        solicitud.save(request)
                    log(u'Elimino clase: %s' % lecciongrupo, request, "del")
                    lecciongrupo.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'actualizaclase':
                try:
                    lecciongrupo = LeccionGrupo.objects.get(pk=int(request.POST['id']))
                    clase = None
                    if int(request.POST['valor']) > 0:
                        clase = ClasesTallerPlanificacionMateria.objects.get(pk=int(request.POST['valor']))
                    lecciongrupo.clasestallerplanificacionmateria = clase
                    lecciongrupo.save(request)
                    log(u'Modifico clase: %s' % lecciongrupo, request, "edit")
                    return ok_json(data={'docencia': clase.actividadesaprendizajecondocenciaasistida.nombre if clase.actividadesaprendizajecondocenciaasistida else '', 'autonoma': clase.actividadestrabajoautonomas, 'colaborativa': clase.actividadesaprendizajecolaborativas.nombre if clase.actividadesaprendizajecolaborativas else '', 'practica': clase.actividadesaprendizajepractico})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'incidencia':
                try:
                    data = {}
                    data['lecciongrupo'] = lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                    data['incidencias'] = lecciongrupo.incidencia_set.all()
                    template = get_template("pro_clases/resolucionesincidencias.html")
                    html = template.render(data)  # Directamente pasamos el diccionario `data`
                    return ok_json(data={'html': html})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'subtipoincidencia':
                try:
                    linea = TipoIncidencia.objects.get(pk=request.POST['id'])
                    lista = []
                    for sublinea in linea.subtipoincidencia_set.filter(activo=True):
                        lista.append([sublinea.id, sublinea.nombre])
                    return ok_json({'lista': lista})
                except:
                    return bad_json(error=3)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'view':
                try:
                    data['title'] = u'Lección'
                    if LeccionGrupo.objects.filter(profesor=profesor, abierta=True).exists():
                        data['lecciongrupo'] = lecciongrupo = LeccionGrupo.objects.filter(profesor=profesor, abierta=True)[0]
                    else:
                        data['lecciongrupo'] = lecciongrupo = LeccionGrupo.objects.get(pk=request.GET['id'])
                    data['lecciones'] = lecciones = lecciongrupo.lecciones.all()
                    data['clasesprogramadas'] =ClasesTallerPlanificacionMateria.objects.filter(tallerplanificacionmateria__planificacionmateria__materia__in=[x.clase.materia for x in lecciones], fecha=lecciongrupo.fecha)
                    data['tiene_programacion'] = PlanificacionMateria.objects.filter(materia__in=[x.clase.materia for x in lecciones], aprobado=True).exists()
                    clases = Clase.objects.filter(leccion__in=lecciones)
                    clasesi = Clase.objects.filter(leccion__in=lecciones)[0]
                    data['tiposincidencias'] = TipoIncidencia.objects.filter(sede=lecciongrupo.aula.sede)
                    data['incidencias'] = lecciongrupo.incidencia_set.all()
                    data['deber'] = None
                    if lecciongrupo.archivo_set.exists():
                        data['deber'] = lecciongrupo.archivo_set.all()[0]
                    data['clases_horario_estricto'] = CLASES_HORARIO_ESTRICTO
                    data['clases_continuas_automaticas'] = CLASES_CONTINUAS_AUTOMATICAS
                    data['ver_foto_leccion'] = VER_FOTO_LECCION
                    data['ver_deuda_leccion'] = VER_DEUDA_LECCION
                    data['calculo_asistencia_clase'] = CALCULO_ASISTENCIA_CLASE
                    data['usa_planificacion']  =  PlanificacionMateria.objects.filter(materia__clase__in=clases, aprobado=True).exists()
                    data['asistencia_en_grupo'] = ASISTENCIA_EN_GRUPO
                    data['turno'] = lecciones.all()[0].clase.turno
                    data['presentes'] = AsistenciaLeccion.objects.filter(leccion__lecciongrupo=lecciongrupo, asistio=True).distinct().count()
                    data['ausentes'] = AsistenciaLeccion.objects.filter(leccion__lecciongrupo=lecciongrupo, asistio=False).distinct().count()
                    data['totalasistencias'] = AsistenciaLeccion.objects.filter(leccion__lecciongrupo=lecciongrupo).distinct().count()
                    data['es_ingles'] = True if clasesi.materia.asignatura.id in [4311, 4312, 4313, 4316, 4317, 4318, 4319, 4320] else False
                    return render(request, "pro_clases/leccion.html", data)
                except Exception as ex:
                    pass

            if action == 'adddeberes':
                try:
                    data['title'] = u'Adicionar deberes'
                    data['lecciongrupo'] = LeccionGrupo.objects.get(pk=request.GET['id'])
                    data['form'] = ArchivoDeberForm(initial={'nombre': 'Deber leccion'})
                    return render(request, "pro_clases/adddeberes.html", data)
                except Exception as ex:
                    pass

            if action == 'contenidoacademico':
                try:
                    data['title'] = u'Contenido academico'
                    data['lecciongrupo'] = lecciongrupo = LeccionGrupo.objects.get(pk=request.GET['id'])
                    lecciones = lecciongrupo.lecciones.all()
                    data['tiene_programacion'] = PlanificacionMateria.objects.filter(materia__in=[x.clase.materia for x in lecciones]).exists()
                    form = ContenidoAcademicoForm(initial={'contenido': lecciongrupo.contenido,
                                                           'estrategiasmetodologicas': lecciongrupo.estrategiasmetodologicas,
                                                           'clasestallerplanificacionmateria': lecciongrupo.clasestallerplanificacionmateria,
                                                           'observaciones': lecciongrupo.observaciones})
                    form.adicionar(lecciongrupo)
                    data['form'] = form
                    return render(request, "pro_clases/contenidoacademico.html", data)
                except Exception as ex:
                    pass

            if action == 'deldeber':
                try:
                    lecciongrupo = LeccionGrupo.objects.get(pk=request.GET['id'])
                    archivo = Archivo.objects.filter(lecciongrupo=lecciongrupo)
                    log(u'Elimino deber de clase: %s' % lecciongrupo, request, "del")
                    archivo.delete()
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass
                return HttpResponseRedirect("/pro_clases?action=view&id=" + request.GET['id'])

            if action == 'delleccion':
                try:
                    data['title'] = u'Eliminar lección'
                    data['lecciongrupo'] = LeccionGrupo.objects.get(pk=request.GET['id'])
                    return render(request, "pro_clases/delleccion.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Listado de clases impartidas'
                hoy = datetime.now().date()
                materias = Materia.objects.filter(nivel__periodo=periodo,
                                                  nivel__distributivoaprobado=True,
                                                  profesormateria__profesor=profesor,
                                                  profesormateria__tipoprofesor__id=TIPO_DOCENTE_TEORIA,
                                                  profesormateria__principal=True).distinct()
                materia = None
                if 'id' in request.GET:
                    materia = Materia.objects.get(pk=request.GET['id'])
                    leccionesgrupo = LeccionGrupo.objects.filter(lecciones__clase__materia=materia, profesor=profesor).distinct().order_by('-fecha', '-turno__comienza')
                else:
                    leccionesgrupo = LeccionGrupo.objects.filter(lecciones__clase__materia__in=materias, profesor=profesor).distinct().order_by('-fecha', '-turno__comienza')
                paging = Paginator(leccionesgrupo, 30)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'pro_clases':
                            paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    else:
                        p = paginasesion
                    page = paging.page(p)
                except:
                    p = 1
                    page = paging.page(p)
                request.session['paginador'] = p
                request.session['paginador_url'] = 'pro_clases'
                data['paging'] = paging
                data['page'] = page
                data['leccionesgrupo'] = page.object_list
                data['ids'] = materia.id if materia else None
                data['materias'] = materias
                data['clases_horario_estricto'] = CLASES_HORARIO_ESTRICTO
                data['tiene_clases_abiertas'] = profesor.tiene_clases_abiertas()
                return render(request, "pro_clases/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
