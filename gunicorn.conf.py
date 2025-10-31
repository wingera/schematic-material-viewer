# Gunicorn 配置文件

# 绑定地址和端口
bind = "0.0.0.0:5000"

# 工作进程数
workers = 2

# 工作进程类型 (使用 eventlet 支持 WebSocket)
worker_class = "eventlet"

# 每个工作进程处理的请求数后重启
max_requests = 1000
max_requests_jitter = 100

# 超时设置
timeout = 30
keepalive = 2

# 日志配置 - 使用标准输出而不是文件
accesslog = "-"
errorlog = "-"
loglevel = "info"

# 进程名称
proc_name = "schematic-materials-viewer"

# 预加载应用
preload_app = True

# 环境变量
raw_env = [
    "FLASK_ENV=production",
]

# 服务器钩子
def when_ready(server):
    server.log.info("Server is ready. Serving requests...")

def on_exit(server):
    server.log.info("Server is shutting down...")
