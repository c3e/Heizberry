#!/usr/bin/env python3

import argparse
import re
import serial
import time
import signal
import logging
import sys
import schedule
import paho.mqtt.client as mqtt
from beamer import acer as beamercodes
code = beamercodes.clubbeamer()

def on_connect(client, userdata, flags, rc):
    global beamer_state
    global input_source

    log.debug("Connected with result code " + str(rc))

    beamer_state = readBeamerState()
    client.publish("foobar/oben/cantina/beamer/status", beamer_state, qos=1, retain=True)

    input_source = readInputSource()
    client.publish("foobar/oben/cantina/beamer/source", input_source, qos=1, retain=True)

    client.subscribe("foobar/oben/cantina/beamer/action")


def on_publish(client, userdata, mid):
    log.debug("mid: "+str(mid))


def on_message(client, userdata, message):
    msg = message.payload.decode("utf-8")
    log.debug('received message: {}'.format(msg))
    if (msg == "on"):
        ser.write(code.set['on'])

    if (msg == "off"):
        ser.write(code.set['off'])

    if (msg == "vga"):
        ser.write(code.set['vga'])

    if (msg == "hdmi1"):
        ser.write(code.set['hdmi1'][0])
        time.sleep(1)
        ser.write(code.set['hdmi1'][1])

    if (msg == "hdmi2"):
        ser.write(code.set['hdmi2'][0])
        time.sleep(0.5)
        ser.write(code.set['hdmi2'][1])
        time.sleep(0.5)
        ser.write(code.set['hdmi2'][2])


def readBeamerState():
    ser.write(b"* 0 Lamp ?\r")
    read_val = ser.read(size=64)
    if(re.match(b'.*Lamp.1.*', read_val)):
        status = "on"
    else:
        status = "off"
    return status


def beamerStatusChanged():
    global beamer_state
    if (beamer_state != readBeamerState()):
        log.debug('Beamer state has changed')
        beamer_state = readBeamerState()
        return True
    else:
        return False


def readInputSource():
    ser.write(b"* 0 Src ?\r")
    read_val = ser.read(size=64)
    if(re.match(b'.*Src.0.*', read_val)):
        return "no_input"
    elif (re.match(b'.*Src.1.*', read_val)):
        return "vga"
    elif (re.match(b'.*Src.8.*', read_val)):
        return "hdmi"
    elif (readBeamerState()):
        return "off"

def inputSourceChanged():
    global input_source
    if (input_source != readInputSource()):
        log.debug('Input source has changed to {}'.format(readInputSource() ))
        input_source = readInputSource()
        return True
    else:
        return False

def terminate(signum, frame):
    log.warn('SIGTERM received. Shutting down!')
    log.info('Closing serial connection')
    ser.close()
    log.info('stopping mqtt client')
    client.loop_stop()
    log.info('disconnecting mqtt client')
    client.disconnect()
    log.info('beamerctl stopped all functions; exit')
    sys.exit(0)


def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="increase output verbosity")
    return parser.parse_args()

def periodicUpdate():
    log.debug('run scheduled statusupdates')
    client.publish("foobar/oben/cantina/beamer/status", readBeamerState(), qos=1, retain=True)
    client.publish("foobar/oben/cantina/beamer/source", readInputSource(), qos=1, retain=True)


if __name__ == '__main__':
    beamer_state = False
    input_source = False

    signal.signal(signal.SIGINT, terminate)
    args = getArgs()
    logging.basicConfig(
        level=logging.DEBUG, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    log = logging.getLogger('beamerctl')
    if args.verbose:
        log.setLevel(logging.DEBUG)
        log.info('Loglevel set to DEBUG')
    else:
        log.setLevel(logging.WARN)
    
    serialport = '/dev/ttyUSB0'

    try:
        ser = serial.Serial(port=serialport, baudrate=9600, timeout=1)
    except serial.serialutil.SerialException as e:
        log.critical(e)
        sys.exit(1)
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("10.42.0.244", 1883, 60)

    client.loop_start()

    log.debug('schedule periodic statusupdates')
    schedule.every(1).minutes.do(periodicUpdate)

    time.sleep(5)

    while True:
        schedule.run_pending()

        if (inputSourceChanged()):
            client.publish("foobar/oben/cantina/beamer/source",
                           input_source, qos=1,  retain=True) 

        if (beamerStatusChanged()):
            client.publish("foobar/oben/cantina/beamer/status",
                           beamer_state, qos=1,  retain=True)
        time.sleep(1)
