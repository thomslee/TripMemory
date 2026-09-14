FROM python:3.12-slim

WORKDIR /app

# apt 使用国内镜像源（腾讯云，避免 Debian 官方源超时）
RUN sed -i 's|deb.debian.org|mirrors.cloud.tencent.com|g' /etc/apt/sources.list.d/debian.sources

# HEIC 照片解码依赖（pillow-heif 需要 libheif 运行库）
RUN apt-get update && apt-get install -y --no-install-recommends libheif1 \
    && rm -rf /var/lib/apt/lists/*

# 使用清华pip源加速
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

EXPOSE 8003

CMD ["python", "run.py"]
