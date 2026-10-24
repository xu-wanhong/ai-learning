# Day 34 · 让程序在后台一直跑

> 环境：macOS 26.5 · zsh
> 今天只解决一个问题：**"程序要一直跑着，但我不想一直盯着终端。"**

---

## 练习：四步对比

### 准备

```bash
cat > app.py <<'END'
import time
print("服务启动了")
raise ValueError("出错了")
END
```

验证：

```bash
$ cat app.py
import time
print("服务启动了")
raise ValueError("出错了")
```

---

### 第 1 步 · 直接跑（对照组）

```bash
$ python3 app.py
服务启动了
Traceback (most recent call last):
  File "app.py", line 3, in <module>
    raise ValueError("出错了")
ValueError: 出错了
```

**正常消息和报错都在屏幕上。关掉终端，全没了。**

---

### 第 2 步 · `> a.log`（只存正常消息）

```bash
$ python3 app.py > a.log
Traceback (most recent call last):
  File "/Users/hzj/app.py", line 3, in <module>
    raise ValueError("出错了")
ValueError: 出错了
```

> ⚠️ **注意这一段 Traceback 出现在【终端】上，不在 a.log 里。**

```bash
$ cat a.log
服务启动了
```

**结论**：

| 位置 | 内容 |
|---|---|
| 终端 | **Traceback**（报错） |
| `a.log` | **只有 "服务启动了"**（正常消息） |

**`>` 只接了管道 1，报错（管道 2）仍然往终端去。**

---

### 第 3 步 · `> b.log 2>&1`（报错也存进来）

```bash
$ python3 app.py > b.log 2>&1
```

**终端上一片空白 ✅**

```bash
$ cat b.log
服务启动了
Traceback (most recent call last):
  File "/Users/hzj/app.py", line 3, in <module>
    raise ValueError("出错了")
ValueError: 出错了
```

**正常消息 + 报错，全在文件里。**

---

### 第 4 步 · `nohup ... &`（后台 + 断终端不死）

```bash
$ nohup python3 app.py > c.log 2>&1 &
[1] 43622
[1]  + exit 1     nohup python3 app.py > c.log 2>&1 &
```

**终端立刻还给你了 ✅**

```bash
$ cat c.log
服务启动了
Traceback (most recent call last):
  File "/Users/hzj/app.py", line 3, in <module>
    raise ValueError("出错了")
ValueError: 出错了
```

**和 `b.log` 一模一样。**

---

## 四步对比表

| 写法 | 终端被占住？ | 关终端会死？ | 正常消息 | 报错 |
|---|---|---|---|---|
| `python3 app.py` | ✅ 占住 | ✅ 死 | 终端 | **终端** |
| `python3 app.py > a.log` | ✅ 占住 | ✅ 死 | **a.log** | **终端（丢了）** |
| `python3 app.py > b.log 2>&1` | ✅ 占住 | ✅ 死 | **b.log** | **b.log** |
| **`nohup python3 app.py > c.log 2>&1 &`** | ❌ **不占** | ❌ **不死** | **c.log** | **c.log** |

---

## 关于 `exit 1`

```
[1]  + exit 1     nohup python3 app.py > c.log 2>&1 &
        └──┬──┘
      退出码 1
```

**`exit 1` 说的是"程序失败了"，不是"nohup 失败了"。**

`nohup` 成功做到了三件事：

- ✅ 把程序放到后台
- ✅ 断开终端也不死
- ✅ 把输出写进 `c.log`

**然后程序自己 `raise ValueError` → 退出码 1。**

| 退出码 | 意思 |
|---|---|
| `0` | 成功 |
| **`1`** | **程序自己报错了** |
| `127` | 命令没找到 |
| `130` | 被 `Ctrl+C` 中断 |

**`echo $?` 可以查上一条命令的退出码。**

> **`exit 1` 只告诉你"失败了"，不告诉你"为什么"。**
> **要知道为什么，必须看 `c.log`** —— 这就是 `2>&1` 不能省的原因。

---

## 记住这一行

```bash
nohup 你的命令 > 日志文件 2>&1 &
```

**停掉它**：

```bash
kill $(lsof -ti :8000)
```

---

## 还没学的（以后有服务器再说）

- `ssh` / `scp` / `rsync` —— 连服务器、传文件
- `systemd` —— 崩溃自动重启、开机自启
- `tar` —— 打包
- `Docker` —— 容器化部署

**现在没有服务器，学了也记不住。先掌握上面那一行。**
