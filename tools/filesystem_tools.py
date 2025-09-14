import os
import re
import shutil
import hashlib

# -----------------
# Helper functions
# -----------------

def _index_text(text: str):
    """
    Build an index for the given text.
    Returns a dict with:
      - lines: list of { line (1-based), start, end, length, eol }
      - total_length: len(text)
      - line_count
      - newline: 'LF' | 'CRLF' | 'CR' | 'mixed' | 'none'
    Notes:
      - start/end refer to indices in the full string for the content segment (excluding EOL).
      - column is 1-based and applies to content only (not including EOL).
    """
    lines = []
    pos = 0
    eols_seen = set()
    for m in re.finditer(r"\r\n|\r|\n", text):
        eol = m.group(0)
        content_start = pos
        content_end = m.start()
        lines.append({
            'line': len(lines) + 1,
            'start': content_start,
            'end': content_end,
            'length': content_end - content_start,
            'eol': eol,
        })
        eols_seen.add(eol)
        pos = m.end()
    # Last line (may have no EOL)
    if pos <= len(text):
        content_start = pos
        content_end = len(text)
        # If text is empty, we still create one logical empty line
        if content_start == content_end and len(lines) == 0:
            lines.append({
                'line': 1,
                'start': 0,
                'end': 0,
                'length': 0,
                'eol': '',
            })
        elif content_start != content_end:
            lines.append({
                'line': len(lines) + 1,
                'start': content_start,
                'end': content_end,
                'length': content_end - content_start,
                'eol': '',
            })
        # else: text ended exactly on an EOL, no trailing empty line

    if not eols_seen:
        newline_style = 'none'
    elif len(eols_seen) == 1:
        e = next(iter(eols_seen))
        newline_style = 'CRLF' if e == '\r\n' else ('LF' if e == '\n' else 'CR')
    else:
        newline_style = 'mixed'

    return {
        'lines': lines,
        'total_length': len(text),
        'line_count': len(lines),
        'newline': newline_style,
    }


def _offset_from_line_col(index, line: int, column: int):
    """
    Convert 1-based (line, column) to 0-based absolute offset in the full text.
    Column counts characters within the line content only (excluding EOL).
    Raises ValueError if out of bounds.
    """
    if line < 1 or line > max(1, index['line_count']):
        raise ValueError('Line out of range')
    # In empty file case we ensured one logical empty line.
    lines = index['lines']
    # Handle empty file case
    if len(lines) == 0 and line == 1:
        if column != 1:
            raise ValueError('Column out of range')
        return 0
    # Normal case
    try:
        line_info = lines[line - 1]
    except IndexError:
        raise ValueError('Line out of range')
    if column < 1 or column > line_info['length'] + 1:
        raise ValueError('Column out of range')
    return line_info['start'] + (column - 1)


def _line_col_from_offset(index, offset: int):
    """
    Convert a 0-based absolute offset to 1-based (line, column).
    Column counts characters within the line content only (excluding EOL).
    """
    if offset < 0 or offset > index['total_length']:
        raise ValueError('Offset out of range')
    lines = index['lines']
    if not lines:
        return 1, 1
    lo, hi = 0, len(lines) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        s, e = lines[mid]['start'], lines[mid]['end']
        if offset < s:
            hi = mid - 1
        elif offset > e:
            lo = mid + 1
        else:
            # inside this line (or at end)
            return mid + 1, (offset - s) + 1
    # If beyond last content end, it's at EOF after last line
    last = lines[-1]
    return last['line'], last['length'] + 1


def _slice_content_by_lines(content: str, index, start_line: int, end_line: int) -> str:
    """
    Return the content from start_line to end_line inclusive, preserving original EOLs.
    """
    if start_line < 1 or end_line < start_line:
        raise ValueError('Invalid line range')
    lines = index['lines']
    if not lines:
        return ''
    end_line = min(end_line, len(lines))
    parts = []
    for i in range(start_line - 1, end_line):
        ln = lines[i]
        parts.append(content[ln['start']:ln['end']] + ln['eol'])
    return ''.join(parts)


def _hash_sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _normalize_newlines(text: str, newline_style: str, fallback: str = 'LF') -> str:
    """
    Normalize text newlines to match newline_style ('LF'|'CRLF'|'CR'|'mixed'|'none').
    If 'mixed' or 'none', use fallback ('LF' by default).
    """
    if newline_style in ('mixed', 'none'):
        target = '\n' if fallback == 'LF' else ('\r\n' if fallback == 'CRLF' else '\r')
    else:
        target = '\n' if newline_style == 'LF' else ('\r\n' if newline_style == 'CRLF' else '\r')
    # Replace any of \r\n, \r, or \n with target
    return re.sub(r"\r\n|\r|\n", target, text)


class ReadFolderContentTool:
    schema = {
        "type": "function",
        "name": "read_folder_content",
        "description": (
            "List all files and folders in a specified folder. "
            "Provide the folder path relative to the project root (where main.py is called). "
            "This tool returns both files and directories. "
            "Use this tool to explore available resources, scripts, data files, and subfolders in a given folder. "
            "Do not use for reading file contents; use only to get names of items in the folder. "
            "Safety: Never use this tool to access system or hidden folders. Only use for project-relevant paths."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string", "description": "The folder path relative to the project root (where main.py is called)."}
            },
            "required": ["relative_path"],
            "additionalProperties": False,
        },
    }

    def __init__(self, root_path):
        self.root_path = root_path

    def run(self, relative_path):
        folder_path = os.path.join(self.root_path, relative_path)
        if not os.path.isdir(folder_path):
            return {"status": "error", "message": "Folder not found."}
        items = os.listdir(folder_path)
        return {"status": "success", "items": items}


class ReadFileContentTool:
    schema = {
        "type": "function",
        "name": "read_file_content",
        "description": (
            "Read and return file content. Optionally return an index or only a line range to save tokens. "
            "Safety: Never use this tool to access system or hidden files. Only project-relevant paths."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string", "description": "Path relative to project root."},
                "with_index": {"type": "boolean", "description": "[Legacy] If true, return full index.", "default": False},
                "content_mode": {"type": "string", "enum": ["full", "range", "none"], "default": "full", "description": "full = return whole file; range = only start..end lines; none = no content."},
                "start_line": {"type": "integer", "minimum": 1, "description": "First line when content_mode='range'. Inclusive."},
                "end_line": {"type": "integer", "minimum": 1, "description": "Last line when content_mode='range'. Inclusive."},
                "index_mode": {"type": "string", "enum": ["none", "full", "range"], "default": "none", "description": "Controls index verbosity. 'with_index'=True implies 'full' if this is 'none'."},
                "with_hash": {"type": "boolean", "default": False, "description": "Include SHA-256 of current file content."},
                "max_chars": {"type": "integer", "minimum": 1, "description": "If set, clip returned content to this many characters."}
            },
            "required": ["relative_path", "with_index", "content_mode", "index_mode", "with_hash", "max_chars", "start_line", "end_line"],
            "additionalProperties": False,
        },
    }

    def __init__(self, root_path):
        self.root_path = root_path

    def run(self, relative_path, with_index=False, content_mode='full', start_line=None, end_line=None, index_mode='none', with_hash=False, max_chars=None):
        file_path = os.path.join(self.root_path, relative_path)
        if not os.path.isfile(file_path):
            return {"status": "error", "message": "File not found."}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            idx = _index_text(content)
            result = {"status": "success"}

            # Content handling
            if content_mode == 'none':
                pass
            elif content_mode == 'range':
                if start_line is None or end_line is None:
                    return {"status": "error", "message": "start_line and end_line required for content_mode='range'."}
                try:
                    slice_text = _slice_content_by_lines(content, idx, start_line, end_line)
                except Exception as e:
                    return {"status": "error", "message": str(e)}
                if max_chars is not None and len(slice_text) > max_chars:
                    slice_text = slice_text[:max_chars]
                result["content"] = slice_text
            else:  # full
                out = content
                if max_chars is not None and len(out) > max_chars:
                    out = out[:max_chars]
                result["content"] = out

            # Index handling
            if index_mode == 'full' or (with_index and index_mode == 'none'):
                result["index"] = idx
            elif index_mode == 'range':
                if start_line is None or end_line is None:
                    return {"status": "error", "message": "start_line and end_line required for index_mode='range'."}
                lines = idx['lines']
                sl = max(1, start_line)
                el = min(end_line, len(lines))
                result["index"] = {
                    'line_count': idx['line_count'],
                    'newline': idx['newline'],
                    'range': {
                        'start_line': sl,
                        'end_line': el,
                        'lines': lines[sl-1:el],
                    }
                }

            if with_hash:
                result['sha256'] = _hash_sha256(content)

            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}


class WriteFileContentTool:
    schema = {
        "type": "function",
        "name": "write_file_content",
        "description": (
            "Write string content to a specified file. Creates the file if it does not exist. "
            "Provide the file path relative to the project root (where main.py is called) and the content as a string. "
            "Use this tool to save or update project files, scripts, or data files. "
            "Safety: Never use this tool to access system or hidden files. Only use for project-relevant paths."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string", "description": "The file path relative to the project root (where main.py is called)."},
                "content": {"type": "string", "description": "The string content to write to the file."},
            },
            "required": ["relative_path", "content"],
            "additionalProperties": False,
        },
    }

    def __init__(self, root_path, permission_required=True):
        self.root_path = root_path
        self.permission_required = permission_required

    def run(self, relative_path, content):
        file_path = os.path.join(self.root_path, relative_path)
        abs_file_path = os.path.abspath(file_path)
        abs_root_path = os.path.abspath(self.root_path)
        if not abs_file_path.startswith(abs_root_path):
            return {"status": "error", "message": "File path is outside the project scope."}
        folder = os.path.dirname(abs_file_path)
        if self.permission_required:
            permission = input(f"Write to file '{relative_path}'? This may create or overwrite files. Proceed? (y/n): ")
            if permission.lower() != 'y':
                return {"status": "error", "message": "File write cancelled by user."}
        if not os.path.exists(folder):
            os.makedirs(folder)
        try:
            with open(abs_file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"status": "success", "message": f"File '{relative_path}' written successfully."}
        except Exception as e:
            return {"status": "error", "message": str(e)}


class CreateFolderTool:
    schema = {
        "type": "function",
        "name": "create_folder",
        "description": (
            "Create a folder at the specified path relative to the project root (where main.py is called). "
            "If the folder already exists, do nothing. "
            "Use this tool to organize project files and resources. "
            "Safety: Never use this tool to access system or hidden folders. Only use for project-relevant paths."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string", "description": "The folder path relative to the project root (where main.py is called)."}
            },
            "required": ["relative_path"],
            "additionalProperties": False,
        },
    }

    def __init__(self, root_path, permission_required=True):
        self.root_path = root_path
        self.permission_required = permission_required

    def run(self, relative_path):
        folder_path = os.path.join(self.root_path, relative_path)
        abs_folder_path = os.path.abspath(folder_path)
        abs_root_path = os.path.abspath(self.root_path)
        if not abs_folder_path.startswith(abs_root_path):
            return {"status": "error", "message": "Folder path is outside the project scope."}
        if self.permission_required:
            permission = input(f"Create folder '{relative_path}'? Proceed? (y/n): ")
            if permission.lower() != 'y':
                return {"status": "error", "message": "Folder creation cancelled by user."}
        try:
            os.makedirs(abs_folder_path, exist_ok=True)
            return {"status": "success", "message": f"Folder '{relative_path}' created successfully."}
        except Exception as e:
            return {"status": "error", "message": str(e)}


class RemovePathsTool:
    schema = {
        "type": "function",
        "name": "remove_paths",
        "description": (
            "Remove files and/or folders at the specified relative paths. "
            "Provide a list of paths relative to the project root (where main.py is called). "
            "Deletes files and directories recursively when needed. "
            "Safety: Never use this tool to access system or hidden paths. Only use for project-relevant paths."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file or folder paths relative to the project root to remove.",
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    }

    def __init__(self, root_path, permission_required=True):
        self.root_path = root_path
        self.permission_required = permission_required

    def run(self, paths):
        if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
            return {"status": "error", "message": "'paths' must be a list of strings."}
        abs_root = os.path.abspath(self.root_path)
        to_delete = []  # (rel, abs, kind)
        not_found = []
        out_of_scope = []
        invalid = []

        # Collect targets
        for rel in paths:
            if not rel or rel.strip() in {".", "/", "\\"}:
                invalid.append(rel)
                continue
            abs_path = os.path.abspath(os.path.join(self.root_path, rel))
            if not abs_path.startswith(abs_root):
                out_of_scope.append(rel)
                continue
            if abs_path == abs_root:
                invalid.append(rel)
                continue
            if os.path.isfile(abs_path) or os.path.islink(abs_path):
                to_delete.append((rel, abs_path, 'file'))
            elif os.path.isdir(abs_path):
                to_delete.append((rel, abs_path, 'dir'))
            else:
                not_found.append(rel)

        if not to_delete and not_found and not out_of_scope and not invalid:
            return {"status": "error", "message": "No deletable targets found."}

        if self.permission_required and to_delete:
            preview = "\n".join([f"- {rel}" for rel, _, _ in to_delete])
            prompt = (
                "You are about to remove the following paths:\n"
                f"{preview}\nProceed? (y/n): "
            )
            permission = input(prompt)
            if permission.lower() != 'y':
                return {"status": "error", "message": "Removal cancelled by user."}

        removed = []
        errors = []
        for rel, abs_path, kind in to_delete:
            try:
                if kind == 'file':
                    os.remove(abs_path)
                else:
                    shutil.rmtree(abs_path)
                removed.append(rel)
            except Exception as e:
                errors.append({"path": rel, "error": str(e)})

        status = "success" if not errors else "error"
        msg_parts = []
        if removed:
            msg_parts.append(f"Removed {len(removed)} item(s).")
        if not_found:
            msg_parts.append(f"Not found: {len(not_found)}")
        if out_of_scope:
            msg_parts.append(f"Out of scope: {len(out_of_scope)}")
        if invalid:
            msg_parts.append(f"Invalid: {len(invalid)}")
        if errors:
            msg_parts.append(f"Errors: {len(errors)}")
        message = " ".join(msg_parts) or "No action taken."

        return {
            "status": status,
            "message": message,
            "removed": removed,
            "not_found": not_found,
            "out_of_scope": out_of_scope,
            "invalid": invalid,
            "errors": errors,
        }


class InsertTextInFileTool:
    schema = {
        "type": "function",
        "name": "insert_text_in_file",
        "description": (
            "Insert text into a file at a specific (line, column) position. "
            "Line and column are 1-based and column counts characters within the line content only. "
            "Safety: Only operates within the project root. Prompts for confirmation when enabled."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string", "description": "Path to the file relative to project root."},
                "line": {"type": "integer", "minimum": 1, "description": "1-based line number."},
                "column": {"type": "integer", "minimum": 1, "description": "1-based column within the line (content only)."},
                "text": {"type": "string", "description": "Text to insert at the position."},
                "expected_sha256": {"type": "string", "description": "If provided, ensure file hash matches before writing."},
                "normalize_newlines": {"type": "boolean", "default": True, "description": "Normalize inserted text newlines to file's style."},
                "newline_fallback": {"type": "string", "enum": ["LF", "CRLF", "CR"], "default": "LF", "description": "Fallback when file has mixed/none newlines."}
            },
            "required": ["relative_path", "line", "column", "text", "expected_sha256", "normalize_newlines", "newline_fallback"],
            "additionalProperties": False,
        },
    }

    def __init__(self, root_path, permission_required=True):
        self.root_path = root_path
        self.permission_required = permission_required

    def run(self, relative_path, line, column, text, expected_sha256=None, normalize_newlines=True, newline_fallback='LF'):
        abs_root = os.path.abspath(self.root_path)
        file_path = os.path.join(self.root_path, relative_path)
        abs_file = os.path.abspath(file_path)
        if not abs_file.startswith(abs_root):
            return {"status": "error", "message": "File path is outside the project scope."}
        if not os.path.isfile(abs_file):
            return {"status": "error", "message": "File not found."}
        try:
            with open(abs_file, 'r', encoding='utf-8') as f:
                content = f.read()
            if expected_sha256 is not None:
                actual = _hash_sha256(content)
                if actual != expected_sha256:
                    return {"status": "error", "message": "File hash mismatch; aborting insert.", "actual_sha256": actual}
            idx = _index_text(content)
            try:
                offset = _offset_from_line_col(idx, line, column)
            except ValueError as ve:
                return {"status": "error", "message": str(ve)}

            ins_text = text
            if normalize_newlines:
                ins_text = _normalize_newlines(ins_text, idx['newline'], newline_fallback)

            new_content = content[:offset] + ins_text + content[offset:]

            if self.permission_required:
                preview = ins_text if len(ins_text) <= 80 else ins_text[:77] + '...'
                permission = input(
                    f"Insert into '{relative_path}' at L{line}:C{column}?\n"
                    f"Text preview: {preview}\nProceed? (y/n): "
                )
                if permission.lower() != 'y':
                    return {"status": "error", "message": "Insertion cancelled by user."}

            with open(abs_file, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return {
                "status": "success",
                "message": f"Inserted {len(ins_text)} char(s) at L{line}:C{column}.",
                "new_length": len(new_content),
                "sha256": _hash_sha256(new_content),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


class ReplaceTextInFileTool:
    schema = {
        "type": "function",
        "name": "replace_text_in_file",
        "description": (
            "Replace text in a file between two (line, column) positions. "
            "Start is inclusive, end is exclusive. 1-based line/column, column counts characters within line content only."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string", "description": "Path to the file relative to project root."},
                "start_line": {"type": "integer", "minimum": 1, "description": "Start line (inclusive)."},
                "start_column": {"type": "integer", "minimum": 1, "description": "Start column (inclusive)."},
                "end_line": {"type": "integer", "minimum": 1, "description": "End line (exclusive end position)."},
                "end_column": {"type": "integer", "minimum": 1, "description": "End column (exclusive)."},
                "text": {"type": "string", "description": "Replacement text."},
                "expected_sha256": {"type": "string", "description": "If provided, ensure file hash matches before writing."},
                "normalize_newlines": {"type": "boolean", "default": True, "description": "Normalize replacement text newlines to file's style."},
                "newline_fallback": {"type": "string", "enum": ["LF", "CRLF", "CR"], "default": "LF", "description": "Fallback when file has mixed/none newlines."}
            },
            "required": ["relative_path", "start_line", "start_column", "end_line", "end_column", "text", "expected_sha256", "normalize_newlines", "newline_fallback"],
            "additionalProperties": False,
        },
    }

    def __init__(self, root_path, permission_required=True):
        self.root_path = root_path
        self.permission_required = permission_required

    def run(self, relative_path, start_line, start_column, end_line, end_column, text, expected_sha256=None, normalize_newlines=True, newline_fallback='LF'):
        abs_root = os.path.abspath(self.root_path)
        file_path = os.path.join(self.root_path, relative_path)
        abs_file = os.path.abspath(file_path)
        if not abs_file.startswith(abs_root):
            return {"status": "error", "message": "File path is outside the project scope."}
        if not os.path.isfile(abs_file):
            return {"status": "error", "message": "File not found."}
        try:
            with open(abs_file, 'r', encoding='utf-8') as f:
                content = f.read()
            if expected_sha256 is not None:
                actual = _hash_sha256(content)
                if actual != expected_sha256:
                    return {"status": "error", "message": "File hash mismatch; aborting replace.", "actual_sha256": actual}
            idx = _index_text(content)
            try:
                start_off = _offset_from_line_col(idx, start_line, start_column)
                end_off = _offset_from_line_col(idx, end_line, end_column)
            except ValueError as ve:
                return {"status": "error", "message": str(ve)}
            if end_off < start_off:
                return {"status": "error", "message": "End position precedes start position."}

            rep_text = text
            if normalize_newlines:
                rep_text = _normalize_newlines(rep_text, idx['newline'], newline_fallback)

            new_content = content[:start_off] + rep_text + content[end_off:]

            if self.permission_required:
                preview = rep_text if len(rep_text) <= 80 else rep_text[:77] + '...'
                permission = input(
                    f"Replace in '{relative_path}' from L{start_line}:C{start_column} to L{end_line}:C{end_column}?\n"
                    f"Replacement preview: {preview}\nProceed? (y/n): "
                )
                if permission.lower() != 'y':
                    return {"status": "error", "message": "Replacement cancelled by user."}

            with open(abs_file, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return {
                "status": "success",
                "message": (
                    f"Replaced range L{start_line}:C{start_column}-L{end_line}:C{end_column} "
                    f"with {len(rep_text)} char(s)."
                ),
                "new_length": len(new_content),
                "sha256": _hash_sha256(new_content),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


class SearchInFileTool:
    schema = {
        "type": "function",
        "name": "search_in_file",
        "description": (
            "Search for a string or regex in a file and return match positions with optional context."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string", "description": "Path to the file relative to project root."},
                "query": {"type": "string", "description": "Literal string or regex pattern to search for."},
                "regex": {"type": "boolean", "default": False, "description": "Interpret query as a regex if true."},
                "case_sensitive": {"type": "boolean", "default": False, "description": "Case-sensitive search if true."},
                "max_results": {"type": "integer", "minimum": 1, "default": 20, "description": "Maximum number of matches to return."},
                "before_lines": {"type": "integer", "minimum": 0, "default": 0, "description": "Number of context lines before the match."},
                "after_lines": {"type": "integer", "minimum": 0, "default": 0, "description": "Number of context lines after the match."}
            },
            "required": ["relative_path", "query", "regex", "case_sensitive", "max_results", "before_lines", "after_lines"],
            "additionalProperties": False,
        },
    }

    def __init__(self, root_path):
        self.root_path = root_path

    def run(self, relative_path, query, regex=False, case_sensitive=False, max_results=20, before_lines=0, after_lines=0):
        file_path = os.path.join(self.root_path, relative_path)
        if not os.path.isfile(file_path):
            return {"status": "error", "message": "File not found."}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            idx = _index_text(content)
            flags = 0 if case_sensitive else re.IGNORECASE
            if regex:
                pattern = re.compile(query, flags)
            else:
                pattern = re.compile(re.escape(query), flags)

            results = []
            for m in pattern.finditer(content):
                if len(results) >= max_results:
                    break
                start_off, end_off = m.start(), m.end()
                try:
                    sl, sc = _line_col_from_offset(idx, start_off)
                    el, ec = _line_col_from_offset(idx, end_off)
                except ValueError:
                    continue
                # Context
                ctx_start = max(1, sl - before_lines)
                ctx_end = min(idx['line_count'], el + after_lines)
                context_text = _slice_content_by_lines(content, idx, ctx_start, ctx_end) if (before_lines or after_lines) else ''
                results.append({
                    'start_line': sl,
                    'start_column': sc,
                    'end_line': el,
                    'end_column': ec,
                    'match': m.group(0),
                    'context_start_line': ctx_start if context_text else None,
                    'context_end_line': ctx_end if context_text else None,
                    'context': context_text if context_text else None,
                })

            return {"status": "success", "count": len(results), "results": results, "line_count": idx['line_count']}
        except Exception as e:
            return {"status": "error", "message": str(e)}
