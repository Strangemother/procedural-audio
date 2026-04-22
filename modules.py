

class Synths(object):
    ANALOG_GENERATOR = 'Analog Generator'
    DRUMSYNTH = 'DrumSynth'
    FM = 'FM'
    FMX = 'FMX'
    GENERATOR = 'Generator'
    INPUT = 'Input'
    KICKER = 'Kicker'
    VORBIS_PLAYER = 'Vorbis player'
    SAMPLER = 'Sampler'
    SPECTRAVOICE = 'SpectraVoice'


class Module(object):
    """A mounable module.
    """
    type = Synths.GENERATOR
    name = None # type.lower()
    int_value = -1
    parent = None
    prefix = '  M'

    def sv_get_module_name(self):
        if self.parent:
            return self.parent.sv_get_module_name(self.int_value).decode('utf')

    def sv_set_module_name(self, name):
        if self.parent:
            return self.parent.sv_set_module_name(self.int_value, name)

    def sv_send_event(self, track_num, note, vel=129, ctl=0, ctl_val=0):
        return self.parent.sv_send_event(track_num, note, vel,
                                        self.int_value, ctl, ctl_val)

    def log(self, *a):
        v = ' '.join(map(str, a))
        print(f'{self.prefix}({self.get_name()}#{self.int_value}) {v}')

    def get_name(self):
        return self.name or self.sv_get_module_name() or self.type.lower()

    def get_type(self):
        return self.type

    def xyz(self):
        return [512, 512, 0]

    def set_owner(self, parent, value):
        self.log('set_owner', parent)
        self.parent = parent
        self.set_int(value)

    def set_int(self, value):
        self.log('set_int', value)
        self.int_value = value
        return value

    def connect_to(self, other_int):
        self.log('Connect', self.name, 'to', other_int)
        return self.parent.sv_connect_module(self.int_value, other_int)


class Generator(Module):
    type = Synths.GENERATOR

