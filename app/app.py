 #!/usr/bin/env python3
"""
Created on Mon Dec 13 11:05:11 2021

1. Runs the Mobotix C++ sampler with the given arguments.
2. The .rgb files are too large, so we used ffmpeg to convert to JPG.
3. It performs a loop through a list of camera presets to move the camera,
captures frames, and uploads them to a plugin instance.  
4. The script exits when the loop is complete.
5. Errors are logged to beehive and the loop sleeps between iterations.
"""

import argparse
import logging
import os
import sys

from pathlib import Path
from select import select
import timeout_decorator

from waggle.plugin import Plugin
from MobotixScan import scan_custom, scan_presets

ARCHIVE_DIR = "/archive"
DEFAULT_SCAN_TIMEOUT =900


def main(args):
    with Plugin() as plugin:
        if args.mode == "preset":
            try:
                scan_presets(args)
            except timeout_decorator.TimeoutError:
                logging.error(f"Unknown_Timeout")
                plugin.publish('exit.status', 'Unknown_Timeout')
                sys.exit("Exit error: Unknown_Timeout")
        elif args.mode == "custom":
            if not os.path.exists(ARCHIVE_DIR):
                os.mkdir(ARCHIVE_DIR)

            scan_custom(args)
        else:
            logging.error("Invalid scan mode. Select `--mode dense` or `--mode preset`.")
            sys.exit(-1)


def default_preset():
    '''Creating comma separated string of ints for default movement.'''
    int_list = [i for j in range(4) for i in range(j+1, 33, 4)]
    int_string = ', '.join(map(str, int_list))
    return int_string


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="The plugin runs Mobotix sampler and collects raw thermal data."
    )
    parser.add_argument("--debug", action="store_true", help="enable debug logs")
    parser.add_argument(
        "--ip",
        required=True,
        type=str,
        dest="ip",
        default=os.getenv("CAMERA_IP", ""),
        help="Camera IP or URL",
    )
    parser.add_argument(
    "--mode",
        choices=['custom', 'preset'],
        default= 'preset',
        help="Mode of operation: 'custom' scanning, 'preset' scanning."
        )
    parser.add_argument(
        "-pt",
        "--preset",
        dest="preset",
        type=str,
        default= default_preset(),
        help="""preset locations for preset scanning, as a comma-separated string. 
        Also, used as starting position for custom scan.
        (0-for non-scaning mode.)"""
    )
    
    parser.add_argument(
        "-u",
        "--user",
        dest="user",
        type=str,
        default=os.getenv("CAMERA_USER", "admin"),
        help="Camera User ID",
    )
    parser.add_argument(
        "-p",
        "--password",
        dest="password",
        type=str,
        default=os.getenv("CAMERA_PASSWORD", "meinsm"),
        help="Camera Password",
    )
    parser.add_argument(
        "-w",
        "--workdir",
        dest="workdir",
        type=Path,
        default="./data",
        help="Directory to cache Camara data before upload",
    )
    parser.add_argument(
        "-f",
        "--frames",
        dest="frames",
        type=int,
        default=os.getenv("FRAMES_PER_LOOP", 1),
        help="Frames to capture per loop",
    )
    parser.add_argument(
        "-l",
        "--loops",
        dest="loops",
        type=int,
        default=os.getenv("LOOPS", 1),
        help="Number of loops to perform. Defaults to oneshot mode (l=1).",
    )
    parser.add_argument(
        "-s",
        "--loopsleep",
        dest="loopsleep",
        type=int,
        default=os.getenv("LOOP_SLEEP", 300),
        help="Seconds to sleep in-between loops",
    )

    parser.add_argument(
        "--ptshots",
        dest="num_shots",
        type=int,
        default=15,
        help="Number of images for custom scan",
    )

    parser.add_argument(
        "--ptdir",
        dest="move_direction",
        type=str,
        choices=["left", "right", "up", "down"],
        default="right",
        help="Direction to move: 'left' or 'right' are preffered.",
    )

    parser.add_argument(
        "--ptspeed",
        dest="move_speed",
        type=int,
        default=3,
        help="Speed to move",
    )

    parser.add_argument(
        "--ptdur",
        dest="move_duration",
        type=float,
        default=0.5,
        help="Duration to move",
    )


    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
    )

    main(args)
