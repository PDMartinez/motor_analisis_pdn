@echo off
cd /d "C:/xampp/htdocs/motor_analisis_pdn"
"C:/xampp/htdocs/motor_analisis_pdn/.venv/Scripts/python.exe" "C:/xampp/htdocs/motor_analisis_pdn\src\analisis\ejecutar_analisis.py" --solicitud-json "C:/xampp/htdocs/motor_analisis_pdn\trabajos\solicitud_3.json" >> "C:/xampp/htdocs/motor_analisis_pdn\logs\lanzador_3.log" 2>&1
