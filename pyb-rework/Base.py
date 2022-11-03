'''
Base, inheriting from Device, is an object to represent base stations. This contains 
'''

import time
from Device import * #EVERYTHING FROM THIS IS READONLY (you can use write functions, but cannot actually modify a variable)
import Device #USE THIS TO MODIFY VARIABLES (e.g. Device.device_ID = 1, not device_ID = 1)
from Radio import *
import asyncio

ROVER_COUNT = 3

GSM_UART: busio.UART = busio.UART(board.A5, board.D6, baudrate=9600)

class GPSData:
    lat: float
    long: float
    temperature: int
    timestamp: int

    def __init__(self, lat, long, temperature, timestamp):
        self.lat = lat
        self.long = long
        self.temperature = temperature
        self.timestamp = timestamp

#this is a global variable so i can still get the data even if the rover loop times out
rover_data: dict[int, GPSData] = {}
for i in range(ROVER_COUNT):
        rover_data[i] = None

def get_corrections():
    '''Returns the corrections from the GPS as a bytearray'''
    # Read UART for newline terminated data - produces bytestr
    return GPS_UART.readline()
    # TODO: add timeout

async def rtcm3_loop():
    '''Runs continuously but in parallel. Attempts to send GPS uart readings every second (approx.)'''
    print("Beginning rtcm3_loop")
    while None in rover_data.values(): #Finish running when rover data is done
        print("Getting RTCM3 and broadcasting...\r\n")
        gps_data = await readline_uart_async(GPS_UART)
        print("GPS Raw bytes:", gps_data)
        radio_broadcast(PacketType.RTCM3, gps_data) #pls no break TODO: timeout for hw failure
        print("Corrections sent \r\n")
        await asyncio.sleep(1)
    print("End RTCM3 Loop")

async def rover_data_loop():
    print("Beginning rover_data_loop")
    while not None in rover_data:
        packet = await async_radio_receive()
        if packet.type == PacketType.NMEA:
            print("Received NMEA...\r\n")
            if not rover_data[packet.sender]:
                print("Received NMEA from a new rover,", packet.sender, "\r\n")
                raw = validate_NMEA(packet.payload)
                if raw != None:
                    rover_data[packet.sender] = GPSData(GPS.latitude, GPS.longitude, 0, GPS.timestamp_utc)
            
            if rover_data[packet.sender]:
                print("Sending ACK to rover", packet.sender, "\r\n")
                send_ack(packet.sender)


if __name__ == "__main__":
    Device.device_ID = 0
    #Base needs to:
    #Get RTCM3 correction.
    #Send RTCM3 data
    #Receive packet
    #If GPS data received:
    # If rover not already received, store GPS data.
    # Send ACK to rover
    #end
    try:
        print("Begin ASYNC...")
        asyncio.run(asyncio.wait_for(asyncio.gather(rover_data_loop(), rtcm3_loop()), ROVER_COMMS_TIMEOUT))
        print("Finished ASYNC...")
    except TimeoutError:
        print("Timeout!")
        pass #Don't care, we have data, just send what we got

    # print("Begin ASYNC...")
    # # loop.create_task(rover_data_loop())
    # # loop.create_task(rtcm3_loop())
    # # loop.run_forever()
    # print("Finished ASYNC...")