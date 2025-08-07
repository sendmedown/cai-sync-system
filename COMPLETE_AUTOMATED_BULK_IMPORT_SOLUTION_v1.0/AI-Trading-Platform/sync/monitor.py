#!/usr/bin/env python3
"""
File System Monitor for Manus-Notion API Bridge
==============================================

This script provides advanced file system monitoring capabilities with
intelligent change detection, batch processing, and integration with the
main synchronization system.

Author: Manus AI
Version: 1.0
Date: July 7, 2025
"""

import os
import sys
import time
import json
import logging
import hashlib
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Optional, Callable
from dataclasses import dataclass, asdict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
import queue

@dataclass
class FileChangeEvent:
    """Represents a file system change event"""
    file_path: str
    event_type: str  # created, modified, deleted, moved
    timestamp: str
    checksum: Optional[str] = None
    file_size: Optional[int] = None
    old_path: Optional[str] = None  # For move events

@dataclass
class MonitorConfig:
    """Configuration for file monitoring"""
    watch_directories: List[str]
    excluded_patterns: List[str]
    debounce_delay: float = 1.0  # seconds
    batch_size: int = 10
    batch_timeout: float = 5.0  # seconds
    enable_checksums: bool = True
    max_file_size_mb: int = 50

class FileSystemMonitor:
    """Advanced file system monitoring with intelligent change detection"""
    
    def __init__(self, config: MonitorConfig, change_callback: Callable[[List[FileChangeEvent]], None]):
        self.config = config
        self.change_callback = change_callback
        self.observer = Observer()
        self.event_queue = queue.Queue()
        self.file_checksums: Dict[str, str] = {}
        self.pending_events: Dict[str, FileChangeEvent] = {}
        self.last_event_time: Dict[str, float] = {}
        self.running = False
        
        self.logger = self._setup_logging()
        self.batch_processor_thread = None
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the monitor"""
        logger = logging.getLogger('file_monitor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _calculate_checksum(self, file_path: str) -> Optional[str]:
        """Calculate file checksum if enabled"""
        if not self.config.enable_checksums:
            return None
        
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (OSError, IOError):
            return None
    
    def _get_file_size(self, file_path: str) -> Optional[int]:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except (OSError, IOError):
            return None
    
    def _should_monitor_file(self, file_path: str) -> bool:
        """Determine if a file should be monitored"""
        # Check file size
        file_size = self._get_file_size(file_path)
        if file_size and file_size > (self.config.max_file_size_mb * 1024 * 1024):
            return False
        
        # Check excluded patterns
        file_name = os.path.basename(file_path)
        for pattern in self.config.excluded_patterns:
            if pattern.replace('*', '') in file_name or pattern in file_path:
                return False
        
        return True
    
    def _is_file_changed(self, file_path: str) -> bool:
        """Check if file has actually changed using checksum"""
        if not os.path.exists(file_path):
            return True  # File was deleted
        
        current_checksum = self._calculate_checksum(file_path)
        stored_checksum = self.file_checksums.get(file_path)
        
        if current_checksum != stored_checksum:
            if current_checksum:
                self.file_checksums[file_path] = current_checksum
            return True
        
        return False
    
    def _create_change_event(self, file_path: str, event_type: str, old_path: str = None) -> FileChangeEvent:
        """Create a file change event with metadata"""
        checksum = None
        file_size = None
        
        if os.path.exists(file_path) and event_type != 'deleted':
            checksum = self._calculate_checksum(file_path)
            file_size = self._get_file_size(file_path)
        
        return FileChangeEvent(
            file_path=file_path,
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            checksum=checksum,
            file_size=file_size,
            old_path=old_path
        )
    
    def _debounce_event(self, file_path: str, event_type: str, old_path: str = None):
        """Apply debouncing to file events"""
        current_time = time.time()
        last_time = self.last_event_time.get(file_path, 0)
        
        # Update last event time
        self.last_event_time[file_path] = current_time
        
        # If within debounce delay, update pending event
        if current_time - last_time < self.config.debounce_delay:
            self.pending_events[file_path] = self._create_change_event(file_path, event_type, old_path)
            return
        
        # Process immediately if outside debounce window
        event = self._create_change_event(file_path, event_type, old_path)
        self.pending_events[file_path] = event
        
        # Schedule processing after debounce delay
        def process_delayed():
            time.sleep(self.config.debounce_delay)
            if file_path in self.pending_events:
                delayed_event = self.pending_events.pop(file_path)
                self.event_queue.put(delayed_event)
        
        threading.Thread(target=process_delayed, daemon=True).start()
    
    def _batch_processor(self):
        """Process events in batches"""
        batch = []
        last_batch_time = time.time()
        
        while self.running:
            try:
                # Try to get an event with timeout
                try:
                    event = self.event_queue.get(timeout=1.0)
                    batch.append(event)
                except queue.Empty:
                    # Check if we should process partial batch
                    if batch and (time.time() - last_batch_time) > self.config.batch_timeout:
                        self._process_batch(batch)
                        batch = []
                        last_batch_time = time.time()
                    continue
                
                # Process batch if full or timeout reached
                if (len(batch) >= self.config.batch_size or 
                    (time.time() - last_batch_time) > self.config.batch_timeout):
                    self._process_batch(batch)
                    batch = []
                    last_batch_time = time.time()
                
            except Exception as e:
                self.logger.error(f"Error in batch processor: {e}")
                time.sleep(1)
        
        # Process remaining events
        if batch:
            self._process_batch(batch)
    
    def _process_batch(self, events: List[FileChangeEvent]):
        """Process a batch of file change events"""
        if not events:
            return
        
        # Filter out events for files that haven't actually changed
        filtered_events = []
        for event in events:
            if event.event_type == 'deleted' or self._is_file_changed(event.file_path):
                filtered_events.append(event)
        
        if filtered_events:
            self.logger.info(f"Processing batch of {len(filtered_events)} file changes")
            try:
                self.change_callback(filtered_events)
            except Exception as e:
                self.logger.error(f"Error in change callback: {e}")

class SyncEventHandler(FileSystemEventHandler):
    """File system event handler for the monitor"""
    
    def __init__(self, monitor: FileSystemMonitor):
        self.monitor = monitor
        super().__init__()
    
    def on_created(self, event: FileSystemEvent):
        if not event.is_directory and self.monitor._should_monitor_file(event.src_path):
            self.monitor.logger.debug(f"File created: {event.src_path}")
            self.monitor._debounce_event(event.src_path, 'created')
    
    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory and self.monitor._should_monitor_file(event.src_path):
            self.monitor.logger.debug(f"File modified: {event.src_path}")
            self.monitor._debounce_event(event.src_path, 'modified')
    
    def on_deleted(self, event: FileSystemEvent):
        if not event.is_directory:
            self.monitor.logger.debug(f"File deleted: {event.src_path}")
            self.monitor._debounce_event(event.src_path, 'deleted')
            # Remove from checksum cache
            self.monitor.file_checksums.pop(event.src_path, None)
    
    def on_moved(self, event: FileSystemEvent):
        if not event.is_directory:
            self.monitor.logger.debug(f"File moved: {event.src_path} -> {event.dest_path}")
            # Handle as delete + create
            self.monitor._debounce_event(event.src_path, 'deleted')
            if self.monitor._should_monitor_file(event.dest_path):
                self.monitor._debounce_event(event.dest_path, 'created', event.src_path)
            
            # Update checksum cache
            old_checksum = self.monitor.file_checksums.pop(event.src_path, None)
            if old_checksum and self.monitor._should_monitor_file(event.dest_path):
                self.monitor.file_checksums[event.dest_path] = old_checksum

def start_monitoring(config: MonitorConfig, change_callback: Callable[[List[FileChangeEvent]], None]) -> FileSystemMonitor:
    """Start file system monitoring with the given configuration"""
    monitor = FileSystemMonitor(config, change_callback)
    
    # Start batch processor
    monitor.running = True
    monitor.batch_processor_thread = threading.Thread(target=monitor._batch_processor, daemon=True)
    monitor.batch_processor_thread.start()
    
    # Setup file system observers
    event_handler = SyncEventHandler(monitor)
    
    for watch_dir in config.watch_directories:
        if os.path.exists(watch_dir):
            monitor.observer.schedule(event_handler, watch_dir, recursive=True)
            monitor.logger.info(f"Monitoring directory: {watch_dir}")
        else:
            monitor.logger.warning(f"Watch directory does not exist: {watch_dir}")
    
    monitor.observer.start()
    monitor.logger.info("File system monitoring started")
    
    return monitor

def stop_monitoring(monitor: FileSystemMonitor):
    """Stop file system monitoring"""
    monitor.logger.info("Stopping file system monitoring")
    monitor.running = False
    
    if monitor.observer:
        monitor.observer.stop()
        monitor.observer.join()
    
    if monitor.batch_processor_thread:
        monitor.batch_processor_thread.join(timeout=5)
    
    monitor.logger.info("File system monitoring stopped")

def save_monitor_state(monitor: FileSystemMonitor, state_file: str):
    """Save monitor state to file"""
    state_data = {
        'file_checksums': monitor.file_checksums,
        'last_save_time': datetime.now().isoformat()
    }
    
    try:
        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=2)
    except Exception as e:
        monitor.logger.error(f"Error saving monitor state: {e}")

def load_monitor_state(monitor: FileSystemMonitor, state_file: str):
    """Load monitor state from file"""
    try:
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state_data = json.load(f)
            
            monitor.file_checksums = state_data.get('file_checksums', {})
            monitor.logger.info(f"Loaded monitor state with {len(monitor.file_checksums)} file checksums")
    except Exception as e:
        monitor.logger.error(f"Error loading monitor state: {e}")

# Example usage and testing
if __name__ == "__main__":
    def example_callback(events: List[FileChangeEvent]):
        """Example callback function"""
        print(f"Received {len(events)} file change events:")
        for event in events:
            print(f"  {event.event_type}: {event.file_path}")
    
    # Example configuration
    config = MonitorConfig(
        watch_directories=["../docs", "../tasks", "../assets"],
        excluded_patterns=["*.tmp", "*.log", ".git/", "__pycache__/"],
        debounce_delay=1.0,
        batch_size=5,
        batch_timeout=3.0,
        enable_checksums=True,
        max_file_size_mb=50
    )
    
    # Start monitoring
    monitor = start_monitoring(config, example_callback)
    
    try:
        print("File monitoring started. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        stop_monitoring(monitor)

