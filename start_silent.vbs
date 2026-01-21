Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "start_pusher.bat" & Chr(34), 0
Set WshShell = Nothing