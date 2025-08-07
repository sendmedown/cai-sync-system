#!/usr/bin/env python3
"""
Automated Notion Importer for Bulk File Collections
===================================================

This script provides comprehensive automated import capabilities for large file
collections into Notion workspaces. Designed specifically for Richard's 340-file
collection (4GB), this importer implements intelligent processing, organization,
and import strategies that eliminate manual import work.

Author: Manus AI
Version: 1.0
Date: July 7, 2025
Target: Zero manual import work for 340 files (4GB)
"""

import os
import json
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import concurrent.futures
from queue import Queue
import threading

# Import analysis results
from bulk_file_analyzer import FileAnalysis, CollectionAnalysis, BulkFileAnalyzer

# Notion integration
try:
    from notion_client import Client as NotionClient
    from notion_client.errors import APIResponseError, RequestTimeoutError
    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False
    print("Warning: notion-client not available. Install with: pip install notion-client")

# Content processing libraries
try:
    import textract
    TEXTRACT_AVAILABLE = True
except ImportError:
    TEXTRACT_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

@dataclass
class ImportJob:
    """Represents an individual file import job"""
    job_id: str
    file_analysis: FileAnalysis
    batch_id: int
    priority: int
    status: str = "pending"  # pending, processing, completed, failed
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    notion_page_id: Optional[str] = None
    notion_page_url: Optional[str] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    retry_count: int = 0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

@dataclass
class ImportBatch:
    """Represents a batch of import jobs"""
    batch_id: int
    jobs: List[ImportJob]
    status: str = "pending"
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    total_size: int = 0
    processing_time: float = 0.0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        self.total_files = len(self.jobs)
        self.total_size = sum(job.file_analysis.file_size for job in self.jobs)

@dataclass
class ImportResults:
    """Overall import operation results"""
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_processing_time: float
    total_size_processed: int
    pages_created: int
    databases_created: int
    files_uploaded: int
    start_time: str
    end_time: str
    success_rate: float
    average_processing_time: float
    errors: List[str]
    warnings: List[str]

class AutomatedNotionImporter:
    """Comprehensive automated Notion importer for bulk file collections"""
    
    def __init__(self, config_path: str = "README.sync.yaml", analysis_path: str = "analysis_results"):
        self.config_path = config_path
        self.analysis_path = Path(analysis_path)
        
        # Load configuration
        self.config = self._load_config()
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Initialize Notion client
        self.notion_client = None
        if NOTION_AVAILABLE and self.config.get('notion', {}).get('integration_token'):
            try:
                self.notion_client = NotionClient(
                    auth=self.config['notion']['integration_token']
                )
                self.logger.info("Notion client initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Notion client: {e}")
        
        # Import state
        self.import_jobs: List[ImportJob] = []
        self.import_batches: List[ImportBatch] = []
        self.processing_queue = Queue()
        self.results_queue = Queue()
        
        # Processing statistics
        self.stats = {
            'jobs_created': 0,
            'jobs_completed': 0,
            'jobs_failed': 0,
            'total_processing_time': 0.0,
            'pages_created': 0,
            'errors': [],
            'warnings': []
        }
        
        # Content processors
        self.content_processors = {
            'document': self._process_document,
            'presentation': self._process_presentation,
            'spreadsheet': self._process_spreadsheet,
            'image': self._process_image,
            'video': self._process_video,
            'audio': self._process_audio,
            'archive': self._process_archive,
            'code': self._process_code,
            'data': self._process_data,
            'other': self._process_other
        }
        
        # Rate limiting
        self.api_rate_limiter = self._create_rate_limiter()
        
        # Progress tracking
        self.progress_callback = None
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            import yaml
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.warning(f"Could not load config from {self.config_path}: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'notion': {
                'integration_token': None,
                'parent_page_id': None,
                'rate_limit_requests_per_minute': 10
            },
            'processing': {
                'max_concurrent_jobs': 3,
                'batch_size': 20,
                'retry_attempts': 3,
                'timeout_seconds': 300
            },
            'content': {
                'max_file_size_mb': 50,
                'image_max_width': 1920,
                'image_max_height': 1080,
                'text_preview_length': 500
            }
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging"""
        logger = logging.getLogger('automated_notion_importer')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # Create logs directory
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            
            # File handler
            log_file = log_dir / f'import_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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
            
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        return logger
    
    def _create_rate_limiter(self):
        """Create API rate limiter"""
        class RateLimiter:
            def __init__(self, requests_per_minute=10):
                self.requests_per_minute = requests_per_minute
                self.requests = []
                self.lock = threading.Lock()
            
            def wait_if_needed(self):
                with self.lock:
                    now = time.time()
                    # Remove requests older than 1 minute
                    self.requests = [req_time for req_time in self.requests if now - req_time < 60]
                    
                    if len(self.requests) >= self.requests_per_minute:
                        # Wait until we can make another request
                        sleep_time = 60 - (now - self.requests[0])
                        if sleep_time > 0:
                            time.sleep(sleep_time)
                    
                    self.requests.append(now)
        
        rate_limit = self.config.get('notion', {}).get('rate_limit_requests_per_minute', 10)
        return RateLimiter(rate_limit)
    
    def load_analysis_results(self) -> Tuple[List[FileAnalysis], CollectionAnalysis]:
        """Load file analysis results"""
        try:
            # Load file analyses
            file_analyses_path = self.analysis_path / 'file_analyses.json'
            with open(file_analyses_path, 'r') as f:
                file_analyses_data = json.load(f)
            
            file_analyses = [FileAnalysis(**data) for data in file_analyses_data]
            
            # Load collection analysis
            collection_analysis_path = self.analysis_path / 'collection_analysis.json'
            with open(collection_analysis_path, 'r') as f:
                collection_analysis_data = json.load(f)
            
            collection_analysis = CollectionAnalysis(**collection_analysis_data)
            
            self.logger.info(f"Loaded analysis for {len(file_analyses)} files")
            return file_analyses, collection_analysis
            
        except Exception as e:
            self.logger.error(f"Failed to load analysis results: {e}")
            raise
    
    def create_import_jobs(self, file_analyses: List[FileAnalysis], 
                          collection_analysis: CollectionAnalysis) -> List[ImportBatch]:
        """Create import jobs from analysis results"""
        self.logger.info("Creating import jobs from analysis results")
        
        # Sort files by priority
        sorted_analyses = sorted(file_analyses, key=lambda x: x.priority_score, reverse=True)
        
        # Create jobs
        jobs = []
        for i, analysis in enumerate(sorted_analyses):
            job = ImportJob(
                job_id=f"job_{i+1:04d}",
                file_analysis=analysis,
                batch_id=0,  # Will be set when creating batches
                priority=analysis.priority_score
            )
            jobs.append(job)
        
        self.import_jobs = jobs
        self.stats['jobs_created'] = len(jobs)
        
        # Create batches
        batches = self._create_import_batches(jobs, collection_analysis)
        self.import_batches = batches
        
        self.logger.info(f"Created {len(jobs)} import jobs in {len(batches)} batches")
        return batches
    
    def _create_import_batches(self, jobs: List[ImportJob], 
                              collection_analysis: CollectionAnalysis) -> List[ImportBatch]:
        """Create optimal import batches"""
        batch_size = self.config.get('processing', {}).get('batch_size', 20)
        max_batch_size_mb = 50  # 50MB per batch
        
        batches = []
        current_batch_jobs = []
        current_batch_size = 0
        
        for job in jobs:
            file_size_mb = job.file_analysis.file_size / (1024 * 1024)
            
            # Check if we should start a new batch
            if (len(current_batch_jobs) >= batch_size or 
                current_batch_size + file_size_mb > max_batch_size_mb):
                
                if current_batch_jobs:
                    # Create batch
                    batch_id = len(batches) + 1
                    for batch_job in current_batch_jobs:
                        batch_job.batch_id = batch_id
                    
                    batch = ImportBatch(
                        batch_id=batch_id,
                        jobs=current_batch_jobs.copy()
                    )
                    batches.append(batch)
                    
                    current_batch_jobs = []
                    current_batch_size = 0
            
            current_batch_jobs.append(job)
            current_batch_size += file_size_mb
        
        # Add final batch
        if current_batch_jobs:
            batch_id = len(batches) + 1
            for batch_job in current_batch_jobs:
                batch_job.batch_id = batch_id
            
            batch = ImportBatch(
                batch_id=batch_id,
                jobs=current_batch_jobs.copy()
            )
            batches.append(batch)
        
        return batches
    
    def execute_import(self, batches: Optional[List[ImportBatch]] = None, 
                      progress_callback: Optional[callable] = None) -> ImportResults:
        """Execute the complete import operation"""
        if batches is None:
            batches = self.import_batches
        
        self.progress_callback = progress_callback
        
        self.logger.info(f"Starting import of {len(batches)} batches")
        start_time = datetime.now()
        
        try:
            # Validate Notion connection
            if not self._validate_notion_connection():
                raise Exception("Notion connection validation failed")
            
            # Create Notion organization structure
            self._create_notion_organization()
            
            # Process batches
            for batch in batches:
                self.logger.info(f"Processing batch {batch.batch_id} ({batch.total_files} files)")
                self._process_batch(batch)
                
                if self.progress_callback:
                    completed_batches = len([b for b in batches if b.status == "completed"])
                    progress = completed_batches / len(batches)
                    self.progress_callback(progress, f"Completed batch {batch.batch_id}")
            
            # Generate results
            end_time = datetime.now()
            results = self._generate_import_results(start_time, end_time)
            
            # Save results
            self._save_import_results(results)
            
            self.logger.info(f"Import completed: {results.completed_jobs}/{results.total_jobs} files")
            return results
            
        except Exception as e:
            self.logger.error(f"Import failed: {e}")
            raise
    
    def _validate_notion_connection(self) -> bool:
        """Validate Notion API connection"""
        if not self.notion_client:
            self.logger.error("Notion client not initialized")
            return False
        
        try:
            # Test API connection
            self.api_rate_limiter.wait_if_needed()
            users = self.notion_client.users.list()
            self.logger.info("Notion connection validated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Notion connection validation failed: {e}")
            return False
    
    def _create_notion_organization(self):
        """Create Notion page organization structure"""
        self.logger.info("Creating Notion organization structure")
        
        try:
            parent_page_id = self.config.get('notion', {}).get('parent_page_id')
            if not parent_page_id:
                self.logger.warning("No parent page ID configured")
                return
            
            # Create main project page
            self.api_rate_limiter.wait_if_needed()
            main_page = self.notion_client.pages.create(
                parent={"page_id": parent_page_id},
                properties={
                    "title": {
                        "title": [{
                            "text": {"content": "AI Trading Platform - Bulk Import"}
                        }]
                    }
                },
                children=[
                    {
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [{
                                "type": "text",
                                "text": {"content": "Automated File Import"}
                            }]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{
                                "type": "text",
                                "text": {"content": f"Imported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                            }]
                        }
                    }
                ]
            )
            
            self.main_page_id = main_page['id']
            self.logger.info(f"Created main import page: {main_page['id']}")
            
            # Create category pages
            self._create_category_pages()
            
        except Exception as e:
            self.logger.error(f"Failed to create Notion organization: {e}")
            raise
    
    def _create_category_pages(self):
        """Create category-specific pages"""
        categories = set()
        for job in self.import_jobs:
            categories.add(job.file_analysis.suggested_category)
        
        self.category_pages = {}
        
        for category in categories:
            try:
                self.api_rate_limiter.wait_if_needed()
                category_page = self.notion_client.pages.create(
                    parent={"page_id": self.main_page_id},
                    properties={
                        "title": {
                            "title": [{
                                "text": {"content": category}
                            }]
                        }
                    },
                    children=[
                        {
                            "object": "block",
                            "type": "heading_2",
                            "heading_2": {
                                "rich_text": [{
                                    "type": "text",
                                    "text": {"content": f"{category} Files"}
                                }]
                            }
                        }
                    ]
                )
                
                self.category_pages[category] = category_page['id']
                self.logger.info(f"Created category page for {category}")
                
            except Exception as e:
                self.logger.warning(f"Failed to create category page for {category}: {e}")
    
    def _process_batch(self, batch: ImportBatch):
        """Process a single import batch"""
        batch.status = "processing"
        batch.started_at = datetime.now().isoformat()
        
        start_time = time.time()
        
        # Process jobs in parallel
        max_workers = self.config.get('processing', {}).get('max_concurrent_jobs', 3)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all jobs
            future_to_job = {
                executor.submit(self._process_job, job): job 
                for job in batch.jobs
            }
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    result = future.result()
                    if result:
                        batch.completed_files += 1
                        self.stats['jobs_completed'] += 1
                    else:
                        batch.failed_files += 1
                        self.stats['jobs_failed'] += 1
                        
                except Exception as e:
                    self.logger.error(f"Job {job.job_id} failed: {e}")
                    job.status = "failed"
                    job.error_message = str(e)
                    batch.failed_files += 1
                    self.stats['jobs_failed'] += 1
        
        # Update batch status
        batch.processing_time = time.time() - start_time
        batch.completed_at = datetime.now().isoformat()
        batch.status = "completed"
        
        self.logger.info(
            f"Batch {batch.batch_id} completed: "
            f"{batch.completed_files}/{batch.total_files} files successful"
        )
    
    def _process_job(self, job: ImportJob) -> bool:
        """Process a single import job"""
        job.status = "processing"
        job.started_at = datetime.now().isoformat()
        
        start_time = time.time()
        
        try:
            self.logger.info(f"Processing {job.job_id}: {job.file_analysis.file_name}")
            
            # Get content processor
            content_type = job.file_analysis.content_type
            processor = self.content_processors.get(content_type, self._process_other)
            
            # Process file content
            notion_content = processor(job.file_analysis)
            
            # Create Notion page
            page_id, page_url = self._create_notion_page(job.file_analysis, notion_content)
            
            # Update job status
            job.status = "completed"
            job.notion_page_id = page_id
            job.notion_page_url = page_url
            job.processing_time = time.time() - start_time
            job.completed_at = datetime.now().isoformat()
            
            self.stats['pages_created'] += 1
            self.stats['total_processing_time'] += job.processing_time
            
            self.logger.info(f"Completed {job.job_id} in {job.processing_time:.2f}s")
            return True
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.processing_time = time.time() - start_time
            job.completed_at = datetime.now().isoformat()
            
            self.logger.error(f"Failed {job.job_id}: {e}")
            self.stats['errors'].append(f"{job.job_id}: {str(e)}")
            
            return False
    
    def _process_document(self, file_analysis: FileAnalysis) -> Dict[str, Any]:
        """Process document files"""
        content = {"blocks": []}
        
        try:
            if TEXTRACT_AVAILABLE:
                # Extract text content
                text = textract.process(file_analysis.file_path).decode('utf-8')
                
                # Split into paragraphs
                paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                
                for paragraph in paragraphs[:20]:  # Limit to first 20 paragraphs
                    if len(paragraph) > 2000:  # Split very long paragraphs
                        chunks = [paragraph[i:i+2000] for i in range(0, len(paragraph), 2000)]
                        for chunk in chunks:
                            content["blocks"].append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{
                                        "type": "text",
                                        "text": {"content": chunk}
                                    }]
                                }
                            })
                    else:
                        content["blocks"].append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{
                                    "type": "text",
                                    "text": {"content": paragraph}
                                }]
                            }
                        })
            else:
                # Fallback: create file reference
                content["blocks"].append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": f"Document file: {file_analysis.file_name}"}
                        }]
                    }
                })
                
        except Exception as e:
            self.logger.warning(f"Document processing failed for {file_analysis.file_name}: {e}")
            content["blocks"].append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": f"Could not process document content: {str(e)}"}
                    }]
                }
            })
        
        return content
    
    def _process_presentation(self, file_analysis: FileAnalysis) -> Dict[str, Any]:
        """Process presentation files"""
        content = {"blocks": []}
        
        # Add presentation info
        content["blocks"].append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": "Presentation File"}
                }]
            }
        })
        
        content["blocks"].append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"File: {file_analysis.file_name}"}
                }]
            }
        })
        
        if file_analysis.content_summary:
            content["blocks"].append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": file_analysis.content_summary}
                    }]
                }
            })
        
        return content
    
    def _process_spreadsheet(self, file_analysis: FileAnalysis) -> Dict[str, Any]:
        """Process spreadsheet files"""
        content = {"blocks": []}
        
        try:
            if PANDAS_AVAILABLE and file_analysis.file_path.endswith('.csv'):
                # Read CSV data
                df = pd.read_csv(file_analysis.file_path, nrows=100)  # Limit rows
                
                # Create table
                if len(df) > 0:
                    # Table header
                    header_cells = []
                    for col in df.columns:
                        header_cells.append([{
                            "type": "text",
                            "text": {"content": str(col)}
                        }])
                    
                    # Table rows
                    table_rows = []
                    for _, row in df.head(20).iterrows():  # Limit to 20 rows
                        row_cells = []
                        for col in df.columns:
                            row_cells.append([{
                                "type": "text",
                                "text": {"content": str(row[col])[:100]}  # Limit cell content
                            }])
                        table_rows.append({"cells": row_cells})
                    
                    # Create table block
                    content["blocks"].append({
                        "object": "block",
                        "type": "table",
                        "table": {
                            "table_width": len(df.columns),
                            "has_column_header": True,
                            "has_row_header": False,
                            "children": [
                                {
                                    "object": "block",
                                    "type": "table_row",
                                    "table_row": {"cells": header_cells}
                                }
                            ] + [
                                {
                                    "object": "block",
                                    "type": "table_row",
                                    "table_row": row
                                } for row in table_rows
                            ]
                        }
                    })
                else:
                    content["blocks"].append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{
                                "type": "text",
                                "text": {"content": "Empty spreadsheet"}
                            }]
                        }
                    })
            else:
                # Fallback: file reference
                content["blocks"].append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": f"Spreadsheet file: {file_analysis.file_name}"}
                        }]
                    }
                })
                
        except Exception as e:
            self.logger.warning(f"Spreadsheet processing failed for {file_analysis.file_name}: {e}")
            content["blocks"].append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": f"Could not process spreadsheet: {str(e)}"}
                    }]
                }
            })
        
        return content
    
    def _process_image(self, file_analysis: FileAnalysis) -> Dict[str, Any]:
        """Process image files"""
        content = {"blocks": []}
        
        # Note: Notion API doesn't support direct file uploads
        # This would require a file hosting service
        content["blocks"].append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"Image file: {file_analysis.file_name}"}
                }]
            }
        })
        
        if file_analysis.content_summary:
            content["blocks"].append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": file_analysis.content_summary}
                    }]
                }
            })
        
        return content
    
    def _process_video(self, file_analysis: FileAnalysis) -> Dict[str, Any]:
        """Process video files"""
        return self._process_media_file(file_analysis, "Video")
    
    def _process_audio(self, file_analysis: FileAnalysis) -> Dict[str, Any]:
        """Process audio files"""
        return self._process_media_file(file_analysis, "Audio")
    
    def _process_media_file(self, file_analysis: FileAnalysis, media_type: str) -> Dict[str, Any]:
        """Process media files (video/audio)"""
        content = {"blocks": []}
        
        content["blocks"].append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"{media_type} File"}
                }]
            }
        })
        
        content["blocks"].append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"File: {file_analysis.file_name}"}
                }]
            }
        })
        
        content["blocks"].append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"Size: {file_analysis.file_size / (1024*1024):.1f} MB"}
                }]
            }
        })
        
        return content
    
    def _process_archive(self, file_analysis: FileAnalysis) -> Dict[str, Any]:
        """Process archive files"""
        content = {"blocks": []}
        
        content["blocks"].append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": "Archive File"}
                }]
            }
        })
        
        content["blocks"].append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"Archive: {file_analysis.file_name}"}
                }]
            }
        })
        
        content["blocks"].append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": "This archive file requires extraction before content can be imported."}
                }],
                "icon": {"emoji": "📦"}
            }
        })
        
        return content
    
    def _process_code(self, file_analysis: FileAnalysis) -> Dict[str, Any]:
        """Process code files"""
        content = {"blocks": []}
        
        try:
            # Read code content
            with open(file_analysis.file_path, 'r', encoding=file_analysis.encoding or 'utf-8') as f:
                code_content = f.read()
            
            # Limit code length
            if len(code_content) > 5000:
                code_content = code_content[:5000] + "\n\n... (truncated)"
            
            # Determine language
            ext_to_lang = {
                '.py': 'python',
                '.js': 'javascript',
                '.html': 'html',
                '.css': 'css',
                '.java': 'java',
                '.cpp': 'cpp',
                '.c': 'c',
                '.php': 'php',
                '.rb': 'ruby',
                '.go': 'go'
            }
            
            file_ext = Path(file_analysis.file_path).suffix.lower()
            language = ext_to_lang.get(file_ext, 'plain text')
            
            content["blocks"].append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": code_content}
                    }],
                    "language": language
                }
            })
            
        except Exception as e:
            self.logger.warning(f"Code processing failed for {file_analysis.file_name}: {e}")
            content["blocks"].append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": f"Could not read code file: {str(e)}"}
                    }]
                }
            })
        
        return content
    
    def _process_data(self, file_analysis: FileAnalysis) -> Dict[str, Any]:
        """Process data files (JSON, XML, etc.)"""
        content = {"blocks": []}
        
        try:
            # Read data content
            with open(file_analysis.file_path, 'r', encoding=file_analysis.encoding or 'utf-8') as f:
                data_content = f.read()
            
            # Limit content length
            if len(data_content) > 3000:
                data_content = data_content[:3000] + "\n\n... (truncated)"
            
            # Determine format
            file_ext = Path(file_analysis.file_path).suffix.lower()
            if file_ext == '.json':
                language = 'json'
            elif file_ext in ['.xml']:
                language = 'xml'
            elif file_ext in ['.yaml', '.yml']:
                language = 'yaml'
            else:
                language = 'plain text'
            
            content["blocks"].append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": data_content}
                    }],
                    "language": language
                }
            })
            
        except Exception as e:
            self.logger.warning(f"Data processing failed for {file_analysis.file_name}: {e}")
            content["blocks"].append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": f"Could not read data file: {str(e)}"}
                    }]
                }
            })
        
        return content
    
    def _process_other(self, file_analysis: FileAnalysis) -> Dict[str, Any]:
        """Process other/unknown file types"""
        content = {"blocks": []}
        
        content["blocks"].append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"File: {file_analysis.file_name}"}
                }]
            }
        })
        
        content["blocks"].append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"Type: {file_analysis.file_type}"}
                }]
            }
        })
        
        content["blocks"].append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"Size: {file_analysis.file_size / (1024*1024):.1f} MB"}
                }]
            }
        })
        
        return content
    
    def _create_notion_page(self, file_analysis: FileAnalysis, 
                           content: Dict[str, Any]) -> Tuple[str, str]:
        """Create Notion page for file"""
        try:
            # Determine parent page
            category = file_analysis.suggested_category
            parent_page_id = self.category_pages.get(category, self.main_page_id)
            
            # Create page title
            page_title = file_analysis.file_name
            if len(page_title) > 100:
                page_title = page_title[:97] + "..."
            
            # Rate limiting
            self.api_rate_limiter.wait_if_needed()
            
            # Create page
            page_data = {
                "parent": {"page_id": parent_page_id},
                "properties": {
                    "title": {
                        "title": [{
                            "text": {"content": page_title}
                        }]
                    }
                }
            }
            
            # Add content blocks (limit to 100 blocks per API call)
            blocks = content.get("blocks", [])
            if blocks:
                page_data["children"] = blocks[:100]
            
            page = self.notion_client.pages.create(**page_data)
            page_id = page['id']
            
            # Add remaining blocks if any
            if len(blocks) > 100:
                remaining_blocks = blocks[100:]
                for i in range(0, len(remaining_blocks), 100):
                    batch = remaining_blocks[i:i+100]
                    self.api_rate_limiter.wait_if_needed()
                    self.notion_client.blocks.children.append(
                        block_id=page_id,
                        children=batch
                    )
            
            # Generate page URL
            page_url = f"https://notion.so/{page_id.replace('-', '')}"
            
            return page_id, page_url
            
        except Exception as e:
            self.logger.error(f"Failed to create Notion page for {file_analysis.file_name}: {e}")
            raise
    
    def _generate_import_results(self, start_time: datetime, end_time: datetime) -> ImportResults:
        """Generate comprehensive import results"""
        total_jobs = len(self.import_jobs)
        completed_jobs = len([j for j in self.import_jobs if j.status == "completed"])
        failed_jobs = len([j for j in self.import_jobs if j.status == "failed"])
        
        total_processing_time = (end_time - start_time).total_seconds()
        total_size_processed = sum(j.file_analysis.file_size for j in self.import_jobs if j.status == "completed")
        
        success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        avg_processing_time = (sum(j.processing_time for j in self.import_jobs if j.processing_time > 0) / 
                              max(1, len([j for j in self.import_jobs if j.processing_time > 0])))
        
        return ImportResults(
            total_jobs=total_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            total_processing_time=total_processing_time,
            total_size_processed=total_size_processed,
            pages_created=self.stats['pages_created'],
            databases_created=0,  # Not implemented yet
            files_uploaded=0,     # Not implemented yet
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            success_rate=success_rate,
            average_processing_time=avg_processing_time,
            errors=self.stats['errors'],
            warnings=self.stats['warnings']
        )
    
    def _save_import_results(self, results: ImportResults):
        """Save import results to files"""
        try:
            # Create results directory
            results_dir = Path('import_results')
            results_dir.mkdir(exist_ok=True)
            
            # Save detailed results
            with open(results_dir / 'import_results.json', 'w') as f:
                json.dump(asdict(results), f, indent=2, default=str)
            
            # Save job details
            jobs_data = [asdict(job) for job in self.import_jobs]
            with open(results_dir / 'import_jobs.json', 'w') as f:
                json.dump(jobs_data, f, indent=2, default=str)
            
            # Save batch details
            batches_data = [asdict(batch) for batch in self.import_batches]
            with open(results_dir / 'import_batches.json', 'w') as f:
                json.dump(batches_data, f, indent=2, default=str)
            
            # Generate summary report
            self._generate_summary_report(results, results_dir)
            
            self.logger.info(f"Import results saved to {results_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to save import results: {e}")
    
    def _generate_summary_report(self, results: ImportResults, results_dir: Path):
        """Generate human-readable summary report"""
        report_lines = [
            "# Automated Notion Import Summary Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Import Results",
            f"- Total Files: {results.total_jobs:,}",
            f"- Successfully Imported: {results.completed_jobs:,}",
            f"- Failed: {results.failed_jobs:,}",
            f"- Success Rate: {results.success_rate:.1f}%",
            "",
            "## Performance Metrics",
            f"- Total Processing Time: {results.total_processing_time / 3600:.1f} hours",
            f"- Average Time per File: {results.average_processing_time:.2f} seconds",
            f"- Total Data Processed: {results.total_size_processed / (1024*1024*1024):.2f} GB",
            f"- Pages Created: {results.pages_created:,}",
            "",
            "## Timeline",
            f"- Start Time: {results.start_time}",
            f"- End Time: {results.end_time}",
        ]
        
        if results.errors:
            report_lines.extend([
                "",
                "## Errors",
            ])
            for error in results.errors[:10]:  # Show first 10 errors
                report_lines.append(f"- {error}")
            
            if len(results.errors) > 10:
                report_lines.append(f"- ... and {len(results.errors) - 10} more errors")
        
        if results.warnings:
            report_lines.extend([
                "",
                "## Warnings",
            ])
            for warning in results.warnings[:10]:  # Show first 10 warnings
                report_lines.append(f"- {warning}")
        
        # Save report
        with open(results_dir / 'summary_report.md', 'w') as f:
            f.write('\n'.join(report_lines))

def main():
    """Main function for running automated import"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Automated Notion importer for bulk file collections')
    parser.add_argument('--analysis-path', '-a', default='analysis_results', 
                       help='Path to analysis results directory')
    parser.add_argument('--config', '-c', default='README.sync.yaml', 
                       help='Configuration file path')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Perform dry run without actual import')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.analysis_path):
        print(f"Error: Analysis results directory '{args.analysis_path}' does not exist")
        print("Please run bulk_file_analyzer.py first")
        return 1
    
    print(f"🚀 Starting automated Notion import")
    print(f"📊 Analysis path: {args.analysis_path}")
    print(f"⚙️  Config file: {args.config}")
    
    if args.dry_run:
        print("🧪 DRY RUN MODE - No actual import will be performed")
    
    try:
        # Initialize importer
        importer = AutomatedNotionImporter(args.config, args.analysis_path)
        
        # Load analysis results
        file_analyses, collection_analysis = importer.load_analysis_results()
        
        # Create import jobs
        batches = importer.create_import_jobs(file_analyses, collection_analysis)
        
        print(f"📦 Created {len(batches)} import batches")
        print(f"📁 Total files to import: {len(file_analyses):,}")
        print(f"💾 Total size: {collection_analysis.total_size / (1024*1024*1024):.2f} GB")
        
        if not args.dry_run:
            # Progress callback
            def progress_callback(progress, message):
                print(f"Progress: {progress*100:.1f}% - {message}")
            
            # Execute import
            results = importer.execute_import(batches, progress_callback)
            
            print(f"\n✅ Import Complete!")
            print(f"📊 Success Rate: {results.success_rate:.1f}%")
            print(f"📁 Files Imported: {results.completed_jobs:,}/{results.total_jobs:,}")
            print(f"⏱️  Total Time: {results.total_processing_time / 3600:.1f} hours")
            print(f"📄 Pages Created: {results.pages_created:,}")
            
            if results.failed_jobs > 0:
                print(f"❌ Failed Files: {results.failed_jobs:,}")
                print(f"📋 Check import_results/ for detailed error information")
        else:
            print(f"\n🧪 Dry run completed - no files were actually imported")
            print(f"📋 Would have processed {len(file_analyses):,} files in {len(batches)} batches")
        
        return 0
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())

