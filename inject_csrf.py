import os
import glob
import re

for root, _, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use regex to find <form ... method=\"POST\" ...>
            new_content = re.sub(
                r'(<form[^>]*method=[\"\']POST[\"\'][^>]*>)',
                r'\1\n<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>',
                content,
                flags=re.IGNORECASE
            )
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f'Updated {filepath}')
