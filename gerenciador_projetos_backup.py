import os
import sys
import shutil
import datetime
import subprocess
import threading
import queue
import json
import calendar
import re
import uuid
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import ctypes

def round_window_corners(window):
    """Aplica cantos arredondados nativos no Windows 11 usando a DWM API"""
    if sys.platform != "win32":
        return
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            hwnd = window.winfo_id()
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_ROUND = 2
        dwmapi = ctypes.WinDLL("dwmapi")
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
            ctypes.sizeof(ctypes.c_int)
        )
    except Exception:
        pass

# ==========================================
# CONFIGURAÇÕES DE CORES E ESTILO (SILENT GUARDIAN THEME)
# ==========================================
COLOR_BG_DARK = "#131315"      # background
COLOR_BG_CARD = "#201f21"      # surface-container
COLOR_BG_INPUT = "#0e0e10"     # surface-container-lowest
COLOR_TEXT_PRIMARY = "#e5e1e4" # on-background / on-surface
COLOR_TEXT_MUTED = "#bbcac0"   # on-surface-variant
COLOR_ACCENT = "#50dea5"       # primary
COLOR_ACCENT_HOVER = "#00b37e" # primary-container (darker for hover on light text, or reverse depending on use)
COLOR_WARNING = "#ffb86d"      # secondary
COLOR_DANGER = "#ffb4ab"       # error
COLOR_BORDER = "#3c4a42"       # outline-variant

# Estrutura padrão de pastas para o criador de projetos
DEFAULT_STRUCTURE = [
    "01 - Documentos",
    "02 - Edição (Arquivos de Salvamento dos PGMs)",
    "03 - Material",
    "03 - Material/Audio/SFX/Foley",
    "03 - Material/Audio/Gravadores/A001",
    "03 - Material/Audio/Gravadores/A002",
    "03 - Material/Audio/Gravadores/B001",
    "03 - Material/Audio/Gravadores/B002",
    "03 - Material/Audio/Trilha",
    "03 - Material/Video/A001/B001",
    "03 - Material/Foto/A001",
    "03 - Material/Foto/A002",
    "03 - Material/Foto/B001",
    "03 - Material/Foto/B002",
    "03 - Material/Graph",
    "03 - Material/Motion",
    "04 - Renders"
]

# Tradução simplificada para o Datepicker
MONTHS_PT = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

def format_size(num_bytes):
    """Retorna tamanho formatado legível (B, KB, MB, GB, TB)"""
    try:
        val = float(num_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(val) < 1024.0:
                return f"{val:3.1f} {unit}"
            val /= 1024.0
        return f"{val:.1f} PB"
    except Exception:
        return f"{num_bytes} B"

# ==========================================
# WIDGET CUSTOMIZADO: BOTÃO COM HOVER DINÂMICO
# ==========================================
class HoverButton(tk.Button):
    """Botão customizado com suporte a hover dinâmico e design flat premium"""
    def __init__(self, master, hover_bg, hover_fg, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.default_bg = self["bg"]
        self.default_fg = self["fg"]
        self.hover_bg = hover_bg
        self.hover_fg = hover_fg
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self.config(bg=self.hover_bg, fg=self.hover_fg)

    def on_leave(self, e):
        self.config(bg=self.default_bg, fg=self.default_fg)


# ==========================================
# WIDGET CUSTOMIZADO: BOTÃO ARREDONDADO COM CANVASES
# ==========================================
class RoundedButton(tk.Canvas):
    """Botão customizado com cantos arredondados usando Canvas para evitar dependência do OS"""
    def __init__(self, master, text, bg, fg, hover_bg, hover_fg, command=None, radius=8, font=("Segoe UI", 9, "bold"), height=40, **kwargs):
        # canvas bg matches parent frame background
        super().__init__(master, bg=master["bg"] if "bg" in master.keys() else COLOR_BG_DARK, highlightthickness=0, bd=0, cursor="hand2")
        self.text = text
        self.default_bg = bg
        self.default_fg = fg
        self.hover_bg = hover_bg
        self.hover_fg = hover_fg
        self.command = command
        self.radius = radius
        self.font = font
        self.height = height
        
        self.current_bg = bg
        self.current_fg = fg
        self.state = "normal"
        
        self.configure(height=height)
        
        self.bind("<Configure>", self.draw)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)

    def config(self, **kwargs):
        # Mapeia opções padrões de botões para o Canvas redesenhar
        if "state" in kwargs:
            self.state = kwargs["state"]
            if self.state == "disabled":
                self.current_bg = COLOR_BORDER
                self.current_fg = COLOR_TEXT_MUTED
            else:
                self.current_bg = self.default_bg
                self.current_fg = self.default_fg
            self.draw()
        if "bg" in kwargs:
            self.default_bg = kwargs["bg"]
            self.current_bg = kwargs["bg"]
            self.draw()
        if "text" in kwargs:
            self.text = kwargs["text"]
            self.draw()
        # Repassa outras opções suportadas para o canvas nativo
        canvas_keys = ["width", "height", "cursor"]
        canvas_args = {k: v for k, v in kwargs.items() if k in canvas_keys}
        if canvas_args:
            super().configure(**canvas_args)
            self.draw()

    def draw(self, event=None):
        self.delete("all")
        if event:
            w = event.width
            h = event.height
        else:
            w = self.winfo_width()
            h = self.winfo_height()
        r = self.radius
        
        if w <= 1: w = 200
        if h <= 1: h = self.height
        
        # Desenha cantos arredondados usando arcos
        self.create_arc(0, 0, 2*r, 2*r, start=90, extent=90, fill=self.current_bg, outline=self.current_bg)
        self.create_arc(w-2*r, 0, w, 2*r, start=0, extent=90, fill=self.current_bg, outline=self.current_bg)
        self.create_arc(w-2*r, h-2*r, w, h, start=270, extent=90, fill=self.current_bg, outline=self.current_bg)
        self.create_arc(0, h-2*r, 2*r, h, start=180, extent=90, fill=self.current_bg, outline=self.current_bg)
        
        # Preenche os retângulos central e horizontal
        self.create_rectangle(r, 0, w-r, h, fill=self.current_bg, outline=self.current_bg)
        self.create_rectangle(0, r, w, h-r, fill=self.current_bg, outline=self.current_bg)
        
        # Insere o rótulo de texto centralizado
        self.create_text(w/2, h/2, text=self.text, fill=self.current_fg, font=self.font, justify="center")

    def on_enter(self, e):
        if self.state == "disabled": return
        self.current_bg = self.hover_bg
        self.current_fg = self.hover_fg
        self.draw()

    def on_leave(self, e):
        if self.state == "disabled": return
        self.current_bg = self.default_bg
        self.current_fg = self.default_fg
        self.draw()

    def on_press(self, e):
        if self.state == "disabled": return
        # Efeito de clique (escurece levemente o background)
        self.draw()

    def on_release(self, e):
        if self.state == "disabled": return
        if self.command:
            self.command()


# ==========================================
# WIDGET: DATEPICKER MODAL CUSTOMIZADO
# ==========================================
class CalendarDialog(tk.Toplevel):
    """Modal de calendário dark sem dependências externas"""
    def __init__(self, parent, day_var, month_var, year_var):
        super().__init__(parent)
        self.parent = parent
        self.day_var = day_var
        self.month_var = month_var
        self.year_var = year_var

        self.title("Selecionar Data")
        self.geometry("320x360")
        self.resizable(False, False)
        self.configure(bg=COLOR_BG_DARK)
        round_window_corners(self)
        self.transient(parent)
        self.grab_set()

        # Determina a data inicial baseada nos campos ou data atual
        try:
            self.current_day = int(day_var.get())
            self.current_month = int(month_var.get())
            self.current_year = int(year_var.get())
        except ValueError:
            now = datetime.datetime.now()
            self.current_day = now.day
            self.current_month = now.month
            self.current_year = now.year

        self.build_widgets()

    def build_widgets(self):
        # Header com Mês e Ano + Botões de Navegação (Usando < e > seguros)
        nav_frame = tk.Frame(self, bg=COLOR_BG_CARD, pady=8)
        nav_frame.pack(fill=tk.X)

        btn_prev = HoverButton(
            nav_frame, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="<", bg=COLOR_BG_DARK, fg=COLOR_TEXT_PRIMARY, bd=0, 
            font=("Segoe UI", 10, "bold"), width=4, command=self.prev_month
        )
        btn_prev.pack(side=tk.LEFT, padx=10)

        self.lbl_month_year = tk.Label(
            nav_frame, text="", bg=COLOR_BG_CARD, fg=COLOR_ACCENT,
            font=("Segoe UI", 11, "bold"), width=16
        )
        self.lbl_month_year.pack(side=tk.LEFT, expand=True, fill=tk.X)

        btn_next = HoverButton(
            nav_frame, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text=">", bg=COLOR_BG_DARK, fg=COLOR_TEXT_PRIMARY, bd=0, 
            font=("Segoe UI", 10, "bold"), width=4, command=self.next_month
        )
        btn_next.pack(side=tk.RIGHT, padx=10)

        # Container dos dias da semana
        week_frame = tk.Frame(self, bg=COLOR_BG_DARK, pady=6)
        week_frame.pack(fill=tk.X)
        days_headers = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
        for d in days_headers:
            lbl = tk.Label(week_frame, text=d, bg=COLOR_BG_DARK, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8, "bold"), width=5)
            lbl.pack(side=tk.LEFT, expand=True)

        # Grid de dias do calendário
        self.grid_frame = tk.Frame(self, bg=COLOR_BG_DARK)
        self.grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.draw_days()

    def draw_days(self):
        # Limpa o grid anterior
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        self.lbl_month_year.config(text=f"{MONTHS_PT[self.current_month]} {self.current_year}")

        # Obtém matriz de dias do mês
        cal_matrix = calendar.monthcalendar(self.current_year, self.current_month)

        for row_idx, week in enumerate(cal_matrix):
            for col_idx, day in enumerate(week):
                if day == 0:
                    # Espaço vazio fora do mês corrente
                    lbl_empty = tk.Label(self.grid_frame, bg=COLOR_BG_DARK, width=4, height=1)
                    lbl_empty.grid(row=row_idx, column=col_idx, padx=2, pady=2, sticky="nsew")
                else:
                    # Estilo diferenciado para o dia selecionado atualmente
                    is_selected = (day == self.current_day)
                    bg_color = COLOR_ACCENT if is_selected else COLOR_BG_CARD
                    fg_color = "#ffffff" if is_selected else COLOR_TEXT_PRIMARY

                    btn_day = HoverButton(
                        self.grid_frame, hover_bg=COLOR_ACCENT_HOVER, hover_fg="#ffffff",
                        text=str(day), bg=bg_color, fg=fg_color, bd=0,
                        font=("Segoe UI", 9, "bold" if is_selected else "normal"),
                        width=4, height=1, command=lambda d=day: self.select_day(d)
                    )
                    btn_day.grid(row=row_idx, column=col_idx, padx=2, pady=2, sticky="nsew")

        # Ajusta distribuição de tamanho do grid uniformemente
        for i in range(7):
            self.grid_frame.columnconfigure(i, weight=1)
        for i in range(len(cal_matrix)):
            self.grid_frame.rowconfigure(i, weight=1)

    def prev_month(self):
        self.current_month -= 1
        if self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        self.draw_days()

    def next_month(self):
        self.current_month += 1
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        self.draw_days()

    def select_day(self, day):
        self.day_var.set(f"{day:02d}")
        self.month_var.set(f"{self.current_month:02d}")
        self.year_var.set(str(self.current_year))
        self.grab_release()
        self.destroy()


# ==========================================
# WIDGET: PAINEL COM SCROLLBAR VERTICAL
# ==========================================
class ScrollablePanel(tk.Frame):
    """
    Painel conteiner com barra de rolagem vertical para permitir navegação
    fluida em telas com resoluções menores ou altas escalas de DPI.
    """
    def __init__(self, parent, bg=COLOR_BG_DARK, *args, **kwargs):
        super().__init__(parent, bg=bg, *args, **kwargs)
        self.bg = bg

        self.canvas = tk.Canvas(self, bg=bg, bd=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview, style="Vertical.TScrollbar")
        self.content = tk.Frame(self.canvas, bg=bg)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas_window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Suporte universal à rolagem do mouse quando o ponteiro estiver sobre o painel ou qualquer widget filho
        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_mousewheel, add="+")
        self.bind_all("<Button-5>", self._on_mousewheel, add="+")

    def _on_content_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # Sincroniza a largura do frame interno com a largura visível do canvas
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _is_descendant(self, widget):
        if widget is None:
            return False
        return widget == self or (isinstance(widget, tk.Misc) and str(widget).startswith(str(self) + "."))

    def _on_mousewheel(self, event):
        try:
            if not self.winfo_ismapped():
                return
            widget = self.winfo_containing(event.x_root, event.y_root)
            if widget and self._is_descendant(widget):
                if event.num == 4:
                    self.canvas.yview_scroll(-2, "units")
                elif event.num == 5:
                    self.canvas.yview_scroll(2, "units")
                elif event.delta:
                    # Windows (delta ~120) / macOS (delta ~1)
                    if abs(event.delta) >= 120:
                        step = -1 * int(event.delta / 120)
                    else:
                        step = -1 if event.delta > 0 else 1
                    self.canvas.yview_scroll(step, "units")
        except Exception:
            pass


# ==========================================
# APLICATIVO PRINCIPAL (APP FRAMEWORK)
# ==========================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Evitar sobreposição de ícone pelo Python na barra de tarefas (Windows)
        if sys.platform == "win32":
            try:
                myappid = 'mpfolders.workflowbackup.app.1'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception:
                pass

        # Define caminho do arquivo de configurações local (portabilidade em .exe)
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_filepath = os.path.join(base_dir, "config_gerenciador.json")

        # Variáveis de Estado e carregamento de config
        self.custom_folders = []
        self.clipboard_branch = None
        self.clipboard_root_name = None
        self.load_config()  # Carrega as pastas, geometrias e sashes salvas anteriormente

        self.title("MPFolders v1.0 - Workflow & Backup")
        self.geometry(self.window_geometry)
        self.configure(bg=COLOR_BG_DARK)
        self.minsize(980, 680)
        round_window_corners(self)
        
        self.bind("<Configure>", self._on_configure)
        
        if self.window_state in ("maximized", "zoomed"):
            self.after(50, lambda: self.state("zoomed"))
        elif self.window_state in ("minimized", "iconic"):
            self.after(50, lambda: self.iconify())
        
        # Carregar ícone da janela (se disponível)
        if getattr(sys, 'frozen', False):
            asset_dir = sys._MEIPASS
        else:
            asset_dir = os.path.dirname(os.path.abspath(__file__))
            
        icon_path = os.path.join(asset_dir, 'icon.ico')
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        # Fila para comunicação de threads (evita travamento da GUI)
        self.log_queue = queue.Queue()

        self.setup_styles()
        self.build_ui()
        self.check_queue_loop()

        # Restaura a posição das sashes após a janela estar totalmente visível e desenhada
        self.after(200, self.restore_sashes)

        # Vincula o fechamento da janela ao salvamento de dados finais
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        # Configurações globais de estilos customizados para simular app moderno
        style.configure(".", background=COLOR_BG_DARK, foreground=COLOR_TEXT_PRIMARY)
        style.configure("TFrame", background=COLOR_BG_DARK)
        
        # Abas (Notebook)
        style.configure("TNotebook", background=COLOR_BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=COLOR_BG_CARD, foreground=COLOR_TEXT_MUTED, 
                        padding=[15, 6], font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", 
                  background=[("selected", COLOR_ACCENT), ("active", COLOR_BORDER)],
                  foreground=[("selected", "#ffffff"), ("active", COLOR_TEXT_PRIMARY)])

        # LabelFrames
        style.configure("TLabelframe", background=COLOR_BG_CARD, foreground=COLOR_ACCENT, 
                        borderwidth=1, bordercolor=COLOR_BORDER)
        style.configure("TLabelframe.Label", background=COLOR_BG_CARD, foreground=COLOR_ACCENT, 
                        font=("Segoe UI", 10, "bold"))

        # Labels de base
        style.configure("TLabel", background=COLOR_BG_CARD, foreground=COLOR_TEXT_PRIMARY)
        style.configure("Header.TLabel", background=COLOR_BG_DARK, foreground=COLOR_ACCENT, 
                        font=("Segoe UI", 14, "bold"))
        style.configure("Sub.TLabel", background=COLOR_BG_DARK, foreground=COLOR_TEXT_MUTED, 
                        font=("Segoe UI", 9))

        # Estilo para Comboboxes (corrige bug de fundo branco no modo readonly)
        style.configure("TCombobox", 
                        fieldbackground=COLOR_BG_INPUT, 
                        background=COLOR_BG_DARK, 
                        foreground=COLOR_TEXT_PRIMARY,
                        arrowcolor=COLOR_TEXT_PRIMARY,
                        bordercolor=COLOR_BORDER,
                        lightcolor=COLOR_BG_DARK,
                        darkcolor=COLOR_BG_DARK)
        style.map("TCombobox", 
                  fieldbackground=[("readonly", COLOR_BG_INPUT)],
                  foreground=[("readonly", COLOR_TEXT_PRIMARY)])

        # Barra de Rolagem Vertical (Dark)
        style.configure("Vertical.TScrollbar",
                        background=COLOR_BG_CARD,
                        troughcolor=COLOR_BG_DARK,
                        bordercolor=COLOR_BG_DARK,
                        arrowcolor=COLOR_TEXT_MUTED)
        style.map("Vertical.TScrollbar",
                  background=[("active", COLOR_ACCENT), ("pressed", COLOR_ACCENT_HOVER)],
                  arrowcolor=[("active", COLOR_ACCENT)])

    def build_ui(self):
        # Header Superior do App
        header_frame = tk.Frame(self, bg=COLOR_BG_DARK, pady=6, padx=15)
        header_frame.pack(fill=tk.X)
        
        lbl_title = ttk.Label(header_frame, text="MPFolders v1", style="Header.TLabel")
        lbl_title.pack(anchor="w")
        
        lbl_sub = ttk.Label(header_frame, text="Workflow & Projetos - Ferramenta portátil integrada para automação e segurança.", style="Sub.TLabel")
        lbl_sub.pack(anchor="w")

        lbl_sub = ttk.Label(header_frame, text="Paulo Fernando de M. E. @ Gandget S&P © Todos os direitos reservados ", style="Sub.TLabel")
        lbl_sub.pack(anchor="w")

        # Container Principal de Abas
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # Abas Individuais
        self.tab_creator = tk.Frame(self.notebook, bg=COLOR_BG_DARK)
        self.tab_cleaner = tk.Frame(self.notebook, bg=COLOR_BG_DARK)
        self.tab_backup = tk.Frame(self.notebook, bg=COLOR_BG_DARK)
        self.tab_renamer = tk.Frame(self.notebook, bg=COLOR_BG_DARK)
        self.tab_card_copy = tk.Frame(self.notebook, bg=COLOR_BG_DARK)

        self.notebook.add(self.tab_creator, text=" Criar Estrutura de Projeto ")
        self.notebook.add(self.tab_cleaner, text=" Limpar Pastas Vazias / Lixo ")
        self.notebook.add(self.tab_backup, text=" Backup Incremental Seguro ")
        self.notebook.add(self.tab_renamer, text=" Renomeador Incremental ")
        self.notebook.add(self.tab_card_copy, text=" Copia do Cartão ")

        # Inicialização das Interfaces de cada aba
        self.init_tab_creator()
        self.init_tab_cleaner()
        self.init_tab_backup()
        self.init_tab_renamer()
        self.init_tab_card_copy()

    # =========================================================================
    # PERSISTÊNCIA DAS CONFIGURAÇÕES DO USUÁRIO
    # =========================================================================
    def load_config(self):
        """Carrega do arquivo json local, se houver falhas inicia com a estrutura original"""
        try:
            if os.path.exists(self.config_filepath):
                with open(self.config_filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "custom_folders" in data and "templates" not in data:
                        self.templates = {"Padrão": data["custom_folders"]}
                        self.active_template = "Padrão"
                    else:
                        self.templates = data.get("templates", {"Padrão": list(DEFAULT_STRUCTURE)})
                        self.active_template = data.get("active_template", "Padrão")
                    
                    self.window_state = data.get("window_state", "normal")
                    self.window_geometry = data.get("window_geometry", "1024x768")
                    self.sash_creator = data.get("sash_creator", 410)
                    self.sash_cleaner = data.get("sash_cleaner", 370)
                    self.sash_backup = data.get("sash_backup", 380)
                    self.sash_renamer = data.get("sash_renamer", 390)
                    self.sash_card_copy = data.get("sash_card_copy", 390)
            else:
                self.templates = {"Padrão": list(DEFAULT_STRUCTURE)}
                self.active_template = "Padrão"
                self.window_state = "normal"
                self.window_geometry = "1024x768"
                self.sash_creator = 410
                self.sash_cleaner = 370
                self.sash_backup = 380
                self.sash_renamer = 390
                self.sash_card_copy = 390
        except Exception:
            self.templates = {"Padrão": list(DEFAULT_STRUCTURE)}
            self.active_template = "Padrão"
            self.window_state = "normal"
            self.window_geometry = "1024x768"
            self.sash_creator = 410
            self.sash_cleaner = 370
            self.sash_backup = 380
            self.sash_renamer = 390
            self.sash_card_copy = 390

        self.last_normal_geometry = self.window_geometry
        self.custom_folders = list(self.templates.get(self.active_template, list(DEFAULT_STRUCTURE)))

    def _on_configure(self, event):
        if event.widget == self:
            try:
                st = self.state()
                if st == "normal":
                    self.last_normal_geometry = self.geometry()
            except Exception:
                pass

    def save_config(self):
        """Salva a lista atualizada de pastas no arquivo de configuração"""
        try:
            self.templates[self.active_template] = list(self.custom_folders)
            
            # Tenta pegar as posições das sashes
            try:
                sash_cr = self.paned_creator.sash_coord(0)[0]
            except Exception:
                sash_cr = 410
            try:
                sash_cl = self.paned_cleaner.sash_coord(0)[0]
            except Exception:
                sash_cl = 370
            try:
                sash_bk = self.paned_backup.sash_coord(0)[0]
            except Exception:
                sash_bk = 380
            try:
                sash_rn = self.paned_renamer.sash_coord(0)[0]
            except Exception:
                sash_rn = 390
            try:
                sash_cc = self.paned_card_copy.sash_coord(0)[0]
            except Exception:
                sash_cc = 390

            st = "normal"
            try:
                s = self.state()
                if s == "zoomed":
                    st = "maximized"
                elif s == "iconic":
                    st = "minimized"
                else:
                    st = "normal"
                    self.last_normal_geometry = self.geometry()
            except Exception:
                pass
            self.window_state = st

            data = {
                "templates": self.templates,
                "active_template": self.active_template,
                "window_state": self.window_state,
                "window_geometry": getattr(self, "last_normal_geometry", self.geometry()),
                "sash_creator": sash_cr,
                "sash_cleaner": sash_cl,
                "sash_backup": sash_bk,
                "sash_renamer": sash_rn,
                "sash_card_copy": sash_cc
            }
            temp_cfg = f"{self.config_filepath}.{os.getpid()}.tmp"
            with open(temp_cfg, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(temp_cfg, self.config_filepath)
        except Exception as e:
            print(f"Falha ao salvar config local: {e}")
            try:
                temp_cfg = f"{self.config_filepath}.{os.getpid()}.tmp"
                if os.path.exists(temp_cfg):
                    os.remove(temp_cfg)
            except Exception:
                pass

    def restore_sashes(self):
        """Restaura as coordenadas das divisões PanedWindow de forma segura e atrasada"""
        try:
            self.update_idletasks()
            if hasattr(self, 'paned_creator') and hasattr(self, 'sash_creator'):
                self.paned_creator.sash_place(0, self.sash_creator, 0)
            if hasattr(self, 'paned_cleaner') and hasattr(self, 'sash_cleaner'):
                self.paned_cleaner.sash_place(0, self.sash_cleaner, 0)
            if hasattr(self, 'paned_backup') and hasattr(self, 'sash_backup'):
                self.paned_backup.sash_place(0, self.sash_backup, 0)
            if hasattr(self, 'paned_renamer') and hasattr(self, 'sash_renamer'):
                self.paned_renamer.sash_place(0, self.sash_renamer, 0)
            if hasattr(self, 'paned_card_copy') and hasattr(self, 'sash_card_copy'):
                self.paned_card_copy.sash_place(0, self.sash_card_copy, 0)
        except Exception:
            pass

    def on_close(self):
        """Método executado antes do encerramento final"""
        self.save_config()
        self.destroy()

    # =========================================================================
    # TAB 1: CRIADOR DE PROJETOS
    # =========================================================================
    def init_tab_creator(self):
        # Utiliza PanedWindow horizontal para permitir redimensionar as divisões internas
        self.paned_creator = tk.PanedWindow(self.tab_creator, orient=tk.HORIZONTAL, bg=COLOR_BORDER, bd=0, sashwidth=6, sashrelief="flat", showhandle=True, handlesize=8, handlepad=8)
        self.paned_creator.pack(fill=tk.BOTH, expand=True)

        left_panel = ScrollablePanel(self.paned_creator, bg=COLOR_BG_DARK, width=410)
        right_panel = ttk.LabelFrame(self.paned_creator, text=" Árvore Estrutural do Projeto ")
        
        self.paned_creator.add(left_panel, minsize=380)
        self.paned_creator.add(right_panel, minsize=420)

        # --- PAINEL DE ENTRADAS ---
        lf_inputs = ttk.LabelFrame(left_panel.content, text=" Detalhes do Novo Projeto ")
        lf_inputs.pack(side=tk.TOP, fill=tk.X, expand=False, padx=15, pady=(15, 10), ipady=8, ipadx=8)

        # Destino Raiz
        ttk.Label(lf_inputs, text="Diretório de Criação (Raiz):").grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(4, 2))
        self.var_creator_root = tk.StringVar(value=os.getcwd())
        
        entry_root = tk.Entry(lf_inputs, textvariable=self.var_creator_root, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, insertbackground=COLOR_TEXT_PRIMARY, bd=1, relief="solid", font=("Segoe UI", 9))
        entry_root.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(8, 4), pady=2)
        
        btn_browse_root = HoverButton(
            lf_inputs, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Procurar...", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), width=10, command=self.browse_creator_root
        )
        btn_browse_root.grid(row=1, column=2, padx=(2, 8), pady=2)

        # Campo da Data e Componente Datepicker
        ttk.Label(lf_inputs, text="Data de Registro:").grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 2))
        
        now = datetime.datetime.now()
        self.var_day = tk.StringVar(value=f"{now.day:02d}")
        self.var_month = tk.StringVar(value=f"{now.month:02d}")
        self.var_year = tk.StringVar(value=str(now.year))

        date_container = tk.Frame(lf_inputs, bg=COLOR_BG_CARD)
        date_container.grid(row=3, column=0, columnspan=3, sticky="w", padx=8, pady=2)

        tk.Entry(date_container, textvariable=self.var_day, width=4, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, justify="center", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=1)
        tk.Label(date_container, text="/", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED).pack(side=tk.LEFT)
        tk.Entry(date_container, textvariable=self.var_month, width=4, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, justify="center", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=1)
        tk.Label(date_container, text="/", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED).pack(side=tk.LEFT)
        tk.Entry(date_container, textvariable=self.var_year, width=6, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, justify="center", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=1)

        btn_datepicker = HoverButton(
            date_container, hover_bg=COLOR_ACCENT, hover_fg="#ffffff",
            text=" Abrir Calendário ", bg=COLOR_BORDER, fg=COLOR_TEXT_PRIMARY, bd=0,
            font=("Segoe UI", 8, "bold"), height=1, command=self.open_datepicker_modal
        )
        btn_datepicker.pack(side=tk.LEFT, padx=10)

        # Cliente e Projeto
        ttk.Label(lf_inputs, text="Nome do Cliente:").grid(row=4, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 2))
        self.var_client = tk.StringVar()
        entry_client = tk.Entry(lf_inputs, textvariable=self.var_client, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_client.grid(row=5, column=0, columnspan=3, sticky="ew", padx=8, pady=2)

        ttk.Label(lf_inputs, text="Nome do Projeto / Cena:").grid(row=6, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 2))
        self.var_project_name = tk.StringVar()
        entry_project = tk.Entry(lf_inputs, textvariable=self.var_project_name, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_project.grid(row=7, column=0, columnspan=3, sticky="ew", padx=8, pady=2)

        lf_inputs.columnconfigure(0, weight=1)
        lf_inputs.columnconfigure(1, weight=1)

        # Preview do caminho de montagem final
        lf_preview = ttk.LabelFrame(left_panel.content, text=" Caminho de Destino Estimado ")
        lf_preview.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(0, 10))
        
        self.lbl_path_preview = tk.Text(lf_preview, height=4, bg=COLOR_BG_INPUT, fg=COLOR_WARNING, bd=0, wrap=tk.WORD, font=("Consolas", 9))
        self.lbl_path_preview.pack(fill=tk.X, padx=8, pady=8)
        self.lbl_path_preview.insert(tk.END, "Preencha os dados acima para visualizar o caminho...")
        self.lbl_path_preview.config(state=tk.DISABLED)

        # Botão de Execução
        btn_run_creator = RoundedButton(
            left_panel.content, hover_bg=COLOR_ACCENT_HOVER, hover_fg="#ffffff",
            text="Criar Estrutura de Pastas", bg=COLOR_ACCENT, fg="#ffffff",
            font=("Segoe UI", 10, "bold"), height=42, command=self.execute_create_project
        )
        btn_run_creator.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(5, 15))

        # Ligar listeners para atualizar o preview dinamicamente
        for var in (self.var_creator_root, self.var_day, self.var_month, self.var_year, self.var_client, self.var_project_name):
            var.trace_add("write", lambda *args: self.update_path_preview())

        # --- PAINEL DE GESTÃO DE TEMPLATES ---
        templates_bar = tk.Frame(right_panel, bg=COLOR_BG_CARD)
        templates_bar.pack(fill=tk.X, padx=15, pady=(15, 5))

        lbl_tpl = tk.Label(templates_bar, text="Modelo de Pastas:", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9, "bold"))
        lbl_tpl.pack(side=tk.LEFT, padx=(5, 2), pady=2)

        self.var_active_template = tk.StringVar(value=self.active_template)
        self.combo_templates = ttk.Combobox(
            templates_bar, textvariable=self.var_active_template,
            values=list(self.templates.keys()), state="readonly", width=18
        )
        self.combo_templates.pack(side=tk.LEFT, padx=2, pady=2)
        self.combo_templates.bind("<<ComboboxSelected>>", self.on_template_selected)

        btn_save_template = HoverButton(
            templates_bar, hover_bg=COLOR_ACCENT_HOVER, hover_fg="#ffffff",
            text="Salvar Modelo", bg=COLOR_ACCENT, fg="#ffffff", bd=0,
            font=("Segoe UI", 8, "bold"), command=self.save_template_as
        )
        btn_save_template.pack(side=tk.LEFT, padx=2, pady=2)

        btn_del_template = HoverButton(
            templates_bar, hover_bg=COLOR_BORDER, hover_fg=COLOR_DANGER,
            text=" X ", bg=COLOR_BG_DARK, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 9, "bold"), width=3, command=self.delete_current_template
        )
        btn_del_template.pack(side=tk.LEFT, padx=2, pady=2)

        # --- PAINEL DA ÁRVORE DE CHECKBOXES ---
        toolbar_tree = tk.Frame(right_panel, bg=COLOR_BG_CARD)
        toolbar_tree.pack(fill=tk.X, padx=15, pady=5)
        
        btn_chk_all = HoverButton(
            toolbar_tree, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Marcar Tudo", bg=COLOR_BG_DARK, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=self.check_all_folders
        )
        btn_chk_all.pack(side=tk.LEFT, padx=3, pady=2)

        btn_unchk_all = HoverButton(
            toolbar_tree, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Desmarcar Tudo", bg=COLOR_BG_DARK, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=self.uncheck_all_folders
        )
        btn_unchk_all.pack(side=tk.LEFT, padx=3, pady=2)

        btn_clear_all = HoverButton(
            toolbar_tree, hover_bg=COLOR_BORDER, hover_fg=COLOR_DANGER,
            text="Limpar Tudo", bg=COLOR_BG_DARK, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=self.clear_all_folders
        )
        btn_clear_all.pack(side=tk.LEFT, padx=3, pady=2)

        btn_add_cust = HoverButton(
            toolbar_tree, hover_bg=COLOR_ACCENT_HOVER, hover_fg="#ffffff",
            text=" + ", bg=COLOR_ACCENT, fg="#ffffff", bd=0,
            font=("Segoe UI", 10, "bold"), width=3, command=self.add_custom_folder_path
        )
        btn_add_cust.pack(side=tk.RIGHT, padx=3, pady=2)

        # Scrollable Frame para a Árvore de Diretórios
        canvas_scroll = tk.Canvas(right_panel, bg=COLOR_BG_CARD, highlightthickness=0)
        scrollbar_y = ttk.Scrollbar(right_panel, orient="vertical", command=canvas_scroll.yview)
        self.scroll_frame = tk.Frame(canvas_scroll, bg=COLOR_BG_CARD)

        canvas_window = canvas_scroll.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        
        def configure_scroll_frame(e):
            canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all"))
            # Make the frame fill the canvas width
            canvas_scroll.itemconfig(canvas_window, width=e.width)

        canvas_scroll.bind("<Configure>", configure_scroll_frame)
        canvas_scroll.configure(yscrollcommand=scrollbar_y.set)

        # Suporte a rolagem com o Scroll do Mouse
        def _on_mousewheel(event):
            canvas_scroll.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas_scroll.bind("<Enter>", lambda e: canvas_scroll.bind_all("<MouseWheel>", _on_mousewheel))
        canvas_scroll.bind("<Leave>", lambda e: canvas_scroll.unbind_all("<MouseWheel>"))

        canvas_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 0), pady=(5, 15))
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y, pady=(5, 15), padx=(0, 15))

        # Inicializa lista de checkboxes baseando-se nas configurações locais carregadas
        self.checkbox_vars = {}
        self.checkbox_widgets = {}
        self.render_checkbox_list()

    def open_datepicker_modal(self):
        """Dispara a janela do calendário interativo dark"""
        CalendarDialog(self, self.var_day, self.var_month, self.var_year)

    def browse_creator_root(self):
        dir_selected = filedialog.askdirectory(initialdir=self.var_creator_root.get())
        if dir_selected:
            self.var_creator_root.set(os.path.normpath(dir_selected))

    def get_constructed_base_path(self):
        root = self.var_creator_root.get().strip()
        day = self.var_day.get().strip()
        month = self.var_month.get().strip()
        year = self.var_year.get().strip()
        client = self.var_client.get().strip()
        project = self.var_project_name.get().strip()

        if not root:
            return ""
        
        # Se o cliente ou o projeto estiverem vazios, usa o diretório raiz diretamente
        if not client or not project:
            return os.path.normpath(root)
        
        # Estrutura: ANO\CLIENTE\ANO.MES\MES.DIA - PROJETO
        sub_path = os.path.join(year, client, f"{year}.{month}", f"{month}.{day} - {project}")
        full_path = os.path.join(root, sub_path)
        return os.path.normpath(full_path)

    def update_path_preview(self):
        path = self.get_constructed_base_path()
        self.lbl_path_preview.config(state=tk.NORMAL)
        self.lbl_path_preview.delete("1.0", tk.END)
        if path:
            self.lbl_path_preview.insert(tk.END, path)
            self.lbl_path_preview.tag_add("highlight", "1.0", "end")
        else:
            self.lbl_path_preview.insert(tk.END, "Aguardando preenchimento dos campos requeridos...")
        self.lbl_path_preview.config(state=tk.DISABLED)
        self.update_existing_folders_status()

    def render_checkbox_list(self):
        # Limpa widgets existentes caso haja reload
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        self.checkbox_widgets = {}

        # Expandir caminhos para certificar que todos os pais intermediários existam
        all_paths = set()
        for folder in self.custom_folders:
            parts = folder.split('/')
            for i in range(1, len(parts) + 1):
                all_paths.add("/".join(parts[:i]))

        # Reconstruir dicionário de árvore aninhado
        tree_dict = {}
        for path in sorted(all_paths):
            parts = path.split('/')
            current = tree_dict
            for part in parts:
                if part not in current:
                    current[part] = {}
                current = current[part]

        # Renderizador recursivo para desenhar a estrutura de árvore com linhas de guia e botões inline
        def render_node(node, parent_path="", depth=0, prefixes=[]):
            keys = sorted(node.keys())
            for idx, key in enumerate(keys):
                is_last = (idx == len(keys) - 1)
                full_path = f"{parent_path}/{key}" if parent_path else key
                
                # Inicializa estado se não existir
                if full_path not in self.checkbox_vars:
                    self.checkbox_vars[full_path] = tk.BooleanVar(value=True)
                
                # Monta as linhas estruturais de árvore (├─ / └─) baseadas no nível
                line_prefix = ""
                for p in prefixes:
                    line_prefix += "    " if p else "│   "
                
                branch = "└── " if is_last else "├── "
                # Substituído o emoji de pasta por um visualizador limpo de árvore
                display_text = f"{line_prefix}{branch}{key}" if depth > 0 else f"  {key}"
                
                # Container horizontal para alinhar o Checkbutton e os botões de controle
                row_frame = tk.Frame(self.scroll_frame, bg=COLOR_BG_CARD, cursor="hand2")
                row_frame.pack(fill=tk.X, padx=15, pady=1)
                
                # Renderiza o Checkbutton com fonte monoespaçada
                cb = tk.Checkbutton(
                    row_frame,
                    text=display_text,
                    variable=self.checkbox_vars[full_path],
                    bg=COLOR_BG_CARD,
                    fg=COLOR_TEXT_PRIMARY,
                    selectcolor=COLOR_BG_INPUT,
                    activebackground=COLOR_BG_CARD,
                    activeforeground=COLOR_TEXT_PRIMARY,
                    font=("Consolas", 9),
                    anchor="w",
                    justify="left",
                    cursor="hand2",
                    command=lambda p=full_path: self.on_checkbox_toggle(p)
                )
                cb.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))
                self.checkbox_widgets[full_path] = cb

                # Botões inline para Renomear e Excluir
                btn_edit = HoverButton(
                    row_frame, hover_bg=COLOR_BORDER, hover_fg=COLOR_ACCENT,
                    text="Editar", bg=COLOR_BG_CARD, fg=COLOR_BG_CARD, bd=0,
                    font=("Segoe UI", 8, "bold"), width=6, height=1, cursor="hand2",
                    command=lambda p=full_path: self.rename_folder_path(p)
                )
                btn_edit.pack(side=tk.RIGHT, padx=(2, 5))

                btn_del = HoverButton(
                    row_frame, hover_bg=COLOR_BORDER, hover_fg=COLOR_DANGER,
                    text="X", bg=COLOR_BG_CARD, fg=COLOR_BG_CARD, bd=0,
                    font=("Segoe UI", 8, "bold"), width=7, height=1, cursor="hand2",
                    command=lambda p=full_path: self.delete_folder_path(p)
                )
                btn_del.pack(side=tk.RIGHT, padx=(2, 2))

                btn_copy = HoverButton(
                    row_frame, hover_bg=COLOR_BORDER, hover_fg=COLOR_ACCENT,
                    text="Copiar", bg=COLOR_BG_CARD, fg=COLOR_BG_CARD, bd=0,
                    font=("Segoe UI", 8, "bold"), width=6, height=1, cursor="hand2",
                    command=lambda p=full_path: self.copy_branch(p)
                )
                btn_copy.pack(side=tk.RIGHT, padx=(2, 5))

                if self.clipboard_branch is not None:
                    btn_paste = HoverButton(
                        row_frame, hover_bg=COLOR_BORDER, hover_fg=COLOR_ACCENT,
                        text="Colar", bg=COLOR_BG_CARD, fg=COLOR_BG_CARD, bd=0,
                        font=("Segoe UI", 8, "bold"), width=6, height=1, cursor="hand2",
                        command=lambda p=full_path: self.paste_branch(p)
                    )
                    btn_paste.pack(side=tk.RIGHT, padx=(2, 2))
                else:
                    btn_paste = None
                
                # Binds para hover em toda a linha (Row Hover)
                row_frame.bind("<Enter>", lambda e, f=row_frame, c=cb, b1=btn_edit, b2=btn_del, b3=btn_copy, b4=btn_paste: self.on_enter_row(e, f, c, b1, b2, b3, b4))
                row_frame.bind("<Leave>", lambda e, f=row_frame, c=cb, b1=btn_edit, b2=btn_del, b3=btn_copy, b4=btn_paste: self.on_leave_row(e, f, c, b1, b2, b3, b4))
                
                # Bind para clique em qualquer lugar da linha
                def toggle_row(e, path=full_path):
                    # Só alterna se o clique for na linha ou no checkbutton em si
                    if e.widget == row_frame:
                        var = self.checkbox_vars[path]
                        var.set(not var.get())
                        self.on_checkbox_toggle(path)
                
                row_frame.bind("<Button-1>", toggle_row)

                # Continua recursão para desenhar os filhos deste nó
                render_node(node[key], full_path, depth + 1, prefixes + [is_last])

        # Renderiza a estrutura da árvore na GUI
        render_node(tree_dict)
        # Atualiza a verificação de pastas existentes imediatamente após renderizar
        self.update_existing_folders_status()

    def rename_folder_path(self, old_path):
        """Altera recursivamente o nome de um diretório e todas as ramificações filhas sob ele"""
        parts = old_path.split("/")
        current_name = parts[-1]

        # Solicita o novo nome do diretório
        new_name = simpledialog.askstring(
            "Renomear Pasta",
            f"Digite o novo nome para '{current_name}':",
            initialvalue=current_name,
            parent=self
        )

        if not new_name:
            return  # Cancelado ou vazio

        # Limpa o input do usuário contra quebras de caminhos relativos
        new_name = new_name.strip().replace("/", "-").replace("\\", "-")
        if not new_name or new_name == current_name:
            return

        # Reconstrói o novo caminho de origem
        new_parts = list(parts)
        new_parts[-1] = new_name
        new_path = "/".join(new_parts)

        # Atualiza o arquivo de customização listando os novos cabeçalhos
        updated_folders = []
        for folder in self.custom_folders:
            if folder == old_path:
                updated_folders.append(new_path)
            elif folder.startswith(old_path + "/"):
                relative_part = folder[len(old_path):]
                updated_folders.append(new_path + relative_part)
            else:
                updated_folders.append(folder)

        # Transfere os estados das caixas de seleção antigas para as novas chaves
        old_checkbox_vars = dict(self.checkbox_vars)
        self.checkbox_vars = {}

        for path, var in old_checkbox_vars.items():
            if path == old_path:
                self.checkbox_vars[new_path] = tk.BooleanVar(value=var.get())
            elif path.startswith(old_path + "/"):
                relative_part = path[len(old_path):]
                self.checkbox_vars[new_path + relative_part] = tk.BooleanVar(value=var.get())
            else:
                self.checkbox_vars[path] = var

        self.custom_folders = updated_folders
        self.save_config()  # Salva localmente
        self.render_checkbox_list()  # Redesenha a tela

    def delete_folder_path(self, path):
        """Remove permanentemente um diretório e todos os seus filhos recursivamente da árvore de modelos"""
        confirm = messagebox.askyesno(
            "Remover Pasta do Modelo",
            f"Tem certeza que deseja remover permanentemente a pasta '{path}' e todas as suas subpastas do seu modelo estrutural?\n\n(Esta ação não afeta seus arquivos físicos no disco).",
            icon="warning",
            parent=self
        )
        if not confirm:
            return

        # Filtra e reconstrói as listas de pastas sem as removidas
        self.custom_folders = [f for f in self.custom_folders if f != path and not f.startswith(path + "/")]

        # Limpa os estados de checkboxes das chaves excluídas
        keys_to_delete = [k for k in self.checkbox_vars if k == path or k.startswith(path + "/")]
        for k in keys_to_delete:
            if k in self.checkbox_vars:
                del self.checkbox_vars[k]

        self.save_config()  # Salva localmente
        self.render_checkbox_list()  # Redesenha a tela

    def on_checkbox_toggle(self, path):
        parent_state = self.checkbox_vars[path].get()
        if parent_state:
            # Se marcar um filho, marca automaticamente todos os pais intermediários acima
            parts = path.split("/")
            for i in range(1, len(parts)):
                ancestor = "/".join(parts[:i])
                if ancestor in self.checkbox_vars:
                    self.checkbox_vars[ancestor].set(True)
        else:
            # Se desmarcar um pai, desmarca automaticamente todas as subpastas filhas
            for folder_path, var in self.checkbox_vars.items():
                if folder_path.startswith(path + "/"):
                    var.set(False)

    def check_all_folders(self):
        for var in self.checkbox_vars.values():
            var.set(True)

    def uncheck_all_folders(self):
        for var in self.checkbox_vars.values():
            var.set(False)

    def add_custom_folder_path(self):
        dialog = AddFolderDialog(self, self.custom_folders)
        self.wait_window(dialog)
        if dialog.result:
            new_folder = dialog.result.strip().replace("\\", "/")
            if new_folder:
                if new_folder not in self.custom_folders:
                    self.custom_folders.append(new_folder)
                    self.save_config()  # Salva imediatamente nas configurações persistidas
                    self.render_checkbox_list()

    def execute_create_project(self):
        target_path = self.get_constructed_base_path()
        if not target_path:
            messagebox.showerror("Erro de Validação", "Por favor, preencha todos os campos do projeto.", parent=self)
            return

        # Coleta pastas marcadas para criação
        selected_folders = [rel_folder for rel_folder, var in self.checkbox_vars.items() if var.get()]
        if not selected_folders:
            messagebox.showwarning("Aviso", "Nenhuma pasta selecionada para criação.", parent=self)
            return

        existing_folders = []
        to_create_folders = []

        for rel_folder in sorted(selected_folders):
            full_sub = os.path.normpath(os.path.join(target_path, rel_folder))
            if os.path.exists(full_sub):
                existing_folders.append(rel_folder)
            else:
                to_create_folders.append(rel_folder)

        # Se houver pastas existentes, pede confirmação das alterações
        if existing_folders:
            msg = f"Algumas pastas já existem no destino:\n{target_path}\n\n"
            msg += "Pastas que JÁ existem (não serão recriadas):\n"
            for f in existing_folders[:10]:
                msg += f" - {f}\n"
            if len(existing_folders) > 10:
                msg += f" ... e mais {len(existing_folders) - 10} pastas.\n"
            
            msg += "\nPastas que SERÃO criadas:\n"
            if to_create_folders:
                for f in to_create_folders[:10]:
                    msg += f" - {f}\n"
                if len(to_create_folders) > 10:
                    msg += f" ... e mais {len(to_create_folders) - 10} pastas.\n"
            else:
                msg += " - Nenhuma pasta nova para criar.\n"

            msg += "\nDeseja prosseguir e criar apenas as pastas ausentes?"
            
            confirm = messagebox.askyesno("Confirmar Alterações", msg, icon="question", parent=self)
            if not confirm:
                return

        created_count = 0
        try:
            # Cria a raiz do projeto se necessário
            os.makedirs(target_path, exist_ok=True)
            
            # Filtra caminhos marcados para criar apenas os diretórios válidos selecionados e inexistentes
            folders_to_process = to_create_folders if existing_folders else selected_folders
            for rel_folder in sorted(folders_to_process):
                full_sub = os.path.join(target_path, os.path.normpath(rel_folder))
                os.makedirs(full_sub, exist_ok=True)
                created_count += 1

            messagebox.showinfo(
                "Estrutura Criada", 
                f"Sucesso!\n\nProjeto atualizado em:\n{target_path}\n\nTotal de {created_count} novas pastas criadas.",
                parent=self
            )
            # Atualizar os campos das outras abas para conveniência do usuário
            self.var_clean_dir.set(target_path)
            self.var_bkp_src.set(target_path)
            # Atualiza visualmente o status das pastas
            self.update_existing_folders_status()
        except Exception as e:
            messagebox.showerror("Erro de Gravação", f"Ocorreu um erro ao criar a estrutura de pastas:\n{str(e)}", parent=self)


    # =========================================================================
    # TAB 2: LIMPADOR DE PASTAS (EXCLUSÃO SEGURA / ADVANCED BYPASS)
    # =========================================================================
    def init_tab_cleaner(self):
        # Utiliza PanedWindow horizontal para permitir redimensionar as divisões internas
        self.paned_cleaner = tk.PanedWindow(self.tab_cleaner, orient=tk.HORIZONTAL, bg=COLOR_BORDER, bd=0, sashwidth=6, sashrelief="flat", showhandle=True, handlesize=8, handlepad=8)
        self.paned_cleaner.pack(fill=tk.BOTH, expand=True)

        left_panel = ScrollablePanel(self.paned_cleaner, bg=COLOR_BG_DARK, width=370)
        right_panel = ttk.LabelFrame(self.paned_cleaner, text=" Terminal de Limpeza & Relatório ")
        
        self.paned_cleaner.add(left_panel, minsize=350)
        self.paned_cleaner.add(right_panel, minsize=400)

        # --- Opções de Configuração ---
        lf_clean_opts = ttk.LabelFrame(left_panel.content, text=" Configurações de Limpeza ")
        lf_clean_opts.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(15, 10))

        ttk.Label(lf_clean_opts, text="Diretório de Análise:").pack(anchor="w", padx=8, pady=(8, 2))
        self.var_clean_dir = tk.StringVar()
        entry_clean = tk.Entry(lf_clean_opts, textvariable=self.var_clean_dir, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_clean.pack(fill=tk.X, padx=8, pady=2)
        
        btn_browse_clean = HoverButton(
            lf_clean_opts, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Procurar Pasta", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=self.browse_clean_dir
        )
        btn_browse_clean.pack(anchor="e", padx=8, pady=4)

        # Flags de Limpeza
        self.var_clean_empty_dirs = tk.BooleanVar(value=True)
        self.var_clean_temp_files = tk.BooleanVar(value=False)

        cb_empty = tk.Checkbutton(lf_clean_opts, text="Remover pastas vazias recursivamente", variable=self.var_clean_empty_dirs, 
                                  bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_empty.pack(anchor="w", padx=8, pady=4)

        cb_temp = tk.Checkbutton(lf_clean_opts, text="Remover arquivos inúteis/temp (Ex: Thumbs.db)", variable=self.var_clean_temp_files, 
                                 bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_temp.pack(anchor="w", padx=8, pady=4)

        # Bypass de Proteção do System
        self.var_bypass_protection = tk.BooleanVar(value=False)
        cb_bypass = tk.Checkbutton(
            lf_clean_opts, text="Bypass: Forçar limpeza em drives raiz/sistema", 
            variable=self.var_bypass_protection, bg=COLOR_BG_CARD, fg=COLOR_DANGER, 
            selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD,
            activeforeground=COLOR_DANGER, font=("Segoe UI", 9, "bold"),
            command=self.on_bypass_toggle
        )
        cb_bypass.pack(anchor="w", padx=8, pady=6)

        # Nota de Segurança
        note_frame = tk.Frame(left_panel.content, bg=COLOR_BG_CARD, bd=1, relief="solid", highlightthickness=0)
        note_frame.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(0, 10))
        
        lbl_note_title = ttk.Label(note_frame, text="SEGURANÇA EM PRIMEIRO LUGAR", font=("Segoe UI", 9, "bold"), foreground=COLOR_WARNING)
        lbl_note_title.pack(anchor="w", padx=8, pady=(8, 2))
        
        lbl_note_desc = tk.Text(note_frame, wrap=tk.WORD, bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, bd=0, font=("Segoe UI", 9), height=7)
        lbl_note_desc.pack(fill=tk.X, padx=8, pady=(0, 8))
        lbl_note_desc.insert(tk.END, "Esta ferramenta nunca apaga arquivos de dados sem sua instrução.\n\n"
                                     "1. Use 'Simular Limpeza' para fazer um Dry-Run. O terminal listará tudo o que será deletado, sem alterar o disco.\n\n"
                                     "2. Modo Bypass: Permite rodar a limpeza recursiva em drives principais de armazenamento ou diretórios internos sensíveis do OS.")
        lbl_note_desc.config(state=tk.DISABLED)

        # Botões de Ação
        btn_simulate_clean = RoundedButton(
            left_panel.content, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Simular Limpeza (Seguro)", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY,
            font=("Segoe UI", 9, "bold"), height=40, command=self.run_clean_simulation
        )
        btn_simulate_clean.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(5, 4))

        btn_run_clean = RoundedButton(
            left_panel.content, hover_bg="#d93847", hover_fg="#ffffff",
            text="EXECUTAR LIMPEZA AGORA", bg=COLOR_DANGER, fg="#ffffff",
            font=("Segoe UI", 9, "bold"), height=40, command=self.run_clean_real
        )
        btn_run_clean.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(4, 15))

        # --- Terminal de Saída de Log ---
        self.clean_terminal = tk.Text(right_panel, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, insertbackground=COLOR_TEXT_PRIMARY, font=("Consolas", 9))
        self.clean_terminal.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Tags de cores no terminal
        self.clean_terminal.tag_config("green", foreground=COLOR_ACCENT)
        self.clean_terminal.tag_config("red", foreground=COLOR_DANGER)
        self.clean_terminal.tag_config("warning", foreground=COLOR_WARNING)
        self.clean_terminal.tag_config("normal", foreground=COLOR_TEXT_PRIMARY)
        
        self.log_clean("Sistema pronto para análise de diretórios.\nSelecione um diretório de trabalho e escolha 'Simular' ou 'Executar'.")

    def browse_clean_dir(self):
        dir_selected = filedialog.askdirectory(initialdir=self.var_clean_dir.get())
        if dir_selected:
            self.var_clean_dir.set(os.path.normpath(dir_selected))

    def on_bypass_toggle(self):
        """Dispara um prompt rígido de segurança quando o usuário tenta forçar o bypass"""
        if self.var_bypass_protection.get():
            confirm = messagebox.askyesno(
                "PERIGO: Bypass de Segurança Ativado",
                "Ao ativar o bypass de proteção, você desativa as travas que impedem a varredura "
                "recursiva em diretórios críticos do Windows (como C:\\Windows, Arquivos de Programas) "
                "ou raízes brutas de mídias conectadas.\n\n"
                "A limpeza indevida destas áreas pode danificar o sistema operacional ou apagar dados "
                "vitais do usuário de forma irreversível.\n\n"
                "Você assume total responsabilidade e deseja prosseguir?",
                icon="warning",
                parent=self
            )
            if not confirm:
                self.var_bypass_protection.set(False)

    def log_clean(self, msg, tag="normal"):
        self.clean_terminal.insert(tk.END, msg + "\n", tag)
        self.clean_terminal.see(tk.END)

    def is_protected_path(self, path):
        # Se o bypass manual estiver ativo na interface, ignora a restrição
        if self.var_bypass_protection.get():
            self.log_queue.put(("[AVISO] Bypass ativo. Ignorando checagens de proteção de pastas!", "warning"))
            return False

        path = os.path.normpath(path).lower()
        if len(path) <= 3: # C:\, D:\ ou equivalentes
            return True
        protected_system_folders = ["windows", "program files", "program files (x86)", "system32", "users"]
        for pf in protected_system_folders:
            if pf in path.split(os.sep):
                return True
        return False

    def run_clean_simulation(self):
        target = self.var_clean_dir.get().strip()
        if not target or not os.path.exists(target):
            messagebox.showerror("Erro", "Diretório selecionado inválido ou inexistente.", parent=self)
            return

        if self.is_protected_path(target):
            messagebox.showerror("Ação Bloqueada", "Por segurança, não é permitido realizar limpeza em diretórios do sistema ou raiz do drive.", parent=self)
            return

        self.clean_terminal.delete("1.0", tk.END)
        self.log_clean("=== INICIANDO SIMULAÇÃO DE LIMPEZA (NENHUM ARQUIVO SERÁ APAGADO) ===", "warning")
        self.log_clean(f"Diretório alvo: {target}\n", "normal")

        # Inicia simulação em background thread para evitar lags na UI
        threading.Thread(target=self._clean_worker, args=(target, True), daemon=True).start()

    def run_clean_real(self):
        target = self.var_clean_dir.get().strip()
        if not target or not os.path.exists(target):
            messagebox.showerror("Erro", "Diretório selecionado inválido ou inexistente.", parent=self)
            return

        if self.is_protected_path(target):
            messagebox.showerror("Ação Bloqueada", "Por segurança, não é permitido realizar limpeza em diretórios do sistema ou raiz do drive.", parent=self)
            return

        confirm = messagebox.askyesno(
            "Confirmar Exclusão Definitiva",
            "Atenção! Esta ação removerá definitivamente os diretórios e/ou arquivos vazios encontrados.\n\nDeseja prosseguir?",
            icon="warning",
            parent=self
        )
        if not confirm:
            return

        self.clean_terminal.delete("1.0", tk.END)
        self.log_clean("=== EXECUTANDO LIMPEZA EM DISCO (EXCLUSÃO DEFINITIVA) ===", "red")
        self.log_clean(f"Diretório alvo: {target}\n", "normal")

        threading.Thread(target=self._clean_worker, args=(target, False), daemon=True).start()

    def _clean_worker(self, target, dry_run=True):
        junks = ["thumbs.db", ".ds_store", "desktop.ini", "*.tmp"]
        deleted_files_count = 0
        deleted_dirs_count = 0

        # 1. Limpeza de arquivos inúteis/temp
        if self.var_clean_temp_files.get():
            self.log_queue.put(("Buscando arquivos lixo...", "normal"))
            for root, dirs, files in os.walk(target):
                for file in files:
                    file_lower = file.lower()
                    match_junk = False
                    for j in junks:
                        if j.startswith("*."):
                            ext = j.replace("*", "")
                            if file_lower.endswith(ext):
                                match_junk = True
                        elif file_lower == j:
                            match_junk = True
                    
                    if match_junk:
                        full_filepath = os.path.join(root, file)
                        if dry_run:
                            self.log_queue.put((f"[SIMULAÇÃO] Remover arquivo: {full_filepath}", "warning"))
                        else:
                            try:
                                os.remove(full_filepath)
                                self.log_queue.put((f"[APAGADO] Arquivo lixo: {full_filepath}", "red"))
                            except Exception as e:
                                self.log_queue.put((f"[ERRO] Falha ao deletar arquivo {file}: {str(e)}", "red"))
                        deleted_files_count += 1

        # 2. Limpeza de Pastas Vazias (de baixo para cima na árvore - bottom-up)
        if self.var_clean_empty_dirs.get():
            self.log_queue.put(("Analisando diretórios vazios...", "normal"))
            for root, dirs, files in os.walk(target, topdown=False):
                # Se não contiver arquivos nem subpastas
                if not os.listdir(root):
                    if root == target:
                        continue
                    if dry_run:
                        self.log_queue.put((f"[SIMULAÇÃO] Remover pasta vazia: {root}", "warning"))
                    else:
                        try:
                            os.rmdir(root)
                            self.log_queue.put((f"[APAGADO] Pasta vazia: {root}", "red"))
                        except Exception as e:
                            self.log_queue.put((f"[ERRO] Falha ao deletar pasta {root}: {str(e)}", "red"))
                    deleted_dirs_count += 1

        # Resumo final
        self.log_queue.put(("\n=============================================", "normal"))
        if dry_run:
            self.log_queue.put((f"Simulação concluída com sucesso.\nPastas vazias identificadas: {deleted_dirs_count}\nArquivos inúteis identificados: {deleted_files_count}", "green"))
        else:
            self.log_queue.put((f"Limpeza de disco executada.\nPastas vazias removidas: {deleted_dirs_count}\nArquivos inúteis removidos: {deleted_files_count}", "green"))
        self.log_queue.put(("=============================================", "normal"))


    # =========================================================================
    # TAB 3: BACKUP INCREMENTAL (ROBOCOPY ENGINE)
    # =========================================================================
    def init_tab_backup(self):
        # Utiliza PanedWindow horizontal para permitir redimensionar as divisões internas
        self.paned_backup = tk.PanedWindow(self.tab_backup, orient=tk.HORIZONTAL, bg=COLOR_BORDER, bd=0, sashwidth=6, sashrelief="flat", showhandle=True, handlesize=8, handlepad=8)
        self.paned_backup.pack(fill=tk.BOTH, expand=True)

        left_panel = ScrollablePanel(self.paned_backup, bg=COLOR_BG_DARK, width=380)
        right_panel = ttk.LabelFrame(self.paned_backup, text=" Status do Backup Incremental ")
        
        self.paned_backup.add(left_panel, minsize=350)
        self.paned_backup.add(right_panel, minsize=400)

        # --- Painel de Configurações ---
        lf_paths = ttk.LabelFrame(left_panel.content, text=" Seleção de Mídias ")
        lf_paths.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(15, 8))

        # Origem
        ttk.Label(lf_paths, text="Diretório de Origem (Backup de):").pack(anchor="w", padx=8, pady=(8, 2))
        self.var_bkp_src = tk.StringVar()
        entry_src = tk.Entry(lf_paths, textvariable=self.var_bkp_src, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_src.pack(fill=tk.X, padx=8, pady=2)
        
        btn_browse_src = HoverButton(
            lf_paths, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Procurar Origem", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=self.browse_bkp_src
        )
        btn_browse_src.pack(anchor="e", padx=8, pady=4)

        # Destino
        ttk.Label(lf_paths, text="Diretório de Destino (Salvar em):").pack(anchor="w", padx=8, pady=(8, 2))
        self.var_bkp_dst = tk.StringVar()
        entry_dst = tk.Entry(lf_paths, textvariable=self.var_bkp_dst, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_dst.pack(fill=tk.X, padx=8, pady=2)
        
        btn_browse_dst = HoverButton(
            lf_paths, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Procurar Destino", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=self.browse_bkp_dst
        )
        btn_browse_dst.pack(anchor="e", padx=8, pady=4)

        # Parâmetros Avançados de Robocopy
        lf_advanced = ttk.LabelFrame(left_panel.content, text=" Modos de Cópia Incremental ")
        lf_advanced.pack(side=tk.TOP, fill=tk.X, padx=15, pady=8)

        self.var_bkp_xo = tk.BooleanVar(value=True)
        self.var_bkp_fat = tk.BooleanVar(value=True)
        self.var_bkp_mirror = tk.BooleanVar(value=False)

        cb_xo = tk.Checkbutton(lf_advanced, text="Copiar somente arquivos mais recentes", variable=self.var_bkp_xo,
                               bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_xo.pack(anchor="w", padx=8, pady=4)

        cb_fat = tk.Checkbutton(lf_advanced, text="Compatibilidade com FAT/PenDrives", variable=self.var_bkp_fat,
                                bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_fat.pack(anchor="w", padx=8, pady=4)

        cb_mir = tk.Checkbutton(lf_advanced, text="Espelhar diretório total (Remove itens no Destino)", variable=self.var_bkp_mirror,
                                bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD, command=self.warn_mirror_mode)
        cb_mir.pack(anchor="w", padx=8, pady=4)

        # Validador de Espaço em Disco
        self.lf_disk_status = ttk.LabelFrame(left_panel.content, text=" Monitoramento de Espaço ")
        self.lf_disk_status.pack(side=tk.TOP, fill=tk.X, padx=15, pady=8)
        
        self.lbl_space_status = ttk.Label(self.lf_disk_status, text="Aguardando seleção de origem e destino...", wraplength=340, justify="left")
        self.lbl_space_status.pack(padx=8, pady=8, fill=tk.X)

        # Botão de Ação
        self.btn_run_backup = RoundedButton(
            left_panel.content, hover_bg=COLOR_ACCENT_HOVER, hover_fg="#ffffff",
            text="Executar Backup Incremental", bg=COLOR_ACCENT, fg="#ffffff",
            font=("Segoe UI", 10, "bold"), height=42, command=self.start_backup
        )
        self.btn_run_backup.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(8, 15))

        # Triggers de cálculo de espaço
        self.var_bkp_src.trace_add("write", lambda *args: self.calculate_disk_sizes())
        self.var_bkp_dst.trace_add("write", lambda *args: self.calculate_disk_sizes())

        # --- Console de Progresso ---
        self.bkp_terminal = tk.Text(right_panel, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, insertbackground=COLOR_TEXT_PRIMARY, font=("Consolas", 9))
        self.bkp_terminal.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Tags de log do Robocopy
        self.bkp_terminal.tag_config("green", foreground=COLOR_ACCENT)
        self.bkp_terminal.tag_config("red", foreground=COLOR_DANGER)
        self.bkp_terminal.tag_config("warning", foreground=COLOR_WARNING)
        self.bkp_terminal.tag_config("cyan", foreground="#00e1ff")
        
        self.log_bkp("Engine de backup pronta.\nConfigure as pastas de Origem e Destino para começar o processo incremental seguro.")

    def browse_bkp_src(self):
        dir_selected = filedialog.askdirectory(initialdir=self.var_bkp_src.get())
        if dir_selected:
            self.var_bkp_src.set(os.path.normpath(dir_selected))

    def browse_bkp_dst(self):
        dir_selected = filedialog.askdirectory(initialdir=self.var_bkp_dst.get())
        if dir_selected:
            self.var_bkp_dst.set(os.path.normpath(dir_selected))

    def log_bkp(self, msg, tag="normal"):
        self.bkp_terminal.insert(tk.END, msg + "\n", tag)
        self.bkp_terminal.see(tk.END)

    def warn_mirror_mode(self):
        if self.var_bkp_mirror.get():
            confirm = messagebox.askyesno(
                "PERIGO: Modo Espelho",
                "Você ativou o Modo Espelho (/MIR).\n\n"
                "Isto significa que se você tiver arquivos salvos na pasta de destino que NÃO existam "
                "mais na pasta de origem, eles serão APAGADOS DEFINITIVAMENTE no destino para manter "
                "os dois diretórios 100% idênticos.\n\n"
                "Tem certeza que deseja utilizar esta opção?",
                icon="warning",
                parent=self
            )
            if not confirm:
                self.var_bkp_mirror.set(False)

    def calculate_disk_sizes(self):
        src = self.var_bkp_src.get().strip()
        dst = self.var_bkp_dst.get().strip()
        
        if not src or not dst or not os.path.exists(src) or not os.path.exists(dst):
            self.lbl_space_status.config(text="Aguardando seleção de diretórios válidos para calcular tamanhos...")
            return

        # Executa em uma thread rápida para não dar micro-travamento na interface
        threading.Thread(target=self._disk_size_calc_worker, args=(src, dst), daemon=True).start()

    def _disk_size_calc_worker(self, src, dst):
        try:
            # Espaço livre no destino
            total_dst, used_dst, free_dst = shutil.disk_usage(dst)
            free_dst_gb = free_dst / (1024**3)

            # Tamanho da origem (pode demorar alguns segundos)
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(src):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
            
            src_size_gb = total_size / (1024**3)

            # Substituído os emojis de disco e barra
            msg = (
                f" Tamanho Total da Origem: {src_size_gb:.2f} GB\n"
                f" Espaço Livre no Destino: {free_dst_gb:.2f} GB\n\n"
            )

            if free_dst_gb < src_size_gb:
                msg += "ATENÇÃO: O espaço livre de destino é menor que o tamanho total de origem. Caso o backup seja do zero, pode faltar espaço!"
                color = COLOR_WARNING
            else:
                msg += "Espaço em disco suficiente para uma transferência limpa completa."
                color = COLOR_ACCENT

            self.after(0, lambda: self.lbl_space_status.config(text=msg))
        except Exception as e:
            self.after(0, lambda: self.lbl_space_status.config(text=f"Erro ao calcular espaço em disco: {str(e)}"))

    def start_backup(self):
        src = self.var_bkp_src.get().strip()
        dst = self.var_bkp_dst.get().strip()

        if not src or not dst:
            messagebox.showerror("Campos Vazios", "Por favor, especifique o diretório de origem e de destino.", parent=self)
            return

        if not os.path.exists(src):
            messagebox.showerror("Origem Inexistente", "O diretório de Origem selecionado não existe.", parent=self)
            return

        if not os.path.exists(dst):
            try:
                os.makedirs(dst, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Erro de Destino", f"Não foi possível criar o diretório de destino: {str(e)}", parent=self)
                return

        if os.path.normpath(src).lower() == os.path.normpath(dst).lower():
            messagebox.showerror("Erro de Loops", "Origem e destino não podem ser a mesma pasta física.", parent=self)
            return

        confirm = messagebox.askyesno(
            "Confirmar Backup Incremental",
            f"Origem: {src}\nDestino: {dst}\n\nConfirma a execução da rotina?",
            parent=self
        )
        if not confirm:
            return

        self.bkp_terminal.delete("1.0", tk.END)
        self.log_bkp("Inicializando rotina do backup incremental...", "warning")
        self.btn_run_backup.config(state=tk.DISABLED)

        # Dispara thread do backup
        threading.Thread(target=self._backup_worker, args=(src, dst), daemon=True).start()

    def _backup_worker(self, src, dst):
        # Monta um arquivo de log com timestamp no destino
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        log_name = f"backup_{timestamp}_full.log"
        log_filepath = os.path.join(dst, log_name)

        # Monta argumentos para o ROBOCOPY (padrão robusto do Windows)
        args = ["robocopy", src, dst]
        
        if self.var_bkp_mirror.get():
            args.append("/MIR")
        else:
            args.append("/E")

        if self.var_bkp_xo.get():
            args.append("/XO")

        if self.var_bkp_fat.get():
            args.append("/FFT") # Assume precisão FAT de tempo

        args.extend(["/R:3", "/W:5", "/NP", "/V", f"/LOG:{log_filepath}"])

        self.log_queue.put((f"Executando Robocopy no Windows...", "normal"))
        self.log_queue.put((f"Comando compilado: {' '.join(args)}\n", "cyan"))

        # Executa processo em background lendo saídas
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            process = subprocess.Popen(
                args, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                shell=True,
                startupinfo=startupinfo
            )
            
            stdout, stderr = process.communicate()
            exit_code = process.returncode

            if exit_code < 8:
                self.log_queue.put((f"\n[OK] Backup incremental finalizado com sucesso! (Código de saída Robocopy: {exit_code})", "green"))
            else:
                self.log_queue.put((f"\n[FALHA] Robocopy reportou falhas graves. Verifique as permissões! (Código: {exit_code})", "red"))

            self.log_queue.put((f"Salvando relatório físico em: {log_name}", "cyan"))
            self.parse_and_display_log(log_filepath)

        except Exception as e:
            self.log_queue.put((f"[ERRO CRÍTICO] Falha ao disparar motor de cópias: {str(e)}", "red"))
        
        self.after(0, lambda: self.btn_run_backup.config(state=tk.NORMAL))

    def parse_and_display_log(self, log_path):
        if not os.path.exists(log_path):
            self.log_queue.put(("Aviso: Arquivo de log não pôde ser lido para sumário gráfico.", "warning"))
            return

        self.log_queue.put(("\n" + "="*45, "normal"))
        self.log_queue.put("  RELATÓRIO RESUMIDO DE ARQUIVOS COPIADOS:", "cyan")
        self.log_queue.put("="*45 + "\n", "normal")

        # Tenta ler com múltiplos decoders
        decodings = ["utf-8", "cp850", "cp1252", "latin-1"]
        content_lines = []
        for enc in decodings:
            try:
                with open(log_path, "r", encoding=enc) as f:
                    content_lines = f.readlines()
                break
            except UnicodeDecodeError:
                continue

        copied_count = 0
        in_file_list = False
        summary_section = []

        for line in content_lines:
            line_str = line.strip()
            if "Total" in line and "Copied" in line:
                in_file_list = False
            
            if "Started :" in line:
                in_file_list = True
                continue

            if "\t" in line and not line_str.startswith("-") and not "Header" in line:
                if any(tag in line for tag in ["*EXTRA File", "New File", "Newer", "Older", "Replace"]):
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        filename = parts[-1].strip()
                        self.log_queue.put((f"  [+] Copiado/Modificado: {filename}", "green"))
                        copied_count += 1

            if "Files :" in line or "Dirs :" in line or "Bytes :" in line or "Times :" in line:
                summary_section.append(line.replace("\t", "   "))

        if copied_count == 0:
            self.log_queue.put("  (Nenhum arquivo novo ou modificado foi detectado - Estrutura de destino já está idêntica).", "warning")
        else:
            self.log_queue.put(f"\n  Total de arquivos atualizados nesta rodada: {copied_count}", "green")

        if summary_section:
            self.log_queue.put("\n" + "="*45, "normal")
            self.log_queue.put("  ESTATÍSTICAS DA OPERAÇÃO:", "cyan")
            self.log_queue.put("="*45, "normal")
            for summary_line in summary_section:
                self.log_queue.put((summary_line.strip(), "normal"))

    # =========================================================================
    # TAB 4: RENOMEADOR INCREMENTAL DE ARQUIVOS
    # =========================================================================
    def init_tab_renamer(self):
        # Utiliza PanedWindow horizontal para permitir redimensionar as divisões internas
        self.paned_renamer = tk.PanedWindow(self.tab_renamer, orient=tk.HORIZONTAL, bg=COLOR_BORDER, bd=0, sashwidth=6, sashrelief="flat", showhandle=True, handlesize=8, handlepad=8)
        self.paned_renamer.pack(fill=tk.BOTH, expand=True)

        left_panel = ScrollablePanel(self.paned_renamer, bg=COLOR_BG_DARK, width=390)
        right_panel = ttk.LabelFrame(self.paned_renamer, text=" Terminal / Preview de Renomeação ")

        self.paned_renamer.add(left_panel, minsize=370)
        self.paned_renamer.add(right_panel, minsize=400)

        # --- SELEÇÃO DE DIRETÓRIO ---
        lf_dir = ttk.LabelFrame(left_panel.content, text=" Pasta de Trabalho ")
        lf_dir.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(15, 5))

        ttk.Label(lf_dir, text="Diretório dos Arquivos:").pack(anchor="w", padx=8, pady=(6, 2))
        self.var_renamer_dir = tk.StringVar(value=os.getcwd())
        entry_dir = tk.Entry(lf_dir, textvariable=self.var_renamer_dir, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_dir.pack(fill=tk.X, padx=8, pady=2)

        btn_browse_dir = HoverButton(
            lf_dir, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Procurar Pasta", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=self.browse_renamer_dir
        )
        btn_browse_dir.pack(anchor="e", padx=8, pady=(2, 6))

        # --- FILTRO DE EXTENSÕES / TIPOS DE ARQUIVO ---
        lf_exts = ttk.LabelFrame(left_panel.content, text=" Seleção de Tipos / Extensões ")
        lf_exts.pack(side=tk.TOP, fill=tk.X, padx=15, pady=5)

        self.var_ext_img = tk.BooleanVar(value=True)
        self.var_ext_vid = tk.BooleanVar(value=False)
        self.var_ext_aud = tk.BooleanVar(value=False)
        self.var_ext_doc = tk.BooleanVar(value=False)

        cb_img = tk.Checkbutton(lf_exts, text="Imagens (.jpg, .jpeg, .png, .webp...)", variable=self.var_ext_img, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_img.pack(anchor="w", padx=8, pady=2)

        cb_vid = tk.Checkbutton(lf_exts, text="Vídeos (.mp4, .mov, .mkv, .avi...)", variable=self.var_ext_vid, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_vid.pack(anchor="w", padx=8, pady=2)

        cb_aud = tk.Checkbutton(lf_exts, text="Áudios (.mp3, .wav, .aac, .m4a...)", variable=self.var_ext_aud, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_aud.pack(anchor="w", padx=8, pady=2)

        cb_doc = tk.Checkbutton(lf_exts, text="Documentos (.pdf, .docx, .txt...)", variable=self.var_ext_doc, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_doc.pack(anchor="w", padx=8, pady=2)

        ttk.Label(lf_exts, text="Outras Extensões (ex: .raw, .heic ou * para todos):").pack(anchor="w", padx=8, pady=(4, 2))
        self.var_renamer_ext_custom = tk.StringVar(value="")
        entry_custom_ext = tk.Entry(lf_exts, textvariable=self.var_renamer_ext_custom, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_custom_ext.pack(fill=tk.X, padx=8, pady=(0, 6))

        # --- REGRAS DE NOMENCLATURA E INCREMENTO ---
        lf_rules = ttk.LabelFrame(left_panel.content, text=" Regras de Nomenclatura e Incremento ")
        lf_rules.pack(side=tk.TOP, fill=tk.X, padx=15, pady=5)

        ttk.Label(lf_rules, text="Nomenclatura Base (Prefixo):").grid(row=0, column=0, sticky="w", padx=8, pady=(4, 2))
        self.var_renamer_prefix = tk.StringVar(value="Foto_")
        entry_prefix = tk.Entry(lf_rules, textvariable=self.var_renamer_prefix, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9, "bold"))
        entry_prefix.grid(row=0, column=1, sticky="ew", padx=8, pady=2)

        ttk.Label(lf_rules, text="Dígitos do Contador:").grid(row=1, column=0, sticky="w", padx=8, pady=2)
        self.var_renamer_digits = tk.StringVar(value="3")
        spin_digits = ttk.Spinbox(lf_rules, from_=1, to=8, textvariable=self.var_renamer_digits, width=5)
        spin_digits.grid(row=1, column=1, sticky="w", padx=8, pady=2)

        ttk.Label(lf_rules, text="Número Inicial (se do zero):").grid(row=2, column=0, sticky="w", padx=8, pady=2)
        self.var_renamer_start = tk.StringVar(value="1")
        entry_start = tk.Entry(lf_rules, textvariable=self.var_renamer_start, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, width=6, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_start.grid(row=2, column=1, sticky="w", padx=8, pady=2)

        ttk.Label(lf_rules, text="Ordenar Arquivos Por:").grid(row=3, column=0, sticky="w", padx=8, pady=2)
        self.var_renamer_sort = tk.StringVar(value="Nome (Alfabético)")
        combo_sort = ttk.Combobox(lf_rules, textvariable=self.var_renamer_sort, values=["Nome (Alfabético)", "Data de Modificação (Antigo -> Novo)", "Tamanho do Arquivo"], state="readonly")
        combo_sort.grid(row=3, column=1, sticky="ew", padx=8, pady=2)

        lf_rules.columnconfigure(1, weight=1)

        self.var_renamer_auto_continue = tk.BooleanVar(value=True)
        cb_auto_cont = tk.Checkbutton(
            lf_rules, text="Continuar a partir do último número existente", 
            variable=self.var_renamer_auto_continue, bg=COLOR_BG_CARD, fg=COLOR_ACCENT, 
            selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD,
            activeforeground=COLOR_ACCENT, font=("Segoe UI", 9, "bold")
        )
        cb_auto_cont.grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 6))

        # --- BOTÕES DE AÇÃO ---
        btn_sim_renamer = RoundedButton(
            left_panel.content, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Simular Renomeação (Seguro)", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY,
            font=("Segoe UI", 9, "bold"), height=40, command=self.run_renamer_simulation
        )
        btn_sim_renamer.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(10, 4))

        btn_run_renamer = RoundedButton(
            left_panel.content, hover_bg=COLOR_ACCENT_HOVER, hover_fg="#ffffff",
            text="EXECUTAR RENOMEAÇÃO AGORA", bg=COLOR_ACCENT, fg="#ffffff",
            font=("Segoe UI", 9, "bold"), height=40, command=self.run_renamer_real
        )
        btn_run_renamer.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(4, 15))

        # --- TERMINAL DE SAÍDA ---
        self.renamer_terminal = tk.Text(right_panel, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, insertbackground=COLOR_TEXT_PRIMARY, font=("Consolas", 9))
        self.renamer_terminal.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        self.renamer_terminal.tag_config("green", foreground=COLOR_ACCENT)
        self.renamer_terminal.tag_config("red", foreground=COLOR_DANGER)
        self.renamer_terminal.tag_config("warning", foreground=COLOR_WARNING)
        self.renamer_terminal.tag_config("cyan", foreground="#00e1ff")
        self.renamer_terminal.tag_config("normal", foreground=COLOR_TEXT_PRIMARY)

        self.log_renamer("Sistema de renomeação incremental pronto.\nSelecione o diretório, os tipos de arquivo e configure a nomenclatura base.")

    def browse_renamer_dir(self):
        dir_selected = filedialog.askdirectory(initialdir=self.var_renamer_dir.get())
        if dir_selected:
            self.var_renamer_dir.set(os.path.normpath(dir_selected))

    def log_renamer(self, msg, tag="normal"):
        self.renamer_terminal.insert(tk.END, msg + "\n", tag)
        self.renamer_terminal.see(tk.END)

    def validate_renamer_inputs(self):
        target = self.var_renamer_dir.get().strip()
        if not target or not os.path.exists(target) or not os.path.isdir(target):
            messagebox.showerror("Erro", "Diretório selecionado inválido ou inexistente.", parent=self)
            return False

        prefix = self.var_renamer_prefix.get()
        forbidden_chars = r'[\/:*?"<>|]'
        if re.search(forbidden_chars, prefix):
            messagebox.showerror("Nomenclatura Inválida", "A nomenclatura base contém caracteres proibidos para nomes de arquivos (\\ / : * ? \" < > |).", parent=self)
            return False

        return True

    def run_renamer_simulation(self):
        if not self.validate_renamer_inputs():
            return

        target = self.var_renamer_dir.get().strip()
        self.renamer_terminal.delete("1.0", tk.END)
        self.log_renamer("=== INICIANDO SIMULAÇÃO DE RENOMEAÇÃO (NENHUM ARQUIVO SERÁ ALTERADO) ===", "warning")
        self.log_renamer(f"Diretório alvo: {target}\n", "normal")

        threading.Thread(target=self._renamer_worker, args=(target, True), daemon=True).start()

    def run_renamer_real(self):
        if not self.validate_renamer_inputs():
            return

        target = self.var_renamer_dir.get().strip()
        confirm = messagebox.askyesno(
            "Confirmar Renomeação em Lote",
            f"Atenção! Os arquivos na pasta:\n{target}\n\nserão renomeados incrementalmente. Deseja continuar?",
            icon="warning",
            parent=self
        )
        if not confirm:
            return

        self.renamer_terminal.delete("1.0", tk.END)
        self.log_renamer("=== EXECUTANDO RENOMEAÇÃO INCREMENTAL DE ARQUIVOS ===", "cyan")
        self.log_renamer(f"Diretório alvo: {target}\n", "normal")

        threading.Thread(target=self._renamer_worker, args=(target, False), daemon=True).start()

    def _renamer_worker(self, target_dir, dry_run=True):
        try:
            prefix = self.var_renamer_prefix.get().strip()
            
            # Formatação de extensões selecionadas
            selected_exts = set()
            if self.var_ext_img.get():
                selected_exts.update([".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"])
            if self.var_ext_vid.get():
                selected_exts.update([".mp4", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".webm"])
            if self.var_ext_aud.get():
                selected_exts.update([".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg"])
            if self.var_ext_doc.get():
                selected_exts.update([".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv"])
                
            custom_ext_str = self.var_renamer_ext_custom.get().strip()
            match_all_exts = False
            if custom_ext_str:
                if custom_ext_str == "*":
                    match_all_exts = True
                else:
                    raw_exts = [e.strip() for e in re.split(r'[,;\s]+', custom_ext_str) if e.strip()]
                    for e in raw_exts:
                        if e == "*":
                            match_all_exts = True
                            break
                        if not e.startswith('.'):
                            e = '.' + e
                        selected_exts.add(e.lower())

            if not selected_exts and not match_all_exts:
                self.log_queue.put(("[ERRO] Nenhuma extensão de arquivo foi selecionada para renomeação.", "red", "renamer"))
                return

            # Validação do padding de dígitos
            try:
                digits_padding = int(self.var_renamer_digits.get().strip())
                if digits_padding < 1:
                    digits_padding = 3
            except ValueError:
                digits_padding = 3

            # Validação do número inicial
            try:
                start_num = int(self.var_renamer_start.get().strip())
                if start_num < 0:
                    start_num = 1
            except ValueError:
                start_num = 1

            self.log_queue.put((f"Lendo conteúdo do diretório: {target_dir}", "normal", "renamer"))
            
            try:
                all_entries = os.listdir(target_dir)
            except Exception as e:
                self.log_queue.put((f"[ERRO] Não foi possível acessar o diretório '{target_dir}': {str(e)}", "red", "renamer"))
                return

            # Filtra apenas arquivos
            all_files = [f for f in all_entries if os.path.isfile(os.path.join(target_dir, f))]

            if not all_files:
                self.log_queue.put(("[AVISO] Nenhum arquivo foi encontrado na pasta especificada.", "warning", "renamer"))
                return

            # Encontrar maior número existente para a nomenclatura especificada
            max_existing_num = 0
            found_existing = False
            
            # Padrão regex para detectar prefixo + número (ex: Foto_001.jpg, Foto_15.png, etc)
            pattern_str = rf"^{re.escape(prefix)}(\d+)(\..+)?$"
            existing_regex = re.compile(pattern_str, re.IGNORECASE)

            for f in all_files:
                match = existing_regex.match(f)
                if match:
                    found_existing = True
                    num_val = int(match.group(1))
                    if num_val > max_existing_num:
                        max_existing_num = num_val

            if self.var_renamer_auto_continue.get() and found_existing:
                next_start = max_existing_num + 1
                if next_start > start_num:
                    start_num = next_start
                self.log_queue.put((f"[INCREMENTAL] Arquivos existentes com nomenclatura '{prefix}' identificados! Último número: {max_existing_num}. Continuando a partir de: {start_num}", "cyan", "renamer"))
            else:
                if found_existing:
                    self.log_queue.put((f"[AVISO] Arquivos com nomenclatura '{prefix}' já existem (Maior índice: {max_existing_num}), mas a auto-continuação está desativada. Usando número inicial: {start_num}", "warning", "renamer"))
                else:
                    self.log_queue.put((f"[INFO] Nenhum arquivo anterior com a nomenclatura '{prefix}' foi encontrado. Iniciando contador em: {start_num}", "normal", "renamer"))

            # Filtrar arquivos a serem renomeados conforme as extensões selecionadas
            candidate_files = []
            for f in all_files:
                ext = os.path.splitext(f)[1].lower()
                if match_all_exts or ext in selected_exts:
                    # Se auto_continue está ativo e o arquivo JÁ corresponde EXATAMENTE ao padrão de nomenclatura existente, ignora para não re-renomear o que já foi renomeado
                    if self.var_renamer_auto_continue.get() and existing_regex.match(f):
                        continue
                    candidate_files.append(f)

            if not candidate_files:
                self.log_queue.put(("[AVISO] Nenhum arquivo elegível para renomeação encontrado com as extensões selecionadas.", "warning", "renamer"))
                return

            # Ordenar candidatos conforme critério selecionado
            sort_mode = self.var_renamer_sort.get()
            if sort_mode.startswith("Data"):
                candidate_files.sort(key=lambda f: os.path.getmtime(os.path.join(target_dir, f)))
            elif sort_mode.startswith("Tamanho"):
                candidate_files.sort(key=lambda f: os.path.getsize(os.path.join(target_dir, f)))
            else: # Nome / Alfabético (Ordenação natural simples)
                def natural_sort_key(s):
                    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
                candidate_files.sort(key=natural_sort_key)

            self.log_queue.put((f"\nTotal de arquivos a renomear: {len(candidate_files)}", "normal", "renamer"))
            self.log_queue.put("-" * 55, "normal", "renamer")

            # Planejamento das renomeações
            rename_plan = []
            current_count = start_num

            for f in candidate_files:
                ext = os.path.splitext(f)[1] # Mantém extensão original
                num_formatted = str(current_count).zfill(digits_padding)
                new_name = f"{prefix}{num_formatted}{ext}"
                rename_plan.append((f, new_name))
                current_count += 1

            if dry_run:
                for old_n, new_n in rename_plan:
                    self.log_queue.put((f" [SIMULAÇÃO] '{old_n}' ➔ '{new_n}'", "warning", "renamer"))
                self.log_queue.put("\n=============================================", "normal", "renamer")
                self.log_queue.put((f"Simulação de renomeação concluída. {len(rename_plan)} arquivos prontos para alteração.", "green", "renamer"))
                self.log_queue.put("=============================================", "normal", "renamer")
                return

            # EXECUÇÃO REAL (Duas fases para segurança contra colisões e sobrescritas)
            success_count = 0
            fail_count = 0
            
            # Fase 1: Renomear para nomes temporários únicos
            temp_plan = []
            for old_n, new_n in rename_plan:
                old_path = os.path.join(target_dir, old_n)
                unique_tmp_name = f"__mpf_tmp_{uuid.uuid4().hex[:8]}_{old_n}"
                tmp_path = os.path.join(target_dir, unique_tmp_name)
                
                try:
                    os.rename(old_path, tmp_path)
                    temp_plan.append((tmp_path, new_n, old_n))
                except PermissionError:
                    self.log_queue.put((f" [ERRO PERMISSÃO] Arquivo em uso ou bloqueado: '{old_n}'", "red", "renamer"))
                    fail_count += 1
                except Exception as e:
                    self.log_queue.put((f" [ERRO] Falha ao mover para temporário '{old_n}': {str(e)}", "red", "renamer"))
                    fail_count += 1

            # Fase 2: Renomear do nome temporário para o nome final
            for tmp_path, new_n, orig_n in temp_plan:
                final_path = os.path.join(target_dir, new_n)
                try:
                    if os.path.exists(final_path):
                        # Caso o destino já exista fisicamente (colisão não prevista)
                        self.log_queue.put((f" [ERRO COLISÃO] O arquivo de destino '{new_n}' já existe no disco!", "red", "renamer"))
                        # Tenta desfazer voltando para o nome original
                        os.rename(tmp_path, os.path.join(target_dir, orig_n))
                        fail_count += 1
                        continue

                    os.rename(tmp_path, final_path)
                    self.log_queue.put((f" [SUCESSO] '{orig_n}' ➔ '{new_n}'", "green", "renamer"))
                    success_count += 1
                except PermissionError:
                    self.log_queue.put((f" [ERRO PERMISSÃO] Não foi possível renomear temporário para '{new_n}': Arquivo travado.", "red", "renamer"))
                    # Tenta desfazer
                    try:
                        os.rename(tmp_path, os.path.join(target_dir, orig_n))
                    except Exception:
                        pass
                    fail_count += 1
                except Exception as e:
                    self.log_queue.put((f" [ERRO] Falha ao finalizar '{orig_n}' ➔ '{new_n}': {str(e)}", "red", "renamer"))
                    fail_count += 1

            self.log_queue.put("\n=============================================", "normal", "renamer")
            self.log_queue.put((f"Renomeação incremental executada!\nSucesso: {success_count} arquivo(s)\nFalhas: {fail_count} arquivo(s)", "green" if fail_count == 0 else "warning", "renamer"))
            self.log_queue.put("=============================================", "normal", "renamer")

        except Exception as e:
            self.log_queue.put((f"[ERRO INESPERADO] {str(e)}", "red", "renamer"))

    # =========================================================================
    # TAB 5: COPIA DO CARTÃO (INGEST E EXTRAÇÃO APLANADA DE SUBPASTAS)
    # =========================================================================
    def init_tab_card_copy(self):
        # Utiliza PanedWindow horizontal para permitir redimensionar as divisões internas
        self.paned_card_copy = tk.PanedWindow(self.tab_card_copy, orient=tk.HORIZONTAL, bg=COLOR_BORDER, bd=0, sashwidth=6, sashrelief="flat", showhandle=True, handlesize=8, handlepad=8)
        self.paned_card_copy.pack(fill=tk.BOTH, expand=True)

        left_panel = ScrollablePanel(self.paned_card_copy, bg=COLOR_BG_DARK, width=390)
        right_panel = ttk.LabelFrame(self.paned_card_copy, text=" Status / Terminal de Cópia do Cartão ")

        self.paned_card_copy.add(left_panel, minsize=370)
        self.paned_card_copy.add(right_panel, minsize=400)

        # Flags de controle de operação
        self.card_copy_cancel = False
        self.card_copy_running = False

        # --- SELEÇÃO DE ORIGEM ---
        lf_src = ttk.LabelFrame(left_panel.content, text=" Origem no Cartão / Gravador / Câmera ")
        lf_src.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(12, 4))

        ttk.Label(lf_src, text="Pasta Mãe no Cartão (ex: K:\\MULTI\\FOLDER01 ou K:\\DCIM):").pack(anchor="w", padx=8, pady=(4, 2))
        self.var_card_src = tk.StringVar(value="")
        entry_card_src = tk.Entry(lf_src, textvariable=self.var_card_src, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_card_src.pack(fill=tk.X, padx=8, pady=2)

        btn_browse_src = HoverButton(
            lf_src, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Procurar Pasta Mãe", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=self.browse_card_src
        )
        btn_browse_src.pack(anchor="e", padx=8, pady=(2, 6))

        # --- SELEÇÃO DE DESTINO ---
        lf_dst = ttk.LabelFrame(left_panel.content, text=" Pasta de Destino (Aplanada) ")
        lf_dst.pack(side=tk.TOP, fill=tk.X, padx=15, pady=4)

        ttk.Label(lf_dst, text="Diretório onde todos os arquivos serão copiados diretamente:").pack(anchor="w", padx=8, pady=(4, 2))
        self.var_card_dst = tk.StringVar(value="")
        entry_card_dst = tk.Entry(lf_dst, textvariable=self.var_card_dst, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_card_dst.pack(fill=tk.X, padx=8, pady=2)

        f_dst_btns = tk.Frame(lf_dst, bg=COLOR_BG_CARD)
        f_dst_btns.pack(fill=tk.X, padx=8, pady=(2, 6))

        btn_use_proj = HoverButton(
            f_dst_btns, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Usar Raiz de Projetos", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, bd=1, relief="solid",
            font=("Segoe UI", 8), command=self.use_project_dest_for_card
        )
        btn_use_proj.pack(side=tk.LEFT)

        btn_browse_dst = HoverButton(
            f_dst_btns, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Procurar Destino", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=self.browse_card_dst
        )
        btn_browse_dst.pack(side=tk.RIGHT)

        # --- FILTRO DE TIPOS / EXTENSÕES ---
        lf_exts = ttk.LabelFrame(left_panel.content, text=" Seleção de Tipos / Extensões ")
        lf_exts.pack(side=tk.TOP, fill=tk.X, padx=15, pady=4)

        self.var_card_ext_aud = tk.BooleanVar(value=True)
        self.var_card_ext_vid = tk.BooleanVar(value=False)
        self.var_card_ext_img = tk.BooleanVar(value=False)
        self.var_card_ext_all = tk.BooleanVar(value=False)

        cb_aud = tk.Checkbutton(lf_exts, text="Áudios (.wav, .mp3, .aac, .m4a, .flac, .aif...)", variable=self.var_card_ext_aud, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_aud.pack(anchor="w", padx=8, pady=1)

        cb_vid = tk.Checkbutton(lf_exts, text="Vídeos (.mp4, .mov, .mkv, .avi, .mxf, .braw...)", variable=self.var_card_ext_vid, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_vid.pack(anchor="w", padx=8, pady=1)

        cb_img = tk.Checkbutton(lf_exts, text="Fotos / RAW (.jpg, .png, .raw, .cr2, .cr3, .arw, .dng...)", variable=self.var_card_ext_img, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_img.pack(anchor="w", padx=8, pady=1)

        cb_all = tk.Checkbutton(lf_exts, text="Todos os Arquivos (*)", variable=self.var_card_ext_all, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_all.pack(anchor="w", padx=8, pady=1)

        ttk.Label(lf_exts, text="Outras Extensões (ex: .xml, .lrf ou separadas por vírgula):").pack(anchor="w", padx=8, pady=(3, 1))
        self.var_card_ext_custom = tk.StringVar(value="")
        entry_custom_ext = tk.Entry(lf_exts, textvariable=self.var_card_ext_custom, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_custom_ext.pack(fill=tk.X, padx=8, pady=(0, 5))

        # --- FILTRO POR DATA DE CRIAÇÃO ---
        lf_date = ttk.LabelFrame(left_panel.content, text=" Filtro por Data de Criação ")
        lf_date.pack(side=tk.TOP, fill=tk.X, padx=15, pady=4)

        self.var_card_filter_date = tk.BooleanVar(value=False)
        cb_filter_date = tk.Checkbutton(
            lf_date, text="Filtrar apenas arquivos criados em data específica",
            variable=self.var_card_filter_date, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY,
            selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD,
            command=self._on_toggle_card_date_filter
        )
        cb_filter_date.pack(anchor="w", padx=8, pady=(4, 2))

        self.f_card_date_inputs = tk.Frame(lf_date, bg=COLOR_BG_CARD)
        self.f_card_date_inputs.pack(fill=tk.X, padx=8, pady=(1, 3))

        now = datetime.datetime.now()
        self.var_card_day = tk.StringVar(value=f"{now.day:02d}")
        self.var_card_month = tk.StringVar(value=f"{now.month:02d}")
        self.var_card_year = tk.StringVar(value=str(now.year))

        self.entry_card_day = tk.Entry(self.f_card_date_inputs, textvariable=self.var_card_day, width=3, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, justify="center", font=("Segoe UI", 9, "bold"))
        self.entry_card_day.pack(side=tk.LEFT, padx=1)

        self.lbl_card_slash1 = tk.Label(self.f_card_date_inputs, text="/", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED)
        self.lbl_card_slash1.pack(side=tk.LEFT)

        self.entry_card_month = tk.Entry(self.f_card_date_inputs, textvariable=self.var_card_month, width=3, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, justify="center", font=("Segoe UI", 9, "bold"))
        self.entry_card_month.pack(side=tk.LEFT, padx=1)

        self.lbl_card_slash2 = tk.Label(self.f_card_date_inputs, text="/", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED)
        self.lbl_card_slash2.pack(side=tk.LEFT)

        self.entry_card_year = tk.Entry(self.f_card_date_inputs, textvariable=self.var_card_year, width=5, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, justify="center", font=("Segoe UI", 9, "bold"))
        self.entry_card_year.pack(side=tk.LEFT, padx=1)

        self.btn_card_datepicker = HoverButton(
            self.f_card_date_inputs, hover_bg=COLOR_ACCENT, hover_fg="#ffffff",
            text=" Calendário ", bg=COLOR_BORDER, fg=COLOR_TEXT_PRIMARY, bd=0,
            font=("Segoe UI", 8, "bold"), height=1, command=self.open_card_datepicker_modal
        )
        self.btn_card_datepicker.pack(side=tk.LEFT, padx=(6, 2))

        self.btn_card_today = HoverButton(
            self.f_card_date_inputs, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text=" Hoje ", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, bd=1, relief="solid",
            font=("Segoe UI", 8), height=1, command=self.set_card_date_today
        )
        self.btn_card_today.pack(side=tk.LEFT, padx=2)

        self.lbl_card_date_hint = tk.Label(
            lf_date, text="Todos os arquivos serão copiados (sem filtro de data).",
            bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8)
        )
        self.lbl_card_date_hint.pack(anchor="w", padx=8, pady=(0, 4))

        for var in (self.var_card_day, self.var_card_month, self.var_card_year):
            var.trace_add("write", lambda *args: self._on_card_date_change())

        self._on_toggle_card_date_filter()

        # --- TRATAMENTO DE CONFLITOS DE NOMES ---
        lf_conflict = ttk.LabelFrame(left_panel.content, text=" Tratamento de Conflito de Nomes ")
        lf_conflict.pack(side=tk.TOP, fill=tk.X, padx=15, pady=4)

        ttk.Label(lf_conflict, text="Ação ao detectar arquivo com mesmo nome:").pack(anchor="w", padx=8, pady=(4, 2))
        self.conflict_strategies = [
            "Perguntar o que fazer (Interativo)",
            "Prefixar nome da subpasta (ex: ZOOM0001_arquivo.wav)",
            "Adicionar sufixo numérico (ex: arquivo_1.wav)",
            "Sobrescrever arquivo existente",
            "Pular arquivo (não copiar)"
        ]
        self.var_card_conflict_action = tk.StringVar(value=self.conflict_strategies[0])
        combo_conflict = ttk.Combobox(lf_conflict, textvariable=self.var_card_conflict_action, values=self.conflict_strategies, state="readonly")
        combo_conflict.pack(fill=tk.X, padx=8, pady=2)

        self.var_card_always_prefix = tk.BooleanVar(value=False)
        cb_always_prefix = tk.Checkbutton(
            lf_conflict, text="Sempre prefixar nome da subpasta de origem\n(ex: ZOOM0001_ZOOM0001_Tr1.WAV)",
            justify=tk.LEFT, variable=self.var_card_always_prefix, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY,
            selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD
        )
        cb_always_prefix.pack(anchor="w", padx=8, pady=(3, 6))

        # --- BOTÕES DE AÇÃO ---
        f_actions = tk.Frame(left_panel.content, bg=COLOR_BG_DARK)
        f_actions.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(6, 15))

        self.btn_card_copy_run = RoundedButton(
            f_actions, hover_bg=COLOR_ACCENT_HOVER, hover_fg="#ffffff",
            text="Iniciar Cópia do Cartão", bg=COLOR_ACCENT, fg="#ffffff",
            font=("Segoe UI", 10, "bold"), height=38, command=self.run_card_copy_real
        )
        self.btn_card_copy_run.pack(fill=tk.X, pady=(0, 4))

        self.btn_card_copy_sim = RoundedButton(
            f_actions, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Simulação / Prévia da Cópia (Sem gravar)", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY,
            font=("Segoe UI", 9, "bold"), height=34, command=self.run_card_copy_simulation
        )
        self.btn_card_copy_sim.pack(fill=tk.X, pady=(0, 4))

        self.btn_card_copy_cancel = RoundedButton(
            f_actions, hover_bg="#a83232", hover_fg="#ffffff",
            text="Interromper Cópia", bg="#6e2222", fg="#ffffff",
            font=("Segoe UI", 9, "bold"), height=30, command=self.cancel_card_copy
        )
        self.btn_card_copy_cancel.pack(fill=tk.X)
        self.btn_card_copy_cancel.pack_forget()

        # --- PAINEL DIREITO: STATUS E TERMINAL ---
        top_status_frame = tk.Frame(right_panel, bg=COLOR_BG_CARD)
        top_status_frame.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(10, 5))

        self.progress_card = ttk.Progressbar(top_status_frame, orient="horizontal", mode="determinate")
        self.progress_card.pack(fill=tk.X, pady=(0, 4))

        self.lbl_card_status = ttk.Label(top_status_frame, text="Aguardando seleção de origem e destino...", font=("Segoe UI", 9))
        self.lbl_card_status.pack(anchor="w")

        # Terminal de logs
        self.card_terminal = tk.Text(right_panel, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, insertbackground=COLOR_TEXT_PRIMARY, font=("Consolas", 9), bd=0)
        self.card_terminal.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        self.card_terminal.tag_config("green", foreground=COLOR_ACCENT)
        self.card_terminal.tag_config("red", foreground=COLOR_DANGER)
        self.card_terminal.tag_config("warning", foreground=COLOR_WARNING)
        self.card_terminal.tag_config("cyan", foreground="#00e1ff")
        self.card_terminal.tag_config("normal", foreground=COLOR_TEXT_PRIMARY)
        self.card_terminal.tag_config("muted", foreground=COLOR_TEXT_MUTED)

        # Rodapé do Terminal
        bottom_term_frame = tk.Frame(right_panel, bg=COLOR_BG_CARD)
        bottom_term_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=(5, 10))

        btn_clear_card = HoverButton(
            bottom_term_frame, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Limpar Terminal", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, bd=1, relief="solid",
            font=("Segoe UI", 8), command=self.clear_card_log
        )
        btn_clear_card.pack(side=tk.LEFT)

        btn_open_dst = HoverButton(
            bottom_term_frame, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Abrir Pasta de Destino", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=self.open_card_dst_folder
        )
        btn_open_dst.pack(side=tk.RIGHT)

    def browse_card_src(self):
        init_dir = self.var_card_src.get() if (self.var_card_src.get() and os.path.exists(self.var_card_src.get())) else "K:\\" if os.path.exists("K:\\") else os.getcwd()
        dir_selected = filedialog.askdirectory(initialdir=init_dir, title="Selecione a Pasta Mãe no Cartão / Drive (ex: FOLDER01 ou DCIM)")
        if dir_selected:
            self.var_card_src.set(os.path.normpath(dir_selected))

    def browse_card_dst(self):
        init_dir = self.var_card_dst.get() if (self.var_card_dst.get() and os.path.exists(self.var_card_dst.get())) else os.getcwd()
        dir_selected = filedialog.askdirectory(initialdir=init_dir, title="Selecione a Pasta de Destino para os Arquivos")
        if dir_selected:
            self.var_card_dst.set(os.path.normpath(dir_selected))

    def use_project_dest_for_card(self):
        proj_root = getattr(self, "var_creator_root", None)
        if proj_root and proj_root.get() and os.path.exists(proj_root.get()):
            self.var_card_dst.set(proj_root.get())
        else:
            messagebox.showinfo("Informação", "Nenhum diretório raiz de projetos configurado na aba 'Criar Estrutura de Projeto'.", parent=self)

    def clear_card_log(self):
        self.card_terminal.delete("1.0", tk.END)
        self.progress_card['value'] = 0
        self.lbl_card_status.config(text="Pronto.")

    def open_card_dst_folder(self):
        dst = self.var_card_dst.get().strip()
        if dst and os.path.exists(dst):
            try:
                if sys.platform == "win32":
                    os.startfile(dst)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", dst])
                else:
                    subprocess.Popen(["xdg-open", dst])
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível abrir a pasta: {e}", parent=self)
        else:
            messagebox.showwarning("Aviso", "A pasta de destino informada não existe ou não foi selecionada.", parent=self)

    def _on_toggle_card_date_filter(self):
        enabled = self.var_card_filter_date.get()
        state = tk.NORMAL if enabled else tk.DISABLED
        self.entry_card_day.config(state=state)
        self.entry_card_month.config(state=state)
        self.entry_card_year.config(state=state)
        self.btn_card_datepicker.config(state=state)
        self.btn_card_today.config(state=state)
        if enabled:
            d = self.var_card_day.get().strip()
            m = self.var_card_month.get().strip()
            y = self.var_card_year.get().strip()
            self.lbl_card_date_hint.config(
                text=f"Apenas arquivos criados em {d}/{m}/{y} serão copiados.",
                fg=COLOR_ACCENT
            )
        else:
            self.lbl_card_date_hint.config(
                text="Todos os arquivos serão copiados (sem filtro de data).",
                fg=COLOR_TEXT_MUTED
            )

    def _on_card_date_change(self):
        if hasattr(self, 'var_card_filter_date') and self.var_card_filter_date.get():
            d = self.var_card_day.get().strip()
            m = self.var_card_month.get().strip()
            y = self.var_card_year.get().strip()
            self.lbl_card_date_hint.config(
                text=f"Apenas arquivos criados em {d}/{m}/{y} serão copiados.",
                fg=COLOR_ACCENT
            )

    def open_card_datepicker_modal(self):
        """Abre o modal de calendário para a aba de Cópia do Cartão"""
        dlg = CalendarDialog(self, self.var_card_day, self.var_card_month, self.var_card_year)
        self.wait_window(dlg)
        self._on_card_date_change()

    def set_card_date_today(self):
        now = datetime.datetime.now()
        self.var_card_day.set(f"{now.day:02d}")
        self.var_card_month.set(f"{now.month:02d}")
        self.var_card_year.set(str(now.year))
        self._on_card_date_change()

    def get_selected_card_filter_date(self):
        """Valida e retorna datetime.date se o filtro de data estiver ativo, ou None se desativado."""
        if not self.var_card_filter_date.get():
            return None
        try:
            d = int(self.var_card_day.get().strip())
            m = int(self.var_card_month.get().strip())
            y = int(self.var_card_year.get().strip())
            return datetime.date(y, m, d)
        except (ValueError, TypeError):
            messagebox.showerror(
                "Data Inválida",
                "A data informada no filtro de criação é inválida.\nPor favor, insira um dia, mês e ano válidos (ex: DD/MM/AAAA) ou use o botão 'Calendário'.",
                parent=self
            )
            return False

    @staticmethod
    def get_file_dates(filepath):
        """
        Retorna (creation_date, modification_date) de forma compatível e resiliente com Windows e macOS.
        No macOS, st_birthtime obtém a data de criação nativa.
        No Windows, st_ctime / st_birthtime é a data de criação nativa.
        st_mtime obtém a data de gravação original pelo gravador ou câmera (essencial para volumes exFAT/FAT).
        """
        try:
            st = os.stat(filepath)
            m_date = datetime.date.fromtimestamp(st.st_mtime)
            c_date = None

            btime = getattr(st, 'st_birthtime', None)
            if btime is not None and btime > 0:
                try:
                    c_date = datetime.date.fromtimestamp(btime)
                except (ValueError, OverflowError):
                    c_date = None

            if c_date is None:
                if sys.platform == "win32":
                    try:
                        c_date = datetime.date.fromtimestamp(st.st_ctime)
                    except (ValueError, OverflowError):
                        c_date = m_date
                else:
                    c_date = m_date

            return c_date, m_date
        except Exception:
            return None, None

    def cancel_card_copy(self):
        if self.card_copy_running:
            self.card_copy_cancel = True
            self.log_queue.put(("[AVISO] Solicitando cancelamento da cópia...", "warning", "card_copy"))

    def _prepare_card_copy_ui(self):
        self.btn_card_copy_run.config(state=tk.DISABLED)
        self.btn_card_copy_sim.config(state=tk.DISABLED)
        self.btn_card_copy_cancel.pack(fill=tk.X)

    def _reset_card_copy_ui(self):
        self.btn_card_copy_run.config(state=tk.NORMAL)
        self.btn_card_copy_sim.config(state=tk.NORMAL)
        self.btn_card_copy_cancel.pack_forget()

    def _update_card_progress(self, percent, status_text):
        try:
            self.progress_card['value'] = percent
            self.lbl_card_status.config(text=status_text)
        except Exception:
            pass

    def log_card_copy(self, msg, tag="normal"):
        self.card_terminal.insert(tk.END, msg + "\n", tag)
        self.card_terminal.see(tk.END)

    def prompt_conflict_resolution(self, filename, subfolder, src_path, dst_path):
        """Dispara diálogo modal thread-safe para resolução de conflitos de arquivo"""
        res_queue = queue.Queue()
        def _show():
            try:
                dlg = ConflictDialog(self, filename, subfolder, src_path, dst_path)
                self.wait_window(dlg)
                res_queue.put((dlg.action, dlg.apply_to_all))
            except Exception:
                res_queue.put(("suffix", False))

        self.after(0, _show)
        action, apply_all = res_queue.get()
        return action, apply_all

    def run_card_copy_simulation(self):
        src = self.var_card_src.get().strip()
        dst = self.var_card_dst.get().strip()

        if not src or not dst:
            messagebox.showerror("Campos Obrigatórios", "Por favor, selecione a pasta mãe de Origem e a pasta de Destino.", parent=self)
            return

        if not os.path.exists(src):
            messagebox.showerror("Origem Inexistente", "A pasta mãe de Origem selecionada não existe.", parent=self)
            return

        if os.path.normpath(src).lower() == os.path.normpath(dst).lower():
            messagebox.showerror("Erro de Loops", "Origem e destino não podem ser a mesma pasta física.", parent=self)
            return

        target_date = self.get_selected_card_filter_date()
        if target_date is False:
            return

        self._prepare_card_copy_ui()
        threading.Thread(target=self._card_copy_worker, args=(src, dst, True, target_date), daemon=True).start()

    def run_card_copy_real(self):
        src = self.var_card_src.get().strip()
        dst = self.var_card_dst.get().strip()

        if not src or not dst:
            messagebox.showerror("Campos Obrigatórios", "Por favor, selecione a pasta mãe de Origem e a pasta de Destino.", parent=self)
            return

        if not os.path.exists(src):
            messagebox.showerror("Origem Inexistente", "A pasta mãe de Origem selecionada não existe.", parent=self)
            return

        if not os.path.exists(dst):
            try:
                os.makedirs(dst, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Erro de Destino", f"Não foi possível criar a pasta de destino: {str(e)}", parent=self)
                return

        if os.path.normpath(src).lower() == os.path.normpath(dst).lower():
            messagebox.showerror("Erro de Loops", "Origem e destino não podem ser a mesma pasta física.", parent=self)
            return

        try:
            rel = os.path.relpath(dst, src)
            if not rel.startswith("..") and rel != ".":
                messagebox.showerror("Erro de Hierarquia", "A pasta de destino não pode estar dentro da pasta de origem para evitar loops.", parent=self)
                return
        except Exception:
            pass

        target_date = self.get_selected_card_filter_date()
        if target_date is False:
            return

        filter_info = f"\nFiltro de Data: Apenas arquivos criados em {target_date.strftime('%d/%m/%Y')}" if target_date else "\nFiltro de Data: Todos os arquivos (sem restrição)"
        confirm = messagebox.askyesno(
            "Confirmar Cópia do Cartão",
            f"Origem (Cartão): {src}\nDestino: {dst}{filter_info}\n\nConfirma a cópia dos arquivos elegíveis diretamente para o destino?",
            parent=self
        )
        if not confirm:
            return

        self._prepare_card_copy_ui()
        threading.Thread(target=self._card_copy_worker, args=(src, dst, False, target_date), daemon=True).start()

    def _card_copy_worker(self, src_dir, dst_dir, dry_run=True, target_date=None):
        try:
            self.card_copy_running = True
            self.card_copy_cancel = False

            mode_title = "SIMULAÇÃO (DRY-RUN)" if dry_run else "EXECUÇÃO REAL"
            self.log_queue.put((f"===========================================================", "cyan", "card_copy"))
            self.log_queue.put((f"Iniciando Cópia do Cartão - Modo: {mode_title}", "cyan", "card_copy"))
            self.log_queue.put((f"Origem : {src_dir}", "normal", "card_copy"))
            self.log_queue.put((f"Destino: {dst_dir}", "normal", "card_copy"))
            if target_date:
                self.log_queue.put((f"Filtro : Apenas arquivos criados em {target_date.strftime('%d/%m/%Y')}", "cyan", "card_copy"))
            else:
                self.log_queue.put((f"Filtro : Todos os arquivos (sem filtro de data)", "muted", "card_copy"))
            self.log_queue.put((f"===========================================================\n", "cyan", "card_copy"))

            # Determinar extensões permitidas
            selected_exts = set()
            match_all = self.var_card_ext_all.get()
            if self.var_card_ext_aud.get():
                selected_exts.update({".wav", ".mp3", ".aac", ".m4a", ".flac", ".aif", ".aiff", ".ogg", ".wma"})
            if self.var_card_ext_vid.get():
                selected_exts.update({".mp4", ".mov", ".mkv", ".avi", ".mxf", ".braw", ".prores"})
            if self.var_card_ext_img.get():
                selected_exts.update({".jpg", ".jpeg", ".png", ".raw", ".cr2", ".cr3", ".arw", ".nef", ".dng", ".rw2", ".orf"})

            custom_ext = self.var_card_ext_custom.get().strip()
            if custom_ext:
                for ce in custom_ext.split(","):
                    ce = ce.strip().lower()
                    if ce:
                        if not ce.startswith("."):
                            ce = f".{ce}"
                        if ce == ".*":
                            match_all = True
                        else:
                            selected_exts.add(ce)

            if not match_all and not selected_exts:
                self.log_queue.put(("[ERRO] Nenhuma extensão ou tipo de arquivo foi selecionado!", "red", "card_copy"))
                return

            self.log_queue.put((f"Escanendo estrutura de subpastas a partir da pasta mãe...", "muted", "card_copy"))

            found_files = [] # list of (full_path, subfolder_name, filename, size_bytes, date_str)
            ignored_count = 0
            date_ignored_count = 0
            SYSTEM_IGNORES = {".ds_store", "thumbs.db", "desktop.ini"}

            for root, dirs, files in os.walk(src_dir):
                if self.card_copy_cancel:
                    self.log_queue.put(("[CANCELADO] Operação interrompida pelo usuário.", "warning", "card_copy"))
                    return

                rel_dir = os.path.relpath(root, src_dir)
                if rel_dir == ".":
                    subfolder_name = os.path.basename(src_dir)
                else:
                    subfolder_name = os.path.basename(root)

                for f in files:
                    if f.lower() in SYSTEM_IGNORES or f.startswith("._"):
                        continue

                    ext = os.path.splitext(f)[1].lower()
                    if match_all or ext in selected_exts:
                        full_path = os.path.join(root, f)
                        try:
                            c_date, m_date = self.get_file_dates(full_path)
                            if target_date:
                                # Verifica se o arquivo foi criado na data especificada
                                if c_date != target_date and m_date != target_date:
                                    date_ignored_count += 1
                                    continue

                            sz = os.path.getsize(full_path)
                            effective_date = c_date or m_date
                            d_str = effective_date.strftime("%d/%m/%Y") if effective_date else "N/A"
                            found_files.append((full_path, subfolder_name, f, sz, d_str))
                        except Exception as e:
                            self.log_queue.put((f"[AVISO LEITURA] Erro ao ler metadados de '{f}': {e}", "warning", "card_copy"))
                            ignored_count += 1
                    else:
                        ignored_count += 1

            if not found_files:
                if target_date and date_ignored_count > 0:
                    self.log_queue.put((f"[AVISO] Nenhum arquivo criado em {target_date.strftime('%d/%m/%Y')} foi encontrado ({date_ignored_count} arquivo(s) com outras datas ignorados).", "warning", "card_copy"))
                else:
                    self.log_queue.put(("[AVISO] Nenhum arquivo compatível encontrado nas subpastas da origem.", "warning", "card_copy"))
                return

            total_files = len(found_files)
            total_bytes = sum(item[3] for item in found_files)
            self.log_queue.put((f"Varredura concluída:", "normal", "card_copy"))
            self.log_queue.put((f" • Total de arquivos elegíveis: {total_files}", "normal", "card_copy"))
            self.log_queue.put((f" • Volume total de dados: {format_size(total_bytes)}", "normal", "card_copy"))
            if target_date:
                self.log_queue.put((f" • Filtro de data ativo: Apenas criados em {target_date.strftime('%d/%m/%Y')} ({date_ignored_count} arquivos em outras datas ignorados)", "cyan", "card_copy"))
            if ignored_count > 0:
                self.log_queue.put((f" • Arquivos ignorados (outras extensões/sistema): {ignored_count}", "muted", "card_copy"))
            self.log_queue.put("-" * 55, "normal", "card_copy")

            # Verificação de espaço livre em disco
            if not dry_run:
                try:
                    usage = shutil.disk_usage(dst_dir)
                    free_bytes = usage.free
                    if free_bytes < total_bytes:
                        self.log_queue.put((f"[ERRO CRÍTICO] Espaço insuficiente no destino! Livre: {format_size(free_bytes)} | Necessário: {format_size(total_bytes)}", "red", "card_copy"))
                        return
                    else:
                        self.log_queue.put((f"Espaço livre no disco de destino: {format_size(free_bytes)} (Suficiente)", "muted", "card_copy"))
                except Exception as e:
                    self.log_queue.put((f"[AVISO] Não foi possível verificar espaço livre no destino: {e}", "warning", "card_copy"))

            always_prefix = self.var_card_always_prefix.get()
            default_strategy_str = self.var_card_conflict_action.get()
            
            strategy_mode = "ask"
            if "Prefixar" in default_strategy_str:
                strategy_mode = "prefix"
            elif "sufixo" in default_strategy_str.lower():
                strategy_mode = "suffix"
            elif "Sobrescrever" in default_strategy_str:
                strategy_mode = "overwrite"
            elif "Pular" in default_strategy_str:
                strategy_mode = "skip"

            session_apply_all_action = None

            existing_in_dst = set()
            try:
                for f in os.listdir(dst_dir):
                    existing_in_dst.add(f.lower())
            except Exception:
                pass

            planned_names = set()
            success_count = 0
            fail_count = 0
            skipped_count = 0
            bytes_copied = 0

            start_time = datetime.datetime.now()

            for idx, (src_path, subfolder, orig_filename, f_size, f_date_str) in enumerate(found_files, 1):
                if self.card_copy_cancel:
                    self.log_queue.put(("\n[INTERROMPIDO] Cópia cancelada pelo usuário.", "warning", "card_copy"))
                    break

                if always_prefix:
                    base_target = f"{subfolder}_{orig_filename}"
                else:
                    base_target = orig_filename

                final_name = base_target
                target_path = os.path.join(dst_dir, final_name)

                is_conflict = (final_name.lower() in existing_in_dst or final_name.lower() in planned_names)

                if is_conflict:
                    action = strategy_mode
                    if strategy_mode == "ask":
                        if session_apply_all_action:
                            action = session_apply_all_action
                        else:
                            if dry_run:
                                self.log_queue.put((f" [SIMULAÇÃO CONFLITO] '{subfolder}/{orig_filename}' já existe ou colide. Resolução interativa na execução real.", "warning", "card_copy"))
                                action = "prefix"
                            else:
                                action, apply_all = self.prompt_conflict_resolution(orig_filename, subfolder, src_path, target_path)
                                if apply_all:
                                    session_apply_all_action = action

                    if action == "skip":
                        self.log_queue.put((f" [PULADO] '{subfolder}/{orig_filename}' ignorado.", "muted", "card_copy"))
                        skipped_count += 1
                        continue
                    elif action == "overwrite":
                        final_name = base_target
                    elif action == "prefix":
                        final_name = f"{subfolder}_{orig_filename}"
                        if final_name.lower() in existing_in_dst or final_name.lower() in planned_names:
                            root_name, ext_part = os.path.splitext(final_name)
                            c = 1
                            while f"{root_name}_{c}{ext_part}".lower() in existing_in_dst or f"{root_name}_{c}{ext_part}".lower() in planned_names:
                                c += 1
                            final_name = f"{root_name}_{c}{ext_part}"
                    elif action == "suffix":
                        root_name, ext_part = os.path.splitext(base_target)
                        c = 1
                        while f"{root_name}_{c}{ext_part}".lower() in existing_in_dst or f"{root_name}_{c}{ext_part}".lower() in planned_names:
                            c += 1
                        final_name = f"{root_name}_{c}{ext_part}"

                planned_names.add(final_name.lower())
                final_dst_path = os.path.join(dst_dir, final_name)

                if dry_run:
                    conflict_tag = " (Renomeado/Resolvido)" if final_name != orig_filename else ""
                    self.log_queue.put((f" [PRÉVIA {idx}/{total_files}] '{subfolder}/{orig_filename}' [{f_date_str}] ➔ '{final_name}' ({format_size(f_size)}){conflict_tag}", "normal", "card_copy"))
                    pct = int((idx / total_files) * 100)
                    self.after(0, lambda p=pct, i=idx, t=total_files: self._update_card_progress(p, f"Simulação: {i}/{t} arquivos analisados..."))
                else:
                    try:
                        pct = int((idx / total_files) * 100)
                        status_str = f"Copiando {idx}/{total_files} ({format_size(bytes_copied)} / {format_size(total_bytes)}) - {final_name}"
                        self.after(0, lambda p=pct, s=status_str: self._update_card_progress(p, s))

                        shutil.copy2(src_path, final_dst_path)

                        copied_size = os.path.getsize(final_dst_path)
                        if copied_size != f_size:
                            self.log_queue.put((f" [ERRO INTEGRIDADE] Tamanho divergente em '{final_name}'! Original: {f_size}B, Gravado: {copied_size}B", "red", "card_copy"))
                            fail_count += 1
                        else:
                            success_count += 1
                            bytes_copied += copied_size
                            rename_info = f" (como '{final_name}')" if final_name != orig_filename else ""
                            self.log_queue.put((f" [OK {idx}/{total_files}] {subfolder}/{orig_filename}{rename_info} [{f_date_str} | {format_size(f_size)}]", "green", "card_copy"))
                            existing_in_dst.add(final_name.lower())

                    except PermissionError:
                        self.log_queue.put((f" [ERRO PERMISSÃO] Arquivo bloqueado ou protegido contra gravação: '{orig_filename}'", "red", "card_copy"))
                        fail_count += 1
                    except OSError as e:
                        self.log_queue.put((f" [ERRO I/O] Falha de leitura/escrita em '{orig_filename}': {e}", "red", "card_copy"))
                        fail_count += 1
                    except Exception as e:
                        self.log_queue.put((f" [ERRO] Falha ao copiar '{orig_filename}': {e}", "red", "card_copy"))
                        fail_count += 1

            duration = datetime.datetime.now() - start_time
            dur_str = f"{int(duration.total_seconds())}s"

            self.log_queue.put("\n===========================================================", "cyan", "card_copy")
            if dry_run:
                self.log_queue.put((f"Simulação concluída com sucesso! ({dur_str})", "green", "card_copy"))
                self.log_queue.put((f"Total de arquivos simulados: {total_files} | Volume: {format_size(total_bytes)}", "normal", "card_copy"))
                self.log_queue.put((f"Para efetivar a cópia física no disco, clique em 'Iniciar Cópia do Cartão'.", "warning", "card_copy"))
                self.after(0, lambda: self._update_card_progress(100, f"Simulação concluída: {total_files} arquivos prontos."))
            else:
                self.log_queue.put((f"Processo de Cópia Finalizado em {dur_str}!", "green" if fail_count == 0 else "warning", "card_copy"))
                self.log_queue.put((f"Sucesso: {success_count} arquivo(s) copiado(s) ({format_size(bytes_copied)})", "green", "card_copy"))
                if skipped_count > 0:
                    self.log_queue.put((f"Pulados: {skipped_count} arquivo(s)", "muted", "card_copy"))
                if fail_count > 0:
                    self.log_queue.put((f"Falhas: {fail_count} arquivo(s)", "red", "card_copy"))
                self.after(0, lambda: self._update_card_progress(100, f"Concluído! {success_count} copiados, {fail_count} falhas."))
            self.log_queue.put("===========================================================", "cyan", "card_copy")

        except Exception as e:
            self.log_queue.put((f"[FALHA GERAL] {str(e)}", "red", "card_copy"))
        finally:
            self.card_copy_running = False
            self.after(0, self._reset_card_copy_ui)

    # =========================================================================
    # AUXILIAR: CHECK LOOP DE CONTROLE DE THREADS (Thread-Safe GUI)
    # =========================================================================
    def check_queue_loop(self):
        while not self.log_queue.empty():
            item = self.log_queue.get_nowait()
            if len(item) == 3:
                msg, tag, target = item
                if target == "cleaner":
                    self.log_clean(msg, tag)
                elif target == "backup":
                    self.log_bkp(msg, tag)
                elif target == "renamer":
                    self.log_renamer(msg, tag)
                elif target == "card_copy":
                    self.log_card_copy(msg, tag)
                else:
                    self.log_clean(msg, tag)
            else:
                msg, tag = item
                active_tab = self.notebook.index(self.notebook.select())
                if active_tab == 1: # Limpeza
                    self.log_clean(msg, tag)
                elif active_tab == 2: # Backup
                    self.log_bkp(msg, tag)
                elif active_tab == 3: # Renomeador
                    self.log_renamer(msg, tag)
                elif active_tab == 4: # Copia do Cartão
                    self.log_card_copy(msg, tag)
                else:
                    self.log_clean(msg, tag)
                
        self.after(100, self.check_queue_loop)

    # =========================================================================
    # AUXILIAR: MÉTODOS DE UX (ROW HOVER & FOLDER EXISTENCE CHECK)
    # =========================================================================
    def on_enter_row(self, e, frame, cb, *btns):
        frame.config(bg=COLOR_BG_INPUT)
        cb.config(bg=COLOR_BG_INPUT, activebackground=COLOR_BG_INPUT)
        
        for btn in btns:
            if btn:
                btn.default_bg = COLOR_BG_INPUT
                btn.default_fg = COLOR_TEXT_MUTED
                btn.config(bg=COLOR_BG_INPUT, fg=COLOR_TEXT_MUTED)

    def on_leave_row(self, e, frame, cb, *btns):
        try:
            # Verifica se o mouse ainda está dentro dos limites do frame
            x, y = frame.winfo_pointerxy()
            rx = x - frame.winfo_rootx()
            ry = y - frame.winfo_rooty()
            
            width = frame.winfo_width()
            height = frame.winfo_height()
            
            if 0 <= rx < width and 0 <= ry < height:
                return # Mouse entrou em um widget filho (ex: checkbox ou botão), não apaga hover
        except Exception:
            pass

        frame.config(bg=COLOR_BG_CARD)
        cb.config(bg=COLOR_BG_CARD, activebackground=COLOR_BG_CARD)
        
        for btn in btns:
            if btn:
                btn.default_bg = COLOR_BG_CARD
                btn.default_fg = COLOR_BG_CARD
                btn.config(bg=COLOR_BG_CARD, fg=COLOR_BG_CARD)

    def update_existing_folders_status(self):
        base_path = self.get_constructed_base_path()
        if not base_path:
            # Se o caminho for inválido/incompleto, limpa status de todos
            for full_path, cb in self.checkbox_widgets.items():
                original_text = getattr(cb, "original_text", cb.cget("text"))
                if not hasattr(cb, "original_text"):
                    cb.original_text = original_text
                cb.config(text=original_text, fg=COLOR_TEXT_PRIMARY)
            return
        
        for full_path, cb in self.checkbox_widgets.items():
            target_subfolder = os.path.join(base_path, os.path.normpath(full_path))
            exists = os.path.exists(target_subfolder)
            
            original_text = getattr(cb, "original_text", cb.cget("text"))
            if not hasattr(cb, "original_text"):
                cb.original_text = original_text
            
            if exists:
                cb.config(text=f"{original_text} [Já existe]", fg=COLOR_WARNING)
            else:
                cb.config(text=original_text, fg=COLOR_TEXT_PRIMARY)

    # =========================================================================
    # AUXILIAR: MÉTODOS DE GESTÃO DE TEMPLATES
    # =========================================================================
    def on_template_selected(self, event):
        new_template = self.var_active_template.get()
        if new_template in self.templates:
            # Sincroniza o template antigo para não perder alterações
            self.templates[self.active_template] = list(self.custom_folders)
            self.active_template = new_template
            self.custom_folders = list(self.templates[new_template])
            self.save_config()
            self.checkbox_vars = {} # Reseta para remontar estados padrões
            self.render_checkbox_list()

    def save_template_as(self):
        new_name = simpledialog.askstring(
            "Salvar Modelo de Pastas", 
            "Digite o nome do novo modelo de pastas:",
            parent=self
        )
        if new_name:
            new_name = new_name.strip()
            if new_name:
                self.templates[new_name] = list(self.custom_folders)
                self.active_template = new_name
                self.var_active_template.set(new_name)
                self.combo_templates.config(values=list(self.templates.keys()))
                self.save_config()
                messagebox.showinfo("Modelo Salvo", f"Modelo '{new_name}' salvo com sucesso!", parent=self)

    def delete_current_template(self):
        current = self.var_active_template.get()
        if len(self.templates) <= 1:
            messagebox.showerror("Erro", "Não é possível excluir o único modelo existente.", parent=self)
            return
        
        confirm = messagebox.askyesno(
            "Confirmar Exclusão",
            f"Deseja excluir permanentemente o modelo '{current}'?",
            icon="warning",
            parent=self
        )
        if confirm:
            del self.templates[current]
            # Seleciona o primeiro restante
            self.active_template = list(self.templates.keys())[0]
            self.custom_folders = list(self.templates[self.active_template])
            self.var_active_template.set(self.active_template)
            self.combo_templates.config(values=list(self.templates.keys()))
            self.save_config()
            self.checkbox_vars = {}
            self.render_checkbox_list()
            messagebox.showinfo("Modelo Excluído", f"Modelo '{current}' excluído.", parent=self)

    def clear_all_folders(self):
        confirm = messagebox.askyesno(
            "Limpar Modelo",
            "Tem certeza que deseja limpar TODAS as pastas do modelo atual?",
            icon="warning",
            parent=self
        )
        if confirm:
            self.custom_folders = []
            self.checkbox_vars = {}
            self.checkbox_widgets = {}
            self.save_config()
            self.render_checkbox_list()

    def copy_branch(self, path):
        self.clipboard_branch = []
        prefix = path + "/"
        for folder in self.custom_folders:
            if folder.startswith(prefix):
                relative_part = folder[len(prefix):]
                self.clipboard_branch.append(relative_part)
        self.clipboard_root_name = path.split("/")[-1]
        messagebox.showinfo("Copiado", f"Estrutura sob '{path}' copiada!", parent=self)
        self.render_checkbox_list()

    def paste_branch(self, target_path):
        if self.clipboard_branch is None:
            return
        
        # Pergunta se deseja criar a pasta raiz ou colar diretamente
        create_root = messagebox.askyesno(
            "Colar Estrutura",
            f"Deseja criar a pasta principal '{self.clipboard_root_name}'?\n\n"
            f"(Sim: Cria '{target_path}/{self.clipboard_root_name}' e cola os subdiretórios dentro dela.\n"
            f"Não: Cola os subdiretórios diretamente dentro de '{target_path}').",
            parent=self
        )
        
        new_folders = []
        if create_root:
            base_new_path = f"{target_path}/{self.clipboard_root_name}"
            new_folders.append(base_new_path)
            for sub in self.clipboard_branch:
                new_folders.append(f"{base_new_path}/{sub}")
        else:
            for sub in self.clipboard_branch:
                new_folders.append(f"{target_path}/{sub}")
        
        # Adiciona sem duplicar
        added_count = 0
        for nf in new_folders:
            if nf not in self.custom_folders:
                self.custom_folders.append(nf)
                added_count += 1
        
        if added_count > 0:
            self.save_config()
            self.render_checkbox_list()
            messagebox.showinfo("Colado", f"{added_count} subpastas coladas com sucesso!", parent=self)
        else:
            messagebox.showinfo("Aviso", "Nenhuma pasta nova adicionada (todas já existem no modelo).", parent=self)

class ConflictDialog(tk.Toplevel):
    def __init__(self, parent, filename, subfolder, src_path, dst_path):
        super().__init__(parent)
        self.parent = parent
        self.filename = filename
        self.subfolder = subfolder
        self.src_path = src_path
        self.dst_path = dst_path

        self.action = "suffix"  # "prefix", "suffix", "overwrite", "skip"
        self.apply_to_all = False

        self.title("Conflito de Arquivo Detectado")
        self.geometry("540x420")
        self.minsize(500, 380)
        self.resizable(False, False)
        self.configure(bg=COLOR_BG_DARK)

        # Centraliza modal
        self.update_idletasks()
        w, h = 540, 420
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        round_window_corners(self)
        self.transient(parent)
        self.grab_set()

        # UI Header
        header = tk.Frame(self, bg=COLOR_BG_CARD, padx=15, pady=10)
        header.pack(fill=tk.X)
        tk.Label(header, text="⚠️ Conflito de Nome de Arquivo", bg=COLOR_BG_CARD, fg=COLOR_WARNING, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(header, text=f"O arquivo '{filename}' já existe no destino com o mesmo nome.", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 9)).pack(anchor="w")

        # Detalhes
        card = tk.Frame(self, bg=COLOR_BG_INPUT, padx=12, pady=10, highlightbackground=COLOR_BORDER, highlightthickness=1)
        card.pack(fill=tk.X, padx=15, pady=(10, 5))

        src_info = "N/A"
        dst_info = "N/A"
        try:
            if os.path.exists(src_path):
                s_sz = format_size(os.path.getsize(src_path))
                s_dt = datetime.datetime.fromtimestamp(os.path.getmtime(src_path)).strftime("%d/%m/%Y %H:%M")
                src_info = f"{s_sz} | Modificado: {s_dt}"
        except Exception:
            pass

        try:
            if os.path.exists(dst_path):
                d_sz = format_size(os.path.getsize(dst_path))
                d_dt = datetime.datetime.fromtimestamp(os.path.getmtime(dst_path)).strftime("%d/%m/%Y %H:%M")
                dst_info = f"{d_sz} | Modificado: {d_dt}"
        except Exception:
            pass

        tk.Label(card, text=f"Pasta de Origem no Cartão: {subfolder}", bg=COLOR_BG_INPUT, fg=COLOR_ACCENT, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(card, text=f"• Arquivo Novo: {src_info}", bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 0))
        tk.Label(card, text=f"• Arquivo Já Existente: {dst_info}", bg=COLOR_BG_INPUT, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(1, 0))

        # Checkbox "Aplicar para todos os próximos conflitos"
        self.var_apply_all = tk.BooleanVar(value=False)
        cb_all = tk.Checkbutton(self, text="Aplicar esta escolha para todos os próximos conflitos desta cópia",
                                variable=self.var_apply_all, bg=COLOR_BG_DARK, fg=COLOR_TEXT_PRIMARY,
                                selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_DARK,
                                font=("Segoe UI", 9))
        cb_all.pack(anchor="w", padx=15, pady=(8, 6))

        # Botões de Ação
        btn_frame = tk.Frame(self, bg=COLOR_BG_DARK)
        btn_frame.pack(fill=tk.X, padx=15, pady=4)

        # 1. Prefixar pasta filha
        btn_prefix = RoundedButton(
            btn_frame, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text=f"Prefixar Nome da Subpasta ({subfolder}_{filename})", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY,
            height=32, command=lambda: self._select_action("prefix")
        )
        btn_prefix.pack(fill=tk.X, pady=3)

        # 2. Adicionar sufixo
        btn_suffix = RoundedButton(
            btn_frame, hover_bg=COLOR_ACCENT_HOVER, hover_fg="#ffffff",
            text="Adicionar Sufixo Numérico (ex: arquivo_1.ext)", bg=COLOR_ACCENT, fg="#ffffff",
            height=32, command=lambda: self._select_action("suffix")
        )
        btn_suffix.pack(fill=tk.X, pady=3)

        # 3. Sobrescrever
        btn_overwrite = RoundedButton(
            btn_frame, hover_bg="#c94a38", hover_fg="#ffffff",
            text="Sobrescrever Arquivo no Destino", bg="#992b1d", fg="#ffffff",
            height=32, command=lambda: self._select_action("overwrite")
        )
        btn_overwrite.pack(fill=tk.X, pady=3)

        # 4. Pular
        btn_skip = RoundedButton(
            btn_frame, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Pular Arquivo (Não Copiar)", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY,
            height=32, command=lambda: self._select_action("skip")
        )
        btn_skip.pack(fill=tk.X, pady=3)

        self.protocol("WM_DELETE_WINDOW", lambda: self._select_action("suffix"))

    def _select_action(self, action):
        self.action = action
        self.apply_to_all = self.var_apply_all.get()
        self.grab_release()
        self.destroy()

class AddFolderDialog(tk.Toplevel):
    def __init__(self, parent, existing_folders):
        super().__init__(parent)
        self.parent = parent
        self.existing_folders = existing_folders
        self.result = None

        self.title("Adicionar Nova Pasta")
        self.geometry("450x300")
        self.minsize(400, 300)
        self.resizable(True, False)
        self.configure(bg=COLOR_BG_DARK)
        
        # Centraliza modal
        self.update_idletasks()
        width = 450
        height = 300
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        round_window_corners(self)
        self.transient(parent)
        self.grab_set()

        # UI elements
        tk.Label(self, text="Pasta Pai / Onde criar:", bg=COLOR_BG_DARK, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20, pady=(15, 2))
        
        # Reúne todos os caminhos estruturados na árvore para o dropdown
        parents = ["/ (Raiz)"]
        all_paths = set()
        for folder in existing_folders:
            parts = folder.split('/')
            for i in range(1, len(parts) + 1):
                all_paths.add("/".join(parts[:i]))
        parents.extend(sorted(all_paths))

        self.var_parent = tk.StringVar(value="/ (Raiz)")
        self.combo_parent = ttk.Combobox(self, textvariable=self.var_parent, values=parents, state="readonly")
        self.combo_parent.pack(fill=tk.X, padx=20, pady=2)

        tk.Label(self, text="Nome do Novo Diretório:", bg=COLOR_BG_DARK, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20, pady=(10, 2))
        self.var_name = tk.StringVar()
        self.entry_name = tk.Entry(self, textvariable=self.var_name, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, insertbackground=COLOR_TEXT_PRIMARY, bd=1, relief="solid", font=("Segoe UI", 10))
        self.entry_name.pack(fill=tk.X, padx=20, pady=2)
        self.entry_name.focus_set()

        # Botões
        btn_frame = tk.Frame(self, bg=COLOR_BG_DARK)
        btn_frame.pack(fill=tk.X, padx=20, pady=15)

        self.btn_ok = RoundedButton(
            btn_frame, hover_bg=COLOR_ACCENT_HOVER, hover_fg="#ffffff",
            text="Adicionar", bg=COLOR_ACCENT, fg="#ffffff", height=32, command=self.on_ok
        )
        self.btn_ok.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        self.btn_cancel = RoundedButton(
            btn_frame, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Cancelar", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, height=32, command=self.destroy
        )
        self.btn_cancel.pack(side=tk.TOP, fill=tk.X)

        # Binds
        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.destroy())

    def on_ok(self):
        parent_sel = self.var_parent.get().strip()
        name_sel = self.var_name.get().strip()

        if not name_sel:
            messagebox.showerror("Erro", "O nome da pasta não pode ser vazio.", parent=self)
            return

        # Limpa barras indesejadas
        name_sel = name_sel.replace("/", "-").replace("\\", "-")
        
        if parent_sel == "/ (Raiz)":
            self.result = name_sel
        else:
            self.result = f"{parent_sel}/{name_sel}"
        
        self.grab_release()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()