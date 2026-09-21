# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Dynamic Business Rules Extraction Engine.
Extracts business rules, constraints, validation logic, and thresholds
dynamically from Java AST code, database stored procedures, and specification documents.
"""

import re
from typing import Any, Dict, List, Optional
from coded_tools.modernize.memory.memory_manager_tool import MemoryFabric
from coded_tools.modernize.parsers.ddl_parser import DdlParser
from coded_tools.modernize.parsers.doc_parser import DocParser
from coded_tools.modernize.parsers.java_parser import JavaParser


class RulesExtractor:
    """
    Extracts and synthesizes enterprise business rules dynamically without hardcoding.
    """

    @classmethod
    def extract_from_java(cls, file_path: str, content: str) -> List[Dict[str, Any]]:
        """
        Dynamically analyzes Java source code for validation logic, thresholds, and business checks.
        """
        rules = []
        lines = content.splitlines()

        # Method pattern with body detection
        method_pattern = re.compile(
            r"^\s*(?:public|protected|private)?\s*(?:static\s+|final\s+)*([A-Za-z0-9_<>]+)\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*(?:throws\s+[A-Za-z0-9_,\s]+)?\s*\{",
            re.MULTILINE,
        )

        for m in method_pattern.finditer(content):
            ret_type, m_name, params = m.groups()
            start_line = content[: m.start()].count("\n") + 1

            # Only inspect methods that perform validation, eligibility, or calculation checks
            is_rule_method = any(
                prefix in m_name.lower()
                for prefix in ("validate", "iseligible", "ishighrisk", "check", "calculate", "process")
            ) or ret_type.lower() in ("boolean", "validationresult")

            if not is_rule_method:
                continue

            # Find method body boundaries by tracking curly braces
            body_start_pos = m.end() - 1
            brace_count = 0
            body_end_pos = len(content)
            for i in range(body_start_pos, len(content)):
                if content[i] == "{":
                    brace_count += 1
                elif content[i] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        body_end_pos = i + 1
                        break

            end_line = content[:body_end_pos].count("\n") + 1
            body_snippet = content[body_start_pos:body_end_pos]

            # Extract condition statements (if statements) inside method body
            condition_matches = re.findall(r"if\s*\((.*?)\)", body_snippet, re.DOTALL)
            clean_conditions = [re.sub(r"\s+", " ", cond.strip()) for cond in condition_matches]

            # Extract threshold numbers ($2500, $50000, 7 days, etc.)
            thresholds = re.findall(r"\b\d+(?:\.\d+)?\b", body_snippet)

            # Generate descriptive rule name and specification from method name and conditions
            readable_name = re.sub(r"([a-z])([A-Z])", r"\1 \2", m_name)
            readable_name = readable_name.replace("validate ", "").replace("is ", "").title() + " Check"

            # Derive condition summary
            condition_desc = " AND ".join(clean_conditions[:2]) if clean_conditions else "Enforces business condition."

            rules.append({
                "rule_name": readable_name,
                "method_name": m_name,
                "return_type": ret_type,
                "source_file": file_path.replace("\\", "/"),
                "line_start": start_line,
                "line_end": end_line,
                "conditions": clean_conditions,
                "thresholds": thresholds,
                "specification": f"Method {m_name}() validates: {condition_desc}",
                "confidence": 0.95,
                "extractor": "java_ast_condition_analyzer",
            })

        return rules

    @classmethod
    def extract_from_stored_procedure(cls, file_path: str, content: str) -> List[Dict[str, Any]]:
        """
        Dynamically extracts business logic conditions and constraint checks from SQL stored procedures.
        """
        rules = []
        rel_path = file_path.replace("\\", "/")

        # Match IF statements within SQL stored procedure bodies
        if_pattern = re.compile(r"IF\s+(.*?)\s+THEN\s*(.*?)(?=ELSE|END\s+IF|ELSIF)", re.IGNORECASE | re.DOTALL)
        for idx, m in enumerate(if_pattern.finditer(content), start=1):
            condition = re.sub(r"\s+", " ", m.group(1).strip())
            start_line = content[: m.start()].count("\n") + 1
            end_line = content[: m.end()].count("\n") + 1

            rules.append({
                "rule_name": f"Stored Procedure Constraint #{idx}",
                "method_name": "SP_PROCESS_CLAIM",
                "return_type": "SQL_EXCEPTION",
                "source_file": rel_path,
                "line_start": start_line,
                "line_end": end_line,
                "conditions": [condition],
                "thresholds": re.findall(r"\b\d+(?:\.\d+)?\b", condition),
                "specification": f"Stored procedure validates: IF {condition}",
                "confidence": 0.90,
                "extractor": "sql_sp_analyzer",
            })

        return rules

    @classmethod
    def extract_from_documents(cls, file_path: str, content: str) -> List[Dict[str, Any]]:
        """
        Extracts documented business rules, SLAs, and constraints from Markdown and text documents.
        """
        doc_rules = []
        rel_path = file_path.replace("\\", "/")
        lines = content.splitlines()

        rule_regex = re.compile(r"^\s*[-*•]?\s*(?:Rule\s+)?(BR-\d+|SLA-\d+|Rule\s+\d+)[:\-]\s*(.+)$", re.IGNORECASE)
        for idx, line in enumerate(lines, start=1):
            match = rule_regex.search(line)
            if match:
                tag = match.group(1).upper()
                desc = match.group(2).strip()
                doc_rules.append({
                    "rule_tag": tag,
                    "description": desc,
                    "source_file": rel_path,
                    "line_number": idx,
                })

        return doc_rules

    @classmethod
    def extract_all(cls, fabric: MemoryFabric) -> List[Dict[str, Any]]:
        """
        Extracts and correlates all business rules across Java source, SQL procedures, and documentation.
        Synthesizes formal IDs (BR-01, BR-02, ...) with line-level provenance.
        """
        all_rules = []

        # 1. Extract from Java files
        for path, rec in fabric.raw._files.items():
            if path.endswith(".java") and ("Service" in path or "Validation" in path or "Claim" in path):
                content = rec.get_lines(1, rec.line_count)
                extracted = cls.extract_from_java(path, content)
                all_rules.extend(extracted)

        # 2. Extract from Stored Procedures
        for path, rec in fabric.raw._files.items():
            if path.endswith(".sql") or path.endswith(".ddl"):
                content = rec.get_lines(1, rec.line_count)
                if "PROCEDURE" in content.upper():
                    sp_rules = cls.extract_from_stored_procedure(path, content)
                    all_rules.extend(sp_rules)

        # 3. Extract from Documents
        doc_mentions = []
        for path, rec in fabric.raw._files.items():
            if path.endswith((".md", ".txt")):
                content = rec.get_lines(1, rec.line_count)
                doc_rules = cls.extract_from_documents(path, content)
                doc_mentions.extend(doc_rules)

        # 4. Number and formalize rules
        formalized_rules = []
        for idx, r in enumerate(all_rules, start=1):
            r_id = f"BR-{idx:02d}"
            r["rule_id"] = r_id
            # Correlate with any doc mentions
            matched_doc = next(
                (d for d in doc_mentions if any(w in d["description"].lower() for w in r["rule_name"].lower().split())),
                None,
            )
            if matched_doc:
                r["doc_provenance"] = f"{matched_doc['source_file']}:{matched_doc['line_number']}"
                r["doc_statement"] = matched_doc["description"]
            else:
                r["doc_provenance"] = "Inferred from source AST"
                r["doc_statement"] = r["specification"]

            formalized_rules.append(r)

        return formalized_rules
