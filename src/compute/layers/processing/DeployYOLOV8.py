# coding: utf-8
from typing import Tuple, Union

from supervisely import (
    Annotation,
    Label,
    Rectangle,
    ObjClass,
    VideoAnnotation,
    Frame,
    VideoFigure,
    VideoObject,
    FrameCollection,
    VideoObjectCollection,
)

from src.compute.Layer import Layer
from src.compute.classes_utils import ClassConstants
from src.compute.dtl_utils.item_descriptor import ImageDescriptor, VideoDescriptor


class DeployYOLOV8(Layer):
    action = "deploy_yolov8"

    layer_settings = layer_settings = {
        "required": ["settings"],
        "properties": {
            "settings": {
                "type": "object",
                "required": [
                    "session_id",
                    "agent_id",
                    "device",
                    "model_type",
                    "model_name",
                    "task_type",
                    "model_path",
                    "stop_model_session",
                ],
                "properties": {
                    "session_id": {"type": "integer"},
                    "agent_id": {"type": "integer"},
                    "device": {"type": "string"},
                    "model_type": {"type": "string"},
                    "model_name": {"type": "string"},
                    "task_type": {"type": "string"},
                    "model_path": {"oneOf": [{"type": "string"}, {"type": "null"}]},
                    "stop_model_session": {"type": "boolean"},
                },
            },
        },
    }

    def __init__(self, config, net):
        Layer.__init__(self, config, net=net)

    def modifies_data(self):
        return False

    def process(
        self,
        data_el: Tuple[Union[ImageDescriptor, VideoDescriptor], Union[Annotation, VideoAnnotation]],
    ):
        item_desc, ann = data_el
        yield item_desc, ann