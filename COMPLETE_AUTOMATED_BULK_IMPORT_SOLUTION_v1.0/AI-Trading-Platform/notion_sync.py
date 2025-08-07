#!/usr/bin/env python3
"""
Manus-Notion API Bridge - Main Synchronization Script
====================================================

This script implements the core synchronization functionality between
local development environments and Notion workspaces, enabling seamless
collaboration between human developers and AI agents.

Author: Manus AI
Version: 1.0
Date: July 7, 2025
"""

import os
import sys
import json
import yaml
import time
import hashlib
import logging
import requests
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import markdown
import csv
from notion_client import Client as NotionClient
from notion_client.errors import APIResponseError, RequestTimeoutError

# Configuration and Constants
CONFIG_FILE = "sync_config.yaml"
STATE_FILE = "sync_state.json"
LOG_FILE = "sync.log"
DEFAULT_SYNC_INTERVAL = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

@dataclass
class SyncConfig:
    """Configuration structure for the sync system"""
    notion_token: str
    notion_database_id: Optional[str] = None
    notion_parent_page_id: Optional[str] = None
    manus_api_endpoint: Optional[str] = None
    manus_api_key: Optional[str] = None
    sync_directories: List[str] = None
    excluded_patterns: List[str] = None
    sync_interval: int = DEFAULT_SYNC_INTERVAL
    enable_bidirectional: bool = True
    enable_auto_backup: bool = True
    max_file_size_mb: int = 50
    
    def __post_init__(self):
        if self.sync_directories is None:
            self.sync_directories = ["docs/", "tasks/", "assets/"]
        if self.excluded_patterns is None:
            self.excluded_patterns = ["*.tmp", "*.log", ".git/", "__pycache__/"]

@dataclass
class SyncState:
    """State tracking for synchronization operations"""
    last_sync_time: str
    file_checksums: Dict[str, str]
    notion_page_mappings: Dict[str, str]
    sync_errors: List[Dict[str, Any]]
    total_syncs: int = 0
    successful_syncs: int = 0
    
    def __post_init__(self):
        if not hasattr(self, 'file_checksums'):
            self.file_checksums = {}
        if not hasattr(self, 'notion_page_mappings'):
            self.notion_page_mappings = {}
        if not hasattr(self, 'sync_errors'):
            self.sync_errors = []

class NotionSyncManager:
    """Main synchronization manager for Notion integration"""
    
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self.config = self._load_config()
        self.state = self._load_state()
        self.notion_client = NotionClient(auth=self.config.notion_token)
        self.logger = self._setup_logging()
        self.observer = None
        self.sync_thread = None
        self.running = False
        
    def _load_config(self) -> SyncConfig:
        """Load configuration from YAML file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                return SyncConfig(**config_data)
            else:
                # Create default config
                default_config = SyncConfig(
                    notion_token="YOUR_NOTION_TOKEN_HERE",
                    notion_database_id="YOUR_DATABASE_ID_HERE",
                    notion_parent_page_id="YOUR_PARENT_PAGE_ID_HERE"
                )
                self._save_config(default_config)
                self.logger.warning(f"Created default config at {self.config_path}. Please update with your credentials.")
                return default_config
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            raise
    
    def _save_config(self, config: SyncConfig):
        """Save configuration to YAML file"""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(asdict(config), f, default_flow_style=False)
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
            raise
    
    def _load_state(self) -> SyncState:
        """Load synchronization state from JSON file"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    state_data = json.load(f)
                return SyncState(**state_data)
            else:
                return SyncState(
                    last_sync_time=datetime.now().isoformat(),
                    file_checksums={},
                    notion_page_mappings={},
                    sync_errors=[]
                )
        except Exception as e:
            self.logger.error(f"Error loading state: {e}")
            return SyncState(
                last_sync_time=datetime.now().isoformat(),
                file_checksums={},
                notion_page_mappings={},
                sync_errors=[]
            )
    
    def _save_state(self):
        """Save synchronization state to JSON file"""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(asdict(self.state), f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('notion_sync')
        logger.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def calculate_file_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of a file"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculating checksum for {file_path}: {e}")
            return ""
    
    def should_sync_file(self, file_path: str) -> bool:
        """Determine if a file should be synchronized"""
        # Check file size
        try:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > self.config.max_file_size_mb:
                self.logger.warning(f"File {file_path} exceeds size limit ({file_size_mb:.2f}MB)")
                return False
        except OSError:
            return False
        
        # Check excluded patterns
        file_name = os.path.basename(file_path)
        for pattern in self.config.excluded_patterns:
            if pattern.replace('*', '') in file_name or pattern in file_path:
                return False
        
        # Check if file is in sync directories
        for sync_dir in self.config.sync_directories:
            if file_path.startswith(sync_dir) or sync_dir in file_path:
                return True
        
        return False
    
    def convert_markdown_to_notion_blocks(self, markdown_content: str) -> List[Dict[str, Any]]:
        """Convert Markdown content to Notion blocks"""
        blocks = []
        lines = markdown_content.split('\n')
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                if current_paragraph:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": ' '.join(current_paragraph)}}]
                        }
                    })
                    current_paragraph = []
                continue
            
            # Headers
            if line.startswith('#'):
                if current_paragraph:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": ' '.join(current_paragraph)}}]
                        }
                    })
                    current_paragraph = []
                
                header_level = len(line) - len(line.lstrip('#'))
                header_text = line.lstrip('# ').strip()
                
                if header_level == 1:
                    block_type = "heading_1"
                elif header_level == 2:
                    block_type = "heading_2"
                else:
                    block_type = "heading_3"
                
                blocks.append({
                    "object": "block",
                    "type": block_type,
                    block_type: {
                        "rich_text": [{"type": "text", "text": {"content": header_text}}]
                    }
                })
            
            # Code blocks
            elif line.startswith('```'):
                if current_paragraph:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": ' '.join(current_paragraph)}}]
                        }
                    })
                    current_paragraph = []
                # Note: Full code block handling would require multi-line parsing
                continue
            
            # Bullet points
            elif line.startswith('- ') or line.startswith('* '):
                if current_paragraph:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": ' '.join(current_paragraph)}}]
                        }
                    })
                    current_paragraph = []
                
                bullet_text = line[2:].strip()
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": bullet_text}}]
                    }
                })
            
            else:
                current_paragraph.append(line)
        
        # Handle remaining paragraph
        if current_paragraph:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": ' '.join(current_paragraph)}}]
                }
            })
        
        return blocks
    
    def sync_file_to_notion(self, file_path: str) -> bool:
        """Sync a single file to Notion"""
        try:
            self.logger.info(f"Syncing file to Notion: {file_path}")
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Determine file type and convert content
            file_ext = os.path.splitext(file_path)[1].lower()
            file_name = os.path.basename(file_path)
            
            if file_ext == '.md':
                blocks = self.convert_markdown_to_notion_blocks(content)
                title = file_name.replace('.md', '')
            elif file_ext == '.txt':
                blocks = [{
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    }
                }]
                title = file_name.replace('.txt', '')
            else:
                # For other file types, create a simple text block
                blocks = [{
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": f"File: {file_name}\n\n{content[:1000]}..."}}]
                    }
                }]
                title = file_name
            
            # Check if page already exists
            page_id = self.state.notion_page_mappings.get(file_path)
            
            if page_id:
                # Update existing page
                try:
                    # Clear existing blocks
                    existing_blocks = self.notion_client.blocks.children.list(block_id=page_id)
                    for block in existing_blocks.get('results', []):
                        self.notion_client.blocks.delete(block_id=block['id'])
                    
                    # Add new blocks
                    if blocks:
                        self.notion_client.blocks.children.append(
                            block_id=page_id,
                            children=blocks
                        )
                    
                    self.logger.info(f"Updated existing Notion page for {file_path}")
                    
                except APIResponseError as e:
                    if e.status == 404:
                        # Page no longer exists, create new one
                        page_id = None
                    else:
                        raise
            
            if not page_id:
                # Create new page
                page_data = {
                    "parent": {"page_id": self.config.notion_parent_page_id},
                    "properties": {
                        "title": {
                            "title": [{"type": "text", "text": {"content": title}}]
                        }
                    },
                    "children": blocks
                }
                
                response = self.notion_client.pages.create(**page_data)
                page_id = response['id']
                self.state.notion_page_mappings[file_path] = page_id
                self.logger.info(f"Created new Notion page for {file_path}")
            
            # Update file checksum
            self.state.file_checksums[file_path] = self.calculate_file_checksum(file_path)
            self.state.successful_syncs += 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error syncing {file_path} to Notion: {e}")
            self.state.sync_errors.append({
                "file_path": file_path,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return False
    
    def sync_directory_to_notion(self, directory: str) -> int:
        """Sync all eligible files in a directory to Notion"""
        synced_count = 0
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    if self.should_sync_file(file_path):
                        # Check if file has changed
                        current_checksum = self.calculate_file_checksum(file_path)
                        stored_checksum = self.state.file_checksums.get(file_path, "")
                        
                        if current_checksum != stored_checksum:
                            if self.sync_file_to_notion(file_path):
                                synced_count += 1
                            
                            # Rate limiting
                            time.sleep(0.5)
        
        except Exception as e:
            self.logger.error(f"Error syncing directory {directory}: {e}")
        
        return synced_count
    
    def perform_full_sync(self) -> Dict[str, int]:
        """Perform a full synchronization of all configured directories"""
        self.logger.info("Starting full synchronization")
        start_time = time.time()
        
        total_synced = 0
        results = {}
        
        for sync_dir in self.config.sync_directories:
            if os.path.exists(sync_dir):
                synced_count = self.sync_directory_to_notion(sync_dir)
                results[sync_dir] = synced_count
                total_synced += synced_count
                self.logger.info(f"Synced {synced_count} files from {sync_dir}")
            else:
                self.logger.warning(f"Sync directory does not exist: {sync_dir}")
                results[sync_dir] = 0
        
        # Update state
        self.state.last_sync_time = datetime.now().isoformat()
        self.state.total_syncs += 1
        self._save_state()
        
        elapsed_time = time.time() - start_time
        self.logger.info(f"Full sync completed: {total_synced} files in {elapsed_time:.2f} seconds")
        
        return results
    
    def start_file_monitoring(self):
        """Start file system monitoring for automatic synchronization"""
        class SyncEventHandler(FileSystemEventHandler):
            def __init__(self, sync_manager):
                self.sync_manager = sync_manager
                super().__init__()
            
            def on_modified(self, event):
                if not event.is_directory and self.sync_manager.should_sync_file(event.src_path):
                    self.sync_manager.logger.info(f"File modified: {event.src_path}")
                    # Debounce rapid changes
                    time.sleep(1)
                    self.sync_manager.sync_file_to_notion(event.src_path)
                    self.sync_manager._save_state()
            
            def on_created(self, event):
                if not event.is_directory and self.sync_manager.should_sync_file(event.src_path):
                    self.sync_manager.logger.info(f"File created: {event.src_path}")
                    time.sleep(1)
                    self.sync_manager.sync_file_to_notion(event.src_path)
                    self.sync_manager._save_state()
        
        self.observer = Observer()
        event_handler = SyncEventHandler(self)
        
        # Monitor all sync directories
        for sync_dir in self.config.sync_directories:
            if os.path.exists(sync_dir):
                self.observer.schedule(event_handler, sync_dir, recursive=True)
                self.logger.info(f"Monitoring directory: {sync_dir}")
        
        self.observer.start()
        self.logger.info("File monitoring started")
    
    def start_periodic_sync(self):
        """Start periodic synchronization in a separate thread"""
        def sync_worker():
            while self.running:
                try:
                    self.perform_full_sync()
                    time.sleep(self.config.sync_interval)
                except Exception as e:
                    self.logger.error(f"Error in periodic sync: {e}")
                    time.sleep(self.config.sync_interval)
        
        self.sync_thread = threading.Thread(target=sync_worker, daemon=True)
        self.sync_thread.start()
        self.logger.info(f"Periodic sync started (interval: {self.config.sync_interval}s)")
    
    def start(self):
        """Start the synchronization system"""
        self.logger.info("Starting Notion Sync Manager")
        self.running = True
        
        # Perform initial sync
        self.perform_full_sync()
        
        # Start monitoring and periodic sync
        self.start_file_monitoring()
        self.start_periodic_sync()
        
        self.logger.info("Notion Sync Manager started successfully")
    
    def stop(self):
        """Stop the synchronization system"""
        self.logger.info("Stopping Notion Sync Manager")
        self.running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        if self.sync_thread:
            self.sync_thread.join(timeout=10)
        
        self._save_state()
        self.logger.info("Notion Sync Manager stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current synchronization status"""
        return {
            "running": self.running,
            "last_sync_time": self.state.last_sync_time,
            "total_syncs": self.state.total_syncs,
            "successful_syncs": self.state.successful_syncs,
            "error_count": len(self.state.sync_errors),
            "monitored_files": len(self.state.file_checksums),
            "notion_pages": len(self.state.notion_page_mappings)
        }

def main():
    """Main entry point for the synchronization script"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manus-Notion API Bridge Synchronization")
    parser.add_argument("--config", default=CONFIG_FILE, help="Configuration file path")
    parser.add_argument("--sync-once", action="store_true", help="Perform single sync and exit")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--setup", action="store_true", help="Setup initial configuration")
    
    args = parser.parse_args()
    
    if args.setup:
        print("Setting up Manus-Notion API Bridge...")
        print("Please edit the configuration file with your credentials:")
        print(f"  {CONFIG_FILE}")
        
        # Create default config if it doesn't exist
        sync_manager = NotionSyncManager(args.config)
        print("Default configuration created.")
        return
    
    try:
        sync_manager = NotionSyncManager(args.config)
        
        if args.status:
            status = sync_manager.get_status()
            print("Synchronization Status:")
            for key, value in status.items():
                print(f"  {key}: {value}")
            return
        
        if args.sync_once:
            results = sync_manager.perform_full_sync()
            print("Synchronization Results:")
            for directory, count in results.items():
                print(f"  {directory}: {count} files synced")
            return
        
        # Start continuous synchronization
        sync_manager.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            sync_manager.stop()
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

