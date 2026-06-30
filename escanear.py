import asyncio
import threading
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
from collections import deque
from datetime import datetime
from bleak import BleakClient
import customtkinter as ctk
from tkinter import scrolledtext
import tkinter as tk

# ─── TEMA ────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ─── CONFIGURACIÓN ───────────────────────────────
TAGS = {
    "DW0214_verde": {
        "mac": "EF:D4:9A:60:7B:08",
        "color": "royalblue",
        "color_rastro": "cornflowerblue",
        "ctk_color": "#4169e1",
    },
    "Tag2": {
        "mac": "D7:E4:49:3E:07:FC",
        "color": "red",
        "color_rastro": "lightsalmon",
        "ctk_color": "#e14141",
    },
}

ANCHORS = {
    "DW068E": {"pos": [0.0, 0.0], "tipo": "Slave"},
    "DWD885": {"pos": [0.0, 4.0], "tipo": "Slave"},
    "DW8624": {"pos": [4.0, 0.0], "tipo": "Slave"},
    "DW4CAE": {"pos": [4.0, 4.0], "tipo": "Initiator"},
}

UUID_POS  = "003bbdf2-c634-4b3d-ab56-7ec889b89a37"
config    = {"ancho": 4.0, "alto": 4.0}
sistema   = {"pausado": False, "umbral": 0.02, "suavizado": 3}
tag_seleccionado = {"nombre": None}

estado_tags = {
    nombre: {
        "x": 2.0, "y": 2.0, "z": 0.0,
        "quieto": True,
        "historial_x": [],
        "historial_y": [],
        "anterior": None,
        "conectado": False,
        "buffer_x": deque(maxlen=3),
        "buffer_y": deque(maxlen=3),
        "buffer_z": deque(maxlen=3),
        "velocidad": 0.0,
        "tiempo_quieto": 0,
        "log": deque(maxlen=1000),
    }
    for nombre in TAGS
}

# ─── BLE ─────────────────────────────────────────
def decodificar(data):
    flag = data[0]
    if flag == 0x02 and len(data) >= 13:
        x = int.from_bytes(data[1:5],  'little', signed=True) / 1000
        y = int.from_bytes(data[5:9],  'little', signed=True) / 1000
        z = int.from_bytes(data[9:13], 'little', signed=True) / 1000
        q = data[13] if len(data) > 13 else 0
        return x, y, z, q
    return None

def hacer_callback(nombre):
    def callback(sender, data):
        if sistema["pausado"]:
            return
        resultado = decodificar(data)
        if resultado is None:
            return
        x, y, z, q = resultado
        if q == 0:
            return
        if not (0 <= x <= 20 and 0 <= y <= 20 and 0 <= z <= 10):
            return
        tag = estado_tags[nombre]
        n = sistema["suavizado"]
        if tag["buffer_x"].maxlen != n:
            tag["buffer_x"] = deque(tag["buffer_x"], maxlen=n)
            tag["buffer_y"] = deque(tag["buffer_y"], maxlen=n)
            tag["buffer_z"] = deque(tag["buffer_z"], maxlen=n)
        tag["buffer_x"].append(x)
        tag["buffer_y"].append(y)
        tag["buffer_z"].append(z)
        x_s = sum(tag["buffer_x"]) / len(tag["buffer_x"])
        y_s = sum(tag["buffer_y"]) / len(tag["buffer_y"])
        z_s = sum(tag["buffer_z"]) / len(tag["buffer_z"])
        if tag["anterior"]:
            dist = ((x_s - tag["anterior"][0])**2 +
                    (y_s - tag["anterior"][1])**2)**0.5
            tag["velocidad"] = round(dist / 0.1, 2)
            tag["quieto"]    = dist < sistema["umbral"]
            if tag["quieto"]:
                tag["tiempo_quieto"] += 1
            else:
                tag["tiempo_quieto"] = 0
        else:
            tag["quieto"] = False
        tag["x"] = x_s
        tag["y"] = y_s
        tag["z"] = z_s
        tag["anterior"] = (x_s, y_s, z_s)
        hora   = datetime.now().strftime("%H:%M:%S")
        estado = "QUIETO  " if tag["quieto"] else "MOVIENDO"
        tag["log"].appendleft(
            f"{hora} | {estado} | X:{x_s:.2f} Y:{y_s:.2f} Z:{z_s:.2f} | {tag['velocidad']:.2f}m/s"
        )
    return callback

async def conectar_tag(nombre, mac):
    print(f"Conectando a {nombre}...")
    while True:
        try:
            async with BleakClient(mac, timeout=30.0) as client:
                estado_tags[nombre]["conectado"] = True
                print(f"✓ {nombre} conectado!")
                await client.start_notify(UUID_POS, hacer_callback(nombre))
                await asyncio.sleep(9999)
        except Exception as e:
            estado_tags[nombre]["conectado"] = False
            print(f"✗ {nombre} desconectado - Reconectando en 5s...")
            await asyncio.sleep(5)

async def ble_loop():
    await asyncio.gather(*[
        conectar_tag(nombre, info["mac"])
        for nombre, info in TAGS.items()
    ])

def iniciar_ble():
    asyncio.run(ble_loop())

# ─── VENTANA CONFIGURACIÓN ───────────────────────
def abrir_configuracion(root):
    win = ctk.CTkToplevel(root)
    win.title("Configuracion RTLS")
    win.geometry("620x640")
    win.resizable(False, False)
    win.configure(fg_color="#1a1a2e")

    # Título
    ctk.CTkLabel(win, text="⚙  CONFIGURACION RTLS",
                 font=ctk.CTkFont(size=18, weight="bold"),
                 text_color="#e94560").pack(pady=(16, 4), padx=20, anchor='w')

    ctk.CTkFrame(win, height=2, fg_color="#333355").pack(
        fill='x', padx=20, pady=(0, 10))

    # Scroll frame
    scroll = ctk.CTkScrollableFrame(win, fg_color="#16213e",
                                     corner_radius=10)
    scroll.pack(fill='both', expand=True, padx=16, pady=(0, 10))

    # ── Anchors ──
    ctk.CTkLabel(scroll, text="ANCHORS",
                 font=ctk.CTkFont(size=14, weight="bold"),
                 text_color="#e94560").pack(anchor='w', pady=(10, 4), padx=10)

    anchor_entries = {}
    tipos_var      = {}

    for nombre, info in ANCHORS.items():
        frame = ctk.CTkFrame(scroll, fg_color="#0f3460", corner_radius=8)
        frame.pack(fill='x', padx=10, pady=4)

        color_txt = "#ffcc00" if info["tipo"] == "Initiator" else "#aaaaff"
        ctk.CTkLabel(frame, text=nombre,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=color_txt).grid(
            row=0, column=0, padx=12, pady=6, sticky='w')

        tipo_var = ctk.StringVar(value=info["tipo"])
        tipos_var[nombre] = tipo_var
        ctk.CTkOptionMenu(frame, variable=tipo_var,
                          values=["Slave", "Initiator"],
                          width=110, fg_color="#1a1a2e",
                          button_color="#e94560",
                          button_hover_color="#c73652").grid(
            row=0, column=1, padx=8, pady=6)

        ctk.CTkLabel(frame, text="X:", text_color="#aaaaaa").grid(
            row=0, column=2, padx=(12, 2))
        ex = ctk.CTkEntry(frame, width=70, placeholder_text="0.0",
                          fg_color="#1a1a2e", border_color="#333355")
        ex.insert(0, str(info["pos"][0]))
        ex.grid(row=0, column=3, padx=4, pady=6)

        ctk.CTkLabel(frame, text="Y:", text_color="#aaaaaa").grid(
            row=0, column=4, padx=(8, 2))
        ey = ctk.CTkEntry(frame, width=70, placeholder_text="0.0",
                          fg_color="#1a1a2e", border_color="#333355")
        ey.insert(0, str(info["pos"][1]))
        ey.grid(row=0, column=5, padx=(4, 12), pady=6)

        anchor_entries[nombre] = {"ex": ex, "ey": ey}

    # ── Parámetros ──
    ctk.CTkFrame(scroll, height=2, fg_color="#333355").pack(
        fill='x', padx=10, pady=(12, 4))
    ctk.CTkLabel(scroll, text="PARAMETROS",
                 font=ctk.CTkFont(size=14, weight="bold"),
                 text_color="#00d4aa").pack(anchor='w', pady=(4, 6), padx=10)

    param_frame = ctk.CTkFrame(scroll, fg_color="#0f3460", corner_radius=8)
    param_frame.pack(fill='x', padx=10, pady=4)

    params = [
        ("Ancho area (m):",       str(config["ancho"])),
        ("Alto area (m):",        str(config["alto"])),
        ("Umbral movimiento (m):", str(sistema["umbral"])),
        ("Suavizado (lecturas):",  str(sistema["suavizado"])),
    ]
    param_entries = []
    for i, (label, val) in enumerate(params):
        ctk.CTkLabel(param_frame, text=label,
                     text_color="#aaaaaa",
                     font=ctk.CTkFont(size=11)).grid(
            row=i, column=0, padx=12, pady=6, sticky='w')
        e = ctk.CTkEntry(param_frame, width=100,
                         fg_color="#1a1a2e", border_color="#333355")
        e.insert(0, val)
        e.grid(row=i, column=1, padx=12, pady=6, sticky='w')
        param_entries.append(e)

    # ── Tags ──
    ctk.CTkFrame(scroll, height=2, fg_color="#333355").pack(
        fill='x', padx=10, pady=(12, 4))
    ctk.CTkLabel(scroll, text="TAGS",
                 font=ctk.CTkFont(size=14, weight="bold"),
                 text_color="#4169e1").pack(anchor='w', pady=(4, 6), padx=10)

    for nombre, info in TAGS.items():
        tf = ctk.CTkFrame(scroll, fg_color="#0f3460", corner_radius=8)
        tf.pack(fill='x', padx=10, pady=4)
        ctk.CTkLabel(tf, text=f"  {nombre}",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=info["ctk_color"]).grid(
            row=0, column=0, padx=12, pady=6, sticky='w')
        ctk.CTkLabel(tf, text=f"MAC: {info['mac']}",
                     text_color="#888888",
                     font=ctk.CTkFont(size=10)).grid(
            row=0, column=1, padx=12, pady=6, sticky='w')

    # Mensaje
    msg_var = ctk.StringVar(value="")
    msg_label = ctk.CTkLabel(win, textvariable=msg_var,
                              text_color="#00ff88",
                              font=ctk.CTkFont(size=11))
    msg_label.pack(pady=4)

    # Botón guardar
    def guardar():
        try:
            for nombre, entries in anchor_entries.items():
                ANCHORS[nombre]["pos"][0] = float(entries["ex"].get())
                ANCHORS[nombre]["pos"][1] = float(entries["ey"].get())
                ANCHORS[nombre]["tipo"]   = tipos_var[nombre].get()
            config["ancho"]      = float(param_entries[0].get())
            config["alto"]       = float(param_entries[1].get())
            sistema["umbral"]    = float(param_entries[2].get())
            sistema["suavizado"] = int(param_entries[3].get())
            msg_var.set("✓ Configuracion guardada")
            win.after(3000, lambda: msg_var.set(""))
            print("✓ Configuracion guardada")
        except Exception as e:
            msg_var.set(f"Error: {e}")

    ctk.CTkButton(win, text="  GUARDAR CAMBIOS",
                  font=ctk.CTkFont(size=13, weight="bold"),
                  fg_color="#006633", hover_color="#009944",
                  height=40, corner_radius=8,
                  command=guardar).pack(
        fill='x', padx=20, pady=(0, 16))

# ─── VENTANA LOG ─────────────────────────────────
def abrir_log(root, nombre_tag):
    win = ctk.CTkToplevel(root)
    win.title(f"Historial — {nombre_tag}")
    win.geometry("520x520")
    win.configure(fg_color="#1a1a2e")

    color = TAGS[nombre_tag]["ctk_color"]

    ctk.CTkLabel(win,
                 text=f"  Historial: {nombre_tag}",
                 font=ctk.CTkFont(size=15, weight="bold"),
                 text_color=color).pack(
        pady=(14, 4), padx=16, anchor='w')

    ctk.CTkFrame(win, height=2, fg_color="#333355").pack(
        fill='x', padx=16, pady=(0, 8))

    text_area = scrolledtext.ScrolledText(
        win,
        bg="#0d0d1a", fg="#00ff88",
        font=("Courier New", 9),
        wrap=tk.NONE,
        insertbackground='white',
        selectbackground="#333355",
        relief='flat', bd=0
    )
    text_area.pack(padx=16, pady=4, fill='both', expand=True)

    def actualizar():
        if not win.winfo_exists():
            return
        tag  = estado_tags[nombre_tag]
        log  = list(tag["log"])
        text_area.config(state='normal')
        text_area.delete('1.0', tk.END)
        text_area.insert(tk.END,
            f"  {'HORA':8}  {'ESTADO':8}  {'X':6} {'Y':6} {'Z':6}  VEL\n")
        text_area.insert(tk.END, "  " + "─" * 55 + "\n")
        for linea in log:
            text_area.insert(tk.END, "  " + linea + "\n")
        text_area.config(state='disabled')
        win.after(500, actualizar)

    actualizar()

    def exportar():
        from datetime import datetime as dt
        fname = f"log_{nombre_tag}_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(fname, 'w') as f:
            f.write("Hora,Estado,X,Y,Z,Velocidad\n")
            for linea in estado_tags[nombre_tag]["log"]:
                f.write(linea.replace(" | ", ",").replace(
                    "X:", "").replace("Y:", "").replace(
                    "Z:", "").replace("m/s", "") + "\n")
        msg_exp.configure(text=f"✓ Guardado: {fname}")
        print(f"✓ Exportado: {fname}")

    btn_frame = ctk.CTkFrame(win, fg_color="transparent")
    btn_frame.pack(fill='x', padx=16, pady=8)

    ctk.CTkButton(btn_frame, text="Exportar CSV",
                  font=ctk.CTkFont(size=12, weight="bold"),
                  fg_color="#006633", hover_color="#009944",
                  height=34, corner_radius=8,
                  command=exportar).pack(side='left', padx=(0, 8))

    ctk.CTkButton(btn_frame, text="Limpiar",
                  font=ctk.CTkFont(size=12),
                  fg_color="#444444", hover_color="#666666",
                  height=34, corner_radius=8,
                  command=lambda: estado_tags[nombre_tag]["log"].clear()
                  ).pack(side='left')

    msg_exp = ctk.CTkLabel(btn_frame, text="",
                            text_color="#00ff88",
                            font=ctk.CTkFont(size=10))
    msg_exp.pack(side='left', padx=10)

# ─── APP PRINCIPAL ───────────────────────────────
class AppRTLS(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("System RTLS")
        self.geometry("1280x780")
        self.configure(fg_color="#1a1a2e")
        self.resizable(True, True)

        self.log_wins   = {}
        self.panel_vis  = False

        self._build_ui()
        self._build_mapa()
        self._start_animation()

    def _build_ui(self):
        # ── Barra superior ──
        top = ctk.CTkFrame(self, height=56, fg_color="#16213e",
                           corner_radius=0)
        top.pack(fill='x', side='top')
        top.pack_propagate(False)

        ctk.CTkLabel(top, text="⬡  System RTLS",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#e94560").pack(
            side='left', padx=20, pady=10)

        ctk.CTkFrame(top, width=2, fg_color="#333355").pack(
            side='left', fill='y', padx=8, pady=8)

        ctk.CTkLabel(top,
                     text=f"Anchors: {len(ANCHORS)}",
                     font=ctk.CTkFont(size=12),
                     text_color="#aaaacc").pack(side='left', padx=12)

        ctk.CTkLabel(top,
                     text=f"Tags: {len(TAGS)}",
                     font=ctk.CTkFont(size=12),
                     text_color="#aaaacc").pack(side='left', padx=4)

        # Botones derecha
        ctk.CTkButton(top, text="⚙  Configuracion",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      fg_color="#0f3460", hover_color="#1a4a80",
                      height=36, corner_radius=8,
                      command=lambda: abrir_configuracion(self)
                      ).pack(side='right', padx=(8, 16), pady=10)

        self.btn_pausa = ctk.CTkButton(
            top, text="⏸  Detener",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#8b0000", hover_color="#cc0000",
            height=36, corner_radius=8,
            command=self._toggle_pausa)
        self.btn_pausa.pack(side='right', padx=4, pady=10)

        # ── Contenedor principal ──
        self.main = ctk.CTkFrame(self, fg_color="#1a1a2e",
                                  corner_radius=0)
        self.main.pack(fill='both', expand=True)

        # Frame mapa
        self.frame_mapa = ctk.CTkFrame(
            self.main, fg_color="#12122a", corner_radius=10)
        self.frame_mapa.pack(side='left', fill='both',
                              expand=True, padx=(10, 5), pady=10)

        # Panel derecho (oculto)
        self.frame_panel = ctk.CTkFrame(
            self.main, fg_color="#16213e",
            corner_radius=10, width=320)
        self.frame_panel.pack_propagate(False)

    def _build_panel_info(self, nombre):
        # Limpiar panel
        for w in self.frame_panel.winfo_children():
            w.destroy()

        info  = TAGS[nombre]
        color = info["ctk_color"]

        # Header
        h = ctk.CTkFrame(self.frame_panel,
                          fg_color="#0f3460", corner_radius=8)
        h.pack(fill='x', padx=10, pady=(10, 4))

        ctk.CTkLabel(h, text=f"  {nombre}",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=color).pack(
            side='left', padx=10, pady=8)

        ctk.CTkButton(h, text="✕",
                      width=28, height=28,
                      fg_color="#333355",
                      hover_color="#555577",
                      font=ctk.CTkFont(size=12),
                      command=self._cerrar_panel).pack(
            side='right', padx=8, pady=8)

        # Info cards
        campos = [
            ("Estado",     "estado"),
            ("X",          "x"),
            ("Y",          "y"),
            ("Z",          "z"),
            ("Velocidad",  "velocidad"),
            ("Quieto hace","quieto"),
            ("Conexion",   "conexion"),
        ]

        self.info_labels = {}
        for label, key in campos:
            row = ctk.CTkFrame(self.frame_panel,
                               fg_color="#0f3460", corner_radius=6)
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
            val.pack(side='left', padx=4, pady=6)
            self.info_labels[key] = val

        # Separador
        ctk.CTkFrame(self.frame_panel, height=2,
                     fg_color="#333355").pack(
            fill='x', padx=10, pady=(8, 4))

        ctk.CTkLabel(self.frame_panel,
                     text="  Historial de posiciones",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="white").pack(
            anchor='w', padx=10, pady=(4, 2))

        # Mini log (últimas 8 entradas)
        self.mini_log = ctk.CTkTextbox(
            self.frame_panel,
            fg_color="#0d0d1a",
            text_color="#00ff88",
            font=ctk.CTkFont(family="Courier New", size=9),
            corner_radius=6,
            height=140
        )
        self.mini_log.pack(fill='x', padx=10, pady=4)
        self.mini_log.configure(state='disabled')

        # Botón ver historial completo
        ctk.CTkButton(self.frame_panel,
                      text="  Ver historial completo",
                      font=ctk.CTkFont(size=11, weight="bold"),
                      fg_color="#0f3460",
                      hover_color="#1a4a80",
                      height=32, corner_radius=6,
                      command=lambda: abrir_log(self, nombre)
                      ).pack(fill='x', padx=10, pady=(2, 6))

    def _cerrar_panel(self):
        tag_seleccionado["nombre"] = None
        self.panel_vis = False
        self.frame_panel.pack_forget()
        self.frame_mapa.pack(side='left', fill='both',
                              expand=True, padx=(10, 5), pady=10)

    def _toggle_pausa(self):
        sistema["pausado"] = not sistema["pausado"]
        if sistema["pausado"]:
            self.btn_pausa.configure(
                text="▶  Iniciar",
                fg_color="#006633",
                hover_color="#009944")
        else:
            self.btn_pausa.configure(
                text="⏸  Detener",
                fg_color="#8b0000",
                hover_color="#cc0000")

    def _build_mapa(self):
        self.fig = plt.Figure(figsize=(8, 7), facecolor="#12122a")
        self.ax  = self.fig.add_subplot(111)
        self.ax.set_facecolor("#1a1a2e")

        self.canvas_mpl = FigureCanvasTkAgg(self.fig, self.frame_mapa)
        self.canvas_mpl.get_tk_widget().pack(
            fill='both', expand=True, padx=4, pady=4)

        # Anchors
        self.anchor_artists = {}
        for nombre, info in ANCHORS.items():
            p, = self.ax.plot(
                info["pos"][0], info["pos"][1],
                's', color='#e94560', markersize=14, zorder=5)
            tipo = "★" if info["tipo"] == "Initiator" else "▲"
            t = self.ax.annotate(
                f"{tipo} {nombre}", info["pos"],
                textcoords="offset points",
                xytext=(10, 8), fontsize=9,
                color='#ff6b6b', fontweight='bold')
            self.anchor_artists[nombre] = {"plot": p, "text": t}

        self.rect_area = patches.Rectangle(
            (0, 0), config["ancho"], config["alto"],
            linewidth=2, edgecolor='#333366',
            facecolor='#1e1e3a', alpha=0.5
        )
        self.ax.add_patch(self.rect_area)

        # Tags
        self.elementos = {}
        for nombre, info in TAGS.items():
            punto, = self.ax.plot(
                [], [], 'o',
                color=info["color"],
                markersize=16, zorder=10,
                label=nombre, picker=12)
            rastro, = self.ax.plot(
                [], [], '-',
                color=info["color_rastro"],
                linewidth=2, alpha=0.5)
            etiqueta = self.ax.text(
                0, 0, nombre,
                fontsize=8, ha='center',
                va='top', color=info["color"], zorder=11)
            self.elementos[nombre] = {
                "punto":    punto,
                "rastro":   rastro,
                "etiqueta": etiqueta,
            }

        self.ax.set_xlim(-0.5, config["ancho"] + 0.5)
        self.ax.set_ylim(-0.5, config["alto"]  + 0.5)
        self.ax.set_xlabel("X (metros)", color='#aaaacc', fontsize=10)
        self.ax.set_ylabel("Y (metros)", color='#aaaacc', fontsize=10)
        self.ax.tick_params(colors='#aaaacc')
        self.ax.grid(True, linestyle='--', alpha=0.2, color='#444466')
        self.ax.legend(loc='upper right', fontsize=9,
                       facecolor='#16213e',
                       labelcolor='white',
                       edgecolor='#333366')
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#333366')

        self.fig.canvas.mpl_connect('pick_event', self._on_pick)

    def _on_pick(self, event):
        for nombre, elem in self.elementos.items():
            if event.artist == elem["punto"]:
                tag_seleccionado["nombre"] = nombre
                if not self.panel_vis:
                    self.panel_vis = True
                    self.frame_mapa.pack(
                        side='left', fill='both',
                        expand=True, padx=(10, 5), pady=10)
                    self.frame_panel.pack(
                        side='right', fill='y',
                        padx=(0, 10), pady=10)
                self._build_panel_info(nombre)

    def _start_animation(self):
        def update(frame):
            # Actualizar anchors
            for nombre, info in ANCHORS.items():
                self.anchor_artists[nombre]["plot"].set_data(
                    [info["pos"][0]], [info["pos"][1]])

            # Actualizar area
            self.rect_area.set_width(config["ancho"])
            self.rect_area.set_height(config["alto"])
            self.ax.set_xlim(-0.5, config["ancho"] + 0.5)
            self.ax.set_ylim(-0.5, config["alto"]  + 0.5)

            for nombre, info in TAGS.items():
                tag  = estado_tags[nombre]
                x, y = tag["x"], tag["y"]

                if not sistema["pausado"]:
                    tag["historial_x"].append(x)
                    tag["historial_y"].append(y)
                    if len(tag["historial_x"]) > 200:
                        tag["historial_x"].pop(0)
                        tag["historial_y"].pop(0)

                elem = self.elementos[nombre]
                elem["punto"].set_data([x], [y])
                elem["etiqueta"].set_position((x, y - 0.15))

                if not tag["conectado"]:
                    elem["punto"].set_color('#555555')
                elif tag["quieto"]:
                    elem["punto"].set_color('#666688')
                else:
                    elem["punto"].set_color(info["color"])

                elem["rastro"].set_data(
                    tag["historial_x"], tag["historial_y"])

            # Actualizar panel info
            sel = tag_seleccionado["nombre"]
            if sel and sel in estado_tags and self.panel_vis:
                tag = estado_tags[sel]
                seg = round(tag["tiempo_quieto"] * 0.1, 1)

                if hasattr(self, 'info_labels'):
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

                    # Mini log
                    log = list(tag["log"])[:8]
                    self.mini_log.configure(state='normal')
                    self.mini_log.delete('1.0', 'end')
                    for linea in log:
                        self.mini_log.insert('end', linea + "\n")
                    self.mini_log.configure(state='disabled')

            titulo = "⏸ PAUSADO" if sistema["pausado"] else "● EN VIVO"
            self.ax.set_title(
                f"Mapa de posicionamiento UWB  —  {titulo}",
                fontsize=11, color='white', fontweight='bold',
                pad=10)

        self.anim = FuncAnimation(
            self.fig, update,
            interval=100, cache_frame_data=False)
        self.after(100, self.canvas_mpl.draw)

# ─── INICIO ──────────────────────────────────────
hilo_ble = threading.Thread(target=iniciar_ble, daemon=True)
hilo_ble.start()

app = AppRTLS()
app.mainloop()