#!/usr/bin/env python3
"""Wrap src/page.html in a full HTML document and write index.html for GitHub Pages."""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
body = open(os.path.join(ROOT, 'src', 'page.html'), encoding='utf-8').read()
head = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="Live results, maps and coalition math for Israel's 26th Knesset election, from The Globe in Brief.">
<meta property="og:title" content="Israel Election Watcher">
<meta property="og:type" content="website">
<meta property="og:url" content="https://johnnoto.github.io/israel-election-watcher/">
<meta property="og:image" content="https://johnnoto.github.io/israel-election-watcher/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta property="og:description" content="Live Knesset results, a terrain map of who votes where, and a kingmaker model of the coalition math.">
<style>
:root { color-scheme: light; padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); }
body { margin: 0; font-size: 14px; font-family: system-ui, sans-serif; }
img { max-width: 100%; }
[hidden] { display: none !important; }
</style>
'''
title_end = body.index('</style>') + len('</style>')
doc = head + body[:title_end] + '\n</head>\n<body>\n' + body[title_end:] + '\n</body>\n</html>\n'
open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(doc)
print('wrote index.html', len(doc))
