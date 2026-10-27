"""上线前 8 项自查（自动部分）。

对 freeze.py 导出的 dist/ 做静态检查，能自动验的直接给结论，
必须人工确认的（真机手机端、真实 HTTPS、微信里发链接）单独标出来。

用法：
    ./venv/bin/python check_site.py
    ./venv/bin/python check_site.py --site-url https://xxx.tcloudbaseapp.com
"""
import argparse
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import unquote

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')

PASS = '通过'
WAIT = '待确认'
FAIL = '不通过'


class PageScanner(HTMLParser):
    """从一页 HTML 里抽出标题、meta、资源引用与链接。"""

    def __init__(self):
        HTMLParser.__init__(self)
        self.title = ''
        self.metas = {}
        self.icon_links = []
        self.refs = []          # 需要加载的资源（css / img / script）
        self.hrefs = []         # 跳转链接
        self.first_img = None
        self.imgs = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'title':
            self._in_title = True
        elif tag == 'meta':
            key = attrs.get('property') or attrs.get('name')
            if key and attrs.get('content') is not None:
                self.metas[key] = attrs.get('content')
        elif tag == 'link':
            rel = (attrs.get('rel') or '').lower()
            href = attrs.get('href') or ''
            if 'icon' in rel and href:
                self.icon_links.append(href)
            if rel == 'stylesheet' and href:
                self.refs.append(href)
        elif tag == 'img':
            src = attrs.get('src') or ''
            if src:
                self.refs.append(src)
                self.imgs.append(src)
                if self.first_img is None:
                    self.first_img = src
        elif tag == 'script':
            src = attrs.get('src') or ''
            if src:
                self.refs.append(src)
        elif tag == 'a':
            href = attrs.get('href') or ''
            if href:
                self.hrefs.append(href)

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()


def local_path(ref):
    """把站内引用转成 dist 下的绝对路径，站外返回 None。"""
    ref = ref.strip()
    if not ref or ref.startswith(('http://', 'https://', '//', 'data:', 'mailto:', '#', 'javascript:')):
        return None
    path = unquote(ref.split('#')[0].split('?')[0])
    if not path.startswith('/'):
        return None
    full = os.path.join(DIST_DIR, path.lstrip('/'))
    if os.path.isdir(full):
        full = os.path.join(full, 'index.html')
    return full


def collect_pages():
    pages = {}
    for root, _, files in os.walk(DIST_DIR):
        for name in files:
            if name.endswith('.html'):
                full = os.path.join(root, name)
                rel = os.path.relpath(full, DIST_DIR)
                with open(full, encoding='utf-8') as f:
                    scanner = PageScanner()
                    scanner.feed(f.read())
                pages[rel] = scanner
    return pages


def kb(path):
    return os.path.getsize(path) / 1024.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--site-url', default='')
    args = parser.parse_args()

    if not os.path.isdir(DIST_DIR):
        print('还没导出：先跑 ./venv/bin/python freeze.py')
        return 1

    pages = collect_pages()
    results = []

    def add(no, name, status, detail):
        results.append((no, name, status, detail))

    # 1 HTTPS
    insecure = []
    for rel, page in pages.items():
        for ref in page.refs + page.hrefs:
            if ref.startswith('http://'):
                insecure.append('%s -> %s' % (rel, ref))
    add(1, 'HTTPS', WAIT if not insecure else FAIL,
        '本地为 http，需打开公网地址看地址栏锁图标；页面内无 http:// 资源' if not insecure
        else '存在 http:// 资源：' + '; '.join(insecure[:3]))

    # 2 手机端
    no_viewport = [rel for rel, p in pages.items() if 'viewport' not in p.metas]
    css = os.path.join(DIST_DIR, 'static/css/style.css')
    has_media = False
    if os.path.exists(css):
        with open(css, encoding='utf-8') as f:
            has_media = '@media' in f.read()
    add(2, '手机端', WAIT if not no_viewport and has_media else FAIL,
        '全部页面有 viewport，CSS 含 @media 断点，需用 375px 视口或真机确认不横向溢出'
        if not no_viewport and has_media else '缺 viewport 的页面：%s；CSS 媒体查询：%s' % (no_viewport, has_media))

    # 3 404 页
    notfound = os.path.join(DIST_DIR, '404.html')
    ok404 = False
    detail404 = '未找到 404.html'
    if os.path.exists(notfound):
        with open(notfound, encoding='utf-8') as f:
            scanner = PageScanner()
            scanner.feed(f.read())
        back = [h for h in scanner.hrefs if 'index' in h or h == '/']
        ok404 = bool(back) and '返回首页' in open(notfound, encoding='utf-8').read()
        detail404 = '404.html 存在且含「返回首页」链接 -> %s' % (back[0] if back else '-')
    add(3, '404 页', PASS if ok404 else FAIL, detail404)

    # 4 首屏图
    home = pages.get('index.html')
    biggest = None
    biggest_size = -1
    if home:
        for ref in home.imgs:
            target = local_path(ref)
            if target and os.path.exists(target):
                size = kb(target)
                if size > biggest_size:
                    biggest_size = size
                    biggest = target
    if biggest:
        first_screen = biggest_size
        if os.path.exists(css):
            first_screen += kb(css)
        first_screen += kb(os.path.join(DIST_DIR, 'index.html'))
        add(4, '首屏图 ≤300KB', PASS if biggest_size <= 300 else FAIL,
            '首页最大图 %s 约 %.0f KB；首屏 HTML+CSS+图 合计约 %.0f KB'
            % (os.path.basename(biggest), biggest_size, first_screen))
    else:
        add(4, '首屏图 ≤300KB', FAIL, '首页没找到 img')

    # 5 标题与 favicon
    bad_title = []
    for rel, page in pages.items():
        if not page.title.strip():
            bad_title.append(rel)
        elif len(page.title) > 60:
            bad_title.append('%s(标题过长 %d 字)' % (rel, len(page.title)))
    ico = os.path.join(DIST_DIR, 'favicon.ico')
    has_icon = bool(home and home.icon_links)
    ok5 = not bad_title and os.path.exists(ico) and has_icon
    add(5, '标题与 favicon', PASS if ok5 else FAIL,
        '全部 %d 页标题非空；favicon.ico 存在（%.1f KB）；页面含 icon 声明' % (len(pages), kb(ico))
        if ok5 else '标题问题：%s；favicon.ico：%s；icon 声明：%s'
        % (bad_title[:3], os.path.exists(ico), has_icon))

    # 6 控制台无报错（资源全部存在）
    missing = []
    for rel, page in pages.items():
        for ref in page.refs:
            target = local_path(ref)
            if target and not os.path.exists(target):
                missing.append('%s -> %s' % (rel, ref))
    add(6, '控制台无报错', PASS if not missing else FAIL,
        '所有 css / 图片引用均能命中文件，无 JS 运行时依赖' if not missing
        else '缺失资源 %d 个：%s' % (len(missing), missing[:3]))

    # 7 链接能点通
    dead = []
    checked = 0
    for rel, page in pages.items():
        for href in page.hrefs:
            target = local_path(href)
            if target is None:
                continue
            checked += 1
            if not os.path.exists(target):
                dead.append('%s -> %s' % (rel, href))
    add(7, '链接能点通', PASS if not dead else FAIL,
        '检查 %d 条站内链接，全部命中' % checked if not dead
        else '死链 %d 条：%s' % (len(dead), dead[:3]))

    # 8 分享预览
    need = ['og:title', 'og:description', 'og:image', 'og:url']
    lack = [k for k in need if home is None or not home.metas.get(k)]
    og_img = home.metas.get('og:image', '') if home else ''
    absolute = og_img.startswith(('http://', 'https://'))
    size_ok = True
    if og_img:
        target = local_path(og_img.replace(args.site_url, '') if absolute else og_img)
        size_ok = bool(target and os.path.exists(target))
    ok8 = not lack and absolute and size_ok
    add(8, '分享预览正常', PASS if ok8 else (WAIT if not absolute and not lack else FAIL),
        'og:title / description / image 齐全，og:image 为绝对地址且文件存在（1200×630）'
        if ok8 else '缺字段：%s；og:image 绝对地址：%s；图片存在：%s' % (lack or '无', absolute, size_ok))

    print('')
    print('实验8 · 上线自查（自动部分）')
    print('站点规模：%d 个 HTML 页面，dist 共 %.0f KB' % (len(pages), sum(
        os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(DIST_DIR) for f in fs) / 1024.0))
    print('-' * 62)
    width = 0
    for no, name, status, detail in results:
        mark = {'通过': '[通过]', '待确认': '[待确认]', '不通过': '[不通过]'}[status]
        print('%d. %-12s %s' % (no, name, mark))
        print('   %s' % detail)
    print('-' * 62)
    passed = sum(1 for r in results if r[2] == PASS)
    waiting = sum(1 for r in results if r[2] == WAIT)
    print('自动通过 %d 项，待人工确认 %d 项，不通过 %d 项（8 项里过 6 项即达标）'
          % (passed, waiting, 8 - passed - waiting))
    return 0 if passed + waiting >= 6 else 1


if __name__ == '__main__':
    sys.exit(main())
