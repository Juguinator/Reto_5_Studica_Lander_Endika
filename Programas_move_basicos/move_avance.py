
import rclpy
from rclpy.node import Node
from studica_control.srv import SetData


class ControlMotores(Node):

    def __init__(self):
        super().__init__('control_motores')

        self.cliente = self.create_client(
            SetData,
            '/titan0/titan_cmd'
        )

    def enviar_comando(self, motor, velocidad):
        if not self.cliente.wait_for_service(timeout_sec=3.0):
            self.get_logger().error(
                'El servicio /titan0/titan_cmd no está disponible'
            )
            return

        solicitud = SetData.Request()
        solicitud.params = 'set_speed'
        solicitud.initparams.n_encoder = motor
        solicitud.initparams.speed = float(velocidad)

        futuro = self.cliente.call_async(solicitud)
        rclpy.spin_until_future_complete(self, futuro)

        if futuro.result() is not None:
            self.get_logger().info(
                f'Motor {motor}: {futuro.result().message}'
            )
        else:
            self.get_logger().error(
                f'Error al controlar el motor {motor}'
            )


def main(args=None):
    rclpy.init(args=args)
    nodo = ControlMotores()

    try:
        # Comenzar con los tres motores detenidos
        nodo.enviar_comando(1, -1.0)
        nodo.enviar_comando(2, 0.0)
        nodo.enviar_comando(3, 1.0)

    finally:
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
