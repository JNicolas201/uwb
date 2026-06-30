import customtkinter as ctk
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
from config import TAGS, ANCHORS, SISTEMA, CONFIG_AREA
from estado import estado_tags, tag_seleccionado
from ui.panel import PanelInfo
from ui.config_win import abrir_configuracion

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class AppRTLS(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("System RTLS")
        self.geometry("1280x780")
        self.configure(fg_color="#1a1a2e")
        self.resizable(True, True)
        self.panel_vis = False
        self._build_topbar()
        self._build_main()
        self._build_mapa()
        self._start_animation()

    # ── Barra superior ────────────────────────────
    def _build_topbar(self):
        top = ctk.CTkFrame(self, height=56,
                           fg_color="#16213e", corner_radius=0)
        top.pack(fill='x', side='top')
        top.pack_propagate(False)

        ctk.CTkLabel(top, text="⬡  System RTLS",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#e94560").pack(
            side='left', padx=20, pady=10)

        ctk.CTkFrame(top, width=2,
                     fg_color="#333355").pack(
            side='left', fill='y', padx=8, pady=8)

        ctk.CTkLabel(top, text=f"Anchors: {len(ANCHORS)}",
                     font=ctk.CTkFont(size=12),
                     text_color="#aaaacc").pack(
            side='left', padx=12)

        ctk.CTkLabel(top, text=f"Tags: {len(TAGS)}",
                     font=ctk.CTkFont(size=12),
                     text_color="#aaaacc").pack(
            side='left', padx=4)

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

    # ── Layout principal ──────────────────────────
    def _build_main(self):
        self.main = ctk.CTkFrame(self, fg_color="#1a1a2e",
                                  corner_radius=0)
        self.main.pack(fill='both', expand=True)

        self.frame_mapa = ctk.CTkFrame(
            self.main, fg_color="#12122a", corner_radius=10)
        self.frame_mapa.pack(side='left', fill='both',
                              expand=True, padx=(10, 5), pady=10)

        self.panel = PanelInfo(
            self.main,
            on_cerrar=self._cerrar_panel,
            width=320)

    # ── Mapa matplotlib ───────────────────────────
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
            (0, 0), CONFIG_AREA["ancho"], CONFIG_AREA["alto"],
            linewidth=2, edgecolor='#333366',
            facecolor='#1e1e3a', alpha=0.5)
        self.ax.add_patch(self.rect_area)

        # Tags
        self.elementos = {}
        for nombre, info in TAGS.items():
            punto, = self.ax.plot(
                [], [], 'o', color=info["color"],
                markersize=16, zorder=10,
                label=nombre, picker=12)
            rastro, = self.ax.plot(
                [], [], '-', color=info["color_rastro"],
                linewidth=2, alpha=0.5)
            etiqueta = self.ax.text(
                0, 0, nombre, fontsize=8,
                ha='center', va='top',
                color=info["color"], zorder=11)
            self.elementos[nombre] = {
                "punto":    punto,
                "rastro":   rastro,
                "etiqueta": etiqueta,
            }

        self.ax.set_xlim(-0.5, CONFIG_AREA["ancho"] + 0.5)
        self.ax.set_ylim(-0.5, CONFIG_AREA["alto"]  + 0.5)
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

    # ── Eventos ───────────────────────────────────
    def _on_pick(self, event):
        for nombre, elem in self.elementos.items():
            if event.artist == elem["punto"]:
                tag_seleccionado["nombre"] = nombre
                if not self.panel_vis:
                    self.panel_vis = True
                    self.panel.pack(side='right', fill='y',
                                    padx=(0, 10), pady=10)
                self.panel.mostrar(nombre)

    def _cerrar_panel(self):
        tag_seleccionado["nombre"] = None
        self.panel_vis = False
        self.panel.pack_forget()

    def _toggle_pausa(self):
        SISTEMA["pausado"] = not SISTEMA["pausado"]
        if SISTEMA["pausado"]:
            self.btn_pausa.configure(
                text="▶  Iniciar",
                fg_color="#006633",
                hover_color="#009944")
        else:
            self.btn_pausa.configure(
                text="⏸  Detener",
                fg_color="#8b0000",
                hover_color="#cc0000")

    # ── Animación ─────────────────────────────────
    def _start_animation(self):
        def update(frame):
            # Anchors
            for nombre, info in ANCHORS.items():
                self.anchor_artists[nombre]["plot"].set_data(
                    [info["pos"][0]], [info["pos"][1]])

            # Area
            self.rect_area.set_width(CONFIG_AREA["ancho"])
            self.rect_area.set_height(CONFIG_AREA["alto"])
            self.ax.set_xlim(-0.5, CONFIG_AREA["ancho"] + 0.5)
            self.ax.set_ylim(-0.5, CONFIG_AREA["alto"]  + 0.5)

            # Tags
            for nombre, info in TAGS.items():
                    tag  = estado_tags[nombre]
                    x, y = tag["x"], tag["y"]

                    # Interpolación suave
                    elem = self.elementos[nombre]
                    x_actual = elem.get("x_vis", x)
                    y_actual = elem.get("y_vis", y)
                    x_vis = x_actual + (x - x_actual) * 0.3
                    y_vis = y_actual + (y - y_actual) * 0.3
                    elem["x_vis"] = x_vis
                    elem["y_vis"] = y_vis

                    if not SISTEMA["pausado"]:
                        tag["historial_x"].append(x_vis)
                        tag["historial_y"].append(y_vis)
                        if len(tag["historial_x"]) > 200:
                            tag["historial_x"].pop(0)
                            tag["historial_y"].pop(0)

                    elem["punto"].set_data([x_vis], [y_vis])
                    elem["etiqueta"].set_position((x_vis, y_vis - 0.15))

                    if not tag["conectado"]:
                        elem["punto"].set_color('#555555')
                    elif tag["quieto"]:
                        elem["punto"].set_color('#666688')
                    else:
                        elem["punto"].set_color(info["color"])

                    elem["rastro"].set_data(
                        tag["historial_x"], tag["historial_y"])

            # Panel info
            if self.panel_vis:
                self.panel.actualizar()

            titulo = "⏸ PAUSADO" if SISTEMA["pausado"] else "● EN VIVO"
            self.ax.set_title(
                f"Mapa de posicionamiento UWB  —  {titulo}",
                fontsize=11, color='white',
                fontweight='bold', pad=10)

        self.anim = FuncAnimation(
            self.fig, update,
            interval=50, cache_frame_data=False)
        self.after(50, self.canvas_mpl.draw)