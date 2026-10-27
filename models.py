"""数据模型定义。

定义博客的核心数据结构：Post（文章）、Category（分类）、Tag（标签）。
- Post 与 Category 为多对一关系（一篇文章归属一个分类，可为空）；
- Post 与 Tag 为多对多关系，通过 post_tags 关联表实现；
- Category / Tag 共享 id / name / __repr__，由 NamedModel 抽象基类提供，
  子类各自定义与 Post 的关系及特有字段（如 Category.slug）。
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 文章与标签的多对多关系表
POST_TAG_TABLE = db.Table(
    'post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True),
)


class NamedModel(db.Model):
    """Category 与 Tag 的公共抽象基类。

    提供主键 id、唯一名称 name 与通用 __repr__；子类各自定义与 Post 的关系
    （一对多或多对多）以及各自特有的字段（如 Category.slug）。
    本类设为 abstract，不对应任何数据表。
    """
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}>'


class Category(NamedModel):
    """文章分类：与 Post 为一对多关系。"""
    slug = db.Column(db.String(50), unique=True, nullable=False)
    posts = db.relationship('Post', backref='category', lazy='dynamic')


class Tag(NamedModel):
    """文章标签：与 Post 为多对多关系（经 post_tags 关联表）。"""
    posts = db.relationship('Post', secondary=POST_TAG_TABLE, backref='tags')


class Post(db.Model):
    """文章实体。

    created_at 记录创建时间（插入时自动填充）；
    updated_at 仅在记录被更新时写入，未被更新过则为 NULL——
    因此"从未更新"与"刚创建"在语义上保持区分。
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    summary = db.Column(db.String(200), default='')
    content = db.Column(db.Text, nullable=False)
    views = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))

    def __repr__(self):
        return f'<Post {self.title}>'

    def increase_views(self):
        """浏览量 +1 并立即提交事务。"""
        self.views += 1
        db.session.commit()
