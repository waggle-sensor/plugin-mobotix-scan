import logging
import os
import re
import subprocess
from pathlib import Path
from select import select

import timeout_decorator
from waggle.plugin import Plugin

# camera image fetch timeout (seconds)
DEFAULT_CAMERA_TIMEOUT = 120


class MobotixSample():
    def __init__(self, ip, user, passwd, workdir, frames):
        super().__init__()
        self.ip = ip
        self.user = user
        self.password = passwd
        self.workdir = Path(workdir)
        self.frames = frames

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
            self.ip,
            "--user",
            self.user,
            "--password",
            self.password,
            "--dir",
            str(self.workdir),
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
                if m and int(m.groups()[0]) > self.frames:
                    logging.info("Max frame count reached, closing camera capture")
                    return

    def capture(self):
        try:
            self.workdir.mkdir(parents=True, exist_ok=True)
            self.get_camera_frames()
        except Exception as e:
            logging.exception("Camera plugin encountered an error: %s", str(e))
            raise Exception(e)

        for tspath in self.workdir.glob("*"):
            if tspath.suffix == ".rgb":
                tspath = self.convert_rgb_to_jpg(tspath)


                


