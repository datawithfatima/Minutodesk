# MinutoDesk

Prototipo de mesa de ayuda con inteligencia artificial — trabajo de titulación
en Ingeniería en Sistemas.

## Componentes

1. **Clasificador automático** (TF-IDF + SVM): predice tipo (solicitud,
   incidencia, acceso) y categoría de cada ticket. Meta: precisión ≥80 %.
2. **Asistente conversacional "Minutito"**: corre sobre un modelo de lenguaje
   local vía Ollama (no se entrena, se configura con prompts). Meta: ≥30 % de
   resolución autónoma de consultas de primer nivel.
3. **Gamificación**: lógica de negocio simple (sin IA) que da puntos por usar
   el autoservicio ("Mis logros" para el usuario, "Ranking" para el personal).

Prototipo de alcance acotado: corre en una sola máquina, sin servicios en la nube.

## Roles

| Rol | Qué puede hacer |
|---|---|
| Usuario final | Crear tickets, chatear con Minutito, ver sus tickets, logros, histórico, FAQs y reportes propios |
| Técnico | Ver y atender todos los tickets (tomarlos, resolverlos), ver usuarios, ranking y reportes |
| Administrador | Todo lo anterior, más crear/editar usuarios y áreas |

No hay registro público: las cuentas las crea el administrador y cada persona
recibe un enlace por correo para activarla y elegir su contraseña. El login
incluye "¿Olvidaste tu contraseña?".

## Estructura del proyecto

```
backend/    API FastAPI + SQLModel + clasificador ML + pruebas (pytest)
frontend/   React + Vite + Tailwind
data/       Export de tickets históricos (no se sube a git)
docs/       Casos de uso, modelo relacional y documentación
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
- `seed_data.py` crea las áreas, cuentas de demostración (contraseña
  `minutodesk123`) y tu administrador **sin contraseña**: te genera un enlace
  de activación. Sin argumentos crea un administrador de demostración
  (`admin@ejemplo.com`), solo para desarrollo.
- **Correo:** sin `SMTP_HOST` en `backend/.env` los correos no se envían, se
  guardan como `.txt` en `backend/correos_enviados/` (ahí está el enlace de
  activación o de recuperación). Para correos reales configura las variables
  `SMTP_*` (ver `.env.example`).
- **Pruebas:** `python -m pytest` desde `backend/`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Abre <http://localhost:5173>. La URL del backend se deduce del host actual
(puerto 8000) o de `VITE_API_URL`.

## Minutito (Ollama)

Instala [Ollama](https://ollama.com), descarga el modelo y deja el servicio
corriendo en `localhost:11434`:

```bash
ollama pull llama3.2:3b
```

El modelo se cambia en `MODELO_OLLAMA` (`backend/app/services/assistant.py`).
Sin Ollama activo, el chat con Minutito no responde (`iniciar.bat` avisa si no
lo detecta).

## Entrenar el clasificador

Coloca el export crudo en `data/tickets_historicos_raw.csv` y, desde `backend/`:

```bash
python -m app.ml.prepare_dataset
python -m app.ml.train_classifier
```
