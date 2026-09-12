r"""
Простой просмотрщик PDF для Windows.

Как запустить:
    1. Установи Python (если ещё не установлен): https://www.python.org/downloads/
       При установке обязательно поставь галочку "Add Python to PATH".
    2. Установи библиотеку для чтения PDF (один раз, в командной строке):
           pip install PyMuPDF
    3. Запусти программу:
           python pdf_viewer.py
       Или просто дважды кликни на файл pdf_viewer.py, если Python
       настроен на запуск .py файлов по двойному клику.

Как превратить это в отдельный .exe файл (не обязательно, но удобно):
    1. Установи pyinstaller (один раз):
           pip install pyinstaller
    2. Собери .exe (одна команда, всё автоматически):
           pyinstaller --onefile --windowed --name "PDF Просмотрщик" pdf_viewer.py
    3. Готовый файл появится в папке dist\PDF Просмотрщик.exe
       Его можно перенести куда угодно и запускать без Python.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import pymupdf as fitz  # PyMuPDF (актуальное имя модуля)
import sys
import os


class PdfViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Просмотрщик")
        self.root.geometry("900x700")
        self.root.configure(bg="#2b2b2b")

        self.doc = None
        self.current_page = 0
        self.zoom = 1.3
        self.photo_image = None  # держим ссылку, чтобы Tkinter не удалил картинку

        # Для выделения текста мышкой (как в Word)
        self.page_words = []           # список слов текущей страницы: (x0, y0, x1, y1, текст)
        self.selection_start_idx = None
        self.selection_end_idx = None
        self.selecting = False

        self._build_toolbar()
        self._build_canvas()
        self._bind_shortcuts()

        # Если файл передан как аргумент (например, через "Открыть с помощью") - сразу открываем.
        if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
            self.open_pdf(sys.argv[1])

    def _build_toolbar(self):
        toolbar = tk.Frame(self.root, bg="#3c3c3c", height=44)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        btn_style = {
            "bg": "#4a4a4a", "fg": "white", "activebackground": "#5a5a5a",
            "activeforeground": "white", "bd": 0, "padx": 12, "pady": 6,
            "font": ("Segoe UI", 10)
        }

        tk.Button(toolbar, text="Открыть...", command=self.choose_file, **btn_style).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(toolbar, text="◀ Назад", command=self.prev_page, **btn_style).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(toolbar, text="Вперёд ▶", command=self.next_page, **btn_style).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(toolbar, text="−", command=self.zoom_out, **btn_style).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(toolbar, text="+", command=self.zoom_in, **btn_style).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(toolbar, text="Копировать", command=self.copy_selection, **btn_style).pack(side=tk.LEFT, padx=4, pady=4)

        self.page_label = tk.Label(toolbar, text="Файл не открыт", bg="#3c3c3c", fg="white", font=("Segoe UI", 10))
        self.page_label.pack(side=tk.LEFT, padx=16)

    def _build_canvas(self):
        container = tk.Frame(self.root, bg="#2b2b2b")
        container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(container, bg="#1e1e1e", highlightthickness=0)
        v_scroll = tk.Scrollbar(container, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scroll = tk.Scrollbar(container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _bind_shortcuts(self):
        self.root.bind("<Left>", lambda e: self.prev_page())
        self.root.bind("<Right>", lambda e: self.next_page())
        self.root.bind("<Prior>", lambda e: self.prev_page())   # Page Up
        self.root.bind("<Next>", lambda e: self.next_page())    # Page Down
        self.root.bind("<Control-o>", lambda e: self.choose_file())
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-c>", lambda e: self.copy_selection())
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self._on_selection_start)
        self.canvas.bind("<B1-Motion>", self._on_selection_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_selection_end)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Выберите PDF файл",
            filetypes=[("PDF файлы", "*.pdf")]
        )
        if path:
            self.open_pdf(path)

    def open_pdf(self, path):
        try:
            self.doc = fitz.open(path)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{e}")
            return

        self.current_page = 0
        self.root.title(f"PDF Просмотрщик — {os.path.basename(path)}")
        self.render_page()

    def render_page(self):
        if not self.doc:
            return

        page = self.doc.load_page(self.current_page)
        matrix = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=matrix)

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.photo_image = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo_image)
        self.canvas.configure(scrollregion=(0, 0, pix.width, pix.height))

        # Извлекаем слова страницы с координатами (для выделения текста мышкой).
        # get_text("words") возвращает слова уже в порядке чтения (блок, строка, слово).
        raw_words = page.get_text("words")
        self.page_words = [
            (w[0] * self.zoom, w[1] * self.zoom, w[2] * self.zoom, w[3] * self.zoom, w[4])
            for w in raw_words
        ]
        self.selection_start_idx = None
        self.selection_end_idx = None

        self.page_label.config(
            text=f"Страница {self.current_page + 1} из {len(self.doc)}   ·   Масштаб {int(self.zoom * 100)}%"
        )

    def next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.render_page()

    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.render_page()

    def zoom_in(self):
        if self.doc:
            self.zoom = min(self.zoom + 0.2, 4.0)
            self.render_page()

    def zoom_out(self):
        if self.doc:
            self.zoom = max(self.zoom - 0.2, 0.4)
            self.render_page()

    # --- Выделение текста мышкой (как в Word) ---

    def _find_word_index_at(self, x, y):
        """Находит индекс ближайшего слова к точке (x, y) в координатах холста."""
        if not self.page_words:
            return None
        best_idx = 0
        best_dist = None
        for i, (x0, y0, x1, y1, _) in enumerate(self.page_words):
            if x0 <= x <= x1 and y0 <= y <= y1:
                return i
            dx = max(x0 - x, 0, x - x1)
            dy = max(y0 - y, 0, y - y1)
            dist = dx * dx + dy * dy
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_idx = i
        return best_idx

    def _on_selection_start(self, event):
        if not self.doc or not self.page_words:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        idx = self._find_word_index_at(x, y)
        self.selection_start_idx = idx
        self.selection_end_idx = idx
        self.selecting = True
        self._draw_selection_highlights()

    def _on_selection_drag(self, event):
        if not self.selecting or not self.doc or not self.page_words:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        idx = self._find_word_index_at(x, y)
        self.selection_end_idx = idx
        self._draw_selection_highlights()

    def _on_selection_end(self, event):
        self.selecting = False

    def _draw_selection_highlights(self):
        self.canvas.delete("selection_highlight")
        if self.selection_start_idx is None or self.selection_end_idx is None:
            return
        lo = min(self.selection_start_idx, self.selection_end_idx)
        hi = max(self.selection_start_idx, self.selection_end_idx)
        for i in range(lo, hi + 1):
            x0, y0, x1, y1, _ = self.page_words[i]
            self.canvas.create_rectangle(
                x0, y0, x1, y1,
                fill="#4A90D9", outline="",
                stipple="gray50",
                tags="selection_highlight"
            )

    def copy_selection(self):
        if self.selection_start_idx is None or self.selection_end_idx is None:
            return
        lo = min(self.selection_start_idx, self.selection_end_idx)
        hi = max(self.selection_start_idx, self.selection_end_idx)
        text = " ".join(w[4] for w in self.page_words[lo:hi + 1])
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()  # чтобы буфер обмена сохранился, даже если окно потеряет фокус

        # Кратко показываем подтверждение в статусной строке
        old_text = self.page_label.cget("text")
        self.page_label.config(text="Скопировано в буфер обмена ✓")
        self.root.after(1200, lambda: self.page_label.config(text=old_text))


if __name__ == "__main__":
    root = tk.Tk()
    app = PdfViewerApp(root)
    root.mainloop()
