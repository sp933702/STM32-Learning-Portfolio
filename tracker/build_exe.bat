@echo off
chcp 65001 >NUL
rem ===== 一次性建置：產生 repo 根目錄的 STM32Tracker.exe =====
rem 使用 Windows 內建 .NET Framework 的 csc.exe，不需要網路或安裝任何東西。
rem 只有修改 launcher.cs 或 app.ico 時才需要重新執行。
cd /d "%~dp0"

set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%CSC%" (
  echo [錯誤] 找不到 csc.exe（.NET Framework 4）。
  pause
  exit /b 1
)

echo 正在編譯 STM32Tracker.exe ...
"%CSC%" /nologo /target:winexe /optimize+ /codepage:65001 /win32icon:app.ico /reference:System.Windows.Forms.dll /out:..\STM32Tracker.exe launcher.cs
if errorlevel 1 (
  echo [錯誤] 編譯失敗，請把上面的訊息貼給 Claude。
  pause
  exit /b 1
)
echo 編譯完成：%~dp0..\STM32Tracker.exe

cd ..
rem 移除舊的 .bat 啟動方式
if exist "*App.bat" del /q "*App.bat"

echo.
echo 正在 commit 並 push 到 GitHub（讓另一台電腦也有 exe）...
git add STM32Tracker.exe tracker .gitignore README.md CLAUDE.md
git add -u
git commit -q -m "改用 STM32Tracker.exe 啟動 App（無終端機視窗，關閉分頁自動結束）"
git push -q
echo.
echo 完成！之後雙擊 STM32Tracker.exe 開啟 App（可以對它按右鍵建立桌面捷徑）。
echo 這個視窗 5 秒後關閉，並幫你開啟 App。
start "" "STM32Tracker.exe"
timeout /t 5 >NUL
