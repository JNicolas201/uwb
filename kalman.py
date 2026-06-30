import numpy as np
from filterpy.kalman import KalmanFilter

def crear_filtro_kalman():
    kf = KalmanFilter(dim_x=6, dim_z=3)

    dt = 0.1

    kf.F = np.array([
        [1, 0, 0, dt, 0,  0 ],
        [0, 1, 0, 0,  dt, 0 ],
        [0, 0, 1, 0,  0,  dt],
        [0, 0, 0, 1,  0,  0 ],
        [0, 0, 0, 0,  1,  0 ],
        [0, 0, 0, 0,  0,  1 ],
    ])

    kf.H = np.array([
        [1, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0],
    ])

    kf.R = np.diag([0.5, 0.5, 0.1])

    q = 0.02
    kf.Q = np.eye(6) * q
    kf.Q[3:, 3:] *= 2

    kf.P = np.eye(6) * 0.5
    kf.x = np.zeros((6, 1))

    return kf

def inicializar_kalman(tag, x, y, z):
    kf = crear_filtro_kalman()
    kf.x = np.array([[x], [y], [z], [0], [0], [0]])
    tag["kalman"] = kf

def actualizar_kalman(tag, x, y, z):
    kf = tag["kalman"]

    if kf is None:
        inicializar_kalman(tag, x, y, z)
        return x, y, z

    kf.predict()

    medicion = np.array([[x], [y], [z]])
    kf.update(medicion)

    x_f = float(kf.x[0, 0])
    y_f = float(kf.x[1, 0])
    z_f = float(kf.x[2, 0])

    return x_f, y_f, z_f

def obtener_velocidad_kalman(tag):
    if tag["kalman"] is None:
        return 0.0
    vx = float(tag["kalman"].x[3, 0])
    vy = float(tag["kalman"].x[4, 0])
    return round((vx**2 + vy**2)**0.5, 2)