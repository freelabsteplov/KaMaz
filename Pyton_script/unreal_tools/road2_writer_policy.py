import os


CANONICAL_ROAD2_WRITERS = {
    "apply_road_height_carrier_for_road2.py": "Canonical structural writer for the Road2 carrier, receiver tag, and trail actor defaults.",
    "rebuild_m_snowreceiver_rvt_height_mvp_berm.py": "Canonical shared parent material writer for the current Road2 MVP receiver corridor.",
    "apply_road2_material_only_pass.py": "Canonical active Road2 MI writer for the current Road2 MVP receiver corridor.",
}


BLOCKED_ROAD2_WRITERS = {
    "apply_road2_height_baseline_recovery.py": "Deprecated hybrid recovery script. It mixes carrier setup, MI writes, capture heuristics, and clear-mask polarity guesses.",
    "apply_road2_offline_baseline_height_plus50.py": "Deprecated one-off baseline override. It forces HeightAmplitude directly and conflicts with the canonical baseline split.",
    "fix_road2_active_mi_baseline_scalars.py": "Deprecated scalar override script. It writes conflicting HeightAmplitude and visual parameters into the active Road2 MI.",
    "fix_road2_receiver_visibility_baseline.py": "Deprecated shared parent patch. It mutates the active Road2 parent material outside the canonical rebuild path.",
    "apply_road2_visible_snow_whiten_inplace.py": "Deprecated in-place parent patch. It rewires the active Road2 parent graph outside the canonical rebuild path.",
    "apply_visible_snow_to_road_only_carrier.py": "Deprecated alternate Road2 writer. It duplicates and reassigns Road2 carrier materials outside the canonical MI path.",
    "set_road2_carrier_to_localheight_baseline.py": "Deprecated alternate Road2 MI switch. It redirects the active carrier to a local-height detour MI.",
    "rebuild_m_snowreceiver_rvt_height_mvp_clean.py": "Deprecated alternate parent rebuild. Road2 must use the canonical berm rebuild for the current MVP path.",
    "rebuild_visible_road_snow_receiver.py": "Deprecated alternate road receiver rebuild. It rewrites the same receiver corridor through a non-canonical path.",
    "offline_recover_road_receiver.py": "Deprecated recovery path. It is not part of the canonical Road2 writer set.",
    "recover_road_receiver_parent.py": "Deprecated parent-recovery path. It is not part of the canonical Road2 writer set.",
}


def _script_name(script_path_or_name: str) -> str:
    return os.path.basename(script_path_or_name or "")


def ensure_road2_writer_allowed(script_path_or_name: str) -> dict:
    script_name = _script_name(script_path_or_name)
    if script_name in BLOCKED_ROAD2_WRITERS:
        reason = BLOCKED_ROAD2_WRITERS[script_name]
        allowed = ", ".join(sorted(CANONICAL_ROAD2_WRITERS.keys()))
        raise RuntimeError(
            "Road2 writer policy blocked '{0}'. {1} Allowed Road2 writers: {2}".format(
                script_name,
                reason,
                allowed,
            )
        )

    return {
        "script_name": script_name,
        "is_canonical": script_name in CANONICAL_ROAD2_WRITERS,
        "canonical_writers": sorted(CANONICAL_ROAD2_WRITERS.keys()),
        "blocked_writers": sorted(BLOCKED_ROAD2_WRITERS.keys()),
    }
