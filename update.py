def get_updated_tree(curr_tree, new_node, initial_tree):
    updated_tree = curr_tree.copy()

    initial_node_ids = {node['id'] for node in initial_tree['nodes']}
    curr_node_ids = {node['id'] for node in curr_tree['nodes']}

    missing_nodes = initial_node_ids - curr_node_ids

    # Step 2: Add missing nodes
    for node in initial_tree['nodes']:
        if node['id'] in missing_nodes:
            updated_tree['nodes'].append(node)

    # Step 3: Add the corresponding edges for the missing nodes
    for edge in initial_tree['edges']:
        if edge['source'] in missing_nodes or edge['target'] in missing_nodes:
            updated_tree['edges'].append(edge)

    breakpoint()
    return updated_tree