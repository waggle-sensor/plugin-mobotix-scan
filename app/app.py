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
import re
import subprocess
import sys
import time
from pathlib import Path
from select import select

import timeout_decorator
from waggle.plugin import Plugin

# camera image fetch timeout (seconds)
DEFAULT_CAMERA_TIMEOUT = 120



def loop_check(i, m):
    '''
    A unction to determine if the loop should continue based on the value of m 
    (maximum number of iterations) and i (current iteration).'''
    return m < 0 or i < m


def append_path(filename, string):
    '''
    Function takes a filename and a string and returns the filepath 
    with the string appended to the stem.
    '''
    filepath = Path(filename)
    return filepath.parent / (filepath.stem + string + filepath.suffix)

# Dictionary contains "presets" which maps preset position numbers to the 
# corresponding string for curl command for that position. 
presets = {
        1: "%FF%01%00%07%00%01%09",
        2: "%FF%01%00%07%00%02%0A",
        3: "%FF%01%00%07%00%03%0B",
        4: "%FF%01%00%07%00%04%0C",
        5: "%FF%01%00%07%00%05%0D",
        6: "%FF%01%00%07%00%06%0E",
        7: "%FF%01%00%07%00%07%0F",
        8: "%FF%01%00%07%00%08%10",
        9: "%FF%01%00%07%00%09%11",
        10: "%FF%01%00%07%00%10%18",
        11:"%FF%01%00%07%00%11%19",
        12:"%FF%01%00%07%00%12%1A",
        13:"%FF%01%00%07%00%13%1B",
        14:"%FF%01%00%07%00%14%1C",
        15:"%FF%01%00%07%00%15%1D",
        16:"%FF%01%00%07%00%16%1E",
        17:"%FF%01%00%07%00%17%1F",
        18:"%FF%01%00%07%00%18%20",
        19:"%FF%01%00%07%00%19%21",
        20:"%FF%01%00%07%00%20%28",
        21:"%FF%01%00%07%00%21%29",
        22:"%FF%01%00%07%00%22%2A",
        23:"%FF%01%00%07%00%23%2B",
        24:"%FF%01%00%07%00%24%2C",
        25:"%FF%01%00%07%00%25%2D",
        26:"%FF%01%00%07%00%26%2E",
        27:"%FF%01%00%07%00%27%2F",
        28:"%FF%01%00%07%00%28%30",
        29:"%FF%01%00%07%00%29%31",
        30:"%FF%01%00%07%00%30%38",
        31:"%FF%01%00%07%00%31%39",
        32:"%FF%01%00%07%00%32%3A"
    }


# Move to only single preset position (Does not report to the beehive)
def move_to_preset(pt_id, args):
    '''
    This function sends the curl command for the given preset position to the camera via subprocess. 
    It returns the result of the "curl" command. 
    '''
    preset_code = presets.get(pt_id)
    if not preset_code:
        print("Invalid preset number")
        return -1

    cmd = ["curl",
        "-u",
        args.user+':'+args.password,
        "-X",
        "POST",
        "http://{}/control/rcontrol?action=putrs232&rs232outtext=".format(args.ip)+preset_code]

    #print(cmd)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout

    except subprocess.CalledProcessError as e:
        print("Error: {}".format(e))
        return e

    return 0



def extract_timestamp_and_filename(path: Path):
    '''
    extracts the timestamp and filename from the given path.
    '''
    timestamp_str, filename = path.name.split("_", 1)
    timestamp = int(timestamp_str)
    return timestamp, path.with_name(filename)


def extract_resolution(path: Path) -> str:
    '''
    extracts the resolution from the given path
    '''
    return re.search("\d+x\d+", path.stem).group()


def convert_rgb_to_jpg(fname_rgb: Path):
    '''
    function converts a .rgb file to a .jpg file using ffmpeg.
    '''
    fname_jpg = fname_rgb.with_suffix(".jpg")
    image_dims = extract_resolution(fname_rgb)
    subprocess.run(
        [
            "ffmpeg",
            "-f",
            "rawvideo",
            "-pixel_format",
            "bgra",
            "-video_size",
            image_dims,
            "-i",
            str(fname_rgb),
            str(fname_jpg),
        ],
        check=True,
    )

    logging.debug("Removing %s", fname_rgb)
    fname_rgb.unlink()
    return fname_jpg


@timeout_decorator.timeout(DEFAULT_CAMERA_TIMEOUT, use_signals=False)
def get_camera_frames(args):
    cmd = [
        "/thermal-raw",
        "--url",
        args.ip,
        "--user",
        args.user,
        "--password",
        args.password,
        "--dir",
        str(args.workdir),
    ]
    logging.info(f"Calling camera interface: {cmd}")
    with subprocess.Popen(cmd, stdout=subprocess.PIPE) as process:
        while True:
            pollresults = select([process.stdout], [], [], 5)[0]
            if not pollresults:
                logging.warning("Timeout waiting for camera interface output")
                continue
            output = pollresults[0].readline()
            if not output:
                logging.warning("No data from camera interface output")
                continue
            m = re.search("frame\s#(\d+)", output.strip().decode())
            logging.info(output.strip().decode())
            if m and int(m.groups()[0]) > args.frames:
                logging.info("Max frame count reached, closing camera capture")
                return


def main(args):
    loops = 0

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
                    status = move_to_preset(move_pos, args)
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
                    get_camera_frames(args, timeout=args.camera_timeout)
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
                    if tspath.suffix == ".rgb":
                        tspath = convert_rgb_to_jpg(tspath)
                        frames = frames + 1

                    timestamp, path = extract_timestamp_and_filename(tspath)

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
