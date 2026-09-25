import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DELAY = 1.0
PORT = 8765


class SlowHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        time.sleep(DELAY)
        body = f"hello from {self.path}\n".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


print(f"慢服务器已启动：http://127.0.0.1:{PORT}   每个请求睡 {DELAY}s")
print("按 Ctrl+C 停止")
ThreadingHTTPServer(("127.0.0.1", PORT), SlowHandler).serve_forever()