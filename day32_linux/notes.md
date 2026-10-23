# Day 32 · Linux 文件、文本、权限

2026-10-23 · macOS 26.5 · zsh

> **目标**：看得懂文件、找得到内容、改得对权限。
> **三天总目标**：把自己的服务在服务器上跑起来、看得懂它、出问题能查。

---

## 一、命令速查

### 导航

```bash
pwd                         # 现在在哪
cd ~/dev/ai-learning        # 进目录（~ = 家目录）
cd ..                       # 上一级
cd -                        # 回上一个目录
cd                          # 回家目录
ls -lhat                    # 详细 + 隐藏 + 人读 + 按时间
```

| `ls` 参数 | 作用 |
|---|---|
| `-l` | 详细信息 |
| `-a` | 含隐藏文件 |
| `-h` | 大小给人看 |
| `-t` | 按时间排 |
| `-1` | 一行一个 |

### 增删改

```bash
mkdir -p a/b/c      # 建多层（-p 必需，不然中间层不存在会报错）
touch f.txt         # 建空文件
cp 源 目标          # 复制文件
cp -r 源 目标       # 复制目录（目录必须 -r）
mv 源 目标          # 移动 / 改名（同一个命令）
rm 文件             # 删文件
rm -r 目录          # 删目录
rm -rf 目录         # ⚠️ 强制删，没有回收站
```

> ⚠️ **`rm -rf` 前先 `ls` 一遍目标。** `rm -rf ~/` 会毁机器。

### 看内容

```bash
cat f               # 全打出来（小文件）
head -n 20 f        # 前 20 行
tail -n 20 f        # 后 20 行
tail -f f           # 实时跟（Ctrl+C 退出）
less f              # 分页看（q 退出，/ 搜索）
wc -l f             # 数行数
sed -n '2,3p' f     # 只看第 2~3 行
```

### `find` —— 找文件

```bash
find . -name "*.log"                    # 按名字
find . -name "*.log" -type f            # 只找文件
find . -type d                          # 只找目录
find . -name "*.log" -mtime -1          # 1 天内改过的
find . -size +10M                       # 大于 10M
find . -name "*.log" ! -path "./venv/*" # 排除
find . -name "*.log" -print0 | xargs -0 wc -l   # 文件名可能有空格时
```

### `grep` —— 找内容

```bash
grep ERROR app.log              # 含 ERROR 的行
grep -i error app.log           # 忽略大小写
grep -v ERROR app.log           # 不含 ERROR 的行
grep -n ERROR app.log           # 带行号
grep -c ERROR app.log           # 只数条数
grep -r "关键词" .              # ⭐ 递归整个目录
grep -rl ERROR .                # 只输出文件名
grep -C1 ERROR app.log          # 带前后各 1 行
grep -E "ERROR|WARN" app.log    # 正则
grep -oE 'INFO|WARN|ERROR' app.log   # 只输出匹配的部分
```

**你以后最常用的**：`grep -rn "函数名" .` —— 在项目里找定义。

### 管道与文本处理

```bash
cmd1 | cmd2                     # 上一条的输出 = 下一条的输入
awk '{print $1}' f              # 取第 N 列（默认空格分隔）
sort                            # 排序
sort -rn                        # 数字倒序
uniq -c                         # 去重 + 计数（必须【先 sort】）
sed 's/a/b/g' f                 # 替换
cut -d: -f2                     # 按分隔符取列
tr 'A-Z' 'a-z'                  # 字符转换
xargs                           # 文本 → 命令参数
```

**统计日志级别的标准链**：

```bash
awk '{print $3}' app.log | sort | uniq -c | sort -rn
```

**为什么 `uniq -c` 前必须 `sort`**：`uniq` 只合并**相邻**的重复行。

### 权限

```bash
chmod 644 file      # 普通文件
chmod 600 .env      # 密钥（只有我能读）
chmod 755 dir/      # 目录、脚本
chmod +x script.sh  # 加执行位（644 → 755）
chmod -x script.sh  # 去掉执行位
chown user:group f  # 改属主（要 sudo）
```

---

## 二、`ls -l` 那一串怎么读

```
-rw-r--r--@ 1 hzj staff 3 Oct 23 12:39 f.txt
│└┬┘└┬┘└┬┘
│ │  │  └── other（其他人）
│ │  └───── group（同组）
│ └──────── user（属主）
└────────── 类型：- 文件  d 目录  l 软链接
```

**数字怎么算**：**`r=4` `w=2` `x=1`**

| 数字 | 结果 | 给谁用 |
|---|---|---|
| **644** | `rw-r--r--` | 普通文件（代码、配置、日志） |
| **600** | `rw-------` | **密钥、`.env`** ⭐ |
| **755** | `rwxr-xr-x` | **目录、脚本** |
| 700 | `rwx------` | 私有目录 |
| 777 | `rwxrwxrwx` | ❌ 别用 |

**⚠️ 目录的 `x` 位特殊**：

| 对文件 | 对目录 |
|---|---|
| `x` = 能不能执行 | **`x` = 能不能 `cd` 进去** |

**`chmod 644 目录` 会让它"能看不能进"** —— 目录一定用 `755`。

---

## 三、`.env` 的特殊之处

**「`.env` 特殊」来自两件事，都不是操作系统给的待遇：**

| # | 是什么 |
|---|---|
| **1** | **`.` 开头 = 隐藏文件**（`ls` 看不到，要 `ls -a`） |
| **2** | **这个名字被一堆工具默认认**：`python-dotenv`、`uvicorn --env-file`、Docker Compose、Next.js |

`file .env` 返回 `ASCII text` —— **系统只当它是普通文本文件**。

**里面装什么**：不该写进代码的东西

```bash
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...
DEBUG=false
```

**三个文件的关系**：

| 文件 | 进 git？ | 内容 |
|---|---|---|
| `.env` | ❌ **绝不** | 真实密钥 |
| `.env.example` | ✅ 可以 | 只有变量名，值留空 |
| `.gitignore` | ✅ 必须 | 里面要有 `.env` 这一行 |

> **⚠️ 密钥进了 git，就算后来删掉，`git log` 历史里还在 = 已公开。**

---

## 四、踩的坑

| # | 现象 | 原因 | 正确做法 |
|---|---|---|---|
| 1 | `mkdir a/b/c` 报 `No such file or directory` | 没加 `-p` | `mkdir -p a/b/c` |
| 2 | 循环写日志，最后只剩一行 | 用了 `>` 覆盖 | `>>` **追加** |
| 3 | `uniq -c` 计数乱 | 没先 `sort` | `sort \| uniq -c` |
| 4 | `ls` 看不到 `.env` | `.` 开头是隐藏 | `ls -a` |
| 5 | `./hello.sh` 报 `Permission denied` | 没有 `x` 位 | `chmod +x` |
| 6 | `cd` 进不去自己建的目录 | 目录权限 `644` 没 `x` | 目录用 `755` |
| 7 | JSON 写进文件后 `$` 丢了 | 双引号会替换变量 | 用**单引号** `'...'` |
| 8 | `find \| xargs` 文件名带空格出错 | `xargs` 按空格分参数 | `-print0 \| xargs -0` |

### `>` 和 `>>` 的区别（第一大坑）

| 符号 | 行为 | 什么时候用 |
|---|---|---|
| **`>`** | **覆盖**（先清空） | 第一次建文件 |
| **`>>`** | **追加** | **往日志里加内容** |

实测：循环里用 `>` → 只剩最后一行；用 `>>` → 三行都在。

### 引号的区别

| 引号 | 里面的 `$变量` |
|---|---|
| `"..."` 双引号 | **会**被替换 |
| `'...'` 单引号 | **原样保留** |

**写 JSON / 正则 / 代码 → 用单引号。**

---

## 五、macOS 和 Linux 的差异

| 事情 | macOS（BSD） | Linux（GNU） |
|---|---|---|
| **`sed -i` 原地改** | **必须** `sed -i '' 's/a/b/' f` | `sed -i 's/a/b/' f` |
| `ls --version` | ❌ | ✅ |
| `grep -P` | ❌ | ✅ |
| `date -d "yesterday"` | ❌ | ✅ |
| `readlink -f` | ❌ | ✅ |
| `find -printf` | ❌ | ✅ |
| **看端口** | `lsof -i :8000` / `netstat` | **`ss -tlnp`**（Day 33） |

---

## 六、还没搞懂的

1. `awk` 除了 `{print $N}` 还能干什么？什么时候值得学它而不是用 Python？
2. `sed -i ''` 为什么 macOS 要多一个空串？
3. `xargs` 和 `find -exec` 有什么区别？什么时候用哪个？
4. 文件权限里的「同组（group）」在实际项目里怎么用？我好像一直是唯一的用户。
