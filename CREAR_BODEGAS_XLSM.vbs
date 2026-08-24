'' CREAR_BODEGAS_XLSM.vbs
'' Crea datos-bodegas.xlsm importando modBodegas.bas.
'' ORDEN CRITICO: setear AccessVBOM ANTES de abrir Excel.

Option Explicit

Dim basPath, xlsmPath, fso, reg, xl, wb, wsMenu, tieneMenu, comp

Dim scriptDir
scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
basPath  = scriptDir & "modBodegas.bas"
xlsmPath = scriptDir & "datos-bodegas.xlsm"

Set fso = CreateObject("Scripting.FileSystemObject")
If Not fso.FileExists(basPath) Then
    WScript.Echo "[ERROR] No encontrado: " & basPath
    WScript.Quit 1
End If

'' 1. Habilitar AccessVBOM ANTES de abrir Excel
Set reg = CreateObject("WScript.Shell")
reg.RegWrite "HKCU\Software\Microsoft\Office\16.0\Excel\Security\AccessVBOM", 1, "REG_DWORD"
WScript.Echo "AccessVBOM=1 habilitado"
WScript.Sleep 500

'' 2. Abrir Excel
Set xl = CreateObject("Excel.Application")
xl.Visible = False
xl.DisplayAlerts = False

'' 3. Abrir XLSM existente o crear nuevo
If fso.FileExists(xlsmPath) Then
    Set wb = xl.Workbooks.Open(xlsmPath)
    WScript.Echo "XLSM existente abierto."
Else
    Set wb = xl.Workbooks.Add()
    WScript.Echo "Nuevo workbook creado."
End If

'' 4. Hoja MENU
tieneMenu = False
On Error Resume Next
tieneMenu = (wb.Worksheets("MENU").Name = "MENU")
On Error GoTo 0
If Not tieneMenu Then
    Set wsMenu = wb.Worksheets.Add(wb.Worksheets(1))
    wsMenu.Name = "MENU"
Else
    Set wsMenu = wb.Worksheets("MENU")
End If
wsMenu.Cells(1,1).Value = "BODEGAS GESTION - datos-bodegas.xlsm"
wsMenu.Cells(2,1).Value = "Generado: " & Now()
wsMenu.Cells(3,1).Value = "Macro: modBodegas.BajarTodoBat"

'' 5. Eliminar modulo viejo si existe
For Each comp In wb.VBProject.VBComponents
    If comp.Name = "modBodegas" Then
        wb.VBProject.VBComponents.Remove comp
        WScript.Echo "modBodegas anterior removido."
        Exit For
    End If
Next

'' 6. Importar modBodegas.bas
On Error Resume Next
wb.VBProject.VBComponents.Import basPath
If Err.Number <> 0 Then
    WScript.Echo "[ERROR] Import fallo: " & Err.Description & " (" & Err.Number & ")"
    WScript.Echo "Asegurate que 'Confiar en acceso al modelo VBA' este habilitado en Excel."
    wb.Close False
    xl.Quit
    reg.RegWrite "HKCU\Software\Microsoft\Office\16.0\Excel\Security\AccessVBOM", 0, "REG_DWORD"
    WScript.Quit 1
End If
On Error GoTo 0
WScript.Echo "modBodegas importado OK."

'' 7. Guardar como xlsm (52 = xlOpenXMLWorkbookMacroEnabled)
xl.DisplayAlerts = False
wb.SaveAs xlsmPath, 52
wb.Close False
xl.Quit

'' 8. Restaurar AccessVBOM
reg.RegWrite "HKCU\Software\Microsoft\Office\16.0\Excel\Security\AccessVBOM", 0, "REG_DWORD"
WScript.Echo "AccessVBOM restaurado a 0"
WScript.Echo "[OK] datos-bodegas.xlsm listo en: " & xlsmPath
