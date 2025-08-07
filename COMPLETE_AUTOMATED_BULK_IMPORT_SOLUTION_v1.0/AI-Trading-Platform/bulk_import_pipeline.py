
import os
import yaml
import time
import requests

def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def should_exclude(filename, patterns):
    from fnmatch import fnmatch
    return any(fnmatch(filename, pattern) for pattern in patterns)

def walk_directory(source_dir, file_types, excluded_patterns):
    for root, _, files in os.walk(source_dir):
        for file in files:
            filepath = os.path.join(root, file)
            if should_exclude(filepath, excluded_patterns):
                continue
            if any(file.endswith(ft) for ft in file_types):
                yield filepath

def upload_to_notion(file_path, config):
    notion_token = config.get("notion_token")
    parent_page_id = config.get("notion_parent_page_id")

    if not notion_token or not parent_page_id:
        print(f"❌ Missing Notion credentials for: {file_path}")
        return

    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    payload = {
        "parent": { "page_id": parent_page_id },
        "properties": {
            "title": [{
                "text": { "content": os.path.basename(file_path) }
            }]
        },
        "children": [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": { "content": content[:2000] }
                }]
            }
        }]
    }

    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
    if response.status_code == 200:
        print(f"✅ Uploaded: {file_path}")
    else:
        print(f"❌ Failed to upload {file_path}: {response.status_code} - {response.text}")

def simulate_upload(file_path, config, dry_run):
    if dry_run:
        print(f"[SIMULATION] Would upload: {file_path}")
    else:
        upload_to_notion(file_path, config)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bulk Import Pipeline for Notion")
    parser.add_argument("--config", type=str, required=True, help="Path to sync_config.yaml")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    config = load_config(args.config)
    dry_run = config.get("development", {}).get("dry_run", True)
    source_dir = config.get("source_directory", ".")
    file_types = config.get("file_types", [".md", ".txt", ".pdf", ".docx", ".yaml", ".json"])
    excluded_patterns = config.get("excluded_patterns", [])

    if args.verbose:
        print(f"🛠️  Starting import from: {source_dir}")
        print(f"📂 File types: {file_types}")
        print(f"❌ Excluded patterns: {excluded_patterns}")

    files = list(walk_directory(source_dir, file_types, excluded_patterns))

    for file_path in files:
        simulate_upload(file_path, config, dry_run)
        if args.verbose:
            print(f"✅ Processed: {file_path}")
        time.sleep(0.1)

if __name__ == "__main__":
    main()
