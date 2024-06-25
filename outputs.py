import nbformat

def get_outputs(node_id, notebook_path):
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)
        image_output = None
        html_output = None
        text_output = None
        stream_output = None

        for cell in nb.cells:
            if cell.cell_type == 'code' and str(cell.execution_count) == node_id:
                outputs = cell.get('outputs', [])
                for output in outputs:
                    if output['output_type'] in ['display_data', 'execute_result']:
                        data = output.get('data', {})
                        if 'image/png' in data:
                            image_output = {
                                'output_type': 'image/png',
                                'data': data['image/png']
                            }
                        elif 'text/html' in data and html_output is None:
                            html_output = {
                                'output_type': 'text/html',
                                'data': data['text/html']
                            }
                        elif 'text/plain' in data and text_output is None:
                            text_output = {
                                'output_type': 'text/plain',
                                'data': data['text/plain']
                            }
                    elif output['output_type'] == 'stream' and output.get('name') == 'stdout':
                        if stream_output is None:
                            stream_output = {
                                'output_type': 'stream',
                                'data': output.get('text', '')
                            }

        # Prioritize outputs
        if image_output:
            return image_output
        elif html_output:
            return html_output
        elif text_output:
            return text_output
        elif stream_output:
            return stream_output
        
    return {
        'output_type': 'error',
        'data': 'No matching cell or output found'
    }
