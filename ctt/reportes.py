# coding=utf-8
import json
import os
import subprocess
import unicodedata
from datetime import datetime

import requests
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from decorators import last_access
from settings import JR_JAVA_COMMAND, DATABASES, JR_USEROUTPUT_FOLDER, JR_RUN, MEDIA_URL, SUBREPOTRS_FOLDER, \
    MEDIA_ROOT, JR_REPORTS_USER, JR_REPORTS_PASSWORD, REPORTESEXTERNOS, URLREPORTESEXTERNOS
from ctt.commonviews import adduserdata
from ctt.funciones import bad_json, url_back, empty_json, ok_json
from ctt.models import Reporte, CategoriaReporte


# from sx.pisa3 import pisa


def tipoparametro(tipo):
    if tipo == 1:
        return "string"
    elif tipo == 2:
        return "integer"
    elif tipo == 3:
        return "double"
    elif tipo == 4:
        return "boolean"
    elif tipo == 5:
        return "integer"
    elif tipo == 6:
        return "string"
    elif tipo == 7:
        return "integer"
    return "string"


def fixparametro(tipo, valor):
    if tipo == 6:
        # FECHA
        fm = valor.index("-")
        sm = valor.index("-", fm + 1)
        d = valor[:fm]
        m = valor[fm + 1:sm]
        y = valor[sm + 1:]
        return y + "-" + m + "-" + d
    return valor


def transform(parametro, request):
    return "%s=%s:%s" % (parametro.nombre, tipoparametro(parametro.tipo), fixparametro(parametro.tipo, request.GET[parametro.nombre]))


def transform_jasperstarter(parametro, request):
    if parametro.tipo == 1 or parametro.tipo == 6:
        return '%s="%s"' % (parametro.nombre, fixparametro(parametro.tipo, request.GET[parametro.nombre]))
    else:
        return '%s=%s' % (parametro.nombre, fixparametro(parametro.tipo, request.GET[parametro.nombre]))


def elimina_tildes(cadena):
    return ''.join((c for c in unicodedata.normalize('NFD', u"%s" % cadena) if unicodedata.category(c) != 'Mn'))


def fetch_resources(uri, rel):
    return os.path.join(MEDIA_ROOT, uri.replace(MEDIA_URL, ""))


def generar_reporte(request):
    if 'n' in request.GET:
        reporte = Reporte.objects.get(nombre=request.GET['n'])
    else:
        reporte = Reporte.objects.get(pk=request.GET['rid'])
    tipo = request.GET['rt']
    output_folder = os.path.join(JR_USEROUTPUT_FOLDER, elimina_tildes(request.user.username))
    try:
        os.makedirs(output_folder)
    except Exception as ex:
        pass
    d = datetime.now()
    pdfname = reporte.nombre + d.strftime('%Y%m%d_%H%M%S')
    runjrcommand = [JR_JAVA_COMMAND, '-jar',
                    os.path.join(JR_RUN, 'jasperstarter.jar'),
                    'pr', reporte.archivo.file.name,
                    '--jdbc-dir', JR_RUN,
                    '-f', tipo,
                    '-t', 'postgres',
                    '-H', DATABASES['default']['HOST'],
                    '-n', DATABASES['default']['NAME'],
                    '-u', JR_REPORTS_USER,
                    '-p', JR_REPORTS_PASSWORD,
                    '-o', output_folder + os.sep + pdfname]
    parametros = reporte.parametros()
    paramlist = [transform_jasperstarter(p, request) for p in parametros]
    if paramlist:
        runjrcommand.append('-P')
        for parm in paramlist:
            runjrcommand.append(parm)
    else:
        runjrcommand.append('-P')
    runjrcommand.append(u'SUBREPORT_DIR=%s' % SUBREPOTRS_FOLDER)
    runjrcommand.append(u'userreport=%s' % request.user)
    mensaje = ''
    for m in runjrcommand:
        mensaje += ' ' + m
    print(mensaje)
    if REPORTESEXTERNOS:
        respuesta = requests.post(URLREPORTESEXTERNOS, data={'comando': mensaje, 'app': 'ctt', 'reporte': reporte.archivo.file.name}, timeout=300, verify=False)
        datos = json.loads(respuesta.content)
        if datos['result'] == 'ok':
            try:
                sp = os.path.split(reporte.archivo.file.name)
                if os.path.exists(output_folder + os.sep + pdfname + "." + tipo):
                    try:
                        return {'reportfile': "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo])}
                    except Exception as ex:
                        return {"result": "bad", "mensaje": u'Error al generar el reporte.', 'ruta': output_folder + os.sep + pdfname + "." + tipo}
                else:
                    print("NO EXISTE")
                    return {"result": "bad", "mensaje": u'Error al generar el reporte.', 'ruta': output_folder + os.sep + pdfname + "." + tipo}
            except Exception as ex:
                return {"result": "bad", "mensaje": u'Error al generar el reporte.', 'ruta': output_folder + os.sep + pdfname + "." + tipo}
        else:
            return {"result": "bad", "mensaje": u'Error al generar el reporte.', 'ruta': output_folder + os.sep + pdfname + "." + tipo}
    else:
        runjr = subprocess.call(mensaje, shell=True)
        sp = os.path.split(reporte.archivo.file.name)
        if os.path.exists(output_folder + os.sep + pdfname + "." + tipo):
            return {"result": "ok", "archivo": "/".join(['documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo]) , "name": (pdfname + "." + tipo), "realpath": (output_folder + os.sep + pdfname), "r": mensaje, 'reportfile': "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo])}
        else:
            return {"result": "bad", "mensaje": u'Error al generar el reporte.', 'ruta': output_folder + os.sep + pdfname + "." + tipo}


@login_required(login_url='/login')
@last_access
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'run':
                try:
                    return empty_json(generar_reporte(request))
                except Exception as ex:
                    return bad_json(mensaje=repr(ex))

            if action == 'diseno':
                try:
                    from ctt.disenoreporte import diseno
                    return diseno(request)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            data['title'] = u'Reportes'
            search = None
            categorias = []
            if 's' in request.GET:
                search = request.GET['s'].strip()
                try:
                    ids = int(search)
                except Exception as ex:
                    pass
                    ids = 0
                reportes = Reporte.objects.filter(Q(descripcion__icontains=search) | Q(id=int(ids), grupos__in=data['grupos_usuarios']), interface=False, activo=True, escertificadocurso=False).distinct().order_by('descripcion')
            else:
                reportes = Reporte.objects.filter(grupos__in=data['grupos_usuarios'], interface=False, activo=True, escertificadocurso=False).distinct().order_by('descripcion')
            for categoria in CategoriaReporte.objects.all():
                reportes_categoria = reportes.filter(categoria=categoria, grupos__in=data['grupos_usuarios'], interface=False, activo=True, escertificadocurso=False).distinct().order_by('descripcion')
                if reportes_categoria.count() > 0:
                    categorias.append({'nombre': categoria.nombre, 'reportes': reportes_categoria})
            data['categorias'] = categorias
            data['search'] = search if search else ""
            return render(request, "reportes/view.html", data)