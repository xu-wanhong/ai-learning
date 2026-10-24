# Day 33 · 练习题答案

> 环境：macOS 26.5 · zsh
> 示例端口：8899（避开 8000，防止跟别的服务撞）

---

## 题 1 · 起服务 + 全套检查

### 1.1 后台起一个服务占住 8899

```bash
$ python3 -m http.server 8899 &
[1] 42402
Serving HTTP on :: port 8899 (http://[::]:8899/) ...
```

> **看到 `Serving HTTP on ... port 8899` 才算起来。**
> **如果看到 `exit 127` / `command not found`，是命令打错了**（我实际写错过 `pthon3`）。

### 1.2 用 `pgrep -fl` 找到它

```bash
$ pgrep -fl "http.server 8899"
42402 /Library/.../Python -m http.server 8899
└─┬─┘ └──────────────┬──────────────────────┘
 PID          完整的启动命令
```

**`-f`** = 匹配**完整命令行**（不只是进程名）；**`-l`** = 显示命令行。

### 1.3 用 `lsof` 证明 8899 是它占的

```bash
$ lsof -i :8899 -P -n
COMMAND   PID USER   FD   TYPE ... NAME
Python  42402  hzj    4u  IPv6 ... TCP *:8899 (LISTEN)
                                      └──┬──┘ └──┬──┘
                                   端口 8899   正在监听
```

**`*`** = 绑所有网卡（`python3 -m http.server` 不加 `--bind` 时默认如此）。

### 1.4 用 `curl` 拿到状态码 200

```bash
$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8899/
200
```

| 参数 | 作用 |
|---|---|
| `-s` | 静默 |
| `-o /dev/null` | 丢弃响应体 |
| `-w "%{http_code}\n"` | 只输出状态码 |

### 1.5 用一条命令拿到 PID 并 kill

```bash
$ kill $(lsof -ti :8899)
```

**拆解**：

| 部分 | 作用 |
|---|---|
| `lsof -ti :8899` | **只输出 PID**（`-t` = terse） |
| `$(...)` | 命令替换 —— 把输出当成参数 |
| `kill` | 杀它 |

**等价于**：

```bash
PID=$(lsof -ti :8899)
kill $PID
```

### 1.6 再查，证明端口释放

```bash
$ lsof -i :8899 -P -n
（没有输出 —— 端口释放了 ✅）
```

---

## 题 2 · 端口占用报错

### 2.1 先占住 8899

```bash
$ python3 -m http.server 8899 &
```

### 2.2 再起一次 → 报错原文

```bash
$ python3 -m http.server 8899
Traceback (most recent call last):
  File "<frozen runpy>", line 203, in _run_module_as_main
  ...
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/socketserver.py", line 473, in server_bind
    self.socket.bind(self.server_address)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
OSError: [Errno 48] Address already in use
```

> **`[Errno 48] Address already in use`**
> **字面意思："这个门牌号已经被用了。"**

### 2.3 用 `lsof` 找出是谁占的

```bash
$ lsof -i :8899 -P -n
COMMAND   PID USER   FD   TYPE ... NAME
Python  42402  hzj    4u  IPv6 ... TCP *:8899 (LISTEN)
            └─┬─┘
          就是它
```

### 2.4 杀掉，再启动成功

```bash
$ kill $(lsof -ti :8899)
$ sleep 1
$ python3 -m http.server 8899 &
Serving HTTP on :: port 8899 (http://[::]:8899/) ...      ← 起来了 ✅
```

---

## 题 3 · 日志分析

### 3.1 造 20 行日志（含 3 条 ERROR、2 条 WARN）

```bash
{
  echo "2026-10-23 10:01 INFO  请求成功 id=1"
  echo "2026-10-23 10:02 INFO  请求成功 id=2"
  echo "2026-10-23 10:03 WARN  响应慢 800ms"
  echo "2026-10-23 10:04 INFO  请求成功 id=4"
  echo "2026-10-23 10:05 ERROR 连接超时 timeout=30"
  echo "2026-10-23 10:06 INFO  请求成功 id=6"
  echo "2026-10-23 10:07 INFO  请求成功 id=7"
  echo "2026-10-23 10:08 INFO  请求成功 id=8"
  echo "2026-10-23 10:09 INFO  请求成功 id=9"
  echo "2026-10-23 10:10 INFO  请求成功 id=10"
  echo "2026-10-23 10:11 INFO  请求成功 id=11"
  echo "2026-10-23 10:12 WARN  重试第1次"
  echo "2026-10-23 10:13 INFO  请求成功 id=13"
  echo "2026-10-23 10:14 INFO  请求成功 id=14"
  echo "2026-10-23 10:15 INFO  请求成功 id=15"
  echo "2026-10-23 10:16 INFO  请求成功 id=16"
  echo "2026-10-23 10:17 ERROR 数据库连接失败"
  echo "2026-10-23 10:18 INFO  请求成功 id=18"
  echo "2026-10-23 10:19 ERROR 上游返回 502"
  echo "2026-10-23 10:20 INFO  请求成功 id=20"
} > app.log
```

### 3.2 两个终端：`tail -f` + 追加

**终端 A**：

```bash
tail -f app.log
```

**终端 B**：

```bash
echo "2026-10-23 10:21 ERROR 新错误" >> app.log
```

**终端 A 会立刻跳出那一行** —— 这就是 `tail -f` 的作用（`-f` = follow）。

> **`Ctrl + C` 退出 `tail -f`。**

### 3.3 一条命令统计 ERROR / WARN 各几条

```bash
$ grep -oE 'INFO|WARN|ERROR' app.log | sort | uniq -c | sort -rn
  15 INFO
   3 ERROR
   2 WARN
```

**拆解**：

| 步骤 | 作用 |
|---|---|
| `grep -oE 'A\|B\|C'` | **只提取匹配到的级别**（`-o`），不输出整行 |
| `sort` | 排序（`uniq` 只合并**相邻**重复行） |
| `uniq -c` | 去重 + **计数** |
| `sort -rn` | 按数量**倒序** |

**另一种（按列）**：

```bash
$ awk '{print $3}' app.log | sort | uniq -c
```

> `awk` 版本假设"级别永远在第 3 列"；`grep -o` 版本只看内容，**格式变了也能用**。

### 3.4 找最后 30 行里的错误 ⭐

```bash
tail -30 app.log | grep -i error
```

**输出**：

```
2026-10-23 10:05 ERROR 连接超时 timeout=30
2026-10-23 10:17 ERROR 数据库连接失败
2026-10-23 10:19 ERROR 上游返回 502
```

**为什么先 `tail -30`**：日志可能几十万行，`grep` 全文会把**三天前的错误**也翻出来。
**排查"刚才这次失败"，只看最近的。**

**两种顺序的区别**：

| 写法 | 意思 |
|---|---|
| **`tail -30 \| grep`** | 只看最后 30 行，在里面找 → **看"最近的记录"** |
| `grep \| tail -20` | 全文找，取最后 20 条 → **看"最近 N 条错误"** |

**更多变化**：

```bash
tail -100 app.log | grep -i "error\|exception\|traceback"
tail -50 app.log | grep -i -A2 error        # 错误 + 后 2 行（看堆栈）
```

---

## 题 4 · curl 全套

> 我用一个自建的小服务验证的（支持 GET / POST / 回显 header）。
> 端点：`/health`（200）、`/slow`（睡 0.3s）、`/nope`（404）、POST `/chat`（回显 JSON + header）

### 4.1 状态码

```bash
$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/health
200
```

**这是最常用的三件套**：`-s`（静默）+ `-o /dev/null`（丢响应体）+ `-w "%{http_code}"`（只输出状态码）。

### 4.2 响应耗时

```bash
$ curl -s -o /dev/null -w "%{time_total}s\n" http://127.0.0.1:8000/slow
0.305990s
```

**服务端故意 `sleep 0.3`，所以耗时 ≈ 0.3s。**

**一次拿多个指标**：

```bash
$ curl -s -o /dev/null -w "状态=%{http_code} 耗时=%{time_total}s\n" http://127.0.0.1:8000/health
状态=200 耗时=0.0006s
```

### 4.3 响应体前 40 个字符

```bash
$ curl -s http://127.0.0.1:8000/health | head -c 40
{"status": "ok", "service": "demo"}
```

**`head -c 40`** = 取前 40 个**字节**（`-c` = character/bytes）。

> 这次**不要** `-o /dev/null` —— 就是要看内容。

### 4.4 POST + JSON

```bash
$ curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{"model":"gpt","q":"你好"}' \
    http://127.0.0.1:8000/chat
{"received": {"model": "gpt", "q": "你好"}, "auth": "(无)", "content_type": "application/json"}
```

| 参数 | 作用 |
|---|---|
| `-X POST` | 指定方法 |
| **`-H "Content-Type: application/json"`** | 告诉服务端"我发的是 JSON" |
| `-d '{...}'` | 请求体 |

**⚠️ `-d` 外面必须用单引号**：JSON 里有双引号，用双引号包会冲突；而且单引号能防止 `$` 被 shell 吃掉。

### 4.5 带 `Authorization` 头

```bash
$ curl -s -X POST \
    -H "Authorization: Bearer sk-abc123" \
    -H "Content-Type: application/json" \
    -d '{}' \
    http://127.0.0.1:8000/chat
{"received": {}, "auth": "Bearer sk-abc123", "content_type": "application/json"}
```

**`auth` 字段证明 header 确实传到了服务端。**

**多个 header 就写多个 `-H`。**

> **这就是调 LLM API 的标准姿势**：
> ```bash
> curl -s https://api.openai.com/v1/chat/completions \
>   -H "Authorization: Bearer $OPENAI_API_KEY" \
>   -H "Content-Type: application/json" \
>   -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}]}'
> ```

### 附加 · 三种状态码对照

```bash
$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/health
200      ← 门通了，正常

$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/nope
404      ← 门通了，路径不对

$ curl -s -o /dev/null -w "%{http_code}\n" --max-time 2 http://127.0.0.1:9999/
000      ← 连不上（这个端口没人）
```

> **`000` 不是 HTTP 状态码**，是 **curl 自己**表示"我没连上"。

---

## 题 5 · 排障演练（4 种故障）

### 故障 A · 端口被占用

**现象**：

```
OSError: [Errno 48] Address already in use
```

**我怎么查**：

```bash
$ pgrep -fl "http.server 8899"
42875 /Library/.../Python -m http.server 8899          ← 进程在

$ lsof -i :8899 -P -n
COMMAND   PID USER ... NAME
Python  42875  hzj ... TCP *:8899 (LISTEN)             ← 门被占了
```

**根因**：8899 号门已经被 PID 42875 占着。
**解法**：`kill $(lsof -ti :8899)`，或者换个端口。

---

### 故障 B · 绑了 `127.0.0.1`

**现象**：本机能访问，**别人访问不了**。

**我怎么查**：

```bash
$ lsof -i :8899 -P -n
COMMAND   PID USER ... NAME
Python  42832  hzj ... TCP 127.0.0.1:8899 (LISTEN)
                          └────┬────┘
                       只绑本机 ← 问题在这
```

**对比**：

```bash
$ python3 -m http.server 8899 --bind 0.0.0.0 &
$ lsof -i :8899 -P -n
Python  42841  hzj ... TCP *:8899 (LISTEN)             ← 所有网卡
```

**根因**：`127.0.0.1` 只有本机能连；要外部能访问，绑 `0.0.0.0`。

> **这是部署时最经典的坑**：本地好好的，上服务器就访问不了。

---

### 故障 C · 代码有语法错误

**现象**：服务起来就死。

**我怎么查**：

```bash
$ pgrep -fl bad.py
（没输出 —— 进程已经死了）

$ lsof -i :8899 -P -n
（也没有 —— 它根本没绑端口）

$ cat bad.log
  File "bad.py", line 2
    this is not valid python
                       ^^^^^^
SyntaxError: invalid syntax
```

**根因**：语法错误，启动就崩。**日志第一行就是答案。**

---

### 故障 D · 忘了 `2>&1` ⭐

**现象**：**日志文件是空的，完全不知道出了什么事。**

**我怎么查**：

```bash
$ nohup python3 bad.py > bad2.log &
$ cat bad2.log
（空的！什么都没有）
```

**对比：加上 `2>&1` 再跑**：

```bash
$ nohup python3 bad.py > bad3.log 2>&1 &
$ cat bad3.log
  File "bad.py", line 2
    this is not valid python
SyntaxError: invalid syntax
```

**根因**：

| 编号 | 名字 | 是什么 |
|---|---|---|
| `1` | stdout | **正常输出** |
| `2` | stderr | **报错** |

**`> file` 只接了 `1`。报错走 `2`，跑到终端去了（或者丢了）。**
**`2>&1` = "把 `2` 也指到 `1` 指向的地方"。**

> **生产上永远写**：
> ```bash
> nohup 命令 > app.log 2>&1 &
> ```

---

## 踩的坑

| # | 现象 | 原因 | 正确做法 |
|---|---|---|---|
| 1 | `lsof: unacceptable port specification in: -i :` | 冒号后面没写端口号 | `lsof -i :8000` |
| 2 | `lsof: illegal process ID: -n` | **大小写错了**：`-p` 是进程，`-P` 是端口 | `lsof -i :8000 -P -n` |
| 3 | `lsof -i :8000` 没输出 | 服务没起 / 已死 | 先 `pgrep -fl` 查进程 |
| 4 | `zsh: command not found: pthon3` + `exit 127` | **命令拼写错**（少了 y） | `which python3` 验证 |
| 5 | `[1] + exit 127` | 后台任务立刻死了 | 看那个退出码，别急着查端口 |
| 6 | `Serving HTTP` 没出现就查端口 | 服务还没绑上端口 | **先 `sleep 1`** |
| 7 | 日志文件是空的 | 忘了 `2>&1` | `> app.log 2>&1` |
| 8 | 本机能访问、别人不能 | 绑了 `127.0.0.1` | 绑 `0.0.0.0` |
| 9 | 端口号显示成 `irdmi` | `lsof` 把 8000 翻译成服务名 | 加 `-P` |

---

## macOS 和 Linux 的差异（Day 33 相关）

| 事情 | macOS | Linux |
|---|---|---|
| **看端口监听** | `lsof -i :8000 -P -n` 或 `netstat -an \| grep LISTEN` | **`ss -tlnp`** |
| `ss` 命令 | ❌ 没有 | ✅ |
| `lsof -P` | ✅ | ✅（一样） |
| 看进程 | `ps aux` / `pgrep -fl` | 一样 |
| `--bind` | 一样 | 一样 |

**Linux 的 `ss` 用法**：

```bash
ss -tlnp                 # 所有 TCP 监听 + 进程
ss -tlnp | grep 8899
```

| 参数 | 意思 |
|---|---|
| `-t` | TCP |
| `-l` | 只看 LISTEN |
| `-n` | 不解析名字 |
| `-p` | 显示进程 |

---

## 还没搞懂的

1. `ESTABLISHED` 的连接很多（比如上千）说明什么？怎么统计？
2. `TIME_WAIT` 状态是什么？为什么会有很多？
3. 服务在前面加 nginx 之后，`lsof` 看到的是 nginx 还是我的服务？
4. 防火墙（`iptables` / `ufw`）挡住的连接，`lsof` 能看出来吗？
