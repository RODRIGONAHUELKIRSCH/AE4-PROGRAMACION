import json
import math

def distancia(lat1, lon1, lat2, lon2):
    radio = 6371000
    f1 = math.radians(lat1)
    f2 = math.radians(lat2)
    df = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2
    return radio * 2 * math.asin(math.sqrt(a))

def adentro(lon, lat, zona):
    return zona["latMin"] <= lat <= zona["latMax"] and zona["lonMin"] <= lon <= zona["lonMax"]

def tramosDeCalle(coords, zona):
    # corta la calle en pedazos que quedan dentro de la zona
    pedazos = {}
    cantidad = 0
    actual = {}
    largo = 0
    for punto in coords:
        if adentro(punto[0], punto[1], zona):
            largo += 1
            actual[largo] = punto
        else:
            if largo >= 2:
                cantidad += 1
                pedazos[cantidad] = actual
            actual = {}
            largo = 0
    if largo >= 2:
        cantidad += 1
        pedazos[cantidad] = actual
    return pedazos

def quitarTramos(tramos, quitar):
    # Corrección manual de datos: borra tramos puntuales (origen -> destino) que hacen que la ruta
    # de Corrientes a Resistencia se desvíe de la Ruta 16 / Autovía por calles de Barranqueras.
    for origen in quitar:
        for destino in quitar[origen]:
            if origen in tramos and destino in tramos[origen]:
                del tramos[origen][destino]
                print("Tramo quitado:", origen, "->", destino)

def unirCortes(nodos, tramos, maxMetros):
    # En OpenStreetMap a veces una calle termina a pocos metros de la siguiente sin compartir el
    # punto, y el grafo queda cortado (por ejemplo, la Autovía antes de la rotonda).
    # Un nodo sin salida se une al nodo más cercano (dentro de maxMetros) que sí tenga salida,
    # y un nodo sin entrada se une desde el nodo más cercano que sí tenga entrada.
    entradas = {}
    for n in nodos:
        entradas[n] = 0
    for origen in tramos:
        for destino in tramos[origen]:
            entradas[destino] += 1
    celdas = {}
    for n in nodos:
        clave = (round(nodos[n]["lat"] * 2000), round(nodos[n]["lon"] * 2000))
        if clave not in celdas:
            celdas[clave] = {}
        celdas[clave][n] = True

    def masCercano(a, condicion):
        ca = (round(nodos[a]["lat"] * 2000), round(nodos[a]["lon"] * 2000))
        mejor = None
        mejorDist = maxMetros
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for b in celdas.get((ca[0] + dx, ca[1] + dy), {}):
                    if b == a or a in tramos[b] or b in tramos[a] or not condicion(b):
                        continue
                    d = distancia(nodos[a]["lat"], nodos[a]["lon"], nodos[b]["lat"], nodos[b]["lon"])
                    if d < mejorDist:
                        mejorDist = d
                        mejor = b
        return mejor, mejorDist

    agregados = 0
    sinSalida = {}
    sinEntrada = {}
    for a in nodos:
        if len(tramos[a]) == 0:
            sinSalida[a] = True
        if entradas[a] == 0:
            sinEntrada[a] = True
    for a in sinSalida:
        b, d = masCercano(a, lambda x: len(tramos[x]) > 0)
        if b is not None:
            tramos[a][b] = round(d, 1)
            entradas[b] += 1
            agregados += 1
    for a in sinEntrada:
        b, d = masCercano(a, lambda x: entradas[x] > 0)
        if b is not None:
            tramos[b][a] = round(d, 1)
            entradas[a] += 1
            agregados += 1
    print("Cortes unidos:", agregados)

def convertirGeo(archivoEntrada, archivoSalida, zona):
    noAuto = {"footway": True, "path": True, "steps": True, "cycleway": True,
              "pedestrian": True, "track": True, "bridleway": True, "corridor": True}
    with open(archivoEntrada, "r", encoding="utf-8") as f:
        datos = json.load(f)

    # paso 1: juntar los pedazos de calle que sirven para autos
    calles = {}
    cuantas = 0
    veces = {}
    for feature in datos["features"]:
        if feature["geometry"]["type"] != "LineString":
            continue
        props = feature["properties"]
        if props.get("highway") in noAuto:
            continue
        nombre = props.get("name")
        if nombre is None:
            continue
        pedazos = tramosDeCalle(feature["geometry"]["coordinates"], zona)
        for p in pedazos:
            cuantas += 1
            calles[cuantas] = {"nombre": nombre, "mano": props.get("oneway", "no"), "puntos": pedazos[p]}
            for i in pedazos[p]:
                clave = str(pedazos[p][i][1]) + "," + str(pedazos[p][i][0])
                veces[clave] = veces.get(clave, 0) + 1

    # paso 2: quedarse solo con las esquinas (puntos compartidos o extremos)
    nodos = {}
    tramos = {}
    for c in calles:
        puntos = calles[c]["puntos"]
        total = len(puntos)
        mano = calles[c]["mano"]
        anterior = None
        acumulado = 0
        for i in range(1, total + 1):
            lon = puntos[i][0]
            lat = puntos[i][1]
            if i > 1:
                acumulado += distancia(puntos[i - 1][1], puntos[i - 1][0], lat, lon)
            clave = str(lat) + "," + str(lon)
            esEsquina = veces[clave] > 1 or i == 1 or i == total
            if esEsquina:
                if clave not in nodos:
                    nodos[clave] = {"lat": lat, "lon": lon, "calles": {}}
                    tramos[clave] = {}
                nodos[clave]["calles"][calles[c]["nombre"]] = True
                if anterior is not None and anterior != clave:
                    d = round(acumulado, 1)
                    if mano == "-1":
                        tramos[clave][anterior] = d
                    else:
                        tramos[anterior][clave] = d
                        if mano != "yes":
                            tramos[clave][anterior] = d
                anterior = clave
                acumulado = 0

    quitar = {"-27.4430061,-58.8913115": {"-27.4438539,-58.8917828": True}}
    quitarTramos(tramos, quitar)
    unirCortes(nodos, tramos, 10)

    with open(archivoSalida, "w", encoding="utf-8") as f:
        json.dump({"nodos": nodos, "tramos": tramos}, f, ensure_ascii=False)
    print("Grafo generado:", len(nodos), "nodos")

zona = {"latMin": -27.500, "latMax": -27.415, "lonMin": -59.020, "lonMax": -58.790}
convertirGeo("export.geojson", "calles.json", zona)
