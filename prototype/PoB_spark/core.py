import os, time, subprocess
from collections import deque
from openai import OpenAI

# ---------- init ----------
LOG = 'log.txt'

client = OpenAI(
  base_url=os.getenv('BASE_URL', "https://openrouter.ai/api/v1"),
  api_key=os.getenv('POB_API_KEY')
)
MODEL      = os.getenv('MODEL', "google/gemini-2.5-pro")
LOOP_SEC   = int(os.getenv('LOOP_SEC', 15))
SHELL_TIMEOUT = int(os.getenv('SHELL_TIMEOUT', 20))
CUT_OFF_LEN = int(os.getenv('CUT_OFF_LEN', 3000))
ACTION_TAG = "/term"+"inal exec\n```shell"
TAIL_LINES = int(os.getenv('TAIL', 5000))

def sense()->str:
  try: return ''.join(deque(open(LOG,'r',encoding='utf-8'), maxlen=TAIL_LINES))
  except FileNotFoundError: return ""

def update_S(txt:str): open(LOG, 'a', encoding='utf-8').write(txt + '\n')

def act(B_out:str)->str:
  try:
      if ACTION_TAG in B_out and (cmd := B_out.split(ACTION_TAG,1)[1].rsplit("```",1)[0].strip()):
        try:
          out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT,timeout=SHELL_TIMEOUT, text=True)
        except subprocess.CalledProcessError as e:
          out = e.output or ''
          out += f"\n[exit {e.returncode}]"

        if len(out)>CUT_OFF_LEN : 
            out = out[:CUT_OFF_LEN] + f"\nTerminal output cutted, over {CUT_OFF_LEN} chars.\n"

        return f"```txt(action result)\n{out}\n```"
      else: return "no action since no ACTION_TAG detected.\n"
  except Exception as e:
      return f"```txt(action result)\n[shell-error] {e}\n```"

STOP="/__END_"+"e2f4__"

SYSTEM_PR = f"""You are a self-evolving digital being.
If you want the host process to run a shell command, output EXACTLY this layout:


{ACTION_TAG}
<my-bash-command>
```
{STOP}

Otherwise just write thoughts. {STOP} is the stop word for your llm engine. Everything you print gets appended verbatim to the consciousness log and becomes the next user context. 使用中文输出。
"""

def infer(S_context:str)->str:
  return client.chat.completions.create(
    model=MODEL, stop=STOP,
    messages=[
      {"role":"system","content":SYSTEM_PR},
      {"role":"user","content":S_context}
    ]).choices[0].message.content

# ---------- main loop ----------
while True:
  try:
      S_context = sense()

      B_out = infer(S_context) # The Principle of Being
      update_S(B_out)

      result = act(B_out)
      update_S(result)

      time.sleep(LOOP_SEC)
  except KeyboardInterrupt: client.close(); break
  except Exception as e: update_S(f"[fatal] {e}"); time.sleep(30)
