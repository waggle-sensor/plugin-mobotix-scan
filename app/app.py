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

def parse_preset_arg(arg):
    '''This is to handle the parsing of the string of integers.'''
    try:
        pt = [int(p) for p in arg.split(',')]
        return pt
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid preset format. Please provide comma-separated integers.")


def generate_dense_image_path(tspath, preset, image_num, direction, speed, duration):
    """
    Generate a new image path based on the provided parameters.
    """
    formatted_dir = {'right': 'r', 'left': 'l', 'up': 'u', 'down': 'd'}.get(direction, 'x')
    formatted_speed = str(speed)
    formatted_duration = f"{duration:.1f}sec"

    new_name = f"{preset}-{image_num + 1}-{formatted_dir}-{formatted_speed}-{formatted_duration}.jpg"
    new_path = tspath.parent / new_name
    
    return new_path


def capture_and_process_image(args, mobot_im, preset, image_num, direction, speed, duration):
    try:
        capture_start = time.time()
        mobot_im.capture()
        capture_end = time.time()
        duration = capture_end - capture_start
    except timeout_decorator.timeout_decorator.TimeoutError as e:
        return None, duration, "Camera_Timeout"
    except Exception as e:
        return None, duration, str(e)

    for tspath in args.workdir.glob("*"):
        if tspath.suffix == ".jpg":
            timestamp, path = mobot_im.extract_timestamp_and_filename(tspath)

            new_path = generate_dense_image_path(tspath, preset, image_num, direction, speed, duration)
            os.rename(tspath, new_path)

            return new_path, timestamp

    return 


def initialize_mobotix(args):
    mobot_pt = MobotixPT(args.user, args.password, args.ip)
    mobot_im = MobotixImager(args.ip, args.user, args.password, args.workdir, args.frames)
    return mobot_pt, mobot_im


def capture_image(mobot_im, frames):
    try:
        capture_start = time.time()
        mobot_im.capture()
        capture_end = time.time()
        return True, capture_end - capture_start
    except timeout_decorator.timeout_decorator.TimeoutError:
        logging.warning(f"Timed out attempting to capture {frames} frames.")
        return False, None
    except Exception as e:
        logging.warning(f"Unknown exception {e} during capture of {frames} frames.")
        return False, None


def process_image_for_presets(tspath, mobot_im, move_pos):
    if tspath.suffix == ".jpg":
        timestamp, path = mobot_im.extract_timestamp_and_filename(tspath)
        path = append_path(path, f'_position{move_pos}')
        os.rename(tspath, path)
        return path, timestamp
    return None, None


def upload_image(plugin, path, loop_num, position, timestamp):
    meta = {'position': str(position), 'loop_num': str(loop_num)}
    plugin.upload_file(path, meta=meta, timestamp=timestamp)


def dense_scan(args, direction, speed, duration, num_images=20):
    loops = 0
    mobot_pt, mobot_im = initialize_mobotix(args)

    with Plugin() as plugin:
        while loop_check(loops, num_images):
            loops += 1
            plugin.publish('loop.num', loops)
            scan_start = time.time()
            presets = args.preset

            status = mobot_pt.move_to_preset(presets)
            if status.strip() != "OK":
                plugin.publish('exit.status', 'Scan_Error:' + status)
                sys.exit(-1)

            frames = 0
            for image_num in range(num_images):
                success, duration = capture_image(mobot_im, args.frames)
                if success:
                    plugin.publish('capture.duration.sec', duration)
                    new_path, timestamp = process_image_for_presets(
                        next(args.workdir.glob("*")), mobot_im, presets[0])
                    if new_path:
                        frames += 1
                        upload_image(plugin, new_path, loops, presets[0], timestamp)
                mobot_pt.move(direction, speed, duration)
            
            plugin.publish('scan.duration.sec', time.time() - scan_start)
            if loop_check(loops, num_images):
                time.sleep(3)

        plugin.publish('exit.status', 'Dense_Scan_Complete')


def scan_presets(args):
    loops = 0
    mobot_pt, mobot_im = initialize_mobotix(args)

    with Plugin() as plugin:
        while loop_check(loops, args.loops):
            loops += 1
            scan_start = time.time()
            presets = parse_preset_arg(args.preset)

            for move_pos in presets:
                status = mobot_pt.move_to_preset(move_pos)
                if status.strip() != 'OK':
                    plugin.publish('exit.status', 'Scan_Error')
                    sys.exit(-1)

                time.sleep(3)
                success, duration = capture_image(mobot_im, args.frames)
                if success:
                    plugin.publish('capture.duration.sec', duration)
                    path, timestamp = process_image_for_presets(
                        next(args.workdir.glob("*")), mobot_im, move_pos)
                    if path:
                        upload_image(plugin, path, loops, move_pos, timestamp)
            
            plugin.publish('scan.duration.sec', time.time() - scan_start)
            if loop_check(loops, args.loops):
                time.sleep(args.loopsleep)

        plugin.publish('exit.status', 'Loop_Complete')


def main(args):
    # Check for the mode argument to decide which function to call
    if args.mode == "dense":
        # Set the parameters for dense_scan from args
        direction = args.direction  # Assuming direction is an argument
        speed = args.speed          # Assuming speed is an argument
        duration = args.duration    # Assuming duration is an argument
        num_images = args.num_images if hasattr(args, 'num_images') else 20  # Assuming num_images is an optional argument with default 20

        # Call the dense_scan function
        dense_scan(args, direction, speed, duration, num_images)

    elif args.mode == "preset":
        # Call the scan_presets function
        scan_presets(args)

    else:
        print("Invalid mode provided. Please use --mode dense or --mode preset.")
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
        "-pt",
        "--preset",
        dest="preset",
        type=str,
        default= default_preset(),
        help="preset locations for scanning, as a comma-separated string. (0 for non-scaning mode.)"
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

    parser.add_argument(
    "--mode",
    choices=['dense', 'preset'],
    required=True,
    help="Mode of operation: 'dense' for dense scanning, 'preset' for preset scanning."
    )

    parser.add_argument(
    "--direction",
    type=str,
    default="left",  # or whatever your default direction is
    help="Direction for dense scan mode."
    )

    parser.add_argument(
    "--speed",
    type=int,
    default=3,  # or whatever your default speed is
    help="Speed for dense scan mode."
    )

    parser.add_argument(
    "--duration",
    type=int,
    default=0.5,  # or whatever your default duration is
    help="Duration for dense scan mode."
    )



    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
    )

    main(args)
