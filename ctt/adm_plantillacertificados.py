# coding=utf-8
import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import last_access
from ctt.commonviews import adduserdata
from ctt.forms import PlantillaCertificadosEnLineaForm
from ctt.funciones import bad_json, log, generar_nombre, ok_json, PARAMETROS_CERTIFICADO
from ctt.models import PlantillaCertificadosEnLinea, CampoPlantillaCertificado


def _decimal_percent(valor, defecto=0):
    try:
        valor = Decimal(str(valor))
    except Exception:
        valor = Decimal(str(defecto))
    if valor < 0:
        return Decimal('0')
    if valor > 100:
        return Decimal('100')
    return valor.quantize(Decimal('0.001'))


def _campos_json(plantilla):
    if not plantilla:
        return []
    return [
        {
            'identificador': campo.identificador,
            'tipo': campo.tipo,
            'codigo': campo.codigo,
            'etiqueta': campo.etiqueta,
            'texto': campo.texto or '',
            'x': float(campo.x),
            'y': float(campo.y),
            'ancho': float(campo.ancho),
            'alto': float(campo.alto),
            'tamanio_fuente': campo.tamanio_fuente,
            'color': campo.color,
            'negrita': campo.negrita,
            'alineacion': campo.alineacion,
            'orden': campo.orden,
        }
        for campo in plantilla.campos.all().order_by('orden', 'id')
    ]



def _contexto_configuracion(request, form=None, plantilla=None):
    data = {}
    adduserdata(request, data)
    data['title'] = u'Configuracion de plantillas'
    data['plantillas'] = PlantillaCertificadosEnLinea.objects.all().order_by('nombre')
    data['plantilla'] = plantilla
    if form is None:
        form = PlantillaCertificadosEnLineaForm()
        form.adicionar(plantilla)
    data['form'] = form
    data['parametros_disponibles'] = PARAMETROS_CERTIFICADO
    data['parametros_json'] = json.dumps(PARAMETROS_CERTIFICADO)
    data['campos_json'] = json.dumps(_campos_json(plantilla))

    ancho_mm = 297
    alto_mm = 210
    if plantilla:
        ancho_mm, alto_mm = plantilla.dimensiones_mm()
        if not ancho_mm or not alto_mm:
            ancho_mm, alto_mm = 297, 210

    data['plantilla_ancho_mm'] = ancho_mm
    data['plantilla_alto_mm'] = alto_mm
    data['plantilla_aspect_ratio'] = '%.2f / %.2f' % (float(ancho_mm), float(alto_mm))
    return data

@login_required(login_url='/login')
@last_access
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'guardarplantilla':
            plantilla = None
            form = None
            try:
                if request.POST.get('id'):
                    plantilla = PlantillaCertificadosEnLinea.objects.get(pk=int(request.POST['id']))

                form = PlantillaCertificadosEnLineaForm(request.POST, request.FILES)
                form.adicionar(plantilla)
                if not form.is_valid():
                    data = _contexto_configuracion(request, form=form, plantilla=plantilla)
                    return render(request, "adm_plantillacertificados/configuracion.html", data)

                if plantilla is None:
                    plantilla = PlantillaCertificadosEnLinea()

                plantilla.nombre = form.cleaned_data['nombre']
                plantilla.tamanio_pagina = form.cleaned_data['tamanio_pagina']
                plantilla.ancho_mm = form.cleaned_data.get('ancho_mm')
                plantilla.alto_mm = form.cleaned_data.get('alto_mm')
                if form.cleaned_data.get('archivo'):
                    plantilla.archivo = form.cleaned_data['archivo']

                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("plantilla", newfile._name)

                    plantilla.archivo = newfile
                    plantilla.formato = newfile.name.split('.')[-1].upper()

                with transaction.atomic():
                    plantilla.full_clean()
                    plantilla.save()

                log(u'Guardo plantilla de certificado en linea: %s' % plantilla.nombre, request, "add")
                return HttpResponseRedirect('/adm_plantillacertificados?action=configuracion&id=%s' % plantilla.id)

            except Exception as ex:
                if form is None:
                    form = PlantillaCertificadosEnLineaForm(request.POST, request.FILES)
                    form.adicionar(plantilla)
                form.add_error(None, str(ex))
                data = _contexto_configuracion( request, form=form, plantilla=plantilla if plantilla and plantilla.pk else None)
                return render(request, "adm_plantillacertificados/configuracion.html", data)

        if action == 'agregarcampo':
            try:



                return ok_json()
            except Exception as ex:
                return bad_json(error=1, ex=ex)



        if action == 'guardarcampos':
            try:
                plantilla = PlantillaCertificadosEnLinea.objects.get(pk=int(request.POST['id']))
                campos = json.loads(request.POST.get('campos', '[]'))
                parametros_validos = PARAMETROS_CERTIFICADO
                recibidos = []

                with transaction.atomic():
                    for orden, item in enumerate(campos):
                        identificador = item.get('identificador')
                        if not identificador:
                            continue

                        tipo = item.get('tipo') if item.get('tipo') in ('parametro', 'texto') else 'parametro'
                        codigo = item.get('codigo') if tipo == 'parametro' else None
                        texto = item.get('texto') if tipo == 'texto' else ''

                        if tipo == 'parametro' and codigo not in parametros_validos:
                            continue

                        recibidos.append(identificador)

                        etiqueta = parametros_validos[codigo]['label'] if tipo == 'parametro' else (
                                    texto[:80] or 'Texto fijo')

                        campo, created = CampoPlantillaCertificado.objects.get_or_create(
                            plantilla=plantilla,
                            identificador=identificador,
                            defaults={'etiqueta': etiqueta}
                        )

                        campo.tipo = tipo
                        campo.codigo = codigo
                        campo.texto = texto
                        campo.etiqueta = etiqueta
                        campo.orden = orden
                        campo.x = _decimal_percent(item.get('x'), 0)
                        campo.y = _decimal_percent(item.get('y'), 0)
                        campo.ancho = _decimal_percent(item.get('ancho'), 40)
                        campo.alto = _decimal_percent(item.get('alto'), 8)
                        campo.tamanio_fuente = int(item.get('tamanio_fuente') or 24)
                        campo.color = item.get('color') or '#000000'
                        campo.negrita = bool(item.get('negrita'))
                        campo.alineacion = item.get('alineacion') if item.get('alineacion') in ('left', 'center',
                                                                                                'right') else 'center'
                        campo.save()

                    CampoPlantillaCertificado.objects.filter(plantilla=plantilla).exclude(
                        identificador__in=recibidos).delete()
                    plantilla.parametrizado = CampoPlantillaCertificado.objects.filter(plantilla=plantilla).exists()
                    plantilla.save()

                log(u'Configuro campos de plantilla de certificado en linea: %s' % plantilla.nombre, request, "edit")
                return ok_json()
            except Exception as ex:
                return bad_json(error=1, ex=ex)

        if action == 'eliminar':
            try:
                plantilla = PlantillaCertificadosEnLinea.objects.get(pk=int(request.POST['id']))
                nombre = plantilla.nombre
                plantilla.delete()
                log(u'Elimino plantilla de certificado en linea: %s' % nombre, request, "del")
                return ok_json()
            except Exception as ex:
                return bad_json(error=1, ex=ex)

        return bad_json(error=0)

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'configuracion':
                try:
                    plantilla = None
                    if request.GET.get('id'):
                        plantilla = PlantillaCertificadosEnLinea.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_plantillacertificados/configuracion.html",
                                  _contexto_configuracion(request, plantilla=plantilla))
                except Exception as ex:
                    return bad_json(error=3, ex=ex)

            if action == 'eliminar':
                try:
                    data['title'] = u'Eliminar plantilla'
                    data['plantilla'] = PlantillaCertificadosEnLinea.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_plantillacertificados/delete.html", data)
                except Exception as ex:
                    return bad_json(error=3, ex=ex)
        else:
            try:
                plantilla = None
                if request.GET.get('id'):
                    plantilla = PlantillaCertificadosEnLinea.objects.get(pk=int(request.GET['id']))
                return render(request, "adm_plantillacertificados/configuracion.html",
                              _contexto_configuracion(request, plantilla=plantilla))
            except Exception as ex:
                return HttpResponseRedirect('/')
