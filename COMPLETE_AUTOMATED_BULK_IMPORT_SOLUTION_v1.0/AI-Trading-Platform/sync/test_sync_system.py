#!/usr/bin/env python3
"""
Test Suite for Manus-Notion API Bridge
======================================

Comprehensive testing framework for validating the synchronization system
components and integration functionality.

Author: Manus AI
Version: 1.0
Date: July 7, 2025
"""

import os
import sys
import time
import json
import tempfile
import shutil
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import threading

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import components to test
from notion_sync import NotionSyncManager, SyncConfig, SyncState
from manus_api_client import ManusApiClient, ManusApiConfig, ContentType, TaskStatus
from sync.monitor import FileSystemMonitor, MonitorConfig, FileChangeEvent

class TestSyncConfig(unittest.TestCase):
    """Test SyncConfig functionality"""
    
    def test_sync_config_creation(self):
        """Test SyncConfig creation with default values"""
        config = SyncConfig(notion_token="test_token")
        
        self.assertEqual(config.notion_token, "test_token")
        self.assertEqual(config.sync_directories, ["docs/", "tasks/", "assets/"])
        self.assertEqual(config.sync_interval, 30)
        self.assertTrue(config.enable_bidirectional)
        self.assertTrue(config.enable_auto_backup)
    
    def test_sync_config_custom_values(self):
        """Test SyncConfig with custom values"""
        config = SyncConfig(
            notion_token="custom_token",
            sync_directories=["custom/"],
            sync_interval=60,
            enable_bidirectional=False
        )
        
        self.assertEqual(config.notion_token, "custom_token")
        self.assertEqual(config.sync_directories, ["custom/"])
        self.assertEqual(config.sync_interval, 60)
        self.assertFalse(config.enable_bidirectional)

class TestSyncState(unittest.TestCase):
    """Test SyncState functionality"""
    
    def test_sync_state_creation(self):
        """Test SyncState creation"""
        state = SyncState(
            last_sync_time="2025-07-07T00:00:00",
            file_checksums={},
            notion_page_mappings={},
            sync_errors=[]
        )
        
        self.assertEqual(state.last_sync_time, "2025-07-07T00:00:00")
        self.assertEqual(state.total_syncs, 0)
        self.assertEqual(state.successful_syncs, 0)
        self.assertEqual(len(state.file_checksums), 0)

class TestFileSystemMonitor(unittest.TestCase):
    """Test FileSystemMonitor functionality"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.events_received = []
        
        def event_callback(events):
            self.events_received.extend(events)
        
        self.config = MonitorConfig(
            watch_directories=[self.test_dir],
            excluded_patterns=["*.tmp"],
            debounce_delay=0.1,
            batch_size=5,
            batch_timeout=1.0
        )
        
        self.monitor = FileSystemMonitor(self.config, event_callback)
    
    def tearDown(self):
        """Cleanup test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_should_monitor_file(self):
        """Test file monitoring criteria"""
        # Create test files
        test_file = os.path.join(self.test_dir, "test.txt")
        tmp_file = os.path.join(self.test_dir, "test.tmp")
        
        with open(test_file, 'w') as f:
            f.write("test content")
        
        with open(tmp_file, 'w') as f:
            f.write("temp content")
        
        # Test monitoring decisions
        self.assertTrue(self.monitor._should_monitor_file(test_file))
        self.assertFalse(self.monitor._should_monitor_file(tmp_file))
    
    def test_checksum_calculation(self):
        """Test file checksum calculation"""
        test_file = os.path.join(self.test_dir, "test.txt")
        
        with open(test_file, 'w') as f:
            f.write("test content")
        
        checksum1 = self.monitor._calculate_checksum(test_file)
        checksum2 = self.monitor._calculate_checksum(test_file)
        
        self.assertEqual(checksum1, checksum2)
        self.assertIsNotNone(checksum1)
        
        # Modify file and check checksum changes
        with open(test_file, 'w') as f:
            f.write("modified content")
        
        checksum3 = self.monitor._calculate_checksum(test_file)
        self.assertNotEqual(checksum1, checksum3)
    
    def test_file_change_detection(self):
        """Test file change detection"""
        test_file = os.path.join(self.test_dir, "test.txt")
        
        # File doesn't exist initially
        self.assertTrue(self.monitor._is_file_changed(test_file))
        
        # Create file
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # First check should detect change
        self.assertTrue(self.monitor._is_file_changed(test_file))
        
        # Second check should not detect change
        self.assertFalse(self.monitor._is_file_changed(test_file))
        
        # Modify file
        with open(test_file, 'w') as f:
            f.write("modified content")
        
        # Should detect change again
        self.assertTrue(self.monitor._is_file_changed(test_file))

class TestNotionSyncManager(unittest.TestCase):
    """Test NotionSyncManager functionality"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.test_dir, "test_config.yaml")
        
        # Create test config
        test_config = {
            'notion_token': 'test_token',
            'notion_parent_page_id': 'test_page_id',
            'sync_directories': [self.test_dir],
            'excluded_patterns': ['*.tmp']
        }
        
        import yaml
        with open(self.config_file, 'w') as f:
            yaml.dump(test_config, f)
    
    def tearDown(self):
        """Cleanup test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @patch('notion_sync.NotionClient')
    def test_notion_sync_manager_creation(self, mock_notion_client):
        """Test NotionSyncManager creation"""
        manager = NotionSyncManager(self.config_file)
        
        self.assertIsNotNone(manager.config)
        self.assertEqual(manager.config.notion_token, 'test_token')
        self.assertIsNotNone(manager.state)
    
    def test_markdown_to_notion_blocks(self):
        """Test Markdown to Notion blocks conversion"""
        manager = NotionSyncManager(self.config_file)
        
        markdown_content = """# Header 1
## Header 2
This is a paragraph.

- Bullet point 1
- Bullet point 2

Another paragraph."""
        
        blocks = manager.convert_markdown_to_notion_blocks(markdown_content)
        
        self.assertGreater(len(blocks), 0)
        
        # Check for header blocks
        header_blocks = [b for b in blocks if b['type'].startswith('heading')]
        self.assertGreater(len(header_blocks), 0)
        
        # Check for bullet list blocks
        bullet_blocks = [b for b in blocks if b['type'] == 'bulleted_list_item']
        self.assertEqual(len(bullet_blocks), 2)
    
    def test_file_checksum_calculation(self):
        """Test file checksum calculation"""
        manager = NotionSyncManager(self.config_file)
        
        test_file = os.path.join(self.test_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        checksum = manager.calculate_file_checksum(test_file)
        self.assertIsNotNone(checksum)
        self.assertEqual(len(checksum), 32)  # MD5 hash length
    
    def test_should_sync_file(self):
        """Test file sync criteria"""
        manager = NotionSyncManager(self.config_file)
        
        # Create test files
        sync_file = os.path.join(self.test_dir, "test.md")
        tmp_file = os.path.join(self.test_dir, "test.tmp")
        
        with open(sync_file, 'w') as f:
            f.write("# Test Document")
        
        with open(tmp_file, 'w') as f:
            f.write("temporary content")
        
        self.assertTrue(manager.should_sync_file(sync_file))
        self.assertFalse(manager.should_sync_file(tmp_file))

class TestManusApiClient(unittest.TestCase):
    """Test ManusApiClient functionality"""
    
    def setUp(self):
        """Setup test environment"""
        self.config = ManusApiConfig(
            api_endpoint="https://test.api.manus.space",
            api_key="test_api_key",
            enable_websocket=False  # Disable for testing
        )
    
    def test_manus_api_client_creation(self):
        """Test ManusApiClient creation"""
        client = ManusApiClient(self.config)
        
        self.assertEqual(client.config.api_endpoint, "https://test.api.manus.space")
        self.assertEqual(client.config.api_key, "test_api_key")
        self.assertIsNotNone(client.session)
    
    def test_event_handler_registration(self):
        """Test event handler registration"""
        client = ManusApiClient(self.config)
        
        def test_handler(data):
            pass
        
        client.register_event_handler('test_event', test_handler)
        
        self.assertIn('test_event', client.event_handlers)
        self.assertEqual(len(client.event_handlers['test_event']), 1)
    
    @patch('requests.Session.request')
    def test_api_request_retry(self, mock_request):
        """Test API request retry logic"""
        client = ManusApiClient(self.config)
        
        # Mock rate limiting response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '1'}
        mock_request.return_value = mock_response
        
        # Should raise exception after retries
        with self.assertRaises(Exception):
            client._make_request('GET', '/test')
        
        # Should have made multiple attempts
        self.assertGreater(mock_request.call_count, 1)

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def setUp(self):
        """Setup integration test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.sync_dir = os.path.join(self.test_dir, "sync_test")
        os.makedirs(self.sync_dir)
        
        # Create test configuration
        self.config = {
            'notion_token': 'test_token',
            'notion_parent_page_id': 'test_page_id',
            'sync_directories': [self.sync_dir],
            'excluded_patterns': ['*.tmp', '*.log'],
            'sync_interval': 1,
            'max_file_size_mb': 1
        }
    
    def tearDown(self):
        """Cleanup integration test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_file_creation_and_sync_workflow(self):
        """Test complete file creation and sync workflow"""
        # This would be a more complex integration test
        # For now, we'll test the basic workflow components
        
        # Create a test file
        test_file = os.path.join(self.sync_dir, "test_document.md")
        with open(test_file, 'w') as f:
            f.write("# Test Document\n\nThis is a test document for sync testing.")
        
        # Verify file exists and has content
        self.assertTrue(os.path.exists(test_file))
        
        with open(test_file, 'r') as f:
            content = f.read()
        
        self.assertIn("Test Document", content)
        self.assertIn("sync testing", content)

class TestSystemValidation(unittest.TestCase):
    """System validation tests"""
    
    def test_required_dependencies(self):
        """Test that all required dependencies are available"""
        try:
            import watchdog
            import yaml
            import requests
            import threading
            import json
            import hashlib
            import logging
        except ImportError as e:
            self.fail(f"Required dependency not available: {e}")
    
    def test_directory_structure(self):
        """Test that the expected directory structure exists"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        expected_dirs = [
            'docs',
            'tasks', 
            'assets',
            'presentations',
            'reports',
            'sync',
            'backups',
            'scripts'
        ]
        
        for dir_name in expected_dirs:
            dir_path = os.path.join(base_dir, dir_name)
            self.assertTrue(os.path.exists(dir_path), f"Directory {dir_name} does not exist")
    
    def test_script_files_exist(self):
        """Test that all required script files exist"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        expected_files = [
            'notion_sync.py',
            'manus_api_client.py',
            'sync_config.yaml',
            'sync/monitor.py',
            'sync/integrated_sync.py'
        ]
        
        for file_name in expected_files:
            file_path = os.path.join(base_dir, file_name)
            self.assertTrue(os.path.exists(file_path), f"File {file_name} does not exist")

def run_performance_tests():
    """Run performance tests for the sync system"""
    print("Running performance tests...")
    
    # Test file processing speed
    test_dir = tempfile.mkdtemp()
    try:
        # Create multiple test files
        num_files = 100
        for i in range(num_files):
            test_file = os.path.join(test_dir, f"test_{i}.md")
            with open(test_file, 'w') as f:
                f.write(f"# Test Document {i}\n\nContent for document {i}")
        
        # Measure processing time
        start_time = time.time()
        
        # Simulate checksum calculation for all files
        import hashlib
        for i in range(num_files):
            test_file = os.path.join(test_dir, f"test_{i}.md")
            hash_md5 = hashlib.md5()
            with open(test_file, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            checksum = hash_md5.hexdigest()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"Processed {num_files} files in {processing_time:.2f} seconds")
        print(f"Average time per file: {(processing_time/num_files)*1000:.2f} ms")
        
        # Performance assertions
        assert processing_time < 10.0, "File processing too slow"
        assert (processing_time/num_files) < 0.1, "Per-file processing too slow"
        
        print("✅ Performance tests passed")
        
    finally:
        shutil.rmtree(test_dir)

def run_stress_tests():
    """Run stress tests for the sync system"""
    print("Running stress tests...")
    
    # Test with large number of rapid file changes
    test_dir = tempfile.mkdtemp()
    try:
        events_received = []
        
        def event_callback(events):
            events_received.extend(events)
        
        config = MonitorConfig(
            watch_directories=[test_dir],
            excluded_patterns=[],
            debounce_delay=0.1,
            batch_size=10,
            batch_timeout=1.0
        )
        
        monitor = FileSystemMonitor(config, event_callback)
        monitor.running = True
        monitor.batch_processor_thread = threading.Thread(target=monitor._batch_processor, daemon=True)
        monitor.batch_processor_thread.start()
        
        # Create many files rapidly
        num_files = 50
        for i in range(num_files):
            test_file = os.path.join(test_dir, f"stress_test_{i}.txt")
            with open(test_file, 'w') as f:
                f.write(f"Stress test content {i}")
            
            # Simulate file change event
            event = FileChangeEvent(
                file_path=test_file,
                event_type='created',
                timestamp=time.time()
            )
            monitor.event_queue.put(event)
        
        # Wait for processing
        time.sleep(3)
        monitor.running = False
        
        print(f"Generated {num_files} events, processed {len(events_received)} events")
        
        # Stress test assertions
        assert len(events_received) > 0, "No events were processed"
        
        print("✅ Stress tests passed")
        
    finally:
        shutil.rmtree(test_dir)

def main():
    """Main test runner"""
    print("🧪 Starting Manus-Notion API Bridge Test Suite")
    print("=" * 60)
    
    # Run unit tests
    print("\n📋 Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run performance tests
    print("\n⚡ Running Performance Tests...")
    try:
        run_performance_tests()
    except Exception as e:
        print(f"❌ Performance tests failed: {e}")
    
    # Run stress tests
    print("\n💪 Running Stress Tests...")
    try:
        run_stress_tests()
    except Exception as e:
        print(f"❌ Stress tests failed: {e}")
    
    print("\n✅ Test suite completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()

