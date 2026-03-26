import json
import os

import unreal


OUT = os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation", "blueprint_editor_library_methods.json")

methods = []
for name in dir(unreal.BlueprintEditorLibrary):
    if name.startswith("_"):
        continue
    if "graph" in name.lower() or "node" in name.lower() or "blueprint" in name.lower():
        methods.append(name)

payload = {
    "count": len(methods),
    "methods": sorted(methods),
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, ensure_ascii=False)

print(json.dumps({"output": OUT, "count": len(methods)}))
