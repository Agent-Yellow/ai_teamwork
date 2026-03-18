import re
import sys

def parse_vtt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    text_lines = []
    previous_line = ""
    for line in lines:
        line = line.strip()
        # Skip empty lines, WEBVTT header, timestamps
        if not line or line == 'WEBVTT' or '-->' in line or line.startswith('Kind:') or line.startswith('Language:'):
            continue
        # Remove tags like <c> or </c> or <00:00:00.000>
        clean_line = re.sub(r'<[^>]+>', '', line)
        if clean_line and clean_line != previous_line:
            text_lines.append(clean_line)
            previous_line = clean_line

    with open('cleaned_transcript.txt', 'w', encoding='utf-8') as f:
        f.write(' '.join(text_lines))

if __name__ == "__main__":
    parse_vtt(sys.argv[1])
