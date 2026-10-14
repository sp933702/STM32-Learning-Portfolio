#!/usr/bin/env python3
"""STM32 學習進度 App（本機版）

只用 Python 標準函式庫，不需安裝任何套件。
- 資料存在 repo 的 learning/progress.json
- 每次存檔會同步產生 learning/README.md、learning/QUESTIONS.md、learning/notes/<代碼>.md
  （推到 GitHub 後，手機或任何裝置打開 repo 就能複習）
- 結束課題時自動 git commit；完成時加上 tag；有 remote 時自動 push

執行：雙擊 repo 根目錄的 STM32Tracker.exe（以 pythonw 在背景執行，不會出現終端機視窗）
      或 python tracker/app.py
關閉瀏覽器分頁後，App 會在幾秒內自動結束；也可以按頁面右上角的「關閉 App」。
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
SKIP_EXT = {".o", ".d", ".su", ".elf", ".hex", ".bin", ".map", ".list", ".cyclo"}
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
    git("add", "learning")
    if os.path.isdir(PROJECTS):
        git("add", "projects")
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


def commit_learning_quiet(message):
    git("add", "learning")
    if os.path.isdir(PROJECTS):
        git("add", "projects")
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
        lines += [f"- **{t['id']}** {t['title']}（{e['time']}）", f"  {indent(e['text'])}"]
    lines += ["", "## ✅ 已解決的問題與解法", ""]
    for t in tasks:
        items = [e for e in t.get("entries", []) if (e["type"] == "解法") or (e["type"] == "問題" and e.get("resolved"))]
        if not items:
            continue
        lines += [f"### [{t['id']}](notes/{t['id']}.md) {t['title']}", ""]
        for e in items:
            lines += [f"- **{e['type']}**（{e['time']}）：{indent(e['text'])}"]
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
                 + ("" if first else f"這是第 {n} 次進行，請從上次的進度接續，不用從頭講。"),
                 "我的背景、硬體與 2 個月衝刺計畫在專案說明（CLAUDE.md／STM32學習背景與進度）裡。", "",
                 "## 本課題"] + _task_block(t) + _history_block(t)
        if files:
            lines += ["", f"### 目前的程式碼（{rel}，共 {len(files)} 個檔案）"]
            lines += [f"- {f['path']}" for f in _code_files(tid)[:30]] or ["- （沒有 .c/.h/.py 檔）"]
        lines += ["", "## 請這樣帶我",
                  "1. 先用 3–5 句說明這個課題要練什麼、為什麼 IC 設計公司的韌體工程師需要會，以及最後怎麼驗收（對照完成標準）。",
                  "2. 把課題拆成 3–6 個小步驟，列出清單後**一次只帶一步**，等我回報結果再進下一步。",
                  "3. 涉及暫存器的步驟：先問我要查 RM0008 哪一章、哪個暫存器、哪幾個 bit，讓我自己查完再寫程式；完成後和舊 HAL 版比較差異。",
                  "4. 不要一次給完整答案。我卡住時先給方向提示，第二次還卡住再給關鍵程式片段並解釋。",
                  "5. 遇到值得記的觀念或錯誤，提醒我在 App 記成「問題／筆記／解法」。",
                  "6. 最後依完成標準逐條驗收我（包含口頭解釋），全部通過才算完成。",
                  "7. 請用繁體中文。", "",
                  "準備好了就從第 1 點開始。"]
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
                  "3. 等我回報結果再縮小範圍；確定原因後才給修正方向，必要時附上關鍵片段並解釋為什麼。",
                  "4. 解決後幫我整理一段「原因＋解法」，讓我記到 App 的「解法」，面試時也能講。",
                  "5. 請用繁體中文。"]
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
        t["sessions"].append({"start": now(), "end": None})
    t["status"] = "進行中"
    t["finished_at"] = None
    save(db)
    msgs.append(f"開始 {t['id']}。")
    return {"messages": msgs, "prompt": build_prompt(db, t["id"], "start"), "prompt_kind": "start"}


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
    if url:                                 # 已經開著：只打開瀏覽器
        webbrowser.open(url)
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
    print(f"STM32 學習進度 App 已啟動：{url}（關閉瀏覽器分頁即結束）")
    STATE["syncing"] = True
    threading.Thread(target=startup_sync, daemon=True).start()
    threading.Thread(target=watchdog, args=(srv,), daemon=True).start()
    if "--no-browser" not in sys.argv:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
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
