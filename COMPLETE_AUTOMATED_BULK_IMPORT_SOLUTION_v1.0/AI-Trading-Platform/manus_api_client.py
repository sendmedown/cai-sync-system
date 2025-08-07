#!/usr/bin/env python3
"""
Manus API Client - Bidirectional Communication Bridge
===================================================

This module provides comprehensive API client functionality for communicating
with the Manus platform, enabling seamless integration with the Notion sync
system and supporting collaborative AI development workflows.

Author: Manus AI
Version: 1.0
Date: July 7, 2025
"""

import os
import json
import time
import logging
import requests
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import websocket
import ssl

class TaskStatus(Enum):
    """Enumeration of task status values"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ContentType(Enum):
    """Enumeration of content types"""
    DOCUMENT = "document"
    CODE = "code"
    DIAGRAM = "diagram"
    PRESENTATION = "presentation"
    DATA = "data"
    CONFIGURATION = "configuration"

@dataclass
class ManusTask:
    """Data structure for Manus task representation"""
    task_id: str
    title: str
    description: str
    content_type: ContentType
    priority: int
    status: TaskStatus
    created_at: str
    updated_at: str
    assigned_to: Optional[str] = None
    deadline: Optional[str] = None
    dependencies: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    result_content: Optional[str] = None
    result_files: Optional[List[str]] = None

@dataclass
class ManusContent:
    """Data structure for content exchange with Manus"""
    content_id: str
    title: str
    content_type: ContentType
    content_data: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    version: int
    tags: Optional[List[str]] = None
    access_level: str = "internal"

@dataclass
class ManusApiConfig:
    """Configuration for Manus API client"""
    api_endpoint: str
    api_key: str
    websocket_endpoint: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5
    enable_websocket: bool = True
    enable_auto_retry: bool = True

class ManusApiClient:
    """Main API client for Manus platform integration"""
    
    def __init__(self, config: ManusApiConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'Manus-Notion-Bridge/1.0'
        })
        
        self.logger = self._setup_logging()
        self.websocket = None
        self.websocket_thread = None
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.running = False
        
        # Task and content caches
        self.task_cache: Dict[str, ManusTask] = {}
        self.content_cache: Dict[str, ManusContent] = {}
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the API client"""
        logger = logging.getLogger('manus_api_client')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry logic"""
        url = f"{self.config.api_endpoint.rstrip('/')}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.config.timeout,
                    **kwargs
                )
                
                if response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', self.config.retry_delay))
                    self.logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries:
                    self.logger.error(f"Request failed after {self.config.max_retries} retries: {e}")
                    raise
                
                self.logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                time.sleep(self.config.retry_delay * (attempt + 1))
        
        raise requests.exceptions.RequestException("Max retries exceeded")
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler for WebSocket events"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def _trigger_event(self, event_type: str, data: Any):
        """Trigger registered event handlers"""
        handlers = self.event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                self.logger.error(f"Error in event handler for {event_type}: {e}")
    
    def _websocket_on_message(self, ws, message):
        """Handle WebSocket messages"""
        try:
            data = json.loads(message)
            event_type = data.get('type', 'unknown')
            self.logger.debug(f"Received WebSocket event: {event_type}")
            self._trigger_event(event_type, data)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in WebSocket message: {e}")
        except Exception as e:
            self.logger.error(f"Error processing WebSocket message: {e}")
    
    def _websocket_on_error(self, ws, error):
        """Handle WebSocket errors"""
        self.logger.error(f"WebSocket error: {error}")
    
    def _websocket_on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        self.logger.info("WebSocket connection closed")
        
        # Attempt to reconnect if still running
        if self.running and self.config.enable_auto_retry:
            self.logger.info("Attempting to reconnect WebSocket...")
            time.sleep(self.config.retry_delay)
            self._start_websocket()
    
    def _websocket_on_open(self, ws):
        """Handle WebSocket open"""
        self.logger.info("WebSocket connection established")
        
        # Send authentication message
        auth_message = {
            'type': 'authenticate',
            'token': self.config.api_key
        }
        ws.send(json.dumps(auth_message))
    
    def _start_websocket(self):
        """Start WebSocket connection"""
        if not self.config.websocket_endpoint or not self.config.enable_websocket:
            return
        
        try:
            self.websocket = websocket.WebSocketApp(
                self.config.websocket_endpoint,
                on_message=self._websocket_on_message,
                on_error=self._websocket_on_error,
                on_close=self._websocket_on_close,
                on_open=self._websocket_on_open
            )
            
            # Start WebSocket in separate thread
            self.websocket_thread = threading.Thread(
                target=self.websocket.run_forever,
                kwargs={'sslopt': {"cert_reqs": ssl.CERT_NONE}},
                daemon=True
            )
            self.websocket_thread.start()
            
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket: {e}")
    
    def start(self):
        """Start the API client"""
        self.logger.info("Starting Manus API client")
        self.running = True
        
        # Test API connection
        try:
            self.get_status()
            self.logger.info("API connection verified")
        except Exception as e:
            self.logger.error(f"Failed to verify API connection: {e}")
            raise
        
        # Start WebSocket connection
        self._start_websocket()
        
        self.logger.info("Manus API client started successfully")
    
    def stop(self):
        """Stop the API client"""
        self.logger.info("Stopping Manus API client")
        self.running = False
        
        if self.websocket:
            self.websocket.close()
        
        if self.websocket_thread:
            self.websocket_thread.join(timeout=5)
        
        self.logger.info("Manus API client stopped")
    
    # API Methods
    
    def get_status(self) -> Dict[str, Any]:
        """Get Manus platform status"""
        response = self._make_request('GET', '/api/v1/status')
        return response.json()
    
    def create_task(self, task: ManusTask) -> ManusTask:
        """Create a new task in Manus"""
        task_data = asdict(task)
        task_data['content_type'] = task.content_type.value
        task_data['status'] = task.status.value
        
        response = self._make_request('POST', '/api/v1/tasks', json=task_data)
        result_data = response.json()
        
        created_task = ManusTask(
            task_id=result_data['task_id'],
            title=result_data['title'],
            description=result_data['description'],
            content_type=ContentType(result_data['content_type']),
            priority=result_data['priority'],
            status=TaskStatus(result_data['status']),
            created_at=result_data['created_at'],
            updated_at=result_data['updated_at'],
            assigned_to=result_data.get('assigned_to'),
            deadline=result_data.get('deadline'),
            dependencies=result_data.get('dependencies'),
            metadata=result_data.get('metadata')
        )
        
        self.task_cache[created_task.task_id] = created_task
        return created_task
    
    def get_task(self, task_id: str) -> Optional[ManusTask]:
        """Get task by ID"""
        # Check cache first
        if task_id in self.task_cache:
            return self.task_cache[task_id]
        
        try:
            response = self._make_request('GET', f'/api/v1/tasks/{task_id}')
            task_data = response.json()
            
            task = ManusTask(
                task_id=task_data['task_id'],
                title=task_data['title'],
                description=task_data['description'],
                content_type=ContentType(task_data['content_type']),
                priority=task_data['priority'],
                status=TaskStatus(task_data['status']),
                created_at=task_data['created_at'],
                updated_at=task_data['updated_at'],
                assigned_to=task_data.get('assigned_to'),
                deadline=task_data.get('deadline'),
                dependencies=task_data.get('dependencies'),
                metadata=task_data.get('metadata'),
                result_content=task_data.get('result_content'),
                result_files=task_data.get('result_files')
            )
            
            self.task_cache[task_id] = task
            return task
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    def update_task(self, task: ManusTask) -> ManusTask:
        """Update an existing task"""
        task_data = asdict(task)
        task_data['content_type'] = task.content_type.value
        task_data['status'] = task.status.value
        
        response = self._make_request('PUT', f'/api/v1/tasks/{task.task_id}', json=task_data)
        result_data = response.json()
        
        updated_task = ManusTask(
            task_id=result_data['task_id'],
            title=result_data['title'],
            description=result_data['description'],
            content_type=ContentType(result_data['content_type']),
            priority=result_data['priority'],
            status=TaskStatus(result_data['status']),
            created_at=result_data['created_at'],
            updated_at=result_data['updated_at'],
            assigned_to=result_data.get('assigned_to'),
            deadline=result_data.get('deadline'),
            dependencies=result_data.get('dependencies'),
            metadata=result_data.get('metadata'),
            result_content=result_data.get('result_content'),
            result_files=result_data.get('result_files')
        )
        
        self.task_cache[updated_task.task_id] = updated_task
        return updated_task
    
    def list_tasks(self, status: Optional[TaskStatus] = None, 
                   content_type: Optional[ContentType] = None,
                   limit: int = 100) -> List[ManusTask]:
        """List tasks with optional filtering"""
        params = {'limit': limit}
        if status:
            params['status'] = status.value
        if content_type:
            params['content_type'] = content_type.value
        
        response = self._make_request('GET', '/api/v1/tasks', params=params)
        tasks_data = response.json()
        
        tasks = []
        for task_data in tasks_data.get('tasks', []):
            task = ManusTask(
                task_id=task_data['task_id'],
                title=task_data['title'],
                description=task_data['description'],
                content_type=ContentType(task_data['content_type']),
                priority=task_data['priority'],
                status=TaskStatus(task_data['status']),
                created_at=task_data['created_at'],
                updated_at=task_data['updated_at'],
                assigned_to=task_data.get('assigned_to'),
                deadline=task_data.get('deadline'),
                dependencies=task_data.get('dependencies'),
                metadata=task_data.get('metadata'),
                result_content=task_data.get('result_content'),
                result_files=task_data.get('result_files')
            )
            tasks.append(task)
            self.task_cache[task.task_id] = task
        
        return tasks
    
    def submit_content(self, content: ManusContent) -> ManusContent:
        """Submit content to Manus"""
        content_data = asdict(content)
        content_data['content_type'] = content.content_type.value
        
        response = self._make_request('POST', '/api/v1/content', json=content_data)
        result_data = response.json()
        
        submitted_content = ManusContent(
            content_id=result_data['content_id'],
            title=result_data['title'],
            content_type=ContentType(result_data['content_type']),
            content_data=result_data['content_data'],
            metadata=result_data['metadata'],
            created_at=result_data['created_at'],
            updated_at=result_data['updated_at'],
            version=result_data['version'],
            tags=result_data.get('tags'),
            access_level=result_data.get('access_level', 'internal')
        )
        
        self.content_cache[submitted_content.content_id] = submitted_content
        return submitted_content
    
    def get_content(self, content_id: str) -> Optional[ManusContent]:
        """Get content by ID"""
        # Check cache first
        if content_id in self.content_cache:
            return self.content_cache[content_id]
        
        try:
            response = self._make_request('GET', f'/api/v1/content/{content_id}')
            content_data = response.json()
            
            content = ManusContent(
                content_id=content_data['content_id'],
                title=content_data['title'],
                content_type=ContentType(content_data['content_type']),
                content_data=content_data['content_data'],
                metadata=content_data['metadata'],
                created_at=content_data['created_at'],
                updated_at=content_data['updated_at'],
                version=content_data['version'],
                tags=content_data.get('tags'),
                access_level=content_data.get('access_level', 'internal')
            )
            
            self.content_cache[content_id] = content
            return content
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    def request_ai_assistance(self, prompt: str, context: Dict[str, Any] = None,
                            content_type: ContentType = ContentType.DOCUMENT) -> str:
        """Request AI assistance from Manus"""
        request_data = {
            'prompt': prompt,
            'content_type': content_type.value,
            'context': context or {}
        }
        
        response = self._make_request('POST', '/api/v1/ai/assist', json=request_data)
        result = response.json()
        
        return result.get('response', '')
    
    def upload_file(self, file_path: str, metadata: Dict[str, Any] = None) -> str:
        """Upload file to Manus"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'metadata': json.dumps(metadata or {})}
            
            # Temporarily remove Content-Type header for file upload
            headers = self.session.headers.copy()
            if 'Content-Type' in headers:
                del headers['Content-Type']
            
            response = requests.post(
                f"{self.config.api_endpoint}/api/v1/files",
                files=files,
                data=data,
                headers=headers,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('file_id', '')
    
    def download_file(self, file_id: str, output_path: str) -> bool:
        """Download file from Manus"""
        try:
            response = self._make_request('GET', f'/api/v1/files/{file_id}')
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error downloading file {file_id}: {e}")
            return False
    
    def get_project_context(self, project_id: str = None) -> Dict[str, Any]:
        """Get current project context from Manus"""
        params = {}
        if project_id:
            params['project_id'] = project_id
        
        response = self._make_request('GET', '/api/v1/context', params=params)
        return response.json()
    
    def update_project_context(self, context_data: Dict[str, Any], 
                             project_id: str = None) -> bool:
        """Update project context in Manus"""
        request_data = {
            'context': context_data
        }
        if project_id:
            request_data['project_id'] = project_id
        
        try:
            self._make_request('PUT', '/api/v1/context', json=request_data)
            return True
        except Exception as e:
            self.logger.error(f"Error updating project context: {e}")
            return False

# Utility functions for integration

def create_manus_client_from_config(config_file: str = "manus_config.yaml") -> ManusApiClient:
    """Create Manus API client from configuration file"""
    import yaml
    
    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        api_config = ManusApiConfig(**config_data)
        return ManusApiClient(api_config)
        
    except FileNotFoundError:
        # Create default config
        default_config = {
            'api_endpoint': 'https://api.manus.space',
            'api_key': 'YOUR_MANUS_API_KEY_HERE',
            'websocket_endpoint': 'wss://api.manus.space/ws',
            'timeout': 30,
            'max_retries': 3,
            'retry_delay': 5,
            'enable_websocket': True,
            'enable_auto_retry': True
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        print(f"Created default Manus config at {config_file}")
        print("Please update with your API credentials")
        
        api_config = ManusApiConfig(**default_config)
        return ManusApiClient(api_config)

def sync_local_file_to_manus(client: ManusApiClient, file_path: str, 
                           content_type: ContentType = ContentType.DOCUMENT) -> Optional[str]:
    """Sync a local file to Manus platform"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content_data = f.read()
        
        content = ManusContent(
            content_id="",  # Will be assigned by server
            title=os.path.basename(file_path),
            content_type=content_type,
            content_data=content_data,
            metadata={
                'source_file': file_path,
                'sync_timestamp': datetime.now().isoformat()
            },
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            version=1
        )
        
        result = client.submit_content(content)
        return result.content_id
        
    except Exception as e:
        client.logger.error(f"Error syncing file {file_path} to Manus: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    client = create_manus_client_from_config()
    
    try:
        client.start()
        
        # Example: Get status
        status = client.get_status()
        print(f"Manus status: {status}")
        
        # Example: Create a task
        task = ManusTask(
            task_id="",
            title="Test Task",
            description="This is a test task",
            content_type=ContentType.DOCUMENT,
            priority=1,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        created_task = client.create_task(task)
        print(f"Created task: {created_task.task_id}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.stop()

