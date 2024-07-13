import networkx as nx
import os
from flask import Flask, render_template, request, jsonify, send_file
import gzip
from io import BytesIO

app = Flask(__name__)

# Crear un grafo vacío
G = nx.Graph()

# Ruta para la carpeta de uploads
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


node_counter = 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_node', methods=['POST'])
def add_node():
    global node_counter
    data = request.json
    G.add_node(node_counter, pos=(data['lat'], data['lng']))
    node_counter += 1
    return jsonify(success=True, node_id=node_counter - 1)

@app.route('/add_edge', methods=['POST'])
def add_edge():
    data = request.json
    node1 = int(data['node1'])  # Convertir a entero
    node2 = int(data['node2'])  # Convertir a entero
    weight = float(data['weight'])  # Convertir a flotante

    # Verificar si la arista ya existe
    if G.has_edge(node1, node2):
        return jsonify(error="La arista ya existe"), 400

    G.add_edge(node1, node2, weight=weight)
    return jsonify(success=True)


@app.route('/get_edge_weight', methods=['POST'])
def get_edge_weight():
    data = request.json
    weight = G[int(data['node1'])][int(data['node2'])]['weight']  # Convertir a enteros
    return jsonify(weight=weight)

@app.route('/shortest_path', methods=['POST'])
def shortest_path():
    data = request.json
    print("Datos recibidos:", data)  # Imprimir los datos recibidos
    start = int(data['start'])  # Convertir a entero
    end = int(data['end'])     # Convertir a entero
    print("Índices convertidos:", start, end)  # Imprimir los índices convertidos
    try:
        path = nx.dijkstra_path(G, start, end)
        displayPath(path) # Llamamos a displayPath para mostrar la ruta en consola
    except nx.NetworkXNoPath:
        return jsonify(error="No existe un camino entre los nodos especificados"), 400  # Error 400: Bad Request
    return jsonify(path=path)

def displayPath(path):  # Función para mostrar la ruta en consola
    print("Ruta más corta:")
    for i in range(len(path) - 1):
        node1 = path[i]
        node2 = path[i + 1]
        weight = G[node1][node2]['weight']
        print(f"{node1} --- {weight} ---> {node2}")


@app.route('/export_graph', methods=['GET'])
def export_graph():
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'grafo.txt')
    with open(filepath, 'w') as file:
        for node, data in G.nodes(data=True):
            file.write(f"{data['pos'][0]} {data['pos'][1]}\n")
        for node1, node2, data in G.edges(data=True):
            file.write(f"{node1} {node2} {data['weight']}\n")

    return send_file(filepath, as_attachment=True)

@app.route('/import_graph', methods=['POST'])
def import_graph():
    global node_counter
    node_counter = 0

    file = request.files['file']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    G.clear()
    nodes_data = []  # Lista para almacenar los datos de los nodos
    edges_data = []  # Lista para almacenar los datos de las aristas

    with open(filepath, 'r') as f:
        lines = f.readlines()
        # Procesamos primero las aristas para crear los nodos necesarios en el grafo
        for line in lines:
            parts = line.strip().split()
            if len(parts) == 3:  # Arista
                node1_index_in_file = int(parts[0])
                node2_index_in_file = int(parts[1])
                weight = float(parts[2])
                edges_data.append((node1_index_in_file, node2_index_in_file, weight))  # Almacenar datos de la arista

        # Luego, agregamos los nodos
        for i, line in enumerate(lines):
            parts = line.strip().split()
            if len(parts) == 2:  # Nodo
                lat = float(parts[0])
                lng = float(parts[1])
                G.add_node(i, pos=(lat, lng))
                node_counter += 1
                nodes_data.append((lat, lng))  # Almacenar datos del nodo

        # Finalmente, agregamos las aristas utilizando los índices correctos
        for node1_index_in_file, node2_index_in_file, weight in edges_data:
            try:
                # Manejo de errores para coordenadas no exactas:
                node1 = next(
                    (node for node, data in G.nodes(data=True)
                     if abs(data['pos'][0] - nodes_data[node1_index_in_file][0]) < 0.000001 and
                        abs(data['pos'][1] - nodes_data[node1_index_in_file][1]) < 0.000001),
                    None  # Valor predeterminado si no se encuentra el nodo
                )
                node2 = next(
                    (node for node, data in G.nodes(data=True)
                     if abs(data['pos'][0] - nodes_data[node2_index_in_file][0]) < 0.000001 and
                        abs(data['pos'][1] - nodes_data[node2_index_in_file][1]) < 0.000001),
                    None
                )

                if node1 is None or node2 is None:
                    raise ValueError(f"Node not found: {node1_index_in_file} or {node2_index_in_file}")

                # Corregir el índice de los nodos en las aristas
                G.add_edge(node1_index_in_file, node2_index_in_file, weight=weight)  # Restar 1 a los índices
            except (StopIteration, ValueError, IndexError) as e:
                print(f"Error al procesar la arista: {node1_index_in_file} {node2_index_in_file} {weight}. Error: {e}")
                continue  # Saltar la línea si hay un error

    # Extraer los datos del grafo y construir el diccionario de respuesta
    graph_data = get_graph().get_json()

    return jsonify(success=True, graph=graph_data)


@app.route('/get_graph', methods=['GET'])
def get_graph():
    nodes = {node: {"pos": list(data['pos'])} for node, data in G.nodes(data=True)}
    edges = [(u, v, data["weight"]) for u, v, data in G.edges(data=True)]
    return jsonify({"nodes": nodes, "edges": edges})


if __name__ == '__main__':
    app.run(debug=True)
