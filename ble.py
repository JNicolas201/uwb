import asyncio
from datetime import datetime
from bleak import BleakClient
from config import TAGS, UUID_POS, SISTEMA
from estado import estado_tags
from kalman import actualizar_kalman, inicializar_kalman

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
        if SISTEMA["pausado"]:
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

        # Inicializar Kalman en primera lectura
        if tag["kalman"] is None:
            inicializar_kalman(tag, x, y, z)

        # Aplicar filtro Kalman
        x_k, y_k, z_k = actualizar_kalman(tag, x, y, z)

        # Detectar movimiento
        if tag["anterior"]:
            dist = ((x_k - tag["anterior"][0])**2 +
                    (y_k - tag["anterior"][1])**2)**0.5
            vel = round(dist / 0.1, 2)
            tag["velocidad"] = vel
            tag["quieto"]    = dist < SISTEMA["umbral"]
            if tag["quieto"]:
                tag["tiempo_quieto"] += 1
            else:
                tag["tiempo_quieto"] = 0
        else:
            tag["quieto"] = False

        tag["x"] = x_k
        tag["y"] = y_k
        tag["z"] = z_k
        tag["anterior"] = (x_k, y_k, z_k)

        # Log
        hora   = datetime.now().strftime("%H:%M:%S")
        estado = "QUIETO  " if tag["quieto"] else "MOVIENDO"
        tag["log"].appendleft(
            f"{hora} | {estado} | "
            f"X:{x_k:.2f} Y:{y_k:.2f} Z:{z_k:.2f} | "
            f"{tag['velocidad']:.2f}m/s"
        )

    return callback

async def conectar_tag(nombre, mac):
    print(f"Conectando a {nombre}...")
    while True:
        try:
            async with BleakClient(mac, timeout=30.0) as client:
                estado_tags[nombre]["conectado"] = True
                print(f"✓ {nombre} conectado!")
                await client.start_notify(
                    UUID_POS, hacer_callback(nombre))
                await asyncio.sleep(9999)
        except Exception as e:
            estado_tags[nombre]["conectado"] = False
            print(f"✗ {nombre} desconectado — Reconectando en 5s...")
            await asyncio.sleep(5)

async def ble_loop():
    await asyncio.gather(*[
        conectar_tag(nombre, info["mac"])
        for nombre, info in TAGS.items()
    ])

def iniciar_ble():
    asyncio.run(ble_loop())