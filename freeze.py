"""把 Flask 博客导出为纯静态站点，用于 CloudBase 静态托管。

CloudBase 静态托管只发文件、不执行 Python，所以要先在本地把每个页面渲染成
HTML，再整目录上传。本脚本用 Flask 的 test_client 逐页抓取，做两件事：

1. 把站内链接改写成静态文件名（/tag/进阶 → /tag-3.html），
   避免中文 / 空格标签名在服务器上匹配不到文件；
2. 额外导出一个 404.html，静态托管可以把它配置成错误页。

用法：
    ./venv/bin/python freeze.py
    ./venv/bin/python freeze.py --site-url https://xxx.tcloudbaseapp.com

产物在 dist/，把 dist 目录里的所有内容上传到静态托管根目录即可。
"""
import argparse
import os
import re
import shutil
from urllib.parse import quote, unquote

from app import app
from models import Category, Post, Tag

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')

HREF_RE = re.compile(r'href="([^"]*)"')


def collect_urls():
    """收集全部页面，返回 [(Flask 路由, 静态文件相对路径), ...]。"""
    urls = [
        ('/', 'index.html'),
        ('/tags', 'tags.html'),
        ('/archives', 'archives.html'),
        ('/about', 'about.html'),
    ]
    with app.app_context():
        posts = Post.query.filter_by(is_published=True).order_by(Post.created_at.desc()).all()
        categories = Category.query.order_by(Category.id).all()
        tags = Tag.query.order_by(Tag.id).all()

    for post in posts:
        urls.append(('/post/%s' % post.slug, 'post/%s.html' % post.slug))
    # 分类 slug 和标签名可能含中文 / 空格，用 id 命名文件最稳
    for category in categories:
        urls.append(('/category/%s' % category.slug, 'category-%d.html' % category.id))
    for tag in tags:
        urls.append(('/tag/%s' % tag.name, 'tag-%d.html' % tag.id))
    return urls


def build_lookup(urls):
    """Flask 路由 → 静态文件路径，键统一按解码后的形式保存。"""
    lookup = {}
    for url, path in urls:
        lookup[unquote(url)] = path
    return lookup


def rewrite_links(html, lookup):
    """把站内链接改写成静态文件路径，站外链接和锚点保持原样。"""
    def replace(match):
        raw = match.group(1)
        if not raw.startswith('/') or raw.startswith('//'):
            return match.group(0)

        path, _, fragment = raw.partition('#')
        path, _, query = path.partition('?')

        if path in ('', '/'):
            return match.group(0)

        target = lookup.get(unquote(path))
        if not target:
            return match.group(0)

        suffix = ('?' + query) if query else ''
        suffix += ('#' + fragment) if fragment else ''
        return 'href="/%s%s"' % (target, suffix)

    return HREF_RE.sub(replace, html)


def write_file(rel_path, content):
    out_path = os.path.join(DIST_DIR, rel_path)
    parent = os.path.dirname(out_path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return rel_path


def main():
    parser = argparse.ArgumentParser(description='导出静态站点')
    parser.add_argument('--site-url', default=os.environ.get('SITE_URL', ''),
                        help='站点公网地址，用于 og:url / og:image 绝对路径')
    args = parser.parse_args()

    app.config['SITE_URL'] = args.site_url.rstrip('/')

    if os.path.isdir(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR)

    urls = collect_urls()
    lookup = build_lookup(urls)
    client = app.test_client()

    written = []
    failed = []
    for url, path in urls:
        resp = client.get(quote(url, safe='/?=&'))
        if resp.status_code != 200:
            failed.append((url, resp.status_code))
            continue
        html = rewrite_links(resp.get_data(as_text=True), lookup)
        written.append(write_file(path, html))

    resp = client.get('/__this_page_should_not_exist__')
    if resp.status_code == 404:
        html = rewrite_links(resp.get_data(as_text=True), lookup)
        written.append(write_file('404.html', html))
    else:
        failed.append(('/__404__', resp.status_code))

    static_src = os.path.join(BASE_DIR, 'static')
    shutil.copytree(static_src, os.path.join(DIST_DIR, 'static'))

    favicon = os.path.join(static_src, 'images', 'favicon.ico')
    if os.path.exists(favicon):
        shutil.copy(favicon, os.path.join(DIST_DIR, 'favicon.ico'))

    with open(os.path.join(DIST_DIR, 'robots.txt'), 'w', encoding='utf-8') as f:
        f.write('User-agent: *\nAllow: /\n')

    total = 0
    for root, _, files in os.walk(DIST_DIR):
        for name in files:
            total += os.path.getsize(os.path.join(root, name))

    print('导出完成：%d 个 HTML 页面' % len(written))
    for path in written:
        print('  + %s' % path)
    if failed:
        print('失败 %d 个：' % len(failed))
        for url, code in failed:
            print('  ! %s -> HTTP %s' % (url, code))
    print('dist 总体积：%.1f KB' % (total / 1024.0))
    if not args.site_url:
        print('提示：未指定 --site-url，og:image 会是相对路径，微信分享卡片可能拿不到图。')
        print('      拿到公网域名后重跑一次：')
        print('      ./venv/bin/python freeze.py --site-url https://你的域名')
    return 0 if not failed else 1


if __name__ == '__main__':
    raise SystemExit(main())
