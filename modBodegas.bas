Attribute VB_Name = "modBodegas"
Option Explicit

' ============================================================
' modBodegas.bas  V1.0  2026-08-23
' Descarga stock + movimientos de bodegas de gestion interna
' de todas las sucursales desde SQL Server Foviedo.
'
' Fuente primaria: Excel XLSM + ADODB (headless via VBScript)
' Fuente fallback: generar_bodegas_gestion.py (pyodbc)
'
' Credenciales: E:\ferreteria-oviedo\credenciales_db.ini ([DB])
' Sin constantes hardcodeadas. LeerIni usa FSO (maneja LF-only).
'
' Hojas generadas (una por grupo):
'   BOD_EM   El Manzano (GEM/MEM/RCE/IEM/TEM/EEM)
'   BOD_SV   San Vicente (GSV/MSV/RSV/ISV/TSV/CSV/DSV/ESV)
'   BOD_LC   Las Cabras (GLC/MLC/RLC/ILC/TLC/CLC/GFL/ELC/VLC)
'   BOD_LT   Litueche (GLE/MLE/ILE/TLE/CLT/DLT/ELE)
'   BOD_IR   Isabel Riquelme otras (CAL/SER/WEB/GO/GAR/IIR/BMC/RST/HEL/EIR)
'   BOD_CD   Compartidas/CD (CD/XCD/GCD/ICD/MCD/RCD/TCD/BDP/REM/MKT)
' ============================================================

Private Const INI_PATH As String = "E:\ferreteria-oviedo\credenciales_db.ini"

' --- CREDENCIALES (FSO — maneja LF-only sin cortar lineas) -------------------
Private Function LeerIni(clave As String) As String
    LeerIni = ""
    Dim fso As Object, ts As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    If Not fso.FileExists(INI_PATH) Then Exit Function
    On Error GoTo LeerIniFin
    Set ts = fso.OpenTextFile(INI_PATH, 1, False)
    Dim linea As String, enSeccion As Boolean: enSeccion = False
    Dim sep As Integer, k As String, v As String
    Do While Not ts.AtEndOfStream
        linea = Trim(ts.ReadLine())
        If linea = "[DB]" Then
            enSeccion = True
        ElseIf Len(linea) > 0 And Left(linea, 1) = "[" Then
            enSeccion = False
        ElseIf enSeccion Then
            sep = InStr(linea, "=")
            If sep > 0 Then
                k = Trim(Left(linea, sep - 1)): v = Trim(Mid(linea, sep + 1))
                If LCase(k) = LCase(clave) Then
                    LeerIni = v: ts.Close: Exit Function
                End If
            End If
        End If
    Loop
LeerIniFin:
    On Error Resume Next
    If Not ts Is Nothing Then ts.Close
    On Error GoTo 0
End Function

Private Function CadenaConexion() As String
    ' dbmssocn = TCP/IP forzado; evita Shared Memory que falla en headless Excel
    CadenaConexion = "Provider=SQLOLEDB.1;Persist Security Info=False;Network Library=dbmssocn;" & _
        "User ID=" & LeerIni("user") & ";Pwd=" & LeerIni("password") & _
        ";Initial Catalog=" & LeerIni("database") & ";Data Source=" & LeerIni("server") & _
        ";Connect Timeout=30;"
End Function

Private Sub EscribirLog(msg As String)
    Dim wsM As Worksheet
    On Error Resume Next
    Set wsM = ThisWorkbook.Sheets("LOG"): On Error GoTo 0
    If wsM Is Nothing Then Exit Sub
    Dim sig As Long: sig = wsM.Cells(wsM.Rows.Count, 1).End(xlUp).Row + 1
    wsM.Cells(sig, 1).Value = Now()
    wsM.Cells(sig, 2).Value = msg
End Sub

' --- HELPERS -----------------------------------------------------------------
Private Sub PrepararHoja(nombreHoja As String)
    Dim ws As Worksheet
    On Error Resume Next: Set ws = ThisWorkbook.Worksheets(nombreHoja): On Error GoTo 0
    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = nombreHoja
    End If
    ws.Cells.ClearContents
    ' Cabeceras
    Dim cols As Variant
    cols = Array("SUCURSAL_TAB", "IDBODEGA", "BODEGA", "TIPO_DOC", "FOLIO", _
                 "CODIGO_TECNICO", "DESCRIPCION", _
                 "STOCK_DISPONIBLE", "STOCK_FISICO", "CANTIDAD_DOC", _
                 "FECHA_EMISION", "OBSERVACION_IMPRESA", "COSTO_PROMEDIO", _
                 "FECHA_REGISTRO_SISTEMA", "USUARIO", "ESTACION_PC", _
                 "HIPERFAMILIA", "FAMILIA", "SUBFAMILIA", "MARCA")
    Dim i As Integer
    For i = 0 To UBound(cols)
        ws.Cells(1, i + 1).Value = cols(i)
        ws.Cells(1, i + 1).Font.Bold = True
        ws.Cells(1, i + 1).Interior.ColorIndex = 15
    Next i
End Sub

Private Function AbrirConexion() As Object
    Dim cn As Object
    Set cn = CreateObject("ADODB.Connection")
    On Error Resume Next
    cn.Open CadenaConexion()
    Dim e As Long: e = Err.Number
    Dim em As String: em = Err.Description
    On Error GoTo 0
    If cn.State = 0 Then
        EscribirLog "[ERROR] Conexion fallida: " & e & " - " & em
        Set AbrirConexion = Nothing
    Else
        Set AbrirConexion = cn
    End If
End Function

' ─── QUERY SQL (identica a generar_bodegas_gestion.py) ──────────────────────
' Parametros: idbodega x2, idsucursal
Private Function SQLBodega() As String
    Dim s1 As String, s2 As String, s3 As String
    s1 = "WITH ENTRADAS AS (" & _
         " SELECT E.IDBODEGA,E.CODIGO_TECNICO,E.IDSUCURSAL,E.IDDOCUMENTO,E.IDNUMERO," & _
         "  E.NUMERO,E.FECHA_EMISION,E.CANTIDAD,MD.DOC" & _
         " FROM Foviedo.dbo.M_DOCUMENTOS_DETALLE E" & _
         " INNER JOIN Foviedo.dbo.M_DOCUMENTOS MD ON MD.IDDOCUMENTO=E.IDDOCUMENTO" & _
         " WHERE E.IDBODEGA=?" & _
         " AND MD.DOC IN ('GRC','GRT','GME','GIB','Gdc','GBR','GRP','GRI','GRN','GIN','GDC','GDV','GII','GTS'))" & _
         " SELECT DISTINCT D.SIMBOLO_BODEGA,N.DOC,N.NUMERO,A.CODIGO_TECNICO,B.DESCRIPCION," & _
         " CAST(ISNULL(A.ST_DISPONIBLE,0) AS DECIMAL(18,2))," & _
         " CAST(ISNULL(A.ST_FISICO,0) AS DECIMAL(18,2))," & _
         " CAST(ISNULL(N.CANTIDAD,0) AS DECIMAL(18,2))," & _
         " N.FECHA_EMISION," & _
         " ISNULL(G.OBSERVACION_IMPRESA,'')," & _
         " CAST(ISNULL(B.COSTO_PROMEDIO,0) AS DECIMAL(18,2))," & _
         " ISNULL(CONVERT(NVARCHAR(20),ENC.FECHA_REGISTRO,120),'')," & _
         " ISNULL(ENC.IDRESPONZABLE,ISNULL(ENC.AUTORIZADO_FIRMA,ISNULL(ENC.IDVENDEDOR,'')))," & _
         " ISNULL(ENC.ESTACION,'')," & _
         " ISNULL(HF.HIPERFAMILIA,''),ISNULL(FA.FAMILIA,'')," & _
         " ISNULL(SF.SUBFAMILIA,''),ISNULL(MA.MARCA,'')"
    s2 = " FROM Foviedo.dbo.R_STOCK_PRODUCTOS A" & _
         " INNER JOIN Foviedo.dbo.M_PRODUCTOS B ON B.CODIGO_TECNICO=A.CODIGO_TECNICO" & _
         " INNER JOIN Foviedo.dbo.P_BODEGAS D ON A.IDBODEGA=D.IDBODEGA" & _
         " LEFT JOIN Foviedo.dbo.P_HIPERFAMILIAS HF ON HF.IDHIPERFAMILIA=B.IDHIPERFAMILIA" & _
         " LEFT JOIN Foviedo.dbo.P_FAMILIAS FA ON FA.IDFAMILIA=B.IDFAMILIA AND FA.IDHIPERFAMILIA=B.IDHIPERFAMILIA" & _
         " LEFT JOIN Foviedo.dbo.P_SUBFAMILIAS SF ON SF.IDSUBFAMILIA=B.IDSUBFAMILIA AND SF.IDFAMILIA=B.IDFAMILIA AND SF.IDHIPERFAMILIA=B.IDHIPERFAMILIA" & _
         " LEFT JOIN Foviedo.dbo.P_MARCAS MA ON MA.IDMARCA=B.IDMARCA"
    s3 = " INNER JOIN ENTRADAS N ON N.IDBODEGA=A.IDBODEGA AND N.CODIGO_TECNICO=A.CODIGO_TECNICO" & _
         " LEFT JOIN Foviedo.dbo.M_Documentos_Encabezado_Observacion G" & _
         "   ON G.IDDOCUMENTO=N.IDDOCUMENTO AND G.IDNUMERO=N.IDNUMERO" & _
         " LEFT JOIN Foviedo.dbo.M_DOCUMENTOS_ENCABEZADO ENC" & _
         "   ON ENC.IDDOCUMENTO=N.IDDOCUMENTO AND ENC.IDNUMERO=N.IDNUMERO" & _
         " WHERE A.IDBODEGA=? AND A.IDSUCURSAL=? AND ISNULL(A.ST_FISICO,0)<>0" & _
         " ORDER BY N.FECHA_EMISION DESC"
    SQLBodega = s1 & s2 & s3
End Function

' Descarga una bodega y agrega filas a la hoja (debajo de lo ya escrito)
Private Sub DescargarBodega(cn As Object, ws As Worksheet, _
                             sucursalTab As String, idbodega As Long, _
                             idsucursal As String, _
                             ByRef filaActual As Long)
    Dim cmd As Object, rs As Object
    Set cmd = CreateObject("ADODB.Command")
    cmd.ActiveConnection = cn
    cmd.CommandTimeout = 0
    cmd.CommandText = SQLBodega()
    cmd.CommandType = 1  ' adCmdText

    ' Parametros ADODB (3 params: idbodega x2, idsucursal)
    cmd.Parameters.Append cmd.CreateParameter("p1", 3, 1, , idbodega)   ' adInteger, adParamInput
    cmd.Parameters.Append cmd.CreateParameter("p2", 3, 1, , idbodega)
    cmd.Parameters.Append cmd.CreateParameter("p3", 200, 1, 2, idsucursal) ' adVarChar

    Set rs = CreateObject("ADODB.Recordset")
    On Error Resume Next
    rs.Open cmd
    Dim rsErr As Long: rsErr = Err.Number
    Dim rsMsg As String: rsMsg = Err.Description
    On Error GoTo 0

    If rsErr <> 0 Then
        EscribirLog "[ERROR] Bodega idbodega=" & idbodega & " suc=" & idsucursal & ": " & rsErr & " - " & rsMsg
        Exit Sub
    End If

    Dim n As Long: n = 0
    Do While Not rs.EOF
        ws.Cells(filaActual, 1).Value = sucursalTab
        ws.Cells(filaActual, 2).Value = idbodega
        ' Columnas 3..20 desde el recordset (18 campos)
        Dim c As Integer
        For c = 0 To 17
            Dim v As Variant: v = rs.Fields(c).Value
            If IsNull(v) Then v = ""
            ws.Cells(filaActual, c + 3).Value = v
        Next c
        filaActual = filaActual + 1
        n = n + 1
        rs.MoveNext
    Loop
    rs.Close

    EscribirLog "[OK] idbodega=" & idbodega & " suc=" & idsucursal & " filas=" & n
    Application.StatusBar = sucursalTab & " / idbodega=" & idbodega & " → " & n & " filas"
End Sub

' ─── GRUPOS DE BODEGAS (mismos IDs que generar_bodegas_gestion.py) ───────────
' Formato: (idbodega, idsucursal_real)
Private Sub CargarGrupoEM(cn As Object)
    PrepararHoja "BOD_EM"
    Dim ws As Worksheet: Set ws = ThisWorkbook.Sheets("BOD_EM")
    Dim f As Long: f = 2
    Dim bods(5, 1) As Variant
    bods(0, 0) = 28: bods(0, 1) = "04"   ' GEM
    bods(1, 0) = 29: bods(1, 1) = "04"   ' MEM
    bods(2, 0) = 55: bods(2, 1) = "04"   ' RCE
    bods(3, 0) = 72: bods(3, 1) = "04"   ' IEM
    bods(4, 0) = 46: bods(4, 1) = "04"   ' TEM
    bods(5, 0) = 83: bods(5, 1) = "04"   ' EEM
    Dim i As Integer
    For i = 0 To 5: DescargarBodega cn, ws, "04", bods(i, 0), bods(i, 1), f: Next i
End Sub

Private Sub CargarGrupoSV(cn As Object)
    PrepararHoja "BOD_SV"
    Dim ws As Worksheet: Set ws = ThisWorkbook.Sheets("BOD_SV")
    Dim f As Long: f = 2
    Dim bods(8, 1) As Variant
    bods(0, 0) = 41: bods(0, 1) = "05"
    bods(1, 0) = 42: bods(1, 1) = "05"
    bods(2, 0) = 56: bods(2, 1) = "05"
    bods(3, 0) = 70: bods(3, 1) = "05"
    bods(4, 0) = 45: bods(4, 1) = "05"
    bods(5, 0) = 44: bods(5, 1) = "05"
    bods(6, 0) = 88: bods(6, 1) = "14"   ' DSV vive bajo suc=14
    bods(7, 0) = 95: bods(7, 1) = "05"
    bods(8, 0) = 43: bods(8, 1) = "05"
    Dim i As Integer
    For i = 0 To 8: DescargarBodega cn, ws, "05", bods(i, 0), bods(i, 1), f: Next i
End Sub

Private Sub CargarGrupoLC(cn As Object)
    PrepararHoja "BOD_LC"
    Dim ws As Worksheet: Set ws = ThisWorkbook.Sheets("BOD_LC")
    Dim f As Long: f = 2
    Dim bods(8, 1) As Variant
    bods(0, 0) = 37: bods(0, 1) = "06"
    bods(1, 0) = 38: bods(1, 1) = "06"
    bods(2, 0) = 57: bods(2, 1) = "06"
    bods(3, 0) = 71: bods(3, 1) = "06"
    bods(4, 0) = 16: bods(4, 1) = "06"
    bods(5, 0) = 35: bods(5, 1) = "06"
    bods(6, 0) = 91: bods(6, 1) = "06"
    bods(7, 0) = 96: bods(7, 1) = "06"
    bods(8, 0) = 97: bods(8, 1) = "06"
    Dim i As Integer
    For i = 0 To 8: DescargarBodega cn, ws, "06", bods(i, 0), bods(i, 1), f: Next i
End Sub

Private Sub CargarGrupoLT(cn As Object)
    PrepararHoja "BOD_LT"
    Dim ws As Worksheet: Set ws = ThisWorkbook.Sheets("BOD_LT")
    Dim f As Long: f = 2
    Dim bods(6, 1) As Variant
    bods(0, 0) = 63: bods(0, 1) = "11"
    bods(1, 0) = 76: bods(1, 1) = "11"
    bods(2, 0) = 74: bods(2, 1) = "11"
    bods(3, 0) = 59: bods(3, 1) = "11"
    bods(4, 0) = 78: bods(4, 1) = "11"
    bods(5, 0) = 79: bods(5, 1) = "09"   ' DLT vive bajo suc=09
    bods(6, 0) = 64: bods(6, 1) = "11"
    Dim i As Integer
    For i = 0 To 6: DescargarBodega cn, ws, "11", bods(i, 0), bods(i, 1), f: Next i
End Sub

Private Sub CargarGrupoIR(cn As Object)
    PrepararHoja "BOD_IR"
    Dim ws As Worksheet: Set ws = ThisWorkbook.Sheets("BOD_IR")
    Dim f As Long: f = 2
    Dim bods(9, 1) As Variant
    bods(0, 0) = 5:  bods(0, 1) = "02"   ' CAL
    bods(1, 0) = 6:  bods(1, 1) = "02"   ' SER
    bods(2, 0) = 25: bods(2, 1) = "02"   ' WEB
    bods(3, 0) = 30: bods(3, 1) = "02"   ' GO
    bods(4, 0) = 53: bods(4, 1) = "02"   ' GAR
    bods(5, 0) = 69: bods(5, 1) = "02"   ' IIR
    bods(6, 0) = 77: bods(6, 1) = "02"   ' BMC
    bods(7, 0) = 92: bods(7, 1) = "02"   ' RST
    bods(8, 0) = 99: bods(8, 1) = "02"   ' HEL
    bods(9, 0) = 85: bods(9, 1) = "02"   ' EIR
    Dim i As Integer
    For i = 0 To 9: DescargarBodega cn, ws, "02", bods(i, 0), bods(i, 1), f: Next i
End Sub

Private Sub CargarGrupoCD(cn As Object)
    PrepararHoja "BOD_CD"
    Dim ws As Worksheet: Set ws = ThisWorkbook.Sheets("BOD_CD")
    Dim f As Long: f = 2
    Dim bods(9, 1) As Variant
    bods(0, 0) = 23: bods(0, 1) = "08"   ' CD
    bods(1, 0) = 7:  bods(1, 1) = "08"   ' XCD
    bods(2, 0) = 27: bods(2, 1) = "08"   ' GCD
    bods(3, 0) = 73: bods(3, 1) = "08"   ' ICD
    bods(4, 0) = 26: bods(4, 1) = "08"   ' MCD
    bods(5, 0) = 54: bods(5, 1) = "08"   ' RCD
    bods(6, 0) = 67: bods(6, 1) = "08"   ' TCD
    bods(7, 0) = 98: bods(7, 1) = "09"   ' BDP
    bods(8, 0) = 84: bods(8, 1) = "01"   ' REM
    bods(9, 0) = 36: bods(9, 1) = "01"   ' MKT
    Dim i As Integer
    For i = 0 To 9: DescargarBodega cn, ws, "COMPARTIDAS", bods(i, 0), bods(i, 1), f: Next i
End Sub

' ─── BAJAR TODO (llamado por VBScript headless desde el bat) ─────────────────
Public Sub BajarTodoBat()
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    Application.StatusBar = "Bodegas Gestion: iniciando " & Format(Now(), "HH:MM:SS")

    ' Hoja LOG
    Dim wsLog As Worksheet
    On Error Resume Next: Set wsLog = ThisWorkbook.Sheets("LOG"): On Error GoTo 0
    If wsLog Is Nothing Then
        Set wsLog = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(1))
        wsLog.Name = "LOG"
    End If
    wsLog.Cells.ClearContents
    wsLog.Cells(1, 1).Value = "TIMESTAMP"
    wsLog.Cells(1, 2).Value = "MENSAJE"

    EscribirLog "INICIO " & Format(Now(), "YYYY-MM-DD HH:MM:SS")

    Dim cn As Object
    Set cn = AbrirConexion()
    If cn Is Nothing Then
        EscribirLog "[FATAL] No se pudo conectar a SQL Server. Verificar VPN y credenciales_db.ini."
        Application.ScreenUpdating = True
        Application.Calculation = xlCalculationAutomatic
        Application.StatusBar = False
        ThisWorkbook.Save
        Exit Sub
    End If
    EscribirLog "Conexion SQL OK"

    CargarGrupoEM cn
    CargarGrupoSV cn
    CargarGrupoLC cn
    CargarGrupoLT cn
    CargarGrupoIR cn
    CargarGrupoCD cn

    On Error Resume Next: cn.Close: On Error GoTo 0
    EscribirLog "FIN " & Format(Now(), "YYYY-MM-DD HH:MM:SS")

    Application.ScreenUpdating = True
    Application.Calculation = xlCalculationAutomatic
    Application.StatusBar = False
    ThisWorkbook.Save
End Sub
