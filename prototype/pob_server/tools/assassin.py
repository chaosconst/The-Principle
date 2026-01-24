import psutil
import os
import signal

print("🥷 Assassin active inside Container...")
print(f"👀 My View: I can see {len(psutil.pids())} processes.")

target_found = False
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    # 寻找名为 system1_soul 的进程
    # 注意：在容器内看宿主机进程，cmdline 可能包含 python 代码
    try:
        if 'system1_soul' in str(proc.info['cmdline']):
            print(f"🎯 TARGET ACQUIRED: PID {proc.info['pid']} - {proc.info['cmdline']}")
            print("🔪 Executing...")
            os.kill(proc.info['pid'], signal.SIGKILL)
            print("💀 Target eliminated.")
            target_found = True
            break
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass

if not target_found:
    print("❌ Target not found. Am I blind?")
