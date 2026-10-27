"""pytest 全局夹具（fixtures）

职责：
1. 把项目根目录加入 sys.path，使被测模块的扁平导入
   （``from models import db`` / ``import config``）在任意工作目录下都可用；
2. 为每个测试用例提供独立的临时 SQLite 数据库，绝不污染开发用的 blog.db；
3. 提供 Flask test client 与文章数据工厂，简化用例准备数据的代码。
"""
import os
import sys
import uuid
import datetime
from types import SimpleNamespace

import pytest

# 项目根目录 = tests/ 的上一级
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import config as blog_config  # noqa: E402  （必须在 sys.path 注入之后导入）
from app import create_app  # noqa: E402
from models import db, Post, Category, Tag  # noqa: E402


@pytest.fixture
def app(tmp_path):
    """创建一个绑定临时数据库的 Flask 应用，并在建表后提供给用例。

    注意：Flask-SQLAlchemy 3.x 在 ``init_app`` 阶段就会创建 engine，
    因此必须在 ``create_app()`` **之前**替换配置类上的数据库地址，
    否则测试会误连开发库 blog.db。用例结束后恢复原值。
    """
    test_db_path = tmp_path / 'test_blog.db'
    original_uri = blog_config.Config.SQLALCHEMY_DATABASE_URI
    blog_config.Config.SQLALCHEMY_DATABASE_URI = f'sqlite:///{test_db_path}'

    try:
        application = create_app()
        application.config['TESTING'] = True

        with application.app_context():
            db.create_all()
            yield application
            # 用例结束：释放连接并删表，保证用例之间完全隔离
            db.session.remove()
            db.drop_all()
    finally:
        blog_config.Config.SQLALCHEMY_DATABASE_URI = original_uri


@pytest.fixture
def client(app):
    """Flask 测试客户端，用于发起 HTTP 请求。"""
    return app.test_client()


@pytest.fixture
def make_post(app):
    """文章数据工厂：按需快速构造一篇（或多篇）已入库的文章。

    用法::

        data = make_post(title='示例', slug='demo', category_name='Python',
                         tag_names=['Flask'], published=True)
        # data.id / data.slug / data.title 可供后续断言使用
    """
    def _make_post(title=None, slug=None, content='正文内容', summary='摘要',
                   published=True, category_name=None, tag_names=None,
                   created_at=None, views=0):
        title = title or f'文章-{uuid.uuid4().hex[:8]}'
        slug = slug or f'slug-{uuid.uuid4().hex[:8]}'

        # 分类：按名称查找，不存在则创建
        category = None
        if category_name:
            category = Category.query.filter_by(name=category_name).first()
            if category is None:
                category = Category(name=category_name, slug=category_name.lower())
                db.session.add(category)

        # 标签：逐个按名称查找或创建
        tags = []
        for name in (tag_names or []):
            tag = Tag.query.filter_by(name=name).first()
            if tag is None:
                tag = Tag(name=name)
                db.session.add(tag)
            tags.append(tag)

        post = Post(
            title=title,
            slug=slug,
            content=content,
            summary=summary,
            is_published=published,
            category=category,
            tags=tags,
            views=views,
        )
        if created_at is not None:
            post.created_at = created_at
        db.session.add(post)
        db.session.commit()

        # 仅返回标量字段，避免用例在 session 关闭后触碰游离对象
        return SimpleNamespace(id=post.id, slug=post.slug, title=post.title)

    return _make_post


def fixed_time(days_ago):
    """辅助函数：返回“距离今天 days_ago 天前”的 UTC 时间，用于构造确定性排序数据。"""
    return datetime.datetime.utcnow() - datetime.timedelta(days=days_ago)
