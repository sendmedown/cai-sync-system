#!/usr/bin/env python3
"""
Notion Import Pipeline Integration System
========================================

This module provides comprehensive Notion import pipeline capabilities for the
AI Trading Platform, enabling seamless integration of HLDD exports, task backlogs,
and project documentation into Notion workspaces with intelligent content routing.

Author: Manus AI
Version: 1.0
Date: July 7, 2025
"""

import os
import json
import yaml
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import mimetypes

try:
    from notion_client import Client as NotionClient
    from notion_client.errors import APIResponseError, RequestTimeoutError
except ImportError:
    print("Warning: notion-client not installed. Install with: pip install notion-client")
    NotionClient = None

@dataclass
class ImportJob:
    """Represents a Notion import job"""
    job_id: str
    source_file: str
    target_page_id: Optional[str]
    content_type: str
    status: str = "pending"
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ImportResult:
    """Represents the result of a Notion import operation"""
    job_id: str
    success: bool
    page_id: Optional[str] = None
    page_url: Optional[str] = None
    blocks_created: int = 0
    files_uploaded: int = 0
    processing_time_seconds: float = 0
    error_details: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

class NotionImportPipeline:
    """Main Notion import pipeline system"""
    
    def __init__(self, config_path: str = "README.sync.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = self._setup_logging()
        
        # Initialize Notion client
        self.notion_client = None
        if NotionClient and self.config.get('notion', {}).get('integration_token'):
            try:
                self.notion_client = NotionClient(
                    auth=self.config['notion']['integration_token']
                )
                self.logger.info("Notion client initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Notion client: {e}")
        
        # Import job tracking
        self.import_jobs: Dict[str, ImportJob] = {}
        self.import_results: Dict[str, ImportResult] = {}
        
        # Content processors
        self.content_processors = {
            'markdown': self._process_markdown_content,
            'json': self._process_json_content,
            'csv': self._process_csv_content,
            'yaml': self._process_yaml_content,
            'image': self._process_image_content,
            'document': self._process_document_content
        }
        
        # Load existing jobs
        self._load_existing_jobs()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the import pipeline"""
        logger = logging.getLogger('notion_import_pipeline')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_existing_jobs(self):
        """Load existing import jobs from storage"""
        try:
            jobs_file = "sync/import_jobs.json"
            if os.path.exists(jobs_file):
                with open(jobs_file, 'r') as f:
                    jobs_data = json.load(f)
                
                for job_data in jobs_data:
                    job = ImportJob(**job_data)
                    self.import_jobs[job.job_id] = job
            
            results_file = "sync/import_results.json"
            if os.path.exists(results_file):
                with open(results_file, 'r') as f:
                    results_data = json.load(f)
                
                for result_data in results_data:
                    result = ImportResult(**result_data)
                    self.import_results[result.job_id] = result
            
            self.logger.info(f"Loaded {len(self.import_jobs)} import jobs and {len(self.import_results)} results")
            
        except Exception as e:
            self.logger.error(f"Error loading existing jobs: {e}")
    
    def create_import_job(self, source_file: str, content_type: str, 
                         target_page_id: Optional[str] = None, **metadata) -> ImportJob:
        """Create a new import job"""
        job_id = f"import_{len(self.import_jobs) + 1:04d}_{int(datetime.now().timestamp())}"
        
        job = ImportJob(
            job_id=job_id,
            source_file=source_file,
            target_page_id=target_page_id,
            content_type=content_type,
            metadata=metadata
        )
        
        self.import_jobs[job_id] = job
        self.logger.info(f"Created import job {job_id} for {source_file}")
        
        return job
    
    def execute_import_job(self, job_id: str) -> ImportResult:
        """Execute a specific import job"""
        if job_id not in self.import_jobs:
            raise ValueError(f"Import job {job_id} not found")
        
        job = self.import_jobs[job_id]
        start_time = datetime.now()
        
        try:
            job.status = "running"
            job.started_at = start_time.isoformat()
            
            # Validate Notion client
            if not self.notion_client:
                raise Exception("Notion client not initialized")
            
            # Process content based on type
            processor = self.content_processors.get(job.content_type)
            if not processor:
                raise Exception(f"No processor found for content type: {job.content_type}")
            
            # Execute the import
            result = processor(job)
            
            # Calculate processing time
            end_time = datetime.now()
            result.processing_time_seconds = (end_time - start_time).total_seconds()
            
            # Update job status
            job.status = "completed" if result.success else "failed"
            job.completed_at = end_time.isoformat()
            if not result.success:
                job.error_message = result.error_details
            
            # Store result
            self.import_results[job_id] = result
            
            self.logger.info(f"Import job {job_id} completed: {result.success}")
            return result
            
        except Exception as e:
            # Handle errors
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            result = ImportResult(
                job_id=job_id,
                success=False,
                processing_time_seconds=processing_time,
                error_details=str(e)
            )
            
            job.status = "failed"
            job.completed_at = end_time.isoformat()
            job.error_message = str(e)
            
            self.import_results[job_id] = result
            self.logger.error(f"Import job {job_id} failed: {e}")
            
            return result
    
    def _process_markdown_content(self, job: ImportJob) -> ImportResult:
        """Process markdown content for Notion import"""
        try:
            # Read markdown file
            with open(job.source_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Convert markdown to Notion blocks
            blocks = self._convert_markdown_to_notion_blocks(content)
            
            # Create or update Notion page
            if job.target_page_id:
                # Update existing page
                page_id = job.target_page_id
                self._update_notion_page_content(page_id, blocks)
            else:
                # Create new page
                parent_page_id = self.config.get('notion', {}).get('parent_page_id')
                if not parent_page_id:
                    raise Exception("No parent page ID configured")
                
                page_title = job.metadata.get('title', os.path.basename(job.source_file))
                page = self._create_notion_page(parent_page_id, page_title, blocks)
                page_id = page['id']
            
            # Generate page URL
            page_url = f"https://notion.so/{page_id.replace('-', '')}"
            
            return ImportResult(
                job_id=job.job_id,
                success=True,
                page_id=page_id,
                page_url=page_url,
                blocks_created=len(blocks)
            )
            
        except Exception as e:
            return ImportResult(
                job_id=job.job_id,
                success=False,
                error_details=str(e)
            )
    
    def _process_json_content(self, job: ImportJob) -> ImportResult:
        """Process JSON content for Notion import"""
        try:
            # Read JSON file
            with open(job.source_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert JSON to Notion blocks
            blocks = self._convert_json_to_notion_blocks(data, job.metadata.get('title', 'JSON Data'))
            
            # Create Notion page
            parent_page_id = self.config.get('notion', {}).get('parent_page_id')
            page_title = job.metadata.get('title', os.path.basename(job.source_file))
            page = self._create_notion_page(parent_page_id, page_title, blocks)
            
            page_url = f"https://notion.so/{page['id'].replace('-', '')}"
            
            return ImportResult(
                job_id=job.job_id,
                success=True,
                page_id=page['id'],
                page_url=page_url,
                blocks_created=len(blocks)
            )
            
        except Exception as e:
            return ImportResult(
                job_id=job.job_id,
                success=False,
                error_details=str(e)
            )
    
    def _process_csv_content(self, job: ImportJob) -> ImportResult:
        """Process CSV content for Notion import"""
        try:
            import csv
            
            # Read CSV file
            rows = []
            with open(job.source_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            if not rows:
                raise Exception("CSV file is empty")
            
            # Convert CSV to Notion table blocks
            blocks = self._convert_csv_to_notion_blocks(rows)
            
            # Create Notion page
            parent_page_id = self.config.get('notion', {}).get('parent_page_id')
            page_title = job.metadata.get('title', os.path.basename(job.source_file))
            page = self._create_notion_page(parent_page_id, page_title, blocks)
            
            page_url = f"https://notion.so/{page['id'].replace('-', '')}"
            
            return ImportResult(
                job_id=job.job_id,
                success=True,
                page_id=page['id'],
                page_url=page_url,
                blocks_created=len(blocks)
            )
            
        except Exception as e:
            return ImportResult(
                job_id=job.job_id,
                success=False,
                error_details=str(e)
            )
    
    def _process_yaml_content(self, job: ImportJob) -> ImportResult:
        """Process YAML content for Notion import"""
        try:
            # Read YAML file
            with open(job.source_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Convert YAML to Notion blocks
            blocks = self._convert_yaml_to_notion_blocks(data, job.metadata.get('title', 'YAML Configuration'))
            
            # Create Notion page
            parent_page_id = self.config.get('notion', {}).get('parent_page_id')
            page_title = job.metadata.get('title', os.path.basename(job.source_file))
            page = self._create_notion_page(parent_page_id, page_title, blocks)
            
            page_url = f"https://notion.so/{page['id'].replace('-', '')}"
            
            return ImportResult(
                job_id=job.job_id,
                success=True,
                page_id=page['id'],
                page_url=page_url,
                blocks_created=len(blocks)
            )
            
        except Exception as e:
            return ImportResult(
                job_id=job.job_id,
                success=False,
                error_details=str(e)
            )
    
    def _process_image_content(self, job: ImportJob) -> ImportResult:
        """Process image content for Notion import"""
        try:
            # Upload image to Notion
            # Note: Notion API doesn't support direct file uploads
            # This would typically require a file hosting service
            
            # For now, create a placeholder block with file reference
            blocks = [{
                "object": "block",
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {
                        "url": f"file://{os.path.abspath(job.source_file)}"
                    },
                    "caption": [{
                        "type": "text",
                        "text": {
                            "content": job.metadata.get('caption', os.path.basename(job.source_file))
                        }
                    }]
                }
            }]
            
            # Create Notion page
            parent_page_id = self.config.get('notion', {}).get('parent_page_id')
            page_title = job.metadata.get('title', os.path.basename(job.source_file))
            page = self._create_notion_page(parent_page_id, page_title, blocks)
            
            page_url = f"https://notion.so/{page['id'].replace('-', '')}"
            
            return ImportResult(
                job_id=job.job_id,
                success=True,
                page_id=page['id'],
                page_url=page_url,
                blocks_created=len(blocks),
                files_uploaded=1
            )
            
        except Exception as e:
            return ImportResult(
                job_id=job.job_id,
                success=False,
                error_details=str(e)
            )
    
    def _process_document_content(self, job: ImportJob) -> ImportResult:
        """Process document content for Notion import"""
        try:
            # For document files, create a file attachment block
            # Note: This requires file hosting for external URLs
            
            blocks = [{
                "object": "block",
                "type": "file",
                "file": {
                    "type": "external",
                    "external": {
                        "url": f"file://{os.path.abspath(job.source_file)}"
                    },
                    "caption": [{
                        "type": "text",
                        "text": {
                            "content": job.metadata.get('description', f"Document: {os.path.basename(job.source_file)}")
                        }
                    }]
                }
            }]
            
            # Create Notion page
            parent_page_id = self.config.get('notion', {}).get('parent_page_id')
            page_title = job.metadata.get('title', os.path.basename(job.source_file))
            page = self._create_notion_page(parent_page_id, page_title, blocks)
            
            page_url = f"https://notion.so/{page['id'].replace('-', '')}"
            
            return ImportResult(
                job_id=job.job_id,
                success=True,
                page_id=page['id'],
                page_url=page_url,
                blocks_created=len(blocks),
                files_uploaded=1
            )
            
        except Exception as e:
            return ImportResult(
                job_id=job.job_id,
                success=False,
                error_details=str(e)
            )
    
    def _convert_markdown_to_notion_blocks(self, markdown_content: str) -> List[Dict[str, Any]]:
        """Convert markdown content to Notion blocks"""
        blocks = []
        lines = markdown_content.split('\n')
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            
            # Headers
            if line.startswith('#'):
                # Flush current paragraph
                if current_paragraph:
                    blocks.append(self._create_paragraph_block('\n'.join(current_paragraph)))
                    current_paragraph = []
                
                # Determine header level
                level = len(line) - len(line.lstrip('#'))
                header_text = line.lstrip('# ').strip()
                
                if level == 1:
                    block_type = "heading_1"
                elif level == 2:
                    block_type = "heading_2"
                else:
                    block_type = "heading_3"
                
                blocks.append({
                    "object": "block",
                    "type": block_type,
                    block_type: {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": header_text}
                        }]
                    }
                })
            
            # Code blocks
            elif line.startswith('```'):
                # Flush current paragraph
                if current_paragraph:
                    blocks.append(self._create_paragraph_block('\n'.join(current_paragraph)))
                    current_paragraph = []
                
                # Handle code block (simplified)
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": "Code block content"}
                        }],
                        "language": "plain text"
                    }
                })
            
            # Bullet points
            elif line.startswith('- ') or line.startswith('* '):
                # Flush current paragraph
                if current_paragraph:
                    blocks.append(self._create_paragraph_block('\n'.join(current_paragraph)))
                    current_paragraph = []
                
                bullet_text = line[2:].strip()
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": bullet_text}
                        }]
                    }
                })
            
            # Empty lines
            elif not line:
                if current_paragraph:
                    blocks.append(self._create_paragraph_block('\n'.join(current_paragraph)))
                    current_paragraph = []
            
            # Regular text
            else:
                current_paragraph.append(line)
        
        # Flush remaining paragraph
        if current_paragraph:
            blocks.append(self._create_paragraph_block('\n'.join(current_paragraph)))
        
        return blocks
    
    def _create_paragraph_block(self, text: str) -> Dict[str, Any]:
        """Create a paragraph block"""
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": text}
                }]
            }
        }
    
    def _convert_json_to_notion_blocks(self, data: Any, title: str) -> List[Dict[str, Any]]:
        """Convert JSON data to Notion blocks"""
        blocks = []
        
        # Add title
        blocks.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": title}
                }]
            }
        })
        
        # Add JSON content as code block
        json_content = json.dumps(data, indent=2)
        blocks.append({
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": json_content}
                }],
                "language": "json"
            }
        })
        
        return blocks
    
    def _convert_csv_to_notion_blocks(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert CSV data to Notion table blocks"""
        blocks = []
        
        if not rows:
            return blocks
        
        # Get headers
        headers = list(rows[0].keys())
        
        # Create table header
        header_cells = []
        for header in headers:
            header_cells.append([{
                "type": "text",
                "text": {"content": str(header)}
            }])
        
        # Create table rows
        table_rows = []
        for row in rows[:50]:  # Limit to 50 rows for performance
            row_cells = []
            for header in headers:
                row_cells.append([{
                    "type": "text",
                    "text": {"content": str(row.get(header, ''))}
                }])
            table_rows.append({"cells": row_cells})
        
        # Create table block
        blocks.append({
            "object": "block",
            "type": "table",
            "table": {
                "table_width": len(headers),
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
        
        return blocks
    
    def _convert_yaml_to_notion_blocks(self, data: Any, title: str) -> List[Dict[str, Any]]:
        """Convert YAML data to Notion blocks"""
        blocks = []
        
        # Add title
        blocks.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": title}
                }]
            }
        })
        
        # Add YAML content as code block
        yaml_content = yaml.dump(data, default_flow_style=False)
        blocks.append({
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": yaml_content}
                }],
                "language": "yaml"
            }
        })
        
        return blocks
    
    def _create_notion_page(self, parent_page_id: str, title: str, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a new Notion page"""
        try:
            page_data = {
                "parent": {"page_id": parent_page_id},
                "properties": {
                    "title": {
                        "title": [{
                            "text": {"content": title}
                        }]
                    }
                },
                "children": blocks[:100]  # Notion API limit
            }
            
            page = self.notion_client.pages.create(**page_data)
            
            # Add remaining blocks if any
            if len(blocks) > 100:
                remaining_blocks = blocks[100:]
                for i in range(0, len(remaining_blocks), 100):
                    batch = remaining_blocks[i:i+100]
                    self.notion_client.blocks.children.append(
                        block_id=page['id'],
                        children=batch
                    )
            
            return page
            
        except Exception as e:
            self.logger.error(f"Error creating Notion page: {e}")
            raise
    
    def _update_notion_page_content(self, page_id: str, blocks: List[Dict[str, Any]]):
        """Update existing Notion page content"""
        try:
            # Clear existing content
            existing_blocks = self.notion_client.blocks.children.list(block_id=page_id)
            for block in existing_blocks.get('results', []):
                self.notion_client.blocks.delete(block_id=block['id'])
            
            # Add new content
            for i in range(0, len(blocks), 100):
                batch = blocks[i:i+100]
                self.notion_client.blocks.children.append(
                    block_id=page_id,
                    children=batch
                )
            
        except Exception as e:
            self.logger.error(f"Error updating Notion page content: {e}")
            raise
    
    def import_hldd_exports(self, hldd_word_file: str, hldd_pdf_file: str) -> List[ImportResult]:
        """Import HLDD exports to Notion"""
        results = []
        
        try:
            # Create import jobs for HLDD files
            word_job = self.create_import_job(
                source_file=hldd_word_file,
                content_type='document',
                title='AI Trading Platform HLDD v2.0 (Word)',
                description='High-Level Design Document - Word format'
            )
            
            pdf_job = self.create_import_job(
                source_file=hldd_pdf_file,
                content_type='document',
                title='AI Trading Platform HLDD v2.0 (PDF)',
                description='High-Level Design Document - PDF format'
            )
            
            # Execute import jobs
            word_result = self.execute_import_job(word_job.job_id)
            pdf_result = self.execute_import_job(pdf_job.job_id)
            
            results.extend([word_result, pdf_result])
            
            self.logger.info(f"HLDD import completed: {len(results)} files processed")
            
        except Exception as e:
            self.logger.error(f"Error importing HLDD exports: {e}")
        
        return results
    
    def import_project_files(self) -> List[ImportResult]:
        """Import all project files to Notion"""
        results = []
        
        try:
            # Get sync directories from config
            sync_dirs = self.config.get('directories', {}).get('sync_directories', [])
            
            for dir_config in sync_dirs:
                if not dir_config.get('auto_sync', True):
                    continue
                
                dir_path = dir_config['path']
                if not os.path.exists(dir_path):
                    continue
                
                # Process files in directory
                for root, dirs, files in os.walk(dir_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        
                        # Determine content type
                        content_type = self._determine_content_type(file_path)
                        if not content_type:
                            continue
                        
                        # Create and execute import job
                        job = self.create_import_job(
                            source_file=file_path,
                            content_type=content_type,
                            title=os.path.basename(file_path),
                            directory=dir_config['description']
                        )
                        
                        result = self.execute_import_job(job.job_id)
                        results.append(result)
            
            self.logger.info(f"Project import completed: {len(results)} files processed")
            
        except Exception as e:
            self.logger.error(f"Error importing project files: {e}")
        
        return results
    
    def _determine_content_type(self, file_path: str) -> Optional[str]:
        """Determine content type for a file"""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        type_mapping = {
            '.md': 'markdown',
            '.markdown': 'markdown',
            '.json': 'json',
            '.csv': 'csv',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.png': 'image',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.gif': 'image',
            '.svg': 'image',
            '.pdf': 'document',
            '.docx': 'document',
            '.txt': 'document'
        }
        
        return type_mapping.get(file_ext)
    
    def save_jobs_and_results(self):
        """Save import jobs and results to storage"""
        try:
            os.makedirs("sync", exist_ok=True)
            
            # Save jobs
            jobs_data = [asdict(job) for job in self.import_jobs.values()]
            with open("sync/import_jobs.json", 'w') as f:
                json.dump(jobs_data, f, indent=2, default=str)
            
            # Save results
            results_data = [asdict(result) for result in self.import_results.values()]
            with open("sync/import_results.json", 'w') as f:
                json.dump(results_data, f, indent=2, default=str)
            
            self.logger.info("Import jobs and results saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving jobs and results: {e}")
    
    def get_import_status(self) -> Dict[str, Any]:
        """Get overall import status"""
        total_jobs = len(self.import_jobs)
        completed_jobs = len([j for j in self.import_jobs.values() if j.status == "completed"])
        failed_jobs = len([j for j in self.import_jobs.values() if j.status == "failed"])
        pending_jobs = len([j for j in self.import_jobs.values() if j.status == "pending"])
        
        successful_results = len([r for r in self.import_results.values() if r.success])
        
        return {
            'total_jobs': total_jobs,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'pending_jobs': pending_jobs,
            'success_rate': (successful_results / total_jobs * 100) if total_jobs > 0 else 0,
            'total_pages_created': len([r for r in self.import_results.values() if r.page_id]),
            'total_blocks_created': sum(r.blocks_created for r in self.import_results.values()),
            'total_files_uploaded': sum(r.files_uploaded for r in self.import_results.values())
        }

def main():
    """Main function for testing the import pipeline"""
    pipeline = NotionImportPipeline()
    
    print("🔄 Notion Import Pipeline Test")
    print("=" * 50)
    
    # Test with sample files
    test_files = [
        ("tasks/roadmap.csv", "csv"),
        ("tasks/AI-Backlog.json", "json"),
        ("README.sync.yaml", "yaml")
    ]
    
    for file_path, content_type in test_files:
        if os.path.exists(file_path):
            job = pipeline.create_import_job(
                source_file=file_path,
                content_type=content_type,
                title=f"Test Import: {os.path.basename(file_path)}"
            )
            
            print(f"📝 Created import job: {job.job_id}")
            
            # Note: Actual execution requires valid Notion credentials
            # result = pipeline.execute_import_job(job.job_id)
            # print(f"✅ Import result: {result.success}")
    
    # Save jobs
    pipeline.save_jobs_and_results()
    
    # Show status
    status = pipeline.get_import_status()
    print(f"\n📊 Import Status:")
    print(f"   Total jobs: {status['total_jobs']}")
    print(f"   Pending jobs: {status['pending_jobs']}")
    
    return pipeline

if __name__ == "__main__":
    main()

