# coding=utf-8
from datetime import datetime

import xlrd
import openpyxl
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from decorators import secure_module, last_access
from settings import UTILIZA_VALIDACION_CALIFICACIONES, \
    PERMITE_ABRIR_MATERIAS_ENFECHA, ARCHIVO_TIPO_NOTAS, MUESTRA_ESTADO_NIVELACION, NOTA_ESTADO_EN_CURSO, \
    CALCULO_ASISTENCIA_CLASE
from ctt.commonviews import adduserdata, actualizar_nota, obtener_reporte
from ctt.forms import ImportarArchivoXLSForm, SolicitudIngresoNotasForm
from ctt.funciones import log, generar_nombre, url_back, bad_json, ok_json, generar_clave, MiPaginador
from ctt.models import Materia, MateriaAsignada, Archivo, LeccionGrupo, DetalleModeloEvaluativo, \
    SolicitudIngresoNotasAtraso, EvaluacionGenerica, null_to_numeric, ProfesorMateria, \
    SolicitudIngresoNotasEstudiante, ModeloEvaluativo, ActualizacionAsistencia
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
    perfilprincipal = request.session['perfilprincipal']
    data['profesor'] = profesor = perfilprincipal.profesor
    periodo = request.session['periodo']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'cerrarmateriaasignada':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['maid'])
                    materiaasignada.cerrado = (request.POST['cerrado'] == 'false')
                    materiaasignada.fechacierre = datetime.now().date()
                    materiaasignada.save(request)
                    materiaasignada.actualiza_estado()
                    materiasabiertas = MateriaAsignada.objects.filter(materia=materiaasignada.materia, cerrado=False).count()
                    return ok_json({'cerrado': materiaasignada.cerrado, 'materiasabiertas': materiasabiertas, "estadoid": materiaasignada.estado.id, "estado": materiaasignada.estado.nombre})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'cerrarmateria':
                try:
                    materia = Materia.objects.get(pk=request.POST['mid'])
                    materia.cerrado = True
                    materia.fechacierre = datetime.now().date()
                    materia.save(request)
                    for asig in materia.asignados_a_esta_materia():
                        asig.cerrado = True
                        asig.save()
                        if asig.tiene_solicitud_ingreso_aprobada():
                            fecha = datetime.now().date()
                            solicitud = asig.solicitudingresonotasestudiante_set.filter(fechaaprobacion__lte=fecha, fechalimite__gte=fecha, estado=2)[0]
                            solicitud.estado = 4
                            solicitud.save()
                    materia.recalcularmateria()
                    for asig in materia.asignados_a_esta_materia():
                        asig.cierre_materia_asignada()
                    for lg in LeccionGrupo.objects.filter(lecciones__clase__materia=materia, abierta=True):
                        lg.abierta = False
                        lg.horasalida = lg.turno.termina
                        lg.save(request)
                    log(u'Cerro la materia: %s' % materia, request, "add")
                    send_mail(subject='Cierre de materia.',
                              html_template='emails/cierremateria.html',
                              data={'profesor': profesor, 'materia': materia},
                              recipient_list=[profesor.persona])
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'abrirmateria':
                try:
                    materia = Materia.objects.get(pk=request.POST['mid'])
                    materia.cerrado = False
                    materia.save(request)
                    send_mail(subject='Apertura de materia.',
                              html_template='emails/aperturamateria.html',
                              data={'materia': materia},
                              recipient_list=[profesor.persona])
                    log(u'Abrio la materia: %s' % materia, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'nota':
                try:
                    result = actualizar_nota(request)
                    return ok_json(result)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'asis_academica':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['maid'])
                    materiaasignada.asistenciafinal_academica_ir =  float(request.POST['val'])
                    materiaasignada.save()
                    materiaasignada.actualiza_estado()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'asis_asistencial':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['maid'])
                    materiaasignada.asistenciafinal_asistencial_ir = float(request.POST['val'])
                    materiaasignada.save()
                    materiaasignada.actualiza_estado()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'envioclave':
                try:
                    clave = generar_clave(4)
                    datos = profesor.datos_habilitacion()
                    datos.habilitado = False
                    datos.clavegenerada = clave
                    datos.fecha = datetime.now().date()
                    datos.save(request)
                    send_mail(subject='Nueva clave para ingreso de calificaciones.',
                              html_template='emails/nuevaclavecalificaciones.html',
                              data={'clave': datos.clavegenerada},
                              recipient_list=[profesor.persona])
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'verificacionclave':
                try:
                    clave = request.POST['clave']
                    datos = profesor.datos_habilitacion()
                    if datos.clavegenerada == clave and datos.fecha == datetime.now().date():
                        datos.habilitado = True
                        datos.save(request)
                        return ok_json()
                    else:
                        return bad_json(mensaje=u'Clave incorrecta')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'actualizarestado':
                try:
                    materia = Materia.objects.get(pk=request.POST['mid'])
                    for materiaasignada in materia.asignados_a_esta_materia():
                        materiaasignada.actualiza_estado()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'importar':
                try:
                    form = ImportarArchivoXLSForm(request.POST, request.FILES)
                    materia = Materia.objects.get(pk=request.POST['id'])
                    if form.is_valid():
                        nfile = request.FILES['archivo']
                        nfile._name = generar_nombre("importacionnotas_", nfile._name)
                        archivo = Archivo(nombre='IMPORTACION_NOTAS',
                                          fecha=datetime.now(),
                                          archivo=nfile,
                                          tipo_id=ARCHIVO_TIPO_NOTAS)
                        archivo.save(request)
                        workbook = openpyxl.load_workbook(archivo.archivo.file.name)
                        sheet = workbook.worksheets[0]
                        linea = 1
                        hoy = datetime.now().date()
                        for rowx in sheet.iter_rows(values_only=True):
                            if linea >= 4:
                                cols = rowx
                                if materia.materiaasignada_set.filter(id=int(cols[0])).exists():
                                    materiaasignada = materia.materiaasignada_set.filter(id=cols[0])[0]
                                    numero_campo = 3
                                    for campo in EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada, detallemodeloevaluativo__dependiente=False).distinct().order_by('detallemodeloevaluativo__orden'):
                                        try:
                                            valor = float(cols[numero_campo])
                                        except:
                                            valor = 0
                                        if valor != campo.valor:
                                            cronograma = materiaasignada.materia.cronogramacalificaciones()
                                            if cronograma:
                                                permite = campo.detallemodeloevaluativo.permite_ingreso_nota(materiaasignada, cronograma)
                                                if permite:
                                                    result = actualizar_nota(request, materiaasignada=materiaasignada, sel=campo.detallemodeloevaluativo.nombre, valor=valor, rapido=True)
                                        numero_campo += 1
                            linea += 1
                            print(linea)
                        modeloevaluativo = materia.modeloevaluativo
                        local_scope = {}
                        exec(modeloevaluativo.logicamodelo, globals(), local_scope)
                        calculo_modelo_evaluativo = local_scope['calculo_modelo_evaluativo']
                        for materiaasignada in materia.materiaasignada_set.all():
                            calculo_modelo_evaluativo(materiaasignada)
                            materiaasignada.actualiza_estado()
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'observaciones':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materiaasignada.observaciones = request.POST['observacion']
                    materiaasignada.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'segmento':
                try:
                    search = None
                    ids = None
                    if 'id' in request.POST:
                        request.session['pro_evaluaciones_materia'] = data['materiaid'] = int(request.POST['id'])
                    data['materia'] = materia = Materia.objects.filter(profesormateria__profesor=profesor).get(pk=request.session['pro_evaluaciones_materia'])
                    if not CALCULO_ASISTENCIA_CLASE:
                        if ActualizacionAsistencia.objects.filter(materia=materia).exists():
                            for ma in materia.materiaasignada_set.filter(cerrado=False):
                                ma.save(actualiza=True)
                                ma.actualiza_estado()
                            registro = ActualizacionAsistencia.objects.filter(materia=materia)[0]
                            registro.delete()
                    paging = MiPaginador(materia.asignados_a_esta_materia(), 6)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session and 'paginador_url' in request.session:
                            if request.session['paginador_url'] == 'pro_evaluaciones':
                                paginasesion = int(request.session['paginador'])
                        if 'page' in request.POST:
                            p = int(request.POST['page'])
                        else:
                            p = paginasesion
                        page = paging.page(p)
                    except:
                        p = 1
                        page = paging.page(p)
                    request.session['paginador'] = p
                    request.session['paginador_url'] = 'pro_evaluaciones'
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['listaestudiantes'] = page.object_list
                    data['cronograma'] = materia.cronogramacalificaciones()
                    data['permite_abrir_materias_enfecha'] = PERMITE_ABRIR_MATERIAS_ENFECHA
                    data['dentro_fechas'] = materia.fin >= datetime.now().date()
                    data['auditor'] = False
                    data['reporte_0'] = obtener_reporte('acta_notas')
                    data['reporte_1'] = obtener_reporte('lista_control_calificaciones')
                    data['reporte_2'] = obtener_reporte('acta_notas_parcial')
                    data['reporte_3'] = obtener_reporte('evaluaciones_materia')
                    data['reporte_4'] = obtener_reporte('listado_estudiantes_datosxmateria')
                    data['materia_nivelacion'] = materia.es_nivelacion()
                    data['muestra_estado_nivelacion'] = MUESTRA_ESTADO_NIVELACION
                    data['profesormateria'] = ProfesorMateria.objects.filter(materia=materia, profesor=profesor)[0]
                    template = get_template("pro_evaluaciones/segmento.html")
                    json_content = template.render(data)
                    return ok_json({'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=3, ex=ex)

            if action == 'cierretodas':
                try:
                    materia = Materia.objects.get(pk=request.POST['mid'])
                    for materiaasignada in materia.materiaasignada_set.all():
                        materiaasignada.cerrado = True
                        materiaasignada.fechacierre = datetime.now().date()
                        materiaasignada.save(request)
                        materiaasignada.actualiza_estado()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'actualicetodas':
                try:
                    materia = Materia.objects.get(pk=request.POST['mid'])
                    materia.recalcularmateria()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'solicitud':
                try:
                    materia = Materia.objects.get(pk=request.POST['idm'])
                    campo = DetalleModeloEvaluativo.objects.get(pk=request.POST['idc'])
                    if SolicitudIngresoNotasAtraso.objects.filter(materia=materia, profesor=profesor, detallemodeloevaluativo=campo, estado=1).exists():
                        return bad_json(mensaje=u'Ya existe una solicitud registrada para este campo.')
                    solicitud = SolicitudIngresoNotasAtraso(materia=materia,
                                                            profesor=profesor,
                                                            detallemodeloevaluativo=campo,
                                                            motivo=request.POST['motivo'],
                                                            fechasolicitud=datetime.now().date())
                    solicitud.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'solicitudestudiante':
                try:
                    materia = MateriaAsignada.objects.get(pk=request.POST['ida'])
                    campo = ModeloEvaluativo.objects.get(pk=request.POST['idc'])
                    if SolicitudIngresoNotasEstudiante.objects.filter(materiaasignada=materia, profesor=profesor, modeloevaluativo=campo, estado=1).exists():
                        return bad_json(mensaje=u'Ya existe una solicitud registrada para este campo.')
                    solicitud = SolicitudIngresoNotasEstudiante(materiaasignada=materia,
                                                                profesor=profesor,
                                                                modeloevaluativo=campo,
                                                                motivo=request.POST['motivo'],
                                                                fechasolicitud=datetime.now().date())
                    solicitud.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'nee':
                try:
                    data['materias'] = materia = MateriaAsignada.objects.get(pk=int(request.POST['id']))
                    data['nee'] = DescripcionNeeBienestar.objects.filter(nee=materia.nee())
                    template = get_template("pro_evaluaciones/nee.html")
                    json_content = template.render(data)
                    return ok_json(data={"result": "ok", 'html': json_content})
                except Exception as ex:
                    return bad_json(error=1)

            if action == 'importarlms':
                try:
                    materia = Materia.objects.get(pk=int(request.POST['id']))
                    logicaimportacion = materia.modeloevaluativo.logica_modelo_lms(materia.lms)
                    if logicaimportacion.logica:
                        local_scope = {}
                        exec(logicaimportacion.logica, globals(), local_scope)
                        importar_notas = local_scope['importar_notas']
                        datos = importar_notas(materia)
                        for cols in datos:
                            cronograma = materia.cronogramacalificaciones()
                            if materia.materiaasignada_set.filter(id=int(cols['id'])).exists():
                                materiaasignada = materia.materiaasignada_set.filter(id=cols['id'])[0]
                                for campo in cols['notas']:
                                    try:
                                        valor = float(campo['valor'])
                                        if cronograma:
                                            campomodelo = materia.modeloevaluativo.detallemodeloevaluativo_set.filter(nombre=campo['campo'])[0]
                                            permiteingresonotas = campomodelo.permite_ingreso_nota(materiaasignada, cronograma)
                                            if permiteingresonotas:
                                                result = actualizar_nota(request, materiaasignada=materiaasignada, sel=campomodelo.nombre, valor=valor, rapido=True)
                                    except Exception as ex:
                                        pass
                        local_scope = {}
                        exec(materia.modeloevaluativo.logicamodelo, globals(), local_scope)
                        calculo_modelo_evaluativo = local_scope['calculo_modelo_evaluativo']
                        for materiaasignada in materia.materiaasignada_set.all():
                            calculo_modelo_evaluativo(materiaasignada)
                            materiaasignada.actualiza_estado()
                    log(u'importo calificaciones de lms: %s' % materia, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'importar':
                try:
                    data['title'] = u'Importar notas'
                    data['form'] = ImportarArchivoXLSForm()
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    return render(request, "pro_evaluaciones/importar.html", data)
                except Exception as ex:
                    pass

            if action == 'solicitud':
                try:
                    data['title'] = u'Solicitar ingreso de notas'
                    data['form'] = SolicitudIngresoNotasForm()
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    data['campo'] = DetalleModeloEvaluativo.objects.get(pk=request.GET['idc'])
                    return render(request, "pro_evaluaciones/solicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'importarlms':
                try:
                    data['title'] = u'Importar notas de LMS'
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    return render(request, "pro_evaluaciones/importarlms.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Evaluaciones de alumnos'
                data['materias'] = materias = Materia.objects.filter(profesormateria__profesor=profesor, nivel__periodo=periodo)
                materiaid = 0
                if 'idm' in request.GET:
                    if int(request.GET['idm']) > 0:
                        materia = materias.filter(id=int(request.GET['idm']))[0]
                        materiaid = materia.id
                        request.session['pro_evaluaciones_materia'] = materiaid
                    else:
                        del request.session['pro_evaluaciones_materia']
                        materiaid = 0
                elif 'pro_evaluaciones_materia' in request.session:
                    materiaid = int(request.session['pro_evaluaciones_materia'])
                    if materiaid not in Materia.objects.filter(profesormateria__profesor=profesor,
                                                               profesormateria__principal=True,
                                                               nivel__periodo=periodo,
                                                               profesormateria__profesor__profesordistributivohoras__aprobadodecano=True).values_list('id', flat=True):
                        del request.session['pro_evaluaciones_materia']
                        materiaid = 0
                if materiaid > 0:
                    data['materiaid'] = materiaid
                data['utiliza_validacion_calificaciones'] = UTILIZA_VALIDACION_CALIFICACIONES
                data['habilitado_ingreso_calificaciones'] = profesor.habilitado_ingreso_calificaciones()
                return render(request, "pro_evaluaciones/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
