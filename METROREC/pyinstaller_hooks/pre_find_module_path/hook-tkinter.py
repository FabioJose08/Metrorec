def pre_find_module_path(hook_api):
    # Tcl cannot probe data files through the restricted build environment.
    # The build script bundles Tcl/Tk runtime data explicitly.
    return
