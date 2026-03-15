import json
import os

import unreal


OUTPUT_BASENAME = "subobject_api"


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    unreal.log(f"[inspect_subobject_api] Wrote file: {path}")
    return path


def _callable_names(obj):
    names = []
    for name in dir(obj):
        if name.startswith("_"):
            continue
        try:
            value = getattr(obj, name)
        except Exception:
            continue
        if callable(value):
            names.append(name)
    return sorted(names)


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    payload = {
        "has_SubobjectDataSubsystem": hasattr(unreal, "SubobjectDataSubsystem"),
        "has_SubobjectDataBlueprintFunctionLibrary": hasattr(unreal, "SubobjectDataBlueprintFunctionLibrary"),
        "subsystem_methods": [],
        "library_methods": [],
        "get_engine_subsystem_error": "",
        "get_editor_subsystem_error": "",
    }

    subsystem_class = getattr(unreal, "SubobjectDataSubsystem", None)
    if subsystem_class is not None:
        payload["subsystem_methods"] = _callable_names(subsystem_class)
        try:
            subsystem = unreal.get_engine_subsystem(subsystem_class)
            payload["engine_subsystem_type"] = str(type(subsystem))
            payload["engine_subsystem_methods"] = _callable_names(subsystem)
        except Exception as exc:
            payload["get_engine_subsystem_error"] = str(exc)

        try:
            subsystem = unreal.get_editor_subsystem(subsystem_class)
            payload["editor_subsystem_type"] = str(type(subsystem))
            payload["editor_subsystem_methods"] = _callable_names(subsystem)
        except Exception as exc:
            payload["get_editor_subsystem_error"] = str(exc)

    library_class = getattr(unreal, "SubobjectDataBlueprintFunctionLibrary", None)
    if library_class is not None:
        payload["library_methods"] = _callable_names(library_class)

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, payload)
    payload["output_path"] = output_path
    return payload


if __name__ == "__main__":
    print(run())
