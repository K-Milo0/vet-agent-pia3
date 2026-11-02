# Prueba en seco con LM Studio (IAAP-12)

Corrida del 02/11/2026 con la configuración congelada:

- Qwen3-4B Q4_K_M (GGUF) en LM Studio, Context Length 16.384, Max Concurrent Predictions 1.
- `.env` idéntico a `.env.ejemplo`: `LLM_MAX_TOKENS=3000`, temperatura 0.2, `K_FRAGMENTOS=3`.
- Commit `5207adf`, prompts `v1`.

```
python -m vet_agent.evaluar --escenarios prueba_seco --repeticiones 1
```

Archivos:

- `registro_corridas.csv`: las 5 filas, una por intento.
- `comparacion.csv`: el resumen de la corrida.

Se guardaron en esta carpeta, y no en `resultados/registro_corridas.csv`, para que las filas de prueba no se mezclen con las corridas finales: el registro agrega filas y no se borra.

## Resultado

Las 3 configuraciones terminaron en `ok`, pero dos necesitaron un segundo intento.

| Configuración | Intento | Estado | Tiempo | Motivo del error |
|---|---|---|---|---|
| B1 | 1 | error | 52,5 s | El modelo respondió algo que no es JSON válido (terminó normal, no se cortó). |
| B1 | 2 | ok | 47,9 s | |
| B2 | 1 | ok | 86,6 s | |
| B3 | 1 | error | 493,6 s | **La respuesta del moderador se cortó al llegar a `max_tokens` (3000).** |
| B3 | 2 | ok | 522,2 s | |

Tiempo total: 1.207 s (~20 min).

Sin reintentos, IAAP-12 toma 48 + 87 + 522 s ≈ **11 min** por repetición.

## ¿B3 cabe en el contexto?

**Sí.** Según el log de LM Studio, la llamada más grande es la del moderador:

| Intento | Prompt | Respuesta | Total |
|---|---|---|---|
| 1 | 8.627 tokens | 3.000 tokens | 11.627 de 16.384 |
| 2 | 8.520 tokens | 2.755 tokens | 11.275 de 16.384 |

Quedan unos 4.700 tokens libres. Los otros agentes usan menos:

| Agente | Prompt | Respuesta |
|---|---|---|
| Climático | 2.665 | ~1.700 |
| Diagnóstico | 1.433 | ~1.000 |
| Bioseguridad | ~5.170 | ~2.200 |

## Lo que falla: `max_tokens` del moderador

- El moderador necesita casi 3.000 tokens de respuesta para el informe de IAAP-12.
- En el intento 1 llegó al tope y se cortó. En el intento 2 usó 2.755, el 92 % del tope.
- Con `LLM_MAX_TOKENS=3000`, B3 puede fallar seguido en las corridas finales. Cada intento fallido cuesta unos 8 minutos, y con 4 intentos fallidos la corrida queda en `error`.

**Propuesta** (no se aplicó, porque la configuración está congelada):

- Subir `LLM_MAX_TOKENS` a **4096** en `.env.ejemplo`.
- Así el peor caso queda en ~8.700 + 4.096 ≈ 12.800 tokens, todavía bajo 16.384.
- Hay que decidirlo antes de las corridas finales, porque cambia la configuración que se registra en cada fila.

El error de B1 en el intento 1 (JSON inválido) es del modelo, no del tope: se resolvió solo en el intento 2.

## Registro

- `id_corrida` sale con el formato acordado: `B1-IAAP-12-R1-I1` … `B3-IAAP-12-R1-I2`.
- Todas las columnas tienen valor, salvo `fragmentos` en B1 (no busca documentos) y en las filas con error, como se definió.
- Datos fijos de la corrida:
  - `modelo_y_version` = `qwen/qwen3-4b-2507 (gguf Q4_K_M)`
  - `version_sistema` = `5207adf`
  - `version_prompt_base` = `v1`
- B2 y B3 recuperaron 9 fragmentos cada uno (3 por colección).

## Para las corridas finales

- **Tiempo estimado:** con 12 escenarios × 3 repeticiones, son ~6,6 h si nada se reintenta, o ~12 h si se reintenta como en esta prueba. Depende de cuánto se repita B3.
- **Antes de correr en otro PC:**
  - Actualizar las librerías (`pip install -r requirements.txt`): ahora se necesitan `fastapi` y `uvicorn`, y sin ellas `python -m vet_agent.pruebas` falla.
  - Rehacer la base (`descargar_md`, `limpiar_texto`, `indexar_md`) si se armó antes del PR #30, que agregó D3 a `bioseguridad_md`.
