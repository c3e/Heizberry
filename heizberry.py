#!/usr/bin/env python3

import argparse
import re
import time
import signal
import logging
import sys
import schedule
import paho.mqtt.client as mqtt
from eq3bt import Thermostat

thermostatBallpit = Thermostat('00:1A:22:0D:BE:EE')
thermostatCantina = Thermostat('00:1A:22:0D:C2:5D')


temperature_off = 12
temperature_on = 19


def on_connect(client, userdata, flags, rc):
    log.debug("Connected with result code " + str(rc))

    client.subscribe("foobar/oben/baellebad/heizung/action")
    client.subscribe("foobar/oben/cantina/heizung/action")

    sendReadings()


def on_publish(client, userdata, mid):
    log.debug("mid: "+str(mid))


def on_message(client, userdata, message):
    msg = message.payload.decode("utf-8")
    log.debug('received message: %s from %s', format(msg), format(message.topic))

    # Baellebad
    if (message.topic == "foobar/oben/baellebad/heizung/action"):
        thermostatBallpit.mode="manual"
        if (msg == "on"):
            thermostatBallpit.target_temperature=temperature_on
        else:
            if (msg == "off"):
                thermostatBallpit.target_temperature=temperature_off
            else:
                thermostatBallpit.target_temperature=round(float(msg),1)

    # Cantina
    if (message.topic == "foobar/oben/cantina/heizung/action"):
        thermostatCantina.mode="manual"
        if (msg == "on"):
            thermostatCantina.target_temperature=temperature_on
        else:
            if (msg == "off"):
                thermostatCantina.target_temperature=temperature_off
            else:
                thermostatCantina.target_temperature=round(float(msg),1)
    sendReadings()

def sendReadings():
    log.debug('read target temperature from thermostats')

    # Bällebad
    # Update readings
    thermostatBallpit.update()

    # Send target temperatures
    temp=thermostatBallpit.target_temperature
    client.publish("foobar/oben/baellebad/heizung/status", temp, qos=1, retain=True)
    if(temp == temperature_on):
        client.publish("foobar/oben/baellebad/heizung/status", "on", qos=1, retain=True)
    if(temp == temperature_off):
        client.publish("foobar/oben/baellebad/heizung/status", "off", qos=1, retain=True)
    
    # Cantina
    # Update readings
    thermostatCantina.update()

    # Send target temperatures
    temp=thermostatCantina.target_temperature
    client.publish("foobar/oben/cantina/heizung/status", temp, qos=1, retain=True)
    if(temp == temperature_on):
        client.publish("foobar/oben/cantina/heizung/status", "on", qos=1, retain=True)
    if(temp == temperature_off):
        client.publish("foobar/oben/cantina/heizung/status", "off", qos=1, retain=True)

        
    log.debug('sent readings')


def terminate(signum, frame):
    log.warn('SIGTERM received. Shutting down!')
    log.info('stopping mqtt client')
    client.loop_stop()
    log.info('disconnecting mqtt client')
    client.disconnect()
    log.info('heizberry stopped all functions; exit')
    sys.exit(0)


def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="increase output verbosity")
    return parser.parse_args()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, terminate)
    args = getArgs()
    logging.basicConfig(
        level=logging.DEBUG, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    log = logging.getLogger('heizberry')
    if args.verbose:
        log.setLevel(logging.DEBUG)
        log.info('Loglevel set to DEBUG')
    else:
        log.setLevel(logging.WARN)

    log.debug('start mqtt client')
    client = mqtt.Client("Heizberry_oben")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("10.42.0.244", 1883, 60)
    log.debug('connected mqtt client')

    client.loop_start()

    log.debug('schedule periodic readings')
    schedule.every(60).seconds.do(sendReadings)

    time.sleep(10)

    while True:
           schedule.run_pending()
           time.sleep(1)

