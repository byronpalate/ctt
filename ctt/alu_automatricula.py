# coding=utf-8
import json
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from decorators import secure_module, last_access
from settings import DATOS_INTEGRADORES, \
    PERMITE_MATRICULA_ESPECIAL_ALUMNO, LIMITAR_NIVEL_MATRICULA, NIVEL_MALLA_CERO
from ctt.adm_calculofinanzas import costo_matricula
from ctt.commonviews import adduserdata, materias_abiertas, matricular, conflicto_materias_seleccionadas, \
    nivel_matriculacion, existe_periodo_actualizacion_datos, periodo_actualizacion_datos, \
    calcular_costo
from ctt.forms import ActualizarDatosFacturaForm
from ctt.funciones import bad_json, ok_json, remover_tildes
from ctt.models import Nivel, Materia, Clase, Turno, mi_institucion, Asignatura, Periodo


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    perfilprincipal = request.session['perfilprincipal']
    inscripcion = perfilprincipal.inscripcion
    itinerario = inscripcion.mi_itinerario()
    institucion = mi_institucion()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'materiasabiertas':
                try:
                    asignatura = Asignatura.objects.get(pk=request.POST['ida'])
                    nivel = Nivel.objects.get(pk=request.POST['nivel'])
                    return ok_json(data=materias_abiertas(asignatura, inscripcion, nivel, estudiante=True))
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'matricular':
                return matricular(request, True, True)

            if action == 'calculocosto':
                return calcular_costo(request)

            if action == 'conflictohorario':
                try:
                    mismaterias = json.loads(request.POST['mismaterias'])
                    materias = Materia.objects.filter(id__in=[int(x) for x in mismaterias])
                    conflicto = conflicto_materias_seleccionadas(materias)
                    if conflicto:
                        return bad_json(mensaje=conflicto)
                    return ok_json()
                except:
                    return bad_json(error=3)

            if action == 'infohorario':
                try:
                    data = {}
                    periodo = None
                    lista = json.loads(request.POST['lista'])
                    data['materiasregulares'] = materiasregulares = Materia.objects.filter(id__in=lista).distinct()
                    data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                    data['clases'] = clases = Clase.objects.filter(materia__in=materiasregulares, activo=True).distinct()
                    data['turnos'] = Turno.objects.filter(clase__in=clases).distinct().order_by('comienza')
                    if materiasregulares:
                        periodo = materiasregulares.all()[0].nivel.periodo
                    data['periodo'] = periodo
                    template = get_template("alu_automatricula/aluhorario.html")
                    json_content = template.render(data)
                    return ok_json({'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=3, ex=ex)

            if action == 'costomatricula':
                try:
                    nivel = Nivel.objects.get(pk=request.POST['nivel'])
                    fecha = datetime.now().date()
                    asignaturas = json.loads(request.POST['asignaturas'])
                    materias = json.loads(request.POST['materias'])
                    costo = costo_matricula(inscripcion=inscripcion, asignaturas=asignaturas, materias=materias, nivel=nivel, fecha=fecha)
                    return ok_json(data={'costos': costo})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=3, ex=ex)

            if action == 'actualizardatosfactura':
                try:
                    clientefacturacion = inscripcion.clientefacturacion(request)
                    form = ActualizarDatosFacturaForm(request.POST)
                    if form.is_valid():
                        clientefacturacion.nombre = form.cleaned_data['facturanombre']
                        clientefacturacion.direccion = form.cleaned_data['facturadireccion']
                        clientefacturacion.identificacion = form.cleaned_data['facturaidentificacion']
                        clientefacturacion.telefono = form.cleaned_data['facturatelefono']
                        clientefacturacion.tipo = form.cleaned_data['facturatipoidentificacion']
                        clientefacturacion.email = form.cleaned_data['facturaemail']
                        clientefacturacion.save()
                        persona = inscripcion.persona
                        persona.actualizodatosfactura = True
                        persona.save()
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=3, ex=ex)

        return bad_json(error=0)
    else:
        try:
            data['title'] = u'Matriculación online'
            hoy = datetime.now().date()
            # YA MATRICULADO
            if inscripcion.matriculado():
                request.session['info'] = u'Usted ya se encuentra matriculado.'
                return HttpResponseRedirect('/')
                # SIN PERMISO A MATRICULARSE
            if not inscripcion.habilitadomatricula:
                request.session['info'] = u'Debe acercarse a secretaria docente para habilitar el permiso a matricularse.'
                return HttpResponseRedirect('/')
            # LIBRO PENDIENTE DE ENTREGA
            if inscripcion.persona.documentos_sin_entregar():
                request.session['info'] = u'Tiene un libro pendiente de entrega.'
                return HttpResponseRedirect('/')
            # VERIFICACION DATOS
            if DATOS_INTEGRADORES:
                if existe_periodo_actualizacion_datos(1):
                    data['periodoactualizacion'] = periodoactualizacion = periodo_actualizacion_datos(1)
                    if periodoactualizacion.socieconomicos:
                        if not periodoactualizacion.actualizo_datos_socioeconomicos(inscripcion):
                            request.session['info'] = u'Debe actualizar sus datos socioeconómicos.'
                            return HttpResponseRedirect('/')
                    if periodoactualizacion.medicos:
                        if not periodoactualizacion.actualizo_datos_medicos(inscripcion):
                            request.session['info'] = u'Debe actualizar sus datos médicos.'
                            return HttpResponseRedirect('/')
                    if periodoactualizacion.personales:
                        if not periodoactualizacion.actualizo_datos_personales(inscripcion):
                            request.session['info'] = u'Debe actualizar sus datos personales.'
                            return HttpResponseRedirect('/')
            # EXCLUYE GRADUADOS Y EGRESADOS
            if inscripcion.graduado() or inscripcion.egresado() or inscripcion.estainactivo():
                request.session['info'] = u'Solo podrán matricularse estudiantes activos.'
                return HttpResponseRedirect('/')
            # NO PUEDE TENER DEUDAS
            if not institucion.matricularcondeuda:
                if inscripcion.persona.tiene_deuda_vencida():
                    if not inscripcion.permitematriculacondeuda:
                        request.session['info'] = u'Debe cancelar los valores pendientes para poder matricularse.'
                        return HttpResponseRedirect('/')
            # NO PUEDE TENER MATERIAS MAS DE 5 AñOS
            if not inscripcion.recordacademico_set.filter(fecha__gte=hoy - timedelta(days=1825)).exists() and inscripcion.recordacademico_set.exists():
                request.session['info'] = u'Debe acercarse a secretaria para matricularse, por no haber tomado materias hace mas de 5 años.'
                return HttpResponseRedirect('/')
            # MATRICULACION SOLO DISTANCIA
            data['malla'] = malla = inscripcion.mi_malla()
            if not malla.matriculaonline:
                request.session['info'] = u'La matriculación online no está habilitada para su carrera.'
                return HttpResponseRedirect('/')
            # PERDIDA DE CARRERA POR 4TA MATRICULA
            if inscripcion.tiene_perdida_carrera():
                request.session['info'] = u'Atención: Su límite de matrícula por perdida de una o más asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para más información.'
                return HttpResponseRedirect('/')
            # MATRICULACION OBLIGATORIA POR SECRETARIA SI ES 3RA MATRICULA
            if inscripcion.tiene_tercera_matricula():
                request.session['info'] = u'Atención: Su límite de matrícula por perdida de una o más asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para más información.'
                return HttpResponseRedirect('/')
            data['nivel'] = nivel = nivel_matriculacion(inscripcion)
            ultimamatricula = inscripcion.ultima_matricula_sinextendido()
            if ultimamatricula:
                periodo_re = ultimamatricula.nivel.periodo
                periodo_anterior = Periodo.objects.filter(inicio__lt=nivel.periodo.inicio, extendido=False,  tipo=2).order_by('-inicio').first()
                es_posgrado = True if (inscripcion.carrera.posgrado) else False
                if periodo_anterior and periodo_anterior != periodo_re and not es_posgrado:
                    request.session['info'] = u'Debe acercarse a Secretaría para gestionar su matrícula, ya que usted no estudió en periodos consecutivos.'
                    return HttpResponseRedirect('/')
            if not nivel:
                request.session['info'] = u'No existen niveles para matricularse.'
                return HttpResponseRedirect('/')
            else:
                # FECHA TOPE PARA MATRICULACION
                if PERMITE_MATRICULA_ESPECIAL_ALUMNO:
                    if datetime.now().date() > nivel.fechatopematriculaes:
                        request.session['info'] = u'Terminó el periodo de matriculación. Por favor acercarse a secretaria para tramitar la matrícula extraordinaria'
                        return HttpResponseRedirect('/')
                else:
                    if datetime.now().date() > nivel.fechatopematriculaex:
                        request.session['info'] = u'Terminó el periodo de matriculación. Por favor acercarse a secretaria para tramitar la matrícula extraordinaria'
                        return HttpResponseRedirect('/')
                # CRONOGRAMA DE MATRICULACION SEGUN FECHAS
                if not inscripcion.puede_matricularse_seguncronograma(nivel.periodo):
                    request.session['info'] = u'Aún no está habilitado el cronograma de matriculación de su carrera.'
                    return HttpResponseRedirect('/')
            # PERIODO ACTIVO PARA MATRICULACION
            if not nivel.periodo.matriculacionactiva:
                request.session['info'] = u'El periodo no se encuentra activo para poder matricularse.'
                return HttpResponseRedirect('/')
            # PASO TODOS LOS FILTRO DE LIMITACIONES
            data['inscripcion'] = inscripcion
            if inscripcion.mi_nivel().nivel.id == NIVEL_MALLA_CERO:
                data['materiasmalla'] = malla.asignaturamalla_set.filter(Q(itinerario__isnull=True) | Q(itinerario=itinerario), nivelmalla__id=NIVEL_MALLA_CERO).order_by('nivelmalla', 'ejeformativo')
            else:
                if LIMITAR_NIVEL_MATRICULA:
                    data['materiasmalla'] = malla.asignaturamalla_set.filter(Q(itinerario__isnull=True) | Q(itinerario=itinerario), nivelmalla__id__lte=inscripcion.mi_nivel().nivel.id).filter(matriculacion=True).order_by('nivelmalla', 'ejeformativo')
                else:
                    data['materiasmalla'] = malla.asignaturamalla_set.filter(Q(itinerario__isnull=True) | Q(itinerario=itinerario)).filter(matriculacion=True).order_by('nivelmalla', 'ejeformativo')
                    # ACTUALIZO DATOS FACTURA
                if not inscripcion.persona.actualizodatosfactura:
                    data['title'] = u'Actualizar datos facturación'
                    clientefacturacion = inscripcion.clientefacturacion(request)
                    data['form'] = ActualizarDatosFacturaForm(initial={'facturaidentificacion': clientefacturacion.identificacion,
                                                                       'facturatipoidentificacion': clientefacturacion.tipo,
                                                                       'facturanombre': remover_tildes(clientefacturacion.nombre),
                                                                       'facturadireccion': remover_tildes(clientefacturacion.direccion),
                                                                       'facturatelefono': remover_tildes(clientefacturacion.telefono),
                                                                       'facturaemail': clientefacturacion.email})
                    data['matriculado'] = inscripcion.matricula
                    return render(request, "alu_automatricula/actualizardatosfactura.html", data)
            data['maximo_materia_online'] = malla.maximomateriasonline
            data['total_materias_nivel'] = inscripcion.total_materias_nivel()
            if inscripcion.mi_nivel().nivel.id < 7:
                data['materiasmodulos'] = malla.modulomalla_set.all().order_by('asignatura__nombre')
            else:
                data['materiasmodulos'] = None
            data['datosincripcion'] = inscripcion.documentosdeinscripcion_set.all()[0]
            data['aprobo_nivelacion'] = inscripcion.aprobo_nivelacion()
            return render(request, "alu_automatricula/view.html", data)
        except Exception as ex:
            return HttpResponseRedirect('/')
