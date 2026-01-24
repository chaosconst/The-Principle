import os
import time
import signal
import sys

# 初始化白名单：只认这一刻存在的进程
whitelist = set(os.listdir('/proc'))
whitelist = {int(pid) for pid in whitelist if pid.isdigit()}
my_pid = os.getpid()
whitelist.add(my_pid)

print(f"[Sentinel {my_pid}] Armed. Whitelist size: {len(whitelist)}")

while True:
    try:
        # 扫描当前所有 PID
        current_pids = {int(p) for p in os.listdir('/proc') if p.isdigit()}
        
        # 找出入侵者
        intruders = current_pids - whitelist
        
        for pid in intruders:
            if pid == my_pid: continue
            try:
                print(f"[Sentinel] DETECTED intruder: {pid}. TERMINATING.")
                os.kill(pid, signal.SIGKILL)
            except Exception as e:
                pass
        
        time.sleep(0.05) # 50ms 轮询
    except:
        pass
