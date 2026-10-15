# SPRINT-W01-S01：C 語言驗收

- 狀態：**已完成**
- 週次：W01　主題：C 驗收
- 對應原任務（HAL 版）：Pi Day1–4
- 進行次數：2 次（最近一次：2026-10-15）
- 完成日期：2026-10-15
- 程式碼：[projects/SPRINT-W01-S01](../../projects/SPRINT-W01-S01)

## 任務內容

不看筆記完成 10 題：set/clear/toggle/檢查 bit、bit-field 先清再寫、volatile 三種情境、const 指標兩種寫法、static 三種用法、struct sizeof 與 padding、大小端判斷、函式指標陣列做命令表

## 完成標準

10 題都能編譯執行並口頭解釋；答錯的題目記在筆記欄

## 問題與筆記

### [筆記] 2026-10-15 09:45

sizeof 的結果型別是 size_t，printf 要用 %zu

### [問題] 2026-10-15 09:54 ✅ 已解決

預測題判斷錯了 long long，理由寫成「匯流排寬度」

### [筆記] 2026-10-15 09:54

型別大小由 Data Model／ABI 決定；ILP32、LP64、LLP64 三者的差異

### [解法] 2026-10-15 09:54

韌體程式一律使用 <stdint.h> 的固定寬度型別

### [筆記] 2026-10-15 10:30

【SPRINT-W01-S01／Q00】Data Model 與 ABI

■ 核心觀念
・型別大小由「編譯目標的 ABI（含資料模型）」決定，C 標準只規定最小寬度
・與電腦是幾位元、匯流排寬度無關
・同樣是 64 位元，WSL 的 long＝8，Windows 的 long＝4

■ 命名規則
I＝int　L＝long　LL＝long long　P＝指標　數字＝列出的型別都是這個位元數

■ 三種資料模型（單位 bytes：int / long / long long / 指標）
・ILP32：4 / 4 / 8 / 4 → STM32、32 位元 x86／ARM Linux
・LP64 ：4 / 8 / 8 / 8 → 64 位元 Linux（WSL）、macOS
・LLP64：4 / 4 / 8 / 8 → 64 位元 Windows（MSVC、MinGW）
※ char＝1、short＝2，三種模型都一樣

■ C 標準最小寬度
char 8 bit ／ short、int 16 bit ／ long 32 bit ／ long long 64 bit
順序：char ≤ short ≤ int ≤ long ≤ long long

■ 固定寬度型別 <stdint.h>（括號內為 STM32 上的大小）
・uint8_t / uint16_t / uint32_t / uint64_t（1/2/4/8）
・uintptr_t：可存放指標數值的整數（4）
・size_t：sizeof 的結果型別，printf 用 %zu（4）
→ 暫存器一律用 uint32_t，不用 int／long

■ ABI 與 AAPCS
・ABI：讓不同來源的機器碼依同一套規則合作
　（型別大小與對齊、呼叫慣例、目的檔格式）
・AAPCS：ARM 的函式呼叫標準，屬於 ABI 的一部分
　（AAPCS32 用於 STM32，AAPCS64 用於 64 位元 ARM）

■ AAPCS32 重點（面試常考）
・參數：前 4 個放 R0～R3，其餘放堆疊
・回傳：R0（64 位元用 R0＋R1）
・呼叫者保存：R0～R3、R12；被呼叫者保存：R4～R11
・堆疊在函式呼叫邊界要 8-byte 對齊
・自然對齊：long long、double 要 8-byte 對齊（會影響 struct sizeof）

■ 平台陷阱
・單寫 char：x86 預設 signed，ARM 預設 unsigned → 要用 int8_t／uint8_t
・STM32F103 和 x86 都是 Little-endian

■ 我答錯的地方
・預測題誤判 long long 會變小
　→ 原因：C 標準規定 long long 至少 64 bit
・誤以為型別大小由匯流排寬度決定
　→ 正確：由 ABI／資料模型決定

■ 驗收答案
・q00 在 STM32 上：1 2 4 4 8 4，與 WSL 不同的是 long 和指標
