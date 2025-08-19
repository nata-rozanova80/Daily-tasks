Set WshShell = WScript.CreateObject("WScript.Shell")
DesktopPath = WshShell.SpecialFolders("Desktop")
Set fso = CreateObject("Scripting.FileSystemObject")

exePath = fso.GetAbsolutePathName("dist\ChecklistNotes\ChecklistNotes.exe")
workDir = fso.GetParentFolderName(exePath)

Set link = WshShell.CreateShortcut(DesktopPath & "\Checklist Notes.lnk")
link.TargetPath = exePath
link.WorkingDirectory = workDir
link.IconLocation = exePath & ",0"
link.Description = "Checklist Notes — запуск"
link.Save

WScript.Echo "Ярлык создан на рабочем столе."
