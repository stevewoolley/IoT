#!/usr/bin/env python

import json
import awsiot
import logging
import sys
import time
import xmlrpclib
import supervisor.xmlrpc


def callback(client, user_data, message):
    logging.debug("received {} {}".format(message.topic, message))
    for topic in args.topic:
        cmd, arg = awsiot.topic_search(topic, message.topic)
        if cmd == 'getAllProcessInfo':
            logging.debug("command: {}".format(cmd))
            results = proxy.supervisor.getAllProcessInfo()
            logging.info("getAllProcessInfo {}".format(results))
            if args.thing:
                supervised = []
                for s in results:
                    supervised.append('{} ({})'.format(s['name'], s['statename']))
                publisher = awsiot.Publisher(args.endpoint, args.rootCA, args.cert, args.key)
                publisher.publish(awsiot.iot_thing_topic(args.thing),
                                  awsiot.iot_payload(awsiot.REPORTED, {'supervised': ', '.join(supervised)}))
        elif cmd == 'startProcess':
            logging.debug("command: {}".format(cmd))
            if arg:
                proxy.supervisor.startProcess(arg)
            else:
                logging.error('No argument: {}'.format(cmd, arg))
        elif cmd == 'stopProcess':
            logging.debug("command: {}".format(cmd))
            if arg:
                proxy.supervisor.stopProcess(arg)
            else:
                logging.error('No argument: {}'.format(cmd, arg))
        else:
            logging.warning('Unrecognized command: {}'.format(cmd))


if __name__ == "__main__":
    parser = awsiot.iot_arg_parser()
    parser.add_argument("--socket_path", help="socket path", default='/var/run/supervisor.sock')
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    subscriber = awsiot.Subscriber(args.endpoint, args.rootCA, args.cert, args.key)

    proxy = xmlrpclib.ServerProxy(
        'http://127.0.0.1', transport=supervisor.xmlrpc.SupervisorTransport(
            None, None, serverurl='unix://{}'.format(args.socket_path)))

    if args.topic is not None and len(args.topic) > 0:
        for t in args.topic:
            subscriber.subscribe('{}/#'.format(t.split('/').pop(0)), callback)
            time.sleep(2)  # pause

    # Loop forever
    try:
        while True:
            time.sleep(0.5)  # sleep needed because CPU race
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
