# coding=utf-8
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from decorators import secure_module, last_access
from settings import PERMITE_ABRIR_MATERIAS_ENFECHA, MUESTRA_ESTADO_NIVELACION, PERSONA_ADMINS_ACADEMICO_ID
from ctt.commonviews import adduserdata, actualizar_nota, obtener_reporte
from ctt.forms import SolicitudIngresoNotasForm
from ctt.funciones import log, generar_nombre, url_back, bad_json, ok_json, MiPaginador
from ctt.models import Materia, MateriaAsignada, LeccionGrupo, DetalleModeloEvaluativo, \
    SolicitudIngresoNotasEstudiante, ModeloEvaluativo


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
    coordinacion = request.session['coordinacionseleccionada']
    data['PERSONA_ADMINS_ACADEMICO_ID'] = False
    if persona.id in PERSONA_ADMINS_ACADEMICO_ID:
        data['PERSONA_ADMINS_ACADEMICO_ID'] = True

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'segmento':
                try:
                    search = None
                    ids = None
                    if 'id' in request.POST:
                        request.session['pro_evaluaciones_materia'] = data['materiaid'] = int(request.POST['id'])
                    data['materia'] = materia = Materia.objects.get(pk=request.session['pro_evaluaciones_materia'])
                    paging = MiPaginador(materia.asignados_a_esta_materia(), 5)
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
                    template = get_template("adm_evaluaciones/segmento.html")
                    json_content = template.render(data)
                    return ok_json({'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=3, ex=ex)

            if action == 'cerrarmateriaasignada':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['maid'])
                    materiaasignada.cerrado = (request.POST['cerrado'] == 'false')
                    materiaasignada.fechacierre = datetime.now().date()
                    materiaasignada.save(request)
                    materiaasignada.actualiza_estado()
                    materiasabiertas = MateriaAsignada.objects.filter(materia=materiaasignada.materia, cerrado=False).count()
                    log(u'Cerro materia asignada: %s' % materiaasignada.matricula.inscripcion, request, "add")
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
                        asig.cierre_materia_asignada()
                    for lg in LeccionGrupo.objects.filter(lecciones__clase__materia=materia, abierta=True):
                        lg.abierta = False
                        lg.horasalida = lg.turno.termina
                        lg.save(request)
                    log(u'Cerro la materia: %s' % materia, request, "add")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'nota':
                try:
                    result = actualizar_nota(request)
                    log(u'Actualizó nota: %s' % result, request, "add")
                    return ok_json(result)
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

            if action == 'observaciones':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materiaasignada.observaciones = request.POST['observacion']
                    materiaasignada.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

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

            if action == 'solicitudestudiante':
                try:
                    materia = MateriaAsignada.objects.get(pk=request.POST['ida'])
                    campo = ModeloEvaluativo.objects.get(pk=request.POST['idc'])
                    if SolicitudIngresoNotasEstudiante.objects.filter(materiaasignada=materia, profesor=profesor, modeloevaluativo=campo, estado=1).exists():
                        return bad_json(mensaje=u'Ya existe una solicitud registrada para este campo.')
                    solicitud = SolicitudIngresoNotasEstudiante(materiaasignada=materia,
                                                                profesor=materia.profesores()[0],
                                                                modeloevaluativo=campo,
                                                                motivo=request.POST['motivo'],
                                                                fechasolicitud=datetime.now().date())
                    solicitud.save(request)
                    log(u'Genero solicitud apertura de notas por estudiante: %s' % solicitud.materiaasignada.matricula.inscripcion,
                        request, "add")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'subir':
                try:
                    form = RequisitosProcesoAplicanteBecaForm(request.POST, request.FILES)
                    if form.is_valid():
                        ar = SolicitudIngresoNotasEstudiante.objects.get(pk=request.POST['id'])
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivosolingnotest_", newfile._name)
                        ar.archivo = newfile
                        ar.save(request)
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

            if action == 'subir':
                try:
                    data['title'] = u'Subir archivo'
                    data['solicitud'] = SolicitudIngresoNotasEstudiante.objects.get(pk=request.GET['id'])
                    data['materia'] = Materia.objects.get(pk=request.GET['idm'])
                    data['form'] = RequisitosProcesoAplicanteBecaForm()
                    return render(request, "adm_evaluaciones/subir.html", data)
                except Exception as ex:
                    pass

            if action == 'solicitud':
                try:
                    data['title'] = u'Solicitar ingreso de notas'
                    data['form'] = SolicitudIngresoNotasForm()
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    data['campo'] = DetalleModeloEvaluativo.objects.get(pk=request.GET['idc'])
                    return render(request, "adm_evaluaciones/solicitud.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Calificaciones de alumnos'
                data['materias'] = materias = Materia.objects.filter(profesormateria__profesor__coordinacion=coordinacion,
                                                                     nivel__periodo=periodo).order_by('asignatura')
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
                    if materiaid not in Materia.objects.filter(profesormateria__profesor__coordinacion=coordinacion,
                                                               profesormateria__principal=True,
                                                               nivel__periodo=periodo,
                                                               profesormateria__profesor__profesordistributivohoras__aprobadodecano=True).values_list('id', flat=True).order_by('asignatura'):
                        del request.session['pro_evaluaciones_materia']
                        materiaid = 0
                if materiaid > 0:
                    data['materiaid'] = materiaid
                return render(request, "adm_evaluaciones/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
