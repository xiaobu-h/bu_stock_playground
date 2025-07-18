import time
import datetime
import subprocess

def log(msg):
    with open("D:\\log\\monitor.log", "a") as f:
        f.write(f"{datetime.datetime.now()} - {msg}\n")

def run_script(path):
    try:
        subprocess.run(["python", path], check=True) 
    except Exception as e:
        log(f"Failed to run {path}: {e}")

def main():
    has_run_1am = False
    has_run_2am = False

    while True:
        now = datetime.datetime.now()
        hour = now.hour

        # 每天凌晨重置执行标志
        if now.hour == 0 and now.minute == 0:
            has_run_1am = False
            has_run_2am = False
        
        if  hour == 1 and now.minute == 0 and not has_run_1am:
            run_script("C:\\bu_stock_git\\bu_stock_playground\\dividend_monitor.py")
            
        if hour == 1 and now.minute == 10 and not has_run_1am:
            run_script("C:\\bu_stock_git\\bu_stock_playground\\daily_monitor.py")
            has_run_1am = True

        if hour == 2 and not has_run_2am:
            run_script("C:\\bu_stock_git\\bu_stock_playground\\daily_monitor.py")
            has_run_2am = True

        time.sleep(55)  # 每55秒检查一次

if __name__ == "__main__":
    log("start monitoring...")
    main()
