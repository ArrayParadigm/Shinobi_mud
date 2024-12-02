@echo off
for %%f in (update_schema.py) do (
    python %%f
    goto :end
)
:end
pause
