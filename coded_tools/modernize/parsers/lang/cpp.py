# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
C and C++ parser backed by the real tree-sitter C/C++ grammars.

One shared extraction implementation (`CppFamilyParser`) drives two leaf
classes, `CParser` and `CppParser`, selected by the ParserRegistry based on
file extension (and, for the ambiguous `.h`, a content sniff - see
registry.py). Plain C source simply never produces the C++-only node types
(class_specifier, namespace_definition, template_declaration), so the same
walk works for both without a language flag threaded through every method.

Extracts: #include graph, namespaces, classes/structs (including nested and
out-of-line `Class::method` definitions), templates, free and member
functions, calls (via `.`/`->` member access, resolved against local/param/
field types where possible), `new` instantiation, and embedded SQL
(including C's adjacent-string-literal concatenation, e.g.
`"SELECT * FROM " "ORDERS"`, which Java/C# never produce but Pro*C/ODBC code
uses constantly).
"""

from typing import Dict
from typing import List
from typing import Optional

from coded_tools.modernize.parsers import embedded_sql
from coded_tools.modernize.parsers.base import TreeSitterParser
from coded_tools.modernize.parsers.ir import ParseResult
from coded_tools.modernize.parsers.ir import Reference
from coded_tools.modernize.parsers.ir import Symbol

_TYPE_DECL_KINDS = {"class_specifier": "CLASS", "struct_specifier": "STRUCT"}
_POINTER_LIKE_DECLARATORS = ("pointer_declarator", "reference_declarator", "array_declarator")


def simple_type_name(type_text: str) -> str:
    """Strips template args, pointer/reference markers, and namespace qualification.

    "std::shared_ptr<Order>" -> "shared_ptr", "PaymentGateway*" -> "PaymentGateway"
    """
    t = type_text.strip()
    t = t.split("<", 1)[0]
    t = t.replace("*", "").replace("&", "").strip()
    if "::" in t:
        t = t.rsplit("::", 1)[-1]
    return t.strip()


class CppFamilyParser(TreeSitterParser):
    def __init__(self):
        super().__init__()
        self._class_field_types: Dict[str, Dict[str, str]] = {}

    def _extract(self, root, source_bytes: bytes, file_path: str, result: ParseResult) -> None:
        self._class_field_types = {}
        for inc in self._find_includes(root, source_bytes):
            result.references.append(
                Reference(
                    from_symbol=file_path,
                    target_name=inc,
                    kind="INCLUDES",
                    file_path=file_path,
                    line=1,
                    evidence=f"#include {inc}",
                )
            )
        self._walk_scope(root, source_bytes, file_path, result, namespace_stack=[])

    # ------------------------------------------------------------------ #
    # #include
    # ------------------------------------------------------------------ #

    def _find_includes(self, root, source_bytes: bytes) -> List[str]:
        includes = []
        for node in self.walk(root):
            if node.type == "preproc_include":
                path_node = node.child_by_field_name("path")
                if path_node is not None:
                    raw = self.text(path_node, source_bytes)
                    includes.append(raw.strip('<>"'))
        return includes

    # ------------------------------------------------------------------ #
    # Top-level / namespace-scope declarations
    # ------------------------------------------------------------------ #

    def _walk_scope(
        self, node, source_bytes: bytes, file_path: str, result: ParseResult, namespace_stack: List[str]
    ) -> None:
        for child in node.children:
            if child.type == "namespace_definition":
                name_node = child.child_by_field_name("name")
                ns_name = self.text(name_node, source_bytes) if name_node is not None else ""
                body = child.child_by_field_name("body")
                new_stack = namespace_stack + [ns_name] if ns_name else namespace_stack
                if body is not None:
                    self._walk_scope(body, source_bytes, file_path, result, new_stack)
            elif child.type == "linkage_specification":  # extern "C" { ... }
                body = child.child_by_field_name("body")
                if body is not None:
                    self._walk_scope(body, source_bytes, file_path, result, namespace_stack)
            elif child.type in _TYPE_DECL_KINDS:
                self._handle_type_decl(
                    child, _TYPE_DECL_KINDS[child.type], source_bytes, file_path, result, namespace_stack
                )
            elif child.type == "function_definition":
                self._handle_function_definition(child, source_bytes, file_path, result, namespace_stack)
            elif child.type == "template_declaration":
                inner = child.children[-1] if child.children else None
                if inner is not None and inner.type == "function_definition":
                    self._handle_function_definition(inner, source_bytes, file_path, result, namespace_stack)
                elif inner is not None and inner.type in _TYPE_DECL_KINDS:
                    self._handle_type_decl(
                        inner, _TYPE_DECL_KINDS[inner.type], source_bytes, file_path, result, namespace_stack
                    )

    # ------------------------------------------------------------------ #
    # class / struct declarations (incl. nested)
    # ------------------------------------------------------------------ #

    def _handle_type_decl(
        self,
        node,
        kind: str,
        source_bytes: bytes,
        file_path: str,
        result: ParseResult,
        namespace_stack: List[str],
    ) -> None:
        name_node = node.child_by_field_name("name")
        name = self.text(name_node, source_bytes) if name_node is not None else ""
        if not name:
            return
        qname = "::".join(namespace_stack + [name]) if namespace_stack else name

        base_types: List[str] = []
        base_clause = self._first_child_of_type(node, "base_class_clause")
        if base_clause is not None:
            for c in base_clause.children:
                if c.type in ("type_identifier", "qualified_identifier"):
                    base_name = self.text(c, source_bytes)
                    base_types.append(base_name)
                    result.references.append(
                        Reference(
                            from_symbol=qname,
                            target_name=simple_type_name(base_name),
                            kind="INHERITS",
                            file_path=file_path,
                            line=self.line_start(node),
                            evidence=f"{name} : {base_name}",
                        )
                    )

        result.symbols.append(
            Symbol(
                kind=kind,
                name=name,
                qualified_name=qname,
                language=self.language,
                file_path=file_path,
                line_start=self.line_start(node),
                line_end=self.line_end(node),
                parent="::".join(namespace_stack) if namespace_stack else None,
                base_types=base_types,
            )
        )

        body = node.child_by_field_name("body")
        if body is None:
            return  # forward declaration only

        field_types: Dict[str, str] = {}
        self._class_field_types[qname] = field_types

        for member in body.children:
            if member.type == "field_declaration":
                self._handle_field_or_method_decl(member, qname, source_bytes, file_path, result, field_types)
            elif member.type == "function_definition":
                self._handle_function_definition(
                    member, source_bytes, file_path, result, namespace_stack, owner_qname=qname
                )
            elif member.type == "template_declaration":
                inner = member.children[-1] if member.children else None
                if inner is not None and inner.type == "function_definition":
                    self._handle_function_definition(
                        inner, source_bytes, file_path, result, namespace_stack, owner_qname=qname
                    )
            elif member.type in _TYPE_DECL_KINDS:
                self._handle_type_decl(
                    member, _TYPE_DECL_KINDS[member.type], source_bytes, file_path, result, namespace_stack + [name]
                )

    @staticmethod
    def _first_child_of_type(node, type_name: str):
        for c in node.children:
            if c.type == type_name:
                return c
        return None

    @classmethod
    def _unwrap_declarator_name(cls, declarator):
        """Peels pointer/reference/array wrappers to find the leaf identifier."""
        node = declarator
        while node is not None and node.type in _POINTER_LIKE_DECLARATORS:
            node = node.child_by_field_name("declarator")
        if node is not None and node.type in ("field_identifier", "identifier"):
            return node
        return None

    def _handle_field_or_method_decl(
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
        declarator = node.child_by_field_name("declarator")

        if declarator is not None and declarator.type == "function_declarator":
            # Prototype (declaration without a body, e.g. constructor or pure
            # virtual method). Still worth recording so the interface is visible,
            # even though there's no body to scan for calls.
            inner_name = self._unwrap_declarator_name(declarator.child_by_field_name("declarator"))
            if inner_name is None:
                return
            m_name = self.text(inner_name, source_bytes)
            param_types, sig_parts = self._parse_parameters(declarator.child_by_field_name("parameters"), source_bytes)
            qname = f"{class_qname}::{m_name}({','.join(param_types.values())})"
            result.symbols.append(
                Symbol(
                    kind="METHOD",
                    name=m_name,
                    qualified_name=qname,
                    language=self.language,
                    file_path=file_path,
                    line_start=self.line_start(node),
                    line_end=self.line_end(node),
                    parent=class_qname,
                    signature=f"{m_name}({', '.join(sig_parts)})",
                    return_type=type_text,
                )
            )
            return

        name_node = self._unwrap_declarator_name(declarator)
        if name_node is None:
            return
        f_name = self.text(name_node, source_bytes)
        field_types[f_name] = simple_type_name(type_text)
        result.symbols.append(
            Symbol(
                kind="FIELD",
                name=f_name,
                qualified_name=f"{class_qname}::{f_name}",
                language=self.language,
                file_path=file_path,
                line_start=self.line_start(node),
                line_end=self.line_end(node),
                parent=class_qname,
                return_type=type_text,
            )
        )

    # ------------------------------------------------------------------ #
    # Functions: free, inline-in-class, and out-of-line `Class::method`
    # ------------------------------------------------------------------ #

    def _parse_parameters(self, params_node, source_bytes: bytes):
        param_types: Dict[str, str] = {}
        sig_parts: List[str] = []
        if params_node is None:
            return param_types, sig_parts
        for p in params_node.children:
            if p.type != "parameter_declaration":
                continue
            p_type_node = p.child_by_field_name("type")
            p_decl_node = p.child_by_field_name("declarator")
            p_type = self.text(p_type_node, source_bytes) if p_type_node is not None else ""
            p_name_node = self._unwrap_declarator_name(p_decl_node) if p_decl_node is not None else None
            p_name = self.text(p_name_node, source_bytes) if p_name_node is not None else ""
            if p_name:
                param_types[p_name] = simple_type_name(p_type)
            sig_parts.append(f"{p_type} {p_name}".strip())
        return param_types, sig_parts

    def _handle_function_definition(
        self,
        node,
        source_bytes: bytes,
        file_path: str,
        result: ParseResult,
        namespace_stack: List[str],
        owner_qname: Optional[str] = None,
    ) -> None:
        declarator = node.child_by_field_name("declarator")
        if declarator is None or declarator.type != "function_declarator":
            return
        inner = declarator.child_by_field_name("declarator")
        if inner is None:
            return

        if inner.type == "qualified_identifier":
            # Out-of-line definition: `ReturnType Class::method(...)`.
            scope_node = inner.child_by_field_name("scope")
            name_node = inner.child_by_field_name("name")
            class_simple = self.text(scope_node, source_bytes) if scope_node is not None else ""
            m_name = self.text(name_node, source_bytes) if name_node is not None else ""
            owner_qname = "::".join(namespace_stack + [class_simple]) if namespace_stack else class_simple
        else:
            m_name = self.text(inner, source_bytes)
            # owner_qname stays as passed in (inline-in-class) or None (free function)

        if not m_name:
            return

        param_types, sig_parts = self._parse_parameters(declarator.child_by_field_name("parameters"), source_bytes)
        return_type_node = node.child_by_field_name("type")
        return_type = self.text(return_type_node, source_bytes) if return_type_node is not None else ""

        parent = owner_qname if owner_qname else ("::".join(namespace_stack) if namespace_stack else None)
        qname_prefix = owner_qname if owner_qname else parent
        qname = (
            f"{qname_prefix}::{m_name}({','.join(param_types.values())})"
            if qname_prefix
            else f"{m_name}({','.join(param_types.values())})"
        )

        result.symbols.append(
            Symbol(
                kind="METHOD" if owner_qname else "FUNCTION",
                name=m_name,
                qualified_name=qname,
                language=self.language,
                file_path=file_path,
                line_start=self.line_start(node),
                line_end=self.line_end(node),
                parent=parent,
                signature=f"{m_name}({', '.join(sig_parts)})",
                return_type=return_type,
            )
        )

        body = node.child_by_field_name("body")
        if body is None:
            return
        # For an out-of-line method, recover the class's field types (if that
        # class appeared earlier in the same file - the common C++ convention)
        # so `member->method()` calls on implicit fields still resolve.
        field_types = self._class_field_types.get(owner_qname, {}) if owner_qname else {}
        self._walk_body(body, source_bytes, file_path, result, qname, field_types, param_types)

    # ------------------------------------------------------------------ #
    # Method bodies: locals, `new`, calls, embedded SQL
    # ------------------------------------------------------------------ #

    def _walk_body(
        self,
        body,
        source_bytes: bytes,
        file_path: str,
        result: ParseResult,
        owner_qname: str,
        field_types: Dict[str, str],
        param_types: Dict[str, str],
    ) -> None:
        local_types: Dict[str, str] = {}
        consumed: set = set()

        for node in self.walk(body):
            if id(node) in consumed:
                continue

            if node.type == "declaration":
                type_node = node.child_by_field_name("type")
                type_text = self.text(type_node, source_bytes) if type_node is not None else ""
                for decl in node.children:
                    if decl.type == "init_declarator":
                        name_node = self._unwrap_declarator_name(decl.child_by_field_name("declarator"))
                        if name_node is not None:
                            local_types[self.text(name_node, source_bytes)] = simple_type_name(type_text)

            elif node.type == "new_expression":
                type_node = node.child_by_field_name("type")
                type_text = self.text(type_node, source_bytes) if type_node is not None else ""
                if type_text:
                    result.references.append(
                        Reference(
                            from_symbol=owner_qname,
                            target_name=simple_type_name(type_text),
                            kind="INSTANTIATES",
                            file_path=file_path,
                            line=self.line_start(node),
                            evidence=self.text(node, source_bytes)[:120],
                        )
                    )

            elif node.type == "call_expression":
                self._handle_call(
                    node, source_bytes, file_path, result, owner_qname, field_types, param_types, local_types
                )

            elif node.type in ("string_literal", "binary_expression", "concatenated_string"):
                sql_text = embedded_sql.join_string_concat(node, source_bytes)
                if sql_text and embedded_sql.looks_like_sql(sql_text):
                    result.sql_accesses.append(
                        embedded_sql.build_sql_access(
                            sql_text, file_path, self.line_start(node), owner_symbol=owner_qname
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
        owner_qname: str,
        field_types: Dict[str, str],
        param_types: Dict[str, str],
        local_types: Dict[str, str],
    ) -> None:
        function_node = node.child_by_field_name("function")
        if function_node is None:
            return

        if function_node.type == "field_expression":
            receiver_node = function_node.child_by_field_name("argument")
            receiver_text = self.text(receiver_node, source_bytes) if receiver_node is not None else ""
        elif function_node.type == "qualified_identifier":
            # Static/namespaced call: Type::method(...)
            scope_node = function_node.child_by_field_name("scope")
            receiver_text = self.text(scope_node, source_bytes) if scope_node is not None else ""
        else:
            # Bare call: helper() - self-call or free function, not a useful edge here.
            return

        if not receiver_text:
            return

        receiver_type = (
            local_types.get(receiver_text) or param_types.get(receiver_text) or field_types.get(receiver_text)
        )
        if receiver_type is None:
            if receiver_text[0].isupper():
                receiver_type = receiver_text  # looks like a type name (static call)
            else:
                return

        result.references.append(
            Reference(
                from_symbol=owner_qname,
                target_name=receiver_type,
                kind="CALLS",
                file_path=file_path,
                line=self.line_start(node),
                evidence=self.text(node, source_bytes)[:120],
            )
        )


class CParser(CppFamilyParser):
    language = "c"
    extensions = [".c"]
    ts_language_name = "c"


class CppParser(CppFamilyParser):
    language = "cpp"
    extensions = [".cpp", ".cc", ".cxx", ".hpp", ".hh"]
    ts_language_name = "cpp"
