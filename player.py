import ctypes
import time

from pathlib import Path
import atexit

import os



lib_root = './sunvox_lib-2.0e/sunvox_lib/'
lib_target = 'windows/lib_x86_64'
lib_path = Path(lib_root) / lib_target
lib_name = lib_path / "sunvox.dll"

def c_str(v, encode=True, encoding='utf-8'):
    return ctypes.c_char_p(v.encode(encoding) if encode else v)



class CoreLib(object):

    svlib = None
    slotnr = -1
    locked = False

    def clean_slotnr(self, slotnr=None):
        return self.slotnr if slotnr is None else slotnr

    def open_slot(self, slotnr=None):
        success = self.svlib.sv_open_slot(self.clean_slotnr(slotnr))
        ok = success == 0
        if ok:
            print (f"Open slot succeeded!")
        else:
            print (f"Open slot failed, error:{success}")
        return ok

    def load_file(self, slotnr, filename):
        # LOAD FILE
        svfile= filename # "test.sunvox"
        bsvfile = svfile.encode('utf-8')
        success = self.svlib.sv_load(self.clean_slotnr(slotnr), ctypes.c_char_p(bsvfile))
        ok = success == 0
        if ok:
            print (f"Open file {filename} succeeded!")
        else:
            print (f"Open file failed, error:{success}")
        return success

    def save_file(self, filename, slotnr=None):
        r = self.svlib.sv_save(self.clean_slotnr(slotnr), c_str(filename) )
        return r

    def set_volume(self, slotnr, val=256):
        # SET VOLUME
        self.svlib.sv_volume(self.clean_slotnr(slotnr), val)

    def play_from_beginning(self, slotnr=None):
        # START PLAY
        success = self.svlib.sv_play_from_beginning(self.clean_slotnr(slotnr))
        if success == 0:
            print (f"Play file succeeded!")
        else:
            print (f"Play file failed, error:{success}")

    def stop_slot(self, slotnr):
        # STOP PLAY
        return self.svlib.sv_stop(slotnr)

    def close_slot(self, slotnr):
        # CLOSE SLOT
        r = self.svlib.sv_close_slot(slotnr)
        atexit.unregister(self.deinit)
        return r


    def deinit(self):
        # RELEASE SOUND SYSTEM
        return self.svlib.sv_deinit()

    def lock_slot(self, slotnr=None):
        self.locked = self.svlib.sv_lock_slot(slotnr) == 0

    def unlock_slot(self, slotnr=None):
        self.locked = not (self.svlib.sv_unlock_slot(slotnr) == 0)

    def lock(self, slotnr=None):
        return self.svlib.sv_lock_slot(slotnr or self.slotnr)

    def unlock(self, slotnr=None):
        return self.svlib.sv_unlock_slot(slotnr or self.slotnr)

    def close(self):
        return self.close_slot(self.slotnr)

    def stop(self, slotnr=None):
        return self.stop_slot(slotnr or self.slotnr)

    def sv_new_module(self, slotnr, type, name, x,y,z):
        """ Create a new module. USE LOCK/UNLOCK!

            Prototypes:
                int sv_new_module(
                    int slot,
                    const char* type,
                    const char* name,
                    int x, int y, int z
                );

            Parameters:
                slot / sv - slot number / SunVox object ID;
                type - string with module type; example: "Sampler";
                name - module name;
                x, y - module coordinates;
                        center of the module view = 512,512;
                        normal working area: 0,0 ... 1024,1024;
                z - layer number from 0 to 7.
        Return value: the number of the newly created module, or negative error code.
        """
        self.lock(slotnr)
        _name = c_str(name)
        _type = c_str(type)
        v = self.svlib.sv_new_module(slotnr, _type, _name, x,y,z)

        print(f'svlib.sv_new_module {slotnr=}, {type=}, {_name=}', f"xyz={x,y,z} == {v}")
        self.unlock(slotnr)
        return v

    def add_module(self, module, connect_to=None):
        sv_m = self.sv_new_module(self.slotnr,
                    module.get_type(),
                    module.get_name(),
                    *module.xyz(),
                )
        if sv_m < 0:
            raise Exception('add_module error. Code', sv_m)
        # return sv_m
        # self.modules[sv_m] = sv_m
        r = module.set_owner(self, sv_m)
        if connect_to is not None:
            module.connect_to(connect_to)
        return r

    def sv_connect_module(self, a, b, slotnr=None):
        do_unlock = False
        if not self.locked:
            self.lock(slotnr)
            do_unlock = True

        r = self.svlib.sv_connect_module(slotnr or self.slotnr, a, b)

        if do_unlock is True:
            self.unlock(slotnr)

        return r

    def sv_get_module_type(self, num):
        return self.svlib.sv_get_module_type(self.slotnr, num)

    def sv_get_module_name(self, num):
        return self.svlib.sv_get_module_name(self.slotnr, num)

    def sv_get_number_of_modules(self, slotnr=None):
        """ Get the number of module slots (not the actual number of modules)
        in the project. The slot can be empty or it can contain a module.
        Here is the code to determine that the module slot X is not empty:
        ( sv_get_module_flags( slot, X ) & SV_MODULE_FLAG_EXI
        """
        return self.svlib.sv_get_number_of_modules(slotnr or self.slotnr)

    def sv_find_module(self, v, slotnr=None):
        return self.svlib.sv_find_module(slotnr or self.slotnr, v)

    def sv_get_module_flags(self, v, slotnr=None):
        return self.svlib.sv_get_module_flags(slotnr or self.slotnr, v)

    def sv_get_module_name(self, v, slotnr=None):
        return self.svlib.sv_get_module_name(slotnr or self.slotnr, v)

    def sv_set_module_name(self, mod_id, name,slotnr=None, ):
        _name = c_str(name)
        return self.svlib.sv_set_module_name(slotnr or self.slotnr, mod_id, _name)

    def sv_send_event(self, track_num, note, vel=129, module=0, ctl=0, ctl_val=0, slotnr=None):
        """
        Parameters:
            slot / sv:  slot number / SunVox object ID;
            track_num:  track number (within the virtual pattern);
            note:       0 - nothing;
                        1..127 - note number;
                        128 - note off;
                        129, 130... - see NOTECMD_* defines;
            vel:        velocity 1..129; 0 - default;
            module:     0 (empty) or module number + 1 (1..65535);
            ctl:        0xCCEE;
                        CC - controller number (1..255);
                        EE - effect;
            ctl_val:    value (0..32768) of the controller CC
                         or parameter (0..65535) of the effect EE.

            Return value: 0 (success) or negative error code.
        """
        # ; //track 0; note n; velocity 129 (max); module m;
        # //Send Note ON to the module m:
        # int n = 5 * 12 + 4; //octave 5, note 4
        slot = slotnr or self.slotnr
        return self.svlib.sv_send_event(slot, track_num, note, vel, module+1, ctl, ctl_val)
                                # track 0; note n; velocity 129 (max); module m;


class SoundBoard(CoreLib):

    sample_rate = 44100
    slotnr = -1
    _open = False

    def __init__(self, lib_fullpath=None, slotnr=-1):
        self._fullpath = lib_fullpath
        self.slotnr = slotnr
        if self._fullpath:
            self.init_lib(self._fullpath)

    def init_lib(self, lib_fullpath, config=None):
        # global svlib
        svlib = ctypes.CDLL(Path(lib_fullpath).as_posix())
        # CONNECT TO SOUND SYSTEM
        svlib.sv_init.restype = ctypes.c_int32
        svlib.sv_get_module_name.restype = ctypes.c_char_p
        '''
        config      string with additional configuration in the following format:
                    "option_name=value|option_name=value"; or NULL for auto config;
                    example: "buffer=1024|audiodriver=alsa|audiodevice=hw:0,0";
        sample_rate desired sample rate (Hz); min - 44100; the actual rate may
                    be different, if SV_INIT_FLAG_OFFLINE is not set;
        channels    only 2 supported now;
        flags       set of flags SV_INIT_FLAG_*
        '''
        ver = svlib.sv_init(config, self.sample_rate, 2, 0 )
        self.svlib = svlib

        if ver>=0:
            print (f"Init Sound succeeded!")
            atexit.register(self.deinit)
            print('sample rate', svlib.sv_get_sample_rate())
            self.mount()
            return self.svlib

        print (f"Link Sound failed, error:{ver}")

    def mount(self):
        if self.slotnr > -1:
            self._open = self.open_slot(self.slotnr)
            self.mounted()

            if self.auto_delete:
                atexit.register(self.close)

    def mounted(self):
        pass

    def float_set_volume(self, slotnr, v=1):
        return self.set_volume(slotnr, int(v * 256))


class PlayerFactory(object):
    """Spawn slotted players from the machine.
    """
    slotnr = 0
    max_slots = 16

    def get_lib(self):
        return lib_name

    def get_class(self):
        return Player

    def spawn_player(self, child=None, **kw):
        slotnr = self.slotnr
        if slotnr >= self.max_slots:
            print('Max slots reached')
            return False
        Child = child or self.get_class()
        p = Child(self.get_lib(), slotnr=slotnr, **kw)
        self.slotnr += 1
        return p


player_factory = PlayerFactory()

class Player(SoundBoard):
    auto_delete = True
    OUTPUT = 0

    def example(self):
        filename = "test.sunvox"
        self.play_file(filename)
        # self.volume(1)
        time.sleep(2)
        self.stop()
        # self.close()

    # def mounted(self):
    #     self.example()

    def play_file(self, filename):
        self.load_file(self.slotnr, filename)
        self.play_from_beginning(self.slotnr)

    def volume(self, v=-1):
        return self.float_set_volume(self.slotnr, v)

