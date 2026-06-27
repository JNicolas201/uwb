import asyncio
import threading
import matplotlib.pyplot as plt
from bleak import BleakClient

# ─── CONFIGURACIÓN ───────────────────────────────
MAC = "EF:D4:9A:60:7B:08"
UUID_POS = "680c21d9-c946-4c1f-9c11-baa1c21329e7"
UMBRAL = 0.05

ANCHORS = {
    "DW068E":  (0.0, 0.0),
    "DWD885":  (0.0, 4.0),
    "DW8624":  (4.0, 0.0),
}
# ─────────────────────────────────────────────────

pos_actual = {"x": 2.0, "y": 2.0, "quieto": True}
pos_anterior = None

def callback(sender, data):
    global pos_anterior
    if len(data) < 13:
        return

    x = int.from_bytes(data[0:4], 'little') / 1000
    y = int.from_bytes(data[4:8], 'little') / 1000
    z = int.from_bytes(data[8:12], 'little') / 1000

    if pos_anterior:
        dist = ((x - pos_anterior[0])**2 + (y - pos_anterior[1])**2)**0.5
        pos_actual["quieto"] = dist < UMBRAL

    pos_actual["x"] = x
    pos_actual["y"] = y
    pos_anterior = (x, y, z)

    estado = "🔴 QUIETO" if pos_actual["quieto"] else "🟢 MOVIENDO"
    print(f"{estado} → X:{x:.3f}m  Y:{y:.3f}m  Z:{z:.3f}m")

async def ble_loop():
    print("Conectando al tag...")
    while True:
        try:
            async with BleakClient(MAC) as client:
                print("✓ Conectado!")
                await client.start_notify(UUID_POS, callback)
                await asyncio.sleep(9999)
        except Exception as e:
            print(f"⚠ Desconectado: {e} — Reconectando en 3s...")
            await asyncio.sleep(3)

def iniciar_ble():
    asyncio.run(ble_loop())

def mostrar_mapa():
    fig, ax = plt.subplots(figsize=(6, 6))
    plt.ion()

    for nombre, (ax_x, ax_y) in ANCHORS.items():
        ax.plot(ax_x, ax_y, 's', color='darkred', markersize=14)
        ax.annotate(nombre, (ax_x, ax_y),
                    textcoords="offset points",
                    xytext=(8, 8), fontsize=9, color='darkred')

    punto, = ax.plot([], [], 'o', color='blue', markersize=14, label='Tag')
    rastro, = ax.plot([], [], '-', color='lightblue', linewidth=1, alpha=0.5)

    historial_x = []
    historial_y = []

    ax.set_xlim(-0.5, 5.0)
    ax.set_ylim(-0.5, 5.0)
    ax.set_xlabel("X (metros)")
    ax.set_ylabel("Y (metros)")
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.legend()

    while plt.fignum_exists(fig.number):
        x = pos_actual["x"]
        y = pos_actual["y"]
        quieto = pos_actual["quieto"]

        historial_x.append(x)
        historial_y.append(y)

        if len(historial_x) > 100:
            historial_x.pop(0)
            historial_y.pop(0)

        punto.set_data([x], [y])
        punto.set_color('gray' if quieto else 'blue')
        rastro.set_data(historial_x, historial_y)

        ax.set_title(
            f"{'🔴 QUIETO' if quieto else '🟢 MOVIÉNDOSE'}  →  X:{x:.2f}m  Y:{y:.2f}m"
        )

        plt.pause(0.1)

    plt.ioff()
    plt.show()

# ─── INICIO ──────────────────────────────────────
hilo_ble = threading.Thread(target=iniciar_ble, daemon=True)
hilo_ble.start()

mostrar_mapa()