# AE4-MD-IR-PE
This is the repository where Rodrigo Nahuel Kirsch and Federico Molina made the AE4

Programa que exportaba de OpenStreetMap la informacion de las calles en formato json 
Armaba un grafo gracias a convertir.py de mas de 11mil nodos, en navegador.py se usaba dijkstra para
recorrer de a->b con el camino mas corto los pesos se sacaban de la formula de haversine mediante la lat y long
, que se traia desde OpenStreetMap los pesos se expresan en metros. Tiene implementada la funcion de graficar el recorrido.