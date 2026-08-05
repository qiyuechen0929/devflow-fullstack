# DevFlow Fullstack - Python 工具镜像
# 提供完整的 DevFlow CLI 脚本运行环境
# 构建: docker build -t devflow-fullstack .
# 运行: docker run --rm -v $(pwd):/workspace devflow-fullstack review --mode all --dir /workspace

FROM python:3.11-slim

WORKDIR /opt/devflow

# 安装基础依赖（可选，用于 pytest 测试）
RUN pip install --no-cache-dir pytest

# 复制项目文件
COPY devflow-cli.py .
COPY devflow.bat .
COPY devflow.sh .
COPY scripts/ ./scripts/
COPY references/ ./references/
COPY CLAUDE.md .
COPY README.md .
COPY LICENSE .

# 零依赖设计，无需额外安装 Python 包
# 设置编码环境变量，避免 GBK 乱码
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8

WORKDIR /workspace

ENTRYPOINT ["python", "/opt/devflow/devflow-cli.py"]
CMD ["help"]
