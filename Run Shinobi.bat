@echo off
for %%f in (shinobi_mud.py) do (
    python %%f
    goto :end
)
:end
pause
