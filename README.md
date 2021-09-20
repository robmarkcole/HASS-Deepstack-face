# HASS-Deepstack-face
[Home Assistant](https://www.home-assistant.io/) custom components for using Deepstack face detection and recognition. [Deepstack](https://docs.deepstack.cc/) is a service which runs in a docker container and exposes various computer vision models via a REST API.

On you machine with docker, run Deepstack with the face recognition service active on port `80` with:
```
docker run -e VISION-FACE=True -v localstorage:/datastore -p 80:5000 --name deepstack deepquestai/deepstack
```

## Home Assistant setup
Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder). Then configure face recognition.

**Note** that by default the component will **not** automatically scan images, but requires you to call the `image_processing.scan` service e.g. using an automation.

Deepstack [face recognition](https://docs.deepstack.cc/face-recognition/index.html) counts faces (detection) and (optionally) will recognize them if you have trained your Deepstack using the `deepstack_teach_face` service (takes extra time). Configuring `detect_only = True` results in faster processing than recognition mode, but any trained faces will not be listed in the `matched_faces` attribute. An event `image_processing.detect_face` is fired for each detected face.

The `deepstack_face` component adds an `image_processing` entity where the state of the entity is the total number of faces that are found in the camera image. Recognized faces are listed in the entity `matched faces` attribute. The component can optionally save snapshots of the processed images. If you would like to use this option, you need to create a folder where the snapshots will be stored. The folder should be in the same folder where your `configuration.yaml` file is located. In the example below, we have named the folder `snapshots`.

Add to your Home-Assistant config:
```yaml
image_processing:
  - platform: deepstack_face
    ip_address: localhost
    port: 5000
    api_key: mysecretkey
    timeout: 5
    detect_only: False
    save_file_folder: /config/snapshots/
    save_timestamped_file: True
    save_faces: True
    save_faces_folder: /config/faces/
    show_boxes: True
    source:
      - entity_id: camera.local_file
        name: face_counter
```
Configuration variables:
- **ip_address**: the ip address of your deepstack instance.
- **port**: the port of your deepstack instance.
- **api_key**: (Optional) Any API key you have set.
- **timeout**: (Optional, default 10 seconds) The timout for requests to deepstack.
- **detect_only**: (Optional, boolean, default `False`) If `True`, only detection is performed. If `False` then recognition is performed.
- **save_file_folder**: (Optional) The folder to save processed images to. Note that folder path should be added to [whitelist_external_dirs](https://www.home-assistant.io/docs/configuration/basic/)
- **save_timestamped_file**: (Optional, default `False`, requires `save_file_folder` to be configured) Save the processed image with the time of detection in the filename.
- **save_faces**: (Optional, default `False`, requires `save_faces_folder` to be configured and `detect_only` to be set to `False`) Save every recognized face to a file inside the `save_faces_folder` directory.
- **save_faces_folder**: (Optional) The folder to save cut out faces to. Note that folder path should be added to [whitelist_external_dirs](https://www.home-assistant.io/docs/configuration/basic/)
- **show_boxes**: (optional, default `True`), if `False` bounding boxes are not shown on saved images
- **source**: Must be a camera.
- **name**: (Optional) A custom name for the the entity.

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack-face/blob/master/docs/face_usage.png" width="500">
</p>

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Deepstack-face/blob/master/docs/face_detail.png" width="350">
</p>

#### Service `deepstack_teach_face`
This service is for teaching (or [registering](https://docs.deepstack.cc/face-recognition/index.html#face-registration)) faces with deepstack, so that they can be recognized.

Example valid service data:
```
{
  "name": "Adele",
  "file_path": "/config/www/adele.jpeg"
}
```

## Event `image_processing.detect_face`
For each face that is detected, an `image_processing.detect_face` event is fired. The event payload includes the following data:
- `entity_id` : the entity id responsible for the event
- `name` : the name of the face if recognised, otherwise `unknown`
- `confidence`: the confidence in % of the recognition, 0 if `unknown`

**Remember** face recognition is not performed if you have configured `detect_only: True`.

## EVENT `deepstack_face.teach_face`
When a face is taugh to deepstack face, an `deepstack_face.teach_face` event is fired. The event payload includes the following data:
- `name`: the name of the face learned 
- `file_path`: the file path of the file used


To monitor these events from the HA UI you can use `Developer tools -> EVENTS -> :Listen to events`. 

## Object recognition
For object (e.g. person) recognition with Deepstack use https://github.com/robmarkcole/HASS-Deepstack-object

### Support
For code related issues such as suspected bugs, please open an issue on this repo. For general chat or to discuss Home Assistant specific issues related to configuration or use cases, please [use this thread on the Home Assistant forums](https://community.home-assistant.io/t/face-and-person-detection-with-deepstack-local-and-free/92041).

### Docker tips
Add the `-d` flag to run the container in background, thanks [@arsaboo](https://github.com/arsaboo).

### FAQ
Q1: I get the following warning, is this normal?
```
2019-01-15 06:37:52 WARNING (MainThread) [homeassistant.loader] You are using a custom component for image_processing.deepstack_face which has not been tested by Home Assistant. This component might cause stability problems, be sure to disable it if you do experience issues with Home Assistant.
```
A1: Yes this is normal

------

Q2: I hear Deepstack is open source?

A2: Yes, see https://github.com/johnolafenwa/DeepStack

------

Q3: What are the minimum hardware requirements for running Deepstack?

A3. Based on my experience, I would allow 0.5 GB RAM per model.

------

Q4: If I teach (register) a face do I need to re-teach if I restart the container?

A4: So long as you have run the container including `-v localstorage:/datastore` then you do not need to re-teach, as data is persisted between restarts.

------

Q5: I am getting an error from Home Assistant: `Platform error: image_processing - Integration deepstack_object not found`

A5: This can happen when you are running in Docker, and indicates that one of the dependencies isn't installed. It is necessary to reboot your device, or rebuild your Docker container. Note that just restarting Home Assistant will not resolve this.

------

## Video of usage
Checkout this excellent video of usage from [Everything Smart Home](https://www.youtube.com/channel/UCrVLgIniVg6jW38uVqDRIiQ)

[![](http://img.youtube.com/vi/XPs0J1EQhK0/0.jpg)](http://www.youtube.com/watch?v=XPs0J1EQhK0 "")
