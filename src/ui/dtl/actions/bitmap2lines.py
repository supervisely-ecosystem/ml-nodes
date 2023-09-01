import copy
import json
from typing import Optional
from supervisely import ProjectMeta, Bitmap, AnyGeometry
from supervisely.app.widgets import NodesFlow
from src.ui.dtl import Action
from src.ui.dtl.Layer import Layer
from src.ui.widgets import ClassesMapping


class Bitmap2LinesAction(Action):
    name = "bitmap2lines"
    title = "Bitmap to Lines"
    docs_url = (
        "https://docs.supervisely.com/data-manipulation/index/transformation-layers/bitmap2lines"
    )
    description = "This layer (bitmap2lines) converts thinned (skeletonized) bitmaps to lines. It is extremely useful if you have some raster objects representing lines or edges, maybe forming some tree or net structure, and want to work with vector objects. Each input bitmap should be already thinned (use Skeletonize layer to do it), and for single input mask a number of lines will be produced. Resulting lines may have very many vertices, so consider applying Approx Vector layer to results of this layer. Internally the layer builds a graph of 8-connected pixels, determines minimum spanning tree(s), then greedely extracts diameters from connected components of the tree."
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
                "min_points_cnt": options_json["min_points_cnt"],
            }

        def set_settings_from_json(json_data: dict, node_state: dict):
            """This function is used to set options from settings we get from dlt json input"""
            settings = json_data["settings"]
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

        def meta_changed_cb(project_meta: ProjectMeta):
            classes_mapping_widget.loading = True
            classes_mapping_widget.set(
                [
                    cls
                    for cls in project_meta.obj_classes
                    if cls.geometry_type in [Bitmap, AnyGeometry]
                ]
            )
            classes_mapping_widget.loading = False

        options = [
            NodesFlow.Node.Option(
                name="Info",
                option_component=NodesFlow.ButtonOptionComponent(
                    sidebar_component=NodesFlow.WidgetOptionComponent(cls.create_info_widget())
                ),
            ),
            NodesFlow.Node.Option(
                name="min_points_cnt_text",
                option_component=NodesFlow.TextOptionComponent("Min Points Count"),
            ),
            NodesFlow.Node.Option(
                name="min_points_cnt",
                option_component=NodesFlow.IntegerOptionComponent(min=2, default_value=2),
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
            options=options,
            get_settings=get_settings,
            get_src=None,
            meta_changed_cb=meta_changed_cb,
            get_dst=None,
            set_settings_from_json=set_settings_from_json,
            id=layer_id,
        )
