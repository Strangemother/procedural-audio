## Sequence strings

A continuous string denoting keys.


Pressing a note for 3 seconds:

    e6-3s

processed as:

    note press time
    e6     -   3s

Or

    e6_ 3s e6‾


Alternative:

    e6+ 3s e6-

therefore a `press` should change:

    e6.3s


processed as:

    note down time note up
    e6     _   3s  e6   ‾

A `press` performs this action as a single entry.

---

The time delays are pauses in the sequence until another input is required.
Therefore a `press` will process the next step immediately, where are a split change
will play without overlap.

Play two notes simultaneously:

    e6.2s e5.2s

The same notes expanded will play procedurally:

    e6+ 2s e6- e5+ 2s e5-

Therefore to convert the split change into simultaneous notes, it can be rewritten:

    # same as e6.2s e5.2s
    e6+ e5+ 2s e6- e5-


Delays are written procedurally. Adding a delay to the second note in both forms:

    form A: e6.2s .5s e5.1.5s
    form B: e6+ .5s e5+ 1.5s e6- e5-


## Picking Instruments

The sequence will work into a target instrument, made as a model with id.

`04` is a SpectrumVoice called "tool1"
`05` is a Generator called "tool2"

    04 | e6.1s ... d1.1s
    05 | e6.1s ... d1.1s

Inline execution

    04 | e6+ .5s e5+ 1.5s e6- e5- | 05 | e6+ e5+ 2s e6- e5-

## Markers

At some point another sequence should start. This can occur _upon_ the beat of another
note. This can be assigned through markers

    04 | e6+ .5s e5+ 1.5s e6- e5- | 05 | #other e6+ e5+ 2s e6- e5-

    #other
    06 | a6+ .1s c6+ 2.2s a6- a6- | tool1 | e6+ e5+ 2s e6- e5-

A marker simply _switches_ the pointer context. This can occur momentarily.

    04 | e6+ .5s e5+ [04 | c3.3s] 1.5s e6- e5- | 05 | #other e6+ e5+ 2s e6- e5-
    04 | e6+ .5s e5+ [#other | c3.3s] 1.5s e6- e5- | 05 | #other e6+ e5+ 2s e6- e5-
    04 | e6+ .5s e5+ [tool2 | c3.3s] 1.5s e6- e5- | 05 | #other e6+ e5+ 2s e6- e5-

Markers can be used at the end of a sequence to divide long lines.
The special `[...]` means the next line in the file:

    04 | e6+ .5s e5+ 1.5s e6- e5- | 05 | e6+ e5+ 2s e6- e5- [...]
    e6+ .5s e5+ 1.5s e6- e5- [...]
    a3.5s b5.1.5s c4.1s

## Events

Send 'events' for the app to collect and perform async actions

    05 | e4.1s ^foo 2s e4.1s

An event can any word or expression and processed by a function or other eventised capture.

## notes

notes are standard piano notes, or numbers of order for the app:

    e6.2s e5.2s
    66.2s 58.2s

    e6+ e5+ 2s e6- e5-
    66+ 58+ 2s 66- 58-

## delays

A line is read in sequence however the app is sync. Therefore the line is read ahead-of-time and processed on the fly.

A delay may occur as part of the natural stepping sequence:

    e4.1s 2s e4.1s
    e6+ e5+ 2s e6- e5-

But a note may delay itself

    e4.1s e4.1s>2s


