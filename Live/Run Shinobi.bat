@echo off
for %%f in (shinobi_mud_*.py) do (
    python %%f
    goto :end
)
:end
pause
