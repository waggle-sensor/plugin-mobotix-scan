#!/usr/bin/env python3

"""
Created on Wed Mar 04 01:40:21 2023
1. This is a python class of the mobotix-move plugin that moves
Mobotix camera to a single preset position.
2. It uses the "curl" command via subprocess to send commands to the camera.
3. This is meant to perform loop-scan in coordination with Mobotix-sampler.
"""


import os
import re
import subprocess
import sys
import time

import timeout_decorator
import logging

from pathlib import Path
from select import select





class CameraSampler:
    DEFAULT_CAMERA_TIMEOUT = 120

    def __init__(self, args):
        self.args = args

    def extract_timestamp_and_filename(self, path: Path):
        timestamp_str, filename = path.name.split("_", 1)
        timestamp = int(timestamp_str)
        return timestamp, path.with_name(filename)

    def extract_resolution(self, path: Path) -> str:
        return re.search("\d+x\d+", path.stem).group()

    def convert_rgb_to_jpg(self, fname_rgb: Path):
        fname_jpg = fname_rgb.with_suffix(".jpg")
        image_dims = self.extract_resolution(fname_rgb)
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
    def get_camera_frames(self):
        cmd = [
            "/thermal-raw",
            "--url",
            self.args.ip,
            "--user",
            self.args.user,
            "--password",
            self.args.password,
            "--dir",
            str(self.args.workdir),
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
                return



    def run_sampler(self):
        '''Run the Mobotix sampler'''
        try:
            self.get_camera_frames()
        except timeout_decorator.TimeoutError:
            logging.warning(f"Timed out attempting to capture a frame.")
            sys.exit("Exit error: Camera Timeout.")
        except Exception as e:
            logging.warning(f"Unknown exception {e}.")
            sys.exit("Exit error: Unknown Camera Exception.")



class PTController:
    def __init__(self, args):
        self.ip = args.ip
        self.user = args.user
        self.password = args.password
        
        # Dictionary contains "presets" which maps preset position numbers to the corresponding string for curl command for that position.
        self.presets = {
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




    def move_to_preset(self, preset_id):
        '''
        This function sends the curl command for the given preset position to the camera via subprocess. 
        It returns the result of the "curl" command. 
        Do not call it directly as this will not publish error messages in the beehive.
        '''
        preset_code = self.presets.get(preset_id)
        if not preset_code:
            print("Invalid preset number")
            return -1

        cmd = ["curl",
            "-u",
            self.user+':'+self.password,
            "-X",
            "POST",
            "http://{}/control/rcontrol?action=putrs232&rs232outtext=".format(self.ip)+preset_code]

        #print(cmd)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            #time.sleep(3) # removing this for this application only
            return result.stdout

        except subprocess.CalledProcessError as e:
            #print("Error: {}".format(e))
            return e

        return 0

    def move_preset_single(self, preset_id):
        '''
        Moves the camera to a single preset position and publishes the camera message to the beehive.
        '''    
        status = self.move_to_preset(preset_id)
        # publish status to the beehive
        with Plugin() as plugin:
            plugin.publish('mobotix.move.status', status)


