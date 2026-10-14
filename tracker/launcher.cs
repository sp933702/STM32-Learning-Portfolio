// STM32 學習進度 App 的啟動程式
// 以 pythonw（沒有終端機視窗的 Python）在背景執行 tracker\app.py，然後自己結束。
// App 會在瀏覽器分頁全部關閉後自動結束，不會留下背景程式。
// 用 tracker\build_exe.bat 編譯（Windows 內建的 .NET Framework csc.exe，不需安裝任何東西）。
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

[assembly: AssemblyTitle("STM32 學習進度")]
[assembly: AssemblyProduct("STM32 學習進度")]
[assembly: AssemblyVersion("1.0.0.0")]

static class Launcher
{
    const string Title = "STM32 學習進度";

    [STAThread]
    static int Main()
    {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string app = Path.Combine(Path.Combine(root, "tracker"), "app.py");
        if (!File.Exists(app))
        {
            MessageBox.Show("找不到 tracker\\app.py。\n\n請把這個 exe 放在 repo 根目錄（和 tracker 資料夾同一層）。\n目前位置：" + root,
                            Title, MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }

        string pyw = FindPyLauncher();
        if (pyw != null && Run(pyw, "-3 \"" + app + "\"", root)) return 0;

        string pythonw = FindPythonw();
        if (pythonw != null && Run(pythonw, "\"" + app + "\"", root)) return 0;

        MessageBox.Show("找不到 Python（pythonw.exe）。\n\n請到 python.org 安裝 Python 3，安裝時勾選「Add python.exe to PATH」。",
                        Title, MessageBoxButtons.OK, MessageBoxIcon.Error);
        return 2;
    }

    static bool Run(string exe, string args, string dir)
    {
        try
        {
            ProcessStartInfo psi = new ProcessStartInfo(exe, args);
            psi.WorkingDirectory = dir;
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            Process.Start(psi);
            return true;
        }
        catch (Exception)
        {
            return false;
        }
    }

    // py 啟動器的無視窗版本 pyw.exe
    static string FindPyLauncher()
    {
        string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string win = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
        string p = SearchPath("pyw.exe");
        if (p != null) return p;
        foreach (string c in new string[] {
                     Path.Combine(win, "pyw.exe"),
                     Path.Combine(local, @"Programs\Python\Launcher\pyw.exe") })
            if (File.Exists(c)) return c;
        return null;
    }

    static string FindPythonw()
    {
        string p = SearchPath("pythonw.exe");
        if (p != null) return p;
        string py = SearchPath("python.exe");
        if (py != null)
        {
            string w = Path.Combine(Path.GetDirectoryName(py), "pythonw.exe");
            if (File.Exists(w)) return w;
        }
        string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string pf = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
        foreach (string baseDir in new string[] { Path.Combine(local, @"Programs\Python"), pf })
        {
            if (!Directory.Exists(baseDir)) continue;
            string[] dirs;
            try { dirs = Directory.GetDirectories(baseDir, "Python3*"); }
            catch (Exception) { continue; }
            Array.Sort(dirs);
            Array.Reverse(dirs);            // 新版本優先
            foreach (string d in dirs)
            {
                string w = Path.Combine(d, "pythonw.exe");
                if (File.Exists(w)) return w;
            }
        }
        return null;
    }

    static string SearchPath(string name)
    {
        string path = Environment.GetEnvironmentVariable("PATH") ?? "";
        foreach (string raw in path.Split(';'))
        {
            string d = raw.Trim().Trim('"');
            if (d.Length == 0) continue;
            if (d.IndexOf("WindowsApps", StringComparison.OrdinalIgnoreCase) >= 0) continue; // Microsoft Store 的假 python
            try
            {
                string f = Path.Combine(d, name);
                if (File.Exists(f)) return f;
            }
            catch (Exception) { }
        }
        return null;
    }
}
