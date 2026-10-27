"""针对 models.py 的测试：默认值、浏览量自增、ORM 关系与唯一约束。

被测核心函数/行为：
- ``Post.increase_views()``：浏览量 +1 并提交事务；
- Post / Category / Tag 之间的一对多、多对多关系；
- 字段默认值与 slug 唯一约束。
"""
import pytest
from sqlalchemy.exc import IntegrityError

from models import db, Post, Category, Tag


def _new_post(**overrides):
    """构造一个未提交的 Post，必填字段给默认值。"""
    defaults = dict(title='测试文章', slug='test-post', content='正文')
    defaults.update(overrides)
    return Post(**defaults)


def test_post_defaults(app):
    """意图：新建文章时 views/is_published/summary 等应有正确默认值，
    created_at 应自动填充，保证入库数据符合业务预期。"""
    post = _new_post()
    db.session.add(post)
    db.session.commit()

    assert post.views == 0
    assert post.is_published is True
    assert post.summary == ''
    assert post.created_at is not None


def test_increase_views_increments_and_persists(app):
    """意图：increase_views 不仅要让内存对象 +1，还必须提交到数据库；
    用新会话重新读取，验证持久化而非仅修改了内存。"""
    post = _new_post()
    db.session.add(post)
    db.session.commit()
    post_id = post.id

    post.increase_views()
    assert post.views == 1

    # 模拟请求结束后重新取数据：从身份映射中清除后重新查询
    db.session.expunge_all()
    fresh = db.session.get(Post, post_id)
    assert fresh.views == 1


def test_increase_views_multiple_times(app):
    """意图：连续调用应累加（1→2），防止实现错误地总是重置为 1。"""
    post = _new_post()
    db.session.add(post)
    db.session.commit()

    post.increase_views()
    post.increase_views()
    assert post.views == 2


def test_post_repr(app):
    """意图：__repr__ 应包含标题，方便日志与调试时辨识对象。"""
    assert repr(_new_post(title='调试标题')) == '<Post 调试标题>'


def test_category_repr(app):
    """意图：分类的 __repr__ 同样应可读。"""
    assert repr(Category(name='Python', slug='python')) == '<Category Python>'


def test_tag_repr(app):
    """意图：标签的 __repr__ 同样应可读。"""
    assert repr(Tag(name='Flask')) == '<Tag Flask>'


def test_category_post_one_to_many_relationship(app):
    """意图：一个分类下可以挂多篇文章，并可通过 category.posts 反向查询。"""
    cat = Category(name='Python', slug='python')
    db.session.add_all([
        _new_post(slug='p1', category=cat),
        _new_post(slug='p2', title='第二篇', category=cat),
    ])
    db.session.commit()

    assert cat.posts.count() == 2
    # 正向：文章能取到所属分类
    post1 = Post.query.filter_by(slug='p1').first()
    assert post1.category.name == 'Python'


def test_post_tag_many_to_many_relationship(app):
    """意图：文章与标签是多对多——一篇文章可有多个标签，一个标签也可属于多篇文章，
    双向导航（post.tags / tag.posts）都必须可用。"""
    tag_flask = Tag(name='Flask')
    tag_web = Tag(name='Web')
    p1 = _new_post(slug='p1', tags=[tag_flask, tag_web])
    p2 = _new_post(slug='p2', title='文章二', tags=[tag_flask])
    db.session.add_all([p1, p2])
    db.session.commit()

    # 正向：一篇文章两个标签
    fresh_p1 = db.session.get(Post, p1.id)
    assert {t.name for t in fresh_p1.tags} == {'Flask', 'Web'}

    # 反向：Flask 标签下有两篇文章
    flask = Tag.query.filter_by(name='Flask').first()
    assert {p.slug for p in flask.posts} == {'p1', 'p2'}


def test_post_without_category_is_allowed(app):
    """意图：category_id 是可空字段，文章允许不属于任何分类（边界场景）。"""
    post = _new_post(slug='no-cat')
    db.session.add(post)
    db.session.commit()

    assert post.category is None


def test_duplicate_slug_raises_integrity_error(app):
    """意图：slug 是文章详情页 URL 的唯一标识，重复 slug 必须被数据库拒绝，
    否则会出现两篇文章互相覆盖路由的严重问题。"""
    db.session.add_all([_new_post(slug='dup'), _new_post(slug='dup', title='另一篇')])
    with pytest.raises(IntegrityError):
        db.session.commit()
    # 回滚以恢复会话可用状态
    db.session.rollback()


def test_duplicate_tag_name_raises_integrity_error(app):
    """意图：标签名有唯一约束，重复写入同样应报错。"""
    db.session.add_all([Tag(name='Flask'), Tag(name='Flask')])
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
