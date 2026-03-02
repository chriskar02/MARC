"""List all methods of mecademicpy Robot class."""
import mecademicpy.robot as mdr
r = mdr.Robot()
methods = sorted([m for m in dir(r) if not m.startswith('_') and callable(getattr(r, m))])
for m in methods:
    print(m)
