"""5-Phase MiniLang Compiler Engine: Lexical, Syntax/AST, Semantic/Symbol Table, TAC & Constant Folding, Python Target & Run."""
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TokenItem:
    type: str
    value: str
    line: int
    column: int


@dataclass
class DiagnosticItem:
    stage: str
    line: int
    message: str


TOKEN_RULES = [
    ("COMMENT", r"#.*"),
    ("NEWLINE", r"\r?\n"),
    ("SKIP", r"[ \t]+"),
    ("STRING", r'"(?:\\.|[^"\\])*"'),
    ("SSTRING", r"'(?:\\.|[^'\\])*'"),
    ("FLOAT", r"\b\d+\.\d+\b"),
    ("INT", r"\b\d+\b"),
    ("KEYWORD", r"\b(?:LET|INT|FLOAT|STR|BOOL|DISPLAY|IF|ELSE|TRUE|FALSE)\b"),
    ("IDENT", r"\b[A-Za-z_][A-Za-z0-9_]*\b"),
    ("OP", r"==|!=|<=|>=|[+\-*/=<>]"),
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("LBRACE", r"\{"),
    ("RBRACE", r"\}"),
    ("SEMI", r";"),
    ("COLON", r":"),
    ("COMMA", r","),
    ("MISMATCH", r"."),
]


def lex_source(source: str) -> Tuple[List[TokenItem], List[DiagnosticItem]]:
    tokens: List[TokenItem] = []
    errors: List[DiagnosticItem] = []
    pattern = "|".join(f"(?P<{name}>{expr})" for name, expr in TOKEN_RULES)
    line_no = 1
    line_start = 0
    for m in re.finditer(pattern, source):
        kind = m.lastgroup
        val = m.group()
        col = m.start() - line_start + 1
        if kind == "NEWLINE":
            line_no += 1
            line_start = m.end()
        elif kind in ("SKIP", "COMMENT"):
            continue
        elif kind == "MISMATCH":
            errors.append(DiagnosticItem("Lexical Analysis", line_no, f"Unexpected character '{val}' at column {col}."))
        else:
            tok_type = kind
            if tok_type == "SSTRING":
                tok_type = "STRING"
            if kind == "KEYWORD":
                if val in ("INT", "FLOAT", "STR", "BOOL"):
                    tok_type = "TYPE"
                elif val in ("TRUE", "FALSE"):
                    tok_type = "BOOL"
                else:
                    tok_type = val
            tokens.append(TokenItem(type=tok_type, value=val, line=line_no, column=col))
    return tokens, errors


class RecursiveParser:
    def __init__(self, tokens: List[TokenItem]):
        self.tokens = tokens
        self.pos = 0
        self.errors: List[DiagnosticItem] = []
        self.uid = 0

    def next_id(self) -> str:
        self.uid += 1
        return f"n_{self.uid}"

    def peek(self, offset: int = 0) -> Optional[TokenItem]:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else None

    def match(self, expected_type: Optional[str] = None, expected_val: Optional[str] = None) -> Optional[TokenItem]:
        tok = self.peek()
        if tok is None:
            ln = self.tokens[-1].line if self.tokens else 1
            self.errors.append(DiagnosticItem("Syntax Analysis", ln, f"Unexpected end of input; expected {expected_val or expected_type or 'token'}." ))
            return None
        if expected_type and tok.type != expected_type:
            self.errors.append(DiagnosticItem("Syntax Analysis", tok.line, f"Expected {expected_val or expected_type}, found '{tok.value}' ({tok.type})."))
            return None
        if expected_val and tok.value != expected_val:
            self.errors.append(DiagnosticItem("Syntax Analysis", tok.line, f"Expected '{expected_val}', found '{tok.value}'."))
            return None
        self.pos += 1
        return tok

    def parse(self) -> Dict[str, Any]:
        stmts = []
        while self.peek() is not None:
            st = self.parse_stmt()
            if st:
                stmts.append(st)
            else:
                bad = self.match()
                bad_line = bad.line if bad else -1
                if bad and bad.type == "SEMI":
                    continue
                while self.peek() and self.peek().type != "SEMI" and self.peek().line == bad_line:
                    self.pos += 1
                if self.peek() and self.peek().type == "SEMI":
                    self.pos += 1
        return {"id": self.next_id(), "kind": "Program", "label": "Program", "line": 1, "children": stmts}

    def parse_stmt(self) -> Optional[Dict[str, Any]]:
        tok = self.peek()
        if not tok:
            return None
        if tok.type == "LET":
            self.match("LET")
            ident = self.match("IDENT")
            if not ident:
                return None
            decl_type = None
            if self.peek() and self.peek().type == "COLON":
                self.match("COLON")
                t_tok = self.match("TYPE")
                decl_type = t_tok.value if t_tok else None
            if not self.match("OP", "="):
                return None
            rhs = self.parse_expr()
            if not rhs:
                return None
            if self.peek() and self.peek().type == "SEMI":
                self.match("SEMI")
            return {
                "id": self.next_id(),
                "kind": "VarDecl",
                "label": f"LET {ident.value}" + (f": {decl_type}" if decl_type else ""),
                "name": ident.value,
                "varType": decl_type,
                "line": tok.line,
                "children": [rhs],
            }
        if tok.type == "DISPLAY":
            self.match("DISPLAY")
            expr = self.parse_expr()
            if not expr:
                return None
            if self.peek() and self.peek().type == "SEMI":
                self.match("SEMI")
            return {"id": self.next_id(), "kind": "DisplayStmt", "label": "DISPLAY", "line": tok.line, "children": [expr]}
        if tok.type == "IF":
            self.match("IF")
            cond = self.parse_expr()
            if not cond:
                return None
            then_b = self.parse_block()
            children = [cond] + then_b
            if self.peek() and self.peek().type == "ELSE":
                self.match("ELSE")
                else_b = self.parse_block()
                children.append({"id": self.next_id(), "kind": "ElseBlock", "label": "ELSE", "line": tok.line, "children": else_b})
            return {"id": self.next_id(), "kind": "IfStmt", "label": "IF", "line": tok.line, "children": children}
        if tok.type == "IDENT" and self.peek(1) and self.peek(1).value == "=":
            name_tok = self.match("IDENT")
            self.match("OP", "=")
            expr = self.parse_expr()
            if not expr:
                return None
            if self.peek() and self.peek().type == "SEMI":
                self.match("SEMI")
            return {"id": self.next_id(), "kind": "AssignStmt", "label": f"{name_tok.value} =", "name": name_tok.value, "line": tok.line, "children": [expr]}
        self.errors.append(DiagnosticItem("Syntax Analysis", tok.line, f"Syntax error near '{tok.value}'."))
        return None

    def parse_block(self) -> List[Dict[str, Any]]:
        items = []
        if not self.match("LBRACE"):
            return items
        while self.peek() and self.peek().type != "RBRACE":
            st = self.parse_stmt()
            if st:
                items.append(st)
            else:
                self.pos += 1
        self.match("RBRACE")
        return items

    def parse_expr(self) -> Optional[Dict[str, Any]]:
        return self.parse_cmp()

    def parse_cmp(self) -> Optional[Dict[str, Any]]:
        node = self.parse_add()
        while node and self.peek() and self.peek().type == "OP" and self.peek().value in ("==", "!=", "<", ">", "<=", ">="):
            op_tok = self.match("OP")
            right = self.parse_add()
            if not right:
                return None
            node = {"id": self.next_id(), "kind": "BinaryOp", "label": op_tok.value, "op": op_tok.value, "line": op_tok.line, "children": [node, right]}
        return node

    def parse_add(self) -> Optional[Dict[str, Any]]:
        node = self.parse_mul()
        while node and self.peek() and self.peek().type == "OP" and self.peek().value in ("+", "-"):
            op_tok = self.match("OP")
            right = self.parse_mul()
            if not right:
                return None
            node = {"id": self.next_id(), "kind": "BinaryOp", "label": op_tok.value, "op": op_tok.value, "line": op_tok.line, "children": [node, right]}
        return node

    def parse_mul(self) -> Optional[Dict[str, Any]]:
        node = self.parse_primary()
        while node and self.peek() and self.peek().type == "OP" and self.peek().value in ("*", "/"):
            op_tok = self.match("OP")
            right = self.parse_primary()
            if not right:
                return None
            node = {"id": self.next_id(), "kind": "BinaryOp", "label": op_tok.value, "op": op_tok.value, "line": op_tok.line, "children": [node, right]}
        return node

    def parse_primary(self) -> Optional[Dict[str, Any]]:
        tok = self.peek()
        if not tok:
            return None
        if tok.type == "INT":
            self.match("INT")
            return {"id": self.next_id(), "kind": "Literal", "label": f"INT({tok.value})", "value": int(tok.value), "dataType": "INT", "line": tok.line, "children": []}
        if tok.type == "FLOAT":
            self.match("FLOAT")
            return {"id": self.next_id(), "kind": "Literal", "label": f"FLOAT({tok.value})", "value": float(tok.value), "dataType": "FLOAT", "line": tok.line, "children": []}
        if tok.type == "STRING":
            self.match("STRING")
            return {"id": self.next_id(), "kind": "Literal", "label": f"STR({tok.value})", "value": tok.value[1:-1], "dataType": "STR", "line": tok.line, "children": []}
        if tok.type == "BOOL":
            self.match("BOOL")
            return {"id": self.next_id(), "kind": "Literal", "label": f"BOOL({tok.value})", "value": tok.value == "TRUE", "dataType": "BOOL", "line": tok.line, "children": []}
        if tok.type == "IDENT":
            self.match("IDENT")
            return {"id": self.next_id(), "kind": "Identifier", "label": f"ID({tok.value})", "name": tok.value, "line": tok.line, "children": []}
        if tok.type == "LPAREN":
            self.match("LPAREN")
            inner = self.parse_expr()
            self.match("RPAREN")
            return inner
        self.errors.append(DiagnosticItem("Syntax Analysis", tok.line, f"Unexpected token '{tok.value}' in expression."))
        return None


def check_expr_type(node: Dict[str, Any], sym: Dict[str, Dict[str, Any]], errs: List[DiagnosticItem]) -> str:
    kind = node.get("kind")
    if kind == "Literal":
        return node.get("dataType", "INT")
    if kind == "Identifier":
        name = node.get("name")
        if name not in sym:
            errs.append(DiagnosticItem("Semantic Analysis", node.get("line", 1), f"Undeclared variable '{name}' used before declaration."))
            return "UNKNOWN"
        sym[name]["used"] = True
        return sym[name]["type"]
    if kind == "BinaryOp":
        ch = node.get("children", [])
        if len(ch) < 2:
            return "UNKNOWN"
        lt = check_expr_type(ch[0], sym, errs)
        rt = check_expr_type(ch[1], sym, errs)
        op = node.get("op")
        if "UNKNOWN" in (lt, rt):
            return "UNKNOWN"
        if op in ("==", "!=", "<", ">", "<=", ">="):
            if lt != rt and not ({lt, rt} == {"INT", "FLOAT"}):
                errs.append(DiagnosticItem("Semantic Analysis", node.get("line", 1), f"Cannot compare {lt} and {rt} with '{op}'."))
            return "BOOL"
        if op == "+":
            if lt == "STR" and rt == "STR":
                return "STR"
            if "STR" in (lt, rt):
                errs.append(DiagnosticItem("Semantic Analysis", node.get("line", 1), f"Type error on '+' between {lt} and {rt}."))
                return "UNKNOWN"
            return "FLOAT" if "FLOAT" in (lt, rt) else "INT"
        if op in ("-", "*", "/"):
            if "STR" in (lt, rt) or "BOOL" in (lt, rt):
                errs.append(DiagnosticItem("Semantic Analysis", node.get("line", 1), f"Operator '{op}' invalid for {lt} and {rt}."))
                return "UNKNOWN"
            if op == "/":
                return "FLOAT"
            return "FLOAT" if "FLOAT" in (lt, rt) else "INT"
    return "UNKNOWN"


def semantic_pass(ast: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[DiagnosticItem]]:
    sym: Dict[str, Dict[str, Any]] = {}
    errs: List[DiagnosticItem] = []

    def walk(stmts: List[Dict[str, Any]]):
        for st in stmts:
            kind = st.get("kind")
            ln = st.get("line", 1)
            ch = st.get("children", [])
            if kind == "VarDecl":
                name = st.get("name")
                et = check_expr_type(ch[0], sym, errs) if ch else "UNKNOWN"
                dt = st.get("varType") or (et if et != "UNKNOWN" else "INT")
                if dt != et and et != "UNKNOWN" and not (dt == "FLOAT" and et == "INT"):
                    errs.append(DiagnosticItem("Semantic Analysis", ln, f"Type mismatch: cannot assign {et} to {dt} variable '{name}'."))
                sym[name] = {"name": name, "type": dt, "scope": "global", "declaredLine": ln, "initialized": et != "UNKNOWN", "used": False}
            elif kind == "AssignStmt":
                name = st.get("name")
                et = check_expr_type(ch[0], sym, errs) if ch else "UNKNOWN"
                if name not in sym:
                    errs.append(DiagnosticItem("Semantic Analysis", ln, f"Assignment to undeclared variable '{name}'."))
                else:
                    tt = sym[name]["type"]
                    if tt != et and et != "UNKNOWN" and not (tt == "FLOAT" and et == "INT"):
                        errs.append(DiagnosticItem("Semantic Analysis", ln, f"Type mismatch assigning {et} to {tt} variable '{name}'."))
                    sym[name]["initialized"] = True
            elif kind == "DisplayStmt":
                if ch:
                    check_expr_type(ch[0], sym, errs)
            elif kind == "IfStmt":
                if ch:
                    check_expr_type(ch[0], sym, errs)
                    walk([c for c in ch[1:] if c.get("kind") != "ElseBlock"])
                    for c in ch[1:]:
                        if c.get("kind") == "ElseBlock":
                            walk(c.get("children", []))

    walk(ast.get("children", []))
    return list(sym.values()), errs


def constant_fold(node: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    folded = 0
    new_kids = []
    for c in node.get("children", []):
        fc, cnt = constant_fold(c)
        folded += cnt
        new_kids.append(fc)
    copy_node = dict(node)
    copy_node["children"] = new_kids
    if copy_node.get("kind") == "BinaryOp" and len(new_kids) == 2:
        l, r = new_kids[0], new_kids[1]
        if l.get("kind") == "Literal" and r.get("kind") == "Literal":
            lv, rv = l.get("value"), r.get("value")
            op = copy_node.get("op")
            try:
                ops = {
                    "+": lambda a, b: a + b,
                    "-": lambda a, b: a - b,
                    "*": lambda a, b: a * b,
                    "/": lambda a, b: None if b == 0 else a / b,
                    "==": lambda a, b: a == b,
                    "!=": lambda a, b: a != b,
                    "<": lambda a, b: a < b,
                    ">": lambda a, b: a > b,
                    "<=": lambda a, b: a <= b,
                    ">=": lambda a, b: a >= b,
                }
                if op in ops:
                    res = ops[op](lv, rv)
                    if res is not None:
                        if isinstance(res, bool):
                            dt, lbl = "BOOL", f"BOOL({'TRUE' if res else 'FALSE'})"
                        elif isinstance(res, float):
                            res = round(res, 6)
                            dt, lbl = "FLOAT", f"FLOAT({res})"
                        elif isinstance(res, str):
                            dt, lbl = "STR", f'STR("{res}")'
                        else:
                            dt, lbl = "INT", f"INT({res})"
                        return {"id": copy_node["id"], "kind": "Literal", "label": lbl, "value": res, "dataType": dt, "line": copy_node.get("line", 1), "children": []}, folded + 1
            except Exception:
                pass
    return copy_node, folded


class ThreeAddressCode:
    def __init__(self):
        self.t_idx = 0
        self.l_idx = 0
        self.lines: List[str] = []

    def new_t(self) -> str:
        self.t_idx += 1
        return f"t{self.t_idx}"

    def new_l(self) -> str:
        self.l_idx += 1
        return f"L{self.l_idx}"

    def expr(self, node: Dict[str, Any]) -> str:
        k = node.get("kind")
        if k == "Literal":
            v, dt = node.get("value"), node.get("dataType")
            if dt == "STR":
                return f'"{v}"'
            if dt == "BOOL":
                return "True" if v else "False"
            return str(v)
        if k == "Identifier":
            return node.get("name", "_")
        if k == "BinaryOp":
            ch = node.get("children", [])
            la = self.expr(ch[0])
            ra = self.expr(ch[1])
            tmp = self.new_t()
            self.lines.append(f"{tmp} = {la} {node.get('op')} {ra}")
            return tmp
        return "0"

    def stmts(self, items: List[Dict[str, Any]]):
        for st in items:
            k = st.get("kind")
            ch = st.get("children", [])
            if k in ("VarDecl", "AssignStmt"):
                rhs = self.expr(ch[0]) if ch else "0"
                self.lines.append(f"{st.get('name')} = {rhs}")
            elif k == "DisplayStmt":
                val = self.expr(ch[0]) if ch else ""
                self.lines.append(f"PRINT {val}")
            elif k == "IfStmt":
                c_addr = self.expr(ch[0])
                l_else, l_end = self.new_l(), self.new_l()
                self.lines.append(f"IF_FALSE {c_addr} GOTO {l_else}")
                self.stmts([c for c in ch[1:] if c.get("kind") != "ElseBlock"])
                self.lines.append(f"GOTO {l_end}")
                self.lines.append(f"{l_else}:")
                for c in ch[1:]:
                    if c.get("kind") == "ElseBlock":
                        self.stmts(c.get("children", []))
                self.lines.append(f"{l_end}:")


def generate_python_target(tac_lines: List[str]) -> str:
    out = [
        "# Generated Python Target from MiniLang TAC",
        "def run_program():",
        "    logs = []",
    ]
    for raw in tac_lines:
        s = raw.strip()
        if not s:
            continue
        if s.endswith(":"):
            out.append(f"    # {s}")
        elif s.startswith("IF_FALSE "):
            parts = s.split(" GOTO ")
            cond = parts[0].replace("IF_FALSE ", "", 1)
            out.append(f"    if not ({cond}):")
            out.append(f"        # jump {parts[1]}")
            out.append("        pass")
        elif s.startswith("GOTO "):
            out.append(f"    # {s}")
        elif s.startswith("PRINT "):
            expr_str = s.replace("PRINT ", "", 1)
            out.append(f"    logs.append(str({expr_str}))")
        else:
            out.append(f"    {s}")
    out.append("    print('\\n'.join(logs))")
    out.append("")
    out.append("if __name__ == '__main__':")
    out.append("    run_program()")
    return "\n".join(out)


def run_target(py_code: str) -> Tuple[str, str, float]:
    t0 = time.perf_counter()
    fd, path = tempfile.mkstemp(suffix=".py")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(py_code)
        proc = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=3.0)
        ms = round((time.perf_counter() - t0) * 1000, 2)
        return proc.stdout, proc.stderr, ms
    except subprocess.TimeoutExpired:
        ms = round((time.perf_counter() - t0) * 1000, 2)
        return "", "Execution timed out (3.0s).", ms
    finally:
        if os.path.exists(path):
            os.remove(path)


def compile_program(source: str, optimize: bool = True) -> Dict[str, Any]:
    tokens, lex_errs = lex_source(source)
    parser = RecursiveParser(tokens)
    ast = parser.parse()
    syn_errs = parser.errors
    sym_table, sem_errs = semantic_pass(ast)

    raw_tac = ThreeAddressCode()
    raw_tac.stmts(ast.get("children", []))

    if optimize:
        opt_ast, folded = constant_fold(ast)
    else:
        opt_ast, folded = ast, 0

    opt_tac = ThreeAddressCode()
    opt_tac.stmts(opt_ast.get("children", []))

    py_target = generate_python_target(opt_tac.lines)
    all_errs = [asdict(e) for e in (lex_errs + syn_errs + sem_errs)]
    stdout, stderr, ms = ("", "", 0.0)
    if not all_errs:
        stdout, stderr, ms = run_target(py_target)

    return {
        "success": len(all_errs) == 0 and not stderr,
        "tokens": [asdict(t) for t in tokens],
        "ast": ast,
        "optimizedAst": opt_ast,
        "foldedConstants": folded,
        "symbolTable": sym_table,
        "tacBefore": raw_tac.lines,
        "tacAfter": opt_tac.lines,
        "targetCode": py_target,
        "execution": {"stdout": stdout, "stderr": stderr, "durationMs": ms},
        "diagnostics": all_errs,
    }
