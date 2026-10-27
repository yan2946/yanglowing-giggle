FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
EXPOSE 5001
# 经 flask CLI 启动（加载 app.py 模块级 app 实例），避开 __main__ 中的 debug 模式
CMD ["python3", "-m", "flask", "--app", "app", "run", "--host=0.0.0.0", "--port=5001"]