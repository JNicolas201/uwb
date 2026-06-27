import asyncio
import threading
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from collections import deque
from bleak import BleakClient

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
    "DW068E": (0.0, 0.0),
    "DWD885": (0.0, 4.0),
    "DW8624": (4.0, 0.0),
    "DW4CAE": (4.0, 4.0),  # ahora en la esquina
}

UUID_POS  = "003bbdf2-c634-4b3d-ab56-7ec889b89a37"
UMBRAL    = 0.05
SUAVIZADO = 5  # aumenta para más suavidad (3-10)
# ─────────────────────────────────────────────────

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
    }
    for nombre in TAGS
}

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
        resultado = decodificar(data)
        if resultado is None:
            return
        x, y, z, q = resultado
        if q == 0:
            return
        if not (0 <= x <= 10 and 0 <= y <= 10 and 0 <= z <= 5):
            return

        tag = estado_tags[nombre]

        # Filtro de suavizado
        tag["buffer_x"].append(x)
        tag["buffer_y"].append(y)
        tag["buffer_z"].append(z)
        x_suave = sum(tag["buffer_x"]) / len(tag["buffer_x"])
        y_suave = sum(tag["buffer_y"]) / len(tag["buffer_y"])
        z_suave = sum(tag["buffer_z"]) / len(tag["buffer_z"])

        # Detectar movimiento
        if tag["anterior"]:
            dist = ((x_suave - tag["anterior"][0])**2 +
                    (y_suave - tag["anterior"][1])**2)**0.5
            tag["quieto"] = dist < UMBRAL
        else:
            tag["quieto"] = False

        tag["x"] = x_suave
        tag["y"] = y_suave
        tag["z"] = z_suave
        tag["anterior"] = (x_suave, y_suave, z_suave)

        estado = "[QUIETO]" if tag["quieto"] else "[MOVIENDO]"
        print(f"{nombre} {estado} -> X:{x_suave:.3f}m  Y:{y_suave:.3f}m  Z:{z_suave:.3f}m")

    return callback

async def conectar_tag(nombre, mac):
    print(f"Conectando a {nombre} ({mac})...")
    while True:
        try:
            async with BleakClient(mac, timeout=30.0) as client:
                estado_tags[nombre]["conectado"] = True
                print(f"✓ {nombre} conectado!")
                await client.start_notify(UUID_POS, hacer_callback(nombre))
                await asyncio.sleep(9999)
        except Exception as e:
            estado_tags[nombre]["conectado"] = False
            print(f"✗ {nombre} desconectado: {e} - Reconectando en 5s...")
            await asyncio.sleep(5)

async def ble_loop():
    await asyncio.gather(*[
        conectar_tag(nombre, info["mac"])
        for nombre, info in TAGS.items()
    ])

def iniciar_ble():
    asyncio.run(ble_loop())

def mostrar_mapa():
    fig, ax = plt.subplots(figsize=(8, 8))
    plt.ion()

    # Dibujar anchors
    for nombre, (ax_x, ax_y) in ANCHORS.items():
        ax.plot(ax_x, ax_y, 's', color='darkred', markersize=16, zorder=5)
        ax.annotate(nombre, (ax_x, ax_y),
                    textcoords="offset points",
                    xytext=(10, 8), fontsize=10,
                    color='darkred', fontweight='bold')

    # Area del espacio
    rect = patches.Rectangle((0, 0), 4, 4,
                               linewidth=2, edgecolor='gray',
                               facecolor='lightyellow', alpha=0.3)
    ax.add_patch(rect)

    # Crear punto y rastro para cada tag
    elementos = {}
    for nombre, info in TAGS.items():
        punto, = ax.plot([], [], 'o',
                         color=info["color"],
                         markersize=16, zorder=10,
                         label=nombre)
        rastro, = ax.plot([], [], '-',
                          color=info["color_rastro"],
                          linewidth=1.5, alpha=0.6)
        elementos[nombre] = {"punto": punto, "rastro": rastro}

    ax.set_xlim(-0.5, 5.0)
    ax.set_ylim(-0.5, 5.0)
    ax.set_xlabel("X (metros)", fontsize=11)
    ax.set_ylabel("Y (metros)", fontsize=11)
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.legend(loc='upper right', fontsize=10)

    while plt.fignum_exists(fig.number):
        titulo = ""

        for nombre, info in TAGS.items():
            tag = estado_tags[nombre]
            x = tag["x"]
            y = tag["y"]
            z = tag["z"]
            quieto   = tag["quieto"]
            conectado = tag["conectado"]

            tag["historial_x"].append(x)
            tag["historial_y"].append(y)

            if len(tag["historial_x"]) > 150:
                tag["historial_x"].pop(0)
                tag["historial_y"].pop(0)

            elem = elementos[nombre]
            elem["punto"].set_data([x], [y])

            if not conectado:
                elem["punto"].set_color('gray')
            elif quieto:
                elem["punto"].set_color('lightgray')
            else:
                elem["punto"].set_color(info["color"])

            elem["rastro"].set_data(tag["historial_x"], tag["historial_y"])

            estado = "QUIETO" if quieto else "MOV"
            con    = "OK" if conectado else "SIN CONEXION"
            titulo += f"{nombre}: X:{x:.2f} Y:{y:.2f} Z:{z:.2f} [{estado}][{con}]\n"

        ax.set_title(titulo.strip(), fontsize=10, fontweight='bold')
        plt.pause(0.1)

    plt.ioff()
    plt.show()

# ─── INICIO ──────────────────────────────────────
hilo_ble = threading.Thread(target=iniciar_ble, daemon=True)
hilo_ble.start()

mostrar_mapa()