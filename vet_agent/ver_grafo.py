import pathlib

from vet_agent.grafo import construir_grafo

SALIDA = pathlib.Path(__file__).resolve().parents[1] / "docs" / "grafo.png"


# script aparte solo para ver como quedo el grafo, no es parte del sistema
if __name__ == "__main__":
    app = construir_grafo()

    # genera la imagen del grafo y la guarda en docs/grafo.png
    imagen = app.get_graph().draw_mermaid_png()
    SALIDA.write_bytes(imagen)

    print(f"Listo, revisa {SALIDA}")
