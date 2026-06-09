from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import heapq
from datos_fotos import fotos_db

# Iniciamos la aplicación web y habilitamos CORS para que Bubble no sea bloqueado
app = Flask(__name__)
CORS(app)

def cargar_mapa(ruta_archivo):
    try:
        with open('/home/etamot/mysite/mapa.json', 'r', encoding='utf-8') as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        return "Error: No se encontró el archivo mapa.json."

def calcular_ruta_dijkstra(grafo, origen, destino):
    if origen not in grafo or destino not in grafo:
        return ["Error: Origen o destino no existen en el mapa"]

    cola = [(0, origen)]
    distancias = {nodo: float('inf') for nodo in grafo}
    distancias[origen] = 0
    padres = {nodo: None for nodo in grafo}

    while cola:
        distancia_actual, nodo_actual = heapq.heappop(cola)

        if nodo_actual == destino:
            break
        if distancia_actual > distancias[nodo_actual]:
            continue

        for vecino, datos_vecino in grafo[nodo_actual].items():
            peso = datos_vecino["distancia"]
            nueva_distancia = distancia_actual + peso

            if nueva_distancia < distancias[vecino]:
                distancias[vecino] = nueva_distancia
                padres[vecino] = nodo_actual
                heapq.heappush(cola, (nueva_distancia, vecino))

    ruta = []
    nodo = destino
    while nodo is not None:
        ruta.append(nodo)
        nodo = padres[nodo]

    ruta.reverse()
    return ruta if ruta[0] == origen else ["Error: Camino no encontrado"]

# ==========================================
# LA RUTA DE LA API (El puente con Bubble)
# ==========================================
@app.route('/calcular_ruta', methods=['POST'])
def calcular():
    # 1. Recibimos los datos que nos enviará Bubble
    datos = request.json
    origen = datos.get('origen')
    destino = datos.get('destino')

    # 2. Cargamos el mapa y calculamos
    mi_grafo = cargar_mapa('mapa.json')

    # Manejo de error si el mapa no carga
    if isinstance(mi_grafo, str):
        return jsonify({"error": mi_grafo}), 500

    ruta = calcular_ruta_dijkstra(mi_grafo, origen, destino)

    # Manejo de error si la ruta falla
    if len(ruta) > 0 and "Error" in ruta[0]:
        return jsonify({"error": ruta[0]}), 400

    # Listas que enviaremos a Bubble
    lista_fotos = []
    lista_pitches = []
    lista_yaws = []
    lista_distancias = []

    # 4. RECORREMOS LA RUTA PARA ARMAR LAS LISTAS
    for i in range(len(ruta)):
        nodo_actual = ruta[i]

        # Guardamos la foto del nodo actual
        lista_fotos.append(fotos_db.get(nodo_actual, "https://pannellum.org/images/alma.jpg"))

        # Buscamos el pitch y yaw para la flecha
        if i < len(ruta) - 1:
            siguiente_nodo = ruta[i + 1]

            # Buscamos en el json: mi_grafo["origen"]["destino"]
            # Usamos .get() por seguridad en caso de que falte el dato en el JSON
            datos_conexion = mi_grafo[nodo_actual].get(siguiente_nodo, {})
            pitch = datos_conexion.get("pitch", 0)
            yaw = datos_conexion.get("yaw", 0)
            distancia = datos_conexion.get("distancia", 0)

            lista_pitches.append(pitch)
            lista_yaws.append(yaw)
            lista_distancias.append(distancia)
        else:
            # Si es el último nodo, rellenamos con 0 para que todas las listas midan lo mismo
            lista_pitches.append(0)
            lista_yaws.append(0)
            lista_distancias.append(0)

    # 5. Le devolvemos la respuesta a Bubble con TODAS las listas
    return jsonify({
        "ruta": ruta,
        "fotos": lista_fotos,
        "pitches": lista_pitches,
        "yaws": lista_yaws,
        "distancias": lista_distancias
    })

if __name__ == '__main__':
    # Encendemos el servidor en el puerto 5000
    print("🚀 Servidor API iniciado. Esperando conexiones de Bubble...")
    app.run(debug=True, port=5000)