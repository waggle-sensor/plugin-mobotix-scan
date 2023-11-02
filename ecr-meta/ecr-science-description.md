# Mobotix Scanner
This plugin moves Mobotix camera to specified preset locations and captures thermal and visible images and data from given positions. The plugin takes the IP or URL of the camera, the user ID, and the password as command-line arguments. It also takes the preset location IDs as an optional argument.
The 32 preset locations are available for use by calling preset 1-32 or scan in default. For nonPT units, set the preset position to 0, so the scanning code will not be executed. For the constatnt view, set the preset position to single desired position.


## Usage

To execute the plugin use the following (from within the built `Docker` container):

```
python3 /app/app.py --ip ip_address -pt locations --user username --password password 
```



```
python3 /app/app.py --ip 10.11.12.13 -u admin -p password --pt 5
```
This moves camera with ip 10.11.12.13 to preset point 5.


```
python3 /app/app.py --ip 10.11.12.13 -u admin -p password --pt 1,6,4,8
```
This moves camera to preset point 1,6,4,8 and captures images.

```
python3 /app/app.py --ip 10.11.12.13 -u admin -p password --pt 0
```
This will capture images but without moving the camera.




### Usage with `pluginctl` for custom scan
To run one custom scan loop for one preset position
```
sudo pluginctl deploy -n test-custom 10.31.81.1:5000/local/plugin-mobotix-scan -- --ip 10.31.81.16 -p meinsm --mode custom --preset 1 --ptshots 5 --ptdur 500 --ptspeed 4
```

To run multiple custom scan loops for multiple preset position
```
sudo pluginctl deploy -n test-custom 10.31.81.1:5000/local/plugin-mobotix-scan -- --ip 10.31.81.16 -p meinsm --mode custom --preset 1,3, 5 --ptshots 5,5,5 --ptdur 500,400,300 --ptspeed 4,5,5 --ptdir left
```

### Arguments

1. `--debug`: Enable debug logs. This argument doesn't require a value.
   
2. `--ip`: Specifies the camera IP or URL. You can also use the `CAMERA_IP` environment variable.
   
3. `--mode`: Sets the mode of operation. The available choices are:
   - `preset`: Use preset scanning.
   - `custom`: Use custom scanning.

   The default mode is `preset`.

4. `-pt` or `--preset`: For preset scanning, provide preset locations as a comma-separated string. This is also used as the starting position for custom scanning. By default, a range of numbers will be used. You can specify `0` for non-scanning mode.
   
5. `-u` or `--user`: Specifies the camera user ID. By default, it uses the `CAMERA_USER` environment variable or "admin".
   
6. `-p` or `--password`: Specifies the camera password. By default, it uses the `CAMERA_PASSWORD` environment variable or "meinsm".
   
7. `-w` or `--workdir`: Specifies the directory to cache camera data before uploading. The default directory is `./data`.
   
8. `-f` or `--frames`: Specifies the number of frames to capture per loop. By default, it uses the `FRAMES_PER_LOOP` environment variable or sets to 1.
   
9. `-l` or `--loops`: Specifies the number of loops to perform. The default is a one-shot mode, which means `l=1`.
   
10. `-s` or `--loopsleep`: Specifies the seconds to sleep between loops. By default, it uses the `LOOP_SLEEP` environment variable or sets to 300 seconds.
    
11. `--ptshots`: Specifies the number of images for a `custom scan`. This will repeat for each preset. The default is 15.

12. `--ptdir`: Specifies the direction to move. The choices are:
    - `left`
    - `right`
    - `up`
    - `down`
    
    The preferred choices are 'left' or 'right'. Same for each preset in custom scan, and the default direction is `right`.

13. `--ptspeed`: Specifies the speed to move. This will repeat for each preset. The default speed is 3.

14. `--ptdur`: Specifies the duration to move in nano-seconds. This will repeat for each preset. The default duration is 500 nano-seconds.




### Development

The `Docker` container can be built by executing the following:

```
./build.sh
```

