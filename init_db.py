"""数据库初始化脚本：创建表并写入示例文章

首次使用时执行：
    python init_db.py
"""
import datetime

from app import app
from models import db, Post, Category, Tag

# 示例文章数据
SAMPLE_POSTS = [
    {
        'title': '从零搭建一个 Flask 个人博客',
        'slug': 'build-flask-blog-from-scratch',
        'category': 'Python',
        'tags': ['Flask', 'Python', 'Web'],
        'summary': '用 Flask + SQLite + Markdown 搭建一个简洁实用的个人技术博客，从路由到模板全流程记录。',
        'content': """## 为什么自己写博客

市面上的博客平台很多，但自己用 Flask 搭一个，既能练习全栈开发，又能完全掌控内容与样式。

## 技术选型

- **后端**：Flask，轻量且生态丰富
- **数据库**：SQLite，零配置，适合个人站点
- **模板**：Jinja2，Flask 原生支持
- **正文**：Markdown，对技术写作友好

## 核心代码片段

定义文章模型只需要几行：

```python
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

## 小结

整套博客不到 500 行代码就能跑起来，后续可逐步加入评论、SEO、缓存等功能。
""",
    },
    {
        'title': 'Python 装饰器进阶：从原理到实战',
        'slug': 'python-decorator-advanced',
        'category': 'Python',
        'tags': ['Python', '进阶'],
        'summary': '装饰器是 Python 的高阶用法之一，本文从函数对象讲起，过渡到带参装饰器与类装饰器。',
        'content': """## 装饰器本质

装饰器就是一个接收函数、返回函数的函数。

```python
def log(fn):
    def wrapper(*args, **kwargs):
        print(f'调用 {fn.__name__}')
        return fn(*args, **kwargs)
    return wrapper

@log
def hello():
    print('hi')
```

## 带参数的装饰器

需要再嵌一层函数来接收参数：

```python
def repeat(times):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            for _ in range(times):
                fn(*args, **kwargs)
        return wrapper
    return decorator
```

## 小结

理解了闭包与函数对象，装饰器就不再神秘。
""",
    },
    {
        'title': 'VS Code 提升效率的 10 个快捷键',
        'slug': 'vscode-10-shortcuts',
        'category': '工具',
        'tags': ['VS Code', '效率'],
        'summary': '日常开发中最高频使用的 10 个 VS Code 快捷键，每一条都能省下大量时间。',
        'content': """## 列表

1. `Cmd + P` 快速打开文件
2. `Cmd + Shift + P` 命令面板
3. `Cmd + D` 选中下一个相同词
4. `Option + ↑/↓` 上下移动整行
5. `Cmd + /` 注释切换
6. `Cmd + B` 切换侧边栏
7. `Ctrl + `` ` 切换终端
8. `Cmd + F2` 全选相同词
9. `Option + 点击` 多光标编辑
10. `Cmd + Shift + K` 删除整行

## 小结

把这些快捷键练成肌肉记忆，写代码会顺畅很多。
""",
    },
    {
        'title': '聊聊工程师的写作习惯',
        'slug': 'writing-habits-for-engineers',
        'category': '随笔',
        'tags': ['思考', '写作'],
        'summary': '代码写得再好，如果无法清晰表达，影响力也会受限。聊聊技术写作的重要性。',
        'content': """## 为什么工程师要写作

- 写作是二次思考，能帮你梳理逻辑
- 文档是代码的延伸，让团队协作更顺畅
- 公开写作能建立个人技术品牌

## 如何开始

不必追求完美，先写下第一行。坚持每周一篇小总结，半年后你会看到自己的成长。
""",
    },
]


def get_or_create_category(name):
    """获取或创建分类"""
    slug = name.lower()
    cat = Category.query.filter_by(slug=slug).first()
    if cat is None:
        cat = Category(name=name, slug=slug)
        db.session.add(cat)
    return cat


def get_or_create_tag(name):
    """获取或创建标签"""
    t = Tag.query.filter_by(name=name).first()
    if t is None:
        t = Tag(name=name)
        db.session.add(t)
    return t


def main():
    with app.app_context():
        # 删除旧库并重建
        db.drop_all()
        db.create_all()

        # 间隔时间，让归档看起来更真实
        base_time = datetime.datetime.utcnow() - datetime.timedelta(days=90)

        for idx, item in enumerate(SAMPLE_POSTS):
            cat = get_or_create_category(item['category'])
            post = Post(
                title=item['title'],
                slug=item['slug'],
                summary=item['summary'],
                content=item['content'],
                category=cat,
                created_at=base_time + datetime.timedelta(days=idx * 12),
                updated_at=base_time + datetime.timedelta(days=idx * 12),
            )
            for tag_name in item['tags']:
                post.tags.append(get_or_create_tag(tag_name))
            db.session.add(post)

        db.session.commit()
        print(f'✅ 初始化完成，共写入 {len(SAMPLE_POSTS)} 篇示例文章。')


if __name__ == '__main__':
    main()
