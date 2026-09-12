import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import sys
import os

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("UK Public Sector & NHS Job Engine")
        self.root.geometry("850x600")

        frame = ttk.Frame(root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Quick Launches:", font=("Segoe UI", 12, "bold")).pack(anchor="w")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="All Public Finance (UK)", command=lambda: self.run_cmd("--universe All")).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Civil Service Only", command=lambda: self.run_cmd('--universe "Civil Service"')).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="NHS Only", command=lambda: self.run_cmd('--universe "NHS, NHS Scotland"')).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Regulatory (FCA/NAO)", command=lambda: self.run_cmd('--universe "Regulatory"')).pack(side=tk.LEFT, padx=2)

        self.log_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, bg="black", fg="lightgreen", font=("Consolas", 10))
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=10)

        self.stop_btn = ttk.Button(frame, text="STOP", state=tk.DISABLED, command=self.stop_cmd)
        self.stop_btn.pack(pady=5)
        
        self.process = None

    def run_cmd(self, flags):
        if self.process: return
        self.log_area.delete(1.0, tk.END)
        cmd = f"python run_local_engine.py {flags}"
        self.log_area.insert(tk.END, f"Running: {cmd}\n\n")
        self.stop_btn.config(state=tk.NORMAL)
        threading.Thread(target=self._exec, args=(cmd,), daemon=True).start()

    def _exec(self, cmd):
        self.process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in self.process.stdout:
            self.root.after(0, self.log_area.insert, tk.END, line)
            self.root.after(0, self.log_area.see, tk.END)
        self.process.wait()
        self.root.after(0, self.stop_btn.config, {"state": tk.DISABLED})
        self.process = None

    def stop_cmd(self):
        if self.process:
            self.process.kill()

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
