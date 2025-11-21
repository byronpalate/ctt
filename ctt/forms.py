# coding=utf-8
import os
from datetime import datetime, timedelta, date

from django import forms
from django.contrib.auth.models import Group
from django.core.validators import EmailValidator
from django.db.models import Q
from django.forms.models import ModelChoiceField
from django.forms.widgets import DateTimeInput
from django.utils.safestring import mark_safe
from decimal import Decimal

from settings import FORMA_PAGO_RECIBOCAJAINSTITUCION, ALUMNOS_GROUP_ID, FORMA_PAGO_NOTA_CREDITO, MAXIMO_MATERIA_ONLINE, \
    NIVEL_MALLA_UNO, CANTIDAD_MATRICULAS_MAXIMAS, EMAIL_INSTITUCIONAL_AUTOMATICO_ESTUDIANTES, EMAIL_INSTITUCIONAL_AUTOMATICO_DOCENTES,\
    FORMA_PAGO_CTAXCRUZAR, CAJAS_DEPOSITOS

from ctt.models import Persona, Canton, Malla, Nivel, Periodo, Materia, Profesor, Turno, Sexo, Provincia, Carrera, \
    Modalidad, Sesion, DIAS_CHOICES, Periodicidad, Nacionalidad, Pais, Parroquia, TipoSangre, Raza, \
    NacionalidadIndigena, \
    PersonaEstadoCivil, TiposMalla, Asignatura, TipoDuraccionMalla, NivelMalla, \
    EjeFormativo, \
    AreaConocimiento, TipoMateria, CampoFormacion, AsignaturaMalla, Coordinacion, PerfilUsuario, Sede, \
    TiempoDedicacionDocente, \
    DetalleNivelTitulacion, NivelTitulacion, TipoAlias, CampoAmplioConocimiento, CampoDetalladoConocimiento, \
    CampoEspecificoConocimiento, \
    TiposBeca, TiposFinanciamientoBeca, Discapacidad, TiposIdentificacion, Inscripcion, FormaDePago, Banco, TipoCheque, \
    TipoEmisorTarjeta, \
    TipoTarjeta, ProcesadorPagoTarjeta, TipoTarjetaBanco, DiferidoTarjeta, CuentaBanco, TipoTransferencia, \
    ReciboCajaInstitucion, \
    NotaCredito, TipoPeriodo, CompetenciaGenerica, CompetenciaEspecifica, TallerPlanificacionMateria, \
    FasesActividadesArticulacion, \
    ContenidosTallerPlanificacionMateria, ClasesTallerPlanificacionMateria, TipoEstudianteCurso, LocacionesCurso, \
    LugarRecaudacion, \
    PuntoVenta, TIPOS_VALE_CAJA, TipoTecnologicoUniversidad, Cargo, TipoAula, TIPO_REQUEST_CHOICES, \
    TIPO_EMISION_FACTURA, TIPO_AMBIENTE_FACTURACION, \
    ModeloImpresion, TipoCuentaBanco, TipoColegio, ModeloEvaluativo, ParaleloMateria, TipoCostoCurso, TIPOS_PAGO_NIVEL, \
    MateriaCursoEscuelaComplementaria, \
    Aula, CursoEscuelaComplementaria, Locacion, OPCIONES_DESCUENTO_CURSOS, TIPOS_APROBACION_PROTOCOLO, TipoProfesor, \
    TipoIntegracion, CodigoEvaluacion, IvaAplicado, Cliente,  Factura, EspacioFisico, ServicioCatalogo
# Servicio,


class BaseForm(forms.Form):
    formbase = forms.CharField(widget=forms.HiddenInput(), required=False)
    formtype = forms.CharField(widget=forms.HiddenInput(), required=False)
    formwidth = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        # ajaxformdinamicbs.html / ajaxformbs.html
        formbase = kwargs.pop('formbase', 'ajaxformbs.html')
        formtype = kwargs.pop('formtype', 'horizontal')
        formwidth = kwargs.pop('formwidth', 'lg')
        super(BaseForm, self).__init__(*args, **kwargs)
        self.fields['formbase'].initial = formbase
        self.fields['formtype'].initial = formtype
        self.fields['formwidth'].initial = formwidth
        for field in self.fields:
            if field not in ['formwidth', 'formtype', 'formbase']:
                if 'class' in self.fields[field].widget.attrs:
                    if 'selectorfecha' in self.fields[field].widget.attrs['class']:
                        self.fields[field].initial = datetime.now().date()
        self.extra_paramaters()

    def extra_paramaters(self):
        pass

    def form_base(self):
        return self.fields['formbase'].initial

    def screenwidth_width(self):
        return int(self.fields['screenwidth'].initial)

    def eliminar(self, nombre):
        if nombre in self.fields:
            del self.fields[nombre]


class CheckboxSelectMultipleCustom(forms.CheckboxSelectMultiple):
    def render(self, *args, **kwargs):
        output = super(CheckboxSelectMultipleCustom, self).render(*args, **kwargs)
        output = '<input type="text" class="busqueda_multiselect" value="" id="id_'+kwargs['name']+'_filtro" name="'+kwargs['name']+'_filtro" ide="'+kwargs['name']+'">' + output
        output = output.replace('<label for="id_'+kwargs['name'], '<label class="contenido_'+kwargs['name']+'" for="id_'+kwargs['name'])
        output = output.replace('<div id="id_'+kwargs['name'], '<div class="custom-multiselect form-control-multiselect" style="max-height: 150px; overflow-y: scroll" id="id_control_'+kwargs['name'])
        output = output + '<input type="text" class="inputmultiselect" value="" id="id_' + kwargs['name'] + '_validacion" name="' + kwargs['name'] + '_validacion" basename="' + kwargs['name'] + '" style="display: none">'
        return mark_safe(output)


class ExtFileField(forms.FileField):

    def __init__(self, *args, **kwargs):
        self.ext_whitelist = kwargs.pop("ext_whitelist", None)
        self.filetypes = [i.lower() for i in self.ext_whitelist]
        self.filesize = kwargs.pop("max_upload_size", None)
        super(ExtFileField, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        upload = super(ExtFileField, self).clean(*args, **kwargs)
        if upload:
            size = upload.size
            filename = upload.name
            ext = os.path.splitext(filename)[1]
            ext = ext.lower()
            if size == 0 or ext not in self.filetypes or size > self.filesize:
                raise forms.ValidationError("Tipo de fichero o tamaño no permitido!")


def deshabilitar_campo(form, campo):
    form.fields[campo].widget.attrs['readonly'] = True
    form.fields[campo].widget.attrs['disabled'] = True



class PersonaForm(BaseForm):
    nombre1 = forms.CharField(label=u'1er Nombre', max_length=50, required=False, widget=forms.TextInput())
    nombre2 = forms.CharField(label=u'2do Nombre', max_length=50, required=False, widget=forms.TextInput())
    apellido1 = forms.CharField(label=u"1er apellido", max_length=50, required=False, widget=forms.TextInput())
    apellido2 = forms.CharField(label=u"2do apellido", max_length=50, required=False, widget=forms.TextInput())
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False, widget=forms.TextInput())
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, required=False, widget=forms.TextInput())
    nacimiento = forms.DateField(label=u"Fecha nacimiento", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    nacionalidad = forms.ModelChoiceField(label=u"Nacionalidad", queryset=Nacionalidad.objects.all(), required=False, widget=forms.Select())
    paisnac = forms.ModelChoiceField(label=u"País de nacimiento", queryset=Pais.objects.all(), required=False, widget=forms.Select())
    provincianac = forms.ModelChoiceField(label=u"Provincia de nacimiento", queryset=Provincia.objects, required=False, widget=forms.Select())
    cantonnac = forms.ModelChoiceField(label=u"Cantón de nacimiento", queryset=Canton.objects, required=False, widget=forms.Select())
    parroquianac = forms.ModelChoiceField(label=u"Parroquia de nacimiento", queryset=Parroquia.objects, required=False, widget=forms.Select())
    sexo = forms.ModelChoiceField(label=u"Género", queryset=Sexo.objects.all(), widget=forms.Select())
    pais = forms.ModelChoiceField(label=u"País de residencia", queryset=Pais.objects.all(), required=False, widget=forms.Select())
    provincia = forms.ModelChoiceField(label=u"Provincia de residencia", queryset=Provincia.objects.all().order_by('nombre'), required=False, widget=forms.Select())
    canton = forms.ModelChoiceField(label=u"Cantón de residencia", queryset=Canton.objects.order_by('nombre'), required=False, widget=forms.Select())
    parroquia = forms.ModelChoiceField(label=u"Parroquia de residencia", queryset=Parroquia.objects.all().order_by('nombre'), required=False, widget=forms.Select())
    sector = forms.CharField(label=u"Sector", max_length=100, required=False, widget=forms.TextInput())
    direccion = forms.CharField(label=u"Calle principal", max_length=100, required=False, widget=forms.TextInput())
    direccion2 = forms.CharField(label=u"Calle secundaria", max_length=100, required=False, widget=forms.TextInput())
    referencia = forms.CharField(label=u"Referencia", max_length=100, required=False, widget=forms.TextInput())
    num_direccion = forms.CharField(label=u"Número de residencia", max_length=15, required=False, widget=forms.TextInput())
    telefono = forms.CharField(label=u"Teléfono móvil", max_length=50, required=False, widget=forms.TextInput())
    telefono_conv = forms.CharField(label=u"Teléfono fijo", max_length=50, required=False, widget=forms.TextInput())
    email = forms.CharField(label=u"Correo electrónico", max_length=200, required=False, widget=forms.TextInput())
    blog = forms.CharField(label=u"Blog", max_length=200, required=False, widget=forms.TextInput())
    twitter = forms.CharField(label=u"Twitter", max_length=200, required=False, widget=forms.TextInput())
    emailinst = forms.CharField(label=u"Correo institucional", max_length=200, required=False, widget=forms.TextInput())
    sangre = forms.ModelChoiceField(label=u"Tipo de sangre", queryset=TipoSangre.objects.all().order_by('sangre'), required=False, widget=forms.Select())
    etnia = forms.ModelChoiceField(label=u'Etnia', queryset=Raza.objects, required=False, widget=forms.Select())
    nacionalidadindigena = forms.ModelChoiceField(label=u'Nacionalidad Indígena', queryset=NacionalidadIndigena.objects, required=False, widget=forms.Select())
    estadocivil = forms.ModelChoiceField(label=u'Estado civil', queryset=PersonaEstadoCivil.objects, required=False, widget=forms.Select())
    # tipolicencia = forms.ModelChoiceField(label=u'Tipo de licencia de conducción (Si la tiene)', queryset=TipoLicencia.objects, required=False, widget=forms.Select())
    # libretamilitar = forms.CharField(label=u"Libreta militar", max_length=30, required=False, widget=forms.TextInput())
    contactoemergencia = forms.CharField(label=u'En caso de emergencia contactarse con ', max_length=200, required=False, widget=forms.TextInput())
    telefonoemergencia = forms.CharField(label=u'Teléfono de contacto de emergencia', max_length=50, required=False, widget=forms.TextInput())
    emailcontactoemergencia = forms.CharField(label=u'Correo de contacto de emergencia', max_length=200, required=False, widget=forms.TextInput())
    # proyectodevida = forms.CharField(label=u'Proyecto de vida', required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}))
    porcientodiscapacidad = forms.FloatField(label=u'% de Discapacidad', initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    carnetdiscapacidad = forms.CharField(label=u'No. Carnet de persona con discapacidad', required=False, widget=forms.TextInput())
    documentoidentificacion = ExtFileField(label=u'Cédula o Pasaporte escaneados', required=False, help_text=u'Tamaño máximo permitido 1Mb, en formato jpg, png', ext_whitelist=(".jpg", ".png",), widget=forms.FileInput(attrs={'fieldheight': '50'}), max_upload_size=1048576)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self, persona):
        deshabilitar_campo(self, 'nombre1')
        deshabilitar_campo(self, 'nombre2')
        deshabilitar_campo(self, 'apellido1')
        deshabilitar_campo(self, 'apellido2')
        deshabilitar_campo(self, 'cedula')
        deshabilitar_campo(self, 'pasaporte')
        self.fields['canton'].queryset = Canton.objects.filter(provincia=persona.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=persona.canton)
        self.fields['cantonnac'].queryset = Canton.objects.filter(provincia=persona.provincianac)
        self.fields['parroquianac'].queryset = Parroquia.objects.filter(canton=persona.cantonnac)

    def del_campos_docente(self):
        del self.fields['nivelescalafon']
        del self.fields['dedicacion']
        del self.fields['orcid']
        del self.fields['perfilgs']
        del self.fields['perfilacademia']
        del self.fields['perfilscopus']
        del self.fields['perfilmendeley']
        del self.fields['perfilresearchgate']
        del self.fields['indicehautor']
        del self.fields['nivel_ingles']
        del self.fields['tienediscapacidad']
        del self.fields['tipodiscapacidad']
        del self.fields['porcientodiscapacidad']
        del self.fields['carnetdiscapacidad']
        del self.fields['documentoidentificacion']

    def sin_pasaporte(self):
        deshabilitar_campo(self, 'pasaporte')

    def sin_fechanacimiento(self):
        deshabilitar_campo(self, 'nacimiento')

    def sin_emailinst(self):
        deshabilitar_campo(self, 'emailinst')

    def es_docente(self, docente):
        self.fields['nivelescalafon'].initial = docente.nivelescalafon
        self.fields['dedicacion'].initial = docente.dedicacion
        self.fields['orcid'].initial = docente.orcid
        self.fields['perfilgs'].initial = docente.perfilgs
        self.fields['perfilacademia'].initial = docente.perfilacademia
        self.fields['perfilscopus'].initial = docente.perfilscopus
        self.fields['perfilmendeley'].initial = docente.perfilmendeley
        self.fields['perfilresearchgate'].initial = docente.perfilresearchgate
        self.fields['indicehautor'].initial = docente.indicehautor
        self.fields['nivel_ingles'].initial = docente.nivel_ingles
        perfil = docente.persona.mi_perfil_docente()
        self.fields['tienediscapacidad'].initial = perfil.tienediscapacidad
        self.fields['tipodiscapacidad'].initial = perfil.tipodiscapacidad
        self.fields['porcientodiscapacidad'].initial = perfil.porcientodiscapacidad
        self.fields['carnetdiscapacidad'].initial = perfil.carnetdiscapacidad
        # deshabilitar_campo(self, 'nivelescalafon')
        # deshabilitar_campo(self, 'dedicacion')

    def solo_estudiante(self, perfil):
        if not perfil.es_estudiante():
            # del self.fields['proyectodevida']
            del self.fields['centroinformacion']
        else:
            # self.fields['proyectodevida'].initial = perfil.inscripcion.proyectodevida
            if perfil.inscripcion.modalidad_id == MODALIDAD_DISTANCIA:
                self.fields['centroinformacion'].initial = perfil.inscripcion.centroinformacion
            else:
                del self.fields['centroinformacion']

class MallaForm(BaseForm):
    resolucion = forms.CharField(label=u"Resolución", max_length=100, required=False, widget=forms.TextInput())
    codigo = forms.CharField(label=u"Código", max_length=30, required=False, widget=forms.TextInput())
    tipo = forms.TypedChoiceField(
        label='Tipo',
        choices=TiposMalla.choices,
        coerce=int,
        required=False,
        empty_value=None,
        widget=forms.Select()
    )
    modalidad = ModelChoiceField(label=u'Modalidad', queryset=Modalidad.objects.all(), required=False, widget=forms.Select())
    # titulo = ModelChoiceField(label=u'Título obtenido', queryset=TituloObtenido.objects.all(), required=False, widget=forms.Select())
    tipoduraccionmalla = ModelChoiceField(label=u'Tipo duración', queryset=TipoDuraccionMalla.objects.all(), required=False, widget=forms.Select())
    inicio = forms.DateField(label=u"Fecha de aprobación", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    fin = forms.DateField(label=u"Fin de vigencia", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    vigencia = forms.IntegerField(label=u"Años de vigencia", initial='1', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall'}))
    nivelesregulares = forms.FloatField(label=u"Niveles de la malla", initial='1', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall'}))
    nivelacion = forms.BooleanField(label=u'Usa nivelación', required=False)
    organizacionaprendizaje = forms.FloatField(label=u"Planf. y equiv. de la Org. del aprendizaje", initial='0.0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    maximomateriasonline = forms.FloatField(label=u"Máximo de materias en matricula", initial=MAXIMO_MATERIA_ONLINE, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall'}))
    libreopcion = forms.FloatField(label=u"Cantidad de libre opción para egresar", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall'}))
    optativas = forms.FloatField(label=u"Cantidad de optativas para egresar", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall'}))
    arrastres = forms.FloatField(label=u"Cantidad de arrastres", initial='1', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall'}))
    horaspracticas = forms.FloatField(label=u"Horas práctica", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    nivelhoraspracticas = ModelChoiceField(label=u'Registro de practicas desde', queryset=NivelMalla.objects.filter(id__gte=NIVEL_MALLA_UNO), required=False, widget=forms.Select())
    horasvinculacion = forms.FloatField(label=u"Horas vinculación", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    nivelhorasvinculacion = ModelChoiceField(label=u'Registro de vinculación desde', queryset=NivelMalla.objects.filter(id__gte=NIVEL_MALLA_UNO), required=False, widget=forms.Select())
    nivelproyecto = ModelChoiceField(label=u'Registro de proyectos desde', queryset=NivelMalla.objects.filter(id__gte=NIVEL_MALLA_UNO), required=False, widget=forms.Select())
    modelosibalo = forms.BooleanField(label=u'Plantillas de silabo', required=False)
    perfildeegreso = forms.CharField(label=u'Perfil de egreso', required=False, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}))
    observaciones = forms.CharField(label=u'Observaciones', required=False, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self, malla):
        deshabilitar_campo(self, 'modalidad')
        deshabilitar_campo(self, 'tipo')
        if not malla.puede_eliminarse() and malla.tiene_estudiantes_usando():
            deshabilitar_campo(self, 'nivelesregulares')
            deshabilitar_campo(self, 'nivelacion')
            deshabilitar_campo(self, 'arrastres')
            deshabilitar_campo(self, 'libreopcion')
            deshabilitar_campo(self, 'optativas')
        if not malla.asignaturamalla_set.exists():
            deshabilitar_campo(self, 'nivelesregulares')


class ClonarMallaForm(BaseForm):
    resolucion = forms.CharField(label=u"Resolución", max_length=100, required=False, widget=forms.TextInput())
    codigo = forms.CharField(label=u"Código", max_length=30, required=False, widget=forms.TextInput())
    modalidad = ModelChoiceField(label=u'Modalidad', queryset=Modalidad.objects.all(), required=False, widget=forms.Select())
    inicio = forms.DateField(label=u"Fecha de aprobación", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    fin = forms.DateField(label=u"Fin de vigencia", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    vigencia = forms.IntegerField(label=u"Años de vigencia", initial='1', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall'}))
    observaciones = forms.CharField(label=u'Observaciones', required=False, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class ClonarPreciosPeriodoForm(BaseForm):
    periodo = forms.ModelChoiceField(label=u"Período", queryset=Periodo.objects.all(), required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class CambiomallaForm(BaseForm):
    malla_nueva = ModelChoiceField(label=u'Nueva malla', queryset=Malla.objects.all())

    def mallas(self, inscripcion):
        self.fields['malla_nueva'].queryset = Malla.objects.filter(carrera=inscripcion.carrera, modalidad=inscripcion.modalidad, aprobado=True)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


# class CambioitinerarioForm(BaseForm):
#     itinerario = ModelChoiceField(label=u'Nuevo itinerario', queryset=Itinerario.objects.all())
#
#     def extra_paramaters(self):
#         self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
#
#     def itinerarios(self, malla):
#         self.fields['itinerario'].queryset = Itinerario.objects.filter(asignaturamalla__malla=malla).distinct()


class CambionivelmallaForm(BaseForm):
    nuevonivel = ModelChoiceField(label=u'Nuevo nivel', queryset=NivelMalla.objects.all())

    def editar(self, inscripcion):
        malla = inscripcion.mi_malla()
        if malla.nivelacion:
            self.fields['nuevonivel'].queryset = NivelMalla.objects.filter(id__lte=malla.nivelesregulares)
        else:
            self.fields['nuevonivel'].queryset = NivelMalla.objects.filter(id__lte=malla.nivelesregulares, id__gte=1)

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class AsignaturaMallaForm(BaseForm):
    asignatura = ModelChoiceField(label=u'Proyecto formativo', queryset=Asignatura.objects.all(), required=False)
    nivelmalla = ModelChoiceField(label=u'Nivel de malla', queryset=NivelMalla.objects.all(), required=False, widget=forms.Select())
    ejeformativo = ModelChoiceField(label=u'Unidad de Organización Curricular', queryset=EjeFormativo.objects.all(), required=False, widget=forms.Select())
    areaconocimiento = ModelChoiceField(label=u'Área de conocimiento', queryset=AreaConocimiento.objects.all(), required=False)
    tipomateria = ModelChoiceField(label=u'Tipo de asignatura', queryset=TipoMateria.objects.all(), required=False, widget=forms.Select())
    identificacion = forms.CharField(label=u'Identificación', max_length=30, required=False, widget=forms.TextInput())
    practicas = forms.BooleanField(label=u'Prácticas pre-profesionales', required=False, initial=False)
    codigopracticas = forms.CharField(label=u'Código prácticas', max_length=15, required=False, widget=forms.TextInput())
    obligatoria = forms.BooleanField(label=u'Obligatoria', required=False, initial=True)
    matriculacion = forms.BooleanField(label=u'Permite matriculación', required=False, initial=True)
    horassemanales = forms.FloatField(label=u"Horas clases semanales", required=False, initial='0.0', widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    horas = forms.FloatField(label=u"Horas Totales", initial='0.0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    totalhorasaprendizajecontactodocente = forms.FloatField(label=u"Horas de aprendizaje en contacto con el docente", required=False, initial='0.0', widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    totalhorasaprendizajeautonomo = forms.FloatField(label=u"Horas del aprendizaje autónomo", required=False, initial='0.0', widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    totalhorasaprendizajepracticoexperimental = forms.FloatField(label=u"Horas del aprendizaje práctico-experimental", required=False, initial='0.0', widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    creditos = forms.FloatField(label=u"Créditos ", required=False, initial="0.0000", widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimales': '4'}))
    cantidadmatriculas = forms.IntegerField(label=u"Cantidad matrículas", initial=CANTIDAD_MATRICULAS_MAXIMAS, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '0'}))
    sinasistencia = forms.BooleanField(label=u'No valida asistencia', required=False, initial=False)
    validacreditos = forms.BooleanField(label=u'Válida para créditos', initial=True, required=False)
    validapromedio = forms.BooleanField(label=u'Válida para promedio', initial=True, required=False)
    competencia = forms.CharField(label=u'Competencia', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formwidth'].initial = 'lg'


    def adicionar(self, malla):
        if not malla.nivelacion:
            self.fields['nivelmalla'].queryset = NivelMalla.objects.filter(id__gt=0, id__lte=malla.nivelesregulares)
        else:
            self.fields['nivelmalla'].queryset = NivelMalla.objects.filter(id__lte=malla.nivelesregulares)

    def editar(self, malla):
        deshabilitar_campo(self, 'asignatura')
        if not malla.nivelacion:
            self.fields['nivelmalla'].queryset = NivelMalla.objects.filter(id__gt=0, id__lte=malla.nivelesregulares)
        else:
            self.fields['nivelmalla'].queryset = NivelMalla.objects.filter(id__lte=malla.nivelesregulares)

    def editarcompetencia(self, malla):
        self.fields['asignatura'].widget.attrs['readonly'] = True
        self.fields['nivelmalla'].widget.attrs['readonly'] = True
        self.fields['identificacion'].widget.attrs['readonly'] = True
        self.fields['ejeformativo'].widget.attrs['readonly'] = True
        self.fields['itinerario'].widget.attrs['readonly'] = True
        self.fields['areaconocimiento'].widget.attrs['readonly'] = True
        self.fields['tipomateria'].widget.attrs['readonly'] = True
        self.fields['campoformacion'].widget.attrs['readonly'] = True
        self.fields['practicas'].widget.attrs['readonly'] = True
        self.fields['codigopracticas'].widget.attrs['readonly'] = True
        self.fields['obligatoria'].widget.attrs['readonly'] = True
        self.fields['matriculacion'].widget.attrs['readonly'] = True
        self.fields['horassemanales'].widget.attrs['readonly'] = True
        self.fields['horas'].widget.attrs['readonly'] = True
        self.fields['horasdocencia'].widget.attrs['readonly'] = True
        self.fields['horascolaborativas'].widget.attrs['readonly'] = True
        self.fields['horasasistidas'].widget.attrs['readonly'] = True
        self.fields['organizacionaprendizaje'].widget.attrs['readonly'] = True
        self.fields['horasorganizacionaprendizaje'].widget.attrs['readonly'] = True
        self.fields['horasautonomas'].widget.attrs['readonly'] = True
        self.fields['horaspracticas'].widget.attrs['readonly'] = True
        self.fields['creditos'].widget.attrs['readonly'] = True
        self.fields['cantidadmatriculas'].widget.attrs['readonly'] = True
        self.fields['sinasistencia'].widget.attrs['readonly'] = True
        self.fields['titulacion'].widget.attrs['readonly'] = True
        self.fields['validacreditos'].widget.attrs['readonly'] = True
        self.fields['validapromedio'].widget.attrs['readonly'] = True
        if not malla.nivelacion:
            self.fields['nivelmalla'].queryset = NivelMalla.objects.filter(id__gt=0, id__lte=malla.nivelesregulares)
        else:
            self.fields['nivelmalla'].queryset = NivelMalla.objects.filter(id__lte=malla.nivelesregulares)

    def noes_itinerario(self):
        del self.fields['itinerario']


# class ItinerarioMallaForm(BaseForm):
#     nombre = forms.CharField(label=u'Nombre', max_length=150, required=False, widget=forms.TextInput())
#     tituloobtenido = ModelChoiceField(label=u'Titulo Obtenido', queryset=TituloObtenido.objects.all(), required=False)
#
#     def extra_paramaters(self):
#         self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class AsignaturaMallaCompetenciaForm(BaseForm):
    identificacion = forms.CharField(label=u'Identificación', max_length=30, required=False, widget=forms.TextInput())
    codigopracticas = forms.CharField(label=u'Código prácticas', max_length=15, required=False, widget=forms.TextInput())
    competencia = forms.CharField(label=u'Competencia', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self, asignaturamalla):
        if not asignaturamalla.practicas:
            deshabilitar_campo(self, 'codigopracticas')

class AsignaturaMallaHorasDocenciaForm(BaseForm):
    totalhorasaprendizajecontactodocente = forms.FloatField(label=u"Horas de aprendizaje en contacto con el docente", required=False, initial='0.0', widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    totalhorasaprendizajeautonomo = forms.FloatField(label=u"Horas del aprendizaje autónomo", required=False, initial='0.0', widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    totalhorasaprendizajepracticoexperimental = forms.FloatField(label=u"Horas del aprendizaje práctico-experimental", required=False, initial='0.0', widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class AsignaturaMallaPredecesoraForm(BaseForm):
    predecesora = ModelChoiceField(label=u'Asignatura', queryset=AsignaturaMalla.objects.all())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def for_exclude_asignatura(self, asignaturamalla):
        self.fields['predecesora'].queryset = asignaturamalla.malla.asignaturamalla_set.filter(nivelmalla_id__lt=asignaturamalla.nivelmalla.id)

    def for_exclude_asignaturaitinerario(self, asignaturamalla):
        self.fields['predecesora'].queryset = asignaturamalla.malla.asignaturamalla_set.filter(Q(itinerario=asignaturamalla.itinerario) | Q(itinerario__isnull=True), nivelmalla__id__lt=asignaturamalla.nivelmalla.id, nivelmalla__id__gt=0).distinct()


class CompetenciaEspecificaForm(BaseForm):
    nombre = forms.CharField(label=u"Nombre", required=False, widget=forms.Textarea(attrs={'rows': '3', 'class':'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'


class NivelForm(BaseForm):
    coordinacion = forms.ModelChoiceField(label=u"Coordinación", queryset=Coordinacion.objects.all(), required=False)
    paralelo = forms.CharField(label=u"Nombre", required=False, max_length=15, widget=forms.TextInput())
    modalidad = forms.ModelChoiceField(label=u"Modalidad", queryset=Modalidad.objects.all(), widget=forms.Select(), required=False)
    sesion = forms.ModelChoiceField(label=u"Sesion", queryset=Sesion.objects.all(), required=False, widget=forms.Select())
    inicio = forms.DateField(label=u"Fecha inicio", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;', 'width': '30%'}))
    fin = forms.DateField(label=u"Fecha fin", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;', 'width': '60%'}))
    fechacierre = forms.DateField(label=u"Fecha cierre período", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;', 'width': '60%'}))
    fechatopematricula = forms.DateField(label=u"Límite ordinaria", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;', 'width': '30%'}))
    fechatopematriculaext = forms.DateField(label=u"Límite extraordinaria", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;', 'width': '30%'}))
    fechatopematriculaesp = forms.DateField(label=u"Límite especial", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;', 'width': '30%'}))
    mensaje = forms.CharField(label=u'Mensaje', required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, coordinacion, persona):
        deshabilitar_campo(self, 'coordinacion')
        self.fields['sesion'].queryset =  Sesion.objects.filter(sede=coordinacion.sede)
        self.fields['modalidad'].queryset =  persona.mis_modalidades(coordinacion)


class ImportarMateriasForm(BaseForm):
    nivel = ModelChoiceField(label=u'Nivel', queryset=Nivel.objects.all(), required=False)

    def adicionar(self, nivel):
        self.fields['nivel'].queryset = Nivel.objects.filter(periodo=nivel.periodo).exclude(id=nivel.id)

class CambioClaveForm(BaseForm):
    anterior = forms.CharField(label=u'Clave anterior', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    nueva = forms.CharField(label=u'Nueva clave', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    repetir = forms.CharField(label=u'Repetir clave', widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class CargarFotoForm(BaseForm):
    foto = forms.FileField(label=u'Seleccione Imagen', help_text=u'Tamaño máximo permitido 500Kb, en formato jpg o jpeg', widget=forms.FileInput(attrs={'accept': '.jpg, .jpeg','data-max-file-size': 500}))

    def extra_paramaters(self):
        self.fields['formwidth'].initial = ''
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class CambioPerfilForm(BaseForm):
    perfil = forms.ModelChoiceField(PerfilUsuario.objects.all(), label=u'Perfil', widget=forms.Select())

    def perfilpersona(self, persona):
        self.fields['perfil'].queryset = PerfilUsuario.objects.filter(persona=persona)

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'


class CambioCoordinacionForm(BaseForm):
    coordinacion = forms.ModelChoiceField(Coordinacion.objects.all(), label=u'Coordinación', widget=forms.Select())

    def mis_coordinaciones(self, persona):
        from django.db.models import Case, When, Value, IntegerField
        self.fields['coordinacion'].queryset = (persona.lista_coordinaciones().annotate(prioridad=Case(When(nombre__istartswith='FACU', then=Value(0)), default=Value(1), output_field=IntegerField(),)).order_by('prioridad', 'nombre', 'sede_id'))

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'


class CambioPeriodoForm(BaseForm):
    periodo = forms.ModelChoiceField(Periodo.objects.all(), label=u'Período', widget=forms.Select())

    def es_docente(self, docente):
        if docente:
            self.fields['periodo'].queryset = Periodo.objects.filter(visualiza=True)

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'


class CambioClaveSimpleForm(BaseForm):
    anterior = forms.CharField(label=u'Clave anterior', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    nueva = forms.CharField(label=u'Nueva clave', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    repetir = forms.CharField(label=u'Repetir clave', widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class FormTerminos(BaseForm):
    texto = forms.FloatField(label=u"--", initial='0.0', required=False, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'



class AdministrativosForm(BaseForm):
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False, widget=forms.TextInput())
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, initial='', required=False, widget=forms.TextInput())
    nombre1 = forms.CharField(label=u"1er Nombre", max_length=50, widget=forms.TextInput())
    nombre2 = forms.CharField(label=u"2do Nombre", max_length=50, required=False, widget=forms.TextInput())
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, widget=forms.TextInput())
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput())
    nacionalidad = forms.ModelChoiceField(label=u"Nacionalidad", queryset=Nacionalidad.objects.all(), required=False, widget=forms.Select())
    paisnac = forms.ModelChoiceField(label=u"País de nacimiento", queryset=Pais.objects.all(), required=False, widget=forms.Select())
    provincianac = forms.ModelChoiceField(label=u"Provincia de nacimiento", queryset=Provincia.objects, required=False, widget=forms.Select())
    cantonnac = forms.ModelChoiceField(label=u"Cantón de nacimiento", queryset=Canton.objects, required=False, widget=forms.Select())
    parroquianac = forms.ModelChoiceField(label=u"Parroquia de nacimiento", queryset=Parroquia.objects, required=False, widget=forms.Select())
    nacimiento = forms.DateField(label=u"Fecha Nacimiento", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), required=False)
    sexo = forms.ModelChoiceField(label=u"Género", queryset=Sexo.objects.all(), widget=forms.Select())
    etnia = forms.ModelChoiceField(label=u'Etnia', queryset=Raza.objects, required=False, widget=forms.Select())
    nacionalidadindigena = forms.ModelChoiceField(label=u'Nacionalidad Indígena', queryset=NacionalidadIndigena.objects, required=False, widget=forms.Select())
    sangre = forms.ModelChoiceField(label=u"Tipo de Sangre", queryset=TipoSangre.objects.all(), required=False, widget=forms.Select())
    pais = forms.ModelChoiceField(label=u"País residencia", queryset=Pais.objects.all(), required=False, widget=forms.Select())
    provincia = forms.ModelChoiceField(label=u"Provincia de residencia", queryset=Provincia.objects.all(), required=False, widget=forms.Select())
    canton = forms.ModelChoiceField(label=u"Cantón de residencia", queryset=Canton.objects.all(), required=False, widget=forms.Select())
    parroquia = forms.ModelChoiceField(label=u"Parroquia de residencia", queryset=Parroquia.objects.all(), required=False, widget=forms.Select())
    sector = forms.CharField(label=u"Sector", max_length=100, required=False, widget=forms.TextInput())
    direccion = forms.CharField(label=u"Calle Principal", max_length=100, required=False, widget=forms.TextInput())
    num_direccion = forms.CharField(label=u"Número Domicilio", max_length=15, required=False, widget=forms.TextInput())
    direccion2 = forms.CharField(label=u"Calle Secundaria", max_length=100, required=False, widget=forms.TextInput())
    telefono = forms.CharField(label=u"Teléfono Movil", max_length=10, required=False, widget=forms.TextInput())
    telefono_conv = forms.CharField(label=u"Teléfono Fijo", max_length=10, required=False, widget=forms.TextInput())
    email = forms.CharField(label=u"Correo Electrónico", max_length=240, required=False, widget=forms.TextInput())
    sede = forms.ModelChoiceField(label=u"Sede", queryset=Sede.objects.all(), required=False, widget=forms.Select())
    emailinst = forms.CharField(label=u"Correo Institucional", max_length=200, required=False, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self):
        if EMAIL_INSTITUCIONAL_AUTOMATICO_ESTUDIANTES:
            del self.fields['emailinst']

    def adicionar_provincia(self):
        self.fields['canton'].queryset = Canton.objects.filter(id=0)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(id=0)
        self.fields['cantonnac'].queryset = Canton.objects.filter(id=0)
        self.fields['parroquianac'].queryset = Parroquia.objects.filter(id=0)

    def editar(self, administrativo):
        self.fields['canton'].queryset = Canton.objects.filter(provincia=administrativo.persona.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=administrativo.persona.canton)
        self.fields['cantonnac'].queryset = Canton.objects.filter(provincia=administrativo.persona.provincianac)
        self.fields['parroquianac'].queryset = Parroquia.objects.filter(canton=administrativo.persona.cantonnac)

class ClientesForm(BaseForm):
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False, widget=forms.TextInput())
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, initial='', required=False, widget=forms.TextInput())
    nombre1 = forms.CharField(label=u"1er Nombre", max_length=50, widget=forms.TextInput())
    nombre2 = forms.CharField(label=u"2do Nombre", max_length=50, required=False, widget=forms.TextInput())
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, widget=forms.TextInput())
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput())
    sexo = forms.ModelChoiceField(label=u"Género", queryset=Sexo.objects.all(), widget=forms.Select())
    direccion = forms.CharField(label=u"Calle Principal", max_length=100, required=False, widget=forms.TextInput())
    telefono = forms.CharField(label=u"Teléfono Movil", max_length=10, required=False, widget=forms.TextInput())
    email = forms.CharField(label=u"Correo Electrónico", max_length=240, required=False, widget=forms.TextInput())
    empresa = forms.BooleanField(label=u"Pertenece a Empresa?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'formwidth': 200}))
    ruc = forms.CharField(label=u"Ruc", max_length=13, required=False, widget=forms.TextInput())
    nombreempresa = forms.CharField(label=u"Nombre Empresa", max_length=50,required=False, widget=forms.TextInput())
    emailempresa = forms.CharField(label=u"Correo Electrónico Empresa", max_length=240, required=False, widget=forms.TextInput())
    direccionempresa = forms.CharField(label=u"Dirección Empresa", max_length=100, required=False, widget=forms.TextInput())
    telefonoempresa = forms.CharField(label=u"Teléfono Empresa", max_length=10, required=False, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class GrupoUsuarioForm(BaseForm):
    grupo = forms.ModelChoiceField(label=u'Grupo', queryset=Group.objects.all().order_by('name'), required=False, widget=forms.Select())

    def grupos(self, lista):
        self.fields['grupo'].queryset = lista

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'




class NuevaInscripcionForm(BaseForm):
    sede = forms.ModelChoiceField(label=u"Sede", queryset=Sede.objects.all(), required=False, widget=forms.Select())
    coordinacion = forms.ModelChoiceField(label=u"Coordinación", queryset=Coordinacion.objects.all(), required=False, widget=forms.Select())
    mocs = forms.BooleanField(label=u"MOC's", required=False, initial=False, widget=forms.CheckboxInput(attrs={'formwidth': 200}))
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Carrera.objects.all(), required=False)
    modalidad = forms.ModelChoiceField(label=u"Modalidad", queryset=Modalidad.objects.all(), required=False, widget=forms.Select())
    sesion = forms.ModelChoiceField(label=u"Sesión", queryset=Sesion.objects.all(), required=False, widget=forms.Select())
    malla = forms.ModelChoiceField(Malla.objects.all(), required=False, widget=forms.Select())
    periodo = forms.ModelChoiceField(label=u"Período", queryset=Periodo.objects, required=False, widget=forms.Select())
    copiarecord = forms.BooleanField(label=u"Copiar record académico?", required=False)
    fechainiciocarrera = forms.DateField(label=u"Comenzó la carrera", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    prenivelacion = forms.BooleanField(label=u"Homologa nivelación", required=False)
    nivelmalla = forms.ModelChoiceField(label=u"Nivel", queryset=NivelMalla.objects.filter(id__gt=0), required=False, widget=forms.Select())
    observacionespre = forms.CharField(label=u"Observaciones Pre", max_length=100, required=False)
    rindioexamen = forms.BooleanField(label=u'Rindió examen SNNA', required=False)
    fechaexamensnna = forms.DateField(label=u"Fecha examen SNNA", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    puntajesnna = forms.FloatField(label=u'Puntaje SNNA', initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    condicionado = forms.BooleanField(label=u'Condicionado', required=False, widget=forms.CheckboxInput())
    reingreso = forms.BooleanField(label=u'Reingreso', required=False, widget=forms.CheckboxInput())
    homologar = forms.BooleanField(label=u'Solo para Homologación EXTERNA', required=False, widget=forms.CheckboxInput())
    alumnoantiguo = forms.BooleanField(label=u"Alumno Antiguo / Homologación Trayectoria", required=False, initial=False, widget=forms.CheckboxInput(attrs={'formwidth': 200}))
    reconocimientointerno = forms.BooleanField(label=u"Reconocimiento Interno", required=False, initial=False, widget=forms.CheckboxInput(attrs={'formwidth': 200}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, persona, coordinacion):
        self.fields['sede'].queryset = persona.lista_sedes(persona.lista_coordinaciones())
        self.fields['coordinacion'].queryset = Coordinacion.objects.filter(id=0)
        self.fields['carrera'].queryset = Carrera.objects.filter(id=0)
        self.fields['malla'].queryset = Malla.objects.filter(aprobado=True)
        self.fields['sesion'].queryset = Sesion.objects.filter(id=0)
        self.fields['periodo'].queryset = Periodo.objects.filter(id=0)
        del self.fields['alumnoantiguo']

    def sin_record(self):
        del self.fields['copiarecord']


class SedeAdministrativoForm(BaseForm):
    sede = forms.ModelChoiceField(label=u'Sede', queryset=Sede.objects.all(), required=False, widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class ProfesorForm(BaseForm):
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False, widget=forms.TextInput())
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, initial='', required=False, widget=forms.TextInput())
    nombre1 = forms.CharField(label=u"1er Nombre", max_length=50, widget=forms.TextInput())
    nombre2 = forms.CharField(label=u"2do Nombre", required=False, max_length=50, widget=forms.TextInput())
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, widget=forms.TextInput())
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput())
    fechainiciodocente = forms.DateField(label=u'Fecha inicio actividades como docente', initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    coordinacion = forms.ModelChoiceField(label=u"Coordinación", queryset=Coordinacion.objects.all(), required=False, widget=forms.Select())
    dedicacion = forms.ModelChoiceField(label=u'Tiempo de Dedicación', queryset=TiempoDedicacionDocente.objects.all(), required=False, widget=forms.Select())
    nacionalidad = forms.ModelChoiceField(label=u"Nacionalidad", queryset=Nacionalidad.objects.all(), required=False, widget=forms.Select())
    paisnac = forms.ModelChoiceField(label=u"País de Nacimiento", queryset=Pais.objects.all(), required=False, widget=forms.Select())
    provincianac = forms.ModelChoiceField(label=u"Provincia de nacimiento", queryset=Provincia.objects, required=False, widget=forms.Select())
    cantonnac = forms.ModelChoiceField(label=u"Cantón de nacimiento", queryset=Canton.objects, required=False, widget=forms.Select())
    parroquianac = forms.ModelChoiceField(label=u"Parroquia de nacimiento", queryset=Parroquia.objects, required=False, widget=forms.Select())
    nacimiento = forms.DateField(label=u"Fecha de Nacimiento", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), required=False)
    sexo = forms.ModelChoiceField(label=u"Género", queryset=Sexo.objects.all(), widget=forms.Select())
    etnia = forms.ModelChoiceField(label=u'Etnia', queryset=Raza.objects, required=False, widget=forms.Select())
    nacionalidadindigena = forms.ModelChoiceField(label=u'Nacionalidad Indígena', queryset=NacionalidadIndigena.objects, required=False, widget=forms.Select())
    sangre = forms.ModelChoiceField(label=u"Tipo de Sangre", queryset=TipoSangre.objects.all(), required=False, widget=forms.Select())
    pais = forms.ModelChoiceField(label=u"País de Residencia", queryset=Pais.objects.all(), required=False, widget=forms.Select())
    provincia = forms.ModelChoiceField(label=u"Provincia de Residencia", queryset=Provincia.objects.all(), required=False, widget=forms.Select())
    canton = forms.ModelChoiceField(label=u"Cantón de Residencia", queryset=Canton.objects.all(), required=False, widget=forms.Select())
    parroquia = forms.ModelChoiceField(label=u"Parroquia de Residencia", queryset=Parroquia.objects.all(), required=False, widget=forms.Select())
    sector = forms.CharField(label=u"Sector de Residencia", max_length=100, required=False, widget=forms.TextInput())
    direccion = forms.CharField(label=u"Calle Principal", max_length=100, required=False, widget=forms.TextInput())
    num_direccion = forms.CharField(label=u"Número Domicilio", max_length=15, required=False, widget=forms.TextInput())
    direccion2 = forms.CharField(label=u"Calle Secundaria", max_length=100, required=False, widget=forms.TextInput())
    telefono = forms.CharField(label=u"Teléfono Movil", max_length=10, required=False, widget=forms.TextInput())
    telefono_conv = forms.CharField(label=u"Teléfono Fijo", max_length=10, required=False, widget=forms.TextInput())
    email = forms.CharField(label=u"Correo Electrónico", max_length=240, required=False, widget=forms.TextInput())
    emailinst = forms.CharField(label=u"Correo Institucional", max_length=200, required=False, widget=forms.TextInput())
    documentoidentificacion = ExtFileField(label=u'Documento de Identificación',required=True, help_text=u'Tamaño máximo permitido 10Mb, en formato png o jpg', ext_whitelist=(".png", ".jpg"), max_upload_size=10485760)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self):
        self.fields['canton'].queryset = Canton.objects.filter(provincia=0)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=0)
        self.fields['cantonnac'].queryset = Canton.objects.filter(provincia=0)
        self.fields['parroquianac'].queryset = Parroquia.objects.filter(canton=0)
        del self.fields['coordinacion']
        if EMAIL_INSTITUCIONAL_AUTOMATICO_DOCENTES:
            del self.fields['emailinst']

    def editar(self, profesor):
        # deshabilitar_campo(self, 'dedicacion')
        del self.fields['dedicacion']
        self.fields['canton'].queryset = Canton.objects.filter(provincia=profesor.persona.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=profesor.persona.canton)
        self.fields['cantonnac'].queryset = Canton.objects.filter(provincia=profesor.persona.provincianac)
        self.fields['parroquianac'].queryset = Parroquia.objects.filter(canton=profesor.persona.cantonnac)



class EstudioEducacionSuperiorForm(BaseForm):
    institucion = forms.IntegerField(initial='', required=False, label=u'Institución', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    carrera = forms.CharField(label=u"Carrera", max_length=200, required=False)
    cursando = forms.BooleanField(label=u"Cursa actualmente", required=False)
    fechainicio = forms.DateField(label=u"Fecha de inicio", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    fechafin = forms.DateField(label=u"Fecha de finalización", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    cicloactual = forms.CharField(label=u"Ciclo", max_length=200, required=False, widget=forms.TextInput())
    titulo = forms.CharField(label=u"Título", max_length=200, required=False)
    aliastitulo = forms.ChoiceField(label=u"Alias título (Dr. Lic.)", required=False, choices=TipoAlias.choices, widget=forms.Select())
    niveltitulacion = forms.ModelChoiceField(label=u'Nivel Titulación', queryset=NivelTitulacion.objects.all(), required=False, widget=forms.Select())
    detalleniveltitulacion = forms.ModelChoiceField(label=u'Detalle Nivel Titulación', queryset=DetalleNivelTitulacion.objects.all(), required=False, widget=forms.Select())
    campoamplio = forms.ModelChoiceField(label=u'Campo amplio de conocimiento', required=False,  queryset=CampoAmplioConocimiento.objects, widget=forms.Select())
    campoespecifico = forms.ModelChoiceField(label=u'Campo específico de conocimiento', required=False,  queryset=CampoEspecificoConocimiento.objects, widget=forms.Select())
    campodetallado = forms.ModelChoiceField(label=u'Campo detallado de conocimiento', required=False, queryset=CampoDetalladoConocimiento.objects, widget=forms.Select())
    fechagraduacion = forms.DateField(label=u"Fecha de graduación", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    fecharegistro = forms.DateField(label=u"Fecha de registro", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    registro = forms.CharField(label=u'Registro SENESCYT', required=False, widget=forms.TextInput())
    aplicabeca = forms.BooleanField(label=u"Posee beca", required=False)
    tipobeca = forms.ChoiceField(label=u'Tipo beca', required=False, choices=TiposBeca, widget=forms.Select())
    montobeca = forms.FloatField(label=u"Monto beca", initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2'}))
    tipofinanciamientobeca = forms.ChoiceField(label=u'Tipo finanaciamiento beca', required=False, choices=TiposFinanciamientoBeca, widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self, estudio):
        self.fields['institucion'].widget.attrs['descripcion'] = estudio.institucioneducacionsuperior.flexbox_repr() if estudio.institucioneducacionsuperior else None
        self.fields['detalleniveltitulacion'].queryset = DetalleNivelTitulacion.objects.filter(niveltitulacion=estudio.niveltitulacion)

    def adicionar(self):
        self.fields['detalleniveltitulacion'].queryset = DetalleNivelTitulacion.objects.filter(id=0)


class InscripcionForm(BaseForm):
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False, widget=forms.TextInput())
    nombre1 = forms.CharField(label=u"1er Nombre", max_length=50, widget=forms.TextInput(attrs={'placeholder': 'PRIMER NOMBRE' }))
    nombre2 = forms.CharField(label=u"2do Nombre", required=False, max_length=50, widget=forms.TextInput(attrs={'placeholder': 'SEGUNDO NOMBRE' }))
    apellido1 = forms.CharField(label=u"1er apellido", max_length=50, widget=forms.TextInput(attrs={'placeholder': 'APELLIDO PATERNO' }))
    apellido2 = forms.CharField(label=u"2do apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'placeholder': 'APELLIDO MATERNO' }))
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, required=False, widget=forms.TextInput())
    paisnac = forms.ModelChoiceField(label=u"País de nacimiento", queryset=Pais.objects.all(), required=False, widget=forms.Select())
    nacionalidad = forms.ModelChoiceField(label=u"Nacionalidad", queryset=Nacionalidad.objects.all(), required=False, widget=forms.Select())
    provincianac = forms.ModelChoiceField(label=u"Provincia de nacimiento", queryset=Provincia.objects, required=False, widget=forms.Select())
    cantonnac = forms.ModelChoiceField(label=u"Cantón de nacimiento", queryset=Canton.objects, required=False, widget=forms.Select())
    parroquianac = forms.ModelChoiceField(label=u"Parroquia de nacimiento", queryset=Parroquia.objects, required=False, widget=forms.Select())
    nacimiento = forms.DateField(label=u"Fecha de nacimiento", input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    sexo = forms.ModelChoiceField(label=u"Género", queryset=Sexo.objects, widget=forms.Select())
    etnia = forms.ModelChoiceField(label=u'Etnia', queryset=Raza.objects, required=False, widget=forms.Select())
    nacionalidadindigena = forms.ModelChoiceField(label=u'Nacionalidad Indígena', queryset=NacionalidadIndigena.objects, required=False, widget=forms.Select())
    sangre = forms.ModelChoiceField(label=u"Tipo de sangre", queryset=TipoSangre.objects, required=False, widget=forms.Select())
    tienediscapacidad = forms.BooleanField(label=u"Tiene Discapacidad?", required=False)
    tipodiscapacidad = forms.ModelChoiceField(label=u"Tipo de Discapacidad", queryset=Discapacidad.objects.all(), required=False, widget=forms.Select())
    porcientodiscapacidad = forms.FloatField(label=u'% de Discapacidad', initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    carnetdiscapacidad = forms.CharField(label=u'No. Carnet Discapacitado', required=False, widget=forms.TextInput())
    pais = forms.ModelChoiceField(label=u"País de residencia", queryset=Pais.objects.all(), required=False, widget=forms.Select())
    provincia = forms.ModelChoiceField(label=u"Provincia de residencia", queryset=Provincia.objects, required=False, widget=forms.Select())
    canton = forms.ModelChoiceField(label=u"Cantón de residencia", queryset=Canton.objects, required=False, widget=forms.Select())
    parroquia = forms.ModelChoiceField(label=u"Parroquia de residencia", queryset=Parroquia.objects, required=False, widget=forms.Select())
    sector = forms.CharField(label=u"Sector de residencia", max_length=100, required=False, widget=forms.TextInput())
    otraubicacionsalesforce = forms.CharField(label=u"Otra Ubicación", max_length=100, required=False, widget=forms.TextInput())
    direccion = forms.CharField(label=u"Calle principal", max_length=100, required=False, widget=forms.TextInput())
    num_direccion = forms.CharField(label=u"Número residencia", max_length=15, required=False, widget=forms.TextInput())
    direccion2 = forms.CharField(label=u"Calle secundaria", max_length=100, required=False, widget=forms.TextInput())
    telefono = forms.CharField(label=u"Teléfono movil", max_length=10, required=False, widget=forms.TextInput())
    telefono_conv = forms.CharField(label=u"Teléfono Fijo", max_length=10, required=False, widget=forms.TextInput())
    email = forms.CharField(label=u"Correo Electrónico", max_length=240, required=False, widget=forms.TextInput())
    emailinst = forms.CharField(label=u"Correo Institucional", max_length=200, required=False, widget=forms.TextInput())
    provinciacole = forms.ModelChoiceField(label=u"Provincia del Colegio", queryset=Provincia.objects, required=False, widget=forms.Select())
    cantoncole = forms.ModelChoiceField(label=u"Cantón del Colegio", queryset=Canton.objects, required=False, widget=forms.Select())
    colegio = forms.IntegerField(initial='', required=False, label=u'Colegio', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    titulocolegio = forms.CharField(label=u"Título colegio", max_length=240, required=False, widget=forms.TextInput())
    especialidad = forms.IntegerField(initial='', required=False, label=u'Especialidad', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    fechainiciocarrera = forms.DateField(label=u"Inicio carrera", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    sede = forms.ModelChoiceField(label=u"Sede", queryset=Sede.objects, required=False, widget=forms.Select())
    coordinacion = forms.ModelChoiceField(label=u"Coordinación", queryset=Coordinacion.objects, required=False, widget=forms.Select())
    mocs = forms.BooleanField(label=u"MOC's", required=False, initial=False, widget=forms.CheckboxInput(attrs={'formwidth': 200}))
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Carrera.objects, required=False)
    modalidad = forms.ModelChoiceField(label=u"Modalidad", queryset=Modalidad.objects, required=False, widget=forms.Select())
    periodo = forms.ModelChoiceField(label=u"Período", queryset=Periodo.objects, required=False, widget=forms.Select())
    nivel = forms.ModelChoiceField(label=u"Nivel", queryset=Nivel.objects, required=False, widget=forms.Select())
    sesion = forms.ModelChoiceField(label=u"Sesión", queryset=Sesion.objects, required=False, widget=forms.Select())
    malla = forms.ModelChoiceField(Malla.objects.all(), required=False, widget=forms.Select())
    identificador = forms.CharField(label=u'Archivador', required=False, widget=forms.TextInput())
    nombrescompletosmadre = forms.CharField(max_length=500, label=u"Nombre completo de la madre", widget=forms.TextInput(),required=False)
    nombrescompletospadre = forms.CharField(max_length=500, label=u"Nombre completo del padre", widget=forms.TextInput(),required=False)
    otrofuentefinanciacion = forms.CharField(label=u"Otra Fuente Financiación", required=False, widget=forms.TextInput())
    trabaja = forms.BooleanField(label=u'Trabaja?', required=False)
    titulogrado = forms.CharField(label=u"Titulo de Grado", required=False, widget=forms.TextInput())
    universidadgrado = forms.CharField(label=u"Universidad de Grado", required=False, widget=forms.TextInput())
    empresa = forms.CharField(label=u"Empresa donde trabaja", max_length=200, required=False)
    ocupacion = forms.CharField(label=u"Ocupación", required=False, widget=forms.TextInput())
    # telefono_trabajo = forms.CharField(label=u"Teléfono del trabajo", max_length=100, required=False,widget=forms.TextInput())
    fecha_ingreso = forms.DateField(label=u"Comenzo a trabajar", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha','onkeydown': 'return false;'}))
    facturaidentificacion = forms.CharField(max_length=20, label=u'Factura-Identificación', widget=forms.TextInput(attrs={'style':'background-color:#9fb5fe'}))
    facturatipoidentificacion = forms.ChoiceField(label=u'Factura-Tipo identificación', choices=TiposIdentificacion.choices, widget=forms.Select(attrs={'style':'background-color:#9fb5fe'}))
    facturanombre = forms.CharField(max_length=100, label=u'Factura-Nombre beneficiario', widget=forms.TextInput(attrs={'style':'background-color:#9fb5fe'}))
    facturadireccion = forms.CharField(max_length=100, label=u"Factura-Dirección", widget=forms.TextInput(attrs={'style':'background-color:#9fb5fe'}))
    facturatelefono = forms.CharField(max_length=50, label=u"Factura-Teléfono", widget=forms.TextInput(attrs={'class': 'imp-telefono','style':'background-color:#9fb5fe'}))
    facturaemail = forms.CharField(max_length=50, label=u"Factura-Email", widget=forms.TextInput(attrs={'style':'background-color:#9fb5fe'}))
    comoseinformootras = forms.CharField(label=u"Otros", max_length=100, required=False, widget=forms.TextInput())
    rindioexamen = forms.BooleanField(label=u'Rindió examen SNNA', required=False)
    fechaexamensnna = forms.DateField(label=u"Fecha examen SNNA", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    puntajesnna = forms.FloatField(label=u'Puntaje SNNA', initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    conveniohomologacion = forms.BooleanField(label=u'Convenio por homologación', required=False)
    condicionado = forms.BooleanField(label=u'Condicionado', required=False, widget=forms.CheckboxInput(attrs={'formwidth': 200}))
    homologar = forms.BooleanField(label=u'Homologo materias', required=False, widget=forms.CheckboxInput(attrs={'formwidth': 200}))
    examenubicacionidiomas = forms.BooleanField(label=u'Rinde examen ubicación inglés', required=False, widget=forms.CheckboxInput(attrs={'formwidth': 200}))
    observaciones = forms.CharField(label=u'Observaciones', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def sin_trabajo(self):
        del self.fields['trabaja']
        del self.fields['empresa']
        del self.fields['ocupacion']
        # del self.fields['telefono_trabajo']
        del self.fields['fecha_ingreso']
        del self.fields['colegio']
        del self.fields['especialidad']
        del self.fields['titulocolegio']
        del self.fields['universidadgrado']
        del self.fields['titulogrado']

    def adicionar(self, persona):
        del self.fields['fechainiciocarrera']
        self.fields['sede'].queryset = persona.lista_sedes(persona.lista_coordinaciones())
        self.fields['coordinacion'].queryset = Coordinacion.objects.filter(id=0)
        self.fields['carrera'].queryset = Carrera.objects.filter(id=0)
        self.fields['nivel'].queryset = Nivel.objects.filter(id=0)
        self.fields['periodo'].queryset = Periodo.objects.filter(id=0)
        self.fields['canton'].queryset = Canton.objects.filter(id=0)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(id=0)
        self.fields['cantonnac'].queryset = Canton.objects.filter(id=0)
        self.fields['parroquianac'].queryset = Parroquia.objects.filter(id=0)
        self.fields['malla'].queryset = Malla.objects.filter(id=0)
        self.fields['sesion'].queryset = Sesion.objects.filter(id=0)
        if EMAIL_INSTITUCIONAL_AUTOMATICO_ESTUDIANTES:
            del self.fields['emailinst']

    def editar(self, inscripcion):
        deshabilitar_campo(self, 'sede')
        deshabilitar_campo(self, 'coordinacion')
        deshabilitar_campo(self, 'carrera')
        deshabilitar_campo(self, 'malla')
        deshabilitar_campo(self, 'modalidad')
        deshabilitar_campo(self, 'periodo')
        deshabilitar_campo(self, 'nivel')
        del self.fields['homologar']
        del self.fields['orientacion']
        del self.fields['intercambio']
        del self.fields['alumnoantiguo']
        del self.fields['reconocimientointerno']
        self.fields['canton'].queryset = Canton.objects.filter(provincia=inscripcion.persona.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=inscripcion.persona.canton)
        self.fields['cantonnac'].queryset = Canton.objects.filter(provincia=inscripcion.persona.provincianac)
        self.fields['parroquianac'].queryset = Parroquia.objects.filter(canton=inscripcion.persona.cantonnac)
        self.fields['sesion'].queryset = Sesion.objects.filter(sede=inscripcion.sede)
        if inscripcion.matriculado() or inscripcion.graduado() or inscripcion.egresado():
            deshabilitar_campo(self, 'sesion')
        # if inscripcion.documentos_entregados().eshomologacionexterna:
        #     deshabilitar_campo(self, 'eshomologacionexterna')
        malla = inscripcion.mi_malla()
        minivel = inscripcion.mi_nivel().nivel.id
        mallaniveles = malla.nivelesregulares
        if minivel == 0:
            del self.fields['fechainiciocarrera']
            del self.fields['fechafincarrera']
        else:
            if inscripcion.matricula_set.filter(nivelmalla__id=NIVEL_MALLA_UNO) or inscripcion.tiene_homologaciones():
                del self.fields['fechainiciocarrera']



class RecordAcademicoForm(BaseForm):
    periodo = forms.ModelChoiceField(label=u"Período", queryset=Periodo.objects.all(), required=False)
    tipo = forms.ChoiceField(label=u'Tipo', choices=((1, u'ASIGNATURAS DE LA MALLA'), (2, u'TODAS'),), required=False, widget=forms.Select())
    asignatura = forms.ModelChoiceField(label=u"Asignatura", queryset=Asignatura.objects.all(), required=False)
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), required=False)
    creditos = forms.FloatField(label=u"Créditos ", initial="0.0000", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimales': '4'}))
    horas = forms.FloatField(label=u"Horas ", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '0'}))
    nota = forms.FloatField(label=u"Nota", initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '2'}))
    asistencia = forms.FloatField(label=u"% Asistencia", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    aprobada = forms.BooleanField(label=u"Aprobada?", required=False)
    convalidacion = forms.BooleanField(label=u"Homologación otra institución", required=False)
    homologada = forms.BooleanField(label=u"Homologación interna", required=False)
    validacreditos = forms.BooleanField(label=u"Válida para créditos", initial=True, required=False)
    validapromedio = forms.BooleanField(label=u"Válida para promedio", initial=True, required=False)
    optativa = forms.BooleanField(label=u"Optativa", required=False)
    libreconfiguracion = forms.BooleanField(label=u"Libre configuración", required=False)
    observaciones = forms.CharField(label=u'Observaciones', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    archivo = ExtFileField(label=u'Fichero', required=False,help_text=u'Tamaño máximo permitido 4Mb, en formato doc, docx, xls, xlsx, pdf, ppt, pptx, rar, zip, txt',ext_whitelist=(".doc", ".docx", ".xls", ".xlsx", ".pdf", ".ppt", ".pptx", ".zip", ".rar", ".txt"),max_upload_size=4194304)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, inscripcion):
        malla = inscripcion.mi_malla()
        self.fields['asignatura'].queryset = Asignatura.objects.filter(Q(asignaturamalla__malla=malla) | Q(modulomalla__malla=malla) | Q(trabajotitulacionmalla__malla=malla)).distinct()
        self.fields['periodo'].queryset = Periodo.objects.filter(nivel__materia__carrera=inscripcion.carrera).distinct()

    def record_normal(self):
        del self.fields['convalidacion']
        del self.fields['homologada']
        del self.fields['institucion']
        del self.fields['tiporeconocimiento']
        del self.fields['tiemporeconocimiento']
        del self.fields['carrera_he']
        del self.fields['asignatura_he']
        del self.fields['anno_he']
        del self.fields['nota_ant_he']
        del self.fields['creditos_he']
        del self.fields['carrera_hi']
        del self.fields['modalidad_hi']
        del self.fields['asignatura_hi']
        del self.fields['fecha_hi']
        del self.fields['nota_ant_hi']
        del self.fields['creditos_hi']
        del self.fields['observaciones_hi']
        del self.fields['observaciones_he']
        del self.fields['archivo']
        del self.fields['tipohomologacion']

    def homologacion(self, inscripcion):
        malla = inscripcion.mi_malla()
        del self.fields['observaciones']
        del self.fields['aprobada']
        del self.fields['asistencia']
        del self.fields['tipo']
        if inscripcion.carrera.tipogrado.id == CUARTO_NIVEL_TITULACION_ID:
            self.fields['periodo'].queryset = Periodo.objects.filter(tipo__id=TIPO_PERIODO_POSGRADO)
        else:
            self.fields['periodo'].queryset = Periodo.objects.filter(tipo__id=TIPO_PERIODO_GRADO)
        self.fields['asignatura'].queryset = Asignatura.objects.filter(Q(asignaturamalla__malla=malla) | Q(modulomalla__malla=malla)).exclude(id__in=Asignatura.objects.filter(recordacademico__inscripcion=inscripcion, recordacademico__aprobada=True).values_list('id', flat=True)).distinct()



class HistoricoRecordAcademicoForm(BaseForm):
    asignatura = forms.ModelChoiceField(label=u"Asignatura", queryset=Asignatura.objects.all(), required=False)
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    creditos = forms.FloatField(label=u"Créditos ", initial="0.0000", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimales': '4'}))
    horas = forms.FloatField(label=u"Horas", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '0'}))
    nota = forms.FloatField(label=u"Nota", initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '2'}))
    asistencia = forms.FloatField(label=u"% Asistencia", initial='0', widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    aprobada = forms.BooleanField(label=u"Aprobada?", required=False)
    validacreditos = forms.BooleanField(label=u"Válida para créditos", initial=True, required=False)
    validapromedio = forms.BooleanField(label=u"Válida para promedio", initial=True, required=False)
    libreconfiguracion = forms.BooleanField(label=u"Libre configuración", required=False)
    optativa = forms.BooleanField(label=u"Optativa", required=False)
    observaciones = forms.CharField(label=u'Observaciones', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=False, )

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def solo_asignatura(self, idr):
        deshabilitar_campo(self, 'asignatura')
        self.fields['asignatura'].queryset = Asignatura.objects.filter(id=idr)

    def editar(self, historico):
        deshabilitar_campo(self, 'asignatura')
        if historico.homologada or historico.convalidacion:
            deshabilitar_campo(self, 'aprobada')


class EstudioEducacionBasicaForm(BaseForm):
    provinciacole = forms.ModelChoiceField(label=u"Provincia del Colegio", queryset=Provincia.objects, required=False,widget=forms.Select())
    cantoncole = forms.ModelChoiceField(label=u"Cantón del Colegio", queryset=Canton.objects, required=False,widget=forms.Select())
    colegio = forms.IntegerField(initial='', required=False, label=u'Colegio', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    especialidad = forms.IntegerField(initial='', required=False, label=u'Especialidad', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    titulocolegio = forms.CharField(label=u"Título colegio", max_length=200, required=False)
    abanderado = forms.BooleanField(label=u'Fue abanderado', required=False, widget=forms.CheckboxInput(attrs={'formwidth': 200}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self, estudio):
        self.fields['colegio'].widget.attrs['descripcion'] = estudio.institucioneducacionbasica
        self.fields['especialidad'].widget.attrs['descripcion'] = estudio.especialidadeducacionbasica


class CambiaDatosCarreraForm(BaseForm):
    sede = forms.ModelChoiceField(label=u"Sede", queryset=Sede.objects, required=False, widget=forms.Select())
    coordinacion = forms.ModelChoiceField(label=u"Coordinación", queryset=Coordinacion.objects, required=False, widget=forms.Select())
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Carrera.objects, required=False)
    modalidad = forms.ModelChoiceField(label=u"Modalidad", queryset=Modalidad.objects, required=False, widget=forms.Select())
    sesion = forms.ModelChoiceField(label=u"Sesión", queryset=Sesion.objects, required=False, widget=forms.Select())
    periodo = forms.ModelChoiceField(label=u"Período", queryset=Periodo.objects, required=False, widget=forms.Select())
    malla = forms.ModelChoiceField(Malla.objects.all(), required=False, widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, persona):
        self.fields['sede'].queryset = persona.lista_sedes(persona.lista_coordinaciones())
        self.fields['coordinacion'].queryset = Coordinacion.objects.filter(id=0)
        self.fields['carrera'].queryset = Carrera.objects.filter(id=0)
        self.fields['malla'].queryset = Malla.objects.filter(id=0, aprobado=True)
        self.fields['sesion'].queryset = Sesion.objects.filter(id=0)

class ImportarArchivoXLSForm(BaseForm):
    archivo = forms.FileField(label=u'Seleccione archivo',help_text=u'Tamaño máximo permitido 4Mb, en formato xls,xlsx', widget=forms.FileInput(attrs={'accept': '.xls, .xlsx', 'data-max-file-size': 4194304}))

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class RetiradoCarreraForm(BaseForm):
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'

class CambiarFichaInscripcionForm(BaseForm):
    malla = forms.ModelChoiceField(label=u"Ficha", queryset=Malla.objects.filter(aprobado=True))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, persona):
        self.fields['malla'].queryset = Malla.objects.filter(inscripcionmalla__inscripcion__persona=persona,
                                                             aprobado=True)

class ImportarArchivoXLSPeriodoForm(BaseForm):
    periodo = forms.ModelChoiceField(label=u"Período", queryset=Periodo.objects.all(), required=False)
    archivo = forms.FileField(label=u'Seleccione archivo',help_text=u'Tamaño máximo permitido 4Mb, en formato xls,xlsx', widget=forms.FileInput(attrs={'accept': '.xls, .xlsx', 'data-max-file-size': 4194304}))

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class RubroForm(BaseForm):
    valorajuste = forms.FloatField(label=u'Valor ajuste', initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    motivoajuste = forms.CharField(label=u'Motivo Ajuste', required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}))
    fechavence = forms.DateField(label=u"Fecha Vencimiento", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class MoverPagoRubroForm(BaseForm):
    inscripcionorigen = forms.ModelChoiceField(label="Desde", queryset=Inscripcion.objects.all(), empty_label="Seleccione la ficha origen", to_field_name="id", widget=forms.Select(),)
    inscripciondestino = forms.ModelChoiceField(label="Hacia", queryset=Inscripcion.objects.all(), empty_label="Seleccione la ficha destino", to_field_name="id", widget=forms.Select(),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['inscripcionorigen'].label_from_instance = lambda obj: obj.flexbox_repr_malla
        self.fields['inscripciondestino'].label_from_instance = lambda obj: obj.flexbox_repr_malla

    def adicionar(self, persona, inscripcion):
        self.fields['inscripcionorigen'].queryset = Inscripcion.objects.filter(persona=persona).order_by("id")
        self.fields['inscripciondestino'].queryset = Inscripcion.objects.filter(persona=persona).order_by("id")

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'



class FormaPagoForm(BaseForm):
    # Efectivo
    valor = forms.FloatField(label=u"Valor", initial='0.00', widget=forms.TextInput(attrs={'class': 'imp-moneda form-control'}))
    formadepago = forms.ModelChoiceField(label=u'Forma de Pago', queryset=FormaDePago.objects.all().exclude(id=FORMA_PAGO_CTAXCRUZAR), widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    #campos descuento
    totaldescuento = forms.FloatField(label=u"Total descuento ", initial='0.00', widget=forms.TextInput(attrs={'class': 'imp-moneda form-control'}))
    # Cheque
    cuentacheque = forms.CharField(label=u'Número Cuenta', max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    numero = forms.CharField(label=u'Número Cheque', max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    bancocheque = forms.ModelChoiceField(label=u"Banco", queryset=Banco.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    tipocheque = forms.ModelChoiceField(label=u"Tipo de cheque", queryset=TipoCheque.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    fechacobro = forms.DateField(label=u"Fecha Cobro", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control', 'onkeydown': 'return false;'}), required=False)
    emite = forms.CharField(label=u"Emisor", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    # Tarjeta
    tipoemisortarjeta = forms.ModelChoiceField(label=u"Tipo de emisor tarjeta", queryset=TipoEmisorTarjeta.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    tipotarjeta = forms.ModelChoiceField(label=u"Tipo de tarjeta", queryset=TipoTarjeta.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    bancotarjeta = forms.ModelChoiceField(label=u"Banco", queryset=Banco.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    procesadorpago = forms.ModelChoiceField(label=u"Procesador de Pago", queryset=ProcesadorPagoTarjeta.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    tipo = forms.ModelChoiceField(label=u"Tipo", queryset=TipoTarjetaBanco.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    diferido = forms.ModelChoiceField(label=u"Pago diferido a", queryset=DiferidoTarjeta.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    referencia = forms.CharField(label=u"Referencia", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    lote = forms.CharField(label=u"Lote", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    poseedor = forms.CharField(label=u'Poseedor', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    autorizaciontar = forms.CharField(label=u'Autorización', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    # Transferencia/Deposito
    referenciatransferencia = forms.CharField(label=u'Referencia', max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    cuentabanco = forms.ModelChoiceField(label=u"Cuenta", queryset=CuentaBanco.objects.filter(activo=True), required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    tipotransferencia = forms.ModelChoiceField(label=u"Tipo de Transferencia", queryset=TipoTransferencia.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control', 'onkeydown': 'return false;'}), required=False)
    # Recibos de Caja Institucion
    recibocaja = forms.ModelChoiceField(label=u"Recibo de Caja", queryset=ReciboCajaInstitucion.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    # Nota de credito interna
    notacredito = forms.ModelChoiceField(label=u"Nota de Credito", queryset=NotaCredito.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    # Retencion
    numeroret = forms.CharField(label=u'Numero', max_length=20, required=False)
    autorizacion = forms.CharField(label=u'Autorización', max_length=20, required=False)
    fecharet = forms.DateField(label=u"Fecha emision", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), required=False)

    def adicionar(self, inscripcion):
        formaspago = FormaDePago.objects.all().exclude(id=FORMA_PAGO_CTAXCRUZAR).order_by("id")
        self.fields['diferido'].queryset = DiferidoTarjeta.objects.filter(id=0)
        if inscripcion.tiene_nota_credito():
            self.fields['notacredito'].queryset = inscripcion.notacredito_set.filter(saldo__gt=0)
        else:
            del self.fields['notacredito']
            formaspago = formaspago.exclude(id=FORMA_PAGO_NOTA_CREDITO)
        if inscripcion.tiene_recibo_caja():
            self.fields['recibocaja'].queryset = ReciboCajaInstitucion.objects.filter(inscripcion=inscripcion, saldo__gt=0)
        else:
            del self.fields['recibocaja']
            formaspago = formaspago.exclude(id=FORMA_PAGO_RECIBOCAJAINSTITUCION)
        self.fields['formadepago'].queryset = formaspago
        deshabilitar_campo(self, 'totaldescuento')


class EliminarRubroForm(BaseForm):
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'


class LiquidarNotaCreditoForm(BaseForm):
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '4', 'class':'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'


class ChequeProtestadoForm(BaseForm):
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '4', 'class':'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'



class ChequeFechaCobroForm(BaseForm):
    fechacobro = forms.DateField(label=u"Fecha Cobro", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class RetiradoMatriculaForm(BaseForm):
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}))
    archivo = forms.FileField(label=u'Seleccione Evidencias', help_text=u'Tamaño máximo permitido 10Mb, en formato pdf', required=False, widget=forms.FileInput(attrs={'accept': '.pdf', 'data-max-file-size':10240}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class CambioFechaAsignacionMateriaForm(BaseForm):
    fecha = forms.DateField(label=u"Fecha", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'

class RetiradoMateriaForm(BaseForm):
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '4', 'class':'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'

class RetiradoCarreraForm(BaseForm):
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'

class FechaMatriculaForm(BaseForm):
    fecha = forms.DateField(label=u"Fecha Cobro", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class FechaPeriodoEvaluacionesForm(BaseForm):
    califdesde = forms.DateField(label=u"Fecha inicio", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    califhasta = forms.DateField(label=u"Fecha fin", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'

class CronoramaCalificacionesForm(BaseForm):
    nombre = forms.CharField(label=u"Nombre", max_length=200)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class PeriodoForm(BaseForm):
    nombre = forms.CharField(label=u"Nombre", max_length=200)
    inicio = forms.DateField(label=u"Inicio", input_formats=['%d-%m-%Y'], initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    fin = forms.DateField(label=u"Fin", input_formats=['%d-%m-%Y'], initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    tipo = forms.ModelChoiceField(label=u"Tipo de período", queryset=TipoPeriodo.objects.all(), widget=forms.Select())
    valida_asistencia = forms.BooleanField(label=u"Validar asistencias", required=False, initial=True)
    extendido = forms.BooleanField(label=u"Extendido", required=False, initial=True)
    visualiza = forms.BooleanField(label=u"Visualiza Docentes", required=False, initial=True)
    inicio_agregacion = forms.DateField(label=u"Inicio agregaciones", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    limite_agregacion = forms.DateField(label=u"Límite agregaciones", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class CronogramaMatriculacionForm(BaseForm):
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Carrera.objects.all(), required=False)
    modalidad = forms.ModelChoiceField(label=u"Modalidad", queryset=Modalidad.objects.all(), widget=forms.Select(), required=False)
    nivelmalla = forms.ModelChoiceField(label=u"Nivel", queryset=NivelMalla.objects.all(), required=False, widget=forms.Select())
    inicio = forms.DateField(label=u"Fecha inicio", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    fin = forms.DateField(label=u"Fecha Fin", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self):
        deshabilitar_campo(self, 'carrera')
        deshabilitar_campo(self, 'modalidad')
        deshabilitar_campo(self, 'nivelmalla')


class PlanificacionForm(BaseForm):
    creditos = forms.FloatField(label=u"Créditos", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '4', 'disabled': 'disabled'}))
    horas = forms.FloatField(label=u"Horas totales", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1', 'disabled': 'disabled'}))
    horasasistidasporeldocente = forms.FloatField(label=u"Horas del aprendizaje en contacto con el docente", widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    horasautonomas = forms.FloatField(label=u"Horas autónomas", widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    horaspracticas = forms.FloatField(label=u"Horas de aprendizaje práctico experimental", widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    competenciaespecificaperfildeegreso = ModelChoiceField(label=u'Competencia específica del perfil de egreso con la cual se relaciona este proyecto', queryset=CompetenciaEspecifica.objects, required=False, widget=forms.Select())
    competenciaespecificaproyectoformativo = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Competencia específica del proyecto formativo')
    competenciagenericainstitucion = ModelChoiceField(label=u'Competencia generica que se contribuye a desarrollar', queryset=CompetenciaGenerica.objects, required=False, widget=forms.Select())
    contribucioncarrera = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Contribución al perfil de egreso')
    problemaabordadometodosdeensenanza = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Reto o problema del contexto a ser abordado')
    proyectofinal = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Producto central a lograr')
    transversalidad = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Transversalidad')

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'xl'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, malla):
        self.fields['competenciaespecificaperfildeegreso'].queryset = malla.competenciasespecificas.all()


class ImportarPlanificacionForm(BaseForm):
    materia = ModelChoiceField(label=u'Materia', queryset=Materia.objects.all(), required=False)

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'xl'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, materia, profesor, periodo):
        if materia.asignaturamalla:
            self.fields['materia'].queryset = Materia.objects.filter(Q(planificacionmateria__aprobado=True, asignaturamalla=materia.asignaturamalla,profesormateria__profesor=profesor) |  Q(planificacionmateria__aprobado=True, profesormateria__profesor=profesor,asignatura=materia.asignatura, horas=materia.horas)).distinct()
        if materia.modulomalla:
            self.fields['materia'].queryset = Materia.objects.filter(Q(planificacionmateria__aprobado=True, modulomalla=materia.modulomalla) | Q(planificacionmateria__silabomodulomalla__habilitado=True, asignatura=materia.asignatura, horas=materia.horas)).distinct()


class ImportarTallerForm(BaseForm):
    materia = ModelChoiceField(label=u'Materia', queryset=Materia.objects.all(), required=False)
    taller = ModelChoiceField(label=u'Taller', queryset=TallerPlanificacionMateria.objects.all(), required=False)

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'xl'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, materia, profesor, periodo):
        if materia.asignaturamalla:
            self.fields['materia'].queryset = Materia.objects.filter(Q(planificacionmateria__aprobado=True, asignaturamalla=materia.asignaturamalla, profesormateria__profesor=profesor) |  Q(planificacionmateria__aprobado=True, asignatura=materia.asignatura, horas=materia.horas, profesormateria__profesor=profesor)).distinct()
            self.fields['taller'].queryset = TallerPlanificacionMateria.objects.filter(id=0)
        if materia.modulomalla:
            self.fields['materia'].queryset = Materia.objects.filter(Q(planificacionmateria__silabomodulomalla__habilitado=True, modulomalla=materia.modulomalla, profesormateria__profesor=profesor) | Q(planificacionmateria__silabomodulomalla__habilitado=True, asignatura=materia.asignatura, horas=materia.horas, profesormateria__profesor=profesor)).distinct()
            self.fields['taller'].queryset = TallerPlanificacionMateria.objects.filter(id=0)

class TallerPlanificacionForm(BaseForm):
    nombretaller = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Título del taller')
    resultadoaprendizaje = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Resultado de aprendizaje')
    productoesperado = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Producto esperado del taller')
    recursosutilizados = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Recursos utilizados')
    dimensionprocedimental = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Dimensión procedimental')

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'xl'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'

class ContenidoTallerForm(BaseForm):
    contenido = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Contenido')

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'


class RubricaTallerPlanificacionForm(BaseForm):
    resultadoaprendizaje = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Resultado de aprendizaje')
    evidencia = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}), label=u'Producto esperado del taller')
    criterio = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}), label=u'Indicadores')
    logroexcelente = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}), label=u'Excelente')
    logroavanzado = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}), label=u'Muy Bueno')
    logromedio = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}), label=u'Bueno')
    logrobajo = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}), label=u'Regular')
    logrodeficiente = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}), label=u'Deficiente')

    def taller(self, modelo):
        deshabilitar_campo(self, 'resultadoaprendizaje')
        if modelo == 2:
            deshabilitar_campo(self, 'evidencia')

    def planificacion(self):
        del self.fields['resultadoaprendizaje']

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'xl'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'


class ContenidoTallerForm(BaseForm):
    contenido = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Contenido')

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'





class ClaseTallerNuevaForm(BaseForm):
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), required=False)
    fechafin = forms.DateField(label=u"Fecha fin actividad", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), required=False)
    fasesactividadesarticulacion = ModelChoiceField(label=u'Tipo de actividad a realizar en el taller', required=False, queryset=FasesActividadesArticulacion.objects, widget=forms.Select())
    contenido = ModelChoiceField(label=u'Contenido', required=False, queryset=ContenidosTallerPlanificacionMateria.objects, widget=forms.Select())
    actcondoc1 = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Actividad en contacto con el docente',  required=False)
    horas1 = forms.FloatField(label=u'Horas', initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    actcondoc2 = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}),label=u'Otra actividad en contacto con el docente', required=False)
    horas2 = forms.FloatField(label=u'Horas', initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    actividadauto = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Actividad de trabajo autónomo', required=False)
    horas4 = forms.FloatField(label=u'Horas', initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    actividadprac = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Actividad práctica experimental', required=False)
    horas5 = forms.FloatField(label=u'Horas', initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    actcolaborativas = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}),  label=u'Actividad de aprendizaje colaborativo', required=False)

    def quitar_campos(self):
        del self.fields['actcolaborativas']

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, taller):
        self.fields['contenido'].queryset = ContenidosTallerPlanificacionMateria.objects.filter(tallerplanificacionmateria=taller)

    def editar(self, taller):
        self.fields['contenido'].queryset = ContenidosTallerPlanificacionMateria.objects.filter(tallerplanificacionmateria=taller)


class ArchivoPlanificacionForm(BaseForm):
    archivo = ExtFileField(required=False, label=u'Seleccione archivo', help_text=u'Tamaño máximo permitido 40Mb, en formato doc, docx, pdf', ext_whitelist=(".doc", ".docx", ".pdf"), max_upload_size=41943040)

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class ImportarPlanificacionForm(BaseForm):
    materia = ModelChoiceField(label=u'Materia', queryset=Materia.objects.all(), required=False)

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'xl'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, materia, profesor, periodo):
        if materia.asignaturamalla:
            self.fields['materia'].queryset = Materia.objects.filter(Q(planificacionmateria__aprobado=True, asignaturamalla=materia.asignaturamalla,profesormateria__profesor=profesor) |  Q(planificacionmateria__aprobado=True, profesormateria__profesor=profesor,asignatura=materia.asignatura, horas=materia.horas)).distinct()
        if materia.modulomalla:
            self.fields['materia'].queryset = Materia.objects.filter(Q(planificacionmateria__aprobado=True, modulomalla=materia.modulomalla) | Q(planificacionmateria__silabomodulomalla__habilitado=True, asignatura=materia.asignatura, horas=materia.horas)).distinct()


class ImportarTallerForm(BaseForm):
    materia = ModelChoiceField(label=u'Materia', queryset=Materia.objects.all(), required=False)
    taller = ModelChoiceField(label=u'Taller', queryset=TallerPlanificacionMateria.objects.all(), required=False)

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'xl'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, materia, profesor, periodo):
        if materia.asignaturamalla:
            self.fields['materia'].queryset = Materia.objects.filter(Q(planificacionmateria__aprobado=True, asignaturamalla=materia.asignaturamalla, profesormateria__profesor=profesor) |  Q(planificacionmateria__aprobado=True, asignatura=materia.asignatura, horas=materia.horas, profesormateria__profesor=profesor)).distinct()
            self.fields['taller'].queryset = TallerPlanificacionMateria.objects.filter(id=0)
        if materia.modulomalla:
            self.fields['materia'].queryset = Materia.objects.filter(Q(planificacionmateria__silabomodulomalla__habilitado=True, modulomalla=materia.modulomalla, profesormateria__profesor=profesor) | Q(planificacionmateria__silabomodulomalla__habilitado=True, asignatura=materia.asignatura, horas=materia.horas, profesormateria__profesor=profesor)).distinct()
            self.fields['taller'].queryset = TallerPlanificacionMateria.objects.filter(id=0)



class TallerPlanificacionNuevaForm(BaseForm):
    nombretaller = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Título del taller')
    resultadoaprendizaje = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Resultado de aprendizaje')
    productoesperado = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Producto esperado del taller')
    recursosutilizados = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), label=u'Recursos utilizados')

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'xl'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'

class BibliografiaPlanificacionForm(BaseForm):
    digital = forms.BooleanField(initial=False, required=False, label=u'Digital')
    url = forms.CharField(label=u"Url", required=False, max_length=100, widget=forms.TextInput())
    codigo = forms.CharField(label=u"Código", required=False, max_length=100, widget=forms.TextInput())
    titulo = forms.CharField(label=u"Título", required=False, max_length=100, widget=forms.TextInput())
    autor = forms.CharField(label=u"Autor", required=False, max_length=100, widget=forms.TextInput())
    editorial = forms.CharField(label=u"Editorial", required=False, max_length=100, widget=forms.TextInput())
    anno = forms.CharField(label=u"Año Edición", required=False, max_length=100, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class BibliografiaPlanificacionForm(BaseForm):
    digital = forms.BooleanField(initial=False, required=False, label=u'Digital')
    url = forms.CharField(label=u"Url", required=False, max_length=100, widget=forms.TextInput())
    codigo = forms.CharField(label=u"Código", required=False, max_length=100, widget=forms.TextInput())
    titulo = forms.CharField(label=u"Título", required=False, max_length=100, widget=forms.TextInput())
    autor = forms.CharField(label=u"Autor", required=False, max_length=100, widget=forms.TextInput())
    editorial = forms.CharField(label=u"Editorial", required=False, max_length=100, widget=forms.TextInput())
    anno = forms.CharField(label=u"Año Edición", required=False, max_length=100, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class IndicadoresRubricaForm(BaseForm):
    criterio = forms.CharField(required=True, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}), label=u'Indicadores')
    logrodeficiente = forms.CharField(required=True, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}), label=u'Deficiente')
    logroregular = forms.CharField(required=True, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}), label=u'Regular')
    logrobueno = forms.CharField(required=True, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}), label=u'Bueno')
    logromuybueno = forms.CharField(required=True, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}), label=u'Muy Bueno')
    logroexcelente = forms.CharField(required=True, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}), label=u'Excelente')

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'xl'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'

class ObservacionesPlanoficacionForm(BaseForm):
    observaciones = forms.CharField(label=u'Observaciones', required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'

class SolicitudAperturaClaseForm(BaseForm):
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}), required=False)
    turno = ModelChoiceField(label=u'Turno', queryset=Turno.objects.all(), required=False, widget=forms.Select())
    documento = forms.FileField(label=u'Seleccione un pdf', help_text=u'Tamaño máximo permitido 4mb, en formato pdf',  widget=forms.FileInput(attrs={'accept': '.pdf', 'data-max-file-size': 4080}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class SolicitudIngresoNotasForm(BaseForm):
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}), required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'

class ActualizarDatosFacturaForm(BaseForm):
    facturaidentificacion = forms.CharField(max_length=20, label=u'Factura-Identificación', widget=forms.TextInput())
    facturatipoidentificacion = forms.ChoiceField(label=u'Factura-Tipo identificación', choices=TiposIdentificacion, widget=forms.Select())
    facturanombre = forms.CharField(max_length=100, label=u'Factura-Nombre beneficiario', widget=forms.TextInput())
    facturadireccion = forms.CharField(max_length=100, label=u"Factura-Dirección", widget=forms.TextInput())
    facturatelefono = forms.CharField(max_length=50, label=u"Factura-Teléfono", widget=forms.TextInput())
    facturaemail = forms.CharField(max_length=50, label=u"Factura-Email", widget=forms.TextInput())


class ArchivoSyllabusMallaForm(BaseForm):
    nombre = forms.CharField(label=u"Nombre")
    archivo = ExtFileField(label=u'Seleccione archivo', help_text=u'Tamaño máximo permitido 40Mb, en formato doc, docx', ext_whitelist=(".doc", ".docx"), max_upload_size=41943040, required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class ArchivoDeberForm(BaseForm):
    observaciones = forms.CharField(label=u'Observaciones', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    archivo = ExtFileField(label=u'Seleccione archivo', help_text=u'Tamaño máximo permitido 40Mb, en formato doc, docx, xls, xlsx, pdf, ppt, pptx, rar, zip, txt', ext_whitelist=(".doc", ".docx", ".xls", ".xlsx", ".pdf", ".ppt", ".pptx", ".zip", ".rar", ".txt"), max_upload_size=41943040)



class ContenidoAcademicoForm(BaseForm):
    contenido = forms.CharField(label=u'Tema y Subtema', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    estrategiasmetodologicas = forms.CharField(label=u'Estrategias Metodologicas', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    observaciones = forms.CharField(label=u'Observaciones', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    clasestallerplanificacionmateria = forms.ModelChoiceField(label=u"Clases", queryset=ClasesTallerPlanificacionMateria.objects.all(), widget=forms.Select(), required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'

    def adicionar(self, lecciongrupo):
        self.fields['clasestallerplanificacionmateria'].queryset = ClasesTallerPlanificacionMateria.objects.filter(tallerplanificacionmateria__planificacionmateria__materia__in=[x.clase.materia for x in lecciongrupo.lecciones.all()], fecha=lecciongrupo.fecha)



class ActividadInscripcionForm(BaseForm):
    inscripcion = forms.IntegerField(initial='', required=False, label=u'Participante', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    tipo = forms.ModelChoiceField(label=u"Tipo de registro", queryset=TipoEstudianteCurso.objects.all(), required=False, widget=forms.Select())
    locacion = forms.ModelChoiceField(label=u"Locacion", queryset=LocacionesCurso.objects.all(), required=False, widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def transferir(self, recibo):
        self.fields['inscripcion'].widget.attrs['descripcion'] = recibo.inscripcion.flexbox_repr()

    def adicionar(self, curso):
        if not curso.costodiferenciado:
            del self.fields['tipo']
        else:
            self.fields['tipo'].queryset = TipoEstudianteCurso.objects.filter(Q(costodiferenciadocursoperiodo__costomatricula__gt=0) | Q(costodiferenciadocursoperiodo__costocuota__gt=0), costodiferenciadocursoperiodo__tipocostocursoperiodo__tipocostocurso__cursoescuelacomplementaria=curso).distinct()
        if curso.locacionescurso_set.count() > 1:
            self.fields['locacion'].queryset = LocacionesCurso.objects.filter(curso=curso, activo=True)
        else:
            del self.fields['locacion']

    def adicionar_unidad_tit(self):
        del self.fields['locacion']
        del self.fields['tipo']

    def autoregistro(self, curso):
        del self.fields['tipo']
        del self.fields['inscripcion']
        self.fields['locacion'].queryset = LocacionesCurso.objects.filter(curso=curso, activo=True)




class SesionCajaForm(BaseForm):
    caja = forms.ModelChoiceField(label=u"Caja", queryset=LugarRecaudacion.objects, widget=forms.Select())
    fondo = forms.FloatField(label=u"Fondo Inicial", initial='0.00', widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2'}))

    def adicionar(self, miscajas):
        self.fields['caja'].queryset = miscajas.filter(automatico=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class CierreSesionCajaForm(BaseForm):
    fondoinicial = forms.FloatField(label=u"Fondo inicial", initial='0.00', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2', 'disabled': 'disabled'}))
    bill100 = forms.IntegerField(label=u"Cant. de billetes de 100", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    bill50 = forms.IntegerField(label=u"Cant. de billetes de 50", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    bill20 = forms.IntegerField(label=u"Cant. de billetes de 20", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    bill10 = forms.IntegerField(label=u"Cant. de billetes de 10", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    bill5 = forms.IntegerField(label=u"Cant. de billetes de 5", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    bill2 = forms.IntegerField(label=u"Cant. de billetes de 2", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    bill1 = forms.IntegerField(label=u"Cant. de billetes de 1", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    enmonedas = forms.FloatField(label=u"Valor en monedas", initial='0.00', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2'}))
    deposito = forms.FloatField(label=u"Valor en depositos", initial='0.00', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2', 'disabled': 'disabled'}))
    transferencia = forms.FloatField(label=u"Valor en transferencia", initial='0.00', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2', 'disabled': 'disabled'}))
    cheque = forms.FloatField(label=u"Valor en cheques", initial='0.00', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2', 'disabled': 'disabled'}))
    tarjeta = forms.FloatField(label=u"Valor en tarjetas", initial='0.00', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2', 'disabled': 'disabled'}))
    reciboscaja = forms.FloatField(label=u"Recibos de caja", initial='0.00', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2', 'disabled': 'disabled'}))
    notacreditointerna = forms.FloatField(label=u"Nota credito", initial='0.00', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2', 'disabled': 'disabled'}))
    valecajaentregado = forms.FloatField(label=u"Vales de caja(-)", initial='0.00', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2', 'disabled': 'disabled'}))
    valecajadevuelto = forms.FloatField(label=u"Vales de caja(+)", initial='0.00', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2', 'disabled': 'disabled'}))
    total = forms.FloatField(label=u"Valor Comprobacion", initial='0.00', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2', 'disabled': 'disabled'}))
    totalrecaudado = forms.FloatField(label=u"Valor recaudado total", initial='0.00', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2', 'disabled': 'disabled'}))

    def editar(self):
        deshabilitar_campo(self, 'total')

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class PagoForm(BaseForm):
    valor = forms.FloatField(label=u"Valor", initial='0.00', widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2'}))
    factura = forms.IntegerField(label=u"No. Factura")
    facturaidentificacion = forms.CharField(label=u'RUC/Cedula', max_length=20)
    facturanombre = forms.CharField(label=u'Nombre', max_length=100)
    facturadireccion = forms.CharField(label=u"Dirección", max_length=100)
    facturatelefono = forms.CharField(label=u"Teléfono", max_length=50)
    formadepago = forms.ModelChoiceField(label=u'Forma de Pago', queryset=FormaDePago.objects.all())
    # Efectivo
    # Cheque
    numero = forms.CharField(label=u'Numero Cheque', max_length=50, required=False)
    bancocheque = forms.ModelChoiceField(label=u"Banco", queryset=Banco.objects.all(), required=False)
    fechacobro = forms.DateField(label=u"Fecha Cobro", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), required=False)
    emite = forms.CharField(label=u"Emisor", max_length=100, required=False)
    # Tarjeta
    referencia = forms.CharField(label=u"Referencia", max_length=50, required=False)
    bancotarjeta = forms.ModelChoiceField(label=u"Banco", queryset=Banco.objects.all(), required=False)
    tipo = forms.ModelChoiceField(label=u"Tipo", queryset=TipoTarjetaBanco.objects.all(), required=False)
    poseedor = forms.CharField(label=u'Poseedor', max_length=100, required=False)
    procesadorpago = forms.ModelChoiceField(label=u"Procesador de Pago", queryset=ProcesadorPagoTarjeta.objects.all(), required=False)
    # Transferencia/Deposito
    referenciatransferencia = forms.CharField(label=u'Referencia', max_length=50, required=False)
    cuentabanco = forms.ModelChoiceField(label=u"Cuenta", queryset=CuentaBanco.objects.filter(activo=True), required=False)


class FacturaCanceladaForm(BaseForm):
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '200', 'class': 'form-control'}))

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'lg'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class ReciboPagoCanceladoForm(BaseForm):
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '200'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'


class NotaCreditoForm(BaseForm):
    puntoemision = forms.ModelChoiceField(label=u"Punto Emisión", queryset=PuntoVenta.objects.all(), required=False, widget=forms.Select())
    numero = forms.CharField(label=u"Número", max_length=9, required=False, widget=forms.TextInput())
    inscripcion = forms.IntegerField(initial='', required=False, label=u'Estudiante', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), )
    valorinicial = forms.FloatField(label=u'Valor', initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self, notacredito):
        self.fields['inscripcion'].widget.attrs['descripcion'] = notacredito.inscripcion.flexbox_repr()
        del self.fields['puntoemision']
        deshabilitar_campo(self, 'numero')



class NotaCreditoImportadaForm(BaseForm):
    inscripcion = forms.IntegerField(initial='', required=False, label=u'Estudiante', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))

    def editar(self, notacredito):
        self.fields['inscripcion'].widget.attrs['descripcion'] = notacredito.inscripcion.flexbox_repr() if notacredito.inscripcion else ''

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class ImportarNotaCreditoForm(BaseForm):
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), )

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formwidth'].initial = 'md'

class ValeCajaForm(BaseForm):
    tipo = forms.ChoiceField(choices=TIPOS_VALE_CAJA, label=u'Tipo', required=False, widget=forms.Select())
    recibe = forms.IntegerField(initial='', required=False, label=u'Recibe', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    responsable = forms.IntegerField(initial='', required=False, label=u'Autoriza', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    referencia = forms.CharField(label=u'Referencia', max_length=100, required=False, widget=forms.TextInput())
    concepto = forms.CharField(label=u'Concepto', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}))
    valor = forms.FloatField(label=u'Valor', initial='0.00', widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2'}))

    def editar(self, vale):
        deshabilitar_campo(self, 'tipo')
        if vale.recibe:
            self.fields['recibe'].widget.attrs['descripcion'] = vale.recibe.flexbox_repr()
        if vale.responsable:
            self.fields['responsable'].widget.attrs['descripcion'] = vale.responsable.flexbox_repr()


class ReciboCajaForm(BaseForm):
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), )
    inscripcion = forms.IntegerField(initial='', required=False, label=u'Estudiante', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    motivo = forms.CharField(label=u'Motivo', required=False, widget=forms.Textarea(attrs={'rows': '5', 'class': 'form-control'}))
    valorinicial = forms.FloatField(label=u'Valor', initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-moneda'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def transferir(self, recibo):
        self.fields['inscripcion'].widget.attrs['descripcion'] = recibo.inscripcion.flexbox_repr()

class TransferenciaForm(BaseForm):
    tipotransferencia = forms.ModelChoiceField(label=u"Tipo de Transferencia", queryset=TipoTransferencia.objects.all(), required=False)
    cuentabanco = forms.ModelChoiceField(label=u"Cuenta", queryset=CuentaBanco.objects.filter(activo=True), widget=forms.Select())
    referencia = forms.CharField(max_length=50, label=u"Referencia", required=False, widget=forms.TextInput())
    valor = forms.FloatField(label=u"Valor", initial="0.00", widget=forms.TextInput(attrs={'class': 'form-control imp-moneda'}))
    fechabanco = forms.DateField(label=u"Fecha Banco", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'form-control selectorfecha', 'onkeydown': 'return false;'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class DepositoForm(BaseForm):
    cuentabanco = forms.ModelChoiceField(label=u"Cuenta", queryset=CuentaBanco.objects.filter(activo=True), widget=forms.Select())
    referencia = forms.CharField(max_length=50, label=u"No. Comprobate", required=False, widget=forms.TextInput())
    valor = forms.FloatField(label=u"Valor", initial="0.00", widget=forms.TextInput(attrs={'class': 'form-control imp-moneda'}))
    fechabanco = forms.DateField(label=u"Fecha Banco", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'form-control selectorfecha', 'onkeydown': 'return false;'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class TecnologicoUniversidadForm(BaseForm):
    nombre = forms.CharField(label=u"Nombre", required=False, max_length=100,widget=forms.TextInput())
    tipotecnologicouniversidad = forms.ModelChoiceField(label='Tipo Universidad', queryset=TipoTecnologicoUniversidad.objects.all(), required=False, widget=forms.Select())
    universidad = forms.BooleanField(label=u" Es una universidad", required=False, initial=True)
    pais = forms.ModelChoiceField(label= u'País', queryset=Pais.objects.all(),required=False, widget=forms.Select())
    codigosniese = forms.CharField(label=u'Código Sniese', required=False, max_length=100, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class DepositoInscripcionForm(BaseForm):
    cuentabanco = forms.ModelChoiceField(label=u"Banco", queryset=CuentaBanco.objects.filter(activo=True), widget=forms.Select())
    ventanilla = forms.BooleanField(label=u"Pago en ventanilla/Depósito", initial=False, required=False, widget=forms.CheckboxInput(attrs={'class': 'sizecheckmd'}))
    movilweb = forms.BooleanField(label=u"Pago con aplicación móvil-web/Transf.", initial=False, required=False, widget=forms.CheckboxInput(attrs={'class': 'sizecheckmd'}))
    fecha = forms.DateField(label=u"Fecha de transacción", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    valor = forms.FloatField(label=u"Valor", initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    referencia = forms.CharField(max_length=50, label=u"No. Comprobate", required=False, widget=forms.TextInput())
    motivo = forms.CharField(label=u"Observación", max_length=150, required=False)
    archivo = forms.FileField(label=u"Carga de documento",required=False, help_text=u"Tamaño máximo permitido 40Mb, en formato jpg, png", widget=forms.FileInput(attrs={'accept': '.jpg, .jpeg, .png','data-max-file-size': 41943040}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self):
        del self.fields['archivo']

    def estudiante(self):
        del self.fields['motivo']


class DepositoInscripcionMotivoForm(BaseForm):
    motivo = forms.CharField(label=u"Motivo", max_length=150, required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self):
        del self.fields['archivo']


class ReasignarDepositosResponsableForm(BaseForm):
    responsable = forms.ModelChoiceField(label=u"Personal ", queryset=Persona.objects.filter(pk__in=CAJAS_DEPOSITOS), required=False,  widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class CarreraForm(BaseForm):
    nombre = forms.CharField(label=u"Nombre", max_length=100)
    nombreingles = forms.CharField(label=u"Nombre en Ingles", max_length=100)
    mencion = forms.CharField(label=u"Mención", max_length=100, required=False)
    alias = forms.CharField(label=u"Alias", max_length=50, widget=forms.TextInput())
    tipogrado = forms.ModelChoiceField(label=u'Nivel Titulación', queryset=NivelTitulacion.objects.all(),required=False, widget=forms.Select())
    tiposubgrado = forms.ModelChoiceField(label=u'Detalle Nivel Titulación', queryset=DetalleNivelTitulacion.objects.all(), required=False, widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self):
        self.fields['tiposubgrado'].queryset = DetalleNivelTitulacion.objects.filter(id=0)

    def editar(self, carrera):
        self.fields['tiposubgrado'].queryset = DetalleNivelTitulacion.objects.filter(niveltitulacion=carrera.tipogrado)


# class TituloCarreraForm(BaseForm):
#     titulo = forms.ModelChoiceField(label=u'Título obtenido', queryset=TituloObtenido.objects.all(), required=False, widget=forms.Select())
#
#     def extra_paramaters(self):
#         self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class TituloForm(BaseForm):
    nombre = forms.CharField(label=u"Nombre", max_length=200, required=False, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class ResponsableCarreraForm(BaseForm):
    responsable = forms.IntegerField(initial='', required=False, label=u'Responsable', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self, coordinacion, carrera, modalidad):
        responsable = coordinacion.responsable_carrera(carrera, modalidad)
        if responsable:
            self.fields['responsable'].widget.attrs['descripcion'] = responsable.persona.flexbox_repr()
            self.fields['firmadignidad'].widget.attrs['descripcion'] = responsable.firmadignidad
            self.fields['responsable'].widget.attrs['va'] = responsable.persona.id


class ResponsableCoordinacionForm(BaseForm):
    responsable = forms.IntegerField(initial='', required=False, label=u'Responsable', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self, coordinacion):
        responsable = coordinacion.responsable()
        if responsable:
            self.fields['responsable'].widget.attrs['descripcion'] = responsable.persona.flexbox_repr()
            self.fields['firmadignidad'].widget.attrs['descripcion'] = responsable.firmadignidad
            self.fields['responsable'].widget.attrs['va'] = responsable.persona.id


class SecretariaCoordinacionForm(BaseForm):
    responsable = forms.IntegerField(initial='', required=False, label=u'Responsable', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    carrera = forms.ModelChoiceField(label=u'Carrera', queryset=Carrera.objects.all(), required=False, widget=forms.Select())
    modalidad = forms.ModelChoiceField(label=u'Modalidad', queryset=Modalidad.objects.all(), required=False, widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, coordinacion):
        self.fields['carrera'].queryset = coordinacion.carrera.all()


class CarreraCoordinacionForm(BaseForm):
    carrera = forms.ModelChoiceField(label=u'Carrera', queryset=Carrera.objects.all(), required=False, widget=forms.Select())
    responsable = forms.IntegerField(initial='', required=False, label=u'Responsable', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    modalidad = forms.ModelChoiceField(label=u'Modalidad', queryset=Modalidad.objects.all(), widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, coordinacion):
        self.fields['carrera'].queryset = Carrera.objects.exclude().distinct()


class CoordinacionForm(BaseForm):
    sede = forms.ModelChoiceField(label=u'Sede', queryset=Sede.objects.all(), required=False, widget=forms.Select())
    nombre = forms.CharField(max_length=100, label=u"Nombre", required=False, widget=forms.TextInput())
    nombreingles = forms.CharField(max_length=100, label=u"Nombre en ingles", required=False, widget=forms.TextInput())
    alias = forms.CharField(max_length=20, label=u"Alias", required=False, widget=forms.TextInput())
    estado = forms.BooleanField(label=u"Activa?", required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self):
        deshabilitar_campo(self, 'sede')

class CargoPersonaForm(BaseForm):
    cargo = forms.ModelChoiceField(label=u'Cargo', queryset=Cargo.objects.all(), required=False, widget=forms.Select())
    persona = forms.IntegerField(initial='', required=False, label=u'Responsable', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class CajeroForm(BaseForm):
    nombre = forms.CharField(label=u'Nombre de Caja', widget=forms.TextInput, max_length=100)
    cajero = forms.ModelChoiceField(label=u'Cajero', queryset=Persona.objects.filter(administrativo__isnull=False), required=False, widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class IvaForm(BaseForm):
    descripcion = forms.CharField(label=u'Descripción', )
    codigo = forms.IntegerField(label=u'Código', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    porcientoiva = forms.FloatField(label=u"Porciento", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class SedeForm(BaseForm):
    nombre = forms.CharField(max_length=100, label=u"Nombre", required=False, widget=forms.TextInput())
    alias = forms.CharField(label=u"Alias", max_length=50, widget=forms.TextInput())
    provincia = forms.ModelChoiceField(label=u"Provincia", queryset=Provincia.objects.all(), required=False, widget=forms.Select())
    canton = forms.ModelChoiceField(label=u"Cantón", queryset=Canton.objects.all(), required=False, widget=forms.Select())
    parroquia = forms.ModelChoiceField(label=u"Parroquia", queryset=Parroquia.objects.all(), required=False, widget=forms.Select())
    sector = forms.CharField(max_length=100, label=u"Sector", required=False, widget=forms.TextInput())
    ciudad = forms.CharField(max_length=50, label=u"Ciudad", required=False, widget=forms.TextInput())
    direccion = forms.CharField(max_length=100, label=u"Calle principal", required=False, widget=forms.TextInput())
    telefono = forms.CharField(max_length=10, label=u"Teléfono fijo", required=False, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self):
        self.fields['canton'].queryset = Canton.objects.filter(id=0)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(id=0)

    def editar(self, sede):
        self.fields['canton'].queryset = Canton.objects.filter(provincia=sede.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=sede.canton)

class AulaForm(BaseForm):
    nombre = forms.CharField(label=u'Nombre', )
    tipo = forms.ModelChoiceField(label=u"Tipo", queryset=TipoAula.objects.all(), required=False, widget=forms.Select())
    capacidad = forms.IntegerField(label=u'Capacidad', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    coordinacion = forms.ModelMultipleChoiceField(label=u'Coordinaciones', queryset=Coordinacion.objects.all(), required=False, widget=CheckboxSelectMultipleCustom)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, sede):
        self.fields['coordinacion'].queryset = Coordinacion.objects.filter(sede=sede,estado=True)

    def editar(self, aula):
        self.fields['coordinacion'].queryset = Coordinacion.objects.filter(sede=aula.sede,estado=True)



class CargoForm(BaseForm):
    nombre = forms.CharField(max_length=300, label=u"Nombre", required=False, widget=forms.TextInput())
    multiples = forms.BooleanField(label=u"Multiples", required=False, widget=forms.CheckboxInput(attrs={'class': 'lcs_switch'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class CargoPersonaForm(BaseForm):
    cargo = forms.ModelChoiceField(label=u'Cargo', queryset=Cargo.objects.all(), required=False, widget=forms.Select())
    persona = forms.IntegerField(initial='', required=False, label=u'Responsable', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class ParametrosClaseForm(BaseForm):
    horarioestricto = forms.BooleanField(label=u"Clases con horario estricto", required=False)
    abrirmateriasenfecha = forms.BooleanField(label=u"Abrir materias en fecha", required=False)
    clasescontinuasautomaticas = forms.BooleanField(label=u"Clases contínuas automáticas", required=False)
    clasescierreautomatico = forms.BooleanField(label=u"Cierre automático de clases", required=False)
    minutosapeturaantes = forms.IntegerField(label=u"Minutos de apertura antes del inicio de clases", widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    minutosapeturadespues = forms.IntegerField(label=u"Minutos de apertura despues de inicio clases", widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    minutoscierreantes = forms.IntegerField(label=u"Minutos de cierre antes de terminación", widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    egresamallacompleta = forms.BooleanField(label=u"Egreca con malla completa", required=False)

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class ParametrosAplicacionForm(BaseForm):
    claveusuariocedula = forms.BooleanField(label=u"Clave de usuario cédula", required=False)
    defaultpassword = forms.CharField(max_length=100, label=u"Clave por defecto", required=False, widget=forms.TextInput())
    nombreusuariocedula = forms.BooleanField(label=u"Nombre de usuario cédula", required=False)
    actualizarfotoalumnos = forms.BooleanField(label=u"Alumnos actualizan foto", required=False)
    actualizarfotoadministrativos = forms.BooleanField(label=u"Administrativos actualizan foto", required=False)
    controlunicocredenciales = forms.BooleanField(label=u"Control único de credenciales", required=False)
    correoobligatorio = forms.BooleanField(label=u"Correo privado obligatorio", required=False)
    preguntasinscripcion = forms.BooleanField(label=u"Preguntas en inscripción obligatorias", required=False)

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'



class DatosCostosAplicacionForm(BaseForm):
    contribuyenteespecial = forms.BooleanField(label=u"Es contribuyente especial", required=False)
    obligadocontabilidad = forms.BooleanField(label=u"Obligado a llevar contabilidad", required=False)
    costoperiodo = forms.BooleanField(label=u"Usa costo por periodo", required=False)
    costoenmalla = forms.BooleanField(label=u"Usa costo en malla", required=False)
    estudiantevefecharubro = forms.BooleanField(label=u"Estudiantes ven fecha vencimiento rubro", required=False)
    matriculacondeuda = forms.BooleanField(label=u"Matricular con deuda", required=False)
    pagoestrictoasistencia = forms.BooleanField(label=u"Pago estricto asistencia", required=False)
    pagoestrictonotas = forms.BooleanField(label=u"Pago estricto notas", required=False)
    cuotaspagoestricto = forms.IntegerField(label=u"Cuotas pago estricto asistencia", widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    formalizarxporcentaje = forms.BooleanField(label=u"Formalizar la matricula por porcentaje cancelado", required=False)
    formalizarxmatricula = forms.BooleanField(label=u"Formalizar por valor de matricula cancelado", required=False)
    porcentajeformalizar = forms.FloatField(label=u"Pocentaje Formalizar", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    vencematriculaspordias = forms.BooleanField(label=u"Vence matrículas por dias", required=False)
    diashabiles = forms.BooleanField(label=u"Dias hábiles", required=False)
    diasmatriculaexpirapresencial = forms.IntegerField(label=u"Dias expira presencial", widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    diasmatriculaexpirasemipresencial = forms.IntegerField(label=u"Dias expira semipresencial", widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    diasmatriculaexpiradistancia = forms.IntegerField(label=u"Dias expira distancia", widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    diasmatriculaexpiraonline = forms.IntegerField(label=u"Dias expira Online", widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    diasmatriculaexpirahibrida = forms.IntegerField(label=u"Dias expira Hibrida", widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    fechaexpiramatriculagrado = forms.DateField(label=u"Fecha expira Grado", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    fechaexpiramatriculaposgrado = forms.DateField(label=u"Fecha expira PosGrado", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'lg'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'



class DatosBloqueoAplicacionForm(BaseForm):
    deudabloqueaasistencia = forms.BooleanField(label=u"Bloquear módulo mis materias", required=False, widget=forms.CheckboxInput(attrs={'formwidth': 400, 'labelwidth': 200, 'controlwidth': 20}))
    deudabloqueamimalla = forms.BooleanField(label=u"Bloquear módulo mi malla", required=False, widget=forms.CheckboxInput(attrs={'formwidth': 400, 'labelwidth': 200, 'controlwidth': 20}))
    deudabloqueamishorarios = forms.BooleanField(label=u"Bloquear módulo mis horarios", required=False, widget=forms.CheckboxInput(attrs={'formwidth': 400, 'labelwidth': 200, 'controlwidth': 20}))
    deudabloqueadocumentos = forms.BooleanField(label=u"Bloquear módulo descarga documentos", required=False, widget=forms.CheckboxInput(attrs={'formwidth': 400, 'labelwidth': 200, 'controlwidth': 20}))
    deudabloqueacronograma = forms.BooleanField(label=u"Bloquear módulo mi cronograma", required=False, widget=forms.CheckboxInput(attrs={'formwidth': 400, 'labelwidth': 200, 'controlwidth': 20}))
    deudabloqueamatriculacion = forms.BooleanField(label=u"Bloquear módulo matriculación", required=False, widget=forms.CheckboxInput(attrs={'formwidth': 400, 'labelwidth': 200, 'controlwidth': 20}))
    deudabloqueasolicitud = forms.BooleanField(label=u"Bloquear módulo solicitud secretaría", required=False, widget=forms.CheckboxInput(attrs={'formwidth': 400, 'labelwidth': 200, 'controlwidth': 20}))
    deudabloqueanotas = forms.BooleanField(label=u"Bloquear módulo record académico", required=False, widget=forms.CheckboxInput(attrs={'formwidth': 400, 'labelwidth': 200, 'controlwidth': 20}))

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class DatosGeneralesForm(BaseForm):
    solicitudnumeracion = forms.BooleanField(label=u"Solicitudes con numeración", required=False, widget=forms.CheckboxInput(attrs={'formwidth': 400, 'labelwidth': 200, 'controlwidth': 20}))
    solicitudnumeroautomatico = forms.BooleanField(label=u"Solicitud número automático", required=False, widget=forms.CheckboxInput(attrs={'formwidth': 400, 'labelwidth': 200, 'controlwidth': 20}))
    permitealumnoregistrar = forms.BooleanField(label=u"Permite alumno registrar", required=False, widget=forms.CheckboxInput(attrs={'formwidth': 400, 'labelwidth': 200, 'controlwidth': 20}))
    permitealumnoelegirresponsable = forms.BooleanField(label=u"Permite alumno elegir responsable", required=False, widget=forms.CheckboxInput(attrs={'formwidth': 400, 'labelwidth': 200, 'controlwidth': 20}))
    especificarcantidadsolicitud = forms.BooleanField(label=u"Se puedes especificar la cantidad solicitudes", required=False, widget=forms.CheckboxInput(attrs={'formwidth': 400, 'labelwidth': 200, 'controlwidth': 20}))
    diasvencimientosolicitud = forms.IntegerField(label=u'Días vencimiento solicitud', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall'}))

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'



class ApiForm(BaseForm):
    tipo = forms.ChoiceField(label=u'Tipo', choices=TIPO_REQUEST_CHOICES, required=True,  widget=forms.Select())
    nombrecorto = forms.CharField(max_length=50, label=u"Nombre corto", required=True, widget=forms.TextInput())
    descripcion = forms.CharField(max_length=200, label=u"Descripción", required=False, widget=forms.TextInput())
    key = forms.CharField(max_length=50, label=u"Key", required=False, widget=forms.TextInput())
    logicaapi = forms.CharField(label=u'Lógica', widget=forms.Textarea(attrs={'rows': '15', 'class': 'form-control'}), required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class DatosFacturacionAplicacionForm(BaseForm):
    facturacionelectronicaexterna = forms.BooleanField(label=u"Facturación electrónica externa", required=False)
    urlfacturacion = forms.CharField(max_length=100, label=u"URL Facturación", required=False, widget=forms.TextInput())
    apikey = forms.CharField(max_length=100, label=u"API Key", required=False, widget=forms.TextInput())
    pfx = forms.CharField(max_length=100, label=u"PFX", required=False, widget=forms.TextInput())
    codigoporcentajeiva = forms.CharField(max_length=5, label=u"Código porcentaje IVA", required=False, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class DatosUrlAplicacionForm(BaseForm):
    urlaplicacionandroid = forms.CharField(max_length=100, label=u"URL Aplicación estudiantes (Android)", required=False, widget=forms.TextInput())
    urlaplicacionios = forms.CharField(max_length=100, label=u"URL Aplicación estudiantes (IOS)", required=False, widget=forms.TextInput())
    urlaplicacionwindows = forms.CharField(max_length=100, label=u"URL Aplicación estudiantes (Windows)", required=False, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class PuntoVentaForm(BaseForm):
    establecimiento = forms.CharField(label=u'Establecimiento', required=False, widget=forms.TextInput(attrs={}),max_length=3)
    puntoventa = forms.CharField(label=u'Punto de Venta', required=False, widget=forms.TextInput(attrs={}),max_length=3)
    tipoemision = forms.ChoiceField(label=u'Tipo de emisión', choices=TIPO_EMISION_FACTURA, required=False,  widget=forms.Select())
    ambientefacturacion = forms.ChoiceField(label=u'Tipo de ambiente facturación', choices=TIPO_AMBIENTE_FACTURACION, widget=forms.Select())
    facturaelectronica = forms.BooleanField(label=u'Electrónico', required=False)
    numeracionemitida = forms.BooleanField(label=u'Número Documento', required=False)
    secuenciafactura = forms.IntegerField(label=u'Secuencia factura', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    secuencianotacredito = forms.IntegerField(label=u'Secuencia nota crédito', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    secuenciarecibopago = forms.IntegerField(label=u'Secuencia recibo pago', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center'}))
    imprimirfactura = forms.BooleanField(label=u'Imprimir factura', required=False)
    modeloimpresionfactura = forms.ModelChoiceField(label=u"Modelo Impresión Factura", queryset=ModeloImpresion.objects.all(), required=False, widget=forms.Select())
    imprimirrecibopago = forms.BooleanField(label=u'Imprimir recibo de pago', required=False)
    modeloimpresionrecibopago = forms.ModelChoiceField(label=u"Modelo Impresión Rec. Pago", queryset=ModeloImpresion.objects.all(), required=False, widget=forms.Select())
    imprimirnotacredito = forms.BooleanField(label=u'Imprimir Nota Cred.', required=False)
    modeloimpresionnotacredito = forms.ModelChoiceField(label=u"Modelo Impresión Nota Cred.", queryset=ModeloImpresion.objects.all(), required=False, widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self, punto):
        if punto.mis_cajeros():
            deshabilitar_campo(self, 'establecimiento')
            deshabilitar_campo(self, 'puntoventa')
            deshabilitar_campo(self, 'facturaelectronica')
            deshabilitar_campo(self, 'imprimirfactura')
            deshabilitar_campo(self, 'imprimirrecibopago')
            deshabilitar_campo(self, 'imprimirnotacredito')


class CuentaForm(BaseForm):
    banco = forms.ModelChoiceField(label=u"Banco", queryset=Banco.objects.all(), required=False, widget=forms.Select())
    tipocuenta = forms.ModelChoiceField(label=u"Tipo de Cuenta", queryset=TipoCuentaBanco.objects.all(), required=False, widget=forms.Select())
    numero = forms.CharField(label=u'Número Cuenta', max_length=50, required=False)
    representante = forms.CharField(label=u'Representante', )

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class TipoSolicitudForm(BaseForm):
    from django.contrib.auth.models import Group
    nombre = forms.CharField(label=u'Nombre', )
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    valor = forms.FloatField(label=u'Valor', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    costo_unico = forms.BooleanField(label=u'Costo único', required=False)
    costo_base = forms.FloatField(label=u'Costo base', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    gratismatricula = forms.BooleanField(label=u'Gratis matrícula', required=False)
    grupos = forms.ModelMultipleChoiceField(label=u'Grupos', required=False, queryset=Group.objects.all().order_by('name'), widget=CheckboxSelectMultipleCustom)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class ReferenciaWebForm(BaseForm):
    nombre = forms.CharField(max_length=200, label=u"Nombre", required=False, widget=forms.TextInput())
    descripcion = forms.CharField(label=u"Descripción", required=False, widget=forms.Textarea(attrs={'rows': '2'}))
    url = forms.CharField(max_length=200, label=u"URL", required=False, widget=forms.TextInput())
    logo = ExtFileField(label=u'Logo', required=False,
                        help_text=u'Tamaño máximo permitido 1Mb, en formato jpg, png',
                        ext_whitelist=(".jpg", ".png",), widget=forms.FileInput(attrs={'fieldheight': '50'}),
                        max_upload_size=1048576)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def referencia(self):
        del self.fields['descripcion']


class CompetenciaGenericaForm(BaseForm):
    nombre = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}), required=False, label=u"Nombre")

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class SesionForm(BaseForm):
    nombre = forms.CharField(label=u'Nombre', )
    codigo = forms.CharField(label=u'Código', max_length=15, required=False, widget=forms.TextInput())
    comienza = forms.TimeField(label=u"Comienza", input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    termina = forms.TimeField(label=u"Termina", input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    lunes = forms.BooleanField(label=u'Lunes', required=False)
    martes = forms.BooleanField(label=u'Martes', required=False)
    miercoles = forms.BooleanField(label=u'Miércoles', required=False)
    jueves = forms.BooleanField(label=u'Jueves', required=False)
    viernes = forms.BooleanField(label=u'Viernes', required=False)
    sabado = forms.BooleanField(label=u'Sábado', required=False)
    domingo = forms.BooleanField(label=u'Domingo', required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class TurnoForm(BaseForm):
    sesion = forms.ModelChoiceField(label=u"Sesión", queryset=Sesion.objects.all(), required=False, widget=forms.Select())
    comienza = forms.TimeField(label=u"Comienza", input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    termina = forms.TimeField(label=u"Termina", input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    horas = forms.FloatField(label=u"Horas", required=False, initial=0, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'



class CronogramaMatriculacionForm(BaseForm):
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Carrera.objects.all(), required=False)
    modalidad = forms.ModelChoiceField(label=u"Modalidad", queryset=Modalidad.objects.all(), widget=forms.Select(), required=False)
    nivelmalla = forms.ModelChoiceField(label=u"Nivel", queryset=NivelMalla.objects.all(), required=False, widget=forms.Select())
    inicio = forms.DateField(label=u"Fecha inicio", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    fin = forms.DateField(label=u"Fecha Fin", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self):
        deshabilitar_campo(self, 'carrera')
        deshabilitar_campo(self, 'modalidad')
        deshabilitar_campo(self, 'nivelmalla')

class GrupoSistemaForm(BaseForm):
    nombre = forms.CharField(label=u'Nombre', )

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class InfoCorreoForm(BaseForm):
    emailhost = forms.CharField(max_length=100, label=u"IP/Host", required=False, widget=forms.TextInput())
    emailport = forms.IntegerField(label=u"Puerto", widget=forms.TextInput(attrs={'class': 'imp-number', 'decimales': '0'}))
    emailhostuser = forms.CharField(max_length=100, label=u"Usuario", required=False, widget=forms.TextInput())
    emailpassword = forms.CharField(max_length=100, label=u"Contraseña", required=False, widget=forms.TextInput())
    usatls = forms.BooleanField(label=u"TLS", required=False)
    emaildomain = forms.CharField(max_length=100, label=u"Dominio de correo institucional", required=False, widget=forms.TextInput())
    domainapp = forms.CharField(max_length=100, label=u"URL aplicación", required=False, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'



class EditarLogicaModeloForm(BaseForm):
    logica = forms.CharField(label=u'Lógica', widget=forms.Textarea(attrs={'rows': '6', 'class': 'form-control'}), required=False)

    def extra_paramaters(self):
        self.fields['formwidth'].initial = ''
        self.fields['formtype'].initial = 'vertical'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'



class ColegioForm(BaseForm):
    nombre = forms.CharField(label=u"Nombre", required=False, max_length=100,widget=forms.TextInput())
    tipocolegio = forms.ModelChoiceField(label=u"Tipo colegio", queryset=TipoColegio.objects.all(), required=False, widget=forms.Select())
    codigo = forms.CharField(label=u"Código", required=False, max_length=100, widget=forms.TextInput())
    provincia = forms.ModelChoiceField(label=u"Provincia", queryset=Provincia.objects.all(), required=False, widget=forms.Select())
    canton = forms.ModelChoiceField(label=u"Cantón", queryset=Canton.objects.all(), required=False, widget=forms.Select())
    estado = forms.BooleanField(label=u'Estado', required=False, initial=True)

    def adicionar (self):
        self.fields['canton'].queryset = Canton.objects.filter(id=0)

    def editar(self, colegio):
        self.fields['canton'].queryset = Canton.objects.filter(provincia=colegio.provincia)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class EspecialidadForm(BaseForm):
    nombre = forms.CharField(label=u"Nombre", required=False, max_length=100,widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'



class CursoEscuelaForm(BaseForm):
    carrera = forms.ModelChoiceField(Carrera.objects.all(), label=u"Carrera o postgrado", widget=forms.Select())
    nombre = forms.CharField(label=u'Nombre', max_length=250)
    tema = forms.CharField(label=u'Tema', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    usamodeloevaluativo = forms.BooleanField(label=u'Usa Modelo evaluativo', initial=False, required=False)
    modeloevaluativo = forms.ModelChoiceField(label=u"Modelo Evaluativo", queryset=ModeloEvaluativo.objects.all(), required=False, widget=forms.Select())
    solicitante = forms.IntegerField(initial='', label=u'Solicitante', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    departamento = forms.CharField(label=u'Departamento', required=False, max_length=250)
    codigo = forms.CharField(label=u'Código', max_length=15, required=False, widget=forms.TextInput())
    record = forms.BooleanField(label=u'Pasar al record', initial=False, required=False)
    fechainicio = forms.DateField(label=u"Fecha Inicio", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), )
    fechafin = forms.DateField(label=u"Fecha Fin", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), )
    sesion = forms.ModelChoiceField(label=u"Sesión", queryset=Sesion.objects.all(), required=False, widget=forms.Select())
    modalidad = forms.ModelChoiceField(label=u"Modalidad", queryset=Modalidad.objects.all(), required=False, widget=forms.Select())
    permiteregistrootramodalidad = forms.BooleanField(label=u'Permite registro de otras modalidades', initial=False, required=False)
    paralelo = forms.ModelChoiceField(ParaleloMateria.objects.all(), label=u'Paralelo', widget=forms.Select())
    registroonline = forms.BooleanField(label=u'Permite registro online', initial=False, required=False)
    registrootrasede = forms.BooleanField(label=u'Permite registro otra sede', initial=False, required=False)
    registrointerno = forms.BooleanField(label=u'Permite registro interno', initial=False, required=False)
    penalizar = forms.BooleanField(label=u'Penalizar curso si reprueba', initial=False, required=False)
    prerequisitos = forms.BooleanField(label=u'Debe cumplir prerequisitos', initial=False, required=False)
    sincupo = forms.BooleanField(label=u'Sin cupo', initial=False, required=False)
    cupo = forms.IntegerField(label=u'Cupo', initial='1', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    tipocurso = forms.ModelChoiceField(TipoCostoCurso.objects.all(), required=False, label=u'Tipo de Curso', widget=forms.Select())
    validapromedio = forms.BooleanField(label=u'Válida promedio', initial=False, required=False, widget=forms.CheckboxInput(attrs={'disabled': 'disabled'}))
    costodiferenciado = forms.BooleanField(label=u'Costo diferenciado', initial=False, required=False, widget=forms.CheckboxInput(attrs={'disabled': 'disabled'}))
    costomatricula = forms.FloatField(label=u'Costo de matrícula', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2', 'disabled': 'disabled'}))
    costocuota = forms.FloatField(label=u'Costo por cuota', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2', 'disabled': 'disabled'}))
    cuotas = forms.IntegerField(label=u'Número de cuotas', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0', 'disabled': 'disabled'}))
    costototal = forms.FloatField(label=u'Costo total', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2', 'disabled': 'disabled'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, coordinacion, periodo):
        self.fields['sesion'].queryset = Sesion.objects.filter(sede=coordinacion.sede)
        self.fields['tipocurso'].queryset = TipoCostoCurso.objects.filter(cursos=True, tipocostocursoperiodo__activo=True, tipocostocursoperiodo__periodo=periodo, tipocostocursoperiodo__sede=coordinacion.sede).distinct()

    def adicionar_con(self, coordinacion, periodo):
        self.fields['sesion'].queryset = Sesion.objects.filter(sede=coordinacion.sede)
        self.fields['tipocurso'].queryset = TipoCostoCurso.objects.filter(actualizacionconocimiento=True, tipocostocursoperiodo__activo=True, tipocostocursoperiodo__periodo=periodo, tipocostocursoperiodo__sede=coordinacion.sede).distinct()

        del self.fields['libreconfiguracion']
        del self.fields['optativa']
        del self.fields['costodiferenciado']

    def editar(self, coordinacion, actividad):
        self.fields['sesion'].queryset = Sesion.objects.filter(sede=actividad.coordinacion.sede)
        if coordinacion.id in (22, 23):
            self.fields['tipocurso'].queryset = TipoCostoCurso.objects.filter(cursos=True, tipocostocursoperiodo__activo=True, tipocostocursoperiodo__periodo=actividad.periodo, tipocostocursoperiodo__sede=actividad.coordinacion.sede).distinct()
        else:
            self.fields['tipocurso'].queryset = TipoCostoCurso.objects.filter(cursos=True, tipocostocursoperiodo__activo=True, tipocostocursoperiodo__periodo=actividad.periodo, tipocostocursoperiodo__sede=actividad.coordinacion.sede).exclude(id=1).distinct()
        deshabilitar_campo(self, 'usamodeloevaluativo')
        deshabilitar_campo(self, 'modeloevaluativo')
        if actividad.matriculacursoescuelacomplementaria_set.exists():
            deshabilitar_campo(self, 'examencomplexivo')
            deshabilitar_campo(self, 'registrootrasede')
            deshabilitar_campo(self, 'libreconfiguracion')
            deshabilitar_campo(self, 'optativa')
            deshabilitar_campo(self, 'nivelacion')
        self.fields['solicitante'].widget.attrs['descripcion'] = actividad.solicitante.flexbox_repr() if actividad.solicitante else ""
        if Clase.objects.filter(materiacurso__curso=actividad).exists():
            del self.fields['sesion']
            del self.fields['modalidad']

    def editar_ac(self, actividad):
        deshabilitar_campo(self, 'costodiferenciado')
        deshabilitar_campo(self, 'usamodeloevaluativo')
        deshabilitar_campo(self, 'modeloevaluativo')
        # deshabilitar_campo(self, 'costomatricula')
        deshabilitar_campo(self, 'costocuota')
        deshabilitar_campo(self, 'cuotas')
        deshabilitar_campo(self, 'nivelacion')
        self.fields['sesion'].queryset = Sesion.objects.filter(sede=actividad.coordinacion.sede)
        if actividad.coordinacion.id not in (22, 23):
            self.fields['tipocurso'].queryset = TipoCostoCurso.objects.filter(actualizacionconocimiento=True, tipocostocursoperiodo__activo=True, tipocostocursoperiodo__periodo=actividad.periodo, tipocostocursoperiodo__sede=actividad.coordinacion.sede).exclude(id=1).distinct()
        else:
            self.fields['tipocurso'].queryset = TipoCostoCurso.objects.filter(actualizacionconocimiento=True, tipocostocursoperiodo__activo=True, tipocostocursoperiodo__periodo=actividad.periodo, tipocostocursoperiodo__sede=actividad.coordinacion.sede).distinct()

        del self.fields['libreconfiguracion']
        del self.fields['optativa']
        del self.fields['nivelacion']
        del self.fields['costodiferenciado']
        self.fields['solicitante'].widget.attrs['descripcion'] = actividad.solicitante.flexbox_repr() if actividad.solicitante else ""
        if Clase.objects.filter(materiacurso__curso=actividad).exists():
            del self.fields['sesion']
            del self.fields['modalidad']


class CostoCursoEscuelaForm(BaseForm):
    tipo = forms.ModelChoiceField(label=u"Tipo de registro", queryset=TipoEstudianteCurso.objects.all(), required=False, widget=forms.Select())
    costomatricula = forms.FloatField(label=u'Costo de matrícula', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2'}))
    costocuota = forms.FloatField(label=u'Costo por cuota', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2'}))
    cuotas = forms.IntegerField(label=u'Número de cuotas', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    costototal = forms.FloatField(label=u'Costo total', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2', 'disabled': 'disabled'}))

    def editar(self):
        deshabilitar_campo(self, 'tipo')


class MateriasCursoEscuelaForm(BaseForm):
    asignatura = forms.ModelChoiceField(label=u"Asignatura", required=False, queryset=Asignatura.objects.all())
    profesor = forms.IntegerField(initial='', required=False, label=u'Profesor', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", input_formats=['%d-%m-%Y'], initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), )
    fechafin = forms.DateField(label=u"Fecha Fin", input_formats=['%d-%m-%Y'], initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), )
    validacreditos = forms.BooleanField(label=u'Válida para créditos', initial=True, required=False)
    horas = forms.FloatField(label=u"Horas", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '0', 'formwidth': 300}))
    creditos = forms.FloatField(label=u"Créditos", initial="0.0000", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimales': '4', 'formwidth': 300, 'labelwidth': 60}))
    requiereaprobar = forms.BooleanField(label=u'Requerida para aprobar', initial=True, required=False)
    calificar = forms.BooleanField(label=u'Calificar', initial=False, required=False)
    califmaxima = forms.FloatField(label=u"Nota máxima", initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '2'}))
    califminima = forms.FloatField(label=u"Nota para aprobar", initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '2'}))
    porcentaje = forms.FloatField(label=u"Porcentaje calif. final", initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '2'}))
    asistminima = forms.FloatField(label=u"Asistencia para aprobar", initial="0", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, curso):
        self.fields['asignatura'].queryset = Asignatura.objects.filter(trabajotitulacionmalla__malla=curso.malla, trabajotitulacionmalla__tipotrabajotitulacion=curso.tipotrabajotitulacion, trabajotitulacionmalla__unidadtitulacion=curso.unidadtitulacion).distinct()

    def adicionar_curso(self, curso):
        if curso.usamodeloevaluativo:
            del self.fields['califmaxima']
            del self.fields['califminima']
            del self.fields['asistminima']

    def editar(self):
        deshabilitar_campo(self, 'asignatura')


class PagoCursoEscuelaForm(BaseForm):
    tipo = forms.ChoiceField(label=u'Tipo', required=False, choices=TIPOS_PAGO_NIVEL, widget=forms.Select())
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), required=False)
    valor = forms.FloatField(label=u'Valor', initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-moneda'}))

    def excluir_tipos(self, curso):
        self.fields['tipo'].choices = tuple([(x, y) for x, y in TIPOS_PAGO_NIVEL if not curso.pagoscursoescuelacomplementaria_set.filter(tipo=x).exists()])

    def editar(self):
        deshabilitar_campo(self, 'tipo')


class NotificacionCursoForm(BaseForm):
    mensaje = forms.CharField(widget=forms.Textarea(attrs={'rows': '5', 'class': 'form-control'}), label=u"Mensaje")

    def extra_paramaters(self):
        self.fields['formtype'].initial = 'vertical'


class ClaseCursoForm(BaseForm):
    materia = forms.ModelChoiceField(label=u"Materia", queryset=MateriaCursoEscuelaComplementaria.objects.all(), required=False)
    aula = forms.ModelChoiceField(label=u"Aula", queryset=Aula.objects.all())
    turno = forms.ModelChoiceField(label=u"Turno", queryset=Turno.objects.all(), required=False, widget=forms.Select())
    dia = forms.ChoiceField(label=u"Dia", choices=DIAS_CHOICES, required=False, widget=forms.Select())
    inicio = forms.DateField(label=u"Fecha inicio", input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    fin = forms.DateField(label=u"Fecha fin", input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, curso):
        deshabilitar_campo(self, 'materia')
        self.fields['turno'].queryset = Turno.objects.filter(sesion=curso.sesion).distinct()

    def editar(self, curso):
        deshabilitar_campo(self, 'materia')
        self.fields['turno'].queryset = Turno.objects.filter(sesion=curso.sesion).distinct()


class CambiarAulaCursoComplemetarioForm(BaseForm):
    aula = forms.ModelChoiceField(label=u"Aula", queryset=Aula.objects.all())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class CambiarTipoRegistroForm(BaseForm):
    tipo = forms.ModelChoiceField(label=u"Tipo", queryset=TipoEstudianteCurso.objects.all())

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class CambiarFichaInscripcionForm(BaseForm):
    malla = forms.ModelChoiceField(label=u"Ficha", queryset=Malla.objects.filter(aprobado=True))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, persona):
        self.fields['malla'].queryset = Malla.objects.filter(inscripcionmalla__inscripcion__persona=persona, aprobado=True)


class CambiarAulaForm(BaseForm):
    aula = forms.ModelChoiceField(label=u"Aula", queryset=Aula.objects.all())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self, materia):
        if Aula.objects.filter(aulacoordinacion__coordinacion=materia.nivel.coordinacion()).exists():
            self.fields['aula'].queryset = Aula.objects.filter(aulacoordinacion__coordinacion=materia.nivel.coordinacion())
        else:
            self.fields['aula'].queryset = Aula.objects.filter(sede=materia.nivel.sede)


class DividirCursoEscuelaForm(BaseForm):
    paralelo = ModelChoiceField(label=u'Paralelo', queryset=ParaleloMateria.objects.all(), required=False, widget=forms.Select())
    codigo = forms.CharField(label=u'Código', required=False, max_length=30, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class MoverCursoEscuelaForm(BaseForm):
    curso = forms.ModelChoiceField(CursoEscuelaComplementaria.objects.all(), label=u'Curso')

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, curso):
        self.fields['curso'].queryset = CursoEscuelaComplementaria.objects.filter(cerrado=False, coordinacion__sede=curso.coordinacion.sede).exclude(id=curso.id)



class LocacionCursoEscuelaForm(BaseForm):
    locacion = forms.ModelChoiceField(label=u"Locación", queryset=Locacion.objects.all())

    def adicionar(self, sede):
        self.fields['locacion'].queryset = Locacion.objects.filter(sede=sede)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class LocacionForm(BaseForm):
    nombre = forms.CharField(label=u'Nombre', max_length=300, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class MateriasCursoEscuelaForm(BaseForm):
    asignatura = forms.ModelChoiceField(label=u"Asignatura", required=False, queryset=Asignatura.objects.all())
    profesor = forms.IntegerField(initial='', required=False, label=u'Profesor', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", input_formats=['%d-%m-%Y'], initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), )
    fechafin = forms.DateField(label=u"Fecha Fin", input_formats=['%d-%m-%Y'], initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), )
    validacreditos = forms.BooleanField(label=u'Válida para créditos', initial=True, required=False)
    horas = forms.FloatField(label=u"Horas", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '0', 'formwidth': 300}))
    creditos = forms.FloatField(label=u"Créditos", initial="0.0000", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimales': '4', 'formwidth': 300, 'labelwidth': 60}))
    requiereaprobar = forms.BooleanField(label=u'Requerida para aprobar', initial=True, required=False)
    calificar = forms.BooleanField(label=u'Calificar', initial=False, required=False)
    califmaxima = forms.FloatField(label=u"Nota máxima", initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '2'}))
    califminima = forms.FloatField(label=u"Nota para aprobar", initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '2'}))
    porcentaje = forms.FloatField(label=u"Porcentaje calif. final", initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '2'}))
    asistminima = forms.FloatField(label=u"Asistencia para aprobar", initial="0", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    usalms = forms.BooleanField(label=u'Usa Lms', initial=False, required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, curso):
        self.fields['asignatura'].queryset = Asignatura.objects.filter(trabajotitulacionmalla__malla=curso.malla, trabajotitulacionmalla__tipotrabajotitulacion=curso.tipotrabajotitulacion, trabajotitulacionmalla__unidadtitulacion=curso.unidadtitulacion).distinct()

    def adicionar_curso(self, curso):
        if curso.usamodeloevaluativo:
            del self.fields['califmaxima']
            del self.fields['califminima']
            del self.fields['asistminima']

    def editar(self):
        deshabilitar_campo(self, 'asignatura')

class PagoCursoEscuelaForm(BaseForm):
    tipo = forms.ChoiceField(label=u'Tipo', required=False, choices=TIPOS_PAGO_NIVEL, widget=forms.Select())
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), required=False)
    valor = forms.FloatField(label=u'Valor', initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-moneda'}))

    def excluir_tipos(self, curso):
        self.fields['tipo'].choices = tuple([(x, y) for x, y in TIPOS_PAGO_NIVEL if not curso.pagoscursoescuelacomplementaria_set.filter(tipo=x).exists()])

    def editar(self):
        deshabilitar_campo(self, 'tipo')

class ListaModeloEvaluativoForm(BaseForm):
    modelo = forms.ModelChoiceField(ModeloEvaluativo.objects.all(), label=u"Modelos")

    def excluir_modeloactual(self, modeloevaluativo):
        self.fields['modelo'].queryset = ModeloEvaluativo.objects.filter(activo=True).exclude(id=modeloevaluativo.id)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class LocacionCursoForm(BaseForm):
    locacion = forms.ModelChoiceField(label=u'Locacion', queryset=LocacionesCurso.objects.all(), required=False, widget=forms.Select())

    def editar(self, curso):
        self.fields['locacion'].queryset = LocacionesCurso.objects.filter(curso=curso, activo=True)

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class NuevaInscripcionExternaForm(BaseForm):
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False, widget=forms.TextInput())
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, required=False, widget=forms.TextInput())
    nombre1 = forms.CharField(label=u'1er Nombre', max_length=50, required=False, widget=forms.TextInput())
    nombre2 = forms.CharField(label=u'2do Nombre', max_length=50, required=False, widget=forms.TextInput())
    apellido1 = forms.CharField(label=u"1er apellido", max_length=50, required=False, widget=forms.TextInput())
    apellido2 = forms.CharField(label=u"2do apellido", max_length=50, required=False, widget=forms.TextInput())
    nacimiento = forms.DateField(label=u"Fecha nacimiento", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    sexo = forms.ModelChoiceField(Sexo.objects.all(), required=False, label=u"Sexo", widget=forms.Select())
    pais = forms.ModelChoiceField(label=u'País', required=False, queryset=Pais.objects.all(), widget=forms.Select())
    provincia = forms.ModelChoiceField(label=u"Provincia de residencia", queryset=Provincia.objects, required=False, widget=forms.Select())
    canton = forms.ModelChoiceField(label=u"Cantón de residencia", queryset=Canton.objects, required=False, widget=forms.Select())
    parroquia = forms.ModelChoiceField(label=u"Parroquia de residencia", queryset=Parroquia.objects, required=False, widget=forms.Select())
    direccion = forms.CharField(label=u'Dirección', max_length=100)
    telefono = forms.CharField(label=u"Teléfono móvil", max_length=50, required=False, widget=forms.TextInput())
    telefono_conv = forms.CharField(label=u"Teléfono fijo", max_length=50, required=False, widget=forms.TextInput())
    email = forms.CharField(label=u"Correo electrónico", max_length=200, required=False, widget=forms.TextInput())
    tipo = forms.ModelChoiceField(label=u"Tipo de registro", queryset=TipoEstudianteCurso.objects.all(), required=False, widget=forms.Select())
    locacion = forms.ModelChoiceField(label=u"Locacion", queryset=LocacionesCurso.objects.all(), required=False, widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, curso):
        if not curso.costodiferenciado:
            del self.fields['tipo']
        else:
            self.fields['tipo'].queryset = TipoEstudianteCurso.objects.filter(Q(costodiferenciadocursoperiodo__costomatricula__gt=0) | Q(costodiferenciadocursoperiodo__costocuota__gt=0), costodiferenciadocursoperiodo__tipocostocursoperiodo__tipocostocurso__cursoescuelacomplementaria=curso)
        if curso.locacionescurso_set.count() > 1:
            self.fields['locacion'].queryset = LocacionesCurso.objects.filter(curso=curso, activo=True)
        else:
            del self.fields['locacion']



class PorcentajeDescuentoCursoForm(BaseForm):
    descuento = forms.ChoiceField(label=u'Dirigido a', choices=OPCIONES_DESCUENTO_CURSOS, widget=forms.Select())
    porcentaje = forms.FloatField(label=u'Porcentaje', initial='0.00', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '2'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class PreguntaAprobacionesForm(BaseForm):
    aprobacion = forms.ChoiceField(label=u'Tipo Aprobación', choices=TIPOS_APROBACION_PROTOCOLO, widget=forms.Select())
    observacion = forms.CharField(label=u"Observación", max_length=300,widget=forms.TextInput(attrs={'style': 'text-transform: none'}))
    archivo = forms.FileField(label=u'Archivo',help_text=u'Tamaño máximo permitido 3mb, en formato jpg, png, xls, xlsx, doc, docx,pdf', widget=forms.FileInput(attrs={'accept': '.jpg, .png, .xls, .xlsx, .doc, .docx, .pdf', 'data-max-file-size': 3145728}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class AddDocumentoCursosComplementariosForm(BaseForm):
    nombre = forms.CharField(label=u"Nombre del Archivo", max_length=300,widget=forms.TextInput(attrs={'style': 'text-transform: none'}))
    archivo = forms.FileField(label=u'Archivo',help_text=u'Tamaño máximo permitido 1mb, en formato jpg, png, pdf', widget=forms.FileInput(attrs={'accept': '.jpg, .png, .pdf', 'data-max-file-size': 1024}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class ProfesorMateriaCursoForm(BaseForm):
    profesor = forms.IntegerField(initial='', required=True, label=u'Profesor', widget=forms.TextInput(
        attrs={'select2search': 'true', 'class': 'select2advance'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class NivelFormEdit(BaseForm):
    paralelo = forms.CharField(label=u"Paralelo", required=False, max_length=30, widget=forms.TextInput())
    inicio = forms.DateField(label=u"Fecha inicio", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;', 'width': '30%'}))
    fin = forms.DateField(label=u"Fecha fin", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;', 'width': '60%'}))
    fechacierre = forms.DateField(label=u"Fecha cierre período", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;', 'width': '60%'}))
    fechatopematricula = forms.DateField(label=u"Límite ordinaria", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;', 'width': '30%'}))
    fechatopematriculaext = forms.DateField(label=u"Límite extraordinaria", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;', 'width': '30%'}))
    fechatopematriculaesp = forms.DateField(label=u"Límite especial", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;', 'width': '30%'}))
    mensaje = forms.CharField(label=u'Mensaje', required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}))

    def editar(self, nivel):
        deshabilitar_campo(self, 'paralelo')
        if nivel.tiene_matriculados():
            deshabilitar_campo(self, 'inicio')
            deshabilitar_campo(self, 'fin')
            deshabilitar_campo(self, 'fechatopematricula')
            deshabilitar_campo(self, 'fechatopematriculaext')
            deshabilitar_campo(self, 'fechatopematriculaesp')

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class ProfesorMateriaForm(BaseForm):
    profesor = forms.IntegerField(initial='', required=False, label=u'Profesor',widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'select2advance'}))
    tipoprofesor = forms.ModelChoiceField(label=u'Tipo', queryset=TipoProfesor.objects.all(), required=False, widget=forms.Select())
    desde = forms.DateField(label=u"Desde", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    hasta = forms.DateField(label=u"Hasta", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    motivo = forms.CharField(label=u'Motivo', required=False, widget=forms.Textarea(attrs={'rows': '4', 'class':'form-control'}))

    def editar(self):
        deshabilitar_campo(self, "profesor")

    def nuevo(self):
        del self.fields['motivo']

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class MateriaDividirForm(BaseForm):
    materia = ModelChoiceField(label=u'Materia', queryset=Materia.objects.filter(nivel__periodo__activo=True, cerrado=False, nivel__cerrado=False))

    def desde_materia(self, materia):
        self.fields['materia'].queryset = Materia.objects.filter(nivel__periodo__activo=True, cerrado=False, nivel__cerrado=False, asignatura=materia.asignatura).exclude(id=materia.id)

class MateriaNivelForm(BaseForm):
    asignatura = ModelChoiceField(label=u'Asignatura', queryset=Asignatura.objects.all(), required=False)
    modelo = ModelChoiceField(label=u'Modelo evaluativo', queryset=ModeloEvaluativo.objects.filter(activo=True), required=False)
    identificacion = forms.CharField(label=u'Identificación', required=False, max_length=30, widget=forms.TextInput())
    paralelomateria = ModelChoiceField(label=u'Paralelo', queryset=ParaleloMateria.objects.all(), required=False, widget=forms.Select())
    alias = forms.CharField(label=u'Alias', required=False, max_length=100, widget=forms.TextInput())
    horas = forms.FloatField(label=u"Horas Totales", initial='0.0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    creditos = forms.FloatField(label=u"Créditos", initial='0.0000', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimales': '4'}))
    horassemanales = forms.FloatField(label=u"Horas Semanales", initial='0.0', widget=forms.TextInput(attrs={'class': 'imp-numbermed-center', 'decimales': '1'}))
    inicio = forms.DateField(label=u"Fecha inicio", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    fin = forms.DateField(label=u"Fecha fin", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))
    rectora = forms.BooleanField(label=u'Materia general', initial=False, required=False)
    practicas = forms.BooleanField(label=u'Practicas permitidas', initial=False, required=False)
    validacreditos = forms.BooleanField(label=u'Válida para créditos', initial=True, required=False)
    validapromedio = forms.BooleanField(label=u'Válida para promedio', initial=True, required=False)
    intensivo = forms.BooleanField(label=u'Intensivo', initial=False, required=False)
    integracioncurricular = forms.BooleanField(label=u'Integración', initial=False, required=False)
    tipointegracion = ModelChoiceField(label=u'Tipo integración', queryset=TipoIntegracion.objects.all(), required=False, widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self, materia):
        deshabilitar_campo(self, 'asignatura')
        deshabilitar_campo(self, 'paralelomateria')
        deshabilitar_campo(self, 'modelo')
        deshabilitar_campo(self, 'horas')
        deshabilitar_campo(self, 'creditos')
        deshabilitar_campo(self, 'identificacion')
        if not materia.puede_cambiar_fechas:
            deshabilitar_campo(self, 'inicio')
            deshabilitar_campo(self, 'fin')


class MateriaOtrasCarrerasForm(BaseForm):
    asignatura = forms.ModelChoiceField(label=u'Asignatura', queryset=Asignatura.objects.all(), required=False)

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class MateriasCompartidasForm(BaseForm):
    sede = forms.ModelChoiceField(label=u"Sede", queryset=Sede.objects.all(), widget=forms.Select())
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Carrera.objects.all(), widget=forms.Select())
    modalidad = forms.ModelChoiceField(label=u"Modalidad", queryset=Modalidad.objects.all(), widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class CalificacionDiaForm(BaseForm):
    usaperiodocalificaciones = forms.BooleanField(label=u'Usa cronograma', initial=False, required=False)
    diasactivacioncalificaciones = forms.FloatField(label=u'Días para calificar', initial='1', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class EvaluacionDiaForm(forms.Form):
    usaperiodoevaluacion = forms.BooleanField(label=u'Usa cronograma', initial=False, required=False)
    diasactivacion = forms.IntegerField(label=u'Días para evaluar', initial=1, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))


class FechafinAsistenciasForm(BaseForm):
    fecha = forms.DateField(label=u"Fecha Fin", input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}))

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'md'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class MateriaNivelMallaForm(BaseForm):
    malla = ModelChoiceField(label=u'Malla curricular', queryset=Malla.objects.all(), required=False)
    modelo = ModelChoiceField(label=u'Modelo evaluativo', queryset=ModeloEvaluativo.objects.filter(activo=True), required=False, widget=forms.Select())
    paralelomateria = ModelChoiceField(label=u'Paralelo', queryset=ParaleloMateria.objects.all(), required=False, widget=forms.Select())

    def mallas(self, mallas):
        self.fields['malla'].queryset = mallas

    def extra_paramaters(self):
        self.fields['formwidth'].initial = 'xl'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class NivelMatriculaForm(BaseForm):
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Carrera.objects.all(), required=False)
    nivelmalla = forms.ModelChoiceField(label=u"Nivel", queryset=NivelMalla.objects.all(), required=False, widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, nivel):
        self.fields['carrera'].queryset = nivel.coordinacion().carrera.all()

    def editar(self):
        deshabilitar_campo(self, 'carrera')
        deshabilitar_campo(self, 'nivelmalla')



class EvidenciaMallaForm(BaseForm):
    fecha = forms.DateField(label=u"Fecha", input_formats=['%d-%m-%Y'], initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'onkeydown': 'return false;'}), required=False)
    nombre = forms.CharField(label=u"Nombre", max_length=300, required=False)
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    archivo = ExtFileField(label=u'Archivo', help_text=u'Tamaño máximo permitido 40mb, en formato doc, docx, pdf', ext_whitelist=(".doc", ".docx", ".pdf"), max_upload_size=73400320, required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class InfoMallasedeForm(BaseForm):
    sede = forms.ModelChoiceField(label=u"Sede", queryset=Sede.objects, required=False, widget=forms.Select())
    codigo = forms.CharField(label=u"Código", max_length=200, widget=forms.TextInput())
    lugar = forms.CharField(label=u"Lugar Ejecución", max_length=200, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self):
        deshabilitar_campo(self, 'sede')


class CompetenciaForm(BaseForm):
    carrera = ModelChoiceField(label=u'Carrera', queryset=Carrera.objects.all(), required=False)
    nombre = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, miscarreras):
        self.fields['carrera'].queryset = miscarreras


class CompetenciaEspecificaMallaForm(BaseForm):
    competencia = forms.ModelChoiceField(label=u'Competencia', queryset=CompetenciaEspecifica.objects.all(), required=False, widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formtype'].initial = 'vertical'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def adicionar(self, carrera):
        self.fields['competencia'].queryset = CompetenciaEspecifica.objects.filter(carrera=carrera).distinct()


class CompetenciaGenericaMallaForm(BaseForm):
    competencia = forms.ModelChoiceField(label=u'Competencia', queryset=CompetenciaGenerica.objects.all(), required=False, widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formtype'].initial = 'vertical'
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class InformacionSedeMallaForm(BaseForm):
    codigo = forms.CharField(label=u'Código', required=False, max_length=30, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class AsignaturaForm(BaseForm):
    nombre = forms.CharField(label=u'Nombre', max_length=600, required=False)
    codigo = forms.CharField(label=u'Código', max_length=30, required=False, widget=forms.TextInput())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self, asignatura):
        if asignatura.en_uso():
            deshabilitar_campo(self, 'nombre')


class UnificarAsignaturaForm(BaseForm):
    origen = ModelChoiceField(label=u'Asignatura origen', required=False, queryset=Asignatura.objects.all())
    asignatura = ModelChoiceField(label=u'Asignatura final', queryset=Asignatura.objects.all())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

    def editar(self, asignatura):
        deshabilitar_campo(self, 'origen')
        self.fields['asignatura'].queryset = Asignatura.objects.all().exclude(id=asignatura.id)


class ModeloEvaluativoForm(BaseForm):
    nombre = forms.CharField(label=u"Nombre", max_length=100)
    principal = forms.BooleanField(label=u"Principal", required=False, initial=False)
    activo = forms.BooleanField(label=u"Activo", required=False, initial=True)
    notamaxima = forms.FloatField(label=u"Nota Máxima", required=False, initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '2'}))
    notaaprobar = forms.FloatField(label=u"Nota para Aprobar", required=False, initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '2'}))
    notarecuperacion = forms.FloatField(label=u"Nota para Recup.", required=False, initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '2'}))
    asistenciaaprobar = forms.FloatField(label=u"% Asist. para Aprobar.", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    asistenciarecuperacion = forms.FloatField(label=u"% Asist. para Recup.", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    notafinaldecimales = forms.FloatField(label=u"Decimales N.Final", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall'}))
    observaciones = forms.CharField(label=u'Observaciones', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class DetalleModeloEvaluativoForm(BaseForm):
    nombre = forms.CharField(label=u"Nombre", max_length=10, required=False, widget=forms.TextInput())
    alternativa = forms.ModelChoiceField(label=u"Alternativas", queryset=CodigoEvaluacion.objects, widget=forms.Select())
    orden = forms.IntegerField(label=u"Orden en Acta", required=False, initial='0', widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    notaminima = forms.FloatField(label=u"Nota Mínima", required=False, initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '2'}))
    notamaxima = forms.FloatField(label=u"Nota Máxima", required=False, initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '2'}))
    decimales = forms.FloatField(label=u"Decimales", initial='0', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimales': '0'}))
    dependiente = forms.BooleanField(label=u"Campo Dependiente?", required=False, initial=False)
    actualizaestado = forms.BooleanField(label=u"Actualiza Estado?", required=False, initial=False)
    determinaestadofinal = forms.BooleanField(label=u"Determina Estado final?", required=False, initial=False)
    dependeasistencia = forms.BooleanField(label=u"Depende de asisencia?", required=False, initial=False)

    def editar(self):
        deshabilitar_campo(self, 'nombre')

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


class LogicaModeloEvaluativoForm(BaseForm):
    logica = forms.CharField(label=u'Lógica', widget=forms.Textarea(attrs={'rows': '15', 'class': 'form-control'}), required=False)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'

class TipoEspecieForm(BaseForm):
    nombre = forms.CharField(label=u"Nombre", max_length=100)
    iva = ModelChoiceField(label=u'IVA', queryset=IvaAplicado.objects.all(), required=False, widget=forms.Select())
    precio = forms.FloatField(label=u'Precio', initial='0.00', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'

class TipoCostoCursoForm(BaseForm):
    nombre = forms.CharField(label=u"Nombre", max_length=100)
    cursos = forms.BooleanField(initial=True, required=False, label=u'Cursos y escuelas')
    titulacion = forms.BooleanField(initial=False, required=False, label=u'Unidad de titulación')
    actualizacionconocimiento = forms.BooleanField(initial=False, required=False, label=u'Actualización de conocimientos')
    costodiferenciado = forms.BooleanField(initial=False, required=False, label=u'Diferenciado')
    costolibre = forms.BooleanField(initial=False, required=False, label=u'Costo libre')
    validapromedio = forms.BooleanField(label=u'Válida para promedio', initial=False, required=False)

    def edit(self, tipo):
        if tipo.tiene_uso():
            del self.fields['cursos']
            del self.fields['titulacion']
            del self.fields['actualizacionconocimiento']
            del self.fields['costodiferenciado']
            del self.fields['costolibre']
            del self.fields['validapromedio']

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'



class ProformaForm(BaseForm):
    observaciones = forms.CharField(label=u"Observaciones", required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}))
    descuento = forms.FloatField(label=u"Descuento", required=False, initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimales': '2'}))
    iva = ModelChoiceField(label=u'IVA', queryset=IvaAplicado.objects.all(), required=False, widget=forms.Select())

    def editar(self, proforma):
        if proforma and proforma.estado != Proforma.Estado.BORRADOR:
            deshabilitar_campo(self, 'cliente')
            deshabilitar_campo(self, 'observaciones')
            deshabilitar_campo(self, 'descuento')

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'


# =========================
#    GESTIÓN (ADMIN) sfd
# =========================

class RevisionProformaForm(BaseForm):
    cumple = forms.BooleanField(label=u"Verificación cumple", required=False, initial=False)
    comentarios = forms.CharField(label=u"Comentarios", required=False, widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'}))

    def editar(self, revision):
        # si ya hay decisión, bloquear el cambio
        if revision and revision.pk:
            deshabilitar_campo(self, 'cumple')
            # permitir comentar, si quieres bloquear también:
            # deshabilitar_campo(self, 'comentarios')

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'


class EmitirFacturaForm(BaseForm):
    numero = forms.CharField(label=u"Número de factura", max_length=30)
    fecha_emision = forms.DateField(label=u"Fecha de emisión", widget=forms.TextInput(attrs={'class': 'selectorfecha'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'

    def editar(self, factura):
        if factura and factura.pk:
            deshabilitar_campo(self, 'numero')
            deshabilitar_campo(self, 'fecha_emision')


class GenerarTrabajoForm(BaseForm):
    descripcion = forms.CharField(label=u"Descripción", required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'


class RevisionProformaForm(BaseForm):
    cumple = forms.BooleanField(label=u"Verificación cumple", required=False, initial=False)
    comentarios = forms.CharField(label=u"Comentarios", required=False, widget=forms.Textarea(attrs={'rows':'4','class':'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'

class VincularFacturaForm(BaseForm):
    factura = forms.ModelChoiceField(label=u"Factura existente", queryset=Factura.objects.all(), widget=forms.Select())

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'

class GenerarTrabajoForm(BaseForm):
    responsable = forms.ModelChoiceField(label=u"Responsable", queryset=Persona.objects.all(), widget=forms.Select())
    descripcion = forms.CharField(label=u"Descripción", required=False, widget=forms.Textarea(attrs={'rows':'3','class':'form-control'}))

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'


class RequerimientoServicioForm(BaseForm):
    espacio_fisico = forms.ModelChoiceField(label=u"Laboratorio / área", queryset=EspacioFisico.objects.all(), widget=forms.Select())

    cliente = forms.ModelChoiceField(label=u"Cliente", queryset=Cliente.objects.all(), widget=forms.Select())
    descripcion = forms.CharField(
        label=u"Descripción del requerimiento",
        widget=forms.Textarea(attrs={'rows': '4', 'class': 'form-control'})
    )

    archivo = forms.FileField(
        label=u"Archivo adjunto (opcional)",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'


class ProformaDetalleForm(BaseForm):
    servicio = forms.ModelChoiceField(label=u"Servicio", queryset=ServicioCatalogo.objects, widget=forms.Select())
    descripcion = forms.CharField(label=u"Descripción", required=False, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}))
    cantidad = forms.DecimalField(label=u"Cantidad", max_digits=8, decimal_places=2, initial=Decimal('1.00'))
    precio_unitario = forms.DecimalField(label=u"Precio unitario", max_digits=10, decimal_places=2, required=False, help_text=u"Si lo dejas vacío, se tomará el precio base del servicio.")

    def add(self, espaciofisico):
        self.fields['servicio'].queryset = ServicioCatalogo.objects.filter(espacio_fisico=espaciofisico)

    def extra_paramaters(self):
        self.fields['formbase'].initial = 'ajaxformdinamicbs.html'
        self.fields['formtype'].initial = 'vertical'

