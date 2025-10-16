# coding=utf-8
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from ctt.commonviews import adduserdata
from ctt.forms import ModeloEvaluativoForm, DetalleModeloEvaluativoForm, LogicaModeloEvaluativoForm
from ctt.funciones import log, url_back, bad_json, ok_json
from ctt.models import ModeloEvaluativo, DetalleModeloEvaluativo, null_to_numeric


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                form = ModeloEvaluativoForm(request.POST)
                if form.is_valid():
                    modelo = ModeloEvaluativo(nombre=form.cleaned_data['nombre'],
                                              fecha=datetime.now().date(),
                                              principal=form.cleaned_data['principal'],
                                              activo=form.cleaned_data['activo'],
                                              notamaxima=form.cleaned_data['notamaxima'],
                                              notaaprobar=form.cleaned_data['notaaprobar'],
                                              notarecuperacion=form.cleaned_data['notarecuperacion'],
                                              asistenciaaprobar=form.cleaned_data['asistenciaaprobar'],
                                              asistenciarecuperacion=form.cleaned_data['asistenciarecuperacion'],
                                              notafinaldecimales=form.cleaned_data['notafinaldecimales'],
                                              logicamodelo='',
                                              observaciones=form.cleaned_data['observaciones'])
                    modelo.save(request)
                    if not ModeloEvaluativo.objects.filter(principal=True).exists():
                        modelo.principal = True
                        modelo.save(request)
                    if modelo.principal:
                        for m in ModeloEvaluativo.objects.exclude(id=modelo.id):
                            m.principal = False
                            m.save(request)
                    log(u'Adicionado modelo evaluativo: %s' % modelo, request, "add")
                    return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'edit':
            try:
                form = ModeloEvaluativoForm(request.POST)
                if form.is_valid():
                    modelo = ModeloEvaluativo.objects.get(pk=request.POST['id'])
                    modelo.nombre = form.cleaned_data['nombre']
                    modelo.fecha = datetime.now().date()
                    modelo.activo = form.cleaned_data['activo']
                    modelo.principal = form.cleaned_data['principal']
                    modelo.notamaxima = form.cleaned_data['notamaxima']
                    modelo.notaaprobar = form.cleaned_data['notaaprobar']
                    modelo.notarecuperacion = form.cleaned_data['notarecuperacion']
                    modelo.asistenciaaprobar = form.cleaned_data['asistenciaaprobar']
                    modelo.asistenciarecuperacion = form.cleaned_data['asistenciarecuperacion']
                    modelo.notafinaldecimales = form.cleaned_data['notafinaldecimales']
                    modelo.observaciones = form.cleaned_data['observaciones']
                    modelo.save(request)
                    if modelo.principal:
                        for m in ModeloEvaluativo.objects.exclude(id=modelo.id):
                            m.principal = False
                            m.save(request)
                    if not ModeloEvaluativo.objects.filter(principal=True).exists():
                        modelo = ModeloEvaluativo.objects.order_by('-fecha')[0]
                        modelo.principal = True
                        modelo.save(request)
                    log(u'Modifico modelo evaluativo: %s' % modelo, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editestado':
            try:
                modelo = ModeloEvaluativo.objects.get(pk=request.POST['id'])
                if modelo.activo is True:
                    modelo.activo = False
                else :
                    modelo.activo = True
                modelo.save()
                log(u'Modifico modelo evaluativo: %s' % modelo, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'adddetalle':
            try:
                form = DetalleModeloEvaluativoForm(request.POST)
                if form.is_valid():
                    modelo = ModeloEvaluativo.objects.get(pk=request.POST['id'])
                    if modelo.detallemodeloevaluativo_set.filter(nombre=form.cleaned_data['nombre']).exists():
                        return bad_json(mensaje=u"Ya existe un campo con este nombre.")
                    if modelo.detallemodeloevaluativo_set.filter(orden=form.cleaned_data['orden']).exists():
                        return bad_json(mensaje=u"Ya existe un campo con ese número de orden.")
                    detalle = DetalleModeloEvaluativo(modelo=modelo,
                                                      nombre=form.cleaned_data['nombre'],
                                                      alternativa=form.cleaned_data['alternativa'],
                                                      notaminima=form.cleaned_data['notaminima'],
                                                      notamaxima=form.cleaned_data['notamaxima'],
                                                      decimales=form.cleaned_data['decimales'],
                                                      dependiente=form.cleaned_data['dependiente'],
                                                      dependeasistencia=form.cleaned_data['dependeasistencia'],
                                                      orden=form.cleaned_data['orden'],
                                                      determinaestadofinal=form.cleaned_data['determinaestadofinal'],
                                                      actualizaestado=form.cleaned_data['actualizaestado'])
                    detalle.save(request)
                    log(u'Adiciono detalle de modelo evaluativo: %s' % detalle, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editdetalle':
            try:
                form = DetalleModeloEvaluativoForm(request.POST)
                if form.is_valid():
                    detalle = DetalleModeloEvaluativo.objects.get(pk=request.POST['id'])
                    if DetalleModeloEvaluativo.objects.filter(modelo=detalle.modelo, nombre=detalle.nombre, alternativa=form.cleaned_data['alternativa']).exclude(id=detalle.id).exists():
                        return bad_json(mensaje=u"Ya existe un campo con esa alternativa.")
                    if DetalleModeloEvaluativo.objects.filter(modelo=detalle.modelo, orden=form.cleaned_data['orden']).exclude(id=detalle.id).exists():
                        return bad_json(mensaje=u"Ya existe un campo con ese número de orden.")
                    detalle.alternativa = form.cleaned_data['alternativa']
                    detalle.notaminima = form.cleaned_data['notaminima']
                    detalle.notamaxima = form.cleaned_data['notamaxima']
                    detalle.decimales = form.cleaned_data['decimales']
                    detalle.determinaestadofinal = form.cleaned_data['determinaestadofinal']
                    detalle.dependiente = form.cleaned_data['dependiente']
                    detalle.orden = form.cleaned_data['orden']
                    detalle.actualizaestado = form.cleaned_data['actualizaestado']
                    detalle.dependeasistencia = form.cleaned_data['dependeasistencia']
                    detalle.save(request)
                    log(u'Modifico detalle de modelo evaluativo: %s' % detalle, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delmodelo':
            try:
                modelo = ModeloEvaluativo.objects.get(pk=request.POST['id'])
                log(u"Elimino modelo evaluativo: %s" % modelo, request, "del")
                modelo.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'logica':
            try:
                modelo = ModeloEvaluativo.objects.get(pk=request.POST['id'])
                form = LogicaModeloEvaluativoForm(request.POST)
                if form.is_valid():
                    if not modelo.materia_set.exists():
                        modelo.logicamodelo = form.cleaned_data['logica']
                        modelo.save(request)
                log(u"Modifico logica calculo: %s" % modelo, request, "del")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'deldetalle':
            try:
                detalle = DetalleModeloEvaluativo.objects.get(pk=request.POST['id'])
                log(u"Elimino campo de modelo evaluativo: %s" % detalle, request, "del")
                detalle.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Nuevo modelo evaluativo'
                    data['form'] = ModeloEvaluativoForm()
                    return render(request, "adm_modelosevaluativos/add.html", data)
                except Exception as ex:
                    pass

            if action == 'adddetalle':
                try:
                    data['title'] = u'Nuevo campo del modelo evaluativo'
                    data['modelo'] = modelo = ModeloEvaluativo.objects.get(pk=request.GET['id'])
                    ultimodetalle = null_to_numeric(modelo.detallemodeloevaluativo_set.aggregate(valor=Max('orden'))['valor'], 0) + 1
                    data['form'] = DetalleModeloEvaluativoForm(initial={'orden': ultimodetalle})
                    return render(request, "adm_modelosevaluativos/adddetalle.html", data)
                except Exception as ex:
                    pass

            if action == 'detalle':
                try:
                    data['title'] = u'Detalle modelo evaluativo'
                    data['modelo'] = modelo = ModeloEvaluativo.objects.get(pk=request.GET['id'])
                    data['campos'] = modelo.detallemodeloevaluativo_set.all()
                    return render(request, "adm_modelosevaluativos/detalle.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar modelo evaluativo'
                    data['modelo'] = modelo = ModeloEvaluativo.objects.get(pk=request.GET['id'])
                    data['form'] = form = ModeloEvaluativoForm(initial={'nombre': modelo.nombre,
                                                                        'principal': modelo.principal,
                                                                        'activo': modelo.activo,
                                                                        'notamaxima': modelo.notamaxima,
                                                                        'notaaprobar': modelo.notaaprobar,
                                                                        'notarecuperacion': modelo.notarecuperacion,
                                                                        'asistenciaaprobar': modelo.asistenciaaprobar,
                                                                        'asistenciarecuperacion': modelo.asistenciarecuperacion,
                                                                        'notafinaldecimales': modelo.notafinaldecimales,
                                                                        'observaciones': modelo.observaciones})
                    return render(request, "adm_modelosevaluativos/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'editdetalle':
                try:
                    data['title'] = u'Editar campo'
                    data['detalle'] = detalle = DetalleModeloEvaluativo.objects.get(pk=request.GET['id'])
                    form = DetalleModeloEvaluativoForm(initial={'nombre': detalle.nombre,
                                                                'alternativa': detalle.alternativa,
                                                                'notaminima': detalle.notaminima,
                                                                'notamaxima': detalle.notamaxima,
                                                                'decimales': detalle.decimales,
                                                                'dependiente': detalle.dependiente,
                                                                'determinaestadofinal': detalle.determinaestadofinal,
                                                                'orden': detalle.orden,
                                                                'dependeasistencia': detalle.dependeasistencia,
                                                                'actualizaestado': detalle.actualizaestado})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_modelosevaluativos/editdetalle.html", data)
                except Exception as ex:
                    pass

            if action == 'delmodelo':
                try:
                    data['title'] = u'Eliminar modelo evaluativo'
                    data['modelo'] = ModeloEvaluativo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_modelosevaluativos/delmodelo.html", data)
                except Exception as ex:
                    pass

            if action == 'deldetalle':
                try:
                    data['title'] = u'Eliminar campo'
                    data['detalle'] = DetalleModeloEvaluativo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_modelosevaluativos/deldetalle.html", data)
                except Exception as ex:
                    pass

            if action == 'logica':
                try:
                    data['title'] = u'Fórmulas matemáticas para el cálculo del modelo'
                    data['modelo'] = modelo = ModeloEvaluativo.objects.get(pk=request.GET['id'])
                    data['form'] = LogicaModeloEvaluativoForm(initial={'logica': modelo.logicamodelo})
                    data['permite_modificar'] = not modelo.en_uso()
                    return render(request, "adm_modelosevaluativos/logica.html", data)
                except Exception as ex:
                    pass

            if action == 'editestado':
                try:
                    data['title'] = u'Cambiar el estado del modelo'
                    data['modelo'] = ModeloEvaluativo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_modelosevaluativos/editestado.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Modelos evaluativos'
                data['modelos'] = ModeloEvaluativo.objects.all()
                return render(request, "adm_modelosevaluativos/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
