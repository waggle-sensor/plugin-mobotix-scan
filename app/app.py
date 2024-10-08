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
from MobotixScan import scan_custom, scan_presets, calculate_pt



def main(args):
    with Plugin() as plugin:
        if args.mode == "preset":
            try:
                scan_presets(args)
            except timeout_decorator.TimeoutError:
                logging.error(f"Unknown_Timeout")
                plugin.publish('exit.status', 'Unknown_Timeout')
                sys.exit("Exit error while scanning presets: Unknown_Timeout")
        elif args.mode == "custom":
            try:
                scan_custom(args)
            except timeout_decorator.TimeoutError:
                logging.error(f"Unknown_Timeout")
                plugin.publish('exit.status', 'Unknown_Timeout')
                sys.exit("Exit error while scanning custom: Unknown_Timeout")
        elif args.mode == 'direction':
            try:
                directions_clean = args.preset.replace(' ', '')
                directions_list = directions_clean.split(',')

                args.preset=calculate_pt(args.south, args.preset)
                presets_list = args.preset.replace(' ', '').split(',')
                args.directions = dict(zip(presets_list, directions_list))

                logging.info(args.preset)
                scan_presets(args)
            except timeout_decorator.TimeoutError:
                logging.error(f"Unknown_Timeout")
                plugin.publish('exit.status', 'Unknown_Timeout')
                sys.exit("Exit error while scanning direction: Unknown_Timeout")
            except ValueError as e:
                plugin.publish('exit.status', "Unknown_Direction.")
                raise(e)
        else:
            logging.error("Invalid scan mode. Select `--mode custom` or `--mode preset`.")
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
        choices=['preset', 'custom', 'direction'],
        default= 'preset',
        help="Mode of operation: 'custom' scanning, 'preset' scanning, 'direction' scanning."
        )
    parser.add_argument(
        "-pt",
        "--preset",
        dest="preset",
        type=str,
        default= default_preset(),
        help="""preset locations for preset or direction scanning mode, as a comma-separated string. 
        Also, used as starting position for custom scan. F
        or `direction` mode it is direction locations for scanning, as a comma-separated string.
        Values are of the form XS, XH, XB, and XG, where X = N,S,E,W,NE,SW,SE,NW.
        (0-for non-scanning mode.)"""
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
        type=str,
        default=15,
        help="Number of images for custom scan. Repeat for each preset.",
    )

    parser.add_argument(
        "--ptdir",
        dest="move_direction",
        type=str,
        choices=["left", "right", "up", "down"],
        default="right",
        help="Direction to move: 'left' or 'right' are preffered. Do not repeat for each preset.",
    )

    parser.add_argument(
        "--ptspeed",
        dest="move_speed",
        type=str,
        default=3,
        help="Speed to move. Repeat for each preset.",
    )

    parser.add_argument(
        "--ptdur",
        dest="move_duration",
        type=str,
        default=500,
        help="Duration to move in nano-seconds. Repeat for each preset.",
    )

    parser.add_argument(
        "-south",
        "--southdirection",
        dest="south",
        type=str,
        default= '1', # consider a default of 1, i.e. Plane Zero is pointed south.
        help="""A Camera preset value that points the camera toward the south."""
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
    )

    main(args)
