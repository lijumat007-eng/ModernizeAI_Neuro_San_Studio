# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Deterministic Document & SME Note Parser.
Extracts sections, business rule references, entity mentions, and requirements.
"""

import re
from typing import Any, Dict, List, Optional


class DocParser:
    """
    Deterministic parser for Markdown specifications and SME text notes.
    """

    @staticmethod
    def parse_document(file_path: str, content: str) -> Dict[str, Any]:
        rel_path = file_path.replace("\\", "/")
        lines = content.splitlines()

        # 1. Headings / Sections
        sections = []
        heading_matches = list(re.finditer(r"^(#{1,4})\s+(.+)$", content, re.MULTILINE))
        for i, match in enumerate(heading_matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            start_pos = match.end()
            start_line = content[: match.start()].count("\n") + 1
            
            end_pos = heading_matches[i + 1].start() if i + 1 < len(heading_matches) else len(content)
            end_line = content[:end_pos].count("\n") + 1
            body = content[start_pos:end_pos].strip()

            sections.append({
                "title": title,
                "level": level,
                "body": body,
                "start_line": start_line,
                "end_line": end_line,
            })

        # 2. Extract Business Rule tags (e.g. BR-01, Rule 1)
        rule_mentions = []
        rule_pattern = re.compile(r"(BR-[0-9]{2}|Rule\s+[0-9]+|SLA-[0-9]+)", re.IGNORECASE)
        for idx, line in enumerate(lines, start=1):
            for match in rule_pattern.finditer(line):
                rule_mentions.append({
                    "rule_tag": match.group(1).upper(),
                    "line": idx,
                    "snippet": line.strip(),
                })

        # 3. Extract Table Mentions (e.g., POLICY_MASTER, CLAIMS_RECORD)
        table_pattern = re.compile(r"\b([A-Z][A-Z0-9_]{3,}_(?:MASTER|RECORD|ACCOUNT|LOG|ITEMS|TABLE))\b")
        table_mentions = set()
        for line in lines:
            for match in table_pattern.finditer(line):
                table_mentions.add(match.group(1).upper())

        return {
            "file_path": rel_path,
            "sections": sections,
            "rule_mentions": rule_mentions,
            "table_mentions": list(table_mentions),
        }
