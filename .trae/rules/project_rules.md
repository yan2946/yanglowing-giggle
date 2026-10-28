---
description: 个人技术博客的项目约定（Flask + SQLite + CloudBase 静态托管）
globs: ["**/*.py", "**/*.html", "**/*.md"]
alwaysApply: true
---

# 项目约定

## 技术栈与结构
- 后端：Flask 3.0 + Flask-SQLAlchemy 3.1 + Markdown 3.6，入口 `app.py`（应用工厂 `create_app()`）。
- 分层：`config.py` 配置 / `models.py` 模型 / `routes.py` 蓝图 / `templates/` 模板 / `static/` 静态资源。
- 新页面必须继承 `templates/base.html`，不要在模板里重复写 `<head>`。

## 安全红线
- 任何密钥、口令、令牌只能从环境变量读取，禁止写进代码、模板、README。
- `.env`、`blog.db`、`dist/`、`venv/` 已在 `.gitignore` 中，禁止 `git add -f` 强加。
- 提交前必须确认 `git status` 里没有 `.env` 或数据库文件。

## 静态化部署约束
- 线上跑的是 CloudBase 静态托管，**不执行 Python**。任何新增页面都要能被 `freeze.py` 导出，否则线上 404。
- 带中文的路径（如标签名）必须用 `id` 命名文件（`tag-<id>.html`），避免 URL 编码导致 404。
- 修改模板中的站内链接请用 `url_for`，`freeze.py` 会统一重写为静态文件名。
- `og:image`、`og:url` 必须使用绝对地址（由 `SITE_URL` 环境变量注入），否则社交平台抓不到图。
- 每次导出后运行 `check_site.py` 自检；上线后运行 `check_online.py <域名>` 验收 8 项。

## 代码风格
- Python 遵守 PEP 8，4 空格缩进，函数与类写 docstring（中文即可）。
- 提交信息用前缀：`feat:` 新功能 / `fix:` 修缺陷 / `docs:` 文档 / `chore:` 杂项，一次提交只做一件事。
- 改动数据模型必须同步 `tests/` 并在本地跑通 `pytest`，禁止提交红着的测试。
