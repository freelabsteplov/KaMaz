## Goal
Implement a production-ready prototype architecture for a 3D main menu scene in KAMAZ where the player configures the truck, preview updates live in a dedicated menu level, and the chosen setup is passed into the gameplay level.

## Hypothesis
The cleanest Unreal-first solution is a Blueprint-centric flow:
- a dedicated `MenuLevel`
- a persistent `BP_KamazGameInstance` that stores the current session selection
- a world actor `BP_MenuManager` that owns preview scene logic
- UMG widgets that only edit data and send commands to the manager
- Data Assets that define vehicles, maps, environment presets, and camera behavior without hardcoded branches

This keeps menu logic out of Level Blueprint, scales to more trucks and maps, and lets the gameplay level read one consistent selection payload on load.

## Files To Touch
- `Content/BPs/BP_KamazGameInstance`
- `Content/BPs/BP_MenuGameMode`
- `Content/BPs/BP_MenuPlayerController`
- `Content/BPs/BP_KamazLevelRuntimeConfigApplier`
- `Content/CityPark/Kamaz/Menu/Levels/MenuLevel`
- `Content/CityPark/Kamaz/Menu/Blueprints/BP_MenuManager`
- `Content/CityPark/Kamaz/Menu/Blueprints/BP_MenuVehiclePreview`
- `Content/CityPark/Kamaz/Menu/Blueprints/BP_MenuCameraRig`
- `Content/CityPark/Kamaz/Menu/Blueprints/BP_MenuEnvironmentController`
- `Content/CityPark/Kamaz/Menu/Widgets/WBP_MainMenu3D`
- `Content/CityPark/Kamaz/Menu/Widgets/WBP_MenuTabButton`
- `Content/CityPark/Kamaz/Menu/Widgets/WBP_OptionCard`
- `Content/CityPark/Kamaz/Menu/Widgets/WBP_MapCard`
- `Content/CityPark/Kamaz/Menu/Widgets/WBP_SelectionSummary`
- `Content/CityPark/Kamaz/Menu/Structs/S_MenuSelection`
- `Content/CityPark/Kamaz/Menu/Structs/S_MenuEnvironmentOptions`
- `Content/CityPark/Kamaz/Menu/Enums/E_MenuLightingMode`
- `Content/CityPark/Kamaz/Menu/Enums/E_VehicleType`
- `Content/CityPark/Kamaz/Menu/Data/DA_VehicleData_*`
- `Content/CityPark/Kamaz/Menu/Data/DA_MapData_*`
- `Content/CityPark/Kamaz/Menu/Data/DA_MenuCatalog`

## Ordered Steps
1. Create persistent selection storage.
2. Create Data Assets for vehicles, maps, and menu catalog lists.
3. Create a dedicated `MenuLevel` with cinematic lighting and a preview stage.
4. Add `BP_MenuManager` to the level as the orchestration actor.
5. Add `BP_MenuVehiclePreview` for spawn/swap of the preview truck actor.
6. Add `BP_MenuCameraRig` for idle orbit and focus shots.
7. Add `BP_MenuEnvironmentController` to toggle snow, forest, and day/night preview.
8. Build `WBP_MainMenu3D` with `WidgetSwitcher` for sections:
   - Truck
   - Type
   - Map
   - Environment
   - Summary
9. Bind each UI action to update `S_MenuSelection`.
10. On each change, send the full selection to `BP_MenuManager.ApplySelection`.
11. On `Start`, save selection in `BP_KamazGameInstance` and `Open Level` using the selected map asset.
12. In gameplay levels, place `BP_KamazLevelRuntimeConfigApplier` or handle the same read in your gameplay `GameMode` so the chosen truck/environment/light settings are applied on `BeginPlay`.
13. Switch `GameDefaultMap` to `MenuLevel` only after the menu flow is verified.

## Invariants / Do-Not-Break Rules
- Do not modify the existing gameplay truck Blueprint `/Game/CityPark/Kamaz/model/KamazBP` until the menu flow is proven.
- Keep menu orchestration out of Level Blueprint; use dedicated actors and widgets.
- Avoid hardcoded level names and truck classes inside widgets.
- Keep the UI layer presentation-only; world changes must go through `BP_MenuManager`.
- Preserve the current gameplay startup path for `MoscowEA5` until menu validation is complete.
- Use `GameInstance` only for session state, not for scene logic.

## Validation
- Launch project into `MenuLevel`.
- Confirm `WBP_MainMenu3D` appears and mouse input works.
- Change vehicle and verify the preview actor swaps cleanly.
- Change day/night and verify lighting changes without reloading level.
- Toggle snow and forest and verify preview scene updates immediately.
- Click `Start` and verify the target gameplay map opens.
- On gameplay map `BeginPlay`, print the loaded `S_MenuSelection` and verify all fields match the last menu state.
- Only after that, update `Config/DefaultEngine.ini` so `GameDefaultMap=/Game/CityPark/Kamaz/Menu/Levels/MenuLevel`.

## Rollback Notes
- Reset `GameDefaultMap` back to `/Game/Maps/MoscowEA5.MoscowEA5`.
- Remove `BP_MenuManager` and `WBP_MainMenu3D` from `MenuLevel`.
- Remove `BP_KamazGameInstance` assignment if it causes boot issues.
- Fall back to direct play into the existing gameplay map while keeping menu assets isolated in their folder.

## Architecture

### Core Runtime Responsibilities

- `BP_KamazGameInstance`
  - stores `CurrentMenuSelection : S_MenuSelection`
  - exposes:
    - `SetCurrentMenuSelection`
    - `GetCurrentMenuSelection`
    - `ResetMenuSelectionToDefaults`

- `BP_MenuManager`
  - single source of truth for live menu scene behavior
  - holds references to:
    - `BP_MenuVehiclePreview`
    - `BP_MenuCameraRig`
    - `BP_MenuEnvironmentController`
    - `WBP_MainMenu3D`
    - `DA_MenuCatalog`
  - exposes:
    - `InitializeMenu`
    - `ApplySelection`
    - `UpdateVehiclePreview`
    - `UpdateEnvironmentPreview`
    - `UpdateLightingPreview`
    - `StartGame`

- `BP_MenuVehiclePreview`
  - spawns preview truck actor from selected `DA_VehicleData`
  - destroys previous preview actor safely
  - owns preview platform offset, wheel angle pose, optional slow rotation of the truck or turntable

- `BP_MenuCameraRig`
  - holds:
    - `CineCameraActor` or camera component
    - focus target scene component
    - spline or orbit parameters
  - provides:
    - idle orbit
    - `FocusOnVehicleFront`
    - `FocusOnCabin`
    - `FocusOnWheel`
    - `PlayStartTransition`

- `BP_MenuEnvironmentController`
  - toggles preview-only actors or Data Layers:
    - snow meshes / decals / particles
    - forest set dressing
    - day lighting set
    - night lighting set
  - updates fog, skylight, emissive accents, and optional VFX

- `BP_KamazLevelRuntimeConfigApplier`
  - placed in gameplay levels
  - on `BeginPlay` reads `BP_KamazGameInstance.CurrentMenuSelection`
  - applies:
    - chosen vehicle class or spawn setup
    - snow on/off
    - forest on/off
    - day/night
  - this can later move into GameMode or a World Subsystem if the project grows

### Data Layer

- `S_MenuEnvironmentOptions`
  - `bSnowEnabled : bool`
  - `bForestEnabled : bool`
  - `LightingMode : E_MenuLightingMode`

- `S_MenuSelection`
  - `SelectedVehicleId : Name`
  - `SelectedVehicleType : E_VehicleType`
  - `SelectedMapId : Name`
  - `EnvironmentOptions : S_MenuEnvironmentOptions`

- `DA_VehicleData`
  - `VehicleId : Name`
  - `DisplayName : Text`
  - `Description : Text`
  - `VehicleType : E_VehicleType`
  - `PreviewActorClass : Soft Class Reference`
  - `GameplayPawnClass : Soft Class Reference`
  - `PreviewOffset : Transform`
  - `CameraFocusSocketName : Name`
  - `Thumbnail : Texture2D`
  - `AccentColor : LinearColor`
  - `bSupportsSnow : bool`
  - `bSupportsForest : bool`

- `DA_MapData`
  - `MapId : Name`
  - `DisplayName : Text`
  - `MapLevel : Soft Object Reference`
  - `Thumbnail : Texture2D`
  - `Description : Text`
  - `DefaultSpawnTag : Name`
  - `bSupportsSnowToggle : bool`
  - `bSupportsForestToggle : bool`
  - `bSupportsDayNight : bool`
  - `PreviewBackdropTag : Name`

- `DA_MenuCatalog`
  - `Vehicles : Array<DA_VehicleData>`
  - `Maps : Array<DA_MapData>`
  - optional defaults:
    - `DefaultVehicleId`
    - `DefaultMapId`
    - `DefaultLightingMode`
    - `bDefaultSnowEnabled`
    - `bDefaultForestEnabled`

## Recommended Asset and Blueprint List

- Global classes
  - `BP_KamazGameInstance`
  - `BP_MenuGameMode`
  - `BP_MenuPlayerController`
  - `BP_KamazLevelRuntimeConfigApplier`

- Menu actors
  - `BP_MenuManager`
  - `BP_MenuVehiclePreview`
  - `BP_MenuCameraRig`
  - `BP_MenuEnvironmentController`
  - optional:
    - `BP_MenuTurntable`
    - `BP_MenuBackdropStage`

- Widgets
  - `WBP_MainMenu3D`
  - `WBP_MenuTabButton`
  - `WBP_OptionCard`
  - `WBP_MapCard`
  - `WBP_SelectionSummary`
  - optional:
    - `WBP_MenuAnimatedStat`
    - `WBP_StartButton`

- Structs / enums
  - `S_MenuSelection`
  - `S_MenuEnvironmentOptions`
  - `E_MenuLightingMode`
  - `E_VehicleType`

- Data Assets
  - `DA_MenuCatalog`
  - `DA_VehicleData_KamazBase`
  - `DA_VehicleData_KamazSnowplow`
  - `DA_MapData_MoscowEA5`
  - `DA_MapData_SnowTest`
  - `DA_MapData_ClumbiTverskay`

## Blueprint Ownership and Relationships

- `BP_MenuGameMode`
  - uses `BP_MenuPlayerController`
  - does not own logic beyond startup class assignment

- `BP_MenuPlayerController`
  - enables mouse cursor
  - sets input mode `Game and UI`
  - can own fade transition if desired

- `MenuLevel`
  - contains:
    - `BP_MenuManager`
    - `BP_MenuCameraRig`
    - `BP_MenuEnvironmentController`
    - static stage meshes, lights, fog, VFX

- `BP_MenuManager`
  - creates `WBP_MainMenu3D`
  - reads `DA_MenuCatalog`
  - seeds default `S_MenuSelection`
  - pushes initial preview

- `WBP_MainMenu3D`
  - raises events only:
    - `OnVehicleChanged`
    - `OnVehicleTypeChanged`
    - `OnMapChanged`
    - `OnSnowToggled`
    - `OnForestToggled`
    - `OnLightingChanged`
    - `OnStartClicked`
  - should not directly spawn actors or open levels except via `BP_MenuManager`

## Why This Layout

- `WidgetSwitcher`
  - best for tabbed configurator sections without creating multiple full-screen widgets
  - keeps transitions clean and supports staged focus shots

- `BP_MenuManager` instead of Level Blueprint
  - reusable
  - testable
  - easier to move between levels
  - safer when the menu becomes more complex

- `GameInstance` for selection state
  - survives `Open Level`
  - simple in Blueprints
  - ideal for the exact "menu -> gameplay" payload

- Data Assets for options
  - avoid switch/case sprawl
  - allow adding vehicles and maps without changing widget logic
  - support designer-friendly authoring

## Detailed Step-by-Step Implementation

### Phase 1. Session State

1. Create enum `E_MenuLightingMode`
   - `Day`
   - `Night`

2. Create enum `E_VehicleType`
   - `BaseTruck`
   - `Snowplow`
   - `Service`
   - expand later as needed

3. Create struct `S_MenuEnvironmentOptions`
   - `bSnowEnabled`
   - `bForestEnabled`
   - `LightingMode`

4. Create struct `S_MenuSelection`
   - `SelectedVehicleId`
   - `SelectedVehicleType`
   - `SelectedMapId`
   - `EnvironmentOptions`

5. Create `BP_KamazGameInstance`
   - variable `CurrentMenuSelection`
   - function `SetCurrentMenuSelection(NewSelection)`
   - function `GetCurrentMenuSelection`
   - function `ResetMenuSelectionToDefaults`

6. Assign it in project settings:
   - `Maps & Modes -> Game Instance Class`

### Phase 2. Data Assets

1. Create `DA_VehicleData` Blueprintable Data Asset class.
2. Create one asset per truck variant.
3. For now point preview and gameplay to the existing truck:
   - `/Game/CityPark/Kamaz/model/KamazBP`
4. Create `DA_MapData` assets for:
   - `MoscowEA5`
   - `SnowTest_Level`
   - `Clumbi_Tverskay`
5. Create `DA_MenuCatalog` and fill arrays.

Important rule:
- widgets read display info from Data Assets
- `BP_MenuManager` resolves the selected asset by `Id`

### Phase 3. Menu Level

1. Create `MenuLevel`.
2. Set `BP_MenuGameMode` as level GameMode override.
3. Build a controlled stage:
   - central platform for the truck
   - background walls or large hangar panels
   - floor reflections
   - practical spotlights
   - volumetric fog
4. Place `BP_MenuManager`.
5. Place `BP_MenuCameraRig`.
6. Place `BP_MenuEnvironmentController`.

### Phase 4. Preview Truck

1. Create `BP_MenuVehiclePreview`.
2. Give it:
   - `PreviewRoot`
   - `VehicleSocketRoot`
   - optional rotating turntable mesh
3. Function `SpawnPreviewVehicle(DA_VehicleData VehicleData)`
   - if `CurrentPreviewActor` valid -> destroy actor
   - async or sync load `PreviewActorClass`
   - spawn actor deferred
   - attach to `VehicleSocketRoot`
   - apply `PreviewOffset`
   - disable player input / AI / gameplay startup if needed
4. Optional:
   - set wheel steer angle pose
   - animate cabin lights for night mode

### Phase 5. Camera

1. Create `BP_MenuCameraRig`.
2. Use either:
   - `SpringArm + Camera`
   - or a placed `CineCameraActor`
3. Recommended behavior:
   - idle slow orbit around the truck
   - subtle vertical sine drift
   - tab-based focus shots
4. Exposed functions:
   - `SetOrbitEnabled(bool)`
   - `FocusVehicleHero`
   - `FocusVehicleFront`
   - `FocusCabin`
   - `FocusWheel`
   - `PlayStartTransition`

### Phase 6. Environment Preview

1. Create `BP_MenuEnvironmentController`.
2. Add references to:
   - day directional light
   - night directional or moon light
   - skylights
   - fog settings
   - emissive strip lights
   - snow particle system
   - forest dressing actors or Data Layers
3. Function `ApplyEnvironmentOptions(S_MenuEnvironmentOptions Options)`
   - if `bSnowEnabled`:
     - show snow dressing
     - enable snow VFX
     - swap floor decals/material accents to icy version
   - else:
     - hide snow dressing
   - if `bForestEnabled`:
     - show tree cards / rocks / edge dressing
   - else:
     - hide forest set
   - switch day/night light rig

Recommended implementation:
- if preview level uses UE5 World Partition, prefer Data Layers
- if not, simply toggle grouped actors from this controller

### Phase 7. UI

1. Create `WBP_MainMenu3D`.
2. Layout:
   - left or bottom-left main control panel
   - center remains visually open for truck presentation
   - right small summary stack
3. Use `WidgetSwitcher` for tabs:
   - Truck
   - Type
   - Map
   - Environment
   - Summary
4. Use reusable `WBP_OptionCard` for each choice card.
5. Use `WBP_MapCard` for map selection.
6. Add `Start` button in a fixed premium CTA block.

### Phase 8. Manager Wiring

1. On `BP_MenuManager.BeginPlay`
   - create widget `WBP_MainMenu3D`
   - add to viewport
   - read `DA_MenuCatalog`
   - build default `S_MenuSelection`
   - call `ApplySelection(DefaultSelection)`

2. In widget, every change should call manager with the updated full struct.

3. `BP_MenuManager.ApplySelection`
   - cache selection
   - resolve selected vehicle asset
   - resolve selected map asset
   - call preview update functions
   - update widget summary

### Phase 9. Gameplay Apply

1. Create `BP_KamazLevelRuntimeConfigApplier`.
2. Place it in gameplay levels you plan to launch from menu.
3. On `BeginPlay`:
   - `Get Game Instance`
   - cast to `BP_KamazGameInstance`
   - read `CurrentMenuSelection`
   - apply runtime setup
4. Early prototype rule:
   - if all choices still use the same truck class, only use the chosen vehicle ID to drive spawn/loadout differences later

## Blueprint Pseudologic

### Vehicle Selection

```text
WBP_OptionCard_Vehicle.OnClicked
-> Set LocalSelection.SelectedVehicleId = VehicleData.VehicleId
-> Set LocalSelection.SelectedVehicleType = VehicleData.VehicleType
-> Call MenuManager.ApplySelection(LocalSelection)
```

```text
BP_MenuManager.ApplySelection(NewSelection)
-> CurrentSelection = NewSelection
-> VehicleData = FindVehicleDataById(CurrentSelection.SelectedVehicleId)
-> BP_MenuVehiclePreview.SpawnPreviewVehicle(VehicleData)
-> BP_MenuCameraRig.FocusVehicleHero()
-> RefreshWidgetSummary()
```

### Vehicle Type Filter

```text
WBP_VehicleTypeButton.OnClicked
-> Set LocalSelection.SelectedVehicleType = ClickedType
-> Rebuild vehicle list where VehicleData.VehicleType == ClickedType
-> If current vehicle no longer valid:
   -> Select first vehicle in filtered list
-> Call MenuManager.ApplySelection(LocalSelection)
```

### Map Selection

```text
WBP_MapCard.OnClicked
-> Set LocalSelection.SelectedMapId = MapData.MapId
-> Disable UI toggles not supported by this map
-> Clamp environment choices if needed
-> Call MenuManager.ApplySelection(LocalSelection)
```

### Day / Night

```text
WBP_DayNightToggle.OnClicked(Night)
-> Set LocalSelection.EnvironmentOptions.LightingMode = Night
-> Call MenuManager.ApplySelection(LocalSelection)
```

```text
BP_MenuEnvironmentController.ApplyEnvironmentOptions
-> Switch on LightingMode
   -> Day: Enable DayRig, Disable NightRig
   -> Night: Enable NightRig, Disable DayRig
-> Recapture Skylight if needed
-> Update emissive accent intensity
```

### Snow / Forest Toggles

```text
WBP_SnowToggle.OnCheckStateChanged
-> Set LocalSelection.EnvironmentOptions.bSnowEnabled = IsChecked
-> Call MenuManager.ApplySelection(LocalSelection)
```

```text
WBP_ForestToggle.OnCheckStateChanged
-> Set LocalSelection.EnvironmentOptions.bForestEnabled = IsChecked
-> Call MenuManager.ApplySelection(LocalSelection)
```

```text
BP_MenuEnvironmentController.ApplyEnvironmentOptions
-> SetActorHiddenInGame(SnowActors, !bSnowEnabled)
-> SetNiagaraActive(SnowFX, bSnowEnabled)
-> SetActorHiddenInGame(ForestActors, !bForestEnabled)
```

### Start Game

```text
WBP_MainMenu3D.StartButton.OnClicked
-> Call MenuManager.StartGame()
```

```text
BP_MenuManager.StartGame
-> GI = GetGameInstance -> Cast BP_KamazGameInstance
-> GI.SetCurrentMenuSelection(CurrentSelection)
-> MapData = FindMapDataById(CurrentSelection.SelectedMapId)
-> BP_MenuCameraRig.PlayStartTransition()
-> OpenLevel(by Object Reference from MapData.MapLevel)
```

### Gameplay Level Readback

```text
BP_KamazLevelRuntimeConfigApplier.BeginPlay
-> GI = GetGameInstance -> Cast BP_KamazGameInstance
-> Selection = GI.GetCurrentMenuSelection()
-> ApplySelectedVehicle(Selection.SelectedVehicleId)
-> ApplySnow(Selection.EnvironmentOptions.bSnowEnabled)
-> ApplyForest(Selection.EnvironmentOptions.bForestEnabled)
-> ApplyLighting(Selection.EnvironmentOptions.LightingMode)
```

## Production-Ready Prototype Notes

### What Should Stay Prototype-Simple

- Blueprints only
- single `GameInstance` payload
- one menu manager actor
- one preview spawn actor
- one environment controller
- one runtime config applier in playable maps

### What Makes It Production-Ready Enough

- Data Assets instead of hardcoded switch nodes
- menu logic not buried in widgets
- no Level Blueprint dependency
- map capability flags to avoid invalid combinations
- dedicated foldering and naming from day one

## Folder Scheme

- `Content/BPs/`
  - `BP_KamazGameInstance`
  - `BP_MenuGameMode`
  - `BP_MenuPlayerController`
  - `BP_KamazLevelRuntimeConfigApplier`

- `Content/CityPark/Kamaz/Menu/Levels/`
  - `MenuLevel`

- `Content/CityPark/Kamaz/Menu/Blueprints/`
  - `BP_MenuManager`
  - `BP_MenuVehiclePreview`
  - `BP_MenuCameraRig`
  - `BP_MenuEnvironmentController`

- `Content/CityPark/Kamaz/Menu/Widgets/`
  - `WBP_MainMenu3D`
  - `WBP_OptionCard`
  - `WBP_MapCard`
  - `WBP_SelectionSummary`

- `Content/CityPark/Kamaz/Menu/Data/`
  - `DA_MenuCatalog`
  - `DA_VehicleData_*`
  - `DA_MapData_*`

- `Content/CityPark/Kamaz/Menu/Structs/`
  - `S_MenuSelection`
  - `S_MenuEnvironmentOptions`

- `Content/CityPark/Kamaz/Menu/Enums/`
  - `E_MenuLightingMode`
  - `E_VehicleType`

## Visual Style Options

### Option 1. Industrial Premium Hangar

- Dark graphite hangar
- cold white key lights
- amber technical accents
- glossy floor reflections
- overhead rigging and volumetric haze
- restrained HUD overlay

Why it fits:
- strongest match for KAMAZ engineering and heavy vehicle identity
- feels expensive without looking sci-fi for the sake of sci-fi

### Option 2. Arctic Proving Ground

- snow platform
- cold blue air
- distant pines
- light wind snow particles
- rugged test-track mood

Why it fits:
- communicates snow utility and off-road competence immediately
- works especially well if snow clearing is the fantasy

### Option 3. Tech Expo Stage

- black stage
- LED strips
- holographic lines
- minimal environment
- showroom reveal vibe

Why it fits:
- modern and clean
- easier to build
- but can feel too generic or gamey for KAMAZ if overdone

## Best Fit for This Project

Best primary direction:
- `Industrial Premium Hangar`

Reason:
- it supports both day and night variants
- it presents the truck as serious machinery
- it works with snow and forest toggles as optional flavor layers
- it avoids the mismatch of a purely futuristic car-configurator look

Recommended blend:
- base style from `Industrial Premium Hangar`
- seasonal environmental accents borrowed from `Arctic Proving Ground`

## Camera and UI Animation Recommendations

### Camera

- idle orbit:
  - 12 to 18 second full orbit
  - low amplitude
  - slight parallax height drift
- focus transitions:
  - 0.45 to 0.8 second eased move when user changes tab
- hero framing:
  - 3/4 front angle as default
- subtle lens language:
  - mild depth of field
  - very restrained bloom
  - no aggressive shake

Premium camera moments:
- when switching to Truck tab:
  - slow dolly toward front grille
- when switching to Environment:
  - wider shot to show scene dressing
- on `Start`:
  - quick push-in plus UI fade

### UI

- panel reveal:
  - staggered 40 to 80 ms card entries
- selection feedback:
  - thin animated outline sweep
  - soft accent glow
- summary block:
  - rolling text and small opacity fades
- CTA:
  - `Start` button with subtle fill sweep, not arcade pulse

Practical project note:
- there is already `Content/Fonts/Russian_GOST.uasset`
- that is a strong candidate for section headings or numeric labels
- pair it with a cleaner readable body font for descriptions

## Current Diff Summary

- Existing worktree already contains unrelated gameplay, snow, config, plugin, and Python changes.
- This menu plan should be implemented in isolated menu assets first.
- Do not mix initial menu prototype work with current snow/runtime fixes.

## Relevant Log Excerpts

- `Config/DefaultEngine.ini` currently points `GameInstanceClass=/Script/Engine.GameInstance`
- `Config/DefaultEngine.ini` currently points `GameDefaultMap=/Game/Maps/MoscowEA5.MoscowEA5`
- Existing gameplay truck asset is `/Game/CityPark/Kamaz/model/KamazBP`
- Existing gameplay maps visible in content:
  - `/Game/Maps/MoscowEA5`
  - `/Game/Maps/SnowTest_Level`
  - `/Game/Maps/Clumbi_Tverskay`

## Open Questions

- Should the gameplay level physically swap pawn class based on selection, or is the first prototype allowed to always load `KamazBP` and only vary cosmetic/loadout state?
- Do `snow` and `forest` need to affect actual gameplay maps at runtime, or only the preview scene in prototype phase 1?
- Is `Clumbi_Tverskay` intended as a playable route choice or only an environment/test map?
- Does the project want a pure hangar-style menu scene, or a stylized slice of a real KAMAZ yard?
