"""Escenarios de la prueba controlada de Minutito: problemas típicos de primer nivel.

Cada escenario fija de antemano qué le pasa al colaborador (`situacion`), la causa real
que él no conoce (`causa`) y qué lo arregla (`arreglo`). El agente que hace de
colaborador redacta el mensaje con sus palabras y conversa con Minutito, pero el caso
no lo inventa el modelo: está escrito aquí y se puede revisar y citar en la tesis.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Escenario:
    clave: str
    tema: str
    situacion: str
    causa: str
    arreglo: str


ESCENARIOS = [
    # Wi-Fi e internet
    Escenario("wifi-olvidar", "Wi-Fi e internet", "La laptop no se conecta al Wi-Fi de la oficina; dice «No se puede conectar a esta red».",
              "La red quedó guardada con la contraseña anterior.", "Olvidar la red Wi-Fi y volver a conectarse escribiendo la contraseña."),
    Escenario("wifi-modo-avion", "Wi-Fi e internet", "En la laptop no aparece ninguna red Wi-Fi.",
              "El modo avión quedó activado.", "Desactivar el modo avión o activar el Wi-Fi."),
    Escenario("internet-cable", "Wi-Fi e internet", "En el escritorio no hay internet y el ícono de red muestra una X roja.",
              "El cable de red está flojo.", "Volver a conectar bien el cable de red."),
    Escenario("wifi-invitados", "Wi-Fi e internet", "Hay internet, pero el sistema interno de la empresa no abre.",
              "La laptop está conectada a la red Wi-Fi de invitados.", "Conectarse a la red Wi-Fi corporativa."),
    # Impresoras
    Escenario("impresora-cola", "Impresoras", "Manda a imprimir y no sale nada.",
              "Hay un documento atascado en la cola de impresión.", "Cancelar los documentos de la cola de impresión y volver a enviar."),
    Escenario("impresora-predeterminada", "Impresoras", "Imprime y la hoja sale en la impresora de otro piso.",
              "Está seleccionada otra impresora.", "Elegir la impresora correcta al imprimir o dejarla como predeterminada."),
    Escenario("impresora-papel", "Impresoras", "La impresora tiene una luz naranja parpadeando y no imprime.",
              "Hay una hoja atascada.", "Abrir la impresora y retirar la hoja atascada."),
    Escenario("impresora-apagada", "Impresoras", "Al imprimir sale «Impresora sin conexión».",
              "La impresora está apagada.", "Encender la impresora y esperar a que esté lista."),
    # Office y correo
    Escenario("outlook-buzon", "Office y correo", "No puede enviar correos; Outlook dice que el buzón está lleno.",
              "El buzón llegó a su límite.", "Eliminar correos con adjuntos grandes y vaciar Elementos eliminados."),
    Escenario("outlook-sin-conexion", "Office y correo", "Outlook dice «Trabajando sin conexión» y no llegan correos.",
              "Se activó el modo sin conexión.", "En la pestaña Enviar y recibir, desactivar «Trabajar sin conexión»."),
    Escenario("outlook-adjunto", "Office y correo", "No puede enviar un correo con un archivo de 40 MB.",
              "El archivo supera el límite de adjuntos.", "Subir el archivo a OneDrive y enviar el enlace."),
    Escenario("outlook-firma", "Office y correo", "Quiere que sus correos salgan con su firma.",
              "No tiene firma configurada.", "Crear la firma en Archivo > Opciones > Correo > Firmas."),
    Escenario("excel-solo-lectura", "Office y correo", "Un Excel descargado del correo se abre y no deja editar.",
              "El archivo está en vista protegida.", "Pulsar «Habilitar edición» en la barra amarilla."),
    Escenario("word-recuperar", "Office y correo", "Word se cerró de golpe y no guardó el documento.",
              "El documento quedó en la recuperación automática.", "Ir a Archivo > Información > Administrar documento > Recuperar documentos no guardados."),
    Escenario("office-licencia", "Office y correo", "Word muestra «Producto sin licencia».",
              "Office no tiene la sesión de la cuenta corporativa iniciada.", "Iniciar sesión con la cuenta corporativa en Archivo > Cuenta."),
    # Contraseñas y acceso
    Escenario("pass-mayusculas", "Contraseñas", "Windows dice que la contraseña es incorrecta y está seguro de que es esa.",
              "Bloq Mayús está activado.", "Desactivar Bloq Mayús y volver a escribirla."),
    Escenario("pass-caducada", "Contraseñas", "Al iniciar sesión sale que su contraseña caducó.",
              "La contraseña venció.", "Cambiarla en la pantalla que aparece (o con Ctrl+Alt+Supr > Cambiar contraseña) cumpliendo los requisitos."),
    Escenario("pass-teclado", "Contraseñas", "La contraseña, que tiene una @, no la acepta.",
              "El idioma del teclado cambió y la @ sale en otra tecla.", "Cambiar el idioma del teclado (Windows + Espacio) a Español."),
    # VPN y carpetas
    Escenario("vpn-internet", "VPN y carpetas", "Desde la casa la VPN no conecta.",
              "El Wi-Fi de la casa se cayó.", "Revisar que haya internet en la casa (reiniciar el router) y volver a conectar la VPN."),
    Escenario("vpn-reconectar", "VPN y carpetas", "La VPN dice conectada pero no se ven las carpetas compartidas.",
              "La sesión de la VPN quedó colgada.", "Desconectar la VPN, volver a conectarla y abrir otra vez la carpeta."),
    Escenario("unidad-red", "VPN y carpetas", "Desapareció la unidad Z: de la computadora.",
              "La unidad no se reconectó al iniciar.", "Conectarse a la red de la oficina o a la VPN y reiniciar el equipo."),
    Escenario("onedrive-pausado", "VPN y carpetas", "Los archivos no se suben a OneDrive.",
              "La sincronización está pausada.", "Reanudar la sincronización desde el ícono de OneDrive."),
    # Teams y videollamadas
    Escenario("teams-microfono", "Teams", "En las reuniones de Teams no lo escuchan.",
              "Teams tiene seleccionado otro micrófono.", "En Configuración de dispositivos de Teams, elegir el micrófono correcto."),
    Escenario("teams-camara", "Teams", "La cámara no se ve en Teams.",
              "Otra aplicación está usando la cámara.", "Cerrar las otras aplicaciones que usan la cámara y volver a entrar."),
    Escenario("teams-cargando", "Teams", "Teams se queda cargando y no abre.",
              "Teams quedó trabado en segundo plano.", "Salir de Teams por completo desde el ícono junto al reloj y volver a abrirlo."),
    Escenario("teams-notificaciones", "Teams", "No le llegan notificaciones de Teams.",
              "Está activado No molestar en Windows.", "Desactivar No molestar (Asistente de concentración)."),
    # Navegador
    Escenario("navegador-cache", "Navegador", "Una página interna se ve desordenada y no carga bien.",
              "El navegador guardó una versión vieja.", "Recargar con Ctrl+F5 o borrar la caché del navegador."),
    Escenario("navegador-emergentes", "Navegador", "Al descargar un reporte de una página no se abre nada.",
              "El navegador bloquea las ventanas emergentes.", "Permitir ventanas emergentes para ese sitio."),
    Escenario("pdf-predeterminado", "Navegador", "Los PDF se abren en el navegador y no los puede firmar.",
              "El navegador es la aplicación predeterminada para PDF.", "Abrir con Adobe Acrobat o dejarlo como predeterminado para PDF."),
    # Lentitud del equipo
    Escenario("lento-reinicio", "Lentitud", "La laptop está muy lenta.",
              "No se reinicia hace semanas.", "Reiniciar el equipo."),
    Escenario("lento-pestanas", "Lentitud", "Todo va lento cuando tiene el navegador abierto.",
              "Tiene demasiadas pestañas abiertas.", "Cerrar pestañas o cerrar procesos pesados desde el Administrador de tareas."),
    Escenario("lento-disco", "Lentitud", "Sale el aviso de disco lleno y todo va lento.",
              "El disco está lleno.", "Liberar espacio: vaciar la papelera, borrar descargas o usar el Liberador de espacio."),
    # Periféricos
    Escenario("mouse-pilas", "Periféricos", "El mouse inalámbrico no funciona.",
              "Se acabaron las pilas.", "Cambiar las pilas del mouse."),
    Escenario("monitor-extender", "Periféricos", "El segundo monitor está encendido pero no da imagen.",
              "Windows está mostrando solo la pantalla de la laptop.", "Presionar Windows + P y elegir Extender."),
    Escenario("teclado-numerico", "Periféricos", "No funcionan los números del teclado de la derecha.",
              "Bloq Num está desactivado.", "Activar Bloq Num."),
    Escenario("audio-salida", "Periféricos", "No sale sonido de la laptop.",
              "El sonido sale por otro dispositivo.", "Elegir los altavoces correctos en el ícono de sonido."),
    Escenario("proyector", "Periféricos", "Conecta el proyector de la sala y no se ve nada.",
              "No está duplicada la pantalla.", "Presionar Windows + P y elegir Duplicar."),
    Escenario("cargador", "Periféricos", "La laptop no carga.",
              "La regleta donde está el cargador está apagada.", "Revisar que el cargador esté bien conectado y la regleta encendida."),
    # Dudas de uso
    Escenario("captura", "Dudas de uso", "Quiere tomar una captura de solo una parte de la pantalla.",
              "No conoce el atajo.", "Usar Windows + Shift + S."),
    Escenario("teams-compartir", "Dudas de uso", "No sabe cómo compartir la pantalla en una reunión de Teams.",
              "No conoce la opción.", "Pulsar el botón Compartir en la reunión y elegir la pantalla o ventana."),
]
