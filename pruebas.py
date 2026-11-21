import builtins
import io
import json
import random
import sys
import time
from contextlib import redirect_stdout

import navegador

# Pruebas de funcionamiento del Navegador de Rutas.
# Se ejecuta con: python pruebas.py   (en la misma carpeta que navegador.py y calles.json)
# Usa la red real (calles.json) y redes chicas armadas en memoria para los casos límite.
# El "teclado falso" reemplaza a input() con respuestas predefinidas.

resultados = {}


def registrar(codigo, descripcion, esperado, obtenido, ok):
    resultados[codigo] = {"descripcion": descripcion, "esperado": esperado, "obtenido": obtenido, "ok": ok}
    print(codigo, "OK   " if ok else "FALLÓ", descripcion)
    print("      esperado:", esperado)
    print("      obtenido:", obtenido)


def tecladoFalso(respuestas):
    cola = {"numero": 0}

    def falso(pregunta=""):
        cola["numero"] += 1
        return respuestas[cola["numero"]]
    return falso


def metrosDeRuta(grafo, nodos, origen, destino):
    # devuelve (metros reales, tramos) usando las mismas funciones que el programa
    distancias, previos = navegador.dijkstra(grafo, origen, destino)
    if distancias[destino] == float("inf"):
        return None, {}
    pasos, cantidad = navegador.armarRuta(previos, origen, destino)
    tramos, cuantos = navegador.armarTramos(grafo, nodos, pasos, cantidad)
    return distancias[destino], tramos


def distanciaIndependiente(grafo, origen, destino):
    # segunda implementación (networkx) para contrastar a dijkstra()
    import networkx as nx
    g = nx.DiGraph()
    for a in grafo:
        for b in grafo[a]:
            g.add_edge(a, b, weight=grafo[a][b])
    try:
        return nx.dijkstra_path_length(g, origen, destino)
    except nx.NetworkXNoPath:
        return None


def bellmanFord(grafo, origen):
    infinito = float("inf")
    dist = {}
    for n in grafo:
        dist[n] = infinito
    dist[origen] = 0
    for vuelta in range(len(grafo)):
        cambio = False
        for a in grafo:
            if dist[a] == infinito:
                continue
            for b in grafo[a]:
                if dist[a] + grafo[a][b] < dist[b]:
                    dist[b] = dist[a] + grafo[a][b]
                    cambio = True
        if not cambio:
            break
    return dist


datos = navegador.cargarDatos("calles.json")
nodos = datos["nodos"]
grafo = datos["tramos"]


def esquina(c1, c2, ciudad):
    return navegador.buscarEsquina(nodos, c1, c2)[ciudad]


# ---------------------------------------------------------------- PR-01 intraurbana (Corrientes)
o = esquina("san lorenzo", "3 de abril", "Corrientes")
d = esquina("lavalle", "costanera juan pablo", "Corrientes")
metros, tramos = metrosDeRuta(grafo, nodos, o, d)
ref = distanciaIndependiente(grafo, o, d)
registrar("PR-01", "Ruta dentro de Corrientes (San Lorenzo y 3 de Abril -> Lavalle y Costanera)",
          "Igual a networkx (" + str(round(ref, 1)) + " m)", str(round(metros, 1)) + " m en " + str(len(tramos)) + " tramos",
          abs(metros - ref) < 0.01)

# ---------------------------------------------------------------- PR-02 intraurbana (Resistencia)
o = esquina("peron", "cangallo", "Resistencia")
d = esquina("mansilla", "julio argentino roca", "Resistencia")
metros, tramos = metrosDeRuta(grafo, nodos, o, d)
ref = distanciaIndependiente(grafo, o, d)
registrar("PR-02", "Ruta dentro de Resistencia (Perón y Cangallo -> Gral. Mansilla y Julio A. Roca)",
          "Igual a networkx (" + str(round(ref, 1)) + " m)", str(round(metros, 1)) + " m en " + str(len(tramos)) + " tramos",
          abs(metros - ref) < 0.01)

# ---------------------------------------------------------------- PR-03 interurbana por el puente
o = esquina("san lorenzo", "3 de abril", "Corrientes")
d = esquina("peron", "cangallo", "Resistencia")
metros, tramos = metrosDeRuta(grafo, nodos, o, d)
ref = distanciaIndependiente(grafo, o, d)
callesRuta = {}
for t in tramos:
    callesRuta[tramos[t]["calle"]] = True
registrar("PR-03", "Ruta de Corrientes a Resistencia (debe cruzar el Puente General Belgrano)",
          "Igual a networkx y pasa por el puente",
          str(round(metros, 1)) + " m; puente: " + str("Puente General Belgrano" in callesRuta),
          abs(metros - ref) < 0.01 and "Puente General Belgrano" in callesRuta)

# ---------------------------------------------------------------- PR-04 el grafo es dirigido: ida y vuelta difieren
metrosVuelta, tramosVuelta = metrosDeRuta(grafo, nodos, d, o)
registrar("PR-04", "Sentido de circulación: la vuelta Resistencia -> Corrientes no tiene por qué medir igual",
          "Ida distinta de vuelta", "ida " + str(round(metros)) + " m, vuelta " + str(round(metrosVuelta)) + " m",
          abs(metros - metrosVuelta) > 1)

# ---------------------------------------------------------------- PR-05 normalización de texto
a = navegador.buscarEsquina(nodos, "PERON", "cangallo")
b = navegador.buscarEsquina(nodos, "Perón", "CANGALLO")
registrar("PR-05", "Normalización: 'PERON'+'cangallo' frente a 'Perón'+'CANGALLO'",
          "Misma esquina", str(a == b and len(a) == 1), a == b and len(a) == 1)

# ---------------------------------------------------------------- PR-06 esquina que existe en las dos ciudades
dosCiudades = navegador.buscarEsquina(nodos, "san martin", "pellegrini")
registrar("PR-06", "Desambiguación: San Martín y Pellegrini existe en ambas ciudades",
          "Dos ciudades", str(sorted(dosCiudades)), len(dosCiudades) == 2)
builtins_input = builtins.input
builtins.input = tecladoFalso({1: "san martin", 2: "pellegrini", 3: "2"})
salida = io.StringIO()
with redirect_stdout(salida):
    elegida = navegador.pedirEsquina(nodos, "Esquina de prueba")
builtins.input = builtins_input
registrar("PR-06b", "Desambiguación: elegir la opción 2 devuelve la esquina de la segunda ciudad",
          "Esquina de " + list(dosCiudades)[1], navegador.ciudadDeNodo(nodos[elegida]),
          elegida == list(dosCiudades.values())[1])

# ---------------------------------------------------------------- PR-07 grafo chico: mano única, corte y sin camino
chico = {"A": {"B": 100.0, "C": 50.0}, "B": {"A": 100.0, "D": 100.0}, "C": {"A": 50.0, "D": 300.0},
         "D": {"B": 100.0}, "Z": {}}
nodosChico = {}
for k in chico:
    nodosChico[k] = {"lat": 0, "lon": 0, "calles": {"Calle " + k: True}}
dist, prev = navegador.dijkstra(chico, "A", "D")
registrar("PR-07", "Grafo chico: A -> D por B (100+100) y no por C (50+300)", "200 m", str(dist["D"]) + " m", dist["D"] == 200)
dist, prev = navegador.dijkstra(chico, "D", "C")
registrar("PR-07b", "Mano única: D -> C debe rodear (D->B->A->C = 100+100+50)", "250 m", str(dist["C"]) + " m", dist["C"] == 250)
dist, prev = navegador.dijkstra(chico, "A", "Z")
registrar("PR-08", "Caso límite: destino sin conexión (Z aislado)", "Distancia infinita",
          str(dist["Z"]), dist["Z"] == float("inf"))
dist, prev = navegador.dijkstra(chico, "A", "A")
registrar("PR-09", "Caso límite: origen = destino", "0 m", str(dist["A"]) + " m", dist["A"] == 0)

# ---------------------------------------------------------------- PR-10 eliminar arista y recalcular
copia = {}
for k in chico:
    copia[k] = dict(chico[k])
builtins.input = tecladoFalso({1: "Calle B", 2: "Calle D", 3: "1", 4: "n"})
# eliminarArista usa pedirEsquina (dos calles por esquina): se arma un nodo con dos calles
nodosEdicion = {"A": {"lat": 0, "lon": 0, "calles": {"Calle A": True, "Calle X": True}},
                "B": {"lat": 0, "lon": 0, "calles": {"Calle B": True, "Calle X": True}},
                "C": {"lat": 0, "lon": 0, "calles": {"Calle C": True, "Calle X": True}},
                "D": {"lat": 0, "lon": 0, "calles": {"Calle D": True, "Calle X": True}},
                "Z": {"lat": 0, "lon": 0, "calles": {"Calle Z": True, "Calle X": True}}}
builtins.input = tecladoFalso({1: "calle b", 2: "calle x", 3: "1", 4: "n"})
with redirect_stdout(io.StringIO()):
    navegador.eliminarArista(copia, nodosEdicion)
builtins.input = builtins_input
dist, prev = navegador.dijkstra(copia, "A", "D")
registrar("PR-10", "Eliminar el tramo B->A (primer tramo listado de B) y no su sentido contrario",
          "A->B sigue existiendo", "B->A existe: " + str("A" in copia["B"]) + "; A->B existe: " + str("B" in copia["A"]),
          ("A" not in copia["B"]) and ("B" in copia["A"]))

# ---------------------------------------------------------------- PR-11 eliminar nodo
copia = {}
for k in chico:
    copia[k] = dict(chico[k])
builtins.input = tecladoFalso({1: "calle b", 2: "calle x", 3: "s"})
with redirect_stdout(io.StringIO()):
    navegador.eliminarNodo(copia, nodosEdicion)
builtins.input = builtins_input
dist, prev = navegador.dijkstra(copia, "A", "D")
registrar("PR-11", "Eliminar la esquina B: A -> D debe ir por C (50+300)", "350 m y B ya no está en el grafo",
          str(dist["D"]) + " m; B en el grafo: " + str("B" in copia), dist["D"] == 350 and "B" not in copia)

# ---------------------------------------------------------------- PR-12 entradas inválidas
builtins.input = tecladoFalso({1: "x", 2: "", 3: "N"})
with redirect_stdout(io.StringIO()):
    respuesta = navegador.pedirSiNo("¿Seguro? (s/n): ")
builtins.input = builtins_input
registrar("PR-12", "pedirSiNo: rechaza 'x' y '' y acepta 'N' (mayúscula)", "False", str(respuesta), respuesta is False)
builtins.input = tecladoFalso({1: "esta calle no existe", 2: "tampoco", 3: ""})
salida = io.StringIO()
with redirect_stdout(salida):
    resultado = navegador.pedirEsquina(nodos, "Esquina de prueba")
builtins.input = builtins_input
registrar("PR-12b", "pedirEsquina: calle inexistente y luego primera calle vacía",
          "Mensaje de error y cancelación (None)", "None" if resultado is None else "otra cosa",
          resultado is None and "No encontré" in salida.getvalue() and "Cancelado" in salida.getvalue())
registrar("PR-12c", "cargarDatos con archivo inexistente", "None sin excepción",
          str(navegador.cargarDatos("noExiste.json")), navegador.cargarDatos("noExiste.json") is None)

# ---------------------------------------------------------------- PR-13 validación cruzada con Bellman-Ford
random.seed(4)
semilla = {}
cantidad = 0
for n in grafo:
    cantidad += 1
    if cantidad % 700 == 0:
        semilla[n] = True
diferencias = 0
comparados = 0
for origen in semilla:
    dist, prev = navegador.dijkstra(grafo, origen)
    bf = bellmanFord(grafo, origen)
    for n in grafo:
        comparados += 1
        if dist[n] != bf[n] and abs(dist[n] - bf[n]) > 0.001:
            diferencias += 1
registrar("PR-13", "Validación cruzada: Dijkstra contra Bellman-Ford desde " + str(len(semilla)) + " orígenes a todos los nodos",
          "0 diferencias", str(comparados) + " pares comparados, " + str(diferencias) + " diferencias", diferencias == 0)

# ---------------------------------------------------------------- PR-14 rendimiento
o = esquina("san lorenzo", "3 de abril", "Corrientes")
d = esquina("peron", "cangallo", "Resistencia")
inicio = time.time()
for i in range(5):
    navegador.dijkstra(grafo, o, d)
promedio = (time.time() - inicio) / 5
registrar("PR-14", "Rendimiento: ruta de Corrientes a Resistencia sobre " + str(len(grafo)) + " nodos",
          "Menos de 2 segundos", str(round(promedio, 3)) + " s por consulta", promedio < 2)

total = len(resultados)
buenas = 0
for c in resultados:
    if resultados[c]["ok"]:
        buenas += 1
print("\nResumen:", buenas, "de", total, "pruebas OK")
json.dump(resultados, open("resultadosPruebas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
sys.exit(0 if buenas == total else 1)
