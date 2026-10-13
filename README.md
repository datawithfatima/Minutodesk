# MinutoDesk

Prototipo de mesa de ayuda con inteligencia artificial — trabajo de titulación
en Ingeniería en Sistemas.

## Componentes

1. **Clasificador automático** (TF-IDF + SVM): predice tipo (solicitud,
   incidencia, acceso) y categoría de cada ticket. Meta: precisión ≥80 %.
2. **Asistente conversacional "Minutito"**: responde al instante las consultas
   frecuentes (contraseñas, VPN, impresoras, Office, videollamadas…) con pasos
   verificados, y para lo demás usa un modelo de lenguaje local vía Ollama (no se
   entrena, se configura con prompts). Meta: ≥30 % de resolución autónoma de
   consultas de primer nivel. Un ticket solo cuenta como resuelto por Minutito si
   el usuario lo confirma.
3. **Gamificación**: lógica de negocio simple (sin IA) que da puntos por usar
   el autoservicio ("Mis logros" para el usuario, "Ranking" para el personal).

Prototipo de alcance acotado: corre en una sola máquina, sin servicios en la nube.
La interfaz está en español y se adapta a móvil, tablet y escritorio.

## Roles

| Rol | Qué puede hacer |
|---|---|
| Usuario final | Crear tickets (con el formulario o hablando con Minutito), ver sus tickets, logros, histórico, FAQs y reportes propios |
| Técnico | Ver y atender todos los tickets (tomarlos, resolverlos, cancelarlos con motivo, corregir categoría y prioridad), ver usuarios, ranking y reportes de tickets |
| Administrador | Todo lo anterior, más crear/editar/eliminar usuarios y áreas, ver la calidad del clasificador e importar el CSV histórico |

No hay registro público: las cuentas las crea el administrador. Al crear una
cuenta el sistema genera una **contraseña temporal** que el administrador ve una
sola vez y le entrega a la persona; al iniciar sesión por primera vez el sistema
le exige cambiarla antes de usar nada (se valida en el servidor). Si la olvida,
"¿Olvidaste tu contraseña?" le envía un enlace de recuperación a su correo, y el
administrador también puede generar otra temporal ("Restablecer contraseña").
Cualquier usuario puede cambiar su contraseña o cerrar sesión desde el menú de su
cuenta (arriba a la derecha).

## Crear un ticket

«Crear ticket» (usuario final) reemplaza el formulario anterior de tickets:

1. La persona elige el **tipo** (incidencia, solicitud o gestión de usuarios y accesos); si
   no está segura, escribe la descripción y el SVM le **sugiere** uno.
2. Escribe la **descripción**; el SVM propone la **categoría** (con su confianza y las más
   probables) y ella la confirma o la cambia. Si la confianza es baja, se le pide elegir.
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
ollama pull llama3.2:3b
```

El modelo se cambia en `MODELO_OLLAMA` (`backend/app/services/assistant.py`), y las
respuestas para los problemas frecuentes en `backend/app/services/conocimiento.py`.
Sin Ollama activo, Minutito sigue respondiendo lo frecuente; para el resto avisa que
no está disponible y el ticket queda para el equipo de soporte (`iniciar.bat` avisa
si no lo detecta).

## Actualización mensual con el CSV de tickets

**Desde la página:** como administrador, menú "Datos históricos" → pestaña "Importar CSV"
(la pestaña "Análisis" muestra los gráficos del histórico y "Tickets importados" los
tickets uno por uno, solo de lectura y con prefijo `H-`, sin mezclarse con los de la
plataforma). Eliges el CSV,
el sistema lo limpia y muestra una vista previa (nuevos, actualizados, descartados y
el porqué); solo al pulsar "Confirmar e importar" se guarda. Esto alimenta los
análisis del histórico; el reentrenamiento del clasificador se hace con el script.

**Con el script**, desde `backend/` (importa y además reentrena):

```bash
python scripts/actualizar_mensual.py ruta\al\export.csv
```

Esto, en orden: guarda el CSV en `data/tickets_historicos_raw.csv`, lo importa a
la base para "Datos históricos" (los tickets se identifican por su ID: los
existentes se actualizan y los nuevos se agregan, sin duplicar) y reentrena el
clasificador. Usa `--sin-entrenar` para omitir el reentrenamiento. Después de
reentrenar, reinicia el backend.

De cada ticket importado se guardan, además de los datos para los indicadores, la
descripción, el solicitante y quién lo atendió, solo para que el administrador los
consulte. La base de datos y los CSV no se suben a git.

Para entrenar a mano: `python -m app.ml.prepare_dataset` y
`python -m app.ml.train_classifier`.
