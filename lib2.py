import ctypes
import time

from pathlib import Path
import atexit

import os


lib_root = './sunvox_lib-2.0e/sunvox_lib/'
lib_target = 'windows/lib_x86_64'
lib_path = Path(lib_root) / lib_target
lib_name = lib_path / "sunvox.dll"

print('LIB', lib_name)


from modules import Generator
from notes import Notes
from player import player_factory, SoundBoard

from base import init_lib, run_open_lib
N = Notes()

def main():
    # lib = init_lib(lib_name)
    # run_open_lib(lib)
    # main_soundboard()
    # play_file()
    send_notes()
    # create_a_mod_file()
    return beep_notes()


def main_soundboard():
    """Use the 'SoundBoard' class to load base functions, such as core
    loads.
    """
    # Load the shared library into ctypes
    filename = "assets/test.sunvox"

    sb = SoundBoard()
    sb.init_lib(lib_name)
    sb.open_slot(0)
    sb.load_file(0, filename)
    sb.set_volume(0, 256)
    sb.play_from_beginning(0)

    time.sleep(3)

    sb.stop(0)
    sb.close_slot(0)
    #sb.deinit()
    return sb
    # if svlib:
    #     return run_open_lib()


def play_file():
    pl = main_player()#.example()
    pl.play_file('assets/wooloo.sunvox')
    time.sleep(1.5)
    pl.stop()
    pl.close()
    time.sleep(.5)
    return pl


async def send_notes():
    pl = main_player()
    mod = Generator()
    pl.add_module(mod, connect_to=pl.OUTPUT)
    # mod.connect_to(pl.OUTPUT)
    kb = AsyncKeyboard(mod)
    await kb.sv_send_event(0, N.C4)
    await

def beep_notes():
    pl = main_player()#.example()
    # pl.example()

    # pl.play_file('assets/wooloo.sunvox')
    # time.sleep(2)
    # pl.stop()
    # time.sleep(1)

    mod = Generator()
    pl.add_module(mod)
    mod.connect_to(pl.OUTPUT)

    # Send Note ON to the module m
    n = (4 * 12 + 0) + 1        # octave 4, note 0  == C4
    n = N.octave_note(4,0)      # octave 4, note 0  == C4
    n = N.C4

    mod.sv_send_event(0, n)# ; //track 0; note n; velocity 129 (max); module m;
    mod.sv_send_event(1, n + 2)# ; //track 0; note n; velocity 129 (max); module m;
    time.sleep(.5)

    mod.sv_send_event(0, N.NOTE_OFF)# ; //track 0; note n; velocity 129 (max); module m;
    time.sleep(.5)

    # sv_send_event( slot, 0, n+1, 129, m+1, 0, 0 );
    mod.sv_send_event(0, N.C4)# ; //track 0; note n; velocity 129 (max); module m;
    time.sleep(.5)
    mod.sv_send_event(0, N.NOTE_OFF)# ; //track 0; note n; velocity 129 (max); module m;

    time.sleep(.4)
    mod.sv_send_event(0, N.STOP)# ; //track 0; note n; velocity 129 (max); module m;

    return pl


def create_a_mod_file():
    """Generate a file with one module within.
    """
    pl = main_player()#.example()
    # pl.example()

    # pl.play_file('assets/wooloo.sunvox')
    # time.sleep(2)
    # pl.stop()
    # time.sleep(1)

    mod = Generator()
    pl.add_module(mod)
    mod.connect_to(pl.OUTPUT)
    pl.save_file('alpha.sunvox')
    return pl


def main_player():
    pl = player_factory.spawn_player()
    return pl



if __name__ == "__main__":
    sb = main()
    # l = sb.svlib
