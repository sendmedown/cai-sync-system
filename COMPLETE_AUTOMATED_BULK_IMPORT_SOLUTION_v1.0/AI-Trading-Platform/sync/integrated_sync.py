#!/usr/bin/env python3
"""
Integrated Manus-Notion Sync System
===================================

This is the main integration script that combines file monitoring, Notion sync,
and Manus API communication into a unified synchronization system.

Author: Manus AI
Version: 1.0
Date: July 7, 2025
"""

import os
import sys
import time
import json
import yaml
import logging
import threading
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from notion_sync import NotionSyncManager, SyncConfig
from manus_api_client import ManusApiClient, ManusApiConfig, ContentType, TaskStatus
from sync.monitor import FileSystemMonitor, MonitorConfig, FileChangeEvent, start_monitoring, stop_monitoring

class IntegratedSyncSystem:
    """Main integrated synchronization system"""
    
    def __init__(self, config_file: str = "sync_config.yaml"):
        self.config_file = config_file
        self.config = self._load_config()
        
        # Initialize components
        self.notion_sync = None
        self.manus_client = None
        self.file_monitor = None
        
        self.running = False
        self.logger = self._setup_logging()
        
        # Statistics
        self.stats = {
            'files_synced': 0,
            'notion_updates': 0,
            'manus_tasks': 0,
            'errors': 0,
            'start_time': None
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {self.config_file}")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing configuration file: {e}")
            raise
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the integrated system"""
        logger = logging.getLogger('integrated_sync')
        logger.setLevel(logging.INFO)
        
        # File handler
        log_file = self.config.get('advanced', {}).get('log_file', 'integrated_sync.log')
        file_handler = logging.FileHandler(log_file)
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
        
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        return logger
    
    def _initialize_notion_sync(self):
        """Initialize Notion synchronization component"""
        try:
            notion_config = SyncConfig(
                notion_token=self.config['notion_token'],
                notion_database_id=self.config.get('notion_database_id'),
                notion_parent_page_id=self.config.get('notion_parent_page_id'),
                sync_directories=self.config.get('sync_directories', []),
                excluded_patterns=self.config.get('excluded_patterns', []),
                sync_interval=self.config.get('sync_interval', 30),
                enable_bidirectional=self.config.get('enable_bidirectional', True),
                enable_auto_backup=self.config.get('enable_auto_backup', True),
                max_file_size_mb=self.config.get('max_file_size_mb', 50)
            )
            
            self.notion_sync = NotionSyncManager()
            self.notion_sync.config = notion_config
            self.logger.info("Notion sync component initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Notion sync: {e}")
            raise
    
    def _initialize_manus_client(self):
        """Initialize Manus API client"""
        try:
            manus_config = ManusApiConfig(
                api_endpoint=self.config.get('manus_api_endpoint', 'https://api.manus.space'),
                api_key=self.config.get('manus_api_key', ''),
                timeout=self.config.get('advanced', {}).get('timeout', 30),
                max_retries=self.config.get('advanced', {}).get('max_retries', 3),
                retry_delay=self.config.get('advanced', {}).get('retry_delay', 5)
            )
            
            if manus_config.api_key and manus_config.api_key != 'YOUR_MANUS_API_KEY_HERE':
                self.manus_client = ManusApiClient(manus_config)
                
                # Register event handlers
                self.manus_client.register_event_handler('task_completed', self._handle_manus_task_completed)
                self.manus_client.register_event_handler('content_updated', self._handle_manus_content_updated)
                
                self.logger.info("Manus API client initialized")
            else:
                self.logger.warning("Manus API key not configured, skipping Manus integration")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Manus client: {e}")
            # Don't raise - Manus integration is optional
    
    def _initialize_file_monitor(self):
        """Initialize file system monitoring"""
        try:
            monitor_config = MonitorConfig(
                watch_directories=self.config.get('sync_directories', []),
                excluded_patterns=self.config.get('excluded_patterns', []),
                debounce_delay=1.0,
                batch_size=self.config.get('advanced', {}).get('batch_size', 10),
                batch_timeout=5.0,
                enable_checksums=True,
                max_file_size_mb=self.config.get('max_file_size_mb', 50)
            )
            
            self.file_monitor = start_monitoring(monitor_config, self._handle_file_changes)
            self.logger.info("File system monitoring initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize file monitor: {e}")
            raise
    
    def _handle_file_changes(self, events: List[FileChangeEvent]):
        """Handle file system change events"""
        try:
            self.logger.info(f"Processing {len(events)} file change events")
            
            for event in events:
                self.stats['files_synced'] += 1
                
                # Sync to Notion
                if self.notion_sync and event.event_type in ['created', 'modified']:
                    if os.path.exists(event.file_path):
                        success = self.notion_sync.sync_file_to_notion(event.file_path)
                        if success:
                            self.stats['notion_updates'] += 1
                        else:
                            self.stats['errors'] += 1
                
                # Sync to Manus if configured
                if self.manus_client and event.event_type in ['created', 'modified']:
                    self._sync_file_to_manus(event.file_path)
                
                # Handle deletions
                if event.event_type == 'deleted':
                    self._handle_file_deletion(event.file_path)
            
            # Save state after processing
            if self.notion_sync:
                self.notion_sync._save_state()
                
        except Exception as e:
            self.logger.error(f"Error handling file changes: {e}")
            self.stats['errors'] += 1
    
    def _sync_file_to_manus(self, file_path: str):
        """Sync a file to Manus platform"""
        try:
            if not os.path.exists(file_path):
                return
            
            # Determine content type based on file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext == '.md':
                content_type = ContentType.DOCUMENT
            elif file_ext in ['.py', '.js', '.html', '.css']:
                content_type = ContentType.CODE
            elif file_ext in ['.png', '.jpg', '.svg']:
                content_type = ContentType.DIAGRAM
            else:
                content_type = ContentType.DOCUMENT
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content_data = f.read()
            
            # Create content object
            from manus_api_client import ManusContent
            content = ManusContent(
                content_id="",
                title=os.path.basename(file_path),
                content_type=content_type,
                content_data=content_data,
                metadata={
                    'source_file': file_path,
                    'sync_timestamp': datetime.now().isoformat(),
                    'file_size': os.path.getsize(file_path)
                },
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                version=1
            )
            
            # Submit to Manus
            result = self.manus_client.submit_content(content)
            if result:
                self.logger.info(f"Synced {file_path} to Manus: {result.content_id}")
            
        except Exception as e:
            self.logger.error(f"Error syncing {file_path} to Manus: {e}")
    
    def _handle_file_deletion(self, file_path: str):
        """Handle file deletion events"""
        try:
            # Remove from Notion sync state
            if self.notion_sync:
                if file_path in self.notion_sync.state.file_checksums:
                    del self.notion_sync.state.file_checksums[file_path]
                
                # Optionally delete from Notion (based on configuration)
                if self.config.get('delete_from_notion_on_local_delete', False):
                    page_id = self.notion_sync.state.notion_page_mappings.get(file_path)
                    if page_id:
                        try:
                            # Note: Notion API doesn't support page deletion
                            # We could archive or move to trash instead
                            self.logger.info(f"File {file_path} deleted locally, Notion page preserved")
                        except Exception as e:
                            self.logger.error(f"Error handling Notion page for deleted file: {e}")
            
            self.logger.info(f"Handled deletion of {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error handling file deletion: {e}")
    
    def _handle_manus_task_completed(self, data: Dict[str, Any]):
        """Handle Manus task completion events"""
        try:
            task_id = data.get('task_id')
            result_files = data.get('result_files', [])
            
            self.logger.info(f"Manus task completed: {task_id}")
            self.stats['manus_tasks'] += 1
            
            # Download result files if any
            for file_id in result_files:
                output_path = f"manus_results/{task_id}_{file_id}"
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                if self.manus_client.download_file(file_id, output_path):
                    self.logger.info(f"Downloaded Manus result: {output_path}")
                    
                    # Trigger sync of the downloaded file
                    if self.notion_sync:
                        self.notion_sync.sync_file_to_notion(output_path)
            
        except Exception as e:
            self.logger.error(f"Error handling Manus task completion: {e}")
    
    def _handle_manus_content_updated(self, data: Dict[str, Any]):
        """Handle Manus content update events"""
        try:
            content_id = data.get('content_id')
            self.logger.info(f"Manus content updated: {content_id}")
            
            # Fetch updated content and sync locally
            if self.manus_client:
                content = self.manus_client.get_content(content_id)
                if content:
                    # Save to local file
                    local_path = f"manus_content/{content.title}"
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    
                    with open(local_path, 'w', encoding='utf-8') as f:
                        f.write(content.content_data)
                    
                    self.logger.info(f"Updated local file from Manus: {local_path}")
            
        except Exception as e:
            self.logger.error(f"Error handling Manus content update: {e}")
    
    def start(self):
        """Start the integrated synchronization system"""
        try:
            self.logger.info("Starting Integrated Manus-Notion Sync System")
            self.stats['start_time'] = datetime.now().isoformat()
            self.running = True
            
            # Initialize components
            self._initialize_notion_sync()
            self._initialize_manus_client()
            self._initialize_file_monitor()
            
            # Start Notion sync
            if self.notion_sync:
                self.notion_sync.start()
            
            # Start Manus client
            if self.manus_client:
                self.manus_client.start()
            
            # Perform initial sync
            self._perform_initial_sync()
            
            self.logger.info("Integrated sync system started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start integrated sync system: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Stop the integrated synchronization system"""
        try:
            self.logger.info("Stopping Integrated Manus-Notion Sync System")
            self.running = False
            
            # Stop file monitor
            if self.file_monitor:
                stop_monitoring(self.file_monitor)
            
            # Stop Notion sync
            if self.notion_sync:
                self.notion_sync.stop()
            
            # Stop Manus client
            if self.manus_client:
                self.manus_client.stop()
            
            self.logger.info("Integrated sync system stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping integrated sync system: {e}")
    
    def _perform_initial_sync(self):
        """Perform initial synchronization of all files"""
        try:
            self.logger.info("Performing initial synchronization")
            
            if self.notion_sync:
                results = self.notion_sync.perform_full_sync()
                total_synced = sum(results.values())
                self.stats['notion_updates'] += total_synced
                self.logger.info(f"Initial sync completed: {total_synced} files synced to Notion")
            
        except Exception as e:
            self.logger.error(f"Error in initial sync: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        status = {
            'running': self.running,
            'start_time': self.stats['start_time'],
            'statistics': self.stats.copy()
        }
        
        if self.notion_sync:
            notion_status = self.notion_sync.get_status()
            status['notion'] = notion_status
        
        if self.manus_client:
            try:
                manus_status = self.manus_client.get_status()
                status['manus'] = manus_status
            except Exception as e:
                status['manus'] = {'error': str(e)}
        
        return status
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Integrated Manus-Notion Sync System")
    parser.add_argument("--config", default="sync_config.yaml", help="Configuration file path")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--initial-sync", action="store_true", help="Perform initial sync and exit")
    
    args = parser.parse_args()
    
    try:
        sync_system = IntegratedSyncSystem(args.config)
        
        if args.status:
            status = sync_system.get_status()
            print("Integrated Sync System Status:")
            print(json.dumps(status, indent=2))
            return
        
        if args.initial_sync:
            sync_system._initialize_notion_sync()
            sync_system._perform_initial_sync()
            print("Initial synchronization completed")
            return
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, sync_system._signal_handler)
        signal.signal(signal.SIGTERM, sync_system._signal_handler)
        
        # Start the system
        sync_system.start()
        
        # Keep running
        try:
            while sync_system.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
        sync_system.stop()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

