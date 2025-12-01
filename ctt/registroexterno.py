# coding=utf-8
import os
import random
from datetime import datetime

from captcha.image import ImageCaptcha
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from settings import EMAIL_DOMAIN, ALUMNOS_GROUP_ID, SITE_ROOT, USA_CAPCHA, EMAIL_DOMAIN_ESTUDIANTES, \
    CARRERA_FORMACION_CONTINUA_ID, NOTA_ESTADO_EN_CURSO, CLIENTES_GROUP_ID
from ctt.commonviews import obtener_reporte
from ctt.forms import RegistroExternoForm
from ctt.funciones import convertir_fecha, bad_json, generar_nombre, generar_clave, ok_json, \
    generar_usuario, url_back, fechatope_cursos, remover_tildes
from ctt.models import Inscripcion, Persona, Sede, Capcha, Malla, CursoEscuelaComplementaria, \
    MatriculaCursoEscuelaComplementaria, \
    MateriaAsignadaCurso, TipoEstudianteCurso, CostodiferenciadoCursoPeriodo, \
    PorcentajeDescuentoCursos, Cliente, EmpresaEmpleadora
from ctt.tasks import send_mail


@transaction.atomic()
def view(request):
    if "persona" in request.session:
        return HttpResponseRedirect("/")
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == "inicializacion":
                try:
                    screensize = request.POST['screensize']
                    request.session['screenwidth'] = int(screensize.split('x')[0])
                    return ok_json()
                except Exception as ex:
                    return bad_json(error=5)

            if action == 'registro':
                try:
                    form = RegistroExternoForm(request.POST)
                    if form.is_valid():
                        cedula = form.cleaned_data['cedula'].strip()
                        pasaporte = form.cleaned_data['pasaporte'].strip()
                        if not cedula and not pasaporte:
                            return bad_json(mensaje=u"Debe ingresar una identificación.")
                        if cedula:
                            if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).exists():
                                return bad_json(mensaje=u"Existe una persona registrada con esta identificación. Ingrese con sus datos ya creados")
                        if pasaporte:
                            if Persona.objects.filter(Q(cedula=pasaporte) | Q(pasaporte=pasaporte)).exists():
                                return bad_json(mensaje=u"Existe una persona registrada con esta identificación. Ingrese con sus datos ya creados")
                        personacliente = Persona(nombre1=remover_tildes(form.cleaned_data['nombre1']),
                                                 nombre2=remover_tildes(form.cleaned_data['nombre2']),
                                                 apellido1=remover_tildes(form.cleaned_data['apellido1']),
                                                 apellido2=remover_tildes(form.cleaned_data['apellido2']),
                                                 cedula=remover_tildes(cedula),
                                                 pasaporte=pasaporte,
                                                 sexo=form.cleaned_data['sexo'],
                                                 direccion=remover_tildes(form.cleaned_data['direccion']),
                                                 telefono=remover_tildes(form.cleaned_data['telefono']),
                                                 email=form.cleaned_data['email'])
                        personacliente.save(request)
                        cliente = Cliente(persona=personacliente,
                                          personacontacto=form.cleaned_data['personacontacto'],
                                          telefonocontacto=form.cleaned_data['telefonocontacto'],
                                          emailcontacto=form.cleaned_data['emailcontacto'],
                                          activo=True)
                        cliente.save(request)
                        generar_usuario(persona=personacliente, group_id=CLIENTES_GROUP_ID)
                        personacliente.crear_perfil(cliente=cliente)
                        if form.cleaned_data['empresa']:
                            ruc = form.cleaned_data['ruc'].strip()
                            nombreempresa = form.cleaned_data['nombreempresa'].strip()
                            if not EmpresaEmpleadora.objects.filter(ruc=ruc).exists():
                                empresa = EmpresaEmpleadora(nombre=nombreempresa,
                                                            ruc=ruc,
                                                            direccion=form.cleaned_data['direccionempresa'].strip(),
                                                            celular=form.cleaned_data['telefonoempresa'].strip()
                                                            )
                                empresa.save()
                                cliente.empresa = empresa
                                cliente.save()
                            else:
                                empresaexiste = EmpresaEmpleadora.objects.get(ruc=ruc)
                                cliente.empresa = empresaexiste
                                cliente.save()

                        send_mail(subject='Registro completo CTT Indoamerica.',
                                  html_template='emails/registrook.html',
                                  data={'cliente': cliente},
                                  recipient_list=[cliente.persona],
                                  correos=cliente.correo_de_envio())

                        return ok_json({"id": cliente.id})
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'registro':
                try:
                    data = {'title': u'Formulario de Inscripción',
                            'currenttime': datetime.now(),
                            'especial': True}
                    form = RegistroExternoForm()
                    data['form'] = form
                    data['reporte_1'] = obtener_reporte('ficha_inscripcion')
                    data['email_domain'] = EMAIL_DOMAIN
                    data['email_domain_estudiante'] = EMAIL_DOMAIN_ESTUDIANTES
                    data['permite_modificar'] = True
                    data['currenttime'] = datetime.now()
                    data['especial'] = True
                    return render(request, "registroexterno/registro.html", data)
                except Exception as ex:
                    pass

            if action == 'registrook':
                try:
                    data = {'title': u'Registro Exitoso'}
                    return render(request, "registroexterno/registrook.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data = {'title': u'Cursos de formación',
                        "background": random.randint(1, 6),
                        'currenttime': datetime.now(),
                        'especial': True}
                return render(request, "registroexterno/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
