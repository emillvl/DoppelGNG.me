"""Discover and rewrite document, CSS, module, and literal resource dependencies."""
from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlsplit, urldefrag

from bs4 import BeautifulSoup
import tinycss2
from tinycss2.ast import StringToken


RESOURCE_ATTRIBUTES = {'script': ('src',), 'img': ('src', 'srcset'), 'source': ('src', 'srcset'), 'video': ('src', 'poster'), 'audio': ('src',), 'track': ('src',), 'iframe': ('src',), 'embed': ('src',), 'object': ('data',), 'input': ('src',), 'image': ('href', 'xlink:href'), 'use': ('href', 'xlink:href')}
RESOURCE_RELS = {'stylesheet', 'icon', 'preload', 'modulepreload', 'manifest', 'apple-touch-icon', 'mask-icon'}
JS_REFERENCES = re.compile(r'''(?:(?:\bimport\s*\(|\bimportScripts\s*\(|\b(?:fetch|Worker|SharedWorker)\s*\(|\bnew\s+URL\s*\(|\bfrom\s+|\bimport\s+)["'](?P<module>[^"'\n]+)["']|["'](?P<asset>(?:https?://|/|\./|\.\./)[^"'\s<>]+?\.(?:js|mjs|css|woff2?|ttf|otf|png|jpe?g|webp|avif|gif|svg|mp4|webm|wasm|json)(?:\?[^"'\s<>]*)?)["'])''')


def absolute(value, base):
    value = str(value).strip()
    if not value or value.startswith(('#', 'data:', 'blob:', 'javascript:', 'mailto:', 'tel:')):
        return None
    url = urldefrag(urljoin(base, value))[0]
    parts = urlsplit(url)
    return url if parts.scheme in ('http', 'https') and not parts.username and not parts.password else None


def srcset_parts(value):
    # A data URL can contain commas; preserve it as one candidate.
    return re.findall(r'(?:data:[^\s]+|[^,\s]+)(?:\s+\d+(?:\.\d+)?[wx])?', value)


def css_process(text, base, rewrite=None):
    dependencies = []

    def url_value(value):
        url = absolute(value, base)
        if url:
            dependencies.append(url)
        return rewrite(url) if rewrite and url else value

    def walk(tokens):
        for token in tokens:
            if token.type == 'url':
                new = url_value(token.value)
                token.value = new
                token.representation = f'url({json.dumps(new, ensure_ascii=False)})'
            elif token.type == 'function' and token.lower_name == 'url':
                value = tinycss2.serialize(token.arguments).strip().strip('\"\'')
                new = url_value(value)
                token.arguments = [StringToken(token.source_line, token.source_column, new, json.dumps(new, ensure_ascii=False))]
            else:
                if getattr(token, 'type', '') == 'at-rule' and token.lower_at_keyword == 'import':
                    first = next((item for item in token.prelude if item.type != 'whitespace'), None)
                    if first and first.type == 'string':
                        first.value = url_value(first.value)
                        first.representation = json.dumps(first.value, ensure_ascii=False)
                for field in ('prelude', 'content', 'arguments'):
                    children = getattr(token, field, None)
                    if children:
                        walk(children)
    tokens = tinycss2.parse_stylesheet(text, skip_comments=False, skip_whitespace=False)
    walk(tokens)
    return list(dict.fromkeys(dependencies)), tinycss2.serialize(tokens)


def js_process(text, base, rewrite=None):
    dependencies = []

    def replace(match):
        value = match.group('module') or match.group('asset')
        # Bare module specifiers need the original import map or build runtime.
        if not value.startswith(('/', './', '../', 'http://', 'https://')):
            return match.group(0)
        url = absolute(value, base)
        if url:
            dependencies.append(url)
        return match.group(0).replace(value, rewrite(url)) if rewrite and url else match.group(0)
    result = JS_REFERENCES.sub(replace, text)
    return list(dict.fromkeys(dependencies)), result


def html_process(text, base, rewrite=None):
    soup = BeautifulSoup(text, 'html.parser')
    base_tag = soup.find('base', href=True)
    effective_base = urljoin(base, base_tag['href']) if base_tag else base
    dependencies = []

    def value(original):
        url = absolute(original, effective_base)
        if url:
            dependencies.append(url)
        return rewrite(url) if rewrite and url else original

    for tag in soup.find_all(True):
        attributes = RESOURCE_ATTRIBUTES.get(tag.name, ())
        if tag.name == 'link' and RESOURCE_RELS.intersection(tag.get('rel', [])):
            attributes = ('href',)
        for attribute in attributes:
            if not tag.get(attribute):
                continue
            if attribute == 'srcset':
                candidates = []
                for candidate in srcset_parts(tag[attribute]):
                    parts = candidate.split()
                    candidates.append(' '.join([value(parts[0]), *parts[1:]]))
                tag[attribute] = ', '.join(candidates)
            else:
                tag[attribute] = value(tag[attribute])
        if tag.get('style'):
            found, new = css_process(tag['style'], effective_base, rewrite)
            dependencies.extend(found)
            if rewrite:
                tag['style'] = new
        if tag.name == 'style' and tag.string:
            found, new = css_process(str(tag.string), effective_base, rewrite)
            dependencies.extend(found)
            if rewrite:
                tag.string = new
        if tag.name == 'script' and tag.string and tag.get('type', '') in ('', 'module', 'text/javascript', 'application/javascript'):
            found, new = js_process(str(tag.string), effective_base, rewrite)
            dependencies.extend(found)
            if rewrite:
                tag.string = new
        if rewrite and tag.name == 'a' and tag.get('href'):
            target = absolute(tag['href'], effective_base)
            if target and urlsplit(target).netloc == urlsplit(base).netloc:
                fragment = urlsplit(tag['href']).fragment
                tag['href'] = rewrite(target) + ('#' + fragment if fragment else '')
    if rewrite and base_tag:
        base_tag['href'] = rewrite(effective_base)
    return list(dict.fromkeys(dependencies)), str(soup) if rewrite else text


def process(text, content_type, base, rewrite=None):
    mime = content_type.lower()
    if 'html' in mime:
        return html_process(text, base, rewrite)
    if 'css' in mime:
        return css_process(text, base, rewrite)
    if 'javascript' in mime or urlsplit(base).path.endswith(('.js', '.mjs')):
        return js_process(text, base, rewrite)
    return [], text
