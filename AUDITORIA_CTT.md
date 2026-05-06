# Auditoria Proyecto CTT

Nota (2026-05-05): Se aplicaron correcciones para eliminar `TemplateDoesNotExist`, assets faltantes y problemas de POST/redirect con barra final. Ver tambien `TEMPLATES_AUTOGENERADAS.md` para el detalle de plantillas autogeneradas.

## Resumen

- Templates HTML totales: 832
- Templates HTML vacios (0 bytes): 218
- Templates referenciados desde Python (render/get_template): 889
- Templates faltantes (referenciados desde Python pero no existen): 225
- Templates vacios pero referenciados desde Python: 130
- Includes faltantes en templates: 3
- Extends faltantes en templates: 0
- Assets static faltantes (referenciados en templates): 4
- Templates (html_template/template=...) vacios: 21

## Hallazgos de Configuracion (settings.py)

- `DEBUG` se asigna 2 veces (el ultimo valor gana).
- `STATIC_URL` se asigna 2 veces (el ultimo valor gana).
- `STATIC_URL` (primera ocurrencia): `/static/`
- `STATIC_URL` (ultima ocurrencia): `static/`

## Archivos/Modulos Faltantes Detectados (a mano)

- `ctt/auth_pipelines.py` existe: `False`
- `ctt/disenoreporte.py` existe: `False`
- `thirdparty/JasperStarter/lib` existe: `False`
- `media/` existe: `False`

## Dependencias / Reproducibilidad

- No hay `requirements.txt`, `pyproject.toml`, `Pipfile` o similar en la raiz del proyecto (solo aparece dentro de `.venv/`).

## Static Assets Faltantes

- `static/fontawesome/css/all.min.css` (referenciado pero no existe)
- `static/images/ctt_lab.webp` (referenciado pero no existe)
- `static/images/deuna.jpg` (referenciado pero no existe)
- `static/images/iconos/sin_icono.png` (referenciado pero no existe)

## Includes Faltantes

- `matriculas/segmento.html` incluye `calificaciones/generico/encabezado.html` (no existe)
- `matriculas/segmento.html` incluye `calificaciones/generico/filanotas.html` (no existe)
- `matriculas/segmento.html` incluye `calificaciones/generico/extradata.html` (no existe)

## Templates Vacias (0 bytes) por Carpeta (Top)

- `inscripciones`: 103
- `emails`: 83
- `docentes`: 24
- `administrativos`: 2
- `account.html`: 1
- `cargarfoto.html`: 1
- `changepassrecovery.html`: 1
- `mailbox`: 1
- `nuevomensaje.html`: 1
- `reportes`: 1

## Templates Faltantes Referenciadas Desde Python (por Carpeta Top)

- `pro_planificacion`: 83
- `adm_periodos`: 27
- `adm_notacredito`: 10
- `adm_cliente`: 9
- `adm_colegios`: 8
- `adm_caja`: 7
- `adm_depositoinscripcion`: 7
- `pro_clases`: 6
- `pro_evaluaciones`: 6
- `adm_recibo_caja`: 5
- `fecha_evaluaciones`: 5
- `adm_evaluaciones`: 4
- `adm_facturas`: 4
- `adm_tecnologicouniversidad`: 4
- `adm_valecaja`: 4
- `adm_institucion`: 3
- `adm_recibopago`: 3
- `alu_automatricula`: 3
- `alu_cursoscomplementarios`: 3
- `pro_aperturaclase`: 3
- `adm_depositos`: 2
- `servicios`: 2
- `adm_transferencias`: 2
- `alu_notas`: 2
- `adm_soporte`: 2
- `pro_asistencias`: 2
- `adm_cursoscomplementarios`: 1
- `alu_asistencias`: 1
- `alu_horarios`: 1
- `alu_malla`: 1
- `adm_terminosycondiciones`: 1
- `gestion_servicios`: 1
- `inscripciones`: 1
- `niveles`: 1
- `pro_horarios`: 1

## Lista Completa: Templates Faltantes (referenciadas)

```text
adm_caja/addpapeleta.html  <-  ctt/adm_caja.py
adm_caja/addsesion.html  <-  ctt/adm_caja.py
adm_caja/cerrarsesion.html  <-  ctt/adm_caja.py
adm_caja/delpapeleta.html  <-  ctt/adm_caja.py
adm_caja/editpapeleta.html  <-  ctt/adm_caja.py
adm_caja/papeletas.html  <-  ctt/adm_caja.py
adm_caja/view.html  <-  ctt/adm_caja.py
adm_cliente/activar.html  <-  ctt/adm_cliente.py
adm_cliente/activarperfil.html  <-  ctt/adm_cliente.py
adm_cliente/addgrupo.html  <-  ctt/adm_cliente.py
adm_cliente/asignarsede.html  <-  ctt/adm_cliente.py
adm_cliente/delgrupo.html  <-  ctt/adm_cliente.py
adm_cliente/desactivar.html  <-  ctt/adm_cliente.py
adm_cliente/desactivarperfil.html  <-  ctt/adm_cliente.py
adm_cliente/edit.html  <-  ctt/adm_cliente.py
adm_cliente/resetear.html  <-  ctt/adm_cliente.py
adm_colegios/add.html  <-  ctt/adm_colegios.py
adm_colegios/addespecialidades.html  <-  ctt/adm_colegios.py
adm_colegios/del.html  <-  ctt/adm_colegios.py
adm_colegios/delespecialidades.html  <-  ctt/adm_colegios.py
adm_colegios/edit.html  <-  ctt/adm_colegios.py
adm_colegios/editespecialidades.html  <-  ctt/adm_colegios.py
adm_colegios/especialidades.html  <-  ctt/adm_colegios.py
adm_colegios/view.html  <-  ctt/adm_colegios.py
adm_cursoscomplementarios/exportaralms.html  <-  ctt/adm_cursoscomplementarios.py
adm_depositoinscripcion/autorizar.html  <-  ctt/adm_depositoinscripcion.py
adm_depositoinscripcion/desautorizar.html  <-  ctt/adm_depositoinscripcion.py
adm_depositoinscripcion/edit.html  <-  ctt/adm_depositoinscripcion.py
adm_depositoinscripcion/marcarprocesado.html  <-  ctt/adm_depositoinscripcion.py
adm_depositoinscripcion/observaciones.html  <-  ctt/adm_depositoinscripcion.py
adm_depositoinscripcion/reasignar.html  <-  ctt/adm_depositoinscripcion.py
adm_depositoinscripcion/view.html  <-  ctt/adm_depositoinscripcion.py
adm_depositos/edit.html  <-  ctt/adm_depositos.py
adm_depositos/view.html  <-  ctt/adm_depositos.py
adm_evaluaciones/segmento.html  <-  ctt/adm_evaluaciones.py
adm_evaluaciones/solicitud.html  <-  ctt/adm_evaluaciones.py
adm_evaluaciones/subir.html  <-  ctt/adm_evaluaciones.py
adm_evaluaciones/view.html  <-  ctt/adm_evaluaciones.py
adm_facturas/abonos.html  <-  ctt/adm_facturas.py
adm_facturas/anular.html  <-  ctt/adm_facturas.py
adm_facturas/rubros.html  <-  ctt/adm_facturas.py
adm_facturas/view.html  <-  ctt/adm_facturas.py
adm_institucion/addlms.html  <-  ctt/adm_institucion.py
adm_institucion/dellms.html  <-  ctt/adm_institucion.py
adm_institucion/editlms.html  <-  ctt/adm_institucion.py
adm_notacredito/addnotacredito.html  <-  ctt/adm_notacredito.py
adm_notacredito/editncimportada.html  <-  ctt/adm_notacredito.py
adm_notacredito/editnotacredito.html  <-  ctt/adm_notacredito.py
adm_notacredito/eliminar.html  <-  ctt/adm_notacredito.py
adm_notacredito/generar.html  <-  ctt/adm_notacredito.py
adm_notacredito/generarnotacredito.html  <-  ctt/adm_notacredito.py
adm_notacredito/importar.html  <-  ctt/adm_notacredito.py
adm_notacredito/liquidar.html  <-  ctt/adm_notacredito.py
adm_notacredito/pagos.html  <-  ctt/adm_notacredito.py
adm_notacredito/view.html  <-  ctt/adm_notacredito.py
adm_periodos/abrirperiodo.html  <-  ctt/adm_periodos.py
adm_periodos/add.html  <-  ctt/adm_periodos.py
adm_periodos/addcronograma.html  <-  ctt/adm_periodos.py
adm_periodos/addcronogramapre.html  <-  ctt/adm_periodos.py
adm_periodos/addperiodosol.html  <-  ctt/adm_periodos.py
adm_periodos/aprueboevaluacion.html  <-  ctt/adm_periodos.py
adm_periodos/cerrarperiodo.html  <-  ctt/adm_periodos.py
adm_periodos/cromatriculacion.html  <-  ctt/adm_periodos.py
adm_periodos/croprematriculacion.html  <-  ctt/adm_periodos.py
adm_periodos/delcronograma.html  <-  ctt/adm_periodos.py
adm_periodos/delcronogramapre.html  <-  ctt/adm_periodos.py
adm_periodos/delperiodo.html  <-  ctt/adm_periodos.py
adm_periodos/delperiodosolicitud.html  <-  ctt/adm_periodos.py
adm_periodos/deshabmatricula.html  <-  ctt/adm_periodos.py
adm_periodos/deshabprematricula.html  <-  ctt/adm_periodos.py
adm_periodos/desverperiodo.html  <-  ctt/adm_periodos.py
adm_periodos/edit.html  <-  ctt/adm_periodos.py
adm_periodos/editcronograma.html  <-  ctt/adm_periodos.py
adm_periodos/editcronogramapre.html  <-  ctt/adm_periodos.py
adm_periodos/editperiodosolicitud.html  <-  ctt/adm_periodos.py
adm_periodos/editperiodosolicitudperiodo.html  <-  ctt/adm_periodos.py
adm_periodos/habmatricula.html  <-  ctt/adm_periodos.py
adm_periodos/habprematricula.html  <-  ctt/adm_periodos.py
adm_periodos/habverperiodo.html  <-  ctt/adm_periodos.py
adm_periodos/matriculasmora.html  <-  ctt/adm_periodos.py
adm_periodos/periodosolicitud.html  <-  ctt/adm_periodos.py
adm_periodos/view.html  <-  ctt/adm_periodos.py
adm_recibo_caja/add.html  <-  ctt/adm_recibo_caja.py
adm_recibo_caja/edit.html  <-  ctt/adm_recibo_caja.py
adm_recibo_caja/liquidar.html  <-  ctt/adm_recibo_caja.py
adm_recibo_caja/transferir.html  <-  ctt/adm_recibo_caja.py
adm_recibo_caja/view.html  <-  ctt/adm_recibo_caja.py
adm_recibopago/anular.html  <-  ctt/adm_recibopago.py
adm_recibopago/rubros.html  <-  ctt/adm_recibopago.py
adm_recibopago/view.html  <-  ctt/adm_recibopago.py
adm_soporte/mensajepersona.html  <-  ctt/api.py
adm_soporte/mensajesoporte.html  <-  ctt/api.py
adm_tecnologicouniversidad/add.html  <-  ctt/adm_tecnologicouniversidad.py
adm_tecnologicouniversidad/del.html  <-  ctt/adm_tecnologicouniversidad.py
adm_tecnologicouniversidad/edit.html  <-  ctt/adm_tecnologicouniversidad.py
adm_tecnologicouniversidad/view.html  <-  ctt/adm_tecnologicouniversidad.py
adm_terminosycondiciones/aceptar.html  <-  ctt/commonviews.py
adm_transferencias/edit.html  <-  ctt/adm_transferencias.py
adm_transferencias/view.html  <-  ctt/adm_transferencias.py
adm_valecaja/add.html  <-  ctt/adm_valecaja.py
adm_valecaja/del.html  <-  ctt/adm_valecaja.py
adm_valecaja/edit.html  <-  ctt/adm_valecaja.py
adm_valecaja/view.html  <-  ctt/adm_valecaja.py
alu_asistencias/view.html  <-  ctt/alu_asistencias.py
alu_automatricula/actualizardatosfactura.html  <-  ctt/alu_automatricula.py
alu_automatricula/aluhorario.html  <-  ctt/alu_automatricula.py
alu_automatricula/view.html  <-  ctt/alu_automatricula.py
alu_cursoscomplementarios/registrar.html  <-  ctt/alu_cursoscomplementarios.py
alu_cursoscomplementarios/registrarlocaciones.html  <-  ctt/alu_cursoscomplementarios.py
alu_cursoscomplementarios/view.html  <-  ctt/alu_cursoscomplementarios.py
alu_horarios/view.html  <-  ctt/alu_horarios.py
alu_malla/view.html  <-  ctt/alu_malla.py
alu_notas/extracurricular.html  <-  ctt/alu_notas.py
alu_notas/view.html  <-  ctt/alu_notas.py
fecha_evaluaciones/addcronograma.html  <-  ctt/fecha_evaluaciones.py
fecha_evaluaciones/delcronograma.html  <-  ctt/fecha_evaluaciones.py
fecha_evaluaciones/edit.html  <-  ctt/fecha_evaluaciones.py
fecha_evaluaciones/materias.html  <-  ctt/fecha_evaluaciones.py
fecha_evaluaciones/view.html  <-  ctt/fecha_evaluaciones.py
gestion_servicios/vincular_factura.html  <-  ctt/gestion_servicios.py
inscripciones/importarestudiante.html  <-  ctt/inscripciones.py
niveles/graficahorarios.html  <-  ctt/niveles.py
pro_aperturaclase/addsolicitud.html  <-  ctt/pro_aperturaclase.py
pro_aperturaclase/delsolicitud.html  <-  ctt/pro_aperturaclase.py
pro_aperturaclase/view.html  <-  ctt/pro_aperturaclase.py
pro_asistencias/segmento.html  <-  ctt/pro_asistencias.py
pro_asistencias/view.html  <-  ctt/pro_asistencias.py
pro_clases/adddeberes.html  <-  ctt/pro_clases.py
pro_clases/contenidoacademico.html  <-  ctt/pro_clases.py
pro_clases/delleccion.html  <-  ctt/pro_clases.py
pro_clases/leccion.html  <-  ctt/pro_clases.py
pro_clases/resolucionesincidencias.html  <-  ctt/pro_clases.py
pro_clases/view.html  <-  ctt/pro_clases.py
pro_evaluaciones/importar.html  <-  ctt/pro_evaluaciones.py
pro_evaluaciones/importarlms.html  <-  ctt/pro_evaluaciones.py
pro_evaluaciones/nee.html  <-  ctt/pro_evaluaciones.py
pro_evaluaciones/segmento.html  <-  ctt/pro_evaluaciones.py
pro_evaluaciones/solicitud.html  <-  ctt/pro_evaluaciones.py
pro_evaluaciones/view.html  <-  ctt/pro_evaluaciones.py
pro_horarios/view.html  <-  ctt/pro_horarios.py
pro_planificacion/actualizarhibridas.html  <-  ctt/pro_planificacion.py
pro_planificacion/add.html  <-  ctt/pro_planificacion.py
pro_planificacion/addantropometria.html  <-  ctt/pro_planificacion.py
pro_planificacion/addbibliografiabasica.html  <-  ctt/pro_planificacion.py
pro_planificacion/addbibliografiacomplementaria.html  <-  ctt/pro_planificacion.py
pro_planificacion/addbibliografiacomplementariasolicitada.html  <-  ctt/pro_planificacion.py
pro_planificacion/addclase.html  <-  ctt/pro_planificacion.py
pro_planificacion/addcontenido.html  <-  ctt/pro_planificacion.py
pro_planificacion/addestudiantegrupopractica.html  <-  ctt/pro_planificacion.py
pro_planificacion/addevolucion.html  <-  ctt/pro_planificacion.py
pro_planificacion/addexamenescomplementarios.html  <-  ctt/pro_planificacion.py
pro_planificacion/addgrupopractica.html  <-  ctt/pro_planificacion.py
pro_planificacion/addguia.html  <-  ctt/pro_planificacion.py
pro_planificacion/addguiacienciasbasicas.html  <-  ctt/pro_planificacion.py
pro_planificacion/addguiacienciasbasicasenfermeria.html  <-  ctt/pro_planificacion.py
pro_planificacion/addguiacienciasbasicasn.html  <-  ctt/pro_planificacion.py
pro_planificacion/addguiasimulacionclinica.html  <-  ctt/pro_planificacion.py
pro_planificacion/addindicador.html  <-  ctt/pro_planificacion.py
pro_planificacion/addindicadorplanificacion.html  <-  ctt/pro_planificacion.py
pro_planificacion/addtaller.html  <-  ctt/pro_planificacion.py
pro_planificacion/bibliografia.html  <-  ctt/pro_planificacion.py
pro_planificacion/contenidos.html  <-  ctt/pro_planificacion.py
pro_planificacion/delantropometria.html  <-  ctt/pro_planificacion.py
pro_planificacion/delbibliografiabasica.html  <-  ctt/pro_planificacion.py
pro_planificacion/delbibliografiabasicasolicitada.html  <-  ctt/pro_planificacion.py
pro_planificacion/delbibliografiacomplementaria.html  <-  ctt/pro_planificacion.py
pro_planificacion/delbibliografiacomplementariasolicitada.html  <-  ctt/pro_planificacion.py
pro_planificacion/delclase.html  <-  ctt/pro_planificacion.py
pro_planificacion/delcontenido.html  <-  ctt/pro_planificacion.py
pro_planificacion/delestudiantegrupopractica.html  <-  ctt/pro_planificacion.py
pro_planificacion/delete.html  <-  ctt/pro_planificacion.py
pro_planificacion/delevolucion.html  <-  ctt/pro_planificacion.py
pro_planificacion/delexamenescomplementarios.html  <-  ctt/pro_planificacion.py
pro_planificacion/delgrupopracticas.html  <-  ctt/pro_planificacion.py
pro_planificacion/delguia.html  <-  ctt/pro_planificacion.py
pro_planificacion/delguiacienciasbasicas.html  <-  ctt/pro_planificacion.py
pro_planificacion/delguiacienciasbasicasenfermeria.html  <-  ctt/pro_planificacion.py
pro_planificacion/delguiaguiasimulacionclinica.html  <-  ctt/pro_planificacion.py
pro_planificacion/delindicador.html  <-  ctt/pro_planificacion.py
pro_planificacion/delindicadorplanificacion.html  <-  ctt/pro_planificacion.py
pro_planificacion/deltaller.html  <-  ctt/pro_planificacion.py
pro_planificacion/detalleguia.html  <-  ctt/pro_planificacion.py
pro_planificacion/detallerubrica.html  <-  ctt/pro_planificacion.py
pro_planificacion/detallerubricaplanificacion.html  <-  ctt/pro_planificacion.py
pro_planificacion/detalletaller.html  <-  ctt/pro_planificacion.py
pro_planificacion/diasguia.html  <-  ctt/pro_planificacion.py
pro_planificacion/edit.html  <-  ctt/pro_planificacion.py
pro_planificacion/editantropometria.html  <-  ctt/pro_planificacion.py
pro_planificacion/editbibliografiabasica.html  <-  ctt/pro_planificacion.py
pro_planificacion/editbibliografiabasicasolicitada.html  <-  ctt/pro_planificacion.py
pro_planificacion/editbibliografiacomplementaria.html  <-  ctt/pro_planificacion.py
pro_planificacion/editbibliografiacomplementariasolicitada.html  <-  ctt/pro_planificacion.py
pro_planificacion/editclase.html  <-  ctt/pro_planificacion.py
pro_planificacion/editcontenido.html  <-  ctt/pro_planificacion.py
pro_planificacion/editevolucion.html  <-  ctt/pro_planificacion.py
pro_planificacion/editexamenescomplementarios.html  <-  ctt/pro_planificacion.py
pro_planificacion/editguia.html  <-  ctt/pro_planificacion.py
pro_planificacion/editguiacienciasbasicas.html  <-  ctt/pro_planificacion.py
pro_planificacion/editguiacienciasbasicasenfermeria.html  <-  ctt/pro_planificacion.py
pro_planificacion/editguiacienciasbasicasing.html  <-  ctt/pro_planificacion.py
pro_planificacion/editguiasimulacionclinica.html  <-  ctt/pro_planificacion.py
pro_planificacion/editindicador.html  <-  ctt/pro_planificacion.py
pro_planificacion/editindicadorplanificacion.html  <-  ctt/pro_planificacion.py
pro_planificacion/edittaller.html  <-  ctt/pro_planificacion.py
pro_planificacion/grupospracticas.html  <-  ctt/pro_planificacion.py
pro_planificacion/horashibridas.html  <-  ctt/pro_planificacion.py
pro_planificacion/importarplanificacion.html  <-  ctt/pro_planificacion.py
pro_planificacion/importartaller.html  <-  ctt/pro_planificacion.py
pro_planificacion/importartallermed.html  <-  ctt/pro_planificacion.py
pro_planificacion/observacionesbibliografia.html  <-  ctt/pro_planificacion.py
pro_planificacion/observacionesguia.html  <-  ctt/pro_planificacion.py
pro_planificacion/observacionesguiasim.html  <-  ctt/pro_planificacion.py
pro_planificacion/rubrica.html  <-  ctt/pro_planificacion.py
pro_planificacion/rubricaplanificacion.html  <-  ctt/pro_planificacion.py
pro_planificacion/solicitarbibliografiabasica.html  <-  ctt/pro_planificacion.py
pro_planificacion/subirarchivo.html  <-  ctt/pro_planificacion.py
pro_planificacion/subirarchivoguia.html  <-  ctt/pro_planificacion.py
pro_planificacion/talleres.html  <-  ctt/pro_planificacion.py
pro_planificacion/tomandompracticas.html  <-  ctt/pro_planificacion.py
pro_planificacion/verificar.html  <-  ctt/pro_planificacion.py
pro_planificacion/verificarbibliografia.html  <-  ctt/pro_planificacion.py
pro_planificacion/verificartaller.html  <-  ctt/pro_planificacion.py
pro_planificacion/view.html  <-  ctt/pro_planificacion.py
servicios/requerimiento_delete.html  <-  ctt/adm_ordenestrabajo.py  (+1 mas)
servicios/requerimiento_edit.html  <-  ctt/servicios.py
```

## Lista Completa: Templates Vacias pero Referenciadas

```text
account.html  <-  ctt/commonviews.py
administrativos/asignarsede.html  <-  ctt/administrativos.py
administrativos/edit.html  <-  ctt/administrativos.py
cargarfoto.html  <-  ctt/commonviews.py
docentes/activar.html  <-  ctt/docentes.py
docentes/activarperfil.html  <-  ctt/docentes.py
docentes/actualizartitulos.html  <-  ctt/docentes.py
docentes/add.html  <-  ctt/docentes.py
docentes/addadministrativo.html  <-  ctt/docentes.py
docentes/addarchivo.html  <-  ctt/docentes.py
docentes/addarchivocurso.html  <-  ctt/docentes.py
docentes/addarchivopublicacion.html  <-  ctt/docentes.py
docentes/addcurso.html  <-  ctt/docentes.py
docentes/addestudiante.html  <-  ctt/docentes.py
docentes/addpublicacion.html  <-  ctt/docentes.py
docentes/addtitulacion.html  <-  ctt/docentes.py
docentes/borrarcv.html  <-  ctt/docentes.py
docentes/cargarcv.html  <-  ctt/docentes.py
docentes/delcurso.html  <-  ctt/docentes.py
docentes/delpublicacion.html  <-  ctt/docentes.py
docentes/deltitulacion.html  <-  ctt/docentes.py
docentes/desactivar.html  <-  ctt/docentes.py
docentes/desactivarperfil.html  <-  ctt/docentes.py
docentes/edit.html  <-  ctt/docentes.py
docentes/editcurso.html  <-  ctt/docentes.py
docentes/editpublicacion.html  <-  ctt/docentes.py
docentes/edittitulacion.html  <-  ctt/docentes.py
docentes/resetear.html  <-  ctt/docentes.py
inscripciones/abrirmatricula.html  <-  ctt/inscripciones.py
inscripciones/activar.html  <-  ctt/inscripciones.py
inscripciones/activarcertificadonoadeudar.html  <-  ctt/inscripciones.py
inscripciones/activarperfil.html  <-  ctt/inscripciones.py
inscripciones/addadministrativo.html  <-  ctt/inscripciones.py
inscripciones/adddefensa.html  <-  ctt/inscripciones.py
inscripciones/adddocente.html  <-  ctt/inscripciones.py
inscripciones/adddocumento.html  <-  ctt/inscripciones.py
inscripciones/addentrevista.html  <-  ctt/inscripciones.py
inscripciones/addestudio.html  <-  ctt/inscripciones.py
inscripciones/addestudiosuperior.html  <-  ctt/inscripciones.py
inscripciones/addexamen.html  <-  ctt/inscripciones.py
inscripciones/addexameni.html  <-  ctt/inscripciones.py
inscripciones/addhistorico.html  <-  ctt/inscripciones.py
inscripciones/addidioma.html  <-  ctt/inscripciones.py
inscripciones/addobservacioncertificadonoadeuda.html  <-  ctt/inscripciones.py
inscripciones/addotrosrequisitos.html  <-  ctt/inscripciones.py
inscripciones/addreconocimiento.html  <-  ctt/inscripciones.py
inscripciones/addrecord.html  <-  ctt/inscripciones.py
inscripciones/addrecordhomologada.html  <-  ctt/inscripciones.py
inscripciones/addsolicitudhomologacion.html  <-  ctt/inscripciones.py
inscripciones/addtrabajo.html  <-  ctt/inscripciones.py
inscripciones/adicionarotracarrera.html  <-  ctt/inscripciones.py
inscripciones/anularsolicitud.html  <-  ctt/inscripciones.py
inscripciones/aprobarcertificadonoadeudar.html  <-  ctt/inscripciones.py
inscripciones/asignarcanvas.html  <-  ctt/inscripciones.py
inscripciones/cambiarinscripcion.html  <-  ctt/inscripciones.py
inscripciones/cambiarinscripcionpasantia.html  <-  ctt/inscripciones.py
inscripciones/cambiocohorte.html  <-  ctt/inscripciones.py
inscripciones/cambiodatoscarrera.html  <-  ctt/inscripciones.py
inscripciones/cambiomalla.html  <-  ctt/inscripciones.py
inscripciones/cambionivel.html  <-  ctt/inscripciones.py
inscripciones/cambionivelmatricula.html  <-  ctt/inscripciones.py
inscripciones/cambiorecordhomologacion.html  <-  ctt/inscripciones.py
inscripciones/cargarfoto.html  <-  ctt/inscripciones.py
inscripciones/confirmarentrevista.html  <-  ctt/inscripciones.py
inscripciones/convalidar.html  <-  ctt/inscripciones.py
inscripciones/darperiodo.html  <-  ctt/inscripciones.py
inscripciones/deldefensa.html  <-  ctt/inscripciones.py
inscripciones/deldocumento.html  <-  ctt/inscripciones.py
inscripciones/delentrevista.html  <-  ctt/inscripciones.py
inscripciones/delestudio.html  <-  ctt/inscripciones.py
inscripciones/delete.html  <-  ctt/inscripciones.py
inscripciones/delexamen.html  <-  ctt/inscripciones.py
inscripciones/delhistorico.html  <-  ctt/inscripciones.py
inscripciones/delidioma.html  <-  ctt/inscripciones.py
inscripciones/delmovilidad.html  <-  ctt/inscripciones.py
inscripciones/delotrosrequisitos.html  <-  ctt/inscripciones.py
inscripciones/delreconocimiento.html  <-  ctt/inscripciones.py
inscripciones/delrecord.html  <-  ctt/inscripciones.py
inscripciones/delsolicitudhomologacion.html  <-  ctt/inscripciones.py
inscripciones/deltrabajo.html  <-  ctt/inscripciones.py
inscripciones/deltribunal.html  <-  ctt/inscripciones.py
inscripciones/desactivar.html  <-  ctt/inscripciones.py
inscripciones/desactivarperfil.html  <-  ctt/inscripciones.py
inscripciones/deshabcambiomodalidad.html  <-  ctt/inscripciones.py
inscripciones/deshabexamen.html  <-  ctt/inscripciones.py
inscripciones/deshabilitarhomologacion.html  <-  ctt/inscripciones.py
inscripciones/deshabilitarhomologacionpre.html  <-  ctt/inscripciones.py
inscripciones/edit.html  <-  ctt/inscripciones.py
inscripciones/editdatosdefensa.html  <-  ctt/inscripciones.py
inscripciones/editdatosdefensaextra.html  <-  ctt/inscripciones.py
inscripciones/editdocumento.html  <-  ctt/inscripciones.py
inscripciones/editestudio.html  <-  ctt/inscripciones.py
inscripciones/editestudiosuperior.html  <-  ctt/inscripciones.py
inscripciones/edithistorico.html  <-  ctt/inscripciones.py
inscripciones/editidioma.html  <-  ctt/inscripciones.py
inscripciones/editmovilidad.html  <-  ctt/inscripciones.py
inscripciones/editotrosrequisitos.html  <-  ctt/inscripciones.py
inscripciones/editreconocimiento.html  <-  ctt/inscripciones.py
inscripciones/edittrabajo.html  <-  ctt/inscripciones.py
inscripciones/edittribunal.html  <-  ctt/inscripciones.py
inscripciones/fechainicioconvalidacion.html  <-  ctt/inscripciones.py
inscripciones/generarrubrosparqueo.html  <-  ctt/inscripciones.py
inscripciones/generarrubrosparqueoadicional.html  <-  ctt/inscripciones.py
inscripciones/habcambiomodalidad.html  <-  ctt/inscripciones.py
inscripciones/habexamen.html  <-  ctt/inscripciones.py
inscripciones/habilitarhomologacion.html  <-  ctt/inscripciones.py
inscripciones/habilitarhomologacionpre.html  <-  ctt/inscripciones.py
inscripciones/homologar.html  <-  ctt/inscripciones.py
inscripciones/idsalesforce.html  <-  ctt/inscripciones.py
inscripciones/importar.html  <-  ctt/inscripciones.py
inscripciones/importarcanvas.html  <-  ctt/inscripciones.py
inscripciones/moverentrevista.html  <-  ctt/inscripciones.py
inscripciones/moverexamen.html  <-  ctt/inscripciones.py
inscripciones/movilidad.html  <-  ctt/inscripciones.py
inscripciones/notatrabajotitulacion.html  <-  ctt/inscripciones.py
inscripciones/notificartribunal.html  <-  ctt/inscripciones.py
inscripciones/novalidapromedio.html  <-  ctt/inscripciones.py
inscripciones/novalidar.html  <-  ctt/inscripciones.py
inscripciones/novalidarpromedio.html  <-  ctt/inscripciones.py
inscripciones/recalcularcreditos.html  <-  ctt/inscripciones.py
inscripciones/resetear.html  <-  ctt/inscripciones.py
inscripciones/resetearcertificado.html  <-  ctt/inscripciones.py
inscripciones/retirocarrera.html  <-  ctt/inscripciones.py
inscripciones/trabajotitulacion.html  <-  ctt/inscripciones.py
inscripciones/tribunal.html  <-  ctt/inscripciones.py
inscripciones/validapromedio.html  <-  ctt/inscripciones.py
inscripciones/validar.html  <-  ctt/inscripciones.py
inscripciones/validarpromedio.html  <-  ctt/inscripciones.py
mailbox/integrantesgrupo.html  <-  ctt/api.py
nuevomensaje.html  <-  ctt/api.py
```

## Templates de Email (html_template/template=...) Vacias

```text
emails/aperturamateria.html  <-  ctt/pro_evaluaciones.py
emails/asignarsolicitud.html  <-  ctt/models.py
emails/comentarsolicitud.html  <-  ctt/models.py
emails/correobasico.html  <-  ctt/tasks.py
emails/deber.html  <-  ctt/pro_clases.py
emails/incidencia.html  <-  ctt/models.py
emails/matricula.html  <-  ctt/commonviews.py
emails/notificacionanulacionmatricula.html  <-  ctt/matriculas.py
emails/notificacionaperturadistributivo.html  <-  ctt/models.py
emails/notificacionaprimerflujodistributivo.html  <-  ctt/models.py
emails/notificacioncambiodistributivo.html  <-  ctt/models.py
emails/notificaciondeposito.html  <-  ctt/adm_depositoinscripcion.py
emails/notificacionflujodistributivo.html  <-  ctt/models.py
emails/notificacionparqueadero.html  <-  ctt/models.py
emails/nuevaclavecalificaciones.html  <-  ctt/pro_evaluaciones.py
emails/observaciondocenteguia.html  <-  ctt/pro_planificacion.py
emails/observacionguiadocente.html  <-  ctt/pro_planificacion.py
emails/reasignarsolicitud.html  <-  ctt/models.py
emails/rechazosolicituddistributivo.html  <-  ctt/models.py
emails/respuestaincidencia.html  <-  ctt/models.py
emails/respuestasolicitud.html  <-  ctt/models.py
```
