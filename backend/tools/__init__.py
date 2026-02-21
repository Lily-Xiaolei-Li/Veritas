"""
Agent-B Research Tools
======================

可重用的学术研究工具集。

工具列表:
- reference_lookup: 从 VF Store 查找论文参考文献列表
- section_lookup: 从 VF Store 查找论文特定章节
"""

from .reference_lookup import lookup_references, ReferenceLookup, extract_references_from_md
from .section_lookup import (
    lookup_section, 
    lookup_all_sections, 
    SectionLookup,
    lookup_abstract,
    lookup_introduction,
    lookup_methodology,
    lookup_literature_review,
    lookup_empirical_analysis,
    lookup_conclusion,
    AVAILABLE_SECTIONS
)

__all__ = [
    # reference_lookup
    'lookup_references',
    'ReferenceLookup', 
    'extract_references_from_md',
    # section_lookup
    'lookup_section',
    'lookup_all_sections',
    'SectionLookup',
    'lookup_abstract',
    'lookup_introduction',
    'lookup_methodology',
    'lookup_literature_review',
    'lookup_empirical_analysis',
    'lookup_conclusion',
    'AVAILABLE_SECTIONS',
]
