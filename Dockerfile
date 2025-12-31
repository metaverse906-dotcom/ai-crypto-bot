# Dockerfile - Multi-stage build 優化版
# 階段 1: 編譯 TA-Lib（builder）
FROM python:3.12-slim AS builder

# 安裝編譯工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 編譯 TA-Lib
WORKDIR /tmp
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xvzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    rm -rf /tmp/*

# 安裝 Python 依賴（使用 builder cache）
COPY requirements.txt /tmp/
RUN pip install --user --no-cache-dir -r /tmp/requirements.txt

# 階段 2: Runtime（最終映像）
FROM python:3.12-slim

# 只複製必要的 TA-Lib 庫文件
COPY --from=builder /usr/lib/libta_lib.* /usr/lib/
COPY --from=builder /usr/include/ta-lib /usr/include/ta-lib

# 複製 Python 套件
COPY --from=builder /root/.local /root/.local

# 設置環境變量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH

# 創建目錄
WORKDIR /app
RUN mkdir -p /app/data /app/logs

# 複製應用代碼
COPY . /app

# 創建非 root 用戶
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app
USER botuser

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# 預設命令
CMD ["python", "main.py"]