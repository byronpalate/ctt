# coding=utf-8
import random
import re
import string
from datetime import datetime

import xlrd
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render

from decorators import secure_module, last_access
from settings import ARCHIVO_TIPO_GENERAL, ARCHIVO_TIPO_NOTAS
from ctt.commonviews import adduserdata, obtener_reporte, actualizar_nota
from ctt.forms import ImportarArchivoXLSForm, ProgramaCertificadoForm, CertificadoForm, CargaMasivaCertificadosForm, \
    ConfiguracionCertificadoProgramaForm
from ctt.funciones import log, ok_json, bad_json, url_back, generar_nombre, generar_pdf_certificado_ctt, PARAMETROS_CERTIFICADO
from ctt.models import ProgramasCertificados, Certificados, Archivo, Persona, Materia, EvaluacionGenerica, \
    PlantillaCertificadosEnLinea


FUENTES_PARAMETROS_CERTIFICADO = [
    ('calculado.participante', u'Participante del programa'),
    ('calculado.cedula', u'Cédula/Identificación'),
    ('calculado.mes', u'Mes de emisión'),
    ('calculado.anio', u'Año de emisión'),
    ('calculado.fechas', u'Rango de fechas calculado'),

    ('certificado.tipo', u'Tipo Certificado'),
    ('certificado.horas', u'Horas del certificado'),
    ('certificado.codigoverificacion', u'Código de verificación'),
    ('certificado.ciudad', u'Ciudad'),

    ('programa.nombre', u'Nombre del programa'),
    ('programa.horas', u'Horas del programa'),
]

def normalize(s):
    replacements = (
        ("á", "a"),
        ("é", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ú", "u"),
        # ("ñ", "n")
    )
    for a, b in replacements:
        s = s.replace(a, b).replace(a.lower(), b.lower())
    return s

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
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addprograma':
            try:
                form = ProgramaCertificadoForm(request.POST)
                if form.is_valid():
                    programa = ProgramasCertificados(nombre=form.cleaned_data['nombre'],
                                                     tipo=form.cleaned_data['tipo'],
                                                     horas=form.cleaned_data['horas'],
                                                     inicio=form.cleaned_data['inicio'],
                                                     fin=form.cleaned_data['fin'],
                                                     modalidad=form.cleaned_data['modalidad'],
                                                     facilitador=form.cleaned_data['facilitador'],
                                                     plantilla=form.cleaned_data['plantilla'],
                                                     plantillacertificadoctt=form.cleaned_data['plantilla'],
                                                     debepagar=form.cleaned_data['debepagar'],
                                                     tipopersona=form.cleaned_data['tipopersona'])
                    programa.save()
                    log(u'Adiciono programa certificado: %s' % programa, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editprograma':
            try:
                form = ProgramaCertificadoForm(request.POST)
                if form.is_valid():
                    programa = ProgramasCertificados.objects.get(pk=request.POST['id'])
                    programa.nombre = form.cleaned_data['nombre']
                    programa.tipo = form.cleaned_data['tipo']
                    programa.horas = form.cleaned_data['horas']
                    programa.inicio = form.cleaned_data['inicio']
                    programa.fin = form.cleaned_data['fin']
                    programa.modalidad = form.cleaned_data['modalidad']
                    programa.facilitador = form.cleaned_data['facilitador']
                    programa.plantilla = form.cleaned_data['plantilla']
                    programa.plantillacertificadoctt = form.cleaned_data['plantilla']
                    programa.debepagar = form.cleaned_data['debepagar']
                    programa.tipopersona = form.cleaned_data['tipopersona']
                    programa.aprobadofinanciero = form.cleaned_data['aprobadofinanciero']
                    programa.save(request)
                    log(u'Edito programa: %s' % programa.nombre, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
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
                    workbook = xlrd.open_workbook(archivo.archivo.file.name)
                    sheet = workbook.sheet_by_index(0)
                    linea = 1
                    hoy = datetime.now().date()
                    for rowx in range(sheet.nrows):
                        if linea >= 4:
                            cols = sheet.row_values(rowx)
                            if materia.materiaasignada_set.filter(id=int(cols[0])).exists():
                                materiaasignada = materia.materiaasignada_set.filter(id=cols[0])[0]
                                numero_campo = 3
                                for campo in EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada,
                                                                               detallemodeloevaluativo__dependiente=False).distinct().order_by('detallemodeloevaluativo__orden'):
                                    try:
                                        valor = float(cols[numero_campo])
                                    except:
                                        valor = 0
                                    if valor != campo.valor:
                                        cronograma = materiaasignada.materia.cronogramacalificaciones()
                                        if cronograma:
                                            permite = campo.detallemodeloevaluativo.permite_ingreso_nota(
                                                materiaasignada, cronograma)
                                            if permite:
                                                result = actualizar_nota(request, materiaasignada=materiaasignada,
                                                                         sel=campo.detallemodeloevaluativo.nombre,
                                                                         valor=valor, rapido=True)
                                    numero_campo += 1
                        linea += 1
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addcertificado':
            try:
                form = CertificadoForm(request.POST)
                programa = ProgramasCertificados.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    if form.cleaned_data['codigo']:
                        codigo = form.cleaned_data['codigo']
                    else:
                        chars = string.ascii_uppercase + string.digits
                        codigo = ''.join(random.choice(chars) for _ in range(10))
                    if bool(form.cleaned_data['externo']):
                        persona = None
                    else:
                        persona = form.cleaned_data['persona']
                    certificado = Certificados(persona_id=persona,
                                               programa=programa,
                                               codigoverificacion=codigo,
                                               fecharegistro=datetime.today(),
                                               ciudad=form.cleaned_data['ciudad'],
                                               avalacademico=form.cleaned_data['aval'],
                                               aprobadoasistencia=form.cleaned_data['aprobadoasistencia'],
                                               tema=form.cleaned_data['tema'],
                                               trato=form.cleaned_data['trato'],
                                               externo=form.cleaned_data['externo'],
                                               nombres=form.cleaned_data['nombres'],
                                               identificacion=form.cleaned_data['identificacion'],
                                               fechainicio=form.cleaned_data['fechainicio'],
                                               fechafin=form.cleaned_data['fechafin'],
                                               horas=form.cleaned_data['horas'])
                    certificado.save()
                    log(u'Adiciono certificado: %s' % certificado, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'del':
            try:
                programa = ProgramasCertificados.objects.get(pk=request.POST['id'])
                programa.delete()
                log(u'%s elimino el programa: %s' % (persona, programa), request, "del")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delcertificado':
            try:
                certificado = Certificados.objects.get(pk=request.POST['id'])
                certificado.delete()
                log(u'%s elimino el certificado: %s' % (persona, certificado), request, "del")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cargamasiva':
            try:
                form = CargaMasivaCertificadosForm(request.POST, request.FILES)
                programa = ProgramasCertificados.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("estudiantes_", nfile._name)
                    archivo = Archivo(nombre='CERTIFICADOS',
                                      fecha=datetime.now(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save(request)
                    ciudad = form.cleaned_data['ciudad']
                    aval = form.cleaned_data['aval']
                    workbook = xlrd.open_workbook(archivo.archivo.file.name)
                    sheet = workbook.sheet_by_index(0)
                    linea = 1
                    hoy = datetime.now().date()
                    datos = {'nombres': [],
                             'cedula': [],
                             'asignacion': [],
                             'tema': []}
                    for rowx in range(sheet.nrows):
                        cols = sheet.row_values(rowx)
                        i = 0
                        if rowx == 0:
                            for col in cols:
                                col = normalize(col.encode('utf-8')).lower()
                                x = re.findall(r"\Bombr", col)
                                y = re.findall(r"\Bllido", col)
                                z = re.findall(r"\Bdula", col) or re.findall(r"\Btifica", col)
                                a = re.findall(r"\Bsigna", col)
                                b = re.findall(r"\Bema", col) or re.findall(r"\Balle", col)
                                if x:
                                    datos['nombres'].append(i)
                                if y:
                                    datos['nombres'].append(i)
                                if z:
                                    datos['cedula'].append(i)
                                if a:
                                    datos['asignacion'].append(i)
                                if b:
                                    datos['tema'].append(i)
                                i += 1
                            continue
                        if datos['cedula']:
                            try:
                                cedula = int(cols[datos['cedula'][0]])
                            except:
                                cedula = cols[datos['cedula'][0]]
                        else:
                            cedula = 9999999999

                        if Persona.objects.filter(inscripcion__persona__cedula__icontains=cedula).exists():
                            persona = Persona.objects.filter(inscripcion__persona__cedula__icontains=cedula)[0].nombre_completo_inverso()
                        else:
                            persona = u''
                            if datos['nombres']:
                                for p in list(dict.fromkeys(datos['nombres'])):
                                    persona += cols[p] +u' '

                        persona=normalize(persona.encode('utf-8')).upper().decode('utf-8')
                        aprobadoasistencia = form.cleaned_data['aprobadoasistencia']
                        if datos['asignacion']:
                            d = normalize((cols[datos['asignacion'][0]].encode('utf-8'))).lower()
                            if len(d.split()) > 1:
                                d = u'otra'
                            for x in (
                                    (1, r"\Bobad"),
                                    (2, r"\Bsisten"),
                                    (3, r"\Btra"),
                                    (4, r"\Bartici"),
                                    (5, r"\Btruct"),
                                    (6, r"\Bcilit"),
                                    (7, r"\Butor"),
                                    (8, r"\Budit")
                            ):
                                if re.findall(x[1], d):
                                    aprobadoasistencia = x[0]

                        if datos['tema']:
                            tema = cols[datos['tema'][0]]
                        else:
                            tema = ''

                        if not Certificados.objects.filter(nombres=persona, programa=programa).exists():
                            chars = string.ascii_uppercase + string.digits
                            codigo = ''.join(random.choice(chars) for _ in range(10))
                            certificado = Certificados(nombres=persona,
                                                       externo=True,
                                                       programa=programa,
                                                       codigoverificacion=codigo,
                                                       fecharegistro=datetime.now(),
                                                       ciudad=ciudad,
                                                       avalacademico=aval,
                                                       identificacion=cedula,
                                                       tema=tema,
                                                       aprobadoasistencia=aprobadoasistencia)
                            certificado.save(request)
                            log(u'Adiciono certificado: %s' % certificado, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'configuracionCertificado':
            try:
                programa = ProgramasCertificados.objects.get(pk=request.POST['id'])
                form = ConfiguracionCertificadoProgramaForm(request.POST)

                if form.is_valid():
                    programa.plantillacertificadoctt = form.cleaned_data['plantillacertificadoctt']
                    programa.save(request)
                    log(u'Configuro plantilla de certificado ctt para programa: %s' % programa, request, "edit")
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

            if action == 'registrados':
                try:
                    data['title'] = u'Participantes/Instructores Registrados'
                    data['programa'] = programa = ProgramasCertificados.objects.get(pk=request.GET['id'])
                    data['registrados'] = Certificados.objects.filter(programa=programa)
                    data['reporte'] = obtener_reporte(str(programa.plantilla))
                    data['reporte1'] = obtener_reporte("lista_registrados_certificados")
                    return render(request, "adm_emisioncertificados/registrados.html", data)
                except Exception as ex:
                    pass

            if action == 'addprograma':
                try:
                    data['title'] = u'Adicionar programa'
                    form = ProgramaCertificadoForm()
                    data['form'] = form
                    return render(request, "adm_emisioncertificados/addprograma.html", data)
                except Exception as ex:
                    pass

            if action == 'addcertificado':
                try:
                    data['title'] = u'Adicionar participante'
                    data['programa'] = ProgramasCertificados.objects.get(pk=request.GET['pid'])
                    form = CertificadoForm()
                    data['form'] = form
                    return render(request, "adm_emisioncertificados/addcertificado.html", data)
                except Exception as ex:
                    pass

            if action == 'editprograma':
                try:
                    data['title'] = u'Editar programa'
                    data['programa'] = programa = ProgramasCertificados.objects.get(pk=request.GET['id'])
                    data['form'] = ProgramaCertificadoForm(initial={'nombre': programa.nombre,
                                                                    'tipo': programa.tipo,
                                                                    'horas': programa.horas,
                                                                    'inicio': programa.inicio,
                                                                    'fin': programa.fin,
                                                                    'modalidad': programa.modalidad,
                                                                    'facilitador': programa.facilitador,
                                                                    'plantilla': programa.plantillacertificadoctt,
                                                                    'debepagar': programa.debepagar})
                    return render(request, "adm_emisioncertificados/editprograma.html", data)
                except Exception as ex:
                    pass

            if action == 'importar':
                try:
                    data['title'] = u'Importar certificados'
                    data['form'] = ImportarArchivoXLSForm()
                    return render(request, "adm_emisioncertificados/importar.html", data)
                except Exception as ex:
                    pass

            if action == 'del':
                try:
                    data['title'] = u'Eliminar Programa'
                    data['programa'] = ProgramasCertificados.objects.get(pk=request.GET['id'])
                    return render(request, "adm_emisioncertificados/del.html", data)
                except Exception as ex:
                    pass

            if action == 'delcertificado':
                try:
                    data['title'] = u'Eliminar Certificado'
                    data['certificado'] = Certificados.objects.get(pk=request.GET['id'])
                    data['programa'] = ProgramasCertificados.objects.get(pk=request.GET['pid'])
                    return render(request, "adm_emisioncertificados/delcertificado.html", data)
                except Exception as ex:
                    pass

            if action == 'cargamasiva':
                try:
                    data['title'] = u'Carga masiva'
                    data['programa'] = programa = ProgramasCertificados.objects.get(pk=request.GET['id'])
                    data['form'] = CargaMasivaCertificadosForm()
                    return render(request, "adm_emisioncertificados/cargamasiva.html", data)
                except Exception as ex:
                    pass

            #Agregado Anavas emision certificados
            if action == 'configuracionCertificado':
                try:
                    data['title'] = u'Configurar certificado'
                    data['programa'] = programa = ProgramasCertificados.objects.get(pk=request.GET['id'])
                    data['form'] = ConfiguracionCertificadoProgramaForm(initial={
                        'plantillacertificadoctt': programa.plantillacertificadoctt
                    })
                    data['plantillas'] = PlantillaCertificadosEnLinea.objects.filter(activo=True).order_by('nombre')
                    data['parametros_disponibles'] = PARAMETROS_CERTIFICADO
                    data['fuentes_parametros'] = FUENTES_PARAMETROS_CERTIFICADO
                    return render(request, "adm_plantillacertificados/configuracionparametros.html", data)
                except Exception as ex:
                    pass

            if action == 'descargarcertificadoctt':
                try:
                    certificado = Certificados.objects.get(pk=int(request.GET['id']))
                    pdf_bytes = generar_pdf_certificado_ctt(certificado)
                    response = HttpResponse(pdf_bytes, content_type='application/pdf')
                    response['Content-Disposition'] = 'attachment; filename="certificado_%s.pdf"' % certificado.codigoverificacion
                    return response
                except Exception as ex:
                    return bad_json(error=3, ex=ex)
            #Fin emision certificados

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Programas'
                data['programas'] = programas = ProgramasCertificados.objects.all()
                return render(request, "adm_emisioncertificados/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
