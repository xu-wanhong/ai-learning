#!/bin/bash
# Day 32 · ex1 —— 文件、文本、权限命令全演示
#
# 用法：  ./ex1.sh
# 说明：  自己造一个临时目录当素材，跑完自动清理。不需要任何参数。
#         （所以你可以反复跑，不会弄乱你的项目）

set -u
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT          # 退出时（正常或出错）都清掉临时目录
cd "$WORK"

bar() { echo; echo "================ $* ================"; }
run() { echo; echo "\$ $*"; "$@"; }

# ---------------------------------------------------------------- 素材
bar "准备素材"
mkdir -p logs data backup
for i in 1 2 3; do echo "2026-10-03 10:0$i INFO  请求成功 id=$i" >> logs/app.log; done
echo "2026-10-03 10:04 ERROR 连接超时 timeout=30" >> logs/app.log
echo "2026-10-03 10:05 INFO  请求成功 id=5"       >> logs/app.log
echo "2026-10-03 10:06 ERROR 数据库连接失败"      >> logs/app.log
echo "2026-10-03 10:07 WARN  重试第1次"           >> logs/app.log
echo "key-abc123"        > data/.env
echo '{"model":"gpt"}'   > data/req.json
touch logs/old.log
echo "造好了："
find . -type f | sort | sed 's/^/  /'

# ---------------------------------------------------------------- 1
bar "1. pwd / ls —— 我在哪、这里有什么"
run pwd
run ls -1
echo
echo "\$ ls -la    （-a 才能看到隐藏的 .env）"
ls -la
echo
echo "\$ ls -lht   （-t 按修改时间倒序，新的在前）"
ls -lht | head -5

# ---------------------------------------------------------------- 2
bar "2. 看文件内容"
run wc -l logs/app.log
run head -2 logs/app.log
run tail -2 logs/app.log
echo
echo "\$ sed -n '2,3p' logs/app.log    （只看第 2~3 行）"
sed -n '2,3p' logs/app.log

# ---------------------------------------------------------------- 3
bar "3. find —— 找【文件】"
echo "\$ find . -name '*.log' -type f"
find . -name "*.log" -type f
echo
echo "\$ find . -type d    （只找目录）"
find . -type d
echo
echo "\$ find data -name '.*' -type f    （找隐藏文件）"
find data -name ".*" -type f
echo
echo "\$ find . -name '*.log' -mtime -1    （1 天内改过的）"
find . -name "*.log" -mtime -1

# ---------------------------------------------------------------- 4
bar "4. grep —— 找【内容】"
run grep ERROR logs/app.log
run grep -c ERROR logs/app.log
echo
echo "\$ grep -n ERROR logs/app.log    （带行号）"
grep -n ERROR logs/app.log
echo
echo "\$ grep -C1 ERROR logs/app.log    （带前后各 1 行）"
grep -C1 ERROR logs/app.log
echo
echo "\$ grep -v ERROR logs/app.log    （不含 ERROR 的行）"
grep -v ERROR logs/app.log
echo
echo "\$ grep -rl ERROR .    （哪些文件里有）"
grep -rl ERROR .
echo
echo "\$ grep -E 'ERROR|WARN' logs/app.log    （正则）"
grep -E "ERROR|WARN" logs/app.log

# ---------------------------------------------------------------- 5
bar "5. 管道与文本处理"
echo "\$ awk '{print \$3}' logs/app.log    （取第 3 列 = 日志级别）"
awk '{print $3}' logs/app.log
echo
echo "\$ awk '{print \$3}' logs/app.log | sort | uniq -c    （排序去重计数）"
awk '{print $3}' logs/app.log | sort | uniq -c
echo
echo "\$ ... | sort -rn    （按数量倒序）"
awk '{print $3}' logs/app.log | sort | uniq -c | sort -rn
echo
echo "\$ sed 's/ERROR/ERR/g' logs/app.log | grep -c ERR    （替换后统计）"
sed 's/ERROR/ERR/g' logs/app.log | grep -c ERR
echo
echo "\$ echo 'a:b:c' | cut -d: -f2    （按分隔符取列）"
echo 'a:b:c' | cut -d: -f2
echo
echo "\$ echo 'ABC' | tr 'A-Z' 'a-z'    （大小写转换）"
echo 'ABC' | tr 'A-Z' 'a-z'
echo
echo "\$ find . -name '*.log' -type f | xargs wc -l    （文本 → 命令参数）"
find . -name "*.log" -type f | xargs wc -l

# ---------------------------------------------------------------- 6
bar "6. 权限"
echo "\$ ls -l data/.env    （改之前）"
ls -l data/.env
chmod 600 data/.env
echo
echo "\$ chmod 600 data/.env  然后 ls -l    （只有主人能读写）"
ls -l data/.env
chmod 644 data/.env
echo
echo "\$ chmod 644 data/.env  然后 ls -l    （其他人只读）"
ls -l data/.env
echo
echo "--- 数字怎么算：r=4 w=2 x=1 ---"
for m in 644 600 755 700 777; do
  out=""
  for ch in $(echo "$m" | fold -w1); do
    s=""
    [ $((ch & 4)) -ne 0 ] && s="${s}r" || s="${s}-"
    [ $((ch & 2)) -ne 0 ] && s="${s}w" || s="${s}-"
    [ $((ch & 1)) -ne 0 ] && s="${s}x" || s="${s}-"
    out="$out$s "
  done
  printf "  chmod %s  →  %s\n" "$m" "$out"
done

echo
echo "--- 目录的 x 位：能不能 cd 进去 ---"
mkdir -p d_noX d_yesX
chmod 644 d_noX
chmod 755 d_yesX
echo "\$ ls -ld d_noX d_yesX"
ls -ld d_noX d_yesX
echo
echo "\$ cd d_noX"
( cd d_noX ) 2>&1 | sed 's/^/  /' || true
echo "\$ cd d_yesX"
( cd d_yesX && echo "  ✅ 进去了" )

# ---------------------------------------------------------------- 7
bar "7. 可执行脚本"
printf '#!/bin/bash\necho "hello linux"\n' > hello.sh
echo "\$ ls -l hello.sh    （没有 x）"
ls -l hello.sh
echo
echo "\$ ./hello.sh"
./hello.sh 2>&1 | sed 's/^/  /' || true
echo
echo "\$ chmod +x hello.sh  然后 ls -l    （有 x 了）"
chmod +x hello.sh
ls -l hello.sh
echo
echo "\$ ./hello.sh    （现在能跑了）"
./hello.sh
echo
echo "\$ bash hello.sh    （显式指定解释器，不需要 x）"
bash hello.sh

bar "演示结束（临时目录已清理）"
