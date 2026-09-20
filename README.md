# MinutoDesk

Prototipo de mesa de ayuda corporativa con inteligencia artificial — trabajo de
titulación en Ingeniería en Sistemas.

## Componentes

1. **Clasificador automático** (TF-IDF + SVM): predice tipo (solicitud,
   incidencia, acceso) y categoría (software, hardware, redes, seguridad) de
   cada ticket. Meta: precisión ≥80%, cobertura del 100%.
2. **Asistente conversacional "Minutito"**: corre sobre un modelo de lenguaje
   local vía Ollama (no se entrena, se configura con prompts). Meta: ≥30% de
   resolución autónoma de consultas de primer nivel.
3. **Gamificación**: lógica de negocio simple (sin IA) que da puntos e
   insignias por usar el autoservicio.

Prototipo de alcance acotado: corre en una sola máquina conectada a la red
interna, sin servicios en la nube.

## Estructura del proyecto

```
backend/    API FastAPI + SQLModel + clasificador ML
frontend/   React + Vite (pendiente)
data/       Export de tickets históricos (tickets_historicos.csv)
```

## Backend: instalación y arranque

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Verificar que arrancó: [http://localhost:8000/health](http://localhost:8000/health)
debe devolver `{"status": "ok"}`.
