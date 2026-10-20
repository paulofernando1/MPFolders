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
import time
import string
import hashlib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import ctypes
import errno

try:
    import winreg
except ImportError:
    winreg = None

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
COLOR_DIFF_TAG = "#ffb86d"     # tag para arquivos com diferenças (amarelo/laranja)
COLOR_ONLY_A_TAG = "#82aaff"   # tag para arquivos exclusivos da Pasta A (azul)
COLOR_ONLY_B_TAG = "#c792ea"   # tag para arquivos exclusivos da Pasta B (roxo)
COLOR_MATCH_TAG = "#50dea5"    # tag para arquivos idênticos (verde)

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

def format_timedelta_human(seconds):
    """Retorna diferença de tempo legível em português (ex: 2h 15m, 45s, 3d 4h)"""
    sec = int(abs(seconds))
    if sec < 60:
        return f"{sec}s"
    minutes = sec // 60
    rem_sec = sec % 60
    if minutes < 60:
        return f"{minutes}m {rem_sec}s" if rem_sec > 0 else f"{minutes}m"
    hours = minutes // 60
    rem_min = minutes % 60
    if hours < 24:
        return f"{hours}h {rem_min}m" if rem_min > 0 else f"{hours}h"
    days = hours // 24
    rem_hours = hours % 24
    return f"{days}d {rem_hours}h" if rem_hours > 0 else f"{days}d"

def get_path_storage_info(path):
    """
    Identifica se o caminho é Cloud Folder, NAS de Rede (UNC ou Mapeado), USB ou Disco Local.
    Retorna tupla: (badge_text, color_hex, is_cloud, is_nas, provider_name)
    """
    if not path or not isinstance(path, str):
        return ("Não definido", COLOR_TEXT_MUTED, False, False, "Nenhum")
    p = os.path.normpath(path.strip().strip('"'))
    if not p:
        return ("Não definido", COLOR_TEXT_MUTED, False, False, "Nenhum")

    # 1. Caminho de Rede UNC (\\servidor\share)
    if p.startswith("\\\\"):
        parts = [part for part in p.split("\\") if part]
        server = parts[0] if parts else "NAS"
        return (f"🌐 NAS / Rede UNC ({server})", "#64b5f6", False, True, f"NAS ({server})")

    p_lower = p.lower()
    # 2. Cloud Folders (Dropbox, OneDrive, Google Drive, iCloud, etc.)
    if "dropbox" in p_lower:
        return ("☁ Nuvem: Dropbox (Sincronização Ativa)", "#4fc3f7", True, False, "Dropbox")
    if "onedrive" in p_lower:
        return ("☁ Nuvem: OneDrive (Smart Sync)", "#4fc3f7", True, False, "OneDrive")
    if "google drive" in p_lower or "meu drive" in p_lower or "my drive" in p_lower:
        return ("☁ Nuvem: Google Drive", "#4fc3f7", True, False, "Google Drive")
    if "icloud" in p_lower:
        return ("☁ Nuvem: iCloud Drive", "#4fc3f7", True, False, "iCloud")
    if "nextcloud" in p_lower or "owncloud" in p_lower:
        return ("☁ Nuvem: Nextcloud/OwnCloud", "#4fc3f7", True, False, "Nextcloud")

    # 3. Análise do tipo de unidade do Windows (ctypes GetDriveTypeW)
    if sys.platform == "win32":
        drive = os.path.splitdrive(p)[0]
        if drive:
            drive_root = drive + "\\"
            try:
                dt = ctypes.windll.kernel32.GetDriveTypeW(drive_root)
                if dt == 4:  # DRIVE_REMOTE
                    return (f"🌐 Unidade de Rede Mapeada ({drive})", "#64b5f6", False, True, "NAS Mapeado")
                elif dt == 2:  # DRIVE_REMOVABLE
                    return (f"🔌 Disco Removível / USB ({drive})", "#ffb74d", False, False, "USB")
                elif dt == 3:  # DRIVE_FIXED
                    return (f"💾 Disco Local ({drive})", "#81c784", False, False, "Local")
                elif dt == 5:
                    return (f"💿 Unidade Óptica ({drive})", "#ffb74d", False, False, "CD/DVD")
                elif dt == 6:
                    return (f"⚡ Disco RAM ({drive})", "#81c784", False, False, "RAMDisk")
            except Exception:
                pass

    return ("📁 Pasta Local / Armazenamento Padrão", "#81c784", False, False, "Local")

def to_long_path(path):
    """
    Normaliza caminhos absolutos no Windows para o namespace estendido (\\\\?\\ ou \\\\?\\UNC\\),
    eliminando o limite histórico de MAX_PATH (260 caracteres) nas chamadas de sistema.
    """
    if sys.platform != "win32" or not path or not isinstance(path, str):
        return path
    if path.startswith("\\\\?\\"):
        return path
    try:
        abs_p = os.path.abspath(path)
        if abs_p.startswith("\\\\"):
            return "\\\\?\\UNC\\" + abs_p.lstrip("\\")
        return "\\\\?\\" + abs_p
    except Exception:
        return path

def from_long_path(path):
    """Remove prefixo \\\\?\\ ou \\\\?\\UNC\\ para exibição amigável em telas e logs."""
    if not path or not isinstance(path, str):
        return path
    if path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[8:]
    if path.startswith("\\\\?\\"):
        return path[4:]
    return path

def safe_relpath(path, start=None):
    """Calcula caminho relativo de forma resiliente mesmo com prefixos \\\\?\\ misturados."""
    try:
        p_clean = from_long_path(path)
        s_clean = from_long_path(start) if start else None
        return os.path.relpath(p_clean, s_clean)
    except Exception:
        return os.path.relpath(path, start)

def truncate_filename_safe(filename, max_len=255):
    """
    Trunca com segurança o nome de um componente de arquivo preservando
    rigorosamente a extensão original (.ext) para respeitar o limite máximo
    de 255 caracteres imposto por sistemas de arquivos (NTFS, exFAT, FAT32, ext4, APFS).
    """
    if not filename or len(filename) <= max_len:
        return filename
    root, ext = os.path.splitext(filename)
    if len(ext) >= max_len:
        return filename[:max_len]
    allowed_root = max_len - len(ext)
    return root[:allowed_root] + ext

def get_volume_filesystem(path):
    """Retorna o tipo de sistema de arquivos do volume (ex: NTFS, FAT32, exFAT) no Windows."""
    if sys.platform != "win32" or not path:
        return ""
    try:
        abs_p = from_long_path(os.path.abspath(path))
        drive = os.path.splitdrive(abs_p)[0]
        if drive:
            root_path = drive + "\\"
            buf_name = ctypes.create_unicode_buffer(261)
            buf_fs = ctypes.create_unicode_buffer(261)
            max_comp_len = ctypes.c_ulong()
            flags = ctypes.c_ulong()
            res = ctypes.windll.kernel32.GetVolumeInformationW(
                root_path,
                buf_name, ctypes.sizeof(buf_name),
                None,
                ctypes.byref(max_comp_len),
                ctypes.byref(flags),
                buf_fs, ctypes.sizeof(buf_fs)
            )
            if res:
                return buf_fs.value
    except Exception:
        pass
    return ""

def predict_path_and_name_issues(items, dst_dir):
    """
    Analisa previamente uma lista de itens a serem copiados para dst_dir e verifica:
      - Arquivos cujo caminho final excederá MAX_PATH (260 caracteres);
      - Nomes de arquivo individuais que excedem 255 caracteres;
      - Limitações rígidas se o volume de destino for FAT32.
    Retorna (long_path_count, long_name_count, fs_type, warning_note).
    """
    long_path_count = 0
    long_name_count = 0
    fs_type = get_volume_filesystem(dst_dir)

    for item in items:
        rel_p = item.get("rel_path", "") if isinstance(item, dict) else str(item)
        target_f = os.path.join(dst_dir, rel_p.replace("/", os.sep))
        base_n = os.path.basename(target_f)
        if len(target_f) >= 260:
            long_path_count += 1
        if len(base_n) > 255:
            long_name_count += 1

    notes = []
    if long_path_count > 0:
        notes.append(f"• {long_path_count} arquivo(s) com caminho extenso (>260 caracteres) detectado(s). O MPFolders ativará o namespace Unicode estendido (\\\\?\\) para assegurar a gravação sem erros.")
    if long_name_count > 0:
        notes.append(f"• {long_name_count} arquivo(s) com nome individual >255 caracteres detectado(s).")
    if fs_type and "FAT" in fs_type.upper() and long_path_count > 0:
        notes.append(f"• Atenção: O disco de destino usa {fs_type}, que possui restrições severas de profundidade e tamanho total de caminho no Windows.")

    warning_note = "\n\n📏 Previsão de Caminhos e Extensões de Nome:\n" + "\n".join(notes) if notes else ""
    return long_path_count, long_name_count, fs_type, warning_note

def check_cloud_file_attributes(file_path):
    """
    Verifica se o arquivo em disco possui atributos de arquivo em nuvem (OneDrive / Dropbox Smart Sync).
    Retorna string com aviso se for 'Online-Only' ou None se for local hidratado.
    """
    if sys.platform != "win32" or not file_path:
        return None
    try:
        lp = to_long_path(file_path)
        if not os.path.exists(lp):
            return None
        FILE_ATTRIBUTE_OFFLINE = 0x1000
        FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000
        attrs = ctypes.windll.kernel32.GetFileAttributesW(lp)
        if attrs != -1:
            if (attrs & FILE_ATTRIBUTE_OFFLINE) or (attrs & FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS):
                return "Online-Only (Nuvem)"
    except Exception:
        pass
    return None

def compute_file_hash(filepath, block_size=1024*1024, stop_event=None):
    """Calcula hash SHA-256 do arquivo em blocos de 1MB com suporte a cancelamento imediato."""
    hasher = hashlib.sha256()
    with open(to_long_path(filepath), "rb") as f:
        while True:
            if stop_event and stop_event.is_set():
                return None
            chunk = f.read(block_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def safe_compute_file_hash(filepath, stop_event=None, max_retries=3, delay=0.15):
    """Calcula hash SHA-256 de forma resiliente contra locks de sincronização de nuvem e erros de leitura."""
    for attempt in range(max_retries):
        if stop_event and stop_event.is_set():
            return None, "Cancelado"
        try:
            h = compute_file_hash(filepath, stop_event=stop_event)
            if stop_event and stop_event.is_set():
                return None, "Cancelado"
            return h, None
        except PermissionError as pe:
            if getattr(pe, 'winerror', None) == 32 and attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
                continue
            return None, "Arquivo bloqueado por sincronização de nuvem ou outro processo"
        except OSError as oe:
            win_err = getattr(oe, 'winerror', None)
            err_no = getattr(oe, 'errno', None)
            if win_err in (53, 64, 121, 1231):
                return None, f"Falha de rede no NAS (WinError {win_err})"
            if win_err == 206 or err_no == getattr(errno, 'ENAMETOOLONG', 36):
                return None, "Caminho ou nome do arquivo excede o limite do sistema (WinError 206 / MAX_PATH)"
            if attempt < max_retries - 1:
                time.sleep(delay)
                continue
            return None, f"Erro de E/S: {oe}"
        except Exception as e:
            return None, str(e)
    return None, "Falha de leitura"

def safe_copy_file_resilient(src, dst, max_retries=3, delay=0.35):
    """
    Copia arquivo de src para dst com preservação de metadados (shutil.copy2).
    Possui suporte a caminhos longos (to_long_path), resiliência a locks temporários
    de sincronização em nuvem (WinError 32) e diagnóstico preciso de limites de caminho e
    extensão de nome de arquivo (WinError 206 / ENAMETOOLONG / WinError 123).
    """
    lp_dst = to_long_path(dst)
    lp_src = to_long_path(src)

    try:
        os.makedirs(os.path.dirname(lp_dst), exist_ok=True)
    except OSError as de:
        win_err = getattr(de, 'winerror', None)
        err_no = getattr(de, 'errno', None)
        if win_err == 206 or err_no == getattr(errno, 'ENAMETOOLONG', 36):
            return False, f"Caminho da pasta excede o limite do sistema (WinError 206: MAX_PATH): {from_long_path(os.path.dirname(dst))}"
        return False, f"Falha ao criar diretório de destino: {str(de)}"

    last_err = None
    for attempt in range(max_retries):
        try:
            shutil.copy2(lp_src, lp_dst)
            return True, None
        except PermissionError as pe:
            last_err = pe
            # WinError 32: Sharing violation / lock temporário de sincronização (Dropbox/OneDrive)
            if getattr(pe, 'winerror', None) == 32:
                time.sleep(delay * (attempt + 1))
                continue
            else:
                break
        except OSError as oe:
            last_err = oe
            win_err = getattr(oe, 'winerror', None)
            err_no = getattr(oe, 'errno', None)
            if win_err == 206 or err_no == getattr(errno, 'ENAMETOOLONG', 36):
                return False, f"Nome ou caminho do arquivo excede o limite do sistema (WinError 206 / MAX_PATH / 255 chars): {from_long_path(dst)}"
            if win_err == 123:
                return False, f"Sintaxe ou caracteres de nome de arquivo não suportados pela unidade destino (WinError 123): {from_long_path(dst)}"
            if win_err in (53, 64, 121, 1231):
                return False, f"Falha de rede no NAS (WinError {win_err}): Servidor inacessível"
            time.sleep(delay)
        except Exception as e:
            last_err = e
            break

    err_msg = str(last_err)
    if getattr(last_err, 'winerror', None) == 32:
        err_msg = "Arquivo bloqueado temporariamente pela sincronização da Nuvem (Dropbox/OneDrive)"
    elif getattr(last_err, 'winerror', None) == 206:
        err_msg = "Tamanho do caminho ou nome de arquivo excede o limite permitido pelo sistema de arquivos (WinError 206)"
    return False, err_msg


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
# WIDGET: MODAL PARA DEFINIR NOME DA UNIDADE DE REDE
# ==========================================
class DriveCustomizeDialog(tk.Toplevel):
    """Modal dark para definir o nome/rótulo e ícone personalizado da unidade no Windows Explorer"""
    def __init__(self, parent, drive_letter, default_name="", default_icon="", is_mapping=True):
        super().__init__(parent)
        self.parent = parent
        self.result = None  # None = cancelado; dict = {"label": str, "icon": str}

        action_title = "Mapear" if is_mapping else "Personalizar"
        self.title(f"{action_title} Unidade — {drive_letter}")
        self.geometry("490x380")
        self.resizable(False, False)
        self.configure(bg=COLOR_BG_DARK)
        round_window_corners(self)
        self.transient(parent)
        self.grab_set()

        # Centraliza na janela pai
        self.update_idletasks()
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 245
            y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 190
            self.geometry(f"+{max(10, x)}+{max(10, y)}")
        except Exception:
            pass

        # Header do Modal
        f_top = tk.Frame(self, bg=COLOR_BG_DARK)
        f_top.pack(fill=tk.X, padx=20, pady=(14, 4))

        lbl_title = tk.Label(
            f_top, text=f"🏷 Personalizar Nome e Ícone da Unidade ({drive_letter})",
            font=("Segoe UI", 10, "bold"), bg=COLOR_BG_DARK, fg=COLOR_TEXT_PRIMARY
        )
        lbl_title.pack(anchor="w")

        # 1. Campo Nome / Rótulo
        lbl_desc_name = tk.Label(
            self, text="Nome de Exibição no Windows Explorer / MPFolders:",
            font=("Segoe UI", 8, "bold"), bg=COLOR_BG_DARK, fg=COLOR_TEXT_PRIMARY
        )
        lbl_desc_name.pack(anchor="w", padx=20, pady=(6, 2))

        self.var_name = tk.StringVar(value=default_name)
        self.entry_name = tk.Entry(
            self, textvariable=self.var_name, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY,
            bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9)
        )
        self.entry_name.pack(fill=tk.X, padx=20, pady=(0, 6))
        self.entry_name.focus_set()
        self.entry_name.select_range(0, tk.END)

        # 2. Campo Ícone Customizado
        lbl_desc_icon = tk.Label(
            self, text="Ícone Personalizado da Unidade (.ico, .exe ou .dll):",
            font=("Segoe UI", 8, "bold"), bg=COLOR_BG_DARK, fg=COLOR_TEXT_PRIMARY
        )
        lbl_desc_icon.pack(anchor="w", padx=20, pady=(4, 2))

        f_icon_entry = tk.Frame(self, bg=COLOR_BG_DARK)
        f_icon_entry.pack(fill=tk.X, padx=20, pady=(0, 4))

        self.var_icon = tk.StringVar(value=default_icon)
        self.entry_icon = tk.Entry(
            f_icon_entry, textvariable=self.var_icon, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY,
            bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 8)
        )
        self.entry_icon.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        btn_browse_ico = HoverButton(
            f_icon_entry, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Procurar...", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY,
            bd=1, relief="solid", font=("Segoe UI", 8, "bold"), padx=8, pady=2,
            command=self.browse_icon
        )
        btn_browse_ico.pack(side=tk.LEFT, padx=(0, 4))

        btn_clear_ico = HoverButton(
            f_icon_entry, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Limpar", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED,
            bd=1, relief="solid", font=("Segoe UI", 8), padx=6, pady=2,
            command=self.clear_icon
        )
        btn_clear_ico.pack(side=tk.LEFT)

        # Presets Rápidos de Ícones do Windows
        f_presets = tk.Frame(self, bg=COLOR_BG_DARK)
        f_presets.pack(fill=tk.X, padx=20, pady=(2, 6))

        lbl_presets = tk.Label(
            f_presets, text="Presets:", font=("Segoe UI", 8), bg=COLOR_BG_DARK, fg=COLOR_TEXT_MUTED
        )
        lbl_presets.pack(side=tk.LEFT, padx=(0, 6))

        presets_list = [
            ("📁 Pasta", r"C:\Windows\System32\shell32.dll,4"),
            ("🌐 Rede", r"C:\Windows\System32\shell32.dll,9"),
            ("💾 Disco", r"C:\Windows\System32\shell32.dll,7"),
            ("☁ Nuvem", r"C:\Windows\System32\shell32.dll,275")
        ]
        for p_label, p_val in presets_list:
            btn_p = HoverButton(
                f_presets, hover_bg=COLOR_ACCENT_HOVER, hover_fg="#ffffff",
                text=p_label, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY,
                bd=1, relief="solid", font=("Segoe UI", 7), padx=5, pady=1,
                command=lambda val=p_val: self.var_icon.set(val)
            )
            btn_p.pack(side=tk.LEFT, padx=2)

        # Dica / Observação
        lbl_hint = tk.Label(
            self, text="* Dica: O ícone é gravado no Registro (HKCU/HKLM) e atualizado no Windows Explorer.\n  No modo subst local, o Explorer pode herdar o nome da partição física raiz.",
            font=("Segoe UI", 7, "italic"), bg=COLOR_BG_DARK, fg=COLOR_TEXT_MUTED, justify=tk.LEFT
        )
        lbl_hint.pack(anchor="w", padx=20, pady=(0, 10))

        # Botões de Ação
        f_btns = tk.Frame(self, bg=COLOR_BG_DARK)
        f_btns.pack(fill=tk.X, padx=20, pady=(0, 14))

        btn_cancel = HoverButton(
            f_btns, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Cancelar", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED,
            bd=1, relief="solid", font=("Segoe UI", 8), padx=10, pady=4,
            command=self.on_cancel
        )
        btn_cancel.pack(side=tk.RIGHT, padx=(8, 0))

        btn_ok_text = "Mapear Unidade" if is_mapping else "Salvar Alterações"
        btn_ok = HoverButton(
            f_btns, hover_bg=COLOR_ACCENT_HOVER, hover_fg="#ffffff",
            text=btn_ok_text, bg=COLOR_ACCENT, fg="#ffffff",
            bd=1, relief="solid", font=("Segoe UI", 8, "bold"), padx=14, pady=4,
            command=self.on_ok
        )
        btn_ok.pack(side=tk.RIGHT)

        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.on_cancel())
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

    def browse_icon(self):
        f = filedialog.askopenfilename(
            title="Selecione um Arquivo de Ícone (.ico, .exe, .dll)",
            filetypes=[
                ("Ícones e Executáveis (*.ico, *.exe, *.dll)", "*.ico;*.exe;*.dll"),
                ("Arquivos de Ícone (*.ico)", "*.ico"),
                ("Bibliotecas e Programas (*.dll, *.exe)", "*.dll;*.exe"),
                ("Todos os Arquivos", "*.*")
            ],
            parent=self
        )
        if f:
            self.var_icon.set(os.path.normpath(f))

    def clear_icon(self):
        self.var_icon.set("")

    def on_ok(self):
        self.result = {
            "label": self.var_name.get().strip(),
            "icon": self.var_icon.get().strip()
        }
        self.grab_release()
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()


DriveLabelDialog = DriveCustomizeDialog


def normalize_drive_letter(raw_drive):
    r"""
    Normaliza qualquer representação de letra de unidade para o formato canônico 'X:'.
    Trata com precisão formatos como:
      - 'X:\:' (retornado nativamente pelo comando subst no Windows)
      - 'X:\' ou 'X:/'
      - 'X:' ou 'X'
      - 'X:  [Livre]' ou 'X:  [Ocupado...]'
    """
    if not raw_drive:
        return ""
    s = str(raw_drive).strip()
    m = re.match(r"^([a-zA-Z])", s)
    if m:
        return f"{m.group(1).upper()}:"
    return s.rstrip("\\/").rstrip(":") + ":"


def set_drive_label(drive_letter, label, unc_target=None):
    """Define o nome amigável da unidade no Windows Explorer através do Registro e Shell"""
    if not winreg or sys.platform != "win32":
        return
    norm = normalize_drive_letter(drive_letter)
    if not norm:
        return
    ltr = norm[0].upper()
    label_clean = (label or "").strip()
    if label_clean:
        # 1. Tenta gravar em HKCU (usuário atual)
        try:
            key_path = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\{ltr}\DefaultLabel"
            k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, label_clean)
            winreg.CloseKey(k)
        except Exception:
            pass

        # 2. Tenta gravar em HKLM (caso esteja em sessão elevada/admin)
        try:
            key_path = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\{ltr}\DefaultLabel"
            k_lm = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            winreg.SetValueEx(k_lm, "", 0, winreg.REG_SZ, label_clean)
            winreg.CloseKey(k_lm)
        except Exception:
            pass

        # 3. Se for conexão de rede UNC, grava em MountPoints2 (_LabelFromReg)
        if unc_target and unc_target.startswith(r"\\"):
            try:
                unc_clean = unc_target.lstrip(r"\\").replace(r"\\", "#")
                mp_key = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2\##{unc_clean}"
                k2 = winreg.CreateKey(winreg.HKEY_CURRENT_USER, mp_key)
                winreg.SetValueEx(k2, "_LabelFromReg", 0, winreg.REG_SZ, label_clean)
                winreg.CloseKey(k2)
            except Exception:
                pass
    else:
        remove_drive_label(drive_letter)

    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    except Exception:
        pass


def remove_drive_label(drive_letter):
    """Remove o rótulo amigável associado à letra no Registro do Windows (HKCU e HKLM)"""
    if not winreg or sys.platform != "win32":
        return
    norm = normalize_drive_letter(drive_letter)
    if not norm:
        return
    ltr = norm[0].upper()
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            key_path = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\{ltr}\DefaultLabel"
            winreg.DeleteKey(root, key_path)
        except Exception:
            pass
        try:
            winreg.DeleteKey(root, rf"Software\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\{ltr}")
        except Exception:
            pass
    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    except Exception:
        pass


def get_drive_label(drive_letter, target=None):
    """Lê o nome customizado de exibição da unidade a partir do Registro do Windows"""
    if not winreg or sys.platform != "win32":
        return ""
    norm = normalize_drive_letter(drive_letter)
    if not norm:
        return ""
    ltr = norm[0].upper()
    try:
        key_path = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\{ltr}\DefaultLabel"
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(k, "")
        winreg.CloseKey(k)
        if val and str(val).strip():
            return str(val).strip()
    except Exception:
        pass

    if target and target.startswith(r"\\"):
        try:
            unc_clean = target.lstrip(r"\\").replace(r"\\", "#")
            mp_key = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2\##{unc_clean}"
            k2 = winreg.OpenKey(winreg.HKEY_CURRENT_USER, mp_key)
            val2, _ = winreg.QueryValueEx(k2, "_LabelFromReg")
            winreg.CloseKey(k2)
            if val2 and str(val2).strip():
                return str(val2).strip()
        except Exception:
            pass
    return ""


def set_drive_icon(drive_letter, icon_path):
    """Define o ícone personalizado da unidade no Windows Explorer através do Registro e Shell"""
    if not winreg or sys.platform != "win32":
        return
    norm = normalize_drive_letter(drive_letter)
    if not norm:
        return
    ltr = norm[0].upper()
    icon_clean = (icon_path or "").strip()
    if icon_clean:
        # 1. Tenta gravar em HKCU
        try:
            key_path = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\{ltr}\DefaultIcon"
            k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, icon_clean)
            winreg.CloseKey(k)
        except Exception:
            pass

        # 2. Tenta gravar em HKLM (caso esteja em sessão elevada/admin)
        try:
            key_path = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\{ltr}\DefaultIcon"
            k_lm = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            winreg.SetValueEx(k_lm, "", 0, winreg.REG_SZ, icon_clean)
            winreg.CloseKey(k_lm)
        except Exception:
            pass
    else:
        remove_drive_icon(drive_letter)

    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    except Exception:
        pass


def remove_drive_icon(drive_letter):
    """Remove o ícone customizado associado à letra no Registro do Windows (HKCU e HKLM)"""
    if not winreg or sys.platform != "win32":
        return
    norm = normalize_drive_letter(drive_letter)
    if not norm:
        return
    ltr = norm[0].upper()
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            key_path = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\{ltr}\DefaultIcon"
            winreg.DeleteKey(root, key_path)
        except Exception:
            pass
        try:
            winreg.DeleteKey(root, rf"Software\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\{ltr}")
        except Exception:
            pass
    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    except Exception:
        pass


def get_drive_icon(drive_letter):
    """Lê o caminho do ícone customizado da unidade a partir do Registro do Windows"""
    if not winreg or sys.platform != "win32":
        return ""
    norm = normalize_drive_letter(drive_letter)
    if not norm:
        return ""
    ltr = norm[0].upper()
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            key_path = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\{ltr}\DefaultIcon"
            k = winreg.OpenKey(root, key_path, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(k, "")
            winreg.CloseKey(k)
            if val and str(val).strip():
                return str(val).strip()
        except Exception:
            pass
    return ""


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
# WIDGET: CONTAINER COM AUTO-FLOW / WRAP EM MÚLTIPLAS LINHAS
# ==========================================
class FlowFrame(tk.Frame):
    """
    Container responsivo que acomoda widgets em fluxo contínuo e aumenta automaticamente
    a quantidade de linhas ao redimensionar ou quando o espaço horizontal for reduzido,
    evitando que qualquer botão ou campo de busca seja cortado ou ocultado.
    """
    def __init__(self, master, padx=3, pady=3, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.flow_padx = padx
        self.flow_pady = pady
        self.flow_widgets = []
        self._last_flow_width = 0
        self.bind("<Configure>", self._on_flow_configure)

    def add_widget(self, widget):
        """Adiciona um widget ou frame à fila de fluxo"""
        self.flow_widgets.append(widget)
        widget.grid(row=0, column=len(self.flow_widgets) - 1, padx=self.flow_padx, pady=self.flow_pady, sticky="w")
        self.after_idle(self.reflow)
        return widget

    def reflow(self, width=None):
        """Recalcula e posiciona os widgets linha por linha baseado na largura disponível"""
        if width is None:
            width = self.winfo_width()
        if width <= 20:
            return
        self._last_flow_width = width
        row = 0
        col = 0
        current_x = 0
        for w in self.flow_widgets:
            w.grid_forget()
            req_w = w.winfo_reqwidth()
            # Se ultrapassar a largura disponível e já houver elementos na linha atual, quebra linha
            if current_x + req_w + (self.flow_padx * 2) > width and current_x > 0:
                row += 1
                col = 0
                current_x = 0
            w.grid(row=row, column=col, padx=self.flow_padx, pady=self.flow_pady, sticky="w")
            current_x += req_w + (self.flow_padx * 2)
            col += 1

    def _on_flow_configure(self, event):
        if event.widget is not self:
            return
        if abs(event.width - self._last_flow_width) >= 2:
            self.reflow(event.width)



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

        # Variáveis do Módulo 1: Comparador de Pastas (Diff)
        self.var_diff_dir_a = tk.StringVar(value="")
        self.var_diff_dir_b = tk.StringVar(value="")
        self.var_diff_cmp_size = tk.BooleanVar(value=True)
        self.var_diff_cmp_mtime = tk.BooleanVar(value=True)
        self.var_diff_cmp_ctime = tk.BooleanVar(value=False)
        self.var_diff_cmp_name = tk.BooleanVar(value=False)
        self.var_diff_cmp_integrity = tk.BooleanVar(value=False)
        self.var_diff_recursive = tk.BooleanVar(value=True)
        self.var_diff_ignore_hidden = tk.BooleanVar(value=True)
        self.var_diff_time_tolerance = tk.StringVar(value="2")
        self.diff_results = []
        self.diff_filtered_results = []
        self.diff_active_filter = "all"
        self.diff_search_query = tk.StringVar(value="")
        self.diff_is_running = False
        self.diff_stop_event = threading.Event()
        self.diff_is_copying = False
        self.diff_stop_copy_event = threading.Event()

        # Variáveis do Módulo 2: Mapeador de Unidades de Rede
        self.var_netdrive_letter = tk.StringVar(value="Z:")
        self.var_netdrive_path = tk.StringVar(value="")
        self.var_netdrive_type = tk.StringVar(value="unc")  # 'unc' ou 'subst'
        self.var_netdrive_persistent = tk.BooleanVar(value=True)
        self.var_netdrive_use_creds = tk.BooleanVar(value=False)
        self.var_netdrive_user = tk.StringVar(value="")
        self.var_netdrive_password = tk.StringVar(value="")
        self.mapped_drives_cache = []

        self.load_config()  # Carrega as pastas, geometrias e sashes salvas anteriormente

        self.title("MPFolders v1.1 - Workflow, Backup & Gerenciador")
        self.geometry(self.window_geometry)
        self.configure(bg=COLOR_BG_DARK)
        self.minsize(1000, 700)
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
                        padding=[12, 5], font=("Segoe UI", 9, "bold"), borderwidth=0)
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

        # Barra de Rolagem Horizontal (Dark)
        style.configure("Horizontal.TScrollbar",
                        background=COLOR_BG_CARD,
                        troughcolor=COLOR_BG_DARK,
                        bordercolor=COLOR_BG_DARK,
                        arrowcolor=COLOR_TEXT_MUTED)
        style.map("Horizontal.TScrollbar",
                  background=[("active", COLOR_ACCENT), ("pressed", COLOR_ACCENT_HOVER)],
                  arrowcolor=[("active", COLOR_ACCENT)])

        # Treeview (Dark Theme)
        style.configure("Treeview",
                        background=COLOR_BG_CARD,
                        foreground=COLOR_TEXT_PRIMARY,
                        fieldbackground=COLOR_BG_CARD,
                        rowheight=25,
                        bordercolor=COLOR_BORDER,
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        background=COLOR_BG_INPUT,
                        foreground=COLOR_ACCENT,
                        relief="flat",
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview.Heading",
                  background=[("active", COLOR_BORDER)],
                  foreground=[("active", COLOR_TEXT_PRIMARY)])
        style.map("Treeview",
                  background=[("selected", "#2a3d34")],
                  foreground=[("selected", COLOR_TEXT_PRIMARY)])

        # Progressbar
        style.configure("TProgressbar",
                        background=COLOR_ACCENT,
                        troughcolor=COLOR_BG_INPUT,
                        bordercolor=COLOR_BORDER,
                        lightcolor=COLOR_ACCENT,
                        darkcolor=COLOR_ACCENT)

    def build_ui(self):
        # Header Superior do App
        header_frame = tk.Frame(self, bg=COLOR_BG_DARK, pady=6, padx=15)
        header_frame.pack(fill=tk.X)
        
        lbl_title = ttk.Label(header_frame, text="MPFolders v1.1", style="Header.TLabel")
        lbl_title.pack(anchor="w")
        
        lbl_sub = ttk.Label(header_frame, text="Workflow & Projetos - Ferramenta portátil integrada para automação, comparação e segurança.", style="Sub.TLabel")
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
        self.tab_diff = tk.Frame(self.notebook, bg=COLOR_BG_DARK)
        self.tab_netdrive = tk.Frame(self.notebook, bg=COLOR_BG_DARK)

        self.notebook.add(self.tab_creator, text=" Pastas ")
        self.notebook.add(self.tab_cleaner, text=" Limpar Pastas ")
        self.notebook.add(self.tab_backup, text=" Backup ")
        self.notebook.add(self.tab_renamer, text=" Renomeador ")
        self.notebook.add(self.tab_card_copy, text=" Copia do Cartão ")
        self.notebook.add(self.tab_diff, text=" Comparar Pastas ")
        self.notebook.add(self.tab_netdrive, text=" Unidades de Rede ")

        # Inicialização das Interfaces de cada aba
        self.init_tab_creator()
        self.init_tab_cleaner()
        self.init_tab_backup()
        self.init_tab_renamer()
        self.init_tab_card_copy()
        self.init_tab_diff()
        self.init_tab_netdrive()

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
                    self.sash_diff = data.get("sash_diff", 400)
                    self.sash_netdrive = data.get("sash_netdrive", 400)
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
                self.sash_diff = 400
                self.sash_netdrive = 400
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
            self.sash_diff = 400
            self.sash_netdrive = 400

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
            try:
                sash_df = self.paned_diff.sash_coord(0)[0]
            except Exception:
                sash_df = 400
            try:
                sash_nd = self.paned_netdrive.sash_coord(0)[0]
            except Exception:
                sash_nd = 400

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
                "sash_card_copy": sash_cc,
                "sash_diff": sash_df,
                "sash_netdrive": sash_nd
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
            if hasattr(self, 'paned_diff') and hasattr(self, 'sash_diff'):
                self.paned_diff.sash_place(0, self.sash_diff, 0)
            if hasattr(self, 'paned_netdrive') and hasattr(self, 'sash_netdrive'):
                self.paned_netdrive.sash_place(0, self.sash_netdrive, 0)
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
            os.makedirs(to_long_path(target_path), exist_ok=True)
            
            # Filtra caminhos marcados para criar apenas os diretórios válidos selecionados e inexistentes
            folders_to_process = to_create_folders if existing_folders else selected_folders
            for rel_folder in sorted(folders_to_process):
                full_sub = os.path.join(target_path, os.path.normpath(rel_folder))
                os.makedirs(to_long_path(full_sub), exist_ok=True)
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
                                os.remove(to_long_path(full_filepath))
                                self.log_queue.put((f"[APAGADO] Arquivo lixo: {full_filepath}", "red"))
                            except Exception as e:
                                self.log_queue.put((f"[ERRO] Falha ao deletar arquivo {file}: {str(e)}", "red"))
                        deleted_files_count += 1

        # 2. Limpeza de Pastas Vazias (de baixo para cima na árvore - bottom-up)
        if self.var_clean_empty_dirs.get():
            self.log_queue.put(("Analisando diretórios vazios...", "normal"))
            for root, dirs, files in os.walk(target, topdown=False):
                # Se não contiver arquivos nem subpastas
                if not os.listdir(to_long_path(root)):
                    if root == target:
                        continue
                    if dry_run:
                        self.log_queue.put((f"[SIMULAÇÃO] Remover pasta vazia: {root}", "warning"))
                    else:
                        try:
                            os.rmdir(to_long_path(root))
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
        self.log_queue.put(("  RELATÓRIO RESUMIDO DE ARQUIVOS COPIADOS:", "cyan"))
        self.log_queue.put(("="*45 + "\n", "normal"))

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
            self.log_queue.put(("  (Nenhum arquivo novo ou modificado foi detectado - Estrutura de destino já está idêntica).", "warning"))
        else:
            self.log_queue.put((f"\n  Total de arquivos atualizados nesta rodada: {copied_count}", "green"))

        if summary_section:
            self.log_queue.put(("\n" + "="*45, "normal"))
            self.log_queue.put(("  ESTATÍSTICAS DA OPERAÇÃO:", "cyan"))
            self.log_queue.put(("="*45, "normal"))
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
            self.log_queue.put(("-" * 55, "normal", "renamer"))

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
                self.log_queue.put(("\n=============================================", "normal", "renamer"))
                self.log_queue.put((f"Simulação de renomeação concluída. {len(rename_plan)} arquivos prontos para alteração.", "green", "renamer"))
                self.log_queue.put(("=============================================", "normal", "renamer"))
                return

            # EXECUÇÃO REAL (Duas fases para segurança contra colisões e sobrescritas)
            success_count = 0
            fail_count = 0
            
            # Fase 1: Renomear para nomes temporários únicos
            temp_plan = []
            for old_n, new_n in rename_plan:
                old_path = os.path.join(target_dir, old_n)
                # Garante que o nome temporário nunca exceda 255 caracteres
                root_old, ext_old = os.path.splitext(old_n)
                safe_root = root_old[:220]
                unique_tmp_name = f"__mpf_tmp_{uuid.uuid4().hex[:8]}_{safe_root}{ext_old}"
                tmp_path = os.path.join(target_dir, unique_tmp_name)
                
                try:
                    os.rename(to_long_path(old_path), to_long_path(tmp_path))
                    temp_plan.append((tmp_path, new_n, old_n))
                except PermissionError:
                    self.log_queue.put((f" [ERRO PERMISSÃO] Arquivo em uso ou bloqueado: '{old_n}'", "red", "renamer"))
                    fail_count += 1
                except OSError as oe:
                    win_err = getattr(oe, 'winerror', None)
                    err_no = getattr(oe, 'errno', None)
                    if win_err == 206 or err_no == getattr(errno, 'ENAMETOOLONG', 36):
                        self.log_queue.put((f" [ERRO LIMITE NOME] Nome ou caminho excede o limite do sistema (WinError 206): '{old_n}'", "red", "renamer"))
                    else:
                        self.log_queue.put((f" [ERRO] Falha ao mover para temporário '{old_n}': {str(oe)}", "red", "renamer"))
                    fail_count += 1
                except Exception as e:
                    self.log_queue.put((f" [ERRO] Falha ao mover para temporário '{old_n}': {str(e)}", "red", "renamer"))
                    fail_count += 1

            # Fase 2: Renomear do nome temporário para o nome final
            for tmp_path, new_n, orig_n in temp_plan:
                safe_new_n = truncate_filename_safe(new_n, max_len=255)
                final_path = os.path.join(target_dir, safe_new_n)
                try:
                    if os.path.exists(to_long_path(final_path)):
                        # Caso o destino já exista fisicamente (colisão não prevista)
                        self.log_queue.put((f" [ERRO COLISÃO] O arquivo de destino '{safe_new_n}' já existe no disco!", "red", "renamer"))
                        # Tenta desfazer voltando para o nome original
                        os.rename(to_long_path(tmp_path), to_long_path(os.path.join(target_dir, orig_n)))
                        fail_count += 1
                        continue

                    os.rename(to_long_path(tmp_path), to_long_path(final_path))
                    rename_tag = f" '{orig_n}' ➔ '{safe_new_n}'"
                    if safe_new_n != new_n:
                        rename_tag += " (Nome ajustado para 255 chars)"
                    self.log_queue.put((f" [SUCESSO]{rename_tag}", "green", "renamer"))
                    success_count += 1
                except PermissionError:
                    self.log_queue.put((f" [ERRO PERMISSÃO] Não foi possível renomear temporário para '{safe_new_n}': Arquivo travado.", "red", "renamer"))
                    # Tenta desfazer
                    try:
                        os.rename(to_long_path(tmp_path), to_long_path(os.path.join(target_dir, orig_n)))
                    except Exception:
                        pass
                    fail_count += 1
                except OSError as oe:
                    win_err = getattr(oe, 'winerror', None)
                    err_no = getattr(oe, 'errno', None)
                    err_txt = "Nome excede limite do sistema (WinError 206 / 255 chars)" if (win_err == 206 or err_no == getattr(errno, 'ENAMETOOLONG', 36)) else str(oe)
                    self.log_queue.put((f" [ERRO] Falha ao finalizar '{orig_n}' ➔ '{safe_new_n}': {err_txt}", "red", "renamer"))
                    try:
                        os.rename(to_long_path(tmp_path), to_long_path(os.path.join(target_dir, orig_n)))
                    except Exception:
                        pass
                    fail_count += 1
                except Exception as e:
                    self.log_queue.put((f" [ERRO] Falha ao finalizar '{orig_n}' ➔ '{safe_new_n}': {str(e)}", "red", "renamer"))
                    fail_count += 1

            self.log_queue.put(("\n=============================================", "normal", "renamer"))
            self.log_queue.put((f"Renomeação incremental executada!\nSucesso: {success_count} arquivo(s)\nFalhas: {fail_count} arquivo(s)", "green" if fail_count == 0 else "warning", "renamer"))
            self.log_queue.put(("=============================================", "normal", "renamer"))

        except Exception as e:
            self.log_queue.put((f"[ERRO INESPERADO] {str(e)}", "red", "renamer"))

    # =========================================================================
    # TAB 5: COPIA DO CARTÃO (INGEST E EXTRAÇÃO APLANADA DE SUBPASTAS)
    # =========================================================================
    def init_tab_card_copy(self):
        # Utiliza PanedWindow horizontal para permitir redimensionar as divisões internas
        self.paned_card_copy = tk.PanedWindow(self.tab_card_copy, orient=tk.HORIZONTAL, bg=COLOR_BORDER, bd=0, sashwidth=6, sashrelief="flat", showhandle=True, handlesize=8, handlepad=8)
        self.paned_card_copy.pack(fill=tk.BOTH, expand=True)

        left_container = tk.Frame(self.paned_card_copy, bg=COLOR_BG_DARK, width=390)
        left_panel = ScrollablePanel(left_container, bg=COLOR_BG_DARK, width=390)
        right_panel = ttk.LabelFrame(self.paned_card_copy, text=" Status / Terminal de Cópia do Cartão ")

        self.paned_card_copy.add(left_container, minsize=370)
        self.paned_card_copy.add(right_panel, minsize=400)

        # Flags de controle de operação
        self.card_copy_cancel = False
        self.card_copy_running = False

        # --- BOTÕES DE AÇÃO FIXADOS NA BASE DO PAINEL ESQUERDO (SEMPRE VISÍVEIS) ---
        f_actions = tk.Frame(left_container, bg=COLOR_BG_DARK)
        f_actions.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=(6, 10))

        self.btn_card_copy_run = RoundedButton(
            f_actions, hover_bg=COLOR_ACCENT_HOVER, hover_fg="#ffffff",
            text="Iniciar Cópia do Cartão", bg=COLOR_ACCENT, fg="#ffffff",
            font=("Segoe UI", 10, "bold"), height=36, command=self.run_card_copy_real
        )
        self.btn_card_copy_run.pack(fill=tk.X, pady=(0, 4))

        self.btn_card_copy_sim = RoundedButton(
            f_actions, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Simulação / Prévia da Cópia (Sem gravar)", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY,
            font=("Segoe UI", 9, "bold"), height=32, command=self.run_card_copy_simulation
        )
        self.btn_card_copy_sim.pack(fill=tk.X, pady=(0, 4))

        self.btn_card_copy_cancel = RoundedButton(
            f_actions, hover_bg="#a83232", hover_fg="#ffffff",
            text="Interromper Cópia", bg="#6e2222", fg="#ffffff",
            font=("Segoe UI", 9, "bold"), height=30, command=self.cancel_card_copy
        )
        self.btn_card_copy_cancel.pack(fill=tk.X)
        self.btn_card_copy_cancel.pack_forget()

        left_panel.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # --- SELEÇÃO DE ORIGEM ---
        lf_src = ttk.LabelFrame(left_panel.content, text=" Origem no Cartão / Gravador / Câmera ")
        lf_src.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(8, 3))

        ttk.Label(lf_src, text="Pasta Mãe no Cartão (ex: K:\\MULTI\\FOLDER01 ou K:\\DCIM):").pack(anchor="w", padx=8, pady=(3, 1))
        self.var_card_src = tk.StringVar(value="")
        entry_card_src = tk.Entry(lf_src, textvariable=self.var_card_src, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_card_src.pack(fill=tk.X, padx=8, pady=2)

        btn_browse_src = HoverButton(
            lf_src, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Procurar Pasta Mãe", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=self.browse_card_src
        )
        btn_browse_src.pack(anchor="e", padx=8, pady=(2, 5))

        # --- SELEÇÃO DE DESTINO ---
        lf_dst = ttk.LabelFrame(left_panel.content, text=" Pasta de Destino (Aplanada) ")
        lf_dst.pack(side=tk.TOP, fill=tk.X, padx=15, pady=3)

        ttk.Label(lf_dst, text="Diretório onde todos os arquivos serão copiados diretamente:").pack(anchor="w", padx=8, pady=(3, 1))
        self.var_card_dst = tk.StringVar(value="")
        entry_card_dst = tk.Entry(lf_dst, textvariable=self.var_card_dst, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_card_dst.pack(fill=tk.X, padx=8, pady=2)

        f_dst_btns = tk.Frame(lf_dst, bg=COLOR_BG_CARD)
        f_dst_btns.pack(fill=tk.X, padx=8, pady=(2, 5))

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
        lf_exts.pack(side=tk.TOP, fill=tk.X, padx=15, pady=3)

        self.var_card_ext_aud = tk.BooleanVar(value=True)
        self.var_card_ext_vid = tk.BooleanVar(value=True)
        self.var_card_ext_img = tk.BooleanVar(value=True)
        self.var_card_ext_all = tk.BooleanVar(value=False)

        cb_aud = tk.Checkbutton(lf_exts, text="Áudios (.wav, .mp3, .aac, .m4a, .flac, .aif...)", variable=self.var_card_ext_aud, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_aud.pack(anchor="w", padx=8, pady=1)

        cb_vid = tk.Checkbutton(lf_exts, text="Vídeos (.mp4, .mov, .mkv, .avi, .mxf, .braw...)", variable=self.var_card_ext_vid, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_vid.pack(anchor="w", padx=8, pady=1)

        cb_img = tk.Checkbutton(lf_exts, text="Fotos / RAW (.jpg, .png, .raw, .cr2, .cr3, .arw, .dng...)", variable=self.var_card_ext_img, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_img.pack(anchor="w", padx=8, pady=1)

        cb_all = tk.Checkbutton(lf_exts, text="Todos os Arquivos (*)", variable=self.var_card_ext_all, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_all.pack(anchor="w", padx=8, pady=1)

        ttk.Label(lf_exts, text="Outras Extensões (ex: .xml, .lrf ou separadas por vírgula):").pack(anchor="w", padx=8, pady=(2, 1))
        self.var_card_ext_custom = tk.StringVar(value="")
        entry_custom_ext = tk.Entry(lf_exts, textvariable=self.var_card_ext_custom, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_custom_ext.pack(fill=tk.X, padx=8, pady=(0, 4))

        # --- FILTRO POR DATA DE CRIAÇÃO ---
        lf_date = ttk.LabelFrame(left_panel.content, text=" Filtro por Data de Criação ")
        lf_date.pack(side=tk.TOP, fill=tk.X, padx=15, pady=3)

        self.var_card_filter_date = tk.BooleanVar(value=False)
        cb_filter_date = tk.Checkbutton(
            lf_date, text="Filtrar apenas arquivos criados em data específica",
            variable=self.var_card_filter_date, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY,
            selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD,
            command=self._on_toggle_card_date_filter
        )
        cb_filter_date.pack(anchor="w", padx=8, pady=(3, 1))

        self.f_card_date_inputs = tk.Frame(lf_date, bg=COLOR_BG_CARD)
        self.f_card_date_inputs.pack(fill=tk.X, padx=8, pady=(1, 2))

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
        self.lbl_card_date_hint.pack(anchor="w", padx=8, pady=(0, 3))

        for var in (self.var_card_day, self.var_card_month, self.var_card_year):
            var.trace_add("write", lambda *args: self._on_card_date_change())

        self._on_toggle_card_date_filter()

        # --- TRATAMENTO DE CONFLITOS DE NOMES ---
        lf_conflict = ttk.LabelFrame(left_panel.content, text=" Tratamento de Conflito de Nomes ")
        lf_conflict.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(3, 6))

        ttk.Label(lf_conflict, text="Ação ao detectar arquivo com mesmo nome:").pack(anchor="w", padx=8, pady=(3, 1))
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
        cb_always_prefix.pack(anchor="w", padx=8, pady=(2, 5))

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

    @staticmethod
    def _clean_card_path(raw_path):
        """Limpa aspas e normaliza caminhos, garantindo barra final em raízes de unidade (ex: K: -> K:\\)."""
        if not raw_path:
            return ""
        p = str(raw_path).strip().strip('"').strip("'")
        if not p:
            return ""
        if sys.platform == "win32" and len(p) == 2 and p[1] == ":" and p[0].isalpha():
            return p.upper() + "\\"
        norm_p = os.path.normpath(p)
        if sys.platform == "win32" and len(norm_p) == 2 and norm_p[1] == ":" and norm_p[0].isalpha():
            return norm_p.upper() + "\\"
        return norm_p

    def browse_card_src(self):
        cur_src = self._clean_card_path(self.var_card_src.get())
        init_dir = cur_src if (cur_src and os.path.exists(to_long_path(cur_src))) else "K:\\" if os.path.exists("K:\\") else os.getcwd()
        dir_selected = filedialog.askdirectory(initialdir=init_dir, title="Selecione a Pasta Mãe no Cartão / Drive (ex: FOLDER01 ou DCIM)")
        if dir_selected:
            self.var_card_src.set(self._clean_card_path(dir_selected))

    def browse_card_dst(self):
        cur_dst = self._clean_card_path(self.var_card_dst.get())
        init_dir = cur_dst if (cur_dst and os.path.exists(to_long_path(cur_dst))) else os.getcwd()
        dir_selected = filedialog.askdirectory(initialdir=init_dir, title="Selecione a Pasta de Destino para os Arquivos")
        if dir_selected:
            self.var_card_dst.set(self._clean_card_path(dir_selected))

    def use_project_dest_for_card(self):
        proj_root = getattr(self, "var_creator_root", None)
        if proj_root and proj_root.get():
            cleaned = self._clean_card_path(proj_root.get())
            if cleaned and os.path.exists(to_long_path(cleaned)):
                self.var_card_dst.set(cleaned)
                return
        messagebox.showinfo("Informação", "Nenhum diretório raiz de projetos válido configurado na aba 'Pastas'.", parent=self)

    def clear_card_log(self):
        self.card_terminal.delete("1.0", tk.END)
        self.progress_card['value'] = 0
        self.lbl_card_status.config(text="Pronto.")

    def open_card_dst_folder(self):
        dst = self._clean_card_path(self.var_card_dst.get())
        if dst and os.path.exists(to_long_path(dst)):
            try:
                if sys.platform == "win32":
                    os.startfile(from_long_path(dst))
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
            st = os.stat(to_long_path(filepath))
            m_date = None
            c_date = None

            try:
                if st.st_mtime and st.st_mtime > 0:
                    m_date = datetime.date.fromtimestamp(st.st_mtime)
            except (ValueError, OverflowError, OSError):
                m_date = None

            btime = getattr(st, 'st_birthtime', None)
            if btime is not None and btime > 0:
                try:
                    c_date = datetime.date.fromtimestamp(btime)
                except (ValueError, OverflowError, OSError):
                    c_date = None

            if c_date is None:
                if sys.platform == "win32":
                    try:
                        if st.st_ctime and st.st_ctime > 0:
                            c_date = datetime.date.fromtimestamp(st.st_ctime)
                    except (ValueError, OverflowError, OSError):
                        c_date = m_date
                else:
                    c_date = m_date

            if m_date is None:
                m_date = c_date

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

    def _prompt_threadsafe_yesno(self, title, message):
        """Exibe messagebox.askyesno de forma thread-safe na thread principal da GUI."""
        res_queue = queue.Queue()
        def _ask():
            try:
                ans = messagebox.askyesno(title, message, parent=self)
                res_queue.put(bool(ans))
            except Exception:
                res_queue.put(False)
        self.after(0, _ask)
        return res_queue.get()

    def run_card_copy_simulation(self):
        if self.card_copy_running:
            return
        src = self._clean_card_path(self.var_card_src.get())
        dst = self._clean_card_path(self.var_card_dst.get())

        if not src or not dst:
            messagebox.showerror("Campos Obrigatórios", "Por favor, selecione a pasta mãe de Origem e a pasta de Destino.", parent=self)
            return

        self.var_card_src.set(src)
        self.var_card_dst.set(dst)

        if not os.path.exists(to_long_path(src)):
            messagebox.showerror("Origem Inexistente", "A pasta mãe de Origem selecionada não existe.", parent=self)
            return

        if os.path.abspath(from_long_path(src)).rstrip("\\/").lower() == os.path.abspath(from_long_path(dst)).rstrip("\\/").lower():
            messagebox.showerror("Erro de Loops", "Origem e destino não podem ser a mesma pasta física.", parent=self)
            return

        target_date = self.get_selected_card_filter_date()
        if target_date is False:
            return

        self._prepare_card_copy_ui()
        threading.Thread(target=self._card_copy_worker, args=(src, dst, True, target_date), daemon=True).start()

    def run_card_copy_real(self):
        if self.card_copy_running:
            return
        src = self._clean_card_path(self.var_card_src.get())
        dst = self._clean_card_path(self.var_card_dst.get())

        if not src or not dst:
            messagebox.showerror("Campos Obrigatórios", "Por favor, selecione a pasta mãe de Origem e a pasta de Destino.", parent=self)
            return

        self.var_card_src.set(src)
        self.var_card_dst.set(dst)

        if not os.path.exists(to_long_path(src)):
            messagebox.showerror("Origem Inexistente", "A pasta mãe de Origem selecionada não existe.", parent=self)
            return

        if not os.path.exists(to_long_path(dst)):
            try:
                os.makedirs(to_long_path(dst), exist_ok=True)
            except Exception as e:
                messagebox.showerror("Erro de Destino", f"Não foi possível criar a pasta de destino: {str(e)}", parent=self)
                return

        if os.path.abspath(from_long_path(src)).rstrip("\\/").lower() == os.path.abspath(from_long_path(dst)).rstrip("\\/").lower():
            messagebox.showerror("Erro de Loops", "Origem e destino não podem ser a mesma pasta física.", parent=self)
            return

        try:
            rel = safe_relpath(dst, src)
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

    def _copy_card_file_streaming(self, lp_src, lp_dst, idx, total_files, final_name, bytes_copied_so_far, total_bytes):
        """
        Copia um arquivo em blocos de 4MB com atualização de progresso em tempo real,
        suporte a interrupção imediata, remoção preventiva de atributo somente-leitura no destino,
        retentativas contra locks temporários (WinError 32) e preservação segura de metadados.
        """
        chunk_size = 4 * 1024 * 1024  # 4 MB
        max_retries = 3
        last_err = None

        for attempt in range(max_retries):
            if self.card_copy_cancel:
                return False, "Cancelado"
            try:
                if os.path.exists(lp_dst):
                    try:
                        os.chmod(lp_dst, 0o666)
                    except Exception:
                        pass

                written = 0
                last_ui_update = 0.0
                with open(lp_src, "rb") as fsrc, open(lp_dst, "wb") as fdst:
                    while True:
                        if self.card_copy_cancel:
                            break
                        buf = fsrc.read(chunk_size)
                        if not buf:
                            break
                        fdst.write(buf)
                        written += len(buf)
                        now_ts = time.monotonic()
                        if now_ts - last_ui_update >= 0.15:
                            last_ui_update = now_ts
                            cur_total = bytes_copied_so_far + written
                            pct = int((cur_total / total_bytes) * 100) if total_bytes > 0 else int((idx / total_files) * 100)
                            pct = max(0, min(99, pct))
                            status_str = f"Copiando {idx}/{total_files} ({format_size(cur_total)} / {format_size(total_bytes)}) - {final_name}"
                            self.after(0, lambda p=pct, s=status_str: self._update_card_progress(p, s))

                if self.card_copy_cancel:
                    try:
                        if os.path.exists(lp_dst):
                            os.remove(lp_dst)
                    except Exception:
                        pass
                    return False, "Cancelado"

                # Preserva timestamps e metadados de forma tolerante (não invalida a cópia se o destino recusar ACL/atributos)
                try:
                    shutil.copystat(lp_src, lp_dst)
                except Exception:
                    pass

                # Garante que o arquivo copiado no destino não fique travado como Read-Only vindo do cartão FAT32/exFAT
                try:
                    os.chmod(lp_dst, 0o666)
                except Exception:
                    pass

                return True, None

            except PermissionError as pe:
                last_err = pe
                if getattr(pe, 'winerror', None) == 32 and attempt < max_retries - 1:
                    time.sleep(0.35 * (attempt + 1))
                    continue
                raise
            except OSError as oe:
                last_err = oe
                win_err = getattr(oe, 'winerror', None)
                if win_err == 32 and attempt < max_retries - 1:
                    time.sleep(0.35 * (attempt + 1))
                    continue
                raise

        if last_err:
            raise last_err
        return False, "Falha desconhecida"

    def _card_copy_worker(self, src_dir, dst_dir, dry_run=True, target_date=None):
        try:
            self.card_copy_running = True
            self.card_copy_cancel = False

            src_dir = self._clean_card_path(src_dir)
            dst_dir = self._clean_card_path(dst_dir)

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
                selected_exts.update({
                    ".wav", ".bwf", ".mp3", ".aac", ".m4a", ".flac", ".aif", ".aiff",
                    ".ogg", ".wma", ".opus", ".caf", ".amr", ".3gp"
                })
            if self.var_card_ext_vid.get():
                selected_exts.update({
                    ".mp4", ".mov", ".mkv", ".avi", ".mxf", ".braw", ".prores",
                    ".mts", ".m2ts", ".ts", ".mpg", ".mpeg", ".wmv", ".webm",
                    ".r3d", ".ari", ".crm", ".insv", ".360", ".lrv"
                })
            if self.var_card_ext_img.get():
                selected_exts.update({
                    ".jpg", ".jpeg", ".png", ".raw", ".cr2", ".cr3", ".arw",
                    ".nef", ".nrw", ".dng", ".rw2", ".orf", ".raf", ".pef",
                    ".srw", ".heic", ".heif", ".hif", ".tif", ".tiff", ".bmp", ".webp"
                })

            custom_ext = self.var_card_ext_custom.get().strip()
            if custom_ext:
                for ce in custom_ext.split(","):
                    ce = ce.strip().lower()
                    if ce:
                        if ce == "*":
                            match_all = True
                        else:
                            if not ce.startswith("."):
                                ce = f".{ce}"
                            if ce == ".*":
                                match_all = True
                            else:
                                selected_exts.add(ce)

            if not match_all and not selected_exts:
                msg_no_ext = "Nenhuma extensão ou tipo de arquivo foi selecionado! Marque Áudios, Vídeos, Fotos/RAW ou Todos os Arquivos (*)."
                self.log_queue.put((f"[ERRO] {msg_no_ext}", "red", "card_copy"))
                self.after(0, lambda: self._update_card_progress(0, "Erro: Nenhum tipo de arquivo selecionado."))
                self.after(0, lambda m=msg_no_ext: messagebox.showerror("Tipo de Arquivo Obrigatório", m, parent=self))
                return

            self.log_queue.put((f"Escaneando estrutura de subpastas a partir da pasta mãe...", "muted", "card_copy"))
            self.after(0, lambda: self._update_card_progress(0, "Escaneando arquivos no cartão..."))

            found_files = []       # list of (full_path, subfolder_name, filename, size_bytes, date_str)
            date_ignored_files = [] # list of (full_path, subfolder_name, filename, size_bytes, date_str)
            ignored_count = 0
            date_ignored_count = 0
            SYSTEM_IGNORES = {".ds_store", "thumbs.db", "desktop.ini", "wpsettings.dat", "indexervolumeguid", "autorun.inf"}
            SYSTEM_DIRS_IGNORE = {
                "system volume information", "$recycle.bin", "recycler",
                "lost.dir", ".trashes", ".spotlight-v100", ".fseventsd", "__macosx"
            }

            walk_src = to_long_path(src_dir)
            for root_raw, dirs, files in os.walk(walk_src):
                if self.card_copy_cancel:
                    self.log_queue.put(("[CANCELADO] Operação interrompida pelo usuário.", "warning", "card_copy"))
                    self.after(0, lambda: self._update_card_progress(0, "Operação cancelada."))
                    return

                # Filtra diretórios ocultos/sistema do cartão de memória
                dirs[:] = [d for d in dirs if d.lower() not in SYSTEM_DIRS_IGNORE and not d.startswith(".")]

                root = from_long_path(root_raw)
                rel_dir = safe_relpath(root, src_dir)
                if rel_dir == ".":
                    subfolder_name = os.path.basename(src_dir.rstrip("\\/"))
                else:
                    subfolder_name = os.path.basename(root.rstrip("\\/"))
                if not subfolder_name:
                    drv_part = os.path.splitdrive(src_dir)[0].rstrip(":")
                    subfolder_name = drv_part if drv_part else "CARD"

                for f in files:
                    if f.lower() in SYSTEM_IGNORES or f.startswith("._"):
                        continue

                    ext = os.path.splitext(f)[1].lower()
                    if match_all or ext in selected_exts:
                        full_path = os.path.join(root, f)
                        try:
                            c_date, m_date = self.get_file_dates(full_path)
                            sz = os.path.getsize(to_long_path(full_path))
                            effective_date = m_date or c_date
                            d_str = effective_date.strftime("%d/%m/%Y") if effective_date else "N/A"
                            file_entry = (full_path, subfolder_name, f, sz, d_str)

                            if target_date:
                                # Verifica se o arquivo foi criado ou gravado na data especificada
                                if c_date != target_date and m_date != target_date:
                                    date_ignored_count += 1
                                    date_ignored_files.append(file_entry)
                                    continue

                            found_files.append(file_entry)
                        except Exception as e:
                            self.log_queue.put((f"[AVISO LEITURA] Erro ao ler metadados de '{f}': {e}", "warning", "card_copy"))
                            ignored_count += 1
                    else:
                        ignored_count += 1

            if not found_files:
                if target_date and date_ignored_count > 0:
                    distinct_dates = sorted({item[4] for item in date_ignored_files if item[4] != "N/A"})
                    dates_preview = ", ".join(distinct_dates[:6]) + ("..." if len(distinct_dates) > 6 else "")
                    self.log_queue.put((
                        f"[AVISO] Nenhum arquivo com a data {target_date.strftime('%d/%m/%Y')} foi encontrado, "
                        f"mas existem {date_ignored_count} arquivo(s) no cartão com a(s) data(s): {dates_preview}.",
                        "warning", "card_copy"
                    ))
                    if not dry_run:
                        prompt_msg = (
                            f"Nenhum arquivo gravado em {target_date.strftime('%d/%m/%Y')} foi encontrado.\n\n"
                            f"Porém, foram encontrados {date_ignored_count} arquivo(s) elegíveis no cartão com a(s) data(s):\n"
                            f"• {dates_preview}\n"
                            f"(Isso ocorre com frequência quando a bateria/relógio interno do gravador ou câmera reseta, ex: 01/01/2014).\n\n"
                            f"Deseja copiar esses {date_ignored_count} arquivo(s) mesmo assim?"
                        )
                        if self._prompt_threadsafe_yesno("Diferença de Data no Cartão Detectada", prompt_msg):
                            found_files = date_ignored_files
                            date_ignored_count = 0
                            self.log_queue.put(("[INFO] Prosseguindo com a cópia dos arquivos ignorando a divergência de data do relógio do cartão.", "cyan", "card_copy"))
                        else:
                            self.after(0, lambda: self._update_card_progress(0, "Nenhum arquivo copiado (filtro de data)."))
                            return
                    else:
                        warn_sim = (
                            f"Nenhum arquivo com a data {target_date.strftime('%d/%m/%Y')} foi encontrado.\n\n"
                            f"Existem {date_ignored_count} arquivo(s) no cartão com a(s) data(s): {dates_preview}.\n"
                            f"Desmarque o filtro de data ou ajuste a data para copiá-los."
                        )
                        self.after(0, lambda: self._update_card_progress(0, f"Simulação: 0 arquivos na data {target_date.strftime('%d/%m/%Y')}."))
                        self.after(0, lambda m=warn_sim: messagebox.showwarning("Filtro de Data", m, parent=self))
                        return
                else:
                    ext_hint = f" ({ignored_count} arquivo(s) de outros formatos foram ignorados pelo filtro de extensões)" if ignored_count > 0 else ""
                    msg_empty = f"Nenhum arquivo compatível foi encontrado nas subpastas de '{src_dir}'{ext_hint}."
                    self.log_queue.put((f"[AVISO] {msg_empty}", "warning", "card_copy"))
                    self.after(0, lambda: self._update_card_progress(0, "Nenhum arquivo compatível encontrado na origem."))
                    self.after(0, lambda m=msg_empty: messagebox.showwarning("Nenhum Arquivo Encontrado", m + "\n\nVerifique se a pasta de origem está correta e se os tipos de mídia desejados (Áudios, Vídeos, Fotos/RAW ou Todos) estão marcados.", parent=self))
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
            self.log_queue.put(("-" * 55, "normal", "card_copy"))

            # Verificação de espaço livre em disco
            if not dry_run:
                try:
                    os.makedirs(to_long_path(dst_dir), exist_ok=True)
                    usage = shutil.disk_usage(to_long_path(dst_dir) if os.path.exists(to_long_path(dst_dir)) else dst_dir)
                    free_bytes = usage.free
                    if free_bytes > 0 and free_bytes < total_bytes:
                        err_space = f"Espaço insuficiente no destino! Livre: {format_size(free_bytes)} | Necessário: {format_size(total_bytes)}"
                        self.log_queue.put((f"[ERRO CRÍTICO] {err_space}", "red", "card_copy"))
                        self.after(0, lambda: self._update_card_progress(0, "Erro: Espaço em disco insuficiente no destino."))
                        self.after(0, lambda m=err_space: messagebox.showerror("Espaço Insuficiente", m, parent=self))
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
                for f in os.listdir(to_long_path(dst_dir)):
                    existing_in_dst.add(f.lower())
            except Exception:
                pass

            planned_names = set()
            success_count = 0
            fail_count = 0
            skipped_count = 0
            bytes_copied = 0
            total_long_paths = 0
            total_truncated_names = 0

            start_time = datetime.datetime.now()

            for idx, (src_path, subfolder, orig_filename, f_size, f_date_str) in enumerate(found_files, 1):
                if self.card_copy_cancel:
                    self.log_queue.put(("\n[INTERROMPIDO] Cópia cancelada pelo usuário.", "warning", "card_copy"))
                    break

                if always_prefix:
                    base_target = f"{subfolder}_{orig_filename}"
                else:
                    base_target = orig_filename

                # Sanitização preventiva para respeitar o teto de 255 chars preservando a extensão original
                orig_base_len = len(base_target)
                base_target = truncate_filename_safe(base_target, 255)
                if len(base_target) < orig_base_len:
                    total_truncated_names += 1

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
                        pref_candidate = truncate_filename_safe(f"{subfolder}_{orig_filename}", 255)
                        if pref_candidate.lower() in existing_in_dst or pref_candidate.lower() in planned_names:
                            root_name, ext_part = os.path.splitext(pref_candidate)
                            c = 1
                            while True:
                                suffix_str = f"_{c}"
                                allowed_stem = 255 - len(ext_part) - len(suffix_str)
                                cand_root = root_name[:allowed_stem] if allowed_stem > 0 else root_name
                                cand_name = f"{cand_root}{suffix_str}{ext_part}"
                                if cand_name.lower() not in existing_in_dst and cand_name.lower() not in planned_names:
                                    final_name = cand_name
                                    break
                                c += 1
                        else:
                            final_name = pref_candidate
                    elif action == "suffix":
                        root_name, ext_part = os.path.splitext(base_target)
                        c = 1
                        while True:
                            suffix_str = f"_{c}"
                            allowed_stem = 255 - len(ext_part) - len(suffix_str)
                            cand_root = root_name[:allowed_stem] if allowed_stem > 0 else root_name
                            cand_name = f"{cand_root}{suffix_str}{ext_part}"
                            if cand_name.lower() not in existing_in_dst and cand_name.lower() not in planned_names:
                                final_name = cand_name
                                break
                            c += 1

                # Assegura que final_name não exceda 255 chars preservando extensão
                final_name = truncate_filename_safe(final_name, 255)
                planned_names.add(final_name.lower())
                final_dst_path = os.path.join(dst_dir, final_name)

                if len(final_dst_path) >= 260:
                    total_long_paths += 1

                if dry_run:
                    conflict_tag = " (Renomeado/Resolvido)" if final_name != orig_filename else ""
                    if len(final_dst_path) >= 260:
                        conflict_tag += " [Caminho Longo >260]"
                    self.log_queue.put((f" [PRÉVIA {idx}/{total_files}] '{subfolder}/{orig_filename}' [{f_date_str}] ➔ '{final_name}' ({format_size(f_size)}){conflict_tag}", "normal", "card_copy"))
                    pct = int((idx / total_files) * 100)
                    self.after(0, lambda p=pct, i=idx, t=total_files: self._update_card_progress(p, f"Simulação: {i}/{t} arquivos analisados..."))
                else:
                    try:
                        pct = int((bytes_copied / total_bytes) * 100) if total_bytes > 0 else int((idx / total_files) * 100)
                        status_str = f"Copiando {idx}/{total_files} ({format_size(bytes_copied)} / {format_size(total_bytes)}) - {final_name}"
                        self.after(0, lambda p=pct, s=status_str: self._update_card_progress(p, s))

                        lp_src = to_long_path(src_path)
                        lp_dst = to_long_path(final_dst_path)
                        os.makedirs(to_long_path(os.path.dirname(final_dst_path)), exist_ok=True)

                        ok_copy, copy_err = self._copy_card_file_streaming(
                            lp_src, lp_dst, idx, total_files, final_name, bytes_copied, total_bytes
                        )
                        if not ok_copy:
                            if copy_err == "Cancelado":
                                self.log_queue.put(("\n[INTERROMPIDO] Cópia cancelada pelo usuário.", "warning", "card_copy"))
                                break
                            self.log_queue.put((f" [ERRO] Falha ao copiar '{orig_filename}': {copy_err}", "red", "card_copy"))
                            fail_count += 1
                            continue

                        copied_size = os.path.getsize(lp_dst)
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
                        win_err = getattr(e, 'winerror', None)
                        err_no = getattr(e, 'errno', None)
                        if win_err == 206 or err_no == getattr(errno, 'ENAMETOOLONG', 36):
                            self.log_queue.put((f" [ERRO CAMINHO/NOME] Caminho ou nome excede o limite do sistema (WinError 206 / MAX_PATH): '{final_name}'", "red", "card_copy"))
                        elif win_err == 123:
                            self.log_queue.put((f" [ERRO NOME INVÁLIDO] Caracteres ou sintaxe inválida no nome para este disco (WinError 123): '{final_name}'", "red", "card_copy"))
                        else:
                            self.log_queue.put((f" [ERRO I/O] Falha de leitura/escrita em '{orig_filename}': {e}", "red", "card_copy"))
                        fail_count += 1
                    except Exception as e:
                        self.log_queue.put((f" [ERRO] Falha ao copiar '{orig_filename}': {e}", "red", "card_copy"))
                        fail_count += 1

            duration = datetime.datetime.now() - start_time
            dur_str = f"{int(duration.total_seconds())}s"

            self.log_queue.put(("\n===========================================================", "cyan", "card_copy"))
            if dry_run:
                self.log_queue.put((f"Simulação concluída com sucesso! ({dur_str})", "green", "card_copy"))
                self.log_queue.put((f"Total de arquivos simulados: {total_files} | Volume: {format_size(total_bytes)}", "normal", "card_copy"))
                if total_long_paths > 0:
                    self.log_queue.put((f" • Previsão de caminhos extensos (>260 chars): {total_long_paths} (suporte a \\\\?\\ ativado)", "cyan", "card_copy"))
                if total_truncated_names > 0:
                    self.log_queue.put((f" • Nomes ajustados para o limite de 255 chars: {total_truncated_names} (extensões preservadas)", "warning", "card_copy"))
                self.log_queue.put((f"Para efetivar a cópia física no disco, clique em 'Iniciar Cópia do Cartão'.", "warning", "card_copy"))
                self.after(0, lambda: self._update_card_progress(100, f"Simulação concluída: {total_files} arquivos prontos."))
            else:
                self.log_queue.put((f"Processo de Cópia Finalizado em {dur_str}!", "green" if fail_count == 0 else "warning", "card_copy"))
                self.log_queue.put((f"Sucesso: {success_count} arquivo(s) copiado(s) ({format_size(bytes_copied)})", "green", "card_copy"))
                if total_long_paths > 0:
                    self.log_queue.put((f" • Caminhos extensos (>260 chars) processados via \\\\?\\: {total_long_paths}", "cyan", "card_copy"))
                if total_truncated_names > 0:
                    self.log_queue.put((f" • Nomes ajustados para o limite de 255 chars: {total_truncated_names}", "warning", "card_copy"))
                if skipped_count > 0:
                    self.log_queue.put((f"Pulados: {skipped_count} arquivo(s)", "muted", "card_copy"))
                if fail_count > 0:
                    self.log_queue.put((f"Falhas: {fail_count} arquivo(s)", "red", "card_copy"))
                self.after(0, lambda: self._update_card_progress(100, f"Concluído! {success_count} copiados, {fail_count} falhas."))
            self.log_queue.put(("===========================================================", "cyan", "card_copy"))

        except Exception as e:
            self.log_queue.put((f"[FALHA GERAL] {str(e)}", "red", "card_copy"))
            self.after(0, lambda err=str(e): self._update_card_progress(0, f"Falha na cópia: {err}"))
        finally:
            self.card_copy_running = False
            self.after(0, self._reset_card_copy_ui)

    # =========================================================================
    # TAB 6: COMPARADOR DE PASTAS E ARQUIVOS (FOLDER & FILE DIFF)
    # =========================================================================
    def init_tab_diff(self):
        self.paned_diff = tk.PanedWindow(self.tab_diff, orient=tk.HORIZONTAL, bg=COLOR_BORDER, bd=0, sashwidth=6, sashrelief="flat", showhandle=True, handlesize=8, handlepad=8)
        self.paned_diff.pack(fill=tk.BOTH, expand=True)

        left_panel = ScrollablePanel(self.paned_diff, bg=COLOR_BG_DARK, width=400)
        right_panel = ttk.LabelFrame(self.paned_diff, text=" Resultados da Comparação ")

        self.paned_diff.add(left_panel, minsize=370)
        self.paned_diff.add(right_panel, minsize=420)

        # --- SELEÇÃO DE PASTAS ---
        lf_dirs = ttk.LabelFrame(left_panel.content, text=" Diretórios para Análise ")
        lf_dirs.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(15, 8))

        # Pasta A (Referência)
        ttk.Label(lf_dirs, text="Pasta A (Referência / Origem):").pack(anchor="w", padx=8, pady=(6, 2))
        entry_a = tk.Entry(lf_dirs, textvariable=self.var_diff_dir_a, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_a.pack(fill=tk.X, padx=8, pady=2)

        f_btn_a = tk.Frame(lf_dirs, bg=COLOR_BG_CARD)
        f_btn_a.pack(fill=tk.X, padx=8, pady=(1, 2))
        btn_browse_a = HoverButton(
            f_btn_a, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Procurar Pasta A", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=self.browse_diff_dir_a
        )
        btn_browse_a.pack(side=tk.RIGHT)

        self.lbl_diff_storage_a = tk.Label(lf_dirs, text="", font=("Segoe UI", 8, "bold"), bg=COLOR_BG_CARD, fg="#81c784", anchor="w")
        self.lbl_diff_storage_a.pack(fill=tk.X, padx=8, pady=(0, 4))

        # Pasta B (Comparação)
        ttk.Label(lf_dirs, text="Pasta B (Comparação / Destino):").pack(anchor="w", padx=8, pady=(4, 2))
        entry_b = tk.Entry(lf_dirs, textvariable=self.var_diff_dir_b, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_b.pack(fill=tk.X, padx=8, pady=2)

        f_btn_b = tk.Frame(lf_dirs, bg=COLOR_BG_CARD)
        f_btn_b.pack(fill=tk.X, padx=8, pady=(2, 2))

        btn_swap = HoverButton(
            f_btn_b, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Inverter (A ⇄ B)", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, bd=1, relief="solid",
            font=("Segoe UI", 8), command=self.swap_diff_dirs
        )
        btn_swap.pack(side=tk.LEFT)

        btn_browse_b = HoverButton(
            f_btn_b, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Procurar Pasta B", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=self.browse_diff_dir_b
        )
        btn_browse_b.pack(side=tk.RIGHT)

        self.lbl_diff_storage_b = tk.Label(lf_dirs, text="", font=("Segoe UI", 8, "bold"), bg=COLOR_BG_CARD, fg="#81c784", anchor="w")
        self.lbl_diff_storage_b.pack(fill=tk.X, padx=8, pady=(0, 6))

        # --- METADADOS E CRITÉRIOS DE COMPARAÇÃO ---
        lf_meta = ttk.LabelFrame(left_panel.content, text=" Metadados & Critérios a Comparar ")
        lf_meta.pack(side=tk.TOP, fill=tk.X, padx=15, pady=8)

        cb_name = tk.Checkbutton(lf_meta, text="Nome do Arquivo (Maiúsculas / Minúsculas)", variable=self.var_diff_cmp_name,
                                 bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_name.pack(anchor="w", padx=8, pady=3)

        cb_integrity = tk.Checkbutton(lf_meta, text="Verificação de Integridade (Hash SHA-256)", variable=self.var_diff_cmp_integrity,
                                      bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_integrity.pack(anchor="w", padx=8, pady=3)

        cb_size = tk.Checkbutton(lf_meta, text="Tamanho do Arquivo (Bytes)", variable=self.var_diff_cmp_size,
                                 bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_size.pack(anchor="w", padx=8, pady=3)

        cb_mtime = tk.Checkbutton(lf_meta, text="Data de Última Modificação (mtime)", variable=self.var_diff_cmp_mtime,
                                  bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_mtime.pack(anchor="w", padx=8, pady=3)

        cb_ctime = tk.Checkbutton(lf_meta, text="Data de Criação (ctime / birthtime)", variable=self.var_diff_cmp_ctime,
                                  bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_ctime.pack(anchor="w", padx=8, pady=3)

        cb_recur = tk.Checkbutton(lf_meta, text="Varredura Recursiva (Incluir Subpastas)", variable=self.var_diff_recursive,
                                  bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_recur.pack(anchor="w", padx=8, pady=3)

        cb_ignore = tk.Checkbutton(lf_meta, text="Ignorar arquivos de sistema (.DS_Store, Thumbs.db...)", variable=self.var_diff_ignore_hidden,
                                   bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        cb_ignore.pack(anchor="w", padx=8, pady=3)

        f_tol = tk.Frame(lf_meta, bg=COLOR_BG_CARD)
        f_tol.pack(fill=tk.X, padx=8, pady=(4, 8))
        ttk.Label(f_tol, text="Tolerância de data:").pack(side=tk.LEFT)
        sp_tol = ttk.Spinbox(f_tol, from_=0, to=60, textvariable=self.var_diff_time_tolerance, width=4)
        sp_tol.pack(side=tk.LEFT, padx=6)
        ttk.Label(f_tol, text="segundos (evita falso FAT32)").pack(side=tk.LEFT)

        # --- RESUMO ESTATÍSTICO ---
        lf_stats = ttk.LabelFrame(left_panel.content, text=" Resumo da Análise ")
        lf_stats.pack(side=tk.TOP, fill=tk.X, padx=15, pady=8)

        f_grid = tk.Frame(lf_stats, bg=COLOR_BG_CARD)
        f_grid.pack(fill=tk.X, padx=8, pady=6)
        f_grid.columnconfigure(0, weight=1)
        f_grid.columnconfigure(1, weight=1)

        ttk.Label(f_grid, text="Total Únicos:").grid(row=0, column=0, sticky="w", pady=2)
        self.lbl_diff_count_total = ttk.Label(f_grid, text="0", font=("Segoe UI", 9, "bold"))
        self.lbl_diff_count_total.grid(row=0, column=1, sticky="e", pady=2)

        ttk.Label(f_grid, text="⚠Diferentes:").grid(row=1, column=0, sticky="w", pady=2)
        self.lbl_diff_count_diff = tk.Label(f_grid, text="0", font=("Segoe UI", 9, "bold"), bg=COLOR_BG_CARD, fg=COLOR_DIFF_TAG)
        self.lbl_diff_count_diff.grid(row=1, column=1, sticky="e", pady=2)

        ttk.Label(f_grid, text="🔵 Apenas na Pasta A:").grid(row=2, column=0, sticky="w", pady=2)
        self.lbl_diff_count_only_a = tk.Label(f_grid, text="0", font=("Segoe UI", 9, "bold"), bg=COLOR_BG_CARD, fg=COLOR_ONLY_A_TAG)
        self.lbl_diff_count_only_a.grid(row=2, column=1, sticky="e", pady=2)

        ttk.Label(f_grid, text="🟣 Apenas na Pasta B:").grid(row=3, column=0, sticky="w", pady=2)
        self.lbl_diff_count_only_b = tk.Label(f_grid, text="0", font=("Segoe UI", 9, "bold"), bg=COLOR_BG_CARD, fg=COLOR_ONLY_B_TAG)
        self.lbl_diff_count_only_b.grid(row=3, column=1, sticky="e", pady=2)

        ttk.Label(f_grid, text="🟢 Idênticos:").grid(row=4, column=0, sticky="w", pady=2)
        self.lbl_diff_count_match = tk.Label(f_grid, text="0", font=("Segoe UI", 9, "bold"), bg=COLOR_BG_CARD, fg=COLOR_MATCH_TAG)
        self.lbl_diff_count_match.grid(row=4, column=1, sticky="e", pady=2)

        # --- SINCRONIZAÇÃO E CÓPIA DE FALTANTES ---
        lf_sync = ttk.LabelFrame(left_panel.content, text=" ⚡ Cópia de Faltantes & Sincronização ")
        lf_sync.pack(side=tk.TOP, fill=tk.X, padx=15, pady=8)

        ttk.Label(lf_sync, text="Transfira com 1 clique os arquivos faltantes preservando subpastas:", style="Sub.TLabel", wraplength=340).pack(anchor="w", padx=8, pady=(4, 6))

        self.btn_copy_a_to_b = HoverButton(
            lf_sync, text="Copiar Faltantes: A ➜ B (0)", bg=COLOR_BG_INPUT, fg=COLOR_ONLY_A_TAG,
            hover_bg=COLOR_BORDER, hover_fg="#ffffff", bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=lambda: self.copy_missing_files("a_to_b")
        )
        self.btn_copy_a_to_b.pack(fill=tk.X, padx=8, pady=3)

        self.btn_copy_b_to_a = HoverButton(
            lf_sync, text="Copiar Faltantes: B ➜ A (0)", bg=COLOR_BG_INPUT, fg=COLOR_ONLY_B_TAG,
            hover_bg=COLOR_BORDER, hover_fg="#ffffff", bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=lambda: self.copy_missing_files("b_to_a")
        )
        self.btn_copy_b_to_a.pack(fill=tk.X, padx=8, pady=3)

        self.btn_copy_selected = HoverButton(
            lf_sync, text="Copiar Item(ns) Selecionado(s)...", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY,
            hover_bg=COLOR_BORDER, hover_fg=COLOR_ACCENT, bd=1, relief="solid",
            font=("Segoe UI", 8), command=self.copy_selected_diff_items
        )
        self.btn_copy_selected.pack(fill=tk.X, padx=8, pady=(3, 8))

        # --- AÇÕES E PROGRESSO ---
        self.btn_diff_start = RoundedButton(
            left_panel.content, hover_bg=COLOR_ACCENT_HOVER, hover_fg="#ffffff",
            text="COMPARAR PASTAS AGORA", bg=COLOR_ACCENT, fg="#ffffff",
            font=("Segoe UI", 9, "bold"), height=38, command=self.start_diff_comparison
        )
        self.btn_diff_start.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(10, 4))

        self.btn_diff_cancel = RoundedButton(
            left_panel.content, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Cancelar Análise / Cópia", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED,
            font=("Segoe UI", 8), height=30, command=self.cancel_diff_comparison
        )
        self.btn_diff_cancel.pack(side=tk.TOP, fill=tk.X, padx=15, pady=2)

        self.btn_diff_save_md_left = RoundedButton(
            left_panel.content, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Salvar Relatório (.md)", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY,
            font=("Segoe UI", 9, "bold"), height=36, command=self.export_diff_markdown
        )
        self.btn_diff_save_md_left.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(8, 4))

        self.diff_progress = ttk.Progressbar(left_panel.content, mode="indeterminate", style="TProgressbar")
        self.diff_progress.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(8, 2))

        self.lbl_diff_status = ttk.Label(left_panel.content, text="Aguardando início...", style="Sub.TLabel")
        self.lbl_diff_status.pack(side=tk.TOP, anchor="w", padx=15, pady=(0, 15))

        # ==================== PAINEL DA DIREITA: RESULTADOS ====================
        toolbar = FlowFrame(right_panel, bg=COLOR_BG_CARD, padx=2, pady=2)
        toolbar.pack(fill=tk.X, padx=10, pady=8)
        self.diff_toolbar = toolbar

        # Botões de filtro rápido
        self.btn_filter_all = HoverButton(toolbar, text="Todos (0)", bg=COLOR_BORDER, fg="#ffffff", hover_bg=COLOR_ACCENT, hover_fg="#ffffff",
                                          bd=1, relief="solid", font=("Segoe UI", 8, "bold"), command=lambda: self.set_diff_filter("all"))
        toolbar.add_widget(self.btn_filter_all)

        self.btn_filter_diff = HoverButton(toolbar, text="Diferentes (0)", bg=COLOR_BG_INPUT, fg=COLOR_DIFF_TAG, hover_bg=COLOR_BORDER, hover_fg=COLOR_DIFF_TAG,
                                           bd=1, relief="solid", font=("Segoe UI", 8, "bold"), command=lambda: self.set_diff_filter("diff"))
        toolbar.add_widget(self.btn_filter_diff)

        self.btn_filter_only_a = HoverButton(toolbar, text="Apenas em A (0)", bg=COLOR_BG_INPUT, fg=COLOR_ONLY_A_TAG, hover_bg=COLOR_BORDER, hover_fg=COLOR_ONLY_A_TAG,
                                             bd=1, relief="solid", font=("Segoe UI", 8, "bold"), command=lambda: self.set_diff_filter("only_a"))
        toolbar.add_widget(self.btn_filter_only_a)

        self.btn_filter_only_b = HoverButton(toolbar, text="Apenas em B (0)", bg=COLOR_BG_INPUT, fg=COLOR_ONLY_B_TAG, hover_bg=COLOR_BORDER, hover_fg=COLOR_ONLY_B_TAG,
                                             bd=1, relief="solid", font=("Segoe UI", 8, "bold"), command=lambda: self.set_diff_filter("only_b"))
        toolbar.add_widget(self.btn_filter_only_b)

        self.btn_filter_match = HoverButton(toolbar, text="Idênticos (0)", bg=COLOR_BG_INPUT, fg=COLOR_MATCH_TAG, hover_bg=COLOR_BORDER, hover_fg=COLOR_MATCH_TAG,
                                            bd=1, relief="solid", font=("Segoe UI", 8, "bold"), command=lambda: self.set_diff_filter("match"))
        toolbar.add_widget(self.btn_filter_match)

        # Campo de busca em tempo real agrupado
        f_search = tk.Frame(toolbar, bg=COLOR_BG_CARD)
        lbl_search = ttk.Label(f_search, text="Buscar:", font=("Segoe UI", 8))
        lbl_search.pack(side=tk.LEFT, padx=(4, 4))
        entry_search = tk.Entry(f_search, textvariable=self.diff_search_query, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 8), width=14)
        entry_search.pack(side=tk.LEFT, padx=2)
        entry_search.bind("<KeyRelease>", lambda e: self.filter_diff_results())
        toolbar.add_widget(f_search)

        # Botões de transferência rápida
        self.btn_tb_copy_a_to_b = HoverButton(
            toolbar, hover_bg=COLOR_BORDER, hover_fg=COLOR_ONLY_A_TAG,
            text="Copiar A ➜ B", bg=COLOR_BG_INPUT, fg=COLOR_ONLY_A_TAG, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=lambda: self.copy_missing_files("a_to_b")
        )
        toolbar.add_widget(self.btn_tb_copy_a_to_b)

        self.btn_tb_copy_b_to_a = HoverButton(
            toolbar, hover_bg=COLOR_BORDER, hover_fg=COLOR_ONLY_B_TAG,
            text="Copiar B ➜ A", bg=COLOR_BG_INPUT, fg=COLOR_ONLY_B_TAG, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=lambda: self.copy_missing_files("b_to_a")
        )
        toolbar.add_widget(self.btn_tb_copy_b_to_a)

        btn_open_file = HoverButton(
            toolbar, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Abrir Arquivo", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8), command=self.open_diff_selected_file
        )
        toolbar.add_widget(btn_open_file)

        btn_save_md_right = HoverButton(
            toolbar, hover_bg=COLOR_ACCENT_HOVER, hover_fg="#ffffff",
            text="Relatório (.md)", bg=COLOR_ACCENT, fg="#ffffff", bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=self.export_diff_markdown
        )
        toolbar.add_widget(btn_save_md_right)

        # Container Treeview
        tree_container = tk.Frame(right_panel, bg=COLOR_BG_DARK)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        columns = ("status", "rel_path", "size_a", "size_b", "mtime_a", "mtime_b", "details")
        self.diff_tree = ttk.Treeview(tree_container, columns=columns, show="headings", selectmode="extended")

        self.diff_scroll_y = ttk.Scrollbar(tree_container, orient="vertical", command=self.diff_tree.yview, style="Vertical.TScrollbar")
        self.diff_scroll_x = ttk.Scrollbar(tree_container, orient="horizontal", command=self.diff_tree.xview, style="Horizontal.TScrollbar")
        self.diff_tree.configure(yscrollcommand=self.diff_scroll_y.set, xscrollcommand=self.diff_scroll_x.set)

        self.diff_tree.heading("status", text="Status")
        self.diff_tree.heading("rel_path", text="Caminho Relativo")
        self.diff_tree.heading("size_a", text="Tamanho A")
        self.diff_tree.heading("size_b", text="Tamanho B")
        self.diff_tree.heading("mtime_a", text="Modificação A")
        self.diff_tree.heading("mtime_b", text="Modificação B")
        self.diff_tree.heading("details", text="Detalhes da Comparação")

        self.diff_tree.column("status", width=110, anchor="center")
        self.diff_tree.column("rel_path", width=260, anchor="w")
        self.diff_tree.column("size_a", width=85, anchor="e")
        self.diff_tree.column("size_b", width=85, anchor="e")
        self.diff_tree.column("mtime_a", width=125, anchor="center")
        self.diff_tree.column("mtime_b", width=125, anchor="center")
        self.diff_tree.column("details", width=280, anchor="w")

        # Tags de cores
        self.diff_tree.tag_configure("diff", foreground=COLOR_DIFF_TAG)
        self.diff_tree.tag_configure("only_a", foreground=COLOR_ONLY_A_TAG)
        self.diff_tree.tag_configure("only_b", foreground=COLOR_ONLY_B_TAG)
        self.diff_tree.tag_configure("match", foreground=COLOR_MATCH_TAG)

        self.diff_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.diff_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.diff_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.diff_tree.bind("<Double-1>", lambda e: self.open_diff_selected_file())

        # Menu Contextual (Botão Direito)
        self.diff_context_menu = tk.Menu(self, tearoff=0, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, activebackground=COLOR_ACCENT, activeforeground="#000000", font=("Segoe UI", 9))
        self.diff_context_menu.add_command(label="Copiar Selecionado(s): A ➜ B", command=lambda: self.copy_selected_diff_items("a_to_b"))
        self.diff_context_menu.add_command(label="Copiar Selecionado(s): B ➜ A", command=lambda: self.copy_selected_diff_items("b_to_a"))
        self.diff_context_menu.add_separator()
        self.diff_context_menu.add_command(label="Abrir Arquivo na Pasta A", command=lambda: self.open_diff_specific_folder("a"))
        self.diff_context_menu.add_command(label="Abrir Arquivo na Pasta B", command=lambda: self.open_diff_specific_folder("b"))
        self.diff_context_menu.add_separator()
        self.diff_context_menu.add_command(label="Copiar Caminho Relativo", command=self.copy_diff_rel_path_to_clipboard)

        self.diff_tree.bind("<Button-3>", self.show_diff_context_menu)

        # Status inferior
        status_bar = tk.Frame(right_panel, bg=COLOR_BG_CARD, padx=8, pady=4)
        status_bar.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.lbl_diff_tree_status = ttk.Label(status_bar, text="Nenhuma comparação realizada. Selecione duas pastas para analisar.", style="Sub.TLabel")
        self.lbl_diff_tree_status.pack(side=tk.LEFT)

        # Atualização automática de badges de armazenamento
        self.var_diff_dir_a.trace_add("write", lambda *a: self.update_diff_storage_badges())
        self.var_diff_dir_b.trace_add("write", lambda *a: self.update_diff_storage_badges())
        self.update_diff_storage_badges()

    def browse_diff_dir_a(self):
        p = filedialog.askdirectory(title="Selecione a Pasta A (Referência)", parent=self)
        if p:
            self.var_diff_dir_a.set(os.path.normpath(p))

    def browse_diff_dir_b(self):
        p = filedialog.askdirectory(title="Selecione a Pasta B (Comparação)", parent=self)
        if p:
            self.var_diff_dir_b.set(os.path.normpath(p))

    def swap_diff_dirs(self):
        a = self.var_diff_dir_a.get()
        b = self.var_diff_dir_b.get()
        self.var_diff_dir_a.set(b)
        self.var_diff_dir_b.set(a)

    def log_diff(self, msg, tag="normal"):
        if hasattr(self, 'lbl_diff_status'):
            self.lbl_diff_status.config(text=msg)

    def start_diff_comparison(self):
        if self.diff_is_running:
            return

        dir_a = self.var_diff_dir_a.get().strip().strip('"')
        dir_b = self.var_diff_dir_b.get().strip().strip('"')

        if not dir_a or not os.path.isdir(dir_a):
            messagebox.showerror("Erro de Validação", "Selecione um diretório válido para a Pasta A.", parent=self)
            return
        if not dir_b or not os.path.isdir(dir_b):
            messagebox.showerror("Erro de Validação", "Selecione um diretório válido para a Pasta B.", parent=self)
            return

        try:
            float(self.var_diff_time_tolerance.get().strip())
        except Exception:
            self.var_diff_time_tolerance.set("2")

        self.diff_is_running = True
        self.diff_stop_event.clear()
        self.diff_progress.start(10)
        self.btn_diff_start.config(state="disabled")
        self.btn_diff_cancel.config(state="normal")
        self.lbl_diff_status.config(text="Iniciando varredura e comparação...")

        # Limpa árvore e resultados anteriores
        self.diff_tree.delete(*self.diff_tree.get_children())
        self.diff_results = []
        self.diff_filtered_results = []

        threading.Thread(target=self._diff_worker, args=(dir_a, dir_b), daemon=True).start()

    def cancel_diff_comparison(self):
        if self.diff_is_running:
            self.diff_stop_event.set()
            self.lbl_diff_status.config(text="Interrompendo análise...")
        if getattr(self, "diff_is_copying", False):
            self.diff_stop_copy_event.set()
            self.lbl_diff_status.config(text="Interrompendo cópia de arquivos...")

    def update_diff_storage_badges(self):
        """Atualiza dinamicamente as indicações visuais de tipo de armazenamento das pastas A e B"""
        dir_a = self.var_diff_dir_a.get().strip().strip('"')
        dir_b = self.var_diff_dir_b.get().strip().strip('"')

        badge_a, color_a, _, _, _ = get_path_storage_info(dir_a) if dir_a else ("", COLOR_TEXT_MUTED, False, False, "")
        badge_b, color_b, _, _, _ = get_path_storage_info(dir_b) if dir_b else ("", COLOR_TEXT_MUTED, False, False, "")

        if hasattr(self, 'lbl_diff_storage_a'):
            self.lbl_diff_storage_a.config(text=f"  {badge_a}" if badge_a else "", fg=color_a)
        if hasattr(self, 'lbl_diff_storage_b'):
            self.lbl_diff_storage_b.config(text=f"  {badge_b}" if badge_b else "", fg=color_b)

    def _diff_worker(self, dir_a, dir_b):
        start_time = time.time()
        try:
            cmp_size = self.var_diff_cmp_size.get()
            cmp_mtime = self.var_diff_cmp_mtime.get()
            cmp_ctime = self.var_diff_cmp_ctime.get()
            cmp_name = self.var_diff_cmp_name.get()
            cmp_integrity = self.var_diff_cmp_integrity.get()
            recursive = self.var_diff_recursive.get()
            ignore_hidden = self.var_diff_ignore_hidden.get()
            try:
                tolerance = float(self.var_diff_time_tolerance.get().strip())
            except Exception:
                tolerance = 2.0

            # Validação e tratamento de erros de rede/NAS ou pastas inacessíveis
            for d_name, d_path in [("Pasta A", dir_a), ("Pasta B", dir_b)]:
                try:
                    if not os.path.exists(d_path):
                        raise FileNotFoundError(f"{d_name} não foi encontrada ou o servidor está inacessível: {d_path}")
                except OSError as oe:
                    win_err = getattr(oe, 'winerror', None)
                    if win_err in (53, 64, 121, 1231):
                        raise OSError(f"Falha de comunicação com o NAS na {d_name} (WinError {win_err}): Servidor de rede inacessível ou conexão instável.")
                    raise

            # Função segura para leitura de metadados com resiliência a caminhos longos e locks de sincronização de nuvem
            def safe_read_metadata(full_path):
                lp_path = to_long_path(full_path)
                for attempt in range(3):
                    try:
                        st = os.stat(lp_path)
                        ctime = getattr(st, "st_birthtime", st.st_ctime)
                        cloud_status = check_cloud_file_attributes(lp_path)
                        return {
                            "size": st.st_size,
                            "mtime": st.st_mtime,
                            "ctime": ctime,
                            "path": full_path,
                            "cloud_status": cloud_status
                        }
                    except PermissionError as pe:
                        # WinError 32: arquivo temporariamente bloqueado por Dropbox ou OneDrive
                        if getattr(pe, 'winerror', None) == 32 and attempt < 2:
                            time.sleep(0.12)
                            continue
                        return {
                            "size": 0, "mtime": 0, "ctime": 0, "path": full_path,
                            "cloud_status": "Bloqueado por Sincronização em Nuvem"
                        }
                    except OSError as oe:
                        win_err = getattr(oe, 'winerror', None)
                        err_no = getattr(oe, 'errno', None)
                        if win_err == 206 or err_no == getattr(errno, 'ENAMETOOLONG', 36):
                            return {
                                "size": 0, "mtime": 0, "ctime": 0, "path": full_path,
                                "cloud_status": "Caminho longo excede MAX_PATH (WinError 206)"
                            }
                        return None
                    except Exception:
                        return None
                return None

            badge_a, _, _, is_nas_a, _ = get_path_storage_info(dir_a)
            self.after(0, lambda: self.lbl_diff_status.config(text=f"Varrendo Pasta A ({badge_a})..."))
            files_a = {}
            if recursive:
                for root, dirs, files in os.walk(dir_a):
                    if self.diff_stop_event.is_set():
                        break
                    for f in files:
                        if ignore_hidden and (f.startswith(".") or f.lower() in ("thumbs.db", "desktop.ini")):
                            continue
                        full_p = os.path.join(root, f)
                        try:
                            rel_p = safe_relpath(full_p, dir_a).replace("\\", "/")
                            meta = safe_read_metadata(full_p)
                            if meta:
                                meta["rel_path"] = rel_p
                                files_a[rel_p.lower()] = meta
                        except Exception:
                            pass
            else:
                try:
                    for entry in os.scandir(dir_a):
                        if self.diff_stop_event.is_set():
                            break
                        if entry.is_file():
                            if ignore_hidden and (entry.name.startswith(".") or entry.name.lower() in ("thumbs.db", "desktop.ini")):
                                continue
                            try:
                                meta = safe_read_metadata(entry.path)
                                if meta:
                                    meta["rel_path"] = entry.name
                                    files_a[entry.name.lower()] = meta
                            except Exception:
                                pass
                except Exception:
                    pass

            if self.diff_stop_event.is_set():
                self.after(0, lambda: self._on_diff_finished(interrupted=True))
                return

            badge_b, _, _, is_nas_b, _ = get_path_storage_info(dir_b)
            self.after(0, lambda: self.lbl_diff_status.config(text=f"Varrendo Pasta B ({badge_b})..."))
            files_b = {}
            if recursive:
                for root, dirs, files in os.walk(dir_b):
                    if self.diff_stop_event.is_set():
                        break
                    for f in files:
                        if ignore_hidden and (f.startswith(".") or f.lower() in ("thumbs.db", "desktop.ini")):
                            continue
                        full_p = os.path.join(root, f)
                        try:
                            rel_p = safe_relpath(full_p, dir_b).replace("\\", "/")
                            meta = safe_read_metadata(full_p)
                            if meta:
                                meta["rel_path"] = rel_p
                                files_b[rel_p.lower()] = meta
                        except Exception:
                            pass
            else:
                try:
                    for entry in os.scandir(dir_b):
                        if self.diff_stop_event.is_set():
                            break
                        if entry.is_file():
                            if ignore_hidden and (entry.name.startswith(".") or entry.name.lower() in ("thumbs.db", "desktop.ini")):
                                continue
                            try:
                                meta = safe_read_metadata(entry.path)
                                if meta:
                                    meta["rel_path"] = entry.name
                                    files_b[entry.name.lower()] = meta
                            except Exception:
                                pass
                except Exception:
                    pass

            if self.diff_stop_event.is_set():
                self.after(0, lambda: self._on_diff_finished(interrupted=True))
                return

            self.after(0, lambda: self.lbl_diff_status.config(text="Comparando metadados e analisando divergências..."))

            all_keys = sorted(set(files_a.keys()) | set(files_b.keys()))
            results = []

            for key in all_keys:
                if self.diff_stop_event.is_set():
                    break

                in_a = key in files_a
                in_b = key in files_b

                if in_a and not in_b:
                    info_a = files_a[key]
                    det = "Não existe na Pasta B"
                    if info_a.get("cloud_status"):
                        det += f" [☁ {info_a['cloud_status']}]"
                    results.append({
                        "status": "only_a",
                        "status_text": "Apenas em A",
                        "rel_path": info_a["rel_path"],
                        "size_a": info_a["size"],
                        "size_b": None,
                        "mtime_a": info_a["mtime"],
                        "mtime_b": None,
                        "details": det,
                        "path_a": info_a["path"],
                        "path_b": None
                    })
                elif in_b and not in_a:
                    info_b = files_b[key]
                    det = "Não existe na Pasta A"
                    if info_b.get("cloud_status"):
                        det += f" [☁ {info_b['cloud_status']}]"
                    results.append({
                        "status": "only_b",
                        "status_text": "Apenas em B",
                        "rel_path": info_b["rel_path"],
                        "size_a": None,
                        "size_b": info_b["size"],
                        "mtime_a": None,
                        "mtime_b": info_b["mtime"],
                        "details": det,
                        "path_a": None,
                        "path_b": info_b["path"]
                    })
                else:
                    info_a = files_a[key]
                    info_b = files_b[key]
                    rel_p = info_a["rel_path"]
                    diff_reasons = []

                    # Comparação de Nome (caso o usuário queira verificar diferença de caixa alta/baixa ou grafia)
                    if cmp_name and info_a["rel_path"] != info_b["rel_path"]:
                        name_a = os.path.basename(info_a["rel_path"])
                        name_b = os.path.basename(info_b["rel_path"])
                        diff_reasons.append(f"🔤 Nome/Caixa ({name_a} vs {name_b})")

                    dt_diff = info_a["mtime"] - info_b["mtime"]
                    size_diff = info_a["size"] - info_b["size"]

                    newer_folder = "A" if dt_diff > tolerance else ("B" if dt_diff < -tolerance else "equal")
                    if newer_folder == "A":
                        newer_str = f"A é mais recente (+{format_timedelta_human(dt_diff)})"
                    elif newer_folder == "B":
                        newer_str = f"B é mais recente (+{format_timedelta_human(-dt_diff)})"
                    else:
                        newer_str = "Mesma data"

                    if size_diff > 0:
                        size_str = f"A é maior (+{format_size(size_diff)})"
                    elif size_diff < 0:
                        size_str = f"B é maior (+{format_size(-size_diff)})"
                    else:
                        size_str = "Mesmo tamanho"

                    if cmp_mtime and newer_folder != "equal":
                        diff_reasons.append(f"🕒 {newer_str}")

                    if cmp_size and info_a["size"] != info_b["size"]:
                        diff_reasons.append(f"📦 {size_str}")

                    if cmp_ctime and abs(info_a["ctime"] - info_b["ctime"]) > tolerance:
                        ct_a = datetime.datetime.fromtimestamp(info_a["ctime"]).strftime("%d/%m/%Y %H:%M")
                        ct_b = datetime.datetime.fromtimestamp(info_b["ctime"]).strftime("%d/%m/%Y %H:%M")
                        diff_reasons.append(f"📅 Criação ({ct_a} vs {ct_b})")

                    # Verificação de Integridade do Conteúdo (Hash SHA-256)
                    if cmp_integrity:
                        if info_a["size"] != info_b["size"]:
                            if not cmp_size:
                                diff_reasons.append("⚠ Conteúdo divergente (tamanhos distintos)")
                        elif info_a["size"] == 0:
                            pass
                        else:
                            filename_disp = os.path.basename(rel_p)
                            self.after(0, lambda fn=filename_disp: self.lbl_diff_status.config(
                                text=f"Checando integridade (SHA-256): {fn}..."
                            ))
                            hash_a, err_a = safe_compute_file_hash(info_a["path"], stop_event=self.diff_stop_event)
                            if self.diff_stop_event.is_set():
                                break
                            if err_a:
                                diff_reasons.append(f"❌ Erro leitura Pasta A: {err_a}")
                            else:
                                hash_b, err_b = safe_compute_file_hash(info_b["path"], stop_event=self.diff_stop_event)
                                if self.diff_stop_event.is_set():
                                    break
                                if err_b:
                                    diff_reasons.append(f"❌ Erro leitura Pasta B: {err_b}")
                                elif hash_a != hash_b:
                                    diff_reasons.append("⚠ Integridade violada / Hash SHA-256 divergente")

                    if info_a.get("cloud_status"):
                        diff_reasons.append(f"[☁ A: {info_a['cloud_status']}]")
                    if info_b.get("cloud_status"):
                        diff_reasons.append(f"[☁ B: {info_b['cloud_status']}]")

                    if diff_reasons:
                        results.append({
                            "status": "diff",
                            "status_text": "Diferente",
                            "rel_path": rel_p,
                            "size_a": info_a["size"],
                            "size_b": info_b["size"],
                            "mtime_a": info_a["mtime"],
                            "mtime_b": info_b["mtime"],
                            "newer_folder": newer_folder,
                            "newer_desc": newer_str,
                            "size_desc": size_str,
                            "details": " | ".join(diff_reasons),
                            "path_a": info_a["path"],
                            "path_b": info_b["path"]
                        })
                    else:
                        match_detail = "Metadados e integridade (SHA-256) coincidem" if cmp_integrity else "Metadados selecionados coincidem"
                        results.append({
                            "status": "match",
                            "status_text": "Idêntico",
                            "rel_path": rel_p,
                            "size_a": info_a["size"],
                            "size_b": info_b["size"],
                            "mtime_a": info_a["mtime"],
                            "mtime_b": info_b["mtime"],
                            "details": match_detail,
                            "path_a": info_a["path"],
                            "path_b": info_b["path"]
                        })

            self.diff_results = results
            elapsed = time.time() - start_time
            self.after(0, lambda: self._on_diff_finished(interrupted=False, elapsed=elapsed))

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erro na Comparação", f"Falha durante a varredura:\n{str(e)}", parent=self))
            self.after(0, lambda: self._on_diff_finished(interrupted=True))

    def _on_diff_finished(self, interrupted=False, elapsed=0.0):
        self.diff_is_running = False
        self.diff_progress.stop()
        self.btn_diff_start.config(state="normal")
        self.btn_diff_cancel.config(state="disabled")

        if interrupted:
            self.lbl_diff_status.config(text="Comparação interrompida pelo usuário.")
            return

        # Atualiza contadores estatísticos
        total = len(self.diff_results)
        cnt_diff = sum(1 for r in self.diff_results if r["status"] == "diff")
        cnt_only_a = sum(1 for r in self.diff_results if r["status"] == "only_a")
        cnt_only_b = sum(1 for r in self.diff_results if r["status"] == "only_b")
        cnt_match = sum(1 for r in self.diff_results if r["status"] == "match")

        self.lbl_diff_count_total.config(text=str(total))
        self.lbl_diff_count_diff.config(text=str(cnt_diff))
        self.lbl_diff_count_only_a.config(text=str(cnt_only_a))
        self.lbl_diff_count_only_b.config(text=str(cnt_only_b))
        self.lbl_diff_count_match.config(text=str(cnt_match))

        # Atualiza textos dos botões de filtro
        self.btn_filter_all.config(text=f"Todos ({total})")
        self.btn_filter_diff.config(text=f"Diferentes ({cnt_diff})")
        self.btn_filter_only_a.config(text=f"Apenas em A ({cnt_only_a})")
        self.btn_filter_only_b.config(text=f"Apenas em B ({cnt_only_b})")
        self.btn_filter_match.config(text=f"Idênticos ({cnt_match})")

        # Atualiza botões de cópia de faltantes
        if hasattr(self, 'btn_copy_a_to_b'):
            self.btn_copy_a_to_b.config(text=f"Copiar Faltantes: A ➜ B ({cnt_only_a})")
        if hasattr(self, 'btn_copy_b_to_a'):
            self.btn_copy_b_to_a.config(text=f"Copiar Faltantes: B ➜ A ({cnt_only_b})")
        if hasattr(self, 'btn_tb_copy_a_to_b'):
            self.btn_tb_copy_a_to_b.config(text=f"Copiar A ➜ B ({cnt_only_a})")
        if hasattr(self, 'btn_tb_copy_b_to_a'):
            self.btn_tb_copy_b_to_a.config(text=f"Copiar B ➜ A ({cnt_only_b})")

        if hasattr(self, 'diff_toolbar') and hasattr(self.diff_toolbar, 'reflow'):
            self.after_idle(self.diff_toolbar.reflow)

        self.lbl_diff_status.config(text=f"Concluído em {elapsed:.1f}s ({total} arquivos comparados).")
        self.filter_diff_results()

    def set_diff_filter(self, filter_key):
        self.diff_active_filter = filter_key
        # Atualiza estilos dos botões de filtro
        btns = [
            ("all", self.btn_filter_all),
            ("diff", self.btn_filter_diff),
            ("only_a", self.btn_filter_only_a),
            ("only_b", self.btn_filter_only_b),
            ("match", self.btn_filter_match)
        ]
        for key, btn in btns:
            if key == filter_key:
                btn.config(bg=COLOR_BORDER, fg="#ffffff")
            else:
                btn.config(bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY)
        self.filter_diff_results()

    def filter_diff_results(self):
        query = self.diff_search_query.get().strip().lower()
        active = self.diff_active_filter

        self.diff_tree.delete(*self.diff_tree.get_children())
        filtered = []

        for item in self.diff_results:
            if active != "all" and item["status"] != active:
                continue
            if query and (query not in item["rel_path"].lower() and query not in item["details"].lower()):
                continue
            filtered.append(item)

        for item in filtered:
            sa = format_size(item["size_a"]) if item["size_a"] is not None else "-"
            sb = format_size(item["size_b"]) if item["size_b"] is not None else "-"
            ma = datetime.datetime.fromtimestamp(item["mtime_a"]).strftime("%d/%m/%Y %H:%M") if item["mtime_a"] is not None else "-"
            mb = datetime.datetime.fromtimestamp(item["mtime_b"]).strftime("%d/%m/%Y %H:%M") if item["mtime_b"] is not None else "-"

            self.diff_tree.insert(
                "", tk.END,
                values=(item["status_text"], item["rel_path"], sa, sb, ma, mb, item["details"]),
                tags=(item["status"],)
            )

        self.lbl_diff_tree_status.config(text=f"Exibindo {len(filtered)} de {len(self.diff_results)} itens.")

    def show_diff_context_menu(self, event):
        """Abre o menu contextual na linha onde o usuário clicou com o botão direito"""
        item_id = self.diff_tree.identify_row(event.y)
        if item_id:
            if item_id not in self.diff_tree.selection():
                self.diff_tree.selection_set(item_id)
            self.diff_context_menu.tk_popup(event.x_root, event.y_root)

    def copy_diff_rel_path_to_clipboard(self):
        selected = self.diff_tree.selection()
        if not selected:
            return
        values = self.diff_tree.item(selected[0], "values")
        if values and len(values) > 1:
            rel_p = values[1]
            self.clipboard_clear()
            self.clipboard_append(rel_p)
            self.log_diff(f"Caminho copiado: {rel_p}")

    def open_diff_specific_folder(self, which="a"):
        selected = self.diff_tree.selection()
        if not selected:
            messagebox.showinfo("Aviso", "Selecione um arquivo na tabela.", parent=self)
            return
        values = self.diff_tree.item(selected[0], "values")
        if not values or len(values) < 2:
            return
        rel_p = values[1]
        base_dir = self.var_diff_dir_a.get().strip().strip('"') if which == "a" else self.var_diff_dir_b.get().strip().strip('"')
        target_path = os.path.join(base_dir, rel_p.replace("/", os.sep))
        if not os.path.exists(target_path):
            messagebox.showwarning("Aviso", f"O arquivo não existe na Pasta {which.upper()}:\n{target_path}", parent=self)
            return
        try:
            if sys.platform == "win32":
                subprocess.run(f'explorer /select,"{os.path.normpath(target_path)}"', shell=True)
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", target_path])
            else:
                subprocess.run(["xdg-open", os.path.dirname(target_path)])
        except Exception as e:
            messagebox.showerror("Erro ao Abrir", f"Falha ao abrir no gerenciador de arquivos: {str(e)}", parent=self)

    def copy_missing_files(self, direction="a_to_b"):
        """Copia todos os arquivos exclusivos de uma pasta para a outra (A ➜ B ou B ➜ A)"""
        if self.diff_is_running or getattr(self, "diff_is_copying", False):
            messagebox.showwarning("Aviso", "Uma operação de análise ou cópia já está em andamento. Aguarde.", parent=self)
            return

        dir_a = self.var_diff_dir_a.get().strip().strip('"')
        dir_b = self.var_diff_dir_b.get().strip().strip('"')
        if not dir_a or not os.path.isdir(dir_a) or not dir_b or not os.path.isdir(dir_b):
            messagebox.showerror("Erro de Diretórios", "Diretórios A e B inválidos. Selecione pastas existentes e realize uma comparação.", parent=self)
            return

        target_status = "only_a" if direction == "a_to_b" else "only_b"
        items_to_copy = [r for r in self.diff_results if r["status"] == target_status]

        src_dir = dir_a if direction == "a_to_b" else dir_b
        dst_dir = dir_b if direction == "a_to_b" else dir_a
        src_label = "Pasta A" if direction == "a_to_b" else "Pasta B"
        dst_label = "Pasta B" if direction == "a_to_b" else "Pasta A"

        if not items_to_copy:
            messagebox.showinfo("Nenhum Arquivo Faltante", f"Não há arquivos faltantes na {dst_label} para copiar a partir da {src_label}.", parent=self)
            return

        total_files = len(items_to_copy)
        total_bytes = sum((r["size_a"] or 0) if direction == "a_to_b" else (r["size_b"] or 0) for r in items_to_copy)
        formatted_total_size = format_size(total_bytes)

        # Informações de armazenamento e alertas de Cloud / NAS
        badge_dst, _, dst_is_cloud, dst_is_nas, _ = get_path_storage_info(dst_dir)
        extra_note = ""
        if dst_is_cloud:
            extra_note = f"\n\n☁ Armazenamento em Nuvem Detectado ({badge_dst}):\nOs arquivos copiados serão adicionados à fila de sincronização do provedor."
        elif dst_is_nas:
            extra_note = f"\n\n🌐 NAS / Armazenamento de Rede Detectado ({badge_dst}):\nA velocidade da transferência dependerá da estabilidade e taxa da rede."

        # Previsão antecipada de caminhos longos (>260 chars) e limites de nome (>255 chars)
        _, _, _, path_warning = predict_path_and_name_issues(items_to_copy, dst_dir)

        confirm = messagebox.askyesno(
            "Confirmar Cópia de Arquivos Faltantes",
            f"Deseja copiar todos os arquivos faltantes?\n\n"
            f"• Direção: {src_label} ➜ {dst_label}\n"
            f"• Origem: {src_dir}\n"
            f"• Destino: {dst_dir}\n"
            f"• Quantidade: {total_files} arquivo(s)\n"
            f"• Tamanho Total: ~{formatted_total_size}"
            f"{extra_note}"
            f"{path_warning}\n\n"
            f"A estrutura de diretórios e subpastas será preservada.",
            parent=self
        )
        if not confirm:
            return

        self.diff_is_copying = True
        self.diff_stop_copy_event.clear()
        self.diff_progress.start(10)
        self.btn_diff_start.config(state="disabled")
        self.btn_diff_cancel.config(state="normal")
        if hasattr(self, 'btn_copy_a_to_b'):
            self.btn_copy_a_to_b.config(state="disabled")
        if hasattr(self, 'btn_copy_b_to_a'):
            self.btn_copy_b_to_a.config(state="disabled")

        threading.Thread(target=self._copy_worker, args=(items_to_copy, src_dir, dst_dir, direction), daemon=True).start()

    def copy_selected_diff_items(self, target_direction=None):
        """Copia os itens selecionados na tabela (faltantes ou modificados com sobrescrita)"""
        if self.diff_is_running or getattr(self, "diff_is_copying", False):
            messagebox.showwarning("Aviso", "Uma operação já está em andamento. Aguarde.", parent=self)
            return

        selected = self.diff_tree.selection()
        if not selected:
            messagebox.showinfo("Aviso", "Selecione um ou mais arquivos na tabela para copiar.", parent=self)
            return

        dir_a = self.var_diff_dir_a.get().strip().strip('"')
        dir_b = self.var_diff_dir_b.get().strip().strip('"')
        if not dir_a or not os.path.isdir(dir_a) or not dir_b or not os.path.isdir(dir_b):
            messagebox.showerror("Erro", "Diretórios A e B inválidos.", parent=self)
            return

        direction = target_direction
        if not direction:
            resp = messagebox.askquestion(
                "Direção da Cópia",
                f"Você selecionou {len(selected)} arquivo(s).\n\n"
                f"Para qual direção deseja transferir?\n\n"
                f"[Sim] = Copiar de Pasta A para Pasta B (A ➜ B)\n"
                f"[Não] = Copiar de Pasta B para Pasta A (B ➜ A)",
                parent=self
            )
            direction = "a_to_b" if resp == "yes" else "b_to_a"

        src_dir = dir_a if direction == "a_to_b" else dir_b
        dst_dir = dir_b if direction == "a_to_b" else dir_a
        src_label = "Pasta A" if direction == "a_to_b" else "Pasta B"
        dst_label = "Pasta B" if direction == "a_to_b" else "Pasta A"

        items_to_copy = []
        for sel_id in selected:
            values = self.diff_tree.item(sel_id, "values")
            if not values or len(values) < 2:
                continue
            rel_p = values[1]
            item = next((r for r in self.diff_results if r["rel_path"] == rel_p), None)
            if item:
                src_file = os.path.join(src_dir, rel_p.replace("/", os.sep))
                if os.path.exists(src_file):
                    items_to_copy.append(item)

        if not items_to_copy:
            messagebox.showwarning("Aviso", f"Nenhum dos arquivos selecionados existe fisicamente na origem ({src_label}).", parent=self)
            return

        total_files = len(items_to_copy)
        total_bytes = sum((r["size_a"] or 0) if direction == "a_to_b" else (r["size_b"] or 0) for r in items_to_copy)
        formatted_total_size = format_size(total_bytes)

        badge_dst, _, dst_is_cloud, dst_is_nas, _ = get_path_storage_info(dst_dir)
        extra_note = ""
        if dst_is_cloud:
            extra_note = f"\n\n☁ Armazenamento em Nuvem Detectado ({badge_dst}):\nOs arquivos copiados serão adicionados à fila de sincronização do provedor."
        elif dst_is_nas:
            extra_note = f"\n\n🌐 NAS / Armazenamento de Rede Detectado ({badge_dst}):\nA velocidade da transferência dependerá da estabilidade e taxa da rede."

        # Previsão antecipada de caminhos longos (>260 chars) e limites de nome (>255 chars)
        _, _, _, path_warning = predict_path_and_name_issues(items_to_copy, dst_dir)

        confirm = messagebox.askyesno(
            "Confirmar Cópia Selecionada",
            f"Deseja copiar {total_files} arquivo(s) de {src_label} para {dst_label}?\n\n"
            f"• Origem: {src_dir}\n"
            f"• Destino: {dst_dir}\n"
            f"• Quantidade: {total_files} arquivo(s)\n"
            f"• Volume Total: ~{formatted_total_size}"
            f"{extra_note}"
            f"{path_warning}\n\n"
            f"(Arquivos existentes no destino serão sobrescritos com segurança)",
            parent=self
        )
        if not confirm:
            return

        self.diff_is_copying = True
        self.diff_stop_copy_event.clear()
        self.diff_progress.start(10)
        self.btn_diff_start.config(state="disabled")
        self.btn_diff_cancel.config(state="normal")
        if hasattr(self, 'btn_copy_a_to_b'):
            self.btn_copy_a_to_b.config(state="disabled")
        if hasattr(self, 'btn_copy_b_to_a'):
            self.btn_copy_b_to_a.config(state="disabled")

        threading.Thread(target=self._copy_worker, args=(items_to_copy, src_dir, dst_dir, direction), daemon=True).start()

    def _copy_worker(self, items_to_copy, src_dir, dst_dir, direction):
        total = len(items_to_copy)
        success_count = 0
        errors = []

        for i, item in enumerate(items_to_copy, 1):
            if self.diff_stop_copy_event.is_set():
                break

            rel_p = item["rel_path"]
            src_file = os.path.join(src_dir, rel_p.replace("/", os.sep))
            dst_file = os.path.join(dst_dir, rel_p.replace("/", os.sep))

            self.after(0, lambda idx=i, p=rel_p: self.lbl_diff_status.config(
                text=f"Copiando ({idx}/{total}): {os.path.basename(p)}"
            ))

            try:
                ok, err = safe_copy_file_resilient(src_file, dst_file)
                if ok:
                    success_count += 1
                else:
                    errors.append((rel_p, err))
            except Exception as e:
                errors.append((rel_p, str(e)))

        self.after(0, lambda: self._on_copy_finished(success_count, total, errors, direction))

    def _on_copy_finished(self, success_count, total, errors, direction):
        self.diff_is_copying = False
        self.diff_progress.stop()
        self.btn_diff_start.config(state="normal")
        self.btn_diff_cancel.config(state="disabled")
        if hasattr(self, 'btn_copy_a_to_b'):
            self.btn_copy_a_to_b.config(state="normal")
        if hasattr(self, 'btn_copy_b_to_a'):
            self.btn_copy_b_to_a.config(state="normal")

        if errors:
            err_sample = "\n".join([f"• {p}: {msg}" for p, msg in errors[:6]])
            if len(errors) > 6:
                err_sample += f"\n... e mais {len(errors) - 6} arquivo(s) com erro."
            messagebox.showwarning(
                "Cópia Concluída com Alertas",
                f"Transferência concluída com algumas pendências:\n\n"
                f"✅ Sucesso: {success_count} de {total} arquivo(s).\n"
                f"⚠ Ocorrências: {len(errors)} falha(s).\n\n"
                f"Possíveis causas (Locks de sincronização em nuvem, limites de caminho/nome ou latência de NAS):\n{err_sample}",
                parent=self
            )
        else:
            messagebox.showinfo(
                "Cópia Concluída com Sucesso",
                f"Todos os {success_count} arquivo(s) foram copiados com sucesso!",
                parent=self
            )

        # Atualiza a análise automaticamente após a transferência
        self.start_diff_comparison()

    def open_diff_selected_file(self):
        selected = self.diff_tree.selection()
        if not selected:
            messagebox.showinfo("Aviso", "Selecione um arquivo na tabela para abrir.", parent=self)
            return

        values = self.diff_tree.item(selected[0], "values")
        if not values or len(values) < 2:
            return

        rel_p = values[1]
        target_item = next((r for r in self.diff_results if r["rel_path"] == rel_p), None)
        if not target_item:
            return

        target_path = target_item.get("path_a") or target_item.get("path_b")
        if not target_path or not os.path.exists(target_path):
            messagebox.showwarning("Aviso", "O arquivo não foi encontrado no disco.", parent=self)
            return

        try:
            if sys.platform == "win32":
                subprocess.run(f'explorer /select,"{os.path.normpath(target_path)}"', shell=True)
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", target_path])
            else:
                subprocess.run(["xdg-open", os.path.dirname(target_path)])
        except Exception as e:
            messagebox.showerror("Erro ao Abrir", f"Falha ao abrir o arquivo: {str(e)}", parent=self)

    def export_diff_markdown(self):
        if not self.diff_results:
            messagebox.showwarning("Aviso", "Nenhuma análise foi executada ainda. Realize uma comparação antes de exportar o relatório.", parent=self)
            return

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        initial_file = f"Relatorio_Comparacao_{ts}.md"
        out_path = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar Relatório de Comparação (.md)",
            defaultextension=".md",
            filetypes=[("Documento Markdown", "*.md"), ("Todos os Arquivos", "*.*")],
            initialfile=initial_file
        )

        if not out_path:
            return

        try:
            dir_a = self.var_diff_dir_a.get().strip()
            dir_b = self.var_diff_dir_b.get().strip()
            badge_a, _, _, _, _ = get_path_storage_info(dir_a)
            badge_b, _, _, _, _ = get_path_storage_info(dir_b)

            cmp_size = self.var_diff_cmp_size.get()
            cmp_mtime = self.var_diff_cmp_mtime.get()
            cmp_ctime = self.var_diff_cmp_ctime.get()
            cmp_name = self.var_diff_cmp_name.get()
            cmp_integrity = self.var_diff_cmp_integrity.get()
            recursive = self.var_diff_recursive.get()
            tolerance = self.var_diff_time_tolerance.get()

            cnt_total = len(self.diff_results)
            diffs = [r for r in self.diff_results if r["status"] == "diff"]
            only_a = [r for r in self.diff_results if r["status"] == "only_a"]
            only_b = [r for r in self.diff_results if r["status"] == "only_b"]
            matches = [r for r in self.diff_results if r["status"] == "match"]

            md_lines = []
            md_lines.append("# 📊 Relatório de Comparação de Pastas — MPFolders")
            md_lines.append("")
            md_lines.append(f"- **Data da Análise:** {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}")
            md_lines.append(f"- **Pasta A (Referência):** `{dir_a}`  *{badge_a}*")
            md_lines.append(f"- **Pasta B (Comparação):** `{dir_b}`  *{badge_b}*")
            md_lines.append("")
            md_lines.append("### ⚙ Critérios de Comparação")
            md_lines.append(f"- **Nome do Arquivo (Maiúsculas/Minúsculas):** {'Sim' if cmp_name else 'Não'}")
            md_lines.append(f"- **Verificação de Integridade (Hash SHA-256):** {'Sim' if cmp_integrity else 'Não'}")
            md_lines.append(f"- **Tamanho:** {'Sim' if cmp_size else 'Não'}")
            md_lines.append(f"- **Data de Modificação:** {'Sim' if cmp_mtime else 'Não'}")
            md_lines.append(f"- **Data de Criação:** {'Sim' if cmp_ctime else 'Não'}")
            md_lines.append(f"- **Recursivo (Subpastas):** {'Sim' if recursive else 'Não'}")
            md_lines.append(f"- **Tolerância de Timestamp:** {tolerance} segundo(s)")
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")
            md_lines.append("## 📈 Resumo Estatístico")
            md_lines.append("")
            md_lines.append("| Categoria | Quantidade |")
            md_lines.append("| :--- | :---: |")
            md_lines.append(f"| **Total de Arquivos Únicos** | **{cnt_total}** |")
            md_lines.append(f"| ⚠ **Arquivos com Metadados Diferentes** | **{len(diffs)}** |")
            md_lines.append(f"| 🔵 **Arquivos Exclusivos da Pasta A** | **{len(only_a)}** |")
            md_lines.append(f"| 🟣 **Arquivos Exclusivos da Pasta B** | **{len(only_b)}** |")
            md_lines.append(f"| 🟢 **Arquivos Idênticos** | **{len(matches)}** |")
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")

            # 1. Arquivos com diferenças
            md_lines.append(f"## ⚠ 1. Arquivos com Diferenças ({len(diffs)})")
            md_lines.append("")
            if diffs:
                md_lines.append("| Caminho Relativo | Tamanho A | Tamanho B | Modificação A | Modificação B | Mais Recente | Detalhes & Nuvem |")
                md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
                for item in diffs:
                    sa = format_size(item["size_a"]) if item["size_a"] is not None else "-"
                    sb = format_size(item["size_b"]) if item["size_b"] is not None else "-"
                    ma = datetime.datetime.fromtimestamp(item["mtime_a"]).strftime("%d/%m/%Y %H:%M:%S") if item["mtime_a"] is not None else "-"
                    mb = datetime.datetime.fromtimestamp(item["mtime_b"]).strftime("%d/%m/%Y %H:%M:%S") if item["mtime_b"] is not None else "-"
                    newer = item.get("newer_desc", "-")
                    clean_rel = item["rel_path"].replace("|", "/")
                    clean_det = item["details"].replace("|", "-")
                    md_lines.append(f"| `{clean_rel}` | {sa} | {sb} | {ma} | {mb} | **{newer}** | {clean_det} |")
            else:
                md_lines.append("_Nenhum arquivo diferente encontrado._")
            md_lines.append("")

            # 2. Exclusivos da Pasta A
            md_lines.append(f"## 🔵 2. Arquivos Exclusivos da Pasta A ({len(only_a)})")
            md_lines.append("")
            if only_a:
                md_lines.append("| Caminho Relativo | Tamanho | Última Modificação | Notas |")
                md_lines.append("| :--- | :--- | :--- | :--- |")
                for item in only_a:
                    sa = format_size(item["size_a"]) if item["size_a"] is not None else "-"
                    ma = datetime.datetime.fromtimestamp(item["mtime_a"]).strftime("%d/%m/%Y %H:%M:%S") if item["mtime_a"] is not None else "-"
                    clean_rel = item["rel_path"].replace("|", "/")
                    clean_det = item["details"].replace("|", "-")
                    md_lines.append(f"| `{clean_rel}` | {sa} | {ma} | {clean_det} |")
            else:
                md_lines.append("_Nenhum arquivo exclusivo na Pasta A._")
            md_lines.append("")

            # 3. Exclusivos da Pasta B
            md_lines.append(f"## 🟣 3. Arquivos Exclusivos da Pasta B ({len(only_b)})")
            md_lines.append("")
            if only_b:
                md_lines.append("| Caminho Relativo | Tamanho | Última Modificação | Notas |")
                md_lines.append("| :--- | :--- | :--- | :--- |")
                for item in only_b:
                    sb = format_size(item["size_b"]) if item["size_b"] is not None else "-"
                    mb = datetime.datetime.fromtimestamp(item["mtime_b"]).strftime("%d/%m/%Y %H:%M:%S") if item["mtime_b"] is not None else "-"
                    clean_rel = item["rel_path"].replace("|", "/")
                    clean_det = item["details"].replace("|", "-")
                    md_lines.append(f"| `{clean_rel}` | {sb} | {mb} | {clean_det} |")
            else:
                md_lines.append("_Nenhum arquivo exclusivo na Pasta B._")
            md_lines.append("")

            # 4. Arquivos Idênticos
            md_lines.append(f"## 🟢 4. Arquivos Idênticos ({len(matches)})")
            md_lines.append("")
            if matches:
                md_lines.append("| Caminho Relativo | Tamanho | Última Modificação |")
                md_lines.append("| :--- | :--- | :--- |")
                for item in matches:
                    sa = format_size(item["size_a"]) if item["size_a"] is not None else "-"
                    ma = datetime.datetime.fromtimestamp(item["mtime_a"]).strftime("%d/%m/%Y %H:%M:%S") if item["mtime_a"] is not None else "-"
                    clean_rel = item["rel_path"].replace("|", "/")
                    md_lines.append(f"| `{clean_rel}` | {sa} | {ma} |")
            else:
                md_lines.append("_Nenhum arquivo idêntico encontrado._")
            md_lines.append("")

            md_lines.append("---")
            md_lines.append("*Relatório gerado automaticamente pelo MPFolders — Ferramenta Portátil de Gestão de Pastas.*")

            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(md_lines))

            res = messagebox.askyesno(
                "Relatório Salvo",
                f"Relatório exportado com sucesso!\n\nArquivo: {os.path.basename(out_path)}\n\nDeseja abrir o arquivo agora?",
                parent=self
            )
            if res:
                if sys.platform == "win32":
                    os.startfile(out_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", out_path])
                else:
                    subprocess.run(["xdg-open", out_path])

        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Falha ao gerar relatório Markdown: {str(e)}", parent=self)

    # =========================================================================
    # TAB 7: MAPEADOR DE UNIDADES DE REDE NO WINDOWS (NETWORK DRIVE MAPPER)
    # =========================================================================
    def init_tab_netdrive(self):
        self.paned_netdrive = tk.PanedWindow(self.tab_netdrive, orient=tk.HORIZONTAL, bg=COLOR_BORDER, bd=0, sashwidth=6, sashrelief="flat", showhandle=True, handlesize=8, handlepad=8)
        self.paned_netdrive.pack(fill=tk.BOTH, expand=True)

        left_panel = ScrollablePanel(self.paned_netdrive, bg=COLOR_BG_DARK, width=400)
        right_panel = ttk.LabelFrame(self.paned_netdrive, text=" Unidades Mapeadas & Gerenciamento ")

        self.paned_netdrive.add(left_panel, minsize=370)
        self.paned_netdrive.add(right_panel, minsize=420)

        # --- CONFIGURAÇÃO DO NOVO MAPEAMENTO ---
        lf_map = ttk.LabelFrame(left_panel.content, text=" Novo Mapeamento de Unidade ")
        lf_map.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(15, 8))

        # Letra da Unidade
        ttk.Label(lf_map, text="Letra da Unidade:").pack(anchor="w", padx=8, pady=(6, 2))
        self.combo_netdrive_letter = ttk.Combobox(lf_map, textvariable=self.var_netdrive_letter, state="readonly", font=("Segoe UI", 9, "bold"))
        self.combo_netdrive_letter.pack(fill=tk.X, padx=8, pady=2)

        # Caminho da Pasta (Local ou UNC)
        ttk.Label(lf_map, text="Caminho da Pasta (Local ou Rede UNC):").pack(anchor="w", padx=8, pady=(8, 2))
        entry_net_path = tk.Entry(lf_map, textvariable=self.var_netdrive_path, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9))
        entry_net_path.pack(fill=tk.X, padx=8, pady=2)

        btn_browse_path = HoverButton(
            lf_map, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Procurar Pasta Local...", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), command=self.browse_netdrive_path
        )
        btn_browse_path.pack(anchor="e", padx=8, pady=(2, 6))

        # Tipo de Mapeamento
        ttk.Label(lf_map, text="Tipo de Mapeamento (para pastas locais):").pack(anchor="w", padx=8, pady=(4, 2))
        f_type = tk.Frame(lf_map, bg=COLOR_BG_CARD)
        f_type.pack(fill=tk.X, padx=8, pady=2)
        rb_unc = tk.Radiobutton(f_type, text=r"Rede UNC (\\localhost\C$...)", variable=self.var_netdrive_type, value="unc",
                                bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        rb_unc.pack(anchor="w", pady=1)
        rb_subst = tk.Radiobutton(f_type, text="Unidade Virtual Local (subst)", variable=self.var_netdrive_type, value="subst",
                                  bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD)
        rb_subst.pack(anchor="w", pady=1)

        # Opção de Persistência no Logon
        cb_persist = tk.Checkbutton(
            lf_map, text="Remapear no logon do Windows (Persistente)", variable=self.var_netdrive_persistent,
            bg=COLOR_BG_CARD, fg=COLOR_ACCENT, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD,
            font=("Segoe UI", 9, "bold")
        )
        cb_persist.pack(anchor="w", padx=8, pady=(6, 4))

        # Opção de Credenciais
        cb_creds = tk.Checkbutton(
            lf_map, text="Usar credenciais de rede específicas", variable=self.var_netdrive_use_creds,
            bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_BG_INPUT, activebackground=COLOR_BG_CARD,
            command=self._on_toggle_netdrive_creds
        )
        cb_creds.pack(anchor="w", padx=8, pady=(2, 4))

        self.f_creds = tk.Frame(lf_map, bg=COLOR_BG_CARD)
        self.f_creds.pack(fill=tk.X, padx=8, pady=(0, 6))

        ttk.Label(self.f_creds, text="Usuário:").grid(row=0, column=0, sticky="w", pady=2)
        entry_user = tk.Entry(self.f_creds, textvariable=self.var_netdrive_user, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9), width=24)
        entry_user.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=2)

        ttk.Label(self.f_creds, text="Senha:").grid(row=1, column=0, sticky="w", pady=2)
        entry_pwd = tk.Entry(self.f_creds, textvariable=self.var_netdrive_password, show="*", bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid", insertbackground=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9), width=24)
        entry_pwd.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=2)
        self.f_creds.pack_forget()

        # Dica / Informações
        note_frame = tk.Frame(left_panel.content, bg=COLOR_BG_CARD, bd=1, relief="solid")
        note_frame.pack(side=tk.TOP, fill=tk.X, padx=15, pady=8)
        lbl_nt = ttk.Label(note_frame, text="COMO FUNCIONA NO WINDOWS", font=("Segoe UI", 9, "bold"), foreground=COLOR_WARNING)
        lbl_nt.pack(anchor="w", padx=8, pady=(6, 2))

        lbl_desc = tk.Text(note_frame, wrap=tk.WORD, bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, bd=0, font=("Segoe UI", 8), height=6)
        lbl_desc.pack(fill=tk.X, padx=8, pady=(0, 6))
        lbl_desc.insert(tk.END, "• Modo Rede UNC: Utiliza o comando 'net use' com /persistent:yes para que o Windows reconecte a unidade automaticamente a cada logon.\n\n"
                                "• Modo Virtual (subst): Cria uma unidade de disco rápida mapeada diretamente para uma pasta local, registrando no início de sessão do usuário se persistente.")
        lbl_desc.config(state=tk.DISABLED)

        # Botões de Ação
        f_actions = tk.Frame(left_panel.content, bg=COLOR_BG_CARD)
        f_actions.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(10, 15))

        btn_map_now = HoverButton(
            f_actions, hover_bg=COLOR_ACCENT_HOVER, hover_fg="#ffffff",
            text="Mapear Unidade", bg=COLOR_ACCENT, fg="#ffffff", bd=1, relief="solid",
            font=("Segoe UI", 9, "bold"), padx=10, pady=4, command=self.execute_map_drive
        )
        btn_map_now.pack(side=tk.LEFT, padx=(0, 6))

        btn_clear = HoverButton(
            f_actions, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Limpar Campos", bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8), padx=8, pady=4, command=self.clear_netdrive_fields
        )
        btn_clear.pack(side=tk.LEFT)

        # ==================== PAINEL DA DIREITA: GERENCIAMENTO ====================
        toolbar = FlowFrame(right_panel, bg=COLOR_BG_CARD, padx=3, pady=3)
        toolbar.pack(fill=tk.X, padx=10, pady=8)
        self.netdrive_toolbar = toolbar

        btn_refresh = HoverButton(
            toolbar, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Atualizar Lista", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), padx=8, pady=3, command=self.refresh_mapped_drives
        )
        toolbar.add_widget(btn_refresh)

        btn_open_exp = HoverButton(
            toolbar, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Abrir no Explorer", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8), padx=8, pady=3, command=self.open_selected_netdrive
        )
        toolbar.add_widget(btn_open_exp)

        btn_rename = HoverButton(
            toolbar, hover_bg=COLOR_BORDER, hover_fg=COLOR_TEXT_PRIMARY,
            text="Personalizar Unidade", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, relief="solid",
            font=("Segoe UI", 8), padx=8, pady=3, command=self.customize_selected_netdrive
        )
        toolbar.add_widget(btn_rename)

        btn_del_sel = HoverButton(
            toolbar, hover_bg=COLOR_BORDER, hover_fg="#ffffff",
            text="Desconectar Selecionada", bg=COLOR_WARNING, fg="#131315", bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), padx=8, pady=3, command=self.disconnect_selected_netdrive
        )
        toolbar.add_widget(btn_del_sel)

        btn_del_all = HoverButton(
            toolbar, hover_bg="#d93847", hover_fg="#ffffff",
            text="Desconectar TODAS", bg=COLOR_DANGER, fg="#ffffff", bd=1, relief="solid",
            font=("Segoe UI", 8, "bold"), padx=8, pady=3, command=self.disconnect_all_netdrives
        )
        toolbar.add_widget(btn_del_all)

        # Tabela Treeview
        tree_frame = tk.Frame(right_panel, bg=COLOR_BG_DARK)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        cols = ("drive", "label", "icon", "target", "type", "status", "persistent")
        self.netdrive_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse", height=7)

        scroll_nd_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.netdrive_tree.yview, style="Vertical.TScrollbar")
        self.netdrive_tree.configure(yscrollcommand=scroll_nd_y.set)

        self.netdrive_tree.heading("drive", text="Letra")
        self.netdrive_tree.heading("label", text="Nome / Rótulo")
        self.netdrive_tree.heading("icon", text="Ícone")
        self.netdrive_tree.heading("target", text="Caminho Mapeado / Destino")
        self.netdrive_tree.heading("type", text="Tipo")
        self.netdrive_tree.heading("status", text="Status")
        self.netdrive_tree.heading("persistent", text="Remapear no Logon")

        self.netdrive_tree.column("drive", width=50, anchor="center")
        self.netdrive_tree.column("label", width=130, anchor="w")
        self.netdrive_tree.column("icon", width=105, anchor="w")
        self.netdrive_tree.column("target", width=240, anchor="w")
        self.netdrive_tree.column("type", width=105, anchor="center")
        self.netdrive_tree.column("status", width=85, anchor="center")
        self.netdrive_tree.column("persistent", width=120, anchor="center")

        scroll_nd_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.netdrive_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.netdrive_tree.bind("<Double-1>", lambda e: self.open_selected_netdrive())

        # Menu de contexto (botão direito)
        self.netdrive_context_menu = tk.Menu(self, tearoff=0, bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, activebackground=COLOR_BORDER, activeforeground="#ffffff")
        self.netdrive_context_menu.add_command(label="Abrir no Explorer", command=self.open_selected_netdrive)
        self.netdrive_context_menu.add_command(label="Personalizar Nome e Ícone...", command=self.customize_selected_netdrive)
        self.netdrive_context_menu.add_separator()
        self.netdrive_context_menu.add_command(label="Desconectar Esta Unidade", command=self.disconnect_selected_netdrive)
        self.netdrive_tree.bind("<Button-3>", self.show_netdrive_context_menu)

        # Terminal de Logs
        lf_log = ttk.LabelFrame(right_panel, text=" Log de Execução de Comandos ")
        lf_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        self.netdrive_terminal = tk.Text(lf_log, bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, insertbackground=COLOR_TEXT_PRIMARY, font=("Consolas", 9), height=7)
        scroll_log = ttk.Scrollbar(lf_log, orient="vertical", command=self.netdrive_terminal.yview, style="Vertical.TScrollbar")
        self.netdrive_terminal.configure(yscrollcommand=scroll_log.set)

        self.netdrive_terminal.tag_config("normal", foreground=COLOR_TEXT_PRIMARY)
        self.netdrive_terminal.tag_config("green", foreground=COLOR_ACCENT)
        self.netdrive_terminal.tag_config("warning", foreground=COLOR_WARNING)
        self.netdrive_terminal.tag_config("red", foreground=COLOR_DANGER)
        self.netdrive_terminal.tag_config("cyan", foreground="#64d2ff")

        scroll_log.pack(side=tk.RIGHT, fill=tk.Y)
        self.netdrive_terminal.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.netdrive_terminal.config(state=tk.DISABLED)

        # Inicializa a lista de drives após a interface carregar
        self.after(300, self.refresh_mapped_drives)

    def _on_toggle_netdrive_creds(self):
        if self.var_netdrive_use_creds.get():
            self.f_creds.pack(fill=tk.X, padx=8, pady=(0, 6))
        else:
            self.f_creds.pack_forget()

    def browse_netdrive_path(self):
        p = filedialog.askdirectory(title="Selecione a Pasta para Mapear", parent=self)
        if p:
            self.var_netdrive_path.set(os.path.normpath(p))

    def clear_netdrive_fields(self):
        self.var_netdrive_path.set("")
        self.var_netdrive_user.set("")
        self.var_netdrive_password.set("")

    def log_netdrive(self, msg, tag="normal"):
        if hasattr(self, 'netdrive_terminal'):
            self.netdrive_terminal.config(state=tk.NORMAL)
            ts = datetime.datetime.now().strftime("[%H:%M:%S] ")
            self.netdrive_terminal.insert(tk.END, ts + msg + "\n", tag)
            self.netdrive_terminal.see(tk.END)
            self.netdrive_terminal.config(state=tk.DISABLED)

    def refresh_mapped_drives(self):
        if sys.platform != "win32":
            self.log_netdrive("O gerenciamento de letras de unidade de rede é exclusivo do Windows.", "warning")
            return

        try:
            self.netdrive_tree.delete(*self.netdrive_tree.get_children())
            mask = ctypes.windll.kernel32.GetLogicalDrives()
            used_letters = [chr(65 + i) for i in range(26) if (mask & (1 << i))]

            mapped_list = []
            mpr = ctypes.windll.mpr

            # 1. Unidades de Rede via WNetGetConnection
            for ltr in used_letters:
                drv = ltr + ":"
                buf = ctypes.create_unicode_buffer(512)
                sz = ctypes.c_ulong(512)
                res = mpr.WNetGetConnectionW(drv, buf, ctypes.byref(sz))
                if res == 0:
                    remote_path = buf.value
                    is_persist = "Não"
                    if winreg:
                        try:
                            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Network\{ltr}")
                            is_persist = "Sim (Logon)"
                            winreg.CloseKey(k)
                        except FileNotFoundError:
                            pass
                    mapped_list.append({
                        "drive": drv,
                        "target": remote_path,
                        "type": "Rede (net use)",
                        "status": "Conectado",
                        "persistent": is_persist
                    })

            # 2. Unidades virtuais locais via subst
            try:
                out = subprocess.check_output("subst", shell=True, text=True)
                for line in out.splitlines():
                    if "=>" in line:
                        parts = line.split("=>")
                        drv = normalize_drive_letter(parts[0])
                        target = parts[1].strip()
                        is_persist = "Não"
                        if winreg and drv:
                            try:
                                k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
                                val, _ = winreg.QueryValueEx(k, f"MPFolders_Drive_{drv[0]}")
                                is_persist = "Sim (Logon)"
                                winreg.CloseKey(k)
                            except Exception:
                                pass
                        mapped_list.append({
                            "drive": drv,
                            "target": target,
                            "type": "Virtual (subst)",
                            "status": "Conectado",
                            "persistent": is_persist
                        })
            except Exception:
                pass

            # Preenche Treeview
            for item in mapped_list:
                lbl = get_drive_label(item["drive"], item["target"]) or "-"
                icon_path = get_drive_icon(item["drive"])
                icon_disp = "Padrão"
                if icon_path:
                    if "shell32.dll,4" in icon_path:
                        icon_disp = "📁 Pasta"
                    elif "shell32.dll,9" in icon_path:
                        icon_disp = "🌐 Rede"
                    elif "shell32.dll,7" in icon_path:
                        icon_disp = "💾 Disco"
                    elif "shell32.dll,275" in icon_path:
                        icon_disp = "☁ Nuvem"
                    else:
                        icon_disp = os.path.basename(icon_path)
                self.netdrive_tree.insert(
                    "", tk.END,
                    values=(item["drive"], lbl, icon_disp, item["target"], item["type"], item["status"], item["persistent"])
                )

            self.mapped_drives_cache = mapped_list

            # Atualiza Combobox com letras disponíveis (Z até D)
            combo_values = []
            suggested_letter = None

            for code in range(ord('Z'), ord('C'), -1):
                letter = chr(code)
                drv = f"{letter}:"
                # Verifica se está em uso
                in_use = drv in [m["drive"] for m in mapped_list] or drv in [f"{u}:" for u in used_letters]
                if in_use:
                    # Encontra descrição
                    desc = next((m["target"] for m in mapped_list if m["drive"] == drv), "Em uso pelo sistema")
                    combo_values.append(f"{drv}  [Ocupado: {desc[:25]}]")
                else:
                    combo_values.append(f"{drv}  [Livre]")
                    if suggested_letter is None:
                        suggested_letter = f"{drv}  [Livre]"

            self.combo_netdrive_letter["values"] = combo_values
            if suggested_letter:
                self.combo_netdrive_letter.set(suggested_letter)
            elif combo_values:
                self.combo_netdrive_letter.set(combo_values[0])

            self.log_netdrive(f"Lista atualizada. {len(mapped_list)} unidade(s) mapeada(s) detectada(s).", "normal")

        except Exception as e:
            self.log_netdrive(f"Falha ao atualizar unidades de rede: {str(e)}", "red")

    def execute_map_drive(self):
        if sys.platform != "win32":
            messagebox.showerror("Aviso", "Mapeamento de unidades de rede com letras de drive é suportado apenas no Windows.", parent=self)
            return

        raw_letter = self.var_netdrive_letter.get().strip()
        if not raw_letter:
            messagebox.showerror("Erro", "Selecione uma letra de unidade.", parent=self)
            return
        drive_letter = normalize_drive_letter(raw_letter)

        target_path = self.var_netdrive_path.get().strip().strip('"')
        if not target_path:
            messagebox.showerror("Erro", "Informe o caminho da pasta a ser mapeada.", parent=self)
            return

        # Checa se a unidade já está em uso
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        letter_idx = ord(drive_letter[0]) - ord('A')
        if 0 <= letter_idx < 26 and (mask & (1 << letter_idx)):
            res = messagebox.askyesno(
                "Unidade em Uso",
                f"A unidade {drive_letter} já está sendo utilizada no Windows.\n\nDeseja forçar a desconexão anterior antes de remapear?",
                parent=self
            )
            if not res:
                return
            subprocess.run(["net", "use", drive_letter, "/delete", "/y"], capture_output=True, text=True)
            subprocess.run(["subst", drive_letter, "/d"], capture_output=True, text=True)
            remove_drive_label(drive_letter)
            remove_drive_icon(drive_letter)

        # Solicita o nome/rótulo amigável e ícone personalizado da unidade em janela modal
        default_label = os.path.basename(os.path.normpath(target_path)) if target_path else ""
        dialog = DriveCustomizeDialog(self, drive_letter, default_name=default_label, default_icon="", is_mapping=True)
        self.wait_window(dialog)

        if dialog.result is None:
            self.log_netdrive("Mapeamento cancelado pelo usuário.", "normal")
            return

        chosen_label = dialog.result.get("label", "") if isinstance(dialog.result, dict) else str(dialog.result or "")
        chosen_icon = dialog.result.get("icon", "") if isinstance(dialog.result, dict) else ""
        mode = self.var_netdrive_type.get()
        persistent = self.var_netdrive_persistent.get()

        try:
            # Se já é um caminho UNC (\\servidor\pasta)
            if target_path.startswith(r"\\"):
                cmd = ["net", "use", drive_letter, target_path]
                if self.var_netdrive_use_creds.get() and self.var_netdrive_user.get():
                    user = self.var_netdrive_user.get().strip()
                    pwd = self.var_netdrive_password.get()
                    if pwd:
                        cmd.append(pwd)
                    cmd.append(f"/user:{user}")
                cmd.append("/persistent:yes" if persistent else "/persistent:no")

                self.log_netdrive(f"Executando: net use {drive_letter} {target_path} ...", "cyan")
                p = subprocess.run(cmd, capture_output=True, text=True)
                if p.returncode == 0:
                    set_drive_label(drive_letter, chosen_label, unc_target=target_path)
                    set_drive_icon(drive_letter, chosen_icon)
                    name_info = f" [Nome: '{chosen_label}']" if chosen_label else ""
                    icon_info = f" [Ícone: '{os.path.basename(chosen_icon)}']" if chosen_icon else ""
                    self.log_netdrive(f"Sucesso: Unidade {drive_letter} mapeada para {target_path}{name_info}{icon_info}!", "green")
                    messagebox.showinfo("Sucesso", f"Unidade {drive_letter} mapeada com sucesso!{name_info}{icon_info}", parent=self)
                else:
                    err = p.stderr.strip() or p.stdout.strip()
                    self.log_netdrive(f"Erro ao mapear {drive_letter}: {err}", "red")
                    messagebox.showerror("Erro do Windows", f"Falha ao mapear unidade:\n\n{err}", parent=self)

            elif mode == "unc":
                # Converte caminho local para compartilhamento administrativo UNC localhost
                drive_p, rest_p = os.path.splitdrive(target_path)
                ltr_char = drive_p.rstrip(":")
                unc_target = rf"\\localhost\{ltr_char}${rest_p}"

                cmd = ["net", "use", drive_letter, unc_target]
                if self.var_netdrive_use_creds.get() and self.var_netdrive_user.get():
                    user = self.var_netdrive_user.get().strip()
                    pwd = self.var_netdrive_password.get()
                    if pwd:
                        cmd.append(pwd)
                    cmd.append(f"/user:{user}")
                cmd.append("/persistent:yes" if persistent else "/persistent:no")

                self.log_netdrive(f"Executando: net use {drive_letter} {unc_target} ...", "cyan")
                p = subprocess.run(cmd, capture_output=True, text=True)
                if p.returncode == 0:
                    set_drive_label(drive_letter, chosen_label, unc_target=unc_target)
                    set_drive_icon(drive_letter, chosen_icon)
                    name_info = f" [Nome: '{chosen_label}']" if chosen_label else ""
                    icon_info = f" [Ícone: '{os.path.basename(chosen_icon)}']" if chosen_icon else ""
                    self.log_netdrive(f"Sucesso: Unidade de rede {drive_letter} mapeada para {unc_target}{name_info}{icon_info}!", "green")
                    messagebox.showinfo("Sucesso", f"Unidade de rede {drive_letter} mapeada com sucesso!{name_info}{icon_info}", parent=self)
                else:
                    err = p.stderr.strip() or p.stdout.strip()
                    self.log_netdrive(f"Erro ao mapear UNC ({err}). Tentando alternativa subst...", "warning")
                    # Oferece fallback para subst
                    res = messagebox.askyesno(
                        "Falha no Modo Rede UNC",
                        f"O compartilhamento de rede local retornou erro:\n{err}\n\nDeseja mapear como Unidade Virtual Local (subst) agora?",
                        parent=self
                    )
                    if res:
                        self._map_subst(drive_letter, target_path, persistent, chosen_label=chosen_label, chosen_icon=chosen_icon)

            else:
                self._map_subst(drive_letter, target_path, persistent, chosen_label=chosen_label, chosen_icon=chosen_icon)

            self.refresh_mapped_drives()

        except Exception as e:
            self.log_netdrive(f"Exceção durante mapeamento: {str(e)}", "red")
            messagebox.showerror("Erro", f"Falha ao mapear unidade: {str(e)}", parent=self)

    def _map_subst(self, drive_letter, target_path, persistent, chosen_label="", chosen_icon=""):
        self.log_netdrive(f"Executando: subst {drive_letter} \"{target_path}\" ...", "cyan")
        p = subprocess.run(["subst", drive_letter, target_path], capture_output=True, text=True)
        if p.returncode == 0:
            if chosen_label:
                set_drive_label(drive_letter, chosen_label)
            if chosen_icon:
                set_drive_icon(drive_letter, chosen_icon)

            if persistent and winreg:
                try:
                    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(k, f"MPFolders_Drive_{drive_letter[0]}", 0, winreg.REG_SZ, f'subst {drive_letter} "{target_path}"')
                    winreg.CloseKey(k)
                    self.log_netdrive(f"Persistência no Logon configurada no Registro (HKCU\\Run).", "green")
                except Exception as ex:
                    self.log_netdrive(f"Aviso ao registrar logon: {str(ex)}", "warning")

            name_info = f" [Nome: '{chosen_label}']" if chosen_label else ""
            icon_info = f" [Ícone: '{os.path.basename(chosen_icon)}']" if chosen_icon else ""
            self.log_netdrive(f"Sucesso: Unidade virtual {drive_letter} criada para {target_path}{name_info}{icon_info}!", "green")
            messagebox.showinfo("Sucesso", f"Unidade virtual {drive_letter} criada com sucesso!{name_info}{icon_info}", parent=self)
        else:
            err = p.stderr.strip() or p.stdout.strip()
            self.log_netdrive(f"Erro ao executar subst {drive_letter}: {err}", "red")
            messagebox.showerror("Erro", f"Falha no comando subst:\n\n{err}", parent=self)

    def customize_selected_netdrive(self):
        selected = self.netdrive_tree.selection()
        if not selected:
            messagebox.showinfo("Aviso", "Selecione uma unidade na lista para personalizar.", parent=self)
            return

        values = self.netdrive_tree.item(selected[0], "values")
        if not values:
            return

        drv = normalize_drive_letter(values[0])
        target = values[3] if len(values) > 3 else (values[2] if len(values) > 2 else None)
        current_label = get_drive_label(drv, target)
        current_icon = get_drive_icon(drv)

        dialog = DriveCustomizeDialog(self, drv, default_name=current_label, default_icon=current_icon, is_mapping=False)
        self.wait_window(dialog)

        if dialog.result is not None:
            new_label = dialog.result.get("label", "")
            new_icon = dialog.result.get("icon", "")
            set_drive_label(drv, new_label, unc_target=target)
            set_drive_icon(drv, new_icon)

            parts = []
            if new_label:
                parts.append(f"Nome: '{new_label}'")
            else:
                parts.append("Nome padrão")
            if new_icon:
                parts.append(f"Ícone: '{os.path.basename(new_icon)}'")
            else:
                parts.append("Ícone padrão")

            self.log_netdrive(f"Unidade {drv} personalizada: " + ", ".join(parts), "green")
            self.refresh_mapped_drives()

    rename_selected_netdrive = customize_selected_netdrive

    def show_netdrive_context_menu(self, event):
        item_id = self.netdrive_tree.identify_row(event.y)
        if item_id:
            self.netdrive_tree.selection_set(item_id)
            self.netdrive_context_menu.tk_popup(event.x_root, event.y_root)

    def disconnect_selected_netdrive(self):
        selected = self.netdrive_tree.selection()
        if not selected:
            messagebox.showinfo("Aviso", "Selecione uma unidade mapeada na lista para desconectar.", parent=self)
            return

        values = self.netdrive_tree.item(selected[0], "values")
        if not values:
            return

        drv = normalize_drive_letter(values[0])
        label_disp = f" [{values[1]}]" if len(values) > 1 and values[1] != "-" else ""
        target_disp = values[3] if len(values) > 3 else (values[2] if len(values) > 2 else "")
        res = messagebox.askyesno(
            "Confirmar Desconexão",
            f"Deseja realmente desconectar a unidade {drv}{label_disp}?\n\nCaminho: {target_disp}",
            parent=self
        )
        if not res:
            return

        self.log_netdrive(f"Desconectando unidade {drv}...", "cyan")

        # 1. Desconecta via subst (se for unidade virtual)
        p_subst = subprocess.run(["subst", drv, "/d"], capture_output=True, text=True)
        if p_subst.returncode == 0:
            self.log_netdrive(f"Unidade virtual {drv} desconectada via subst.", "green")

        # 2. Desconecta via net use (se for compartilhamento de rede)
        p_net = subprocess.run(["net", "use", drv, "/delete", "/y"], capture_output=True, text=True)
        if p_net.returncode == 0:
            self.log_netdrive(f"Unidade de rede {drv} desconectada via net use.", "green")

        # 3. Fallback via API WNetCancelConnection2W
        try:
            ctypes.windll.mpr.WNetCancelConnection2W(drv, 1, True)
        except Exception:
            pass

        # 4. Fallback via API DefineDosDeviceW (DDD_REMOVE_DEFINITION = 0x2)
        try:
            target_path = values[3] if len(values) > 3 else None
            if target_path:
                ctypes.windll.kernel32.DefineDosDeviceW(0x6, drv, target_path)
            ctypes.windll.kernel32.DefineDosDeviceW(0x2, drv, None)
        except Exception:
            pass

        remove_drive_label(drv)
        remove_drive_icon(drv)

        if winreg and drv:
            try:
                k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(k, f"MPFolders_Drive_{drv[0]}")
                winreg.CloseKey(k)
            except Exception:
                pass

        # Validação se a letra do drive foi liberada no sistema
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        letter_idx = ord(drv[0].upper()) - ord('A')
        still_connected = bool(0 <= letter_idx < 26 and (mask & (1 << letter_idx)))

        if not still_connected or p_subst.returncode == 0 or p_net.returncode == 0:
            self.log_netdrive(f"Unidade {drv} desconectada com sucesso.", "green")
            messagebox.showinfo("Sucesso", f"Unidade {drv} desconectada com sucesso!", parent=self)
        else:
            err_subst = p_subst.stderr.strip() or p_subst.stdout.strip()
            err_net = p_net.stderr.strip() or p_net.stdout.strip()
            err_details = []
            if err_subst:
                err_details.append(f"subst: {err_subst}")
            if err_net:
                err_details.append(f"net use: {err_net}")
            err_msg = "\n".join(err_details) if err_details else "O Windows não liberou a letra da unidade."
            self.log_netdrive(f"Erro ao desconectar {drv}: {err_msg}", "red")
            messagebox.showerror("Erro ao Desconectar", f"Não foi possível desconectar a unidade {drv}:\n\n{err_msg}", parent=self)

        self.refresh_mapped_drives()

    def disconnect_all_netdrives(self):
        if not self.mapped_drives_cache:
            messagebox.showinfo("Aviso", "Nenhuma unidade mapeada encontrada para desconectar.", parent=self)
            return

        res = messagebox.askyesno(
            "Confirmar Desconexão Geral",
            "Atenção: Deseja desconectar TODAS as unidades mapeadas listadas?",
            parent=self
        )
        if not res:
            return

        for item in self.mapped_drives_cache:
            drv = normalize_drive_letter(item["drive"])
            self.log_netdrive(f"Desconectando {drv}...", "cyan")
            subprocess.run(["subst", drv, "/d"], capture_output=True, text=True)
            subprocess.run(["net", "use", drv, "/delete", "/y"], capture_output=True, text=True)
            try:
                ctypes.windll.mpr.WNetCancelConnection2W(drv, 1, True)
            except Exception:
                pass
            try:
                ctypes.windll.kernel32.DefineDosDeviceW(0x2, drv, None)
            except Exception:
                pass
            remove_drive_label(drv)
            remove_drive_icon(drv)
            if winreg and drv:
                try:
                    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                    winreg.DeleteValue(k, f"MPFolders_Drive_{drv[0]}")
                    winreg.CloseKey(k)
                except Exception:
                    pass

        self.log_netdrive("Todas as unidades mapeadas foram desconectadas.", "green")
        self.refresh_mapped_drives()

    def open_selected_netdrive(self):
        selected = self.netdrive_tree.selection()
        if not selected:
            messagebox.showinfo("Aviso", "Selecione uma unidade na lista para abrir.", parent=self)
            return

        values = self.netdrive_tree.item(selected[0], "values")
        if not values:
            return

        drv = normalize_drive_letter(values[0])
        try:
            if os.path.exists(f"{drv}\\"):
                os.startfile(f"{drv}\\")
            else:
                messagebox.showwarning("Aviso", f"A unidade {drv} não está acessível no momento.", parent=self)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao abrir a unidade {drv}: {str(e)}", parent=self)

    # =========================================================================
    # AUXILIAR: CHECK LOOP DE CONTROLE DE THREADS (Thread-Safe GUI)
    # =========================================================================
    def check_queue_loop(self):
        try:
            while not self.log_queue.empty():
                item = self.log_queue.get_nowait()
                try:
                    if isinstance(item, (tuple, list)) and len(item) == 3:
                        msg, tag, target = item
                        if target == "cleaner":
                            self.log_clean(msg, tag)
                        elif target == "backup":
                            self.log_bkp(msg, tag)
                        elif target == "renamer":
                            self.log_renamer(msg, tag)
                        elif target == "card_copy":
                            self.log_card_copy(msg, tag)
                        elif target == "diff":
                            self.log_diff(msg, tag)
                        elif target == "netdrive":
                            self.log_netdrive(msg, tag)
                        else:
                            self.log_clean(msg, tag)
                    else:
                        if isinstance(item, (tuple, list)) and len(item) == 2:
                            msg, tag = item
                        else:
                            msg, tag = str(item), "normal"
                        active_tab = self.notebook.index(self.notebook.select())
                        if active_tab == 1: # Limpeza
                            self.log_clean(msg, tag)
                        elif active_tab == 2: # Backup
                            self.log_bkp(msg, tag)
                        elif active_tab == 3: # Renomeador
                            self.log_renamer(msg, tag)
                        elif active_tab == 4: # Copia do Cartão
                            self.log_card_copy(msg, tag)
                        elif active_tab == 5: # Comparar Pastas
                            self.log_diff(msg, tag)
                        elif active_tab == 6: # Unidades de Rede
                            self.log_netdrive(msg, tag)
                        else:
                            self.log_clean(msg, tag)
                except Exception:
                    pass
        finally:
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
        try:
            x = max(10, parent.winfo_x() + (parent.winfo_width() - w) // 2)
            y = max(10, parent.winfo_y() + (parent.winfo_height() - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

        round_window_corners(self)
        self.transient(parent)
        self.grab_set()

        # UI Header
        header = tk.Frame(self, bg=COLOR_BG_CARD, padx=15, pady=10)
        header.pack(fill=tk.X)
        tk.Label(header, text="⚠ Conflito de Nome de Arquivo", bg=COLOR_BG_CARD, fg=COLOR_WARNING, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(header, text=f"O arquivo '{filename}' já existe no destino com o mesmo nome.", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 9)).pack(anchor="w")

        # Detalhes
        card = tk.Frame(self, bg=COLOR_BG_INPUT, padx=12, pady=10, highlightbackground=COLOR_BORDER, highlightthickness=1)
        card.pack(fill=tk.X, padx=15, pady=(10, 5))

        src_info = "N/A"
        dst_info = "N/A"
        try:
            lp_s = to_long_path(src_path)
            if os.path.exists(lp_s):
                s_sz = format_size(os.path.getsize(lp_s))
                s_dt = datetime.datetime.fromtimestamp(os.path.getmtime(lp_s)).strftime("%d/%m/%Y %H:%M")
                src_info = f"{s_sz} | Modificado: {s_dt}"
        except Exception:
            pass

        try:
            lp_d = to_long_path(dst_path)
            if os.path.exists(lp_d):
                d_sz = format_size(os.path.getsize(lp_d))
                d_dt = datetime.datetime.fromtimestamp(os.path.getmtime(lp_d)).strftime("%d/%m/%Y %H:%M")
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
        try:
            x = max(10, parent.winfo_x() + (parent.winfo_width() - width) // 2)
            y = max(10, parent.winfo_y() + (parent.winfo_height() - height) // 2)
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass
        
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