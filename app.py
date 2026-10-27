"""Flask 应用入口。

create_app() 组装应用实例：加载 Config 配置、初始化 SQLAlchemy、注册
``|markdown`` 模板过滤器（返回 Markup 以避免 Jinja2 自动转义）以及 blog 蓝图。
直接运行本模块即可启动开发服务器；首次使用需先执行 ``python init_db.py``
完成建表与示例文章写入。
"""
import markdown
from flask import Flask, render_template
from markupsafe import Markup

import config
from models import db
from routes import blog_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(config.Config)

    # 初始化数据库
    db.init_app(app)

    # 注册 Markdown 渲染过滤器（模板里用 |markdown）
    # 返回 Markup 对象，告诉 Jinja2 这是安全 HTML，不要再做自动转义
    md_extensions = app.config.get('MARKDOWN_EXTENSIONS', [])

    @app.template_filter('markdown')
    def markdown_filter(text):
        return Markup(markdown.markdown(text, extensions=md_extensions, output_format='html'))

    # 注册蓝图
    app.register_blueprint(blog_bp)

    # 向所有模板注入站点公网地址（供 og:url / og:image 拼绝对路径）
    @app.context_processor
    def inject_site_url():
        return {'site_url': app.config.get('SITE_URL', '')}

    # 自定义 404 页：静态托管时会导出成 404.html
    @app.errorhandler(404)
    def handle_not_found(error):
        return render_template('404.html'), 404

    return app


app = create_app()


if __name__ == '__main__':
    # 首次运行前请先执行：python init_db.py
    app.run(host='0.0.0.0', port=5001, debug=True)
