

import argparse
import time
import os
import logging
from pathlib import Path


from mobotix import PTController, CameraSampler
from waggle.plugin import Plugin

def loop_check(i, m):
    return m < 0 or i < m




def main(args):
    '''
        Calls sampler and mover functions 
    '''

    camera_sampler = CameraSampler(args)
    camera_scanner = PTController(args)

    loops = 0
    with Plugin() as plugin:
        while loop_check(loops, args.loops):
            for move_pos in args.preset:
                loops = loops + 1
                logging.info(f"Loop {loops} of " +
                ("infinite" if args.loops < 0 else str(args.loops)))
                frames = 0

                camera_sampler.run_sampler()

                #This move will exclude the last position but give more time for movement
                camera_scanner.move_preset_single(move_pos)

                # upload files
                for tspath in args.workdir.glob("*"):
                    if tspath.suffix == ".rgb":
                        tspath = camera_sampler.convert_rgb_to_jpg(tspath)
                        frames = frames + 1

                        # upload the file
                        logging.debug(f"Uploading {tspath}...")
                        plugin.upload_file(str(tspath))

                logging.info(f"Processed {frames} frames in loop {loops}")
                #time.sleep(2) # For safety.




if __name__ == "__main__": 
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ip",
        #required=True,
        type=str,
        dest="ip",
        default=os.getenv("CAMERA_IP", ""),
        help="Camera IP or URL",
    )
    parser.add_argument(
        "-pt",
        "--preset",
        dest="preset",
        #required=True,
        type=int, 
        default= [i for j in range(4) for i in range(j+1, 32, 4)],
        nargs="+",
        help="preset locations for scanning"
        )
    parser.add_argument(
        "-i",
        "--interval",
        dest="interval",
        type=int,
        default=os.getenv("SCAN_INTERVAL", 300),
        help="Seconds to sleep in-between full-scans",
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
        required=True,
        type=str,
        default=os.getenv("CAMERA_PASSWORD", "meinsm"),
        help="Camera Password",
    )
    args = parser.parse_args()

    
    main(args)
