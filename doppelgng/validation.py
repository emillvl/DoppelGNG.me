"""Compare browser snapshots, screenshots, and interaction states."""
from __future__ import annotations

import io
import json
import time
from urllib.parse import urlsplit

from PIL import Image, ImageChops, ImageStat
from selenium.webdriver.common.by import By

from .storage import now


def visual_diff(original, local, destination, *, channel_threshold=25, allowed_ratio=0.01):
    a, b = Image.open(original).convert('RGB'), Image.open(local).convert('RGB')
    if a.size != b.size:
        return {'passed': False, 'reason': 'Screenshot dimensions differ', 'original': a.size, 'local': b.size}
    difference = ImageChops.difference(a, b)
    extrema = difference.split()
    maximum = ImageChops.lighter(ImageChops.lighter(extrema[0], extrema[1]), extrema[2])
    mask = maximum.point(lambda value: 255 if value > channel_threshold else 0)
    changed = mask.histogram()[255]
    ratio = changed / (a.width * a.height)
    difference.save(destination)
    return {'passed': ratio <= allowed_ratio, 'changed_pixel_ratio': ratio, 'mean_channel_difference': sum(ImageStat.Stat(difference).mean) / 3, 'allowed_ratio': allowed_ratio, 'channel_threshold': channel_threshold, 'diff': str(destination)}


def snapshot(browser):
    return browser.driver.execute_script('''
        return {title:document.title, text:document.body.innerText.replace(/\\s+/g,' ').trim(),
          viewport:[innerWidth,innerHeight], scroll:[scrollX,scrollY],
          width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,
          links:Array.from(document.querySelectorAll('a[href]'),a=>({href:a.href,text:(a.innerText||a.getAttribute('aria-label')||'').trim(),target:a.target})),
          controls:Array.from(document.querySelectorAll('button,input,select,textarea,[role="button"],details'), e=>({tag:e.tagName,type:e.type||'',text:(e.innerText||e.getAttribute('aria-label')||'').trim(),disabled:e.disabled||false})),
          brokenImages:Array.from(document.images).filter(i=>i.currentSrc&&i.complete&&!i.naturalWidth).map(i=>i.currentSrc),
          fonts:Array.from(document.fonts).map(f=>({family:f.family,status:f.status,weight:f.weight,style:f.style})),
          headings:Array.from(document.querySelectorAll('h1,h2,h3'),e=>({text:e.innerText, font:getComputedStyle(e).fontFamily,size:getComputedStyle(e).fontSize})),
          forms:Array.from(document.forms,f=>({action:f.action,method:f.method}))};
    ''')


def scroll(browser, fraction):
    browser.driver.execute_script('document.documentElement.style.scrollBehavior="auto"; window.scrollTo(0, Math.round((document.documentElement.scrollHeight-innerHeight)*arguments[0]));', fraction)
    time.sleep(0.85)
    browser.settle()


def exercise_discovery(browser):
    # Scrolling reveals lazy assets and viewport-triggered navigation prefetches.
    for fraction in (0, 0.25, 0.5, 0.75, 1, 0):
        scroll(browser, fraction)


def record_baseline(browser, url, directory, viewports, on_observation=None):
    records = []
    for width, height in viewports:
        browser.viewport(width, height)
        browser.navigate(url)
        exercise_discovery(browser)
        for position, fraction in (('top', 0), ('middle', 0.5), ('bottom', 1)):
            scroll(browser, fraction)
            filename = f'original-{width}x{height}-{position}.png'
            browser.driver.save_screenshot(str(directory / filename))
            records.append({'viewport': [width, height], 'position': position, 'fraction': fraction, 'screenshot': filename, 'snapshot': snapshot(browser)})
        if on_observation:
            on_observation()
    scroll(browser, 0)
    (directory / 'baseline.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    return records


def normalize_links(values, origin):
    result = []
    for item in values:
        url = item['href']
        if url.startswith(origin):
            url = url[len(origin):]
        result.append((url, item['text'], item['target']))
    return result


def local_validate(browser, url, local_url, directory, baselines, *, allowed_ratio=0.01):
    observations = []
    errors = []
    current_viewport = None
    start = len(browser.bidi.events)
    original_origin = f'{urlsplit(url).scheme}://{urlsplit(url).netloc}'
    local_origin = f'{urlsplit(local_url).scheme}://{urlsplit(local_url).netloc}'
    for baseline in baselines:
        viewport = baseline['viewport']
        if viewport != current_viewport:
            browser.viewport(*viewport)
            browser.navigate(local_url)
            exercise_discovery(browser)
            current_viewport = viewport
        scroll(browser, baseline['fraction'])
        filename = baseline['screenshot'].replace('original-', 'local-')
        browser.driver.save_screenshot(str(directory / filename))
        measured = snapshot(browser)
        expected = baseline['snapshot']
        comparison = visual_diff(directory / baseline['screenshot'], directory / filename, directory / filename.replace('local-', 'diff-'), allowed_ratio=allowed_ratio)
        checks = {
            'visual': comparison['passed'], 'title': expected['title'] == measured['title'],
            'content': expected['text'] == measured['text'],
            'headings_and_fonts': expected['headings'] == measured['headings'],
            'layout_width': measured['width'] <= viewport[0] and measured['width'] == expected['width'],
            'layout_height': abs(expected['height'] - measured['height']) <= 2,
            'images': not measured['brokenImages'],
            'links': normalize_links(expected['links'], original_origin) == normalize_links(measured['links'], local_origin),
            'controls': expected['controls'] == measured['controls'],
        }
        observations.append({'viewport': viewport, 'position': baseline['position'], 'checks': checks, 'visual': comparison, 'snapshot': measured, 'screenshot': filename})
        errors.extend(f'{viewport} {baseline["position"]}: {name}' for name, passed in checks.items() if not passed)
    browser.driver.refresh()
    browser.settle()
    if browser.driver.title != baselines[-1]['snapshot']['title']:
        errors.append('Direct-route refresh changed page title')
    events = browser.bidi.events[start:]
    for event in events:
        params = event.get('params', {})
        method = event.get('method')
        if method == 'network.fetchError':
            errors.append(f'Network failure: {params.get("request", {}).get("url")}: {params.get("errorText")}')
        elif method == 'network.responseCompleted' and params['response']['status'] >= 400:
            errors.append(f'HTTP {params["response"]["status"]}: {params["response"]["url"]}')
        elif method == 'log.entryAdded' and params.get('level') == 'error':
            errors.append(f'Browser console: {params.get("text")}')
        elif method == 'recorder.error':
            errors.append('Browser event recorder disconnected')
    result = {'passed': not errors, 'checked_at': now(), 'observations': observations, 'errors': list(dict.fromkeys(errors)), 'refresh_tested': True}
    (directory / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def interaction_check(browser, url, local_url, directory, configured=None, after_original=None):
    """Compare controls and disclosures, rejecting controls associated with forms."""
    browser.navigate(url)
    discovered = browser.driver.execute_script('''
        const selector=e=>{if(e.id)return '#'+CSS.escape(e.id); const p=[]; while(e&&e.nodeType===1){let n=1,s=e;while(s=s.previousElementSibling)if(s.tagName===e.tagName)n++;p.unshift(e.tagName.toLowerCase()+':nth-of-type('+n+')');e=e.parentElement;}return p.join('>');};
        return Array.from(document.querySelectorAll('button,input:not([type="hidden"]),select,textarea,[role="button"],details')).map(e=>({
          selector:selector(e),tag:e.tagName,type:e.type||'',text:(e.innerText||e.getAttribute('aria-label')||'').trim(),
          target:e.getAttribute('aria-controls'),expanded:e.hasAttribute('aria-expanded'),form:!!e.closest('form'),
          summary:e.tagName==='DETAILS'&&e.querySelector('summary')?selector(e.querySelector('summary')):null}));
    ''')
    scenarios = list(configured or [])
    covered = {scenario['selector'] for scenario in scenarios}
    for control in discovered:
        if control['selector'] in covered or control['summary'] in covered:
            continue
        if control['summary']:
            scenarios.append({'action': 'details', 'selector': control['summary'], 'assert_selector': control['selector']})
            covered.add(control['selector'])
        elif control['expanded'] and control['target'] and not control['form']:
            scenarios.append({'action': 'click', 'selector': control['selector'], 'assert_selector': '[id=' + json.dumps(control['target']) + ']'})
            covered.add(control['selector'])
    results = []
    for scenario in scenarios:
        if scenario['action'] not in ('click', 'hover', 'details'):
            raise ValueError(f'Unsupported read-only scenario action: {scenario["action"]}')
        states = []
        screenshots = []
        for target in (url, local_url):
            event_start = len(browser.bidi.events)
            browser.navigate(target)
            element = browser.driver.find_element(By.CSS_SELECTOR, scenario['selector'])
            if browser.driver.execute_script('return arguments[0].closest("form") !== null || !!arguments[0].form', element):
                raise ValueError('Submitting forms on the original site requires a separately authorized service test')
            if scenario['action'] == 'hover':
                from selenium.webdriver import ActionChains
                ActionChains(browser.driver).move_to_element(element).perform()
            else:
                element.click()
            browser.settle()
            assertion = browser.driver.find_element(By.CSS_SELECTOR, scenario.get('assert_selector', scenario['selector']))
            states.append({'text': assertion.text, 'expanded': assertion.get_attribute('aria-expanded'), 'pressed': assertion.get_attribute('aria-pressed'), 'selected': assertion.get_attribute('aria-selected'), 'checked': assertion.get_attribute('checked'), 'value': assertion.get_attribute('value'), 'open': assertion.get_attribute('open'), 'displayed': assertion.is_displayed()})
            filename = f'interaction-{len(results)}-{"original" if target == url else "local"}.png'
            browser.driver.save_screenshot(str(directory / filename))
            screenshots.append(filename)
            if target == url and after_original:
                after_original(browser.bidi.events[event_start:])
        comparison = visual_diff(directory / screenshots[0], directory / screenshots[1], directory / f'interaction-{len(results)}-diff.png')
        local_errors = []
        for event in browser.bidi.events[event_start:]:
            params = event.get('params', {})
            if event.get('method') == 'network.fetchError' or (event.get('method') == 'log.entryAdded' and params.get('level') == 'error') or (event.get('method') == 'network.responseCompleted' and params['response']['status'] >= 400):
                local_errors.append({'method': event['method'], 'url': params.get('response', params.get('request', {})).get('url'), 'message': params.get('text', params.get('errorText')), 'status': params.get('response', {}).get('status')})
        results.append({'scenario': scenario, 'passed': states[0] == states[1] and comparison['passed'] and not local_errors, 'original': states[0], 'local': states[1], 'visual': comparison, 'browser_errors': local_errors})
    untested = [control for control in discovered if control['selector'] not in covered and control['summary'] not in covered]
    if untested:
        results.append({'passed': False, 'reason': 'Interactive controls need explicit read-only scenarios or a verified local service adapter', 'untested': untested})
    (directory / 'interactions.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    return results
