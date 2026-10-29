#!/usr/bin/env python3
"""STM32 學習進度 App（本機版）

只用 Python 標準函式庫，不需安裝任何套件。
- 資料存在 repo 的 learning/progress.json
- 每次存檔會同步產生 learning/README.md、learning/QUESTIONS.md、learning/notes/<代碼>.md
  （推到 GitHub 後，手機或任何裝置打開 repo 就能複習）
- 結束課題時自動 git commit；完成時加上 tag；有 remote 時自動 push

執行：雙擊 repo 根目錄的 STM32Tracker.exe（以 pythonw 在背景執行，不會出現終端機視窗）
      或 python tracker/app.py
介面用 Microsoft Edge 的 App 模式開成獨立視窗（沒有網址列／分頁）；找不到 Edge 時改用 Chrome，再不行才用預設瀏覽器。
關閉視窗後，App 會在幾秒內自動結束；也可以按右上角的「關閉 App」。
"""
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # repo 根目錄
LEARN = os.path.join(ROOT, "learning")
NOTES = os.path.join(LEARN, "notes")
DATA = os.path.join(LEARN, "progress.json")
PROJECTS = os.path.join(ROOT, "projects")
SKIP_DIRS = {"Debug", "Release", ".metadata", "__pycache__", ".git"}
SKIP_EXT = {".o", ".d", ".su", ".elf", ".hex", ".bin", ".map", ".list", ".cyclo", ".out", ".exe", ".obj"}
MAX_UPLOAD = 20 * 1024 * 1024
LOCK = threading.Lock()
PORT_FILE = os.path.join(HERE, ".app_port")       # 記錄執行中的連接埠，避免重複開啟
LOG_FILE = os.path.join(HERE, "app.log")
APP_ID = "stm32-tracker"
IS_WIN = sys.platform.startswith("win")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if IS_WIN else 0
CLIENT_TIMEOUT = 150      # 秒：分頁太久沒回報就視為已關閉（背景分頁計時器可能被瀏覽器降到每分鐘一次）
BYE_GRACE = 4             # 秒：分頁關閉後等這麼久，沒有新分頁就結束（重新整理不會誤關）
FIRST_CLIENT_WAIT = 180   # 秒：啟動後一直沒有瀏覽器連進來就結束
STATE = {"syncing": False, "sync_msg": ""}
CLIENTS = {}              # 分頁 id → 最後一次回報時間
WATCH = {"had_client": False, "empty_since": None, "started": time.time(), "quit": False}
ENTRY_TYPES = ("問題", "筆記", "解法")
STATUSES = ("未開始", "進行中", "已完成", "卡關", "暫緩")


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------- git
def git(*args, input_text=None, timeout=60):
    """執行 git，回傳 (成功, 輸出文字)。"""
    try:
        p = subprocess.run(
            ["git", "-c", "core.quotepath=false", *args],
            cwd=ROOT,
            input=input_text.encode("utf-8") if input_text is not None else None,
            stdin=None if input_text is not None else subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
            creationflags=NO_WINDOW,                       # 不要跳出黑色視窗
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},  # 沒有終端機，不能等待輸入
        )
    except FileNotFoundError:
        return False, "找不到 git，請先安裝 Git for Windows。"
    except subprocess.TimeoutExpired:
        return False, "git 執行逾時（可能在等待登入，請先在終端機手動 git push 一次）。"
    out = (p.stdout + p.stderr).decode("utf-8", "replace").strip()
    return p.returncode == 0, out


def git_info():
    ok, top = git("rev-parse", "--show-toplevel")
    if not ok:
        return {"is_repo": False}
    _, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    ok_r, remote = git("remote", "get-url", "origin")
    web = remote_to_web(remote) if ok_r else None
    _, log = git("log", "-8", "--pretty=format:%h\x1f%H\x1f%ad\x1f%s", "--date=format:%m-%d %H:%M")
    commits = []
    for line in log.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 4:
            commits.append({"short": parts[0], "hash": parts[1], "date": parts[2], "msg": parts[3]})
    _, status = git("status", "--porcelain")
    return {
        "is_repo": True,
        "branch": branch,
        "remote": remote if ok_r else None,
        "web": web,
        "commits": commits,
        "dirty": bool(status.strip()),
    }


def remote_to_web(url):
    url = url.strip()
    m = re.match(r"git@([^:]+):(.+?)(\.git)?$", url)
    if m:
        return f"https://{m.group(1)}/{m.group(2)}"
    m = re.match(r"https?://(?:[^@/]+@)?(.+?)(\.git)?$", url)
    if m:
        return f"https://{m.group(1)}"
    return None


def task_commits(task_id):
    _, log = git("log", "--all", "-30", "--fixed-strings", f"--grep={task_id}",
                 "--pretty=format:%h\x1f%H\x1f%ad\x1f%s", "--date=format:%Y-%m-%d %H:%M")
    res = []
    for line in log.splitlines():
        p = line.split("\x1f")
        if len(p) == 4:
            res.append({"short": p[0], "hash": p[1], "date": p[2], "msg": p[3]})
    return res


def commit_learning(message, tag=None):
    """提交 learning/，必要時打 tag 並 push。回傳訊息列表。"""
    msgs = []
    if not git_info().get("is_repo"):
        return ["（此資料夾不是 Git repo，只存在本機。）"]
    stage_all()
    ok, out = git("diff", "--cached", "--quiet")
    if ok:
        msgs.append("沒有新的變更需要 commit。")
    else:
        ok, out = git("commit", "-F", "-", input_text=message)
        msgs.append("已 commit。" if ok else "commit 失敗：" + out)
    if tag:
        ok_t, _ = git("rev-parse", "-q", "--verify", f"refs/tags/{tag}")
        if not ok_t:
            ok, out = git("tag", "-a", tag, "-F", "-", input_text=f"完成 {tag}")
            msgs.append(f"已建立 tag {tag}。" if ok else "建立 tag 失敗：" + out)
    msgs.append(push())
    return msgs


def push():
    ok_r, _ = git("remote", "get-url", "origin")
    if not ok_r:
        return "尚未設定 GitHub remote，只 commit 在本機。"
    ok, out = git("push", "--follow-tags", "-u", "origin", "HEAD", timeout=90)
    return "已 push 到 GitHub。" if ok else "push 失敗：" + out


def pull():
    ok_r, _ = git("remote", "get-url", "origin")
    if not ok_r:
        return False, "尚未設定 GitHub remote。"
    _, st = git("status", "--porcelain")
    if st.strip():
        commit_learning_quiet("自動儲存：同步前提交進度")
    ok, out = git("pull", "--rebase", "--autostash", timeout=90)
    return ok, ("已從 GitHub 取得最新進度。" if ok else "pull 失敗：" + out)


def stage_all():
    """筆記、程式碼，以及 App 本身（讓另一台電腦同步到新版 App）。"""
    git("add", "learning")
    if os.path.isdir(PROJECTS):
        git("add", "projects")
    for p in ("tracker", "README.md", "CLAUDE.md", ".gitignore", "STM32Tracker.exe"):
        if os.path.exists(os.path.join(ROOT, p)):
            git("add", "-A", "--", p)


def commit_learning_quiet(message):
    stage_all()
    ok, _ = git("diff", "--cached", "--quiet")
    if not ok:
        git("commit", "-F", "-", input_text=message)


# ---------------------------------------------------------------- data
def load():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def save(db):
    tmp = DATA + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA)
    export_markdown(db)


def find(db, tid):
    for t in db["tasks"]:
        if t["id"] == tid:
            return t
    raise KeyError(f"找不到任務 {tid}")


def export_markdown(db):
    os.makedirs(NOTES, exist_ok=True)
    tasks = db["tasks"]
    # 每項任務的筆記頁
    for t in tasks:
        path = os.path.join(NOTES, f"{t['id']}.md")
        if not t.get("entries") and not t.get("sessions") and not os.path.isdir(os.path.join(PROJECTS, t["id"])):
            if os.path.exists(path):
                os.remove(path)
            continue
        lines = [f"# {t['id']}：{t['title']}", ""]
        lines += [f"- 狀態：**{t['status']}**", f"- 週次：{t.get('week') or ''}　主題：{t.get('topic') or ''}"]
        if t.get("orig"):
            lines.append(f"- 對應原任務（HAL 版）：{t['orig']}")
        if t.get("sessions"):
            lines.append(f"- 進行次數：{len(t['sessions'])} 次（最近一次：{t['sessions'][-1]['start'][:10]}）")
        if t.get("finished_at"):
            lines.append(f"- 完成日期：{t['finished_at']}")
        if os.path.isdir(os.path.join(PROJECTS, t["id"])):
            lines.append(f"- 程式碼：[projects/{t['id']}](../../projects/{t['id']})")
        lines += ["", "## 任務內容", "", t.get("content") or "", "",
                  "## 完成標準", "", t.get("criteria") or "", ""]
        if t.get("summary"):
            lines += ["## 總結", "", t["summary"], ""]
        if t.get("entries"):
            lines += ["## 問題與筆記", ""]
            for e in t["entries"]:
                mark = ""
                if e["type"] == "問題":
                    mark = " ✅ 已解決" if e.get("resolved") else " ❓ 未解決"
                lines.append(f"### [{e['type']}] {e['time']}{mark}")
                lines += ["", e["text"], ""]
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines))

    # 總覽
    sprint = [t for t in tasks if t.get("plan") == "SPRINT"]
    done = sum(1 for t in sprint if t["status"] == "已完成")
    lines = ["# STM32 學習進度", "",
             f"2 個月衝刺：{done} / {len(sprint)} 完成（{round(done * 100 / max(1, len(sprint)))}%）　"
             f"最後更新：{now()}", "",
             "- [全部問題整理（複習用）](QUESTIONS.md)", "",
             "## 2 個月衝刺（暫存器版）", "",
             "| 代碼 | 任務 | 狀態 | 筆記 |", "|---|---|---|---|"]
    for t in sprint:
        link = f"[{len(t['entries'])} 則](notes/{t['id']}.md)" if (t.get("entries") or t.get("sessions")) else ""
        lines.append(f"| {t['id']} | {t['title']} | {t['status']} | {link} |")
    lines += ["", "## 原計畫（HAL 版）", "", "| 代碼 | 任務 | 狀態 | 筆記 |", "|---|---|---|---|"]
    for t in tasks:
        if t.get("plan") != "HAL":
            continue
        link = f"[筆記](notes/{t['id']}.md)" if t.get("entries") else ""
        lines.append(f"| {t['id']} | {t['title']} | {t['status']} | {link} |")
    with open(os.path.join(LEARN, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    # 問題集
    qs = [(t, e) for t in tasks for e in t.get("entries", []) if e["type"] in ("問題", "解法")]
    lines = ["# 問題整理（複習與面試用）", "", "未解決的問題排在最前面。", ""]
    open_q = [(t, e) for t, e in qs if e["type"] == "問題" and not e.get("resolved")]
    lines += [f"## ❓ 未解決（{len(open_q)}）", ""]
    for t, e in open_q:
        lines += [f"- **{t['id']}** {t['title']}（{e['time']}）", "", f"  {indent(e['text'])}", ""]
    lines += ["", "## ✅ 已解決的問題與解法", ""]
    for t in tasks:
        items = [e for e in t.get("entries", []) if (e["type"] == "解法") or (e["type"] == "問題" and e.get("resolved"))]
        if not items:
            continue
        lines += [f"### [{t['id']}](notes/{t['id']}.md) {t['title']}", ""]
        for e in items:
            lines += [f"- **{e['type']}**（{e['time']}）：", "", f"  {indent(e['text'])}", ""]
        lines.append("")
    with open(os.path.join(LEARN, "QUESTIONS.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def indent(text):
    return text.replace("\n", "\n  ")


def active_task(db):
    for t in db["tasks"]:
        s = t.get("sessions") or []
        if s and not s[-1].get("end"):
            return t
    return None


# ---------------------------------------------------------------- code files
def task_dir(tid):
    if not re.match(r"^[A-Za-z0-9_-]+$", tid or ""):
        raise ValueError("任務代碼不正確。")
    return os.path.join(PROJECTS, tid)


def safe_path(tid, rel):
    base = os.path.realpath(task_dir(tid))
    rel = (rel or "").replace("\\", "/").lstrip("/")
    parts = [x for x in rel.split("/") if x not in ("", ".")]
    if not parts or ".." in parts:
        raise ValueError("檔案路徑不正確。")
    full = os.path.realpath(os.path.join(base, *parts))
    if not full.startswith(base + os.sep):
        raise ValueError("檔案路徑不正確。")
    return full, parts


def skipped(parts):
    return any(p in SKIP_DIRS for p in parts[:-1]) or os.path.splitext(parts[-1])[1].lower() in SKIP_EXT


def list_files(tid):
    base = task_dir(tid)
    res = []
    if not os.path.isdir(base):
        return res
    for dp, dns, fns in os.walk(base):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
        for fn in sorted(fns):
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, base).replace(os.sep, "/")
            res.append({"path": rel, "size": os.path.getsize(full)})
            if len(res) >= 2000:
                return res
    return res


def read_text(tid, rel):
    full, _ = safe_path(tid, rel)
    with open(full, "rb") as f:
        data = f.read(300_000)
    if b"\0" in data[:4000]:
        return None
    for enc in ("utf-8", "big5", "gbk"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", "replace")


def open_folder(tid):
    d = task_dir(tid)
    os.makedirs(d, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(d)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", d])  # noqa: S603,S607
    else:
        subprocess.Popen(["xdg-open", d])  # noqa: S603,S607
    return d


# ---------------------------------------------------------------- prompts
CODE_EXT = {".c", ".h", ".py"}
CODE_SKIP = ("Drivers/", "Middlewares/", "CMSIS/")
CODE_BUDGET = 15000          # 求助提示詞最多附上的程式碼字數


def _task_block(t):
    lines = [f"- 代碼：{t['id']}（{t.get('week') or ''}／{t.get('topic') or ''}，預定 {t.get('period') or '未定'}）",
             f"- 課題：{t['title']}", "", "### 課題內容", t.get("content") or "（無）"]
    if t.get("output"):
        lines += ["", "### 產出物", t["output"]]
    lines += ["", "### 完成標準", t.get("criteria") or "（無）"]
    if t.get("orig"):
        lines += ["", f"### 對應的舊 HAL 版任務：{t['orig']}"]
    return lines


def _history_block(t, limit=6, skip=""):
    lines = []
    entries = [e for e in t.get("entries", []) if not (skip and e["text"] == skip)]
    open_q = [e for e in entries if e["type"] == "問題" and not e.get("resolved")]
    if open_q:
        lines += ["", "### 尚未解決的問題"] + [f"- （{e['time']}）{e['text']}" for e in open_q]
    others = [e for e in entries if not (e["type"] == "問題" and not e.get("resolved"))]
    if others:
        lines += ["", f"### 最近的筆記（最新 {min(limit, len(others))} 則）"]
        lines += [f"- [{e['type']}]（{e['time']}）{e['text']}" for e in others[-limit:]]
    return lines


def _entry_title(e):
    """筆記的第一行當標題（去掉 ** 粗體符號）。"""
    for line in e["text"].splitlines():
        line = line.strip().strip("*").strip()
        if line:
            return line[:80]
    return "（空白）"


def _previous_block(db, t):
    """上一課的重點：讓 Claude 知道我上一課學到哪、留下哪些 TODO。"""
    same = [x for x in db["tasks"] if x.get("plan") == t.get("plan")]
    idx = next((i for i, x in enumerate(same) if x["id"] == t["id"]), 0)
    before = same[:idx]
    prev = next((x for x in reversed(before) if x.get("sessions") or x.get("entries")), None)
    if not prev:
        return []
    lines = ["", f"## 上一課：{prev['id']}「{prev['title']}」（{prev['status']}）",
             f"- 完成標準：{prev.get('criteria') or '（無）'}"]
    if prev.get("summary"):
        lines.append(f"- 總結：{prev['summary']}")
    files = [f["path"] for f in _code_files(prev["id"])]
    if files:
        lines.append(f"- 程式碼（projects/{prev['id']}/）：" + "、".join(files[:12]))
    todos = []
    for e in prev.get("entries", []):
        for line in e["text"].splitlines():
            if "TODO" in line.upper():
                todos.append(line.strip().lstrip("-・ ").strip())
    if todos:
        lines += ["", "### 上一課留下的 TODO（看本課是否要處理）"] + [f"- {x}" for x in dict.fromkeys(todos)]
    ents = prev.get("entries", [])
    if ents:
        shown = ents[-40:]
        lines += ["", f"### 上一課學過的主題（筆記標題，共 {len(ents)} 則" + ("，列最新 40 則" if len(ents) > 40 else "") + "）"]
        lines += [f"- {_entry_title(e)}" if _entry_title(e).startswith("【") else f"- [{e['type']}] {_entry_title(e)}"
                  for e in shown]
    done = [x for x in before if x["status"] == "已完成" and x["id"] != prev["id"]]
    if done:
        lines += ["", "### 更早已完成的課題"] + [f"- {x['id']}「{x['title']}」" for x in done]
    return lines


STEP_EXPLAIN = [
    "## 每一步都要講清楚：為什麼、設了什麼、代表什麼、為什麼是這個順序",
    "1. **為什麼**：這一步的目的；不做或做錯會出現什麼實際現象（例如 LED 不亮、讀到錯的值、HardFault、超過規格）。",
    "2. **設了什麼、代表什麼**：等我自己查完、寫完之後再對答案（不要先給），用表格逐一列出：",
    "   `暫存器 | 欄位（bit） | 設定值（二進位／十六進位） | 代表什麼 | 為什麼選這個值`，",
    "   最後算出整個暫存器的預期值，讓我用 debugger 比對。",
    "3. **為什麼是這個順序**：和前後步驟的相依關係，順序反過來會發生什麼事。",
    "4. **HAL 對照：程式碼直接貼給我，差異讓我自己找**。不要叫我去打開 Cube 韌體包或舊的 HAL 專案找檔案；直接貼出相關 HAL 函式（例如 `HAL_GPIO_Init()`、`HAL_GPIO_WritePin()`）裡實際操作暫存器的關鍵片段，註明出自哪個檔案、哪個函式（例如 `stm32f1xx_hal_gpio.c` 的 `HAL_GPIO_Init()`）；可以刪掉參數檢查等無關的行，但保留暫存器操作與判斷式。舊 HAL 專案裡 CubeMX 產生的程式（例如 `MX_GPIO_Init()`、`SystemClock_Config()`）也一樣直接貼出。貼完後給我 2–4 個引導問題（例如「它怎麼決定寫 CRL 還是 CRH？」「ODR 是在寫 CRH 之前還是之後設定？」），**不要直接說出差異或答案**，等我回答後再確認、補充或修正。",
    "",
    "範例（S02 的 Flash latency 步驟）：",
    "- 為什麼：Flash 讀取時間固定約 41.7 ns，72 MHz 一個週期只有 13.9 ns；等待週期不夠 → CPU 讀到錯的指令 → 程式亂跑或 HardFault",
    "- 設了什麼：",
    "",
    "| 暫存器 | 欄位（bit） | 設定值 | 代表什麼 | 為什麼選這個值 |",
    "|---|---|---|---|---|",
    "| `FLASH->ACR` | LATENCY（2:0） | `010` | 2 個等待週期（2 WS） | 48 < SYSCLK ≤ 72 MHz 要 2 WS |",
    "| `FLASH->ACR` | PRFTBE（4） | `1` | 開啟 Prefetch | 等待週期 > 0 時用預取補回效能 |",
    "",
    "- 預期值：`0x32`（PRFTBS 唯讀，硬體回報為 1）",
    "- 為什麼是這個順序：要在 SW 切到 PLL **之前**設定；先升頻再設的話，中間那段 72 MHz、0 WS 連設定 latency 的指令都可能讀錯",
    "- 對照 HAL：`HAL_RCC_ClockConfig()` 的第二個參數 `FLatency = FLASH_LATENCY_2`，HAL 會依升頻或降頻決定在切換前或切換後設定",
]


WRAP_UP = [
    "## 收尾總整理（驗收通過後一定要做）",
    "從頭到尾把整堂課重講一次，整理成**一則**可以直接貼進 App 的【解法】筆記（放在 ```markdown 區塊），標題用「【解法】<課題代碼> 總整理：從頭到尾每一步」：",
    "1. **整體流程**：一行一步的流程圖（例如 `開 RCC 時脈 → 設定模式 → 寫入輸出`），讓我一眼看出順序。",
    "2. **每一步依序說明**（每步一個小標題）：",
    "   - 為什麼要做：目的，以及不做或做錯會出現什麼現象",
    "   - 設了什麼、代表什麼：表格 `暫存器 | 欄位（bit） | 設定值 | 代表什麼 | 為什麼選這個值`",
    "   - 為什麼排在這裡：跟前一步、後一步的相依關係，順序反過來會怎樣",
    "3. **最終暫存器值總表**：每個用到的暫存器的最終值（十六進位），以及我實際用 debugger 量到的值，兩者是否一致。",
    "4. **我這堂課踩過的錯**：一行一個，寫出錯在哪、正確做法（引用筆記標題）。",
    "5. **對照 HAL**：每一步對應 HAL 的哪個函式或結構欄位，貼出 HAL 的關鍵程式片段（註明檔案與函式）和自寫版並排；這時我已經回答過引導問題，可以直接整理差異與 HAL 為什麼多做那些事。",
    "6. **面試版 30 秒說明**：如果面試官問「你怎麼用暫存器做 <本課主題>？」，我可以怎麼回答。",
]


NOTE_FORMAT = [
    "## 筆記格式（每次幫我整理重點都照這個格式）",
    "App 會用 Markdown 顯示筆記。每則筆記放在**獨立的 ```markdown 程式碼區塊**裡，方便我一鍵複製貼進 App；一則只講一個主題。",
    "- 第 1 行：`【筆記】`、`【問題】` 或 `【解法】` 加標題（對應 App 的三種類型；踩到的錯誤用【問題】，正確做法用【解法】）",
    "- 第 2 行：**一句話重點**（粗體）",
    "- 之後：條列說明，一行一個重點；對照、bit 定義、比較用 Markdown 表格；暫存器、巨集、程式碼用 `反引號`，多行程式用程式碼區塊",
    "- 表格儲存格裡要寫 `|` 時（例如 `REG |= Msk`），寫成 `\\|`，避免被當成欄位分隔",
    "- 整理某個步驟時，用「為什麼／設了什麼（表格）／代表什麼／為什麼是這個順序」的結構，表格附上預期的暫存器值",
    "- 驗收題的答案寫成面試可以直接講的版本",
    "- 不要用 ①②③、㉞、「步驟 2」、「第 3 點」這類編號指涉前面的內容，讀的人得回頭找編號是什麼；每次提到都直接寫出內容，例如「開 GPIOC 時脈（`RCC_APB2ENR` 的 `IOPCEN`）」、「設定 PC13 模式（`GPIOC->CRH`）」。列清單時可以編號，但後文引用時要寫出名稱。引用之前的筆記時寫出筆記標題。",
    "",
    "範例：",
    "````markdown",
    "【筆記】RCC_CR 的 HSE 相關 bit",
    "**HSEON 開啟 HSE，HSERDY 由硬體回報已穩定**",
    "",
    "| bit | 名稱 | 屬性 | 意義 |",
    "|---|---|---|---|",
    "| 16 | HSEON | rw | 1 = 開啟 HSE |",
    "| 17 | HSERDY | r | 1 = HSE 已穩定（硬體設定） |",
    "",
    "- 命名規律：結尾 **ON** 是開關（rw）、結尾 **RDY** 是就緒旗標（r）",
    "- 本板接被動石英 → HSEBYP 設 `0`",
    "````",
]


def _code_files(tid):
    return [f for f in list_files(tid)
            if os.path.splitext(f["path"])[1].lower() in CODE_EXT and not any(s in f["path"] for s in CODE_SKIP)]


def build_prompt(db, tid, kind="start", stuck_text=""):
    t = find(db, tid)
    files = list_files(tid)
    n = len(t.get("sessions") or [])
    rel = f"projects/{tid}/"
    web = (git_info().get("web") or "")
    if kind == "start":
        first = n <= 1 and not t.get("entries")
        lines = [f"我要{'開始' if first else '繼續'} STM32 學習課題 {tid}「{t['title']}」。"
                 + ("" if first else (f"這是第 {n} 次進行，" if n > 1 else "這個課題已經有進度，")
                    + "請從下面的筆記接續，不用從頭講。"),
                 "我的背景、硬體與 2 個月衝刺計畫在專案說明（CLAUDE.md／STM32學習背景與進度）裡。", "",
                 "## 本課題"] + _task_block(t) + _history_block(t)
        lines += _previous_block(db, t)
        if files:
            lines += ["", f"### 目前的程式碼（{rel}，共 {len(files)} 個檔案）"]
            lines += [f"- {f['path']}" for f in _code_files(tid)[:30]] or ["- （沒有 .c/.h/.py 檔）"]
        lines += ["", "## 請這樣帶我",
                  "0. 先看「上一課」：用 2–3 句說明本課怎麼接續上一課（沿用哪些檔案或函式、上一課的 TODO 本課要不要處理）；我上一課已經學過的觀念直接引用，不要重講。",
                  "1. 用 3–5 句說明這個課題要練什麼、為什麼 IC 設計公司的韌體工程師需要會，以及最後怎麼驗收（對照完成標準）。",
                  "2. 把課題拆成 3–6 個小步驟，每一步附一句「為什麼要做、為什麼排在這裡」；列出清單後**一次只帶一步**，等我回報結果再進下一步。",
                  "3. 涉及暫存器的步驟：先問我要查 RM0008 哪一章、哪個暫存器、哪幾個 bit，讓我自己查完再寫程式；完成後和 HAL 版比較：HAL 的程式碼直接貼給我，差異讓我自己找，不要直接告訴我答案。",
                  "4. 不要一次給完整答案。我卡住時先給方向提示，第二次還卡住再給關鍵程式片段並解釋。",
                  "4.5 每一步都照下面「每一步都要講清楚」的四點說明；「為什麼」可以先講，「設定值」等我查完再對答案。",
                  "5. 每完成一個步驟，或我踩到值得記的錯誤時，主動用下面的「筆記格式」幫我整理，讓我貼進 App。",
                  "6. 最後依完成標準逐條驗收我（包含口頭解釋），全部通過後做下面的「收尾總整理」，才算完成。",
                  "7. 請用繁體中文。不要用 ①②③、㉞、「步驟 2」、「第 3 點」這類編號指涉前面的內容，讀的人得回頭找編號是什麼；每次提到都直接寫出內容，例如「開 GPIOC 時脈（`RCC_APB2ENR` 的 `IOPCEN`）」、「設定 PC13 模式（`GPIOC->CRH`）」。列清單時可以編號，但後文引用時要寫出名稱。", ""] + STEP_EXPLAIN + [""] + WRAP_UP + [""] + NOTE_FORMAT + ["",
                  "準備好了就從第 0 點開始。"]
    else:
        lines = [f"我在 STM32 學習課題 {tid}「{t['title']}」卡關了，需要協助。", "",
                 "## 卡在哪裡", stuck_text.strip() or "（請先問我卡在哪裡）", "",
                 "## 課題資訊"] + _task_block(t) + _history_block(t, limit=8, skip="【卡關】" + stuck_text.strip())
        code = _code_files(tid)
        if code:
            lines += ["", f"## 目前的程式碼（{rel}）"]
            used = 0
            for f in code:
                text = read_text(tid, f["path"]) or ""
                if used + len(text) > CODE_BUDGET:
                    lines.append(f"- {f['path']}（太長未附上）")
                    continue
                used += len(text)
                lang = "python" if f["path"].endswith(".py") else "c"
                lines += ["", f"`{f['path']}`", f"```{lang}", text.rstrip(), "```"]
        else:
            lines += ["", "## 程式碼", "（App 裡還沒有這個課題的程式碼，我會另外貼上相關片段。）"]
        if web:
            lines += ["", f"GitHub：{web}/tree/HEAD/{rel}"]
        lines += ["", "## 請這樣幫我",
                  "1. 先問我 1–3 個釐清問題（例如：完整錯誤訊息、debugger 看到的暫存器值、LED／波形實際表現），不要急著給答案。",
                  "2. 列出最可能的 2–3 個原因，每個原因給一個我能自己驗證的檢查方法（看哪個暫存器、量哪支腳、加哪行測試）。",
                  "3. 等我回報結果再縮小範圍；確定原因後才給修正方向，必要時附上關鍵片段，並說明修正後每個暫存器設定值代表什麼、為什麼這樣設、順序為什麼重要。",
                  "4. 解決後用下面的「筆記格式」幫我整理：踩到的錯誤一則【問題】、正確做法一則【解法】，面試時也能講。",
                  "5. 請用繁體中文。不要用 ①②③、㉞、「步驟 2」、「第 3 點」這類編號指涉前面的內容，讀的人得回頭找編號是什麼；每次提到都直接寫出內容，例如「開 GPIOC 時脈（`RCC_APB2ENR` 的 `IOPCEN`）」、「設定 PC13 模式（`GPIOC->CRH`）」。列清單時可以編號，但後文引用時要寫出名稱。", ""] + NOTE_FORMAT
    return "\n".join(lines)


# ---------------------------------------------------------------- actions
def act_start(db, body):
    t = find(db, body["id"])
    msgs = []
    cur = active_task(db)
    if cur and cur["id"] != t["id"]:
        cur["sessions"][-1]["end"] = now()
        msgs.append(f"已暫停 {cur['id']}。")
    if not (t["sessions"] and not t["sessions"][-1].get("end")):
        # 記下開始前的狀態，「暫時離開」時可以還原
        t["sessions"].append({"start": now(), "end": None,
                              "prev_status": t["status"], "prev_finished": t.get("finished_at")})
    t["status"] = "進行中"
    t["finished_at"] = None
    save(db)
    msgs.append(f"開始 {t['id']}。")
    return {"messages": msgs, "prompt": build_prompt(db, t["id"], "start"), "prompt_kind": "start"}


def act_leave(db, body):
    """暫時離開：結束這次但不 commit、不改變課題狀態。
    這次沒有新增任何紀錄（例如誤按開始）時，連這次的進行紀錄都不留，狀態還原成開始前。"""
    t = find(db, body["id"])
    s = t["sessions"][-1] if t["sessions"] and not t["sessions"][-1].get("end") else None
    if not s:
        return ["這個課題目前沒有在進行。"]
    added = [e for e in t.get("entries", []) if e["time"] >= s["start"]]
    if added:
        s["end"] = now()
        msg = f"已暫時離開 {t['id']}（這次新增的 {len(added)} 則紀錄已存在本機，下次同步時一起上傳）。"
    else:
        t["sessions"].pop()
        t["status"] = s.get("prev_status") or ("進行中" if t["sessions"] else "未開始")
        t["finished_at"] = s.get("prev_finished")
        msg = f"已離開 {t['id']}，沒有任何變更。"
    save(db)
    return [msg]


def act_restart(db, body):
    """誤按開始或想從頭來過：清掉這個課題的進行紀錄、筆記與總結，當成第一次重新開始。
    projects/<代碼>/ 裡的程式碼不會刪除。"""
    t = find(db, body["id"])
    t["sessions"] = []
    t["entries"] = []
    t["summary"] = None
    t["finished_at"] = None
    t["status"] = "未開始"
    if not body.get("start", True):
        save(db)
        return ["已重設為「未開始」。"]
    res = act_start(db, {"id": t["id"]})
    res["messages"].insert(0, f"已清除 {t['id']} 的紀錄，重新開始。")
    return res


def act_entry(db, body):
    t = find(db, body["id"])
    typ = body.get("type", "筆記")
    text = (body.get("text") or "").strip()
    if typ not in ENTRY_TYPES or not text:
        raise ValueError("請輸入內容。")
    t["entries"].append({"time": now(), "type": typ, "text": text,
                         "resolved": False if typ == "問題" else None})
    save(db)
    return ["已儲存。"]


def act_entry_update(db, body):
    t = find(db, body["id"])
    e = t["entries"][int(body["index"])]
    if "text" in body:
        e["text"] = body["text"].strip()
    if "resolved" in body and e["type"] == "問題":
        e["resolved"] = bool(body["resolved"])
    save(db)
    return ["已更新。"]


def act_entry_delete(db, body):
    t = find(db, body["id"])
    t["entries"].pop(int(body["index"]))
    save(db)
    return ["已刪除。"]


def act_finish(db, body):
    t = find(db, body["id"])
    done = bool(body.get("done"))
    summary = (body.get("summary") or "").strip()
    status = "已完成" if done else (body.get("status") if body.get("status") in STATUSES else "進行中")
    if status == "卡關" and not summary:
        raise ValueError("選擇「卡關」時，請描述卡在哪裡（這段會變成求助提示詞）。")
    if t["sessions"] and not t["sessions"][-1].get("end"):
        t["sessions"][-1]["end"] = now()
    n = len(t["sessions"])
    if done:
        t["status"] = "已完成"
        t["finished_at"] = datetime.now().strftime("%Y-%m-%d")
        if summary:
            t["summary"] = summary
        head = f"{t['id']}: 完成 {t['title']}"
    elif status == "卡關":
        t["status"] = "卡關"
        t["entries"].append({"time": now(), "type": "問題", "text": "【卡關】" + summary, "resolved": False})
        head = f"{t['id']}: 卡關 {t['title']}"
    else:
        t["status"] = status
        if summary:   # 每次的進度都保留，不會互相覆蓋
            t["entries"].append({"time": now(), "type": "筆記", "text": "【本次進度】" + summary, "resolved": None})
        head = f"{t['id']}: 進度 {t['title']}（第 {n} 次）"
    save(db)
    msg = f"{head}\n\n狀態：{t['status']}"
    if summary:
        msg += f"\n\n{summary}"
    msgs = commit_learning(msg, tag=t["id"] if done else None)
    if status == "卡關":
        return {"messages": msgs, "prompt": build_prompt(db, t["id"], "stuck", summary), "prompt_kind": "stuck"}
    return msgs


def act_status(db, body):
    t = find(db, body["id"])
    if body.get("status") not in STATUSES:
        raise ValueError("狀態不正確。")
    t["status"] = body["status"]
    if t["status"] == "已完成" and not t.get("finished_at"):
        t["finished_at"] = datetime.now().strftime("%Y-%m-%d")
    save(db)
    return ["狀態已更新。"]


def act_open_folder(db, body):
    find(db, body["id"])
    d = open_folder(body["id"])
    return [f"已開啟資料夾：{d}"]


def act_delete_file(db, body):
    find(db, body["id"])
    full, _ = safe_path(body["id"], body.get("path"))
    os.remove(full)
    return ["已刪除檔案。"]


def act_sync(db, body):
    ok, m = pull()
    msgs = [m]
    if ok:
        msgs.append(push())
    return msgs


ACTIONS = {
    "/api/start": act_start,
    "/api/restart": act_restart,
    "/api/leave": act_leave,
    "/api/entry": act_entry,
    "/api/entry/update": act_entry_update,
    "/api/entry/delete": act_entry_delete,
    "/api/finish": act_finish,
    "/api/status": act_status,
    "/api/sync": act_sync,
    "/api/open-folder": act_open_folder,
    "/api/file/delete": act_delete_file,
}


# ---------------------------------------------------------------- http
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send(self, code, data, ctype="application/json; charset=utf-8"):
        body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/favicon.ico":
            with open(os.path.join(HERE, "app.ico"), "rb") as f:
                return self.send(200, f.read(), "image/x-icon")
        if u.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                return self.send(200, f.read(), "text/html; charset=utf-8")
        if u.path == "/api/state":
            if STATE["syncing"]:
                return self.send(200, {"syncing": True})
            with LOCK:
                db = load()
            return self.send(200, {"tasks": db["tasks"], "git": git_info(), "now": now(),
                                   "sync_msg": STATE.pop("sync_msg", "") or ""})
        if u.path == "/api/ping":
            cid = parse_qs(u.query).get("c", [""])[0]
            if cid:
                CLIENTS[cid] = time.time()
                WATCH["had_client"] = True
            return self.send(200, {"app": APP_ID})
        if u.path == "/api/prompt":
            q = parse_qs(u.query)
            try:
                with LOCK:
                    db = load()
                kind = q.get("kind", ["start"])[0]
                text = build_prompt(db, q.get("id", [""])[0], kind, q.get("stuck", [""])[0])
            except (KeyError, ValueError) as e:
                return self.send(400, {"error": str(e)})
            return self.send(200, {"prompt": text})
        if u.path == "/api/files":
            tid = parse_qs(u.query).get("id", [""])[0]
            try:
                return self.send(200, {"files": list_files(tid), "dir": os.path.relpath(task_dir(tid), ROOT).replace(os.sep, "/")})
            except ValueError as e:
                return self.send(400, {"error": str(e)})
        if u.path == "/api/file":
            q = parse_qs(u.query)
            try:
                text = read_text(q.get("id", [""])[0], q.get("path", [""])[0])
            except (ValueError, OSError) as e:
                return self.send(400, {"error": str(e)})
            return self.send(200, {"text": text})
        if u.path == "/api/commits":
            tid = parse_qs(u.query).get("id", [""])[0]
            return self.send(200, {"commits": task_commits(tid) if tid else []})
        self.send(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        # 只接受本機頁面發出的請求
        origin = self.headers.get("Origin")
        if origin and not re.match(r"^http://(127\.0\.0\.1|localhost):\d+$", origin):
            return self.send(403, {"error": "forbidden"})
        if u.path == "/api/upload":
            return self.upload(parse_qs(u.query))
        if u.path == "/api/bye":            # 分頁關閉（navigator.sendBeacon）
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            CLIENTS.pop(parse_qs(u.query).get("c", [""])[0], None)
            return self.send(200, {"ok": True})
        if u.path == "/api/open-url":       # 外部連結（GitHub）用預設瀏覽器開，不在 App 視窗裡開
            n = int(self.headers.get("Content-Length") or 0)
            link = (json.loads(self.rfile.read(n) or b"{}").get("url") or "")
            if re.match(r"^https://", link):
                webbrowser.open(link)
            return self.send(200, {"ok": True})
        if u.path == "/api/quit":           # 頁面上的「關閉 App」
            WATCH["quit"] = True
            return self.send(200, {"ok": True})
        fn = ACTIONS.get(u.path)
        if not fn:
            return self.send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
            with LOCK:
                db = load()
                res = fn(db, body)
            out = res if isinstance(res, dict) else {"messages": res}
            self.send(200, {"ok": True, **out})
        except (KeyError, ValueError, IndexError) as e:
            self.send(400, {"ok": False, "error": str(e)})
        except Exception as e:  # noqa: BLE001
            self.send(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})


def _upload(self, q):
    try:
        tid = q.get("id", [""])[0]
        with LOCK:
            find(load(), tid)
        full, parts = safe_path(tid, q.get("path", [""])[0])
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_UPLOAD:
            self.rfile.read(n)
            return self.send(400, {"ok": False, "error": f"{parts[-1]} 超過 20 MB，略過。"})
        data = self.rfile.read(n)
        if skipped(parts):
            return self.send(200, {"ok": True, "skipped": True})
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(data)
        self.send(200, {"ok": True})
    except (KeyError, ValueError, OSError) as e:
        self.send(400, {"ok": False, "error": str(e)})


Handler.upload = _upload


def free_port(start=8765):
    for port in range(start, start + 20):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("找不到可用的連接埠")


def log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
    except OSError:
        pass


def alert(msg):
    """沒有終端機視窗時，用 Windows 對話框顯示錯誤。"""
    log(msg)
    print(msg)
    if IS_WIN:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, msg, "STM32 學習進度", 0x10)
        except Exception:  # noqa: BLE001
            pass


WINDOW_SIZE = (1200, 900)


def find_app_browser():
    """找 Edge（Windows 內建）或 Chrome，用來開 App 模式視窗。"""
    if os.environ.get("STM32_BROWSER"):
        return os.environ["STM32_BROWSER"]
    if not IS_WIN:
        return None
    roots = [os.environ.get(k) for k in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
    rels = [r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"]
    for rel in rels:                       # Edge 優先
        for root in roots:
            if root and os.path.isfile(os.path.join(root, rel)):
                return os.path.join(root, rel)
    return None


def watch_window(proc):
    """保險：視窗程序結束（例如被強制關閉、沒送出關閉通知）時，也讓 App 結束。"""
    t0 = time.time()
    proc.wait()
    if time.time() - t0 < 5:      # 立刻結束代表交給了已開著的視窗，不算關閉
        return
    time.sleep(6)                 # 若還有其他視窗，它們會在這段時間內回報
    cutoff = time.time() - 6.5
    for k, seen in list(CLIENTS.items()):
        if seen < cutoff:
            CLIENTS.pop(k, None)
    WATCH["had_client"] = True


def open_window(url, watch=False):
    """以獨立視窗開啟 App；失敗時退回預設瀏覽器。"""
    exe = find_app_browser()
    if exe:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        profile = os.path.join(base, "STM32Tracker", "window")   # 專用設定檔：不影響你平常的瀏覽器
        first = not os.path.isdir(profile)
        args = [exe, f"--app={url}", f"--user-data-dir={profile}", "--no-first-run",
                "--no-default-browser-check", "--disable-sync", "--disable-features=Translate"]
        if first:                          # 第一次給預設大小，之後沿用你調整過的視窗大小與位置
            args.append(f"--window-size={WINDOW_SIZE[0]},{WINDOW_SIZE[1]}")
        try:
            proc = subprocess.Popen(args, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL,  # noqa: S603
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if watch:
                threading.Thread(target=watch_window, args=(proc,), daemon=True).start()
            return
        except OSError as e:
            log(f"無法開啟 App 視窗（{exe}）：{e}")
    webbrowser.open(url)


def running_instance():
    """如果 App 已經在執行，回傳它的網址。"""
    try:
        with open(PORT_FILE, encoding="utf-8") as f:
            port = int(f.read().strip())
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=1.5) as r:  # noqa: S310
            if json.loads(r.read()).get("app") == APP_ID:
                return f"http://127.0.0.1:{port}/"
    except (OSError, ValueError):
        pass
    return None


def startup_sync():
    gi = git_info()
    if gi.get("is_repo") and gi.get("remote"):
        with LOCK:
            ok, msg = pull()
            if ok:                        # 本機還沒推上去的 commit 也一起推，另一台電腦才拿得到
                msg += "\n" + push()
            try:
                export_markdown(load())
            except Exception:  # noqa: BLE001
                pass
        STATE["sync_msg"] = msg if ok else "⚠ " + msg
        log(msg)
    elif not gi.get("is_repo"):
        STATE["sync_msg"] = "提醒：這個資料夾還不是 Git repo，筆記只會存在本機。"
    STATE["syncing"] = False


def watchdog(srv):
    """所有分頁都關閉後自動結束程式（不會留下背景程式）。"""
    last = time.time()
    while True:
        time.sleep(1)
        t = time.time()
        if t - last > 10:                 # 電腦剛從睡眠醒來：給分頁時間重新回報
            for k in list(CLIENTS):
                CLIENTS[k] = t
            WATCH["empty_since"] = None
        last = t
        if LOCK.locked() or STATE["syncing"]:   # 正在 commit／push，等它做完
            continue
        if WATCH["quit"]:
            break
        for k, seen in list(CLIENTS.items()):
            if t - seen > CLIENT_TIMEOUT:
                CLIENTS.pop(k, None)
        if not WATCH["had_client"]:
            if t - WATCH["started"] > FIRST_CLIENT_WAIT:
                log("沒有瀏覽器連線，自動結束。")
                break
            continue
        if CLIENTS:
            WATCH["empty_since"] = None
        elif WATCH["empty_since"] is None:
            WATCH["empty_since"] = t
        elif t - WATCH["empty_since"] > BYE_GRACE:
            break
    log("App 結束。")
    srv.shutdown()


def main():
    if not os.path.exists(DATA):
        alert(f"找不到 learning/progress.json\n\n請確認 STM32Tracker.exe 放在 repo 根目錄。\n目前位置：{ROOT}")
        sys.exit(1)
    url = running_instance()
    if url:                                 # 已經開著：只再開一個視窗
        open_window(url)
        return
    try:
        if os.path.getsize(LOG_FILE) > 200_000:
            os.remove(LOG_FILE)
    except OSError:
        pass
    with LOCK:
        export_markdown(load())
    port = free_port()
    url = f"http://127.0.0.1:{port}/"
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    with open(PORT_FILE, "w", encoding="utf-8") as f:
        f.write(str(port))
    log(f"App 啟動：{url}")
    print(f"STM32 學習進度 App 已啟動：{url}（關閉視窗即結束）")
    STATE["syncing"] = True
    threading.Thread(target=startup_sync, daemon=True).start()
    threading.Thread(target=watchdog, args=(srv,), daemon=True).start()
    if "--no-browser" not in sys.argv:
        threading.Timer(0.2, lambda: open_window(url, watch=True)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        try:
            os.remove(PORT_FILE)
        except OSError:
            pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        alert("App 發生錯誤，無法啟動：\n\n" + traceback.format_exc()[-1500:])
        sys.exit(1)
