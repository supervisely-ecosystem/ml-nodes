from typing import Optional
import copy
import os
from pathlib import Path

from supervisely.app.widgets import NodesFlow, Button, Container, Flexbox, Text
from supervisely import ProjectMeta
from supervisely import Polygon, Polyline, AnyGeometry

import src.globals as g
from src.ui.dtl import AnnotationAction
from src.ui.dtl.Layer import Layer
from src.ui.widgets import ClassesList, ClassesListPreview
from src.ui.dtl.utils import (
    classes_list_settings_changed_meta,
    get_classes_list_value,
    set_classes_list_preview,
    set_classes_list_settings_from_json,
    get_set_settings_button_style,
    get_set_settings_container,
)


class ApproxVectorAction(AnnotationAction):
    name = "approx_vector"
    title = "Approx Vector"
    docs_url = (
        "https://docs.supervisely.com/data-manipulation/index/transformation-layers/approx_vector"
    )
    description = "This layer (approx_vector) approximates vector figures: lines and polygons. The operation decreases number of vertices with Douglas-Peucker algorithm."

    md_description = ""
    for p in ("readme.md", "README.md"):
        p = Path(os.path.realpath(__file__)).parent.joinpath(p)
        if p.exists():
            with open(p) as f:
                md_description = f.read()
            break

    @classmethod
    def create_new_layer(cls, layer_id: Optional[str] = None):
        _current_meta = ProjectMeta()
        classes_list_widget = ClassesList(multiple=True)
        classes_list_preview = ClassesListPreview()
        classes_list_save_btn = Button("Save", icon="zmdi zmdi-floppy")
        classes_list_set_default_btn = Button("Set Default", icon="zmdi zmdi-refresh")
        classes_list_widgets_container = Container(
            widgets=[
                classes_list_widget,
                Flexbox(
                    widgets=[
                        classes_list_save_btn,
                        classes_list_set_default_btn,
                    ],
                    gap=105,
                ),
            ]
        )
        classes_list_edit_text = Text("Classes")
        classes_list_edit_btn = Button(
            text="EDIT",
            icon="zmdi zmdi-edit",
            button_type="text",
            button_size="small",
            emit_on_click="openSidebar",
            style=get_set_settings_button_style(),
        )
        classes_list_edit_container = get_set_settings_container(
            classes_list_edit_text, classes_list_edit_btn
        )

        saved_classes_settings = []
        default_classes_settings = []

        def _get_classes_list_value():
            return get_classes_list_value(classes_list_widget, multiple=True)

        def _set_classes_list_preview():
            set_classes_list_preview(
                classes_list_widget, classes_list_preview, saved_classes_settings
            )

        def _save_classes_list_settings():
            nonlocal saved_classes_settings
            saved_classes_settings = _get_classes_list_value()

        def _set_default_classes_mapping_setting():
            # save setting to var
            nonlocal saved_classes_settings
            saved_classes_settings = copy.deepcopy(default_classes_settings)

        def meta_changed_cb(project_meta: ProjectMeta):
            nonlocal _current_meta
            if project_meta == _current_meta:
                return
            _current_meta = project_meta

            classes_list_widget.loading = True
            obj_classes = [
                cls
                for cls in project_meta.obj_classes
                if cls.geometry_type in [Polygon, Polyline, AnyGeometry]
            ]

            # set classes to widget
            classes_list_widget.set(obj_classes)

            # update settings according to new meta
            nonlocal saved_classes_settings
            saved_classes_settings = classes_list_settings_changed_meta(
                saved_classes_settings, obj_classes
            )

            # update settings preview
            _set_classes_list_preview()

            classes_list_widget.loading = False

        def get_settings(options_json: dict) -> dict:
            """This function is used to get settings from options json we get from NodesFlow widget"""
            return {
                "classes": saved_classes_settings,
                "epsilon": options_json["epsilon"],
            }

        def _set_settings_from_json(settings: dict):
            classes_list_widget.loading = True
            classes_list_settings = settings.get("classes", [])
            set_classes_list_settings_from_json(
                classes_list_widget=classes_list_widget, settings=classes_list_settings
            )
            # save settings
            _save_classes_list_settings()
            # update settings preview
            _set_classes_list_preview()
            classes_list_widget.loading = False

        @classes_list_save_btn.click
        def classes_list_save_btn_cb():
            _save_classes_list_settings()
            _set_classes_list_preview()
            g.updater("metas")

        @classes_list_set_default_btn.click
        def classes_list_set_default_btn_cb():
            _set_default_classes_mapping_setting()
            set_classes_list_settings_from_json(
                classes_list_widget=classes_list_widget, settings=saved_classes_settings
            )
            _set_classes_list_preview()
            g.updater("metas")

        def create_options(src: list, dst: list, settings: dict) -> dict:
            _set_settings_from_json(settings)
            epsilon_val = settings.get("epsilon", 3)
            if epsilon_val < 1:
                raise ValueError("Epsilon must be greater than 0")
            settings_options = [
                NodesFlow.Node.Option(
                    name="Select Classes",
                    option_component=NodesFlow.WidgetOptionComponent(
                        widget=classes_list_edit_container,
                        sidebar_component=NodesFlow.WidgetOptionComponent(
                            classes_list_widgets_container
                        ),
                        sidebar_width=380,
                    ),
                ),
                NodesFlow.Node.Option(
                    name="classes_preview_text",
                    option_component=NodesFlow.WidgetOptionComponent(classes_list_preview),
                ),
                NodesFlow.Node.Option(
                    name="epsilon_text",
                    option_component=NodesFlow.TextOptionComponent("Epsilon"),
                ),
                NodesFlow.Node.Option(
                    name="epsilon",
                    option_component=NodesFlow.IntegerOptionComponent(
                        min=1, default_value=epsilon_val
                    ),
                ),
            ]
            return {
                "src": [],
                "dst": [],
                "settings": settings_options,
            }

        return Layer(
            action=cls,
            id=layer_id,
            create_options=create_options,
            get_settings=get_settings,
            meta_changed_cb=meta_changed_cb,
        )
