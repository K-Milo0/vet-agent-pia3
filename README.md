# vet-agent-pia3

## Qué es

Sistema multiagente para la vigilancia de influenza aviar H5N1. Cuatro agentes (climático, diagnóstico, bioseguridad y moderador) analizan un caso, buscan evidencia en un corpus de documentos (RAG) y redactan un informe de apoyo a la decisión. Ningún informe se entrega sin la **revisión humana obligatoria**: una persona debe aprobarlo (o devolverlo con comentarios al moderador).

## Cómo instalar

Todos los comandos se corren desde la carpeta principal del repo.

1. **Python 3.10 o superior** (los comandos de este README se probaron con Python 3.13).
2. Crea y activa un entorno virtual:
   - macOS / Linux: `python3 -m venv .venv` y luego `source .venv/bin/activate`
   - Windows (PowerShell): `python -m venv .venv` y luego `.venv\Scripts\Activate.ps1`
3. Instala las dependencias (tarda varios minutos: incluye `torch` y `sentence-transformers`):
   ```
   pip install -r requirements.txt
   ```
4. Copia el archivo de configuración:
   - macOS / Linux: `cp .env.ejemplo .env`
   - Windows: `copy .env.ejemplo .env`
5. Carga el modelo en **LM Studio**:
   - Modelo: `qwen/qwen3-4b-2507` (Qwen3-4B Q4_K_M, GGUF).
   - Al cargarlo, sube **Context Length** a `16384` y deja **Max Concurrent Predictions** en `1`. Con menos contexto el moderador falla con `exceed_context_size_error`.
   - Enciende el servidor (pestaña *Developer* → *Start Server*, o `lms server start`). Debe quedar en `http://localhost:1234/v1`, que es el `LLM_URL` del `.env`.
6. **Sin LM Studio** (solo para probar): en el `.env` cambia `USAR_SIMULACION=false` por `USAR_SIMULACION=true`. Los agentes responden con textos de ejemplo.

### Documentos para la búsqueda (RAG)

La base de búsqueda `chroma_db/` **no está en git**: cada persona la arma en su computador. Sin ella el sistema corre igual, pero cada agente avisa `sin contexto RAG` y el informe sale sin fuentes citadas. Para armarla (necesita internet y tarda; el detalle está en [corpus/README.md](corpus/README.md)):

```
python -m vet_agent.rag.prefiltro
python -m vet_agent.rag.descargar_md
python -m vet_agent.rag.limpiar_texto
python -m vet_agent.rag.validar
python -m vet_agent.rag.indexar_md
```

Los 18 documentos del eje D que vienen de PDF ya están en `corpus/md/diagnostico/`. La primera vez que se busca, se descarga el modelo de embeddings `paraphrase-multilingual-MiniLM-L12-v2`.

## Cómo usarlo

**Demo web (Streamlit)** — formulario del caso, ejecución de los agentes y revisión humana en pantalla:

```
streamlit run app_demo.py
```

Se abre en <http://localhost:8501>.

**Terminal** — corre el caso de ejemplo `CASO_H5N1` y pregunta por terminal si apruebas el informe (`s` o `n`):

```
python -m vet_agent.main
```

**API (FastAPI)**:

```
uvicorn vet_agent.api:app --reload
```

| Ruta | Qué hace |
|---|---|
| `GET /escenarios` | Lista los escenarios de `corpus/escenarios` (por ejemplo `IAAP-00`, `IAAP-12`). |
| `GET /escenarios/{id}` | Devuelve solo la Parte A (la entrada) de ese escenario. |
| `POST /analizar` | Recibe un caso en JSON y devuelve `informe` y `fuentes`. Aprueba la revisión humana automáticamente. |

Documentación interactiva en <http://localhost:8000/docs>.

## Pruebas y evaluación

**Pruebas automáticas** (no necesitan LM Studio ni internet):

```
python -m vet_agent.pruebas
```

Deben pasar todas. La prueba de integración con Chroma real se omite (y el programa lo avisa) si no están indexadas las tres colecciones.

**Evaluación** — compara tres configuraciones: B1 (LLM sin RAG), B2 (un solo agente con RAG) y B3 (multiagente):

```
python -m vet_agent.evaluar
python -m vet_agent.evaluar --escenarios corpus/escenarios --repeticiones 3
```

Necesita `chroma_db` armada y LM Studio encendido (o `USAR_SIMULACION=true`). **Una corrida completa con el modelo real puede tomar muchas horas.** Cada intento queda como una fila en `resultados/registro_corridas.csv`, y el resumen de la última ejecución en `resultados/comparacion.csv`.

## Carpetas

- `vet_agent/agentes`: los cuatro agentes (climático, diagnóstico, bioseguridad y moderador) y su base común.
- `vet_agent/rag`: descarga, limpieza, validación e indexación de documentos, y la búsqueda en Chroma.
- `vet_agent/datos`: clima (Open-Meteo), tabla de planteles simulados y carga de escenarios desde Excel.
- `corpus`: documentos fuente, metadatos, escenarios de Investigación (`escenarios/`) y preguntas de prueba.
- `resultados`: salidas de `evaluar.py` (comparaciones y registro de corridas).
- `docs`: documentación del proyecto (diccionario de datos).

Además, en la raíz: `app_demo.py` (demo), `vet_agent/prompts.py` (prompts de los agentes), `vet_agent/grafo.py` (flujo entre agentes) y `.env.ejemplo` (configuración de ejemplo).

## Más información

- [corpus/README.md](corpus/README.md): cómo se arma el corpus y estado de los documentos.
- [corpus/datos/README.md](corpus/datos/README.md): aviso sobre los planteles simulados.
- [resultados/README.md](resultados/README.md): resultados de la comparación de configuraciones y problemas de memoria con MLX.
- [docs/diccionario_datos.md](docs/diccionario_datos.md): campos del caso, reglas de normalización y formato de los escenarios.
