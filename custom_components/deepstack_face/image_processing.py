"""
Component that will perform facial recognition via deepstack.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/image_processing.deepstack_face
"""
import base64
import logging
import time

import deepstack.core as ds

import requests
import voluptuous as vol

from homeassistant.const import ATTR_ENTITY_ID, ATTR_NAME
from homeassistant.core import split_entity_id
import homeassistant.helpers.config_validation as cv
from homeassistant.components.image_processing import (
    PLATFORM_SCHEMA,
    ImageProcessingFaceEntity,
    ATTR_CONFIDENCE,
    CONF_SOURCE,
    CONF_ENTITY_ID,
    CONF_NAME,
    DOMAIN,
)
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_PORT,
    HTTP_BAD_REQUEST,
    HTTP_OK,
    HTTP_UNAUTHORIZED,
)

_LOGGER = logging.getLogger(__name__)

CONF_API_KEY = "api_key"
CONF_TIMEOUT = "timeout"
DEFAULT_API_KEY = ""
DEFAULT_TIMEOUT = 10

CLASSIFIER = "deepstack_face"
DATA_DEEPSTACK = "deepstack_classifiers"
FILE_PATH = "file_path"
SERVICE_TEACH_FACE = "deepstack_teach_face"


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_IP_ADDRESS): cv.string, vol.Required(CONF_PORT): cv.port}
)

SERVICE_TEACH_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(FILE_PATH): cv.string,
    }
)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the classifier."""
    if DATA_DEEPSTACK not in hass.data:
        hass.data[DATA_DEEPSTACK] = []

    ip_address = config[CONF_IP_ADDRESS]
    port = config[CONF_PORT]
    entities = []
    for camera in config[CONF_SOURCE]:
        face_entity = FaceClassifyEntity(
            ip_address, port, camera[CONF_ENTITY_ID], camera.get(CONF_NAME)
        )
        entities.append(face_entity)
        hass.data[DATA_DEEPSTACK].append(face_entity)

    add_devices(entities)

    def service_handle(service):
        """Handle for services."""
        entity_ids = service.data.get("entity_id")

        classifiers = hass.data[DATA_DEEPSTACK]
        if entity_ids:
            classifiers = [c for c in classifiers if c.entity_id in entity_ids]

        for classifier in classifiers:
            name = service.data.get(ATTR_NAME)
            file_path = service.data.get(FILE_PATH)
            classifier.teach(name, file_path)

    hass.services.register(
        DOMAIN, SERVICE_TEACH_FACE, service_handle, schema=SERVICE_TEACH_SCHEMA
    )


class FaceClassifyEntity(ImageProcessingFaceEntity):
    """Perform a face classification."""

    def __init__(self, ip_address, port, camera_entity, name=None):
        """Init with the API key and model id."""
        super().__init__()
        self._url_check = "http://{}:{}/v1/vision/face/recognize".format(
            ip_address, port
        )
        self._url_register = "http://{}:{}/v1/vision/face/register".format(
            ip_address, port
        )
        self._camera = camera_entity
        if name:
            self._name = name
        else:
            camera_name = split_entity_id(camera_entity)[1]
            self._name = "{} {}".format(CLASSIFIER, camera_name)
        self._matched = {}

    def process_image(self, image):
        """Process an image."""
        response = ds.post_image(
            self._url_check, image, api_key="Mysecretkey", timeout=DEFAULT_TIMEOUT
        )
        if response:
            if response.status_code == HTTP_OK:
                predictions_json = response.json()["predictions"]
                self._matched = ds.get_recognised_faces(predictions_json)
                self.total_faces = len(predictions_json)
        else:
            self.total_faces = None
            self._matched = {}

    def teach(self, name, file_path):
        """Teach classifier a face name."""
        if not self.hass.config.is_allowed_path(file_path):
            return
        pass
        # register_face(self._url_register, name, file_path)

    @property
    def camera_entity(self):
        """Return camera entity id from process pictures."""
        return self._camera

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Ensure consistent state."""
        return self.total_faces

    @property
    def device_state_attributes(self):
        """Return the classifier attributes."""
        return {
            "matched_faces": self._matched,
            "total_matched_faces": len(self._matched),
        }
