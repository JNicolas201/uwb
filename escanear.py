import asyncio
import threading
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.widgets import Button
from collections import deque
from datetime import datetime
from bleak import BleakClient
from matplotlib.animation import FuncAnimation
import tkinter as tk
from tkinter import ttk, scrolledtext

# ─── CONFIGURACIÓN ───────────────────────────────
TAGS = {
    "DW0214_verde": {
        "mac": "EF:D4:9A:60:7B:08",
        "color": "royalblue",
        "color_rastro": "cornflowerblue",
    },
    "Tag2": {
        "mac": "D7:E4:49:3E:07:FC",
        "color": "red",
        "color_rastro": "lightsalmon",
    },
}

ANCHORS = {
    "DW068E": {"pos": [0.0, 0.0], "tipo": "Slave"},
    "DWD885": {"pos": [0.0, 4.0], "tipo": "Slave"},
    "DW8624": {"pos": [4.0, 0.0], "tipo": "Slave"},
    "DW4CAE": {"pos": [4.0, 4.0], "tipo": "Initiator"},
}

UUID_POS  = "003bbdf2-c634-4b3d-ab56-7ec889b89a37"
UMBRAL    = 0.02
SUAVIZADO = 3
# ─────────────────────────────────────────────────

config           = {"ancho": 4.0, "alto": 4.0}
sistema          = {"pausado": False, "umbral": UMBRAL, "suavizado": SUAVIZADO}
tag_seleccionado = {"nombre": None, "panel_visible": False}

estado_tags = {
    nombre: {
        "x": 2.0, "y": 2.0, "z": 0.0,
        "quieto": True,
        "historial_x": [],
        "historial_y": [],
        "anterior": None,
        "conectado": False,
        "buffer_x": deque(maxlen=SUAVIZADO),
        "buffer_y": deque(maxlen=SUAVIZADO),
        "buffer_z": deque(maxlen=SUAVIZADO),
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

        # Actualizar buffer con suavizado actual
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

        hora = datetime.now().strftime("%H:%M:%S")
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

# ─── VENTANA CONFIGURACIÓN (tkinter) ─────────────
def abrir_configuracion():
    win = tk.Toplevel()
    win.title("Configuracion RTLS")
    win.configure(bg='#1e1e1e')
    win.geometry("600x580")
    win.resizable(False, False)

    style = ttk.Style(win)
    style.theme_use('clam')
    style.configure('TLabel',   background='#1e1e1e', foreground='white', font=('Arial', 10))
    style.configure('TEntry',   fieldbackground='#3a3a3a', foreground='white', font=('Arial', 10))
    style.configure('TButton',  background='#006600', foreground='white', font=('Arial', 10, 'bold'))
    style.configure('Header.TLabel', background='#1e1e1e', foreground='#ff6b6b',
                    font=('Arial', 12, 'bold'))
    style.configure('Sub.TLabel', background='#1e1e1e', foreground='#aaffaa',
                    font=('Arial', 11, 'bold'))

    # ── Título ──
    ttk.Label(win, text="CONFIGURACION RTLS", style='Header.TLabel').grid(
        row=0, column=0, columnspan=4, pady=(12, 4), padx=15, sticky='w')

    ttk.Separator(win, orient='horizontal').grid(
        row=1, column=0, columnspan=4, sticky='ew', padx=10)

    # ── Anchors ──
    ttk.Label(win, text="ANCHORS", style='Sub.TLabel').grid(
        row=2, column=0, columnspan=4, pady=(8, 2), padx=15, sticky='w')

    ttk.Label(win, text="Nombre",    foreground='#aaaaaa').grid(row=3, column=0, padx=15)
    ttk.Label(win, text="Tipo",      foreground='#aaaaaa').grid(row=3, column=1, padx=5)
    ttk.Label(win, text="X (m)",     foreground='#aaaaaa').grid(row=3, column=2, padx=5)
    ttk.Label(win, text="Y (m)",     foreground='#aaaaaa').grid(row=3, column=3, padx=5)

    anchor_entries = {}
    tipos_var      = {}
    for i, (nombre, info) in enumerate(ANCHORS.items()):
        r = i + 4
        color = '#ffcc00' if info["tipo"] == "Initiator" else 'white'
        ttk.Label(win, text=nombre, foreground=color,
                  font=('Arial', 10, 'bold')).grid(row=r, column=0, padx=15, pady=3)

        tipo_var = tk.StringVar(value=info["tipo"])
        tipos_var[nombre] = tipo_var
        tipo_menu = ttk.Combobox(win, textvariable=tipo_var,
                                  values=["Slave", "Initiator"],
                                  width=10, state='readonly')
        tipo_menu.grid(row=r, column=1, padx=5, pady=3)

        ex = ttk.Entry(win, width=8)
        ex.insert(0, str(info["pos"][0]))
        ex.grid(row=r, column=2, padx=5, pady=3)

        ey = ttk.Entry(win, width=8)
        ey.insert(0, str(info["pos"][1]))
        ey.grid(row=r, column=3, padx=5, pady=3)

        anchor_entries[nombre] = {"ex": ex, "ey": ey}

    ttk.Separator(win, orient='horizontal').grid(
        row=9, column=0, columnspan=4, sticky='ew', padx=10, pady=6)

    # ── Parámetros ──
    ttk.Label(win, text="PARAMETROS", style='Sub.TLabel').grid(
        row=10, column=0, columnspan=4, pady=(4, 4), padx=15, sticky='w')

    ttk.Label(win, text="Ancho area (m):").grid(row=11, column=0, padx=15, sticky='w', pady=3)
    e_ancho = ttk.Entry(win, width=10)
    e_ancho.insert(0, str(config["ancho"]))
    e_ancho.grid(row=11, column=1, padx=5, pady=3, sticky='w')

    ttk.Label(win, text="Alto area (m):").grid(row=12, column=0, padx=15, sticky='w', pady=3)
    e_alto = ttk.Entry(win, width=10)
    e_alto.insert(0, str(config["alto"]))
    e_alto.grid(row=12, column=1, padx=5, pady=3, sticky='w')

    ttk.Label(win, text="Umbral movimiento (m):").grid(row=13, column=0, padx=15, sticky='w', pady=3)
    e_umb = ttk.Entry(win, width=10)
    e_umb.insert(0, str(sistema["umbral"]))
    e_umb.grid(row=13, column=1, padx=5, pady=3, sticky='w')

    ttk.Label(win, text="Suavizado (lecturas):").grid(row=14, column=0, padx=15, sticky='w', pady=3)
    e_suav = ttk.Entry(win, width=10)
    e_suav.insert(0, str(sistema["suavizado"]))
    e_suav.grid(row=14, column=1, padx=5, pady=3, sticky='w')

    ttk.Separator(win, orient='horizontal').grid(
        row=15, column=0, columnspan=4, sticky='ew', padx=10, pady=6)

    # ── Tags info ──
    ttk.Label(win, text="TAGS", style='Sub.TLabel').grid(
        row=16, column=0, columnspan=4, pady=(4, 4), padx=15, sticky='w')

    for i, (nombre, info) in enumerate(TAGS.items()):
        ttk.Label(win, text=f"{nombre}   MAC: {info['mac']}",
                  foreground=info["color"],
                  font=('Arial', 9)).grid(
            row=17 + i, column=0, columnspan=4,
            padx=15, sticky='w', pady=2)

    # Mensaje estado
    msg = tk.StringVar(value="")
    ttk.Label(win, textvariable=msg,
              foreground='#00ff88').grid(
        row=20, column=0, columnspan=4, padx=15, pady=4)

    # ── Botón guardar ──
    def guardar():
        try:
            for nombre, entries in anchor_entries.items():
                ANCHORS[nombre]["pos"][0] = float(entries["ex"].get())
                ANCHORS[nombre]["pos"][1] = float(entries["ey"].get())
                ANCHORS[nombre]["tipo"]   = tipos_var[nombre].get()

            config["ancho"]       = float(e_ancho.get())
            config["alto"]        = float(e_alto.get())
            sistema["umbral"]     = float(e_umb.get())
            sistema["suavizado"]  = int(e_suav.get())

            msg.set("✓ Configuracion guardada correctamente")
            win.after(3000, lambda: msg.set(""))
            print("✓ Configuracion guardada")
        except Exception as e:
            msg.set(f"Error: {e}")

    tk.Button(win, text="GUARDAR CAMBIOS",
              bg='#006600', fg='white',
              font=('Arial', 11, 'bold'),
              relief='flat', padx=10, pady=6,
              command=guardar).grid(
        row=21, column=0, columnspan=4, pady=12)

# ─── MAPA PRINCIPAL ──────────────────────────────
def mostrar_mapa():
    fig = plt.figure(figsize=(15, 8))
    fig.patch.set_facecolor('#1e1e1e')
    fig.canvas.manager.set_window_title("System RTLS")

    # Barra superior
    ax_top = fig.add_axes([0.0, 0.93, 1.0, 0.07])
    ax_top.set_facecolor('#8b0000')
    ax_top.axis('off')
    ax_top.text(0.01, 0.5, "System RTLS",
                transform=ax_top.transAxes,
                fontsize=15, color='white',
                fontweight='bold', va='center')
    ax_top.text(0.22, 0.5,
                f"Anchors: {len(ANCHORS)}   |   Tags: {len(TAGS)}",
                transform=ax_top.transAxes,
                fontsize=11, color='#ffcccc', va='center')

    ax_btn_pausa = fig.add_axes([0.60, 0.935, 0.09, 0.055])
    btn_pausa = Button(ax_btn_pausa, 'DETENER',
                       color='#cc0000', hovercolor='#ff3333')
    btn_pausa.label.set_color('white')
    btn_pausa.label.set_fontweight('bold')

    ax_btn_cfg = fig.add_axes([0.71, 0.935, 0.11, 0.055])
    btn_cfg = Button(ax_btn_cfg, 'CONFIGURACION',
                     color='#333333', hovercolor='#555555')
    btn_cfg.label.set_color('white')
    btn_cfg.label.set_fontweight('bold')

    def toggle_pausa(event):
        sistema["pausado"] = not sistema["pausado"]
        if sistema["pausado"]:
            btn_pausa.label.set_text('INICIAR')
            btn_pausa.ax.set_facecolor('#006600')
        else:
            btn_pausa.label.set_text('DETENER')
            btn_pausa.ax.set_facecolor('#cc0000')
        fig.canvas.draw_idle()

    btn_pausa.on_clicked(toggle_pausa)
    btn_cfg.on_clicked(lambda e: abrir_configuracion())

    # Mapa grande por defecto
    ax = fig.add_axes([0.01, 0.02, 0.97, 0.89])
    ax.set_facecolor('#2d2d2d')

    # Panel derecho oculto
    ax_panel = fig.add_axes([0.53, 0.02, 0.45, 0.89])
    ax_panel.set_facecolor('#2d2d2d')
    ax_panel.axis('off')
    ax_panel.set_visible(False)

    plt.ion()

    # Anchors
    anchor_artists = {}
    for nombre, info in ANCHORS.items():
        p, = ax.plot(info["pos"][0], info["pos"][1],
                     's', color='darkred', markersize=14, zorder=5)
        tipo = "★" if info["tipo"] == "Initiator" else "▲"
        t = ax.annotate(f"{tipo} {nombre}", info["pos"],
                        textcoords="offset points",
                        xytext=(10, 8), fontsize=9,
                        color='#ff6b6b', fontweight='bold')
        anchor_artists[nombre] = {"plot": p, "text": t}

    rect_area = patches.Rectangle(
        (0, 0), config["ancho"], config["alto"],
        linewidth=2, edgecolor='#555555',
        facecolor='#3a3a3a', alpha=0.4
    )
    ax.add_patch(rect_area)

    # Tags
    elementos = {}
    for nombre, info in TAGS.items():
        punto, = ax.plot([], [], 'o',
                         color=info["color"],
                         markersize=16, zorder=10,
                         label=nombre, picker=12)
        rastro, = ax.plot([], [], '-',
                          color=info["color_rastro"],
                          linewidth=2, alpha=0.5)
        etiqueta = ax.text(0, 0, nombre,
                           fontsize=8, ha='center',
                           va='top', color=info["color"], zorder=11)
        elementos[nombre] = {
            "punto":    punto,
            "rastro":   rastro,
            "etiqueta": etiqueta,
        }

    ax.set_xlim(-0.5, config["ancho"] + 0.5)
    ax.set_ylim(-0.5, config["alto"]  + 0.5)
    ax.set_xlabel("X (metros)", fontsize=10, color='white')
    ax.set_ylabel("Y (metros)", fontsize=10, color='white')
    ax.tick_params(colors='white')
    ax.grid(True, linestyle='--', alpha=0.3, color='#555555')
    ax.legend(loc='upper right', fontsize=9,
              facecolor='#3a3a3a', labelcolor='white')
    for spine in ax.spines.values():
        spine.set_edgecolor('#555555')

    # Panel info
    ax_panel.text(0.04, 0.97, "INFO DEL TAG",
                  transform=ax_panel.transAxes,
                  fontsize=12, color='white', fontweight='bold')
    ax_panel.plot([0.04, 0.96], [0.93, 0.93],
                  color='#555555', linewidth=1,
                  transform=ax_panel.transAxes)

    campos = ["nombre", "estado", "x", "y", "z",
              "velocidad", "quieto", "conexion"]
    labels = ["Tag:", "Estado:", "X:", "Y:", "Z:",
              "Velocidad:", "Quieto hace:", "Conexion:"]

    textos_info = {}
    y_i = 0.88
    for campo, label in zip(campos, labels):
        ax_panel.text(0.04, y_i, label,
                      transform=ax_panel.transAxes,
                      fontsize=9, color='#aaaaaa')
        tv = ax_panel.text(0.40, y_i, "---",
                           transform=ax_panel.transAxes,
                           fontsize=9, color='white', fontweight='bold')
        textos_info[campo] = tv
        y_i -= 0.075

    ax_panel.plot([0.04, 0.96], [0.28, 0.28],
                  color='#555555', linewidth=1,
                  transform=ax_panel.transAxes)
    ax_panel.text(0.04, 0.25, "HISTORIAL DE POSICIONES",
                  transform=ax_panel.transAxes,
                  fontsize=10, color='white', fontweight='bold')

    # Log scrolleable con tkinter dentro del panel
    log_widget = {"ref": None, "activo": False}

    # Botón cerrar
    ax_btn_cerrar = fig.add_axes([0.84, 0.935, 0.07, 0.045])
    btn_cerrar = Button(ax_btn_cerrar, 'X  Cerrar',
                        color='#555555', hovercolor='#777777')
    btn_cerrar.label.set_color('white')
    btn_cerrar.ax.set_visible(False)

    # Ventana tkinter para el log
    log_win = {"ref": None}

    def abrir_log_win(nombre_tag):
        if log_win["ref"] and tk.Toplevel.winfo_exists(log_win["ref"]):
            log_win["ref"].destroy()

        win_log = tk.Toplevel()
        win_log.title(f"Historial - {nombre_tag}")
        win_log.configure(bg='#1e1e1e')
        win_log.geometry("480x500")
        log_win["ref"] = win_log

        tk.Label(win_log,
                 text=f"Historial completo: {nombre_tag}",
                 bg='#1e1e1e', fg='white',
                 font=('Arial', 12, 'bold')).pack(pady=8)

        text_area = scrolledtext.ScrolledText(
            win_log,
            bg='#1a1a1a', fg='#00ff88',
            font=('Courier', 9),
            wrap=tk.NONE,
            width=58, height=28
        )
        text_area.pack(padx=10, pady=5, fill='both', expand=True)

        def actualizar_log():
            if not win_log.winfo_exists():
                return
            tag = estado_tags[nombre_tag]
            log = list(tag["log"])
            text_area.config(state='normal')
            text_area.delete('1.0', tk.END)
            for linea in log:
                text_area.insert(tk.END, linea + "\n")
            text_area.config(state='disabled')
            win_log.after(500, actualizar_log)

        actualizar_log()

        tk.Button(win_log,
                  text="Exportar CSV",
                  bg='#006600', fg='white',
                  font=('Arial', 10, 'bold'),
                  relief='flat', padx=8, pady=4,
                  command=lambda: exportar_csv(nombre_tag)
                  ).pack(pady=8)

    def exportar_csv(nombre_tag):
        from datetime import datetime as dt
        fname = f"log_{nombre_tag}_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(fname, 'w') as f:
            f.write("Hora,Estado,X,Y,Z,Velocidad\n")
            for linea in estado_tags[nombre_tag]["log"]:
                f.write(linea.replace(" | ", ",").replace(
                    "X:", "").replace("Y:", "").replace(
                    "Z:", "").replace("m/s", "") + "\n")
        print(f"✓ Exportado: {fname}")

    def cerrar_panel(event):
        tag_seleccionado["nombre"]        = None
        tag_seleccionado["panel_visible"] = False
        ax.set_position([0.01, 0.02, 0.97, 0.89])
        ax_panel.set_visible(False)
        btn_cerrar.ax.set_visible(False)
        if log_win["ref"] and tk.Toplevel.winfo_exists(log_win["ref"]):
            log_win["ref"].destroy()
        fig.canvas.draw_idle()

    btn_cerrar.on_clicked(cerrar_panel)

    def on_pick(event):
        for nombre, elem in elementos.items():
            if event.artist == elem["punto"]:
                tag_seleccionado["nombre"]        = nombre
                tag_seleccionado["panel_visible"] = True
                ax.set_position([0.01, 0.02, 0.50, 0.89])
                ax_panel.set_visible(True)
                btn_cerrar.ax.set_visible(True)
                abrir_log_win(nombre)
                fig.canvas.draw_idle()

    fig.canvas.mpl_connect('pick_event', on_pick)

    # ── Update ────────────────────────────────────
    def update(frame):
        for nombre, info in ANCHORS.items():
            anchor_artists[nombre]["plot"].set_data(
                [info["pos"][0]], [info["pos"][1]]
            )

        rect_area.set_width(config["ancho"])
        rect_area.set_height(config["alto"])
        ax.set_xlim(-0.5, config["ancho"] + 0.5)
        ax.set_ylim(-0.5, config["alto"]  + 0.5)

        for nombre, info in TAGS.items():
            tag  = estado_tags[nombre]
            x, y = tag["x"], tag["y"]

            if not sistema["pausado"]:
                tag["historial_x"].append(x)
                tag["historial_y"].append(y)
                if len(tag["historial_x"]) > 150:
                    tag["historial_x"].pop(0)
                    tag["historial_y"].pop(0)

            elem = elementos[nombre]
            elem["punto"].set_data([x], [y])
            elem["etiqueta"].set_position((x, y - 0.15))

            if not tag["conectado"]:
                elem["punto"].set_color('gray')
            elif tag["quieto"]:
                elem["punto"].set_color('#888888')
            else:
                elem["punto"].set_color(info["color"])

            elem["rastro"].set_data(
                tag["historial_x"], tag["historial_y"]
            )

        sel = tag_seleccionado["nombre"]
        if sel and sel in estado_tags:
            tag = estado_tags[sel]
            seg = round(tag["tiempo_quieto"] * 0.1, 1)
            textos_info["nombre"].set_text(sel)
            textos_info["estado"].set_text(
                "QUIETO" if tag["quieto"] else "MOVIENDO"
            )
            textos_info["estado"].set_color(
                "#ff6b6b" if tag["quieto"] else "#6bff6b"
            )
            textos_info["x"].set_text(f"{tag['x']:.3f} m")
            textos_info["y"].set_text(f"{tag['y']:.3f} m")
            textos_info["z"].set_text(f"{tag['z']:.3f} m")
            textos_info["velocidad"].set_text(
                f"{tag['velocidad']:.2f} m/s"
            )
            textos_info["quieto"].set_text(f"{seg} seg")
            textos_info["conexion"].set_text(
                "CONECTADO" if tag["conectado"] else "SIN CONEXION"
            )
            textos_info["conexion"].set_color(
                "#6bff6b" if tag["conectado"] else "#ff6b6b"
            )

        titulo = "PAUSADO" if sistema["pausado"] else "EN VIVO"
        ax.set_title(f"Mapa de posicionamiento UWB  [{titulo}]",
                     fontsize=11, color='white', fontweight='bold')

    anim = FuncAnimation(fig, update, interval=100,
                         cache_frame_data=False)
    plt.show(block=True)

# ─── INICIO ──────────────────────────────────────
hilo_ble = threading.Thread(target=iniciar_ble, daemon=True)
hilo_ble.start()

# Iniciar tkinter root oculto
root = tk.Tk()
root.withdraw()

mostrar_mapa()