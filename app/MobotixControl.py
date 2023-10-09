import subprocess
import time
import datetime


import logging
import re
import subprocess
from pathlib import Path
from select import select


# for netcdf and plot
import numpy as np
#import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

from waggle.plugin import Plugin

# camera image fetch timeout (seconds)
DEFAULT_CAMERA_TIMEOUT = 30

# camera move timeout (seconds)
DEFAULT_MOVEMENT_TIMEOUT = 30

class MobotixPT:
    ''' A class representing Mobotix Pan-Tilt camera control.

    Parameters:
        user (str): Camera user ID.
        passwd (str): Camera password.
        ip (str): Camera IP or URL.
    '''
    def __init__(self, user, passwd, ip):
        self.user = user
        self.passwd = passwd
        self.ip = ip
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
        

        self.speed_codes = {
            'right': {
                 1: '%FF%01%00%02%01%00%04',
                 2: '%FF%01%00%02%0F%00%12',
                 3: '%FF%01%00%02%1F%00%22',
                 4: '%FF%01%00%02%2F%00%32',
                 5: '%FF%01%00%02%FF%00%02'
            },
            'left': {
                1: '%FF%01%00%04%01%00%06',
                2: '%FF%01%00%04%0F%00%14',
                3: '%FF%01%00%04%1F%00%24',
                4: '%FF%01%00%04%2F%00%34',
                5: '%FF%01%00%04%FF%00%04'
            },
            'up': {
                1: '%FF%01%00%08%00%01%0A',
                2: '%FF%01%00%08%00%0F%18',
                3: '%FF%01%00%08%00%1F%28', 
                4: '%FF%01%00%08%00%2F%38',
                5: '%FF%01%00%08%00%FF%08'
            },
            'down': {
                1: '%FF%01%00%10%00%01%12',
                2: '%FF%01%00%10%00%0F%20',
                3: '%FF%01%00%10%00%1F%30',
                4: '%FF%01%00%10%00%2F%40',
                5: '%FF%01%00%10%00%FF%10'
            }
        }


    def _send_command(self, code):
        cmd = ["curl",
               "-u",
               f"{self.user}:{self.passwd}",
               "-X",
               "POST",
               f"http://{self.ip}/control/rcontrol?action=putrs232&rs232outtext={code}"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=DEFAULT_MOVEMENT_TIMEOUT, text=True)
            
            if result.stdout.strip() != 'OK':
                logging.warning('PT unit did not respond with OK')
                raise Exception(f"INVALID_CREDENTIALS_OR_CONNECTION_ERROR:{result.stdout}")
            else:
                return result.stdout

        except subprocess.TimeoutExpired as e:
            logging.error("Error: {}".format(e))
            return e
        except subprocess.CalledProcessError as e:
            logging.error("Error: {}".format(e))
            return e

    def move_to_preset(self, pt_id):
        '''Moves the camera to the specified preset location.'''
        preset_code = self.presets.get(pt_id)
        if preset_code:
            return self._send_command(preset_code)
        else:
            return "Invalid preset ID."

    def move(self, direction, speed, duration):
        '''
        Moves the camera in the specified direction at the
          given speed and duration.'''
        code = self.speed_codes[direction].get(speed)
        if code:
            self._send_command(code)
            time.sleep(duration)
            self.stop()
        else:
            return "Invalid code value for movement."
        

    def stop(self):
        '''Stops the camera movement.'''
        code = '%FF%01%00%00%00%00%01'
        return self._send_command(code)

    def remote_reset(self):
        '''Remote reset of the camera moves it to home position.'''
        code = '%FF%01%00%0F%00%00%10'
        return self._send_command(code)





class MobotixImager():
    ''' A class for capturing frames and processsing image data.

    Parameters:
        ip (str): Camera IP or URL.
        user (str): Camera user ID.
        passwd (str): Camera password.
        workdir (str or Path): Directory to cache camera data before publishing to beehive.
        frames (int): Number of frames to capture in each attempt.
'''
    def __init__(self, ip, user, passwd, workdir, frames):
        super().__init__()
        self.ip = ip
        self.user = user
        self.password = passwd
        self.workdir = Path(workdir)
        self.frames = frames

    def extract_timestamp_and_filename(self, path: Path):
        '''Extracts timestamp and filename from mobotix file path.'''
        timestamp_str, filename = path.name.split("_", 1)
        timestamp = int(timestamp_str)
        return timestamp, path.with_name(filename)

    def extract_resolution(self, path: Path):
        '''Extracts image resolution from the file name.'''
        return re.search("\d+x\d+", path.stem).group()

    def convert_rgb_to_jpg(self, fname_rgb: Path):
        fname_jpg = fname_rgb.with_suffix(".jpg")
        image_dims = self.extract_resolution(fname_rgb)
        try:
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
                timeout=60
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"Error converting RGB to JPG: {e}")
            raise

        logging.info("Removing %s", fname_rgb)
        fname_rgb.unlink()
        return fname_jpg
    

    
    def read_metadata_and_data(self, file_path):
        with file_path.open('r') as f:
            lines = f.readlines()

        metadata = {}
        for line in lines[:7]:  # Assuming metadata is the first 7 lines
            key, value = line.strip().split(';')
            metadata[key] = value

        temperature_data = [list(map(float, line.split(';'))) for line in lines[8:]]
        return metadata, np.array(temperature_data)

    def convert_to_dataset(self, metadata, temperature_data, time):
        height, width = int(metadata['height']), int(metadata['width'])
        ds = xr.Dataset(
            {'temperature': (['time', 'y', 'x'], temperature_data[np.newaxis, :, :])},
            coords={
                'time': [time],
                'y': np.arange(height),
                'x': np.arange(width)
            }
        )

        time_cal = datetime.datetime.fromtimestamp(time).strftime('%d %b %Y %H:%M:%S UTC')
        ds['time'].attrs['strftime']=time_cal
        ds['time'].attrs['units']= 'seconds since 1970-01-01 00:00:00 UTC'

        for key, value in metadata.items():
            ds.attrs[key] = value
        return ds

    def save_to_netcdf(self, ds, file_path):
        output_filename = file_path.with_suffix(".nc")
        ds.to_netcdf(output_filename)
        return output_filename

    def plot_data(self, ds, file_path):
        fig, ax = plt.subplots(figsize=(8, 5))
        ds.temperature.squeeze().plot(ax=ax, cmap='turbo', yincrease=False)
        plot_filename = file_path.with_name(f"{file_path.stem}_plot.jpg")
        fig.savefig(plot_filename)
        return plot_filename

    def csv_to_netcdf(self, file_path):

        try:
            metadata, temperature_data = self.read_metadata_and_data(file_path)
            time, _ = self.extract_timestamp_and_filename(file_path)
            ds = self.convert_to_dataset(metadata, temperature_data, time/1000000000)
            nc_filename = self.save_to_netcdf(ds, file_path)
            plot_filename = self.plot_data(ds, file_path)
            logging.info(f"File saved as {nc_filename}")
            logging.info(f"Plot saved as {plot_filename}")
        except Exception as e:
            logging.error(f"Error in converting CSV to NetCDF: {e}")
            raise

        return


    


    def get_camera_frames(self):
        '''Calls the camera interface to capture frames and 
        stores them in the working directory.
        '''

        cmd = [
            "/thermal-raw",
            "--url",
            self.ip,
            "--user",
            self.user,
            "--password",
            self.password,
            "--dir",
            str(self.workdir),
        ]
        logging.info(f"Calling camera interface: {cmd}")

        start_time = time.time()
        
        try:
            with subprocess.Popen(cmd, stdout=subprocess.PIPE) as process:
                while True:
                    pollresults = select([process.stdout], [], [], 5)[0]

                    if time.time() - start_time > DEFAULT_CAMERA_TIMEOUT:
                        logging.exception("Camera timeout.")
                        raise Exception("Camera timeout.")
                    elif not pollresults:
                        logging.info("Timeout waiting for camera interface output")
                        continue

                    output = pollresults[0].readline()
                    if not output:
                        logging.warning("No data from camera interface output")
                        continue
                    m = re.search("frame\s#(\d+)", output.strip().decode())
                    logging.info(output.strip().decode())
                    if m and int(m.groups()[0]) >= self.frames:
                        logging.info("Max frame count reached, closing camera capture")
                        return
                    
        except Exception as e:
            logging.exception("Camera plugin encountered an error: %s", str(e))
            raise

    def capture(self):
        '''Captures frames from the camera, converts them to JPG, 
        and stores them in the working directory.'''
        try:
            self.workdir.mkdir(parents=True, exist_ok=True)
            self.get_camera_frames()
        except Exception as e:
            logging.exception("Camera plugin encountered an error: %s", str(e))
            raise Exception(e)

        for tspath in self.workdir.glob("*"):
            if tspath.suffix == ".rgb":
                tspath = self.convert_rgb_to_jpg(tspath)
            elif 'celsius' in tspath.name:
                self.csv_to_netcdf(tspath)

        return tspath




