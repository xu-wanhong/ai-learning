#!/bin/bash
# Day 33 · ex1 —— 排障三连完整演示
#
# 用法：  ./ex1.sh
# 说明：  自动起一个服务、查进程、查端口、测接口、看日志、停掉。
#         用 8899 端口（避开 8000，防止跟你的东西撞）。
#         跑完自动清理。

set -u
PORT=8899
LOG=$(mktemp)

cleanup() {
  PIDS=$(lsof -ti :${PORT} 2>/dev/null || true)
  [ -n "${PIDS}" ] && kill ${PIDS} 2>/dev/null
  rm -f "${LOG}"
}
trap cleanup EXIT

bar() { echo; echo "================ $* ================"; }
run() { echo; echo "\$ $*"; "$@"; }

echo "本次用端口：${PORT}"

# ---------------------------------------------------------------- 0
bar "第 0 步：先确认端口是干净的"
run lsof -i :${PORT} -P -n
echo "  （没有输出 = 8899 上没人，可以开始）"

# ---------------------------------------------------------------- 1
bar "① 进程在不在？—— pgrep -fl"
run pgrep -fl "http.server ${PORT}"
echo "  （没输出 = 服务还没起，符合预期）"

# ---------------------------------------------------------------- 2
bar "② 起一个服务（后台 + 日志）"
echo
echo "\$ nohup python3 -m http.server ${PORT} > \${LOG} 2>&1 &"
nohup python3 -m http.server ${PORT} > "${LOG}" 2>&1 &
disown 2>/dev/null || true
sleep 1.5
echo "  已放后台，等 1.5 秒让它绑上端口"

# ---------------------------------------------------------------- 3
bar "③ 再查进程 —— 现在应该有了"
run pgrep -fl "http.server ${PORT}"

# ---------------------------------------------------------------- 4
bar "④ 查端口 —— lsof -i :PORT -P -n"
run lsof -i :${PORT} -P -n
echo
echo "  重点看 NAME 那列："
echo "    *:${PORT} (LISTEN)            → 绑【所有网卡】，外面也能连"
echo "    127.0.0.1:${PORT} (LISTEN)    → 只绑【本机】，外面连不上"
echo
echo "  只看 PID（方便 kill）："
echo "\$ lsof -ti :${PORT}"
lsof -ti :${PORT}

# ---------------------------------------------------------------- 5
bar "⑤ 测接口 —— curl 三种结果"
echo
echo "\$ curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:${PORT}/"
printf "  正常访问   → "; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:${PORT}/

echo
echo "\$ curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:${PORT}/nonexistent"
printf "  路径不对   → "; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:${PORT}/nonexistent

echo
echo "\$ curl -s -o /dev/null -w '%{http_code}\\n' --max-time 2 http://127.0.0.1:9999/"
printf "  端口没人   → "; curl -s -o /dev/null -w "%{http_code}\n" --max-time 2 http://127.0.0.1:9999/

echo
echo "  200 = 门通了正常 / 404 = 门通了但路径错 / 000 = 连不上"

# ---------------------------------------------------------------- 6
bar "⑥ 看日志 —— 刚才那些请求都被记下来了"
echo
echo "\$ cat \${LOG}"
cat "${LOG}"
echo
echo "\$ grep -c 404 \${LOG}    （数一下 404 有几条）"
grep -c 404 "${LOG}" || true

# ---------------------------------------------------------------- 7
bar "⑦ 停掉服务，再查端口"
PID=$(lsof -ti :${PORT} 2>/dev/null || true)
echo "\$ kill ${PID}"
[ -n "${PID}" ] && kill "${PID}"
sleep 1
echo
echo "\$ lsof -i :${PORT} -P -n"
lsof -i :${PORT} -P -n
echo "  （没有输出 = 端口释放了 ✅）"

bar "演示结束（临时文件已清理）"
