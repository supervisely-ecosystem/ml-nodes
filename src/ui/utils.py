import json

from supervisely.app.widgets import Container, Flexbox, FileThumbnail, ProjectThumbnail, Text
from supervisely import ProjectMeta
import supervisely as sly

from src.utils import (
    LegacyProjectItem,
    get_project_by_name,
    get_project_meta,
    download_preview,
    update_project_info,
    get_all_datasets,
)
from src.compute.Net import Net
from src.compute.Layer import Layer as NetLayer
from src.compute.dtl_utils.image_descriptor import ImageDescriptor
from src.ui.dtl import actions, actions_list
from src.ui.dtl.Action import Action
from src.ui.dtl.Layer import Layer
from src.ui.dtl import (
    SOURCE_ACTIONS,
    SAVE_ACTIONS,
    PIXEL_LEVEL_TRANSFORMS,
    SPATIAL_LEVEL_TRANSFORMS,
    ANNOTATION_TRANSFORMS,
    OTHER,
)
from src.exceptions import (
    CustomException,
    ActionNotFoundError,
    CreateNodeError,
    LayerNotFoundError,
)
import src.globals as g
import src.utils as utils


def find_layer_id_by_dst(dst: str):
    for layer_id, layer in g.layers.items():
        if dst in layer.get_dst():
            return layer_id
    return None


def init_layers(nodes_state: dict):
    data_layers_ids = []
    save_layers_ids = []
    transform_layers_ids = []
    all_layers_ids = []
    for node_id, node_options in nodes_state.items():
        try:
            layer = g.layers[node_id]
            layer: Layer
        except KeyError:
            raise LayerNotFoundError(node_id)

        try:
            layer.parse_options(node_options)
        except CustomException as e:
            e.message = f"Error parsing options: {e.message}"
            e.extra["action_name"] = layer.action.name
            raise e
        except Exception as e:
            raise CustomException(
                f"Error parsing options",
                error=e,
                extra={"action_name": layer.action.name},
            )

        if layer.action.name in actions_list[SOURCE_ACTIONS]:
            data_layers_ids.append(node_id)
        if layer.action.name in actions_list[SAVE_ACTIONS]:
            save_layers_ids.append(node_id)
        if layer.action.name in [
            action
            for group in (
                PIXEL_LEVEL_TRANSFORMS,
                SPATIAL_LEVEL_TRANSFORMS,
                ANNOTATION_TRANSFORMS,
                OTHER,
            )
            for action in actions_list[group]
        ]:
            transform_layers_ids.append(node_id)
        all_layers_ids.append(node_id)

    return {
        "data_layers_ids": data_layers_ids,
        "save_layers_ids": save_layers_ids,
        "transformation_layers_ids": transform_layers_ids,
        "all_layers_ids": all_layers_ids,
    }


def init_src(edges: list):
    for edge in edges:
        from_node_id = edge["output"]["node"]
        from_node_interface = edge["output"]["interface"]
        to_node_id = edge["input"]["node"]
        try:
            layer = g.layers[to_node_id]
        except KeyError:
            raise LayerNotFoundError(to_node_id)
        layer: Layer
        layer.add_source(from_node_id, from_node_interface)


def set_preview(data_layers_ids):
    for data_layer_id in data_layers_ids:
        data_layer = g.layers[data_layer_id]
        src = data_layer.get_src()
        if src is None or len(src) == 0:
            # Skip if no sources specified for data layer
            continue

        project_name, dataset_name = src[0].split("/")
        try:
            project_info = get_project_by_name(project_name)
            project_meta = get_project_meta(project_info.id)
        except Exception as e:
            raise CustomException(
                f"Error getting project meta", error=e, extra={"project_name": project_name}
            )

        try:
            preview_img_path, preview_ann_path = download_preview(project_name, dataset_name)
        except Exception as e:
            raise CustomException(
                f"Error downloading image and annotation for preview",
                error=e,
                extra={"project_name": project_name, "dataset_name": dataset_name},
            )
        preview_img = sly.image.read(preview_img_path)
        with open(preview_ann_path, "r") as f:
            preview_ann = sly.Annotation.from_json(json.load(f), project_meta)
        preview_path = f"{g.PREVIEW_DIR}/{project_name}/{dataset_name}"
        img_desc = ImageDescriptor(
            LegacyProjectItem(
                project_name=project_name,
                ds_name=dataset_name,
                image_name="preview_image",
                ia_data={"image_ext": ".jpg"},
                img_path=f"{preview_path}/preview_image.jpg",
                ann_path=f"{preview_path}/preview_ann.json",
            ),
            False,
        )
        img_desc = img_desc.clone_with_img(preview_img)
        img_desc.write_image_local(f"{preview_path}/preview_image.jpg")
        data_layer.update_preview(img_desc, preview_ann)


def init_output_metas(net: Net, all_layers_ids: list, nodes_state: dict, edges: list):
    def calc_metas(net):
        cur_level_layers_idxs = {
            idx for idx, layer in enumerate(net.layers) if layer.type == "data"
        }
        datalevel_metas = {}
        for data_layer_idx in cur_level_layers_idxs:
            data_layer = net.layers[data_layer_idx]
            try:
                input_meta = data_layer.in_project_meta
            except AttributeError:
                input_meta = ProjectMeta()
            except KeyError:
                input_meta = ProjectMeta()
            for src in data_layer.srcs:
                datalevel_metas[src] = input_meta

        def get_dest_layers_idxs(the_layer_idx):
            the_layer = net.layers[the_layer_idx]
            return [
                idx
                for idx, dest_layer in enumerate(net.layers)
                if len(set(the_layer.dsts) & set(dest_layer.srcs)) > 0
            ]

        def layer_input_metas_are_calculated(the_layer_idx):
            the_layer = net.layers[the_layer_idx]
            return all((x in datalevel_metas for x in the_layer.srcs))

        processed_layers = set()
        while len(cur_level_layers_idxs) != 0:
            next_level_layers_idxs = set()

            for cur_layer_idx in cur_level_layers_idxs:
                cur_layer = net.layers[cur_layer_idx]
                processed_layers.add(cur_layer_idx)
                # TODO no need for dict here?
                cur_layer_input_metas = {src: datalevel_metas[src] for src in cur_layer.srcs}

                # update ui layer meta
                merged_meta = utils.merge_input_metas(cur_layer_input_metas.values())
                ui_layer_id = all_layers_ids[cur_layer_idx]
                ui_layer = g.layers[ui_layer_id]
                ui_layer: Layer
                ui_layer.update_project_meta(merged_meta)

                # update settings according to new meta
                node_options = nodes_state.get(ui_layer_id, {})
                ui_layer.parse_options(node_options)
                init_src(edges)
                ui_layer = g.layers[ui_layer_id]

                # update net layer with new settings
                layer_config = ui_layer.to_json()
                action = layer_config["action"]
                if action not in NetLayer.actions_mapping:
                    raise ActionNotFoundError(action)
                layer_cls = NetLayer.actions_mapping[action]
                if layer_cls.type == "data":
                    layer = layer_cls(layer_config)
                elif layer_cls.type == "processing":
                    layer = layer_cls(layer_config)
                elif layer_cls.type == "save":
                    layer = layer_cls(layer_config, g.RESULTS_DIR, net)
                    net.save_layer = layer
                net.layers[cur_layer_idx] = layer

                # calculate output meta of current net layer
                cur_layer = net.layers[cur_layer_idx]
                cur_layer_res_meta = cur_layer.make_output_meta(cur_layer_input_metas)

                # update output meta of current ui layer
                ui_layer.output_meta = cur_layer_res_meta

                for dst in cur_layer.dsts:
                    datalevel_metas[dst] = cur_layer_res_meta

                # yield cur_layer_res_meta, cur_layer_idx

                dest_layers_idxs = get_dest_layers_idxs(cur_layer_idx)
                for next_candidate_idx in dest_layers_idxs:
                    if layer_input_metas_are_calculated(next_candidate_idx):
                        next_level_layers_idxs.update([next_candidate_idx])

            cur_level_layers_idxs = next_level_layers_idxs

        return processed_layers

    processed_layers = calc_metas(net)
    for layer_idx in range(len(net.layers)):
        if layer_idx not in processed_layers:
            ui_layer_id = all_layers_ids[layer_idx]
            ui_layer = g.layers[ui_layer_id]
            ui_layer.update_project_meta(ProjectMeta())
    return net


def update_previews(net: Net, data_layers_ids: list, all_layers_ids: list):
    for layer in g.layers.values():
        layer.clear_preview()
    updated = set()

    net.preview_mode = True
    net.preprocess()

    for data_layer_id in data_layers_ids:
        data_layer = g.layers[data_layer_id]
        src = data_layer.get_src()
        if len(src) == 0:
            # if no sources specified for data layer, skip
            continue
        project_name, dataset_name = src[0].split("/")
        if dataset_name == "*":
            dataset_name = get_all_datasets(get_project_by_name(project_name).id)[0].name
        preview_path = f"{g.PREVIEW_DIR}/{project_name}/{dataset_name}"

        img_desc = ImageDescriptor(
            LegacyProjectItem(
                project_name=project_name,
                ds_name=dataset_name,
                image_name="preview_image",
                ia_data={"image_ext": ".jpg"},
                img_path=f"{preview_path}/preview_image.jpg",
                ann_path=f"{preview_path}/preview_ann.json",
            ),
            False,
        )
        ann = data_layer.get_ann()
        data_el = (img_desc, ann)

        processing_generator = net.start_iterate(data_el, skip_save_layers=True)
        for data_el, layer_indx in processing_generator:
            if layer_indx in updated:
                continue
            layer = g.layers[all_layers_ids[layer_indx]]
            layer: Layer
            if len(data_el) == 1:
                img_desc, ann = data_el[0]
            elif len(data_el) == 3:
                img_desc, ann, _ = data_el
            else:
                img_desc, ann = data_el
            layer.update_preview(img_desc, ann)
            layer.set_preview_loading(False)
            updated.add(layer_indx)
    net.preview_mode = False


def create_results_widget(file_infos, supervisely_layers):
    widgets = []
    if len(file_infos) > 0:
        widgets.append(
            Flexbox(
                widgets=[
                    Text("Archives: "),
                    *[FileThumbnail(file_info) for file_info in file_infos],
                ]
            )
        )
    if len(supervisely_layers) > 0:
        widgets.append(
            Flexbox(
                widgets=[
                    Text("Projects: "),
                    *[
                        ProjectThumbnail(update_project_info(l.sly_project_info))
                        for l in supervisely_layers
                    ],
                ]
            )
        )
    return Container(widgets=widgets)


def get_layer_id(action_name: str):
    g.layers_count += 1
    id = action_name + "_" + str(g.layers_count)
    return id


def register_layer(layer: Layer):
    g.layers[layer.id] = layer


def create_new_layer(
    action_name: str,
) -> Layer:
    try:
        action = actions[action_name]
    except KeyError:
        raise ActionNotFoundError(action_name)
    id = get_layer_id(action_name)
    action: Action
    try:
        layer = action.create_new_layer(id)
    except CustomException as e:
        e.extra["action_name"] = action_name
    except Exception as e:
        raise e
    register_layer(layer)
    return layer


def create_node(layer: Layer, position=None):
    try:
        node = layer.create_node()
    except CustomException as e:
        e.extra["layer_config"] = layer.to_json()
        raise e
    except Exception as e:
        raise e
    node.set_position(position)
    return node


def show_error(message: str, error: CustomException):
    description = str(error)
    if error.extra:
        g.error_extra_literal.show()
        extra_text = json.dumps(error.extra, indent=4)
    else:
        g.error_extra_literal.hide()
        extra_text = ""
    g.error_dialog.title = message
    g.error_description.text = description
    g.error_extra.set_text(extra_text)
    g.error_dialog.show()