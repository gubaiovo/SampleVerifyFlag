# Dockerfile

# 1. 使用 Python 3.13 轻量版镜像 (与你本地开发环境一致)
FROM python:3.13-slim

# 2. 设置容器内工作目录
WORKDIR /app

# 3. 安装 uv 工具
RUN pip install uv -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 复制依赖锁定文件
# 我们只需要复制这两个文件来安装依赖，利用 Docker 缓存层
COPY pyproject.toml uv.lock ./

# 5. 使用 uv 安装依赖
# --system: 直接安装到系统 Python 环境，不创建虚拟环境 (Docker 中通常不需要 venv)
# --no-cache: 减小镜像体积
RUN uv pip sync uv.lock --system --no-cache

# 6. 复制源代码
# 将 src 文件夹复制到 /app/src
COPY src/ /app/src/

# 7. 预创建挂载点目录
# 这一步是为了确保权限正确，虽然 Docker 挂载时会自动创建，但显式创建更安全
RUN mkdir -p /app/data/users \
             /app/data/challenge/zips \
             /app/data/challenge/exps

# 8. 暴露端口
EXPOSE 5000

# 9. 启动命令
CMD ["python", "src/app.py"]