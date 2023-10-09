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
import shutil
import time
import datetime
from pathlib import Path
from select import select
import timeout_decorator

from waggle.plugin import Plugin

from MobotixControl import MobotixPT, MobotixImager

ARCHIVE_DIR = "/archive"
DEFAULT_SCAN_TIMEOUT =900

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

@timeout_decorator.timeout(DEFAULT_SCAN_TIMEOUT, use_signals=True)
def scan_presets(args):
    '''
    Runs Mobotix sampler to capture frames from the camera, 
    and uploads them to beehive. It loops through a list of preset position, moving the 
    camera to given positions. The number of loops can be specified.
    '''
    loops = 0

    # Instantiate the Mobotix PT and  camera imager class for movement of the camera
    mobot_pt = MobotixPT(args.user, args.password, args.ip)
    mobot_im = MobotixImager(args.ip, args.user, args.password, args.workdir, args.frames)

    with Plugin() as plugin:
        while loop_check(loops, args.loops):
            loops = loops + 1
            plugin.publish('loop.num', loops)
            
            scan_start = time.time()
            logging.info(f"Loop {loops} of " + ("infinite" if args.loops < 0 else str(args.loops)))
            frames = 0
            presets = parse_preset_arg(args.preset) # get a list from string

            for move_pos in presets:

                meta={'position': str(move_pos),
                    'loop_num':str(loops)}

                if presets[0]!=0:
                    # Move the camera if scan is requested
                    status = mobot_pt.move_to_preset(move_pos)

                    plugin.publish('mobotix.move.status', status)

                    if status.strip() != str('OK'):
                        scan_end = time.time()
                        plugin.publish('scan.duration.sec', scan_end-scan_start)
                        plugin.publish('exit.status', 'Scan_Error', meta=meta)
                        sys.exit(-1)

                    time.sleep(3) #For Safety
                
                # Run the Mobotix sampler
                try:
                    capture_start = time.time()
                    mobot_im.capture()
                    capture_end = time.time()
                    plugin.publish('capture.duration.sec', capture_end-capture_start)
                except Exception as e:
                    logging.warning(f"Unknown exception {e} during capture of {args.frames} frames.")
                    scan_end = time.time()
                    plugin.publish('scan.duration.sec', scan_end-scan_start)
                    plugin.publish('exit.status', str(e), meta=meta)
                    sys.exit()


                # upload files
                for tspath in args.workdir.glob("*"):
                    if tspath.suffix == ".jpg":
                        frames = frames + 1

                    timestamp, path = mobot_im.extract_timestamp_and_filename(tspath)

                    #add move position to file name
                    path=append_path(path, f'_position{move_pos}')
                    os.rename(tspath, path)

                    logging.debug(path)
                    logging.debug(timestamp)

                    
                    plugin.upload_file(path, meta=meta, timestamp=timestamp)

            scan_end = time.time()
            plugin.publish('scan.duration.sec', scan_end-scan_start)

            logging.info(f"Processed {frames} frames")
            if loop_check(loops, args.loops):
                logging.info(f"Sleeping for {args.loopsleep} seconds between loops")
                time.sleep(args.loopsleep)

        
        plugin.publish('exit.status', 'Loop_Complete')




### Functions for custom scan

def process_and_upload_files(plugin, mobot_im, args, seq_name, meta):
    for tspath in args.workdir.glob("*"):
        print('>>>>>> this file tspath -> '+str(tspath))
        timestamp, path = mobot_im.extract_timestamp_and_filename(tspath)
        time_cal = datetime.datetime.fromtimestamp(timestamp/1_000_000_000).strftime('%Y-%m-%d_%H%M%S')
        print('>>>>>> this file extracted path -> '+str(path))
        new_name = append_path(path,time_cal+seq_name)
        print('>>>>>> this file new name  -> '+str(new_name))
        os.rename(tspath, Path(new_name))
        print('>>>>>> this file renamed ')
        print(str(new_name))
        shutil.copy(new_name, os.path.join(ARCHIVE_DIR, os.path.basename(new_name)))
        plugin.upload_file(new_name, timestamp=timestamp)

def generate_imgseq_name(start_pos, image_num, move_direction, move_speed, move_duration):
    duration_ms = int(1000*move_duration)

    move_string = f"_Pt{start_pos}-{move_direction}-S{move_speed}xD{duration_ms}ms_Img{str(image_num)}"
    return move_string


def scan_custom(args, num_images, move_pos=None, move_direction="right", move_speed=5, move_duration=0.5):
    mobot_pt = MobotixPT(user='admin', passwd='wagglesage', ip='10.31.81.16')
    mobot_im = MobotixImager(user='admin', passwd='wagglesage', ip='10.31.81.16', workdir=args.workdir, frames=1)

    print(">>>>inside the capture function!")
    if move_pos is not None and move_pos != 0:
        status = mobot_pt.move_to_preset(move_pos)
        time.sleep(3)  # For Safety

    with Plugin() as plugin:
        for i in range(0, num_images):
            try:
                mobot_im.capture()
            except Exception as e:
                logging.warning(f"Exception {e} during capture.")
                sys.exit(f"Exit error: {str(e)}")
            print('>>>>>>>capturing image ' + str(i))
            mobot_pt.move(direction=move_direction, speed=move_speed, duration=move_duration)

            seq_name = generate_imgseq_name(move_pos, i, move_direction, move_speed, move_duration)
            process_and_upload_files(plugin, mobot_im, args, seq_name, meta={})
            print(">>>>Complete "+ str(i) + " loop")

    return None



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
                
            scan_custom(args,num_images=15, move_pos=3, move_direction="right", move_speed=3, move_duration=0.5)
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

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
    )

    main(args)
