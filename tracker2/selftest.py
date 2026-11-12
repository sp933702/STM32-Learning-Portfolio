#!/usr/bin/env python3
"""新版 App（tracker2）的自我檢查。

修改 tracker2/ 裡的任何檔案之後執行：
    python tracker2/selftest.py
全部通過會顯示「全部通過」，否則列出失敗的項目。檢查過程不會改動真正的筆記資料。
"""
import ast
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = []
KINDS = ("register", "driver", "arch", "debug", "concept", "career", "prep")
PROMPT_FILES = ("teach_new", "teach_continue", "teach_common", "scope", "hal", "wrapup", "refs", "notes", "style", "stuck",
                "review", "backfill") + \
    tuple("kind_" + k for k in KINDS)
FORBIDDEN = ("對應的舊 HAL 版任務", "預定 10-", "4.5 ", "目標次數")     # 不應該出現在提示詞裡的文字
LIMITS = {"new": 10000, "continue": 10000, "review": 12000, "backfill": 30000}   # 提示詞字數上限（求助提示詞另外算，因為含程式碼）

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


def check(name):
    def deco(fn):
        try:
            note = fn()
            RESULTS.append((True, name, note or ""))
        except Skip as e:
            RESULTS.append((None, name, str(e)))
        except AssertionError as e:
            RESULTS.append((False, name, str(e) or "檢查沒有通過"))
        except Exception as e:  # noqa: BLE001
            RESULTS.append((False, name, f"{type(e).__name__}: {e}"))
        return fn
    return deco


class Skip(Exception):
    pass


def load_app(root_override=None):
    """把 app.py 當模組載入。root_override 給測試用的資料夾，避免動到真正的資料。"""
    old = os.environ.get("STM32_TRACKER_ROOT")
    if root_override:
        os.environ["STM32_TRACKER_ROOT"] = root_override
    else:
        os.environ.pop("STM32_TRACKER_ROOT", None)
    try:
        spec = importlib.util.spec_from_file_location("tracker2_app_" + ("tmp" if root_override else "real"),
                                                      os.path.join(HERE, "app.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old is None:
            os.environ.pop("STM32_TRACKER_ROOT", None)
        else:
            os.environ["STM32_TRACKER_ROOT"] = old


def page_scripts():
    html = open(os.path.join(HERE, "index.html"), encoding="utf-8").read()
    return re.findall(r"<script>(.*?)</script>", html, flags=re.S)


def node():
    exe = shutil.which("node")
    if not exe:
        raise Skip("找不到 node，略過（不影響使用；裝了 Node.js 才會檢查頁面程式的語法）")
    return exe


@check("app.py 語法")
def _():
    ast.parse(open(os.path.join(HERE, "app.py"), encoding="utf-8").read())


@check("提示詞規則檔齊全")
def _():
    for name in PROMPT_FILES:
        path = os.path.join(HERE, "prompts", name + ".md")
        assert os.path.isfile(path), f"缺少 prompts/{name}.md"
        text = re.sub(r"<!--.*?-->", "", open(path, encoding="utf-8-sig").read(), flags=re.S).strip()
        assert text, f"prompts/{name}.md 是空的"
    return f"{len(PROMPT_FILES)} 個"


@check("頁面程式語法（index.html）")
def _():
    exe = node()
    scripts = page_scripts()
    assert len(scripts) >= 2, "index.html 應該有錯誤攔截與主程式兩段 <script>"
    for i, js in enumerate(scripts):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(js)
        try:
            r = subprocess.run([exe, "--check", f.name], capture_output=True, text=True, encoding="utf-8", errors="replace")
            assert r.returncode == 0, f"第 {i + 1} 段 <script> 有語法錯誤：\n{r.stderr.strip()[:600]}"
        finally:
            os.unlink(f.name)
    return f"{len(scripts)} 段"


@check("Markdown 顯示（表格裡的 | 與程式碼）")
def _():
    exe = node()
    main = page_scripts()[-1]
    a, b = main.index("const esc"), main.index("let S = {")
    test = r'''
const out = md(["| 目的 | 寫法 | 效果 |", "|---|---|---|",
  "| 設成 1 | `REG \\|= Msk` | 只有遮罩的 bit 變 1 |",
  "| OR | `a | b` | 反引號內不跳脫也可以 |",
  "| 文字 | A \\| B | 一般文字的跳脫 |"].join("\n"));
const rows = out.split("<tr>").slice(1).map(r => (r.match(/<t[dh]>/g) || []).length);
if (rows.join(",") !== "3,3,3,3") { console.error("表格欄數錯誤：" + rows.join(",")); process.exit(1); }
if (!out.includes("<code>REG |= Msk</code>")) { console.error("跳脫的 | 沒有還原"); process.exit(1); }
const code = md("```c\nint a = 1 < 2;\n```");
if (!code.includes("<pre><code>int a = 1 &lt; 2;</code></pre>")) { console.error("程式碼區塊錯誤：" + code); process.exit(1); }
const list = md("- 第一點\n- **粗體**與 `碼`");
if (!list.includes("<ul><li>第一點</li><li><b>粗體</b>與 <code>碼</code></li></ul>")) { console.error("清單錯誤：" + list); process.exit(1); }
'''
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write("const $ = () => null;\n" + main[a:b] + test)
    try:
        r = subprocess.run([exe, f.name], capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert r.returncode == 0, r.stderr.strip()[:600]
    finally:
        os.unlink(f.name)


@check("筆記資料可以讀取（learning/progress.json）")
def _():
    db = json.load(open(os.path.join(ROOT, "learning", "progress.json"), encoding="utf-8"))
    tasks = db["tasks"]
    n = 0
    for t in tasks:
        for k in ("id", "title", "status", "plan", "entries", "sessions"):
            assert k in t, f"{t.get('id')} 缺少欄位 {k}"
        for e in t["entries"]:
            assert {"time", "type", "text"} <= set(e), f"{t['id']} 有筆記缺少必要欄位"
            n += 1
    return f"{len(tasks)} 個課題、{n} 則筆記"


@check("用實際資料產生提示詞")
def _():
    app = load_app()
    db = app.load()
    sizes, worst = {}, {}
    for t in db["tasks"]:
        if t.get("plan") != "SPRINT":
            continue
        for kind in ("new", "continue", "stuck"):
            text = app.build_prompt(db, t["id"], kind, "測試：卡在某個地方")
            for bad in FORBIDDEN:
                assert bad not in text, f"{t['id']} 的 {kind} 提示詞出現不該有的文字「{bad}」"
            for must in ("## 寫法規則", "## 筆記格式"):
                assert must in text, f"{t['id']} 的 {kind} 提示詞缺少「{must}」"
            if kind in LIMITS:
                assert len(text) <= LIMITS[kind], f"{t['id']} 的 {kind} 提示詞有 {len(text)} 字，超過上限 {LIMITS[kind]}"
            if len(text) > worst.get(kind, (0, ""))[0]:
                worst[kind] = (len(text), t["id"])
        extra = (["review"] if app.can_review(t) else []) + \
                (["backfill"] if t.get("entries") and app.task_kind(t) in app.TECH_KINDS else [])
        for kind in extra:
            text = app.build_prompt(db, t["id"], kind)
            need = ("## 請這樣考我", "## 結束時給我") if kind == "review" else ("## 請這樣整理", "## 收尾總整理", "收尾總整理時另外附上")
            for must in need + ("## 寫法規則", "## 筆記格式"):
                assert must in text, f"{t['id']} 的 {kind} 提示詞缺少「{must}」"
            assert len(text) <= LIMITS[kind], f"{t['id']} 的 {kind} 提示詞有 {len(text)} 字，超過上限 {LIMITS[kind]}"
            if len(text) > worst.get(kind, (0, ""))[0]:
                worst[kind] = (len(text), t["id"])
    active = app.active_task(db)
    if active:
        auto = app.build_prompt(db, active["id"], "start")
        sizes["進行中的課題"] = f"{active['id']} {app.prompt_kind(active)} {len(auto)} 字"
    return "；".join([f"最長 {k}：{v[0]} 字（{v[1]}）" for k, v in worst.items()] + list(sizes.values()))


@check("課程資料：必修、選修、必學範圍")
def _():
    db = json.load(open(os.path.join(ROOT, "learning", "progress.json"), encoding="utf-8"))
    sp = [t for t in db["tasks"] if t.get("plan") == "SPRINT"]
    ids = {t["id"] for t in db["tasks"]}
    assert all(t.get("stage") for t in sp), "課題還沒有階段等欄位（另一台電腦要先同步到第 3 批之後的資料）"
    for t in sp:
        assert t.get("kind") in KINDS, f"{t['id']} 的類型不正確：{t.get('kind')}"
        assert t.get("priority") in ("core", "optional", "merged"), f"{t['id']} 的 priority 不正確"
        assert isinstance(t.get("order"), int), f"{t['id']} 沒有順序"
        assert t["status"] in ("未開始", "進行中", "已完成", "卡關", "暫緩"), f"{t['id']} 的狀態舊版 App 不認得：{t['status']}"
        if t["priority"] == "merged":
            assert t.get("merged_into") in ids, f"{t['id']} 併入的課題不存在"
        else:
            assert t.get("must"), f"{t['id']} 沒有必學範圍"
            assert len({m["id"] for m in t["must"]}) == len(t["must"]) and all(m.get("text") for m in t["must"]), f"{t['id']} 的必學範圍格式不對"
    n = lambda pr: sum(1 for t in sp if t["priority"] == pr)
    return f"必修 {n('core')}、選修 {n('optional')}、已併入 {n('merged')}；必學項目 {sum(len(t.get('must') or []) for t in sp)} 項"


@check("各類課題的提示詞用對規則")
def _():
    app = load_app()
    db = app.load()
    sp = [t for t in db["tasks"] if t.get("plan") == "SPRINT" and t.get("priority") != "merged"]
    seen = {}
    for t in sp:
        seen.setdefault(app.task_kind(t), t)
    missing = [k for k in KINDS if k not in seen]
    assert not missing, f"沒有這些類型的課題可以測試：{missing}"
    for kind, t in seen.items():
        text = app.build_prompt(db, t["id"], "new")
        if t.get("must"):
            assert "### 必學範圍" in text, f"{t['id']} 的提示詞沒有必學範圍"
        if kind == "career":
            for bad in ("RM0008", "HAL 對照", "收尾總整理", "範圍控制"):
                assert bad not in text, f"求職類課題（{t['id']}）的提示詞不應該出現「{bad}」"
        elif kind == "prep":
            assert "HAL 對照" not in text and "收尾總整理（驗收通過後一定要做）" not in text
        else:
            assert "## 範圍控制" in text and "## 收尾總整理" in text and "## 查文件的方式" in text, f"{t['id']} 缺少共通規則"
            assert ("## HAL 對照" in text) == (kind == "register"), f"HAL 對照只應該出現在暫存器類課題（{t['id']}）"
    assert "datasheet" in app.build_prompt(db, seen["driver"]["id"], "new")
    return "、".join(f"{k}（{t['id'].replace('SPRINT-', '')}）" for k, t in seen.items())


@check("預估完成日的計算")
def _():
    import datetime as dt
    app = load_app()
    mk = lambda i, status, start=None, fin=None, kind="register", stage="基礎", pr="core": {
        "id": f"T{i}", "plan": "SPRINT", "status": status, "kind": kind, "stage": stage, "priority": pr, "order": i,
        "sessions": [{"start": start + " 20:00", "end": start + " 21:00"}] if start else [], "entries": [], "finished_at": fin}
    db = {"tasks": [
        mk(1, "已完成", "2026-01-01", "2026-01-02", kind="concept"),        # 觀念課不列入平均
        mk(2, "已完成", "2026-01-03", "2026-01-08"),                       # 6 天
        mk(3, "已完成", "2026-01-09", "2026-01-22"),                       # 14 天
        mk(4, "進行中", "2026-01-23"), mk(5, "未開始"), mk(6, "未開始", kind="prep"),
        mk(7, "未開始", kind="career", stage="求職線"), mk(8, "未開始", pr="optional", stage="選修"), mk(9, "暫緩", pr="merged")]}
    f = app.forecast(db, today=dt.date(2026, 1, 25))
    assert (f["tech_done"], f["tech_total"], f["career_total"], f["optional_total"]) == (3, 6, 1, 1), f
    assert f["avg_days"] == 10.0 and f["avg_from"] == ["T2", "T3"], f
    assert f["remaining"] == 1.7 and f["eta"] == "2026-02-11", f          # 0.5（進行中）＋1＋0.2（準備）＝1.7 課 × 10 天
    assert f["study_days_28"] == 4, f
    assert app.forecast({"tasks": [mk(1, "未開始")]}, today=dt.date(2026, 1, 1))["eta"] is None


@check("複習排程的計算")
def _():
    import datetime as dt
    app = load_app()
    day = lambda n: (dt.date(2026, 1, 10) + dt.timedelta(days=n)).strftime("%Y-%m-%d")
    mk = lambda revs, **kw: dict({"id": "T1", "plan": "SPRINT", "status": "已完成", "kind": "register", "priority": "core",
                                  "finished_at": day(0), "entries": [], "sessions": [],
                                  "reviews": [{"date": day(n), "result": r} for n, r in revs]}, **kw)
    info = lambda revs, today, **kw: app.review_info(mk(revs, **kw), today=dt.date(2026, 1, 10) + dt.timedelta(days=today))
    assert info([], 0)["next"] == day(1) and not info([], 0)["due"], "完成後隔天才第一次複習"
    assert info([], 1)["due"] and info([], 5)["late"] == 4
    assert info([(0, "good")], 0)["next"] == day(1), "完成當天做的複習不影響排程"
    assert info([(1, "good")], 1)["next"] == day(4), "順利 → 3 天後"
    assert info([(1, "good"), (4, "good")], 4)["next"] == day(11), "再順利 → 7 天後"
    assert info([(1, "good"), (4, "ok")], 4)["next"] == day(7), "部分卡住 → 同樣的間隔（3 天）再一次"
    assert info([(1, "good"), (4, "good"), (11, "weak")], 11)["next"] == day(12), "需要重看 → 隔天"
    assert info([(1, "ok"), (1, "good")], 1)["next"] == day(4), "同一天複習兩次只算最後一次"
    full = [(1, "good"), (4, "good"), (11, "good"), (32, "good")]
    assert info(full, 32)["next"] == day(32 + app.REVIEW_KEEP), "四個間隔都順利之後改成長間隔"
    assert app.REVIEW_INTERVALS == (1, 3, 7, 21)
    for kw in ({"status": "進行中"}, {"kind": "career"}, {"kind": "prep"}, {"priority": "merged"}, {"plan": "HAL"}):
        assert info([], 5, **kw) is None, f"這種課題不應該排複習：{kw}"
    # 提醒：前置課題完成後可以開始的課題、還沒有總整理的課題
    dep = mk([], id="A", entries=[{"type": "解法", "text": "【解法】某個做法", "time": "2026-01-10 10:00"}])
    nxt = {"id": "B", "plan": "SPRINT", "status": "未開始", "kind": "career", "priority": "core", "title": "履歷", "start_after": "A",
           "entries": [], "sessions": []}
    dep["title"] = "陀螺儀"
    kinds = [(x["kind"], x["task"]) for x in app.nudges({"tasks": [dep, nxt]})]
    assert kinds == [("start", "B"), ("backfill", "A")], kinds
    dep["entries"].append({"type": "解法", "text": "【解法】A 總整理：從頭到尾每一步", "time": "2026-01-10 11:00"})
    nxt["status"] = "進行中"
    assert app.nudges({"tasks": [dep, nxt]}) == [], "有總整理、後續課題已開始之後就不再提醒"


@check("面試準備頁的彙整")
def _():
    app = load_app()
    F = "`" * 3
    note = "\n".join(["【解法】volatile 的實驗", "**一句話重點**", "", "**原因**", "- 編譯器不知道中斷會改它", "",
                      "**面試版**", "- tick 在中斷加 1、主程式讀", F + "c", "# 這行在程式碼裡，不是標題", F, "- 限制：不保證原子性", "",
                      "**其他補充**", "- 這段不屬於面試版"])
    sec = app.speak_section(note)
    assert sec.startswith("**面試版**") and "不保證原子性" in sec and "不是標題" in sec, "面試版段落沒有取完整"
    assert "其他補充" not in sec and "編譯器不知道" not in sec, "面試版段落取到別段的內容"
    listed = "- **驗證結果**：一致\n- **面試版 30 秒說明**：先開時脈\n  - 再設定模式\n- **必學範圍對照**：略"
    assert app.speak_section(listed) == "- **面試版 30 秒說明**：先開時脈\n  - 再設定模式", app.speak_section(listed)
    assert app.speak_section("【筆記】沒有相關段落\n- 面試常考") == ""
    mk = lambda typ, text: {"id": text[:6], "type": typ, "text": text, "time": "2026-01-10 10:00"}
    db = {"tasks": [
        {"id": "T1", "plan": "SPRINT", "title": "GPIO", "stage": "基礎", "order": 1, "status": "已完成", "kind": "register",
         "priority": "core", "finished_at": "2026-01-10", "sessions": [],
         "entries": [mk("面試", "【面試】為什麼要先開周邊時脈？\n**沒有時脈，暫存器寫不進去**\n- 可能的追問：怎麼確認"),
                     mk("解法", "【解法】驗收回答範本（面試用）\n- 第一題的回答"), mk("解法", note),
                     mk("筆記", "【筆記】Include guard\n- 防止重複引入（面試常問）"), mk("筆記", "【筆記】無關的筆記\n- 內容")]},
        {"id": "T2", "plan": "SPRINT", "title": "SysTick", "stage": "基礎", "order": 2, "status": "已完成", "kind": "register",
         "priority": "core", "finished_at": "2026-01-12", "sessions": [], "entries": [mk("筆記", "【筆記】只有一般筆記")]},
        {"id": "T3", "plan": "SPRINT", "title": "履歷", "stage": "求職線", "order": 3, "status": "未開始", "kind": "career",
         "priority": "core", "sessions": [], "entries": []}]}
    assert app.type_from_text("【面試】題目") == "面試" and "面試" in app.ENTRY_TYPES
    text = "\n".join(app.interview_lines(db))
    for must in ("#### 為什麼要先開周邊時脈？", "**沒有時脈，暫存器寫不進去**", "#### 驗收回答範本（面試用）",
                 "#### 面試版說明（出自「volatile 的實驗」）", "- Include guard", "## 還沒有面試卡的已完成課題", "- T2 SysTick"):
        assert must in text, f"面試準備頁缺少「{must}」"
    assert "無關的筆記" not in text and "只有一般筆記" not in text and "T3" not in text, "面試準備頁放進了無關的內容"
    assert "面試卡 1 則" in text


@check("TODO 會帶進提示詞")
def _():
    app = load_app()
    db = app.load()
    todos = app.all_todos(db)
    opened = [x for x in todos if not x["done"]]
    if not opened:
        return "目前沒有未處理的 TODO"
    last = [t for t in db["tasks"] if t.get("plan") == "SPRINT"][-1]
    text = app.build_prompt(db, last["id"], "new")
    for x in opened:
        assert x["text"] in text, f"TODO「{x['text'][:30]}」沒有出現在提示詞"
    return f"{len(opened)} 項未處理"


@check("貼上的文字拆成多則")
def _():
    app = load_app()
    F = "`" * 3
    reply = "\n".join([
        "好的，這一步整理成三則筆記：", "",
        F + "markdown", "【筆記】SysTick 的時脈來源", "**CLKSOURCE 選處理器時脈**", "",
        "| 欄位 | 值 |", "|---|---|", "| CLKSOURCE | 1 |", F, "",
        "下面這則包含程式碼：", "",
        F + "markdown", "【問題】延遲函式用 if，沒有等待", "**if 只檢查一次**", "",
        F + "c", "while ((now - start) < ms) { }", F, "", "- 改用 while", F, "",
        F + "markdown", "【待學】GCC 最佳化等級的差異：做效能量測時再學", F, "",
        F + "markdown", "【本次進度】完成 SysTick 初始化，下一步做 non-blocking LED", F, "",
        "有問題再跟我說。"])
    items = app.split_notes(reply)
    assert [x["type"] for x in items] == ["筆記", "問題", "待學", "進度"], [x["type"] for x in items]
    assert "有問題再跟我說" not in items[-1]["text"] and "好的" not in items[0]["text"], "區塊外的說明文字不應該存進去"
    assert F + "c" in items[1]["text"] and "- 改用 while" in items[1]["text"], "筆記裡的程式碼區塊被切斷了"
    assert all(x["keep"] and x["tagged"] for x in items)

    plain = "【筆記】第一則\n內容一\n\n【解法】第二則\n" + F + "c\n// 【筆記】這行在程式碼裡，不是新的一則\n" + F + "\n\n【待解決】為什麼 VAL 寫入任何值都會清零？"
    items = app.split_notes(plain)
    assert [x["type"] for x in items] == ["筆記", "解法", "問題"], [x["type"] for x in items]
    assert "不是新的一則" in items[1]["text"]
    assert app.make_entry("問題", items[2]["text"])["open"] is True, "【待解決】應該標成待解決"
    assert app.make_entry("問題", "【問題】踩過的錯")["open"] is False, "【問題】預設不是待解決"

    one = app.split_notes("沒有標題的一段話\n第二行", "解法")
    assert len(one) == 1 and one[0]["type"] == "解法" and one[0]["keep"]

    mixed = app.split_notes("這是我自己打的說明\n\n【筆記】正式的筆記\n內容")
    assert len(mixed) == 2 and mixed[0]["keep"] is False and mixed[1]["keep"] is True, "標題前的說明文字應該預設不存"
    return "整段回覆、沒有區塊、單則、含說明文字 四種情況"


@check("舊版 App 新增的筆記會自動補上 ID")
def _():
    app = load_app()
    db = {"tasks": [{"id": "T1", "entries": [
        {"time": "2026-01-01 10:00", "type": "問題", "text": "舊版記的問題", "resolved": False},
        {"time": "2026-01-01 10:00", "type": "問題", "text": "舊版記的問題", "resolved": False},
        {"time": "2026-01-01 10:01", "type": "問題", "text": "【卡關】舊版記的卡關", "resolved": False},
        {"id": "keepme", "time": "2026-01-01 10:02", "type": "筆記", "text": "已經有 ID", "resolved": None}]}]}
    a = [e["id"] for e in app.ensure_ids(json.loads(json.dumps(db)))["tasks"][0]["entries"]]
    b = [e["id"] for e in app.ensure_ids(json.loads(json.dumps(db)))["tasks"][0]["entries"]]
    assert a == b, "同一份資料每次補上的 ID 應該相同"
    assert len(set(a)) == 4 and a[3] == "keepme", "ID 重複，或已有的 ID 被改掉"
    ents = app.ensure_ids(db)["tasks"][0]["entries"]
    assert not app.is_open(ents[0]) and app.is_open(ents[2]), "舊版的【問題】不算待解決，【卡關】才算"


@check("App 的讀寫功能（使用暫存的資料副本）")
def _():
    tmp = tempfile.mkdtemp(prefix="tracker2_selftest_")
    try:
        os.makedirs(os.path.join(tmp, "learning"))
        shutil.copy2(os.path.join(ROOT, "learning", "progress.json"), os.path.join(tmp, "learning", "progress.json"))
        app = load_app(tmp)
        assert app.ROOT == tmp, "測試資料夾沒有生效"
        from http.server import ThreadingHTTPServer
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{port}"

        def call(path, body=None):
            data = json.dumps(body).encode("utf-8") if body is not None else None
            req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310
                return json.loads(r.read())

        def refused(path, body):
            """這個操作應該被拒絕（回傳 400）。"""
            import urllib.error
            try:
                call(path, body)
            except urllib.error.HTTPError as e:
                return e.code == 400
            return False
        try:
            st = call("/api/state")
            tid = next(t["id"] for t in st["tasks"] if t.get("plan") == "SPRINT")
            before = len(next(t for t in st["tasks"] if t["id"] == tid)["entries"])
            call("/api/entry", {"id": tid, "type": "筆記", "text": "【筆記】自我檢查\nTODO：自我檢查用的待辦"})
            st = call("/api/state")
            task = next(t for t in st["tasks"] if t["id"] == tid)
            assert len(task["entries"]) == before + 1, "新增筆記沒有存進去"
            todo = next((x for x in st["todos"] if x["text"] == "自我檢查用的待辦"), None)
            assert todo and not todo["done"], "筆記裡的 TODO 沒有被找到"
            call("/api/todo", {"key": todo["key"], "done": True})
            st = call("/api/state")
            assert next(x for x in st["todos"] if x["key"] == todo["key"])["done"], "TODO 勾選沒有存進去"
            pr = call("/api/prompt?id=" + tid + "&kind=start")
            assert pr["kind"] in ("new", "continue") and pr["prompt"], "提示詞 API 沒有回傳內容"
            # 一次貼上多則 → 預覽 → 存入
            F = "`" * 3
            pasted = "\n".join([F + "markdown", "【筆記】自我檢查", "和剛剛那則同標題、內容不同", F, "",
                                F + "markdown", "【問題】自我檢查的錯", "- 原因與解法", F, "",
                                F + "markdown", "【待學】自我檢查的延伸主題", F])
            pv = call("/api/entry/preview", {"id": tid, "type": "筆記", "text": pasted})["items"]
            assert [x["type"] for x in pv] == ["筆記", "問題", "待學"], "預覽的類型不對"
            assert pv[0]["dup"] and not pv[0]["dup"]["same"] and pv[0]["mode"] == "replace", "同標題的筆記沒有被偵測到"
            assert pv[1]["dup"] is None and pv[1]["mode"] == "add"
            n0 = len(next(t for t in call("/api/state")["tasks"] if t["id"] == tid)["entries"])
            call("/api/entry/batch", {"id": tid, "items": [
                {"type": x["type"], "text": x["text"], "mode": x["mode"], "dup_eid": (x["dup"] or {}).get("eid")} for x in pv]})
            st = call("/api/state")
            ents = next(t for t in st["tasks"] if t["id"] == tid)["entries"]
            assert len(ents) == n0 + 2, f"應該新增 2 則、取代 1 則，實際多了 {len(ents) - n0} 則"
            assert all(e.get("id") for t in st["tasks"] for e in t["entries"]), "有筆記沒有 ID"
            replaced = next(e for e in ents if e["id"] == pv[0]["dup"]["eid"])
            assert "內容不同" in replaced["text"] and replaced.get("edited"), "取代沒有生效"
            later = next((x for x in st["later"] if "自我檢查的延伸主題" in x["text"]), None)
            assert later and not later["done"], "待學沒有出現在待學清單"
            call("/api/entry/update", {"id": tid, "eid": later["eid"], "done": True})
            mistake = next(e for e in ents if e["text"].startswith("【問題】自我檢查的錯"))
            assert mistake["open"] is False and mistake["resolved"] is True, "【問題】應該預設為踩過的錯（不是待解決）"
            call("/api/entry/update", {"id": tid, "eid": mistake["id"], "open": True})
            call("/api/entry/update", {"id": tid, "eid": replaced["id"], "text": "【解法】自我檢查改過的內容", "type": "解法"})
            st = call("/api/state")
            ents = next(t for t in st["tasks"] if t["id"] == tid)["entries"]
            assert next(x for x in st["later"] if x["eid"] == later["eid"])["done"], "待學的「已學」沒有存進去"
            assert next(e for e in ents if e["id"] == mistake["id"])["open"] is True, "待解決沒有存進去"
            assert next(e for e in ents if e["id"] == replaced["id"])["type"] == "解法", "編輯後的類型沒有存進去"
            call("/api/entry/delete", {"id": tid, "eid": mistake["id"]})
            ents = next(t for t in call("/api/state")["tasks"] if t["id"] == tid)["entries"]
            assert all(e["id"] != mistake["id"] for e in ents), "刪除沒有生效"
            # 必學範圍勾選
            task = next(t for t in call("/api/state")["tasks"] if t["id"] == tid)
            if task.get("must"):
                mid = task["must"][0]["id"]
                call("/api/must", {"id": tid, "mid": mid, "done": False})
                assert not next(t for t in call("/api/state")["tasks"] if t["id"] == tid)["must"][0]["done"]
                call("/api/must", {"id": tid, "mid": mid, "done": True})
                assert next(t for t in call("/api/state")["tasks"] if t["id"] == tid)["must"][0]["done"], "必學範圍的勾選沒有存進去"
            assert "eta" in call("/api/state")["forecast"], "狀態裡沒有進度推算"
            # 舊計畫（HAL）唯讀；已併入的課題不能開始
            st = call("/api/state")
            hal = next((t["id"] for t in st["tasks"] if t.get("plan") == "HAL"), None)
            if hal:
                assert refused("/api/entry", {"id": hal, "type": "筆記", "text": "不應該存進去"}), "舊計畫應該是唯讀的"
                assert refused("/api/start", {"id": hal}), "舊計畫的課題不應該能開始"
            merged = next((t["id"] for t in st["tasks"] if t.get("priority") == "merged"), None)
            if merged:
                assert refused("/api/start", {"id": merged}), "已併入的課題不應該能開始"
            # 關閉 App 時自動結束進行中的這一次
            fresh = next(t["id"] for t in st["tasks"] if t.get("plan") == "SPRINT" and t["status"] == "未開始" and t.get("priority") != "merged")
            call("/api/start", {"id": fresh})
            app.close_open_session()                      # 剛開始、沒有筆記：視為誤按，不留紀錄
            t2 = next(t for t in call("/api/state")["tasks"] if t["id"] == fresh)
            assert not t2["sessions"] and t2["status"] == "未開始", "誤按開始後關閉，應該還原成未開始"
            call("/api/start", {"id": fresh})
            call("/api/entry", {"id": fresh, "type": "筆記", "text": "【筆記】關閉前記的"})
            app.close_open_session()                      # 有筆記：結束這一次，狀態維持進行中
            t2 = next(t for t in call("/api/state")["tasks"] if t["id"] == fresh)
            assert len(t2["sessions"]) == 1 and t2["sessions"][0]["end"] and t2["status"] == "進行中", "關閉時沒有自動結束這一次"
            # 複習：記錄結果、下次複習日、面試卡、撤銷
            st = call("/api/state")
            assert "review" in st and "nudges" in st, "狀態裡沒有複習資訊"
            rid = next((t["id"] for t in st["tasks"] if t["id"] in st["review"]), None)
            if rid:
                pr = call("/api/prompt?id=" + rid + "&kind=review")
                assert pr["kind"] == "review" and "請這樣考我" in pr["prompt"], "複習提示詞沒有產生"
                assert call("/api/prompt?id=" + rid + "&kind=backfill")["kind"] == "backfill"
                n = st["review"][rid]["count"]
                out = call("/api/review", {"id": rid, "result": "ok", "note": "自我檢查：BSRR 還不穩"})
                assert "下次複習" in out["messages"][0], out
                st = call("/api/state")
                assert st["review"][rid]["count"] == n + 1 and not st["review"][rid]["due"], "複習紀錄沒有存進去，或沒有排下次複習日"
                assert "自我檢查：BSRR 還不穩" in call("/api/prompt?id=" + rid + "&kind=review")["prompt"], "上次還不穩的地方沒有帶進提示詞"
                call("/api/entry", {"id": rid, "type": "筆記", "text": "【面試】自我檢查的面試題\n**一句話答案**\n- 可能的追問：無"})
                card = next(e for t in call("/api/state")["tasks"] if t["id"] == rid for e in t["entries"] if e["text"].startswith("【面試】自我檢查"))
                assert card["type"] == "面試", "【面試】開頭的筆記沒有分類成面試"
                iv = open(os.path.join(tmp, "learning", "INTERVIEW.md"), encoding="utf-8").read()
                assert "#### 自我檢查的面試題" in iv, "面試卡沒有彙整到 INTERVIEW.md"
                page = open(os.path.join(tmp, "learning", "notes", rid + ".md"), encoding="utf-8").read()
                assert "## 複習紀錄" in page and "部分卡住" in page, "筆記頁沒有複習紀錄"
                assert refused("/api/review", {"id": rid, "result": "很好"}), "不正確的複習結果應該被拒絕"
                call("/api/review", {"id": rid, "undo": True})
                assert call("/api/state")["review"][rid]["count"] == n, "撤銷複習紀錄沒有生效"
            assert refused("/api/review", {"id": fresh, "result": "good"}), "還沒完成的課題不應該能記錄複習"
            if hal:
                assert refused("/api/review", {"id": hal, "result": "good"}), "舊計畫不應該能記錄複習"
            # 完成課題：排入複習並帶出複習提示詞（暫存資料夾不是 Git repo 才測，避免真的 commit）
            if not app.git_info().get("is_repo"):
                done = call("/api/finish", {"id": fresh, "done": True, "summary": ""})
                assert done.get("prompt_kind") == "review" and done.get("prompt_task") == fresh, "完成技術課題後應該帶出複習提示詞"
                assert any("已排入複習" in m for m in done["messages"]), done["messages"]
                assert fresh in call("/api/state")["review"], "完成的課題沒有排入複習"
            assert os.path.isfile(os.path.join(tmp, "learning", "INTERVIEW.md")), "面試準備頁沒有產生"
            q = open(os.path.join(tmp, "learning", "QUESTIONS.md"), encoding="utf-8").read()
            assert "## ❓ 待解決" in q and "## 踩過的錯" in q, "QUESTIONS.md 的格式不對"
            assert os.path.isfile(os.path.join(tmp, "learning", "notes", tid + ".md")), "筆記頁沒有產生"
            assert os.path.isfile(os.path.join(tmp, "learning", "README.md")), "進度總覽沒有產生"
        finally:
            srv.shutdown()
            srv.server_close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    print(f"STM32 學習進度 App（新版）自我檢查　Python {sys.version.split()[0]}\n")
    failed = 0
    for ok, name, note in RESULTS:
        mark = "[通過]" if ok else ("[略過]" if ok is None else "[失敗]")
        failed += ok is False
        print(f"{mark} {name}" + (f"：{note}" if note else ""))
    print("\n" + ("全部通過。" if not failed else f"有 {failed} 項失敗，請先修正再使用新版 App。"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
