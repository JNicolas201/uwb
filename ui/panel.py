import customtkinter as ctk
from tkinter import scrolledtext
import tkinter as tk
from config import TAGS
from estado import estado_tags, tag_seleccionado

def abrir_log(parent, nombre_tag):
    win = ctk.CTkToplevel(parent)
    win.title(f"Historial — {nombre_tag}")
    win.geometry("520x520")
    win.configure(fg_color="#1a1a2e")

    color = TAGS[nombre_tag]["ctk_color"]
    ctk.CTkLabel(win,
                 text=f"  Historial: {nombre_tag}",
                 font=ctk.CTkFont(size=15, weight="bold"),
                 text_color=color).pack(pady=(14, 4), padx=16, anchor='w')

    ctk.CTkFrame(win, height=2, fg_color="#333355").pack(
        fill='x', padx=16, pady=(0, 8))

    text_area = scrolledtext.ScrolledText(
        win,
        bg="#0d0d1a", fg="#00ff88",
        font=("Courier New", 9),
        wrap=tk.NONE,
        relief='flat', bd=0
    )
    text_area.pack(padx=16, pady=4, fill='both', expand=True)

    def actualizar():
        if not win.winfo_exists():
            return
        log = list(estado_tags[nombre_tag]["log"])
        text_area.config(state='normal')
        text_area.delete('1.0', tk.END)
        text_area.insert(
            tk.END,
            f"  {'HORA':8}  {'ESTADO':8}  "
            f"{'X':6} {'Y':6} {'Z':6}  VEL\n"
        )
        text_area.insert(tk.END, "  " + "─" * 55 + "\n")
        for linea in log:
            text_area.insert(tk.END, "  " + linea + "\n")
        text_area.config(state='disabled')
        win.after(500, actualizar)

    actualizar()

    def exportar():
        from datetime import datetime as dt
        fname = (f"log_{nombre_tag}_"
                 f"{dt.now().strftime('%Y%m%d_%H%M%S')}.csv")
        with open(fname, 'w') as f:
            f.write("Hora,Estado,X,Y,Z,Velocidad\n")
            for linea in estado_tags[nombre_tag]["log"]:
                f.write(
                    linea.replace(" | ", ",")
                         .replace("X:", "")
                         .replace("Y:", "")
                         .replace("Z:", "")
                         .replace("m/s", "") + "\n"
                )
        msg_exp.configure(text=f"✓ Guardado: {fname}")

    btn_f = ctk.CTkFrame(win, fg_color="transparent")
    btn_f.pack(fill='x', padx=16, pady=8)

    ctk.CTkButton(btn_f, text="Exportar CSV",
                  fg_color="#006633", hover_color="#009944",
                  height=34, corner_radius=6,
                  command=exportar).pack(side='left', padx=(0, 8))

    ctk.CTkButton(btn_f, text="Limpiar",
                  fg_color="#444444", hover_color="#666666",
                  height=34, corner_radius=6,
                  command=lambda: estado_tags[nombre_tag]["log"].clear()
                  ).pack(side='left')

    msg_exp = ctk.CTkLabel(btn_f, text="",
                            text_color="#00ff88",
                            font=ctk.CTkFont(size=10))
    msg_exp.pack(side='left', padx=10)


class PanelInfo(ctk.CTkFrame):
    def __init__(self, parent, on_cerrar, **kwargs):
        super().__init__(parent, fg_color="#16213e",
                         corner_radius=10, **kwargs)
        self.on_cerrar  = on_cerrar
        self.info_labels = {}
        self.mini_log   = None
        self.nombre_tag = None
        self.app_parent = parent  # ← nombre cambiado

    def mostrar(self, nombre):
        self.nombre_tag = nombre

        # Destruir widgets hijos manualmente
        for w in list(self.children.values()):
            try:
                w.destroy()
            except Exception:
                pass

        info  = TAGS[nombre]
        color = info["ctk_color"]

        # Header
        h = ctk.CTkFrame(self, fg_color="#0f3460", corner_radius=8)
        h.pack(fill='x', padx=10, pady=(10, 4))

        ctk.CTkLabel(h, text=f"  {nombre}",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=color).pack(side='left', padx=10, pady=8)

        ctk.CTkButton(h, text="✕",
                      width=28, height=28,
                      fg_color="#333355",
                      hover_color="#555577",
                      font=ctk.CTkFont(size=12),
                      command=self.on_cerrar).pack(
            side='right', padx=8, pady=8)

        # Cards info
        campos = [
            ("Estado",      "estado"),
            ("X",           "x"),
            ("Y",           "y"),
            ("Z",           "z"),
            ("Velocidad",   "velocidad"),
            ("Quieto hace", "quieto"),
            ("Conexion",    "conexion"),
        ]

        self.info_labels = {}
        for label, key in campos:
            row = ctk.CTkFrame(self, fg_color="#0f3460", corner_radius=6)
            row.pack(fill='x', padx=10, pady=2)
            ctk.CTkLabel(row, text=f"  {label}:",
                         text_color="#888899",
                         font=ctk.CTkFont(size=11),
                         width=100, anchor='w').pack(
                side='left', padx=4, pady=6)
            val = ctk.CTkLabel(row, text="---",
                               text_color="white",
                               font=ctk.CTkFont(size=11, weight="bold"),
                               anchor='w')
            val.pack(side='left', padx=4)
            self.info_labels[key] = val

        # Separador
        ctk.CTkFrame(self, height=2,
                     fg_color="#333355").pack(
            fill='x', padx=10, pady=(8, 4))

        ctk.CTkLabel(self, text="  Historial reciente",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="white").pack(
            anchor='w', padx=10, pady=(4, 2))

        self.mini_log = ctk.CTkTextbox(
            self,
            fg_color="#0d0d1a",
            text_color="#00ff88",
            font=ctk.CTkFont(family="Courier New", size=9),
            corner_radius=6,
            height=130
        )
        self.mini_log.pack(fill='x', padx=10, pady=4)
        self.mini_log.configure(state='disabled')

        ctk.CTkButton(self,
                      text="  Ver historial completo",
                      font=ctk.CTkFont(size=11, weight="bold"),
                      fg_color="#0f3460",
                      hover_color="#1a4a80",
                      height=32, corner_radius=6,
                      command=lambda: abrir_log(self.app_parent, nombre)
                      ).pack(fill='x', padx=10, pady=(2, 8))

    def actualizar(self):
        nombre = self.nombre_tag
        if not nombre or nombre not in estado_tags:
            return
        if not self.info_labels:
            return

        tag = estado_tags[nombre]
        seg = round(tag["tiempo_quieto"] * 0.1, 1)

        self.info_labels["estado"].configure(
            text="QUIETO" if tag["quieto"] else "MOVIENDO",
            text_color="#ff6b6b" if tag["quieto"] else "#6bff6b")
        self.info_labels["x"].configure(
            text=f"{tag['x']:.3f} m")
        self.info_labels["y"].configure(
            text=f"{tag['y']:.3f} m")
        self.info_labels["z"].configure(
            text=f"{tag['z']:.3f} m")
        self.info_labels["velocidad"].configure(
            text=f"{tag['velocidad']:.2f} m/s")
        self.info_labels["quieto"].configure(
            text=f"{seg} seg")
        self.info_labels["conexion"].configure(
            text="CONECTADO" if tag["conectado"] else "SIN CONEXION",
            text_color="#6bff6b" if tag["conectado"] else "#ff6b6b")

        if self.mini_log:
            log = list(tag["log"])[:8]
            self.mini_log.configure(state='normal')
            self.mini_log.delete('1.0', 'end')
            for linea in log:
                self.mini_log.insert('end', linea + "\n")
            self.mini_log.configure(state='disabled')