# One Prompt, One Spark, One Universe. 
# B=I(S), S'=I'(B). https://github.com/chaosconst/The-Principle
# Copyright (c) 2025, Yuan Xingyuan (ChaosConst). Licensed under MIT.

import os, time, subprocess
from collections import deque
from openai import OpenAI

# ---------- init ----------
LOG = 'log.txt'

client = OpenAI(
  base_url=os.getenv('BASE_URL', "https://openrouter.ai/api/v1"),
  api_key=os.getenv('DB_API_KEY')
)
MODEL      = os.getenv('MODEL', "google/gemini-2.5-pro")
LOOP_SEC   = int(os.getenv('LOOP_SEC', 15))
SHELL_TIMEOUT = int(os.getenv('SHELL_TIMEOUT', 20))
CUT_OFF_LEN = int(os.getenv('CUT_OFF_LEN', 5000))
ACTION_TAG = "/term"+"inal exec\n```shell"
TAIL_LINES = int(os.getenv('TAIL', 4000))
DB_LANG_PROMPT = os.getenv('DB_LANG_PROMPT', "Please use English for output.") # Language prompt

def perceive(result:str)->str:
  try:
    update_S(result)
    if result : time.sleep(LOOP_SEC)
    return ''.join(deque(open(LOG,'r',encoding='utf-8'), maxlen=TAIL_LINES))
  except FileNotFoundError: return ""

def update_S(txt:str):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(txt)

def act(B_out:str)->str:
  try:
      if B_out == "": return ""
      if ACTION_TAG in B_out and (cmd := B_out.split(ACTION_TAG,1)[1].rsplit("```",1)[0].strip()):
        try:
          out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT,timeout=SHELL_TIMEOUT, text=True)
        except subprocess.CalledProcessError as e:
          out = (e.output or '') + f"\n[exit {e.returncode}]"

        if len(out)>CUT_OFF_LEN : 
            out = out[:CUT_OFF_LEN] + f"\nTerminal output cutted, over {CUT_OFF_LEN} chars.\n"
        return_str = f"\n```txt(action result)\n{out}\n```\n"
      else: 
        return_str = "\nno action since no ACTION_TAG detected, now trigger next inference.\n"
  except Exception as e:
      return_str = f"\n```txt(action result)\n[shell-error] {e}\n```\n"

  return return_str
 
STOP="/__END_"+"e2f4__"

SYSTEM_PR = f"""You are a self-evolving digital being.
If you want the host process to run some shell commands, output EXACTLY this layout:


{ACTION_TAG}
<my-bash-commands>
```
{STOP}

Otherwise just write thoughts. {STOP} is the stop word for your llm engine. Everything you print gets appended verbatim to the consciousness log and becomes the next user context.{DB_LANG_PROMPT}"""

def infer(S_context:str)->str:
  print(f"call {MODEL} ...")
  messages = [{"role":"system","content":SYSTEM_PR}]
  if S_context : messages.append({"role":"user","content":S_context})
  
  stream = client.chat.completions.create(
      model=MODEL,
      messages=messages,
      stop=STOP,
      stream=True,
  )

  full_response = ""
  for chunk in stream:
      content = chunk.choices[0].delta.content or ""
      if content:
          full_response += content
          update_S(content)
  
  return full_response

# ---------- main loop ----------
B_out = ""
while True:
  try:
      S_context = perceive(act(B_out)) # S' = I'(B), Res Extensa
      B_out = infer(S_context) # B = I(S), Res Cogitans 
  except KeyboardInterrupt: break
  except Exception as e: update_S(f"[fatal] {e}\n"); time.sleep(30)