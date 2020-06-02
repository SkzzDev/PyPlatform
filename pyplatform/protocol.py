import struct


class PyPlatformProtocol():
    def __init__(self, network):
        self.network = network
        self.packets_to_treat = b""

    def send_data(self, category, event, packet_data = None):  # packet_data must be binary
        final_packet_data = category.encode() + event.encode()
        if packet_data is not None:
            final_packet_data += packet_data
        packet_len = struct.pack("!L", len(final_packet_data) + 8)  # +8 because \x01\x01 (2), \x00\x00 (2), packet_len (long => 4)
        packet_sent = packet_len + b"\x01\x01" + final_packet_data + b"\x00\x00"
        try:
            self.network.send_packet(packet_sent)
        except Exception as e:
            print("[PyPlatformProtocol | Error] Couldn't send data: " + str(e))
            self.connection_lost()

        # Example
        # my_message = bytes("Je vous écris mon message úûñçËÀ!", "utf-8")
        # self.sendData("\x1A", "\x04", struct.pack("!I%dsfi??" % len(my_message), len(my_message), my_message, 45.248, 4, True, False))

    def packet_data_received(self, predicted_len_packet_data, packet_data):
        len_packet_data = len(packet_data)  # Length of all the packets remaining to treat
        if predicted_len_packet_data == len_packet_data:  # First packet in the list is the last one to treat
            category, event = packet_data[:2].decode()
            content = packet_data[2:]
            try:
                self.parse_data(category, event, content)
            except Exception as e:
                print("[PyPlatformProtocol | Error] Couldn't parse data received.")
                self.connection_lost(e)
        else:  # Packet received doesn't match its header
            pass

    # "Abstract method"
    def parse_data(self, category, event, content):
        raise NotImplementedError

    # "Abstract method"
    def connection_lost(self, exception=None):
        raise NotImplementedError

    # "Abstract method"
    def connection_made(self):
        raise NotImplementedError

    def is_connected(self):
        return self.network.is_connected
