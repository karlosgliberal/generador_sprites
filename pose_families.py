"""Pose families: group animations by body pose type.

Each family has its own reference frame, prompt suffix, and set of parts
generated from an avatar matching that pose.
"""

from __future__ import annotations

POSE_FAMILIES: dict[str, dict] = {
    "neutral": {
        "animations": ["idle", "walk"],
        "reference_frame": "idle/frame_00.png",
        "description": "standing upright, arms at sides",
        "prompt_suffix": "",
    },
    "attack": {
        "animations": ["punch", "sword_attack"],
        "reference_frame": "punch/frame_04.png",
        "description": "arm extended forward in attack pose",
        "prompt_suffix": "arm extended forward, attacking pose",
    },
    "airborne": {
        "animations": ["jump", "run"],
        "reference_frame": "jump/frame_02.png",
        "description": "legs bent, body compact, mid-air",
        "prompt_suffix": "jumping mid-air, legs bent",
    },
    "collapsed": {
        "animations": ["death"],
        "reference_frame": "death/frame_09.png",
        "description": "body horizontal, collapsed on ground",
        "prompt_suffix": "lying horizontal on ground, defeated, collapsed",
    },
}

# Reverse lookup: animation name -> family name
_ANIM_TO_FAMILY: dict[str, str] = {}
for _family, _info in POSE_FAMILIES.items():
    for _anim in _info["animations"]:
        _ANIM_TO_FAMILY[_anim] = _family


def family_for_animation(animation: str) -> str:
    """Return the pose family name for a given animation. Falls back to 'neutral'."""
    return _ANIM_TO_FAMILY.get(animation, "neutral")


def all_families() -> list[str]:
    """Return list of all family names."""
    return list(POSE_FAMILIES.keys())
