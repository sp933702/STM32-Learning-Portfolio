@echo off
chcp 65001 >NUL
rem ===== 一次性建置：產生 repo 根目錄的 STM32Tracker2.exe（新版 App 的啟動檔）=====
rem 使用 Windows 內建 .NET Framework 的 csc.exe，不需要網路或安裝任何東西。
rem 舊版的 STM32Tracker.exe 與 tracker 資料夾不會被更動。
rem 只有修改 launcher.cs 或 app.ico 時才需要重新執行。
cd /d "%~dp0"

set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%CSC%" (
  echo [錯誤] 找不到 csc.exe（.NET Framework 4）。
  pause
  exit /b 1
)

echo 正在編譯 STM32Tracker2.exe ...
"%CSC%" /nologo /target:winexe /optimize+ /codepage:65001 /win32icon:app.ico /reference:System.Windows.Forms.dll /out:..\STM32Tracker2.exe launcher.cs
if errorlevel 1 (
  echo [錯誤] 編譯失敗，請把上面的訊息貼給 Claude。
  pause
  exit /b 1
)
echo 編譯完成：%~dp0..\STM32Tracker2.exe
echo.
echo 完成！之後雙擊 STM32Tracker2.exe 開啟新版 App（綠色圖示）。
echo 舊版 STM32Tracker.exe（藍色圖示）仍然可以使用，兩者共用同一份筆記，但不要同時開啟。
echo 這個視窗 5 秒後關閉，並幫你開啟新版 App。
cd ..
start "" "STM32Tracker2.exe"
timeout /t 5 >NUL
