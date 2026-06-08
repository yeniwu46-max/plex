# -*- coding: utf-8 -*-
"""PLEX 多智能体模块（CrewAI + Mock fallback）。"""

from .crew import backend_name, get_agents_status, run_student_diagnose, run_teacher_suggestion

__all__ = [
    'backend_name',
    'get_agents_status',
    'run_student_diagnose',
    'run_teacher_suggestion',
]
