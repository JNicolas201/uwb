from collections import deque
from config import TAGS, SISTEMA

def crear_estado_tags():
    return {
        nombre: {
            "x":            2.0,
            "y":            2.0,
            "z":            0.0,
            "quieto":       True,
            "historial_x":  [],
            "historial_y":  [],
            "anterior":     None,
            "conectado":    False,
            "buffer_x":     deque(maxlen=SISTEMA["suavizado"]),
            "buffer_y":     deque(maxlen=SISTEMA["suavizado"]),
            "buffer_z":     deque(maxlen=SISTEMA["suavizado"]),
            "velocidad":    0.0,
            "tiempo_quieto": 0,
            "log":          deque(maxlen=1000),
            "kalman":       None,  # se inicializa en kalman.py
        }
        for nombre in TAGS
    }

# Estado global compartido entre todos los módulos
estado_tags      = crear_estado_tags()
tag_seleccionado = {"nombre": None}