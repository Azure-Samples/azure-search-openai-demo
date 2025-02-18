import os

import pypandoc


def convert_md_to_html(directory):
    # Ensure the output directory exists
    html_output_dir = os.path.join(directory, 'html')
    os.makedirs(html_output_dir, exist_ok=True)

    # Iterate over all files in the directory
    for filename in os.listdir(directory):
        if filename.endswith('.md'):
            filepath = os.path.join(directory, filename)
            base_filename = os.path.splitext(filename)[0]

            # Convert to HTML
            html_output_path = os.path.join(html_output_dir, f'{base_filename}.html')
            pypandoc.convert_file(filepath, 'html', outputfile=html_output_path)
            print(f'Converted {filename} to {html_output_path}')

if __name__ == '__main__':
    # Specify the directory containing the Markdown files
    directory = '.'
    convert_md_to_html(directory)