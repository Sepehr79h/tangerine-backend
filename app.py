from flask import Flask, request, jsonify
import os
import subprocess
from flask_cors import CORS
from collections import defaultdict
from openai import OpenAI
from nbformat import read
from dotenv import load_dotenv
import nbformat
import ast

load_dotenv()

app = Flask(__name__)
CORS(app)

# Directory where uploaded notebooks will be saved
UPLOAD_FOLDER = 'notebooks'
OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def home():
    return "Notebook processing API. Use /upload-notebook to upload notebooks."
    
def process_notebooks(folder_name):
    subprocess.run(["node", "Jupyter-Notebook-Project/generate_python_files_from_nbs.js", folder_name])
    subprocess.run(["python", "Jupyter-Notebook-Project/generate_json_dictionaries_all_files.py", folder_name])
    subprocess.run(["node", "Jupyter-Notebook-Project/analyze_notebooks.js", folder_name])
    subprocess.run(["python", "Jupyter-Notebook-Project/generate_graphs_cell_level.py", folder_name])

@app.route('/get-tree-structure', methods=['POST'])
def get_tree_structure():
    print('Processing tree structure in backend...')
    data = request.json
    filepath = data['filepath']
    frontend_path = '../tangerine'
    filename = filepath.split('.')[0]
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    notebook_path = os.path.join(frontend_path, filepath)
    new_notebook_path = os.path.join(folder_path, filepath)
    subprocess.run(['cp', notebook_path, new_notebook_path])

    process_notebooks(folder_path)    
    gv_path = os.path.join(folder_path, filename + '_new_labels.gv')
    try:
        with open(gv_path, 'r') as file:
            lines = file.readlines()
        nodes = []
        edges = []
        for line in lines:
            if '->' in line:
                source, target = line.strip().split('->')
                edges.append({'source': source.strip(), 'target': target.strip()})
            elif '[' in line:
                node_id = line.split('[', 1)[0].strip()
                nodes.append({'id': node_id})
        #remove duplicate nodes
        nodes = [dict(t) for t in {tuple(d.items()) for d in nodes}]
        treeData = {'nodes': nodes, 'edges': edges}
        print(treeData)
        print('Tree structure processed successfully')
        treeData = enrich_tree_data(treeData, notebook_path)
        #print(treeData)
        #breakpoint()
        treeData = get_grouped_tree_structure(treeData)
        print(treeData)
        return jsonify(treeData)
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404
    
def enrich_tree_data(treeData, notebook_path):
    # Load the notebook
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)
    
    # Initialize the result dictionary
    result = {"cells": []}
    
    # Iterate through the notebook cells
    for cell in nb.cells:
        if cell.cell_type == 'code':
            # Extract the code and the execution count (cell_id in this context)
            cell_data = {
                "cell_id": str(cell.execution_count),
                "code": cell.source.split('\n')  # Splitting source code by newline to get a list of code lines
            }
            result['cells'].append(cell_data)
    
    gpt_input = str(result | treeData)
    #breakpoint()
    client = OpenAI(
        api_key=OPENAI_API_KEY,#os.environ.get("CUSTOM_ENV_NAME"),
    )
    response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {
        "role": "system",
        "content": "You will be given a json that contains the python code of the cells in a jupyter notebook file, and the nodes and edges to show the dependency between the cells which will be used for a ReactFlow visualization. Update the nodes key in the JSON so that it assigns the cell to the appropriate parentNode and adds a descriptive titles to to represent what each node is doing. Ensure the output is strictly in JSON format, suitable for direct use in ReactFlow, without any additional explanations, strings, or context. Use the following format:\n\n{\n  \"nodes\": [\n    {\"id\": \"import\", \"data\": {\"label\": \"Data Import\"}},\n    {\"id\": \"wrangle\", \"data\": {\"label\": \"Data Wrangling\"}},\n    {\"id\": \"explore\", \"data\": {\"label\": \"Data Exploration\"}},\n    {\"id\": \"model\", \"data\": {\"label\": \"Model Building\"}},\n    {\"id\": \"evaluate\", \"data\": {\"label\": \"Model Evaluation\"}},\n    {\"id\": \"<cell_id>\", \"data\": {\"label\": \"<1-5 word descriptive title explaining what this code cell is doing>\"}, \"parentNode\": \"<import, wrangle, explore, model, evaluate>\"}\n  ]\n}"
        },
        {
        "role": "user",
        "content": gpt_input
        },
    ],
    temperature=0,
    max_tokens=4095,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0
    )
    #breakpoint()
    output = response.choices[0].message.content
    output = ast.literal_eval(output)
    output["edges"] = treeData["edges"]
    #breakpoint()

    return output

    
@app.route('/get-node-category', methods=['POST'])
def get_node_category():
    print("Getting node category on backend...")
    client = OpenAI(
        api_key=OPENAI_API_KEY,#os.environ.get("CUSTOM_ENV_NAME"),
    )
    data = request.json
    #breakpoint()
    filepath = data['filepath']
    cell_id = int(data['cellIndex'])
    # get the code from the cell in the notebook with filepath
    frontend_path = '../tangerine'
    file_path = os.path.join(frontend_path, filepath)
    # Ensure the file exists
    if not os.path.exists(file_path):
        return {"error": "File not found"}, 404
    # Read the notebook
    with open(file_path, 'r', encoding='utf-8') as f:
        nb = read(f, as_version=4)
    # Extract the code from the specified cell
    code = None
    for cell in nb.cells:
        if cell.cell_type == 'code' and cell.execution_count == cell_id:
            code = cell.source
            break
    if code is None:
        print("no execution count found for cell: ", cell_id)
        return 'other'
    #breakpoint()
    #code = data['code']
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
            "role": "system",
            "content": "You will be provided with Python code, and your task is to categorize the code as one of the following categories:\n- IMPORT\n- DATA WRANGLE\n- EXPLORE\n- MODEL\n- EVALUATE. Return the category as one of the following strings (in lowercase): import, wrangle, explore, model, evaluate"
            },
            {
            "role": "user",
            "content": code
            },
        ],
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return response.choices[0].message.content
    #return jsonify(response)

@app.route('/get-node-header', methods=['POST'])
def get_node_header():
    print("Getting node headers on backend...")
    client = OpenAI(
        api_key=OPENAI_API_KEY,#os.environ.get("CUSTOM_ENV_NAME"),
    )
    data = request.json
    #breakpoint()
    filepath = data['filepath']
    cell_id = int(data['cellIndex'])
    # get the code from the cell in the notebook with filepath
    frontend_path = '../tangerine'
    file_path = os.path.join(frontend_path, filepath)
    # Ensure the file exists
    if not os.path.exists(file_path):
        return {"error": "File not found"}, 404
    # Read the notebook
    with open(file_path, 'r', encoding='utf-8') as f:
        nb = read(f, as_version=4)
    # Extract the code from the specified cell
    code = None
    for cell in nb.cells:
        if cell.cell_type == 'code' and cell.execution_count == cell_id:
            code = cell.source
            break
    if code is None:
        print("no execution count found for cell: ", cell_id)
        return 'other'
    #breakpoint()
    #code = data['code']
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
            "role": "system",
            "content": "You will be provided with Python code, and your task is to provide a header for the code, that is no longer than 3 words. Return the header as a string."
            },
            {
            "role": "user",
            "content": code
            },
        ],
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return response.choices[0].message.content
    #return jsonify(response)

def update_parentNode(data):
    for node in data['nodes']:
        if 'parentNode' in node:
            node['categoryColor'] = node['parentNode']
            del node['parentNode']
    data['nodes'] = [node for node in data['nodes'] if 'categoryColor' in node]
    return data

def create_node_groups(data):
    groups = {}
    current_group = None

    #store the nodes where id is a digit first
    cell_nodes = [node for node in data['nodes'] if node['id'].isdigit()]
    sorted_nodes = sorted(cell_nodes, key=lambda x: int(x['id']))

    # creates a group for each set of sequential nodes (id is sequential) that have the same parentNode
    for node in sorted_nodes:
        parent = node['categoryColor']
        if parent != current_group:
            current_group = parent
            group_name = "group_"+node["id"]
            groups[group_name] = [node]
        else:
            groups[group_name].append(node)
    
    # drop groups with 1 or 0 nodes
    groups = {k: v for k, v in groups.items() if len(v) > 1}
    return groups

def update_nodes_with_groups(data, groups):
    for group in groups:
        # create a new node for the group
        group_node = {
            'id': group,
            'data': {
                'label': group
            },
            'categoryColor': groups[group][0]['categoryColor']
        }
        data['nodes'].append(group_node)

        # add edges between the group and its nodes
        for node in groups[group]:
            # change parentNode to the group in data['nodes']
            node['parentNode'] = group
            #find the node in data['nodes'] and update it
            for n in data['nodes']:
                if n['id'] == node['id']:
                    n['parentNode'] = group
                    break     
    return data

def update_edges_with_groups(data, groups):
    # Initialize a set for the new edges to avoid duplicates
    new_edges = set()

    # Iterate over the existing edges to construct new edges based on group membership
    for edge in data['edges']:
        source, target = edge['source'], edge['target']
        source_group, target_group = None, None

        # Determine if the source node is part of any group
        for group, nodes in groups.items():
            if any(node['id'] == source for node in nodes):
                source_group = group
                break

        # Determine if the target node is part of any group
        for group, nodes in groups.items():
            if any(node['id'] == target for node in nodes):
                target_group = group
                break

        # Create new edges based on the group membership of source and target nodes
        if source_group and target_group and source_group != target_group:
            new_edges.add((source_group, target_group))
        if source_group and source_group != target_group:
            new_edges.add((source_group, target))
        if target_group and source_group != target_group:
            new_edges.add((source, target_group))

    # Add the new edges to the data['edges'], ensuring no duplicates are introduced
    for edge in new_edges:
        if not any(e['source'] == edge[0] and e['target'] == edge[1] for e in data['edges']):
            data['edges'].append({'source': edge[0], 'target': edge[1]})

    return data

def get_grouped_tree_structure(data):
    data = update_parentNode(data)
    groups = create_node_groups(data)
    data = update_nodes_with_groups(data, groups)
    data = update_edges_with_groups(data, groups)
    return data

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    # #process_notebooks(UPLOAD_FOLDER)
    # test_parse_gv_file('nb_1191_new_labels.gv')
    #get_tree_structure('nb_1194.ipynb')

    app.run(debug=True, port=5002, use_reloader=False)
