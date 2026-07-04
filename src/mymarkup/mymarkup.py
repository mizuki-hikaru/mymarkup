import re
import inspect
from html import escape
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse


SAFE_SCHEMES = {"http", "https", "mailto"}


@dataclass
class Metadata:
    title: str
    description: str


class Context:
    def index(self):
        raise Exception("index undefined")

    def breadcrumbs(self):
        raise Exception("breadcrumbs undefined")


class Token:
    def render(self, context: Context):
        raise Exception("render undefined")


class BlockToken(Token):
    subclasses = []

    def __init_subclass__(cls):
        BlockToken.subclasses.append(cls)

    @classmethod
    def parse(_, lines: list[str], i: int) -> tuple["BlockToken", int]:
        for cls in BlockToken.subclasses:
            token, i = cls.parse(lines, i)
            if token:
                return token, i
        raise Exception(f"No block token matched line {i}: {lines[i]!r}")


class InlineToken(Token):
    subclasses = []

    def __init_subclass__(cls):
        InlineToken.subclasses.append(cls)

    @classmethod
    def parse(_, line: str, i: int) -> tuple["InlineToken", int]:
        for cls in InlineToken.subclasses:
            token, i = cls.parse(line, i)
            if token:
                return token, i
        raise Exception(f"No inline token matched character {i}: {line[i:]!r}")


@dataclass
class Document(Token):
    children: list[BlockToken]

    @classmethod
    def parse(cls, lines: list[str]) -> "Document":
        children = []
        i = 0
        while i < len(lines):
            token, i = BlockToken.parse(lines, i)
            children.append(token)
        return Document(children)

    def render(self, context: Context):
        return "".join([x.render(context) for x in self.children])

    def metadata(self):
        title = None
        description = None
        context = Context()
        for child in self.children:
            if isinstance(child, Heading) and child.level == 1 and not title:
                title = child.text.render(context)
            if isinstance(child, Paragraph) and not description:
                description = " ".join([x.render(context) for x in child.paragraph_lines])
            if title and description:
                break
        if not title:
            raise Exception("No title found")
        if not description:
            raise Exception("No description found")
        return Metadata(title, description)


@dataclass
class Span(Token):
    children: list[InlineToken]

    @classmethod
    def parse(cls, line: str) -> "Span":
        children = []
        i = 0
        while i < len(line):
            token, i = InlineToken.parse(line, i)
            children.append(token)
        return Span(children)

    def render(self, context: Context):
        return "".join([x.render(context) for x in self.children])


@dataclass
class Directive(BlockToken):
    directive: str

    @classmethod
    def opening_re(cls) -> re.Pattern[str]:
        return re.compile(r"^:([a-zA-Z_][a-zA-Z0-9_]*):$")

    @classmethod
    def parse(cls, lines: list[str], i: int) -> tuple[Optional["Directive"], int]:
        match = Directive.opening_re().match(lines[i].strip())
        if not match:
            return None, i
        return Directive(match.group(1)), i + 1

    def render(self, context: Context):
        func = context.__class__.__dict__.get(self.directive)
        if not inspect.isfunction(func):
            raise Exception(f"Could not find function in context: {self.directive}")
        return getattr(context, self.directive)()


class BlankLine(BlockToken):
    @classmethod
    def parse(cls, lines: list[str], i: int) -> tuple[Optional["BlankLine"], int]:
        return (BlankLine(), i + 1) if lines[i].strip() == "" else (None, i)

    def render(self, context: Context):
        return ""


@dataclass
class CodeBlock(BlockToken):
    language: Optional[str]
    code_lines: list[str]

    @classmethod
    def opening_re(cls) -> re.Pattern[str]:
        return re.compile(r"^(`{3,})([A-Za-z0-9_-]+)?$")

    @classmethod
    def closing_re(cls, fence) -> re.Pattern[str]:
        return re.compile(rf"^{fence}$")

    @classmethod
    def parse(cls, lines: list[str], i: int) -> tuple[Optional["CodeBlock"], int]:
        match = CodeBlock.opening_re().match(lines[i])
        if not match:
            return None, i
        fence = match.group(1)
        language = match.group(2)
        code_lines = []
        closing_re = CodeBlock.closing_re(fence)
        j = i + 1
        while j < len(lines):
            if closing_re.match(lines[j]):
                return CodeBlock(language, code_lines), j + 1
            code_lines.append(lines[j])
            j += 1
        return None, i

    def render(self, context: Context):
        code = "\n".join([escape(x, quote=True) for x in self.code_lines])
        if self.language:
            language_class = f' class="language-{escape(self.language, quote=True)}"'
        else:
            language_class = ""
        return f'<pre><code{language_class}>{code}</code></pre>'


class HorizontalRule(BlockToken):
    @classmethod
    def opening_re(cls) -> re.Pattern[str]:
        return re.compile(r"^\s*---+\s*$")

    @classmethod
    def parse(cls, lines: list[str], i: int) -> tuple[Optional["HorizontalRule"], int]:
        return (HorizontalRule(), i + 1) if HorizontalRule.opening_re().match(lines[i]) else (None, i)

    def render(self, context: Context):
        return "<hr>"


@dataclass
class Heading(BlockToken):
    text: Span
    level: int
    center: bool

    @classmethod
    def opening_re(cls) -> re.Pattern[str]:
        return re.compile(r"^(#{1,6})\s+(.+?)\s*( #{,6})?$")

    @classmethod
    def parse(cls, lines: list[str], i: int) -> tuple[Optional["Heading"], int]:
        match = Heading.opening_re().match(lines[i])
        if not match:
            return None, i
        text = Span.parse(match.group(2).strip())
        level = len(match.group(1))
        center = ((match.group(3) or "").strip() == match.group(1))
        return Heading(text, level, center), i + 1

    def render(self, context: Context):
        cls = ' class="center"' if self.center else ""
        return f"<h{self.level}{cls}>{self.text.render(context)}</h{self.level}>"


@dataclass
class List(BlockToken):
    ordered: bool
    items: list[Document]

    @classmethod
    def opening_re(cls) -> re.Pattern[str]:
        return re.compile(r"^( [-#] )(.*)$")

    @classmethod
    def parse(cls, lines: list[str], i: int) -> tuple[Optional["List"], int]:
        match = List.opening_re().match(lines[i])
        if not match:
            return None, i
        marker = match.group(1)
        inner_lines = [match.group(2)]
        items = []
        j = i + 1
        while j < len(lines):
            if lines[j].strip() == "" or lines[j][:3] == "   ":
                inner_lines.append(lines[j][3:])
                j += 1
            elif lines[j][:3] == marker:
                items.append(Document.parse(inner_lines))
                inner_lines = [lines[j][3:]]
                j += 1
            else:
                break
        items.append(Document.parse(inner_lines))
        return List("#" in marker, items), j

    def render(self, context: Context):
        tag = "ol" if self.ordered else "ul"
        items = "".join([f"<li>{item.render(context)}</li>" for item in self.items])
        return f"<{tag}>{items}</{tag}>"


@dataclass
class BlockQuote(BlockToken):
    document: Document

    @classmethod
    def parse(cls, lines: list[str], i: int) -> tuple[Optional["BlockQuote"], int]:
        if not lines[i].startswith("> "):
            return None, i
        j = i + 1
        while j < len(lines) and lines[j].startswith("> "):
            j += 1
        return BlockQuote(Document.parse([line[2:] for line in lines[i:j]])), j

    def render(self, context: Context):
        return f"<blockquote>{self.document.render(context)}</blockquote>"


@dataclass
class Paragraph(BlockToken):
    paragraph_lines: list[Span]
    align: str

    @classmethod
    def is_other_block_token(_, lines: list[str], i: int) -> bool:
        for cls in BlockToken.subclasses:
            if cls != Paragraph:
                token, i = cls.parse(lines, i)
                if token:
                    return True
        return False

    @classmethod
    def parse(cls, lines: list[str], i: int) -> tuple[Optional["Paragraph"], int]:
        alignments = ("center", "left", "right")
        align = ""
        paragraph_lines = []
        j = i
        while j < len(lines):
            if Paragraph.is_other_block_token(lines, j):
                break
            line = lines[j].strip()
            if i == j:
                for alignment in alignments:
                    marker = f"{alignment}:"
                    if line.startswith(marker):
                        align = alignment
                        line = line[len(marker):].strip()
                        break
            paragraph_lines.append(Span.parse(line))
            j += 1
        return (Paragraph(paragraph_lines, align), j) if paragraph_lines else (None, i)

    def render(self, context: Context):
        text = " ".join([x.render(context) for x in self.paragraph_lines])
        align_class = (f' class="{self.align}"' if self.align else "")
        return f'<p{align_class}>{text}</p>'


@dataclass
class Bold(InlineToken):
    text: Span

    @classmethod
    def opening_re(cls) -> re.Pattern[str]:
        return re.compile(r"^\*[A-Za-z0-9]$")

    @classmethod
    def closing_re(cls) -> re.Pattern[str]:
        return re.compile(r"^[A-Za-z0-9]\*$")

    @classmethod
    def parse(cls, line: str, i: int) -> tuple[Optional["Bold"], int]:
        if not Bold.opening_re().match(line[i:i+2]):
            return None, i
        closing_re = Bold.closing_re()
        j = i + 1
        while j + 1 < len(line):
            if closing_re.match(line[j:j+2]):
                return Bold(Span.parse(line[i+1:j+1])), j + 2
            j += 1
        return None, i

    def render(self, context: Context):
        return f"<strong>{self.text.render(context)}</strong>"


@dataclass
class InlineCode(InlineToken):
    code: str

    @classmethod
    def is_fence(cls, line: str, start: int, fence_length: int) -> bool:
        end = start + fence_length
        return line[start:end] == "`" * fence_length

    @classmethod
    def parse(cls, line: str, i: int) -> tuple[Optional["InlineCode"], int]:
        fence_length = 0
        while InlineCode.is_fence(line, i, fence_length + 1):
            fence_length += 1
        if fence_length == 0:
            return None, i
        j = i + fence_length
        while j + fence_length <= len(line):
            if InlineCode.is_fence(line, j, fence_length):
                start = i + fence_length
                return InlineCode(line[start:j]), j + fence_length
            j += 1
        return None, i

    def render(self, context: Context):
        return f"<code>{escape(self.code, quote=True)}</code>"


@dataclass
class Link(InlineToken):
    text: Span
    href: str
    button: bool

    @classmethod
    def opening_re(cls) -> re.Pattern[str]:
        return re.compile(r"^([\[{][^}\]]+[}\]])\(([^)]+)\)")

    @classmethod
    def parse(cls, line: str, i: int) -> tuple[Optional["Link"], int]:
        match = Link.opening_re().match(line[i:])
        if not match:
            return None, i
        text = match.group(1)
        if (text[0] == '[') != (text[-1] == ']'):
            return None, i
        button = (text[0] == '{')
        text = Span.parse(text[1:-1].strip())
        href = match.group(2)
        end = i + len(match.group(0))
        return Link(text, href, button), end

    def render(self, context: Context):
        if not is_safe_href(self.href):
            raise Exception(f"Unsafe href: {self.href}")
        button_class = (' class="button"' if self.button else "")
        return f'<a href="{escape(self.href, quote=True)}"{button_class}>{self.text.render(context)}</a>'


@dataclass
class URL(InlineToken):
    href: str

    @classmethod
    def opening_re(cls) -> re.Pattern[str]:
        return re.compile(r"^https?://[^\s<>\[\]()]+")

    @classmethod
    def parse(cls, line: str, i: int) -> tuple[Optional["URL"], int]:
        match = URL.opening_re().match(line[i:])
        if not match:
            return None, i
        href = match.group(0)
        return URL(href), i + len(href)

    def render(self, context: Context):
        if not is_safe_href(self.href):
            raise Exception(f"Unsafe href: {self.href}")
        href = escape(self.href, quote=True)
        return f'<a href="{href}">{href}</a>'


@dataclass
class Text(InlineToken):
    value: str

    @classmethod
    def is_other_inline_token(_, line: str, i: int) -> bool:
        for cls in InlineToken.subclasses:
            if cls != Text:
                token, i = cls.parse(line, i)
                if token:
                    return True
        return False

    @classmethod
    def parse(cls, line: str, i: int) -> tuple[Optional["Text"], int]:
        value = ""
        j = i
        while j < len(line):
            if Text.is_other_inline_token(line, j):
                break
            value += line[j]
            j += 1
        return (Text(value), j) if value else (None, i)

    def render(self, context: Context):
        value = escape(self.value, quote=True)
        return value


def metadata(source: str, context: Context = Context()) -> Metadata:
    lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return Document.parse(lines).metadata()


def render(source: str, context: Context = Context()) -> str:
    lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return Document.parse(lines).render(context)


def is_safe_href(href: str) -> bool:
    href = href.strip()
    parsed = urlparse(href)
    return (not parsed.scheme) or (parsed.scheme.lower() in SAFE_SCHEMES)
