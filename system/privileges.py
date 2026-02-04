import ctypes
import sys

def is_admin() -> bool:
    """
    Verifica se il processo corrente ha privilegi amministrativi.
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def relaunch_as_admin():
    """
    Rilancia lo script corrente con privilegi admin tramite UAC.
    """
    params = " ".join(f'"{arg}"' for arg in sys.argv)
    # ShellExecuteW con verbo "runas" chiede elevazione
    ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        params,
        None,
        1
    )
    sys.exit(0)

