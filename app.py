from flask import Flask, request, jsonify
import os
import subprocess
from flask_cors import CORS
from collections import defaultdict

app = Flask(__name__)
CORS(app)

# Directory where uploaded notebooks will be saved
UPLOAD_FOLDER = 'notebooks'
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
    frontend_path = '/path/to/frontend'
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
        treeData = {'nodes': nodes, 'edges': edges}
        print('Tree structure processed successfully')
        return jsonify(treeData)
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404


if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    # #process_notebooks(UPLOAD_FOLDER)
    # test_parse_gv_file('nb_1191_new_labels.gv')
    #get_tree_structure('nb_1194.ipynb')

    app.run(debug=True, port=5001, use_reloader=False)
