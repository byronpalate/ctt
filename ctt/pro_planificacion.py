# coding=utf-8
import json
import random
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models.aggregates import Max, Sum
from django.http import HttpResponseRedirect, HttpResponse
from django.http.response import JsonResponse, HttpResponseServerError
from django.shortcuts import render
from django.db import transaction
from django.template import RequestContext, Context
from django.template.loader import get_template
from django.db.models import Q

from decorators import secure_module, last_access
from settings import TIPO_DOCENTE_TEORIA
from ctt.commonviews import adduserdata, obtener_reporte
from ctt.forms import PlanificacionForm, ImportarPlanificacionForm, ImportarTallerForm, \
    TallerPlanificacionForm, ContenidoTallerForm, RubricaTallerPlanificacionForm, \
    ArchivoPlanificacionForm, BibliografiaPlanificacionForm, \
    TallerPlanificacionNuevaForm, ClaseTallerNuevaForm, IndicadoresRubricaForm, ObservacionesPlanoficacionForm

from ctt.funciones import log, generar_nombre, url_back, bad_json, ok_json, convertir_fecha, generar_color_hexadecimal
from ctt.models import Materia, PlanificacionMateria, TallerPlanificacionMateria, \
    ContenidosTallerPlanificacionMateria, null_to_numeric, ActividadesAprendizajeCondocenciaAsistida, \
    ActividadesTrabajoAutonomas, ActividadesAprendizajePractico, ActividadesAprendizajeColaborativas, \
    ClasesTallerPlanificacionMateria, LeccionGrupo, BibliografiaComplementariaPlanificacion, \
    BibliografiaBasicaPlanificacion, GuiasPracticasMateria, \
    RubricaResultadoAprendizaje, IndicadorRubrica, \
    Asignatura, NivelMalla, Persona, Modalidad,  Profesor,  null_to_text

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
    profesor = perfilprincipal.profesor
    periodo = request.session['periodo']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'listatalleres':
                try:
                    materia = Materia.objects.get(pk=request.POST['id'])
                    talleres = TallerPlanificacionMateria.objects.filter(planificacionmateria__materia__id=materia.id)
                    lista = []
                    for taller in talleres:
                        lista.append([taller.id, taller.nombretaller])
                    return ok_json({'lista': lista})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'add':
                try:
                    materia = Materia.objects.get(pk=request.POST['id'])
                    modelo = None
                    if materia.asignaturamalla:
                        modelo = materia.asignaturamalla.malla.modelonuevo
                    else:
                        modelo = materia.modulomalla.malla.modelonuevo
                    if modelo == 2:
                        form = PlanificacionNuevaForm(request.POST, request.FILES)
                    else:
                        form = PlanificacionForm(request.POST, request.FILES)
                    if form.is_valid():
                        horas = 0
                        creditos = 0
                        malla = None
                        if materia.asignaturamalla:
                            horas = materia.asignaturamalla.horas
                            creditos = materia.asignaturamalla.creditos
                        else:
                            horas = materia.modulomalla.horas
                            creditos = materia.modulomalla.creditos
                        planificacionmateria = PlanificacionMateria(materia=materia,
                                                                    horariotutorias=form.cleaned_data[
                                                                        'horariotutorias'] if modelo == 0 else 0,
                                                                    horariopracticas=form.cleaned_data[
                                                                        'horariopracticas'] if modelo == 0 else 0,
                                                                    horas=horas,
                                                                    creditos=creditos,
                                                                    horasasistidasporeldocente=form.cleaned_data[
                                                                        'horasasistidasporeldocente'],
                                                                    horascolaborativas=form.cleaned_data[
                                                                        'horascolaborativas'] if modelo == 0 else 0,
                                                                    horasautonomas=form.cleaned_data['horasautonomas'],
                                                                    horaspracticas=form.cleaned_data['horaspracticas'],
                                                                    competenciagenericainstitucion=form.cleaned_data[
                                                                        'competenciagenericainstitucion'],
                                                                    competenciaespecificaperfildeegreso=
                                                                    form.cleaned_data[
                                                                        'competenciaespecificaperfildeegreso'],
                                                                    competenciaespecificaproyectoformativo=
                                                                    form.cleaned_data[
                                                                        'competenciaespecificaproyectoformativo'],
                                                                    contribucioncarrera=form.cleaned_data[
                                                                        'contribucioncarrera'],
                                                                    problemaabordadometodosdeensenanza=
                                                                    form.cleaned_data[
                                                                        'problemaabordadometodosdeensenanza'],
                                                                    proyectofinal=form.cleaned_data['proyectofinal'],
                                                                    transversalidad=form.cleaned_data[
                                                                        'transversalidad'] if modelo != 0 else "")
                        planificacionmateria.save(request)
                        planificacionmateria.mi_rubrica()
                        log(u'Adiciono planificacion del Docente: %s' % planificacionmateria, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editbibliografiacomplementariasolicitada':
                try:
                    bibliografia = BibliografiaComplementariaSolicitada.objects.get(pk=request.POST['id'])
                    planificacionmateria = bibliografia.planificacionmateria
                    form = BibliografiaComplementariaSolicitadaForm(request.POST)
                    if form.is_valid():
                        bibliografia.digital = form.cleaned_data['digital']
                        bibliografia.titulo = form.cleaned_data['titulo']
                        bibliografia.autor = form.cleaned_data['autor']
                        bibliografia.editorial = form.cleaned_data['editorial']
                        bibliografia.anno = form.cleaned_data['anno']
                        bibliografia.save(request)
                        planificacionmateria.verificada = False
                        planificacionmateria.save(request)
                        log(u'Modifico bibliografia %s a planificacion %s' % (bibliografia, planificacionmateria),
                            request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addtaller':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    modelo = None
                    if planificacionmateria.materia.asignaturamalla:
                        modelo = planificacionmateria.materia.asignaturamalla.malla.modelonuevo
                    else:
                        modelo = planificacionmateria.materia.modulomalla.malla.modelonuevo
                    if modelo == 2:
                        form = TallerPlanificacionNuevaForm(request.POST)
                    else:
                        form = TallerPlanificacionForm(request.POST)
                    if form.is_valid():
                        taller = TallerPlanificacionMateria(planificacionmateria=planificacionmateria,
                                                            nombretaller=form.cleaned_data['nombretaller'],
                                                            resultadoaprendizaje=form.cleaned_data[
                                                                'resultadoaprendizaje'],
                                                            recursosutilizados=form.cleaned_data['recursosutilizados'],
                                                            dimensionprocedimental=form.cleaned_data[
                                                                'dimensionprocedimental'] if modelo == 0 else "",
                                                            productoesperado=form.cleaned_data['productoesperado'])
                        taller.save(request)
                        taller.mi_rubrica()
                        log(u'Adiciono taller de planificacion del Docente: %s' % taller, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addbibliografiabasica':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    form = BibliografiaPlanificacionForm(request.POST)
                    if form.is_valid():
                        bibliografia = BibliografiaBasicaPlanificacion(planificacionmateria=planificacionmateria,
                                                                       codigobibliotecabibliografiabasica=form.cleaned_data['codigo'],
                                                                       digital=form.cleaned_data['digital'],
                                                                       weburl=form.cleaned_data['url'],
                                                                       bibliografiabasica=form.cleaned_data['titulo'],
                                                                       autor=form.cleaned_data['autor'],
                                                                       editorial=form.cleaned_data['editorial'],
                                                                       anno=form.cleaned_data['anno'],
                                                                        fuente=form.cleaned_data['fuente'])
                        bibliografia.save(request)
                        planificacionmateria.verificadabiblioteca = False
                        planificacionmateria.save(request)
                        log(u'Adiciono bibliografia %s a planificacion %s' % (bibliografia, planificacionmateria),
                            request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addsolicitarbibliografiabasica':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    form = SolicitarBibliografiaPlanificacionForm(request.POST)
                    if form.is_valid():
                        bibliografia = BibliografiaBasicaSolicitada(planificacionmateria=planificacionmateria,
                                                                    digital=form.cleaned_data['digital'],
                                                                    titulo=form.cleaned_data['titulo'],
                                                                    autor=form.cleaned_data['autor'],
                                                                    editorial=form.cleaned_data['editorial'],
                                                                    anno=form.cleaned_data['anno'])
                        bibliografia.save(request)
                        planificacionmateria.verificada = False
                        planificacionmateria.save(request)
                        log(u'Solicito bibliografia %s a planificacion %s' % (bibliografia, planificacionmateria),
                            request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addsolicitarbibliografiacomplementaria':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    form = BibliografiaComplementariaSolicitadaForm(request.POST)
                    if form.is_valid():
                        bibliografia = BibliografiaComplementariaSolicitada(planificacionmateria=planificacionmateria,
                                                                            digital=form.cleaned_data['digital'],
                                                                            titulo=form.cleaned_data['titulo'],
                                                                            autor=form.cleaned_data['autor'],
                                                                            editorial=form.cleaned_data['editorial'],
                                                                            anno=form.cleaned_data['anno'])
                        bibliografia.save(request)
                        planificacionmateria.verificada = False
                        planificacionmateria.save(request)
                        log(u'Solicito bibliografia %s a planificacion %s' % (bibliografia, planificacionmateria),
                            request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editbibliografiabasica':
                try:
                    bibliografia = BibliografiaBasicaPlanificacion.objects.get(pk=request.POST['id'])
                    planificacionmateria = bibliografia.planificacionmateria
                    form = BibliografiaPlanificacionForm(request.POST)
                    if form.is_valid():
                        bibliografia.codigobibliotecabibliografiabasica = form.cleaned_data['codigo']
                        bibliografia.digital = form.cleaned_data['digital']
                        bibliografia.weburl = form.cleaned_data['url']
                        bibliografia.bibliografiabasica = form.cleaned_data['titulo']
                        bibliografia.autor = form.cleaned_data['autor']
                        bibliografia.editorial = form.cleaned_data['editorial']
                        bibliografia.anno = form.cleaned_data['anno']
                        bibliografia.fuente = form.cleaned_data['fuente']
                        bibliografia.save(request)
                        planificacionmateria.verificadabiblioteca = False
                        planificacionmateria.save(request)
                        log(u'Modifico bibliografia %s a planificacion %s' % (bibliografia, planificacionmateria),
                            request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editbibliografiabasicasolicitada':
                try:
                    bibliografia = BibliografiaBasicaSolicitada.objects.get(pk=request.POST['id'])
                    planificacionmateria = bibliografia.planificacionmateria
                    form = SolicitarBibliografiaPlanificacionForm(request.POST)
                    if form.is_valid():
                        bibliografia.digital = form.cleaned_data['digital']
                        bibliografia.titulo = form.cleaned_data['titulo']
                        bibliografia.autor = form.cleaned_data['autor']
                        bibliografia.editorial = form.cleaned_data['editorial']
                        bibliografia.anno = form.cleaned_data['anno']
                        bibliografia.save(request)
                        planificacionmateria.verificada = False
                        planificacionmateria.save(request)
                        log(u'Modifico bibliografia %s a planificacion %s' % (bibliografia, planificacionmateria),
                            request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editbibliografiacomplementaria':
                try:
                    bibliografia = BibliografiaComplementariaPlanificacion.objects.get(pk=request.POST['id'])
                    planificacionmateria = bibliografia.planificacionmateria
                    form = BibliografiaPlanificacionForm(request.POST)
                    if form.is_valid():
                        bibliografia.codigobibliotecabibliografiacomplementaria = form.cleaned_data['codigo']
                        bibliografia.digital = form.cleaned_data['digital']
                        bibliografia.weburl = form.cleaned_data['url']
                        bibliografia.bibliografiacomplementaria = form.cleaned_data['titulo']
                        bibliografia.autor = form.cleaned_data['autor']
                        bibliografia.editorial = form.cleaned_data['editorial']
                        bibliografia.anno = form.cleaned_data['anno']
                        bibliografia.fuente = form.cleaned_data['fuente']
                        bibliografia.save(request)
                        planificacionmateria.verificadabiblioteca = False
                        planificacionmateria.save(request)
                        log(u'Modifico bibliografia %s a planificacion %s' % (bibliografia, planificacionmateria),
                            request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addbibliografiacomplementaria':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    form = BibliografiaPlanificacionForm(request.POST)
                    if form.is_valid():
                        bibliografia = BibliografiaComplementariaPlanificacion(
                            planificacionmateria=planificacionmateria,
                            codigobibliotecabibliografiacomplementaria=form.cleaned_data['codigo'],
                            digital=form.cleaned_data['digital'],
                            weburl=form.cleaned_data['url'],
                            bibliografiacomplementaria=form.cleaned_data['titulo'],
                            autor=form.cleaned_data['autor'],
                            editorial=form.cleaned_data['editorial'],
                            anno=form.cleaned_data['anno'],
                            fuente=form.cleaned_data['fuente'])
                        bibliografia.save(request)
                        planificacionmateria.verificadabiblioteca = False
                        planificacionmateria.save(request)
                        log(u'Adiciono bibliografia %s a planificacion %s' % (bibliografia, planificacionmateria),
                            request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addguia':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    form = GuiaPracticaPlanificacionForm(request.POST)
                    if form.is_valid():
                        if form.cleaned_data['horas'] > planificacionmateria.disponile_gias_practica():
                            return bad_json(mensaje=u'Sobrepasa el total de horas de practicas.')
                        guia = GuiasPracticasMateria(planificacionmateria=planificacionmateria,
                                                     titulo=form.cleaned_data['titulo'],
                                                     taller=form.cleaned_data['taller'],
                                                     tipo=form.cleaned_data['tipo'],
                                                     recursos=form.cleaned_data['recursos'],
                                                     equipos=form.cleaned_data['equipos'],
                                                     materiales=form.cleaned_data['materialessoftware'],
                                                     reactivos=form.cleaned_data['reactivos'],
                                                     destino=form.cleaned_data['destino'],
                                                     empresa=form.cleaned_data['empresa'],
                                                     contactoempresa=form.cleaned_data['contactoempresa'],
                                                     materialesbibliograficos=form.cleaned_data[
                                                         'materialesbibliograficos'],
                                                     instrumentos=form.cleaned_data['instrumentos'],
                                                     herramientas=form.cleaned_data['herramientas'],
                                                     objetivo=form.cleaned_data['objetivo'],
                                                     fundamentoteorico=form.cleaned_data['fundamentoteorico'],
                                                     procedimiento=form.cleaned_data['procedimiento'],
                                                     horas=form.cleaned_data['horas'],
                                                     resultados=form.cleaned_data['resultados'],
                                                     inicio=form.cleaned_data['inicio'],
                                                     fin=form.cleaned_data['fin']
                                                     )
                        guia.save(request)
                        guia.taller.verificada = False
                        guia.taller.save(request)
                        log(u'Adiciono guia practica de planificacion del Docente: %s' % guia, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editguia':
                try:
                    guia = GuiasPracticasMateria.objects.get(pk=request.POST['id'])
                    form = GuiaPracticaPlanificacionForm(request.POST)
                    if form.is_valid():
                        if form.cleaned_data['horas'] > null_to_numeric(
                                guia.planificacionmateria.disponile_gias_practica() + guia.horas, 1):
                            return bad_json(mensaje=u'Sobrepasa el total de horas de practicas.')
                        guia.titulo = form.cleaned_data['titulo']
                        guia.tipo = form.cleaned_data['tipo']
                        guia.taller = form.cleaned_data['taller']
                        guia.recursos = form.cleaned_data['recursos']
                        guia.equipos = form.cleaned_data['equipos']
                        guia.materiales = form.cleaned_data['materialessoftware']
                        guia.reactivos = form.cleaned_data['reactivos']
                        guia.destino = form.cleaned_data['destino']
                        guia.empresa = form.cleaned_data['empresa']
                        guia.contactoempresa = form.cleaned_data['contactoempresa']
                        guia.materialesbibliograficos = form.cleaned_data['materialesbibliograficos']
                        guia.instrumentos = form.cleaned_data['instrumentos']
                        guia.herramientas = form.cleaned_data['herramientas']
                        guia.objetivo = form.cleaned_data['objetivo']
                        guia.procedimiento = form.cleaned_data['procedimiento']
                        guia.fundamentoteorico = form.cleaned_data['fundamentoteorico']
                        guia.horas = form.cleaned_data['horas']
                        guia.resultados = form.cleaned_data['resultados']
                        guia.inicio = form.cleaned_data['inicio']
                        guia.fin = form.cleaned_data['fin']
                        guia.save(request)
                        guia.taller.verificada = False
                        guia.taller.save(request)
                        log(u'Modifico guia practica de planificacion del Docente: %s' % guia, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delguia':
                try:
                    guia = GuiasPracticasMateria.objects.get(pk=request.POST['id'])
                    log(u'Elimino guia: %s' % guia, request, "del")
                    guia.taller.verificada = False
                    guia.taller.save(request)
                    guia.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)

            if action == 'addguiacienciasbasicasing':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    form = GuiaNuevaPracticaPlanificacionIngForm(request.POST)
                    form.addlab()
                    form.listartipo()
                    if form.is_valid():

                        if GuiasNuevaPracticasMateria.objects.filter(planificacionmateria=planificacionmateria,
                                                                     noguia=form.cleaned_data['noguia']).exists():
                            return bad_json(mensaje=u'Ya existe ese numero de practica.')
                        guia = GuiasNuevaPracticasMateria(planificacionmateria=planificacionmateria,
                                                          titulo=form.cleaned_data['titulo'],
                                                          tipopractica=form.cleaned_data['tipopractica'],
                                                          # inicio=form.cleaned_data['inicio'],
                                                          # fin=form.cleaned_data['fin'],
                                                          taller=form.cleaned_data['taller'],
                                                          noguia=form.cleaned_data['noguia'],
                                                          horas=form.cleaned_data['horas'],
                                                          objetivo=form.cleaned_data['objetivo'],
                                                          fundamento=form.cleaned_data['fundamento'],
                                                          procedimiento=form.cleaned_data['procedimiento'],
                                                          resultados=form.cleaned_data['resultados'])
                        guia.save(request)
                        fechas = request.POST.getlist('fechas[]')
                        for f in fechas:
                            if f:  # Evita vacíos
                                fecha_dt = datetime.strptime(f, '%d-%m-%Y').date()  # según tu formato
                                FechasGuiasNuevaPracticasMateria.objects.create(guia=guia,fecha=fecha_dt)

                        if form.cleaned_data['tipopractica'] in ['1', '5']:
                            guia.lugar_1.set(form.cleaned_data['laboratorio'])
                            for eq in form.cleaned_data['equiposlabo']:
                                eqp = EquipoPracticaGuia(guia=guia,
                                                         equipo=eq)
                                eqp.save()
                            guia.reactivoslista.set(form.cleaned_data['reactivoslista'])
                            guia.herramientaslista.set(form.cleaned_data['herramientaslista'])
                            guia.color = generar_color_hexadecimal()
                            guia.otro = form.cleaned_data['otros']
                            guia.save()

                        if form.cleaned_data['tipopractica'] in ['5']:
                            guia.sin_lab = form.cleaned_data['sin_lab']
                            guia.save()

                        if form.cleaned_data['tipopractica'] == '4':
                            guia.nombreestablecimiento = form.cleaned_data['empresa']
                            guia.personacontacto = form.cleaned_data['personacontacto']
                            guia.save()

                        if 'archivo' in request.FILES:
                            archivo = request.FILES['archivo']
                            archivo._name = generar_nombre("archivo_", archivo._name)
                            guia.archivo = archivo
                            guia.save(request)
                        log(u'Adiciono guia practica de planificacion del Docente de Ingenieria: %s' % guia, request, "add")
                        return ok_json()
                    else:
                        print(form.errors)
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editguiacienciasbasicasing':
                try:
                    guia = GuiasNuevaPracticasMateria.objects.get(pk=request.POST['id'])
                    form = GuiaNuevaPracticaPlanificacionIngForm(request.POST)
                    form.addlab()
                    form.listartipo()
                    if form.is_valid():
                        guia.titulo = form.cleaned_data['titulo']
                        # guia.inicio = form.cleaned_data['inicio']
                        # guia.fin = form.cleaned_data['fin']
                        guia.tipopractica = form.cleaned_data['tipopractica']
                        guia.taller = form.cleaned_data['taller']
                        guia.noguia = form.cleaned_data['noguia']
                        guia.horas = form.cleaned_data['horas']
                        guia.objetivo = form.cleaned_data['objetivo']
                        guia.fundamento = form.cleaned_data['fundamento']
                        guia.procedimiento = form.cleaned_data['procedimiento']
                        guia.resultados = form.cleaned_data['resultados']
                        guia.save(request)

                        if form.cleaned_data['tipopractica'] in ['1', '5']:
                            guia.lugar_1.set(form.cleaned_data['laboratorio'])
                            EquipoPracticaGuia.objects.filter(guia=guia).delete()
                            for eq in form.cleaned_data['equiposlabo']:
                                eqp = EquipoPracticaGuia(guia=guia,
                                                         equipo=eq)
                                eqp.save()
                            guia.reactivoslista.set(form.cleaned_data['reactivoslista'])
                            guia.herramientaslista.set(form.cleaned_data['herramientaslista'])
                            guia.color = generar_color_hexadecimal()
                            guia.otro = form.cleaned_data['otros']
                            guia.save()

                        if form.cleaned_data['tipopractica'] == '5':
                            if form.cleaned_data['sin_lab']:
                                guia.lugar_1.clear()
                            guia.sin_lab = form.cleaned_data['sin_lab']
                            guia.save()

                        if form.cleaned_data['tipopractica'] == '4':
                            guia.nombreestablecimiento = form.cleaned_data['empresa']
                            guia.personacontacto = form.cleaned_data['personacontacto']
                            guia.save()

                        if 'archivo' in request.FILES:
                            archivo = request.FILES['archivo']
                            archivo._name = generar_nombre("archivo_", archivo._name)
                            guia.archivo = archivo
                            guia.save(request)
                        log(u'Modifico nueva guia practica de planificacion del Docente: %s' % guia, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6,form=form)
                except Exception as ex:
                    print(ex)
                    transaction.set_rollback(True)
                    return bad_json(error=1,ex=ex)

            if action == 'addguiacienciasbasicas':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    form = GuiaNuevaPracticaPlanificacionForm(request.POST)
                    form.addlab()
                    if form.is_valid():
                        if GuiasNuevaPracticasMateria.objects.filter(planificacionmateria=planificacionmateria,
                                                                     noguia=form.cleaned_data['noguia']).exists():
                            return bad_json(mensaje=u'Ya existe ese numero de practica.')
                        guia = GuiasNuevaPracticasMateria(planificacionmateria=planificacionmateria,
                                                          titulo=form.cleaned_data['titulo'],
                                                          tipopractica=form.cleaned_data['tipopractica'],
                                                          # inicio=form.cleaned_data['inicio'],
                                                          # fin=form.cleaned_data['fin'],
                                                          taller=form.cleaned_data['taller'],
                                                          noguia=form.cleaned_data['noguia'],
                                                          horas=form.cleaned_data['horas'],
                                                          recursos=form.cleaned_data['recursos'],
                                                          equipos=form.cleaned_data['equipos'],
                                                          materiales=form.cleaned_data['materiales'],
                                                          reactivos=form.cleaned_data['reactivos'],
                                                          objetivo=form.cleaned_data['objetivo'],
                                                          fundamento=form.cleaned_data['fundamento'],
                                                          procedimiento=form.cleaned_data['procedimiento'],
                                                          resultados=form.cleaned_data['resultados'],
                                                          referencias=form.cleaned_data['referencias'],
                                                          aprendizaje=form.cleaned_data['aprendizaje'],
                                                          disposiciones=form.cleaned_data['disposiciones'],
                                                          # grupo=form.cleaned_data['grupo'],
                                                          # nivelbioseguridad1=form.cleaned_data['nivelbioseguridad1'],
                                                          # practicas=form.cleaned_data['practicas'],
                                                          # actividades=form.cleaned_data['actividades'],
                                                          emergencia=form.cleaned_data['emergencia'],
                                                          refuerzo=form.cleaned_data['refuerzo'],
                                                          # tipo=form.cleaned_data['tipo'],
                                                          observaciones=form.cleaned_data['observaciones'])
                        guia.save(request)
                        fechas = request.POST.getlist('fechas[]')
                        for f in fechas:
                            if f:  # Evita vacíos
                                fecha_dt = datetime.strptime(f, '%d-%m-%Y').date()  # según tu formato
                                FechasGuiasNuevaPracticasMateria.objects.create(guia=guia, fecha=fecha_dt)
                        if form.cleaned_data['tipopractica'] == '1':
                            guia.lugar=form.cleaned_data['laboratorio']
                            guia.save()
                            for eq in form.cleaned_data['equiposlabo']:
                                eqp = EquipoPracticaGuia(guia=guia,
                                                         equipo=eq)
                                eqp.save()
                            guia.reactivoslista.set(form.cleaned_data['reactivoslista'])
                            guia.materialeslista.set(form.cleaned_data['materialeslista'])
                            guia.suministroslista.set(form.cleaned_data['suministroslista'])
                            guia.medicamentoslista.set(form.cleaned_data['medicamentoslista'])
                            guia.color = generar_color_hexadecimal()
                            guia.save()

                        if form.cleaned_data['tipopractica'] == '2':
                            guia.enfermeria = form.cleaned_data['enfermeria']
                            guia.medicina = form.cleaned_data['medicina']
                            guia.odontologia = form.cleaned_data['odontologia']
                            guia.establecimiento = form.cleaned_data['tipoestablecimiento']
                            guia.nombreestablecimiento = form.cleaned_data['establecimiento']
                            guia.internadoexternado = form.cleaned_data['internadoexternado']
                            guia.save()

                        if 'archivo' in request.FILES:
                            archivo = request.FILES['archivo']
                            archivo._name = generar_nombre("archivo_", archivo._name)
                            guia.archivo = archivo
                            guia.save(request)
                        log(u'Adiciono guia practica de planificacion del Docente: %s' % guia, request, "add")
                        return ok_json()
                    else:
                        print(form.errors)
                        return bad_json(error=6,form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editguiacienciasbasicas':
                try:
                    guia = GuiasNuevaPracticasMateria.objects.get(pk=request.POST['id'])
                    form = GuiaNuevaPracticaPlanificacionForm(request.POST)
                    form.addlab()
                    if form.is_valid():
                        guia.titulo = form.cleaned_data['titulo']
                        # guia.inicio = form.cleaned_data['inicio']
                        guia.tipopractica = form.cleaned_data['tipopractica']
                        # guia.fin = form.cleaned_data['fin']
                        guia.taller = form.cleaned_data['taller']
                        guia.noguia = form.cleaned_data['noguia']
                        guia.horas = form.cleaned_data['horas']
                        guia.recursos = form.cleaned_data['recursos']
                        guia.equipos = form.cleaned_data['equipos']
                        guia.materiales = form.cleaned_data['materiales']
                        guia.reactivos = form.cleaned_data['reactivos']
                        guia.objetivo = form.cleaned_data['objetivo']
                        guia.fundamento = form.cleaned_data['fundamento']
                        guia.procedimiento = form.cleaned_data['procedimiento']
                        guia.resultados = form.cleaned_data['resultados']
                        guia.referencias = form.cleaned_data['referencias']
                        guia.aprendizaje = form.cleaned_data['aprendizaje']
                        guia.disposiciones = form.cleaned_data['disposiciones']
                        # guia.grupo = form.cleaned_data['grupo']
                        # guia.nivelbioseguridad1 = form.cleaned_data['nivelbioseguridad1']
                        # guia.practicas = form.cleaned_data['practicas']
                        # guia.actividades = form.cleaned_data['actividades']
                        guia.emergencia = form.cleaned_data['emergencia']
                        guia.refuerzo = form.cleaned_data['refuerzo']
                        guia.observaciones = form.cleaned_data['observaciones']
                        guia.enfermeria = form.cleaned_data['enfermeria']
                        guia.medicina = form.cleaned_data['medicina']
                        guia.odontologia = form.cleaned_data['odontologia']
                        guia.establecimiento = form.cleaned_data['tipoestablecimiento']
                        guia.nombreestablecimiento = form.cleaned_data['establecimiento']
                        guia.internadoexternado = form.cleaned_data['internadoexternado']
                        guia.save(request)

                        if form.cleaned_data['tipopractica'] == '1':
                            guia.lugar = form.cleaned_data['laboratorio']
                            guia.save()

                            EquipoPracticaGuia.objects.filter(guia=guia).delete()
                            for eq in form.cleaned_data['equiposlabo']:
                                eqp = EquipoPracticaGuia(guia=guia,
                                                         equipo=eq)
                                eqp.save()
                            guia.reactivoslista.set(form.cleaned_data['reactivoslista'])
                            guia.materialeslista.set(form.cleaned_data['materialeslista'])
                            guia.suministroslista.set(form.cleaned_data['suministroslista'])
                            guia.medicamentoslista.set(form.cleaned_data['medicamentoslista'])
                            guia.color = generar_color_hexadecimal()
                            guia.save()

                        if 'archivo' in request.FILES:
                            archivo = request.FILES['archivo']
                            archivo._name = generar_nombre("archivo_", archivo._name)
                            guia.archivo = archivo
                            guia.save(request)
                        log(u'Modifico nueva guia practica de planificacion del Docente: %s' % guia, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    print(ex)
                    transaction.set_rollback(True)
                    return bad_json(error=1,ex=ex)

            if action == 'delguiacienciasbasicas':
                try:
                    guia = GuiasNuevaPracticasMateria.objects.get(pk=request.POST['id'])
                    log(u'Elimino nueva guia: %s' % guia, request, "del")
                    guia.delete()
                    return ok_json()
                except Exception as ex:
                    print(ex)
                    transaction.set_rollback(True)

            if action == 'addguiacienciasbasicasenfermeria':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    form = GuiaNuevaPracticaEnfermeriaPlanificacionForm(request.POST)
                    if form.is_valid():
                        if GuiasNuevaPracticasEnfermeriaMateria.objects.filter(
                                planificacionmateria=planificacionmateria, noguia=form.cleaned_data['noguia']).exists():
                            return bad_json(mensaje=u'Ya existe ese numero de practica.')
                        guia = GuiasNuevaPracticasEnfermeriaMateria(planificacionmateria=planificacionmateria,
                                                                    titulo=form.cleaned_data['titulo'],
                                                                    inicio=form.cleaned_data['inicio'],
                                                                    fin=form.cleaned_data['fin'],
                                                                    taller=form.cleaned_data['taller'],
                                                                    noguia=form.cleaned_data['noguia'],
                                                                    horas=form.cleaned_data['horas'],
                                                                    materiales=form.cleaned_data['materiales'],
                                                                    objetivo=form.cleaned_data['objetivo'],
                                                                    fundamento=form.cleaned_data['fundamento'],
                                                                    procedimiento=form.cleaned_data['procedimiento'],
                                                                    resultados=form.cleaned_data['resultados'],
                                                                    referencias=form.cleaned_data['referencias'],
                                                                    aprendizaje=form.cleaned_data['aprendizaje'],
                                                                    disposiciones=form.cleaned_data['disposiciones'],
                                                                    grupo=form.cleaned_data['grupo'],
                                                                    nivelbioseguridad=form.cleaned_data[
                                                                        'nivelbioseguridad'],
                                                                    emergencia=form.cleaned_data['emergencia'],
                                                                    refuerzo=form.cleaned_data['refuerzo'],
                                                                    observaciones=form.cleaned_data['observaciones'])
                        guia.save(request)
                        log(u'Adiciono guia practica de enfermeria de la planificacion del Docente: %s' % guia, request,
                            "add")
                        return ok_json()
                    else:
                        print(form.errors)
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editguiacienciasbasicasenfermeria':
                try:
                    guia = GuiasNuevaPracticasEnfermeriaMateria.objects.get(pk=request.POST['id'])
                    form = GuiaNuevaPracticaEnfermeriaPlanificacionForm(request.POST)
                    if form.is_valid():
                        guia.titulo = form.cleaned_data['titulo']
                        guia.inicio = form.cleaned_data['inicio']
                        guia.fin = form.cleaned_data['fin']
                        guia.taller = form.cleaned_data['taller']
                        guia.noguia = form.cleaned_data['noguia']
                        guia.horas = form.cleaned_data['horas']
                        guia.equipos = form.cleaned_data['equipos']
                        guia.materiales = form.cleaned_data['materiales']
                        guia.objetivo = form.cleaned_data['objetivo']
                        guia.fundamento = form.cleaned_data['fundamento']
                        guia.procedimiento = form.cleaned_data['procedimiento']
                        guia.resultados = form.cleaned_data['resultados']
                        guia.referencias = form.cleaned_data['referencias']
                        guia.aprendizaje = form.cleaned_data['aprendizaje']
                        guia.disposiciones = form.cleaned_data['disposiciones']
                        guia.grupo = form.cleaned_data['grupo']
                        guia.nivelbioseguridad = form.cleaned_data['nivelbioseguridad']
                        guia.emergencia = form.cleaned_data['emergencia']
                        guia.refuerzo = form.cleaned_data['refuerzo']
                        guia.observaciones = form.cleaned_data['observaciones']
                        guia.save(request)
                        log(u'Modifico nueva guia practica de enfermeria de la planificacion del Docente: %s' % guia,
                            request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    print(ex)
                    transaction.set_rollback(True)
                    return bad_json(error=1,ex=ex)

            if action == 'delguiacienciasbasicasenfermeria':
                try:
                    guia = GuiasNuevaPracticasEnfermeriaMateria.objects.get(pk=request.POST['id'])
                    log(u'Elimino nueva guia: %s' % guia, request, "del")
                    guia.delete()
                    return ok_json()
                except Exception as ex:
                    print(ex)
                    transaction.set_rollback(True)

            if action == 'addguiasimulacionclinica':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    form = GuiaNuevaSimPracticaPlanificacionForm(request.POST)
                    if form.is_valid():
                        if GuiasNuevaPracticasMateria.objects.filter(planificacionmateria=planificacionmateria,
                                                                     noguia=form.cleaned_data['nopractica']).exists():
                            return bad_json(mensaje=u'Ya existe ese numero de practica.')
                        guia = GuiasNuevaSimPracticasMateria(planificacionmateria=planificacionmateria,
                                                             fechainicio=form.cleaned_data['fechainicio'],
                                                             fechafin=form.cleaned_data['fechafin'],
                                                             estudiantes=form.cleaned_data['estudiantes'],
                                                             grupos=form.cleaned_data['grupos'],
                                                             tipopractica=form.cleaned_data['tipopractica'],
                                                             docentetec=Profesor.objects.get(
                                                                 pk=form.cleaned_data['docentetec']),
                                                             nopractica=form.cleaned_data['nopractica'],
                                                             titulogeneral=form.cleaned_data['titulogeneral'],
                                                             tituloespecifico=form.cleaned_data['tituloespecifico'],
                                                             objetivogeneral=form.cleaned_data['objetivogeneral'],
                                                             objetivosespecificos=form.cleaned_data[
                                                                 'objetivosespecificos'],
                                                             resultados=form.cleaned_data['resultados'],
                                                             materialescen=form.cleaned_data['materialescen'],
                                                             materialesest=form.cleaned_data['materialesest'],
                                                             escenario=form.cleaned_data['escenario'],
                                                             descripciongen=form.cleaned_data['descripciongen'],
                                                             alergias=form.cleaned_data['alergias'],
                                                             antecedentesper=form.cleaned_data['antecedentesper'],
                                                             antecedentesfam=form.cleaned_data['antecedentesfam'],
                                                             habitos=form.cleaned_data['habitos'],
                                                             verba=form.cleaned_data['verba'],
                                                             preteo=form.cleaned_data['preteo'],
                                                             referencias=form.cleaned_data['referencias'],
                                                             registo=form.cleaned_data['registo'],
                                                             observaciones=form.cleaned_data['observaciones'],
                                                             medicacion=form.cleaned_data['medicacion'],
                                                             otros=form.cleaned_data['otros'],
                                                             color=generar_color_hexadecimal())
                        guia.save(request)
                        log(u'Adiciono guia practica de planificacion del Docente: %s' % guia, request, "add")
                        return ok_json()
                    else:
                        print(form.errors)
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editguiasimulacionclinica':
                try:
                    guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.POST['id'])
                    form = GuiaNuevaSimPracticaPlanificacionForm(request.POST)
                    if form.is_valid():
                        guia.fechainicio = form.cleaned_data['fechainicio']
                        guia.fechafin = form.cleaned_data['fechafin']
                        estudiantes = form.cleaned_data['estudiantes']
                        guia.grupos = form.cleaned_data['grupos']
                        guia.tipopractica = form.cleaned_data['tipopractica']
                        guia.docentetec = Profesor.objects.get(pk=form.cleaned_data['docentetec'])
                        guia.nopractica = form.cleaned_data['nopractica']
                        guia.titulogeneral = form.cleaned_data['titulogeneral']
                        guia.tituloespecifico = form.cleaned_data['tituloespecifico']
                        guia.objetivogeneral = form.cleaned_data['objetivogeneral']
                        guia.objetivosespecificos = form.cleaned_data['objetivosespecificos']
                        guia.resultados = form.cleaned_data['resultados']
                        guia.materialescen = form.cleaned_data['materialescen']
                        guia.materialesest = form.cleaned_data['materialesest']
                        guia.escenario = form.cleaned_data['escenario']
                        guia.descripciongen = form.cleaned_data['descripciongen']
                        guia.alergias = form.cleaned_data['alergias']
                        guia.antecedentesper = form.cleaned_data['antecedentesper']
                        guia.antecedentesfam = form.cleaned_data['antecedentesfam']
                        guia.habitos = form.cleaned_data['habitos']
                        guia.verba = form.cleaned_data['verba']
                        guia.preteo = form.cleaned_data['preteo']
                        guia.referencias = form.cleaned_data['referencias']
                        guia.registo = form.cleaned_data['registo']
                        guia.observaciones = form.cleaned_data['observaciones']
                        guia.color = generar_color_hexadecimal()
                        guia.save(request)
                        log(u'Modifico nueva guia practica de planificacion de simulación del Docente: %s' % guia,
                            request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:

                    transaction.set_rollback(True)
                    return bad_json(error=1,ex=ex)

            if action == 'delguiasimulacionclinica':
                try:
                    guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.POST['id'])
                    log(u'Elimino nueva guia simulación: %s' % guia, request, "del")
                    guia.delete()
                    return ok_json()
                except Exception as ex:
                    print(ex)
                    transaction.set_rollback(True)

            if action == 'addexamenescomplementarios':
                try:
                    guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.POST['id'])
                    form = ExamenesComplementariosPracticaPlanificacionForm(request.POST)
                    if form.is_valid():
                        examenes = ExamenesComplementariosPracticasMateria(guiasnuevasim=guia,
                                                                           hb=form.cleaned_data['hb'],
                                                                           htco=form.cleaned_data['htco'],
                                                                           leucocitos=form.cleaned_data['leucocitos'],
                                                                           neutrofilos=form.cleaned_data['neutrofilos'],
                                                                           linfocitos=form.cleaned_data['linfocitos'],
                                                                           eosinofilos=form.cleaned_data['eosinofilos'],
                                                                           basofilos=form.cleaned_data['basofilos'],
                                                                           rx=form.cleaned_data['rx'],
                                                                           eco=form.cleaned_data['eco'],
                                                                           tac=form.cleaned_data['tac'],
                                                                           rmn=form.cleaned_data['rmn'])
                        examenes.save(request)
                        log(u'Adiciono examenes complementarios de guia practica de planificacion del Docente: %s' % guia,
                            request, "add")
                        return ok_json()
                    else:
                        print(form.errors)
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editexamenescomplementarios':
                try:
                    examen = ExamenesComplementariosPracticasMateria.objects.get(pk=request.POST['id'])
                    form = ExamenesComplementariosPracticaPlanificacionForm(request.POST)
                    if form.is_valid():
                        examen.hb = form.cleaned_data['hb']
                        examen.htco = form.cleaned_data['htco']
                        examen.leucocitos = form.cleaned_data['leucocitos']
                        examen.neutrofilos = form.cleaned_data['neutrofilos']
                        examen.linfocitos = form.cleaned_data['linfocitos']
                        examen.eosinofilos = form.cleaned_data['eosinofilos']
                        examen.basofilos = form.cleaned_data['basofilos']
                        examen.rx = form.cleaned_data['rx']
                        examen.eco = form.cleaned_data['eco']
                        examen.tac = form.cleaned_data['tac']
                        examen.rmn = form.cleaned_data['rmn']
                        examen.save(request)
                        log(u'Modifico examenes complementarios de planificacion de simulación del Docente: %s' % examen,
                            request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delexamenescomplementarios':
                try:
                    examen = ExamenesComplementariosPracticasMateria.objects.get(pk=request.POST['id'])
                    log(u'Elimino examen complementario de la guia simulación: %s' % examen, request, "del")
                    examen.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)

            if action == 'addantropometria':
                try:
                    guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.POST['id'])
                    form = AntropometriaPracticaPlanificacionForm(request.POST)
                    if form.is_valid():
                        antropometria = AntropometriaPracticasMateria(guiasnuevasim=guia,
                                                                      biotipo=form.cleaned_data['biotipo'],
                                                                      estadogral=form.cleaned_data['estadogral'],
                                                                      estadoconc=form.cleaned_data['estadoconc'],
                                                                      estadonutr=form.cleaned_data['estadonutr'],
                                                                      peso=form.cleaned_data['peso'],
                                                                      talla=form.cleaned_data['talla'],
                                                                      im=form.cleaned_data['imc'])
                        antropometria.save(request)
                        log(u'Adiciono la antropometria de la guia practica de planificacion del Docente: %s' % guia,
                            request, "add")
                        return ok_json()
                    else:
                        print(form.errors)
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editantropometria':
                try:
                    antropometria = AntropometriaPracticasMateria.objects.get(pk=request.POST['id'])
                    form = AntropometriaPracticaPlanificacionForm(request.POST)
                    if form.is_valid():
                        antropometria.biotipo = form.cleaned_data['biotipo']
                        antropometria.estadogral = form.cleaned_data['estadogral']
                        antropometria.estadoconc = form.cleaned_data['estadoconc']
                        antropometria.estadonutr = form.cleaned_data['estadonutr']
                        antropometria.peso = form.cleaned_data['peso']
                        antropometria.talla = form.cleaned_data['talla']
                        antropometria.imc = form.cleaned_data['imc']
                        antropometria.save(request)
                        log(u'Modifico antropometria de planificacion de simulación del Docente: %s' % antropometria,
                            request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delantropometria':
                try:
                    antropometria = AntropometriaPracticasMateria.objects.get(pk=request.POST['id'])
                    log(u'Elimino antropometriade la guia simulación: %s' % antropometria, request, "del")
                    antropometria.delete()
                    return ok_json()
                except Exception as ex:
                    print(ex)
                    transaction.set_rollback(True)

            if action == 'addevolucion':
                try:
                    guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.POST['id'])
                    form = EvolucionSimPracticaPlanificacionForm(request.POST)
                    if form.is_valid():
                        evo = EvolucionPracticasMateria(guiasnuevasim=guia,
                                                        estadio=form.cleaned_data['estadio'],
                                                        tiempo=form.cleaned_data['tiempo'],
                                                        estadoconc=form.cleaned_data['estadoconc'],
                                                        pa=form.cleaned_data['pa'],
                                                        fc=form.cleaned_data['fc'],
                                                        t=form.cleaned_data['t'],
                                                        sat=form.cleaned_data['sat'],
                                                        fr=form.cleaned_data['fr'],
                                                        respac=form.cleaned_data['respac'],
                                                        accionsim=form.cleaned_data['accionsim'],
                                                        accioncam=form.cleaned_data['accioncam'])
                        evo.save(request)
                        log(u'Adiciono la evolución de la guia practica de planificacion del Docente: %s' % guia,
                            request, "add")
                        return ok_json()
                    else:
                        print(form.errors)
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editevolucion':
                try:
                    evo = EvolucionPracticasMateria.objects.get(pk=request.POST['id'])
                    form = EvolucionSimPracticaPlanificacionForm(request.POST)
                    if form.is_valid():
                        evo.estadio = form.cleaned_data['estadio']
                        evo.tiempo = form.cleaned_data['tiempo']
                        evo.estadoconc = form.cleaned_data['estadoconc']
                        evo.pa = form.cleaned_data['pa']
                        evo.fc = form.cleaned_data['fc']
                        evo.t = form.cleaned_data['t']
                        evo.sat = form.cleaned_data['sat']
                        evo.fr = form.cleaned_data['fr']
                        evo.respac = form.cleaned_data['respac']
                        evo.accionsim = form.cleaned_data['accionsim']
                        evo.accioncam = form.cleaned_data['accioncam']
                        evo.save(request)
                        log(u'Modifico evolución de planificacion de simulación del Docente: %s' % evo, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    print(ex)
                    transaction.set_rollback(True)
                    return bad_json(error=1,ex=ex)

            if action == 'delevolucion':
                try:
                    evo = EvolucionPracticasMateria.objects.get(pk=request.POST['id'])
                    log(u'Elimino evolución de la guia simulación: %s' % evo, request, "del")
                    evo.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)

            if action == 'delcontenido':
                try:
                    contenido = ContenidosTallerPlanificacionMateria.objects.get(pk=request.POST['id'])
                    log(u'Elimino contenido: %s' % contenido, request, "del")
                    planificacionmateria = contenido.tallerplanificacionmateria.planificacionmateria
                    planificacionmateria.verificada = False
                    planificacionmateria.save(request)
                    taller = contenido.tallerplanificacionmateria
                    taller.verificada = False
                    taller.save(request)
                    contenido.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'edittaller':
                try:
                    taller = TallerPlanificacionMateria.objects.get(pk=request.POST['id'])
                    modelo = None
                    planificacionmateria = PlanificacionMateria.objects.filter(tallerplanificacionmateria=taller)[0]
                    if planificacionmateria.materia.asignaturamalla:
                        modelo = planificacionmateria.materia.asignaturamalla.malla.modelonuevo
                    else:
                        modelo = planificacionmateria.materia.modelomalla.malla.modelonuevo
                    if modelo == 2:
                        form = TallerPlanificacionNuevaForm(request.POST)
                    else:
                        form = TallerPlanificacionForm(request.POST)
                    if form.is_valid():
                        taller.nombretaller = form.cleaned_data['nombretaller']
                        taller.resultadoaprendizaje = form.cleaned_data['resultadoaprendizaje']
                        taller.recursosutilizados = form.cleaned_data['recursosutilizados']
                        taller.dimensionprocedimental = form.cleaned_data[
                            'dimensionprocedimental'] if taller.planificacionmateria.materia.asignaturamalla.malla.modelonuevo == 0 else ""
                        taller.productoesperado = form.cleaned_data['productoesperado']
                        taller.verificada = False
                        taller.save(request)
                        log(u'Modifico taller de planificacion del Docente: %s' % taller, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editindicador':
                try:
                    indicador = IndicadorRubrica.objects.get(pk=request.POST['id'])
                    form = IndicadoresRubricaForm(request.POST)
                    if form.is_valid():
                        indicador.criterio = form.cleaned_data['criterio']
                        indicador.logroexcelente = form.cleaned_data['logroexcelente']
                        indicador.logromuybueno = form.cleaned_data['logromuybueno']
                        indicador.logrobueno = form.cleaned_data['logrobueno']
                        indicador.logroregular = form.cleaned_data['logroregular']
                        indicador.logrodeficiente = form.cleaned_data['logrodeficiente']
                        indicador.save(request)
                        log(u'Modifico indicador de taller del Docente: %s' % indicador.rubricaresultadoaprendizaje,
                            request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editindicadorplanificacion':
                try:
                    indicador = IndicadorRubrica.objects.get(pk=request.POST['id'])
                    form = IndicadoresRubricaForm(request.POST)
                    if form.is_valid():
                        indicador.criterio = form.cleaned_data['criterio']
                        indicador.logroexcelente = form.cleaned_data['logroexcelente']
                        indicador.logromuybueno = form.cleaned_data['logromuybueno']
                        indicador.logrobueno = form.cleaned_data['logrobueno']
                        indicador.logroregular = form.cleaned_data['logroregular']
                        indicador.logrodeficiente = form.cleaned_data['logrodeficiente']
                        indicador.save(request)
                        log(u'Modifico indicador de planificacion del Docente: %s' % indicador.criterio, request,
                            "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addcontenido':
                try:
                    taller = TallerPlanificacionMateria.objects.get(pk=request.POST['id'])
                    form = ContenidoTallerForm(request.POST)
                    if form.is_valid():
                        contenido = ContenidosTallerPlanificacionMateria(tallerplanificacionmateria=taller,
                                                                         contenido=form.cleaned_data['contenido'])
                        contenido.save(request)
                        planificacionmateria = taller.planificacionmateria
                        taller.verificada = False
                        taller.save(request)
                        log(u'Adiciono contenido de taller: %s' % contenido, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addclase':
                try:
                    taller = TallerPlanificacionMateria.objects.get(pk=request.POST['id'])
                    modelo = None
                    if taller.planificacionmateria.materia.asignaturamalla:
                        modelo = taller.planificacionmateria.materia.asignaturamalla.malla.modelonuevo
                    else:
                        modelo = taller.planificacionmateria.materia.modulomalla.malla.modelonuevo
                    if modelo == 2:
                        form = ClaseTallerNuevaForm(request.POST)
                    else:
                        form = ClaseTallerForm(request.POST)
                    if form.is_valid():
                        fechainicio = None
                        fechafin = None
                        if taller.planificacionmateria.materia:
                            fechainicio = taller.planificacionmateria.materia.inicio
                            fechafin = taller.planificacionmateria.materia.fin
                        elif taller.planificacionmateria.materiacurso:
                            fechainicio = taller.planificacionmateria.materiacurso.fecha_inicio
                            fechafin = taller.planificacionmateria.materiacurso.fecha_fin
                        else:
                            fechainicio = taller.planificacionmateria.materiacursotitulacion.fecha_inicio
                            fechafin = taller.planificacionmateria.materiacursotitulacion.fecha_fin
                        if form.cleaned_data['fecha'] > form.cleaned_data['fechafin']:
                            return bad_json(mensaje=u'Fechas incorrectas.')
                        if (null_to_numeric(form.cleaned_data['horas1'], 1) + null_to_numeric(
                                form.cleaned_data['horas2'], 1) + null_to_numeric(form.cleaned_data['horas4'],
                                                                                  1) + null_to_numeric(
                            form.cleaned_data['horas5'], 1)) <= 0:
                            return bad_json(mensaje=u'Debe seleccionar una actividad.')
                        if null_to_numeric(null_to_numeric(form.cleaned_data['horas1'], 1) + null_to_numeric(
                                form.cleaned_data['horas2'], 1), 1) > taller.planificacionmateria.disponile_docencia():
                            return bad_json(mensaje=u'Supera el limite de horas de docencia asistida.')
                        if null_to_numeric(form.cleaned_data['horas4'],
                                           1) > taller.planificacionmateria.disponile_autonoma():
                            return bad_json(mensaje=u'Supera el limite de horas de trabajo autónomo.')
                        if null_to_numeric(form.cleaned_data['horas5'],
                                           1) > taller.planificacionmateria.disponile_practica():
                            return bad_json(mensaje=u'Supera el limite de horas de trabajo práctico.')
                        clase = ClasesTallerPlanificacionMateria(tallerplanificacionmateria=taller,
                                                                 fecha=form.cleaned_data['fecha'],
                                                                 fechafinactividades=form.cleaned_data['fechafin'],
                                                                 contenido=form.cleaned_data['contenido'],
                                                                 horasdocente_uno=null_to_numeric(
                                                                     form.cleaned_data['horas1'], 1),
                                                                 horasdocente_dos=null_to_numeric(
                                                                     form.cleaned_data['horas2'], 1),
                                                                 actividadesaprendizajecolaborativas=form.cleaned_data[
                                                                     'actividadcol'] if modelo == 0 else None,
                                                                 horascolaborativas=null_to_numeric(
                                                                     form.cleaned_data['horas3'],
                                                                     1) if modelo == 0 else 0,
                                                                 actividadestrabajoautonomas=form.cleaned_data[
                                                                     'actividadauto'],
                                                                 horasautonomas=null_to_numeric(
                                                                     form.cleaned_data['horas4'], 1),
                                                                 actividadesaprendizajepractico=form.cleaned_data[
                                                                     'actividadprac'],
                                                                 horaspracticas=null_to_numeric(
                                                                     form.cleaned_data['horas5'], 1),
                                                                 fasesactividadesarticulacion=form.cleaned_data[
                                                                     'fasesactividadesarticulacion'] if modelo != 0 else None,
                                                                 actividadcontactodocente_uno=form.cleaned_data[
                                                                     'actcondoc1'],
                                                                 actividadcontactodocente_dos=form.cleaned_data[
                                                                     'actcondoc2'],
                                                                 actividadaprendcolab=form.cleaned_data[
                                                                     'actcolaborativas'] if form.cleaned_data[
                                                                     'actcolaborativas'] else None)
                        clase.save(request)
                        taller.verificada = False
                        taller.save(request)
                        log(u'Adiciono clase a taller: %s' % clase, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editclase':
                try:
                    clase = ClasesTallerPlanificacionMateria.objects.get(pk=request.POST['id'])
                    if clase.tallerplanificacionmateria.planificacionmateria.materia.asignaturamalla.malla.modelonuevo == 2:
                        form = ClaseTallerNuevaForm(request.POST)
                    else:
                        form = ClaseTallerForm(request.POST)
                    if form.is_valid():
                        taller = clase.tallerplanificacionmateria
                        fechainicio = None
                        fechafin = None
                        if taller.planificacionmateria.materia:
                            fechainicio = taller.planificacionmateria.materia.inicio
                            fechafin = taller.planificacionmateria.materia.fin
                        elif taller.planificacionmateria.materiacurso:
                            fechainicio = taller.planificacionmateria.materiacurso.fecha_inicio
                            fechafin = taller.planificacionmateria.materiacurso.fecha_fin
                        else:
                            fechainicio = taller.planificacionmateria.materiacursotitulacion.fecha_inicio
                            fechafin = taller.planificacionmateria.materiacursotitulacion.fecha_fin
                        if form.cleaned_data['fecha'] > form.cleaned_data['fechafin']:
                            return bad_json(mensaje=u'Fechas incorrectas.')
                        if not taller.planificacionmateria.materia.carrera.posgrado:
                            if form.cleaned_data['fecha'] < fechainicio or form.cleaned_data['fecha'] > fechafin:
                                return bad_json(mensaje=u'Fecha fuera del rango de las fechas de la materia.')
                            if form.cleaned_data['fechafin'] < fechainicio or form.cleaned_data['fechafin'] > fechafin:
                                return bad_json(mensaje=u'Fecha fin fuera del rango de las fechas de la materia.')
                            if clase.tallerplanificacionmateria.planificacionmateria.materia.asignaturamalla.malla.modelonuevo == 0 and (
                                    null_to_numeric(form.cleaned_data['horas1'], 1) + null_to_numeric(
                                form.cleaned_data['horas2'], 1) + null_to_numeric(form.cleaned_data['horas4'],
                                                                                  1) + null_to_numeric(
                                form.cleaned_data['horas5'], 1)) <= 0:
                                return bad_json(mensaje=u'Debe seleccionar una actividad.')
                            if null_to_numeric(null_to_numeric(form.cleaned_data['horas1'], 1) + null_to_numeric(
                                    form.cleaned_data['horas2'], 1),
                                               1) > taller.planificacionmateria.disponile_docencia() + clase.horasdocente:
                                return bad_json(mensaje=u'Supera el limite de horas de docencia asistida.')
                        if null_to_numeric(form.cleaned_data['horas4'],
                                           1) > taller.planificacionmateria.disponile_autonoma() + clase.horasautonomas:
                            return bad_json(mensaje=u'Supera el limite de horas de trabajo autónomo.')
                        if null_to_numeric(form.cleaned_data['horas5'],
                                           1) > taller.planificacionmateria.disponile_practica() + clase.horaspracticas:
                            return bad_json(mensaje=u'Supera el limite de horas de trabajo práctico.')
                        clase.fecha = form.cleaned_data['fecha']
                        clase.fechafinactividades = form.cleaned_data['fechafin']
                        clase.contenido = form.cleaned_data['contenido']
                        clase.horasdocente_uno = null_to_numeric(form.cleaned_data['horas1'], 1)
                        clase.horasdocente_dos = null_to_numeric(form.cleaned_data['horas2'], 1)
                        clase.horascolaborativas = null_to_numeric(form.cleaned_data[
                                                                       'horas3'] if clase.tallerplanificacionmateria.planificacionmateria.materia.asignaturamalla.malla.modelonuevo != 2 else 0,
                                                                   1)
                        clase.actividadestrabajoautonomas = form.cleaned_data['actividadauto']
                        clase.horasautonomas = null_to_numeric(form.cleaned_data['horas4'], 1)
                        clase.actividadesaprendizajepractico = form.cleaned_data['actividadprac']
                        clase.horaspracticas = null_to_numeric(form.cleaned_data['horas5'], 1)
                        clase.fasesactividadesarticulacion = form.cleaned_data[
                            'fasesactividadesarticulacion'] if clase.tallerplanificacionmateria.planificacionmateria.materia.asignaturamalla.malla.modelonuevo == 2 else None
                        clase.actividadcontactodocente_uno = form.cleaned_data['actcondoc1']
                        clase.actividadcontactodocente_dos = form.cleaned_data['actcondoc2']
                        clase.actividadaprendcolab = form.cleaned_data['actcolaborativas'] if form.cleaned_data[
                            'actcolaborativas'] else None
                        clase.save(request)
                        taller = clase.tallerplanificacionmateria
                        taller.verificada = False
                        taller.save(request)
                        log(u'Modifico clase de taller: %s' % clase, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(mensaje=ex.message)

            if action == 'editcontenido':
                try:
                    contenido = ContenidosTallerPlanificacionMateria.objects.get(pk=request.POST['id'])
                    form = ContenidoTallerForm(request.POST)
                    if form.is_valid():
                        contenido.contenido = form.cleaned_data['contenido']
                        contenido.save(request)
                        taller = contenido.tallerplanificacionmateria
                        taller.verificada = False
                        taller.save(request)
                        log(u'Modifico contenido de taller: %s' % contenido, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'rubrica':
                try:
                    taller = TallerPlanificacionMateria.objects.get(pk=request.POST['id'])
                    rubrica = taller.mi_rubrica()
                    form = RubricaTallerPlanificacionForm(request.POST)
                    if form.is_valid():
                        rubrica.evidencia = form.cleaned_data['evidencia']
                        rubrica.criterio = form.cleaned_data['criterio']
                        rubrica.logroavanzado = form.cleaned_data['logroavanzado']
                        rubrica.logrobajo = form.cleaned_data['logrobajo']
                        rubrica.logrodeficiente = form.cleaned_data['logrodeficiente']
                        rubrica.logroexcelente = form.cleaned_data['logroexcelente']
                        rubrica.logromedio = form.cleaned_data['logromedio']
                        rubrica.save(request)
                        taller.verificada = False
                        taller.save(request)
                        log(u'Modifico rubrica de taller de planificacion del Docente: %s' % taller, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addindicador':
                try:
                    rubrica = RubricaResultadoAprendizaje.objects.get(pk=request.POST['id'])
                    form = IndicadoresRubricaForm(request.POST)
                    if form.is_valid():
                        indicador = IndicadorRubrica(rubricaresultadoaprendizaje=rubrica,
                                                     criterio=form.cleaned_data['criterio'],
                                                     logroexcelente=form.cleaned_data['logroexcelente'],
                                                     logromuybueno=form.cleaned_data['logromuybueno'],
                                                     logrobueno=form.cleaned_data['logrobueno'],
                                                     logroregular=form.cleaned_data['logroregular'],
                                                     logrodeficiente=form.cleaned_data['logrodeficiente'])
                        indicador.save(request)
                        log(u'Inserto indicador rubrica de taller de planificacion del Docente: %s' % rubrica.tallerplanificacionmateria.planificacionmateria,
                            request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addindicadorplanificacion':
                try:
                    rubrica = RubricaResultadoAprendizaje.objects.get(pk=request.POST['id'])
                    form = IndicadoresRubricaForm(request.POST)
                    if form.is_valid():
                        indicador = IndicadorRubrica(rubricaresultadoaprendizaje=rubrica,
                                                     criterio=form.cleaned_data['criterio'],
                                                     logroexcelente=form.cleaned_data['logroexcelente'],
                                                     logromuybueno=form.cleaned_data['logromuybueno'],
                                                     logrobueno=form.cleaned_data['logrobueno'],
                                                     logroregular=form.cleaned_data['logroregular'],
                                                     logrodeficiente=form.cleaned_data['logrodeficiente'])
                        indicador.save(request)
                        log(u'Inserto indicador rubrica de taller de planificacion del Docente: %s' % rubrica.planificacionmateria,
                            request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'rubricaplanificacion':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    rubrica = planificacionmateria.mi_rubrica()
                    form = RubricaTallerPlanificacionForm(request.POST)
                    if form.is_valid():
                        rubrica.evidencia = form.cleaned_data['evidencia']
                        rubrica.criterio = form.cleaned_data['criterio']
                        rubrica.logroavanzado = form.cleaned_data['logroavanzado']
                        rubrica.logrobajo = form.cleaned_data['logrobajo']
                        rubrica.logrodeficiente = form.cleaned_data['logrodeficiente']
                        rubrica.logroexcelente = form.cleaned_data['logroexcelente']
                        rubrica.logromedio = form.cleaned_data['logromedio']
                        rubrica.save(request)
                        planificacionmateria.verificada = False
                        planificacionmateria.save(request)
                        log(u'Modifico rubrica de planificacion del Docente: %s' % planificacionmateria, request,
                            "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'edit':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    materia = planificacionmateria.materia
                    if materia.asignaturamalla.malla.modelonuevo == 2:
                        form = PlanificacionNuevaForm(request.POST, request.FILES)
                    else:
                        form = PlanificacionForm(request.POST, request.FILES)
                    if form.is_valid():
                        horas = 0
                        if materia.asignaturamalla:
                            horas = materia.asignaturamalla.horas
                        else:
                            horas = materia.modulomalla.horas
                        if planificacionmateria.total_horas_asistidas() > form.cleaned_data[
                            'horasasistidasporeldocente']:
                            return bad_json(
                                mensaje='La cantidad de horas de docencia no puede ser menor a las ya planificadas.')
                        if planificacionmateria.total_horas_autonomas() > form.cleaned_data['horasautonomas']:
                            return bad_json(
                                mensaje='La cantidad de horas autonomas no puede ser menor a las ya planificadas.')
                        if planificacionmateria.total_horas_practicas() > form.cleaned_data['horaspracticas']:
                            return bad_json(
                                mensaje='La cantidad de horas de practica no puede ser menor a las ya planificadas.')
                        if materia.asignaturamalla == 0 and planificacionmateria.total_horas_colaborativas() > \
                                form.cleaned_data['horascolaborativas']:
                            return bad_json(
                                mensaje='La cantidad de horas colaborativsa no puede ser menor a las ya planificadas.')
                        if materia.asignaturamalla == 0 and null_to_numeric(
                                form.cleaned_data['horasasistidasporeldocente'] + form.cleaned_data[
                                    'horascolaborativas'] + form.cleaned_data['horasautonomas'] + form.cleaned_data[
                                    'horaspracticas'], 1) != horas:
                            return bad_json(
                                mensaje=u'Las suma de las horas no puede ser diferente a las horas totales.')
                        planificacionmateria.horariotutorias = form.cleaned_data[
                            'horariotutorias'] if materia.asignaturamalla.malla.modelonuevo == 0 else 0
                        planificacionmateria.horariopracticas = form.cleaned_data[
                            'horariopracticas'] if materia.asignaturamalla.malla.modelonuevo == 0 else 0
                        planificacionmateria.horasasistidasporeldocente = form.cleaned_data[
                            'horasasistidasporeldocente']
                        planificacionmateria.horascolaborativas = form.cleaned_data[
                            'horascolaborativas'] if materia.asignaturamalla.malla.modelonuevo == 0 else 0
                        planificacionmateria.horasautonomas = form.cleaned_data['horasautonomas']
                        planificacionmateria.horaspracticas = form.cleaned_data['horaspracticas']
                        planificacionmateria.competenciagenericainstitucion = form.cleaned_data[
                            'competenciagenericainstitucion']
                        planificacionmateria.competenciaespecificaperfildeegreso = form.cleaned_data[
                            'competenciaespecificaperfildeegreso']
                        planificacionmateria.competenciaespecificaproyectoformativo = form.cleaned_data[
                            'competenciaespecificaproyectoformativo']
                        planificacionmateria.contribucioncarrera = form.cleaned_data['contribucioncarrera']
                        planificacionmateria.problemaabordadometodosdeensenanza = form.cleaned_data[
                            'problemaabordadometodosdeensenanza']
                        planificacionmateria.proyectofinal = form.cleaned_data['proyectofinal']
                        planificacionmateria.transversalidad = form.cleaned_data[
                            'transversalidad'] if materia.asignaturamalla.malla.modelonuevo != 0 else ""
                        planificacionmateria.verificada = False
                        planificacionmateria.save(request)
                        if planificacionmateria.tiene_rubrica():
                            rubrica = planificacionmateria.mi_rubrica()
                            rubrica.evidencia = planificacionmateria.proyectofinal
                            rubrica.save()
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delete':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    log(u'Elimino planificacion: %s' % planificacionmateria, request, "del")
                    planificacionmateria.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'deltaller':
                try:
                    taller = TallerPlanificacionMateria.objects.get(pk=request.POST['id'])
                    log(u'Elimino taller: %s' % taller, request, "del")
                    taller.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'delindicador':
                try:
                    indicador = IndicadorRubrica.objects.get(pk=request.POST['id'])
                    log(u'Elimino indicador: %s' % indicador.criterio, request, "del")
                    indicador.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'delindicadorplanificacion':
                try:
                    indicador = IndicadorRubrica.objects.get(pk=request.POST['id'])
                    log(u'Elimino indicador: %s' % indicador.criterio, request, "del")
                    indicador.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'delbibliografiabasica':
                try:
                    bibliografia = BibliografiaBasicaPlanificacion.objects.get(pk=request.POST['id'])
                    log(u'Elimino bibliografia: %s' % bibliografia.bibliografiabasica, request, "del")
                    planificacionmateria = bibliografia.planificacionmateria
                    planificacionmateria.verificadabiblioteca = False
                    planificacionmateria.save(request)
                    bibliografia.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'delbibliografiabasicasolicitada':
                try:
                    bibliografia = BibliografiaBasicaSolicitada.objects.get(pk=request.POST['id'])
                    log(u'Elimino bibliografia solicitada: %s' % bibliografia, request, "del")
                    planificacionmateria = bibliografia.planificacionmateria
                    planificacionmateria.verificada = False
                    planificacionmateria.save(request)
                    bibliografia.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'delbibliografiacomplementariasolicitada':
                try:
                    bibliografia = BibliografiaComplementariaSolicitada.objects.get(pk=request.POST['id'])
                    log(u'Elimino bibliografia complementaria: %s' % bibliografia, request, "del")
                    planificacionmateria = bibliografia.planificacionmateria
                    planificacionmateria.verificada = False
                    planificacionmateria.save(request)
                    bibliografia.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'delbibliografiacomplementaria':
                try:
                    bibliografia = BibliografiaComplementariaPlanificacion.objects.get(pk=request.POST['id'])
                    log(u'Elimino bibliografia complementaria: %s' % bibliografia, request, "del")
                    planificacionmateria = bibliografia.planificacionmateria
                    planificacionmateria.verificadabiblioteca = False
                    planificacionmateria.save(request)
                    bibliografia.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'importarplanificacion':
                try:
                    materia = Materia.objects.get(pk=request.POST['id'])
                    form = ImportarPlanificacionForm(request.POST)
                    if form.is_valid():
                        materiaplanificada = form.cleaned_data['materia']
                        planificacionmateriaplanificada = materiaplanificada.mi_planificacion()
                        rubricap = planificacionmateriaplanificada.mi_rubrica()
                        if materia.tiene_planificacion():
                            return bad_json(mensaje=u'Esta materia ya está planificada')
                        planificacionmateria = PlanificacionMateria(materia=materia,
                                                                    horas=planificacionmateriaplanificada.horas,
                                                                    creditos=planificacionmateriaplanificada.creditos,
                                                                    horariotutorias=planificacionmateriaplanificada.horariotutorias,
                                                                    horasasistidasporeldocente=planificacionmateriaplanificada.horasasistidasporeldocente,
                                                                    horascolaborativas=planificacionmateriaplanificada.horascolaborativas,
                                                                    horasautonomas=planificacionmateriaplanificada.horasautonomas,
                                                                    horaspracticas=planificacionmateriaplanificada.horaspracticas,
                                                                    competenciagenericainstitucion=planificacionmateriaplanificada.competenciagenericainstitucion,
                                                                    competenciaespecificaperfildeegreso=planificacionmateriaplanificada.competenciaespecificaperfildeegreso,
                                                                    competenciaespecificaproyectoformativo=planificacionmateriaplanificada.competenciaespecificaproyectoformativo,
                                                                    contribucioncarrera=planificacionmateriaplanificada.contribucioncarrera,
                                                                    problemaabordadometodosdeensenanza=planificacionmateriaplanificada.problemaabordadometodosdeensenanza,
                                                                    transversalidad=planificacionmateriaplanificada.transversalidad,
                                                                    proyectofinal=planificacionmateriaplanificada.proyectofinal)
                        planificacionmateria.save(request)
                        rubrica = planificacionmateria.mi_rubrica()
                        rubrica.criterio = rubricap.criterio
                        rubrica.logroavanzado = rubricap.logroavanzado
                        rubrica.logrobajo = rubricap.logrobajo
                        rubrica.logrodeficiente = rubricap.logrodeficiente
                        rubrica.logroexcelente = rubricap.logroexcelente
                        rubrica.logromedio = rubricap.logromedio
                        rubrica.save(request)
                        rubricaanterior = RubricaResultadoAprendizaje.objects.filter(
                            planificacionmateria=planificacionmateriaplanificada)[0]
                        for indicadoranterior in rubricaanterior.indicadorrubrica_set.all():
                            indicadoractual = IndicadorRubrica(rubricaresultadoaprendizaje=rubrica,
                                                               criterio=indicadoranterior.criterio,
                                                               logroexcelente=indicadoranterior.logroexcelente,
                                                               logromuybueno=indicadoranterior.logromuybueno,
                                                               logrobueno=indicadoranterior.logrobueno,
                                                               logroregular=indicadoranterior.logroregular,
                                                               logrodeficiente=indicadoranterior.logrodeficiente)
                            indicadoractual.save(request)
                        for bibliografia in planificacionmateriaplanificada.bibliografiacomplementariaplanificacion_set.all():
                            bibliografianueva = BibliografiaComplementariaPlanificacion(
                                planificacionmateria=planificacionmateria,
                                digital=bibliografia.digital,
                                weburl=bibliografia.weburl,
                                codigobibliotecabibliografiacomplementaria=bibliografia.codigobibliotecabibliografiacomplementaria,
                                bibliografiacomplementaria=bibliografia.bibliografiacomplementaria,
                                autor=bibliografia.autor,
                                editorial=bibliografia.editorial,
                                anno=bibliografia.anno,
                                fuente=bibliografia.fuente
                            )
                            bibliografianueva.save(request)
                        for bibliografia in planificacionmateriaplanificada.bibliografiabasicaplanificacion_set.all():
                            bibliografianueva = BibliografiaBasicaPlanificacion(
                                planificacionmateria=planificacionmateria,
                                digital=bibliografia.digital,
                                weburl=bibliografia.weburl,
                                codigobibliotecabibliografiabasica=bibliografia.codigobibliotecabibliografiabasica,
                                bibliografiabasica=bibliografia.bibliografiabasica,
                                autor=bibliografia.autor,
                                editorial=bibliografia.editorial,
                                anno=bibliografia.anno,
                                fuente=bibliografia.fuente)
                            bibliografianueva.save(request)
                        log(u'Importo planificacion: %s' % planificacionmateria, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'importartaller':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    form = ImportarTallerForm(request.POST)
                    if form.is_valid():
                        tallerimporta = form.cleaned_data['taller']
                        materiaplanificada = form.cleaned_data['materia']
                        planificacionmateriaplanificada = materiaplanificada.mi_planificacion()
                        rubricap = planificacionmateriaplanificada.mi_rubrica()
                        taller = TallerPlanificacionMateria(planificacionmateria=planificacionmateria,
                                                            nombretaller=tallerimporta.nombretaller,
                                                            resultadoaprendizaje=tallerimporta.resultadoaprendizaje,
                                                            recursosutilizados=tallerimporta.recursosutilizados,
                                                            productoesperado=tallerimporta.productoesperado,
                                                            dimensionprocedimental=tallerimporta.dimensionprocedimental)
                        taller.save(request)
                        rubricat = tallerimporta.mi_rubrica()
                        rubrica = taller.mi_rubrica()
                        rubrica.evidencia = rubricat.evidencia
                        rubrica.criterio = rubricat.criterio
                        rubrica.logroavanzado = rubricat.logroavanzado
                        rubrica.logrobajo = rubricat.logrobajo
                        rubrica.logrodeficiente = rubricat.logrodeficiente
                        rubrica.logroexcelente = rubricat.logroexcelente
                        rubrica.logromedio = rubricat.logromedio
                        rubrica.save(request)
                        if rubricat.mis_indicadores():
                            for indicadoranteriortaller in rubricat.mis_indicadores():
                                indicadoractualtaller = IndicadorRubrica(rubricaresultadoaprendizaje=rubrica,
                                                                         criterio=indicadoranteriortaller.criterio,
                                                                         logroexcelente=indicadoranteriortaller.logroexcelente,
                                                                         logromuybueno=indicadoranteriortaller.logromuybueno,
                                                                         logrobueno=indicadoranteriortaller.logrobueno,
                                                                         logroregular=indicadoranteriortaller.logroregular,
                                                                         logrodeficiente=indicadoranteriortaller.logrodeficiente)
                                indicadoractualtaller.save()
                        for guiaimporta in tallerimporta.guiaspracticasmateria_set.all():
                            guia = GuiasPracticasMateria(titulo=guiaimporta.titulo,
                                                         planificacionmateria=planificacionmateria,
                                                         taller=taller,
                                                         tipo=guiaimporta.tipo,
                                                         recursos=guiaimporta.recursos,
                                                         equipos=guiaimporta.equipos,
                                                         materiales=guiaimporta.materiales,
                                                         reactivos=guiaimporta.reactivos,
                                                         destino=guiaimporta.destino,
                                                         empresa=guiaimporta.empresa,
                                                         contactoempresa=guiaimporta.contactoempresa,
                                                         materialesbibliograficos=guiaimporta.materialesbibliograficos,
                                                         instrumentos=guiaimporta.instrumentos,
                                                         herramientas=guiaimporta.herramientas,
                                                         objetivo=guiaimporta.objetivo,
                                                         actividades=guiaimporta.actividades,
                                                         resultados=guiaimporta.resultados,
                                                         conclusiones=guiaimporta.conclusiones,
                                                         fundamentoteorico=guiaimporta.fundamentoteorico,
                                                         procedimiento=guiaimporta.procedimiento,
                                                         horas=guiaimporta.horas,
                                                         inicio=guiaimporta.inicio,
                                                         fin=guiaimporta.fin,
                                                         archivo=guiaimporta.archivo)
                            guia.save(request)
                        for guiaimportanueva in tallerimporta.guiasnuevapracticasmateria_set.all():
                            guianueva = GuiasNuevaPracticasMateria(titulo=guiaimportanueva.titulo,
                                                                   planificacionmateria=planificacionmateria,
                                                                   taller=taller,
                                                                   inicio=guiaimportanueva.inicio,
                                                                   fin=guiaimportanueva.fin,
                                                                   noguia=guiaimportanueva.noguia,
                                                                   horas=guiaimportanueva.horas,
                                                                   dimensionprocedimental=guiaimportanueva.dimensionprocedimental,
                                                                   recursos=guiaimportanueva.recursos,
                                                                   equipos=guiaimportanueva.equipos,
                                                                   materiales=guiaimportanueva.materiales,
                                                                   reactivos=guiaimportanueva.reactivos,
                                                                   objetivo=guiaimportanueva.objetivo,
                                                                   fundamento=guiaimportanueva.fundamento,
                                                                   procedimiento=guiaimportanueva.procedimiento,
                                                                   resultados=guiaimportanueva.resultados,
                                                                   referencias=guiaimportanueva.referencias,
                                                                   aprendizaje=guiaimportanueva.aprendizaje,
                                                                   disposiciones=guiaimportanueva.disposiciones,
                                                                   tipo=guiaimportanueva.tipo,
                                                                   archivo=guiaimportanueva.archivo,
                                                                   emergencia=guiaimportanueva.emergencia,
                                                                   refuerzo=guiaimportanueva.refuerzo,
                                                                   observaciones=guiaimportanueva.observaciones,
                                                                   tipopractica=guiaimportanueva.tipopractica)
                            guianueva.save(request)
                            if guiaimportanueva.tipo == 1:
                                guianueva.lugar = guiaimportanueva.lugar
                                guianueva.save()
                                for eq in guiaimportanueva.equipopracticaguia_set.all():
                                    eqp = EquipoPracticaGuia(guia=guianueva,
                                                             equipo=eq.equipo)
                                    eqp.save()
                                guianueva.reactivoslista.set(guiaimportanueva.reactivoslista.all())
                                guianueva.materialeslista.set(guiaimportanueva.materialeslista.all())
                                guianueva.suministroslista.set(guiaimportanueva.suministroslista.all())
                                guianueva.medicamentoslista.set(guiaimportanueva.medicamentoslista.all())
                                guianueva.color = generar_color_hexadecimal()
                                guianueva.save()

                            if guiaimportanueva.tipo == 2:
                                guianueva.enfermeria = guiaimportanueva.enfermeria
                                guianueva.medicina = guiaimportanueva.medicina
                                guianueva.odontologia = guiaimportanueva.odontologia
                                guianueva.establecimiento = guiaimportanueva.establecimiento
                                guianueva.nombreestablecimiento = guiaimportanueva.nombreestablecimiento
                                guianueva.internadoexternado = guiaimportanueva.internadoexternado
                                guianueva.save()

                            log(u'Se importa guia practica nuevo formato: %s' % guianueva, request, "add")

                        for guiaimportaenfermeria in tallerimporta.guiasnuevapracticasenfermeriamateria_set.all():
                            guiaenfermeria = GuiasNuevaPracticasEnfermeriaMateria(titulo=guiaimportanueva.titulo,
                                                                                  planificacionmateria=planificacionmateria,
                                                                                  taller=taller,
                                                                                  inicio=guiaimportaenfermeria.inicio,
                                                                                  fin=guiaimportaenfermeria.fin,
                                                                                  noguia=guiaimportaenfermeria.noguia,
                                                                                  horas=guiaimportaenfermeria.horas,
                                                                                  materiales=guiaimportaenfermeria.materiales,
                                                                                  equipos=guiaimportaenfermeria.equipos,
                                                                                  objetivo=guiaimportaenfermeria.objetivo,
                                                                                  fundamento=guiaimportaenfermeria.fundamento,
                                                                                  procedimiento=guiaimportaenfermeria.procedimiento,
                                                                                  resultados=guiaimportaenfermeria.resultados,
                                                                                  referencias=guiaimportaenfermeria.referencias,
                                                                                  aprendizaje=guiaimportaenfermeria.aprendizaje,
                                                                                  disposiciones=guiaimportaenfermeria.disposiciones,
                                                                                  nivelbioseguridad=guiaimportaenfermeria.nivelbioseguridad,
                                                                                  tipo=guiaimportaenfermeria.tipo,
                                                                                  emergencia=guiaimportaenfermeria.emergencia,
                                                                                  grupo=guiaimportaenfermeria.grupo,
                                                                                  refuerzo=guiaimportaenfermeria.refuerzo,
                                                                                  observaciones=guiaimportaenfermeria.observaciones)
                            guiaenfermeria.save(request)
                        for contenidoimporta in tallerimporta.contenidostallerplanificacionmateria_set.all():
                            contenido = ContenidosTallerPlanificacionMateria(tallerplanificacionmateria=taller,
                                                                             contenido=contenidoimporta.contenido)
                            contenido.save(request)
                            for clase in contenidoimporta.clasestallerplanificacionmateria_set.all():
                                dias = (clase.fecha - materiaplanificada.inicio).days
                                fecha = planificacionmateria.materia.inicio + timedelta(days=dias)
                                if fecha > planificacionmateria.materia.fin:
                                    fecha = planificacionmateria.materia.fin
                                claseimporta = ClasesTallerPlanificacionMateria(tallerplanificacionmateria=taller,
                                                                                fecha=fecha,
                                                                                fechafinactividades=fecha,
                                                                                contenido=contenido,
                                                                                actividadesaprendizajecondocenciaasistida_uno=clase.actividadesaprendizajecondocenciaasistida_uno,
                                                                                actividadesaprendizajecondocenciaasistida_dos=clase.actividadesaprendizajecondocenciaasistida_dos,
                                                                                horasdocente=clase.horasdocente,
                                                                                horasdocente_uno=clase.horasdocente_uno,
                                                                                horasdocente_dos=clase.horasdocente_dos,
                                                                                actividadestrabajoautonomas=clase.actividadestrabajoautonomas,
                                                                                horasautonomas=clase.horasautonomas,
                                                                                actividadesaprendizajepractico=clase.actividadesaprendizajepractico,
                                                                                horaspracticas=clase.horaspracticas,
                                                                                actividadesaprendizajecolaborativas=clase.actividadesaprendizajecolaborativas,
                                                                                fasesactividadesarticulacion=clase.fasesactividadesarticulacion,
                                                                                actividadcontactodocente_uno=clase.actividadcontactodocente_uno,
                                                                                actividadcontactodocente_dos=clase.actividadcontactodocente_dos,
                                                                                horascolaborativas=clase.horascolaborativas,
                                                                                actividadaprendcolab=clase.actividadaprendcolab)
                                claseimporta.save(request)
                        log(u'Importo Taller %s' % taller, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'importartallermed':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    form = ImportarTallerForm(request.POST)
                    if form.is_valid():
                        tallerimporta = form.cleaned_data['taller']
                        materiaplanificada = form.cleaned_data['materia']
                        planificacionmateriaplanificada = materiaplanificada.mi_planificacion()
                        rubricap = planificacionmateriaplanificada.mi_rubrica()
                        taller = TallerPlanificacionMateria(planificacionmateria=planificacionmateria,
                                                            nombretaller=tallerimporta.nombretaller,
                                                            resultadoaprendizaje=tallerimporta.resultadoaprendizaje,
                                                            recursosutilizados=tallerimporta.recursosutilizados,
                                                            productoesperado=tallerimporta.productoesperado,
                                                            dimensionprocedimental=tallerimporta.dimensionprocedimental)
                        taller.save(request)
                        rubricat = tallerimporta.mi_rubrica()
                        rubrica = taller.mi_rubrica()
                        rubrica.evidencia = rubricat.evidencia
                        rubrica.criterio = rubricat.criterio
                        rubrica.logroavanzado = rubricat.logroavanzado
                        rubrica.logrobajo = rubricat.logrobajo
                        rubrica.logrodeficiente = rubricat.logrodeficiente
                        rubrica.logroexcelente = rubricat.logroexcelente
                        rubrica.logromedio = rubricat.logromedio
                        rubrica.save(request)
                        if rubricat.mis_indicadores():
                            for indicadoranteriortaller in rubricat.mis_indicadores():
                                indicadoractualtaller = IndicadorRubrica(rubricaresultadoaprendizaje=rubrica,
                                                                         criterio=indicadoranteriortaller.criterio,
                                                                         logroexcelente=indicadoranteriortaller.logroexcelente,
                                                                         logromuybueno=indicadoranteriortaller.logromuybueno,
                                                                         logrobueno=indicadoranteriortaller.logrobueno,
                                                                         logroregular=indicadoranteriortaller.logroregular,
                                                                         logrodeficiente=indicadoranteriortaller.logrodeficiente)
                                indicadoractualtaller.save()

                        for contenidoimporta in tallerimporta.contenidostallerplanificacionmateria_set.all():
                            contenido = ContenidosTallerPlanificacionMateria(tallerplanificacionmateria=taller,
                                                                             contenido=contenidoimporta.contenido)
                            contenido.save(request)
                            for clase in contenidoimporta.clasestallerplanificacionmateria_set.all():
                                dias = (clase.fecha - materiaplanificada.inicio).days
                                fecha = planificacionmateria.materia.inicio + timedelta(days=dias)
                                if fecha > planificacionmateria.materia.fin:
                                    fecha = planificacionmateria.materia.fin
                                claseimporta = ClasesTallerPlanificacionMateria(tallerplanificacionmateria=taller,
                                                                                fecha=fecha,
                                                                                fechafinactividades=fecha,
                                                                                contenido=contenido,
                                                                                actividadesaprendizajecondocenciaasistida_uno=clase.actividadesaprendizajecondocenciaasistida_uno,
                                                                                actividadesaprendizajecondocenciaasistida_dos=clase.actividadesaprendizajecondocenciaasistida_dos,
                                                                                horasdocente=clase.horasdocente,
                                                                                horasdocente_uno=clase.horasdocente_uno,
                                                                                horasdocente_dos=clase.horasdocente_dos,
                                                                                actividadestrabajoautonomas=clase.actividadestrabajoautonomas,
                                                                                horasautonomas=clase.horasautonomas,
                                                                                actividadesaprendizajepractico=clase.actividadesaprendizajepractico,
                                                                                horaspracticas=clase.horaspracticas,
                                                                                actividadesaprendizajecolaborativas=clase.actividadesaprendizajecolaborativas,
                                                                                fasesactividadesarticulacion=clase.fasesactividadesarticulacion,
                                                                                actividadcontactodocente_uno=clase.actividadcontactodocente_uno,
                                                                                actividadcontactodocente_dos=clase.actividadcontactodocente_dos,
                                                                                horascolaborativas=clase.horascolaborativas,
                                                                                actividadaprendcolab=clase.actividadaprendcolab)
                                claseimporta.save(request)
                        log(u'Importo Taller de medicina  %s' % taller, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delclase':
                try:
                    clase = ClasesTallerPlanificacionMateria.objects.get(pk=request.POST['id'])
                    if clase.en_uso():
                        return bad_json(mensaje=u'La clase se encuentra en uso')
                    log(u'Elimino clase: %s' % clase, request, "del")
                    taller = clase.tallerplanificacionmateria
                    taller.verificada = False
                    taller.save(request)
                    clase.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'actualizafecha':
                try:
                    clase = ClasesTallerPlanificacionMateria.objects.get(pk=request.POST['id'])
                    valor = convertir_fecha(request.POST['valor'])
                    clase.fecha = valor
                    clase.save(request)
                    taller = clase.tallerplanificacionmateria
                    if not taller.aprobado:
                        taller.verificada = False
                        taller.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'actualizafechafinactu':
                try:
                    clase = ClasesTallerPlanificacionMateria.objects.get(pk=request.POST['id'])
                    valor = convertir_fecha(request.POST['valor'])
                    clase.fechafinactividades = valor
                    clase.save(request)
                    taller = clase.tallerplanificacionmateria
                    if not taller.aprobado:
                        taller.verificada = False
                        taller.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'subirarchivo':
                try:
                    clase = ClasesTallerPlanificacionMateria.objects.get(pk=request.POST['id'])
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivoplanificacion_", newfile._name)
                        clase.archivo = newfile
                        clase.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'subirarchivoguia':
                try:
                    guia = GuiasPracticasMateria.objects.get(pk=request.POST['id'])
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivoplanificacion_", newfile._name)
                        guia.archivo = newfile
                        guia.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'verificarbibliografia':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    planificacionmateria.verificadabiblioteca = True
                    planificacionmateria.save(request)
                    log(u'Confirmo planificacion: %s' % planificacionmateria, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'verificarplanificacion':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    planificacionmateria.verificada = True
                    planificacionmateria.save(request)
                    log(u'Confirmo planificacion: %s' % planificacionmateria, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'verificartaller':
                try:
                    taller = TallerPlanificacionMateria.objects.get(pk=request.POST['id'])
                    if taller.planificacionmateria.materia.asignaturamalla:
                        malla = taller.planificacionmateria.materia.asignaturamalla.malla
                    else:
                        malla = taller.planificacionmateria.materia.modulomalla.malla
                    if not taller.clasestallerplanificacionmateria_set.exists():
                        return bad_json(mensaje=u'Debe definir una clase para el taller %s' % taller)
                    for clase in taller.clasestallerplanificacionmateria_set.all():
                        if malla.validacion == 2:
                            if not clase.contenido:
                                return bad_json(
                                    mensaje=u'Debe escoger contenido para la clase del dia %s del taller %s' % (
                                        clase.fecha.strftime('%d-%m-%Y'), taller))
                            if not clase.horasdocente and not clase.horascolaborativas and not clase.horaspracticas and not clase.horasautonomas:
                                return bad_json(
                                    mensaje=u'Debe completar las horas para la clase del dia %s del taller %s' % (
                                        clase.fecha.strftime('%d-%m-%Y'), taller))
                            if not taller.planificacionmateria.materia.carrera.posgrado:
                                if taller.planificacionmateria.materia.asignaturamalla:
                                    if not clase.actividadesaprendizajecondocenciaasistida_uno and not clase.actividadcontactodocente_uno and not clase.actividadaprendcolab:
                                        return bad_json(
                                            mensaje=u'Debe escoger las actividades a realizar en la clase del dia %s del taller %s' % (
                                                clase.fecha.strftime('%d-%m-%Y'), taller))
                                    if taller.planificacionmateria.materia.asignaturamalla.malla.modelonuevo == 0:
                                        if not clase.actividadesaprendizajecondocenciaasistida_uno and not clase.actividadcontactodocente_uno:
                                            if clase.horasdocente_uno:
                                                return bad_json(
                                                    mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                        clase.fecha.strftime('%d-%m-%Y'), taller))
                                    else:
                                        if not clase.actividadcontactodocente_uno:
                                            return bad_json(
                                                mensaje=u'Debe escoger las actividades a realizar en la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    if taller.planificacionmateria.materia.asignaturamalla.malla.modelonuevo == 0:
                                        if (clase.actividadcontactodocente_uno and not clase.horasdocente_uno):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    else:
                                        if (clase.actividadcontactodocente_uno and not clase.horasdocente_uno) or (
                                                not clase.actividadcontactodocente_uno and clase.horasdocente_uno):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    if taller.planificacionmateria.materia.asignaturamalla.malla.modelonuevo == 0:
                                        if not clase.actividadesaprendizajecondocenciaasistida_dos and not clase.actividadcontactodocente_dos:
                                            if clase.horasdocente_dos:
                                                return bad_json(
                                                    mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                        clase.fecha.strftime('%d-%m-%Y'), taller))
                                        if (clase.actividadcontactodocente_dos and not clase.horasdocente_dos):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    else:
                                        if (clase.actividadcontactodocente_dos and not clase.horasdocente_dos) or (
                                                not clase.actividadcontactodocente_dos and clase.horasdocente_dos):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                elif taller.planificacionmateria.materia.modulomalla:
                                    if taller.planificacionmateria.materia.modulomalla.malla.modelonuevo == 0:
                                        if not clase.actividadesaprendizajecondocenciaasistida_uno and not clase.actividadcontactodocente_uno:
                                            return bad_json(
                                                mensaje=u'Debe escoger las actividades a realizar en la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    else:
                                        if not clase.actividadcontactodocente_uno:
                                            return bad_json(
                                                mensaje=u'Debe escoger las actividades a realizar en la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    if taller.planificacionmateria.materia.modulomalla.malla.modelonuevo == 0:
                                        if (
                                                clase.actividadesaprendizajecondocenciaasistida_uno and not clase.horasdocente_uno) or (
                                                not clase.actividadesaprendizajecondocenciaasistida_uno and clase.horasdocente_uno):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    else:
                                        if (clase.actividadcontactodocente_uno and not clase.horasdocente_uno) or (
                                                not clase.actividadcontactodocente_uno and clase.horasdocente_uno):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    if taller.planificacionmateria.materia.modulomalla.malla.modelonuevo == 0:
                                        if (
                                                clase.actividadesaprendizajecondocenciaasistida_dos and not clase.horasdocente_dos) or (
                                                not clase.actividadesaprendizajecondocenciaasistida_dos and clase.horasdocente_dos):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    else:
                                        if (clase.actividadcontactodocente_dos and not clase.horasdocente_dos) or (
                                                not clase.actividadcontactodocente_dos and clase.horasdocente_dos):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                            if (clase.actividadestrabajoautonomas and not clase.horasautonomas) or (
                                    not clase.actividadestrabajoautonomas and clase.horasautonomas):
                                return bad_json(
                                    mensaje=u'Debe completar las horas autonomas de la clase del dia %s del taller %s' % (
                                        clase.fecha.strftime('%d-%m-%Y'), taller))
                            if (clase.actividadesaprendizajepractico and not clase.horaspracticas) or (
                                    not clase.actividadesaprendizajepractico and clase.horaspracticas):
                                return bad_json(
                                    mensaje=u'Debe completar las horas practicas de la clase del dia %s del taller %s' % (
                                        clase.fecha.strftime('%d-%m-%Y'), taller))
                            if ((
                                    clase.actividadesaprendizajecolaborativas or clase.actividadaprendcolab) and not clase.horascolaborativas):
                                return bad_json(
                                    mensaje=u'Debe completar las horas colaborativas de la clase del dia %s del taller %s' % (
                                        clase.fecha.strftime('%d-%m-%Y'), taller))
                            if (not clase.actividadesaprendizajecolaborativas and not clase.actividadaprendcolab):
                                if clase.horascolaborativas:
                                    return bad_json(
                                        mensaje=u'Debe completar las horas colaborativas de la clase del dia %s del taller %s' % (
                                            clase.fecha.strftime('%d-%m-%Y'), taller))
                        else:
                            if not clase.contenido:
                                return bad_json(
                                    mensaje=u'Debe escoger contenido para la clase del dia %s del taller %s' % (
                                        clase.fecha.strftime('%d-%m-%Y'), taller))
                            if not clase.horasdocente and not clase.horascolaborativas and not clase.horaspracticas and not clase.horasautonomas:
                                return bad_json(
                                    mensaje=u'Debe completar las horas para la clase del dia %s del taller %s' % (
                                        clase.fecha.strftime('%d-%m-%Y'), taller))
                            if not taller.planificacionmateria.materia.carrera.posgrado:
                                if taller.planificacionmateria.materia.asignaturamalla:
                                    if taller.planificacionmateria.materia.asignaturamalla.malla.modelonuevo == 0:
                                        if not clase.actividadesaprendizajecondocenciaasistida_uno and not clase.actividadcontactodocente_uno:
                                            if clase.horasdocente_uno:
                                                return bad_json(
                                                    mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                        clase.fecha.strftime('%d-%m-%Y'), taller))
                                            else:
                                                return bad_json(
                                                    mensaje=u'Debe escoger las actividades a realizar en la clase del dia %s del taller %s' % (
                                                        clase.fecha.strftime('%d-%m-%Y'), taller))
                                    else:
                                        if not clase.actividadcontactodocente_uno:
                                            return bad_json(
                                                mensaje=u'Debe escoger las actividades a realizar en la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    if taller.planificacionmateria.materia.asignaturamalla.malla.modelonuevo == 0:
                                        if ((
                                                clase.actividadesaprendizajecondocenciaasistida_uno or clase.actividadcontactodocente_uno) and not clase.horasdocente_uno):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    else:
                                        if (clase.actividadcontactodocente_uno and not clase.horasdocente_uno) or (
                                                not clase.actividadcontactodocente_uno and clase.horasdocente_uno):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    if taller.planificacionmateria.materia.asignaturamalla.malla.modelonuevo == 0:
                                        if not clase.actividadesaprendizajecondocenciaasistida_dos and not clase.actividadcontactodocente_dos:
                                            if clase.horasdocente_dos:
                                                return bad_json(
                                                    mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                        clase.fecha.strftime('%d-%m-%Y'), taller))
                                        if ((
                                                clase.actividadesaprendizajecondocenciaasistida_dos or clase.actividadcontactodocente_dos) and not clase.horasdocente_dos):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    else:
                                        if (clase.actividadcontactodocente_dos and not clase.horasdocente_dos) or (
                                                not clase.actividadcontactodocente_dos and clase.horasdocente_dos):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                elif taller.planificacionmateria.materia.modulomalla:
                                    if taller.planificacionmateria.materia.modulomalla.malla.modelonuevo == 0:
                                        if not clase.actividadesaprendizajecondocenciaasistida_uno and not clase.actividadcontactodocente_uno:
                                            return bad_json(
                                                mensaje=u'Debe escoger las actividades a realizar en la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    else:
                                        if not clase.actividadcontactodocente_uno:
                                            return bad_json(
                                                mensaje=u'Debe escoger las actividades a realizar en la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    if taller.planificacionmateria.materia.modulomalla.malla.modelonuevo == 0:
                                        if (
                                                clase.actividadesaprendizajecondocenciaasistida_uno and not clase.horasdocente_uno) or (
                                                not clase.actividadesaprendizajecondocenciaasistida_uno and clase.horasdocente_uno):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    else:
                                        if (clase.actividadcontactodocente_uno and not clase.horasdocente_uno) or (
                                                not clase.actividadcontactodocente_uno and clase.horasdocente_uno):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    if taller.planificacionmateria.materia.modulomalla.malla.modelonuevo == 0:
                                        if (
                                                clase.actividadesaprendizajecondocenciaasistida_dos and not clase.horasdocente_dos) or (
                                                not clase.actividadesaprendizajecondocenciaasistida_dos and clase.horasdocente_dos):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                                    else:
                                        if (clase.actividadcontactodocente_dos and not clase.horasdocente_dos) or (
                                                not clase.actividadcontactodocente_dos and clase.horasdocente_dos):
                                            return bad_json(
                                                mensaje=u'Debe completar las horas de docencia de la clase del dia %s del taller %s' % (
                                                    clase.fecha.strftime('%d-%m-%Y'), taller))
                            if (clase.actividadestrabajoautonomas and not clase.horasautonomas) or (
                                    not clase.actividadestrabajoautonomas and clase.horasautonomas):
                                return bad_json(
                                    mensaje=u'Debe completar las horas autonomas de la clase del dia %s del taller %s' % (
                                        clase.fecha.strftime('%d-%m-%Y'), taller))
                            if (clase.actividadesaprendizajepractico and not clase.horaspracticas) or (
                                    not clase.actividadesaprendizajepractico and clase.horaspracticas):
                                return bad_json(
                                    mensaje=u'Debe completar las horas practicas de la clase del dia %s del taller %s' % (
                                        clase.fecha.strftime('%d-%m-%Y'), taller))
                            if ((
                                    clase.actividadesaprendizajecolaborativas or clase.actividadaprendcolab) and not clase.horascolaborativas):
                                return bad_json(
                                    mensaje=u'Debe completar las horas colaborativas de la clase del dia %s del taller %s' % (
                                        clase.fecha.strftime('%d-%m-%Y'), taller))
                            if (not clase.actividadesaprendizajecolaborativas and not clase.actividadaprendcolab):
                                if clase.horascolaborativas:
                                    return bad_json(
                                        mensaje=u'Debe completar las horas colaborativas de la clase del dia %s del taller %s' % (
                                            clase.fecha.strftime('%d-%m-%Y'), taller))
                    taller.verificada = True
                    taller.save(request)
                    log(u'Confirmo planificacion del taller: %s' % taller, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addgrupopractica':
                try:
                    materia = Materia.objects.get(pk=request.POST['id'])
                    form = GrupoMateriaForm(request.POST)
                    if form.is_valid():
                        grupo = GruposPracticas(materia=materia, nombre=form.cleaned_data['nombre'])
                        grupo.save()
                        log(u'Adiciono grupo de materia: %s' % grupo.materia, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addestudiantegrupopractica':
                try:
                    grupo = GruposPracticas.objects.get(pk=request.POST['id'])
                    form = EstudianteGrupoPracticaForm(request.POST)
                    if form.is_valid():
                        grupoestudiante = MateriaAsignadaGrupoPracticas(grupo=grupo,
                                                                        materiaasignada=form.cleaned_data[
                                                                            'materiaasignada'])
                        grupoestudiante.save()
                        log(u'Adiciono estudiante al grupo: %s' % grupoestudiante.grupo.nombre, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6, form=form)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delestudiantegrupopractica':
                try:
                    grupo = MateriaAsignadaGrupoPracticas.objects.get(pk=request.POST['id'])
                    grupo.delete()
                    log(u'Elimino grupo docencia: %s' % grupo, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'delgrupopracticas':
                try:
                    grupo = GruposPracticas.objects.get(pk=request.POST['id'])
                    grupo.delete()
                    log(u'Elimino grupo de practicas: %s' % grupo.nombre, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'actualizarhibridas':
                try:
                    planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                    log(u'Actualizo hibridas: %s' % planificacionmateria, request, "edit")
                    for asignatura_malla_hibrida in planificacionmateria.materia.asignaturamalla.asignaturamallahibrida_set.all():
                        PlanificacionMateriaAsignaturaMallaHibrida.objects.get_or_create(
                            asignaturamallahibrida=asignatura_malla_hibrida,
                            planificacionmateria=planificacionmateria)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

        if action == 'updatehorasdocentes':
            try:
                profesormateria = PlanificacionMateriaAsignaturaMallaHibrida.objects.get(pk=request.POST['mid'])
                profesormateria.totalhorasaprendizajecontactodocente = float(request.POST['valor'])
                profesormateria.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updatehorasexperimentales':
            try:
                profesormateria = PlanificacionMateriaAsignaturaMallaHibrida.objects.get(pk=request.POST['mid'])
                profesormateria.totalhorasaprendizajepracticoexperimental = float(request.POST['valor'])
                profesormateria.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updatehorasautonomas':
            try:
                profesormateria = PlanificacionMateriaAsignaturaMallaHibrida.objects.get(pk=request.POST['mid'])
                profesormateria.totalhorasaprendizajeautonomo = float(request.POST['valor'])
                profesormateria.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'equiposlabo':
            try:
                id = request.POST.get('id')
                if id:
                    lab = LaboratoriosPracticas.objects.get(pk=id)
                    equipos = lab.equipolaboratoriopracticas_set.all()
                    data = [{'id': equipo.id, 'nombre': equipo.nombre} for equipo in equipos]
                    return JsonResponse(data, safe=False)
                return JsonResponse([], safe=False)
            except:
                return bad_json(error=3)

        if action == 'equiposlabon':
            try:
                # Obtener múltiples IDs de laboratorios seleccionados
                ids = request.POST.getlist('ids')  # Cambiar de 'id' a 'ids[]' para manejar múltiples
                if ids:
                    # Filtrar los equipos que pertenecen a cualquiera de los laboratorios seleccionados
                    equipos = EquipoLaboratorioPracticas.objects.filter(laboratorio__id__in=ids).order_by('nombre').distinct()
                    # Crear una lista de diccionarios con la información de los equipos
                    data = [{'id': equipo.id, 'nombre': equipo.nombre,'tipo':equipo.tipo} for equipo in equipos]
                    return JsonResponse(data, safe=False)
                return JsonResponse([], safe=False)
            except Exception as e:
                # Puedes agregar más detalles al error para facilitar la depuración
                return JsonResponse({'error': str(e)}, status=400)

        if action == 'verificarobservacion':
            try:
                obs = ObservacionesGuiasNuevaPracticasMateria.objects.get(pk=request.POST['id'])
                obs.estado = (request.POST['valor'] == 'true')
                obs.save(request)
                guia = obs.guia
                if not guia.observacionesguiasnuevapracticasmateria_set.filter(estado=False).exists():
                    guia.observacion = False
                    guia.save()

                send_mail(subject=('Observacion en Guia Práctica por parte del Técnico de Laboratorio'),
                          html_template='emails/observacionguiadocente.html',
                          data={'guia': guia, 'obs': obs},
                          recipient_list=[obs.realizadapor])

                log(u"Se cambio el estado de la observacion: %s a %s" % (obs, obs.estado), request, "edit")

                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'verificarobservacionsim':
            try:
                obs = ObservacionesGuiasNuevaPracticasMateriaSim.objects.get(pk=request.POST['id'])
                obs.estado = (request.POST['valor'] == 'true')
                obs.save(request)
                guia = obs.guia
                if not guia.observacionesguiasnuevapracticasmateriasim_set.filter(estado=False).exists():
                    guia.observacion = False
                    guia.save()

                send_mail(subject=('Observacion en Guia Práctica de Simulación por parte del Técnico de Laboratorio'),
                          html_template='emails/observacionguiadocente.html',
                          data={'guia': guia, 'obs': obs},
                          recipient_list=[obs.realizadapor])

                log(u"Se cambio el estado de la observacion: %s a %s" % (obs, obs.estado), request, "edit")

                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'observacionesguia':
            try:
                guia = GuiasNuevaPracticasMateria.objects.get(pk=request.POST['id'])
                ultimo_registro = ObservacionesGuiasNuevaPracticasMateria.objects.filter(guia=guia).latest('id')
                form = ObservacionesPlanoficacionForm(request.POST)
                if form.is_valid():
                    if len(null_to_text(form.cleaned_data['observaciones'])) > 0:
                        observacion = ObservacionesGuiasNuevaPracticasMateria(guia=guia,
                                                                              observacion=form.cleaned_data[
                                                                                  'observaciones'].upper(),
                                                                              realizadapor=persona,
                                                                              estado=True)
                        observacion.save(request)

                        send_mail(subject=('Observacion en Guia Práctica por parte del Docente de la Materia'),
                                  html_template='emails/observaciondocenteguia.html',
                                  data={'guia': guia, 'obs': observacion},
                                  recipient_list=[ultimo_registro.realizadapor])
                        log(u'Se añade una observacion a la guia practica de parte del docente: %s' % guia, request,
                            "edit")
                        return ok_json()
                    else:
                        return ok_json()
                else:
                    return bad_json(error=6, form=form)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'observacionesguiasim':
            try:
                guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.POST['id'])
                ultimo_registro = ObservacionesGuiasNuevaPracticasMateriaSim.objects.filter(guia=guia).latest('id')
                form = ObservacionesPlanoficacionForm(request.POST)
                if form.is_valid():
                    if len(null_to_text(form.cleaned_data['observaciones'])) > 0:
                        observacion = ObservacionesGuiasNuevaPracticasMateria(guia=guia,
                                                                              observacion=form.cleaned_data[
                                                                                  'observaciones'].upper(),
                                                                              realizadapor=persona,
                                                                              estado=True)
                        observacion.save(request)

                        send_mail(
                            subject=('Observacion en Guia Práctica de Simulacion por parte del Docente de la Materia'),
                            html_template='emails/observaciondocenteguia.html',
                            data={'guia': guia, 'obs': observacion},
                            recipient_list=[ultimo_registro.realizadapor])
                        log(u'Se añade una observacion a la guia practica de simulacion de parte del docente: %s' % guia,
                            request, "edit")
                        return ok_json()
                    else:
                        return ok_json()
                else:
                    return bad_json(error=6, form=form)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'obtener_resultado_aprendizaje':
            try:
                taller_id = request.POST.get('idtaller')
                if taller_id:
                    taller = TallerPlanificacionMateria.objects.get(id=taller_id)
                    return JsonResponse({'resultadoaprendizaje': taller.resultadoaprendizaje})
            except Exception as ex:
                pass

        if action == 'diasguia':
            try:
                guia = GuiasNuevaPracticasMateria.objects.get(pk=request.POST['id'])
                form = SuministrosPracticaGuiaForm(request.POST)
                if form.is_valid():
                    fechas_str = request.POST.getlist("fechas[]")  # ← lista con todas las fechas
                    fechas = []
                    for f in fechas_str:
                        f = f.strip()
                        if not f:
                            continue
                        try:
                            fecha = datetime.strptime(f, "%d-%m-%Y").date()
                            fechas.append(fecha)
                        except ValueError:
                            # fecha inválida
                            pass
                    guia.fechasguiasnuevapracticasmateria_set.all().delete()  # si quieres reemplazar todas
                    for fecha in fechas:
                        FechasGuiasNuevaPracticasMateria.objects.create(guia=guia,fecha=fecha)
                    log(u'Se modifico fechas de ejecucion de guia: %s' % guia, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6, form=form)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    malla = None
                    materiamalla = None
                    horas = 0
                    creditos = 0
                    malla = None
                    competencia = ''
                    modelo = None
                    if materia.asignaturamalla:
                        horas = materia.asignaturamalla.horas
                        creditos = materia.asignaturamalla.creditos
                        horasasistidasporeldocente = materia.asignaturamalla.horasasistidas
                        horascolaborativas = materia.asignaturamalla.horascolaborativas
                        horasautonomas = materia.asignaturamalla.horasautonomas
                        horaspracticas = materia.asignaturamalla.horaspracticas
                        malla = materia.asignaturamalla.malla
                        competencia = materia.asignaturamalla.competencia
                        modelo = materia.asignaturamalla.malla.modelonuevo
                    else:
                        horas = materia.modulomalla.horas
                        creditos = materia.modulomalla.creditos
                        horasasistidasporeldocente = materia.modulomalla.horasasistidas
                        horascolaborativas = materia.modulomalla.horascolaborativas
                        horasautonomas = materia.modulomalla.horasautonomas
                        horaspracticas = materia.modulomalla.horaspracticas
                        malla = materia.modulomalla.malla
                        competencia = materia.modulomalla.competencia
                        modelo = materia.modulomalla.malla.modelonuevo
                    if modelo == 2:
                        form = PlanificacionNuevaForm(initial={
                            'horasasistidasporeldocente': materia.asignaturamalla.totalhorasaprendizajecontactodocente if materia.asignaturamalla else 0,
                            'horascolaborativas': horascolaborativas,
                            'horaspracticas': materia.asignaturamalla.totalhorasaprendizajepracticoexperimental if materia.asignaturamalla else 0,
                            'horasautonomas': materia.asignaturamalla.totalhorasaprendizajeautonomo if materia.asignaturamalla else 0,
                            'competenciaespecificaproyectoformativo': competencia,
                            'creditos': creditos,
                            'horas': horas}, )
                    else:
                        form = PlanificacionForm(initial={'horasasistidasporeldocente': horasasistidasporeldocente,
                                                          'horascolaborativas': horascolaborativas,
                                                          'horaspracticas': horaspracticas,
                                                          'horasautonomas': horasautonomas,
                                                          'competenciaespecificaproyectoformativo': competencia,
                                                          'creditos': creditos,
                                                          'horas': horas}, )
                    form.adicionar(malla)
                    data['form'] = form
                    return render(request, "pro_planificacion/add.html", data)
                except Exception as ex:
                    pass

            if action == 'verificarplanificacion':
                try:
                    data['title'] = u'Verificar planificacion'
                    data['planificacionmateria'] = PlanificacionMateria.objects.get(pk=request.GET['id'])
                    return render(request, "pro_planificacion/verificar.html", data)
                except Exception as ex:
                    pass

            if action == 'verificarbibliografia':
                try:
                    data['title'] = u'Verificar la Bibliografía'
                    data['planificacionmateria'] = PlanificacionMateria.objects.get(pk=request.GET['id'])
                    return render(request, "pro_planificacion/verificarbibliografia.html", data)
                except Exception as ex:
                    pass

            if action == 'verificartaller':
                try:
                    data['title'] = u'Verificar planificacion del taller'
                    data['taller'] = taller = TallerPlanificacionMateria.objects.get(pk=request.GET['id'])
                    data['planificacionmateria'] = \
                        PlanificacionMateria.objects.filter(tallerplanificacionmateria=taller)[0]
                    return render(request, "pro_planificacion/verificartaller.html", data)
                except Exception as ex:
                    pass

            if action == 'rubrica':
                try:
                    data['title'] = u'Rubrica Taller'
                    data['taller'] = taller = TallerPlanificacionMateria.objects.get(pk=request.GET['id'])
                    rubrica = taller.mi_rubrica()
                    form = RubricaTallerPlanificacionForm(initial={'resultadoaprendizaje': taller.resultadoaprendizaje,
                                                                   'evidencia': taller.productoesperado if taller.planificacionmateria.materia.asignaturamalla.malla.modelonuevo == 2 else rubrica.evidencia,
                                                                   'criterio': rubrica.criterio,
                                                                   'logroexcelente': rubrica.logroexcelente,
                                                                   'logroavanzado': rubrica.logroavanzado,
                                                                   'logrobajo': rubrica.logrobajo,
                                                                   'logrodeficiente': rubrica.logrodeficiente,
                                                                   'logromedio': rubrica.logromedio})
                    form.taller(taller.planificacionmateria.materia.asignaturamalla.malla.modelonuevo)
                    data['form'] = form
                    data['permite_modificar'] = False if taller.planificacionmateria.aprobado else True
                    return render(request, "pro_planificacion/rubrica.html", data)
                except Exception as ex:
                    pass

            if action == 'detallerubrica':
                try:
                    data['taller'] = taller = TallerPlanificacionMateria.objects.get(pk=request.GET['id'])
                    data['planificacionmateria'] = taller.planificacionmateria
                    data['title'] = u'Detalle Rubrica Taller'
                    data['rubrica'] = rubrica = taller.mi_rubrica()
                    data['indicadores'] = rubrica.mis_indicadores()
                    data['principal'] = taller.planificacionmateria.materia.es_profesor_materia_planifica(profesor)
                    return render(request, "pro_planificacion/detallerubrica.html", data)
                except Exception as ex:
                    pass

            if action == 'detallerubricaplanificacion':
                try:
                    data['title'] = u'Detalle Rubrica Planificación'
                    data['planificacionmateria'] = planificacion = PlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    data['rubrica'] = rubrica = planificacion.mi_rubrica()
                    data['indicadores'] = rubrica.mis_indicadores()
                    return render(request, "pro_planificacion/detallerubricaplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'rubricaplanificacion':
                try:
                    data['title'] = u'Rubrica Planificación'
                    data['planificacion'] = planificacionmateria = PlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    rubrica = planificacionmateria.mi_rubrica()
                    form = RubricaTallerPlanificacionForm(initial={'evidencia': rubrica.evidencia,
                                                                   'criterio': rubrica.criterio,
                                                                   'logroexcelente': rubrica.logroexcelente,
                                                                   'logroavanzado': rubrica.logroavanzado,
                                                                   'logrobajo': rubrica.logrobajo,
                                                                   'logrodeficiente': rubrica.logrodeficiente,
                                                                   'logromedio': rubrica.logromedio})
                    form.planificacion()
                    data['form'] = form
                    data['permite_modificar'] = False if planificacionmateria.aprobado else True
                    return render(request, "pro_planificacion/rubricaplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar Planificación '
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    malla = None
                    if planificacionmateria.materia.asignaturamalla:
                        malla = planificacionmateria.materia.asignaturamalla.malla
                        modelo = planificacionmateria.materia.asignaturamalla.malla.modelonuevo
                    else:
                        malla = planificacionmateria.materia.modulomalla.malla
                        modelo = planificacionmateria.materia.modulomalla.malla.modelonuevo
                    data['ultimo'] = null_to_numeric(
                        planificacionmateria.bibliografiacomplementariaplanificacion_set.aggregate(valor=Max('id'))[
                            'valor'], 0) + 1
                    data['bibliografias'] = planificacionmateria.bibliografiacomplementariaplanificacion_set.all()
                    data['bibliografiasbasicas'] = planificacionmateria.bibliografiabasicaplanificacion_set.all()
                    if modelo == 2:
                        form = PlanificacionNuevaForm(initial={'horariotutorias': planificacionmateria.horariotutorias,
                                                               'horariopracticas': planificacionmateria.horariopracticas,
                                                               'horas': planificacionmateria.horas,
                                                               'creditos': planificacionmateria.creditos,
                                                               'horasasistidasporeldocente': planificacionmateria.horasasistidasporeldocente,
                                                               'horascolaborativas': planificacionmateria.horascolaborativas,
                                                               'horaspracticas': planificacionmateria.horaspracticas,
                                                               'horasautonomas': planificacionmateria.horasautonomas,
                                                               'competenciaespecificaperfildeegreso': planificacionmateria.competenciaespecificaperfildeegreso,
                                                               'competenciaespecificaproyectoformativo': planificacionmateria.competenciaespecificaproyectoformativo,
                                                               'competenciagenericainstitucion': planificacionmateria.competenciagenericainstitucion,
                                                               'contribucioncarrera': planificacionmateria.contribucioncarrera,
                                                               'problemaabordadometodosdeensenanza': planificacionmateria.problemaabordadometodosdeensenanza,
                                                               'proyectofinal': planificacionmateria.proyectofinal,
                                                               'transversalidad': planificacionmateria.transversalidad})
                    else:
                        form = PlanificacionForm(initial={'horariotutorias': planificacionmateria.horariotutorias,
                                                          'horariopracticas': planificacionmateria.horariopracticas,
                                                          'horas': planificacionmateria.horas,
                                                          'creditos': planificacionmateria.creditos,
                                                          'horasasistidasporeldocente': planificacionmateria.horasasistidasporeldocente,
                                                          'horascolaborativas': planificacionmateria.horascolaborativas,
                                                          'horaspracticas': planificacionmateria.horaspracticas,
                                                          'horasautonomas': planificacionmateria.horasautonomas,
                                                          'competenciaespecificaperfildeegreso': planificacionmateria.competenciaespecificaperfildeegreso,
                                                          'competenciaespecificaproyectoformativo': planificacionmateria.competenciaespecificaproyectoformativo,
                                                          'competenciagenericainstitucion': planificacionmateria.competenciagenericainstitucion,
                                                          'contribucioncarrera': planificacionmateria.contribucioncarrera,
                                                          'problemaabordadometodosdeensenanza': planificacionmateria.problemaabordadometodosdeensenanza,
                                                          'proyectofinal': planificacionmateria.proyectofinal})
                    form.adicionar(malla)
                    data['form'] = form
                    return render(request, "pro_planificacion/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'talleres':
                try:
                    data['title'] = u'Talleres'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(pk=request.GET['id'])
                    # coordinacion = planificacionmateria.materia.profesor_principal().distributivohoras(planificacionmateria.materia.nivel.periodo).coordinacion
                    coordinacion = planificacionmateria.materia.coordinacion_materia()
                    if planificacionmateria.materia.asignaturamalla:
                        data['modelonuevo'] = planificacionmateria.materia.asignaturamalla.malla.modelonuevo
                    else:
                        data['modelonuevo'] = planificacionmateria.materia.modulomalla.malla.modelonuevo
                    data['talleres'] = planificacionmateria.tallerplanificacionmateria_set.all()
                    data['guias'] = planificacionmateria.guiaspracticasmateria_set.all()
                    data['guiasnuevas'] = planificacionmateria.guiasnuevapracticasmateria_set.all().order_by('noguia')
                    data['guiassimnuevas'] = planificacionmateria.guiasnuevasimpracticasmateria_set.all().order_by('nopractica')
                    data['guiassimnuevasenfermeria'] = planificacionmateria.guiasnuevapracticasenfermeriamateria_set.all().order_by('noguia')
                    data['guiassalud'] = planificacionmateria.materia.carrera.id in (63, 64, 16, 119)
                    data['importartaller'] = planificacionmateria.materia.nivel.coordinacion().id in (15,42,7,12,45,5)
                    data['guiasing'] = coordinacion.id in (5,12,45, 15)
                    data['reporte_0'] = obtener_reporte('reporte_guias_laboratorio')
                    data['reporte_1'] = obtener_reporte('reporte_guias_visita')
                    data['reporte_2'] = obtener_reporte('reporte_guias_bd')
                    data['reporte_3'] = obtener_reporte('reporte_guias_simulacion')
                    data['reporte_4'] = obtener_reporte('reporte_guias_cienciasbasicas')
                    data['reporte_5'] = obtener_reporte('reporte_guias_simulacionclinica')
                    data['reporte_6'] = obtener_reporte('reporte_guias_laboratorio_tipo1')
                    data['reporte_7'] = obtener_reporte('reporte_guias_laboratorio_tipo2')
                    data['reporte_8'] = obtener_reporte('reporte_guias_laboratorio_tipo3')
                    data['reporte_9'] = obtener_reporte('reporte_guias_laboratorio_tipo1_ing')
                    data['reporte_10'] = obtener_reporte('reporte_guias_laboratorio_tipo4_ing')
                    data['reporte_11'] = obtener_reporte('reporte_guias_laboratorio_tipo1_5_ing')
                    data['principal'] = planificacionmateria.materia.es_profesor_materia_planifica(profesor)
                    return render(request, "pro_planificacion/talleres.html", data)
                except Exception as ex:
                    pass

            if action == 'practicas':
                try:
                    data['title'] = u'Talleres'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    data['guiasnuevas'] = planificacionmateria.guiasnuevapracticasmateria_set.all().order_by('noguia')
                    data['guiassimnuevas'] = planificacionmateria.guiasnuevasimpracticasmateria_set.all().order_by(
                        'nopractica')
                    data[
                        'guiassimnuevasenfermeria'] = planificacionmateria.guiasnuevapracticasenfermeriamateria_set.all().order_by(
                        'noguia')
                    data['guiassalud'] = planificacionmateria.materia.carrera.id in (63, 64)
                    data['reporte_4'] = obtener_reporte('reporte_guias_cienciasbasicas')
                    data['reporte_5'] = obtener_reporte('reporte_guias_simulacionclinica')
                    return render(request, "pro_planificacion/talleres.html", data)
                except Exception as ex:
                    pass

            if action == 'bibliografia':
                try:
                    data['title'] = u'Bibliografía'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(pk=request.GET['id'])
                    data['bibliografiasbasicas'] = planificacionmateria.bibliografiabasicaplanificacion_set.all()
                    data['bibliografiascomplementarias'] = planificacionmateria.bibliografiacomplementariaplanificacion_set.all()
                    data['bibliografiasbasicassolicitadas'] = planificacionmateria.bibliografiabasicasolicitada_set.all()
                    data['bibliografiascomplementariassolicitadas'] = planificacionmateria.bibliografiacomplementariasolicitada_set.all()
                    return render(request, "pro_planificacion/bibliografia.html", data)
                except Exception as ex:
                    pass

            if action == 'contenidos':
                try:
                    data['taller'] = taller = TallerPlanificacionMateria.objects.get(pk=request.GET['id'])
                    data['title'] = u'Contenidos de talleres'
                    data['planificacionmateria'] = taller.planificacionmateria
                    data['contenidos'] = taller.contenidostallerplanificacionmateria_set.all()
                    data['principal'] = taller.planificacionmateria.materia.es_profesor_materia_planifica(profesor)
                    return render(request, "pro_planificacion/contenidos.html", data)
                except Exception as ex:
                    pass

            if action == 'addtaller':
                try:
                    data['title'] = u'Adicionar Taller'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    modelo = None
                    if planificacionmateria.materia.asignaturamalla:
                        modelo = planificacionmateria.materia.asignaturamalla.malla.modelonuevo
                    else:
                        modelo = planificacionmateria.materia.modulomalla.malla.modelonuevo
                    if modelo == 0:
                        data['form'] = TallerPlanificacionForm()
                    else:
                        data['form'] = TallerPlanificacionNuevaForm()
                    return render(request, "pro_planificacion/addtaller.html", data)
                except Exception as ex:
                    pass

            if action == 'addindicador':
                try:
                    data['title'] = u'Adicionar Indicador'
                    data['rubrica'] = rubrica = RubricaResultadoAprendizaje.objects.get(pk=request.GET['id'])
                    data['taller'] = rubrica.mi_taller()
                    data['form'] = IndicadoresRubricaForm()
                    return render(request, "pro_planificacion/addindicador.html", data)
                except Exception as ex:
                    pass

            if action == 'addindicadorplanificacion':
                try:
                    data['title'] = u'Adicionar Indicador Planificación'
                    data['rubrica'] = rubrica = RubricaResultadoAprendizaje.objects.get(pk=request.GET['id'])
                    data['planificacion'] = rubrica.mi_planificacion()
                    data['form'] = IndicadoresRubricaForm()
                    return render(request, "pro_planificacion/addindicadorplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'addbibliografiabasica':
                try:
                    data['title'] = u'Adicionar bibliografia basica'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(pk=request.GET['id'])
                    sede = None
                    if planificacionmateria.materia:
                        sede = planificacionmateria.materia.nivel.sede
                    elif planificacionmateria.materiacurso:
                        sede = planificacionmateria.materiacurso.curso.coordinacion.sede
                    else:
                        sede = planificacionmateria.materiacursotitulacion.curso.coordinacion.sede
                    data['sede'] = sede
                    data['form'] = BibliografiaPlanificacionForm()
                    return render(request, "pro_planificacion/addbibliografiabasica.html", data)
                except Exception as ex:
                    pass

            if action == 'addsolicitarbibliografiabasica':
                try:
                    data['title'] = u'Solicitar bibliografia basica'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    sede = None
                    if planificacionmateria.materia:
                        sede = planificacionmateria.materia.nivel.sede
                    elif planificacionmateria.materiacurso:
                        sede = planificacionmateria.materiacurso.curso.coordinacion.sede
                    else:
                        sede = planificacionmateria.materiacursotitulacion.curso.coordinacion.sede
                    data['sede'] = sede
                    data['form'] = SolicitarBibliografiaPlanificacionForm()
                    return render(request, "pro_planificacion/solicitarbibliografiabasica.html", data)
                except Exception as ex:
                    pass

            if action == 'addsolicitarbibliografiacomplementaria':
                try:
                    data['title'] = u'Solicitar bibliografia complementaria'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    sede = None
                    if planificacionmateria.materia:
                        sede = planificacionmateria.materia.nivel.sede
                    elif planificacionmateria.materiacurso:
                        sede = planificacionmateria.materiacurso.curso.coordinacion.sede
                    else:
                        sede = planificacionmateria.materiacursotitulacion.curso.coordinacion.sede
                    data['sede'] = sede
                    data['form'] = SolicitarBibliografiaPlanificacionForm()
                    return render(request, "pro_planificacion/addbibliografiacomplementariasolicitada.html", data)
                except Exception as ex:
                    pass

            if action == 'editbibliografiabasica':
                try:
                    data['title'] = u'Editar bibliografia basica'
                    data['bibliografia'] = bibliografia = BibliografiaBasicaPlanificacion.objects.get(pk=request.GET['id'])
                    sede = None
                    if bibliografia.planificacionmateria.materia:
                        sede = bibliografia.planificacionmateria.materia.nivel.sede
                    elif bibliografia.planificacionmateria.materiacurso:
                        sede = bibliografia.planificacionmateria.materiacurso.curso.coordinacion.sede
                    else:
                        sede = bibliografia.planificacionmateria.materiacursotitulacion.curso.coordinacion.sede
                    data['sede'] = sede
                    data['form'] = BibliografiaPlanificacionForm(
                        initial={'codigo': bibliografia.codigobibliotecabibliografiabasica,
                                 'digital': bibliografia.digital,
                                 'url': bibliografia.weburl,
                                 'titulo': bibliografia.bibliografiabasica,
                                 'autor': bibliografia.autor,
                                 'editorial': bibliografia.editorial,
                                 'anno': bibliografia.anno,
                                 'fuente': bibliografia.fuente})
                    return render(request, "pro_planificacion/editbibliografiabasica.html", data)
                except Exception as ex:
                    pass

            if action == 'editbibliografiabasicasolicitada':
                try:
                    data['title'] = u'Editar bibliografia basica solicitada'
                    data['bibliografia'] = bibliografia = BibliografiaBasicaSolicitada.objects.get(pk=request.GET['id'])
                    sede = None
                    if bibliografia.planificacionmateria.materia:
                        sede = bibliografia.planificacionmateria.materia.nivel.sede
                    elif bibliografia.planificacionmateria.materiacurso:
                        sede = bibliografia.planificacionmateria.materiacurso.curso.coordinacion.sede
                    else:
                        sede = bibliografia.planificacionmateria.materiacursotitulacion.curso.coordinacion.sede
                    data['sede'] = sede
                    data['form'] = SolicitarBibliografiaPlanificacionForm(initial={'digital': bibliografia.digital,
                                                                                   'titulo': bibliografia.titulo,
                                                                                   'autor': bibliografia.autor,
                                                                                   'editorial': bibliografia.editorial,
                                                                                   'anno': bibliografia.anno})
                    return render(request, "pro_planificacion/editbibliografiabasicasolicitada.html", data)
                except Exception as ex:
                    pass

            if action == 'editbibliografiacomplementariasolicitada':
                try:
                    data['title'] = u'Editar bibliografia complementaria solicitada'
                    data['bibliografia'] = bibliografia = BibliografiaComplementariaSolicitada.objects.get(
                        pk=request.GET['id'])
                    sede = None
                    if bibliografia.planificacionmateria.materia:
                        sede = bibliografia.planificacionmateria.materia.nivel.sede
                    elif bibliografia.planificacionmateria.materiacurso:
                        sede = bibliografia.planificacionmateria.materiacurso.curso.coordinacion.sede
                    else:
                        sede = bibliografia.planificacionmateria.materiacursotitulacion.curso.coordinacion.sede
                    data['sede'] = sede
                    data['form'] = SolicitarBibliografiaPlanificacionForm(initial={'digital': bibliografia.digital,
                                                                                   'titulo': bibliografia.titulo,
                                                                                   'autor': bibliografia.autor,
                                                                                   'editorial': bibliografia.editorial,
                                                                                   'anno': bibliografia.anno})
                    return render(request, "pro_planificacion/editbibliografiacomplementariasolicitada.html", data)
                except Exception as ex:
                    pass

            if action == 'editbibliografiacomplementaria':
                try:
                    data['title'] = u'Editar bibliografia complementaria'
                    data['bibliografia'] = bibliografia = BibliografiaComplementariaPlanificacion.objects.get(pk=request.GET['id'])
                    sede = None
                    if bibliografia.planificacionmateria.materia:
                        sede = bibliografia.planificacionmateria.materia.nivel.sede
                    elif bibliografia.planificacionmateria.materiacurso:
                        sede = bibliografia.planificacionmateria.materiacurso.curso.coordinacion.sede
                    else:
                        sede = bibliografia.planificacionmateria.materiacursotitulacion.curso.coordinacion.sede
                    data['sede'] = sede
                    data['form'] = BibliografiaPlanificacionForm(
                        initial={'codigo': bibliografia.codigobibliotecabibliografiacomplementaria,
                                 'digital': bibliografia.digital,
                                 'url': bibliografia.weburl,
                                 'titulo': bibliografia.bibliografiacomplementaria,
                                 'autor': bibliografia.autor,
                                 'editorial': bibliografia.editorial,
                                 'anno': bibliografia.anno,
                                 'fuente': bibliografia.fuente})
                    return render(request, "pro_planificacion/editbibliografiacomplementaria.html", data)
                except Exception as ex:
                    pass

            if action == 'addbibliografiacomplementaria':
                try:
                    data['title'] = u'Adicionar bibliografia complementaria'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    sede = None
                    if planificacionmateria.materia:
                        sede = planificacionmateria.materia.nivel.sede
                    elif planificacionmateria.materiacurso:
                        sede = planificacionmateria.materiacurso.curso.coordinacion.sede
                    else:
                        sede = planificacionmateria.materiacursotitulacion.curso.coordinacion.sede
                    data['sede'] = sede
                    data['form'] = BibliografiaPlanificacionForm()
                    return render(request, "pro_planificacion/addbibliografiacomplementaria.html", data)
                except Exception as ex:
                    pass

            if action == 'edittaller':
                try:
                    data['title'] = u'Editar taller'
                    data['taller'] = taller = TallerPlanificacionMateria.objects.get(pk=request.GET['id'])
                    data['planificacionmateria'] = planificacionmateria = taller.planificacionmateria
                    data['ultimo'] = int(null_to_numeric(
                        taller.contenidostallerplanificacionmateria_set.aggregate(valor=Max('id'))['valor'], 0)) + 1
                    if planificacionmateria.materia.asignaturamalla.malla.modelonuevo == 2:
                        data['form'] = TallerPlanificacionNuevaForm(initial={'nombretaller': taller.nombretaller,
                                                                             'resultadoaprendizaje': taller.resultadoaprendizaje,
                                                                             'recursosutilizados': taller.recursosutilizados,
                                                                             'dimensionprocedimental': taller.dimensionprocedimental,
                                                                             'productoesperado': taller.productoesperado})
                    else:
                        data['form'] = TallerPlanificacionForm(initial={'nombretaller': taller.nombretaller,
                                                                        'resultadoaprendizaje': taller.resultadoaprendizaje,
                                                                        'recursosutilizados': taller.recursosutilizados,
                                                                        'dimensionprocedimental': taller.dimensionprocedimental,
                                                                        'productoesperado': taller.productoesperado})
                    return render(request, "pro_planificacion/edittaller.html", data)
                except Exception as ex:
                    pass

            if action == 'editindicador':
                try:
                    data['title'] = u'Editar Indicador'
                    data['indicador'] = indicador = IndicadorRubrica.objects.get(pk=request.GET['id'])
                    data['taller'] = indicador.mi_rubrica().mi_taller()
                    data['form'] = IndicadoresRubricaForm(initial={'criterio': indicador.criterio,
                                                                   'logroexcelente': indicador.logroexcelente,
                                                                   'logromuybueno': indicador.logromuybueno,
                                                                   'logrobueno': indicador.logrobueno,
                                                                   'logroregular': indicador.logroregular,
                                                                   'logrodeficiente': indicador.logrodeficiente})
                    return render(request, "pro_planificacion/editindicador.html", data)
                except Exception as ex:
                    pass

            if action == 'editindicadorplanificacion':
                try:
                    data['title'] = u'Editar Indicador'
                    data['indicador'] = indicador = IndicadorRubrica.objects.get(pk=request.GET['id'])
                    data['planificacion'] = indicador.mi_rubrica().mi_planificacion()
                    data['form'] = IndicadoresRubricaForm(initial={'criterio': indicador.criterio,
                                                                   'logroexcelente': indicador.logroexcelente,
                                                                   'logromuybueno': indicador.logromuybueno,
                                                                   'logrobueno': indicador.logrobueno,
                                                                   'logroregular': indicador.logroregular,
                                                                   'logrodeficiente': indicador.logrodeficiente})
                    return render(request, "pro_planificacion/editindicadorplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'addcontenido':
                try:
                    data['title'] = u'Adicionar contenido'
                    data['taller'] = taller = TallerPlanificacionMateria.objects.get(pk=request.GET['id'])
                    data['form'] = ContenidoTallerForm()
                    return render(request, "pro_planificacion/addcontenido.html", data)
                except Exception as ex:
                    pass

            if action == 'addclase':
                try:
                    data['title'] = u'Adicionar clase'
                    data['taller'] = taller = TallerPlanificacionMateria.objects.get(pk=request.GET['id'])
                    if not taller.clasestallerplanificacionmateria_set.exists():
                        fechainicio = None
                        fechafin = None
                        if taller.planificacionmateria.materia:
                            fechainicio = taller.planificacionmateria.materia.inicio
                        elif taller.planificacionmateria.materiacurso:
                            fechainicio = taller.planificacionmateria.materiacurso.fecha_inicio
                        else:
                            fechainicio = taller.planificacionmateria.materiacursotitulacion.fecha_inicio
                    else:
                        fechainicio = taller.clasestallerplanificacionmateria_set.all().order_by('-fecha')[0].fecha
                    modelo = None
                    if taller.planificacionmateria.materia.asignaturamalla:
                        modelo = taller.planificacionmateria.materia.asignaturamalla.malla.modelonuevo
                    else:
                        modelo = taller.planificacionmateria.materia.modulomalla.malla.modelonuevo
                    if modelo == 2:
                        form = ClaseTallerNuevaForm(initial={'fecha': fechainicio,
                                                             'fechafin': fechainicio})
                        form.quitar_campos()
                    else:
                        form = ClaseTallerForm(initial={'fecha': fechainicio,
                                                        'fechafin': fechainicio})
                        form.quitar_campos()
                    form.adicionar(taller)
                    data['form'] = form
                    data['modelonuevo'] = modelo
                    return render(request, "pro_planificacion/addclase.html", data)
                except Exception as ex:
                    pass

            if action == 'editclase':
                try:
                    data['title'] = u'Editar clase'
                    data['clase'] = clase = ClasesTallerPlanificacionMateria.objects.get(pk=request.GET['id'])
                    if clase.tallerplanificacionmateria.planificacionmateria.materia.asignaturamalla.malla.modelonuevo == 2:
                        form = ClaseTallerNuevaForm(initial={'fecha': clase.fecha,
                                                             'fechafin': clase.fechafinactividades,
                                                             'contenido': clase.contenido,
                                                             'fasesactividadesarticulacion': clase.fasesactividadesarticulacion,
                                                             'actividaddoc1': clase.actividadesaprendizajecondocenciaasistida_uno,
                                                             'horas1': clase.horasdocente_uno,
                                                             'actividaddoc2': clase.actividadesaprendizajecondocenciaasistida_dos,
                                                             'horas2': clase.horasdocente_dos,
                                                             'actividadauto': clase.actividadestrabajoautonomas,
                                                             'horas4': clase.horasautonomas,
                                                             'actividadprac': clase.actividadesaprendizajepractico,
                                                             'horas5': clase.horaspracticas,
                                                             'actcondoc1': clase.actividadcontactodocente_uno,
                                                             'actcondoc2': clase.actividadcontactodocente_dos})
                        form.quitar_campos()
                    else:
                        form = ClaseTallerForm(initial={'fecha': clase.fecha,
                                                        'fechafin': clase.fechafinactividades,
                                                        'contenido': clase.contenido,
                                                        'actividaddoc1': clase.actividadesaprendizajecondocenciaasistida_uno,
                                                        'horas1': clase.horasdocente_uno,
                                                        'actividaddoc2': clase.actividadesaprendizajecondocenciaasistida_dos,
                                                        'horas2': clase.horasdocente_dos,
                                                        'actividadcol': clase.actividadesaprendizajecolaborativas,
                                                        'horas3': clase.horascolaborativas,
                                                        'actividadauto': clase.actividadestrabajoautonomas,
                                                        'horas4': clase.horasautonomas,
                                                        'actividadprac': clase.actividadesaprendizajepractico,
                                                        'horas5': clase.horaspracticas,
                                                        'actcondoc1': clase.actividadcontactodocente_uno,
                                                        'actcondoc2': clase.actividadcontactodocente_dos,
                                                        'actcolaborativas': clase.actividadaprendcolab})
                        form.quitar_campos()
                    form.editar(clase.tallerplanificacionmateria)
                    data['form'] = form
                    return render(request, "pro_planificacion/editclase.html", data)
                except Exception as ex:
                    pass

            if action == 'editcontenido':
                try:
                    data['title'] = u'Editar contenido'
                    data['contenido'] = contenido = ContenidosTallerPlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    data['taller'] = contenido.tallerplanificacionmateria
                    data['form'] = ContenidoTallerForm(initial={'contenido': contenido.contenido})
                    return render(request, "pro_planificacion/editcontenido.html", data)
                except Exception as ex:
                    pass

            if action == 'addguia':
                try:
                    data['title'] = u'Adicionar Guía Práctica'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    form = GuiaPracticaPlanificacionForm()
                    form.adicionar(planificacionmateria)
                    data['form'] = form
                    return render(request, "pro_planificacion/addguia.html", data)
                except Exception as ex:
                    pass

            if action == 'editguia':
                try:
                    data['title'] = u'Editar Guía Práctica'
                    data['guia'] = guia = GuiasPracticasMateria.objects.get(pk=request.GET['id'])
                    form = GuiaPracticaPlanificacionForm(initial={'objetivo': guia.objetivo,
                                                                  'titulo': guia.titulo,
                                                                  'taller': guia.taller,
                                                                  'tipo': guia.tipo,
                                                                  'recursos': guia.recursos,
                                                                  'equipos': guia.equipos,
                                                                  'materiales': guia.materiales,
                                                                  'materialessoftware': guia.materiales,
                                                                  'reactivos': guia.reactivos,
                                                                  'destino': guia.destino,
                                                                  'empresa': guia.empresa,
                                                                  'contactoempresa': guia.contactoempresa,
                                                                  'materialesbibliograficos': guia.materialesbibliograficos,
                                                                  'instrumentos': guia.instrumentos,
                                                                  'herramientas': guia.herramientas,
                                                                  'procedimiento': guia.procedimiento,
                                                                  'fundamentoteorico': guia.fundamentoteorico,
                                                                  'resultados': guia.resultados,
                                                                  'conclusiones': guia.conclusiones,
                                                                  'inicio': guia.inicio,
                                                                  'fin': guia.fin,
                                                                  'horas': guia.horas})
                    form.adicionar(guia.planificacionmateria)
                    data['form'] = form
                    return render(request, "pro_planificacion/editguia.html", data)
                except Exception as ex:
                    pass

            if action == 'delguia':
                try:
                    data['title'] = u'Eliminar guía práctica de la materia'
                    data['guia'] = guia = GuiasPracticasMateria.objects.get(pk=request.GET['id'])
                    data['planificacionmateria'] = planificacionmateria = guia.planificacionmateria
                    return render(request, "pro_planificacion/delguia.html", data)
                except Exception as ex:
                    pass

            if action == 'addguiacienciasbasicas':
                try:
                    data['title'] = u'Adicionar Guía de Ciencias Básicas'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(pk=request.GET['id'])
                    sede=planificacionmateria.materia.profesor_principal().distributivohoras(planificacionmateria.materia.nivel.periodo).coordinacion.sede
                    # coordinacion = planificacionmateria.materia.profesor_principal().distributivohoras(planificacionmateria.materia.nivel.periodo).coordinacion
                    coordinacion = planificacionmateria.materia.coordinacion_materia()
                    form = GuiaNuevaPracticaPlanificacionForm()
                    form.adicionar(planificacionmateria,sede,coordinacion)
                    data['form'] = form
                    return render(request, "pro_planificacion/addguiacienciasbasicas.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'addguiacienciasbasicasing':
                try:
                    data['title'] = u'Adicionar Guía de Ciencias Básicas Ingenierias'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(pk=request.GET['id'])
                    sede = planificacionmateria.materia.profesor_principal().distributivohoras(planificacionmateria.materia.nivel.periodo).coordinacion.sede
                    # coordinacion = planificacionmateria.materia.profesor_principal().distributivohoras(planificacionmateria.materia.nivel.periodo).coordinacion
                    coordinacion = planificacionmateria.materia.coordinacion_materia()
                    form = GuiaNuevaPracticaPlanificacionIngForm()
                    form.adicionar(planificacionmateria, sede, coordinacion)
                    form.listartipo()
                    data['form'] = form
                    return render(request, "pro_planificacion/addguiacienciasbasicasn.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'editguiacienciasbasicasing':
                try:
                    data['title'] = u'Editar Guía Práctica Ingenierias'
                    data['guia'] = guia = GuiasNuevaPracticasMateria.objects.get(pk=request.GET['id'])
                    coordinacion = guia.planificacionmateria.materia.profesor_principal().distributivohoras(guia.planificacionmateria.materia.nivel.periodo).coordinacion
                    sede = guia.planificacionmateria.materia.profesor_principal().distributivohoras(guia.planificacionmateria.materia.nivel.periodo).coordinacion.sede
                    form = GuiaNuevaPracticaPlanificacionIngForm(initial={'titulo': guia.titulo,
                                                                       # 'inicio': guia.inicio,
                                                                       # 'fin': guia.fin,
                                                                       # 'tipo': guia.tipo,
                                                                       'taller': guia.taller,
                                                                       'noguia': guia.noguia,
                                                                       'horas': guia.horas,
                                                                       'reactivos': guia.reactivos,
                                                                       'objetivo': guia.objetivo,
                                                                       'fundamento': guia.fundamento,
                                                                       'procedimiento': guia.procedimiento,
                                                                       'resultados': guia.resultados,
                                                                       'aprendizaje': guia.taller.resultadoaprendizaje,
                                                                       'tipopractica': guia.tipopractica,
                                                                       'reactivoslista': guia.reactivoslista.all(),
                                                                       'herramientaslista': guia.herramientaslista.all(),
                                                                       'laboratorio': guia.lugar_1.all(),
                                                                       'otros': guia.otro,
                                                                       'empresa': guia.nombreestablecimiento,
                                                                       'personacontacto': guia.personacontacto,
                                                                       'sin_lab': guia.sin_lab
                                                                       })
                    equipos=EquipoPracticaGuia.objects.filter(guia=guia)
                    data['equipos_ids'] = list(equipos.values_list('equipo_id', flat=True))
                    form.adicionar(guia.planificacionmateria, sede, coordinacion)
                    form.listartipo()
                    data['form'] = form
                    return render(request, "pro_planificacion/editguiacienciasbasicasing.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'editguiacienciasbasicas':
                try:
                    data['title'] = u'Editar Guía Práctica'
                    data['guia'] = guia = GuiasNuevaPracticasMateria.objects.get(pk=request.GET['id'])
                    coordinacion = guia.planificacionmateria.materia.profesor_principal().distributivohoras(guia.planificacionmateria.materia.nivel.periodo).coordinacion
                    sede = guia.planificacionmateria.materia.profesor_principal().distributivohoras(guia.planificacionmateria.materia.nivel.periodo).coordinacion.sede
                    form = GuiaNuevaPracticaPlanificacionForm(initial={'titulo': guia.titulo,
                                                                       # 'inicio': guia.inicio,
                                                                       # 'fin': guia.fin,
                                                                       # 'tipo': guia.tipo,
                                                                       'taller': guia.taller,
                                                                       'noguia': guia.noguia,
                                                                       'horas': guia.horas,
                                                                       'dimensionprocedimental': guia.dimensionprocedimental,
                                                                       'recursos': guia.recursos,
                                                                       'equipos': guia.equipos,
                                                                       'materiales': guia.materiales,
                                                                       'reactivos': guia.reactivos,
                                                                       'objetivo': guia.objetivo,
                                                                       'fundamento': guia.fundamento,
                                                                       'procedimiento': guia.procedimiento,
                                                                       'resultados': guia.resultados,
                                                                       'referencias': guia.referencias,
                                                                       'aprendizaje': guia.taller.resultadoaprendizaje,
                                                                       'disposiciones': guia.disposiciones,
                                                                       # 'grupo': guia.grupo,
                                                                       # 'nivelbioseguridad': guia.nivelbioseguridad,
                                                                       # 'practicas': guia.practicas,
                                                                       # 'actividades': guia.actividades,
                                                                       'emergencia': guia.emergencia,
                                                                       'refuerzo': guia.refuerzo,
                                                                       'observaciones': guia.observaciones,
                                                                       'tipopractica': guia.tipopractica,
                                                                       'reactivoslista': guia.reactivoslista.all(),
                                                                       'materialeslista': guia.materialeslista.all(),
                                                                       'suministroslista': guia.suministroslista.all(),
                                                                       'medicamentoslista': guia.medicamentoslista.all(),
                                                                       'laboratorio': guia.lugar,
                                                                       'enfermeria': guia.enfermeria,
                                                                       'medicina': guia.medicina,
                                                                       'odontologia': guia.odontologia,
                                                                       'tipoestablecimiento': guia.establecimiento,
                                                                       'establecimiento': guia.nombreestablecimiento,
                                                                       'internadoexternado': guia.internadoexternado
                                                                       })
                    equipos = EquipoPracticaGuia.objects.filter(guia=guia)
                    data['equipos_ids'] = list(equipos.values_list('equipo_id', flat=True))
                    form.adicionar(guia.planificacionmateria, sede, coordinacion)
                    data['form'] = form
                    return render(request, "pro_planificacion/editguiacienciasbasicas.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'detalleguia':
                try:
                    data['title'] = u'Detalle Guia'
                    data['guia'] = guia = GuiasNuevaPracticasMateria.objects.get(pk=request.GET['id'])
                    data['equipos'] = eqps = EquipoPracticaGuia.objects.filter(guia=guia).order_by('equipo')
                    data['reactivos'] = guia.reactivoslista.all()
                    data['materiales'] = guia.materialeslista.all()
                    data['suministros'] = guia.suministroslista.all()
                    data['medicamentos'] = guia.medicamentoslista.all()
                    data['herramientas'] = guia.herramientaslista.all()
                    data['guiassalud'] = guia.planificacionmateria.materia.carrera.id in (63, 64, 16, 119)
                    data['laboratorios']  = guia.lugar_1.all()
                    form = SuministrosPracticaGuiaForm()
                    data['form'] = form
                    data['permite_modificar'] = False
                    return render(request, "pro_planificacion/detalleguia.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'diasguia':
                try:
                    data['title'] = u'Dias a desarrollar guia'
                    data['guia'] = guia = GuiasNuevaPracticasMateria.objects.get(pk=request.GET['id'])
                    data['dias'] = guia.fechasguiasnuevapracticasmateria_set.all()
                    form = SuministrosPracticaGuiaForm()
                    data['form'] = form
                    return render(request, "pro_planificacion/diasguia.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'delguiacienciasbasicas':
                try:
                    print(request.GET['id'])
                    data['title'] = u'Eliminar guía práctica de la materia'
                    data['guia'] = guia = GuiasNuevaPracticasMateria.objects.get(pk=request.GET['id'])
                    data['planificacionmateria'] = planificacionmateria = guia.planificacionmateria
                    return render(request, "pro_planificacion/delguiacienciasbasicas.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'addguiacienciasbasicasenfermeria':
                try:
                    data['title'] = u'Adicionar Guía de Ciencias Básicas'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    form = GuiaNuevaPracticaEnfermeriaPlanificacionForm(initial={
                        'proyectoformativo': Asignatura.objects.get(pk=planificacionmateria.materia.asignatura_id)},
                    )
                    form.adicionar(planificacionmateria)
                    data['form'] = form
                    return render(request, "pro_planificacion/addguiacienciasbasicasenfermeria.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'editguiacienciasbasicasenfermeria':
                try:
                    data['title'] = u'Editar Guía Práctica'
                    data['guia'] = guia = GuiasNuevaPracticasEnfermeriaMateria.objects.get(pk=request.GET['id'])
                    form = GuiaNuevaPracticaEnfermeriaPlanificacionForm(initial={'titulo': guia.titulo,
                                                                                 'inicio': guia.inicio,
                                                                                 'fin': guia.fin,
                                                                                 'tipo': guia.tipo,
                                                                                 'taller': guia.taller,
                                                                                 'noguia': guia.noguia,
                                                                                 'horas': guia.horas,
                                                                                 'materiales': guia.materiales,
                                                                                 'equipos': guia.equipos,
                                                                                 'objetivo': guia.objetivo,
                                                                                 'fundamento': guia.fundamento,
                                                                                 'resultados': guia.resultados,
                                                                                 'referencias': guia.referencias,
                                                                                 'aprendizaje': guia.aprendizaje,
                                                                                 'disposiciones': guia.disposiciones,
                                                                                 'grupo': guia.grupo,
                                                                                 'nivelbioseguridad': guia.nivelbioseguridad,
                                                                                 'emergencia': guia.emergencia,
                                                                                 'refuerzo': guia.refuerzo,
                                                                                 'observaciones': guia.observaciones})
                    form.adicionar(guia.planificacionmateria)
                    data['form'] = form
                    return render(request, "pro_planificacion/editguiacienciasbasicasenfermeria.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'delguiacienciasbasicasenfermeria':
                try:
                    print(request.GET['id'])
                    data['title'] = u'Eliminar guía práctica de la materia'
                    data['guia'] = guia = GuiasNuevaPracticasEnfermeriaMateria.objects.get(pk=request.GET['id'])
                    data['planificacionmateria'] = planificacionmateria = guia.planificacionmateria
                    return render(request, "pro_planificacion/delguiacienciasbasicasenfermeria.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'addguiasimulacionclinica':
                try:
                    data['title'] = u'Adicionar Guía de Simulación'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    form = GuiaNuevaSimPracticaPlanificacionForm(
                        initial={'asignatura': Asignatura.objects.get(pk=planificacionmateria.materia.asignatura_id)})
                    data['form'] = form
                    return render(request, "pro_planificacion/addguiasimulacionclinica.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'editguiasimulacionclinica':
                try:
                    data['title'] = u'Editar Guía Práctica'
                    data['guia'] = guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.GET['id'])
                    form = GuiaNuevaSimPracticaPlanificacionForm(initial={'fechainicio': guia.fechainicio,
                                                                          'fechafin': guia.fechafin,
                                                                          'estudiantes': guia.estudiantes,
                                                                          'grupos': guia.grupos,
                                                                          'tipopractica': guia.tipopractica,
                                                                          'docentetec': guia.docentetec,
                                                                          'nopractica': guia.nopractica,
                                                                          'titulogeneral': guia.titulogeneral,
                                                                          'tituloespecifico': guia.tituloespecifico,
                                                                          'objetivogeneral': guia.objetivogeneral,
                                                                          'objetivosespecificos': guia.objetivosespecificos,
                                                                          'resultados': guia.resultados,
                                                                          'materialescen': guia.materialescen,
                                                                          'materialesest': guia.materialesest,
                                                                          'escenario': guia.escenario,
                                                                          'descripciongen': guia.descripciongen,
                                                                          'alergias': guia.alergias,
                                                                          'antecedentesper': guia.antecedentesper,
                                                                          'antecedentesfam': guia.antecedentesfam,
                                                                          'habitos': guia.habitos,
                                                                          'verba': guia.verba,
                                                                          'preteo': guia.preteo,
                                                                          'referencias': guia.referencias,
                                                                          'registo': guia.registo,
                                                                          'medicacion': guia.medicacion,
                                                                          'observaciones': guia.observaciones,
                                                                          'otros': guia.otros})
                    data['form'] = form
                    return render(request, "pro_planificacion/editguiasimulacionclinica.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'delguiasimulacionclinica':
                try:
                    data['title'] = u'Eliminar guía práctica de la materia'
                    data['guia'] = guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.GET['id'])
                    data['planificacionmateria'] = planificacionmateria = guia.planificacionmateria
                    return render(request, "pro_planificacion/delguiaguiasimulacionclinica.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'addexamenescomplementarios':
                try:
                    data['title'] = u'Adicionar Evolución de la Guía de Simulación'
                    data['guia'] = guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.GET['id'])
                    data['planificacionmateria'] = planificacionmateria = guia.planificacionmateria
                    form = ExamenesComplementariosPracticaPlanificacionForm()
                    data['form'] = form
                    return render(request, "pro_planificacion/addexamenescomplementarios.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'editexamenescomplementarios':
                try:
                    data['title'] = u'Editar Exmanenes complementarios de la Guía de Simulación'
                    guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.GET['id'])
                    data['examen'] = examen = \
                        ExamenesComplementariosPracticasMateria.objects.filter(guiasnuevasim=guia)[0]
                    form = ExamenesComplementariosPracticaPlanificacionForm(initial={'hb': examen.hb,
                                                                                     'htco': examen.htco,
                                                                                     'leucocitos': examen.leucocitos,
                                                                                     'neutrofilos': examen.neutrofilos,
                                                                                     'linfocitos': examen.linfocitos,
                                                                                     'eosinofilos': examen.eosinofilos,
                                                                                     'basofilos': examen.basofilos,
                                                                                     'rx': examen.rx,
                                                                                     'eco': examen.eco,
                                                                                     'tac': examen.tac,
                                                                                     'rmn': examen.rmn})
                    data['form'] = form
                    return render(request, "pro_planificacion/editexamenescomplementarios.html", data)
                except Exception as ex:
                    pass

            if action == 'delexamenescomplementarios':
                try:
                    data['title'] = u'Eliminar evolución de la guía práctica de la materia'
                    guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.GET['id'])
                    data['examen'] = ExamenesComplementariosPracticasMateria.objects.filter(guiasnuevasim=guia)[0]
                    data['planificacionmateria'] = planificacionmateria = guia.planificacionmateria
                    return render(request, "pro_planificacion/delexamenescomplementarios.html", data)
                except Exception as ex:
                    pass

            if action == 'addantropometria':
                try:
                    data['title'] = u'Adicionar Evolución de la Guía de Simulación'
                    data['guia'] = guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.GET['id'])
                    data['planificacionmateria'] = planificacionmateria = guia.planificacionmateria
                    form = AntropometriaPracticaPlanificacionForm()
                    data['form'] = form
                    return render(request, "pro_planificacion/addantropometria.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'editantropometria':
                try:
                    data['title'] = u'Editar Antropometria de la Guía de Simulación'
                    data['guia'] = guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.GET['id'])
                    data['antropometria'] = antropometria = \
                        AntropometriaPracticasMateria.objects.filter(guiasnuevasim=guia)[0]
                    form = AntropometriaPracticaPlanificacionForm(initial={'biotipo': antropometria.biotipo,
                                                                           'estadogral': antropometria.estadogral,
                                                                           'estadoconc': antropometria.estadoconc,
                                                                           'estadonutr': antropometria.estadonutr,
                                                                           'peso': antropometria.peso,
                                                                           'talla': antropometria.talla,
                                                                           'imc': antropometria.imc})
                    data['form'] = form
                    return render(request, "pro_planificacion/editantropometria.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'delantropometria':
                try:
                    data['title'] = u'Eliminar antropometria de la guía práctica de la materia'
                    data['guia'] = guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.GET['id'])
                    data['antropometria'] = AntropometriaPracticasMateria.objects.filter(guiasnuevasim=guia)[0]
                    data['planificacionmateria'] = planificacionmateria = guia.planificacionmateria
                    return render(request, "pro_planificacion/delantropometria.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'addevolucion':
                try:
                    data['title'] = u'Adicionar Evolución de la Guía de Simulación'
                    data['guia'] = guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.GET['id'])
                    data['planificacionmateria'] = planificacionmateria = guia.planificacionmateria
                    form = EvolucionSimPracticaPlanificacionForm()
                    data['form'] = form
                    return render(request, "pro_planificacion/addevolucion.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'editevolucion':
                try:
                    data['title'] = u'Editar Evolución de la Guía de Simulación'
                    data['evo'] = evo = EvolucionPracticasMateria.objects.get(pk=request.GET['id'])
                    data['guia'] = evo.guiasnuevasim
                    form = EvolucionSimPracticaPlanificacionForm(initial={'estadio': evo.estadio,
                                                                          'tiempo': evo.tiempo,
                                                                          'estadoconc': evo.estadoconc,
                                                                          'pa': evo.pa,
                                                                          'fc': evo.fc,
                                                                          't': evo.t,
                                                                          'sat': evo.sat,
                                                                          'fr': evo.fr,
                                                                          'respac': evo.respac,
                                                                          'accionsim': evo.accionsim,
                                                                          'accioncam': evo.accioncam})
                    data['form'] = form
                    return render(request, "pro_planificacion/editevolucion.html", data)
                except Exception as ex:
                    pass

            if action == 'delevolucion':
                try:
                    data['title'] = u'Eliminar evolución de la guía práctica de la materia'
                    data['evo'] = evo = EvolucionPracticasMateria.objects.get(pk=request.GET['id'])
                    data['guia'] = guia = evo.guiasnuevasim
                    data['planificacionmateria'] = planificacionmateria = guia.planificacionmateria
                    return render(request, "pro_planificacion/delevolucion.html", data)
                except Exception as ex:
                    return HttpResponseServerError(f"Error inesperado: {str(ex)}")
                    pass

            if action == 'delcontenido':
                try:
                    data['title'] = u'Eliminar contenido'
                    data['contenido'] = contenido = ContenidosTallerPlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    data['taller'] = contenido.tallerplanificacionmateria
                    return render(request, "pro_planificacion/delcontenido.html", data)
                except Exception as ex:
                    pass

            if action == 'detalletaller':
                try:
                    data['taller'] = taller = TallerPlanificacionMateria.objects.get(pk=request.GET['id'])
                    if taller.planificacionmateria.materia.asignaturamalla:
                        data['modelonuevo'] = taller.planificacionmateria.materia.asignaturamalla.malla.modelonuevo
                    else:
                        data['modelonuevo'] = taller.planificacionmateria.materia.modulomalla.malla.modelonuevo
                    data['title'] = u'Clases del taller'
                    data['planificacionmateria'] = taller.planificacionmateria
                    data['principal'] = taller.planificacionmateria.materia.es_profesor_materia_planifica(profesor)
                    return render(request, "pro_planificacion/detalletaller.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar planificación'
                    data['materia'] = PlanificacionMateria.objects.get(pk=request.GET['id'])
                    return render(request, "pro_planificacion/delete.html", data)
                except Exception as ex:
                    pass

            if action == 'delclase':
                try:
                    data['title'] = u'Eliminar clase'
                    data['clase'] = ClasesTallerPlanificacionMateria.objects.get(pk=request.GET['id'])
                    return render(request, "pro_planificacion/delclase.html", data)
                except Exception as ex:
                    pass

            if action == 'deltaller':
                try:
                    data['title'] = u'Eliminar taller de planificación'
                    data['taller'] = taller = TallerPlanificacionMateria.objects.get(pk=request.GET['id'])
                    data['planificacionmateria'] = planificacionmateria = taller.planificacionmateria
                    return render(request, "pro_planificacion/deltaller.html", data)
                except Exception as ex:
                    pass

            if action == 'delindicador':
                try:
                    data['title'] = u'Eliminar indicador'
                    data['indicador'] = indicador = IndicadorRubrica.objects.get(pk=request.GET['id'])
                    data['taller'] = indicador.mi_rubrica().mi_taller()
                    return render(request, "pro_planificacion/delindicador.html", data)
                except Exception as ex:
                    pass

            if action == 'delindicadorplanificacion':
                try:
                    data['title'] = u'Eliminar indicador planificación'
                    data['indicador'] = indicador = IndicadorRubrica.objects.get(pk=request.GET['id'])
                    data['planificacion'] = indicador.mi_rubrica().mi_planificacion()
                    return render(request, "pro_planificacion/delindicadorplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'delbibliografiabasica':
                try:
                    data['title'] = u'Eliminar bibliografia basica'
                    data['bibliografia'] = bibliografia = BibliografiaBasicaPlanificacion.objects.get(
                        pk=request.GET['id'])
                    return render(request, "pro_planificacion/delbibliografiabasica.html", data)
                except Exception as ex:
                    pass

            if action == 'delbibliografiabasicasolicitada':
                try:
                    data['title'] = u'Eliminar bibliografia basica'
                    data['bibliografia'] = bibliografia = BibliografiaBasicaSolicitada.objects.get(pk=request.GET['id'])
                    return render(request, "pro_planificacion/delbibliografiabasicasolicitada.html", data)
                except Exception as ex:
                    pass

            if action == 'delbibliografiacomplementariasolicitada':
                try:
                    data['title'] = u'Eliminar bibliografia basica'
                    data['bibliografia'] = bibliografia = BibliografiaComplementariaSolicitada.objects.get(
                        pk=request.GET['id'])
                    return render(request, "pro_planificacion/delbibliografiacomplementariasolicitada.html", data)
                except Exception as ex:
                    pass

            if action == 'delbibliografiacomplementaria':
                try:
                    data['title'] = u'Eliminar bibliografia complementaria'
                    data['bibliografia'] = bibliografia = BibliografiaComplementariaPlanificacion.objects.get(
                        pk=request.GET['id'])
                    return render(request, "pro_planificacion/delbibliografiacomplementaria.html", data)
                except Exception as ex:
                    pass

            if action == 'importarplanificacion':
                try:
                    data['title'] = u'Importacion de Planificación de materia'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    form = ImportarPlanificacionForm()
                    form.adicionar(materia, profesor, periodo)
                    data['form'] = form
                    return render(request, "pro_planificacion/importarplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'importartaller':
                try:
                    data['title'] = u'Importacion de Taller de Planificación'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    materia = planificacionmateria.materia
                    form = ImportarTallerForm()
                    form.adicionar(materia, profesor, periodo)
                    data['form'] = form
                    return render(request, "pro_planificacion/importartaller.html", data)
                except Exception as ex:
                    pass

            if action == 'importartallermed':
                try:
                    data['title'] = u'Importacion de Taller de Planificación'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    materia = planificacionmateria.materia
                    form = ImportarTallerForm()
                    form.adicionar(materia, profesor, periodo)
                    data['form'] = form
                    return render(request, "pro_planificacion/importartallermed.html", data)
                except Exception as ex:
                    pass

            if action == 'subirarchivo':
                try:
                    data['title'] = u'Subir archivo'
                    data['clase'] = clase = ClasesTallerPlanificacionMateria.objects.get(pk=request.GET['id'])
                    data['form'] = ArchivoPlanificacionForm()
                    return render(request, "pro_planificacion/subirarchivo.html", data)
                except Exception as ex:
                    pass

            if action == 'subirarchivoguia':
                try:
                    data['title'] = u'Subir archivo'
                    data['guia'] = guia = GuiasPracticasMateria.objects.get(pk=request.GET['id'])
                    data['form'] = ArchivoPlanificacionForm()
                    return render(request, "pro_planificacion/subirarchivoguia.html", data)
                except Exception as ex:
                    pass

            if action == 'observacionesbibliografia':
                try:
                    data['title'] = u' Observaciones a planificación de la materia'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    data['form'] = ObservacionesPlanoficacionForm(
                        initial={'observaciones': planificacionmateria.observacionesbiblioteca})
                    data['permite_modificar'] = False
                    return render(request, "pro_planificacion/observacionesbibliografia.html", data)
                except Exception as ex:
                    pass

            if action == 'grupospracticas':
                try:
                    data['title'] = u'Tomando la materia'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['grupospracticas'] = materia.grupospracticas_set.all()
                    data['nivel'] = materia.nivel
                    return render(request, "pro_planificacion/grupospracticas.html", data)
                except Exception as ex:
                    pass

            if action == 'tomandompracticas':
                try:
                    data['title'] = u'Tomando la Practica'
                    data['grupo'] = grupo = GruposPracticas.objects.get(pk=request.GET['id'])
                    data['materiasasignadas'] = grupo.materiaasignadagrupopracticas_set.all()
                    return render(request, "pro_planificacion/tomandompracticas.html", data)
                except Exception as ex:
                    pass

            if action == 'addgrupopractica':
                try:
                    data['title'] = u'Grupo'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['form'] = GrupoMateriaForm()
                    return render(request, "pro_planificacion/addgrupopractica.html", data)
                except Exception as ex:
                    pass

            if action == 'addestudiantegrupopractica':
                try:
                    data['title'] = u'Grupo'
                    data['grupo'] = grupo = GruposPracticas.objects.get(pk=request.GET['id'])
                    form = EstudianteGrupoPracticaForm()
                    form.materia(grupo.materia)
                    data['form'] = form
                    return render(request, "pro_planificacion/addestudiantegrupopractica.html", data)
                except Exception as ex:
                    pass

            if action == 'delestudiantegrupopractica':
                try:
                    data['title'] = u'Eliminar Grupo'
                    data['grupo'] = MateriaAsignadaGrupoPracticas.objects.get(pk=request.GET['id'])
                    return render(request, "pro_planificacion/delestudiantegrupopractica.html", data)
                except Exception as ex:
                    pass

            if action == 'delgrupopracticas':
                try:
                    data['title'] = u'Eliminar archivo o documento'
                    data['grupo'] = GruposPracticas.objects.get(pk=request.GET['id'])
                    return render(request, "pro_planificacion/delgrupopracticas.html", data)
                except Exception as ex:
                    pass

            if action == 'horashibridas':
                try:
                    data['title'] = u'Hibrida'
                    data['planificacionmateria'] = planificacionmateria = PlanificacionMateria.objects.get(
                        pk=request.GET['id'])
                    data[
                        'hibridas'] = planificacionmateria.planificacionmateriaasignaturamallahibrida_set.all().order_by(
                        'asignaturamallahibrida__modalidad')
                    return render(request, "pro_planificacion/horashibridas.html", data)
                except Exception as ex:
                    pass

            if action == 'actualizarhibridas':
                try:
                    data['title'] = u'Actualizar distributivo'
                    data['planificacionmateria'] = PlanificacionMateria.objects.get(pk=request.GET['id'])
                    return render(request, "pro_planificacion/actualizarhibridas.html", data)
                except Exception as ex:
                    pass

            if action == 'observacionesguia':
                try:
                    data['title'] = u' Observaciones a Guia Practica'
                    data['guia'] = guia = GuiasNuevaPracticasMateria.objects.get(pk=request.GET['id'])
                    data['observaciones'] = guia.observacionesguiasnuevapracticasmateria_set.all()
                    data['form'] = ObservacionesPlanoficacionForm()
                    return render(request, "pro_planificacion/observacionesguia.html", data)
                except Exception as ex:
                    pass

            if action == 'observacionesguiasim':
                try:
                    data['title'] = u' Observaciones a Guia Practica de Simulación'
                    data['guia'] = guia = GuiasNuevaSimPracticasMateria.objects.get(pk=request.GET['id'])
                    data['observaciones'] = guia.observacionesguiasnuevapracticasmateriasim_set.all()
                    data['form'] = ObservacionesPlanoficacionForm()
                    return render(request, "pro_planificacion/observacionesguiasim.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Planificación de la materia'
                data['materias'] = materia = Materia.objects.filter(
                    Q(asignaturamalla__malla__modelonuevo=0) | Q(modulomalla__malla__modelonuevo=0),
                    profesormateria__profesor=profesor, profesormateria__tipoprofesor__id=TIPO_DOCENTE_TEORIA,
                    nivel__periodo=periodo).distinct()
                data['materiasn'] = materian = Materia.objects.filter(
                    Q(asignaturamalla__malla__modelonuevo=2) | Q(modulomalla__malla__modelonuevo=2),
                    profesormateria__profesor=profesor, profesormateria__tipoprofesor__id=TIPO_DOCENTE_TEORIA,
                    nivel__periodo=periodo).distinct()
                data['practicas'] = Materia.objects.filter(grupospracticas__profesormateriapracticas__profesor=profesor,
                                                           nivel__periodo=periodo).distinct()
                data['reporte_0'] = obtener_reporte('silabo')
                data['reporte_1'] = obtener_reporte('silabonuevo')
                data['profesor'] = profesor
                data['periodo'] = periodo.id
                return render(request, "pro_planificacion/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
