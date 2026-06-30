import threading
from ble import iniciar_ble
from ui.app import AppRTLS

# Crear archivo vacío para que ui sea un paquete
import os
if not os.path.exists("ui/__init__.py"):
    open("ui/__init__.py", "w").close()

if __name__ == "__main__":
    # Iniciar BLE en hilo separado
    hilo_ble = threading.Thread(target=iniciar_ble, daemon=True)
    hilo_ble.start()

    # Iniciar app
    app = AppRTLS()
    app.mainloop()