#!/bin/bash
# Day 32 · ex2 —— grep 的 12 个常用参数，每个一个例子
#
# 用法：  ./ex2.sh
# 说明：  自己造一个临时日志，跑完自动清理。

set -u
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

# 造一个够用的日志
cat > app.log <<'LOG'
2026-10-03 10:01 INFO  请求成功 id=1
2026-10-03 10:02 INFO  请求成功 id=2
2026-10-03 10:03 INFO  请求成功 id=3
2026-10-03 10:04 ERROR 连接超时 timeout=30
2026-10-03 10:05 INFO  请求成功 id=5
2026-10-03 10:06 ERROR 数据库连接失败
2026-10-03 10:07 WARN  重试第1次
2026-10-03 10:08 error 小写的 error 也能匹配吗
LOG
mkdir -p sub && cp app.log sub/other.log

show() { echo; echo "\$ $*"; }

echo "================ 素材（8 行）================"
cat -n app.log

echo
echo "================ grep 逐个参数 ================"

show "grep ERROR app.log"
grep ERROR app.log

show "grep -i error app.log            # -i 忽略大小写（4 行都出来了）"
grep -i error app.log

show "grep -c ERROR app.log            # -c 只输出【条数】"
grep -c ERROR app.log

show "grep -n ERROR app.log            # -n 带【行号】"
grep -n ERROR app.log

show "grep -v ERROR app.log            # -v 反向：不含 ERROR 的行"
grep -v ERROR app.log

show "grep -C1 ERROR app.log           # -C1 带前后各 1 行【上下文】"
grep -C1 ERROR app.log

show "grep -A1 ERROR app.log           # -A1 只带后面 1 行（After）"
grep -A1 ERROR app.log

show "grep -B1 ERROR app.log           # -B1 只带前面 1 行（Before）"
grep -B1 ERROR app.log

show "grep -rl ERROR .                # -r 递归 + -l 只输出【文件名】"
grep -rl ERROR .

show "grep -rn ERROR .                # -r 递归 + -n 行号（⭐ 最常用）"
grep -rn ERROR .

show "grep -E 'ERROR|WARN' app.log    # -E 用 | 正则"
grep -E "ERROR|WARN" app.log

show "grep -oE 'INFO|WARN|ERROR' app.log   # -o 只输出【匹配到的部分】"
grep -oE "INFO|WARN|ERROR" app.log

show "grep -w INFO app.log            # -w 整词匹配（INFO 不会匹配到 INFOX）"
grep -w INFO app.log

echo
echo "================ 组合：统计日志级别 ================"
echo
echo "\$ grep -oE 'INFO|WARN|ERROR' app.log | sort | uniq -c | sort -rn"
grep -oE "INFO|WARN|ERROR" app.log | sort | uniq -c | sort -rn

echo
echo "================ 组合：找出最后 3 行里的错误 ================"
echo
echo "\$ tail -3 app.log | grep -i error"
tail -3 app.log | grep -i error

echo
echo "================ 演示结束（临时目录已清理）================"
