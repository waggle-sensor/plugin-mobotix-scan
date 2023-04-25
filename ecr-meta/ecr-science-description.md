# Mobotix Scanner
This plugin moves Mobotix camera to specified preset locations and captures thermal and visible images and data from given positions. The plugin takes the IP or URL of the camera, the user ID, and the password as command-line arguments. It also takes the preset location IDs as an optional argument.
The 32 preset locations are available for use by calling preset 1-32 or scan in default. For nonPT units, set the preset position to 0, so the scanning code will not be executed. For the constatnt view, set the preset position to single desired position.


## Usage

To execute the plugin use the following (from within the built `Docker` container):

```
python3 /app/app.py --ip ip_address -pt locations --user username --password password 
```
    `ip_address`: The IP address or URL of the camera.
    `username`: The user ID of the camera.
     `password`: The password of the camera.
    `interval`: Interval between the loops in seconds (optional, defaults to 300 Seconds).
     `loops`: Scanning loops to perform (optional, defaults to -1=infinite).
    `location`: The preset location ID of the camera (optional, defaults to scanning mode).


Example:

```
python3 /app/app.py --ip 10.11.12.13 -u admin -p password --pt 5
```

This moves camera with ip 10.11.12.13 to preset point 5.

### Development

The `Docker` container can be built by executing the following:

```
./build.sh
```

