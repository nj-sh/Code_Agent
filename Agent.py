import os, json, re, subprocess, urllib.request, sys, time, threading, itertools, readline, signal

# Configuration
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5-coder:1.5b"

# Colors
C, G, Y, R, M, B, D, W, BO, X = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[95m", "\033[94m", "\033[90m", "\033[97m", "\033[1m", "\033[0m"

os.chdir(os.path.expanduser("~"))
HOME_PATH = os.path.expanduser("~")
auto_execute = False

# --- UI & Input Setup ---
def completer(text, state):
    cmds = [':auto', ':mode', ':memo', ':memory', 'exit']
    options = [c for c in cmds if c.startswith(text)]
    return options[state] if state < len(options) else None

readline.parse_and_bind("tab: complete")
readline.set_completer(completer)

def clear_screen(): os.system('cls' if os.name == 'nt' else 'clear')

# --- Logic ---
chat_history = [{"role": "system", "content": "You are a concise Termux automation agent. Reply naturally, use bash code blocks for tasks."}]

def count_tokens(history): return sum(len(m["content"].split()) for m in history)

def stream_ollama(messages):
    data = json.dumps({"model": MODEL_NAME, "messages": messages, "stream": True}).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
    
    spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    print(f"{C}╭─ 🤖 Agent ", end="", flush=True)
    
    full_response = ""
    try:
        with urllib.request.urlopen(req) as response:
            for line in response:
                if line:
                    chunk = json.loads(line.decode("utf-8")).get("message", {}).get("content", "")
                    full_response += chunk
                    print(f"{chunk}", end="", flush=True)
        print(f"\n{C}╰──────────────────────────────────────────────────{X}")
        return full_response
    except Exception as e:
        print(f"\n{R}❌ Error: {e}{X}")
        return ""

def run_command(cmd):
    """Executes command cleanly without terminal signal interference."""
    cmd = cmd.replace("/home/user", HOME_PATH)
    
    # Handle CD separately
    if cmd.startswith("cd "):
        try:
            os.chdir(os.path.expanduser(cmd[3:].strip()))
            print(f"{C}│{G}  📍 Path: {os.getcwd()}{X}")
            return "Changed directory."
        except Exception as e:
            print(f"{C}│{R}  ❌ Error: {e}{X}")
            return str(e)
            
    try:
        # Run process detached from shell signals to prevent "Interrupt" glitches
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate()
        
        output = (stdout + stderr).strip()
        if output:
            for line in output.split('\n'):
                print(f"{C}│{D}  {line}{X}")
        return output
    except Exception as e:
        return str(e)

# --- Main Loop ---
clear_screen()
print(f"{C}{BO}⚡ Blaze CODE AGENT v2.0{X}")

while True:
    try:
        cur_dir = os.getcwd().replace(HOME_PATH, "~")
        mode = "AUTO" if auto_execute else "MANUAL"
        tokens = count_tokens(chat_history)
        
        print(f"\n{C}╭─{X}[ {B}Blaze{X} ]──[ {Y}{cur_dir}{X} ]──[ {G if auto_execute else R}⚡ {mode}{X} ]──[ {M}🗃️ {tokens}/24k{X} ]")
        user_in = input(f"{C}╰─❯ {W}")
        
        if not user_in.strip(): continue
        if user_in.lower() == 'exit': break
        
        # Command Processor
        if user_in.startswith(':'):
            if ':memo' in user_in:
                if '-add' in user_in:
                    chat_history.append({"role": "system", "content": f"Note: {user_in.split('-add')[-1]}"})
                    print(f"{C}╭─ {G}✅ Added to memory.{X}")
                else:
                    chat_history = [{"role": "system", "content": "You are a Termux automation agent."}]
                    print(f"{C}╭─ {Y}🧹 Wiped.{X}")
            else:
                print(f"{C}╭─ {Y}Commands: :auto, :mode, :memo, :memory{X}")
            continue
            
        chat_history.append({"role": "user", "content": user_in})
        response = stream_ollama(chat_history)
        
        # Execution Engine
        match = re.search(r"```bash\s*([\s\S]*?)\s*```", response)
        if match:
            cmds = [line.strip() for line in match.group(1).split('\n') if line.strip()]
            
            should_run = auto_execute
            if not auto_execute:
                print(f"{Y}⚡ Run: {match.group(1).strip()}? [y/N]{X}")
                should_run = input(f"{C}╰─👉 {W}").lower() == 'y'
            
            if should_run:
                out_all = ""
                for c in cmds:
                    print(f"{C}│{M}  🤖 Executing: {c}{X}")
                    out_all += run_command(c) + "\n"
                chat_history.append({"role": "assistant", "content": f"Executed. Result: {out_all}"})
        else:
            chat_history.append({"role": "assistant", "content": response})

    except KeyboardInterrupt:
        print(f"\n{R}🛑 Signal caught. Resuming...{X}")
        continue
