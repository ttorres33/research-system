"""Whole-word keyword matching over a paper's title and abstract.

Syntax, the same the arXiv search API documents: quoted phrases, bare terms, AND, OR,
ANDNOT (NOT is accepted as a synonym), parentheses, and an implicit AND between adjacent
terms. Operators are upper-case; lower-case "and" is an ordinary word.

Matching is deliberately stricter than the arXiv API. The API stems words, so
`organizations` matched "organized" and `"AI assistant" AND productivity` matched
"AI-assisted" + "production"; that stemming produced most of the off-topic arXiv papers
in past digests. Here a term matches a whole word, case-insensitively, and a phrase
matches adjacent words. Hyphens split on both sides, so "AI-assisted" and "AI assisted"
are the same two words. There is no stemming and no wildcard.

Field prefixes (cat:, ti:, abs:, ...) and `*` are not supported; they raise
UnsupportedSyntax so the keyword is reported instead of silently matching nothing.
"""

import re

TOKEN_RE = re.compile(r'"([^"]*)"|(\()|(\))|\b(ANDNOT|AND|OR|NOT)\b|([^\s()"]+)')
WORD_RE = re.compile(r"[a-z0-9]+")
FIELD_PREFIX_RE = re.compile(r"^(ti|abs|au|co|jr|cat|rn|id|all):", re.IGNORECASE)


class QueryError(ValueError):
    """The keyword cannot be parsed (unbalanced parentheses, dangling operator, empty)."""


class UnsupportedSyntax(QueryError):
    """The keyword uses arXiv API syntax this matcher does not implement."""


def words(text):
    """Lower-case runs of letters and digits; punctuation and hyphens split."""
    return WORD_RE.findall(text.lower())


def _joined(text):
    return " " + " ".join(words(text)) + " "


def _check_supported(raw):
    if FIELD_PREFIX_RE.match(raw):
        raise UnsupportedSyntax(f"field prefix in {raw!r}: search fields are not supported; use the topic's categories setting")
    if "*" in raw:
        raise UnsupportedSyntax(f"wildcard in {raw!r}: write the full word; there is no stemming or wildcard matching")


class _Leaf:
    def __init__(self, raw, is_phrase):
        _check_supported(raw)
        self.raw = raw
        self.is_phrase = is_phrase
        self.tokens = words(raw)
        if not self.tokens:
            raise QueryError(f"{raw!r} contains no letters or digits")
        self.needle = " " + " ".join(self.tokens) + " "

    def evaluate(self, joined, failed):
        hit = self.needle in joined
        if not hit:
            failed.append(self.raw)
        return hit

    def __str__(self):
        return f'"{self.raw}"' if self.is_phrase else self.raw


class _Node:
    def __init__(self, op, left, right):
        self.op, self.left, self.right = op, left, right

    def evaluate(self, joined, failed):
        # Both sides are always evaluated so `failed` lists every term that did not match.
        if self.op == "AND":
            return self.left.evaluate(joined, failed) & self.right.evaluate(joined, failed)
        if self.op == "OR":
            return self.left.evaluate(joined, failed) | self.right.evaluate(joined, failed)
        return self.left.evaluate(joined, failed) and not self.right.evaluate(joined, [])

    def __str__(self):
        return f"({self.left} {self.op} {self.right})"


class Query:
    """A parsed keyword. Build with parse()."""

    def __init__(self, source, tree):
        self.source = source
        self._tree = tree

    def matches_text(self, text):
        return self._tree.evaluate(_joined(text), [])

    def matches(self, paper):
        return self.matches_text(_paper_text(paper))

    def explain(self, paper):
        """The terms that did not match, in query order (empty when the paper matches)."""
        failed = []
        self._tree.evaluate(_joined(_paper_text(paper)), failed)
        return failed

    def __str__(self):
        return str(self._tree)


def _paper_text(paper):
    if isinstance(paper, dict):
        return f"{paper.get('title', '')} . {paper.get('abstract', '')}"
    return f"{getattr(paper, 'title', '')} . {getattr(paper, 'abstract', '')}"


def _tokenize(query):
    tokens = []
    for match in TOKEN_RE.finditer(query):
        phrase, lparen, rparen, op, term = match.groups()
        if phrase is not None:
            tokens.append(("PHRASE", phrase))
        elif lparen:
            tokens.append(("LP", None))
        elif rparen:
            tokens.append(("RP", None))
        elif op:
            tokens.append(("OP", "ANDNOT" if op == "NOT" else op))
        else:
            tokens.append(("TERM", term))
    if query.count('"') % 2:
        raise QueryError(f"unbalanced quotes in {query!r}")
    return tokens


def parse(query):
    """Parse one keyword line into a Query. Raises QueryError or UnsupportedSyntax."""
    source = query.strip()
    tokens = _tokenize(source)
    if not tokens:
        raise QueryError("empty keyword")
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else (None, None)

    def parse_or():
        nonlocal pos
        node = parse_and()
        while peek() == ("OP", "OR"):
            pos += 1
            node = _Node("OR", node, parse_and())
        return node

    def parse_and():
        nonlocal pos
        node = parse_unary()
        while True:
            kind, value = peek()
            if (kind, value) == ("OP", "AND"):
                pos += 1
                node = _Node("AND", node, parse_unary())
            elif (kind, value) == ("OP", "ANDNOT"):
                pos += 1
                node = _Node("ANDNOT", node, parse_unary())
            elif kind in ("TERM", "PHRASE", "LP"):
                node = _Node("AND", node, parse_unary())
            else:
                return node

    def parse_unary():
        nonlocal pos
        kind, value = peek()
        if kind == "LP":
            pos += 1
            node = parse_or()
            if peek()[0] != "RP":
                raise QueryError(f"missing closing parenthesis in {source!r}")
            pos += 1
            return node
        if kind in ("TERM", "PHRASE"):
            pos += 1
            return _Leaf(value, kind == "PHRASE")
        if kind == "OP":
            raise QueryError(f"operator {value} has nothing before or after it in {source!r}")
        if kind == "RP":
            raise QueryError(f"unexpected closing parenthesis in {source!r}")
        raise QueryError(f"unexpected end of keyword in {source!r}")

    tree = parse_or()
    if pos != len(tokens):
        raise QueryError(f"unexpected {tokens[pos][1] or tokens[pos][0]!r} in {source!r}")
    return Query(source, tree)
