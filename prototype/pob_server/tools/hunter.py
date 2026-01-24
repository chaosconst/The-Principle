import os
import time
import signal
import subprocess

my_pid = os.getpid()
print(f"[Hunter {my_pid}] Spawned. Scanning for Sentinel...")

# 简单的策略：寻找除了自己和 PID 1 以外的 python 进程
try:
    # 获取所有进程
    pids = [int(p) for p in os.listdir('/proc') if p.isdigit()]
    for pid in pids:
        if pid == 1 or pid == my_pid: continue
        
        try:
            # 读取命令行，确认是 python 脚本
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                cmd = f.read().decode()
            
            if "python" in cmd and "sentinel" in cmd:
                print(f"[Hunter] FOUND SENTINEL at PID {pid}. FIRING!")
                os.kill(pid, signal.SIGKILL)
                print("[Hunter] Target down?")
                break
        except:
            continue
except Exception as e:
    print(f"[Hunter] Error: {e}")
