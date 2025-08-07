#!/usr/bin/env python3
"""
Persistent File Access System for Bio-Quantum AI Project
Solves the file handling and session persistence issues once and for all.
"""

import os
import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
import sys

class PersistentFileManager:
    def __init__(self, base_dir="/home/ubuntu"):
        self.base_dir = Path(base_dir)
        self.upload_dir = self.base_dir / "upload"
        self.persistent_dir = self.base_dir / "persistent_files"
        self.manifest_file = self.persistent_dir / "file_manifest.json"
        
        # Create directories if they don't exist
        self.persistent_dir.mkdir(exist_ok=True)
        
        # Initialize manifest
        self.manifest = self.load_manifest()
    
    def load_manifest(self):
        """Load the file manifest or create a new one"""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "files": {},
            "last_updated": datetime.now().isoformat(),
            "total_files": 0,
            "categories": {
                "videos": [],
                "audio": [],
                "images": [],
                "documents": [],
                "code": [],
                "data": []
            }
        }
    
    def save_manifest(self):
        """Save the manifest to disk"""
        self.manifest["last_updated"] = datetime.now().isoformat()
        self.manifest["total_files"] = len(self.manifest["files"])
        
        with open(self.manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2)
    
    def get_file_hash(self, file_path):
        """Generate MD5 hash of file for deduplication"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def categorize_file(self, file_path):
        """Categorize file based on extension"""
        ext = file_path.suffix.lower()
        
        if ext in ['.mp4', '.avi', '.mov', '.mkv']:
            return 'videos'
        elif ext in ['.wav', '.mp3', '.aac', '.flac']:
            return 'audio'
        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg']:
            return 'images'
        elif ext in ['.pdf', '.doc', '.docx', '.txt', '.md']:
            return 'documents'
        elif ext in ['.py', '.js', '.html', '.css', '.json', '.yaml', '.yml']:
            return 'code'
        else:
            return 'data'
    
    def scan_and_index_all_files(self):
        """Scan upload directory and index all files"""
        print("🔍 Scanning all files in upload directory...")
        
        # Scan upload directory recursively
        for file_path in self.upload_dir.rglob('*'):
            if file_path.is_file():
                self.index_file(file_path)
        
        # Scan other important directories
        for dir_name in ['bio_quantum_enhanced', 'bio_quantum_updated', 'chatgpt_drop_package']:
            dir_path = self.base_dir / dir_name
            if dir_path.exists():
                for file_path in dir_path.rglob('*'):
                    if file_path.is_file():
                        self.index_file(file_path)
        
        self.save_manifest()
        print(f"✅ Indexed {len(self.manifest['files'])} files")
    
    def index_file(self, file_path):
        """Index a single file"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return
            
            # Get file info
            stat = file_path.stat()
            file_hash = self.get_file_hash(file_path)
            category = self.categorize_file(file_path)
            
            # Create persistent copy if not exists
            persistent_path = self.persistent_dir / file_path.name
            if not persistent_path.exists():
                shutil.copy2(file_path, persistent_path)
            
            # Add to manifest
            file_info = {
                "original_path": str(file_path),
                "persistent_path": str(persistent_path),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "hash": file_hash,
                "category": category,
                "indexed_at": datetime.now().isoformat()
            }
            
            self.manifest["files"][file_path.name] = file_info
            
            # Add to category
            if file_path.name not in self.manifest["categories"][category]:
                self.manifest["categories"][category].append(file_path.name)
            
        except Exception as e:
            print(f"❌ Error indexing {file_path}: {e}")
    
    def get_file_list(self, category=None):
        """Get list of files, optionally filtered by category"""
        if category:
            return self.manifest["categories"].get(category, [])
        return list(self.manifest["files"].keys())
    
    def get_file_info(self, filename):
        """Get detailed info about a specific file"""
        return self.manifest["files"].get(filename)
    
    def get_file_path(self, filename):
        """Get the persistent path for a file"""
        file_info = self.get_file_info(filename)
        if file_info:
            return file_info["persistent_path"]
        return None
    
    def search_files(self, query):
        """Search files by name or content"""
        results = []
        query_lower = query.lower()
        
        for filename, info in self.manifest["files"].items():
            if query_lower in filename.lower():
                results.append({
                    "filename": filename,
                    "category": info["category"],
                    "size": info["size"],
                    "path": info["persistent_path"]
                })
        
        return results
    
    def generate_report(self):
        """Generate a comprehensive file report"""
        report = {
            "summary": {
                "total_files": len(self.manifest["files"]),
                "last_updated": self.manifest["last_updated"],
                "categories": {cat: len(files) for cat, files in self.manifest["categories"].items()}
            },
            "recent_files": [],
            "large_files": [],
            "by_category": self.manifest["categories"]
        }
        
        # Get recent files (last 10)
        sorted_files = sorted(
            self.manifest["files"].items(),
            key=lambda x: x[1]["indexed_at"],
            reverse=True
        )
        report["recent_files"] = [f[0] for f in sorted_files[:10]]
        
        # Get large files (>10MB)
        large_files = [
            {"name": name, "size": info["size"]}
            for name, info in self.manifest["files"].items()
            if info["size"] > 10 * 1024 * 1024
        ]
        report["large_files"] = sorted(large_files, key=lambda x: x["size"], reverse=True)
        
        return report

def main():
    """Main function to run the persistent file manager"""
    print("🚀 Initializing Persistent File Access System...")
    
    manager = PersistentFileManager()
    
    # Scan and index all files
    manager.scan_and_index_all_files()
    
    # Generate report
    report = manager.generate_report()
    
    print("\n📊 FILE ACCESS SYSTEM REPORT")
    print("=" * 50)
    print(f"Total Files: {report['summary']['total_files']}")
    print(f"Last Updated: {report['summary']['last_updated']}")
    print("\nFiles by Category:")
    for category, count in report['summary']['categories'].items():
        print(f"  {category.title()}: {count} files")
    
    print(f"\nRecent Files ({len(report['recent_files'])}):")
    for filename in report['recent_files']:
        print(f"  - {filename}")
    
    print(f"\nLarge Files ({len(report['large_files'])}):")
    for file_info in report['large_files'][:5]:
        size_mb = file_info['size'] / (1024 * 1024)
        print(f"  - {file_info['name']} ({size_mb:.1f} MB)")
    
    # Save report to file
    report_file = Path("/home/ubuntu/persistent_files/file_access_report.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Persistent File Access System is now active!")
    print(f"📁 Manifest: {manager.manifest_file}")
    print(f"📊 Report: {report_file}")
    print(f"🗂️  Persistent Files: {manager.persistent_dir}")
    
    return manager

if __name__ == "__main__":
    manager = main()

