import customtkinter as ctk
from config import TAGS, ANCHORS, SISTEMA, CONFIG_AREA

def abrir_configuracion(root):
    win = ctk.CTkToplevel(root)
    win.title("Configuracion RTLS")
    win.geometry("620x660")
    win.resizable(False, False)
    win.configure(fg_color="#1a1a2e")

    ctk.CTkLabel(win, text="⚙  CONFIGURACION RTLS",
                 font=ctk.CTkFont(size=18, weight="bold"),
                 text_color="#e94560").pack(
        pady=(16, 4), padx=20, anchor='w')

    ctk.CTkFrame(win, height=2, fg_color="#333355").pack(
        fill='x', padx=20, pady=(0, 10))

    scroll = ctk.CTkScrollableFrame(win, fg_color="#16213e",
                                     corner_radius=10)
    scroll.pack(fill='both', expand=True, padx=16, pady=(0, 10))

    # ── Anchors ──
    ctk.CTkLabel(scroll, text="ANCHORS",
                 font=ctk.CTkFont(size=14, weight="bold"),
                 text_color="#e94560").pack(
        anchor='w', pady=(10, 4), padx=10)

    anchor_entries = {}
    tipos_var      = {}

    for nombre, info in ANCHORS.items():
        frame = ctk.CTkFrame(scroll, fg_color="#0f3460", corner_radius=8)
        frame.pack(fill='x', padx=10, pady=4)

        color = "#ffcc00" if info["tipo"] == "Initiator" else "#aaaaff"
        ctk.CTkLabel(frame, text=nombre,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=color, width=80).grid(
            row=0, column=0, padx=12, pady=8, sticky='w')

        tipo_var = ctk.StringVar(value=info["tipo"])
        tipos_var[nombre] = tipo_var
        ctk.CTkOptionMenu(frame, variable=tipo_var,
                          values=["Slave", "Initiator"],
                          width=110,
                          fg_color="#1a1a2e",
                          button_color="#e94560",
                          button_hover_color="#c73652").grid(
            row=0, column=1, padx=8, pady=8)

        ctk.CTkLabel(frame, text="X:",
                     text_color="#aaaaaa").grid(
            row=0, column=2, padx=(12, 2))
        ex = ctk.CTkEntry(frame, width=70,
                          fg_color="#1a1a2e",
                          border_color="#333355")
        ex.insert(0, str(info["pos"][0]))
        ex.grid(row=0, column=3, padx=4, pady=8)

        ctk.CTkLabel(frame, text="Y:",
                     text_color="#aaaaaa").grid(
            row=0, column=4, padx=(8, 2))
        ey = ctk.CTkEntry(frame, width=70,
                          fg_color="#1a1a2e",
                          border_color="#333355")
        ey.insert(0, str(info["pos"][1]))
        ey.grid(row=0, column=5, padx=(4, 12), pady=8)

        anchor_entries[nombre] = {"ex": ex, "ey": ey}

    # ── Parámetros ──
    ctk.CTkFrame(scroll, height=2, fg_color="#333355").pack(
        fill='x', padx=10, pady=(12, 4))
    ctk.CTkLabel(scroll, text="PARAMETROS",
                 font=ctk.CTkFont(size=14, weight="bold"),
                 text_color="#00d4aa").pack(
        anchor='w', pady=(4, 6), padx=10)

    pf = ctk.CTkFrame(scroll, fg_color="#0f3460", corner_radius=8)
    pf.pack(fill='x', padx=10, pady=4)

    params = [
        ("Ancho area (m):",        str(CONFIG_AREA["ancho"])),
        ("Alto area (m):",         str(CONFIG_AREA["alto"])),
        ("Umbral movimiento (m):", str(SISTEMA["umbral"])),
        ("Suavizado (lecturas):",  str(SISTEMA["suavizado"])),
    ]
    param_entries = []
    for i, (label, val) in enumerate(params):
        ctk.CTkLabel(pf, text=label,
                     text_color="#aaaaaa",
                     font=ctk.CTkFont(size=11)).grid(
            row=i, column=0, padx=12, pady=6, sticky='w')
        e = ctk.CTkEntry(pf, width=100,
                         fg_color="#1a1a2e",
                         border_color="#333355")
        e.insert(0, val)
        e.grid(row=i, column=1, padx=12, pady=6, sticky='w')
        param_entries.append(e)

    # ── Tags ──
    ctk.CTkFrame(scroll, height=2, fg_color="#333355").pack(
        fill='x', padx=10, pady=(12, 4))
    ctk.CTkLabel(scroll, text="TAGS",
                 font=ctk.CTkFont(size=14, weight="bold"),
                 text_color="#4169e1").pack(
        anchor='w', pady=(4, 6), padx=10)

    for nombre, info in TAGS.items():
        tf = ctk.CTkFrame(scroll, fg_color="#0f3460", corner_radius=8)
        tf.pack(fill='x', padx=10, pady=4)
        ctk.CTkLabel(tf, text=f"  {nombre}",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=info["ctk_color"]).grid(
            row=0, column=0, padx=12, pady=8, sticky='w')
        ctk.CTkLabel(tf, text=f"MAC: {info['mac']}",
                     text_color="#888888",
                     font=ctk.CTkFont(size=10)).grid(
            row=0, column=1, padx=12, pady=8, sticky='w')

    # Mensaje
    msg_var = ctk.StringVar(value="")
    ctk.CTkLabel(win, textvariable=msg_var,
                 text_color="#00ff88",
                 font=ctk.CTkFont(size=11)).pack(pady=4)

    def guardar():
        try:
            for nombre, entries in anchor_entries.items():
                ANCHORS[nombre]["pos"][0] = float(entries["ex"].get())
                ANCHORS[nombre]["pos"][1] = float(entries["ey"].get())
                ANCHORS[nombre]["tipo"]   = tipos_var[nombre].get()
            CONFIG_AREA["ancho"]  = float(param_entries[0].get())
            CONFIG_AREA["alto"]   = float(param_entries[1].get())
            SISTEMA["umbral"]     = float(param_entries[2].get())
            SISTEMA["suavizado"]  = int(param_entries[3].get())
            msg_var.set("✓ Configuracion guardada")
            win.after(3000, lambda: msg_var.set(""))
        except Exception as e:
            msg_var.set(f"Error: {e}")

    ctk.CTkButton(win, text="  GUARDAR CAMBIOS",
                  font=ctk.CTkFont(size=13, weight="bold"),
                  fg_color="#006633", hover_color="#009944",
                  height=40, corner_radius=8,
                  command=guardar).pack(
        fill='x', padx=20, pady=(0, 16))