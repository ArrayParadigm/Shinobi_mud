@echo off
for %%f in (veilborn_mud.py) do (
    python %%f
    goto :end
)
:end
pause
