
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

import xarray as xr

from waggle.plugin import Plugin

from MobotixControl import MobotixPT, MobotixImager

DEFAULT_SCAN_TIMEOUT =900
ARCHIVE_DIR = "/archive"

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

def process_and_upload_files(plugin, mobot_im, args, seq_name):
    if not os.path.exists(ARCHIVE_DIR):
        os.mkdir(ARCHIVE_DIR)

    for tspath in args.workdir.glob("*"):
        timestamp, path = mobot_im.extract_timestamp_and_filename(tspath)
        time_cal = datetime.datetime.fromtimestamp(timestamp/1_000_000_000).strftime('_%Y-%m-%dT%H%M%S')
        new_name = append_path(path,time_cal+seq_name)
        os.rename(tspath, Path(new_name))
        shutil.copy(new_name, os.path.join(ARCHIVE_DIR, os.path.basename(new_name)))
        plugin.upload_file(new_name, timestamp=timestamp)

def generate_imgseq_name(start_pos, image_num, move_direction, move_speed, move_duration):
    duration_ms = int(1000*move_duration)

    move_string = f"_Pt{start_pos}-{move_direction}-S{move_speed}xD{duration_ms}ms_Img{str(image_num)}"
    return move_string

@timeout_decorator.timeout(DEFAULT_SCAN_TIMEOUT, use_signals=True)
def scan_custom(args):
    mobot_pt = MobotixPT(user=args.user, passwd=args.password, ip=args.ip)
    mobot_im = MobotixImager(user=args.user, passwd=args.password, ip=args.ip, workdir=args.workdir, frames=args.frames)
    
    logging.info('entered the custom function')
    presets = parse_preset_arg(args.preset) # get a list from string
    if presets is not None and presets[0] != 0:
        for pt in presets:
            scan_start = time.time()
            status = mobot_pt.move_to_preset(pt)
            time.sleep(3)  # For Safety

            with Plugin() as plugin:
                for img in range(0, args.num_shots):
                    try:
                        mobot_im.capture()
                    except Exception as e:
                        logging.warning(f"Exception {e} during capture.")
                        sys.exit(f"Exit error: {str(e)}")
                    mobot_pt.move(direction=args.move_direction, speed=args.move_speed, duration=args.move_duration)

                    seq_name = generate_imgseq_name(presets[0], img, args.move_direction, args.move_speed, args.move_duration)
                    process_and_upload_files(plugin, mobot_im, args, seq_name)
                    logging.info(">>>>Complete "+ str(img) + " loop")

                scan_end = time.time()
                plugin.publish('scan.duration.sec', scan_end-scan_start)
                plugin.publish('exit.status', 'Loop_Complete')

    return None



### Functions for Panorama

def merge_netcdfs(archive_dir, out_filename):
    """
    Merges multiple NetCDF files in a directory into a single file.
    
    Args:
    - directory (str): The directory containing the NetCDF files.
    - output_filename (str): The name of the merged NetCDF file.
    """

    # List all .nc files in the directory
    files = [os.path.join(archive_dir, f) for f in os.listdir(archive_dir) if f.endswith('.nc')]

    # Open all datasets and concatenate along a new dimension (let's call it 'shot')
    with xr.open_mfdataset(files) as ds:
        ds.to_netcdf(out_filename)


@timeout_decorator.timeout(DEFAULT_SCAN_TIMEOUT, use_signals=True)
def scan_custom_panorama(args):
    #First scan custom
    scan_custom(args)



