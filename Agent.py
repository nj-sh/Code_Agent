
#!/usr/bin/env python3
"""
CODEX v3.1 — Terminal AI Assistant (Fixed)
Direct ops: list, mkdir, cd + plain-text command detection
Fixes: success detection, duplicate thinking blocks, false error messages
"""

import os, json, re, subprocess, sys, time, threading, signal, random
import urllib.request, urllib.error
from dataclasses import dataclass

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5-coder:1.5b"
COMMAND_TIMEOUT = 60
MAX_HISTORY = 50
HOME = os.path.expanduser("~")

class C:
    CYAN = "\033[96m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
    RED = "\033[91m"; GRAY = "\033[90m"; BOLD = "\033[1m"
    RESET = "\033[0m"; DIM = "\033[2m"; TOKEN = "\033[38;5;221m"
    THINK = "\033[38;5;245m"; BLUE = "\033[94m"

@dataclass
class CmdResult:
    success: bool; output: str; exit_code: int; duration: float; command: str

class Spinner:
    def __init__(self): self._r = False; self._t = None
    def start(self):
        self._r = True; self._t = threading.Thread(target=self._spin, daemon=True); self._t.start()
    def _spin(self):
        ch = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"; i = 0
        while self._r:
            sys.stdout.write(f"\r{ch[i]} "); sys.stdout.flush(); i = (i+1)%len(ch); time.sleep(0.1)
    def stop(self):
        self._r = False
        if self._t: self._t.join(timeout=0.5)
        sys.stdout.write("\r"+" "*30+"\r"); sys.stdout.flush()

class OllamaClient:
    def __init__(self, url, model): self.url, self.model = url, model
    def chat(self, messages):
        data = json.dumps({"model":self.model,"messages":messages,"stream":True,
                           "options":{"temperature":0.1}}).encode()
        req = urllib.request.Request(self.url, data=data, headers={"Content-Type":"application/json"})
        full = ""; sp = Spinner(); sp.start(); got = False
        for a in range(3):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    for line in resp:
                        try: c = json.loads(line.decode())["message"]["content"]
                        except: continue
                        if not c: continue
                        if not got: got = True; sp.stop()
                        full += c; sys.stdout.write(c); sys.stdout.flush()
                if got: print()
                return True, full
            except Exception as e:
                if a < 2: sp.stop(); time.sleep(1)
                else: sp.stop(); print(f"\n{C.RED}✗ Ollama unreachable{C.RESET}"); return False, ""
        if not got: sp.stop()
        return got, full

# ─── Known simple commands (run directly, no LLM) ────────────
SIMPLE_CMDS = {
    "list": "ls",
    "list files": "ls -la",
    "list all": "ls -la",
    "show files": "ls -la",
    "what's here": "ls",
    "whats here": "ls",
    "dir": "ls",
    "pwd": "pwd",
    "where am i": "pwd",
    "date": "date",
    "time": "date",
    "whoami": "whoami",
    "help": "echo 'Commands: list, pwd, date, cd <path>, mkdir <name>, make a folder <name>'",
}

# ─── Plain command detector (for LLM output without backticks) ──
SHELL_CMDS = {"ls","cd","mkdir","pwd","date","whoami","echo","cat","touch","rm","cp","mv",
              "grep","find","sort","head","tail","wc","chmod","chown","ps","top","kill",
              "df","du","free","uname","which","whereis","apt","pip","npm","git","docker"}

class InputClassifier:
    GREETINGS = {"hey","hi","hello","yo","sup","heyo","howdy"}
    ANGER = {"wtf","wth","stupid","bad","terrible","broken","useless"}
    AFFIRM = {"yes","y","yeah","yep","sure","ok","okay","do it","run","execute","go"}
    REJECT = {"no","n","nope","nah","cancel","stop","dont","don't","skip"}
    QUESTIONS = ["what","why","how","when","where","who","which"]

    @classmethod
    def classify(cls, text):
        t = text.strip().lower()
        if t in cls.GREETINGS: return "greeting"
        if t in cls.ANGER: return "anger"
        if t in cls.AFFIRM: return "affirm"
        if t in cls.REJECT: return "reject"
        if any(t.startswith(q) for q in cls.QUESTIONS): return "question"
        if t.startswith("cd "): return "cd_cmd"
        if t in SIMPLE_CMDS: return "simple_cmd"
        if re.match(r'mk(?:dir)?\s+', t): return "direct_op"
        if re.match(r'(?:make|create)\s+(?:a\s+)?(?:folder|dir|directory)\s+', t): return "direct_op"
        return "command"

SYS = """You are CODEX — a terminal AI assistant like GitHub Copilot.

RULES:
1. When a command FAILS — read the error, try a different approach.
2. When a command SUCCEEDS — confirm briefly and move on. Do NOT re-suggest the same command.
3. NEVER ask for credentials (GitHub, email, password) unless task is about git.
4. You get 3 attempts total, then explain problem to user and ask for help.
5. Output ```bash blocks for commands. One sentence explanation max.
6. mkdir, cd, and simple commands are handled by the script automatically."""

def prompt(cwd, mode):
    return f"{SYS}\n\nDIR: {cwd}\nMODE: {mode.upper()}\n"

class CodexAgent:
    def __init__(self):
        self.cwd = os.getcwd()
        self.client = OllamaClient(OLLAMA_URL, MODEL_NAME)
        self.log = []; self.mode = "auto"; self._pending = None
        self._running_proc = None; self._awaiting = False
        self.history = [{"role":"system","content":prompt(self.cwd,self.mode)}]
        self.cls = InputClassifier()

    def _rebuild(self):
        self.history[0] = {"role":"system","content":prompt(self.cwd,self.mode)}

    def estimate_tokens(self):
        return int(sum(len(m["content"].split()) for m in self.history) / 0.75)

    def prompt_str(self):
        p = self.cwd.replace(HOME,"~"); t = self.estimate_tokens()
        tag = f"{C.GREEN}AU{C.RESET}" if self.mode=="auto" else f"{C.YELLOW}MA{C.RESET}"
        return f"{C.CYAN}{p}{C.RESET} {C.TOKEN}[{t}t]{C.RESET} {tag} {C.GREEN}❯{C.RESET} "

    def extract_cmds(self, text):
        cmds = []
        for lang, code in re.findall(r'```(\w+)?\s*([\s\S]*?)```', text):
            code = code.strip()
            if not code or lang.lower() not in ("bash","sh","shell",""): continue
            for line in code.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    cmds.append(line)
        if not cmds:
            t = text.strip()
            if t and not t.startswith("#") and "\n" not in t:
                first = t.split()[0].lower() if t.split() else ""
                if first in SHELL_CMDS or first.startswith("./") or first.startswith("/"):
                    cmds.append(t)
        return cmds

    def list_dirs(self, path):
        try: return [e for e in os.listdir(path) if os.path.isdir(os.path.join(path, e))]
        except: return []

    def find_best_match(self, name, root=None):
        if root is None: root = self.cwd
        nl = name.lower()
        for check in [
            lambda e,nl: e.lower()==nl,
            lambda e,nl: nl in e.lower(),
            lambda e,nl: e.lower().startswith(nl),
        ]:
            try:
                for entry in os.listdir(root):
                    fp = os.path.join(root, entry)
                    if os.path.isdir(fp) and check(entry, nl): return fp, entry
            except: pass
        parent = os.path.dirname(root)
        if parent and parent != root: return self.find_best_match(name, parent)
        return None, None

    def do_cd(self, path):
        expanded = os.path.expanduser(path)
        test = expanded if os.path.isabs(expanded) else os.path.join(self.cwd, expanded)
        test = os.path.normpath(test)
        if os.path.isdir(test):
            os.chdir(test); self.cwd = os.getcwd(); self._rebuild()
            print(f"  📍 {self.cwd.replace(HOME,'~')}"); return True
        fp, m = self.find_best_match(os.path.basename(test),
            os.path.dirname(test) if os.path.isdir(os.path.dirname(test)) else None)
        if fp:
            os.chdir(fp); self.cwd = os.getcwd(); self._rebuild()
            print(f"  {C.DIM}→ '{m}'{C.RESET}\n  📍 {self.cwd.replace(HOME,'~')}"); return True
        dirs = self.list_dirs(self.cwd)
        if dirs: print(f"  {C.YELLOW}📂 Available: {', '.join(dirs[:10])}{C.RESET}")
        else: print(f"  {C.RED}📂 No dirs{C.RESET}")
        return False

    def do_mkdir(self, name):
        name = name.strip().strip("'\"")
        path = os.path.join(self.cwd, name)
        try:
            os.makedirs(path, exist_ok=True)
            print(f"  {C.GREEN}✅ Created '{name}'{C.RESET}")
            return True
        except Exception as e:
            print(f"  {C.RED}❌ {e}{C.RESET}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # FIX #1: `success` is now properly set from returncode
    # ═══════════════════════════════════════════════════════════════
    def run_cmd(self, cmd):
        t0 = time.time(); out=""; success=False; cancelled=False; ec = -1
        try:
            self._running_proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, cwd=self.cwd, preexec_fn=os.setsid)
            try:
                out,_ = self._running_proc.communicate(timeout=COMMAND_TIMEOUT)
                # FIX: Capture returncode and set success BEFORE finally block clears it
                ec = self._running_proc.returncode
                if ec == 0:
                    success = True
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(self._running_proc.pid), signal.SIGKILL)
                out = "⏱ timeout"; ec = -1
        except KeyboardInterrupt:
            if self._running_proc and self._running_proc.poll() is None:
                try: os.killpg(os.getpgid(self._running_proc.pid), signal.SIGKILL)
                except: self._running_proc.kill()
            out = "⛔ Cancelled"; cancelled = True; ec = -1; print()
        finally:
            self._running_proc = None
        duration = time.time() - t0
        r = CmdResult(success, out.strip(), ec, duration, cmd)
        self.log.append(r)
        # FIX: Show ✓ for success, ✗ for failure (was always ✗ before)
        if success:
            mark = f"{C.GREEN}✓{C.RESET}"
        elif cancelled:
            mark = f"{C.YELLOW}⛔{C.RESET}"
        else:
            mark = f"{C.RED}✗{C.RESET}"
        info = f" (exit {ec})" if not success and not cancelled and ec != -1 else ""
        print(f"  {mark} {C.GRAY}{cmd}{C.RESET}{info} ({duration:.2f}s)")
        if out.strip() and not cancelled:
            for line in out.strip().split("\n")[:15]:
                print(f"    {line}")
        elif not success and not out.strip() and not cancelled:
            if "mkdir" in cmd:
                print(f"    {C.DIM}(dir may already exist){C.RESET}")
        return r, cancelled

    # ═══════════════════════════════════════════════════════════════
    # FIX #2: No duplicate "thinking" block for initial response
    # ═══════════════════════════════════════════════════════════════
    def send_with_think(self, prompt_text):
        """Send to LLM and show response. Used for retries only."""
        print(f"\n{C.THINK}┌─ thinking ─────────────────────{C.RESET}")
        self.history.append({"role":"user","content":prompt_text})
        ok, resp = self.client.chat(self.history)
        print(f"{C.THINK}└─────────────────────────────────{C.RESET}")
        if ok:
            self.history.append({"role":"assistant","content":resp})
            if len(self.history) > MAX_HISTORY:
                self.history = [self.history[0]] + self.history[-(MAX_HISTORY-1):]
            return resp
        return None

    def is_hallucinating(self, resp, task):
        rl = resp.lower(); tl = task.lower()
        creds = ["github username","github credentials","git user","password","api key","ssh key"]
        needs_git = any(g in tl for g in ["git","push","pull","commit","clone","remote"])
        for kw in creds:
            if kw in rl and not needs_git: return True, f"Credential request '{kw}' unrelated"
        return False, None

    # ═══════════════════════════════════════════════════════════════
    # FIX #3: Clean auto-cycle — no false retries on success
    # ═══════════════════════════════════════════════════════════════
    def run_auto_cycle(self, resp, task=""):
        attempts = 0; max_auto = 3; last = ""
        for loop in range(10):
            if last and resp == last:
                attempts += 1
                if attempts >= max_auto:
                    print(f"  {C.YELLOW}❌ Repeating {attempts+1}x — resetting{C.RESET}")
                    if len(self.history) >= 2: self.history.pop()
                    resp = self.send_with_think(
                        f"Stop repeating. Task: {task[:100]}. Try different approach.")
                    if not resp: return; attempts = 0; last = ""; continue
            last = resp
            is_h, reason = self.is_hallucinating(resp, task)
            if is_h:
                print(f"  {C.YELLOW}⚠️ {reason}{C.RESET}")
                if len(self.history) >= 2: self.history.pop()
                resp = self.send_with_think(f"Stop asking for credentials. Task: {task[:100]}.")
                if not resp: return; continue
            cmds = self.extract_cmds(resp)
            if not cmds:
                if any(q in resp.lower() for q in ["what is","i need","please provide","tell me","enter your"]):
                    self._awaiting = True
                    print(f"\n  {C.BLUE}💬 [Codex needs your input]{C.RESET}")
                return
            all_ok = True
            for c in cmds:
                cd_m = re.match(r'^cd\s+(.+)$', c)
                if cd_m:
                    if not self.do_cd(cd_m.group(1)):
                        all_ok = False; attempts += 1
                        dirs = self.list_dirs(self.cwd)
                        ds = ", ".join(dirs[:15]) if dirs else "(none)"
                        if attempts >= max_auto:
                            print(f"  {C.YELLOW}❌ Can't find dir after {attempts} tries{C.RESET}")
                            self.send_with_think(
                                f"Can't find dir. Available: {ds}. Ask user for help.")
                            self._awaiting = True; return
                        else:
                            resp = self.send_with_think(
                                f"cd failed. Available: {ds}. Try a different dir.")
                            if not resp: return; break
                    continue
                mk_m = re.match(r'^mkdir\s+(.+)$', c)
                if mk_m: self.do_mkdir(mk_m.group(1)); continue
                r, cancelled = self.run_cmd(c)
                if cancelled: return
                if not r.success:
                    all_ok = False; attempts += 1
                    if attempts >= max_auto:
                        print(f"  {C.YELLOW}❌ Failed {attempts} times{C.RESET}")
                        self.send_with_think(
                            f"Failed {attempts}x:\n{r.command}\n{r.output[:400]}\nExplain the problem, ask user for help.")
                        self._awaiting = True; return
                    else:
                        resp = self.send_with_think(
                            f"Attempt {attempts+1} failed:\n{r.command}\n{r.output[:400]}\nTry a different approach.")
                        if not resp: return; break
            if all_ok:
                if attempts:
                    print(f"  {C.GREEN}✓ Done after {attempts+1} attempt(s){C.RESET}")
                return
        print(f"  {C.YELLOW}⚠️ Gave up.{C.RESET}")

    def handle_greeting(self):
        print(f"  {C.CYAN}{random.choice(['Hey!','Hi!','Yo!','Hello!'])} What's up?{C.RESET}")
    def handle_anger(self):
        print(f"  {C.YELLOW}Sorry, what's wrong?{C.RESET}")
    def handle_question(self, inp):
        self.history.append({"role":"user","content":f"Answer briefly: {inp}"})
        ok, resp = self.client.chat(self.history)
        if ok:
            self.history.append({"role":"assistant","content":resp})
            if len(self.history) > MAX_HISTORY:
                self.history = [self.history[0]] + self.history[-(MAX_HISTORY-1):]

    def run(self):
        os.system("clear")
        print(f"{C.BOLD}{C.CYAN}╔════════════════════════╗")
        print(f"║   ⚡ CODEX v3.1 AI   ║")
        print(f"╚════════════════════════╝{C.RESET}")
        print(f"  {C.YELLOW}{MODEL_NAME}{C.RESET}")
        print(f"  {C.GRAY}Direct: list, cd, mkdir, make a folder{C.RESET}")
        print(f"  {C.GRAY}:auto  :manual  exit{C.RESET}")
        print(f"{C.CYAN}{'─'*50}{C.RESET}")
        while True:
            try: inp = input(self.prompt_str()).strip()
            except (KeyboardInterrupt, EOFError): print(f"\n{C.CYAN}👋{C.RESET}"); break
            if not inp: continue
            if inp.lower() == "exit": break
            if inp.lower() in (":auto",":a"):
                self.mode="auto"; self._rebuild(); print(f"  {C.GREEN}⚡ Auto{C.RESET}"); continue
            if inp.lower() in (":manual",":m"):
                self.mode="manual"; self._rebuild(); print(f"  {C.YELLOW}🔒 Manual{C.RESET}"); continue

            cls = self.cls.classify(inp)
            if self._awaiting:
                self._awaiting = False
                self.history.append({"role":"user","content":inp})
                ok, resp = self.client.chat(self.history)
                if ok:
                    self.history.append({"role":"assistant","content":resp})
                    if self.mode == "auto": self.run_auto_cycle(resp, inp)
                continue
            if self._pending:
                if cls == "affirm":
                    for c in self._pending:
                        cd_m = re.match(r'^cd\s+(.+)$', c)
                        if cd_m: self.do_cd(cd_m.group(1))
                        else: self.run_cmd(c)
                    self._pending = None; continue
                elif cls == "reject": self._pending = None; continue
            if cls == "greeting": self.handle_greeting(); continue
            if cls == "anger": self.handle_anger(); continue
            if cls == "cd_cmd": self.do_cd(inp[3:].strip()); continue
            if cls == "question": self.handle_question(inp); continue

            # ── Simple commands (list, pwd, date) — no LLM ──
            if cls == "simple_cmd":
                self.run_cmd(SIMPLE_CMDS[inp.lower()]); continue

            # ── Direct mkdir ──
            if cls == "direct_op":
                m = re.match(r'mk(?:dir)?\s+(.+)$', inp)
                if not m: m = re.match(r'(?:make|create)\s+(?:a\s+)?(?:folder|dir|directory)\s+(.+)$', inp)
                if m: self.do_mkdir(m.group(1)); continue

            # ── LLM ──
            # FIX: Pass to LLM — no duplicate thinking wrapper here
            self.history.append({"role":"user","content":inp})
            ok, resp = self.client.chat(self.history)
            if not ok: self.history.pop(); continue
            if self.mode == "auto":
                self.run_auto_cycle(resp, inp)
            else:
                cmds = self.extract_cmds(resp)
                if cmds:
                    print(f"\n  {C.YELLOW}❓ Run {len(cmds)} command(s)? (yes/no){C.RESET}")
                    self._pending = cmds
            self.history.append({"role":"assistant","content":resp})
            if len(self.history) > MAX_HISTORY:
                self.history = [self.history[0]] + self.history[-(MAX_HISTORY-1):]

if __name__ == "__main__":
    CodexAgent().run()
