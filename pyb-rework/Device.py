'''Generic object for devices intended to be inherited.
Contains all require methods and variables for a generic device to be setup.

Use init_hardware to setup IO
Use radio_send(data) to send data
Use gps_receive to get GPS readout
Use radio_receive to receive data'''

# Import packages
import adafruit_gps
import board
import busio
import adafruit_ds3231
import time
import asyncio
import io
from Radio import *

# Initialise constants
RETRY_LIMIT = 3

#Properties
device_ID: int = None
'''Unique ID for the device. -1 = Base; 0,1,2 = Rover'''

GPS_UART: busio.UART = busio.UART(board.A1, board.A2, baudrate=115200, timeout=0.01)
'''GPS UART1 for communications'''

# GPS configured to operate on a single UART, so not longer necessary
# GPS_UART_RTCM3: busio.UART = busio.UART(board.D4, board.D5, baudrate=115200)
# '''GPS UART2 for rtcm3 communication (unidirectional towards GPS)'''

RADIO_UART: busio.UART = busio.UART(board.D11, board.D10, baudrate=9600, timeout=0.01)
'''UART bus for radio module'''

I2C: busio.I2C = board.I2C()
'''I2C bus (for RTC module)'''

RTC: adafruit_ds3231.DS3231 = adafruit_ds3231.DS3231(I2C)
'''RTC timer'''
#Immediately set alarm for 3 hrs away
RTC.alarm1 = (time.localtime(time.mktime(RTC.alarm1[0])+10800), "monthly")

'''GPS parser'''
gps_stream: io.BytesIO = io.BytesIO()
GPS: adafruit_gps.GPS = adafruit_gps.GPS(gps_stream)


async def readline_uart_async(uart: busio.UART):
    '''Magic readline wrapper that makes it async. Not thread-safe for the *same* uart'''
    timeout = uart.timeout
    uart.timeout = 0.01
    data = None
    while data is None:
        data = uart.readline()
        if data is None:
            await asyncio.sleep(0)
    uart.timeout = timeout
    return data

def validate_NMEA(raw):
    '''Validates NMEA and checks for quality 4.
    Retutrns raw data. To access the data call GPS.<ATTRIBUTE>'''
    gps_stream.flush()
    gps_stream.write(raw)

    # May need timeout
    if GPS.update():
        print("No new NMEA data")
        return None
        
    # If NMEA received back
    if GPS.fix_quality == '4':
        print("Quality 4 NMEA data received from GPS")
        return raw
    else:
        print("NMEA not quality 4")
    return None

def radio_broadcast(type: PacketType, payload: bytes):
    '''Send payload over radio'''
    print("PRE_SERIALIZE:", payload)
    raw = RadioPacket(type, payload, device_ID).serialize()
    print("BROADCASTING:", raw)
    RADIO_UART.write(raw)

def send_ack(recipient: int):
    '''Send ACK intended for given device ID'''
    radio_broadcast(PacketType.ACK, struct.pack('h', recipient))

def radio_receive():
    ''' Gets data from the radio `` \n
    Returns `RadioPacket` or `None`'''    
    # Read UART buffer until EOL
    raw = RADIO_UART.readline()
    if raw == None: raise TimeoutError

    try:
        return RadioPacket.deserialize(raw)
    except ChecksumError:
        print("FUCKED DATA:", raw)
        return None

async def async_radio_receive():
    raw = await readline_uart_async(RADIO_UART)

    try:
        print("RAWPKT:", raw)
        return RadioPacket.deserialize(raw)
    except: # Originally only ChecksumErrors but regardless of why it fails we don't want to return
        pass

def shutdown():
    # SHUTDOWN SCRIPT USING RTC I2C STUFF
    RTC.alarm2_status = False
    RTC.alarm1_status = False

def latch_on():
    pass

#ACTUAL MAIN CODE THAT RUNS ON IMPORT
# Initialise the device
#except we did that up top so :shrug: