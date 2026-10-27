"""针对 app.py 的测试：应用工厂与 markdown 模板过滤器。

被测核心函数：
- ``create_app()``：组装 Flask 应用、加载配置、初始化数据库、注册蓝图与过滤器；
- 闭包内注册的 ``markdown`` 过滤器（通过 Jinja 环境间接测试）。
"""
from flask import Flask

from app import create_app


def test_create_app_returns_flask_instance():
    """意图：create_app 必须返回一个可用的 Flask 应用实例，这是整个站点的启动前提。"""
    app = create_app()
    assert isinstance(app, Flask)


def test_create_app_loads_config():
    """意图：验证配置确实从 Config 类加载（密钥与博客标题为代表性字段），
    避免“应用能启动但配置全部丢失”的回归。"""
    app = create_app()
    assert app.config['SECRET_KEY'] == 'dev-secret-key-change-in-production'
    assert app.config['POSTS_PER_PAGE'] == 5


def test_blueprint_registered():
    """意图：routes.py 中的 blog 蓝图必须已注册，否则所有页面路由都会 404。"""
    app = create_app()
    assert 'blog' in app.blueprints


def test_markdown_filter_is_registered():
    """意图：模板依赖 ``|markdown`` 过滤器渲染文章正文，过滤器缺失会导致模板渲染报错。"""
    app = create_app()
    assert 'markdown' in app.jinja_env.filters


def test_markdown_filter_renders_heading():
    """意图：基础 Markdown 语法（标题）应被转换为对应 HTML 标签。
    注：配置启用了 toc 扩展，标题会被附加 id 属性，因此只断言关键结构。"""
    app = create_app()
    render = app.jinja_env.filters['markdown']
    html = render('# Hello')
    assert '<h1' in html
    assert 'Hello</h1>' in html


def test_markdown_filter_renders_inline_code():
    """意图：行内代码应包裹在 <code> 标签中，保证技术文章的代码片段样式正确。"""
    app = create_app()
    render = app.jinja_env.filters['markdown']
    assert '<code>x = 1</code>' in render('`x = 1`')


def test_markdown_filter_fenced_code_extension():
    """意图：fenced_code + codehilite 扩展必须生效——三反引号代码块应渲染为
    带 codehilite 容器的 <pre><code>；语法高亮会把代码拆进 <span>，
    因此断言代码原文单词与容器结构，而非完整字符串。"""
    app = create_app()
    render = app.jinja_env.filters['markdown']
    md = '```python\nprint(1)\n```'
    html = render(md)
    assert 'codehilite' in html
    assert '<pre>' in html
    assert 'print' in html


def test_markdown_filter_tables_extension():
    """意图：tables 扩展必须生效，表格语法应渲染成 <table> 而非原始竖线文本。"""
    app = create_app()
    render = app.jinja_env.filters['markdown']
    md = '| a | b |\n|---|---|\n| 1 | 2 |'
    assert '<table>' in render(md)


def test_markdown_filter_empty_string():
    """意图：边界场景——空字符串应安全地返回空字符串，不抛出异常。"""
    app = create_app()
    render = app.jinja_env.filters['markdown']
    assert render('') == ''
