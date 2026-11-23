import ast
import io
import json
import tokenize
from typing import Any


class CodeAnalysisError(Exception):
    """Raised when a Python file cannot be safely analysed or updated."""


def _get_docstring(node: ast.AST) -> str | None:
    try:
        return ast.get_docstring(node, clean=False)
    except (TypeError, ValueError):
        return None


def _node_source(source: str, node: ast.AST, limit: int = 1200) -> str:
    segment = ast.get_source_segment(source, node) or ""
    if len(segment) > limit:
        return segment[:limit] + "\n# ... excerpt truncated ..."
    return segment


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    try:
        arguments = ast.unparse(node.args)
        returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        return f"{prefix}{node.name}({arguments}){returns}"
    except Exception:
        return node.name


def analyze_python_source(source: str) -> dict[str, Any]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        location = f"line {exc.lineno}" if exc.lineno else "an unknown line"
        raise CodeAnalysisError(f"Python syntax error at {location}: {exc.msg}") from exc

    targets: list[dict[str, Any]] = []
    used_ids: dict[str, int] = {}
    function_count = 0
    class_count = 0

    def add_target(node: ast.AST, kind: str, name: str, qualified_name: str) -> None:
        nonlocal function_count, class_count
        base_id = qualified_name or "module"
        occurrence = used_ids.get(base_id, 0) + 1
        used_ids[base_id] = occurrence
        target_id = base_id if occurrence == 1 else f"{base_id}#{occurrence}"

        if kind in {"function", "async_function"}:
            function_count += 1
        elif kind == "class":
            class_count += 1

        item: dict[str, Any] = {
            "id": target_id,
            "kind": kind,
            "name": name,
            "qualified_name": qualified_name,
            "existing_docstring": _get_docstring(node),
            "source_excerpt": _node_source(source, node),
            "line": getattr(node, "lineno", 1),
        }

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            item["signature"] = _signature(node)
            item["returns"] = ast.unparse(node.returns) if node.returns else None

        targets.append(item)

    add_target(tree, "module", "module", "module")

    def walk_body(body: list[ast.stmt], parent_name: str) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                qualified_name = f"{parent_name}.{node.name}" if parent_name else node.name
                add_target(node, "class", node.name, qualified_name)
                walk_body(node.body, qualified_name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified_name = f"{parent_name}.{node.name}" if parent_name else node.name
                kind = "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
                add_target(node, kind, node.name, qualified_name)
                walk_body(node.body, qualified_name)

    walk_body(tree.body, "")

    return {
        "tree": tree,
        "targets": targets,
        "line_count": len(source.splitlines()),
        "function_count": function_count,
        "class_count": class_count,
    }


def _find_suite_colon(source: str, node: ast.AST) -> int:
    """Return the character offset of a def/class suite colon on its header line."""
    node_line = getattr(node, "lineno", None)
    if node_line is None:
        raise CodeAnalysisError("Could not locate a function or class definition in the source file.")

    depth = 0
    header_started = False
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for token in tokens:
            if token.start[0] < node_line:
                continue
            if token.start[0] > node_line:
                break
            if token.type == tokenize.NAME and token.string in {"def", "class"}:
                header_started = True
                continue
            if not header_started:
                continue
            if token.type == tokenize.OP:
                if token.string in "([{":
                    depth += 1
                elif token.string in ")]}" and depth > 0:
                    depth -= 1
                elif token.string == ":" and depth == 0:
                    line_start = sum(len(line) for line in source.splitlines(keepends=True)[: node_line - 1])
                    return line_start + token.end[1]
    except tokenize.TokenError as exc:
        raise CodeAnalysisError(f"Could not safely inspect a one-line function: {exc}") from exc

    raise CodeAnalysisError("Could not locate the function or class definition's colon.")


def _make_string_literal(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def insert_docstrings(
    source: str,
    targets: list[dict[str, Any]],
    generated_docstrings: dict[str, str],
) -> tuple[str, int]:
    """Insert generated docstrings without asking the LLM to rewrite program code."""
    analysis = analyze_python_source(source)
    tree = analysis["tree"]

    node_by_id: dict[str, ast.AST] = {}
    used_ids: dict[str, int] = {}

    def register(node: ast.AST, qualified_name: str) -> None:
        base_id = qualified_name or "module"
        occurrence = used_ids.get(base_id, 0) + 1
        used_ids[base_id] = occurrence
        target_id = base_id if occurrence == 1 else f"{base_id}#{occurrence}"
        node_by_id[target_id] = node

    register(tree, "module")

    def walk_body(body: list[ast.stmt], parent_name: str) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                name = f"{parent_name}.{node.name}" if parent_name else node.name
                register(node, name)
                walk_body(node.body, name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f"{parent_name}.{node.name}" if parent_name else node.name
                register(node, name)
                walk_body(node.body, name)

    walk_body(tree.body, "")

    line_offsets: list[int] = []
    running = 0
    lines = source.splitlines(keepends=True)
    for line in lines:
        line_offsets.append(running)
        running += len(line)

    edits: list[tuple[int, str]] = []
    for target in targets:
        target_id = target["id"]
        docstring = generated_docstrings.get(target_id)
        node = node_by_id.get(target_id)

        if not isinstance(docstring, str) or not docstring.strip() or node is None:
            continue
        if _get_docstring(node) is not None:
            continue

        literal = _make_string_literal(docstring.strip())

        if isinstance(node, ast.Module):
            if node.body:
                first_line = node.body[0].lineno
                offset = line_offsets[first_line - 1]
                newline = "\r\n" if "\r\n" in source else "\n"
                edits.append((offset, f"{literal}{newline}"))
            elif source:
                edits.append((len(source), f"\n{literal}\n"))
            else:
                edits.append((0, f"{literal}\n"))
            continue

        if not getattr(node, "body", None):
            continue

        first_statement = node.body[0]
        node_line = getattr(node, "lineno", None)
        if first_statement.lineno == node_line:
            colon_offset = _find_suite_colon(source, node)
            edits.append((colon_offset, f" {literal};"))
        else:
            statement_line = first_statement.lineno
            offset = line_offsets[statement_line - 1]
            line = lines[statement_line - 1]
            indent = line[: len(line) - len(line.lstrip(" \t"))]
            newline = "\r\n" if "\r\n" in source else "\n"
            edits.append((offset, f"{indent}{literal}{newline}"))

    updated = source
    for offset, insertion in sorted(edits, key=lambda item: item[0], reverse=True):
        updated = updated[:offset] + insertion + updated[offset:]

    try:
        ast.parse(updated)
    except SyntaxError as exc:
        raise CodeAnalysisError(
            "The generated docstrings could not be inserted safely. The original code has not been changed. "
            f"Validation failed at line {exc.lineno}: {exc.msg}"
        ) from exc

    return updated, len(edits)
