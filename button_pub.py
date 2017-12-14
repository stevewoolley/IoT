#!/usr/bin/env python

import argparse
import json
import awsiot
import logging
from gpiozero import Button
from signal import pause

LOG_FILE = '/var/log/iot.log'


def pressed():
    logging.info("button_pub: button pressed on pin: {}".format(args.pin))
    message = {args.source: args.high_value}
    if args.topic is not None:
        for t in args.topic:
            publisher.publish(t, json.dumps(message))
    if args.thing is not None:
        publisher.publish(awsiot.iot_thing_topic(args.thing), awsiot.iot_payload(json.dumps(message)))


def released():
    logging.info("button_sub: button_released on pin: {}".format(args.pin))
    message = {args.source: args.low_value}
    if args.topic is not None:
        for t in args.topic:
            publisher.publish(t, json.dumps(message))
    if args.thing is not None:
        publisher.publish(awsiot.iot_thing_topic(args.thing), awsiot.iot_payload(json.dumps(message)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--endpoint", required=True, help="Your AWS IoT custom endpoint")
    parser.add_argument("-r", "--rootCA", required=True, help="Root CA file path")
    parser.add_argument("-c", "--cert", required=True, help="Certificate file path")
    parser.add_argument("-k", "--key", required=True, help="Private key file path")
    parser.add_argument("-n", "--thing", help="Targeted thing name")

    parser.add_argument("-g", "--groupCA", default=None, help="Group CA file path")
    parser.add_argument("-m", "--mqttHost", default=None, help="Targeted mqtt host")

    parser.add_argument("-t", "--topic", help="MQTT topic(s)", nargs='+', required=False)
    parser.add_argument("-l", "--log_level", help="Log Level", default=logging.INFO)

    parser.add_argument("-p", "--pin", help="gpio pin (using BCM numbering)", type=int, required=True)
    parser.add_argument("-u", "--pull_up",
                        help="If True (the default), the GPIO pin will be pulled high by default. " +
                             "In this case, connect the other side of the button to ground. " +
                             "If False, the GPIO pin will be pulled low by default. " +
                             "In this case, connect the other side of the button to 3V3",
                        type=bool, default=True)
    parser.add_argument("-s", "--source", help="Source", default="Sensor")
    parser.add_argument("-y", "--high_value", help="high value", default="high")
    parser.add_argument("-z", "--low_value", help="low value", default="low")

    args = parser.parse_args()

    logging.basicConfig(filename=LOG_FILE, level=args.log_level)

    publisher = awsiot.Publisher(args.endpoint, args.rootCA, args.cert, args.key)

    pir = Button(args.pin, pull_up=args.pull_up)

    pir.when_pressed = pressed
    pir.when_released = released

    pause()
