# coding=utf-8
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from settings import MANAGERS
from ctt.models import *

class ModeloBaseTabularAdmin(admin.TabularInline):
    exclude = ("usuario_creacion", "fecha_creacion", "usuario_modificacion", "fecha_modificacion")

class ModeloBaseAdmin(admin.ModelAdmin):
    def get_actions(self, request):
        actions = super(ModeloBaseAdmin, self).get_actions(request) or {}
        if request.user.username not in [x[0] for x in MANAGERS]:
            actions.pop('delete_selected', None)  # no falla si no existe
        return actions

    def has_add_permission(self, request):
        return request.user.username in [x[0] for x in MANAGERS]

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return request.user.username in [x[0] for x in MANAGERS]

    def get_form(self, request, obj=None, **kwargs):
        self.exclude = ("usuario_creacion", "fecha_creacion", "usuario_modificacion", "fecha_modificacion", "status", "valida_deuda", "extendido", "becado", "becaexterna", "iece", "beneficiomonetario", "tipobeca", "porcientobeca", "montobeca", "montomensual", "montobeneficio", "cantidadmeses", "fechatope", "formalizada", "promedionotas", "promedioasistencias", "aprobadofinanzas", "permiteanular", "promovido", "paraleloprincipal", "estadomatricula")
        form = super(ModeloBaseAdmin, self).get_form(request, obj, **kwargs)
        return form

    def save_model(self, request, obj, form, change):
        if request.user.username not in [x[0] for x in MANAGERS]:
            raise Exception('Sin permiso a modificacion.')
        else:
            obj.save(request)


class ParametroReporteAdmin(ModeloBaseTabularAdmin):
    model = ParametroReporte


class PagoAdmin(ModeloBaseAdmin):
    model = Pago


class ReporteAdmin(ModeloBaseAdmin):
    inlines = [ParametroReporteAdmin]
    list_display = ('nombre', 'descripcion', 'archivo', 'categoria', 'interface')
    ordering = ('nombre',)
    search_fields = ('nombre',)


class LogEntryAdmin(ModeloBaseAdmin):
    date_hierarchy = 'action_time'
    list_filter = ['action_flag']
    search_fields = ['change_message', 'object_repr', 'user__username']
    list_display = ['action_time', 'user', 'action_flag', 'change_message']

    def get_actions(self, request):
        actions = super(LogEntryAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        self.readonly_fields = [x.name for x in self.model._meta.local_fields]
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        raise Exception('Sin permiso a modificacion')


class ModuloAdmin(ModeloBaseAdmin):
    list_display = ('url', 'nombre', 'descripcion', 'activo')
    ordering = ('url',)
    search_fields = ('url', 'nombre', 'descripcion')
    list_filter = ('activo',)

class CoordinacionAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'sede_id', 'alias', 'estado', 'nombreingles','activadopracticacomunitaria')
    ordering = ('nombre',)
    search_fields = ('nombre',)

class CarreraAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'alias', 'mencion', 'activa', 'costoinscripcion','posgrado','codigotalentohumano','tipogrado_id')
    ordering = ('nombre',)
    search_fields = ('nombre',)

admin.site.register(Reporte, ReporteAdmin)
admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(Modulo, ModuloAdmin)
admin.site.register(Coordinacion, CoordinacionAdmin)
admin.site.register(Carrera,CarreraAdmin)