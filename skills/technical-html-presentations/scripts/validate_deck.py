#!/usr/bin/env python3
"""Validate structural invariants of a self-contained HTML slide deck."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
NAVIGATION_TAGS = {"a", "area"}
LINK_RESOURCE_REL_TOKENS = {
    "apple-touch-icon",
    "apple-touch-icon-precomposed",
    "apple-touch-startup-image",
    "dns-prefetch",
    "icon",
    "manifest",
    "mask-icon",
    "modulepreload",
    "preconnect",
    "prefetch",
    "preload",
    "stylesheet",
}
TAG_RESOURCE_ATTRIBUTES = {
    "applet": {"archive", "code", "codebase"},
    "body": {"background"},
    "html": {"manifest"},
    "object": {"archive", "classid", "codebase", "data"},
    "table": {"background"},
    "td": {"background"},
    "th": {"background"},
}


def _is_external(value: str, base_href: str | None = None) -> bool:
    resolved = urljoin(base_href, value.strip()) if base_href else value.strip()
    return resolved.startswith("//") or urlparse(resolved).scheme in {"http", "https"}


def _first_attribute(attrs: list[tuple[str, str | None]], name: str) -> str | None:
    return next((value for attr_name, value in attrs if attr_name == name), None)


def _strip_css_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


class DeckParser(HTMLParser):
    def __init__(self, allow_external: bool = False) -> None:
        super().__init__()
        self.allow_external = allow_external
        self.stack: list[str] = []
        self.svg_stack: list[bool] = []
        self.errors: list[str] = []
        self.slides = 0
        self.notes = 0
        self.progress_elements = 0
        self.counter_element: tuple[str, int] | None = None
        self.counter_text: list[str] = []
        self.base_href: str | None = None
        self.resource_urls: list[tuple[str, str]] = []
        self.css_text: list[str] = []
        self.style_blocks: list[str] = []
        self.srcdocs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_element(tag, attrs, push=tag not in VOID_TAGS)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in VOID_TAGS and not self._is_svg_element(tag):
            self.errors.append(f"self-closing syntax on non-void HTML element <{tag}>")
        self._handle_element(tag, attrs, push=False)

    def _is_svg_element(self, tag: str) -> bool:
        return tag == "svg" or bool(
            self.stack
            and self.svg_stack[-1]
            and self.stack[-1] != "foreignobject"
        )

    def _handle_element(self, tag: str, attrs: list[tuple[str, str | None]], push: bool) -> None:
        classes = set((_first_attribute(attrs, "class") or "").split())
        if push:
            is_svg = self._is_svg_element(tag)
            self.stack.append(tag)
            self.svg_stack.append(is_svg)
        if tag == "section" and "slide" in classes:
            self.slides += 1
        if tag == "aside" and "speaker-notes" in classes:
            self.notes += 1
        if "progress" in classes:
            self.progress_elements += 1
        if "counter" in classes and push and self.counter_element is None:
            self.counter_element = (tag, len(self.stack))
        base_href = _first_attribute(attrs, "href")
        if tag == "base" and self.base_href is None and base_href:
            self.base_href = base_href
        style = _first_attribute(attrs, "style")
        if style:
            self.css_text.append(style)
        srcdoc = _first_attribute(attrs, "srcdoc")
        if tag == "iframe" and srcdoc is not None:
            self.srcdocs.append(srcdoc)
        resource_attributes = {"poster", "src"}
        resource_attributes.update(TAG_RESOURCE_ATTRIBUTES.get(tag, set()))
        if tag == "link":
            rel_tokens = set((_first_attribute(attrs, "rel") or "").lower().split())
            if rel_tokens & LINK_RESOURCE_REL_TOKENS:
                resource_attributes.add("href")
        elif tag not in NAVIGATION_TAGS | {"base"}:
            resource_attributes.update({"href", "xlink:href"})
        for name in resource_attributes:
            value = _first_attribute(attrs, name)
            if value:
                values = value.split() if name == "archive" else (value,)
                self.resource_urls.extend((name, url) for url in values)
        for name in ("imagesrcset", "srcset"):
            value = _first_attribute(attrs, name)
            if not value:
                continue
            for candidate in value.split(","):
                url = candidate.strip().split(maxsplit=1)[0]
                if url:
                    self.resource_urls.append((name, url))

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_TAGS:
            self.errors.append(f"malformed closing tag </{tag}> for void element")
            return
        if not self.stack or self.stack[-1] != tag:
            expected = self.stack[-1] if self.stack else "nothing"
            self.errors.append(f"unbalanced closing tag </{tag}>; expected {expected}")
            return
        if self.counter_element == (tag, len(self.stack)):
            self.counter_element = None
        self.stack.pop()
        self.svg_stack.pop()

    def handle_data(self, data: str) -> None:
        if self.counter_element is not None:
            self.counter_text.append(data)
        if self.stack and self.stack[-1] == "style":
            self.css_text.append(data)
            self.style_blocks.append(data)


def _external_dependency_errors(root: DeckParser) -> list[str]:
    errors: list[str] = []
    parsers: list[tuple[DeckParser, str | None]] = [(root, None)]
    seen_srcdocs: set[tuple[str, str | None]] = set()
    while parsers:
        parser, inherited_base = parsers.pop()
        base_href = (
            urljoin(inherited_base, parser.base_href)
            if inherited_base and parser.base_href
            else parser.base_href or inherited_base
        )
        for name, value in parser.resource_urls:
            if _is_external(value, base_href):
                errors.append(f"external dependency: {name}={value}")

        css_text = "\n".join(_strip_css_comments(css) for css in parser.css_text)
        css_imports = [
            match.group(2)
            for pattern in (
                r"@import\s+url\(\s*(['\"]?)(.*?)\1\s*\)",
                r"@import\s+(['\"])(.*?)\1",
            )
            for match in re.finditer(pattern, css_text, re.IGNORECASE)
        ]
        css_urls = [
            match.group(2)
            for match in re.finditer(
                r"url\(\s*(['\"]?)(.*?)\1\s*\)", css_text, re.IGNORECASE
            )
        ]
        if any(_is_external(value, base_href) for value in css_imports):
            errors.append("external CSS @import dependency found")
        if any(_is_external(value, base_href) for value in css_urls):
            errors.append("external CSS url() dependency found")

        for srcdoc in parser.srcdocs:
            key = (srcdoc, base_href)
            if key in seen_srcdocs:
                continue
            seen_srcdocs.add(key)
            fragment = DeckParser()
            fragment.feed(srcdoc)
            parsers.append((fragment, base_href))
    return errors


def validate(path: Path, allow_external: bool = False) -> list[str]:
    text = path.read_text(encoding="utf-8")
    parser = DeckParser(allow_external=allow_external)
    parser.feed(text)
    errors = list(parser.errors)
    if not allow_external:
        errors.extend(_external_dependency_errors(parser))
    if parser.stack:
        errors.append(f"unclosed tags: {', '.join(parser.stack)}")
    if parser.slides == 0:
        errors.append("no semantic <section class=\"slide\"> elements found")
    if parser.notes != parser.slides:
        errors.append(f"speaker-note count {parser.notes} does not match slide count {parser.slides}")
    if parser.progress_elements != 1:
        errors.append(
            f"progress element count {parser.progress_elements}; expected exactly 1"
        )

    counter = " ".join(parser.counter_text).strip()
    match = re.fullmatch(r"1\s*/\s*(\d+)", counter)
    if not match:
        errors.append(f"initial counter must be '1 / N'; found {counter!r}")
    elif int(match.group(1)) != parser.slides:
        errors.append(f"counter total {match.group(1)} does not match slide count {parser.slides}")

    style_css = "\n".join(_strip_css_comments(css) for css in parser.style_blocks)
    progress = re.search(
        r"(?:^|})\s*\.progress\s*\{[^}]*?width:\s*([0-9.]+)%",
        style_css,
        re.DOTALL,
    )
    if not progress:
        errors.append("initial .progress width percentage not found")
    elif parser.slides:
        actual = float(progress.group(1))
        expected = 100 / parser.slides
        if abs(actual - expected) > 0.02:
            errors.append(f"initial progress width {actual}% does not match {expected:.3f}% for {parser.slides} slides")

    return errors


def main() -> int:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument(
        "--allow-external",
        action="store_true",
        help="permit external resource dependencies",
    )
    argument_parser.add_argument("deck", metavar="DECK.html", type=Path)
    args = argument_parser.parse_args()
    path = args.deck
    if not path.is_file():
        argument_parser.error(f"file not found: {path}")
    errors = validate(path, allow_external=args.allow_external)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    dependency_status = "external resources permitted" if args.allow_external else "local dependencies"
    print(f"OK: {path} has consistent slides, notes, counter, progress, and {dependency_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
