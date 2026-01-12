import json
import os

HISTORY_FILE = "shorts_factory/history.json"

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, 'r') as f:
        return json.load(f)

def add_entry(project_id, title, keywords):
    history = load_history()
    
    # Check duplicate
    for h in history:
        if h['id'] == project_id:
            print(f"Project {project_id} already in history.")
            return

    new_entry = {
        "id": project_id,
        "title": title,
        "keywords": keywords
    }
    history.append(new_entry)
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    print(f"Added project {project_id} to history.")

def get_used_keywords():
    history = load_history()
    all_keywords = []
    for h in history:
        all_keywords.extend(h.get('keywords', []))
    return list(set(all_keywords))

def get_previous_titles():
    history = load_history()
    return [h['title'] for h in history]

if __name__ == "__main__":
    # Test
    print("Previous Titles:", get_previous_titles())
    print("Used Keywords:", get_used_keywords())
