#!/usr/bin/env python3
"""STM32 學習進度 App（新版，tracker2）

和舊版 App（tracker/，STM32Tracker.exe）並行，兩者共用 learning/progress.json。
共用資料的規則：只新增欄位，不改名、不刪除舊版在用的欄位。兩個 App 不要同時開啟。

只用 Python 標準函式庫，不需安裝任何套件。
- 資料存在 repo 的 learning/progress.json
- 每次存檔會同步產生 learning/README.md、learning/QUESTIONS.md、learning/notes/<代碼>.md
- 結束課題時自動 git commit；完成時加上 tag；有 remote 時自動 push
- 提示詞的規則放在 tracker2/prompts/*.md，改檔就生效

執行：雙擊 repo 根目錄的 STM32Tracker2.exe（以 pythonw 在背景執行，不會出現終端機視窗）
      或 python tracker2/app.py
修改這個資料夾後，請執行 python tracker2/selftest.py 檢查。
"""
import hashlib
import json
import os
import random
import re
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import uuid
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT_OVERRIDE = os.environ.get("STM32_TRACKER_ROOT")   # 測試用：改用另一份資料，不動到真正的 repo
ROOT = _ROOT_OVERRIDE or os.path.dirname(HERE)     # repo 根目錄
RUN_DIR = ROOT if _ROOT_OVERRIDE else HERE         # 連接埠檔與紀錄檔的位置
LEARN = os.path.join(ROOT, "learning")
NOTES = os.path.join(LEARN, "notes")
DATA = os.path.join(LEARN, "progress.json")
PROJECTS = os.path.join(ROOT, "projects")
SKIP_DIRS = {"Debug", "Release", ".metadata", "__pycache__", ".git"}
SKIP_EXT = {".o", ".d", ".su", ".elf", ".hex", ".bin", ".map", ".list", ".cyclo", ".out", ".exe", ".obj"}
MAX_UPLOAD = 20 * 1024 * 1024
LOCK = threading.Lock()
PORT_FILE = os.path.join(RUN_DIR, ".app_port")    # 記錄執行中的連接埠，避免重複開啟
LOG_FILE = os.path.join(RUN_DIR, "app.log")
APP_ID = "stm32-tracker2"
OLD_APP_ID = "stm32-tracker"                       # 舊版 App
OLD_PORT_FILE = os.path.join(ROOT, "tracker", ".app_port")
FIRST_PORT = 8775                                  # 舊版從 8765 開始，錯開避免混淆
IS_WIN = sys.platform.startswith("win")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if IS_WIN else 0
CLIENT_TIMEOUT = 150      # 秒：分頁太久沒回報就視為已關閉（背景分頁計時器可能被瀏覽器降到每分鐘一次）
BYE_GRACE = 4             # 秒：分頁關閉後等這麼久，沒有新分頁就結束（重新整理不會誤關）
FIRST_CLIENT_WAIT = 180   # 秒：啟動後一直沒有瀏覽器連進來就結束
STATE = {"syncing": False, "sync_msg": "", "sync_error": None}
CLIENTS = {}              # 分頁 id → 最後一次回報時間
WATCH = {"had_client": False, "empty_since": None, "started": time.time(), "quit": False}
ENTRY_TYPES = ("問題", "筆記", "解法", "進度", "待學", "面試")   # 舊版只認得前三種，其餘在舊版看得到內容但沒有底色
PROGRESS_TAG = "【本次進度】"
STUCK_TAG = "【卡關】"
OPEN_TAG = "【待解決】"                              # 還沒有答案的疑問
CARD_TAG = "【面試】"                                # 面試卡：一題一則，彙整到 learning/INTERVIEW.md
TAG_TYPES = (("【問題】", "問題"), ("【筆記】", "筆記"), ("【解法】", "解法"),
             (PROGRESS_TAG, "進度"), ("【待學】", "待學"), (STUCK_TAG, "問題"), (OPEN_TAG, "問題"), (CARD_TAG, "面試"))
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
    if STATE.get("sync_error"):
        return "同步衝突還沒解決，這次的變更先只存在這台電腦（已 commit，沒有上傳）。"
    ok, out = git("push", "--follow-tags", "-u", "origin", "HEAD", timeout=90)
    return "已 push 到 GitHub。" if ok else "push 失敗：" + out


def rebase_in_progress():
    ok, gd = git("rev-parse", "--git-dir")
    if not ok:
        return False
    gd = gd if os.path.isabs(gd) else os.path.join(ROOT, gd)
    return any(os.path.isdir(os.path.join(gd, d)) for d in ("rebase-merge", "rebase-apply"))


def pull():
    """從 GitHub 取得最新進度。和本機的修改衝突時自動還原到同步前的狀態，並記下 sync_error。"""
    ok_r, _ = git("remote", "get-url", "origin")
    if not ok_r:
        return False, "尚未設定 GitHub remote。"
    if rebase_in_progress():              # 上次同步被中斷，先還原
        git("rebase", "--abort")
    _, st = git("status", "--porcelain")
    if st.strip():
        commit_learning_quiet("自動儲存：同步前提交進度")
    ok, out = git("pull", "--rebase", "--autostash", timeout=90)
    if ok:
        STATE["sync_error"] = None
        return True, "已從 GitHub 取得最新進度。"
    conflict = rebase_in_progress() or "CONFLICT" in out
    if rebase_in_progress():
        git("rebase", "--abort")          # 回到同步前的狀態，本機的筆記不會少
    if conflict:
        STATE["sync_error"] = {"time": now(), "detail": out[-2000:]}
        log("同步衝突，已還原：" + out[-500:])
        return False, "同步衝突：這台電腦和 GitHub 上的進度互相衝突，已還原到同步前的狀態。"
    return False, "pull 失敗：" + out


def stage_all():
    """筆記、程式碼，以及 App 本身（讓另一台電腦同步到新版 App）。"""
    git("add", "learning")
    if os.path.isdir(PROJECTS):
        git("add", "projects")
    for p in ("tracker", "tracker2", "docs", "README.md", "CLAUDE.md", ".gitignore",
              "STM32Tracker.exe", "STM32Tracker2.exe"):
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
        return ensure_ids(json.load(f))


def ensure_ids(db):
    """每則筆記都要有固定 ID。舊版 App 新增的筆記沒有 ID，這裡用內容算出一個固定的值補上，
    所以同一則筆記每次讀取都得到相同的 ID；下次由新版存檔時才真正寫進檔案。"""
    for t in db["tasks"]:
        seen = {e["id"] for e in t.get("entries", []) if e.get("id")}
        for e in t.get("entries", []):
            if e.get("id"):
                continue
            base = hashlib.sha1(f"{t['id']}|{e.get('time')}|{e.get('type')}|{e.get('text')}".encode("utf-8")).hexdigest()[:10]
            eid, n = base, 1
            while eid in seen:
                n += 1
                eid = f"{base}{n}"
            seen.add(eid)
            e["id"] = eid
    return db


def type_from_text(text, fallback="筆記"):
    """依開頭的【】決定類型；沒有【】就用 fallback。"""
    for tag, typ in TAG_TYPES:
        if text.startswith(tag):
            return typ
    return fallback


def is_open(e):
    """待解決：真正還沒有答案的問題。【問題】預設是「踩過的錯」，不算待解決。"""
    if e.get("type") != "問題" or e.get("resolved"):
        return False
    if "open" in e:
        return bool(e["open"])
    return e["text"].startswith((STUCK_TAG, OPEN_TAG))      # 舊版 App 記下的卡關或待解決


def is_progress(e):
    return e.get("type") == "進度" or e["text"].startswith(PROGRESS_TAG)


def is_later(e):
    return e.get("type") == "待學"


def make_entry(typ, text, open_=None):
    text = text.strip()
    e = {"id": uuid.uuid4().hex[:10], "time": now(), "type": typ, "text": text}
    apply_type(e, typ, open_=text.startswith((STUCK_TAG, OPEN_TAG)) if open_ is None else open_, force=True)
    return e


def apply_type(e, typ, open_=False, force=False):
    """設定類型與相關欄位。resolved 是舊版就有的欄位：問題＝不是待解決、待學＝已學、其他＝None。"""
    if not force and e.get("type") == typ:
        return
    e["type"] = typ
    if typ == "問題":
        e["open"] = bool(open_)
        e["resolved"] = not e["open"]
    else:
        e.pop("open", None)
        e["resolved"] = False if typ == "待學" else None


def find_entry(t, eid):
    for i, e in enumerate(t.get("entries", [])):
        if e.get("id") == eid:
            return i, e
    raise KeyError("找不到這則紀錄（可能已經被刪除，請重新整理）。")


FENCE_OPEN = re.compile(r"^\s{0,3}(`{3,})\s*([\w+-]*)\s*$")
HEAD_RE = re.compile("^(" + "|".join(re.escape(tag) for tag, _ in TAG_TYPES) + ")")


def _fence_blocks(lines):
    """找出最外層的程式碼區塊，回傳 [(語言, 內容行)]。
    區塊裡又有帶語言的區塊（例如 ```markdown 裡的 ```c）時視為巢狀，不會提早結束。"""
    blocks, i = [], 0
    while i < len(lines):
        m = FENCE_OPEN.match(lines[i])
        if not m:
            i += 1
            continue
        mark, lang, body, depth, j = m.group(1), m.group(2).lower(), [], 0, i + 1
        while j < len(lines):
            c = FENCE_OPEN.match(lines[j])
            if c and len(c.group(1)) >= len(mark):
                if c.group(2) and len(c.group(1)) == len(mark):
                    depth += 1                    # 內層區塊開始
                elif depth > 0 and len(c.group(1)) == len(mark):
                    depth -= 1                    # 內層區塊結束
                elif not c.group(2):
                    break                         # 最外層結束
            body.append(lines[j])
            j += 1
        blocks.append((lang, body))
        i = j + 1
    return blocks


def _split_by_head(text):
    """依行首的【筆記】【問題】【解法】【本次進度】【待學】【卡關】【待解決】拆成多則（程式碼區塊裡的不算）。"""
    chunks, cur, fence = [], [], None
    for line in text.split("\n"):
        m = FENCE_OPEN.match(line)
        if m:
            if fence is None:
                fence = len(m.group(1))
            elif len(m.group(1)) >= fence and not m.group(2):
                fence = None
        if fence is None and HEAD_RE.match(line) and any(x.strip() for x in cur):
            chunks.append("\n".join(cur))
            cur = []
        cur.append(line)
    chunks.append("\n".join(cur))
    return [c.strip("\n").rstrip() for c in chunks if c.strip()]


def split_notes(text, fallback="筆記"):
    """把一段貼上的文字拆成多則筆記。
    - 有 ```markdown 區塊：每個區塊是一則（區塊外的說明文字不存）。
    - 沒有：依行首的【】標題拆開；完全沒有【】就是一則。
    回傳 [{type, text, title, tagged, keep}]。keep=False 表示預設不存（標題前面的說明文字）。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    md_blocks = [b for lang, b in _fence_blocks(text.split("\n")) if lang in ("markdown", "md")]
    chunks = []
    if md_blocks:
        for body in md_blocks:
            chunks += _split_by_head("\n".join(body))
    else:
        chunks = _split_by_head(text)
    items = []
    for c in chunks:
        tagged = bool(HEAD_RE.match(c))
        items.append({"type": type_from_text(c, fallback), "text": c, "tagged": tagged,
                      "title": _entry_title({"text": c}), "keep": True})
    if any(x["tagged"] for x in items):
        for x in items:
            x["keep"] = x["tagged"]          # 夾在中間、沒有【】開頭的段落多半是說明文字
    return items


def _title_key(text):
    return re.sub(r"\s+", "", _entry_title({"text": text}))


def save(db, export=True):
    prune_cards(db)
    tmp = DATA + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA)
    if export:
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
        lines += [f"- 狀態：**{t['status']}**",
                  f"- 階段：{t['stage']}　主題：{t.get('topic') or ''}" if t.get("stage") else f"- 週次：{t.get('week') or ''}　主題：{t.get('topic') or ''}"]
        if t.get("plan") == "HAL" and t.get("orig"):
            lines.append(f"- 對應原任務（HAL 版）：{t['orig']}")
        if t.get("priority") == "merged":
            lines.append(f"- 已併入：{t.get('merged_into')}")
        elif t.get("priority") == "optional":
            lines.append("- 類別：選修")
        if t.get("sessions"):
            lines.append(f"- 進行次數：{len(t['sessions'])} 次（最近一次：{t['sessions'][-1]['start'][:10]}）")
        if t.get("finished_at"):
            lines.append(f"- 完成日期：{t['finished_at']}")
        rv = review_info(t)
        if rv:
            lines.append(f"- 複習：{rv['count']} 次，" + ("已到複習日" if rv["due"] else f"下次 {rv['next']}"))
        if os.path.isdir(os.path.join(PROJECTS, t["id"])):
            lines.append(f"- 程式碼：[projects/{t['id']}](../../projects/{t['id']})")
        lines += ["", "## 任務內容", "", t.get("content") or "", "",
                  "## 完成標準", "", t.get("criteria") or "", ""]
        if t.get("must"):
            lines += ["## 必學範圍", ""] + [f"- [{'x' if m.get('done') else ' '}] {m['text']}" for m in t["must"]] + [""]
        if t.get("optional_topics"):
            lines += ["## 選修主題", ""] + [f"- {x}" for x in t["optional_topics"]] + [""]
        if t.get("summary"):
            lines += ["## 總結", "", t["summary"], ""]
        if t.get("reviews"):
            lines += ["## 複習紀錄", ""]
            lines += [f"- {r['date']}：{REVIEW_RESULTS.get(r.get('result'), '')}" + (f"　{r['note']}" if r.get("note") else "")
                      for r in t["reviews"]] + [""]
        if t.get("entries"):
            lines += ["## 問題與筆記", ""]
            for e in t["entries"]:
                mark = ""
                if is_open(e):
                    mark = " ❓ 待解決"
                elif e["type"] == "待學" and e.get("resolved"):
                    mark = " ✅ 已學"
                lines.append(f"### [{e['type']}] {e['time']}{mark}")
                lines += ["", e["text"], ""]
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines))

    # 總覽：依階段分組，顯示必修／選修、必學範圍與依實際速度推算的完成日
    sprint = sorted([t for t in tasks if t.get("plan") == "SPRINT"], key=lambda t: t.get("order", 0))
    fc = forecast(db)
    lines = ["# STM32 學習進度", "",
             f"- 技術必修：{fc['tech_done']} / {fc['tech_total']} 完成　求職線：{fc['career_done']} / {fc['career_total']}　"
             f"選修：{fc['optional_done']} / {fc['optional_total']}",
             f"- 最近 4 週有 {fc['study_days_28']} 個學習日"]
    if fc["eta"]:
        lines.append(f"- 預估技術主線完成日：{fc['eta']}（剩 {fc['remaining']:g} 課，依最近 {len(fc['avg_from'])} 課平均每課 {fc['avg_days']:g} 天推算，會隨實際速度變動）")
    due = [t for t in sprint if (review_info(t) or {}).get("due")]
    if due:
        lines.append(f"- 待複習：{len(due)} 課（" + "、".join(t["title"] for t in due[:8]) + ("…" if len(due) > 8 else "") + "）")
    cs = card_summary(db)
    if sum(cs["total"][k] for k in CARD_DEFAULT_KINDS):
        lines.append("- 翻卡自測：" + "、".join(f"{CARD_KIND_NAMES[k]} {cs['total'][k]} 張" for k in CARD_DEFAULT_KINDS)
                     + f"；產生這一頁時有 {sum(cs['due'][k] for k in CARD_DEFAULT_KINDS)} 張到期")
    lines += [f"- 最後更新：{now()}", "", "- [全部問題整理（複習用）](QUESTIONS.md)", "- [面試準備（面試卡與面試版說明）](INTERVIEW.md)", ""]
    stage = None
    for t in sprint:
        if t.get("stage") != stage:
            stage = t.get("stage")
            lines += ["", f"## {stage or '學習計畫'}", "", "| 代碼 | 課題 | 類別 | 狀態 | 必學 | 下次複習 | 筆記 |", "|---|---|---|---|---|---|---|"]
        cat = {"optional": "選修", "merged": f"已併入 {t.get('merged_into', '')}"}.get(t.get("priority"), "必修")
        must = t.get("must") or []
        mtxt = f"{sum(1 for m in must if m.get('done'))} / {len(must)}" if must else ""
        link = f"[{len(t['entries'])} 則](notes/{t['id']}.md)" if (t.get("entries") or t.get("sessions")) else ""
        status = "" if t.get("priority") == "merged" else t["status"]
        rv = review_info(t)
        rtxt = (f"**{rv['next']}（到期）**" if rv["due"] else rv["next"]) if rv else ""
        lines.append(f"| {t['id']} | {t['title']} | {cat} | {status} | {mtxt} | {rtxt} | {link} |")
    lines += ["", "## 舊紀錄（HAL 版，已封存）", "", "| 代碼 | 任務 | 狀態 | 筆記 |", "|---|---|---|---|"]
    for t in tasks:
        if t.get("plan") != "HAL":
            continue
        link = f"[筆記](notes/{t['id']}.md)" if t.get("entries") else ""
        lines.append(f"| {t['id']} | {t['title']} | {t['status']} | {link} |")
    with open(os.path.join(LEARN, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    # 問題集：待解決的附全文；踩過的錯與解法只列標題，全文在各課的筆記頁
    sprint_first = sorted(tasks, key=lambda t: t.get("plan") != "SPRINT")
    strip_tag = lambda title: HEAD_RE.sub("", title, count=1).strip() or title
    open_q = [(t, e) for t in sprint_first for e in t.get("entries", []) if is_open(e)]
    lines = ["# 問題整理（複習與面試用）", "",
             "- 「待解決」是還沒有答案的問題，附全文。",
             "- 「踩過的錯」與「解法」只列標題，點課題名稱可以看全文。", "",
             f"## ❓ 待解決（{len(open_q)}）", ""]
    for t, e in open_q:
        lines += [f"### {t['id']} {t['title']}（{e['time']}）", "", e["text"], ""]
    if not open_q:
        lines += ["目前沒有。", ""]
    for head, cond in (("踩過的錯", lambda e: e["type"] == "問題" and not is_open(e)),
                       ("解法", lambda e: e["type"] == "解法")):
        total = sum(1 for t in tasks for e in t.get("entries", []) if cond(e))
        lines += [f"## {head}（{total}）", ""]
        for t in sprint_first:
            items = [e for e in t.get("entries", []) if cond(e)]
            if not items:
                continue
            lines += [f"### [{t['id']}](notes/{t['id']}.md) {t['title']}", ""]
            lines += [f"- {strip_tag(_entry_title(e))}" for e in items]
            lines.append("")
    later = [(t, e) for t in sprint_first for e in t.get("entries", []) if is_later(e)]
    if later:
        todo = [(t, e) for t, e in later if not e.get("resolved")]
        lines += [f"## 待學清單（{len(todo)} 項還沒學）", ""]
        lines += [f"- [{'x' if e.get('resolved') else ' '}] {strip_tag(_entry_title(e))}（{t['id']}）" for t, e in later]
        lines.append("")
    with open(os.path.join(LEARN, "QUESTIONS.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(LEARN, "INTERVIEW.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(interview_lines(db)) + "\n")


# ---------------------------------------------------------------- interview
SPEAK_MARK = "面試版"          # 筆記裡「面試版 30 秒說明」這類段落的開頭


def _bare(line):
    """去掉行首的 Markdown 符號（#、-、*、空白），用來判斷這一行在講什麼。"""
    return line.strip().lstrip("#").strip().lstrip("-").strip().strip("*").strip()


def speak_section(text):
    """取出筆記裡「面試版」那一段：從那一行開始，到下一個標題或粗體小標為止。"""
    out, on, fence, bullet = [], False, False, False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fence = not fence
        if not on:
            if not fence and _bare(line).startswith(SPEAK_MARK):
                on, bullet = True, line.startswith(("- ", "* "))
                out.append(line)
            continue
        head = line.lstrip().startswith("#") or re.match(r"^\s*\*\*[^*]+\*\*\s*[:：]?\s*$", line)
        if not fence and (head or (bullet and line.startswith(("- ", "* ")))):
            break
        out.append(line)
    return "\n".join(out).strip()


def interview_items(t):
    """一個課題裡和面試有關的內容：面試卡、標題含「面試」的筆記、筆記裡的面試版段落、其他提到面試的筆記標題。"""
    cards, answers, speaks, related = [], [], [], []
    for e in t.get("entries", []):
        title = _entry_title(e)
        if e.get("type") == "面試":
            cards.append(e)
        elif "面試" in title:
            answers.append(e)
        elif speak_section(e["text"]):
            speaks.append((e, speak_section(e["text"])))
        elif "面試" in e["text"]:
            related.append(e)
    return cards, answers, speaks, related


def interview_lines(db):
    """learning/INTERVIEW.md：依課程順序彙整面試卡與面試版說明。"""
    strip_tag = lambda title: HEAD_RE.sub("", title, count=1).strip() or title
    body = lambda e: "\n".join(e["text"].strip().splitlines()[1:]).strip()
    sprint = sorted([t for t in db["tasks"] if t.get("plan") == "SPRINT" and t.get("priority") != "merged"],
                    key=lambda t: t.get("order", 0))
    found = [(t, interview_items(t)) for t in sprint]
    n_cards = sum(len(x[0]) for _, x in found)
    n_other = sum(len(x[1]) + len(x[2]) for _, x in found)
    lines = ["# 面試準備", "",
             "- 這一頁由學習進度 App 自動彙整，請不要直接修改；要改內容請到 App 改對應的筆記。",
             "- 用法：先遮住答案自己講一次，再對照。講不順的課題回 App 按「複習」再考一次。",
             f"- 目前有面試卡 {n_cards} 則、驗收回答與面試版說明 {n_other} 段。", ""]
    stage = None
    for t, (cards, answers, speaks, related) in found:
        if not (cards or answers or speaks or related):
            continue
        if t.get("stage") != stage:
            stage = t.get("stage")
            lines += [f"## {stage or '學習計畫'}", ""]
        lines += [f"### [{t['id']}](notes/{t['id']}.md) {t['title']}", ""]
        rv = review_info(t)
        if rv:
            last = rv["last"]
            lines += [f"- 複習 {rv['count']} 次" + (f"，最近一次 {last['date']}（{REVIEW_RESULTS.get(last.get('result'), '')}）" if last else "")
                      + ("，已到複習日" if rv["due"] else f"，下次 {rv['next']}"), ""]
        for e in cards:
            lines += [f"#### {strip_tag(_entry_title(e))}", "", body(e), ""]
        for e in answers:
            lines += [f"#### {strip_tag(_entry_title(e))}", "", body(e), ""]
        for e, text in speaks:
            lines += [f"#### 面試版說明（出自「{strip_tag(_entry_title(e))}」）", "", "\n".join(text.splitlines()[1:]).strip() or text, ""]
        if related:
            lines += ["其他提到面試的筆記（全文在這一課的筆記頁）：", ""] + [f"- {strip_tag(_entry_title(e))}" for e in related] + [""]
    todo = [t for t, x in found if can_review(t) and not x[0]]
    if todo:
        lines += ["## 還沒有面試卡的已完成課題", "", "到 App 對這些課題按「複習」，複習結束時 Claude 會把題目整理成面試卡。", ""]
        lines += [f"- {t['id']} {t['title']}" for t in todo] + [""]
    return lines


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
PROMPT_DIR = os.path.join(HERE, "prompts")
CODE_EXT = {".c", ".h", ".py"}
CODE_SKIP = ("Drivers/", "Middlewares/", "CMSIS/")
CODE_BUDGET = 15000          # 求助提示詞最多附上的程式碼字數
OWN_TITLES = 80              # 本課筆記標題最多列幾則
PREV_TITLES = 30             # 上一課筆記標題最多列幾則


def tpl(name):
    """讀取 prompts/<name>.md。每次產生提示詞都重新讀，改檔後不用重開 App。"""
    path = os.path.join(PROMPT_DIR, name + ".md")
    try:
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
    except OSError:
        raise ValueError(f"找不到提示詞規則檔 tracker2/prompts/{name}.md") from None
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S).strip()
    if not text:
        raise ValueError(f"提示詞規則檔 tracker2/prompts/{name}.md 是空的")
    return text.splitlines()


def _task_block(t):
    lines = [f"- 代碼：{t['id']}（主題：{t.get('topic') or '—'}）",
             f"- 課題：{t['title']}", "", "### 課題內容", t.get("content") or "（無）"]
    if t.get("output"):
        lines += ["", "### 產出物", t["output"]]
    lines += ["", "### 完成標準", t.get("criteria") or "（無）"]
    return lines


def _entry_title(e):
    """筆記的第一行當標題（去掉 # 與 ** 符號）。"""
    for line in e["text"].splitlines():
        line = line.strip().lstrip("#").strip().strip("*").strip()
        if line:
            return line[:80]
    return "（空白）"


def _title_line(e):
    title = _entry_title(e)
    return f"- {title}" if title.startswith("【") else f"- [{e['type']}] {title}"


def _clip(text, limit):
    text = text.strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "…（後略）"


def _last_progress(t):
    for e in reversed(t.get("entries", [])):
        if is_progress(e):
            return e
    return None


def _own_notes_block(t, limit=OWN_TITLES, skip=""):
    """本課已經記下的筆記：只列標題，不貼全文。"""
    ents = [e for e in t.get("entries", [])
            if not is_progress(e) and not is_later(e) and not (skip and e["text"] == skip)]
    if not ents:
        return []
    shown = ents[-limit:]
    head = f"### 本課已經記下的筆記（只列標題，共 {len(ents)} 則" + (f"，列最新 {limit} 則" if len(ents) > limit else "") + "）"
    return ["", head] + [_title_line(e) for e in shown]


def _blockers_block(t, skip=""):
    """待解決的問題：真正還沒有答案的，所以貼全文。"""
    ents = [e for e in t.get("entries", []) if is_open(e) and not (skip and e["text"] == skip)]
    if not ents:
        return []
    return ["", "### 待解決的問題（還沒有答案）"] + [f"- （{e['time']}）{_clip(e['text'], 800)}" for e in ents]


def todo_key(text):
    return hashlib.sha1(re.sub(r"\s+", "", text).encode("utf-8")).hexdigest()[:10]


def all_todos(db, plan="SPRINT"):
    """所有課題筆記裡含 TODO 的行。處理完在 App 勾掉之前，每一課的提示詞都會帶上。"""
    done = db.get("todo_done") or {}
    res, seen = [], set()
    for t in db["tasks"]:
        if t.get("plan") != plan:
            continue
        for e in t.get("entries", []):
            for line in e["text"].splitlines():
                if "TODO" not in line.upper():
                    continue
                text = re.sub(r"^TODO\s*[:：]?\s*", "", line.strip().lstrip("-・*• ").strip(), flags=re.I).strip()
                if not text:
                    continue
                key = todo_key(text)
                if key in seen:
                    continue
                seen.add(key)
                res.append({"key": key, "text": text, "task": t["id"], "title": t["title"],
                            "note": HEAD_RE.sub("", _entry_title(e), count=1).strip(),
                            "done": key in done, "done_at": done.get(key)})
    return res


def all_later(db, plan="SPRINT"):
    """待學清單：課堂中先記下來、之後有空再學的延伸主題。"""
    return [{"task": t["id"], "title": t["title"], "eid": e["id"], "text": e["text"], "time": e["time"],
             "done": bool(e.get("resolved"))}
            for t in db["tasks"] if t.get("plan") == plan for e in t.get("entries", []) if is_later(e)]


def _todo_block(db, t):
    items = [x for x in all_todos(db, t.get("plan") or "SPRINT") if not x["done"]]
    if not items:
        return []
    return ["", "## 還沒處理的 TODO（之前的課留下的，看本課是否適合處理）"] + \
           [f"- {x['text']}（來自 {x['task']}「{x['title']}」的筆記「{x['note']}」）" for x in items]


def _open_elsewhere_block(db, t):
    """其他課題裡還沒有答案的問題：換課之後也要繼續帶著，直到解決。"""
    items = [(x, e) for x in plan_tasks(db, t.get("plan")) if x["id"] != t["id"] for e in x.get("entries", []) if is_open(e)]
    if not items:
        return []
    return ["", "## 之前的課還沒解決的問題（還沒有答案；本課碰到相關內容時幫我一起弄懂）"] + \
           [f"- （{x['id']}「{x['title']}」）{_clip(e['text'], 400)}" for x, e in items]


def plan_tasks(db, plan):
    """同一個計畫的課題，依學習順序（order）排列；沒有 order 的維持檔案裡的順序。"""
    same = [x for x in db["tasks"] if x.get("plan") == plan]
    return [x for _, x in sorted(enumerate(same), key=lambda p: (p[1].get("order", p[0]) if plan == "SPRINT" else p[0], p[0]))]


def _previous_block(db, t, brief=False):
    """上一課的重點：讓 Claude 知道我上一課學到哪。"""
    same = plan_tasks(db, t.get("plan"))
    idx = next((i for i, x in enumerate(same) if x["id"] == t["id"]), 0)
    before = same[:idx]
    prev = next((x for x in reversed(before) if x.get("sessions") or x.get("entries")), None)
    if not prev:
        return []
    lines = ["", f"## 上一課：{prev['id']}「{prev['title']}」（{prev['status']}）"]
    files = [f["path"] for f in _code_files(prev["id"])]
    if files:
        lines.append(f"- 程式碼（projects/{prev['id']}/）：" + "、".join(files[:12]))
    if not brief:
        lines.insert(2, f"- 完成標準：{prev.get('criteria') or '（無）'}")
        if prev.get("summary"):
            lines.append(f"- 總結：{prev['summary']}")
        ents = [e for e in prev.get("entries", []) if not is_progress(e) and not is_later(e)]
        if ents:
            shown = ents[-PREV_TITLES:]
            lines += ["", f"### 上一課學過的主題（只列筆記標題，共 {len(ents)} 則"
                      + (f"，列最新 {PREV_TITLES} 則" if len(ents) > PREV_TITLES else "") + "）"]
            lines += [_title_line(e) for e in shown]
    done = [x for x in before if x["status"] == "已完成"]
    if done:
        lines += ["", f"### 到目前為止已完成的課題（依學習順序，共 {len(done)} 課）"]
        lines += [f"- {x['id']}「{x['title']}」" + ("（就是上一課，筆記標題列在上面）" if x["id"] == prev["id"] and not brief
                                                 else "（就是上一課）" if x["id"] == prev["id"] else "") for x in done]
    return lines


def _code_files(tid):
    return [f for f in list_files(tid)
            if os.path.splitext(f["path"])[1].lower() in CODE_EXT and not any(s in f["path"] for s in CODE_SKIP)]


def _code_list_block(tid):
    files = list_files(tid)
    if not files:
        return []
    code = _code_files(tid)
    return ["", f"### 目前的程式碼（projects/{tid}/，共 {len(files)} 個檔案）"] + \
           ([f"- {f['path']}" for f in code[:30]] or ["- （沒有 .c/.h/.py 檔）"])


KIND_DEFAULT = "register"
TECH_KINDS = ("register", "driver", "arch", "debug", "concept")   # 走完整帶課流程的類型
CAREER_STAGE = "求職線"
API_LINES = 60               # 模組介面最多列幾行
PROTO_RE = re.compile(r"^(?!typedef\b|return\b|else\b)[A-Za-z_][\w \t\*]*?\b[A-Za-z_]\w*\s*\([^;{}()]*\)\s*;")
DEFINE_RE = re.compile(r"^#define\s+([A-Z][A-Z0-9_]*)\s+(\S.*)$")


def task_kind(t):
    return t.get("kind") or KIND_DEFAULT


def _must_block(t):
    """本課的必學範圍與選修主題（第 3 批加入 progress.json 的 must／optional_topics）。"""
    must = t.get("must") or []
    lines = []
    if must:
        done = sum(1 for m in must if m.get("done"))
        lines += ["", f"### 必學範圍（要學到能不看筆記口頭解釋；[x] 是我已經確認學會的，共 {done}／{len(must)}）"]
        lines += [f"- [{'x' if m.get('done') else ' '}] {m['text']}" for m in must]
    if t.get("optional_topics"):
        lines += ["", "### 選修主題（本課先不做，除非我主動提）"] + [f"- {x}" for x in t["optional_topics"]]
    return lines


def header_api(tid):
    """從課題專案的 Inc/*.h 擷取函式宣告與常數，讓 Claude 知道已經有哪些模組可以沿用。"""
    out = []
    for f in list_files(tid):
        path = f["path"]
        if not path.lower().endswith(".h") or any(s in path for s in CODE_SKIP) or "/" not in path:
            continue
        text = read_text(tid, path) or ""
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        items = []
        for raw in text.split("\n"):
            line = raw.split("//")[0].strip()
            if PROTO_RE.match(line):
                items.append(re.sub(r"\s+", " ", line))
            else:
                m = DEFINE_RE.match(line)
                if m and not m.group(1).endswith("_H") and not m.group(1).endswith("_H_"):
                    items.append(f"#define {m.group(1)} {m.group(2).strip()}")
        if items:
            out.append((path, items))
    return out


def _api_block(db, t):
    """已經寫好的模組介面：本課專案有標頭檔就用本課的，否則用最近一個有專案的課題。"""
    same = plan_tasks(db, t.get("plan"))
    idx = next((i for i, x in enumerate(same) if x["id"] == t["id"]), 0)
    for cand in [t] + list(reversed(same[:idx])):
        api = header_api(cand["id"])
        if not api:
            continue
        lines = ["", f"### 已經寫好的模組介面（projects/{cand['id']}/ 的標頭檔，可以直接沿用）"]
        n = 0
        for path, items in api:
            lines.append(f"`{path}`")
            for it in items:
                if n >= API_LINES:
                    return lines + ["- （後面省略）"]
                lines.append(f"- `{it}`")
                n += 1
        return lines
    return []


def _rules(t, opening):
    """依課題類型組合規則。opening 是 teach_new 或 teach_continue。"""
    kind = task_kind(t)
    if kind in ("career", "prep"):
        lines = [""]
        if opening == "teach_continue":
            lines += ["這是同一個課題的新對話。請先根據「上次進度」和已經記下的筆記標題，確認我現在做到哪、下一步是什麼。", ""]
        lines += tpl("kind_" + kind) + [""] + tpl("notes") + [""] + tpl("style")
        if kind == "prep":
            lines += [""] + tpl("refs")
        return lines
    if kind not in TECH_KINDS:
        kind = KIND_DEFAULT
    lines = [""] + tpl(opening) + tpl("teach_common") + [""] + tpl("scope") + [""] + tpl("kind_" + kind)
    if kind == "register":
        lines += [""] + tpl("hal")
    lines += [""] + tpl("wrapup") + [""] + tpl("notes") + [""] + tpl("style") + [""] + tpl("refs")
    return lines


REVIEW_WRAP = 5000           # 複習提示詞附上的總整理筆記字數上限
CARDS_WRAP = 8000            # 產生面試卡提示詞附上的總整理筆記字數上限
BACKFILL_SOLUTIONS = 9000    # 補做總整理：【解法】筆記全文的字數上限
BACKFILL_MISTAKES = 7000     # 補做總整理：踩過的錯全文的字數上限
WRAPUP_EXTRA = "收尾總整理時另外附上"


def wrapup_note(t):
    """收尾總整理的筆記（標題含「總整理」），沒有就回傳 None。"""
    for e in reversed(t.get("entries", [])):
        if "總整理" in _entry_title(e):
            return e
    return None


def _mistakes(t):
    return [e for e in t.get("entries", []) if e.get("type") == "問題" and not is_open(e)]


def _gist(e):
    """筆記第 2 行的粗體「一句話重點」，沒有就回傳空字串。"""
    rows = [x.strip() for x in e["text"].splitlines() if x.strip()]
    if len(rows) > 1 and rows[1].startswith("**") and rows[1].endswith("**") and len(rows[1]) > 4:
        return rows[1].strip("*").strip()[:120]
    return ""


def _titles_block(head, ents, limit=40, gist=False):
    if not ents:
        return []
    more = f"，列最新 {limit} 則" if len(ents) > limit else ""
    what = "標題與一句話重點" if gist else "只列標題"
    line = lambda e: _title_line(e) + (f"：{_gist(e)}" if gist and _gist(e) else "")
    return ["", f"### {head}（{what}，共 {len(ents)} 則{more}）"] + [line(e) for e in ents[-limit:]]


def _reviews_block(t):
    revs = t.get("reviews") or []
    if not revs:
        return ["", "### 之前的複習", "（這是第一次複習。）"]
    lines = ["", f"### 之前的複習（共 {len(revs)} 次" + ("，列最近 5 次" if len(revs) > 5 else "") + "）"]
    for r in revs[-5:]:
        lines.append(f"- {r['date']}：{REVIEW_RESULTS.get(r.get('result'), '')}" + (f"；還不穩的地方：{r['note']}" if r.get("note") else ""))
    return lines


def _full_notes_block(head, ents, budget):
    """筆記全文，超過字數上限的只列標題。"""
    if not ents:
        return []
    lines, used, rest = ["", f"### {head}（共 {len(ents)} 則）"], 0, []
    for e in ents:
        if used + len(e["text"]) > budget:
            rest.append(e)
            continue
        used += len(e["text"])
        lines += ["", f"（{e['time']}）", e["text"].strip(), "", "---"]
    if rest:
        lines += ["", f"以下 {len(rest)} 則太長沒有附上全文，需要時請我貼："] + [_title_line(e) for e in rest]
    return lines


def _wrapup_extra(t):
    """各類課題在收尾總整理時另外要附的內容（kind_*.md 的最後一段）。"""
    kind = task_kind(t) if task_kind(t) in TECH_KINDS else KIND_DEFAULT
    lines = tpl("kind_" + kind)
    for i, line in enumerate(lines):
        if WRAPUP_EXTRA in line:
            return [""] + lines[i:]
    return []


def prompt_kind(t, kind="start"):
    """start 會依有沒有筆記自動分成 new（新課題）或 continue（同一課換新對話）。"""
    if kind in ("new", "continue", "stuck", "review", "backfill", "cards"):
        return kind
    has_notes = any(not e["text"].startswith(STUCK_TAG) for e in t.get("entries", []))
    return "continue" if has_notes else "new"


def build_prompt(db, tid, kind="start", stuck_text=""):
    t = find(db, tid)
    kind = prompt_kind(t, kind)
    simple = task_kind(t) in ("career", "prep")
    intro = "我的背景、硬體與學習計畫在專案說明（CLAUDE.md／STM32學習背景與進度）裡。"
    if kind == "new":
        lines = [f"我要開始 STM32 學習課題 {tid}「{t['title']}」。", intro, "",
                 "## 本課題"] + _task_block(t) + _must_block(t) + _code_list_block(tid)
        if task_kind(t) != "career":
            lines += _api_block(db, t)
        lines += _previous_block(db, t) + _todo_block(db, t) + _open_elsewhere_block(db, t)
        lines += _rules(t, "teach_new")
        lines += ["", "準備好了就開始。" if simple else "準備好了就從「先接續」開始。"]
    elif kind == "continue":
        lines = [f"我要繼續 STM32 學習課題 {tid}「{t['title']}」，這是同一個課題的新對話。", intro, "",
                 "## 本課題"] + _task_block(t) + _must_block(t)
        prog = _last_progress(t)
        lines += ["", "### 上次進度"]
        lines += [f"（{prog['time']}）{_clip(prog['text'][len(PROGRESS_TAG):] if prog['text'].startswith(PROGRESS_TAG) else prog['text'], 1500)}"] if prog else \
                 ["（App 裡沒有記錄上次進度。請先問我上次做到哪一步。）"]
        lines += _blockers_block(t) + _own_notes_block(t) + _code_list_block(tid)
        if task_kind(t) != "career":
            lines += _api_block(db, t)
        lines += _previous_block(db, t, brief=True) + _todo_block(db, t) + _open_elsewhere_block(db, t)
        lines += _rules(t, "teach_continue")
        lines += ["", "準備好了就先確認我現在做到哪。"]
    elif kind == "review":
        if not can_review(t):
            raise ValueError("只有已完成的技術課題可以產生複習提示詞。")
        nth = len(t.get("reviews") or []) + 1
        lines = [f"我要複習 STM32 學習課題 {tid}「{t['title']}」（{t['finished_at']} 完成，這是第 {nth} 次複習）。請當面試官，用口頭問答考我。",
                 intro, "", "## 複習的課題"] + _task_block(t) + _must_block(t)
        lines += _titles_block("我在這一課踩過的錯", _mistakes(t), gist=True) + _blockers_block(t)
        lines += _titles_block("這一課已經有的面試卡", [e for e in t.get("entries", []) if e.get("type") == "面試"])
        lines += _reviews_block(t) + _weak_cards_block(db, t)
        wrap = wrapup_note(t)
        if wrap:
            lines += ["", "### 本課的總整理筆記（給你出題和對答案用，不要直接唸給我聽）", _clip(wrap["text"], REVIEW_WRAP)]
        else:
            lines += _titles_block("本課記下的【解法】", [e for e in t.get("entries", []) if e.get("type") == "解法"], gist=True)
        lines += [""] + tpl("review") + [""] + tpl("notes") + [""] + tpl("style")
        lines += ["", "準備好了就出第一題。"]
    elif kind == "backfill":
        if t.get("plan") != "SPRINT" or task_kind(t) not in TECH_KINDS or not t.get("entries"):
            raise ValueError("這個課題沒有可以整理的筆記。")
        ents = t.get("entries", [])
        solved = [e for e in ents if e.get("type") == "解法"]
        other = [e for e in ents if e.get("type") in ("筆記", "面試")]
        lines = [f"我要為 STM32 學習課題 {tid}「{t['title']}」補做收尾總整理。這一課上課時沒有做這一步，請根據下面我當時記下的筆記來整理。",
                 intro, "", "## 課題"] + _task_block(t) + _must_block(t)
        lines += _full_notes_block("我記下的【解法】", solved, BACKFILL_SOLUTIONS)
        lines += _full_notes_block("我踩過的錯", _mistakes(t), BACKFILL_MISTAKES)
        lines += _blockers_block(t) + _titles_block("其他筆記", other, limit=60) + _code_list_block(tid)
        lines += [""] + tpl("backfill") + [""] + tpl("wrapup") + _wrapup_extra(t) + [""] + tpl("notes") + [""] + tpl("style")
        lines += ["", "先告訴我你打算把這堂課分成哪幾步，並列出資訊不夠、需要我補充的地方，等我回答後再開始整理。"]
    elif kind == "cards":
        if t.get("plan") != "SPRINT" or task_kind(t) not in TECH_KINDS or not t.get("entries"):
            raise ValueError("這個課題沒有可以整理的筆記。")
        ents = t.get("entries", [])
        lines = [f"我要為 STM32 學習課題 {tid}「{t['title']}」整理面試卡，之後用來翻卡自測。請根據下面我的筆記來寫。",
                 intro, "", "## 課題"] + _task_block(t) + _must_block(t)
        lines += _titles_block("我在這一課踩過的錯", _mistakes(t), gist=True)
        lines += _titles_block("這一課已經有的面試卡（不要重複）", [e for e in ents if e.get("type") == "面試"])
        wrap = wrapup_note(t)
        if wrap:
            lines += ["", "### 本課的總整理筆記", _clip(wrap["text"], CARDS_WRAP)]
        else:
            lines += _full_notes_block("我記下的【解法】", [e for e in ents if e.get("type") == "解法"], BACKFILL_SOLUTIONS)
            lines += _titles_block("其他筆記", [e for e in ents if e.get("type") == "筆記"], limit=60, gist=True)
        lines += [""] + tpl("cards") + [""] + tpl("notes") + [""] + tpl("style")
        lines += ["", "先列出你打算出的題目（一行一題，標明對應哪個必學項目），我確認後再寫成面試卡。"]
    else:
        skip = STUCK_TAG + stuck_text.strip()
        lines = [f"我在 STM32 學習課題 {tid}「{t['title']}」卡關了，需要協助。", intro, "",
                 "## 卡在哪裡", stuck_text.strip() or "（請先問我卡在哪裡）", "",
                 "## 課題資訊"] + _task_block(t) + _own_notes_block(t, limit=40, skip=skip)
        code = _code_files(tid)
        if code:
            lines += ["", f"## 目前的程式碼（projects/{tid}/）"]
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
        lines += [""] + tpl("stuck") + [""] + tpl("notes") + [""] + tpl("style")
        if task_kind(t) != "career":
            lines += [""] + tpl("refs")
    return "\n".join(lines)


# ---------------------------------------------------------------- progress
def _date(s):
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


def study_dates(t):
    """這個課題有學習紀錄的日期（開始進行或記筆記的日子）。"""
    return {s["start"][:10] for s in t.get("sessions", []) if s.get("start")} | \
           {e["time"][:10] for e in t.get("entries", []) if e.get("time")}


def is_core(t):
    return t.get("priority", "core") == "core"


def is_tech(t):
    return t.get("stage") != CAREER_STAGE


def task_span_days(t):
    """從第一次開始到完成，跨了幾天（含頭尾）。"""
    dates = sorted(study_dates(t))
    if not dates or not t.get("finished_at"):
        return None
    return max(1, (_date(t["finished_at"]) - _date(dates[0])).days + 1)


def forecast(db, today=None):
    """進度儀表：必修完成數、最近的學習頻率、依實際速度推算的技術主線完成日。不設每課的次數上限。"""
    today = today or datetime.now().date()
    sp = [t for t in db["tasks"] if t.get("plan") == "SPRINT"]
    tech = [t for t in sp if is_core(t) and is_tech(t)]
    career = [t for t in sp if is_core(t) and not is_tech(t)]
    done = lambda ts: [t for t in ts if t["status"] == "已完成"]
    # 平均速度只看動手做的課（暫存器、驅動、架構、除錯）；觀念驗收和準備項目太短，會讓預估過於樂觀
    finished = sorted([t for t in done(tech) if task_span_days(t) and task_kind(t) in ("register", "driver", "arch", "debug")],
                      key=lambda t: t["finished_at"])
    spans = [task_span_days(t) for t in finished[-3:]]
    avg = round(sum(spans) / len(spans), 1) if spans else None
    weight = lambda t: 0.2 if task_kind(t) == "prep" else (0.5 if t["status"] == "進行中" else 1)   # 進行中的算半課
    remaining = round(sum(weight(t) for t in tech if t["status"] != "已完成"), 1)
    recent = {d for t in sp for d in study_dates(t) | {r["date"][:10] for r in t.get("reviews") or [] if r.get("date")}
              if 0 <= (today - _date(d)).days < 28}
    recent |= {d for d in (db.get("card_log") or {}) if 0 <= (today - _date(d)).days < 28}
    eta = None
    if avg and remaining:
        eta = (today + timedelta(days=round(remaining * avg))).strftime("%Y-%m-%d")
    return {"tech_done": len(done(tech)), "tech_total": len(tech), "career_done": len(done(career)), "career_total": len(career),
            "optional_done": len(done([t for t in sp if t.get("priority") == "optional"])),
            "optional_total": sum(1 for t in sp if t.get("priority") == "optional"),
            "study_days_28": len(recent), "avg_days": avg, "avg_from": [t["id"] for t in finished[-3:]],
            "remaining": remaining, "eta": eta, "today": today.strftime("%Y-%m-%d")}


# ---------------------------------------------------------------- review
REVIEW_INTERVALS = (1, 3, 7, 21)     # 完成後隔幾天複習；這次順利就換下一個間隔
REVIEW_KEEP = 45                     # 四個間隔都順利之後，每隔這麼多天再抽問一次，維持到面試
REVIEW_RESULTS = {"good": "順利", "ok": "部分卡住", "weak": "需要重看"}
HANDS_ON_KINDS = ("register", "driver", "arch", "debug")


def can_review(t):
    """已完成的技術課題才排複習（求職類、準備類、已併入的不排）。"""
    return bool(t.get("plan") == "SPRINT" and t.get("status") == "已完成" and t.get("priority") != "merged"
                and task_kind(t) in TECH_KINDS and t.get("finished_at"))


def review_info(t, today=None):
    """複習排程。順利 → 換下一個間隔；部分卡住 → 同一個間隔再一次；需要重看 → 回到 1 天。
    完成當天做的複習只記錄、不影響排程（剛學完還記得，不代表隔天還記得）；同一天複習多次只算最後一次。"""
    if not can_review(t):
        return None
    today = today or datetime.now().date()
    base = _date(t["finished_at"])
    revs = sorted(t.get("reviews") or [], key=lambda r: r.get("date") or "")
    by_day = {}
    for r in revs:
        if r.get("date"):
            by_day[r["date"][:10]] = r.get("result")
    level, last = 0, base
    for day in sorted(by_day):
        d = _date(day)
        if d == base:
            continue
        level = level + 1 if by_day[day] == "good" else (0 if by_day[day] == "weak" else level)
        last = max(last, d)
    gap = REVIEW_INTERVALS[level] if level < len(REVIEW_INTERVALS) else REVIEW_KEEP
    nxt = last + timedelta(days=gap)
    return {"count": len(revs), "level": level, "gap": gap, "next": nxt.strftime("%Y-%m-%d"), "due": nxt <= today,
            "late": max(0, (today - nxt).days), "in_days": (nxt - today).days, "last": revs[-1] if revs else None}


def nudges(db):
    """任務列表上方的提醒：前置課題完成後可以開始的課題（履歷第一版）、還沒有總整理筆記的已完成課題。"""
    out, by = [], {t["id"]: t for t in db["tasks"]}
    for t in db["tasks"]:
        dep = by.get(t.get("start_after") or "")
        if dep and dep["status"] == "已完成" and t["status"] == "未開始":
            out.append({"kind": "start", "task": t["id"], "title": t["title"], "after": dep["id"], "after_title": dep["title"]})
    for t in sorted(db["tasks"], key=lambda t: t.get("order", 0)):
        if can_review(t) and task_kind(t) in HANDS_ON_KINDS and t.get("entries") and not wrapup_note(t):
            out.append({"kind": "backfill", "task": t["id"], "title": t["title"]})
    for t in sorted(db["tasks"], key=lambda t: t.get("order", 0)):
        if can_review(t) and t.get("entries") and sum(1 for e in t["entries"] if e.get("type") == "面試") < FEW_CARDS:
            out.append({"kind": "cards", "task": t["id"], "title": t["title"]})
    return out


def act_review(db, body):
    """記錄一次複習結果，或撤銷最後一次紀錄。"""
    t = find(db, body["id"])
    if body.get("undo"):
        if not t.get("reviews"):
            raise ValueError("這個課題沒有複習紀錄。")
        r = t["reviews"].pop()
        save(db)
        return [f"已撤銷 {r['date']} 的複習紀錄。"]
    if not can_review(t):
        raise ValueError("只有已完成的技術課題可以記錄複習。")
    result = body.get("result")
    if result not in REVIEW_RESULTS:
        raise ValueError("複習結果不正確。")
    t.setdefault("reviews", []).append({"date": datetime.now().strftime("%Y-%m-%d"), "result": result,
                                        "note": (body.get("note") or "").strip()[:500]})
    save(db)
    info = review_info(t)
    when = "明天" if info["in_days"] == 1 else f"{info['in_days']} 天後"
    return [f"已記錄複習：{REVIEW_RESULTS[result]}。下次複習 {info['next']}（{when}）。"]


# ---------------------------------------------------------------- cards
# 翻卡自測：卡片不另外存，每次由筆記與必學項目組出來；progress.json 最上層的 cards 只記每張卡的排程。
CARD_KINDS = ("card", "must", "mistake", "note")
CARD_KIND_NAMES = {"card": "面試卡", "must": "必學項目", "mistake": "踩過的錯", "note": "筆記與解法"}
CARD_DEFAULT_KINDS = ("card", "must", "mistake")
CARD_BATCH = 10                      # 一次自測幾張
FEW_CARDS = 3                        # 已完成的課題面試卡少於這個數量時，提醒可以補
MUST_SECTION = "必學範圍對照"          # 總整理筆記裡逐項寫出必學重點的那一段
MUST_SKIP = re.compile(r"驗收|總整理")  # 這類必學項目是流程，不是可以口頭回答的題目


def _split_title(text):
    """筆記的第一行當題目（去掉【】開頭），其餘當答案。"""
    rows = text.strip().splitlines()
    if not rows:
        return "", ""
    title = HEAD_RE.sub("", rows[0].strip().lstrip("#").strip(), count=1).strip().strip("*").strip()
    return title, "\n".join(rows[1:]).strip()


def _bigrams(text):
    text = re.sub(r"[\s`*|｜、，。；：:;,.()（）「」／/\-]+", "", text).lower()
    return {text[i:i + 2] for i in range(len(text) - 1)}


def must_answer(wrap, item):
    """從總整理筆記的「必學範圍對照」找出這個必學項目對應的那幾行。回傳 (答案, 整段)；找不到就是空字串。"""
    if not wrap:
        return "", ""
    rows = wrap["text"].splitlines()
    start = next((i for i, x in enumerate(rows) if MUST_SECTION in x), None)
    if start is None:
        return "", ""
    bullet, sec = rows[start].startswith(("- ", "* ")), []
    for x in rows[start + 1:]:
        head = x.lstrip().startswith("#") or re.match(r"^\s*\*\*[^*]+\*\*\s*[:：]?\s*$", x)
        if head or (bullet and x.startswith(("- ", "* "))):
            break
        sec.append(x)
    want = _bigrams(item)
    filled = [x for x in sec if x.strip()]
    top = min((len(x) - len(x.lstrip()) for x in filled), default=0)
    best, score = None, 0.0
    for i, x in enumerate(sec):
        # 只比對最外層的項目（縮排在底下的是它的補充）；比的是每一行「：」之前或表格第一格的項目名稱
        if not x.strip() or len(x) - len(x.lstrip()) != top or re.match(r"^\s*\|?[\s:|-]+\|?\s*$", x):
            continue
        name = x.strip().strip("|").split("|")[0] if x.lstrip().startswith("|") else re.split(r"[:：]", x, maxsplit=1)[0]
        cand = _bigrams(name)
        sc = len(want & cand) / max(3, min(len(want), len(cand)))
        if sc > score:
            best, score = i, sc
    whole = "\n".join(sec).strip()
    if best is None or score < 0.5:
        return "", whole
    line = sec[best]
    if line.lstrip().startswith("|"):                       # 表格：帶上表頭
        top = best
        while top > 0 and sec[top - 1].lstrip().startswith("|"):
            top -= 1
        head = sec[top:top + 2] if top + 1 < best else []
        return "\n".join(head + [line]).strip(), whole
    indent = len(line) - len(line.lstrip())
    out = [line.strip()]
    for x in sec[best + 1:]:                                # 帶上縮排在它底下的幾行
        if not x.strip() or len(x) - len(x.lstrip()) <= indent:
            break
        out.append(x[indent:])
    return "\n".join(out), whole


def build_deck(db):
    """所有卡片（不含排程）。來源：【面試】卡、踩過的錯、已完成課題的必學項目、筆記與解法。"""
    deck = []
    for t in plan_tasks(db, "SPRINT"):
        if t.get("priority") == "merged":
            continue
        base = {"task": t["id"], "task_title": t["title"]}
        for e in t.get("entries", []):
            typ = e.get("type")
            kind = "card" if typ == "面試" else "mistake" if (typ == "問題" and not is_open(e)) else \
                   "note" if typ in ("筆記", "解法") else None
            if not kind or not e.get("id"):
                continue
            title, body = _split_title(e["text"])
            if not title or not body or (kind == "note" and "總整理" in title):
                continue
            deck.append(dict(base, key="e:" + e["id"], kind=kind, eid=e["id"], front=title, back=body, ref="",
                             hint="當時錯在哪？正確的做法是什麼？" if kind == "mistake" else "", born=e["time"][:10]))
        if can_review(t):
            wrap = wrapup_note(t)
            for m in t.get("must") or []:
                if not m.get("id") or MUST_SKIP.search(m.get("text") or ""):
                    continue
                ans, whole = must_answer(wrap, m["text"])
                ref = "" if ans else (whole or (wrap["text"] if wrap else ""))
                deck.append(dict(base, key=f"m:{t['id']}:{m['id']}", kind="must", eid=None, front=m["text"], back=ans, ref=ref,
                                 hint="不看筆記，口頭解釋這一項", born=t["finished_at"]))
    return deck


def card_info(db, card, today=None):
    """一張卡的排程。沒有紀錄的卡在進卡堆的隔天到期。"""
    today = today or datetime.now().date()
    st = (db.get("cards") or {}).get(card["key"]) or {}
    nxt = st.get("next") or (_date(card["born"]) + timedelta(days=1)).strftime("%Y-%m-%d")
    return {"lv": st.get("lv", 0), "next": nxt, "due": _date(nxt) <= today, "n": st.get("n", 0),
            "miss": st.get("miss", 0), "last": st.get("last")}


def card_summary(db, today=None):
    """各類卡片的總數與到期數，以及每個課題各有幾張。"""
    today = today or datetime.now().date()
    total, due, nxt, tasks = {k: 0 for k in CARD_KINDS}, {k: 0 for k in CARD_KINDS}, {k: None for k in CARD_KINDS}, {}
    for c in build_deck(db):
        info = card_info(db, c, today)
        row = tasks.setdefault(c["task"], {"id": c["task"], "title": c["task_title"],
                                           "total": {k: 0 for k in CARD_KINDS}, "due": {k: 0 for k in CARD_KINDS}})
        total[c["kind"]] += 1
        row["total"][c["kind"]] += 1
        if info["due"]:
            due[c["kind"]] += 1
            row["due"][c["kind"]] += 1
        elif nxt[c["kind"]] is None or info["next"] < nxt[c["kind"]]:
            nxt[c["kind"]] = info["next"]
    return {"total": total, "due": due, "next": nxt, "tasks": list(tasks.values()), "names": CARD_KIND_NAMES, "batch": CARD_BATCH}


def _spread(cards):
    """相鄰兩張盡量來自不同課題（交錯練習），其餘順序不變。"""
    rest, out = list(cards), []
    while rest:
        i = next((k for k, c in enumerate(rest) if not out or c["task"] != out[-1]["task"]), 0)
        out.append(rest.pop(i))
    return out


def pick_cards(db, mode="due", kinds=None, task="", limit=CARD_BATCH, today=None):
    """挑出這一輪要翻的卡。due：到期的，先面試卡、再依到期日；free：自由練習，隨機、不看到期日。"""
    kinds = [k for k in (kinds or CARD_DEFAULT_KINDS) if k in CARD_KINDS]
    deck = [dict(c, **card_info(db, c, today)) for c in build_deck(db) if c["kind"] in kinds and (not task or c["task"] == task)]
    if mode == "free":
        random.shuffle(deck)
    else:
        deck = [c for c in deck if c["due"]]
        deck.sort(key=lambda c: (c["kind"] != "card", c["next"], c["key"]))
    picked = _spread(deck[:limit] if limit else deck)
    return picked, len(deck)


def prune_cards(db):
    """筆記或必學項目已經不存在的卡，把排程紀錄清掉。"""
    cards = db.get("cards")
    if not cards:
        return
    valid = {"e:" + e["id"] for t in db["tasks"] for e in t.get("entries", []) if e.get("id")} | \
            {f"m:{t['id']}:{m['id']}" for t in db["tasks"] for m in t.get("must") or [] if m.get("id")}
    for key in [k for k in cards if k not in valid]:
        del cards[key]


def _weak_cards_block(db, t):
    """翻卡自測時答不出來、到現在還沒補回來的卡：帶進複習提示詞，請 Claude 優先考。"""
    st = db.get("cards") or {}
    weak = [c for c in build_deck(db) if c["task"] == t["id"] and c["kind"] in CARD_DEFAULT_KINDS
            and st.get(c["key"], {}).get("miss") and not st[c["key"]].get("lv")]
    if not weak:
        return []
    return ["", "### 翻卡自測時答不出來的（優先再考）"] + [f"- {c['front']}（{CARD_KIND_NAMES[c['kind']]}）" for c in weak[:20]]


def act_card_rate(db, body):
    """記錄一張卡的自評。記得 → 換下一個間隔；模糊 → 同樣的間隔；忘了 → 回到隔天。同一天只算第一次。"""
    key, result = body.get("key") or "", body.get("result")
    if result not in REVIEW_RESULTS:
        raise ValueError("自評結果不正確。")
    card = next((c for c in build_deck(db) if c["key"] == key), None)
    if not card:
        raise ValueError("找不到這張卡（對應的筆記可能已經刪除）。")
    today = datetime.now().date()
    day = today.strftime("%Y-%m-%d")
    cards = db.setdefault("cards", {})
    st = cards.get(key) or {"lv": 0, "n": 0, "miss": 0}
    if st.get("last") == day:
        return {"messages": [], "counted": False, "card": card_info(db, card, today)}
    lv = st.get("lv", 0) + 1 if result == "good" else (0 if result == "weak" else st.get("lv", 0))
    gap = REVIEW_INTERVALS[lv] if lv < len(REVIEW_INTERVALS) else REVIEW_KEEP
    cards[key] = {"lv": lv, "next": (today + timedelta(days=gap)).strftime("%Y-%m-%d"), "last": day,
                  "n": st.get("n", 0) + 1, "miss": st.get("miss", 0) + (result == "weak")}
    log_ = db.setdefault("card_log", {})
    log_[day] = log_.get(day, 0) + 1
    save(db, export=False)             # 一輪要評很多張，不必每張都重新產生所有筆記頁
    return {"messages": [], "counted": True, "card": card_info(db, card, today)}


# ---------------------------------------------------------------- actions
def act_start(db, body):
    t = find(db, body["id"])
    if t.get("priority") == "merged":
        raise ValueError(f"這個課題已經併入 {t.get('merged_into')}，請從那一課開始。")
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
    return {"messages": msgs, "prompt": build_prompt(db, t["id"], "start"), "prompt_kind": prompt_kind(t)}


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
    t.pop("reviews", None)
    if not body.get("start", True):
        save(db)
        return ["已重設為「未開始」。"]
    res = act_start(db, {"id": t["id"]})
    res["messages"].insert(0, f"已清除 {t['id']} 的紀錄，重新開始。")
    return res


def act_entry(db, body):
    """存一則。開頭有【】就依它決定類型，沒有才用畫面上選的類型。"""
    t = find(db, body["id"])
    text = (body.get("text") or "").strip()
    fallback = body.get("type") if body.get("type") in ENTRY_TYPES else "筆記"
    if not text:
        raise ValueError("請輸入內容。")
    e = make_entry(type_from_text(text, fallback), text)
    t["entries"].append(e)
    save(db)
    return [f"已儲存（{e['type']}）。"]


def act_entry_preview(db, body):
    """把貼上的文字拆成多則並檢查重複，只回傳預覽，不存檔。"""
    t = find(db, body["id"])
    fallback = body.get("type") if body.get("type") in ENTRY_TYPES else "筆記"
    items = split_notes(body.get("text") or "", fallback)
    existing = {}
    for e in t.get("entries", []):
        if not is_progress(e):
            existing[_title_key(e["text"])] = e          # 同標題取最新的一則
    for it in items:
        dup = None if it["type"] == "進度" else existing.get(_title_key(it["text"]))
        it["dup"] = {"eid": dup["id"], "time": dup["time"], "same": dup["text"].strip() == it["text"].strip()} if dup else None
        it["mode"] = "skip" if (not it["keep"] or (dup and it["dup"]["same"])) else ("replace" if dup else "add")
    return {"messages": [], "items": items}


def act_entry_batch(db, body):
    """一次存多則。mode：add 新增、replace 取代同標題的舊筆記、skip 略過。"""
    t = find(db, body["id"])
    added = replaced = skipped = 0
    for it in body.get("items") or []:
        text = (it.get("text") or "").strip()
        mode = it.get("mode") or "add"
        if not text or mode == "skip":
            skipped += 1
            continue
        typ = it.get("type") if it.get("type") in ENTRY_TYPES else type_from_text(text)
        if mode == "replace" and it.get("dup_eid"):
            try:
                _, e = find_entry(t, it["dup_eid"])
            except KeyError:
                e = None
            if e is not None:
                e["text"] = text
                e["edited"] = now()
                apply_type(e, typ)
                replaced += 1
                continue
        t["entries"].append(make_entry(typ, text))
        added += 1
    if not (added or replaced):
        return ["沒有需要儲存的紀錄。"]
    save(db)
    parts = [f"新增 {added} 則"] if added else []
    parts += [f"取代 {replaced} 則"] if replaced else []
    parts += [f"略過 {skipped} 則"] if skipped else []
    return ["已儲存：" + "、".join(parts) + "。"]


def act_entry_update(db, body):
    t = find(db, body["id"])
    _, e = find_entry(t, body.get("eid"))
    if "text" in body:
        text = (body["text"] or "").strip()
        if not text:
            raise ValueError("內容不能是空的；要移除請按刪除。")
        if text != e["text"]:
            e["text"] = text
            e["edited"] = now()
    if body.get("type") in ENTRY_TYPES:
        apply_type(e, body["type"])
    if "open" in body and e["type"] == "問題":
        e["open"] = bool(body["open"])
        e["resolved"] = not e["open"]
    if "done" in body and e["type"] == "待學":
        e["resolved"] = bool(body["done"])
    save(db)
    return ["已更新。"]


def act_entry_delete(db, body):
    t = find(db, body["id"])
    i, _ = find_entry(t, body.get("eid"))
    t["entries"].pop(i)
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
        text = summary if summary.startswith(STUCK_TAG) else STUCK_TAG + summary
        t["entries"].append(make_entry("問題", text, open_=True))
        head = f"{t['id']}: 卡關 {t['title']}"
    else:
        t["status"] = status
        if summary:   # 每次的進度都保留，不會互相覆蓋
            text = summary if summary.startswith(PROGRESS_TAG) else PROGRESS_TAG + summary
            t["entries"].append(make_entry("進度", text))
        head = f"{t['id']}: 進度 {t['title']}（第 {n} 次）"
    save(db)
    msg = f"{head}\n\n狀態：{t['status']}"
    if summary:
        msg += f"\n\n{summary}"
    msgs = commit_learning(msg, tag=t["id"] if done else None)
    if status == "卡關":
        return {"messages": msgs, "prompt": build_prompt(db, t["id"], "stuck", summary), "prompt_kind": "stuck"}
    if done:
        for x in db["tasks"]:
            if x.get("start_after") == t["id"] and x["status"] == "未開始":
                msgs.append(f"現在可以開始「{x['title']}」（{x['id']}）了，和技術課並行。")
        info = review_info(t)
        if info:
            msgs.append(f"已排入複習，第一次在 {info['next']}。現在可以先做一次約 15 分鐘的口頭複習。")
            return {"messages": msgs, "prompt": build_prompt(db, t["id"], "review"), "prompt_kind": "review", "prompt_task": t["id"]}
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


def act_must(db, body):
    """勾選或取消一項必學範圍。"""
    t = find(db, body["id"])
    m = next((x for x in t.get("must") or [] if x.get("id") == body.get("mid")), None)
    if m is None:
        raise ValueError("找不到這個必學項目。")
    m["done"] = datetime.now().strftime("%Y-%m-%d") if body.get("done") else None
    save(db)
    return ["已更新必學範圍。"]


def act_todo(db, body):
    """勾掉或恢復一項 TODO。存在 progress.json 最上層的 todo_done（舊版 App 存檔時會保留它）。"""
    key = body.get("key") or ""
    if key not in {x["key"] for x in all_todos(db)}:
        raise ValueError("找不到這項 TODO。")
    done = db.setdefault("todo_done", {})
    if body.get("done"):
        done[key] = datetime.now().strftime("%Y-%m-%d")
    else:
        done.pop(key, None)
    save(db)
    return ["已更新 TODO。"]


def act_sync(db, body):
    ok, m = pull()
    msgs = [m]
    if ok:
        msgs.append(push())
    return msgs


# 舊計畫（HAL 版）已封存：這些操作不能用在舊計畫的課題上
READONLY_HAL = {"/api/start", "/api/restart", "/api/leave", "/api/entry", "/api/entry/batch", "/api/entry/update",
                "/api/entry/delete", "/api/finish", "/api/status", "/api/must", "/api/review", "/api/file/delete"}


def check_writable(db, tid):
    if find(db, tid).get("plan") == "HAL":
        raise ValueError("舊計畫（HAL 版）已封存，只能查看。")


ACTIONS = {
    "/api/start": act_start,
    "/api/restart": act_restart,
    "/api/leave": act_leave,
    "/api/entry": act_entry,
    "/api/entry/preview": act_entry_preview,
    "/api/entry/batch": act_entry_batch,
    "/api/entry/update": act_entry_update,
    "/api/entry/delete": act_entry_delete,
    "/api/finish": act_finish,
    "/api/status": act_status,
    "/api/sync": act_sync,
    "/api/todo": act_todo,
    "/api/must": act_must,
    "/api/review": act_review,
    "/api/card/rate": act_card_rate,
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
                                   "todos": all_todos(db), "later": all_later(db), "forecast": forecast(db),
                                   "review": {t["id"]: r for t in db["tasks"] for r in [review_info(t)] if r},
                                   "nudges": nudges(db), "cards": card_summary(db),
                                   "sync_error": STATE.get("sync_error"),
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
                tid = q.get("id", [""])[0]
                kind = prompt_kind(find(db, tid), q.get("kind", ["start"])[0])
                text = build_prompt(db, tid, kind, q.get("stuck", [""])[0])
            except (KeyError, ValueError) as e:
                return self.send(400, {"error": str(e)})
            return self.send(200, {"prompt": text, "kind": kind})
        if u.path == "/api/cards":
            q = parse_qs(u.query)
            try:
                with LOCK:
                    db = load()
                mode = "free" if q.get("mode", ["due"])[0] == "free" else "due"
                kinds = [k for k in q.get("kinds", [""])[0].split(",") if k]
                limit = max(0, int(q.get("limit", [str(CARD_BATCH)])[0] or 0))
                cards, total = pick_cards(db, mode, kinds, q.get("task", [""])[0], limit)
            except (KeyError, ValueError) as e:
                return self.send(400, {"error": str(e)})
            return self.send(200, {"cards": cards, "total": total, "mode": mode})
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
                if u.path in READONLY_HAL and body.get("id"):
                    check_writable(db, body["id"])
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
            check_writable(load(), tid)
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


def free_port(start=FIRST_PORT):
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
            ctypes.windll.user32.MessageBoxW(None, msg, "STM32 學習進度（新版）", 0x10)
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
        profile = os.path.join(base, "STM32Tracker2", "window")  # 專用設定檔：不影響你平常的瀏覽器，也和舊版分開
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


def old_app_running():
    """舊版 App 是否正在執行（兩個 App 共用同一份資料，不能同時開）。"""
    try:
        with open(OLD_PORT_FILE, encoding="utf-8") as f:
            port = int(f.read().strip())
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=1.5) as r:  # noqa: S310
            return json.loads(r.read()).get("app") == OLD_APP_ID
    except (OSError, ValueError):
        return False


SHORT_SESSION_MIN = 10       # 沒有記任何筆記、又短於這個分鐘數的進行紀錄視為誤按，不保留


def close_open_session():
    """App 關閉時如果還有課題在進行，自動結束這一次（課題狀態不變），並在本機 commit。"""
    try:
        with LOCK:
            db = load()
            t = active_task(db)
            if not t:
                return
            s = t["sessions"][-1]
            added = [e for e in t.get("entries", []) if e["time"] >= s["start"]]
            minutes = (datetime.now() - datetime.strptime(s["start"], "%Y-%m-%d %H:%M")).total_seconds() / 60
            if added or minutes >= SHORT_SESSION_MIN:
                s["end"] = now()
            else:
                t["sessions"].pop()
                t["status"] = s.get("prev_status") or ("進行中" if t["sessions"] else "未開始")
                t["finished_at"] = s.get("prev_finished")
            save(db)
            if git_info().get("is_repo"):
                commit_learning_quiet(f"自動儲存：關閉 App 時結束 {t['id']} 的這一次")
        log(f"關閉時自動結束 {t['id']} 的這一次。")
    except Exception as e:  # noqa: BLE001
        log(f"關閉時自動結束進行中的課題失敗：{type(e).__name__}: {e}")


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
        alert(f"找不到 learning/progress.json\n\n請確認 STM32Tracker2.exe 放在 repo 根目錄。\n目前位置：{ROOT}")
        sys.exit(1)
    if old_app_running():
        alert("舊版 App（STM32Tracker.exe）還開著。\n\n兩個 App 共用同一份筆記，不能同時開啟。\n請先關閉舊版，再開新版。")
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
    print(f"STM32 學習進度 App（新版）已啟動：{url}（關閉視窗即結束）")
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
        close_open_session()
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
