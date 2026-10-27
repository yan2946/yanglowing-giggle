"""博客配置文件"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # 数据库配置（SQLite）
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'blog.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 密钥（生产环境请替换为强随机值）
    SECRET_KEY = 'dev-secret-key-change-in-production'

    # 博客基础信息
    BLOG_TITLE = '技术随笔'
    BLOG_SUBTITLE = '记录代码、思考与成长'
    BLOG_AUTHOR = 'Lumen'
    BLOG_AUTHOR_BIO = '一名热爱分享的后端工程师，专注于 Python、分布式系统与开发者工具。'
    BLOG_AUTHOR_GITHUB = 'https://github.com'
    BLOG_AUTHOR_EMAIL = 'me@example.com'

    # 每页文章数
    POSTS_PER_PAGE = 5

    # Markdown 渲染配置
    MARKDOWN_EXTENSIONS = [
        'fenced_code',
        'codehilite',
        'tables',
        'toc',
        'nl2br',
    ]
