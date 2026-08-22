# error_parser.py
import re


class ErrorParser:
    PATTERNS = {
        "gcc": re.compile(
            r"^(.+?):(\d+):(?:(\d+):)?\s*(error|warning|note):\s*(.*)$", re.MULTILINE
        ),
        "clang": re.compile(
            r"^(.+?):(\d+):(?:(\d+):)?\s*(error|warning|note):\s*(.*)$", re.MULTILINE
        ),
        "javac": re.compile(r"^(.+?):(\d+):\s*(error|warning):\s*(.*)$", re.MULTILINE),
        "python": re.compile(r'^\s*File "(.+?)", line (\d+), in .+?$', re.MULTILINE),
        "node": re.compile(r"^\s*at\s+(.+?):(\d+):(\d+)$", re.MULTILINE),
        "rustc": re.compile(r"^(.*):(\d+):(\d+):\s*(error|warning):\s*(.*)$", re.MULTILINE),
        "cargo": re.compile(r"^(error|warning):\s*(.*)$", re.MULTILINE),
        "go": re.compile(r"^(.*):(\d+):\s*(.*)$", re.MULTILINE),
        "msvc": re.compile(r"^(.*)\((\d+)\):\s*(error|warning)\s*(.*)$", re.MULTILINE),
        "maven": re.compile(r"^\[ERROR\]\s*(.*)$", re.MULTILINE),
        "gradle": re.compile(r"^\s*FAILURE: Build failed with an exception\.\s*$", re.MULTILINE),
    }

    @staticmethod
    def parse(tool_name, stderr):
        if not stderr:
            return []
        key = (tool_name or "").lower()
        # choose best pattern
        pattern = None
        for k in ErrorParser.PATTERNS:
            if k in key:
                pattern = ErrorParser.PATTERNS[k]
                break
        if not pattern:
            # fallback: split lines and return raw lines
            return [{"raw": line} for line in stderr.splitlines() if line.strip()]

        errors = []
        for m in pattern.finditer(stderr):
            g = m.groups()
            if key in ("gcc", "clang", "rustc"):
                errors.append(
                    {
                        "file": g[0],
                        "line": int(g[1]),
                        "column": int(g[2]) if g[2] else None,
                        "level": g[3],
                        "message": g[4],
                    }
                )
            elif key == "javac":
                errors.append({"file": g[0], "line": int(g[1]), "level": g[2], "message": g[3]})
            elif key == "go":
                errors.append({"file": g[0], "line": int(g[1]), "level": "error", "message": g[2]})
            elif key == "msvc":
                errors.append({"file": g[0], "line": int(g[1]), "level": g[2], "message": g[3]})
            else:
                # generic
                msg = g[0] if len(g) == 1 else " ".join([str(x) for x in g if x])
                errors.append({"raw": msg})
        return errors

    @staticmethod
    def format_error(err):
        if "raw" in err:
            return err["raw"]
        parts = []
        if "file" in err:
            p = err["file"]
            if "line" in err and err["line"]:
                p += f":{err['line']}"
                if "column" in err and err["column"]:
                    p += f":{err['column']}"
            parts.append(p)
        if "level" in err:
            parts.append(f"[{err['level'].upper()}]")
        if "message" in err:
            parts.append(err["message"])
        return " ".join(parts)
