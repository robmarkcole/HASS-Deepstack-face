"""
Component that will perform facial recognition via deepstack.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/image_processing.deepstack_face
"""
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
from homeassistant.const import CONF_IP_ADDRESS, CONF_PORT

_LOGGER = logging.getLogger(__name__)

CONF_API_KEY = "api_key"
CONF_TIMEOUT = "timeout"
DEFAULT_API_KEY = ""
DEFAULT_TIMEOUT = 10

CONF_DETECT_ONLY = "detect_only"

CLASSIFIER = "deepstack_face"
DATA_DEEPSTACK = "deepstack_classifiers"
FILE_PATH = "file_path"
SERVICE_TEACH_FACE = "deepstack_teach_face"


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_IP_ADDRESS): cv.string,
        vol.Required(CONF_PORT): cv.port,
        vol.Optional(CONF_API_KEY, default=DEFAULT_API_KEY): cv.string,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Optional(CONF_DETECT_ONLY, default=False): cv.boolean,
    }
)

SERVICE_TEACH_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(FILE_PATH): cv.string,
    }
)


def parse_predictions(predictions):
    """Parse the predictions data into the format required for HA image_processing.detect_face event."""
    faces = []
    for entry in predictions:
        if entry["userid"] == "unknown":
            continue
        face = {}
        face["name"] = entry["userid"]
        face[ATTR_CONFIDENCE] = round(100.0 * entry["confidence"], 2)
        faces.append(face)
    return faces


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the classifier."""
    if DATA_DEEPSTACK not in hass.data:
        hass.data[DATA_DEEPSTACK] = []

    ip_address = config[CONF_IP_ADDRESS]
    port = config[CONF_PORT]
    api_key = config.get(CONF_API_KEY)
    timeout = config.get(CONF_TIMEOUT)
    detect_only = config.get(CONF_DETECT_ONLY)

    entities = []
    for camera in config[CONF_SOURCE]:
        face_entity = FaceClassifyEntity(
            ip_address,
            port,
            api_key,
            timeout,
            detect_only,
            camera[CONF_ENTITY_ID],
            camera.get(CONF_NAME),
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

    def __init__(
        self, ip_address, port, api_key, timeout, detect_only, camera_entity, name=None
    ):
        """Init with the API key and model id."""
        super().__init__()
        self._dsface = ds.DeepstackFace(ip_address, port, api_key, timeout)
        self._detect_only = detect_only
        self._camera = camera_entity
        if name:
            self._name = name
        else:
            camera_name = split_entity_id(camera_entity)[1]
            self._name = "{} {}".format(CLASSIFIER, camera_name)
        self._matched = {}

    def process_image(self, image):
        """Process an image."""
        try:
            if self._detect_only:
                self._dsface.detect(image)
            else:
                self._dsface.recognise(image)
        except ds.DeepstackException as exc:
            _LOGGER.error("Depstack error : %s", exc)
            return
        predictions = self._dsface.predictions.copy()

        if len(predictions) > 0:
            self.total_faces = len(predictions)
            self._matched = ds.get_recognised_faces(predictions)
            faces = parse_predictions(predictions)
            self.process_faces(
                faces, self.total_faces
            )  # fire image_processing.detect_face
        else:
            self.total_faces = None
            self._matched = {}

    def teach(self, name, file_path):
        """Teach classifier a face name."""
        if not self.hass.config.is_allowed_path(file_path):
            return
        with open(file_path, "rb") as image:
            self._dsface.register_face(name, image)
            _LOGGER.info("Depstack face taught name : %s", name)

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
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def device_state_attributes(self):
        """Return the classifier attributes."""
        return {
            "matched_faces": self._matched,
            "total_matched_faces": len(self._matched),
        }
