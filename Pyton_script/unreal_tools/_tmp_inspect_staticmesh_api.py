import unreal


def _print_methods(obj, token):
    names = sorted([n for n in dir(obj) if token.lower() in n.lower()])
    print(f"--- {obj.__name__ if hasattr(obj, '__name__') else str(obj)} contains '{token}' ---")
    for n in names:
        print(n)


def main():
    _print_methods(unreal.StaticMeshEditorSubsystem, "vert")
    _print_methods(unreal.StaticMeshEditorSubsystem, "triangle")
    _print_methods(unreal.StaticMeshEditorSubsystem, "lod")
    _print_methods(unreal.EditorStaticMeshLibrary, "vert")
    _print_methods(unreal.EditorStaticMeshLibrary, "triangle")
    _print_methods(unreal.EditorStaticMeshLibrary, "lod")


if __name__ == "__main__":
    main()
