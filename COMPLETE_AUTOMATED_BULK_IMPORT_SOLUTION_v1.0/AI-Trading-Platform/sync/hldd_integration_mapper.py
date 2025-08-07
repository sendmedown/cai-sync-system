#!/usr/bin/env python3
"""
HLDD Integration Mapper for Semantic Sync Framework
==================================================

This module provides intelligent mapping and integration capabilities for
High-Level Design Documents (HLDD) within the Manus-Notion sync framework,
enabling automatic content classification, routing, and synchronization.

Author: Manus AI
Version: 1.0
Date: July 7, 2025
"""

import os
import re
import json
import yaml
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class HLDDSection:
    """Represents a section within the HLDD document"""
    section_id: str
    title: str
    content: str
    level: int
    parent_section: Optional[str] = None
    subsections: List[str] = None
    metadata: Dict[str, Any] = None
    notion_page_id: Optional[str] = None
    last_updated: str = None
    
    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []
        if self.metadata is None:
            self.metadata = {}
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()

@dataclass
class HLDDMapping:
    """Mapping configuration for HLDD content to Notion structure"""
    document_title: str
    version: str
    sections: List[HLDDSection]
    notion_workspace_id: str
    notion_parent_page_id: str
    sync_rules: Dict[str, Any]
    created_at: str
    updated_at: str

class HLDDSemanticMapper:
    """Semantic mapper for HLDD content integration"""
    
    def __init__(self, config_path: str = "hldd_mapping_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = self._setup_logging()
        
        # Semantic patterns for content classification
        self.section_patterns = {
            'architecture': [
                r'architecture', r'system design', r'technical architecture',
                r'component design', r'infrastructure', r'framework'
            ],
            'security': [
                r'security', r'authentication', r'authorization', r'encryption',
                r'compliance', r'audit', r'privacy', r'protection'
            ],
            'integration': [
                r'integration', r'api', r'interface', r'connector',
                r'middleware', r'bridge', r'sync', r'communication'
            ],
            'implementation': [
                r'implementation', r'development', r'coding', r'deployment',
                r'installation', r'setup', r'configuration'
            ],
            'testing': [
                r'testing', r'validation', r'verification', r'qa',
                r'quality assurance', r'test cases', r'scenarios'
            ],
            'documentation': [
                r'documentation', r'specification', r'requirements',
                r'user guide', r'manual', r'reference'
            ],
            'project_management': [
                r'project', r'timeline', r'milestone', r'task',
                r'schedule', r'planning', r'roadmap', r'backlog'
            ]
        }
        
        # Notion page templates for different content types
        self.notion_templates = {
            'architecture': {
                'icon': '🏗️',
                'properties': {
                    'Category': {'select': {'name': 'Architecture'}},
                    'Status': {'select': {'name': 'Active'}},
                    'Priority': {'select': {'name': 'High'}}
                }
            },
            'security': {
                'icon': '🔒',
                'properties': {
                    'Category': {'select': {'name': 'Security'}},
                    'Status': {'select': {'name': 'Active'}},
                    'Priority': {'select': {'name': 'Critical'}}
                }
            },
            'integration': {
                'icon': '🔗',
                'properties': {
                    'Category': {'select': {'name': 'Integration'}},
                    'Status': {'select': {'name': 'Active'}},
                    'Priority': {'select': {'name': 'High'}}
                }
            },
            'implementation': {
                'icon': '⚙️',
                'properties': {
                    'Category': {'select': {'name': 'Implementation'}},
                    'Status': {'select': {'name': 'In Progress'}},
                    'Priority': {'select': {'name': 'Medium'}}
                }
            },
            'testing': {
                'icon': '🧪',
                'properties': {
                    'Category': {'select': {'name': 'Testing'}},
                    'Status': {'select': {'name': 'Planned'}},
                    'Priority': {'select': {'name': 'Medium'}}
                }
            },
            'documentation': {
                'icon': '📚',
                'properties': {
                    'Category': {'select': {'name': 'Documentation'}},
                    'Status': {'select': {'name': 'Active'}},
                    'Priority': {'select': {'name': 'Low'}}
                }
            },
            'project_management': {
                'icon': '📋',
                'properties': {
                    'Category': {'select': {'name': 'Project Management'}},
                    'Status': {'select': {'name': 'Active'}},
                    'Priority': {'select': {'name': 'High'}}
                }
            }
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load HLDD mapping configuration"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return yaml.safe_load(f)
            else:
                # Create default configuration
                default_config = {
                    'hldd_source_files': [
                        'docs/HLDD_DIMIA_INTEGRATION_PLAN.md',
                        'docs/DNA_INSPIRED_MIDDLEWARE_ARCHITECTURE.md'
                    ],
                    'notion_workspace': {
                        'parent_page_id': 'YOUR_PARENT_PAGE_ID',
                        'database_id': 'YOUR_DATABASE_ID'
                    },
                    'sync_rules': {
                        'auto_create_pages': True,
                        'preserve_hierarchy': True,
                        'update_existing': True,
                        'create_cross_references': True
                    },
                    'content_processing': {
                        'extract_diagrams': True,
                        'process_code_blocks': True,
                        'create_task_items': True,
                        'generate_summaries': True
                    }
                }
                
                with open(self.config_path, 'w') as f:
                    yaml.dump(default_config, f, default_flow_style=False)
                
                return default_config
        except Exception as e:
            self.logger.error(f"Error loading HLDD mapping config: {e}")
            return {}
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the HLDD mapper"""
        logger = logging.getLogger('hldd_mapper')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def parse_hldd_document(self, file_path: str) -> List[HLDDSection]:
        """Parse HLDD document and extract structured sections"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            sections = []
            current_section = None
            section_counter = 0
            
            # Split content by headers
            lines = content.split('\n')
            current_content = []
            
            for line in lines:
                # Check for markdown headers
                header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
                
                if header_match:
                    # Save previous section if exists
                    if current_section:
                        current_section.content = '\n'.join(current_content).strip()
                        sections.append(current_section)
                    
                    # Create new section
                    header_level = len(header_match.group(1))
                    header_title = header_match.group(2).strip()
                    section_counter += 1
                    
                    current_section = HLDDSection(
                        section_id=f"section_{section_counter:03d}",
                        title=header_title,
                        content="",
                        level=header_level,
                        metadata={
                            'source_file': file_path,
                            'line_number': len(sections) + 1,
                            'category': self._classify_section_content(header_title)
                        }
                    )
                    current_content = []
                else:
                    current_content.append(line)
            
            # Add final section
            if current_section:
                current_section.content = '\n'.join(current_content).strip()
                sections.append(current_section)
            
            # Establish parent-child relationships
            self._establish_section_hierarchy(sections)
            
            self.logger.info(f"Parsed {len(sections)} sections from {file_path}")
            return sections
            
        except Exception as e:
            self.logger.error(f"Error parsing HLDD document {file_path}: {e}")
            return []
    
    def _classify_section_content(self, title: str) -> str:
        """Classify section content based on title and patterns"""
        title_lower = title.lower()
        
        for category, patterns in self.section_patterns.items():
            for pattern in patterns:
                if re.search(pattern, title_lower):
                    return category
        
        return 'general'
    
    def _establish_section_hierarchy(self, sections: List[HLDDSection]):
        """Establish parent-child relationships between sections"""
        section_stack = []
        
        for section in sections:
            # Find parent section based on header level
            while section_stack and section_stack[-1].level >= section.level:
                section_stack.pop()
            
            if section_stack:
                parent = section_stack[-1]
                section.parent_section = parent.section_id
                parent.subsections.append(section.section_id)
            
            section_stack.append(section)
    
    def extract_actionable_items(self, sections: List[HLDDSection]) -> List[Dict[str, Any]]:
        """Extract actionable items and tasks from HLDD sections"""
        actionable_items = []
        
        # Patterns for identifying actionable content
        task_patterns = [
            r'TODO:?\s*(.+)',
            r'Action:?\s*(.+)',
            r'Task:?\s*(.+)',
            r'Implementation:?\s*(.+)',
            r'Next steps?:?\s*(.+)',
            r'Requirements?:?\s*(.+)'
        ]
        
        for section in sections:
            content_lines = section.content.split('\n')
            
            for line_num, line in enumerate(content_lines):
                line = line.strip()
                
                for pattern in task_patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        task_description = match.group(1).strip()
                        
                        actionable_items.append({
                            'id': f"{section.section_id}_task_{len(actionable_items) + 1}",
                            'title': task_description,
                            'section_id': section.section_id,
                            'section_title': section.title,
                            'category': section.metadata.get('category', 'general'),
                            'priority': self._determine_task_priority(task_description),
                            'status': 'pending',
                            'created_at': datetime.now().isoformat(),
                            'source_line': line_num + 1,
                            'context': line
                        })
        
        return actionable_items
    
    def _determine_task_priority(self, task_description: str) -> str:
        """Determine task priority based on content analysis"""
        high_priority_keywords = [
            'critical', 'urgent', 'immediate', 'asap', 'priority',
            'security', 'bug', 'fix', 'error', 'issue'
        ]
        
        medium_priority_keywords = [
            'important', 'should', 'recommended', 'enhancement',
            'improvement', 'optimization'
        ]
        
        task_lower = task_description.lower()
        
        for keyword in high_priority_keywords:
            if keyword in task_lower:
                return 'high'
        
        for keyword in medium_priority_keywords:
            if keyword in task_lower:
                return 'medium'
        
        return 'low'
    
    def generate_notion_mapping(self, sections: List[HLDDSection]) -> HLDDMapping:
        """Generate Notion mapping configuration for HLDD sections"""
        mapping = HLDDMapping(
            document_title="AI Trading Platform HLDD",
            version="2.0",
            sections=sections,
            notion_workspace_id=self.config.get('notion_workspace', {}).get('workspace_id', ''),
            notion_parent_page_id=self.config.get('notion_workspace', {}).get('parent_page_id', ''),
            sync_rules=self.config.get('sync_rules', {}),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        return mapping
    
    def create_semantic_filemap(self, mapping: HLDDMapping) -> Dict[str, Any]:
        """Create semantic file mapping for sync framework"""
        filemap = {
            'document_info': {
                'title': mapping.document_title,
                'version': mapping.version,
                'created_at': mapping.created_at,
                'updated_at': mapping.updated_at
            },
            'notion_config': {
                'workspace_id': mapping.notion_workspace_id,
                'parent_page_id': mapping.notion_parent_page_id
            },
            'section_mappings': {},
            'content_routing': {
                'architecture': [],
                'security': [],
                'integration': [],
                'implementation': [],
                'testing': [],
                'documentation': [],
                'project_management': []
            },
            'sync_metadata': {
                'total_sections': len(mapping.sections),
                'last_sync': None,
                'sync_status': 'pending'
            }
        }
        
        # Map sections to routing categories
        for section in mapping.sections:
            category = section.metadata.get('category', 'general')
            
            section_info = {
                'section_id': section.section_id,
                'title': section.title,
                'level': section.level,
                'parent_section': section.parent_section,
                'notion_page_id': section.notion_page_id,
                'content_length': len(section.content),
                'last_updated': section.last_updated
            }
            
            filemap['section_mappings'][section.section_id] = section_info
            
            if category in filemap['content_routing']:
                filemap['content_routing'][category].append(section.section_id)
            else:
                filemap['content_routing']['general'] = filemap['content_routing'].get('general', [])
                filemap['content_routing']['general'].append(section.section_id)
        
        return filemap
    
    def save_mapping_to_file(self, mapping: HLDDMapping, output_path: str):
        """Save HLDD mapping to JSON file"""
        try:
            mapping_data = asdict(mapping)
            
            with open(output_path, 'w') as f:
                json.dump(mapping_data, f, indent=2, default=str)
            
            self.logger.info(f"HLDD mapping saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving HLDD mapping: {e}")
    
    def load_mapping_from_file(self, input_path: str) -> Optional[HLDDMapping]:
        """Load HLDD mapping from JSON file"""
        try:
            with open(input_path, 'r') as f:
                mapping_data = json.load(f)
            
            # Reconstruct HLDDSection objects
            sections = []
            for section_data in mapping_data['sections']:
                section = HLDDSection(**section_data)
                sections.append(section)
            
            mapping_data['sections'] = sections
            mapping = HLDDMapping(**mapping_data)
            
            self.logger.info(f"HLDD mapping loaded from {input_path}")
            return mapping
            
        except Exception as e:
            self.logger.error(f"Error loading HLDD mapping: {e}")
            return None

def process_hldd_files(hldd_files: List[str], output_dir: str = "sync/mappings") -> Dict[str, Any]:
    """Process multiple HLDD files and generate comprehensive mapping"""
    mapper = HLDDSemanticMapper()
    os.makedirs(output_dir, exist_ok=True)
    
    all_sections = []
    all_actionable_items = []
    
    for hldd_file in hldd_files:
        if os.path.exists(hldd_file):
            sections = mapper.parse_hldd_document(hldd_file)
            actionable_items = mapper.extract_actionable_items(sections)
            
            all_sections.extend(sections)
            all_actionable_items.extend(actionable_items)
            
            mapper.logger.info(f"Processed {hldd_file}: {len(sections)} sections, {len(actionable_items)} tasks")
    
    # Generate comprehensive mapping
    mapping = mapper.generate_notion_mapping(all_sections)
    filemap = mapper.create_semantic_filemap(mapping)
    
    # Save outputs
    mapping_file = os.path.join(output_dir, "hldd_notion_mapping.json")
    filemap_file = os.path.join(output_dir, "semantic_filemap.json")
    tasks_file = os.path.join(output_dir, "actionable_items.json")
    
    mapper.save_mapping_to_file(mapping, mapping_file)
    
    with open(filemap_file, 'w') as f:
        json.dump(filemap, f, indent=2)
    
    with open(tasks_file, 'w') as f:
        json.dump(all_actionable_items, f, indent=2)
    
    return {
        'mapping': mapping,
        'filemap': filemap,
        'actionable_items': all_actionable_items,
        'output_files': {
            'mapping': mapping_file,
            'filemap': filemap_file,
            'tasks': tasks_file
        }
    }

if __name__ == "__main__":
    # Example usage
    hldd_files = [
        "docs/HLDD_DIMIA_INTEGRATION_PLAN.md",
        "docs/DNA_INSPIRED_MIDDLEWARE_ARCHITECTURE.md"
    ]
    
    result = process_hldd_files(hldd_files)
    
    print(f"✅ Processed {len(result['mapping'].sections)} HLDD sections")
    print(f"✅ Extracted {len(result['actionable_items'])} actionable items")
    print(f"✅ Generated semantic mapping files:")
    for name, path in result['output_files'].items():
        print(f"   - {name}: {path}")

