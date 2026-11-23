# =============================================================================
# LOGIX-Analyzer  (versión 2.0, revisada)
# AE4 - Ingeniería de Requerimientos I + Matemática Discreta (TIFAS 2026)
# Integrantes: Federico Molina - Rodrigo Nahuel Kirsch
#
# QUÉ HACE
#   Programa de consola que analiza el sistema heredado LOGIX con modelos de
#   Matemática Discreta: digrafos y matrices (adyacencia, alcanzabilidad),
#   sistemas de ecuaciones (Gauss-Jordan), puntos de equilibrio, camino mínimo
#   (Dijkstra), matriz de decisión ponderada, relaciones como matrices
#   (incidencia y trazabilidad), digrafo de procesos y conteo. Los datos se
#   cargan desde archivos JSON o por teclado: no hay datos fijos en el código.
#
# CÓMO SE EJECUTA
#   python logixAnalyzer.py
#   Requiere Python 3.10 o superior (el menú usa match/case).
#   Opcional, solo para la opción 14 (gráficos):  pip install matplotlib networkx
#   Sin esas bibliotecas el programa funciona igual; solo no dibuja gráficos.
#
# TRAZABILIDAD  requerimiento -> modelo matemático -> funciones
#   RF-01 a RF-06  Digrafo y matriz de A        cargarModulosArchivo, cargarModulosTeclado, armarSistema
#   RF-07 a RF-13  Grados, rankings, extremos   calcularGrados, armarFichas, mostrarGrados,
#                                               ordenarBurbuja, ordenarSeleccion
#   RF-14 a RF-16  Cierre transitivo (Warshall) warshall, busquedaBinaria, modulosAfectados
#   RF-17 a RF-19  Diagonal de la matriz A*     modulosEnCiclos, gruposDeCiclos
#   RF-20 a RF-25  Método del pivote, det.      cargarSistemaArchivo, cargarSistemaTeclado,
#                                               determinante, gaussJordan, resolverSistema
#   RF-26 a RF-30  Sistema 2 x 2 entre rectas   cargarCostosArchivo, puntoEquilibrio, mostrarEquilibrios
#   RF-31 a RF-34  Grafo ponderado y Dijkstra   cargarRedArchivo, dijkstra, mostrarCaminoMinimo
#   RF-35 y RF-36  Orden topológico             ordenDeMigracion
#   RF-37 a RF-41 y RF-63  Ficha de un módulo   consultarModulo
#   RF-42 a RF-47  Combinación lineal v = P.w   cargarDecisionArchivo, validarPesos, calcularPuntajes,
#                                               rankingDeAlternativas, pesoDeCambio
#   RF-48 a RF-52  Relaciones como matrices     multiplicarTablas, analizarIncidencia,
#                                               analizarTrazabilidad
#   RF-53 a RF-58 y RF-64  Digrafo de procesos          cargarProcesoArchivo, caminosSimples, mostrarProceso
#   RF-59 a RF-62  Principios de conteo         permutaciones, variaciones, combinaciones
#   (opcional, sin RF)  Gráficos                generarGraficos y las funciones dibujar...
#
# ESTRUCTURAS Y ALGORITMOS
#   Matrices y grafos como diccionarios de diccionarios; fichas como lista de diccionarios;
#   números con Fraction (exactos). Ordenamiento (burbuja, selección) y búsqueda (binaria,
#   secuencial) programados a mano.
#
# CONVENCIONES
#   camelCase sin guiones bajos; una función hace una sola cosa ("mostrar..." imprime,
#   "cargar..." lee datos, el resto calcula). No se usa "if __name__ == ..." (exige guiones
#   bajos): importar este archivo abre el menú.
# =============================================================================

import json
import os
import sys
import time
import tempfile
from fractions import Fraction

# Bibliotecas opcionales para la opción 14 (gráficos). Si no están instaladas,
# la variable hayGraficos queda en False y el resto del programa no se afecta.
try:
    import matplotlib.pyplot as plt
    import networkx as nx
    hayGraficos = True
except ImportError:
    hayGraficos = False

# --- Parámetros del programa (se escriben en minúscula por la convención) -----
maxModulos = 15            # límite de módulos que pide el RF-04
maxIncognitas = 5          # límite de incógnitas que pide el RNF-07
infinito = float("inf")    # "todavía no hay camino" en Dijkstra (más seguro que 999999)
nombreCarpetaGraficos = "graficos"   # carpeta donde se guardan las imágenes PNG

# --- Funciones generales de archivos y de entrada de datos ---

def calcularCarpetaPrograma():
    """Devuelve la carpeta donde está guardado este programa.
    Devuelve: str: ruta de la carpeta del programa; si no se puede saber (modo interactivo), la
      carpeta de trabajo actual.
    """
    if len(sys.argv) == 0 or sys.argv[0] == "":
        return os.getcwd()
    return os.path.dirname(os.path.abspath(sys.argv[0]))


carpetaPrograma = calcularCarpetaPrograma()

def rutaArchivo(nombreArchivo):
    """Resuelve dónde está un archivo de datos.
    Parámetros: nombreArchivo (str): nombre o ruta del archivo.
    Devuelve: str: ruta que se debe abrir (puede no existir; el error lo informa quien lee).
    """
    if os.path.exists(nombreArchivo):
        return nombreArchivo
    return os.path.join(carpetaPrograma, nombreArchivo)

def leerArchivoJson(nombreArchivo):
    """Lee un archivo JSON y devuelve su contenido como diccionario.
    Parámetros: nombreArchivo (str): nombre o ruta del archivo.
    Devuelve: dict | None: contenido del archivo, o None si hubo un error.
    Complejidad: O(tamaño del archivo).
    """
    ruta = rutaArchivo(nombreArchivo)
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except FileNotFoundError:
        print("Error: no se encontró el archivo", nombreArchivo)
        return None
    except json.JSONDecodeError:
        print("Error: el archivo", nombreArchivo, "no tiene formato JSON válido.")
        return None
    except OSError:
        print("Error: no se pudo abrir el archivo", nombreArchivo)
        return None
    if not isinstance(datos, dict):
        print("Error: el archivo", nombreArchivo, "debe contener un objeto JSON { ... }.")
        return None
    return datos

def aFraccion(valor):
    """Convierte un valor leído (número JSON o texto) en un Fraction exacto.
    Parámetros: valor (int | float | str): dato a convertir.
    Devuelve: Fraction | None: el número exacto, o None si no es un número válido (texto cualquiera,
      True/False, nan, infinito).
    """
    if isinstance(valor, bool):
        return None
    try:
        if isinstance(valor, (int, float)):
            return Fraction(str(valor))
        if isinstance(valor, str):
            return Fraction(valor.strip().replace(",", "."))   # acepta coma decimal (0,5)
    except (ValueError, ZeroDivisionError):
        return None
    return None

def pedirEntero(mensaje, minimo, maximo):
    """Pide un entero por teclado y repite la pregunta hasta que sea válido.
    Parámetros: mensaje (str): texto que se muestra al pedir el dato; minimo (int): menor valor
      aceptado; maximo (int): mayor valor aceptado.
    Devuelve: int: el valor ingresado, ya validado.
    """
    valor = None
    while valor is None:
        texto = input(mensaje)
        try:
            numero = int(texto)
            if numero < minimo or numero > maximo:
                print("  Valor fuera de rango. Ingrese de", minimo, "a", maximo)
            else:
                valor = numero
        except ValueError:
            print("  Debe ingresar un número entero.")
    return valor

def pedirNumeros(mensaje, cantidad):
    """Pide una línea con exactamente 'cantidad' números y repite hasta que sea válida.
    Parámetros: mensaje (str): texto que se muestra al pedir el dato; cantidad (int): cuántos
      números se esperan.
    Devuelve: list[Fraction]: los números ingresados, en el mismo orden.
    """
    numeros = None
    while numeros is None:
        partes = input(mensaje).split()
        lista = []
        for parte in partes:
            numero = aFraccion(parte)
            if numero is not None:
                lista.append(numero)
        if len(lista) != len(partes):
            print("  Solo se admiten números (por ejemplo 3, 4.5 o 9/2).")
        elif len(lista) != cantidad:
            print("  Se esperaban", cantidad, "números y se ingresaron", len(lista))
        else:
            numeros = lista
    return numeros

def pedirNombreArchivo(sugerido):
    """Pide el nombre de un archivo; con solo presionar Enter se usa el sugerido.
    Parámetros: sugerido (str): nombre por defecto (el del archivo de datos del caso).
    Devuelve: str: nombre escrito por el usuario, o el sugerido si lo dejó vacío.
    """
    texto = input("Nombre del archivo (Enter = " + sugerido + "): ").strip()
    if texto == "":
        return sugerido
    return texto

def formatearNumero(numero):
    """Devuelve un número como texto legible para mostrar resultados.
    Parámetros: numero (Fraction | int | float): valor a mostrar.
    Devuelve: str: el número como texto.
    """
    if isinstance(numero, float):
        if numero == infinito:
            return "inf"
        numero = Fraction(str(numero))
    numero = Fraction(numero)
    if numero.denominator == 1:
        return str(numero.numerator)
    aproximado = round(float(numero), 4)
    if Fraction(str(aproximado)) == numero:
        return str(aproximado)
    return str(numero.numerator) + "/" + str(numero.denominator) + " ≈ " + str(aproximado)

def textoOperando(numero):
    """Devuelve un número para escribirlo dentro de una operación entre filas.
    Parámetros: numero (Fraction): coeficiente de la operación.
    Devuelve: str: texto del coeficiente.
    """
    if numero.denominator == 1:
        return str(numero.numerator)
    return "(" + str(numero.numerator) + "/" + str(numero.denominator) + ")"

# --- Funciones generales de matrices y tablas ---

def crearMatriz(filas, columnas, valor):
    """Crea una matriz (lista de listas) de 'filas' x 'columnas' con el valor dado.
    Parámetros: filas (int): cantidad de filas; columnas (int): cantidad de columnas. valor: valor
      inicial de todos los elementos.
    Devuelve: list[list]: la matriz creada.
    """
    matriz = []
    for i in range(filas):
        fila = []
        for j in range(columnas):
            fila.append(valor)
        matriz.append(fila)
    return matriz

def copiarMatriz(matriz):
    """Copia una matriz (lista de listas) elemento por elemento.
    Parámetros: matriz (list[list]): matriz original.
    Devuelve: list[list]: copia independiente.
    """
    copia = []
    for fila in matriz:
        nuevaFila = []
        for valor in fila:
            nuevaFila.append(valor)
        copia.append(nuevaFila)
    return copia

def crearTabla(filas, columnas, valor):
    """Crea una tabla como diccionario de diccionarios: tabla[fila][columna] = valor.
    Parámetros: filas (list[str]): nombres de las filas; columnas (list[str]): nombres de las
      columnas. valor: valor inicial de todas las celdas.
    Devuelve: dict: la tabla creada.
    """
    tabla = {}
    for fila in filas:
        tabla[fila] = {}
        for columna in columnas:
            tabla[fila][columna] = valor
    return tabla

def crearMatrizDiccionario(nombres, valor):
    """Crea una matriz cuadrada con nombres: matriz[origen][destino] = valor.
    Parámetros: nombres (list[str]): nombres de filas y de columnas (son los mismos). valor: valor
      inicial.
    Devuelve: dict: matriz cuadrada.
    """
    return crearTabla(nombres, nombres, valor)

def copiarMatrizDiccionario(nombres, matriz):
    """Copia una matriz cuadrada hecha con diccionarios.
    Parámetros: nombres (list[str]): nombres de filas y columnas; matriz (dict): matriz original.
    Devuelve: dict: copia independiente.
    """
    copia = crearMatrizDiccionario(nombres, 0)
    for fila in nombres:
        for columna in nombres:
            copia[fila][columna] = matriz[fila][columna]
    return copia

def mostrarTabla(titulo, filas, columnas, tabla):
    """Muestra una tabla (matriz con nombres) alineada en columnas.
    Parámetros: titulo (str): título que se imprime arriba; filas (list[str]): nombres de las filas,
      en el orden en que se muestran; columnas (list[str]): nombres de las columnas; tabla (dict):
      tabla[fila][columna] con los valores.
    """
    ancho = 5
    for nombre in filas + columnas:
        if len(nombre) + 2 > ancho:
            ancho = len(nombre) + 2
    print()
    print(titulo)
    encabezado = " " * (ancho + 1)
    for columna in columnas:
        encabezado = encabezado + columna.rjust(ancho)
    print(encabezado)
    for fila in filas:
        linea = fila.rjust(ancho) + " "
        for columna in columnas:
            linea = linea + formatearNumero(tabla[fila][columna]).rjust(ancho)
        print(linea)

def mostrarMatriz(titulo, nombres, matriz):
    """Muestra una matriz cuadrada con nombres (llama a mostrarTabla).
    Parámetros: titulo (str): título de la matriz; nombres (list[str]): nombres de filas y columnas;
      matriz (dict): matriz[fila][columna].
    """
    mostrarTabla(titulo, nombres, nombres, matriz)

def multiplicarTablas(filas, medio, columnas, a, b, booleano):
    """Producto de dos tablas (matrices con nombres), también rectangulares. Modelo matemático:
      (A.B)(i,j) = suma sobre k de a(i,k) * b(k,j), donde i recorre 'filas', k recorre 'medio' y j
      recorre 'columnas'. Si 'booleano' es True se calcula el producto booleano (A (.) B): el
      resultado es 1 si existe algún k con a(i,k) = 1 y b(k,j) = 1, y 0 en caso contrario
      (composición de relaciones). Parámetros: filas (list[str]): nombres de las filas de A (y del
      resultado); medio (list[str]): columnas de A = filas de B (índice k de la suma); columnas
      (list[str]): nombres de las columnas de B (y del resultado); a (dict): primera tabla,
      a[fila][k]; b (dict): segunda tabla, b[k][columna]; booleano (bool): True para el producto
      booleano, False para el común. Devuelve: dict: tabla resultado[fila][columna]. Complejidad:
      O(f * m * c) con f, m, c las cantidades de filas, medio y columnas.
    """
    resultado = crearTabla(filas, columnas, 0)
    for i in filas:
        for j in columnas:
            suma = 0
            for k in medio:
                suma = suma + a[i][k] * b[k][j]
            if booleano and suma > 0:
                suma = 1
            resultado[i][j] = suma
    return resultado

def multiplicarMatrices(modulos, a, b):
    """Producto común de dos matrices cuadradas con nombres (A.A cuenta caminos de largo 2).
    Parámetros: modulos (list[str]): nombres de filas y columnas; a (dict): primera matriz; b
      (dict): segunda matriz.
    Devuelve: dict: matriz producto.
    """
    return multiplicarTablas(modulos, modulos, modulos, a, b, False)

def transponerTabla(filas, columnas, tabla):
    """Devuelve la transpuesta de una tabla: resultado[columna][fila] = tabla[fila][columna].
    Parámetros: filas (list[str]): filas de la tabla original; columnas (list[str]): columnas de la
      tabla original; tabla (dict): tabla original.
    Devuelve: dict: tabla transpuesta (sus filas son 'columnas' y sus columnas son 'filas').
    """
    traspuesta = crearTabla(columnas, filas, 0)
    for i in filas:
        for j in columnas:
            traspuesta[j][i] = tabla[i][j]
    return traspuesta

def contarUnos(filas, columnas, tabla):
    """Suma todos los elementos de una tabla de ceros y unos (cuenta los unos).
    Parámetros: filas (list[str]): nombres de las filas; columnas (list[str]): nombres de las
      columnas; tabla (dict): tabla de ceros y unos.
    Devuelve: int: cantidad de unos.
    """
    cantidad = 0
    for i in filas:
        for j in columnas:
            cantidad = cantidad + tabla[i][j]
    return cantidad

# --- Ordenamiento y búsqueda sobre listas de registros (diccionarios) ---

def ordenarBurbuja(registros, clave, descendente):
    """Ordenamiento de burbuja (bubble sort) de una lista de registros.
    Parámetros: registros (list[dict]): lista a ordenar (no se modifica: se trabaja sobre una
      copia); clave (str): campo del diccionario por el que se ordena (por ejemplo 'entrada');
      descendente (bool): True para orden de mayor a menor.
    Devuelve: list[dict]: nueva lista ordenada.
    Complejidad: O(n^2) en el peor caso; O(n) si ya está ordenada. Ejemplo: con grados de entrada
      (2, 1, 4) y descendente=True devuelve (4, 2, 1).
    """
    lista = list(registros)
    cantidad = len(lista)
    huboIntercambio = True
    pasada = 0
    while huboIntercambio and pasada < cantidad - 1:
        huboIntercambio = False
        # Después de cada pasada el último elemento ya está en su lugar definitivo.
        for j in range(cantidad - 1 - pasada):
            if descendente:
                debeIntercambiar = lista[j][clave] < lista[j + 1][clave]
            else:
                debeIntercambiar = lista[j][clave] > lista[j + 1][clave]
            if debeIntercambiar:
                auxiliar = lista[j]
                lista[j] = lista[j + 1]
                lista[j + 1] = auxiliar
                huboIntercambio = True
        pasada = pasada + 1
    return lista

def ordenarSeleccion(registros, clave, descendente):
    """Ordenamiento por selección (selection sort) de una lista de registros.
    Parámetros: registros (list[dict]): lista a ordenar (no se modifica: se trabaja sobre una
      copia); clave (str): campo por el que se ordena; descendente (bool): True para orden de mayor
      a menor.
    Devuelve: list[dict]: nueva lista ordenada.
    Complejidad: O(n^2) comparaciones siempre; O(n) intercambios.
    """
    lista = list(registros)
    cantidad = len(lista)
    for i in range(cantidad - 1):
        posExtremo = i
        for j in range(i + 1, cantidad):
            if descendente:
                esMejor = lista[j][clave] > lista[posExtremo][clave]
            else:
                esMejor = lista[j][clave] < lista[posExtremo][clave]
            if esMejor:
                posExtremo = j
        if posExtremo != i:
            auxiliar = lista[i]
            lista[i] = lista[posExtremo]
            lista[posExtremo] = auxiliar
    return lista

def busquedaSecuencial(registros, clave, valor):
    """Búsqueda secuencial (lineal) de un valor en una lista de registros.
    Parámetros: registros (list[dict]): lista donde buscar; clave (str): campo que se compara.
      valor: valor buscado.
    Devuelve: int: posición (desde 0) del primer registro que coincide, o -1 si no está.
    Complejidad: O(n).
    """
    posicion = 0
    while posicion < len(registros):
        if registros[posicion][clave] == valor:
            return posicion
        posicion = posicion + 1
    return -1

def busquedaBinaria(registros, clave, valor):
    """Búsqueda binaria (dicotómica) de un valor en una lista ORDENADA de menor a mayor.
    Parámetros: registros (list[dict]): lista ordenada de menor a mayor por 'clave'; clave (str):
      campo que se compara. valor: valor buscado.
    Devuelve: int: posición (desde 0) del registro, o -1 si no está.
    Complejidad: O(log n). Ejemplo: en 9 módulos ordenados por código se necesitan a lo sumo 4
      comparaciones.
    """
    bajo = 0
    alto = len(registros) - 1
    while bajo <= alto:
        medio = (bajo + alto) // 2
        if registros[medio][clave] == valor:
            return medio
        elif registros[medio][clave] < valor:
            bajo = medio + 1
        else:
            alto = medio - 1
    return -1

# --- RF-01 a RF-06 - Cargar los módulos y la matriz de adyacencia ---

def armarSistema(modulos, dependencias):
    """Valida los datos y arma el sistema (digrafo) de módulos. Modelo matemático: digrafo G = (V, E)
      con V = módulos y matriz de adyacencia A tal que A[i][j] = 1 si el módulo i depende del módulo
      j (convención de la consigna). Valida: entre 1 y maxModulos módulos; códigos de texto, no
      vacíos y sin repetir; cada dependencia nombra un módulo existente. Parámetros: modulos
      (list[str]): códigos de los módulos, en el orden de la convención; dependencias (dict):
      {módulo: [módulos de los que depende]}. Devuelve: dict | None: {'modulos': lista,
      'adyacencia': matriz} o None (con mensaje) si algún dato no es válido. Complejidad: O(n^2) por
      crear la matriz.
    """
    if not isinstance(modulos, list) or len(modulos) < 1 or len(modulos) > maxModulos:
        print("Error: el sistema debe tener entre 1 y", maxModulos, "módulos.")
        return None
    vistos = {}
    for codigo in modulos:
        if not isinstance(codigo, str) or codigo.strip() == "":
            print("Error: los códigos de módulo deben ser texto no vacío.")
            return None
        if codigo in vistos:
            print("Error: el código", codigo, "está repetido.")
            return None
        vistos[codigo] = True
    if not isinstance(dependencias, dict):
        print("Error: 'dependencias' debe ser un diccionario módulo -> lista de módulos.")
        return None
    adyacencia = crearMatrizDiccionario(modulos, 0)
    for modulo in dependencias:
        if modulo not in adyacencia:
            print("Error: el módulo", modulo, "no está en la lista de módulos.")
            return None
        if not isinstance(dependencias[modulo], list):
            print("Error: las dependencias de", modulo, "deben ser una lista.")
            return None
        for destino in dependencias[modulo]:
            if destino not in adyacencia:
                print("Error: el módulo", modulo, "depende de", destino, "que no existe.")
                return None
            adyacencia[modulo][destino] = 1
    return {"modulos": modulos, "adyacencia": adyacencia}

def cargarModulosArchivo(nombreArchivo):
    """RF-01, RF-03 a RF-06. Carga el sistema de módulos desde un archivo JSON.
    Parámetros: nombreArchivo (str): nombre del archivo JSON.
    Devuelve: dict | None: el sistema (ver armarSistema) o None si hubo un error.
    """
    datos = leerArchivoJson(nombreArchivo)
    if datos is None:
        return None
    if "modulos" not in datos or "dependencias" not in datos:
        print("Error: el archivo debe tener las claves 'modulos' y 'dependencias'.")
        return None
    return armarSistema(datos["modulos"], datos["dependencias"])

def cargarModulosTeclado():
    """RF-02 a RF-05. Pide los módulos y sus dependencias por teclado.
    Devuelve: dict | None: el sistema (ver armarSistema).
    """
    cantidad = pedirEntero("Cantidad de módulos (1 a " + str(maxModulos) + "): ", 1, maxModulos)
    modulos = []
    while len(modulos) < cantidad:
        codigo = input("Código del módulo " + str(len(modulos) + 1) + ": ").strip().upper()
        if codigo == "":
            print("  El código no puede estar vacío.")
        elif codigo in modulos:
            print("  Ese código ya existe.")
        else:
            modulos.append(codigo)
    dependencias = {}
    for modulo in modulos:
        texto = input("¿De qué módulos depende " + modulo + "? (códigos separados por espacio, Enter si ninguno): ")
        dependencias[modulo] = []
        for codigo in texto.upper().split():
            if codigo in modulos:
                dependencias[modulo].append(codigo)
            else:
                print("  El módulo", codigo, "no existe, se ignora.")
    return armarSistema(modulos, dependencias)

# --- RF-07 a RF-13 - Grados de entrada y de salida ---

def calcularGrados(sistema):
    """Calcula los grados de entrada y de salida de cada módulo. Modelo matemático: grado de salida de
      i = suma de la fila i de A (de cuántos módulos depende i: acoplamiento). Grado de entrada de j
      = suma de la columna j de A (cuántos módulos dependen de j: criticidad). La suma de todos los
      grados de entrada es igual a la de salida y a la cantidad de arcos |E|. Parámetros: sistema
      (dict): sistema armado por armarSistema. Devuelve: tuple[dict, dict]: (entrada, salida), cada
      uno {módulo: grado}. Complejidad: O(n^2).
    """
    modulos = sistema["modulos"]
    adyacencia = sistema["adyacencia"]
    entrada = {}
    salida = {}
    for i in modulos:
        sumaFila = 0
        sumaColumna = 0
        for k in modulos:
            sumaFila = sumaFila + adyacencia[i][k]
            sumaColumna = sumaColumna + adyacencia[k][i]
        salida[i] = sumaFila
        entrada[i] = sumaColumna
    return entrada, salida

def armarFichas(sistema, alcance):
    """Arma una ficha (diccionario) por módulo: código, grados y módulos afectados.
    Parámetros: sistema (dict): sistema de módulos; alcance (dict): matriz de alcanzabilidad A* (ver
      warshall).
    Devuelve: list[dict]: una ficha {'modulo', 'entrada', 'salida', 'afectados'} por módulo, en el
      orden de la convención.
    """
    entrada, salida = calcularGrados(sistema)
    fichas = []
    for modulo in sistema["modulos"]:
        ficha = {"modulo": modulo,
                 "entrada": entrada[modulo],
                 "salida": salida[modulo],
                 "afectados": modulosAfectados(sistema, alcance, modulo)}
        fichas.append(ficha)
    return fichas

def codigosEmpatados(ranking, clave):
    """Devuelve los códigos que están primeros en un ranking, contando los empates.
    Parámetros: ranking (list[dict]): fichas ya ordenadas de mayor a menor (o de menor a mayor);
      clave (str): campo del ranking ('entrada' o 'salida').
    Devuelve: list[str]: códigos de los módulos cuyo valor de 'clave' es igual al del primero.
    """
    codigos = []
    posicion = 0
    while posicion < len(ranking) and ranking[posicion][clave] == ranking[0][clave]:
        codigos.append(ranking[posicion]["modulo"])
        posicion = posicion + 1
    return codigos

def mostrarGrados(sistema, alcance):
    """RF-07 a RF-13. Muestra los grados de cada módulo y dos rankings.
    Parámetros: sistema (dict): sistema de módulos; alcance (dict): matriz de alcanzabilidad A*.
    """
    fichas = armarFichas(sistema, alcance)
    print()
    print("Grados de cada módulo (RF-07 a RF-13)")
    for ficha in fichas:
        print(" ", ficha["modulo"], "-> entrada:", ficha["entrada"], " salida:", ficha["salida"])
    rankingCriticos = ordenarBurbuja(fichas, "entrada", True)
    rankingAcoplados = ordenarSeleccion(fichas, "salida", True)
    print("Ranking de criticidad (grado de entrada, burbuja):", " ".join(f["modulo"] + "(" + str(f["entrada"]) + ")" for f in rankingCriticos), "")
    print("Ranking de acoplamiento (grado de salida, selección):", " ".join(f["modulo"] + "(" + str(f["salida"]) + ")" for f in rankingAcoplados), "")
    print("Más crítico (mayor grado de entrada):", codigosEmpatados(rankingCriticos, "entrada"))
    print("Más acoplado (mayor grado de salida):", codigosEmpatados(rankingAcoplados, "salida"))
    rankingMenores = ordenarBurbuja(fichas, "entrada", False)
    print("Se pueden eliminar sin afectar a otro (grado de entrada 0):", end=" ")
    if rankingMenores[0]["entrada"] == 0:
        print(codigosEmpatados(rankingMenores, "entrada"))
    else:
        print("ninguno")

# --- RF-14 a RF-16 - Matriz de alcanzabilidad (Warshall) y módulos afectados ---

def warshall(sistema):
    """Calcula la matriz de alcanzabilidad A* (cierre transitivo) con el algoritmo de Warshall. Modelo
      matemático: A*[i][j] = 1 si existe un camino de longitud >= 1 de i a j. En la etapa k se
      considera a k como intermediario permitido: si i llega a k y k llega a j, entonces i llega a
      j. Al terminar la etapa k se conocen todos los caminos cuyos intermedios están entre los
      primeros k módulos; al terminar la última, todos los caminos. Equivale a la suma booleana A v
      A^2 v ... v A^n. Optimización: si i no llega a k se omite el recorrido de j (no puede
      aportar). Parámetros: sistema (dict): sistema de módulos. Devuelve: dict: matriz A*
      (diccionario de diccionarios de 0 y 1). La diagonal vale 1 exactamente en los módulos que
      están en un ciclo. Complejidad: O(n^3) en el peor caso.
    """
    modulos = sistema["modulos"]
    alcance = copiarMatrizDiccionario(modulos, sistema["adyacencia"])
    for k in modulos:
        for i in modulos:
            if alcance[i][k] == 1:
                for j in modulos:
                    if alcance[k][j] == 1:
                        alcance[i][j] = 1
    return alcance

def modulosAfectados(sistema, alcance, codigo):
    """Lectura por columna de A*: módulos que pueden verse afectados si se modifica 'codigo'. Modelo
      matemático: A*[i][j] = 1 significa que i depende (directa o indirectamente) de j; por lo tanto
      un cambio en j puede afectar a todo i con A*[i][j] = 1. Es la columna j de A*. Parámetros:
      sistema (dict): sistema de módulos; alcance (dict): matriz A*; codigo (str): módulo que se
      modifica. Devuelve: list[str]: módulos afectados, en el orden de la convención.
    """
    afectados = []
    for i in sistema["modulos"]:
        if alcance[i][codigo] == 1:
            afectados.append(i)
    return afectados

def mostrarAfectados(sistema, alcance):
    """RF-14 a RF-16. Pide uno o más módulos y muestra el alcance directo y el impacto según A*.
    Parámetros: sistema (dict): sistema de módulos; alcance (dict): matriz A*.
    """
    fichasOrdenadas = ordenarSeleccion(armarFichas(sistema, alcance), "modulo", False)
    texto = input("Módulos que se modifican (separados por espacio): ").upper()
    cambiados = {}
    afectados = {}
    for codigo in texto.split():
        posicion = busquedaBinaria(fichasOrdenadas, "modulo", codigo)
        if posicion == -1:
            print("  El módulo", codigo, "no existe, se ignora.")
        else:
            cambiados[codigo] = True
            for modulo in fichasOrdenadas[posicion]["afectados"]:
                afectados[modulo] = True
    lista = []
    for modulo in sistema["modulos"]:
        if modulo in afectados:
            lista.append(modulo)
    print("Alcance directo:", len(cambiados), "módulo(s)")
    print("Impacto según A*:", len(lista), "módulo(s):", lista)

# --- RF-17 a RF-19 - Dependencias circulares ---

def modulosEnCiclos(sistema, alcance):
    """RF-17 a RF-19. Devuelve los módulos que están en un ciclo (diagonal de A* igual a 1). Modelo
      matemático: A*[i][i] = 1 si y solo si hay un camino que sale de i y vuelve a i, es decir, i
      está en un ciclo (dependencia circular). Parámetros: sistema (dict): sistema de módulos;
      alcance (dict): matriz A*. Devuelve: list[str]: módulos con A*[i][i] = 1, en el orden de la
      convención.
    """
    enCiclo = []
    for i in sistema["modulos"]:
        if alcance[i][i] == 1:
            enCiclo.append(i)
    return enCiclo

def gruposDeCiclos(sistema, alcance):
    """Agrupa los módulos que están en el mismo ciclo (componentes fuertemente conexas). Modelo
      matemático: i y j están en la misma componente fuertemente conexa si A*[i][j] = 1 y A*[j][i] =
      1 (se alcanzan mutuamente). 'Se alcanzan mutuamente' es una relación de equivalencia y sus
      clases son las componentes. Solo se informan las que contienen un ciclo (diagonal en 1).
      Parámetros: sistema (dict): sistema de módulos; alcance (dict): matriz A*. Devuelve:
      list[list[str]]: un grupo (lista de códigos) por cada ciclo independiente.
    """
    modulos = sistema["modulos"]
    grupos = []
    yaAgrupado = {}
    for i in modulos:
        if alcance[i][i] == 1 and i not in yaAgrupado:
            grupo = []
            for j in modulos:
                if alcance[i][j] == 1 and alcance[j][i] == 1:
                    grupo.append(j)
                    yaAgrupado[j] = True
            grupos.append(grupo)
    return grupos

# --- RF-35 y RF-36 - Orden de migración (orden topológico) ---

def ordenDeMigracion(sistema):
    """RF-35 y RF-36. Propone un orden de migración: cada módulo después de los que necesita. Modelo
      matemático: orden topológico inverso del digrafo. Como A[i][j] = 1 significa 'i depende de j',
      j debe migrarse antes que i. Algoritmo: se lleva la cuenta de dependencias pendientes de cada
      módulo (su grado de salida); se migra uno con 0 pendientes y se descuenta una a quienes
      dependían de él. Si en algún momento no hay ninguno con 0 pendientes, todos los que quedan
      esperan a otro que queda: hay un ciclo y el orden no existe. Parámetros: sistema (dict):
      sistema de módulos. Devuelve: list[str]: orden de migración; lista vacía si el grafo tiene
      ciclos. Complejidad: O(n^2).
    """
    modulos = sistema["modulos"]
    adyacencia = sistema["adyacencia"]
    entrada, salida = calcularGrados(sistema)
    pendientes = {}      # cuántas dependencias sin migrar tiene cada módulo
    migrado = {}
    for modulo in modulos:
        pendientes[modulo] = salida[modulo]
        migrado[modulo] = False
    orden = []
    while len(orden) < len(modulos):
        elegido = None
        for modulo in modulos:
            if elegido is None and not migrado[modulo] and pendientes[modulo] == 0:
                elegido = modulo
        if elegido is None:
            return []        # hay un ciclo: no existe orden de migración
        migrado[elegido] = True
        orden.append(elegido)
        for modulo in modulos:   # los que dependían del elegido tienen una pendiente menos
            if adyacencia[modulo][elegido] == 1:
                pendientes[modulo] = pendientes[modulo] - 1
    return orden

# --- Análisis completo y consulta de un módulo ---

def densidadDeAlcance(sistema, alcance):
    """Indicador de acoplamiento normalizado: porcentaje de unos de A* sobre n^2.
    Parámetros: sistema (dict): sistema de módulos; alcance (dict): matriz A*.
    Devuelve: float: porcentaje (0 a 100) redondeado a un decimal.
    """
    modulos = sistema["modulos"]
    unos = contarUnos(modulos, modulos, alcance)
    return round(100 * unos / (len(modulos) * len(modulos)), 1)

def analizarSistema(sistema):
    """Corre RF-07 a RF-19, RF-35 y RF-36 sobre el digrafo cargado y muestra los resultados.
    Parámetros: sistema (dict): sistema de módulos.
    """
    modulos = sistema["modulos"]
    mostrarMatriz("Matriz de adyacencia A", modulos, sistema["adyacencia"])
    alcance = warshall(sistema)
    mostrarGrados(sistema, alcance)
    mostrarMatriz("A^2 (dependencias indirectas de longitud 2)", modulos,
                  multiplicarMatrices(modulos, sistema["adyacencia"], sistema["adyacencia"]))
    mostrarMatriz("Matriz de alcanzabilidad A* (Warshall)", modulos, alcance)
    print()
    print("Si se modifica cada módulo, pueden verse afectados (lectura por columna):")
    for codigo in modulos:
        print(" ", codigo, "->", modulosAfectados(sistema, alcance, codigo))
    print("Pares alcanzables (unos de A*):", contarUnos(modulos, modulos, alcance),
          "- densidad:", densidadDeAlcance(sistema, alcance), "% de", len(modulos) * len(modulos))
    ciclos = modulosEnCiclos(sistema, alcance)
    if len(ciclos) == 0:
        print("No hay dependencias circulares (el grafo es acíclico).")
        print("Orden de migración (RF-35 y RF-36):", ordenDeMigracion(sistema))
    else:
        print("Módulos en dependencias circulares (RF-17 a RF-19):", ciclos)
        print("Grupos de módulos en el mismo ciclo:", gruposDeCiclos(sistema, alcance))
        print("Orden de migración: no existe porque hay ciclos.")

def consultarModulo(sistema):
    """RF-37 a RF-41 y RF-63. Muestra la ficha de un módulo que elige el usuario.
    Parámetros: sistema (dict): sistema de módulos.
    """
    alcance = warshall(sistema)
    fichas = armarFichas(sistema, alcance)
    fichasOrdenadas = ordenarSeleccion(fichas, "modulo", False)
    codigo = input("Código del módulo a consultar: ").strip().upper()
    posicion = busquedaBinaria(fichasOrdenadas, "modulo", codigo)
    if posicion == -1:
        print("El módulo", codigo, "no existe en el sistema cargado.")
        return
    ficha = fichasOrdenadas[posicion]
    rankingCriticos = ordenarBurbuja(fichas, "entrada", True)
    rankingAcoplados = ordenarSeleccion(fichas, "salida", True)
    puestoCritico = busquedaSecuencial(rankingCriticos, "modulo", codigo) + 1
    puestoAcoplado = busquedaSecuencial(rankingAcoplados, "modulo", codigo) + 1
    print("Módulo", codigo)
    print("  Grado de entrada:", ficha["entrada"], "(puesto", puestoCritico, "de", len(fichas), "en criticidad)")
    print("  Grado de salida :", ficha["salida"], "(puesto", puestoAcoplado, "de", len(fichas), "en acoplamiento)")
    print("  Si se modifica pueden verse afectados:", ficha["afectados"])
    if alcance[codigo][codigo] == 1:
        print("  Está en una dependencia circular.")
    else:
        print("  No está en ninguna dependencia circular.")

# --- RF-20 a RF-25 - Sistemas de ecuaciones lineales (hasta 5 x 5), aritmética exacta ---

def cargarSistemaArchivo(nombreArchivo):
    """RF-20. Carga un sistema de ecuaciones desde un archivo JSON.
    Parámetros: nombreArchivo (str): nombre del archivo JSON.
    Devuelve: list[list[Fraction]] | None: matriz ampliada (M | B) de n filas y n + 1 columnas, o
      None si hubo un error.
    """
    datos = leerArchivoJson(nombreArchivo)
    if datos is None:
        return None
    if "paquetes" not in datos or not isinstance(datos["paquetes"], list):
        print("Error: el archivo debe tener la clave 'paquetes' con una lista de ecuaciones.")
        return None
    cantidad = len(datos["paquetes"])
    if cantidad < 1 or cantidad > maxIncognitas:
        print("Error: el sistema debe tener entre 1 y", maxIncognitas, "ecuaciones.")
        return None
    ampliada = []
    for paquete in datos["paquetes"]:
        if not isinstance(paquete, dict) or "coeficientes" not in paquete or "precio" not in paquete \
                or not isinstance(paquete["coeficientes"], list):
            print("Error: cada ecuación debe tener 'coeficientes' (lista) y 'precio'.")
            return None
        fila = []
        for coeficiente in paquete["coeficientes"] + [paquete["precio"]]:
            numero = aFraccion(coeficiente)
            if numero is None:
                print("Error: el valor", coeficiente, "no es un número.")
                return None
            fila.append(numero)
        if len(fila) != cantidad + 1:
            print("Error: cada ecuación debe tener", cantidad, "coeficientes y un término independiente.")
            return None
        ampliada.append(fila)
    return ampliada

def cargarSistemaTeclado():
    """RF-21. Pide la cantidad de incógnitas y cada ecuación en una línea.
    Devuelve: list[list[Fraction]]: matriz ampliada (M | B).
    """
    cantidad = pedirEntero("Cantidad de incógnitas (1 a " + str(maxIncognitas) + "): ", 1, maxIncognitas)
    ampliada = []
    for i in range(cantidad):
        ampliada.append(pedirNumeros("Ecuación " + str(i + 1) + " (" + str(cantidad)
                                     + " coeficientes y el término independiente): ", cantidad + 1))
    return ampliada

def determinante(ampliada):
    """Calcula det(M), donde M es la matriz ampliada sin su última columna. Modelo matemático: se
      triangula una copia de M con operaciones entre filas. Sumar a una fila un múltiplo de otra no
      cambia el determinante; intercambiar dos filas lo multiplica por -1; el determinante de una
      matriz triangular es el producto de su diagonal. Con Fraction el resultado es exacto: det = 0
      solo si realmente es cero (no hace falta ninguna tolerancia). Parámetros: ampliada
      (list[list[Fraction]]): matriz ampliada (M | B). Devuelve: Fraction: determinante de M.
      Complejidad: O(n^3).
    """
    n = len(ampliada)
    m = crearMatriz(n, n, Fraction(0))
    for i in range(n):
        for j in range(n):
            m[i][j] = ampliada[i][j]
    det = Fraction(1)
    for c in range(n):
        filaPivote = -1
        for f in range(c, n):
            if filaPivote == -1 and m[f][c] != 0:
                filaPivote = f
        if filaPivote == -1:
            return Fraction(0)
        if filaPivote != c:
            m[c], m[filaPivote] = m[filaPivote], m[c]
            det = -det
        det = det * m[c][c]
        for f in range(c + 1, n):
            factor = m[f][c] / m[c][c]
            for k in range(n):
                m[f][k] = m[f][k] - factor * m[c][k]
    return det

def elegirPivote(m, fila, columna):
    """Elige la fila del pivote para una columna, mirando de 'fila' hacia abajo.
    Parámetros: m (list[list[Fraction]]): matriz de trabajo; fila (int): primera fila candidata (las
      anteriores ya tienen su pivote); columna (int): columna que se está reduciendo.
    Devuelve: int: índice de la fila elegida, o -1 si toda la columna es cero desde 'fila'.
    """
    n = len(m)
    primero = -1
    conUno = -1
    for f in range(fila, n):
        if m[f][columna] != 0:
            if primero == -1:
                primero = f
            if conUno == -1 and abs(m[f][columna]) == 1:
                conUno = f
    if conUno != -1:
        return conUno
    return primero

def gaussJordan(ampliada, mostrarPasos):
    """Método del pivote (Gauss-Jordan) con aritmética exacta. Modelo matemático: para cada columna c
      se elige un pivote, se lleva a 1 dividiendo su fila y se hacen ceros en el resto de la columna
      (arriba y abajo). Las operaciones elementales no cambian el conjunto de soluciones. Al final
      la matriz queda en forma escalonada reducida. Se clasifica con el teorema de Rouché-Frobenius
      comparando rg(M) y rg(M|B) (filas no nulas): - rg(M) < rg(M|B) -> incompatible (sin solución)
      - rg(M) = rg(M|B) < n -> compatible indeterminado (infinitas soluciones) - rg(M) = rg(M|B) = n
      -> compatible determinado (solución única) Parámetros: ampliada (list[list[Fraction]]): matriz
      ampliada (M | B); no se modifica; mostrarPasos (bool): True para imprimir cada operación entre
      filas. Devuelve: tuple[str, list[Fraction]]: (clasificación, solución). La solución es la
      lista (x1, ..., xn) si es compatible determinado; vacía en otro caso. Complejidad: O(n^3).
    """
    n = len(ampliada)
    m = copiarMatriz(ampliada)
    fila = 0
    for c in range(n):
        filaPivote = elegirPivote(m, fila, c)
        if filaPivote != -1:
            if filaPivote != fila:
                m[fila], m[filaPivote] = m[filaPivote], m[fila]
                if mostrarPasos:
                    print("  F" + str(fila + 1), "<-> F" + str(filaPivote + 1))
            pivote = m[fila][c]
            if pivote != 1:
                for k in range(n + 1):
                    m[fila][k] = m[fila][k] / pivote
                if mostrarPasos:
                    if pivote == -1:
                        print("  F" + str(fila + 1), "<- -F" + str(fila + 1))
                    else:
                        print("  F" + str(fila + 1), "<- F" + str(fila + 1), "/", textoOperando(pivote))
            for f in range(n):
                if f != fila and m[f][c] != 0:
                    factor = m[f][c]
                    for k in range(n + 1):
                        m[f][k] = m[f][k] - factor * m[fila][k]
                    if mostrarPasos:
                        signo = "-" if factor > 0 else "+"
                        producto = "F" + str(fila + 1) if abs(factor) == 1 else textoOperando(abs(factor)) + " * F" + str(fila + 1)
                        print("  F" + str(f + 1), "<- F" + str(f + 1), signo, producto)
            fila = fila + 1
    # Clasificación: se cuentan las filas no nulas de M (rango de M) y de (M | B).
    rangoM = 0
    rangoAmpliada = 0
    for f in range(n):
        if any(m[f][k] != 0 for k in range(n)):
            rangoM = rangoM + 1
            rangoAmpliada = rangoAmpliada + 1
        elif m[f][n] != 0:
            rangoAmpliada = rangoAmpliada + 1
    if rangoM < rangoAmpliada:
        return "incompatible", []
    if rangoM < n:
        return "compatible indeterminado", []
    return "compatible determinado", [m[f][n] for f in range(n)]

def resolverSistema(ampliada):
    """RF-22 a RF-25. Muestra determinante, pasos del pivote, clasificación y verificación.
    Parámetros: ampliada (list[list[Fraction]]): matriz ampliada (M | B).
    """
    print("det(M) =", formatearNumero(determinante(ampliada)))
    clasificacion, solucion = gaussJordan(ampliada, True)
    print("El sistema es", clasificacion)
    if clasificacion == "compatible determinado":
        for i in range(len(solucion)):
            print("  Incógnita", i + 1, "=", formatearNumero(solucion[i]))
        for f in range(len(ampliada)):     # verificación por sustitución
            suma = 0
            for k in range(len(solucion)):
                suma = suma + ampliada[f][k] * solucion[k]
            print("  Verificación ecuación", f + 1, ":", formatearNumero(suma), "=",
                  formatearNumero(ampliada[f][len(solucion)]))
        texto = input("¿Calcular un costo con estos valores? Ingrese las cantidades (Enter para no): ")
        if texto != "":
            cantidades = []
            for parte in texto.split():
                numero = aFraccion(parte)
                if numero is not None:
                    cantidades.append(numero)
            if len(cantidades) != len(solucion) or len(cantidades) != len(texto.split()):
                print("Se esperaban", len(solucion), "cantidades numéricas.")
            else:
                total = 0
                for i in range(len(solucion)):
                    total = total + cantidades[i] * solucion[i]
                print("Costo = vector de cantidades · vector solución =", formatearNumero(total))

# --- RF-26 a RF-30 - Punto de equilibrio entre dos alternativas de costo lineal ---

def cargarCostosArchivo(nombreArchivo):
    """RF-26. Carga las alternativas de costo desde un archivo JSON.
    Parámetros: nombreArchivo (str): nombre del archivo JSON.
    Devuelve: dict | None: {nombre: {'fijo': Fraction, 'anual': Fraction}} o None si hay error.
    """
    datos = leerArchivoJson(nombreArchivo)
    if datos is None:
        return None
    if "alternativas" not in datos or not isinstance(datos["alternativas"], dict):
        print("Error: el archivo debe tener la clave 'alternativas' con un diccionario.")
        return None
    alternativas = {}
    for nombre in datos["alternativas"]:
        datosAlt = datos["alternativas"][nombre]
        if not isinstance(datosAlt, dict) or "fijo" not in datosAlt or "anual" not in datosAlt:
            print("Error: la alternativa", nombre, "debe tener 'fijo' y 'anual'.")
            return None
        fijo = aFraccion(datosAlt["fijo"])
        anual = aFraccion(datosAlt["anual"])
        if fijo is None or anual is None:
            print("Error: los costos de la alternativa", nombre, "deben ser números.")
            return None
        alternativas[nombre] = {"fijo": fijo, "anual": anual}
    if len(alternativas) < 1:
        print("Error: no hay alternativas en el archivo.")
        return None
    return alternativas

def cargarCostosTeclado():
    """RF-27. Pide nombre, costo fijo y costo anual de cada alternativa.
    Devuelve: dict: {nombre: {'fijo': Fraction, 'anual': Fraction}}.
    """
    cantidad = pedirEntero("Cantidad de alternativas (2 a 10): ", 2, 10)
    alternativas = {}
    while len(alternativas) < cantidad:
        nombre = input("Nombre de la alternativa " + str(len(alternativas) + 1) + ": ").strip().upper()
        if nombre == "" or nombre in alternativas:
            print("  El nombre está vacío o ya existe.")
        else:
            datos = pedirNumeros("  Costo fijo y costo anual de " + nombre + " (dos números): ", 2)
            alternativas[nombre] = {"fijo": datos[0], "anual": datos[1]}
    return alternativas

def puntoEquilibrio(alternativa1, alternativa2):
    """RF-28 a RF-30. Calcula en qué año se igualan los costos acumulados de dos alternativas. Modelo
      matemático: cada alternativa es una recta C = fijo + anual * n. Se plantea el sistema 2 x 2 en
      las incógnitas (n, C): anual1 * n - C = -fijo1 anual2 * n - C = -fijo2 y se resuelve con
      gaussJordan. Si los costos anuales son iguales las rectas son paralelas (o coincidentes) y no
      hay un único punto de equilibrio. Parámetros: alternativa1 (dict): {'fijo', 'anual'} de la
      primera alternativa; alternativa2 (dict): {'fijo', 'anual'} de la segunda alternativa.
      Devuelve: tuple[str, list[Fraction]]: (clasificación, [n, C]); la lista está vacía si no hay
      solución única.
    """
    ampliada = [[alternativa1["anual"], Fraction(-1), -alternativa1["fijo"]],
                [alternativa2["anual"], Fraction(-1), -alternativa2["fijo"]]]
    return gaussJordan(ampliada, False)

def compararEnAnio(alternativas, anio):
    """Calcula el costo acumulado de cada alternativa en un año y las ordena.
    Parámetros: alternativas (dict): {nombre: {'fijo', 'anual'}}; anio (Fraction | int): año de
      operación n.
    Devuelve: list[dict]: registros {'nombre', 'costo'} ordenados de menor a mayor costo
      (selección); el primero es la alternativa más económica en ese año.
    """
    registros = []
    for nombre in alternativas:
        costo = alternativas[nombre]["fijo"] + alternativas[nombre]["anual"] * anio
        registros.append({"nombre": nombre, "costo": costo})
    return ordenarSeleccion(registros, "costo", False)

def mostrarEquilibrios(alternativas):
    """RF-28 a RF-30. Muestra el equilibrio de cada par de alternativas y compara en años elegidos.
    Parámetros: alternativas (dict): {nombre: {'fijo', 'anual'}}.
    """
    nombres = list(alternativas.keys())
    for i in range(len(nombres)):
        for j in range(i + 1, len(nombres)):
            a = nombres[i]
            b = nombres[j]
            clasificacion, solucion = puntoEquilibrio(alternativas[a], alternativas[b])
            if clasificacion == "compatible determinado":
                print(" ", a, "y", b, "-> n =", formatearNumero(solucion[0]), "años, costo =", formatearNumero(solucion[1]))
                if solucion[0] < 0:
                    print("     (año negativo: no hay equilibrio en el futuro)")
            else:
                print(" ", a, "y", b, "-> no hay punto de equilibrio único (" + clasificacion + ")")
    texto = input("¿Comparar en algún año? Ingrese los años separados por espacio (Enter para no): ")
    for anio in texto.split():
        n = aFraccion(anio)
        if n is None or n < 0:
            print("  Año inválido:", anio)
            continue
        ranking = compararEnAnio(alternativas, n)
        print("  Año", anio, end=": ")
        for registro in ranking:
            print(registro["nombre"], "=", formatearNumero(registro["costo"]), end="  ")
        print("-> más económica:", ranking[0]["nombre"])

# --- RF-31 a RF-34 - Camino mínimo (Dijkstra) ---

def cargarRedArchivo(nombreArchivo):
    """RF-31. Carga la red de distribución (grafo ponderado no dirigido).
    Parámetros: nombreArchivo (str): nombre del archivo JSON.
    Devuelve: dict | None: grafo[nodo][vecino] = minutos (Fraction), o None si hay error.
    """
    datos = leerArchivoJson(nombreArchivo)
    if datos is None:
        return None
    if "aristas" not in datos or not isinstance(datos["aristas"], list):
        print("Error: el archivo debe tener la clave 'aristas' con una lista.")
        return None
    grafo = {}
    for arista in datos["aristas"]:
        if not isinstance(arista, dict) or "desde" not in arista or "hasta" not in arista or "minutos" not in arista:
            print("Error: cada arista debe tener 'desde', 'hasta' y 'minutos'.")
            return None
        desde = arista["desde"]
        hasta = arista["hasta"]
        peso = aFraccion(arista["minutos"])
        if not isinstance(desde, str) or not isinstance(hasta, str) or peso is None:
            print("Error: arista inválida (nodos de texto y 'minutos' numérico):", desde, "-", hasta)
            return None
        if peso < 0:
            print("Error: Dijkstra no admite pesos negativos (arista", desde, "-", hasta + ").")
            return None
        if desde not in grafo:
            grafo[desde] = {}
        if hasta not in grafo:
            grafo[hasta] = {}
        grafo[desde][hasta] = peso
        grafo[hasta][desde] = peso
    return grafo

def mostrarMatrizPesos(grafo):
    """Muestra la matriz de pesos W del grafo ('inf' donde no hay arista directa).
    Parámetros: grafo (dict): grafo[nodo][vecino] = minutos.
    """
    nodos = list(grafo.keys())
    ancho = 5
    for nodo in nodos:
        if len(nodo) + 2 > ancho:
            ancho = len(nodo) + 2
    print()
    print("Matriz de pesos W (minutos)")
    encabezado = " " * (ancho + 1)
    for nodo in nodos:
        encabezado = encabezado + nodo.rjust(ancho)
    print(encabezado)
    for u in nodos:
        linea = u.rjust(ancho) + " "
        for v in nodos:
            if u == v:
                linea = linea + "0".rjust(ancho)
            elif v in grafo[u]:
                linea = linea + formatearNumero(grafo[u][v]).rjust(ancho)
            else:
                linea = linea + "inf".rjust(ancho)
        print(linea)

def buscarMinimoNoFijado(distancia, fijado):
    """Busca el vértice no fijado de menor distancia (en empates, el primero).
    Parámetros: distancia (dict): distancia provisoria desde el origen a cada vértice; fijado
      (dict): {vértice: True si su distancia ya es definitiva}.
    Devuelve: str | None: el vértice elegido, o None si ya están todos fijados.
    Complejidad: O(n). Dijkstra la llama n veces, de ahí su costo total O(n^2).
    """
    elegido = None
    for nodo in distancia:
        if not fijado[nodo]:
            if elegido is None or distancia[nodo] < distancia[elegido]:
                elegido = nodo
    return elegido

def dijkstra(grafo, origen, destino, mostrarEtapas):
    """RF-32 a RF-34. Camino mínimo de 'origen' a 'destino' con el algoritmo de Dijkstra. Modelo
      matemático: grafo ponderado con pesos no negativos. En cada etapa se FIJA el vértice no fijado
      de menor distancia provisoria (como los pesos no son negativos, ningún otro camino puede
      mejorarla) y se ACTUALIZA la distancia de sus vecinos si pasar por él es más corto. Se guarda
      el predecesor de cada vértice para reconstruir el camino desde el destino hacia atrás.
      Parámetros: grafo (dict): grafo[nodo][vecino] = minutos; origen (str): vértice de partida;
      destino (str): vértice de llegada; mostrarEtapas (bool): True para imprimir cada etapa (útil
      para comparar con la tabla de etapas hecha a mano). Devuelve: tuple: (distancia, camino). Si
      no hay camino devuelve (infinito, []). Complejidad: O(n^2) (búsqueda lineal del mínimo en cada
      etapa).
    """
    if origen not in grafo or destino not in grafo:
        return infinito, []
    distancia = {}
    anterior = {}
    fijado = {}
    for nodo in grafo:
        distancia[nodo] = infinito
        anterior[nodo] = None
        fijado[nodo] = False
    distancia[origen] = 0
    etapa = 1
    u = buscarMinimoNoFijado(distancia, fijado)
    while u is not None and distancia[u] != infinito:
        fijado[u] = True
        if mostrarEtapas:
            print("  Etapa", etapa, ": se fija", u, "con distancia", formatearNumero(distancia[u]))
        for v in grafo[u]:
            if not fijado[v] and distancia[u] + grafo[u][v] < distancia[v]:
                distancia[v] = distancia[u] + grafo[u][v]
                anterior[v] = u
                if mostrarEtapas:
                    print("     se actualiza", v, "a", formatearNumero(distancia[v]), "(viniendo de", u + ")")
        etapa = etapa + 1
        u = buscarMinimoNoFijado(distancia, fijado)
    if distancia[destino] == infinito:
        return infinito, []
    camino = []                       # se reconstruye desde el destino hacia atrás
    actual = destino
    while actual is not None:
        camino.insert(0, actual)
        actual = anterior[actual]
    return distancia[destino], camino

def longitudDeRuta(grafo, ruta):
    """Suma los minutos de una ruta fija dada como lista de vértices.
    Parámetros: grafo (dict): grafo[nodo][vecino] = minutos; ruta (list[str]): vértices en orden,
      por ejemplo ['D', 'H1', 'Z1', 'Z3'].
    Devuelve: Fraction | int | None: total de minutos, o None si algún tramo no existe en la red.
    """
    total = 0
    for i in range(len(ruta) - 1):
        if ruta[i] not in grafo or ruta[i + 1] not in grafo[ruta[i]]:
            return None
        total = total + grafo[ruta[i]][ruta[i + 1]]
    return total

def mostrarCaminoMinimo():
    """RF-32 a RF-34. Carga la red, pide origen y destino y muestra W, las etapas y el camino mínimo."""
    grafo = cargarRedArchivo(pedirNombreArchivo("redDistribucion.json"))
    if grafo is None:
        return
    origen = input("Vértice de origen: ").strip().upper()
    destino = input("Vértice de destino: ").strip().upper()
    if origen not in grafo or destino not in grafo:
        print("Alguno de los vértices no existe en la red.")
        return
    mostrarMatrizPesos(grafo)
    print()
    minimo, camino = dijkstra(grafo, origen, destino, True)
    if len(camino) == 0:
        print("No hay camino entre", origen, "y", destino)
        return
    print("Camino mínimo:", " - ".join(camino), "=", formatearNumero(minimo))
    texto = input("Ruta fija para comparar (vértices separados por espacio, Enter para omitir): ").upper()
    if texto != "":
        largo = longitudDeRuta(grafo, texto.split())
        if largo is None:
            print("La ruta fija no es válida: algún tramo no existe en la red.")
        else:
            print("Ruta fija:", " - ".join(texto.split()), "=", formatearNumero(largo))
            print("Ahorro del camino mínimo:", formatearNumero(largo - minimo), "minutos")

# --- RF-42 a RF-47 - Matriz de decisión ponderada (combinación lineal v = P.w) ---

def textoPorcentaje(numero):
    """Devuelve una fracción 0..1 como porcentaje con un decimal (por ejemplo '55.9 %').
    Parámetros: numero (Fraction): valor entre 0 y 1.
    Devuelve: str: porcentaje como texto.
    """
    return str(round(float(100 * numero), 1)) + " %"

def validarPesos(criterios, pesos, etiqueta):
    """Convierte y valida un vector de pesos w = (w1, ..., wk).
    Parámetros: criterios (list[str]): códigos de los criterios; pesos (dict): {criterio: peso} tal
      como se leyó del archivo; etiqueta (str): nombre del vector para los mensajes de error.
    Devuelve: dict | None: {criterio: Fraction} o None (con mensaje) si no es válido.
    """
    if not isinstance(pesos, dict):
        print("Error:", etiqueta, "debe ser un diccionario criterio -> peso.")
        return None
    resultado = {}
    suma = Fraction(0)
    for criterio in criterios:
        peso = aFraccion(pesos.get(criterio))
        if peso is None or peso < 0:
            print("Error: en", etiqueta, "falta el peso de", criterio, "o no es un número no negativo.")
            return None
        resultado[criterio] = peso
        suma = suma + peso
    if suma != 1:
        print("Error: los pesos de", etiqueta, "deben sumar 1 y suman", formatearNumero(suma))
        return None
    return resultado

def cargarDecisionArchivo(nombreArchivo):
    """RF-42 a RF-44. Carga la matriz de decisión ponderada desde un archivo JSON.
    Parámetros: nombreArchivo (str): nombre del archivo JSON.
    Devuelve: dict | None: {'criterios', 'nombres', 'pesos', 'puntajes', 'escenarios'} con todos los
      números como Fraction, o None si hubo un error.
    """
    datos = leerArchivoJson(nombreArchivo)
    if datos is None:
        return None
    for clave in ["criterios", "pesos", "puntajes"]:
        if clave not in datos:
            print("Error: el archivo debe tener la clave '" + clave + "'.")
            return None
    criterios = datos["criterios"]
    if not isinstance(criterios, list) or len(criterios) < 1:
        print("Error: 'criterios' debe ser una lista no vacía.")
        return None
    pesos = validarPesos(criterios, datos["pesos"], "'pesos'")
    if pesos is None:
        return None
    if not isinstance(datos["puntajes"], dict) or len(datos["puntajes"]) < 2:
        print("Error: 'puntajes' debe tener al menos dos alternativas.")
        return None
    puntajes = {}
    for alternativa in datos["puntajes"]:
        puntajes[alternativa] = {}
        for criterio in criterios:
            valor = aFraccion(datos["puntajes"][alternativa].get(criterio)) \
                if isinstance(datos["puntajes"][alternativa], dict) else None
            if valor is None or valor < 1 or valor > 5:
                print("Error: el puntaje de", alternativa, "en", criterio, "debe ser un número de 1 a 5.")
                return None
            puntajes[alternativa][criterio] = valor
    escenarios = {}
    if "escenarios" in datos and isinstance(datos["escenarios"], dict):
        for nombre in datos["escenarios"]:
            vector = validarPesos(criterios, datos["escenarios"][nombre], "el escenario '" + nombre + "'")
            if vector is None:
                return None
            escenarios[nombre] = vector
    nombres = {}
    for criterio in criterios:
        nombres[criterio] = criterio
        if isinstance(datos.get("nombresCriterios"), dict) and criterio in datos["nombresCriterios"]:
            nombres[criterio] = datos["nombresCriterios"][criterio]
    return {"criterios": criterios, "nombres": nombres, "pesos": pesos,
            "puntajes": puntajes, "escenarios": escenarios}

def calcularPuntajes(decision, pesos):
    """RF-42 a RF-47. Calcula v = P.w: el puntaje total de cada alternativa. Modelo matemático: P es la
      matriz de puntajes (alternativas x criterios) y w el vector de pesos. v_i = suma sobre j de
      p(i,j) * w(j) es una COMBINACIÓN LINEAL de las columnas de P con coeficientes w. Como los
      pesos suman 1, v queda en la misma escala de 1 a 5 que los puntajes. Parámetros: decision
      (dict): decisión cargada (usa 'criterios' y 'puntajes'); pesos (dict): vector de pesos
      {criterio: Fraction}. Devuelve: dict: {alternativa: Fraction} con el puntaje total de cada
      una.
    """
    valores = {}
    for alternativa in decision["puntajes"]:
        total = Fraction(0)
        for criterio in decision["criterios"]:
            total = total + decision["puntajes"][alternativa][criterio] * pesos[criterio]
        valores[alternativa] = total
    return valores

def rankingDeAlternativas(valores):
    """Ordena las alternativas de mayor a menor puntaje (ordenamiento por selección).
    Parámetros: valores (dict): {alternativa: puntaje}.
    Devuelve: list[dict]: registros {'nombre', 'puntaje'}; el primero es la mejor alternativa.
    """
    return ordenarSeleccion([{"nombre": n, "puntaje": valores[n]} for n in valores], "puntaje", True)

def redistribuirPesos(criterios, pesos, criterio, nuevoPeso):
    """Cambia el peso de un criterio y reparte el resto en la misma proporción. Modelo matemático: si
      el criterio c pasa de w(c) a t, los demás se multiplican por (1 - t) / (1 - w(c)); así siguen
      sumando 1 y conservan su importancia relativa. Se usa para el análisis de sensibilidad.
      Parámetros: criterios (list[str]): códigos de los criterios; pesos (dict): vector de pesos
      original; criterio (str): criterio cuyo peso cambia; nuevoPeso (Fraction): nuevo peso t, con 0
      <= t <= 1. Devuelve: dict: nuevo vector de pesos.
    """
    nuevo = {}
    for c in criterios:
        if c == criterio:
            nuevo[c] = nuevoPeso
        elif pesos[criterio] == 1:
            nuevo[c] = (1 - nuevoPeso) / (len(criterios) - 1)
        else:
            nuevo[c] = pesos[c] * (1 - nuevoPeso) / (1 - pesos[criterio])
    return nuevo

def pesoDeCambio(decision, criterio, ganadora, otra):
    """Calcula desde qué peso del criterio la alternativa 'otra' supera a la 'ganadora'. Modelo
      matemático: al variar el peso t del criterio c (con el resto repartido en proporción) la
      diferencia v(ganadora) - v(otra) es una función lineal de t. Vale d0 en t = 0 y d1 =
      p(ganadora,c) - p(otra,c) en t = 1. Si cambia de signo entre 0 y 1, se anula en t* = d0 / (d0
      - d1). Parámetros: decision (dict): decisión cargada; criterio (str): criterio cuyo peso se
      hace variar; ganadora (str): alternativa que hoy está primera; otra (str): alternativa con la
      que se compara. Devuelve: Fraction | None: peso t* (entre 0 y 1) a partir del cual 'otra'
      supera a la ganadora, o None si con ningún peso de ese criterio la supera.
    """
    pesos = decision["pesos"]
    if pesos[criterio] == 1:
        return None
    d0 = Fraction(0)
    for c in decision["criterios"]:
        if c != criterio:
            diferencia = decision["puntajes"][ganadora][c] - decision["puntajes"][otra][c]
            d0 = d0 + diferencia * pesos[c] / (1 - pesos[criterio])
    d1 = decision["puntajes"][ganadora][criterio] - decision["puntajes"][otra][criterio]
    if d0 > 0 and d1 < 0:
        return d0 / (d0 - d1)
    return None

def mostrarDecision(decision):
    """RF-42 a RF-47. Muestra P, w, v = P.w, el ranking y el análisis de sensibilidad.
    Parámetros: decision (dict): decisión cargada con cargarDecisionArchivo.
    """
    criterios = decision["criterios"]
    alternativas = list(decision["puntajes"].keys())
    print()
    print("Criterios")
    for criterio in criterios:
        print(" ", criterio, "-", decision["nombres"][criterio], "- peso", formatearNumero(decision["pesos"][criterio]))
    mostrarTabla("Matriz de puntajes P (1 a 5)", alternativas, criterios, decision["puntajes"])
    valores = calcularPuntajes(decision, decision["pesos"])
    ranking = rankingDeAlternativas(valores)
    print()
    print("v = P . w ->", end=" ")
    for alternativa in alternativas:
        print(alternativa, "=", formatearNumero(valores[alternativa]), end="  ")
    print()
    print("Orden (selección):", " > ".join(r["nombre"] + " (" + formatearNumero(r["puntaje"]) + ")" for r in ranking))
    ganadora = ranking[0]["nombre"]
    for nombre in decision["escenarios"]:
        valoresEsc = calcularPuntajes(decision, decision["escenarios"][nombre])
        rankingEsc = rankingDeAlternativas(valoresEsc)
        resultado = "se mantiene" if rankingEsc[0]["nombre"] == ganadora else "CAMBIA"
        print("Escenario '" + nombre + "':", " > ".join(r["nombre"] + " (" + formatearNumero(r["puntaje"]) + ")"
                                                       for r in rankingEsc), "-> la recomendación", resultado)
    print("Sensibilidad: peso a partir del cual otra alternativa supera a", ganadora)
    hayCambio = False
    for criterio in criterios:
        for otra in alternativas:
            if otra != ganadora:
                umbral = pesoDeCambio(decision, criterio, ganadora, otra)
                if umbral is not None:
                    hayCambio = True
                    print("  si el peso de", criterio, "supera", textoPorcentaje(umbral), "->", otra, "pasa a", ganadora,
                          "(hoy:", textoPorcentaje(decision["pesos"][criterio]) + ")")
    if not hayCambio:
        print("  ningún criterio, con ningún peso, cambia la alternativa recomendada.")
    texto = input("Criterio y nuevo peso para probar (por ejemplo C4 0.5; Enter para omitir): ").upper().split()
    if len(texto) == 2 and texto[0] in criterios and aFraccion(texto[1]) is not None and 0 <= aFraccion(texto[1]) <= 1:
        nuevos = redistribuirPesos(criterios, decision["pesos"], texto[0], aFraccion(texto[1]))
        valoresNuevos = calcularPuntajes(decision, nuevos)
        print("Con", texto[0], "=", texto[1], "y el resto en proporción:",
              " > ".join(r["nombre"] + " (" + formatearNumero(r["puntaje"]) + ")" for r in rankingDeAlternativas(valoresNuevos)))
    elif len(texto) > 0:
        print("Entrada no válida; se omite la prueba.")

# --- RF-48 a RF-52 - Relaciones como matrices: incidencia (Punto 1) y trazabilidad (Punto 5) ---

def armarRelacion(filas, columnas, pares, nombre):
    """Arma la matriz booleana de una relación entre dos conjuntos. Modelo matemático: una relación R
      de X en Y se representa con una matriz r(x, y) = 1 si x está relacionado con y. 'pares' da,
      para cada elemento de X, la lista de elementos de Y con los que se relaciona. Parámetros:
      filas (list[str]): elementos del primer conjunto X; columnas (list[str]): elementos del
      segundo conjunto Y; pares (dict): {x: [y, ...]}; nombre (str): nombre de la relación para los
      mensajes de error. Devuelve: dict | None: tabla[x][y] de 0 y 1, o None (con mensaje) si algún
      elemento no existe.
    """
    if not isinstance(pares, dict):
        print("Error: la relación", nombre, "debe ser un diccionario elemento -> lista.")
        return None
    tabla = crearTabla(filas, columnas, 0)
    for x in pares:
        if x not in tabla or not isinstance(pares[x], list):
            print("Error: en", nombre, "el elemento", x, "no existe o su lista es inválida.")
            return None
        for y in pares[x]:
            if y not in columnas:
                print("Error: en", nombre, y, "no existe.")
                return None
            tabla[x][y] = 1
    return tabla

def cargarListaDeNombres(datos, clave):
    """Lee de un JSON una lista de nombres no vacía y sin repetidos.
    Parámetros: datos (dict): contenido del archivo; clave (str): clave donde está la lista.
    Devuelve: list[str] | None: la lista, o None (con mensaje) si falta o es inválida.
    """
    lista = datos.get(clave)
    if not isinstance(lista, list) or len(lista) == 0:
        print("Error: falta la lista '" + clave + "'.")
        return None
    vistos = {}
    for nombre in lista:
        if not isinstance(nombre, str) or nombre in vistos:
            print("Error: la lista '" + clave + "' tiene un nombre inválido o repetido.")
            return None
        vistos[nombre] = True
    return lista

def cargarIncidenciaArchivo(nombreArchivo):
    """RF-48 y RF-49. Carga la matriz de incidencia S (solicitudes x módulos).
    Devuelve: dict | None: {'filas', 'columnas', 'tabla'} o None si hubo un error.
    """
    datos = leerArchivoJson(nombreArchivo)
    if datos is None:
        return None
    solicitudes = cargarListaDeNombres(datos, "solicitudes")
    modulos = cargarListaDeNombres(datos, "modulos")
    if solicitudes is None or modulos is None:
        return None
    tabla = armarRelacion(solicitudes, modulos, datos.get("incidencia"), "incidencia")
    if tabla is None:
        return None
    return {"filas": solicitudes, "columnas": modulos, "tabla": tabla}

def calcularSuperposicion(incidencia):
    """Calcula el alcance directo a = S.u y la matriz de superposición S.S^T. Modelo matemático: u es
      el vector de unos; a(i) = suma de la fila i de S = cantidad de módulos que modifica la
      solicitud i. (S.S^T)(i,k) = cantidad de módulos que modifican a la vez las solicitudes i y k;
      su diagonal es el alcance directo (porque s(i,j)^2 = s(i,j) en una matriz de ceros y unos).
      Parámetros: incidencia (dict): {'filas', 'columnas', 'tabla'} de cargarIncidenciaArchivo.
      Devuelve: tuple[dict, dict]: (alcance, superposicion) con alcance[solicitud] y
      superposicion[solicitud][solicitud].
    """
    filas = incidencia["filas"]
    columnas = incidencia["columnas"]
    unos = crearTabla(columnas, ["u"], 1)
    producto = multiplicarTablas(filas, columnas, ["u"], incidencia["tabla"], unos, False)
    alcance = {fila: producto[fila]["u"] for fila in filas}
    traspuesta = transponerTabla(filas, columnas, incidencia["tabla"])
    superposicion = multiplicarTablas(filas, columnas, filas, incidencia["tabla"], traspuesta, False)
    return alcance, superposicion

def analizarIncidencia(nombreArchivo):
    """RF-48 y RF-49. Muestra S, el alcance directo y la superposición S.S^T.
    Parámetros: nombreArchivo (str): archivo JSON con la matriz de incidencia.
    """
    incidencia = cargarIncidenciaArchivo(nombreArchivo)
    if incidencia is None:
        return
    filas = incidencia["filas"]
    mostrarTabla("Matriz de incidencia S (solicitudes x módulos)", filas, incidencia["columnas"], incidencia["tabla"])
    alcance, superposicion = calcularSuperposicion(incidencia)
    mostrarTabla("S . S^T (diagonal = alcance directo; fuera de la diagonal = módulos compartidos)",
                 filas, filas, superposicion)
    registros = [{"nombre": fila, "alcance": alcance[fila]} for fila in filas]
    print()
    print("Alcance directo a = S.u:", "  ".join(fila + "=" + str(alcance[fila]) for fila in filas))
    ranking = ordenarBurbuja(registros, "alcance", True)
    print("Solicitudes de mayor a menor alcance (burbuja):", [r["nombre"] + "(" + str(r["alcance"]) + ")" for r in ranking])
    pares = []
    for i in range(len(filas)):
        for k in range(i + 1, len(filas)):
            if superposicion[filas[i]][filas[k]] > 0:
                pares.append({"nombre": filas[i] + "-" + filas[k], "comparten": superposicion[filas[i]][filas[k]]})
    pares = ordenarBurbuja(pares, "comparten", True)
    print("Pares con módulos en común:", [p["nombre"] + "(" + str(p["comparten"]) + ")" for p in pares])
    if len(pares) > 0:
        primero = pares[0]["nombre"].split("-")
        comunes = [m for m in incidencia["columnas"] if incidencia["tabla"][primero[0]][m] == 1 and incidencia["tabla"][primero[1]][m] == 1]
        print("Mayor superposición:", pares[0]["nombre"], "comparten", comunes, "-> conviene planificarlas juntas.")

def cargarTrazabilidadArchivo(nombreArchivo):
    """RF-50. Carga las relaciones requerimiento-componente y componente-prueba.
    Devuelve: dict | None: {'requerimientos', 'componentes', 'pruebas', 'rc', 'ct'} o None.
    """
    datos = leerArchivoJson(nombreArchivo)
    if datos is None:
        return None
    requerimientos = cargarListaDeNombres(datos, "requerimientos")
    componentes = cargarListaDeNombres(datos, "componentes")
    pruebas = cargarListaDeNombres(datos, "pruebas")
    if requerimientos is None or componentes is None or pruebas is None:
        return None
    rc = armarRelacion(requerimientos, componentes, datos.get("reqComp"), "reqComp")
    ct = armarRelacion(componentes, pruebas, datos.get("compPrueba"), "compPrueba")
    if rc is None or ct is None:
        return None
    return {"requerimientos": requerimientos, "componentes": componentes, "pruebas": pruebas, "rc": rc, "ct": ct}

def calcularTrazabilidad(trazabilidad):
    """Calcula RT = RC (.) CT, el producto booleano de las dos relaciones. Modelo matemático:
      composición de relaciones. rt(r, t) = 1 si existe un componente c con rc(r, c) = 1 y ct(c, t)
      = 1: la prueba t verifica al requerimiento r a través de algún componente. Una fila nula de RT
      es un requerimiento sin prueba. Parámetros: trazabilidad (dict): datos cargados con
      cargarTrazabilidadArchivo. Devuelve: dict: tabla rt[requerimiento][prueba] de 0 y 1.
    """
    return multiplicarTablas(trazabilidad["requerimientos"], trazabilidad["componentes"],
                             trazabilidad["pruebas"], trazabilidad["rc"], trazabilidad["ct"], True)

def filasNulas(filas, columnas, tabla):
    """Devuelve los nombres de las filas formadas solo por ceros.
    Parámetros: filas (list[str]): nombres de las filas; columnas (list[str]): nombres de las
      columnas; tabla (dict): tabla de ceros y unos.
    Devuelve: list[str]: filas nulas (elementos sin ninguna relación).
    """
    return [fila for fila in filas if sum(tabla[fila][columna] for columna in columnas) == 0]

def impactoDeComponente(trazabilidad, componente):
    """Análisis de impacto de modificar un componente. Modelo matemático: la columna del componente en
      RC da los requerimientos involucrados; la fila del componente en CT da las pruebas que lo
      verifican directamente; las filas de esos requerimientos en RT dan todas las pruebas que
      conviene repetir para volver a verificarlos completos. Parámetros: trazabilidad (dict): datos
      cargados; componente (str): componente que se modifica. Devuelve: tuple[list, list, list]:
      (requerimientos involucrados, pruebas directas, pruebas para reverificar los requerimientos
      afectados).
    """
    rt = calcularTrazabilidad(trazabilidad)
    requerimientos = [r for r in trazabilidad["requerimientos"] if trazabilidad["rc"][r][componente] == 1]
    directas = [t for t in trazabilidad["pruebas"] if trazabilidad["ct"][componente][t] == 1]
    completas = [t for t in trazabilidad["pruebas"] if any(rt[r][t] == 1 for r in requerimientos)]
    return requerimientos, directas, completas

def analizarTrazabilidad(nombreArchivo):
    """RF-50 a RF-52. Muestra RC, CT, RT, las filas nulas y el impacto.
    Parámetros: nombreArchivo (str): archivo JSON con las relaciones de trazabilidad.
    """
    trazabilidad = cargarTrazabilidadArchivo(nombreArchivo)
    if trazabilidad is None:
        return
    r = trazabilidad["requerimientos"]
    c = trazabilidad["componentes"]
    t = trazabilidad["pruebas"]
    mostrarTabla("RC (requerimiento x componente)", r, c, trazabilidad["rc"])
    mostrarTabla("CT (componente x prueba)", c, t, trazabilidad["ct"])
    rt = calcularTrazabilidad(trazabilidad)
    mostrarTabla("RT = RC (.) CT (producto booleano)", r, t, rt)
    print()
    print("Requerimientos sin prueba (filas nulas de RT):", filasNulas(r, t, rt))
    print("Componentes sin prueba (filas nulas de CT):", filasNulas(c, t, trazabilidad["ct"]))
    print("Requerimientos sin componente (filas nulas de RC):", filasNulas(r, c, trazabilidad["rc"]))
    codigo = input("Componente que se modifica (Enter para omitir): ").strip().upper()
    if codigo != "":
        if codigo not in c:
            print("El componente", codigo, "no existe.")
        else:
            reqs, directas, completas = impactoDeComponente(trazabilidad, codigo)
            print("Requerimientos involucrados (columna", codigo, "de RC):", reqs)
            print("Pruebas que lo verifican (fila", codigo, "de CT):", directas)
            print("Pruebas para reverificar esos requerimientos (filas de RT):", completas)

# --- RF-53 a RF-58 - Digrafo de procesos: caminos simples, duración y porcentaje manual ---

def cargarProcesoArchivo(nombreArchivo):
    """RF-53. Carga un proceso como digrafo de actividades con duración.
    Parámetros: nombreArchivo (str): nombre del archivo JSON.
    Devuelve: dict | None: {'codigos', 'actividades', 'sucesores', 'inicio', 'fin'} con los minutos
      como Fraction, o None si hubo un error.
    """
    datos = leerArchivoJson(nombreArchivo)
    if datos is None:
        return None
    actividades = datos.get("actividades")
    if not isinstance(actividades, dict) or len(actividades) < 1:
        print("Error: falta el diccionario 'actividades'.")
        return None
    codigos = list(actividades.keys())
    convertidas = {}
    for codigo in codigos:
        actividad = actividades[codigo]
        if not isinstance(actividad, dict) or actividad.get("tipo") not in ["manual", "automatica", "sin dato"]:
            print("Error: la actividad", codigo, "debe tener 'tipo' manual, automatica o sin dato.")
            return None
        minutos = aFraccion(actividad.get("minutos"))
        if minutos is None or minutos < 0:
            print("Error: la actividad", codigo, "debe tener 'minutos' numérico no negativo.")
            return None
        convertidas[codigo] = {"nombre": str(actividad.get("nombre", codigo)), "tipo": actividad["tipo"], "minutos": minutos}
    sucesores = datos.get("sucesores")
    if not isinstance(sucesores, dict):
        print("Error: falta el diccionario 'sucesores'.")
        return None
    inicio = datos.get("inicio")
    fin = datos.get("fin")
    if inicio not in convertidas or fin not in convertidas:
        print("Error: 'inicio' y 'fin' deben ser actividades existentes.")
        return None
    return {"codigos": codigos, "actividades": convertidas, "sucesores": sucesores, "inicio": inicio, "fin": fin}

def armarSistemaProceso(proceso):
    """Convierte el proceso en un digrafo (reutiliza armarSistema) para usar Warshall. Modelo
      matemático: G_P = (V, E) con V = actividades y a(i,j) = 1 si la actividad j sigue a la i. La
      diagonal de A* señala los ciclos (retrabajo). Parámetros: proceso (dict): proceso cargado.
      Devuelve: dict | None: sistema {'modulos', 'adyacencia'} o None si hay un sucesor inexistente.
    """
    return armarSistema(proceso["codigos"], proceso["sucesores"])

def explorarCaminos(sistema, actual, destino, recorrido, resultado):
    """Búsqueda en profundidad (recursiva) de todos los caminos simples hacia 'destino'.
    Parámetros: sistema (dict): digrafo del proceso; actual (str): vértice donde se está parado;
      destino (str): vértice final buscado; recorrido (list[str]): camino construido hasta ahora (se
      modifica y se restaura); resultado (list[list[str]]): lista donde se guardan los caminos
      completos.
    """
    recorrido.append(actual)
    if actual == destino:
        resultado.append(list(recorrido))
    else:
        for siguiente in sistema["modulos"]:
            if sistema["adyacencia"][actual][siguiente] == 1 and siguiente not in recorrido:
                explorarCaminos(sistema, siguiente, destino, recorrido, resultado)
    recorrido.pop()

def caminosSimples(proceso):
    """RF-53 a RF-58. Devuelve todos los caminos simples del inicio al fin del proceso.
    Parámetros: proceso (dict): proceso cargado con cargarProcesoArchivo.
    Devuelve: list[list[str]]: caminos, cada uno como lista de códigos de actividad.
    """
    sistema = armarSistemaProceso(proceso)
    if sistema is None:
        return []
    resultado = []
    explorarCaminos(sistema, proceso["inicio"], proceso["fin"], [], resultado)
    return resultado

def duracionDelCamino(proceso, camino, soloManuales):
    """Suma los minutos de las actividades de un camino (E no se considera: vale 0).
    Parámetros: proceso (dict): proceso cargado; camino (list[str]): actividades del camino;
      soloManuales (bool): True para sumar solo las actividades de tipo manual.
    Devuelve: Fraction | int: minutos totales.
    """
    total = 0
    for codigo in camino:
        actividad = proceso["actividades"][codigo]
        if not soloManuales or actividad["tipo"] == "manual":
            total = total + actividad["minutos"]
    return total

def resumirProceso(proceso):
    """Calcula, para cada camino simple, su duración, sus minutos manuales y su porcentaje manual.
    Parámetros: proceso (dict): proceso cargado.
    Devuelve: list[dict]: registros {'camino', 'minutos', 'manuales', 'porcentaje'} ordenados de
      mayor a menor duración (burbuja). 'porcentaje' es un Fraction 0..1.
    """
    registros = []
    for camino in caminosSimples(proceso):
        minutos = duracionDelCamino(proceso, camino, False)
        manuales = duracionDelCamino(proceso, camino, True)
        porcentaje = Fraction(0)
        if minutos > 0:
            porcentaje = Fraction(manuales) / Fraction(minutos)
        registros.append({"camino": camino, "minutos": minutos, "manuales": manuales, "porcentaje": porcentaje})
    return ordenarBurbuja(registros, "minutos", True)

def mostrarProceso(proceso):
    """Muestra la matriz del proceso, los ciclos y los caminos simples con sus tiempos.
    Parámetros: proceso (dict): proceso cargado.
    """
    sistema = armarSistemaProceso(proceso)
    if sistema is None:
        return
    codigos = proceso["codigos"]
    mostrarMatriz("Matriz de adyacencia del proceso (a(i,j) = 1 si j sigue a i)", codigos, sistema["adyacencia"])
    alcance = warshall(sistema)
    ciclos = modulosEnCiclos(sistema, alcance)
    if len(ciclos) == 0:
        print("El proceso es acíclico: no hay retrabajo.")
    else:
        print("Ciclos (retrabajo o esperas):", gruposDeCiclos(sistema, alcance))
    print("Caminos simples de", proceso["inicio"], "a", proceso["fin"], "(la actividad 'sin dato' no suma tiempo):")
    for registro in resumirProceso(proceso):
        print("  ", "->".join(registro["camino"]), ":", formatearNumero(registro["minutos"]), "min, manuales",
              formatearNumero(registro["manuales"]), "min =", textoPorcentaje(registro["porcentaje"]))

def mostrarComparacionProcesos():
    """RF-58 y RF-64. Analiza el proceso actual y, si se indica, el reingenierizado, y calcula la
      reducción. Modelo matemático: la reducción porcentual es (d0 - d1) / d0, con d0 la duración
      del camino más largo del proceso actual y d1 la del camino más largo del reingenierizado (peor
      caso de cada proceso).
    """
    actual = cargarProcesoArchivo(pedirNombreArchivo("procesoPedido.json"))
    if actual is None:
        return
    print()
    print("PROCESO ACTUAL")
    mostrarProceso(actual)
    texto = input("Archivo del proceso reingenierizado (Enter para omitir): ").strip()
    if texto == "":
        return
    nuevo = cargarProcesoArchivo(texto)
    if nuevo is None:
        return
    print()
    print("PROCESO REINGENIERIZADO")
    mostrarProceso(nuevo)
    resumenActual = resumirProceso(actual)
    resumenNuevo = resumirProceso(nuevo)
    if len(resumenActual) > 0 and len(resumenNuevo) > 0 and resumenActual[0]["minutos"] > 0:
        d0 = resumenActual[0]["minutos"]
        d1 = resumenNuevo[0]["minutos"]
        print()
        print("Camino más largo:", formatearNumero(d0), "min ->", formatearNumero(d1), "min; reducción =",
              textoPorcentaje(Fraction(d0 - d1) / Fraction(d0)))

# --- RF-59 a RF-62 - Principios de conteo ---

def factorial(n):
    """n! = n * (n - 1) * ... * 1 (0! = 1). Cantidad de formas de ordenar n elementos distintos.
    Parámetros: n (int): entero no negativo.
    Devuelve: int: el factorial de n.
    """
    resultado = 1
    for i in range(2, n + 1):
        resultado = resultado * i
    return resultado

def permutaciones(n):
    """Permutaciones de n elementos distintos: P(n) = n!. Importa el orden y se usan todos."""
    return factorial(n)

def variaciones(n, r):
    """Variaciones sin repetición: V(n, r) = n! / (n - r)!. Importa el orden; se eligen r de n."""
    if r > n or r < 0:
        return 0
    resultado = 1
    for i in range(n - r + 1, n + 1):
        resultado = resultado * i
    return resultado

def combinaciones(n, r):
    """Combinaciones sin repetición: C(n, r) = n! / (r! (n - r)!). NO importa el orden."""
    return variaciones(n, r) // factorial(r)

def variacionesConRepeticion(n, r):
    """Variaciones con repetición: n^r (principio de multiplicación). Importa el orden y se puede
      repetir.
    """
    resultado = 1
    for i in range(r):
        resultado = resultado * n
    return resultado

def mostrarConteo():
    """RF-59 a RF-62. Muestra los conteos del informe y permite calcular n y r propios."""
    print()
    print("Conteos del informe")
    print("  P1-h  Elegir 4 situaciones de 6 (no importa el orden): C(6,4) =", combinaciones(6, 4))
    print("  P2-k  5 elementos, 6 decisiones cada uno: 6^5 =", variacionesConRepeticion(6, 5))
    print("  P2-k  Base histórica solo conservar o migrar: 2 * 6^4 =", 2 * variacionesConRepeticion(6, 4))
    print("  P5-i  Pares de revisión con 6 desarrolladores: C(6,2) =", combinaciones(6, 2))
    print("  P5-i  Asignaciones (autor, revisor) distintos: V(6,2) =", variaciones(6, 2))
    print("  P5-i  Ordenar 5 solicitudes: 5! =", permutaciones(5))
    print("  P5-i  Atender 3 de 5 con orden: V(5,3) =", variaciones(5, 3))
    print("  P5-i  Atender 3 de 5 sin orden: C(5,3) =", combinaciones(5, 3))
    n = pedirEntero("n para un conteo propio (0 para omitir, hasta 20): ", 0, 20)
    if n > 0:
        r = pedirEntero("r (0 a " + str(n) + "): ", 0, n)
        print("  P(" + str(n) + ") =", permutaciones(n), " V(" + str(n) + "," + str(r) + ") =", variaciones(n, r),
              " C(" + str(n) + "," + str(r) + ") =", combinaciones(n, r), " " + str(n) + "^" + str(r) + " =",
              variacionesConRepeticion(n, r))

# --- Gráficos (opcional: necesita matplotlib y networkx) ---

def prepararCarpetaGraficos(carpeta):
    """Crea la carpeta de gráficos si no existe y devuelve su ruta.
    Parámetros: carpeta (str | None): carpeta de salida; si es None se usa 'graficos' junto al
      programa.
    Devuelve: str: ruta de la carpeta lista para guardar imágenes.
    """
    if carpeta is None:
        carpeta = os.path.join(carpetaPrograma, nombreCarpetaGraficos)
    if not os.path.isdir(carpeta):
        os.makedirs(carpeta)
    return carpeta

def calcularPosiciones(grafoNx, semilla):
    """Calcula dónde se dibuja cada vértice (distribución con resortes, resultado repetible).
    Parámetros: grafoNx: grafo de networkx; semilla (int): número que fija la disposición.
    Devuelve: dict: {vértice: (x, y)}.
    """
    return nx.spring_layout(grafoNx, seed=semilla, k=1.3, iterations=200)

def dibujarDigrafo(ejes, sistema, titulo, semilla):
    """Dibuja el digrafo de dependencias resaltando ciclos y módulos críticos.
    Parámetros: ejes: ejes de matplotlib donde se dibuja; sistema (dict): sistema de módulos; titulo
      (str): título del gráfico; semilla (int): semilla de la disposición.
    """
    modulos = sistema["modulos"]
    alcance = warshall(sistema)
    entrada, salida = calcularGrados(sistema)
    g = nx.DiGraph()
    g.add_nodes_from(modulos)
    arcosCiclo = []
    arcosNormales = []
    for i in modulos:
        for j in modulos:
            if sistema["adyacencia"][i][j] == 1:
                g.add_edge(i, j)
                if alcance[j][i] == 1:
                    arcosCiclo.append((i, j))
                else:
                    arcosNormales.append((i, j))
    posiciones = calcularPosiciones(g, semilla)
    colores = [entrada[m] for m in modulos]
    bordes = ["#C00000" if alcance[m][m] == 1 else "#333333" for m in modulos]
    anchos = [3.2 if alcance[m][m] == 1 else 1.0 for m in modulos]
    nodos = nx.draw_networkx_nodes(g, posiciones, ax=ejes, node_color=colores, cmap=plt.cm.Blues, vmin=0,
                                   vmax=max(max(colores), 1) + 1, edgecolors=bordes, linewidths=anchos,
                                   node_size=1300)
    nx.draw_networkx_labels(g, posiciones, ax=ejes, font_size=9, font_weight="bold")
    estilo = {"ax": ejes, "node_size": 1300, "arrowstyle": "-|>", "arrowsize": 16,
              "connectionstyle": "arc3,rad=0.12"}
    nx.draw_networkx_edges(g, posiciones, edgelist=arcosNormales, edge_color="#555555", width=1.4, **estilo)
    nx.draw_networkx_edges(g, posiciones, edgelist=arcosCiclo, edge_color="#C00000", width=2.4, **estilo)
    unos = contarUnos(modulos, modulos, alcance)
    ciclos = gruposDeCiclos(sistema, alcance)
    ejes.set_title(titulo + "\n" + str(len(modulos)) + " módulos, " + str(len(arcosNormales) + len(arcosCiclo))
                   + " arcos, " + str(unos) + " pares alcanzables, " + str(len(ciclos)) + " ciclo(s)", fontsize=10)
    ejes.axis("off")
    return nodos

def dibujarAlcanzabilidad(ejes, sistema, titulo):
    """Dibuja la matriz de alcanzabilidad A* como mapa de calor (1 = alcanzable).
    Parámetros: ejes: ejes de matplotlib; sistema (dict): sistema de módulos; titulo (str): título
      del gráfico.
    """
    modulos = sistema["modulos"]
    alcance = warshall(sistema)
    datos = []
    for i in modulos:
        fila = []
        for j in modulos:
            fila.append(alcance[i][j])
        datos.append(fila)
    ejes.imshow(datos, cmap="Blues", vmin=0, vmax=1.6)
    for i in range(len(modulos)):
        for j in range(len(modulos)):
            ejes.text(j, i, str(datos[i][j]), ha="center", va="center", fontsize=8,
                      color="white" if datos[i][j] == 1 else "#777777")
        if datos[i][i] == 1:
            ejes.add_patch(plt.Rectangle((i - 0.5, i - 0.5), 1, 1, fill=False, edgecolor="#C00000", linewidth=2.5))
    ejes.set_xticks(range(len(modulos)))
    ejes.set_yticks(range(len(modulos)))
    ejes.set_xticklabels(modulos, fontsize=8, rotation=90)
    ejes.set_yticklabels(modulos, fontsize=8)
    ejes.set_title(titulo + "\n" + str(contarUnos(modulos, modulos, alcance)) + " unos; recuadro rojo = ciclo", fontsize=10)

def dibujarRedPonderada(ejes, grafo, camino, rutaFija, titulo, semilla):
    """Dibuja la red de distribución con sus pesos, el camino mínimo y una ruta fija.
    Parámetros: ejes: ejes de matplotlib; grafo (dict): grafo[nodo][vecino] = minutos; camino
      (list[str]): camino mínimo (puede estar vacío); rutaFija (list[str]): ruta fija a comparar
      (puede estar vacía); titulo (str): título del gráfico; semilla (int): semilla de la
      disposición.
    """
    g = nx.Graph()
    for u in grafo:
        for v in grafo[u]:
            g.add_edge(u, v, peso=formatearNumero(grafo[u][v]))
    posiciones = calcularPosiciones(g, semilla)
    nx.draw_networkx_nodes(g, posiciones, ax=ejes, node_color="#DDE8F7", edgecolors="#333333", node_size=950)
    nx.draw_networkx_labels(g, posiciones, ax=ejes, font_size=9, font_weight="bold")
    nx.draw_networkx_edges(g, posiciones, ax=ejes, edge_color="#999999", width=1.4)
    if len(rutaFija) > 1:
        tramos = [(rutaFija[i], rutaFija[i + 1]) for i in range(len(rutaFija) - 1)]
        nx.draw_networkx_edges(g, posiciones, ax=ejes, edgelist=tramos, edge_color="#E07B00", width=3, style="dashed")
    if len(camino) > 1:
        tramos = [(camino[i], camino[i + 1]) for i in range(len(camino) - 1)]
        nx.draw_networkx_edges(g, posiciones, ax=ejes, edgelist=tramos, edge_color="#1E8E3E", width=4)
    nx.draw_networkx_edge_labels(g, posiciones, ax=ejes, edge_labels=nx.get_edge_attributes(g, "peso"), font_size=8)
    ejes.set_title(titulo, fontsize=10)
    ejes.axis("off")

def dibujarRectasCostos(ejes, alternativas, horizonte):
    """Dibuja las rectas de costo acumulado C(n) = fijo + anual*n y sus puntos de equilibrio.
    Parámetros: ejes: ejes de matplotlib; alternativas (dict): {nombre: {'fijo', 'anual'}};
      horizonte (int): cantidad de años que se dibujan.
    """
    anios = list(range(horizonte + 1))
    for nombre in alternativas:
        costos = [float(alternativas[nombre]["fijo"] + alternativas[nombre]["anual"] * n) for n in anios]
        ejes.plot(anios, costos, linewidth=2, label="Alternativa " + nombre)
    nombres = list(alternativas.keys())
    for i in range(len(nombres)):
        for j in range(i + 1, len(nombres)):
            clasificacion, solucion = puntoEquilibrio(alternativas[nombres[i]], alternativas[nombres[j]])
            if clasificacion == "compatible determinado" and 0 <= solucion[0] <= horizonte:
                ejes.plot([float(solucion[0])], [float(solucion[1])], "o", color="black")
                ejes.annotate(nombres[i] + "=" + nombres[j] + " n=" + formatearNumero(solucion[0]),
                              (float(solucion[0]), float(solucion[1])), textcoords="offset points",
                              xytext=(8, -14), fontsize=8)
    ejes.set_xlabel("años de operación n")
    ejes.set_ylabel("costo acumulado (miles de u.m.)")
    ejes.set_title("Costo acumulado y puntos de equilibrio", fontsize=10)
    ejes.grid(alpha=0.3)
    ejes.legend(fontsize=8)

def dibujarDecision(ejes, decision):
    """Dibuja v = P.w como barras apiladas: cuánto aporta cada criterio al puntaje de cada alternativa.
    Parámetros: ejes: ejes de matplotlib; decision (dict): decisión cargada.
    """
    alternativas = list(decision["puntajes"].keys())
    izquierda = [0.0] * len(alternativas)
    for criterio in decision["criterios"]:
        aportes = [float(decision["puntajes"][a][criterio] * decision["pesos"][criterio]) for a in alternativas]
        ejes.barh(alternativas, aportes, left=izquierda, label=criterio + " (peso " + formatearNumero(decision["pesos"][criterio]) + ")")
        izquierda = [izquierda[k] + aportes[k] for k in range(len(alternativas))]
    valores = calcularPuntajes(decision, decision["pesos"])
    for k in range(len(alternativas)):
        ejes.text(izquierda[k] + 0.04, k, formatearNumero(valores[alternativas[k]]), va="center", fontsize=9, fontweight="bold")
    ejes.invert_yaxis()
    ejes.set_xlabel("puntaje total v (escala 1 a 5)")
    ejes.set_title("Matriz de decisión ponderada: v = P.w", fontsize=10)
    ejes.legend(fontsize=7, loc="lower right")

def calcularNiveles(sistema, inicio):
    """Asigna a cada vértice un nivel (columna) para dibujar un proceso de izquierda a derecha.
    Parámetros: sistema (dict): digrafo del proceso; inicio (str): actividad inicial.
    Devuelve: dict: {vértice: nivel}.
    """
    niveles = {inicio: 0}
    cola = [inicio]
    posicion = 0
    while posicion < len(cola):
        actual = cola[posicion]
        posicion = posicion + 1
        for siguiente in sistema["modulos"]:
            if sistema["adyacencia"][actual][siguiente] == 1 and siguiente not in niveles:
                niveles[siguiente] = niveles[actual] + 1
                cola.append(siguiente)
    for codigo in sistema["modulos"]:
        if codigo not in niveles:
            niveles[codigo] = 0
    return niveles

def dibujarProcesoGrafo(ejes, proceso, titulo):
    """Dibuja el digrafo de un proceso: naranja = manual, celeste = automática, gris = sin dato.
    Parámetros: ejes: ejes de matplotlib; proceso (dict): proceso cargado; titulo (str): título del
      gráfico.
    """
    sistema = armarSistemaProceso(proceso)
    alcance = warshall(sistema)
    niveles = calcularNiveles(sistema, proceso["inicio"])
    g = nx.DiGraph()
    g.add_nodes_from(sistema["modulos"])
    arcosCiclo = []
    arcosNormales = []
    for i in sistema["modulos"]:
        for j in sistema["modulos"]:
            if sistema["adyacencia"][i][j] == 1:
                g.add_edge(i, j)
                if alcance[j][i] == 1:
                    arcosCiclo.append((i, j))
                else:
                    arcosNormales.append((i, j))
    contadorPorNivel = {}
    posiciones = {}
    for codigo in sistema["modulos"]:
        nivel = niveles[codigo]
        contadorPorNivel[nivel] = contadorPorNivel.get(nivel, 0) + 1
        posiciones[codigo] = (nivel, -contadorPorNivel[nivel])
    mapaColor = {"manual": "#F4B183", "automatica": "#9DC3E6", "sin dato": "#D9D9D9"}
    colores = [mapaColor[proceso["actividades"][c]["tipo"]] for c in sistema["modulos"]]
    etiquetas = {}
    for c in sistema["modulos"]:
        etiquetas[c] = c + "\n" + formatearNumero(proceso["actividades"][c]["minutos"]) + " min"
    nx.draw_networkx_nodes(g, posiciones, ax=ejes, node_color=colores, edgecolors="#333333", node_size=1500)
    nx.draw_networkx_labels(g, posiciones, labels=etiquetas, ax=ejes, font_size=8)
    estilo = {"ax": ejes, "node_size": 1500, "arrowstyle": "-|>", "arrowsize": 14, "connectionstyle": "arc3,rad=0.15"}
    nx.draw_networkx_edges(g, posiciones, edgelist=arcosNormales, edge_color="#555555", width=1.4, **estilo)
    nx.draw_networkx_edges(g, posiciones, edgelist=arcosCiclo, edge_color="#C00000", width=2.4, **estilo)
    mayor = resumirProceso(proceso)
    detalle = ""
    if len(mayor) > 0:
        detalle = "\ncamino más largo: " + formatearNumero(mayor[0]["minutos"]) + " min, " + textoPorcentaje(mayor[0]["porcentaje"]) + " manual"
    ejes.set_title(titulo + detalle, fontsize=10)
    ejes.axis("off")
    ejes.margins(0.12)

def guardarFigura(figura, carpeta, nombreArchivo, abrirVentana):
    """Guarda una figura como PNG, la cierra y opcionalmente la muestra en una ventana.
    Parámetros: figura: figura de matplotlib; carpeta (str): carpeta de destino; nombreArchivo
      (str): nombre del PNG; abrirVentana (bool): True para abrir además una ventana interactiva.
    Devuelve: str: ruta del archivo guardado.
    """
    figura.tight_layout()
    ruta = os.path.join(carpeta, nombreArchivo)
    figura.savefig(ruta, dpi=150)
    if abrirVentana:
        plt.show(block=True)        # espera a que el usuario cierre la ventana
    plt.close(figura)
    return ruta

def generarGrafico(numero, carpeta, abrirVentana):
    """Opcional (sin RF). Genera uno de los gráficos usando los archivos JSON del caso.
    Parámetros: numero (int): gráfico a generar (1 a 6); carpeta (str | None): carpeta de salida
      (None = carpeta 'graficos' del programa); abrirVentana (bool): True para mostrar además una
      ventana.
    Devuelve: str | None: ruta de la imagen creada, o None si faltan datos o bibliotecas.
    """
    if not hayGraficos:
        print("Para ver gráficos instale las bibliotecas:  pip install matplotlib networkx")
        return None
    carpeta = prepararCarpetaGraficos(carpeta)
    if numero in [1, 2]:
        original = cargarModulosArchivo("modulosLogix.json")
        reestructurado = cargarModulosArchivo("modulosReestructurado.json")
        if original is None or reestructurado is None:
            return None
        figura, ejes = plt.subplots(1, 2, figsize=(13, 6))
        if numero == 1:
            dibujarDigrafo(ejes[0], original, "G: LOGIX original", 5)
            dibujarDigrafo(ejes[1], reestructurado, "G': con bus de eventos EVT", 5)
            return guardarFigura(figura, carpeta, "digrafosGyGprima.png", abrirVentana)
        dibujarAlcanzabilidad(ejes[0], original, "A* de G")
        dibujarAlcanzabilidad(ejes[1], reestructurado, "A* de G'")
        return guardarFigura(figura, carpeta, "alcanzabilidadGyGprima.png", abrirVentana)
    if numero == 3:
        red = cargarRedArchivo("redDistribucion.json")
        drones = cargarRedArchivo("redConDrones.json")
        if red is None or drones is None:
            return None
        figura, ejes = plt.subplots(1, 2, figsize=(13, 5.5))
        distancia, camino = dijkstra(red, "D", "Z3", False)
        dibujarRedPonderada(ejes[0], red, camino, ["D", "H1", "Z1", "Z3"],
                            "Red de la Tabla 5: mínimo D-Z3 = " + formatearNumero(distancia) + " min (verde); ruta fija = 23 (naranja)", 4)
        distancia, camino = dijkstra(drones, "D", "Z3", False)
        dibujarRedPonderada(ejes[1], drones, camino, [], "Con corredor de drones: mínimo D-Z3 = " + formatearNumero(distancia) + " min", 4)
        return guardarFigura(figura, carpeta, "redDistribucion.png", abrirVentana)
    if numero == 4:
        alternativas = cargarCostosArchivo("costosAlternativas.json")
        if alternativas is None:
            return None
        figura, ejes = plt.subplots(figsize=(8, 5))
        dibujarRectasCostos(ejes, alternativas, 12)
        return guardarFigura(figura, carpeta, "costosAcumulados.png", abrirVentana)
    if numero == 5:
        decision = cargarDecisionArchivo("decisionAlternativas.json")
        if decision is None:
            return None
        figura, ejes = plt.subplots(figsize=(8, 4))
        dibujarDecision(ejes, decision)
        return guardarFigura(figura, carpeta, "matrizDecision.png", abrirVentana)
    if numero == 6:
        actual = cargarProcesoArchivo("procesoPedido.json")
        nuevo = cargarProcesoArchivo("procesoReingenierizado.json")
        if actual is None or nuevo is None:
            return None
        figura, ejes = plt.subplots(2, 1, figsize=(11, 9))
        dibujarProcesoGrafo(ejes[0], actual, "G_P: proceso actual de atención de un pedido")
        dibujarProcesoGrafo(ejes[1], nuevo, "G_P': proceso reingenierizado")
        return guardarFigura(figura, carpeta, "procesoPedidos.png", abrirVentana)
    return None

def generarGraficos():
    """Opcional (sin RF). Menú de gráficos: elige uno o todos, los guarda como PNG y opcionalmente los
      abre.
    """
    if not hayGraficos:
        print("Esta opción necesita matplotlib y networkx. Instálelas con:  pip install matplotlib networkx")
        return
    # Respuesta s/N: acepta mayúsculas y minúsculas ("s", "S", "si", "SI", "n", "N"); Enter = no.
    texto = ""
    while texto not in ["s", "si", "sí", "n", "no"]:
        texto = input("¿Abrir los gráficos también en una ventana? (s/N): ").strip().lower()
        if texto == "":
            texto = "n"
        elif texto not in ["s", "si", "sí", "n", "no"]:
            print("  Responda s o n (mayúscula o minúscula).")
    ventana = texto in ["s", "si", "sí"]
    opcion = -1
    while opcion != 0:                  # se repite hasta que el usuario elija volver al menú
        print()
        print("Gráficos disponibles")
        print("  1. Digrafos G y G' (dependencias, ciclos y criticidad)")
        print("  2. Matrices de alcanzabilidad A* de G y G'")
        print("  3. Red de distribución y camino mínimo (sin y con drones)")
        print("  4. Rectas de costo acumulado y puntos de equilibrio")
        print("  5. Matriz de decisión ponderada")
        print("  6. Procesos de atención de pedidos (actual y reingenierizado)")
        print("  7. Todos")
        print("  0. Volver al menú principal")
        opcion = pedirEntero("Gráfico (0 a 7): ", 0, 7)
        if opcion == 7:
            numeros = [1, 2, 3, 4, 5, 6]
        elif opcion == 0:
            numeros = []
        else:
            numeros = [opcion]
        for numero in numeros:
            try:
                ruta = generarGrafico(numero, None, ventana)
            except Exception as error:      # un fallo al dibujar no debe sacar al usuario del menú
                plt.close("all")
                ruta = None
                print("No se pudo generar el gráfico", numero, "->", type(error).__name__, error)
            if ruta is not None:
                print("Gráfico guardado en", ruta)

# --- Casos de prueba automáticos ---

def registrarCaso(resultados, nombre, obtenido, esperado):
    """Compara lo obtenido con lo esperado (resuelto a mano), lo muestra y lo guarda.
    Parámetros: resultados (list[bool]): lista donde se acumula True/False de cada verificación;
      nombre (str): descripción de lo que se verifica. obtenido: valor calculado por el programa.
      esperado: valor calculado a mano (informe o modelo.pdf).
    """
    coincide = (obtenido == esperado)
    if coincide:
        print("  OK    ", nombre)
    else:
        print("  FALLA ", nombre, "-> obtenido:", obtenido, " esperado:", esperado)
    resultados.append(coincide)

def probarModulos(resultados):
    """Casos 1 a 3: digrafos de dependencias (Tabla 2, G' con EVT y subgrafo del anexo)."""
    print("Caso 1 - LOGIX original (Tabla 2)")
    logix = cargarModulosArchivo("modulosLogix.json")
    if logix is not None:
        modulos = logix["modulos"]
        alcance = warshall(logix)
        entrada, salida = calcularGrados(logix)
        registrarCaso(resultados, "grados de salida", list(salida.values()), [3, 0, 1, 1, 2, 1, 1, 2, 3])
        registrarCaso(resultados, "grados de entrada", list(entrada.values()), [2, 1, 4, 1, 2, 1, 2, 1, 0])
        registrarCaso(resultados, "unos de A*", contarUnos(modulos, modulos, alcance), 40)
        registrarCaso(resultados, "módulos en ciclos", modulosEnCiclos(logix, alcance), ["INV", "ROB", "ASG", "RUT", "SEG"])
        registrarCaso(resultados, "grupos de ciclos", gruposDeCiclos(logix, alcance), [["INV", "ROB"], ["ASG", "RUT", "SEG"]])
        registrarCaso(resultados, "orden de migración (no existe)", ordenDeMigracion(logix), [])
        impacto = {}
        for codigo in ["INV", "ROB"]:
            for modulo in modulosAfectados(logix, alcance, codigo):
                impacto[modulo] = True
        registrarCaso(resultados, "impacto de s4 (INV y ROB)", len(impacto), 8)
        fichas = armarFichas(logix, alcance)
        registrarCaso(resultados, "más crítico", codigosEmpatados(ordenarBurbuja(fichas, "entrada", True), "entrada"), ["INV"])
        registrarCaso(resultados, "más acoplados",
                      sorted(codigosEmpatados(ordenarSeleccion(fichas, "salida", True), "salida")), ["PED", "REP"])
        registrarCaso(resultados, "densidad de alcance (40 / 81)", densidadDeAlcance(logix, alcance), 49.4)
    else:
        resultados.append(False)

    print("Caso 2 - LOGIX reestructurado con EVT")
    reestructurado = cargarModulosArchivo("modulosReestructurado.json")
    if reestructurado is not None:
        modulos = reestructurado["modulos"]
        alcance = warshall(reestructurado)
        registrarCaso(resultados, "unos de A*", contarUnos(modulos, modulos, alcance), 30)
        registrarCaso(resultados, "acíclico", modulosEnCiclos(reestructurado, alcance), [])
        registrarCaso(resultados, "orden de migración", ordenDeMigracion(reestructurado),
                      ["CLI", "EVT", "INV", "ROB", "SEG", "RUT", "ASG", "PED", "ENT", "REP"])
    else:
        resultados.append(False)

    print("Caso 3 - Subgrafo del anexo manual")
    anexo = cargarModulosArchivo("modulosAnexo.json")
    if anexo is not None:
        registrarCaso(resultados, "unos de A*", contarUnos(anexo["modulos"], anexo["modulos"], warshall(anexo)), 19)
    else:
        resultados.append(False)

def probarAlgebra(resultados):
    """Casos 4 a 6: sistema de la Tabla 6, equilibrios y camino mínimo (todo con Fraction)."""
    print("Caso 4 - Sistema de la Tabla 6")
    ampliada = cargarSistemaArchivo("sistemaTabla6.json")
    if ampliada is not None:
        registrarCaso(resultados, "determinante", determinante(ampliada), Fraction(11))
        clasificacion, solucion = gaussJordan(ampliada, False)
        registrarCaso(resultados, "clasificación", clasificacion, "compatible determinado")
        registrarCaso(resultados, "solución x, y, z", solucion, [Fraction(12), Fraction(20), Fraction(35)])
        registrarCaso(resultados, "costo inicial de B = (4, 6, 3) . (x, y, z)",
                      4 * solucion[0] + 6 * solucion[1] + 3 * solucion[2], Fraction(273))
    else:
        resultados.append(False)
    uno = Fraction(1)
    clasificacion, solucion = gaussJordan([[uno, uno, uno], [Fraction(2), Fraction(2), Fraction(3)]], False)
    registrarCaso(resultados, "caso límite x + y = 1 ; 2x + 2y = 3", clasificacion, "incompatible")
    clasificacion, solucion = gaussJordan([[uno, uno, uno], [Fraction(2), Fraction(2), Fraction(2)]], False)
    registrarCaso(resultados, "caso límite x + y = 1 ; 2x + 2y = 2", clasificacion, "compatible indeterminado")

    print("Caso 5 - Puntos de equilibrio (Punto 4)")
    alternativas = cargarCostosArchivo("costosAlternativas.json")
    if alternativas is not None:
        esperados = [["A", "B", "4.2", "462"], ["A", "C", "6", "660"], ["B", "C", "29.4", "1596"]]
        for par in esperados:
            clasificacion, solucion = puntoEquilibrio(alternativas[par[0]], alternativas[par[1]])
            registrarCaso(resultados, "equilibrio " + par[0] + "-" + par[1], solucion, [Fraction(par[2]), Fraction(par[3])])
        for anio in [3, 5, 10]:
            esperada = {3: "A", 5: "B", 10: "B"}[anio]
            registrarCaso(resultados, "más económica a los " + str(anio) + " años",
                          compararEnAnio(alternativas, anio)[0]["nombre"], esperada)
    else:
        resultados.append(False)
    iguales = {"X": {"fijo": Fraction(100), "anual": Fraction(50)}, "Y": {"fijo": Fraction(200), "anual": Fraction(50)}}
    clasificacion, solucion = puntoEquilibrio(iguales["X"], iguales["Y"])
    registrarCaso(resultados, "caso límite: mismo costo anual", clasificacion, "incompatible")

    print("Caso 6 - Camino mínimo (Tabla 5)")
    red = cargarRedArchivo("redDistribucion.json")
    if red is not None:
        distancia, camino = dijkstra(red, "D", "Z3", False)
        registrarCaso(resultados, "D a Z3", [distancia, camino], [16, ["D", "H2", "Z2", "Z3"]])
        registrarCaso(resultados, "ruta fija D-H1-Z1-Z3", longitudDeRuta(red, ["D", "H1", "Z1", "Z3"]), 23)
        registrarCaso(resultados, "destino inexistente", dijkstra(red, "D", "XX", False), (infinito, []))
    else:
        resultados.append(False)
    drones = cargarRedArchivo("redConDrones.json")
    if drones is not None:
        distancia, camino = dijkstra(drones, "D", "Z3", False)
        registrarCaso(resultados, "D a Z3 con corredor de drones", [distancia, camino], [14, ["D", "Z3"]])
    else:
        resultados.append(False)

def probarDecisionYRelaciones(resultados):
    """Casos 7 a 10: matriz de decisión, incidencia, trazabilidad y procesos (RF-42 a RF-58)."""
    print("Caso 7 - Matriz de decisión ponderada (Punto 4-i)")
    decision = cargarDecisionArchivo("decisionAlternativas.json")
    if decision is not None:
        valores = calcularPuntajes(decision, decision["pesos"])
        registrarCaso(resultados, "v = P.w", [valores["A"], valores["B"], valores["C"]],
                      [Fraction("2.25"), Fraction("3.8"), Fraction("3.1")])
        registrarCaso(resultados, "mejor alternativa", rankingDeAlternativas(valores)[0]["nombre"], "B")
        escenario = decision["escenarios"]["Prioridad a la evolucion"]
        valoresEscenario = calcularPuntajes(decision, escenario)
        registrarCaso(resultados, "escenario con C4 = 40 %", [valoresEscenario["A"], valoresEscenario["B"], valoresEscenario["C"]],
                      [Fraction("2.05"), Fraction("3.85"), Fraction("3.5")])
        registrarCaso(resultados, "peso de C4 desde el cual C supera a B",
                      pesoDeCambio(decision, "C4", "B", "C"), Fraction(19, 34))
    else:
        resultados.append(False)
    pesosMalos = validarPesos(["C1", "C2"], {"C1": 0.5, "C2": 0.6}, "prueba")
    registrarCaso(resultados, "pesos que no suman 1 se rechazan", pesosMalos, None)

    print("Caso 8 - Incidencia y superposición (Punto 1-i)")
    incidencia = cargarIncidenciaArchivo("incidenciaSolicitudes.json")
    if incidencia is not None:
        alcance, superposicion = calcularSuperposicion(incidencia)
        registrarCaso(resultados, "alcance directo a = S.u", list(alcance.values()), [2, 2, 4, 2, 1, 4])
        registrarCaso(resultados, "superposición (s3, s6)", superposicion["s3"]["s6"], 3)
        registrarCaso(resultados, "superposición (s1, s2)", superposicion["s1"]["s2"], 1)
    else:
        resultados.append(False)

    print("Caso 9 - Trazabilidad (Punto 5-g y 5-h)")
    trazabilidad = cargarTrazabilidadArchivo("trazabilidad.json")
    if trazabilidad is not None:
        rt = calcularTrazabilidad(trazabilidad)
        registrarCaso(resultados, "RT fila R2", [rt["R2"]["T1"], rt["R2"]["T2"], rt["R2"]["T3"]], [1, 1, 0])
        registrarCaso(resultados, "requerimientos sin prueba", filasNulas(trazabilidad["requerimientos"], trazabilidad["pruebas"], rt), ["R4"])
        registrarCaso(resultados, "componentes sin prueba", filasNulas(trazabilidad["componentes"], trazabilidad["pruebas"], trazabilidad["ct"]), ["C4"])
        involucrados, directas, reverificar = impactoDeComponente(trazabilidad, "C1")
        registrarCaso(resultados, "impacto de C1", [involucrados, directas, reverificar], [["R1", "R2"], ["T1"], ["T1", "T2"]])
    else:
        resultados.append(False)

    print("Caso 10 - Procesos de atención de pedidos (Punto 2-h a 2-j)")
    actual = cargarProcesoArchivo("procesoPedido.json")
    nuevo = cargarProcesoArchivo("procesoReingenierizado.json")
    if actual is not None and nuevo is not None:
        resumenActual = resumirProceso(actual)
        registrarCaso(resultados, "cantidad de caminos simples", len(resumenActual), 2)
        registrarCaso(resultados, "camino normal", [resumenActual[0]["minutos"], resumenActual[0]["manuales"]], [65, 53])
        registrarCaso(resultados, "porcentaje manual del normal", resumenActual[0]["porcentaje"], Fraction(53, 65))
        registrarCaso(resultados, "camino urgente", [resumenActual[1]["minutos"], resumenActual[1]["manuales"]], [45, 33])
        registrarCaso(resultados, "ciclo V-Q", modulosEnCiclos(armarSistemaProceso(actual), warshall(armarSistemaProceso(actual))), ["V", "Q"])
        resumenNuevo = resumirProceso(nuevo)
        registrarCaso(resultados, "proceso reingenierizado", [resumenNuevo[0]["minutos"], resumenNuevo[0]["manuales"]], [14, 0])
        registrarCaso(resultados, "proceso reingenierizado acíclico",
                      modulosEnCiclos(armarSistemaProceso(nuevo), warshall(armarSistemaProceso(nuevo))), [])
        registrarCaso(resultados, "reducción (65 - 14) / 65", Fraction(65 - 14, 65) * 100, Fraction(5100, 65))
    else:
        resultados.append(False)

def probarConteoYOrdenamiento(resultados):
    """Casos 11 a 13: combinatoria, ciclo de tres módulos, ordenamiento y búsqueda."""
    print("Caso 11 - Conteo (Puntos 1-h, 2-k y 5-i)")
    registrarCaso(resultados, "C(6,4)", combinaciones(6, 4), 15)
    registrarCaso(resultados, "6^5 (variaciones con repetición)", variacionesConRepeticion(6, 5), 7776)
    registrarCaso(resultados, "2 . 6^4", 2 * variacionesConRepeticion(6, 4), 2592)
    registrarCaso(resultados, "C(6,2)", combinaciones(6, 2), 15)
    registrarCaso(resultados, "V(6,2)", variaciones(6, 2), 30)
    registrarCaso(resultados, "5!", permutaciones(5), 120)
    registrarCaso(resultados, "V(5,3)", variaciones(5, 3), 60)
    registrarCaso(resultados, "C(5,3)", combinaciones(5, 3), 10)
    registrarCaso(resultados, "caso límite C(3,5)", combinaciones(3, 5), 0)

    print("Caso 12 - Ciclo de tres módulos (A->B, B->C, C->A)")
    triangulo = armarSistema(["A", "B", "C"], {"A": ["B"], "B": ["C"], "C": ["A"]})
    registrarCaso(resultados, "un solo grupo", gruposDeCiclos(triangulo, warshall(triangulo)), [["A", "B", "C"]])
    registrarCaso(resultados, "dependencia inexistente se rechaza", armarSistema(["A"], {"A": ["Z"]}), None)

    print("Caso 13 - Ordenamiento y búsqueda")
    registros = []
    for valor in [5, 2, 9, 1, 7, 3]:
        registros.append({"valor": valor})
    burbuja = ordenarBurbuja(registros, "valor", False)
    seleccion = ordenarSeleccion(registros, "valor", False)
    registrarCaso(resultados, "burbuja ascendente", [r["valor"] for r in burbuja], [1, 2, 3, 5, 7, 9])
    registrarCaso(resultados, "selección ascendente", [r["valor"] for r in seleccion], [1, 2, 3, 5, 7, 9])
    registrarCaso(resultados, "burbuja descendente", [r["valor"] for r in ordenarBurbuja(registros, "valor", True)], [9, 7, 5, 3, 2, 1])
    registrarCaso(resultados, "el original no se modifica", [r["valor"] for r in registros], [5, 2, 9, 1, 7, 3])
    registrarCaso(resultados, "búsqueda binaria (está)", busquedaBinaria(seleccion, "valor", 7), 4)
    registrarCaso(resultados, "búsqueda binaria (no está)", busquedaBinaria(seleccion, "valor", 4), -1)
    registrarCaso(resultados, "búsqueda secuencial (está)", busquedaSecuencial(registros, "valor", 9), 2)
    registrarCaso(resultados, "búsqueda secuencial (no está)", busquedaSecuencial(registros, "valor", 4), -1)
    registrarCaso(resultados, "lista vacía", [ordenarBurbuja([], "valor", False), busquedaBinaria([], "valor", 1)], [[], -1])

def ejecutarCasosDePrueba():
    """Corre todos los casos de prueba y muestra cuántas verificaciones pasaron."""
    resultados = []
    print()
    print("Casos de prueba (los archivos JSON deben estar en la carpeta del programa)")
    inicio = time.time()
    probarModulos(resultados)
    probarAlgebra(resultados)
    probarDecisionYRelaciones(resultados)
    probarConteoYOrdenamiento(resultados)
    if hayGraficos:
        print("Caso 14 - Gráficos (opcional)")
        carpetaTemporal = tempfile.mkdtemp()
        plt.switch_backend("Agg")           # sin ventanas: solo se guarda el archivo
        rutaImagen = generarGrafico(1, carpetaTemporal, False)
        registrarCaso(resultados, "se creó el gráfico de los digrafos", rutaImagen is not None and os.path.isfile(rutaImagen), True)
    aprobados = 0
    for coincide in resultados:
        if coincide:
            aprobados = aprobados + 1
    print()
    print("Resultado:", aprobados, "de", len(resultados), "verificaciones correctas",
          "(" + str(round(time.time() - inicio, 2)) + " s).")

# --- Programa principal (menú) ---

def mostrarMenu():
    """Imprime el menú agrupado por tema (los números de RF indican el requisito que cubre)."""
    print()
    print("================ LOGIX-Analyzer v2.0 ================")
    print(" Módulos y dependencias")
    print("  1. Cargar módulos desde archivo JSON (RF-01, RF-03 a RF-06)")
    print("  2. Cargar módulos por teclado (RF-02 a RF-05)")
    print("  3. Analizar el sistema cargado (RF-07 a RF-19, RF-35 y RF-36)")
    print("  4. Ver módulos afectados por un cambio (RF-14 a RF-16)")
    print("  8. Consultar un módulo (búsqueda y rankings)")
    print(" Modelos matemáticos")
    print("  5. Resolver un sistema de ecuaciones (RF-22 a RF-25)")
    print("  6. Puntos de equilibrio entre alternativas (RF-28 a RF-30)")
    print("  7. Camino mínimo en la red de distribución (RF-32 a RF-34)")
    print(" 10. Matriz de decisión ponderada y sensibilidad (RF-42 a RF-47)")
    print(" 11. Incidencia de solicitudes y trazabilidad (RF-48 a RF-52)")
    print(" 12. Procesos de atención de pedidos (RF-53 a RF-58)")
    print(" 13. Conteo: combinaciones, variaciones, permutaciones (RF-59 a RF-62)")
    print(" Herramientas")
    print("  9. Ejecutar los casos de prueba")
    print(" 14. Generar gráficos ( necesita matplotlib y networkx)")
    print("  0. Salir")

def elegirOrigenDeDatos(mensaje):
    """Pregunta si los datos se cargan desde archivo o por teclado y devuelve 'a' o 't'.
    Parámetros: mensaje (str): texto de la pregunta.
    Devuelve: str: 'a' para archivo, 't' para teclado (cualquier otra respuesta es teclado).
    """
    forma = input(mensaje + " desde archivo (a) o por teclado (t)? ").strip().lower()
    if forma == "a":
        return "a"
    return "t"

def main():
    """Programa principal: muestra el menú y ejecuta la opción elegida con match/case."""
    sistema = None
    opcion = ""
    while opcion != "0":
        mostrarMenu()
        opcion = input("Opción: ").strip()
        match opcion:
            case "1":
                sistema = cargarModulosArchivo(pedirNombreArchivo("modulosLogix.json"))
                if sistema is not None:
                    print("Se cargaron", len(sistema["modulos"]), "módulos:", sistema["modulos"])
            case "2":
                sistema = cargarModulosTeclado()
            case "3" | "4" | "8":
                if sistema is None:
                    print("Primero cargue los módulos (opción 1 o 2).")
                else:
                    match opcion:
                        case "3":
                            analizarSistema(sistema)
                        case "4":
                            mostrarAfectados(sistema, warshall(sistema))
                        case "8":
                            consultarModulo(sistema)
            case "5":
                match elegirOrigenDeDatos("¿Cargar el sistema"):
                    case "a":
                        ampliada = cargarSistemaArchivo(pedirNombreArchivo("sistemaTabla6.json"))
                    case _:
                        ampliada = cargarSistemaTeclado()
                if ampliada is not None:
                    resolverSistema(ampliada)
            case "6":
                match elegirOrigenDeDatos("¿Cargar las alternativas"):
                    case "a":
                        alternativas = cargarCostosArchivo(pedirNombreArchivo("costosAlternativas.json"))
                    case _:
                        alternativas = cargarCostosTeclado()
                if alternativas is not None:
                    mostrarEquilibrios(alternativas)
            case "7":
                mostrarCaminoMinimo()
            case "9":
                ejecutarCasosDePrueba()
            case "10":
                decision = cargarDecisionArchivo(pedirNombreArchivo("decisionAlternativas.json"))
                if decision is not None:
                    mostrarDecision(decision)
            case "11":
                analizarIncidencia(pedirNombreArchivo("incidenciaSolicitudes.json"))
                analizarTrazabilidad(pedirNombreArchivo("trazabilidad.json"))
            case "12":
                mostrarComparacionProcesos()
            case "13":
                mostrarConteo()
            case "14":
                generarGraficos()
            case "0":
                pass
            case _:
                print("Opción inválida.")
    print("Fin del programa.")


main()
