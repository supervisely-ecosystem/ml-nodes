# coding: utf-8

import os
import re
from src.utils import LegacyProjectItem

from supervisely import sly_logger
from supervisely.app.widgets.sly_tqdm.sly_tqdm import CustomTqdm, Progress
from supervisely.sly_logger import logger, EventType

from src.compute.dtl_utils.dtl_helper import DtlHelper, DtlPaths
from src.compute.dtl_utils.image_descriptor import ImageDescriptor

from src.compute.tasks import task_helpers
from src.compute.tasks import progress_counter

from src.compute.utils import json_utils
from src.compute.utils import logging_utils

import supervisely as sly

from src.compute.Net import Net


def make_legacy_project_item(project: sly.Project, dataset, item_name):
    item_name_base, item_ext = os.path.splitext(item_name)
    return LegacyProjectItem(
        project_name=project.name,
        ds_name=dataset.name,
        image_name=item_name_base,
        ia_data={"image_ext": item_ext},
        img_path=dataset.get_img_path(item_name),
        ann_path=dataset.get_ann_path(item_name),
    )


def check_in_graph():
    helper = DtlHelper()
    net = Net(helper.graph, helper.in_project_metas, helper.paths.results_dir)
    net.validate()
    net.calc_metas()

    # to ensure validation
    is_archive = net.is_archive()

    need_download = net.may_require_images()
    return {"download_images": need_download, "is_archive": is_archive}


def calculate_datasets_conflict_map(helper):
    tmp_datasets_map = {}

    # Save all [datasets : projects] relations
    for _, pr_dir in helper.in_project_dirs.items():
        project = sly.Project(directory=pr_dir, mode=sly.OpenMode.READ)
        for dataset in project:
            projects_list = tmp_datasets_map.setdefault(dataset.name, [])
            projects_list.append(project.name)

    datasets_conflict_map = {}
    for dataset_name in tmp_datasets_map:
        projects_names_list = tmp_datasets_map[dataset_name]
        for project_name in projects_names_list:
            datasets_conflict_map[project_name] = datasets_conflict_map.get(project_name, {})
            datasets_conflict_map[project_name][dataset_name] = len(projects_names_list) > 1

    return datasets_conflict_map


def main(progress: Progress):
    task_helpers.task_verification(check_in_graph)

    logger.info("DTL started")
    helper = DtlHelper()

    try:
        net = Net(helper.graph, helper.paths.results_dir)
        net.validate()
        net.calc_metas()
        net.preprocess()
        datasets_conflict_map = calculate_datasets_conflict_map(helper)
    except Exception as e:
        logger.error("Error occurred on DTL-graph initialization step!")
        raise e

    total = net.get_total_elements()
    elements_generator = net.get_elements_generator()
    results_counter = 0
    with progress(message=f"Processing items...", total=total) as pbar:
        for data_el in elements_generator:
            try:
                export_output_generator = net.start(data_el)
                for res_export in export_output_generator:
                    logger.trace(
                        "image processed",
                        extra={"img_name": res_export[0][0].get_img_name()},
                    )
                    results_counter += 1
            except Exception as e:
                extra = {
                    "project_name": data_el[0].get_pr_name(),
                    "ds_name": data_el[0].get_ds_name(),
                    "image_name": data_el[0].get_img_name(),
                    "exc_str": str(e),
                }
                logger.warn(
                    "Image was skipped because some error occurred",
                    exc_info=True,
                    extra=extra,
                )
            finally:
                pbar.update()
            # progress.iter_done_report()
            # progress.update()

    # # is_archive = net.is_archive()
    # results_counter = 0
    # for pr_name, pr_dir in helper.in_project_dirs.items():
    #     project = sly.Project(directory=pr_dir, mode=sly.OpenMode.READ)
    #     # progress = progress_counter.progress_counter_dtl(pr_name, project.total_items)
    #     for dataset in project:
    #         dataset: sly.Dataset
    #         with progress(
    #             message=f"Processing items in {project.name}/{dataset.name}", total=len(dataset)
    #         ) as pbar:
    #             for item_name in dataset:
    #                 try:
    #                     img_desc = ImageDescriptor(
    #                         make_legacy_project_item(project, dataset, item_name),
    #                         datasets_conflict_map[project.name][dataset.name],
    #                     )
    #                     ann_json = json_utils.json_load(dataset.get_ann_path(item_name))
    #                     ann = sly.Annotation.from_json(ann_json, project.meta)
    #                     data_el = (img_desc, ann)
    #                     export_output_generator = net.start(data_el)
    #                     for res_export in export_output_generator:
    #                         logger.trace(
    #                             "image processed",
    #                             extra={"img_name": res_export[0][0].get_img_name()},
    #                         )
    #                         results_counter += 1
    #                 except Exception as e:
    #                     extra = {
    #                         "project_name": project.name,
    #                         "ds_name": dataset.name,
    #                         "image_name": item_name,
    #                         "exc_str": str(e),
    #                     }
    #                     logger.warn(
    #                         "Image was skipped because some error occurred",
    #                         exc_info=True,
    #                         extra=extra,
    #                     )
    #                 finally:
    #                     pbar.update()
    #                 # progress.iter_done_report()
    #                 # progress.update()

    logger.info(
        "DTL finished",
        extra={"event_type": EventType.DTL_APPLIED, "new_proj_size": results_counter},
    )
    return net


if __name__ == "__main__":
    if os.getenv("DEBUG_LOG_TO_FILE", None):
        sly_logger.add_default_logging_into_file(logger, DtlPaths().debug_dir)
    logging_utils.main_wrapper("DTL", main)
