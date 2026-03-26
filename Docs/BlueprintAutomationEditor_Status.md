# BlueprintAutomationEditor: What Works / What Does Not

## Short Description

`BlueprintAutomationEditor` is an editor-only Unreal Engine plugin for safe,
controlled work with Blueprint assets and Blueprint graphs.

It is not a gameplay plugin.
It is not a runtime snow system.
It is not a general executor.

In this project it acts as the safe C++ layer under our Unreal Python helpers.

## What Works

The plugin currently works well for editor-side Blueprint operations:

- load Blueprint by asset path or object path
- create Blueprint assets
- add simple variables
- add SCS components
- open EventGraph or a named graph
- inspect Blueprint graphs to JSON
- inspect nodes and linked pins
- scan available Blueprint actions
- resolve actions by signature
- create graph nodes:
  - function call
  - variable get
  - variable set
  - custom event
  - event by signature
  - dynamic cast
- link pins through schema-safe validation
- apply graph batches from JSON
- compile Blueprint and collect messages
- save Blueprint packages

Practical result in `Kamaz_Cleaner`:

- `KamazBP` was inspected and compiled through this plugin
- `BP_PlowBrush_Component` was inspected and compiled through this plugin
- graph snapshots were exported into `Saved\BlueprintAutomation`
- batch-style graph editing is already in active use through the Python bridge

## What Works Well In This Project Specifically

For `Kamaz_Cleaner`, the plugin is already proven useful for:

- exporting `KamazBP` graph snapshots
- exporting `BP_PlowBrush_Component` graph snapshots
- finding actual node wiring instead of guessing
- compiling after controlled Blueprint edits
- saving those edits safely
- powering project-local helpers in:
  - `Pyton_script/unreal_tools`

This means the plugin itself is alive and operational.

## What Does Not Work

The plugin does not do these things:

- it does not run gameplay logic at runtime
- it does not drive PIE behavior directly
- it does not solve material graph issues by itself
- it does not edit materials as its main responsibility
- it does not manage `MOZA` or any input hardware path
- it does not replace Unreal Python or higher-level orchestration
- it does not understand project intent without an external tool layer

Important practical point:

- if snow is not visible or live plow writing is not happening, that is not
  automatically a plugin failure
- in the current project, the strongest blocker is in runtime BP/material-side
  logic, not in `BlueprintAutomationEditor`

## Current Known Limits

These are the real limits of the plugin today:

- editor-only
- action index is a snapshot, not a live subscribed model
- some node signatures are version-sensitive across UE 5.1-5.7
- `SpawnerSignature` stability depends on Unreal internals
- high-level graph planning still belongs in the Python/tool layer
- material editing workflows are outside the plugin's main scope

## Bridge Layer Above The Plugin

The plugin is used through:

- Unreal Python bridge:
  - `UBlueprintAutomationPythonBridge`
- project helper scripts:
  - `Pyton_script/unreal_tools/*.py`

So the working stack is:

1. `BlueprintAutomationEditor` provides safe primitive operations
2. Python helpers compose them into actual project workflows
3. JSON diagnostics are written into `Saved\BlueprintAutomation`

## Current Conclusion

For this project, the plugin status is:

- working for Blueprint inspection
- working for Blueprint graph mutation
- working for compile/save
- working as the safe automation backbone
- not the primary cause of the current snow runtime blocker

Short version:

- Blueprint tooling layer: works
- runtime snow behavior: still needs BP/material-side fixes
