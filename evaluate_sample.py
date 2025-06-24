import torch

import argparse
import pickle as pkl

import decord
from decord import VideoReader
import numpy as np
import yaml

from dover.datasets import UnifiedFrameSampler, spatial_temporal_view_decomposition, get_single_view
from dover.models import DOVER

mean, std = (
    torch.FloatTensor([123.675, 116.28, 103.53]),
    torch.FloatTensor([58.395, 57.12, 57.375]),
)

def exp_func(x):
    return 1 / (1 + np.exp(-x))

def fuse_results(results: list):
    norm_x0 = (results[0] - 0.1107) / 0.07355
    norm_x1 = (results[1] + 0.08285) / 0.03774
    x = norm_x0 * 0.6104 + norm_x1 * 0.3896
    # print(x)
    return exp_func(x), exp_func(norm_x0), exp_func(norm_x1)


def gaussian_rescale(pr):
    # The results should follow N(0,1)
    pr = (pr - np.mean(pr)) / np.std(pr)
    return pr


def uniform_rescale(pr):
    # The result scores should follow U(0,1)
    return np.arange(len(pr))[np.argsort(pr).argsort()] / len(pr)


def build_model(opt):
    ### Load DOVER
    device = "cuda"
    evaluator = DOVER(**opt["model"]["args"]).to(device)
    evaluator.load_state_dict(
        torch.load(opt["test_load_path"], map_location=device)
    )
    return evaluator


def calculate_dover_score(opt, evaluator, video_path):

    device = "cuda"
    dopt = opt["data"]["val-l1080p"]["args"]

    # read video and fps
    decord.bridge.set_bridge("torch")
    vreader = VideoReader(video_path)

    # based on the clip len, calculate the frame interval, and the number of clips
    # num clips should be min(dopt["sample_types"]["technical"]["num_clips"], possible_num_clips)
    possible_num_clips = len(vreader) // dopt["sample_types"]["technical"]["clip_len"]
    num_clips = min(dopt["sample_types"]["technical"]["num_clips"], possible_num_clips)
    frame_interval = len(vreader) // (num_clips * dopt["sample_types"]["technical"]["clip_len"])
    # print(f"num_clips: {num_clips}, frame_interval: {frame_interval}")
    dopt["sample_types"]["technical"]["num_clips"] = num_clips
    dopt["sample_types"]["technical"]["frame_interval"] = frame_interval
    

    temporal_samplers = {}
    for stype, sopt in dopt["sample_types"].items():
        if "t_frag" not in sopt:
            # resized temporal sampling for TQE in DOVER
            temporal_samplers[stype] = UnifiedFrameSampler(
                sopt["clip_len"], sopt["num_clips"], sopt["frame_interval"]
            )
        else:
            # temporal sampling for AQE in DOVER
            temporal_samplers[stype] = UnifiedFrameSampler(
                sopt["clip_len"] // sopt["t_frag"],
                sopt["t_frag"],
                sopt["frame_interval"],
                sopt["num_clips"],
            )

    samplers = temporal_samplers

    ### Avoid duplicated video decoding!!! Important!!!!
    all_frame_inds = []
    frame_inds = {}
    for stype in samplers:
        frame_inds[stype] = samplers[stype](len(vreader), False)
        all_frame_inds.append(frame_inds[stype])
    # print(all_frame_inds)
    ### Each frame is only decoded one time!!!
    all_frame_inds = np.concatenate(all_frame_inds, 0)
    frame_dict = {idx: vreader[idx] for idx in np.unique(all_frame_inds)}

    video = {}
    for stype in samplers:
        imgs = [frame_dict[idx] for idx in frame_inds[stype]]
        video[stype] = torch.stack(imgs, 0).permute(3, 0, 1, 2)

    sampled_video = {}
    for stype, sopt in dopt["sample_types"].items():
        sampled_video[stype] = get_single_view(video[stype], stype, **sopt)

    views = sampled_video
    # ### View Decomposition
    # views, _ = spatial_temporal_view_decomposition(
    #     args.video_path, dopt["sample_types"], temporal_samplers
    # )

    for k, v in views.items():
        num_clips = dopt["sample_types"][k].get("num_clips", 1)
        views[k] = (
            ((v.permute(1, 2, 3, 0) - mean) / std)
            .permute(3, 0, 1, 2)
            .reshape(v.shape[0], num_clips, -1, *v.shape[2:])
            .transpose(0, 1)
            .to(device)
        )

    # print(views.keys())

    results = [r.mean().item() for r in evaluator(views)]
    output, technical, aesthetic = fuse_results(results)
    return output, technical, aesthetic



