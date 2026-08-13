@echo off
echo === DEPLOY BODEGAS GESTION ===
E:\nodejs-portable\node.exe E:\npm-global\node_modules\firebase-tools\lib\bin\firebase.js deploy --project isabel-riquelme-merma --only hosting
if errorlevel 1 ( echo ERROR en deploy & pause & exit /b 1 )
echo.
echo Deploy OK
pause
