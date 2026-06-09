# coding=utf-8
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from settings import RUBRO_OTRO_EXAMEN_UBICACION_ID, TIPO_IVA_0_ID
from ctt.commonviews import adduserdata
from ctt.forms import ArchivoListadoAprobadosExamenComplexivoForm
from ctt.funciones import log, bad_json, ok_json, url_back, generar_nombre, \
    fechatope_examenubicacion_ingles
from ctt.models import ConvocatoriaExamenSuficiencia, ProcesoAplicanteExamenSuficiencia, \
    RequisitosProcesoAplicanteSuficiencia, \
    TipoSolicitudSecretariaDocente, \
    null_to_numeric, Rubro, RubroOtro, DetalleConvocatoriaExamenSuficiencia, \
    RequisitosDetalleConvocatoriaExamenSuficiencia


def validar_inscripcion_convocatoria(inscripcion, convocatoria):
    if convocatoria.coordinacion.exists() and not convocatoria.coordinacion.filter(id=inscripcion.coordinacion_id).exists():
        return u'Usted no pertenece a la facultad designada para esta convocatoria.'

    if convocatoria.modalidad.exists() and not convocatoria.modalidad.filter(id=inscripcion.modalidad_id).exists():
        return u'Usted no pertenece a la modalidad designada para esta convocatoria.'

    if convocatoria.sede_id and inscripcion.sede_id != convocatoria.sede_id:
        return u'Usted no pertenece a la sede designada para esta convocatoria.'

    return None


def crear_registro_examen_ingles(inscripcion, proceso, request):
    if proceso.registro(inscripcion):
        return None

    hoy = datetime.now().date()
    tipo = TipoSolicitudSecretariaDocente.objects.get(pk=57)
    registro = ProcesoAplicanteExamenSuficiencia(
        convocatoria=proceso,
        inscripcion=inscripcion,
        fechaaplicacion=datetime.today(),
        promedionotas=0,
        fechatope=fechatope_examenubicacion_ingles(hoy, inscripcion)
    )
    registro.save(request)

    for actividad in proceso.detalleconvocatoriaexamensuficiencia_set.all():
        for requisito in actividad.requisitosdetalleconvocatoriaexamensuficiencia_set.all():
            RequisitosProcesoAplicanteSuficiencia(proceso=registro, requisito=requisito).save(request)

    valor = null_to_numeric(tipo.valor + tipo.costo_base, 2)
    rubro = Rubro(
        inscripcion=inscripcion,
        valor=valor,
        iva_id=TIPO_IVA_0_ID,
        valortotal=valor,
        saldo=valor,
        periodo=proceso.periodo,
        fecha=hoy,
        fechavence=hoy
    )
    rubro.save(request)
    RubroOtro(rubro=rubro, tipo_id=RUBRO_OTRO_EXAMEN_UBICACION_ID).save(request)
    rubro.actulizar_nombre('EXAMEN DE ' + proceso.tipoconvocatoria.nombrerubro + ' DE INGLES')
    return registro


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
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'subir':
            try:
                form = ArchivoListadoAprobadosExamenComplexivoForm(request.POST, request.FILES)
                if form.is_valid():
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("documentopostulacionidiomas_", newfile._name)

                    requisito = RequisitosDetalleConvocatoriaExamenSuficiencia.objects.get(pk=request.POST['id'])
                    aplicante = ProcesoAplicanteExamenSuficiencia.objects.get(pk=request.POST['aplicante'])
                    archivo = RequisitosProcesoAplicanteSuficiencia.objects.filter(proceso=aplicante,requisito=requisito).first()
                    if not archivo:
                        archivonuevo=RequisitosProcesoAplicanteSuficiencia(proceso=aplicante,
                                                                           requisito=requisito,
                                                                           archivo=newfile)
                        archivonuevo.save()
                    else:
                        archivo.archivo = newfile
                        archivo.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'registrarse':
            try:
                proceso = ConvocatoriaExamenSuficiencia.objects.get(pk=request.POST['id'])
                mensaje = validar_inscripcion_convocatoria(inscripcion, proceso)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                registro = crear_registro_examen_ingles(inscripcion, proceso, request)
                if registro:
                    log(u'Registro de estudiante a convocarotia de ingles: %s' % registro.inscripcion, request, "add")
                return ok_json()
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
                    data['requisito'] = requisito =RequisitosDetalleConvocatoriaExamenSuficiencia.objects.get(pk=request.GET['id'])
                    data['aplicante'] = ProcesoAplicanteExamenSuficiencia.objects.filter(inscripcion=inscripcion,convocatoria=requisito.detalleproceso.convocatoriaconsultorio).first()
                    data['form'] = ArchivoListadoAprobadosExamenComplexivoForm()
                    return render(request, "alu_postulacionexamensuficiencia/subir.html", data)
                except Exception as ex:
                    pass

            if action == 'registrarse':
                try:
                    data['title'] = u'Registrarse en el proceso'
                    data['proceso'] = proceso = ConvocatoriaExamenSuficiencia.objects.get(pk=request.GET['id'])
                    if datetime.today().date() > proceso.fechafin:
                        return HttpResponseRedirect('/alu_postulacionexamensuficiencia')
                    data['detalles'] = proceso.detalleconvocatoriaexamensuficiencia_set.all().order_by('inicio','fin')
                    return render(request, "alu_postulacionexamensuficiencia/aplicar.html", data)
                except Exception as ex:
                    pass

            if action == 'registro':
                try:
                    data['title'] = u'Registro para examen de suficiencia'
                    registro = None
                    data['proceso'] = proceso = ConvocatoriaExamenSuficiencia.objects.get(pk=request.GET['id'])
                    registro = proceso.registro(inscripcion) #Consulta si tiene un registro y si no lo tiene lo crea
                    if not registro:
                        return HttpResponseRedirect('/alu_postulacionexamensuficiencia')
                    data['requisitos'] = RequisitosDetalleConvocatoriaExamenSuficiencia.objects.filter(detalleproceso__convocatoriaconsultorio = proceso)
                    data['detalles'] = proceso.detalleconvocatoriaexamensuficiencia_set.all()
                    data['registro'] = registro
                    data['inscripcion'] = inscripcion
                    data['actividad_evaluacion'] = DetalleConvocatoriaExamenSuficiencia.objects.filter(convocatoriaconsultorio=proceso)[0] if DetalleConvocatoriaExamenSuficiencia.objects.filter(convocatoriaconsultorio=proceso).exists() else False
                    return render(request, "alu_postulacionexamensuficiencia/registro.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Procesos de postulación a la suficiencia de ingles'
                fecha = datetime.now().date()
                data['procesos'] = proceso = ConvocatoriaExamenSuficiencia.objects.filter(fechainicio__lte=fecha,
                                                                                          fechafin__gte=fecha, activo=True,
                                                                                          modalidad=inscripcion.modalidad,
                                                                                          sede=inscripcion.sede,
                                                                                          coordinacion=inscripcion.coordinacion).distinct()
                data['inscripcion'] = inscripcion
                return render(request, "alu_postulacionexamensuficiencia/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
