"""Script para revisar escenarios JSON (Tarea 3 · Camilo).

Revisa los archivos de corpus/escenarios, valida campos, traduce documentos_esperados
con las equivalencias de Revision_fuentes_scraping_PIA3.xlsx y comprueba que existan
en el corpus según reporte_validacion.xlsx.

Uso:
    python -m vet_agent.datos.revisar_escenarios
    python -m vet_agent.datos.revisar_escenarios --carpeta corpus/escenarios
"""

import argparse
import json
import pathlib


RAIZ = pathlib.Path(__file__).resolve().parents[2]
CARPETA_ESCENARIOS = RAIZ / "corpus" / "escenarios"
EQUIV_XLSX = RAIZ / "corpus" / "fuentes" / "Revision_fuentes_scraping_PIA3.xlsx"
VALIDACION_XLSX = RAIZ / "corpus" / "md" / "reporte_validacion.xlsx"


def _columna(encabezado, nombre):
    """Indice de la columna `nombre` en la fila de encabezados (asi no depende del orden)."""
    nombres = [str(c).strip() if c is not None else "" for c in encabezado]
    if nombre not in nombres:
        raise KeyError(f"no está la columna {nombre!r} en los encabezados: {nombres}")
    return nombres.index(nombre)


def _cargar_equivalencias():
    try:
        import openpyxl
    except ImportError:
        return {}
    if not EQUIV_XLSX.exists():
        return {}
    wb = openpyxl.load_workbook(EQUIV_XLSX)
    if "Equivalencias IDs" not in wb.sheetnames:
        return {}
    ws = wb["Equivalencias IDs"]
    filas = ws.iter_rows(values_only=True)
    encabezado = next(filas, ())
    col_viejo = _columna(encabezado, "ID anterior (planilla antigua)")
    col_nuevo = _columna(encabezado, "ID vigente (Anexo A / E4)")
    equiv = {}
    for r in filas:
        viejo = r[col_viejo]
        nuevo = r[col_nuevo]
        if viejo and nuevo:
            viejo_s = str(viejo).strip()
            nuevo_s = str(nuevo).strip()
            if viejo_s and nuevo_s and nuevo_s.lower() != "(ninguno)":
                equiv[viejo_s] = nuevo_s
    return equiv


def _cargar_ids_ok():
    try:
        import openpyxl
    except ImportError:
        return set()
    if not VALIDACION_XLSX.exists():
        return set()
    wb = openpyxl.load_workbook(VALIDACION_XLSX)
    if "Archivos" not in wb.sheetnames:
        return set()
    ws = wb["Archivos"]
    filas = ws.iter_rows(values_only=True)
    encabezado = next(filas, ())
    col_id = _columna(encabezado, "id")
    col_estado = _columna(encabezado, "estado")
    ids_ok = set()
    for r in filas:
        id_ = r[col_id]
        estado = r[col_estado]
        if id_ and estado:
            if str(estado).strip().lower() != "excluido":
                ids_ok.add(str(id_).strip())
    return ids_ok


def _vacio(valor):
    if valor is None:
        return True
    if isinstance(valor, str):
        return valor.strip() == ""
    if isinstance(valor, (list, tuple, set)):
        return len(valor) == 0
    if isinstance(valor, dict):
        return len(valor) == 0
    return False


def _es_numero(valor):
    if isinstance(valor, bool):
        return False
    if isinstance(valor, (int, float)):
        return True
    if isinstance(valor, str):
        s = valor.strip()
        if s == "":
            return False
        try:
            float(s.replace(",", "."))
            return True
        except Exception:
            return False
    return False


def _revisar_objeto(obj, ruta, avisos, camino=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            nuevo_camino = f"{camino}.{k}" if camino else k
            if _vacio(v):
                avisos.append(f"{ruta}: campo vacío a propósito o sospechoso en {nuevo_camino}: {type(v).__name__}")
            else:
                _revisar_objeto(v, ruta, avisos, nuevo_camino)
    elif isinstance(obj, list):
        if len(obj) == 0:
            if camino:
                avisos.append(f"{ruta}: lista vacía en {camino}")
        else:
            for i, v in enumerate(obj):
                _revisar_objeto(v, ruta, avisos, f"{camino}[{i}]")


def revisar_archivo(ruta, equiv, ids_ok):
    try:
        data = json.loads(ruta.read_text(encoding="utf-8"))
    except Exception as e:
        return {"archivo": ruta.name, "errores": [f"no se pudo leer JSON: {e}"], "avisos": [], "documentos_esperados_traducidos": [], "faltantes": []}

    errores = []
    avisos = []
    id_esc = data.get("id_escenario") or ruta.stem

    parte_a = data.get("parte_a_entrada") or {}
    parte_b = data.get("parte_b_referencia") or {}

    _revisar_objeto(parte_a, id_esc, avisos, "parte_a_entrada")
    _revisar_objeto(parte_b, id_esc, avisos, "parte_b_referencia")

    numeros_a_revisar = [
        ("parte_a_entrada.n_animales", parte_a.get("n_animales")),
        ("parte_a_entrada.mortalidad_pct", parte_a.get("mortalidad_pct")),
        ("parte_a_entrada.morbilidad_pct", parte_a.get("morbilidad_pct")),
    ]
    clima = parte_a.get("clima") or {}
    numeros_a_revisar.append(("parte_a_entrada.clima.temperatura_media_c", clima.get("temperatura_media_c")))
    numeros_a_revisar.append(("parte_a_entrada.clima.humedad_relativa_pct", clima.get("humedad_relativa_pct")))
    numeros_a_revisar.append(("parte_a_entrada.clima.precipitacion_mm", clima.get("precipitacion_mm")))

    for nombre, val in numeros_a_revisar:
        if val is None or (isinstance(val, str) and val.strip() == ""):
            avisos.append(f"{id_esc}: {nombre} vacío")
            continue
        if not _es_numero(val):
            errores.append(f"{id_esc}: {nombre} debe ser número, es {type(val).__name__}: {val}")

    docs_esperados = parte_b.get("documentos_esperados") or []
    if isinstance(docs_esperados, str):
        docs_esperados = [d.strip() for d in docs_esperados.split(";") if d.strip()]
    docs_traducidos = []
    for d in docs_esperados:
        if not d:
            continue
        d_s = str(d).strip()
        if d_s in equiv:
            docs_traducidos.append(equiv[d_s])
        else:
            docs_traducidos.append(d_s)
    vistos = set()
    docs_unicos = []
    for d in docs_traducidos:
        if d not in vistos:
            vistos.add(d)
            docs_unicos.append(d)

    faltantes = []
    for d in docs_unicos:
        if d not in ids_ok:
            faltantes.append(d)

    return {
        "archivo": ruta.name,
        "id_escenario": id_esc,
        "errores": errores,
        "avisos": avisos,
        "documentos_esperados_originales": docs_esperados,
        "documentos_esperados_traducidos": docs_unicos,
        "faltantes": faltantes,
    }


def revisar_carpeta(carpeta):
    equiv = _cargar_equivalencias()
    ids_ok = _cargar_ids_ok()
    print(f"Equivalencias cargadas: {len(equiv)}")
    print(f"IDs OK en corpus (no excluidos): {len(ids_ok)}")
    print(f"Revisando: {carpeta}")
    print()

    archivos = sorted(carpeta.glob("*.json"))
    if not archivos:
        print("No se encontraron archivos .json")
        return

    resultados = []
    for ruta in archivos:
        res = revisar_archivo(ruta, equiv, ids_ok)
        resultados.append(res)
        print(f"== {res.get('archivo')} ({res.get('id_escenario')}) ==")
        if res["errores"]:
            for e in res["errores"]:
                print(f"  ERROR: {e}")
        if res["avisos"]:
            for a in res["avisos"]:
                print(f"  AVISO: {a}")
        orig = res.get("documentos_esperados_originales") or []
        trad = res.get("documentos_esperados_traducidos") or []
        if orig:
            print(f"  documentos_esperados (orig): {orig}")
        if trad:
            print(f"  documentos_esperados (traducidos): {trad}")
        if res["faltantes"]:
            for f in res["faltantes"]:
                print(f"  FALTA EN CORPUS: {f}")
        print()

    todos_faltantes = []
    for r in resultados:
        for f in r["faltantes"]:
            todos_faltantes.append(f"{f} ({r.get('id_escenario')})")
    vistos_f = []
    set_f = set()
    for x in todos_faltantes:
        clave = x.split(" ")[0]
        if clave not in set_f:
            vistos_f.append(x)
            set_f.add(clave)
    print("== RESUMEN ==")
    print(f"Archivos revisados: {len(resultados)}")
    print(f"Documentos que faltan en el corpus: {len(vistos_f)}")
    if vistos_f:
        for x in vistos_f:
            print(f"  - {x}")
    else:
        print("  (ninguno)")


def main():
    parser = argparse.ArgumentParser(description="Revisar escenarios JSON")
    parser.add_argument("--carpeta", default=None, help="Carpeta con archivos JSON")
    args = parser.parse_args()
    if args.carpeta:
        carpeta = pathlib.Path(args.carpeta)
        if not carpeta.is_absolute():
            carpeta = RAIZ / carpeta
    else:
        carpeta = CARPETA_ESCENARIOS
    revisar_carpeta(carpeta)


if __name__ == "__main__":
    main()
