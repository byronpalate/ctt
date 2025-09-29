# coding=utf-8
import threading
from datetime import datetime
from itertools import chain

# import django.utils.simplejson as json
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.aggregates import Max, Sum
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template

from decorators import secure_module, last_access
from settings import FORMA_PAGO_EFECTIVO, FORMA_PAGO_TARJETA, FORMA_PAGO_CHEQUE, FORMA_PAGO_DEPOSITO, \
    FORMA_PAGO_TRANSFERENCIA, FORMA_PAGO_NOTA_CREDITO, FORMA_PAGO_RECIBOCAJAINSTITUCION, FORMA_PAGO_RETENCION, \
    FORMA_PAGO_CTAXCRUZAR, TIPO_IVA_0_ID, RUBRO_OTRO_RECARGO_ID, COBRO_DEUDA_ANTERIOR_PRIMERO, \
    PAGO_TARJETA_NACIONAL_ID, OTROS_BANCOS_EXTERNOS_ID, TIPO_TARJETA_CREDITO_ID, TIPO_TARJETA_DEBITO_ID, \
    DIFERIDO_TARJETA_CORRIENTE_ID, PERSONA_ADMINS_ACADEMICO_ID
from ctt.commonviews import adduserdata, obtener_reporte
from ctt.forms import RubroForm, FormaPagoForm, EliminarRubroForm, MoverPagoRubroForm
from ctt.funciones import MiPaginador, log, convertir_fecha, ok_json, bad_json, empty_json, url_back, generar_nombre
from ctt.models import Inscripcion, Rubro, Pago, Banco, TipoOtroRubro, RubroOtro, Persona, ClienteFactura, \
    PagoCheque, RubroEspecieValorada, PagoTransferenciaDeposito, TipoEspecieValorada, DepositoInscripcion, \
    InscripcionFlags, RubroLiquidado, ValeCaja, \
    TipoCheque, TipoEmisorTarjeta, IvaAplicado, null_to_numeric, DatoCheque, DatoTransferenciaDeposito, Periodo, \
    RubroAnticipado, TipoTarjetaBanco, RubroCuota, FormaDePago

from ctt.printdoc import imprimir_contenido


class EspecieSerieGenerador:
    def __init__(self):
        self.__lock = threading.RLock()

    def generar_especie(self, rubro, tipo):
        self.__lock.acquire()
        try:
            serie = null_to_numeric(RubroEspecieValorada.objects.filter(rubro__fecha__year=rubro.fecha.year).aggregate(valor=Max('serie'))['valor'], 0) + 1
            rubroe = RubroEspecieValorada(rubro=rubro,
                                          tipoespecie=tipo,
                                          serie=serie)
            rubroe.save()
            return rubroe
        finally:
            self.__lock.release()


generador_especies = EspecieSerieGenerador()


def pagaryfacturar(request, transaction, sesion_caja):
    try:
        lista_rubros_anticipados = []
        data = json.loads(request.POST['data'])
        pagos = data['pagos']
        hoy = datetime.now().date()
        # FACTURA
        factura = None
        recibopago = None
        tienedescuentopp = False
        facturar = data['facturar']
        inscripcion = Inscripcion.objects.get(pk=int(data['inscripcion']))
        matricula = inscripcion.ultima_matricula_sinextendido()
        if matricula:
            pp = inscripcion.carrera.precio_periodo(inscripcion.mi_nivel().nivel.id, matricula.nivel.periodo, inscripcion.sede , inscripcion.modalidad)
            tienedescuentopp = True if pp.detalle_descuento(data['pagos'][0]['formadepago']) else False
        flags = inscripcion.mis_flag()
        facturacredito = False
        puntosalva = transaction.savepoint()
        if facturar == 'si':
            facturacredito = data['factura']['facturacredito']
            if not facturacredito:
                if not flags.permitepagoparcial:
                    valorrubros = 0
                    valorpagos = 0
                    for rubroid in data['rubros']:
                        rubro = Rubro.objects.get(pk=int(rubroid[0]))
                        valorrubros += rubro.saldo
                    if tienedescuentopp:
                        valorrubros -= data['pagos'][0]['descuento']
                    for pago in pagos:
                        valorpagos += float(pago['valor'])
                    if valorpagos < valorrubros:
                        return {'result': 'bad', "error": u"El valor del pago es menor al valor total del rubro."}
            clientefacturacion = inscripcion.clientefacturacion(request)
            if 'bancaonline' not in data.get('factura', {}):
                clientefacturacion.nombre = data['factura']['nombre']
                clientefacturacion.direccion = data['factura']['direccion']
                clientefacturacion.identificacion = data['factura']['identificacion']
                clientefacturacion.telefono = data['factura']['telefono']
                clientefacturacion.tipo = int(data['factura']['tipo'])
                clientefacturacion.email = data['factura']['email']
                clientefacturacion.save()
            # CHEQUEAR NUMERO DE FACTURA
            if sesion_caja.caja.puntodeventa.facturaelectronica:
                data['factura']['numero'] = str(sesion_caja.caja.puntodeventa.secuencial_factura())
            else:
                if Factura.objects.filter(numero=sesion_caja.caja.puntodeventa.numeracion() + "-" + data['factura']['numero'].zfill(9)).exists():
                    transaction.savepoint_rollback(puntosalva)
                    return {'result': 'bad', "error": u"Numero de factura ya existe."}
            # CREA LA FACTURA
            factura = Factura(numero=sesion_caja.caja.puntodeventa.numeracion() + "-" + data['factura']['numero'].zfill(9),
                              numeroreal=int(float(data['factura']['numero'])),
                              fecha=datetime.now().date(),
                              valida=True,
                              subtotal=0,
                              iva=0,
                              total=0,
                              impresa=False,
                              sesion=sesion_caja,
                              identificacion=clientefacturacion.identificacion,
                              tipo=clientefacturacion.tipo,
                              email=clientefacturacion.email,
                              nombre=clientefacturacion.nombre,
                              direccion=clientefacturacion.direccion,
                              telefono=clientefacturacion.telefono,
                              pagada=False if facturacredito else True)
            factura.save(request)
            factura.claveacceso = factura.genera_clave_acceso_factura()
            factura.save(request)
        listatipospago = []
        pagopararecibo = None
        tipopagopararecibo = 0
        depositoinscripcion = None
        excedente_total = 0.0
        for pago in pagos:
            tp = None
            if pago['formadepago'] == FORMA_PAGO_EFECTIVO:
                descuentofp = pp.detalle_descuento(FORMA_PAGO_EFECTIVO) if matricula else None
            elif pago['formadepago'] == FORMA_PAGO_CHEQUE:
                descuentofp = pp.detalle_descuento(FORMA_PAGO_CHEQUE) if matricula else None
                if DatoCheque.objects.filter(numero=pago['numero'], cuenta=pago['cuenta'], banco=Banco.objects.get(pk=pago['bancocheque'])).exists():
                    datocheque = DatoCheque.objects.filter(numero=pago['numero'], cuenta=pago['cuenta'], banco=Banco.objects.get(pk=pago['bancocheque']))[0]
                else:
                    datocheque = DatoCheque(numero=pago['numero'],
                                            cuenta=pago['cuenta'],
                                            banco=Banco.objects.get(pk=pago['bancocheque']),
                                            fecha=datetime.now().date(),
                                            fechacobro=convertir_fecha(pago['fechacobro']),
                                            emite=pago['emite'],
                                            tipocheque=TipoCheque.objects.get(pk=pago['tipocheque']))
                    datocheque.save(request)
                if datocheque.pagocheque_set.filter(pagos__valido=True).exists():
                    if sesion_caja.fecha != datocheque.fecha:
                        transaction.savepoint_rollback(puntosalva)
                        return {'result': 'bad', "error": u"Cheque procesado en otra fecha."}
                if PagoCheque.objects.filter(datocheque=datocheque).exists():
                    tp = PagoCheque.objects.filter(datocheque=datocheque)[0]
                else:
                    tp = PagoCheque(datocheque=datocheque)
                    tp.save(request)
                if not pagopararecibo:
                    pagopararecibo = tp
                    tipopagopararecibo = 1
                if tp not in listatipospago:
                    listatipospago.append(tp)
                datocheque.actualiza_valor()
            elif pago['formadepago'] == FORMA_PAGO_DEPOSITO:
                descuentofp = pp.detalle_descuento(FORMA_PAGO_DEPOSITO) if matricula else None
                if DatoTransferenciaDeposito.objects.filter(deposito=True, referencia=pago['referencia'], fecha=datetime.now().date(), cuentabanco__id=pago['cuentabanco'], fechabanco=convertir_fecha(pago['fecha'])).exists():
                    datotransferenciadeposito = DatoTransferenciaDeposito.objects.filter(deposito=True, referencia=pago['referencia'], fecha=datetime.now().date(), cuentabanco__id=pago['cuentabanco'], fechabanco=convertir_fecha(pago['fecha']))[0]
                else:
                    datotransferenciadeposito = DatoTransferenciaDeposito(referencia=pago['referencia'],
                                                                          fecha=datetime.now().date(),
                                                                          cuentabanco_id=pago['cuentabanco'],
                                                                          fechabanco=convertir_fecha(pago['fecha']),
                                                                          deposito=True)
                    datotransferenciadeposito.save(request)
                if datotransferenciadeposito.pagotransferenciadeposito_set.filter(pagos__valido=True).exists():
                    if sesion_caja.fecha != datotransferenciadeposito.fecha:
                        transaction.savepoint_rollback(puntosalva)
                        return {'result': 'bad', "error": u"Depósito procesado en otra fecha."}
                if PagoTransferenciaDeposito.objects.filter(datotransferenciadeposito=datotransferenciadeposito).exists():
                    tp = PagoTransferenciaDeposito.objects.filter(datotransferenciadeposito=datotransferenciadeposito)[0]
                else:
                    tp = PagoTransferenciaDeposito(datotransferenciadeposito=datotransferenciadeposito)
                    tp.save(request)
                padre = tp.padre()
                if DepositoInscripcion.objects.filter(cuentabanco=padre.cuentabanco, fecha=padre.fechabanco, referencia=padre.referencia, deposito=True, procesado=False).exists():
                    depositoinscripcion = DepositoInscripcion.objects.filter(cuentabanco=padre.cuentabanco, fecha=padre.fechabanco, referencia=padre.referencia, deposito=True, procesado=False)[0]
                if not pagopararecibo:
                    pagopararecibo = tp
                    tipopagopararecibo = 2
                if tp not in listatipospago:
                    listatipospago.append(tp)
                datotransferenciadeposito.actualiza_valor()
            elif pago['formadepago'] == FORMA_PAGO_TRANSFERENCIA:
                descuentofp = pp.detalle_descuento(FORMA_PAGO_TRANSFERENCIA) if matricula else None
                if DatoTransferenciaDeposito.objects.filter(deposito=False, referencia=pago['referencia'], fecha=datetime.now().date(), cuentabanco__id=pago['cuentabanco'], fechabanco=convertir_fecha(pago['fecha'])).exists():
                    datotransferenciadeposito = DatoTransferenciaDeposito.objects.filter(deposito=False, referencia=pago['referencia'], fecha=datetime.now().date(), cuentabanco__id=pago['cuentabanco'], fechabanco=convertir_fecha(pago['fecha']))[0]
                else:
                    datotransferenciadeposito = DatoTransferenciaDeposito(referencia=pago['referencia'],
                                                                          fecha=datetime.now().date(),
                                                                          cuentabanco_id=pago['cuentabanco'],
                                                                          tipotransferencia_id=pago['tipotransferencia'],
                                                                          fechabanco=convertir_fecha(pago['fecha']),
                                                                          deposito=False)
                    datotransferenciadeposito.save(request)
                if datotransferenciadeposito.pagotransferenciadeposito_set.filter(pagos__valido=True).exists():
                    if sesion_caja.fecha != datotransferenciadeposito.fecha:
                        transaction.savepoint_rollback(puntosalva)
                        return {'result': 'bad', "error": u"Transferencia procesado en otra fecha."}
                if PagoTransferenciaDeposito.objects.filter(datotransferenciadeposito=datotransferenciadeposito).exists():
                    tp = PagoTransferenciaDeposito.objects.filter(datotransferenciadeposito=datotransferenciadeposito)[0]
                else:
                    tp = PagoTransferenciaDeposito(datotransferenciadeposito=datotransferenciadeposito)
                    tp.save(request)
                padre = tp.padre()
                if DepositoInscripcion.objects.filter(cuentabanco=padre.cuentabanco, fecha=padre.fechabanco, referencia=padre.referencia, deposito=False, procesado=False).exists():
                    depositoinscripcion = DepositoInscripcion.objects.filter(cuentabanco=padre.cuentabanco, fecha=padre.fechabanco, referencia=padre.referencia, deposito=False, procesado=False)[0]
                if not pagopararecibo:
                    pagopararecibo = tp
                    tipopagopararecibo = 3
                if tp not in listatipospago:
                    listatipospago.append(tp)
                datotransferenciadeposito.actualiza_valor()
            elif pago['formadepago'] == FORMA_PAGO_TARJETA:
                descuentofp = pp.detalle_descuento(FORMA_PAGO_TARJETA) if matricula else None
                if DatoTarjeta.objects.filter(referencia=pago['referencia'], lote=pago['lote'], autorizacion=pago['autorizaciontar']).exists():
                    datotarjeta = DatoTarjeta.objects.filter(referencia=pago['referencia'], lote=pago['lote'], autorizacion=pago['autorizaciontar'])[0]
                else:
                    tipoemisortarjeta = None
                    if pago['tipoemisortarjeta']:
                        tipoemisortarjeta = TipoEmisorTarjeta.objects.get(pk=pago['tipoemisortarjeta'])
                    diferido = None
                    if pago['diferido']:
                        diferido = DiferidoTarjeta.objects.filter(banco=pago['bancotarjeta'],
                                                                  tipoemisortarjeta=tipoemisortarjeta,
                                                                  tipotarjetabanco=pago['tarjeta'],
                                                                  valordatafast=pago['diferido'])[0]
                    datotarjeta = DatoTarjeta(banco=Banco.objects.get(pk=pago['bancotarjeta']),
                                              tipo_id=pago['tipotarjeta'],
                                              tipotarjeta_id=pago['tarjeta'],
                                              tipoemisortarjeta=tipoemisortarjeta,
                                              diferido=diferido,
                                              poseedor=pago['poseedor'],
                                              procesadorpago_id=pago['procesadorpago'],
                                              referencia=pago['referencia'],
                                              lote=pago['lote'],
                                              autorizacion=pago['autorizaciontar'],
                                              fecha=datetime.now().date())
                    datotarjeta.save(request)
                if datotarjeta.pagotarjeta_set.filter(pagos__valido=True).exists():
                    if sesion_caja.fecha != datotarjeta.fecha:
                        transaction.savepoint_rollback(puntosalva)
                        return {'result': 'bad', "error": u"Tarjeta procesada en otra fecha."}
                if PagoTarjeta.objects.filter(datotarjeta=datotarjeta).exists():
                    tp = PagoTarjeta.objects.filter(datotarjeta=datotarjeta)[0]
                else:
                    tp = PagoTarjeta(datotarjeta=datotarjeta)
                    tp.save(request)
                if not pagopararecibo:
                    pagopararecibo = tp
                    tipopagopararecibo = 4
                if tp not in listatipospago:
                    listatipospago.append(tp)
                datotarjeta.actualiza_valor()
            elif pago['formadepago'] == FORMA_PAGO_RECIBOCAJAINSTITUCION:
                descuentofp = pp.detalle_descuento(FORMA_PAGO_RECIBOCAJAINSTITUCION) if matricula else None
                if ReciboCajaInstitucion.objects.get(pk=pago['recibocaja']).saldo >= float(pago['valor']):
                    tp = PagoReciboCajaInstitucion(recibocaja_id=pago['recibocaja'],
                                                   valor=float(pago['valor']),
                                                   fecha=datetime.now().date())
                    tp.save(request)
                    if not pagopararecibo:
                        pagopararecibo = tp
                        tipopagopararecibo = 5
                    rc = tp.recibocaja
                    rc.save()
                    if tp not in listatipospago:
                        listatipospago.append(tp)
                else:
                    transaction.savepoint_rollback(puntosalva)
                    return {'result': 'bad', "error": u"Recibo de caja no tiene saldo suficiente."}
            elif pago['formadepago'] == FORMA_PAGO_NOTA_CREDITO:
                descuentofp = pp.detalle_descuento(FORMA_PAGO_NOTA_CREDITO) if matricula else None
                if NotaCredito.objects.get(pk=pago['notacredito']).saldo >= float(pago['valor']):
                    tp = PagoNotaCredito(notacredito_id=pago['notacredito'],
                                         valor=float(pago['valor']),
                                         fecha=datetime.now().date())
                    tp.save(request)
                    if not pagopararecibo:
                        pagopararecibo = tp
                        tipopagopararecibo = 6
                    nc = tp.notacredito
                    nc.actualiza_valor()
                    if tp not in listatipospago:
                        listatipospago.append(tp)
                else:
                    transaction.savepoint_rollback(puntosalva)
                    return {'result': 'bad', "error": u"Nota de crédito no tiene saldo suficiente."}
            valor_inicial = float(pago['valor'])
            valor_restante = valor_inicial
            pago2 = None
            for rubroid in data['rubros']:
                rubro = Rubro.objects.get(pk=int(rubroid[0]))

                # inicio descuentos
                if descuentofp:
                    if rubro.validoprontopago and descuentofp.fechainicio.date() <= hoy <= descuentofp.fechafin.date() and descuentofp.porcentaje > 0 and pagos[0]['aplica_pp']:
                        valordescontar = null_to_numeric((rubro.saldo * descuentofp.porcentaje) / 100.0, 2)
                        descuentoefectivo = False
                        descuento = DescuentoRecargoRubro(rubro=rubro,
                                                          recargo=False,
                                                          motivo='POR PRONTO PAGO',
                                                          precio=rubro.saldo,
                                                          descuentoefectivo=descuentoefectivo,
                                                          porciento=descuentofp.porcentaje,
                                                          responsable=sesion_caja.caja.persona,
                                                          fecha=hoy,
                                                          valordescuento=valordescontar)
                        descuento.save(request)
                        rubro.save(request)
                # fin descuentos

                if rubro.es_anticipo():
                    if rubro not in lista_rubros_anticipados:
                        lista_rubros_anticipados.append(rubro)
                if valor_inicial > 0 and rubro.saldo > 0:
                    if facturacredito:
                        valor_linea = null_to_numeric(rubroid[1], 2)
                        valoraplicar = valor_restante if valor_linea >= valor_restante else valor_linea
                    else:
                        valoraplicar = valor_restante if rubro.saldo >= valor_restante else rubro.saldo
                    pago2 = Pago(fecha=datetime.now().date(),
                                 valor=valoraplicar,
                                 rubro=rubro,
                                 efectivo=True if not tp else False,
                                 anticipado=True if facturacredito else False,
                                 sesion=sesion_caja
                                 )
                    pago2.save(request)

                    valor_restante -= valoraplicar

                    rubro.save(request)
                    if rubro.cancelado and rubro.es_solicitud():
                        solicitud = rubro.dato_solicitud()
                        solicitud.siendoatendida = True
                        solicitud.save(request)
                    if tp:
                        tp.pagos.add(pago2)
                    if (pago2.es_deposito() or pago2.es_transferencia()) and depositoinscripcion:
                        pago2.depositoinscripcion = depositoinscripcion
                        pago2.save(request)
                        depositoinscripcion.save(request)
                        if depositoinscripcion.saldo < 0:
                            transaction.savepoint_rollback(puntosalva)
                            return {'result': 'bad', "error": u"El depósito no tiene el saldo solicitado."}
                    if facturar == 'si':
                        factura.pagos.add(pago2)
                if facturar == 'si':
                    factura.ivaaplicado = rubro.iva
                    factura.save(request)
                else:
                    if rubro.es_notadebito():
                        if rubro.notadebito().factura:
                            facturarubro = rubro.notadebito().factura
                            if facturarubro:
                                facturarubro.pagada = facturarubro.verifica_credito()
                                facturarubro.save(request)
                    if not recibopago:
                        secuencia = sesion_caja.caja.puntodeventa.secuencial_recibo()
                        recibopago = ReciboPago(numero=sesion_caja.caja.puntodeventa.numeracion() + "-" + str(secuencia).zfill(9),
                                                numeroreal=secuencia,
                                                fecha=datetime.now().date(),
                                                sesion=sesion_caja,
                                                inscripcion=rubro.inscripcion)
                        recibopago.save(request)
                    recibopago.pagos.add(pago2)
                    recibopago.save(request)
                if facturacredito:
                    pagonota = Pago.objects.filter(rubro=rubro, factura=factura)[0]
                    rubrocredito = Rubro(inscripcion=rubro.inscripcion,
                                         nombre=rubro.nombre,
                                         fecha=rubro.fecha,
                                         valor=pagonota.valor,
                                         iva_id=TIPO_IVA_0_ID,
                                         valoriva=0,
                                         periodo=rubro.periodo,
                                         valortotal=pagonota.valor,
                                         saldo=pagonota.valor,
                                         fechavence=rubro.fechavence)
                    rubrocredito.save(request)
                    rubrocreditonc = RubroNotaDebito(rubro=rubrocredito,
                                                     motivo=rubro.nombre,
                                                     factura=factura)
                    rubrocreditonc.save(request)
                    rubrocredito.actulizar_nombre()
            for tipopago in listatipospago:
                tipopago.actualiza_valor()
                padre = tipopago.padre()
                padre.actualiza_valor()
            if facturar == 'si':
                factura.actualizarsubtotales()
            else:
                recibopago.actualizarsubtotales()
            # SI HAY EXCEDENTE ENTONCES ADICIONAR UN RECIBO DE CAJA INSTITUCIONAL
            # Si hubo pronto pago en alguno, NO generar excedente
            excedente_pago = round(max(valor_restante, 0.0), 2)
            if excedente_pago > 0:
                excedente_total += excedente_pago

        # === SI HAY EXCEDENTE (sumado de todas las formas de pago), crear UN SOLO RC ===
        if excedente_total > 0:
            pagoexedente = Pago(
                fecha=datetime.now().date(),
                iva=0,
                valor=excedente_total,
                efectivo=True if tipopagopararecibo == 0 else False,
                sesion=sesion_caja
            )
            pagoexedente.save(request)

            # Vincular al tipo de pago 'portador' si aplica (cheque/dep./transf./tarjeta)
            if pagopararecibo and tipopagopararecibo != 0:
                pagopararecibo.pagos.add(pagoexedente)
                pagopararecibo.actualiza_valor()
                padre = pagopararecibo.padre()
                padre.actualiza_valor()

            rc = ReciboCajaInstitucion(
                inscripcion=inscripcion,
                pago=pagoexedente,
                motivo='PAGO ANTICIPADO DE VALORES',
                sesioncaja=sesion_caja,
                fecha=datetime.now().date(),
                hora=datetime.now().time(),
                valorinicial=excedente_total,
                saldo=excedente_total
            )
            rc.save(request)

            if factura:
                facturaexedente = FacturaPagoExedente(
                    factura=factura,
                    recibocajainstitucion=rc,
                    pago=pagoexedente
                )
                facturaexedente.save(request)
            else:
                recibopagoexedente = ReciboPagoExedente(
                    pago=pagoexedente,
                    recibocajainstitucion=rc,
                    recibopago=recibopago
                )
                recibopagoexedente.save(request)
        if factura:
            if factura.sesion.caja.puntodeventa.facturaelectronica:
                factura.electronica = True
                factura.save(request)
            if factura.sesion.caja.puntodeventa.imprimirfactura:
                imprimir_contenido(request, 'factura', factura.id)
        if recibopago:
            if recibopago.sesion.caja.puntodeventa.imprimirrecibo:
                imprimir_contenido(request, 'recibo', recibopago.id)
        # ACTUALIZA PRE-NOTIFICACION DE PAGOS
        for deposito in inscripcion.depositoinscripcion_set.filter(procesado=False):
            deposito.save(request)
        inscripcion.resetea_autorizaciones()
        for rubro in lista_rubros_anticipados:
            if rubro.adeuda():
                transaction.savepoint_rollback(puntosalva)
                return {'result': 'bad', "error": u"El rubro de pago anticipo debe ser cancelado en su totalidad."}
        transaction.savepoint_commit(puntosalva)
        return {'result': 'ok'}
    except Exception as ex:
        pass

@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    sesion_caja = None
    caja = None
    puedepagar = False
    if persona.puede_recibir_pagos():
        sesion_caja = persona.caja_abierta()
        if sesion_caja:
            caja = sesion_caja.caja
            puedepagar = sesion_caja.puede_pagar()
    data['sesion_caja'] = sesion_caja
    data['caja'] = caja
    data['puede_pagar'] = puedepagar
    data['PERSONA_ADMINS_ACADEMICO_ID'] = False
    if persona.id in PERSONA_ADMINS_ACADEMICO_ID:
        data['PERSONA_ADMINS_ACADEMICO_ID'] = True

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'pagosderecibo':
            try:
                data= {}
                data['recibocaja'] = recibocaja = ReciboCajaInstitucion.objects.get(pk=int(request.POST['id']))
                data['pagos'] = Pago.objects.filter(pagorecibocajainstitucion__recibocaja=recibocaja).distinct()
                template = get_template("finanzas/pagosderecibo.html")
                json_content = template.render(data)
                return ok_json({'html': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=3)

        if action == 'ccnc':
            try:
                nc = NotaCredito.objects.get(pk=request.POST['nc'])
                valor = float(request.POST['valor'])
                if nc.saldo < valor:
                    return bad_json()
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'ccrecibo':
            try:
                rc = ReciboCajaInstitucion.objects.get(pk=request.POST['rc'])
                valor = float(request.POST['valor'])
                if rc.saldo < valor:
                    return bad_json()
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'infodeposito':
            try:
                if DatoTransferenciaDeposito.objects.filter(deposito=True, cuentabanco__id=int(request.POST['banco']), referencia=request.POST['referencia']).exists():
                    return ok_json(data={'repetido': True})
                return ok_json(data={'repetido': False})
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'infotransferencia':
            try:
                if DatoTransferenciaDeposito.objects.filter(deposito=False, cuentabanco__id=int(request.POST['banco']), referencia=request.POST['referencia']).exists():
                    return ok_json(data={'repetido': True})
                return ok_json(data={'repetido': False})
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'autorizarcobros':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                flags = inscripcion.mis_flag()
                flags.puedecobrar = True if request.POST['valor'] == 'true' else False
                flags.save()
                log(u'Autorizo cobros debiendo nd: %s' % (inscripcion), request, "edit")
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'autorizarsupletorios':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                flags = inscripcion.mis_flag()
                flags.puedetomarsupletorio = True if request.POST['valor'] == 'true' else False
                flags.save()
                log(u'Autorizo tomar supletorios SP: %s' % (inscripcion), request, "edit")
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'deudaanterior':
            try:
                persona = Persona.objects.filter(inscripcion__id=request.POST['id'])[0]
                persona.deudahistorica = True if request.POST['valor'] == 'true' else False
                persona.save()
                log(u'Modifico estado deuda anterior: %s' % (persona), request, "edit")
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'matriculardeuda':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                inscripcion.permitematriculacondeuda = True if request.POST['valor'] == 'true' else False
                inscripcion.save()
                log(u'Autorizó matriculación con deuda: %s' % (inscripcion), request, "edit")
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'pagoparcial':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                flags = inscripcion.mis_flag()
                flags.permitepagoparcial = True if request.POST['valor'] == 'true' else False
                flags.save()
                log(u'Autorizó pago parcial: %s' % (inscripcion), request, "edit")
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'notificardeuda':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                flags = inscripcion.mis_flag()
                flags.notificardeuda = True if request.POST['valor'] == 'true' else False
                flags.save()
                if flags.notificardeuda:
                    log(u'Activo notificación deudas: %s - Insc.:%s' % (inscripcion,inscripcion.id), request, "edit")
                else:
                    log(u'Desactivo notificación deudas: %s - Insc.:%s' % (inscripcion,inscripcion.id), request, "edit")
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'pagocheque':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                flags = inscripcion.mis_flag()
                flags.tienechequeprotestado = True if request.POST['valor'] == 'true' else False
                flags.save()
                log(u'Autorizó pago con cheque: %s' % (inscripcion), request, "edit")
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'descuentos':
            try:
                ids = request.POST['rubros']
                # porciento = int(request.POST['porciento'])
                porciento = int(0)
                valor = float(request.POST['valor'])
                motivo = request.POST['motivo']
                idrubros = []
                for i in ids.split(","):
                    idrubros.append(int(i))
                for rubro in Rubro.objects.filter(id__in=idrubros):
                    if rubro.tiene_descuentorecargo() or rubro.tiene_pagos() or rubro.es_recargodescuento():
                        return bad_json(mensaje=u'No se puede aplicar el descuento al rubro porque ya tiene un descuento o ya tiene pagos asociados.')
                for rubro in Rubro.objects.filter(id__in=idrubros):
                    if porciento:
                        valordescontar = null_to_numeric((rubro.saldo * porciento) / 100.0, 2)
                        descuentoefectivo = False
                    else:
                        valordescontar = valor
                        porciento = null_to_numeric((valor / rubro.saldo) * 100.0, 0)
                        descuentoefectivo = True
                    descuento = DescuentoRecargoRubro(rubro=rubro,
                                                      recargo=False,
                                                      motivo=motivo,
                                                      precio=rubro.saldo,
                                                      descuentoefectivo=descuentoefectivo,
                                                      porciento=porciento,
                                                      responsable=persona,
                                                      fecha=datetime.now().date(),
                                                      valordescuento=valordescontar)
                    descuento.save(request)
                    rubro.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'recargos':
            try:
                ids = request.POST['rubros']
                porciento = request.POST['porciento']
                motivo = request.POST['motivo']
                idrubros = []
                for i in ids.split(","):
                    idrubros.append(int(i))
                rubros = Rubro.objects.filter(pk__in=idrubros)
                for rubro in rubros:
                    if rubro.tiene_descuentorecargo() or rubro.tiene_pagos() or rubro.es_recargodescuento():
                        return bad_json(mensaje=u'No se puede aplicar el recargo al rubro: %s' % rubro.id)
                for rubro in rubros:
                    recargos = null_to_numeric((rubro.valor * porciento) / 100.0, 2)
                    rubrorecargo = Rubro(fecha=rubro.fecha,
                                         valor=recargos,
                                         inscripcion=rubro.inscripcion,
                                         cancelado=False,
                                         periodo=rubro.periodo,
                                         fechavence=rubro.fechavence)
                    rubrorecargo.save(request)
                    ro = RubroOtro(rubro=rubrorecargo,
                                   tipo_id=RUBRO_OTRO_RECARGO_ID,
                                   descripcion='RECARGO')
                    ro.save(request)
                    rubrorecargo.actulizar_nombre()
                    movimiento = DescuentoRecargoRubro(rubro=rubro,
                                                       rubrorecargo=rubrorecargo,
                                                       recargo=True,
                                                       motivo=motivo,
                                                       precio=rubro.valor,
                                                       porciento=porciento,
                                                       responsable=persona,
                                                       fecha=datetime.now().date(),
                                                       valordescuento=recargos)
                    movimiento.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'pagaryfacturar':
            try:
                return empty_json(pagaryfacturar(request, transaction, sesion_caja))
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(extradata={'error': str(ex.message)})

        if action == 'imprimirnc':
            try:
                nc = NotaCredito.objects.get(pk=request.POST['nc'])
                imprimir_contenido(request, 'notacredito', nc.id)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(extradata={'error': str(ex.message)})

        if action == 'addespecie':
            try:
                tipoespecie = TipoEspecieValorada.objects.get(pk=request.POST['id'])
                inscripcion = Inscripcion.objects.get(pk=request.POST['idi'])
                periodosolicitud = 0
                # for p in PeriodoSolicitud.objects.all():
                #     if p.vigente():
                #         periodosolicitud = p.id
                periodosolicitud = Periodo.objects.filter(parasolicitudes=True)[0]
                rubro = Rubro(fecha=datetime.now().date(),
                              valor=tipoespecie.precio,
                              inscripcion=inscripcion,
                              iva=tipoespecie.iva,
                              periodo=periodosolicitud,
                              fechavence=datetime.now().date())
                rubro.save(request)
                generador_especies.generar_especie(rubro=rubro,
                                                   tipo=tipoespecie)
                rubro.actulizar_nombre()
                log(u'Adiciono especie valorada: %s - %s' % (tipoespecie, rubro.inscripcion), request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delrubro':
            try:
                form = EliminarRubroForm(request.POST)
                rubro = Rubro.objects.get(pk=request.POST['id'])
                if rubro.tiene_recargo():
                    recargo = rubro.recargo()
                    if not recargo.rubrorecargo.cancelado or recargo.rubrorecargo.tiene_pagos():
                        return bad_json(mensaje=u'Debe eliminar o cancelar el recargo primero.')
                    else:
                        recargo.delete()
                if form.is_valid():
                    motivo = form.cleaned_data['motivo']
                    log(u'Elimino rubro: %s - %s' % (rubro, motivo), request, "del")
                    rubro.delete()
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json()

        if action == 'revertirdescuento':
            try:
                rubro = Rubro.objects.get(pk=request.POST['id'])
                descuento = rubro.descuento()
                if not descuento:
                    return bad_json(mensaje=u'El rubro no tiene descuento aplicado.')
                if rubro.tiene_pagos():
                    return bad_json(mensaje=u'El rubro tiene pagos no se puede eliminar el descuento.')
                descuento.delete()
                rubro.save()
                log(u'Reverso descuento de rubro: %s' % rubro, request, "del")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json()

        if action == 'protestopagoconcheque':
            try:
                flag = InscripcionFlags.objects.filter(inscripcion__id=request.POST['id'])[0]
                inscripcion = Inscripcion.objects.get(pk=flag.inscripcion.id)
                flag.delete()
                log(u'Elimino restriccion de cobro con cheque: %s' % inscripcion, request, "del")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=3)

        if action == 'generarrubroinscripcion':
            try:
                inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
                inscripcion.generar_rubro_inscripcion(inscripcion.mi_malla())
                log(u'Genero rubro de inscripcion: %s' % inscripcion, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=3)

        if action == 'addotro':
            try:
                tipootro = TipoOtroRubro.objects.get(pk=request.POST['tid'])
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                ivaaplicado = IvaAplicado.objects.get(pk=int(request.POST['iva']))
                periodo = Periodo.objects.get(pk=int(request.POST['periodo']))
                valor = float(request.POST['valor'])
                valoriva = 0
                if ivaaplicado.porcientoiva > 0:
                    valoriva = null_to_numeric(valor * ivaaplicado.porcientoiva)
                rubro = Rubro(fecha=datetime.now().date(),
                              valor=valor,
                              periodo=periodo,
                              valoriva=valoriva,
                              valortotal=null_to_numeric(valor + valoriva, 2),
                              saldo=null_to_numeric(valor + valoriva, 2),
                              inscripcion=inscripcion,
                              cancelado=False,
                              iva=ivaaplicado,
                              fechavence=convertir_fecha(request.POST['fe']))
                rubro.save(request)
                rubrootro = RubroOtro(rubro=rubro,
                                      tipo=tipootro)
                rubrootro.save(request)
                rubro.actulizar_nombre(nombre=request.POST['ta'])
                log(u'Adiciono rubro tipo otro: %s' % rubrootro, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'pasivo':
            try:
                rubro = Rubro.objects.get(pk=request.POST['id'])
                if not request.POST['motivopasivo']:
                    return bad_json(mensaje=u'Debe ingresar el motivo para dar de Baja el rubro.')
                rubro.motivopasivo = request.POST['motivopasivo']
                rubro.fechapasivo = datetime.now().date()
                rubro.pasivo = True
                rubro.save()
                log(u'Envio a estado pasivo el rubro: %s - %s' % (rubro, rubro.id), request, "edit")
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'activo':
            try:
                rubro = Rubro.objects.get(pk=request.POST['id'])
                rubro.pasivo = False
                rubro.save()
                log(u'Activo el rubro que constaba como estado pasivo: %s - %s' % (rubro, rubro.id), request, "edit")
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'procesado':
            try:
                deposito = DepositoInscripcion.objects.get(pk=request.POST['id'])
                deposito.estadoprocesado = int(request.POST['estadoprocesado'])
                deposito.save()
                log(u'Cambio estado de procesado: %s' % deposito.motivo, request, "edit")
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'valido':
            try:
                deposito = DepositoInscripcion.objects.get(pk=request.POST['id'])
                deposito.valido = True
                deposito.save()
                log(u'Valido documento deposito: %s' % deposito.motivo, request, "edit")
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'invalido':
            try:
                deposito = DepositoInscripcion.objects.get(pk=request.POST['id'])
                deposito.valido = False
                deposito.save()
                log(u'Invalido documento deposito: %s' % deposito.motivo, request, "edit")
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'editrubro':
            try:
                form = RubroForm(request.POST)
                if form.is_valid():
                    rubro = Rubro.objects.get(pk=request.POST['id'])
                    if rubro.valorajuste > 0:
                        return bad_json(mensaje=u'No se puede aplicar el ajuste al rubro porque ya tiene un ajuste anterior.')
                    if form.cleaned_data['valorajuste'] > 0:
                        if rubro.tiene_descuentorecargo() or rubro.es_recargodescuento():
                            return bad_json(mensaje=u'No se puede aplicar el ajuste al rubro porque ya tiene un descuento.')
                        if (rubro.valor - form.cleaned_data['valorajuste']) < rubro.total_pagado():
                            return bad_json(mensaje=u'No se puede aplicar el ajuste al rubro porque excede el valor abonado.')
                        rubro.valorajuste = form.cleaned_data['valorajuste']
                        rubro.valor = rubro.valor - form.cleaned_data['valorajuste']
                        rubro.motivoajuste = form.cleaned_data['motivoajuste']
                    rubro.fechavence = form.cleaned_data['fechavence']
                    rubro.save(request)
                    if form.cleaned_data['valorajuste'] > 0:
                        log(u'Modifico valorajuste del rubro: %s de %s' % (rubro.inscripcion, rubro), request, "edit")
                    else:
                        log(u'Modifico fecha de vencimiento del rubro: %s de %s' % (rubro.inscripcion, rubro), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editdeposito':
            try:
                form = DepositoInscripcionMotivoForm(request.POST)
                if form.is_valid():
                    deposito = DepositoInscripcion.objects.get(pk=request.POST['id'])
                    deposito.motivo = form.cleaned_data['motivo']
                    deposito.save(request)
                    log(u'Modifico rubro: %s de %s' % (persona, deposito), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'adddeposito':
            try:
                form = DepositoInscripcionForm(request.POST, request.FILES)
                if form.is_valid():
                    inscripcion = Inscripcion.objects.get(pk=request.POST['inscripcion'])
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("deposito_", newfile._name)
                    if DepositoInscripcion.objects.filter(cuentabanco=form.cleaned_data['cuentabanco'], fecha=form.cleaned_data['fecha'], referencia=form.cleaned_data['referencia'], ventanilla=True if form.cleaned_data['ventanilla'] else False).exists():
                        return bad_json(mensaje=u'Ya existe ese número de referencia ingresado')
                    deposito = DepositoInscripcion(inscripcion=inscripcion,
                                                   fecha=form.cleaned_data['fecha'],
                                                   ventanilla=True if form.cleaned_data['ventanilla'] else False,
                                                   movilweb=True if form.cleaned_data['movilweb'] else False,
                                                   referencia=form.cleaned_data['referencia'],
                                                   cuentabanco=form.cleaned_data['cuentabanco'],
                                                   valor=form.cleaned_data['valor'],
                                                   motivo=form.cleaned_data['motivo'],
                                                   archivo=newfile,
                                                   procesado=False)
                    deposito.save(request)
                    log(u'Adiciono deposito de inscripcion: %s' % deposito, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'activarrubro':
            try:
                form = RubroForm(request.POST)
                if form.is_valid():
                    rubro = Rubro.objects.get(pk=request.POST['id'])
                    if rubro.tiene_pagos() or rubro.tiene_descuento() or rubro.tiene_recargo() or rubro.es_recargodescuento():
                        return bad_json(mensaje=u'El valor no puede ser modificado.')
                    rubro.fechavence = form.cleaned_data['fechavence']
                    if form.cleaned_data['valor'] <= 0:
                        return bad_json(mensaje=u'El valor no puede ser 0.')
                    rubro.valor = form.cleaned_data['valor']
                    rubro.save(request)
                    log(u'Modifico rubro: %s' % rubro, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addncinterna':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                form = NotaCreditoForm(request.POST)
                if form.is_valid():
                    nc = NotaCredito(inscripcion=inscripcion,
                                     valorinicial=form.cleaned_data['valorinicial'],
                                     motivo=form.cleaned_data['motivo'],
                                     fecha=form.cleaned_data['fecha'])
                    nc.save(request)
                    log(u'Adiciono nota de credito interna: %s - %s' % (inscripcion.persona, nc), request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addanticipado':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                form = RecaudacionAnticipadaForm(request.POST)
                if form.is_valid():
                    valor = form.cleaned_data['valor']
                    ivaaplicado = form.cleaned_data['iva']
                    valoriva = 0
                    if ivaaplicado.porcientoiva > 0:
                        valoriva = null_to_numeric(valor * ivaaplicado.porcientoiva)
                    rubro = Rubro(fecha=datetime.now().date(),
                                  valor=valor,
                                  valoriva=valoriva,
                                  valortotal=null_to_numeric(valor + valoriva, 2),
                                  saldo=null_to_numeric(valor + valoriva, 2),
                                  periodo=form.cleaned_data['periodo'],
                                  inscripcion=inscripcion,
                                  iva=ivaaplicado,
                                  fechavence=datetime.now().date())
                    rubro.save(request)
                    rubrootro = RubroAnticipado(rubro=rubro,
                                                motivo=form.cleaned_data['motivo'])
                    rubrootro.save(request)
                    rubro.actulizar_nombre(nombre='ANTICIPO')
                    log(u'Adiciono rubro tipo anticipado: %s' % rubro, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'liquidar':
            try:
                rubro = Rubro.objects.get(pk=request.POST['id'])
                if rubro.es_recargodescuento():
                    rubroorigen = rubro.origen_recargodescuento().rubro
                    if not rubroorigen.cancelado:
                        return bad_json(mensaje=u'No puede liquidar este rubro sin antes cancelar el origen.')
                form = EliminarRubroForm(request.POST)
                if form.is_valid():
                    valorliquidado = rubro.valor - rubro.total_pagado()
                    liquidado = RubroLiquidado(rubro=rubro,
                                               fecha=datetime.now().date(),
                                               motivo=form.cleaned_data['motivo'],
                                               valor=valorliquidado)
                    liquidado.save(request)
                    rubro.cancelado = True
                    rubro.saldo = 0
                    rubro.save(request)
                    log(u"Liquido rubro: %s" % rubro, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'infoidentificacion':
            try:
                identificacion = request.POST['identificacion']
                if Persona.objects.filter(Q(cedula=identificacion) | Q(pasaporte=identificacion)).exists():
                    persona = Persona.objects.filter(Q(cedula=identificacion) | Q(pasaporte=identificacion))[0]
                    return ok_json({'nombre': persona.nombre_completo(), 'direccion': persona.direccion, 'telefono': persona.telefono, 'tipo': 1, 'email': persona.email})
                elif ClienteFactura.objects.filter(identificacion=identificacion).exists():
                    cliente = ClienteFactura.objects.filter(identificacion=identificacion)[0]
                    return ok_json({'nombre': cliente.nombre, 'direccion': cliente.direccion, 'telefono': cliente.telefono, 'email': cliente.email})
                return bad_json(mensaje=u'No existen datos para la busqueda')
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'segotros':
            try:
                data = {}
                data['inscripcion'] = Inscripcion.objects.get(pk=request.POST['id'])
                data['tiposotros'] = TipoOtroRubro.objects.all()
                data['hoy'] = datetime.now().date()
                data['tiposivaaplicado'] = IvaAplicado.objects.filter(activo=True)
                template = get_template("finanzas/segotros.html")
                json_content = template.render(data)
                return ok_json({'data': json_content})
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'moverpagos':
            try:
                if request.POST['inscripcionorigen'] == '':
                    return bad_json(mensaje=u'Seleccione la ficha origen')
                if request.POST['inscripciondestino'] == '':
                    return bad_json(mensaje=u'Seleccione la ficha destino')
                inscripcionorigen = Inscripcion.objects.get(pk=request.POST['inscripcionorigen'])
                inscripciondestino = Inscripcion.objects.get(pk=request.POST['inscripciondestino'])
                form = MoverPagoRubroForm(request.POST)
                if form.is_valid():
                    listado = request.POST['seleccionados']
                    transferidos = 0
                    if listado:
                        rubros_a_transferir = Rubro.objects.filter(id__in=[int(x) for x in listado.split(',')])
                        for rubro_origen in rubros_a_transferir:
                            tipo_origen = rubro_origen.tipo()
                            rubro_destino = next((r for r in Rubro.objects.filter(inscripcion=inscripciondestino) if r.tipo() == tipo_origen), None)
                            if rubro_destino:
                                if rubro_origen.valor <= rubro_destino.valor:
                                    saldo_restante = rubro_destino.valor - rubro_origen.valor
                                    # Solo modificar el rubro destino si NO tiene pagos
                                    if not rubro_destino.tiene_pagos():
                                        if saldo_restante > 0:
                                            rubro_origen.valor = rubro_destino.valor
                                            rubro_origen.saldo = saldo_restante
                                            rubro_destino.delete()
                                        else:
                                            rubro_destino.delete()  # Eliminar si el saldo es cero
                                    # Transferir el rubro de origen a destino
                                    rubro_origen.inscripcion = inscripciondestino
                                    rubro_origen.save()
                                    transferidos += 1
                                else:
                                    # Si el valor en origen es mayor, no se transfiere
                                    continue
                        if transferidos >= 0:
                            log(u'Transfiere rubros del alumno %s de la ficha %s a la ficha %s' % (inscripciondestino, inscripcionorigen.id, inscripciondestino.id), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'permitediferir':
            try:
                banco = Banco.objects.get(pk=request.POST['id'])
                tipotarjetabanco = TipoTarjetaBanco.objects.get(pk=request.POST['idtt'])
                tipotarjeta = TipoEmisorTarjeta.objects.get(pk=request.POST['idte'])
                lista = []
                for i in banco.mi_diferido(tipotarjeta, tipotarjetabanco):
                    lista.append([i.valordatafast, '1' if i.intereses else '0', '1' if i.difiere else '0', i.nombre])
                return ok_json({'lista': lista})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=3)

        if action == 'generarrubrosposgrado':
            try:
                rubrocuota = RubroCuota.objects.filter(rubro_id=request.POST['id'])[0]
                matricula = rubrocuota.matricula
                matricula.calcular_arancel_posgrado()
                log(u'Edito cuota de posgrado: %s - Rubro: %s' % (matricula,rubrocuota.rubro.id), request, "edit")
                rubroid=rubrocuota.rubro_id
                rubro=Rubro.objects.get(pk=rubroid)
                inscripcion = InscripcionFlags.objects.get(inscripcion_id=rubro.inscripcion_id)
                inscripcion.nogeneracosto=True
                inscripcion.save()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'validapp':
            try:
                Rubro.objects.filter(pk=request.POST['id']).update(validoprontopago=True)
                log(u'Valida rubro para pronto pago - Rubroid: %s' % str(request.POST['id']), request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'novalidapp':
            try:
                Rubro.objects.filter(pk=request.POST['id']).update(validoprontopago=False)
                log(u'Quita rubro como pronto pago - Rubroid: %s' % str(request.POST['id']), request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'revertirajuste':
            try:
                rubro = Rubro.objects.get(pk=request.POST['id'])
                rubro.valor = rubro.valor + rubro.valorajuste
                rubro.motivoajuste = 'SE REVIERTE AJUSTE - VALOR: $ ' + str(rubro.valorajuste)
                rubro.valorajuste = 0
                rubro.save()
                log(u'Se Revierte ajuste del rubro: %s' % rubro, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'inscripcionrubros':
            try:
                inscripcionorigen = Inscripcion.objects.get(pk=request.POST['idorigen'])
                data['rubrosinscripcion'] = inscripcionorigen.rubro_set.all().order_by('-fecha')
                segmento = render(request, "finanzas/inscripcionrubros.html", data)
                return ok_json({"segmento": segmento.content.decode('utf-8')})
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        return bad_json(error=0)

    else:
        data['title'] = u'Consulta de finanzas'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'delrubro':
                try:
                    data['title'] = u'Eliminar Rubro'
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = rubro.inscripcion
                    data['form'] = EliminarRubroForm()
                    return render(request, "finanzas/delrubro.html", data)
                except Exception as ex:
                    pass

            if action == 'protestopagoconcheque':
                try:
                    data['title'] = u'Permitir pago de protesto con Cheque'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "finanzas/protestopagoconcheque.html", data)
                except Exception as ex:
                    pass

            if action == 'generarrubroinscripcion':
                try:
                    data['title'] = u'Generar rubro de inscripción'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "finanzas/generarrubro.html", data)
                except Exception as ex:
                    pass

            if action == 'editrubro':
                try:
                    data['title'] = u'Editar Rubro'
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    data['form'] = RubroForm(initial={'fechavence': rubro.fechavence})
                    return render(request, "finanzas/editrubro.html", data)
                except Exception as ex:
                    return bad_json(mensaje=ex.message)

            if action == 'adddeposito':
                try:
                    data['title'] = u'Nuevo comprobante de pago'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['iid'])
                    data['form'] = DepositoInscripcionForm()
                    return render(request, "finanzas/adddeposito.html", data)
                except Exception as ex:
                    pass

            if action == 'editdeposito':
                try:
                    data['title'] = u'Editar Motivo Depósito'
                    data['deposito'] = deposito = DepositoInscripcion.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['iid'])
                    data['form'] = DepositoInscripcionMotivoForm(initial={'motivo': deposito.motivo})
                    return render(request, "finanzas/editdeposito.html", data)
                except Exception as ex:
                    return bad_json(mensaje=ex.message)

            if action == 'activarrubro':
                try:
                    data['title'] = u'Activar Rubro'
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    data['form'] = RubroForm(initial={'valor': rubro.valor,
                                                      'fechavence': rubro.fechavence})
                    return render(request, "finanzas/activarrubro.html", data)
                except Exception as ex:
                    pass

            if action == 'moverpagos':
                try:
                    data['title'] = u'Mover Pagos'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    persona = Persona.objects.get(pk=inscripcion.persona.id)
                    form = MoverPagoRubroForm()
                    form.adicionar(persona, inscripcion)
                    data['form']=form
                    return render(request, "finanzas/moverpagos.html", data)
                except Exception as ex:
                    pass

            if action == 'rubros':
                try:
                    data['title'] = u'Listado de rubros del alumno'
                    pp = None
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    inscripcion.chequea_mora()
                    flags = inscripcion.mis_flag()
                    rubrosnocancelados = inscripcion.rubro_set.filter(cancelado=False).order_by('cancelado', 'fechavence')
                    rubroscanceldos = inscripcion.rubro_set.filter(cancelado=True).order_by('-fecha')
                    rubros = list(chain(rubrosnocancelados, rubroscanceldos))
                    data['rubros'] = rubros
                    data['reciboscaja'] = inscripcion.recibocajainstitucion_set.all()
                    data['notascredito'] = inscripcion.notacredito_set.all()
                    data['especies'] = TipoEspecieValorada.objects.filter(activa=True)
                    data['tiene_nota_debito'] = RubroNotaDebito.objects.filter(rubro__inscripcion=inscripcion, rubro__cancelado=False).exists()
                    if DescuentoRecargoRubro.objects.filter(recargo=True).exists():
                        ultima = DescuentoRecargoRubro.objects.filter(recargo=True).order_by('-id')[0]
                        data['motivo_recargo'] = ultima.motivo
                        data['porciento_recargo'] = ultima.porciento if ultima.porciento else 0
                    else:
                        data['motivo_recargo'] = ""
                        data['porciento_recargo'] = 0
                    data['depositosinscipcion'] = inscripcion.depositoinscripcion_set.all()
                    data['flags'] = inscripcion.mis_flag()
                    data['ci'] = inscripcion.persona.cedula
                    data['pasaporte'] = inscripcion.persona.pasaporte
                    data['email'] = inscripcion.persona.email
                    data['reporte_0'] = obtener_reporte('listado_deuda_xinscripcion')
                    data['periodos_rubros'] = Periodo.objects.all()
                    data['cobro_deuda_anterior_primero'] = COBRO_DEUDA_ANTERIOR_PRIMERO
                    data['guayas'] = True if inscripcion.persona.provincia_id == 9 else False
                    return render(request, "finanzas/rubros.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'pagar':
                try:
                    data['title'] = 'Pago de Rubros del Alumno'
                    ids = request.GET['ids'].split(",")
                    data['rubros'] = rubros = Rubro.objects.filter(id__in=ids).order_by('fechavence')
                    data['inscripcion'] = inscripcion = rubros[0].inscripcion
                    pp_all_qs = Rubro.objects.filter(inscripcion=inscripcion, validoprontopago=True, cancelado=False, pasivo=False).exclude(pago__isnull=False, pago__valido=True)
                    # para permitir el descuento al seleccionar cualquier subconjunto pero que sean ProntoPago (no necesariamente todos), cambiar a:
                    # solo_pp_seleccionados = rubros_sel_qs.exists() and not rubros_sel_qs.filter(validoprontopago=False).exists()
                    solo_pp_seleccionados_y_todos = (rubros.exists() and not rubros.filter(validoprontopago=False).exists() and rubros.count() == pp_all_qs.count() and pp_all_qs.count() > 0)
                    data['solo_pp_seleccionados_y_todos'] = solo_pp_seleccionados_y_todos
                    data['rubros_descuento'] = []
                    matricula = inscripcion.ultima_matricula_sinextendido()
                    rubros_descuento_por_fp = {}
                    if matricula:
                        precioperiodo = inscripcion.carrera.precio_periodo(inscripcion.mi_nivel().nivel.id,
                                                                matricula.nivel.periodo,
                                                                inscripcion.sede, inscripcion.modalidad)
                        for fp in FormaDePago.objects.exclude(id=FORMA_PAGO_CTAXCRUZAR).order_by("id"):
                            descuento_fp = precioperiodo.detalle_descuento(fp.id) # Obtener el porcentaje
                            if descuento_fp:
                                total_descuento = 0
                                rubros_list = []
                                for rubro in Rubro.objects.filter(id__in=ids, validoprontopago=True):
                                    descuentopp = null_to_numeric(rubro.valor * (descuento_fp.porcentaje / 100), 2)
                                    total_descuento += descuentopp
                                    rubros_list.append({'rubro_id': rubro.id, 'valor_original': rubro.valor, 'descuentopp': descuentopp, 'valor_con_descuento': rubro.valor - descuentopp })
                                if total_descuento > 0:
                                    rubros_descuento_por_fp[fp.id] = {'total_descuento': total_descuento,
                                                                      'fechainicio': descuento_fp.fechainicio.strftime('%Y-%m-%d'),
                                                                      'fechafin': descuento_fp.fechafin.strftime('%Y-%m-%d'),
                                                                      'porcentaje': descuento_fp.porcentaje,
                                                                      'nombre': fp.nombre,
                                                                      'rubros': rubros_list}
                    data['rubros_descuento_por_fp'] = rubros_descuento_por_fp
                    data['pago_efectivo_id'] = FORMA_PAGO_EFECTIVO
                    data['pago_tarjeta_id'] = FORMA_PAGO_TARJETA
                    data['pago_cheque_id'] = FORMA_PAGO_CHEQUE
                    data['pago_deposito_id'] = FORMA_PAGO_DEPOSITO
                    data['pago_transferencia_id'] = FORMA_PAGO_TRANSFERENCIA
                    data['pago_nota_credito_id'] = FORMA_PAGO_NOTA_CREDITO
                    data['pago_recibo_caja_id'] = FORMA_PAGO_RECIBOCAJAINSTITUCION
                    data['pago_retencion_id'] = FORMA_PAGO_RETENCION
                    data['pago_cxcruza_id'] = FORMA_PAGO_CTAXCRUZAR
                    data['tiene_cheque_protestado'] = inscripcion.tiene_cheque_protestado()
                    data['tiene_nota_credito'] = inscripcion.tiene_nota_credito()
                    data['factura'] = caja.puntodeventa.secuenciafactura + 1
                    clientefacturacion = inscripcion.clientefacturacion(request)
                    data['facturaidentificacion'] = clientefacturacion.identificacion
                    data['tipo_identificacion'] = clientefacturacion.tipo
                    data['facturanombre'] = clientefacturacion.nombre
                    data['facturadireccion'] = clientefacturacion.direccion
                    data['facturatelefono'] = clientefacturacion.telefono
                    data['facturaemail'] = clientefacturacion.email
                    data['totalapagar'] = sum([x.saldo for x in rubros])
                    data['deudainicial'] = rubros[0].valortotal
                    form = FormaPagoForm()
                    form.adicionar(inscripcion)
                    data['form'] = form
                    data['pago_tarjeta_nacional_id'] = PAGO_TARJETA_NACIONAL_ID
                    data['otros_bancos_externos_id'] = OTROS_BANCOS_EXTERNOS_ID
                    data['tipo_tarjeta_credito_id'] = TIPO_TARJETA_CREDITO_ID
                    data['tipo_tarjeta_debito_id'] = TIPO_TARJETA_DEBITO_ID
                    data['diferido_tarjeta_corriente_id'] = DIFERIDO_TARJETA_CORRIENTE_ID
                    data['tiene_nota_debito'] = rubros.filter(rubronotadebito__isnull=False).exists()
                    data['tiene_iva'] = rubros.filter(iva_id__gt=1).exists()
                    data['depositos'] = inscripcion.depositoinscripcion_set.filter(autorizado=True, saldo__gt=0)
                    data['facturacion_electronica'] = caja.puntodeventa.facturaelectronica
                    return render(request, "finanzas/pagar.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'pagos':
                try:
                    data['title'] = u'Pagos del rubro'
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    data['descuentos'] = DescuentoRecargoRubro.objects.filter(rubro=rubro, recargo=False)
                    data['pagos'] = Pago.objects.filter(rubro=rubro)
                    data['ci'] = rubro.inscripcion.persona.cedula
                    return render(request, "finanzas/pagos.html", data)
                except Exception as ex:
                    pass

            if action == 'liquidar':
                try:
                    data['title'] = u'Liquidar Rubro'
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    data['form'] = EliminarRubroForm()
                    return render(request, "finanzas/liquidar.html", data)
                except Exception as ex:
                    pass

            if action == 'revertirdescuento':
                try:
                    data['title'] = u'Revertir descuento'
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    return render(request, "finanzas/revertirdescuento.html", data)
                except Exception as ex:
                    pass

            if action == 'addncinterna':
                try:
                    data['title'] = u"Crear Nota de crédito"
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = NotaCreditoForm()
                    return render(request, "finanzas/addncinterna.html", data)
                except Exception as ex:
                    pass

            if action == 'addanticipado':
                try:
                    data['title'] = u"Recaudación anticipada"
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = RecaudacionAnticipadaForm()
                    return render(request, "finanzas/addanticipado.html", data)
                except Exception as ex:
                    pass

            if action == 'depositosnuevos':
                try:
                    data['title'] = u"Depositos ingresados"
                    data['depositos'] = DepositoInscripcion.objects.filter(procesado=False, autorizado=True, saldo__gt=0)
                    return render(request, "finanzas/depositosnuevos.html", data)
                except Exception as ex:
                    pass

            if action == 'generarrubrosposgrado':
                try:
                    data['title'] = u'Generar Rubros de Posgrado'
                    data['rubro'] = Rubro.objects.get(pk=request.GET['id'])
                    return render(request, "finanzas/generarrubrosposgrado.html", data)
                except Exception as ex:
                    pass

            if action == 'validapp':
                try:
                    data['title'] = u'Valida rubro para Pronto Pago'
                    data['rubro'] = Rubro.objects.get(pk=request.GET['id'])
                    return render(request, "finanzas/validapp.html", data)
                except Exception as ex:
                    pass

            if action == 'novalidapp':
                try:
                    data['title'] = u'No Valida rubro para Pronto Pago'
                    data['rubro'] = Rubro.objects.get(pk=request.GET['id'])
                    return render(request, "finanzas/novalidapp.html", data)
                except Exception as ex:
                    pass

            if action == 'revertirajuste':
                try:
                    data['title'] = u'Revertir Ajuste'
                    data['rubro'] = Rubro.objects.get(pk=request.GET['id'])
                    return render(request, "finanzas/revertirajuste.html", data)
                except Exception as ex:
                    pass

            if action == 'valido':
                try:
                    data['title'] = u'Validar documento'
                    data['deposito'] = DepositoInscripcion.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['iid'])
                    return render(request, "finanzas/valido.html", data)
                except Exception as ex:
                    pass

            if action == 'invalido':
                try:
                    data['title'] = u'Invalidar documento'
                    data['deposito'] = DepositoInscripcion.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['iid'])
                    return render(request, "finanzas/invalido.html", data)
                except Exception as ex:
                    pass

            if action == 'procesado':
                try:
                    data['title'] = u'Procesado'
                    data['deposito'] = depositoinscripcion = DepositoInscripcion.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['iid'])
                    data['form'] = CambiarEstadoDepositoInscripcionForm(initial={'estadoprocesado': depositoinscripcion.estadoprocesado})
                    return render(request, "finanzas/procesado.html", data)
                except Exception as ex:
                    pass

            if action == 'pasivo':
                try:
                    data['title'] = u'Deuda Pasiva'
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(id=rubro.inscripcion_id)
                    return render(request, "finanzas/pasivo.html", data)
                except Exception as ex:
                    pass

            if action == 'activo':
                try:
                    data['title'] = u'Activar Deuda Pasiva'
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(id=rubro.inscripcion_id)
                    return render(request, "finanzas/activo.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)

        else:
            try:
                data['title'] = u'Finanzas'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        inscripciones = Inscripcion.objects.filter(Q(persona__nombre1__icontains=search) |
                                                                   Q(persona__nombre2__icontains=search) |
                                                                   Q(persona__apellido1__icontains=search) |
                                                                   Q(persona__apellido2__icontains=search) |
                                                                   Q(persona__cedula__icontains=search) |
                                                                   Q(persona__pasaporte__icontains=search) |
                                                                   Q(identificador__icontains=search) |
                                                                   Q(carrera__nombre__icontains=search)).distinct().order_by('persona__apellido1', 'persona__apellido2', 'persona__nombre1', 'persona__nombre2')
                    else:
                        inscripciones = Inscripcion.objects.filter(Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1])).distinct().order_by('persona__apellido1', 'persona__apellido2', 'persona__nombre1', 'persona__nombre2')
                elif 'id' in request.GET:
                    ids = int(request.GET['id'])
                    inscripciones = Inscripcion.objects.filter(id=ids)
                else:
                    inscripciones = Inscripcion.objects.all().order_by('persona__apellido1', 'persona__apellido2', 'persona__nombre1', 'persona__nombre2')
                paging = MiPaginador(inscripciones, 10)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'finanzas':
                            paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    else:
                        p = paginasesion
                    page = paging.page(p)
                except Exception as ex:
                    p = 1
                    page = paging.page(p)
                request.session['paginador'] = p
                request.session['paginador_url'] = 'finanzas'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['inscripciones'] = page.object_list
                if sesion_caja:
                    data['total_notacredito_sesion'] = sesion_caja.total_notadecredito_sesion()
                    data['total_efectivo_sesion'] = sesion_caja.total_efectivo_sesion()
                    data['cantidad_facturas_sesion'] = sesion_caja.cantidad_facturas_sesion()
                    data['cantidad_recibopago_sesion'] = sesion_caja.cantidad_recibopago_sesion()
                    data['cantidad_cheques_sesion'] = sesion_caja.cantidad_cheques_sesion()
                    data['total_cheque_sesion'] = sesion_caja.total_cheque_sesion()
                    data['cantidad_tarjetas_sesion'] = sesion_caja.cantidad_tarjetas_sesion()
                    data['total_tarjeta_sesion'] = sesion_caja.total_tarjeta_sesion()
                    data['cantidad_depositos_sesion'] = sesion_caja.cantidad_depositos_sesion()
                    data['total_deposito_sesion'] = sesion_caja.total_deposito_sesion()
                    data['cantidad_transferencias_sesion'] = sesion_caja.cantidad_transferencias_sesion()
                    data['total_transferencia_sesion'] = sesion_caja.total_transferencia_sesion()
                    data['cantidad_recibocaja_sesion'] = sesion_caja.cantidad_recibocaja_sesion()
                    data['total_recibocaja_sesion'] = sesion_caja.total_recibocaja_sesion()
                    data['total_otros_ingresos'] = null_to_numeric(ValeCaja.objects.filter(sesion=sesion_caja, tipooperacion=2).distinct().aggregate(valor=Sum('valor'))['valor'], 2)
                    data['total_otros_egresos'] = null_to_numeric(ValeCaja.objects.filter(sesion=sesion_caja, tipooperacion=1).distinct().aggregate( valor=Sum('valor'))['valor'], 2)
                    data['depositos_pendientes_procesar'] = DepositoInscripcion.objects.filter(procesado=False, autorizado=True, saldo__gt=0).count()
                    data['total_sesion'] = sesion_caja.total_sesion()
                data['pago_efectivo_id'] = FORMA_PAGO_EFECTIVO
                data['pago_tarjeta_id'] = FORMA_PAGO_TARJETA
                data['pago_cheque_id'] = FORMA_PAGO_CHEQUE
                data['pago_deposito_id'] = FORMA_PAGO_DEPOSITO
                data['pago_transferencia_id'] = FORMA_PAGO_TRANSFERENCIA
                data['pago_recibo_caja_id'] = FORMA_PAGO_RECIBOCAJAINSTITUCION
                data['reporte_0'] = obtener_reporte("certificado_matricula_alumno")
                data['reporte_1'] = obtener_reporte("reporte_compromiso_pago")
                data['reporte_2'] = obtener_reporte("cronograma_pagos")
                return render(request, "finanzas/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
