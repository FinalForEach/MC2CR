"""Main Native Tkinter GUI application for MC2CR with modern Sun Valley theme."""

from __future__ import annotations

import multiprocessing
import os
import queue
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from mc2cr.gui.theme import setup_native_theme, toggle_theme
from mc2cr.gui.worker import CompleteEvent, ConversionWorker, ErrorEvent, LogEvent, ProgressEvent
from mc2cr.paths import get_default_cr_saves_dir, get_default_mc_saves_dir, resolve_mc_saves_root
from mc2cr.scanner import MinecraftWorldInfo, inspect_mc_world, scan_mc_worlds


class MC2CRApp:
    """MC2CR Native GUI Application."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("MC2CR - Minecraft to Cosmic Reach Converter")
        self.root.geometry("660x740")
        self.root.minsize(580, 600)

        self.event_queue: queue.Queue = queue.Queue()
        self.worker: Optional[ConversionWorker] = None
        self.discovered_worlds: List[MinecraftWorldInfo] = []
        self.selected_custom_world: Optional[MinecraftWorldInfo] = None
        self.is_dark_theme = True

        # State Variables
        self.mc_saves_dir_var = tk.StringVar(value=str(resolve_mc_saves_root()))
        self.cr_saves_dir_var = tk.StringVar(value=str(get_default_cr_saves_dir()))
        self.selected_world_label_var = tk.StringVar()
        self.output_world_name_var = tk.StringVar()
        self.y_offset_var = tk.IntVar(value=-64)
        self.workers_var = tk.StringVar(value="Auto")
        self.mapping_file_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Ready to convert.")
        self.eta_var = tk.StringVar(value="")

        # Setup Styling & UI
        setup_native_theme(self.root, theme="dark")
        self._build_ui()
        self._update_log_colors()
        self._refresh_mc_worlds()

    def _build_ui(self) -> None:
        main_frame = ttk.Frame(self.root, padding="16 14 16 14")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header with Title and Theme Switcher
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header_frame, text="MC2CR World Converter", style="Title.TLabel").pack(side=tk.LEFT)
        self.btn_theme = ttk.Button(header_frame, text="☀️ Light", style="Action.TButton", command=self._on_toggle_theme)
        self.btn_theme.pack(side=tk.RIGHT)

        # 1. Source World Section
        src_group = ttk.LabelFrame(main_frame, text=" Minecraft Source World ", padding="10 10 10 10")
        src_group.pack(fill=tk.X, pady=(0, 10))

        # Saves Directory Row
        dir_frame = ttk.Frame(src_group)
        dir_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(dir_frame, text="Saves Directory:").pack(side=tk.LEFT)
        dir_entry = ttk.Entry(dir_frame, textvariable=self.mc_saves_dir_var)
        dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 6))
        ttk.Button(dir_frame, text="Browse...", command=self._browse_mc_saves_dir).pack(side=tk.LEFT)
        ttk.Button(dir_frame, text="Refresh", command=self._refresh_mc_worlds).pack(side=tk.LEFT, padx=(4, 0))

        # World Selector Row
        world_frame = ttk.Frame(src_group)
        world_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(world_frame, text="Select World:").pack(side=tk.LEFT)
        self.world_combo = ttk.Combobox(world_frame, textvariable=self.selected_world_label_var, state="readonly")
        self.world_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(18, 6))
        self.world_combo.bind("<<ComboboxSelected>>", self._on_world_selected)
        ttk.Button(world_frame, text="Custom World...", command=self._browse_custom_world).pack(side=tk.LEFT)

        # World Info Card
        self.info_frame = ttk.Frame(src_group, padding="6 4 6 4")
        self.info_frame.pack(fill=tk.X, pady=(4, 0))
        self.lbl_world_details = ttk.Label(self.info_frame, text="No world selected.")
        self.lbl_world_details.pack(anchor=tk.W)

        # 2. Destination Section
        dst_group = ttk.LabelFrame(main_frame, text=" Cosmic Reach Destination ", padding="10 10 10 10")
        dst_group.pack(fill=tk.X, pady=(0, 10))

        cr_dir_frame = ttk.Frame(dst_group)
        cr_dir_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(cr_dir_frame, text="CR Worlds Dir:").pack(side=tk.LEFT)
        ttk.Entry(cr_dir_frame, textvariable=self.cr_saves_dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 6))
        ttk.Button(cr_dir_frame, text="Browse...", command=self._browse_cr_saves_dir).pack(side=tk.LEFT)

        out_name_frame = ttk.Frame(dst_group)
        out_name_frame.pack(fill=tk.X)
        ttk.Label(out_name_frame, text="Output Folder:").pack(side=tk.LEFT)
        ttk.Entry(out_name_frame, textvariable=self.output_world_name_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

        # 3. Settings
        cfg_group = ttk.LabelFrame(main_frame, text=" Conversion Options ", padding="10 8 10 8")
        cfg_group.pack(fill=tk.X, pady=(0, 10))

        cfg_row1 = ttk.Frame(cfg_group)
        cfg_row1.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(cfg_row1, text="Y-Offset (blocks):").pack(side=tk.LEFT)
        ttk.Spinbox(cfg_row1, from_=-256, to=256, textvariable=self.y_offset_var, width=8).pack(side=tk.LEFT, padx=(8, 20))
        ttk.Label(cfg_row1, text="Parallel Workers:").pack(side=tk.LEFT)
        ttk.Combobox(cfg_row1, textvariable=self.workers_var, values=["Auto", "1", "2", "4", "8", "16"], width=6, state="readonly").pack(side=tk.LEFT, padx=(8, 0))

        cfg_row2 = ttk.Frame(cfg_group)
        cfg_row2.pack(fill=tk.X)
        ttk.Label(cfg_row2, text="Mapping Override:").pack(side=tk.LEFT)
        ttk.Entry(cfg_row2, textvariable=self.mapping_file_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))
        ttk.Button(cfg_row2, text="Select...", command=self._browse_mapping_file).pack(side=tk.LEFT)

        # 4. Action & Progress Section
        act_frame = ttk.Frame(main_frame)
        act_frame.pack(fill=tk.X, pady=(0, 8))

        self.btn_convert = ttk.Button(act_frame, text="Convert World", style="Accent.TButton", command=self._start_conversion)
        self.btn_convert.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.btn_open_folder = ttk.Button(act_frame, text="Open CR Worlds", style="Action.TButton", command=self._open_cr_folder)
        self.btn_open_folder.pack(side=tk.RIGHT)

        # Progress Status
        prog_info_frame = ttk.Frame(main_frame)
        prog_info_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(prog_info_frame, textvariable=self.status_var, style="Bold.TLabel").pack(side=tk.LEFT)
        ttk.Label(prog_info_frame, textvariable=self.eta_var).pack(side=tk.RIGHT)

        self.progress_bar = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        # Log Console
        log_group = ttk.LabelFrame(main_frame, text=" Conversion Log ", padding="6 6 6 6")
        log_group.pack(fill=tk.BOTH, expand=True)

        font_family = "Consolas" if sys.platform == "win32" else "Monospace"
        self.log_text = tk.Text(log_group, wrap=tk.WORD, height=8, font=(font_family, 9), relief=tk.FLAT, padx=6, pady=6)
        scrollbar = ttk.Scrollbar(log_group, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _on_toggle_theme(self) -> None:
        toggle_theme()
        self.is_dark_theme = not self.is_dark_theme
        self.btn_theme.config(text="☀️ Light" if self.is_dark_theme else "🌙 Dark")
        self._update_log_colors()

    def _update_log_colors(self) -> None:
        bg = "#1e1e1e" if self.is_dark_theme else "#fafafa"
        fg = "#d4d4d4" if self.is_dark_theme else "#222222"
        insert_bg = "#ffffff" if self.is_dark_theme else "#000000"
        self.log_text.configure(bg=bg, fg=fg, insertbackground=insert_bg)

    def _log(self, text: str) -> None:
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    def _refresh_mc_worlds(self) -> None:
        saves_dir = Path(self.mc_saves_dir_var.get())
        self.discovered_worlds = scan_mc_worlds(saves_dir)
        labels = [w.display_label for w in self.discovered_worlds]
        self.world_combo["values"] = labels

        if self.discovered_worlds:
            self.world_combo.current(0)
            self._on_world_selected()
        else:
            self.selected_world_label_var.set("")
            self.lbl_world_details.config(text="No Minecraft worlds found in this directory.")

    def _on_world_selected(self, _event: Optional[tk.Event] = None) -> None:
        idx = self.world_combo.current()
        if idx >= 0 and idx < len(self.discovered_worlds):
            self.selected_custom_world = None
            info = self.discovered_worlds[idx]
            self._update_world_details(info)

    def _update_world_details(self, info: MinecraftWorldInfo) -> None:
        details = (
            f"Folder: {info.folder_name}  |  Version: {info.version_str or 'Unknown'}  |  "
            f"Regions: {info.region_count}  |  Last Played: {info.last_played_str or 'Unknown'}"
        )
        self.lbl_world_details.config(text=details)
        self.output_world_name_var.set(info.folder_name)

    def _browse_mc_saves_dir(self) -> None:
        chosen = filedialog.askdirectory(title="Select Minecraft Saves Directory", initialdir=self.mc_saves_dir_var.get())
        if chosen:
            self.mc_saves_dir_var.set(chosen)
            self._refresh_mc_worlds()

    def _browse_custom_world(self) -> None:
        chosen = filedialog.askdirectory(title="Select Custom Minecraft World Directory")
        if chosen:
            info = inspect_mc_world(Path(chosen))
            if info is None:
                messagebox.showerror("Invalid World", f"The selected folder does not appear to be a Minecraft world:\n{chosen}")
                return
            self.selected_custom_world = info
            self.selected_world_label_var.set(f"[Custom] {info.display_label}")
            self._update_world_details(info)

    def _browse_cr_saves_dir(self) -> None:
        chosen = filedialog.askdirectory(title="Select Cosmic Reach Worlds Directory", initialdir=self.cr_saves_dir_var.get())
        if chosen:
            self.cr_saves_dir_var.set(chosen)

    def _browse_mapping_file(self) -> None:
        chosen = filedialog.askopenfilename(title="Select Block Mapping Override JSON", filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if chosen:
            self.mapping_file_var.set(chosen)

    def _open_cr_folder(self) -> None:
        folder = Path(self.cr_saves_dir_var.get())
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # type: ignore
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as e:
            messagebox.showwarning("Open Folder", f"Could not open directory: {e}")

    def _get_active_world_info(self) -> Optional[MinecraftWorldInfo]:
        if self.selected_custom_world is not None:
            return self.selected_custom_world
        idx = self.world_combo.current()
        if idx >= 0 and idx < len(self.discovered_worlds):
            return self.discovered_worlds[idx]
        return None

    def _start_conversion(self) -> None:
        world_info = self._get_active_world_info()
        if not world_info:
            messagebox.showwarning("No World Selected", "Please select a Minecraft world to convert.")
            return

        out_name = self.output_world_name_var.get().strip()
        if not out_name:
            messagebox.showwarning("Invalid Name", "Please specify an output folder name.")
            return

        cr_root = Path(self.cr_saves_dir_var.get().strip())
        out_path = cr_root / out_name

        if out_path.exists():
            confirm = messagebox.askyesno(
                "Destination Exists",
                f"The destination world folder already exists:\n\n{out_path}\n\nDo you want to overwrite it?",
            )
            if not confirm:
                return

        workers_val = self.workers_var.get()
        max_workers = int(workers_val) if workers_val.isdigit() else None
        mapping_file = self.mapping_file_var.get().strip() or None

        self.btn_convert.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self.status_var.set("Starting conversion...")
        self.eta_var.set("")
        self._log(f"\n{'=' * 45}\nConverting '{world_info.display_name}' -> '{out_path.name}'")

        self.worker = ConversionWorker(
            input_path=world_info.path,
            output_path=out_path,
            y_offset=self.y_offset_var.get(),
            max_workers=max_workers,
            mapping_override=mapping_file,
            event_queue=self.event_queue,
        )
        self.worker.start()
        self.root.after(100, self._process_events)

    def _process_events(self) -> None:
        try:
            while True:
                event = self.event_queue.get_nowait()
                if isinstance(event, ProgressEvent):
                    self.progress_bar["value"] = event.percentage
                    phase_name = "Saving" if event.phase == "save" else "Converting"
                    self.status_var.set(f"{phase_name} {event.item_name} [{event.current}/{event.total}] ({event.percentage:.1f}%)")
                    self.eta_var.set(f"ETA: {event.eta_str} | Elapsed: {event.elapsed_str}")
                elif isinstance(event, LogEvent):
                    self._log(event.message)
                elif isinstance(event, CompleteEvent):
                    self._on_conversion_complete(event.stats)
                    return
                elif isinstance(event, ErrorEvent):
                    self._on_conversion_error(event.error_message)
                    return
        except queue.Empty:
            pass

        if self.worker and self.worker.is_alive():
            self.root.after(100, self._process_events)

    def _on_conversion_complete(self, stats: dict) -> None:
        self.btn_convert.config(state=tk.NORMAL)
        self.progress_bar["value"] = 100
        self.status_var.set("Conversion complete!")
        self.eta_var.set(f"Finished in {stats.get('elapsed_seconds', 0):.2f}s")

        self._log("-" * 45)
        self._log("Conversion Complete!")
        self._log(f"MC Chunks Read:      {stats.get('mc_chunks_converted', 0)}")
        self._log(f"CR Chunks Created:   {stats.get('cr_chunks_generated', 0)}")
        self._log(f"CR Regions Saved:    {stats.get('cr_regions_saved', 0)}")
        self._log(f"Time Elapsed:        {stats.get('elapsed_seconds', 0):.2f}s")
        self._log("=" * 45)

        messagebox.showinfo(
            "Success",
            f"Successfully converted '{stats.get('world_name')}' to Cosmic Reach!\n\nSaved to: {self.cr_saves_dir_var.get()}/{self.output_world_name_var.get()}",
        )

    def _on_conversion_error(self, err_msg: str) -> None:
        self.btn_convert.config(state=tk.NORMAL)
        self.status_var.set("Conversion failed.")
        self.eta_var.set("")
        self._log(f"[ERROR] {err_msg}")
        messagebox.showerror("Conversion Failed", f"An error occurred during conversion:\n\n{err_msg}")


def main() -> None:
    """Entry point for the MC2CR GUI application."""
    multiprocessing.freeze_support()
    root = tk.Tk()
    app = MC2CRApp(root)
    root.mainloop()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
