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
import time
from pathlib import Path
from select import select

import timeout_decorator
from waggle.plugin import Plugin

from MobotixControl import MobotixPT, MobotixImager

def loop_check(i, m):
    '''
    A function to determine if the loop should continue based on the value of m 
    (maximum number of iterations) and i (current iteration).'''
    return m < 0 or i < m


def append_path(filename, string):
    '''
    Function takes a filename and a string and returns the filepath 
    with the string appended to the stem.
    '''
    filepath = Path(filename)
    return filepath.parent / (filepath.stem + string + filepath.suffix)


def main(args):
    loops = 0

    # Instantiate the MobotixControl and  mobotix camera class for movement of the camera
    mobot_pt = MobotixPT(args.user, args.password, args.ip)
    mobot_im = MobotixImager(args.ip, args.user, args.password, args.workdir, args.frames)

    with Plugin() as plugin:
        while loop_check(loops, args.loops):
            loops = loops + 1
            plugin.publish('loop.num', loops)
            
            scan_start = time.time()
            logging.info(f"Loop {loops} of " + ("infinite" if args.loops < 0 else str(args.loops)))
            frames = 0

            for move_pos in args.preset:
                if args.preset[0]!=0:
                    # Move the caemra if scan is requested
                    status = mobot_pt.move_to_preset(move_pos)

                    plugin.publish('mobotix.move.status', status)

                    if status.strip() != str('OK'):
                        scan_end = time.time()
                        plugin.publish('scan.duration.sec', scan_end-scan_start)
                        plugin.publish('exit.status', 'Scan_Error')
                        sys.exit(-1)

                    time.sleep(3) #For Safety
                
                # Run the Mobotix sampler
                try:
                    capture_start = time.time()
                    mobot_im.capture()
                    capture_end = time.time()
                    plugin.publish('capture.duration.sec', capture_end-capture_start)
                except timeout_decorator.timeout_decorator.TimeoutError:
                    logging.warning(f"Timed out attempting to capture {args.frames} frames.")
                    scan_end = time.time()
                    plugin.publish('scan.duration.sec', scan_end-scan_start)
                    plugin.publish('exit.status', 'Camera_Timeout')
                    sys.exit("Exit error: Camera Timeout.")
                except Exception as e:
                    logging.warning(f"Unknown exception {e} during capture of {args.frames} frames.")
                    scan_end = time.time()
                    plugin.publish('scan.duration.sec', scan_end-scan_start)
                    plugin.publish('exit.status', e)
                    sys.exit("Exit error: Unknown Camera Exception.")


                # upload files
                for tspath in args.workdir.glob("*"):
                    if tspath.suffix == ".jpg":
                        frames = frames + 1

                    timestamp, path = mobot_im.extract_timestamp_and_filename(tspath)

                    #add move position to file name
                    path=append_path(path, '_position'+str(move_pos))
                    os.rename(tspath, path)

                    logging.debug(path)
                    logging.debug(timestamp)


                    meta={'position': str(move_pos),
                          'loop_num':str(loops)}
                    
                    plugin.upload_file(path, meta=meta, timestamp=timestamp)

            scan_end = time.time()
            plugin.publish('scan.duration.sec', scan_end-scan_start)

            logging.info(f"Processed {frames} frames")
            if loop_check(loops, args.loops):
                logging.info(f"Sleeping for {args.loopsleep} seconds between loops")
                time.sleep(args.loopsleep)

        
        plugin.publish('exit.status', 'Loop_Complete')



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
        help="preset locations for scanning. (0 for non-scaning mode .)"
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
        default=os.getenv("LOOPS", -1),
        help="Number of loops to perform. Defaults to 'infinite' (-1)",
    )
    parser.add_argument(
        "-s",
        "--loopsleep",
        dest="loopsleep",
        type=int,
        default=os.getenv("LOOP_SLEEP", 300),
        help="Seconds to sleep in-between loops",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
    )

    main(args)
