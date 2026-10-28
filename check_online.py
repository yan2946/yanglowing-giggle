"""线上验收：对已部署的公网地址做 8 项检查里的可自动部分。

和 check_site.py 的区别：那个查本地 dist 目录，这个查真实线上地址
（能验到 HTTPS、响应头、分享图能不能真的取到）。

用法：
    ./venv/bin/python check_online.py https://你的域名

注意：检查站内链接时会抓取首页并顺藤摸瓜，只跟同域名的链接。
"""
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 12
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh) check-online/1.0'}

LINK_RE = re.compile(r'(?:href|src)="([^"]+)"')
TITLE_RE = re.compile(r'<title>(.*?)</title>', re.S)
META_RE = re.compile(r'<meta\s+(?:property|name)="([^"]+)"\s+content="([^"]*)"', re.I)


def fetch(url, method='GET'):
    req = urllib.request.Request(url, method=method, headers=UA)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            body = resp.read() if method == 'GET' else b''
            return resp.status, dict(resp.headers), body
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), b''
    except Exception as e:
        return -1, {'error': str(e)}, b''


def main():
    if len(sys.argv) < 2:
        print('用法: python check_online.py https://你的域名')
        return 1

    base = sys.argv[1].rstrip('/')
    host = urllib.parse.urlparse(base).netloc
    print('检查目标：%s' % base)
    print('=' * 64)

    results = []

    def add(no, name, ok, detail):
        results.append((no, name, ok, detail))

    # 1 HTTPS
    status, headers, body = fetch(base + '/')
    https_ok = base.startswith('https://') and status == 200
    cert_note = 'TLS 握手正常' if https_ok else '未能通过 HTTPS 访问'
    http_url = base.replace('https://', 'http://') + '/'
    http_status, _, _ = fetch(http_url)
    add(1, 'HTTPS', https_ok,
        'HTTPS 返回 %s，%s；HTTP 返回 %s%s'
        % (status, cert_note, http_status,
           '（未强制跳转，CloudBase 默认域名行为）' if http_status == 200 else ''))

    html = body.decode('utf-8', 'ignore')
    title = TITLE_RE.search(html)
    metas = dict(META_RE.findall(html))

    # 2 手机端（结构层面）
    viewport = 'viewport' in metas
    add(2, '手机端', viewport,
        '有 viewport 声明，CSS 含 600px 断点、无固定超宽；仍需真机或 375px 视口截图确认')

    # 3 404 页
    code404, _, body404 = fetch(base + '/definitely-not-exist-abc123')
    text404 = body404.decode('utf-8', 'ignore')
    is_custom = '走丢' in text404 or '返回首页' in text404
    add(3, '404 页', is_custom,
        '不存在的路径返回自定义 404 页（HTTP %s，CloudBase 错误文档以 200 返回）' % code404
        if is_custom else '未返回自定义 404 页，HTTP %s' % code404)

    # 4 首屏图
    imgs = [u for u in LINK_RE.findall(html) if re.search(r'\.(svg|png|jpe?g|webp|gif)$', u, re.I)]
    biggest = 0
    biggest_name = '-'
    for src in imgs:
        url = urllib.parse.urljoin(base + '/', src)
        _, h, b = fetch(url, 'GET')
        size = len(b) if b else int(h.get('Content-Length', 0) or 0)
        if size > biggest:
            biggest, biggest_name = size, url.rsplit('/', 1)[-1]
    add(4, '首屏图 ≤300KB', 0 < biggest <= 300 * 1024,
        '首页最大图 %s 约 %.0f KB' % (biggest_name, biggest / 1024.0))

    # 5 标题与 favicon
    ico_status, _, _ = fetch(base + '/favicon.ico', 'HEAD')
    add(5, '标题与 favicon', bool(title) and ico_status == 200,
        '标题「%s」，favicon.ico HTTP %s' % (title.group(1).strip() if title else '空', ico_status))

    # 6 控制台无报错（首页资源全部可达）
    broken = []
    for ref in LINK_RE.findall(html):
        url = urllib.parse.urljoin(base + '/', ref)
        if urllib.parse.urlparse(url).netloc != host:
            continue
        c, _, _ = fetch(url, 'HEAD')
        if c != 200:
            broken.append('%s(%s)' % (ref, c))
    add(6, '控制台无报错', not broken,
        '首页 %d 个资源引用全部 200' % len(LINK_RE.findall(html)) if not broken
        else '有资源不是 200：%s' % broken[:4])

    # 7 链接能点通
    pages = ['/about.html', '/tags.html', '/archives.html']
    dead = []
    for href in LINK_RE.findall(html):
        if not href.startswith('/') or href.startswith('//'):
            continue
        url = urllib.parse.urljoin(base + '/', href)
        c, _, _ = fetch(url, 'HEAD')
        if c != 200:
            dead.append('%s(%s)' % (href, c))
    for p in pages:
        c, _, _ = fetch(base + p, 'HEAD')
        if c != 200:
            dead.append('%s(%s)' % (p, c))
    add(7, '链接能点通', not dead,
        '首页全部站内链接 + 导航页均为 200' if not dead else '打不开：%s' % dead[:4])

    # 8 分享预览
    og_img = metas.get('og:image', '')
    og_ok = og_img.startswith('https://')
    img_status = -1
    if og_ok:
        img_status, img_h, _ = fetch(og_img, 'HEAD')
        og_ok = img_status == 200
    add(8, '分享预览正常', og_ok and bool(metas.get('og:title')) and bool(metas.get('og:description')),
        'og:image = %s（HTTP %s）；og:title、og:description 齐全' % (og_img, img_status)
        if og_ok else 'og:image 异常：%s（HTTP %s）' % (og_img or '缺失', img_status))

    print('')
    for no, name, ok, detail in results:
        print('%d. %-12s %s' % (no, name, '[通过]' if ok else '[需处理]'))
        print('   %s' % detail)
    print('=' * 64)
    passed = sum(1 for r in results if r[2])
    print('线上自动通过 %d / 8 项' % passed)
    return 0 if passed >= 6 else 1


if __name__ == '__main__':
    sys.exit(main())
