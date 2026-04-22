import ctypes
import time


def init_lib(lib_fullpath):
    global svlib
    svlib = ctypes.CDLL(lib_fullpath.as_posix())
    # CONNECT TO SOUND SYSTEM
    svlib.sv_init.restype = ctypes.c_int32
    ver = svlib.sv_init(None, 44100, 2, 0 )
    if ver>=0:
        print(f"Init Sound succeeded!")
        return svlib

    print(f"Link Sound failed, error:{ver}")
    return


def run_open_lib(svlib):
    # REQUEST SLOT
    slotnr = 0
    open_slot(slotnr)

    filename = "assets/test.sunvox"
    load_file(slotnr, filename)

    # SET VOLUME
    svlib.sv_volume(slotnr, 256)

    # START PLAY
    success = svlib.sv_play_from_beginning(slotnr)
    if success == 0:
        print(f"Play file succeeded!")
    else:
        print(f"Play file failed, error:{success}")

    # LET PLAY FOR 5 SECONDS
    time.sleep(5)

    # STOP PLAY
    svlib.sv_stop(slotnr)

    # CLOSE SLOT
    svlib.sv_close_slot(slotnr)

    # RELEASE SOUND SYSTEM
    svlib.sv_deinit()


def open_slot(slotnr=0):
    success = svlib.sv_open_slot(slotnr)
    if success == 0:
        print(f"Open slot succeeded!")
    else:
        print(f"Open slot failed, error:{success}")


def load_file(slotnr, filename):
    # LOAD FILE
    svfile= filename # "test.sunvox"
    bsvfile = svfile.encode('utf-8')
    success = svlib.sv_load(slotnr, ctypes.c_char_p(bsvfile))
    if success == 0:
        print(f"Open file '{filename}' succeeded!")
        return True
    else:
        print(f"Open file failed, error:{success}")
    return False
