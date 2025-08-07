
import os
import yaml
import time

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

def simulate_upload(file_path, config):
    print(f"[SIMULATION] Would upload: {file_path}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bulk Import Pipeline for Notion")
    parser.add_argument("--config", type=str, required=True, help="Path to sync_config.yaml")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    config = load_config(args.config)
    source_dir = config.get("source_directory", ".")
    file_types = config.get("file_types", [".md", ".txt", ".pdf", ".docx", ".yaml", ".json"])
    excluded_patterns = config.get("excluded_patterns", [])

    if args.verbose:
        print(f"🛠️  Starting import from: {source_dir}")
        print(f"📂 File types: {file_types}")
        print(f"❌ Excluded patterns: {excluded_patterns}")

    files = list(walk_directory(source_dir, file_types, excluded_patterns))

    for file_path in files:
        simulate_upload(file_path, config)
        if args.verbose:
            print(f"✅ Processed: {file_path}")
        time.sleep(0.1)  # Simulate API rate limit

if __name__ == "__main__":
    main()
