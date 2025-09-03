# 使用官方Python轻量级镜像
FROM docker.1ms.run/library/python:3.10-slim

# 设置工作目录

WORKDIR /usr/local

# 复制依赖文件并安装（如果存在requirements.txt）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 更新包索引并安装 tzdata
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata && \
    rm -rf /var/lib/apt/lists/*  # 清理缓存以减小镜像大小
# 设置时区环境变量
ENV TZ=Asia/Shanghai
ENV PYTHONPATH=/usr/local:$PYTHONPATH
# 创建时区链接
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 复制所有项目文件到容器
COPY . .

RUN sed -i 's/\r$//' /usr/local/run.sh #删除windows换行符

# 暴露应用程序端口
EXPOSE 5050
# 设置Shell脚本为可执行
RUN chmod +x /usr/local/run.sh
## 设置启动命令
#CMD ["python", "run_scripts.py"]
# 设置启动命令
CMD ["/bin/bash", "/usr/local/run.sh"]