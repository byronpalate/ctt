# coding=utf-8
import operator
import os
import sys
import time

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeOperators



from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP

from dateutil.relativedelta import *
from django.contrib.auth.models import User, Group
from django.db import models
from django.db.models import F, PROTECT, Prefetch, UniqueConstraint
from django.db.models.aggregates import Sum, Avg, Min, Max
from django.db.models.query import QuerySet
from django.db.models.query_utils import Q
from django.utils import timezone
from django.db.models.functions import Coalesce

from settings import CLASES_HORARIO_ESTRICTO, CLASES_APERTURA_ANTES, CLASES_APERTURA_DESPUES, ARCHIVO_TIPO_SYLLABUS, \
    ARCHIVO_TIPO_DEBERES, NOTA_ESTADO_EN_CURSO, NOTA_ESTADO_APROBADO, CANTIDAD_MATRICULAS_MAXIMAS, \
    UTILIZA_VALIDACION_CALIFICACIONES, CLASES_CIERRE_ANTES, PREPROYECTO_ESTADO_APROBADO_ID, \
    PREPROYECTO_ESTADO_PENDIENTE_ID, PREPROYECTO_ESTADO_RECHAZADO_ID, GENERAR_RUBRO_MORA_CUOTA, \
    GENERAR_RUBRO_MORA_MATRICULA, \
    ENVIO_SOLO_CORREO_INSTITUCIONAL, MATRICULA_ESPECIAL_ID, MATRICULA_EXTRAORDINARIA_ID, MATRICULA_REGULAR_ID, \
    TIPO_DOCENTE_TEORIA, TIPO_DOCENTE_PRACTICA, SOLICITUD_APERTURACLASE_APROBADA_ID, \
    SOLICITUD_APERTURACLASE_RECHAZADA_ID, SOLICITUD_APERTURACLASE_PENDIENTE_ID, TIEMPO_DEDICACION_MEDIO_TIEMPO_ID, \
    TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID, TIEMPO_DEDICACION_TECNICO_DOCENTE_ID, CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID, \
    CRITERIO_PRACTICAS_TIEMPO_COMPLETO_ID, MAXIMO_HORAS_DOCENCIA_TIEMPO_COMPLETO, CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID, \
    CRITERIO_PRACTICAS_MEDIO_TIEMPO_ID, MAXIMO_HORAS_DOCENCIA_MEDIO_TIEMPO, DIAS_VENCIMIENTO_SOLICITUD, \
    TIEMPO_DEDICACION_PARCIAL_ID, \
    CRITERIO_HORAS_CLASE_PARCIAL_ID, CRITERIO_PRACTICAS_PARCIAL_ID, \
    CRITERIO_HORAS_CLASE_TECNICO_DOCENTE_ID, CRITERIO_PRACTICAS_TECNICO_DOCENTE_ID, \
    MAXIMO_HORAS_DOCENCIA_PARCIAL, MAXIMO_HORAS_DOCENCIA_TECNICO_DOCENTE, \
    SOLICITUD_SECRETARIA_MATRICULA_GRATUITAS, TIPO_INSCRIPCION_REGULAR, \
    TIPO_GRATUIDAD_PARCIAL, TIPO_GRATUIDAD_TOTAL, \
    TIPO_GRATUIDAD_NINGUNA, TIPO_INSCRIPCION_IRREGULAR, PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD, TIPO_IVA_0_ID, \
    TIPO_RESPUESTA_ENCUESTA_TEXTO_ID, SOLICITUD_NUMERO_AUTOMATICO, PUEDE_ESPECIFICAR_CANTIDAD_SOLICITUD_SECRETARIA, \
    CONVENIO_ESTADO_PENDIENTE, CONVENIO_ESTADO_APROBADO, CONVENIO_ESTADO_RECHAZADO, RUBRO_OTRO_ARANCEL_ID, \
    RUBRO_OTRO_MATRICULA_ID, RUBRO_OTRO_OTROS_EDUCATIVOS_ID, RUBRO_OTRO_DERECHOS_ESPECIES_ID, \
    RUBRO_OTRO_CURSOS_LIBRE_CONFIGURACION_ID, RUBRO_OTRO_CURSOS_UNIDAD_TITULACION_ID, RUBRO_OTRO_SOLICITUD_ID, \
    TIEMPO_PRORROGA_UNO, TIEMPO_PRORROGA_DOS, TIEMPO_ACTUALIZAON_CONOCIMIENTO, TIPO_ESTADO_TITULACION_PRORROGA_UNO, \
    TIPO_ESTADO_TITULACION_PRORROGA_DOS, TIPO_ESTADO_TITULACION_ESPECIAL, TIPO_ESTADO_NO_TITULACION, \
    UTILIZA_GRATUIDADES, MODELO_NIVELACION, TIPO_PERIODO_POSGRADO, TIPO_PERIODO_GRADO, RAZA_ID, \
    PROYECTOINVESTIGACION_ESTADO_PENDIENTE_ID, PROYECTOINVESTIGACION_ESTADO_APROBADO_ID, \
    PROYECTOINVESTIGACION_ESTADO_RECHAZADO_ID, TERCER_NIVEL_TITULACION_ID, CUARTO_NIVEL_TITULACION_ID, \
    PERFIL_ESTUDIANTE_ID, PERFIL_ADMINISTRATIVO_ID, \
    PERFIL_PROFESOR_ID, PERFIL_EMPLEADOR_ID, TIPO_COLEGIO_FISCAL, TIPO_COLEGIO_MUNICIPAL, TIPO_COLEGIO_PARTICULAR, \
    TIPO_COLEGIO_FISCOMISIONAL, TIPO_RESPUESTA_ENCUESTA_FECHA_ID, CARRERA_FORMACION_CONTINUA_ID, COLEGIO_UTI_ID, \
    PROCESADOR_PAGO_DATAFAST, TIPO_CONVENIO_INDIVIDUAL, PROVEEDOR_PAGOONLINE_PAYPHONE, \
    OTROS_BANCOS_EXTERNOS_ID, PROVEEDOR_PAGOONLINE_DATAFAST, TIPO_IVA_15_ID, APP_DOMAIN, SITE_ROOT, FORMA_PAGO_TARJETA, \
    PERFIL_CLIENTE_ID
from settings import NOTA_ESTADO_REPROBADO, NOTA_ESTADO_SUPLETORIO, NIVEL_MALLA_CERO, \
    NIVEL_MALLA_UNO, SEXO_FEMENINO, SEXO_MASCULINO, TIPO_MORA_RUBRO, GENERAR_RUBRO_MORA, VALOR_MORA_RUBRO
from ctt.funciones import enletras, validarRGB
from ctt.tasks import send_mail, send_html_mail
from django.core.validators import MinValueValidator

def ctt_list_classes():
    listclass = []
    current_module = sys.modules[__name__]
    for key in dir(current_module):
        if isinstance(getattr(current_module, key), type):
            try:
                eval(key + '.objects')
                listclass.append(key)
            except:
                pass
    return listclass


def null_to_numeric(valor, decimales=0):
    if decimales >= 0:
        if decimales >= 1:
            return float(str(Decimal(str(valor) if valor else 0).quantize(Decimal('.' + ''.zfill(decimales - 1) + '1'), rounding=ROUND_HALF_UP) if valor else 0))
        else:
            return float(str(Decimal(str(valor) if valor else 0).quantize(Decimal('1.'), rounding=ROUND_HALF_UP) if valor else 0))
    return valor if valor else 0


def null_to_decimal(valor, decimales=None):
    if decimales >= 0:
        if decimales >= 1:
            return Decimal(str(valor) if valor else 0).quantize(Decimal('.' + ''.zfill(decimales - 1) + '1'), rounding=ROUND_HALF_UP) if valor else 0
        else:
            return Decimal(str(valor) if valor else 0).quantize(Decimal('1.'), rounding=ROUND_HALF_UP) if valor else 0
    return Decimal(valor if valor else 0)


def null_to_text(text, upper=True, trim=True, cap=False, lower=False, transform=True):
    if not text:
        return ''
    if transform:
        if upper:
            text = text.upper()
        if cap:
            text = text.capitalize()
        if lower:
            text = text.lower()
    if trim:
        text = text.strip()
    return text


def id_search(param):
    try:
        return int(param)
    except:
        return 0


class CustomQuerySet(QuerySet):
    def delete(self):
        for i in self:
            i.delete()


class ActiveManager(models.Manager):
    def get_query_set(self):
        return CustomQuerySet(self.model, using=self._db)


TIPOS_NOTICIAS = (
    (1, u'INFORMATIVA'),
    (2, u'URGENTE'),
    (3, u'ADMINISTRATIVA'),
    (4, u'ESTUDIANTES'),
    (5, u'PROFESORES')
)


ACTIVIDAD_RUCRIMPE = (
    (0, u'--'),
    (1, u'Emprendimiento'),
    (2, u'Actividades Profesionales (Relacionadas al perfil de su carrera'),
    (3, u'Actividades Profesionales (NO relacionadas al perfil de su carrera'),
)

TIPOS_IDENTIFICACION = (
    (1, u'CEDULA'),
    (2, u'RUC'),
    (3, u'PASAPORTE')
)

class TiposIdentificacion(models.IntegerChoices):
    CEDULA = 1, 'CEDULA'
    RUC = 2, 'RUC'
    PASAPORTE = 3, 'PASAPORTE'


class TipoFactura(models.IntegerChoices):
    FISICA = 1, 'FÍSICA'
    ELECTRONICA = 2, 'ELECTRÓNICA'


class TiposMalla(models.IntegerChoices):
    HORAS = 1, 'HORAS'
    CREDITOS = 2, 'CRÉDITOS'


TIPOS_BECA = (
    (1, u'TOTAL'),
    (2, u'PARCIAL')
)

TIPO_ALIAS = (
    ('', u'--'),
    ('AB.', u'AB.'),
    ('ARQ.', u'ARQ.'),
    ('CPA.', u'CPA.'),
    ('DR.', u'DR.'),
    ('ING.', u'ING.'),
    ('LIC.', u'LIC.'),
    ('MBA.', u'MBA.'),
    ('MDI.', u'MDI.'),
    ('MG.', u'MG.'),
    ('MSc.', u'MSc.'),
    ('PHD.', u'PHD.'),
    ('PSIC.', u'PSIC.'),
    ('TLGO.', u'TLGO.'),
    ('TEC.', u'TEC.'),
    ('ESP.', u'ESP.'),
    ('PP.', u'PP.'),
)




DIAS_CHOICES = (
    (1, u'LUNES'),
    (2, u'MARTES'),
    (3, u'MIERCOLES'),
    (4, u'JUEVES'),
    (5, u'VIERNES'),
    (6, u'SABADO'),
    (7, u'DOMINGO')
)

TIPO_APENDICE_CHOICES = (
    (1, u'TABLAS'),
    (2, u'IMAGENES'),
    (3, u'GRAFICOS')
)


MESES_CHOICES = (
    (1, u'ENERO'),
    (2, u'FEBRERO'),
    (3, u'MARZO'),
    (4, u'ABRIL'),
    (5, u'MAYO'),
    (6, u'JUNIO'),
    (7, u'JULIO'),
    (8, u'AGOSTO'),
    (9, u'SEPTIEMBRE'),
    (10, u'OCTUBRE'),
    (11, u'NOVIEMBRE'),
    (12, u'DICIEMBRE')
)




ESTADO_INSCRIPCION = (
    (1, u'PENDIENTE'),
    (2, u'ADMITIDO'),
    (3, u'NO ADMITIDO')
)


CERTIFICACION_IDIOMA = (
    (1, u'PRESENTO'),
    (2, u'NO PRESENTO'),
    (3, u'EXAMEN')
)




TIPO_MENSAJE = (
    (1, u'ENVIADO'),
    (2, u'RECIBIDO'),
)


TIPO_CALCULO_MALLAS = (
    (1, u'HORAS'),
    (2, u'CREDITOS'),
)


TIPOS_PARAMETRO_REPORTE = (
    (1, u'TEXTO'),
    (2, u'NUMERO ENTERO'),
    (3, u'NUMERO DECIMAL'),
    (4, u'VERDADERO O FALSO'),
    (5, u'REGISTRO DE DATOS'),
    (6, u'FECHA'),
    (7, u'LISTA'),
    (8, u'LISTA DEFINIDA'),
)

ESTADOS_NOTICIAS = (
    (1, u'PENDIENTE'),
    (2, u'APROBADA'),
    (3, u'RECHAZADA')
)

ESTADOS_MATRICULA = (
    (1, u'APROBADO'),
    (2, u'NO APROBADO'),
    (3, u'RETIRADO'),
)

TIPO_REQUEST_CHOICES = (
    (1, u'GET'),
    (2, u'POST')
)

ACTIVE_DIRECTORY_CHOICES = (
    (1, u'CREAR'),
    (2, u'MODIFICAR'),
    (3, u'DESACTIVAR')
)

class DiasEvaluacion(models.IntegerChoices):
    SEMANA_1 = 7, "1 SEMANA ANTES"
    SEMANA_2 = 14, "2 SEMANAS ANTES"
    MES_1 = 30, "1 MES ANTES"
    SEMANAS_6 = 45, "6 SEMANAS ANTES"
    SEMANAS_8 = 60, "8 SEMANAS ANTES"
    SEMANAS_9 = 67, "9 SEMANAS ANTES"
    SEMANAS_10 = 74, "10 SEMANAS ANTES"

class Periodicidad(models.IntegerChoices):
    DIARIO = 1, "DIARIO"
    SEMANAL = 2, "SEMANAL"
    MENSUAL = 3, "MENSUAL"

class TipoAlias(models.IntegerChoices):
    NINGUNO = 0, '--'
    ABOGADO = 1, 'AB.'
    ARQUITECTO = 2, 'ARQ.'
    CONTADOR_PUBLICO_AUT = 3, 'CPA.'
    DOCTOR = 4, 'DR.'
    INGENIERO = 5, 'ING.'
    LICENCIADO = 6, 'LIC.'
    MASTER_MBA = 7, 'MBA.'
    MASTER_DIR_INST = 8, 'MDI.'
    MAGISTER = 9, 'MG.'
    MASTER_SCIENCE = 10, 'MSc.'
    DOCTORADO = 11, 'PHD.'
    PSICOLOGO = 12, 'PSIC.'
    TECNOLOGO = 13, 'TLGO.'
    TECNICO = 14, 'TEC.'
    ESPECIALISTA = 15, 'ESP.'
    PRESBITERO_PASTOR = 16, 'PP.'

class TiposBeca(models.IntegerChoices):
    TOTAL = 1, 'TOTAL'
    PARCIAL = 2, 'PARCIAL'

class TiposFinanciamientoBeca(models.IntegerChoices):
    IES = 1, 'IES'
    SENESCYT = 2, 'SENESCYT'
    OTRO = 3, 'OTRO'
    TRANSFERENCIAS_ESTADO = 4, 'TRANSFERENCIAS DEL ESTADO'


TIPO_EMISION_FACTURA = (
    (1, u'NORMAL'),
    (2, u'POR INDISPONIBILIDAD')
)
TIPO_AMBIENTE_FACTURACION = (
    (1, u'PRUEBAS'),
    (2, u'PRODUCCIÓN')
)

TIPOS_PAGO_NIVEL = (
    (1, u'SEGUNDA MATRICULA'),
    (2, u'TERCERA MATRICULA'),
    (3, u'MATRICULA EXTRAORDINARIA'),
    (4, u'MATRICULA ESPECIAL'),
    (5, u'MODULOS')
)
OPCIONES_DESCUENTO_CURSOS = (
    (1, u'ALUMNOS'),
    (2, u'EGRESADOS'),
    (3, u'ADMINISTRATIVOS'),
    (4, u'DOCENTES'),
    (5, u'EXTERNOS'),
    (6, u'GRADUADOS'),
)
TIPOS_APROBACION_PROTOCOLO = (
    (0, u'--------'),
    (1, u'CEISH'),
    (2, u'Comité de Ética asistencial'),
    (3, u'Otro')
)
class Perms(models.Model):
    class Meta:
        permissions = (
            ("puede_modificar_datos_admin", "Modificar datos de administracionn"),
            ("puede_modificar_horarios", "Modificar horarios"),
            ("puede_modificar_niveles", "Modificar niveles"),
            ("puede_modificar_rolpago_profesores", "Modificar rolpago profesores"),
            ("puede_modificar_carreras", "Modificar carreras"),
            ("puede_modificar_mallas", "Modificar mallas"),
            ("puede_modificar_silabos", "Modificar silabos"),
            ("puede_modificar_cursos", "Modificar cursos"),
            ("puede_modificar_pagos_curso", "Modificar pagos curso"),
            ("puede_adicionar_rubros", "Adicionar rubros"),
            ("puede_modificar_rubros", "Modificar rubros"),
            ("puede_autorizar_cobros", "Autorizar cobros")
        )


class ModeloBase(models.Model):
    """ Modelo base para todos los modelos del proyecto """
    from django.contrib.auth.models import User
    usuario_creacion = models.ForeignKey(User, related_name='+', blank=True, null=True, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    usuario_modificacion = models.ForeignKey(User, related_name='+', blank=True, null=True, on_delete=models.CASCADE)
    fecha_modificacion = models.DateTimeField(blank=True, null=True)

    def en_uso(self):
        import django.apps
        modelos = django.apps.apps.get_models()
        """ Método que verifica si el modelo esta en uso """
        try:
            for rel in self._meta.get_fields():
                try:
                    related = rel.related_model.objects.filter(**{rel.field.name: self})
                    if related.exists():
                        return True
                except AttributeError:
                    pass
            return False
        except:
            pass
        return True

    objects = ActiveManager()

    def extra_delete(self):
        return [True, False]

    def delete(self, force=True, extra=None, *args, **kwargs):
        extra = self.extra_delete()
        if not extra[0]:
            raise Exception('No se puede eliminar')
        if extra[1]:
            if self.en_uso():
                raise Exception('Registros relacionados')
        super(ModeloBase, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        usuario = None
        if len(args):
            usuario = args[0].user.id
        if self.id:
            self.usuario_modificacion_id = usuario if usuario else 1
            self.fecha_modificacion = datetime.now()
        else:
            self.usuario_creacion_id = usuario if usuario else 1
            self.fecha_creacion = datetime.now()
        models.Model.save(self)

    class Meta:
        abstract = True


def modeloevaluativo_generico():
    return True



def total_matriculas_activas():
    return Matricula.objects.filter(cerrada=False, retiromatricula__isnull=True).count()


def total_matriculados(periodo):
    return Matricula.objects.filter(nivel__cerrado=False, nivel__periodo=periodo, retiromatricula__isnull=True).count()


def total_matriculados_con_provincia(periodo):
    return Matricula.objects.filter(nivel__cerrado=False, nivel__periodo=periodo, inscripcion__persona__provincia__isnull=False, retiromatricula__isnull=True).count()


def dia_semana_correcto(dia, mes, anio, dia_semana):
    return dia_semana == date(anio, mes, dia).isoweekday()


def custom_string_export(resultado):
    return resultado.replace(u"ñ", u"n").replace(u"Ñ", u"N").replace(u"á", u"a").replace(u"é", u"e").replace(u"í", u"i").replace(u"ó", u"o").replace(u"ú", u"u").replace(u"Á", u"A").replace(u"É", u"E").replace(u"Í", u"I").replace(u"Ó", u"O").replace(u"Ú", u"U")


def mi_institucion():
    return TituloInstitucion.objects.all()[0]

def minimo_a_pagar(periodo):
    return ValoresMinimosPeriodoBecaMatricula.objects.filter(periodo=periodo)[0]


def years_ago(years, stardate, day=None):
    if day:
        day -= 1
    else:
        day = stardate.day
    month = stardate.month
    year = stardate.year
    try:
        return date(year - years, month, day)
    except:
        return years_ago(years, stardate, day)


def years_future(years, stardate, day=None):
    if day:
        day -= 1
    else:
        day = stardate.day
    month = stardate.month
    year = stardate.year
    try:
        return date(year + years, month, day)
    except:
        return years_ago(years, stardate, day)


def valoracion_calificacion(nota):
    if ValoracionCalificacion.objects.filter(inicio__lte=nota, fin__gte=nota).exists():
        return ValoracionCalificacion.objects.filter(inicio__lte=nota, fin__gte=nota)[0]
    return None

class NivelTitulacion(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Niveles de titulación"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(NivelTitulacion, self).save(*args, **kwargs)


class DetalleNivelTitulacion(ModeloBase):
    niveltitulacion = models.ForeignKey(NivelTitulacion, blank=True, null=True, verbose_name=u"Nivel titulacion", on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Detalle niveles de titulación"
        unique_together = ('nombre', 'niveltitulacion')

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(DetalleNivelTitulacion, self).save(*args, **kwargs)


class Pais(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")
    codigosniese = models.CharField(max_length=15, default='', verbose_name=u'Codigo Sniese')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Paises"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigosniese = null_to_text(self.codigosniese)
        super(Pais, self).save(*args, **kwargs)


class Nacionalidad(ModeloBase):
    nombremasculino = models.CharField(default='', max_length=100, verbose_name=u"Nacionalidad Masculina")
    nombrefemenino = models.CharField(default='', max_length=100, verbose_name=u"Nacionalidad Femenina")
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nacionalidad")
    pais = models.ForeignKey(Pais, blank=True, null=True, verbose_name=u'País', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Nacionalidades"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombrefemenino = null_to_text(self.nombrefemenino)
        self.nombremasculino = null_to_text(self.nombremasculino)
        self.nombre = null_to_text(self.nombre)
        super(Nacionalidad, self).save(*args, **kwargs)


class Provincia(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")
    alias = models.CharField(default='', max_length=50, blank=True, verbose_name=u'Alias')
    codigosniese = models.CharField(max_length=15, default='', verbose_name=u'Codigo Sniese')
    codigoiso = models.CharField(max_length=10, default='', verbose_name=u'Codigo iso')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Provincias"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def cantidad_matriculados(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__provincia=self, nivel__periodo=periodo, retiromatricula__isnull=True).count()

    def cantidad_matriculados_carrera(self, periodo, carrera):
        return Matricula.objects.filter(inscripcion__persona__provincia=self, inscripcion__carrera=carrera, nivel__periodo=periodo, retiromatricula__isnull=True).count()

    def porciento_matriculados(self, periodo):
        total = total_matriculados(periodo)
        if total:
            return null_to_numeric((self.cantidad_matriculados(periodo) / float(total)) * 100.0, 2)
        return 0

    def porciento_matriculados_con_provincia(self, periodo):
        total = total_matriculados_con_provincia(periodo)
        if total:
            return null_to_numeric((self.cantidad_matriculados(periodo) / float(total)) * 100.0, 2)
        return 0

    def cantidad_total_estudiantes_provincias(self, periodo, sede):
        return Inscripcion.objects.filter(matricula__nivel__periodo=periodo, persona__provincia=self, sede=sede).distinct().count()

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigosniese = null_to_text(self.codigosniese)
        super(Provincia, self).save(*args, **kwargs)


class Canton(ModeloBase):
    provincia = models.ForeignKey(Provincia, blank=True, null=True, verbose_name=u"Provincia", on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")
    codigosniese = models.CharField(max_length=15, default='', verbose_name=u'Codigo Sniese')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Cantones"
        ordering = ['nombre']

    def cantidad_matriculados(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__canton=self, nivel__periodo=periodo, retiromatricula__isnull=True).count()

    def porciento_matriculados(self, periodo):
        total = total_matriculados(periodo)
        if total:
            return null_to_numeric((self.cantidad_matriculados(periodo) / float(total)) * 100.0, 2)
        return 0

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigosniese = null_to_text(self.codigosniese)
        super(Canton, self).save(*args, **kwargs)


class TipoColegio(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u' Nombre')
    codigosniese = models.CharField(max_length=15, default='', verbose_name=u'Codigo Sniese')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de Colegios"
        ordering = ['nombre']
        unique_together = ('nombre',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("TipoColegio.objects.filter(Q(nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_alias(self):
        return [self.nombre]

    def flexbox_repr(self):
        return self.nombre + ' - ' + str(self.id)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigosniese = null_to_text(self.codigosniese)
        super(TipoColegio, self).save(*args, **kwargs)


class Colegio(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    tipocolegio = models.ForeignKey(TipoColegio, blank=True, null=True, verbose_name=u'Tipo colegio', on_delete=models.CASCADE)
    codigo = models.CharField(default='', max_length=100, verbose_name=u'Codigo')
    provincia = models.ForeignKey(Provincia, blank=True, null=True, verbose_name=u'Provincia', on_delete=models.CASCADE)
    canton = models.ForeignKey(Canton, blank=True, null=True, verbose_name=u'Canton', on_delete=models.CASCADE)
    estado = models.BooleanField(default=True, verbose_name=u'Estado')

    def __str__(self):
        return u'%s - %s - %s' % (self.nombre, self.provincia, self.canton)

    class Meta:
        verbose_name_plural = u"Colegios"
        ordering = ['nombre', 'provincia', 'canton']

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Colegio.objects.filter(Q(nombre__contains='%s') | Q(codigo__contains='%s') | Q(id=id_search('%s')))" % (q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_alias(self):
        return [self.nombre]

    def flexbox_repr(self):
        return self.nombre + " - " + self.tipocolegio.nombre + " - " + self.provincia.nombre + " - " + self.canton.nombre + " - " + self.codigo + ' - ' + str(self.id)

    def extra_delete(self):
        return [True, False]

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigo = null_to_text(self.codigo)
        super(Colegio, self).save(*args, **kwargs)


class CampoAmplioConocimiento(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    codigo = models.CharField(default='', max_length=50, verbose_name=u'Código')
    codigointernacional = models.CharField(max_length=50, null=True, blank=True, verbose_name=u'Código Internacional')

    def __str__(self):
        return u'%s' % self.nombre


class CampoEspecificoConocimiento(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    codigo = models.IntegerField(default=0, verbose_name=u'Código')
    campoamplio = models.ForeignKey(CampoAmplioConocimiento, verbose_name=u'Campo Amplio de Conocimiento', on_delete=models.CASCADE)
    codigointernacional = models.CharField(max_length=50, null=True, blank=True, verbose_name=u'Código Internacional')

    def __str__(self):
        return u'%s' % self.nombre


class CampoDetalladoConocimiento(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    codigo = models.IntegerField(default=0, verbose_name=u'Código')
    campoespecifico = models.ForeignKey(CampoEspecificoConocimiento, verbose_name=u'Campo Amplio de Conocimiento', on_delete=models.CASCADE)
    codigointernacional = models.CharField(max_length=50, null=True, blank=True, verbose_name=u'Código Internacional')

    def __str__(self):
        return u'%s | %s' % (self.nombre, self.codigointernacional)


class Modulo(ModeloBase):
    url = models.CharField(default='', max_length=100, verbose_name=u'URL')
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    descripcion = models.CharField(default='', max_length=200, verbose_name=u'Descripción')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')
    externo = models.BooleanField(default=False, verbose_name=u'Externo')

    def __str__(self):
        return u'%s (/%s)' % (self.nombre, self.url)

    class Meta:
        verbose_name_plural = u"Modulos"
        ordering = ['nombre']
        unique_together = ('url',)

    def save(self, *args, **kwargs):
        self.url = null_to_text(self.url, lower=True)
        self.nombre = null_to_text(self.nombre, cap=True)
        self.descripcion = null_to_text(self.descripcion, cap=True)
        super(Modulo, self).save(*args, **kwargs)


class GruposModulos(ModeloBase):
    from django.contrib.auth.models import Group
    grupo = models.ForeignKey(Group, on_delete=models.CASCADE)
    modulos = models.ManyToManyField(Modulo, verbose_name=u'Modulos')

    def __str__(self):
        return u'%s' % self.grupo.name

    class Meta:
        verbose_name_plural = u"Grupos de modulos"
        ordering = ['grupo']
        unique_together = ('grupo',)

    def modulos_activos(self):
        return self.modulos.filter(activo=True)




class Carrera(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    nombreingles = models.CharField(default='', max_length=100, verbose_name=u'Nombre Ingles')
    alias = models.CharField(default='', max_length=50, blank=True, verbose_name=u'Alias')
    mencion = models.CharField(default='', max_length=100, blank=True, verbose_name=u'Mención')
    activa = models.BooleanField(default=True, verbose_name=u"Estado")
    costoinscripcion = models.FloatField(default=0, verbose_name=u"Costo de inscripción")
    tipogrado = models.ForeignKey(NivelTitulacion, blank=True, null=True, on_delete=models.CASCADE)
    tiposubgrado = models.ForeignKey(DetalleNivelTitulacion, blank=True, null=True, on_delete=models.CASCADE)
    posgrado = models.BooleanField(default=False, verbose_name=u"Posgrado")
    codigotalentohumano = models.CharField(max_length=15, default='', verbose_name=u'Codigo ta')
    campodetalladoconocimiento = models.ForeignKey(CampoDetalladoConocimiento, null=True, blank=True, verbose_name=u'Campo Detallado Conocimiento', on_delete=models.CASCADE)
    periodos = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Períodos')
    modulos = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Módulos')
    cartaaceptacion = models.CharField(default='', blank=True, null=True, max_length=200, verbose_name=u'cartaaceptacion')

    def __str__(self):
        return (u'%s CON MENCION EN %s' % (self.nombre, self.mencion)) if self.mencion else u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Carreras"
        ordering = ['nombre', 'mencion']
        unique_together = ('nombre', 'mencion')

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Carrera.objects.filter(Q(nombre__icontains='%s') | Q(mencion__icontains='%s') | Q(id=id_search('%s')))" % (q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.nombre_completo() + ' - ' + str(self.id)

    def extra_delete(self):
        if self.en_uso():
            return [False, False]
        return [True, False]

    def nombre_completo(self):
        return self.nombre + (' CON MENCION EN ' + self.mencion if self.mencion else "")

    def profesores_periodo(self, periodo, coordinacion):
        return Profesor.objects.filter(profesormateria__materia__nivel__periodo=periodo, profesormateria__materia__nivel__nivellibrecoordinacion__coordinacion__carrera=self, profesormateria__materia__nivel__nivellibrecoordinacion__coordinacion=coordinacion).distinct()

    def cantidad_facturas(self):
        return Factura.objects.filter(pagos__sesion__fecha=datetime.now().date(), pagos__rubro__inscripcion__carrera=self).distinct().count()

    def total_pagos(self):
        return null_to_numeric(Pago.objects.filter(rubro__inscripcion__carrera=self, valido=True).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def total_pagos_rango(self, inicio, fin):
        return null_to_numeric(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, rubro__inscripcion__carrera=self, valido=True).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def total_pagos_fecha(self, fecha):
        return null_to_numeric(Pago.objects.filter(fecha=fecha, rubro__inscripcion__carrera=self, valido=True).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def cantidad_facturas_rango_fechas(self, inicio, fin):
        return Factura.objects.filter(fecha__gte=inicio, fecha__lte=fin, pagos__rubro__inscripcion__carrera=self).distinct().count()

    def total_pagos_rango_fechas(self, inicio, fin):
        return null_to_numeric(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, rubro__inscripcion__carrera=self, valido=True).distinct().aggregate(valor=Sum('valor'))['sum'], 2)

    def total_pagos_por_fechas(self, inicio, fin):
        return null_to_numeric(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, valido=True).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def cantidad_facturas_por_fechas(self, inicio, fin):
        return Factura.objects.filter(fecha__gte=inicio, fecha__lte=fin).distinct().count()

    def porciento_cantidad_facturas(self, inicio, fin):
        if self.cantidad_facturas_por_fechas(inicio, fin):
            return null_to_numeric((self.cantidad_facturas_rango_fechas(inicio, fin) / float(self.cantidad_facturas_por_fechas(inicio, fin))) * 100.0, 2)
        return 0

    def porciento_valor_pagos(self, inicio, fin):
        return null_to_numeric((self.total_pagos_rango_fechas(inicio, fin) / float(self.total_pagos_por_fechas(inicio, fin))) * 100.0, 2)

    def valor_deudores_activos_30dias(self):
        hoy = datetime.now().date()
        fechavence = hoy - timedelta(days=30)
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy, fechavence__gte=fechavence, inscripcion__carrera=self).aggregate(valor=Sum('valor'))['valor'], 2)

    def valor_apagar_activos_30dias(self):
        hoy = datetime.now().date()
        fechavence = (datetime.now() + timedelta(days=30)).date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy, fechavence__gte=fechavence, inscripcion__carrera=self).aggregate(valor=Sum('valor'))['valor'], 2)

    def valor_deudores_activos_31_90dias(self):
        hoy = (datetime.now() - timedelta(days=31)).date()
        fechavence = (datetime.now() - timedelta(days=90)).date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lte=hoy, fechavence__gte=fechavence, inscripcion__carrera=self).aggregate(valor=Sum('valor'))['valor'], 2)

    def valor_apagar_activos_31_90dias(self):
        hoy = (datetime.now() + timedelta(days=31)).date()
        fechavence = (datetime.now() + timedelta(days=90)).date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__gte=hoy, fechavence__lte=fechavence, inscripcion__carrera=self).aggregate(valor=Sum('saldo'))['valor'], 2)

    def valor_deudores_activos_mas_90dias(self):
        hoy = (datetime.now() - timedelta(days=91)).date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lte=hoy, inscripcion__carrera=self).aggregate(valor=Sum('valor'))['valor'], 2)

    def valor_apagar_activos_mas_90dias(self):
        hoy = (datetime.now() + timedelta(days=91)).date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__gte=hoy, inscripcion__carrera=self).aggregate(valor=Sum('saldo'))['valor'], 2)

    def valor_deudores_activos_total(self):
        return self.valor_deudores_activos_30dias() + self.valor_deudores_activos_31_90dias() + self.valor_deudores_activos_mas_90dias()

    def valor_deudores_activos_total_sede(self, sede):
        hoy = datetime.now().date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, pasivo=False, fechavence__lt=hoy, inscripcion__carrera=self, inscripcion__sede=sede).exclude(inscripcion__modalidad__id=3).aggregate(valor=Sum('saldo'))['valor'], 2)

    def valor_deudores_activos_total_posgrado(self):
        hoy = datetime.now().date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, pasivo=False, fechavence__lt=hoy, inscripcion__carrera=self).aggregate(valor=Sum('saldo'))['valor'], 2)

    def valor_deudores_activos_total_modalidad(self, modalidad):
        hoy = datetime.now().date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, pasivo=False, fechavence__lt=hoy, inscripcion__carrera=self, inscripcion__modalidad=modalidad).aggregate(valor=Sum('saldo'))['valor'], 2)

    def valor_apagar_activos_total(self):
        return self.valor_apagar_activos_30dias() + self.valor_apagar_activos_31_90dias() + self.valor_apagar_activos_mas_90dias()

    def valor_deudas_activos_total(self):
        return self.valor_deudores_activos_total() + self.valor_apagar_activos_total()

    def cantidad_total_deudores(self):
        return Inscripcion.objects.filter(rubro__fechavence__lt=datetime.now().date(), rubro__cancelado=False, retirocarrera=None, carrera=self).distinct().count()

    def cantidad_total_apagar(self):
        return Inscripcion.objects.filter(rubro__fechavence__gt=datetime.now().date(), rubro__cancelado=False, retirocarrera=None, carrera=self).distinct().count()

    def cantidad_matriculados(self, periodo):
        return Matricula.objects.filter(inscripcion__carrera=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados_mujeres(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__sexo_id=SEXO_FEMENINO, inscripcion__carrera=self, nivel__periodo=periodo, retiromatricula__isnull=True).count()

    def cantidad_matriculados_modalidad(self, modalidad):
        return Matricula.objects.filter(inscripcion__carrera=self, cerrada=False, inscripcion__modalidad=modalidad).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados_modalidad_sede(self, modalidad, sede):
        return Matricula.objects.filter(inscripcion__carrera=self, cerrada=False, inscripcion__modalidad=modalidad, inscripcion__sede=sede).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados_hombres(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__sexo_id=SEXO_MASCULINO, inscripcion__carrera=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados_beca(self, periodo):
        return Matricula.objects.filter(becado=True, inscripcion__carrera=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def porciento_matriculados_beca(self, periodo):
        if self.cantidad_matriculados(periodo):
            return null_to_numeric((self.cantidad_matriculados_beca(periodo) / float(self.cantidad_matriculados(periodo))) * 100.0, 2)
        return 0

    def cantidad_matriculados_discapacidad(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__perfilinscripcion__tienediscapacidad=True, inscripcion__carrera=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def porciento_matriculados_discapacidad(self, periodo):
        if self.cantidad_matriculados(periodo):
            return null_to_numeric((self.cantidad_matriculados_discapacidad(periodo) / float(self.cantidad_matriculados(periodo))) * 100.0, 2)
        return 0

    def cantidad_matriculados_provincia(self, provincia, periodo):
        return Matricula.objects.filter(inscripcion__persona__provincia=provincia, inscripcion__carrera=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados_canton(self, canton, periodo):
        return Matricula.objects.filter(inscripcion__persona__canton=canton, inscripcion__carrera=self, nivel__periodo=periodo, retiromatricula__isnull=True).distinct().count()

    def matriculados_menor_30(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__nacimiento__gte=years_ago(30, datetime.now()), inscripcion__persona__nacimiento__lte=datetime.now().date(), inscripcion__carrera=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def matriculados_31_40(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__nacimiento__gte=years_ago(40, datetime.now()), inscripcion__persona__nacimiento__lte=years_ago(31, datetime.now()), inscripcion__carrera=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def matriculados_41_50(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__nacimiento__gte=years_ago(50, datetime.now()), inscripcion__persona__nacimiento__lte=years_ago(41, datetime.now()), inscripcion__carrera=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def matriculados_51_60(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__nacimiento__gte=years_ago(60, datetime.now()), inscripcion__persona__nacimiento__lte=years_ago(51, datetime.now()), inscripcion__carrera=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def matriculados_mayor_61(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__nacimiento__lte=years_ago(61, datetime.now()), inscripcion__carrera=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def coordinador(self, coordinacion):
        if CoordinadorCarrera.objects.filter(carrera=self, coordinacion=coordinacion).exists():
            return CoordinadorCarrera.objects.filter(carrera=self, coordinacion=coordinacion)[0]
        return None

    def coordinaciones(self):
        return self.coordinacion_set.all()

    def matriculados(self, periodo):
        return Matricula.objects.filter(inscripcion__carrera=self, nivel__periodo=periodo).distinct().count()

    def inscritos(self):
        return Inscripcion.objects.filter(carrera=self).count()

    def competencias(self):
        return CompetenciaEspecifica.objects.filter(carrera=self).count()

    def cantidad_niveles(self):
        return Nivel.objects.filter(nivellibrecoordinacion__coordinacion__carrera=self).distinct().count()

    def promedio_estudiantes_docencia(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, proceso__periodo=periodo).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_autoevaluacion_docencia(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=2, proceso__periodo=periodo).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_par_docencia(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=3, proceso__periodo=periodo).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_directivo_docencia(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=4, proceso__periodo=periodo).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_general_docencia(self, periodo):
        return null_to_numeric((self.promedio_estudiantes_docencia(periodo) + self.promedio_autoevaluacion_docencia(periodo) + self.promedio_par_docencia(periodo) + self.promedio_directivo_docencia(periodo)) / 4.0, 1)

    def promedio_estudiantes_investigacion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, proceso__periodo=periodo).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_autoevaluacion_investigacion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=2, proceso__periodo=periodo).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_par_investigacion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=3, proceso__periodo=periodo).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_directivo_investigacion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=4, proceso__periodo=periodo).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_general_investigacion(self, periodo):
        return null_to_numeric((self.promedio_estudiantes_investigacion(periodo) + self.promedio_autoevaluacion_investigacion(periodo) + self.promedio_par_investigacion(periodo) + self.promedio_directivo_investigacion(periodo)) / 4.0, 1)

    def promedio_estudiantes_gestion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, proceso__periodo=periodo).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_autoevaluacion_gestion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=2, proceso__periodo=periodo).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_par_gestion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=3, proceso__periodo=periodo).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_directivo_gestion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=4, proceso__periodo=periodo).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_general_gestion(self, periodo):
        return null_to_numeric((self.promedio_estudiantes_gestion(periodo) + self.promedio_autoevaluacion_gestion(periodo) + self.promedio_par_gestion(periodo) + self.promedio_directivo_gestion(periodo)) / 4.0, 1)

    def mis_niveles_periodo(self, periodo):
        return self.nivel_set.filter(carrera=self, periodo=periodo)

    def total_matriculados_retirados(self, periodo, coordinacion):
        return Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=self, nivel__nivellibrecoordinacion__coordinacion=coordinacion, retiromatricula__isnull=False).distinct().count()

    def total_matriculados(self, periodo, coordinacion):
        return Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=self, nivel__nivellibrecoordinacion__coordinacion=coordinacion).exclude(retiromatricula__isnull=False).distinct().count()

    def total_matriculados_modalidad(self, periodo, coordinacion, modalidad):
        return Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=self, nivel__nivellibrecoordinacion__coordinacion=coordinacion, nivel__modalidad=modalidad).exclude(retiromatricula__isnull=False).distinct().count()

    def total_inscritos_periodo(self, periodo, coordinacion):
        return Inscripcion.objects.filter(periodo=periodo, carrera=self, coordinacion=coordinacion).count()

    def total_inscritos_periodo_modalidad(self, periodo, coordinacion, modalidad):
        return Inscripcion.objects.filter(periodo=periodo, carrera=self, coordinacion=coordinacion, modalidad=modalidad).count()

    def total_inscritos(self, coordinacion):
        return Inscripcion.objects.filter(carrera=self, coordinacion=coordinacion).exclude(retirocarrera__isnull=False).count()

    def total_inscritos_modalidad(self, coordinacion, modalidad):
        return Inscripcion.objects.filter(carrera=self, coordinacion=coordinacion, modalidad=modalidad).exclude(retirocarrera__isnull=False).count()

    def total_matriculados_regular(self, periodo, coordinacion):
        return Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=self, nivel__nivellibrecoordinacion__coordinacion=coordinacion, tipomatricula__id=MATRICULA_REGULAR_ID).exclude(retiromatricula__isnull=False).distinct().count()

    def total_matriculados_extraordinarias(self, periodo, coordinacion):
        return Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=self, nivel__nivellibrecoordinacion__coordinacion=coordinacion, tipomatricula__id=MATRICULA_EXTRAORDINARIA_ID).exclude(retiromatricula__isnull=False).distinct().count()

    def total_matriculados_especiales(self, periodo, coordinacion):
        return Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=self, nivel__nivellibrecoordinacion__coordinacion=coordinacion, tipomatricula__id=MATRICULA_ESPECIAL_ID).exclude(retiromatricula__isnull=False).distinct().count()

    def costo_coordinacion(self, coordinacion):
        if CostoInscripcionCoordinacionCarrera.objects.filter(carrera=self, coordinacion=coordinacion).exists():
            return CostoInscripcionCoordinacionCarrera.objects.filter(carrera=self, coordinacion=coordinacion)[0]
        return None

    def tiene_coordinacion(self, coordinacionsel):
        for coord in self.coordinaciones():
            if coord == coordinacionsel:
                return True
        return False

    def mis_mallas(self):
        return self.malla_set.all()

    def mis_modalidades(self):
        return Modalidad.objects.filter(malla__carrera=self).distinct()

    def precio_periodo(self, nivel, periodo, sede, modalidad, corte=None):
        if self.tipogrado.id == CUARTO_NIVEL_TITULACION_ID:
            if self.preciosperiodo_set.filter(periodo=periodo, nivel=nivel, sede=sede, modalidad=modalidad, cortes=corte).exists():
                prec_periodo = self.preciosperiodo_set.filter(periodo=periodo, nivel=nivel, sede=sede, modalidad=modalidad, cortes=corte)[0]
            else:
                prec_periodo = PreciosPeriodo(periodo=periodo,
                                              nivel=nivel,
                                              carrera=self,
                                              cortes=corte,
                                              modalidad=modalidad,
                                              sede=sede,
                                              preciomatricula=0,
                                              precioarancel=0,
                                              precioderechorotativo=0,
                                              fecha=periodo.inicio)
                prec_periodo.save()
                prec_periodo.generardetalle()
        else:
            if self.preciosperiodo_set.filter(periodo=periodo, nivel=nivel, sede=sede, modalidad=modalidad).exists():
                prec_periodo = self.preciosperiodo_set.filter(periodo=periodo, nivel=nivel, sede=sede, modalidad=modalidad)[0]
            else:
                prec_periodo = PreciosPeriodo(periodo=periodo,
                                              nivel=nivel,
                                              carrera=self,
                                              modalidad=modalidad,
                                              sede=sede,
                                              preciomatricula=0,
                                              precioarancel=0,
                                              precioderechorotativo=0,
                                              fecha=periodo.inicio)
                prec_periodo.save()
                prec_periodo.generardetalle()
        return prec_periodo

    def precio_periodo_posgrado(self, nivel, periodo, sede, modalidad, corte=None):
        nivelinicio = nivel.id
        precioarancelcompleto = 0
        totalniveles = self.preciosperiodo_set.filter(periodo=periodo, sede=sede, modalidad=modalidad).exclude(precioarancel=0).count()
        for niveles in range(nivelinicio, totalniveles):
            if self.preciosperiodo_set.filter(periodo=periodo, nivel=niveles, sede=sede, modalidad=modalidad, cortes=corte).exists():
                prec_periodo = self.preciosperiodo_set.filter(periodo=periodo, nivel=niveles, sede=sede, modalidad=modalidad, cortes=corte)[0]
                precioarancelcompleto += prec_periodo.precioarancel
        if prec_periodo.descuentoformapago_set.filter(fechainicio__lte=fecha, fechafin__gte=fecha).exists():
            esprontopago = True
        else:
            esprontopago = False
        return [precioarancelcompleto, esprontopago]

    def precio_posgrado_completo(self, nivel, periodo, sede, modalidad, fecha, corte=None):
        preciocompleto = 0
        totalniveles = self.preciosperiodo_set.filter(periodo=periodo, sede=sede, modalidad=modalidad).exclude(precioarancel=0).count()
        for niveles in range(1, totalniveles + 1):
            if self.preciosperiodo_set.filter(periodo=periodo, nivel=niveles, sede=sede, modalidad=modalidad, cortes=corte).exists():
                prec_periodo = self.preciosperiodo_set.filter(periodo=periodo, nivel=niveles, sede=sede, modalidad=modalidad, cortes=corte)[0]
                if prec_periodo.preciomatricula:
                    preciocompleto = prec_periodo.precioarancel
                else:
                    preciocompleto += prec_periodo.precioarancel
        if prec_periodo.descuentoformapago_set.filter(fechainicio__lte=fecha, fechafin__gte=fecha).exists():
            esprontopago = True
        else:
            esprontopago = False
        return [preciocompleto, esprontopago]

    def precio_modulo_inscripcion(self, periodo, sede, modalidad, malla, corte=None):
        if self.tipogrado.id == CUARTO_NIVEL_TITULACION_ID:
            if self.preciosperiodomodulosinscripcion_set.filter(periodo=periodo, sede=sede, modalidad=modalidad, malla=malla, malla__activo=True, cortes=corte).exists():
                prec_periodo = self.preciosperiodomodulosinscripcion_set.filter(periodo=periodo, sede=sede, modalidad=modalidad,malla=malla, malla__activo=True, cortes=corte)[0]
            else:
                prec_periodo = PreciosPeriodoModulosInscripcion(periodo=periodo,
                                                                carrera=self,
                                                                modalidad=modalidad,
                                                                sede=sede,
                                                                cortes=corte,
                                                                precioinscripcion=0,
                                                                precioinduccion=0,
                                                                porcentajesegundamatricula=0,
                                                                porcentajeterceramatricula=0,
                                                                porcentajematriculaextraordinaria=0,
                                                                preciomodulo=0,
                                                                precioadelantoidiomas=0,
                                                                malla=malla)
                prec_periodo.save()
        else:
            if self.preciosperiodomodulosinscripcion_set.filter(periodo=periodo, sede=sede, modalidad=modalidad,malla=malla, malla__activo=True).exists():
                prec_periodo = self.preciosperiodomodulosinscripcion_set.filter(periodo=periodo, sede=sede, modalidad=modalidad,malla=malla, malla__activo=True)[0]
            else:
                prec_periodo = PreciosPeriodoModulosInscripcion(periodo=periodo,
                                                                carrera=self,
                                                                modalidad=modalidad,
                                                                sede=sede,
                                                                precioinscripcion=0,
                                                                precioinduccion=0,
                                                                porcentajesegundamatricula=0,
                                                                porcentajeterceramatricula=0,
                                                                porcentajematriculaextraordinaria=0,
                                                                preciomodulo=0,
                                                                precioadelantoidiomas=0,
                                                                malla=malla)
                prec_periodo.save()
        return prec_periodo

    def precio_modulo_inscripcion_carrera(self, periodo, sede, modalidad, carrera, malla, corte=None):
        prec_periodo_c = None
        if self.preciosperiodomodulosinscripcion_set.filter(periodo=periodo, sede=sede, modalidad=modalidad, carrera=carrera, malla=malla).exists():
            prec_periodo_c = self.preciosperiodomodulosinscripcion_set.filter(periodo=periodo, sede=sede, modalidad=modalidad, malla=malla)[0]
        return prec_periodo_c

    def total_periodo(self, nivel, periodo, sede, modalidad, corte=None):
        if self.tipogrado.id == CUARTO_NIVEL_TITULACION_ID:
            valor = self.precio_periodo(nivel, periodo, sede, modalidad, corte=corte)
        else:
            valor = self.precio_periodo(nivel, periodo, sede, modalidad)
        return null_to_numeric(valor.precioarancel + valor.preciomatricula + valor.precioderechorotativo, 2)

    def total_periodo_descuento(self, nivel, periodo, sede, modalidad, formapago, corte=None):
        porcentaje = 0
        preciodescuento = 0
        if self.tipogrado.id == CUARTO_NIVEL_TITULACION_ID:
            valor = self.precio_periodo(nivel, periodo, sede, modalidad, corte=corte)
            if DescuentoFormaPago.objects.filter(precioperiodo=valor, formadepago=formapago).exists():
                descuento = DescuentoFormaPago.objects.filter(precioperiodo=valor, formadepago=formapago)[0]
                porcentaje = descuento.descuento
                preciodescuento = (valor.precioarancel * porcentaje) / 100
        else:
            valor = self.precio_periodo(nivel, periodo, sede, modalidad)
            if DescuentoFormaPago.objects.filter(precioperiodo=valor, formadepago=formapago).exists():
                descuento = DescuentoFormaPago.objects.filter(precioperiodo=valor, formadepago=formapago)[0]
                porcentaje = descuento.descuento
                preciodescuento = (valor.precioarancel * porcentaje) / 100
        return null_to_numeric(valor.preciomatricula + (valor.precioarancel - preciodescuento), 2)

    def total_descuento_formapago(self, nivel, periodo, sede, modalidad, formapago, corte=None):
        porcentaje = 0
        preciodescuento = 0
        if self.tipogrado.id == CUARTO_NIVEL_TITULACION_ID:
            valor = self.precio_periodo(nivel, periodo, sede, modalidad, corte=corte)
            if DescuentoFormaPago.objects.filter(precioperiodo=valor, formadepago=formapago).exists():
                descuento = DescuentoFormaPago.objects.filter(precioperiodo=valor, formadepago=formapago)[0]
                porcentaje = descuento.descuento
                preciodescuento = (valor.precioarancel * porcentaje) / 100
        else:
            valor = self.precio_periodo(nivel, periodo, sede, modalidad)
            if DescuentoFormaPago.objects.filter(precioperiodo=valor, formadepago=formapago).exists():
                descuento = DescuentoFormaPago.objects.filter(precioperiodo=valor, formadepago=formapago)[0]
                porcentaje = descuento.descuento
                preciodescuento = (valor.precioarancel * porcentaje) / 100
        return null_to_numeric(preciodescuento, 2)

    def niveles_maximos_modalidad(self, modalidad):
        maximo = null_to_numeric(self.malla_set.filter(modalidad=modalidad).aggregate(valor=Max('nivelesregulares'))['valor'], 0)
        return NivelMalla.objects.filter(id__lte=maximo)

    def mis_modalidades_nivel(self, nivel):
        return Modalidad.objects.filter(malla__carrera=self, malla__carrera__malla__asignaturamalla__materia__nivel=nivel).distinct()

    def cantidad_matriculados_primernivel_sede(self, periodo, sede):
        return Matricula.objects.filter(inscripcion__carrera=self, nivel__periodo=periodo, nivelmalla__id=NIVEL_MALLA_UNO, inscripcion__sede=sede).distinct().count()

    def cantidad_retirados_primernivel_sede(self, periodo, sede):
        return Matricula.objects.filter(inscripcion__carrera=self, nivel__periodo=periodo, nivelmalla__id=NIVEL_MALLA_UNO, retiromatricula__isnull=False, inscripcion__sede=sede).distinct().count()

    def cantidad_matriculados_primernivel(self, periodo):
        return Matricula.objects.filter(inscripcion__carrera=self, nivel__periodo=periodo, nivelmalla__id=NIVEL_MALLA_UNO).distinct().count()

    def cantidad_matriculados_primernivel_nuevos(self, periodo):
        return Matricula.objects.filter(inscripcion__carrera=self, nivel__periodo=periodo, nivelmalla__id=NIVEL_MALLA_UNO).exclude(materiaasignada__matriculas__gte=2).distinct().count()

    def cantidad_matriculados_primernivel_repetidores(self, periodo):
        return Matricula.objects.filter(inscripcion__carrera=self, nivel__periodo=periodo, nivelmalla__id=NIVEL_MALLA_UNO, materiaasignada__matriculas__gte=2).distinct().count()

    def cantidad_retirados_primernivel(self, periodo):
        return Matricula.objects.filter(inscripcion__carrera=self, nivel__periodo=periodo, nivelmalla__id=NIVEL_MALLA_UNO, retiromatricula__isnull=False).distinct().count()

    def total_general_graduados(self, inicio, fin):
        return Graduado.objects.filter(inscripcion__carrera=self, fecharefrendacion__gte=inicio, fecharefrendacion__lte=fin).exclude(inscripciones__carrera__tipogrado__id=CUARTO_NIVEL_TITULACION_ID).distinct().count()

    def total_general_graduados_pos(self, inicio, fin):
        return Graduado.objects.filter(inscripcion__carrera=self, fecharefrendacion__gte=inicio, fecharefrendacion__lte=fin, inscripciones__carrera__tipogrado__id=CUARTO_NIVEL_TITULACION_ID).distinct().count()

    def profesores_periodo_pos(self, periodo):
        return Profesor.objects.filter(profesormateria__materia__nivel__periodo=periodo, profesormateria__materia__nivel__nivellibrecoordinacion__coordinacion__carrera=self).distinct()

    def cantidad_estudiantes_provincias(self, periodo, modalidad, provincia, sede):
        return Inscripcion.objects.filter(carrera=self, matricula__nivel__periodo=periodo, modalidad=modalidad, persona__provincia=provincia, sede=sede).distinct().count()

    def cantidad_tutorias_carrera(self, sede, tutor, inicio, fin):
        return Tutoria.objects.filter(actaavance__asistenciaactaavance__inscripcion__carrera=self, tutor__profesor__coordinacion__sede=sede, tutor__profesor=tutor, fecha__gte=inicio, fecha__lte=fin).count()

    def cantidad_mallas(self):
        return self.malla_set.count()

    def permite_modificar(self):
        return not self.en_uso()

    def puede_eliminarse(self):
        if self.inscripcion_set.exists():
            return False
        if Materia.objects.filter(carrera=self).exists():
            return False
        return True

    def cartera_general_posgrado(self):
        hoy = datetime.now().date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy, pasivo=False, inscripcion__carrera__posgrado=True).aggregate(valor=Sum('saldo'))['valor'], 2)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.mencion = null_to_text(self.mencion)
        self.alias = null_to_text(self.alias)
        self.nombreingles = null_to_text(self.nombreingles)
        super(Carrera, self).save(*args, **kwargs)


class CompetenciaEspecifica(ModeloBase):
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE)
    nombre = models.TextField(default='', verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Competencia especifica"
        ordering = ['nombre']

    def puede_eliminarse(self):
        if self.malla_set.exists():
            return False
        if self.planificacionmateria_set.exists():
            return False
        return True

    def malla_usando(self):
        return self.malla_set.exists()

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(CompetenciaEspecifica, self).save(*args, **kwargs)


class CompetenciaGenerica(ModeloBase):
    nombre = models.TextField(default='', verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Competencia generica"
        ordering = ['nombre']

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(CompetenciaGenerica, self).save(*args, **kwargs)


class TipoParroquia(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipo Parroquia"
        ordering = ['nombre']

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoParroquia, self).save(*args, **kwargs)


class Parroquia(ModeloBase):
    canton = models.ForeignKey(Canton, blank=True, null=True, verbose_name=u"Canton", on_delete=models.CASCADE)
    tipo = models.ForeignKey(TipoParroquia, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Parroquias"
        ordering = ['nombre']

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(Parroquia, self).save(*args, **kwargs)


class Sexo(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    codigosniese = models.CharField(max_length=15, default='', verbose_name=u'Codigo Sniese')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Sexos"
        unique_together = ('nombre',)

    def cantidad_matriculados(self):
        return Matricula.objects.filter(nivel__cerrado=False, nivel__periodo__activo=True, inscripcion__persona__sexo=self).count()

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(Sexo, self).save(*args, **kwargs)


class Genero(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Generos"
        unique_together = ('nombre',)

    def cantidad_matriculados(self):
        return Matricula.objects.filter(nivel__cerrado=False, nivel__periodo__activo=True, inscripcion__persona__genero=self).count()
        pass

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(Genero, self).save(*args, **kwargs)


class PersonaEstadoCivil(ModeloBase):
    nombre = models.CharField(max_length=50, verbose_name=u"Nombre")
    codigosniese = models.CharField(max_length=15, default='', verbose_name=u'Codigo Sniese')

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = u"Estados civiles"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigosniese = null_to_text(self.codigosniese)
        super(PersonaEstadoCivil, self).save(*args, **kwargs)




class TipoSangre(ModeloBase):
    sangre = models.CharField(default='', max_length=4, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.sangre

    class Meta:
        verbose_name_plural = u"Tipos de sangre"
        unique_together = ('sangre',)

    def save(self, *args, **kwargs):
        self.sangre = null_to_text(self.sangre)
        super(TipoSangre, self).save(*args, **kwargs)


TIPO_EMISION_COMPROBANTE = ((1, u'NORMAL'), (2, u'POR INDISPONIBILIDAD'))

TIPO_AMBIENTE_FACTURACION = ((1, u'PRUEBAS'), (2, u'PRODUCCIÓN'))


class Persona(ModeloBase):
    nombre1 = models.CharField(default='', max_length=50, verbose_name=u'1er Nombre')
    nombre2 = models.CharField(default='', max_length=50, verbose_name=u'2do Nombre')
    apellido1 = models.CharField(default='', max_length=50, verbose_name=u"1er Apellido")
    apellido2 = models.CharField(default='', max_length=50, verbose_name=u"2do Apellido")
    cedula = models.CharField(default='', max_length=13, verbose_name=u"Cedula")
    pasaporte = models.CharField(default='', max_length=15, verbose_name=u"Pasaporte")
    nacimiento = models.DateField(verbose_name=u"Fecha de nacimiento",blank=True, null=True)
    sexo = models.ForeignKey(Sexo, verbose_name=u'Sexo', on_delete=models.CASCADE)
    genero = models.ForeignKey(Genero, blank=True, null=True, verbose_name=u'Genero', on_delete=models.CASCADE)
    otrogenero = models.CharField(default='', max_length=200, verbose_name=u"Otro Genero")
    paisnac = models.ForeignKey(Pais, blank=True, null=True, related_name='+', verbose_name=u'País nacimiento', on_delete=models.CASCADE)
    provincianac = models.ForeignKey(Provincia, blank=True, null=True, related_name='provincianac', verbose_name=u"Provincia de nacimiento", on_delete=models.CASCADE)
    cantonnac = models.ForeignKey(Canton, blank=True, null=True, related_name='cantonnac', verbose_name=u"Cantón de nacimiento", on_delete=models.CASCADE)
    parroquianac = models.ForeignKey(Parroquia, blank=True, related_name='parroquianac', null=True, verbose_name=u"Parroquia de nacimiento", on_delete=models.CASCADE)
    nacionalidad = models.ForeignKey(Nacionalidad, blank=True, null=True, verbose_name=u"Nacionalidad", on_delete=models.CASCADE)
    pais = models.ForeignKey(Pais, blank=True, null=True, related_name='pais', verbose_name=u'País residencia', on_delete=models.CASCADE)
    provincia = models.ForeignKey(Provincia, blank=True, null=True, related_name='provincia', verbose_name=u"Provincia de residencia", on_delete=models.CASCADE)
    canton = models.ForeignKey(Canton, blank=True, null=True, related_name='canton', verbose_name=u"Cantón de residencia", on_delete=models.CASCADE)
    parroquia = models.ForeignKey(Parroquia, blank=True, related_name='parroquia', null=True, verbose_name=u"Parroquia de residencia", on_delete=models.CASCADE)
    sector = models.CharField(default='', max_length=100, verbose_name=u"Sector de residencia")
    ciudad = models.CharField(default='', max_length=50, verbose_name=u"Ciudad de residencia")
    direccion = models.CharField(default='', max_length=100, verbose_name=u"Calle principal")
    direccion2 = models.CharField(default='', max_length=100, verbose_name=u"Calle secundaria")
    referencia = models.CharField(default='', max_length=100, verbose_name=u"Referencia")
    num_direccion = models.CharField(default='', max_length=15, verbose_name=u"Numero de domicilio")
    telefono = models.CharField(default='', max_length=50, verbose_name=u"Teléfono movil")
    telefono_conv = models.CharField(default='', max_length=50, verbose_name=u"Teléfono fijo")
    email = models.CharField(default='', max_length=200, verbose_name=u"Correo electrónico personal")
    twitter = models.CharField(default='', max_length=200, verbose_name=u"Twitter")
    blog = models.CharField(default='', max_length=200, verbose_name=u"Blog")
    emailinst = models.CharField(default='', max_length=200, verbose_name=u"Correo electrónico institucional")
    sangre = models.ForeignKey(TipoSangre, blank=True, null=True, verbose_name=u"Tipo de Sangre", on_delete=models.CASCADE)
    estadocivil = models.ForeignKey(PersonaEstadoCivil, blank=True, null=True, verbose_name=u"Estado civil", on_delete=models.CASCADE)
    libretamilitar = models.CharField(default='', max_length=30, verbose_name=u"Libreta Militar")
    redmaestros = models.BooleanField(default=False, verbose_name=u"Red de maestros")
    actualizodatosfactura = models.BooleanField(default=False, verbose_name=u"Actualizó datos factura")
    deudahistorica = models.BooleanField(default=False, verbose_name=u"Deudas historica")
    usuario = models.ForeignKey(User, null=True, verbose_name=u'Usuario', on_delete=models.CASCADE)
    iddigitalizada = models.FileField(upload_to='iddigitalizada/%Y/%m/%d', blank=True, null=True, verbose_name=u'Documento digitalizado')
    codigocontable = models.IntegerField(default=0, verbose_name=u'Codigo contable.')
    registrocontable = models.BooleanField(default=False, verbose_name=u'Registro en contable.')

    def __str__(self):
        return u'%s %s %s %s' % (self.apellido1, self.apellido2, self.nombre1, self.nombre2)

    class Meta:
        verbose_name_plural = u"Personas"
        # unique_together = ('emailinst',)
        ordering = ['apellido1', 'apellido2', 'nombre1', 'nombre2']

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        if len(q.split(' ')) == 2:
            qq = q.split(' ')
            return eval(("Persona.objects.filter(apellido1__contains='%s', apellido2__contains='%s')" % (qq[0], qq[1])) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))
        return eval(("Persona.objects.filter(Q(nombre1__contains='%s') | Q(nombre2__contains='%s') | Q(apellido1__contains='%s') | Q(apellido2__contains='%s') | Q(cedula__contains='%s') | Q(id=id_search('%s')))" % (q, q, q, q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def esta_gestacion(self):
        return ESTADO_GESTACION_CHOICES[self.gestacion - 1][1]

    def esta_fuma(self):
        return LISTADO_FUMA[self.frecuenciafuma - 1][1]

    def consume_alcohol(self):
        return LISTADO_ALCOHOL[self.frecuenciaalcohol - 1][1]

    def consume_drogas(self):
        return LISTADO_DROGAS[self.frecuenciadroga - 1][1]

    def flexbox_repr(self):
        return self.cedula + " - " + self.nombre_completo_inverso() + ' - ' + str(self.id)

    def flexbox_alias(self):
        return [self.id, self.nombre_completo()]

    def tiene_perfilusuario(self):
        return self.perfilusuario_set.exists()

    def es_mujer(self):
        return self.sexo.id == SEXO_FEMENINO

    def es_hombre(self):
        return self.sexo.id == SEXO_MASCULINO

    def tiene_conocimientos(self):
        if self.conocimientoinformatico_set.exists():
            return self.conocimientoinformatico_set.all()
        return None

    def tiene_experiencia(self):
        if self.trabajopersona_set.exists():
            return self.trabajopersona_set.all().order_by('-fecha')
        return None

    def tiene_estudios(self):
        if self.estudiopersona_set.exists():
            return self.estudiopersona_set.all()
        return None

    def ultimo_estudio(self):
        if self.estudiopersona_set.exists():
            return self.estudiopersona_set.all().order_by('-id')[0]
        return None

    def ultimo_estudiopostgraduado(self):
        if self.estudiopersona_set.filter(estudiosposteriores=True).exists():
            return self.estudiopersona_set.filter(estudiosposteriores=True).order_by('-id')[0]
        return None

    def ultimo_trabajo(self):
        if self.trabajopersona_set.exists():
            return self.trabajopersona_set.order_by('-fecha')[0]
        return None

    def hojavida_llena(self):
        if self.tiene_idiomadomina() and self.tiene_referencias():
            return True
        return False

    def tiene_perfil(self):
        return self.perfilusuario_set.exists()

    def perfil_activo(self):
        perfil = self.perfilusuario_set.filter(principal=True).last()
        if not perfil:
            perfil = self.perfilusuario_set.all().last()
            perfil.principal = True
            perfil.save()
        return perfil

    def perfil_estudiante_activo(self):
        perfil = self.perfilusuario_set.filter(inscripcion__isnull=False, principal=True).last()
        if not perfil:
            perfil = self.perfilusuario_set.filter(inscripcion__isnull=False).last()
            perfil.principal = True
            perfil.save()
        return perfil

    def carrera_activa(self):
        carreraactiva = self.perfilusuario_set.filter(inscripcion__isnull=False, principal=True).last().inscripcion.carrera.nombre
        if not carreraactiva:
            perfil = self.perfilusuario_set.filter(inscripcion__isnull=False).last()
            perfil.principal = True
            perfil.save()
            carreraactiva = perfil.insccripcion.carrera.nombre
        return carreraactiva

    def mis_perfiles_estudiante(self):
        return self.perfilusuario_set.filter(inscripcion__isnull=False)

    def es_bibliotecario(self):
        return self.responsablebiblioteca_set.exists()

    def mis_bibliotecas(self):
        from bib.models import Biblioteca
        return Biblioteca.objects.filter(responsablebiblioteca__persona=self).distinct()

    def tiene_perfil_inscripcion(self):
        return self.perfilinscripcion_set.exists()

    def tiene_perfil_docente(self):
        return self.perfildocente_set.exists()

    def tiene_phd(self):
        if self.estudiopersona_set.filter(aliastitulo='PHD.').exists():
            return True
        return False

    def crear_perfil(self, administrativo=None, inscripcion=None, profesor=None, empleador=None,cliente=None):
        if inscripcion:
            perfil = PerfilUsuario(persona=self,
                                   inscripcion=inscripcion,
                                   tipoperfilusuario_id=PERFIL_ESTUDIANTE_ID)
            perfil.save()
        elif administrativo:
            perfil = PerfilUsuario(persona=self,
                                   administrativo=administrativo,
                                   tipoperfilusuario_id=PERFIL_ADMINISTRATIVO_ID)
            perfil.save()
        elif profesor:
            perfil = PerfilUsuario(persona=self,
                                   profesor=profesor,
                                   tipoperfilusuario_id=PERFIL_PROFESOR_ID)
            perfil.save()
        elif empleador:
            perfil = PerfilUsuario(persona=self,
                                   empleador=empleador,
                                   tipoperfilusuario_id=PERFIL_EMPLEADOR_ID)
            perfil.save()
        elif cliente:
            perfil = PerfilUsuario(persona=self,
                                   cliente=cliente,
                                   tipoperfilusuario_id=PERFIL_CLIENTE_ID)
            perfil.save()

    def lista_perfiles(self):
        return TipoPerfilUsuario.objects.filter(perfilusuario__persona=self).distinct()

    def mi_perfil(self):
        if self.tiene_perfil_inscripcion():
            return self.perfilinscripcion_set.all()[0]
        else:
            perfil = PerfilInscripcion(persona=self,
                                       tienediscapacidad=False,
                                       raza_id=RAZA_ID)
            perfil.save()
            return perfil

    def mi_perfil_docente(self):
        if self.tiene_perfil_docente():
            return self.perfildocente_set.all()[0]
        else:
            perfil = PerfilDocente(persona=self,
                                   tienediscapacidad=False,
                                   raza_id=RAZA_ID)
            perfil.save()
            return perfil

    def tiene_multiples_perfiles(self):
        return self.perfilusuario_set.count() > 1

    def mis_perfilesusuarios(self):
        return self.perfilusuario_set.all()

    def mis_perfilesusuarios_basicos(self):
        return self.perfilusuario_set.filter(Q(empleador__isnull=False) | Q(administrativo__isnull=False) | Q(profesor__isnull=False) | Q(principal__isnull=False)).distinct()

    def perfilusuario_principal(self):
        if self.perfilusuario_set.filter(profesor__isnull=False, profesor__activo=True).exists():
            return self.perfilusuario_set.filter(profesor__isnull=False, profesor__activo=True)[0]
        elif self.perfilusuario_set.filter(administrativo__isnull=False, administrativo__activo=True).exists():
            return self.perfilusuario_set.filter(administrativo__isnull=False, administrativo__activo=True)[0]
        elif self.perfilusuario_set.filter(inscripcion__isnull=False, inscripcion__activo=True).exists():
            return self.perfilusuario_set.filter(inscripcion__isnull=False, inscripcion__activo=True).order_by('-principal')[0]
        elif self.perfilusuario_set.filter(empleador__isnull=False, empleador__activo=True).exists():
            return self.perfilusuario_set.filter(empleador__isnull=False, empleador__activo=True)[0]
        elif self.perfilusuario_set.filter(cliente__isnull=False, cliente__activo=True).exists():
            return self.perfilusuario_set.filter(cliente__isnull=False, cliente__activo=True)[0]
        return None

    def tiene_ficha(self):
        from socioecon.models import FichaSocioeconomicaINEC
        return self.fichasocioeconomicainec_set.exists()

    def mi_ficha(self):
        from socioecon.models import FichaSocioeconomicaINEC
        if self.tiene_ficha():
            ficha = self.fichasocioeconomicainec_set.all()[0]
        else:
            ficha = FichaSocioeconomicaINEC(persona=self)
            ficha.save()
        return ficha

    def tiene_mensajes(self):
        return self.mensajedestinatario_set.filter(leido=False).exists()

    def tiene_foto(self):
        return self.fotopersona_set.exists()

    def es_empleador(self):
        return self.empleador_set.exists()

    def es_administrador(self):
        return self.usuario.is_superuser

    def es_estudiante(self):
        return self.perfilusuario_set.filter(inscripcion__isnull=False).exists()

    def es_cliente(self):
        return self.perfilusuario_set.filter(cliente__isnull=False).exists()

    def es_estudiante_matriculado(self):
        return self.perfilusuario_set.filter(inscripcion__isnull=False, inscripcion__matricula__cerrada=False).exclude(inscripcion__coordinacion__id__in=(22, 23)).exists()

    def es_egresado(self):
        if self.es_estudiante_matriculado():
            return False
        else:
            return self.perfilusuario_set.filter(inscripcion__egresado__isnull=False).exists()

    def es_graduado(self):
        return self.perfilusuario_set.filter(inscripcion__graduado__isnull=False).exists()

    def es_administrativo(self):
        return self.perfilusuario_set.filter(administrativo__isnull=False).exists()

    def es_profesor(self):
        return self.perfilusuario_set.filter(profesor__isnull=False).exists()

    def es_cliente(self):
        return self.perfilusuario_set.filter(cliente__isnull=False).exists()

    def mis_inscripciones(self):
        return self.perfilusuario_set.filter(inscripcion__isnull=False)

    def necesita_cambiar_clave(self):
        return self.cambioclavepersona_set.filter(solicitada=False).exists()

    def clave_cambiada(self):
        if self.cambioclavepersona_set.exists():
            self.cambioclavepersona_set.all().delete()

    def cambiar_clave(self):
        if self.cambioclavepersona_set.exists():
            cc = self.cambioclavepersona_set.all()[0]
        else:
            cc = CambioClavePersona(persona=self)
            cc.save()
        return cc

    def datos_extension(self):
        if not self.personaextension_set.exists():
            from med.models import PersonaExamenFisico, PersonaFichaMedica, PersonaExtension, Odontograma
            pe = PersonaExtension(persona=self)
            pe.save()
            pfm = PersonaFichaMedica(personaextension=pe)
            pfm.save()
            od = Odontograma(fichamedica=pfm)
            od.save()
        return self.personaextension_set.all()[0]

    def mi_empresa(self):
        if self.empleador_set.all().exists():
            return self.empleador_set.all()[0].empresa
        return None

    def mis_bibliotecas_sede(self, perfil):
        from bib.models import Biblioteca
        if perfil.es_estudiante():
            return Biblioteca.objects.filter(sede=perfil.inscripcion.sede)
        elif perfil.es_administrativo():
            return Biblioteca.objects.filter(sede=perfil.administrativo.sede)
        elif perfil.es_profesor():
            return Biblioteca.objects.filter(sede=perfil.profesor.coordinacion.sede)
        return []


    def documentos_reservados(self):
        return self.reservadocumento_set.filter(entregado=False, anulado=False, limitereserva__gte=datetime.now())

    def direccion_completa(self):
        return u"%s %s %s %s %s %s %s" % ((self.provincia.nombre + ",") if self.provincia else "",
                                          (self.ciudad + ",") if self.ciudad else "",
                                          (self.parroquia.nombre + ",") if self.parroquia else "",
                                          (self.sector + ",") if self.sector else "",
                                          (self.direccion + ",") if self.direccion else "",
                                          (self.direccion2 + ",") if self.direccion2 else "",
                                          self.num_direccion)

    def lista_sedes(self, coordinaciones):
        return Sede.objects.filter(coordinacion__in=coordinaciones).distinct()

    def identificacion(self):
        if self.cedula:
            return self.cedula
        elif self.pasaporte:
            return self.pasaporte
        return None

    def tipo_identificacion(self):
        if self.cedula:
            return "CEDULA"
        elif self.pasaporte:
            return "PASAPORTE"
        else:
            return "RUC"

    def tipo_identificacion_comprobante(self):
        if self.cedula:
            return 1
        elif self.pasaporte:
            return 2
        else:
            return 3

    def mi_direccion(self):
        if self.direccion:
            return self.direccion
        elif self.direccion2:
            return self.direccion2
        return ''

    def mi_telefono(self):
        if self.telefono_conv:
            return self.telefono_conv
        elif self.telefono:
            return self.telefono
        return ''

    def mi_email(self):
        if self.email:
            return self.email
        elif self.emailinst:
            return self.emailinst
        return ''

    def lista_identificaciones(self):
        data = []
        if self.cedula:
            data.append(self.cedula)
        elif self.pasaporte:
            data.append(self.pasaporte)
        return data

    def telefonos(self):
        data = []
        if self.telefono_conv:
            data.append(self.telefono_conv)
        if self.telefono:
            data.append(self.telefono)
        return data

    def activo(self):
        return self.usuario.is_active

    def puede_recibir_pagos(self):
        cajas = self.mis_cajas()
        return SesionCaja.objects.filter(caja__in=cajas, abierta=True, fecha=datetime.now().date(), caja__automatico=False).exists()

    def mis_cajas(self):
        return self.lugarrecaudacion_set.filter(activo=True)

    def caja_abierta(self):
        cajas = self.mis_cajas()
        if SesionCaja.objects.filter(caja__in=cajas, abierta=True, caja__automatico=False).exists():
            return SesionCaja.objects.filter(caja__in=cajas, abierta=True, caja__automatico=False)[0]
        return None

    def caja_abierta_dia(self, fecha):
        return SesionCaja.objects.filter(caja__persona=self, abierta=True, fecha=fecha).exists()

    def datos_incompletos(self):
        if not self.nombre1 or not self.apellido1:
            return True
        if not self.cedula and not self.pasaporte:
            return True
        if not self.nacimiento or not self.sexo or not self.provincia or not self.pais:
            return True
        if not self.direccion or not self.email:
            return True
        perfil = self.mi_perfil()
        if not perfil.raza:
            return True
        return False

    def tiene_idiomadomina(self):
        if self.idiomadomina_set.exists():
            return self.idiomadomina_set.all()
        return None

    def tiene_conocimientosadicionales(self):
        if self.conocimientoadiconal_set.exists():
            return self.conocimientoadiconal_set.all()
        return None

    def tiene_referencias(self):
        if self.referenciapersona_set.exists():
            return self.referenciapersona_set.all()
        return None

    def datos_examen_fisico(self):
        return self.datos_extension().personaexamenfisico()

    def nombre_completo(self):
        return u'%s %s %s %s' % (self.nombre1, self.nombre2, self.apellido1, self.apellido2)

    def nombres(self):
        return u'%s %s' % (self.nombre1, self.nombre2)

    def apellidos(self):
        return u'%s %s' % (self.apellido1, self.apellido2)

    def nombre_apellido_principal(self):
        return u'%s %s' % (self.nombre1, self.apellido1)

    def nombre_completo_inverso(self):
        return u'%s %s %s %s' % (self.apellido1, self.apellido2, self.nombre1, self.nombre2)

    def nombre_completo_simple(self):
        return u'%s %s' % (self.nombre1, self.apellido1[0] if self.apellido1 else "")

    def nombres_completos(self):
        return u'%s %s' % (self.nombre1, self.nombre2 if self.nombre2 else "")

    def nombre_iniciales(self):
        return u"%s" % (self.nombre1[:3])

    def mi_cumpleannos(self):
        hoy = datetime.now().date()
        if not self.nacimiento:
            return False
        nacimiento = self.nacimiento
        if nacimiento.day == hoy.day and nacimiento.month == hoy.month:
            return True
        return False

    def edad(self):
        edad = 0
        hoy = datetime.now().date()
        nac = self.nacimiento
        if hoy.year > nac.year:
            try:
                edad = hoy.year - nac.year
                if hoy.month <= nac.month:
                    if hoy.month == nac.month:
                        if hoy.day < nac.day:
                            edad -= 1
                    else:
                        edad -= 1
            except:
                pass
        return edad

    def edad_completa(self):
        return relativedelta(date.today(), self.nacimiento)

    def foto(self):
        if self.fotopersona_set.exists():
            return self.fotopersona_set.all()[0]
        return None

    def borrar_foto(self):
        fotos = self.fotopersona_set.all()
        fotos.delete()

    def cv(self):
        if self.cvpersona_set.exists():
            return self.cvpersona_set.all()[0]
        return None

    def cedula_doc(self):
        if self.cedulapersona_set.exists():
            return self.cedulapersona_set.all()[0]
        return None

    def borrar_cv(self):
        cv = self.cvpersona_set.all()
        cv.delete()

    def borrar_cedula(self):
        cedula = self.cedulapersona_set.all()
        cedula.delete()

    def emails(self):
        if self.emailinst:
            return self.emailinst
        elif self.email:
            return self.email
        return None

    def lista_emails(self):
        lista = []
        if self.es_administrativo():
            lista.append(self.emailinst)
        else:
            lista.append(self.emailinst)
        return lista

    def lista_emails_correo(self):
        lista = []
        if ENVIO_SOLO_CORREO_INSTITUCIONAL:
            if self.es_empleador():
                lista.append(self.email)
            else:
                lista.append(self.emailinst)
            return lista
        else:
            return self.lista_emails()

    def inscripcion_principal(self):
        inscripcion = None
        if self.inscripcion_set.filter(matricula__cerrada=False).exists():
            inscripcion = self.inscripcion_set.filter(matricula__cerrada=False)[0]
        elif self.perfilusuario_set.filter(principal=True).exists():
            inscripcion = self.perfilusuario_set.filter(principal=True)[0].inscripcion
        elif self.inscripcion_set.exists():
            inscripcion = self.inscripcion_set.all()[0]
        return inscripcion

    def mis_perfilesinscripciones(self):
        return self.perfilusuario_set.filter(inscripcion__isnull=False)

    def profesor(self):
        if self.profesor_set.exists():
            return self.profesor_set.all()[0]
        return None

    def administrativo(self):
        if self.administrativo_set.exists():
            return self.administrativo_set.all()[0]
        return None

    def en_grupo(self, grupo):
        return self.usuario.groups.filter(id=grupo).exists()

    def en_grupos(self, lista):
        return self.usuario.groups.filter(id__in=lista).exists()

    def grupos(self):
        return self.usuario.groups.all().distinct()

    def incidencias_pendientes(self):
        return Incidencia.objects.filter(tipo__responsable=self, cerrada=False).count()

    def es_responsablecoordinacion(self):
        return self.responsablecoordinacion_set.exists()

    def mi_coordinacion(self):
        if self.es_responsablecoordinacion():
            return Coordinacion.objects.filter(responsablecoordinacion__persona=self)[0]
        elif self.es_coordinadorcarrera():
            return self.coordinadorcarrera_set.all()[0].coordinacion
        return None

    def lista_coordinaciones(self):
        lista = []
        listaresponsable = []
        if self.es_administrativo():
            administrativo = self.administrativo()
            lista = Coordinacion.objects.filter(sede=administrativo.sede).values_list('id', flat=True)
        if self.cargoinstitucion_set.exists():
            cargopersona = self.cargoinstitucion_set.all()[0]
            if cargopersona.sede:
                lista = Coordinacion.objects.filter(sede=cargopersona.sede).values_list('id', flat=True)
            else:
                lista = Coordinacion.objects.all().values_list('id', flat=True)
        else:
            if self.es_responsablecoordinacion():
                for coordinacion in Coordinacion.objects.filter(responsablecoordinacion__persona=self):
                    if coordinacion.id not in listaresponsable:
                        listaresponsable.append(coordinacion.id)
            if self.es_coordinadorcarrera():
                for coordinacion in Coordinacion.objects.filter(coordinadorcarrera__persona=self).distinct():
                    if coordinacion.id not in listaresponsable:
                        listaresponsable.append(coordinacion.id)
            if Coordinacion.objects.filter(perfilaccesousuario__persona=self).exists():
                for coordinacion in Coordinacion.objects.filter(perfilaccesousuario__persona=self).distinct():
                    if coordinacion.id not in listaresponsable:
                        listaresponsable.append(coordinacion.id)
            if self.es_secretaria():
                for coordinacion in Coordinacion.objects.filter(secretariacoordinacion__persona=self).distinct():
                    if coordinacion.id not in listaresponsable:
                        listaresponsable.append(coordinacion.id)

        return Coordinacion.objects.filter(id__in=lista if not listaresponsable else listaresponsable, estado=True).order_by('sede_id')

    def es_coordinadorcarrera(self):
        return self.coordinadorcarrera_set.exists()

    def es_personalcarrera(self):
        return self.perfilaccesousuario_set.exists()

    def es_secretaria(self):
        return SecretariaCoordinacion.objects.filter(persona=self).exists()

    def mis_coordinadorcarreras(self):
        return self.coordinadorcarrera_set.all()

    def mis_niveles(self, coordinacion, periodo):
        return Nivel.objects.filter(nivellibrecoordinacion__coordinacion=coordinacion, periodo=periodo).order_by('inicio').distinct()

    def mis_niveles_modalidad(self, coordinacion, periodo):
        modalidades = self.mis_modalidades(coordinacion)
        return Nivel.objects.filter(nivellibrecoordinacion__coordinacion=coordinacion, periodo=periodo, modalidad__in=modalidades).order_by('inicio').distinct()

    def bloqueados(self, coordinacion, periodo):
        return Matricula.objects.filter(inscripcion__coordinacion=coordinacion, inscripcion__periodo=periodo).distinct()

    def lista_carreras_coordinacion(self, coordinacion):
        lista = []
        if self.cargoinstitucion_set.exists():
            return coordinacion.carrera.all()
        if self.responsablecoordinacion_set.filter(coordinacion=coordinacion).exists():
            return coordinacion.carrera.all()
        if self.secretariacoordinacion_set.filter(coordinacion=coordinacion).exists():
            return coordinacion.carrera.all()
        if self.coordinadorcarrera_set.filter(coordinacion=coordinacion).exists():
            for carrera in Carrera.objects.filter(id__in=[x.carrera.id for x in self.coordinadorcarrera_set.filter(coordinacion=coordinacion)]):
                if carrera not in lista:
                    lista.append(carrera.id)
        if self.perfilaccesousuario_set.filter(coordinacion=coordinacion).exists():
            for carrera in Carrera.objects.filter(id__in=[x.carrera.id for x in self.perfilaccesousuario_set.filter(coordinacion=coordinacion)]):
                if carrera not in lista:
                    lista.append(carrera.id)
        return Carrera.objects.filter(id__in=lista)

    def ultima_consulta_psicologica(self):
        if self.pacientesconsultapsicologica_set.exists():
            return self.pacientesconsultapsicologica_set.all().order_by('-consulta__fecha', '-consulta__id')[0]
        return None

    def lugar_recaudacion(self):
        return self.lugarrecaudacion_set.filter(activo=True)

    def cantidad_consultasmedicas(self):
        return self.personaconsultamedica_set.count()

    def cantidad_consultasodontologicas(self):
        return self.personaconsultaodontologica_set.count()

    def tieneconusltaodontologicapendiente(self):
        return self.personaconsultaodontologica_set.filter(estado=False).exists()

    def cantidad_consultapsicologicas(self):
        return self.pacientesconsultapsicologica_set.count()

    def odontograma(self):
        return self.datos_extension().personafichamedica().odontograma()

    def actualiza_situacion_laboral(self):
        fichasocioeconomica = self.mi_ficha()
        if self.trabajopersona_set.filter(fechafin__isnull=True).exists():
            if fichasocioeconomica.situacionlaboral in [2, 3, 4, 5]:
                fichasocioeconomica.situacionlaboral = 1
        fichasocioeconomica.save()

    def datos_snna(self):
        if self.datossnna_set.exists():
            return self.datossnna_set.all()[0]
        else:
            datos = DatosSNNA(persona=self)
            datos.save()
            return datos

    def tiene_permiso(self, permiso):
        return self.usuario.has_perm(permiso)

    def matriculado(self):
        return Matricula.objects.filter(cerrada=False, inscripcion__persona=self).exists()

    def matriculado_periodo(self, periodo):
        return Matricula.objects.filter(cerrada=False, inscripcion__persona=self, nivel__periodo=periodo).exists()

    def titulacionmaxima(self):
        if self.estudiopersona_set.filter(verificado=True).exists():
            return self.estudiopersona_set.filter(verificado=True).order_by('-niveltitulacion__id')[0]
        return None

    def tiene_seguimiento(self):
        return SeguimientoPreInscrito.objects.filter(preinscrito=self).exists()

    def ultimo_seguimiento(self):
        if self.tiene_seguimiento():
            return SeguimientoPreInscrito.objects.filter(preinscrito=self)[0]
        return None

    def tiene_contrato_institucion_activo(self):
        return self.trabajopersona_set.filter(institucionactual=True, activo=True).exists()

    def tiene_discapacidad(self):
        return self.mi_perfil().tienediscapacidad

    def es_abanderado(self):
        return self.estudiopersona_set.filter(abanderado=True, verificado=True).exists()

    def pertenece_colegio_uti(self):
        return self.estudiopersona_set.filter(institucioneducacionbasica__id=COLEGIO_UTI_ID, verificado=True).exists()

    def tiene_deuda_vencida(self):
        return Rubro.objects.filter(cancelado=False, fechavence__lt=datetime.now().date(), inscripcion__persona=self).exists()

    def puede_acceder_matricula(self, coordinacion):
        return coordinacion in self.lista_coordinaciones()

    def adeuda_a_la_fecha(self):
        return null_to_numeric(Rubro.objects.filter(cancelado=False, inscripcion__persona=self, fechavence__lt=datetime.now().date()).aggregate(valor=Sum('saldo'))['valor'], 2)

    def valor_deuda_vencida(self):
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=datetime.now().date(), inscripcion__persona=self).aggregate(valor=Sum('saldo'))['valor'], 2)

    def cantidad_elementos_asignados_evaluacion(self, proceso):
        return self.responsableevidenciaevaluacioninstitucional_set.filter(origeninformacionelementosevaluacioninstitucional__estandarevaluacioninstitucional__indicadorevaluacioninstitucional__subcriterioevaluacioninstitucional__criterioevaluacioninstitucional__evaluacioninstitucional=proceso).count()

    def cantidad_elementos_completados_evaluacion(self, proceso):
        return self.responsableevidenciaevaluacioninstitucional_set.filter(origeninformacionelementosevaluacioninstitucional__evidenciaevaluacioninstitucional__estado=2, origeninformacionelementosevaluacioninstitucional__estandarevaluacioninstitucional__indicadorevaluacioninstitucional__subcriterioevaluacioninstitucional__criterioevaluacioninstitucional__evaluacioninstitucional=proceso).distinct().count()

    def porciento_cumplimiento_evaluacion(self, proceso):
        return null_to_numeric((self.cantidad_elementos_completados_evaluacion(proceso) / self.cantidad_elementos_asignados_evaluacion(proceso)) * 100.0, 2)

    def cantidad_elementos_asignados_evaluacion_revisor(self, proceso):
        return self.revisorevidenciaevaluacioninstitucional_set.filter(origeninformacionelementosevaluacioninstitucional__estandarevaluacioninstitucional__indicadorevaluacioninstitucional__subcriterioevaluacioninstitucional__criterioevaluacioninstitucional__evaluacioninstitucional=proceso).count()

    def cantidad_elementos_completados_evaluacion_revisor(self, proceso):
        return self.revisorevidenciaevaluacioninstitucional_set.filter(origeninformacionelementosevaluacioninstitucional__evidenciaevaluacioninstitucional__estado=2, origeninformacionelementosevaluacioninstitucional__estandarevaluacioninstitucional__indicadorevaluacioninstitucional__subcriterioevaluacioninstitucional__criterioevaluacioninstitucional__evaluacioninstitucional=proceso).distinct().count()

    def porciento_cumplimiento_evaluacion_revisor(self, proceso):
        return null_to_numeric((self.cantidad_elementos_completados_evaluacion_revisor(proceso) / self.cantidad_elementos_asignados_evaluacion_revisor(proceso)) * 100.0, 2)

    def mis_modalidades(self, coordinacion):
        if self.cargoinstitucion_set.exists():
            return Modalidad.objects.all()
        if self.responsablecoordinacion_set.filter(coordinacion=coordinacion).exists():
            return Modalidad.objects.filter(malla__carrera__coordinacion=coordinacion).distinct()
        if self.secretariacoordinacion_set.filter(coordinacion=coordinacion).exists():
            return Modalidad.objects.filter(malla__carrera__coordinacion=coordinacion).distinct()
        if self.coordinadorcarrera_set.filter(coordinacion=coordinacion).exists():
            return Modalidad.objects.filter(id__in=[x.modalidad.id for x in self.coordinadorcarrera_set.filter(coordinacion=coordinacion)]).distinct()
        return []

    def mis_departamentos(self):
        return self.personadepartamento_set.all()

    def mis_subdepartamentos(self):
        return self.personasubdepartamento_set.all()

    def mis_cargos(self):
        return self.personacargo_set.all()

    def mis_designaciones(self):
        return self.personadesignacion_set.all()

    def mis_ubicaciones(self):
        return self.personaubicacion_set.all()

    def mis_impresiones(self):
        return self.personaimprimirprocesos_set.all()

    def mis_nivelesreporte(self):
        return self.personanivelreporte_set.all()

    def numero_ponencias(self, anio):
        return self.ponencias_set.filter(anio=anio).count()

    def cantidadinscritossinmatricula(self, periodo):
        return Inscripcion.objects.filter(personainscribio=self, periodo=periodo, matricula__isnull=True).count()

    def cantidadinscritos(self, periodo):
        return Inscripcion.objects.filter(personainscribio=self, periodo=periodo).count()

    def mis_datosbancarios(self):
        return self.informacionbancariapersona_set.first()

    def documentos_sin_entregar(self):
        cantidadsinentregar = 0
        return cantidadsinentregar


    def save(self, *args, **kwargs):
        self.nombre1 = null_to_text(self.nombre1)
        self.nombre2 = null_to_text(self.nombre2)
        self.apellido1 = null_to_text(self.apellido1)
        self.apellido2 = null_to_text(self.apellido2)
        self.cedula = null_to_text(self.cedula)
        self.pasaporte = null_to_text(self.pasaporte)
        self.sector = null_to_text(self.sector)
        self.direccion = null_to_text(self.direccion)
        self.direccion2 = null_to_text(self.direccion2)
        self.referencia = null_to_text(self.referencia)
        self.num_direccion = null_to_text(self.num_direccion)
        self.telefono = null_to_text(self.telefono)
        self.telefono_conv = null_to_text(self.telefono_conv)
        self.email = null_to_text(self.email, lower=True)
        self.twitter = null_to_text(self.twitter, lower=True)
        self.blog = null_to_text(self.blog, lower=True)
        self.emailinst = null_to_text(self.emailinst, lower=True)
        self.libretamilitar = null_to_text(self.libretamilitar, lower=True)
        super(Persona, self).save(*args, **kwargs)




class Sede(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    provincia = models.ForeignKey(Provincia, blank=True, null=True, verbose_name=u"Provincia", on_delete=models.CASCADE)
    canton = models.ForeignKey(Canton, blank=True, null=True, verbose_name=u"Cantón", on_delete=models.CASCADE)
    parroquia = models.ForeignKey(Parroquia, blank=True, null=True, verbose_name=u"Parroquia", on_delete=models.CASCADE)
    sector = models.CharField(default='', max_length=100, verbose_name=u"Sector")
    ciudad = models.CharField(default='', max_length=50, verbose_name=u"Ciudad")
    alias = models.CharField(default='', max_length=2, verbose_name=u"Alias")
    direccion = models.CharField(default='', max_length=100, verbose_name=u"Calle principal")
    telefono = models.CharField(default='', max_length=50, verbose_name=u"Teléfono fijo")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Sedes"
        ordering = ['nombre']
        unique_together = ('nombre',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Sede.objects.filter(Q(nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.nombre + ' - ' + str(self.id)

    def aulas(self):
        return self.aula_set.all()

    def coordinacion_formacion_continua(self):
        if self.coordinacion_set.filter(carrera__id=CARRERA_FORMACION_CONTINUA_ID).exists():
            return self.coordinacion_set.filter(carrera__id=CARRERA_FORMACION_CONTINUA_ID)[0]
        return None

    def mis_coordinaciones(self):
        return self.coordinacion_set.all()

    def tiene_biblioteca(self):
        return self.biblioteca_set.exists()

    def mi_bibliotecas(self):
        return self.biblioteca_set.all()

    def tiene_cargos(self):
        return self.cargoinstitucion_set.exists()

    def mis_cargos(self):
        return self.cargoinstitucion_set.all()

    def mis_bibliotecarios(self):
        from bib.models import ResponsableBiblioteca
        return ResponsableBiblioteca.objects.filter(biblioteca__in=self.mi_bibliotecas())

    def mis_secretarias(self):
        return SecretariaCoordinacion.objects.filter(coordinacion__sede=self).distinct()

    def tiene_puntoventa(self):
        return self.puntoventa_set.exists()

    def mis_puntoventa(self):
        return self.puntoventa_set.all()

    def mis_puntoventa_activos(self):
        return self.puntoventa_set.filter(activo=True)

    def profesores_periodo(self, periodo):
        return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__coordinacion__sede=self, profesordistributivohoras__detalledistributivo__isnull=False, profesordistributivohoras__periodo=periodo).distinct()

    def profesores_periodo_distribtivo(self, periodo):
        return ProfesorDistributivoHoras.objects.filter(horas__gt=0, coordinacion__sede=self, detalledistributivo__isnull=False, periodo=periodo).distinct()

    def profesores_periodo_coordinacion(self, periodo, coordinacion):
        return Profesor.objects.filter(Q(profesordistributivohoras__horasdocencia__gt=0) | Q(profesordistributivohoras__horasinvestigacion__gt=0) | Q(profesordistributivohoras__horasgestion__gt=0), activo=True, profesordistributivohoras__coordinacion__sede=self, profesordistributivohoras__detalledistributivo__isnull=False, profesordistributivohoras__periodo=periodo, profesordistributivohoras__coordinacion=coordinacion).distinct()

    def profesores_periodo_carrera(self, periodo, coordinacion, carreraid):
        return Profesor.objects.filter(Q(profesordistributivohoras__horasdocencia__gt=0) | Q(profesordistributivohoras__horasinvestigacion__gt=0) | Q(profesordistributivohoras__horasgestion__gt=0), activo=True, profesordistributivohoras__coordinacion__sede=self, profesordistributivohoras__detalledistributivo__isnull=False, profesordistributivohoras__periodo=periodo, profesordistributivohoras__coordinacion=coordinacion, profesordistributivohoras__carrera__id=carreraid).distinct()

    def cantidad_matriculados_primernivel(self, periodo):
        return Matricula.objects.filter(inscripcion__sede=self, nivel__periodo=periodo, nivelmalla__id=NIVEL_MALLA_UNO, ).distinct().count()

    def cantidad_retirados_primernivel(self, periodo):
        return Matricula.objects.filter(inscripcion__sede=self, nivel__periodo=periodo, nivelmalla__id=NIVEL_MALLA_UNO, retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados_periodo(self, periodo, carrera):
        return Matricula.objects.filter(inscripcion__sede=self, inscripcion__carrera=carrera, nivel__periodo=periodo).distinct().count()

    def cantidad_retirados_periodo(self, periodo, carrera):
        return Matricula.objects.filter(inscripcion__sede=self, inscripcion__carrera=carrera, nivel__periodo=periodo, retiromatricula__isnull=False).distinct().count()

    def cantidad_promovidos_periodo(self, periodo, carrera):
        return Matricula.objects.filter(inscripcion__sede=self, inscripcion__carrera=carrera, nivel__periodo=periodo, promovido=True).distinct().count()

    def cantidad_nopromovidos_periodo(self, periodo, carrera):
        return Matricula.objects.filter(inscripcion__sede=self, inscripcion__carrera=carrera, nivel__periodo=periodo, promovido=False).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_total_matriculados_periodo(self, periodo):
        return Matricula.objects.filter(inscripcion__sede=self, nivel__periodo=periodo).distinct().count()

    def cantidad_total_retirados_periodo(self, periodo):
        return Matricula.objects.filter(inscripcion__sede=self, nivel__periodo=periodo, retiromatricula__isnull=False).distinct().count()

    def cantidad_total_promovidos_periodo(self, periodo):
        return Matricula.objects.filter(inscripcion__sede=self, nivel__periodo=periodo, promovido=True).distinct().count()

    def cantidad_total_nopromovidos_periodo(self, periodo):
        return Matricula.objects.filter(inscripcion__sede=self, nivel__periodo=periodo, promovido=False).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_graduados_pos(self, modalidad, inicio, fin):
        return Graduado.objects.filter(inscripcion__sede=self, inscripcion__modalidad=modalidad, fecharefrendacion__gte=inicio, fecharefrendacion__lte=fin, inscripciones__carrera__tipogrado__id=CUARTO_NIVEL_TITULACION_ID).distinct().count()

    def cantidad_graduados(self, modalidad, inicio, fin):
        return Graduado.objects.filter(inscripcion__sede=self, inscripcion__modalidad=modalidad, fecharefrendacion__gte=inicio, fecharefrendacion__lte=fin).exclude(inscripciones__carrera__tipogrado__id=CUARTO_NIVEL_TITULACION_ID).distinct().count()

    def total_general_graduados(self, inicio, fin):
        return Graduado.objects.filter(inscripcion__sede=self, fecharefrendacion__gte=inicio, fecharefrendacion__lte=fin).exclude(inscripciones__carrera__tipogrado__id=CUARTO_NIVEL_TITULACION_ID).distinct().count()

    def total_general_graduados_pos(self, inicio, fin):
        return Graduado.objects.filter(inscripcion__sede=self, fecharefrendacion__gte=inicio, fecharefrendacion__lte=fin, inscripciones__carrera__tipogrado__id=CUARTO_NIVEL_TITULACION_ID).distinct().count()

    def total_profesores_periodo(self, periodo):
        return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__coordinacion__sede=self, profesordistributivohoras__periodo=periodo).count()

    def cantidad_profesores_tiempo_completo(self, periodo):
        return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__coordinacion__sede=self, profesordistributivohoras__periodo=periodo, dedicacion__id=TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID).count()

    def cantidad_profesores_tiempo_parcial(self, periodo):
        return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__coordinacion__sede=self, profesordistributivohoras__periodo=periodo, dedicacion__id=TIEMPO_DEDICACION_PARCIAL_ID).count()

    def cantidad_profesores_medio_tiempo(self, periodo):
        return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__coordinacion__sede=self, profesordistributivohoras__periodo=periodo, dedicacion__id=TIEMPO_DEDICACION_MEDIO_TIEMPO_ID).count()

    def cantidad_profesores_tecnico_docente(self, periodo):
        return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__coordinacion__sede=self, profesordistributivohoras__periodo=periodo, dedicacion__id=TIEMPO_DEDICACION_TECNICO_DOCENTE_ID).count()

    def porcentaje_profesores_tiempo_completo(self, periodo):
        return null_to_numeric((self.cantidad_profesores_tiempo_completo(periodo) / float(self.total_profesores_periodo(periodo)) * 100), 2)

    def porcentaje_profesores_tiempo_parcial(self, periodo):
        return null_to_numeric((self.cantidad_profesores_tiempo_parcial(periodo) / float(self.total_profesores_periodo(periodo)) * 100), 2)

    def porcentaje_profesores_medio_tiempo(self, periodo):
        return null_to_numeric((self.cantidad_profesores_medio_tiempo(periodo) / float(self.total_profesores_periodo(periodo)) * 100), 2)

    def porcentaje_profesores_tecnico_docente(self, periodo):
        return null_to_numeric((self.cantidad_profesores_tecnico_docente(periodo) / float(self.total_profesores_periodo(periodo)) * 100), 2)

    def cantidad_matriculados_discapacidad(self, modalidad, periodo):
        return Matricula.objects.filter(inscripcion__sede=self, nivel__periodo=periodo, inscripcion__persona__perfilinscripcion__tienediscapacidad=True, inscripcion__modalidad=modalidad).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados_fiscal_periodo_sede(self, periodo, carrera):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_FISCAL, sede=self, carrera=carrera, matricula__nivel__periodo=periodo).distinct().count()

    def cantidad_matriculados_fiscomi_periodo_sede(self, periodo, carrera):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_FISCOMISIONAL, sede=self, carrera=carrera, matricula__nivel__periodo=periodo).distinct().count()

    def cantidad_matriculados_particular_periodo_sede(self, periodo, carrera):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_PARTICULAR, sede=self, carrera=carrera, matricula__nivel__periodo=periodo).distinct().count()

    def cantidad_matriculados_municipal_periodo_sede(self, periodo, carrera):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_MUNICIPAL, sede=self, carrera=carrera, matricula__nivel__periodo=periodo).distinct().count()

    def cantidad_total_matriculados_fiscal_periodo_sede(self, periodo):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_FISCAL, sede=self, matricula__nivel__periodo=periodo).distinct().count()

    def cantidad_total_matriculados_fiscomi_periodo_sede(self, periodo):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_FISCOMISIONAL, sede=self, matricula__nivel__periodo=periodo).distinct().count()

    def cantidad_total_matriculados_particular_periodo_sede(self, periodo):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_PARTICULAR, sede=self, matricula__nivel__periodo=periodo).distinct().count()

    def cantidad_total_matriculados_municipal_periodo_sede(self, periodo):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_MUNICIPAL, sede=self, matricula__nivel__periodo=periodo).distinct().count()

    def cartera_general_sede(self):
        hoy = datetime.now().date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy, pasivo=False, inscripcion__sede=self, inscripcion__carrera__posgrado=False).exclude(inscripcion__modalidad__id=3).aggregate(valor=Sum('saldo'))['valor'], 2)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.sector = null_to_text(self.sector)
        self.ciudad = null_to_text(self.ciudad)
        self.direccion = null_to_text(self.direccion)
        self.telefono = null_to_text(self.telefono)
        super(Sede, self).save(*args, **kwargs)




class Modalidad(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    alias = models.CharField(default='', max_length=50, blank=True, verbose_name=u'Alias')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Modalidades"
        ordering = ['nombre']
        unique_together = ('nombre',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Modalidad.objects.filter(Q(nombre__icontains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.nombre + ' - ' + str(self.id)

    def cantidad_matriculados_periodo_sede(self, periodo, sede, carrera):
        return Matricula.objects.filter(inscripcion__sede=sede, inscripcion__carrera=carrera, inscripcion__modalidad=self, nivel__periodo=periodo).distinct().count()

    def cantidad_retirados_periodo_sede(self, periodo, sede, carrera):
        return Matricula.objects.filter(inscripcion__sede=sede, inscripcion__carrera=carrera, inscripcion__modalidad=self, nivel__periodo=periodo, retiromatricula__isnull=False).distinct().count()

    def cantidad_promovidos_periodo_sede(self, periodo, sede, carrera):
        return Matricula.objects.filter(inscripcion__sede=sede, inscripcion__carrera=carrera, inscripcion__modalidad=self, nivel__periodo=periodo, promovido=True).distinct().count()

    def cantidad_nopromovidos_periodo_sede(self, periodo, sede, carrera):
        return Matricula.objects.filter(inscripcion__sede=sede, inscripcion__carrera=carrera, inscripcion__modalidad=self, nivel__periodo=periodo, promovido=False).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_total_matriculados_periodo(self, periodo, sede):
        return Matricula.objects.filter(inscripcion__sede=sede, inscripcion__modalidad=self, nivel__periodo=periodo).distinct().count()

    def cantidad_total_retirados_periodo(self, periodo, sede):
        return Matricula.objects.filter(inscripcion__sede=sede, inscripcion__modalidad=self, nivel__periodo=periodo, retiromatricula__isnull=False).distinct().count()

    def cantidad_total_promovidos_periodo(self, periodo, sede):
        return Matricula.objects.filter(inscripcion__sede=sede, inscripcion__modalidad=self, nivel__periodo=periodo, promovido=True).distinct().count()

    def cantidad_total_nopromovidos_periodo(self, periodo, sede):
        return Matricula.objects.filter(inscripcion__sede=sede, inscripcion__modalidad=self, nivel__periodo=periodo, promovido=False).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_graduados(self, sede, carrera, inicio, fin):
        return Graduado.objects.filter(inscripcion__modalidad=self, inscripcion__sede=sede, inscripcion__carrera=carrera, fecharefrendacion__gte=inicio, fecharefrendacion__lte=fin).distinct().count()

    def cantidad_matriculados_discapacidad(self, sede, carrera, periodo):
        return Matricula.objects.filter(inscripcion__sede=sede, nivel__periodo=periodo, inscripcion__persona__perfilinscripcion__tienediscapacidad=True, inscripcion__carrera=carrera, inscripcion__modalidad=self).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados_fiscal_periodo_sede(self, periodo, sede, carrera):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_FISCAL, sede=sede, carrera=carrera, modalidad=self, matricula__nivel__periodo=periodo).distinct().count()

    def cantidad_matriculados_fiscomi_periodo_sede(self, periodo, sede, carrera):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_FISCOMISIONAL, sede=sede, carrera=carrera, modalidad=self, matricula__nivel__periodo=periodo).distinct().count()

    def cantidad_matriculados_particular_periodo_sede(self, periodo, sede, carrera):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_PARTICULAR, sede=sede, carrera=carrera, modalidad=self, matricula__nivel__periodo=periodo).distinct().count()

    def cantidad_matriculados_municipal_periodo_sede(self, periodo, sede, carrera):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_MUNICIPAL, sede=sede, carrera=carrera, modalidad=self, matricula__nivel__periodo=periodo).distinct().count()

    def cantidad_total_matriculados_fiscal_periodo_sede(self, periodo, sede):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_FISCAL, sede=sede, modalidad=self, matricula__nivel__periodo=periodo).distinct().count()

    def cantidad_total_matriculados_fiscomi_periodo_sede(self, periodo, sede):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_FISCOMISIONAL, sede=sede, modalidad=self, matricula__nivel__periodo=periodo).distinct().count()

    def cantidad_total_matriculados_particular_periodo_sede(self, periodo, sede):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_PARTICULAR, sede=sede, modalidad=self, matricula__nivel__periodo=periodo).distinct().count()

    def cantidad_total_matriculados_municipal_periodo_sede(self, periodo, sede):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_MUNICIPAL, sede=sede, modalidad=self, matricula__nivel__periodo=periodo).distinct().count()

    def cartera_general_sede_modalidad(self, sede):
        hoy = datetime.now().date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy, pasivo=False, inscripcion__sede=sede, inscripcion__carrera__posgrado=False, inscripcion__modalidad=self).aggregate(valor=Sum('saldo'))['valor'], 2)

    def cartera_general_distancia(self):
        hoy = datetime.now().date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy, pasivo=False, inscripcion__modalidad=self).aggregate(valor=Sum('saldo'))['valor'], 2)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(Modalidad, self).save(*args, **kwargs)


class ActividadEmpresaEmpleadora(ModeloBase):
    nombre = models.CharField(default='', max_length=50, verbose_name=u"Nombre")
    codigosniese = models.CharField(max_length=15, default='', verbose_name=u'Codigo Sniese')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Actividades de empresas empleadoras"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(ActividadEmpresaEmpleadora, self).save(*args, **kwargs)

TIPOS_INSTITUCIONES = (
    (1, u'PÚBLICA'),
    (2, u'PRIVADA'),
    (4, u'ORGANISMOS INTERNACIONALES'),
    (5, u'OTRO'),
    (6, u'MIXTA'),
    (7, u'ASOCIACIONES'),
    (8, u'COOPERATIVAS'),
    (9, u'COMUNIDADES'),
    (10, u'ONG'),
)

SECTOR_ECONOMICO = (
    (0, u'--'),
    (1, u'AGRICULTURA, GANADERÍA,  SILVICULTURA Y PESCA.'),
    (2, u'EXPLOTACIÓN DE MINAS Y CANTERAS.'),
    (3, u'INDUSTRIAS MANUFACTURERAS.'),
    (4, u'SUMINISTRO DE ELECTRICIDAD, GAS, VAPOR Y AIRE ACONDICIONADO.'),
    (5, u'DISTRIBUCIÓN DE AGUA; ALCANTARILLADO, GESTIÓN DE DESECHOS Y ACTIVIDADES DE SANEAMIENTO.'),
    (6, u'CONSTRUCCIÓN.'),
    (7, u'COMERCIO AL POR MAYOR Y AL POR MENOR; REPARACIÓN DE VEHÍCULOS AUTOMOTORES Y MOTOCICLETAS.'),
    (8, u'TRANSPORTE Y ALMACENAMIENTO.'),
    (9, u'ACTIVIDADES DE ALOJAMIENTO Y DE SERVICIO DE COMIDAS.'),
    (10, u'INFORMACIÓN Y COMUNICACIÓN.'),
    (11, u'ACTIVIDADES FINANCIERAS Y DE SEGUROS.'),
    (12, u'ACTIVIDADES INMOBILIARIAS.'),
    (13, u'ACTIVIDADES PROFESIONALES, CIENTÍFICAS Y TÉCNICAS.'),
    (14, u'ACTIVIDADES DE SERVICIOS ADMINISTRATIVOS Y DE APOYO.'),
    (15, u'ADMINISTRACIÓN PÚBLICA Y DEFENSA; PLANES DE SEGURIDAD SOCIAL DE AFILIACIÓN OBLIGATORIA.'),
    (16, u'ENSEÑANZA.'),
    (17, u'ACTIVIDADES DE ATENCIÓN DE LA SALUD HUMANA Y DE ASISTENCIA SOCIAL.'),
    (18, u'ARTES, ENTRETENIMIENTO Y RECREACIÓN.'),
    (19, u'OTRAS ACTIVIDADES DE SERVICIOS.'),
    (20, u'ACTIVIDADES DE LOS HOGARES COMO EMPLEADORES; ACTIVIDADES NO DIFERENCIADAS DE LOS HOGARES COMO PRODUCTORES DE BIENES Y SERVICIOS PARA USO PROPIO.'),
    (21, u'ACTIVIDADES DE ORGANIZACIONES Y ÓRGANOS EXTRATERRITORIALES.')
)

class EmpresaEmpleadora(ModeloBase):
    nombre = models.CharField(default='', max_length=250, verbose_name=u"Nombre")
    ruc = models.CharField(default='', max_length=13, verbose_name=u"RUC")
    provincia = models.ForeignKey(Provincia, blank=True, null=True, verbose_name=u"Provincia", on_delete=models.CASCADE)
    canton = models.ForeignKey(Canton, blank=True, null=True, verbose_name=u"Ciudad", on_delete=models.CASCADE)
    direccion = models.CharField(default='', max_length=100, verbose_name=u"Dirección")
    telefonos = models.CharField(default='', max_length=100, verbose_name=u"Teléfonos")
    celular = models.CharField(default='', max_length=100, verbose_name=u"Celular")
    autorizada = models.BooleanField(default=False, verbose_name=u"Autorizada")
    tipoinstitucion = models.IntegerField(default=1, choices=TIPOS_INSTITUCIONES, verbose_name=u"Tipo Institución")
    actividad = models.ForeignKey(ActividadEmpresaEmpleadora, blank=True, null=True, verbose_name=u"Actividad", on_delete=models.CASCADE)
    administradorexterno = models.CharField(default='', max_length=500, blank=True, null=True, verbose_name=u"Administrador externo")
    administradorinterno = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u"Administrador interno", on_delete=models.CASCADE)
    actividadeconomica = models.IntegerField(default=1, choices=SECTOR_ECONOMICO, verbose_name=u"Actividad Economica")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Empresas empleadoras"
        ordering = ['nombre']
        unique_together = ('ruc',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("EmpresaEmpleadora.objects.filter(Q(nombre__contains='%s') | Q(ruc__contains='%s') | Q(id=id_search('%s')))" % (q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_alias(self):
        return [self.ruc + " - " + self.nombre]

    def flexbox_repr(self):
        return self.ruc + " - " + self.nombre

    def empleador(self):
        return self.empleador_set.all()

    def tiene_representante(self):
        return self.representantelegalempresaempleadora_set.filter(fechainicio__lte=datetime.now().date(), fechafin__isnull=True).exists()

    def mi_representante(self):
        if self.tiene_representante():
            return self.representantelegalempresaempleadora_set.filter(fechainicio__lte=datetime.now().date(), fechafin__isnull=True)[0]
        return None

    def tiene_actividad(self):
        if self.conveniopasantia_set.exists():
            return True
        elif self.ofertalaboral_set.exists():
            return True
        return False

    def tiene_usuarios(self):
        return self.empleador_set.exists()

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.ruc = null_to_text(self.ruc)
        self.direccion = null_to_text(self.direccion)
        self.telefonos = null_to_text(self.telefonos)
        self.celular = null_to_text(self.celular)
        super(EmpresaEmpleadora, self).save(*args, **kwargs)


class RepresentanteLegalEmpresaEmpleadora(ModeloBase):
    empresaempleadora = models.ForeignKey(EmpresaEmpleadora, blank=True, null=True, verbose_name=u"Empresa", on_delete=models.CASCADE)
    nombres = models.CharField(default='', max_length=50, verbose_name=u'Nombres')
    cedula = models.CharField(default='', max_length=13, verbose_name=u"Cedula")
    telefono = models.CharField(default='', max_length=50, blank=True, null=True, verbose_name=u"Teléfono movil")
    telefono_conv = models.CharField(default='', max_length=50, blank=True, null=True, verbose_name=u"Teléfono fijo")
    email = models.CharField(default='', max_length=200, verbose_name=u"Correo electrónico personal")
    fechainicio = models.DateField(blank=True, null=True)
    fechafin = models.DateField(blank=True, null=True)
    cargo = models.CharField(default='', max_length=300, verbose_name=u"Cargo")

    def __str__(self):
        return u'%s' % self.nombres

    class Meta:
        verbose_name_plural = u"Representante Legal Empresa Empleadora"
        ordering = ['-fechainicio']
        unique_together = ('cedula',)

    def nombre_completo(self):
        return u'%s' % self.nombres

    def save(self, *args, **kwargs):
        self.nombres = null_to_text(self.nombres)
        self.cedula = null_to_text(self.cedula)
        self.telefono = null_to_text(self.telefono)
        self.telefono_conv = null_to_text(self.telefono_conv)
        self.email = null_to_text(self.email, lower=True)
        self.cargo = null_to_text(self.cargo)
        super(RepresentanteLegalEmpresaEmpleadora, self).save(*args, **kwargs)

class Empleador(ModeloBase):
    empresa = models.ForeignKey(EmpresaEmpleadora, verbose_name=u"Empresa", on_delete=models.CASCADE)
    persona = models.ForeignKey(Persona, verbose_name=u"Empleador", on_delete=models.CASCADE)
    cargo = models.CharField(default='', max_length=100, verbose_name=u"Cargo")
    activo = models.BooleanField(default=True, verbose_name=u"Activo")

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name_plural = u"Empleadores"
        unique_together = ('empresa', 'persona',)

    def save(self, *args, **kwargs):
        self.cargo = null_to_text(self.cargo)
        super(Empleador, self).save(*args, **kwargs)



class CambioClavePersona(ModeloBase):
    persona = models.ForeignKey(Persona, verbose_name=u'Persona', on_delete=models.CASCADE)
    clavecambio = models.CharField(default='', max_length=50, verbose_name=u'Cambio de clave')
    solicitada = models.BooleanField(default=False, verbose_name=u'Solicitada')

    class Meta:
        unique_together = ('persona',)


class TituloPersona(ModeloBase):
    persona = models.ForeignKey(Persona, verbose_name=u'Persona', on_delete=models.CASCADE)
    titulo = models.CharField(default='', max_length=50, verbose_name=u'Titulo')

    def __str__(self):
        return u'%s %s' % (self.titulo, self.persona.nombre_completo())

    class Meta:
        verbose_name_plural = u"Titulos"
        unique_together = ('persona',)

    def save(self, *args, **kwargs):
        self.titulo = null_to_text(self.titulo)
        super(TituloPersona, self).save(*args, **kwargs)


class FotoPersona(ModeloBase):
    persona = models.ForeignKey(Persona, verbose_name=u'Persona', on_delete=models.CASCADE)
    foto = models.FileField(upload_to='fotos/%Y/%m/%d', verbose_name=u'Foto')

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name_plural = u"Fotos"
        unique_together = ('persona',)

    def download_foto(self):
        return self.foto.url





class TipoTecnologicoUniversidad(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u' Nombre')
    codigosniese = models.CharField(max_length=15, default='', verbose_name=u'Codigo Sniese')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de Tecnologicos o Universidades"
        ordering = ['nombre']
        unique_together = ('nombre',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("TipoTecnologicoUniversidad.objects.filter(Q(nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_alias(self):
        return [self.nombre]

    def flexbox_repr(self):
        return self.nombre + ' - ' + str(self.id)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigosniese = null_to_text(self.codigosniese)
        super(TipoTecnologicoUniversidad, self).save(*args, **kwargs)


class TecnologicoUniversidad(ModeloBase):
    nombre = models.CharField(default='', max_length=400, verbose_name=u'Nombre')
    tipotecnologicouniversidad = models.ForeignKey(TipoTecnologicoUniversidad, blank=True, null=True, verbose_name=u'Tipo colegio', on_delete=models.CASCADE)
    universidad = models.BooleanField(default=True, verbose_name=u'Es universidad')
    pais = models.ForeignKey(Pais, blank=True, null=True, verbose_name=u'Pais', on_delete=models.CASCADE)
    codigosniese = models.CharField(max_length=15, default='', blank=True, verbose_name=u'Codigo Sniese')

    def __str__(self):
        return u'%s - %s' % (self.nombre, self.pais if self.pais else '')

    class Meta:
        verbose_name_plural = u"Tecnologicos o Universidades"
        ordering = ['nombre', 'pais']

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("TecnologicoUniversidad.objects.filter(Q(nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_alias(self):
        return [self.nombre]

    def flexbox_repr(self):
        return self.nombre + (" - " + self.pais.nombre if self.pais else '') + ' - ' + str(self.id)

    def extra_delete(self):
        return [True, False]

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigosniese = null_to_text(self.codigosniese)
        super(TecnologicoUniversidad, self).save(*args, **kwargs)

class Discapacidad(ModeloBase):
    nombre = models.CharField(default='', max_length=50, verbose_name=u'Nombre')
    codigosniese = models.CharField(max_length=15, default='', verbose_name=u'Codigo Sniese')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de discapacidades"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigosniese = null_to_text(self.codigosniese)
        super(Discapacidad, self).save(*args, **kwargs)



class TiempoDedicacionDocente(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    horas = models.FloatField(default=0, verbose_name=u'Horas')
    codigosniese = models.CharField(max_length=15, default='', verbose_name=u'Codigo Sniese')
    activo = models.BooleanField(default=False, verbose_name=u"Activo")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Dedicaciones docentes"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TiempoDedicacionDocente, self).save(*args, **kwargs)


class Especialidad(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Especialidades"
        ordering = ['nombre']
        unique_together = ('nombre',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Especialidad.objects.filter(Q(nombre__icontains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_alias(self):
        return [self.nombre]

    def flexbox_repr(self):
        return self.nombre + ' - ' + str(self.id)

    def extra_delete(self):
        return [True, False]

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(Especialidad, self).save(*args, **kwargs)


class Asignatura(ModeloBase):
    nombre = models.CharField(default='', max_length=600, verbose_name=u'Nombre')
    codigo = models.CharField(default='', max_length=30, verbose_name=u'Código')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Asignaturas"
        ordering = ["nombre"]
        unique_together = ('nombre',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Asignatura.objects.filter(Q(nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.nombre + " - " + self.codigo + ' - ' + str(self.id)

    def extra_delete(self):
        if self.en_uso():
            return [False, False]
        return [True, False]

    def disponible_periodo(self, periodo):
        return Materia.objects.filter(asignatura=self, nivel__periodo=periodo, cerrado=False).exists()

    def enuso_malla(self):
        return self.asignaturamalla_set.exists()

    def cantidad_mallas(self):
        return Malla.objects.filter(asignaturamalla__asignatura=self).distinct().count()

    def en_nivel_propedeutico(self, inscripcion):
        return inscripcion.mi_malla().asignaturamalla_set.filter(asignatura=self, nivelmalla_id=NIVEL_MALLA_CERO).exists()

    def permite_modificar(self):
        return not self.en_uso()

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigo = null_to_text(self.codigo)
        super(Asignatura, self).save(*args, **kwargs)




class TipoPeriodo(ModeloBase):
    nombre = models.CharField(default='', max_length=50, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de periodos"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoPeriodo, self).save(*args, **kwargs)


class Periodo(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    inicio = models.DateField(verbose_name=u'Fecha inicio')
    fin = models.DateField(verbose_name=u'Fecha fin')
    activo = models.BooleanField(default=True, verbose_name=u'Visible')
    matriculacionactiva = models.BooleanField(default=False, verbose_name=u'Activa la matriculación')
    prematriculacionactiva = models.BooleanField(default=False, verbose_name=u'Activa la pre matriculación')
    tipo = models.ForeignKey(TipoPeriodo, verbose_name=u'Tipo', on_delete=models.CASCADE)
    valida_asistencia = models.BooleanField(default=True, verbose_name=u'Valida asistencia')
    valida_deuda = models.BooleanField(default=False, verbose_name=u'Valida deudas')
    inicio_agregacion = models.DateField(verbose_name=u'Fecha inicio de agregaciones')
    limite_agregacion = models.DateField(verbose_name=u'Fecha límite de agregaciones')
    cerrado = models.BooleanField(default=False, verbose_name=u'Cerrado')
    visualiza = models.BooleanField(default=True, verbose_name=u'Pueden ver el período Docentes')
    parasolicitudes = models.BooleanField(default=False, verbose_name=u'Activo para solicitudes')
    inicio_solicitudes = models.DateField(default=timezone.now, blank=True, null=True, verbose_name=u'Fecha inicio de solicitudes')
    limite_solicitudes = models.DateField(default=timezone.now, blank=True, null=True, verbose_name=u'Fecha límite de solicitudes')
    modificar_niveles = models.BooleanField(default=False, verbose_name=u'Permite modificar niveles')

    def __str__(self):
        return u'%s: %s a %s' % (self.nombre, self.inicio.strftime('%d-%m-%Y'), self.fin.strftime('%d-%m-%Y'))

    class Meta:
        verbose_name_plural = u"Periodos lectivos"
        ordering = ['-inicio']
        unique_together = ('nombre',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Periodo.objects.filter(Q(nombre__contains='%s') | Q(tipo__nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.nombre + ' - ' + str(self.id)

    def esta_aprobadoevaluacion(self):
        proceso = ProcesoEvaluativoAcreditacion.objects.filter(periodo=self)[0]
        return proceso.aprovadoevaluacion

    def fecha_agregaciones(self):
        return self.inicio_agregacion <= datetime.now().date() <= self.limite_agregacion

    def periodo_repr(self):
        return MESES_CHOICES[self.inicio.month - 1][1] + " " + str(self.inicio.year) + " a " + MESES_CHOICES[self.fin.month - 1][0] + " " + str(self.fin.year)

    def es_posgrado(self):
        return self.tipo_id == TIPO_PERIODO_POSGRADO

    def es_grado(self):
        return self.tipo_id == TIPO_PERIODO_GRADO

    def esta_cerrado(self):
        return self.cerrado

    def puede_eliminarse(self):
        if self.nivel_set.exists():
            return False
        return True

    def auto_evaluacion(self, profesor):
        return RespuestaEvaluacionAcreditacion.objects.filter(proceso__periodo=self, profesor=profesor, tipoinstrumento=2)[0]

    def evaluacion_docente(self, profesor):
        return RespuestaEvaluacionAcreditacion.objects.filter(proceso__periodo=self, profesor=profesor)[0]

    def cantidad_matriculas_solo_modulos(self):
        return Matricula.objects.filter(materiasregulares=F('materiasmodulos'), nivel__periodo=self).count()

    def cantidad_matriculados_carrera_sin_provincia(self, carrera):
        return Matricula.objects.filter(inscripcion__persona__provincia__isnull=True, inscripcion__carrera=carrera, nivel__periodo=self, retiromatricula__isnull=True).count()

    def cantidad_matriculados_sin_provincia(self):
        return Matricula.objects.filter(inscripcion__persona__provincia__isnull=True, nivel__periodo=self, retiromatricula__isnull=True).count()

    def porciento_matriculados_sin_provincia(self):
        total = total_matriculados(self)
        if total:
            return null_to_numeric((self.cantidad_matriculados_sin_provincia() / float(total)) * 100.0, 2)
        return 0

    def rubros_generados(self):
        if RubroCuota.objects.filter(matricula__nivel__periodo=self).exists():
            return True
        elif RubroMatricula.objects.filter(matricula__nivel__periodo=self).exists():
            return True
        return False

    def proceso_evaluativo(self):
        return self.proceso_evaluativoacreditacion()

    def proceso_evaluativo_docente(self):
        return self.proceso_evaluativodocente()

    def proceso_evaluativoacreditacion(self):
        if ProcesoEvaluativoAcreditacion.objects.filter(periodo=self).exists():
            proceso = ProcesoEvaluativoAcreditacion.objects.filter(periodo=self)[0]
        else:
            proceso = ProcesoEvaluativoAcreditacion(periodo=self,
                                                    instrumentoheteroinicio=self.inicio,
                                                    instrumentoheterofin=self.fin,
                                                    instrumentoheteroactivo=False,
                                                    instrumentoautoinicio=self.inicio,
                                                    instrumentoautofin=self.fin,
                                                    instrumentoautoactivo=False,
                                                    instrumentodirectivoinicio=self.inicio,
                                                    instrumentodirectivofin=self.fin,
                                                    instrumentodirectivoactivo=False,
                                                    instrumentoparinicio=self.inicio,
                                                    instrumentoparfin=self.fin,
                                                    instrumentoparactivo=False)
            proceso.save()
        return proceso

    def proceso_evaluativodocente(self):
        if ProcesoEvaluativoDocente.objects.filter(periodo=self).exists():
            proceso = ProcesoEvaluativoDocente.objects.filter(periodo=self)[0]
        else:
            proceso = ProcesoEvaluativoDocente(periodo=self, instrumentoheteroinicio=self.inicio, instrumentoheterofin=self.fin, instrumentoheteroactivo=False)
            proceso.save()
        return proceso

    def proceso_beca(self, form):
        proceso_de_beca = FechaProcesosBeca(periodo=self,
                                            fechainicio=form.cleaned_data['fechainicio'],
                                            fechafin=form.cleaned_data['fechafin'],
                                            nombre=form.cleaned_data['nombre'],
                                            activo=False)
        proceso_de_beca.save()
        return proceso_de_beca

    def semanas(self):
        d = self.inicio
        d -= timedelta(d.weekday())
        semanas = []
        while d < self.fin:
            semana = (d, d + timedelta(4))
            semanas.append(semana)
            d = d + timedelta(7)
        return semanas

    def cronograma_actualizacion_datos(self):
        if self.cronogramaactualizaciondatos_set.exists():
            return self.cronogramaactualizaciondatos_set.all()[0]
        else:
            cronograma = CronogramaActualizacionDatos(periodo=self,
                                                      activopersonales=False,
                                                      datospersonaleshasta=self.fin,
                                                      activomedicos=False,
                                                      datosmedicoshasta=self.fin,
                                                      activosocioeconomicos=False,
                                                      datossocioeconomicoshasta=self.fin)
            cronograma.save()
            return cronograma

    def matriculados(self):
        return Matricula.objects.filter(nivel__periodo=self)

    def total_matriculados_retirados(self):
        return Matricula.objects.filter(nivel__periodo=self, retiromatricula__isnull=False).count()

    def total_matriculados_regular(self):
        return Matricula.objects.filter(nivel__periodo=self, tipomatricula__id=MATRICULA_REGULAR_ID).exclude(retiromatricula__isnull=False).count()

    def total_matriculados_extraordinarias(self):
        return Matricula.objects.filter(nivel__periodo=self, tipomatricula__id=MATRICULA_EXTRAORDINARIA_ID).exclude(retiromatricula__isnull=False).count()

    def total_matriculados_especiales(self):
        return Matricula.objects.filter(nivel__periodo=self, tipomatricula__id=MATRICULA_ESPECIAL_ID).exclude(retiromatricula__isnull=False).count()

    def finalizo(self):
        return datetime.now().date() > self.fin

    def vigente(self):
        return self.fin >= datetime.now().date() >= self.inicio

    def proximosperiodos(self):
        return self.fin >= datetime.now().date()

    def nombre_corto(self):
        return self.tipo.nombre + " - " + self.inicio.strftime("%d-%m-%Y") + " - " + self.fin.strftime("%d-%m-%Y")

    def clases_horario(self, dia, turno, materias):
        return Clase.objects.filter(materia__in=materias, dia=dia, turno=turno, activo=True).distinct()

    def distributivo_horas(self):
        if not self.criteriodocenciaperiodo_set.filter(criterio__id=CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID).exists():
            criterio = CriterioDocenciaPeriodo(criterio_id=CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID,
                                               periodo=self)
            criterio.save()
        if not self.criteriodocenciaperiodo_set.filter(criterio__id=CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID).exists():
            criterio = CriterioDocenciaPeriodo(criterio_id=CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID,
                                               periodo=self)
            criterio.save()
        if not self.criteriodocenciaperiodo_set.filter(criterio__id=CRITERIO_HORAS_CLASE_PARCIAL_ID).exists():
            criterio = CriterioDocenciaPeriodo(criterio_id=CRITERIO_HORAS_CLASE_PARCIAL_ID,
                                               periodo=self)
            criterio.save()

        if not self.criteriodocenciaperiodo_set.filter(criterio__id=CRITERIO_HORAS_CLASE_TECNICO_DOCENTE_ID).exists():
            criterio = CriterioDocenciaPeriodo(criterio_id=CRITERIO_HORAS_CLASE_TECNICO_DOCENTE_ID,
                                               periodo=self)
            criterio.save()

    def total_matriculados(self):
        return Matricula.objects.filter(nivel__periodo=self, retiromatricula__isnull=True).distinct().count()

    def sedes(self):
        return Sede.objects.filter(inscripcion__matricula__nivel__periodo=self).distinct()

    def cantidad_matriculados_primernivel(self):
        return Matricula.objects.filter(nivel__periodo=self, nivelmalla__id=NIVEL_MALLA_UNO).distinct().count()

    def cantidad_retirados_primernivel(self):
        return Matricula.objects.filter(nivel__periodo=self, nivelmalla__id=NIVEL_MALLA_UNO, retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados_primernivel_nuevos(self):
        return Matricula.objects.filter(nivel__periodo=self, nivelmalla__id=NIVEL_MALLA_UNO).exclude(materiaasignada__matriculas__gte=2).distinct().count()

    def cantidad_matriculados_primernivel_repetidores(self):
        return Matricula.objects.filter(nivel__periodo=self, nivelmalla__id=NIVEL_MALLA_UNO, materiaasignada__matriculas__gte=2).distinct().count()

    def cantidad_matriculados(self, carrera):
        return Matricula.objects.filter(inscripcion__carrera=carrera, nivel__periodo=self).distinct().count()

    def cantidad_retirados(self, carrera):
        return Matricula.objects.filter(inscripcion__carrera=carrera, nivel__periodo=self, retiromatricula__isnull=False).distinct().count()

    def cantidad_promovidos(self, carrera):
        return Matricula.objects.filter(inscripcion__carrera=carrera, nivel__periodo=self, promovido=True).distinct().count()

    def cantidad_nopromovidos(self, carrera):
        return Matricula.objects.filter(inscripcion__carrera=carrera, nivel__periodo=self, promovido=False).distinct().count()

    def cantidad_total_matriculados(self):
        return Matricula.objects.filter(nivel__periodo=self).distinct().count()

    def cantidad_total_retirados(self):
        return Matricula.objects.filter(nivel__periodo=self, retiromatricula__isnull=False).distinct().count()

    def cantidad_total_promovidos(self):
        return Matricula.objects.filter(nivel__periodo=self, promovido=True).distinct().count()

    def cantidad_total_nopromovidos(self):
        return Matricula.objects.filter(nivel__periodo=self, promovido=False).distinct().count()

    def cantidad_discapacitados(self):
        return Matricula.objects.filter(nivel__periodo=self, inscripcion__persona__perfilinscripcion__tienediscapacidad=True).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados_fiscal_periodo_sede(self, carrera):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_FISCAL, carrera=carrera, matricula__nivel__periodo=self).distinct().count()

    def cantidad_matriculados_fiscomi_periodo_sede(self, carrera):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_FISCOMISIONAL, carrera=carrera, matricula__nivel__periodo=self).distinct().count()

    def cantidad_matriculados_particular_periodo_sede(self, carrera):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_PARTICULAR, carrera=carrera, matricula__nivel__periodo=self).distinct().count()

    def cantidad_matriculados_municipal_periodo_sede(self, carrera):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_MUNICIPAL, carrera=carrera, matricula__nivel__periodo=self).distinct().count()

    def cantidad_total_matriculados_fiscal_periodo_sede(self):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_FISCAL, matricula__nivel__periodo=self).distinct().count()

    def cantidad_total_matriculados_fiscomi_periodo_sede(self):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_FISCOMISIONAL, matricula__nivel__periodo=self).distinct().count()

    def cantidad_total_matriculados_particular_periodo_sede(self):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_PARTICULAR, matricula__nivel__periodo=self).distinct().count()

    def cantidad_total_matriculados_municipal_periodo_sede(self):
        return Inscripcion.objects.filter(persona__estudiopersona__institucioneducacionbasica__tipocolegio__id=TIPO_COLEGIO_MUNICIPAL, matricula__nivel__periodo=self).distinct().count()

    def niveles_sede_periodo(self, sede):
        return self.nivel_set.filter(sede=sede).order_by('inicio')

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(Periodo, self).save(*args, **kwargs)


class Locacion(ModeloBase):
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Locaciones"
        ordering = ['nombre']

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(Locacion, self).save(*args, **kwargs)


class NombreNivelacion(ModeloBase):
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Nombres de nivelaciones"
        ordering = ['nombre']
        unique_together = ('periodo', 'sede',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(NombreNivelacion, self).save(*args, **kwargs)


class Sesion(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    sede = models.ForeignKey(Sede, blank=True, null=True, on_delete=models.CASCADE)
    comienza = models.TimeField(verbose_name=u'Hora inicio')
    termina = models.TimeField(verbose_name=u'Hora fin')
    lunes = models.BooleanField(default=True, verbose_name=u'Lunes')
    martes = models.BooleanField(default=True, verbose_name=u'Martes')
    miercoles = models.BooleanField(default=True, verbose_name=u'Miercoles')
    jueves = models.BooleanField(default=True, verbose_name=u'Jueves')
    viernes = models.BooleanField(default=True, verbose_name=u'Viernes')
    sabado = models.BooleanField(default=False, verbose_name=u'Sabado')
    domingo = models.BooleanField(default=False, verbose_name=u'Domingo')
    codigo = models.CharField(default='', max_length=10, verbose_name=u'Código')

    def __str__(self):
        return u'%s - %s a %s' % (self.nombre, self.comienza.strftime("%I:%M %p"), self.termina.strftime("%I:%M %p"))

    class Meta:
        verbose_name_plural = u"Sesiones"
        ordering = ['comienza']
        unique_together = ('nombre',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Sesion.objects.filter(Q(nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.nombre + ' - ' + str(self.id)

    def dia_habilitado(self, dia):
        if dia == 1 and self.lunes:
            return True
        if dia == 2 and self.martes:
            return True
        if dia == 3 and self.miercoles:
            return True
        if dia == 4 and self.jueves:
            return True
        if dia == 5 and self.viernes:
            return True
        if dia == 6 and self.sabado:
            return True
        if dia == 7 and self.domingo:
            return True
        return False

    def cantidad_dias_plus_1(self):
        cant = 0
        for i in range(1, 8):
            cant += 1 if self.clases_los_(i) else 0
        return cant + 1

    def semana(self):
        s = []
        if self.lunes:
            s.append(("Lunes", 1))
        if self.martes:
            s.append(("Martes", 2))
        if self.miercoles:
            s.append(("Miercoles", 3))
        if self.jueves:
            s.append(("Jueves", 4))
        if self.viernes:
            s.append(("Viernes", 5))
        if self.sabado:
            s.append(("Sabado", 6))
        if self.domingo:
            s.append(("Domingo", 7))
        return s

    def toda_semana(self):
        return [("Lunes", 1), ("Martes", 2), ("Miercoles", 3), ("Jueves", 4), ("Viernes", 5), ("Sabado", 6), ("Domingo", 7)]

    def clases_los_(self, x):
        if x == 1:
            return self.lunes
        if x == 2:
            return self.martes
        if x == 3:
            return self.miercoles
        if x == 4:
            return self.jueves
        if x == 5:
            return self.viernes
        if x == 6:
            return self.sabado
        if x == 7:
            return self.domingo

    def repr_dias(self):
        if self.lunes and self.martes and self.miercoles and self.jueves and self.viernes and self.sabado and self.domingo:
            return "Toda la Semana"
        elif self.lunes and self.martes and self.miercoles and self.jueves and self.viernes and not self.sabado and not self.domingo:
            return "Dias Laborables"
        elif not self.lunes and not self.martes and not self.miercoles and not self.jueves and not self.viernes and self.sabado and self.domingo:
            return "Fines de Semana"
        else:
            dias = []
            if self.lunes:
                dias.append("Lunes")
            if self.martes:
                dias.append("Martes")
            if self.miercoles:
                dias.append("Miercoles")
            if self.jueves:
                dias.append("Jueves")
            if self.viernes:
                dias.append("Viernes")
            if self.sabado:
                dias.append("Sabado")
            if self.domingo:
                dias.append("Domingo")
            return ", ".join(dias)

    def repr_dias_resumido(self):
        if self.lunes and self.martes and self.miercoles and self.jueves and self.viernes and self.sabado and self.domingo:
            return "Toda la Semana"
        elif self.lunes and self.martes and self.miercoles and self.jueves and self.viernes and not self.sabado and not self.domingo:
            return "Dias Laborables"
        elif not self.lunes and not self.martes and not self.miercoles and not self.jueves and not self.viernes and self.sabado and self.domingo:
            return "Fines de Semana"
        else:
            dias = []
            if self.lunes:
                dias.append("Lu")
            if self.martes:
                dias.append("Ma")
            if self.miercoles:
                dias.append("Mi")
            if self.jueves:
                dias.append("Ju")
            if self.viernes:
                dias.append("Vi")
            if self.sabado:
                dias.append("Sa")
            if self.domingo:
                dias.append("Do")
            return ", ".join(dias)

    def cantidad_turnos(self):
        return Turno.objects.filter(sesion=self).count()

    def turnos(self):
        return Turno.objects.filter(sesion=self).order_by('comienza')

    def turnos_clase(self, clases):
        return Turno.objects.filter(sesion=self, clase__in=clases).distinct().order_by('comienza')

    def turnos_clase_practica(self, clases):
        return Turno.objects.filter(sesion=self, clasepractica__in=clases).distinct().order_by('comienza')

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigo = null_to_text(self.codigo)
        super(Sesion, self).save(*args, **kwargs)




class NivelMalla(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    promediar = models.BooleanField(default=False, verbose_name=u'Promediar')
    nivelacion = models.BooleanField(default=False, verbose_name=u'Nivel de nivelación')
    grado = models.BooleanField(default=False, verbose_name=u'Costo fijo')
    codigosniese = models.CharField(max_length=15, default='', verbose_name=u'Codigo Sniese')

    class Meta:
        verbose_name_plural = u"Niveles de malla"
        ordering = ['id']
        unique_together = ('nombre',)

    def __str__(self):
        return u'%s' % self.nombre

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("NivelMalla.objects.filter(Q(nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.nombre + ' - ' + str(self.id)

    def total_horas(self, malla):
        return null_to_numeric(self.asignaturamalla_set.filter(malla=malla).aggregate(valor=Sum('horas'))['valor'], 1)

    def total_creditos(self, malla):
        return null_to_numeric(self.asignaturamalla_set.filter(malla=malla).aggregate(valor=Sum('creditos'))['valor'], 4)

    def es_nivelacion(self):
        return self.id == NIVEL_MALLA_CERO

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigosniese = null_to_text(self.codigosniese)
        super(NivelMalla, self).save(*args, **kwargs)


class TipoDuraccionMalla(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    codigosniese = models.CharField(max_length=15, default='', verbose_name=u'Codigo Sniese')

    class Meta:
        verbose_name_plural = u"Tipo duraccion malla"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def __str__(self):
        return u'%s' % self.nombre

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigosniese = null_to_text(self.codigosniese)
        super(TipoDuraccionMalla, self).save(*args, **kwargs)




class Malla(ModeloBase):
    carrera = models.ForeignKey(Carrera, verbose_name=u"Carrera", on_delete=models.CASCADE)
    inicio = models.DateField(verbose_name=u"Fecha aprobación")
    fin = models.DateField(verbose_name=u"Fecha fin vigencia", blank=True, null=True)
    horaspracticas = models.FloatField(default=0, verbose_name=u"Horas de practicas")
    nivelhoraspracticas = models.ForeignKey(NivelMalla, related_name='nivelhoraspracticas', blank=True, null=True, on_delete=models.CASCADE)
    horasvinculacion = models.FloatField(default=0, verbose_name=u"Horas de vinculacion")
    nivelhorasvinculacion = models.ForeignKey(NivelMalla, related_name='nivelhorasvinculacion', blank=True, null=True, on_delete=models.CASCADE)
    horastrabajotitulacion = models.FloatField(default=0, verbose_name=u"Horas del trabajo de titulacion")
    niveltrabajotitulacion = models.ForeignKey(NivelMalla, related_name='niveltrabajotitulacion', blank=True, null=True, on_delete=models.CASCADE)
    creditoscompletar = models.FloatField(default=0, verbose_name=u"No. créditos a completar")
    materiascompletar = models.IntegerField(default=0, verbose_name=u"No. materias a completar")
    libreopcion = models.IntegerField(default=0, verbose_name=u"No. materias libre opción")
    optativas = models.IntegerField(default=0, verbose_name=u"No. materias Optativas")
    modalidad = models.ForeignKey(Modalidad, verbose_name=u"Modalidad", blank=True, null=True, on_delete=models.CASCADE)
    nivelesregulares = models.IntegerField(default=0, verbose_name=u"Niveles regulares")
    tipo = models.IntegerField(choices=TiposMalla.choices, default=TiposMalla.CREDITOS, verbose_name=u"Tipo de malla")
    vigencia = models.IntegerField(default=1, verbose_name=u'Vigencia')
    resolucion = models.CharField(default='', verbose_name=u'Resolucion', max_length=100)
    codigo = models.CharField(default='', verbose_name=u'Codigo', max_length=30)
    # tituloobtenido = models.ForeignKey(TituloObtenido, verbose_name=u"Titulo obtenido", blank=True, null=True, on_delete=models.CASCADE)
    tipoduraccionmalla = models.ForeignKey(TipoDuraccionMalla, blank=True, null=True, on_delete=models.CASCADE)
    cantidadsemanas = models.IntegerField(default=0, verbose_name=u"Cantidad semanas")
    cantidadarrastres = models.IntegerField(default=0, verbose_name=u"Cantidad arrastres")
    organizacionaprendizaje = models.FloatField(default=0, verbose_name=u"Organizacion aprendizaje")
    nivelacion = models.BooleanField(default=False, verbose_name=u"Nivelacion")
    matriculaonline = models.BooleanField(default=True, verbose_name=u"Permite matricula online")
    modelosibalo = models.BooleanField(default=False, verbose_name=u"Modelos de silabo")
    maximomateriasonline = models.IntegerField(default=0, verbose_name=u"Maximo materias matricula online")
    competenciasespecificas = models.ManyToManyField(CompetenciaEspecifica, verbose_name=u"Competencias especificas")
    competenciasgenericas = models.ManyToManyField(CompetenciaGenerica, verbose_name=u"Competencias genéricas")
    perfildeegreso = models.TextField(default='', verbose_name=u'Perfil de egreso')
    observaciones = models.TextField(default='', verbose_name=u'Observaciones')
    validacion = models.IntegerField(default=0, verbose_name=u"Validacion")
    aprobado = models.BooleanField(default=False, verbose_name=u"Aprobado")
    persona_aprueba = models.ForeignKey(Persona, related_name='persona_aprueba', blank=True, null=True, on_delete=models.CASCADE)
    fecha_aprueba = models.DateField(verbose_name=u"Fecha de aprobacion", blank=True, null=True)
    activo = models.BooleanField(default=False, verbose_name=u"Activo")

    def __str__(self):
        return u'%s - %s - %s al %s - id malla: %s' % (self.carrera, self.modalidad, self.inicio.year, self.fin.year, self.id)

    class Meta:
        verbose_name_plural = u"Mallas curriculares"
        ordering = ('carrera', '-inicio', 'modalidad')

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Malla.objects.filter(Q(carrera__nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.carrera.nombre + " - " + str(self.inicio.year) + " - " + ((self.modalidad.nombre + " - ") if self.modalidad else "") + ((self.tituloobtenido.nombre + " - ") if self.tituloobtenido else "") + ' - ' + str(self.id)

    def tiene_asignaturas_malla(self):
        return self.asignaturamalla_set.exists()

    def codigos(self):
        return self.informacionsedemalla_set.all()

    def cantidad_materias(self, inscripcion):
        return self.asignaturamalla_set.filter().count()



    def cantidad_estudiantes_usando(self):
        return self.inscripcionmalla_set.count()

    def tiene_estudiantes_usando(self):
        return self.inscripcionmalla_set.exists()

    def tiene_materias_practicas(self):
        return self.asignaturamalla_set.filter(practicas=True).exists()

    def niveles_usada(self):
        return Nivel.objects.filter(malla=self)

    def precio_periodo(self, nivel, periodo, sede):
        if self.preciosperiodo_set.filter(periodo=periodo, nivel=nivel, sede=sede).exists():
            prec_periodo = self.preciosperiodo_set.filter(periodo=periodo, nivel=nivel, sede=sede)[0]
        else:
            prec_periodo = PreciosPeriodo(periodo=periodo,
                                          nivel=nivel,
                                          carrera=self.carrera,
                                          modalidad=self.modalidad,
                                          sede=sede,
                                          malla=self,
                                          preciomatricula=0,
                                          precioarancel=0,
                                          precioderechorotativo=0,
                                          fecha=periodo.inicio)
            prec_periodo.save()
            prec_periodo.generardetalle()
        return prec_periodo

    def inicio_anno(self):
        return self.inicio.year

    def cantidad_creditos(self):
        creditosmalla = null_to_numeric(self.asignaturamalla_set.filter().aggregate(valor=Sum('creditos'))['valor'], 4)
        return null_to_numeric(creditosmalla , 4)

    def cantidad_creditos_solo_malla(self, inscripcion):
        return null_to_numeric(self.asignaturamalla_set.filter().aggregate(valor=Sum('creditos'))['valor'], 4)

    def cantidad_materiascompletar(self):
        materiasmalla = self.asignaturamalla_set.filter().count()
        return materiasmalla

    def total_ceditos_nivel(self, nivel):
        return null_to_numeric(self.asignaturamalla_set.filter(nivelmalla=nivel).aggregate(valor=Sum('creditos'))['valor'], 4)

    def total_ceditos_nivel_debe_matricularse(self, nivel, inscripcion):
        return null_to_numeric(self.asignaturamalla_set.filter(nivelmalla=nivel).filter(matriculacion=True).aggregate(valor=Sum('creditos'))['valor'], 4)

    def total_ceditos_eje(self, eje):
        return null_to_numeric(self.asignaturamalla_set.filter( ejeformativo=eje).aggregate(valor=Sum('creditos'))['valor'], 4)

    def horas(self):
        return null_to_numeric(self.asignaturamalla_set.filter().aggregate(valor=Sum('horas'))['valor'], 1)

    def total_totales(self):
        return null_to_numeric(self.horaspracticas + self.horasvinculacion + self.horas(), 1)

    def total_horas_nivel(self, nivel):
        return null_to_numeric(self.asignaturamalla_set.filter(nivelmalla=nivel).aggregate(valor=Sum('horas'))['valor'], 1)

    def total_horas_eje(self, eje):
        return null_to_numeric(self.asignaturamalla_set.filter( ejeformativo=eje).aggregate(valor=Sum('horas'))['valor'], 1)

    def total_valor_nivel(self, nivel):
        return null_to_numeric(self.asignaturamalla_set.filter(nivelmalla=nivel).aggregate(valor=Sum('costo'))['valor'], 2)

    def total_valor_eje(self, eje):
        return null_to_numeric(self.asignaturamalla_set.filter(ejeformativo=eje).aggregate(valor=Sum('costo'))['valor'], 2)

    def total_valor(self):
        return null_to_numeric(self.asignaturamalla_set.all().aggregate(valor=Sum('costo'))['valor'], 2)

    def creditos_acumulados(self, nivelmalla):
        return null_to_numeric(self.asignaturamalla_set.filter(nivelmalla__id__lte=nivelmalla).aggregate(valor=Sum('creditos'))['valor'], 4)

    def mis_niveles(self):
        return NivelMalla.objects.filter(asignaturamalla__malla=self).distinct()

    def nivel_malla(self, idn):
        if NivelMalla.objects.filter(id=idn).exists():
            return NivelMalla.objects.get(pk=idn)
        else:
            nivelmalla = NivelMalla(id=idn, nombre='NIVEL ' + str(id))
            nivelmalla.save()
            return nivelmalla

    def lista_niveles(self):
        return [self.nivel_malla(x) for x in range(0 if self.nivelacion else 1, self.nivelesregulares + 1)]

    def asignatura_malla(self, eje, nivelmalla):
        return self.asignaturamalla_set.filter(nivelmalla=nivelmalla, ejeformativo=eje)

    def asignatura_malla_itinerario(self, eje, nivelmalla, inscripcion):
        return self.asignaturamalla_set.filter( nivelmalla=nivelmalla, ejeformativo=eje).distinct()

    def asignaturas_malla_sin_itinerario(self, eje, nivelmalla):
        return self.asignaturamalla_set.filter(nivelmalla=nivelmalla, ejeformativo=eje)

    def asignaturas_malla_sin_itinerario_basico(self, eje, nivelmalla):
        return self.asignaturamalla_set.filter(nivelmalla=nivelmalla, ejeformativo=eje)
        # return self.asignaturamalla_set.filter(Q(itinerario__isnull=True) | Q(itinerario=inscripcion.mi_itinerario()), nivelmalla=nivelmalla, ejeformativo=eje)

    def puede_eliminarse(self):
        if self.inscripcionmalla_set.exists():
            return False
        elif self.asignaturamalla_set.exists():
            return False
        return True

    def puede_modificarse(self):
        if self.inscripcionmalla_set.exists():
            return False
        elif self.materia_set.exists():
            return False
        return True

    def extra_delete(self):
        return [True, True]

    def nivel_malla_uso(self, nivel):
        return AsignaturaMalla.objects.filter(Q(historicorecordacademico__isnull=False) | Q(materia__isnull=False), malla=self, nivelmalla=nivel).exists()

    def nivel_maximo_estudiantes(self, nivelmalla):
        return Inscripcion.objects.filter(inscripcionmalla__malla=self, inscripcionnivel__nivel__id__gt=nivelmalla.id).exists()

    def informacion_sede(self, sede):
        if self.informacionsedemalla_set.filter(sede=sede).exists():
            return self.informacionsedemalla_set.filter(sede=sede)[0]
        else:
            infomalla = InformacionSedeMalla(malla=self,
                                             sede=sede)
            infomalla.save()
            return infomalla

    def permite_modificar(self):
        if self.materia_set.exists():
            return False
        elif self.inscripcionmalla_set.exists():
            return False
        elif self.nivel_set.exists():
            return False
        return True

    def horas_practicas(self):
        return null_to_numeric(self.asignaturamalla_set.all().aggregate(horas=Sum('horaspracticasprofesionales'))['horas'], 1)

    def usando_competencia_especifica(self, competencia):
        return competencia.planificacionmateria_set.filter(materia__asignaturamalla__malla=self).exists()

    def usando_competencia_generica(self, competencia):
        return competencia.planificacionmateria_set.filter(materia__asignaturamalla__malla=self).exists()

    def vigente(self):
        return datetime.now().date() >= self.inicio and datetime.now().date() <= self.fin

    def precio_modulo_inscripcion(self, periodo, sede, carrera, modalidad, malla):
        if self.preciosperiodomodulosinscripcion_set.filter(periodo=periodo, sede=sede, carrera=carrera, modalidad=modalidad,malla=malla).exists():
            prec_periodo = self.preciosperiodomodulosinscripcion_set.filter(periodo=periodo, sede=sede, carrera=carrera, modalidad=modalidad,malla=malla)[0]
        else:
            prec_periodo = PreciosPeriodoModulosInscripcion(periodo=periodo,
                                                            malla=self,
                                                            sede=sede,
                                                            carrera=carrera,
                                                            modalidad=modalidad,
                                                            precioinscripcion=0,
                                                            precioinduccion=0,
                                                            porcentajesegundamatricula=0,
                                                            porcentajeterceramatricula=0,
                                                            porcentajematriculaextraordinaria=0,
                                                            preciomodulo=0,
                                                            preciotitulacion=0,
                                                            precioadelantoidiomas=0)
            prec_periodo.save()
        return prec_periodo

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.creditos_completar = self.cantidad_creditos()
        self.materias_completar = self.cantidad_materiascompletar()
        self.perfildeegreso = null_to_text(self.perfildeegreso)
        self.observaciones = null_to_text(self.observaciones)
        self.resolucion = null_to_text(self.resolucion)
        self.codigo = null_to_text(self.codigo)
        super(Malla, self).save(*args, **kwargs)


class InformacionSedeMalla(ModeloBase):
    malla = models.ForeignKey(Malla, verbose_name=u"Malla", on_delete=models.CASCADE)
    sede = models.ForeignKey(Sede, verbose_name=u"Sede", on_delete=models.CASCADE)
    codigo = models.CharField(default='', max_length=200, verbose_name=u'Codigo')
    lugar = models.CharField(default='',blank=True, null=True,max_length=200, verbose_name=u'Lugar ejecucion')

    def __str__(self):
        return u'%s - %s' % (self.malla.carrera.nombre, self.codigo)

    class Meta:
        verbose_name_plural = u"Información de Sede de la malla"

    def cantidad_inscritos(self):
        return Inscripcion.objects.filter(inscripcionmalla__malla=self.malla, sede=self.sede).distinct().count()

    def cantidad_egregsados(self):
        return Inscripcion.objects.filter(inscripcionmalla__malla=self.malla, sede=self.sede, egresado__isnull=False, graduado__isnull=True).distinct().count()

    def cantidad_graduados(self):
        return Inscripcion.objects.filter(inscripcionmalla__malla=self.malla, sede=self.sede, egresado__isnull=False, graduado__isnull=False).distinct().count()

    def save(self, *args, **kwargs):
        self.codigo = null_to_text(self.codigo)
        super(InformacionSedeMalla, self).save(*args, **kwargs)


class EvidenciaMalla(ModeloBase):
    fecha = models.DateField(verbose_name=u'Fecha')
    malla = models.ForeignKey(Malla, verbose_name=u"Malla", on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    descripcion = models.TextField(default='', verbose_name=u'Descripción')
    archivo = models.FileField(upload_to='archivo/%Y/%m/%d', blank=True, null=True, verbose_name=u'Solicitudes')

    def __str__(self):
        return u'%s - %s' % (self.malla.carrera.nombre, self.nombre)

    class Meta:
        verbose_name_plural = u"Evidencias de la malla"

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.descripcion = null_to_text(self.descripcion)
        super(EvidenciaMalla, self).save(*args, **kwargs)

class TipoMateria(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de materias"
        ordering = ['id']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoMateria, self).save(*args, **kwargs)


class CampoFormacion(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Campo Formacion"
        ordering = ['id']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(CampoFormacion, self).save(*args, **kwargs)


class AreaConocimiento(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    codigo = models.CharField(default='', max_length=50, verbose_name=u'Código')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Areas de conocimientos"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigo = null_to_text(self.codigo)
        super(AreaConocimiento, self).save(*args, **kwargs)



class EjeFormativo(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Ejes formativos"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(EjeFormativo, self).save(*args, **kwargs)


#
# class Itinerario(ModeloBase):
#     malla = models.ForeignKey(Malla, blank=True, null=True, verbose_name=u'Malla', on_delete=models.CASCADE)
#     nombre = models.CharField(verbose_name=u'Nombre', max_length=255)
#     tituloobtenido = models.ForeignKey(TituloObtenido, blank=True, null=True, on_delete=models.CASCADE)
#
#     def __str__(self):
#         return u'%s' % self.nombre
#
#     class Meta:
#         verbose_name_plural = u"Itinerarios"
#         ordering = ['nombre']
#         unique_together = ('malla', 'nombre',)
#
#     def save(self, *args, **kwargs):
#         self.nombre = null_to_text(self.nombre)
#         super(Itinerario, self).save(*args, **kwargs)
#

class AsignaturaMalla(ModeloBase):
    malla = models.ForeignKey(Malla, verbose_name=u'Malla', on_delete=models.CASCADE)
    # itinerario = models.ForeignKey(Itinerario, blank=True, null=True, verbose_name=u'Itinerario', on_delete=models.CASCADE)
    asignatura = models.ForeignKey(Asignatura, verbose_name=u'Asignatura malla', on_delete=models.CASCADE)
    tipomateria = models.ForeignKey(TipoMateria, verbose_name=u'Tipo de materia', blank=True, null=True, on_delete=models.CASCADE)
    campoformacion = models.ForeignKey(CampoFormacion, verbose_name=u'Campo formacion', blank=True, null=True, on_delete=models.CASCADE)
    areaconocimiento = models.ForeignKey(AreaConocimiento, verbose_name=u'Area de conocimiento', blank=True, null=True, on_delete=models.CASCADE)
    nivelmalla = models.ForeignKey(NivelMalla, verbose_name=u"Nivel de Malla", on_delete=models.CASCADE)
    ejeformativo = models.ForeignKey(EjeFormativo, verbose_name=u"Eje Formativo", on_delete=models.CASCADE)
    horas = models.FloatField(default=0, verbose_name=u'Horas')
    horasdocencia = models.FloatField(default=0, verbose_name=u'Horas docencia')
    horascolaborativas = models.FloatField(default=0, verbose_name=u'Horas colaborativas')
    horasasistidas = models.FloatField(default=0, verbose_name=u'Horas asistidas')
    horasorganizacionaprendizaje = models.FloatField(default=0, verbose_name=u'Horas Organizacion aprendizaje')
    horasautonomas = models.FloatField(default=0, verbose_name=u'Horas autonomas')
    horaspracticas = models.FloatField(default=0, verbose_name=u'Horas practicas')
    totalhorasaprendizajecontactodocente = models.FloatField(default=0, verbose_name=u"Total de horas de aprendizaje en contrato con el docente")
    totalhorasaprendizajepracticoexperimental = models.FloatField(default=0, verbose_name=u"Total de horas de aprendizaje práctico-experimental")
    totalhorasaprendizajeautonomo = models.FloatField(default=0, verbose_name=u"Total de horas del aprendizaje autónomo")
    horassemanales = models.FloatField(default=0, verbose_name=u'Horas Semanales')
    creditos = models.FloatField(default=0, verbose_name=u'créditos')
    costo = models.FloatField(default=0, verbose_name=u'Costo')
    sinasistencia = models.BooleanField(default=False, verbose_name=u'Sin asistencia')
    validacreditos = models.BooleanField(default=True, verbose_name=u'Valida para créditos')
    validapromedio = models.BooleanField(default=True, verbose_name=u'Valida para promedio')
    practicas = models.BooleanField(default=False, verbose_name=u'Practicas en materia')
    codigopracticas = models.CharField(verbose_name=u'Código practicas', blank=True, null=True, max_length=15)
    obligatoria = models.BooleanField(default=True, verbose_name=u'Debe tomar materia')
    matriculacion = models.BooleanField(default=True, verbose_name=u'Matriculación')
    titulacion = models.BooleanField(default=False, verbose_name=u'Para titulación')
    internado = models.BooleanField(default=False, verbose_name=u'Internado')
    externado = models.BooleanField(default=False, verbose_name=u'Externado')
    cantidadmatriculas = models.IntegerField(default=0, verbose_name=u'Cantidad Matriculas')
    identificacion = models.CharField(default='', max_length=30, verbose_name=u'Identificación')
    competencia = models.TextField(verbose_name=u'Competencia')

    def __str__(self):
        return u'%s - [%s] - %s' % (self.asignatura.nombre, self.malla, self.nivelmalla)

    class Meta:
        verbose_name_plural = u"Asignaturas de mallas"
        ordering = ['asignatura']
        unique_together = ('malla', 'asignatura')

    def nombrecorto(self):
        return self.asignatura.nombre + ((" - [" + self.tipomateria.nombre[0:1] + "]") if self.tipomateria else '')

    def tiene_syllabus_aprobados(self):
        return self.silaboasignaturamalla_set.filter(habilitado=True).exists()

    def tiene_syllabus_pendiente(self):
        return self.silaboasignaturamalla_set.filter(habilitado=False).exists()

    def cantidad_syllabus_aprobados(self):
        return self.silaboasignaturamalla_set.filter(habilitado=True).count()

    def syllabus_actual(self):
        if self.tiene_syllabus_aprobados():
            return self.silaboasignaturamalla_set.filter(habilitado=True).order_by('-fecha')[0]
        return None

    def cantidad_predecesoras(self):
        return self.asignaturamallapredecesora_set.count()

    def tiene_predecesoras(self):
        return AsignaturaMallaPredecesora.objects.filter(predecesora=self).exists()

    def lista_predecesoras(self):
        return self.asignaturamallapredecesora_set.all()

    def cantidad_matriculas_asignatura(self, inscripcion):
        return inscripcion.historicorecordacademico_set.filter(asignatura=self.asignatura).count()

    def puede_modificarse(self):
        if self.materia_set.exists():
            return False
        elif self.historicorecordacademico_set.exists():
            return False
        elif self.pasantia_set.exists():
            return False
        return True

    def nivel_maximo_estudiantes(self):
        return Inscripcion.objects.filter(inscripcionmalla__malla=self.malla, inscripcionnivel__nivel__id__gt=self.nivelmalla.id).exists()

    def es_itinerario(self):
        return None

    def save(self, *args, **kwargs):
        self.identificacion = null_to_text(self.identificacion)
        self.competencia = null_to_text(self.competencia)
        super(AsignaturaMalla, self).save(*args, **kwargs)


class AsignaturaMallaPredecesora(ModeloBase):
    asignaturamalla = models.ForeignKey(AsignaturaMalla, verbose_name=u'Asignatura malla', on_delete=models.CASCADE)
    predecesora = models.ForeignKey(AsignaturaMalla, related_name='predecesora', verbose_name=u'Predecesora', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.predecesora.asignatura.nombre

    class Meta:
        verbose_name_plural = u"Precedencias de asignatura de malla"
        unique_together = ('asignaturamalla', 'predecesora',)

    def save(self, *args, **kwargs):
        super(AsignaturaMallaPredecesora, self).save(*args, **kwargs)

class Coordinacion(ModeloBase):
    sede = models.ForeignKey(Sede, verbose_name=u'Sede', on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    nombreingles = models.CharField(default='', max_length=200, verbose_name=u'Nombre Ingles')
    alias = models.CharField(default='', max_length=50, blank=True, verbose_name=u'Alias')
    carrera = models.ManyToManyField(Carrera, verbose_name=u'Carreras', blank=True)
    estado = models.BooleanField(default=True, verbose_name=u"Estado")
    activadopracticacomunitaria = models.BooleanField(default=True, verbose_name=u"Estado")
    fondocarnetapp = models.FileField(upload_to='fondocarnetapp', blank=True, null=True, verbose_name=u'Fondo carnet')
    logo = models.FileField(upload_to='logo', blank=True, null=True, verbose_name=u'Logo')
    backgroundapp = models.FileField(upload_to='backgroundapp', blank=True, null=True, verbose_name=u'Backgroundapp')
    colortextosobrecolor = models.CharField(default='', max_length=100, blank=True, verbose_name=u'Colortextosobrecolor')

    def __str__(self):
        return u'%s - %s' % (self.nombre, self.sede.nombre[0])

    class Meta:
        verbose_name_plural = u"Coordinaciones de carreras"
        ordering = ['sede', 'nombre']
        unique_together = ('sede', 'nombre',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Coordinacion.objects.filter(Q(nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.nombre + " - " + self.sede.nombre[0] + ' - ' + str(self.id)

    def niveles(self, periodo):
        return Nivel.objects.filter(periodo=periodo, nivellibrecoordinacion__coordinacion=self)

    def cantidad_facturas_dia(self):
        return Factura.objects.filter(fecha=datetime.now().date(), pagos__rubro__inscripcion__coordinacion=self).distinct().count()

    def total_pagos_dia(self):
        return null_to_numeric(Pago.objects.filter(fecha=datetime.now().date(), rubro__inscripcion__coordinacion=self, valido=True).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def total_pagos_fecha(self, fecha):
        return null_to_numeric(Pago.objects.filter(fecha=fecha, rubro__inscripcion__coordinacion=self, valido=True).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def cantidad_facturas_rango_fechas(self, inicio, fin):
        return Factura.objects.filter(fecha__gte=inicio, fecha__lte=fin, pagos__rubro__inscripcion__coordinacion=self).distinct().count()

    def total_pagos_rango_fechas(self, inicio, fin):
        return null_to_numeric(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, rubro__inscripcion=self, valido=True).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def total_pagos_por_fechas(self, inicio, fin):
        return null_to_numeric(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, valido=True).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def cantidad_facturas_por_fechas(self, inicio, fin):
        return Factura.objects.filter(fecha__gte=inicio, fecha__lte=fin).distinct().count()

    def porciento_cantidad_facturas(self, inicio, fin):
        if self.cantidad_facturas_por_fechas(inicio, fin):
            return null_to_numeric((self.cantidad_facturas_rango_fechas(inicio, fin) / float(self.cantidad_facturas_por_fechas(inicio, fin))) * 100.0, 2)
        return 0

    def porciento_valor_pagos(self, inicio, fin):
        if self.total_pagos_por_fechas(inicio, fin):
            return null_to_numeric((self.total_pagos_rango_fechas(inicio, fin) / float(self.total_pagos_por_fechas(inicio, fin))) * 100.0, 2)
        return 0

    def valor_deudores_activos_30dias(self):
        hoy = datetime.now().date()
        fechavence = (datetime.now() - timedelta(days=30)).date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lte=hoy, fechavence__gte=fechavence, inscripcion__coordinacion=self).aggregate(valor=Sum('saldo'))['valor'], 2)

    def valor_apagar_activos_30dias(self):
        hoy = datetime.now().date()
        fechavence = (datetime.now() + timedelta(days=30)).date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__gt=hoy, fechavence__lte=fechavence, inscripcion__coordinacion=self).aggregate(valor=Sum('saldo'))['valor'], 2)

    def valor_deudores_activos_31_90dias(self):
        hoy = (datetime.now() - timedelta(days=31)).date()
        fechavence = (datetime.now() - timedelta(days=90)).date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lte=hoy, fechavence__gte=fechavence, inscripcion__coordinacion=self).aggregate(valor=Sum('saldo'))['valor'], 2)

    def valor_apagar_activos_31_90dias(self):
        hoy = (datetime.now() + timedelta(days=31)).date()
        fechavence = (datetime.now() + timedelta(days=90)).date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__gte=hoy, fechavence__lte=fechavence, inscripcion__coordinacion=self).aggregate(valor=Sum('saldo'))['valor'], 2)

    def valor_deudores_activos_mas_90dias(self):
        hoy = datetime.now().date() - timedelta(days=91)
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy, inscripcion__coordinacion=self).aggregate(valor=Sum('saldo'))['valor'], 2)

    def valor_apagar_activos_mas_90dias(self):
        hoy = (datetime.now() + timedelta(days=91)).date()
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__gte=hoy, inscripcion__coordinacion=self).aggregate(valor=Sum('saldo'))['valor'], 2)

    def valor_deudas_activos_total(self):
        return self.valor_deudores_activos_total() + self.valor_apagar_activos_total()

    def valor_apagar_activos_total(self):
        return self.valor_apagar_activos_30dias() + self.valor_apagar_activos_31_90dias() + self.valor_apagar_activos_mas_90dias()

    def cantidad_total_apagar(self):
        return Inscripcion.objects.filter(rubro__fechavence__gt=datetime.now().date(), rubro__cancelado=False, retirocarrera=None, carrera__in=self.carrera.all(), sede=self.sede).distinct().count()

    def valor_deudores_activos_total(self):
        return self.valor_deudores_activos_30dias() + self.valor_deudores_activos_31_90dias() + self.valor_deudores_activos_mas_90dias()

    def cantidad_total_deudores(self):
        return Inscripcion.objects.filter(rubro__fechavence__lt=datetime.now().date(), retirocarrera=None, carrera__in=self.carrera.all(), sede=self.sede).distinct().count()

    def cantidad_matriculados_periodo(self, periodo):
        return Matricula.objects.filter(nivel__nivellibrecoordinacion__coordinacion=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados(self, periodo):
        return Matricula.objects.filter(nivel__nivellibrecoordinacion__coordinacion=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados_mujeres(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__sexo_id=SEXO_FEMENINO, nivel__nivellibrecoordinacion__coordinacion=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados_hombres(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__sexo_id=SEXO_MASCULINO, nivel__nivellibrecoordinacion__coordinacion=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados_beca(self, periodo):
        return Matricula.objects.filter(becado=True, inscripcion__persona__sexo_id=SEXO_MASCULINO, nivel__nivellibrecoordinacion__coordinacion=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def porciento_matriculados_beca(self, periodo):
        if self.cantidad_matriculados(periodo):
            return null_to_numeric((self.cantidad_matriculados_beca(periodo) / float(self.cantidad_matriculados(periodo))) * 100.0, 2)
        return 0

    def cantidad_matriculados_discapacidad(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__perfilinscripcion__tienediscapacidad=True, nivel__nivellibrecoordinacion__coordinacion=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def porciento_matriculados_discapacidad(self, periodo):
        if self.cantidad_matriculados(periodo):
            return null_to_numeric((self.cantidad_matriculados_discapacidad(periodo) / float(self.cantidad_matriculados(periodo))) * 100.0, 2)
        return 0

    def cantidad_matriculados_provincia(self, provincia, periodo):
        return Matricula.objects.filter(inscripcion__persona__provincia=provincia, nivel__nivellibrecoordinacion__coordinacion=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados_canton(self, canton, periodo):
        return Matricula.objects.filter(inscripcion__persona__canton=canton, nivel__nivellibrecoordinacion__coordinacion=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_niveles(self):
        return Nivel.objects.filter(nivellibrecoordinacion__coordinacion=self).distinct().count()

    def tiene_niveles(self):
        return Nivel.objects.filter(nivellibrecoordinacion__coordinacion=self).exists()

    def cantidad_docentes(self):
        return self.profesor_set.count()

    def tiene_docentes(self):
        return self.profesor_set.exists()

    def responsable(self):
        if self.responsablecoordinacion_set.all().exists():
            return self.responsablecoordinacion_set.all()[0]
        return None

    def director(self):
        if self.directorcoordinacion_set.all().exists():
            return self.directorcoordinacion_set.all()[0]
        return None

    def responsabledirectorpracticas(self):
        if self.directorcoordinacionpracticas_set.all().exists():
            return self.directorcoordinacionpracticas_set.all()[0]
        return None

    def responsable_carrera(self, carrera, modalidad):
        if self.coordinadorcarrera_set.filter(carrera=carrera, modalidad=modalidad).exists():
            return self.coordinadorcarrera_set.filter(carrera=carrera, modalidad=modalidad)[0]
        return None

    def responsable_investigador_carrera(self, carrera):
        if self.coordinadorinvestigadorcarrera_set.filter(carrera=carrera).exists():
            return self.coordinadorinvestigadorcarrera_set.filter(carrera=carrera)[0]
        return None

    def mis_carreras(self):
        return self.carrera.all()

    def mis_carreras_periodo(self, periodo):
        return self.carrera.filter(Q(malla__asignaturamalla__materia__nivel__periodo=periodo)).distinct()

    def mis_secretarias(self):
        return SecretariaCoordinacion.objects.filter(coordinacion=self).distinct()

    def carreras_activas(self):
        return self.carrera.filter(activa=True)

    def matriculados_menor_30(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__nacimiento__gt=years_ago(31, datetime.now()), nivel__nivellibrecoordinacion__coordinacion=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def matriculados_31_40(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__nacimiento__lte=years_ago(31, datetime.now()), inscripcion__persona__nacimiento__gt=years_ago(41, datetime.now()), nivel__nivellibrecoordinacion__coordinacion=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def matriculados_41_50(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__nacimiento__lte=years_ago(41, datetime.now()), inscripcion__persona__nacimiento__gt=years_ago(51, datetime.now()), nivel__nivellibrecoordinacion__coordinacion=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def matriculados_51_60(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__nacimiento__lte=years_ago(51, datetime.now()), inscripcion__persona__nacimiento__gt=years_ago(61, datetime.now()), nivel__nivellibrecoordinacion__coordinacion=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def matriculados_mayor_61(self, periodo):
        return Matricula.objects.filter(inscripcion__persona__nacimiento__lte=years_ago(61, datetime.now()), nivel__nivellibrecoordinacion__coordinacion=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def promedio_estudiantes_docencia(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, proceso__periodo=periodo).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_autoevaluacion_docencia(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=2, proceso__periodo=periodo).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_par_docencia(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=3, proceso__periodo=periodo).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_directivo_docencia(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=4, proceso__periodo=periodo).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_general_docencia(self, periodo):
        return null_to_numeric((self.promedio_estudiantes_docencia(periodo) + self.promedio_autoevaluacion_docencia(periodo) + self.promedio_par_docencia(periodo) + self.promedio_directivo_docencia(periodo)) / 4.0, 1)

    def promedio_estudiantes_investigacion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, proceso__periodo=periodo).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_autoevaluacion_investigacion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=2, proceso__periodo=periodo).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_par_investigacion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=3, proceso__periodo=periodo).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_directivo_investigacion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=4, proceso__periodo=periodo).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_general_investigacion(self, periodo):
        return null_to_numeric((self.promedio_estudiantes_investigacion(periodo) + self.promedio_autoevaluacion_investigacion(periodo) + self.promedio_par_investigacion(periodo) + self.promedio_directivo_investigacion(periodo)) / 4.0, 1)

    def promedio_estudiantes_gestion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, proceso__periodo=periodo).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_autoevaluacion_gestion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=2, proceso__periodo=periodo).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_par_gestion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=3, proceso__periodo=periodo).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_directivo_gestion(self, periodo):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=4, proceso__periodo=periodo).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_general_gestion(self, periodo):
        return null_to_numeric((self.promedio_estudiantes_gestion(periodo) + self.promedio_autoevaluacion_gestion(periodo) + self.promedio_par_gestion(periodo) + self.promedio_directivo_gestion(periodo)) / 4.0, 1)

    def niveles_malla(self, carrera, periodo):
        return NivelMalla.objects.filter(nivel__nivellibrecoordinacion__coordinacion=self, nivel__carrera=carrera, nivel__periodo=periodo).distinct().order_by('id')

    def mis_paralelos(self, carrera, periodo):
        return Nivel.objects.filter(nivellibrecoordinacion__coordinacion=self, periodo=periodo, carrera=carrera).distinct().order_by('nivelmalla', 'paralelo')

    def cantidad_matriculados_carrera_coordinacion_periodo(self, carrera, periodo):
        return Matricula.objects.filter(nivel__nivellibrecoordinacion__coordinacion=self, nivel__periodo=periodo, nivel__carrera=carrera).exclude(retiromatricula__isnull=False).distinct().count()

    def cantidad_matriculados_coordinacion_periodo(self, periodo):
        return Matricula.objects.filter(nivel__nivellibrecoordinacion__coordinacion=self, nivel__periodo=periodo).exclude(retiromatricula__isnull=False).distinct().count()

    def total_matriculados(self, periodo):
        return Matricula.objects.filter(nivel__periodo=periodo, nivel__nivellibrecoordinacion__coordinacion=self).exclude(retiromatricula__isnull=False).distinct().count()

    def total_inscritos(self):
        return Inscripcion.objects.filter(sede=self.sede, carrera__in=self.carrera.all()).distinct().count()

    def cantidad_personas_acceso(self, carrera):
        return PerfilAccesoUsuario.objects.filter(carrera=carrera, coordinacion=self).distinct().count()

    def cantidad_personas_acceso_modalidad(self, carrera, modalidad):
        return PerfilAccesoUsuario.objects.filter(carrera=carrera, modalidad=modalidad, coordinacion=self).distinct().count()

    def total_inscritos_periodo(self, periodo):
        return Inscripcion.objects.filter(periodo=periodo, sede=self.sede, carrera__in=self.carrera.all()).distinct().count()

    def total_matriculados_retirados_periodo(self, periodo):
        return Matricula.objects.filter(nivel__periodo=periodo, retiromatricula__isnull=False, nivel__nivellibrecoordinacion__coordinacion=self).distinct().count()

    def total_matriculados_regular_periodo(self, periodo):
        return Matricula.objects.filter(nivel__periodo=periodo, nivel__nivellibrecoordinacion__coordinacion=self, tipomatricula__id=MATRICULA_REGULAR_ID).exclude(retiromatricula__isnull=False).distinct().count()

    def total_matriculados_extraordinarias_periodo(self, periodo):
        return Matricula.objects.filter(nivel__periodo=periodo, nivel__nivellibrecoordinacion__coordinacion=self, tipomatricula__id=MATRICULA_EXTRAORDINARIA_ID).exclude(retiromatricula__isnull=False).distinct().count()

    def total_matriculados_especiales_periodo(self, periodo):
        return Matricula.objects.filter(nivel__periodo=periodo, nivel__nivellibrecoordinacion__coordinacion=self, tipomatricula__id=MATRICULA_ESPECIAL_ID).exclude(retiromatricula__isnull=False).distinct().count()

    def profesores_periodo(self, periodo):
        return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__coordinacion=self, profesordistributivohoras__periodo=periodo).distinct()

    def total_profesores_periodo(self, periodo):
        return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__coordinacion=self, profesordistributivohoras__periodo=periodo).distinct().count()

    def total_docentes_tiempo_completo_periodo(self, periodo):
        return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__coordinacion=self, profesordistributivohoras__periodo=periodo, profesordistributivohoras__dedicacion__id=TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID).distinct().count()

    def total_docentes_medio_tiempo_periodo(self, periodo):
        return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__coordinacion=self, profesordistributivohoras__periodo=periodo, profesordistributivohoras__dedicacion__id=TIEMPO_DEDICACION_MEDIO_TIEMPO_ID).distinct().count()

    def total_docentes_tiempo_parcial_periodo(self, periodo):
        return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__coordinacion=self, profesordistributivohoras__periodo=periodo, profesordistributivohoras__dedicacion__id=TIEMPO_DEDICACION_PARCIAL_ID).distinct().count()

    def total_docentes_tecnico_docente_periodo(self, periodo):
        return Profesor.objects.filter(profesordistributivohoras__horas__gt=0, profesordistributivohoras__coordinacion=self, profesordistributivohoras__periodo=periodo, profesordistributivohoras__dedicacion__id=TIEMPO_DEDICACION_TECNICO_DOCENTE_ID).distinct().count()

    def cantidad_materias_periodo(self, periodo):
        return ProfesorMateria.objects.filter(profesor__profesordistributivohoras__coordinacion=self, principal=True, materia__nivel__periodo=periodo).count()

    def cantidad_materias_planificadas_periodo(self, periodo):
        return ProfesorMateria.objects.filter(profesor__profesordistributivohoras__coordinacion=self, materia__nivel__periodo=periodo, principal=True, materia__planificacionmateria__aprobado=True).count()

    def cantidad_materias_sinplanificadas_periodo(self, periodo):
        return self.cantidad_materias_periodo(periodo) - self.cantidad_materias_planificadas_periodo(periodo)

    def puede_eliminarse(self):
        if self.inscripcion_set.exists():
            return False
        if self.nivellibrecoordinacion_set.exists():
            return False
        if self.cursoescuelacomplementaria_set.exists():
            return False
        return True

    def puede_eliminar_carrera(self, carrera):
        if self.inscripcion_set.filter(carrera=carrera).exists():
            return False
        if Materia.objects.filter(carrera=carrera, nivel__nivellibrecoordinacion__coordinacion=self).exists():
            return False
        return True

    def cantidad_materias_periodo_estadisticas(self, periodo):
        return ProfesorMateria.objects.filter(principal=True, horassemanales__gt=0, profesor__profesordistributivohoras__horas__gt=0, profesor__profesordistributivohoras__coordinacion=self, profesor__profesordistributivohoras__periodo=periodo, materia__nivel__periodo=periodo).count()

    def cantidad_materias_planificadas_periodo_estadisticas(self, periodo):
        return ProfesorMateria.objects.filter(principal=True, horassemanales__gt=0, profesor__profesordistributivohoras__horas__gt=0, profesor__profesordistributivohoras__coordinacion=self, materia__planificacionmateria__aprobado=True, profesor__profesordistributivohoras__periodo=periodo, materia__nivel__periodo=periodo).count()

    def cantidad_materias_sinplanificadas_periodo_estadisticas(self, periodo):
        return ProfesorMateria.objects.filter(principal=True, horassemanales__gt=0, profesor__profesordistributivohoras__horas__gt=0, profesor__profesordistributivohoras__coordinacion=self, materia__planificacionmateria__aprobado=False, profesor__profesordistributivohoras__periodo=periodo, materia__nivel__periodo=periodo).count()

    def download_fondocarnet_app(self):
        if self.fondocarnetapp:
            return u'%s/%s' % (APP_DOMAIN, self.fondocarnetapp.url)
        return ''

    def download_logo_app(self):
        if self.logo:
            return u'%s/%s' % (APP_DOMAIN, self.logo.url)
        return ''

    def download_background_app(self):
        if self.backgroundapp:
            return u'%s/%s' % (APP_DOMAIN, self.backgroundapp.url)
        return ''

    def valor_colortextosobrecolor(self):
        return validarRGB(self.colortextosobrecolor)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.nombreingles = null_to_text(self.nombreingles)
        self.alias = null_to_text(self.alias)
        super(Coordinacion, self).save(*args, **kwargs)







class ResponsableCoordinacion(ModeloBase):
    coordinacion = models.ForeignKey(Coordinacion, verbose_name=u'Coordinación', on_delete=models.CASCADE)
    persona = models.ForeignKey(Persona, verbose_name=u'Persona', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name_plural = u"Responsables de coordinación"
        unique_together = ('coordinacion',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("ResponsableCoordinacion.objects.filter(Q(persona__nombre1__contains='%s') | Q(persona__nombre2__contains='%s') | Q(persona__apellido1__contains='%s') | Q(persona__apellido2__contains='%s') | Q(id=id_search('%s')))" % (q, q, q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return (self.persona.cedula if self.persona.cedula else self.persona.pasaporte) + " - " + self.persona.nombre_completo_inverso() + ' - ' + str(self.id)

    def mis_carreras(self):
        return self.coordinacion.carrera.all()

class DirectorCoordinacion(ModeloBase):
    coordinacion = models.ForeignKey(Coordinacion, verbose_name=u'Coordinación', on_delete=models.CASCADE)
    persona = models.ForeignKey(Persona, verbose_name=u'Persona', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name_plural = u"Directores de coordinación"
        unique_together = ('coordinacion',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("DirectorCoordinacion.objects.filter(Q(persona__nombre1__contains='%s') | Q(persona__nombre2__contains='%s') | Q(persona__apellido1__contains='%s') | Q(persona__apellido2__contains='%s') | Q(id=id_search('%s')))" % (q, q, q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return (self.persona.cedula if self.persona.cedula else self.persona.pasaporte) + " - " + self.persona.nombre_completo_inverso() + ' - ' + str(self.id)

    def mis_carreras(self):
        return self.coordinacion.carrera.all()



class SecretariaCoordinacion(ModeloBase):
    coordinacion = models.ForeignKey(Coordinacion, verbose_name=u'Coordinación', on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, blank=True, null=True, verbose_name=u'Carrera', on_delete=models.CASCADE)
    modalidad = models.ForeignKey(Modalidad, blank=True, null=True, verbose_name=u'Modalidad', on_delete=models.CASCADE)
    persona = models.ForeignKey(Persona, verbose_name=u'Persona', on_delete=models.CASCADE)
    principal = models.BooleanField(default=False, verbose_name=u"Principal")

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name_plural = u"Secretarias de coordinación"
        ordering = ['coordinacion', 'persona', 'carrera', 'modalidad']
        unique_together = ('coordinacion', 'persona', 'carrera', 'modalidad')

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("SecretariaCoordinacion.objects.filter(Q(persona__nombre1__contains='%s') | Q(persona__nombre2__contains='%s') | Q(persona__apellido1__contains='%s') | Q(persona__apellido2__contains='%s') | Q(id=id_search('%s')))" % (q, q, q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return (self.persona.cedula if self.persona.cedula else self.persona.pasaporte) + " - " + self.persona.nombre_completo_inverso() + ' - ' + str(self.id)

    def mis_carreras(self):
        return self.coordinacion.carrera.all()





class Administrativo(ModeloBase):
    persona = models.ForeignKey(Persona, verbose_name=u"Persona", on_delete=models.CASCADE)
    sede = models.ForeignKey(Sede, blank=True, null=True, verbose_name=u'Sede', on_delete=models.CASCADE)
    activo = models.BooleanField(default=True, verbose_name=u"Activo")

    def __str__(self):
        return u'%s' % self.persona

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        if len(q.split(' ')) == 2:
            qq = q.split(' ')
            return eval(("Administrativo.objects.filter(persona__apellido1__contains='%s', persona__apellido2__contains='%s')" % (qq[0], qq[1])) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))
        return eval(("Administrativo.objects.filter(Q(persona__nombre1__contains='%s') | Q(persona__nombre2__contains='%s') | Q(persona__apellido1__contains='%s') | Q(persona__apellido2__contains='%s') | Q(persona__cedula__contains='%s') | Q(id=id_search('%s')))" % (q, q, q, q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return (self.persona.cedula if self.persona.cedula else self.persona.pasaporte) + " - " + self.persona.nombre_completo() + ' - ' + str(self.id)

    class Meta:
        verbose_name_plural = u"Administrativos"
        ordering = ['persona']
        unique_together = ('persona',)

    def tiene_escalados(self):
        return SolicitudEscalda.objects.filter(solicitudsoporte__estado=3, activo=True, personaescalada=self).exists()


class TipoCurso(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u"Nombre")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de cursos"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoCurso, self).save(*args, **kwargs)


class CursoPersona(ModeloBase):
    persona = models.ForeignKey(Persona, verbose_name=u"Persona", on_delete=models.CASCADE)
    tipocurso = models.ForeignKey(TipoCurso, verbose_name=u"Tipo Curso", on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=200, verbose_name=u"Nombre del curso")
    educacionsuperior = models.BooleanField(default=True, verbose_name=u"Educacion superior")
    institucion = models.ForeignKey(TecnologicoUniversidad, blank=True, null=True, verbose_name=u"Institución", on_delete=models.CASCADE)
    institucionformacion = models.CharField(default='', max_length=200, verbose_name=u"Institucion Formacion")
    apolloinstitucion = models.BooleanField(default=False, verbose_name=u"Apoyo de la Institución")
    fecha_inicio = models.DateField(verbose_name=u'Fecha inicio')
    fecha_fin = models.DateField(verbose_name=u'Fecha fin')
    horas = models.FloatField(default=0, verbose_name=u'Horas')
    archivo = models.FileField(upload_to='cursopersona/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    verificado = models.BooleanField(default=False, verbose_name=u'Verificado')

    def __str__(self):
        return u'%s %s %s' % (self.tipocurso, self.nombre, self.institucion)

    class Meta:
        verbose_name_plural = u"Cursos de realizados"
        ordering = ['-fecha_inicio']
        unique_together = ('persona', 'tipocurso', 'nombre', 'fecha_inicio', 'fecha_fin',)

    def extra_delete(self):
        if self.verificado:
            return [False, False]
        return [True, False]

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.institucionformacion = null_to_text(self.institucionformacion)
        super(CursoPersona, self).save(*args, **kwargs)



class Turno(ModeloBase):
    sesion = models.ForeignKey(Sesion, verbose_name=u'Sesion', on_delete=models.CASCADE)
    turno = models.IntegerField(default=0, verbose_name=u'Turno')
    comienza = models.TimeField(verbose_name=u'Comienza')
    termina = models.TimeField(verbose_name=u'Termina')
    horas = models.FloatField(default=0, verbose_name=u'Horas')

    class Meta:
        verbose_name_plural = u"Turnos de clases"
        ordering = ['comienza', 'termina']
        unique_together = ('sesion', 'comienza', 'termina',)

    def __str__(self):
        return u'Turno %s [%s a %s]' % (str(self.turno), self.comienza.strftime("%I:%M %p"), self.termina.strftime("%I:%M %p"))

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Turno.objects.filter(Q(sesion__nombre__icontains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.nombre_horario() + ' - ' + str(self.id)

    def nombre_horario(self):
        return self.comienza.strftime("%I:%M %p") + ' a ' + self.termina.strftime("%I:%M %p")

    def horario_profesor_actual(self, dia, profesor):
        return self.clase_set.filter(dia=dia, activo=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date(), materia__profesormateria__profesor=profesor, materia__cerrado=False, materia__profesormateria__principal=True).distinct().order_by('inicio')

    def horario_practicas_profesor_actual(self, dia, profesor):
        return self.clasepractica_set.filter(dia=dia, activo=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date(), grupo__profesormateriapracticas__profesor=profesor, grupo__materia__cerrado=False, grupo__profesormateriapracticas__principal=True).distinct().order_by('inicio')

    def horario_profesor_pasado(self, dia, profesor):
        return self.clase_set.filter(dia=dia, activo=True, inicio__lte=datetime.now().date(), fin__lt=datetime.now().date(), materia__profesormateria__profesor=profesor, materia__cerrado=False, materia__profesormateria__principal=True).distinct().order_by('inicio')

    def horario_practicas_profesor_pasado(self, dia, profesor):
        return self.clasepractica_set.filter(dia=dia, activo=True, inicio__lte=datetime.now().date(), fin__lt=datetime.now().date(), grupo__profesormateriapracticas__profesor=profesor, grupo__materia__cerrado=False, grupo__profesormateriapracticas__principal=True).distinct().order_by('inicio')

    def horario_profesor_periodo(self, dia, profesor, periodo):
        return self.clase_set.filter(dia=dia, activo=True, materia__nivel__periodo=periodo, materia__profesormateria__profesor=profesor, materia__profesormateria__principal=True).distinct().order_by('inicio')

    def horario_alumno_actual(self, dia, matricula):
        return self.clase_set.filter(dia=dia, activo=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date(), materia__materiaasignada__matricula=matricula).distinct().order_by('inicio')

    def horario_matricula_actual(self, dia, matricula):
        return self.clase_set.filter(dia=dia, activo=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date(), materia__materiaasignada__matricula=matricula).distinct().order_by('inicio')

    # def horario_profesor_futuro(self, dia, profesor):
    #     return self.clase_set.filter(dia=dia, activo=True, inicio__gt=datetime.now().date(), materia__profesormateria__profesor=profesor, materia__profesormateria__principal=True).distinct().order_by('inicio')
    #
    # def horario_practicas_profesor_futuro(self, dia, profesor):
    #     return self.clasepractica_set.filter(dia=dia, activo=True, inicio__gt=datetime.now().date(), grupo__profesormateriapracticas__profesor=profesor, grupo__profesormateriapracticas__principal=True).distinct().order_by('inicio')

    def horario_profesor_futuro(self, dia, profesor):
        return self.clase_set.filter(dia=dia, activo=True, inicio__gt=datetime.now().date(), materia__profesormateria__profesor=profesor, materia__profesormateria__principal=True,materia__nivel__periodo__visualiza=True).distinct().order_by('inicio')

    def horario_practicas_profesor_futuro(self, dia, profesor):
        return self.clasepractica_set.filter(dia=dia, activo=True, inicio__gt=datetime.now().date(), grupo__profesormateriapracticas__profesor=profesor, grupo__profesormateriapracticas__principal=True,grupo__materia__nivel__periodo__visualiza=True).distinct().order_by('inicio')

    def horario_alumno_futuro(self, dia, matricula):
        return self.clase_set.filter(dia=dia, activo=True, inicio__gt=datetime.now().date(), materia__materiaasignada__matricula=matricula).distinct().order_by('inicio')

    def horario_matricula_futuro(self, dia, matricula):
        return self.clase_set.filter(dia=dia, activo=True, inicio__gt=datetime.now().date(), materia__materiaasignada__matricula=matricula).distinct().order_by('inicio')

    def duracion(self):
        s = timedelta(hours=self.comienza.hour, minutes=self.comienza.minute)
        e = timedelta(hours=self.termina.hour, minutes=self.termina.minute)
        return e - s




class Nivel(ModeloBase):
    periodo = models.ForeignKey(Periodo, verbose_name=u"Período", on_delete=models.CASCADE)
    sede = models.ForeignKey(Sede, null=True, blank=True, on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, null=True, blank=True, on_delete=models.CASCADE)
    modalidad = models.ForeignKey(Modalidad, verbose_name=u'Modalidad', on_delete=models.CASCADE)
    sesion = models.ForeignKey(Sesion, verbose_name=u'Sesión', on_delete=models.CASCADE)
    malla = models.ForeignKey(Malla, null=True, blank=True, verbose_name=u"Malla", on_delete=models.CASCADE)
    nivelmalla = models.ForeignKey(NivelMalla, null=True, blank=True, verbose_name=u"Nivel", on_delete=models.CASCADE)
    paralelo = models.CharField(default='', max_length=30, verbose_name=u"Paralelo")
    inicio = models.DateField(verbose_name=u"Fecha inicio")
    fin = models.DateField(verbose_name=u"Fecha fin")
    cerrado = models.BooleanField(default=False, verbose_name=u"Cerrado")
    fechafinclases = models.DateField(null=True, blank=True, verbose_name=u"fecha fin de clases")
    fechacierre = models.DateField(null=True, blank=True, verbose_name=u"fecha de cierre")
    fechatopematricula = models.DateField(verbose_name=u'Fecha Tope Matricula Ordinaria')
    fechatopematriculaex = models.DateField(verbose_name=u'Fecha Tope Matricula Extraordinaria')
    fechatopematriculaes = models.DateField(verbose_name=u'Fecha Tope Matricula Especial')
    capacidadmatricula = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Capacidad de matriculas')
    nivelgrado = models.BooleanField(default=False, verbose_name=u'Nivel de grado')
    aplicabecas = models.BooleanField(default=True, verbose_name=u'Aplican becas')
    distributivoaprobado = models.BooleanField(default=False, verbose_name=u'Distributivo aprobado')
    responsableaprobacion = models.ForeignKey(Persona, null=True, blank=True, verbose_name=u"Responsable aprobación", on_delete=models.CASCADE)
    fechaprobacion = models.DateField(null=True, blank=True, verbose_name=u"Fecha aprobación")
    mensaje = models.TextField(default='', blank=True, verbose_name=u'Mensaje')
    aprobadofinanciero = models.BooleanField(default=False, verbose_name=u'"Distributivo aprobado')
    responsableaprobacionfinanciero = models.ForeignKey(Persona, null=True, blank=True, verbose_name=u'Responsable aprobación financiero', on_delete=models.CASCADE, related_name='responsable_aprobacion_financiero_set')
    fechaprobacionfinanciero = models.DateField(null=True, blank=True, verbose_name=u'Fecha aprobación financiera')

    def __str__(self):
        return u'%s - %s - %s' % (self.paralelo, (self.coordinacion() if self.coordinacion() else ""), self.inicio.strftime('%d-%m-%Y'))

    class Meta:
        verbose_name_plural = u"Niveles"
        unique_together = ('periodo', 'sede', 'carrera', 'modalidad', 'sesion', 'malla', 'nivelmalla', 'paralelo',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Nivel.objects.filter(Q(carrera__nombre__contains='%s') |Q(sesion__nombre__contains='%s') |Q(nivelmalla__nombre__contains='%s') |Q(paralelo__contains='%s') |Q(periodo__nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q, q, q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.paralelo + " - " + ((self.nivelmalla.nombre + " - " + self.carrera.alias + " - ") if self.carrera else "") + ((self.coordinacion().alias + " - ") if self.coordinacion() else "") + self.periodo.nombre + " - " + str(self.id)

    def nombre_simple(self):
        return self.paralelo

    def clases_activas_horario(self, dia, turno, materia=None):
        if materia:
            return Clase.objects.filter(activo=True, dia=dia, turno=turno, materia=materia).order_by('inicio')
        else:
            return Clase.objects.filter(activo=True, dia=dia, materia__nivel=self, turno=turno).order_by('inicio', 'materia__asignatura')

    def clases_practicas_activas_horario(self, dia, turno, grupo=None):
        if grupo:
            return ClasePractica.objects.filter(activo=True, dia=dia, turno=turno, grupo=grupo).order_by('inicio')
        else:
            return ClasePractica.objects.filter(activo=True, dia=dia, grupo__materia__nivel=self, turno=turno).order_by('inicio', 'grupo__materia__asignatura')

    def fuera_fecha_matricula(self):
        return datetime.now().date() > self.fechatopematricula

    def fuera_fecha_matriculaex(self):
        if self.fechatopematriculaex:
            return datetime.now().date() > self.fechatopematriculaex
        return False

    def historico(self):
        return self.fin < datetime.now().date()

    def puede_eliminarse(self):
        if self.cerrado:
            return False
        if self.materia_set.exists():
            return False
        if self.matricula_set.exists():
            return False
        return True

    def coordinacion(self, coordinacion=None):
        if self.nivellibrecoordinacion_set.all().exists():
            return self.nivellibrecoordinacion_set.all()[0].coordinacion
        elif self.carrera:
            if self.carrera:
                if Coordinacion.objects.filter(carrera__in=[self.carrera], sede=self.sede).exists():
                    coordinacion = Coordinacion.objects.filter(carrera__in=[self.carrera], sede=self.sede)[0]
                    nivelcoordinacion = NivelLibreCoordinacion(nivel=self,
                                                               coordinacion=coordinacion)
                    nivelcoordinacion.save()
        elif coordinacion:
            if (coordinacion.id not in [18, 19, 36]):
                if self.inicio < self.periodo.inicio:
                    self.inicio = self.periodo.inicio
                if self.fin > self.periodo.fin:
                    self.fin = self.periodo.fin
            nivelcoordinacion = NivelLibreCoordinacion(nivel=self,
                                                       coordinacion=coordinacion)
            nivelcoordinacion.save()
            return coordinacion
        return None

    def matricula_cerrada(self):
        return datetime.now().date() > self.fechatopematricula

    def matriculaextraordinaria_cerrada(self):
        return datetime.now().date() > self.fechatopematriculaex

    def matriculaespecial_cerrada(self):
        return datetime.now().date() > self.fechatopematriculaes

    def matriculaespecial_abierta(self):
        return self.fechatopematriculaes >= datetime.now().date() > self.fechatopematriculaex

    def matriculaextraordinaria_abierta(self):
        return self.fechatopematriculaex >= datetime.now().date() > self.fechatopematricula

    def matricularegular_abierta(self):
        return datetime.now().date() <= self.fechatopematricula

    def cerrar_disponible(self):
        return self.materia_set.count() == self.materia_set.filter(cerrado=True).count()

    def nombre_corto(self):
        return u'%s %s %s %s %s' % (("COSTO FIJO " if self.nivelgrado else ""), (self.nivelmalla if self.nivelmalla else ""), self.paralelo, (self.carrera if self.carrera else ""), (self.sede if self.sede else ""))

    def nombre_extra_corto(self):
        return u'%s %s' % ((self.nivelmalla if self.nivelmalla else ""), self.paralelo)

    def cantidad_matriculados(self):
        return self.matricula_set.all().count()

    def mat_materias(self):
        return self.materia_set.all().count()

    def total_cuotas(self):
        return self.pagonivel_set.filter(tipo__gte=1, tipo__lte=10).count()

    def inicio_repr(self):
        return self.inicio.strftime('%d-%m-%Y')

    def fin_repr(self):
        return self.fin.strftime('%d-%m-%Y')

    def matriculados(self):
        return self.matricula_set.all().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombre1', 'inscripcion__persona__nombre2')

    def materias(self):
        return self.materia_set.all().order_by('asignatura__nombre', 'inicio')

    def materias_con_docente(self):
        return self.materia_set.filter(profesormateria__isnull=False).order_by('asignatura__nombre', 'inicio')

    def materias_modelo(self, cronograma):
        return self.materia_set.filter(modeloevaluativo=cronograma.modelo, nivel__periodo=cronograma.periodo, usaperiodocalificaciones=True).distinct().order_by('asignatura__nombre', 'inicio')

    def extension(self):
        if self.nivelextension_set.exists():
            return self.nivelextension_set.all()[0]
        else:
            ne = NivelExtension(nivel=self,
                                modificarcupo=True,
                                modificarhorario=True)
            ne.save()
            return ne

    def tiene_matriculados(self):
        return self.matricula_set.exists()

    def total_matriculados(self):
        return Matricula.objects.filter(nivel=self).exclude(retiromatricula__isnull=False).count()

    def total_materias_abiertas(self):
        return Materia.objects.filter(nivel=self, cerrado=False).count()

    def total_materias_cerradas(self):
        return Materia.objects.filter(nivel=self, cerrado=True).count()

    def total_matriculados_cerrados(self):
        return Matricula.objects.filter(nivel=self, cerrada=True).exclude(retiromatricula__isnull=False).count()

    def total_matriculados_pendientes(self):
        return self.total_matriculados() - self.total_matriculados_cerrados()

    def total_matriculados_sin_retiros(self):
        return Matricula.objects.filter(nivel=self, retiromatricula__isnull=True).count()

    def total_matriculados_regular(self):
        return Matricula.objects.filter(nivel=self, tipomatricula__id=MATRICULA_REGULAR_ID).exclude(retiromatricula__isnull=False).count()

    def total_matriculados_extraordinarias(self):
        return Matricula.objects.filter(nivel=self, tipomatricula__id=MATRICULA_EXTRAORDINARIA_ID).exclude(retiromatricula__isnull=False).count()

    def total_matriculados_especiales(self):
        return Matricula.objects.filter(nivel=self, tipomatricula__id=MATRICULA_ESPECIAL_ID).exclude(retiromatricula__isnull=False).count()

    def mis_carreras(self):
        return Carrera.objects.filter(malla__asignaturamalla__materia__nivel=self).distinct()

    def modelos_evaluativos(self):
        return ModeloEvaluativo.objects.filter(materia__nivel=self).distinct()

    def total_docentes_completo(self):
        return Profesor.objects.filter(profesormateria__materia__nivel=self, profesordistributivohoras__horas__gt=0, profesordistributivohoras__dedicacion__id=TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID).distinct().count()

    def total_docentes_medio_tiempo(self):
        return Profesor.objects.filter(profesormateria__materia__nivel=self, profesordistributivohoras__horas__gt=0, profesordistributivohoras__dedicacion__id=TIEMPO_DEDICACION_MEDIO_TIEMPO_ID).distinct().count()

    def total_docentes_parcial(self):
        return Profesor.objects.filter(profesormateria__materia__nivel=self, profesordistributivohoras__horas__gt=0, profesordistributivohoras__dedicacion__id=TIEMPO_DEDICACION_PARCIAL_ID).distinct().count()

    def total_docentes_tecnico_docente(self):
        return Profesor.objects.filter(profesormateria__materia__nivel=self, profesordistributivohoras__horas__gt=0, profesordistributivohoras__dedicacion__id=TIEMPO_DEDICACION_TECNICO_DOCENTE_ID).distinct().count()

    def total_profesores(self):
        return Profesor.objects.filter(profesormateria__materia__nivel=self, profesordistributivohoras__horas__gt=0).distinct().count()

    def save(self, *args, **kwargs):
        self.paralelo = null_to_text(self.paralelo)
        self.mensaje = null_to_text(self.mensaje)
        if self.inicio >= self.fin:
            self.inicio = self.periodo.inicio
            self.fin = self.periodo.fin
        if self.fechatopematricula > self.fin:
            self.fechatopematricula = self.fin
        if self.fechatopematriculaex > self.fin:
            self.fechatopematriculaex = self.fin
        super(Nivel, self).save(*args, **kwargs)


class TipoInscripcion(ModeloBase):
    nombre = models.CharField(verbose_name=u'Nombre', max_length=100)
    alias = models.CharField(default='', max_length=50, blank=True, verbose_name=u'Alias')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de inscripciones"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.alias = null_to_text(self.alias)
        super(TipoInscripcion, self).save(*args, **kwargs)



class TipoSolicitudSecretariaDocente(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    valor = models.FloatField(default=0, verbose_name=u'Valor')
    descripcion = models.TextField(default="", verbose_name=u'Descripción')
    costo_unico = models.BooleanField(default=True, verbose_name=u'Costo Unico')
    costo_base = models.FloatField(default=0, verbose_name=u'Costo Base')
    grupos = models.ManyToManyField(Group, verbose_name=u'Grupos Responsables')
    gratismatricula = models.IntegerField(default=0, verbose_name=u'Cantidad gratuitas')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')
    validamatricula = models.BooleanField(default=True, verbose_name=u'Valida matricula')
    respuesta = models.TextField(default="", verbose_name=u'Respuesta automática')
    plantilla = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Plantilla')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de solicitudes a secretaria docente"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def tiene_costo(self):
        return self.valor > 0 or self.costo_base > 0

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.descripcion = null_to_text(self.descripcion)
        self.respuesta = null_to_text(self.respuesta)
        super(TipoSolicitudSecretariaDocente, self).save(*args, **kwargs)


class Inscripcion(ModeloBase):
    persona = models.ForeignKey(Persona, verbose_name=u'Persona', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha de inscripción')
    hora = models.TimeField(verbose_name=u'Hora de inscripción')
    sede = models.ForeignKey(Sede, blank=True, null=True, verbose_name=u'Sede', on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, verbose_name=u'Carrera', on_delete=models.CASCADE)
    modalidad = models.ForeignKey(Modalidad, verbose_name=u'Modalidad', on_delete=models.CASCADE)
    sesion = models.ForeignKey(Sesion, verbose_name=u'Sesión', on_delete=models.CASCADE)
    coordinacion = models.ForeignKey(Coordinacion, blank=True, null=True, verbose_name=u'Coordinación', on_delete=models.CASCADE)
    fechainicioestadotitulacion = models.DateField(verbose_name=u'Fecha fin malla', blank=True, null=True)
    fechalimiteprorrogauno = models.DateField(verbose_name=u'Fecha límite prorroga 1', blank=True, null=True)
    fechalimiteprorrogados = models.DateField(verbose_name=u'Fecha límite prorroga dos', blank=True, null=True)
    fechalimiteactualizacionc = models.DateField(verbose_name=u'Fecha límite actualización conocimiento', blank=True, null=True)
    periodo = models.ForeignKey(Periodo, blank=True, null=True, verbose_name=u'Período de inscripción', on_delete=models.CASCADE)
    nivel = models.ForeignKey(Nivel, blank=True, null=True, verbose_name=u'Período de inscripción', on_delete=models.CASCADE)
    identificador = models.CharField(default='', blank=True, max_length=200, verbose_name=u'Indentificador')
    cumplimiento = models.BooleanField(default=False, verbose_name=u'Cumplimiento')
    fechainicioconvalidacion = models.DateField(blank=True, null=True, verbose_name=u'Fecha inicio de convalidación')
    promediogeneral = models.FloatField(default=0, verbose_name=u'Promedio general')
    promediomalla = models.FloatField(default=0, verbose_name=u'Promedio malla')
    promedionivelacion = models.FloatField(default=0, verbose_name=u'Promedio nivelación')
    nivelhomologado = models.ForeignKey(NivelMalla, blank=True, null=True, verbose_name=u'Nivel homologado', on_delete=models.CASCADE)
    condicionado = models.BooleanField(default=True, verbose_name=u"Condicionado")
    activo = models.BooleanField(default=True, verbose_name=u"Activo")
    fechainiciocarrera = models.DateField(blank=True, null=True, verbose_name=u'Fecha inicio de carrera')
    fechafincarrera = models.DateField(blank=True, null=True, verbose_name=u'Fecha inicio de carrera')
    observaciones = models.TextField(default='', verbose_name=u'Observaciones')
    habilitadomatricula = models.BooleanField(default=False, verbose_name=u"Habilitado para matricula")
    permitematriculacondeuda = models.BooleanField(default=False, verbose_name=u"Habilitado para matricula con deuda")
    habilitadoexamen = models.BooleanField(default=False, verbose_name=u"Habilitado para examen")
    proyectodevida = models.TextField(default='', verbose_name=u'Observaciones')
    tipoinscripcion = models.ForeignKey(TipoInscripcion, blank=True, null=True, verbose_name=u'Tipo de Inscripción', on_delete=models.CASCADE)
    linktesis = models.TextField(default='', verbose_name=u'Link tesis')
    cumpleperfil = models.BooleanField(default=False, verbose_name=u"Cumple Perfil")
    nivelado = models.BooleanField(default=False, verbose_name=u"Nivelado")
    estadoinscripcion = models.IntegerField(choices=ESTADO_INSCRIPCION, default=1, verbose_name=u'Estado Inscripción')
    certificacionidioma = models.IntegerField(choices=CERTIFICACION_IDIOMA, default=2, verbose_name=u'Certificación Idioma')
    redisenio = models.BooleanField(default=False, verbose_name=u'Rediseño')
    orientacion = models.BooleanField(default=False, verbose_name=u'Proceso de Orientación Profesional')
    examenubicacionidiomas = models.BooleanField(default=False, verbose_name=u'Examen de Ubicación Inglés')
    numerooficio = models.CharField(default='', max_length=300, blank=True, null=True, verbose_name=u'Número de oficio')
    habilitadocambiomodalidad = models.BooleanField(default=False, verbose_name=u"Habilitado para cambio de modalidad")
    notatitulacion = models.FloatField(default=0, verbose_name=u'Nota Titulación')
    enviadobecapromocional = models.BooleanField(default=False, verbose_name=u'Enviar notificación beca promocional')
    alumnoantiguo = models.BooleanField(default=False, verbose_name=u'Alumno Antiguo')
    mocs = models.BooleanField(default=False, verbose_name=u'Mocs')
    personainscribio = models.ForeignKey(Persona, null=True, related_name='persona_inscribe', verbose_name=u'Persona quien Inscribe', on_delete=models.CASCADE)
    otrofuentefinanciacion = models.CharField(default='', max_length=300, blank=True, null=True, verbose_name=u'Otra fuente de financiacion')
    reconocimientointerno = models.BooleanField(default=False, verbose_name=u'Reconocimiento Interno')
    activocertificadonoadeudar = models.BooleanField(default=False,blank=True,null=True, verbose_name=u"Activa secretaria para certificar no deuda")
    certificadoaprobadosecretaria = models.BooleanField(default=False,blank=True,null=True, verbose_name=u"Aprobado por secretaria para certificado de no adeudar")
    personasecretaria = models.IntegerField(default=0,blank=True,null=True,verbose_name=u"Persona de secretaria que aprbo no adeuda")
    fechasecretaria = models.DateTimeField(blank=True,null=True,verbose_name=u"fecha de secretaria que aprbo no adeuda")
    certificadoaprobadocolecturia = models.BooleanField(default=False,blank=True,null=True, verbose_name=u"Aprobado por colecturia para certificado de no adeudar")
    personacolecturia = models.IntegerField(default=0, blank = True, null = True, verbose_name = u"Persona de colecturia que aprbo no adeuda")
    fechacolecturia = models.DateTimeField(blank=True, null=True, verbose_name=u"fecha de colecturia que aprbo no adeuda")
    certificadoaprobadobiblioteca = models.BooleanField(default=False,blank=True,null=True, verbose_name=u"Aprobado por biblioteca para certificado de no adeudar")
    personabiblioteca = models.IntegerField(default=0, blank = True, null = True, verbose_name = u"Persona de biblioteca que aprbo no adeuda")
    fechabiblioteca = models.DateTimeField(blank=True, null=True, verbose_name=u"fecha de biblioteca que aprbo no adeuda")
    puede_solicitar_noadeudar = models.BooleanField(default=False, blank=True, null=True)
    pre_retirocarrera = models.BooleanField(default=False, verbose_name=u'Pre retiro')
    padre = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Inscripción padre', help_text='Otra inscripción que actúa como padre (p.ej., reinscripción, cambio, etc.)')

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name_plural = u"Inscripciones de alumnos"
        ordering = ["persona", '-fecha']

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        if len(q.split(' ')) == 2:
            qq = q.split(' ')
            return eval(("Inscripcion.objects.filter(persona__apellido1__contains='%s', persona__apellido2__contains='%s')" % (qq[0], qq[1])) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))
        return eval(("Inscripcion.objects.filter(Q(persona__nombre1__contains='%s') | Q(persona__nombre2__contains='%s') | Q(persona__apellido1__contains='%s') | Q(persona__apellido2__contains='%s') | Q(persona__cedula__contains='%s') | Q(persona__pasaporte__contains='%s') | Q(id=id_search('%s')))" % (q, q, q, q, q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return (self.persona.cedula if self.persona.cedula else self.persona.pasaporte) + " - " + self.persona.nombre_completo_inverso() + " - (" + self.carrera.alias + (" - " + self.coordinacion.alias if self.coordinacion else '') + " - " + self.modalidad.nombre + " - " + self.sesion.nombre + ")" + ' - ' + str(self.mi_malla().inicio.year) + ' -' + str(self.id)

    def flexbox_reprpago(self):
        return (self.persona.cedula if self.persona.cedula else self.persona.pasaporte) + " - " + self.persona.nombre_completo_inverso() + " - (" + self.carrera.nombre + (" - " + self.coordinacion.alias if self.coordinacion else '') + " - " + self.modalidad.nombre + ")" + ' - ' + str(self.mi_malla().inicio.year)

    def flexbox_repr_malla(self):
        return "Id Malla: " + str(self.mi_malla().id) + " - " + "Id Inscripcion: " + str(self.id) + " - " + self.persona.nombre_completo_inverso() + " - (" + self.carrera.alias + (" - " + self.coordinacion.alias if self.coordinacion else '') + " - " + self.modalidad.nombre + ")" + ' - ' + str(self.mi_malla().inicio.year)

    def tiene_tiporeconocimiento(self):
        return self.tiporeconocimientoinscripcion_set.all().exists()

    def flexbox_alias(self):
        return [self.persona.nombre_completo_inverso()]

    def perfil_usuario(self):
        return self.perfilusuario_set.all()[0]

    def existe_en_malla(self, asignatura):
        return self.mi_malla().asignaturamalla_set.filter(asignatura=asignatura).exists()



    def es_regular(self):
        return self.tipoinscripcion_id == TIPO_INSCRIPCION_REGULAR

    def es_gratuidad_total(self):
        return self.tipogratuidad_id == TIPO_GRATUIDAD_TOTAL

    def es_gratuidad_parcial(self):
        return self.tipogratuidad_id == TIPO_GRATUIDAD_PARCIAL

    def es_gratuidad_ninguna(self):
        return self.tipogratuidad_id == TIPO_GRATUIDAD_NINGUNA

    def mis_flag(self):
        if self.inscripcionflags_set.exists():
            return self.inscripcionflags_set.all()[0]
        else:
            flag = InscripcionFlags(inscripcion=self)
            flag.save()
            return flag

    def retiro_carrera(self):
        return self.retirocarrera_set.exists()

    def tiene_coordinacion(self):
        return Coordinacion.objects.filter(carrera=self.carrera, sede=self.sede).exists()

    def registro_examen_complexivo(self):
        return MatriculaCursoEscuelaComplementaria.objects.filter(inscripcion=self, curso__examencomplexivo=True).exists()

    def mi_coordinacion(self):
        if self.tiene_coordinacion():
            return Coordinacion.objects.filter(carrera=self.carrera, sede=self.sede)[0]
        return None

    def esta_nivelado(self):
        if self.matriculacursoescuelacomplementaria_set.filter(curso__nivelacion=True).exists():
            return True
        if self.matricula_set.filter(nivelmalla__id=NIVEL_MALLA_CERO).exists():
            return True
        return False

    def tiene_homologaciones(self):
        return self.recordacademico_set.filter(Q(homologada=True) | Q(convalidacion=True)).exists()

    def tiene_matriculas(self):
        return self.matricula_set.exists()

    def tiene_proyecto_activo(self):
        return self.preproyectogrado_set.filter(Q(estado__in=[1, 2]) | Q(proyectogrado__in=[1, 2, 4])).exists()

    def tiene_asignaturas_reprobadas(self):
        return self.recordacademico_set.filter(aprobada=False).exists()

    def numero_reprobadas_x_nivel_anterior(self, nivel):
        if self.recordacademico_set.filter(aprobada=False).exists():
            return self.recordacademico_set.filter(aprobada=False, asignaturamalla__nivelmalla__id=nivel-1).count()
        return 0

    def numero_reprobadas_precedencia_x_nivel_anterior(self, nivel):
        if self.recordacademico_set.filter(aprobada=False).exists():
            return self.recordacademico_set.filter(aprobada=False, asignaturamalla__nivelmalla__id=nivel-1, asignaturamalla__asignaturamallapredecesora__predecesora_id__isnull=False).count()
        return 0

    def cantidad_matriculas(self, asignatura):
        return self.historicorecordacademico_set.filter(asignatura=asignatura, convalidacion=False, homologada=False, noaplica=False).count()

    def puede_matricularse_seguncronograma(self, periodo):
        minivel = self.mi_nivel().nivel
        hoy = datetime.now().date()
        if periodo.periodomatriculacion_set.filter(carrera=self.carrera, nivelmalla=minivel, modalidad=self.modalidad).exists():
            pornivel = periodo.periodomatriculacion_set.filter(carrera=self.carrera, nivelmalla=minivel, modalidad=self.modalidad)[0]
            return pornivel.fecha_inicio <= hoy <= pornivel.fecha_fin
        elif periodo.periodomatriculacion_set.filter(carrera=self.carrera, modalidad=self.modalidad, nivelmalla__isnull=True).exists():
            pornivel = periodo.periodomatriculacion_set.filter(carrera=self.carrera, modalidad=self.modalidad, nivelmalla__isnull=True)[0]
            return pornivel.fecha_inicio <= hoy <= pornivel.fecha_fin
        elif periodo.periodomatriculacion_set.filter(carrera=self.carrera, modalidad__isnull=True, nivelmalla__isnull=True).exists():
            pornivel = periodo.periodomatriculacion_set.filter(carrera=self.carrera, modalidad__isnull=True, nivelmalla__isnull=True)[0]
            return pornivel.fecha_inicio <= hoy <= pornivel.fecha_fin
        else:
            if periodo.periodomatriculacion_set.exists():
                return False
        return True

    def puede_prematricularse_seguncronograma(self, periodo):
        minivel = self.mi_nivel().nivel
        hoy = datetime.now().date()
        if periodo.periodoprematriculacion_set.filter(carrera=self.carrera, nivelmalla=minivel, modalidad=self.modalidad).exists():
            pornivel = periodo.periodoprematriculacion_set.filter(carrera=self.carrera, nivelmalla=minivel, modalidad=self.modalidad)[0]
            return pornivel.fecha_inicio <= hoy <= pornivel.fecha_fin
        elif periodo.periodoprematriculacion_set.filter(carrera=self.carrera, modalidad=self.modalidad).exists():
            pornivel = periodo.periodoprematriculacion_set.filter(carrera=self.carrera, modalidad=self.modalidad)[0]
            return pornivel.fecha_inicio <= hoy <= pornivel.fecha_fin
        elif periodo.periodoprematriculacion_set.filter(carrera=self.carrera).exists():
            pornivel = periodo.periodoprematriculacion_set.filter(carrera=self.carrera)[0]
            return pornivel.fecha_inicio <= hoy <= pornivel.fecha_fin
        else:
            if periodo.periodoprematriculacion_set.exists():
                return False
        return True

    def tiene_nota_credito(self):
        return self.notacredito_set.filter(saldo__gt=0).exists()

    def tiene_recibo_caja(self):
        return self.recibocajainstitucion_set.filter(saldo__gt=0).exists()

    def pasantias(self):
        return self.pasantia_set.all()

    def talleres(self):
        return self.participanteactividadextracurricular_set.filter(actividad__cerrado=True)

    def horas_talleres(self):
        horas = 0
        if self.participanteactividadextracurricular_set.filter(actividad__cerrado=True).exists():
            for actividad in self.participanteactividadextracurricular_set.filter(actividad__cerrado=True):
                if actividad.nota >= actividad.actividad.nota_aprobar and actividad.asistencia >= actividad.actividad.asistencia_aprobar:
                    horas += actividad.actividad.horas
        return horas

    def materia_sinasistencia(self, asignatura):
        malla = self.mi_malla()

        if malla.asignaturamalla_set.filter(asignatura=asignatura, sinasistencia=True).exists():
            return True

        return False

    def materia_verificahorario(self, asignatura):
        malla = self.mi_malla()

        if malla.asignaturamalla_set.filter( asignatura=asignatura, obligatoria=True).exists():
            return True

        return False

    def asignatura_en_asignaturamalla(self, asignatura):
        malla = self.mi_malla()
        if malla.asignaturamalla_set.filter(asignatura=asignatura).exists():
            return malla.asignaturamalla_set.filter(asignatura=asignatura)[0]
        return None



    def promedio_talleres(self):
        return null_to_numeric(self.participanteactividadextracurricular_set.filter(actividad__cerrado=True).aggregate(valor=Avg('nota'))['valor'], 2)

    def vcc(self):
        return self.participanteproyectovinculacion_set.filter()

    def tiene_actividad_extra(self):
        if self.pasantias() or self.talleres() or self.vcc() or self.practicas():
            return True
        return False

    def tiene_entrevistas_pendientes(self):
        hoy = datetime.now()
        if self.aplicanteoferta_set.filter(fechaentrevista__lt=hoy.date()):
            return True
        elif self.aplicanteoferta_set.filter(fechaentrevista=hoy.date(), horaentrevista__lt=hoy.time()):
            return True
        return False

    def tiene_ofertas_disponibles(self):
        if OfertaLaboral.objects.filter(cerrada=False, fin__gte=datetime.now().date(), carreras=None).exists():
            if OfertaLaboral.objects.filter(cerrada=False, fin__gte=datetime.now().date(), carreras=None, sexo=None).exists():
                if AplicanteOferta.objects.filter(inscripcion=self).exists():
                    ofertas = OfertaLaboral.objects.filter(cerrada=False, fin__gte=datetime.now().date(), carreras=None, sexo=None)
                    for oferta in ofertas:
                        if not AplicanteOferta.objects.filter(inscripcion=self, oferta=oferta).exists():
                            return True
                    return False
                return True
            elif OfertaLaboral.objects.filter(cerrada=False, fin__gte=datetime.now().date(), carreras=None, sexo=self.persona.sexo).exists():
                if AplicanteOferta.objects.filter(inscripcion=self).exists():
                    ofertas = OfertaLaboral.objects.filter(cerrada=False, fin__gte=datetime.now().date(), carreras=None, sexo=self.persona.sexo)
                    for oferta in ofertas:
                        if not AplicanteOferta.objects.filter(inscripcion=self, oferta=oferta).exists():
                            return True
                    return False
                return True
        elif OfertaLaboral.objects.filter(cerrada=False, fin__gte=datetime.now().date(), carreras__in=[self.carrera]).exists():
            if OfertaLaboral.objects.filter(cerrada=False, fin__gte=datetime.now().date(), carreras__in=[self.carrera], sexo=None).exists():
                if AplicanteOferta.objects.filter(inscripcion=self).exists():
                    ofertas = OfertaLaboral.objects.filter(cerrada=False, fin__gte=datetime.now().date(), carreras__in=[self.carrera], sexo=None)
                    for oferta in ofertas:
                        if not AplicanteOferta.objects.filter(inscripcion=self, oferta=oferta).exists():
                            return True
                    return False
                return True
            elif OfertaLaboral.objects.filter(cerrada=False, fin__gte=datetime.now().date(), carreras__in=[self.carrera], sexo=self.persona.sexo).exists():
                if AplicanteOferta.objects.filter(inscripcion=self).exists():
                    ofertas = OfertaLaboral.objects.filter(cerrada=False, fin__gte=datetime.now().date(), carreras__in=[self.carrera], sexo=self.persona.sexo)
                    for oferta in ofertas:
                        if not AplicanteOferta.objects.filter(inscripcion=self, oferta=oferta).exists():
                            return True
                    return False
                return True
        return False

    def tiene_tercera_matricula(self):
        for record in self.recordacademico_set.filter(aprobada=False, asignaturamalla__isnull=False):
            if record.historicorecordacademico_set.count() == 2:
                return True
        return False

    def tercera_matricula(self):
        for record in self.recordacademico_set.filter(aprobada=False, asignaturamalla__isnull=False):
            if record.historicorecordacademico_set.count() == 2:
                return record.asignatura

    def tiene_perdida_carrera(self):
        for record in self.recordacademico_set.filter(aprobada=False, asignaturamalla__isnull=False):
            if record.historicorecordacademico_set.filter(aprobada=False).count() >= CANTIDAD_MATRICULAS_MAXIMAS:
                return True
        return False

    def clientefacturacion(self, request):
        if self.clientefacturainscripcion_set.exists():
            clientefactura = self.clientefacturainscripcion_set.all()[0].clientefactura
        else:
            if not ClienteFactura.objects.filter(clientefacturainscripcion__inscripcion__persona=self.persona).exists():
                clientefactura = ClienteFactura(identificacion=self.persona.identificacion(),
                                                tipo=self.persona.tipo_identificacion_comprobante(),
                                                nombre=self.persona.nombre_completo(),
                                                direccion=self.persona.mi_direccion(),
                                                telefono=self.persona.mi_telefono(),
                                                email=self.persona.mi_email())
                clientefactura.save(request)
            else:
                clientefactura = ClienteFactura.objects.filter(clientefacturainscripcion__inscripcion__persona=self.persona)[0]
            clientefacturacion = ClienteFacturaInscripcion(inscripcion=self,
                                                           clientefactura=clientefactura)
            clientefacturacion.save(request)
        return clientefactura

    def aprobadaasignatura(self, asignaturamalla):
        if self.recordacademico_set.filter(asignatura=asignaturamalla.asignatura).exists():
            return self.recordacademico_set.filter(asignatura=asignaturamalla.asignatura)[0]
        return None

    def preguntas_inscripcion(self):
        if self.tiene_preguntas_inscripcion():
            return self.preguntasinscripcion_set.all()[0]
        else:
            preguntas = PreguntasInscripcion(inscripcion=self)
            preguntas.save()
            return preguntas

    def tiene_preguntas_inscripcion(self):
        return self.preguntasinscripcion_set.exists()

    def cantidad_pasantias(self):
        return self.pasantia_set.count()

    def cantidad_pasantias_aprobadas(self):
        return self.pasantia_set.filter(estado=2).count()

    def horas_pasantias(self):
        return null_to_numeric(self.pasantia_set.filter(estado=2).aggregate(valor=Sum('horas'))['valor'], 1)

    def notas_pasantias(self):
        return null_to_numeric(self.pasantia_set.filter(estado=2).aggregate(valor=Sum('calificacion'))['valor'], 2)

    def materias(self, periodo):
        return MateriaAsignada.objects.filter(materia__nivel__periodo=periodo, matricula__inscripcion=self)

    def creditos(self):
        return null_to_numeric(self.recordacademico_set.filter(validacreditos=True).aggregate(valor=Sum('creditos'))['valor'], 4)

    def generar_rubro_homologacion(self, malla, periodo):
        from django.shortcuts import get_object_or_404
        hoy = datetime.now().date()
        valor = 0
        if self.periodo:
            costo_periodo = self.carrera.precio_modulo_inscripcion(periodo, self.sede, self.modalidad, malla)
            documentos = self.documentos_entregados()
            if documentos.homologar and costo_periodo.preciohomologacion:
                valor = costo_periodo.preciohomologacion
            if valor > 0:
                if documentos.homologar:
                    tiporubro = get_object_or_404(TipoOtroRubro, pk=4)
                    # Buscar si ya existe un Rubro con el mismo periodo y tipo
                    rubro_existente = self.rubro_set.filter(rubrootro__tipo=tiporubro,nombre__icontains="ESTUDIO DE HOMOLOGACION").first()
                    if rubro_existente:
                        # Si ya existe, no se crea uno nuevo, y puedes manejar este caso como prefieras
                        print("El rubro ya existe.")
                    else:
                        rubro = Rubro(fecha=hoy,
                                      valor=valor,
                                      inscripcion=self,
                                      iva_id=TIPO_IVA_0_ID,
                                      fechavence=hoy,
                                      periodo=periodo)
                        rubro.save()
                        tiporubro = TipoOtroRubro.objects.get(pk=4)
                        rubrootro = RubroOtro(rubro=rubro,
                                              tipo=tiporubro)
                        rubrootro.save()
                        rubro.actulizar_nombre('ESTUDIO DE HOMOLOGACION')

    def generar_rubro_inscripcion(self, malla):
        hoy = datetime.now().date()
        valor = 0
        valorinduccion = 0
        valorreingreso = 0
        if self.periodo:
            costo_periodo = self.carrera.precio_modulo_inscripcion(self.periodo, self.sede, self.modalidad, malla)
            costo_conveniohomologacion = None
            documentos = self.documentos_entregados()
            if costo_periodo.precioinscripcion:
                if documentos.conveniohomologacion:
                    valor = costo_conveniohomologacion.costoconvenio if costo_conveniohomologacion else 0
                else:
                    valor = costo_periodo.precioinscripcion
            if costo_periodo.precioinduccion and not documentos.homologar:
                valorinduccion = costo_periodo.precioinduccion
            if documentos.reingreso and costo_periodo.precioreingreso:
                valorreingreso = costo_periodo.precioreingreso
            if self.persona.redmaestros and costo_periodo.precioredmaestros:
                valor = costo_periodo.precioredmaestros
            if self.orientacion:
                tipo = TipoSolicitudSecretariaDocente.objects.get(pk=56)
                rubro = Rubro(fecha=hoy,
                              valor=tipo.valor,
                              inscripcion=self,
                              iva_id=TIPO_IVA_0_ID,
                              fechavence=self.fecha)
                rubro.save()
                rubroinscripcion = RubroInscripcion(rubro=rubro,
                                                    inscripcion=self)
                rubroinscripcion.save()
                rubro.actulizar_nombre('DERECHO ORIENTACIÓN PROFESIONAL')
            if not self.carrera.posgrado:
                if valor > 0:
                    rubro = Rubro(fecha=hoy,
                                  valor=valor,
                                  inscripcion=self,
                                  iva_id=TIPO_IVA_0_ID,
                                  fechavence=self.fecha)
                    rubro.save()
                    rubroinscripcion = RubroInscripcion(rubro=rubro,
                                                        inscripcion=self)
                    rubroinscripcion.save()
                    rubro.actulizar_nombre()
            else:
                if not documentos.reingreso:
                    if valor > 0:
                        rubro = Rubro(fecha=hoy,
                                      valor=valor,
                                      inscripcion=self,
                                      iva_id=TIPO_IVA_0_ID,
                                      fechavence=self.fecha)
                        rubro.save()
                        rubroinscripcion = RubroInscripcion(rubro=rubro,
                                                            inscripcion=self)
                        rubroinscripcion.save()
                        rubro.actulizar_nombre('INSCRIPCION PROGRAMA')
                else:
                    if valor > 0:
                        tipo = TipoSolicitudSecretariaDocente.objects.get(pk=51)
                        rubro = Rubro(fecha=hoy,
                                      valor=tipo.valor,
                                      inscripcion=self,
                                      iva_id=TIPO_IVA_0_ID,
                                      fechavence=self.fecha,
                                      periodo=self.periodo)
                        rubro.save()
                        tiporubro = TipoOtroRubro.objects.get(pk=22)
                        rubrootro = RubroOtro(rubro=rubro,
                                              tipo=tiporubro)
                        rubrootro.save()
                        rubro.actulizar_nombre('HOMOLOGACION POSGRADOS')
            if valorinduccion > 0:
                rubro = Rubro(fecha=hoy,
                              valor=valorinduccion,
                              inscripcion=self,
                              iva_id=TIPO_IVA_0_ID,
                              fechavence=self.fecha,
                              periodo=self.periodo)
                rubro.save()
                tiporubro = TipoOtroRubro.objects.get(pk=21)
                rubrootro = RubroOtro(rubro=rubro,
                                      tipo=tiporubro)
                rubrootro.save()
                rubro.actulizar_nombre('CURSO INDUCCION')
            if valorreingreso > 0:
                rubro = Rubro(fecha=hoy,
                              valor=valorreingreso,
                              inscripcion=self,
                              iva_id=TIPO_IVA_0_ID,
                              fechavence=self.fecha,
                              periodo=self.periodo)
                rubro.save()
                tiporubro = TipoOtroRubro.objects.get(pk=22)
                rubrootro = RubroOtro(rubro=rubro,
                                      tipo=tiporubro)
                rubrootro.save()
                rubro.actulizar_nombre('VALOR DE REINGRESO')

    def generar_rubro_parqueadero(self, sede, periodo, modalidad, tipovehiculo, tiempo, posgrado, duplicado, solicitud):
        valor = 0
        nombrevehiculo = 'AUTO' if int(tipovehiculo) == 1 else 'MOTO'
        nombretiempo = 'MENSUAL' if tiempo.id == 1 else 'SEMESTRAL'
        hoy = datetime.now().date()
        if self.matriculado_periodo(periodo):
            if posgrado:
                if PreciosServicioParqueadero.objects.filter(sede=sede, periodo=periodo, modalidad=modalidad, tipovehiculo=tipovehiculo, tiempo=tiempo, posgrado=posgrado).exists():
                    costo_servicioparqueadero = PreciosServicioParqueadero.objects.filter(sede=sede, periodo=periodo, modalidad=modalidad, tipovehiculo=tipovehiculo, tiempo=tiempo, posgrado=True)[0]
                    valor = costo_servicioparqueadero.costosubtotal if duplicado == 1 else costo_servicioparqueadero.costoadicionalperdida
                else:
                    valor = 0
            else:
                if PreciosServicioParqueadero.objects.filter(sede=sede, periodo=periodo, modalidad=modalidad, tipovehiculo=tipovehiculo, tiempo=tiempo, posgrado=False).exists():
                    costo_servicioparqueadero = PreciosServicioParqueadero.objects.filter(sede=sede, periodo=periodo, modalidad=modalidad, tipovehiculo=tipovehiculo, tiempo=tiempo, posgrado=False)[0]
                    valor = costo_servicioparqueadero.costosubtotal if duplicado == 1 else costo_servicioparqueadero.costoadicionalperdida
                else:
                    valor = 0
            if valor > 0:
                rubro = Rubro(fecha=hoy,
                              valor=valor,
                              inscripcion=self,
                              iva_id=TIPO_IVA_15_ID,
                              fechavence=hoy,
                              periodo=periodo)
                rubro.save()
                tiporubro = TipoOtroRubro.objects.get(pk=24)
                rubrootro = RubroOtro(rubro=rubro,
                                      tipo=tiporubro,
                                      solicitud=solicitud)
                rubrootro.save()
                if duplicado == 1:
                    if posgrado:
                        rubro.actulizar_nombre(str(costo_servicioparqueadero.nombre) + ' POSGRADO - ' + nombrevehiculo+' - ' + nombretiempo)
                        return True
                    else:
                        rubro.actulizar_nombre(str(costo_servicioparqueadero.nombre) + ' ' + str(costo_servicioparqueadero.modalidad)+' - ' + nombrevehiculo + ' - ' + nombretiempo)
                        return True
                else:
                    rubro.actulizar_nombre('COSTO TAC ADICIONAL O PERDIDA')
                    return True
        return False

    def generar_rubro_titulacion(self, periodo):
        hoy = datetime.now().date()
        valortitulacion = 0
        if self.periodo:
            costo_periodo = self.carrera.precio_modulo_inscripcion(periodo, self.sede, self.modalidad,self.mi_malla())
            if costo_periodo.preciotitulacion:
                valortitulacion = costo_periodo.preciotitulacion
            if valortitulacion > 0:
                rubro = Rubro(fecha=hoy,
                              valor=valortitulacion,
                              inscripcion=self,
                              iva_id=TIPO_IVA_0_ID,
                              fechavence=hoy,
                              periodo=periodo)
                rubro.save()
                tiporubro = TipoOtroRubro.objects.get(pk=20)
                rubrootro = RubroOtro(rubro=rubro,
                                      tipo=tiporubro)
                rubrootro.save()
                rubro.actulizar_nombre('CURSO UNIDAD TITULACION')
                return True
            else:
                return False

    def actualizar_creditos(self):
        for historico in self.historicorecordacademico_set.all():
            creditos = historico.creditos
            horas = historico.horas
            validacreditos = historico.validacreditos
            validapromedio = historico.validapromedio
            asignatura = historico.asignatura
            am = self.asignatura_en_asignaturamalla(asignatura)

            if am:
                creditos = am.creditos
                horas = am.horas
                validacreditos = am.validacreditos
                validapromedio = am.validapromedio

            historico.asignaturamalla = am
            historico.creditos = creditos
            historico.horas = horas
            historico.validacreditos = validacreditos
            historico.validapromedio = validapromedio
            historico.save()
            historico.actualizar()

    def actualizar_niveles_records(self):
        for record in self.recordacademico_set.all():
            record.save()
            for historico in record.historicorecordacademico_set.all():
                historico.save()
        self.save()

    def promedio_pasantias(self):
        return null_to_numeric(self.pasantia_set.filter(estado=2).aggregate(valor=Avg('calificacion'))['valor'], 2)

    def promedio_vcc(self):
        return null_to_numeric(self.participanteproyectovinculacion_set.filter(proyecto__cerrado=True, estado__id=NOTA_ESTADO_APROBADO).aggregate(valor=Avg('nota'))['valor'], 2)

    def horas_vcc(self):
        return null_to_numeric(self.participanteproyectovinculacion_set.filter(cerrado=True, estado__id=NOTA_ESTADO_APROBADO).aggregate(horas=Sum('horas'))['horas'], 0)

    def promedio_ppp(self):
        return null_to_numeric(ParticipantePracticaPreProfesional.objects.filter(materiaasignada__matricula__inscripcion=self, practica__cerrado=True).aggregate(valor=Avg('nota'))['valor'], 2)

    def horas_ppp(self):
        horaspracticamateria = null_to_numeric(ParticipantePracticaPreProfesional.objects.filter(materiaasignada__matricula__inscripcion=self, practica__cerrado=True).aggregate(valor=Sum('practica__horas'))['valor'], 0)
        horaspracticapasantia = null_to_numeric(Pasantia.objects.filter(inscripcion=self, estado=2).aggregate(valor=Sum('horas'))['valor'], 0)
        return null_to_numeric(horaspracticamateria + horaspracticapasantia, 0)

    def ultima_coordinacion_matriculado(self):
        if self.matricula_set.all().exists():
            matricula = self.matricula_set.all().order_by('-nivel__fin')[0]
            return matricula.nivel.coordinacion()
        return None

    def tiene_cheque_protestado(self):
        if self.inscripcionflags_set.exists():
            return self.inscripcionflags_set.all()[0].tienechequeprotestado
        return False

    def tiene_malla(self):
        return self.inscripcionmalla_set.exists()

    def mi_malla(self, malla=None):
        if self.inscripcionmalla_set.exists():
            return self.inscripcionmalla_set.all()[0].malla
        else:
            if not malla:
                if Malla.objects.filter(carrera=self.carrera, modalidad=self.modalidad,aprobado=True).exists():
                    malla = Malla.objects.filter(carrera=self.carrera, modalidad=self.modalidad,aprobado=True).order_by('-inicio')[0]
                elif Malla.objects.filter(carrera=self.carrera, aprobado=True).exists():
                    malla = Malla.objects.filter(carrera=self.carrera, aprobado=True).order_by('-inicio')[0]
            if malla:
                im = InscripcionMalla(inscripcion=self, malla=malla)
                im.save()
            return malla


    def matriculado(self):
        return self.matricula_set.filter(cerrada=False).exists()

    def matriculado_internado(self):
        return self.matriculainternadorotativo_set.filter(cerrada=False).exists()

    def matriculado_periodo(self, periodo):
        return self.matricula_set.filter(nivel__periodo_id=periodo.id).exists()

    def tiene_matricula_internado_rotatito(self, periodo):
        return self.matriculainternadorotativo_set.filter(internado__periodo_inicio_internado_id=periodo.id).exists()

    def becado_periodo(self, periodo):
        return self.matricula_set.filter(nivel__periodo=periodo, becado=True).exists()

    def matricula(self):
        if self.matriculado():
            return self.matricula_set.filter(cerrada=False)[0]
        return None

    def ultima_matricula(self):
        if self.matricula_set.exists():
            return self.matricula_set.all().order_by('-fecha')[0]
        return None

    def ultima_matricula_sinextendido(self):
        if self.matricula_set.exists():
            return self.matricula_set.filter(nivel__periodo__extendido=False).order_by('-fecha')[0]
        return None

    def ultima_matricula_cerrada_sin_periodo_extendido(self):
        if self.matricula_set.filter(cerrada=True).exclude(nivel__periodo__extendido=True).exists():
            return self.matricula_set.filter(cerrada=True).exclude(nivel__periodo__extendido=True).order_by('-fecha')[0]
        return None

    def ultima_matricula_cerrada(self):
        if self.matricula_set.filter(cerrada=True).exists():
            return self.matricula_set.filter(cerrada=True).order_by('-fecha')[0]
        return None

    def ultima_matricula_otra_ficha(self):
        if Matricula.objects.filter(inscripcion__persona=self.persona).exclude(inscripcion=self).exists():
            return Matricula.objects.filter(inscripcion__persona=self.persona).exclude(inscripcion=self).order_by('-fecha')[0]
        return None

    def matricula_periodo(self, periodo):
        if self.matriculado_periodo(periodo):
            return self.matricula_set.filter(nivel__periodo_id=periodo.id)[0]
        return None

    def matricula_periodo_internado_rotativo(self, periodo):
        if self.tiene_matricula_internado_rotatito(periodo):
            return self.matriculainternadorotativo_set.filter(internado__periodo_inicio_internado_id=periodo.id)[0]
        return None

    def matricula_tiene_pago_minimo(self):
        if self.matriculado():
            if self.matricula_set.filter(nivel__periodo__valida_deuda=True, nivel__periodo__extendido=False).exists():
                matricula = self.matricula_set.filter(nivel__periodo__valida_deuda=True, nivel__periodo__extendido=False).order_by('-fecha')[0]
                return matricula.tienepagominimo
        return True

    def matricula_formalizada(self):
        if self.matriculado():
            if self.matricula_set.filter(nivel__periodo__valida_deuda=True, nivel__periodo__extendido=False).exists():
                matricula = self.matricula_set.filter(nivel__periodo__valida_deuda=True, nivel__periodo__extendido=False).order_by('-fecha')[0]
                return matricula.formalizada
        return True

    def ya_aprobada(self, asignatura):
        return self.recordacademico_set.filter(asignatura=asignatura, aprobada=True).exists()

    def sin_asistencia(self, asignatura):
        malla = self.mi_malla()
        if malla.asignaturamalla_set.filter(asignatura=asignatura, sinasistencia=True).exists():
            return True

    def estado_asignatura(self, asignatura):
        if self.recordacademico_set.filter(asignatura=asignatura).exists():
            if self.recordacademico_set.filter(asignatura=asignatura, aprobada=True).exists():
                return NOTA_ESTADO_APROBADO
            return NOTA_ESTADO_REPROBADO
        return 0

    def puede_tomar_materia(self, asignatura):
        mi_nivel = self.mi_nivel().nivel.id
        if self.mi_malla().asignaturamalla_set.filter( asignatura=asignatura).exists():
            asignaturamalla = self.mi_malla().asignaturamalla_set.filter( asignatura=asignatura)[0]
            if mi_nivel > 0 and asignaturamalla.nivelmalla.id > 0:

                    for precedencias in asignaturamalla.asignaturamallapredecesora_set.filter():
                        if not self.recordacademico_set.filter(asignatura=precedencias.predecesora.asignatura, aprobada=True).exists():
                            return False
                    return True
            elif mi_nivel == 0 and asignaturamalla.nivelmalla.id > 0:
                return False
            elif mi_nivel == 0 and asignaturamalla.nivelmalla.id == 0:
                return True
        else:
            pass
        return False



    def puede_tomar_materia_asignatura(self, asignatura):
        mi_nivel = self.mi_nivel().nivel.id
        if self.mi_malla().asignaturamalla_set.filter( asignatura=asignatura).exists():
            asignaturamalla = self.mi_malla().asignaturamalla_set.filter( asignatura=asignatura)[0]
            for precedencias in asignaturamalla.asignaturamallapredecesora_set.all():
                if not self.recordacademico_set.filter(asignatura=precedencias.predecesora.asignatura, aprobada=True).exists():
                    return False
            return True
        else:
            return False

    def documentos_entregados(self):
        if self.documentosdeinscripcion_set.exists():
            return self.documentosdeinscripcion_set.all()[0]
        else:
            documentos = DocumentosDeInscripcion(inscripcion=self)
            documentos.save()
            return documentos

    def solicitud_homologacion(self):
        if self.solicitudhomologacion_set.exists():
            return self.solicitudhomologacion_set.all().order_by('-periodo_homologacion__inicio')[0]
        else:
            return None

    def es_reingreso(self):
        if self.documentosdeinscripcion_set.exists():
            return self.documentosdeinscripcion_set.get().reingreso
        return False

    def actualiza_tipo_inscripcion(self):
        inscripcionnivel = self.mi_nivel()
        if inscripcionnivel.nivel.id == NIVEL_MALLA_CERO:
            self.tipoinscripcion_id = TIPO_INSCRIPCION_REGULAR
        else:
            if self.matricula_set.exists():
                matricula = self.ultima_matricula()
                self.tipoinscripcion = matricula.tipoinscripcion
            else:
                self.tipoinscripcion_id = TIPO_INSCRIPCION_REGULAR
        self.save()

    def actualiza_gratuidad(self):
        pass

    def total_pasantias(self):
        return self.pasantia_set.all().count()

    def total_materias_malla_sin_pre(self):
        total = 0
        malla = self.mi_malla()
        if not malla:
            return total
        return AsignaturaMalla.objects.filter(Q(malla=malla) & Q(nivelmalla__id__gt=NIVEL_MALLA_CERO) & Q(
            nivelmalla__id__lt=malla.nivelesregulares)).count()

    def total_materias_aprobadas_malla(self):
        return RecordAcademico.objects.filter(aprobada=True, asignaturamalla__malla=self.mi_malla()).count()

    def total_materias_aprobadas(self):
        return RecordAcademico.objects.filter(inscripcion=self, aprobada=True, validacreditos=True).count()

    def lista_materias_record_malla_nuevo(self):
        malla = self.mi_malla()
        asignaturas = RecordAcademico.objects.filter(inscripcion=self).order_by('-fecha', 'asignatura__nombre')
        return asignaturas

    def porcientocompletado(self):
        if self.total_materias_aprobadas() > 0:
            if self.total_materias_aprobadas() > self.total_materias_malla_sin_pre():
                return float(1)
            return float(self.total_materias_aprobadas()) / float(self.total_materias_malla_sin_pre())
        return 0

    def alumno_estado(self):
        return self.egresado_set.exists()

    def total_rubros(self):
        return null_to_numeric(self.rubro_set.aggregate(valor=Sum('valortotal'))['valor'], 2)

    def total_rubros_sin_notadebito(self):
        return null_to_numeric(self.rubro_set.exclude(rubronotadebito__rubro__inscripcion=self).aggregate(valor=Sum('valortotal'))['valor'], 2)

    def total_rubros_pendientes(self):
        return null_to_numeric(self.rubro_set.filter(cancelado=False).aggregate(valor=Sum('saldo'))['valor'], 2)

    def rubros_pendientes(self):
        return self.rubro_set.filter(cancelado=False).order_by('fechavence')

    def total_descuento(self):
        return null_to_numeric(DescuentoRecargoRubro.objects.filter(rubro__inscripcion=self, recargo=False).distinct().aggregate(valor=Sum('valordescuento'))['valor'], 2)

    def total_descuento_pendiente(self):
        return null_to_numeric(DescuentoRecargoRubro.objects.filter(rubro__inscripcion=self, recargo=False, rubro__cancelado=False).distinct().aggregate(valor=Sum('valordescuento'))['valor'], 2)

    def total_liquidado(self):
        return null_to_numeric(RubroLiquidado.objects.filter(rubro__inscripcion=self).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def total_pagado(self):
        return null_to_numeric(Pago.objects.filter(rubro__inscripcion=self, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def total_pagado_periodo(self, periodo):
        return null_to_numeric(Pago.objects.filter(rubro__inscripcion=self, rubro__periodo=periodo, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def total_valores_periodo(self, periodo):
        return null_to_numeric(Rubro.objects.filter(inscripcion=self, periodo=periodo).aggregate(valor=Sum('valor'))['valor'], 2)

    def total_valores_periodo_prontopago(self, periodo):
        return null_to_numeric(Rubro.objects.filter(inscripcion=self, periodo=periodo, validoprontopago=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def total_cancelado(self):
        return null_to_numeric(PagoCancelado.objects.filter(rubro__inscripcion=self).aggregate(valor=Sum('valor'))['valor'], 2)

    def total_pagado_pendiente(self):
        return null_to_numeric(Pago.objects.filter(rubro__inscripcion=self, rubro__cancelado=False, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def total_notacredito(self):
        return null_to_numeric(self.notacredito_set.all().aggregate(valor=Sum('valorinicial'))['valor'], 2)

    def total_adeudado(self):
        return null_to_numeric(self.rubro_set.aggregate(valor=Sum('saldo'))['valor'], 2)

    def adeuda_a_la_fecha(self):
        return null_to_numeric(self.rubro_set.filter(fechavence__lt=datetime.now().date()).aggregate(valor=Sum('saldo'))['valor'], 2)

    def credito_a_la_fecha(self):
        return null_to_numeric(self.rubro_set.filter(fechavence__gte=datetime.now().date()).aggregate(valor=Sum('saldo'))['valor'], 2)

    def tiene_deuda_vencida(self):
        return self.rubro_set.filter(cancelado=False, fechavence__lt=datetime.now().date()).exists()

    def tiene_deuda_fuera_periodo(self, periodo):
        return Rubro.objects.filter(cancelado=False, fechavence__lt=datetime.now().date(), inscripcion=self).exclude(periodo=periodo).exists()

    def tiene_deuda(self):
        return self.rubro_set.filter(cancelado=False).exists()

    def tiene_deuda_orientacion(self):
        return self.rubro_set.filter(cancelado=True, nombre='DERECHO ORIENTACIÓN PROFESIONAL').exists()

    def tiene_deuda_inscripcion(self):
        return self.rubro_set.filter(nombre__icontains='INSCRIPCION').exists()

    def tiene_deuda_inscripcion_pagada(self):
        return self.rubro_set.filter(cancelado=True,nombre__icontains='INSCRIPCION').exists()

    def tiene_credito(self):
        return self.rubro_set.filter(cancelado=False, fechavence__gte=datetime.now().date()).exists()

    def estainactivo(self):
        return not self.persona.usuario.is_active

    def recordacademico(self):
        return self.recordacademico_set.all()

    def egresado(self):
        return self.egresado_set.exists()

    def graduado(self):
        return self.graduado_set.exists()

    def datos_egresado(self):
        if self.egresado():
            return self.egresado_set.all()[0]
        return None

    def datos_graduado(self):
        if self.graduado():
            return self.graduado_set.all()[0]
        return None

    def tiene_deuda_externa(self):
        if self.inscripcionflags_set.exists():
            return self.inscripcionflags_set.all()[0].tienedeudaexterna
        return False

    def tiene_notadebito(self):
        return RubroNotaDebito.objects.filter(rubro__cancelado=False, rubro__inscripcion=self).exists()

    def valor_pendiente_notadebito(self):
        notasdebitos = RubroNotaDebito.objects.filter(rubro__cancelado=False, rubro__inscripcion=self)
        valor = 0
        for notadebito in notasdebitos:
            valor += notadebito.rubro.adeudado()
        return valor

    def chequea_mora(self):
        for rubro in self.rubro_set.filter(cancelado=False):
            rubro.cheque_mora()

    def registrado_proyecto(self, proyecto):
        return ParticipanteProyectoVinculacion.objects.filter(proyecto=proyecto, inscripcion=self).exists()

    def registrado_curso(self, curso):
        return MatriculaCursoEscuelaComplementaria.objects.filter(curso=curso, inscripcion=self).exists()

    def puede_registrar_proyecto(self, proyecto):
        carreras = proyecto.carreras.all()
        if proyecto.fin <= datetime.now().date():
            return False
        if proyecto.participanteproyectovinculacion_set.all().count() >= proyecto.limiteparticipantes:
            return False
        if carreras.count() > 0 and self.carrera not in [x for x in carreras]:
            return False
        if proyecto.limiteparticipantes:
            if proyecto.limiteproyectovinculacion_set.filter(carrera=self.carrera).exists():
                limite = proyecto.limiteproyectovinculacion_set.filter(carrera=self.carrera)[0]
                if limite.limite == 0:
                    limiteparacarrera = proyecto.limiteparticipantes - null_to_numeric(proyecto.limiteproyectovinculacion_set.exclude(carrera=self.carrera).aggregate(suma=Sum('limite'))['suma'])
                    lista = [x.carrera.id for x in proyecto.limiteproyectovinculacion_set.filter(limite=0)]
                    inscritos = proyecto.participanteproyectovinculacion_set.filter(inscripcion__carrera__id__in=lista).count()
                    if inscritos >= limiteparacarrera:
                        return False
                else:
                    inscritos = proyecto.participanteproyectovinculacion_set.filter(inscripcion__carrera=self.carrera).count()
                    limiteparacarrera = proyecto.limiteproyectovinculacion_set.filter(carrera=self.carrera)[0].limite
                    if inscritos >= limiteparacarrera:
                        return False
        return True

    def puede_registrar_actividad(self, actividad):
        carreras = actividad.carrera.all()
        if carreras.count() > 0 and self.carrera not in [x for x in carreras]:
            return False
        elif actividad.fechainicio <= datetime.now().date():
            return False
        return True

    def participante_proyecto(self, proyecto):
        if ParticipanteProyectoVinculacion.objects.filter(proyecto=proyecto, inscripcion=self).exists():
            return ParticipanteProyectoVinculacion.objects.filter(proyecto=proyecto, inscripcion=self)[0]
        return None

    def horas_acumuladas_vinculacion(self):
        return null_to_numeric(self.participanteproyectovinculacion_set.filter(proyecto__cerrado=True, estado__id=NOTA_ESTADO_APROBADO).aggregate(valor=Sum('horas'))['valor'], 1)

    def creditos_acumuladas_vinculacion(self):
        return null_to_numeric(ProyectosVinculacion.objects.filter(cerrado=True, participanteproyectovinculacion__estado__id=NOTA_ESTADO_APROBADO).aggregate(valor=Sum('creditos'))['valor'], 4)

    def proyectosregistrados(self):
        return self.participanteproyectovinculacion_set.all().count()

    def registrado_actividadextracurricular(self, actividad):
        return ParticipanteActividadExtraCurricular.objects.filter(actividad=actividad, inscripcion=self).exists()

    def promedio_graduado(self):
        return null_to_numeric(self.recordacademico_set.filter(validacreditos=True, aprobada=True).aggregate(valor=Avg('nota'))['valor'], 2)

    def cantidad_materias_validas(self):
        return self.recordacademico_set.filter(validacreditos=True).count()

    def calcular_nivel(self):
        malla = self.mi_malla()
        niveles_maximos = malla.nivelesregulares
        numeronivel = NIVEL_MALLA_CERO
        if not malla.nivelacion:
            numeronivel = NIVEL_MALLA_UNO
        # if self.documentos_entregados().pre:
        #     numeronivel = NIVEL_MALLA_UNO
        if self.nivelhomologado:
            numeronivel = self.nivelhomologado.id
        cantidad_arrastres = 0
        aprobadas = [x.asignatura.id for x in self.recordacademico_set.filter(aprobada=True)]
        for minivel in range(numeronivel, niveles_maximos + 1):
            numeronivel = minivel
            total_optativas_nivel = 0
            total_libreopcion_nivel = 0
            total_regulares_nivel = malla.asignaturamalla_set.filter(nivelmalla__id=minivel).count()
            total_nivel_malla = total_optativas_nivel + total_libreopcion_nivel + total_regulares_nivel
            aprobadas_nivel = malla.asignaturamalla_set.filter(asignatura__id__in=aprobadas, nivelmalla__id=minivel).count()
            if aprobadas_nivel < total_nivel_malla:
                cantidad_arrastres += total_nivel_malla - aprobadas_nivel
                if cantidad_arrastres > malla.cantidadarrastres:
                    break
            if not aprobadas_nivel:
                break
        nivel = NivelMalla.objects.get(pk=numeronivel)
        return nivel

    def tiene_nivel(self):
        return self.inscripcionnivel_set.exists()

    def mi_nivel(self):
        if self.tiene_nivel():
            ficha = self.inscripcionnivel_set.all()[0]
        else:
            ficha = InscripcionNivel(inscripcion=self,
                                     nivel_id=NIVEL_MALLA_UNO)
            ficha.save()
        return ficha

    def proximo_nivel(self, nivel):
        if NivelMalla.objects.filter(id__gt=nivel.id).exists():
            return NivelMalla.objects.filter(id__gt=nivel.id).order_by('id')[0]
        return nivel

    def actualizar_nivel(self):
        nivel = self.mi_nivel()
        nuevonivel = self.calcular_nivel()
        nivel.nivel = nuevonivel
        nivel.save()

    def mi_primerperiodo(self):
        if self.matricula_set.filter(nivelmalla=1).exists():
            ficha = self.matricula_set.filter(nivelmalla=1)[0]
            periodoid = Nivel.objects.filter(pk=ficha.nivel_id)[0]
            return periodoid.periodo_id
        else:
            return 0

    def actualiza_matriculas(self, asignatura):
        for materia in MateriaAsignada.objects.filter(matricula__inscripcion=self, materia__asignatura=asignatura):
            materia.save()
            if AgregacionEliminacionMaterias.objects.filter(matricula=materia.matricula, asignatura=asignatura).exists():
                age = AgregacionEliminacionMaterias.objects.filter(matricula=materia.matricula, asignatura=asignatura)[0]
                age.matriculas = materia.matriculas
                age.save()

    def promedio_record(self):
        return null_to_numeric(self.recordacademico_set.filter(validapromedio=True, aprobada=True).aggregate(valor=Avg('nota'))['valor'], 2)

    def actualiza_promedio_record(self):
        self.promediogeneral=null_to_numeric(self.recordacademico_set.filter(validapromedio=True, aprobada=True).aggregate(valor=Avg('nota'))['valor'], 2)
        self.save()
        return True

    def asistencia_record(self):
        return null_to_numeric(self.recordacademico_set.filter(validapromedio=True, aprobada=True).aggregate(valor=Avg('asistencia'))['valor'], 2)

    def total_creditos(self):
        return null_to_numeric(self.recordacademico_set.filter(validacreditos=True, aprobada=True).aggregate(valor=Sum('creditos'))['valor'], 4)

    def total_creditos_malla(self):
        return null_to_numeric(self.recordacademico_set.filter(validacreditos=True, aprobada=True, asignatura__asignaturamalla__malla=self.mi_malla()).aggregate(valor=Sum('creditos'))['valor'], 4)

    def total_creditos_otros(self):
        return null_to_numeric(self.recordacademico_set.filter(validacreditos=True, aprobada=True).exclude(asignatura__asignaturamalla__malla=self.mi_malla()).aggregate(valor=Sum('creditos'))['valor'], 4)

    def total_creditos_otros_libre_c(self):
        return null_to_numeric(self.recordacademico_set.filter(aprobada=True, libreconfiguracion=True).exclude(asignatura__asignaturamalla__malla=self.mi_malla()).aggregate(valor=Sum('creditos'))['valor'], 4)

    def total_creditos_otros_optativa(self):
        return null_to_numeric(self.recordacademico_set.filter(validacreditos=True, aprobada=True, optativa=True).exclude(asignatura__asignaturamalla__malla=self.mi_malla()).aggregate(valor=Sum('creditos'))['valor'], 4)

    def total_horas(self):
        return null_to_numeric(self.recordacademico_set.filter(validacreditos=True, aprobada=True, asignatura__asignaturamalla__malla=self.mi_malla()).aggregate(valor=Sum('horas'))['valor'], 2)

    def materia_retirado(self, materia):
        if MateriaAsignada.objects.filter(matricula__inscripcion=self, materia=materia).exists():
            materiaasignada = MateriaAsignada.objects.get(matricula__inscripcion=self, materia=materia)
            return materiaasignada.retirado()
        return False

    def total_horas_reprobadas(self):
        return null_to_numeric(self.recordacademico_set.filter(aprobada=False, asignatura__asignaturamalla__malla=self.mi_malla()).aggregate(valor=Sum('horas'))['valor'], 2)

    def total_horas_malla(self):
        return null_to_numeric(self.mi_malla().asignaturamalla_set.aggregate(valor=Sum('horas'))['valor'], 1)

    def total_materias_nivel(self):
        minivel = self.mi_nivel().nivel
        return self.mi_malla().asignaturamalla_set.filter(nivelmalla=minivel).count()

    def total_materias_pendientes_malla(self):
        malla = self.mi_malla()
        return malla.asignaturamalla_set.all().count() - malla.asignaturamalla_set.filter(asignatura__in=[x.asignatura for x in self.recordacademico_set.all()]).count()

    def porciento_asistencia_proyecto(self, proyecto):
        total = self.asistenciaactaavance_set.filter(actaavance__isnull=False, actaavance__tutoria__tutor__preproyecto__proyectogrado=proyecto).distinct().count()
        asistio = self.asistenciaactaavance_set.filter(actaavance__isnull=False, asistio=True, actaavance__tutoria__tutor__preproyecto__proyectogrado=proyecto).distinct().count()
        if total:
            return null_to_numeric(asistio * 100.0 / total, 0)
        return 0

    def promedio_nota_nivelacion(self):
        nota = 0
        if self.tipocalculonivelacion == 0:
            nota = 0
        return null_to_numeric(nota, 2)

    def nota_minima_nivelacion(self):
        return MODELO_NIVELACION[self.tipocalculonivelacion][0]

    def asistenciaminima_minima_nivelacion(self):
        return MODELO_NIVELACION[self.tipocalculonivelacion][0]

    def promedio_asistencia_nivelacion(self):
        return null_to_numeric(MateriaAsignada.objects.filter(matricula__nivelmalla__id=0).aggregate(valor=Avg('asistenciafinal'))['valor'], 0)

    def aprobo_nivelacion(self):
        malla = self.mi_malla()
        if malla.nivelacion:
            if self.documentos_entregados().pre:
                return True
            return self.promedio_nota_nivelacion() >= self.nota_minima_nivelacion() and self.promedio_asistencia_nivelacion() >= self.asistenciaminima_minima_nivelacion()
        return True

    def esta_aprobado_asignatura(self, asignatura):
        return self.recordacademico_set.filter(asignatura=asignatura, aprobada=True).exists()

    def esta_reprobado_asignatura(self, asignatura):
        return self.recordacademico_set.filter(asignatura=asignatura, aprobada=False).exists()

    def promedio_malla(self):
        return null_to_numeric(self.recordacademico_set.filter(validapromedio=True, aprobada=True, asignaturamalla__isnull=False).distinct().aggregate(valor=Avg('nota'))['valor'], 2)

    def actualizar_promedios(self):
        self.promediogeneral = self.promedio_record()
        self.promedionivelacion = self.promedio_nota_nivelacion()
        self.promediomalla = self.promedio_malla()
        self.valoracioncalificacion = valoracion_calificacion(self.promediogeneral)
        self.save()

    def tiene_record(self):
        return self.recordacademico_set.exists()

    def rindio_examen(self, examen):
        if examen:
            return RespuestaExamenAdmision.objects.filter(exameninscripcion=examen, exameninscripcion__inscripcion=self).exists()
        return False

    def registro_examen(self, registro):
        if registro:
            return RespuestaExamenAdmision.objects.filter(exameninscripcion__examenadmision=registro.examenadmision, exameninscripcion__inscripcion=self).exists()
        return False

    def mi_examen_admision(self, examen):
        if self.rindio_examen(examen):
            return RespuestaExamenAdmision.objects.filter(exameninscripcion=examen, exameninscripcion__inscripcion=self)[0]
        return None

    def examen_encurso(self, examen):
        if RespuestaExamenAdmision.objects.filter(exameninscripcion=examen, exameninscripcion__inscripcion=self).exists():
            respuesta = RespuestaExamenAdmision.objects.filter(exameninscripcion=examen, exameninscripcion__inscripcion=self)[0]
            return not respuesta.finalizo()
        return False

    def tiene_examen_inscripcion(self):
        return self.exameninscripcion_set.exists()

    def mi_enxamen_inscripcion(self):
        return self.exameninscripcion_set.all().order_by('-id')[0]

    def tiene_entrevista(self):
        return self.inscripcionentrevista_set.exists()

    def mi_entrevista(self):
        return self.inscripcionentrevista_set.all().order_by('-id')[0]

    def tiene_horas_pendientes_vinculacion(self):
        malla = self.mi_malla()
        return malla.horasvinculacion > self.horas_vcc()

    def horas_pendientes_vinculacion(self):
        malla = self.mi_malla()
        return malla.horasvinculacion - self.horas_vcc()

    def tiene_horas_pendientes_practica(self):
        malla = self.mi_malla()
        return malla.horaspracticas > self.horas_ppp()



    def horas_pendientes_practica(self):
        malla = self.mi_malla()
        return malla.horaspracticas - self.horas_ppp()

    def puede_registrar_practicas(self):
        malla = self.mi_malla()
        if malla.nivelhoraspracticas:
            return self.mi_nivel().nivel.id >= malla.nivelhoraspracticas.id
        return True

    def puede_registrar_vinculacion(self):
        malla = self.mi_malla()
        if malla.nivelhorasvinculacion:
            return self.mi_nivel().nivel.id >= malla.nivelhorasvinculacion.id
        return True

    def puede_tomar_materia_titulacion(self, materia):
        malla = self.mi_malla()
        asignatura = materia.asignatura
        curso = materia.curso
        if malla.trabajotitulacionmalla_set.filter(asignatura=asignatura, unidadtitulacion=curso.unidadtitulacion, tipotrabajotitulacion=curso.tipotrabajotitulacion).exists():
            materiatitulacion = malla.trabajotitulacionmalla_set.filter(asignatura=asignatura, unidadtitulacion=curso.unidadtitulacion, tipotrabajotitulacion=curso.tipotrabajotitulacion)[0]
            for materiap in TrabajoTitulacionMallaPredecesora.objects.filter(trabajotitulacionmalla=materiatitulacion):
                if not self.recordacademico_set.filter(asignatura=materiap.predecesora.asignatura, aprobada=True).exists():
                    return False
            if materiatitulacion.cantidadmatriculas:
                if self.historicorecordacademico_set.filter(asignatura=asignatura, aprobada=False).count() >= materiatitulacion.cantidadmatriculas:
                    return False
            if self.recordacademico_set.filter(asignatura=asignatura, aprobada=True).exists():
                return False
            return True
        return False


    def fecha_inicio_titulacion(self):
        if self.matricula_set.exists():
            return self.matricula_set.order_by('-fecha')[0].nivel.fin
        return datetime.now().date()

    def cumplio_malla(self):
        malla = self.mi_malla()
        return malla.asignaturamalla_set.filter().distinct().count() == self.recordacademico_set.filter(asignaturamalla__isnull=False, aprobada=True).count()

    def proxima_fecha_prorroga(self, fecha, periocidad):
        month = fecha.month
        year = fecha.year
        if (month + periocidad) > 12:
            sobrante = (month + periocidad) - 12
            if sobrante > 12:
                sobrante = sobrante / 12
                nextmonth = month
                nextyear = year + sobrante + 1
            else:
                nextmonth = sobrante
                nextyear = year + 1
        elif month == 12 and periocidad == 1:
            nextmonth = 1
            nextyear = year + 1
        else:
            nextmonth = month + periocidad
            nextyear = year
        dia = fecha.day
        while dia >= 0:
            try:
                return datetime(nextyear, nextmonth, dia).date()
            except:
                dia -= 1

    def cantidad_observacion_titulacion(self):
        return self.observaciontitulacion_set.count()

    def tiene_observacion_titulacion(self):
        return self.observaciontitulacion_set.exists()

    def tiene_trabajo_titulacion(self):
        return self.preproyectogrado_set.filter(estado=2).exists()

    def tiene_proyecto_grado(self):
        return ProyectoGrado.objects.filter(preproyecto__inscripciones=self).exists()

    def tiene_examen_complexivo(self):
        return ExamenComplexivo.objects.filter(proyectocomplexivo__inscripcion=self).exists()

    def tiene_proyecto_grado_en_tutoria(self):
        return ProyectoGrado.objects.filter(preproyecto__inscripciones=self, estado=1).exists()

    def mi_examen_complexivo(self):
        if self.tiene_examen_complexivo():
            return ExamenComplexivo.objects.filter(proyectocomplexivo__inscripcion=self).order_by('-id')[0]
        return None

    def mi_proyecto_grado(self):
        if self.tiene_proyecto_grado():
            return ProyectoGrado.objects.filter(preproyecto__inscripciones=self)[0]
        return None

    def mi_proyecto_grado_en_tutoria(self):
        if self.tiene_proyecto_grado_en_tutoria():
            return ProyectoGrado.objects.filter(preproyecto__inscripciones=self, estado=1)[0]
        return None

    def tiene_tutorias_pendientes(self):
        return self.asistenciaactaavance_set.filter(confirmado=False).exists()

    def mi_ultimo_examen_admision_cerrado(self):
        if self.exameninscripcion_set.filter(respuestaexamenadmision__administrarexamenadmision__cerrado=True).exists():
            return self.exameninscripcion_set.filter(respuestaexamenadmision__administrarexamenadmision__cerrado=True).order_by('-respuestaexamenadmision__fecha')[0].mi_respuesta_examen()
        return None

    def mi_ultimo_examen_admision(self):
        if self.exameninscripcion_set.filter(respuestaexamenadmision__fecha__isnull=False).exists():
            return self.exameninscripcion_set.filter(respuestaexamenadmision__fecha__isnull=False).order_by('-respuestaexamenadmision__fecha')[0].mi_respuesta_examen()
        return None

    def mi_ultima_entrevista_admision(self):
        if RespuestaEntrevista.objects.filter(inscripcionentrevista__inscripcion=self, confirmada=True).exists():
            return RespuestaEntrevista.objects.filter(inscripcionentrevista__inscripcion=self, confirmada=True).order_by('-fecha')[0]
        return None

    def esta_registrado_curso(self, curso):
        return self.matriculacursoescuelacomplementaria_set.filter(curso=curso).exists()

    def es_becario(self):
        return self.matricula_set.filter(becado=True, cerrada=False).exists()

    def tiene_documentacion(self):
        return self.archivodocumentoinscripcion_set.exists()

    def actualizar_homologacion(self):
        documentos = self.documentos_entregados()
        if not documentos.homologar:
            if self.tiene_record():
                documentos.homologar = self.tiene_homologaciones()
                documentos.save()

    def resetea_autorizaciones(self):
        flags = self.mis_flag()
        flags.puedecobrar = False
        flags.save()

    def fecha_inicio_carrera(self):
        if self.fechainiciocarrera:
            return self.fechainiciocarrera
        elif self.matricula_set.exists():
            return self.matricula_set.order_by('fecha')[0].nivel.inicio
        elif self.recordacademico_set.exists():
            return self.recordacademico_set.order_by('fecha')[0].fecha
        return datetime.now().date()

    def actualiza_fecha_inicio_carrera(self):
        inscripcion = self
        if not inscripcion.graduado():
            if inscripcion.matricula_set.filter(nivelmalla__id=NIVEL_MALLA_UNO).exists():
                matricula = inscripcion.matricula_set.filter(nivelmalla__id=NIVEL_MALLA_UNO).order_by('fecha')[0]
                inscripcion.fechainiciocarrera = matricula.nivel.inicio
                inscripcion.save()
            elif not inscripcion.matricula_set.filter(nivelmalla__id=NIVEL_MALLA_UNO).exists():
                if inscripcion.recordacademico_set.filter(Q(homologada=True) | Q(convalidacion=True)).exists():
                    fecha = inscripcion.recordacademico_set.filter(Q(homologada=True) | Q(convalidacion=True)).aggregate(fecha=Min('fecha'))['fecha']
                    inscripcion.fechainicioconvalidacion = fecha
                    inscripcion.fechainiciocarrera = fecha
                    inscripcion.save()

    def tiene_examenes_asignados(self):
        return self.exameninscripcion_set.exists()

    def tiene_entrevistas_asignadas(self):
        return self.inscripcionentrevista_set.exists()

    def valor_deuda_vencida(self):
        return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=datetime.now().date(), inscripcion=self).aggregate(valor=Sum('saldo'))['valor'], 2)

    def mis_profesores_acreditacion(self):
        return ProfesorMateria.objects.filter(tipoprofesor__id=TIPO_DOCENTE_TEORIA, materia__materiaasignada__matricula__inscripcion=self).distinct().order_by('-tipoprofesor', 'profesor')

    def profesores_homologacion(self):
        return self.profesorinscripcionhomologacion_set.all().order_by('profesor__persona')

    def existe_solicitudfinanciamiento(self, periodo):
        if periodo.id == 93:
            return self.prorrogafinanciamiento_set.exists()
        else:
            return False

    def existe_solicitudsecretaria_abierta(self, tipo, periodo):
        return self.solicitudsecretariadocente_set.filter(tipo=tipo, cerrada=False, matricula__nivel__periodo=periodo).exists()

    def tiene_procesobeca(self, periodo):
        return self.procesoaplicantebeca_set.filter(fechaprocesosbeca__periodo=periodo).exists()

    def tiene_procesobeca_no_negado(self, periodo):
        return self.procesoaplicantebeca_set.filter(fechaprocesosbeca__periodo=periodo).exclude(estado=3).exists()

    def turnos_dia_fecha(self, fecha):
        return Turno.objects.filter(Q(clase__dia=fecha.isoweekday(), clase__inicio__lte=fecha, clase__fin__gte=fecha, clase__materia__materiaasignada__matricula__inscripcion=self, clase__materia__cerrado=False, clase__activo=True) | Q(clase__dia=fecha.isoweekday(), clase__inicio__lte=fecha, clase__fin__gte=fecha, clase__materiacurso__materiaasignadacurso__matricula__inscripcion=self, clase__materiacurso__cerrada=False, clase__activo=True) | Q(clase__dia=fecha.isoweekday(), clase__inicio__lte=fecha, clase__fin__gte=fecha, clase__materiatitulacion__materiaasignadacursounidadtitulacion__matricula__inscripcion=self, clase__materiacurso__cerrada=False, clase__activo=True)).distinct()

    def turnos_practicas_dia_fecha(self, fecha):
        return Turno.objects.filter(Q(clasepractica__dia=fecha.isoweekday(), clasepractica__inicio__lte=fecha, clasepractica__fin__gte=fecha, clasepractica__grupo__materiaasignadagrupopracticas__materiaasignada__matricula__inscripcion=self, clasepractica__grupo__materia__cerrado=False, clasepractica__activo=True)).distinct()

    def clases_horario_fecha(self, fecha, turno):
        return Clase.objects.filter(Q(turno=turno, dia=fecha.isoweekday(), inicio__lte=fecha, fin__gte=fecha, materia__materiaasignada__matricula__inscripcion=self, materia__cerrado=False, activo=True) | Q(turno=turno, dia=fecha.isoweekday(), inicio__lte=fecha, fin__gte=fecha, materiatitulacion__materiaasignadacursounidadtitulacion__matricula__inscripcion=self, materiatitulacion__cerrada=False, activo=True)).distinct()

    def clases_practicas_horario_fecha(self, fecha, turno):
        return ClasePractica.objects.filter(turno=turno, dia=fecha.isoweekday(), inicio__lte=fecha, fin__gte=fecha, grupo__materiaasignadagrupopracticas__materiaasignada__matricula__inscripcion=self, grupo__materia__cerrado=False, activo=True).distinct()

    def entrevistaorientacion_pendiente(self):
        return self.solicitudentrevista_set.filter(estado=False).exists()

    def entrevistaorientacion_lista(self):
        return self.solicitudentrevista_set.all().order_by('id')

    def existe_registro_orientacion(self):
        return self.solicitudentrevista_set.all().exists()

    def malla_nueva(self):
        malla = self.mi_malla()
        if malla.modelonuevo != 0:
            return True
        return False

    def valor_inicial_prorroga_pagado(self, periodo):
        valorpagado = 0
        if self.solicitudsecretariadocente_set.filter(tipo__id__in=(41, 45), matricula__nivel__periodo=periodo).exists():
            for p in Pago.objects.filter(rubro__rubromatricula__isnull=False, rubro__inscripcion=self, rubro__periodo=periodo, valido=True):
                valorpagado += p.valor
            for p in Pago.objects.filter(rubro__rubrocuota__isnull=False, rubro__inscripcion=self, rubro__periodo=periodo, valido=True):
                valorpagado += p.valor
            for p in Pago.objects.filter(rubro__rubroagregacion__isnull=False, rubro__inscripcion=self, rubro__periodo=periodo, valido=True):
                valorpagado += p.valor
            for p in Pago.objects.filter(rubro__rubrootromatricula__isnull=False, rubro__inscripcion=self, rubro__periodo=periodo, valido=True):
                valorpagado += p.valor
            if self.carrera.posgrado:
                if valorpagado >= 1500:
                    return True
            elif self.carrera.id == 64:
                if valorpagado >= 2000:
                    return True
            else:
                if self.modalidad.id == 3:
                    if valorpagado >= 215:
                        return True
                elif self.modalidad.id == 2:
                    if valorpagado >= 600:
                        return True
                elif self.modalidad.id == 4:
                    if valorpagado >= 215:
                        return True
                elif self.modalidad.id == 1:
                    if self.sede.id == 1:
                        if valorpagado >= 600:
                            return True
                    elif self.sede.id == 2:
                        if valorpagado >= 700:
                            return True
        else:
            return True
        return False

    def repr_becapromocional(self):
        return BECA_PROMOCIONAL[self.becapromocional - 0][1]

    def repr_fuente(self):
        return FUENTES_INSCRIPCION[self.fuente - 0][1]

    def diasinscripcionhastahoy(self):
        dias = datetime.today() - self.fecha_creacion
        return int(dias.days)

    def tienea_solicitud_parqueadero(self):
        if self.solicitudparqueo_set.filter(activo=True).exists():
            return True
        return False

    def tiene_solicitud_beca_pagada(self, periodo):
        if self.rubro_set.filter(periodo=periodo,rubrootro__solicitud__tipo__id=38).exists():
            existe_pago = self.rubro_set.filter(periodo=periodo, rubrootro__solicitud__tipo__id=38)[0]
            if existe_pago.cancelado == True:
                return True
        else:
            return False

    def tiene_solicitud_prorroga(self, periodo):
        if self.rubro_set.filter(periodo=periodo,rubrootro__solicitud__tipo__id=45).exists():
            existe_pago = self.rubro_set.filter(periodo=periodo, rubrootro__solicitud__tipo__id=45)[0]
            if existe_pago.cancelado == True:
                return True
        else:
            return False

    def tiene_solicitud_homologacion(self):
        return self.solicitudhomologacion_set.filter(anulado=False).exists()

    def validacion_internado(self):
        if self.tiene_ingles_pendientes():
            return False, "No puede realizar la solicitud porque tiene niveles de inglés pendientes."
        if self.tiene_deuda_vencida():
            return False, "No puede continuar con la solicitud por registrar deuda vencida."
        count_total_asignaturas = self.mi_malla().asignaturamalla_set.count()
        count_en_record = RecordAcademico.objects.filter(inscripcion=self, aprobada=True).count()
        if count_total_asignaturas > 0:
            porcentaje = (count_en_record / count_total_asignaturas) * 100
            if porcentaje <= 70:
                return False, "Debe tener al menos el 70% de su malla académica aprobada para solicitar el internado."
        return True, ""

    def _tiene_record_via_prehomologacion(self) -> bool:
        return RecordAcademico.objects.filter(materiahomologacion__prehomologacion__inscripcion=self).exists()

    def paso_homologacion(self) -> int:
        """
        0 = Sin documentos homologación
        1 = Documentos listos
        2 = Solicitud creada
        3 = Información Pre-Homologación
        4 = Materias Pre-Homologadas
        5 = Ya consta en Record Académico
        """

        # 1️⃣ Documentos
        try:
            docs = self.documentos_entregados()
            if not docs.homologar:
                return 0
        except DocumentosDeInscripcion.DoesNotExist:
            return 0

        # 5️⃣ ¿Algún RecordAcadémico ligado a una materia de pre-homologación?
        if self._tiene_record_via_prehomologacion():
            return 5

        # 4️⃣ ¿Hay materias en PreHomologacionInscripcion?
        if PreHomologacionInscripcion.objects.filter(prehomologacion__inscripcion=self).exists():
            return 4

        # 3️⃣ ¿Existe la cabecera PreHomologacionInscripcionInformacion?
        if self.prehomologacioninscripcioninformacion_set.exists():
            return 3

        # 2️⃣ ¿Solicitud?
        if self.solicitudhomologacion_set.exists():
            return 2

        return 1  # Solo documentos

    def homologacion_validacion_creditos_nivel(self):
        info = self.prehomologacioninscripcioninformacion_set.prefetch_related(
            Prefetch('prehomologacionvalidacionconocimientos_set', queryset=PreHomologacionValidacionConocimientos.objects.only('nivel_aprobado', 'creditos_aprobado'))).first()

        if info:
            validacion = info.prehomologacionvalidacionconocimientos_set.first()
            if validacion:
                return {'nivel': validacion.nivel_aprobado,
                        'creditos': validacion.creditos_aprobado}
        return {'nivel': None, 'creditos': None}

    def tiene_costo_periodo(self):
        return True if PreciosPeriodoModulosInscripcion.objects.filter(periodo=self.periodo,sede=self.sede,modalidad=self.modalidad,malla=self.mi_malla(),precioinscripcion__gt=0) else False

    def nota_final_graduado(self):
        if self.graduado():
            g = self.graduado_set.all()[0]
            return round(g.promediotitulacion, 2)
        return 0

    def ultima_matricula_rep(self):
        if self.ultima_matricula():
            return u'%s %s' % (self.ultima_matricula().nivel.periodo.tipo, self.ultima_matricula().nivel.periodo.nombre)
        return u'NO REGISTRA MATRÍCULA'

    def tiene_nee(self):
        return self.inclusionbienestar_set.exists()

    def save(self, *args, **kwargs):
        self.identificador = null_to_text(self.identificador)
        self.coordinacion = self.mi_coordinacion()
        if self.id:
            self.nivelado = self.esta_nivelado()
            self.promediogeneral = self.promedio_record()
            # self.promedionivelacion = self.promedio_nota_nivelacion()
            self.promediomalla = self.promedio_malla()
            if not self.cumplimiento:
                self.cumplimiento = self.cumplio_malla()
            if self.cumplimiento:
                if not self.fechainicioestadotitulacion:
                    self.fechainicioestadotitulacion = self.fecha_inicio_titulacion()
                if not self.fechalimiteprorrogauno:
                    self.fechalimiteprorrogauno = self.proxima_fecha_prorroga(self.fechainicioestadotitulacion, TIEMPO_PRORROGA_UNO)
                if not self.fechalimiteprorrogados:
                    self.fechalimiteprorrogados = self.proxima_fecha_prorroga(self.fechalimiteprorrogauno, TIEMPO_PRORROGA_DOS)
                if not self.fechalimiteactualizacionc:
                    self.fechalimiteactualizacionc = self.proxima_fecha_prorroga(self.fechalimiteprorrogados, TIEMPO_ACTUALIZAON_CONOCIMIENTO)
                self.datos_egresado()
            self.valoracioncalificacion = valoracion_calificacion(self.promediogeneral)
        if not self.tipoinscripcion:
            self.tipoinscripcion_id = TIPO_INSCRIPCION_REGULAR
        super(Inscripcion, self).save(*args, **kwargs)





class InscripcionNivel(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u"Inscripción", on_delete=models.CASCADE)
    nivel = models.ForeignKey(NivelMalla, verbose_name=u"Nivel", on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.nivel

    class Meta:
        unique_together = ('inscripcion',)


class InscripcionMalla(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    malla = models.ForeignKey(Malla, verbose_name=u'Malla', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.inscripcion, self.malla)

    class Meta:
        verbose_name_plural = u"Mallas de inscripciones"
        unique_together = ('inscripcion',)


class Raza(ModeloBase):
    nombre = models.CharField(default='', max_length=50, verbose_name=u'Nombre')
    codigosniese = models.CharField(max_length=15, default='', verbose_name=u'Codigo Sniese')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Etnias"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigosniese = null_to_text(self.codigosniese)
        super(Raza, self).save(*args, **kwargs)




class NacionalidadIndigena(ModeloBase):
    nombre = models.CharField(default='', max_length=50, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Nacionalidades Indigenas"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(NacionalidadIndigena, self).save(*args, **kwargs)


class ParaleloMateria(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Paralelos de materias"
        ordering = ['nombre']
        unique_together = ('nombre',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("ParaleloMateria.objects.filter(Q(nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(ParaleloMateria, self).save(*args, **kwargs)

class CodigoEvaluacion(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    alias = models.CharField(default='', max_length=50, verbose_name=u'Alias')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Códigos de evaluación"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.alias = null_to_text(self.alias)
        super(CodigoEvaluacion, self).save(*args, **kwargs)

class ModeloEvaluativo(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")
    fecha = models.DateField(verbose_name=u"Fecha")
    principal = models.BooleanField(default=False, verbose_name=u"Principal")
    notamaxima = models.FloatField(default=0, verbose_name=u'Nota maxima')
    notaaprobar = models.FloatField(default=0, verbose_name=u'Nota para aprobar')
    notarecuperacion = models.FloatField(default=0, verbose_name=u'Nota para recuperación')
    asistenciaaprobar = models.FloatField(default=0, verbose_name=u'Asistencia para aprobar')
    asistenciarecuperacion = models.FloatField(default=0, verbose_name=u'Asistencia para recuperación')
    observaciones = models.TextField(default='', max_length=200, verbose_name=u'Observaciones')
    logicamodelo = models.TextField(default='', max_length=200, verbose_name=u'logica')
    notafinaldecimales = models.IntegerField(default=0, verbose_name=u'lugares decimales')
    activo = models.BooleanField(default=True, verbose_name=u"Activo")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Modelos evaluativos"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def en_uso(self):
        if self.materia_set.exists():
            return True
        if self.cursoescuelacomplementaria_set.exists():
            return True
        # if self.lmsmodeloevaluativo_set.exists():
        #     return True
        # if self.solicitudingresonotasestudiante_set.exists():
        #     return True
        return False

    def campos(self):
        return self.detallemodeloevaluativo_set.all()

    def campos_editables(self):
        return self.detallemodeloevaluativo_set.filter(dependiente=False)

    def puede_modificarse(self):
        return not EvaluacionGenerica.objects.filter(detallemodeloevaluativo__modelo=self, valor__gt=0).exists()

    def campo(self, nombre):
        return self.detallemodeloevaluativo_set.filter(nombre=nombre)[0]

    def campos_dependientes(self):
        return self.detallemodeloevaluativo_set.filter(dependiente=True)

    def cantidad_campos(self):
        return self.detallemodeloevaluativo_set.count()

    def cronogramas_periodo(self, nivel):
        return self.cronogramaevaluacionmodelo_set.filter(nivel=nivel)

    def fecha_habilitada(self, campo, periodo):
        if FechaEvaluacionCampoModelo.objects.filter(periodo=periodo, campo=campo).exists():
            return FechaEvaluacionCampoModelo.objects.filter(periodo=periodo, campo=campo)[0]
        return None

    def logica_modelo_lms(self, lms):
        if self.lmsmodeloevaluativo_set.exists():
            return self.lmsmodeloevaluativo_set.all()[0]
        else:
            logicamodelo = LmsModeloEvaluativo(lms=lms,
                                               modeloevaluativo=self)
            logicamodelo.save()
            return logicamodelo

    def requiere_pago(self):
        return self.detallemodeloevaluativo_set.filter(requierepago=True).exists()

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.observaciones = null_to_text(self.observaciones)
        super(ModeloEvaluativo, self).save(*args, **kwargs)



class DetalleModeloEvaluativo(ModeloBase):
    modelo = models.ForeignKey(ModeloEvaluativo, verbose_name=u"Modelo", on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=10, verbose_name=u"Nombre campo")
    alternativa = models.ForeignKey(CodigoEvaluacion, verbose_name=u"Alternativas de evaluación", on_delete=models.CASCADE)
    notaminima = models.FloatField(default=0, verbose_name=u'Nota mínima')
    notamaxima = models.FloatField(default=0, verbose_name=u'Nota máxima')
    decimales = models.IntegerField(default=0, verbose_name=u'lugares decimales')
    actualizaestado = models.BooleanField(default=False, verbose_name=u"Actualiza el estado")
    determinaestadofinal = models.BooleanField(default=False, verbose_name=u"Determina estado final")
    dependiente = models.BooleanField(default=False, verbose_name=u"Campo dependiente")
    dependeasistencia = models.BooleanField(default=False, verbose_name=u"Depende de asistencia")
    orden = models.IntegerField(default=0, verbose_name=u"Orden en acta")
    requierepago = models.BooleanField(default=False, verbose_name=u"Requiere Pago")

    def __str__(self):
        return u'%s (%s a %s)' % (self.nombre, self.notaminima.__str__(), self.notamaxima.__str__())

    class Meta:
        verbose_name_plural = u"Modelos evaluativos - detalles"
        ordering = ['orden']
        unique_together = ('modelo', 'nombre',)

    def permite_ingreso_nota(self, materiaasignada, cronograma):
        permite = False
        if self.requierepago:
            if materiaasignada.tiene_pagado_recuperacion():
                permite = True
        elif materiaasignada.materia.tiene_solicitud_ingreso_aprobada(self):
            permite = True
        elif materiaasignada.tiene_solicitud_ingreso_aprobada():
            permite = True
        elif materiaasignada.homologada() or materiaasignada.convalidada():
            permite = False
        elif materiaasignada.cerrado:
            permite = False
        else:
            if materiaasignada.materia.usaperiodocalificaciones:
                if cronograma:
                    if self.fechaevaluacioncampomodelo_set.filter(cronograma=cronograma).exists():
                        fechas = self.fechaevaluacioncampomodelo_set.filter(cronograma=cronograma)[0]
                        permite = fechas.inicio <= datetime.now().date() <= fechas.fin
            else:
                permite = (datetime(materiaasignada.materia.fin.year, materiaasignada.materia.fin.month, materiaasignada.materia.fin.day, 0, 0, 0) + timedelta(days=materiaasignada.materia.diasactivacioncalificaciones)).date() >= datetime.now().date()
            if not materiaasignada.sinasistencia:
                if self.dependeasistencia and permite:
                    permite = materiaasignada.porciento_requerido()
        return permite

    def htmlid(self):
        return self.nombre.replace('.', '_')

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(DetalleModeloEvaluativo, self).save(*args, **kwargs)


class FasesActividadesArticulacion(ModeloBase):
    nombre = models.CharField(verbose_name=u'Nombre', max_length=100)

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Fases Actividades Articulacion"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(FasesActividadesArticulacion, self).save(*args, **kwargs)


class Materia(ModeloBase):
    nivel = models.ForeignKey(Nivel, verbose_name=u'Nivel', on_delete=models.CASCADE)
    asignatura = models.ForeignKey(Asignatura, verbose_name=u'Asignatura', on_delete=models.CASCADE)
    asignaturamalla = models.ForeignKey(AsignaturaMalla, blank=True, null=True, verbose_name=u'Asignatura malla', on_delete=models.CASCADE)
    # modulomalla = models.ForeignKey(ModuloMalla, blank=True, null=True, verbose_name=u'Modulo malla', on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, related_name='+', blank=True, null=True, verbose_name=u'Carrera', on_delete=models.CASCADE)
    malla = models.ForeignKey(Malla, blank=True, null=True, verbose_name=u'Malla', on_delete=models.CASCADE)
    tipomateria = models.ForeignKey(TipoMateria, verbose_name=u'Tipo de materia', blank=True, null=True, on_delete=models.CASCADE)
    identificacion = models.CharField(default='', max_length=100, verbose_name=u'Código')
    alias = models.CharField(default='', blank=True, null=True, max_length=100, verbose_name=u'Alias')
    paralelomateria = models.ForeignKey(ParaleloMateria, blank=True, null=True, verbose_name=u'Paralelo materia', on_delete=models.CASCADE)
    horassemanales = models.FloatField(default=0, verbose_name=u'Horas Semanales')
    horas = models.FloatField(default=0, verbose_name=u'Horas')
    creditos = models.FloatField(default=0, verbose_name=u'créditos')
    inicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha Inicial')
    fin = models.DateField(blank=True, null=True, verbose_name=u'Fecha Final')
    fechafinasistencias = models.DateField(blank=True, null=True, verbose_name=u'Fecha Final para asistencias')
    rectora = models.BooleanField(default=False, verbose_name=u'Materia general')
    carrerascomunes = models.ManyToManyField(Carrera, related_name='+', verbose_name=u'Carreras comunes')
    cerrado = models.BooleanField(default=False, verbose_name=u'Cerrada')
    fechacierre = models.DateField(null=True, blank=True, verbose_name=u'Fecha de cierre')
    tutoria = models.BooleanField(default=False, verbose_name=u'Materia de tutoria')
    practicas = models.BooleanField(default=False, verbose_name=u'Materia practica')
    grado = models.BooleanField(default=False, verbose_name=u'Materia de grado')
    cupo = models.IntegerField(default=0, verbose_name=u'Cupo')
    cupocompartido = models.IntegerField(default=0, verbose_name=u'Cupo compartido')
    modeloevaluativo = models.ForeignKey(ModeloEvaluativo, blank=True, null=True, verbose_name=u'Cupo', on_delete=models.CASCADE)
    usaperiodoevaluacion = models.BooleanField(default=True, verbose_name=u'Usa cronograma de evaluaciones')
    diasactivacion = models.IntegerField(choices=DiasEvaluacion.choices, default=7, verbose_name=u'Días de activación')
    usaperiodocalificaciones = models.BooleanField(default=True, verbose_name=u'Usa cronograma de calificaciones')
    diasactivacioncalificaciones = models.IntegerField(default=1, verbose_name=u'Dias para ingreso de notas')
    validacreditos = models.BooleanField(default=True, verbose_name=u'Valida para créditos')
    validapromedio = models.BooleanField(default=True, verbose_name=u'Valida para promedio')
    sinasistencia = models.BooleanField(default=False, verbose_name=u'Sin asistencia')
    modulonivelmalla = models.ForeignKey(NivelMalla, blank=True, null=True, verbose_name=u'Nivel modulo', on_delete=models.CASCADE)
    asistenciaremota = models.BooleanField(default=False, verbose_name=u'')
    permite_modificar = models.BooleanField(default=False, verbose_name=u'Permite Modificar')
    bloqueado = models.BooleanField(default=False)


    def __str__(self):
        return u'%s - %s - %s - [%s]' % (self.nombre_completo(), self.profesor_principal() if self.profesor_principal() else '', self.nivel.paralelo, self.id)

    class Meta:
        verbose_name_plural = u"Materias"
        unique_together = ('nivel', 'asignaturamalla', 'paralelomateria',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Materia.objects.filter(Q(asignatura__nombre__contains='%s') | Q(identificacion__contains='%s') | Q(id=id_search('%s')))" % (q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.nombre_completo() + " - " + (self.paralelomateria.nombre if self.paralelomateria else self.nivel.paralelo.nombre) + " - (" + self.inicio.strftime('%d-%m-%Y') + " / " + self.fin.strftime('%d-%m-%Y') + ") - " + str(self.id)

    def tiene_silabo_malla(self):
        if self.asignaturamalla:
            return self.asignaturamalla.archivo_set.filter(aprobado=True).exists()
        return False

    def silabo_malla(self):
        if self.asignaturamalla:
            if self.asignaturamalla.archivo_set.filter(aprobado=True).exists():
                return self.asignaturamalla.archivo_set.filter(aprobado=True).all().order_by('-fecha')[0]
        return None

    def puede_cambiar_modelo(self):
        return not EvaluacionGenerica.objects.filter(detallemodeloevaluativo__modelo=self.modeloevaluativo, valor__gt=0).exists()

    def documentos(self):
        return self.documentosmateria_set.all().order_by('nombre')

    def finalizo(self):
        return self.fin < datetime.now().date()

    def coordinacion_materia(self):
        if self.nivel.nivellibrecoordinacion_set.exists():
            return self.nivel.nivellibrecoordinacion_set.all()[0].coordinacion
        return None

    def horas_restantes_horario(self):
        return null_to_numeric(Turno.objects.filter(clase__materia=self, clase__activo=True).aggregate(valor=Sum('horas'))['valor'], 1)

    def tiene_solicitud_ingreso(self, campo, profesor):
        return self.solicitudingresonotasatraso_set.filter(detallemodeloevaluativo=campo, profesor=profesor, estado=1).exists()

    def tiene_solicitud_ingreso_aprobada(self, campo):
        fecha = datetime.now().date()
        return self.solicitudingresonotasatraso_set.filter(fechaaprobacion__lte=fecha, fechalimite__gte=fecha, detallemodeloevaluativo=campo, estado=2).exists()

    def max_capacidad_aula(self):
        return null_to_numeric(Aula.objects.filter(clase__materia=self, clase__activo=True).distinct().aggregate(valor=Min('capacidad'))['valor'], 0)

    def tiene_capacidad(self):
        return self.materiaasignada_set.filter(matricula__retiromatricula__isnull=True).count() < self.cupo

    def aulas(self):
        return Aula.objects.filter(clase__materia=self, clase__activo=True).distinct().order_by('capacidad')

    def capacidad_sobrepasada(self):
        if self.materiaasignada_set.filter(matricula__retiromatricula__isnull=True).count() > self.cupo:
            return self.materiaasignada_set.filter(matricula__retiromatricula__isnull=True).count() - self.cupo
        return 0

    def capcidad_total(self):
        return self.cupo

    def capacidad_disponible(self):
        if self.materiaasignada_set.filter(matricula__retiromatricula__isnull=True).count() < self.cupo:
            return self.cupo - self.materiaasignada_set.filter(matricula__retiromatricula__isnull=True).count()
        return 0

    def capacidad_disponible_inscripcion(self, inscripcion):
        if self.rectora and self.cupocompartido > 0 and self.asignaturamalla:
            if self.asignaturamalla.malla.carrera == inscripcion.carrera:
                if self.materiaasignada_set.filter(matricula__retiromatricula__isnull=True, matricula__inscripcion__carrera=inscripcion.carrera).count() < (self.cupo - self.cupocompartido):
                    return (self.cupo - self.cupocompartido) - self.materiaasignada_set.filter(matricula__retiromatricula__isnull=True, matricula__inscripcion__carrera=inscripcion.carrera).count()
                return 0
            else:
                if self.materiaasignada_set.filter(matricula__retiromatricula__isnull=True).exclude(matricula__inscripcion__carrera=self.asignaturamalla.malla.carrera).count() < self.cupocompartido:
                    return self.cupocompartido - self.materiaasignada_set.filter(matricula__retiromatricula__isnull=True).exclude(matricula__inscripcion__carrera=self.asignaturamalla.malla.carrera).count()
                return 0
        else:
            if self.materiaasignada_set.filter(matricula__retiromatricula__isnull=True).count() < self.cupo:
                return self.cupo - self.materiaasignada_set.filter(matricula__retiromatricula__isnull=True).count()
            return 0

    def cerrar_disponible(self):
        return not self.materiaasignada_set.filter(cerrado=False).exists()

    def tiene_clases(self):
        return self.lecciones().count() > 0

    def cantidad_clases(self):
        return self.clase_set.filter(activo=True).count()

    def profesores_materia(self):
        return self.profesormateria_set.all().order_by('id')

    def profesoresficticios_materia(self):
        return self.profesorficticiomateria_set.all().order_by('id')

    def profesores_materia_dia(self, fecha):
        if self.profesormateria_set.filter(desde__lte=fecha, hasta__gte=fecha, tipoprofesor__id=TIPO_DOCENTE_TEORIA, principal=True).exists():
            return self.profesormateria_set.filter(desde__lte=fecha, hasta__gte=fecha, tipoprofesor__id=TIPO_DOCENTE_TEORIA, principal=True)[0]
        return None

    def profesores(self):
        return ", ".join([x.profesor.persona.nombre_completo_inverso() for x in self.profesores_materia()])

    def horario(self):
        if self.clase_set.filter(activo=True).exists():
            return self.clase_set.filter(activo=True).order_by('dia')
        return None

    def horario_asignado(self):
        if self.clase_set.filter(activo=True).exists():
            return self.clase_set.filter(activo=True)[0]
        return None

    def horarios_asignados(self):
        if self.clase_set.filter(activo=True).exists():
            return self.clase_set.filter(activo=True).distinct('turno')
        return None

    def clases_informacion(self):
        return ["%s - %s a %s - (%s al %s) - %s" % (x.dia_semana(), x.turno.comienza.strftime('%I:%M %p'), x.turno.termina.strftime('%I:%M %p'), x.inicio.strftime('%d-%m-%Y'), x.fin.strftime('%d-%m-%Y'), x.aula.nombre) for x in self.clase_set.filter(activo=True).order_by('dia', 'turno__comienza')]

    def clases_informacion_simple(self):
        return ["%s - %s a %s - (%s al %s)" % (x.dia_semana(), x.turno.comienza.strftime('%I:%M %p'), x.turno.termina.strftime('%I:%M %p'), x.inicio.strftime('%d-%m-%Y'), x.fin.strftime('%d-%m-%Y')) for x in self.clase_set.filter(activo=True).order_by('dia', 'turno__comienza')]

    def clases_informacion_simple_mobile(self):
        clases = [
            "%s - %s a %s" % (
                x.dia_semana(),
                x.turno.comienza.strftime('%I:%M %p'),
                x.turno.termina.strftime('%I:%M %p')
            )
            for x in self.clase_set.filter(activo=True).order_by('dia', 'turno__comienza')
        ]
        return "; ".join(clases) if clases else ""

    def aulas_rep(self):
        aulas = []
        lista = Aula.objects.filter(clase__materia=self, clase__activo=True).distinct().order_by('capacidad')
        if lista:
            for a in lista:
                aulas.append(a.nombre)
            return ",".join(aulas)
        else:
            aulas.append("SIN AULAS CONFIGURADAS")
            return ",".join(aulas)

    def dias_programados(self):
        dias_lista = []
        for dia in self.clase_set.filter(activo=True).order_by('dia', 'turno__comienza'):
            dia_nombre = dia.dia_semana()[0:3].__str__()
            if dia_nombre not in dias_lista:
                dias_lista.append(dia_nombre)
        diassemana = ",".join(dias_lista)
        return "[" + diassemana + "]"

    def profesor_principal(self):
        if self.profesormateria_set.filter(principal=True).exists():
            return self.profesormateria_set.filter(principal=True)[0].profesor
        return None

    def profesor_principal_planificacion(self):
        if self.nivel.modalidad.id == 3:
            if self.profesormateria_set.filter(planifica=True).exists():
                return self.profesormateria_set.filter(planifica=True)[0].profesor
            return None
        else:
            if self.profesormateria_set.filter(principal=True).exists():
                return self.profesormateria_set.filter(principal=True)[0].profesor
            return None

    def profesor_materia_principal(self):
        if self.profesormateria_set.filter(principal=True).exists():
            return self.profesormateria_set.filter(principal=True)[0]
        return None

    def es_profesor_materia_principal(self, profesor):
        return self.profesormateria_set.filter(profesor=profesor)[0].principal

    def es_profesor_materia_planifica(self, profesor):
        if self.nivel.modalidad.id == 3:
            return self.profesormateria_set.filter(profesor=profesor)[0].planifica
        else:
            return self.es_profesor_materia_principal(profesor)

    def puede_editar_materia(self, profesor):
        principal = self.profesormateria_set.filter(profesor=profesor)[0]
        if (principal.materia.nivel.modalidad.id != 3 and principal.principal) or (not principal.principal and not profesor.distributivohoras(principal.materia.nivel.periodo).dedicacion.id == 4 and principal.materia.nivel.modalidad.id == 3):
            return True
        return False

    def profesor_actual(self):
        hoy = datetime.now().date()
        if self.profesormateria_set.filter(desde__lte=hoy, hasta__gte=hoy).exists():
            return self.profesormateria_set.filter(desde__lte=hoy, hasta__gte=hoy)[0]
        return self.profesormateria_set.all()[0]

    def nombre_completo(self):
        return self.asignatura.nombre + " - [" + (self.identificacion if self.identificacion else "###") + "]" + (' - ' + self.paralelomateria.nombre if self.paralelomateria else '') + " - [" + (str(self.id)) + "]"

    def nombre_simple(self):
        return self.asignatura.nombre + " - [" + (self.identificacion if self.identificacion else "###") + "]" + " - [" + (str(self.id)) + "]"

    def nombre_horario(self):
        return self.asignatura.nombre + " - [" + (self.identificacion if self.identificacion else "###") + "] " + (' - ' + self.paralelomateria.nombre if self.paralelomateria else '') + " (" + self.inicio.strftime('%d-%m-%Y') + " al " + self.fin.strftime('%d-%m-%Y') + ")"

    def asignados_a_esta_materia(self):
        return self.materiaasignada_set.all().order_by('matricula__inscripcion__persona')

    def asignados_a_esta_materia_por_id(self):
        return self.materiaasignada_set.all().order_by('id')

    def asignados_a_esta_materia_sinretirados(self):
        return self.materiaasignada_set.filter(materiaasignadaretiro__isnull=True).distinct().order_by('matricula__inscripcion__persona')

    def cantidad_asignados_a_esta_materia_sinretirados(self):
        return self.materiaasignada_set.filter(materiaasignadaretiro__isnull=True).distinct().count()

    def cantidad_matriculas_materia(self):
        return self.materiaasignada_set.all().count()

    def tiene_matriculas(self):
        return self.materiaasignada_set.exists()

    def lecciones(self):
        return LeccionGrupo.objects.filter(lecciones__clase__materia=self).order_by('fecha', 'horaentrada')

    def lecciones_individuales(self):
        return Leccion.objects.filter(clase__materia=self).order_by('lecciongrupo__fecha', 'lecciongrupo__horaentrada')

    def mis_lecciones(self, profesor):
        return LeccionGrupo.objects.filter(lecciones__clase__materia=self, profesor=profesor).order_by('fecha', 'horaentrada')

    def syllabus_malla(self):
        if self.asignaturamalla:
            return
        return None

    def syllabus(self):
        if Archivo.objects.filter(materia=self, tipo_id=ARCHIVO_TIPO_SYLLABUS).exists():
            return Archivo.objects.filter(materia=self, tipo_id=ARCHIVO_TIPO_SYLLABUS).order_by('-id')[0]
        return None

    def deber(self):
        if Archivo.objects.filter(materia=self, tipo_id=ARCHIVO_TIPO_DEBERES).exists():
            return Archivo.objects.filter(materia=self, tipo_id=ARCHIVO_TIPO_DEBERES).distinct('lecciongrupo')
        return None

    def en_fecha(self):
        return self.inicio <= datetime.now().date() <= self.fin

    def pasada_fecha(self):
        return datetime.now().date() > self.fin

    def pueden_evaluar_docentes(self, proceso):
        if proceso.activado:
            if proceso.rangoactivacion:
                dias = proceso.diasactivacion
                if datetime.now().date() >= date(self.fin.year, self.fin.month, self.fin.day) - timedelta(days=dias):
                    return True
            else:
                return True
        return False

    def tiene_calificaciones(self):
        return self.materiaasignada_set.filter(notafinal__gt=0).exists()

    def cerrar(self):
        for ma in self.materiaasignada_set.all():
            ma.cerrado = True
            ma.save(True)
            ma.actualiza_estado()
        self.cerrado = True
        self.fechacierre = datetime.now().date()
        self.save()

    def tiene_horario(self):
        return self.clase_set.exists()

    def horarios(self):
        return self.clase_set.filter(activo=True).order_by('inicio', 'dia', 'turno__comienza')

    def mi_carrera(self):
        if self.nivel.carrera:
            return self.nivel.carrera
        elif self.asignaturamalla:
            return self.asignaturamalla.malla.carrera
        return None

    def mi_malla(self):
        if self.nivel.malla:
            return self.nivel.malla
        elif self.asignaturamalla:
            return self.asignaturamalla.malla
        return None

    def mi_alias(self):
        return self.nivel.periodo.nombre.strip() + "-" + self.carrera.alias.strip() + "-" + (str(self.asignaturamalla.nivelmalla.id) if self.asignaturamalla else "M") + "-" + str(self.asignatura.id) + "-" + str(self.paralelomateria.id)

    def actualiza_identificacion(self):
        self.identificacion = self.nivel.periodo.nombre.strip() + "-" + self.carrera.alias.strip() + "-" + (str(self.asignaturamalla.nivelmalla.id) if self.asignaturamalla else "M") + "-" + str(self.id) + "-" + str(self.nivel.id)
        self.save()

    def recalcularmateria(self):
        for materiaasignada in self.materiaasignada_set.all():
            modeloevaluativomateria = materiaasignada.materia.modeloevaluativo
            local_scope = {}
            exec(modeloevaluativomateria.logicamodelo, globals(), local_scope)
            calculo_modelo_evaluativo = local_scope['calculo_modelo_evaluativo']
            calculo_modelo_evaluativo(materiaasignada)
            materiaasignada.notafinal = null_to_numeric(materiaasignada.notafinal, modeloevaluativomateria.notafinaldecimales)
            if materiaasignada.notafinal > modeloevaluativomateria.notamaxima:
                materiaasignada.notafinal = modeloevaluativomateria.notamaxima
            materiaasignada.save()
            encurso = True
            for campomodelo in modeloevaluativomateria.campos().filter(actualizaestado=True):
                if materiaasignada.valor_nombre_campo(campomodelo.nombre) > 0:
                    encurso = False
            if not encurso:
                materiaasignada.actualiza_estado()
            else:
                materiaasignada.estado_id = NOTA_ESTADO_EN_CURSO
                materiaasignada.save()

    def recalcularmateriaproyectosgrado(self):
        for materiaasignada in self.materiaasignada_set.all():
            modeloevaluativomateria = materiaasignada.materia.modeloevaluativo
            local_scope = {}
            exec(modeloevaluativomateria.logicamodelo, globals(), local_scope)
            calculo_modelo_evaluativo = local_scope['calculo_modelo_evaluativo']
            calculo_modelo_evaluativo(materiaasignada)
            materiaasignada.notafinal = null_to_numeric(materiaasignada.notafinal,
                                                        modeloevaluativomateria.notafinaldecimales)
            if materiaasignada.notafinal > modeloevaluativomateria.notamaxima:
                materiaasignada.notafinal = modeloevaluativomateria.notamaxima
            materiaasignada.estado_id = NOTA_ESTADO_EN_CURSO
            materiaasignada.save()

    def cronogramacalificaciones(self):
        if self.cronogramaevaluacionmodelo_set.filter(nivel=self.nivel).exists():
            return self.cronogramaevaluacionmodelo_set.filter(nivel=self.nivel)[0]
        elif CronogramaEvaluacionModelo.objects.filter(nivel=self.nivel, modelo=self.modeloevaluativo, materias__isnull=True).order_by('id').exists():
            return CronogramaEvaluacionModelo.objects.filter(nivel=self.nivel, modelo=self.modeloevaluativo, materias__isnull=True).order_by('id')[0]
        return None

    def promedio_nota_general(self):
        return null_to_numeric(self.asignados_a_esta_materia_sinretirados().aggregate(valor=Avg('notafinal'))['valor'], 2)

    def promedio_asistencia_general(self):
        return null_to_numeric(self.asignados_a_esta_materia_sinretirados().aggregate(valor=Avg('asistenciafinal'))['valor'], 2)

    def es_nivelacion(self):
        if self.asignaturamalla:
            return self.asignaturamalla.nivelmalla.id == 0
        return False

    def es_ingles_intensivo(self):
        if self.intensivo and self.asignatura.id in [4311, 4312, 4313, 4316, 4317, 4318, 4319, 4320]:
            return True

    def cantidad_matriculas_mora(self):
        return self.materiaasignada_set.filter(matricula__inscripcion__rubro__cancelado=False, matricula__inscripcion__rubro__fechavence__lt=datetime.now().date()).distinct().count()

    def cantidad_retirados(self):
        return self.materiaasignada_set.filter(materiaasignadaretiro__isnull=False).distinct().count()

    def mi_nivelmalla(self):
        if self.asignaturamalla:
            return self.asignaturamalla.nivelmalla
        return None

    def tiene_planificacion(self):
        return self.planificacionmateria_set.exists()

    def mi_planificacion(self):
        if self.tiene_planificacion():
            return self.planificacionmateria_set.all()[0]
        return None

    def mi_planificacion_periodo(self, periodo):
        if self.tiene_planificacion():
            return self.planificacionmateria_set.all()[0]
        return None

    def mi_planificacion_coordinador(self):
        if self.tiene_planificacion():
            return self.planificacionmateria_set.filter()[0]
        return None

    def tiene_planificacion_aprobada(self):
        return self.planificacionmateria_set.filter(aprobado=True).exists()

    def cantidad_solicitudes_pendientes(self):
        return self.solicitudtutoria_set.filter(pendiente=True).count()

    def cantidad_tutoriasmateria_programadas(self):
        hoy = datetime.now()
        self.tutoriamateria_set.filter(
            Q(fecha__gt=hoy.date()) | Q(fecha=hoy.date(), hora__gt=hoy.time())).distinct().count()
        return self.tutoriamateria_set.all().distinct().count()

    def cantidad_solicitudes_realizadas(self):
        return self.tutoriamateria_set.filter(cerrado=True).count()

    def tiene_tutoria_programada(self):
        hoy = datetime.now()
        return self.tutoriamateria_set.filter(Q(fecha__gt=hoy.date()) | Q(fecha=hoy.date(), hora__gt=hoy.time())).distinct().exists()

    def proxima_tutoria_programada(self):
        hoy = datetime.now()
        return self.tutoriamateria_set.filter(Q(fecha__gt=hoy.date()) | Q(fecha=hoy.date(), hora__gt=hoy.time())).distinct().order_by('fecha', 'hora')[0]

    def tutorias(self):
        return self.tutoriamateria_set.all()

    def practica(self):
        return self.practicamateria_set.all()

    def materia_nombre_planificada(self):
        return u'%s - %s - %s - [%s]' % (self.nombre_completo(), self.profesor_principal_planificacion() if self.profesor_principal_planificacion() else '', self.nivel.paralelo, self.id)

    def puede_cambiar_fechas(self):
        for profesores in self.profesores_materia():
            distributivo = profesores.profesor.distributivohoras(self.nivel.periodo)
            if null_to_text(distributivo.codigocontrato) == "":
                return False
        return True

    def tipo_origen(self):
        return 1

    def tiene_solicitud_activa(self):
        ct = ContentType.objects.get_for_model(Materia)
        return SolicitudCambio.objects.filter(
            content_type=ct,
            object_id=self.id
        ).exclude(estado__in=[4,5]).exists()

    def solicitud_activa(self):
        ct = ContentType.objects.get_for_model(Materia)
        return SolicitudCambio.objects.filter(
            content_type=ct,
            object_id=self.id
        ).exclude(estado__in=[4,5]).first()

    def solicitud_rechazada(self):
        ct = ContentType.objects.get_for_model(Materia)
        return SolicitudCambio.objects.filter(
            content_type=ct,
            object_id=self.id,
            estado=5
        ).order_by('-id').first()  # la más reciente

    def ultima_solicitud(self):
        ct = ContentType.objects.get_for_model(Materia)
        return SolicitudCambio.objects.filter(
            content_type=ct,
            object_id=self.id
        ).order_by('-id').first()

    def puede_editar_distributivo(self):

        # Verificar que esté aprobado financieramente
        if not self.nivel.aprobadofinanciero:
            return False  # No se puede editar si no está aprobado financieramente

        # Obtener la solicitud activa
        solicitud = self.solicitud_activa()

        # Si no hay una solicitud activa, no se puede editar
        if not solicitud:
            return False

        # La solicitud debe estar en estado 'Desbloqueo' (3)
        if solicitud.estado != 3:
            return False

        # No debe estar bloqueado
        if self.bloqueado:
            return False

        # Si cumplió todas las condiciones, se puede editar
        return True

    def save(self, *args, **kwargs):
        self.identificacion = null_to_text(self.identificacion)
        if not self.id:
            self.fechafinasistencias = self.fin
        self.carrera = self.mi_carrera()
        self.malla = self.mi_malla()
        self.alias = self.mi_alias()
        super(Materia, self).save(*args, **kwargs)


class TipoProfesor(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")

    class Meta:
        verbose_name_plural = u"Tipos de Profesores"
        ordering = ['id']
        unique_together = ('nombre',)

    def __str__(self):
        return u'%s' % self.nombre

    def es_principal(self):
        return self.id == TIPO_DOCENTE_TEORIA

    def es_practica(self):
        return self.id == TIPO_DOCENTE_PRACTICA

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoProfesor, self).save(*args, **kwargs)



class TipoMatricula(ModeloBase):
    nombre = models.CharField(default='', max_length=50, verbose_name=u'Nombre')
    codigosniese = models.CharField(max_length=15, default='', verbose_name=u'Codigo Sniese')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de Matriculas"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigosniese = null_to_text(self.codigosniese)
        super(TipoMatricula, self).save(*args, **kwargs)


class Matricula(ModeloBase):
    nivel = models.ForeignKey(Nivel, verbose_name=u"Nivel", on_delete=models.CASCADE)
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u"Inscripción", on_delete=models.CASCADE)
    becado = models.BooleanField(default=False, verbose_name=u"Becado")
    becaexterna = models.BooleanField(default=False, verbose_name=u"Beca externa")
    iece = models.BooleanField(default=False, verbose_name=u"Beca IECE")
    beneficiomonetario = models.BooleanField(default=False, verbose_name=u"Beneficio monetario")
    tipomatricula = models.ForeignKey(TipoMatricula, null=True, blank=True, verbose_name=u"Tipo de matricula", on_delete=models.CASCADE)
    porcientobeca = models.FloatField(default=0, verbose_name=u"% de Beca")
    montobeca = models.FloatField(default=0, verbose_name=u"Monto Beca")
    montomensual = models.FloatField(default=0, verbose_name=u"Monto mensual")
    cantidadmeses = models.IntegerField(default=1, verbose_name=u'Cantidad de meses')
    montobeneficio = models.FloatField(default=0, verbose_name=u"Beneficio economico")
    observaciones = models.TextField(default='', max_length=1000, verbose_name=u"Observaciones")
    fecha = models.DateField(null=True, blank=True, verbose_name=u"Fecha")
    hora = models.TimeField(null=True, blank=True, verbose_name=u"Hora")
    fechatope = models.DateField(null=True, blank=True, verbose_name=u"Fecha límite de cancelación")
    formalizada = models.BooleanField(default=False, verbose_name=u"Formalizada")
    promedionotas = models.FloatField(default=0, verbose_name=u"Promedio calificaciones")
    promedioasistencias = models.FloatField(default=0, verbose_name=u"Promedio asistencia")
    totalhoras = models.FloatField(default=0, verbose_name=u'Total de horas')
    totalcreditos = models.FloatField(default=0, verbose_name=u'Total de créditos')
    aprobadofinanzas = models.BooleanField(default=False, verbose_name=u"Beca aprobada Finanzas")
    permiteanular = models.BooleanField(default=False, verbose_name=u"Permite anular con pagos")
    promovido = models.BooleanField(default=False, verbose_name=u"Promovido")
    nivelmalla = models.ForeignKey(NivelMalla, null=True, blank=True, verbose_name=u"Nivel malla", on_delete=models.CASCADE)
    paraleloprincipal = models.ForeignKey(ParaleloMateria, null=True, blank=True, verbose_name=u"Paralelo principal", on_delete=models.CASCADE)
    materiasregulares = models.IntegerField(default=0, verbose_name=u'Cantidad de materias regulares')
    materiasmodulos = models.IntegerField(default=0, verbose_name=u'Cantidad de materias modulos')
    cerrada = models.BooleanField(default=False, verbose_name=u"Cerrada")
    tipoinscripcion = models.ForeignKey(TipoInscripcion, blank=True, null=True, verbose_name=u'Tipo de Inscripción', on_delete=models.CASCADE)
    resolucionconsejo = models.TextField(blank=True, null=True, verbose_name=u'Resolución de consejo')
    bloqueo = models.BooleanField(default=False, verbose_name=u"Bloqueo")
    estadomatricula = models.IntegerField(choices=ESTADOS_MATRICULA, default=2)
    personamatriculo = models.ForeignKey(Persona, null=True, verbose_name=u'Persona quien matricula', on_delete=models.CASCADE)
    tienepagominimo = models.BooleanField(default=False, verbose_name=u"Tiene pago minimo")

    def __str__(self):
        return u'%s %s %s' % (self.inscripcion, (self.nivel if self.nivel else ""), self.observaciones)

    class Meta:
        verbose_name_plural = u"Matriculas"
        ordering = ['inscripcion__persona', '-fecha']
        unique_together = ('nivel', 'inscripcion',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        if len(q.split(' ')) == 2:
            qq = q.split(' ')
            return eval(("Matricula.objects.filter(inscripcion__persona__apellido1__contains='%s', inscripcion__persona__apellido2__contains='%s')" % (qq[0], qq[1])) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))
        return eval(("Matricula.objects.filter(Q(inscripcion__persona__nombre1__contains='%s') | Q(inscripcion__persona__apellido1__contains='%s') | Q(inscripcion__persona__apellido2__contains='%s') | Q(inscripcion__persona__cedula__contains='%s')| Q(id=id_search('%s')))" % (q, q, q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return (self.inscripcion.persona.cedula if self.inscripcion.persona.cedula else self.inscripcion.persona.pasaporte) + " - " + self.nivel.inicio.strftime('%d-%m-%Y') + " - " + self.inscripcion.persona.nombre_completo_inverso() + ' - ' + str(self.id)

    def clases_horario(self, dia, turno, periodo):
        return Clase.objects.filter(dia=dia, activo=True, turno=turno, materia__nivel__periodo=periodo, materia__materiaasignada__matricula=self)

    def es_regular(self):
        return self.fecha <= self.nivel.fechatopematricula

    def es_extraordinaria(self):
        return self.nivel.fechatopematricula < self.fecha <= self.nivel.fechatopematriculaex

    def es_especial(self):
        return self.nivel.fechatopematriculaex < self.fecha <= self.nivel.fechatopematriculaes

    def es_otra(self):
        return self.fecha > self.nivel.fechatopematriculaes

    def pago_matricula(self):
        if self.rubromatricula_set.exists():
            return self.rubromatricula_set.all()[0].rubro.cancelado
        return False

    def pago_inscripcion(self):
        if RubroInscripcion.objects.filter(inscripcion=self).exists():
            return RubroInscripcion.objects.filter(inscripcion=self)[0].rubro.cancelado
        return True

    def pago_1racuota(self):
        if self.rubrocuota_set.filter(cuota=1).exists():
            if not self.rubrocuota_set.all()[0].rubro.cancelado:
                return False
        return True

    def tiene_deuda_vencida_cuotas(self, cuotas):
        return self.rubrocuota_set.filter(rubro__cancelado=False, rubro__fechavence__lt=datetime.now().date()).count() >= cuotas

    def en_fecha(self):
        return self.nivel.periodo.fin >= datetime.now().date() >= self.nivel.periodo.inicio

    def porciento_materias_seleccionadas(self):
        minivel = self.inscripcion.mi_nivel().nivel
        cantidad_materias_nivel = self.inscripcion.mi_malla().asignaturamalla_set.filter(nivelmalla=minivel).count()
        if cantidad_materias_nivel:
            return null_to_numeric((self.cantidad_materias() / float(cantidad_materias_nivel)) * 100.0, 2)
        return 0

    def retirado(self) -> bool:
        return self.retiromatricula_set.exists()

    def retiro_ultimo(self):
        return self.retiromatricula_set.order_by('-fecha', '-id').first()

    def materias_profesor(self, profesor):
        return ProfesorMateria.objects.filter(profesor=profesor, materia__materiaasignada__matricula=self).distinct()

    def cantidad_creditos(self):
        return null_to_numeric(self.materiaasignada_set.filter(validacreditos=True).exclude(materiaasignadaretiro__valida=False).aggregate(valor=Sum('creditos'))['valor'], 4)

    def permite_agregaciones(self):
        return self.nivel.periodo.limite_agregacion >= datetime.now().date() >= self.nivel.periodo.inicio_agregacion

    def ya_cobrada(self):
        return RubroMatricula.objects.filter(matricula=self).count() > 0

    def rubrosmatricula(self):
        return null_to_numeric(self.inscripcion.rubro_set.filter(Q(rubrocuota__matricula=self) | Q(rubromatricula__matricula=self) | Q(rubrootromatricula__matricula=self) | Q(rubroagregacion__materiaasignada__matricula=self)).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def cuota1_cancelada(self):
        cuotauno = self.nivel.pagonivel_set.get(tipo=1)
        if self.rubrocuota_set.filter(cuota=1, rubro__fechavence=cuotauno.fecha).exists():
            fechavence = cuotauno.fecha
            fechavence += timedelta(7)
            if self.rubrocuota_set.filter(cuota=1).exists():
                cuota = self.rubrocuota_set.get(cuota=1)
            else:
                return True
            if fechavence >= datetime.now().date():
                return True
            elif not cuota.rubro.cancelado:
                return False
            return True
        else:
            if self.rubrocuota_set.filter(cuota=1).exists():
                cuota = self.rubrocuota_set.get(cuota=1)
                fechavence = cuota.rubro.fechavence
                fechavence += timedelta(7)
            else:
                return True
            if datetime.now().date() >= fechavence:
                if cuota.rubro.cancelado:
                    return True
                else:
                    return False
            else:
                return True

    def tiene_rubros_cuota_pagados(self):
        return RubroCuota.objects.filter(matricula=self, rubro__pago__isnull=False).exists()

    def tiene_rubros_pagados(self):
        if RubroMateria.objects.filter(materiaasignada__matricula=self, rubro__pago__isnull=False).exists():
            return True
        if RubroCuota.objects.filter(matricula=self, rubro__pago__isnull=False).exists():
            return True
        if RubroMatricula.objects.filter(matricula=self, rubro__pago__isnull=False).exists():
            return True
        if RubroOtroMatricula.objects.filter(matricula=self, rubro__pago__isnull=False).exists():
            return True
        if RubroDerecho.objects.filter(materiaasignada__matricula=self, rubro__pago__isnull=False).exists():
            return True
        if RubroAgregacion.objects.filter(materiaasignada__matricula=self, rubro__pago__isnull=False).exists():
            return True
        return False

    def solo_pago_notacredito(self):
        if RubroMateria.objects.filter(materiaasignada__matricula=self).exists():
            for r in RubroMateria.objects.filter(materiaasignada__matricula=self):
                if r.rubro.solo_pago_notacredito():
                    return True
        if RubroCuota.objects.filter(matricula=self).exists():
            for r in RubroCuota.objects.filter(matricula=self):
                if r.rubro.solo_pago_notacredito():
                    return True
        if RubroMatricula.objects.filter(matricula=self).exists():
            for r in RubroMatricula.objects.filter(matricula=self):
                if r.rubro.solo_pago_notacredito():
                    return True
        if RubroOtroMatricula.objects.filter(matricula=self).exists():
            for r in RubroOtroMatricula.objects.filter(matricula=self):
                if r.rubro.solo_pago_notacredito():
                    return True
        if RubroDerecho.objects.filter(materiaasignada__matricula=self).exists():
            for r in RubroDerecho.objects.filter(materiaasignada__matricula=self):
                if r.rubro.solo_pago_notacredito():
                    return True
        if RubroAgregacion.objects.filter(materiaasignada__matricula=self).exists():
            for r in RubroDerecho.objects.filter(materiaasignada__matricula=self):
                if r.rubro.solo_pago_notacredito():
                    return True
        return False

    def eliminar_rubros_matricula(self):
        if self.formalizada is False:
            for rubro in RubroMateria.objects.filter(materiaasignada__matricula=self):
                r = rubro.rubro
                rubro.delete()
                r.verifica_rubro_otro(RUBRO_OTRO_ARANCEL_ID)
            for rubro in RubroCuota.objects.filter(matricula=self):
                r = rubro.rubro
                rubro.delete()
                r.verifica_rubro_otro(RUBRO_OTRO_ARANCEL_ID)
            for rubro in RubroMatricula.objects.filter(matricula=self):
                r = rubro.rubro
                rubro.delete()
                r.verifica_rubro_otro(RUBRO_OTRO_MATRICULA_ID)
            for rubro in RubroOtroMatricula.objects.filter(matricula=self):
                r = rubro.rubro
                rubro.delete()
                r.verifica_rubro_otro(RUBRO_OTRO_OTROS_EDUCATIVOS_ID)
            for rubro in RubroDerecho.objects.filter(materiaasignada__matricula=self):
                r = rubro.rubro
                rubro.delete()
                r.verifica_rubro_otro(RUBRO_OTRO_DERECHOS_ESPECIES_ID)
            for rubro in RubroAgregacion.objects.filter(materiaasignada__matricula=self):
                r = rubro.rubro
                rubro.delete()
                r.verifica_rubro_otro(RUBRO_OTRO_ARANCEL_ID)

    def eliminar_rubros_matricula_total(self):
        if self.formalizada is False:
            for rubro in RubroMateria.objects.filter(materiaasignada__matricula=self):
                r = rubro.rubro
                r.delete()
            for rubro in RubroCuota.objects.filter(matricula=self):
                r = rubro.rubro
                r.delete()
            for rubro in RubroMatricula.objects.filter(matricula=self):
                r = rubro.rubro
                r.delete()
            for rubro in RubroOtroMatricula.objects.filter(matricula=self):
                r = rubro.rubro
                r.delete()
            for rubro in RubroDerecho.objects.filter(materiaasignada__matricula=self):
                r = rubro.rubro
                r.delete()
            for rubro in RubroAgregacion.objects.filter(materiaasignada__matricula=self):
                r = rubro.rubro
                r.delete()

    def eliminar_rubros_cuota(self):
        if self.formalizada is False:
            for rubro in RubroCuota.objects.filter(matricula=self):
                r = rubro.rubro
                rubro.delete()
                r.verifica_rubro_otro(RUBRO_OTRO_ARANCEL_ID)

    def precio_sugerido(self):
        return 0

    def tiene_evaluacion(self):
        return null_to_numeric(self.materiaasignada_set.aggregate(valor=Sum('notafinal'))['valor']) > 0

    def nivel_cerrado(self):
        return self.nivel.cerrado

    def tiene_pago(self):
        if Pago.objects.filter(rubro__rubrocuota__matricula=self).exists():
            return True
        if Pago.objects.filter(rubro__rubromatricula__matricula=self).exists():
            return True
        if Pago.objects.filter(rubro__rubrootromatricula__matricula=self).exists():
            return True
        if Pago.objects.filter(rubro__rubroagregacion__materiaasignada__matricula=self).exists():
            return True
        if Pago.objects.filter(rubro__rubroderecho__materiaasignada__matricula=self).exists():
            return True
        if Pago.objects.filter(rubro__rubromateria__materiaasignada__matricula=self).exists():
            return True
        return False

    def tiene_rubros(self):
        if self.rubrocuota_set.filter(matricula=self).exists():
            return True
        if self.rubromatricula_set.filter(matricula=self).exists():
            return True
        if self.rubrootromatricula_set.filter(matricula=self).exists():
            return True
        if RubroAgregacion.objects.filter(materiaasignada__matricula=self).exists():
            return True
        if RubroDerecho.objects.filter(materiaasignada__matricula=self).exists():
            return True
        if RubroMateria.objects.filter(materiaasignada__matricula=self).exists():
            return True
        return False

    def tiene_pago_encuota(self):
        return Pago.objects.filter(rubro__rubrocuota__matricula=self).exists()

    def tiene_pago_enmatricula(self):
        return Pago.objects.filter(rubro__rubromatricula__matricula=self).exists()

    def cantidad_materias(self):
        return self.materiaasignada_set.count()

    def materias(self):
        return self.materiaasignada_set.all()

    def materias_periodo(self):
        return Materia.objects.filter(materiaasignada__matricula=self).distinct()

    def materias_periodo_sin_ingles(self):
        return self.materiaasignada_set.all().exclude(asignaturareal__id__in=[4311, 4312, 4313, 4316, 4317, 4318, 4319, 4320])

    def materias_aprobadas_sin_ingles(self):
        return self.materiaasignada_set.filter(estado_id=NOTA_ESTADO_APROBADO).exclude(asignaturareal__id__in=[4311, 4312, 4313, 4316, 4317, 4318, 4319, 4320])

    def retiro_academico(self, tipo, motivo, newfile):
        retiro = RetiroMatricula(matricula=self,
                                 fecha=datetime.now(),
                                 subtipo=tipo,
                                 archivo=newfile,
                                 motivo=motivo)
        retiro.save()
        for materia in self.materiaasignada_set.all():
            pasarecord = False
            if materia.homologada() or materia.convalidada():
                pasarecord = True
            materia.cerrado = True
            materia.fechacierre = datetime.now().date()
            if not materia.materiaasignadaretiro_set.exists():
                retiromateria = MateriaAsignadaRetiro(materiaasignada=materia,
                                                      motivo='RETIRO DE MATRICULA',
                                                      valida=pasarecord,
                                                      fecha=retiro.fecha)
                retiromateria.save()
            materia.save()
            materia.actualiza_estado()

    def calcular_rubros_matricula(self):
        from ctt.adm_calculofinanzas import calcular_rubros
        calcular_rubros(self)


    def calcular_arancel_posgrado(self):
        from ctt.adm_calculofinanzas import calculo_arancel_posgrado
        calculo_arancel_posgrado(self)

    def agregacion(self, materiaasignada, tiponominacion):
        from ctt.adm_calculofinanzas import calcular_agregacion
        calcular_agregacion(self, materiaasignada.asignaturareal, tiponominacion)

    def eliminar_materia(self, materiaasignada, persona):
        registro = AgregacionEliminacionMaterias(matricula=self,
                                                 agregacion=False,
                                                 asignatura=materiaasignada.materia.asignatura,
                                                 responsable=persona,
                                                 fecha=datetime.now().date(),
                                                 creditos=materiaasignada.materia.creditos,
                                                 nivelmalla=materiaasignada.materia.nivel.nivelmalla if materiaasignada.materia.nivel.nivelmalla else None,
                                                 matriculas=materiaasignada.matriculas)
        registro.save()
        from ctt.adm_calculofinanzas import calculo_eliminacionmateria
        calculo_eliminacionmateria(materiaasignada, persona, 'ELIMINACION DE MATERIA')
        if materiaasignada.materia.asignatura.id in [4311, 4312, 4313, 4316, 4317, 4318, 4319, 4320]:
            if RubroAgregacion.objects.filter(materiaasignada=materiaasignada).exists():
                rubroagregacion = RubroAgregacion.objects.get(materiaasignada=materiaasignada)
                rubro = Rubro.objects.get(pk=rubroagregacion.rubro_id)
                rubroagregacion.delete()
                rubro.delete()
        materiaasignada.delete()

    def total_rubros_matricula(self):
        return null_to_numeric(self.inscripcion.rubro_set.filter(rubromatricula__matricula=self).aggregate(valor=Sum('valor'))['valor'], 2)

    def total_rubros_cuota(self):
        return null_to_numeric(self.inscripcion.rubro_set.filter(rubrocuota__matricula=self).aggregate(valor=Sum('valor'))['valor'], 2)

    def total_rubros_otrosmatricula(self):
        return null_to_numeric(self.inscripcion.rubro_set.filter(rubrootromatricula__matricula=self).aggregate(valor=Sum('valor'))['valor'], 2)

    def total_rubros_agregaciones(self):
        return null_to_numeric(self.inscripcion.rubro_set.filter(rubroagregacion__materiaasignada__matricula=self).aggregate(valor=Sum('valor'))['valor'], 2)

    def total_rubros_materia(self):
        return null_to_numeric(self.inscripcion.rubro_set.filter(rubromateria__materiaasignada__matricula=self).aggregate(valor=Sum('valor'))['valor'], 2)

    def pagado_rubros_matricula(self):
        return null_to_numeric(Pago.objects.filter(rubro__rubromatricula__matricula=self, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def pagado_rubros_cuota(self):
        return null_to_numeric(Pago.objects.filter(rubro__rubrocuota__matricula=self, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def pagado_rubros_otrosmatricula(self):
        return null_to_numeric(Pago.objects.filter(rubro__rubrootromatricula__matricula=self, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def pagado_rubros_agregaciones(self):
        return null_to_numeric(Pago.objects.filter(rubro__rubroagregacion__materiaasignada__matricula=self, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def pagado_rubros_materia(self):
        return null_to_numeric(Pago.objects.filter(rubro__rubromateria__materiaasignada__matricula=self, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def costo_materia(self, materiaasignada):
        malla = self.inscripcion.mi_malla()
        if malla.asignaturamalla_set.filter(asignatura=materiaasignada.materia.asignatura).exists():
            return malla.asignaturamalla_set.filter(asignatura=materiaasignada.materia.asignatura)[0].costo
        return 0

    def cantidad_evaluacionestudiantes_total_acreditacion(self):
        return ProfesorMateria.objects.filter(tipoprofesor__id=TIPO_DOCENTE_TEORIA, materia__materiaasignada__matricula=self, materia__materiaasignada__materiaasignadaretiro__isnull=True).distinct().count()

    def cantidad_evaluacionestudiantes_realizada_acreditacion(self, periodo):
        return RespuestaEvaluacionAcreditacion.objects.filter(proceso__periodo=periodo, tipoinstrumento=1, evaluador=self.inscripcion.persona).distinct().count()

    def cantidad_evaluacionestudiantes_restantes_acreditacion(self):
        periodo = self.nivel.periodo
        return self.cantidad_evaluacionestudiantes_total_acreditacion() - self.cantidad_evaluacionestudiantes_realizada_acreditacion(periodo)

    def mis_profesores_acreditacion(self):
        return ProfesorMateria.objects.filter(tipoprofesor__id=TIPO_DOCENTE_TEORIA, materia__materiaasignada__matricula=self, materia__materiaasignada__materiaasignadaretiro__isnull=True).distinct().order_by('-tipoprofesor', 'profesor')

    def cantidad_cuotas(self):
        return self.rubrocuota_set.count()

    def promedio_nota(self):
        return null_to_numeric(self.materiaasignada_set.filter(validapromedio=True).exclude(materiaasignadaretiro__valida=False).aggregate(valor=Avg('notafinal'))['valor'], 2)

    def promedio_asistencias(self):
        return null_to_numeric(self.materiaasignada_set.filter(sinasistencia=False, materiaasignadaretiro__isnull=True).aggregate(valor=Avg('asistenciafinal'))['valor'], 0)

    def promedio_nota_nivelacion(self):
        return null_to_numeric(self.materiaasignada_set.aggregate(valor=Avg('notafinal'))['valor'], 2)

    def promedio_asistencias_nivelacion(self):
        return null_to_numeric(self.materiaasignada_set.aggregate(valor=Avg('asistenciafinal'))['valor'], 0)

    def promedio_nota_periodo(self):
        if self.nivelmalla_id == 0:
            return self.promedio_nota_nivelacion()
        return self.promedio_nota()

    def promedio_asistencia_periodo(self):
        if self.nivelmalla_id == 0:
            return self.promedio_asistencias_nivelacion()
        return self.promedio_asistencias()

    def es_nivelacion(self):
        return self.nivelmalla.id == NIVEL_MALLA_CERO

    def aprobo_nivelacion(self):
        return self.inscripcion.promedio_nota_nivelacion() >= self.inscripcion.nota_minima_nivelacion() and self.inscripcion.promedio_asistencia_nivelacion() >= self.inscripcion.asistenciaminima_minima_nivelacion()

    def cursando_asignatura(self, asignatura):
        return self.materiaasignada_set.filter(Q(materia__asignatura=asignatura) | Q(asignaturareal=asignatura), materia__cerrado=False).exists()

    def tiene_deuda_vencida(self):
        if self.rubromatricula_set.filter(rubro__cancelado=False, rubro__fechavence__lt=datetime.now().date()).exists():
            return True
        elif self.rubrocuota_set.filter(rubro__cancelado=False, rubro__fechavence__lt=datetime.now().date()).exists():
            return True
        elif self.rubrootromatricula_set.filter(rubro__cancelado=False, rubro__fechavence__lt=datetime.now().date()).exists():
            return True
        elif RubroMateria.objects.filter(materiaasignada__matricula=self, rubro__cancelado=False, rubro__fechavence__lt=datetime.now().date()).exists():
            return True
        elif RubroDerecho.objects.filter(materiaasignada__matricula=self, rubro__cancelado=False, rubro__fechavence__lt=datetime.now().date()).exists():
            return True
        elif RubroAgregacion.objects.filter(materiaasignada__matricula=self, rubro__cancelado=False, rubro__fechavence__lt=datetime.now().date()).exists():
            return True
        return False

    def paralelo_principal_materias(self):
        paralelos = []
        for materiaasignada in self.materiaasignada_set.all():
            if materiaasignada.materia.paralelomateria not in paralelos:
                cantidad = self.materiaasignada_set.filter(materia__paralelomateria=materiaasignada.materia.paralelomateria).distinct().count()
                paralelos.append([materiaasignada.materia.paralelomateria, cantidad])
        maximo = 0
        paraleloprincipal = None
        for paralelo in paralelos:
            if paralelo[1] > maximo:
                maximo = paralelo[1]
                paraleloprincipal = paralelo[0]
        return paraleloprincipal

    def mis_fechas_periodo(self):
        if self.nivel.fechacarrareperiodo_set.filter(carrera=self.inscripcion.carrera).exists():
            return self.nivel.fechacarrareperiodo_set.filter(carrera=self.inscripcion.carrera)[0]
        return None

    def turnos_dia(self, dia):
        return Turno.objects.filter(clase__dia=dia, clase__materia__in=Materia.objects.filter(materiaasignada__matricula=self)).distinct()

    def actualiza_tipo_inscripcion(self):
        if self.nivelmalla.id == NIVEL_MALLA_CERO:
            self.tipoinscripcion_id = TIPO_INSCRIPCION_REGULAR
        else:
            # CALCULO TIPO GRATUIDAD
            self.tipoinscripcion_id = TIPO_INSCRIPCION_REGULAR
            if UTILIZA_GRATUIDADES:
                nivel = self.nivelmalla
                malla = self.inscripcion.mi_malla()
                cantidadmateriasnivel = malla.asignaturamalla_set.filter( nivelmalla=nivel).distinct().count()
                cantidadperiodo = self.materiaasignada_set.filter(asignaturamalla__isnull=False).count()
                porciento = (100.0/cantidadmateriasnivel)*cantidadperiodo
                if porciento < PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD:
                    self.tipoinscripcion_id = TIPO_INSCRIPCION_IRREGULAR
        self.save()

    def calcular_costo_materia_posgrado(self, asignatura):
        from ctt.adm_calculofinanzas import costo_materia_posgrado
        return costo_materia_posgrado(self.inscripcion, asignatura, self.nivel)

    def calcular_costo_materia(self, asignatura):
        from ctt.adm_calculofinanzas import costo_materia
        return costo_materia(self.inscripcion, asignatura, self.nivel)

    def mi_promocion(self):
        if self.promocionmatricula_set.exists():
            return self.promocionmatricula_set.all()[0]
        else:
            promocion = PromocionMatricula(matricula=self,
                                           nivelmalla=self.nivelmalla)
            promocion.save()
            return promocion

    def calcular_estado_matricula(self):
        if self.retirado():
            self.estadomatricula = 3
        else:
            if self.materias_periodo_sin_ingles().count() > 0:
                porcentaje = (self.materias_aprobadas_sin_ingles().count() * 100) / (self.materias_periodo_sin_ingles().count())
            else:
                porcentaje = (self.materias_aprobadas_sin_ingles().count() * 100) / 1
            self.estadomatricula = 1 if (porcentaje >= 50) else 2
        self.save()

    def diasinscripcionmatricula(self):
        dias = self.fecha_creacion - self.inscripcion.fecha_creacion
        return int(dias.days)

    def mail_notificacion_parqueadero(self, persona, destino):
        send_mail(subject='NOTIFICACION PARQUEADERO.',
                  html_template='emails/notificacionparqueadero.html',
                  data={'m': self, 'persona': persona, 'destino': destino},
                  recipient_list=[destino])

    def generar_solicitud_prorroga(self, cargoinstitucion, inscripcion, comentario):
        carrera = inscripcion.carrera
        if carrera.posgrado:
            tipo = TipoSolicitudSecretariaDocente.objects.get(pk=41)
        else:
            tipo = TipoSolicitudSecretariaDocente.objects.get(pk=45)
        solicitud = SolicitudSecretariaDocente(fecha=datetime.now().date(),
                                               hora=datetime.now().time(),
                                               inscripcion=self.inscripcion,
                                               tipo=tipo,
                                               descripcion=comentario,
                                               cerrada=False,
                                               responsable=cargoinstitucion.persona,
                                               matricula=self)
        solicitud.save()
        if tipo.requisitostiposolicitudsecretariadocente_set.count() > 0:
            for r in tipo.requisitostiposolicitudsecretariadocente_set.all():
                requisito = RequisitosSolicitudSecretariaDocente(solicitud=solicitud,
                                                                 requisito=r)
                requisito.save()
        if cargoinstitucion.persona:
            historial = HistorialSolicitud(solicitud=solicitud,
                                           fecha=datetime.now(),
                                           persona=solicitud.responsable,
                                           respuesta='')
            historial.save()
        if SOLICITUD_NUMERO_AUTOMATICO:
            if SolicitudSecretariaDocente.objects.filter(numero_tramite__gt=0).exists():
                ultima = SolicitudSecretariaDocente.objects.filter(numero_tramite__gt=0).order_by('-id')[0]
                solicitud.numero_tramite = ultima.numero_tramite + 1
            else:
                solicitud.numero_tramite = 1
            solicitud.save()
        if solicitud.tipo.tiene_costo():
            cantidad = 1
            if PUEDE_ESPECIFICAR_CANTIDAD_SOLICITUD_SECRETARIA:
                cantidad = 1
            if solicitud.tipo.costo_unico:
                valor = null_to_numeric(solicitud.tipo.valor + solicitud.tipo.costo_base, 2)
            else:
                valor = null_to_numeric((solicitud.tipo.valor * cantidad) + solicitud.tipo.costo_base, 2)
            # for p in PeriodoSolicitud.objects.all():
            #     if p.vigente():
            #         periodosolicitud = p.id
            periodosolicitud = Periodo.objects.filter(parasolicitudes=True)[0]
            rubro = Rubro(inscripcion=self.inscripcion,
                          valor=valor,
                          iva_id=TIPO_IVA_0_ID,
                          valortotal=valor,
                          saldo=valor,
                          periodo=periodosolicitud,
                          fecha=datetime.now().date(),
                          fechavence=datetime.now().date())
            rubro.save()
            rubrootro = RubroOtro(rubro=rubro,
                                  tipo_id=RUBRO_OTRO_SOLICITUD_ID,
                                  solicitud=solicitud)
            rubrootro.save()
            rubro.actulizar_nombre(nombre=solicitud.tipo.nombre)
            return True
        return False

    def tiene_seguimiento(self):
        return SeguimientoMatriculado.objects.filter(matricula=self).exists()

    def ultimo_seguimiento(self):
        if self.tiene_seguimiento():
            return SeguimientoMatriculado.objects.filter(matricula=self)[0]
        return None

    def bajoparcial1(self):
        return self.materiaasignada_set.filter(
            evaluaciongenerica__detallemodeloevaluativo__nombre='PARC1',
            evaluaciongenerica__valor__lt=3
        ).distinct().order_by('asignaturareal__nombre')

    def bajoparcial2(self):
        return self.materiaasignada_set.filter(
            evaluaciongenerica__detallemodeloevaluativo__nombre='PARC2',
            evaluaciongenerica__valor__lt=3
        ).distinct().order_by('asignaturareal__nombre')

    def obtener_alertas_activas(self):
        # Obtener alertas estándar abiertas
        alertas_estandar = AsesorSeguimiento.objects.filter(
            inscripcion=self.inscripcion,
            alertas__isnull=False,
            cerrado=False
        ).select_related('alertas')

        # Obtener alertas personalizadas abiertas
        alertas_personalizadas = AsesorSeguimiento.objects.filter(
            inscripcion=self.inscripcion,
            otrasalertas__isnull=False,  # No nulo
            otrasalertas__gt='',  # No vacío
            alertas__isnull=True,  # No tienen ID de alerta estándar
            cerrado=False
        ).values('otrasalertas', 'nivel_riesgo')

        # Combinar ambas listas
        alertas = list(alertas_estandar) + list(alertas_personalizadas)
        return alertas

    def alertas_tiemporeal(self):
        """
        Devuelve una lista de dicts con las alertas estándar
        que SÍ se disparan para la inscripción en el periodo actual.
        """
        alertas_activas = []

        alertas_qs = (
            AlertaSeguimiento.objects
            .filter(
                activo=True,
                logicamodelo__isnull=False
            )
            .exclude(logicamodelo='')
            .order_by('id')
        )

        # Usa select_related si AlertaSeguimiento tiene FK que
        # se usan dentro de alertas_seguimiento()
        # .select_related('…')

        for alerta in alertas_qs:
            try:
                if alerta.alertas_seguimiento(self.inscripcion, self.nivel.periodo):
                    alertas_activas.append({
                        'id_alerta': alerta.id,
                        'nombre_alerta': alerta.nombre,
                        'alerta': alerta,
                    })
            except Exception as e:
                logging.warning(f"[alertas_tiemporeal] Alerta {alerta.id}: {e}")
                continue

        return alertas_activas

    # ------------------------------------------------------------------ #
    # 2) % DE RIESGO GLOBAL (solo catálogo, sin asesor)                  #
    # ------------------------------------------------------------------ #
    def riesgo_total_alertas(self):
        """
        % de riesgo basado EXCLUSIVAMENTE en alertas estándar.
        100 % ⇒ todas las alertas activas del sistema se cumplen.
        """
        universo_qs = (
            AlertaSeguimiento.objects
            .filter(activo=True)
            .exclude(logicamodelo__isnull=True, logicamodelo__exact='')
        )

        riesgo_maximo = (
                universo_qs.aggregate(total=models.Sum('nivel_riesgo'))['total'] or 0
        )
        if riesgo_maximo == 0:
            return 0.0

        riesgo_obtenido = 0
        for alerta in universo_qs:
            try:
                if alerta.alertas_seguimiento(self.inscripcion, self.nivel.periodo):
                    riesgo_obtenido += alerta.nivel_riesgo
            except Exception as e:
                logging.warning(f"[riesgo_total_alertas] Alerta {alerta.id}: {e}")

        return round((riesgo_obtenido / riesgo_maximo) * 100, 2)

    # ------------------------------------------------------------------ #
    # 3) % DE RIESGO SEGÚN SEGUIMIENTO DEL ASESOR                        #
    #    (catálogo + manual; las manuales SÍ cuentan para el 100 %)      #
    # ------------------------------------------------------------------ #
    def calcular_riesgo_total(self, periodo=None):
        """
        100 % ⇒ el asesor ha dejado abiertas TODAS las alertas estándar
                y manuales posibles (y todas se disparan si son de catálogo).

        – Catálogo: se suma nivel_riesgo SOLO si la regla se cumple.
        – Manual:  se suma siempre que esté abierta.
        – Para que el 100 % sea coherente se añaden las manuales al techo.
        """
        if periodo is None:
            periodo = self.nivel.periodo

        # Universo estándar
        universo_std = (
            AlertaSeguimiento.objects
            .filter(activo=True)
            .exclude(logicamodelo__isnull=True, logicamodelo__exact='')
        )
        riesgo_maximo = (
                universo_std.aggregate(total=models.Sum('nivel_riesgo'))['total'] or 0
        )

        # Seguimientos abiertos
        qs = (
            AsesorSeguimiento.objects
            .filter(
                inscripcion=self.inscripcion,
                cerrado=False
            )
            .select_related('alertas')
        )
        if not qs.exists() or riesgo_maximo == 0:
            return 0.0

        ids_std_vistos = set()
        riesgo_obtenido = 0

        for seg in qs:
            try:
                # ---------- Catálogo ----------
                if seg.alertas:
                    aid = seg.alertas_id
                    if aid in ids_std_vistos:
                        continue  # evita duplicados
                    if seg.alertas.alertas_seguimiento(self.inscripcion, periodo):
                        riesgo_obtenido += seg.alertas.nivel_riesgo
                    ids_std_vistos.add(aid)

                # ---------- Manual (otrasalertas) ----------
                elif seg.otrasalertas:
                    nivel = seg.nivel_riesgo or 0
                    riesgo_obtenido += nivel
                    riesgo_maximo   += nivel     # para que cuente en el 100 %
            except Exception as e:
                logging.warning(f"[calcular_riesgo_total] Seg {seg.pk}: {e}")

        return round((riesgo_obtenido / riesgo_maximo) * 100, 2)

    def calcular_riesgo_total_sumado(self, periodo=None):
        """
        Riesgo total que combina:
          1) Alertas estándar (AlertaSeguimiento)
          2) Alertas manuales/no cerradas de AsesorSeguimiento
        El denominador es la suma de los niveles de riesgo de *todas* las alertas
        consideradas (estándar + activas de asesor).
        """
        if periodo is None:
            periodo = self.nivel.periodo

        riesgo_obtenido = 0
        riesgo_maximo = 0

        # -------- 1. Alertas estándar --------
        alertas_std = (
            AlertaSeguimiento.objects
            .filter(activo=True)
            .exclude(logicamodelo__isnull=True, logicamodelo__exact='')
        )
        for a in alertas_std:
            riesgo_maximo += a.nivel_riesgo
            if a.alertas_seguimiento(self.inscripcion, periodo):
                riesgo_obtenido += a.nivel_riesgo

        # -------- 2. Alertas activas de asesor --------
        asesor_qs = AsesorSeguimiento.objects.filter(
            inscripcion=self.inscripcion,
            cerrado=False
        )
        for a in asesor_qs:
            # Cuando viene de catálogo AlertaSeguimiento
            if a.alertas:
                riesgo_obtenido += a.alertas.nivel_riesgo
                riesgo_maximo += a.alertas.nivel_riesgo
            # Otras alertas creadas manualmente
            elif a.otrasalertas:
                riesgo_obtenido += a.nivel_riesgo
                riesgo_maximo += a.nivel_riesgo

        # -------- Resultado normalizado --------
        if riesgo_maximo == 0:
            return 0.0

        porcentaje = (riesgo_obtenido / riesgo_maximo) * 100
        return round(porcentaje, 2)

    def save(self, *args, **kwargs):
        self.observaciones = null_to_text(self.observaciones)
        self.resolucionconsejo = null_to_text(self.resolucionconsejo)
        if self.fecha <= self.nivel.fechatopematricula:
            self.tipomatricula_id = MATRICULA_REGULAR_ID
        elif self.nivel.fechatopematricula < self.fecha <= self.nivel.fechatopematriculaex:
            self.tipomatricula_id = MATRICULA_EXTRAORDINARIA_ID
        else:
            self.tipomatricula_id = MATRICULA_ESPECIAL_ID
        if not self.id:
            self.nivelmalla = self.inscripcion.mi_nivel().nivel
        if self.id:
            self.paraleloprincipal = self.paralelo_principal_materias()
            self.promedioasistencias = self.promedio_asistencia_periodo()
            self.promedionotas = self.promedio_nota_periodo()
            self.totalhoras = null_to_numeric(self.materiaasignada_set.filter(validacreditos=True).aggregate(valor=Sum('horas'))['valor'], 1)
            self.totalcreditos = null_to_numeric(self.materiaasignada_set.filter(validacreditos=True).aggregate(valor=Sum('creditos'))['valor'], 4)
        if self.cerrada:
            malla = self.inscripcion.mi_malla()
            if self.nivelmalla.id == malla.nivelesregulares:
                self.promovido = self.inscripcion.cumplio_malla()
            else:
                self.promovido = self.nivelmalla.id < self.inscripcion.mi_nivel().nivel.id
        super(Matricula, self).save(*args, **kwargs)


class AgregacionEliminacionMaterias(ModeloBase):
    matricula = models.ForeignKey(Matricula, verbose_name=u"Matricula", on_delete=models.CASCADE)
    agregacion = models.BooleanField(default=True, verbose_name=u"Agregación o Eliminación de materia")
    asignatura = models.ForeignKey(Asignatura, verbose_name=u"Asignatura", on_delete=models.CASCADE)
    responsable = models.ForeignKey(Persona, verbose_name=u"Responsable", on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u"Fecha")
    creditos = models.FloatField(default=0, verbose_name=u'créditos')
    nivelmalla = models.ForeignKey(NivelMalla, blank=True, null=True, verbose_name=u'Nivel', on_delete=models.CASCADE)
    matriculas = models.IntegerField(default=0, verbose_name=u'Matricula')
    adelanto = models.BooleanField(default=False, verbose_name=u"Adelanto de materia")

    def __str__(self):
        return u'Agregación o elimiminación de materias %s' % self.matricula.inscripcion

    class Meta:
        verbose_name_plural = u"Agregaciones o eliminaciones de materias"


class RetiroCategoria(ModeloBase):
    nombre = models.CharField(max_length=50, unique=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class RetiroSubtipo(ModeloBase):
    categoria  = models.ForeignKey(RetiroCategoria, on_delete=models.PROTECT, related_name='subtipos')
    nombre     = models.CharField(max_length=50)
    es_abierto = models.BooleanField(default=False)
    activo     = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['categoria', 'nombre'], name='uix_subtipo_por_categoria')]
        ordering = ['categoria__nombre', 'nombre']

    def __str__(self): return f'{self.categoria.nombre} - {self.nombre}'


ESTADO_RETIRO = (
    (1, u'Abierto'),
    (2, u'Cerrado'),
)


class RetiroMatricula(ModeloBase):
    matricula = models.ForeignKey(Matricula, verbose_name=u'Matricula', on_delete=models.CASCADE)
    subtipo = models.ForeignKey(RetiroSubtipo, blank=True, null=True, verbose_name='Tipo de retiro', on_delete=models.PROTECT)
    estado = models.IntegerField(choices=ESTADO_RETIRO, null=True, default=None, verbose_name=u'Estado')
    fecha = models.DateField(verbose_name=u'Fecha de retiro')
    motivo = models.TextField(default='', verbose_name=u'Motivo')
    covid = models.BooleanField(default=False, verbose_name=u'Covid')
    archivo = models.FileField(upload_to='evidenciaretiro/%Y/%m', blank=True, null=True, verbose_name=u'Archivo')

    def __str__(self):
        return u'Retiro de matricula %s motivo:%s' % (self.matricula.inscripcion, self.motivo)

    class Meta:
        verbose_name_plural = u"Retiros de matriculas"
        unique_together = ('matricula',)
        ordering = ['matricula__inscripcion']

    def extra_delete(self):
        if self.matricula.cerrada:
            return [False, False]
        return [True, False]

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        super(RetiroMatricula, self).save(*args, **kwargs)


class RetiroCarrera(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u"Inscripción", on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u"Fecha")
    motivo = models.TextField(default='', verbose_name=u"Motivo")

    def __str__(self):
        return u'Retiro de Carrera %s motivo:%s' % (self.inscripcion, self.motivo)

    class Meta:
        verbose_name_plural = u"Retiros de inscripciones"
        unique_together = ('inscripcion',)
        ordering = ['inscripcion']

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        super(RetiroCarrera, self).save(*args, **kwargs)


class TipoCostoCurso(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    cursos = models.BooleanField(default=False, verbose_name=u"Solo Cursos y escuelas")
    costodiferenciado = models.BooleanField(default=False, verbose_name=u"Costo diferenciado")
    costolibre = models.BooleanField(default=False, verbose_name=u"Costo libre")
    validapromedio = models.BooleanField(default=False, verbose_name=u"validapromedio")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de costos cursos"
        ordering = ['id']

    def mis_costos_periodo(self, periodo, sede):
        if self.tipocostocursoperiodo_set.filter(periodo=periodo, sede=sede).exists():
            costo = self.tipocostocursoperiodo_set.filter(periodo=periodo, sede=sede)[0]
        else:
            costo = TipoCostoCursoPeriodo(periodo=periodo,
                                          sede=sede,
                                          tipocostocurso=self,
                                          activo=False,
                                          cuotas=1)
            costo.save()
        if self.costodiferenciado:
            for tipoestudiante in TipoEstudianteCurso.objects.all():
                if not CostodiferenciadoCursoPeriodo.objects.filter(tipocostocursoperiodo=costo, tipo=tipoestudiante).exists():
                    cd = CostodiferenciadoCursoPeriodo(tipocostocursoperiodo=costo,
                                                       tipo=tipoestudiante,
                                                       cuotas=1)
                    cd.save()
        return costo

    def tiene_uso(self):
        if self.cursoescuelacomplementaria_set.exists():
            return True
        if self.cursounidadtitulacion_set.exists():
            return True
        return False

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoCostoCurso, self).save(*args, **kwargs)


class CursoEscuelaComplementaria(ModeloBase):
    nombre = models.CharField(verbose_name=u'Nombre', max_length=250)
    usamodeloevaluativo = models.BooleanField(default=False)
    modeloevaluativo = models.ForeignKey(ModeloEvaluativo, blank=True, null=True, verbose_name=u'Modelo Evaluativo', on_delete=models.CASCADE)
    coordinacion = models.ForeignKey(Coordinacion, blank=True, null=True, verbose_name=u'Coordinación', on_delete=models.CASCADE)
    codigo = models.CharField(verbose_name=u'Código', max_length=15)
    solicitante = models.ForeignKey(Persona, related_name='solicitante', blank=True, null=True, verbose_name=u'Solicitante', on_delete=models.CASCADE)
    departamento = models.CharField(verbose_name=u'Departamento', max_length=250)
    fecha_inicio = models.DateField(verbose_name=u'Fecha Inicio')
    fecha_fin = models.DateField(verbose_name=u'Fecha Fin')
    tema = models.TextField(verbose_name=u'Nombre')
    periodo = models.ForeignKey(Periodo, blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    sesion = models.ForeignKey(Sesion, verbose_name=u'Sesion', on_delete=models.CASCADE)
    modalidad = models.ForeignKey(Modalidad, verbose_name=u'Modalidad', on_delete=models.CASCADE)
    tipocurso = models.ForeignKey(TipoCostoCurso, blank=True, null=True, verbose_name=u'Modalidad', on_delete=models.CASCADE)
    sincupo = models.BooleanField(default=False, verbose_name=u"Sin cupo")
    cupo = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Cupo')
    paralelo = models.ForeignKey(ParaleloMateria, verbose_name=u"Paralelo", on_delete=models.CASCADE)
    depositorequerido = models.BooleanField(default=False, verbose_name=u"Deposito requerido")
    depositoobligatorio = models.BooleanField(default=False, verbose_name=u"Deposito obligatorio")
    cerrado = models.BooleanField(default=False, verbose_name=u"Cerrado")
    costodiferenciado = models.BooleanField(default=False, verbose_name=u"Costo diferenciado")
    costomatricula = models.FloatField(default=0, verbose_name=u'Costo de matrícula')
    costocuota = models.FloatField(default=0, verbose_name=u'Costo por cuota')
    cuotas = models.IntegerField(default=0, verbose_name=u'Número de cuotas')
    activo = models.BooleanField(default=False, verbose_name=u"Activo")
    registroonline = models.BooleanField(default=False, verbose_name=u"Permite registro Online")
    registrootrasede = models.BooleanField(default=False, verbose_name=u"Permite registro Otra sede")
    registrointerno = models.BooleanField(default=False, verbose_name=u"Permite registro Interno")
    record = models.BooleanField(default=False, verbose_name=u"Pasa al record")
    examencomplexivo = models.BooleanField(default=False, verbose_name=u"Examen Complexivo")
    libreconfiguracion = models.BooleanField(default=False, verbose_name=u"Libre configuracion")
    optativa = models.BooleanField(default=False, verbose_name=u"Optativa")
    nivelacion = models.BooleanField(default=False, verbose_name=u"Nivelacion")
    aprobacionfinanciero = models.BooleanField(default=False, verbose_name=u"Aprobación financiero")
    apruebafinanciero = models.ForeignKey(Persona, related_name='apruebafinanciero', blank=True, null=True, verbose_name=u'Solicitante', on_delete=models.CASCADE)
    actualizacionconocimiento = models.BooleanField(default=False, verbose_name=u"Actualización conocimientos")
    permiteregistrootramodalidad = models.BooleanField(default=False, verbose_name=u"Permite registros de otras modalidades")
    penalizar = models.BooleanField(default=False, verbose_name=u"Penalizar reprobación de curso")
    prerequisitos = models.BooleanField(default=False, verbose_name=u"Debe cumplir prerequisitos")
    carrera = models.ForeignKey(Carrera, null=True, verbose_name=u'Carrera', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.nombre, self.paralelo)

    class Meta:
        verbose_name_plural = u"Cursos complementarios"
        ordering = ['nombre']
        unique_together = ('codigo',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("CursoEscuelaComplementaria.objects.filter(nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.nombre + " - " + str(self.id)

    def generar_cronograma_pagos(self):
        fecha = self.fecha_inicio
        if self.costomatricula:
            if not PagosCursoEscuelaComplementaria.objects.filter(curso=self, tipo=0):
                pagocurso = PagosCursoEscuelaComplementaria(curso=self,
                                                            tipo=0,
                                                            fecha=datetime.now().date(),
                                                            valor=self.costomatricula)
                pagocurso.save()
        if self.costocuota:
            for cuota in range(1, int(self.cuotas) + 1):
                if not PagosCursoEscuelaComplementaria.objects.filter(curso=self, tipo=cuota).exists():
                    if cuota == 1:
                        fecha = fecha + timedelta(days=4)
                    else:
                        fecha = fecha + relativedelta(months=1)
                    pagocurso = PagosCursoEscuelaComplementaria(curso=self,
                                                                tipo=cuota,
                                                                fecha=fecha,
                                                                valor=self.costocuota)
                    pagocurso.save()
                else:
                    fecha = PagosCursoEscuelaComplementaria.objects.get(curso=self, tipo=cuota).fecha

    def disponible(self):
        return datetime.now().date() <= self.fecha_inicio and self.cupo > self.matriculacursoescuelacomplementaria_set.count()

    def registrados(self):
        return self.matriculacursoescuelacomplementaria_set.count()

    def cupo_disponible(self):
        if self.cupo:
            return self.cupo > self.matriculacursoescuelacomplementaria_set.filter(retiromatriculacursoescuelacomplementaria__isnull=True).count()
        return True

    def mis_registrados(self):
        return self.matriculacursoescuelacomplementaria_set.filter(retiromatriculacursoescuelacomplementaria__isnull=True)

    def registros_validos(self):
        return self.matriculacursoescuelacomplementaria_set.filter(retiromatriculacursoescuelacomplementaria__isnull=True).count()

    def cantiad_cupo_disponible(self):
        if self.cupo:
            return self.cupo - self.matriculacursoescuelacomplementaria_set.filter(retiromatriculacursoescuelacomplementaria__isnull=True).count()
        return 1

    def existe_descuento(self, descuento):
        return self.porcentajedescuentocursos_set.filter(descuento=descuento).exists()

    def total_descuentos(self):
        return self.porcentajedescuentocursos_set.all().count()

    def terminada(self):
        return datetime.now().date() > self.fecha_fin

    def permite_cerrar(self):
        return self.materiacursoescuelacomplementaria_set.count() == self.materiacursoescuelacomplementaria_set.filter(cerrada=True).count()

    def costo(self):
        if self.pagoscursoescuelacomplementaria_set.exists():
            return null_to_numeric(self.pagoscursoescuelacomplementaria_set.aggregate(valor=Sum('valor'))['valor'], 2)
        return null_to_numeric(self.costomatricula + (self.costocuota), 2)


    def clases_activas_horario(self, dia, turno, materia):
        return Clase.objects.filter(activo=True, dia=dia, turno=turno, materiacurso=materia).order_by('inicio')

    def tiene_materias(self):
        return self.materiacursoescuelacomplementaria_set.exists()

    def cantidad_materias(self):
        return self.materiacursoescuelacomplementaria_set.count()

    def puede_cambiar_modelo(self):
        return not self.materiacursoescuelacomplementaria_set.filter(cerrada=True).exists()

    def locaciones_distintas(self):
        return self.locacionescurso_set.count() > 1

    def actualiza_deposito_requerido(self):
        requerido = False
        if self.costomatricula or self.costocuota:
            requerido = True
        else:
            if self.costodiferenciado:
                if self.tipocurso.mis_costos_periodo(self.periodo, self.coordinacion.sede).costodiferenciadocursoperiodo_set.filter(Q(costomatricula__gt=0) | Q(costocuota__gt=0)).exists():
                    requerido = True
        self.depositorequerido = requerido
        self.save()

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigo = null_to_text(self.codigo)
        self.departamento = null_to_text(self.departamento)
        self.tema = null_to_text(self.tema)
        super(CursoEscuelaComplementaria, self).save(*args, **kwargs)



class TipoAula(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de aulas"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoAula, self).save(*args, **kwargs)


class Aula(ModeloBase):
    sede = models.ForeignKey(Sede, verbose_name=u'Sede', on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    tipo = models.ForeignKey(TipoAula, verbose_name=u'Tipo', on_delete=models.CASCADE)
    capacidad = models.IntegerField(default=0, verbose_name=u'Capacidad')
    cantidadequipos = models.IntegerField(default=0, verbose_name=u'Cantidad equipos')

    def __str__(self):
        return u'%s - %s (Cap: %s)' % (self.nombre, self.sede, str(self.capacidad))

    class Meta:
        verbose_name_plural = u"Aulas"
        ordering = ['sede', 'nombre']
        unique_together = ('sede', 'tipo', 'nombre',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Aula.objects.filter(Q(nombre__contains='%s') | Q(tipo__nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.sede.nombre + ' - ' + self.nombre + ' - ' + str(self.id)

    def libre_hoy(self):
        fecha = datetime.now().date()
        return not self.clase_set.filter(activo=True, aula=self, dia=fecha.weekday() + 1, inicio__lte=fecha, fin__gte=fecha).exists()

    def clases_fecha(self, fecha):
        return self.clase_set.filter(activo=True, dia=fecha.weekday() + 1, inicio__lte=fecha, fin__gte=fecha).order_by('turno__comienza').distinct()

    def clasespracticas_fecha(self, fecha):
        return self.clasepractica_set.filter(activo=True, dia=fecha.weekday() + 1, inicio__lte=fecha, fin__gte=fecha).order_by('turno__comienza').distinct()

    def horas_total_dia(self, fecha):
        totalteoricas = null_to_numeric(Clase.objects.filter(aula=self, activo=True, dia=fecha.isoweekday(), inicio__lte=fecha, fin__gte=fecha).distinct().aggregate(valor=Sum('turno__horas'))['valor'], 1)
        totalpracticas = null_to_numeric(ClasePractica.objects.filter(aula=self, activo=True, dia=fecha.isoweekday(), inicio__lte=fecha, fin__gte=fecha).distinct().aggregate(valor=Sum('turno__horas'))['valor'], 1)
        return totalteoricas + totalpracticas

    def coordinaciones(self):
        return Coordinacion.objects.filter(aulacoordinacion__aula=self).distinct()

    def nombre_coordinaciones(self):
        return Coordinacion.objects.filter(aulacoordinacion__aula=self).distinct().values_list('nombre', flat=True)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(Aula, self).save(*args, **kwargs)



class AulaCoordinacion(ModeloBase):
    coordinacion = models.ForeignKey(Coordinacion, verbose_name=u"Coordinación", on_delete=models.CASCADE)
    aula = models.ForeignKey(Aula, verbose_name=u"Aula", on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.aula, self.coordinacion)

    class Meta:
        verbose_name_plural = u"Coordinación de carrera - aulas"
        unique_together = ('coordinacion', 'aula',)


class TipoArchivo(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de archivos"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoArchivo, self).save(*args, **kwargs)


class TipoDocumento(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de Documento"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoDocumento, self).save(*args, **kwargs)




class TipoEstado(ModeloBase):
    nombre = models.CharField(default='', max_length=50, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de estados"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def aprobada(self):
        return self.id == NOTA_ESTADO_APROBADO

    def reprobado(self):
        return self.id == NOTA_ESTADO_REPROBADO

    def encurso(self):
        return self.id == NOTA_ESTADO_EN_CURSO

    def supletorio(self):
        return self.id == NOTA_ESTADO_SUPLETORIO

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("TipoEstado.objects.filter(Q(nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.nombre + ' - ' + str(self.id)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoEstado, self).save(*args, **kwargs)


class CausaHomologacion(ModeloBase):
    nombre = models.CharField(max_length=120)
    activo = models.BooleanField(default=True)

class RecordAcademico(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    matriculas = models.IntegerField(default=0, verbose_name=u'Matriculas')
    # modulomalla = models.ForeignKey(ModuloMalla, blank=True, null=True, verbose_name=u'Modulo malla', on_delete=models.CASCADE)
    asignaturamalla = models.ForeignKey(AsignaturaMalla, blank=True, null=True, verbose_name=u'Modulo malla', on_delete=models.CASCADE)
    asignatura = models.ForeignKey(Asignatura, verbose_name=u'Asignatura', on_delete=models.CASCADE)
    nota = models.FloatField(default=0, verbose_name=u'Nota')
    asistencia = models.FloatField(default=0, verbose_name=u'Asistencia')
    sinasistencia = models.BooleanField(default=False, verbose_name=u'Sin asistencia')
    fecha = models.DateField(verbose_name=u'Record academico')
    noaplica = models.BooleanField(default=False, verbose_name=u'No aplica para matricularse')
    aprobada = models.BooleanField(default=False, verbose_name=u'Aprobada')
    causa_homologacion = models.ForeignKey(CausaHomologacion, null=True, blank=True, on_delete=models.PROTECT)
    convalidacion = models.BooleanField(default=False, verbose_name=u'Homologada')
    pendiente = models.BooleanField(default=False, verbose_name=u'Pendiente')
    creditos = models.FloatField(default=0, blank=True, verbose_name=u'créditos')
    horas = models.FloatField(default=0, blank=True, verbose_name=u'Horas')
    homologada = models.BooleanField(default=False, verbose_name=u'Homologada')
    validacreditos = models.BooleanField(default=True, verbose_name=u'Valida para créditos')
    validapromedio = models.BooleanField(default=True, verbose_name=u'Valida para promedios')
    libreconfiguracion = models.BooleanField(default=False, verbose_name=u"Libre configuracion")
    optativa = models.BooleanField(default=False, verbose_name=u"Optativa")
    observaciones = models.TextField(default='', blank=True, null=True, verbose_name=u'Observaciones')
    materiaregular = models.ForeignKey(Materia, blank=True, null=True, verbose_name=u'Materia regular', on_delete=models.CASCADE)
    padre = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, verbose_name='Padre (record)', help_text='Otro registro record que actúa como padre')

    def __str__(self):
        return u'%s [Nota:%s Asist:%s] %s' % (self.asignatura, str(self.nota), str(self.asistencia), ("APROBADA" if self.aprobada else "REPROBADA"))

    class Meta:
        verbose_name_plural = u"Registros academicos"
        unique_together = ('inscripcion', 'asignatura')

    def datos_homologacion(self):
        if self.homologacioninscripcion_set.exists():
            return self.homologacioninscripcion_set.all()[0]
        return None

    def datos_convalidacion(self):
        if self.convalidacioninscripcion_set.exists():
            return self.convalidacioninscripcion_set.all()[0]
        return None

    def esta_suspensa(self):
        return not self.aprobada

    def puede_volver_matricular(self):
        return self.matricula_actual() < CANTIDAD_MATRICULAS_MAXIMAS

    def matricula_actual(self):
        return self.historicorecordacademico_set.exclude(noaplica=True).exclude(convalidacion=True).exclude(homologada=True).distinct().count()

    def esta_pendiente(self):
        return not self.aprobada

    def tiene_malla(self):
        return self.inscripcion.tiene_malla()

    def existe_en_malla(self):
        return self.inscripcion.mi_malla().asignaturamalla_set.filter(asignatura=self.asignatura).exists()

    def asignatura_malla(self):
        if self.existe_en_malla():
            return self.inscripcion.mi_malla().asignaturamalla_set.filter(asignatura=self.asignatura)[0]
        return None

    def nivel_asignatura(self):
        am = self.asignatura_malla()
        return am.nivelmalla if am else None

    def actualizar(self):
        if not self.historicorecordacademico_set.filter(fecha=self.fecha).exists():
            nuevohistorico = HistoricoRecordAcademico(recordacademico=self,
                                                      inscripcion=self.inscripcion,
                                                      asignaturamalla=self.asignaturamalla,
                                                      trabajotitulacionmalla=self.trabajotitulacionmalla,
                                                      asignatura=self.asignatura,
                                                      nota=self.nota,
                                                      asistencia=self.asistencia,
                                                      sinasistencia=self.sinasistencia,
                                                      fecha=self.fecha,
                                                      noaplica=self.noaplica,
                                                      libreconfiguracion=self.libreconfiguracion,
                                                      optativa=self.optativa,
                                                      aprobada=self.aprobada,
                                                      convalidacion=self.convalidacion,
                                                      homologada=self.homologada,
                                                      pendiente=self.pendiente,
                                                      creditos=self.creditos,
                                                      horas=self.horas,
                                                      validacreditos=self.validacreditos,
                                                      validapromedio=self.validapromedio,
                                                      materiaregular=self.materiaregular,
                                                      materiacurso=self.materiacurso,
                                                      materiacursotitulacion=self.materiacursotitulacion,
                                                      valoracioncalificacion=self.valoracioncalificacion,
                                                      observaciones=self.observaciones)
            nuevohistorico.save()
        seleccionada = self.historicorecordacademico_set.all().order_by('-aprobada', '-fecha')[0]
        self.trabajotitulacionmalla = seleccionada.trabajotitulacionmalla
        self.asignaturamalla = seleccionada.asignaturamalla
        self.asignatura = seleccionada.asignatura
        self.nota = seleccionada.nota
        self.asistencia = seleccionada.asistencia
        self.sinasistencia = seleccionada.sinasistencia
        self.fecha = seleccionada.fecha
        self.noaplica = seleccionada.noaplica
        self.aprobada = seleccionada.aprobada
        self.convalidacion = seleccionada.convalidacion
        self.homologada = seleccionada.homologada
        self.pendiente = seleccionada.pendiente
        self.creditos = seleccionada.creditos
        self.horas = seleccionada.horas
        self.validacreditos = seleccionada.validacreditos
        self.validapromedio = seleccionada.validapromedio
        self.materiaregular = seleccionada.materiaregular
        self.materiacurso = seleccionada.materiacurso
        self.materiacursotitulacion = seleccionada.materiacursotitulacion
        self.valoracioncalificacion = seleccionada.valoracioncalificacion
        self.observaciones = seleccionada.observaciones
        self.save()

    def tiene_acta_curso(self):
        return self.materiacurso_id > 0

    def tiene_acta_nivel(self):
        return self.materiaregular_id > 0

    def tiene_acta(self):
        return self.tiene_acta_curso() or self.tiene_acta_nivel()

    def acta_materia_curso(self):
        if self.tiene_acta_curso():
            return self.materiacurso
        return None

    def acta_materia_nivel(self):
        if self.tiene_acta_nivel():
            return self.materiaregular
        return None

    def periodo(self):
        if self.tiene_acta_nivel():
            return self.acta_materia_nivel().nivel.periodo
        return None

    def tiene_historico(self):
        return self.historicorecordacademico_set.exists()

    def mi_historico(self):
        return self.inscripcion.historicorecordacademico_set.filter(asignatura=self.asignatura, fecha=self.fecha)[0]

    def profesor(self):
        if self.materiaregular:
            return self.materiaregular.profesor_principal()
        elif self.materiacurso:
            return self.materiacurso.profesor
        return None

    def es_nivelacion(self):
        if self.asignaturamalla:
            return self.asignaturamalla.nivelmalla.id == 0
        return False

    def es_movilidad(self):
        if MateriaAsignada.objects.filter(materia=self.materiaregular, matricula__inscripcion=self.inscripcion, movilidad=True).exists():
            return True
        return False

    def es_ingles(self):
        if self.asignatura_id in [4311, 4312, 4313, 4316, 4317, 4318, 4319, 4320]:
            return True
        return False

    def save(self, *args, **kwargs):
        self.asignaturamalla = self.asignatura_malla()

        if not self.aprobada:
            self.creditos = 0
            self.horas = 0
            self.validacreditos = False
        if self.id:
            self.matriculas = self.matricula_actual()
        if self.noaplica:
            self.aprobada = True
            self.validacreditos = False
            self.validapromedio = False
            self.creditos = 0
            self.horas = 0
        self.pendiente = False
        self.observaciones = null_to_text(self.observaciones)
        self.valoracioncalificacion = valoracion_calificacion(self.nota)
        super(RecordAcademico, self).save(*args, **kwargs)


class MateriaAsignada(ModeloBase):
    matricula = models.ForeignKey(Matricula, verbose_name=u"Matricula", on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, verbose_name=u"Materia", on_delete=models.CASCADE)
    asignaturareal = models.ForeignKey(Asignatura, blank=True, null=True, verbose_name=u"Representa", on_delete=models.CASCADE)
    asignaturamalla = models.ForeignKey(AsignaturaMalla, blank=True, null=True, verbose_name=u'Asignatura malla', on_delete=models.CASCADE)
    # modulomalla = models.ForeignKey(ModuloMalla, blank=True, null=True, verbose_name=u'Modulo malla', on_delete=models.CASCADE)
    notafinal = models.FloatField(default=0, verbose_name=u"Nota final")
    asistenciafinal = models.FloatField(default=100, verbose_name=u"Asistencia final")
    cerrado = models.BooleanField(default=False, verbose_name=u'Cerrada')
    fechacierre = models.DateField(null=True, blank=True, verbose_name=u'Fecha de cierre')
    matriculas = models.IntegerField(default=0, verbose_name=u'Matriculas')
    observaciones = models.TextField(default='', verbose_name=u'Observaciones')
    estado = models.ForeignKey(TipoEstado, blank=True, null=True, verbose_name=u'Estado', on_delete=models.CASCADE)
    sinasistencia = models.BooleanField(default=False, verbose_name=u'Validar asistencia para calificacion')
    verificahorario = models.BooleanField(default=True, verbose_name=u'Debe asistir a clases')
    evaluar = models.BooleanField(default=False, verbose_name=u'Realizar evaluación tardia')
    fechaevaluar = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha autorización')
    fechaasignacion = models.DateField(blank=True, null=True, verbose_name=u'Fecha asignación')
    horas = models.FloatField(default=0, verbose_name=u'Horas')
    creditos = models.FloatField(default=0, verbose_name=u'créditos')
    validacreditos = models.BooleanField(default=True, verbose_name=u'Valida para créditos')
    validapromedio = models.BooleanField(default=True, verbose_name=u'Valida para promedio')
    asistenciafinal_academica_ir = models.FloatField(default=0, verbose_name=u"Asistencia académica IR (%)", help_text=u"Porcentaje de asistencia a actividades académicas del internado (0–100).")
    asistenciafinal_asistencial_ir = models.FloatField(default=0, verbose_name=u"Asistencia asistencial IR (%)", help_text=u"Porcentaje de asistencia a actividades asistenciales/clinicas del internado (0–100).")

    def __str__(self):
        return u'%s %s [Nota:%s Asis:%s] ' % (self.matricula, self.materia, str(self.notafinal), str(self.asistenciafinal))

    def nombre_corto(self):
        return u'%s %s' % (self.matricula.nivel.periodo, self.materia.asignatura)

    class Meta:
        verbose_name_plural = u'Materias asignadas'
        ordering = ['matricula']
        unique_together = ('matricula', 'materia',)

    def flexbox_alias(self):
        return self.matricula.inscripcion

    def aprobada(self):
        return self.estado_id == NOTA_ESTADO_APROBADO

    def reprobado(self):
        return self.estado_id == NOTA_ESTADO_REPROBADO

    def encurso(self):
        return self.estado_id == NOTA_ESTADO_EN_CURSO

    def recuperacion(self):
        return self.estado_id == NOTA_ESTADO_SUPLETORIO

    def asistencias_lecciones(self):
        return self.asistencialeccion_set.all().order_by('leccion__fecha', 'leccion__horaentrada')

    def cantidad_asistencias_lecciones(self):
        return self.asistencialeccion_set.all().count()

    def existe_en_malla(self):
        return self.matricula.inscripcion.mi_malla().asignaturamalla_set.filter(asignatura=self.materia.asignatura).exists()

    def seleccionado_practica(self, profesormateria):
        return self.alumnospracticamateria_set.filter(profesor=profesormateria.profesor).exists()

    def materia_malla(self):
        if self.existe_en_malla():
            return self.matricula.inscripcion.mi_malla().asignaturamalla_set.filter(asignatura=self.materia.asignatura)[0]
        return None

    def creditos_malla(self):
        if self.existe_en_malla():
            return self.materia_malla().creditos
        return 0

    def horas_malla(self):
        if self.existe_en_malla():
            return self.materia_malla().horas
        return 0

    def en_otra_carrera(self):
        return self.materia.asignatura != self.asignaturareal and self.matricula.inscripcion.existe_en_malla(self.asignaturareal)

    def homologada(self):
        return self.materiaasignadahomologacion_set.exists()

    def convalidada(self):
        return self.materiaasignadaconvalidacion_set.exists()

    def datos_homologacion(self):
        if self.homologada():
            return self.materiaasignadahomologacion_set.all()[0].homologacion
        return None

    def datos_convalidacion(self):
        if self.convalidada():
            return self.materiaasignadaconvalidacion_set.all()[0].convalidacion
        return None

    def retirado(self):
        return self.materiaasignadaretiro_set.exists()

    def fecha(self):
        if self.matricula.agregacioneliminacionmaterias_set.filter(agregacion=True, asignatura=self.materia.asignatura).exists():
            ag = self.matricula.agregacioneliminacionmaterias_set.filter(agregacion=True, asignatura=self.materia.asignatura).order_by('-fecha')[0]
            return ag.fecha
        return self.matricula.fecha

    def cierre_materia_asignada(self, noactualiza=None):
        if self.pasar_record():
            if not noactualiza:
                self.actualiza_estado()
            convalidada = False
            homologada = False
            if self.asignaturareal:
                asignatura = self.asignaturareal
            else:
                asignatura = self.materia.asignatura
            asignaturamalla = self.matricula.inscripcion.asignatura_en_asignaturamalla(asignatura)
            if asignaturamalla:
                validacreditos = asignaturamalla.validacreditos
                validapromedio = asignaturamalla.validapromedio
                creditos = asignaturamalla.creditos
                horas = asignaturamalla.horas
            else:
                validacreditos = self.materia.validacreditos
                validapromedio = self.materia.validapromedio
                creditos = self.materia.creditos
                horas = self.materia.horas
            aprobada = self.aprobada()
            if self.convalidada():
                convalidada = True
                aprobada = True
            if self.homologada():
                homologada = True
                aprobada = True
            if not aprobada:
                creditos = 0
                horas = 0
            existente = None
            if HistoricoRecordAcademico.objects.filter(inscripcion=self.matricula.inscripcion, asignatura=asignatura, fecha=self.materia.fin).exists():
                existente = HistoricoRecordAcademico.objects.filter(inscripcion=self.matricula.inscripcion, asignatura=asignatura, fecha=self.materia.fin)[0]
            elif HistoricoRecordAcademico.objects.filter(inscripcion=self.matricula.inscripcion, materiaregular=self.materia).exists():
                existente = HistoricoRecordAcademico.objects.filter(inscripcion=self.matricula.inscripcion, materiaregular=self.materia)[0]
            if existente:
                existente.nota = self.notafinal
                existente.asignaturamalla = self.matricula.inscripcion.asignatura_en_asignaturamalla(asignatura)
                existente.horas = horas
                existente.creditos = creditos
                existente.validacreditos = validacreditos
                existente.validapromedio = validapromedio
                existente.asistencia = self.asistenciafinal
                existente.sinasistencia = False
                existente.fecha = self.materia.fin
                existente.convalidacion = convalidada
                existente.homologada = homologada
                existente.aprobada = aprobada
                existente.materiaregular = self.materia
                existente.pendiente = False
                existente.observaciones = self.observaciones
                existente.save()
                existente.actualizar()
            else:
                historico = HistoricoRecordAcademico(inscripcion=self.matricula.inscripcion,
                                                     asignatura=asignatura,
                                                     asignaturamalla=self.matricula.inscripcion.asignatura_en_asignaturamalla(asignatura),
                                                     nota=self.notafinal,
                                                     creditos=creditos,
                                                     horas=horas,
                                                     validacreditos=validacreditos,
                                                     validapromedio=validapromedio,
                                                     asistencia=self.asistenciafinal,
                                                     sinasistencia=False,
                                                     fecha=self.materia.fin,
                                                     convalidacion=convalidada,
                                                     homologada=homologada,
                                                     aprobada=aprobada,
                                                     pendiente=False,
                                                     materiaregular=self.materia,
                                                     observaciones=self.observaciones)
                historico.save()
                if self.matricula.inscripcion.recordacademico_set.filter(asignatura=historico.asignatura).exists():
                    historico.recordacademico = self.matricula.inscripcion.recordacademico_set.filter(asignatura=historico.asignatura)[0]
                    historico.save()
                historico.actualizar()
            self.matricula.inscripcion.actualizar_nivel()

    def ya_cobrada(self):
        return RubroMateria.objects.filter(materiaasignada=self).count() > 0

    def cantidad_matriculas(self):
        return self.matricula.inscripcion.historicorecordacademico_set.filter(asignatura=self.materia.asignatura, fecha__lt=self.materia.nivel.fin, noaplica=False).count() + 1

    def asistencias(self):
        lecciones = self.materia.lecciones_individuales()
        asistencias = self.asistencialeccion_set.all()
        if asistencias.count() != lecciones.count():
            for leccion in lecciones:
                asistencia = self.asistencialeccion_set.filter(leccion=leccion).order_by('-asistio')
                if not asistencia.exists():
                    asistencia = AsistenciaLeccion(leccion=leccion,
                                                   materiaasignada=self,
                                                   asistio=True)
                    asistencia.save()
                else:
                    if asistencia.count() > 1:
                        eliminar = asistencia[1:]
                        for a in eliminar:
                            a.delete()
            self.save(actualiza=True)
            self.actualiza_estado()
        return self.asistencialeccion_set.all().order_by('leccion__fecha', 'leccion__horaentrada')

    def asistencia_leccion(self, leccion):
        if self.asistencialeccion_set.count() >= leccion + 1:
            return self.asistencialeccion_set.order_by('leccion__fecha', 'leccion__horaentrada')[leccion]
        return None

    def asistencia_real(self):
        return self.asistencias().filter(leccion__fecha__gte=self.fechaasignacion, asistio=True).count()

    def asistencia_plan(self):
        return self.asistencias().filter(leccion__fecha__gte=self.fechaasignacion).count()

    def porciento_asistencia(self):
        try:
            if self.homologada() or self.convalidada():
                return 100
            else:
                total = null_to_numeric(self.asistencialeccion_set.filter(leccion__fecha__gte=self.fechaasignacion, leccion__fecha__lte=self.materia.fechafinasistencias).distinct().count(), 0)
                if total:
                    real = null_to_numeric(self.asistencialeccion_set.filter(leccion__fecha__gte=self.fechaasignacion, leccion__fecha__lte=self.materia.fechafinasistencias, asistio=True).exclude(justificacionausenciaasistencialeccion__isnull=False).distinct().count(), 0)
                    justificada = null_to_numeric(JustificacionAusenciaAsistenciaLeccion.objects.filter(asistencialeccion__leccion__fecha__gte=self.fechaasignacion, asistencialeccion__leccion__fecha__lte=self.materia.fechafinasistencias, asistencialeccion__materiaasignada=self).distinct().aggregate(valor=Sum('porcientojustificado'))['valor'], 0)
                    return null_to_numeric(((real + justificada) * 100) / total, 0)
        except:
            pass
        return 100

    def porciento_requerido(self):
        return self.asistenciafinal >= self.materia.modeloevaluativo.asistenciaaprobar

    def cantidad_evaluaciones_clase(self):
        return self.evaluacionleccion_set.filter(leccion__clase__materia=self.materia).count()

    def total_lecciones(self):
        return LeccionGrupo.objects.filter(lecciones__clase__materia=self.materia).count()

    def promedio_evaluacion_clase(self):
        return null_to_numeric(self.evaluacionleccion_set.filter(leccion__clase__materia=self.materia).aggregate(valor=Avg('evaluacion'))['valor'], 2)

    def profesores(self):
        return [x.profesor for x in self.materia.profesormateria_set.all()]

    def syllabus(self):
        if Archivo.objects.filter(tipo_id=ARCHIVO_TIPO_SYLLABUS, asignaturamalla__malla=self.matricula.inscripcion.mi_malla(), asignaturamalla__asignatura=self.materia.asignatura, aprobado=True).exists():
            return Archivo.objects.filter(tipo_id=ARCHIVO_TIPO_SYLLABUS, asignaturamalla__malla=self.matricula.inscripcion.mi_malla(), asignaturamalla__asignatura=self.materia.asignatura, aprobado=True).distinct().order_by('-fecha')[0]
        return None

    def permite_calificacion(self):
        if self.homologada() or self.convalidada():
            return False
        if self.matricula.retirado():
            if self.materiaasignadaretiro_set.exists():
                retiro = self.materiaasignadaretiro_set.all()[0]
                if not retiro.valida:
                    return False
            else:
                return False
        return True

    def evaluacion_generica(self):
        if not self.evaluaciongenerica_set.exists():
            modelo = self.materia.modeloevaluativo
            for campos in modelo.detallemodeloevaluativo_set.all():
                evaluacion = EvaluacionGenerica(materiaasignada=self,
                                                detallemodeloevaluativo=campos,
                                                valor=0)
                evaluacion.save()
        return self.evaluaciongenerica_set.all()

    def evaluacion(self):
        return self.evaluacion_generica()

    def esta_aprobado_final(self):
        self.actualiza_estado()
        return self.estado_id == NOTA_ESTADO_APROBADO

    def pertenece_malla(self):
        return AsignaturaMalla.objects.filter(asignatura=self.materia.asignatura).exists()

    def pasar_record(self):
        if self.materiaasignadaretiro_set.exists():
            return self.materiaasignadaretiro_set.all()[0].valida
        return True

    def retiro(self):
        if self.materiaasignadaretiro_set.exists():
            return self.materiaasignadaretiro_set.all()[0]
        else:
            retiro = MateriaAsignadaRetiro(materiaasignada=self,
                                           valida=False)
            retiro.save()
            return retiro

    def esta_retirado(self):
        return self.materiaasignadaretiro_set.exists()

    def valida_pararecord(self):
        if self.esta_retirado():
            return self.retiro().valida
        return True

    def puedo_eliminarla(self):
        if datetime.now().date() > self.materia.nivel.fin:
            return False
        if self.materia.nivel.cerrado:
            return False
        for rubro in self.rubromateria_set.all():
            if rubro.rubro.tiene_pagos():
                return False
        for rubro in self.rubroagregacion_set.all():
            if rubro.rubro.tiene_pagos():
                return False
        for rubro in self.rubroderecho_set.all():
            if rubro.rubro.tiene_pagos():
                return False
        return True

    def nivel(self):
        if self.existe_en_malla():
            return self.materia_malla().nivelmalla
        return None

    def eje(self):
        if self.existe_en_malla():
            return self.materia_malla().ejeformativo
        return None

    def campo(self, campo):
        return self.evaluacion_generica().filter(detallemodeloevaluativo__nombre=campo)[0] if self.evaluacion_generica().filter(detallemodeloevaluativo__nombre=campo).exists() else None

    def valor_nombre_campo(self, campo):
        return self.evaluacion_generica().filter(detallemodeloevaluativo__nombre=campo)[0].valor if self.evaluacion_generica().filter(detallemodeloevaluativo__nombre=campo).exists() else 0

    def permite_ingreso_por_asistencia(self, campo):
        campo = self.evaluacion_generica().filter(detallemodeloevaluativo__nombre=campo)[0]
        if campo.detallemodeloevaluativo.dependeasistencia:
            return self.porciento_requerido()
        return True

    def actualiza_estado(self):
        modelo = self.materia.modeloevaluativo
        self.estado_id = NOTA_ESTADO_EN_CURSO
        actualizar = False
        determinar_estado_final = False
        if self.homologada() or self.convalidada():
            self.estado_id = NOTA_ESTADO_APROBADO
        else:
            for campo in modelo.campos().filter(actualizaestado=True):
                if self.valor_nombre_campo(campo.nombre) > 0:
                    actualizar = True
                    break
            for campo in modelo.campos().filter(determinaestadofinal=True):
                if self.valor_nombre_campo(campo.nombre) > 0:
                    determinar_estado_final = True
                    break
            if actualizar or self.cerrado:
                if self.materia.nivel.periodo.valida_asistencia:
                    if not self.sinasistencia:
                        if self.asistenciafinal >= modelo.asistenciaaprobar and self.notafinal >= modelo.notaaprobar:
                            self.estado_id = NOTA_ESTADO_APROBADO
                        elif modelo.asistenciaaprobar <= self.asistenciafinal and self.notafinal >= modelo.notarecuperacion:
                            self.estado_id = NOTA_ESTADO_SUPLETORIO
                        elif modelo.asistenciaaprobar <= self.asistenciafinal and self.notafinal < modelo.notarecuperacion:
                            self.estado_id = NOTA_ESTADO_REPROBADO

                            ### internado
                        if self.materia.asignaturamalla.internado:
                            if self.asistenciafinal_academica_ir >= modelo.asistenciaaprobar and self.asistenciafinal_asistencial_ir >= 100 and self.notafinal >= modelo.notaaprobar:
                                self.estado_id = NOTA_ESTADO_APROBADO
                            elif self.asistenciafinal_academica_ir >= modelo.asistenciaaprobar and self.asistenciafinal_asistencial_ir >= 100 and self.notafinal >= modelo.notarecuperacion:
                                self.estado_id = NOTA_ESTADO_SUPLETORIO
                            elif self.asistenciafinal_academica_ir >= modelo.asistenciaaprobar and self.asistenciafinal_asistencial_ir >= 100 and self.notafinal < modelo.notarecuperacion:
                                self.estado_id = NOTA_ESTADO_REPROBADO
                            else:
                                self.estado_id = NOTA_ESTADO_REPROBADO


                    else:
                        if self.notafinal >= modelo.notaaprobar:
                            self.estado_id = NOTA_ESTADO_APROBADO
                        elif self.notafinal >= modelo.notarecuperacion:
                            self.estado_id = NOTA_ESTADO_SUPLETORIO
                        else:
                            self.estado_id = NOTA_ESTADO_REPROBADO
                else:
                    if self.notafinal >= modelo.notaaprobar:
                        self.estado_id = NOTA_ESTADO_APROBADO
                    elif modelo.notaaprobar > self.notafinal >= modelo.notarecuperacion:
                        self.estado_id = NOTA_ESTADO_SUPLETORIO
            if determinar_estado_final or self.cerrado:
                if not self.estado_id == NOTA_ESTADO_APROBADO:
                    self.estado_id = NOTA_ESTADO_REPROBADO
        self.save(True)

    def actualiza_notafinal(self):
        modeloevaluativomateria = self.materia.modeloevaluativo
        local_scope = {}
        exec(modeloevaluativomateria.logicamodelo, globals(), local_scope)
        calculo_modelo_evaluativo = local_scope['calculo_modelo_evaluativo']
        calculo_modelo_evaluativo(self)
        self.notafinal = null_to_numeric(self.notafinal, modeloevaluativomateria.notafinaldecimales)
        self.save()
        self.actualiza_estado()

    def parciales(self):
        lista = []
        for campo in self.materia.modeloevaluativo.campos():
            lista.append([campo.nombre, self.valor_nombre_campo(campo.nombre)])
        return lista

    def evaluada(self, profesor):
        return self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, profesor=profesor).exists()

    def pueden_evaluar_docentes(self, proceso):
        hoy = datetime.now().date()
        if not self.materia.usaperiodoevaluacion:
            if (datetime(self.materia.fin.year, self.materia.fin.month, self.materia.fin.day, 0, 0, 0) + timedelta(days=self.materia.diasactivacion)).date() >= hoy >= self.materia.fin and proceso.instrumentoheteroactivo:
                return True
        else:
            if proceso.instrumentoheteroactivo and proceso.instrumentoheteroinicio <= hoy <= proceso.instrumentoheterofin:
                return True
        if self.evaluar and proceso.instrumentoheteroactivo:
            return True
        return False

    def es_materiamalla(self):
        return self.asignaturamalla is not None

    def cantidad_tutorias_solicitadas(self):
        return SolicitudTutoria.objects.filter(materiaasignada=self).count()

    def cantidad_tutorias_programadas(self):
        hoy = datetime.now()
        return self.materia.tutoriamateria_set.filter(Q(fecha__gt=hoy.date()) | Q(fecha=hoy.date(), hora__gt=hoy.time())).distinct().count()

    def cantidad_tutorias_recibidas(self):
        return SolicitudTutoria.objects.filter(materiaasignada=self, pendiente=False, asistenciatutoria__isnull=False).count()

    def cantidad_tutorias_canceladas(self):
        return SolicitudTutoria.objects.filter(materiaasignada=self, pendiente=False, asistenciatutoria__isnull=True).count()

    def tiene_solicitudes_pendientes(self):
        return SolicitudTutoria.objects.filter(materiaasignada=self, pendiente=True).exists()

    def solicitud_pendiente(self):
        if self.tiene_solicitudes_pendientes():
            return SolicitudTutoria.objects.filter(materiaasignada=self, pendiente=True)[0]
        return None

    def verifica_campos_modelo(self):
        for campo in self.materia.modeloevaluativo.detallemodeloevaluativo_set.all():
            if not self.evaluaciongenerica_set.filter(detallemodeloevaluativo=campo).exists():
                evaluaion = EvaluacionGenerica(materiaasignada=self,
                                               detallemodeloevaluativo=campo)
                evaluaion.save()

    def valida_para_credito(self):
        asignaturamalla = self.matricula.inscripcion.asignatura_en_asignaturamalla(self.asignaturareal)
        if asignaturamalla:
            return asignaturamalla.validacreditos

        return self.materia.validacreditos

    def valida_para_promedio(self):
        asignaturamalla = self.matricula.inscripcion.asignatura_en_asignaturamalla(self.asignaturareal)
        if asignaturamalla:
            return asignaturamalla.validapromedio
        return self.materia.validapromedio

    def valor_campos(self):
        return EvaluacionGenerica.objects.filter(materiaasignada=self).order_by('detallemodeloevaluativo__orden')

    def nombre_campos(self):
        return DetalleModeloEvaluativo.objects.filter(evaluaciongenerica__materiaasignada=self).order_by('orden')

    def tiene_nee(self):
        return InclusionBienestarMatricula.objects.filter(matricula=self.matricula).exists()

    def nee(self):
        if self.tiene_inclusion():
            return InclusionBienestarMatricula.objects.filter(matricula=self.matricula).first()
        return None

    def tiene_solicitud_ingreso_aprobada(self):
        fecha = datetime.now().date()
        return self.solicitudingresonotasestudiante_set.filter(fechaaprobacion__lte=fecha, fechalimite__gte=fecha, estado=2).exists()

    def tiene_solicitud_ingresonotas(self):
        return self.solicitudingresonotasestudiante_set.exists()

    def solicitud_ingresonotas(self):
        return self.solicitudingresonotasestudiante_set.all()[0]

    def tiene_solicitud_secretaria_certificado_culminacion(self):
        return self.solicitudsecretariadocente_set.filter(tipo_id=18).exists()

    def solicitud_secretaria_certificado_culminacion(self):
        if self.tiene_solicitud_secretaria_certificado_culminacion():
            return self.solicitudsecretariadocente_set.filter(tipo_id=18).first()
        return False

    def tiene_solicitud_derecho_supletorio(self):
        return self.solicitudsecretariadocente_set.filter(tipo_id=25).exists()

    def solicitud_derecho_supletorio(self):
        if self.tiene_solicitud_derecho_supletorio():
            return self.solicitudsecretariadocente_set.filter(tipo_id=25).first()
        return False

    def tiene_pagado_recuperacion(self):
        solicitud = self.solicitud_derecho_supletorio()
        return bool(solicitud and solicitud.pagada())

    def campos_api(self):
        campos = []
        notas = []
        for c in self.materia.modeloevaluativo.campos():
            campos.append(c.nombre)
            notas.append(str(self.valor_nombre_campo(c.nombre)))
        campos.append('NOTA')
        notas.append(str(self.notafinal))
        return [";".join(campos), ";".join(notas)]

    def save(self, actualiza=False, *args, **kwargs):
        if not self.fechaasignacion:
            self.fechaasignacion = self.matricula.fecha
        if actualiza:
            if self.id:
                if self.sinasistencia:
                    self.asistenciafinal = 100
                else:
                    if not self.asignaturamalla.internado:
                        self.asistenciafinal = self.porciento_asistencia()
        if self.cerrado and not self.fechacierre:
            if self.materia.fechacierre:
                self.fechacierre = self.materia.fechacierre
            else:
                self.fechacierre = datetime.now().date()
        self.validacreditos = self.valida_para_credito()
        self.validapromedio = self.valida_para_promedio()
        super(MateriaAsignada, self).save(*args, **kwargs)





class TipoEstudianteCurso(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de estudiante curso"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoEstudianteCurso, self).save(*args, **kwargs)

class LocacionesCurso(ModeloBase):
    curso = models.ForeignKey(CursoEscuelaComplementaria, verbose_name=u'Curso', on_delete=models.CASCADE)
    locacion = models.ForeignKey(Locacion, verbose_name=u'Locacion', on_delete=models.CASCADE)
    cupo = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return u'%s' % self.locacion.nombre

    def registrados(self):
        return self.matriculacursoescuelacomplementaria_set.count()

    def extra_delete(self):
        if self.matriculacursoescuelacomplementaria_set.exists():
            return [False, False]
        return [True, False]

TIPO_REGISTRO_MATRICULA_CURSO = (
    (1, u'EXAMEN COMPLEXIVO'),
    (2, u'CULMINO DE TRABAJO DE TITULACION')
)

class MatriculaCursoEscuelaComplementaria(ModeloBase):
    curso = models.ForeignKey(CursoEscuelaComplementaria, verbose_name=u'Curso Complementario', on_delete=models.CASCADE)
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u'Inscripción Curso', on_delete=models.CASCADE)
    tipoestudiantecurso = models.ForeignKey(TipoEstudianteCurso, blank=True, null=True, verbose_name=u'Inscripción Curso', on_delete=models.CASCADE)
    locacion = models.ForeignKey(LocacionesCurso, blank=True, null=True, verbose_name=u'Inscripción Curso', on_delete=models.CASCADE)
    codigo = models.CharField(max_length=30, verbose_name=u'Código')
    estado = models.ForeignKey(TipoEstado, verbose_name=u'Estado', on_delete=models.CASCADE)
    tiporegistro = models.IntegerField(default=1, choices=TIPO_REGISTRO_MATRICULA_CURSO)
    notateoria = models.FloatField(default=0, verbose_name=u'Nota Teorica')
    notateoriareal = models.FloatField(default=0, verbose_name=u'Nota Teorica')
    porcentajeteoria = models.FloatField(default=0, verbose_name=u'Porcentaje Teorica')
    porcentajepractico = models.FloatField(default=0, verbose_name=u'Porcentaje Practica')
    notapracticareal = models.FloatField(default=0, verbose_name=u'Nota Practica')
    notapractica = models.FloatField(default=0, verbose_name=u'Nota Practica')
    notaexamen = models.FloatField(default=0, verbose_name=u'Nota Examen')
    notaculminacion = models.FloatField(default=0, verbose_name=u'Nota Culminacion')
    fecha = models.DateField(null=True, blank=True, verbose_name=u"Fecha")
    hora = models.TimeField(null=True, blank=True, verbose_name=u"Hora")
    fechatope = models.DateField(null=True, blank=True, verbose_name=u"Fecha límite de cancelación")
    formalizada = models.BooleanField(default=False, verbose_name=u"Formalizada")

    def __str__(self):
        return u'%s - %s' % (self.inscripcion, self.curso)

    class Meta:
        unique_together = ('curso', 'inscripcion',)
        ordering = ['inscripcion__persona', '-fecha']

    def extra_delete(self):
        if self.curso.cerrado:
            return [False, False]
        return [True, False]

    def aprobada(self):
        return self.estado_id == NOTA_ESTADO_APROBADO

    def nota_final(self):
        pp = self.porcentajepractico
        pt = self.porcentajeteoria
        if pp > 0 and pt > 0:
            self.notapracticareal = null_to_numeric((self.notapractica * pp) / 100,2)
            self.notateoriareal = null_to_numeric((self.notateoria * pt) / 100,2)
            return null_to_numeric(self.notateoriareal + self.notapracticareal, 2)
        return 0

    def notaculminacion_final(self):
        return null_to_numeric(self.notaculminacion, 2)

    def reprobado(self):
        return self.estado_id == NOTA_ESTADO_REPROBADO

    def encurso(self):
        return self.estado_id == NOTA_ESTADO_EN_CURSO

    def actualiza_estado(self):
        self.estado_id = NOTA_ESTADO_EN_CURSO
        if not self.materiaasignadacurso_set.filter(materia__cerrada=False).exists():
            self.estado_id = NOTA_ESTADO_APROBADO
            for materiaasignada in self.materiaasignadacurso_set.filter(materia__requiereaprobar=True):
                if materiaasignada.reprobado():
                    self.estado_id = NOTA_ESTADO_REPROBADO
        self.save()
        if self.estado.id == NOTA_ESTADO_APROBADO:
            self.codigo = self.curso.codigo + str(self.id)
        else:
            self.codigo = ''
        self.save()

    def esta_retirado(self):
        return self.retiromatriculacursoescuelacomplementaria_set.exists()

    def tiene_rubros_pagados(self):
        return Pago.objects.filter(rubro__rubrocursoescuelacomplementaria__participante=self).exists()

    def eliminar_rubros_matricula(self):
        for rubro in RubroCursoEscuelaComplementaria.objects.filter(participante=self):
            r = rubro.rubro
            rubro.delete()
            r.verifica_rubro_otro(RUBRO_OTRO_CURSOS_LIBRE_CONFIGURACION_ID)

    def eliminar_rubros_matricula_total(self):
        for rubro in RubroCursoEscuelaComplementaria.objects.filter(participante=self):
            r = rubro.rubro
            r.delete()

    def generar_rubro(self):
        curso = self.curso
        costomatricula = curso.costomatricula
        costocuota = curso.costocuota
        cuotas = curso.cuotas
        tipocurso = None
        if curso.costodiferenciado:
            tipo = self.tipoestudiantecurso
            if CostodiferenciadoCursoPeriodo.objects.filter(tipocostocursoperiodo__tipocostocurso__cursoescuelacomplementaria=curso, tipo=tipo, tipocostocursoperiodo__periodo=curso.periodo, tipocostocursoperiodo__sede=curso.coordinacion.sede).exists():
                costotipo = CostodiferenciadoCursoPeriodo.objects.filter(tipocostocursoperiodo__tipocostocurso__cursoescuelacomplementaria=curso, tipo=tipo, tipocostocursoperiodo__periodo=curso.periodo, tipocostocursoperiodo__sede=curso.coordinacion.sede)[0]
                costomatricula = costotipo.costomatricula
                costocuota = costotipo.costocuota
                cuotas = costotipo.cuotas
        if costomatricula:
            if not self.rubrocursoescuelacomplementaria_set.exists():
                rubro = Rubro(inscripcion=self.inscripcion,
                              fecha=curso.fecha_inicio,
                              iva_id=TIPO_IVA_0_ID,
                              valor=costomatricula,
                              fechavence=curso.fecha_inicio)
                rubro.save()
                rubrocurso = RubroCursoEscuelaComplementaria(rubro=rubro,
                                                             participante=self)
                rubrocurso.save()
                if tipocurso == 22:
                    rubro.actulizar_nombre('CURSO-PG: ' + self.curso.nombre)
                else:
                    rubro.actulizar_nombre()
        if costocuota:
            fechacuota = curso.fecha_inicio
            for numerocuota in range(1, cuotas + 1):
                if not self.rubrocursoescuelacomplementaria_set.filter(cuota=numerocuota).exists():
                    rubro = Rubro(inscripcion=self.inscripcion,
                                  fecha=fechacuota,
                                  iva_id=TIPO_IVA_0_ID,
                                  valor=costocuota,
                                  fechavence=fechacuota)
                    rubro.save()
                    rubrocurso = RubroCursoEscuelaComplementaria(rubro=rubro,
                                                                 cuota=numerocuota,
                                                                 participante=self)
                    rubrocurso.save()
                    if tipocurso == 22:
                        rubro.actulizar_nombre('CURSO-PG: ' + self.curso.nombre)
                    else:
                        rubro.actulizar_nombre()
                    fechacuota = fechacuota + timedelta(days=30)

    def generar_rubro_descuento(self, descuento):
        curso = self.curso
        costomatricula = curso.costomatricula
        costocuota = curso.costocuota
        cuotas = curso.cuotas
        if curso.costodiferenciado:
            tipo = self.tipoestudiantecurso
            if CostodiferenciadoCursoPeriodo.objects.filter(tipocostocursoperiodo__tipocostocurso__cursoescuelacomplementaria=curso, tipo=tipo, tipocostocursoperiodo__periodo=curso.periodo, tipocostocursoperiodo__sede=curso.coordinacion.sede).exists():
                costotipo = CostodiferenciadoCursoPeriodo.objects.filter(tipocostocursoperiodo__tipocostocurso__cursoescuelacomplementaria=curso, tipo=tipo, tipocostocursoperiodo__periodo=curso.periodo, tipocostocursoperiodo__sede=curso.coordinacion.sede)[0]
                costomatricula = costotipo.costomatricula
                costocuota = costotipo.costocuota
                cuotas = costotipo.cuotas
        if costomatricula:
            costomatricula = costomatricula - ((descuento * costomatricula)/100)
            if not self.rubrocursoescuelacomplementaria_set.exists():
                rubro = Rubro(inscripcion=self.inscripcion,
                              fecha=curso.fecha_inicio,
                              iva_id=TIPO_IVA_0_ID,
                              valor=costomatricula,
                              fechavence=curso.fecha_inicio)
                rubro.save()
                rubrocurso = RubroCursoEscuelaComplementaria(rubro=rubro,
                                                             participante=self)
                rubrocurso.save()
                rubro.actulizar_nombre()
        if costocuota:
            fechacuota = curso.fecha_inicio
            for numerocuota in range(1, cuotas + 1):
                if not self.rubrocursoescuelacomplementaria_set.filter(cuota=numerocuota).exists():
                    rubro = Rubro(inscripcion=self.inscripcion,
                                  fecha=fechacuota,
                                  iva_id=TIPO_IVA_0_ID,
                                  valor=costocuota,
                                  fechavence=fechacuota)
                    rubro.save()
                    # rubrocurso = RubroCursoEscuelaComplementaria(rubro=rubro,
                    #                                              cuota=numerocuota,
                    #                                              participante=self)
                    rubrocurso.save()
                    rubro.actulizar_nombre()
                    fechacuota = fechacuota + timedelta(days=30)

    def save(self, *args, **kwargs):
        self.codigo = null_to_text(self.codigo)
        super(MatriculaCursoEscuelaComplementaria, self).save(*args, **kwargs)



class ActualizacionAsistencia(ModeloBase):
    materia = models.ForeignKey(Materia, blank=True, null=True, verbose_name=u'Materia', on_delete=models.CASCADE)


class TipoIncidencia(ModeloBase):
    sede = models.ForeignKey(Sede, verbose_name=u"Sede", on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=200, verbose_name=u"Nombre incidencia")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de Incidencias"
        ordering = ['sede', 'nombre']

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoIncidencia, self).save(*args, **kwargs)


class SubTipoincidencia(ModeloBase):
    tipo = models.ForeignKey(TipoIncidencia, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=500)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Subtipos de Incidencias"
        ordering = ['tipo', 'nombre']

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(SubTipoincidencia, self).save(*args, **kwargs)




class EvaluacionGenerica(ModeloBase):
    materiaasignada = models.ForeignKey(MateriaAsignada, verbose_name=u"Materia asignada", on_delete=models.CASCADE)
    detallemodeloevaluativo = models.ForeignKey(DetalleModeloEvaluativo, verbose_name=u'Detalle modelo evaluación', on_delete=models.CASCADE)
    valor = models.FloatField(default=0, verbose_name=u'Valor evaluación')

    class Meta:
        ordering = ['detallemodeloevaluativo']
        unique_together = ('materiaasignada', 'detallemodeloevaluativo',)

    def save(self, *args, **kwargs):
        if self.valor >= self.detallemodeloevaluativo.notamaxima:
            self.valor = self.detallemodeloevaluativo.notamaxima
        elif self.valor <= self.detallemodeloevaluativo.notaminima:
            self.valor = self.detallemodeloevaluativo.notaminima
        self.valor = null_to_numeric(self.valor, self.detallemodeloevaluativo.decimales)
        super(EvaluacionGenerica, self).save(*args, **kwargs)



class MateriaAsignadaRetiro(ModeloBase):
    materiaasignada = models.ForeignKey(MateriaAsignada, verbose_name=u"Materia asignada", on_delete=models.CASCADE)
    retiromatricula = models.ForeignKey(RetiroMatricula, blank=True, null=True, verbose_name=u"Retiro Matricula", on_delete=models.CASCADE)
    motivo = models.CharField(max_length=500, default='', verbose_name=u'Motivo')
    valida = models.BooleanField(default=False, verbose_name=u"Valida")
    fecha = models.DateField(blank=True, null=True)

    def __str__(self):
        return u'%s %s' % (self.materiaasignada.matricula.inscripcion.persona, self.materiaasignada.materia.asignatura)

    class Meta:
        unique_together = ('materiaasignada',)

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        super(MateriaAsignadaRetiro, self).save(*args, **kwargs)


class CategoriaReporte(ModeloBase):
    nombre = models.CharField(max_length=50, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Categorías de reportes"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(CategoriaReporte, self).save(*args, **kwargs)


class Reporte(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    descripcion = models.CharField(default='', max_length=200, verbose_name=u'Descripción')
    detalle = models.CharField(default='', max_length=400, verbose_name=u'Detalle')
    archivo = models.FileField(upload_to='reportes', blank=True, null=True, verbose_name=u'Archivo')
    categoria = models.ForeignKey(CategoriaReporte, verbose_name=u'Categoria', on_delete=models.CASCADE)
    grupos = models.ManyToManyField(Group, blank=True, verbose_name=u'Grupos')
    interface = models.BooleanField(default=False, verbose_name=u'Interface')
    formatoxls = models.BooleanField(default=True, verbose_name=u'Formatoxls')
    formatocsv = models.BooleanField(default=True, verbose_name=u'Formatocsv')
    formatoword = models.BooleanField(default=True, verbose_name=u'Formatoword')
    formatopdf = models.BooleanField(default=True, verbose_name=u'FormatoPDF')
    vista = models.TextField(default='', blank=True, null=True, verbose_name=u'vista')
    html = models.TextField(default='', blank=True, null=True, verbose_name=u'html')
    activo = models.BooleanField(default=False, verbose_name=u'activo')
    escertificadocurso = models.BooleanField(default=False, verbose_name=u'certificado curso')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Reportes"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def download_link(self):
        return self.archivo.url

    def parametros(self):
        return ParametroReporte.objects.filter(reporte=self).order_by('id')

    def tiporeporte(self):
        tipos = ''
        if self.formatoxls:
            tipos += ',xls'
        if self.formatoword:
            tipos += ',doc'
        if self.formatopdf:
            tipos += ',pdf'
        if self.formatocsv:
            tipos += ',csv'
        return tipos

    def existe(self, nombrereporte):
        return Reporte.objects.filter(nombre=nombrereporte).exists()

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre, lower=True)
        self.descripcion = null_to_text(self.descripcion, cap=True)
        self.detalle = null_to_text(self.detalle, cap=True)
        super(Reporte, self).save(*args, **kwargs)


class ParametroReporte(ModeloBase):
    reporte = models.ForeignKey(Reporte, verbose_name=u'Reporte', on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    descripcion = models.CharField(default='', max_length=200, verbose_name=u'Descripción')
    tipo = models.IntegerField(choices=TIPOS_PARAMETRO_REPORTE, default=1, verbose_name=u'Tipo de parametro')
    extra = models.TextField(default='', verbose_name=u'Clase relacionada', blank=True)

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Parametros de reportes"
        ordering = ['nombre']
        unique_together = ('reporte', 'nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre, lower=True)
        self.descripcion = null_to_text(self.descripcion, cap=True)
        self.extra = null_to_text(self.extra, transform=False)
        super(ParametroReporte, self).save(*args, **kwargs)


class ClienteFactura(ModeloBase):
    identificacion = models.CharField(default='', max_length=20, verbose_name=u'RUC')
    tipo = models.IntegerField(choices=TiposIdentificacion.choices, default=TiposIdentificacion.CEDULA, verbose_name=u"Tipo de identificación")
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    direccion = models.TextField(default='', verbose_name=u'Dirección')
    telefono = models.CharField(default='', max_length=50, verbose_name=u'Teléfono')
    email = models.CharField(default='', blank=True, null=True, max_length=200, verbose_name=u"Correo electrónico")

    def __str__(self):
        return u'Cliente No. %s %s' % (self.identificacion, self.nombre)

    class Meta:
        verbose_name_plural = u"Clientes de facturación"
        ordering = ['identificacion']

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.identificacion = null_to_text(self.identificacion)
        self.direccion = null_to_text(self.direccion)
        self.telefono = null_to_text(self.telefono)
        self.email = null_to_text(self.email, transform=False)
        super(ClienteFactura, self).save(*args, **kwargs)


class ClienteFacturaInscripcion(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion, on_delete=models.CASCADE)
    clientefactura = models.ForeignKey(ClienteFactura, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('inscripcion',)


class ModeloImpresion(ModeloBase):
    referencia = models.CharField(default='', max_length=40, verbose_name=u'Nombre')
    modelo = models.CharField(default='', max_length=100, verbose_name=u'Modelo')
    plantilla = models.CharField(default='', max_length=200, verbose_name=u'Plantilla')

    def __str__(self):
        return u'%s - %s - %s' % (self.referencia, self.modelo, self.plantilla)

    class Meta:
        verbose_name_plural = u"Diseño de impresiones"
        unique_together = ('modelo',)

    def save(self, *args, **kwargs):
        self.referencia = self.referencia.strip()
        self.modelo = self.modelo.strip()
        self.plantilla = self.plantilla.strip()
        super(ModeloImpresion, self).save(*args, **kwargs)


TIPO_EMISION_FACTURA = (
    (1, u'NORMAL'),
    (2, u'POR INDISPONIBILIDAD')
)

TIPO_AMBIENTE_FACTURACION = (
    (1, u'PRUEBAS'),
    (2, u'PRODUCCIÓN')
)


class PuntoVenta(ModeloBase):
    establecimiento = models.CharField(default='', max_length=3, verbose_name=u'Establecimiento')
    puntoventa = models.CharField(default='', max_length=3, verbose_name=u'Punto de venta')
    sede = models.ForeignKey(Sede, verbose_name=u'Sede', on_delete=models.CASCADE)
    activo = models.BooleanField(default=True, verbose_name=u'Activo')
    facturaelectronica = models.BooleanField(default=False, verbose_name=u'Factura electronica')
    secuenciafactura = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Secuencial Factura')
    secuenciarecibopago = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Secuencial Recibo Pago')
    autorizacion = models.CharField(default='', blank=True, max_length=100, verbose_name=u'Autorizacion SRI')
    numeracionemitida = models.BooleanField(default=False, verbose_name=u'Numeración emitida')
    imprimirfactura = models.BooleanField(default=False, verbose_name=u'Imprimir factura')
    imprimirrecibo = models.BooleanField(default=False, verbose_name=u'Imprimir recibo')
    tipoemision = models.IntegerField(choices=TIPO_EMISION_FACTURA, default=1, verbose_name=u"Tipo de identificación")
    ambientefacturacion = models.IntegerField(choices=TIPO_AMBIENTE_FACTURACION, default=2, verbose_name=u"Tipo de identificación")
    modeloimpresionfactura = models.ForeignKey(ModeloImpresion, blank=True, null=True, related_name="+", on_delete=models.CASCADE)
    modeloimpresionrecibopago = models.ForeignKey(ModeloImpresion, blank=True, null=True, related_name="+", on_delete=models.CASCADE)
    modeloimpresionnotacredito = models.ForeignKey(ModeloImpresion, blank=True, null=True, related_name="+", on_delete=models.CASCADE)

    def __str__(self):
        return u'%s-%s - %s' % (self.establecimiento, self.puntoventa, "ELECTRONICO" if self.facturaelectronica else "MANUAL")

    class Meta:
        verbose_name_plural = u"Puntos de venta"
        ordering = ['establecimiento']
        unique_together = ('establecimiento', 'puntoventa')

    def numeracion(self):
        return self.establecimiento + '-' + self.puntoventa

    def mis_cajeros(self):
        return self.lugarrecaudacion_set.all()

    def mis_cajeros_activos(self):
        return self.lugarrecaudacion_set.filter(activo=True)

    def secuencial_factura(self):
        self.secuenciafactura = int(self.secuenciafactura) + 1
        self.save()
        if Factura.objects.filter(numero=self.numeracion() + "-" + str(self.secuenciafactura).zfill(9)).exists():
            self.secuencial_factura()
        return self.secuenciafactura

    def secuencial_recibo(self):
        self.secuenciarecibopago = int(self.secuenciarecibopago) + 1
        self.save()
        if ReciboPago.objects.filter(numero=self.numeracion() + "-" + str(self.secuenciarecibopago).zfill(9)).exists():
            self.secuencial_recibo()
        return self.secuenciarecibopago

    def save(self, *args, **kwargs):
        self.establecimiento = null_to_text(self.establecimiento)
        self.puntoventa = null_to_text(self.puntoventa)
        self.autorizacion = null_to_text(self.autorizacion)
        super(PuntoVenta, self).save(*args, **kwargs)


class LugarRecaudacion(ModeloBase):
    persona = models.ForeignKey(Persona, verbose_name=u'Persona', on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    puntodeventa = models.ForeignKey(PuntoVenta, blank=True, null=True, verbose_name=u'Punto de venta', on_delete=models.CASCADE)
    activo = models.BooleanField(default=True, verbose_name=u'Activo')
    automatico = models.BooleanField(default=False, verbose_name=u'Automatico')
    usuariocontable = models.CharField(blank=True, null=True, max_length=15, verbose_name=u'Codigo contable')

    class Meta:
        verbose_name_plural = u"Lugares de recaudación"
        ordering = ['nombre']
        unique_together = ('persona', 'puntodeventa', )

    def __str__(self):
        return u'%s %s' % (self.nombre, self.persona)

    def esta_abierta(self):
        return SesionCaja.objects.filter(caja=self, abierta=True).exists()

    def sesion_caja(self):
        if SesionCaja.objects.filter(caja=self, abierta=True).exists():
            return SesionCaja.objects.filter(caja=self, abierta=True)[0]
        return None

    def sesion_caja_automatica(self):
        hoy = datetime.now().date()
        if SesionCaja.objects.filter(caja=self, abierta=True, fecha__lt=hoy).exists():
            anterior = SesionCaja.objects.filter(caja=self, abierta=True, fecha__lt=hoy)[0]
            anterior.abierta = False
            anterior.save()
            cierre = CierreSesionCaja(sesion=anterior,
                                      fecha=hoy,
                                      hora=datetime.now().time())
            cierre.save()
            cierre.actualiza_valores()
        if SesionCaja.objects.filter(caja=self, abierta=True, fecha=hoy).exists():
            caja = SesionCaja.objects.filter(caja=self, abierta=True, fecha=hoy)[0]
        else:
            caja = SesionCaja(caja=self,
                              fecha=hoy,
                              hora=datetime.now().time())
            caja.save()
        return caja

    def sesion_fecha(self, fecha):
        if self.sesioncaja_set.filter(fecha=fecha).exists():
            return self.sesioncaja_set.filter(fecha=fecha)
        return None

    def puede_eliminarse(self):
        return not self.sesioncaja_set.exists()

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(LugarRecaudacion, self).save(*args, **kwargs)


class ProcesadorPagoTarjeta(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    paymentuserid = models.CharField(default='', max_length=500, verbose_name=u'User id')
    paymentpassword = models.CharField(default='', max_length=500, verbose_name=u'Password')
    paymententityid = models.CharField(default='', max_length=50, verbose_name=u'Entidad')
    mid = models.CharField(default='', max_length=1500, verbose_name=u'MID')
    tid = models.CharField(default='', max_length=500, verbose_name=u'TID')
    paymenturl = models.CharField(default='', max_length=500, verbose_name=u'URL')
    paymenturlprueba = models.CharField(default='', max_length=500, verbose_name=u'URL')
    refoundurl = models.CharField(default='', max_length=500, verbose_name=u'URL')
    refoundurlprueba = models.CharField(default='', max_length=500, verbose_name=u'URL')
    scripturl = models.CharField(default='', max_length=500, verbose_name=u'URL')
    scripturlprueba = models.CharField(default='', max_length=500, verbose_name=u'URL')
    permitepagoonline = models.BooleanField(default=False, verbose_name=u'Permite pago online')
    pruebas = models.BooleanField(default=False, verbose_name=u'Modo prueba')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')
    pagominimodiferido = models.FloatField(default=0, verbose_name=u'Pago minimo')
    comision = models.FloatField(default=0, verbose_name=u'Comision')
    urlretorno = models.CharField(default='', max_length=500, verbose_name=u'URL')
    ip = models.CharField(default='', max_length=15, verbose_name=u'IP')
    codigocorriente = models.CharField(default='', max_length=5, verbose_name=u'codigo corriente')
    nombrecomercio = models.CharField(default='', max_length=50, verbose_name=u'Nombre comercio')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Procesadores de pago de tarjetas"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def en_uso(self):
        if self.pagotarjeta_set.exists():
            return True
        if self.recibocajainstitucion_set.exists():
            return True
        return False

    def identificador_emisor(self, emisor):
        if not self.identificaciontipoemisortarjeta_set.filter(tipoemisortarjeta=emisor).exists():
            identificador = IdentificacionTipoEmisorTarjeta(tipoemisortarjeta=emisor,
                                                            procesadorpagotarjeta=self)
            identificador.save()
        else:
            identificador = self.identificaciontipoemisortarjeta_set.filter(tipoemisortarjeta=emisor)[0]
        return identificador

    def generar_tarjetas(self):
        for emisor in TipoEmisorTarjeta.objects.all():
            self.identificador_emisor(emisor)

    def es_datafast(self):
        return self.id == PROVEEDOR_PAGOONLINE_DATAFAST

    def es_payphone(self):
        return self.id == PROVEEDOR_PAGOONLINE_PAYPHONE

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.nombrecomercio = null_to_text(self.nombrecomercio)
        self.codigocorriente = null_to_text(self.codigocorriente)
        super(ProcesadorPagoTarjeta, self).save(*args, **kwargs)


class IvaAplicado(ModeloBase):
    descripcion = models.CharField(max_length=300, verbose_name=u'Nombre')
    porcientoiva = models.FloatField(default=0, verbose_name=u'% IVA aplicado')
    codigo = models.IntegerField(default=0, verbose_name=u'Codigo')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return u'%s' % self.descripcion

    class Meta:
        verbose_name = u"IVA aplicado"
        verbose_name_plural = u"IVA aplicados"

    def save(self, *args, **kwargs):
        self.descripcion = null_to_text(self.descripcion)
        super(IvaAplicado, self).save(*args, **kwargs)

class Cliente(ModeloBase):
    persona = models.ForeignKey(Persona, verbose_name=u"Persona", on_delete=models.CASCADE)
    empresa = models.ForeignKey(EmpresaEmpleadora, verbose_name=u"Empresa",blank=True, null=True, on_delete=models.CASCADE)
    activo = models.BooleanField(default=True, verbose_name=u"Activo")

    def chequea_mora(self):
        for rubro in self.rubro_set.filter(cancelado=False):
            rubro.cheque_mora()

    def total_rubros(self):
        return null_to_numeric(self.rubro_set.aggregate(valor=Sum('valortotal'))['valor'], 2)

    def total_rubros_sin_notadebito(self):
        return null_to_numeric(
            self.rubro_set.exclude(rubronotadebito__rubro__inscripcion=self).aggregate(valor=Sum('valortotal'))[
                'valor'], 2)

    def total_rubros_pendientes(self):
        return null_to_numeric(self.rubro_set.filter(cancelado=False).aggregate(valor=Sum('saldo'))['valor'], 2)

    def rubros_pendientes(self):
        return self.rubro_set.filter(cancelado=False).order_by('fechavence')

    def total_descuento(self):
        return null_to_numeric(
            DescuentoRecargoRubro.objects.filter(rubro__cliente=self, recargo=False).distinct().aggregate(
                valor=Sum('valordescuento'))['valor'], 2)

    def total_descuento_pendiente(self):
        return null_to_numeric(DescuentoRecargoRubro.objects.filter(rubro__cliente=self, recargo=False,
                                                                    rubro__cancelado=False).distinct().aggregate(
            valor=Sum('valordescuento'))['valor'], 2)

    def total_liquidado(self):
        return null_to_numeric(
            RubroLiquidado.objects.filter(rubro__cliente=self).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def total_pagado(self):
        return null_to_numeric(
            Pago.objects.filter(rubro__cliente=self, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def total_pagado_periodo(self, periodo):
        return null_to_numeric(
            Pago.objects.filter(rubro__cliente=self, rubro__periodo=periodo, valido=True).aggregate(
                valor=Sum('valor'))['valor'], 2)

    def total_valores_periodo(self, periodo):
        return null_to_numeric(
            Rubro.objects.filter(inscripcion=self, periodo=periodo).aggregate(valor=Sum('valor'))['valor'], 2)

    def total_valores_periodo_prontopago(self, periodo):
        return null_to_numeric(Rubro.objects.filter(inscripcion=self, periodo=periodo, validoprontopago=True).aggregate(
            valor=Sum('valor'))['valor'], 2)

    def total_cancelado(self):
        return null_to_numeric(
            PagoCancelado.objects.filter(rubro__cliente=self).aggregate(valor=Sum('valor'))['valor'], 2)

    def total_pagado_pendiente(self):
        return null_to_numeric(
            Pago.objects.filter(rubro__cliente=self, rubro__cancelado=False, valido=True).aggregate(
                valor=Sum('valor'))['valor'], 2)

    def total_notacredito(self):
        return null_to_numeric(self.notacredito_set.all().aggregate(valor=Sum('valorinicial'))['valor'], 2)

    def total_adeudado(self):
        return null_to_numeric(self.rubro_set.aggregate(valor=Sum('saldo'))['valor'], 2)

    def adeuda_a_la_fecha(self):
        return null_to_numeric(
            self.rubro_set.filter(fechavence__lt=datetime.now().date()).aggregate(valor=Sum('saldo'))['valor'], 2)

    def credito_a_la_fecha(self):
        return null_to_numeric(
            self.rubro_set.filter(fechavence__gte=datetime.now().date()).aggregate(valor=Sum('saldo'))['valor'], 2)

    def tiene_deuda_vencida(self):
        return self.rubro_set.filter(cancelado=False, fechavence__lt=datetime.now().date()).exists()

    def tiene_deuda_fuera_periodo(self, periodo):
        return Rubro.objects.filter(cancelado=False, fechavence__lt=datetime.now().date(), inscripcion=self).exclude(
            periodo=periodo).exists()

    def tiene_deuda(self):
        return self.rubro_set.filter(cancelado=False).exists()

    def tiene_deuda_orientacion(self):
        return self.rubro_set.filter(cancelado=True, nombre='DERECHO ORIENTACIÓN PROFESIONAL').exists()

    def tiene_deuda_inscripcion(self):
        return self.rubro_set.filter(nombre__icontains='INSCRIPCION').exists()

    def tiene_deuda_inscripcion_pagada(self):
        return self.rubro_set.filter(cancelado=True, nombre__icontains='INSCRIPCION').exists()

    def tiene_credito(self):
        return self.rubro_set.filter(cancelado=False, fechavence__gte=datetime.now().date()).exists()

    def __str__(self):
        return u'%s' % self.persona

class Rubro(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion, blank=True, null=True,  verbose_name=u'Inscripción', on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, blank=True, null=True,  verbose_name=u'Cliente', on_delete=models.CASCADE)
    persona = models.ForeignKey(Persona, blank=True, null=True,  verbose_name=u'Persona', on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=300, verbose_name=u'Nombre')
    fecha = models.DateField(verbose_name=u'Fecha')
    fechavence = models.DateField(verbose_name=u'Fecha vencimiento')
    valor = models.FloatField(default=0, verbose_name=u'Valor')
    iva = models.ForeignKey(IvaAplicado, verbose_name=u'IVA', on_delete=models.CASCADE)
    valoriva = models.FloatField(default=0, verbose_name=u'Valor IVA')
    valortotal = models.FloatField(default=0, verbose_name=u'Valor total')
    saldo = models.FloatField(default=0, verbose_name=u'Saldo')
    cancelado = models.BooleanField(default=False, verbose_name=u'Cancelado')
    pasivo = models.BooleanField(default=False, verbose_name=u'Pasivo')
    fechapasivo = models.DateField(null=True, verbose_name=u'Fecha pasivo')
    motivopasivo = models.TextField(default='', verbose_name=u'Motivo')
    valornivelactual = models.FloatField(default=0, verbose_name=u'Valor nivel actual')
    observacion = models.TextField(default='', verbose_name=u'Observacion')
    validoprontopago = models.BooleanField(default=False, verbose_name=u'Pronto pago')
    valorajuste = models.FloatField(default=0, verbose_name=u'Valor Ajuste')
    motivoajuste = models.TextField(default='', verbose_name=u'Motivo Ajuste')

    def __str__(self):
        return u'%s - %s - %s' % (self.nombre, self.fechavence.strftime("%d-%m-%Y"), str(self.valor))

    class Meta:
        verbose_name_plural = u"Rubros"

    def extra_delete(self):
        if self.pago_set.exists():
            return [False, False]
        for recargo in DescuentoRecargoRubro.objects.filter(rubro=self, recargo=True):
            rubrorecargo = recargo.rubro
            if rubrorecargo.pago_set.exists():
                return [False, False]
        return [True, False]

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Rubro.objects.filter(Q(inscripcion__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.nombre + ' - ' + str(self.id)

    def tiene_pagos(self):
        return self.pago_set.filter(valido=True).exists()

    def liquidado(self):
        return self.rubroliquidado_set.exists()

    def datos_liqidacion(self):
        if self.liquidado():
            return self.rubroliquidado_set.all()[0]
        return None

    def solo_pago_notacredito(self):
        if self.pago_set.exists():
            for pago in self.pago_set.all():
                if pago.es_notacredito():
                    return True
        return False

    def es_especie(self):
        return self.rubroespecievalorada_set.exists()

    def es_notadebito(self):
        return self.rubronotadebito_set.exists()

    def es_solicitud(self):
        return self.rubrootro_set.filter(solicitud__isnull=False).exists()

    def dato_solicitud(self):
        if self.es_solicitud():
            return self.rubrootro_set.filter(solicitud__isnull=False)[0].solicitud
        return None

    def dato_otro(self):
        return self.rubrootro_set.all()[0]

    def es_cuota(self):
        return self.rubrocuota_set.exists()

    def es_matricula(self):
        if self.rubromatricula_set.exists():
            return True
        if self.rubrocuota_set.exists():
            return True
        if self.rubrootromatricula_set.exists():
            return True
        if self.rubroagregacion_set.exists():
            return True
        if self.rubromateria_set.exists():
            return True
        if self.rubroderecho_set.exists():
            return True
        return False

    def matricula(self):
        if self.rubromatricula_set.exists():
            return self.rubromatricula_set.all()[0].matricula if self.rubromatricula_set.all()[0].matricula else self.rubromatricula_set.all()[0].matriculainternado
        if self.rubrocuota_set.exists():
            return self.rubrocuota_set.all()[0].matricula if self.rubrocuota_set.all()[0].matricula else self.rubrocuota_set.all()[0].matriculainternado
        if self.rubrootromatricula_set.exists():
            return self.rubrootromatricula_set.all()[0].matricula
        if self.rubroagregacion_set.exists():
            return self.rubroagregacion_set.all()[0].materiaasignada.matricula
        if self.rubromateria_set.exists():
            return self.rubromateria_set.all()[0].materiaasignada.matricula
        if self.rubroderecho_set.exists():
            return self.rubroderecho_set.all()[0].materiaasignada.matricula
        return None

    def es_otromatricula(self):
        return self.rubrootromatricula_set.exists()

    def es_materia(self):
        return self.rubromateria_set.exists()

    def es_inscripcion(self):
        return self.rubroinscripcion_set.exists()

    def es_anticipo(self):
        return self.rubroanticipado_set.exists()

    def es_derechoexamen(self):
        return self.rubroderecho_set.exists()

    def es_otro(self):
        return self.rubrootro_set.exists()

    def es_agregacion(self):
        return self.rubroagregacion_set.exists()

    def es_curso(self):
        return self.rubrocursoescuelacomplementaria_set.exists()


    def es_mora(self):
        return self.rubrootro_set.filter(tipo__id=TIPO_MORA_RUBRO).exists()

    def es_recargodescuento(self):
        return DescuentoRecargoRubro.objects.filter(rubrorecargo=self).exists()

    def origen_recargodescuento(self):
        if self.es_recargodescuento():
            return DescuentoRecargoRubro.objects.filter(rubrorecargo=self)[0]
        return None

    def reporte_especie(self):
        if self.rubroespecievalorada_set.exists():
            return self.rubroespecievalorada_set.all()[0]
        return None

    def notadebito(self):
        if self.rubronotadebito_set.exists():
            return self.rubronotadebito_set.all()[0]
        return None

    def vencido(self):
        return not self.cancelado and self.fechavence < datetime.now().date()

    def con_descuentourecargo(self):
        return DescuentoRecargoRubro.objects.filter(rubro=self).exists()

    def con_recargo(self):
        return DescuentoRecargoRubro.objects.filter(rubro=self, recargo=True).exists()

    def total_recargo(self):
        if self.con_recargo():
            return DescuentoRecargoRubro.objects.filter(rubro=self, recargo=True)[0].rubrorecargo.valor
        return 0

    def tiene_descuentorecargo(self):
        return DescuentoRecargoRubro.objects.filter(rubro=self).exists()

    def tiene_descuento(self):
        return DescuentoRecargoRubro.objects.filter(rubro=self, recargo=False).exists()

    def tiene_descuento_total(self):
        return null_to_numeric(DescuentoRecargoRubro.objects.filter(rubro=self, recargo=False).aggregate(valor=Sum('valordescuento'))['valor'], 2) >= self.valor

    def tiene_recargo(self):
        return DescuentoRecargoRubro.objects.filter(rubro=self, recargo=True).exists()

    def tiene_iva(self):
        return Rubro.objects.filter(pk=self.id, iva_id__gt=1).exists()

    def descuento(self):
        if DescuentoRecargoRubro.objects.filter(rubro=self, recargo=False).exists():
            return DescuentoRecargoRubro.objects.filter(rubro=self, recargo=False)[0]
        return None

    def recargo(self):
        if DescuentoRecargoRubro.objects.filter(rubro=self, recargo=True).exists():
            return DescuentoRecargoRubro.objects.filter(rubro=self, recargo=True)[0]
        return None

    def ultimo_pago(self):
        if self.tiene_pagos():
            return self.pago_set.all().order_by('-fecha')[0]
        return None

    def puede_eliminarse(self):
        return not self.cancelado and not self.pago_set.filter(valido=True).exists() and not self.rubronotadebito_set.exists()

    def tipo_especie(self):
        if self.es_especie():
            return self.rubroespecievalorada_set.all()[0].tipoespecie_id
        return None

    def valor_beca(self):
        if self.rubrookbeca_set.exists():
            descuento = self.descuento()
            return descuento.valordescuento
        return 0

    def beca_aplicada(self):
        return self.rubrookbeca_set.exists()

    def aplica_a_beca(self):
        if self.es_matricula():
            if not self.beca_aplicada():
                return True
        return False

    def adeuda(self):
        if not self.liquidado():
            return self.adeudado() > 0
        return False

    def liquidar(self, motivo):
        rubroliquidado = RubroLiquidado(rubro=self,
                                        fecha=datetime.now().date(),
                                        motivo=motivo,
                                        valor=self.saldo)
        rubroliquidado.save()
        self.save()

    def total_valor_descuento(self):
        return null_to_numeric(DescuentoRecargoRubro.objects.filter(rubro=self, recargo=False).aggregate(valor=Sum('valordescuento'))['valor'], 2)

    def total_pagado(self):
        cancelado = null_to_numeric(self.pagocancelado_set.aggregate(valor=Sum('valor'))['valor'], 2)
        pagado = null_to_numeric(Pago.objects.filter(rubro=self).aggregate(valor=Sum('valor'))['valor'], 2)
        return null_to_numeric(pagado - cancelado, 2)

    def total_cancelado(self):
        return null_to_numeric(self.pagocancelado_set.aggregate(valor=Sum('valor'))['valor'], 2)

    def adeudado(self):
        if not self.liquidado():
            if int(self.iva_id) > 1:
                return null_to_numeric(self.valortotal - null_to_numeric(self.total_pagado() + self.total_valor_descuento(), 2), 2)
            else:
                return null_to_numeric(self.valor - null_to_numeric(self.total_pagado() + self.total_valor_descuento(), 2), 2)
        return 0

    # def adeudado(self):
    #     if not self.liquidado():
    #         if not self.tiene_descuento_total():
    #             return null_to_numeric(self.valortotal - null_to_numeric(self.total_pagado(), 2), 2)
    #     return 0

    def nivel(self):
        if self.es_matricula():
            return self.matricula().nivelmalla
        return None

    def tipo(self):
        if self.rubroinscripcion_set.exists():
            return "INSCRIPCION"
        if self.rubroanticipado_set.exists():
            return "ANTICIPO"
        if self.rubromatricula_set.exists():
            return "MATRICULA"
        if self.rubrootromatricula_set.exists():
            return self.rubrootromatricula_set.all()[0].descripcion
        if self.rubromateria_set.exists():
            return "MATERIA"
        if self.rubroderecho_set.exists():
            return "DERECHO DE EXAMEN"
        if self.rubrootro_set.exists():
            return "OTRO - " + self.rubrootro_set.all()[0].tipo.nombre
        if self.rubroespecievalorada_set.exists():
            return "ESPECIE"
        if self.rubrocuota_set.exists():
            return "ARANCEL"
        if self.rubrocursoescuelacomplementaria_set.exists():
            return "CURSO"
        if self.rubroagregacion_set.exists():
            return "AGREGACION MATERIAS"
        if self.rubronotadebito_set.exists():
            return "NOTA DE DEBITO"
        return "OTRO"

    def periodo_relacionado(self):
        if self.rubroinscripcion_set.exists():
            return self.rubroinscripcion_set.all()[0].inscripcion.periodo
        if self.rubroanticipado_set.exists():
            return self.periodo
        if self.rubromatricula_set.exists():
            return self.rubromatricula_set.all()[0].matricula.nivel.periodo if self.rubromatricula_set.all()[0].matricula else self.periodo
        if self.rubrootromatricula_set.exists():
            return self.rubrootromatricula_set.all()[0].matricula.nivel.periodo
        if self.rubromateria_set.exists():
            return self.rubromateria_set.all()[0].materiaasignada.matricula.nivel.periodo
        if self.rubroderecho_set.exists():
            return self.rubroderecho_set.all()[0].materiaasignada.matricula.nivel.periodo
        if self.rubrootro_set.exists():
            return self.periodo
        if self.rubroespecievalorada_set.exists():
            return self.periodo
        if self.rubrocuota_set.exists():
            return self.rubrocuota_set.all()[0].matricula.nivel.periodo if self.rubrocuota_set.all()[0].matricula else self.periodo
        if self.rubrocursoescuelacomplementaria_set.exists():
            return self.rubrocursoescuelacomplementaria_set.all()[0].participante.curso.periodo
        if self.rubroagregacion_set.exists():
            return self.rubroagregacion_set.all()[0].materiaasignada.matricula.nivel.periodo
        if self.rubronotadebito_set.exists():
            return self.periodo
        return None

    def tipo_exp(self):
        if self.rubroinscripcion_set.exists():
            return "INS"
        if self.rubroanticipado_set.exists():
            return "ANT"
        if self.rubromatricula_set.exists():
            return "MAT"
        if self.rubrootromatricula_set.exists():
            return "OTM"
        if self.rubromateria_set.exists():
            return "MAR"
        if self.rubroderecho_set.exists():
            return "DER"
        if self.rubrootro_set.exists():
            return "OTR"
        if self.rubroespecievalorada_set.exists():
            return "ESP"
        if self.rubrocuota_set.exists():
            return "CUO"
        if self.rubrocursoescuelacomplementaria_set.exists():
            rubrocurso = self.relacionado()
            if rubrocurso.participante.curso.coordinacion.id in (16, 17):
                return "CURI"
            elif rubrocurso.participante.curso.coordinacion.id in (22, 23):
                return "CURF"
            elif rubrocurso.participante.curso.coordinacion.id == 28:
                return "CURV"
            else:
                return "CUR"
        if self.rubrocursoescuelacomplementaria_set.exists():
            return "CUR"
        if self.rubroagregacion_set.exists():
            return "AGR"
        if self.rubronotadebito_set.exists():
            return "NDB"
        return "OTR"

    def tipo_exp_rel(self):
        if self.rubroespecievalorada_set.exists():
            return str(self.rubroespecievalorada_set.all()[0].tipoespecie.id)
        if self.rubrocursoescuelacomplementaria_set.exists():
            return str(self.rubrocursoescuelacomplementaria_set.all()[0].participante.curso.tipocurso.id)
        return ""

    def relacionado(self):
        if self.rubroinscripcion_set.exists():
            return self.rubroinscripcion_set.all()[0]
        if self.rubroanticipado_set.exists():
            return self.rubroanticipado_set.all()[0]
        if self.rubromatricula_set.exists():
            return self.rubromatricula_set.all()[0]
        if self.rubrootromatricula_set.exists():
            return self.rubrootromatricula_set.all()[0]
        if self.rubromateria_set.exists():
            return self.rubromateria_set.all()[0]
        if self.rubroderecho_set.exists():
            return self.rubroderecho_set.all()[0]
        if self.rubrootro_set.exists():
            return self.rubrootro_set.all()[0]
        if self.rubroespecievalorada_set.exists():
            return self.rubroespecievalorada_set.all()[0]
        if self.rubrocuota_set.exists():
            return self.rubrocuota_set.all()[0]
        if self.rubrocursoescuelacomplementaria_set.exists():
            return self.rubrocursoescuelacomplementaria_set.all()[0]
        if self.rubroagregacion_set.exists():
            return self.rubroagregacion_set.all()[0]
        if self.rubronotadebito_set.exists():
            return self.rubronotadebito_set.all()[0]
        return None

    def nombre_completo(self):
        if self.rubroinscripcion_set.exists():
            return u"INSCRIPCION"
        if self.rubroanticipado_set.exists():
            return u"ANTICIPO"
        if self.rubrocuota_set.exists():
            if self.matricula().inscripcion.carrera.posgrado :
                return u"COSTO MODULO MAESTRIA"
            else:
                return u"ARANCELES CUOTA # %s/%s %s"[:299] % (str(self.rubrocuota_set.all()[0].cuota), str(self.rubrocuota_set.all()[0].totalcuota), self.rubrocuota_set.all()[0].nombre_corto())
        if self.rubromatricula_set.exists():
            return u"MATRICULA: %s"[:299] % self.rubromatricula_set.all()[0].nombre_corto()
        if self.rubrootromatricula_set.exists():
            return u"%s"[:299] % self.rubrootromatricula_set.all()[0].descripcion
        if self.rubromateria_set.exists():
            return u"ARANCEL: %s"[:299] % self.rubromateria_set.all()[0].materiaasignada.materia.asignatura.nombre
        if self.rubroderecho_set.exists():
            return u"DERECHO DE EXAMEN: %s"[:299] % self.rubroderecho_set.all()[0].materiaasignada.materia.asignatura.nombre
        if self.rubroagregacion_set.exists():
            return u"ARANCEL: %s"[:299] % self.rubroagregacion_set.all()[0].materiaasignada.materia.asignatura.nombre
        if self.rubrocursoescuelacomplementaria_set.exists():
            return u"CURSO: %s"[:299] % self.rubrocursoescuelacomplementaria_set.all()[0].participante.curso.nombre
        if self.rubroespecievalorada_set.exists():
            return u"%s"[:299] % self.rubroespecievalorada_set.all()[0].tipoespecie.nombre
        if self.rubronotadebito_set.exists():
            return u"%s"[:299] % self.rubronotadebito_set.all()[0].motivo
        return u"OTRO"

    def actulizar_nombre(self, nombre=None):
        if nombre:
            self.nombre = nombre
        if not self.nombre:
            self.nombre = self.nombre_completo()
        self.periodo = self.periodo_relacionado()
        self.save()

    def verifica_rubro_otro(self, tipo):
        if not self.relacionado():
            rubrootro = RubroOtro(rubro=self,
                                  tipo_id=tipo)
            rubrootro.save()

    def cheque_mora(self):
        if GENERAR_RUBRO_MORA:
            if self.vencido() and not self.es_mora() and not self.con_descuentourecargo():
                if (self.es_cuota() and GENERAR_RUBRO_MORA_CUOTA) or (self.es_matricula() and GENERAR_RUBRO_MORA_MATRICULA):
                    rubrorecargo = Rubro(fecha=self.fecha,
                                         valor=VALOR_MORA_RUBRO,
                                         inscripcion=self.inscripcion,
                                         cancelado=False,
                                         fechavence=self.fechavence)
                    rubrorecargo.save()
                    rubrorecargootro = RubroOtro(rubro=rubrorecargo,
                                                 tipo_id=TIPO_MORA_RUBRO)
                    rubrorecargootro.save()
                    rubrorecargo.actulizar_nombre()
                    recargo = DescuentoRecargoRubro(rubro=self,
                                                    rubrorecargo=rubrorecargo,
                                                    recargo=True,
                                                    motivo='RECARGO POR MORA',
                                                    precio=rubrorecargo.valor,
                                                    fecha=datetime.now().date())
                    recargo.save()

    def rubro_beca(self):
        if self.rubrookbeca_set.exists():
            return self.rubrookbeca_set.all()[0]
        else:
            rokbeca = RubroOkBeca(rubro=self,
                                  fecha=datetime.now().date())
            rokbeca.save()
            return rokbeca

    def valor_con_descuento(self):
        return null_to_numeric(self.valor - self.total_valor_descuento(), 2)

    def tipoprimerpago(self):
        pago = self.pago_set.all().order_by('id').first()
        return pago

    def save(self, *args, **kwargs):
        super(Rubro, self).save(*args, **kwargs)
        institucion = mi_institucion()
        descuento = 0
        if self.id:
            descuento = self.total_valor_descuento()
        porcientoiva = float(self.iva.porcientoiva)
        if not self.id:
            if self.valortotal > 0:
                self.valortotal = null_to_numeric(self.valortotal, 2)
                self.valoriva = null_to_numeric(self.valortotal - (self.valortotal / (1 + porcientoiva)), 2)
                self.valor = null_to_numeric(self.valortotal - self.valoriva, 2)
            else:
                self.valor = null_to_numeric(self.valor - descuento, 2)
                self.valoriva = null_to_numeric(self.valor * porcientoiva, 2)
                self.valortotal = null_to_numeric(self.valor + self.valoriva, 2)
            self.saldo = self.valortotal
        else:
            self.valoriva = null_to_numeric((self.valor - descuento) * porcientoiva, 2)
            self.valortotal = null_to_numeric((self.valor - descuento) + self.valoriva, 2)
            self.saldo = self.adeudado()
        if self.saldo <= 0:
            self.cancelado = True
        else:
            self.cancelado = False
        if self.id:
            if not self.es_curso():
                if self.es_otro():
                    relacionado = self.relacionado()
                    # Tipo 23 "Examen ubicacion"
                    if relacionado.tipo_id == 23:
                        valortotalexamen = self.valortotal
                        valorpagadoexamen = 0
                        for p in Pago.objects.filter(rubro__inscripcion=self.inscripcion, rubro__periodo=self.periodo, rubro=self, valido=True):
                            valorpagadoexamen += p.valor
                        if valortotalexamen == valorpagadoexamen:
                            matriculaexamen = ProcesoAplicanteExamenSuficiencia.objects.filter(inscripcion=self.inscripcion, convocatoria__periodo=self.periodo, formalizada=False)[0]
                            matriculaexamen.formalizada = True
                            matriculaexamen.save()
                    # Tipo 24 "Solicitud Parqueadero"
                    if relacionado.tipo_id == 24:
                        if SolicitudParqueo.objects.filter(inscripcion=self.inscripcion, periodo=self.periodo, activo=True).exists():
                            valortotalparqueo = self.valortotal
                            valorpagadoparqueo = 0
                            for p in Pago.objects.filter(rubro__inscripcion=self.inscripcion, rubro__periodo=self.periodo, rubro=self, valido=True):
                                valorpagadoparqueo += p.valor
                                if valorpagadoparqueo >= valortotalparqueo:
                                    solicitudparqueo = SolicitudParqueo.objects.get(inscripcion=self.inscripcion, periodo=self.periodo, activo=True)
                                    solicitudparqueo.formalizada = True
                                    solicitudparqueo.save()
                else:
                    if not self.es_otromatricula():
                        if self.es_cuota() or self.es_matricula() or self.es_agregacion():
                            if self.inscripcion.matriculado_periodo(self.periodo):
                                from ctt.adm_calculofinanzas import calculo_costo_total
                                matriculaperiodo = self.inscripcion.matricula_periodo(self.periodo)
                                totalperiodo = calculo_costo_total(matriculaperiodo)
                                valortotalperiodo = totalperiodo[8]
                            else:
                                valortotalperiodo = 0
                            valorpagado = 0
                            for p in Pago.objects.filter(Q(rubro__rubromatricula__isnull=False) | Q(rubro__rubrocuota__isnull=False) | Q(rubro__rubroagregacion__isnull=False), rubro__inscripcion=self.inscripcion, rubro__periodo=self.periodo, valido=True):
                                valorpagado += p.valor
                            if valortotalperiodo > 0:
                                porcentaje = round((valorpagado * 100)/valortotalperiodo, 2)
                            else:
                                porcentaje = 0
                            if institucion.formalizarxporcentaje is True:
                                if porcentaje >= institucion.porcentajeformalizar:
                                    if self.inscripcion.matriculado_periodo(self.periodo):
                                        matricula = self.inscripcion.matricula_periodo(self.periodo)
                                        matricula.formalizada = True
                                        try:
                                            if matricula.inscripcion.idsalesforcei:
                                                api_token_sf2.enviar_cumple_arancel(matricula.inscripcion.idsalesforcei, matricula.inscripcion.idsalesforcei, matricula.inscripcion.carrera.id, matricula.inscripcion.modalidad.id, matricula.inscripcion.sede.id, valorpagado)
                                        except Exception as ex:
                                            print(f"Error lanzando el envío de cumple arancel: {ex}")
                                        matricula.save()
                                        Matricula.objects.filter(pk=matricula.id).update(tienepagominimo=True)
                                    else:
                                        if self.inscripcion.tiene_matricula_internado_rotatito(self.periodo):
                                            matricula = self.inscripcion.matricula_periodo_internado_rotativo(self.periodo)
                                            matricula.formalizada = True
                                            matricula.save()
                            else:
                                if self.inscripcion.matriculado_periodo(self.periodo):
                                    matricula = self.inscripcion.matricula_periodo(self.periodo)
                                    if matricula.pago_matricula():
                                        if self.inscripcion.matriculado_periodo(self.periodo):
                                            matricula = self.inscripcion.matricula_periodo(self.periodo)
                                            matricula.formalizada = True
                                            try:
                                                if matricula.inscripcion.idsalesforcei:
                                                    api_token_sf2.enviar_cumple_arancel(matricula.inscripcion.idsalesforcei,matricula.inscripcion.idsalesforcei,matricula.inscripcion.carrera.id,matricula.inscripcion.modalidad.id,matricula.inscripcion.sede.id,valorpagado)
                                            except Exception as ex:
                                                print(f"Error lanzando el envío de cumple arancel: {ex}")
                                            matricula.save()
                                            Matricula.objects.filter(pk=matricula.id).update(tienepagominimo=True)
                                else:
                                    if self.inscripcion.tiene_matricula_internado_rotatito(self.periodo):
                                        matricula = self.inscripcion.matricula_periodo_internado_rotativo(self.periodo)
                                        if matricula.pago_matricula():
                                            matricula.formalizada = True
                                            matricula.save()
            else:
                valortotalcurso = self.valortotal
                valorpagadocurso = 0
                for p in Pago.objects.filter(rubro__inscripcion=self.inscripcion, rubro__periodo=self.periodo, rubro=self, valido=True):
                    valorpagadocurso += p.valor
                if valortotalcurso == valorpagadocurso:
                    rubrocurso = RubroCursoEscuelaComplementaria.objects.get(rubro=self)
                    matriculacurso = rubrocurso.participante
                    matriculacurso.formalizada = True
                    matriculacurso.save()
        try:
            if self.inscripcion.idsalesforcei:
                inscripcion = self.inscripcion
                total_saldo1 = Rubro.objects.filter(inscripcion=inscripcion, nombre__icontains="inscripcion", saldo__gte=0).aggregate(total_saldo1=Sum('saldo'))['total_saldo1'] or 0  # Manejo de None
                total_saldo2 = Rubro.objects.filter(inscripcion=inscripcion, nombre__icontains="induccion", saldo__gte=0).aggregate(total_saldo2=Sum('saldo'))['total_saldo2'] or 0  # Manejo de None
                total_saldo3 = Rubro.objects.filter(inscripcion=inscripcion, nombre__icontains="homologacion", saldo__gte=0).aggregate(total_saldo3=Sum('saldo'))['total_saldo3'] or 0  # Manejo de None
                saldo_inscripcion = total_saldo1 + total_saldo2 + total_saldo3
                correo = inscripcion.persona.emailinst
                id = str(inscripcion.idsalesforcei)
                id2 = str(inscripcion.persona.idsalesforce)
                totalmatricula = Rubro.objects.filter(inscripcion=inscripcion, nombre__icontains="matricula", saldo__gte=0).aggregate(totalmatricula=Sum('saldo'))['totalmatricula']
                totalarancel = Rubro.objects.filter(inscripcion=inscripcion, nombre__icontains="arancel", saldo__gte=0).aggregate(totalarancel=Sum('saldo'))['totalarancel']
                resultado = api_token_sf2.enviar_saldos(id, saldo_inscripcion, 0, 0)
                if not totalmatricula == None or not totalarancel == None:
                    resultado2 = api_token_sf2.enviar_saldo2(id, totalmatricula, totalarancel)
                if resultado:
                    print("Actualización completada con éxito.")
                    print(resultado)
                else:
                    raise Exception("Actualización fallida sin error específico.")
        except Exception as ex:
            print(f"Error al enviar saldos a Salesforce: {str(ex)}")
        self.nombre = null_to_text(self.nombre)
        self.motivopasivo = null_to_text(self.motivopasivo)
        self.motivoajuste = null_to_text(self.motivoajuste)
        self.observacion = null_to_text(self.observacion)
        super(Rubro, self).save(*args, **kwargs)


class RubroLiquidado(ModeloBase):
    rubro = models.ForeignKey(Rubro, verbose_name=u'Rubro', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha de aprobación')
    motivo = models.TextField(default='', verbose_name=u'Motivo')
    valor = models.FloatField(default=0, verbose_name=u'Valor liquidado')

    def __str__(self):
        return u'Rubro: %s %s' % (self.rubro.inscripcion, str(self.rubro.valor))

    class Meta:
        verbose_name_plural = u"Rubros liquidados"
        unique_together = ('rubro',)

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        self.valor = null_to_numeric(self.valor, 2)
        super(RubroLiquidado, self).save(*args, **kwargs)


class RubroOkBeca(ModeloBase):
    rubro = models.ForeignKey(Rubro, verbose_name=u'Rubro', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha de aprobación')
    valorbeca = models.FloatField(default=0, verbose_name=u'Valor')
    aplicado = models.BooleanField(default=False, verbose_name=u'Aplicado')
    porcientobeca = models.FloatField(default=0, verbose_name=u'Porcentaje')

    def __str__(self):
        return u'Rubro: %s %s' % (self.rubro.inscripcion, str(self.rubro.valor))

    class Meta:
        unique_together = ('rubro',)


class TipoEspecieValorada(ModeloBase):
    nombre = models.CharField(default='', max_length=50, verbose_name=u'Nombre')
    precio = models.FloatField(default=0, verbose_name=u'Precio')
    reporte = models.ForeignKey(Reporte, null=True, blank=True, verbose_name=u'Reporte', on_delete=models.CASCADE)
    destinatario = models.CharField(default='', max_length=100, blank=True, verbose_name=u'Destinatario')
    cargo = models.CharField(default='', max_length=100, blank=True, verbose_name=u'Cargo')
    iva = models.ForeignKey(IvaAplicado, verbose_name=u'IVA', on_delete=models.CASCADE)
    activa = models.BooleanField(default=True, verbose_name=u'Activa')

    def __str__(self):
        return u'%s - %s' % (self.nombre, str(self.precio))

    class Meta:
        ordering = ['nombre']
        verbose_name_plural = u"Tipos de especies valoradas"

    def total_generadas(self):
        return self.rubroespecievalorada_set.count()

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.destinatario = null_to_text(self.destinatario)
        self.cargo = null_to_text(self.cargo)
        super(TipoEspecieValorada, self).save(*args, **kwargs)


class HistoricoTipoEspecieValorada(ModeloBase):
    tipoespecievalorada = models.ForeignKey(TipoEspecieValorada, verbose_name=u'TipoEspecieValorada', on_delete=models.CASCADE)
    precio = models.FloatField(default=0, verbose_name=u'Precio')
    fecha = models.DateTimeField(verbose_name=u'Fecha de cambio')
    persona = models.ForeignKey(Persona, verbose_name=u'Persona', on_delete=models.CASCADE)


class RubroEspecieValorada(ModeloBase):
    rubro = models.ForeignKey(Rubro, verbose_name=u'Rubro', on_delete=models.CASCADE)
    tipoespecie = models.ForeignKey(TipoEspecieValorada, verbose_name=u'Tipo de especie', on_delete=models.CASCADE)
    serie = models.IntegerField(default=0, verbose_name=u'Serie')

    class Meta:
        verbose_name_plural = u"Rubros de especies valoradas"
        unique_together = ('rubro',)

    def __str__(self):
        return u'Rubro: %s %s' % (self.rubro.inscripcion, str(self.rubro.valor))

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Rubro.objects.filter(Q(rubroespecievalorada__serie__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.serie + ' - ' + str(self.id)

    def numero_serie(self):
        return str(self.rubro.fecha.year) + str(self.serie).zfill(4)


class RubroInscripcion(ModeloBase):
    rubro = models.ForeignKey(Rubro, on_delete=models.CASCADE)
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u'Inscripcion', on_delete=models.CASCADE)

    def __str__(self):
        return u'Rubro: %s %s' % (self.rubro.inscripcion, str(self.rubro.valor))

    class Meta:
        verbose_name_plural = u"Rubros de inscripciones"
        unique_together = ('rubro',)


class RubroAnticipado(ModeloBase):
    rubro = models.ForeignKey(Rubro, on_delete=models.CASCADE)
    motivo = models.TextField(default='', verbose_name=u'Motivo')

    class Meta:
        unique_together = ('rubro',)


class RubroCuota(ModeloBase):
    rubro = models.ForeignKey(Rubro, verbose_name=u'Rubro', on_delete=models.CASCADE)
    matricula = models.ForeignKey(Matricula, blank=True, null=True, verbose_name=u'Matricula', on_delete=models.CASCADE)
    cuota = models.IntegerField(default=1, verbose_name=u'Cuota')
    totalcuota = models.IntegerField(default=1, verbose_name=u'Cuota')

    def __str__(self):
        return u'Rubro: %s %s' % (self.rubro.inscripcion, str(self.rubro.valor))

    class Meta:
        verbose_name_plural = u"Rubros de cuotas"
        unique_together = ('rubro',)

    def nombre_corto(self):
        if self.matricula.becado:
            if self.matricula.nivel.nivelmalla:
                return self.matricula.nivel.nivelmalla.nombre + " - " + self.matricula.nivel.paralelo + " (BECA " + str(self.matricula.porcientobeca) + "%)"
            else:
                return " (BECA " + str(self.matricula.porcientobeca) + "%) - " + str(self.matricula.nivel.periodo.tipo) + " " + str(self.matricula.nivel.periodo.nombre)
        else:
            return self.matricula.nivel.periodo


class RubroOtroMatricula(ModeloBase):
    rubro = models.ForeignKey(Rubro, verbose_name=u'Rubro', on_delete=models.CASCADE)
    matricula = models.ForeignKey(Matricula, verbose_name=u'Matricula', on_delete=models.CASCADE)
    tipo = models.IntegerField(default=0, verbose_name=u'Tipo')
    descripcion = models.TextField(default='', verbose_name=u'Descripción')

    def __str__(self):
        return u'Rubro: %s %s' % (self.rubro.inscripcion, str(self.rubro.valor))

    class Meta:
        verbose_name_plural = u"Rubros de otros pagos de matriculas"
        unique_together = ('rubro',)

    def nombre_corto(self):
        return self.descripcion

    def save(self, *args, **kwargs):
        self.descripcion = null_to_text(self.descripcion)
        super(RubroOtroMatricula, self).save(*args, **kwargs)


class RubroAgregacion(ModeloBase):
    rubro = models.ForeignKey(Rubro, verbose_name=u'Rubro', on_delete=models.CASCADE)
    materiaasignada = models.ForeignKey(MateriaAsignada, verbose_name=u'Materia agregada', on_delete=models.CASCADE)
    adelanto = models.BooleanField(default=False, verbose_name=u'Adelanto')

    def __str__(self):
        return u'Rubro: %s %s' % (self.rubro.inscripcion, str(self.rubro.valor))

    class Meta:
        verbose_name_plural = u"Rubros de agregaciones"
        unique_together = ('rubro',)


class RubroMatricula(ModeloBase):
    rubro = models.ForeignKey(Rubro, verbose_name=u'Rubro', on_delete=models.CASCADE)
    matricula = models.ForeignKey(Matricula, blank=True, null=True, verbose_name=u'Matricula', on_delete=models.CASCADE)
    cuota = models.IntegerField(default=1, verbose_name=u'Cuota')

    def __str__(self):
        return u'Rubro: %s %s' % (self.rubro.inscripcion, str(self.rubro.valor))

    class Meta:
        verbose_name_plural = u"Rubros de matriculas"
        unique_together = ('rubro',)

    def nombre_corto(self):
        if self.matricula.becado:
            if self.matricula.nivel.nivelmalla:
                return self.matricula.nivel.nivelmalla.nombre + " - " + self.matricula.nivel.paralelo + " (BECA " + str(self.matricula.porcientobeca) + "%)"
            else:
                return "(BECA " + str(self.matricula.porcientobeca) + "%) - " + str(self.matricula.nivel.periodo.tipo) + " " + str(self.matricula.nivel.periodo.nombre)
        else:
            if self.matricula.nivel.nivelmalla and self.matricula.nivel.paralelo:
                return self.matricula.nivel.nivelmalla.nombre + " - " + self.matricula.nivel.paralelo
            else:
                return self.matricula.nivel.paralelo


class RubroDerecho(ModeloBase):
    rubro = models.ForeignKey(Rubro, verbose_name=u'Rubro', on_delete=models.CASCADE)
    materiaasignada = models.ForeignKey(MateriaAsignada, verbose_name=u'Materia asignada', on_delete=models.CASCADE)

    def __str__(self):
        return u'Rubro: %s %s' % (self.rubro.inscripcion, str(self.rubro.valor))

    class Meta:
        verbose_name_plural = u"Rubros de derecho examenes"
        unique_together = ('rubro', 'materiaasignada',)


class RubroMateria(ModeloBase):
    rubro = models.ForeignKey(Rubro, verbose_name=u'Rubro', on_delete=models.CASCADE)
    materiaasignada = models.ForeignKey(MateriaAsignada, verbose_name=u'Materia asignada', on_delete=models.CASCADE)

    def __str__(self):
        return u'Rubro: %s %s' % (self.rubro.inscripcion, str(self.rubro.valor))

    class Meta:
        verbose_name_plural = u"Rubros de materias"
        unique_together = ('rubro',)



class TipoOtroRubro(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    preciolibre = models.BooleanField(default=True, verbose_name=u'Precio libre')
    precio = models.FloatField(default=0, verbose_name=u'Precio')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos otros rubros"
        ordering = ['nombre']
        unique_together = ('nombre',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("TipoOtroRubro.objects.filter(Q(nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.nombre + ' - ' + str(self.id)

    def precio_sugerido(self):
        if PrecioTipoOtroRubro.objects.filter(tipo=self).exists():
            return PrecioTipoOtroRubro.objects.filter(tipo=self).order_by('fecha')[0].precio
        return 0

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoOtroRubro, self).save(*args, **kwargs)


class PrecioTipoOtroRubro(ModeloBase):
    tipo = models.ForeignKey(TipoOtroRubro, verbose_name=u'Tipo', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha')
    precio = models.FloatField(default=0, verbose_name=u'Precio')

    def __str__(self):
        return u'Precio Tipo de Otro Rubro %s' % self.tipo

    class Meta:
        verbose_name_plural = u"Precios tipos de otros rubros"
        unique_together = ('tipo', 'fecha',)


class SolicitudSecretariaDocente(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion, blank=True, null=True, verbose_name=u'Solicitante', on_delete=models.CASCADE)
    tipo = models.ForeignKey(TipoSolicitudSecretariaDocente, verbose_name=u'Tipo de solicitud', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha de solictud')
    hora = models.TimeField(verbose_name=u'Hora')
    descripcion = models.TextField(default='', verbose_name=u'Descripción')
    respuesta = models.TextField(default='', blank=True, null=True, verbose_name=u'Respuesta')
    cerrada = models.BooleanField(default=False, verbose_name=u'Cerrada')
    siendoatendida = models.BooleanField(default=False, verbose_name=u'Siendo Atendida')
    fechacierre = models.DateField(null=True, blank=True, verbose_name=u'Fecha de entrega')
    numero_tramite = models.IntegerField(default=0, verbose_name=u'Numero de Trámite')
    matricula = models.ForeignKey(Matricula, blank=True, null=True, verbose_name=u'Matrícula', on_delete=models.CASCADE)
    materiaasignada = models.ForeignKey(MateriaAsignada, blank=True, null=True, verbose_name=u'Materia Asignada', on_delete=models.CASCADE)
    responsable = models.ForeignKey(Persona, related_name='responsable', blank=True, null=True, verbose_name=u'Responsable', on_delete=models.CASCADE)
    archivado = models.CharField(default='', max_length=100, verbose_name=u'Archivado en')
    archivo = models.FileField(upload_to='archivo/%Y/%m/%d', blank=True, null=True, verbose_name=u'Solicitudes')
    valorprorroga = models.FloatField(default=0, blank=True, null=True, verbose_name=u'Valor prorroga')

    def __str__(self):
        return u'%s %s %s' % (self.inscripcion.persona, self.tipo, self.fecha.strftime("%d-%m-%Y"))

    class Meta:
        verbose_name_plural = u"Solicitudes"
        ordering = ['cerrada', '-numero_tramite', '-fecha', '-hora']
        unique_together = ('inscripcion', 'tipo', 'fecha', 'hora',)

    def rubrootro(self):
        if self.rubrootro_set.exists():
            return self.rubrootro_set.all()[0]
        return None

    def verificar_gratuidad(self):
        if SOLICITUD_SECRETARIA_MATRICULA_GRATUITAS:
            if self.rubrootro_set.exists() and self.matricula:
                if self.matricula.solicitudsecretariadocente_set.filter(tipo=self.tipo).count() <= self.tipo.gratismatricula:
                    rubro = self.rubro()
                    rubro.liquidar('SOLICITUD GRATUITA')

    def rubro(self):
        rubrootro = self.rubrootro()
        return rubrootro.rubro if rubrootro else None

    def especie(self):
        if RubroEspecieValorada.objects.filter(solicitud=self).exists():
            return RubroEspecieValorada.objects.filter(solicitud=self)[0]
        return None

    def especiepagada(self):
        rubro = self.especie().rubro
        return rubro.cancelado if rubro else True

    def valor(self):
        rubro = self.rubro()
        return rubro.valor if rubro else 0

    def pagada(self):
        rubro = self.rubro()
        return rubro.cancelado if rubro else True

    def vencida(self):
        if DIAS_VENCIMIENTO_SOLICITUD:
            return not self.siendoatendida and datetime.now().date() > (datetime(self.fecha.year, self.fecha.month, self.fecha.day, 0, 0, 0) + timedelta(days=DIAS_VENCIMIENTO_SOLICITUD)).date()
        return False

    def mail_subject_nuevo(self):
        send_mail(subject='Nueva solicitud a registrada.',
                  html_template='emails/nuevasolicitud.html',
                  data={'d': self},
                  recipient_list=[self.inscripcion.persona])

    def mail_subject_cierre(self):
        send_mail(subject='Su solicitud ya fue atendida y cerrada.',
                  html_template='emails/respuestasolicitud.html',
                  data={'d': self},
                  recipient_list=[self.inscripcion.persona])

    def mail_asignacion(self):
        send_mail(subject='Solicitud asiganda.',
                  html_template='emails/asignarsolicitud.html',
                  data={'d': self},
                  recipient_list=[self.inscripcion.persona])

    def mail_reenvio(self):
        send_mail(subject='Solicitud asiganda.',
                  html_template='emails/reasignarsolicitud.html',
                  data={'d': self},
                  recipient_list=[self.inscripcion.persona])

    def mail_subject_comentar(self):
        send_mail(subject='La solicitud recibida ha sido atendida.',
                  html_template='emails/comentarsolicitud.html',
                  data={'d': self},
                  recipient_list=[self.inscripcion.persona])

    def ultima_respuesta(self):
        if self.historialsolicitud_set.exists():
            return self.historialsolicitud_set.all().order_by('-fecha')[0]
        else:
            historial = HistorialSolicitud(solicitud=self,
                                           fecha=self.fecha,
                                           )
            historial.save()
            return historial
        return None

    def asignaciones(self):
        return self.historialsolicitud_set.all()

    def tiene_costo(self):
        rubro = self.rubro()
        if rubro:
            return rubro.valor > 0
        return False

    def tiene_rubros_pagados(self):
        return Pago.objects.filter(rubro__rubrootro__solicitud=self).exists()

    def eliminar_rubros(self):
        for rubro in RubroOtro.objects.filter(solicitud=self):
            r = rubro.rubro
            rubro.delete()
            r.verifica_rubro_otro(RUBRO_OTRO_SOLICITUD_ID)

    def valorprorrogar(self, periodo):
        rm = null_to_decimal(self.inscripcion.rubro_set.filter(rubromatricula__isnull=False, cancelado=False, periodo=periodo).aggregate(valor=Sum('saldo'))['valor'], 2)
        rc = null_to_decimal(self.inscripcion.rubro_set.filter(rubrocuota__isnull=False, cancelado=False, periodo=periodo).aggregate(valor=Sum('saldo'))['valor'], 2)
        rg = null_to_decimal(self.inscripcion.rubro_set.filter(rubroagregacion__isnull=False, cancelado=False, periodo=periodo).aggregate(valor=Sum('saldo'))['valor'], 2)
        rom = null_to_decimal(self.inscripcion.rubro_set.filter(rubrootromatricula__isnull=False, cancelado=False, periodo=periodo).aggregate(valor=Sum('saldo'))['valor'], 2)
        roa = null_to_decimal(self.inscripcion.rubro_set.filter(rubrootro__isnull=False, rubrootro__tipo__id__in=(10, 11, 12, 13, 14, 18), cancelado=False, periodo=periodo).aggregate(valor=Sum('saldo'))['valor'], 2)
        rnd = null_to_decimal(self.inscripcion.rubro_set.filter(rubronotadebito__isnull=False, cancelado=False, periodo=periodo).aggregate(valor=Sum('saldo'))['valor'], 2)
        return null_to_decimal(rm+rc+rg+rom+roa+rnd, 2)

    def total_cuotas(self):
        return null_to_decimal(self.diferimientosolicitudprorrogasecretaria_set.aggregate(valor=Sum('valor'))['valor'], 2)

    def tiene_requisitos(self):
        return self.requisitossolicitudsecretariadocente_set.exists()

    def es_medica(self):
        return self.solicitudsecretariafaltas_set.filter(medica=True).exists()

    def responsablen(self):
        return PersonalSolicitudProrroga.objects.filter(carrera=self.inscripcion.carrera,modalidad=self.inscripcion.modalidad,sede=self.inscripcion.sede,nivel=self.matricula.nivelmalla).last()


    def save(self, *args, **kwargs):
        self.descripcion = null_to_text(self.descripcion)
        self.respuesta = null_to_text(self.respuesta)
        self.archivado = null_to_text(self.archivado)
        super(SolicitudSecretariaDocente, self).save(*args, **kwargs)



class HistorialSolicitud(ModeloBase):
    solicitud = models.ForeignKey(SolicitudSecretariaDocente, verbose_name=u'Solicitud', on_delete=models.CASCADE)
    fecha = models.DateTimeField(verbose_name=u'Fecha de solictud')
    persona = models.ForeignKey(Persona, verbose_name=u'Persona', on_delete=models.CASCADE,blank=True,null=True)
    respuesta = models.TextField(default='', blank=True, null=True, verbose_name=u'Respuesta')

    class Meta:
        ordering = ['fecha']
        unique_together = ('solicitud', 'fecha', 'persona',)

    def save(self, *args, **kwargs):
        self.respuesta = null_to_text(self.respuesta)
        super(HistorialSolicitud, self).save(*args, **kwargs)


class RubroOtro(ModeloBase):
    rubro = models.ForeignKey(Rubro, verbose_name=u'Rubro', on_delete=models.CASCADE)
    tipo = models.ForeignKey(TipoOtroRubro, verbose_name=u'Tipo', on_delete=models.CASCADE)
    solicitud = models.ForeignKey(SolicitudSecretariaDocente, blank=True, null=True, verbose_name=u'Solicitud', on_delete=models.CASCADE)


    def __str__(self):
        return u'Rubro: %s %s' % (self.rubro.inscripcion, str(self.rubro.valor))

    class Meta:
        verbose_name_plural = u"Otros rubros"
        unique_together = ('rubro',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("RubroOtro.objects.filter(Q(rubro__inscripcion__contains='%s') | Q(rubro__tipo__nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return str(self.rubro.valor) + ' - ' + str(self.id)

    def save(self, *args, **kwargs):
        super(RubroOtro, self).save(*args, **kwargs)


class SesionCaja(ModeloBase):
    caja = models.ForeignKey(LugarRecaudacion, verbose_name=u'Caja', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha')
    hora = models.TimeField(verbose_name=u'Hora')
    fondo = models.FloatField(default=0, verbose_name=u'Fondo inicial')
    facturaempieza = models.IntegerField(default=0, verbose_name=u'Factura inicial')
    facturatermina = models.IntegerField(blank=True, null=True, verbose_name=u'Factura final')
    reciboempieza = models.IntegerField(default=0, verbose_name=u'Recibo inicial')
    recibotermina = models.IntegerField(blank=True, null=True, verbose_name=u'Recibo final')
    abierta = models.BooleanField(default=True, verbose_name=u'Abierta')
    autorizacion = models.CharField(default='', max_length=20, verbose_name=u'Autorización SRI')

    def __str__(self):
        return u'%s - %s' % (self.fecha.strftime("%d-%m-%Y"), self.caja)

    class Meta:
        verbose_name_plural = u"Sesiones de recaudación de caja"
        ordering = ['-fecha', '-hora']
        unique_together = ('caja', 'fecha', 'hora',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        if len(q) == 10 and q[2] in ['-', ':', '/'] and q[2] in ['-', ':', '/']:
            try:
                return eval(("SesionCaja.objects.filter(fecha=datetime(int(q[6:10]), int(q[3:5]), int(q[0:2])).date())") + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))
            except:
                pass
        return eval(("SesionCaja.objects.filter(Q(caja__nombre__contains='%s') | Q(caja__persona__apellido1__contains='%s') | Q(caja__persona__apellido2__contains='%s') | Q(caja__persona__nombre1__contains='%s') | Q(caja__persona__nombre2__contains='%s') | Q(caja__persona__cedula__contains='%s') | Q(id=id_search('%s')))" % (q, q, q, q, q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.caja.nombre + " - " + self.fecha.strftime("%d-%m-%Y") + " - " + str(self.id)

    def puede_cerar_automatico(self):
        return datetime.now().date() > self.fecha

    def total_efectivo_sesion(self):
        return null_to_numeric(Pago.objects.filter(sesion=self, efectivo=True, valido=True, anticipado=False).aggregate(valor=Sum('valor'))['valor'], 2)

    def cantidad_facturas_sesion(self):
        return Factura.objects.filter(pagos__sesion=self, valida=True).distinct().count()

    def cantidad_recibopago_sesion(self):
        return ReciboPago.objects.filter(pagos__sesion=self, valido=True).distinct().count()

    def cantidad_cheques_sesion(self):
        return DatoCheque.objects.filter(pagocheque__pagos__sesion=self, pagocheque__pagos__valido=True).distinct().count()

    def total_cheque_sesion(self):
        return null_to_numeric(Pago.objects.filter(pagocheque__isnull=False, sesion=self, valido=True).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def cantidad_tarjetas_sesion(self):
        return DatoTarjeta.objects.filter(pagotarjeta__pagos__sesion=self, pagotarjeta__pagos__valido=True).distinct().count()

    def total_tarjeta_sesion(self):
        return null_to_numeric(Pago.objects.filter(pagotarjeta__isnull=False, sesion=self, valido=True).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def cantidad_depositos_sesion(self):
        return DatoTransferenciaDeposito.objects.filter(pagotransferenciadeposito__pagos__sesion=self, deposito=True, pagotransferenciadeposito__pagos__valido=True).distinct().count()

    def total_deposito_sesion(self):
        return null_to_numeric(Pago.objects.filter(pagotransferenciadeposito__datotransferenciadeposito__deposito=True, sesion=self, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def cantidad_transferencias_sesion(self):
        return DatoTransferenciaDeposito.objects.filter(pagotransferenciadeposito__pagos__sesion=self, deposito=False, pagotransferenciadeposito__pagos__valido=True).distinct().count()

    def total_transferencia_sesion(self):
        return null_to_numeric(Pago.objects.filter(pagotransferenciadeposito__datotransferenciadeposito__deposito=False, sesion=self, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def cantidad_notasdecredito_sesion(self):
        return PagoNotaCredito.objects.filter(pagos__sesion=self, pagos__valido=True).distinct().count()

    def total_notadecredito_sesion(self):
        return null_to_numeric(Pago.objects.filter(sesion=self, pagonotacredito__isnull=False, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def total_vales_ingresos(self):
        return null_to_numeric(ValeCaja.objects.filter(sesion=self, tipooperacion=2).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def total_vales_egresos(self):
        return null_to_numeric(ValeCaja.objects.filter(sesion=self, tipooperacion=1).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def cantidad_recibocaja_sesion(self):
        return ReciboCajaInstitucion.objects.filter(pagorecibocajainstitucion__pagos__sesion=self, pagorecibocajainstitucion__pagos__valido=True).distinct().count()

    def total_recibocaja_sesion(self):
        return null_to_numeric(Pago.objects.filter(sesion=self, pagorecibocajainstitucion__isnull=False, valido=True).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def total_pre_facturas(self):
        return null_to_numeric(Pago.objects.filter(sesion=self, anticipado=True, valido=True).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def total_sesion(self):
        return null_to_numeric(self.fondo + self.total_vales_ingresos() - self.total_vales_egresos() + self.total_efectivo_sesion() + self.total_cheque_sesion() + self.total_deposito_sesion() + self.total_transferencia_sesion() + self.total_tarjeta_sesion() + self.total_notadecredito_sesion(), 2)

    def cierre_sesion(self):
        if self.cierresesioncaja_set.exists():
            return self.cierresesioncaja_set.all()[0]
        return None

    def hora_cierre(self):
        if self.cierresesioncaja_set.exists():
            return self.cierresesioncaja_set.all()[0].hora
        return None

    def factura_minima(self):
        return null_to_numeric(Factura.objects.filter(sesion=self).aggregate(minimo=Min('numeroreal'))['minimo'], 0)

    def factura_maxima(self):
        return null_to_numeric(Factura.objects.filter(sesion=self).aggregate(maximo=Max('numeroreal'))['maximo'], 0)

    def recibo_minima(self):
        return null_to_numeric(ReciboPago.objects.filter(sesion=self).aggregate(minimo=Min('numeroreal'))['minimo'], 0)

    def recibo_maxima(self):
        return null_to_numeric(ReciboPago.objects.filter(sesion=self).aggregate(maximo=Max('numeroreal'))['maximo'], 0)

    def puede_pagar(self):
        return self.fecha == datetime.now().date()

    def facturar_rubros_datafast(self, autorizacion):
        pass

    def save(self, *args, **kwargs):
        self.facturaempieza = self.factura_minima()
        self.facturatermina = self.factura_maxima()
        self.reciboempieza = self.recibo_minima()
        self.recibotermina = self.recibo_maxima()
        self.autorizacion = null_to_text(self.autorizacion)
        super(SesionCaja, self).save(*args, **kwargs)


class CierreSesionCaja(ModeloBase):
    sesion = models.ForeignKey(SesionCaja, verbose_name=u'Sesion de caja', on_delete=models.CASCADE)
    total = models.FloatField(default=0, verbose_name=u'Total')
    bill100 = models.IntegerField(default=0, verbose_name=u'Billetes de 100')
    bill50 = models.IntegerField(default=0, verbose_name=u'Billetes de 50')
    bill20 = models.IntegerField(default=0, verbose_name=u'Billetes de 20')
    bill10 = models.IntegerField(default=0, verbose_name=u'Billetes de 10')
    bill5 = models.IntegerField(default=0, verbose_name=u'Billetes de 5')
    bill2 = models.IntegerField(default=0, verbose_name=u'Billetes de 2')
    bill1 = models.IntegerField(default=0, verbose_name=u'Billetes de 1')
    enmonedas = models.FloatField(default=0, verbose_name=u'Total en momedas')
    efectivo = models.FloatField(default=0, verbose_name=u'Total en momedas')
    deposito = models.FloatField(default=0, verbose_name=u'Total en depositos')
    cheque = models.FloatField(default=0, verbose_name=u'Total en cheque')
    transferencia = models.FloatField(default=0, verbose_name=u'Total en transferencia')
    tarjeta = models.FloatField(default=0, verbose_name=u'Total en tarjeta')
    recibocaja = models.FloatField(default=0, verbose_name=u'Total en recibo caja')
    recibocajainstitucion = models.FloatField(default=0, verbose_name=u'Total en recibo caja')
    notacreditointerna = models.FloatField(default=0, verbose_name=u'Total en nota credito')
    valecajaingreso = models.FloatField(default=0, verbose_name=u'Total en valecaja')
    valecajaegreso = models.FloatField(default=0, verbose_name=u'Total en valecaja')
    fecha = models.DateField(blank=True, null=True, verbose_name=u'Fecha')
    hora = models.TimeField(blank=True, null=True, verbose_name=u'Hora')

    def __str__(self):
        return u'Billetes cierre sesion: %s' % self.sesion

    class Meta:
        verbose_name_plural = u"Resumenes cierre de sesion de caja"
        unique_together = ('sesion',)

    def papeletas(self):
        return self.papeletadeposito_set.all()

    def en_fecha(self):
        if self.sesion.fecha == datetime.now().date():
            return True
        return False

    def en_fecha_papeleta(self):
        limite = self.fecha + timedelta(days=4)
        return datetime.now().date() <= limite

    def total_papeletas(self):
        return self.papeletadeposito_set.count()

    def total_dinero_papeletas(self):
        return null_to_numeric(self.papeletadeposito_set.aggregate(valor=Sum('valor'))['valor'], 2)

    def diferencia_papeletas(self):
        if self.papeletadeposito_set.exists():
            return null_to_numeric(self.total - self.total_dinero_papeletas(), 2)
        return 0

    def actualiza_valores(self):
        self.deposito = null_to_numeric(Pago.objects.filter(pagotransferenciadeposito__datotransferenciadeposito__deposito=True, sesion=self.sesion, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
        self.transferencia = null_to_numeric(Pago.objects.filter(pagotransferenciadeposito__datotransferenciadeposito__deposito=False, sesion=self.sesion, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
        self.cheques = null_to_numeric(Pago.objects.filter(pagocheque__isnull=False, sesion=self.sesion, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
        self.tarjetas = null_to_numeric(Pago.objects.filter(pagotarjeta__isnull=False, sesion=self.sesion, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
        self.valorcajaentregado = null_to_numeric(ValeCaja.objects.filter(sesion=self.sesion, tipooperacion=1).distinct().aggregate(valor=Sum('valor'))['valor'], 2)
        self.valorcajadevuelto = null_to_numeric(ValeCaja.objects.filter(sesion=self.sesion, tipooperacion=2).distinct().aggregate(valor=Sum('valor'))['valor'], 2)
        self.recibocaja = null_to_numeric(Pago.objects.filter(pagorecibocajainstitucion__isnull=False, sesion=self.sesion, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
        self.recibocajainstitucion = null_to_numeric(ReciboCajaInstitucion.objects.filter(sesioncaja=self.sesion).aggregate(valor=Sum('valorinicial'))['valor'], 2)
        self.notacreditointerna = null_to_numeric(Pago.objects.filter(pagonotacredito__isnull=False, sesion=self.sesion, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
        self.save()

    def save(self, *args, **kwargs):
        self.efectivo = null_to_numeric(self.bill100 * 100 + self.bill50 * 50 + self.bill20 * 20 + self.bill10 * 10 + self.bill5 * 5 + self.bill2 * 2 + self.bill1 * 1 + self.enmonedas, 2)
        self.total = self.deposito + self.transferencia + self.cheque + self.tarjeta + self.efectivo + self.valecajaingreso - self.valecajaegreso
        super(CierreSesionCaja, self).save(*args, **kwargs)


class Banco(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    tasaprotesto = models.FloatField(default=0, verbose_name=u'Tasa de protesto')
    tieneplantilla = models.BooleanField(default=True, verbose_name=u'Plantilla')
    idbancocontable = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'id Banco')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Bancos"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def en_uso(self):
        if self.cuentabanco_set.exists():
            return True
        if self.informacionbancariapersona_set.exists():
            return True
        return False

    def bancos_internacionles(self):
        return self.id == OTROS_BANCOS_EXTERNOS_ID

    def mi_diferido(self, tipoemisortarjeta, tipotarjetabanco):
        if not self.diferidotarjeta_set.filter(tipoemisortarjeta=tipoemisortarjeta, tipotarjetabanco=tipotarjetabanco).exists():
            diferido = DiferidoTarjeta(banco=self,
                                       tipoemisortarjeta=tipoemisortarjeta,
                                       tipotarjetabanco=tipotarjetabanco,
                                       nombre='CORRIENTE',
                                       valordatafast=0,
                                       difiere=False,
                                       intereses=False)
            diferido.save()
        return self.diferidotarjeta_set.filter(tipoemisortarjeta=tipoemisortarjeta, tipotarjetabanco=tipotarjetabanco, activo=True)

    def codigo_banco(self):
        if self.idbancocontable != 0:
            return self.idbancocontable
        return 0

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(Banco, self).save(*args, **kwargs)


class TipoCuentaBanco(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos Cuentas Bancarias"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoCuentaBanco, self).save(*args, **kwargs)


class CuentaBanco(ModeloBase):
    banco = models.ForeignKey(Banco, verbose_name=u'Banco', on_delete=models.CASCADE)
    tipocuenta = models.ForeignKey(TipoCuentaBanco, verbose_name=u'Tipo de cuenta', on_delete=models.CASCADE)
    numero = models.CharField(default='', max_length=50, verbose_name='Numero')
    representante = models.CharField(default='', max_length=100, verbose_name=u'Representante')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')
    observacion = models.CharField(default='', max_length=100, verbose_name=u'Observación')

    def __str__(self):
        cuenta = self.numero
        ncuenta = cuenta[-3:]
        return u'%s %s %s' % (self.banco, ncuenta, self.observacion)

    class Meta:
        verbose_name_plural = u"Cuentas bancarias"
        ordering = ['numero']
        unique_together = ('banco', 'tipocuenta', 'numero')

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("CuentaBanco.objects.filter(Q(banco__nombre__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.banco.nombre + " - " + self.tipocuenta.nombre + " - " + self.numero

    def save(self, *args, **kwargs):
        self.numero = null_to_text(self.numero)
        self.representante = null_to_text(self.representante)
        super(CuentaBanco, self).save(*args, **kwargs)


class PapeletaDeposito(ModeloBase):
    cierresesioncaja = models.ForeignKey(CierreSesionCaja, verbose_name=u'Cierre Sesion de caja', on_delete=models.CASCADE)
    referencia = models.CharField(default='', max_length=50, verbose_name=u'Referencia')
    cuentabanco = models.ForeignKey(CuentaBanco, verbose_name=u'Cuenta', on_delete=models.CASCADE)
    valor = models.FloatField(default=0, verbose_name=u'Valor')

    def __str__(self):
        return u'%s' % self.referencia

    def save(self, *args, **kwargs):
        self.referencia = null_to_text(self.referencia)
        super(PapeletaDeposito, self).save(*args, **kwargs)


class FormaDePago(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Formas de pago"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def es_tarjeta(self):
        return self.id == FORMA_PAGO_TARJETA

    def es_efectivo(self):
        return self.id == FORMA_PAGO_EFECTIVO

    def es_cheque(self):
        return self.id == FORMA_PAGO_CHEQUE

    def es_deposito(self):
        return self.id == FORMA_PAGO_DEPOSITO

    def es_transferencia(self):
        return self.id == FORMA_PAGO_TRANSFERENCIA

    def es_notacredito(self):
        return self.id == FORMA_PAGO_NOTA_CREDITO

    def es_recibocaja(self):
        return self.id == FORMA_PAGO_RECIBOCAJAINSTITUCION

    def es_retencion(self):
        return self.id == FORMA_PAGO_RETENCION

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(FormaDePago, self).save(*args, **kwargs)


TIPO_DEPOSITO = (
    (1, u'Ventanilla en Banco'),
    (2, u'Mi Vecino - Banco del barrio'),
    (3, u'Banca Móvil (Celular)'),
    (4, u'Banca Web (Computador)')
)
ESTADOS_DEPOSITO_INSCRIPCION = (
    (1, u'SI'),
    (2, u'REVISAR'),
    (3, u'NO'),
)

class DepositoInscripcion(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    cuentabanco = models.ForeignKey(CuentaBanco, verbose_name=u'Cuenta banco', on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, blank=True, null=True, verbose_name=u'Periodo al que pertenece el pago', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha deposito')
    fechaaprobacion = models.DateField(verbose_name=u'Fecha deposito', blank=True, null=True)
    motivo = models.CharField(default='', max_length=200, verbose_name=u'Motivo')
    archivo = models.FileField(upload_to='documentos/%Y/%m/%d', verbose_name=u'Archivo')
    procesado = models.BooleanField(default=False, verbose_name=u'Procesado')
    estadoprocesado = models.IntegerField(choices=ESTADOS_DEPOSITO_INSCRIPCION, default=1)
    autorizado = models.BooleanField(default=False, verbose_name=u'Autorizado')
    valido = models.BooleanField(default=True, verbose_name=u'Valido')
    referencia = models.CharField(default='', max_length=50, verbose_name=u'Referencia')
    deposito = models.BooleanField(default=True, verbose_name=u"Deposito")
    ventanilla = models.BooleanField(default=True, verbose_name=u"Pago en ventanilla/Depósito")
    movilweb = models.BooleanField(default=False, verbose_name=u"Pago con aplicación movil-web/Transf.")
    responsable = models.ForeignKey(Persona, related_name='responsabledeposito', blank=True, null=True, verbose_name=u'Responsable', on_delete=models.CASCADE)
    valor = models.FloatField(default=0, verbose_name=u"Valor")
    saldo = models.FloatField(default=0, verbose_name=u"Valor")
    observacion = models.BooleanField(default=False, verbose_name=u'Observacion')
    observaciones = models.TextField(default='', blank=True, null=True, verbose_name=u'Observaciones')

    mimetype = models.CharField(max_length=100, null=True, blank=True, verbose_name='MIME real')
    hash_archivo = models.CharField(max_length=64, null=True, blank=True, db_index=True, verbose_name='SHA-256')
    firma_logica = models.CharField(max_length=128, null=True, blank=True, db_index=True, verbose_name='Firma lógica')

    autenticidad_score = models.IntegerField(default=0, verbose_name='Score autenticidad')
    motivo_no_aut = models.CharField(max_length=255, null=True, blank=True, verbose_name='Motivo no auto-aut')

    ocr_texto = models.TextField(null=True, blank=True)
    ocr_banco = models.CharField(max_length=64, null=True, blank=True)
    ocr_empresa = models.CharField(max_length=128, null=True, blank=True)
    ocr_referencia = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    ocr_documento = models.CharField(max_length=64, null=True, blank=True)  # alias de ref si viene como "Documento" o comprobante pud ser
    ocr_monto = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ocr_fecha_pago = models.DateField(null=True, blank=True)
    comparado_ok = models.BooleanField(default=False, verbose_name='Comparación OCR OK')


    def __str__(self):
        return u'%s %s %s' % (self.referencia, self.cuentabanco, str(self.valor))

    class Meta:
        verbose_name_plural = u"Depositos de inscripciones"
        unique_together = ('inscripcion', 'cuentabanco', 'fecha', 'referencia', 'deposito',)

    def liquidar(self):
        liquidado = DepositoInscripcionLiquidado(depositoinscripcion=self,
                                                 fecha=datetime.now().date(),
                                                 valor=self.saldo)
        liquidado.save()
        self.save()

    def esta_liquidado(self):
        return self.depositoinscripcionliquidado_set.exists()

    def esta_registrado(self):
        return DatoTransferenciaDeposito.objects.filter(deposito=self.deposito, cuentabanco=self.cuentabanco, fechabanco=self.fecha, referencia=self.referencia).exists()

    def saldo_actual(self):
        if not self.esta_liquidado():
            return null_to_numeric(self.valor - null_to_numeric(DatoTransferenciaDeposito.objects.filter(deposito=self.deposito, cuentabanco=self.cuentabanco, fechabanco=self.fecha, referencia=self.referencia).aggregate(valor=Sum('valor'))['valor'], 2), 2)
        return 0

    def save(self, *args, **kwargs):
        super(DepositoInscripcion, self).save(*args, **kwargs)
        self.motivo = null_to_text(self.motivo)
        self.saldo = self.saldo_actual()
        if self.saldo <= 0:
            self.estadoprocesado = 1
        else:
            if self.estadoprocesado == 2:
                self.estadoprocesado = 2
            else:
                self.estadoprocesado = 3
        self.referencia = null_to_text(self.referencia)
        super(DepositoInscripcion, self).save(*args, **kwargs)


class DepositoInscripcionLiquidado(ModeloBase):
    depositoinscripcion = models.ForeignKey(DepositoInscripcion, verbose_name=u'Deposito Inscripcion', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha de aprobación')
    valor = models.FloatField(default=0, verbose_name=u'Valor liquidado')

    class Meta:
        verbose_name_plural = u"Deposito Inscripcion liquidados"
        unique_together = ('depositoinscripcion',)


class Pago(ModeloBase):
    sesion = models.ForeignKey(SesionCaja, null=True, blank=True, verbose_name=u'Sesion de caja', on_delete=models.CASCADE)
    rubro = models.ForeignKey(Rubro, null=True, blank=True, verbose_name=u'Rubros', on_delete=PROTECT)
    fecha = models.DateField(verbose_name=u'Fecha')
    iva = models.FloatField(default=0, verbose_name=u'IVA')
    valor = models.FloatField(default=0, verbose_name=u'Valor')
    efectivo = models.BooleanField(default=True, verbose_name=u'Pago en efectivo')
    anticipado = models.BooleanField(default=False, verbose_name=u'Pago de Factura anticipada')
    descuento = models.FloatField(default=0, verbose_name=u'Descuento')
    valido = models.BooleanField(default=True, verbose_name=u"Valido")
    depositoinscripcion = models.ForeignKey(DepositoInscripcion, null=True, blank=True, verbose_name=u'Deposito Inscripcion', on_delete=models.CASCADE)
    codigocontable = models.IntegerField(default=0, verbose_name=u'Codigo contable')
    codigocontablenumero = models.IntegerField(default=0, verbose_name=u'Codigo contable numero')
    registrocontable = models.BooleanField(default=False, verbose_name=u'Registro en contable')
    notacredito = models.BooleanField(default=False, verbose_name=u'Tiene nota de credito')
    formadepago = models.ForeignKey(FormaDePago, blank=True, null=True, verbose_name=u'Sesion de caja', on_delete=models.CASCADE)

    def __str__(self):
        return u'Pago $%s %s' % (str(self.valor), self.rubro)

    class Meta:
        verbose_name_plural = u"Pagos"
        ordering = ['fecha']

    def subtotal(self):
        return self.valor + self.descuento

    def totaldescuento(self):
        return self.descuento

    def tipo(self):
        if self.pagotarjeta_set.exists():
            return "TARJETA"
        elif self.pagocheque_set.exists():
            return "CHEQUE"
        elif self.pagotransferenciadeposito_set.exists():
            if self.es_deposito():
                return "DEPOSITO"
            return "TRANSFERENCIA"
        elif self.pagonotacredito_set.exists():
            return "NOTA DE CREDITO"
        elif self.pagorecibocajainstitucion_set.exists():
            return "RECIBO CAJA INSTITUCION"
        return "EFECTIVO"

    def tipo_exp(self):
        if self.pagotarjeta_set.exists():
            return "TAR"
        elif self.pagocheque_set.exists():
            return "CHE"
        elif self.pagotransferenciadeposito_set.exists():
            if self.es_deposito():
                return "DEP"
            return "TRA"
        elif self.pagonotacredito_set.exists():
            return "NOT"
        elif self.pagorecibocajainstitucion_set.exists():
            return "REC"
        return "EFE"

    def nombre(self):
        return self.tipo() + " $" + str(self.relacionado().valor)

    def relacionado(self):
        if self.pagotarjeta_set.exists():
            return self.pagotarjeta_set.all()[0]
        elif self.pagocheque_set.exists():
            return self.pagocheque_set.all()[0]
        elif self.pagotransferenciadeposito_set.exists():
            return self.pagotransferenciadeposito_set.all()[0]
        elif self.pagonotacredito_set.exists():
            return self.pagonotacredito_set.all()[0]
        elif self.pagorecibocajainstitucion_set.exists():
            return self.pagorecibocajainstitucion_set.all()[0]
        return None

    def es_notadecredito(self):
        if self.pagonotacredito_set.exists():
            return self.pagonotacredito_set.all()[0]

    def es_chequevista(self):
        if self.pagocheque_set.exists():
            cheque = self.pagocheque_set.all()[0]
            return cheque.datocheque.a_vista()
        return False

    def es_tarjeta(self):
        return self.pagotarjeta_set.exists()

    def dato_tarjeta(self):
        if self.es_tarjeta():
            return DatoTarjeta.objects.filter(pagotarjeta__pagos=self)[0]
        return None

    def es_notacredito(self):
        return self.pagonotacredito_set.exists()

    def dato_notacredito(self):
        if self.es_notacredito():
            return NotaCredito.objects.filter(pagonotacredito__pagos=self)[0]
        return None

    def es_recibocajainst(self):
        return self.pagorecibocajainstitucion_set.exists()

    def dato_recibocajainst(self):
        if self.es_recibocajainst():
            return ReciboCajaInstitucion.objects.filter(pagorecibocajainstitucion__pagos=self)[0]
        return None

    def es_chequepostfechado(self):
        if self.pagocheque_set.exists():
            cheque = self.pagocheque_set.all()[0]
            return not cheque.datocheque.a_vista()
        return False

    def es_cheque(self):
        return self.pagocheque_set.exists()

    def dato_cheque(self):
        if self.es_cheque():
            return DatoCheque.objects.filter(pagocheque__pagos=self)[0]
        return None

    def es_transferencia(self):
        return self.pagotransferenciadeposito_set.filter(datotransferenciadeposito__deposito=False).exists()

    def dato_transferencia(self):
        if self.es_transferencia():
            return DatoTransferenciaDeposito.objects.filter(deposito=False, pagotransferenciadeposito__pagos=self)[0]
        return None

    def es_deposito(self):
        return self.pagotransferenciadeposito_set.filter(datotransferenciadeposito__deposito=True).exists()

    def dato_deposito(self):
        if self.es_deposito():
            return DatoTransferenciaDeposito.objects.filter(deposito=True, pagotransferenciadeposito__pagos=self)[0]
        return None

    def es_especievalorada(self):
        return self.rubro.es_especie()

    def dbf_factura(self):
        if self.factura_set.exists():
            return self.factura_set.all()[0]
        return None

    def factura(self):
        if self.factura_set.exists():
            return self.factura_set.all()[0]
        return None

    def recibopago(self):
        if self.recibopago_set.exists():
            return self.recibopago_set.all()[0]
        return None

    def extra_delete(self):
        return [False, False]

    def save(self, *args, **kwargs):
        self.valor = null_to_numeric(self.valor, 2)
        iva = 0
        if self.rubro:
            if self.rubro.iva.id == TIPO_IVA_0_ID:
                iva = 0
            else:
                if self.valor > 0:
                    porciento = ((100 / self.rubro.valortotal) * self.valor / 100)
                    iva = null_to_numeric(self.rubro.valoriva * porciento, 2)
                else:
                    iva = 0
        self.iva = null_to_numeric(iva, 2)
        if not self.anticipado:
            if self.rubro:
                if self.rubro.tiene_descuento():
                    if self.rubro.total_valor_descuento() == self.rubro.valor:
                        self.descuento = null_to_numeric(self.rubro.total_valor_descuento(), 2)
                    else:
                        descuento = ((self.valor - self.iva) / (self.rubro.valortotal - self.rubro.valoriva))
                        self.descuento = null_to_numeric(self.rubro.total_valor_descuento() * descuento, 2)
            else:
                self.descuento = 0
        super(Pago, self).save(*args, **kwargs)


FORMATO_ENVIO_COMPROBANTE = (
    (1, u'NINGUNO'),
    (2, u'ENVIO A SISTEMA EXTERNO'),
    (3, u'CONSULTA POR SISTEMA EXTERNO')
)

FORMATO_PROCESO_COMPROBANTE = (
    (1, u'NINGUNO'),
    (2, u'X-KEY, X-PASSWORD'),
    (3, u'AUTORIZACION'),
    (4, u'AUTORIZACION EN LOGICA'),
    (5, u'TEXTO PLANO'),
    (6, u'PERSONALIZADO')
)

class ProveedorFacturacionElectronica(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    urlfactura = models.CharField(default='', max_length=300, verbose_name=u'url envio')
    urlconsultafactura = models.CharField(default='', max_length=300, verbose_name=u'url de consulta')
    urlnotacredito = models.CharField(default='', max_length=300, verbose_name=u'url envio')
    urlconsultanotacredito = models.CharField(default='', max_length=300, verbose_name=u'url de consulta')
    urlrecibopago = models.CharField(default='', max_length=300, verbose_name=u'url envio')
    urlconsultarecibopago = models.CharField(default='', max_length=300, verbose_name=u'url de consulta')
    urlnotadebito = models.CharField(default='', max_length=300, verbose_name=u'url envio')
    urlconsultanotadebito = models.CharField(default='', max_length=300, verbose_name=u'url de consulta')
    urlrecibocaja = models.CharField(default='', max_length=300, verbose_name=u'url envio')
    formatoenvio = models.IntegerField(choices=FORMATO_ENVIO_COMPROBANTE, default=1, verbose_name=u"Formato de envio")
    formatoproceso = models.IntegerField(choices=FORMATO_PROCESO_COMPROBANTE, default=1, verbose_name=u"Formato de proceso")
    clientid = models.CharField(default='', max_length=200, verbose_name=u'Client ID')
    autorizacion = models.CharField(default='', max_length=200, verbose_name=u'autorizacion')
    apikey = models.CharField(default='', max_length=200, verbose_name=u'API Key')
    usuario = models.CharField(default='', max_length=200, verbose_name=u'Usuario')
    establecimiento = models.CharField(default='', max_length=200, verbose_name=u'Establecimiento')
    envioexportacionfacturas = models.TextField(default='', blank=True, verbose_name=u"Envio exportacion facturas")
    logicaexportacionfacturas = models.TextField(default='', blank=True, verbose_name=u"Información exportacion facturas")
    confirmacionexportacionfacturas = models.TextField(default='', blank=True, verbose_name=u"Confirmación exportacion facturas")
    envioexportacionnotascredito = models.TextField(default='', blank=True, verbose_name=u"Envio exportacion notas de credito")
    logicaexportacionnotascredito = models.TextField(default='', blank=True, verbose_name=u"Información exportacion notas de credito")
    confirmacionexportacionnotascredito = models.TextField(default='', blank=True, verbose_name=u"Confirmación exportacion notas de credito")
    envioexportacionreciboscaja = models.TextField(default='', blank=True, verbose_name=u"Envio exportacion recibos de caja")
    logicaexportacionreciboscaja = models.TextField(default='', blank=True, verbose_name=u"Logica exportacion recibos de caja")
    confirmacionexportacionreciboscaja = models.TextField(default='', blank=True, verbose_name=u"Confirmacion exportacion recibos de caja")
    envioexportacionrecibospago = models.TextField(default='', blank=True, verbose_name=u"Envio exportacion recibos de pago")
    logicaexportacionrecibospago = models.TextField(default='', blank=True, verbose_name=u"Información exportacion recibos de pago")
    confirmacionexportacionrecibospago = models.TextField(default='', blank=True, verbose_name=u"Confirmación exportación recibos de pago")

    def __str__(self):
        return u"%s" % self.nombre

    class Meta:
        verbose_name_plural = u"Proveedores Facturacion Electronica"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def puede_eliminarse(self):
        if self.notacreditotributaria_set.exists():
            return False
        if self.factura_set.exists():
            return False
        if self.tituloinstitucion_set.exists():
            return False
        return True

    def cantidad_facturas(self):
        return self.factura_set.count()

    def cantidad_recibos(self):
        return self.recibopago_set.count()

    def cantidad_recibos_caja(self):
        return self.recibocajainstitucion_set.count()

    def cantidad_notas_creditos(self):
        return self.notacreditotributaria_set.count()

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.urlconsultafactura = null_to_text(self.urlconsultafactura, transform=False)
        self.urlconsultanotacredito = null_to_text(self.urlconsultanotacredito, transform=False)
        self.urlnotacredito = null_to_text(self.urlnotacredito, transform=False)
        self.urlconsultarecibopago = null_to_text(self.urlconsultarecibopago, transform=False)
        self.urlrecibopago = null_to_text(self.urlrecibopago, transform=False)
        self.urlconsultanotadebito = null_to_text(self.urlconsultanotadebito, transform=False)
        self.urlnotadebito = null_to_text(self.urlnotadebito, transform=False)
        self.urlconsultanotadebito = null_to_text(self.urlconsultanotadebito, transform=False)
        self.urlrecibocaja = null_to_text(self.urlrecibocaja, transform=False)
        self.clientid = null_to_text(self.clientid, transform=False)
        self.autorizacion = null_to_text(self.autorizacion, transform=False)
        self.usuario = null_to_text(self.usuario, transform=False)
        self.establecimiento = null_to_text(self.establecimiento, transform=False)
        self.apikey = null_to_text(self.apikey, transform=False)
        self.logicaexportacionfacturas = null_to_text(self.logicaexportacionfacturas, transform=False)
        self.logicaexportacionnotascredito = null_to_text(self.logicaexportacionnotascredito, transform=False)
        self.logicaexportacionreciboscaja = null_to_text(self.logicaexportacionreciboscaja, transform=False)
        self.logicaexportacionrecibospago = null_to_text(self.logicaexportacionrecibospago, transform=False)
        super(ProveedorFacturacionElectronica, self).save(*args, **kwargs)


class TipoTransferencia(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de transferencias"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoTransferencia, self).save(*args, **kwargs)


class DatoTransferenciaDeposito(ModeloBase):
    deposito = models.BooleanField(default=True, verbose_name=u'Es desposito')
    cuentabanco = models.ForeignKey(CuentaBanco, verbose_name=u'Cuenta banco', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha')
    tipotransferencia = models.ForeignKey(TipoTransferencia, blank=True, null=True, verbose_name=u"Tipo de transferencia", on_delete=models.CASCADE)
    referencia = models.CharField(default='', max_length=50, verbose_name=u'Referencia')
    fechabanco = models.DateField(blank=True, null=True, verbose_name=u'Fecha')
    valor = models.FloatField(default=0, verbose_name=u'Valor')

    def __str__(self):
        return u'%s - %s - %s - %s' % ('DEP' if self.deposito else 'TRA', self.cuentabanco, self.fecha.strftime("%d-%m-%Y"), self.referencia)

    class Meta:
        verbose_name_plural = u"Pagos con transferencias/depositos"
        unique_together = ('deposito', 'cuentabanco', 'fecha', 'referencia',)

    def actualiza_valor(self):
        self.valor = null_to_numeric(Pago.objects.filter(pagotransferenciadeposito__datotransferenciadeposito=self, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
        self.save()

    def inscripciones(self):
        return Inscripcion.objects.filter(rubro__pago__pagotransferenciadeposito__datotransferenciadeposito=self).distinct()

    def facturas(self):
        return Factura.objects.filter(pagos__pagotransferenciadeposito__datotransferenciadeposito=self).distinct()

    def recibopagos(self):
        return ReciboPago.objects.filter(pagos__pagotransferenciadeposito__datotransferenciadeposito=self).distinct()

    def extra_delete(self):
        return [False, False]

    def save(self, *args, **kwargs):
        self.referencia = null_to_text(self.referencia)
        super(DatoTransferenciaDeposito, self).save(*args, **kwargs)


class PagoTransferenciaDeposito(ModeloBase):
    datotransferenciadeposito = models.ForeignKey(DatoTransferenciaDeposito, verbose_name=u'Dato', on_delete=models.CASCADE)
    valor = models.FloatField(default=0, verbose_name=u'Valor')
    pagos = models.ManyToManyField(Pago, verbose_name=u'Pagos')
    valido = models.BooleanField(default=True, verbose_name=u"Valido")

    def __str__(self):
        return u'%s' % str(self.valor)

    def padre(self):
        return self.datotransferenciadeposito

    def actualiza_valor(self):
        self.valor = null_to_numeric(self.pagos.filter(valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
        self.save()

    def extra_delete(self):
        return [False, False]


class TipoCheque(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de cheques"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoCheque, self).save(*args, **kwargs)


class DatoCheque(ModeloBase):
    banco = models.ForeignKey(Banco, verbose_name=u'Banco', on_delete=models.CASCADE)
    cuenta = models.CharField(default='', max_length=50, verbose_name=u'Cuenta')
    numero = models.CharField(default='', max_length=50, verbose_name=u'Numero')
    fecha = models.DateField(verbose_name=u'Fecha de emision')
    fechacobro = models.DateField(verbose_name=u'Fecha de cobro')
    tipocheque = models.ForeignKey(TipoCheque, verbose_name=u"Tipos de cheques", on_delete=models.CASCADE)
    emite = models.CharField(default='', max_length=100, verbose_name=u'Emite')
    protestado = models.BooleanField(default=False, verbose_name=u'Protestado')
    valido = models.BooleanField(default=True, verbose_name=u"Valido")
    valor = models.FloatField(default=0, verbose_name=u'Valor')

    def __str__(self):
        return u'%s - %s - %s' % (self.banco, self.cuenta, self.numero)

    class Meta:
        verbose_name_plural = u"Datos de Cheques"
        ordering = ['-fechacobro']
        unique_together = ('banco', 'cuenta', 'numero',)

    def a_vista(self):
        return self.fecha == self.fechacobro

    def esta_protestado(self):
        return self.chequeprotestado_set.exists()

    def dato_protesto(self):
        if self.esta_protestado():
            return self.chequeprotestado_set.all()[0]
        return None

    def tiene_pagos(self):
        return self.pagocheque_set.exists()

    def inscripciones(self):
        return Inscripcion.objects.filter(rubro__pago__pagocheque__datocheque=self).distinct()

    def facturas(self):
        return Factura.objects.filter(pagos__pagocheque__datocheque=self).distinct()

    def recibopagos(self):
        return ReciboPago.objects.filter(pagos__pagocheque__datocheque=self).distinct()

    def actualiza_valor(self):
        self.valor = null_to_numeric(Pago.objects.filter(valido=True, pagocheque__datocheque=self).aggregate(valor=Sum('valor'))['valor'], 2)
        self.save()

    def extra_delete(self):
        return [False, False]

    def save(self, *args, **kwargs):
        self.numero = null_to_text(self.numero)
        self.cuenta = null_to_text(self.cuenta)
        self.emite = null_to_text(self.emite)
        super(DatoCheque, self).save(*args, **kwargs)


class PagoCheque(ModeloBase):
    datocheque = models.ForeignKey(DatoCheque, verbose_name=u"Dato", on_delete=models.CASCADE)
    valor = models.FloatField(default=0, verbose_name=u'Valor')
    pagos = models.ManyToManyField(Pago, verbose_name=u'Pagos')
    valido = models.BooleanField(default=True, verbose_name=u"Valido")

    def __str__(self):
        return u'%s' % str(self.valor)

    def padre(self):
        return self.datocheque

    def actualiza_valor(self):
        self.valor = null_to_numeric(self.pagos.filter(valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
        self.save()

    def extra_delete(self):
        return [False, False]


class TipoTarjetaBanco(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    difiere = models.BooleanField(default=False, verbose_name=u'Difiere')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de tarjetas de bancos"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoTarjetaBanco, self).save(*args, **kwargs)


class TipoTarjeta(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de tarjetas"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoTarjeta, self).save(*args, **kwargs)


class TipoEmisorTarjeta(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    codigodatafast = models.CharField(default='', max_length=10, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de emisores de tarjetas "
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.codigodatafast = null_to_text(self.codigodatafast)
        super(TipoEmisorTarjeta, self).save(*args, **kwargs)


class IdentificacionTipoEmisorTarjeta(ModeloBase):
    tipoemisortarjeta = models.ForeignKey(TipoEmisorTarjeta, verbose_name=u'Tipo tarjeta banco', on_delete=models.CASCADE)
    procesadorpagotarjeta = models.ForeignKey(ProcesadorPagoTarjeta, verbose_name=u'Tipo tarjeta banco', on_delete=models.CASCADE)
    codigo = models.CharField(default='', max_length=25, verbose_name=u'codigo')

    def save(self, *args, **kwargs):
        self.codigo = null_to_text(self.codigo)
        super(IdentificacionTipoEmisorTarjeta, self).save(*args, **kwargs)

class CoordinadorCarrera(ModeloBase):
    coordinacion = models.ForeignKey(Coordinacion, blank=True, null=True, verbose_name=u'Coordinación', on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, verbose_name=u'Carrera', on_delete=models.CASCADE)
    modalidad = models.ForeignKey(Modalidad, verbose_name=u'Modalidad', blank=True, null=True, on_delete=models.CASCADE)
    persona = models.ForeignKey(Persona, verbose_name=u'Persona', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name_plural = u"Coordinadores de carreras"
        unique_together = ('coordinacion', 'carrera', 'modalidad')

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("CoordinadorCarrera.objects.filter(Q(persona__nombre1__contains='%s') Q(persona__nombre2__contains='%s') | Q(persona__apellido1__contains='%s') | Q(persona__apellido2__contains='%s') | Q(id=id_search('%s')))" % (q, q, q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.persona.nombre_completo_inverso() + ' - ' + str(self.id)

    def mis_carreras(self):
        return Carrera.objects.filter(coordinadorcarrera__persona=self.persona).distinct()


class PerfilAccesoUsuario(ModeloBase):
    coordinacion = models.ForeignKey(Coordinacion, blank=True, null=True, verbose_name=u'Coordinación', on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, verbose_name=u'Carrera', on_delete=models.CASCADE)
    modalidad = models.ForeignKey(Modalidad, blank=True, null=True, verbose_name=u'Modalidad', on_delete=models.CASCADE)
    persona = models.ForeignKey(Persona, verbose_name=u'Persona', on_delete=models.CASCADE)

    class Meta:
        ordering = ['coordinacion', 'carrera', 'persona']
        unique_together = ('coordinacion', 'carrera', 'persona', 'modalidad')


class NivelLibreCoordinacion(ModeloBase):
    nivel = models.ForeignKey(Nivel, verbose_name=u'Nivel', on_delete=models.CASCADE)
    coordinacion = models.ForeignKey(Coordinacion, verbose_name=u'Coordinación', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s %s' % (self.nivel, self.coordinacion)

    class Meta:
        verbose_name_plural = u"Niveles libres de coordinaciones"
        unique_together = ('nivel',)


class InscripcionFlags(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    tienechequeprotestado = models.BooleanField(default=False, verbose_name=u'Tiene protestos')
    tienedeudaexterna = models.BooleanField(default=False, verbose_name=u'Deuda desde otra plataforma')
    permitepagoparcial = models.BooleanField(default=False, verbose_name=u'Permite pagos parciales')
    motivo = models.TextField(default='', verbose_name=u'Motivo')
    puedecobrar = models.BooleanField(default=False, verbose_name=u'Puede cobrar con nota de debito')
    nogeneracosto = models.BooleanField(default=False, verbose_name=u'Genera costos')
    notificardeuda = models.BooleanField(default=False, verbose_name=u'Notificar Deuda')
    puedetomarsupletorio = models.BooleanField(default=False, verbose_name=u'Puede tomar o dar supletorio sin pago')

    def __str__(self):
        return u'%s' % self.inscripcion

    class Meta:
        verbose_name_plural = u"Inscripciones con observaciones"
        unique_together = ('inscripcion',)

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        super(InscripcionFlags, self).save(*args, **kwargs)



class GrupoCoordinadorCarrera(ModeloBase):
    group = models.ForeignKey(Group, verbose_name=u'Grupo', on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, verbose_name=u'Carrera', on_delete=models.CASCADE)

    def __str__(self):
        return u'Grupos responsables de carreras'

    class Meta:
        verbose_name_plural = u"Grupos responsables de carreras"
        unique_together = ('group', 'carrera',)


class Cargo(ModeloBase):
    nombre = models.CharField(default='', max_length=300, verbose_name=u'Nombre')
    prioridad = models.IntegerField(default=0)
    multiples = models.BooleanField(default=False)
    codigosniese = models.CharField(max_length=15, default='', verbose_name=u'Codigo Sniese')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Cargos"
        ordering = ['prioridad', 'nombre']
        unique_together = ('nombre',)

    def tiene_responsable(self):
        return self.cargoinstitucion_set.exists()

    def responsables(self):
        return self.cargoinstitucion_set.all()

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(Cargo, self).save(*args, **kwargs)


class CargoCoordinacion(ModeloBase):
    cargo = models.ForeignKey(Cargo, verbose_name=u'Cargo', on_delete=models.CASCADE)
    coordinacion = models.ForeignKey(Coordinacion, verbose_name=u'Coordinacion', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.cargo, self.coordinacion)

    class Meta:
        verbose_name_plural = u"Cargos coordinaciones"
        ordering = ['cargo', 'coordinacion']
        unique_together = ('cargo', 'coordinacion',)


class CargoInstitucion(ModeloBase):
    cargo = models.ForeignKey(Cargo, verbose_name=u'Cargo', on_delete=models.CASCADE)
    persona = models.ForeignKey(Persona, verbose_name=u'Persona', on_delete=models.CASCADE)
    sede = models.ForeignKey(Sede, blank=True, null=True, verbose_name=u'Sede', on_delete=models.CASCADE)

    def __str__(self):
        return u'Cargo: %s responsable: %s' % (self.cargo, self.persona)

    class Meta:
        verbose_name_plural = u"Cargos de la institución"
        ordering = ['cargo', 'persona']

    def save(self, *args, **kwargs):
        super(CargoInstitucion, self).save(*args, **kwargs)


class TituloInstitucion(ModeloBase):
    nombre = models.CharField(default='', max_length=300, verbose_name=u'Nombre')
    telefono = models.CharField(default='', max_length=200, verbose_name=u'Teléfonos')
    correo = models.CharField(default='', max_length=200, verbose_name=u'Correo electrónico')
    web = models.CharField(default='', max_length=200, verbose_name=u'Web')
    provincia = models.ForeignKey(Provincia, blank=True, null=True, verbose_name=u"Provincia", on_delete=models.CASCADE)
    canton = models.ForeignKey(Canton, blank=True, null=True, verbose_name=u"Cantón", on_delete=models.CASCADE)
    parroquia = models.ForeignKey(Parroquia, blank=True, null=True, verbose_name=u"Parroquia", on_delete=models.CASCADE)
    sector = models.CharField(default='', max_length=100, verbose_name=u"Sector")
    ciudad = models.CharField(default='', max_length=50, verbose_name=u"Ciudad")
    direccion = models.CharField(default='', max_length=300, verbose_name=u'Dirección')
    ruc = models.CharField(default='', max_length=20, verbose_name=u"RUC")
    obligadocontabilidad = models.BooleanField(default=True, verbose_name=u"Obligado a llevar contabilidad")
    contribuyenteespecial = models.BooleanField(default=False, verbose_name=u"Contribuyente especial")
    matricularcondeuda = models.BooleanField(default=True, verbose_name=u"Matricular con deuda")
    costoperiodo = models.BooleanField(default=True, verbose_name=u"Usa costo periodo")
    costoenmalla = models.BooleanField(default=False, verbose_name=u"Usa costo en malla")
    facturacionelectronicaexterna = models.BooleanField(default=False, verbose_name=u"Usa facturación electrónica externa")
    autofirmadocomprobantes = models.BooleanField(default=False, verbose_name=u"Auto firmado nota de credito")
    urlfacturacion = models.CharField(default='', max_length=100, verbose_name=u'url facturacion')
    deudabloqueaasistencia = models.BooleanField(default=False, verbose_name=u"Bloquea modulo mis materias")
    deudabloqueamimalla = models.BooleanField(default=False, verbose_name=u"Bloquea modulo mi malla")
    deudabloqueamishorarios = models.BooleanField(default=False, verbose_name=u"Bloquea modulo mis horarios")
    deudabloqueadocumentos = models.BooleanField(default=False, verbose_name=u"Bloquea modulo descarga de documentos")
    deudabloqueacronograma = models.BooleanField(default=False, verbose_name=u"Bloquea modulo mi cronograma")
    deudabloqueamatriculacion = models.BooleanField(default=False, verbose_name=u"Bloquea modulo matriculacion")
    deudabloqueasolicitud = models.BooleanField(default=False, verbose_name=u"Bloquea modulo solicitud a secretaria")
    deudabloqueanotas = models.BooleanField(default=False, verbose_name=u"Bloquea modulo record académico")
    matriculapormateria = models.BooleanField(default=False, verbose_name=u"Matriculacion por materias")
    diasaprobacioningresonotas = models.IntegerField(default=0, verbose_name=u"Dias para ingreso de notas")
    emailhost = models.CharField(default='', max_length=100, verbose_name=u'Email host')
    emaildomain = models.CharField(default='', max_length=100, verbose_name=u'Dominio de correo institucional')
    domainapp = models.CharField(default='', max_length=100, verbose_name=u'Dominio aplicacion')
    emailport = models.IntegerField(default=0, verbose_name=u'Email port')
    emailhostuser = models.CharField(default='', max_length=100, verbose_name=u'Email host user')
    emailpassword = models.CharField(default='', max_length=100, verbose_name=u'Email password')
    enviosolocorreoinstitucional = models.BooleanField(default=False, verbose_name=u"Envío solo correo institucional")
    usatls = models.BooleanField(default=False, verbose_name=u"Envío solo correo institucional")
    horarioestricto = models.BooleanField(default=False, verbose_name=u"Horario estricto")
    abrirmateriasenfecha = models.BooleanField(default=False, verbose_name=u"Horario estricto")
    clasescontinuasautomaticas = models.BooleanField(default=False, verbose_name=u"Clases continuas automáticas")
    clasescierreautomatico = models.BooleanField(default=False, verbose_name=u"Cierre automático de clases")
    minutosapeturaantes = models.IntegerField(default=0, verbose_name=u'Minutos de apertura antes del inicio de clases')
    minutosapeturadespues = models.IntegerField(default=0, verbose_name=u'Minutos de apertura despues de inicio clases')
    minutoscierreantes = models.IntegerField(default=0, verbose_name=u'Minutos de cierre antes de terminación')
    defaultpassword = models.CharField(default='', max_length=100, verbose_name=u'Clave por defecto')
    claveusuariocedula = models.BooleanField(default=False, verbose_name=u"Cédula como clave de usuario")
    nombreusuariocedula = models.BooleanField(default=False, verbose_name=u"Cédula como clave de usuario")
    correoobligatorio = models.BooleanField(default=False, verbose_name=u"Correo obligatorio")
    actualizarfotoalumnos = models.BooleanField(default=False, verbose_name=u"Actualizar foto de alumnos")
    actualizarfotoadministrativos = models.BooleanField(default=False, verbose_name=u"Administrativos actualizan foto")
    controlunicocredenciales = models.BooleanField(default=False, verbose_name=u"Control único credenciales")
    estudiantevefecharubro = models.BooleanField(default=False, verbose_name=u"Control único credenciales")
    pagoestrictoasistencia = models.BooleanField(default=False, verbose_name=u"Pago estricto asistencia")
    pagoestrictonotas = models.BooleanField(default=False, verbose_name=u"Pago estricto notas")
    preguntasinscripcion = models.BooleanField(default=False, verbose_name=u"Preguntas inscripcion")
    solicitudnumeracion = models.BooleanField(default=False, verbose_name=u"Números en solicitud")
    solicitudnumeroautomatico = models.BooleanField(default=False, verbose_name=u"Solicitud número automatico")
    permitealumnoregistrar = models.BooleanField(default=False, verbose_name=u"Solicitud número automatico")
    permitealumnoelegirresponsable = models.BooleanField(default=False, verbose_name=u"Permite al alumno elegir responsable")
    diasvencimientosolicitud = models.IntegerField(default=0, verbose_name=u'Díaz vencimiento solicitud')
    especificarcantidadsolicitud = models.BooleanField(default=False, verbose_name=u"Solicitudes a secretaría")
    solicitudmatriculagratuitas = models.BooleanField(default=False, verbose_name=u"Solicitudes en matricula gratuitas")
    cuotaspagoestricto = models.IntegerField(default=0, verbose_name=u'Cuotas pago estricto')
    apikey = models.CharField(default='', max_length=100, verbose_name=u'API Key')
    apikeymooc = models.CharField(default='', max_length=100, verbose_name=u'API Key')
    pfx = models.CharField(default='', max_length=100, verbose_name=u'PFX')
    codigoporcentajeiva = models.CharField(default='', max_length=5, verbose_name=u'Codigo IVA')
    urlaplicacionandroid = models.CharField(default='', max_length=100, verbose_name=u'url Aplicación estudiantes android')
    urlaplicacionios = models.CharField(default='', max_length=100, verbose_name=u'url Aplicación estudiantes IOS')
    urlaplicacionwindows = models.CharField(default='', max_length=100, verbose_name=u'url Aplicación estudiantes Windows')
    urlwebservicead = models.CharField(default='', max_length=100, verbose_name=u'url Web Service Active Directory')
    usabiblioteca = models.BooleanField(default=False, verbose_name=u"Usa biblioteca")
    documentoscoleccion = models.BooleanField(default=False, verbose_name=u"Documentos colección")
    documentosautonumeracion = models.BooleanField(default=False, verbose_name=u"Autonumeración de documentos")
    documentoscoleccionautonumeracion = models.BooleanField(default=False, verbose_name=u"Documentos colección autonumeración")
    egresamallacompleta = models.BooleanField(default=True, verbose_name=u"Egresar con malla completa")
    versionstaticsjs = models.IntegerField(default=1, verbose_name=u"Version archivo js")
    versionstaticscss = models.IntegerField(default=1, verbose_name=u"Version archivo css")
    versionstaticsimg = models.IntegerField(default=1, verbose_name=u"Version archivo img")
    porcentajeformalizar = models.FloatField(default=0, verbose_name=u'Porcentaje para formalizar matriculas')
    formalizarxporcentaje = models.BooleanField(default=False, verbose_name=u"Formalizar por porcentaje pagado")
    formalizarxmatricula = models.BooleanField(default=True, verbose_name=u"Formalizar por valor de matricula")
    vencematriculaspordias = models.BooleanField(default=True, verbose_name=u"Vence matriculas por dias")
    diashabiles = models.BooleanField(default=False, verbose_name=u"Dias hábiles")
    diasmatriculaexpirapresencial = models.IntegerField(default=0, verbose_name=u"Dias matricula expira presencial")
    diasmatriculaexpirasemipresencial = models.IntegerField(default=0, verbose_name=u"Dias matricula expira semipresencial")
    diasmatriculaexpiradistancia = models.IntegerField(default=0, verbose_name=u"Dias matricula expira distancia")
    diasmatriculaexpiraonline = models.IntegerField(default=0, verbose_name=u"Dias matricula expira online")
    diasmatriculaexpirahibrida = models.IntegerField(default=0, verbose_name=u"Dias matricula expira hibrida")
    fechaexpiramatriculagrado = models.DateField(null=True, blank=True, verbose_name=u"Fecha expira matricula Grado")
    fechaexpiramatriculaposgrado = models.DateField(null=True, blank=True, verbose_name=u"Fecha expira matricula Posgrado")
    cronenviomateriaslms = models.BooleanField(default=False, verbose_name=u"Documentos colección autonumeración")
    cronbloqueusuariolms = models.BooleanField(default=False, verbose_name=u"Documentos colección autonumeración")

    class Meta:
        verbose_name_plural = u"Institución"

    def __str__(self):
        return u'%s' % self.nombre

    @staticmethod
    def cantidad_integrantes(grupo):
        return User.objects.filter(groups=grupo).count()

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.telefono = null_to_text(self.telefono)
        self.direccion = null_to_text(self.direccion, cap=True)
        self.sector = null_to_text(self.sector)
        self.ciudad = null_to_text(self.ciudad)
        self.ruc = null_to_text(self.ruc)
        self.telefono = null_to_text(self.telefono)
        self.correo = null_to_text(self.correo, lower=True)
        self.web = null_to_text(self.web, lower=True)
        super(TituloInstitucion, self).save(*args, **kwargs)

TIPOS_VALE_CAJA = (
    (1, u'EGRESO'),
    (2, u'INGRESO')
)

class ValeCaja(ModeloBase):
    sesion = models.ForeignKey(SesionCaja, verbose_name=u'Sesion de caja', on_delete=models.CASCADE)
    tipooperacion = models.IntegerField(choices=TIPOS_VALE_CAJA, default=1, verbose_name=u'Tipo vale')
    valor = models.FloatField(default=0, verbose_name=u'Valor')
    recibe = models.ForeignKey(Persona, related_name='+', blank=True, null=True, verbose_name=u'Recibe', on_delete=models.CASCADE)
    responsable = models.ForeignKey(Persona, related_name='+', blank=True, null=True, verbose_name=u'Recibe', on_delete=models.CASCADE)
    referencia = models.CharField(default='', max_length=100, blank=True, null=True, verbose_name=u'Referencia')
    concepto = models.TextField(default='', verbose_name=u'Concepto')
    fecha = models.DateField(verbose_name=u"Fecha")
    hora = models.TimeField(verbose_name=u'Hora')

    def __str__(self):
        return u'%s - %s' % (self.referencia, str(self.valor))

    class Meta:
        ordering = ['-fecha', 'hora']
        verbose_name_plural = u"Vales de cajas"

    def tipo_repr(self):
        return TIPOS_VALE_CAJA[self.tipooperacion - 1][1]

    def puede_eliminarse(self):
        return self.sesion.abierta

    def extra_delete(self):
        if not self.puede_eliminarse():
            return [False, False]
        return [True, False]

    def save(self, *args, **kwargs):
        self.concepto = null_to_text(self.concepto)
        self.referencia = null_to_text(self.referencia)
        super(ValeCaja, self).save(*args, **kwargs)




class Impresion(ModeloBase):
    usuario = models.ForeignKey(User, verbose_name=u'Usuario', on_delete=models.CASCADE)
    impresa = models.BooleanField(default=False, verbose_name=u'Impresa')
    contenido = models.TextField(default='', verbose_name=u'Contenido')


class TipoInstitucion(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de instituciones"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoInstitucion, self).save(*args, **kwargs)


class Institucion(ModeloBase):
    tipo = models.ForeignKey(TipoInstitucion, verbose_name=u"Tipo de Institución", on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")

    def __str__(self):
        return u'%s (%s)' % (self.nombre, self.tipo)

    class Meta:
        verbose_name_plural = u"Instituciones"
        ordering = ['nombre']
        unique_together = ('tipo', 'nombre',)

    def mis_cargos(self):
        if not AutoridadesInstitucion.objects.all().exists():
            autoridades = AutoridadesInstitucion(institucion=self,
                                                 rector='',
                                                 vicerectoracademico='',
                                                 secretariageneral='')
            autoridades.save()
        else:
            autoridades = self.autoridadesinstitucion_set.all()[0]
        return autoridades

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(Institucion, self).save(*args, **kwargs)


class AutoridadesInstitucion(ModeloBase):
    institucion = models.ForeignKey(Institucion, verbose_name=u"Institución", on_delete=models.CASCADE)
    rector = models.ForeignKey(Persona, related_name='+', blank=True, null=True, verbose_name=u"Rector", on_delete=models.CASCADE)
    vicerectoracademico = models.ForeignKey(Persona, related_name='+', blank=True, null=True, verbose_name=u"Vicerector", on_delete=models.CASCADE)
    secretariageneral = models.ForeignKey(Persona, related_name='+', blank=True, null=True, verbose_name=u"Secretaria general", on_delete=models.CASCADE)




class PerfilInscripcion(ModeloBase):
    persona = models.ForeignKey(Persona, verbose_name=u"Persona", blank=True, null=True, on_delete=models.CASCADE)
    raza = models.ForeignKey(Raza, blank=True, null=True, verbose_name=u'Raza', on_delete=models.CASCADE)
    nacionalidadindigena = models.ForeignKey(NacionalidadIndigena, blank=True, null=True, verbose_name=u'Nacionalidad indigena', on_delete=models.CASCADE)
    esextranjero = models.BooleanField(default=False, verbose_name=u"Es extranjero?")
    tienediscapacidad = models.BooleanField(default=False, verbose_name=u"Tiene Discapacidad?")
    tipodiscapacidad = models.ForeignKey(Discapacidad, null=True, blank=True, verbose_name=u"Tipo de Discapacidad", on_delete=models.CASCADE)
    porcientodiscapacidad = models.FloatField(default=0, verbose_name=u'% de Discapacidad')
    carnetdiscapacidad = models.CharField(default='', max_length=50, verbose_name=u'Carnet Discapacitado')

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name_plural = u"Perfiles sociales"
        unique_together = ('persona',)

    def save(self, *args, **kwargs):
        self.carnetdiscapacidad = null_to_text(self.carnetdiscapacidad)
        self.porcientodiscapacidad = null_to_numeric(self.porcientodiscapacidad, 0)
        super(PerfilInscripcion, self).save(*args, **kwargs)


class PerfilDocente(ModeloBase):
    persona = models.ForeignKey(Persona, verbose_name=u"Persona", blank=True, null=True, on_delete=models.CASCADE)
    raza = models.ForeignKey(Raza, blank=True, null=True, verbose_name=u'Raza', on_delete=models.CASCADE)
    nacionalidadindigena = models.ForeignKey(NacionalidadIndigena, blank=True, null=True, verbose_name=u'Nacionalidad indigena', on_delete=models.CASCADE)
    esextranjero = models.BooleanField(default=False, verbose_name=u"Es extranjero?")
    tienediscapacidad = models.BooleanField(default=False, verbose_name=u"Tiene Discapacidad?")
    tipodiscapacidad = models.ForeignKey(Discapacidad, null=True, blank=True, verbose_name=u"Tipo de Discapacidad", on_delete=models.CASCADE)
    porcientodiscapacidad = models.FloatField(default=0, verbose_name=u'% de Discapacidad')
    carnetdiscapacidad = models.CharField(default='', max_length=50, verbose_name=u'Carnet Discapacitado')

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name_plural = u"Perfiles sociales"
        unique_together = ('persona',)

    def save(self, *args, **kwargs):
        self.carnetdiscapacidad = null_to_text(self.carnetdiscapacidad)
        self.porcientodiscapacidad = null_to_numeric(self.porcientodiscapacidad, 0)
        super(PerfilDocente, self).save(*args, **kwargs)


TIPOS_UNIVERSIDAD_MOVILIDAD = (
    (1, u'PÚBLICA'),
    (2, u'PARTICULAR')
)


class EstudioPersona(ModeloBase):
    persona = models.ForeignKey(Persona, verbose_name=u"Persona", blank=True, null=True, on_delete=models.CASCADE)
    superior = models.BooleanField(default=False, verbose_name=u'Estudios superiores')
    institucioneducacionbasica = models.ForeignKey(Colegio, blank=True, null=True, verbose_name=u'Colegio', on_delete=models.CASCADE)
    especialidadeducacionbasica = models.ForeignKey(Especialidad, blank=True, null=True, verbose_name=u'Especialidad', on_delete=models.CASCADE)
    abanderado = models.BooleanField(default=False, verbose_name=u'Abanderado')
    fechagraduacion = models.DateField(blank=True, null=True, verbose_name=u"Fecha graduación")
    institucioneducacionsuperior = models.ForeignKey(TecnologicoUniversidad, blank=True, null=True, verbose_name=u'Tecnologico u universidad', on_delete=models.CASCADE)
    niveltitulacion = models.ForeignKey(NivelTitulacion, blank=True, null=True, verbose_name=u'Nivel titulación', on_delete=models.CASCADE)
    detalleniveltitulacion = models.ForeignKey(DetalleNivelTitulacion, blank=True, null=True, verbose_name=u'Nivel titulación', on_delete=models.CASCADE)
    carrera = models.CharField(default='', max_length=400, verbose_name=u'Carrera')
    titulo = models.CharField(default='', max_length=400, verbose_name=u'Titulo')
    aliastitulo = models.CharField(default='', max_length=15, verbose_name=u'Alias titulo')
    registro = models.CharField(default='', max_length=50, verbose_name=u'Registro SENESCYT')
    fecharegistro = models.DateField(blank=True, null=True, verbose_name=u"Fecha registro SENESCYT")
    cursando = models.BooleanField(default=False, verbose_name=u'Estudios actuales')
    cicloactual = models.CharField(default='', max_length=100, verbose_name=u'Ciclo actual')
    fechainicio = models.DateField(verbose_name=u"Fecha inicio", blank=True, null=True)
    fechafin = models.DateField(blank=True, null=True, verbose_name=u"Fecha fin")
    archivo = models.FileField(upload_to='estudiopersona/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    verificado = models.BooleanField(default=False, verbose_name=u'Verificado')
    principal = models.BooleanField(default=False, verbose_name=u'Principal')
    aplicabeca = models.BooleanField(default=False, verbose_name=u'Tiene Beca')
    tipobeca = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Tipo Beca', choices=TIPOS_BECA)
    montobeca = models.FloatField(default=0, verbose_name=u'Monto Beca')
    documento = models.FileField(upload_to='estudiopersona/%Y/%m/%d', blank=True, null=True, verbose_name=u'Documento')
    titulocolegio = models.CharField(default='', max_length=400, verbose_name=u'Titulo colegio')
    universidadprocede = models.CharField(verbose_name=u'Universidad de la que viene', max_length=500, blank=False, null=True)
    tipouniversidadprocede = models.IntegerField(choices=TIPOS_UNIVERSIDAD_MOVILIDAD, default=1, null=False, blank=True, verbose_name=u"Tipo de universidad")
    campoamplio = models.ForeignKey(CampoAmplioConocimiento, blank=True, null=True,  verbose_name=u'Campo Amplio de Conocimiento', on_delete=models.CASCADE)
    campoespecifico = models.ForeignKey(CampoEspecificoConocimiento, blank=True, null=True,  verbose_name=u'Campo Especifico de Conocimiento', on_delete=models.CASCADE)
    campodetallado = models.ForeignKey(CampoDetalladoConocimiento, blank=True, null=True,   verbose_name=u'Campo Detallado de Conocimiento', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.titulo if self.superior else self.especialidadeducacionbasica.nombre

    class Meta:
        verbose_name_plural = u"Estudios realizados"

    def extra_delete(self):
        if self.verificado:
            return [False, False]
        return [True, False]

    def save(self, *args, **kwargs):
        self.titulo = null_to_text(self.titulo)
        self.titulocolegio = null_to_text(self.titulocolegio)
        self.carrera = null_to_text(self.carrera)
        self.registro = null_to_text(self.registro)
        self.cicloactual = null_to_text(self.cicloactual)
        super(EstudioPersona, self).save(*args, **kwargs)




class HistoricoRecordAcademico(ModeloBase):
    recordacademico = models.ForeignKey(RecordAcademico, blank=True, null=True, verbose_name=u'Record academico', on_delete=models.CASCADE)
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    # modulomalla = models.ForeignKey(ModuloMalla, blank=True, null=True, verbose_name=u'Modulo malla', on_delete=models.CASCADE)
    asignaturamalla = models.ForeignKey(AsignaturaMalla, blank=True, null=True, verbose_name=u'Modulo malla', on_delete=models.CASCADE)
    asignatura = models.ForeignKey(Asignatura, verbose_name=u'Asignatura', on_delete=models.CASCADE)
    nota = models.FloatField(default=0, verbose_name=u'Nota')
    asistencia = models.FloatField(default=0, verbose_name=u'Asistencia')
    sinasistencia = models.BooleanField(default=False, verbose_name=u'Sin asistencia')
    fecha = models.DateField(verbose_name=u'Record academico')
    noaplica = models.BooleanField(default=False, verbose_name=u'No aplica para matricularse')
    aprobada = models.BooleanField(default=False, verbose_name=u'Aprobada')
    causa_homologacion = models.ForeignKey(CausaHomologacion, null=True, blank=True, on_delete=models.PROTECT)
    convalidacion = models.BooleanField(default=False, verbose_name=u'Homologada')
    pendiente = models.BooleanField(default=False, verbose_name=u'Pendiente')
    creditos = models.FloatField(default=0, blank=True, verbose_name=u'créditos')
    horas = models.FloatField(default=0, blank=True, verbose_name=u'Horas')
    homologada = models.BooleanField(default=False, verbose_name=u'Homologada')
    validacreditos = models.BooleanField(default=True, verbose_name=u'Valida para créditos')
    validapromedio = models.BooleanField(default=True, verbose_name=u'Valida para promedios')
    libreconfiguracion = models.BooleanField(default=False, verbose_name=u"Libre configuracion")
    optativa = models.BooleanField(default=False, verbose_name=u"Optativa")
    observaciones = models.TextField(default='', blank=True, null=True, verbose_name=u'Observaciones')
    materiaregular = models.ForeignKey(Materia, blank=True, null=True, verbose_name=u'Materia regular', on_delete=models.CASCADE)
    padre = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, verbose_name='Padre (histórico)', help_text='Otro registro histórico que actúa como padre')

    def __str__(self):
        return u'%s [Nota:%s Asist:%s] %s' % (self.asignatura, str(self.nota), str(self.asistencia), ("aprobado" if self.aprobada else "suspenso"))

    class Meta:
        verbose_name_plural = u"Historia de registros academicos"
        unique_together = ('inscripcion', 'asignatura', 'fecha')

    def esta_suspensa(self):
        return not self.aprobada

    def matricula_actual(self):
        return self.inscripcion.historicorecordacademico_set.filter(asignatura=self.asignatura).exclude(noaplica=True).exclude(convalidacion=True).exclude(homologada=True).distinct().count()

    def tiene_malla(self):
        return self.inscripcion.tiene_malla()

    def existe_en_malla(self):
        return self.inscripcion.mi_malla().asignaturamalla_set.filter(asignatura=self.asignatura).exists()


    def nivel_asignatura(self):
        if self.existe_en_malla():
            return self.inscripcion.mi_malla().asignaturamalla_set.filter(asignatura=self.asignatura)[0].nivelmalla
        return None

    def tiene_acta_nivel(self):
        return self.materiaregular_id > 0

    def tiene_acta_curso(self):
        return self.materiacurso_id > 0

    def acta_materia_nivel(self):
        if self.tiene_acta_nivel():
            return self.materiaregular
        return None

    def acta_materia_curso(self):
        if self.tiene_acta_curso():
            return self.materiacurso
        return None

    def periodo(self):
        if self.tiene_acta_nivel():
            return self.acta_materia_nivel().nivel.periodo
        return None

    def actualizar(self):
        if not self.inscripcion.recordacademico_set.filter(asignatura=self.asignatura).exists():
            record = RecordAcademico(inscripcion=self.inscripcion,
                                     asignatura=self.asignatura,
                                     matriculas=self.matricula_actual(),
                                     asignaturamalla=self.asignaturamalla,
                                     trabajotitulacionmalla=self.trabajotitulacionmalla,
                                     nota=self.nota,
                                     asistencia=self.asistencia,
                                     sinasistencia=self.sinasistencia,
                                     fecha=self.fecha,
                                     noaplica=self.noaplica,
                                     aprobada=self.aprobada,
                                     convalidacion=self.convalidacion,
                                     homologada=self.homologada,
                                     pendiente=self.pendiente,
                                     creditos=self.creditos,
                                     horas=self.horas,
                                     validacreditos=self.validacreditos,
                                     validapromedio=self.validapromedio,
                                     libreconfiguracion=self.libreconfiguracion,
                                     optativa=self.optativa,
                                     materiaregular=self.materiaregular,
                                     materiacurso=self.materiacurso,
                                     materiacursotitulacion=self.materiacursotitulacion,
                                     internado=self.internado,
                                     valoracioncalificacion=self.valoracioncalificacion,
                                     observaciones=self.observaciones,
                                     materiahomologacion=self.materiahomologacion,
                                     modulovalidacion=self.modulovalidacion)
            record.save()
            historico = record.mi_historico()
            historico.recordacademico = record
            historico.save()
        else:
            seleccionada = self.inscripcion.historicorecordacademico_set.filter(asignatura=self.asignatura).order_by('-aprobada', '-nota')[0]
            record = self.inscripcion.recordacademico_set.filter(asignatura=self.asignatura)[0]
            record.matriculas = self.matricula_actual()
            record.asignaturamalla = seleccionada.asignaturamalla
            record.trabajotitulacionmalla = seleccionada.trabajotitulacionmalla
            record.nota = seleccionada.nota
            record.asistencia = seleccionada.asistencia
            record.sinasistencia = seleccionada.sinasistencia
            record.fecha = seleccionada.fecha
            record.noaplica = seleccionada.noaplica
            record.aprobada = seleccionada.aprobada
            record.convalidacion = seleccionada.convalidacion
            record.homologada = seleccionada.homologada
            record.libreconfiguracion = seleccionada.libreconfiguracion
            record.optativa = seleccionada.optativa
            record.pendiente = seleccionada.pendiente
            record.creditos = seleccionada.creditos
            record.horas = seleccionada.horas
            record.validacreditos = seleccionada.validacreditos
            record.validapromedio = seleccionada.validapromedio
            record.materiaregular = seleccionada.materiaregular
            record.materiacurso = seleccionada.materiacurso
            record.materiacursotitulacion = seleccionada.materiacursotitulacion
            record.valoracioncalificacion = seleccionada.valoracioncalificacion
            record.observaciones = seleccionada.observaciones
            record.materiahomologacion = seleccionada.materiahomologacion
            record.internado = seleccionada.internado
            record.modulovalidacion = seleccionada.modulovalidacion
            record.save()
            record.inscripcion.save()
        self.recordacademico = record
        self.save()
        record.matriculas = record.matricula_actual()
        record.save()
        actualiza=self.inscripcion.actualiza_promedio_record()
        self.inscripcion.save()

    def datos_convalidacion(self):
        if not self.recordacademico.convalidacioninscripcion_set.exists():
            convalidacion = ConvalidacionInscripcion(record=self.recordacademico,
                                                     historico=self,
                                                     centro='',
                                                     carrera='',
                                                     asignatura='',
                                                     anno=datetime.now().year.__str__(),
                                                     nota_ant='0',
                                                     nota_act='0',
                                                     creditos=0,
                                                     observaciones='')
            convalidacion.save()
        return self.recordacademico.convalidacioninscripcion_set.all()[0]

    def datos_homologacion(self):
        if not self.recordacademico.homologacioninscripcion_set.exists():
            homologacion = HomologacionInscripcion(record=self.recordacademico,
                                                   historico=self,
                                                   fecha=datetime.now().date(),
                                                   nota_ant=0,
                                                   creditos=0,
                                                   observaciones='')
            homologacion.save()
        return self.recordacademico.homologacioninscripcion_set.all()[0]

    def asignatura_malla(self):
        if self.existe_en_malla():
            return self.inscripcion.mi_malla().asignaturamalla_set.filter(asignatura=self.asignatura)[0]
        return None

    def es_nivelacion(self):
        asm = self.asignatura_malla()
        if asm:
            return asm.nivelmalla.id == 0
        return False

    def es_movilidad(self):
        if MateriaAsignada.objects.filter(materia=self.materiaregular, matricula__inscripcion=self.inscripcion, movilidad=True).exists():
            return True
        return False

    def save(self, *args, **kwargs):
        self.asignaturamalla = self.asignatura_malla()
        if not self.aprobada:
            self.creditos = 0
            self.horas = 0
            self.validacreditos = False
        if self.noaplica:
            self.aprobada = True
            self.validacreditos = False
            self.validapromedio = False
            self.creditos = 0
            self.horas = 0
        self.pendiente = False
        self.observaciones = null_to_text(self.observaciones)
        self.valoracioncalificacion = valoracion_calificacion(self.nota)
        super(HistoricoRecordAcademico, self).save(*args, **kwargs)







class TipoPerfilUsuario(ModeloBase):
    nombre = models.CharField(max_length=300, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s ' % (self.nombre)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoPerfilUsuario, self).save(*args, **kwargs)




class FacturasInstitucion(ModeloBase):
    fecha = models.DateField()
    numero = models.CharField(max_length=30)
    fechavencimiento = models.DateField()
    pagada = models.BooleanField(default=False)
    archivo = models.FileField(upload_to='facturasinstitucion/%Y/%m/%d', blank=True, null=True, verbose_name=u'Factura')

    def save(self, *args, **kwargs):
        self.numero = null_to_text(self.numero)
        super(FacturasInstitucion, self).save(*args, **kwargs)


class FacturasInstitucionNotificacion(ModeloBase):
    fecha = models.DateField()
    usuario = models.ForeignKey(User, verbose_name=u'Usuario', on_delete=models.CASCADE)


class Capcha(ModeloBase):
    numero = models.CharField(max_length=30)
    key = models.CharField(max_length=30)
    archivo = models.FileField(upload_to='capcha/', blank=True, null=True, verbose_name=u'Solicitudes')

    def save(self, *args, **kwargs):
        self.numero = null_to_text(self.numero, lower=True)
        super(Capcha, self).save(*args, **kwargs)



TIPO_REQUEST_CHOICES = (
    (1, u'GET'),
    (2, u'POST'),
)

class Api(ModeloBase):
    nombrecorto = models.CharField(default='', max_length=50, verbose_name=u'Nombre corto')
    descripcion = models.CharField(default='', max_length=200, verbose_name=u'Descripción')
    key = models.CharField(default='', max_length=50, verbose_name=u"Key")
    tipo = models.IntegerField(default=1, choices=TIPO_REQUEST_CHOICES)
    logicaapi = models.TextField(default='', blank=True, null=True, verbose_name=u'logica')
    activo = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.nombrecorto = null_to_text(self.nombrecorto, lower=True)
        self.descripcion = null_to_text(self.descripcion)
        self.key = null_to_text(self.key, transform=False)
        self.logicaapi = null_to_text(self.logicaapi, transform=False)
        super(Api, self).save(*args, **kwargs)




def expira_15_min():
    return datetime.now() + timedelta(minutes=15)


class APIKey(ModeloBase):
    key = models.CharField(max_length=400, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=expira_15_min)
    name = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = datetime.now() + timedelta(minutes=15)
        super().save(*args, **kwargs)


class RubroCodigos(ModeloBase):
    tiporubro = models.CharField(default='', max_length=10, verbose_name=u'Codigo')
    tipogrado = models.ForeignKey(NivelTitulacion, blank=True, null=True, on_delete=models.CASCADE)
    modalidad = models.ForeignKey(Modalidad, blank=True, null=True, on_delete=models.CASCADE)
    subnivel = models.CharField(default='', max_length=10, verbose_name=u'subnivel')
    codigo = models.CharField(default='', max_length=50, verbose_name=u'Codigo')
    nombre = models.CharField(default='', max_length=300, verbose_name=u'Nombre')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return u'%s' % (self.nombre)


class AreaNegocios(ModeloBase):
    tipogrado = models.ForeignKey(NivelTitulacion, blank=True, null=True, on_delete=models.CASCADE)
    modalidad = models.ForeignKey(Modalidad, blank=True, null=True, verbose_name=u'Modalidad', on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, blank=True, null=True, verbose_name=u'Carrera', on_delete=models.CASCADE)
    codigo = models.CharField(default='', max_length=50, verbose_name=u'Codigo')

    def __str__(self):
        return u'%s' % (self.nombre)


class CentroCostos(ModeloBase):
    coordinacion = models.ForeignKey(Coordinacion, blank=True, null=True, verbose_name=u'Coordinacion', on_delete=models.CASCADE)
    codigo = models.CharField(default='', max_length=50, verbose_name=u'Codigo')

    def __str__(self):
        return u'%s' % (self.nombre)

class DiferidoTarjeta(ModeloBase):
    banco = models.ForeignKey(Banco, verbose_name=u"banco", blank=True, null=True, on_delete=models.CASCADE)
    tipoemisortarjeta = models.ForeignKey(TipoEmisorTarjeta, blank=True, null=True, verbose_name=u"tipo emisor", on_delete=models.CASCADE)
    tipotarjetabanco = models.ForeignKey(TipoTarjetaBanco, blank=True, null=True, verbose_name=u"tipo emisor", on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    valordatafast = models.IntegerField(default=0, verbose_name=u'valor datafast')
    intereses = models.BooleanField(default=True, verbose_name=u'Con intereses')
    difiere = models.BooleanField(default=False, verbose_name=u'Difiere')
    activo = models.BooleanField(default=True)
    tipocredito = models.CharField(blank=True, null=True, max_length=2, verbose_name=u'Tipo credito')

    def __str__(self):
        return u'%s - %s' % (self.nombre, u'CON INTERESES' if self.intereses else u'SIN INTERESES')

    class Meta:
        verbose_name_plural = u" Pagos diferidos tarjetas"
        ordering = ['valordatafast']

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(DiferidoTarjeta, self).save(*args, **kwargs)


class ReciboCajaInstitucion(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion,  blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente,  blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    pago = models.ForeignKey(Pago, blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    motivo = models.TextField(default='', verbose_name=u'Motivo')
    fecha = models.DateField(verbose_name=u'Fecha')
    hora = models.TimeField(verbose_name=u'Hora')
    valorinicial = models.FloatField(default=0, verbose_name=u'Valor')
    saldo = models.FloatField(default=0, verbose_name=u'Saldo')
    sesioncaja = models.ForeignKey(SesionCaja, blank=True, null=True, verbose_name=u'Sesion de caja', on_delete=models.CASCADE)
    anticipado = models.BooleanField(default=False, verbose_name=u"Valido")

    def __str__(self):
        return u'Recibo caja: %s $%s de $%s - %s' % (self.inscripcion, self.saldo, self.valorinicial, self.fecha.strftime("%d-%m-%Y"))

    class Meta:
        verbose_name_plural = u"Recibos de caja institución"

    def esta_liquidado(self):
        return self.recibocajaliquidado_set.exists()

    def datos_liquidado(self):
        if self.esta_liquidado():
            return self.recibocajaliquidado_set.all()[0]
        return None

    def valor_restante(self):
        if not self.esta_liquidado():
            return null_to_numeric(self.valorinicial - null_to_numeric(self.pagorecibocajainstitucion_set.filter(valido=True).aggregate(valor=Sum('valor'))['valor'], 2), 2)
        return 0

    def actualiza_valor(self):
        pass

    def tiene_pagos(self):
        return self.pagorecibocajainstitucion_set.exists()

    def extra_delete(self):
        if self.pagorecibocajainstitucion_set.exists():
            return [False, False]
        return [True, False]

    def save(self, valor=None, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        self.valorinicial = null_to_numeric(self.valorinicial, 2)
        if self.id:
            self.saldo = self.valor_restante()
        else:
            self.saldo = self.valorinicial
        super(ReciboCajaInstitucion, self).save(*args, **kwargs)


class NotaCredito(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente,  blank=True, null=True, verbose_name=u'Cliente', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha')
    numero = models.CharField(default='', max_length=20, verbose_name=u"Numero")
    motivo = models.CharField(default='', max_length=200, verbose_name=u'Motivo')
    valorinicial = models.FloatField(default=0, verbose_name=u'Valor inicial')
    saldo = models.FloatField(default=0, verbose_name=u'Saldo')
    electronica = models.BooleanField(default=False)
    esbecaoayuda = models.BooleanField(default=False, verbose_name=u"Es beca o ayuda")
    periodo = models.CharField(default='', max_length=20, blank=True, null=True, verbose_name=u'Nombre Periodo')
    motivootros = models.CharField(default='', max_length=200, verbose_name=u'Motivo Otros')

    def __str__(self):
        return u'%s $%s de $%s - %s' % (self.numero, self.saldo, self.valorinicial, self.fecha.strftime("%d-%m-%Y"))

    class Meta:
        verbose_name_plural = u"Notas de crédito"
        ordering = ['-fecha', 'numero']

    def adeudado(self):
        return null_to_numeric(self.valorinicial - self.total_pagado(), 2)

    def total_pagado(self):
        return null_to_numeric(Pago.objects.filter(pagonotacredito__notacredito=self, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def enletras(self):
        return enletras(self.valorinicial)

    def tiene_pagos(self):
        return self.pagonotacredito_set.exists()

    def esta_liquidado(self):
        return self.notacreditoaliquidado_set.exists()

    def datos_liquidado(self):
        if self.esta_liquidado():
            return self.notacreditoaliquidado_set.all()[0]
        return None

    def valor_restante(self):
        if not self.esta_liquidado():
            return null_to_numeric(self.valorinicial - null_to_numeric(PagoNotaCredito.objects.filter(notacredito=self, valido=True).aggregate(valor=Sum('valor'))['valor'], 2), 2)
        return 0

    def actualiza_valor(self):
        self.saldo = self.valor_restante()
        self.save()

    def extra_delete(self):
        return [True, True]

    def save(self, *args, **kwargs):
        self.numero = null_to_text(self.numero)
        self.motivo = null_to_text(self.motivo)
        self.motivootros = null_to_text(self.motivootros)
        if self.id:
            self.saldo = self.valor_restante()
        super(NotaCredito, self).save(*args, **kwargs)


class NotaCreditoaLiquidado(ModeloBase):
    notacredito = models.ForeignKey(NotaCredito, verbose_name=u'Nota Credito', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha de aprobación')
    motivo = models.TextField(default='', verbose_name=u'Motivo')
    valor = models.FloatField(default=0, verbose_name=u'Valor liquidado')

    def __str__(self):
        return u'%s' % self.motivo

    class Meta:
        verbose_name_plural = u"Notas de crédito liquidadas"
        unique_together = ('notacredito',)

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        super(NotaCreditoaLiquidado, self).save(*args, **kwargs)



class PreciosPeriodo(ModeloBase):
    periodo = models.ForeignKey(Periodo, verbose_name=u'Periodo', on_delete=models.CASCADE)
    sede = models.ForeignKey(Sede, verbose_name=u'Sede', on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, blank=True, null=True, verbose_name=u'Carrera', on_delete=models.CASCADE)
    modalidad = models.ForeignKey(Modalidad, blank=True, null=True, verbose_name=u'Modalidad', on_delete=models.CASCADE)
    malla = models.ForeignKey(Malla, blank=True, null=True, verbose_name=u'Malla', on_delete=models.CASCADE)
    nivel = models.ForeignKey(NivelMalla, verbose_name=u'Nivel', on_delete=models.CASCADE)
    cortes = models.ForeignKey(Nivel, blank=True, null=True, verbose_name=u'Nivel Cortes', on_delete=models.CASCADE)
    preciomatricula = models.FloatField(default=0, verbose_name=u"Precio Matricula")
    precioarancel = models.FloatField(default=0, verbose_name=u"Precio Arancel")
    precioderechorotativo = models.FloatField(default=0, verbose_name=u"Precio Derecho Rotativo")
    fecha = models.DateField(verbose_name=u'Fecha  primer rubro')
    cuotas = models.IntegerField(default=1, verbose_name=u'Cuotas')
    meses = models.IntegerField(default=1, verbose_name=u'Meses')
    clonado = models.BooleanField(default=False, verbose_name=u'Clonado')
    aplicaextra = models.BooleanField(default=True, verbose_name=u'Aplica Extra Ordinaria')

    def __str__(self):
        return u'%s - %s - %s - %s - %s - %s - %s - %s - %s' % (self.periodo, self.sede, self.carrera, self.modalidad, self.nivel, self.preciomatricula, self.precioarancel, self.cuotas, self.meses)

    def nombre_corto(self):
        return u'%s - %s - %s - %s - %s' % (self.periodo.nombre, self.sede, self.carrera, self.modalidad, self.nivel)

    def generaextraordinaria(self):
        if self.aplicaextra:
            return True
        return False

    def detalle_materias(self):
        return self.detallepreciosmaterias_set.all()

    def generardetalle(self):
        for am in AsignaturaMalla.objects.filter(malla=self.malla, nivelmalla=self.nivel):
            if not self.detallepreciosmaterias_set.filter(asignaturamalla=am).exists():
                detalle = DetallePreciosMaterias(preciosperiodo=self,
                                                 asignaturamalla=am)
                detalle.save()

    def actualizar_detalle(self):
        pi = PreciosPeriodoModulosInscripcion.objects.filter(periodo=self.periodo, sede=self.sede, malla=self.malla)[0]
        if pi.tipocalculo == 1:
            totaldivision = null_to_numeric(AsignaturaMalla.objects.filter(detallepreciosmaterias__preciosperiodo=self).aggregate(valor=Sum("horas"))['valor'], 2)
        else:
            totaldivision = null_to_numeric(AsignaturaMalla.objects.filter(detallepreciosmaterias__preciosperiodo=self).aggregate(valor=Sum("creditos"))['valor'], 5)
        if self.precioarancel and totaldivision:
            valorunidad = null_to_numeric((self.precioarancel / totaldivision), 2)
            valoraplicar = self.precioarancel
            for detalle in self.detalle_materias():
                if pi.tipocalculo == 1:
                    detalle.valor = null_to_numeric((detalle.asignaturamalla.horas * valorunidad), 2)
                else:
                    detalle.valor = null_to_numeric((detalle.asignaturamalla.creditos * valorunidad), 2)
                detalle.save()
                valoraplicar = null_to_numeric((valoraplicar - detalle.valor), 2)
            if valoraplicar > 0 and detalle:
                detalle.valor = null_to_numeric((valoraplicar + detalle.valor), 2)
                detalle.save()
        else:
            for detalle in self.detalle_materias():
                detalle.valor=0
                detalle.save()

    def actualiza_valor(self):
        self.precioarancel = null_to_numeric(self.detallepreciosmaterias_set.aggregate(valor=Sum('valor'))['valor'], 2)
        self.save()

    def total(self):
        return null_to_numeric(self.precioarancel + self.preciomatricula, 2)

    def tiene_descuento(self):
        return self.descuentoformapago_set.exists()

    def descuento(self, formadepago):
        if self.descuentoformapago_set.filter(formadepago=formadepago).exists():
            return self.descuentoformapago_set.filter(precioperiodo=self, formadepago=formadepago)[0].porcentaje
        return 0

    def detalle_descuento(self, formadepago):
        if self.descuentoformapago_set.filter(formadepago=formadepago).exists():
            return self.descuentoformapago_set.filter(precioperiodo=self, formadepago=formadepago)[0]
        return None

class DescuentoFormaPago(ModeloBase):
    precioperiodo = models.ForeignKey(PreciosPeriodo, verbose_name=u'Precios del Periodo', on_delete=models.CASCADE)
    formadepago = models.ForeignKey(FormaDePago, verbose_name=u'Fromas de Pago', on_delete=models.CASCADE)
    fechainicio = models.DateTimeField(verbose_name=u'Desde', blank=True, null=True)
    fechafin = models.DateTimeField(verbose_name=u'Hasta', blank=True, null=True)
    porcentaje = models.IntegerField(default=0, verbose_name=u"Porcentaje")

    def __str__(self):
        return u'%s - %s - %s' % (self.precioperiodo, self.formadepago, self.porcentaje)

    class Meta:
        verbose_name_plural = u"Evaluador"
        unique_together = ('precioperiodo', 'formadepago')


class RetiroFinanciero(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion, on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE)
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha de retiro')
    motivo = models.TextField(default='', verbose_name=u'Motivo')
    valor = models.FloatField(default=0, verbose_name=u'Valor')
    responsable = models.ForeignKey(Persona, related_name="+", blank=True, null=True, on_delete=models.CASCADE)
    procesado = models.BooleanField(default=False)
    responsableproceso = models.ForeignKey(Persona, related_name="+", blank=True, null=True, on_delete=models.CASCADE)
    devuelto = models.BooleanField(default=False)

    def __str__(self):
        return u'%s' % self.inscripcion

    class Meta:
        verbose_name_plural = u"Retiros financieros"
        ordering = ['procesado', '-fecha']


class CronogramaEvaluacionModelo(ModeloBase):
    nivel = models.ForeignKey(Nivel, blank=True, null=True, verbose_name=u"Nivel", on_delete=models.CASCADE)
    modelo = models.ForeignKey(ModeloEvaluativo, verbose_name=u"Modelo", on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=200, verbose_name=u"Nombre")
    materias = models.ManyToManyField(Materia, verbose_name=u"Materias")

    def campos_editables(self):
        return self.fechaevaluacioncampomodelo_set.filter(campo__dependiente=False).order_by('campo__orden')

    def materia_seleccionada_cronograma(self, materia):
        return self.materias.filter(id=materia.id).exists()

    def __str__(self):
        return u'%s - %s' % (self.nombre, self.nivel)

    def verifica_campos_modelo(self):
        for campo in self.modelo.detallemodeloevaluativo_set.all():
            if not self.fechaevaluacioncampomodelo_set.filter(campo=campo).exists():
                fecha = FechaEvaluacionCampoModelo(cronograma=self,
                                                   campo=campo,
                                                   inicio=self.nivel.inicio,
                                                   fin=self.nivel.fin)
                fecha.save()

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(CronogramaEvaluacionModelo, self).save(*args, **kwargs)


class FechaEvaluacionCampoModelo(ModeloBase):
    cronograma = models.ForeignKey(CronogramaEvaluacionModelo, verbose_name=u"cronograma", on_delete=models.CASCADE)
    campo = models.ForeignKey(DetalleModeloEvaluativo, verbose_name=u"Campo", on_delete=models.CASCADE)
    inicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha Inicial')
    fin = models.DateField(blank=True, null=True, verbose_name=u'Fecha Final')

    def __str__(self):
        return u'%s - %s - %s - %s' % (self.cronograma, self.campo.nombre, self.inicio.strftime('%d-%m-%Y'), self.fin.strftime('%d-%m-%Y'))

    class Meta:
        unique_together = ('cronograma', 'campo',)


ESTADOS_SOLICITUD_COMPROBANTE = (
    (1, u'PENDIENTE'),
    (2, u'PROCESADA')
)

class Factura(ModeloBase):
    numero = models.CharField(default='', max_length=20, verbose_name=u"Numero")
    numeroreal = models.IntegerField(default=0, verbose_name=u"Numero")
    fecha = models.DateField(verbose_name=u"Fecha")
    valida = models.BooleanField(default=True, verbose_name=u"Valida")
    sesion = models.ForeignKey(SesionCaja, null=True, blank=True, verbose_name=u'Sesion de caja', on_delete=models.CASCADE)
    impresa = models.BooleanField(default=False, verbose_name=u"Impresa")
    pagos = models.ManyToManyField(Pago, blank=True, verbose_name=u"Pagos")
    identificacion = models.CharField(default='', max_length=20, verbose_name=u"Identificacion")
    tipo = models.IntegerField(choices=TiposIdentificacion.choices, default=1, verbose_name=u"Tipo de identificación")
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")
    direccion = models.TextField(default='', verbose_name=u"Dirección")
    telefono = models.CharField(default='', max_length=50, verbose_name=u"Teléfono")
    email = models.CharField(default='', blank=True, null=True, max_length=200, verbose_name=u"Correo electrónico")
    electronica = models.BooleanField(default=False, verbose_name=u"Electrónica")
    weburl = models.CharField(default='', null=True, blank=True, max_length=200, verbose_name=u"Web url")
    claveacceso = models.CharField(default='', null=True, blank=True, max_length=200, verbose_name=u"Clave de acceso")
    tipoambiente = models.IntegerField(default=0, verbose_name=u"Tipo ambiente")
    tipoemision = models.IntegerField(default=0, verbose_name=u"Tipo emision")
    basecero = models.FloatField(default=0, verbose_name=u"Base cero")
    baseiva = models.FloatField(default=0, verbose_name=u"Base iva")
    subtotal = models.FloatField(default=0, verbose_name=u"Subtotal")
    descuento = models.FloatField(default=0, verbose_name=u"Descuento")
    iva = models.FloatField(default=0, verbose_name=u"IVA")
    total = models.FloatField(default=0, verbose_name=u"Total")
    contabilizada = models.BooleanField(default=False, verbose_name=u"Contabilizada")
    firmada = models.BooleanField(default=False, verbose_name=u"Firmada")
    enviadasri = models.BooleanField(default=False, verbose_name=u"Enviada SRI")
    falloenviodasri = models.BooleanField(default=False, verbose_name=u"Fallo de Envio SRI")
    mensajeenvio = models.TextField(blank=True, null=True, verbose_name=u"Mensaje de Envio SRI")
    falloautorizacionsri = models.BooleanField(default=False, verbose_name=u"Fallo de Autorización SRI")
    mensajeautorizacion = models.TextField(blank=True, null=True, verbose_name=u"Mensaje de Autorización")
    autorizada = models.BooleanField(default=False, verbose_name=u"Autorizada")
    enviadacliente = models.BooleanField(default=False, verbose_name=u"Enviada por correo")
    xmlgenerado = models.BooleanField(default=False, verbose_name=u"XML Generado")
    xml = models.TextField(blank=True, null=True, verbose_name=u'XML')
    xmlfirmado = models.TextField(blank=True, null=True, verbose_name=u'XML Firmado')
    xmlarchivo = models.FileField(upload_to='comprobantes/facturas/', blank=True, null=True, verbose_name=u'XML Archivo')
    pdfarchivo = models.FileField(upload_to='comprobantes/facturas/', blank=True, null=True, verbose_name=u'XML Archivo')
    fechaautorizacion = models.DateTimeField(verbose_name=u"Fecha autorizacion", blank=True, null=True)
    autorizacion = models.TextField(default='', verbose_name=u'Autorizacion', blank=True, null=True)
    pagada = models.BooleanField(default=True, verbose_name=u"Pagada")
    estado = models.IntegerField(choices=ESTADOS_SOLICITUD_COMPROBANTE, default=1)
    codigocontable = models.IntegerField(default=0, verbose_name=u'Codigo contable')
    codigocontablenumero = models.IntegerField(default=0, verbose_name=u'Codigo contable numero')
    registrocontable = models.BooleanField(default=False, verbose_name=u'Registro en contable')

    def __str__(self):
        return u'%s' % self.numero

    class Meta:
        verbose_name_plural = u"Facturas"
        ordering = ['numero']
        unique_together = ('numero', 'electronica')

    def inscripcion(self):
        if self.pagos.exists():
            return self.pagos.all()[0].rubro.inscripcion
        return None

    def enletras(self):
        return enletras(self.total)

    def direccioncorta(self):
        return self.direccion[0:35]

    def direccioncorta2(self):
        return self.direccion[35:]

    def persona_cajero(self):
        if self.pagos.exists():
            return self.pagos.all()[0].sesion.caja.persona
        return None

    def establecimiento(self):
        if PuntoVenta.objects.filter(establecimiento=self.numero.split('-')[0], puntoventa=self.numero.split('-')[1]).exists():
            return PuntoVenta.objects.filter(establecimiento=self.numero.split('-')[0], puntoventa=self.numero.split('-')[1])[0]
        return None

    def sesioncaja(self):
        if self.pagos.exists():
            return self.pagos.all()[0].sesion
        return None

    def puede_reimprimirse(self):
        return self.fecha == datetime.now().date()

    def anulada(self):
        if FacturaCancelada.objects.filter(factura=self).exists():
            return FacturaCancelada.objects.filter(factura=self)[0]
        return None

    def descuentos(self):
        return null_to_numeric(self.pagos.aggregate(descuento=Sum('descuento'))['descuento'], 2)

    def en_fecha(self):
        return datetime.now().date() == self.fecha

    def estudiante(self):
        return self.pagos.all()[0].rubro.inscripcion.persona

    def tipo_identificacion(self):
        if self.tipo == 1:
            return "CEDULA"
        elif self.tipo == 2:
            return "RUC"
        else:
            return "PASAPORTE"

    def tipo_identificacion_facturaconelectronica(self):
        if self.tipo == 1:
            return "05"
        elif self.tipo == 2:
            return "04"
        else:
            return "06"

    def actualizarsubtotales(self):
        self.basecero = 0
        self.baseiva = 0
        valortotal = 0
        valoriva = 0
        for pago in self.pagos.all():
            if pago.iva > 0:
                self.baseiva += null_to_numeric(pago.valor - pago.iva, 2)
            else:
                self.basecero += (pago.valor + pago.descuento)
            valortotal += pago.valor
            valoriva += pago.iva
        self.basecero = null_to_numeric(self.basecero, 2)
        self.baseiva = null_to_numeric(self.baseiva, 2)
        self.descuento = self.descuentos()
        self.iva = null_to_numeric(valoriva, 2)
        self.subtotal = null_to_numeric(self.basecero + self.baseiva, 2)
        self.total = null_to_numeric(valortotal, 2)
        self.save()

    def cancelar(self, motivo):
        facturacancelada = FacturaCancelada(factura=self,
                                            motivo=motivo,
                                            fecha=datetime.now(),
                                            sesion=self.sesion)

        facturacancelada.save()
        for pago in self.pagos.all():
            pagocancelado = PagoCancelado(facturacancelada=facturacancelada,
                                          rubro=pago.rubro,
                                          iva=pago.iva,
                                          valor=pago.valor,
                                          efectivo=pago.efectivo,
                                          descuento=pago.descuento)
            pagocancelado.save()
            pago.valido = False
            pago.save()
            if pago.depositoinscripcion:
                depositoinscripcion = pago.depositoinscripcion
                depositoinscripcion.save()
            relacionado = pago.relacionado()
            if relacionado:
                relacionado.valido = False
                relacionado.save()
                relacionado.actualiza_valor()
                padrerelacionado = relacionado.padre()
                padrerelacionado.actualiza_valor()
            pago.rubro.save()
        for pagoexedente in self.facturapagoexedente_set.all():
            recibocaja = pagoexedente.recibocajainstitucion
            liquidado = ReciboCajaLiquidado(recibocaja=recibocaja,
                                            fecha=datetime.now().date(),
                                            motivo='ANULACION DE FACTURA',
                                            valor=recibocaja.saldo)
            liquidado.save()
            recibocaja.save()
        self.valida = False
        self.save()

    def total_efectivo(self):
        return null_to_numeric(self.pagos.filter(efectivo=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def total_cheque(self):
        return null_to_numeric(self.pagos.filter(pagocheque__isnull=False).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def detalle_pago_cheque(self):
        return PagoCheque.objects.filter(pagos__factura=self).distinct()

    def total_dineroelectronico(self):
        return 0

    def total_tarjetacredito(self):
        return null_to_numeric(self.pagos.filter(pagotarjeta__isnull=False).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def detalle_pago_trajetacredito(self):
        return PagoTarjeta.objects.filter(pagos__factura=self).distinct()

    def total_transferenciadeposito(self):
        return null_to_numeric(self.pagos.filter(pagotransferenciadeposito__isnull=False).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def detalle_pago_transferenciadeposito(self):
        return PagoTransferenciaDeposito.objects.filter(pagos__factura=self).distinct()

    def total_recibocaja(self):
        return null_to_numeric(self.pagos.filter(pagorecibocajainstitucion__isnull=False).distinct().aggregate(valor=Sum('valor'))['valor'], 2)

    def detalle_pago_recibocaja(self):
        return PagoReciboCajaInstitucion.objects.filter(pagos__factura=self).distinct()

    def verifica_credito(self):
        if self.rubronotadebito_set.exists():
            for rubro in self.rubronotadebito_set.all():
                if not rubro.rubro.cancelado:
                    return False
        return True

    def es_credito(self):
        return self.rubronotadebito_set.exists()

    def genera_clave_acceso_factura(self):
        hoy = self.fecha
        numero = int(self.numeroreal)
        return self.generar_clave_acceso(hoy, numero, '01')

    def generar_clave_acceso(self, fecha, numero, codigo):
        institucion = mi_institucion()
        hoy = fecha
        puntoventa = self.sesion.caja.puntodeventa
        codigoestablecimiento = puntoventa.establecimiento
        codigopuntoemision = puntoventa.puntoventa
        codigonumerico = str(Decimal('%02d%02d%04d' % (hoy.day, hoy.month, hoy.year)) + Decimal(institucion.ruc) + Decimal('%3s%3s%9s' % (codigoestablecimiento, codigopuntoemision, str(numero).zfill(9))))[:8]
        parcial = "%02d%02d%04d%2s%13s%1d%3s%3s%9s%8s%1d" % (hoy.day, hoy.month, hoy.year, codigo, institucion.ruc,
                                                             self.tipoambiente, codigoestablecimiento,
                                                             codigopuntoemision, str(numero).zfill(9),
                                                             codigonumerico, self.tipoemision)
        digitoverificador = self.generar_digito_verificador(parcial)
        return parcial + str(digitoverificador)

    def generar_digito_verificador(self, cadena):
        basemultiplicador = 7
        aux = [0] * len(cadena)
        multiplicador = 2
        total = 0
        for i in range(len(cadena) - 1, -1, -1):
            aux[i] = int(cadena[i]) * multiplicador
            multiplicador += 1
            if multiplicador > basemultiplicador:
                multiplicador = 2
            total += aux[i]
        if total == 0 or total == 1:
            verificador = 0
        else:
            verificador = 0 if (11 - (total % 11)) == 11 else 11 - (total % 11)
        if verificador == 10:
            verificador = 1
        return verificador

    def total_pagado(self):
        return null_to_numeric(Pago.objects.filter(rubro__rubronotadebito__factura=self, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)

    def extra_delete(self):
        return [False, False]

    def save(self, *args, **kwargs):
        self.numero = null_to_text(self.numero)
        self.identificacion = null_to_text(self.identificacion) if self.identificacion else '9999999999'
        self.direccion = null_to_text(self.direccion)
        self.nombre = null_to_text(self.nombre)
        self.telefono = null_to_text(self.telefono)
        self.weburl = null_to_text(self.weburl)
        self.claveacceso = null_to_text(self.claveacceso)
        super(Factura, self).save(*args, **kwargs)

class FacturaCancelada(ModeloBase):
    factura = models.ForeignKey(Factura, verbose_name=u'Factura', on_delete=models.CASCADE)
    motivo = models.CharField(default='', max_length=200, verbose_name=u'Motivo')
    fecha = models.DateField(verbose_name=u'Fecha')
    sesion = models.ForeignKey(SesionCaja, null=True, blank=True, verbose_name=u'Sesion de caja', on_delete=models.CASCADE)

    def __str__(self):
        return u'Factura cancelada No.%s %s %s' % (self.factura, self.fecha.strftime("%d-%m-%Y"), (self.sesion if self.sesion else ""))

    class Meta:
        verbose_name_plural = u"Facturas canceladas"
        unique_together = ('factura',)

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        super(FacturaCancelada, self).save(*args, **kwargs)

class ReciboPago(ModeloBase):
    numero = models.CharField(default='', max_length=20, verbose_name=u"Numero")
    numeroreal = models.IntegerField(default=0, verbose_name=u"Numero")
    fecha = models.DateField(verbose_name=u"Fecha")
    sesion = models.ForeignKey(SesionCaja, null=True, blank=True, verbose_name=u'Sesion de caja', on_delete=models.CASCADE)
    impresa = models.BooleanField(default=False, verbose_name=u"Impresa")
    pagos = models.ManyToManyField(Pago, blank=True, verbose_name=u"Pagos")
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u'Inscripcion', on_delete=models.CASCADE)
    basecero = models.FloatField(default=0, verbose_name=u"Base cero")
    baseiva = models.FloatField(default=0, verbose_name=u"Base iva")
    subtotal = models.FloatField(default=0, verbose_name=u"Subtotal")
    descuento = models.FloatField(default=0, verbose_name=u"Descuento")
    iva = models.FloatField(default=0, verbose_name=u"IVA")
    total = models.FloatField(default=0, verbose_name=u"Total")
    valido = models.BooleanField(default=True, verbose_name=u"Valido")
    estado = models.IntegerField(choices=ESTADOS_SOLICITUD_COMPROBANTE, default=1)
    codigocontable = models.IntegerField(default=0, verbose_name=u'Codigo contable')
    codigocontablenumero = models.IntegerField(default=0, verbose_name=u'Codigo contable numero')
    registrocontable = models.BooleanField(default=False, verbose_name=u'Registro en contable')

    def __str__(self):
        return u'Recibo No. %s' % self.numero

    class Meta:
        verbose_name_plural = u"Recibos de pago"
        ordering = ['numero']
        unique_together = ('numero',)

    def actualiza_total(self):
        return null_to_numeric(self.pagos.all().aggregate(valor=Sum('valor'))['valor'], 2)

    def descuentos(self):
        return null_to_numeric(self.pagos.aggregate(descuento=Sum('descuento'))['descuento'], 2)

    def actualizarsubtotales(self):
        self.basecero = 0
        self.baseiva = 0
        valortotal = 0
        valoriva = 0
        for pago in self.pagos.all():
            if pago.iva > 0:
                self.baseiva += null_to_numeric(pago.valor - pago.iva, 2)
            else:
                self.basecero += pago.valor
            valortotal += pago.valor
            valoriva += pago.iva
        self.basecero = null_to_numeric(self.basecero, 2)
        self.baseiva = null_to_numeric(self.baseiva, 2)
        self.descuento = self.descuentos()
        self.iva = null_to_numeric(valoriva, 2)
        self.subtotal = null_to_numeric(self.basecero + self.baseiva, 2)
        self.total = null_to_numeric(valortotal, 2)
        self.save()

    def cancelar(self, motivo):
        recibopagocancelado = ReciboPagoCancelado(recibopago=self,
                                                  motivo=motivo,
                                                  fecha=datetime.now(),
                                                  sesion=self.sesion)

        recibopagocancelado.save()
        facturas = []
        for pago in self.pagos.all():
            pagocancelado = PagoCancelado(recibopagocancelado=recibopagocancelado,
                                          rubro=pago.rubro,
                                          iva=pago.iva,
                                          valor=pago.valor,
                                          efectivo=pago.efectivo,
                                          descuento=pago.descuento)
            pagocancelado.save()
            pago.valido = False
            pago.save()
            if pago.depositoinscripcion:
                depositoinscripcion = pago.depositoinscripcion
                depositoinscripcion.save()
            relacionado = pago.relacionado()
            if relacionado:
                relacionado.valido = False
                relacionado.save()
                relacionado.actualiza_valor()
                padrerelacionado = relacionado.padre()
                padrerelacionado.actualiza_valor()
            pago.rubro.save()
            notadebito = pago.rubro.notadebito()
            if notadebito and notadebito.factura:
                facturas.append(notadebito.factura)
        for factura in facturas:
            factura.cancelada = factura.verifica_credito()
            factura.save()
        for pagoexedente in self.recibopagoexedente_set.all():
            recibocaja = pagoexedente.recibocajainstitucion
            liquidado = ReciboCajaLiquidado(recibocaja=recibocaja,
                                            fecha=datetime.now().date(),
                                            motivo='ANULACION DE FACTURA',
                                            valor=recibocaja.saldo)
            liquidado.save()
            recibocaja.save()
        self.valido = False
        self.save()

    def extra_delete(self):
        return [False, False]

    def save(self, *args, **kwargs):
        self.numero = null_to_text(self.numero)
        if self.id:
            self.total = self.actualiza_total()
        super(ReciboPago, self).save(*args, **kwargs)


class ReciboPagoCancelado(ModeloBase):
    recibopago = models.ForeignKey(ReciboPago, verbose_name=u'Factura', on_delete=models.CASCADE)
    motivo = models.CharField(default='', max_length=200, verbose_name=u'Motivo')
    fecha = models.DateField(verbose_name=u'Fecha')
    sesion = models.ForeignKey(SesionCaja, null=True, blank=True, verbose_name=u'Sesion de caja', on_delete=models.CASCADE)

    def __str__(self):
        return u'Recibo cancelado No.%s %s %s' % (self.recibopago, self.fecha.strftime("%d-%m-%Y"), (self.sesion if self.sesion else ""))

    class Meta:
        verbose_name_plural = u"Recibos de pago cancelados"
        unique_together = ('recibopago',)

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        super(ReciboPagoCancelado, self).save(*args, **kwargs)


class PagoCancelado(ModeloBase):
    rubro = models.ForeignKey(Rubro, verbose_name=u'Rubros', on_delete=models.CASCADE)
    facturacancelada = models.ForeignKey(FacturaCancelada, blank=True, null=True, verbose_name=u'Factura cancelada', on_delete=models.CASCADE)
    recibopagocancelado = models.ForeignKey(ReciboPagoCancelado, blank=True, null=True, verbose_name=u'Recibo de pago cancelado', on_delete=models.CASCADE)
    iva = models.FloatField(default=0, verbose_name=u'IVA')
    valor = models.FloatField(default=0, verbose_name=u'Valor')
    efectivo = models.BooleanField(default=True, verbose_name=u'Pago en efectivo')
    descuento = models.FloatField(default=0, verbose_name=u'Descuento')

    def __str__(self):
        return u'Pago $%s %s' % (str(self.valor), self.rubro)

    class Meta:
        verbose_name_plural = u"Pagos"

    def subtotal(self):
        return self.valor + self.descuento

    def totaldescuento(self):
        return self.descuento

    def save(self, *args, **kwargs):
        self.valor = null_to_numeric(self.valor, 2)
        self.iva = null_to_numeric(self.iva, 2)
        super(PagoCancelado, self).save(*args, **kwargs)


class ChequeProtestado(ModeloBase):
    cheque = models.ForeignKey(DatoCheque, verbose_name=u'Cheque', on_delete=models.CASCADE)
    motivo = models.TextField(default='', verbose_name=u'Motivo')
    fecha = models.DateField(verbose_name=u'Fecha')

    def __str__(self):
        return u'Cheque protestado No. %s - %s' % (self.cheque.numero, self.fecha.strftime("%d-%m-%Y"))

    class Meta:
        verbose_name_plural = u"Cheques protestados"
        unique_together = ('cheque',)

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        super(ChequeProtestado, self).save(*args, **kwargs)


class DescuentoRecargoRubro(ModeloBase):
    rubro = models.ForeignKey(Rubro, related_name='+', verbose_name=u'Rubro', on_delete=models.CASCADE)
    recargo = models.BooleanField(default=False, verbose_name=u'Es recargo')
    descuentoefectivo = models.BooleanField(default=False, verbose_name=u'Es efectivo')
    precio = models.FloatField(default=0, verbose_name=u'Valor inicial')
    porciento = models.IntegerField(default=0, verbose_name=u'% apliado')
    rubrorecargo = models.ForeignKey(Rubro, related_name='+', null=True, blank=True, verbose_name=u'Rubro generado', on_delete=models.CASCADE)
    motivo = models.TextField(default='', verbose_name=u'Motivo')
    valordescuento = models.FloatField(default=0, verbose_name=u'Valor descuento')
    responsable = models.ForeignKey(Persona, null=True, blank=True, verbose_name=u'Responsable', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha')
    facturaaplicada = models.ForeignKey(Factura, null=True, blank=True, verbose_name=u'Factua aplicada', on_delete=models.CASCADE)

    def __str__(self):
        if self.recargo:
            if self.porciento:
                return u'Recargo del %s a %s' % (self.porciento, self.precio)
            return u'Recargo'
        else:
            return u'Descuento del %s a %s' % (self.porciento.__str__() + "%", self.precio)

    def montodescuento(self):
        return null_to_numeric((self.precio * self.porciento) / 100.0, 2)

    class Meta:
        verbose_name_plural = u"Descuentos y recargos a rubros"
        unique_together = ('rubro',)

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        super(DescuentoRecargoRubro, self).save(*args, **kwargs)


class NotaCreditoImportadas(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion, blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    persona = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha')
    numero = models.CharField(default='', max_length=20, verbose_name=u"Numero")
    motivo = models.CharField(default='', max_length=200, verbose_name=u'Motivo')
    valor = models.FloatField(default=0, verbose_name=u'Valor')
    procesada = models.BooleanField(default=False, verbose_name=u"Procesada")
    electronica = models.BooleanField(default=False, verbose_name=u"Electronica")
    consaldo = models.BooleanField(default=False, verbose_name=u"Electronica")
    esbecaoayuda = models.BooleanField(default=False, verbose_name=u"Es beca o ayuda")
    periodo = models.CharField(default='', max_length=20, blank=True, null=True, verbose_name=u'Nombre Periodo')
    motivootros = models.CharField(default='', max_length=200, verbose_name=u'Motivo Otros')

    def __str__(self):
        return u'%s' % self.numero

    class Meta:
        ordering = ['numero']
        unique_together = ('numero',)
        verbose_name_plural = u"Notas de créditos importadas"

    def save(self, *args, **kwargs):
        self.numero = null_to_text(self.numero)
        self.motivo = null_to_text(self.motivo)
        self.motivootros = null_to_text(self.motivootros)
        super(NotaCreditoImportadas, self).save(*args, **kwargs)


class ReciboCajaLiquidado(ModeloBase):
    recibocaja = models.ForeignKey(ReciboCajaInstitucion, verbose_name=u'Recibo Caja Institucion', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha de aprobación')
    motivo = models.TextField(default='', verbose_name=u'Motivo')
    valor = models.FloatField(default=0, verbose_name=u'Valor liquidado')

    def __str__(self):
        return u'%s' % self.motivo

    class Meta:
        verbose_name_plural = u"Recibo caja liquidados"
        unique_together = ('recibocaja',)

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        super(ReciboCajaLiquidado, self).save(*args, **kwargs)


class PagoReciboCajaInstitucion(ModeloBase):
    recibocaja = models.ForeignKey(ReciboCajaInstitucion, verbose_name=u'Recibo de caja', on_delete=models.CASCADE)
    valor = models.FloatField(default=0, verbose_name=u'Valor')
    fecha = models.DateField(verbose_name=u'Fecha')
    pagos = models.ManyToManyField(Pago, verbose_name=u'Pagos')
    valido = models.BooleanField(default=True, verbose_name=u"Valido")

    def __str__(self):
        return u'Pago Recibo Caja Institución $%s' % str(self.valor)

    class Meta:
        verbose_name_plural = u"Pagos con recibos cajas"

    def padre(self):
        return self.recibocaja

    def actualiza_valor(self):
        self.valor = null_to_numeric(self.pagos.filter(valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
        self.save()

    def extra_delete(self):
        return [False, True]


class PagosCursoEscuelaComplementaria(ModeloBase):
    curso = models.ForeignKey(CursoEscuelaComplementaria, verbose_name=u'Curso Complementario', on_delete=models.CASCADE)
    tipo = models.IntegerField(choices=TIPOS_PAGO_NIVEL, default=0, verbose_name=u"Tipo de pagos")
    valor = models.FloatField(default=0, verbose_name=u'Valor')
    fecha = models.DateField(verbose_name=u'Fecha')

    def __str__(self):
        return u'%s %s $%s %s' % (self.curso, self.tipo, str(self.valor), self.fecha.strftime("%d-%m-%Y"))

    class Meta:
        verbose_name_plural = u"Pagos de cursos"
        ordering = ['tipo']
        unique_together = ('curso', 'tipo',)

    def nombre(self):
        return [y for x, y in TIPOS_PAGO_NIVEL if x == self.tipo][0]

class RetiroMatriculaCursoEscuelaComplementaria(ModeloBase):
    fecha = models.DateField(verbose_name=u'Fecha')
    matricula = models.ForeignKey(MatriculaCursoEscuelaComplementaria, verbose_name=u'Matricula', on_delete=models.CASCADE)
    observacion = models.TextField(default='', verbose_name=u"Observacion")

    def __str__(self):
        return u'Retirado: %s' % self.matricula

    def save(self, *args, **kwargs):
        self.observacion = null_to_text(self.observacion)
        super(RetiroMatriculaCursoEscuelaComplementaria, self).save(*args, **kwargs)



class PorcentajeDescuentoCursos(ModeloBase):
    curso = models.ForeignKey(CursoEscuelaComplementaria, null=True, blank=True, verbose_name=u"Curso", on_delete=models.CASCADE)
    descuento = models.IntegerField(choices=OPCIONES_DESCUENTO_CURSOS, default=1, verbose_name=u"Descuentos")
    porcentaje = models.FloatField(default=0, verbose_name=u"Porcentaje")

    def __str__(self):
        if self.descuento == 1:
            nombre = 'ESTUDIANTE'
        elif self.descuento == 2:
            nombre = 'EGRESADO'
        elif self.descuento == 3:
            nombre = 'ADMINISTRATIVO'
        elif self.descuento == 4:
            nombre = 'DOCENTE'
        elif self.descuento == 5:
            nombre = 'EXTERNO'
        elif self.descuento == 6:
            nombre = 'GRADUADO'
        return u'%s (- %s' % (nombre, Decimal('%02d' % self.porcentaje)) + "%)"

class TipoIntegracion(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Paralelos de materias"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def flexbox_repr(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoIntegracion, self).save(*args, **kwargs)

class NivelEstudiantesMatricula(ModeloBase):
    nivel = models.ForeignKey(Nivel, verbose_name=u'Nivel', on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, verbose_name=u'Carrera', on_delete=models.CASCADE)
    nivelmalla = models.ForeignKey(NivelMalla, blank=True, null=True, verbose_name=u'Niveles', on_delete=models.CASCADE)
    modalidad = models.ForeignKey(Modalidad, blank=True, null=True, verbose_name=u'Modalidad', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = u"Niveles estudiante matricula"
        unique_together = ('nivel', 'nivelmalla',)

    def __str__(self):
        return u'%s - %s' % (self.carrera, self.nivelmalla if self.nivelmalla else '')



class Area(ModeloBase):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class FlujoAprobacion(ModeloBase):
    nombre = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.nombre


class PasoFlujo(ModeloBase):
    flujo = models.ForeignKey(FlujoAprobacion, on_delete=models.CASCADE, related_name='pasos')
    area = models.ForeignKey(Area, on_delete=models.CASCADE)
    orden = models.PositiveIntegerField()
    usuarios = models.ManyToManyField(User, blank=True)


    def __str__(self):
        return f"{self.flujo.nombre} - Paso {self.orden} - {self.area.nombre}"

    class Meta:
        ordering = ['flujo', 'orden']
        unique_together = ('flujo', 'orden')


from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


ESTADOS_SOLICITUD = [
    (1, 'Pendiente'),     # Aún no inicia la aprobación.
    (2, 'En Proceso'),    # Se encuentra en alguna de las etapas intermedias.
    (3, 'Desbloqueo'),    # Se aprobó en la última etapa y se libera para edición.
    (4, 'Finalizado'),    # Edición finalizada y solicitud cerrada (flujo completado).
    (5, 'Rechazado'),     # Alguna etapa rechazó la solicitud.
]

MOTIVOS_CAMBIO_DISTRIBUTIVO = [
    (1, 'Renuncia de docentes'),
    (2, 'No apertura de cursos'),
    (3, 'Registro de docentes para prácticas'),
    (4, 'Asignación de docentes o nuevo ingreso'),
]

class SolicitudCambio(ModeloBase):
    flujo = models.ForeignKey(FlujoAprobacion, on_delete=models.CASCADE, related_name='solicitudes')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    objeto = GenericForeignKey('content_type', 'object_id')
    etapa_actual = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    estado = models.IntegerField(choices=ESTADOS_SOLICITUD, default=1)
    usuario_solicitante = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='solicitudes_cambio')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    descripcion_cambio = models.TextField(blank=True, default="", verbose_name="Motivo o Detalle del Cambio")
    motivo_cambio = models.IntegerField(choices=MOTIVOS_CAMBIO_DISTRIBUTIVO, null=True, blank=True, verbose_name="Motivo del Cambio")
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    usuario_resuelve = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resoluciones_cambio')
    comentarios_resolucion = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Solicitud {self.pk} - {self.objeto} [{self.estado}]"

    def persona_solicitante(self):
        return Persona.objects.filter(usuario=self.usuario_solicitante).first()

    def solicitud_botones(self):
        return self.estado in [1, 2]

    def puede_finalizarse(self):
        if self.estado != 3:
            return False

        ultimo_evento = self.historial.filter(accion__in=["Aprobacion"]).order_by('-fecha').first()
        if not ultimo_evento:
            return False

        tiempo_transcurrido = timezone.now() - ultimo_evento.fecha
        return timezone.now() >= (ultimo_evento.fecha + timedelta(hours=24))

    def aprobar_etapa(self, usuario, comentarios=""):
        self.usuario_resuelve = usuario
        self.comentarios_resolucion = comentarios
        self.fecha_resolucion = timezone.now()
        siguiente_area = self.obtener_siguiente_area()
        if siguiente_area:
            self.etapa_actual = siguiente_area
            self.estado = 2
            self.fecha_resolucion = None
            self.usuario_resuelve = None
            self.comentarios_resolucion = ""
        else:
            self.estado = 3
            self.desbloquear_objeto()

        HistorialSolicitudDistributivo.objects.create(
            solicitud=self,
            accion="Aprobacion",
            usuario=usuario,
            comentarios=comentarios
        )
        paso_siguiente = PasoFlujo.objects.filter(flujo=self.flujo, area=siguiente_area).first()
        if paso_siguiente:
            for usuario in paso_siguiente.usuarios.all():
                destino = usuario.persona_set.first()
                send_mail(subject='Aprobacion del distirbutivo.',
                          html_template='emails/notificacionflujodistributivo.html',
                          data={'d': self, 'destino': destino},
                          recipient_list=[destino])
        self.save()

    def rechazar_etapa(self, usuario, comentarios=""):
        self.usuario_resuelve = usuario
        self.comentarios_resolucion = comentarios
        self.fecha_resolucion = timezone.now()
        self.estado = 5
        self.save()

        HistorialSolicitudDistributivo.objects.create(
            solicitud=self,
            accion="Rechazo",
            usuario=usuario,
            comentarios=comentarios
        )
        destino = Persona.objects.filter(usuario=self.usuario_solicitante).first()
        send_mail(subject='Rechazo de la solicitud.',
                  html_template='emails/rechazosolicituddistributivo.html',
                  data={'d': self, 'solicitud': self, 'destino': destino},
                  recipient_list=[destino])

    def obtener_siguiente_area(self):
        try:
            paso_actual = PasoFlujo.objects.get(flujo=self.flujo, area=self.etapa_actual)
            orden_siguiente = paso_actual.orden + 1
            paso_siguiente = PasoFlujo.objects.filter(flujo=self.flujo, orden=orden_siguiente).first()
            if paso_siguiente:
                return paso_siguiente.area
        except PasoFlujo.DoesNotExist:
            pass
        return None

    def desbloquear_objeto(self):
        if self.objeto and hasattr(self.objeto, 'bloqueado'):
            self.objeto.bloqueado = False
            self.objeto.save()
            persona = Persona.objects.filter(usuario__username='administrador').first()
            destino = Persona.objects.filter(usuario=self.usuario_solicitante).first()
            send_mail(subject='Apertura del distributivo.',
                      html_template='emails/notificacionaperturadistributivo.html',
                      data={'d': self, 'solicitud': self, 'destino': destino},
                      recipient_list=[destino])

    def finalizar_edicion(self, usuario, comentarios=""):
        if self.estado == 3:
            # Rebloquear
            if self.objeto and hasattr(self.objeto, 'bloqueado'):
                self.objeto.bloqueado = True
                self.objeto.save()

            self.estado = 4
            self.usuario_resuelve = usuario
            self.fecha_resolucion = timezone.now()
            self.comentarios_resolucion = comentarios
            self.save()

            HistorialSolicitudDistributivo.objects.create(
                solicitud=self,
                accion="Finalización",
                usuario=usuario,
                comentarios=comentarios
            )


    def save(self, *args, **kwargs):
        es_creacion = self._state.adding  # ✅ detecta si es creación
        self.descripcion_cambio = null_to_text(self.descripcion_cambio)
        super(SolicitudCambio, self).save(*args, **kwargs)

        if es_creacion:
            primer_paso = self.flujo.pasos.order_by('orden').first()
            for usuario in primer_paso.usuarios.all():
                destino = usuario.persona_set.first()
                persona = Persona.objects.filter(usuario=self.usuario_solicitante).first()
                send_mail(
                    subject='Apertura del distributivo.',
                    html_template='emails/notificacionaprimerflujodistributivo.html',
                    data={'d': self, 'solicitud': self, 'persona': persona, 'destino': destino},
                    recipient_list=[destino]
                )

class HistorialSolicitudDistributivo(ModeloBase):
    solicitud = models.ForeignKey(SolicitudCambio, on_delete=models.CASCADE, related_name='historial')
    accion = models.CharField(max_length=50)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    comentarios = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.solicitud.id} - {self.accion} por {self.usuario} el {self.fecha}"


class CriterioDocencia(ModeloBase):
    nombre = models.CharField(default='', max_length=300, verbose_name=u"Nombre")
    dedicacion = models.ForeignKey(TiempoDedicacionDocente, blank=True, null=True, verbose_name=u"Dedicación docente", on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Criterios de docencia"
        ordering = ['nombre']
        unique_together = ('nombre', 'dedicacion',)

    def criterios_periodo(self, periodo):
        return self.criteriodocenciaperiodo_set.filter(periodo=periodo)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(CriterioDocencia, self).save(*args, **kwargs)


class CriterioInvestigacion(ModeloBase):
    nombre = models.CharField(default='', max_length=300, verbose_name=u"Nombre")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Criterios de investigación"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def criterios_periodo(self, periodo):
        return self.criterioinvestigacionperiodo_set.filter(periodo=periodo)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(CriterioInvestigacion, self).save(*args, **kwargs)


class CriterioGestion(ModeloBase):
    nombre = models.CharField(default='', max_length=300, verbose_name=u"Nombre")

    def __str__(self):
        return u'%s' % self.nombre

    def criterios_periodo(self, periodo):
        return self.criteriogestionperiodo_set.filter(periodo=periodo)

    class Meta:
        verbose_name_plural = u"Criterios de gestión"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(CriterioGestion, self).save(*args, **kwargs)


class CriterioVinculacion(ModeloBase):
    nombre = models.CharField(default='', max_length=300, verbose_name=u"Nombre")

    def __str__(self):
        return u'%s' % self.nombre

    def criterios_periodo(self, periodo):
        return self.criteriovinculacionperiodo_set.filter(periodo=periodo)

    class Meta:
        verbose_name_plural = u"Criterios de vinculación"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(CriterioVinculacion, self).save(*args, **kwargs)


class CriterioDocenciaPeriodo(ModeloBase):
    criterio = models.ForeignKey(CriterioDocencia, verbose_name=u'Criterio', on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, verbose_name=u'Periodo', on_delete=models.CASCADE)
    minimo = models.FloatField(default=0, verbose_name=u'Mínimo')
    maximo = models.FloatField(default=0, verbose_name=u'Máximo')
    estado = models.BooleanField(default=True, verbose_name=u"Estado")
    logicamodelo = models.TextField(default='', max_length=200, verbose_name=u'logica')

    def __str__(self):
        return u'%s' % self.criterio

    class Meta:
        verbose_name_plural = u"Criterios de docencia periodo"
        unique_together = ('criterio', 'periodo',)

    def rango_horas(self):
        return range(int(self.minimo), int(self.maximo) + 1)

    def es_automatico(self):
        return self.criterio.id in [CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID, CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID, CRITERIO_HORAS_CLASE_PARCIAL_ID, CRITERIO_HORAS_CLASE_TECNICO_DOCENTE_ID, CRITERIO_PRACTICAS_TIEMPO_COMPLETO_ID, CRITERIO_PRACTICAS_MEDIO_TIEMPO_ID, CRITERIO_PRACTICAS_PARCIAL_ID, CRITERIO_PRACTICAS_TECNICO_DOCENTE_ID]

    def tiene_rubrica(self):
        return self.rubricacriteriodocencia_set.exists()

    def usada_en_docente(self):
        return self.detalledistributivo_set.exists()

class CriterioInvestigacionPeriodo(ModeloBase):
    criterio = models.ForeignKey(CriterioInvestigacion, verbose_name=u'Criterio', on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, verbose_name=u'Periodo', on_delete=models.CASCADE)
    minimo = models.FloatField(default=0, verbose_name=u'Mínimo')
    maximo = models.FloatField(default=0, verbose_name=u'Máximo')
    estado = models.BooleanField(default=True, verbose_name=u"Estado")

    def __str__(self):
        return u'%s' % self.criterio

    class Meta:
        verbose_name_plural = u"Criterios de investigación periodo"
        unique_together = ('criterio', 'periodo',)

    def rango_horas(self):
        return range(int(self.minimo), int(self.maximo) + 1)

    def tiene_rubrica(self):
        return self.rubricacriterioinvestigacion_set.exists()

    def usada_en_docente(self):
        return self.detalledistributivo_set.exists()


class CriterioGestionPeriodo(ModeloBase):
    criterio = models.ForeignKey(CriterioGestion, verbose_name=u'Criterio', on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, verbose_name=u'Periodo', on_delete=models.CASCADE)
    minimo = models.FloatField(default=0, verbose_name=u'Mínimo')
    maximo = models.FloatField(default=0, verbose_name=u'Máximo')
    estado = models.BooleanField(default=True, verbose_name=u"Estado")

    def __str__(self):
        return u'%s' % self.criterio

    class Meta:
        verbose_name_plural = u"Criterios de gestión periodo"
        unique_together = ('criterio', 'periodo',)

    def rango_horas(self):
        return range(int(self.minimo), int(self.maximo) + 1)

    def tiene_rubrica(self):
        return self.rubricacriteriogestion_set.exists()

    def usada_en_docente(self):
        return self.detalledistributivo_set.exists()


class CriterioVinculacionPeriodo(ModeloBase):
    criterio = models.ForeignKey(CriterioVinculacion, verbose_name=u'Criterio', on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, verbose_name=u'Periodo', on_delete=models.CASCADE)
    minimo = models.FloatField(default=0, verbose_name=u'Mínimo')
    maximo = models.FloatField(default=0, verbose_name=u'Máximo')
    estado = models.BooleanField(default=True, verbose_name=u"Estado")

    def __str__(self):
        return u'%s' % self.criterio

    class Meta:
        verbose_name_plural = u"Criterios de gestión periodo"
        unique_together = ('criterio', 'periodo',)

    def rango_horas(self):
        return range(int(self.minimo), int(self.maximo) + 1)

    def tiene_rubrica(self):
        return self.rubricacriteriovinculacion_set.exists()

    def usada_en_docente(self):
        return self.detalledistributivo_set.exists()

class NivelEscalafonDocente(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u" Niveles de escalafón docente"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(NivelEscalafonDocente, self).save(*args, **kwargs)

class Profesor(ModeloBase):
    persona = models.ForeignKey(Persona, verbose_name=u"Persona", on_delete=models.CASCADE)
    fechainiciodocente = models.DateField(verbose_name=u'Fecha inicio actividades como docente')
    dedicacion = models.ForeignKey(TiempoDedicacionDocente, verbose_name=u"Dedicación", on_delete=models.CASCADE)
    coordinacion = models.ForeignKey(Coordinacion, null=True, blank=True, verbose_name=u"Coordinación", on_delete=models.CASCADE)
    activo = models.BooleanField(default=True, verbose_name=u"Activo")
    objetivodocente = models.TextField(verbose_name=u"Objetivo como docente", blank=True, null=True)
    descripcionprof = models.TextField(verbose_name=u"Descripción como profesional", blank=True, null=True)
    salario = models.FloatField(default=0, verbose_name=u'Salario')
    dependenciauti = models.BooleanField(default=False, verbose_name=u"Relación Dependencia UTI")
    justificar = models.BooleanField(default=False, verbose_name=u"Justificacion")
    orcid = models.CharField(default='', max_length=2000, verbose_name=u'ORCID')
    perfilgs = models.CharField(default='', max_length=2000, verbose_name=u'Perfil GS')
    perfilacademia = models.CharField(default='', max_length=2000, verbose_name=u'Perfil Academia')
    perfilscopus = models.CharField(default='', max_length=2000, verbose_name=u'Perfil Scopus')
    perfilmendeley = models.CharField(default='', max_length=2000, verbose_name=u'Perfil Mendeley')
    perfilresearchgate = models.CharField(default='', max_length=2000, verbose_name=u'Perfil Research Gate')
    indicehautor = models.CharField(default='', max_length=2000, verbose_name=u'Indice H Autor')
    documentoidentificacion = models.FileField(upload_to='documentosprofesor/%Y/%m/%d', blank=True, null=True, verbose_name=u'Escaneado de Cedula')
    validoth = models.BooleanField(default=False, verbose_name=u"Verificado TH")
    nivelescalafon = models.ForeignKey(NivelEscalafonDocente, null=True, blank=True, verbose_name=u"Nivel escalafon", on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name_plural = u"Profesores"
        ordering = ['persona__apellido1', 'persona__apellido2', 'persona__nombre1', 'persona__nombre2']
        unique_together = ('persona',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        if len(q.split(' ')) == 2:
            qq = q.split(' ')
            return eval(("Profesor.objects.filter(persona__apellido1__contains='%s', persona__apellido2__contains='%s')" % (qq[0], qq[1])) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))
        return eval(("Profesor.objects.filter(Q(persona__nombre1__contains='%s') | Q(persona__nombre2__contains='%s') | Q(persona__apellido1__contains='%s') | Q(persona__apellido2__contains='%s') | Q(persona__cedula__contains='%s') | Q(id=id_search('%s')))" % (q, q, q, q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return (self.persona.cedula if self.persona.cedula else self.persona.pasaporte) + " - " + self.persona.nombre_completo() + ' - ' + str(self.id)

    def datos_habilitacion(self):
        if self.habilitadoingresocalificaciones_set.exists():
            return self.habilitadoingresocalificaciones_set.all()[0]
        else:
            datos = HabilitadoIngresoCalificaciones(profesor=self,
                                                    fecha=datetime.now().date(),
                                                    clavegenerada='',
                                                    habilitado=False)
            datos.save()
            return datos

    def habilitado_ingreso_calificaciones(self):
        if UTILIZA_VALIDACION_CALIFICACIONES:
            datos = self.datos_habilitacion()
            if datos.habilitado and datos.fecha == datetime.now().date():
                return True
            return False
        return True

    def tabla_ponderacion(self, periodo):
        return self.distributivohoras(periodo).tablaponderacion

    def cantidad_horas_criterio_docencia(self, periodo):
        return self.distributivohoras(periodo).horasdocencia

    def ponderacion_horas_docencia(self, periodo):
        return null_to_numeric(self.cantidad_horas_criterio_docencia(periodo) / 40.0, 2)

    def cantidad_horas_criterio_investigacion(self, periodo):
        return self.distributivohoras(periodo).horasinvestigacion

    def ponderacion_horas_investigacion(self, periodo):
        return null_to_numeric(self.cantidad_horas_criterio_investigacion(periodo) / 40.0, 2)

    def cantidad_horas_criterio_gestion(self, periodo):
        return self.distributivohoras(periodo).horasgestion

    def ponderacion_horas_gestion(self, periodo):
        return null_to_numeric(self.cantidad_horas_criterio_gestion(periodo) / 40.0, 2)

    def cantidad_horas_criterio_vinculacion(self, periodo):
        return self.distributivohoras(periodo).horasvinculacion

    def ponderacion_horas_vinculacion(self, periodo):
        return null_to_numeric(self.cantidad_horas_criterio_vinculacion(periodo) / 40.0, 2)

    def cantidad_criterios_docencia(self, periodo):
        return self.distributivohoras(periodo).detalledistributivo_set.filter(criteriodocenciaperiodo__isnull=False).count()

    def cantidad_criterios_investigacion(self, periodo):
        return self.distributivohoras(periodo).detalledistributivo_set.filter(criterioinvestigacionperiodo__isnull=False).count()

    def cantidad_criterios_gestion(self, periodo):
        return self.distributivohoras(periodo).detalledistributivo_set.filter(criteriogestionperiodo__isnull=False).count()

    def cantidad_criterios_vinculacion(self, periodo):
        return self.distributivohoras(periodo).detalledistributivo_set.filter(criteriovinculacionperiodo__isnull=False).count()

    def cantidad_total_horas_criterios(self, periodo):
        return self.distributivohoras(periodo).total_horas()

    def cantidad_proyectogrado_activos(self):
        return TutorPreproyecto.objects.filter(profesor=self, preproyecto__proyectogrado__estado__in=[1, 4], activo=True).count()

    def tutor_proyectogrado_activos(self):
        return TutorPreproyecto.objects.filter(profesor=self, preproyecto__proyectogrado__estado__in=[1, 4], activo=True)

    def necesita_evaluarse(self, periodo):
        return self.necesita_evaluarse_regular(periodo)

    def necesita_evaluarse_regular(self, periodo):
        return self.cantidad_materias_periodo(periodo) > 0

    def autoevaluado_periodo_acreditacion(self, periodo,  sede, carrera, modalidad):
        return RespuestaEvaluacionAcreditacion.objects.filter(tipoinstrumento=2, proceso__periodo=periodo, profesor=self, evaluador=None, sede=sede, carrera=carrera, modalidad=modalidad).exists()

    def dato_autoevaluado_periodo_acreditacion(self, periodo, sede, carrera, modalidad):
        if self.autoevaluado_periodo_acreditacion(periodo,  sede, carrera, modalidad):
            return RespuestaEvaluacionAcreditacion.objects.filter(tipoinstrumento=2, proceso__periodo=periodo, profesor=self, evaluador=None, sede=sede, carrera=carrera, modalidad=modalidad)[0]
        return None

    def mis_coordinadores(self, periodo):
        return Persona.objects.filter(coordinadorcarrera__carrera__nivel__materia__profesormateria__profesor=self, coordinadorcarrera__carrera__nivel__periodo=periodo, coordinadorcarrera__periodo=periodo).distinct()

    def cantidad_coordinadores(self, periodo):
        return self.mis_coordinadores(periodo).count()

    def cantidad_materias_periodo(self, periodo):
        return ProfesorMateria.objects.filter(profesor=self, principal=True, materia__nivel__periodo=periodo).count()

    def cantidad_materias_periodo_estadisticas(self, periodo):
        return ProfesorMateria.objects.filter(profesor=self, principal=True, materia__nivel__periodo=periodo, horassemanales__gt=0).count()

    def cantidad_materias_planificadas_periodo(self, periodo):
        return ProfesorMateria.objects.filter(profesor=self, materia__nivel__periodo=periodo, principal=True, materia__planificacionmateria__aprobado=True).count()

    def cantidad_materias_planificadas_periodo_estadisticas(self, periodo):
        return ProfesorMateria.objects.filter(profesor=self, materia__nivel__periodo=periodo, principal=True, materia__planificacionmateria__aprobado=True, horassemanales__gt=0).count()

    def cantidad_materias_sinplanificadas_periodo(self, periodo):
        return self.cantidad_materias_periodo(periodo) - self.cantidad_materias_planificadas_periodo(periodo)

    def cantidad_materias_sinplanificadas_periodo_estadisticas(self, periodo):
        return self.cantidad_materias_periodo_estadisticas(periodo) - self.cantidad_materias_planificadas_periodo_estadisticas(periodo)

    def porciento_cumplimiento_materias_periodo(self, periodo):
        if self.cantidad_materias_periodo(periodo):
            return null_to_numeric((self.cantidad_materias_planificadas_periodo(periodo) * 100.0) / self.cantidad_materias_periodo(periodo), 2)
        return 0

    def porciento_cumplimiento_materias_periodo_estadisticas(self, periodo):
        if self.cantidad_materias_periodo(periodo):
            return null_to_numeric((self.cantidad_materias_planificadas_periodo_estadisticas(periodo) * 100.0) / self.cantidad_materias_periodo_estadisticas(periodo), 2)
        return 0

    def mis_materias(self, periodo):
        return ProfesorMateria.objects.filter(profesor=self, materia__nivel__periodo=periodo)

    def mis_materiaspracticas(self, periodo):
        return ProfesorMateriaPracticas.objects.filter(profesor=self, grupo__materia__nivel__periodo=periodo)

    def mis_coordinaciones_materias(self, periodo):
        return Coordinacion.objects.filter(nivellibrecoordinacion__nivel__materia__profesormateria__profesor=self, nivellibrecoordinacion__nivel__periodo=periodo).distinct()

    def esta_evaluado_por_alumno_materia_acreditacion(self, persona, materia):
        return self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, materia=materia, evaluador=persona).exists()

    def materias_imparte(self):
        return Materia.objects.filter(nivel__fin__gte=datetime.now().date(), profesormateria__profesor=self).distinct()

    def materias_imparte_activas(self):
        return Materia.objects.filter(cerrado=False, profesormateria__profesor=self).distinct()

    def materias_imparte_periodo(self, periodo):
        return Materia.objects.filter(nivel__periodo=periodo, profesormateria__profesor=self).distinct()

    def asignaturas_imparte_periodo(self, periodo):
        return Asignatura.objects.filter(materia__nivel__periodo=periodo, materia__profesormateria__profesor=self).distinct()

    def carreras_imparte_periodo(self, periodo):
        return Carrera.objects.filter(Q(malla__asignaturamalla__materia__nivel__periodo=periodo, malla__asignaturamalla__materia__profesormateria__profesor=self) ).distinct()

    def me_imparte(self, matricula):
        return MateriaAsignada.objects.filter(materia__profesormateria__profesor=self, matricula=matricula)

    def tiene_lecciongrupo(self, inicio, fin):
        return LeccionGrupo.objects.filter(profesor=self, fecha__gte=inicio, fecha__lte=fin).exists()

    def cantidad_lecciones(self, periodo):
        return LeccionGrupo.objects.filter(profesor=self, lecciones__clase__materia__nivel__periodo=periodo).distinct().count()

    def actualizartiempodedicacion(self, cantidadmaterias):
        tiempo = TiempoDedicacionDocente.objects.filter(materias__lte=cantidadmaterias).order_by('-materias')[0]
        self.dedicacion = tiempo
        self.save()
        if self.nivelcategoria:
            if RangoCategoria.objects.filter(nombre=self.nivelcategoria.nombre, dedicacion=self.dedicacion, nivel=self.persona.titulacionmaxima().niveltitulacion).exists():
                nuevorango = RangoCategoria.objects.filter(nombre=self.nivelcategoria.nombre, dedicacion=self.dedicacion, nivel=self.persona.titulacionmaxima().niveltitulacion)[0]
                self.nivelcategoria = nuevorango
            else:
                self.nivelcategoria = None
            self.save()

    def distributivohoras(self, periodo):
        try:
            if self.profesordistributivohoras_set.filter(periodo=periodo):
                return self.profesordistributivohoras_set.filter(periodo=periodo)[0]
            else:
                tablaponderacion = None
                if TablaPonderacionInstrumento.objects.exists():
                    tablaponderacion = TablaPonderacionInstrumento.objects.all()[0]
                horas = ProfesorDistributivoHoras(profesor=self,
                                                  periodo=periodo,
                                                  coordinacion=self.coordinacion,
                                                  dedicacion=self.dedicacion,
                                                  tablaponderacion=tablaponderacion)
                horas.save()
                return horas
        except Exception as ex:
            pass

    def distributivohorasdocente(self, periodo):
        if self.profesordistributivohoras_set.filter(periodo=periodo, aprobadofinanciero=True, aprobadodecano=True):
            return self.profesordistributivohoras_set.filter(periodo=periodo, aprobadofinanciero=True, aprobadodecano=True)[0]
        else:
            tablaponderacion = None
            if TablaPonderacionInstrumento.objects.exists():
                tablaponderacion = TablaPonderacionInstrumento.objects.all()[0]
            if ProfesorDistributivoHoras.objects.filter(profesor=self, periodo=periodo).exists():
                horas = ProfesorDistributivoHoras.objects.filter(profesor=self, periodo=periodo)[0]
            else:
                horas = ProfesorDistributivoHoras(profesor=self,
                                                  periodo=periodo,
                                                  coordinacion=self.coordinacion,
                                                  dedicacion=self.dedicacion,
                                                  tablaponderacion=tablaponderacion)
                horas.save()
            return horas

    def total_horas_periodo(self, periodo):
        return null_to_numeric(ProfesorMateria.objects.filter(profesor=self, materia__nivel__periodo=periodo, sesuma=True).distinct().aggregate(valor=Sum('horassemanales'))['valor'], 1)

    def total_horas_periodo_practicas(self, periodo):
        return null_to_numeric(ProfesorMateriaPracticas.objects.filter(profesor=self, grupo__materia__nivel__periodo=periodo, sesuma=True).distinct().aggregate(valor=Sum('horassemanales'))['valor'], 1)


    def esta_evaluado_por_alumno_materia(self, persona, materia):
        return self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, materia=materia, evaluador=persona).exists()

    def esta_evaluado_por_alumno_materia_docente(self, persona, materia):
        return self.respuestaevaluaciondocente_set.filter(tipoinstrumento=1, materia=materia, evaluador=persona).exists()

    def esta_autoevaluado_por_carrera_sede_modaldiad(self, persona, materia):
        return self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, materia=materia, evaluador=persona).exists()

    def clases_horario(self, dia, turno, periodo):
        return Clase.objects.filter(dia=dia, activo=True, turno=turno, materia__nivel__periodo=periodo, materia__profesormateria__profesor=self)

    def tiene_que_evaluarse(self, periodo):
        distributivo = self.distributivohoras(periodo)
        criteriosdocencia = CriterioDocenciaPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        criteriosinvestigacion = CriterioInvestigacionPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        criteriosgestion = CriterioGestionPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        return Rubrica.objects.filter(Q(rubricacriteriodocencia__criterio__in=criteriosdocencia) |
                                      Q(rubricacriterioinvestigacion__criterio__in=criteriosinvestigacion) |
                                      Q(rubricacriteriogestion__criterio__in=criteriosgestion), proceso__periodo=periodo, para_auto=True).exists()

    def mis_rubricas(self, periodo):
        distributivo = self.distributivohoras(periodo)
        criteriosdocencia = CriterioDocenciaPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        criteriosinvestigacion = CriterioInvestigacionPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        criteriosgestion = CriterioGestionPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        return Rubrica.objects.filter(Q(rubricacriteriodocencia__criterio__in=criteriosdocencia) |
                                      Q(rubricacriterioinvestigacion__criterio__in=criteriosinvestigacion) |
                                      Q(rubricacriteriogestion__criterio__in=criteriosgestion), proceso__periodo=periodo, para_auto=True).distinct()

    def mis_rubricas_par(self, periodo):
        distributivo = self.distributivohoras(periodo)
        criteriosdocencia = CriterioDocenciaPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        criteriosinvestigacion = CriterioInvestigacionPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        criteriosgestion = CriterioGestionPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        return Rubrica.objects.filter(Q(rubricacriteriodocencia__criterio__in=criteriosdocencia) |
                                      Q(rubricacriterioinvestigacion__criterio__in=criteriosinvestigacion) |
                                      Q(rubricacriteriogestion__criterio__in=criteriosgestion), proceso__periodo=periodo, para_par=True).distinct()

    def mis_rubricas_directivo(self, periodo):
        distributivo = self.distributivohoras(periodo)
        criteriosdocencia = CriterioDocenciaPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        criteriosinvestigacion = CriterioInvestigacionPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        criteriosgestion = CriterioGestionPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        return Rubrica.objects.filter(Q(rubricacriteriodocencia__criterio__in=criteriosdocencia) |
                                      Q(rubricacriterioinvestigacion__criterio__in=criteriosinvestigacion) |
                                      Q(rubricacriteriogestion__criterio__in=criteriosgestion), proceso__periodo=periodo, para_directivo=True).distinct()

    def cantidad_estudiantes_encuestados_docencia(self, periodo):
        return self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, proceso__periodo=periodo, materiaasignada__isnull=False).count()

    def promedio_estudiantes_coordinacion_docencia(self, periodo, coordinacion):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, proceso__periodo=periodo, coordinacion=coordinacion, valortotaldocencia__gt=0).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_autoevaluacion_coordinacion_docencia(self, periodo, coordinacion):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=2, proceso__periodo=periodo, coordinacion=coordinacion, valortotaldocencia__gt=0).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_par_coordinacion_docencia(self, periodo, coordinacion):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=3, proceso__periodo=periodo, coordinacion=coordinacion, valortotaldocencia__gt=0).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_directivo_coordinacion_docencia(self, periodo, coordinacion):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=4, proceso__periodo=periodo, coordinacion=coordinacion, valortotaldocencia__gt=0).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_general_coordinacion_docencia(self, periodo, coordinacion):
        return null_to_numeric((self.promedio_estudiantes_coordinacion_docencia(periodo, coordinacion) + self.promedio_autoevaluacion_coordinacion_docencia(periodo, coordinacion) + self.promedio_par_coordinacion_docencia(periodo, coordinacion) + self.promedio_directivo_coordinacion_docencia(periodo, coordinacion)) / 4.0, 1)

    def promedio_estudiantes_coordinacion_investigacion(self, periodo, coordinacion):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, proceso__periodo=periodo, coordinacion=coordinacion, valortotalinvestigacion__gt=0).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_autoevaluacion_coordinacion_investigacion(self, periodo, coordinacion):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=2, proceso__periodo=periodo, coordinacion=coordinacion, valortotalinvestigacion__gt=0).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_par_coordinacion_investigacion(self, periodo, coordinacion):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=3, proceso__periodo=periodo, coordinacion=coordinacion, valortotalinvestigacion__gt=0).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_directivo_coordinacion_investigacion(self, periodo, coordinacion):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=4, proceso__periodo=periodo, coordinacion=coordinacion, valortotalinvestigacion__gt=0).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_general_coordinacion_investigacion(self, periodo, coordinacion):
        return null_to_numeric((self.promedio_estudiantes_coordinacion_investigacion(periodo, coordinacion) + self.promedio_autoevaluacion_coordinacion_investigacion(periodo, coordinacion) + self.promedio_par_coordinacion_investigacion(periodo, coordinacion) + self.promedio_directivo_coordinacion_investigacion(periodo, coordinacion)) / 4.0, 1)

    def promedio_estudiantes_coordinacion_gestion(self, periodo, coordinacion):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, proceso__periodo=periodo, coordinacion=coordinacion, valortotalgestion__gt=0).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_autoevaluacion_coordinacion_gestion(self, periodo, coordinacion):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=2, proceso__periodo=periodo, coordinacion=coordinacion, valortotalgestion__gt=0).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_par_coordinacion_gestion(self, periodo, coordinacion):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=3, proceso__periodo=periodo, coordinacion=coordinacion, valortotalgestion__gt=0).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_directivo_coordinacion_gestion(self, periodo, coordinacion):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=4, proceso__periodo=periodo, coordinacion=coordinacion, valortotalgestion__gt=0).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_general_coordinacion_gestion(self, periodo, coordinacion):
        return null_to_numeric((self.promedio_estudiantes_coordinacion_gestion(periodo, coordinacion) + self.promedio_autoevaluacion_coordinacion_gestion(periodo, coordinacion) + self.promedio_par_coordinacion_gestion(periodo, coordinacion) + self.promedio_directivo_coordinacion_gestion(periodo, coordinacion)) / 4.0, 1)

    def promedio_estudiantes_carrera_docencia(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, proceso__periodo=periodo, carrera=carrera, valortotaldocencia__gt=0).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_autoevaluacion_carrera_docencia(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=2, proceso__periodo=periodo, carrera=carrera, valortotaldocencia__gt=0).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_par_carrera_docencia(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=3, proceso__periodo=periodo, carrera=carrera, valortotaldocencia__gt=0).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_directivo_carrera_docencia(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=4, proceso__periodo=periodo, carrera=carrera, valortotaldocencia__gt=0).aggregate(valor=Avg('valortotaldocencia'))['valor'], 1)

    def promedio_general_carrera_docencia(self, periodo, carrera):
        return null_to_numeric((self.promedio_estudiantes_carrera_docencia(periodo, carrera) + self.promedio_autoevaluacion_carrera_docencia(periodo, carrera) + self.promedio_par_carrera_docencia(periodo, carrera) + self.promedio_directivo_carrera_docencia(periodo, carrera)) / 4.0, 1)

    def promedio_estudiantes_carrera_investigacion(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, proceso__periodo=periodo, carrera=carrera, valortotalinvestigacion__gt=0).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_autoevaluacion_carrera_investigacion(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=2, proceso__periodo=periodo, carrera=carrera, valortotalinvestigacion__gt=0).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_par_carrera_investigacion(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=3, proceso__periodo=periodo, carrera=carrera, valortotalinvestigacion__gt=0).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_directivo_carrera_investigacion(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=4, proceso__periodo=periodo, carrera=carrera, valortotalinvestigacion__gt=0).aggregate(valor=Avg('valortotalinvestigacion'))['valor'], 1)

    def promedio_general_carrera_investigacion(self, periodo, carrera):
        return null_to_numeric((self.promedio_estudiantes_carrera_investigacion(periodo, carrera) + self.promedio_autoevaluacion_carrera_investigacion(periodo, carrera) + self.promedio_par_carrera_investigacion(periodo, carrera) + self.promedio_directivo_carrera_investigacion(periodo, carrera)) / 4.0, 1)

    def promedio_estudiantes_carrera_gestion(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, proceso__periodo=periodo, carrera=carrera, valortotalgestion__gt=0).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_autoevaluacion_carrera_gestion(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=2, proceso__periodo=periodo, carrera=carrera, valortotalgestion__gt=0).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_par_carrera_gestion(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=3, proceso__periodo=periodo, carrera=carrera, valortotalgestion__gt=0).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_directivo_carrera_gestion(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=4, proceso__periodo=periodo, carrera=carrera, valortotalgestion__gt=0).aggregate(valor=Avg('valortotalgestion'))['valor'], 1)

    def promedio_estudiantes_carrera_vinculacion(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, proceso__periodo=periodo, carrera=carrera, valortotalgestion__gt=0).aggregate(valor=Avg('valortotalvinculacion'))['valor'], 1)

    def promedio_autoevaluacion_carrera_vinculacion(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=2, proceso__periodo=periodo, carrera=carrera, valortotalgestion__gt=0).aggregate(valor=Avg('valortotalvinculacion'))['valor'], 1)

    def promedio_par_carrera_vinculacion(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=3, proceso__periodo=periodo, carrera=carrera, valortotalgestion__gt=0).aggregate(valor=Avg('valortotalvinculacion'))['valor'], 1)

    def promedio_directivo_carrera_vinculacion(self, periodo, carrera):
        return null_to_numeric(self.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=4, proceso__periodo=periodo, carrera=carrera, valortotalgestion__gt=0).aggregate(valor=Avg('valortotalvinculacion'))['valor'], 1)

    def promedio_general_carrera_gestion(self, periodo, carrera):
        return null_to_numeric((self.promedio_estudiantes_carrera_gestion(periodo, carrera) + self.promedio_autoevaluacion_carrera_gestion(periodo, carrera) + self.promedio_par_carrera_gestion(periodo, carrera) + self.promedio_directivo_carrera_gestion(periodo, carrera)) / 4.0, 1)

    def promedio_general_carrera_vinculacion(self, periodo, carrera):
        return null_to_numeric((self.promedio_estudiantes_carrera_vinculacion(periodo, carrera) + self.promedio_autoevaluacion_carrera_gestion(periodo, carrera) + self.promedio_par_carrera_vinculacion(periodo, carrera) + self.promedio_directivo_carrera_vinculacion(periodo, carrera)) / 4.0, 1)

    def carrera_principal_periodo(self, periodo):
        lista = {}
        try:
            for materia in self.materias_imparte_periodo(periodo):
                if materia.asignaturamalla:
                    carrera = materia.asignaturamalla.malla.carrera
                    if carrera in lista:
                        lista[carrera] += 1
                    else:
                        lista[carrera] = 1
            return max(lista.iteritems(), key=operator.itemgetter(1))[0]
        except:
            return None

    def evaluado_par_periodo(self, periodo, par):
        return RespuestaEvaluacionAcreditacion.objects.filter(tipoinstrumento=3, proceso__periodo=periodo, profesor=self, evaluador=par).exists()

    def dato_evaluado_par_periodo(self, periodo, par):
        if self.evaluado_par_periodo(periodo, par):
            return RespuestaEvaluacionAcreditacion.objects.filter(tipoinstrumento=3, proceso__periodo=periodo, profesor=self, evaluador=par)[0]
        return None

    def evaluado_directivo_periodo(self, periodo, par):
        return RespuestaEvaluacionAcreditacion.objects.filter(tipoinstrumento=4, proceso__periodo=periodo, profesor=self, evaluador=par).exists()

    def dato_evaluado_directivo_periodo(self, periodo, par):
        if self.evaluado_directivo_periodo(periodo, par):
            return RespuestaEvaluacionAcreditacion.objects.filter(tipoinstrumento=4, proceso__periodo=periodo, profesor=self, evaluador=par)[0]
        return None

    def turnos_dia(self, dia):
        return Turno.objects.filter(clase__dia=dia, clase__materia__profesormateria__profesor=self).distinct()

    def tiene_titulacion_registrada(self):
        return self.persona.estudiopersona_set.exists()

    def esta_laborando(self):
        return self.persona.trabajopersona_set.filter(institucionactual=True, ejerce=True, activo=True).exists()

    def es_profesor_practicas(self, clases):
        return TipoProfesor.objects.filter(profesormateria__materia__clase__in=clases, profesormateria__profesor=self, id=TIPO_DOCENTE_PRACTICA).exists()

    def tiene_clases_abiertas(self):
        return self.lecciongrupo_set.filter(abierta=True).exists()

    def tiene_clases_abiertas_practicas(self):
        return self.lecciongrupopractica_set.filter(abierta=True).exists()

    def registro_convocatoria(self, convocatoria):
        if self.profesorproyectoinvestigacion_set.filter(proyectoinvestigacion__convocatoria=convocatoria, principal=True).exists():
            return self.profesorproyectoinvestigacion_set.filter(proyectoinvestigacion__convocatoria=convocatoria, principal=True)[0]
        return None

    def mis_carreras(self, periodo):
        return Carrera.objects.filter(malla__asignaturamalla__materia__nivel__periodo=periodo, malla__asignaturamalla__materia__profesormateria__profesor=self).distinct()

    def tiene_titulo_tercer_nivel(self):
        return EstudioPersona.objects.filter(niveltitulacion__id=TERCER_NIVEL_TITULACION_ID).exists()

    def tiene_titulo_cuarto_nivel(self):
        return EstudioPersona.objects.filter(niveltitulacion__id=CUARTO_NIVEL_TITULACION_ID).exists()

    def mis_materias_periodo_sede(self, periodo, sede):
        return Materia.objects.filter(profesormateria__profesor=self, nivel__periodo=periodo, nivel__sede=sede)

    def numero_publicaciones(self, anio):
        return self.publicaciones_set.filter(tipopublicacion__id=9, fechapublicacion__year=anio).count()

    def numero_libros(self, anio):
        return self.publicaciones_set.filter(tipopublicacion__id=2, fechapublicacion__year=anio).count()

    def numero_capitulos(self, anio):
        return self.publicaciones_set.filter(tipopublicacion__id=3, fechapublicacion__year=anio).count()

    def actualizar_distributivo_horas(self, periodo):
        if not periodo.cerrado:
            distributivo = self.distributivohoras(periodo)
            if distributivo.dedicacion.id == TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID:
                distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo__criterio__id__in=[CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID, CRITERIO_HORAS_CLASE_PARCIAL_ID, CRITERIO_HORAS_CLASE_TECNICO_DOCENTE_ID]).delete()
                distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo__criterio__id__in=[CRITERIO_PRACTICAS_MEDIO_TIEMPO_ID, CRITERIO_PRACTICAS_PARCIAL_ID, CRITERIO_PRACTICAS_TECNICO_DOCENTE_ID]).delete()
            if distributivo.dedicacion.id == TIEMPO_DEDICACION_MEDIO_TIEMPO_ID:
                distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo__criterio__id__in=[CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID, CRITERIO_HORAS_CLASE_PARCIAL_ID, CRITERIO_HORAS_CLASE_TECNICO_DOCENTE_ID]).delete()
                distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo__criterio__id__in=[CRITERIO_PRACTICAS_TIEMPO_COMPLETO_ID, CRITERIO_PRACTICAS_PARCIAL_ID, CRITERIO_PRACTICAS_TECNICO_DOCENTE_ID]).delete()
            if distributivo.dedicacion.id == TIEMPO_DEDICACION_PARCIAL_ID:
                distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo__criterio__id__in=[CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID, CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID, CRITERIO_HORAS_CLASE_TECNICO_DOCENTE_ID]).delete()
                distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo__criterio__id__in=[CRITERIO_PRACTICAS_TIEMPO_COMPLETO_ID, CRITERIO_PRACTICAS_MEDIO_TIEMPO_ID, CRITERIO_PRACTICAS_TECNICO_DOCENTE_ID]).delete()
            if distributivo.dedicacion.id == TIEMPO_DEDICACION_TECNICO_DOCENTE_ID:
                distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo__criterio__id__in=[CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID, CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID, CRITERIO_HORAS_CLASE_PARCIAL_ID, ]).delete()
                distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo__criterio__id__in=[CRITERIO_PRACTICAS_TIEMPO_COMPLETO_ID, CRITERIO_PRACTICAS_MEDIO_TIEMPO_ID, CRITERIO_PRACTICAS_PARCIAL_ID, ]).delete()
            if distributivo.dedicacion.id not in (TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID, TIEMPO_DEDICACION_MEDIO_TIEMPO_ID, TIEMPO_DEDICACION_PARCIAL_ID, TIEMPO_DEDICACION_TECNICO_DOCENTE_ID):
                distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo__criterio__id__in=[CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID, CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID, CRITERIO_HORAS_CLASE_PARCIAL_ID, CRITERIO_HORAS_CLASE_TECNICO_DOCENTE_ID]).delete()
                distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo__criterio__id__in=[CRITERIO_PRACTICAS_TIEMPO_COMPLETO_ID, CRITERIO_PRACTICAS_MEDIO_TIEMPO_ID, CRITERIO_PRACTICAS_PARCIAL_ID, CRITERIO_PRACTICAS_TECNICO_DOCENTE_ID]).delete()
            if not ProfesorMateria.objects.filter(profesor=self, materia__nivel__periodo=periodo).exists():
                distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo__criterio__id__in=[CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID, CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID, CRITERIO_HORAS_CLASE_PARCIAL_ID, CRITERIO_HORAS_CLASE_TECNICO_DOCENTE_ID]).delete()
            if not ProfesorMateriaPracticas.objects.filter(profesor=self, grupo__materia__nivel__periodo=periodo).exists():
                distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo__criterio__id__in=[CRITERIO_PRACTICAS_TIEMPO_COMPLETO_ID, CRITERIO_PRACTICAS_MEDIO_TIEMPO_ID, CRITERIO_PRACTICAS_PARCIAL_ID, CRITERIO_PRACTICAS_TECNICO_DOCENTE_ID]).delete()
            if distributivo.dedicacion.id == TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID and (CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID or CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID):
                if ProfesorMateria.objects.filter(profesor=self, materia__nivel__periodo=periodo).exists():
                    if CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID).exists():
                        distributivoperiodo = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID)[0]
                    else:
                        distributivoperiodo = CriterioDocenciaPeriodo(periodo=periodo,
                                                                      criterio_id=CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID,
                                                                      minimo=0,
                                                                      maximo=MAXIMO_HORAS_DOCENCIA_TIEMPO_COMPLETO)
                        distributivoperiodo.save()
                    if distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo).exists():
                        detalle = distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo)[0]
                        detalle.horas = self.total_horas_periodo(periodo)
                        detalle.save()
                    else:
                        detalle = DetalleDistributivo(distributivo=distributivo,
                                                      criteriodocenciaperiodo=distributivoperiodo,
                                                      horas=self.total_horas_periodo(periodo))
                        detalle.save()
                    distributivo.save()
                if ProfesorMateriaPracticas.objects.filter(profesor=self, grupo__materia__nivel__periodo=periodo).exists():
                    if CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_PRACTICAS_TIEMPO_COMPLETO_ID).exists():
                        distributivoperiodo = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_PRACTICAS_TIEMPO_COMPLETO_ID)[0]
                    else:
                        distributivoperiodo = CriterioDocenciaPeriodo(periodo=periodo,
                                                                      criterio_id=CRITERIO_PRACTICAS_TIEMPO_COMPLETO_ID,
                                                                      minimo=0,
                                                                      maximo=MAXIMO_HORAS_DOCENCIA_TIEMPO_COMPLETO)
                        distributivoperiodo.save()
                    if distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo).exists():
                        detalle = distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo)[0]
                        detalle.horas = self.total_horas_periodo_practicas(periodo)
                        detalle.save()
                    else:
                        detalle = DetalleDistributivo(distributivo=distributivo,
                                                      criteriodocenciaperiodo=distributivoperiodo,
                                                      horas=self.total_horas_periodo_practicas(periodo))
                        detalle.save()
                    distributivo.save()

            if distributivo.dedicacion.id == TIEMPO_DEDICACION_MEDIO_TIEMPO_ID and (CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID or CRITERIO_PRACTICAS_MEDIO_TIEMPO_ID):
                if ProfesorMateria.objects.filter(profesor=self, materia__nivel__periodo=periodo).exists():
                    if CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID).exists():
                        distributivoperiodo = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID)[0]
                    else:
                        distributivoperiodo = CriterioDocenciaPeriodo(periodo=periodo,
                                                                      criterio_id=CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID,
                                                                      minimo=0,
                                                                      maximo=MAXIMO_HORAS_DOCENCIA_MEDIO_TIEMPO)
                        distributivoperiodo.save()
                    if distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo).exists():
                        detalle = distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo)[0]
                        detalle.horas = self.total_horas_periodo(periodo)
                        detalle.save()
                    else:
                        detalle = DetalleDistributivo(distributivo=distributivo,
                                                      criteriodocenciaperiodo=distributivoperiodo,
                                                      horas=self.total_horas_periodo(periodo))
                        detalle.save()
                    distributivo.save()
                if ProfesorMateriaPracticas.objects.filter(profesor=self, grupo__materia__nivel__periodo=periodo).exists():
                    if CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_PRACTICAS_MEDIO_TIEMPO_ID).exists():
                        distributivoperiodo = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_PRACTICAS_MEDIO_TIEMPO_ID)[0]
                    else:
                        distributivoperiodo = CriterioDocenciaPeriodo(periodo=periodo,
                                                                      criterio_id=CRITERIO_PRACTICAS_MEDIO_TIEMPO_ID,
                                                                      minimo=0,
                                                                      maximo=MAXIMO_HORAS_DOCENCIA_MEDIO_TIEMPO)
                        distributivoperiodo.save()
                    if distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo).exists():
                        detalle = distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo)[0]
                        detalle.horas = self.total_horas_periodo_practicas(periodo)
                        detalle.save()
                    else:
                        detalle = DetalleDistributivo(distributivo=distributivo,
                                                      criteriodocenciaperiodo=distributivoperiodo,
                                                      horas=self.total_horas_periodo_practicas(periodo))
                        detalle.save()
                    distributivo.save()
            if distributivo.dedicacion.id == TIEMPO_DEDICACION_PARCIAL_ID and (CRITERIO_HORAS_CLASE_PARCIAL_ID or CRITERIO_PRACTICAS_PARCIAL_ID):
                if ProfesorMateria.objects.filter(profesor=self, materia__nivel__periodo=periodo).exists():
                    if CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_HORAS_CLASE_PARCIAL_ID).exists():
                        distributivoperiodo = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_HORAS_CLASE_PARCIAL_ID)[0]
                    else:
                        distributivoperiodo = CriterioDocenciaPeriodo(periodo=periodo,
                                                                      criterio_id=CRITERIO_HORAS_CLASE_PARCIAL_ID,
                                                                      minimo=0,
                                                                      maximo=MAXIMO_HORAS_DOCENCIA_PARCIAL)
                        distributivoperiodo.save()
                    if distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo).exists():
                        detalle = distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo)[0]
                        detalle.horas = self.total_horas_periodo(periodo)
                        detalle.save()
                    else:
                        detalle = DetalleDistributivo(distributivo=distributivo,
                                                      criteriodocenciaperiodo=distributivoperiodo,
                                                      horas=self.total_horas_periodo(periodo))
                        detalle.save()
                    distributivo.save()
                if ProfesorMateriaPracticas.objects.filter(profesor=self, grupo__materia__nivel__periodo=periodo).exists():
                    if CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_PRACTICAS_PARCIAL_ID).exists():
                        distributivoperiodo = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_PRACTICAS_PARCIAL_ID)[0]
                    else:
                        distributivoperiodo = CriterioDocenciaPeriodo(periodo=periodo,
                                                                      criterio_id=CRITERIO_PRACTICAS_PARCIAL_ID,
                                                                      minimo=0,
                                                                      maximo=MAXIMO_HORAS_DOCENCIA_PARCIAL)
                        distributivoperiodo.save()
                    if distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo).exists():
                        detalle = distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo)[0]
                        detalle.horas = self.total_horas_periodo_practicas(periodo)
                        detalle.save()
                    else:
                        detalle = DetalleDistributivo(distributivo=distributivo,
                                                      criteriodocenciaperiodo=distributivoperiodo,
                                                      horas=self.total_horas_periodo_practicas(periodo))
                        detalle.save()
                    distributivo.save()

            if distributivo.dedicacion.id == TIEMPO_DEDICACION_TECNICO_DOCENTE_ID and (CRITERIO_HORAS_CLASE_TECNICO_DOCENTE_ID or CRITERIO_PRACTICAS_TECNICO_DOCENTE_ID):
                if ProfesorMateria.objects.filter(profesor=self, materia__nivel__periodo=periodo).exists():
                    if CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_HORAS_CLASE_TECNICO_DOCENTE_ID).exists():
                        distributivoperiodo = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_HORAS_CLASE_TECNICO_DOCENTE_ID)[0]
                    else:
                        distributivoperiodo = CriterioDocenciaPeriodo(periodo=periodo,
                                                                      criterio_id=CRITERIO_HORAS_CLASE_TECNICO_DOCENTE_ID,
                                                                      minimo=0,
                                                                      maximo=MAXIMO_HORAS_DOCENCIA_TECNICO_DOCENTE)
                        distributivoperiodo.save()
                    if distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo).exists():
                        detalle = distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo)[0]
                        detalle.horas = self.total_horas_periodo(periodo)
                        detalle.save()
                    else:
                        detalle = DetalleDistributivo(distributivo=distributivo,
                                                      criteriodocenciaperiodo=distributivoperiodo,
                                                      horas=self.total_horas_periodo(periodo))
                        detalle.save()
                    distributivo.save()
                if ProfesorMateriaPracticas.objects.filter(profesor=self, grupo__materia__nivel__periodo=periodo).exists():
                    if CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_PRACTICAS_TECNICO_DOCENTE_ID).exists():
                        distributivoperiodo = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__id=CRITERIO_PRACTICAS_TECNICO_DOCENTE_ID)[0]
                    else:
                        distributivoperiodo = CriterioDocenciaPeriodo(periodo=periodo,
                                                                      criterio_id=CRITERIO_PRACTICAS_TECNICO_DOCENTE_ID,
                                                                      minimo=0,
                                                                      maximo=MAXIMO_HORAS_DOCENCIA_TECNICO_DOCENTE)
                        distributivoperiodo.save()
                    if distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo).exists():
                        detalle = distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo=distributivoperiodo)[0]
                        detalle.horas = self.total_horas_periodo_practicas(periodo)
                        detalle.save()
                    else:
                        detalle = DetalleDistributivo(distributivo=distributivo,
                                                      criteriodocenciaperiodo=distributivoperiodo,
                                                      horas=self.total_horas_periodo_practicas(periodo))
                        detalle.save()
                    distributivo.save()

            distributivo.actualiza_detalle_modalidad()

    def save(self, *args, **kwargs):
        self.objetivodocente = null_to_text(self.objetivodocente)
        self.descripcionprof = null_to_text(self.descripcionprof)
        super(Profesor, self).save(*args, **kwargs)


class PerfilUsuario(ModeloBase):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    tipoperfilusuario = models.ForeignKey(TipoPerfilUsuario, blank=True, null=True, verbose_name=u'Tipo Perfil Usuario', on_delete=models.CASCADE)
    empleador = models.ForeignKey(Empleador, blank=True, null=True, verbose_name=u'Empleador', on_delete=models.CASCADE)
    administrativo = models.ForeignKey(Administrativo, blank=True, null=True, verbose_name=u'Administrativo', on_delete=models.CASCADE)
    profesor = models.ForeignKey(Profesor, blank=True, null=True, verbose_name=u'Profesor', on_delete=models.CASCADE)
    inscripcion = models.ForeignKey(Inscripcion, blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    principal = models.BooleanField(default=False, verbose_name=u'Inscripción principal')
    codigo_texto = models.CharField(default='', max_length=200, verbose_name=u"Código Texto")
    codigo_qr = models.FileField(upload_to='qr', verbose_name=u'Códigos QR', blank=True, null=True)

    def __str__(self):
        if self.es_estudiante():
            return u'%s - %s' % ("ESTUDIANTE", self.inscripcion.carrera.nombre)
        elif self.es_profesor():
            return u'%s' % "PROFESOR"
        elif self.es_administrativo():
            return u'%s' % "ADMINISTRATIVO"
        elif self.es_empleador():
            return u'%s' % "EMPLEADOR"

    class Meta:
        ordering = ['persona', 'inscripcion', 'administrativo', 'profesor', 'empleador']
        unique_together = ('persona', 'inscripcion', 'administrativo', 'profesor', 'empleador')

    def es_estudiante(self):
        return self.inscripcion is not None

    def es_profesor(self):
        return self.profesor is not None

    def es_administrativo(self):
        return self.administrativo is not None

    def es_empleador(self):
        return self.empleador is not None

    def es_cliente(self):
        return self.cliente is not None

    def establecer_estudiante_principal(self):
        if self.es_estudiante() and not self.principal:
            PerfilUsuario.objects.filter(persona=self.persona, inscripcion__isnull=False).update(principal=False)
            self.principal = True
            self.save()

    def activo(self):
        if self.es_estudiante():
            return self.inscripcion.activo
        elif self.es_profesor():
            return self.profesor.activo
        elif self.es_administrativo():
            return self.administrativo.activo
        elif self.es_empleador():
            return self.empleador.activo
        return False

    def tipo(self):
        if self.es_estudiante():
            return self.inscripcion.carrera.alias
        elif self.es_administrativo():
            return "ADMINISTRATIVO"
        elif self.es_profesor():
            return "PROFESOR"
        elif self.es_empleador():
            return "EMPLEADOR"
        else:
            return "NO DEFINIDO"

    def entrego_carnet(self):
        return self.entregacarnetperfil_set.exists()

    def entrega_carnet(self):
        if self.entrego_carnet():
            return self.entregacarnetperfil_set.all()[0]
        return None

class ProfesorMateria(ModeloBase):
    materia = models.ForeignKey(Materia, verbose_name=u'Materia', on_delete=models.CASCADE)
    profesor = models.ForeignKey(Profesor, verbose_name=u'Profesor', on_delete=models.CASCADE)
    tipoprofesor = models.ForeignKey(TipoProfesor, blank=True, null=True, verbose_name=u'Tipo Profesor', on_delete=models.CASCADE)
    horassemanales = models.FloatField(default=0, verbose_name=u'Horas')
    desde = models.DateField(verbose_name=u'Fecha inicio')
    hasta = models.DateField(verbose_name=u'Fecha fin')
    principal = models.BooleanField(default=True, verbose_name=u'Profesor principal')
    planifica = models.BooleanField(default=False, verbose_name=u'Profesor Planifica')
    sesuma = models.BooleanField(default=True, verbose_name=u'Suma a Total horas')
    motivo = models.TextField(default='', verbose_name=u"Motivo")
    horasapagar = models.IntegerField(default=0, verbose_name=u'Horas a Pagar')
    horasapagarsincrona = models.IntegerField(default=0, verbose_name=u'Horas Síncronas/Asíncronas a Pagar')
    horasapagarpae = models.IntegerField(default=0, verbose_name=u'Horas PAE a Pagar')
    costohora = models.FloatField(default=0, verbose_name=u"Costo Hora")
    costohorasincrona = models.FloatField(default=0, verbose_name=u"Costo Hora Sincrónicas")
    costohorapae = models.FloatField(default=0, verbose_name=u"Costo Hora PAE")
    valorextra = models.FloatField(default=0, verbose_name=u"Valor Extra")
    salario = models.FloatField(default=0, verbose_name=u"Salario")
    archivo = models.FileField(null=True, upload_to='materiaasignada/%Y/%m/%d', verbose_name=u'Archivo Subido', max_length=255)
    archivosubido = models.BooleanField(verbose_name=u'Archivo subido', default=False, null=True)
    aprobadofinanciero = models.BooleanField(verbose_name=u'Aprobado por Financiero', default=False, null=True)
    enviadopagar = models.BooleanField(verbose_name=u'Enviado a pagar', default=False, null=True)
    fecha_enviadopagar = models.DateField(null=True, verbose_name=u'Fecha de envio a pagar')
    fecha_aprobadofinanciero = models.DateField(null=True, verbose_name=u'Fecha aprueba financiero')
    desaprobadofinanciero = models.BooleanField(default=False, null=True, verbose_name=u'Aprobado por Financiero')
    motivo_desaprobado = models.TextField(verbose_name=u'Motivo de desapruebo', default='')
    persona_archivo = models.ForeignKey(Persona, null=True, verbose_name=u'Persona que sube el archivo', on_delete=models.CASCADE)
    exportadolms = models.BooleanField(default=False, verbose_name=u'Lms')

    def __str__(self):
        return u'%s %s %s' % (self.materia.nombre_completo(), self.tipoprofesor, self.profesor)

    class Meta:
        verbose_name_plural = u"Profesores de materias"
        unique_together = ('materia', 'profesor',)

    def es_profesor_practica(self):
        return self.tipoprofesor_id == TIPO_DOCENTE_PRACTICA

    def es_profesor_teoria(self):
        return self.tipoprofesor_id == TIPO_DOCENTE_TEORIA

    def tiene_lecciones(self):
        return LeccionGrupo.objects.filter(profesor=self.profesor, lecciones__clase__materia=self.materia).exists()

    def cantidad_lecciones(self):
        return LeccionGrupo.objects.filter(profesor=self.profesor, lecciones__clase__materia=self.materia).count()

    def syllabus(self):
        if self.materia.archivo_set.filter(profesor=self.profesor).exists():
            return self.materia.archivo_set.filter(profesor=self.profesor)[0]
        return None

    def nivel_materia(self):
        return Materia.objects.get(materia=self).nivel

    def pueden_evaluar_docente_acreditacion(self, matricula):
        proceso = self.materia.nivel.periodo.proceso_evaluativo()
        fecha = datetime.now().date()
        if not self.materia.usaperiodoevaluacion:
            puedevaluase = (datetime(self.materia.fin.year, self.materia.fin.month, self.materia.fin.day, 0, 0, 0) - timedelta(days=self.materia.diasactivacion)).date() <= datetime.now().date()
        else:
            if CronogramaEvaluacionHetero.objects.filter(proceso=proceso, carrera=self.materia.carrera).exists():
                puedevaluase = CronogramaEvaluacionHetero.objects.filter(proceso=proceso, carrera=self.materia.carrera, activo=True, inicio__lte=fecha, fin__gte=fecha).exists()
            else:
                puedevaluase = False
        return puedevaluase

    def pueden_evaluar_docente_nuevo(self, matricula):
        proceso = self.materia.nivel.periodo.proceso_evaluativo_docente()
        fecha = datetime.now().date()
        if not self.materia.usaperiodoevaluacion:
            puedevaluase = (datetime(self.materia.fin.year, self.materia.fin.month, self.materia.fin.day, 0, 0, 0) - timedelta(days=self.materia.diasactivacion)).date() <= datetime.now().date()
        else:
            if proceso.instrumentoheteroactivo:
                puedevaluase = True
            else:
                puedevaluase = False
        return puedevaluase

    def mis_rubricas_hetero(self):
        periodo = self.materia.nivel.periodo
        distributivo = self.profesor.distributivohoras(periodo)
        criteriosdocencia = CriterioDocenciaPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        criteriosinvestigacion = CriterioInvestigacionPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        criteriosgestion = CriterioGestionPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        criteriosvinculacion = CriterioVinculacionPeriodo.objects.filter(detalledistributivo__distributivo=distributivo)
        if self.tipoprofesor_id == TIPO_DOCENTE_PRACTICA:
            return Rubrica.objects.filter(Q(rubricacriteriodocencia__criterio__in=criteriosdocencia) |
                                          Q(rubricacriterioinvestigacion__criterio__in=criteriosinvestigacion) |
                                          Q(rubricacriteriovinculacion__criterio__in=criteriosvinculacion) |
                                          Q(rubricacriteriogestion__criterio__in=criteriosgestion), para_materiapractica=True, proceso__periodo=periodo, para_hetero=True).distinct()
        else:
            return Rubrica.objects.filter(Q(rubricacriteriodocencia__criterio__in=criteriosdocencia) |
                                          Q(rubricacriterioinvestigacion__criterio__in=criteriosinvestigacion) |
                                          Q(rubricacriteriovinculacion__criterio__in=criteriosvinculacion) |
                                          Q(rubricacriteriogestion__criterio__in=criteriosgestion), para_materiapractica=False, proceso__periodo=periodo, para_hetero=True).distinct()

    def mis_rubricas_hetero_docente(self):
        periodo = self.materia.nivel.periodo
        if self.tipoprofesor_id == TIPO_DOCENTE_PRACTICA:
            return RubricaDocente.objects.filter( para_materiapractica=True, proceso__periodo=periodo, para_hetero=True).distinct()
        else:
            return RubricaDocente.objects.filter( para_materiapractica=False, proceso__periodo=periodo, para_hetero=True).distinct()

    def evaluado(self, matricula):
        return RespuestaEvaluacionAcreditacion.objects.filter(tipoinstrumento=1, profesor=self.profesor, materia=self.materia, materiaasignada__matricula=matricula).exists()

    def evaluado_docente(self, matricula):
        return RespuestaEvaluacionDocente.objects.filter(tipoinstrumento=1, profesor=self.profesor, materia=self.materia, materiaasignada__matricula=matricula).exists()

    def mail_notificacion_distributivo(self, persona, destino):
        send_mail(subject='Existe un cambio en el DISTRIBUTIVO.',
                  html_template='emails/notificacioncambiodistributivo.html',
                  data={'d': self, 'persona': persona, 'destino': destino},
                  recipient_list=[destino])

    def mail_notificacion_aprobarfinanciero(self, persona, destino):
        send_mail(subject='CONFIRMACION DE HORAS A PAGAR.',
                  html_template='emails/notificacioncambiodistributivo.html',
                  data={'d': self, 'persona': persona, 'destino': destino},
                  recipient_list=[destino])

    def leccion_fecha(self, clase, fecha):
        if LeccionGrupo.objects.filter(profesor=self.profesor, fecha=fecha, lecciones__clase=clase).exists():
            return LeccionGrupo.objects.filter(profesor=self.profesor, fecha=fecha, lecciones__clase=clase)[0]
        return None

    def total_salario(self):
        return null_to_numeric(self.salario.aggregate(valor=Sum('salario'))['valor'], 2)

    def tiene_contrato(self):
        return ProfesorDistributivoHoras.objects.filter(periodo=self.materia.nivel.periodo, profesor=self.profesor, aprobadofinanciero=True).exists()

    def save(self, *args, **kwargs):
        self.horasapagar = null_to_numeric(self.horasapagar, 0)
        self.horasapagarsincrona = null_to_numeric(self.horasapagarsincrona, 0)
        self.horasapagarpae = null_to_numeric(self.horasapagarpae, 0)
        self.costohora = null_to_numeric(self.costohora, 2)
        self.costohorasincrona = null_to_numeric(self.costohorasincrona, 2)
        self.costohorapae = null_to_numeric(self.costohorapae, 2)
        self.valorextra = null_to_numeric(self.valorextra, 2)
        self.motivo = null_to_text(self.motivo)
        self.motivo_desaprobado = null_to_text(self.motivo_desaprobado)
        if self.id:
            self.salario = null_to_numeric((self.horasapagar * self.costohora) + (self.horasapagarsincrona * self.costohorasincrona), 2)
        super(ProfesorMateria, self).save(*args, **kwargs)



class MateriaCursoEscuelaComplementaria(ModeloBase):
    curso = models.ForeignKey(CursoEscuelaComplementaria, verbose_name=u'Curso Complementario', on_delete=models.CASCADE)
    asignatura = models.ForeignKey(Asignatura, verbose_name=u'Asignatura', on_delete=models.CASCADE)
    profesor = models.ForeignKey(Profesor, blank=True, null=True, verbose_name=u'Profesor', on_delete=models.CASCADE)
    fecha_inicio = models.DateField(verbose_name=u'Fecha Inicio')
    fecha_fin = models.DateField(verbose_name=u'Fecha Fin')
    calificar = models.BooleanField(default=False, verbose_name=u'Calificar')
    calfmaxima = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Calificación Máxima')
    calfminima = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Calificación Minima')
    horas = models.FloatField(default=0, verbose_name=u'Horas')
    creditos = models.FloatField(default=0, verbose_name=u'créditos')
    asistminima = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Asistencia Minima')
    cerrada = models.BooleanField(default=False, verbose_name=u'Cerrado')
    validacreditos = models.BooleanField(default=False, verbose_name=u'Valida para créditos')
    validapromedio = models.BooleanField(default=False, verbose_name=u'valida para promedio')
    requiereaprobar = models.BooleanField(default=True, verbose_name=u'Requerida para aprobar el curso')
    aprobadofinanciero = models.BooleanField(default=False)
    fechaaprobadofinanciero = models.DateTimeField(verbose_name=u'Fecha aprobado financiero', blank=True, null=True)
    aprobadodecano = models.BooleanField(default=False)
    fechaaprobadodecano = models.DateTimeField(verbose_name=u'Fecha aprobado decano', blank=True, null=True)
    horasapagar = models.IntegerField(default=0, verbose_name=u'Horas a Pagar')
    costohora = models.FloatField(default=0, verbose_name=u'Costo Hora')
    salario = models.FloatField(default=0, verbose_name=u'Salario')


    def __str__(self):
        return u'%s - %s' % (self.curso, self.asignatura)

    class Meta:
        unique_together = ('curso', 'asignatura',)

    def clases_activas_horario(self, dia):
        return self.clase_set.filter(dia=dia, activo=True).distinct()

    def tiene_horario(self):
        return self.clase_set.exists()

    def horarios(self):
        return self.clase_set.filter(activo=True).order_by('inicio', 'dia', 'turno__comienza')

    def horarios_asignados(self):
        if self.clase_set.filter(activo=True).exists():
            return self.clase_set.filter(activo=True).distinct('turno')
        return None

    def clases_informacion(self):
        return ["%s - %s a %s - (%s al %s) - %s" % (x.dia_semana(), x.turno.comienza.strftime('%I:%M %p'), x.turno.termina.strftime('%I:%M %p'), x.inicio.strftime('%d-%m-%Y'), x.fin.strftime('%d-%m-%Y'), x.aula.nombre) for x in self.clase_set.filter(activo=True).order_by('dia', 'turno__comienza')]

    def dias_programados(self):
        dias_lista = []
        for dia in self.clase_set.filter(activo=True).order_by('dia', 'turno__comienza'):
            dia_nombre = dia.dia_semana()[0:3].__str__()
            if dia_nombre not in dias_lista:
                dias_lista.append(dia_nombre)
        diassemana = ",".join(dias_lista)
        return "[" + diassemana + "]"

    def cantidad_clases(self):
        return self.clase_set.filter(activo=True).count()

    def aulas(self):
        return Aula.objects.filter(clase__materiacurso=self, clase__activo=True).distinct().order_by('capacidad')

    def tiene_clases(self):
        return LeccionGrupo.objects.filter(lecciones__clase__materiacurso=self).exists()

    def total_salario(self):
        return null_to_numeric(self.salario.aggregate(valor=Sum('salario'))['valor'], 2)

    def materiadistributivo(self, distributivocomplementaria):
        if MateriaDistributivoHorasComplementarias.objects.filter(materia=self, distributivocomplementaria=distributivocomplementaria).exists():
            return MateriaDistributivoHorasComplementarias.objects.filter(materia=self, distributivocomplementaria=distributivocomplementaria)[0]
        return None


    def tipo_origen(self):
        return 2

    def save(self, *args, **kwargs):
        self.horasapagar = null_to_numeric(self.horasapagar, 0)
        self.costohora = null_to_numeric(self.costohora, 2)
        if self.id:
            self.salario = null_to_numeric((self.horasapagar * self.costohora), 2)
        super(MateriaCursoEscuelaComplementaria, self).save(*args, **kwargs)




class Clase(ModeloBase):
    materia = models.ForeignKey(Materia, blank=True, null=True, verbose_name=u'Materia', on_delete=models.CASCADE)
    materiacurso = models.ForeignKey(MateriaCursoEscuelaComplementaria, blank=True, null=True, verbose_name=u'Materia', on_delete=models.CASCADE)
    turno = models.ForeignKey(Turno, verbose_name=u'Turno', on_delete=models.CASCADE)
    dia = models.IntegerField(choices=DIAS_CHOICES, default=0, verbose_name=u'Dia')
    inicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha Inicial')
    fin = models.DateField(blank=True, null=True, verbose_name=u'Fecha Final')
    aula = models.ForeignKey(Aula, verbose_name=u'Aula', on_delete=models.CASCADE)
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        if self.materia:
            materia = self.materia
        elif self.materiacurso:
            materia = self.materiacurso
        else:
            materia = self.materiatitulacion
        return u'%s %s %s' % (materia, self.turno, self.aula)

    class Meta:
        verbose_name_plural = u"Clases horarios"
        unique_together = ('materia', 'materiacurso', 'turno', 'dia', 'inicio', 'fin',)

    def nombre_materia(self):
        if self.materia:
            materia = self.materia.asignatura.nombre
        elif self.materiacurso:
            materia = self.materiacurso.asignatura.nombre
        else:
            materia = self.materiatitulacion.asignatura.nombre
        return materia

    def dia_semana(self):
        return DIAS_CHOICES[self.dia - 1][1]

    def tiene_lecciones(self):
        return self.leccion_set.exists()

    def tiene_leccion(self, fecha):
        return self.leccion_set.filter(fecha=fecha).exists()

    def tiene_lecciongrupo(self, fecha):
        return LeccionGrupo.objects.filter(fecha=fecha, lecciones__clase=self).exists()

    def tiene_lecciongrupo_rango_fechas(self, inicio, fin):
        return LeccionGrupo.objects.filter(fecha__gte=inicio, fecha__lte=fin, lecciones__clase=self).exists()

    def lecciongrupo_fecha(self, fecha):
        if self.tiene_lecciongrupo(fecha):
            return LeccionGrupo.objects.filter(fecha=fecha, lecciones__clase=self).distinct()[0]
        return None

    def lecciongrupo_rango_fechas(self, inicio, fin):
        if self.tiene_lecciongrupo_rango_fechas(inicio, fin):
            return LeccionGrupo.objects.filter(fecha__gte=inicio, fecha__lte=fin, lecciones__clase=self).distinct()[0]
        return None

    def lecciones_dia(self, fecha):
        if self.tiene_leccion(fecha):
            return self.leccion_set.filter(fecha=fecha)[0]
        return None

    def profesores(self):
        return self.materia.profesores()

    def cantidad_lecciones(self):
        return self.leccion_set.count()

    def fecha_comienzo_profesor(self, profesor):
        return self.materia.profesormateria_set.filter(profesor=profesor)[0].desde

    def fecha_fin_profesor(self, profesor):
        return self.materia.profesormateria_set.filter(profesor=profesor)[0].hasta

    def nombre_conflicto(self):
        if self.materia:
            return self.__str__() + " - " + self.materia.nivel.paralelo
        elif self.materiacurso:
            return self.__str__() + " - " + str(self.materiacurso.curso.paralelo)

        else:
            return self.__str__() + " - " + self.materiatitulacion.curso.paralelo

    def conflicto_aula(self):
        clasesexistentes = Clase.objects.filter(Q(materia__cerrado=False) |
                                                Q(materiacurso__cerrada=False) |
                                                Q(materiatitulacion__cerrada=False)).filter(Q(activo=True) &
                                                                                            Q(aula=self.aula) &
                                                                                            Q(dia=self.dia) &
                                                                                            (Q(inicio__lte=self.inicio, fin__gte=self.inicio) |
                                                                                             Q(inicio__lte=self.fin, fin__gte=self.fin) |
                                                                                             Q(inicio__gte=self.inicio, fin__lte=self.fin)) & (Q(turno=self.turno) |
                                                                                                                                               ((Q(turno__termina__gte=self.turno.comienza) & Q(turno__termina__lte=self.turno.termina)) |
                                                                                                                                                (Q(turno__comienza__gte=self.turno.comienza) & Q(turno__comienza__lte=self.turno.termina))))).exclude(id=self.id)
        if clasesexistentes:
            return clasesexistentes[0]
        return None

    def conflicto_docente(self):
        return None

    def nombre_horario(self):
        if self.materia:
            nombre = self.materia.asignatura.nombre
        elif self.materiacurso:
            nombre = self.materiacurso.asignatura.nombre
        else:
            nombre = self.materiatitulacion.asignatura.nombre
        return nombre + " - [" + (self.materia.identificacion if self.materia.identificacion else "###") + "] (" + self.inicio.strftime('%d-%m-%Y') + " al " + self.fin.strftime('%d-%m-%Y') + ")"

    def fechas_horarios(self):
        return self.inicio.strftime('%d-%m-%Y') + " al " + self.fin.strftime('%d-%m-%Y')

    def nombre_conflicto_docente(self):
        profesor = ''
        if self.materia:
            profesorprincipal = self.materia.profesor_principal()
            if profesorprincipal:
                profesor = profesorprincipal.__str__()
        elif self.materiacurso:
            if self.materiacurso.profesor:
                profesor = self.materiacurso.profesor.__str__()
        else:
            if self.materiatitulacion.profesor:
                profesor = self.materiatitulacion.profesor.__str__()
        return profesor + " - " + self.nombre_horario() + " - " + self.turno.__str__() + " - " + self.dia_semana() + ' - Aula: ' + self.aula.__str__()

    def disponible(self):
        d = datetime.now()
        if self.inicio > d.date():
            return False
        if CLASES_HORARIO_ESTRICTO:
            if self.dia == d.isoweekday():
                d2 = datetime(d.year, d.month, d.day, self.turno.comienza.hour, self.turno.comienza.minute)
                dt = (time.mktime(time.localtime()) - time.mktime(d2.timetuple())) / 60
                if dt < 0:
                    return abs(dt) <= CLASES_APERTURA_ANTES
                else:
                    return dt <= CLASES_APERTURA_DESPUES
            return False
        return True

    def mi_asistencia(self, inscripcion, fecha):
        if self.leccion_set.filter(fecha=fecha).exists():
            if self.materia:
                return AsistenciaLeccion.objects.filter(leccion__fecha=fecha, leccion__clase=self, materiaasignada__matricula__inscripcion=inscripcion)[0]
            elif self.materiacurso:
                return AsistenciaLeccion.objects.filter(leccion__fecha=fecha, leccion__clase=self, materiaasignadacurso__matricula__inscripcion=inscripcion)[0]
            elif self.materiatitulacion:
                return AsistenciaLeccion.objects.filter(leccion__fecha=fecha, leccion__clase=self, materiaasignadatitulacion__matricula__inscripcion=inscripcion)[0]
        return None

    def practicas(self):
        if self.gruposclasespracticas_set.all().exists():
            return self.gruposclasespracticas_set.all()[0]
        return None

    def fue_visitada_el(self, fecha):
        return VisitaInSituDocente.objects.filter(clase=self, fecha=fecha).exists()

    def save(self, *args, **kwargs):
        super(Clase, self).save(*args, **kwargs)



class Leccion(ModeloBase):
    clase = models.ForeignKey(Clase, verbose_name=u'Horario', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'fecha')
    horaentrada = models.TimeField(verbose_name=u'Hora entrada')
    horasalida = models.TimeField(blank=True, null=True, verbose_name=u'Hora salida')
    abierta = models.BooleanField(default=True, verbose_name=u'Abierta')
    contenido = models.TextField(default='', verbose_name=u'Contenido')
    estrategiasmetodologicas = models.TextField(default='', verbose_name=u'Estrategias metodologicas')
    observaciones = models.TextField(default='', verbose_name=u'Observaciones')

    class Meta:
        verbose_name_plural = u"Lecciones"
        ordering = ['-fecha', '-horaentrada']
        unique_together = ('clase', 'fecha',)

    def __str__(self):
        return u'%s %s' % (self.leccion_grupo(), self.clase.nombre_materia())

    def extra_delete(self):
        if self.clase.materia:
            if self.clase.materia.cerrado:
                return [False, False]
        if self.clase.materiacurso:
            if self.clase.materiacurso.cerrada:
                return [False, False]
        if self.clase.materiatitulacion:
            if self.clase.materiatitulacion.cerrada:
                return [False, False]

    def puede_tomar_asistencias(self):
        if not self.abierta:
            return False
        return True

    def mis_asistencias(self):
        return self.asistencialeccion_set.all()

    def asistencia_de_leccion(self):
        matriculas = self.clase.materia.asignados_a_esta_materia()
        asistencias = self.asistencialeccion_set.all()
        if matriculas.count() != asistencias.count():
            for materiaasignada in matriculas:
                asistenciasleccion = self.asistencialeccion_set.filter(materiaasignada=materiaasignada)
                if not asistenciasleccion.exists():
                    asistencia = AsistenciaLeccion(leccion=self,
                                                   materiaasignada=materiaasignada,
                                                   asistio=False)
                    asistencia.save()
                else:
                    if asistenciasleccion.count() > 1:
                        for otras in asistenciasleccion[1:]:
                            otras.delete()
                materiaasignada.save(actualiza=True)
                materiaasignada.actualiza_estado()
        return self.asistencialeccion_set.all()

    def asistencia_real(self):
        return self.asistencialeccion_set.filter(asistio=True).count()

    def asistencia_plan(self):
        return self.asistencialeccion_set.all().count()

    def porciento_asistencia(self):
        if self.asistencia_plan():
            return null_to_numeric((self.asistencia_real() * 100.0) / self.asistencia_plan(), 0)
        return 0

    def leccion_grupo(self):
        if LeccionGrupo.objects.filter(lecciones=self).exists():
            return LeccionGrupo.objects.filter(lecciones=self)[0]
        return None

    def deber(self):
        return Archivo.objects.filter(lecciongrupo__lecciones=self, tipo=ARCHIVO_TIPO_DEBERES)

    def save(self, *args, **kwargs):
        self.contenido = null_to_text(self.contenido)
        self.observaciones = null_to_text(self.observaciones)
        self.estrategiasmetodologicas = null_to_text(self.estrategiasmetodologicas)
        super(Leccion, self).save(*args, **kwargs)


class LeccionGrupo(ModeloBase):
    profesor = models.ForeignKey(Profesor, verbose_name=u'Profesor', on_delete=models.CASCADE)
    turno = models.ForeignKey(Turno, verbose_name=u'Turno', on_delete=models.CASCADE)
    aula = models.ForeignKey(Aula, verbose_name=u'Aula', on_delete=models.CASCADE)
    dia = models.IntegerField(choices=DIAS_CHOICES, default=1, verbose_name=u'Dia')
    fecha = models.DateField(verbose_name=u'Fecha')
    horaentrada = models.TimeField(verbose_name=u'Hora entrada')
    horasalida = models.TimeField(blank=True, null=True, verbose_name=u'Hora salida')
    abierta = models.BooleanField(default=True, verbose_name=u'Abierta')
    contenido = models.TextField(default='', verbose_name=u'Contenido')
    estrategiasmetodologicas = models.TextField(default='', verbose_name=u'Estrategia metodologica')
    observaciones = models.TextField(default='', verbose_name=u'Observaciones')
    lecciones = models.ManyToManyField(Leccion, verbose_name=u'Lecciones')
    motivoapertura = models.TextField(default='', verbose_name=u'Motivo apertura')
    origen_movil = models.BooleanField(default=False, verbose_name=u'Origen movil')
    origen_coordinador = models.BooleanField(default=False, verbose_name=u'Origen coordinador')
    automatica = models.BooleanField(default=False, verbose_name=u'Abierta automaticamente')
    solicitada = models.BooleanField(default=False, verbose_name=u'Solicitada apertura')
    actualizarasistencias = models.BooleanField(default=False, verbose_name=u'Solicitada apertura')

    class Meta:
        verbose_name_plural = u"Grupos de lecciones"
        ordering = ['-fecha', '-horaentrada']
        unique_together = ('profesor', 'turno', 'fecha',)

    def __str__(self):
        return u'%s - %s %s ' % (self.profesor.persona, self.fecha, self.turno)

    def mis_leciones(self):
        return self.lecciones.all()

    def puede_tomar_asistencias(self):
        return self.abierta

    def permite_cerrarla(self):
        if not self.solicitada:
            if CLASES_HORARIO_ESTRICTO:
                clase = self.lecciones.all()[0].clase
                if datetime.now() < (datetime(self.fecha.year, self.fecha.month, self.fecha.day, clase.turno.termina.hour, clase.turno.termina.minute) - timedelta(minutes=CLASES_CIERRE_ANTES)):
                    return False
        return True

    def periodo(self):
        return self.lecciones.all()[0].clase.materia.nivel.periodo

    def cerrar(self):
        self.abierta = False
        self.save()

    def materias_cerradas(self):
        return self.lecciones.filter(clase__materia__cerrado=True).exists()

    def puede_eliminarse(self):
        return not Materia.objects.filter(clase__leccion__lecciongrupo=self, cerrado=True).exists()

    def asistencia_real(self):
        return AsistenciaLeccion.objects.filter(leccion__lecciongrupo=self, asistio=True).count()

    def asistencia_plan(self):
        return AsistenciaLeccion.objects.filter(leccion__lecciongrupo=self).count()

    def porciento_asistencia(self):
        if self.asistencia_plan():
            return null_to_numeric((self.asistencia_real() * 100.0) / self.asistencia_plan(), 0)
        return 0

    def deber(self):
        return Archivo.objects.filter(lecciongrupo=self, tipo=ARCHIVO_TIPO_DEBERES)

    def total_presentes(self):
        return AsistenciaLeccion.objects.filter(leccion__lecciongrupo=self, asistio=True).count()

    def total_alumnos(self):
        return AsistenciaLeccion.objects.filter(leccion__lecciongrupo=self).count()

    def total_ausentes(self):
        return self.total_alumnos() - self.total_presentes()

    def mis_materias(self):
        return Materia.objects.filter(clase__leccion__lecciongrupo=self)

    def mi_asistencia_inscripcion(self, materiasignada):
        if AsistenciaLeccion.objects.filter(leccion__lecciongrupo=self, materiaasignada=materiasignada).exists():
            return AsistenciaLeccion.objects.filter(leccion__lecciongrupo=self, materiaasignada=materiasignada)[0]
        return None

    def tiene_incidencia(self):
        return self.incidencia_set.exists()

    def save(self, *args, **kwargs):
        self.contenido = null_to_text(self.contenido)
        self.observaciones = null_to_text(self.observaciones)
        self.motivoapertura = null_to_text(self.motivoapertura)
        self.estrategiasmetodologicas = null_to_text(self.estrategiasmetodologicas)
        if self.id:
            for leccion in self.mis_leciones():
                leccion.contenido = self.contenido
                leccion.estrategiasmetodologicas = self.estrategiasmetodologicas
                leccion.observaciones = self.observaciones
                leccion.fecha = self.fecha
                leccion.horaentrada = self.horaentrada
                leccion.horasalida = self.horasalida
                leccion.abierta = self.abierta
                leccion.save()
        super(LeccionGrupo, self).save(*args, **kwargs)



class Archivo(ModeloBase):
    tipo = models.ForeignKey(TipoArchivo, verbose_name=u'Tipo', on_delete=models.CASCADE)
    tipodocumento = models.ForeignKey(TipoDocumento, blank=True, null=True, verbose_name=u'Tipo', on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=300, verbose_name=u'Nombre')
    materia = models.ForeignKey(Materia, blank=True, null=True, verbose_name=u'Materia', on_delete=models.CASCADE)
    asignaturamalla = models.ForeignKey(AsignaturaMalla, blank=True, null=True, verbose_name=u'Asignatura malla', on_delete=models.CASCADE)
    lecciongrupo = models.ForeignKey(LeccionGrupo, blank=True, null=True, verbose_name=u'Lección grupo', on_delete=models.CASCADE)
    fecha = models.DateTimeField(verbose_name=u'Fecha')
    grupo = models.ManyToManyField(Group, verbose_name=u'Grupo')
    modulo = models.CharField(default='', blank=True, max_length=50, verbose_name=u'Modulo')
    profesor = models.ForeignKey(Profesor, blank=True, null=True, verbose_name=u'Profesor', on_delete=models.CASCADE)
    inscripcion = models.ForeignKey(Inscripcion, blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='documentos/%Y/%m', verbose_name=u'Archivo')
    aprobado = models.BooleanField(default=False, verbose_name=u'Aprobado')
    interfaz = models.BooleanField(default=False, verbose_name=u'Interfaz')
    observaciones = models.TextField(default='', blank=True, null=True, verbose_name=u'Observaciones')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Archivos"
        ordering = ['nombre', 'modulo']

    def nombre_archivo(self):
        return os.path.split(str(self.archivo.name))[1]

    def tipo_archivo(self):
        a = self.nombre_archivo()
        n = a[a.rindex(".") + 1:]
        if n == 'pdf' or n == 'doc' or n == 'docx':
            return n
        return 'other'

    def download_link(self):
        return self.archivo.url

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.modulo = null_to_text(self.modulo, lower=True)
        self.observaciones = null_to_text(self.observaciones)
        super(Archivo, self).save(*args, **kwargs)



class EvaluacionLeccion(ModeloBase):
    leccion = models.ForeignKey(Leccion, verbose_name=u'Lección', on_delete=models.CASCADE)
    materiaasignada = models.ForeignKey(MateriaAsignada, blank=True, null=True, verbose_name=u'Materia Asignada', on_delete=models.CASCADE)
    evaluacion = models.FloatField(default=0, verbose_name=u'Evaluación')

    class Meta:
        verbose_name_plural = u"Evaluaciones de lecciones"



class MateriaAsignadaCurso(ModeloBase):
    matricula = models.ForeignKey(MatriculaCursoEscuelaComplementaria, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    materia = models.ForeignKey(MateriaCursoEscuelaComplementaria, verbose_name=u'Materia', on_delete=models.CASCADE)
    notafinal = models.FloatField(default=0, verbose_name=u'Calificación')
    asistenciafinal = models.FloatField(default=100, verbose_name=u'Asistencia')
    estado = models.ForeignKey(TipoEstado, verbose_name=u'Estado', on_delete=models.CASCADE)
    # pasorecord = models.BooleanField(default=False, verbose_name=u'pasorecord')
    exportadolms = models.BooleanField(default=False, verbose_name=u'Lms')

    class Meta:
        unique_together = ('matricula', 'materia',)
        ordering = ['matricula']

    def aprobada(self):
        return self.estado_id == NOTA_ESTADO_APROBADO

    def reprobado(self):
        return self.estado_id == NOTA_ESTADO_REPROBADO

    def encurso(self):
        return self.estado_id == NOTA_ESTADO_EN_CURSO

    def recuperacion(self):
        return self.estado_id == NOTA_ESTADO_SUPLETORIO

    def existe_en_malla(self):
        malla = self.matricula.inscripcion.mi_malla()
        return malla.asignaturamalla_set.filter(asignatura=self.materia.asignatura).exists()

    def evaluacion_generica(self):
        if not self.evaluaciongenericacurso_set.exists():
            modelo = self.materia.curso.modeloevaluativo
            for campos in modelo.detallemodeloevaluativo_set.all():
                evaluacion = EvaluacionGenericaCurso(materiaasignadacurso=self,
                                                     detallemodeloevaluativo=campos,
                                                     valor=0)
                evaluacion.save()
        return self.evaluaciongenericacurso_set.all()

    def campo(self, campo):
        return self.evaluacion_generica().filter(detallemodeloevaluativo__nombre=campo)[0] if self.evaluacion_generica().filter(detallemodeloevaluativo__nombre=campo).exists() else None

    def valor_nombre_campo(self, campo):
        return self.evaluacion_generica().filter(detallemodeloevaluativo__nombre=campo)[0].valor if self.evaluacion_generica().filter(detallemodeloevaluativo__nombre=campo).exists() else 0

    def permite_calificacion(self):
        return True

    def materia_malla(self):
        malla = self.matricula.inscripcion.mi_malla()
        if self.existe_en_malla():
            return malla.asignaturamalla_set.filter(asignatura=self.materia.asignatura)[0]
        return None

    def verifica_campos_modelo(self):
        for campo in self.materia.curso.modeloevaluativo.detallemodeloevaluativo_set.all():
            if not self.evaluaciongenericacurso_set.filter(detallemodeloevaluativo=campo).exists():
                evaluaion = EvaluacionGenericaCurso(materiaasignadacurso=self,
                                                    detallemodeloevaluativo=campo)
                evaluaion.save()

    def porciento_requerido(self):
        if self.materia.calificar:
            return self.asistenciafinal >= self.materia.asistminima
        return 100

    def porciento_asistencia(self):
        total = self.asistencialeccion_set.count()
        real = self.asistencialeccion_set.filter(asistio=True).count()
        if total:
            return null_to_numeric((real * 100.0) / total, 0)
        return 0

    def actualiza_estado(self):
        if self.asistencialeccion_set.exists():
            self.asistenciafinal = self.porciento_asistencia()
        self.estado_id = NOTA_ESTADO_EN_CURSO
        if self.materia.calificar:
            if self.notafinal > 0:
                if self.notafinal >= self.materia.calfminima and self.asistenciafinal >= self.materia.asistminima:
                    self.estado_id = NOTA_ESTADO_APROBADO
                else:
                    self.estado_id = NOTA_ESTADO_REPROBADO
        else:
            if self.asistenciafinal >= self.materia.asistminima:
                self.estado_id = NOTA_ESTADO_APROBADO
        if self.materia.cerrada and self.estado_id == NOTA_ESTADO_EN_CURSO:
            self.estado_id = NOTA_ESTADO_REPROBADO
        self.save()

    def quitar_de_historico(self):
        if HistoricoRecordAcademico.objects.filter(inscripcion=self.matricula.inscripcion, asignatura=self.materia.asignatura, fecha=self.materia.fecha_fin).exists():
            historico = HistoricoRecordAcademico.objects.filter(inscripcion=self.matricula.inscripcion, asignatura=self.materia.asignatura, fecha=self.materia.fecha_fin)[0]
            historico.recordacademico = None
            historico.save()
            historico.delete()
            if HistoricoRecordAcademico.objects.filter(inscripcion=self.matricula.inscripcion, asignatura=self.materia.asignatura).exists():
                historico = HistoricoRecordAcademico.objects.filter(inscripcion=self.matricula.inscripcion, asignatura=self.materia.asignatura)[0]
                historico.actualizar()
            else:
                record = RecordAcademico.objects.filter(inscripcion=self.matricula.inscripcion, asignatura=self.materia.asignatura)[0]
                record.delete()

    def cierre_materia_asignada(self):
        self.actualiza_estado()
        aprobada = self.aprobada()
        if not self.matricula.inscripcion.graduado():
            if self.materia.curso.record:
                historico = None
                if HistoricoRecordAcademico.objects.filter(inscripcion=self.matricula.inscripcion, asignatura=self.materia.asignatura, fecha=self.materia.fecha_fin).exists():
                    historico = HistoricoRecordAcademico.objects.filter(inscripcion=self.matricula.inscripcion, asignatura=self.materia.asignatura, fecha=self.materia.fecha_fin)[0]
                elif HistoricoRecordAcademico.objects.filter(inscripcion=self.matricula.inscripcion, asignatura=self.materia.asignatura, materiacurso=self.materia).exists():
                    historico = HistoricoRecordAcademico.objects.filter(inscripcion=self.matricula.inscripcion, asignatura=self.materia.asignatura, materiacurso=self.materia)[0]
                if historico:
                    historico.asignaturamalla = self.matricula.inscripcion.asignatura_en_asignaturamalla(self.materia.asignatura)
                    historico.nota = self.notafinal
                    historico.horas = self.materia.horas
                    historico.creditos = self.materia.creditos
                    historico.validacreditos = self.materia.validacreditos
                    historico.validapromedio = self.materia.validapromedio
                    historico.asistencia = self.asistenciafinal
                    historico.fecha = self.materia.fecha_fin
                    historico.convalidacion = False
                    historico.optativa = self.materia.curso.optativa
                    historico.libreconfiguracion = self.materia.curso.libreconfiguracion
                    historico.sinasistencia = False
                    historico.homologada = False
                    historico.aprobada = aprobada
                    historico.pendiente = False
                    historico.observaciones = self.materia.curso.nombre[:99]
                    historico.save()
                else:
                    historico = HistoricoRecordAcademico(inscripcion=self.matricula.inscripcion,
                                                         asignatura=self.materia.asignatura,
                                                         asignaturamalla=self.matricula.inscripcion.asignatura_en_asignaturamalla(self.materia.asignatura),
                                                         nota=self.notafinal,
                                                         creditos=self.materia.creditos,
                                                         horas=self.materia.horas,
                                                         validacreditos=self.materia.validacreditos,
                                                         validapromedio=self.materia.validapromedio,
                                                         asistencia=self.asistenciafinal,
                                                         sinasistencia=False,
                                                         fecha=self.materia.fecha_fin,
                                                         convalidacion=False,
                                                         homologada=False,
                                                         aprobada=aprobada,
                                                         pendiente=False,
                                                         optativa=self.materia.curso.optativa,
                                                         libreconfiguracion=self.materia.curso.libreconfiguracion,
                                                         observaciones=self.materia.curso.nombre[:99],
                                                         materiacurso=self.materia)
                    historico.save()
                historico.actualizar()
                historico.inscripcion.actualizar_nivel()

    def save(self, actualiza=None, *args, **kwargs):
        if actualiza:
            self.notafinal = null_to_numeric(self.notafinal, 2)
            if self.asistencialeccion_set.exists():
                self.asistenciafinal = self.porciento_asistencia()
        super(MateriaAsignadaCurso, self).save(*args, **kwargs)



class AsistenciaLeccion(ModeloBase):
    leccion = models.ForeignKey(Leccion, verbose_name=u'Lección', on_delete=models.CASCADE)
    materiaasignada = models.ForeignKey(MateriaAsignada, blank=True, null=True, verbose_name=u'Materia Asignada', on_delete=models.CASCADE)
    materiaasignadacurso = models.ForeignKey(MateriaAsignadaCurso, blank=True, null=True, verbose_name=u'Materia Asignada Curso', on_delete=models.CASCADE)
    asistio = models.BooleanField(default=False, verbose_name=u'Asistencia')
    confirmada = models.BooleanField(default=False, verbose_name=u'Contenido')
    confirmadaasistencia = models.BooleanField(default=False, verbose_name=u'Docencia asistencia')
    confirmadacolaborativa = models.BooleanField(default=False, verbose_name=u'Aprendizaje colaborativa')
    confirmadaautonoma = models.BooleanField(default=False, verbose_name=u'Trabajo autónoma')
    confirmadapractica = models.BooleanField(default=False, verbose_name=u'Aprendizaje práctica')

    class Meta:
        verbose_name_plural = u"Asistencia de lecciones"
        ordering = ['materiaasignada', 'materiaasignadacurso']
        unique_together = ('leccion', 'materiaasignada', 'materiaasignadacurso')

    def __str__(self):
        if self.materiaasignada:
            persona = self.materiaasignada.matricula.inscripcion.persona.__str__()
        elif self.materiaasignadacurso:
            persona = self.materiaasignadacurso.matricula.inscripcion.persona.__str__()
        else:
            persona = self.materiaasignadatitulacion.matricula.inscripcion.persona.__str__()
        return u'%s - %s' % (persona, self.leccion.fecha.strftime('%d-%m-%Y'))

    def valida(self):
        if self.materiaasignada:
            return self.materiaasignada.fechaasignacion <= self.leccion.fecha <= self.leccion.clase.materia.fechafinasistencias
        return True

    def evaluaciones(self):
        return EvaluacionLeccion.objects.filter(Q(materiaasignada=self.materiaasignada) | Q(materiaasignadacurso=self.materiaasignadacurso) | Q(materiaasignadatitulacion=self.materiaasignadatitulacion), leccion=self.leccion)

    def porciento_asistencia_actual(self):
        if self.materiaasignada:
            total = AsistenciaLeccion.objects.filter(leccion__clase__materia=self.leccion.clase.materia, materiaasignada=self.materiaasignada).count()
            real = AsistenciaLeccion.objects.filter(leccion__clase__materia=self.leccion.clase.materia, materiaasignada=self.materiaasignada, asistio=True).count()
            if total:
                return null_to_numeric((real * 100.0) / total, 2)
        elif self.materiaasignadacurso:
            total = AsistenciaLeccion.objects.filter(leccion__clase__materiacurso=self.leccion.clase.materiacurso, materiaasignadacurso=self.materiaasignadacurso).count()
            real = AsistenciaLeccion.objects.filter(leccion__clase__materiacurso=self.leccion.clase.materiacurso, materiaasignadacurso=self.materiaasignadacurso, asistio=True).count()
            if total:
                return null_to_numeric((real * 100.0) / total, 2)
        else:
            total = AsistenciaLeccion.objects.filter(leccion__clase__materiatitulacion=self.leccion.clase.materiacurso, materiaasignadatitulacion=self.materiaasignadatitulacion).count()
            real = AsistenciaLeccion.objects.filter(leccion__clase__materiatitulacion=self.leccion.clase.materiacurso, materiaasignadatitulacion=self.materiaasignadatitulacion, asistio=True).count()
            if total:
                return null_to_numeric((real * 100.0) / total, 2)
        return 100

    def promedio_evaluacion(self):
        return null_to_numeric(EvaluacionLeccion.objects.filter(Q(materiaasignada=self.materiaasignada) | Q(materiaasignadacurso=self.materiaasignadacurso) | Q(materiaasignadatitulacion=self.materiaasignadatitulacion), leccion=self.leccion).aggregate(valor=Avg('evaluacion'))['valor'], 0)

    def permite_tomar(self):
        if self.materiaasignada:
            return self.materiaasignada.permite_calificacion()
        elif self.materiaasignadacurso:
            return self.materiaasignadacurso.permite_calificacion()
        else:
            return self.materiaasignadatitulacion.permite_calificacion()

    def puede_tomar_asistencia(self):
        if self.materiaasignada:
            if self.materiaasignada.esta_retirado():
                return False
        elif self.materiaasignadacurso:
            if self.materiaasignadacurso.matricula.esta_retirado():
                return False
        return True

    def esta_justificada(self):
        return self.justificacionausenciaasistencialeccion_set.exists()

    def justificacion(self):
        if self.justificacionausenciaasistencialeccion_set.exists():
            return self.justificacionausenciaasistencialeccion_set.all()[0]


class Incidencia(ModeloBase):
    lecciongrupo = models.ForeignKey(LeccionGrupo, verbose_name=u"Lección", on_delete=models.CASCADE)
    tipo = models.ForeignKey(TipoIncidencia, verbose_name=u"Tipo incidencia", on_delete=models.CASCADE)
    subtipo = models.ForeignKey(SubTipoincidencia, null=True, verbose_name=u"Sub tipo incidencia", on_delete=models.CASCADE)
    contenido = models.TextField(default='', verbose_name=u"Contenido")
    solucion = models.TextField(default='', verbose_name=u"Solución")
    cerrada = models.BooleanField(default=False, verbose_name=u"Cerrada")
    sede = models.ForeignKey(Sede, null=True, verbose_name=u"Sede", on_delete=models.CASCADE)
    asistencialeccion = models.ForeignKey(AsistenciaLeccion, blank=True, null=True, verbose_name=u"Asistencia Leccion", on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.lecciongrupo, self.tipo)

    class Meta:
        verbose_name_plural = u"Incidencias en clases"
        ordering = ['-lecciongrupo__fecha']
        unique_together = ('lecciongrupo', 'tipo', 'contenido',)

    def respondida(self):
        if len(self.solucion) == 0:
            return False
        return True

    def mail_nuevo(self, periodo):
        ca = self.lecciongrupo.profesor.carrera_principal_periodo(periodo)
        for lista in self.tipo.responsabletipoincidencia_set.all():
            send_mail(subject='Nueva incidencia de clases.',
                      html_template='emails/incidencia.html',
                      data={'d': self, 'periodo': periodo, 'carrera': ca},
                      recipient_list=[lista.responsable])
            send_html_mail(subject='Nueva incidencia de clases.',
                           html_template='emails/incidencia.html',
                           data={'d': self, 'periodo': periodo},
                           recipient_list=[lista.responsable],
                           recipient_list_cc=[])

    def mail_respuesta(self):
        send_mail(subject='Su incidencia ya fue atendida, disculpas por las molestias.',
                  html_template='emails/respuestaincidencia.html',
                  data={'d': self},
                  recipient_list=[self.lecciongrupo.profesor.persona])

    def save(self, *args, **kwargs):
        self.contenido = null_to_text(self.contenido)
        self.solucion = null_to_text(self.solucion)
        super(Incidencia, self).save(*args, **kwargs)


class JustificacionAusenciaAsistenciaLeccion(ModeloBase):
    asistencialeccion = models.ForeignKey(AsistenciaLeccion, on_delete=models.CASCADE)
    porcientojustificado = models.FloatField(default=100, verbose_name=u"Porciento Justificado")
    motivo = models.TextField(default='', verbose_name=u"Motivo")
    fecha = models.DateField(verbose_name=u"Fecha")
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('asistencialeccion',)

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        super(JustificacionAusenciaAsistenciaLeccion, self).save(*args, **kwargs)


class Noticia(ModeloBase):
    tipo = models.IntegerField(choices=TIPOS_NOTICIAS, default=1, verbose_name=u'Tipo de noticia')
    titular = models.CharField(default='', max_length=100, verbose_name=u'Titular')
    cuerpo = models.TextField(default='', verbose_name=u'Noticia')
    desde = models.DateField(verbose_name=u'Fecha inicio de publicación')
    hasta = models.DateField(verbose_name=u'Fecha fin de publicación')
    publica = models.ForeignKey(Persona, verbose_name=u'Responsable', on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADOS_NOTICIAS, default=1)
    imagen = models.ForeignKey(Archivo, blank=True, null=True, verbose_name=u'Imagen', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.titular

    class Meta:
        verbose_name_plural = u"Noticias"
        ordering = ['-hasta']
        unique_together = ('tipo', 'titular', 'desde', 'hasta',)

    def esta_pendiente(self):
        return self.estado == 1

    def esta_aprobada(self):
        return self.estado == 2

    def esta_rechazada(self):
        return self.estado == 3

    def publicada(self):
        return self.desde <= datetime.now().date() <= self.hasta and self.esta_aprobada()

    def download_foto(self):
        if self.imagen:
            return self.imagen.archivo.url
        return None

    def save(self, *args, **kwargs):
        self.titular = null_to_text(self.titular)
        self.cuerpo = null_to_text(self.cuerpo, transform=False)
        super(Noticia, self).save(*args, **kwargs)




class Mensaje(ModeloBase):
    asunto = models.CharField(default='', max_length=100, verbose_name=u'Asunto')
    contenido = models.TextField(default='', verbose_name=u'Contenido')
    fecha = models.DateField(verbose_name=u'Fecha')
    hora = models.TimeField(verbose_name=u'Hora')
    origen = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u'Origen', on_delete=models.CASCADE)
    borrador = models.BooleanField(default=True, verbose_name=u'es borrador')
    archivo = models.ManyToManyField(Archivo, verbose_name=u'Archivos adjuntos')
    visible = models.BooleanField(default=True, verbose_name=u'Visible')

    def __str__(self):
        return u'%s' % self.asunto

    class Meta:
        verbose_name_plural = u"Mensajes"
        ordering = ['-fecha', '-hora']

    def tiene_adjunto(self):
        return self.archivo.exists()

    def destinatarios(self):
        return self.mensajedestinatario_set.all()

    def es_reenvio(self):
        return MensajeDestinatario.objects.filter(reenvio=self).exists()

    def esta_leido(self, persona):
        return self.mensajedestinatario_set.filter(destinatario=persona, leido=True).exists()

    def save(self, *args, **kwargs):
        self.asunto = null_to_text(self.asunto, transform=False)
        self.contenido = null_to_text(self.contenido, transform=False)
        super(Mensaje, self).save(*args, **kwargs)



class MensajeDestinatario(ModeloBase):
    mensaje = models.ForeignKey(Mensaje, verbose_name=u'Mensaje', on_delete=models.CASCADE)
    destinatario = models.ForeignKey(Persona, verbose_name=u'Destinatario', on_delete=models.CASCADE)
    leido = models.BooleanField(default=False, verbose_name=u'Leido')
    fecha = models.DateField(blank=True, null=True, verbose_name=u'Fecha')
    hora = models.TimeField(blank=True, null=True, verbose_name=u'Fecha')
    visible = models.BooleanField(default=True, verbose_name=u'Visible')
    reenvio = models.ForeignKey(Mensaje, blank=True, null=True, related_name='reenvio', verbose_name=u'Origen reenvio', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('mensaje', 'destinatario',)




class BancaOnline(ModeloBase):
    banco = models.ForeignKey(Banco, verbose_name=u'Banco', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha')
    procesado = models.BooleanField(default=False, verbose_name=u'Procesado')
    valorrecaudacion = models.FloatField(default=0, verbose_name=u'Valor recaudación')
    cajero = models.ForeignKey(LugarRecaudacion, verbose_name=u'Cajero', on_delete=models.CASCADE)
    archivo = models.ForeignKey(Archivo, verbose_name=u'Archivo', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.banco, self.fecha.strftime("%d-%m-%Y"))

    class Meta:
        verbose_name_plural = u"Recaudaciones bancarias"
        unique_together = ('banco', 'fecha',)


class DetalleRecaudacionBanca(ModeloBase):
    recaudacion = models.ForeignKey(BancaOnline, verbose_name=u'Recaudación', on_delete=models.CASCADE)
    cuentabanco = models.ForeignKey(CuentaBanco, verbose_name=u'Cuenta banco', on_delete=models.CASCADE)
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    valor = models.FloatField(default=0, verbose_name=u'Valor')
    referencia = models.CharField(default='', max_length=150, verbose_name=u'Referencia')
    hora = models.TimeField(blank=True, null=True, verbose_name=u'Hora')

    def __str__(self):
        return u'%s - %s - %s' % (self.inscripcion, self.valor, self.referencia)

    class Meta:
        verbose_name_plural = u"Detalles de recaudaciones bancarias"
        unique_together = ('recaudacion', 'cuentabanco', 'inscripcion',)

    def save(self, *args, **kwargs):
        self.referencia = self.referencia
        super(DetalleRecaudacionBanca, self).save(*args, **kwargs)



class HabilitadoIngresoCalificaciones(ModeloBase):
    profesor = models.ForeignKey(Profesor, on_delete=models.CASCADE)
    fecha = models.DateField()
    clavegenerada = models.CharField(max_length=4)
    habilitado = models.BooleanField(default=False)

    class Meta:
        unique_together = ('profesor',)

class EntregaCarnetPerfil(ModeloBase):
    perfilusuario = models.ForeignKey(PerfilUsuario, on_delete=models.CASCADE)
    fecha = models.DateField()


class PlanificacionMateria(ModeloBase):
    materia = models.ForeignKey(Materia, blank=True, null=True, verbose_name=u'Materia', on_delete=models.CASCADE)
    materiacurso = models.ForeignKey(MateriaCursoEscuelaComplementaria, blank=True, null=True, verbose_name=u'Materia', on_delete=models.CASCADE)
    horariotutorias = models.TextField(default='', verbose_name=u'Horario de tutoria')
    horariopracticas = models.TextField(default='', verbose_name=u'Horario de practicas')
    horas = models.FloatField(default=0, verbose_name=u'Horas')
    creditos = models.FloatField(default=0, verbose_name=u'créditos')
    horasasistidasporeldocente = models.FloatField(default=0)
    horascolaborativas = models.FloatField(default=0)
    horasautonomas = models.FloatField(default=0)
    horaspracticas = models.FloatField(default=0)
    competenciagenericainstitucion = models.ForeignKey(CompetenciaGenerica, verbose_name=u'competencia genérica de la institucion', on_delete=models.CASCADE)
    competenciaespecificaperfildeegreso = models.ForeignKey(CompetenciaEspecifica, verbose_name=u'competencia específica del perfilde egreso', on_delete=models.CASCADE)
    competenciaespecificaproyectoformativo = models.TextField(default='', verbose_name=u'competencia específica del proyecto formativo')
    contribucioncarrera = models.TextField(default='', verbose_name=u'contribucion a la carrera')
    problemaabordadometodosdeensenanza = models.TextField(default='', verbose_name=u'problema abordado y metodos de enseñanza')
    proyectofinal = models.TextField(default='', verbose_name=u'proyecto final')
    verificada = models.BooleanField(default=False, verbose_name=u'Verificada')
    aprobado = models.BooleanField(default=False, verbose_name=u'Aprobado')
    valida = models.BooleanField(default=True, verbose_name=u'Valida')
    aprueba = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u'Persona Aprueba', on_delete=models.CASCADE)
    fechaaprobacion = models.DateField(blank=True, null=True, verbose_name=u'Fecha aprobación')
    observacion = models.BooleanField(default=False, verbose_name=u'Observacion')
    observaciones = models.TextField(default='', blank=True, null=True, verbose_name=u'Observaciones')
    transversalidad = models.TextField(default='', verbose_name=u'Transversalidad')
    metodologias = models.TextField(default='', verbose_name=u'Metodologias')
    verificadabiblioteca = models.BooleanField(default=False, verbose_name=u'Verificada')
    aprobadobiblioteca = models.BooleanField(default=False, verbose_name=u'Aprobado')
    observacionbiblioteca = models.BooleanField(default=False, verbose_name=u'Observacion')
    observacionesbiblioteca = models.TextField(default='', blank=True, null=True, verbose_name=u'Observaciones')

    def __str__(self):
        return u'%s' % self.materia.nombre_completo()

    class Meta:
        verbose_name_plural = u"Microcurriculo de materias"
        unique_together = ('materia',)

    def es_plantilla(self):
        if self.materia:
            if self.materia.asignaturamalla:
                return self.silaboasignaturamalla_set.exists()
        return False

    def profesor(self):
        if self.materia:
            return self.materia.profesor_principal()
        elif self.materiacursotitulacion:
            return self.materiacursotitulacion.profesor
        elif self.materiacurso:
            return self.materiacurso.profesor
        return None

    def cantidad_talleres(self):
        return self.tallerplanificacionmateria_set.count()

    def todos_talleres_aprobadas(self):
        if self.tallerplanificacionmateria_set.filter(aprobado=True).count() >= self.tallerplanificacionmateria_set.count():
            return True
        else:
            return False

    def todos_talleres_observacion(self):
        if self.tallerplanificacionmateria_set.filter(observacion=True).exists():
            return True
        else:
            return False

    def cantidad_clases(self):
        return ClasesTallerPlanificacionMateria.objects.filter(tallerplanificacionmateria__planificacionmateria=self).count()

    def mi_rubrica(self):
        if self.rubricaresultadoaprendizaje_set.exists():
            rubrica = self.rubricaresultadoaprendizaje_set.all()[0]
        else:
            rubrica = RubricaResultadoAprendizaje(planificacionmateria=self,
                                                  evidencia=self.proyectofinal)
            rubrica.save()
        return rubrica

    def tiene_rubrica(self):
        return self.rubricaresultadoaprendizaje_set.exists()

    def bibliografia_basica(self):
        return self.bibliografiabasicaplanificacion_set.all()

    def bibliografia_complementaria(self):
        return self.bibliografiacomplementariaplanificacion_set.all()

    def total_bibliografia(self):
        return self.bibliografiacomplementariaplanificacion_set.count() + self.bibliografiabasicaplanificacion_set.count()

    def total_horas_asistidas(self):
        return null_to_numeric(ClasesTallerPlanificacionMateria.objects.filter(tallerplanificacionmateria__planificacionmateria=self).aggregate(valor=Sum('horasdocente'))['valor'], 1)

    def total_horas_colaborativas(self):
        return null_to_numeric(ClasesTallerPlanificacionMateria.objects.filter(tallerplanificacionmateria__planificacionmateria=self).aggregate(valor=Sum('horascolaborativas'))['valor'], 1)

    def total_horas_autonomas(self):
        return null_to_numeric(ClasesTallerPlanificacionMateria.objects.filter(tallerplanificacionmateria__planificacionmateria=self).aggregate(valor=Sum('horasautonomas'))['valor'], 1)

    def total_horas_practicas(self):
        return null_to_numeric(ClasesTallerPlanificacionMateria.objects.filter(tallerplanificacionmateria__planificacionmateria=self).aggregate(valor=Sum('horaspracticas'))['valor'], 1)

    def total_horas_guias_practicas(self):
        return null_to_numeric(GuiasPracticasMateria.objects.filter(planificacionmateria=self).aggregate(valor=Sum('horas'))['valor'], 1)

    def cantidad_guias_practicas(self):
        return GuiasPracticasMateria.objects.filter(planificacionmateria=self).count()+GuiasNuevaPracticasMateria.objects.filter(planificacionmateria=self).count()+GuiasNuevaSimPracticasMateria.objects.filter(planificacionmateria=self).count()

    def disponile_docencia(self):
        return null_to_numeric(self.horasasistidasporeldocente - self.total_horas_asistidas(), 1)

    def disponile_autonoma(self):
        return null_to_numeric(self.horasautonomas - self.total_horas_autonomas(), 1)

    def disponile_colabora(self):
        return null_to_numeric(self.horascolaborativas - self.total_horas_colaborativas(), 1)

    def disponile_practica(self):
        return null_to_numeric(self.horaspracticas - self.total_horas_practicas(), 1)

    def disponile_gias_practica(self):
        return null_to_numeric(self.horaspracticas - self.total_horas_guias_practicas(), 1)

    def practica(self):
        return self.guiaspracticasmateria_set.all()

    def tiene_tallerplanificacion_aprobada(self):
        return self.tallerplanificacionmateria_set.filter(aprobado=True).exists()

    def mis_guias_nuevas_simulacion(self):
        return self.guiasnuevasimpracticasmateria_set.all().order_by('id')

    def save(self, *args, **kwargs):
        self.horariotutorias = null_to_text(self.horariotutorias)
        self.horariopracticas = null_to_text(self.horariopracticas)
        self.competenciaespecificaproyectoformativo = null_to_text(self.competenciaespecificaproyectoformativo)
        self.contribucioncarrera = null_to_text(self.contribucioncarrera)
        self.problemaabordadometodosdeensenanza = null_to_text(self.problemaabordadometodosdeensenanza)
        self.proyectofinal = null_to_text(self.proyectofinal)
        super(PlanificacionMateria, self).save(*args, **kwargs)



class TallerPlanificacionMateria(ModeloBase):
    planificacionmateria = models.ForeignKey(PlanificacionMateria, verbose_name=u'Microcurriculo de Materia', on_delete=models.CASCADE)
    nombretaller = models.TextField(default='', verbose_name=u'Nombre')
    resultadoaprendizaje = models.TextField(default='', verbose_name=u'resultado de aprendizaje')
    recursosutilizados = models.TextField(default='', verbose_name=u'recursos utilizados')
    dimensionprocedimental = models.TextField(default='', verbose_name=u'dimension procedimental')
    productoesperado = models.TextField(default='', verbose_name=u'Producto esperado del taller')
    verificada = models.BooleanField(default=False, verbose_name=u'Verificada')
    aprobado = models.BooleanField(default=False, verbose_name=u'Aprobado')
    aprueba = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u'Persona Aprueba', on_delete=models.CASCADE)
    fechaaprobacion = models.DateField(blank=True, null=True, verbose_name=u'Fecha aprobación')
    observaciones = models.TextField(default='', blank=True, null=True, verbose_name=u'Observaciones')
    observacion = models.BooleanField(default=False, verbose_name=u'Observacion')

    def __str__(self):
        return u'%s' % self.nombretaller

    class Meta:
        ordering = ['nombretaller']
        verbose_name_plural = u"Talleres de materia"

    def cantidad_contenido(self):
        return self.contenidostallerplanificacionmateria_set.count()

    def cantidad_clases(self):
        return self.clasestallerplanificacionmateria_set.count()

    def contenidos(self):
        return self.contenidostallerplanificacionmateria_set.all()

    def mis_clases(self):
        return self.clasestallerplanificacionmateria_set.all().order_by('fecha', 'id')

    def mis_guias_nuevas(self):
        return self.guiasnuevapracticasmateria_set.all().order_by('id')

    def mis_guias(self):
        return self.guiaspracticasmateria_set.all().order_by('id')

    def total_horas_asistidas(self):
        return null_to_numeric(self.clasestallerplanificacionmateria_set.aggregate(valor=Sum('horasdocente'))['valor'], 1)

    def total_horas_autonomas(self):
        return null_to_numeric(self.clasestallerplanificacionmateria_set.aggregate(valor=Sum('horasautonomas'))['valor'], 1)

    def total_horas_practicas(self):
        return null_to_numeric(self.clasestallerplanificacionmateria_set.aggregate(valor=Sum('horaspracticas'))['valor'], 1)

    def total_horas_colaborativas(self):
        return null_to_numeric(self.clasestallerplanificacionmateria_set.aggregate(valor=Sum('horascolaborativas'))['valor'], 1)

    def mi_rubrica(self):
        if self.rubricaresultadoaprendizaje_set.exists():
            rubrica = self.rubricaresultadoaprendizaje_set.all()[0]
        else:
            rubrica = RubricaResultadoAprendizaje(tallerplanificacionmateria=self,
                                                  evidencia=self.productoesperado)
            rubrica.save()
        return rubrica

    def save(self, *args, **kwargs):
        self.nombretaller = null_to_text(self.nombretaller)
        self.resultadoaprendizaje = null_to_text(self.resultadoaprendizaje)
        self.recursosutilizados = null_to_text(self.recursosutilizados)
        self.dimensionprocedimental = null_to_text(self.dimensionprocedimental)
        super(TallerPlanificacionMateria, self).save(*args, **kwargs)


class ObservacionesTallerPlanificacionMateria(ModeloBase):
    taller = models.ForeignKey(TallerPlanificacionMateria, verbose_name=u'Taller Planificacion Materia', on_delete=models.CASCADE)
    observacion = models.TextField(default='', verbose_name=u'Nombre')
    realizadapor = models.ForeignKey(Persona, verbose_name=u'Realizada por', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.observacion


class ContenidosTallerPlanificacionMateria(ModeloBase):
    tallerplanificacionmateria = models.ForeignKey(TallerPlanificacionMateria, verbose_name=u'Taller Materia', on_delete=models.CASCADE)
    contenido = models.TextField(default='', verbose_name=u'Contenido')

    def __str__(self):
        return u'%s' % self.contenido

    class Meta:
        verbose_name_plural = u"Contenidos del Taller"
        ordering = ['contenido']

    def save(self, *args, **kwargs):
        self.contenido = null_to_text(self.contenido)
        super(ContenidosTallerPlanificacionMateria, self).save(*args, **kwargs)



class ActividadesAprendizajeCondocenciaAsistida(ModeloBase):
    nombre = models.CharField(verbose_name=u'Nombre', max_length=100)

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Actividades de aprendizaje condocencia asistida"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(ActividadesAprendizajeCondocenciaAsistida, self).save(*args, **kwargs)


class ActividadesTrabajoAutonomas(ModeloBase):
    nombre = models.CharField(verbose_name=u'Nombre', max_length=100)

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Actividades de trabajo autonomas"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(ActividadesTrabajoAutonomas, self).save(*args, **kwargs)


class ActividadesAprendizajePractico(ModeloBase):
    nombre = models.CharField(verbose_name=u'Nombre', max_length=100)

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Actividades de aprendizaje practico"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(ActividadesAprendizajePractico, self).save(*args, **kwargs)


class ActividadesAprendizajeColaborativas(ModeloBase):
    nombre = models.CharField(verbose_name=u'Nombre', max_length=100)

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Actividades de aprendizaje colaborativas"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(ActividadesAprendizajeColaborativas, self).save(*args, **kwargs)


class ClasesTallerPlanificacionMateria(ModeloBase):
    tallerplanificacionmateria = models.ForeignKey(TallerPlanificacionMateria, verbose_name=u'Taller Materia', on_delete=models.CASCADE)
    fecha = models.DateField()
    fechafinactividades = models.DateField()
    contenido = models.ForeignKey(ContenidosTallerPlanificacionMateria, blank=True, null=True, verbose_name=u'Contenidos taller', on_delete=models.CASCADE)
    actividadesaprendizajecondocenciaasistida_uno = models.ForeignKey(ActividadesAprendizajeCondocenciaAsistida, related_name='+', blank=True, null=True, verbose_name=u'Actividades de aprendizaje condocencia asistida', on_delete=models.CASCADE)
    actividadesaprendizajecondocenciaasistida_dos = models.ForeignKey(ActividadesAprendizajeCondocenciaAsistida, related_name='+', blank=True, null=True, verbose_name=u'Actividades de aprendizaje condocencia asistida', on_delete=models.CASCADE)
    horasdocente_uno = models.FloatField(default=0)
    horasdocente_dos = models.FloatField(default=0)
    horasdocente = models.FloatField(default=0)
    actividadesaprendizajecolaborativas = models.ForeignKey(ActividadesAprendizajeColaborativas, blank=True, null=True, verbose_name=u'Actividades de aprendizaje colaborativas', on_delete=models.CASCADE)
    horascolaborativas = models.FloatField(default=0)
    actividadestrabajoautonomas = models.TextField(default='', blank=True, null=True, verbose_name=u'Autonomas')
    horasautonomas = models.FloatField(default=0)
    actividadesaprendizajepractico = models.TextField(default='', blank=True, null=True, verbose_name=u'Practicas')
    horaspracticas = models.FloatField(default=0)
    archivo = models.FileField(upload_to='microcurriculo/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    fasesactividadesarticulacion = models.ForeignKey(FasesActividadesArticulacion, related_name='+', blank=True, null=True, verbose_name=u'Fases Actividades Articulacion', on_delete=models.CASCADE)
    actividadcontactodocente_uno = models.TextField(default='', blank=True, null=True, verbose_name=u'Actividades de aprendizaje condocencia asistida')
    actividadcontactodocente_dos = models.TextField(default='', blank=True, null=True, verbose_name=u'Actividades de aprendizaje condocencia asistida')
    actividadaprendcolab = models.TextField(default='', blank=True, null=True, verbose_name=u'Actividades de aprendizaje colaborativo')

    def __str__(self):
        return u'%s' % self.contenido

    class Meta:
        verbose_name_plural = u"Talleres de materia"

    def lecciones(self):
        return self.lecciongrupo_set.all()

    def tiene_clases_impartidas(self):
        return self.lecciongrupo_set.exists()

    def total_horas(self):
        return null_to_numeric(self.horasdocente + self.horascolaborativas + self.horasautonomas + self.horaspracticas, 1)

    def save(self, *args, **kwargs):
        self.actividadestrabajoautonomas = null_to_text(self.actividadestrabajoautonomas)
        self.actividadesaprendizajepractico = null_to_text(self.actividadesaprendizajepractico)
        self.actividadcontactodocente_uno = null_to_text(self.actividadcontactodocente_uno)
        self.actividadcontactodocente_dos = null_to_text(self.actividadcontactodocente_dos)
        self.actividadaprendcolab = null_to_text(self.actividadaprendcolab)
        self.horasdocente = null_to_numeric(self.horasdocente_uno + self.horasdocente_dos, 1)
        super(ClasesTallerPlanificacionMateria, self).save(*args, **kwargs)

class BibliografiaComplementariaPlanificacion(ModeloBase):
    planificacionmateria = models.ForeignKey(PlanificacionMateria, verbose_name=u'Taller Materia', on_delete=models.CASCADE)
    digital = models.BooleanField(default=False)
    weburl = models.CharField(default='', null=True, blank=True, max_length=500, verbose_name=u"Web url")
    codigobibliotecabibliografiacomplementaria = models.CharField(default='', max_length=100, verbose_name=u'codigo biblioteca bibliografia complementaria')
    bibliografiacomplementaria = models.TextField(default='', verbose_name=u'bibliografia complementaria')
    autor = models.CharField(default='', max_length=100, verbose_name=u'Autor')
    editorial = models.CharField(default='', max_length=100, verbose_name=u'Editorial')
    anno = models.CharField(default='', max_length=100, verbose_name=u'Año de Edición')

    def __str__(self):
        return u'%s' % self.bibliografiacomplementaria

    class Meta:
        ordering = ['bibliografiacomplementaria']
        verbose_name_plural = u"bibliografia complementaria"

    def save(self, *args, **kwargs):
        self.codigobibliotecabibliografiacomplementaria = null_to_text(self.codigobibliotecabibliografiacomplementaria)
        self.autor = null_to_text(self.autor)
        self.editorial = null_to_text(self.editorial)
        self.anno = null_to_text(self.anno)
        super(BibliografiaComplementariaPlanificacion, self).save(*args, **kwargs)



class BibliografiaBasicaPlanificacion(ModeloBase):
    planificacionmateria = models.ForeignKey(PlanificacionMateria, verbose_name=u'Taller Materia', on_delete=models.CASCADE)
    digital = models.BooleanField(default=False)
    weburl = models.CharField(default='', null=True, blank=True, max_length=500, verbose_name=u"Web url")
    codigobibliotecabibliografiabasica = models.CharField(default='', max_length=100, verbose_name=u'codigo biblioteca bibliografia basica')
    bibliografiabasica = models.TextField(default='', verbose_name=u'bibliografia basica')
    autor = models.CharField(default='', max_length=100, verbose_name=u'Autor')
    editorial = models.CharField(default='', max_length=100, verbose_name=u'Editorial')
    anno = models.CharField(default='', max_length=100, verbose_name=u'Año de Edición')

    def __str__(self):
        return u'%s' % self.bibliografiabasica

    class Meta:
        ordering = ['bibliografiabasica']
        verbose_name_plural = u"bibliografia complementaria"

    def save(self, *args, **kwargs):
        self.codigobibliotecabibliografiabasica = null_to_text(self.codigobibliotecabibliografiabasica)
        self.bibliografiabasica = null_to_text(self.bibliografiabasica)
        self.autor = null_to_text(self.autor)
        self.editorial = null_to_text(self.editorial)
        self.anno = null_to_text(self.anno)
        self.autor = null_to_text(self.autor)
        self.autor = null_to_text(self.autor)
        super(BibliografiaBasicaPlanificacion, self).save(*args, **kwargs)


TIPOS_GUIAS_CHOICES = (
    (1, u"LABORATORIOS"),
    (2, u"VISITA"),
    (3, u"BASE DE DATOS"),
    (4, u"SIMULACIÓN")
)
class GuiasPracticasMateria(ModeloBase):
    titulo = models.CharField(verbose_name=u'Titulo', max_length=300)
    planificacionmateria = models.ForeignKey(PlanificacionMateria, verbose_name=u'Planificacion', on_delete=models.CASCADE)
    taller = models.ForeignKey(TallerPlanificacionMateria, blank=True, null=True, verbose_name=u'Planificacion', on_delete=models.CASCADE)
    tipo = models.IntegerField(default=1, choices=TIPOS_GUIAS_CHOICES)
    recursos = models.CharField(verbose_name=u'Recursos', blank=True, null=True, max_length=300)
    equipos = models.CharField(verbose_name=u'Equipos o herramientas', blank=True, null=True, max_length=300)
    materiales = models.CharField(verbose_name=u'Materiales', blank=True, null=True, max_length=300)
    reactivos = models.CharField(verbose_name=u'Reactivos', blank=True, null=True, max_length=300)
    destino = models.CharField(verbose_name=u'Destino (lugar geográfico)', blank=True, null=True, max_length=300)
    empresa = models.CharField(verbose_name=u'Empresa o institución en donde se va a desarrollar la visita', blank=True, null=True, max_length=300)
    contactoempresa = models.CharField(verbose_name=u'Persona de contacto en la institución y/o empresa', blank=True, null=True, max_length=300)
    materialesbibliograficos = models.CharField(verbose_name=u'Materiales  bibliograficos', blank=True, null=True, max_length=300)
    instrumentos = models.CharField(verbose_name=u'Instrumentos', blank=True, null=True, max_length=300)
    herramientas = models.CharField(verbose_name=u'Herramientas/software', blank=True, null=True, max_length=300)
    objetivo = models.TextField(default='', verbose_name=u'Nombre')
    actividades = models.TextField(default='', verbose_name=u'Nombre')
    resultados = models.TextField(default='', verbose_name=u'resultado de aprendizaje')
    conclusiones = models.TextField(default='', verbose_name=u'recursos utilizados')
    fundamentoteorico = models.TextField(default='', verbose_name=u'Fundamentos teoricos')
    procedimiento = models.TextField(default='', verbose_name=u'Procedimientos metodologia')
    horas = models.FloatField(default=0)
    archivo = models.FileField(upload_to='planificacion/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    inicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha inicio')
    fin = models.DateField(blank=True, null=True, verbose_name=u'Fecha fin')

    def __str__(self):
        return u'%s' % self.titulo

    class Meta:
        verbose_name_plural = u"Guias par de materia"

    def practica(self):
        return self.practicamateria_set.all()

    def asistencia(self):
        return self.asistenciaguiaspracticas_set.all()

    def save(self, *args, **kwargs):
        self.titulo = null_to_text(self.titulo)
        self.objetivo = null_to_text(self.objetivo)
        self.actividades = null_to_text(self.actividades)
        self.procedimiento = null_to_text(self.procedimiento)
        self.fundamentoteorico = null_to_text(self.fundamentoteorico)
        self.resultados = null_to_text(self.resultados)
        self.conclusiones = null_to_text(self.conclusiones)
        super(GuiasPracticasMateria, self).save(*args, **kwargs)

    def practicas_planificadas(self):
        return self.practicamateria_set.all().count()

    def practicas_planificadas_cerradas(self):
        return self.practicamateria_set.filter(cerrado=True).count()


class RubricaResultadoAprendizaje(ModeloBase):
    planificacionmateria = models.ForeignKey(PlanificacionMateria, blank=True, null=True, verbose_name=u'Planificación Materia', on_delete=models.CASCADE)
    tallerplanificacionmateria = models.ForeignKey(TallerPlanificacionMateria, blank=True, null=True, verbose_name=u'Taller Materia', on_delete=models.CASCADE)
    evidencia = models.TextField(blank=True, null=True, verbose_name=u'Evidencia')
    criterio = models.TextField(blank=True, null=True, verbose_name=u'Criterio')
    logroexcelente = models.TextField(blank=True, null=True, verbose_name=u'Excelente')
    logroavanzado = models.TextField(blank=True, null=True, verbose_name=u'Avanzado')
    logromedio = models.TextField(blank=True, null=True, verbose_name=u'Medio')
    logrobajo = models.TextField(blank=True, null=True, verbose_name=u'Bajo')
    logrodeficiente = models.TextField(blank=True, null=True, verbose_name=u'Deficiente')

    def mi_taller(self):
        return self.tallerplanificacionmateria

    def mi_planificacion(self):
        return self.planificacionmateria

    def mis_indicadores(self):
        if self.indicadorrubrica_set.exists():
            return self.indicadorrubrica_set.all().order_by('id')
        else:
            return None


class IndicadorRubrica(ModeloBase):
    rubricaresultadoaprendizaje = models.ForeignKey(RubricaResultadoAprendizaje, blank=True, null=True, verbose_name=u'Rubrica', on_delete=models.CASCADE)
    criterio = models.TextField(blank=True, null=True, verbose_name=u'Criterio')
    logroexcelente = models.TextField(blank=True, null=True, verbose_name=u'Excelente')
    logromuybueno = models.TextField(blank=True, null=True, verbose_name=u'Muy bueno')
    logrobueno = models.TextField(blank=True, null=True, verbose_name=u'Bueno')
    logroregular = models.TextField(blank=True, null=True, verbose_name=u'Regular')
    logrodeficiente = models.TextField(blank=True, null=True, verbose_name=u'Deficiente')

    def mi_rubrica(self):
        return self.rubricaresultadoaprendizaje

ESTADOS_SOLICITUD_APERTURA = (
    (1, u'PENDIENTE'),
    (2, u'APROBADO'),
    (3, u'RECHAZADO')
)


class SolicitudAperturaClase(ModeloBase):
    profesor = models.ForeignKey(Profesor, on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u"Fecha")
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, blank=True, null=True, on_delete=models.CASCADE)
    coordinacion = models.ForeignKey(Coordinacion, blank=True, null=True, on_delete=models.CASCADE)
    fecharespuesta = models.DateField(verbose_name=u"Fecha respuesta", blank=True, null=True)
    motivo = models.TextField(default='')

    estado = models.IntegerField(choices=ESTADOS_SOLICITUD_APERTURA, default=1)

    motivorechazo = models.TextField(blank=True, null=True)
    documento = models.FileField(upload_to='solicitudes/%Y/%m/%d', blank=True, null=True)
    aperturada = models.BooleanField(default=False)

    def __str__(self):
        return u'%s - %s - %s' % (self.profesor, self.fecha.strftime("%d-%m-%Y"), self.turno)

    class Meta:
        verbose_name_plural = u"Solicitudes de aperturas de clases"
        ordering = ('-fecha',)

    def esta_aprobada(self):
        return self.estado == SOLICITUD_APERTURACLASE_APROBADA_ID

    def esta_rechazada(self):
        return self.estado == SOLICITUD_APERTURACLASE_RECHAZADA_ID

    def esta_pendiente(self):
        return self.estado == SOLICITUD_APERTURACLASE_PENDIENTE_ID

    def esta_aprobadaverificada(self):
        return self.estadoverificada == SOLICITUD_APERTURACLASE_APROBADA_ID

    def esta_rechazadaverificada(self):
        return self.estadoverificada == SOLICITUD_APERTURACLASE_RECHAZADA_ID

    def esta_pendienteverificada(self):
        return self.estadoverificada == SOLICITUD_APERTURACLASE_PENDIENTE_ID

    def actualiza_carrera(self):
        if Clase.objects.filter(turno=self.turno, inicio__lte=self.fecha, fin__gte=self.fecha, dia=self.fecha.isoweekday(), materia__profesormateria__profesor=self.profesor, materia__profesormateria__principal=True).exists():
            clase = Clase.objects.filter(turno=self.turno, inicio__lte=self.fecha, fin__gte=self.fecha, dia=self.fecha.isoweekday(), materia__profesormateria__profesor=self.profesor, materia__profesormateria__principal=True)[0]
            if clase.materia.asignaturamalla:
                return clase.materia.asignaturamalla.malla.carrera
        return None

    def actualiza_coordinacion(self):
        if Clase.objects.filter(turno=self.turno, inicio__lte=self.fecha, fin__gte=self.fecha, dia=self.fecha.isoweekday(), materia__profesormateria__profesor=self.profesor, materia__profesormateria__principal=True).exists():
            clase = Clase.objects.filter(turno=self.turno, inicio__lte=self.fecha, fin__gte=self.fecha, dia=self.fecha.isoweekday(), materia__profesormateria__profesor=self.profesor, materia__profesormateria__principal=True)[0]
            return clase.materia.nivel.nivellibrecoordinacion_set.all()[0].coordinacion
        return None

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        self.carrera = self.actualiza_carrera()
        self.coordinacion = self.actualiza_coordinacion()
        super(SolicitudAperturaClase, self).save(*args, **kwargs)


class SolicitudIngresoNotasAtraso(ModeloBase):
    materia = models.ForeignKey(Materia, verbose_name=u"Materia", on_delete=models.CASCADE)
    profesor = models.ForeignKey(Profesor, verbose_name=u"Materia", on_delete=models.CASCADE)
    detallemodeloevaluativo = models.ForeignKey(DetalleModeloEvaluativo, verbose_name=u"Detalle Modelo Evaluativo", on_delete=models.CASCADE)
    motivo = models.TextField(default='')
    fechasolicitud = models.DateField(verbose_name=u'Fecha')
    fechaaprobacion = models.DateField(verbose_name=u'Fecha', blank=True, null=True)
    fechalimite = models.DateField(verbose_name=u'Fecha', blank=True, null=True)
    estado = models.IntegerField(choices=ESTADOS_SOLICITUD_APERTURA, default=1)
    dias = models.IntegerField(default=0, verbose_name=u'Dias aprobar')

    class Meta:
        verbose_name = u"Solicitud ingreso nota atraso"
        ordering = ['fechasolicitud']

    def esta_aprobada(self):
        return self.estado == SOLICITUD_APERTURACLASE_APROBADA_ID

    def esta_rechazada(self):
        return self.estado == SOLICITUD_APERTURACLASE_RECHAZADA_ID

    def esta_pendiente(self):
        return self.estado == SOLICITUD_APERTURACLASE_PENDIENTE_ID

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        super(SolicitudIngresoNotasAtraso, self).save(*args, **kwargs)

ESTADOS_SOLICITUD_INGRESONOTASESTUDIANTE = (
    (1, u'PENDIENTE'),
    (2, u'APROBADO'),
    (3, u'RECHAZADO'),
    (4, u'CERRADO')
)

class SolicitudIngresoNotasEstudiante(ModeloBase):
    materiaasignada = models.ForeignKey(MateriaAsignada, verbose_name=u"Materia", on_delete=models.CASCADE)
    profesor = models.ForeignKey(Profesor, verbose_name=u"Profesor", on_delete=models.CASCADE)
    modeloevaluativo = models.ForeignKey(ModeloEvaluativo, verbose_name=u"Detalle Modelo Evaluativo", on_delete=models.CASCADE)
    motivo = models.TextField(default='')
    fechasolicitud = models.DateField(verbose_name=u'Fecha solicitud')
    fechaaprobacion = models.DateField(verbose_name=u'Fecha aprobacion', blank=True, null=True)
    fechalimite = models.DateField(verbose_name=u'Fecha límite', blank=True, null=True)
    estado = models.IntegerField(choices=ESTADOS_SOLICITUD_INGRESONOTASESTUDIANTE, default=1)
    dias = models.IntegerField(default=0, verbose_name=u'Dias aprobar')
    archivo = models.FileField(upload_to='archivosolingnotest/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')

    def esta_aprobada(self):
        return self.estado == SOLICITUD_APERTURACLASE_APROBADA_ID

    def esta_rechazada(self):
        return self.estado == SOLICITUD_APERTURACLASE_RECHAZADA_ID

    def esta_pendiente(self):
        return self.estado == SOLICITUD_APERTURACLASE_PENDIENTE_ID

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        super(SolicitudIngresoNotasEstudiante, self).save(*args, **kwargs)




class EvaluacionGenericaCurso(ModeloBase):
    materiaasignadacurso = models.ForeignKey(MateriaAsignadaCurso, verbose_name=u"Materia asignada", on_delete=models.CASCADE)
    detallemodeloevaluativo = models.ForeignKey(DetalleModeloEvaluativo, verbose_name=u'Detalle modelo evaluación', on_delete=models.CASCADE)
    valor = models.FloatField(default=0, verbose_name=u'Valor evaluación')

    class Meta:
        ordering = ['detallemodeloevaluativo']
        unique_together = ('materiaasignadacurso', 'detallemodeloevaluativo',)

    def save(self, *args, **kwargs):
        if self.valor >= self.detallemodeloevaluativo.notamaxima:
            self.valor = self.detallemodeloevaluativo.notamaxima
        elif self.valor <= self.detallemodeloevaluativo.notaminima:
            self.valor = self.detallemodeloevaluativo.notaminima
        self.valor = null_to_numeric(self.valor, self.detallemodeloevaluativo.decimales)
        super(EvaluacionGenericaCurso, self).save(*args, **kwargs)


class AlumnosPracticaMateria(ModeloBase):
    profesor = models.ForeignKey(Profesor, verbose_name=u'Profesor', on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, verbose_name=u'Materia', on_delete=models.CASCADE)
    materiaasignada = models.ForeignKey(MateriaAsignada, verbose_name=u'Participante', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('profesor', 'materiaasignada',)




class ProfesorDistributivoHoras(ModeloBase):
    periodo = models.ForeignKey(Periodo, verbose_name=u"Período", on_delete=models.CASCADE)
    profesor = models.ForeignKey(Profesor, verbose_name=u'Profesor', on_delete=models.CASCADE)
    dedicacion = models.ForeignKey(TiempoDedicacionDocente, blank=True, null=True, verbose_name=u"Dedicación", on_delete=models.CASCADE)
    coordinacion = models.ForeignKey(Coordinacion, blank=True, null=True, verbose_name=u"Coordinación", on_delete=models.CASCADE)
    horas = models.FloatField(default=0, verbose_name=u'Horas docencia')
    horasdocencia = models.FloatField(default=0, verbose_name=u'Horas docencia')
    horasinvestigacion = models.FloatField(default=0, verbose_name=u'Horas investigación')
    horasgestion = models.FloatField(default=0, verbose_name=u'Horas gestion')
    horasvinculacion = models.FloatField(default=0, verbose_name=u'Horas vinculacion')
    salario = models.FloatField(default=0, verbose_name=u'Salario')
    evaluacionmanual = models.BooleanField(default=False)
    calificacionfinal = models.FloatField(default=0, verbose_name=u'Calificacion final')
    aprobadofinanciero = models.BooleanField(default=False)
    fechaaprobadofinanciero = models.DateTimeField(null=True, verbose_name=u'Fecha aprobado financiero')
    aprobadodecano = models.BooleanField(default=False)
    fechaaprobadodecano = models.DateTimeField(null=True, verbose_name=u'Fecha aprobado decano')
    codigocontrato = models.CharField(default='', max_length=50, verbose_name=u"Contrato")
    fechacontrato = models.DateField(null=True, verbose_name=u'Fecha contrato')
    carrera = models.ForeignKey(Carrera, blank=True, null=True, verbose_name=u"Carrera", on_delete=models.CASCADE)
    modalidad = models.ForeignKey(Modalidad, blank=True, null=True, verbose_name=u"Modalidad", on_delete=models.CASCADE)
    lugarresidencia = models.TextField(default='', verbose_name=u"Lugar residencia")
    archivohorario = models.FileField(upload_to='horariodistributivo/', blank=True, null=True, verbose_name=u'Archivo')
    verificacionth = models.BooleanField(default=False)
    aprobadoth = models.BooleanField(default=False)
    fechaaprobadoth = models.DateTimeField(null=True, verbose_name=u'Fecha aprobado TH')
    bloqueado = models.BooleanField(default=False)

    def __str__(self):
        return u'%s' % self.profesor

    class Meta:
        unique_together = ('periodo', 'profesor',)

    def tiene_carrera_modalidad(self):
        return (self.carrera_id is not None and self.carrera_id > 0) and (self.modalidad_id is not None and self.modalidad_id > 0)

    def tiene_evaluaciones(self):
        return self.profesor.respuestaevaluacionacreditacion_set.filter(proceso__periodo=self.periodo).exists()

    def calcula_horas_docencia(self):
        return null_to_numeric(self.detalledistributivo_set.filter(criteriodocenciaperiodo__isnull=False).aggregate(valor=Sum('horas'))['valor'], 1)

    def calcula_horas_investigacion(self):
        return null_to_numeric(self.detalledistributivo_set.filter(criterioinvestigacionperiodo__isnull=False).aggregate(valor=Sum('horas'))['valor'], 1)

    def calcula_horas_gestion(self):
        return null_to_numeric(self.detalledistributivo_set.filter(criteriogestionperiodo__isnull=False).aggregate(valor=Sum('horas'))['valor'], 1)

    def calcula_horas_vinculacion(self):
        return null_to_numeric(self.detalledistributivo_set.filter(criteriovinculacionperiodo__isnull=False).aggregate(valor=Sum('horas'))['valor'], 1)

    def detalle_horas_docencia(self):
        return self.detalledistributivo_set.filter(criteriodocenciaperiodo__isnull=False)

    def detalle_horas_docencia_especifico(self, sede, carrera, modalidad):
        return self.detalledistributivo_set.filter(criteriodocenciaperiodo__isnull=False, carreradetalledistributivo__sede=sede, carreradetalledistributivo__carrera=carrera, carreradetalledistributivo__modalidad=modalidad).distinct()

    def detalle_horas_investigacion(self):
        return self.detalledistributivo_set.filter(criterioinvestigacionperiodo__isnull=False)

    def detalle_horas_investigacion_especifico(self, sede, carrera, modalidad):
        return self.detalledistributivo_set.filter(criterioinvestigacionperiodo__isnull=False, carreradetalledistributivo__sede=sede, carreradetalledistributivo__carrera=carrera, carreradetalledistributivo__modalidad=modalidad).distinct()

    def detalle_horas_gestion(self):
        return self.detalledistributivo_set.filter(criteriogestionperiodo__isnull=False)

    def detalle_horas_gestion_especifico(self, sede, carrera, modalidad):
        return self.detalledistributivo_set.filter(criteriogestionperiodo__isnull=False, carreradetalledistributivo__sede=sede, carreradetalledistributivo__carrera=carrera, carreradetalledistributivo__modalidad=modalidad).distinct()

    def detalle_horas_vinculacion(self):
        return self.detalledistributivo_set.filter(criteriovinculacionperiodo__isnull=False)

    def detalle_horas_vinculacion_especifico(self, sede, carrera, modalidad):
        return self.detalledistributivo_set.filter(criteriovinculacionperiodo__isnull=False, carreradetalledistributivo__sede=sede, carreradetalledistributivo__carrera=carrera, carreradetalledistributivo__modalidad=modalidad).distinct()

    def total_horas(self):
        return null_to_numeric(self.horasdocencia + self.horasinvestigacion + self.horasgestion + self.horasvinculacion, 1)

    def total_ponderacion_horas(self):
        return self.ponderacion_horas_docencia + self.ponderacion_horas_investigacion + self.ponderacion_horas_gestion + self.ponderacion_horas_vinculacion

    def calcular_ponderaciones(self):
        horas = self.total_horas()
        if horas:
            self.ponderacion_horas_docencia = null_to_numeric(self.horasdocencia / horas, 2)
            self.ponderacion_horas_investigacion = null_to_numeric(self.horasinvestigacion / horas, 2)
            self.ponderacion_horas_gestion = null_to_numeric(self.horasgestion / horas, 2)
            self.ponderacion_horas_vinculacion = null_to_numeric(self.horasvinculacion / horas, 2)

    def puede_modificarse(self):
        return not self.periodo.cerrado

    def resumen_evaluacion_acreditacion(self):
        if self.resumenfinalevaluacionacreditacion_set.exists():
            resumen_evaluacion = self.resumenfinalevaluacionacreditacion_set.all()[0]
        else:
            resumen_evaluacion = ResumenFinalEvaluacionAcreditacion(distributivo=self)
            resumen_evaluacion.save()
        return resumen_evaluacion

    def resumen_evaluacion_acreditacion_carrera(self, sede, carrera, modalidad):
        if ResumenFinalCarreraEvaluacionAcreditacion.objects.filter(resumenfinalevaluacionacreditacion__distributivo=self, sede=sede, carrera=carrera, modalidad=modalidad).exists():
            resumen_evaluacion = ResumenFinalCarreraEvaluacionAcreditacion.objects.filter(resumenfinalevaluacionacreditacion__distributivo=self, sede=sede, carrera=carrera, modalidad=modalidad)[0]
        else:
            resumen_evaluacion = ResumenFinalCarreraEvaluacionAcreditacion(resumenfinalevaluacionacreditacion=self.resumen_evaluacion_acreditacion(), sede=sede, carrera=carrera, modalidad=modalidad)
            resumen_evaluacion.save()
        return resumen_evaluacion

    def resumen_evaluacion_acreditacion_programa(self, programa):
        if ResumenFinalTipoProgramaEvaluacionAcreditacion.objects.filter(resumenfinalevaluacionacreditacion__distributivo=self, grupocarreraproceso=programa).exists():
            resumen_evaluacion = ResumenFinalTipoProgramaEvaluacionAcreditacion.objects.filter(resumenfinalevaluacionacreditacion__distributivo=self, grupocarreraproceso=programa)[0]
        else:
            resumen_evaluacion = ResumenFinalTipoProgramaEvaluacionAcreditacion(resumenfinalevaluacionacreditacion=self.resumen_evaluacion_acreditacion(), grupocarreraproceso=programa)
            resumen_evaluacion.save()
        return resumen_evaluacion

    def actualiza_detalle_modalidad(self):
        self.resumenmodalidad_set.all().delete()
        horas_totales = ProfesorMateria.objects.filter(profesor=self.profesor, materia__nivel__periodo=self.periodo).aggregate(total=Sum('horassemanales'))['total'] or 0

        # Calcular las horas de enseñanza de materia y el porcentaje para cada combinación de sede, programa y modalidad
        combinaciones_campus_programa_modalidad = ProfesorMateria.objects.filter(profesor=self.profesor, materia__nivel__periodo=self.periodo).values_list('materia__nivel__sede', 'materia__carrera', 'materia__nivel__modalidad').distinct()

        # Crear un conjunto con las combinaciones actuales de sede, programa y modalidad
        combinaciones_actuales = set(combinaciones_campus_programa_modalidad)

        # Eliminar objetos CarreraDetalleDistributivo para combinaciones que ya no existen
        for criterio in self.detalledistributivo_set.all():
            if criterio.es_automatico() and criterio.es_materias():
                for carreradetalle in criterio.carreradetalledistributivo_set.all():
                    combinacion_actual = (carreradetalle.sede_id, carreradetalle.carrera_id, carreradetalle.modalidad_id)
                    if combinacion_actual not in combinaciones_actuales:
                        carreradetalle.delete()

        if combinaciones_campus_programa_modalidad:
            for campus, programa, modalidad in combinaciones_campus_programa_modalidad:
                horas_materia = ProfesorMateria.objects.filter(profesor=self.profesor, materia__nivel__periodo=self.periodo, materia__nivel__sede=campus, materia__carrera=programa, materia__nivel__modalidad=modalidad).aggregate(total=Sum('horassemanales'))['total'] or 0
                porcentaje = round((horas_materia / horas_totales) * 100, 2) if horas_totales else 0

                if horas_materia > 0:
                    if horas_totales:
                        porcentaje = null_to_numeric((horas_materia / horas_totales) * 100, 2)
                    if self.resumenmodalidad_set.filter(modalidad_id=modalidad, carrera_id=programa, sede_id=campus).exists():
                        r = self.resumenmodalidad_set.filter(modalidad_id=modalidad, carrera_id=programa, sede_id=campus)[0]
                        r.porciento = porcentaje
                        r.horas = horas_materia
                        r.save()
                    else:
                        r = ResumenModalidad(distributivo=self,
                                             sede_id=campus,
                                             modalidad_id=modalidad,
                                             carrera_id=programa,
                                             porciento=porcentaje,
                                             horas=horas_materia)
                        r.save()

                # Crear o actualizar objetos CarreraDetalleDistributivo para los criterios de prácticas automáticos
                for criterio in self.detalledistributivo_set.all():
                    if criterio.es_automatico() and criterio.es_materias():
                        carreradetalle_queryset = criterio.carreradetalledistributivo_set.filter(sede_id=campus,
                                                                                                 carrera_id=programa,
                                                                                                 modalidad_id=modalidad)
                        if carreradetalle_queryset.exists():
                            carreradetalle_queryset.update(horas=horas_materia)
                        elif horas_materia > 0:
                            carreradetalle = CarreraDetalleDistributivo(criterio=criterio,
                                                                        sede_id=campus,
                                                                        carrera_id=programa,
                                                                        modalidad_id=modalidad,
                                                                        horas=horas_materia)
                            carreradetalle.save()
                        else:
                            carreradetalle_queryset.delete()
        else:
            # Eliminar objetos CarreraDetalleDistributivo para los criterios de materia automáticos
            for criterio in self.detalledistributivo_set.all():
                if criterio.es_automatico() and criterio.es_materias():
                    criterio.carreradetalledistributivo_set.all().delete()

        horas_totales_practicas = ProfesorMateriaPracticas.objects.filter(profesor=self.profesor, grupo__materia__nivel__periodo=self.periodo).aggregate(total=Sum('horassemanales'))['total'] or 0

        # Calcular las horas de prácticas y el porcentaje para cada combinación de sede, programa y modalidad
        combinaciones_campus_programa_modalidad = ProfesorMateriaPracticas.objects.filter(profesor=self.profesor, grupo__materia__nivel__periodo=self.periodo).values_list('grupo__materia__nivel__sede', 'grupo__materia__carrera', 'grupo__materia__nivel__modalidad').distinct()

        # Crear un conjunto con las combinaciones actuales de sede, programa y modalidad para prácticas
        combinaciones_actuales_practicas = set(combinaciones_campus_programa_modalidad)

        # Eliminar objetos CarreraDetalleDistributivo para combinaciones de prácticas que ya no existen
        for criterio in self.detalledistributivo_set.all():
            if criterio.es_automatico() and criterio.es_practicas():
                for carreradetalle in criterio.carreradetalledistributivo_set.all():
                    combinacion_actual = (carreradetalle.sede_id, carreradetalle.carrera_id, carreradetalle.modalidad_id)
                    if combinacion_actual not in combinaciones_actuales_practicas:
                        carreradetalle.delete()

        if combinaciones_campus_programa_modalidad:
            for campus, programa, modalidad in combinaciones_campus_programa_modalidad:
                horas_practicas = ProfesorMateriaPracticas.objects.filter(profesor=self.profesor, grupo__materia__nivel__periodo=self.periodo, grupo__materia__nivel__sede=campus, grupo__materia__carrera=programa, grupo__materia__nivel__modalidad=modalidad).aggregate(total=Sum('horassemanales'))['total'] or 0
                porcentaje = round((horas_practicas / horas_totales_practicas) * 100, 2) if horas_totales_practicas else 0

                # Crear o actualizar objetos CarreraDetalleDistributivo para los criterios de prácticas automáticos
                for criterio in self.detalledistributivo_set.all():
                    if criterio.es_automatico() and criterio.es_practicas():
                        carreradetalle_queryset = criterio.carreradetalledistributivo_set.filter(sede_id=campus,
                                                                                                 carrera_id=programa,
                                                                                                 modalidad_id=modalidad)
                        if carreradetalle_queryset.exists():
                            carreradetalle_queryset.update(horas=horas_practicas)
                        elif horas_practicas > 0:
                            carreradetalle = CarreraDetalleDistributivo(criterio=criterio,
                                                                        sede_id=campus,
                                                                        carrera_id=programa,
                                                                        modalidad_id=modalidad,
                                                                        horas=horas_practicas)
                            carreradetalle.save()
                        else:
                            carreradetalle_queryset.delete()
        else:
            # Eliminar objetos CarreraDetalleDistributivo para los criterios de prácticas automáticos
            for criterio in self.detalledistributivo_set.all():
                if criterio.es_automatico() and criterio.es_practicas():
                    criterio.carreradetalledistributivo_set.all().delete()

        self.actualizar_detalle_criterio()

    def tiene_resumen_modalidad(self):
        return self.resumenmodalidad_set.filter(horas__gt=0).exists()

    def total_salario(self):
        return null_to_numeric(ProfesorMateria.objects.filter(materia__nivel__periodo=self.periodo, profesor=self.profesor).aggregate(valor=Sum('salario'))['valor'], 2)

    def total_salario_practicas(self):
        return null_to_numeric(ProfesorMateriaPracticas.objects.filter(grupo__materia__nivel__periodo=self.periodo, profesor=self.profesor).aggregate(valor=Sum('salario'))['valor'], 2)

    def actualizar_detalle_criterio(self):
        if not self.periodo.cerrado:
            self.resumenmodalidadcriterio_set.all().delete()
            horastotales = null_to_numeric(self.total_horas())
            porcentaje = 0
            for s in Sede.objects.filter(carreradetalledistributivo__criterio__distributivo=self).distinct():
                for c in Carrera.objects.filter(carreradetalledistributivo__criterio__distributivo=self).distinct():
                    for m in Modalidad.objects.filter(carreradetalledistributivo__criterio__distributivo=self).distinct():
                        horasm = null_to_numeric(CarreraDetalleDistributivo.objects.filter(criterio__distributivo=self, modalidad=m, carrera=c, sede=s).aggregate(valor=Sum('horas'))['valor'], 1)
                        if horasm > 0:
                            if horastotales:
                                porcentaje = null_to_numeric((horasm / horastotales) * 100.0, 2)
                            if self.resumenmodalidadcriterio_set.filter(modalidad=m, carrera=c, sede=s).exists():
                                r = self.resumenmodalidadcriterio_set.filter(modalidad=m, carrera=c, sede=s)[0]
                                r.porciento = porcentaje
                                r.horas = horasm
                                r.save()
                            else:
                                r = ResumenModalidadCriterio(distributivo=self,
                                                             sede=s,
                                                             modalidad=m,
                                                             carrera=c,
                                                             porciento=porcentaje,
                                                             horas=horasm)
                                r.save()

    def resumen_modalidad_criterio(self):
        return self.resumenmodalidadcriterio_set.all().order_by('sede', 'carrera', 'modalidad')

    def respuesta_auto(self):
        return RespuestaEvaluacionAcreditacion.objects.filter(profesor=self.profesor, proceso__periodo=self.periodo, tipoinstrumento=2, carrera__id__in=[x.carrera.id for x in self.resumenmodalidadcriterio_set.all()], modalidad__id__in=[x.modalidad.id for x in self.resumenmodalidadcriterio_set.all()], sede_id__in=[x.sede.id for x in self.resumenmodalidadcriterio_set.all()]).order_by('sede', 'carrera', 'modalidad')

    def respuesta_criterios_auto(self):
        return RespuestaEvaluacionAcreditacion.objects.filter(profesor=self.profesor, proceso__periodo=self.periodo, tipoinstrumento=2).exclude(carrera__resumenmodalidadcriterio__distributivo=self, modalidad__resumenmodalidadcriterio__distributivo=self, sede__resumenmodalidadcriterio__distributivo=self).order_by('sede', 'carrera', 'modalidad')

    def respuesta_criterios_par(self):
        return RespuestaEvaluacionAcreditacion.objects.filter(profesor=self.profesor, proceso__periodo=self.periodo, tipoinstrumento=3).exclude(carrera__resumenmodalidadcriterio__distributivo=self, modalidad__resumenmodalidadcriterio__distributivo=self, sede__resumenmodalidadcriterio__distributivo=self).order_by('sede', 'carrera', 'modalidad')

    def respuesta_criterios_directivo(self):
        return RespuestaEvaluacionAcreditacion.objects.filter(profesor=self.profesor, proceso__periodo=self.periodo, tipoinstrumento=4).exclude(carrera__resumenmodalidadcriterio__distributivo=self, modalidad__resumenmodalidadcriterio__distributivo=self, sede__resumenmodalidadcriterio__distributivo=self).order_by('sede', 'carrera', 'modalidad')

    def ponderacion_horas_docencia_carrera(self, sede, carrera, modalidad):
        return null_to_numeric(CarreraDetalleDistributivo.objects.filter(criterio__criteriodocenciaperiodo__isnull=False, criterio__distributivo__periodo=self.periodo, sede=sede, carrera=carrera, modalidad=modalidad, criterio__distributivo=self).aggregate(valor=Sum('horas'))['valor'], 2)

    def ponderacion_horas_investigacion_carrera(self, sede, carrera, modalidad):
        return null_to_numeric(CarreraDetalleDistributivo.objects.filter(criterio__criterioinvestigacionperiodo__isnull=False, criterio__distributivo__periodo=self.periodo, sede=sede, carrera=carrera, modalidad=modalidad, criterio__distributivo=self).aggregate(valor=Sum('horas'))['valor'], 2)

    def ponderacion_horas_gestion_carrera(self, sede, carrera, modalidad):
        return null_to_numeric(CarreraDetalleDistributivo.objects.filter(criterio__criteriogestionperiodo__isnull=False, criterio__distributivo__periodo=self.periodo, sede=sede, carrera=carrera, modalidad=modalidad, criterio__distributivo=self).aggregate(valor=Sum('horas'))['valor'], 2)

    def ponderacion_horas_vinculacion_carrera(self, sede, carrera, modalidad):
        return null_to_numeric(CarreraDetalleDistributivo.objects.filter(criterio__criteriovinculacionperiodo__isnull=False, criterio__distributivo__periodo=self.periodo, sede=sede, carrera=carrera, modalidad=modalidad, criterio__distributivo=self).aggregate(valor=Sum('horas'))['valor'], 2)

    def ponderacion_horas_docencia_programa(self, grupo):
        return null_to_numeric(CarreraDetalleDistributivo.objects.filter(criterio__criteriodocenciaperiodo__isnull=False, criterio__distributivo__periodo=self.periodo, carrera__in=grupo.carrera.all(), criterio__distributivo=self).aggregate(valor=Sum('horas'))['valor'], 2)

    def ponderacion_horas_investigacion_programa(self, grupo):
        return null_to_numeric(CarreraDetalleDistributivo.objects.filter(criterio__criterioinvestigacionperiodo__isnull=False, criterio__distributivo__periodo=self.periodo, carrera__in=grupo.carrera.all(),  criterio__distributivo=self).aggregate(valor=Sum('horas'))['valor'], 2)

    def ponderacion_horas_gestion_programa(self, grupo):
        return null_to_numeric(CarreraDetalleDistributivo.objects.filter(criterio__criteriogestionperiodo__isnull=False, criterio__distributivo__periodo=self.periodo, carrera__in=grupo.carrera.all(),  criterio__distributivo=self).aggregate(valor=Sum('horas'))['valor'], 2)

    def ponderacion_horas_vinculacion_programa(self, grupo):
        return null_to_numeric(CarreraDetalleDistributivo.objects.filter(criterio__criteriovinculacionperiodo__isnull=False, criterio__distributivo__periodo=self.periodo, carrera__in=grupo.carrera.all(), criterio__distributivo=self).aggregate(valor=Sum('horas'))['valor'], 2)

    def detalle_horastotales_docencia_simulacion(self):
        suma = 0
        for detalle in self.detalledistributivo_set.filter(criteriodocenciaperiodo__isnull=False):
            suma += detalle.simulador_calcular_criterios()
        return suma

    def tiene_solicitud_activa(self):
        ct = ContentType.objects.get_for_model(ProfesorDistributivoHoras)
        return SolicitudCambio.objects.filter(content_type=ct, object_id=self.id).exclude(estado=4).exists()


    def solicitud_activa(self):
        ct = ContentType.objects.get_for_model(ProfesorDistributivoHoras)
        return SolicitudCambio.objects.filter(content_type=ct, object_id=self.id).exclude(estado=4).first()

    def tiene_datos_completos(self):
        if TrabajoPersona.objects.filter(distributivo=self,persona=self.profesor.persona).exists():
            datos=TrabajoPersona.objects.filter(distributivo=self,persona=self.profesor.persona).first()
            return all([datos.distributivo is not None,
                        datos.persona is not None,
                        bool(datos.contrato.strip()) if datos.contrato else False,
                        datos.fecha is not None,
                        datos.fechafin is not None,
                        datos.campus is not None,
                        datos.nivelescalafon is not None,
                        datos.tipocontrato is not None,
                        datos.tipocontratoth is not None,
                        ])
        else:
            return False

    def save(self, *args, **kwargs):
        if self.id:
            self.horasdocencia = self.calcula_horas_docencia()
            self.horasinvestigacion = self.calcula_horas_investigacion()
            self.horasgestion = self.calcula_horas_gestion()
            self.horasvinculacion = self.calcula_horas_vinculacion()
            self.horas = self.total_horas()
            self.calcular_ponderaciones()
            if self.total_horas():
                self.salario = self.total_salario() + self.total_salario_practicas()
            self.lugarresidencia = null_to_text(self.lugarresidencia)
            self.codigocontrato = null_to_text(self.codigocontrato)
        super(ProfesorDistributivoHoras, self).save(*args, **kwargs)


class ResumenModalidad(ModeloBase):
    distributivo = models.ForeignKey(ProfesorDistributivoHoras, on_delete=models.CASCADE)
    sede = models.ForeignKey(Sede, blank=True, null=True, on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE)
    modalidad = models.ForeignKey(Modalidad, on_delete=models.CASCADE)
    porciento = models.FloatField(default=0)
    horas = models.FloatField(default=0)
    horasdedicadas = models.FloatField(default=0)

    def save(self, *args, **kwargs):
        super(ResumenModalidad, self).save(*args, **kwargs)



class DetalleDistributivo(ModeloBase):
    distributivo = models.ForeignKey(ProfesorDistributivoHoras, on_delete=models.CASCADE)
    criteriodocenciaperiodo = models.ForeignKey(CriterioDocenciaPeriodo, blank=True, null=True, on_delete=models.CASCADE)
    criterioinvestigacionperiodo = models.ForeignKey(CriterioInvestigacionPeriodo, blank=True, null=True, on_delete=models.CASCADE)
    criteriogestionperiodo = models.ForeignKey(CriterioGestionPeriodo, blank=True, null=True, on_delete=models.CASCADE)
    criteriovinculacionperiodo = models.ForeignKey(CriterioVinculacionPeriodo, blank=True, null=True, on_delete=models.CASCADE)
    horas = models.FloatField(default=0)

    def __str__(self):
        return u'%s' % self.nombre()

    class Meta:
        unique_together = ('distributivo', 'criteriodocenciaperiodo', 'criterioinvestigacionperiodo', 'criteriogestionperiodo', 'criteriovinculacionperiodo',)

    def es_criteriodocencia(self):
        if self.criteriodocenciaperiodo is not None:
            return True
        return False

    def es_criterioinvestigacion(self):
        if self.criterioinvestigacionperiodo is not None:
            return True
        return False

    def es_criteriogestion(self):
        if self.criteriogestionperiodo is not None:
            return True
        return False

    def es_criteriovinculacion(self):
        if self.criteriovinculacionperiodo is not None:
            return True
        return False

    def tiene_actividades(self):
        return self.actividaddetalledistributivo_set.exists()

    def actividades(self):
        return self.actividaddetalledistributivo_set.all()

    def cantidad_actividades(self):
        return self.actividaddetalledistributivo_set.count()

    def nombre(self):
        if self.es_criteriodocencia():
            return self.criteriodocenciaperiodo.criterio
        if self.es_criterioinvestigacion():
            return self.criterioinvestigacionperiodo.criterio
        if self.es_criteriovinculacion():
            return self.criteriovinculacionperiodo.criterio
        else:
            return self.criteriogestionperiodo.criterio

    def tipo(self):
        if self.es_criteriodocencia():
            return 1
        elif self.es_criterioinvestigacion():
            return 2
        elif self.es_criteriogestion():
            return 3
        else:
            return 4

    def total_horas(self):
        return null_to_numeric(self.actividaddetalledistributivo_set.aggregate(valor=Sum('horas'))['valor'], 1)

    def es_automatico(self):
        if self.es_criteriodocencia():
            return self.criteriodocenciaperiodo.criterio.id in [CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID, CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID, CRITERIO_HORAS_CLASE_PARCIAL_ID, CRITERIO_HORAS_CLASE_TECNICO_DOCENTE_ID, CRITERIO_PRACTICAS_TIEMPO_COMPLETO_ID, CRITERIO_PRACTICAS_MEDIO_TIEMPO_ID, CRITERIO_PRACTICAS_PARCIAL_ID, CRITERIO_PRACTICAS_TECNICO_DOCENTE_ID]
        return False

    def es_materias(self):
        if self.es_criteriodocencia():
            return self.criteriodocenciaperiodo.criterio.id in [CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID, CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID, CRITERIO_HORAS_CLASE_PARCIAL_ID, CRITERIO_HORAS_CLASE_TECNICO_DOCENTE_ID]
        return False

    def es_practicas(self):
        if self.es_criteriodocencia():
            return self.criteriodocenciaperiodo.criterio.id in [CRITERIO_PRACTICAS_TIEMPO_COMPLETO_ID, CRITERIO_PRACTICAS_MEDIO_TIEMPO_ID, CRITERIO_PRACTICAS_PARCIAL_ID, CRITERIO_PRACTICAS_TECNICO_DOCENTE_ID]
        return False

    def existe_detalle_carrera(self):
        return self.carreradetalledistributivo_set.exists()

    def horas_detalle_carrera(self):
        horas = null_to_numeric(self.carreradetalledistributivo_set.aggregate(valor=Sum('horas'))['valor'], 2)
        if horas == self.horas:
            return True
        else:
            return False

    def total_horas_detalle_carrera(self):
        return null_to_numeric(self.carreradetalledistributivo_set.aggregate(valor=Sum('horas'))['valor'], 2)

    def simulador_calcular_criterios(self):
        local_scope = {}
        logicamodelo = ""
        suma = 0
        if self.es_criteriodocencia and self.criteriodocenciaperiodo.logicamodelo:
            logicamodelo= self.criteriodocenciaperiodo.logicamodelo
            exec(logicamodelo, globals(), local_scope)
            calculo_modelo_criterios = local_scope['calculo_modelo_criterios']
            suma = calculo_modelo_criterios(self)
        return suma

    def resultado_calculo(self):
        resultado = self.simulador_calcular_criterios()
        if self.es_criteriodocencia:
            if resultado is None or not self.criteriodocenciaperiodo.logicamodelo:
                return "No aplica"
            elif resultado < self.criteriodocenciaperiodo.minimo or resultado > self.criteriodocenciaperiodo.maximo:
                return "No cumple"
            else:
                return "Cumple"
        else: ""





class Encuesta(ModeloBase):
    nombre = models.CharField(max_length=300, verbose_name=u'Nombre')
    grupos = models.ManyToManyField(Group, verbose_name=u'Grupos')
    fechainicio = models.DateField(verbose_name=u'Fecha inicio')
    fechafin = models.DateField(verbose_name=u'Fecha fin')
    activa = models.BooleanField(default=True, verbose_name=u'Activa')
    obligatoria = models.BooleanField(default=False, verbose_name=u"Obligatoria")
    informaciongeneral = models.TextField()
    egresados = models.BooleanField(default=False, verbose_name=u"Egresados")
    graduados = models.BooleanField(default=False, verbose_name=u"Graduados")
    seguimiento = models.BooleanField(default=False, verbose_name=u"Seguimiento")
    carreras = models.ManyToManyField(Carrera, verbose_name=u'Carreras')
    archivo = models.FileField(upload_to='evidenciaencuesta/%Y/%m/%d', blank=True, null=True, verbose_name=u'Evidencia Encuesta')
    practicaslaborales = models.BooleanField(default=False,null=True,blank=True, verbose_name=u"Practicas Laborales")
    soporte = models.BooleanField(default=False,null=True,blank=True, verbose_name=u"Soporte")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        ordering = ['-fechainicio', '-id']

    def grupos_encuestas(self):
        return self.grupos.all()

    def carreras_encuestasseguimiento(self):
        return self.carreras.all()

    def carreras_encuestas(self):
        return self.carreras.all()

    def respuesta_encuesta(self, persona):
        if self.respuestaencuesta_set.filter(persona=persona).exists():
            return self.respuestaencuesta_set.filter(persona=persona)[0]
        return None

    def respuesta_encuestapersona(self, encuestapersona):
        if self.respuestaencuesta_set.filter(personaencuesta=encuestapersona).exists():
            return self.respuestaencuesta_set.filter(personaencuesta=encuestapersona)[0]
        return None

    def respuesta_encuestaseguimiento(self, persona, seguimiento):
        if self.respuestaencuestaseguimiento_set.filter(persona=persona, seguimiento__id=seguimiento.id).exists():
            return self.respuestaencuestaseguimiento_set.filter(persona=persona, seguimiento__id=seguimiento.id)[0]
        return None

    def cantidad_respuesta(self):
        return self.respuestaencuesta_set.count()

    def puede_responderse(self):
        return self.fechainicio <= datetime.now().date() <= self.fechafin and self.activa

    def cantidad_encuestado(self):
        if self.personaencuesta_set.exists():
            return self.personaencuesta_set.count()
        return User.objects.filter(groups__in=self.grupos.all()).distinct().count()

    def cantidad_encuestado_lista(self):
        return self.personaencuesta_set.count()

    def finalizo(self):
        return datetime.now().date() > self.fechafin

    def puede_activarse(self):
        if not GrupoPreguntaEncuesta.objects.filter(encuesta=self).exists():
            return False
        for grupo in GrupoPreguntaEncuesta.objects.filter(encuesta=self):
            if not grupo.preguntaencuesta_set.exists():
                return False
            for pregunta in grupo.preguntaencuesta_set.exclude(tiposeleccion__id__in=[TIPO_RESPUESTA_ENCUESTA_TEXTO_ID, TIPO_RESPUESTA_ENCUESTA_FECHA_ID]):
                if not pregunta.tiporespuestaencuesta_set.exists():
                    return False
        return True

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.informaciongeneral = null_to_text(self.informaciongeneral)
        super(Encuesta, self).save(*args, **kwargs)

class GrupoPreguntaEncuesta(ModeloBase):
    encuesta = models.ForeignKey(Encuesta, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=300, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    def preguntas(self):
        return self.preguntaencuesta_set.all().order_by('numero')

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(GrupoPreguntaEncuesta, self).save(*args, **kwargs)


class TipoSeleccionPreguntaEncuesta(ModeloBase):
    nombre = models.CharField(max_length=300, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipo seleccion encuesta"

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoSeleccionPreguntaEncuesta, self).save(*args, **kwargs)


class PreguntaEncuesta(ModeloBase):
    numero = models.IntegerField(default=0)
    grupopreguntaencuesta = models.ForeignKey(GrupoPreguntaEncuesta, on_delete=models.CASCADE)
    tiposeleccion = models.ForeignKey(TipoSeleccionPreguntaEncuesta, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=300, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % (self.nombre)

    def respuestas(self):
        return self.tiporespuestaencuesta_set.all().order_by('id')

    def cantidad_misma_respuesta(self, respuesta):
        return self.detallerespuesencuesta_set.filter(tiporespuestaencuesta=respuesta).count()

    def cantidad_misma_respuesta_seguimiento(self, respuesta):
        return self.detallerespuesencuestaseguimiento_set.filter(tiporespuestaencuesta=respuesta).count()

    def mi_detalle_respuesta(self):
        if self.detallerespuesencuesta_set.exists():
            return self.detallerespuesencuesta_set.all()[0]
        return None

    def mi_respuesta(self):
        if self.detallerespuesencuesta_set.exists():
            return self.detallerespuesencuesta_set.all()[0].tiporespuestaencuesta
        return None

    def respuesta_pregunta_persona(self, respuesta):
        if self.detallerespuesencuesta_set.filter(respuestaencuesta=respuesta).exists():
            return self.detallerespuesencuesta_set.filter(respuestaencuesta=respuesta).all()[0]
        return None

    def respuesta_pregunta_persona_seguimiento(self, respuesta):
        if self.detallerespuesencuestaseguimiento_set.filter(respuestaencuesta=respuesta).exists():
            return self.detallerespuesencuestaseguimiento_set.filter(respuestaencuesta=respuesta).all()[0]
        return None

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(PreguntaEncuesta, self).save(*args, **kwargs)


class TipoRespuestaEncuesta(ModeloBase):
    preguntaencuesta = models.ForeignKey(PreguntaEncuesta, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=300, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s ' % (self.nombre)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoRespuestaEncuesta, self).save(*args, **kwargs)



class PersonaEncuesta(ModeloBase):
    encuesta = models.ForeignKey(Encuesta, on_delete=models.CASCADE)
    persona = models.ForeignKey(Persona, blank=True, null=True, on_delete=models.CASCADE)
    externo = models.BooleanField(default=False)
    nombre = models.CharField(default='', blank=True, max_length=300, verbose_name=u"Nombre")
    email = models.CharField(default='', max_length=200, verbose_name=u"Correo electrónico personal")

    def respondio_encuesta(self):
        return self.encuesta.respuestaencuesta_set.filter(Q(persona=self.persona) | Q(personaencuesta=self)).exists()

    def respuesta_encuesta(self):
        if self.respondio_encuesta():
            return self.encuesta.respuestaencuesta_set.filter(Q(persona=self.persona) | Q(personaencuesta=self))[0]
        return 0

    def respuesta_encuestaseg(self):
        if self.respondio_encuesta():
            return self.encuesta.respuestaencuestaseguimiento_set.filter(Q(persona=self.persona) | Q(personaencuesta=self))[0]
        return 0

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.email = null_to_text(self.email, lower=True)
        super(PersonaEncuesta, self).save(*args, **kwargs)


class RespuestaEncuesta(ModeloBase):
    encuesta = models.ForeignKey(Encuesta, on_delete=models.CASCADE)
    fecha = models.DateField()
    persona = models.ForeignKey(Persona, blank=True, null=True, on_delete=models.CASCADE)
    personaencuesta = models.ForeignKey(PersonaEncuesta, blank=True, null=True, on_delete=models.CASCADE)
    inscripcion = models.ForeignKey(Inscripcion, blank=True, null=True, on_delete=models.CASCADE)
    nivelmalla = models.ForeignKey(NivelMalla, blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('encuesta', 'persona',)


class DetalleRespuesEncuesta(ModeloBase):
    respuestaencuesta = models.ForeignKey(RespuestaEncuesta, on_delete=models.CASCADE)
    preguntaencuesta = models.ForeignKey(PreguntaEncuesta, on_delete=models.CASCADE)
    tiporespuestaencuesta = models.ForeignKey(TipoRespuestaEncuesta, blank=True, null=True, on_delete=models.CASCADE)
    respuesta = models.TextField(blank=True, null=True)
    fecha = models.DateField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.respuesta:
            self.respuesta = null_to_text(self.respuesta, transform=False)
        super(DetalleRespuesEncuesta, self).save(*args, **kwargs)



class TipoActividad(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    representacion = models.CharField(default='', max_length=6, verbose_name=u'Código')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de actividades"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        self.representacion = null_to_text(self.representacion)
        super(TipoActividad, self).save(*args, **kwargs)


class Actividad(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    inicio = models.DateField(verbose_name=u'Fecha inicio')
    fin = models.DateField(verbose_name=u'Fecha fin')
    tipo = models.ForeignKey(TipoActividad, verbose_name=u'Tipo', on_delete=models.CASCADE)
    lunes = models.BooleanField(default=False, verbose_name=u'Lunes')
    martes = models.BooleanField(default=False, verbose_name=u'Martes')
    miercoles = models.BooleanField(default=False, verbose_name=u'Miercoles')
    jueves = models.BooleanField(default=False, verbose_name=u'Jueves')
    viernes = models.BooleanField(default=False, verbose_name=u'Viernes')
    sabado = models.BooleanField(default=False, verbose_name=u'Sabado')
    domingo = models.BooleanField(default=False, verbose_name=u'Domingo')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Actividades"
        ordering = ['-inicio']
        unique_together = ('nombre', 'inicio', 'fin',)

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(Actividad, self).save(*args, **kwargs)

class SilaboAsignaturaMalla(ModeloBase):
    asignaturamalla = models.ForeignKey(AsignaturaMalla, verbose_name=u'Asignatura malla', on_delete=models.CASCADE)
    planificacionmateria = models.ForeignKey(PlanificacionMateria, verbose_name=u'Taller Materia', on_delete=models.CASCADE)
    habilitado = models.BooleanField(default=False)
    fecha = models.DateField(verbose_name=u'fecha', blank=True, null=True)
    persona = models.ForeignKey(Persona, verbose_name=u'Persona', blank=True, null=True, on_delete=models.CASCADE)

class NivelExtension(ModeloBase):
    nivel = models.ForeignKey(Nivel, verbose_name=u'Nivel', on_delete=models.CASCADE)
    modificarcupo = models.BooleanField(default=True, verbose_name=u'Cupo Materia')
    modificarhorario = models.BooleanField(default=True, verbose_name=u'Horario Visible')
    modificardocente = models.BooleanField(default=True, verbose_name=u'Modificar docente')
    modificarplanificacion = models.BooleanField(default=True, verbose_name=u'Modificar planificacion')

    class Meta:
        unique_together = ('nivel',)


class Graduado(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u"Inscripción", on_delete=models.CASCADE)
    rector = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u"Rector", on_delete=models.CASCADE)
    fechagraduado = models.DateField(verbose_name=u"Fecha de acta de grado")
    numeroactagrado = models.CharField(default='', max_length=50, verbose_name=u"Numero acta de grado")
    duracion = models.FloatField(default=0, verbose_name=u"Duracion")
    fecharefrendacion = models.DateField(verbose_name=u"Fecha de refrendación")
    numerorefrendacion = models.CharField(default='', max_length=50, verbose_name=u"Numero de refrendación")
    notatrabajotitulacion = models.FloatField(default=0, verbose_name=u"Nota de trabajo titulacion")
    promediotitulacion = models.FloatField(default=0, verbose_name=u"Nota de sustentación")
    registro = models.CharField(default='', max_length=50, verbose_name=u'Registro senescyt')
    observaciones = models.TextField(default='', verbose_name=u'Observaciones')
    linktesis = models.TextField(default='', verbose_name=u'Link tesis')
    nombreimpresion = models.TextField(default='', verbose_name=u'Nombres impresión titúlo')
    numerofolio = models.TextField(default='', max_length=50, verbose_name=u'Numero Folio')
    codigotitulo = models.TextField(default='', max_length=50, verbose_name=u'Codigo Titulo')

    def __str__(self):
        return u'%s [graduado]' % self.inscripcion

    class Meta:
        verbose_name_plural = u"Alumnos graduados"
        unique_together = ('inscripcion',)

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("Graduado.objects.filter(Q(inscripcion__persona__nombre1__contains='%s') | Q(inscripcion__persona__nombre2__contains='%s') | Q(inscripcion__persona__apellido1__contains='%s') | Q(inscripcion__persona__apellido2__contains='%s') | Q(inscripcion__persona__cedula__contains='%s') | Q(id=id_search('%s')))" % (q, q, q, q, q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return (self.inscripcion.persona.cedula if self.inscripcion.persona.cedula else self.inscripcion.persona.pasaporte) + " - " + self.inscripcion.persona.nombre_completo_inverso() + " - " + self.inscripcion.carrera.nombre + ' - ' + str(self.id)

    def seguimientos(self):
        return self.inscripcion.persona.trabajopersona_set.all()

    def reconocimiento_estudios(self):
        if not self.tiporeconocimientograduado_set.exists():
            c = None
            if ConvalidacionInscripcion.objects.filter(record__convalidacion=True, record__inscripcion__graduado=self).exists():
                c = ConvalidacionInscripcion.objects.filter(record__convalidacion=True, record__inscripcion__graduado=self)[0]
            tr = TipoReconocimientoGraduado(graduado=self,
                                            tiporeconocimiento=c.tiporeconocimiento if c else None,
                                            tiemporeconocimiento=c.tiemporeconocimiento if c else 0,
                                            institucion=c.institucion if c else None,
                                            carrera=c.carrera if c else '')
            tr.save()
        else:
            tr = self.tiporeconocimientograduado_set.all()[0]
        return tr

    def save(self, *args, **kwargs):
        self.observaciones = null_to_text(self.observaciones)
        self.registro = null_to_text(self.registro)
        self.numeroactagrado = null_to_text(self.numeroactagrado)
        self.numerorefrendacion = null_to_text(self.numerorefrendacion)
        self.nombreimpresion = null_to_text(self.nombreimpresion)
        self.numerofolio = null_to_text(self.numerofolio)
        self.codigotitulo = null_to_text(self.codigotitulo)
        super(Graduado, self).save(*args, **kwargs)


class ValoracionCalificacion(ModeloBase):
    categoria = models.CharField(max_length=100)
    nominacion = models.CharField(max_length=5)
    inicio = models.FloatField(default=0)
    fin = models.FloatField(default=0)

    class Meta:
        verbose_name_plural = u'Tabla valorativa de calificaciones'
        ordering = ['-inicio']
        unique_together = ('nominacion', 'categoria')

    def __str__(self):
        return self.categoria + ' (' + self.nominacion + ') Rango: De ' + str(self.inicio) + ' a ' + str(self.fin)

    def nombre_corto(self):
        return self.categoria + ' (' + self.nominacion + ')'

    def save(self, *args, **kwargs):
        self.categoria = null_to_text(self.categoria)
        self.nominacion = null_to_text(self.nominacion)
        super(ValoracionCalificacion, self).save(*args, **kwargs)


class DocumentosDeInscripcion(ModeloBase):
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    pre = models.BooleanField(default=False, verbose_name=u'Pre nivelación')
    observaciones_pre = models.CharField(default='', max_length=100, verbose_name=u'Observaciones')
    homologar = models.BooleanField(default=False, verbose_name=u"Homologa materias")
    titulo = models.BooleanField(default=False, verbose_name=u'Titulo')
    cedula = models.BooleanField(default=False, verbose_name=u'Cedula')
    votacion = models.BooleanField(default=False, verbose_name=u'Certificado de votación')
    fotos = models.BooleanField(default=False, verbose_name=u'Fotos')
    cert_med = models.BooleanField(default=False, verbose_name=u'Certificado médico')
    reingreso = models.BooleanField(default=False, verbose_name=u"Reingreso")
    eshomologacionexterna = models.BooleanField(default=False, verbose_name=u"Homologación Externa")
    conveniohomologacion = models.BooleanField(default=False, verbose_name=u"Convenio por Homologación")
    reconocimientointerno = models.BooleanField(default=False, verbose_name=u"Reconocimiento Interno")

    def __str__(self):
        return u'%s' % self.inscripcion

    class Meta:
        verbose_name_plural = u"Documentos de inscripciones"
        unique_together = ('inscripcion',)

    def save(self, *args, **kwargs):
        self.observaciones_pre = null_to_text(self.observaciones_pre)
        super(DocumentosDeInscripcion, self).save(*args, **kwargs)



class TipoDocumentoInscripcion(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    estado = models.BooleanField(default=False, verbose_name=u'estado')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name_plural = u"Tipos de documentos de inscripcion"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def existedocumento(self,inscripcion):
        if ArchivoDocumentoInscripcion.objects.filter(tipodocumentoinscripcion=self, inscripcion=inscripcion).exists():
            return ArchivoDocumentoInscripcion.objects.filter(tipodocumentoinscripcion=self, inscripcion=inscripcion)[0]
        else:
            return False

    def save(self, *args, **kwargs):
        self.nombre = null_to_text(self.nombre)
        super(TipoDocumentoInscripcion, self).save(*args, **kwargs)

class ArchivoDocumentoInscripcion(ModeloBase):
    tipodocumentoinscripcion = models.ForeignKey(TipoDocumentoInscripcion, blank=True, null=True, verbose_name=u'Tipo documento inscripcion', on_delete=models.CASCADE)
    fecha = models.DateTimeField(verbose_name=u'Fecha')
    inscripcion = models.ForeignKey(Inscripcion, blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='documentos/%Y/%m/%d', verbose_name=u'Archivo')
    observaciones = models.TextField(default='', blank=True, null=True, verbose_name=u'Observaciones')

    def __str__(self):
        return u'%s' % self.tipodocumentoinscripcion

    class Meta:
        verbose_name_plural = u"Archivos"

    def save(self, *args, **kwargs):
        self.observaciones = null_to_text(self.observaciones)
        super(ArchivoDocumentoInscripcion, self).save(*args, **kwargs)

class MateriasCompartidas(ModeloBase):
    materia = models.ForeignKey(Materia, verbose_name=u"Materia", on_delete=models.CASCADE)
    sede = models.ForeignKey(Sede, verbose_name=u'Sede', on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, blank=True, null=True, verbose_name=u'Carrera', on_delete=models.CASCADE)
    modalidad = models.ForeignKey(Modalidad, blank=True, null=True, verbose_name=u'Modalidad', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s - %s' % (self.sede, self.carrera, self.modalidad)

    class Meta:
        verbose_name_plural = u"Materias compartidas"

    @staticmethod
    def flexbox_query(q, filtro=None, exclude=None, cantidad=None):
        return eval(("MateriasCompartidas.objects.filter(Q(materia__contains='%s') | Q(id=id_search('%s')))" % (q, q)) + (".filter(%s)" % filtro if filtro else "") + (".exclude(%s)" % exclude if exclude else "") + (".distinct()") + ("[:%s]" % cantidad if cantidad else ""))

    def flexbox_repr(self):
        return self.materia.asignatura.nombre + ' - ' + str(self.id)



class PreciosPeriodoModulosInscripcion(ModeloBase):
    periodo = models.ForeignKey(Periodo, verbose_name=u'Periodo', on_delete=models.CASCADE)
    sede = models.ForeignKey(Sede, verbose_name=u'Sede', on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, blank=True, null=True, verbose_name=u'Carrera', on_delete=models.CASCADE)
    modalidad = models.ForeignKey(Modalidad, blank=True, null=True, verbose_name=u'Modalidad', on_delete=models.CASCADE)
    malla = models.ForeignKey(Malla, blank=True, null=True, verbose_name=u'Malla', on_delete=models.CASCADE)
    cortes = models.ForeignKey(Nivel, blank=True, null=True, verbose_name=u'Nivel Cortes', on_delete=models.CASCADE)
    precioinscripcion = models.FloatField(default=0, verbose_name=u"Precio inscripcion")
    preciohomologacion = models.FloatField(default=0, verbose_name=u"Precio homologacion")
    preciohomologacionconvenio = models.FloatField(default=0, verbose_name=u"Precio homologacion convenio")
    precioredmaestros = models.FloatField(default=0, verbose_name=u"Precio maestros")
    preciomodulo = models.FloatField(default=0, verbose_name=u"Precio modulo")
    porcentajesegundamatricula = models.IntegerField(default=0, verbose_name=u"Precio modulo")
    porcentajeterceramatricula = models.IntegerField(default=0, verbose_name=u"Precio modulo")
    porcentajematriculaextraordinaria = models.IntegerField(default=0, verbose_name=u"Precio modulo")
    precioinduccion = models.FloatField(default=0, verbose_name=u"Precio inducción")
    precioreingreso = models.FloatField(default=0, verbose_name=u"Precio reingreso")
    preciotitulacion = models.FloatField(default=0, verbose_name=u"Precio titulación")
    precioadelantoidiomas = models.FloatField(default=0, verbose_name=u"Precio adelanto idiomas")
    precioarrastremodulo = models.FloatField(default=0, verbose_name=u"Precio arrastre modulo")
    clonado = models.BooleanField(default=False, verbose_name=u'Clonado')
    sininscripcion = models.BooleanField(default=False, verbose_name=u'Sin inscripción')
    tipocalculo = models.IntegerField(choices=TIPO_CALCULO_MALLAS, default=1, verbose_name=u"Tipo calculo")

    def __str__(self):
        return u'%s - %s - %s - %s - %s - %s - %s - %s - %s - %s - %s - %s - %s - %s - %s' % (self.periodo, self.sede, self.carrera, self.modalidad, self.precioinscripcion, self.preciohomologacion, self.preciohomologacionconvenio, self.precioredmaestros, self.preciomodulo, self.precioarrastremodulo, self.porcentajesegundamatricula, self.porcentajeterceramatricula, self.porcentajematriculaextraordinaria, self.preciotitulacion, self.precioadelantoidiomas)

    def en_uso_periodo(self):
        if Materia.objects.filter(Q(asignaturamalla__malla__carrera=self.carrera, asignaturamalla__malla__modalidad=self.modalidad), nivel__sede=self.sede, nivel__periodo=self.periodo).exists():
            return True
        elif Matricula.objects.filter(inscripcion__carrera=self.carrera, inscripcion__modalidad=self.modalidad, inscripcion__sede=self.sede, nivel__periodo=self.periodo).exists():
            return True
        return False

    def tiene_valor_adelanto_idiomas(self):
        costoadelantoidiomas = self.objects.filter(nivel__periodo=self.periodo, nivel__sede=self.sede, asignaturamalla__malla__carrera=self.carrera, asignaturamalla__malla__modalidad=self.modalidad)
        return costoadelantoidiomas
    #
    # class Meta:
    #     unique_together = ('periodo', 'sede', 'malla')


class TipoCostoCursoPeriodo(ModeloBase):
    periodo = models.ForeignKey(Periodo, verbose_name=u'Periodo', on_delete=models.CASCADE)
    sede = models.ForeignKey(Sede, verbose_name=u'Sede', on_delete=models.CASCADE)
    tipocostocurso = models.ForeignKey(TipoCostoCurso, blank=True, null=True, verbose_name=u'Tipo Costo Curso', on_delete=models.CASCADE)
    costomatricula = models.FloatField(default=0, verbose_name=u'Costo de matrícula')
    costocuota = models.FloatField(default=0, verbose_name=u'Costo arancel')
    cuotas = models.IntegerField(default=1, verbose_name=u'Número de cuotas')
    activo = models.BooleanField(default=True, verbose_name=u"Activo")

    def mi_costo_dif(self):
        if self.costodiferenciadocursoperiodo_set.exists():
            return self.costodiferenciadocursoperiodo_set.all()[0]
        return None


class CostodiferenciadoCursoPeriodo(ModeloBase):
    tipocostocursoperiodo = models.ForeignKey(TipoCostoCursoPeriodo, verbose_name=u'Curso', on_delete=models.CASCADE)
    tipo = models.ForeignKey(TipoEstudianteCurso, verbose_name=u'Tipo', on_delete=models.CASCADE)
    costomatricula = models.FloatField(default=0, verbose_name=u'Costo de matrícula')
    costocuota = models.FloatField(default=0, verbose_name=u'Costo por cuota')
    cuotas = models.IntegerField(default=0, verbose_name=u'Número de cuotas')

    def costototal(self):
        return null_to_numeric(self.costomatricula + (self.costocuota * self.cuotas), 2)

    def __str__(self):
        return u'%s' % self.tipo

    class Meta:
        verbose_name_plural = u"Tipos de costo del curso"
        ordering = ['tipo']

class ValoresMinimosPeriodoBecaMatricula(ModeloBase):
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE)
    valormatricula = models.IntegerField(blank=True, null=True, verbose_name=u"Centidad de cupo Cupo", default=0)
    activavalormatricula = models.BooleanField(default=False)
    porcentajematricula = models.IntegerField(blank=True, null=True, default=0)
    activaporcentajematricula = models.BooleanField(default=False)
    valorbeca = models.IntegerField(blank=True, null=True, default=0)
    activavalorbeca = models.BooleanField(default=False)
    porcentajebeca = models.IntegerField(blank=True, null=True, default=0)
    activaporcentajebeca = models.BooleanField(default=False)


class RubroNotaDebito(ModeloBase):
    rubro = models.ForeignKey(Rubro, verbose_name=u'Rubro', on_delete=models.CASCADE)
    motivo = models.TextField(default='', verbose_name=u'Motivo')
    factura = models.ForeignKey(Factura, null=True, blank=True, verbose_name=u'Factura', on_delete=models.CASCADE)
    anticipado = models.BooleanField(default=False)

    def __str__(self):
        return u'Rubro: %s %s' % (self.rubro.inscripcion, str(self.rubro.valor))

    class Meta:
        verbose_name_plural = u"Rubros notas de debito"
        unique_together = ('rubro',)

    def verifica_estado(self):
        if self.factura:
            if self.rubro.cancelado:
                factura = self.factura
                factura.cancelada = True
                factura.save()

    def save(self, *args, **kwargs):
        self.motivo = null_to_text(self.motivo)
        super(RubroNotaDebito, self).save(*args, **kwargs)


class RubroCursoEscuelaComplementaria(ModeloBase):
    rubro = models.ForeignKey(Rubro, on_delete=models.CASCADE)
    participante = models.ForeignKey(MatriculaCursoEscuelaComplementaria, on_delete=models.CASCADE)
    cuota = models.IntegerField(default=0, verbose_name=u'Cuota')

    def __str__(self):
        return u'Rubro: %s %s' % (self.rubro.inscripcion, str(self.rubro.valor))

    class Meta:
        verbose_name_plural = u"Rubros de cursos complementarios"
        unique_together = ('rubro',)

class TipoTerminosAcuerdos(ModeloBase):
    nombre = models.TextField(default='', blank=True, null=True, verbose_name=u"Tipo de terminos y acuerdos")
    textomostrar = models.TextField(default='', blank=True, null=True, verbose_name=u"Texto a mostrar")
    paraprofesores = models.BooleanField(default=False, verbose_name=u'Para profesores')
    paraalumnos = models.BooleanField(default=False, verbose_name=u'Para alumnos')
    paraadministrativos = models.BooleanField(default=False, verbose_name=u'Para administrativos')
    estado = models.BooleanField(default=False, verbose_name=u'Para Estado')
    archivo = models.FileField(upload_to='terminosycondiciones/%Y', blank=True, null=True, verbose_name=u'Archivo')
    url = models.TextField(default='', blank=True, null=True, verbose_name=u"Url con politicas")


class AceptacionTerminosAcuerdos(ModeloBase):
    persona = models.ForeignKey(Persona, verbose_name=u'personaaceptaterminos', on_delete=models.CASCADE)
    tipoacuerdo = models.ForeignKey(TipoTerminosAcuerdos, verbose_name=u'Tipo de terminos y acuerdos', on_delete=models.CASCADE)
    fechaaceptacion = models.DateField(default=timezone.now, blank=True, null=True, verbose_name=u'Fecha aceptacion')

class TipoServicio(ModeloBase):
    nombre = models.CharField(max_length=180)           # "Salón Ágora", "Lab Materiales"

    def __str__(self):
        return self.nombre

class EspacioFisico(ModeloBase):
    codigo = models.CharField(max_length=20, unique=True)  # AGORA, LAB_MAT, etc.
    nombre = models.CharField(max_length=150)              # "Salón Ágora", "Lab Materiales"
    descripcion = models.TextField(blank=True)
    tipo_servicio = models.ForeignKey(TipoServicio, blank=True, null=True,verbose_name=u'tiposervicio', on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre

class ServicioCatalogo(ModeloBase):
    class TipoCobro(models.IntegerChoices):
        POR_ITEM = 1, "Por ítem (muestra / pieza / ensayo / paquete)"
        POR_HORA = 2, "Por hora"

    espacio_fisico = models.ForeignKey(EspacioFisico, on_delete=models.PROTECT, related_name="servicios", verbose_name="Laboratorio / Área")
    nombre = models.TextField()  # descripción larga del ítem
    tipo_cobro = models.PositiveSmallIntegerField(choices=TipoCobro.choices, default=TipoCobro.POR_ITEM)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)
    observacion = models.TextField(blank=True)

    def __str__(self):
        txt = (self.nombre or "").strip()
        return (txt[:80] + "…") if len(txt) > 80 else txt


class RequerimientoServicio(ModeloBase):
    class Estado(models.IntegerChoices):
        RECIBIDO         = 1, "Recibido"
        EN_PROFORMA      = 2, "Proforma en elaboración"
        PROFORMA_ENVIADA = 3, "Proforma enviada al cliente"
        CERRADO          = 4, "Cerrado"

    cliente = models.ForeignKey(Cliente, null=True, blank=True, on_delete=models.SET_NULL, related_name="requerimientos")
    nombre_contacto = models.CharField(max_length=255)
    email_contacto = models.EmailField()
    telefono_contacto = models.CharField(max_length=50, blank=True)
    espacio_fisico = models.ForeignKey(EspacioFisico, null=True, blank=True, on_delete=models.SET_NULL, related_name="requerimientos")
    descripcion = models.TextField()
    archivo = models.FileField(upload_to="requerimientos/", blank=True)

    estado = models.PositiveSmallIntegerField(
        choices=Estado.choices,
        default=Estado.RECIBIDO
    )

    fecha_recepcion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Req #{self.id} - {self.nombre_contacto}"


class Proforma(ModeloBase):
    class Estado(models.IntegerChoices):
        BORRADOR  = 1, "Borrador"
        ENVIADA   = 2, "Enviada"
        APROBADA  = 3, "Aprobada"
        RECHAZADA = 4, "Rechazada"

    numero = models.CharField(max_length=30, unique=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="proformas")
    estado = models.PositiveSmallIntegerField(choices=Estado.choices, default=Estado.BORRADOR)
    iva = models.ForeignKey(IvaAplicado, verbose_name="IVA", on_delete=models.PROTECT, null=True, blank=True,)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    impuestos = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    observaciones = models.TextField(blank=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey('ctt.Persona', null=True, blank=True, on_delete=models.SET_NULL, related_name="proformas_creadas")

    requerimiento = models.ForeignKey(
        RequerimientoServicio,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='proformas'
    )

    def tiene_rubro(self):
        return bool(getattr(self, 'rubro_servicio', None))

    def rubro_pagado(self):
        rs = getattr(self, 'rubro_servicio', None)
        if not rs or not getattr(rs, 'rubro', None):
            return False
        return bool(rs.rubro.cancelado)

    def recomputar_totales(self):
        detalles = self.detalles.all()

        # Subtotal = suma de subtotales de detalles
        sub = sum((d.subtotal for d in detalles), Decimal('0.00'))
        self.subtotal = sub.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Aseguramos descuento como Decimal
        descuento = self.descuento or Decimal('0.00')

        # Base imponible = subtotal - descuento (no negativa)
        base_imponible = (self.subtotal - descuento).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )
        if base_imponible < 0:
            base_imponible = Decimal('0.00')

        # porcientoiva viene como 0.15 (equivale a 15%)
        if self.iva and self.iva.porcientoiva is not None:
            porcentaje = Decimal(str(self.iva.porcientoiva))  # 0.15
        else:
            porcentaje = Decimal('0.00')

        # impuestos = base * porcentaje  (ya NO se divide para 100)
        self.impuestos = (base_imponible * porcentaje).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )

        # Total final
        self.total = (base_imponible + self.impuestos).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )


    def enviar_al_cliente(self, actor_persona=None):
        estado_anterior = self.estado
        # recalcula totales antes de enviar
        self.recomputar_totales()
        self.estado = self.Estado.ENVIADA
        self.fecha_envio = timezone.now()
        self.save()

        self.registrar_evento(
            tipo=ProformaHistorial.TipoEvento.ENVIO,
            mensaje="Proforma enviada al cliente.",
            actor_persona=actor_persona,
            estado_anterior=estado_anterior,
            estado_nuevo=self.estado,
        )

    def registrar_evento(self, tipo, mensaje="", actor_persona=None, actor_externo="", estado_anterior=None,
                         estado_nuevo=None):
        from .models import ProformaHistorial  # o ajusta el import según tu estructura

        ProformaHistorial.objects.create(
            proforma=self,
            tipo=tipo,
            mensaje=mensaje,
            actor_persona=actor_persona,
            actor_externo=actor_externo,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
        )

    def __str__(self): return f"Proforma {self.numero}"


class ProformaDetalle(ModeloBase):
    proforma = models.ForeignKey(Proforma, related_name='detalles', on_delete=models.CASCADE)
    servicio = models.ForeignKey(ServicioCatalogo, on_delete=models.PROTECT)
    descripcion = models.CharField(max_length=255, blank=True)

    cantidad = models.DecimalField(max_digits=8, decimal_places=2, default=1)

    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        if not self.precio_unitario:
            self.precio_unitario = self.servicio.precio_base

        # cantidad = piezas / ensayos (POR_ITEM) o horas (POR_HORA)
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.servicio.nombre} x {self.cantidad}"


class RevisionProforma(ModeloBase):
    proforma = models.OneToOneField(Proforma, on_delete=models.CASCADE, related_name="revision")
    revisado_por = models.ForeignKey('Persona', on_delete=models.PROTECT, related_name="proformas_revisadas")
    cumple = models.BooleanField()
    comentarios = models.TextField(blank=True)

class SolicitudTrabajo(ModeloBase):
    class Estado(models.IntegerChoices):
        PEND_PAGO = 1, "Pendiente de pago"
        PAGADA    = 2, "Pagada"
        EN_PROCESO= 3, "En proceso"
        ENTREGADA = 4, "Entregada"
        CERRADA   = 5, "Cerrada"
        NO_CUMPLE = 6, "No cumplimiento"

    proforma = models.OneToOneField(Proforma, on_delete=models.PROTECT, related_name="solicitud_trabajo")
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    estado = models.PositiveSmallIntegerField(choices=Estado.choices, default=Estado.PEND_PAGO)

    def __str__(self):
        return f"Solicitud #{self.pk} - {self.cliente} - {self.get_estado_display()}"

class FacturaItem(ModeloBase):
    factura = models.ForeignKey('Factura', related_name="items", on_delete=models.CASCADE)
    descripcion = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2,
                                   validators=[MinValueValidator(Decimal("0.01"))])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def total(self): return self.cantidad * self.precio_unitario


class Trabajo(ModeloBase):
    solicitud = models.OneToOneField(SolicitudTrabajo, related_name="trabajo", on_delete=models.PROTECT)
    responsable = models.ForeignKey('Persona', on_delete=models.PROTECT, related_name="trabajos_asignados")
    descripcion = models.TextField(blank=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

class EntregaResultado(ModeloBase):
    trabajo = models.OneToOneField(Trabajo, related_name="entrega", on_delete=models.PROTECT)
    recibido_por = models.CharField(max_length=255)
    observaciones = models.TextField(blank=True)
    archivo = models.FileField(upload_to="resultados/", blank=True)
    fecha_entrega = models.DateTimeField(auto_now_add=True)

class InformeNoCumplimiento(ModeloBase):
    proforma = models.ForeignKey(Proforma, on_delete=models.PROTECT, related_name="informes_no_cumplimiento")
    descripcion = models.TextField()
    adjunto = models.FileField(upload_to="no_cumple/", blank=True)

class ProformaHistorial(ModeloBase):
    class TipoEvento(models.IntegerChoices):
        CREACION   = 1, "Creación"
        EDICION    = 2, "Edición"
        ENVIO      = 3, "Envío al cliente"
        APROBACION = 4, "Aprobación del cliente"
        RECHAZO    = 5, "Rechazo del cliente"
        COMENTARIO = 6, "Comentario / observación"

    proforma = models.ForeignKey(
        Proforma,
        related_name="historial",
        on_delete=models.CASCADE
    )

    tipo = models.PositiveSmallIntegerField(choices=TipoEvento.choices)
    fecha = models.DateTimeField(default=timezone.now)

    # Quién hizo la acción
    actor_persona = models.ForeignKey('ctt.Persona', null=True, blank=True, on_delete=models.SET_NULL, related_name="eventos_proforma")
    actor_externo = models.CharField(max_length=255, blank=True, help_text="Nombre o referencia del cliente externo si no está logueado.")

    estado_anterior = models.PositiveSmallIntegerField(null=True, blank=True)
    estado_nuevo = models.PositiveSmallIntegerField(null=True, blank=True)

    mensaje = models.TextField(blank=True)  # aquí va el “por qué”, comentario, etc.

    def __str__(self):
        return f"[{self.get_tipo_display()}] Proforma {self.proforma.numero} - {self.fecha:%Y-%m-%d %H:%M}"

class RubroServicio(ModeloBase):
    rubro = models.OneToOneField('Rubro', on_delete=models.CASCADE, related_name='rubro_servicio')
    proforma = models.OneToOneField('Proforma', on_delete=models.PROTECT, related_name='rubro_servicio')
    descripcion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Rubro servicio {self.rubro_id} - proforma {self.proforma.numero}"



