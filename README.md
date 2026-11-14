# MinutoDesk

Prototipo de mesa de ayuda con inteligencia artificial — trabajo de titulación
en Ingeniería en Sistemas.

## Componentes

1. **Clasificador automático** (TF-IDF + SVM): predice tipo (solicitud,
   incidencia, acceso) y categoría de cada ticket. Meta: precisión ≥80 %.
2. **Asistente conversacional "Minutito"**: un chat tipo ChatGPT para soporte de
   primer nivel, con un modelo de lenguaje local vía Ollama (no se entrena, se
   configura con prompts). Se conversa **sin ticket**: si se resuelve, la persona lo
   confirma; si no (o es algo que solo puede hacer el equipo), Minutito arma el
   ticket con la conversación. Meta: ≥30 % de resolución autónoma (conversaciones
   resueltas sin ticket sobre las terminadas).
3. **Gamificación**: lógica de negocio simple (sin IA) que da puntos por usar
   el autoservicio ("Mis logros" para el usuario, "Ranking" para el personal).

Prototipo de alcance acotado: corre en una sola máquina, sin servicios en la nube.
La interfaz está en español y se adapta a móvil, tablet y escritorio.

## Roles

| Rol | Qué puede hacer |
|---|---|
| Usuario | Crear tickets (con el formulario o hablando con Minutito), conversar con soporte, responder aprobaciones, ver sus tickets, logros, histórico y FAQs |
| Técnico | Ver y atender todos los tickets (tomarlos, resolverlos, cancelarlos con motivo, corregir categoría y prioridad), ver usuarios, ranking y reportes de tickets |
| Administrador | Todo lo anterior, más crear/editar/eliminar usuarios y áreas, ver la calidad del clasificador e importar el CSV histórico |

No hay registro público: las cuentas las crea el administrador. Al crear una
cuenta, a la persona le llega a su correo un **enlace para elegir su contraseña**
(vale 3 días); el administrador nunca la ve. Si la olvida, "¿Olvidaste tu
contraseña?" le envía un enlace de recuperación, y el administrador puede pedir
que se le envíe uno nuevo ("Restablecer contraseña", vale 24 horas). Tras 5
intentos fallidos de inicio de sesión, ese correo queda bloqueado 15 minutos.

## Chat con soporte y aprobaciones

En cada ticket, el usuario y el técnico conversan en «Chat con soporte» / «Chat con el
usuario». El técnico puede **solicitar una aprobación** a otra persona (p. ej. el jefe
del área): le llega un aviso por correo y la responde en «Aprobaciones» (aprobar, o
rechazar con motivo). Mientras haya una aprobación pendiente el ticket no se puede
resolver. Minutito solo está en el panel del usuario final.
Cualquier usuario puede cambiar su contraseña o cerrar sesión desde el menú de su
cuenta (arriba a la derecha).

## Crear un ticket

«Crear ticket» (usuario final) reemplaza el formulario anterior de tickets:

1. La persona elige el **tipo** (incidencia, solicitud o gestión de usuarios y accesos); si
   no está segura, escribe la descripción y el SVM le **sugiere** uno.
2. Escribe la **descripción** y el SVM clasifica la **categoría** solo: si su confianza
   supera el umbral medido al entrenar (40 %), queda **asignada automáticamente** (la persona
   puede cambiarla si quiere); si no, se le muestran las más probables y debe elegir.
3. Elige la **prioridad** (por defecto Normal) y puede **adjuntar hasta 3 archivos de 10 MB**
   (Word, Excel, PowerPoint, PDF, imagen, video, audio o texto).
4. «Gestión de usuarios y accesos» abre el **alta de colaborador** (datos estructurados, con
   validación de cédula); esos tickets no pasan por el SVM.

Lo que la persona confirma, y lo que el técnico corrige, se compara con la sugerencia del SVM:
así el administrador ve el **acierto real en uso** (Reportes → Calidad del clasificador). Las
opciones del formulario (listas, aplicaciones, licencias, extensiones) están en
`backend/app/services/catalogos.py`. Los archivos se guardan en `backend/uploads/` (ignorado por git).

## Estados de un ticket

| Estado | Significado |
|---|---|
| Nuevo | Recién creado, nadie lo atiende todavía (en la base se guarda como `abierto`) |
| En proceso | Un técnico lo tomó |
| Resuelto | Lo cerró Minutito (con la confirmación del usuario) o el equipo de soporte |
| Cancelado | El personal lo cerró sin resolverlo, siempre con un motivo que el usuario ve |

Solo el técnico o el administrador pueden cancelar un ticket, y pueden reabrirlo si fue
un error. Un ticket cancelado no cuenta como resuelto, no entra en el tiempo medio de
resolución ni en el % de resolución autónoma, y no da puntos. Cada cambio de estado queda
en el historial del ticket con quién lo hizo.

## Otras funciones del portal

- **Encuesta de satisfacción:** al resolverse un ticket, quien lo abrió lo califica de 1 a 5
  estrellas con un comentario opcional (el correo de «resuelto» lo invita). El resultado
  está en Reportes → Satisfacción del usuario.
- **Exportar reportes:** Reportes → Excel o PDF (técnico y administrador). El Excel trae una
  hoja con todos los tickets, sin descripciones. La calidad del clasificador solo va en el
  del administrador.
- **Base de conocimiento:** el usuario ve los procedimientos de `services/conocimiento.py`
  (los mismos de Minutito) y los busca describiendo su problema. Es solo lectura.
- **Respuestas predefinidas:** en el chat del ticket, el personal inserta textos listos con
  `{nombre}`, `{ticket}` y `{tecnico}`, y los ajusta antes de enviar.
- **Tickets duplicados:** en el detalle, el personal busca tickets abiertos parecidos y
  marca el actual como duplicado de otro; queda cancelado con el motivo «Duplicado del
  ticket #X» y la atención sigue en el principal.
- **Respaldos:** cada 24 h se copia la base a `backend/respaldos/` (se guardan los últimos
  14; `RESPALDO_AUTOMATICO=0` lo apaga). Para restaurar: detener el backend y reemplazar
  `minutodesk.db` por la copia.
- **Bitácora de auditoría:** el administrador ve en «Bitácora y respaldos» quién hizo qué y
  cuándo (inicios de sesión, usuarios, tickets, descargas, exportaciones, intentos sin
  permiso). No guarda contraseñas ni el texto de los mensajes (`services/auditoria.py`).

## Estructura del proyecto

```
backend/    API FastAPI + SQLModel + clasificador ML + pruebas (pytest)
frontend/   React + Vite + Tailwind
data/       Export de tickets históricos (no se sube a git)
```

## Arranque rápido (Windows)

Con el entorno ya instalado, doble clic a `iniciar.bat`: abre backend y
frontend en dos ventanas y el navegador en <http://localhost:5173>.

## Backend: instalación y arranque

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts/seed_data.py --admin-email tu@correo.com --admin-nombre "Tu Nombre"
uvicorn app.main:app --reload
```

- Verificar: <http://localhost:8000/health> debe devolver `{"status": "ok"}`.
- `seed_data.py` crea las áreas y tu administrador con una **contraseña
  temporal** que imprime una sola vez; la cambias al primer ingreso. Desde ahí,
  el administrador crea las demás cuentas en la página (Usuarios). Con `--demo`
  agrega además cuentas de prueba (contraseña `minutodesk123`), solo para
  desarrollo.
- **Correo (solo recuperación de contraseña):** sin `SMTP_HOST` en `backend/.env`
  los correos no se envían, se guardan como `.txt` en `backend/correos_enviados/`
  (ahí está el enlace de recuperación). Para correos reales configura las
  variables `SMTP_*` (ver `.env.example`).
- Las bases creadas con una versión anterior se actualizan solas al arrancar
  (columnas nuevas y el estado «cancelado»), sin perder datos.
- **Pruebas:** `python -m pytest` desde `backend/`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Abre <http://localhost:5173>. La URL del backend se deduce del host actual
(puerto 8000) o de `VITE_API_URL`. La tipografía (Inter) se instala con npm, así
que la interfaz funciona sin conexión a internet.

## Minutito (Ollama)

Instala [Ollama](https://ollama.com), descarga el modelo y deja el servicio
corriendo en `localhost:11434`:

```bash
ollama pull qwen2.5:7b
```

Se eligió `qwen2.5:7b` por su desempeño en español dentro del hardware del
prototipo (sin GPU: cada respuesta tarda unos 30–50 s y se va mostrando mientras se
escribe). El modelo se cambia en `MODELO_CHAT` (`backend/app/services/minutito_chat.py`).
Los pasos verificados de `backend/app/services/conocimiento.py` se le pasan al modelo
como referencia del tema. Cuando ofrece crear un ticket, el modelo agrega una marca
que el servidor quita y que hace resaltar el botón «Crear ticket con esta
conversación». Sin Ollama activo, Minutito avisa que no está disponible y ofrece
crear el ticket (`iniciar.bat` avisa si no lo detecta).

## Datos históricos y entrenamiento

El CSV histórico (`data/tickets_historicos_raw.csv`, tickets del 26/12/2025 al
04/09/2026) se cargó **una sola vez**: es el conjunto con el que se entrena el
clasificador y lo que muestra "Datos históricos" (análisis y tickets importados, solo
de lectura y con prefijo `H-`). Ya no se vuelve a subir desde la página.

Para reentrenar a mano con ese mismo CSV: `python -m app.ml.prepare_dataset` y
`python -m app.ml.train_classifier` (desde `backend/`), y reinicia el backend.

Los tickets posteriores no se usan para entrenar. Los tickets nuevos de la empresa se
cargaron una sola vez (la pantalla de carga ya se retiró): cada uno se creó en
MinutoDesk con su fecha y estado reales: el SVM propone tipo y categoría, y los
reales quedan como la elección de la persona, así que la comparación aparece en
"Reportes → Calidad del clasificador" (acierto en uso). Se ignoran los ID del
histórico y los ya cargados, y se descartan los que no traen tipo, categoría o
descripción. Quien pidió el ticket no necesita cuenta: su nombre queda en el ticket
(a cargo de una cuenta interna sin acceso).

### Privacidad de los datos de la empresa

Los nombres de solicitantes y técnicos del histórico y de los tickets cargados se
guardan como alias estables ("Solicitante 007", "Técnico 03"); en la base solo queda
el hash del nombre. En las descripciones se reemplazan correos, cédulas, teléfonos y
nombres de personas. Para anonimizar lo que esté en la base:
`python scripts/anonimizar_datos.py` (desde `backend/`). Los CSV originales de `data/`
siguen con los datos reales: no salen de este equipo (están en `.gitignore`).

### Evaluación simulada de Minutito

Los tickets cargados se atendieron en la herramienta anterior, así que no hay
conversaciones reales con Minutito. En "Datos históricos → Evaluación de Minutito" se
le pasa a Minutito el texto de cada ticket y una persona del equipo marca si la
respuesta lo habría resuelto (o si no es de primer nivel). El porcentaje se reporta
como **estimación por evaluación experta**, separado de la resolución autónoma real,
y no crea conversaciones ni cambia los tickets.

### Simulación del tiempo de resolución

"Datos históricos → Simulación de tiempos" compara el tiempo promedio real de los tickets
nuevos cargados (ya resueltos) con el simulado: a los que según la evaluación Minutito
habría resuelto se les asigna el tiempo de una conversación (15 minutos por defecto). La
línea base del histórico se calcula con creación → fecha de solución. Ojo: la columna
"Días de atención" del export no es el tiempo real sino el plazo (SLA) según la prioridad.

