FROM python:3.10

WORKDIR /app

# 虽然是完整版，但为了确保"豪华体验"，我们还是显式安装一套瑞士军刀
# update 是必须的，否则找不到包
RUN apt-get update && apt-get install -y \
    vim \
    net-tools \
    iputils-ping \
    dnsutils \
    htop \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY .env .
COPY the_principle_lite_zh.md .

RUN pip install --no-cache-dir -r requirements.txt

# 复制核心代码
COPY app.py .
COPY compress_memory.py .
COPY vision/ ./vision/

# 初始化空记忆
RUN touch consciousness.txt

EXPOSE 8000

CMD ["python3", "app.py", "--host", "0.0.0.0", "--port", "8000"]
