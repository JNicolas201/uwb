# ─── TAGS ────────────────────────────────────────
TAGS = {
    "DW0214_verde": {
        "mac":        "EF:D4:9A:60:7B:08",
        "color":      "royalblue",
        "color_rastro": "cornflowerblue",
        "ctk_color":  "#4169e1",
    },
    "Tag2": {
        "mac":        "D7:E4:49:3E:07:FC",
        "color":      "red",
        "color_rastro": "lightsalmon",
        "ctk_color":  "#e14141",
    },
}

# ─── ANCHORS ─────────────────────────────────────
ANCHORS = {
    "DW068E": {"pos": [0.0, 0.0], "tipo": "Slave"},
    "DWD885": {"pos": [0.0, 4.0], "tipo": "Slave"},
    "DW8624": {"pos": [4.0, 0.0], "tipo": "Slave"},
    "DW4CAE": {"pos": [4.0, 4.0], "tipo": "Initiator"},
}

# ─── BLE ─────────────────────────────────────────
UUID_POS = "003bbdf2-c634-4b3d-ab56-7ec889b89a37"

# ─── SISTEMA ─────────────────────────────────────
SISTEMA = {
    "pausado":   False,
    "umbral":    0.02,
    "suavizado": 3,
}

# ─── AREA ────────────────────────────────────────
CONFIG_AREA = {
    "ancho": 4.0,
    "alto":  4.0,
}