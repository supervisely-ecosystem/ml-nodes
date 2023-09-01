import copy
from typing import Optional
from supervisely.app.widgets import NodesFlow
from supervisely import ProjectMeta
from src.ui.dtl import Action
from src.ui.dtl.Layer import Layer
from src.ui.widgets import ClassesMapping


class DuplicateObjectsAction(Action):
    name = "duplicate_objects"
    title = "Duplicate Objects"
    docs_url = "https://docs.supervisely.com/data-manipulation/index/transformation-layers/duplicate_objects"
    description = "This layer (duplicate_objects) clones figures of required classes."
    # when setting options from settings json, values from _settings_mapping will be mapped to options.
    # If there is no option mapped directly to setting, set this option mapping to None and set the option value
    # in set_settings_from_json function. If option name is different from setting name - set mapping in
    # _settings_mapping below. If option name is the same as setting name - no need to set mapping.
    _settings_mapping = {
        "classes_mapping": None,
    }

    @classmethod
    def create_new_layer(cls, layer_id: Optional[str] = None):
        classes_mapping_widget = ClassesMapping()

        def _get_classes_mapping_value():
            mapping = classes_mapping_widget.get_mapping()
            values = {
                name: values["value"]
                for name, values in mapping.items()
                if not values["ignore"] and not values["default"]
            }
            return values

        def get_settings(options_json: dict) -> dict:
            """This function is used to get settings from options json we get from NodesFlow widget"""
            return {
                "classes_mapping": _get_classes_mapping_value(),
            }

        def meta_changed_cb(project_meta: ProjectMeta):
            classes_mapping_widget.loading = True
            classes_mapping_widget.set(project_meta.obj_classes)
            classes_mapping_widget.loading = False

        def set_settings_from_json(json_data: dict, node_state: dict):
            """This function is used to set options from settings we get from dlt json input"""
            settings = copy.deepcopy(json_data["settings"])
            classes_mapping = {}
            other_default = settings["classes_mapping"].get("__other__", None) == "__default__"
            for cls in classes_mapping_widget.get_classes():
                if cls.name in settings["classes_mapping"]:
                    value = settings["classes_mapping"][cls.name]
                    if value == "__default__":
                        value = cls.name
                    if value == "__ignore__":
                        value = ""
                    classes_mapping[cls.name] = value
                elif other_default:
                    classes_mapping[cls.name] = cls.name
                else:
                    classes_mapping[cls.name] = ""
            classes_mapping_widget.set_mapping(classes_mapping)
            return node_state

        options = [
            NodesFlow.Node.Option(
                name="Info",
                option_component=NodesFlow.ButtonOptionComponent(
                    sidebar_component=NodesFlow.WidgetOptionComponent(cls.create_info_widget())
                ),
            ),
            NodesFlow.Node.Option(
                name="classes_mapping_text",
                option_component=NodesFlow.TextOptionComponent("Classes Mapping"),
            ),
            NodesFlow.Node.Option(
                name="Set Classes Mapping",
                option_component=NodesFlow.ButtonOptionComponent(
                    sidebar_component=NodesFlow.WidgetOptionComponent(classes_mapping_widget)
                ),
            ),
        ]

        return Layer(
            action=cls,
            id=layer_id,
            options=options,
            get_src=None,
            get_dst=None,
            get_settings=get_settings,
            meta_changed_cb=meta_changed_cb,
            set_settings_from_json=set_settings_from_json,
        )
