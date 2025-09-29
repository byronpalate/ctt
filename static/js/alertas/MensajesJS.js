const NotificacionError = (titulo, mensaje) => {
    Swal.fire({
        icon: 'error', title: titulo, text: mensaje, confirmButtonColor: "#E74C3C"
    })
}

const NotificacionAlerta = (icon,titulo, mensaje) => {
    Swal.fire({
        icon: icon, title: titulo, text: mensaje, confirmButtonColor: "#E74C3C"
    })
}

const PopEsquinaAviso = (icon,mensaje) => {
    Swal.fire({
        position: "top-end",
        icon: icon,
        title: mensaje,
        showConfirmButton: false,
        timer: 1500
    });
}

function mostrarErroresFormulario(errors) {
    let erroresHTML = '';

    // Construir un listado de errores en HTML
    for (const [campo, mensajes] of Object.entries(errors)) {
        mensajes.forEach(mensaje => {
        erroresHTML += `<li><strong>${campo}:</strong> ${mensaje}</li>`;
    });
    }
    // Mostrar los errores usando Swal.fire
    Swal.fire({
        title: 'Verifique los Campos',
        html: erroresHTML,
        icon: 'error',
        confirmButtonText: 'Entendido'
    });
}
