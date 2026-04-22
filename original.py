import ctypes
import time

# get script directory
import os
scriptpath = "C:/Users/jay/Documents/projects/sunvox/sunvox_lib-2.0e/sunvox_lib/windows/lib_x86_64"
# scriptdir = os.path.dirname(scriptpath)
# construct full path to sunvox lib
libname=os.path.join(scriptpath,"sunvox.dll")

if __name__ == "__main__":
    # Load the shared library into ctypes
    svlib = ctypes.CDLL(libname)

    # CONNECT TO SOUND SYSTEM
    svlib.sv_init.restype=ctypes.c_int32
    ver = svlib.sv_init(None, 44100, 2, 0 )
    print (f"Init Sound succeeded!") if ver>=0 else print (f"Link Sound failed, error:{ver}")

    if( ver >= 0 ):
        # REQUEST SLOT
        slotnr=0
        success=svlib.sv_open_slot(slotnr)
        print (f"Open slot succeeded!") if success==0 else print (f"Open slot failed, error:{success}")

        # LOAD FILE
        svfile="test.sunvox"
        bsvfile = svfile.encode('utf-8')
        success = svlib.sv_load(slotnr, ctypes.c_char_p(bsvfile))
        print (f"Open file succeeded!") if success==0 else print (f"Open file failed, error:{success}")

        # SET VOLUME
        svlib.sv_volume(slotnr,256)

        # START PLAY
        success = svlib.sv_play_from_beginning(slotnr)
        print (f"Play file succeeded!") if success==0 else print (f"Play file failed, error:{success}")

        # LET PLAY FOR 5 SECONDS
        time.sleep(5)

        # STOP PLAY
        svlib.sv_stop(slotnr)

        # CLOSE SLOT
        svlib.sv_close_slot(slotnr)

        # RELEASE SOUND SYSTEM
        svlib.sv_deinit()