import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# Ángulos en grados y distancias en milímetros
angulos = np.arange(360)
distancias = np.zeros(360)

fig = plt.figure()
ax = fig.add_subplot(111, projection="polar")
puntos, = ax.plot([], [], "g.", markersize=3)

ax.set_theta_zero_location("N")
ax.set_theta_direction(-1)
ax.set_ylim(0, 8000)
ax.set_title("LiDAR Studica - 360°")

def actualizar(_):
    # Sustituir por las lecturas reales del sensor
    theta = np.radians(angulos)
    puntos.set_data(theta, distancias)
    return puntos,

ani = FuncAnimation(fig, actualizar, interval=100)
plt.show()