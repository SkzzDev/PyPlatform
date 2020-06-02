import _thread
import struct


class PyPlatformNetworkException(Exception):
    pass


class PyPlatformNetwork:
    def __init__(self, protocol):
        self.socket = None
        self.protocol = protocol
        self.is_connected = False

    def assign_socket(self, socket):
        self.socket = socket
        self.connection_made()

    def send_packet(self, packet):
        if self.socket is not None:
            self.socket.send(packet)
        else:
            raise PyPlatformNetworkException("No socket has been set.")

    def connection_made(self):
        self.is_connected = True
        self.protocol.connection_made()
        _thread.start_new_thread(self.thread_receive_packet, ())

    def connection_lost(self, exception=None):
        self.protocol.connection_lost(exception)

    def thread_receive_packet(self):
        if self.socket is not None:
            while True:
                try:
                    len_outer_packet_data = int(struct.unpack("!L", self.socket.recv(4))[0]) - 4
                    packet = self.socket.recv(len_outer_packet_data)
                    len_inner_packet_data = len_outer_packet_data - 4
                    self.protocol.packet_data_received(len_inner_packet_data, packet[2:-2])
                except Exception as e:
                    self.connection_lost(e)
                    break
            self.socket.close()
        else:
            raise PyPlatformNetworkException("No socket has been set.")
