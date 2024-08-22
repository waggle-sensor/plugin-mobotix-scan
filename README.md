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

## **Command-Line Arguments**

### **--debug**
- **Description**: Enables debug logs.
- **Usage**: Optional.
- **Example**: `--debug`

### **--ip**
- **Description**: Specifies the camera IP or URL.
- **Usage**: Required.
- **Example**: `--ip 10.11.12.13`
- **Default**: Value from the `CAMERA_IP` environment variable.

### **--mode**
- **Description**: Sets the mode of operation.
- **Choices**: `preset`, `custom`, `direction`
- **Usage**: Optional.
- **Example**: `--mode custom`
- **Default**: `preset`

### **-pt, --preset**
- **Description**: Provides preset locations as a comma-separated string. Used for preset and direction scanning modes and as the starting position for custom scanning. For direction mode, it specifies direction locations for scanning.
- **Usage**: Optional.
- **Example**: `--preset 1,6,4,8`
- **Default**: A generated string covering default movement positions.

### **-u, --user**
- **Description**: Specifies the camera user ID.
- **Usage**: Optional.
- **Example**: `--user admin`
- **Default**: `admin` or value from the `CAMERA_USER` environment variable.

### **-p, --password**
- **Description**: Specifies the camera password.
- **Usage**: Optional.
- **Example**: `--password mypassword`
- **Default**: `meinsm` or value from the `CAMERA_PASSWORD` environment variable.

### **-w, --workdir**
- **Description**: Directory to cache camera data before upload.
- **Usage**: Optional.
- **Example**: `--workdir /path/to/directory`
- **Default**: `./data`

### **-f, --frames**
- **Description**: Number of frames to capture per loop.
- **Usage**: Optional.
- **Example**: `--frames 5`
- **Default**: `1` or value from the `FRAMES_PER_LOOP` environment variable.

### **-l, --loops**
- **Description**: Number of loops to perform.
- **Usage**: Optional.
- **Example**: `--loops 10`
- **Default**: `1` or value from the `LOOPS` environment variable.

### **-s, --loopsleep**
- **Description**: Seconds to sleep in between loops.
- **Usage**: Optional.
- **Example**: `--loopsleep 300`
- **Default**: `300` or value from the `LOOP_SLEEP` environment variable.

### **--ptshots**
- **Description**: Number of images for custom scan. Repeat for each preset.
- **Usage**: Optional.
- **Example**: `--ptshots 10`
- **Default**: `15`

### **--ptdir**
- **Description**: Direction to move the camera. Options include `left`, `right`, `up`, `down`.
- **Usage**: Optional.
- **Example**: `--ptdir left`
- **Default**: `right`

### **--ptspeed**
- **Description**: Speed to move the camera.
- **Usage**: Optional.
- **Example**: `--ptspeed 5`
- **Default**: `3`

### **--ptdur**
- **Description**: Duration to move the camera in nanoseconds.
- **Usage**: Optional.
- **Example**: `--ptdur 1000`
- **Default**: `500`

### **-south, --southdirection**
- **Description**: A camera preset value that points the camera toward the south. Used in the `direction` mode.
- **Usage**: Optional.
- **Example**: `--southdirection 28`
- **Default**: `1`


