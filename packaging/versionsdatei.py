"""Erzeugt packaging/version.txt (Windows-Dateiversion) aus kasse.__version__."""
import pathlib
import re

wurzel = pathlib.Path(__file__).resolve().parent
version = re.search(r'__version__ = "([^"]+)"', (wurzel.parent / "src/kasse/__init__.py").read_text()).group(1)
teile = (version.split(".") + ["0", "0", "0"])[:4]
tupel = ", ".join(str(int(t)) for t in teile)
(wurzel / "version.txt").write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({tupel}), prodvers=({tupel})),
  kids=[StringFileInfo([StringTable('040704B0', [
    StringStruct('CompanyName', 'Registrierkasse'),
    StringStruct('FileDescription', 'Registrierkasse (RKSV)'),
    StringStruct('FileVersion', '{version}'),
    StringStruct('ProductName', 'Registrierkasse'),
    StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [0x0407, 1200])])])
""", encoding="utf-8")
print(version)
