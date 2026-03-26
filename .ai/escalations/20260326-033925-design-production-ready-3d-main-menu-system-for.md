# Senior Escalation Packet

- Generated: 2026-03-26 03:39:25 +03:00
- Project root: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner
- Branch: snow-source-truth-snapshot

## Goal

Спроектировать для проекта KAMAZ production-ready prototype главного меню в формате отдельной 3D menu scene:

- запуск игры открывает отдельный `MenuLevel`
- в центре меню находится постановочная 3D-сцена с `KamazBP`
- UI поверх сцены выбирает машину, тип машины, карту, окружение и день/ночь
- изменение выбора сразу обновляет предпросмотр
- по `Start` выбранные параметры передаются в игровой уровень без хардкода в `Level Blueprint`

## Hypothesis

Самая безопасная и расширяемая реализация для этого проекта:

- отдельный `MenuLevel` вместо плоского меню в игровом уровне
- отдельный `BP_MenuManager`, а не логика в `Level Blueprint`
- каталог доступных машин/карт/пресетов через `Primary Data Asset`
- текущее состояние выбора хранится в отдельном `BP_KamazGameInstance`
- предпросмотр разделен на независимые контроллеры: машина, камера, окружение, свет
- игровая карта получает уже готовый `S_MenuSelection` через `GameInstance`, а применение делает отдельный `BP_MapRuntimeConfigurator`

Такой подход остается Blueprint-first, хорошо ложится на текущую структуру проекта, и не требует немедленного C++ вмешательства в `UCLASS`/`USTRUCT`-заголовки.

## Files to touch

Ниже перечислены рекомендуемые новые сущности для реализации v1.

- `Config/DefaultEngine.ini`
- `/Game/Maps/MenuLevel`
- `/Game/BPs/Menu/BP_MenuGameMode`
- `/Game/BPs/Menu/BP_MenuPlayerController`
- `/Game/BPs/Menu/BP_KamazGameInstance`
- `/Game/BPs/Menu/BP_MenuManager`
- `/Game/BPs/Menu/BP_MenuVehiclePreview`
- `/Game/BPs/Menu/BP_MenuCameraRig`
- `/Game/BPs/Menu/BP_MenuEnvironmentStage`
- `/Game/BPs/Menu/BP_MenuLightingRig`
- `/Game/BPs/Menu/BP_MapRuntimeConfigurator`
- `/Game/BPs/Menu/BPI_MenuSelectionConsumer`
- `/Game/UI/Menu/WBP_MainMenu3D`
- `/Game/UI/Menu/WBP_MenuNavTabs`
- `/Game/UI/Menu/WBP_VehiclePicker`
- `/Game/UI/Menu/WBP_MapPicker`
- `/Game/UI/Menu/WBP_EnvironmentPicker`
- `/Game/UI/Menu/WBP_LightingPicker`
- `/Game/UI/Menu/WBP_MenuOptionCard`
- `/Game/Data/Menu/Structs/S_MenuSelection`
- `/Game/Data/Menu/Enums/E_MenuVehicleType`
- `/Game/Data/Menu/Enums/E_MenuLightingMode`
- `/Game/Data/Menu/DA_MenuCatalog`
- `/Game/Data/Menu/Vehicles/DA_VehicleData_*`
- `/Game/Data/Menu/Maps/DA_MapData_*`
- `/Game/Data/Menu/Environment/DA_EnvironmentProfile_*`
- `/Game/Data/Menu/Lighting/DA_LightingProfile_*`
- `/Game/CityPark/Kamaz/model/KamazBP` as the initial hero vehicle reference
- `/Game/Maps/MoscowEA5`
- `/Game/Maps/SnowTest_Level`
- `/Game/Variant_Offroad/Maps/Lvl_Offroad`

## Existing project anchors

Архитектура ниже привязана к уже существующим сущностям репозитория:

- текущий `GameDefaultMap` и `EditorStartupMap` указывают на `/Game/Maps/MoscowEA5`
- в проекте уже есть `BP_KamazGameMode` и `BP_KamazPlayerController`
- основная машина уже присутствует как `/Game/CityPark/Kamaz/model/KamazBP`
- уже существуют игровые карты `/Game/Maps/MoscowEA5`, `/Game/Maps/SnowTest_Level`, `/Game/Variant_Offroad/Maps/Lvl_Offroad`
- в C++ уже есть Blueprint-callable snow hooks через `USnowStateBlueprintLibrary`
- в проекте уже есть `USnowStateRuntimeSettings` и `ASnowRuntimeBootstrapV1`

Это значит, что меню можно внедрить как новую изолированную систему, не ломая текущий snow/runtime pipeline.

## Recommended architecture

### 1. Runtime layers

`MenuLevel`

- отвечает только за презентацию, выбор параметров и переход в игру
- содержит постановочную сцену, а не игровой flow

`BP_KamazGameInstance`

- хранит каноническое состояние выбора между уровнями
- содержит `PendingSelection` и `CommittedSelection`
- предоставляет функции `InitializeDefaults`, `CommitSelection`, `GetSelection`

`BP_MenuManager`

- центральный orchestration actor уровня меню
- загружает `DA_MenuCatalog`
- создает `WBP_MainMenu3D`
- держит ссылки на `BP_MenuVehiclePreview`, `BP_MenuCameraRig`, `BP_MenuEnvironmentStage`, `BP_MenuLightingRig`
- валидирует выбор при смене карты и обновляет preview

`BP_MapRuntimeConfigurator`

- размещается в каждой игровой карте
- на `BeginPlay` читает `CommittedSelection` из `BP_KamazGameInstance`
- применяет машину, день/ночь, snow/forest, доступные environment actors
- вызывает интерфейсные receiver-акторы без логики в `Level Blueprint`

### 2. Data-driven catalog

`DA_MenuCatalog`

- один корневой asset со списками доступных `Vehicle`, `Map`, `Environment`, `Lighting`
- именно его читает `BP_MenuManager`

`DA_VehicleData`

- `VehicleId : Name`
- `DisplayName : Text`
- `VehicleType : E_MenuVehicleType`
- `PreviewActorClass : ActorClass`
- `GameplayPawnClass : PawnClass`
- `PreviewLookAtSocket : Name`
- `PreviewOffset : Transform`
- `CameraDistance : Float`
- `SupportedMapIds : Name Array`
- `bDefaultSelectable : Bool`

`DA_MapData`

- `MapId : Name`
- `DisplayName : Text`
- `LevelName : Name`
- `LevelSoftReference : World Soft Object`
- `DefaultVehicleId : Name`
- `DefaultEnvironmentId : Name`
- `DefaultLightingMode : E_MenuLightingMode`
- `SupportedVehicleTypes : E_MenuVehicleType Array`
- `SupportsSnow : Bool`
- `SupportsForest : Bool`
- `SupportsDayNightSwitch : Bool`
- `RuntimeConfiguratorTag : Name`

`DA_EnvironmentProfile`

- `EnvironmentId : Name`
- `DisplayName : Text`
- `bEnableSnow : Bool`
- `bEnableForest : Bool`
- `PreviewStageVariant : Name`
- `SnowVisualPreset : Name`
- `ForestVisualPreset : Name`
- `AllowedMapIds : Name Array`

`DA_LightingProfile`

- `LightingMode : E_MenuLightingMode`
- `DisplayName : Text`
- `DirectionalRotation : Rotator`
- `DirectionalIntensity : Float`
- `SkyIntensity : Float`
- `FogDensity : Float`
- `ExposureCompensation : Float`
- `HeadlightAccentIntensity : Float`
- `EmissiveBoost : Float`

### 3. State model

`S_MenuSelection`

- `SelectedVehicleId : Name`
- `SelectedVehicleType : E_MenuVehicleType`
- `SelectedMapId : Name`
- `SelectedEnvironmentId : Name`
- `bSnowEnabled : Bool`
- `bForestEnabled : Bool`
- `SelectedLightingMode : E_MenuLightingMode`

Рекомендация для v1:

- хранить IDs как `Name`, а не строки
- `VehicleType` использовать как фильтр списка машин
- `SelectedVehicleId` использовать как фактический выбор для spawn/preview
- `bSnowEnabled` и `bForestEnabled` держать отдельно, даже если в UI сначала будут 3 готовых пресета

## Blueprint and widget structure

### Core Blueprints

`BP_MenuGameMode`

- используется только в `MenuLevel`
- `Default Pawn = None`
- `PlayerControllerClass = BP_MenuPlayerController`
- не содержит игровой логики

`BP_MenuPlayerController`

- `Show Mouse Cursor = true`
- `Set Input Mode Game and UI`
- optionally блокирует pawn input

`BP_MenuManager`

- единственная точка маршрутизации UI -> preview -> GameInstance -> OpenLevel

`BP_MenuVehiclePreview`

- спавнит/меняет preview vehicle actor
- знает как аккуратно удалить старый preview actor
- хранит `VehicleAnchor` и `FocusPoint`

`BP_MenuCameraRig`

- `Root`
- `OrbitPivot`
- `SpringArm`
- `CineCamera`
- idle orbit + micro-dolly + smooth reframing

`BP_MenuEnvironmentStage`

- переключает set dressing preview-сцены
- сначала лучше держать 3 варианта прямо в одном уровне:
- `Clean`
- `Snow`
- `Forest`
- если сцена разрастется, перейти на streaming sublevels, не меняя интерфейс менеджера

`BP_MenuLightingRig`

- управляет `DirectionalLight`, `SkyLight`, `ExponentialHeightFog`, `PostProcess`
- применяет `DA_LightingProfile`

`BP_MapRuntimeConfigurator`

- gameplay-side consumer выбора
- не зависит от UI
- умеет найти нужный vehicle data, spawn vehicle, применить light/environment options

`BPI_MenuSelectionConsumer`

- интерфейс для любых акторов карты, которые хотят получить выбор игрока
- функция `ApplyMenuSelection(S_MenuSelection Selection)`

### Widgets

`WBP_MainMenu3D`

- один root widget
- overlay поверх 3D-сцены
- левый или нижний блок выбора
- правый блок с характеристиками/описанием/кнопкой `Start`

`WBP_MenuNavTabs`

- верхняя навигация
- `Vehicle`
- `Type`
- `Map`
- `Environment`
- `Lighting`

`WBP_VehiclePicker`

- список карточек машин

`WBP_MapPicker`

- список карт

`WBP_EnvironmentPicker`

- пресеты `Snow`, `Forest`, `Clean`
- или два независимых тумблера `Snow` и `Forest`

`WBP_LightingPicker`

- `Day`
- `Night`

`WBP_MenuOptionCard`

- переиспользуемая карточка выбора
- иконка, заголовок, subtitle, selected state, hover animation

### WidgetSwitcher recommendation

Использовать `WidgetSwitcher` стоит здесь:

- в `WBP_MainMenu3D` для переключения панелей выбора
- один индекс на активную вкладку

Не использовать `WidgetSwitcher` как замену state management:

- текущее меню-состояние хранит `BP_MenuManager`
- `WidgetSwitcher` отвечает только за видимую страницу интерфейса

## Object relationships

Связь сущностей должна быть такой:

`WBP_MainMenu3D`

- шлет UI events в `BP_MenuManager`

`BP_MenuManager`

- хранит `CurrentSelection`
- запрашивает данные в `DA_MenuCatalog`
- вызывает:
- `BP_MenuVehiclePreview.UpdateVehicle`
- `BP_MenuCameraRig.FocusVehicle`
- `BP_MenuEnvironmentStage.ApplyEnvironment`
- `BP_MenuLightingRig.ApplyLighting`
- `BP_KamazGameInstance.CommitSelection`

`BP_MapRuntimeConfigurator`

- читает `BP_KamazGameInstance.CommittedSelection`
- применяет выбор через размещенные на карте актеры или через `BPI_MenuSelectionConsumer`

## Why not Level Blueprint

Для этой системы лучше не использовать `Level Blueprint`, кроме, максимум, одноразового placement helper-а.

Причины:

- меню станет сложно масштабировать
- логика выбора и логика сцены смешаются
- переиспользование на втором menu-level или demo-level станет больным
- тестировать и менять flow через отдельный `BP_MenuManager` гораздо проще

Рекомендация:

- orchestration в `BP_MenuManager`
- scene controllers отдельными Blueprint actors
- gameplay-side application в `BP_MapRuntimeConfigurator`

## Detailed implementation steps

## Ordered steps

1. Создать `E_MenuVehicleType`, `E_MenuLightingMode` и `S_MenuSelection`.
2. Создать `DA_VehicleData`, `DA_MapData`, `DA_EnvironmentProfile`, `DA_LightingProfile`, `DA_MenuCatalog`.
3. Создать `BP_KamazGameInstance` и переключить `GameInstanceClass` с `/Script/Engine.GameInstance` на него.
4. Создать `MenuLevel` и назначить ему `BP_MenuGameMode`.
5. Разместить в `MenuLevel` актеры `BP_MenuManager`, `BP_MenuVehiclePreview`, `BP_MenuCameraRig`, `BP_MenuEnvironmentStage`, `BP_MenuLightingRig`.
6. Собрать `WBP_MainMenu3D` с `WidgetSwitcher` и отдельными picker widgets.
7. На `BeginPlay` в `BP_MenuManager` загрузить `DA_MenuCatalog`, инициализировать дефолтный `S_MenuSelection`, создать widget, применить первый preview.
8. Реализовать vehicle flow: выбор карточки меняет `SelectedVehicleId`, перестраивает preview actor и мягко рефреймит камеру.
9. Реализовать map flow: выбор карты валидирует совместимые vehicle/environment options и при необходимости мягко откатывает invalid state к дефолту карты.
10. Реализовать environment flow: `Snow`, `Forest`, `Clean` переключают set dressing preview-сцены без загрузки игровых уровней.
11. Реализовать lighting flow: `Day/Night` применяет отдельные lighting profiles и усиливает emissive/volumetric cues.
12. Создать `BP_MapRuntimeConfigurator` и добавить его в `MoscowEA5`, `SnowTest_Level`, `Lvl_Offroad`.
13. На `Start` сохранять `CommittedSelection` в `BP_KamazGameInstance`, проигрывать короткий exit transition и делать `OpenLevel`.
14. В `BP_MapRuntimeConfigurator.BeginPlay` читать `CommittedSelection`, спавнить нужный pawn или конфигурацию `KamazBP`, применять environment/light flags, и опционально оповещать actors через `BPI_MenuSelectionConsumer`.
15. После стабилизации перевести `GameDefaultMap` на `MenuLevel`.

## Preview scene implementation

Для v1 preview-сцены рекомендована такая постановка:

- машина стоит не на turntable, а на технологической площадке с реальным контекстом
- камера показывает front 3/4 angle как default hero shot
- окружение не должно быть большим полноценным уровнем
- фон состоит из ограниченной сценографической площадки и пары дальних silhouette cards

Практичная сборка:

- одна центральная площадка из бетона или металла
- мокрый пол с легким отражением
- один back wall с индустриальной графикой
- один дальний фон с fog cards
- snow/forest variants включаются как сценографические слои

## Camera direction

Чтобы меню выглядело дорого, камера должна не крутиться бесконечно вокруг машины, а работать как automotive reveal shot:

- idle orbit всего 6-12 градусов по yaw
- очень медленный micro-pan
- very light dolly in/out на 10-20 см
- легкий roll не нужен
- на hover/select камера может переходить к другому framing preset

Рекомендуемая схема:

- intro `LevelSequence` на 3-5 секунд
- после intro управление переходит в `BP_MenuCameraRig`
- `BP_MenuCameraRig` работает по `Timeline + CurveFloat`

Рекомендуемые поля в `DA_VehicleData` для камеры:

- `PreviewLookAtSocket`
- `CameraDistance`
- `CameraHeightOffset`
- `CameraYawOffset`
- `FOV`

## Gameplay handoff strategy

Канонический путь передачи параметров:

1. UI меняет `CurrentSelection` в `BP_MenuManager`.
2. `BP_MenuManager` вызывает `BP_KamazGameInstance.CommitSelection(CurrentSelection)`.
3. `BP_MenuManager` вызывает `OpenLevel(SelectedMap.LevelName)`.
4. Игровая карта стартует.
5. `BP_MapRuntimeConfigurator.BeginPlay` читает `CommittedSelection`.
6. Карта применяет vehicle/environment/light choices.

Почему именно `GameInstance`:

- живет между уровнями
- не требует парсить option string
- легко использовать в Blueprints
- подходит для single-player configurator flow

Дополнительно, если позже нужен deep-link/debug:

- можно дублировать ключевые параметры в `OpenLevel Options`
- но источником истины все равно оставить `GameInstance`

## Integration with current snow systems

Для этого проекта важно не смешивать menu preview и gameplay snow runtime.

Рекомендация:

- в `MenuLevel` снег должен быть только визуальным preview layer
- не нужно запускать весь gameplay snow runtime для idle menu сцены
- в игровых уровнях snow опция применяется через `BP_MapRuntimeConfigurator`

Если карта поддерживает snow runtime:

- активировать нужные snow actors/components только в gameplay level
- использовать уже существующие `BP_WheelSnowTrace_Component`, `BP_PlowBrush_Component`, `ASnowRuntimeBootstrapV1` по месту
- при необходимости вызывать `USnowStateBlueprintLibrary::FlushPersistentSnowState` перед выходом из snow-session или при сохранении

Если карта snow не поддерживает:

- `BP_MenuManager` должен либо скрыть опцию `Snow`, либо дизейблить ее по `DA_MapData.SupportsSnow`

## Blueprint logic pseudo-flow

### Vehicle selection

```text
WBP_VehiclePicker.OnVehicleCardClicked(VehicleId)
 -> BP_MenuManager.SetSelectedVehicle(VehicleId)
 -> CurrentSelection.SelectedVehicleId = VehicleId
 -> CurrentSelection.SelectedVehicleType = ResolveVehicleType(VehicleId)
 -> BP_MenuVehiclePreview.UpdateVehicle(VehicleData)
 -> BP_MenuCameraRig.FocusVehicle(VehicleData)
 -> WBP_MainMenu3D.RefreshSelectionState()
```

### Vehicle type filtering

```text
WBP_MainMenu3D.OnVehicleTypeChanged(NewType)
 -> BP_MenuManager.SetVehicleType(NewType)
 -> CurrentSelection.SelectedVehicleType = NewType
 -> Filter Vehicles where VehicleData.VehicleType == NewType
 -> If current SelectedVehicleId is invalid:
 ->    Set SelectedVehicleId = FirstFilteredVehicleId
 -> Update Preview
```

### Map selection

```text
WBP_MapPicker.OnMapClicked(MapId)
 -> BP_MenuManager.SetSelectedMap(MapId)
 -> CurrentSelection.SelectedMapId = MapId
 -> ValidateSelectionAgainstMap()
 -> If Vehicle not supported:
 ->    Set SelectedVehicleId = MapData.DefaultVehicleId
 -> If Environment not supported:
 ->    Set SelectedEnvironmentId = MapData.DefaultEnvironmentId
 -> If Lighting not supported:
 ->    Set SelectedLightingMode = MapData.DefaultLightingMode
 -> UpdatePreview()
```

### Day/Night switch

```text
WBP_LightingPicker.OnLightingChanged(NewLightingMode)
 -> BP_MenuManager.SetLightingMode(NewLightingMode)
 -> CurrentSelection.SelectedLightingMode = NewLightingMode
 -> BP_MenuLightingRig.ApplyLighting(LightingProfile)
 -> BP_MenuVehiclePreview.RefreshEmissiveState(NewLightingMode)
```

### Snow toggle

```text
WBP_EnvironmentPicker.OnSnowToggled(bEnabled)
 -> BP_MenuManager.SetSnowEnabled(bEnabled)
 -> CurrentSelection.bSnowEnabled = bEnabled
 -> BP_MenuEnvironmentStage.ApplyEnvironment(CurrentSelection)
 -> If bEnabled:
 ->    CurrentSelection.SelectedEnvironmentId = SnowProfileId
```

### Forest toggle

```text
WBP_EnvironmentPicker.OnForestToggled(bEnabled)
 -> BP_MenuManager.SetForestEnabled(bEnabled)
 -> CurrentSelection.bForestEnabled = bEnabled
 -> BP_MenuEnvironmentStage.ApplyEnvironment(CurrentSelection)
```

### Preset environment buttons

```text
OnClicked SnowPreset
 -> bSnowEnabled = true
 -> bForestEnabled = false
 -> SelectedEnvironmentId = Snow
 -> UpdatePreview()

OnClicked ForestPreset
 -> bSnowEnabled = false
 -> bForestEnabled = true
 -> SelectedEnvironmentId = Forest
 -> UpdatePreview()

OnClicked CleanPreset
 -> bSnowEnabled = false
 -> bForestEnabled = false
 -> SelectedEnvironmentId = Clean
 -> UpdatePreview()
```

### Start button

```text
WBP_MainMenu3D.OnStartClicked
 -> BP_MenuManager.ValidateSelection()
 -> BP_KamazGameInstance.CommitSelection(CurrentSelection)
 -> Play UI Fade Out
 -> Play Camera Exit Transition
 -> OpenLevel(SelectedMapData.LevelName)
```

### Gameplay-side apply

```text
BP_MapRuntimeConfigurator.BeginPlay
 -> GI = Cast BP_KamazGameInstance(GetGameInstance)
 -> Selection = GI.GetCommittedSelection()
 -> VehicleData = ResolveVehicleData(Selection.SelectedVehicleId)
 -> ApplyLighting(Selection.SelectedLightingMode)
 -> ApplyEnvironment(Selection.bSnowEnabled, Selection.bForestEnabled)
 -> SpawnOrConfigureVehicle(VehicleData)
 -> Broadcast ApplyMenuSelection to actors implementing BPI_MenuSelectionConsumer
```

## Visual style options

### Style A: Industrial Hero Bay

- темный сервисный ангар
- мокрый бетон
- холодный белый key light + янтарные practical lights
- UI как техно-индустриальный конфигуратор
- ощущение тяжелой техники и инженерной мощности

### Style B: Arctic Proving Ground

- открытая снежная площадка
- холодный воздух, fog, wind particles
- синевато-белый свет днем, глубокие контрасты ночью
- акцент на snow-cleaning identity проекта

### Style C: Premium Studio Configurator

- минималистичная студия
- большой LED-wall фон
- glossy reflections
- очень чистый automotive showroom feel

## Best fit for KAMAZ

Лучше всего проекту подходит гибрид `Industrial Hero Bay + Arctic accents`.

Причины:

- KAMAZ визуально лучше работает в industrial context, чем в стерильной студии
- проект уже связан со снегом и утилитарной техникой
- такой стиль позволяет и heavy-duty характер, и премиальную подачу

Практический рецепт:

- база сцены индустриальная
- снег, лес и ночь добавляются как режимы
- UI чистый и современный, но не luxury-car minimalism

## Animations that make the menu feel expensive

Камера:

- short intro fly-in from wide shot to hero angle
- asymmetrical idle orbit, а не постоянный full spin
- smooth reframing when vehicle changes
- quick close-up insert on headlights/plow for selected variants

UI:

- staggered reveal for cards
- thin line sweeps and subtle mask reveals
- hover state with scale 1.02 and emissive accent, не сильный bounce
- soft blur/fade on panel switching through `WidgetSwitcher`
- start button with compressed hold-like transition, not instant cut

Свет и сцена:

- night mode should turn on practical emissive accents
- wet floor reflections should react to camera angle
- low-density particles only, без постоянной бурной метели

## Folder layout proposal

Минимально конфликтная схема для этого репозитория:

- `/Game/Maps/MenuLevel`
- `/Game/BPs/Menu/Managers`
- `/Game/BPs/Menu/Preview`
- `/Game/BPs/Menu/Gameplay`
- `/Game/UI/Menu`
- `/Game/Data/Menu/Enums`
- `/Game/Data/Menu/Structs`
- `/Game/Data/Menu/Vehicles`
- `/Game/Data/Menu/Maps`
- `/Game/Data/Menu/Environment`
- `/Game/Data/Menu/Lighting`

Существующие vehicle assets лучше не переносить:

- оставить `KamazBP` в `/Game/CityPark/Kamaz/model/KamazBP`
- новые Data Assets просто ссылаются на него

## Invariants / Do-not-break rules

- Не выносить orchestration меню в `Level Blueprint`.
- `GameInstance` является источником истины для выбора между уровнями.
- Data Assets являются источником истины для доступных опций.
- Preview scene не должна напрямую модифицировать gameplay maps.
- Snow preview в меню должен быть визуальным, а не полной копией gameplay runtime.
- Невалидные для карты опции должны автоматически откатываться к поддерживаемому значению.
- Для v1 не трогать C++ заголовки с `UCLASS/USTRUCT/UENUM`, если можно обойтись Blueprint/Data Assets.

## Validation

Проверки для v1:

- Игра стартует в `MenuLevel`.
- `WBP_MainMenu3D` создается без ошибок.
- Выбор машины реально меняет preview actor.
- Выбор карты меняет доступность environment/light options.
- `Snow`, `Forest`, `Clean` обновляют preview-сцену без перезагрузки уровня.
- `Day/Night` мгновенно меняет lighting rig.
- `Start` открывает выбранную карту.
- На карте `BP_MapRuntimeConfigurator` получает тот же `S_MenuSelection`, который был в меню.
- Если карта не поддерживает снег или лес, UI показывает disabled state вместо silent failure.

## Rollback notes

- Если система окажется слишком тяжелой, rollback делается удалением нового menu asset root и возвратом `GameDefaultMap` обратно на `/Game/Maps/MoscowEA5`.
- Существующие gameplay maps и `KamazBP` не должны зависеть от меню напрямую.
- Все новые зависимости должны быть направлены от menu system к существующим assets, а не наоборот.

## Current diff summary

Рабочее дерево уже сильно загрязнено существующей snow/runtime работой. Для этого запроса в рамках текущего прохода добавлен только design artifact:

- new file: `.ai/escalations/20260326-033925-design-production-ready-3d-main-menu-system-for.md`

Риск смешения изменений:

- высокий, если пытаться в том же проходе массово менять активные snow assets
- низкий, если меню внедрять отдельным новым asset root и отдельным `GameInstance`

## Relevant log excerpts

Последний smoke/build контекст не показывает блокеров именно для меню, но показывает соседние техдолги проекта:

- repeated Nanite warning: translucent material `Glass1111` on mesh `Lights2`
- editor shutdown passed normally after smoke
- в recent logs видны cleanup paths для `MoscowEA5` и `Clumbi_Tverskay`

Для menu system это значит:

- меню лучше внедрять изолированно
- не считать соседние Nanite warnings частью menu task

## Open questions

- В v1 выбор машины должен переключать реальные разные pawn classes, или пока это только разные конфигурации `KamazBP`?
- Нужен ли отдельный preview preset под каждую карту, или достаточно глобальной menu сцены с environment variants?
- Карта `Lvl_Offroad` должна стартовать через тот же `BP_MapRuntimeConfigurator`, или у нее будет собственный runtime-applier?
- Нужно ли сохранять последний выбор игрока между запусками через `SaveGame`, или пока достаточно `GameInstance` на одну сессию?
