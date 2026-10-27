"""针对 routes.py 的测试：通过 Flask test client 对全部页面做端到端验证。

覆盖视图函数：
- index：列表展示、发布状态过滤、时间倒序、分页、越界页码；
- post_detail：正常访问、404、未发布 404、浏览量自增、Markdown 渲染；
- category / tag：筛选、标题、不存在时 404；
- archives：只列已发布文章并按时间倒序；
- about：正常渲染；
- context_processor：全局变量注入到模板。
"""
from conftest import fixed_time
from models import db, Post


# ---------------------------------------------------------------------------
# 首页 /
# ---------------------------------------------------------------------------

def test_index_empty_database(client):
    """意图：边界场景——库里一篇文章都没有时，首页应 200 并显示空状态文案，而非报错。"""
    resp = client.get('/')
    assert resp.status_code == 200
    assert '这里还没有内容'.encode() in resp.data


def test_index_lists_published_posts(client, make_post):
    """意图：已发布文章的标题应出现在首页列表中。"""
    make_post(title='我的第一篇博客', slug='first-post')
    resp = client.get('/')
    assert resp.status_code == 200
    assert '我的第一篇博客'.encode() in resp.data


def test_index_hides_unpublished_posts(client, make_post):
    """意图：草稿（is_published=False）绝不能出现在公开首页，防止未完成内容泄露。"""
    make_post(title='公开文章', slug='public', published=True)
    make_post(title='私密草稿', slug='secret', published=False)

    html = client.get('/').data.decode()
    assert '公开文章' in html
    assert '私密草稿' not in html


def test_index_orders_by_created_at_desc(client, make_post):
    """意图：文章必须按创建时间倒序（最新在前）展示。通过两个标题在 HTML 中
    出现的先后位置断言排序，而不是依赖列表页暴露数据结构。"""
    make_post(title='最旧的文章', slug='old', created_at=fixed_time(30))
    make_post(title='最新的文章', slug='new', created_at=fixed_time(1))

    html = client.get('/').data.decode()
    assert html.index('最新的文章') < html.index('最旧的文章')


def test_index_pagination_first_page(client, make_post):
    """意图：POSTS_PER_PAGE=5，构造 6 篇文章后第一页只展示 5 篇，
    并出现指向第 2 页的“下一页”链接。
    显式给定不同创建时间，避免同时间戳下分页顺序不确定。"""
    for i in range(6):
        make_post(title=f'文章{i}', slug=f'post-{i}', created_at=fixed_time(i))

    html = client.get('/').data.decode()
    assert '下一页' in html
    assert 'page=2' in html
    assert '文章0' in html


def test_index_pagination_second_page(client, make_post):
    """意图：第二页应只展示第 6 篇文章，且第一页的文章不应再出现。"""
    for i in range(6):
        # fixed_time(i) 随编号增大而越早：文章5 最早，落在第二页
        make_post(title=f'文章{i}', slug=f'post-{i}', created_at=fixed_time(i))

    html = client.get('/?page=2').data.decode()
    assert '文章5' in html  # 最早创建 -> 排在最后 -> 第二页
    assert '文章0' not in html


def test_index_page_out_of_range_returns_empty(client, make_post):
    """意图：error_out=False 时，超出范围的页码不应 404，而应返回 200 与空列表。"""
    make_post(title='仅有的一篇', slug='only')
    resp = client.get('/?page=999')
    assert resp.status_code == 200
    assert '这里还没有内容'.encode() in resp.data


# ---------------------------------------------------------------------------
# 文章详情 /post/<slug>
# ---------------------------------------------------------------------------

def test_post_detail_success(client, make_post):
    """意图：已发布文章详情页正常返回 200，且标题、正文均出现在页面中。"""
    make_post(title='详情页文章', slug='detail-post', content='正文 ABC')
    resp = client.get('/post/detail-post')
    assert resp.status_code == 200
    assert '详情页文章'.encode() in resp.data
    assert '正文 ABC'.encode() in resp.data


def test_post_detail_not_found(client):
    """意图：访问不存在的 slug 必须返回 404，而不是 500 或空白页。"""
    resp = client.get('/post/does-not-exist')
    assert resp.status_code == 404


def test_post_detail_unpublished_returns_404(client, make_post):
    """意图：未发布文章即使知道 slug 也不能通过 URL 直接访问。"""
    make_post(title='草稿', slug='draft', published=False)
    resp = client.get('/post/draft')
    assert resp.status_code == 404


def test_post_detail_increases_views(client, app, make_post):
    """意图：每访问一次详情页，浏览量应 +1 并落库（端到端验证 increase_views
    在视图中被真正调用，而不只是单元层面可用）。"""
    data = make_post(slug='viewed')

    client.get('/post/viewed')
    with app.app_context():
        assert db.session.get(Post, data.id).views == 1

    client.get('/post/viewed')
    with app.app_context():
        assert db.session.get(Post, data.id).views == 2


def test_post_detail_renders_markdown(client, make_post):
    """意图：正文以 Markdown 存储，详情页必须输出渲染后的 HTML（而非被转义的源码）。
    这是端到端回归：过滤器必须返回 Markup，否则页面会出现 &lt;h1&gt; 之类转义文本。"""
    make_post(slug='md', content='# 大标题\n\n正文段落')
    html = client.get('/post/md').data.decode()
    assert '<h1' in html
    assert '大标题</h1>' in html
    assert '正文段落' in html
    assert '&lt;h1' not in html  # 未被自动转义


# ---------------------------------------------------------------------------
# 分类 /category/<slug>
# ---------------------------------------------------------------------------

def test_category_page_filters_posts(client, make_post):
    """意图：分类页只展示该分类下的文章，标题显示分类名。"""
    make_post(title='Python 文章', slug='py', category_name='Python')
    make_post(title='工具文章', slug='tool', category_name='工具')

    resp = client.get('/category/python')
    assert resp.status_code == 200
    html = resp.data.decode()
    assert '分类：Python' in html
    assert 'Python 文章' in html
    assert '工具文章' not in html


def test_category_page_hides_unpublished(client, make_post):
    """意图：分类筛选同样要遵守“未发布不展示”的规则。"""
    make_post(title='草稿', slug='draft', category_name='Python', published=False)
    make_post(title='正式', slug='formal', category_name='Python', published=True)

    html = client.get('/category/python').data.decode()
    assert '正式' in html
    assert '草稿' not in html


def test_category_not_found(client):
    """意图：不存在的分类返回 404。"""
    assert client.get('/category/nope').status_code == 404


# ---------------------------------------------------------------------------
# 标签 /tag/<name>
# ---------------------------------------------------------------------------

def test_tag_page_filters_posts(client, make_post):
    """意图：标签页只展示带该标签的文章（验证多对多关系查询在视图中正确）。"""
    make_post(title='Flask 实战', slug='flask-post', tag_names=['Flask'])
    make_post(title='Django 实战', slug='django-post', tag_names=['Django'])

    html = client.get('/tag/Flask').data.decode()
    assert '标签：Flask' in html
    assert 'Flask 实战' in html
    assert 'Django 实战' not in html


def test_tag_post_with_multiple_tags_appears_under_each(client, make_post):
    """意图：一篇文章挂多个标签时，从任一标签入口都应能找到它。"""
    make_post(title='多标签文章', slug='multi', tag_names=['Python', 'Web'])

    assert '多标签文章' in client.get('/tag/Python').data.decode()
    assert '多标签文章' in client.get('/tag/Web').data.decode()


def test_tag_not_found(client):
    """意图：不存在的标签返回 404。"""
    assert client.get('/tag/Unknown').status_code == 404


# ---------------------------------------------------------------------------
# 归档 /archives 与 关于 /about
# ---------------------------------------------------------------------------

def test_archives_lists_only_published_and_orders_desc(client, make_post):
    """意图：归档页应包含全部已发布文章（含数量统计）、排除草稿，并按时间倒序。"""
    make_post(title='旧文', slug='old', created_at=fixed_time(20))
    make_post(title='新文', slug='new', created_at=fixed_time(1))
    make_post(title='草稿', slug='draft', published=False)

    html = client.get('/archives').data.decode()
    assert '共 2 篇文章' in html
    assert '旧文' in html and '新文' in html
    assert '草稿' not in html
    # 倒序：新文位置更靠前
    assert html.index('新文') < html.index('旧文')


def test_archives_empty(client):
    """意图：边界场景——无文章时归档页正常渲染。"""
    assert client.get('/archives').status_code == 200


def test_about_page(client):
    """意图：关于页为静态页面，应稳定返回 200 并包含其标志性标题。"""
    resp = client.get('/about')
    assert resp.status_code == 200
    assert '关于我'.encode() in resp.data


# ---------------------------------------------------------------------------
# 上下文处理器
# ---------------------------------------------------------------------------

def test_global_context_injected_into_pages(client):
    """意图：context_processor 注入的博客标题应出现在所有页面的页头中，
    一旦注入失效，模板会因变量缺失而渲染异常或显示空白。"""
    html = client.get('/').data.decode()
    assert '技术随笔' in html
