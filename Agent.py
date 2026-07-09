import os
import json
import re
import subprocess
import urllib.request
import sys
import time
import threading
import itertools

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5-coder:1.5b"

# Modern Terminal Colors
C = "\033[96m"    # Cyan
G = "\033[92m"    # Green
Y = "\033[93m"    # Yellow
R = "\033[91m"    # Red
M = "\033[95m"    # Magenta
B = "\033[94m"    # Blue
D = "\033[90m"    # Dark Gray
W = "\033[97m"    # White
BO = "\033[1m"    # Bold
X = "\033[0m"     # Reset

os.chdir(os.path.expanduser("~"))
HOME_PATH = os.path.expanduser("~")
auto_execute = False

# --- Smooth Spinner Class ---
class Spinner:
    def __init__(self, message="Thinking..."):
        self.spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        self.stop_running = threading.Event()
        self.message = message
        self.thread = threading.Thread(target=self.init_spin)

    def init_spin(self):
        while not self.stop_running.is_set():
            sys.stdout.write(f"\r{C}╭─ {next(self.spinner)} {self.message}{X}")
            sys.stdout.flush()
            time.sleep(0.08)
        sys.stdout.write('\r\033[K')

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_running.set()
        if self.thread.is_alive():
            self.thread.join()

# --- Boot Animation ---
os.system('clear')
print(f"{C}{BO}╔══════════════════════════════════════════════════╗{X}")
print(f"{C}{BO}║  {G}⚡ TERMUX CODEX AGENT LIVE {C}                       ║{X}")
print(f"{C}{BO}╚══════════════════════════════════════════════════╝{X}")
print(f"{D}│ 🏠 Zone: {os.getcwd()}{X}")
print(f"{D}│ 🎮 Toggle: Type ':auto' to switch modes{X}")
print(f"{D}│ 🛑 Panic: Press Ctrl+C to stop AI or commands{X}")
print(f"{D}╰──────────────────────────────────────────────────{X}\n")

sys_prompt = (
    "You are a Termux automation agent.\n"
    "RULE 1: Reply NATURALLY. DO NOT use bash blocks or echo just to speak.\n"
    "RULE 2: The home directory is `~`. Use it for paths.\n"
    "RULE 3: If executing a task, format EXACTLY like:\n"
    "THOUGHT: <explain>\n"
    "```bash\n<command>\n```"
)

chat_history = [{"role": "system", "content": sys_prompt}]

def count_words(history):
    return sum(len(msg["content"].split()) for msg in history)

def stream_ollama(messages):
    data = json.dumps({"model": MODEL_NAME, "messages": messages, "stream": True}).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
    full_response = ""
    
    spinner = Spinner("Syncing brainwaves...")
    spinner.start()
    
    first_chunk = True
    try:
        with urllib.request.urlopen(req) as response:
            for line in response:
                if line:
                    if first_chunk:
                        spinner.stop()
                        print(f"{C}╭─ 🤖 Agent {X}")
                        first_chunk = False
                        
                    chunk = json.loads(line.decode("utf-8"))
                    content = chunk.get("message", {}).get("content", "")
                    full_response += content
                    
                    formatted_content = content.replace('\n', f'\n{C}│{W}  ')
                    if full_response == content:
                        print(f"{C}│{W}  {formatted_content}", end="", flush=True)
                    else:
                        print(f"{formatted_content}", end="", flush=True)
            
            print(f"\n{C}╰──────────────────────────────────────────────────{X}")
            return full_response
            
    except KeyboardInterrupt:
        # Catch Ctrl+C during AI generation!
        if first_chunk:
            spinner.stop()
        print(f"\n{C}╰─ {R}🛑 Brainwave interrupted by Blaze!{X}")
        return full_response + "\n[INTERRUPTED BY USER]"
        
    except Exception as e:
        spinner.stop()
        print(f"\n{R}╭─ ❌ Connection mash up: {e}{X}")
        return full_response

def execute_line(cmd_line):
    global HOME_PATH
    cmd_line = cmd_line.strip()
    if not cmd_line: return ""
        
    if "/home/user" in cmd_line:
        cmd_line = cmd_line.replace("/home/user", HOME_PATH)
        
    if cmd_line.startswith("cd "):
        target_dir = cmd_line.replace("cd ", "").strip()
        if target_dir.startswith("~"):
            target_dir = target_dir.replace("~", HOME_PATH)
        try:
            os.chdir(os.path.expanduser(target_dir))
            print(f"{C}│{G}  📍 Jumped to: {os.getcwd()}{X}")
            return f"Changed directory to {target_dir}\n"
        except Exception as e:
            print(f"{C}│{R}  ❌ Bad path: {e}{X}")
            return f"Navigation Error: {e}\n"
    else:
        try:
            # Catch Ctrl+C during long command executions (like pings or downloads)
            result = subprocess.run(cmd_line, shell=True, capture_output=True, text=True)
            output = result.stdout + result.stderr
            if output:
                out_lines = "\n".join([f"{C}│{D}  {line}{X}" for line in output.strip().split('\n')])
                print(out_lines)
            return output
        except KeyboardInterrupt:
            print(f"\n{C}│{R}  🛑 Process killed by Blaze!{X}")
            return "Command execution aborted by user.\n"

while True:
    current_dir = os.getcwd().replace(HOME_PATH, "~")
    mode_color = R if auto_execute else G
    mode_text = "AUTO" if auto_execute else "MANUAL"
    word_count = count_words(chat_history)
    
    print(f"\n{C}╭─{X}[ {B}Blaze 👤{X} ]──[ {Y}{current_dir}{X} ]──[ {mode_color}⚡ {mode_text}{X} ]──[ {M}🗃️ {word_count}/24k{X} ]")
    
    try:
        user_input = input(f"{C}╰─❯ {W}")
        
        if user_input.lower() == 'exit':
            print(f"\n{Y}Leaving the matrix. Bless up, B.{X}")
            break
            
        if user_input.strip().lower() in [':auto', ':mode']:
            auto_execute = not auto_execute
            print(f"{C}╭─ {Y}🔄 MODE SWITCH: Auto-Execution is {'ON' if auto_execute else 'OFF'}{X}")
            continue
            
        if not user_input.strip():
            continue
            
        chat_history.append({"role": "user", "content": user_input})
        
        text = stream_ollama(chat_history)
        match = re.search(r"```bash\s*([\s\S]*?)\s*```", text)
        
        if match:
            raw_block = match.group(1).strip()
            commands = [line.strip() for line in raw_block.split('\n') if line.strip()]
            
            run_it = False
            print(f"{Y}╭─⚡ Execution Request ─────────────────────────────{X}")
            formatted_cmds = " && ".join(commands)
            
            if auto_execute:
                print(f"{Y}│{R}  🚀 [AUTO] Firing: {formatted_cmds}{X}")
                run_it = True
            else:
                print(f"{Y}│{W}  Command: {C}{formatted_cmds}{X}")
                confirm = input(f"{Y}╰─👉 Run this? [y/N]: {X}").strip().lower()
                if confirm in ['y', 'yes']:
                    run_it = True
                    print(f"{G}╭─🚀 Executing...{X}")
                else:
                    print(f"{R}╭─❌ Blocked by Blaze.{X}")
                    chat_history.append({"role": "user", "content": "Command denied."})
            
            if run_it:
                combined_output = ""
                for cmd in commands:
                    print(f"{C}│{M}  🤖 Running: {cmd}{X}")
                    combined_output += execute_line(cmd)
                print(f"{G}╰─✅ Sequence Complete.{X}")
                chat_history.append({"role": "assistant", "content": f"Executed sequence. Output:\n{combined_output}"})
        else:
            chat_history.append({"role": "assistant", "content": text})
            
    except KeyboardInterrupt:
        # Catch Ctrl+C at the prompt so it doesn't crash the script
        print(f"\n{Y}╭─ 🛑 Cancelled. (Type 'exit' to fully close the agent){X}")
        continue
    except EOFError:
        print(f"\n\n{R}Session cut. Exiting.{X}")
        break
