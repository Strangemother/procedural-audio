from itertools import cycle


class Notes(object):

    EMPTY = 0
    NOTE_OFF = 128
    ALL_NOTES_OFF = 129  # notes of all synths off
    CLEAN_SYNTHS = 130  # stop and clean all synths
    STOP = 131
    PLAY = 132
    SET_PITCH = 133
    PREV_TRACK = 134

    # Generated on the fly.
    def __init__(self):
        d = self.generate()
        self.__dict__.update(d)

    def generate(self):
        letters = 'CDEFGAB'
        ints = 0, 10
        iv = 0
        r = {}
        for i in range(*ints):
            for letter in letters:
                for c in (letter.upper(), letter.lower()):
                    if c in ['e', 'b']:
                        continue
                    iv += 1
                    r[f'{c}{i}'] = iv

        return r

    def octave_note(self, octave, note=0, offset=True ):
        return octave * 12 + note + int(offset)

    on = octave_note