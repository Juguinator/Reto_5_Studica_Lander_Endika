"""
Teleoperación de un robot con un mando PlayStation (ROS 2)
==========================================================

QUÉ HACE
    Lee el mando PlayStation conectado al robot y/o el MANDO DIGITAL (una
    página web), traduce lo que pulsas en velocidades y las envía a:
      - los 3 motores del chasis  -> servicio ROS /titan0/titan_cmd
      - servo_1 (elevación de la pinza, continuo)  -> topic ROS /servo_1/cmd
      - servo_2 (apertura y cierre de la pinza)    -> topic ROS /servo_2/cmd
      - servo_3 (rotación de la pinza, continuo)   -> topic ROS /servo_3/cmd
      - LEDs verde y rojo         -> topics ROS /led_verde/cmd y /led_rojo/cmd
    Además lee los botones START / STOP y los finales de carrera por los
    topics /<nombre>/state del componente "dio" de params.yaml, y lee el
    LiDAR por el puerto serie para dibujarlo en una página web y para el modo
    autónomo.

CONTROLES
    Stick izquierdo ......... mover el robot (adelante / derecha / atrás /
                              izquierda, según hacia dónde lo inclines)
    R1 / L1 ................. girar sobre sí mismo (R1 en un sentido, L1 en
                              el contrario)
    Círculo ................. modo turbo ON/OFF: la velocidad se multiplica por
                              FACTOR_MODO_TURBO (x2) al desplazarse con el stick
                              izquierdo, al girar con R1/L1 y con los gatillos
    Triángulo (mantener) .... VELOCIDAD MÁXIMA (VELOCIDAD_MAXIMA) en todos esos
                              movimientos, tenga o no el turbo activado. Al
                              soltarlo se vuelve a la velocidad normal (o
                              turbo, si está activado)
    Stick derecho (arriba/abajo) ... subir/bajar la pinza (servo_1); cuanto más
                              lo inclinas, más rápido gira
    Stick derecho (izquierda/derecha) ... girar la pinza (servo_3) a velocidad
                              fija: izquierda = velocidad positiva, derecha =
                              negativa (sentido invertido, ver SENTIDO_ROTACION_PINZA)
    Cruz (X) (mantener) ..... ABRIR la pinza (servo_2) a velocidad fija
    Cuadrado (mantener) ..... CERRAR la pinza (servo_2) a velocidad fija
    Gatillo izquierdo (L2) .. mueve las ruedas por etapas, según lo apretado:
                                etapa 1 -> (-velocidad, 0, 0)
                                etapa 2 -> (-velocidad, -velocidad, 0)
                                etapa 3 -> (-velocidad, -velocidad, -velocidad)
    Gatillo derecho (R2) .... igual, en el otro sentido:
                                etapa 1 -> (0, 0, velocidad)
                                etapa 2 -> (0, velocidad, velocidad)
                                etapa 3 -> (velocidad, velocidad, velocidad)
                              Cada etapa empieza al apretar el gatillo un cierto
                              porcentaje (ETAPAS_GATILLO: ahora 1%, 50% y 100%,
                              es decir, la etapa 3 solo con el gatillo a fondo).
                              Si se aprietan los dos a la vez, el chasis se para.
                              R1/L1 tienen prioridad sobre los gatillos, y los
                              gatillos sobre el stick izquierdo.
                              Con el mando digital (página web) los gatillos son
                              de todo o nada, así que siempre se llega a la etapa 3.
    Options ................. MODO AUTÓNOMO ON/OFF (ver más abajo): el robot se
                              mueve solo, esquivando obstáculos con el LiDAR

    Teclado (solo en el mando digital):
        W A S D = stick izquierdo        Flechas = stick derecho
        Q / E = L1 / R1                  U / O = L2 / R2
        J = Cuadrado   K = Cruz   L = Círculo   I = Triángulo
        P = Options (modo autónomo)

BOTONES, LEDs Y FINALES DE CARRERA (físicos, en la VMX; ver params.yaml)
    El robot solo obedece al mando cuando está EN MARCHA. Al arrancar el
    programa está PARADO y no se mueve nada hasta pulsar START:
      START ... pone el robot en marcha
      STOP .... lo para todo (motores y los 3 servos); para volver a
                moverlo hay que pulsar START otra vez
      RESET ... sin uso de momento
    LEDs:  verde fijo = en marcha | rojo fijo = parado
    FC_SUP / FC_INF ... finales de carrera de servo_1: FC_SUP impide seguir
      subiendo (stick derecho hacia ARRIBA) y FC_INF impide seguir bajando
      (hacia ABAJO). Se puede mover en el sentido contrario.
    Todos los botones y finales de carrera son contactos normalmente abiertos.
    Seguridad: si dejan de llegar datos del botón STOP, el robot se para.

ORGANIZACIÓN DEL ARCHIVO (de arriba abajo)
    1. Configuración ........ valores que querrás ajustar
    2. Protocolo del mando .. detalles técnicos del driver de Linux
    3. Mapa del mando ....... número de cada botón y de cada eje
    4. EstadoMando .......... ENTRADA: sabe qué hay pulsado en cada momento
                              (y MandoFisico, que lee el mando PlayStation)
    5. MandoVirtual ......... ENTRADA: el mando digital (página web) y el árbitro
                              que da prioridad al mando físico
    6. ControlRobot ......... SALIDA: habla con ROS (motores, servos, LEDs; lee botones)
    7. StreamCamara ......... SALIDA: emite la cámara por HTTP (imagen normal y
                              otra con reconocimiento de colores), LidarSerie
                              (lee el LiDAR) y VisorLidar (lo dibuja en una web)
    8. Funciones de cálculo . convierten sticks en velocidades y eligen el rumbo
                              del modo autónomo
    9. PanelControl ......... estado del robot (START/STOP), LEDs, finales de carrera
   10. ControladorManual .... el "cerebro": decide qué enviar en cada ciclo
   11. main ................. lo prepara todo y repite el bucle

MANDO FÍSICO Y MANDO DIGITAL (variable MANDO_DIGITAL, en la configuración)
    El mando PlayStation conectado a la Raspberry (Bluetooth/USB) se usa siempre.
    Con MANDO_DIGITAL = True se activa además el MANDO DIGITAL: abre en el
    navegador de tu PC o móvil  http://10.12.34.2:1182  (no hace falta
    emparejar nada). Se maneja con la pantalla (táctil o ratón), con el
    teclado, o con un mando conectado por USB a TU ordenador. Si se corta la
    conexión, el robot se para en medio segundo. Si la cámara está activada,
    la imagen sale de fondo en la página.

    El mando FÍSICO tiene prioridad absoluta sobre el digital:
      - Mientras el mando físico se esté usando (o tenga algo pulsado), y hasta
        5 segundos después de la última vez que se tocó, el digital queda
        bloqueado. La página muestra "Mando físico conectado".
      - Si el mando físico se mueve mientras alguien usa el digital, se le
        corta la conexión al digital (se sueltan sus controles).
      - Pasados 5 segundos sin tocar el mando físico, el digital vuelve a
        estar disponible (la página se reconecta sola).
      - Si no hay mando físico conectado, el digital funciona sin esperas. El
        mando físico se puede conectar o desconectar con el programa en marcha.
    Con MANDO_DIGITAL = False la página no se sirve y el mando físico es
    obligatorio (si no se encuentra, el programa termina).

    La página lleva un BORDE ROJO mientras el robot está PARADO (al arrancar o
    tras pulsar STOP), hasta que se pulsa el botón START del robot.

CÁMARA
    Al arrancar, el programa emite la imagen de la cámara por la red en dos
    puertos (los dos salen de la misma cámara, y corren en hilos aparte, así
    que no afectan al control del robot):
      - Imagen normal ................ http://10.12.34.2:1181
      - Reconocimiento de colores .... http://10.12.34.2:1183
        Dibuja un recuadro blanco con el nombre (rojo, azul o verde, ver
        COLORES_HSV) sobre la mancha más grande de cada color. Solo se procesa
        mientras alguien tiene abierta esa dirección, para no cargar la CPU.

LIDAR
    El programa lee el LiDAR (YDLIDAR) directamente por el puerto serie
    (LIDAR_PUERTO_SERIE) y lo dibuja en una gráfica polar en el navegador:
      http://10.12.34.2:1184
    Arriba (0°) hacia delante, los ángulos crecen en sentido horario, y los
    anillos marcan la distancia en milímetros (hasta LIDAR_RANGO_MAX_MM). La
    página se actualiza unas 10 veces por segundo y avisa si dejan de llegar
    datos. Si el 0° no coincide con el frente del robot, o la gráfica sale
    como en un espejo, ajusta LIDAR_GIRO_GRADOS o LIDAR_INVERTIR_SENTIDO.
    El LiDAR está montado al revés, por eso LIDAR_GIRO_GRADOS = 180.

MODO AUTÓNOMO (botón Options del mando físico, del digital o tecla P)
    Options lo activa; pulsarlo otra vez lo desactiva. Con el modo activo el
    robot se mueve solo a AUTONOMO_VELOCIDAD (0.1), sin girar sobre sí mismo
    (como las ruedas son omnidireccionales, se desplaza en cualquier dirección):
      - Cada vez que llega un barrido del LiDAR mira, en direcciones cada
        AUTONOMO_PASO_GRADOS grados, cuánto espacio libre hay (el obstáculo más
        cercano dentro de un cono de ±AUTONOMO_ANCHO_GRADOS grados).
      - Elige la dirección más despejada, con preferencia por ir hacia delante.
        Si delante hay un obstáculo, se desliza hacia el lado más libre; si hay
        una esquina o un callejón, retrocede.
      - Si hay obstáculos a menos de AUTONOMO_DISTANCIA_PARADA_MM en todas las
        direcciones, se queda parado hasta que haya sitio.
    Se desactiva solo si: el robot pasa a PARADO (STOP), dejan de llegar datos
    del LiDAR, o tomas el mando (stick izquierdo, R1/L1 o gatillos; ver
    AUTONOMO_CANCELA_CON_MANDO). No se puede activar sin datos del LiDAR. Los
    servos de la pinza se siguen manejando con el mando. Ojo: el modo autónomo
    NO depende de la conexión del mando; si se cae el wifi, el robot sigue
    moviéndose hasta que pulses STOP en el robot.

FLUJO (se repite unas 50 veces por segundo)
    leer eventos -> actualizar EstadoMando -> calcular velocidades
    -> enviar a ROS solo lo que haya cambiado
"""

import glob
import json
import math
import os
import select
import struct
import termios
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float64
from studica_control.srv import SetData


# =====================================================================
# 1. CONFIGURACIÓN
#    Lo que querrás ajustar está aquí arriba, agrupado y comentado.
# =====================================================================

# --- Depuración ------------------------------------------------------
# Imprime el número y el valor de CADA evento del mando. Úsalo para
# averiguar qué número tiene cada botón o eje si cambias de mando.
MODO_DEBUG = False

# Imprime el ángulo del stick izquierdo en cada ciclo mientras esté fuera
# de la zona muerta (unas 50 líneas por segundo). Ponlo en False si te
# llena la terminal.
MOSTRAR_ANGULO = True

# --- ROS 2 -----------------------------------------------------------
NOMBRE_NODO = 'control_motores'
SERVICIO_MOTORES = '/titan0/titan_cmd'  # servicio que fija la velocidad de un motor
TOPIC_SERVO_1 = '/servo_1/cmd'          # topic de servo_1 (elevación de la pinza)
TOPIC_PINZA = '/servo_2/cmd'            # topic de servo_2 (apertura y cierre de la pinza)
TOPIC_ROTACION_PINZA = '/servo_3/cmd'   # topic de servo_3 (rotación de la pinza)

# Números de los motores del chasis, en el mismo orden en que se reciben
# las velocidades (v1, v2, v3).
MOTORES = (1, 2, 3)

# Segundos que se espera a que el servicio de motores esté disponible.
TIMEOUT_SERVICIO = 1.0

# --- Red ---------------------------------------------------------------
# Solo se usa para escribir las direcciones en los mensajes de la terminal; no
# cambia la IP real del robot (esa se configura en la red).
IP_ROBOT = "10.12.34.2"

# --- Mando -----------------------------------------------------------
# El mando PlayStation conectado a la Raspberry (RUTA_MANDO) se usa siempre.
# True  -> además se activa el MANDO DIGITAL: una página web que abres en el
#          navegador de tu PC o móvil (no hace falta emparejar nada). Si hay
#          mando físico conectado, el físico tiene prioridad absoluta.
# False -> sin mando digital: la página no se sirve y el mando físico es
#          obligatorio (si no se encuentra, el programa termina).
MANDO_DIGITAL = True

RUTA_MANDO = "/dev/input/js0"

# Solo con MANDO_DIGITAL = True
MANDO_VIRTUAL_PUERTO = 1182   # se abre en http://10.12.34.2:1182

# Segundos sin tocar el mando físico para que se habilite el mando digital.
SEGUNDOS_PRIORIDAD_FISICO = 5.0

# Cada cuántos segundos se intenta conectar el mando físico si no está.
REINTENTO_MANDO_FISICO = 2.0

# Si la página deja de enviar datos durante este tiempo (segundos), se sueltan
# todos los controles y el robot se para.
TIMEOUT_MANDO_VIRTUAL = 0.5

# --- Gatillos L2 / R2 -------------------------------------------------
# Se miden de 0 a 100 (%). Por encima de este valor cuentan como "botón
# pulsado" (salen en los mensajes de pulsado/soltado y, en el mando físico,
# cuentan como "en uso" para dar prioridad sobre el mando digital).
UMBRAL_GATILLO = 1

# Etapas de los gatillos al mover el chasis: porcentaje a partir del cual
# se pasa a la etapa 1, 2 y 3. Con (1, 50, 100): etapa 1 desde el 1 %,
# etapa 2 desde el 50 % y etapa 3 solo con el gatillo a fondo.
ETAPAS_GATILLO = (1, 50, 100)

# --- Movimiento del chasis (stick izquierdo, R1/L1 y gatillos) -----------
VELOCIDAD_BASE = 0.3          # velocidad normal de los motores

# Con el modo turbo activado, la velocidad (al desplazarse con el stick, al
# girar con R1/L1 y con los gatillos) se multiplica por este factor (2.0 = el
# doble).
FACTOR_MODO_TURBO = 2.0

# Velocidad máxima de los motores. Mientras se mantiene pulsado el botón
# BOTON_VELOCIDAD_MAXIMA (Triángulo), el robot va a esta velocidad, tenga o
# no el turbo activado. Además, el chasis nunca supera este valor.
VELOCIDAD_MAXIMA = 1.0

# El stick izquierdo se considera centrado cuando sus DOS ejes están por
# debajo de este valor (el máximo es 32767). Con que uno lo supere, se mueve.
ZONA_MUERTA_STICK_IZQ = 5000

# En los movimientos laterales (derecha / izquierda), el motor 2 va a la
# velocidad completa y los motores 1 y 3 reciben esta fracción de ella (valor
# heredado del código original).
CORRECCION_LATERAL = 0.5

# --- servo_1: elevación de la pinza, continuo (stick derecho, eje vertical) -
ZONA_MUERTA_STICK_DER = 8000  # zona muerta del stick derecho
VEL_SERVO_MAX = 100.0         # velocidad máxima del servo (rango -100..100)

# Con el stick: negativo = arriba, positivo = abajo.
# Si el servo gira al revés de lo esperado, cambia este signo a -1.
SENTIDO_SERVO = 1

# --- Pinza: servo_2, continuo (Cruz = abrir, Cuadrado = cerrar) ------------
VEL_PINZA = 30.0              # velocidad fija mientras se mantiene el botón
                              # (rango -100..100)
# Si la pinza hace lo contrario (abre al pulsar Cuadrado), cambia este signo a -1.
SENTIDO_PINZA = 1

# --- Rotación de la pinza: servo_3, continuo (stick derecho, eje horizontal) ---
# Usa la misma zona muerta que servo_1 (ZONA_MUERTA_STICK_DER).
VEL_ROTACION_PINZA = 10.0      # velocidad fija mientras el stick esté hacia un lado
                              # (rango -100..100)
# Con 1: stick a la izquierda = velocidad negativa, a la derecha = positiva.
# Con -1 (valor actual, sentido invertido): izquierda = positiva, derecha = negativa.
SENTIDO_ROTACION_PINZA = -1

# --- Botones físicos, LEDs y finales de carrera (VMX DIO) --------------------
# Van por el componente "dio" de params.yaml. Entradas: /<nombre>/state (Bool,
# nivel del pin: True = HIGH). Salidas: /<nombre>/cmd (Bool).
#
# Cableado: todos los botones y finales de carrera son contactos normalmente
# abiertos (NO) entre el pin y GND. El pin está en HIGH en reposo y pasa a LOW
# al pulsar o tocar.

# Entradas que se leen: clave interna -> topic
ENTRADAS_DIO = {
    "stop": '/btn_stop/state',
    "start": '/btn_start/state',
    "fc_sup": '/fc_sup/state',
    "fc_inf": '/fc_inf/state',
    # "reset": '/btn_reset/state',     # RESET (pin 15): sin uso de momento
}
TOPIC_LED_VERDE = '/led_verde/cmd'
TOPIC_LED_ROJO = '/led_rojo/cmd'
LEDS_ACTIVOS_EN_ALTO = True   # True: pin en HIGH = LED encendido

TIMEOUT_DATOS_DIO = 3.0       # segundos sin datos del botón STOP => se para el robot
REFRESCO_LEDS = 1.0           # segundos: se repite la orden a los LEDs por si se perdió
SPIN_POR_CICLO = 5            # veces que se llama a spin_once en cada ciclo (cada una
                              # procesa como mucho un mensaje de ROS)

# --- Cámara (emisión de vídeo por HTTP) ----------------------------------
CAMARA_ACTIVADA = True        # False para arrancar el robot sin cámara
CAMARA_INDICE = 0             # /dev/video0 (prueba 1 si no sale imagen)
CAMARA_ANCHO = 800            # 1920x1080 satura el wifi y la CPU de la Pi;
CAMARA_ALTO = 600             # sube la resolución solo si va fluido
CAMARA_CALIDAD_JPEG = 10      # 0-100: menos calidad = menos datos por wifi
CAMARA_GIRO_180 = True        # la cámara está montada boca abajo
CAMARA_PUERTO = 1181          # (FRC: la radio permite los puertos 1180-1190)

# Segunda emisión, con reconocimiento de colores. Sale de la misma cámara (no
# se abre dos veces) y solo se procesa mientras alguien la está viendo.
CAMARA_COLORES_ACTIVADA = True    # necesita CAMARA_ACTIVADA = True
CAMARA_COLORES_PUERTO = 1183

# Rangos HSV de cada color, como ((H, S, V) mínimo, (H, S, V) máximo). Ajústalos
# con tu luz. El rojo "da la vuelta" en H (0 y 180), por eso son dos rangos.
COLORES_HSV = {
    "rojo": [((0, 75, 168), (16, 214, 255)), ((170, 120, 70), (180, 255, 255))],
    "azul": [((85, 152, 93), (130, 255, 255))],
    "verde": [((46, 86, 94), (97, 162, 255))],
}
COLORES_AREA_MINIMA = 800     # píxeles: las manchas más pequeñas se ignoran (ruido)
COLORES_DESENFOQUE = (7, 7)   # tamaño del desenfoque previo (debe ser impar)
COLORES_KERNEL = 5            # tamaño del filtro que borra los puntos sueltos

# --- LiDAR (visualización por HTTP) --------------------------------------
LIDAR_ACTIVADO = True         # False para no leer el LiDAR ni abrir su página
LIDAR_PUERTO_SERIE = "/dev/ttyUSB0"  # puerto serie del LiDAR; None = probar /dev/ttyUSB* y /dev/ttyACM*
LIDAR_BAUDIOS = (115200, 230400)     # velocidades que se prueban, por orden
LIDAR_TIEMPO_CONEXION = 5.0   # segundos que se espera datos válidos en cada prueba
LIDAR_DISTANCIA_MAX_MM = 5000 # lecturas más lejanas se descartan
LIDAR_PUERTO = 1184           # se abre en http://10.12.34.2:1184
LIDAR_RANGO_MAX_MM = 8000     # radio de la gráfica, en milímetros (los puntos más
                              # lejanos no se dibujan)

# Corrección de la orientación (se aplica a los ángulos que manda el LiDAR):
LIDAR_GIRO_GRADOS = 180       # grados que se suman al ángulo (por si el 0° del
                              # LiDAR no mira al frente del robot)
LIDAR_INVERTIR_SENTIDO = False  # True si la gráfica sale como en un espejo (el
                              # LiDAR serie ya cuenta en sentido horario, como la gráfica)
LIDAR_TIMEOUT_DATOS = 2.0     # segundos sin recibir un barrido => la página avisa

# --- Modo autónomo (botón Options) ---------------------------------------
# Necesita el LiDAR (LIDAR_ACTIVADO = True). Ver "MODO AUTÓNOMO" al principio.
AUTONOMO_VELOCIDAD = 0.25      # velocidad de los motores en modo autónomo (fija: no la
                              # cambian ni el turbo ni el Triángulo)
AUTONOMO_DISTANCIA_PARADA_MM = 250   # si en TODAS las direcciones hay algo más cerca
                              # que esto, el robot se para (ajústalo al tamaño del robot)
AUTONOMO_DISTANCIA_LIBRE_MM = 1000   # a partir de esta distancia una dirección se
                              # considera totalmente libre (más lejos da igual)
AUTONOMO_ANCHO_GRADOS = 35    # medio ancho del cono que se mira en cada dirección
                              # (±35° = 70° en total; súbelo si el robot es ancho)
AUTONOMO_PASO_GRADOS = 10     # cada cuántos grados se prueba una dirección
AUTONOMO_PREFERENCIA_FRENTE_MM = 400  # ventaja (en mm de espacio libre) de ir hacia
                              # delante frente a ir hacia atrás; los lados reciben la mitad
AUTONOMO_HISTERESIS_MM = 150  # una dirección nueva debe ganar por este margen a la
                              # actual para cambiar (evita que el robot dude)
AUTONOMO_TIMEOUT_LIDAR = 1.0  # segundos sin barrido nuevo => se desactiva el modo
AUTONOMO_CANCELA_CON_MANDO = True    # True: mover el stick izquierdo, R1/L1 o los
                              # gatillos desactiva el modo y te da el control

# --- Bucle principal -------------------------------------------------
PERIODO_CICLO = 0.02          # segundos entre ciclos (0.02 s = 50 ciclos/segundo)


# =====================================================================
# 2. PROTOCOLO DEL MANDO (API "joystick" de Linux) - no hace falta tocarlo
# =====================================================================
# Cada evento que entrega /dev/input/js0 ocupa 8 bytes:
#     I -> tiempo en milisegundos (no lo usamos)
#     h -> valor (botón: 0 ó 1; eje: -32767..32767)
#     B -> tipo de evento (botón o eje)
#     B -> número del botón o del eje
FORMATO_EVENTO = "IhBB"
TAMANO_EVENTO = struct.calcsize(FORMATO_EVENTO)

TIPO_BOTON = 0x01
TIPO_EJE = 0x02

# Al abrir el mando, el driver manda un evento por cada botón y eje con
# este bit activado, para informar de cómo está todo en ese instante.
# No son pulsaciones reales.
FLAG_INICIAL = 0x80

VALOR_MAX_EJE = 32767         # los ejes van de -32767 a +32767


# =====================================================================
# 3. MAPA DEL MANDO (numeración de un mando PlayStation: DualShock 4 /
#    DualSense). Si algún número no coincide con tu mando, pon
#    MODO_DEBUG = True y mira qué número sale al pulsar cada cosa.
# =====================================================================

# Ejes. En los sticks, Y negativo = arriba y Y positivo = abajo.
EJE_IZQ_X = 0
EJE_IZQ_Y = 1
EJE_GATILLO_IZQ = 2           # L2 analógico (suelto = -32767, a fondo = +32767)
EJE_DER_X = 3
EJE_DER_Y = 4
EJE_GATILLO_DER = 5           # R2 analógico

# Botones
BOTON_CRUZ = 0
BOTON_CIRCULO = 1
BOTON_TRIANGULO = 2
BOTON_CUADRADO = 3
BOTON_L1 = 4
BOTON_R1 = 5
BOTON_L2 = 6                  # L2 como botón digital (además del eje)
BOTON_R2 = 7                  # R2 como botón digital
BOTON_SHARE = 8
BOTON_OPTIONS = 9
BOTON_PS = 10
BOTON_L3 = 11                 # pulsar el stick izquierdo
BOTON_R3 = 12                 # pulsar el stick derecho
BOTON_MODO_TURBO = BOTON_CIRCULO   # modo turbo (la Cruz está ocupada por la pinza)
BOTON_PINZA_ABRIR = BOTON_CRUZ
BOTON_PINZA_CERRAR = BOTON_CUADRADO
BOTON_VELOCIDAD_MAXIMA = BOTON_TRIANGULO   # mantener pulsado: velocidad máxima
BOTON_AUTONOMO = BOTON_OPTIONS             # pulsar: modo autónomo ON/OFF
# La cruceta y el touchpad no están mapeados. Con MODO_DEBUG verás su
# número (en muchos mandos PlayStation la cruceta llega como ejes 6 y 7).

# Los gatillos son ejes analógicos, pero además los tratamos como botones
# "virtuales" con estos nombres. Así salen en los mensajes de
# pulsado/soltado y se pueden consultar con esta_pulsado / toggle_activo.
GATILLO_IZQ = "L2"
GATILLO_DER = "R2"
GATILLO_POR_EJE = {
    EJE_GATILLO_IZQ: GATILLO_IZQ,
    EJE_GATILLO_DER: GATILLO_DER,
}


# =====================================================================
# 4. ENTRADA: EL ESTADO DEL MANDO Y EL MANDO FÍSICO
# =====================================================================
class EstadoMando:
    """Recuerda qué está pulsado y dónde están los sticks en cada momento.

    Es la "entrada" del programa: no sabe nada de motores ni de ROS. Solo
    se mantiene al día con los eventos del mando y responde preguntas como
    "¿está pulsado R1?" o "¿dónde está el stick izquierdo?".

    Para cada botón guarda dos cosas distintas:
      - pulsado: True mientras lo mantienes apretado.
      - toggle:  un interruptor que cambia (activo/inactivo) cada vez que
                 PULSAS el botón. Sirve para modos del tipo "on/off".
    """

    def __init__(self):
        self.ejes = {}       # nº de eje -> última posición (-32767..32767)
        self.pulsados = {}   # botón o gatillo -> True si está pulsado ahora
        self.toggles = {}    # botón o gatillo -> True si su interruptor está activo

    # -----------------------------------------------------------------
    # Actualización del estado
    # -----------------------------------------------------------------
    def procesar_evento(self, tipo, numero, valor):
        """Actualiza el estado con un evento leído del mando."""
        # Los eventos "iniciales" sirven para sincronizar el estado al abrir
        # el mando, pero no son pulsaciones reales.
        es_inicial = bool(tipo & FLAG_INICIAL)
        # Quitamos el bit de "inicial" para quedarnos con el tipo puro
        tipo = tipo & ~FLAG_INICIAL

        if MODO_DEBUG:
            nombre = "BOTON" if tipo == TIPO_BOTON else "EJE"
            print(f"DEBUG {nombre} numero={numero} valor={valor}")

        if tipo == TIPO_BOTON:
            self._actualizar_boton(numero, valor != 0, es_inicial)

        elif tipo == TIPO_EJE:
            self.ejes[numero] = valor

            # Los gatillos (que son ejes) también actúan como botones virtuales
            if numero in GATILLO_POR_EJE:
                pulsado = self.valor_gatillo(numero) > UMBRAL_GATILLO
                self._actualizar_boton(GATILLO_POR_EJE[numero], pulsado, es_inicial)

    def _actualizar_boton(self, clave, pulsado, es_inicial):
        """Anota si un botón está pulsado y gestiona su interruptor (toggle)."""
        estaba_pulsado = self.pulsados.get(clave, False)
        self.pulsados[clave] = pulsado

        # Si no hay cambio (o es un evento inicial) no ha pasado nada "real"
        if es_inicial or pulsado == estaba_pulsado:
            return

        print(f"[{clave}] {'pulsado' if pulsado else 'soltado'}")

        # Al PULSAR (no al soltar) se invierte el interruptor
        if pulsado:
            self.toggles[clave] = not self.toggles.get(clave, False)

    # -----------------------------------------------------------------
    # Consultas
    # -----------------------------------------------------------------
    def stick_izquierdo(self):
        """Devuelve (x, y) del stick izquierdo. Y negativo = arriba."""
        return (self.ejes.get(EJE_IZQ_X, 0), self.ejes.get(EJE_IZQ_Y, 0))

    def stick_derecho(self):
        """Devuelve (x, y) del stick derecho. Y negativo = arriba."""
        return (self.ejes.get(EJE_DER_X, 0), self.ejes.get(EJE_DER_Y, 0))

    def valor_gatillo(self, eje):
        """Cuánto está apretado un gatillo: 0 (suelto) a 100 (a fondo)."""
        bruto = self.ejes.get(eje, -VALOR_MAX_EJE)   # sin eventos aún = suelto
        porcentaje = (bruto + VALOR_MAX_EJE) / (2 * VALOR_MAX_EJE) * 100
        return max(0, min(100, round(porcentaje)))

    def esta_pulsado(self, clave):
        """True mientras el botón esté mantenido pulsado."""
        return self.pulsados.get(clave, False)

    def toggle_activo(self, clave):
        """Interruptor: pulsar una vez lo activa, otra vez lo desactiva."""
        return self.toggles.get(clave, False)


def leer_eventos(fd, mando):
    """Lee TODOS los eventos pendientes del mando y se los pasa a `mando`.

    El mando se abre en modo no bloqueante: cuando ya no quedan eventos,
    os.read lanza BlockingIOError y salimos de la función.
    """
    while True:
        try:
            datos = os.read(fd, TAMANO_EVENTO)
        except BlockingIOError:
            return                 # no hay más eventos por ahora

        # Lectura vacía o incompleta: lo dejamos para el próximo ciclo
        if len(datos) != TAMANO_EVENTO:
            return

        _, valor, tipo, numero = struct.unpack(FORMATO_EVENTO, datos)
        mando.procesar_evento(tipo, numero, valor)


class MandoFisico:
    """El mando PlayStation conectado a la Raspberry (RUTA_MANDO).

    - Sin `arbitro` (MANDO_DIGITAL = False): el mando es obligatorio. Si no
      se encuentra o se desconecta, se propaga el error y el programa termina.
    - Con `arbitro` (MANDO_DIGITAL = True): el mando es opcional. Si no está,
      el programa sigue con el mando digital y reintenta conectarlo cada
      REINTENTO_MANDO_FISICO segundos; si se desconecta, también lo reintenta.
    """

    def __init__(self, destino, arbitro=None):
        self.destino = destino        # quien recibe los eventos (EstadoMando o ArbitroMando)
        self.arbitro = arbitro
        self.fd = None
        self.proximo_intento = 0.0
        self.avisado_ausente = False

    def conectar(self):
        """Abre el mando. Devuelve True si lo ha conseguido."""
        if self.arbitro is None:
            # Modo "no bloqueante": si no hay eventos, la lectura no se queda
            # esperando y el bucle puede seguir funcionando.
            self.fd = os.open(RUTA_MANDO, os.O_RDONLY | os.O_NONBLOCK)
            print("Mando físico conectado. Mueve el joystick.")
            return True

        try:
            self.fd = os.open(RUTA_MANDO, os.O_RDONLY | os.O_NONBLOCK)
        except OSError as error:
            self.proximo_intento = time.monotonic() + REINTENTO_MANDO_FISICO
            if not self.avisado_ausente:
                print(f"[Mando físico] No conectado ({error}). "
                      f"Se usa el mando digital y se reintenta cada "
                      f"{REINTENTO_MANDO_FISICO:g} s.")
                self.avisado_ausente = True
            return False

        self.avisado_ausente = False
        print("[Mando físico] Conectado. Tiene prioridad sobre el mando digital.")
        self.arbitro.fisico_conectado()
        return True

    def leer(self):
        """Lee los eventos pendientes (y, si falta el mando, intenta conectarlo)."""
        if self.fd is None:
            if self.arbitro is not None and time.monotonic() >= self.proximo_intento:
                self.conectar()
            return

        if self.arbitro is None:
            leer_eventos(self.fd, self.destino)
            return

        try:
            leer_eventos(self.fd, self.destino)
        except OSError as error:
            print(f"[Mando físico] Desconectado: {error}")
            self.cerrar()
            self.arbitro.fisico_desconectado()
            self.proximo_intento = time.monotonic() + REINTENTO_MANDO_FISICO

    def cerrar(self):
        """Cierra el archivo del mando."""
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


# =====================================================================
# 5. ENTRADA ALTERNATIVA: EL MANDO DIGITAL (página web)
# =====================================================================
# Con MANDO_DIGITAL = True el robot sirve una página web con un mando en
# pantalla. La página manda por HTTP el estado de los botones y los ejes, y
# aquí se convierte en los mismos eventos que daría el mando físico, así que
# EstadoMando (y todo lo que hay detrás) no nota la diferencia.
N_BOTONES_VIRTUAL = 13                                           # botones 0..12
# Código HTTP con el que se responde a la página según quién tenga el control:
#   ok -> 204 | otra página lo tiene -> 409 | manda el mando físico -> 423
CODIGOS_RESPUESTA = {"ok": 204, "ocupado": 409, "fisico": 423}
EJES_EN_REPOSO = (0, 0, -VALOR_MAX_EJE, 0, 0, -VALOR_MAX_EJE)    # ejes 0..5

# La página del mando. Va dentro del propio archivo para no depender de
# ficheros sueltos. __PUERTO_CAMARA__ se sustituye al servirla.
PAGINA_MANDO_VIRTUAL = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<title>Mando digital</title>
<style>
  :root {
    --s: min(36vmin, 260px);   /* tamaño de los sticks */
    --b: min(13vmin, 90px);    /* tamaño de los botones de cara */
    --m: 3vmin;                /* margen */
    --top: var(--m);           /* altura de los botones L2/R2 */
    --texto: #e8ecf1;
    --acento: #4da3ff;
  }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html, body {
    margin: 0; height: 100%; overflow: hidden; background: #0b0e12; color: var(--texto);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    touch-action: none; user-select: none; -webkit-user-select: none; -webkit-touch-callout: none;
  }
  #video { position: fixed; inset: 0; width: 100%; height: 100%; object-fit: contain; }

  #barra { position: fixed; top: 1.5vmin; left: 50%; transform: translateX(-50%);
           display: flex; gap: 8px; align-items: center; z-index: 5; }
  #estado, #pantalla {
    font-size: clamp(12px, 2.4vmin, 16px); padding: 5px 12px; border-radius: 999px;
    white-space: nowrap;
    background: rgba(10, 14, 20, .75); border: 1px solid rgba(255,255,255,.2); color: var(--texto);
  }
  #pantalla { cursor: pointer; }
  #estado::before { content: "●"; margin-right: 6px; color: #ff5d5d; }
  #estado.ok::before { color: #3ddc84; }
  #estado.ocupado::before { color: #ffb74d; }
  #estado.fisico::before { color: var(--acento); }

  /* Borde rojo mientras el robot está PARADO (hasta pulsar START en el robot) */
  #borde { position: fixed; inset: 0; display: none; pointer-events: none; z-index: 20;
           border: 8px solid #ff3b3b; box-shadow: inset 0 0 28px rgba(255, 59, 59, .55); }
  body.parado #borde { display: block; }

  .stick, .btn {
    position: fixed; background: rgba(20, 26, 34, .55);
    border: 2px solid rgba(255,255,255,.28); touch-action: none; cursor: pointer;
  }
  .stick { width: var(--s); height: var(--s); border-radius: 50%; }
  #stickL { left: var(--m); bottom: var(--m); }
  #stickR { right: var(--m); bottom: var(--m); }
  .knob {
    position: absolute; left: 50%; top: 50%; width: 42%; height: 42%; margin: -21% 0 0 -21%;
    border-radius: 50%; background: rgba(255,255,255,.3); border: 2px solid rgba(255,255,255,.6);
    pointer-events: none;
  }
  .stick .pista { position: absolute; left: 0; right: 0; top: -2.4em; text-align: center; }

  .btn {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    font-weight: 700; font-size: clamp(14px, 3.6vmin, 30px); color: var(--texto); line-height: 1.1;
  }
  .btn.on { background: var(--acento); border-color: #fff; color: #04121f !important; }

  .pista { display: none; font-size: clamp(10px, 1.9vmin, 13px); font-weight: 500; opacity: .6; }
  @media (hover: hover) and (pointer: fine) { .pista { display: block; } }

  /* Gatillos y hombros */
  .hombro { width: calc(var(--b) * 1.7); height: calc(var(--b) * .8); border-radius: 14px; }
  #l2 { left: var(--m); top: var(--top); }
  #l1 { left: var(--m); top: calc(var(--top) + var(--b) * .8 + 1.2vmin); }
  #r2 { right: var(--m); top: var(--top); }
  #r1 { right: var(--m); top: calc(var(--top) + var(--b) * .8 + 1.2vmin); }

  /* Options (modo autónomo): entre L1 y R1. Verde mientras el modo está activo */
  #opt { left: 50%; top: calc(var(--top) + var(--b) * .8 + 1.2vmin);
         width: calc(var(--b) * 1.9); height: calc(var(--b) * .8);
         margin-left: calc(var(--b) * -.95); border-radius: 14px;
         font-size: clamp(11px, 2.6vmin, 20px); }
  #opt small { font-size: .72em; font-weight: 500; opacity: .8; }
  body.autonomo #opt { background: #3ddc84; border-color: #fff; color: #04121f; }

  /* Botones de cara en rombo */
  #rombo { position: fixed; width: calc(var(--b) * 2.7); height: calc(var(--b) * 2.7);
           right: calc(var(--m) * 2 + var(--s)); bottom: var(--m); }
  #rombo .btn { position: absolute; width: var(--b); height: var(--b); border-radius: 50%;
                font-size: clamp(22px, 6.5vmin, 46px); }
  #tri { top: 0;    left: calc(50% - var(--b) / 2); color: #5ee0a0; }
  #cru { bottom: 0; left: calc(50% - var(--b) / 2); color: #6fb1ff; }
  #cua { left: 0;   top: calc(50% - var(--b) / 2);  color: #ff9ad5; }
  #cir { right: 0;  top: calc(50% - var(--b) / 2);  color: #ff7a7a; }

  @media (orientation: portrait) {
    :root { --top: calc(var(--m) + 10vmin); }   /* deja sitio a la barra de estado */
    #rombo { right: var(--m); bottom: calc(var(--m) * 2 + var(--s)); }
  }
</style>
</head>
<body class="parado">
  <img id="video" alt="">
  <div id="borde"></div>

  <div id="barra">
    <div id="estado">Conectando…</div>
    <div id="pantalla">Pantalla completa</div>
  </div>

  <button class="btn hombro" id="l2" data-t="l2">L2<span class="pista">U</span></button>
  <button class="btn hombro" id="l1" data-b="4">L1<span class="pista">Q</span></button>
  <button class="btn hombro" id="r2" data-t="r2">R2<span class="pista">O</span></button>
  <button class="btn hombro" id="r1" data-b="5">R1<span class="pista">E</span></button>

  <button class="btn" id="opt" data-b="9">OPTIONS<small>Autónomo</small><span class="pista">P</span></button>

  <div class="stick" id="stickL"><div class="knob"></div><span class="pista">W A S D</span></div>
  <div class="stick" id="stickR"><div class="knob"></div><span class="pista">Flechas</span></div>

  <div id="rombo">
    <button class="btn" id="tri" data-b="2">△<span class="pista">I</span></button>
    <button class="btn" id="cua" data-b="3">□<span class="pista">J</span></button>
    <button class="btn" id="cir" data-b="1">○<span class="pista">L</span></button>
    <button class="btn" id="cru" data-b="0">✕<span class="pista">K</span></button>
  </div>

<script>
(() => {
  'use strict';

  const PUERTO_CAMARA = __PUERTO_CAMARA__;     // 0 = sin cámara
  const MAX = 32767;                           // valor máximo de un eje
  const N_BOTONES = 13;
  const ID = Math.random().toString(36).slice(2, 10);   // identifica esta página

  // ---------------------------------------------------------------
  // Fuentes de entrada: pantalla táctil / ratón, teclado y mando USB.
  // Cada una guarda su estado; luego se combinan en uno solo.
  //   b: botones (numeración del mando PlayStation en Linux)
  //   lx, ly, rx, ry: sticks de -1 a 1 (y negativo = arriba)
  //   l2, r2: gatillos de 0 a 1
  // ---------------------------------------------------------------
  const nuevaFuente = () => ({ b: new Array(N_BOTONES).fill(false),
                               lx: 0, ly: 0, rx: 0, ry: 0, l2: 0, r2: 0 });
  const tactil = nuevaFuente(), teclado = nuevaFuente(), usb = nuevaFuente();

  const botonesEl = [...document.querySelectorAll('[data-b]')];
  const gatillosEl = [...document.querySelectorAll('[data-t]')];
  const sticks = [
    { el: document.getElementById('stickL'), x: 'lx', y: 'ly' },
    { el: document.getElementById('stickR'), x: 'rx', y: 'ry' },
  ];
  sticks.forEach(s => { s.knob = s.el.querySelector('.knob'); });

  const tope = s => s.el.clientWidth / 2 - s.knob.offsetWidth / 2;   // recorrido máx. del stick

  // ---------------------------------------------------------------
  // Táctil / ratón (con captura del puntero: varios dedos a la vez)
  // ---------------------------------------------------------------
  botonesEl.concat(gatillosEl).forEach(el => {
    const poner = on => {
      if (el.dataset.t) tactil[el.dataset.t] = on ? 1 : 0;
      else tactil.b[+el.dataset.b] = on;
      cambio();
    };
    el.addEventListener('pointerdown', e => { e.preventDefault(); el.setPointerCapture(e.pointerId); poner(true); });
    ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(ev =>
      el.addEventListener(ev, () => poner(false)));
  });

  sticks.forEach(s => {
    let id = null;
    const mover = e => {
      const r = s.el.getBoundingClientRect(), t = tope(s);
      let dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2);
      const d = Math.hypot(dx, dy);
      if (d > t) { dx *= t / d; dy *= t / d; }
      tactil[s.x] = dx / t; tactil[s.y] = dy / t;
      cambio();
    };
    const fin = () => { id = null; tactil[s.x] = 0; tactil[s.y] = 0; cambio(); };
    s.el.addEventListener('pointerdown', e => { e.preventDefault(); id = e.pointerId; s.el.setPointerCapture(id); mover(e); });
    s.el.addEventListener('pointermove', e => { if (e.pointerId === id) mover(e); });
    ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(ev =>
      s.el.addEventListener(ev, e => { if (e.pointerId === id) fin(); }));
  });

  // ---------------------------------------------------------------
  // Teclado
  //   W A S D = stick izq.   Flechas = stick der.   Q/E = L1/R1   U/O = L2/R2
  //   J = Cuadrado   K = Cruz   L = Círculo   I = Triángulo   P = Options
  // ---------------------------------------------------------------
  const TECLAS_BOTON = { KeyK: 0, KeyL: 1, KeyI: 2, KeyJ: 3, KeyQ: 4, KeyE: 5, KeyP: 9 };
  const TECLAS = new Set(['KeyW', 'KeyA', 'KeyS', 'KeyD', 'KeyU', 'KeyO',
                          'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight',
                          ...Object.keys(TECLAS_BOTON)]);
  const pulsadas = new Set();

  function leerTeclado() {
    const eje = (neg, pos) => (pulsadas.has(pos) ? 1 : 0) - (pulsadas.has(neg) ? 1 : 0);
    let lx = eje('KeyA', 'KeyD'), ly = eje('KeyW', 'KeyS');
    let rx = eje('ArrowLeft', 'ArrowRight'), ry = eje('ArrowUp', 'ArrowDown');
    const ml = Math.hypot(lx, ly), mr = Math.hypot(rx, ry);
    if (ml > 1) { lx /= ml; ly /= ml; }
    if (mr > 1) { rx /= mr; ry /= mr; }
    Object.assign(teclado, { lx, ly, rx, ry,
                             l2: pulsadas.has('KeyU') ? 1 : 0, r2: pulsadas.has('KeyO') ? 1 : 0 });
    for (const [tecla, n] of Object.entries(TECLAS_BOTON)) teclado.b[n] = pulsadas.has(tecla);
    cambio();
  }
  addEventListener('keydown', e => {
    if (!TECLAS.has(e.code) || e.ctrlKey || e.metaKey || e.altKey) return;
    e.preventDefault();
    if (e.repeat) return;
    pulsadas.add(e.code); leerTeclado();
  });
  addEventListener('keyup', e => { if (pulsadas.delete(e.code)) leerTeclado(); });
  addEventListener('blur', () => { pulsadas.clear(); leerTeclado(); });
  document.addEventListener('visibilitychange', () => { pulsadas.clear(); leerTeclado(); });
  addEventListener('contextmenu', e => e.preventDefault());

  // ---------------------------------------------------------------
  // Mando USB conectado al PC (Gamepad API, mapeo "standard")
  // Se convierte a la numeración del mando PlayStation en Linux.
  // ---------------------------------------------------------------
  let habiaUsb = false;
  function leerUsb() {
    const pads = navigator.getGamepads ? [...navigator.getGamepads()] : [];
    const p = pads.find(x => x && x.connected && x.mapping === 'standard');
    if (!p && !habiaUsb) { requestAnimationFrame(leerUsb); return; }   // sin mando USB: nada que hacer
    habiaUsb = !!p;
    const zm = v => (Math.abs(v) < 0.08 ? 0 : v);
    usb.b.fill(false);
    Object.assign(usb, { lx: 0, ly: 0, rx: 0, ry: 0, l2: 0, r2: 0 });
    if (p) {
      const bt = i => !!(p.buttons[i] && p.buttons[i].pressed);
      usb.b[0] = bt(0); usb.b[1] = bt(1); usb.b[2] = bt(3); usb.b[3] = bt(2);   // ✕ ○ △ □
      usb.b[4] = bt(4); usb.b[5] = bt(5);                                        // L1 R1
      usb.b[8] = bt(8); usb.b[9] = bt(9); usb.b[10] = bt(16);                    // Share Options PS
      usb.b[11] = bt(10); usb.b[12] = bt(11);                                    // L3 R3
      Object.assign(usb, { lx: zm(p.axes[0]), ly: zm(p.axes[1]), rx: zm(p.axes[2]), ry: zm(p.axes[3]),
                           l2: p.buttons[6] ? p.buttons[6].value : 0, r2: p.buttons[7] ? p.buttons[7].value : 0 });
    }
    cambio();
    requestAnimationFrame(leerUsb);
  }

  // ---------------------------------------------------------------
  // Combinar las fuentes, pintar la pantalla y preparar el envío
  // ---------------------------------------------------------------
  function combinar() {
    const c = { b: new Array(N_BOTONES).fill(false), lx: 0, ly: 0, rx: 0, ry: 0, l2: 0, r2: 0 };
    for (const f of [tactil, teclado, usb]) {
      for (let i = 0; i < N_BOTONES; i++) c.b[i] = c.b[i] || f.b[i];
      c.lx += f.lx; c.ly += f.ly; c.rx += f.rx; c.ry += f.ry;
      c.l2 = Math.max(c.l2, f.l2); c.r2 = Math.max(c.r2, f.r2);
    }
    for (const [x, y] of [['lx', 'ly'], ['rx', 'ry']]) {
      const m = Math.hypot(c[x], c[y]);
      if (m > 1) { c[x] /= m; c[y] /= m; }
    }
    if (document.hidden) {                     // pestaña oculta: todo suelto
      return { b: new Array(N_BOTONES).fill(false), lx: 0, ly: 0, rx: 0, ry: 0, l2: 0, r2: 0 };
    }
    return c;
  }

  function pintar(c) {
    botonesEl.forEach(el => el.classList.toggle('on', !!c.b[+el.dataset.b]));
    gatillosEl.forEach(el => el.classList.toggle('on', c[el.dataset.t] > 0.5));
    sticks.forEach(s => {
      const t = tope(s);
      s.knob.style.transform = `translate(${c[s.x] * t}px, ${c[s.y] * t}px)`;
    });
  }

  function aSnapshot(c) {
    const q = v => Math.round(Math.max(-1, Math.min(1, v)) * MAX);
    const gat = v => Math.round(v * 2 * MAX - MAX);          // 0..1 -> -32767..32767
    const b = c.b.slice();
    b[6] = c.l2 > 0.5; b[7] = c.r2 > 0.5;
    return { b: b.map(x => (x ? 1 : 0)),
             a: [q(c.lx), q(c.ly), gat(c.l2), q(c.rx), q(c.ry), gat(c.r2)] };
  }

  // Cola de estados pendientes de enviar (se envían en orden, de uno en uno)
  const cola = [];
  let ultimoTxt = '', ultimo = null, ultimoEnvio = 0;

  function cambio() {
    const c = combinar();
    pintar(c);
    const s = aSnapshot(c), txt = JSON.stringify(s);
    if (txt === ultimoTxt) return;
    ultimoTxt = txt; ultimo = s;
    const fin = cola[cola.length - 1];
    // Si solo cambian los ejes, se reemplaza el último pendiente en vez de acumular
    if (fin && JSON.stringify(fin.b) === JSON.stringify(s.b)) cola[cola.length - 1] = s;
    else cola.push(s);
    if (cola.length > 40) cola.shift();
  }

  // ---------------------------------------------------------------
  // Envío al robot: un POST tras otro. Si no hay cambios, un "latido"
  // cada 100 ms (el robot se para si dejan de llegar datos).
  // ---------------------------------------------------------------
  const estadoEl = document.getElementById('estado');
  function mostrar(clase, texto) {
    estadoEl.className = clase; estadoEl.textContent = texto;
  }
  const dormir = ms => new Promise(r => setTimeout(r, ms));

  // El robot indica en cada respuesta si está PARADO o ACTIVO (X-Estado) y si
  // el modo autónomo está activado (X-Autonomo). Mientras está PARADO (hasta
  // que se pulsa START en el robot) la interfaz lleva borde rojo, y el botón
  // Options se pone verde mientras el modo autónomo está activo.
  function marcarEstadoRobot(r) {
    const e = r.headers.get('X-Estado');
    if (e) document.body.classList.toggle('parado', e !== 'ACTIVO');
    const a = r.headers.get('X-Autonomo');
    if (a) document.body.classList.toggle('autonomo', a === '1');
  }

  async function bucleEnvio() {
    for (;;) {
      let s = cola.shift();
      if (!s) {
        if (performance.now() - ultimoEnvio < 100) { await dormir(8); continue; }
        s = ultimo;
      }
      const ctl = new AbortController();
      const aborto = setTimeout(() => ctl.abort(), 1000);
      const t0 = performance.now();
      try {
        const r = await fetch('/estado', {
          method: 'POST', cache: 'no-store', signal: ctl.signal,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: ID, b: s.b, a: s.a }),
        });
        ultimoEnvio = performance.now();
        marcarEstadoRobot(r);
        if (r.status === 204) mostrar('ok', 'Conectado · ' + Math.round(ultimoEnvio - t0) + ' ms');
        else if (r.status === 423) { mostrar('fisico', 'Mando físico conectado'); await dormir(250); }
        else if (r.status === 409) { mostrar('ocupado', 'Otro mando tiene el control'); await dormir(250); }
        else mostrar('', 'Error ' + r.status);
      } catch (e) {
        mostrar('', 'Sin conexión con el robot');
        await dormir(300);
      } finally {
        clearTimeout(aborto);
      }
    }
  }

  // ---------------------------------------------------------------
  // Cámara (la emite el robot en otro puerto) y pantalla completa
  // ---------------------------------------------------------------
  if (PUERTO_CAMARA) {
    const video = document.getElementById('video');
    const url = () => `http://${location.hostname}:${PUERTO_CAMARA}/?t=${Date.now()}`;
    video.onerror = () => setTimeout(() => { video.src = url(); }, 3000);
    video.src = url();
  }
  const pantallaEl = document.getElementById('pantalla');
  if (!document.documentElement.requestFullscreen) pantallaEl.style.display = 'none';   // p. ej. iPhone
  pantallaEl.addEventListener('click', () => {
    if (document.fullscreenElement) document.exitFullscreen();
    else if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen().catch(() => {});
  });
  addEventListener('resize', cambio);

  cambio();
  leerUsb();
  bucleEnvio();
})();
</script>
</body>
</html>
"""


class ArbitroMando:
    """Decide quién manda cuando hay mando físico y mando digital a la vez.

    El mando FÍSICO tiene prioridad absoluta:
      - Está "en uso" mientras tenga algo pulsado o fuera de su posición de
        reposo, y hasta SEGUNDOS_PRIORIDAD_FISICO segundos después de la última
        vez que se tocó. En ese tiempo el mando digital es rechazado.
      - En cuanto el mando físico se toca, se corta la conexión al mando digital
        (se sueltan sus controles) y los eventos del físico pasan a EstadoMando.
      - El ruido del stick (valores dentro de la zona muerta) no cuenta como
        "tocar" el mando, para que un stick con holgura no bloquee el digital.

    Los eventos del mando físico entran por `procesar_evento` (igual que en
    EstadoMando); el mando digital consulta `fisico_manda`.
    """

    def __init__(self, mando):
        self.mando = mando                  # EstadoMando compartido
        self.digital = None                 # MandoVirtual (se asigna desde main)
        self.cerrojo = threading.Lock()     # el servidor web usa varios hilos
        self.conectado = False              # ¿hay mando físico conectado?
        self.ultimo_toque = 0.0             # cuándo se tocó por última vez
        self.fuera_de_reposo = set()        # controles del físico que no están en reposo

    # -----------------------------------------------------------------
    # Reposo de cada control
    # -----------------------------------------------------------------
    @staticmethod
    def _eje_fuera_de_reposo(numero, valor):
        """True si un eje está fuera de su posición de reposo."""
        if numero in (EJE_IZQ_X, EJE_IZQ_Y):
            return abs(valor) >= ZONA_MUERTA_STICK_IZQ
        if numero in (EJE_DER_X, EJE_DER_Y):
            return abs(valor) >= ZONA_MUERTA_STICK_DER
        if numero in GATILLO_POR_EJE:
            porcentaje = (valor + VALOR_MAX_EJE) / (2 * VALOR_MAX_EJE) * 100
            return round(porcentaje) > UMBRAL_GATILLO
        return abs(valor) >= VALOR_MAX_EJE // 2          # cruceta y otros ejes

    @staticmethod
    def _valor_reposo(numero):
        return -VALOR_MAX_EJE if numero in GATILLO_POR_EJE else 0

    # -----------------------------------------------------------------
    # Conexión del mando físico
    # -----------------------------------------------------------------
    def fisico_conectado(self):
        """Se llama al conectar el mando físico: cuenta como un toque."""
        with self.cerrojo:
            self.conectado = True
            self.ultimo_toque = time.monotonic()
            self.fuera_de_reposo.clear()

    def fisico_desconectado(self):
        """Se llama al perder el mando físico: se sueltan sus controles."""
        with self.cerrojo:
            self.conectado = False
            sueltos = list(self.fuera_de_reposo)
            self.fuera_de_reposo.clear()
        for tipo, numero in sueltos:
            if tipo == TIPO_BOTON:
                self.mando.procesar_evento(TIPO_BOTON, numero, 0)
            else:
                self.mando.procesar_evento(TIPO_EJE, numero, self._valor_reposo(numero))

    def fisico_manda(self):
        """True si el mando físico está conectado y en uso (o se usó hace poco)."""
        with self.cerrojo:
            if not self.conectado:
                return False
            if self.fuera_de_reposo:
                return True
            return time.monotonic() - self.ultimo_toque < SEGUNDOS_PRIORIDAD_FISICO

    # -----------------------------------------------------------------
    # Eventos del mando físico
    # -----------------------------------------------------------------
    def procesar_evento(self, tipo, numero, valor):
        """Recibe un evento del mando físico y lo pasa a EstadoMando."""
        es_inicial = bool(tipo & FLAG_INICIAL)
        tipo_puro = tipo & ~FLAG_INICIAL

        if tipo_puro == TIPO_BOTON:
            clave, fuera = (TIPO_BOTON, numero), valor != 0
        elif tipo_puro == TIPO_EJE:
            clave, fuera = (TIPO_EJE, numero), self._eje_fuera_de_reposo(numero, valor)
        else:
            self.mando.procesar_evento(tipo, numero, valor)
            return

        with self.cerrojo:
            estaba_fuera = clave in self.fuera_de_reposo
            if fuera:
                self.fuera_de_reposo.add(clave)
            else:
                self.fuera_de_reposo.discard(clave)
            # "Tocar" = pulsar, soltar, o mover un control fuera de su reposo.
            # Los eventos iniciales (al abrir el mando) no cuentan.
            toque = (fuera or estaba_fuera) and not es_inicial
            if toque:
                self.ultimo_toque = time.monotonic()

        digital_manda = self.digital is not None and self.digital.tiene_control()
        if toque:
            if self.digital is not None:
                self.digital.soltar_todo("se ha movido el mando físico")
        elif digital_manda:
            return        # ruido del mando físico: no debe pisar al digital

        self.mando.procesar_evento(tipo, numero, valor)


class MandoVirtual:
    """Mando digital: sirve la página del mando y recibe lo que pulsas en ella.

    - GET  /        -> la página del mando.
    - POST /estado  -> la página manda aquí el estado de botones y ejes
                       (varias veces por segundo, aunque no cambie nada).

    Seguridad:
      - Si dejan de llegar datos (se cierra la pestaña, se corta el wifi...)
        se sueltan todos los controles y el robot se para.
      - Solo una página a la vez tiene el control; las demás reciben un 409
        hasta que la activa deje de enviar datos.
      - El mando físico tiene prioridad absoluta (ver ArbitroMando): mientras
        manda, la página recibe un 423 y muestra "Mando físico conectado".
      - Cada respuesta lleva la cabecera X-Estado (PARADO o ACTIVO) para que la
        página pinte el borde rojo mientras el robot está parado, y X-Autonomo
        (1 o 0) para que el botón Options se ilumine con el modo autónomo.
      - Quien abra la página en la red del robot podrá moverlo.
    """

    def __init__(self, mando, arbitro=None):
        self.mando = mando                    # EstadoMando que se mantiene al día
        self.arbitro = arbitro                # decide si manda el mando físico
        self.estado_robot = PARADO            # lo actualiza main en cada ciclo
        self.modo_autonomo = False            # idem: ¿está activado el modo autónomo?
        self.servidor = None
        self.cerrojo = threading.Lock()       # el servidor usa varios hilos
        self.botones = [False] * N_BOTONES_VIRTUAL
        self.ejes = list(EJES_EN_REPOSO)
        self.cliente = None                   # página que tiene el control ahora
        self.ultimo_dato = 0.0                # cuándo llegó el último dato

    def iniciar(self):
        """Arranca el servidor web. Devuelve True si fue bien."""
        virtual = self
        puerto_camara = CAMARA_PUERTO if CAMARA_ACTIVADA else 0
        pagina = PAGINA_MANDO_VIRTUAL.replace(
            "__PUERTO_CAMARA__", str(puerto_camara)).encode("utf-8")

        class Manejador(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"     # mantiene la conexión abierta
            timeout = 5                       # cierra las conexiones muertas

            def handle(self):
                try:
                    super().handle()
                except OSError:               # la pestaña se cerró: no es un error
                    pass

            def do_GET(self):
                if self.path.split("?")[0] in ("/", "/index.html"):
                    self._responder(200, pagina, "text/html; charset=utf-8")
                else:
                    self._responder(404)

            def do_POST(self):
                if self.path != "/estado":
                    self.close_connection = True
                    return self._responder(404)
                try:
                    largo = int(self.headers.get("Content-Length", 0))
                    if not 0 < largo <= 2048:
                        raise ValueError("tamaño no válido")
                    datos = json.loads(self.rfile.read(largo))
                    cliente = str(datos["id"])[:32]
                    botones = [bool(v) for v in datos["b"]]
                    ejes = [max(-VALOR_MAX_EJE, min(VALOR_MAX_EJE, int(v)))
                            for v in datos["a"]]
                    if len(botones) != N_BOTONES_VIRTUAL or len(ejes) != len(EJES_EN_REPOSO):
                        raise ValueError("faltan botones o ejes")
                except (ValueError, KeyError, TypeError):
                    self.close_connection = True      # el cuerpo puede quedar a medias
                    return self._responder(400)
                resultado = virtual.recibir(cliente, botones, ejes)
                self._responder(CODIGOS_RESPUESTA[resultado])

            def _responder(self, codigo, cuerpo=b"", tipo=None):
                self.send_response(codigo)
                if tipo:
                    self.send_header("Content-Type", tipo)
                if codigo != 204:                     # un 204 no lleva cuerpo
                    self.send_header("Content-Length", str(len(cuerpo)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Estado", virtual.estado_robot)   # PARADO / ACTIVO
                self.send_header("X-Autonomo", "1" if virtual.modo_autonomo else "0")
                self.end_headers()
                if cuerpo:
                    self.wfile.write(cuerpo)

            def log_message(self, *args):             # no llenar la terminal
                pass

        try:
            self.servidor = ThreadingHTTPServer(("0.0.0.0", MANDO_VIRTUAL_PUERTO), Manejador)
        except OSError as error:
            print(f"[Mando digital] No se pudo abrir el puerto {MANDO_VIRTUAL_PUERTO}: {error}")
            return False

        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        print(f"[Mando digital] Ábrelo en el navegador: "
              f"http://{IP_ROBOT}:{MANDO_VIRTUAL_PUERTO}")
        return True

    def recibir(self, cliente, botones, ejes):
        """Aplica el estado que manda una página.

        Devuelve "ok" si se ha aplicado, "fisico" si manda el mando físico o
        "ocupado" si otra página tiene el control.
        """
        ahora = time.monotonic()
        with self.cerrojo:
            if self.arbitro is not None and self.arbitro.fisico_manda():
                return "fisico"
            ocupado = (self.cliente is not None and cliente != self.cliente
                       and ahora - self.ultimo_dato < TIMEOUT_MANDO_VIRTUAL)
            if ocupado:
                return "ocupado"
            if cliente != self.cliente:
                print(f"[Mando digital] Conectado ({cliente})")
                self.cliente = cliente
            self.ultimo_dato = ahora
            self._aplicar(botones, ejes)
            return "ok"

    def vigilar(self):
        """Se llama en cada ciclo: si la página calla, suelta todos los controles."""
        with self.cerrojo:
            if self.cliente is None:
                return
            if time.monotonic() - self.ultimo_dato < TIMEOUT_MANDO_VIRTUAL:
                return
            print("[Mando digital] Sin datos de la página: se sueltan los controles")
            self._aplicar([False] * N_BOTONES_VIRTUAL, EJES_EN_REPOSO)
            self.cliente = None

    def tiene_control(self):
        """True si hay una página manejando el robot ahora mismo."""
        with self.cerrojo:
            return self.cliente is not None

    def soltar_todo(self, motivo):
        """Corta la conexión de la página activa y suelta todos sus controles."""
        with self.cerrojo:
            if self.cliente is None:
                return
            print(f"[Mando digital] Desconectado: {motivo}")
            self._aplicar([False] * N_BOTONES_VIRTUAL, EJES_EN_REPOSO)
            self.cliente = None

    def _aplicar(self, botones, ejes):
        """Convierte las diferencias con el estado anterior en eventos del mando."""
        for numero, pulsado in enumerate(botones):
            if pulsado != self.botones[numero]:
                self.botones[numero] = pulsado
                self.mando.procesar_evento(TIPO_BOTON, numero, 1 if pulsado else 0)
        for numero, valor in enumerate(ejes):
            if valor != self.ejes[numero]:
                self.ejes[numero] = valor
                self.mando.procesar_evento(TIPO_EJE, numero, valor)

    def detener(self):
        """Para el servidor web."""
        if self.servidor is not None:
            self.servidor.shutdown()
            self.servidor.server_close()


# =====================================================================
# 6. SALIDA: EL ROBOT (ROS 2)
# =====================================================================
class ControlRobot(Node):
    """Nodo de ROS 2 que envía las órdenes al hardware.

    - Motores: llamadas al servicio SERVICIO_MOTORES (una por motor).
    - servo_1 (elevación de la pinza): mensajes en el topic TOPIC_SERVO_1.
    - Pinza (servo_2, apertura y cierre): mensajes en el topic TOPIC_PINZA.
    - Rotación de la pinza (servo_3): mensajes en el topic TOPIC_ROTACION_PINZA.
    - LEDs: mensajes Bool en TOPIC_LED_VERDE y TOPIC_LED_ROJO.
    - Entradas digitales (botones y finales de carrera): se suscribe a los
      topics de ENTRADAS_DIO y guarda el último nivel recibido en `entradas`.
    - LiDAR: `lidar_mm` guarda el último barrido (360 distancias en mm, una por
      grado; 0 = sin lectura). Lo rellena LidarSerie desde su propio hilo.
    """

    def __init__(self):
        super().__init__(NOMBRE_NODO)
        self.cliente_motores = self.create_client(SetData, SERVICIO_MOTORES)
        # El 10 es el tamaño de la cola de mensajes del publicador
        self.pub_servo = self.create_publisher(Float64, TOPIC_SERVO_1, 10)
        self.pub_pinza = self.create_publisher(Float64, TOPIC_PINZA, 10)
        self.pub_rotacion = self.create_publisher(Float64, TOPIC_ROTACION_PINZA, 10)
        self.pub_led_verde = self.create_publisher(Bool, TOPIC_LED_VERDE, 10)
        self.pub_led_rojo = self.create_publisher(Bool, TOPIC_LED_ROJO, 10)

        self.lidar_mm = None          # último barrido del LiDAR (None = aún no ha llegado)
        self.lidar_momento = None     # cuándo llegó

        self.entradas = {}            # nombre -> True (pin HIGH) / False (pin LOW)
        self.ultima_recepcion = {}    # nombre -> cuándo llegó el último dato
        for nombre, topic in ENTRADAS_DIO.items():
            self.create_subscription(
                Bool, topic, lambda msg, n=nombre: self._recibir_entrada(n, msg), 10)

    def _recibir_entrada(self, nombre, mensaje):
        """Se llama cuando llega el estado de un botón o final de carrera."""
        self.entradas[nombre] = bool(mensaje.data)
        self.ultima_recepcion[nombre] = time.monotonic()

    def enviar_velocidad_motor(self, motor, velocidad):
        """Fija la velocidad de UN motor y espera la respuesta del servicio."""
        if not self.cliente_motores.wait_for_service(timeout_sec=TIMEOUT_SERVICIO):
            self.get_logger().error(f'Servicio {SERVICIO_MOTORES} no disponible')
            return

        solicitud = SetData.Request()
        solicitud.params = 'set_speed'
        # El campo se llama n_encoder, pero aquí lleva el número de motor
        solicitud.initparams.n_encoder = motor
        solicitud.initparams.speed = float(velocidad)

        futuro = self.cliente_motores.call_async(solicitud)
        rclpy.spin_until_future_complete(self, futuro)   # espera la respuesta

        if futuro.result() is not None:
            self.get_logger().info(f'Motor {motor}: {futuro.result().message}')
        else:
            self.get_logger().error(f'Error al controlar el motor {motor}')

    def mover_motores(self, velocidades):
        """Envía una velocidad a cada motor. `velocidades` = (v1, v2, v3)."""
        for motor, velocidad in zip(MOTORES, velocidades):
            self.enviar_velocidad_motor(motor, velocidad)

    def mover_servo(self, velocidad):
        """Publica la velocidad de servo_1 (-100..100). 0 = parado."""
        mensaje = Float64()
        mensaje.data = float(velocidad)
        self.pub_servo.publish(mensaje)

    def mover_pinza(self, velocidad):
        """Publica la velocidad de la pinza (servo_2). 0 = parada."""
        mensaje = Float64()
        mensaje.data = float(velocidad)
        self.pub_pinza.publish(mensaje)

    def mover_rotacion_pinza(self, velocidad):
        """Publica la velocidad de rotación de la pinza (servo_3). 0 = parada."""
        mensaje = Float64()
        mensaje.data = float(velocidad)
        self.pub_rotacion.publish(mensaje)

    def mostrar_leds(self, verde, rojo):
        """Enciende o apaga los LEDs (True = encendido)."""
        for publicador, encendido in ((self.pub_led_verde, verde),
                                      (self.pub_led_rojo, rojo)):
            mensaje = Bool()
            mensaje.data = (bool(encendido) == LEDS_ACTIVOS_EN_ALTO)
            publicador.publish(mensaje)

    def detener_todo(self):
        """Para los motores del chasis y los 3 servos (y deja el LED rojo)."""
        self.mover_motores((0.0,) * len(MOTORES))
        self.mover_servo(0.0)
        self.mover_pinza(0.0)
        self.mover_rotacion_pinza(0.0)
        self.mostrar_leds(False, True)                # parado: rojo fijo


# =====================================================================
# 7. SALIDA: LA CÁMARA Y EL LIDAR (emisión por HTTP)
# =====================================================================
# Rangos de color preparados una sola vez (en cada fotograma solo se aplican).
_RANGOS_COLORES = {
    nombre: [(np.array(bajo), np.array(alto)) for bajo, alto in rangos]
    for nombre, rangos in COLORES_HSV.items()
}
_KERNEL_COLORES = np.ones((COLORES_KERNEL, COLORES_KERNEL), np.uint8)


def detectar_colores(frame):
    """Marca sobre `frame` los colores de COLORES_HSV. Modifica el fotograma.

    Para cada color busca la mancha más grande y, si su área supera
    COLORES_AREA_MINIMA, dibuja un recuadro blanco con el nombre del color.
    """
    hsv = cv2.cvtColor(cv2.GaussianBlur(frame, COLORES_DESENFOQUE, 0), cv2.COLOR_BGR2HSV)
    for nombre, rangos in _RANGOS_COLORES.items():
        mascara = None
        for bajo, alto in rangos:                    # el rojo tiene dos rangos
            parte = cv2.inRange(hsv, bajo, alto)
            mascara = parte if mascara is None else cv2.bitwise_or(mascara, parte)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, _KERNEL_COLORES)
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contornos:
            continue
        mayor = max(contornos, key=cv2.contourArea)
        if cv2.contourArea(mayor) > COLORES_AREA_MINIMA:
            x, y, ancho, alto_c = cv2.boundingRect(mayor)
            cv2.rectangle(frame, (x, y), (x + ancho, y + alto_c), (255, 255, 255), 2)
            cv2.putText(frame, nombre, (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (255, 255, 255), 2)


class ServidorMJPEG:
    """Servidor HTTP que emite como vídeo MJPEG el último fotograma JPEG que
    se le entregue con `publicar`.

    Atiende a cada navegador en un hilo propio (daemon, muere solo al cerrar
    el programa) y sabe cuántos navegadores lo están viendo.
    """

    def __init__(self, puerto, nombre):
        self.puerto = puerto
        self.nombre = nombre                  # solo para los mensajes
        self.servidor = None
        self.ultimo = None                    # último fotograma (bytes JPEG)
        self.cond = threading.Condition()     # avisa de que hay fotograma nuevo
        self.cerrojo = threading.Lock()       # protege el contador de espectadores
        self.espectadores = 0                 # navegadores conectados ahora
        self.activo = False

    def iniciar(self):
        """Abre el puerto y arranca el servidor. Devuelve True si fue bien."""
        emisor = self

        class Manejador(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type",
                                 "multipart/x-mixed-replace; boundary=frame")
                self.end_headers()
                with emisor.cerrojo:
                    emisor.espectadores += 1
                try:
                    while emisor.activo:
                        with emisor.cond:
                            emisor.cond.wait(timeout=2)
                            f = emisor.ultimo
                        if f is None:
                            continue
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg"
                                         b"\r\n\r\n" + f + b"\r\n")
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    with emisor.cerrojo:
                        emisor.espectadores -= 1

            def log_message(self, *args):     # no llenar la terminal
                pass

        try:
            self.servidor = ThreadingHTTPServer(("0.0.0.0", self.puerto), Manejador)
        except OSError as error:           # p. ej. puerto ocupado por otro programa
            print(f"[{self.nombre}] No se pudo abrir el puerto {self.puerto}: {error}")
            return False
        self.activo = True
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        return True

    def publicar(self, jpeg):
        """Entrega un fotograma nuevo (bytes JPEG) a los navegadores conectados."""
        with self.cond:
            self.ultimo = jpeg
            self.cond.notify_all()

    def hay_espectadores(self):
        """True si algún navegador está viendo esta emisión."""
        return self.espectadores > 0

    def detener(self):
        """Para el servidor y despierta a los navegadores conectados."""
        self.activo = False
        with self.cond:
            self.cond.notify_all()
        if self.servidor is not None:
            self.servidor.shutdown()
            self.servidor.server_close()


class StreamCamara:
    """Lee la cámara y la emite por HTTP en dos puertos.

      - CAMARA_PUERTO ............. imagen normal.
      - CAMARA_COLORES_PUERTO ..... la misma imagen con los colores marcados
                                    (solo si CAMARA_COLORES_ACTIVADA). Los
                                    colores solo se procesan mientras haya
                                    algún navegador viéndola.

    Un hilo propio (daemon) lee la cámara y codifica cada fotograma; cada
    emisión (ServidorMJPEG) atiende a sus navegadores en otros hilos.
    Si la cámara falla, el robot sigue funcionando sin imagen.
    """

    def __init__(self):
        self.cap = None
        self.activo = False
        self.normal = ServidorMJPEG(CAMARA_PUERTO, "Cámara")
        self.colores = (ServidorMJPEG(CAMARA_COLORES_PUERTO, "Cámara de colores")
                        if CAMARA_COLORES_ACTIVADA else None)

    def iniciar(self):
        """Abre la cámara y arranca los servidores. Devuelve True si fue bien."""
        self.cap = cv2.VideoCapture(CAMARA_INDICE, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            print(f"[Cámara] No se pudo abrir /dev/video{CAMARA_INDICE}")
            return False

        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMARA_ANCHO)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMARA_ALTO)

        if not self.normal.iniciar():
            self.cap.release()
            return False
        print(f"[Cámara] Emitiendo en http://{IP_ROBOT}:{CAMARA_PUERTO}")

        if self.colores is not None:
            if self.colores.iniciar():
                print(f"[Cámara] Reconocimiento de colores en "
                      f"http://{IP_ROBOT}:{CAMARA_COLORES_PUERTO}")
            else:
                self.colores = None        # sin colores, pero la cámara sigue

        self.activo = True
        threading.Thread(target=self._leer_camara, daemon=True).start()
        return True

    def _leer_camara(self):
        """Hilo: lee fotogramas, los gira si hace falta y los publica."""
        while self.activo:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            if CAMARA_GIRO_180:
                frame = cv2.flip(frame, -1)

            self._publicar(self.normal, frame)

            # Los colores se calculan sobre el mismo fotograma, después de
            # publicar el normal (dibujar modifica la imagen), y solo si
            # alguien está mirando.
            if self.colores is not None and self.colores.hay_espectadores():
                detectar_colores(frame)
                self._publicar(self.colores, frame)

    @staticmethod
    def _publicar(servidor, frame):
        """Codifica el fotograma en JPEG y se lo entrega a un servidor."""
        ok, jpg = cv2.imencode(".jpg", frame,
                               [cv2.IMWRITE_JPEG_QUALITY, CAMARA_CALIDAD_JPEG])
        if ok:
            servidor.publicar(jpg.tobytes())

    def detener(self):
        """Para los servidores y libera la cámara."""
        self.activo = False
        self.normal.detener()
        if self.colores is not None:
            self.colores.detener()
        time.sleep(0.1)                       # deja terminar al hilo lector
        if self.cap is not None:
            self.cap.release()


# --- Lectura del LiDAR por puerto serie (YDLIDAR) ------------------------
LIDAR_START = b"\xA5\x60"
LIDAR_STOP = b"\xA5\x65"
HEADER = b"\xAA\x55"


class DecoderLidar:
    def __init__(self):
        self.buf = bytearray()
        self.sample_size = None
        self.points = []

    def _detect_size(self):
        pos0 = self.buf.find(HEADER)
        if pos0 < 0:
            del self.buf[:-1]
            return False

        del self.buf[:pos0]

        for size in (2, 3):
            pos, count = 0, 0

            while pos + 10 <= len(self.buf):
                n = self.buf[pos + 3]
                end = pos + 10 + n * size

                if n == 0 or end + 2 > len(self.buf):
                    break

                if self.buf[end:end + 2] != HEADER:
                    break

                count += 1
                pos = end

            if count >= 2:
                self.sample_size = size
                return True

        return False

    def feed(self, data):
        self.buf.extend(data)
        completed = []

        while True:
            if self.sample_size is None:
                if not self._detect_size():
                    break

            start = self.buf.find(HEADER)

            if start < 0:
                del self.buf[:-1]
                break

            if start:
                del self.buf[:start]

            if len(self.buf) < 10:
                break

            n = self.buf[3]

            if n == 0:
                del self.buf[:2]

                if self.points:
                    completed.append(self.points)
                    self.points = []

                continue

            end = 10 + n * self.sample_size

            if len(self.buf) < end + 2:
                break

            if self.buf[end:end + 2] != HEADER:
                del self.buf[:2]
                continue

            packet = bytes(self.buf[:end])
            del self.buf[:end]

            ct = packet[2]

            fsa = ((packet[4] | packet[5] << 8) >> 1) / 64
            lsa = ((packet[6] | packet[7] << 8) >> 1) / 64

            diff = (lsa - fsa) % 360
            step = diff / (n - 1) if n > 1 else 0

            if ct & 1 and self.points:
                completed.append(self.points)
                self.points = []

            raw_samples = packet[10:]

            for i in range(n):
                sample = raw_samples[
                    i * self.sample_size:
                    (i + 1) * self.sample_size
                ]

                if self.sample_size == 2:
                    raw = sample[0] | sample[1] << 8
                else:
                    raw = sample[1] | sample[2] << 8

                distance = raw >> 2

                if distance <= 0:
                    continue

                angle = (fsa + step * i) % 360

                if self.sample_size == 2:
                    angle += math.degrees(math.atan(
                        21.8 * (155.3 - distance) /
                        (155.3 * distance)
                    ))

                self.points.append((angle % 360, distance))

            if len(self.buf) > 20000:
                del self.buf[:-2000]

        return completed


class PuertoSerie:
    """Puerto serie mínimo hecho solo con la librería estándar (os y termios),
    para no depender de pyserial. Sin paridad, 8 bits, 1 bit de parada."""

    VELOCIDADES = {115200: termios.B115200, 230400: termios.B230400}

    def __init__(self, ruta, baudios):
        if baudios not in self.VELOCIDADES:
            raise OSError(f"velocidad no soportada: {baudios}")
        self.fd = os.open(ruta, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        try:
            vel = self.VELOCIDADES[baudios]
            attrs = termios.tcgetattr(self.fd)
            attrs[0] = 0                                                  # iflag
            attrs[1] = 0                                                  # oflag
            attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL       # cflag
            attrs[3] = 0                                                  # lflag (modo crudo)
            attrs[4] = vel                                                # velocidad de entrada
            attrs[5] = vel                                                # velocidad de salida
            attrs[6][termios.VMIN] = 0
            attrs[6][termios.VTIME] = 0
            termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        except Exception:
            os.close(self.fd)
            raise

    def leer(self, maximo=4096, timeout=0.1):
        """Devuelve los bytes disponibles (espera hasta `timeout` segundos)."""
        listo, _, _ = select.select([self.fd], [], [], timeout)
        if not listo:
            return b""
        try:
            return os.read(self.fd, maximo)
        except BlockingIOError:
            return b""

    def escribir(self, datos):
        os.write(self.fd, datos)

    def vaciar_entrada(self):
        termios.tcflush(self.fd, termios.TCIFLUSH)

    def cerrar(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


class LidarSerie:
    """Lee el LiDAR por el puerto serie en un hilo propio y deja cada barrido
    en `robot.lidar_mm` (360 distancias en mm, una por grado) y
    `robot.lidar_momento`, que es lo que dibuja VisorLidar.

    Aplica LIDAR_INVERTIR_SENTIDO y LIDAR_GIRO_GRADOS a los ángulos.
    Si no se puede conectar, el robot sigue sin LiDAR.
    """

    def __init__(self, robot):
        self.robot = robot
        self.ser = None
        self.decoder = None
        self.activo = False

    def _puertos_candidatos(self):
        if LIDAR_PUERTO_SERIE:
            return [LIDAR_PUERTO_SERIE]
        return sorted(glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*'))

    def _probar(self, puerto, baudios):
        """Abre el puerto, arranca el escaneo y espera datos válidos."""
        try:
            ser = PuertoSerie(puerto, baudios)
        except (termios.error, OSError) as error:
            print(f"[LiDAR] {puerto}: {error}")
            return False
        print(f"[LiDAR] Probando {puerto} a {baudios}...")
        ser.vaciar_entrada()
        ser.escribir(LIDAR_START)
        decoder = DecoderLidar()
        limite = time.monotonic() + LIDAR_TIEMPO_CONEXION
        while time.monotonic() < limite:
            datos = ser.leer(4096)
            if datos and (decoder.feed(datos) or decoder.points):
                self.ser, self.decoder = ser, decoder
                return True
        try:
            ser.escribir(LIDAR_STOP)
            ser.cerrar()
        except Exception:
            pass
        return False

    def iniciar(self):
        """Conecta con el LiDAR y arranca el hilo. Devuelve True si fue bien."""
        for puerto in self._puertos_candidatos():
            for baudios in LIDAR_BAUDIOS:
                if self._probar(puerto, baudios):
                    print(f"[LiDAR] Conectado en {puerto} a {baudios}")
                    self.activo = True
                    threading.Thread(target=self._leer, daemon=True).start()
                    return True
        print("[LiDAR] No se pudo conectar con el LiDAR: el robot sigue sin él.")
        return False

    def _leer(self):
        while self.activo:
            try:
                datos = self.ser.leer(4096)
                if not datos:
                    continue
                for barrido in self.decoder.feed(datos):
                    self._publicar(barrido)
            except Exception as error:
                print("[LiDAR] Error leyendo:", error)
                self.activo = False

    def _publicar(self, barrido):
        """Convierte un barrido [(grados, mm)] a 360 distancias, una por grado."""
        distancias = [0] * 360
        for grados, mm in barrido:
            if not 0 < mm <= LIDAR_DISTANCIA_MAX_MM:
                continue
            if LIDAR_INVERTIR_SENTIDO:
                grados = -grados
            angulo = round(grados + LIDAR_GIRO_GRADOS) % 360
            mm = int(mm)
            if distancias[angulo] == 0 or mm < distancias[angulo]:
                distancias[angulo] = mm
        if self.robot.lidar_momento is None:
            print("[LiDAR] Recibiendo datos")
        self.robot.lidar_mm = distancias
        self.robot.lidar_momento = time.monotonic()

    def detener(self):
        """Para el escaneo y cierra el puerto."""
        self.activo = False
        time.sleep(0.15)
        try:
            self.ser.escribir(LIDAR_STOP)
            self.ser.cerrar()
        except Exception:
            pass


# La página del LiDAR. Va dentro del propio archivo, como la del mando digital.
PAGINA_LIDAR = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>LiDAR</title>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; overflow: hidden; background: #0b0e12; color: #e8ecf1;
               font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
  canvas { position: fixed; inset: 0; width: 100%; height: 100%; }
  #barra { position: fixed; top: 10px; left: 50%; transform: translateX(-50%); display: flex;
           gap: 10px; align-items: center; white-space: nowrap; z-index: 2; }
  #titulo, #estado { font-size: 14px; padding: 5px 12px; border-radius: 999px;
                     background: rgba(10, 14, 20, .75); border: 1px solid rgba(255,255,255,.2); }
  #estado::before { content: "●"; margin-right: 6px; color: #ff5d5d; }
  #estado.ok::before { color: #3ddc84; }
</style>
</head>
<body>
  <canvas id="c"></canvas>
  <div id="barra">
    <div id="titulo">LiDAR Studica - 360°</div>
    <div id="estado">Conectando…</div>
  </div>

<script>
(() => {
  'use strict';
  const lienzo = document.getElementById('c');
  const g = lienzo.getContext('2d');
  const estadoEl = document.getElementById('estado');
  let distancias = new Array(360).fill(0);   // mm, una por grado (0 = sin lectura)
  let maximo = 8000;                         // mm: radio de la gráfica

  function ajustar() {
    const d = window.devicePixelRatio || 1;
    lienzo.width = Math.round(innerWidth * d);
    lienzo.height = Math.round(innerHeight * d);
    dibujar();
  }

  function dibujar() {
    const d = window.devicePixelRatio || 1, w = lienzo.width, h = lienzo.height;
    g.clearRect(0, 0, w, h);
    const x0 = w / 2, y0 = h / 2 + 18 * d;                  // deja sitio a la barra de arriba
    const radio = Math.min(w, h - 80 * d) * 0.46;
    g.lineWidth = d;
    g.font = (11 * d) + 'px system-ui, sans-serif';
    g.fillStyle = 'rgba(255,255,255,.55)';
    g.strokeStyle = 'rgba(255,255,255,.18)';

    // Anillos de distancia (4) y sus etiquetas, en mm
    for (let i = 1; i <= 4; i++) {
      const r = radio * i / 4;
      g.beginPath(); g.arc(x0, y0, r, 0, 2 * Math.PI); g.stroke();
      g.textAlign = 'left';
      g.fillText(Math.round(maximo * i / 4) + ' mm', x0 + 4 * d, y0 - r - 3 * d);
    }

    // Radios cada 30°: 0° arriba, y los ángulos crecen en sentido horario
    for (let a = 0; a < 360; a += 30) {
      const t = a * Math.PI / 180, sx = Math.sin(t), sy = -Math.cos(t);
      g.beginPath(); g.moveTo(x0, y0); g.lineTo(x0 + radio * sx, y0 + radio * sy); g.stroke();
      g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(a + '°', x0 + (radio + 16 * d) * sx, y0 + (radio + 16 * d) * sy);
    }

    // El robot (triángulo apuntando al 0°)
    g.fillStyle = '#4da3ff';
    g.beginPath(); g.moveTo(x0, y0 - 9 * d); g.lineTo(x0 + 6 * d, y0 + 6 * d);
    g.lineTo(x0 - 6 * d, y0 + 6 * d); g.closePath(); g.fill();

    // Puntos del LiDAR (los que pasan del máximo no se dibujan)
    g.fillStyle = '#3ddc84';
    for (let a = 0; a < 360; a++) {
      const mm = distancias[a];
      if (mm <= 0 || mm > maximo) continue;
      const t = a * Math.PI / 180, r = radio * mm / maximo;
      g.fillRect(x0 + r * Math.sin(t) - 1.5 * d, y0 - r * Math.cos(t) - 1.5 * d, 3 * d, 3 * d);
    }
  }

  function mostrar(clase, texto) { estadoEl.className = clase; estadoEl.textContent = texto; }
  const dormir = ms => new Promise(r => setTimeout(r, ms));

  // Pide los datos al robot unas 10 veces por segundo
  async function bucle() {
    for (;;) {
      try {
        const r = await fetch('/datos', { cache: 'no-store' });
        const j = await r.json();
        distancias = j.d; maximo = j.max;
        if (j.ok) mostrar('ok', j.puntos + ' puntos');
        else mostrar('', j.edad === null ? 'Sin datos del LiDAR' : 'Sin datos del LiDAR desde hace ' + Math.round(j.edad) + ' s');
        dibujar();
      } catch (e) {
        mostrar('', 'Sin conexión con el robot');
        await dormir(500);
      }
      await dormir(100);
    }
  }

  addEventListener('resize', ajustar);
  ajustar();
  bucle();
})();
</script>
</body>
</html>
"""


class VisorLidar:
    """Sirve una página con la gráfica polar del LiDAR.

    - GET /       -> la página.
    - GET /datos  -> el último barrido en JSON, que la página pide ~10 veces
                     por segundo:  d = 360 distancias en mm (una por grado,
                     0 = sin lectura), ok = si los datos son recientes,
                     puntos = cuántos grados tienen lectura, edad = segundos
                     desde el último barrido (null si no ha llegado ninguno),
                     max = LIDAR_RANGO_MAX_MM.

    Los barridos los guarda LidarSerie en ControlRobot; aquí solo se leen. Corre en hilos propios (daemon): no afecta al control.
    """

    def __init__(self, robot):
        self.robot = robot
        self.servidor = None

    def _datos(self):
        """Prepara el JSON con el último barrido."""
        distancias = self.robot.lidar_mm
        momento = self.robot.lidar_momento
        if distancias is None:
            distancias, edad = [0] * 360, None
        else:
            edad = time.monotonic() - momento
        puntos = sum(1 for mm in distancias if mm > 0)
        return json.dumps({
            "d": distancias,
            "ok": edad is not None and edad < LIDAR_TIMEOUT_DATOS,
            "puntos": puntos,
            "edad": edad,
            "max": LIDAR_RANGO_MAX_MM,
        }, separators=(",", ":")).encode("utf-8")

    def iniciar(self):
        """Arranca el servidor web. Devuelve True si fue bien."""
        visor = self
        pagina = PAGINA_LIDAR.encode("utf-8")

        class Manejador(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"     # mantiene la conexión abierta
            timeout = 5                       # cierra las conexiones muertas

            def handle(self):
                try:
                    super().handle()
                except OSError:               # la pestaña se cerró: no es un error
                    pass

            def do_GET(self):
                ruta = self.path.split("?")[0]
                if ruta in ("/", "/index.html"):
                    self._responder(200, pagina, "text/html; charset=utf-8")
                elif ruta == "/datos":
                    self._responder(200, visor._datos(), "application/json")
                else:
                    self._responder(404)

            def _responder(self, codigo, cuerpo=b"", tipo=None):
                self.send_response(codigo)
                if tipo:
                    self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(cuerpo)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                if cuerpo:
                    self.wfile.write(cuerpo)

            def log_message(self, *args):     # no llenar la terminal
                pass

        try:
            self.servidor = ThreadingHTTPServer(("0.0.0.0", LIDAR_PUERTO), Manejador)
        except OSError as error:
            print(f"[LiDAR] No se pudo abrir el puerto {LIDAR_PUERTO}: {error}")
            return False
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        print(f"[LiDAR] Gráfica en http://{IP_ROBOT}:{LIDAR_PUERTO} (datos por puerto serie)")
        return True

    def detener(self):
        """Para el servidor web."""
        if self.servidor is not None:
            self.servidor.shutdown()
            self.servidor.server_close()


# =====================================================================
# 8. FUNCIONES DE CÁLCULO (no tocan ROS ni el mando: solo hacen cuentas)
# =====================================================================
def calcular_angulo(x, y):
    """Ángulo del stick en grados: 0 = arriba, 90 = derecha, 180 = abajo,
    270 = izquierda. Devuelve None si el stick está centrado."""
    if abs(x) < ZONA_MUERTA_STICK_IZQ and abs(y) < ZONA_MUERTA_STICK_IZQ:
        return None

    # "Arriba" es Y negativo, por eso se usa -y
    angulo = math.degrees(math.atan2(x, -y))
    return round(angulo % 360, 2)


def calcular_velocidades_chasis(angulo, velocidad):
    """Devuelve (v_motor1, v_motor2, v_motor3) para ir hacia donde apunta
    el stick. El círculo se divide en 4 sectores de 90 grados:

        adelante  -> de 315 a  45 grados
        derecha   -> de  45 a 135 grados
        atrás     -> de 135 a 225 grados
        izquierda -> de 225 a 315 grados
    """
    if angulo is None:                       # stick centrado: todo parado
        return (0, 0, 0)

    if angulo >= 315 or angulo < 45:         # adelante  (W)
        return (-velocidad, 0, velocidad)

    if angulo < 135:                         # derecha   (D)
        return (velocidad * CORRECCION_LATERAL, -velocidad, velocidad * CORRECCION_LATERAL)

    if angulo < 225:                         # atrás     (S)
        return (velocidad, 0, -velocidad)

    # Solo queda el sector de 225 a 315 grados
    return (-velocidad * CORRECCION_LATERAL, velocidad, -velocidad * CORRECCION_LATERAL)   # izquierda (A)


def calcular_etapa_gatillo(porcentaje):
    """Convierte lo apretado que está un gatillo (0-100 %) en una etapa: 0 si
    no llega al primer umbral de ETAPAS_GATILLO, y 1, 2 o 3 según cuántos
    umbrales alcance (con 1, 50 y 100: 3 = gatillo a fondo)."""
    return sum(1 for umbral in ETAPAS_GATILLO if porcentaje >= umbral)


def calcular_velocidades_gatillos(l2, r2, velocidad):
    """Devuelve (v1, v2, v3) según los gatillos, o None si ninguno está apretado.

    `l2` y `r2` son el porcentaje de cada gatillo (0-100).
        L2: etapa 1 (-v, 0, 0)   etapa 2 (-v, -v, 0)   etapa 3 (-v, -v, -v)
        R2: etapa 1 (0, 0, v)    etapa 2 (0, v, v)     etapa 3 (v, v, v)
    Con los dos apretados a la vez devuelve todo a cero.
    """
    etapa_l2 = calcular_etapa_gatillo(l2)
    etapa_r2 = calcular_etapa_gatillo(r2)

    if etapa_l2 == 0 and etapa_r2 == 0:
        return None
    if etapa_l2 > 0 and etapa_r2 > 0:
        return (0, 0, 0)

    if etapa_l2 > 0:
        return tuple(-velocidad if i < etapa_l2 else 0 for i in range(3))
    return tuple(velocidad if i >= 3 - etapa_r2 else 0 for i in range(3))


def calcular_despeje(distancias, rumbo):
    """Espacio libre (mm) en la dirección `rumbo` (0 = frente, 90 = derecha).

    Es la distancia del obstáculo más cercano dentro de un cono de
    ±AUTONOMO_ANCHO_GRADOS grados alrededor de esa dirección, y como mucho
    AUTONOMO_DISTANCIA_LIBRE_MM. Un 0 en `distancias` significa "sin lectura"
    y se toma como libre.
    """
    despeje = AUTONOMO_DISTANCIA_LIBRE_MM
    for grado in range(rumbo - AUTONOMO_ANCHO_GRADOS, rumbo + AUTONOMO_ANCHO_GRADOS + 1):
        distancia = distancias[grado % 360]
        if 0 < distancia < despeje:
            despeje = distancia
    return despeje


def elegir_rumbo_autonomo(distancias, rumbo_anterior):
    """Elige hacia dónde moverse en el modo autónomo.

    `distancias` son las 360 lecturas del LiDAR (mm, una por grado; 0 = sin
    lectura, 0° = frente del robot). Devuelve (rumbo, despeje): el rumbo en grados
    (0 = adelante, 90 = derecha, 180 = atrás, 270 = izquierda) y su espacio libre.
    El rumbo es None si en todas las direcciones hay algo a menos de
    AUTONOMO_DISTANCIA_PARADA_MM (el robot debe quedarse parado).

    Puntuación de cada dirección = espacio libre + una ventaja por ir hacia
    delante (AUTONOMO_PREFERENCIA_FRENTE_MM: toda hacia delante, la mitad hacia
    los lados, nada hacia atrás). Para no dudar entre dos direcciones parecidas,
    se mantiene la anterior salvo que la nueva gane por AUTONOMO_HISTERESIS_MM.
    """
    puntuaciones = {}
    for rumbo in range(0, 360, AUTONOMO_PASO_GRADOS):
        despeje = calcular_despeje(distancias, rumbo)
        ventaja = AUTONOMO_PREFERENCIA_FRENTE_MM * (1 + math.cos(math.radians(rumbo))) / 2
        puntuaciones[rumbo] = (despeje + ventaja, despeje)

    mejor = max(puntuaciones, key=lambda rumbo: puntuaciones[rumbo][0])

    anterior = puntuaciones.get(rumbo_anterior)
    if (anterior is not None and anterior[1] >= AUTONOMO_DISTANCIA_PARADA_MM
            and puntuaciones[mejor][0] < anterior[0] + AUTONOMO_HISTERESIS_MM):
        mejor = rumbo_anterior

    despeje = puntuaciones[mejor][1]
    if despeje < AUTONOMO_DISTANCIA_PARADA_MM:
        return None, despeje
    return mejor, despeje


def calcular_velocidades_rumbo(rumbo, velocidad):
    """Devuelve (v_motor1, v_motor2, v_motor3) para desplazarse hacia `rumbo`
    (0 = adelante, 90 = derecha, 180 = atrás, 270 = izquierda) sin girar.

    Mezcla los movimientos de calcular_velocidades_chasis: adelante/atrás
    (-v, 0, v) y derecha/izquierda (v*C, -v, v*C), con C = CORRECCION_LATERAL.
    Las direcciones intermedias son una combinación de las dos. Se escala para
    que la rueda más rápida vaya exactamente a `velocidad`.
    """
    radianes = math.radians(rumbo)
    derecha, adelante = math.sin(radianes), math.cos(radianes)
    v1 = -adelante + CORRECCION_LATERAL * derecha
    v2 = -derecha
    v3 = adelante + CORRECCION_LATERAL * derecha
    mayor = max(abs(v1), abs(v2), abs(v3))
    return tuple(round(v * velocidad / mayor, 3) + 0.0 for v in (v1, v2, v3))   # + 0.0: evita el -0.0


def calcular_velocidad_servo(eje):
    """Convierte la posición vertical del stick derecho (-32767..32767) en
    velocidad del servo (-VEL_SERVO_MAX..VEL_SERVO_MAX).

    Dentro de la zona muerta devuelve 0 (parado). Fuera, la velocidad crece
    de forma proporcional hasta llegar al máximo con el stick a tope.
    """
    if abs(eje) < ZONA_MUERTA_STICK_DER:
        return 0

    signo = 1 if eje > 0 else -1

    # Qué parte del recorrido útil (desde el borde de la zona muerta hasta
    # el tope del stick) lleva recorrida el stick: de 0.0 a 1.0
    recorrido_util = VALOR_MAX_EJE - ZONA_MUERTA_STICK_DER
    fraccion = (abs(eje) - ZONA_MUERTA_STICK_DER) / recorrido_util
    fraccion = min(1.0, fraccion)

    return round(signo * fraccion * VEL_SERVO_MAX * SENTIDO_SERVO)


# =====================================================================
# 9. ESTADO DEL ROBOT: START / STOP, LEDs Y FINALES DE CARRERA
# =====================================================================
PARADO = "PARADO"     # el mando no mueve nada (estado al arrancar el programa)
ACTIVO = "ACTIVO"     # en marcha: el mando controla el robot


class PanelControl:
    """Decide si el robot puede moverse, según los botones físicos.

    Dos estados:
      - PARADO (al arrancar el programa): el mando no mueve nada.
        Al pulsar START pasa a ACTIVO.
      - ACTIVO: el mando controla el robot.
        Mientras STOP esté pulsado pasa a PARADO.
    Tras un STOP hay que pulsar START otra vez: soltar STOP no reanuda.
    Si dejan de llegar datos del botón STOP (el driver falla) se pasa a PARADO,
    porque no se puede garantizar que el paro funcione.

    El botón RESET no se usa de momento.

    También enciende los LEDs según el estado (verde = en marcha, rojo =
    parado) y responde a las consultas de los finales de carrera.
    """

    def __init__(self, robot):
        self.robot = robot
        self.estado = PARADO
        self.inicio = time.monotonic()
        self.pulsado_antes = {}        # para detectar el momento exacto de pulsar
        self.fc_antes = {}             # para avisar cuando un final de carrera cambia
        self.ultimos_leds = None       # (verde, rojo) enviados la última vez
        self.momento_leds = 0.0        # cuándo se enviaron
        self.avisado_sin_stop = False
        self.avisado_faltan_datos = False

    # -----------------------------------------------------------------
    # Lectura de las entradas (contactos NO: pulsado = pin en LOW)
    # -----------------------------------------------------------------
    def _accionado(self, nombre):
        """True si el botón está pulsado / el final de carrera tocado."""
        nivel = self.robot.entradas.get(nombre)       # True = pin en HIGH
        return nivel is not None and not nivel        # sin datos = no accionado

    def fc_sup_activo(self):
        """True si el final de carrera superior está tocado."""
        return self._accionado("fc_sup")

    def fc_inf_activo(self):
        """True si el final de carrera inferior está tocado."""
        return self._accionado("fc_inf")

    def _pulsacion_nueva(self, nombre):
        """True solo en el ciclo en que se pulsa el botón (no mientras se mantiene).

        El primer dato que llega solo sirve de referencia: si el botón ya estaba
        pulsado al arrancar el programa, no cuenta como una pulsación.
        """
        if nombre not in self.robot.entradas:
            return False
        pulsado = self._accionado(nombre)
        antes = self.pulsado_antes.get(nombre)
        self.pulsado_antes[nombre] = pulsado
        return antes is False and pulsado

    # -----------------------------------------------------------------
    # Un ciclo
    # -----------------------------------------------------------------
    def actualizar(self):
        """Se llama en cada ciclo: actualiza el estado y los LEDs."""
        stop = self._accionado("stop")
        start_nuevo = self._pulsacion_nueva("start")
        self._avisar_finales_de_carrera()
        self._avisar_si_faltan_datos()

        anterior = self.estado
        if stop or self._stop_sin_datos():
            self.estado = PARADO
        elif start_nuevo:
            self.estado = ACTIVO

        if self.estado != anterior:
            print(f"[Estado] {anterior} -> {self.estado}")
        self._actualizar_leds()

    def _stop_sin_datos(self):
        """True si hace demasiado que no llega nada del botón STOP."""
        ultima = self.robot.ultima_recepcion.get("stop", self.inicio)
        sin_datos = time.monotonic() - ultima > TIMEOUT_DATOS_DIO
        if sin_datos and not self.avisado_sin_stop:
            print(f"[Panel] No llegan datos de {ENTRADAS_DIO['stop']}: el robot se para.")
            self.avisado_sin_stop = True
        elif not sin_datos:
            self.avisado_sin_stop = False
        return sin_datos

    def _avisar_si_faltan_datos(self):
        """Una sola vez, avisa de las entradas de las que no llega nada."""
        if self.avisado_faltan_datos or time.monotonic() - self.inicio < TIMEOUT_DATOS_DIO:
            return
        self.avisado_faltan_datos = True
        faltan = [topic for nombre, topic in ENTRADAS_DIO.items()
                  if nombre not in self.robot.entradas]
        if faltan:
            print("[Panel] Aún no llegan datos de: " + ", ".join(faltan))
            print("        ¿Está 'dio' activado en params.yaml y el driver en marcha?")

    def _avisar_finales_de_carrera(self):
        """Muestra un mensaje cuando un final de carrera se toca o se libera."""
        for nombre, etiqueta in (("fc_sup", "FC_SUP"), ("fc_inf", "FC_INF")):
            if nombre not in self.robot.entradas:
                continue
            activo = self._accionado(nombre)
            if activo != self.fc_antes.get(nombre, False):
                print(f"[{etiqueta}] {'alcanzado' if activo else 'liberado'}")
            self.fc_antes[nombre] = activo

    # -----------------------------------------------------------------
    # LEDs
    # -----------------------------------------------------------------
    def _actualizar_leds(self):
        """Verde fijo = en marcha | rojo fijo = parado."""
        ahora = time.monotonic()
        verde = self.estado == ACTIVO
        rojo = not verde

        # Se envía al cambiar y, además, cada cierto tiempo: así el LED se
        # corrige solo si el driver arrancó después o perdió el mensaje.
        if (verde, rojo) != self.ultimos_leds or ahora - self.momento_leds >= REFRESCO_LEDS:
            self.robot.mostrar_leds(verde, rojo)
            self.ultimos_leds = (verde, rojo)
            self.momento_leds = ahora


# =====================================================================
# 10. EL "CEREBRO": DECIDE QUÉ ENVIAR EN CADA CICLO
# =====================================================================
class ControladorManual:
    """Mira el mando y le dice al robot qué hacer.

    Para no saturar a ROS (ni la terminal) solo envía o muestra algo
    cuando el valor es distinto al del ciclo anterior. Por eso guarda
    aquí los últimos valores utilizados.

    También gestiona el MODO AUTÓNOMO (botón Options): mientras está activo,
    el chasis se mueve solo según el LiDAR en vez de seguir al mando.
    """

    def __init__(self, mando, robot, panel):
        self.mando = mando       # entrada: EstadoMando
        self.robot = robot       # salida: ControlRobot
        self.panel = panel       # estado del robot (START/STOP) y finales de carrera

        # Empiezan en None para que el primer ciclo siempre envíe algo
        # (así el robot arranca con una orden conocida: todo a cero).
        self.ultima_orden = None            # última orden enviada a los motores
        self.ultima_vel_servo = None        # última velocidad enviada a servo_1
        self.ultima_vel_pinza = None        # última velocidad enviada a la pinza
        self.ultima_vel_rotacion = None     # última velocidad enviada a la rotación (servo_3)
        self.ultimos_valores_extra = None   # último stick der. + gatillos mostrado

        # Modo autónomo
        self.autonomo = False               # ¿está activado?
        self.options_antes = False          # para detectar el momento exacto de pulsar Options
        self.rumbo_autonomo = None          # dirección elegida (None = parado)
        self.momento_lidar_usado = None     # barrido del LiDAR con el que se eligió

    def ciclo(self):
        """Un ciclo de control. Se llama una vez por vuelta del bucle."""
        self.panel.actualizar()

        # Options: se detecta el momento de pulsar (también estando parado,
        # para que una pulsación hecha antes de START no cuente después)
        options = self.mando.esta_pulsado(BOTON_AUTONOMO)
        options_nuevo = options and not self.options_antes
        self.options_antes = options

        if self.panel.estado != ACTIVO:
            self._desactivar_autonomo("el robot está parado")
            self._parar_todo()          # parado: el mando no mueve nada
            return

        x, y = self.mando.stick_izquierdo()
        angulo = calcular_angulo(x, y)

        if options_nuevo:
            if self.autonomo:
                self._desactivar_autonomo("has pulsado Options")
            else:
                self._activar_autonomo()
        elif self.autonomo and AUTONOMO_CANCELA_CON_MANDO and self._hay_orden_manual(angulo):
            self._desactivar_autonomo("has tomado el control del mando")

        if self.autonomo:
            orden = self._calcular_orden_autonomo()
        else:
            orden = self._calcular_orden_chasis(angulo)

        self._mostrar_stick_derecho_y_gatillos()
        self._actualizar_servo_1()
        self._actualizar_rotacion_pinza()
        self._actualizar_pinza()

        if MOSTRAR_ANGULO and angulo is not None:
            print(f"Ángulo: {angulo} grados")

        self._enviar_orden_chasis(orden)

    def _parar_todo(self):
        """Deja motores y servos a cero (como siempre, solo envía lo que haya
        cambiado desde el último ciclo)."""
        self._enviar_orden_chasis((0.0,) * len(MOTORES))
        self._enviar_servo_1(0)
        self._enviar_rotacion_pinza(0.0)
        self._enviar_pinza(0.0)

    # -----------------------------------------------------------------
    # Modo autónomo (botón Options)
    # -----------------------------------------------------------------
    def _lidar_disponible(self):
        """True si hay un barrido del LiDAR lo bastante reciente."""
        momento = self.robot.lidar_momento
        return (self.robot.lidar_mm is not None and momento is not None
                and time.monotonic() - momento < AUTONOMO_TIMEOUT_LIDAR)

    def _activar_autonomo(self):
        """Activa el modo autónomo, si hay datos del LiDAR."""
        if not self._lidar_disponible():
            print("[Autónomo] No se activa: no llegan datos del LiDAR.")
            return
        self.autonomo = True
        self.rumbo_autonomo = None
        self.momento_lidar_usado = None
        print(f"[Autónomo] ACTIVADO (velocidad {AUTONOMO_VELOCIDAD}). "
              f"Options otra vez, STOP o mover el mando lo desactivan.")

    def _desactivar_autonomo(self, motivo):
        """Desactiva el modo autónomo (no hace nada si ya estaba desactivado)."""
        if self.autonomo:
            self.autonomo = False
            print(f"[Autónomo] Desactivado: {motivo}.")

    def _hay_orden_manual(self, angulo):
        """True si el mando está pidiendo mover el chasis (stick izquierdo,
        R1/L1 o gatillos)."""
        l2 = self.mando.valor_gatillo(EJE_GATILLO_IZQ)
        r2 = self.mando.valor_gatillo(EJE_GATILLO_DER)
        return (angulo is not None
                or self.mando.esta_pulsado(BOTON_R1)
                or self.mando.esta_pulsado(BOTON_L1)
                or calcular_velocidades_gatillos(l2, r2, 1) is not None)

    def _calcular_orden_autonomo(self):
        """Orden de los motores en modo autónomo.

        Cada vez que llega un barrido nuevo del LiDAR se elige el rumbo más
        despejado (elegir_rumbo_autonomo); entre barridos se mantiene. Si
        faltan datos del LiDAR se desactiva el modo y se para el chasis.
        """
        if not self._lidar_disponible():
            self._desactivar_autonomo("no llegan datos del LiDAR")
            return (0.0,) * len(MOTORES)

        momento = self.robot.lidar_momento
        if momento != self.momento_lidar_usado:            # barrido nuevo
            self.momento_lidar_usado = momento
            rumbo, despeje = elegir_rumbo_autonomo(self.robot.lidar_mm, self.rumbo_autonomo)
            if rumbo != self.rumbo_autonomo:
                if rumbo is None:
                    print(f"[Autónomo] Rodeado de obstáculos (menos de "
                          f"{AUTONOMO_DISTANCIA_PARADA_MM} mm en todas partes): parado.")
                else:
                    print(f"[Autónomo] Rumbo {rumbo}° (espacio libre: {despeje} mm)")
                self.rumbo_autonomo = rumbo

        if self.rumbo_autonomo is None:
            return (0.0,) * len(MOTORES)
        return calcular_velocidades_rumbo(self.rumbo_autonomo, AUTONOMO_VELOCIDAD)

    # -----------------------------------------------------------------
    # Chasis (3 motores)
    # -----------------------------------------------------------------
    def _calcular_orden_chasis(self, angulo):
        """Decide la velocidad de los 3 motores según lo que esté pulsado.

        Prioridad: R1 (giro) > L1 (giro contrario) > gatillos L2/R2
        > stick izquierdo.

        La velocidad es la misma para el giro y para el desplazamiento:
          - normal ..................... VELOCIDAD_BASE
          - modo turbo (Círculo) ....... VELOCIDAD_BASE * FACTOR_MODO_TURBO
          - Triángulo mantenido ........ VELOCIDAD_MAXIMA (tiene prioridad sobre el turbo)
        y nunca pasa de VELOCIDAD_MAXIMA.
        """
        velocidad = VELOCIDAD_BASE
        if self.mando.toggle_activo(BOTON_MODO_TURBO):            # modo turbo
            velocidad = velocidad * FACTOR_MODO_TURBO
        if self.mando.esta_pulsado(BOTON_VELOCIDAD_MAXIMA):       # velocidad máxima
            velocidad = VELOCIDAD_MAXIMA
        velocidad = min(velocidad, VELOCIDAD_MAXIMA)

        # R1 / L1: girar sobre sí mismo
        if self.mando.esta_pulsado(BOTON_R1):
            return (velocidad, velocidad, velocidad)

        if self.mando.esta_pulsado(BOTON_L1):
            return (-velocidad, -velocidad, -velocidad)

        # Gatillos L2 / R2: ruedas por etapas según lo apretados que estén
        l2 = self.mando.valor_gatillo(EJE_GATILLO_IZQ)    # 0 a 100
        r2 = self.mando.valor_gatillo(EJE_GATILLO_DER)    # 0 a 100
        orden_gatillos = calcular_velocidades_gatillos(l2, r2, velocidad)
        if orden_gatillos is not None:
            return orden_gatillos

        # Control normal con el stick izquierdo
        return calcular_velocidades_chasis(angulo, velocidad)

    def _enviar_orden_chasis(self, orden):
        """Envía la orden a los motores, pero solo si ha cambiado."""
        if orden == self.ultima_orden:
            return

        print("Velocidades:", orden)
        self.robot.mover_motores(orden)
        self.ultima_orden = orden

    # -----------------------------------------------------------------
    # servo_1 (elevación de la pinza) con el stick derecho, eje vertical
    # -----------------------------------------------------------------
    def _actualizar_servo_1(self):
        """Mueve servo_1 según el eje vertical del stick derecho."""
        der_x, der_y = self.mando.stick_derecho()
        vel_servo = calcular_velocidad_servo(der_y)

        # Finales de carrera: no se puede seguir empujando hacia un extremo ya
        # alcanzado (stick hacia ARRIBA = Y negativo; hacia ABAJO = Y positivo).
        if vel_servo != 0:
            if der_y < 0 and self.panel.fc_sup_activo():
                vel_servo = 0
            elif der_y > 0 and self.panel.fc_inf_activo():
                vel_servo = 0

        self._enviar_servo_1(vel_servo)

    # -----------------------------------------------------------------
    # Rotación de la pinza (servo_3) con el stick derecho, eje horizontal
    # -----------------------------------------------------------------
    def _actualizar_rotacion_pinza(self):
        """Gira la pinza a velocidad fija según el eje horizontal del stick derecho.

        Con SENTIDO_ROTACION_PINZA = 1: izquierda = velocidad negativa y derecha
        = positiva; con -1 (valor actual) es al revés. Dentro de la zona muerta,
        o con el stick en el centro, se para. Es independiente del eje vertical:
        con el stick en diagonal se mueven servo_1 y servo_3 a la vez.
        """
        der_x, der_y = self.mando.stick_derecho()
        if der_x <= -ZONA_MUERTA_STICK_DER:
            vel_rotacion = -VEL_ROTACION_PINZA * SENTIDO_ROTACION_PINZA
        elif der_x >= ZONA_MUERTA_STICK_DER:
            vel_rotacion = VEL_ROTACION_PINZA * SENTIDO_ROTACION_PINZA
        else:
            vel_rotacion = 0.0
        self._enviar_rotacion_pinza(vel_rotacion)

    # -----------------------------------------------------------------
    # Pinza (servo_2): Cruz abre, Cuadrado cierra (mientras se mantiene)
    # -----------------------------------------------------------------
    def _actualizar_pinza(self):
        """Abre o cierra la pinza a velocidad fija según el botón pulsado.

        Si no hay ningún botón pulsado (o están los dos a la vez), se para.
        """
        abrir = self.mando.esta_pulsado(BOTON_PINZA_ABRIR)
        cerrar = self.mando.esta_pulsado(BOTON_PINZA_CERRAR)

        if abrir and not cerrar:
            vel_pinza = VEL_PINZA * SENTIDO_PINZA
        elif cerrar and not abrir:
            vel_pinza = -VEL_PINZA * SENTIDO_PINZA
        else:
            vel_pinza = 0.0

        self._enviar_pinza(vel_pinza)

    # -----------------------------------------------------------------
    # Envío a servo_1, rotación y pinza (solo cuando cambia el valor)
    # -----------------------------------------------------------------
    def _enviar_servo_1(self, vel_servo):
        if vel_servo != self.ultima_vel_servo:
            print(f"Servo 1: {vel_servo}")
            self.robot.mover_servo(vel_servo)
            self.ultima_vel_servo = vel_servo

    def _enviar_rotacion_pinza(self, vel_rotacion):
        if vel_rotacion != self.ultima_vel_rotacion:
            sentido = vel_rotacion * SENTIDO_ROTACION_PINZA
            estado = "a la derecha" if sentido > 0 else ("a la izquierda" if sentido < 0 else "parada")
            print(f"Rotación de la pinza: {estado} ({vel_rotacion})")
            self.robot.mover_rotacion_pinza(vel_rotacion)
            self.ultima_vel_rotacion = vel_rotacion

    def _enviar_pinza(self, vel_pinza):
        if vel_pinza != self.ultima_vel_pinza:
            estado = "abriendo" if vel_pinza * SENTIDO_PINZA > 0 else (
                "cerrando" if vel_pinza * SENTIDO_PINZA < 0 else "parada")
            print(f"Pinza: {estado} ({vel_pinza})")
            self.robot.mover_pinza(vel_pinza)
            self.ultima_vel_pinza = vel_pinza

    # -----------------------------------------------------------------
    # Solo informativo: stick derecho y gatillos
    # -----------------------------------------------------------------
    def _mostrar_stick_derecho_y_gatillos(self):
        """Muestra el stick derecho y los gatillos cuando cambian."""
        der_x, der_y = self.mando.stick_derecho()
        l2 = self.mando.valor_gatillo(EJE_GATILLO_IZQ)    # 0 a 100
        r2 = self.mando.valor_gatillo(EJE_GATILLO_DER)    # 0 a 100

        valores = (der_x, der_y, l2, r2)
        if valores != self.ultimos_valores_extra:
            print(f"Stick der: ({der_x}, {der_y}) | L2: {l2}% | R2: {r2}%")
            self.ultimos_valores_extra = valores


# =====================================================================
# 11. PROGRAMA PRINCIPAL
# =====================================================================
def main(args=None):
    rclpy.init(args=args)

    robot = ControlRobot()                           # salida: ROS
    mando = EstadoMando()                            # entrada: estado del mando
    panel = PanelControl(robot)                      # START/STOP, LEDs, finales de carrera
    controlador = ControladorManual(mando, robot, panel)    # lógica que los une
    camara = StreamCamara() if CAMARA_ACTIVADA else None
    visor_lidar = VisorLidar(robot) if LIDAR_ACTIVADO else None
    lidar = LidarSerie(robot) if LIDAR_ACTIVADO else None

    # Con mando digital, un árbitro da prioridad al mando físico
    arbitro = ArbitroMando(mando) if MANDO_DIGITAL else None
    mando_digital = MandoVirtual(mando, arbitro) if MANDO_DIGITAL else None
    if arbitro is not None:
        arbitro.digital = mando_digital
    mando_fisico = MandoFisico(arbitro if MANDO_DIGITAL else mando, arbitro)

    try:
        if camara is not None:
            camara.iniciar()           # si falla, el robot sigue sin imagen

        if lidar is not None:
            lidar.iniciar()            # si falla, el robot sigue sin LiDAR

        if visor_lidar is not None:
            visor_lidar.iniciar()      # si falla, el robot sigue sin la gráfica

        if MANDO_DIGITAL and not mando_digital.iniciar():
            print("[Mando digital] No disponible: solo funcionará el mando físico.")

        # Sin mando digital el físico es obligatorio: si falta, lanza un error
        # que se explica más abajo. Con mando digital es opcional.
        mando_fisico.conectar()
        print("Pulsa Ctrl+C para detener.")

        while rclpy.ok():
            for _ in range(SPIN_POR_CICLO):        # 0. recibir botones y finales de carrera
                rclpy.spin_once(robot, timeout_sec=0)
            mando_fisico.leer()            # 1. entrada: leer el mando físico
            if mando_digital is not None:
                mando_digital.vigilar()    #    el digital llega solo; aquí se vigila la conexión
            controlador.ciclo()            # 2. decidir y enviar al robot
            if mando_digital is not None:
                mando_digital.estado_robot = panel.estado   # la página pinta el borde rojo si PARADO
                mando_digital.modo_autonomo = controlador.autonomo   # y ilumina el botón Options
            time.sleep(PERIODO_CICLO)      # 3. pausa para no saturar la CPU

    except FileNotFoundError:
        print("No se encuentra el mando en", RUTA_MANDO)

    except PermissionError:
        print("Sin permisos para leer el mando.")
        print("Ejecuta con sudo si es necesario.")

    except OSError as error:
        # Sin mando digital: por ejemplo, si el mando se desconecta mientras se usa
        # (con mando digital, MandoFisico lo gestiona y el programa sigue)
        print("Se perdió la comunicación con el mando:", error)

    except KeyboardInterrupt:
        print("\nDeteniendo motores...")

    finally:
        # Pase lo que pase, intentamos dejar el robot parado
        try:
            robot.detener_todo()
        except Exception as error:
            print("No se pudieron detener los motores:", error)

        if camara is not None:
            camara.detener()

        if visor_lidar is not None:
            visor_lidar.detener()

        if lidar is not None:
            lidar.detener()

        if mando_digital is not None:
            mando_digital.detener()

        mando_fisico.cerrar()

        robot.destroy_node()

        # Con Ctrl+C rclpy puede haberse cerrado ya solo: no lo cerramos dos veces
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

#Codigo creado por Lander (@Juguinator)
