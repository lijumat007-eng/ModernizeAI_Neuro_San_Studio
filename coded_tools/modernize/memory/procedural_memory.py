# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Tier 4: Procedural Memory Engine.
Stores reusable extraction heuristics, regex patterns, analysis workflows, and validation rules.
"""

from typing import Any, Dict, List, Optional


class ProceduralMemory:
    """
    Tier 4 Procedural Memory storing modernization recipes and heuristics.
    """

    def __init__(self):
        self.recipes: Dict[str, Dict[str, Any]] = {}
        self.initialize_default_recipes()

    def initialize_default_recipes(self):
        """Pre-populates deterministic parsing and validation procedures."""
        self.register_recipe(
            recipe_id="java_sql_extraction",
            description="Regex and AST pattern to extract embedded SQL statements from Java source code.",
            patterns=[
                r'SELECT\s+.*?\s+FROM\s+[A-Za-z0-9_]+',
                r'INSERT\s+INTO\s+[A-Za-z0-9_]+',
                r'UPDATE\s+[A-Za-z0-9_]+\s+SET',
                r'\{call\s+([A-Za-z0-9_]+)\(',
            ],
            target="Java",
        )
        self.register_recipe(
            recipe_id="ddl_table_extraction",
            description="Extracts CREATE TABLE definitions and foreign key constraints.",
            patterns=[
                r'CREATE\s+TABLE\s+([A-Za-z0-9_]+)\s*\((.*?)\);',
                r'CONSTRAINT\s+([A-Za-z0-9_]+)\s+FOREIGN\s+KEY\s*\(([A-Za-z0-9_]+)\)\s+REFERENCES\s+([A-Za-z0-9_]+)\(([A-Za-z0-9_]+)\)',
            ],
            target="SQL",
        )
        self.register_recipe(
            recipe_id="business_rule_extraction",
            description="Identifies formalized business rule statements and validation logic.",
            patterns=[
                r'(?i)Rule\s+(BR-[0-9]+):\s*(.*?)(?=\n\s*(?:Rule|\*|#|$))',
                r'(?i)validate[A-Z][a-zA-Z0-9]*',
            ],
            target="CodeAndDoc",
        )
        self.register_recipe(
            recipe_id="blast_radius_traversal",
            description="Procedure to perform depth-bounded bidirectional traversal on Knowledge Graph.",
            steps=[
                "1. Find matching target entity node (Seed Node).",
                "2. Traverse upstream edges (READS_FROM, WRITES_TO, CALLS) to find calling components.",
                "3. Traverse downstream edges (DEPENDS_ON, WRITES_TO, IMPACTS) to find affected data/rules.",
                "4. Compute impacted risk nodes and strongly connected components.",
            ],
            target="Graph",
        )

    def register_recipe(
        self,
        recipe_id: str,
        description: str,
        target: str,
        patterns: Optional[List[str]] = None,
        steps: Optional[List[str]] = None,
    ):
        self.recipes[recipe_id] = {
            "recipe_id": recipe_id,
            "description": description,
            "target": target,
            "patterns": patterns or [],
            "steps": steps or [],
        }

    def get_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        return self.recipes.get(recipe_id)

    def list_recipes(self) -> List[Dict[str, Any]]:
        return list(self.recipes.values())

    def to_dict(self) -> Dict[str, Any]:
        return self.recipes
