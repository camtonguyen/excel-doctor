import importlib
import pkgutil

# Every rules_*.py module registers its rules at import time (see base.registry).
# Auto-discover them here so adding a new rule file is enough - no list to remember to edit.
for _module_info in pkgutil.iter_modules(__path__, prefix=f"{__name__}."):
    if _module_info.name.rsplit(".", 1)[-1].startswith("rules_"):
        importlib.import_module(_module_info.name)
