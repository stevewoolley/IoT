#!/usr/bin/env python

import json
import awsiot
import logging
import sys
import time
import platform
import datetime

try:
    import picamera
except ImportError:
    logging.error("Unable to import picamera")
    pass

RECOGNIZE = 'recognize'


def snapshot(filename):
    try:
        logging.info("snapshot: {}".format(filename))
        camera.capture(filename)
        return True
    except Exception as e:
        logging.error("snapshot failed {}".format(e.message))
        return False


def recording(filename, max_length=60, width=640, height=480, quality=23):
    try:
        logging.info("recording start: {}".format(filename))
        camera.resolution = (width, height)
        camera.start_recording(filename, format='h264', quality=quality)
        camera.wait_recording(max_length)
        camera.stop_recording()
        logging.info("recording end: {}".format(filename))
        return True
    except Exception as e:
        logging.error("snapshot failed {}".format(e.message))
        return False


def callback(client, user_data, message):
    try:
        msg = json.loads(message.payload)
    except ValueError:
        msg = None
    logging.debug("received {} {}".format(message.topic, msg))
    commands = filter(None, message.topic.replace(args.topic, '').split('/'))
    now = datetime.datetime.now()
    if len(commands) > 0:
        cmd = commands.pop(0)
        tags = {'created': awsiot.timestamp_string(now), 'source': args.source}
        if cmd == 'workspace':
            logging.debug("command: {}".format(cmd))
            filename = "{}-{}.jpg".format(args.source, awsiot.file_timestamp_string(now))
            if snapshot(filename) and args.bucket is not None:
                awsiot.mv_to_s3(filename, args.bucket, tags)
        elif cmd == 'snapshot':
            logging.debug("command: {}".format(cmd))
            filename = "{}.jpg".format(args.source)
            if snapshot(filename) and args.web_bucket is not None:
                awsiot.mv_to_s3(filename, args.web_bucket, tags)
        elif cmd == 'recording':
            logging.debug("command: {}".format(cmd))
            filename_h264 = "{}-{}.h264".format(args.source, awsiot.file_timestamp_string(now))
            filename_mp4 = "{}-{}.mp4".format(args.source, awsiot.file_timestamp_string(now))
            if recording(filename_h264) and args.archive_bucket is not None:
                awsiot.os_execute('MP4Box -add {} {}'.format(filename_h264, filename_mp4))
                awsiot.mv_to_s3(filename_mp4, args.archive_bucket, tags)
                awsiot.rm(filename_h264)
        elif cmd == RECOGNIZE:
            logging.debug("command: {}".format(cmd))
            filename = "{}-{}.jpg".format(args.source, awsiot.file_timestamp_string(now))
            if snapshot(filename) and args.bucket is not None:
                awsiot.mv_to_s3(filename, args.bucket)
                result = awsiot.recognize(filename, args.bucket)
                logging.info("{}: {}".format(RECOGNIZE, result))
                if "Labels" in result:
                    tags[RECOGNIZE] = awsiot.tagify(result['Labels'], 'Name')
                    awsiot.s3_tag(filename, args.bucket, tags)
        else:
            logging.warning('Unrecognized command: {}'.format(cmd))
    else:
        logging.warning("No commands")


if __name__ == "__main__":
    parser = awsiot.iot_arg_parser()
    parser.add_argument("-x", "--width", help="camera resolution width", type=int, default=1920)
    parser.add_argument("-y", "--height", help="camera resolution height", type=int, default=1080)
    parser.add_argument("-z", "--rotation", help="camera rotation", type=int, default=0)
    parser.add_argument("-s", "--source", help="source name", default=platform.node().split('.')[0])
    parser.add_argument("-b", "--bucket", help="S3 bucket")
    parser.add_argument("-w", "--web_bucket", help="S3 bucket for web storage")
    parser.add_argument("-a", "--archive_bucket", help="S3 bucket for archive")
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    subscriber = awsiot.Subscriber(args.endpoint, args.rootCA, args.cert, args.key, args.thing, args.groupCA)

    camera = picamera.PiCamera()
    camera.resolution = (args.width, args.height)
    camera.rotation = args.rotation

    subscriber.subscribe("{}/#".format(args.topic), callback)
    time.sleep(2)  # pause

    # Loop forever
    try:
        while True:
            time.sleep(0.5)  # sleep needed because CPU race
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
