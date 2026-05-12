Set objShell = CreateObject("WScript.Shell")
objShell.Run "api.exe", 0, False
WScript.Sleep 3000
objShell.Run "start http://127.0.0.1:8000", 1
WScript.Sleep 500
objShell.Run "start http://127.0.0.1:8000/qr", 1