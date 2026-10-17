"""Parse resource references and rewrite known URLs in HTML, CSS, and JavaScript."""
from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlsplit, urldefrag

from bs4 import BeautifulSoup
import tinycss2
from tinycss2.ast import StringToken

from .network import origin


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
        for index, token in enumerate(tokens):
            if token.type == 'at-keyword' and token.lower_value == 'import':
                first = next((item for item in tokens[index + 1:] if item.type not in ('whitespace', 'comment')), None)
                if first and first.type == 'string':
                    first.value = url_value(first.value)
                    first.representation = json.dumps(first.value, ensure_ascii=False)
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
    # Style attributes contain declarations, so both inputs use component values.
    tokens = tinycss2.parse_component_value_list(text, skip_comments=False)
    walk(tokens)
    return list(dict.fromkeys(dependencies)), tinycss2.serialize(tokens) if rewrite else text


def js_process(text, base, rewrite=None, *, known_urls=()):
    dependencies = []

    def replace(match):
        value = match.group('module') or match.group('asset')
        expression = match.group(0)
        # A computed import prefix does not identify the complete requested URL.
        if match.group('module') and re.match(r'\s*(?:\+|\.|\[)', text[match.end():]):
            return expression
        # URL probes, fetch calls, and arbitrary literals require observed requests.
        # Inferring GET dependencies could execute an unused service operation.
        runtime_only = match.group('asset') is not None or bool(re.search(r'\bfetch\s*\(', expression))
        if re.search(r'\bnew\s+URL\s*\(', expression):
            runtime_only = not value.startswith(('./', '../')) or not re.search(r'\.[a-zA-Z0-9]{1,8}(?:\?|$)', value) or not re.match(r'\s*,\s*import\.meta\.url\s*\)', text[match.end():])
        # Bare module specifiers need the original import map or build runtime.
        if not value.startswith(('/', './', '../', 'http://', 'https://')):
            return match.group(0)
        url = absolute(value, base)
        if url and not runtime_only:
            dependencies.append(url)
        return expression.replace(value, rewrite(url)) if rewrite and url and (not runtime_only or url in known_urls) else expression
    result = JS_REFERENCES.sub(replace, text)
    return list(dict.fromkeys(dependencies)), result


def html_process(text, base, rewrite=None, *, known_urls=(), integrity=None):
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
        if rewrite and integrity and tag.name in ('script', 'link') and tag.get('integrity'):
            dependency = absolute(tag.get('src' if tag.name == 'script' else 'href', ''), effective_base)
            if dependency:
                tag['integrity'] = integrity(dependency, tag['integrity'])
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
            found, new = js_process(str(tag.string), effective_base, rewrite, known_urls=known_urls)
            dependencies.extend(found)
            if rewrite:
                tag.string = new
        if rewrite and tag.name == 'a' and tag.get('href'):
            target = absolute(tag['href'], effective_base)
            if target and origin(target) == origin(base):
                fragment = urlsplit(tag['href']).fragment
                tag['href'] = rewrite(target) + ('#' + fragment if fragment else '')
    if rewrite and base_tag:
        base_tag['href'] = rewrite(effective_base)
    return list(dict.fromkeys(dependencies)), str(soup) if rewrite else text


def process(text, content_type, base, rewrite=None, *, known_urls=(), integrity=None):
    mime = content_type.lower()
    if 'html' in mime:
        return html_process(text, base, rewrite, known_urls=known_urls, integrity=integrity)
    if 'css' in mime:
        return css_process(text, base, rewrite)
    if 'javascript' in mime or urlsplit(base).path.endswith(('.js', '.mjs')):
        return js_process(text, base, rewrite, known_urls=known_urls)
    return [], text
