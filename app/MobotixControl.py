import subprocess
import time
import timeout_decorator

# camera move timeout (seconds)
DEFAULT_MOVEMENT_TIMEOUT = 15

class MobotixControl:
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

    @timeout_decorator.timeout(DEFAULT_MOVEMENT_TIMEOUT)
    def _send_command(self, code):
        cmd = ["curl",
               "-u",
               f"{self.user}:{self.passwd}",
               "-X",
               "POST",
               f"http://{self.ip}/control/rcontrol?action=putrs232&rs232outtext={code}"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout

        except subprocess.CalledProcessError as e:
            print("Error: {}".format(e))
            return e

    def move_to_preset(self, pt_id):
        preset_code = self.presets.get(pt_id)
        if preset_code:
            return self._send_command(preset_code)
        else:
            return "Invalid preset ID."

    def move(self, direction, speed, duration):
        code = self.speed_codes[direction].get(speed)
        if code:
            self._send_command(code)
            time.sleep(duration)
            self.stop()
        else:
            return "Invalid code value for movement."
        

    def stop(self):
        code = '%FF%01%00%00%00%00%01'
        return self._send_command(code)

    def remote_reset(self):
        code = '%FF%01%00%0F%00%00%10'
        return self._send_command(code)

