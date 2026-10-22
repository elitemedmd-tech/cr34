"""CR3 → JPEG batch converter for Windows 11. Dependencies: rawpy, Pillow."""
import os
import queue
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import rawpy
    from PIL import Image
    BACKEND_ERROR = None
except ImportError as exc:
    BACKEND_ERROR = str(exc)

APP_NAME = 'CR3 → JPEG Конвертер'

class App:
    def __init__(self, root):
        self.root = root
        root.title(APP_NAME)
        root.geometry('790x605')
        root.minsize(660, 540)
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        self.files = []
        self.base_folder = None
        self.output = tk.StringVar(value=str(Path.home() / 'Pictures' / 'CR3_JPEG'))
        self.quality = tk.IntVar(value=95)
        self.keep_structure = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value='Добавьте файлы CR3 или выберите папку.')
        self.count = tk.StringVar(value='Файлов: 0')
        self.create_ui()
        root.after(100, self.poll)
        if BACKEND_ERROR:
            root.after(400, lambda: messagebox.showerror('Ошибка зависимостей', 'Не установлены библиотеки для обработки RAW:\n' + BACKEND_ERROR))

    def create_ui(self):
        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='CR3 → JPEG', font=('Segoe UI', 24, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Пакетная конвертация фотографий Canon RAW в JPEG • Windows 11').pack(anchor='w', pady=(0, 14))
        actions = ttk.Frame(frame)
        actions.pack(fill='x', pady=(0, 8))
        self.add_files_btn = ttk.Button(actions, text='Добавить CR3-файлы', command=self.add_files)
        self.add_files_btn.pack(side='left', padx=(0, 8))
        self.add_folder_btn = ttk.Button(actions, text='Выбрать папку', command=self.add_folder)
        self.add_folder_btn.pack(side='left', padx=(0, 8))
        self.clear_btn = ttk.Button(actions, text='Очистить список', command=self.clear)
        self.clear_btn.pack(side='left')
        ttk.Label(frame, textvariable=self.count).pack(anchor='w')
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill='both', expand=True, pady=(5, 12))
        self.listbox = tk.Listbox(list_frame, selectmode='extended', font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        output_frame = ttk.LabelFrame(frame, text='Сохранение JPEG', padding=10)
        output_frame.pack(fill='x')
        ttk.Entry(output_frame, textvariable=self.output).pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.browse_btn = ttk.Button(output_frame, text='Обзор…', command=self.browse_output)
        self.browse_btn.pack(side='left')
        settings = ttk.Frame(frame)
        settings.pack(fill='x', pady=10)
        ttk.Label(settings, text='Качество JPEG (80–100):').pack(side='left')
        ttk.Spinbox(settings, textvariable=self.quality, from_=80, to=100, width=5).pack(side='left', padx=(9, 18))
        ttk.Checkbutton(settings, text='Сохранять структуру подпапок', variable=self.keep_structure).pack(side='left')
        buttons = ttk.Frame(frame)
        buttons.pack(fill='x', pady=(2, 8))
        self.start_btn = ttk.Button(buttons, text='Конвертировать в JPEG', command=self.start)
        self.start_btn.pack(side='left', padx=(0, 8))
        self.stop_btn = ttk.Button(buttons, text='Остановить', command=self.stop, state='disabled')
        self.stop_btn.pack(side='left')
        self.progress = ttk.Progressbar(frame, mode='determinate', maximum=100)
        self.progress.pack(fill='x', pady=(0, 5))
        ttk.Label(frame, textvariable=self.status, wraplength=730).pack(anchor='w')
        ttk.Label(frame, text='Исходные CR3 не изменяются. Существующие JPEG не перезаписываются.', foreground='#555555').pack(anchor='w', pady=(8, 0))

    def add_files(self):
        paths = filedialog.askopenfilenames(title='Выберите CR3', filetypes=[('Canon RAW', '*.cr3'), ('Все файлы', '*.*')])
        if paths:
            self.base_folder = None
            self.append_paths([Path(x) for x in paths])

    def add_folder(self):
        folder = filedialog.askdirectory(title='Выберите папку с CR3')
        if folder:
            self.base_folder = Path(folder)
            paths = sorted(p for p in self.base_folder.rglob('*') if p.is_file() and p.suffix.lower() == '.cr3')
            self.append_paths(paths)
            if not paths:
                messagebox.showinfo('Файлы не найдены', 'В выбранной папке нет файлов .CR3.')

    def append_paths(self, paths):
        existing = {str(p).casefold() for p in self.files}
        for p in paths:
            if p.suffix.lower() != '.cr3' or str(p).casefold() in existing:
                continue
            self.files.append(p)
            self.listbox.insert('end', str(p))
            existing.add(str(p).casefold())
        self.count.set(f'Файлов: {len(self.files)}')
        self.status.set('Готово к конвертации.')

    def clear(self):
        self.files.clear()
        self.base_folder = None
        self.listbox.delete(0, 'end')
        self.count.set('Файлов: 0')
        self.progress['value'] = 0
        self.status.set('Список очищен.')

    def browse_output(self):
        folder = filedialog.askdirectory(title='Папка для JPEG')
        if folder:
            self.output.set(folder)

    def set_busy(self, busy):
        for widget in (self.add_files_btn, self.add_folder_btn, self.clear_btn, self.browse_btn, self.start_btn):
            widget.configure(state='disabled' if busy else 'normal')
        self.stop_btn.configure(state='normal' if busy else 'disabled')

    def start(self):
        if BACKEND_ERROR:
            messagebox.showerror('Ошибка', 'Отсутствуют rawpy или Pillow.')
            return
        if not self.files:
            messagebox.showwarning('Нет файлов', 'Добавьте хотя бы один файл CR3.')
            return
        try:
            quality = int(self.quality.get())
            if quality < 80 or quality > 100:
                raise ValueError()
        except (ValueError, tk.TclError):
            messagebox.showwarning('Качество', 'Укажите целое число от 80 до 100.')
            return
        output = Path(self.output.get().strip()).expanduser()
        if not str(self.output.get()).strip():
            messagebox.showwarning('Папка', 'Укажите папку для сохранения.')
            return
        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror('Ошибка папки', str(exc))
            return
        self.cancel.clear()
        self.progress['value'] = 0
        self.set_busy(True)
        self.status.set('Обработка…')
        args = (list(self.files), output, quality, self.base_folder, self.keep_structure.get())
        self.worker = threading.Thread(target=self.convert, args=args, daemon=True)
        self.worker.start()

    def stop(self):
        self.cancel.set()
        self.status.set('Остановка после текущего файла…')

    @staticmethod
    def unique_path(path):
        candidate = path
        index = 1
        while candidate.exists():
            candidate = path.with_name(f'{path.stem}_{index}{path.suffix}')
            index += 1
        return candidate

    def convert(self, files, output, quality, base_folder, keep_structure):
        good, errors = 0, []
        log_path = output / 'cr3_conversion_errors.txt'
        for idx, src in enumerate(files, 1):
            if self.cancel.is_set():
                break
            try:
                dest_dir = output
                if keep_structure and base_folder:
                    dest_dir = output / src.relative_to(base_folder).parent
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = self.unique_path(dest_dir / (src.stem + '.jpg'))
                # LibRaw demosaicing and camera-aware white balance; sRGB output.
                with rawpy.imread(str(src)) as raw:
                    rgb = raw.postprocess(use_camera_wb=True, output_color=rawpy.ColorSpace.sRGB,
                                          output_bps=8, no_auto_bright=True)
                with Image.fromarray(rgb) as img:
                    img.save(str(dest), 'JPEG', quality=quality, subsampling=0, optimize=True)
                good += 1
            except Exception as exc:
                errors.append(f'{src}\n  {type(exc).__name__}: {exc}\n')
            self.events.put(('progress', idx, len(files), src.name))
        if errors:
            try:
                log_path.write_text('\n'.join(errors), encoding='utf-8')
            except OSError:
                pass
        self.events.put(('done', good, len(errors), self.cancel.is_set(), str(output)))

    def poll(self):
        try:
            while True:
                evt = self.events.get_nowait()
                if evt[0] == 'progress':
                    _, idx, total, filename = evt
                    self.progress['value'] = idx / total * 100
                    self.status.set(f'{idx}/{total}: {filename}')
                elif evt[0] == 'done':
                    _, good, bad, cancelled, output = evt
                    self.set_busy(False)
                    msg = f'Конвертировано: {good}. Ошибок: {bad}.'
                    if cancelled:
                        msg += ' Остановлено пользователем.'
                    if bad:
                        msg += '\nПодробности: cr3_conversion_errors.txt в выходной папке.'
                    self.status.set(msg.replace('\n', ' '))
                    messagebox.showinfo('Конвертация завершена', msg + f'\nПапка: {output}')
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

if __name__ == '__main__':
    root = tk.Tk()
    try:
        ttk.Style().theme_use('vista' if os.name == 'nt' else 'clam')
    except tk.TclError:
        pass
    App(root)
    root.mainloop()
