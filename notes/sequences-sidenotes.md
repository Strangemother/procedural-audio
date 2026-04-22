## Research

The sequences is a concept extracted from the the VOL project, where the linear process convert to tasks within the grid mesh of work.

A sequence translated to a chain of work for a 'task' within the VOL.

A line from the app:

    04 | e6+ .5s e5+ 1.5s e6- e5- | 05 | #other e6+ e5+ 2s e6- e5-

Converting this to a VOL chain sequence, the `04` presents the 'layer' and each step is a pointer movement. The key converts to a _position_ in the `04` layer.

The delays provide (notably rare) hardcoded pauses after a _previous_ step executes and completes. The `+` and `-` for a note are kinda redundant for a pointer step for now:

    02 | 01 ff e6 b4 51 e5 | 05 | #other e6 e5 2s e6 e5

The above line presents the sequence:

+ In unit `02`, run the following ...
+ execute each pointer marker in sequence `01 ff e6 b4 51 e5`
    + Each step is chain blocking
    + Steps are 'names', but tranlsate (for fun) to HEX
    + each pointer position maintains a VOL context state
+ Move to layer `05`, with the existing context
+ pronounce event `#other`
+ execute each pointer marker in sequence `e5 d6`
+ wait for `2s`
+ execute each pointer marker in sequence `51 e5`

As the sequence complete, there is a _release_ and the pointer continued on within the parent.

# `04` Machine or Context

Within the sound system the `04` represents the ID of the module within the sound system. It _receives_ the incoming patterm as the keys to play - or more precisly the executing tool generates commands as ir processes forward.

Within a VOL, the `04` indicates a _Context_ to use a memory location, storing information across pointer steps. It is a executing machine and will process incoming data for further dispatch.