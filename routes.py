"""路由与视图函数。

定义 blog 蓝图下的全部页面：首页、文章详情、分类、标签、标签总览、归档、关于。
首页与分类/标签页共用 index.html 模板，但布局有意区分：
- 首页传 show_banner=True，显示横幅、不显示标题；
- 分类/标签页传 title=...，显示标题、不显示横幅。
已发布文章的分页查询逻辑统一收敛到 _paginate_published()。
"""
from flask import Blueprint, render_template, request
from sqlalchemy import desc

from config import Config
from models import Post, Category, Tag

blog_bp = Blueprint('blog', __name__)


def _get_categories():
    """获取所有分类（供模板上下文使用，仅模块内部调用）。"""
    return Category.query.order_by(Category.name).all()


@blog_bp.context_processor
def inject_globals():
    """向所有模板注入全局变量：博客信息与分类列表。"""
    return {
        'blog_title': Config.BLOG_TITLE,
        'blog_subtitle': Config.BLOG_SUBTITLE,
        'blog_author': Config.BLOG_AUTHOR,
        'categories': _get_categories,
    }


def _current_page():
    """从查询字符串读取页码，缺省为 1。"""
    return request.args.get('page', 1, type=int)


def _paginate_published(page, *filters):
    """对已发布文章按创建时间倒序分页。

    filters 为额外的过滤条件（如 Post.category_id == cat.id、
    Post.tags.contains(t)），统一处理首页 / 分类 / 标签页的公共查询逻辑。
    """
    return (
        Post.query
        .filter(Post.is_published.is_(True), *filters)
        .order_by(desc(Post.created_at))
        .paginate(page=page, per_page=Config.POSTS_PER_PAGE, error_out=False)
    )


@blog_bp.route('/')
def index():
    """首页：分页展示已发布文章，并显示 Banner。"""
    pagination = _paginate_published(_current_page())
    return render_template(
        'index.html',
        posts=pagination.items,
        pagination=pagination,
        show_banner=True,
    )


@blog_bp.route('/post/<slug>')
def post_detail(slug):
    """文章详情页：按 slug 查询已发布文章，并累计浏览量。"""
    post = Post.query.filter_by(slug=slug, is_published=True).first_or_404()
    post.increase_views()
    return render_template('post.html', post=post)


@blog_bp.route('/category/<slug>')
def show_category(slug):
    """分类页：展示某分类下的已发布文章。"""
    cat = Category.query.filter_by(slug=slug).first_or_404()
    pagination = _paginate_published(_current_page(), Post.category_id == cat.id)
    return render_template(
        'index.html',
        posts=pagination.items,
        pagination=pagination,
        title=f'分类：{cat.name}',
    )


@blog_bp.route('/tag/<name>')
def show_tag(name):
    """标签页：展示带某标签的已发布文章。"""
    t = Tag.query.filter_by(name=name).first_or_404()
    pagination = _paginate_published(_current_page(), Post.tags.contains(t))
    return render_template(
        'index.html',
        posts=pagination.items,
        pagination=pagination,
        title=f'标签：{name}',
    )


@blog_bp.route('/tags')
def tags():
    """标签总览页：按名称列出全部标签及其文章数。"""
    all_tags = Tag.query.order_by(Tag.name).all()
    return render_template('tags.html', tags=all_tags, title='标签')


@blog_bp.route('/archives')
def archives():
    """归档页：按时间倒序列出全部已发布文章。"""
    posts = Post.query.filter_by(is_published=True).order_by(desc(Post.created_at)).all()
    return render_template('archives.html', posts=posts, title='归档')


@blog_bp.route('/about')
def about():
    """关于页。"""
    return render_template('about.html', title='关于')
