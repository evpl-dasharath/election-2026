import json

log_file = r'C:\Users\everl\.gemini\antigravity\brain\41984e60-93d2-46c5-b86b-cef70ae9a3d7\.system_generated\logs\overview.txt'

with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        if data.get('step_index') == 6:
            # this is the MODEL step. we want step 7 which is the USER VIEW_FILE response
            pass
        elif data.get('step_index') == 7:
            # wait, step 6 is PLANNER_RESPONSE with view_file. Step 7 is probably the TOOL_RESPONSE or VIEW_FILE type
            pass
        
        if data.get('source') == 'USER_EXPLICIT' and data.get('type') == 'VIEW_FILE' and 'HomePage.tsx' in data.get('content', ''):
            with open('extracted_homepage.tsx', 'w', encoding='utf-8') as out:
                out.write(data.get('content', ''))
            print('Extracted from USER VIEW_FILE')

        if data.get('type') == 'TOOL_RESPONSE' and 'HomePage.tsx' in data.get('content', ''):
            with open('extracted_homepage2.tsx', 'w', encoding='utf-8') as out:
                out.write(data.get('content', ''))
            print('Extracted from TOOL_RESPONSE')

