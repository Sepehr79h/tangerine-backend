import os
from openai import OpenAI
from dotenv import load_dotenv
import nbformat
load_dotenv()
OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY")

def get_suggestions_input(node_id, notebook_path, edges):
    print(node_id)
    print(edges)
    print('Getting suggestions...')
    # if node_id starts with group then set it to the value after the _
    if node_id.startswith('group'):
        node_id = node_id.split('_')[-1]
    edges = [edge for edge in edges if not edge['source'].startswith('group') and not edge['target'].startswith('group')]
    # Function to recursively find all paths from any node to the root
    def find_paths(node_id, edges, path):
        # Find all edges ending at node_id
        incoming_edges = [edge for edge in edges if edge['target'] == node_id]
        
        # Base case: if there are no incoming edges, this is a root
        if not incoming_edges:
            return [[node_id]]

        paths = []  # This will store all paths from the roots to node_id
        for edge in incoming_edges:
            # Recursive call for each source node of incoming edges
            for subpath in find_paths(edge['source'], edges, path):
                paths.append(subpath + [node_id])

        return paths
    #breakpoint()

    # Retrieve all paths leading to node_id
    all_paths = find_paths(node_id, edges, [])
    final_path = all_paths[-1]

    # Load the notebook
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)

    result = {"cells": []}
    # Iterate through the notebook cells
    for cell in nb.cells:
        if cell.cell_type == 'code' and str(cell.execution_count) in final_path:
            # Extract the code and the execution count (cell_id in this context)
            cell_data = {
                "cell_id": str(cell.execution_count),
                "code": cell.source.split('\n')  # Splitting source code by newline to get a list of code lines
            }
            result['cells'].append(cell_data)
    
    print(result)
    return result

    