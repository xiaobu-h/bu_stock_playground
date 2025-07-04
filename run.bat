@echo off


echo === Running dividend_monitor.py === >> C:\bu_stock_git\dividend_log.txt
"C:\Users\guohy\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe" C:\bu_stock_git\bu_stock_playground\dividend_monitor.py >> C:\bu_stock_git\dividend_log.txt 2>&1

echo === Running daily_monitor.py === >> C:\bu_stock_git\combined_log.txt
"C:\Users\guohy\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe" C:\bu_stock_git\bu_stock_playground\daily_monitor.py >> C:\bu_stock_git\combined_log.txt 2>&1