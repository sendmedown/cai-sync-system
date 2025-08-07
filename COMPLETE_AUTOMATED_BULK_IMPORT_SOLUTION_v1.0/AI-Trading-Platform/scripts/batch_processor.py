#!/usr/bin/env python3
"""
Batch Processing System for Automated File Organization
======================================================

This script provides intelligent batch processing capabilities for organizing
and preparing large file collections for automated Notion import. Designed
specifically for Richard's 340-file collection (4GB), this system implements
smart batching, priority queuing, and resource optimization.

Author: Manus AI
Version: 1.0
Date: July 7, 2025
Target: Optimal batch processing for 340 files (4GB)
"""

import os
import json
import time
import shutil
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import concurrent.futures
import threading
from queue import Queue, PriorityQueue
import tempfile

@dataclass
class ProcessingBatch:
    """Represents a processing batch with optimization parameters"""
    batch_id: str
    files: List[str]
    total_size: int
    priority_score: float
    estimated_time: float
    status: str = "pending"
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    processing_time: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

@dataclass
class FileProcessingJob:
    """Individual file processing job"""
    job_id: str
    file_path: str
    batch_id: str
    priority: int
    file_size: int
    content_type: str
    processing_strategy: str
    status: str = "pending"
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    processing_time: float = 0.0
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

class BatchProcessor:
    """Intelligent batch processing system for file organization"""
    
    def __init__(self, source_directory: str, output_directory: str = "processed_files"):
        self.source_directory = Path(source_directory)
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(exist_ok=True)
        
        # Create processing subdirectories
        self.staging_dir = self.output_directory / "staging"
        self.processed_dir = self.output_directory / "processed"
        self.failed_dir = self.output_directory / "failed"
        self.temp_dir = self.output_directory / "temp"
        
        for dir_path in [self.staging_dir, self.processed_dir, self.failed_dir, self.temp_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Processing state
        self.batches: List[ProcessingBatch] = []
        self.jobs: List[FileProcessingJob] = []
        self.processing_queue = PriorityQueue()
        self.results_queue = Queue()
        
        # Configuration
        self.config = {
            'max_batch_size_mb': 50,
            'max_batch_files': 25,
            'max_concurrent_batches': 2,
            'max_concurrent_jobs': 4,
            'retry_attempts': 3,
            'timeout_seconds': 300,
            'memory_limit_mb': 1024
        }
        
        # Statistics
        self.stats = {
            'batches_created': 0,
            'batches_processed': 0,
            'files_processed': 0,
            'files_failed': 0,
            'total_size_processed': 0,
            'total_processing_time': 0.0,
            'errors': [],
            'warnings': []
        }
        
        # Resource monitoring
        self.resource_monitor = ResourceMonitor()
        
        # Processing strategies
        self.processing_strategies = {
            'document': self._process_document_file,
            'presentation': self._process_presentation_file,
            'spreadsheet': self._process_spreadsheet_file,
            'image': self._process_image_file,
            'video': self._process_video_file,
            'audio': self._process_audio_file,
            'archive': self._process_archive_file,
            'code': self._process_code_file,
            'data': self._process_data_file,
            'other': self._process_other_file
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging for batch processing"""
        logger = logging.getLogger('batch_processor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # Create logs directory
            log_dir = self.output_directory / 'logs'
            log_dir.mkdir(exist_ok=True)
            
            # File handler
            log_file = log_dir / f'batch_processing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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
    
    def analyze_and_create_batches(self, analysis_results_path: str = "analysis_results") -> List[ProcessingBatch]:
        """Analyze files and create optimal processing batches"""
        self.logger.info("Analyzing files and creating processing batches")
        
        # Load analysis results
        analysis_path = Path(analysis_results_path)
        file_analyses = self._load_file_analyses(analysis_path)
        
        if not file_analyses:
            self.logger.error("No file analyses found")
            return []
        
        # Create processing jobs
        jobs = self._create_processing_jobs(file_analyses)
        self.jobs = jobs
        
        # Create optimized batches
        batches = self._create_optimized_batches(jobs)
        self.batches = batches
        
        self.stats['batches_created'] = len(batches)
        
        self.logger.info(f"Created {len(batches)} processing batches for {len(jobs)} files")
        return batches
    
    def _load_file_analyses(self, analysis_path: Path) -> List[Dict[str, Any]]:
        """Load file analysis results"""
        try:
            file_analyses_path = analysis_path / 'file_analyses.json'
            if not file_analyses_path.exists():
                self.logger.error(f"File analyses not found at {file_analyses_path}")
                return []
            
            with open(file_analyses_path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"Failed to load file analyses: {e}")
            return []
    
    def _create_processing_jobs(self, file_analyses: List[Dict[str, Any]]) -> List[FileProcessingJob]:
        """Create individual processing jobs from file analyses"""
        jobs = []
        
        for i, analysis in enumerate(file_analyses):
            job = FileProcessingJob(
                job_id=f"job_{i+1:04d}",
                file_path=analysis['file_path'],
                batch_id="",  # Will be set when creating batches
                priority=analysis.get('priority_score', 50),
                file_size=analysis['file_size'],
                content_type=analysis['content_type'],
                processing_strategy=analysis.get('import_method', 'file_reference')
            )
            jobs.append(job)
        
        return jobs
    
    def _create_optimized_batches(self, jobs: List[FileProcessingJob]) -> List[ProcessingBatch]:
        """Create optimized processing batches"""
        # Sort jobs by priority (highest first)
        sorted_jobs = sorted(jobs, key=lambda x: x.priority, reverse=True)
        
        batches = []
        current_batch_files = []
        current_batch_size = 0
        current_priority_sum = 0
        
        max_batch_size_bytes = self.config['max_batch_size_mb'] * 1024 * 1024
        max_batch_files = self.config['max_batch_files']
        
        for job in sorted_jobs:
            # Check if we should start a new batch
            if (len(current_batch_files) >= max_batch_files or 
                current_batch_size + job.file_size > max_batch_size_bytes):
                
                if current_batch_files:
                    # Create batch
                    batch = self._finalize_batch(
                        current_batch_files, current_batch_size, 
                        current_priority_sum, len(batches) + 1
                    )
                    batches.append(batch)
                    
                    current_batch_files = []
                    current_batch_size = 0
                    current_priority_sum = 0
            
            # Add job to current batch
            job.batch_id = f"batch_{len(batches) + 1:03d}"
            current_batch_files.append(job.file_path)
            current_batch_size += job.file_size
            current_priority_sum += job.priority
        
        # Add final batch
        if current_batch_files:
            batch = self._finalize_batch(
                current_batch_files, current_batch_size, 
                current_priority_sum, len(batches) + 1
            )
            batches.append(batch)
        
        return batches
    
    def _finalize_batch(self, files: List[str], total_size: int, 
                       priority_sum: float, batch_number: int) -> ProcessingBatch:
        """Finalize batch creation with optimization parameters"""
        batch_id = f"batch_{batch_number:03d}"
        
        # Calculate priority score (average priority)
        priority_score = priority_sum / len(files) if files else 0
        
        # Estimate processing time based on file sizes and types
        estimated_time = self._estimate_batch_processing_time(files, total_size)
        
        return ProcessingBatch(
            batch_id=batch_id,
            files=files,
            total_size=total_size,
            priority_score=priority_score,
            estimated_time=estimated_time
        )
    
    def _estimate_batch_processing_time(self, files: List[str], total_size: int) -> float:
        """Estimate processing time for a batch"""
        # Base time calculation
        size_mb = total_size / (1024 * 1024)
        base_time = size_mb * 2.0  # 2 seconds per MB base rate
        
        # Adjust for file count (overhead per file)
        file_overhead = len(files) * 1.0  # 1 second per file
        
        # Adjust for file types (some types take longer)
        type_multiplier = 1.0
        for file_path in files:
            # Simple type detection based on extension
            ext = Path(file_path).suffix.lower()
            if ext in ['.pdf', '.docx', '.pptx']:
                type_multiplier += 0.5
            elif ext in ['.zip', '.rar', '.7z']:
                type_multiplier += 1.0
        
        total_time = (base_time + file_overhead) * (type_multiplier / len(files))
        return max(10.0, total_time)  # Minimum 10 seconds
    
    def process_batches(self, batches: Optional[List[ProcessingBatch]] = None, 
                       progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """Process all batches with intelligent resource management"""
        if batches is None:
            batches = self.batches
        
        self.logger.info(f"Starting processing of {len(batches)} batches")
        start_time = datetime.now()
        
        # Sort batches by priority
        sorted_batches = sorted(batches, key=lambda x: x.priority_score, reverse=True)
        
        # Process batches with concurrency control
        max_concurrent = self.config['max_concurrent_batches']
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submit batch processing jobs
            future_to_batch = {
                executor.submit(self._process_single_batch, batch): batch 
                for batch in sorted_batches
            }
            
            completed_batches = 0
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    result = future.result()
                    completed_batches += 1
                    
                    if progress_callback:
                        progress = completed_batches / len(batches)
                        progress_callback(progress, f"Completed batch {batch.batch_id}")
                    
                    self.logger.info(f"Batch {batch.batch_id} completed: {result}")
                    
                except Exception as e:
                    self.logger.error(f"Batch {batch.batch_id} failed: {e}")
                    batch.status = "failed"
                    self.stats['errors'].append(f"Batch {batch.batch_id}: {str(e)}")
        
        # Generate processing results
        end_time = datetime.now()
        results = self._generate_processing_results(start_time, end_time)
        
        # Save results
        self._save_processing_results(results)
        
        self.logger.info(f"Batch processing completed: {results['summary']}")
        return results
    
    def _process_single_batch(self, batch: ProcessingBatch) -> Dict[str, Any]:
        """Process a single batch of files"""
        batch.status = "processing"
        batch.started_at = datetime.now().isoformat()
        
        self.logger.info(f"Processing batch {batch.batch_id} ({len(batch.files)} files)")
        start_time = time.time()
        
        # Create batch staging directory
        batch_staging_dir = self.staging_dir / batch.batch_id
        batch_staging_dir.mkdir(exist_ok=True)
        
        # Process files in the batch
        success_count = 0
        failure_count = 0
        
        # Get jobs for this batch
        batch_jobs = [job for job in self.jobs if job.batch_id == batch.batch_id]
        
        # Process jobs with concurrency control
        max_concurrent_jobs = self.config['max_concurrent_jobs']
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_jobs) as executor:
            # Submit file processing jobs
            future_to_job = {
                executor.submit(self._process_single_file, job, batch_staging_dir): job 
                for job in batch_jobs
            }
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    result = future.result()
                    if result:
                        success_count += 1
                        self.stats['files_processed'] += 1
                    else:
                        failure_count += 1
                        self.stats['files_failed'] += 1
                        
                except Exception as e:
                    self.logger.error(f"File processing failed for {job.file_path}: {e}")
                    job.status = "failed"
                    job.error_message = str(e)
                    failure_count += 1
                    self.stats['files_failed'] += 1
        
        # Update batch status
        batch.processing_time = time.time() - start_time
        batch.success_count = success_count
        batch.failure_count = failure_count
        batch.completed_at = datetime.now().isoformat()
        batch.status = "completed" if failure_count == 0 else "partial"
        
        self.stats['batches_processed'] += 1
        self.stats['total_processing_time'] += batch.processing_time
        self.stats['total_size_processed'] += batch.total_size
        
        return {
            'batch_id': batch.batch_id,
            'success_count': success_count,
            'failure_count': failure_count,
            'processing_time': batch.processing_time
        }
    
    def _process_single_file(self, job: FileProcessingJob, staging_dir: Path) -> bool:
        """Process a single file"""
        job.status = "processing"
        job.started_at = datetime.now().isoformat()
        
        start_time = time.time()
        
        try:
            self.logger.debug(f"Processing file {job.file_path}")
            
            # Get processing strategy
            strategy = self.processing_strategies.get(
                job.content_type, 
                self._process_other_file
            )
            
            # Execute processing strategy
            output_path = strategy(job, staging_dir)
            
            # Update job status
            job.status = "completed"
            job.output_path = str(output_path) if output_path else None
            job.processing_time = time.time() - start_time
            job.completed_at = datetime.now().isoformat()
            
            return True
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.processing_time = time.time() - start_time
            job.completed_at = datetime.now().isoformat()
            
            self.logger.error(f"File processing failed for {job.file_path}: {e}")
            return False
    
    def _process_document_file(self, job: FileProcessingJob, staging_dir: Path) -> Optional[Path]:
        """Process document files"""
        source_path = Path(job.file_path)
        
        # Create organized output directory
        doc_dir = staging_dir / "documents"
        doc_dir.mkdir(exist_ok=True)
        
        # Copy file to staging area
        output_path = doc_dir / source_path.name
        shutil.copy2(source_path, output_path)
        
        # Extract metadata if possible
        metadata = self._extract_file_metadata(source_path)
        metadata_path = output_path.with_suffix(output_path.suffix + '.meta.json')
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        return output_path
    
    def _process_presentation_file(self, job: FileProcessingJob, staging_dir: Path) -> Optional[Path]:
        """Process presentation files"""
        source_path = Path(job.file_path)
        
        # Create organized output directory
        pres_dir = staging_dir / "presentations"
        pres_dir.mkdir(exist_ok=True)
        
        # Copy file to staging area
        output_path = pres_dir / source_path.name
        shutil.copy2(source_path, output_path)
        
        return output_path
    
    def _process_spreadsheet_file(self, job: FileProcessingJob, staging_dir: Path) -> Optional[Path]:
        """Process spreadsheet files"""
        source_path = Path(job.file_path)
        
        # Create organized output directory
        data_dir = staging_dir / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Copy file to staging area
        output_path = data_dir / source_path.name
        shutil.copy2(source_path, output_path)
        
        return output_path
    
    def _process_image_file(self, job: FileProcessingJob, staging_dir: Path) -> Optional[Path]:
        """Process image files"""
        source_path = Path(job.file_path)
        
        # Create organized output directory
        media_dir = staging_dir / "media" / "images"
        media_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy file to staging area
        output_path = media_dir / source_path.name
        shutil.copy2(source_path, output_path)
        
        # Optimize image if needed
        if job.file_size > 10 * 1024 * 1024:  # > 10MB
            self._optimize_image(output_path)
        
        return output_path
    
    def _process_video_file(self, job: FileProcessingJob, staging_dir: Path) -> Optional[Path]:
        """Process video files"""
        source_path = Path(job.file_path)
        
        # Create organized output directory
        media_dir = staging_dir / "media" / "videos"
        media_dir.mkdir(parents=True, exist_ok=True)
        
        # For large video files, create reference instead of copying
        if job.file_size > 100 * 1024 * 1024:  # > 100MB
            # Create reference file
            ref_path = media_dir / (source_path.stem + '.ref.json')
            reference_data = {
                'original_path': str(source_path),
                'file_name': source_path.name,
                'file_size': job.file_size,
                'content_type': 'video',
                'processing_note': 'Large video file - reference only'
            }
            
            with open(ref_path, 'w') as f:
                json.dump(reference_data, f, indent=2)
            
            return ref_path
        else:
            # Copy smaller video files
            output_path = media_dir / source_path.name
            shutil.copy2(source_path, output_path)
            return output_path
    
    def _process_audio_file(self, job: FileProcessingJob, staging_dir: Path) -> Optional[Path]:
        """Process audio files"""
        source_path = Path(job.file_path)
        
        # Create organized output directory
        media_dir = staging_dir / "media" / "audio"
        media_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy file to staging area
        output_path = media_dir / source_path.name
        shutil.copy2(source_path, output_path)
        
        return output_path
    
    def _process_archive_file(self, job: FileProcessingJob, staging_dir: Path) -> Optional[Path]:
        """Process archive files"""
        source_path = Path(job.file_path)
        
        # Create organized output directory
        archive_dir = staging_dir / "archives"
        archive_dir.mkdir(exist_ok=True)
        
        # Create extraction directory
        extract_dir = archive_dir / source_path.stem
        extract_dir.mkdir(exist_ok=True)
        
        try:
            # Extract archive (basic implementation)
            if source_path.suffix.lower() == '.zip':
                import zipfile
                with zipfile.ZipFile(source_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            else:
                # For other archive types, just copy the file
                output_path = archive_dir / source_path.name
                shutil.copy2(source_path, output_path)
                return output_path
            
            return extract_dir
            
        except Exception as e:
            self.logger.warning(f"Archive extraction failed for {source_path}: {e}")
            # Fallback: copy the archive file
            output_path = archive_dir / source_path.name
            shutil.copy2(source_path, output_path)
            return output_path
    
    def _process_code_file(self, job: FileProcessingJob, staging_dir: Path) -> Optional[Path]:
        """Process code files"""
        source_path = Path(job.file_path)
        
        # Create organized output directory
        code_dir = staging_dir / "code"
        code_dir.mkdir(exist_ok=True)
        
        # Copy file to staging area
        output_path = code_dir / source_path.name
        shutil.copy2(source_path, output_path)
        
        return output_path
    
    def _process_data_file(self, job: FileProcessingJob, staging_dir: Path) -> Optional[Path]:
        """Process data files"""
        source_path = Path(job.file_path)
        
        # Create organized output directory
        data_dir = staging_dir / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Copy file to staging area
        output_path = data_dir / source_path.name
        shutil.copy2(source_path, output_path)
        
        return output_path
    
    def _process_other_file(self, job: FileProcessingJob, staging_dir: Path) -> Optional[Path]:
        """Process other/unknown file types"""
        source_path = Path(job.file_path)
        
        # Create organized output directory
        other_dir = staging_dir / "other"
        other_dir.mkdir(exist_ok=True)
        
        # Copy file to staging area
        output_path = other_dir / source_path.name
        shutil.copy2(source_path, output_path)
        
        return output_path
    
    def _extract_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract basic file metadata"""
        try:
            stat = file_path.stat()
            return {
                'file_name': file_path.name,
                'file_size': stat.st_size,
                'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'file_extension': file_path.suffix,
                'processing_timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'file_name': file_path.name,
                'error': str(e),
                'processing_timestamp': datetime.now().isoformat()
            }
    
    def _optimize_image(self, image_path: Path):
        """Optimize large images"""
        try:
            from PIL import Image
            
            with Image.open(image_path) as img:
                # Resize if too large
                max_size = (1920, 1080)
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    img.save(image_path, optimize=True, quality=85)
                    
        except Exception as e:
            self.logger.warning(f"Image optimization failed for {image_path}: {e}")
    
    def _generate_processing_results(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Generate comprehensive processing results"""
        total_time = (end_time - start_time).total_seconds()
        
        return {
            'summary': {
                'total_batches': len(self.batches),
                'batches_processed': self.stats['batches_processed'],
                'total_files': len(self.jobs),
                'files_processed': self.stats['files_processed'],
                'files_failed': self.stats['files_failed'],
                'success_rate': (self.stats['files_processed'] / len(self.jobs) * 100) if self.jobs else 0,
                'total_size_processed_gb': self.stats['total_size_processed'] / (1024**3),
                'total_processing_time_hours': total_time / 3600,
                'average_processing_time_per_file': (
                    self.stats['total_processing_time'] / max(1, self.stats['files_processed'])
                )
            },
            'batches': [asdict(batch) for batch in self.batches],
            'jobs': [asdict(job) for job in self.jobs],
            'errors': self.stats['errors'],
            'warnings': self.stats['warnings'],
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
    
    def _save_processing_results(self, results: Dict[str, Any]):
        """Save processing results to files"""
        try:
            # Save detailed results
            results_file = self.output_directory / 'processing_results.json'
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            # Save summary report
            self._generate_summary_report(results)
            
            self.logger.info(f"Processing results saved to {self.output_directory}")
            
        except Exception as e:
            self.logger.error(f"Failed to save processing results: {e}")
    
    def _generate_summary_report(self, results: Dict[str, Any]):
        """Generate human-readable summary report"""
        summary = results['summary']
        
        report_lines = [
            "# Batch Processing Summary Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Processing Results",
            f"- Total Batches: {summary['total_batches']}",
            f"- Batches Processed: {summary['batches_processed']}",
            f"- Total Files: {summary['total_files']}",
            f"- Files Processed: {summary['files_processed']}",
            f"- Files Failed: {summary['files_failed']}",
            f"- Success Rate: {summary['success_rate']:.1f}%",
            "",
            "## Performance Metrics",
            f"- Total Size Processed: {summary['total_size_processed_gb']:.2f} GB",
            f"- Total Processing Time: {summary['total_processing_time_hours']:.1f} hours",
            f"- Average Time per File: {summary['average_processing_time_per_file']:.2f} seconds",
            "",
            "## Batch Details",
        ]
        
        for batch in results['batches'][:10]:  # Show first 10 batches
            report_lines.append(
                f"- {batch['batch_id']}: {batch['success_count']}/{len(batch['files'])} files, "
                f"{batch['processing_time']:.1f}s"
            )
        
        if len(results['batches']) > 10:
            report_lines.append(f"- ... and {len(results['batches']) - 10} more batches")
        
        if results['errors']:
            report_lines.extend([
                "",
                "## Errors",
            ])
            for error in results['errors'][:10]:
                report_lines.append(f"- {error}")
        
        # Save report
        report_file = self.output_directory / 'processing_summary.md'
        with open(report_file, 'w') as f:
            f.write('\n'.join(report_lines))

class ResourceMonitor:
    """Monitor system resources during processing"""
    
    def __init__(self):
        self.memory_usage = []
        self.cpu_usage = []
        self.disk_usage = []
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            return psutil.virtual_memory().used / (1024 * 1024)
        except ImportError:
            return 0.0
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            import psutil
            return psutil.cpu_percent()
        except ImportError:
            return 0.0
    
    def get_disk_usage(self, path: str) -> float:
        """Get disk usage for path in GB"""
        try:
            import psutil
            return psutil.disk_usage(path).used / (1024**3)
        except ImportError:
            return 0.0

def main():
    """Main function for testing batch processor"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch processor for file organization')
    parser.add_argument('source_directory', help='Source directory containing files')
    parser.add_argument('--output', '-o', default='processed_files', help='Output directory')
    parser.add_argument('--analysis', '-a', default='analysis_results', help='Analysis results directory')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.source_directory):
        print(f"Error: Source directory '{args.source_directory}' does not exist")
        return 1
    
    print(f"🔄 Starting batch processing")
    print(f"📁 Source: {args.source_directory}")
    print(f"📊 Output: {args.output}")
    
    try:
        # Initialize processor
        processor = BatchProcessor(args.source_directory, args.output)
        
        # Create batches
        batches = processor.analyze_and_create_batches(args.analysis)
        
        if not batches:
            print("❌ No batches created - check analysis results")
            return 1
        
        print(f"📦 Created {len(batches)} processing batches")
        
        # Progress callback
        def progress_callback(progress, message):
            print(f"Progress: {progress*100:.1f}% - {message}")
        
        # Process batches
        results = processor.process_batches(batches, progress_callback)
        
        print(f"\n✅ Batch Processing Complete!")
        print(f"📊 Success Rate: {results['summary']['success_rate']:.1f}%")
        print(f"📁 Files Processed: {results['summary']['files_processed']}")
        print(f"⏱️  Total Time: {results['summary']['total_processing_time_hours']:.1f} hours")
        
        return 0
        
    except Exception as e:
        print(f"❌ Batch processing failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())

