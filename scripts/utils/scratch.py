import json
log_file = r'C:\Users\everl\.gemini\antigravity\brain\41984e60-93d2-46c5-b86b-cef70ae9a3d7\.system_generated\logs\overview.txt'
with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        content = data.get('content', '')
        if 'export default function HomePage' in content and data.get('type') == 'TOOL_RESPONSE':
            print(f"Found in step {data.get('step_index')}")
            with open('extracted_homepage.tsx', 'w', encoding='utf-8') as out:
                out.write(content)
            break
