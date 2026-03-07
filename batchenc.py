import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Menu
import os
import sys
import subprocess
import threading
import re
import json
import webbrowser
import platform
from collections import defaultdict

# --- CONSTANTS ---
APP_VERSION = "1.6.1"
ORIGINAL_VERSION = "1.5.1"
PLACEHOLDER_DIR = "<< same as input directory >>"
CONFIG_FILENAME = "Batchenc_presets.cfg"
SESSION_FILENAME = "last_session.txt"
LOG_FILENAME = "last_run.log"

# --- DRAG AND DROP SETUP ---
dnd_available = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    dnd_available = True
except ImportError:
    pass

# --- SYSTEM HELPERS ---
def get_script_directory():
    """Returns the directory of the script or executable safely."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_short_path(path):
    """Robust Windows 8.3 Short Path converter."""
    """
    if os.name != 'nt' or not os.path.exists(path):
        return path
    try:
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.windll.kernel32
        GetShortPathNameW = kernel.GetShortPathNameW
        GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        GetShortPathNameW.restype = wintypes.DWORD
        
        length = GetShortPathNameW(path, None, 0)
        if length == 0: return path
        
        buf = ctypes.create_unicode_buffer(length)
        if GetShortPathNameW(path, buf, length) == 0:
            return path
        return buf.value
    except Exception:
        return path
    """
    return path

def open_path_in_os(path):
    """Opens a file or directory in the OS default viewer/explorer."""
    if not os.path.exists(path):
        return
    
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.call(["open", path])
    else:
        try:
            subprocess.call(["xdg-open", path])
        except OSError: pass

# --- MAIN APPLICATION CLASS ---
class BatchencApp:
    def __init__(self, root):
        self.root = root
        self.stop_event = threading.Event()
        self.files_storage = []
        self.is_running = False
        
        self.setup_ui()
        self.create_default_presets()
        self.load_presets()
        self.load_session() 

    def setup_ui(self):
        self.root.title(f"Batchenc {APP_VERSION}")
        self.root.minsize(500, 420)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Top Frame
        top_frame = tk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Listbox Frame
        list_frame = tk.Frame(top_frame, bd=2, relief=tk.SUNKEN)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar = tk.Scrollbar(list_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_listbox = tk.Listbox(list_frame, yscrollcommand=self.scrollbar.set, bd=0, 
                                     highlightthickness=0, font=("Tahoma", 8), 
                                     activestyle='none', selectmode=tk.EXTENDED)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.file_listbox.yview)

        # Bindings
        if dnd_available:
            self.file_listbox.drop_target_register(DND_FILES)
            self.file_listbox.dnd_bind('<<Drop>>', self.drop_handler)
        self.file_listbox.bind("<Delete>", self.remove_selected_files)
        self.file_listbox.bind("<BackSpace>", self.remove_selected_files)
        self.file_listbox.bind("<Button-3>", self.show_context_menu)

        # Context Menu
        self.context_menu = Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Open File Location", command=self.open_file_location_action)

        # Buttons Frame
        btn_frame = tk.Frame(top_frame)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        tk.Button(btn_frame, text="Add Files", width=10, command=self.browse_files).pack(pady=(0, 2))
        self.btn_remove = tk.Button(btn_frame, text="Remove", width=10, command=self.remove_selected_files)
        self.btn_remove.pack(pady=(0, 2))
        self.btn_clear = tk.Button(btn_frame, text="Clear", width=10, command=self.clear_files)
        self.btn_clear.pack(pady=(0, 10))
        
        self.overwrite_var = tk.BooleanVar(value=False)
        tk.Checkbutton(btn_frame, text="Overwrite", variable=self.overwrite_var).pack(pady=(0, 2))
        
        self.low_priority_var = tk.BooleanVar(value=False)
        tk.Checkbutton(btn_frame, text="Low Priority", variable=self.low_priority_var).pack(pady=(0, 5))

        tk.Button(btn_frame, text="About", width=10, command=self.open_about_window).pack(pady=(0, 10))
        
        self.btn_start = tk.Button(btn_frame, text="Start", width=10, command=self.start_thread)
        self.btn_start.pack(pady=(0, 2))
        
        self.btn_stop = tk.Button(btn_frame, text="Stop", width=10, command=self.stop_processing, state=tk.DISABLED)
        self.btn_stop.pack(pady=(0, 2))
        
        tk.Button(btn_frame, text="Open Log", width=10, command=self.open_log).pack(pady=(10, 0))

        # Status Label
        self.status_label = tk.Label(self.root, text="Ready", anchor="w", fg="black")
        self.status_label.pack(side=tk.TOP, fill=tk.X, padx=7)

        # Command Frame
        mid_frame = tk.LabelFrame(self.root, text="Command line")
        mid_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(0, 5))
        mid_frame.columnconfigure(0, weight=1)

        self.cmd_combo = ttk.Combobox(mid_frame)
        self.cmd_combo.grid(row=0, column=0, padx=5, pady=12, sticky="ew")
        
        tk.Button(mid_frame, text="+", width=3, font=("Arial", 9, "bold"), command=self.add_preset).grid(row=0, column=1, padx=(0, 2))
        tk.Button(mid_frame, text="-", width=3, font=("Arial", 9, "bold"), command=self.remove_preset).grid(row=0, column=2, padx=(0, 5))

        self.progress = ttk.Progressbar(mid_frame, mode='indeterminate')
        self.progress.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5, pady=(0, 8))
        self.progress.grid_remove()

        # Output Frame
        bot_frame = tk.LabelFrame(self.root, text="Output directory")
        bot_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        bot_frame.columnconfigure(0, weight=1)

        self.output_entry = ttk.Entry(bot_frame)
        self.output_entry.insert(0, PLACEHOLDER_DIR)
        self.output_entry.config(foreground='gray')
        self.output_entry.bind('<FocusIn>', self.on_output_focus_in)
        self.output_entry.bind('<FocusOut>', self.on_output_focus_out)
        self.output_entry.grid(row=0, column=0, padx=5, pady=10, sticky="ew")
        
        tk.Button(bot_frame, text="Browse", width=8, command=self.browse_output_directory).grid(row=0, column=1, padx=5)

    # --- UI UPDATERS (Thread-Aware) ---
    def update_status_main(self, text, color="black"):
        """Direct update for main thread."""
        self.status_label.config(text=text, fg=color)

    def update_status_thread(self, text, color="black"):
        """Queued update for worker thread."""
        self.root.after(0, lambda: self.status_label.config(text=text, fg=color))

    def thread_safe_selection_set(self, index):
        def _update():
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(index)
            self.file_listbox.see(index)
        self.root.after(0, _update)

    def thread_safe_toggle_ui(self, running):
        def _update():
            state = tk.DISABLED if running else tk.NORMAL
            stop_state = tk.NORMAL if running else tk.DISABLED
            
            self.btn_start.config(text="Running..." if running else "Start", state=state)
            self.btn_remove.config(state=state)
            self.btn_clear.config(state=state)
            self.btn_stop.config(state=stop_state)
            
            if running:
                self.progress.grid()
                self.progress.start(10)
            else:
                self.progress.stop()
                self.progress.grid_remove()
        self.root.after(0, _update)

    # --- FILE LIST LOGIC ---
    def add_paths_to_list(self, paths):
        count_added = 0
        for path in paths:
            if not os.path.exists(path): continue
            full_path = os.path.abspath(path)
            if full_path in self.files_storage:
                continue
            self.files_storage.append(full_path)
            self.file_listbox.insert(tk.END, " " + os.path.basename(full_path))
            count_added += 1
        
        if count_added > 0:
            self.file_listbox.yview_moveto(1)
            self.update_status_main(f"Total files: {len(self.files_storage)}")

    def remove_selected_files(self, event=None):
        if self.is_running: return
        selection = self.file_listbox.curselection()
        if not selection: return

        for index in reversed(selection):
            self.file_listbox.delete(index)
            del self.files_storage[index]
        self.update_status_main(f"Total files: {len(self.files_storage)}")

    def clear_files(self):
        if self.is_running: return
        self.file_listbox.delete(0, tk.END)
        self.files_storage.clear()
        self.update_status_main("List cleared.")

    def browse_files(self):
        filenames = filedialog.askopenfilenames(title="Select files")
        if filenames: self.add_paths_to_list(filenames)

    def drop_handler(self, event):
        if event.data:
            self.add_paths_to_list(self.root.tk.splitlist(event.data))

    def show_context_menu(self, event):
        try:
            self.file_listbox.selection_clear(0, tk.END)
            idx = self.file_listbox.nearest(event.y)
            self.file_listbox.selection_set(idx)
            self.context_menu.post(event.x_root, event.y_root)
        except Exception: pass

    def open_file_location_action(self):
        selection = self.file_listbox.curselection()
        if not selection: return
        folder = os.path.dirname(self.files_storage[selection[0]])
        open_path_in_os(folder)

    # --- PRESETS & CONFIG ---
    def create_default_presets(self):
        cfg_path = os.path.join(get_script_directory(), CONFIG_FILENAME)
        if os.path.exists(cfg_path): return
        
        defaults = [
            "# === Audio ===",
            'ffmpeg -i <infile> -c:a aac -b:a 160k <outfile.m4a>',
            'ffmpeg -i <infile> -c:a aac -q:a 2 <outfile.m4a>',
            'lossyWAV.exe <infile> -q U -a 6 -s W x -A --scale 0.25 --stdout --silent --low | flac.exe -8 -e -p -b 512 -P=24576 -s -o <outfile.lossy.flac> -',
            "",
            "# === Video ===",
            'ffmpeg -i <infile> -c:v libx264 -crf 23 <outfile.mp4>',
            "",
            "# === Test ===",
            'echo converting <infile> to <outfile.mp3>',
            'echo ReplayGain on <allfiles>'
        ]
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write("\n".join(defaults))
        except Exception as e: print(f"Error creating defaults: {e}")

    def load_presets(self):
        cfg_path = os.path.join(get_script_directory(), CONFIG_FILENAME)
        if not os.path.exists(cfg_path): return
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                presets = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            self.cmd_combo['values'] = presets
        except Exception as e: print(f"Error loading presets: {e}")

    def add_preset(self):
        text = self.cmd_combo.get().strip()
        if not text: return
        
        curr = list(self.cmd_combo['values'])
        if text not in curr:
            curr.append(text)
            self.cmd_combo['values'] = curr
            
            cfg_path = os.path.join(get_script_directory(), CONFIG_FILENAME)
            try:
                # Append safely
                needs_nl = False
                if os.path.exists(cfg_path):
                    with open(cfg_path, "rb") as f:
                        f.seek(0, 2)
                        if f.tell() > 0:
                            f.seek(-1, 2)
                            if f.read(1) != b'\n': needs_nl = True
                
                with open(cfg_path, "a", encoding="utf-8") as f:
                    if needs_nl: f.write("\n")
                    f.write(text + "\n")
            except Exception as e: print(f"Error adding preset: {e}")

    def remove_preset(self):
        text = self.cmd_combo.get().strip()
        if not text: return
        
        # 1. Update UI
        curr = list(self.cmd_combo['values'])
        if text in curr:
            curr.remove(text)
            self.cmd_combo['values'] = curr
            self.cmd_combo.set('')
            
            # 2. Update File (Preserving Comments)
            cfg_path = os.path.join(get_script_directory(), CONFIG_FILENAME)
            if not os.path.exists(cfg_path): return
            
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                with open(cfg_path, "w", encoding="utf-8") as f:
                    for line in lines:
                        if line.strip() == text and not line.strip().startswith("#"):
                            continue
                        f.write(line)
                        
            except Exception as e: print(f"Error removing preset: {e}")

    # --- SESSION ---
    def save_session(self):
        data = {
            "command_line": self.cmd_combo.get(),
            "output_directory": self.output_entry.get(),
            "file_list": self.files_storage,
            "geometry": self.root.geometry(),
            "overwrite": self.overwrite_var.get(),
            "low_priority": self.low_priority_var.get()
        }
        try:
            with open(os.path.join(get_script_directory(), SESSION_FILENAME), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e: print(f"Error saving session: {e}")

    def load_session(self):
        path = os.path.join(get_script_directory(), SESSION_FILENAME)
        if not os.path.exists(path): return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if "geometry" in data: 
                try: self.root.geometry(data["geometry"])
                except Exception: pass
            
            if "command_line" in data: self.cmd_combo.set(data["command_line"])
            
            if "output_directory" in data:
                d = data["output_directory"]
                self.output_entry.delete(0, tk.END)
                self.output_entry.insert(0, d)
                color = 'gray' if d == PLACEHOLDER_DIR or not d else 'black'
                self.output_entry.config(foreground=color)
                
            if "overwrite" in data:
                self.overwrite_var.set(data["overwrite"])
                
            if "low_priority" in data:
                self.low_priority_var.set(data["low_priority"])

            if "file_list" in data:
                self.add_paths_to_list(data["file_list"])
                
        except Exception as e: print(f"Error loading session: {e}")

    def on_closing(self):
        if self.is_running:
            if not messagebox.askyesno("Exit", "Process is running. Stop and exit?"):
                return
            self.stop_event.set()
        self.save_session()
        self.root.destroy()

    # --- OUTPUT DIR HELPER ---
    def browse_output_directory(self):
        d = filedialog.askdirectory()
        if d:
            d = os.path.normpath(d)
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, d)
            self.output_entry.config(foreground='black')

    def on_output_focus_in(self, event):
        if self.output_entry.get() == PLACEHOLDER_DIR:
            self.output_entry.delete(0, tk.END)
            self.output_entry.config(foreground='black')

    def on_output_focus_out(self, event):
        if not self.output_entry.get().strip():
            self.output_entry.insert(0, PLACEHOLDER_DIR)
            self.output_entry.config(foreground='gray')
            
    @staticmethod
    def resolve_output_dir(raw_output_dir, input_path):
        """Thread-safe logic to resolve output directory from captured string."""
        if raw_output_dir == PLACEHOLDER_DIR or not raw_output_dir:
            return os.path.dirname(input_path)
        if not os.path.exists(raw_output_dir):
            try: os.makedirs(raw_output_dir)
            except OSError: return os.path.dirname(input_path)
        return raw_output_dir

    # --- PROCESSING ENGINE ---
    def open_log(self):
        path = os.path.join(get_script_directory(), LOG_FILENAME)
        if os.path.exists(path):
            open_path_in_os(path)
        else:
            messagebox.showinfo("Log", "No log file found.")

    def run_command_helper(self, cmd, log_file, low_priority=False):
        """Helper to run a subprocess safely and log output."""
        try:
            kwargs = {'stdout': log_file, 'stderr': subprocess.STDOUT, 'shell': True}
            if os.name == 'nt':
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                kwargs['startupinfo'] = si
                
                # Apply Windows Low Priority
                if low_priority:
                    kwargs['creationflags'] = 0x00000040
            else:
                # Apply Unix/Linux/macOS Low Priority using 'nice'
                if low_priority:
                    cmd = f"nice -n 19 {cmd}"
            
            return subprocess.run(cmd, **kwargs)
        except Exception as e:
            log_file.write(f"Error executing subprocess: {e}\n")
            return None

    def processing_thread(self, cmd_template, raw_output_dir, overwrite_mode, low_priority_mode, files_snapshot):
        log_path = os.path.join(get_script_directory(), LOG_FILENAME)
        had_errors = False
        
        self.is_running = True
        self.thread_safe_toggle_ui(True)
        self.update_status_thread("Initializing...", "blue")
        
        try:
            with open(log_path, "w", encoding="utf-8", errors="replace") as log:
                def log_print(msg):
                    log.write(str(msg) + "\n")
                    log.flush()
                
                log_print(f"--- Session Start: {APP_VERSION} ---")
                if low_priority_mode:
                    log_print("--- Running in Low Priority Mode ---")

                # --- ALBUM MODE ---
                if "<allfiles>" in cmd_template:
                    self.update_status_thread("Mode: Directory Processing", "blue")
                    files_by_dir = defaultdict(list)
                    for f in files_snapshot:
                        files_by_dir[os.path.dirname(f)].append(f)
                    
                    total = len(files_by_dir)
                    for i, (folder, files) in enumerate(files_by_dir.items(), 1):
                        if self.stop_event.is_set():
                            log_print("--- Stopped by user ---")
                            break
                            
                        self.update_status_thread(f"Processing dir {i}/{total}", "blue")
                        
                        safe_files = [get_short_path(f) for f in files]
                        all_files_str = " ".join([f'"{f}"' for f in safe_files])
                        cmd = cmd_template.replace("<allfiles>", all_files_str)
                        
                        log_print(f"Dir: {folder}\nCmd: {cmd}")
                        res = self.run_command_helper(cmd, log, low_priority=low_priority_mode)
                        if res and res.returncode != 0: had_errors = True

                # --- STANDARD MODE ---
                else:
                    outfile_regex = re.compile(r"<outfile\.([^>]+)>")
                    match = outfile_regex.search(cmd_template)
                    target_ext = match.group(1) if match else ""
                    tag = match.group(0) if match else ""
                    
                    total = len(files_snapshot)
                    for i, infile in enumerate(files_snapshot):
                        if self.stop_event.is_set():
                            log_print("--- Stopped by user ---")
                            break
                        
                        self.thread_safe_selection_set(i)
                        self.update_status_thread(f"Processing file {i+1}/{total}", "blue")
                        
                        safe_in = get_short_path(infile)
                        # Resolve output dir using captured value (No Widget Access!)
                        out_dir = self.resolve_output_dir(raw_output_dir, infile)
                        safe_out_dir = get_short_path(out_dir)
                        
                        final_out = ""
                        if target_ext:
                            base = os.path.splitext(os.path.basename(infile))[0]
                            final_out = os.path.join(safe_out_dir, f"{base}.{target_ext}")
                            
                            if not overwrite_mode and os.path.exists(final_out):
                                log_print(f"Skipping {os.path.basename(infile)} (File exists)")
                                continue

                        cmd = cmd_template.replace("<infile>", f'"{safe_in}"')
                        if tag and final_out:
                            cmd = cmd.replace(tag, f'"{final_out}"')
                            
                        log_print(f"File: {os.path.basename(infile)}\nCmd: {cmd}")
                        res = self.run_command_helper(cmd, log, low_priority=low_priority_mode)
                        if res and res.returncode != 0: had_errors = True

                log_print("--- Finished ---")
        
        except Exception as e:
            had_errors = True
            print(f"Fatal Error: {e}")

        # Final UI Update
        def _finish():
            self.is_running = False
            self.thread_safe_toggle_ui(False) # Re-enable buttons
            
            if self.stop_event.is_set():
                self.stop_event.clear()
                self.update_status_main("Stopped by user.", "dark orange")
            elif had_errors:
                self.update_status_main("Finished with errors. Check Log.", "dark orange")
                messagebox.showwarning("Finished", "Errors occurred. Check log.")
            else:
                self.update_status_main("Done.", "dark green")
                
        self.root.after(0, _finish)

    def start_thread(self):
        if not self.files_storage:
            messagebox.showwarning("Warning", "No files in list.")
            return
        
        cmd = self.cmd_combo.get().strip()
        if not cmd:
            messagebox.showwarning("Warning", "No command specified.")
            return
            
        if "<infile>" not in cmd and "<allfiles>" not in cmd:
            if not messagebox.askyesno("Warning", "Command contains no file placeholders. Continue?"):
                return

        # CAPTURE STATE IN MAIN THREAD
        raw_output_dir = self.output_entry.get().strip()
        overwrite_mode = self.overwrite_var.get()
        low_priority_mode = self.low_priority_var.get()
        files_snapshot = list(self.files_storage)

        self.stop_event.clear()
        
        # PASS EVERYTHING AS ARGUMENTS (Zero Widget Access in Worker)
        t = threading.Thread(target=self.processing_thread, 
                             args=(cmd, raw_output_dir, overwrite_mode, low_priority_mode, files_snapshot), 
                             daemon=True)
        t.start()

    def stop_processing(self):
        if self.is_running:
            self.stop_event.set()
            self.btn_stop.config(state=tk.DISABLED)
            self.update_status_main("Stopping...", "red")

    def open_about_window(self):
        win = tk.Toplevel(self.root)
        win.title("About")
        win.resizable(False, False)
        frame = tk.Frame(win, padx=20, pady=15)
        frame.pack()
        
        font_b = ("Tahoma", 10, "bold")
        font_n = ("Tahoma", 9)
        font_u = ("Tahoma", 9, "underline")
        
        tk.Label(frame, text="Batchenc", font=font_b).pack()
        tk.Label(frame, text=f"Original v{ORIGINAL_VERSION} by Speek", font=font_n).pack()
        l1 = tk.Label(frame, text="Original Website", font=font_u, fg="blue", cursor="hand2")
        l1.pack(pady=(0, 10))
        l1.bind("<Button-1>", lambda e: webbrowser.open("https://web.archive.org/web/20071011045500/http://members.home.nl/w.speek/download/Batchenc.zip"))
        
        tk.Label(frame, text=f"Refactored v{APP_VERSION}", font=font_n).pack()
        tk.Label(frame, text="by Google Gemini", font=font_n).pack()
        l2 = tk.Label(frame, text="Gemini", font=font_u, fg="blue", cursor="hand2")
        l2.pack()
        l2.bind("<Button-1>", lambda e: webbrowser.open("https://gemini.google.com/"))
        
        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (w // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (h // 2)
        win.geometry(f"+{x}+{y}")

# --- ENTRY POINT ---
if __name__ == "__main__":
    if dnd_available:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = BatchencApp(root)
    root.mainloop()

