# Mobotix Scanner Plugin
This plugin moves the Mobotix camera to specified preset locations and captures thermal and visible images from those positions. The plugin accepts the IP or URL of the camera, user ID, and password as command-line arguments. It also supports preset location IDs as an optional argument. There are 32 preset locations available, accessible by calling preset 1-32 or by scanning in the default mode. For non-PT (Pan/Tilt) units, set the preset position to 0 to disable the scanning code. For a constant view, set the preset position to a single desired location.

## Scanning Modes

### 1. **Preset Scanning Mode (`preset`)**

In this mode, the camera moves to specified preset locations sequentially and captures images at each position. The preset locations are defined using the `-pt` or `--preset` argument as a comma-separated string.
```bash
python3 /app/app.py --ip 10.11.12.13 -u admin -p password --mode preset --pt 1,6,4,8
```
This command moves the camera to preset points 1, 6, 4, and 8 sequentially and captures images at each location.

### 2. Custom Scanning Mode (`custom`)

Custom scanning mode allows more detailed control over the camera’s movement and image capturing process. You can specify multiple custom scan loops, durations, speeds, and directions.


Single custom scan loop:
```bash
sudo pluginctl deploy -n test-custom 10.31.81.1:5000/local/plugin-mobotix-scan -- --ip 10.31.81.16 -p meinsm --mode custom --preset 1 --ptshots 5 --ptdur 500 --ptspeed 4
```
This command performs a custom scan loop starting at preset 1, taking 5 shots, with a movement duration of 500 nanoseconds and a speed of 4.

Multiple custom scan loops:

```bash
    sudo pluginctl deploy -n test-custom 10.31.81.1:5000/local/plugin-mobotix-scan -- --ip 10.31.81.16 -p meinsm --mode custom --preset 1,3,5 --ptshots 5,5,5 --ptdur 500,400,300 --ptspeed 4,5,5 --ptdir left
```
This command performs multiple custom scan loops starting at presets 1, 3, and 5, taking 5 shots at each location with varying durations, speeds, and directions.

### 3. Direction-Based Scanning Mode (`direction`)

In direction-based scanning mode, you start from a specified preset that points South and scan using directional movements. The initial south-pointing preset is provided via the `--southdirection` or `-south argument`, and subsequent directional movements are specified using the -pt or --preset argument.

```bash
python3 /app/app.py --ip 10.11.12.13 -u admin -p password --mode direction --south 28 --pt SES,NEG
```
This command starts from preset 28 (which points south), calculates the necessary directional offset, and moves the camera based on the SES and NEG directional presets.

Arguments

    --debug: Enable debug logs.
    --ip: Specifies the camera IP or URL. The CAMERA_IP environment variable can also be used.
    --mode: Sets the mode of operation. Choices are preset, custom, and direction.
    -pt or --preset: Provide preset locations as a comma-separated string. This is used for preset and direction scanning modes, and as the starting position for custom scanning.
    -u or --user: Specifies the camera user ID. Defaults to admin.
    -p or --password: Specifies the camera password. Defaults to meinsm.
    -south or --southdirection: Specifies the camera preset value that points the camera toward the south. This is used in the direction mode.
    --ptdir: Specifies the direction to move (left, right, up, down). Default is right.
    --ptspeed: Specifies the speed to move. Default is 3.
    --ptdur: Specifies the duration to move in nanoseconds. Default is 500 nanoseconds.
