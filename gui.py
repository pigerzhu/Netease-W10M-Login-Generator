"""Local-only UI. Credentials are neither uploaded nor printed."""
import ctypes
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from generate_settings import generate


class GeneratorWindow:
    def __init__(self, root):
        self.root = root
        root.title('网易云 W10M 登录文件生成器')
        scale = root.winfo_fpixels('1i') / 96
        root.geometry(f'{round(680 * scale)}x{round(230 * scale)}')
        root.minsize(round(620 * scale), round(230 * scale))
        panel = ttk.Frame(root, padding=20)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='网易云 W10M / UWP', font=('Microsoft YaHei UI', 16)).pack(anchor='w')
        ttk.Label(panel, text='输入账号信息，生成 settings.dat', padding=(0, 5, 0, 12)).pack(anchor='w')
        self.values = {}
        self.form = ttk.Frame(panel)
        self.form.pack(fill='x')
        self.entries = {}
        for row, (name, title, default, secret) in enumerate([
            ('musicu', 'MUSIC_U（也支持完整 Cookie）', '', True),
            ('userid', '网易云用户 ID', '', False),
        ]):
            self.add_entry(self.form, row, name, title, default, secret)
        self.show_secret = tk.BooleanVar(value=False)
        ttk.Checkbutton(panel, text='显示 MUSIC_U', variable=self.show_secret, command=self.toggle_secret).pack(anchor='w', pady=(8, 12))
        ttk.Style(root).configure('Generate.TButton', padding=(12, round(10 * scale)))
        ttk.Button(panel, text='生成 settings.dat', style='Generate.TButton', command=self.save).pack(fill='x', pady=(4, 8))
        self.status = tk.StringVar(value='')
        ttk.Label(panel, textvariable=self.status, wraplength=620).pack(anchor='w')

    def add_entry(self, parent, row, name, label, default, secret):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', padx=(0, 14), pady=5)
        self.values[name] = tk.StringVar(value=default)
        entry = ttk.Entry(parent, textvariable=self.values[name], show='*' if secret else '')
        entry.grid(row=row, column=1, sticky='ew', pady=5)
        parent.columnconfigure(1, weight=1)
        self.entries[name] = entry

    def toggle_secret(self):
        self.entries['musicu'].configure(show='' if self.show_secret.get() else '*')

    def save(self):
        path = filedialog.asksaveasfilename(parent=self.root, title='保存登录文件', initialfile='settings.dat', defaultextension='.dat', filetypes=[('UWP Settings', '*.dat')])
        if not path:
            return
        try:
            args = {name: value.get().strip() for name, value in self.values.items()}
            output = generate(Path(path), **args)
        except (ValueError, OSError) as exc:
            messagebox.showerror('未生成文件', str(exc), parent=self.root)
            return
        self.status.set('已生成：' + str(output))
        messagebox.showinfo('文件已生成', '退出手机网易云，备份原 Settings 文件夹，再用此文件替换 settings.dat。', parent=self.root)


def main():
    # Declare DPI awareness before Tk creates any windows, so Windows does not
    # enlarge a 96-DPI bitmap on scaled displays.
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user32.SetProcessDpiAwarenessContext.restype = ctypes.c_bool
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-2))
    root = tk.Tk()
    GeneratorWindow(root)
    root.mainloop()


if __name__ == '__main__':
    main()
