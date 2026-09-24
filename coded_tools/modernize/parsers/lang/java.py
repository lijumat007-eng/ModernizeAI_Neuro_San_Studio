# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Java parser backed by the real tree-sitter Java grammar (not regex).
Extracts package/imports, classes/interfaces/enums/records (including nested
types), fields, methods with parameter and return types, annotations,
extends/implements, `new T()` instantiation, method calls (resolved against
local fields/params/locals where possible), Spring REST endpoints, and
embedded SQL (including string-concatenation SQL that a single-literal regex
would miss).
"""

import re
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from coded_tools.modernize.parsers import embedded_sql
from coded_tools.modernize.parsers.base import TreeSitterParser
from coded_tools.modernize.parsers.ir import Endpoint
from coded_tools.modernize.parsers.ir import ParseResult
from coded_tools.modernize.parsers.ir import Reference
from coded_tools.modernize.parsers.ir import Symbol

_TYPE_DECL_KINDS = {
    "class_declaration": "CLASS",
    "interface_declaration": "INTERFACE",
    "enum_declaration": "ENUM",
    "record_declaration": "RECORD",
}

_MAPPING_ANNOTATIONS = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
    "RequestMapping": "REQUEST",
}


def simple_type_name(type_text: str) -> str:
    """Strips generics, array brackets, and package qualification down to the bare type name.

    "java.util.List<Order>" -> "List", "Order[]" -> "Order", "int" -> "int"
    """
    t = type_text.strip()
    t = t.split("<", 1)[0]
    t = t.replace("[]", "").strip()
    if "." in t:
        t = t.rsplit(".", 1)[-1]
    return t


class JavaParser(TreeSitterParser):
    language = "java"
    extensions = [".java"]
    ts_language_name = "java"

    def _extract(self, root, source_bytes: bytes, file_path: str, result: ParseResult) -> None:
        package = self._find_package(root, source_bytes)
        imports = self._find_imports(root, source_bytes)
        for imp in imports:
            result.references.append(
                Reference(
                    from_symbol=package or file_path,
                    target_name=imp,
                    kind="IMPORTS",
                    file_path=file_path,
                    line=1,
                    evidence=f"import {imp};",
                )
            )

        for child in root.children:
            if child.type in _TYPE_DECL_KINDS:
                self._handle_type_decl(
                    child,
                    _TYPE_DECL_KINDS[child.type],
                    source_bytes,
                    file_path,
                    result,
                    package=package,
                    parent_qname=None,
                    imports=imports,
                )

    # ------------------------------------------------------------------ #
    # Package / imports
    # ------------------------------------------------------------------ #

    def _find_package(self, root, source_bytes: bytes) -> str:
        for child in root.children:
            if child.type == "package_declaration":
                for c in child.children:
                    if c.type in ("scoped_identifier", "identifier"):
                        return self.text(c, source_bytes)
        return ""

    def _find_imports(self, root, source_bytes: bytes) -> List[str]:
        imports = []
        for child in root.children:
            if child.type == "import_declaration":
                for c in child.children:
                    if c.type in ("scoped_identifier", "identifier"):
                        imports.append(self.text(c, source_bytes))
        return imports

    # ------------------------------------------------------------------ #
    # Type declarations (class / interface / enum / record, incl. nested)
    # ------------------------------------------------------------------ #

    def _handle_type_decl(
        self,
        node,
        kind: str,
        source_bytes: bytes,
        file_path: str,
        result: ParseResult,
        package: str,
        parent_qname: Optional[str],
        imports: List[str],
    ) -> None:
        name_node = node.child_by_field_name("name")
        name = self.text(name_node, source_bytes)
        if not name:
            return
        qname = f"{parent_qname}.{name}" if parent_qname else (f"{package}.{name}" if package else name)

        modifiers_node = self._first_child_of_type(node, "modifiers")
        modifiers, annotations = self._split_modifiers(modifiers_node, source_bytes)

        base_types: List[str] = []
        superclass_node = node.child_by_field_name("superclass")
        if superclass_node is not None:
            for type_id in self._find_types(superclass_node):
                base_name = self.text(type_id, source_bytes)
                base_types.append(base_name)
                result.references.append(
                    Reference(
                        from_symbol=qname,
                        target_name=simple_type_name(base_name),
                        kind="INHERITS",
                        file_path=file_path,
                        line=self.line_start(node),
                        evidence=f"{name} extends {base_name}",
                    )
                )
        interfaces_node = node.child_by_field_name("interfaces")
        if interfaces_node is not None:
            for type_id in self._find_types(interfaces_node):
                base_name = self.text(type_id, source_bytes)
                base_types.append(base_name)
                result.references.append(
                    Reference(
                        from_symbol=qname,
                        target_name=simple_type_name(base_name),
                        kind="IMPLEMENTS",
                        file_path=file_path,
                        line=self.line_start(node),
                        evidence=f"{name} implements {base_name}",
                    )
                )

        symbol = Symbol(
            kind=kind,
            name=name,
            qualified_name=qname,
            language="java",
            file_path=file_path,
            line_start=self.line_start(node),
            line_end=self.line_end(node),
            parent=parent_qname,
            modifiers=modifiers,
            annotations=annotations,
            base_types=base_types,
        )
        result.symbols.append(symbol)

        # REST endpoint detection: class-level @RestController/@Controller + a base path
        class_base_path = ""
        for ann_text in annotations:
            m = re.match(r"RequestMapping\((?:value\s*=\s*)?\"([^\"]*)\"", ann_text)
            if m:
                class_base_path = m.group(1)

        body = node.child_by_field_name("body")
        if body is None:
            return

        # Field types visible to methods in this class, for call-receiver resolution.
        field_types: Dict[str, str] = {}

        for member in body.children:
            if member.type in _TYPE_DECL_KINDS:
                self._handle_type_decl(
                    member,
                    _TYPE_DECL_KINDS[member.type],
                    source_bytes,
                    file_path,
                    result,
                    package=package,
                    parent_qname=qname,
                    imports=imports,
                )
            elif member.type == "field_declaration":
                self._handle_field(member, qname, source_bytes, file_path, result, field_types)
            elif member.type in ("method_declaration", "constructor_declaration"):
                self._handle_method(
                    member,
                    qname,
                    source_bytes,
                    file_path,
                    result,
                    field_types,
                    class_base_path,
                )

    @staticmethod
    def _first_child_of_type(node, type_name: str):
        for c in node.children:
            if c.type == type_name:
                return c
        return None

    def _find_types(self, node) -> List:
        """Returns type_identifier / scoped_type_identifier / generic_type nodes directly under node."""
        out = []
        for c in node.children:
            if c.type in ("type_identifier", "scoped_type_identifier", "generic_type"):
                out.append(c)
            elif c.type == "type_list":
                out.extend(self._find_types(c))
        return out

    def _split_modifiers(self, modifiers_node, source_bytes: bytes) -> Tuple[List[str], List[str]]:
        modifiers: List[str] = []
        annotations: List[str] = []
        if modifiers_node is None:
            return modifiers, annotations
        for c in modifiers_node.children:
            if c.type in ("marker_annotation", "annotation"):
                annotations.append(self.text(c, source_bytes).lstrip("@"))
            elif c.type not in ("(", ")"):
                modifiers.append(self.text(c, source_bytes))
        return modifiers, annotations

    # ------------------------------------------------------------------ #
    # Fields
    # ------------------------------------------------------------------ #

    def _handle_field(
        self,
        node,
        class_qname: str,
        source_bytes: bytes,
        file_path: str,
        result: ParseResult,
        field_types: Dict[str, str],
    ) -> None:
        type_node = node.child_by_field_name("type")
        type_text = self.text(type_node, source_bytes) if type_node is not None else ""
        modifiers_node = self._first_child_of_type(node, "modifiers")
        modifiers, annotations = self._split_modifiers(modifiers_node, source_bytes)

        for declarator in node.children:
            if declarator.type != "variable_declarator":
                continue
            name_node = declarator.child_by_field_name("name")
            f_name = self.text(name_node, source_bytes)
            if not f_name:
                continue
            field_types[f_name] = simple_type_name(type_text)
            result.symbols.append(
                Symbol(
                    kind="FIELD",
                    name=f_name,
                    qualified_name=f"{class_qname}.{f_name}",
                    language="java",
                    file_path=file_path,
                    line_start=self.line_start(node),
                    line_end=self.line_end(node),
                    parent=class_qname,
                    modifiers=modifiers,
                    annotations=annotations,
                    return_type=type_text,
                )
            )

    # ------------------------------------------------------------------ #
    # Methods / constructors
    # ------------------------------------------------------------------ #

    def _handle_method(
        self,
        node,
        class_qname: str,
        source_bytes: bytes,
        file_path: str,
        result: ParseResult,
        field_types: Dict[str, str],
        class_base_path: str,
    ) -> None:
        name_node = node.child_by_field_name("name")
        m_name = self.text(name_node, source_bytes) if name_node is not None else "<init>"
        type_node = node.child_by_field_name("type")
        return_type = self.text(type_node, source_bytes) if type_node is not None else ""

        params_node = node.child_by_field_name("parameters")
        param_types: Dict[str, str] = {}
        param_sig_parts: List[str] = []
        if params_node is not None:
            for p in params_node.children:
                if p.type != "formal_parameter":
                    continue
                p_type_node = p.child_by_field_name("type")
                p_name_node = p.child_by_field_name("name")
                p_type = self.text(p_type_node, source_bytes) if p_type_node is not None else ""
                p_name = self.text(p_name_node, source_bytes) if p_name_node is not None else ""
                if p_name:
                    param_types[p_name] = simple_type_name(p_type)
                param_sig_parts.append(f"{p_type} {p_name}".strip())

        signature = f"{m_name}({', '.join(param_sig_parts)})"
        qname = f"{class_qname}.{m_name}({','.join(t for t in param_types.values())})"

        modifiers_node = self._first_child_of_type(node, "modifiers")
        modifiers, annotations = self._split_modifiers(modifiers_node, source_bytes)

        result.symbols.append(
            Symbol(
                kind="METHOD",
                name=m_name,
                qualified_name=qname,
                language="java",
                file_path=file_path,
                line_start=self.line_start(node),
                line_end=self.line_end(node),
                parent=class_qname,
                modifiers=modifiers,
                annotations=annotations,
                signature=signature,
                return_type=return_type,
            )
        )

        # Spring endpoint detection
        for ann_text in annotations:
            for mapping_ann, http_method in _MAPPING_ANNOTATIONS.items():
                if ann_text.startswith(mapping_ann):
                    path_m = re.search(r"\"([^\"]*)\"", ann_text)
                    path = path_m.group(1) if path_m else ""
                    full_route = (class_base_path.rstrip("/") + "/" + path.lstrip("/")).replace("//", "/")
                    result.endpoints.append(
                        Endpoint(
                            route=full_route or path,
                            http_method=http_method,
                            owner_symbol=qname,
                            file_path=file_path,
                            line=self.line_start(node),
                            protocol="REST",
                        )
                    )

        body = node.child_by_field_name("body")
        if body is None:
            return

        local_types: Dict[str, str] = {}
        self._walk_body(body, source_bytes, file_path, result, qname, field_types, param_types, local_types)

    def _walk_body(
        self,
        body,
        source_bytes: bytes,
        file_path: str,
        result: ParseResult,
        method_qname: str,
        field_types: Dict[str, str],
        param_types: Dict[str, str],
        local_types: Dict[str, str],
    ) -> None:
        consumed: set = set()

        for node in self.walk(body):
            if id(node) in consumed:
                continue

            if node.type == "local_variable_declaration":
                type_node = node.child_by_field_name("type")
                type_text = self.text(type_node, source_bytes) if type_node is not None else ""
                for declarator in node.children:
                    if declarator.type == "variable_declarator":
                        n = declarator.child_by_field_name("name")
                        if n is not None:
                            local_types[self.text(n, source_bytes)] = simple_type_name(type_text)

            elif node.type == "object_creation_expression":
                type_node = node.child_by_field_name("type")
                type_text = self.text(type_node, source_bytes) if type_node is not None else ""
                if type_text:
                    result.references.append(
                        Reference(
                            from_symbol=method_qname,
                            target_name=simple_type_name(type_text),
                            kind="INSTANTIATES",
                            file_path=file_path,
                            line=self.line_start(node),
                            evidence=self.text(node, source_bytes)[:120],
                        )
                    )

            elif node.type == "method_invocation":
                self._handle_call(
                    node,
                    source_bytes,
                    file_path,
                    result,
                    method_qname,
                    field_types,
                    param_types,
                    local_types,
                )

            elif node.type in ("string_literal", "binary_expression"):
                sql_text = embedded_sql.join_string_concat(node, source_bytes)
                if sql_text and embedded_sql.looks_like_sql(sql_text):
                    result.sql_accesses.append(
                        embedded_sql.build_sql_access(
                            sql_text,
                            file_path,
                            self.line_start(node),
                            owner_symbol=method_qname,
                        )
                    )
                for d in self.walk(node):
                    consumed.add(id(d))

    def _handle_call(
        self,
        node,
        source_bytes: bytes,
        file_path: str,
        result: ParseResult,
        method_qname: str,
        field_types: Dict[str, str],
        param_types: Dict[str, str],
        local_types: Dict[str, str],
    ) -> None:
        name_node = node.child_by_field_name("name")
        called_name = self.text(name_node, source_bytes) if name_node is not None else ""
        if not called_name:
            return

        object_node = node.child_by_field_name("object")
        if object_node is None:
            # Bare call: helper() - almost always a self-call, not interesting for the graph.
            return

        receiver_text = self.text(object_node, source_bytes)
        # Unwrap `this.repo` -> "repo"
        if object_node.type == "field_access":
            field_name_node = object_node.child_by_field_name("field")
            receiver_text = self.text(field_name_node, source_bytes) if field_name_node is not None else receiver_text
        elif object_node.type != "identifier":
            # Chained call like `a().b()`: not resolvable to a receiver type here; skip.
            return

        receiver_type = (
            local_types.get(receiver_text) or param_types.get(receiver_text) or field_types.get(receiver_text)
        )
        if receiver_type is None:
            # Could be a static call on a class name (Type.method()), or an unresolved
            # local/field. Only keep it if it looks like a type name (starts uppercase).
            if receiver_text and receiver_text[0].isupper():
                receiver_type = receiver_text
            else:
                return

        result.references.append(
            Reference(
                from_symbol=method_qname,
                target_name=receiver_type,
                kind="CALLS",
                file_path=file_path,
                line=self.line_start(node),
                evidence=f"{receiver_text}.{called_name}(...)",
            )
        )
