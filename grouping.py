import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY")

def update_parentNode(data):
    for node in data['nodes']:
        if 'parentNode' in node:
            node['data']['categoryColor'] = node['parentNode']
            del node['parentNode']
    # remove first 5 nodes
    data['nodes'] = data['nodes'][5:]
    return data

def create_node_groups(data):
    groups = {}
    current_group = None

    #store the nodes where id is a digit first
    cell_nodes = [node for node in data['nodes'] if node['id'].isdigit()]
    sorted_nodes = sorted(cell_nodes, key=lambda x: int(x['id']))

    # creates a group for each set of sequential nodes (id is sequential) that have the same parentNode
    for node in sorted_nodes:
        parent = node['data']['categoryColor']
        if parent != current_group:
            current_group = parent
            group_name = "group_"+node["id"]
            groups[group_name] = [node]
        else:
            groups[group_name].append(node)
    
    # drop groups with 1 or 0 nodes
    groups = {k: v for k, v in groups.items() if len(v) > 1}

    new_groups = {}
    for key, value in groups.items():
        if value:  # checking if the list is not empty
            last_id = value[-1]['id']
            new_key = f"{key}_{last_id}"
            new_groups[new_key] = value

    return new_groups

def update_nodes_with_groups(data, groups):
    for group in groups:
        # create a new node for the group
        group_node = {
            'id': group,
            'data': {
                'label': group,
                'categoryColor': groups[group][0]['data']['categoryColor']
            },
            # 'categoryColor': groups[group][0]['data']['categoryColor']
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

def get_labeled_grouped_tree_structure(treeData, groups):
    group_nodes = []
    for node in treeData['nodes']:
        if node.get('id').startswith('group_'):
            group_nodes.append(node)

    client = OpenAI(
        api_key=OPENAI_API_KEY,
    )
    response = client.chat.completions.create(
    model="gpt-4-0125-preview",
        messages=[
            {
            "role": "system",
            "content": "You will be given a json that contains groups, and all the nodes in those respective groups. Your job is to assign descriptive labels to the groups based on the labels of the nodes in each group. The label you assign to a group must be representative of all the labels of the nodes in that group. It shouldn't be something vague like \"data import\". It should capture all the labels of the nodes in the group. Do not repeat any words in the categoryColor in this label, since the uesr already knows about that. Use the following format:\n\n[{'id': '<group_id (e.g. group1)>', 'data': {'label': 'detailed and specific 3 word title representative of all the labels of the nodes in that group. Do not repeat any words in the categoryColor in this label, since the uesr already knows about that.}}, #add other groups]\n\n"
            },
            {
            "role": "user",
            "content": str(groups)
            },
        ],
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    output = response.choices[0].message.content
    output = eval(output)

    for node in treeData['nodes']:
        if node.get('id').startswith('group_'):
            for group in output:
                if group['id'] == node['id']:
                    node['data']['label'] = group['data']['label']
                    # add id of all nodes in the group to the label in the format: first_id-last_id
                    node['data']['label'] += ' [' + groups[node['id']][0]['id'] + '-' + groups[node['id']][-1]['id'] + ']'
        else:
            #add the node id to the label
            node['data']['label'] += ' [' + node['id'] + ']'


                    #node['data']['label'] += ' (' + ', '.join([n['id'] for n in groups[node['id']]]) + ')'
    
    return treeData

def get_grouped_tree_structure(data):
    data = update_parentNode(data)
    groups = create_node_groups(data)
    data = update_nodes_with_groups(data, groups)
    data = update_edges_with_groups(data, groups)
    data = get_labeled_grouped_tree_structure(data, groups)
    return data

if __name__ == '__main__':
    data = {'nodes': [{'id': 'import', 'data': {'label': 'Data Import'}}, {'id': 'wrangle', 'data': {'label': 'Data Wrangling'}}, {'id': 'explore', 'data': {'label': 'Data Exploration'}}, {'id': 'model', 'data': {'label': 'Model Building'}}, {'id': 'evaluate', 'data': {'label': 'Model Evaluation'}}, {'id': '1', 'data': {'label': 'Import Libraries and Settings'}, 'parentNode': 'import'}, {'id': '2', 'data': {'label': 'Load Data'}, 'parentNode': 'import'}, {'id': '3', 'data': {'label': 'Display Data Head'}, 'parentNode': 'explore'}, {'id': '4', 'data': {'label': 'Plot Experience vs Salary'}, 'parentNode': 'explore'}, {'id': '5', 'data': {'label': 'Reshape Data'}, 'parentNode': 'wrangle'}, {'id': '6', 'data': {'label': 'Check Data Shape'}, 'parentNode': 'wrangle'}, {'id': '7', 'data': {'label': 'Assign Target Variable'}, 'parentNode': 'wrangle'}, {'id': '8', 'data': {'label': 'Create Linear Regression Model'}, 'parentNode': 'model'}, {'id': '9', 'data': {'label': 'Fit Data to Model'}, 'parentNode': 'model'}, {'id': '10', 'data': {'label': 'Print Model Coefficient'}, 'parentNode': 'evaluate'}, {'id': '11', 'data': {'label': 'Print Model Intercept'}, 'parentNode': 'evaluate'}, {'id': '12', 'data': {'label': 'Predict y Values'}, 'parentNode': 'model'}, {'id': '13', 'data': {'label': 'Plot Predicted vs Actual'}, 'parentNode': 'evaluate'}, {'id': '14', 'data': {'label': 'Calculate Metrics'}, 'parentNode': 'evaluate'}, {'id': '15', 'data': {'label': 'Print Metrics'}, 'parentNode': 'evaluate'}], 'edges': [{'source': '2', 'target': '3'}, {'source': '2', 'target': '4'}, {'source': '2', 'target': '5'}, {'source': '2', 'target': '7'}, {'source': '5', 'target': '6'}, {'source': '5', 'target': '9'}, {'source': '5', 'target': '12'}, {'source': '5', 'target': '14'}, {'source': '7', 'target': '9'}, {'source': '7', 'target': '14'}, {'source': '8', 'target': '9'}, {'source': '8', 'target': '12'}, {'source': '8', 'target': '14'}, {'source': '9', 'target': '10'}, {'source': '9', 'target': '11'}, {'source': '9', 'target': '12'}, {'source': '9', 'target': '13'}, {'source': '9', 'target': '14'}, {'source': '12', 'target': '13'}, {'source': '12', 'target': '14'}]}
    data = get_grouped_tree_structure(data)
    pass