# BlueprintAutomationEditor

`BlueprintAutomationEditor` is an editor-only Unreal Engine plugin for controlled automation of Blueprint assets and Blueprint graphs from C++.

The plugin is designed as a safe tool layer for GPT/MCP/local bridge integrations. It does not expose arbitrary code execution. Instead, it exposes narrow, explicit operations such as:

- create/load Blueprint assets
- add variables
- add components through SCS
- compile and save Blueprints
- inspect Event Graphs
- create graph nodes
- link pins
- scan Blueprint action database
- resolve and spawn actions by signature

## Scope

This plugin is intended for editor-side automation only.

- It is not a runtime gameplay system.
- It is not based on Python as the primary mechanism.
- It is not a general-purpose executor.
- It is meant to be called from higher-level tooling that already decides what operation should run.

## Module

- Plugin: `BlueprintAutomationEditor`
- Module type: `Editor`
- Loading phase: `Default`

Descriptor:
- `BlueprintAutomationEditor.uplugin`

## Architecture

The plugin is split into service layers.

### 1. Asset/SCS layer

Header:
- `Source/BlueprintAutomationEditor/Public/BlueprintAutomationService.h`

Purpose:
- create Blueprint assets
- load Blueprint assets
- add primitive variables
- add SCS components
- compile/save Blueprint packages

Primary APIs:
- `CreateBlueprintAsset(...)`
- `LoadBlueprintByAssetPath(...)`
- `LoadBlueprintByObjectPath(...)`
- `AddVariable(...)`
- `AddComponent(...)`
- `CompileBlueprint(...)`
- `SaveBlueprint(...)`

### 2. Graph node layer

Header:
- `Source/BlueprintAutomationEditor/Public/BlueprintGraphAutomationService.h`

Purpose:
- access `EventGraph`
- create `CallFunction` nodes
- create variable get/set nodes
- create custom events
- spawn event nodes by signature
- inspect nodes/graphs to JSON
- link pins safely through schema rules

Primary APIs:
- `GetEventGraph(...)`
- `CreateCallFunctionNode(...)`
- `CreateVariableGetNode(...)`
- `CreateVariableSetNode(...)`
- `CreateCustomEventNode(...)`
- `SpawnEventNodeBySignature(...)`
- `LinkPins(...)`
- `InspectGraphToJson(...)`

### 3. Action discovery/spawn layer

Header:
- `Source/BlueprintAutomationEditor/Public/BlueprintActionAutomationService.h`

Purpose:
- build a typed snapshot of currently available Blueprint actions
- export action index to JSON
- resolve actions by spawner signature
- search actions by text
- validate action availability in context
- spawn actions through `UBlueprintNodeSpawner`
- compile and collect compiler diagnostics

Primary APIs:
- `RefreshNodeIndex()`
- `ScanAvailableBlueprintActions(...)`
- `ExportBlueprintActionIndexToJson(...)`
- `ResolveActionBySignature(...)`
- `ResolveActionsByTextQuery(...)`
- `ValidateActionInContext(...)`
- `SpawnActionBySignature(...)`
- `ValidateSpawnInSandboxBlueprint(...)`
- `CompileBlueprintAndCollectMessages(...)`

## Typed action model

The action layer supports a typed index on top of the live Unreal action database.

Key types:
- `EBlueprintActionScanMode`
- `FBlueprintActionIndexPin`
- `FBlueprintActionIndexEntry`
- `FBlueprintActionIndexContext`
- `FBlueprintActionIndexDocument`
- `FBlueprintCompileMessage`
- `FBlueprintCompileReport`

Design rules:
- primary key is `SpawnerSignature`
- live `FBlueprintActionDatabase` remains the source of truth
- typed document is a snapshot for bridge-side querying/export
- legacy JSON API remains available for backward compatibility

## Safety model

The plugin is built around narrow editor operations instead of arbitrary execution.

Safety properties:
- no raw text-to-code execution path
- no unrestricted shell/Python dependency
- graph mutations go through explicit service methods
- graph linking uses schema validation instead of unsafe direct pin mutation
- action validation can run in a transient sandbox Blueprint before touching a real asset

This is the intended integration model for GPT:

1. bridge/tool layer receives a request
2. bridge maps request to one explicit plugin operation
3. plugin executes a bounded editor action
4. plugin returns a structured result or JSON payload

## Typical use cases

- generate a new Actor Blueprint and add standard variables/components
- create a graph skeleton from a planned tool call sequence
- inspect available Blueprint actions after enabling new engine plugins
- search for nodes/functions by text or by signature
- validate whether a node can legally spawn in a specific Blueprint graph
- compile a Blueprint and return warnings/errors to an external agent

## Intended bridge integration

This plugin is suitable as the Unreal-side execution layer for:

- GPT tool calling
- MCP server adapters
- local editor automation bridges
- controlled internal authoring tools

Recommended mapping style:
- one bridge tool maps to one service method
- request/response payloads should stay structured
- do not expose plugin internals directly as an unrestricted command channel

## Python bridge

The plugin now exposes a small `UBlueprintFunctionLibrary` wrapper for Unreal Python:

- `run_smoke_test()`
- `refresh_action_index()`
- `inspect_blueprint_event_graph(asset_path, include_pins=True, include_linked_pins=True)`
- `scan_blueprint_actions(asset_path, context_sensitive=True)`
- `compile_blueprint(asset_path)`
- `apply_graph_batch_json(asset_path, batch_json)`
- `save_blueprint(asset_path)`

Direct Output Log -> Python example:

```python
import unreal
print(unreal.BlueprintAutomationPythonBridge.run_smoke_test())
print(unreal.BlueprintAutomationPythonBridge.inspect_blueprint_event_graph("/Game/CityPark/Kamaz/model/KamazBP"))
```

Convenience helper script for the current project:

- `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Pyton_script\unreal_tools\blueprint_automation_tools.py`

Typical helper usage:

```python
import sys
sys.path.append(r"C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Pyton_script\unreal_tools")
import blueprint_automation_tools as bat
print(bat.run_smoke_test())
print(bat.inspect_kamazbp_graph())
print(bat.scan_kamazbp_actions())
print(bat.compile_kamazbp())
print(bat.export_kamazbp_snapshot())
```

## Console commands

For normal Output Log `Cmd` mode, the plugin also exposes editor console commands:

- `BlueprintAutomation.RunSmokeTest`
- `BlueprintAutomation.ExportKamazBPSnapshot`
- `BlueprintAutomation.ExportBlueprintSnapshot /Game/Path/BP_Name [file_prefix]`

Examples:

```text
BlueprintAutomation.RunSmokeTest
BlueprintAutomation.ExportKamazBPSnapshot
BlueprintAutomation.ExportBlueprintSnapshot /Game/CityPark/Kamaz/model/KamazBP kamazbp
```

Snapshot files are written to:

- `Saved\BlueprintAutomation`

## Build and environment

The plugin is built as part of the project editor target.

Expected environment:
- Unreal Engine 5.x editor build
- Visual Studio toolchain
- editor modules available (`UnrealEd`, `Kismet`, `BlueprintGraph`, etc.)

## Known limitations

- The plugin is editor-only.
- Typed action index is a snapshot, not a live subscribed view.
- `SpawnerSignature` stability depends on Unreal internals and installed engine/plugins.
- Some Blueprint node capabilities remain version-sensitive across UE 5.1-5.7.
- Impure variable get support may require deeper engine-facing handling depending on export visibility in the current engine build.
- Full high-level graph planning/patching still belongs in the bridge layer or in future higher-order APIs.

## Recommended workflow

1. Refresh the action database when engine/plugin state changes.
2. Scan/export the action index.
3. Resolve actions by signature or text query.
4. Validate action usage in the target Blueprint/graph.
5. Spawn nodes and wire them through graph services.
6. Compile and inspect compiler messages.
7. Save only after validation passes.

## Next extension points

Natural next steps for the plugin:

- richer query/filter APIs for action search
- graph patching helpers against existing node sets
- stable schema versioning for JSON payloads
- transaction batching across multi-step graph edits
- higher-level Blueprint templates for common generation workflows
