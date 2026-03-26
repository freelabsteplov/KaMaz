import json
import os

import unreal


OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_rt_factory_api.json",
)


def main():
    payload = {
        "class_name": "",
        "candidate_names": [],
        "interesting_values": {},
        "error": "",
    }

    try:
        factory = unreal.TextureRenderTargetFactoryNew()
        payload["class_name"] = factory.get_class().get_name()
        payload["candidate_names"] = sorted(
            [
                name
                for name in dir(factory)
                if any(token in name.lower() for token in ("size", "width", "height", "format", "texture", "target"))
            ]
        )

        for prop_name in (
            "width",
            "height",
            "size_x",
            "size_y",
            "format",
            "render_target_format",
            "supported_class",
        ):
            try:
                payload["interesting_values"][prop_name] = str(factory.get_editor_property(prop_name))
            except Exception as exc:
                payload["interesting_values"][prop_name] = f"<error: {exc}>"
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
