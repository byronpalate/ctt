# coding=utf-8
import json
import urllib
from datetime import datetime
from itertools import chain

import requests
import urllib.request
import urllib.parse
import urllib3.exceptions

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import get_template

from decorators import secure_module, last_access
from settings import PAYMENT_ENTITYID, PAYMENT_URL, PERMITE_PAGO_ONLINE, \
    MID, TID, TIPO_IVA_0_ID, URL_APP_DATAFAST, PAGO_TARJETA_NACIONAL_ID, OTROS_BANCOS_EXTERNOS_ID, ACCESO_TOKEN, \
    LUGAR_RECAUDACION_TARJETA_ID, PAGO_MINIMO_DIFERIDO_TARJETA, SCRIPT_URL, PAGO_MINIMO_TARJETA, \
    PROVEEDOR_PAGOONLINE_PAYPHONE, FORMA_PAGO_TARJETA
from ctt.commonviews import adduserdata, obtener_reporte
from ctt.funciones import generar_nombre, log, ok_json, bad_json, url_back, remover_caracteres_especiales, \
    remover_tildes
from ctt.models import Rubro, mi_institucion, Banco, \
    LugarRecaudacion, null_to_numeric, Pago, Factura, ReciboPago


def paymentrequest(request, extradata, autorizaciondatafast):
    url = PAYMENT_URL
    ip = '205.204.89.46'
    iva = '004012' + ('%.2f' % extradata['iva']).replace('.', '').zfill(12)
    base0 = '052012' + ('%.2f' % extradata['subtotal_0']).replace('.', '').zfill(12)
    base12 = '053012' + ('%.2f' % extradata['subtotal_12']).replace('.', '').zfill(12)
    clientefacturacion = autorizaciondatafast.cliente.clientefacturacion(request)
    if len(clientefacturacion.identificacion) > 10:
        identificacion = clientefacturacion.identificacion[:10]
    else:
        identificacion = clientefacturacion.identificacion
    data = {
        'entityId': PAYMENT_ENTITYID,
        'amount': '%.2f' % extradata['total'],
        'currency': 'USD',
        'paymentType': 'DB',
        'customer.givenName': u'%s' % remover_caracteres_especiales(autorizaciondatafast.cliente.persona.nombres()),
        'customer.middleName': u'%s' % remover_caracteres_especiales(autorizaciondatafast.cliente.persona.apellido1),
        'customer.surname': u'%s' % remover_caracteres_especiales(autorizaciondatafast.cliente.persona.apellido2),
        'customer.ip': u'%s' % ip,
        'customer.merchantCustomerId': u'%s' % autorizaciondatafast.cliente.id,
        'merchantTransactionId': u'%s' % autorizaciondatafast.id,
        'customer.email': u'%s' % remover_caracteres_especiales(clientefacturacion.email),
        'customer.identificationDocType': u'IDCARD',
        'customer.identificationDocId': u'%s' % identificacion,
        'customer.phone': u'%s' % clientefacturacion.telefono,

        'cart.items[0].name': 'SERVICIOS EDUCATIVOS',
        'cart.items[0].description': 'SERVICIOS EDUCATIVOS',
        'cart.items[0].price': '%.2f' % extradata['total'],
        'cart.items[0].quantity': '1',

        'shipping.street1': u'%s' % remover_caracteres_especiales(clientefacturacion.direccion),
        'billing.street1': u'%s' % remover_caracteres_especiales(clientefacturacion.direccion),
        'shipping.country': u'EC',
        'billing.country': u'EC',

        # 'testMode': 'EXTERNAL',
        'risk.parameters[USER_DATA2]': 'UTI',
        'customParameters[%s_%s]' % (MID, TID): '%s%s%s%s%s%s' % ('0081', '0030070103910', '05100817913101', iva, base0, base12)
    }
    try:
        # opener = urllib2.build_opener(urllib2.HTTPHandler)
        opener = urllib.request.build_opener(urllib.request.HTTPHandler)
        # request = urllib2.Request(url, data=urllib.urlencode(data))
        f = urllib.parse.urlencode(data)
        f = f.encode('utf-8')
        request = urllib.request.Request(url, f)
        request.add_header('Authorization', 'Bearer %s' % ACCESO_TOKEN)
        request.get_method = lambda: 'POST'
        response = opener.open(request)
        return json.loads(response.read())
    except Exception as ex:
        return None


def paymentrequest_payphone(request, extradata, autorizacionpayphone):
    procesador = ProcesadorPagoTarjeta.objects.get(pk=PROVEEDOR_PAGOONLINE_PAYPHONE)
    data = {
        'Amount': ('%.2f' % null_to_numeric(extradata['total'], 2)).replace('.', ''),
        'AmountWithoutTax': ('%.2f' % null_to_numeric(extradata['subtotal_0'], 2)).replace('.', ''),
        'AmountWithTax': ('%.2f' % null_to_numeric(extradata['subtotal_12'], 2)).replace('.', ''),
        'Tax': ('%.2f' % null_to_numeric(extradata['iva'], 2)).replace('.', ''),
        'Currency': 'USD',
        'clientTransactionId': autorizacionpayphone.id,
        'ResponseUrl': procesador.urlretorno,
    }
    try:
        cabeceras = {"authorization": "Bearer %s" % procesador.mid}
        respuesta = requests.post(procesador.paymenturl, headers=cabeceras, data=data, verify=False)
        data = json.loads(respuesta._content)
        return data
    except Exception as e:
        return None


def statuspaymentrequest(autorizaciondatafast):
    try:
        url = PAYMENT_URL + "/" + autorizaciondatafast + "/payment"
        url += '?entityId=' + PAYMENT_ENTITYID
        try:
            # opener = urllib2.build_opener(urllib2.HTTPHandler)
            opener = urllib.request.build_opener(urllib.request.HTTPHandler)
            # request = urllib2.Request(url, data='')
            request = urllib.request.Request(url, data=b'')
            request.add_header('Authorization', 'Bearer %s' % ACCESO_TOKEN)
            request.get_method = lambda: 'GET'
            response = opener.open(request)
            return json.loads(response.read())
        except urllib3.exceptions.HTTPError as e:
            return e.code
    except Exception as ex:
        return None


def statuspaymentrequest_payphone(autorizacionpayphone):
    try:
        procesador = ProcesadorPagoTarjeta.objects.get(pk=PROVEEDOR_PAGOONLINE_PAYPHONE)
        cabeceras = {"authorization": "Bearer %s" % procesador.mid}
        data = {
            'id': autorizacionpayphone.idautorizacion,
        }
        respuesta = requests.post(procesador.scripturl, headers=cabeceras, data=data, verify=False)
        data = json.loads(respuesta._content)
        return data
    except:
        return None


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
    data['cliente'] = cliente = perfilprincipal.cliente
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'adddeposito':
                try:
                    form = DepositoclienteForm(request.POST, request.FILES)
                    if form.is_valid():
                        persona = request.session['persona']
                        if 'archivo' not in request.FILES:
                            return bad_json(mensaje=u"Debe subir el documento en formato PNG o JPG.")
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("deposito_", newfile._name)
                        if form.cleaned_data['ventanilla'] == False and form.cleaned_data['movilweb'] == False:
                            return bad_json(mensaje=u'Debes seleccionar al menos una opción (Ventanilla o Móvil/Web).')
                        if Depositocliente.objects.filter(cuentabanco=form.cleaned_data['cuentabanco'], fecha=form.cleaned_data['fecha'], referencia=form.cleaned_data['referencia'], ventanilla=True if form.cleaned_data['ventanilla'] else False).exists():
                            return bad_json(mensaje=u'Ya existe ese número de referencia ingresado')
                        deposito = Depositocliente(cliente=cliente,
                                                       fecha=form.cleaned_data['fecha'],
                                                       ventanilla=True if form.cleaned_data['ventanilla'] else False,
                                                       movilweb=True if form.cleaned_data['movilweb'] else False,
                                                       deposito=True if form.cleaned_data['ventanilla'] else False,
                                                       referencia=form.cleaned_data['referencia'],
                                                       cuentabanco=form.cleaned_data['cuentabanco'],
                                                       valor=form.cleaned_data['valor'],
                                                       motivo=form.cleaned_data['motivo'],
                                                       archivo=newfile,
                                                       procesado=False,
                                                       estadoprocesado=3)
                        deposito.save(request)
                        from ctt.ocr.deposito_ocr import procesar_deposito_imagen
                        try:

                            # después de deposito.save(request)
                            print(">>> Llamando OCR…", flush=True)
                            deposito, dbg = procesar_deposito_imagen(deposito, return_debug=True)
                            print(">>> OCR DEBUG JSON >>>", flush=True)
                            print(json.dumps(dbg, ensure_ascii=False, indent=2), flush=True)
                            print(">>> FIN OCR DEBUG <<<", flush=True)
                        except Exception as e:
                            transaction.set_rollback(True)
                            return bad_json(mensaje=f"OCR error: {e}")

                        log(u'Adiciono deposito de cliente: %s' % deposito, request, "add")
                        return ok_json()

                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'observaciones':
                try:
                    data = {}
                    data['deposito'] = deposito = Depositocliente.objects.get(pk=int(request.POST['id']))
                    template = get_template("cli_finanzas/observaciones.html")
                    json_content = template.render(data)
                    return ok_json({'html': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=3, ex=ex)

            if action == 'del':
                try:
                    deposito = Depositocliente.objects.get(pk=request.POST['id'])
                    if deposito.procesado or deposito.pago_set.exists():
                        return bad_json(mensaje=u'No puede eliminar el registro ya fue procesado.')
                    log(u"Elimino deposito: %s" % deposito, request, "del")
                    deposito.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'act_valor_autorizacion':
                try:
                    td = True if request.POST['td'] == 'true' else False
                    datos = json.loads(request.POST['lista_items1'])
                    if len(request.POST['identificacion']) > 10:
                        identificacion = request.POST['identificacion'][:10]
                    else:
                        identificacion = request.POST['identificacion']
                    nd = False
                    for d in datos:
                        r = Rubro.objects.get(id=int(d['id']))
                        nd = True if r.es_notadebito() else False
                    if not nd:
                        clientefacturacion = cliente.clientefacturacion(request)
                        clientefacturacion.identificacion = remover_tildes(request.POST['identificacion'])
                        clientefacturacion.tipo = tipo = int(request.POST['tipoidentificacion'])
                        clientefacturacion.nombre = nombre = remover_tildes(request.POST['nombre'])
                        clientefacturacion.direccion = direccion = remover_tildes(request.POST['direccion'])
                        clientefacturacion.telefono = telefono = remover_tildes(request.POST['telefono'])
                        clientefacturacion.email = email = request.POST['email']
                        clientefacturacion.save()
                    else:
                        identificacion = remover_tildes(cliente.persona.identificacion())
                        tipo = cliente.persona.tipo_identificacion_comprobante()
                        nombre = remover_tildes(cliente.persona.nombre_completo())
                        direccion = remover_tildes(cliente.persona.mi_direccion())
                        telefono = remover_tildes(cliente.persona.mi_telefono())
                        email = cliente.persona.mi_email()
                    if AutorizacionDatafast.objects.filter(cliente=cliente, activo=True).exists():
                        AutorizacionDatafast.objects.filter(cliente=cliente, activo=True).update(activo=False)
                    a = AutorizacionDatafast(cliente=cliente,
                                             autorizacion='',
                                             solicitud='',
                                             respuesta='',
                                             fecha=datetime.now(),
                                             valortotal=0,
                                             identificacion=request.POST['identificacion'],
                                             tipo=tipo,
                                             nombre=nombre,
                                             direccion=direccion,
                                             telefono=telefono,
                                             email=email,
                                             tienedescuento=td)
                    a.save()
                    a.valortotal = float(request.POST['valort'])
                    a.save()
                    iva = 0
                    sub0 = 0
                    subiva = 0
                    for d in datos:
                        r = Rubro.objects.get(id=int(d['id']))
                        valor = float(d['valor'])
                        if r.iva_id == TIPO_IVA_0_ID:
                            sub0 += valor
                        else:
                            subiva += valor
                            iva += null_to_numeric(valor - (valor / float(1 + r.iva.porcientoiva)), 2)
                    if float(request.POST['valort']) > 0:
                        sub0 = float(request.POST['valort'])
                    data['iva'] = iva
                    data['subtotal_0'] = sub0
                    data['subtotal_12'] = subiva - iva
                    data['total'] = a.valortotal
                    autorizacion = paymentrequest(request, extradata=data, autorizaciondatafast=a)
                    if autorizacion:
                        if autorizacion['result']['code'] == '000.200.100':
                            a.solicitud = autorizacion
                            a.autorizacion = autorizacion['id']
                            a.save()
                            for d in datos:
                                r = Rubro.objects.get(id=int(d['id']))
                                d = DetalleAutorizacionDatafast(autorizaciondatafast=a,
                                                                rubro=r,
                                                                valor=float(d['valor']))
                                d.save()
                            data['bancos'] = Banco.objects.all().exclude(id=89)
                            data['tipotarjeta'] = TipoTarjeta.objects.all()
                            data['tipo'] = TipoTarjetaBanco.objects.all()
                            data['pago_tarjeta_nacional_id'] = PAGO_TARJETA_NACIONAL_ID
                            data['otros_bancos_externos_id'] = OTROS_BANCOS_EXTERNOS_ID
                            data['permite_diferir'] = PAGO_MINIMO_DIFERIDO_TARJETA <= d.autorizaciondatafast.valortotal
                            template = get_template("cli_finanzas/otrosdatos.html")
                            json_content = template.render(data)
                            return ok_json(data={'procede': True, 'autorizacion': a.autorizacion, 'datosextra': json_content})
                    return ok_json(data={'procede': False})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(extradata={'procede': False, 'errordatafast': ex.message})

            if action == 'act_valor_autorizacion_payphone':
                try:
                    td = True if request.POST['td'] == 'true' else False
                    if 'autorizacion' in request.session:
                        del request.session['autorizacion']
                    datos = json.loads(request.POST['lista_items1'])
                    nd = False
                    for d in datos:
                        r = Rubro.objects.get(id=int(d['id']))
                        nd = True if r.es_notadebito() else False
                    if not nd:
                        clientefacturacion = cliente.clientefacturacion(request)
                        clientefacturacion.ruc = identificacion = request.POST['identificacion']
                        clientefacturacion.tipo = tipo = int(request.POST['tipoidentificacion'])
                        clientefacturacion.nombre = nombre = request.POST['nombre']
                        clientefacturacion.direccion = direccion = request.POST['direccion']
                        clientefacturacion.telefono = telefono = request.POST['telefono']
                        clientefacturacion.email = email = request.POST['email']
                        clientefacturacion.save(request)
                    else:
                        identificacion = cliente.persona.identificacion()
                        tipo = cliente.persona.tipo_identificacion_comprobante()
                        nombre = cliente.persona.nombre_completo()
                        direccion = cliente.persona.mi_direccion()
                        telefono = cliente.persona.mi_telefono()
                        email = cliente.persona.mi_email()
                    if AutorizacionPayPhone.objects.filter(cliente=cliente, activo=True).exists():
                        AutorizacionPayPhone.objects.filter(cliente=cliente, activo=True).update(activo=False)
                    procesador = ProcesadorPagoTarjeta.objects.get(pk=PROVEEDOR_PAGOONLINE_PAYPHONE)
                    a = AutorizacionPayPhone(cliente=cliente,
                                             autorizacion='',
                                             solicitud='',
                                             respuesta='',
                                             fecha=datetime.now(),
                                             valortotal=0,
                                             valorextra=procesador.comision,
                                             identificacion=identificacion,
                                             tipo=tipo,
                                             nombre=nombre,
                                             direccion=direccion,
                                             telefono=telefono,
                                             email=email,
                                             tienedescuento=td)
                    a.save(request)
                    a.valortotal = float(request.POST['valort'])
                    a.save(request)
                    iva = 0
                    sub0 = 0
                    subiva = 0
                    for d in datos:
                        r = Rubro.objects.get(id=int(d['id']))
                        valor = float(d['valor'])
                        if r.iva_id == TIPO_IVA_0_ID:
                            sub0 += valor
                        else:
                            subiva += valor
                            iva += null_to_numeric(valor - (valor / float(1 + r.iva.porcientoiva)), 2)
                    if float(request.POST['valort']) > 0:
                        sub0 = float(request.POST['valort'])
                    data['iva'] = iva
                    data['subtotal_0'] = sub0 + a.valorextra
                    data['subtotal_12'] = null_to_numeric(subiva - iva, 2)
                    data['total'] = a.valortotal
                    autorizacion = paymentrequest_payphone(request, extradata=data, autorizacionpayphone=a)
                    if autorizacion:
                        if 'paymentId' in autorizacion:
                            a.solicitud = autorizacion
                            a.autorizacion = autorizacion['paymentId']
                            a.save()
                            for d in datos:
                                r = Rubro.objects.get(id=int(d['id']))
                                d = DetalleAutorizacionPayPhone(autorizacionpayphone=a,
                                                                rubro=r,
                                                                valor=float(d['valor']))
                                d.save()
                            request.session['autorizacion'] = a.autorizacion
                            url = '/cli_finanzas'
                            if 'payWithCard' in autorizacion:
                                url = autorizacion['payWithCard']
                            elif 'payWithPayPhone' in autorizacion:
                                url = autorizacion['payWithPayPhone']
                            return ok_json(data={'procede': True, 'autorizacion': a.autorizacion, 'url': url})
                    return ok_json(data={'procede': False, 'data': autorizacion, 'solicitud': autorizacion['message']})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(extradata={'procede': False, 'errormensaje': ex.message})

            if action == 'permitediferir':
                try:
                    banco = Banco.objects.get(pk=request.POST['id'])
                    tipotarjetabanco = TipoTarjetaBanco.objects.get(pk=request.POST['idtb'])
                    tipotarjeta = TipoEmisorTarjeta.objects.filter(codigodatafast=request.POST['idt'])[0]
                    lista = []
                    for i in banco.mi_diferido(tipotarjeta, tipotarjetabanco):
                        lista.append([i.valordatafast, '1' if i.intereses else '0', '1' if i.difiere else '0', i.nombre, i.tipocredito if i.tipocredito else ''])
                    return ok_json({'lista': lista})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=3, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'pagos':
                try:
                    data['title'] = u'Pagos del rubro'
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    data['pagos'] = rubro.pago_set.all().order_by('fecha')
                    data['factura'] = rubro.pago_set.all()[0].factura()
                    data['pagos'] = Pago.objects.filter(rubro=rubro)
                    return render(request, "cli_finanzas/pagos.html", data)
                except Exception as ex:
                    pass

            if action == 'adddeposito':
                try:
                    data['title'] = u'Subir comprobante de pago'
                    form = DepositoclienteForm()
                    data['form'] = form
                    return render(request, "cli_finanzas/adddeposito.html", data)
                except Exception as ex:
                    pass

            if action == 'del':
                try:
                    data['title'] = u'Eliminar deposito o transferencia'
                    data['deposito'] = Depositocliente.objects.get(pk=request.GET['id'])
                    return render(request, "cli_finanzas/del.html", data)
                except Exception as ex:
                    pass

            if action == 'pagar':
                try:
                    ids = request.GET['ids'].split(",")
                    data['rubros'] = rubros = Rubro.objects.filter(cliente=cliente,id__in=[int(x) for x in ids]).order_by('fechavence')
                    pp_all_qs = Rubro.objects.filter(cliente=cliente, validoprontopago=True, cancelado=False, pasivo=False)
                    # para permitir el descuento al seleccionar cualquier subconjunto pero que sean ProntoPago (no necesariamente todos), cambiar a:
                    # solo_pp_seleccionados = rubros_sel_qs.exists() and not rubros_sel_qs.filter(validoprontopago=False).exists()

                    solo_pp_seleccionados_y_todos = (rubros.exists() and not rubros.filter(validoprontopago=False).exists() and rubros.count() == pp_all_qs.count() and pp_all_qs.count() > 0)
                    # solo_pp_seleccionados_y_todos = False
                    data['solo_pp_seleccionados_y_todos'] = solo_pp_seleccionados_y_todos
                    data['cliente'] = cliente
                    data['factura'] = 1
                    data['tiene_nota_debito'] = nd = True if rubros[0].es_notadebito() else False
                    clientefacturacion = cliente.clientefacturacion(request)
                    data['facturaidentificacion'] = clientefacturacion.identificacion
                    data['tipo_identificacion'] = clientefacturacion.tipo
                    data['facturanombre'] = remover_tildes(clientefacturacion.nombre)
                    data['facturadireccion'] = remover_tildes(clientefacturacion.direccion)
                    data['facturatelefono'] = remover_tildes(clientefacturacion.telefono)
                    data['facturaemail'] = clientefacturacion.email
                    data['totalapagar'] = total = sum([x.saldo for x in rubros])
                    matricula = cliente.ultima_matricula_sinextendido()
                    rubros_descuento_por_fp = {}
                    if matricula:
                        precioperiodo = cliente.carrera.precio_periodo(cliente.mi_nivel().nivel.id, matricula.nivel.periodo, cliente.sede, cliente.modalidad)
                        descuento_fp = precioperiodo.detalle_descuento(FORMA_PAGO_TARJETA)
                        if descuento_fp:
                            total_descuento = 0
                            rubros_list = []
                            for rubro in Rubro.objects.filter(id__in=ids, validoprontopago=True):
                                descuentopp = null_to_numeric(rubro.valor * (descuento_fp.porcentaje / 100), 2)
                                total_descuento += descuentopp
                                rubros_list.append({'rubro_id': rubro.id,
                                                    'valor_original': rubro.valor,
                                                    'descuentopp': descuentopp,
                                                    'valor_con_descuento': rubro.valor - descuentopp})
                            if total_descuento > 0:
                                rubros_descuento_por_fp[FORMA_PAGO_TARJETA] = {'total_descuento': total_descuento,
                                                                               'fechainicio': descuento_fp.fechainicio.strftime('%Y-%m-%d'),
                                                                               'fechafin': descuento_fp.fechafin.strftime('%Y-%m-%d'),
                                                                               'porcentaje': descuento_fp.porcentaje,
                                                                               'nombre': 'TARJETA',
                                                                               'rubros': rubros_list}
                    data['rubros_descuento_por_fp'] = rubros_descuento_por_fp
                    data['url_app_datafast'] = URL_APP_DATAFAST
                    data['script_url'] = SCRIPT_URL
                    data['pago_minimo_tarjeta'] = PAGO_MINIMO_TARJETA
                    return render(request, "cli_finanzas/pagar.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'resultado':
                try:
                    data['resultado'] = 'bad'
                    data['actual'] = True
                    autorizacion = AutorizacionDatafast.objects.get(autorizacion=request.GET['id'])
                    if not autorizacion.respuesta:
                        resultado = statuspaymentrequest(request.GET['id'])
                        mensaje = MensajeDatafast.objects.get(codigo=resultado['result']['code'])
                        autorizacion.idtransaccion = resultado['id']
                        autorizacion.mensaje = mensaje
                        autorizacion.save()
                        autorizacion.respuesta = resultado.__str__()
                        if resultado['result']['code'] == '000.000.000' or resultado['result']['code'] == '000.100.112' or resultado['result']['code'] == '000.100.110':
                            data['resultado'] = 'ok'
                            referencia = resultado['resultDetails']['ReferenceNbr']
                            listareferencia = referencia.split('_')
                            autorizacion.lote = listareferencia[0]
                            autorizacion.referencia = listareferencia[1]
                            autorizacion.aprobada = True
                        else:
                            autorizacion.motivo = resultado['result']['description']
                        autorizacion.save()
                    if autorizacion.aprobada:
                        puntosalva = transaction.savepoint()
                        try:
                            autorizacion.comprobante_rubros(autorizacion.fecha.date())
                            transaction.savepoint_commit(puntosalva)
                        except Exception as ex:
                            transaction.savepoint_rollback(puntosalva)
                    data['autorizacion'] = autorizacion
                    data['permite_modificar'] = False
                    return render(request, "cli_finanzas/resultado.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'resultadopayphone':
                try:
                    data['resultado'] = 'bad'
                    data['actual'] = True
                    if 'autorizacion' not in request.session:
                        return HttpResponseRedirect('/cli_finanzas')
                    data['numeroautorizacion'] = numeroautorizacion = request.session['autorizacion']
                    autorizacion = AutorizacionPayPhone.objects.filter(autorizacion=numeroautorizacion, cliente=cliente)[0]
                    autorizacion.idautorizacion = request.GET['id']
                    autorizacion.save()
                    resultado = None
                    if not autorizacion.respuesta:
                        resultado = statuspaymentrequest_payphone(autorizacion)
                        autorizacion.respuesta = resultado.__str__()
                        if ('errorCode' in resultado) or int(resultado['statusCode']) == 2:
                            autorizacion.aprobada = False
                            autorizacion.motivo = resultado['message']
                            autorizacion.save()
                        elif int(resultado['statusCode']) == 3:
                            data['resultado'] = 'ok'
                            autorizacion.aprobada = True
                            if resultado['deferredCode']:
                                autorizacion.deferredcode = resultado['deferredCode']
                                if resultado['deferredCode'][:2] == "01":
                                    autorizacion.interes = False
                                if resultado['deferredCode'][:2] == "02":
                                    autorizacion.interes = True
                                if resultado['deferredCode'][2:4] == "01":
                                    autorizacion.gracia = False
                                if resultado['deferredCode'][2:4] == "02":
                                    autorizacion.gracia = True
                                if null_to_numeric(resultado['deferredCode'][4:6], 0) > 0:
                                    autorizacion.mesesdiferido = null_to_numeric(resultado['deferredCode'][4:6], 0)
                                if null_to_numeric(resultado['deferredCode'][6:8], 0) > 0:
                                    autorizacion.mesesgracia = null_to_numeric(resultado['deferredCode'][6:8], 0)
                        autorizacion.save()
                    if autorizacion.aprobada:
                        puntosalva = transaction.savepoint()
                        try:
                            autorizacion.comprobante_rubros(autorizacion.fecha.date())
                            transaction.savepoint_commit(puntosalva)
                        except Exception as ex:
                            transaction.savepoint_rollback(puntosalva)
                    data['autorizacion'] = autorizacion = AutorizacionPayPhone.objects.filter(autorizacion=numeroautorizacion, cliente=cliente)[0]
                    return render(request, "cli_finanzas/resultadopayphone.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'resultadodeuna':
                try:
                    data['resultado'] = 'bad'
                    data['actual'] = True
                    data['autorizacion'] = True
                    # if 'autorizacion' not in request.session:
                    #     return HttpResponseRedirect('/cli_finanzas')
                    return render(request, "cli_finanzas/resultadodeuna.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Listado de rubros que adeuda el alumno'
                if LUGAR_RECAUDACION_TARJETA_ID > 0:
                    lr = LugarRecaudacion.objects.get(id=LUGAR_RECAUDACION_TARJETA_ID)
                    if not lr.activo:
                        return HttpResponseRedirect('/')
                else:
                    return HttpResponseRedirect('/')
                cliente.chequea_mora()
                rubrosnocancelados = cliente.rubro_set.filter(cancelado=False).order_by('cancelado', 'fechavence')
                rubroscanceldos = cliente.rubro_set.filter(cancelado=True).order_by('cancelado', '-fechavence')
                data['rubros'] = list(chain(rubrosnocancelados, rubroscanceldos))
                data['facturas'] = Factura.objects.filter(pagos__rubro__cliente=cliente).order_by('-fecha').distinct()
                data['recibos'] = ReciboPago.objects.filter(pagos__rubro__cliente=cliente).distinct()
                data['total_rubros'] = cliente.total_rubros()
                data['total_pagado'] = cliente.total_pagado()
                data['total_adeudado'] = cliente.total_adeudado()
                data['reporte_0'] = obtener_reporte('listado_deuda_xcliente')
                data['ruc_institucion'] = mi_institucion().ruc
                data['permite_pago_online'] = PERMITE_PAGO_ONLINE
                data['reciboscaja'] = cliente.recibocajainstitucion_set.all()
                data['notascredito'] = cliente.notacredito_set.all()
                return render(request, "cli_finanzas/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
