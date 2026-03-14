from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler, ThrottledDTPHandler
from pyftpdlib.servers import FTPServer
import os

# 配置
FTP_ROOT = os.environ.get("FTP_ROOT", "/data/ftp")
FTP_USER = os.environ.get("FTP_USER", "admin")
FTP_PASS = os.environ.get("FTP_PASS", "admin123")
FTP_PORT = int(os.environ.get("FTP_PORT", "2121"))
MAX_CONS = int(os.environ.get("FTP_MAX_CONS", "256"))
MAX_CONS_PER_IP = int(os.environ.get("FTP_MAX_CONS_PER_IP", "5"))
PASSIVE_PORTS = range(60000, 60100)

def ensure_dir(path):
    """确保目录存在"""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        print(f"[FTP] 创建目录: {path}")

def main():
    # 确保根目录存在
    ensure_dir(FTP_ROOT)
    
    # 创建授权器
    authorizer = DummyAuthorizer()
    authorizer.add_user(FTP_USER, FTP_PASS, FTP_ROOT, perm="elradfmwMT")
    # elradfmwMT = 所有权限: 列表、读取、追加、删除、创建、修改、重命名、删除目录、创建目录
    
    # 限速处理器（防止大文件传输占满带宽）
    class CustomDTPHandler(ThrottledDTPHandler):
        read_limit = 1024 * 1024 * 10  # 10 MB/s
        write_limit = 1024 * 1024 * 10  # 10 MB/s
    
    # 创建处理器
    handler = FTPHandler
    handler.authorizer = authorizer
    handler.banner = "Welcome to LAN File Manager FTP Server"
    handler.masquerade_address = ""
    handler.passive_ports = PASSIVE_PORTS
    # handler.abstracted_fs = None  # 不要设置，使用默认值
    
    # 日志
    handler.log_prefix = '%(username)s@%(remote_ip)s'
    
    # 创建服务器
    server = FTPServer(("0.0.0.0", FTP_PORT), handler)
    server.max_cons = MAX_CONS
    server.max_cons_per_ip = MAX_CONS_PER_IP
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║           LAN File Manager FTP Server                    ║
╠══════════════════════════════════════════════════════════╣
║  监听地址: 0.0.0.0:{FTP_PORT:<5}                              ║
║  根目录:   {FTP_ROOT:<45} ║
║  用户名:   {FTP_USER:<45} ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # 启动服务器
    server.serve_forever()

if __name__ == "__main__":
    main()
