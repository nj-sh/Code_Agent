import os, json, re, subprocess, urllib.request, sys, readline

# --- Configuration ---
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5-coder:1.5b"
HOME_PATH = os.path.expanduser("~")
C, G, Y, R, M, B, D, W, BO, X = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[95m", "\033[94m", "\033[90m", "\033[97m", "\033[1m", "\033[0m"

# --- Logic ---
chat_history = [{"role": "system", "content": "You are a concise Termux agent. Use bash code blocks for all commands."}]

def get_path(): return os.getcwd().replace(HOME_PATH, "~")

def run_command(cmd):
    # CD is handled by the process itself
    if cmd.startswith("cd "):
        try:
            os.chdir(os.path.expanduser(cmd[3:].strip()))
            return f"📍 Path updated to: {get_path()}"
        except Exception as e: return f"❌ Error: {e}"
    
    try:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate()
        return (stdout + stderr).strip()
    except Exception as e: return str(e)

# --- Main Interface ---
os.system('clear')
print(f"{C}{BO}⚡ CODEX AGENT v2.2{X}")

while True:
    tokens = sum(len(m["content"].split()) for m in chat_history)
    print(f"\n{C}╭─{X}[ {B}Blaze{X} ]──[ {Y}{get_path()}{X} ]──[ {M}🗃️ {tokens}t{X} ]")
    
    try:
        user_in = input(f"{C}╰─❯ {W}")
    except KeyboardInterrupt:
        print(f"\n{R}🛑 Interrupted{X}")
        continue

    if not user_in.strip(): continue
    if user_in.lower() == 'exit': break
    if user_in.startswith(':'):
        # Handle :memo or :help here if you want to expand
        print(f"{C}│ {Y}Command mode triggered.{X}")
        continue

    chat_history.append({"role": "user", "content": user_in})
    
    # Get response
    data = json.dumps({"model": MODEL_NAME, "messages": chat_history, "stream": True}).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
    
    print(f"{C}│ 🤖 {X}", end="", flush=True)
    full_resp = ""
    try:
        with urllib.request.urlopen(req) as resp:
            for line in resp:
                chunk = json.loads(line.decode("utf-8")).get("message", {}).get("content", "")
                full_resp += chunk
                print(chunk, end="", flush=True)
        print(f"\n{C}╰──────────────────────────────────────────────────{X}")
    except Exception as e:
        print(f"\n{R}❌ Ollama error: {e}{X}")
        continue

    # Execute bash blocks
    match = re.search(r"```bash\s*([\s\S]*?)\s*```", full_resp)
    if match:
        cmds = [c.strip() for c in match.group(1).split('\n') if c.strip()]
        for c in cmds:
            print(f"{C}│ {M}⚙️ Running: {c}{X}")
            out = run_command(c)
            if out: print(f"{C}│ {D}{out}{X}")
        chat_history.append({"role": "assistant", "content": f"Executed sequence. Result: {out}"})
    else:
        chat_history.append({"role": "assistant", "content": full_resp})
