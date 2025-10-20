# coding=utf-8
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import RequestContext

from decorators import secure_module, last_access
from settings import TIPO_IVA_15_ID
from ctt.commonviews import adduserdata
from ctt.forms import TipoCostoCursoForm, TipoEspecieForm, ClonarPreciosPeriodoForm
from ctt.funciones import log, bad_json, ok_json, url_back, convertir_fecha, generar_nombre
from ctt.models import Sede, PreciosPeriodo, null_to_numeric, PreciosPeriodoModulosInscripcion, TipoCostoCursoPeriodo, \
    TipoCostoCurso, CostodiferenciadoCursoPeriodo, TipoEspecieValorada, \
    HistoricoTipoEspecieValorada, Carrera, Modalidad, Malla, Periodo,  IvaAplicado, DescuentoFormaPago, ValoresMinimosPeriodoBecaMatricula, FormaDePago


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    persona = request.session['persona']
    hoy = datetime.now().date()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'act_precio_mat_curso_dif':
                try:
                    pp = CostodiferenciadoCursoPeriodo.objects.get(pk=int(request.POST['id']))
                    pp.costomatricula = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio curso: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_preciotipotribunal_pago':
                try:
                    pp = PreciosTipoTribunal.objects.get(pk=int(request.POST['id']))
                    pp.pago = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio pago pregrado: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_preciotipotribunal_pagoposgrados':
                try:
                    pp = PreciosTipoTribunal.objects.get(pk=int(request.POST['id']))
                    periodos = int(request.POST['periodos'])
                    if periodos == 2:
                        pp.pagoposgrados2 = float(request.POST['valor'])
                    elif periodos == 3:
                        pp.pagoposgrados3 = float(request.POST['valor'])
                    else:
                        pp.pagoposgrados = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio pago posgrado: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_preciotipotribunal_examencomplexivo':
                try:
                    pp = PreciosTipoTribunal.objects.get(pk=int(request.POST['id']))
                    pp.examencomplexivo = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio examen complexivo: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_preciotipotribunal_tp':
                try:
                    pp = PreciosTipoTribunal.objects.get(pk=int(request.POST['id']))
                    pp.tienepago = bool(request.POST['valor'])
                    pp.save(request)
                    log(u'Activo precio tipo tribunal: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_preciotipotribunal_tc':
                try:
                    pp = PreciosTipoTribunal.objects.get(pk=int(request.POST['id']))
                    pp.tiempocompleto = bool(request.POST['valor'])
                    pp.save(request)
                    log(u'Activo/desactivo precio tipo tribunal: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_preciotipotribunal_mt':
                try:
                    pp = PreciosTipoTribunal.objects.get(pk=int(request.POST['id']))
                    pp.mediotiempo = bool(request.POST['valor'])
                    pp.save(request)
                    log(u'Activo/desactivo precio tipo tribunal: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_preciotipotribunal_ta':
                try:
                    pp = PreciosTipoTribunal.objects.get(pk=int(request.POST['id']))
                    pp.tiempoparcial = bool(request.POST['valor'])
                    pp.save(request)
                    log(u'Activo/desactivo precio tipo tribunal: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_aplicaextra':
                try:
                    pp = PreciosPeriodo.objects.get(pk=int(request.POST['id']))
                    pp.aplicaextra = True if request.POST['valor'] == 'true' else False
                    pp.save(request)
                    log(u'Activo/desactivo aplica valor mat.extraordinaria: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_cuotas_curso_dif':
                try:
                    pp = CostodiferenciadoCursoPeriodo.objects.get(pk=int(request.POST['id']))
                    pp.cuotas = int(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico cuotas curso: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_ara_curso_dif':
                try:
                    pp = CostodiferenciadoCursoPeriodo.objects.get(pk=int(request.POST['id']))
                    pp.costocuota = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio arancel: %s - %s' % (pp.tipocostocursoperiodo.tipocostocurso, pp.costocuota), request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_mat_curso':
                try:
                    pp = TipoCostoCursoPeriodo.objects.get(pk=int(request.POST['id']))
                    pp.costomatricula = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio matricula curso: %s' % pp.tipocostocurso.nombre, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_cuotas_curso':
                try:
                    pp = TipoCostoCursoPeriodo.objects.get(pk=int(request.POST['id']))
                    pp.cuotas = int(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico cuotas: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_ara_curso':
                try:
                    pp = TipoCostoCursoPeriodo.objects.get(pk=int(request.POST['id']))
                    pp.costocuota = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio arancel: %s - %s' % (pp.tipocostocurso,pp.costocuota), request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_mat':
                try:
                    pp = PreciosPeriodo.objects.get(pk=int(request.POST['id']))
                    pp.preciomatricula = float(request.POST['valor'])
                    pp.save(request)
                    valor = null_to_numeric(pp.precioarancel + pp.preciomatricula, 2)
                    log(u'Modifico precio matricula: %s' % pp, request, "edit")
                    return ok_json({'valor': valor})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_ara':
                try:
                    pp = PreciosPeriodo.objects.get(pk=int(request.POST['id']))
                    pp.precioarancel = float(request.POST['valor'])
                    pp.save(request)
                    valor = null_to_numeric(pp.precioarancel + pp.preciomatricula, 2)
                    log(u'Modifico precio arancel: %s' % pp, request, "edit")
                    return ok_json({'valor': valor})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_derechorotativo':
                try:
                    pp = PreciosPeriodo.objects.get(pk=int(request.POST['id']))
                    pp.precioderechorotativo = float(request.POST['valor'])
                    pp.save(request)
                    valor = null_to_numeric(pp.precioarancel + pp.preciomatricula + pp.precioderechorotativo, 2)
                    log(u'Modifico precio derecho rotativo: %s' % pp, request, "edit")
                    return ok_json({'valor': valor})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_cuotas':
                try:
                    pp = PreciosPeriodo.objects.get(pk=int(request.POST['id']))
                    pp.cuotas = int(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico cuotas: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_meses':
                try:
                    pp = PreciosPeriodo.objects.get(pk=int(request.POST['id']))
                    pp.meses = int(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico meses: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_fecha':
                try:
                    pp = PreciosPeriodo.objects.get(pk=int(request.POST['id']))
                    pp.fecha = convertir_fecha(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico fechas: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_modulo':
                try:
                    pp = PreciosPeriodoModulosInscripcion.objects.get(pk=int(request.POST['id']))
                    pp.preciomodulo = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio modulo: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_arrastremodulo':
                try:
                    pp = PreciosPeriodoModulosInscripcion.objects.get(pk=int(request.POST['id']))
                    pp.precioarrastremodulo = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio arrastre modulo: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_sininscripcion':
                try:
                    pp = PreciosPeriodoModulosInscripcion.objects.get(pk=int(request.POST['id']))
                    pp.sininscripcion = True if request.POST['valor'] == 'true' else False
                    pp.save(request)
                    log(u'Activo/desactivo valida valor de inscripcion: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_moduloins':
                try:
                    pp = PreciosPeriodoModulosInscripcion.objects.get(pk=int(request.POST['id']))
                    pp.precioinscripcion = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio inscripcion: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_moduloind':
                try:
                    pp = PreciosPeriodoModulosInscripcion.objects.get(pk=int(request.POST['id']))
                    pp.precioinduccion = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio induccion: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_moduloreingreso':
                try:
                    pp = PreciosPeriodoModulosInscripcion.objects.get(pk=int(request.POST['id']))
                    pp.precioreingreso = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio reingreso: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)
            #
            # if action == 'act_precio_hexterna':
            #     try:
            #         pp = PreciosPeriodoModulosInscripcion.objects.get(pk=int(request.POST['id']))
            #         pp.preciohexterna = float(request.POST['valor'])
            #         pp.save(request)
            #         log(u'Modifico precio homologacion externa: %s' % pp, request, "edit")
            #         return ok_json()
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return bad_json(error=1)

            if action == 'act_precio_modulohomolog':
                try:
                    pp = PreciosPeriodoModulosInscripcion.objects.get(pk=int(request.POST['id']))
                    pp.preciohomologacion = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio homologacion: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_modulohomologconv':
                try:
                    pp = PreciosPeriodoModulosInscripcion.objects.get(pk=int(request.POST['id']))
                    pp.preciohomologacionconvenio = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio homg-conv: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_modulored':
                try:
                    pp = PreciosPeriodoModulosInscripcion.objects.get(pk=int(request.POST['id']))
                    pp.precioredmaestros = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio red maestros: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precio_especie':
                try:
                    pp = TipoEspecieValorada.objects.get(pk=int(request.POST['id']))
                    pp.precio = float(request.POST['valor'])
                    pp.save(request)
                    historico = HistoricoTipoEspecieValorada(tipoespecievalorada=pp,
                                                             precio=float(request.POST['valor']),
                                                             fecha=datetime.now(),
                                                             persona=persona)
                    historico.save(request)
                    log(u'Modifico precio especie: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_porcsegmat':
                try:
                    pp = PreciosPeriodoModulosInscripcion.objects.get(pk=int(request.POST['id']))
                    pp.porcentajesegundamatricula = int(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio arancel: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_porctermat':
                try:
                    pp = PreciosPeriodoModulosInscripcion.objects.get(pk=int(request.POST['id']))
                    pp.porcentajeterceramatricula = int(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio arancel: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_pormatext':
                try:
                    pp = PreciosPeriodoModulosInscripcion.objects.get(pk=int(request.POST['id']))
                    pp.porcentajematriculaextraordinaria = int(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio arancel: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_preciotitulacion':
                try:
                    pp = PreciosPeriodoModulosInscripcion.objects.get(pk=int(request.POST['id']))
                    pp.preciotitulacion = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio titulacion: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'act_precioadelantoidiomas':
                try:
                    pp = PreciosPeriodoModulosInscripcion.objects.get(pk=int(request.POST['id']))
                    pp.precioadelantoidiomas = float(request.POST['valor'])
                    pp.save(request)
                    log(u'Modifico precio adelanto idiomas: %s' % pp, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addcostoconvenio':
                try:
                    form = PreciosConvenioHomologacionForm(request.POST)
                    if form.is_valid():
                        precioconvenio = PreciosConvenioHomologacion(periodo=periodo,
                                                                     nombre=form.cleaned_data['nombre'],
                                                                     costoconvenio=form.cleaned_data['costo'])
                        precioconvenio.save()
                        log(u'Adiciono costo convenio homologacion: %s' % precioconvenio, request, "add")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addcostoparqueadero':
                try:
                    form = PreciosServicioParqueaderoForm(request.POST)
                    if form.is_valid():
                        if not PreciosServicioParqueadero.objects.filter(nombre='SERVICIO DE PARQUEADERO', sede=form.cleaned_data['sede'], periodo=periodo, modalidad=form.cleaned_data['modalidad'], tiempo=form.cleaned_data['tiempo'], tipovehiculo=form.cleaned_data['tipovehiculo'], posgrado=form.cleaned_data['posgrado']).exists():
                            porcientoiva = IvaAplicado.objects.get(pk=TIPO_IVA_15_ID).porcientoiva
                            costototal = float(form.cleaned_data['costototal'])
                            costosubtotal = round((costototal / (porcientoiva + 1)), 2)
                            iva = costototal - costosubtotal
                            costoadicionalperdida = float(form.cleaned_data['costoadicionalperdida']) - (float(form.cleaned_data['costoadicionalperdida']) - round((float(form.cleaned_data['costoadicionalperdida']) / (porcientoiva + 1)),2))
                            precioservicioparqueadero = PreciosServicioParqueadero(periodo=periodo,
                                                                                   sede=form.cleaned_data['sede'],
                                                                                   modalidad=form.cleaned_data['modalidad'],
                                                                                   nombre='SERVICIO DE PARQUEADERO',
                                                                                   costototal=costototal,
                                                                                   costosubtotal=costosubtotal,
                                                                                   iva=iva,
                                                                                   costoadicionalperdida=costoadicionalperdida,
                                                                                   posgrado=form.cleaned_data['posgrado'],
                                                                                   tiempo=form.cleaned_data['tiempo'],
                                                                                   tipovehiculo=form.cleaned_data['tipovehiculo'])
                            precioservicioparqueadero.save()
                            log(u'Adiciono costo servicio parqueadero: %s' % precioservicioparqueadero, request, "add")
                        else:
                            return bad_json('Los parámetros de ingreso ya existen.')
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editcostoparqueadero':
                try:
                    form = PreciosServicioParqueaderoForm(request.POST)
                    if form.is_valid():
                        porcientoiva = IvaAplicado.objects.get(pk=TIPO_IVA_15_ID).porcientoiva
                        costototal = float(form.cleaned_data['costototal'])
                        costosubtotal = round((costototal / (porcientoiva + 1)), 2)
                        iva = round(costototal - costosubtotal, 2)
                        costoadicionalperdida = float(form.cleaned_data['costoadicionalperdida']) - (float(form.cleaned_data['costoadicionalperdida']) - round((float(form.cleaned_data['costoadicionalperdida']) / (porcientoiva + 1)), 2))
                        costoparqueo = PreciosServicioParqueadero.objects.get(pk=request.POST['id'])
                        costoparqueo.nombre = 'SERVICIO DE PARQUEADERO'
                        costoparqueo.sede = form.cleaned_data['sede']
                        costoparqueo.modalidad = form.cleaned_data['modalidad']
                        costoparqueo.costototal = costototal
                        costoparqueo.costosubtotal = costosubtotal
                        costoparqueo.iva = iva
                        costoparqueo.costoadicionalperdida = costoadicionalperdida
                        costoparqueo.posgrado = form.cleaned_data['posgrado']
                        costoparqueo.tiempo = form.cleaned_data['tiempo']
                        costoparqueo.tipovehiculo = form.cleaned_data['tipovehiculo']
                        costoparqueo.save()
                        log(u'Edito costo servicio parqueadero: %s' % costoparqueo, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addcostoscursos':
                try:
                    form = TipoCostoCursoForm(request.POST)
                    if form.is_valid():
                        tipo = TipoCostoCurso(nombre=form.cleaned_data['nombre'],
                                              titulacion=form.cleaned_data['titulacion'],
                                              cursos=form.cleaned_data['cursos'],
                                              actualizacionconocimiento=form.cleaned_data['actualizacionconocimiento'],
                                              costodiferenciado=form.cleaned_data['costodiferenciado'],
                                              validapromedio=form.cleaned_data['validapromedio'])
                        tipo.save()
                        log(u'Adiciono tipo de costo curso: %s' % tipo, request, "add")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editcostoscursos':
                try:
                    form = TipoCostoCursoForm(request.POST)
                    if form.is_valid():
                        tipo = TipoCostoCurso.objects.get(pk=request.POST['id'])
                        tipo.nombre = form.cleaned_data['nombre']
                        if not tipo.tiene_uso():
                            tipo.costolibre = form.cleaned_data['costolibre']
                            tipo.titulacion = form.cleaned_data['titulacion']
                            tipo.cursos = form.cleaned_data['cursos']
                            tipo.actualizacionconocimiento = form.cleaned_data['actualizacionconocimiento']
                            tipo.costodiferenciado = form.cleaned_data['costodiferenciado']
                            tipo.validapromedio = form.cleaned_data['validapromedio']
                        tipo.save()
                        log(u'Adiciono tipo de costo curso: %s' % tipo, request, "add")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editcostoconvenio':
                try:
                    form = PreciosConvenioHomologacionForm(request.POST)
                    if form.is_valid():
                        costoconvenio = PreciosConvenioHomologacion.objects.get(pk=request.POST['id'])
                        costoconvenio.nombre = form.cleaned_data['nombre']
                        # if not costoconvenio.tiene_uso():
                        costoconvenio.costoconvenio = form.cleaned_data['costo']
                        costoconvenio.save()
                        log(u'Edito costo convenio: %s' % costoconvenio, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addespecie':
                try:
                    form = TipoEspecieForm(request.POST)
                    if form.is_valid():
                        tipo = TipoEspecieValorada(nombre=form.cleaned_data['nombre'],
                                                   iva=form.cleaned_data['iva'],
                                                   precio=form.cleaned_data['precio'])
                        tipo.save()
                        log(u'Adiciono tipo de especie valorada: %s' % tipo, request, "add")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editespecie':
                try:
                    form = TipoEspecieForm(request.POST)
                    if form.is_valid():
                        tipo = TipoEspecieValorada.objects.get(pk=request.POST['id'])
                        tipo.nombre = form.cleaned_data['nombre']
                        tipo.iva = form.cleaned_data['iva']
                        tipo.precio = form.cleaned_data['precio']
                        tipo.save()
                        log(u'Modifico tipo de especie valorada: %s' % tipo, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'activartipo':
                try:
                    tipo = TipoCostoCursoPeriodo.objects.get(pk=request.POST['id'])
                    tipo.activo = True
                    tipo.save(request)
                    log(u'Activo tipo de costo curso: %s' % tipo, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'desactivartipo':
                try:
                    tipo = TipoCostoCursoPeriodo.objects.get(pk=request.POST['id'])
                    tipo.activo = False
                    tipo.save(request)
                    log(u'Desactivo tipo de costo curso: %s' % tipo, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'activarespecie':
                try:
                    tipo = TipoEspecieValorada.objects.get(pk=request.POST['id'])
                    tipo.activa = True
                    tipo.save(request)
                    log(u'Activo tipo de especie: %s' % tipo, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'desactivarespecie':
                try:
                    tipo = TipoEspecieValorada.objects.get(pk=request.POST['id'])
                    tipo.activa = False
                    tipo.save(request)
                    log(u'Desactivo tipo de especie: %s' % tipo, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delespecie':
                try:
                    tipo = TipoEspecieValorada.objects.get(pk=request.POST['id'])
                    log(u'Elimino tipo de especie: %s' % tipo, request, "del")
                    tipo.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'clonarvalores':
                try:
                    form = ClonarPreciosPeriodoForm(request.POST)
                    periodoactual = Periodo.objects.get(pk=periodo.id)
                    periodoseleccionado = Periodo.objects.get(pk=int(request.POST['periodo']))
                    if form.is_valid():
                        if periodoactual.preciosperiodo_set.filter(clonado=True).exists():
                            return bad_json(mensaje='No se puede copiar valores a este periodo %s porque ya fueron clonados anteriormente' % periodoactual.nombre)
                        else:
                            if periodoactual == periodoseleccionado:
                                return bad_json(mensaje='No se pude clonar valores del mismo periodo')
                        for valoranterior in periodoseleccionado.preciosperiodo_set.all():
                            if periodoactual.preciosperiodo_set.filter(sede=valoranterior.sede, nivel=valoranterior.nivel, carrera=valoranterior.carrera, modalidad=valoranterior.modalidad).exists():
                                valoractual = periodoactual.preciosperiodo_set.filter(sede=valoranterior.sede, nivel=valoranterior.nivel, carrera=valoranterior.carrera, modalidad=valoranterior.modalidad)[0]
                                valoractual.periodo = periodo
                                valoractual.sede = valoranterior.sede
                                valoractual.carrera = valoranterior.carrera
                                valoractual.modalidad = valoranterior.modalidad
                                valoractual.malla = valoranterior.malla
                                valoractual.nivel = valoranterior.nivel
                                valoractual.cortes = valoranterior.cortes
                                valoractual.preciomatricula = valoranterior.preciomatricula
                                valoractual.precioarancel = valoranterior.precioarancel
                                valoractual.fecha = valoranterior.fecha
                                valoractual.cuotas = valoranterior.cuotas
                                valoractual.meses = valoranterior.meses
                                valoractual.clonado = True
                                valoractual.save(request)
                            else:
                                valoresnuevos = PreciosPeriodo(periodo=periodo,
                                                               sede=valoranterior.sede,
                                                               carrera=valoranterior.carrera,
                                                               modalidad=valoranterior.modalidad,
                                                               malla=valoranterior.malla,
                                                               nivel=valoranterior.nivel,
                                                               cortes=valoranterior.cortes,
                                                               preciomatricula=valoranterior.preciomatricula,
                                                               precioarancel=valoranterior.precioarancel,
                                                               fecha=periodoactual.inicio,
                                                               cuotas=valoranterior.cuotas,
                                                               meses=valoranterior.meses,
                                                               clonado=True)
                                valoresnuevos.save(request)
                        for valoranterior in periodoseleccionado.preciosperiodomodulosinscripcion_set.all():
                            if periodoactual.preciosperiodomodulosinscripcion_set.filter(sede=valoranterior.sede, carrera=valoranterior.carrera, modalidad=valoranterior.modalidad).exists():
                                valoractual = periodoactual.preciosperiodomodulosinscripcion_set.filter(sede=valoranterior.sede, carrera=valoranterior.carrera, modalidad=valoranterior.modalidad)[0]
                                valoractual.periodo = periodo
                                valoractual.sede = valoranterior.sede
                                valoractual.carrera = valoranterior.carrera
                                valoractual.modalidad = valoranterior.modalidad
                                valoractual.malla = valoranterior.malla
                                valoractual.cortes = valoranterior.cortes
                                valoractual.precioinscripcion = valoranterior.precioinscripcion
                                valoractual.preciomodulo = valoranterior.preciomodulo
                                valoractual.porcentajematriculaextraordinaria = valoranterior.porcentajematriculaextraordinaria
                                valoractual.porcentajesegundamatricula = valoranterior.porcentajesegundamatricula
                                valoractual.porcentajeterceramatricula = valoranterior.porcentajeterceramatricula
                                valoractual.preciohomologacion = valoranterior.preciohomologacion
                                valoractual.precioredmaestros = valoranterior.precioredmaestros
                                valoractual.preciohomologacionconvenio = valoranterior.preciohomologacionconvenio
                                valoractual.clonado=True
                                valoractual.save(request)
                            else:
                                valoresnuevos = PreciosPeriodoModulosInscripcion(periodo=periodo,
                                                                                 sede=valoranterior.sede,
                                                                                 malla=valoranterior.malla,
                                                                                 precioinscripcion=valoranterior.precioinscripcion,
                                                                                 preciomodulo=valoranterior.preciomodulo,
                                                                                 porcentajematriculaextraordinaria=valoranterior.porcentajematriculaextraordinaria,
                                                                                 porcentajesegundamatricula=valoranterior.porcentajesegundamatricula,
                                                                                 porcentajeterceramatricula=valoranterior.porcentajeterceramatricula,
                                                                                 preciohomologacion=valoranterior.preciohomologacion,
                                                                                 precioredmaestros=valoranterior.precioredmaestros,
                                                                                 carrera=valoranterior.carrera,
                                                                                 modalidad=valoranterior.modalidad,
                                                                                 cortes=valoranterior.cortes,
                                                                                 preciohomologacionconvenio=valoranterior.preciohomologacionconvenio,
                                                                                 clonado=True)
                                valoresnuevos.save(request)
                        log(u'Clono valores del periodo %s al periodo %s' % (periodoseleccionado.nombre,periodoactual.nombre), request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

        if action == 'clonarvaloresparqueo':
            try:
                form = ClonarPreciosPeriodoForm(request.POST)
                periodoactual = Periodo.objects.get(pk=periodo.id)
                periodoseleccionado = Periodo.objects.get(pk=int(request.POST['periodo']))
                if form.is_valid():
                    if periodoactual.preciosservicioparqueadero_set.filter(clonado=True).exists():
                        return bad_json(mensaje='No se puede copiar valores a este periodo %s porque ya fueron clonados anteriormente' % periodoactual.nombre)
                    else:
                        if periodoactual == periodoseleccionado:
                            return bad_json(mensaje='No se pude clonar valores del mismo periodo')
                    for valoranterior in periodoseleccionado.preciosservicioparqueadero_set.all():
                        valoractual = PreciosServicioParqueadero(periodo=periodo,
                                                                 nombre=valoranterior.nombre,
                                                                 sede=valoranterior.sede,
                                                                 modalidad=valoranterior.modalidad,
                                                                 costosubtotal=valoranterior.costosubtotal,
                                                                 costoadicionalperdida=valoranterior.costoadicionalperdida,
                                                                 posgrado=valoranterior.posgrado,
                                                                 tipovehiculo=valoranterior.tipovehiculo,
                                                                 tiempo_id=valoranterior.tiempo_id,
                                                                 costototal=valoranterior.costototal,
                                                                 iva=valoranterior.iva,
                                                                 clonado=True)
                        valoractual.save(request)
                    log(u'Clono valores del periodo %s al periodo %s' % (periodoseleccionado.nombre, periodoactual.nombre), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addfechaproceso':
            try:
                form = FechaSolicitudProrrogaSecretariaForm(request.POST)
                if form.is_valid():
                    if ProcesoSolicitudProrrogasSecretaria.objects.filter(periodo=periodo, modalidad_id=request.POST['mid']).exists():
                        proceso = ProcesoSolicitudProrrogasSecretaria.objects.filter(periodo=periodo, modalidad_id=request.POST['mid'])[0]
                    else:
                        proceso = ProcesoSolicitudProrrogasSecretaria(periodo=periodo, modalidad_id=request.POST['mid'],)
                        proceso.save()
                    fecha = FechasPeriodoSolicitudProrrogas(orden=request.POST['orden'], fechalimite=convertir_fecha(request.POST['fecha']))
                    fecha.save()
                    fecha.proceso.add(proceso.id)
                    log(u'Adiciono fecha: %s' % proceso, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editfechaproceso':
            try:
                form = FechaSolicitudProrrogaSecretariaForm(request.POST)
                if form.is_valid():
                    fecha = FechasPeriodoSolicitudProrrogas(pk=request.POST['id'])
                    fecha.orden = request.POST['orden']
                    fecha.fechalimite = convertir_fecha(request.POST['fecha'])
                    fecha.save()
                    log(u'Modifico fecha: %s' % fecha, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'subir':
            try:
                form = DocProcesoProrrogasSecretariaForm(request.POST, request.FILES)
                if form.is_valid():
                    pr = ProcesoSolicitudProrrogasSecretaria.objects.get(pk=request.POST['id'])
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("docaprobado_", newfile._name)
                    pr.archivo = newfile
                    pr.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delformapago':
            try:
                forma = DescuentoFormaPago.objects.get(pk=request.POST['id'])
                log(u'Elimino el descuento en la forma de pago: %s' % forma, request, "del")
                forma.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'act_porcentaje_formapago':
            try:
                pp = DescuentoFormaPago.objects.get(pk=int(request.POST['id']))
                pp.porcentaje = int(request.POST['valor'])
                pp.save(request)
                log(u'Modifico porcentaje descuento forma de pago: %s' % pp, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addformapago':
            try:
                form = FormaPagoDescuentoForm(request.POST, request.FILES)
                if form.is_valid():
                    if form.cleaned_data['todas']:
                        pr = PreciosPeriodo.objects.get(pk=request.POST['pid'])
                        for fp in FormaDePago.objects.filter(id__in=[1,3,4,5]).order_by("id"):
                            if not pr.descuentoformapago_set.filter(formadepago_id=fp).exists():
                                descuento = DescuentoFormaPago(precioperiodo=pr,
                                                               formadepago=fp,
                                                               fechainicio=form.cleaned_data['fechainicio'],
                                                               fechafin=form.cleaned_data['fechafin'],
                                                               porcentaje=form.cleaned_data['porcentaje'])
                                descuento.save()
                    else:
                        pr = PreciosPeriodo.objects.get(pk=request.POST['pid'])
                        if not pr.descuentoformapago_set.filter(formadepago_id=form.cleaned_data['formadepago']).exists():
                            descuento = DescuentoFormaPago(precioperiodo=pr,
                                                           formadepago=form.cleaned_data['formadepago'],
                                                           fechainicio=form.cleaned_data['fechainicio'],
                                                           fechafin=form.cleaned_data['fechafin'],
                                                           porcentaje=form.cleaned_data['porcentaje'])
                            descuento.save()
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addvalorperiodobeca':
            try:
                form = ValorPeriodoBecaFormalizarForm(request.POST)
                if form.is_valid():
                    valor = ValoresMinimosPeriodoBecaMatricula(
                        periodo = form.cleaned_data['periodo'],
                        valormatricula = form.cleaned_data['valormatricula'],
                        activavalormatricula = form.cleaned_data['activavalormatricula'],
                        porcentajematricula = form.cleaned_data['porcentajematricula'],
                        activaporcentajematricula = form.cleaned_data['activaporcentajematricula'],
                        valorbeca=form.cleaned_data['valorbeca'],
                        activavalorbeca=form.cleaned_data['activavalorbeca'],
                        porcentajebeca=form.cleaned_data['porcentajebeca'],
                        activaporcentajebeca=form.cleaned_data['activaporcentajebeca']
                    )
                    valor.save()
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editvalorperiodobeca':
            try:
                form = ValorPeriodoBecaFormalizarForm(request.POST)
                if form.is_valid():
                    valor = ValoresMinimosPeriodoBecaMatricula.objects.get(pk=int(request.POST['valor']))
                    valor.periodo = form.cleaned_data['periodo']
                    valor.valormatricula = int(form.cleaned_data['valormatricula'])
                    valor.activavalormatricula = form.cleaned_data['activavalormatricula']
                    valor.porcentajematricula = form.cleaned_data['porcentajematricula']
                    valor.activaporcentajematricula = form.cleaned_data['activaporcentajematricula']
                    valor.valorbeca = form.cleaned_data['valorbeca']
                    valor.activavalorbeca = form.cleaned_data['activavalorbeca']
                    valor.porcentajebeca = form.cleaned_data['porcentajebeca']
                    valor.activaporcentajebeca = form.cleaned_data['activaporcentajebeca']
                    valor.save()
                    log(u'Edito valores minimos para beca y formalizacion: %s' % valor, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        data['title'] = u'Precios del periodo'
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'addcostoconvenio':
                try:
                    data['title'] = u'Adicionar Costos Convenio Homologación'
                    data['form'] = PreciosConvenioHomologacionForm()
                    return render(request, "adm_pagosnivel/addcostoconvenio.html", data)
                except Exception as ex:
                    pass

            if action == 'addcostoparqueadero':
                try:
                    data['title'] = u'Adicionar Costos de servicio de parqueadero'
                    data['form'] = PreciosServicioParqueaderoForm()
                    return render(request, "adm_pagosnivel/addcostoservicioparqueadero.html", data)
                except Exception as ex:
                    pass

            if action == 'addcostoscursos':
                try:
                    data['title'] = u'Adicionar Costos de Cursos'
                    data['form'] = TipoCostoCursoForm()
                    return render(request, "adm_pagosnivel/addcostoscursos.html", data)
                except Exception as ex:
                    pass

            if action == 'editcostoscursos':
                try:
                    data['title'] = u'Adicionar Costos de Cursos'
                    data['tipo'] = tipo = TipoCostoCurso.objects.get(pk=request.GET['id'])
                    form = TipoCostoCursoForm(initial={'nombre': tipo.nombre,
                                                       'costodiferenciado': tipo.costodiferenciado,
                                                       'costolibre': tipo.costolibre,
                                                       'titulacion': tipo.titulacion,
                                                       'actualizacionconocimiento': tipo.actualizacionconocimiento,
                                                       'cursos': tipo.cursos,
                                                       'validapromedio': tipo.validapromedio}, )
                    form.edit(tipo)
                    data['form'] = form
                    return render(request, "adm_pagosnivel/editcostoscursos.html", data)
                except Exception as ex:
                    pass

            if action == 'editcostoconvenio':
                try:
                    data['title'] = u'Editar costo convenio homologación'
                    data['precioconvenio'] = precioconvenio = PreciosConvenioHomologacion.objects.get(pk=request.GET['id'])
                    form = PreciosConvenioHomologacionForm(initial={'nombre': precioconvenio.nombre,
                                                                    'costo': precioconvenio.costoconvenio})
                    data['form'] = form
                    return render(request, "adm_pagosnivel/editcostoconvenio.html", data)
                except Exception as ex:
                    pass

            if action == 'editcostoparqueadero':
                try:
                    data['title'] = u'Editar costo servicio parqueadero'
                    data['precioparqueo'] = precioparqueo = PreciosServicioParqueadero.objects.get(pk=request.GET['id'])
                    form = PreciosServicioParqueaderoForm(initial={'nombre': precioparqueo.nombre,
                                                                   'sede': precioparqueo.sede,
                                                                   'modalidad': precioparqueo.modalidad,
                                                                   'costosubtotal': precioparqueo.costosubtotal,
                                                                   'costototal': precioparqueo.costototal,
                                                                   'iva': precioparqueo.iva,
                                                                   'costoadicionalperdida': precioparqueo.costoadicionalperdida,
                                                                   'posgrado': precioparqueo.posgrado,
                                                                   'tiempo': precioparqueo.tiempo,
                                                                   'tipovehiculo': precioparqueo.tipovehiculo})
                    data['form'] = form
                    return render(request, "adm_pagosnivel/editcostoparqueadero.html", data)
                except Exception as ex:
                    pass

            if action == 'addespecie':
                try:
                    data['title'] = u'Adicionar Valor de Especie'
                    data['form'] = TipoEspecieForm()
                    return render(request, "adm_pagosnivel/addespecie.html", data)
                except Exception as ex:
                    pass

            if action == 'editespecie':
                try:
                    data['title'] = u'Editar Valor de Especie'
                    data['tipo'] = tipo = TipoEspecieValorada.objects.get(pk=request.GET['id'])
                    data['form'] = TipoEspecieForm(initial={'nombre': tipo.nombre,
                                                            'iva': tipo.iva,
                                                            'precio': tipo.precio})
                    return render(request, "adm_pagosnivel/editespecie.html", data)
                except Exception as ex:
                    pass

            if action == 'costosdiferenciadoscurso':
                try:
                    data['title'] = u'Costos Diferenciados'
                    data['tipo'] = tipo = TipoCostoCursoPeriodo.objects.get(pk=request.GET['id'])
                    data['costos'] = tipo.costodiferenciadocursoperiodo_set.all()
                    return render(request, "adm_pagosnivel/costosdiferenciados.html", data)
                except Exception as ex:
                    pass

            if action == 'tipocursos':
                try:
                    data['title'] = u'Tipos de cursos'
                    data['sedes'] = sedes = Sede.objects.all()
                    if 'sede' not in request.session:
                        request.session['sede'] = sede = sedes[0]
                    else:
                        sede = request.session['sede']
                    if 'sede' in request.GET:
                        request.session['sede'] = sede = Sede.objects.get(id=int(request.GET['sede']))
                    data['tiposcursos'] = TipoCostoCurso.objects.all()
                    data['sede'] = sede
                    return render(request, "adm_pagosnivel/tiposcursos.html", data)
                except Exception as ex:
                    pass

            if action == 'especies':
                try:
                    data['title'] = u'Especies valoradas'
                    data['tipoespecievaloradas'] = TipoEspecieValorada.objects.all()
                    return render(request, "adm_pagosnivel/especiesvaloradas.html", data)
                except Exception as ex:
                    pass

            if action == 'activartipo':
                try:
                    data['title'] = u'Activar tipo curso'
                    data['tipo'] = tipo = TipoCostoCursoPeriodo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_pagosnivel/activartipo.html", data)
                except Exception as ex:
                    pass

            if action == 'activarespecie':
                try:
                    data['title'] = u'Habilitar'
                    data['tipo'] = tipo = TipoEspecieValorada.objects.get(pk=request.GET['id'])
                    return render(request, "adm_pagosnivel/activarespecie.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivarespecie':
                try:
                    data['title'] = u'Deshabilitar'
                    data['tipo'] = tipo = TipoEspecieValorada.objects.get(pk=request.GET['id'])
                    return render(request, "adm_pagosnivel/desactivarespecie.html", data)
                except Exception as ex:
                    pass

            if action == 'delespecie':
                try:
                    data['title'] = u'Eliminar Especie'
                    data['tipo'] = tipo = TipoEspecieValorada.objects.get(pk=request.GET['id'])
                    return render(request, "adm_pagosnivel/delespecie.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivartipo':
                try:
                    data['title'] = u'Desactivar tipo curso'
                    data['tipo'] = tipo = TipoCostoCursoPeriodo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_pagosnivel/desactivartipo.html", data)
                except Exception as ex:
                    pass

            if action == 'clonarvalores':
                try:
                    data['title'] = u'Clonar valores desde el periodo:'
                    data['preciosperiodo'] = preciosperiodo = PreciosPeriodo.objects.filter(periodo=request.GET['id'])
                    form = ClonarPreciosPeriodoForm()
                    data['form'] = form
                    return render(request, "adm_pagosnivel/preciosperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'clonarvaloresparqueo':
                try:
                    data['title'] = u'Clonar valores desde el período:'
                    form = ClonarPreciosPeriodoForm()
                    data['form'] = form
                    return render(request, "adm_pagosnivel/preciosparqueo.html", data)
                except Exception as ex:
                    pass

            if action == 'addfechaproceso':
                try:
                    data['title'] = u'Adicionar Fecha'
                    data['modalidad'] = Modalidad.objects.get(pk=request.GET['mid'])
                    data['form'] = FechaSolicitudProrrogaSecretariaForm()
                    return render(request, "adm_pagosnivel/addfecha.html", data)
                except Exception as ex:
                    pass

            if action == 'editfechaproceso':
                try:
                    data['title'] = u'Editar Fecha'
                    data['fecha'] = fecha = FechasPeriodoSolicitudProrrogas.objects.get(pk=request.GET['id'])
                    data['form'] = FechaSolicitudProrrogaSecretariaForm(initial={'orden': fecha.orden,
                                                                                 'fechalimite': fecha.fechalimite})
                    return render(request, "adm_pagosnivel/editfechaproceso.html", data)
                except Exception as ex:
                    pass

            if action == 'subir':
                try:
                    data['title'] = u'Subir archivo'
                    data['proceso'] = ProcesoSolicitudProrrogasSecretaria.objects.get(pk=request.GET['id'])
                    data['modalidad'] = Modalidad.objects.get(pk=request.GET['mid'])
                    data['form'] = DocProcesoProrrogasSecretariaForm()
                    return render(request, "adm_pagosnivel/subir.html", data)
                except Exception as ex:
                    pass

            if action == 'descuentoformapago':
                try:
                    data['title'] = u'Descuentos forma de pago'
                    data['precio'] = precio = PreciosPeriodo.objects.get(pk=request.GET['id'])
                    data['descuentos'] = precio.descuentoformapago_set.all()
                    return render(request, "adm_pagosnivel/descuentoformapago.html", data)
                except Exception as ex:
                    pass

            if action == 'addformapago':
                try:
                    data['title'] = u'Adicionar Forma de Pago'
                    data['precio'] = PreciosPeriodo.objects.get(pk=request.GET['pid'])
                    data['form'] = FormaPagoDescuentoForm()
                    return render(request, "adm_pagosnivel/addformapago.html", data)
                except Exception as ex:
                    pass

            if action == 'delformapago':
                try:
                    data['title'] = u'Eliminar Froma de pago'
                    data['formapago'] = DescuentoFormaPago.objects.get(pk=request.GET['id'])
                    return render(request, "adm_pagosnivel/delformapago.html", data)
                except Exception as ex:
                    pass

            if action == 'addvalorperiodobeca':
                try:
                    data['title'] = u'Adicionar Valores abonados minimos para Formalizar y Postular a la Beca'
                    data['form'] = ValorPeriodoBecaFormalizarForm()
                    return render(request, "adm_pagosnivel/addvalorperiodobeca.html", data)
                except Exception as ex:
                    pass

            if action == 'editvalorperiodobeca':
                try:
                    data['title'] = u'Adicionar Valores abonados minimos para Formalizar y Postular a la Beca'
                    data['valor'] = valor = ValoresMinimosPeriodoBecaMatricula.objects.get(pk=request.GET['valor'])
                    data['form'] = ValorPeriodoBecaFormalizarForm(initial={'periodo': valor.periodo,
                                                                           'valormatricula': valor.valormatricula,
                                                                           'activavalormatricula': valor.activavalormatricula,
                                                                           'porcentajematricula': valor.porcentajematricula,
                                                                           'activaporcentajematricula': valor.activaporcentajematricula,
                                                                           'valorbeca': valor.valorbeca,
                                                                           'activavalorbeca': valor.activavalorbeca,
                                                                           'porcentajebeca': valor.porcentajebeca,
                                                                           'activaporcentajebeca': valor.activaporcentajebeca})
                    return render(request, "adm_pagosnivel/editvalorperiodobeca.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Costos generales'
                if 'seccion' in request.GET:
                    request.session['adm_pagosnivel_seccion'] = seccion = int(request.GET['seccion'])
                else:
                    if 'adm_pagosnivel_seccion' not in request.session:
                        request.session['adm_pagosnivel_seccion'] = 0
                    seccion = request.session['adm_pagosnivel_seccion']
                data['seccion'] = seccion
                if seccion == 0:
                    data['sedes'] = sedes = Sede.objects.all()
                    if 'sede' not in request.session:
                        request.session['sede'] = sede = sedes[0]
                    else:
                        sede = request.session['sede']
                    if 'sede' in request.GET:
                        request.session['sede'] = sede = Sede.objects.get(id=int(request.GET['sede']))
                    data['tiposcursos'] = TipoCostoCurso.objects.all()
                    data['sede'] = sede
                    return render(request, "adm_pagosnivel/0.html", data)
                if seccion == 1:
                    data['coordinacion'] = coordinacion = request.session['coordinacionseleccionada']
                    data['tipoespecievaloradas'] = TipoEspecieValorada.objects.all()
                    return render(request, "adm_pagosnivel/1.html", data)
                if seccion == 2:
                    data['coordinacion'] = coordinacion = request.session['coordinacionseleccionada']
                    carreras = Carrera.objects.filter(coordinacion=request.session['coordinacionseleccionada']).distinct()
                    modalidades = Modalidad.objects.all()
                    mallas = Malla.objects.filter(activo=True)
                    data['nivelescreados'] = periodo.nivel_set.filter(nivellibrecoordinacion__coordinacion=coordinacion)
                    if 'adm_pagosnivel_carrera' not in request.session:
                        request.session['adm_pagosnivel_carrera'] = adm_pagosnivel_carrera = carreras[0].id
                    else:
                        adm_pagosnivel_carrera = request.session['adm_pagosnivel_carrera']
                    if adm_pagosnivel_carrera not in carreras.values_list('id', flat=True):
                        adm_pagosnivel_carrera = carreras[0].id
                    if 'idc' in request.GET:
                        adm_pagosnivel_carrera = int(request.GET['idc'])
                    data['adm_pagosnivel_carrera'] = request.session['adm_pagosnivel_carrera'] = adm_pagosnivel_carrera
                    mallas = mallas.filter(carrera__id=adm_pagosnivel_carrera)

                    if 'adm_pagosnivel_modalidad' not in request.session:
                        request.session['adm_pagosnivel_modalidad'] = adm_pagosnivel_modalidad = modalidades[0].id
                    else:
                        adm_pagosnivel_modalidad = request.session['adm_pagosnivel_modalidad']
                    if adm_pagosnivel_modalidad not in modalidades.values_list('id', flat=True):
                        adm_pagosnivel_modalidad = modalidades[0].id
                    if 'idm' in request.GET:
                        adm_pagosnivel_modalidad = int(request.GET['idm'])
                    data['adm_pagosnivel_modalidad'] = request.session['adm_pagosnivel_modalidad'] = adm_pagosnivel_modalidad
                    mallas = mallas.filter(modalidad__id=adm_pagosnivel_modalidad)
                    if mallas:
                        if 'adm_pagosnivel_malla' not in request.session:
                            request.session['adm_pagosnivel_malla'] = adm_pagosnivel_malla = mallas[0].id
                        else:
                            adm_pagosnivel_malla = request.session['adm_pagosnivel_malla']
                        if adm_pagosnivel_malla not in mallas.values_list('id', flat=True):
                            adm_pagosnivel_malla = mallas[0].id
                        if 'idma' in request.GET:
                            adm_pagosnivel_malla = int(request.GET['idma'])
                        data['adm_pagosnivel_malla'] = request.session['adm_pagosnivel_malla'] = adm_pagosnivel_malla
                        mallas = mallas.all()
                    data['mallas'] = mallas
                    data['carreras'] = carreras
                    data['modalidades'] = modalidades
                    data['periodoseleccionado'] = request.session['periodo']
                    adm_pagosnivel_malla = data.get('adm_pagosnivel_malla', None)
                    data['malla'] = Malla.objects.filter(pk=adm_pagosnivel_malla).first()
                    return render(request, "adm_pagosnivel/2.html", data)
                if seccion == 3:
                    data['modalidades'] = modalidades = Modalidad.objects.all()
                    if 'modalidad' not in request.session:
                        request.session['modalidad'] = modalidad = modalidades[0]
                    else:
                        modalidad = request.session['modalidad']
                    if 'modalidad' in request.GET:
                        request.session['modalidad'] = modalidad = Modalidad.objects.get(id=int(request.GET['modalidad']))
                    data['tiposcursos'] = TipoCostoCurso.objects.all()
                    if ProcesoSolicitudProrrogasSecretaria.objects.filter(periodo=periodo, modalidad=modalidad).exists():
                        data['procesos'] = proceso = ProcesoSolicitudProrrogasSecretaria.objects.filter(periodo=periodo, modalidad=modalidad)[0]
                        data['fechasprocesos'] = FechasPeriodoSolicitudProrrogas.objects.filter(proceso=proceso)
                    else:
                        data['procesos'] = ""
                        data['fechasprocesos'] = ""
                    data['modalidad'] = modalidad
                    return render(request, "adm_pagosnivel/3.html", data)
                if seccion == 4:
                    data['costosconvenio'] = PreciosConvenioHomologacion.objects.filter(periodo=periodo)
                    data['costosparqueadero'] = PreciosServicioParqueadero.objects.filter(periodo=periodo)
                    return render(request, "adm_pagosnivel/4.html", data)
                if seccion == 5:
                    data['valores'] = ValoresMinimosPeriodoBecaMatricula.objects.all()
                    return render(request, "adm_pagosnivel/5.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
