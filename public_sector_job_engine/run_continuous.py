import time
import subprocess
import datetime

print("======================================================")
print("  Continuous Job Search Agent Started")
print("  This agent will constantly search for roles every 24h")
print("======================================================")

while True:
    print(f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Launching public sector job search...")
    try:
        subprocess.run(["python", "run_local_engine.py", "--universe", "All"], check=True)
        print("Search completed. Reports saved to reports/ folder.")
    except Exception as e:
        print(f"Error during search: {e}")
        
    print("\nWaiting 24 hours before next search sweep...")
    print("Press Ctrl+C to stop the continuous agent.")
    time.sleep(86400) # 24 hours
