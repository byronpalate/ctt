from datetime import datetime

from settings import RUBRO_SEGUNDA_MATRICULA_ID, TIPO_IVA_0_ID, RUBRO_MATRICULA_EXTRAORDINARIA_ID, \
    RUBRO_MATRICULA_ESPECIAL_ID, RUBRO_MODULO_ID, RUBRO_TERCERA_MATRICULA_ID, CUARTO_NIVEL_TITULACION_ID
from ctt.funciones import proximafecha, siguientemes
from ctt.models import Rubro, RubroMatricula, RubroOtroMatricula, null_to_numeric, RubroCuota, RubroAgregacion, \
    RetiroFinanciero, Materia, RubroOtro, DescuentoFormaPago


def costo_materia_posgrado(inscripcion, asignatura, nivel, fecha):
    preciosotros = None
    matriculas = 0
    # valor_segunda_matricula = 0
    # valor_tercera_matricula = 0
    asignaturamalla=None
    modulomalla=None
    malla = inscripcion.mi_malla()
    if malla.asignaturamalla_set.filter(asignatura=asignatura, titulacion=False).exists():
        asignaturamalla = malla.asignaturamalla_set.filter(asignatura=asignatura, titulacion=False)[0]
    if asignaturamalla:
        primerperiodo = inscripcion.mi_primerperiodo()
        if primerperiodo > 0:
            costoperiodo = inscripcion.carrera.precio_posgrado_completo(asignaturamalla.nivelmalla, primerperiodo, inscripcion.sede, inscripcion.modalidad, fecha)
        else:
            costoperiodo = inscripcion.carrera.precio_posgrado_completo(asignaturamalla.nivelmalla, nivel.periodo_id, inscripcion.sede, inscripcion.modalidad, fecha)
        valor_arancel = costoperiodo[0]
        # totalcreditos = asignaturamalla.malla.total_ceditos_nivel_debe_matricularse(asignaturamalla.nivelmalla)
        totalcreditos = asignaturamalla.malla.cantidad_creditos_solo_malla(inscripcion)
        costocreditos = valor_arancel / totalcreditos
        # return [asignaturamalla.creditos * costocreditos, matriculas, valor_segunda_matricula, valor_tercera_matricula]
        return [asignaturamalla.creditos * costocreditos, matriculas]
    elif modulomalla:
        if matriculas >= 1 and preciosotros:
            return [preciosotros.preciomodulo, matriculas, preciosotros.porcentajesegundamatricula, preciosotros.porcentajeterceramatricula]
    return [0, 0, 0, 0]


def costo_materia(inscripcion, asignatura, nivel):
    preciosotros = None
    matriculas = 0
    asignaturamalla = None
    modulomalla = None
    esprontopago = False
    hoy = datetime.now().date()
    es_posgrado = True if (inscripcion.carrera.posgrado) else False
    malla = inscripcion.mi_malla()
    if malla.asignaturamalla_set.filter(asignatura=asignatura, titulacion=False).exists():
        asignaturamalla = malla.asignaturamalla_set.filter(asignatura=asignatura, titulacion=False)[0]
        if inscripcion.recordacademico_set.filter(asignatura=asignatura, aprobada=False).exists():
            record = inscripcion.recordacademico_set.filter(asignatura=asignatura, aprobada=False)[0]
            matriculas = record.historicorecordacademico_set.filter(aprobada=False).count()
    if malla.modulomalla_set.filter(asignatura=asignatura).exists():
        modulomalla = malla.modulomalla_set.filter(asignatura=asignatura)[0]
        if inscripcion.recordacademico_set.filter(asignatura=asignatura, aprobada=False).exists():
            record = inscripcion.recordacademico_set.filter(asignatura=asignatura, aprobada=False)[0]
            matriculas = record.historicorecordacademico_set.filter(aprobada=False).count()
            # matriculas = 0
    preciosotros = inscripcion.carrera.precio_modulo_inscripcion(nivel.periodo, inscripcion.sede, inscripcion.modalidad, malla)
    if asignaturamalla:
        if es_posgrado:
            primerperiodo = inscripcion.mi_primerperiodo()
            if primerperiodo > 0:
                costoperiodo = inscripcion.carrera.precio_periodo(asignaturamalla.nivelmalla, primerperiodo, inscripcion.sede, inscripcion.modalidad)
            else:
                costoperiodo = inscripcion.carrera.precio_periodo(asignaturamalla.nivelmalla, nivel.periodo, inscripcion.sede, inscripcion.modalidad)
        else:
            costoperiodo = inscripcion.carrera.precio_periodo(asignaturamalla.nivelmalla, nivel.periodo, inscripcion.sede, inscripcion.modalidad)
        if DescuentoFormaPago.objects.filter(precioperiodo=costoperiodo, fechainicio__lte=hoy, fechafin__gte=hoy).exists():
            esprontopago = True
        else:
            esprontopago = False
        valor_arancel = costoperiodo.precioarancel
        totalcreditos = asignaturamalla.malla.total_ceditos_nivel_debe_matricularse(asignaturamalla.nivelmalla, inscripcion)
        costocreditos = 0
        if totalcreditos > 0:
            costocreditos = valor_arancel / totalcreditos
        return [asignaturamalla.creditos * costocreditos, matriculas, preciosotros.porcentajesegundamatricula, preciosotros.porcentajeterceramatricula, esprontopago]
    elif modulomalla:
        if matriculas >= 1 and preciosotros:
            return [preciosotros.precioarrastremodulo, matriculas, preciosotros.porcentajesegundamatricula, preciosotros.porcentajeterceramatricula, esprontopago]
    return [0, 0, 0, 0, esprontopago]


def costo_materia_intensivo(inscripcion, asignatura, nivel, materia):
    preciosotros = None
    matriculas = 0
    asignaturamalla = None
    modulomalla = None
    esprontopago = False
    malla = inscripcion.mi_malla()
    # if malla.modulomalla_set.filter(asignatura=asignatura).exists():
    #     modulomalla = malla.modulomalla_set.filter(asignatura=asignatura)[0]
    #     if inscripcion.recordacademico_set.filter(asignatura=asignatura, aprobada=False).exists():
    #         record = inscripcion.recordacademico_set.filter(asignatura=asignatura, aprobada=False)[0]
    #         matriculas = record.historicorecordacademico_set.filter(aprobada=False).count()
    #         # matriculas = 0
    preciosotros = inscripcion.carrera.precio_modulo_inscripcion(nivel.periodo, inscripcion.sede, inscripcion.modalidad,inscripcion.mi_malla())
    if modulomalla:
        if materia.intensivo:
            if matriculas >= 1 and preciosotros:
                return [preciosotros.precioarrastremodulo, matriculas, preciosotros.porcentajesegundamatricula, preciosotros.porcentajeterceramatricula, esprontopago]
            else:
                return [preciosotros.preciomodulo, matriculas, preciosotros.porcentajesegundamatricula, preciosotros.porcentajeterceramatricula, esprontopago]
        else:
            if matriculas >= 1 and preciosotros:
                return [preciosotros.precioarrastremodulo, matriculas, preciosotros.porcentajesegundamatricula, preciosotros.porcentajeterceramatricula, esprontopago]
    return [0, 0, 0, 0, esprontopago]


def costo_materia_adelanto(inscripcion, asignatura, nivel):
    matriculas = 0
    asignaturamalla = None
    modulomalla = None
    esprontopago = False
    malla = inscripcion.mi_malla()
    # if malla.asignaturamalla_set.filter(asignatura=asignatura, titulacion=False).exists():
    #     asignaturamalla = malla.asignaturamalla_set.filter(asignatura=asignatura, titulacion=False)[0]
    #     if inscripcion.recordacademico_set.filter(asignatura=asignatura, aprobada=False).exists():
    #         record = inscripcion.recordacademico_set.filter(asignatura=asignatura, aprobada=False)[0]
    #         matriculas = record.historicorecordacademico_set.filter(aprobada=False).count()
    if malla.modulomalla_set.filter(asignatura=asignatura).exists():
        modulomalla = malla.modulomalla_set.filter(asignatura=asignatura)[0]
        if inscripcion.recordacademico_set.filter(asignatura=asignatura, aprobada=False).exists():
            record = inscripcion.recordacademico_set.filter(asignatura=asignatura, aprobada=False)[0]
            matriculas = record.historicorecordacademico_set.filter(aprobada=False).count()
            # matriculas = 0
    preciosotros = inscripcion.carrera.precio_modulo_inscripcion(nivel.periodo, inscripcion.sede, inscripcion.modalidad, inscripcion.mi_malla())
    if modulomalla:
        # if matriculas >= 1 and preciosotros:
        if preciosotros:
            return [preciosotros.precioadelantoidiomas, matriculas, preciosotros.porcentajesegundamatricula, preciosotros.porcentajeterceramatricula, esprontopago]
    return [0, 0, 0, 0, esprontopago]


def costo_matricula(inscripcion, asignaturas, materias, nivel, fecha):
    malla = inscripcion.mi_malla()
    nivelmalla = inscripcion.mi_nivel().nivel
    valor_matricula = 0
    valor_segunda_matricula = 0
    valor_tercera_matricula = 0
    valor_matricula_extra = 0
    porciento_extra_matricula = 0
    valor_modulo = 0
    cuotas = 1
    meses = 1
    valor_arancel = 0
    valor_arancel_nivelactual = 0
    valor_derechorotativo = 0
    preciosotros = None
    if inscripcion.carrera.precio_periodo(nivelmalla, nivel.periodo, inscripcion.sede, inscripcion.modalidad).generaextraordinaria() == True:
        es_especial = fecha > nivel.fechatopematricula
    else:
        es_especial = False
    es_posgrado = True if (inscripcion.carrera.posgrado) else False
    nogeneracosto = True if (inscripcion.inscripcionflags_set.filter(nogeneracosto=True).exists()) else False
    # if inscripcion.carrera.tipogrado.id == CUARTO_NIVEL_TITULACION_ID:
    #     precioperiodo = inscripcion.carrera.precio_periodo(nivelmalla, nivel.periodo, inscripcion.sede, inscripcion.modalidad, corte=nivel)
    # else:
    if es_posgrado:
        primerperiodo = inscripcion.mi_primerperiodo()
        if primerperiodo > 0:
            precioperiodo = inscripcion.carrera.precio_periodo(nivelmalla, primerperiodo, inscripcion.sede, inscripcion.modalidad)
        else:
            precioperiodo = inscripcion.carrera.precio_periodo(nivelmalla, nivel.periodo, inscripcion.sede, inscripcion.modalidad)
    else:
        precioperiodo = inscripcion.carrera.precio_periodo(nivelmalla, nivel.periodo.id, inscripcion.sede, inscripcion.modalidad)
    cuotas = precioperiodo.cuotas
    meses = precioperiodo.meses
    valor_derechorotativo = precioperiodo.precioderechorotativo
    if DescuentoFormaPago.objects.filter(precioperiodo=precioperiodo, fechainicio__lte=fecha, fechafin__gte=fecha).exists():
        esprontopago = True
    else:
        esprontopago = False
    if nogeneracosto:
        valor_matricula = 0
    else:
        if es_posgrado and inscripcion.documentos_entregados().reingreso == True:
            valor_matricula = 0
        else:
            valor_matricula = precioperiodo.preciomatricula
    preciosotros = inscripcion.carrera.precio_modulo_inscripcion(nivel.periodo, inscripcion.sede, inscripcion.modalidad, malla)
    porciento_extra_matricula = preciosotros.porcentajematriculaextraordinaria

    sm = 0
    tm = 0
    mn = 0
    if not es_posgrado:
        for asignaturamalla in malla.asignaturamalla_set.filter(asignatura__id__in=asignaturas):
            costomateria = costo_materia(inscripcion, asignaturamalla.asignatura, nivel)
            matriculas = costomateria[1]
            # segunda matricula
            if matriculas == 1 and preciosotros:
                if es_posgrado:
                    if nogeneracosto:
                        valor_segunda_matricula = 0
                    else:
                        valor_segunda_matricula += null_to_numeric(preciosotros.preciomodulo, 2)
                else:
                    if valor_matricula > 0 and preciosotros.porcentajesegundamatricula > 0:
                        valor_segunda_matricula += null_to_numeric(valor_matricula * (preciosotros.porcentajesegundamatricula / 100.0), 2)
                sm += 1
            # tercera matricula
            if matriculas == 2 and preciosotros:
                if es_posgrado:
                    if nogeneracosto:
                        valor_tercera_matricula = 0
                    else:
                        valor_tercera_matricula += null_to_numeric(preciosotros.preciomodulo, 2)
                else:
                    if valor_matricula > 0 and preciosotros.porcentajeterceramatricula > 0:
                        valor_tercera_matricula += null_to_numeric(valor_matricula * (preciosotros.porcentajeterceramatricula / 100.0), 2)
                tm += 1
            valor_arancel += costomateria[0]
            if asignaturamalla.nivelmalla == nivelmalla:
                valor_arancel_nivelactual += costomateria[0]
            # materia normal
            mn += 1
        if inscripcion.carrera.id in [63] and valor_arancel == 0:  # idcarrera = 63 es enfermeria
            valor_arancel = null_to_numeric(precioperiodo.precioarancel, 2)
    else:
        # for asignaturamalla in malla.asignaturamalla_set.filter(asignatura__id__in=asignaturas):
        #     sm+=1
        # if inscripcion.documentos_entregados().reingreso==True or sm>0:
        if inscripcion.documentos_entregados().reingreso == True:
            valor_arancel = 0
            for asignaturamalla in malla.asignaturamalla_set.filter(asignatura__id__in=asignaturas):
                costomateria = costo_materia_posgrado(inscripcion, asignaturamalla.asignatura, nivel, fecha)
                matriculas = costomateria[0]
                valor_arancel += matriculas
        else:
            if nogeneracosto:
                valor_arancel = 0
            else:
                valor_arancel = null_to_numeric(precioperiodo.precioarancel, 2)
    for asignaturamodulo in malla.modulomalla_set.filter(asignatura__id__in=asignaturas):
        costomateria = costo_materia(inscripcion, asignaturamodulo.asignatura, nivel)
        matriculas = costomateria[1]
        if Materia.objects.filter(id__in=materias, intensivo=True).exists():
            if matriculas >= 1 and preciosotros:
                valor_modulo = null_to_numeric(valor_modulo + preciosotros.precioarrastremodulo, 2)
            else:
                valor_modulo = null_to_numeric(valor_modulo + preciosotros.preciomodulo, 2)
        else:
            if matriculas >= 1 and preciosotros:
                valor_modulo = null_to_numeric(valor_modulo + preciosotros.precioarrastremodulo, 2)
            else:
                valor_modulo = null_to_numeric(valor_modulo + 0, 2)
    if es_especial:
        if valor_matricula > 0 and porciento_extra_matricula > 0:
            valor_matricula_extra = null_to_numeric(valor_matricula * (porciento_extra_matricula / 100.0), 2)

    # if es_posgrado and mn == (sm+tm):

    if es_posgrado:
        if nogeneracosto:
            valor_total = 0
        else:
            valor_total = null_to_numeric(
                null_to_numeric(valor_matricula, 2) +
                null_to_numeric(valor_segunda_matricula, 2) +
                null_to_numeric(valor_tercera_matricula, 2) +
                null_to_numeric(valor_arancel, 2) +
                null_to_numeric(valor_derechorotativo, 2) +
                valor_matricula_extra, 2)
    else:
        valor_total = null_to_numeric(
            null_to_numeric(valor_matricula, 2) +
            null_to_numeric(valor_segunda_matricula, 2) +
            null_to_numeric(valor_tercera_matricula, 2) +
            null_to_numeric(valor_modulo, 2) +
            null_to_numeric(valor_arancel, 2) +
            null_to_numeric(valor_derechorotativo, 2) +
            valor_matricula_extra, 2)
    return [null_to_numeric(valor_matricula, 2),
            null_to_numeric(valor_segunda_matricula, 2),
            null_to_numeric(valor_tercera_matricula, 2),
            null_to_numeric(valor_matricula_extra, 2),
            cuotas,
            null_to_numeric(valor_modulo, 2),
            meses,
            null_to_numeric(valor_arancel, 2),
            null_to_numeric(valor_total, 2),
            nogeneracosto,
            null_to_numeric(valor_arancel_nivelactual, 2),
            null_to_numeric(valor_derechorotativo, 2),
            esprontopago]


def costo_matricula_posgrados(inscripcion, nivel, fecha):
    malla = inscripcion.mi_malla()
    nivelmalla = inscripcion.mi_nivel().nivel
    valor_matricula = 0
    valor_arancel = 0
    preciosotros = None
    es_especial = fecha > nivel.fechatopematricula
    es_posgrado = True if (inscripcion.carrera.posgrado) else False
    primerperiodo = inscripcion.mi_primerperiodo()
    if primerperiodo > 0:
        precioarancelcompleto = inscripcion.carrera.precio_posgrado_completo(nivelmalla, primerperiodo, inscripcion.sede, inscripcion.modalidad, fecha)
    else:
        precioarancelcompleto = inscripcion.carrera.precio_periodo_posgrado(nivelmalla, nivel.periodo, inscripcion.sede, inscripcion.modalidad, fecha)
    valor_arancelcompleto = precioarancelcompleto[0]
    return [null_to_numeric(valor_arancelcompleto, 2), precioarancelcompleto[1]]


def calculo(matricula):
    fecha_pagos = matricula.fecha
    es_posgrado = True if (matricula.inscripcion.carrera.posgrado) else False
    # CALCULO DE LA MATRICULA
    asignaturas = [x.asignaturareal.id for x in matricula.materiaasignada_set.all()]
    materias = [x.materia.id for x in matricula.materiaasignada_set.all()]
    costomatricula = costo_matricula(matricula.inscripcion, asignaturas, materias, matricula.nivel, matricula.fecha)
    if matricula.es_especial() or matricula.es_extraordinaria():
        if costomatricula[3] > 0:  # valor de extraordinaria
            rubro = Rubro(fecha=fecha_pagos,
                          fechavence=fecha_pagos,
                          valor=costomatricula[3],
                          iva_id=TIPO_IVA_0_ID,
                          valoriva=0,
                          valortotal=costomatricula[3],
                          saldo=costomatricula[3],
                          inscripcion=matricula.inscripcion)
            rubro.save()
            ro = RubroOtroMatricula(rubro=rubro,
                                    matricula=matricula,
                                    tipo=RUBRO_MATRICULA_EXTRAORDINARIA_ID if matricula.es_extraordinaria() else RUBRO_MATRICULA_ESPECIAL_ID,
                                    descripcion='MATRICULA EXTRAORDINARIA' if matricula.es_extraordinaria() else 'MATRICULA ESPECIAL')
            ro.save()
            rubro.actulizar_nombre()
    if costomatricula[0] > 0:   # valor de matricula
        if not RubroMatricula.objects.filter(matricula=matricula).exists():
            rubro = Rubro(fecha=fecha_pagos,
                          fechavence=fecha_pagos,
                          valor=costomatricula[0],
                          iva_id=TIPO_IVA_0_ID,
                          valoriva=0,
                          valortotal=costomatricula[0],
                          saldo=costomatricula[0],
                          inscripcion=matricula.inscripcion,
                          validoprontopago=True if costomatricula[12] else False)
            rubro.save()
            ro = RubroMatricula(rubro=rubro,
                                matricula=matricula)
            ro.save()
            if es_posgrado:
                rubro.actulizar_nombre('MATRICULA PROGRAMA')
            else:
                rubro.actulizar_nombre()

    if costomatricula[0] > 0 or es_posgrado:
        if costomatricula[4] > 1:  # cuotas
            cuota_final = null_to_numeric(costomatricula[7] / costomatricula[4], 2)
        else:
            cuota_final = null_to_numeric(costomatricula[7], 2)  # costomatricula[7] = valor del arancel
        proximafechapago = fecha_pagos
        fechasiguiente = fecha_pagos
        for cuota in range(1, costomatricula[4] + 1):
            if cuota > 1:
                fecha_pagos = siguientemes(fechasiguiente)
            if not RubroCuota.objects.filter(matricula=matricula, cuota=cuota).exists():
                rubro = Rubro(fecha=fecha_pagos,
                              fechavence=proximafechapago,
                              valor=cuota_final,
                              iva_id=TIPO_IVA_0_ID,
                              valoriva=0,
                              valortotal=cuota_final,
                              saldo=cuota_final,
                              inscripcion=matricula.inscripcion,
                              valornivelactual=costomatricula[10],
                              validoprontopago=True if costomatricula[12] else False)
                rubro.save()
                ro = RubroCuota(rubro=rubro,
                                matricula=matricula,
                                totalcuota=costomatricula[4],
                                cuota=cuota)
                ro.save()
                if es_posgrado:
                    rubro.actulizar_nombre('ARANCEL PROGRAMA')
                else:
                    rubro.actulizar_nombre()
                fechasiguiente = proximafechapago
            proximafechapago = proximafecha(proximafechapago, costomatricula[6])
    if costomatricula[1] > 0:  # segunda matricula
        valor_segunda_matricula = null_to_numeric(costomatricula[1], 2)
        rubro = Rubro(fecha=fecha_pagos,
                      fechavence=fecha_pagos,
                      valor=valor_segunda_matricula,
                      iva_id=TIPO_IVA_0_ID,
                      valoriva=0,
                      valortotal=valor_segunda_matricula,
                      saldo=valor_segunda_matricula,
                      inscripcion=matricula.inscripcion,
                      validoprontopago=True if costomatricula[12] else False)
        rubro.save()
        if matricula.inscripcion.carrera.posgrado:
            ro = RubroCuota(rubro=rubro,
                            matricula=matricula,
                            cuota=1)
        else:
            descripcion = 'SEGUNDA MATRICULA'
            ro = RubroOtroMatricula(rubro=rubro,
                                    matricula=matricula,
                                    tipo=RUBRO_SEGUNDA_MATRICULA_ID,
                                    descripcion=descripcion)
        ro.save()
        rubro.actulizar_nombre()
    if costomatricula[2] > 0:  # tercer matricula
        valor_tercera_matricula = null_to_numeric(costomatricula[2], 2)
        rubro = Rubro(fecha=fecha_pagos,
                      fechavence=fecha_pagos,
                      valor=valor_tercera_matricula,
                      iva_id=TIPO_IVA_0_ID,
                      valoriva=0,
                      valortotal=valor_tercera_matricula,
                      saldo=valor_tercera_matricula,
                      inscripcion=matricula.inscripcion,
                      validoprontopago=True if costomatricula[12] else False)
        rubro.save()
        if matricula.inscripcion.carrera.posgrado:
            ro = RubroCuota(rubro=rubro,
                            matricula=matricula,
                            cuota=1)
        else:
            ro = RubroOtroMatricula(rubro=rubro,
                                    matricula=matricula,
                                    tipo=RUBRO_TERCERA_MATRICULA_ID,
                                    descripcion='TERCERA MATRICULA')
        ro.save()
        rubro.actulizar_nombre()
    if costomatricula[5] > 0:  # valor modulo
        valor_modulos = null_to_numeric(costomatricula[5], 2)
        rubro = Rubro(fecha=fecha_pagos,
                      fechavence=fecha_pagos,
                      valor=valor_modulos,
                      iva_id=TIPO_IVA_0_ID,
                      valoriva=0,
                      valortotal=valor_modulos,
                      saldo=valor_modulos,
                      inscripcion=matricula.inscripcion)
        rubro.save()
        ro = RubroOtroMatricula(rubro=rubro,
                                matricula=matricula,
                                tipo=RUBRO_MODULO_ID,
                                descripcion='MODULOS')
        ro.save()
        intensivo = True if Materia.objects.filter(id__in=materias, intensivo=True) else False
        if intensivo:
            rubro.actulizar_nombre('INGLES INTENSIVO')
        else:
            rubro.actulizar_nombre()


def calcular_rubros(matricula):
    calculo(matricula=matricula)


def calculo_costo_total(matricula):
    # fecha_pagos = matricula.fecha
    es_posgrado = True if (matricula.inscripcion.carrera.posgrado) else False
    # CALCULO DE LA MATRICULA
    asignaturas = [x.asignaturareal.id for x in matricula.materiaasignada_set.all()]
    materias = [x.materia.id for x in matricula.materiaasignada_set.all()]
    costomatricula = costo_matricula(matricula.inscripcion, asignaturas, materias, matricula.nivel, matricula.fecha)
    return costomatricula


def calculo_rubros_homologacion(inscripcion):
    numerocreditos = 0
    for materias in PreHomologacionInscripcion.objects.filter(inscripcion=inscripcion):
        numerocreditos += materias.asignaturamalla.creditos
    preciosotros = inscripcion.carrera.precio_modulo_inscripcion(inscripcion.periodo, inscripcion.sede, inscripcion.modalidad, inscripcion.mi_malla())
    if numerocreditos > 0:
        rubro = Rubro(fecha=datetime.now().date(),
                      fechavence=datetime.now().date(),
                      valor=numerocreditos*preciosotros.preciohexterna,
                      iva_id=TIPO_IVA_0_ID,
                      valoriva=0,
                      valortotal=numerocreditos*preciosotros.preciohexterna,
                      saldo=numerocreditos*preciosotros.preciohexterna,
                      inscripcion=inscripcion)
        rubro.actulizar_nombre('HOMOLOGACION EXTERNA')
        rubro.save()
        ro = RubroOtro(rubro=rubro,
                       tipo_id=23)
        ro.save()


def calcular_rubros_homologacion(inscripcion):
    calculo_rubros_homologacion(inscripcion=inscripcion)


def calculo_arancel_posgrado(matricula):
    costoarancelcompleto = costo_matricula_posgrados(matricula.inscripcion, matricula.nivel, matricula.fecha)
    if costoarancelcompleto[0] > 0:
        if matricula.rubrocuota_set.filter(matricula=matricula,matricula__rubrocuota__totalcuota=1).exists():
            rubrocuota = RubroCuota.objects.filter(matricula_id=matricula.id,totalcuota=1)[0]
            rubro = Rubro.objects.get(pk=rubrocuota.rubro_id)
            rubro.valor = costoarancelcompleto[0]
            rubro.save()


def calcular_rubros_posgrado(matricula):
    calculo_arancel_posgrado(matricula=matricula)


def calcular_agregacion(matricula, asignatura, tiponominacion):
    ma = matricula.materiaasignada_set.filter(asignaturareal=asignatura)[0]
    inscripcion = matricula.inscripcion
    if tiponominacion == 'moduloasignar':
        if ma.materia.intensivo:
            costom = costo_materia_intensivo(inscripcion, asignatura, matricula.nivel, ma.materia)
        else:
            costom = costo_materia(inscripcion, asignatura, matricula.nivel)
    else:
        costom = costo_materia_adelanto(inscripcion, asignatura, matricula.nivel)
    costo = costom[0]
    matriculas = costom[1]
    segunda = costom[2]
    tercera = costom[3]
    nivelmalla1 = inscripcion.mi_nivel().nivel
    valor_matricula = 0
    if inscripcion.carrera.tipogrado.id == CUARTO_NIVEL_TITULACION_ID:
        precioperiodo = inscripcion.carrera.precio_periodo(nivelmalla1, matricula.nivel.periodo, inscripcion.sede, inscripcion.modalidad, corte=matricula.nivel)
    else:
        precioperiodo = inscripcion.carrera.precio_periodo(nivelmalla1, matricula.nivel.periodo, inscripcion.sede, inscripcion.modalidad)
        valor_matricula = precioperiodo.preciomatricula
    rubro = Rubro(fecha=datetime.now().date(),
                  fechavence=datetime.now().date(),
                  valor=costo,
                  iva_id=TIPO_IVA_0_ID,
                  valoriva=0,
                  valortotal=costo,
                  saldo=costo,
                  inscripcion=inscripcion,
                  validoprontopago=True if costom[4] else False)
    rubro.save()
    ro = RubroAgregacion(rubro=rubro,
                         materiaasignada=ma,
                         adelanto=True if tiponominacion == 'moduloadelanto' else False)
    ro.save()
    if ma.materia.intensivo:
        nombrerubro = 'INGLES INTENSIVO - ' + str(ma.materia.asignatura)
        rubro.actulizar_nombre(nombrerubro)
    else:
        if tiponominacion == 'moduloadelanto':
            nombrerubro = 'MODULO DE IDIOMAS ADELANTADO - ' + str(ma.materia.asignatura)
            rubro.actulizar_nombre(nombrerubro)
        else:
            rubro.actulizar_nombre()
    malla = inscripcion.mi_malla()
    if malla.asignaturamalla_set.filter(asignatura=asignatura).exists():
        if matriculas >= 1 and matriculas < 2:
            valor_segunda_matricula = null_to_numeric(valor_matricula * (segunda / 100.0), 2)
            rubro = Rubro(fecha=datetime.now().date(),
                          fechavence=datetime.now().date(),
                          valor=valor_segunda_matricula,
                          iva_id=TIPO_IVA_0_ID,
                          valoriva=0,
                          valortotal=valor_segunda_matricula,
                          saldo=valor_segunda_matricula,
                          inscripcion=inscripcion)
            rubro.save()
            if matricula.inscripcion.carrera.posgrado:
                descripcion = 'COSTO MODULO'
            else:
                descripcion = 'SEGUNDA MATRICULA'
            ro = RubroOtroMatricula(rubro=rubro,
                                    matricula=inscripcion.matricula(),
                                    tipo=RUBRO_SEGUNDA_MATRICULA_ID,
                                    descripcion=descripcion)
            ro.save()
            if ma.materia.intensivo:
                rubro.actulizar_nombre('INGLES INTENSIVO')
            else:
                rubro.actulizar_nombre()
        if matriculas >= 2:
            valor_tercera_matricula = null_to_numeric(valor_matricula * (tercera / 100.0), 2)
            rubro = Rubro(fecha=datetime.now().date(),
                          fechavence=datetime.now().date(),
                          valor=valor_tercera_matricula,
                          iva_id=TIPO_IVA_0_ID,
                          valoriva=0,
                          valortotal=valor_tercera_matricula,
                          saldo=valor_tercera_matricula,
                          inscripcion=inscripcion)
            rubro.save()
            ro = RubroOtroMatricula(rubro=rubro,
                                    matricula=matricula,
                                    tipo=RUBRO_TERCERA_MATRICULA_ID,
                                    descripcion='TERCERA MATRICULA')
            ro.save()
            rubro.actulizar_nombre()

# def calcular_agregacion_posgrado(matricula, asignatura):
#     precioperiodo=[]
#     ma = matricula.materiaasignada_set.filter(asignaturareal=asignatura)[0]
#     inscripcion = matricula.inscripcion
#     costom = costo_materia_posgrado(inscripcion, asignatura, matricula.nivel)
#     costo = costom[0]
#     matriculas = costom[1]
#     segunda = costom[2]
#     tercera = costom[3]
#     nivelmalla1 = inscripcion.mi_nivel().nivel
#     valor_matricula = 0
#     precioperiodo = costom
#     valor_matricula = precioperiodo[0]
#     rubro = Rubro(fecha=datetime.now().date(),
#                   fechavence=datetime.now().date(),
#                   valor=costo,
#                   iva_id=TIPO_IVA_0_ID,
#                   valoriva=0,
#                   valortotal=costo,
#                   saldo=costo,
#                   inscripcion=inscripcion)
#     rubro.save()
#     ro = RubroAgregacion(rubro=rubro,
#                          materiaasignada=ma)
#     ro.save()
#     rubro.actulizar_nombre()
#     malla = inscripcion.mi_malla()
#     if malla.asignaturamalla_set.filter(asignatura=asignatura).exists():
#         if matriculas >= 1 and matriculas < 2:
#             valor_segunda_matricula = null_to_numeric(valor_matricula * (segunda / 100.0), 2)
#             rubro = Rubro(fecha=datetime.now().date(),
#                           fechavence=datetime.now().date(),
#                           valor=valor_segunda_matricula,
#                           iva_id=TIPO_IVA_0_ID,
#                           valoriva=0,
#                           valortotal=valor_segunda_matricula,
#                           saldo=valor_segunda_matricula,
#                           inscripcion=inscripcion)
#             rubro.save()
#             if matricula.inscripcion.coordinacion.id in [18, 19]:
#                 descripcion = 'COSTO MODULO'
#             else:
#                 descripcion = 'SEGUNDA MATRICULA'
#             ro = RubroOtroMatricula(rubro=rubro,
#                                     matricula=inscripcion.matricula(),
#                                     tipo=RUBRO_SEGUNDA_MATRICULA_ID,
#                                     descripcion=descripcion)
#             ro.save()
#             rubro.actulizar_nombre()
#         if matriculas >= 2:
#             valor_tercera_matricula = null_to_numeric(valor_matricula * (tercera / 100.0), 2)
#             rubro = Rubro(fecha=datetime.now().date(),
#                           fechavence=datetime.now().date(),
#                           valor=valor_tercera_matricula,
#                           iva_id=TIPO_IVA_0_ID,
#                           valoriva=0,
#                           valortotal=valor_tercera_matricula,
#                           saldo=valor_tercera_matricula,
#                           inscripcion=inscripcion)
#             rubro.save()
#             ro = RubroOtroMatricula(rubro=rubro,
#                                     matricula=matricula,
#                                     tipo=RUBRO_TERCERA_MATRICULA_ID,
#                                     descripcion='TERCERA MATRICULA')
#             ro.save()
#             rubro.actulizar_nombre()


def calculo_derecho_rotativo(matricula):
    fecha_pagos = matricula.fecha
    es_posgrado = True if (matricula.inscripcion.carrera.posgrado) else False
    # CALCULO DE LA MATRICULA
    asignaturas = [x.asignaturareal.id for x in matricula.materiaasignada_set.all()]
    materias = [x.materia.id for x in matricula.materiaasignada_set.all()]
    costomatricula = costo_matricula(matricula.inscripcion, asignaturas, materias, matricula.nivel, matricula.fecha)
    if costomatricula[11] > 0:
        valor_derechorotativo = null_to_numeric(costomatricula[11], 2)
        rubro = Rubro(fecha=fecha_pagos,
                      fechavence=fecha_pagos,
                      valor=valor_derechorotativo,
                      iva_id=TIPO_IVA_0_ID,
                      periodo=matricula.nivel.periodo,
                      valoriva=0,
                      valortotal=valor_derechorotativo,
                      saldo=valor_derechorotativo,
                      inscripcion=matricula.inscripcion)
        rubro.save()
        ro = RubroOtro(rubro=rubro,
                       tipo_id=15)
        ro.save()
        rubro.actulizar_nombre('DERECHO INTERNADO ROTATIVO')


def calculo_eliminacionmateria(materiaasignada, responsable, motivo):
    if materiaasignada.matricula.inscripcion.carrera.tipogrado.id == CUARTO_NIVEL_TITULACION_ID:
        costomateria = costo_materia(materiaasignada.matricula.inscripcion, materiaasignada.asignaturareal, materiaasignada.matricula.nivel)
    else:
        costomateria = costo_materia(materiaasignada.matricula.inscripcion, materiaasignada.asignaturareal, materiaasignada.matricula.nivel)
    if costomateria[0] > 0:
        retirofinanciero = RetiroFinanciero(inscripcion=materiaasignada.matricula.inscripcion,
                                            fecha=datetime.now().date(),
                                            motivo=motivo,
                                            periodo=materiaasignada.matricula.nivel.periodo,
                                            asignatura=materiaasignada.asignaturareal,
                                            valor=null_to_numeric(costomateria[0], 2),
                                            responsable=responsable)
        retirofinanciero.save()


def post_cierre_matricula(matricula):
    pass
