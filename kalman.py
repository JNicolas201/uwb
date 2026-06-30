import numpy as np
from filterpy.kalman import KalmanFilter

def crear_filtro_kalman():
    """
    Estado: [x, y, z, vx, vy, vz]
    Medición: [x, y, z]
    Optimizado para movimiento humano (~1.4 m/s velocidad normal)
    """
    kf = KalmanFilter(dim_x=6, dim_z=3)

    dt = 0.1  # 100ms entre lecturas

    # Matriz de transición (modelo de movimiento constante)
    kf.F = np.array([
        [1, 0, 0, dt, 0,  0 ],
        [0, 1, 0, 0,  dt, 0 ],
        [0, 0, 1, 0,  0,  dt],
        [0, 0, 0, 1,  0,  0 ],
        [0, 0, 0, 0,  1,  0 ],
        [0, 0, 0, 0,  0,  1 ],
    ])

    # Matriz de observación (solo medimos posición)
    kf.H = np.array([
        [1, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0],
    ])

    # Ruido de medición (UWB tiene ~10-30cm de error)
    # Más alto = confía menos en la medición, más suave
    # Más bajo = confía más en la medición, más reactivo
    kf.R = np.diag([0.1, 0.1, 0.2])

    # Ruido de proceso (qué tan brusco puede ser el movimiento)
    # Ajustado para velocidad humana normal
    q = 0.05
    kf.Q = np.eye(6) * q
    kf.Q[3:, 3:] *= 2  # velocidades tienen más incertidumbre

    # Covarianza inicial
    kf.P = np.eye(6) * 0.5

    # Estado inicial
    kf.x = np.zeros((6, 1))

    return kf

def inicializar_kalman(tag, x, y, z):
    """Inicializa el filtro con la primera posición conocida"""
    kf = crear_filtro_kalman()
    kf.x = np.array([[x], [y], [z], [0], [0], [0]])
    tag["kalman"] = kf

def actualizar_kalman(tag, x, y, z):
    """
    Aplica el filtro Kalman a una nueva medición.
    Retorna la posición filtrada (x, y, z).
    """
    kf = tag["kalman"]

    if kf is None:
        inicializar_kalman(tag, x, y, z)
        return x, y, z

    # Predicción
    kf.predict()

    # Corrección con la medición
    medicion = np.array([[x], [y], [z]])
    kf.update(medicion)

    # Extraer posición filtrada
    x_f = float(kf.x[0])
    y_f = float(kf.x[1])
    z_f = float(kf.x[2])

    return x_f, y_f, z_f

def obtener_velocidad_kalman(tag):
    """Velocidad estimada por Kalman (más precisa que la calculada)"""
    if tag["kalman"] is None:
        return 0.0
    vx = float(tag["kalman"].x[3])
    vy = float(tag["kalman"].x[4])
    return round((vx**2 + vy**2)**0.5, 2)