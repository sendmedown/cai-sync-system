#!/usr/bin/env python3
"""
Bulk File Analyzer for Automated Notion Import
==============================================

This script provides comprehensive analysis of large file collections to enable
intelligent automated import into Notion. Designed specifically for Richard's
340-file collection (4GB), this analyzer implements advanced content recognition,
organizational hierarchy detection, and import optimization strategies.

Author: Manus AI
Version: 1.0
Date: July 7, 2025
Target: 340 files (4GB) automated Notion import
"""

import os
import json
import hashlib
import mimetypes
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import magic
import chardet

# Advanced content analysis libraries
try:
    import textract
    TEXTRACT_AVAILABLE = True
except ImportError:
    TEXTRACT_AVAILABLE = False
    print("Warning: textract not available. Install with: pip install textract")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL not available. Install with: pip install Pillow")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas not available. Install with: pip install pandas")

@dataclass
class FileAnalysis:
    """Comprehensive file analysis results"""
    file_path: str
    file_name: str
    file_size: int
    file_type: str
    mime_type: str
    encoding: Optional[str]
    content_hash: str
    created_date: Optional[str]
    modified_date: str
    
    # Content analysis
    content_type: str
    content_summary: Optional[str]
    key_topics: List[str]
    language: Optional[str]
    
    # Organization analysis
    directory_level: int
    parent_directory: str
    suggested_category: str
    priority_score: int
    
    # Import strategy
    import_method: str
    notion_format: str
    processing_notes: List[str]
    
    # Quality metrics
    analysis_confidence: float
    processing_complexity: str
    estimated_import_time: float

@dataclass
class CollectionAnalysis:
    """Analysis results for entire file collection"""
    total_files: int
    total_size: int
    analysis_date: str
    
    # File type distribution
    file_types: Dict[str, int]
    content_types: Dict[str, int]
    size_distribution: Dict[str, int]
    
    # Organization insights
    directory_structure: Dict[str, Any]
    suggested_organization: Dict[str, List[str]]
    duplicate_groups: List[List[str]]
    
    # Import planning
    processing_batches: List[Dict[str, Any]]
    estimated_total_time: float
    resource_requirements: Dict[str, Any]
    
    # Quality assessment
    analysis_quality: Dict[str, float]
    potential_issues: List[str]
    optimization_recommendations: List[str]

class BulkFileAnalyzer:
    """Advanced bulk file analyzer for automated Notion import"""
    
    def __init__(self, target_directory: str, output_directory: str = "analysis_results"):
        self.target_directory = Path(target_directory)
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(exist_ok=True)
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Analysis results
        self.file_analyses: List[FileAnalysis] = []
        self.collection_analysis: Optional[CollectionAnalysis] = None
        
        # Content type classifiers
        self.content_classifiers = {
            'document': self._classify_document,
            'presentation': self._classify_presentation,
            'spreadsheet': self._classify_spreadsheet,
            'image': self._classify_image,
            'video': self._classify_video,
            'audio': self._classify_audio,
            'archive': self._classify_archive,
            'code': self._classify_code,
            'data': self._classify_data,
            'other': self._classify_other
        }
        
        # Import strategy mappings
        self.import_strategies = {
            'document': {
                'method': 'content_extraction',
                'notion_format': 'page',
                'complexity': 'medium'
            },
            'presentation': {
                'method': 'slide_extraction',
                'notion_format': 'page_with_blocks',
                'complexity': 'high'
            },
            'spreadsheet': {
                'method': 'data_import',
                'notion_format': 'database',
                'complexity': 'medium'
            },
            'image': {
                'method': 'file_upload',
                'notion_format': 'image_block',
                'complexity': 'low'
            },
            'video': {
                'method': 'file_reference',
                'notion_format': 'file_block',
                'complexity': 'low'
            },
            'audio': {
                'method': 'file_reference',
                'notion_format': 'file_block',
                'complexity': 'low'
            },
            'archive': {
                'method': 'extraction_analysis',
                'notion_format': 'multiple',
                'complexity': 'high'
            },
            'code': {
                'method': 'syntax_highlighting',
                'notion_format': 'code_block',
                'complexity': 'medium'
            },
            'data': {
                'method': 'structured_import',
                'notion_format': 'database',
                'complexity': 'medium'
            },
            'other': {
                'method': 'file_reference',
                'notion_format': 'file_block',
                'complexity': 'low'
            }
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging for analysis operations"""
        logger = logging.getLogger('bulk_file_analyzer')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # File handler
            log_file = self.output_directory / 'analysis.log'
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
    
    def analyze_collection(self) -> CollectionAnalysis:
        """Perform comprehensive analysis of entire file collection"""
        self.logger.info(f"Starting bulk analysis of {self.target_directory}")
        
        start_time = datetime.now()
        
        # Discover all files
        all_files = self._discover_files()
        self.logger.info(f"Discovered {len(all_files)} files for analysis")
        
        # Analyze each file
        for i, file_path in enumerate(all_files, 1):
            try:
                self.logger.info(f"Analyzing file {i}/{len(all_files)}: {file_path.name}")
                analysis = self._analyze_file(file_path)
                self.file_analyses.append(analysis)
                
                # Progress reporting
                if i % 50 == 0:
                    self.logger.info(f"Progress: {i}/{len(all_files)} files analyzed")
                    
            except Exception as e:
                self.logger.error(f"Error analyzing {file_path}: {e}")
                continue
        
        # Generate collection analysis
        self.collection_analysis = self._generate_collection_analysis()
        
        # Save results
        self._save_analysis_results()
        
        end_time = datetime.now()
        analysis_duration = (end_time - start_time).total_seconds()
        
        self.logger.info(f"Analysis completed in {analysis_duration:.2f} seconds")
        self.logger.info(f"Analyzed {len(self.file_analyses)} files successfully")
        
        return self.collection_analysis
    
    def _discover_files(self) -> List[Path]:
        """Discover all files in target directory recursively"""
        all_files = []
        
        for root, dirs, files in os.walk(self.target_directory):
            # Skip hidden directories and common system directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
            
            for file in files:
                # Skip hidden files and common system files
                if not file.startswith('.') and not file.endswith('.tmp'):
                    file_path = Path(root) / file
                    all_files.append(file_path)
        
        return sorted(all_files)
    
    def _analyze_file(self, file_path: Path) -> FileAnalysis:
        """Perform comprehensive analysis of individual file"""
        # Basic file information
        stat = file_path.stat()
        file_size = stat.st_size
        modified_date = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        try:
            created_date = datetime.fromtimestamp(stat.st_ctime).isoformat()
        except:
            created_date = None
        
        # File type detection
        mime_type = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
        
        try:
            file_type = magic.from_file(str(file_path))
        except:
            file_type = mime_type
        
        # Content hash
        content_hash = self._calculate_file_hash(file_path)
        
        # Encoding detection for text files
        encoding = self._detect_encoding(file_path)
        
        # Content analysis
        content_type = self._determine_content_type(file_path, mime_type)
        content_summary, key_topics, language = self._analyze_content(file_path, content_type)
        
        # Organization analysis
        directory_level = len(file_path.relative_to(self.target_directory).parts) - 1
        parent_directory = file_path.parent.name
        suggested_category = self._suggest_category(file_path, content_type, key_topics)
        priority_score = self._calculate_priority_score(file_path, content_type, file_size)
        
        # Import strategy
        import_strategy = self.import_strategies.get(content_type, self.import_strategies['other'])
        import_method = import_strategy['method']
        notion_format = import_strategy['notion_format']
        processing_complexity = import_strategy['complexity']
        
        # Processing notes
        processing_notes = self._generate_processing_notes(file_path, content_type, file_size)
        
        # Quality metrics
        analysis_confidence = self._calculate_confidence(content_type, file_size, encoding)
        estimated_import_time = self._estimate_import_time(file_size, processing_complexity)
        
        return FileAnalysis(
            file_path=str(file_path),
            file_name=file_path.name,
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type,
            encoding=encoding,
            content_hash=content_hash,
            created_date=created_date,
            modified_date=modified_date,
            content_type=content_type,
            content_summary=content_summary,
            key_topics=key_topics,
            language=language,
            directory_level=directory_level,
            parent_directory=parent_directory,
            suggested_category=suggested_category,
            priority_score=priority_score,
            import_method=import_method,
            notion_format=notion_format,
            processing_notes=processing_notes,
            analysis_confidence=analysis_confidence,
            processing_complexity=processing_complexity,
            estimated_import_time=estimated_import_time
        )
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            self.logger.warning(f"Could not calculate hash for {file_path}: {e}")
            return "unknown"
    
    def _detect_encoding(self, file_path: Path) -> Optional[str]:
        """Detect text encoding for text files"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # Read first 10KB
                result = chardet.detect(raw_data)
                return result.get('encoding')
        except Exception:
            return None
    
    def _determine_content_type(self, file_path: Path, mime_type: str) -> str:
        """Determine high-level content type"""
        file_ext = file_path.suffix.lower()
        
        # Document types
        if mime_type.startswith('text/') or file_ext in ['.txt', '.md', '.doc', '.docx', '.pdf', '.rtf']:
            return 'document'
        
        # Presentation types
        if file_ext in ['.ppt', '.pptx', '.odp'] or 'presentation' in mime_type:
            return 'presentation'
        
        # Spreadsheet types
        if file_ext in ['.xls', '.xlsx', '.csv', '.ods'] or 'spreadsheet' in mime_type:
            return 'spreadsheet'
        
        # Image types
        if mime_type.startswith('image/') or file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg']:
            return 'image'
        
        # Video types
        if mime_type.startswith('video/') or file_ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv']:
            return 'video'
        
        # Audio types
        if mime_type.startswith('audio/') or file_ext in ['.mp3', '.wav', '.flac', '.aac']:
            return 'audio'
        
        # Archive types
        if file_ext in ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2']:
            return 'archive'
        
        # Code types
        if file_ext in ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.php', '.rb', '.go']:
            return 'code'
        
        # Data types
        if file_ext in ['.json', '.xml', '.yaml', '.yml', '.sql', '.db']:
            return 'data'
        
        return 'other'
    
    def _analyze_content(self, file_path: Path, content_type: str) -> Tuple[Optional[str], List[str], Optional[str]]:
        """Analyze file content for summary and topics"""
        content_summary = None
        key_topics = []
        language = None
        
        try:
            if content_type == 'document' and TEXTRACT_AVAILABLE:
                # Extract text content
                text = textract.process(str(file_path)).decode('utf-8')
                
                # Generate summary (first 200 characters)
                content_summary = text[:200].strip() + "..." if len(text) > 200 else text.strip()
                
                # Extract key topics (simple keyword extraction)
                words = text.lower().split()
                word_freq = {}
                for word in words:
                    if len(word) > 4 and word.isalpha():
                        word_freq[word] = word_freq.get(word, 0) + 1
                
                # Get top 5 most frequent words as topics
                key_topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
                key_topics = [word for word, freq in key_topics]
                
                # Simple language detection (very basic)
                if any(word in text.lower() for word in ['the', 'and', 'or', 'but', 'in', 'on', 'at']):
                    language = 'english'
            
            elif content_type == 'spreadsheet' and PANDAS_AVAILABLE:
                # Analyze spreadsheet structure
                if file_path.suffix.lower() == '.csv':
                    df = pd.read_csv(file_path, nrows=5)
                    content_summary = f"CSV with {len(df.columns)} columns: {', '.join(df.columns[:5])}"
                    key_topics = list(df.columns[:10])
                
            elif content_type == 'image' and PIL_AVAILABLE:
                # Analyze image properties
                with Image.open(file_path) as img:
                    content_summary = f"Image: {img.format}, {img.size[0]}x{img.size[1]}, {img.mode}"
                    key_topics = [img.format.lower(), f"{img.size[0]}x{img.size[1]}"]
            
        except Exception as e:
            self.logger.debug(f"Content analysis failed for {file_path}: {e}")
        
        return content_summary, key_topics, language
    
    def _suggest_category(self, file_path: Path, content_type: str, key_topics: List[str]) -> str:
        """Suggest organizational category based on analysis"""
        # Check parent directory for hints
        parent_name = file_path.parent.name.lower()
        
        # Common category patterns
        if any(word in parent_name for word in ['doc', 'document', 'paper', 'report']):
            return 'Documentation'
        elif any(word in parent_name for word in ['present', 'slide', 'deck']):
            return 'Presentations'
        elif any(word in parent_name for word in ['data', 'dataset', 'analysis']):
            return 'Data & Analysis'
        elif any(word in parent_name for word in ['image', 'photo', 'picture', 'media']):
            return 'Media & Assets'
        elif any(word in parent_name for word in ['code', 'src', 'source', 'dev']):
            return 'Development'
        elif any(word in parent_name for word in ['project', 'work', 'client']):
            return 'Projects'
        elif any(word in parent_name for word in ['admin', 'legal', 'contract']):
            return 'Administrative'
        elif any(word in parent_name for word in ['research', 'study', 'academic']):
            return 'Research'
        
        # Content type based categories
        category_mapping = {
            'document': 'Documentation',
            'presentation': 'Presentations',
            'spreadsheet': 'Data & Analysis',
            'image': 'Media & Assets',
            'video': 'Media & Assets',
            'audio': 'Media & Assets',
            'code': 'Development',
            'data': 'Data & Analysis',
            'archive': 'Archives',
            'other': 'Miscellaneous'
        }
        
        return category_mapping.get(content_type, 'Miscellaneous')
    
    def _calculate_priority_score(self, file_path: Path, content_type: str, file_size: int) -> int:
        """Calculate import priority score (1-100)"""
        score = 50  # Base score
        
        # Content type priority
        type_priorities = {
            'document': 20,
            'presentation': 15,
            'spreadsheet': 15,
            'data': 10,
            'image': 5,
            'code': 10,
            'video': -5,
            'audio': -5,
            'archive': -10,
            'other': -15
        }
        score += type_priorities.get(content_type, 0)
        
        # File size consideration (prefer smaller files for faster processing)
        if file_size < 1024 * 1024:  # < 1MB
            score += 10
        elif file_size < 10 * 1024 * 1024:  # < 10MB
            score += 5
        elif file_size > 100 * 1024 * 1024:  # > 100MB
            score -= 20
        
        # Recent files get higher priority
        try:
            stat = file_path.stat()
            days_old = (datetime.now().timestamp() - stat.st_mtime) / (24 * 3600)
            if days_old < 30:
                score += 15
            elif days_old < 90:
                score += 10
            elif days_old > 365:
                score -= 10
        except:
            pass
        
        # File name hints
        name_lower = file_path.name.lower()
        if any(word in name_lower for word in ['important', 'critical', 'urgent', 'final']):
            score += 15
        elif any(word in name_lower for word in ['draft', 'temp', 'backup', 'old']):
            score -= 10
        
        return max(1, min(100, score))
    
    def _generate_processing_notes(self, file_path: Path, content_type: str, file_size: int) -> List[str]:
        """Generate processing notes and recommendations"""
        notes = []
        
        # Size-based notes
        if file_size > 50 * 1024 * 1024:  # > 50MB
            notes.append("Large file - consider compression or chunking")
        elif file_size == 0:
            notes.append("Empty file - verify content")
        
        # Type-specific notes
        if content_type == 'document':
            notes.append("Extract text content and preserve formatting")
        elif content_type == 'presentation':
            notes.append("Extract slides and convert to Notion blocks")
        elif content_type == 'spreadsheet':
            notes.append("Import as Notion database with proper schema")
        elif content_type == 'image':
            notes.append("Optimize image size for web display")
        elif content_type == 'archive':
            notes.append("Extract and analyze contents before import")
        
        # File extension specific notes
        ext = file_path.suffix.lower()
        if ext in ['.docx', '.pptx', '.xlsx']:
            notes.append("Office format - use specialized extraction")
        elif ext == '.pdf':
            notes.append("PDF format - may require OCR for scanned documents")
        elif ext in ['.zip', '.rar']:
            notes.append("Compressed archive - extract before processing")
        
        return notes
    
    def _calculate_confidence(self, content_type: str, file_size: int, encoding: Optional[str]) -> float:
        """Calculate analysis confidence score"""
        confidence = 0.8  # Base confidence
        
        # Content type confidence
        if content_type != 'other':
            confidence += 0.1
        
        # File size confidence
        if 1024 < file_size < 10 * 1024 * 1024:  # 1KB - 10MB
            confidence += 0.1
        elif file_size == 0:
            confidence -= 0.3
        
        # Encoding confidence
        if encoding and encoding != 'unknown':
            confidence += 0.05
        
        return min(1.0, max(0.1, confidence))
    
    def _estimate_import_time(self, file_size: int, complexity: str) -> float:
        """Estimate import processing time in seconds"""
        # Base time per MB
        base_time_per_mb = {
            'low': 0.5,
            'medium': 2.0,
            'high': 5.0
        }
        
        size_mb = file_size / (1024 * 1024)
        base_time = size_mb * base_time_per_mb.get(complexity, 2.0)
        
        # Minimum time
        return max(1.0, base_time)
    
    def _classify_document(self, file_path: Path) -> Dict[str, Any]:
        """Classify document files"""
        return {'subtype': 'text_document', 'processing': 'text_extraction'}
    
    def _classify_presentation(self, file_path: Path) -> Dict[str, Any]:
        """Classify presentation files"""
        return {'subtype': 'slide_presentation', 'processing': 'slide_extraction'}
    
    def _classify_spreadsheet(self, file_path: Path) -> Dict[str, Any]:
        """Classify spreadsheet files"""
        return {'subtype': 'data_table', 'processing': 'data_import'}
    
    def _classify_image(self, file_path: Path) -> Dict[str, Any]:
        """Classify image files"""
        return {'subtype': 'visual_media', 'processing': 'image_upload'}
    
    def _classify_video(self, file_path: Path) -> Dict[str, Any]:
        """Classify video files"""
        return {'subtype': 'video_media', 'processing': 'file_reference'}
    
    def _classify_audio(self, file_path: Path) -> Dict[str, Any]:
        """Classify audio files"""
        return {'subtype': 'audio_media', 'processing': 'file_reference'}
    
    def _classify_archive(self, file_path: Path) -> Dict[str, Any]:
        """Classify archive files"""
        return {'subtype': 'compressed_archive', 'processing': 'extraction_required'}
    
    def _classify_code(self, file_path: Path) -> Dict[str, Any]:
        """Classify code files"""
        return {'subtype': 'source_code', 'processing': 'syntax_highlighting'}
    
    def _classify_data(self, file_path: Path) -> Dict[str, Any]:
        """Classify data files"""
        return {'subtype': 'structured_data', 'processing': 'data_parsing'}
    
    def _classify_other(self, file_path: Path) -> Dict[str, Any]:
        """Classify other files"""
        return {'subtype': 'unknown', 'processing': 'file_reference'}
    
    def _generate_collection_analysis(self) -> CollectionAnalysis:
        """Generate comprehensive analysis of entire collection"""
        total_files = len(self.file_analyses)
        total_size = sum(analysis.file_size for analysis in self.file_analyses)
        
        # File type distribution
        file_types = {}
        content_types = {}
        for analysis in self.file_analyses:
            file_types[analysis.file_type] = file_types.get(analysis.file_type, 0) + 1
            content_types[analysis.content_type] = content_types.get(analysis.content_type, 0) + 1
        
        # Size distribution
        size_ranges = {
            'tiny': 0,      # < 1KB
            'small': 0,     # 1KB - 1MB
            'medium': 0,    # 1MB - 10MB
            'large': 0,     # 10MB - 100MB
            'huge': 0       # > 100MB
        }
        
        for analysis in self.file_analyses:
            size = analysis.file_size
            if size < 1024:
                size_ranges['tiny'] += 1
            elif size < 1024 * 1024:
                size_ranges['small'] += 1
            elif size < 10 * 1024 * 1024:
                size_ranges['medium'] += 1
            elif size < 100 * 1024 * 1024:
                size_ranges['large'] += 1
            else:
                size_ranges['huge'] += 1
        
        # Directory structure analysis
        directory_structure = self._analyze_directory_structure()
        
        # Suggested organization
        suggested_organization = self._generate_organization_suggestions()
        
        # Duplicate detection
        duplicate_groups = self._detect_duplicates()
        
        # Processing batches
        processing_batches = self._create_processing_batches()
        
        # Time estimation
        estimated_total_time = sum(analysis.estimated_import_time for analysis in self.file_analyses)
        
        # Resource requirements
        resource_requirements = self._calculate_resource_requirements()
        
        # Quality assessment
        analysis_quality = self._assess_analysis_quality()
        
        # Potential issues
        potential_issues = self._identify_potential_issues()
        
        # Optimization recommendations
        optimization_recommendations = self._generate_optimization_recommendations()
        
        return CollectionAnalysis(
            total_files=total_files,
            total_size=total_size,
            analysis_date=datetime.now().isoformat(),
            file_types=file_types,
            content_types=content_types,
            size_distribution=size_ranges,
            directory_structure=directory_structure,
            suggested_organization=suggested_organization,
            duplicate_groups=duplicate_groups,
            processing_batches=processing_batches,
            estimated_total_time=estimated_total_time,
            resource_requirements=resource_requirements,
            analysis_quality=analysis_quality,
            potential_issues=potential_issues,
            optimization_recommendations=optimization_recommendations
        )
    
    def _analyze_directory_structure(self) -> Dict[str, Any]:
        """Analyze existing directory structure"""
        structure = {}
        
        for analysis in self.file_analyses:
            path_parts = Path(analysis.file_path).relative_to(self.target_directory).parts[:-1]
            
            current = structure
            for part in path_parts:
                if part not in current:
                    current[part] = {'files': 0, 'subdirs': {}}
                current = current[part]['subdirs']
            
            # Count files in each directory
            current = structure
            for part in path_parts:
                current[part]['files'] += 1
                current = current[part]['subdirs']
        
        return structure
    
    def _generate_organization_suggestions(self) -> Dict[str, List[str]]:
        """Generate suggested Notion organization"""
        organization = {}
        
        for analysis in self.file_analyses:
            category = analysis.suggested_category
            if category not in organization:
                organization[category] = []
            organization[category].append(analysis.file_name)
        
        return organization
    
    def _detect_duplicates(self) -> List[List[str]]:
        """Detect duplicate files based on content hash"""
        hash_groups = {}
        
        for analysis in self.file_analyses:
            hash_val = analysis.content_hash
            if hash_val != 'unknown':
                if hash_val not in hash_groups:
                    hash_groups[hash_val] = []
                hash_groups[hash_val].append(analysis.file_path)
        
        # Return groups with more than one file
        return [group for group in hash_groups.values() if len(group) > 1]
    
    def _create_processing_batches(self) -> List[Dict[str, Any]]:
        """Create optimal processing batches"""
        # Sort by priority score
        sorted_analyses = sorted(self.file_analyses, key=lambda x: x.priority_score, reverse=True)
        
        batches = []
        current_batch = []
        current_batch_size = 0
        max_batch_size = 50 * 1024 * 1024  # 50MB per batch
        max_batch_files = 20  # 20 files per batch
        
        for analysis in sorted_analyses:
            if (len(current_batch) >= max_batch_files or 
                current_batch_size + analysis.file_size > max_batch_size):
                
                if current_batch:
                    batches.append({
                        'batch_id': len(batches) + 1,
                        'files': [a.file_path for a in current_batch],
                        'total_size': current_batch_size,
                        'file_count': len(current_batch),
                        'estimated_time': sum(a.estimated_import_time for a in current_batch)
                    })
                
                current_batch = []
                current_batch_size = 0
            
            current_batch.append(analysis)
            current_batch_size += analysis.file_size
        
        # Add final batch
        if current_batch:
            batches.append({
                'batch_id': len(batches) + 1,
                'files': [a.file_path for a in current_batch],
                'total_size': current_batch_size,
                'file_count': len(current_batch),
                'estimated_time': sum(a.estimated_import_time for a in current_batch)
            })
        
        return batches
    
    def _calculate_resource_requirements(self) -> Dict[str, Any]:
        """Calculate processing resource requirements"""
        total_size = sum(a.file_size for a in self.file_analyses)
        max_file_size = max(a.file_size for a in self.file_analyses) if self.file_analyses else 0
        
        return {
            'memory_required_mb': max(512, max_file_size // (1024 * 1024) * 2),
            'disk_space_required_mb': total_size // (1024 * 1024) * 1.5,  # 50% overhead
            'network_bandwidth_mb': total_size // (1024 * 1024),
            'processing_cores': min(4, max(1, len(self.file_analyses) // 100))
        }
    
    def _assess_analysis_quality(self) -> Dict[str, float]:
        """Assess quality of analysis results"""
        if not self.file_analyses:
            return {'overall': 0.0}
        
        confidence_scores = [a.analysis_confidence for a in self.file_analyses]
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        # Content analysis coverage
        content_analyzed = len([a for a in self.file_analyses if a.content_summary])
        content_coverage = content_analyzed / len(self.file_analyses)
        
        # Type classification accuracy
        classified = len([a for a in self.file_analyses if a.content_type != 'other'])
        classification_rate = classified / len(self.file_analyses)
        
        return {
            'overall': (avg_confidence + content_coverage + classification_rate) / 3,
            'confidence': avg_confidence,
            'content_coverage': content_coverage,
            'classification_rate': classification_rate
        }
    
    def _identify_potential_issues(self) -> List[str]:
        """Identify potential processing issues"""
        issues = []
        
        # Large files
        large_files = [a for a in self.file_analyses if a.file_size > 100 * 1024 * 1024]
        if large_files:
            issues.append(f"{len(large_files)} files larger than 100MB may require special handling")
        
        # Empty files
        empty_files = [a for a in self.file_analyses if a.file_size == 0]
        if empty_files:
            issues.append(f"{len(empty_files)} empty files detected")
        
        # Unknown file types
        unknown_types = [a for a in self.file_analyses if a.content_type == 'other']
        if unknown_types:
            issues.append(f"{len(unknown_types)} files with unknown content type")
        
        # Encoding issues
        encoding_issues = [a for a in self.file_analyses if a.encoding is None and a.content_type == 'document']
        if encoding_issues:
            issues.append(f"{len(encoding_issues)} text files with unknown encoding")
        
        # Duplicate files
        duplicates = self._detect_duplicates()
        if duplicates:
            total_duplicates = sum(len(group) - 1 for group in duplicates)
            issues.append(f"{total_duplicates} duplicate files detected")
        
        return issues
    
    def _generate_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Processing order optimization
        recommendations.append("Process high-priority files first to maximize early value")
        
        # Batch size optimization
        avg_file_size = sum(a.file_size for a in self.file_analyses) / len(self.file_analyses)
        if avg_file_size > 10 * 1024 * 1024:  # > 10MB
            recommendations.append("Use smaller batch sizes due to large average file size")
        
        # Content type specific recommendations
        content_types = {}
        for analysis in self.file_analyses:
            content_types[analysis.content_type] = content_types.get(analysis.content_type, 0) + 1
        
        if content_types.get('document', 0) > 50:
            recommendations.append("Consider parallel text extraction for document-heavy collection")
        
        if content_types.get('image', 0) > 100:
            recommendations.append("Implement image compression pipeline for large image collection")
        
        # Duplicate handling
        duplicates = self._detect_duplicates()
        if duplicates:
            recommendations.append("Remove duplicates before import to save time and space")
        
        # Archive handling
        archives = [a for a in self.file_analyses if a.content_type == 'archive']
        if archives:
            recommendations.append("Extract and analyze archive contents before import")
        
        return recommendations
    
    def _save_analysis_results(self):
        """Save analysis results to files"""
        # Save individual file analyses
        file_analyses_data = [asdict(analysis) for analysis in self.file_analyses]
        with open(self.output_directory / 'file_analyses.json', 'w') as f:
            json.dump(file_analyses_data, f, indent=2, default=str)
        
        # Save collection analysis
        if self.collection_analysis:
            with open(self.output_directory / 'collection_analysis.json', 'w') as f:
                json.dump(asdict(self.collection_analysis), f, indent=2, default=str)
        
        # Save summary report
        self._generate_summary_report()
        
        self.logger.info(f"Analysis results saved to {self.output_directory}")
    
    def _generate_summary_report(self):
        """Generate human-readable summary report"""
        if not self.collection_analysis:
            return
        
        report_lines = [
            "# Bulk File Analysis Summary Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Collection Overview",
            f"- Total Files: {self.collection_analysis.total_files:,}",
            f"- Total Size: {self.collection_analysis.total_size / (1024*1024*1024):.2f} GB",
            f"- Estimated Processing Time: {self.collection_analysis.estimated_total_time / 3600:.1f} hours",
            "",
            "## Content Type Distribution",
        ]
        
        for content_type, count in sorted(self.collection_analysis.content_types.items()):
            percentage = (count / self.collection_analysis.total_files) * 100
            report_lines.append(f"- {content_type.title()}: {count} files ({percentage:.1f}%)")
        
        report_lines.extend([
            "",
            "## Size Distribution",
        ])
        
        for size_range, count in self.collection_analysis.size_distribution.items():
            percentage = (count / self.collection_analysis.total_files) * 100
            report_lines.append(f"- {size_range.title()}: {count} files ({percentage:.1f}%)")
        
        report_lines.extend([
            "",
            "## Processing Batches",
            f"- Total Batches: {len(self.collection_analysis.processing_batches)}",
        ])
        
        for batch in self.collection_analysis.processing_batches[:5]:  # Show first 5 batches
            report_lines.append(
                f"- Batch {batch['batch_id']}: {batch['file_count']} files, "
                f"{batch['total_size'] / (1024*1024):.1f} MB, "
                f"{batch['estimated_time'] / 60:.1f} minutes"
            )
        
        if len(self.collection_analysis.processing_batches) > 5:
            report_lines.append(f"- ... and {len(self.collection_analysis.processing_batches) - 5} more batches")
        
        if self.collection_analysis.potential_issues:
            report_lines.extend([
                "",
                "## Potential Issues",
            ])
            for issue in self.collection_analysis.potential_issues:
                report_lines.append(f"- {issue}")
        
        if self.collection_analysis.optimization_recommendations:
            report_lines.extend([
                "",
                "## Optimization Recommendations",
            ])
            for recommendation in self.collection_analysis.optimization_recommendations:
                report_lines.append(f"- {recommendation}")
        
        # Save report
        with open(self.output_directory / 'summary_report.md', 'w') as f:
            f.write('\n'.join(report_lines))

def main():
    """Main function for testing the bulk file analyzer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze files for automated Notion import')
    parser.add_argument('target_directory', help='Directory containing files to analyze')
    parser.add_argument('--output', '-o', default='analysis_results', help='Output directory for results')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.target_directory):
        print(f"Error: Target directory '{args.target_directory}' does not exist")
        return 1
    
    print(f"🔍 Starting bulk file analysis of: {args.target_directory}")
    print(f"📊 Results will be saved to: {args.output}")
    
    analyzer = BulkFileAnalyzer(args.target_directory, args.output)
    collection_analysis = analyzer.analyze_collection()
    
    print(f"\n✅ Analysis Complete!")
    print(f"📁 Analyzed: {collection_analysis.total_files:,} files")
    print(f"💾 Total Size: {collection_analysis.total_size / (1024*1024*1024):.2f} GB")
    print(f"⏱️  Estimated Import Time: {collection_analysis.estimated_total_time / 3600:.1f} hours")
    print(f"📦 Processing Batches: {len(collection_analysis.processing_batches)}")
    
    if collection_analysis.potential_issues:
        print(f"\n⚠️  Potential Issues Found: {len(collection_analysis.potential_issues)}")
        for issue in collection_analysis.potential_issues[:3]:
            print(f"   - {issue}")
    
    print(f"\n📋 Detailed results saved to: {args.output}/")
    print(f"   - file_analyses.json: Individual file analysis")
    print(f"   - collection_analysis.json: Overall collection analysis")
    print(f"   - summary_report.md: Human-readable summary")
    
    return 0

if __name__ == "__main__":
    exit(main())

