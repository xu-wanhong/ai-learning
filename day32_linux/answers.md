# Day 32 · 练习题答案

> 环境：macOS 26.5 · zsh
> 素材：用 `setup.sh` 造的（`logs/app.log` 7 行、`data/.env`、`data/req.json`）

---

## 题 1 · 查看

### 1.1 列出当前目录所有文件（含隐藏），详细信息，按时间排

```bash
$ ls -lhat
total 0
drwxr-xr-x   6 hzj  staff   192 Oct 23 19:09 .
drwxr-xr-x  21 hzj  staff   672 Oct 23 18:06 ..
drwxr-xr-x   3 hzj  staff    96 Oct 23 18:10 logs
drwxr-xr-x   4 hzj  staff   128 Oct 23 18:14 data
drwxr-xr-x   2 hzj  staff    64 Oct 23 18:07 backup
```

| 参数 | 意思 |
|---|---|
| `-l` | 详细信息 |
| `-a` | **含隐藏文件**（`.` 开头的） |
| `-h` | 大小给人看 |
| `-t` | **按修改时间排**（新的在前） |

### 1.2 数 `logs/app.log` 有几行

```bash
$ wc -l logs/app.log
       7 logs/app.log
```

### 1.3 打印最后 2 行

```bash
$ tail -2 logs/app.log
2026-10-03 10:06 ERROR 数据库连接失败
2026-10-03 10:07 WARN  重试第1次
```

---

## 题 2 · 查找

### 2.1 找出所有 `.log` 文件

```bash
$ find . -name "*.log" -type f
./logs/app.log
./logs/old.log
```

> **`-type f`** 保证只找**文件**（防止有名字叫 `xx.log` 的目录）。

### 2.2 找出所有目录

```bash
$ find . -type d
.
./logs
./data
./backup
```

### 2.3 找出 `data/` 下的隐藏文件

```bash
$ find data -name ".*" -type f
data/.env
```

> `.*` 匹配 `.` 开头的名字。另一种写法：`ls -a data/`

---

## 题 3 · 找内容

### 3.1 打印所有 ERROR 行

```bash
$ grep ERROR logs/app.log
2026-10-03 10:04 ERROR 连接超时 timeout=30
2026-10-03 10:06 ERROR 数据库连接失败
```

### 3.2 数出 ERROR 有几条

```bash
$ grep -c ERROR logs/app.log
2
```

### 3.3 打印 ERROR 行并带前后各 1 行

```bash
$ grep -C1 ERROR logs/app.log
2026-10-03 10:03 INFO  请求成功 id=3
2026-10-03 10:04 ERROR 连接超时 timeout=30
2026-10-03 10:05 INFO  请求成功 id=5
2026-10-03 10:06 ERROR 数据库连接失败
2026-10-03 10:07 WARN  重试第1次
```

> `-C1` = **C**ontext 1 行。`-A1` 只看后面，`-B1` 只看前面。

### 3.4 统计 INFO / WARN / ERROR 各几条 ⭐

```bash
$ awk '{print $3}' logs/app.log | sort | uniq -c | sort -rn
   4 INFO
   2 ERROR
   1 WARN
```

**拆解**：

| 步骤 | 做什么 | 结果 |
|---|---|---|
| `awk '{print $3}'` | 每行取第 3 列（级别） | `INFO INFO INFO ERROR INFO ERROR WARN` |
| `sort` | 排序（**`uniq` 只合并相邻的**，所以必须先排） | `ERROR ERROR INFO INFO INFO INFO WARN` |
| `uniq -c` | 去重 + 计数 | `2 ERROR / 4 INFO / 1 WARN` |
| `sort -rn` | 按数量**倒序** | `4 INFO / 2 ERROR / 1 WARN` |

**另一种写法（更稳）**：

```bash
$ grep -oE 'INFO|WARN|ERROR' logs/app.log | sort | uniq -c
   2 ERROR
   4 INFO
   1 WARN
```

> `grep -o` 只提取**匹配到的部分**，不依赖"级别在第 3 列"。日志格式变了也照样能用。

---

## 题 4 · 文本处理

### 4.1 用 `awk` 只打印第 4 列

```bash
$ awk '{print $4}' logs/app.log
请求成功
请求成功
请求成功
连接超时
请求成功
数据库连接失败
重试第1次
```

### 4.2 取出所有日志级别，排序去重并计数

```bash
$ awk '{print $3}' logs/app.log | sort | uniq -c
   2 ERROR
   4 INFO
   1 WARN
```

（和 3.4 是同一条链，去掉最后那个 `sort -rn` 就是按字母序。）

### 4.3 用 `find` + `xargs` 统计所有 `.log` 的行数 ⭐

```bash
$ find . -name "*.log" -type f | xargs wc -l
       0 ./logs/old.log
       7 ./logs/app.log
       7 total
```

**拆解**：

| 步骤 | 做什么 |
|---|---|
| `find . -name "*.log" -type f` | 找出两个文件 → `./logs/app.log`、`./logs/old.log` |
| **`\| xargs`** | **把这两行"文本"变成 `wc -l` 的"参数"** |
| `wc -l` | 统计行数 |

**等价于手写**：

```bash
wc -l ./logs/app.log ./logs/old.log
```

**跑出来的 `7 total` 是 `wc` 自动加的总计行。**

**只要总数**：

```bash
$ find . -name "*.log" -type f | xargs wc -l | tail -1
       7 total
```

**⚠️ 文件名可能带空格时，必须用 `-print0` + `xargs -0`**：

```bash
find . -name "*.log" -type f -print0 | xargs -0 wc -l
```

---

## 题 5 · 权限

### 5.1 把 `data/.env` 设成只有我能读写

```bash
$ chmod 600 data/.env
$ ls -l data/.env
-rw-------@ 1 hzj  staff  11 Oct 23 19:00 data/.env
```

**逐字符读**：

```
-  rw-  ---  ---
│   │    │    └── other（其他人）：什么都不能
│   │    └─────── group（同组）：什么都不能
│   └──────────── user（你）：能读能写
└──────────────── 普通文件
```

**`600` 的算法**：`6 = 4(r) + 2(w)`，`0 = 无`，`0 = 无`。

> **效果**：别人连 `cat data/.env` 都不行。

### 5.2 让 `hello.sh` 能直接跑

```bash
$ printf '#!/bin/bash\necho "hello linux"\n' > hello.sh
$ cat hello.sh
#!/bin/bash
echo "hello linux"

$ ls -l hello.sh
-rw-r--r--@ 1 hzj  staff  31 Oct 23 19:00 hello.sh        ← 没有 x

$ chmod +x hello.sh
$ ls -l hello.sh
-rwxr-xr-x@ 1 hzj  staff  31 Oct 23 19:00 hello.sh        ← 有 x 了

$ ./hello.sh
hello linux
```

**`#!` 那行叫 shebang** —— 告诉系统"用哪个解释器跑这个文件"。

**`./` 的意思**：在当前目录找这个文件。只写 `hello.sh` 不行，因为系统的 `PATH` 不包含 `.`（当前目录）—— **这是安全设计**。

### 5.3 去掉执行位 → 看报错 → 加回来 ⭐

```bash
$ chmod -x hello.sh
$ ls -l hello.sh
-rw-r--r--@ 1 hzj  staff  31 Oct 23 19:00 hello.sh

$ ./hello.sh
bash: ./hello.sh: Permission denied
             ↑ 这就是"没有执行位"的报错

$ bash hello.sh
hello linux
       ↑ 显式指定解释器，【不需要】x 位

$ chmod +x hello.sh
$ ./hello.sh
hello linux
```

**两种跑法的区别**：

| 跑法 | 需要 `x` 吗 | 用哪个解释器 |
|---|---|---|
| `./hello.sh` | ✅ **需要** | 看 shebang（`#!/bin/bash`） |
| `bash hello.sh` | ❌ 不需要 | 你指定的 |

### 补充：`chmod +x` vs `chmod 700`

```bash
chmod +x hello.sh     # → -rwxr-xr-x   【所有人】都能执行
chmod 700 hello.sh    # → -rwx------   【只有你】能执行
```

| 写法 | 行为 |
|---|---|
| `chmod +x` | **在现有权限上加**执行位（644 → 755） |
| `chmod 700` | **直接设成这个值**（不管原来是什么） |

---

## 踩的坑

| # | 现象 | 原因 | 正确做法 |
|---|---|---|---|
| 1 | `mkdir a/b/c` 报 `No such file or directory` | 没加 `-p`，中间层不存在 | `mkdir -p a/b/c` |
| 2 | 循环写日志，最后只剩一行 | 用了 `>` 覆盖 | 用 `>>` **追加** |
| 3 | `uniq -c` 出来的计数乱七八糟 | 没先 `sort`（它只合并**相邻**重复行） | `sort \| uniq -c` |
| 4 | `ls` 看不到 `.env` | `.` 开头是隐藏文件 | `ls -a` |
| 5 | `./hello.sh` 报 `Permission denied` | 没有 `x` 位 | `chmod +x` |
| 6 | `cd` 进不去自己建的目录 | 目录权限设成 `644`，**没有 `x`** | 目录用 `755` |
| 7 | `json` 写进文件后 `$` 丢了 | 用了双引号，变量被替换 | 用**单引号** `'...'` |
| 8 | `find \| xargs` 文件名带空格时出错 | `xargs` 按空格分参数 | `-print0 \| xargs -0` |

---

## macOS 和 Linux 的差异（Day 32 相关）

| 事情 | macOS | Linux |
|---|---|---|
| `sed -i` 原地改 | **必须** `sed -i '' 's/a/b/' f` | `sed -i 's/a/b/' f` |
| `ls --version` | ❌ 不支持 | ✅ |
| `grep -P` | ❌ 不支持 | ✅ |
| `date -d "yesterday"` | ❌ | ✅ |
| `readlink -f` | ❌ | ✅ |
| `find -printf` | ❌ | ✅ |

---

## 还没搞懂的

1. `awk` 除了 `{print $N}` 还能干什么？什么时候值得学它而不是用 Python？
2. `sed` 的 `-i ''` 为什么 macOS 要多一个空串？
3. `xargs` 和 `find -exec` 有什么区别？什么时候用哪个？
4. 文件权限里的「同组（group）」在实际项目里怎么用？我好像一直是唯一的用户。
