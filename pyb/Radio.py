from pyb import UART


class RadioConn:
    startDelim = b'~'
    frameID = b'\x01'
    frameType = b'\x01'
    source = b''

    radioConn = None

    def __init__(self, sourceAddr, uartAddr=0, baudrate=9600, bits=8, parity=None, stop=1, read_buf_len=512,
                 uartConn=None):
        self.source = sourceAddr
        if uartConn is not None:
            self.radioConn = uartConn
        else:
            self.radioConn = UART(baudrate, uartAddr, bits=bits, parity=parity, stop=stop, read_buf_len=read_buf_len)

    def read(self, noBits=None):
        if noBits is None:
            return self.radioConn.read()
        else:
            return self.radioConn.read(noBits)

    def sendTo(self, dest, payload, options=b'00'):
        # init new packet with start delimiter
        packet = self.getPacket(dest, options, payload)
        self.radioConn.write(packet)

    def getPacket(self, dest, options, payload):
        packet = bytearray(self.startDelim)
        if len(payload < 16):
            packet.append(0)
        packet.append(len(payload))
        # define new packet to use for checksum
        payloadPack = bytearray()
        payloadPack.extend(self.frameType)
        payloadPack.extend(self.frameID)
        # type correction for destination address (16-bit)
        if type(dest) == int and dest < 16:
            payloadPack.append(0)
            payloadPack.append(dest)
        elif type(dest) == int:
            payloadPack.append(dest & 255)  # mask to keep 16-bit
        elif type(dest) == bytes and len(dest) < 2:
            payloadPack.append(0)
            payloadPack.extend(dest & 255)  # mask to keep 16-bit
        elif type(dest) == bytes:
            payloadPack.extend(dest & 255)
        payloadPack.extend(options)
        payloadPack.extend(payload)
        payloadPack.append(radioChecksum(payloadPack))
        # append to send packet
        packet.extend(payloadPack)
        return packet


def verifyPacket(payload, crc):
    return crc == radioChecksum(payload)


# assuming packet is in same format as input... this might not be true
def parsePacket(packetBytes):
    delim = packetBytes[0]
    length = packetBytes[1:3]
    fType = packetBytes[4]
    fID = packetBytes[5]
    src = packetBytes[6:8]
    optns = packetBytes[8]
    data = packetBytes[9:-1]
    crc = packetBytes[-1]

    verified = verifyPacket(packetBytes[4:-1], crc) and delim == b'~' and length == len(packetBytes[4:-1])

    return fType, fID, src, optns, data, verified


# X-Bee checksum calculator, using bytes:
# id, type, dest, optns, payload
def radioChecksum(payload):
    return 255 - sum(payload) & 255

# \x7E\x00\x08\x01\x01\x00\x00\x00\x12\xAB\x12\x2E
# \x7E\x00\x08\x01\x01\x56\x78\x00\xAB\x12\xAB\xC7
