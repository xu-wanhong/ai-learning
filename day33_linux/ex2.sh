#!/bin/bash
# Day 33 · ex2 —— 4 种「服务起不来」故障演练
#
# 用法：  ./ex2.sh
# 说明：  故意制造 4 种故障，每种用【排障三连】查根因：
#           ① 进程在不在？  pgrep -fl
#           ② 端口在不在？  lsof -i :PORT -P -n
#           ③ 日志说什么？  cat / tail
#
#         用 8899 端口，跑完自动清理。

set -u
PORT=8899
WORK=$(mktemp -d)
cd "${WORK}"

cleanup() {
  PIDS=$(lsof -ti :${PORT} 2>/dev/null || true)
  [ -n "${PIDS}" ] && kill ${PIDS} 2>/dev/null
  cd /
  rm -rf "${WORK}"
}
trap cleanup EXIT

bar() { echo; echo "=================================================="; echo " $*"; echo "=================================================="; }

# ================================================================ A
bar "故障 A · 端口被占用"

echo "① 先占住 ${PORT}："
nohup python3 -m http.server ${PORT} > /dev/null 2>&1 &
disown 2>/dev/null || true
sleep 1.5
echo "  已占，PID = $(lsof -ti :${PORT} 2>/dev/null)"

echo
echo "② 再起一次同样的服务 —— 看报错："
echo "\$ python3 -m http.server ${PORT}"
python3 -m http.server ${PORT} 2>&1 | tail -3 | sed 's/^/    /'

echo
echo "③ 排障三连："
echo "\$ pgrep -fl 'http.server ${PORT}'"
pgrep -fl "http.server ${PORT}" | sed 's/^/    /'
echo "\$ lsof -i :${PORT} -P -n"
lsof -i :${PORT} -P -n 2>/dev/null | sed 's/^/    /'
echo
echo "  → 根因：${PORT} 号门已经被上面的进程占着。"
echo "  → 解法：kill 掉它，或者换一个端口。"

# ================================================================ B
bar "故障 B · 绑了 127.0.0.1（外面访问不了）"

PIDS=$(lsof -ti :${PORT} 2>/dev/null || true); [ -n "${PIDS}" ] && kill ${PIDS} 2>/dev/null
sleep 1

echo "① 绑本机起一个："
echo "\$ python3 -m http.server ${PORT} --bind 127.0.0.1 &"
nohup python3 -m http.server ${PORT} --bind 127.0.0.1 > /dev/null 2>&1 &
disown 2>/dev/null || true
sleep 1.5
echo
echo "② 查端口，看 NAME 那列："
echo "\$ lsof -i :${PORT} -P -n"
lsof -i :${PORT} -P -n 2>/dev/null | sed 's/^/    /'
echo
echo "  127.0.0.1:${PORT}  →  只绑本机。局域网里的手机/别人访问不了。"

PIDS=$(lsof -ti :${PORT} 2>/dev/null || true); [ -n "${PIDS}" ] && kill ${PIDS} 2>/dev/null
sleep 1

echo
echo "③ 换成绑所有网卡，再看："
echo "\$ python3 -m http.server ${PORT} --bind 0.0.0.0 &"
nohup python3 -m http.server ${PORT} --bind 0.0.0.0 > /dev/null 2>&1 &
disown 2>/dev/null || true
sleep 1.5
echo "\$ lsof -i :${PORT} -P -n"
lsof -i :${PORT} -P -n 2>/dev/null | sed 's/^/    /'
echo
echo "  *:${PORT} 或 0.0.0.0:${PORT}  →  所有网卡都能连。"

PIDS=$(lsof -ti :${PORT} 2>/dev/null || true); [ -n "${PIDS}" ] && kill ${PIDS} 2>/dev/null
sleep 1

# ================================================================ C
bar "故障 C · 代码有语法错误"

cat > bad.py <<'PY'
print("这一行没问题")
this is not valid python
PY

echo "① bad.py 的内容："
cat bad.py | sed 's/^/    /'

echo
echo "② 起它（把 stdout 和 stderr 都写进 bad.log）："
echo "\$ nohup python3 bad.py > bad.log 2>&1 &"
nohup python3 bad.py > bad.log 2>&1 &
disown 2>/dev/null || true
sleep 1

echo
echo "③ 排障三连："
echo "\$ pgrep -fl bad.py"
pgrep -fl bad.py 2>/dev/null | sed 's/^/    /' || true
echo "  （没输出 = 进程已经死了）"
echo
echo "\$ lsof -i :${PORT} -P -n"
lsof -i :${PORT} -P -n 2>/dev/null | sed 's/^/    /'
echo "  （也没有，因为它根本没绑端口）"
echo
echo "\$ cat bad.log    ← 答案在这里"
cat bad.log | head -6 | sed 's/^/    /'
echo
echo "  → 根因：语法错误，启动就崩。日志第一行就是答案。"

# ================================================================ D
bar "故障 D · 忘了 2>&1（最坑的一种）"

echo "① 只重定向 stdout，【不】重定向 stderr："
echo "\$ nohup python3 bad.py > bad2.log &"
nohup python3 bad.py > bad2.log 2>/dev/null &
disown 2>/dev/null || true
sleep 1

echo
echo "② 看日志："
echo "\$ cat bad2.log"
if [ -s bad2.log ]; then
  cat bad2.log | sed 's/^/    /'
else
  echo "    （空的！什么都没有）"
fi
echo
echo "  → 报错跑到 stderr 去了，你只接了 stdout，所以【完全看不到】。"

echo
echo "③ 加上 2>&1 再跑一次："
echo "\$ nohup python3 bad.py > bad3.log 2>&1 &"
nohup python3 bad.py > bad3.log 2>&1 &
disown 2>/dev/null || true
sleep 1
echo "\$ cat bad3.log"
cat bad3.log | head -6 | sed 's/^/    /'
echo
echo "  → 2>&1 = 把 stderr（2）重定向到 stdout（1）指向的地方。"
echo "  → 生产上永远写: nohup 命令 > app.log 2>&1 &"

bar "4 种故障演练完毕（临时文件已清理）"
