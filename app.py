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
from grouping import get_grouped_tree_structure
from suggestions import get_suggestions_input
from update import get_updated_tree
import json

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

@app.route('/get-add-node-tree', methods=['POST'])
def get_add_node_tree():
    data = request.json
    filepath = data['filepath']
    curr_tree = data['currTree']
    new_node = data['newNode']
    initial_tree = get_initial_tree(filepath)
    updated_tree = get_updated_tree(curr_tree, new_node, initial_tree)
    breakpoint()

@app.route('/get-suggestions', methods=['POST'])
def get_node_suggestions():
    data = request.json
    node_id = data['nodeId']
    frontend_path = '../tangerine'
    filepath = data['filepath']
    notebook_path = os.path.join(frontend_path, filepath)
    edges = data['edges']
    suggestions_input = get_suggestions_input(node_id, notebook_path, edges)
    # return [
    #   { "id": "suggestion1", "label": 'Next Step A' },
    #   { "id": "suggestion1", "label": 'Next Step A' },
    #   { "id": "suggestion1", "label": 'Next Step A' }
    # ]
    client = OpenAI(
        api_key=OPENAI_API_KEY,
    )
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {
            "role": "system",
            # "content": "You will be given a json that corresponds to the python code of the cells in a jupyter notebook file that is performing Exploratory Data Analysis (EDA). \n\nYour job is to provide 3 suggestions (each in the form of a code cell) as next possible steps to take after a code cell. Each suggestion should be a continuation of the last cell in the json and the suggestions should have be dependent on the last cell of the json. Suggestions should be independent of each other and not have any dependencies between them as they are alternative paths of exploration.  The suggestions should have a descriptive title, the code cell for that suggestion, and a category corresponding to the EDA stage that the code falls under. \n\nUse the following format:\n\n[\n            {'id': '<suggestion_1>',\n            'label': '<1-5 word descriptive title explaining what this code cell is doing>',\n            'code': ['line1',\n                     'keep adding lines of code here',],\n            'category': '<import, wrangle, explore, model, evaluate>'\n            },\n            {'id': '<suggestion_2>',\n            'label': '<1-5 word descriptive title explaining what this code cell is doing>',\n            'code': ['line1',\n                     'keep adding lines of code here',],\n            'category': '<import, wrangle, explore, model, evaluate>'\n            },\n            {'id': '<suggestion_3>',\n            'label': '<1-5 word descriptive title explaining what this code cell is doing>',\n            'code': ['line1',\n                     'keep adding lines of code here',],\n            'category': '<import, wrangle, explore, model, evaluate>'\n            },           \n]\n\n"
            "content": "You will be given a json that corresponds to the python code of the cells in a jupyter notebook file that is performing Exploratory Data Analysis (EDA). \n\nYour job is to provide 3 suggestions as next possible steps to take after a code cell. Each suggestion should be a continuation of the last cell in the json and the suggestions should have be dependent on the last cell of the json. Suggestions should be independent of each other and not have any dependencies between them as they are alternative paths of exploration.  The suggestions should have a descriptive title and a category corresponding to the EDA stage that the code falls under. \n\nUse the following format:\n\n[\n            {'id': '<suggestion_1>',\n            'label': '<1-5 word descriptive title explaining what this code cell is doing>',\n            'category': '<import, wrangle, explore, model, evaluate>'\n            },\n            {'id': '<suggestion_2>',\n            'label': '<1-5 word descriptive title explaining what this code cell is doing>',\n            'category': '<import, wrangle, explore, model, evaluate>'\n            },\n            {'id': '<suggestion_3>',\n            'label': '<1-5 word descriptive title explaining what this code cell is doing>',\n            'category': '<import, wrangle, explore, model, evaluate>'\n            },           \n]\n\n"
            },
            {
            "role": "user",
            "content": str(suggestions_input)
            },
        ],
        temperature=0,
        max_tokens=4095,
        top_p=0,
        frequency_penalty=0,
        presence_penalty=0
    )
    output = response.choices[0].message.content
    print(output)
    return ast.literal_eval(output)

@app.route('/get-suggestions-code', methods=['POST'])
def get_node_suggestions_code():
    data = request.json
    node_id = data['nodeId']
    frontend_path = '../tangerine'
    filepath = data['filepath']
    notebook_path = os.path.join(frontend_path, filepath)
    edges = data['edges']
    suggestion = data['suggestion']
    suggestions_input = get_suggestions_input(node_id, notebook_path, edges)
    client = OpenAI(
        api_key=OPENAI_API_KEY,
    )
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {
            "role": "system",
            "content": "You will be given a json that contains two keys. First, a 'cells' key that contains the python code of the cells in a jupyter notebook file that is performing Exploratory Data Analysis (EDA). Second, a 'suggestion' key that contains a description of what the next cell in the jupyter notebook should be. \n\nYour job is to provide is to provide the code for this next cell. This code should be a continuation of the last cell in the json it should be dependent on that cell.\n\nUse the following format:\n\n{'code': ['line1', 'keep adding lines of code here',]\n\n"
            },
            {
            "role": "user",
            "content": str(suggestions_input | {'suggestion': suggestion })
            },
        ],
        temperature=0,
        max_tokens=4095,
        top_p=0,
        frequency_penalty=0,
        presence_penalty=0
    )
    output = response.choices[0].message.content
    print(output)
    return ast.literal_eval(output)


def get_initial_tree(filepath):
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
        return treeData
    except FileNotFoundError:
        return {'error': 'File not found'}, 404

@app.route('/get-tree-structure', methods=['POST'])
def get_tree_structure():
    print('Processing tree structure in backend...')
    data = request.json
    filepath = data['filepath']
    frontend_path = '../tangerine'
    notebook_path = os.path.join(frontend_path, filepath)
    try:
        treeData = get_initial_tree(filepath)
        print('1')
        print(treeData)
        print('Tree structure processed successfully')
        # treeData = enrich_tree_data(treeData, notebook_path)
        # print('2')
        # print(treeData)
        # treeData = get_grouped_tree_structure(treeData)
        # print('3')
        # print(treeData)
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
    
    #breakpoint()
    
    # gpt_input = str(result | treeData)
    # breakpoint()
    # client = OpenAI(
    #     api_key=OPENAI_API_KEY,#os.environ.get("CUSTOM_ENV_NAME"),
    # )
    # response = client.chat.completions.create(
    # model="gpt-4-0125-preview",
    # response_format={"type": "json_object"},
    # messages=[
    #     {
    #     "role": "system",
    #     "content": "You will be given a json that contains the python code of the cells in a jupyter notebook file, and the nodes and edges to show the dependency between the cells which will be used for a ReactFlow visualization. Update the nodes key in the JSON so that it assigns the cell to the appropriate parentNode and adds a descriptive titles to to represent what each node is doing. Ensure the output is strictly in JSON format, suitable for direct use in ReactFlow, without any additional explanations, strings, or context. Use the following format:\n\n{\n  \"nodes\": [\n    {\"id\": \"import\", \"data\": {\"label\": \"Data Import\"}},\n    {\"id\": \"wrangle\", \"data\": {\"label\": \"Data Wrangling\"}},\n    {\"id\": \"explore\", \"data\": {\"label\": \"Data Exploration\"}},\n    {\"id\": \"model\", \"data\": {\"label\": \"Model Building\"}},\n    {\"id\": \"evaluate\", \"data\": {\"label\": \"Model Evaluation\"}},\n    {\"id\": \"<cell_id>\", \"data\": {\"label\": \"<1-5 word descriptive title explaining what this code cell is doing>\"}, \"parentNode\": \"<import, wrangle, explore, model, evaluate>\"}\n  ]\n}"
    #     },
    #     {
    #     "role": "user",
    #     "content": gpt_input
    #     },
    # ],
    # temperature=0,
    # max_tokens=4095,
    # top_p=0,
    # frequency_penalty=0,
    # presence_penalty=0
    # )
    # #breakpoint()
    # output = response.choices[0].message.content
    # output = ast.literal_eval(output)
    # output["edges"] = treeData["edges"]
    gpt_input = json.dumps(result)
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {
            "role": "system",
            "content": "You will be given a json that contains the python code of the cells in a jupyter notebook file. Your task is to assign each code cell with a descriptive title and category. Ensure the output is strictly in JSON format, without any additional explanations, strings, or context. Use the format:\n\n[{'id': '1', 'data': {'label': '<1-5 word descriptive title explaining what this code cell is doing>', 'categoryColor': '<import, wrangle, explore, model, evaluate>'}}, # repeat for all the other nodes]"
            },
            {
            "role": "user",
            "content": gpt_input
            }
        ],
        temperature=0,
        max_tokens=4095,
        top_p=0,
        frequency_penalty=0,
        presence_penalty=0
    )
    output = response.choices[0].message.content
    nodes = ast.literal_eval(output)
    edges = treeData["edges"]
    enriched_tree_data = {"nodes": nodes, "edges": edges}
    return enriched_tree_data
    
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

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    # #process_notebooks(UPLOAD_FOLDER)
    # test_parse_gv_file('nb_1191_new_labels.gv')
    #get_tree_structure('nb_1194.ipynb')

    app.run(debug=True, port=5002, use_reloader=False)
