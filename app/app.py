
import argparse
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from select import select

from mobotix import get_camera_frames
from mobotix import extract_timestamp_and_filename, convert_rgb_to_jpg
from mobotix import move_to_preset
import timeout_decorator
from waggle.plugin import Plugin

DEFAULT_CAMERA_TIMEOUT = 30

def loop_check(i, m):
    '''
    A helper function used to control the loop-scan.
        
    Returns True if i < m, where i is a loop counter 
    and m is the number of times to perform the loop-scan. 
    '''
    return m < 0 or i < m



def main(args):
    
    loops = 0
    with Plugin() as plugin:
        while loop_check(loops, args.loops):
            loops = loops + 1
            logging.info(f"Loop {loops} of " + 
                         ("infinite" if args.loops < 0 else str(args.loops)))
            frames = 0

            for move_pos in args.preset:
                # Run the Mobotix sampler
                try:
                    get_camera_frames(args, timeout=args.camera_timeout)
                except timeout_decorator.timeout_decorator.TimeoutError:
                    logging.warning(f"Timed out attempting to capture frame.")
                    sys.exit("Exit error: Camera Timeout.")
                except Exception as e:
                    logging.warning(f"Unknown exception {e}.")
                    sys.exit("Exit error: Unknown Camera Exception.")

                status = move_to_preset(move_pos, args)
                plugin.publish('mobotix.move.status', status)

                # upload files
                for tspath in args.workdir.glob("*"):
                    if tspath.suffix == ".rgb":
                        tspath = convert_rgb_to_jpg(tspath)
                        frames = frames + 1

                    timestamp, path = extract_timestamp_and_filename(tspath)
                    os.rename(tspath, path)

                    logging.debug(path)
                    logging.debug(timestamp)
                    plugin.upload_file(path, timestamp=timestamp)

            logging.info(f"Processed {frames} frames")
            if loop_check(loops, args.loops):
                logging.info(f"Sleeping for {args.loopsleep} seconds between loops")
                time.sleep(args.loopsleep)




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
        "-pt",
        "--preset",
        dest="preset",
        type=int,
        default= [i for j in range(4) for i in range(j+1, 33, 4)],
        nargs="+",
        help="preset locations for scanning"
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
        "-t",
        "--timeout",
        dest="camera_timeout",
        type=int,
        default=os.getenv("CAMERA_TIMEOUT", DEFAULT_CAMERA_TIMEOUT),
        help="Max time (in seconds) to capture frames from camera per loop",
    )
    parser.add_argument(
        "-l",
        "--loops",
        dest="loops",
        type=int,
        default=os.getenv("LOOPS", -1),
        help="Number of loops to perform. Defaults to 'infinite' (-1)",
    )
    parser.add_argument(
        "-s",
        "--loopsleep",
        dest="loopsleep",
        type=int,
        default=os.getenv("LOOP_SLEEP", 30),
        help="Seconds to sleep in-between loops",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
    )

    main(args)
