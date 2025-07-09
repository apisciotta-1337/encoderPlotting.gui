import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading, time, random, csv
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt


class EncoderSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Encoder Simulator")
        self.root.geometry("1600x1100")
        # State variables
        self.running = False
        self.correction_count = 0
        self.enable_backlash_var = tk.BooleanVar(value=True)
        self.enable_correction_var = tk.BooleanVar(value=True)
        self.sample_interval_var = tk.DoubleVar(value=0.5)
        self.session_duration_var = tk.IntVar(value=0)
        self.ppr_var = tk.IntVar(value=200)
        self.status_var = tk.StringVar(value="Ready.")
        self.target_var = tk.StringVar()
        self.actual_var = tk.StringVar()
        self.error_var = tk.StringVar()
        self.total_distance_var = tk.StringVar()
        self.direction_var = tk.StringVar()
        self.correction_var = tk.StringVar()
        self.correction_count_var = tk.StringVar()

        # Style
        default_font = ("Arial", 18)
        self.root.option_add("*Menu.font", default_font)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TLabel", font=default_font)
        style.configure("TEntry", font=default_font)
        style.configure("TButton", font=default_font)
        style.configure("TCheckbutton", font=default_font)
        style.configure("Treeview", font=default_font, rowheight=30)
        style.configure("Treeview.Heading", font=("Arial", 20, "bold"))

        self.apply_dark_theme()
        self.create_menu_bar()
        self.root.bind("<Control-d>", lambda e: self.toggle_theme())

        # === Top central panel ===
        top_panel = ttk.Frame(root)
        top_panel.pack(pady=8, padx=10)

        # Info section
        info_frame = ttk.Frame(top_panel)
        info_frame.grid(row=0, column=0, sticky="n")
        ttk.Label(info_frame, textvariable=self.status_var, foreground="cyan", font=("Arial", 20)).pack(anchor="center",
                                                                                                        pady=1)
        for var in [self.target_var, self.actual_var, self.error_var,
                    self.total_distance_var, self.direction_var,
                    self.correction_var, self.correction_count_var]:
            ttk.Label(info_frame, textvariable=var, font=("Arial", 18)).pack(anchor="center", pady=0)
        self.reset_info()

        # Control section
        control_frame = ttk.Frame(top_panel)
        control_frame.grid(row=0, column=1, padx=60, sticky="n")
        for i, (txt, var) in enumerate([
            ("Sampling Interval (s):", self.sample_interval_var),
            ("Session Duration (s):", self.session_duration_var),
            ("Pulses per Revolution:", self.ppr_var)
        ]):
            ttk.Label(control_frame, text=txt).grid(row=i, column=0, sticky="e", pady=4, padx=(0, 6))
            ttk.Entry(control_frame, textvariable=var, width=20, font=("Arial", 20)).grid(
                row=i, column=1, pady=4, sticky="w", ipady=4
            )
        ttk.Checkbutton(control_frame, text="Enable Backlash Simulation", variable=self.enable_backlash_var).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=2
        )
        ttk.Checkbutton(control_frame, text="Enable Error Correction", variable=self.enable_correction_var).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=2
        )
        self.start_btn = ttk.Button(control_frame, text="Start", width=18, command=self.start_simulation)
        self.start_btn.grid(row=5, column=0, pady=8, sticky="e")
        self.stop_btn = ttk.Button(control_frame, text="Stop", width=18, command=self.stop_simulation, state="disabled")
        self.stop_btn.grid(row=5, column=1, pady=8, sticky="w")

        # === Plot ===
        self.fig, self.ax1 = plt.subplots(figsize=(14, 7))
        self.ax2 = self.ax1.twinx()
        self.apply_plot_dark()
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 5))

        # === Data table ===
        table_frame = ttk.Frame(root)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.table = ttk.Treeview(table_frame, columns=("time", "pos", "vel", "err", "corr"), show="headings")
        for col in self.table["columns"]:
            self.table.heading(col, text=col.title())
            self.table.column(col, anchor="center", width=160)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

    def reset_info(self):
        self.target_var.set("🎯 Target: 0.00 mm")
        self.actual_var.set("📍 Actual: 0.00 mm")
        self.error_var.set("📏 Error: 0.00 mm")
        self.total_distance_var.set("📈 Cumulative: 0.00 mm")
        self.direction_var.set("🔁 Direction: Idle")
        self.correction_var.set("")
        self.correction_count_var.set("🔧 Corrections: 0")

    def create_menu_bar(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Export to CSV", command=self.export_csv)
        file_menu.add_command(label="Save Plot Image", command=self.save_plot_image)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        setting_menu = tk.Menu(menubar, tearoff=0)
        setting_menu.add_command(label="Toggle Theme (Ctrl+D)", command=self.toggle_theme)
        menubar.add_cascade(label="Settings", menu=setting_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About",
                              command=lambda: messagebox.showinfo("About", "Encoder Simulator\nMade with ❤️"))
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def apply_dark_theme(self):
        self.root.configure(bg="#2E2E2E")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background="#2E2E2E", foreground="white", fieldbackground="#3E3E3E")
        style.configure("TLabel", background="#2E2E2E", foreground="white")
        style.configure("TCheckbutton", background="#2E2E2E", foreground="white")
        style.configure("Treeview", background="#2E2E2E", fieldbackground="#2E2E2E", foreground="white")
        style.configure("Treeview.Heading", background="#3E3E3E", foreground="white")

    def apply_plot_dark(self):
        self.fig.patch.set_facecolor('#2E2E2E')
        for ax in (self.ax1, self.ax2):
            ax.set_facecolor('#2E2E2E')
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.tick_params(colors='white')

    def apply_light_theme(self):
        self.root.configure(bg="SystemButtonFace")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background="SystemButtonFace", foreground="black")
        style.configure("Treeview", background="white", fieldbackground="white", foreground="black")
        style.configure("Treeview.Heading", background="lightgray", foreground="black")

    def toggle_theme(self):
        if self.root.cget("bg") == "#2E2E2E":
            self.apply_light_theme()
        else:
            self.apply_dark_theme()
        self.apply_plot_dark()

    def export_csv(self):
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not p: return
        with open(p, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(["Time", "Position", "Velocity", "Error", "Correction"])
            for iid in self.table.get_children():
                w.writerow(self.table.item(iid)["values"])
        messagebox.showinfo("Exported", f"CSV saved to:\n{p}")

    def save_plot_image(self):
        p = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if not p: return
        self.fig.savefig(p)
        messagebox.showinfo("Saved", f"Plot image saved to:\n{p}")

    def start_simulation(self):
        if self.running: return
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.reset_info()
        threading.Thread(target=self.run_simulation, daemon=True).start()

    def stop_simulation(self):
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_var.set("🛑 Simulation stopped.")

    def run_simulation(self):
        target_seq = [0, 6.35, 12.7, 6.35, 0, -6.35, -12.7, -6.35, 0]
        idx, current, cum = 0, 0, 0
        times, pos, vel, hits, cors = [], [], [], [], []
        t0 = time.time();
        lt, lp = t0, 0
        session_duration = self.session_duration_var.get()
        while self.running:
            now = time.time()
            elapsed, dt = now - t0, now - lt
            tgt = target_seq[idx]
            dirn = (1 if current < tgt else -1 if current > tgt else 0)
            if dirn == 0:
                self.status_var.set(f"✅ Reached {tgt:.2f} mm — pausing...")
                hits.append((elapsed, current))
                self.canvas.draw()
                time.sleep(2)
                idx = (idx + 1) % len(target_seq)
                lt = time.time()
                continue
            d = random.uniform(1, 2) * dirn
            if self.enable_backlash_var.get():
                d += random.uniform(0.01, 0.2) * (-1 if dirn > 0 else 1)
            current += d
            if (dirn > 0 and current > tgt) or (dirn < 0 and current < tgt):
                d -= abs(current - tgt);
                current = tgt
            cf = "No";
            corr_amt = 0
            if self.enable_correction_var.get() and abs(current - tgt) <= 0.25:
                corr_amt = tgt - current
                if abs(corr_amt) > 1e-6:
                    self.correction_count += 1
                    cors.append((elapsed, tgt))
                    cf = "Yes"
                current = tgt
            v = (current - lp) / dt if dt > 0 else 0
            cum += abs(d)
            times.append(elapsed);
            pos.append(current);
            vel.append(v)
            # Update info labels
            self.status_var.set("")
            self.target_var.set(f"🎯 Target: {tgt:.2f} mm")
            self.actual_var.set(f"📍 Actual: {current:.2f} mm")
            self.error_var.set(f"📏 Error: {abs(tgt - current):.2f} mm")
            self.total_distance_var.set(f"📈 Cumulative: {cum:.2f} mm")
            self.direction_var.set(f"🔁 Direction: {'Fwd' if dirn == 1 else 'Rev'}")
            self.correction_var.set(f"✔️ Corr: {corr_amt:+.3f} mm" if cf == "Yes" else "")
            self.correction_count_var.set(f"🔧 Corrections: {self.correction_count}")
            self.table.insert("", "end", values=(
                f"{elapsed:.2f}", f"{current:.2f}", f"{v:.2f}",
                f"{abs(tgt - current):.2f}", cf
            ))
            lt, lp = now, current
            self.apply_plot_dark()
            self.ax1.clear();
            self.ax2.clear()
            self.ax1.plot(times, pos, 'b-', label="Position")
            self.ax2.plot(times, vel, 'r-', label="Velocity")
            if hits:
                mx, my = zip(*hits);
                self.ax1.plot(mx, my, 'bo', label="Reached")
            if cors:
                cx, cy = zip(*cors);
                self.ax1.plot(cx, cy, 'ro', label="Corr")
            self.ax1.set_xlabel("Time (s)", fontsize=18)
            self.ax1.tick_params(colors='white', labelsize=14)
            self.ax2.tick_params(colors='white', labelsize=14)
            self.ax1.grid(True, linestyle='--', alpha=0.6)
            self.ax1.legend(fontsize=14)
            self.ax2.legend(fontsize=14)
            self.canvas.draw()
            self.fig.tight_layout()
            if session_duration > 0 and elapsed >= session_duration:
                t0 = now;
                lt = now;
                lp = current
                times, pos, vel, hits, cors = [], [], [], [], []
                cum = 0
                self.correction_count = 0
                self.reset_info()
            time.sleep(self.sample_interval_var.get())


if __name__ == "__main__":
    root = tk.Tk()
    app = EncoderSimulatorApp(root)
    root.mainloop()
