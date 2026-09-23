# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
GraphBuilder: turns the linked IR sitting in Structural Memory (populated by
coded_tools.modernize.parsers.pipeline.parse_repository) into class-level
Knowledge Graph nodes and edges. Replaces the per-language extraction that
used to live inline in KnowledgeGraphTool.build_graph.

Class-level granularity: individual methods/fields never become their own
graph nodes (that detail lives in Structural Memory); a reference emitted by
a method rolls up to its owning class/procedure/program, and repeated calls
between the same two owners collapse into one edge carrying a `weight` and
a bounded `evidence_list` of file:line hits, rather than one edge per call.

Source-qualified identity: pass `source_id` and every symbol node this run
creates is keyed "<source_id>::<qualified_name>", so two sources with a
same-named class never collide. Shared resources (tables, views, procedures)
are NOT source-qualified - they use their bare canonical name, so a table
referenced from a Java repo and one defined in a DB source's own scan land
on the same node. A referenced-but-not-yet-defined table gets an inferred
placeholder node instead of a crash, since the DDL that truly defines it may
live in a source that hasn't been scanned yet.
"""

from typing import Any, Dict, List, Optional

# Symbol kinds that become their own graph node. Everything else (METHOD,
# FUNCTION, PARAGRAPH, FIELD, PROPERTY, NAMESPACE, PACKAGE-as-symbol-only-
# grouping is still included below since packages DO get a node) rolls up to
# the nearest ancestor of one of these kinds.
_GRAPH_NODE_KINDS = {
    "CLASS", "INTERFACE", "STRUCT", "ENUM", "RECORD",
    "PROGRAM", "TABLE", "VIEW", "PROCEDURE", "TRIGGER",
}

# Shared-resource kinds are canonical across sources (a table a Java repo reads
# and the DB source that defines it must land on the same node), so they are
# NEVER source-qualified. Code kinds are private to their own codebase/
# namespace and ARE source-qualified, so e.g. two repos' same-named "Utils"
# class don't collide.
_CANONICAL_KINDS = {"TABLE", "VIEW", "PROCEDURE", "TRIGGER"}

_NODE_TYPE_MAP = {
    "CLASS": "Class", "STRUCT": "Class", "RECORD": "Class", "ENUM": "Class",
    "INTERFACE": "Interface",
    "PROGRAM": "Program",
    "TABLE": "DatabaseTable",
    "VIEW": "View",
    "PROCEDURE": "StoredProcedure",
    "TRIGGER": "Trigger",
}

# References whose *kind itself* is graph-worthy (so from_symbol is already
# the owner, no roll-up needed) vs. those emitted from inside a method body
# (from_symbol is the method; roll up via its registered `parent` chain).
_EDGE_TYPE_MAP = {
    "CALLS": "CALLS",
    "INSTANTIATES": "INSTANTIATES",
    "INHERITS": "INHERITS",
    "IMPLEMENTS": "IMPLEMENTS",
    "INCLUDES": "INCLUDES",
    "READS_FROM": "READS_FROM",
    "WRITES_TO": "WRITES_TO",
    "EXECUTES": "EXECUTES",
    "PERFORMS": "CALLS",
}

_TABLE_LIKE_EDGE_KINDS = {"READS_FROM", "WRITES_TO"}


def remove_source_nodes(kg: Any, source_id: str) -> int:
    """
    Removes every node this `source_id` owns (its id starts with
    "<source_id>::", i.e. every source-qualified CLASS/INTERFACE/PROGRAM/...
    node) along with any edge touching one, before that source is rescanned.

    Canonical shared nodes (tables, views, procedures, triggers - bare ids,
    never source-qualified) are left untouched even if this source's earlier
    scan created or upgraded them, since another source may still depend on
    them; a full project rebuild is the only way to prune a canonical node
    that's genuinely gone. Returns the number of nodes removed.
    """
    prefix = f"{source_id}::"
    to_remove = [n for n in kg.graph.nodes if n.startswith(prefix)]
    kg.graph.remove_nodes_from(to_remove)
    return len(to_remove)


class GraphBuilder:
    """Stateless: `build()` reads `fabric.structural` and writes into `kg`."""

    @classmethod
    def build(cls, kg: Any, fabric: Any, source_id: str = "") -> Dict[str, int]:
        symbols: Dict[str, Dict[str, Any]] = fabric.structural.symbols
        references: List[Dict[str, Any]] = fabric.structural.references

        stats = {"nodes_added": 0, "edges_added": 0, "edges_merged": 0, "edges_skipped": 0}

        def node_id_for(qualified_name: str, kind: str) -> str:
            if kind in _CANONICAL_KINDS or not source_id:
                return qualified_name
            return f"{source_id}::{qualified_name}"

        # 1. One node per graph-worthy symbol (classes, interfaces, procedures, tables, ...)
        for qname, sym in symbols.items():
            kind = sym.get("kind")
            if kind not in _GRAPH_NODE_KINDS:
                continue
            nid = node_id_for(qname, kind)
            # Always (re)write, even if a node already exists at this id: a table
            # can get a low-confidence placeholder (see _ensure_table_placeholder)
            # from a reference scanned before the source that actually defines
            # it. When that defining source is scanned, this must upgrade the
            # placeholder in place, not skip it - nodes hold no aggregation
            # state (unlike edges), so overwriting is always safe.
            kg.add_node(
                node_id=nid,
                node_type=_NODE_TYPE_MAP.get(kind, "Module"),
                label=f"{sym.get('name', qname)}",
                source_file=sym.get("file_path", ""),
                line_start=sym.get("line_start", 1),
                line_end=sym.get("line_end", 1),
                confidence=1.0,
                extractor=f"{sym.get('language', 'unknown')}_parser",
                evidence_snippet=sym.get("signature") or sym.get("name", ""),
                properties={
                    "qualified_name": qname,
                    "kind": kind,
                    "language": sym.get("language", ""),
                    "source_id": source_id,
                    "modifiers": sym.get("modifiers", []),
                    "annotations": sym.get("annotations", []),
                    "base_types": sym.get("base_types", []),
                },
            )
            stats["nodes_added"] += 1

        def resolve_owner(from_symbol: str) -> Optional[str]:
            """Walks a symbol's `parent` chain up to the nearest graph-worthy ancestor,
            returning (node_id, kind) so the caller can apply the same canonical-vs-
            source-qualified rule used when the node was created."""
            seen = set()
            current = from_symbol
            while current and current not in seen:
                seen.add(current)
                sym = symbols.get(current)
                if sym is None:
                    return None
                if sym.get("kind") in _GRAPH_NODE_KINDS:
                    return node_id_for(current, sym["kind"])
                current = sym.get("parent")
            return None

        # 2. One (merged, weighted) edge per (owner, target) pair per reference kind
        for ref in references:
            kind = ref.get("kind")
            edge_type = _EDGE_TYPE_MAP.get(kind)
            if edge_type is None:
                continue  # IMPORTS and anything else not graph-worthy

            src_node = resolve_owner(ref["from_symbol"])
            if src_node is None:
                stats["edges_skipped"] += 1
                continue

            if kind in _TABLE_LIKE_EDGE_KINDS:
                target_node = ref["target_name"]  # canonical, cross-source, never qualified
                cls._ensure_table_placeholder(kg, target_node, ref)
                confidence = ref.get("confidence", 1.0)
            else:
                resolved = ref.get("resolved_target")
                if resolved:
                    resolved_kind = symbols.get(resolved, {}).get("kind", "")
                    target_node = node_id_for(resolved, resolved_kind)
                    confidence = ref.get("confidence", 1.0)
                else:
                    target_node = cls._ensure_external_placeholder(kg, ref["target_name"])
                    confidence = min(ref.get("confidence", 0.3), 0.3)

            if not kg.graph.has_node(src_node) or not kg.graph.has_node(target_node):
                stats["edges_skipped"] += 1
                continue

            merged = cls._add_or_merge_edge(
                kg, src_node, target_node, edge_type,
                file_path=ref.get("file_path", ""), line=ref.get("line", 1),
                evidence=ref.get("evidence", ""), confidence=confidence,
            )
            stats["edges_merged" if merged else "edges_added"] += 1

        return stats

    @staticmethod
    def _ensure_table_placeholder(kg: Any, table_name: str, ref: Dict[str, Any]) -> None:
        if kg.graph.has_node(table_name):
            return
        kg.add_node(
            node_id=table_name, node_type="DatabaseTable", label=f"Table: {table_name}",
            source_file=ref.get("file_path", ""), line_start=ref.get("line", 1), line_end=ref.get("line", 1),
            confidence=0.5, extractor="inferred_from_reference",
            evidence_snippet=f"Referenced via {ref.get('kind')} before its own definition was scanned.",
        )

    @staticmethod
    def _ensure_external_placeholder(kg: Any, target_name: str) -> str:
        node_id = f"external::{target_name}"
        if not kg.graph.has_node(node_id):
            kg.add_node(
                node_id=node_id, node_type="External", label=target_name,
                confidence=0.3, extractor="unresolved_reference",
                evidence_snippet=f"Referenced as '{target_name}' but not found among scanned sources "
                f"(likely a framework/library type, or a source not yet added to this project).",
            )
        return node_id

    @staticmethod
    def _add_or_merge_edge(
        kg: Any, src: str, tgt: str, edge_type: str, file_path: str, line: int, evidence: str, confidence: float,
    ) -> bool:
        """Returns True if an existing edge was merged into, False if a new one was created."""
        existing = kg.graph.get_edge_data(src, tgt, key=edge_type)
        entry = f"{file_path}:{line}"
        if existing:
            weight = existing.get("weight", 1) + 1
            evidence_list = list(existing.get("evidence_list", []))
            if entry not in evidence_list:
                evidence_list.append(entry)
            kg.add_edge(
                src, tgt, edge_type, source_file=existing.get("source_file", file_path),
                line_start=existing.get("line_start", line), line_end=line,
                confidence=max(existing.get("confidence", confidence), confidence),
                extractor="graph_builder", evidence_snippet=existing.get("evidence_snippet", evidence)[:200],
                properties={"weight": weight, "evidence_list": evidence_list[-25:]},
            )
            return True

        kg.add_edge(
            src, tgt, edge_type, source_file=file_path, line_start=line, line_end=line,
            confidence=confidence, extractor="graph_builder", evidence_snippet=evidence[:200],
            properties={"weight": 1, "evidence_list": [entry]},
        )
        return False
