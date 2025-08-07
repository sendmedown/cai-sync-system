#!/usr/bin/env python3
"""
Backlog Task Routing System for AI Trading Platform
===================================================

This module provides intelligent task routing, prioritization, and backlog management
capabilities for the AI Trading Platform development workflow, integrating with the
Manus-Notion sync framework for seamless project coordination.

Author: Manus AI
Version: 1.0
Date: July 7, 2025
"""

import os
import json
import csv
import yaml
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import re

class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskStatus(Enum):
    """Task status types"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskCategory(Enum):
    """Task category classifications"""
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    INTEGRATION = "integration"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    PROJECT_MANAGEMENT = "project_management"
    BUG_FIX = "bug_fix"
    ENHANCEMENT = "enhancement"
    RESEARCH = "research"

@dataclass
class TaskItem:
    """Represents a single task item in the backlog"""
    id: str
    title: str
    description: str
    category: TaskCategory
    priority: TaskPriority
    status: TaskStatus
    assignee: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    due_date: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    source_section: Optional[str] = None
    notion_page_id: Optional[str] = None
    manus_task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Sprint:
    """Represents a development sprint"""
    id: str
    name: str
    start_date: str
    end_date: str
    capacity_hours: float
    tasks: List[str] = field(default_factory=list)
    status: str = "planned"
    goals: List[str] = field(default_factory=list)
    retrospective_notes: Optional[str] = None

@dataclass
class TeamMember:
    """Represents a team member"""
    id: str
    name: str
    role: str
    capacity_hours_per_week: float
    skills: List[str] = field(default_factory=list)
    current_tasks: List[str] = field(default_factory=list)
    availability: Dict[str, bool] = field(default_factory=dict)

class BacklogTaskRouter:
    """Main backlog task routing and management system"""
    
    def __init__(self, config_path: str = "backlog_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = self._setup_logging()
        
        # Task storage
        self.tasks: Dict[str, TaskItem] = {}
        self.sprints: Dict[str, Sprint] = {}
        self.team_members: Dict[str, TeamMember] = {}
        
        # Routing rules
        self.routing_rules = self._initialize_routing_rules()
        
        # Load existing data
        self._load_existing_data()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load backlog configuration"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return yaml.safe_load(f)
            else:
                default_config = {
                    'team_members': [
                        {
                            'id': 'richard',
                            'name': 'Richard (Project Lead)',
                            'role': 'project_manager',
                            'capacity_hours_per_week': 40,
                            'skills': ['project_management', 'architecture', 'strategy']
                        },
                        {
                            'id': 'manus',
                            'name': 'Manus AI',
                            'role': 'ai_developer',
                            'capacity_hours_per_week': 168,  # 24/7 availability
                            'skills': ['implementation', 'documentation', 'testing', 'integration']
                        },
                        {
                            'id': 'chatgpt',
                            'name': 'ChatGPT Assistant',
                            'role': 'ai_assistant',
                            'capacity_hours_per_week': 168,
                            'skills': ['analysis', 'documentation', 'planning', 'research']
                        }
                    ],
                    'sprint_settings': {
                        'default_duration_weeks': 2,
                        'planning_buffer_hours': 8,
                        'review_buffer_hours': 4
                    },
                    'priority_weights': {
                        'critical': 100,
                        'high': 75,
                        'medium': 50,
                        'low': 25
                    },
                    'auto_assignment_rules': {
                        'architecture': ['richard', 'manus'],
                        'security': ['manus', 'richard'],
                        'implementation': ['manus'],
                        'documentation': ['chatgpt', 'manus'],
                        'project_management': ['richard'],
                        'testing': ['manus']
                    }
                }
                
                with open(self.config_path, 'w') as f:
                    yaml.dump(default_config, f, default_flow_style=False)
                
                return default_config
        except Exception as e:
            self.logger.error(f"Error loading backlog config: {e}")
            return {}
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the backlog router"""
        logger = logging.getLogger('backlog_router')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _initialize_routing_rules(self) -> Dict[str, Any]:
        """Initialize task routing rules"""
        return {
            'priority_escalation': {
                'days_in_pending': 7,
                'escalate_to': TaskPriority.HIGH
            },
            'auto_assignment': {
                'enabled': True,
                'consider_capacity': True,
                'consider_skills': True
            },
            'sprint_planning': {
                'auto_include_critical': True,
                'capacity_buffer_percent': 20,
                'dependency_ordering': True
            },
            'notification_triggers': {
                'task_overdue': True,
                'sprint_capacity_exceeded': True,
                'blocked_tasks': True
            }
        }
    
    def _load_existing_data(self):
        """Load existing tasks, sprints, and team data"""
        try:
            # Load tasks
            tasks_file = "tasks/backlog_tasks.json"
            if os.path.exists(tasks_file):
                with open(tasks_file, 'r') as f:
                    tasks_data = json.load(f)
                
                for task_data in tasks_data:
                    task = TaskItem(**task_data)
                    self.tasks[task.id] = task
            
            # Load sprints
            sprints_file = "tasks/sprints.json"
            if os.path.exists(sprints_file):
                with open(sprints_file, 'r') as f:
                    sprints_data = json.load(f)
                
                for sprint_data in sprints_data:
                    sprint = Sprint(**sprint_data)
                    self.sprints[sprint.id] = sprint
            
            # Load team members from config
            for member_data in self.config.get('team_members', []):
                member = TeamMember(**member_data)
                self.team_members[member.id] = member
            
            self.logger.info(f"Loaded {len(self.tasks)} tasks, {len(self.sprints)} sprints, {len(self.team_members)} team members")
            
        except Exception as e:
            self.logger.error(f"Error loading existing data: {e}")
    
    def import_hldd_actionable_items(self, actionable_items_file: str) -> int:
        """Import actionable items from HLDD processing"""
        try:
            with open(actionable_items_file, 'r') as f:
                actionable_items = json.load(f)
            
            imported_count = 0
            
            for item in actionable_items:
                # Convert to TaskItem
                task_id = f"hldd_{item['id']}"
                
                # Skip if already exists
                if task_id in self.tasks:
                    continue
                
                # Determine category from HLDD section
                category = self._map_hldd_category_to_task_category(item.get('category', 'general'))
                
                # Determine priority
                priority = self._map_hldd_priority_to_task_priority(item.get('priority', 'low'))
                
                # Create task
                task = TaskItem(
                    id=task_id,
                    title=item['title'],
                    description=f"From HLDD Section: {item['section_title']}\n\nContext: {item.get('context', '')}",
                    category=category,
                    priority=priority,
                    status=TaskStatus.PENDING,
                    source_section=item['section_id'],
                    tags=['hldd', 'imported'],
                    metadata={
                        'source_file': 'HLDD',
                        'section_title': item['section_title'],
                        'source_line': item.get('source_line'),
                        'import_date': datetime.now().isoformat()
                    }
                )
                
                self.tasks[task_id] = task
                imported_count += 1
            
            self.logger.info(f"Imported {imported_count} tasks from HLDD actionable items")
            return imported_count
            
        except Exception as e:
            self.logger.error(f"Error importing HLDD actionable items: {e}")
            return 0
    
    def _map_hldd_category_to_task_category(self, hldd_category: str) -> TaskCategory:
        """Map HLDD category to task category"""
        mapping = {
            'architecture': TaskCategory.ARCHITECTURE,
            'security': TaskCategory.SECURITY,
            'integration': TaskCategory.INTEGRATION,
            'implementation': TaskCategory.IMPLEMENTATION,
            'testing': TaskCategory.TESTING,
            'documentation': TaskCategory.DOCUMENTATION,
            'project_management': TaskCategory.PROJECT_MANAGEMENT,
            'general': TaskCategory.IMPLEMENTATION
        }
        
        return mapping.get(hldd_category, TaskCategory.IMPLEMENTATION)
    
    def _map_hldd_priority_to_task_priority(self, hldd_priority: str) -> TaskPriority:
        """Map HLDD priority to task priority"""
        mapping = {
            'critical': TaskPriority.CRITICAL,
            'high': TaskPriority.HIGH,
            'medium': TaskPriority.MEDIUM,
            'low': TaskPriority.LOW
        }
        
        return mapping.get(hldd_priority, TaskPriority.MEDIUM)
    
    def create_task(self, title: str, description: str, category: TaskCategory, 
                   priority: TaskPriority, **kwargs) -> TaskItem:
        """Create a new task"""
        task_id = f"task_{len(self.tasks) + 1:04d}"
        
        task = TaskItem(
            id=task_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            status=TaskStatus.PENDING,
            **kwargs
        )
        
        self.tasks[task_id] = task
        
        # Auto-assign if enabled
        if self.routing_rules['auto_assignment']['enabled']:
            self._auto_assign_task(task)
        
        self.logger.info(f"Created task {task_id}: {title}")
        return task
    
    def _auto_assign_task(self, task: TaskItem):
        """Automatically assign task based on category and team capacity"""
        try:
            # Get potential assignees for this category
            category_key = task.category.value
            potential_assignees = self.config.get('auto_assignment_rules', {}).get(category_key, [])
            
            if not potential_assignees:
                return
            
            # Find best assignee based on capacity and skills
            best_assignee = None
            min_workload = float('inf')
            
            for assignee_id in potential_assignees:
                if assignee_id in self.team_members:
                    member = self.team_members[assignee_id]
                    
                    # Calculate current workload
                    current_workload = len(member.current_tasks)
                    
                    # Check if member has relevant skills
                    has_relevant_skills = any(skill in member.skills for skill in [category_key, 'general'])
                    
                    if has_relevant_skills and current_workload < min_workload:
                        best_assignee = assignee_id
                        min_workload = current_workload
            
            if best_assignee:
                task.assignee = best_assignee
                self.team_members[best_assignee].current_tasks.append(task.id)
                self.logger.info(f"Auto-assigned task {task.id} to {best_assignee}")
        
        except Exception as e:
            self.logger.error(f"Error in auto-assignment: {e}")
    
    def prioritize_backlog(self) -> List[TaskItem]:
        """Prioritize backlog based on multiple factors"""
        tasks = list(self.tasks.values())
        
        def priority_score(task: TaskItem) -> float:
            score = 0
            
            # Base priority weight
            priority_weights = self.config.get('priority_weights', {})
            score += priority_weights.get(task.priority.value, 50)
            
            # Age factor (older tasks get higher priority)
            created_date = datetime.fromisoformat(task.created_at.replace('Z', '+00:00'))
            age_days = (datetime.now() - created_date).days
            score += age_days * 2
            
            # Dependency factor (tasks with no dependencies get higher priority)
            if not task.dependencies:
                score += 10
            
            # Blocker factor (blocked tasks get lower priority)
            if task.blockers:
                score -= 20
            
            # Category factor (critical categories get boost)
            critical_categories = [TaskCategory.SECURITY, TaskCategory.ARCHITECTURE]
            if task.category in critical_categories:
                score += 15
            
            return score
        
        # Sort by priority score (descending)
        prioritized_tasks = sorted(tasks, key=priority_score, reverse=True)
        
        return prioritized_tasks
    
    def create_sprint(self, name: str, start_date: str, end_date: str, 
                     capacity_hours: float, goals: List[str] = None) -> Sprint:
        """Create a new sprint"""
        sprint_id = f"sprint_{len(self.sprints) + 1:03d}"
        
        sprint = Sprint(
            id=sprint_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            capacity_hours=capacity_hours,
            goals=goals or []
        )
        
        self.sprints[sprint_id] = sprint
        self.logger.info(f"Created sprint {sprint_id}: {name}")
        
        return sprint
    
    def plan_sprint(self, sprint_id: str, auto_select_tasks: bool = True) -> Dict[str, Any]:
        """Plan a sprint by selecting appropriate tasks"""
        if sprint_id not in self.sprints:
            raise ValueError(f"Sprint {sprint_id} not found")
        
        sprint = self.sprints[sprint_id]
        
        if auto_select_tasks:
            # Get prioritized backlog
            prioritized_tasks = self.prioritize_backlog()
            
            # Filter available tasks (pending status, no blockers)
            available_tasks = [
                task for task in prioritized_tasks
                if task.status == TaskStatus.PENDING and not task.blockers
            ]
            
            # Select tasks for sprint based on capacity
            selected_tasks = []
            total_hours = 0
            capacity_with_buffer = sprint.capacity_hours * 0.8  # 20% buffer
            
            for task in available_tasks:
                estimated_hours = task.estimated_hours or 8  # Default 8 hours
                
                if total_hours + estimated_hours <= capacity_with_buffer:
                    selected_tasks.append(task)
                    total_hours += estimated_hours
                    
                    # Update task status and sprint assignment
                    task.status = TaskStatus.IN_PROGRESS
                    sprint.tasks.append(task.id)
            
            self.logger.info(f"Auto-selected {len(selected_tasks)} tasks for sprint {sprint_id}")
        
        # Generate sprint plan summary
        plan_summary = {
            'sprint_id': sprint_id,
            'sprint_name': sprint.name,
            'total_tasks': len(sprint.tasks),
            'estimated_hours': sum(
                self.tasks[task_id].estimated_hours or 8 
                for task_id in sprint.tasks
            ),
            'capacity_hours': sprint.capacity_hours,
            'capacity_utilization': (
                sum(self.tasks[task_id].estimated_hours or 8 for task_id in sprint.tasks) / 
                sprint.capacity_hours * 100
            ),
            'tasks_by_category': self._analyze_sprint_tasks_by_category(sprint),
            'tasks_by_assignee': self._analyze_sprint_tasks_by_assignee(sprint)
        }
        
        return plan_summary
    
    def _analyze_sprint_tasks_by_category(self, sprint: Sprint) -> Dict[str, int]:
        """Analyze sprint tasks by category"""
        category_counts = {}
        
        for task_id in sprint.tasks:
            if task_id in self.tasks:
                category = self.tasks[task_id].category.value
                category_counts[category] = category_counts.get(category, 0) + 1
        
        return category_counts
    
    def _analyze_sprint_tasks_by_assignee(self, sprint: Sprint) -> Dict[str, int]:
        """Analyze sprint tasks by assignee"""
        assignee_counts = {}
        
        for task_id in sprint.tasks:
            if task_id in self.tasks:
                assignee = self.tasks[task_id].assignee or 'unassigned'
                assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1
        
        return assignee_counts
    
    def generate_roadmap_csv(self, output_file: str = "tasks/roadmap.csv"):
        """Generate roadmap CSV for external tools"""
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'Task ID', 'Title', 'Description', 'Category', 'Priority', 
                    'Status', 'Assignee', 'Estimated Hours', 'Due Date',
                    'Created Date', 'Updated Date', 'Tags', 'Dependencies',
                    'Source Section', 'Notion Page ID', 'Manus Task ID'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for task in self.tasks.values():
                    writer.writerow({
                        'Task ID': task.id,
                        'Title': task.title,
                        'Description': task.description,
                        'Category': task.category.value,
                        'Priority': task.priority.value,
                        'Status': task.status.value,
                        'Assignee': task.assignee or '',
                        'Estimated Hours': task.estimated_hours or '',
                        'Due Date': task.due_date or '',
                        'Created Date': task.created_at,
                        'Updated Date': task.updated_at,
                        'Tags': ', '.join(task.tags),
                        'Dependencies': ', '.join(task.dependencies),
                        'Source Section': task.source_section or '',
                        'Notion Page ID': task.notion_page_id or '',
                        'Manus Task ID': task.manus_task_id or ''
                    })
            
            self.logger.info(f"Generated roadmap CSV: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Error generating roadmap CSV: {e}")
    
    def generate_backlog_json(self, output_file: str = "tasks/AI-Backlog.json"):
        """Generate AI-readable backlog JSON"""
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            backlog_data = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_tasks': len(self.tasks),
                    'total_sprints': len(self.sprints),
                    'team_members': len(self.team_members)
                },
                'tasks': [asdict(task) for task in self.tasks.values()],
                'sprints': [asdict(sprint) for sprint in self.sprints.values()],
                'team_members': [asdict(member) for member in self.team_members.values()],
                'routing_rules': self.routing_rules,
                'statistics': self._generate_backlog_statistics()
            }
            
            with open(output_file, 'w') as f:
                json.dump(backlog_data, f, indent=2, default=str)
            
            self.logger.info(f"Generated AI backlog JSON: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Error generating backlog JSON: {e}")
    
    def _generate_backlog_statistics(self) -> Dict[str, Any]:
        """Generate backlog statistics"""
        stats = {
            'tasks_by_status': {},
            'tasks_by_priority': {},
            'tasks_by_category': {},
            'tasks_by_assignee': {},
            'average_task_age_days': 0,
            'overdue_tasks': 0,
            'blocked_tasks': 0
        }
        
        total_age_days = 0
        current_date = datetime.now()
        
        for task in self.tasks.values():
            # Status distribution
            status = task.status.value
            stats['tasks_by_status'][status] = stats['tasks_by_status'].get(status, 0) + 1
            
            # Priority distribution
            priority = task.priority.value
            stats['tasks_by_priority'][priority] = stats['tasks_by_priority'].get(priority, 0) + 1
            
            # Category distribution
            category = task.category.value
            stats['tasks_by_category'][category] = stats['tasks_by_category'].get(category, 0) + 1
            
            # Assignee distribution
            assignee = task.assignee or 'unassigned'
            stats['tasks_by_assignee'][assignee] = stats['tasks_by_assignee'].get(assignee, 0) + 1
            
            # Age calculation
            created_date = datetime.fromisoformat(task.created_at.replace('Z', '+00:00'))
            age_days = (current_date - created_date).days
            total_age_days += age_days
            
            # Overdue tasks
            if task.due_date:
                due_date = datetime.fromisoformat(task.due_date.replace('Z', '+00:00'))
                if current_date > due_date and task.status != TaskStatus.COMPLETED:
                    stats['overdue_tasks'] += 1
            
            # Blocked tasks
            if task.blockers:
                stats['blocked_tasks'] += 1
        
        if self.tasks:
            stats['average_task_age_days'] = total_age_days / len(self.tasks)
        
        return stats
    
    def save_data(self):
        """Save all data to files"""
        try:
            os.makedirs("tasks", exist_ok=True)
            
            # Save tasks
            tasks_data = [asdict(task) for task in self.tasks.values()]
            with open("tasks/backlog_tasks.json", 'w') as f:
                json.dump(tasks_data, f, indent=2, default=str)
            
            # Save sprints
            sprints_data = [asdict(sprint) for sprint in self.sprints.values()]
            with open("tasks/sprints.json", 'w') as f:
                json.dump(sprints_data, f, indent=2, default=str)
            
            # Generate exports
            self.generate_roadmap_csv()
            self.generate_backlog_json()
            
            self.logger.info("All backlog data saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving backlog data: {e}")

def main():
    """Main function for testing and demonstration"""
    router = BacklogTaskRouter()
    
    # Import HLDD actionable items
    actionable_items_file = "sync/mappings/actionable_items.json"
    if os.path.exists(actionable_items_file):
        imported_count = router.import_hldd_actionable_items(actionable_items_file)
        print(f"✅ Imported {imported_count} tasks from HLDD")
    
    # Create a sample sprint
    start_date = datetime.now().strftime('%Y-%m-%d')
    end_date = (datetime.now() + timedelta(weeks=2)).strftime('%Y-%m-%d')
    
    sprint = router.create_sprint(
        name="HLDD Integration Sprint",
        start_date=start_date,
        end_date=end_date,
        capacity_hours=160,  # 2 weeks * 80 hours/week
        goals=[
            "Complete HLDD-Notion integration",
            "Implement semantic sync framework",
            "Establish task routing system"
        ]
    )
    
    # Plan the sprint
    plan_summary = router.plan_sprint(sprint.id)
    print(f"✅ Planned sprint: {plan_summary['total_tasks']} tasks, {plan_summary['capacity_utilization']:.1f}% capacity")
    
    # Save all data
    router.save_data()
    print("✅ Generated roadmap.csv and AI-Backlog.json")
    
    return router

if __name__ == "__main__":
    main()

