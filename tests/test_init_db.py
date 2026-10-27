"""针对 init_db.py 的测试：两个“获取或创建”辅助函数。

被测核心函数：
- ``get_or_create_category(name)``：不存在则建分类（slug 取名称小写），存在则复用；
- ``get_or_create_tag(name)``：同上，针对标签。

这类函数的关键风险是“重复调用产生重复数据”，因此测试重点是幂等性。
"""
from models import db, Category, Tag
from init_db import get_or_create_category, get_or_create_tag


def test_get_or_create_category_creates_new(app):
    """意图：首次调用时分类不存在，应新建并返回，slug 规则为名称转小写。"""
    cat = get_or_create_category('Python')
    db.session.commit()

    assert cat.id is not None
    assert cat.name == 'Python'
    assert cat.slug == 'python'
    assert Category.query.count() == 1


def test_get_or_create_category_is_idempotent(app):
    """意图：核心回归点——对同一名称重复调用必须返回同一条记录，
    不能插入重复分类（否则侧栏与筛选会出现重复项）。"""
    first = get_or_create_category('Python')
    db.session.commit()
    second = get_or_create_category('Python')

    assert first.id == second.id
    assert Category.query.count() == 1


def test_get_or_create_category_distinct_names(app):
    """意图：不同名称应创建不同分类，避免“查不到时误复用已有记录”。"""
    py = get_or_create_category('Python')
    tool = get_or_create_category('工具')
    db.session.commit()

    assert py.id != tool.id
    assert Category.query.count() == 2


def test_get_or_create_tag_creates_new(app):
    """意图：首次调用应创建标签。"""
    tag = get_or_create_tag('Flask')
    db.session.commit()

    assert tag.id is not None
    assert tag.name == 'Flask'
    assert Tag.query.count() == 1


def test_get_or_create_tag_is_idempotent(app):
    """意图：重复获取同名标签必须幂等，返回同一对象且不新增行。"""
    first = get_or_create_tag('Flask')
    db.session.commit()
    second = get_or_create_tag('Flask')

    assert first.id == second.id
    assert Tag.query.count() == 1
