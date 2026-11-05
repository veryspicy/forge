"""富文本 HTML 净化（写入侧强制，白名单重建式）。

背景：CMS 正文以 HTML 落库，C 端 `v-html` 直接渲染，天然不做二次转义。
若正文混入 `<script>` / `onerror=` / `javascript:` 链接，即构成存储型 XSS。
因此在写入侧（ContentService）统一净化，前端只负责渲染。

实现取向：**白名单重建**——用标准库 HTMLParser 解析后重新序列化，
只输出白名单标签与属性，文本一律 `escape()`，未知标签丢弃（其文本内容保留）。
不使用正则替换式清洗（易被畸形标签绕过），也不引入第三方依赖
（保持后端运行镜像零新增依赖）。

约定：
- 属性白名单按标签收窄，`style` 仅保留 `text-align`（编辑器对齐产物）；
- URL 先剥离控制字符再校验 scheme，非 http/https/mailto/tel 的外链一律丢弃属性值；
- 相对链接（站内 `/contact`、锚点 `#faq`）放行；
- `<a>` 自动补 `rel="noopener noreferrer"`，`target` 仅允许 `_blank` / `_self`；
- `script/style/iframe/object/embed/template/noscript` 连内容一并丢弃。
"""

from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser

# 允许的标签：对齐 Tiptap（StarterKit + Image + Video + TextAlign）与 Markdown 渲染产物
ALLOWED_TAGS: frozenset[str] = frozenset(
    {
        "p",
        "br",
        "hr",
        "div",
        "span",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "strong",
        "b",
        "em",
        "i",
        "u",
        "s",
        "del",
        "sub",
        "sup",
        "code",
        "pre",
        "blockquote",
        "ul",
        "ol",
        "li",
        "a",
        "img",
        "video",
        "source",
        "figure",
        "figcaption",
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "th",
        "td",
    }
)

# 自闭合标签（无 end tag）
VOID_TAGS: frozenset[str] = frozenset({"br", "hr", "img", "source"})

# 连同内容一起丢弃的标签
DROP_CONTENT_TAGS: frozenset[str] = frozenset(
    {"script", "style", "iframe", "object", "embed", "template", "noscript", "svg", "math"}
)

# 按标签收窄的属性白名单，避免把 href/src 泛化到任意标签
ALLOWED_ATTRIBUTES: dict[str, frozenset[str]] = {
    "a": frozenset({"href", "title", "target"}),
    "img": frozenset({"src", "alt", "title", "width", "height", "loading"}),
    "video": frozenset({"src", "poster", "controls", "preload", "width", "height", "style"}),
    "source": frozenset({"src", "type"}),
    "th": frozenset({"colspan", "rowspan", "style"}),
    "td": frozenset({"colspan", "rowspan", "style"}),
    "p": frozenset({"style"}),
    "div": frozenset({"style"}),
    "h1": frozenset({"style"}),
    "h2": frozenset({"style"}),
    "h3": frozenset({"style"}),
    "h4": frozenset({"style"}),
    "h5": frozenset({"style"}),
    "h6": frozenset({"style"}),
}

# 仅允许的内联样式声明（其余丢弃）
ALLOWED_STYLE_PROPERTIES: frozenset[str] = frozenset({"text-align"})

# 允许的 URL scheme（仅作用于带 scheme 的绝对地址）
ALLOWED_URL_SCHEMES: frozenset[str] = frozenset({"http", "https", "mailto", "tel"})

# 布尔属性：出现即输出（值为任意非空字符串）
BOOLEAN_ATTRIBUTES: frozenset[str] = frozenset({"controls"})

_URL_ATTRS: frozenset[str] = frozenset({"href", "src", "poster"})
_SECURITY_REL = "noopener noreferrer"

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x20\x7f]")
_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")
_STYLE_VALUE_RE = re.compile(r"^text-align\s*:\s*(left|right|center|justify)\s*$", re.IGNORECASE)


def _sanitize_style(value: str) -> str | None:
    """只保留合法的 text-align 声明，其余样式丢弃。"""
    for declaration in value.split(";"):
        if not declaration.strip():
            continue
        if not _STYLE_VALUE_RE.match(declaration.strip()):
            return None
        align = declaration.split(":", 1)[1].strip().lower()
        return f"text-align: {align}"
    return None


def _sanitize_url(value: str) -> str | None:
    """校验 URL：剥离控制字符后核对 scheme，非白名单 scheme 返回 None。"""
    stripped = value.strip()
    # 攻击面：java\tscript: / java\nscript: 等插入控制字符的绕过写法
    probe = _CONTROL_CHARS_RE.sub("", stripped)
    match = _SCHEME_RE.match(probe)
    if match and match.group(1).lower() not in ALLOWED_URL_SCHEMES:
        return None
    return stripped


def _sanitize_attribute(tag: str, name: str, value: str, attrs: dict[str, str]) -> str | None:
    """返回净化后的属性值，None 表示丢弃该属性。"""
    lowered = name.lower()

    if lowered in _URL_ATTRS:
        return _sanitize_url(value)

    if lowered == "style":
        return _sanitize_style(value)

    if lowered == "target":
        return value if value.strip().lower() in {"_blank", "_self"} else None

    if lowered == "loading":
        return value if value.strip().lower() in {"lazy", "eager"} else None

    if lowered in {"width", "height", "colspan", "rowspan"}:
        return value if value.strip().isdigit() else None

    if lowered == "type":
        # video/source 的 MIME，形如 video/mp4
        return value if re.fullmatch(r"[\w.+\-]+/[\w.+\-]+", value.strip()) else None

    _ = (tag, attrs)
    return value


class _Sanitizer(HTMLParser):
    """白名单重建式净化器：解析 token 后重新序列化。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._out: list[str] = []
        self._stack: list[str] = []
        self._drop_depth = 0

    # ---- 内部工具 ----
    def _render_start(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        rendered: list[str] = []
        collected: dict[str, str] = {}
        for raw_name, raw_value in attrs:
            name = (raw_name or "").lower()
            allowed = ALLOWED_ATTRIBUTES.get(tag)
            if allowed is None or name not in allowed:
                continue
            value = "" if raw_value is None else raw_value
            if name in BOOLEAN_ATTRIBUTES:
                rendered.append(name)
                continue
            safe = _sanitize_attribute(tag, name, value, collected)
            if safe is None:
                continue
            collected[name] = safe
            rendered.append(f'{name}="{escape(safe, quote=True)}"')

        if tag == "a":
            # 外链安全：编辑器产物与粘贴内容都可能缺 rel
            rendered.append(f'rel="{_SECURITY_REL}"')

        suffix = (" " + " ".join(rendered)) if rendered else ""
        if tag in VOID_TAGS:
            self._out.append(f"<{tag}{suffix}>")
        else:
            self._out.append(f"<{tag}{suffix}>")
            self._stack.append(tag)

    # ---- HTMLParser 回调 ----
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if self._drop_depth:
            if lowered in DROP_CONTENT_TAGS:
                self._drop_depth += 1
            return
        if lowered in DROP_CONTENT_TAGS:
            self._drop_depth = 1
            return
        if lowered in ALLOWED_TAGS:
            self._render_start(lowered, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if self._drop_depth or lowered in DROP_CONTENT_TAGS or lowered not in ALLOWED_TAGS:
            return
        self._render_start(lowered, attrs)
        if lowered not in VOID_TAGS:
            # 自闭合的普通标签（如 `<p />`）需要立即补闭合，避免吞掉后续内容
            self._stack.pop()
            self._out.append(f"</{lowered}>")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if self._drop_depth:
            if lowered in DROP_CONTENT_TAGS:
                self._drop_depth -= 1
            return
        if lowered not in self._stack:
            return
        # 关闭到匹配位置，丢弃中间未闭合标签（保持输出结构闭合）
        while self._stack:
            open_tag = self._stack.pop()
            self._out.append(f"</{open_tag}>")
            if open_tag == lowered:
                break

    def handle_data(self, data: str) -> None:
        if self._drop_depth or not data:
            return
        self._out.append(escape(data, quote=False))

    def handle_comment(self, _data: str) -> None:
        # 注释一律丢弃（避免条件注释等 IE 遗留攻击面）
        return

    # ---- 收尾 ----
    def result(self) -> str:
        while self._stack:
            self._out.append(f"</{self._stack.pop()}>")
        return "".join(self._out)


def sanitize_html(value: str | None) -> str:
    """净化富文本 HTML，返回可安全落库并下发前端的字符串。

    Args:
        value: 原始 HTML（允许 None / 空串）。

    Returns:
        白名单过滤后的 HTML；空输入返回空串。
    """
    if not value:
        return ""
    parser = _Sanitizer()
    parser.feed(value)
    parser.close()
    return parser.result()
