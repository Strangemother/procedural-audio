// WebSocket controller for the Procedural Audio server.

const $ = (id) => document.getElementById(id);

const state = {
    ws: null,
    connected: false,
    pending: [],           // queued sends if not connected
    heldNote: null,        // currently-held keyboard note
};

// ---------- Connection ----------

function setStatus(kind, text) {
    const el = $('status');
    el.className = `status ${kind}`;
    el.textContent = text;
}

function connect() {
    const url = $('wsUrl').value.trim();
    if (!url) return;

    if (state.ws) {
        try { state.ws.close(); } catch (e) { /* ignore */ }
    }

    log('info', `connecting to ${url}...`);
    setStatus('connecting', 'connecting');
    $('connectBtn').textContent = 'Cancel';

    try {
        state.ws = new WebSocket(url);
    } catch (err) {
        log('err', `connect error: ${err.message}`);
        setStatus('disconnected', 'disconnected');
        $('connectBtn').textContent = 'Connect';
        return;
    }

    state.ws.addEventListener('open', () => {
        state.connected = true;
        setStatus('connected', 'connected');
        $('connectBtn').textContent = 'Disconnect';
        log('info', 'connected');
        // flush queued
        while (state.pending.length) {
            state.ws.send(state.pending.shift());
        }
        // auto-refresh mappings + instrument lab state
        send({ action: 'list_mappings' });
        send({ action: 'list_module_types' });
        send({ action: 'list_modules' });
    });

    state.ws.addEventListener('message', (ev) => {
        let data;
        try { data = JSON.parse(ev.data); } catch { data = ev.data; }
        log('recv', data);
        handleIncoming(data);
    });

    state.ws.addEventListener('close', () => {
        state.connected = false;
        setStatus('disconnected', 'disconnected');
        $('connectBtn').textContent = 'Connect';
        log('info', 'disconnected');
    });

    state.ws.addEventListener('error', (err) => {
        log('err', 'websocket error');
    });
}

function disconnect() {
    if (state.ws) state.ws.close();
}

function send(obj) {
    const payload = JSON.stringify(obj);
    if (state.connected && state.ws && state.ws.readyState === 1) {
        state.ws.send(payload);
        log('sent', obj);
    } else {
        state.pending.push(payload);
        log('info', `queued (offline): ${payload}`);
    }
}

// ---------- Log ----------

function log(kind, data) {
    const el = $('log');
    const time = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = `entry ${kind}`;
    const text = typeof data === 'string' ? data : JSON.stringify(data);
    const prefix = { sent: '→', recv: '←', err: '!', info: '·' }[kind] || '';
    entry.innerHTML = `<span class="time">${time}</span>${prefix} ${escapeHtml(text)}`;
    el.appendChild(entry);
    el.scrollTop = el.scrollHeight;
}

function escapeHtml(s) {
    return s.replace(/[&<>"']/g, (c) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

// ---------- Keyboard UI ----------

const KEYS = [
    { note: 'C', black: false, kb: 'a' },
    { note: 'c', black: true,  kb: 'w' }, // C#
    { note: 'D', black: false, kb: 's' },
    { note: 'd', black: true,  kb: 'e' }, // D#
    { note: 'E', black: false, kb: 'd' },
    { note: 'F', black: false, kb: 'f' },
    { note: 'f', black: true,  kb: 't' }, // F#
    { note: 'G', black: false, kb: 'g' },
    { note: 'g', black: true,  kb: 'y' }, // G#
    { note: 'A', black: false, kb: 'h' },
    { note: 'a', black: true,  kb: 'u' }, // A#
    { note: 'B', black: false, kb: 'j' },
    { note: 'C', black: false, kb: 'k', octaveShift: 1 },
];

function buildKeyboard() {
    const kb = $('keyboard');
    kb.innerHTML = '';
    const whiteKeys = KEYS.filter(k => !k.black);
    const whiteWidth = 100 / whiteKeys.length;

    // Place white keys first (flex layout)
    KEYS.forEach((k) => {
        if (k.black) return;
        const el = document.createElement('div');
        el.className = 'key white';
        el.dataset.note = k.note;
        el.dataset.kb = k.kb;
        el.dataset.octaveShift = k.octaveShift || 0;
        el.innerHTML = `${k.note}<br/><small>${k.kb.toUpperCase()}</small>`;
        attachKey(el, k);
        kb.appendChild(el);
    });

    // Place black keys absolutely on top
    let whiteIndex = 0;
    KEYS.forEach((k) => {
        if (!k.black) { whiteIndex++; return; }
        const el = document.createElement('div');
        el.className = 'key black';
        el.dataset.note = k.note;
        el.dataset.kb = k.kb;
        // Position between previous and next white key
        const leftPct = (whiteIndex * whiteWidth) - (whiteWidth * 0.25);
        el.style.left = `${leftPct}%`;
        el.style.width = `${whiteWidth * 0.5}%`;
        el.innerHTML = `<small>${k.kb.toUpperCase()}</small>`;
        attachKey(el, k);
        kb.appendChild(el);
    });
}

function noteFromKey(k) {
    const baseOctave = parseInt($('octave').value, 10) || 4;
    const octave = baseOctave + (k.octaveShift || 0);
    return `${k.note}${octave}`;
}

function attachKey(el, k) {
    const press = (e) => {
        e.preventDefault();
        pressNote(el, k);
    };
    const release = (e) => {
        e.preventDefault();
        releaseNote(el);
    };
    el.addEventListener('mousedown', press);
    el.addEventListener('mouseup', release);
    el.addEventListener('mouseleave', (e) => {
        if (e.buttons) releaseNote(el);
    });
    el.addEventListener('touchstart', press, { passive: false });
    el.addEventListener('touchend', release, { passive: false });
}

function pressNote(el, k) {
    if (el.classList.contains('active')) return;
    el.classList.add('active');
    const note = noteFromKey(k);
    const velocity = parseInt($('velocity').value, 10);
    const moduleEl = $('activeInstrument');
    const module = moduleEl ? moduleEl.value.trim() : '';
    state.heldNote = { el, note, module };
    const payload = { action: 'note', note, velocity };
    if (module) payload.module = module;
    send(payload);
}

function releaseNote(el) {
    if (!el.classList.contains('active')) return;
    el.classList.remove('active');
    const payload = { action: 'note_off' };
    // Send note_off to the same module the press used, if any
    if (state.heldNote && state.heldNote.module) {
        payload.module = state.heldNote.module;
    }
    send(payload);
    state.heldNote = null;
}

// Computer keyboard input
document.addEventListener('keydown', (e) => {
    if (e.repeat) return;
    if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

    if (e.key === 'z') { adjustOctave(-1); return; }
    if (e.key === 'x') { adjustOctave(+1); return; }

    const el = document.querySelector(`.key[data-kb="${e.key.toLowerCase()}"]`);
    if (el) {
        const k = KEYS.find(k => k.kb === e.key.toLowerCase());
        pressNote(el, k);
    }
});
document.addEventListener('keyup', (e) => {
    if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
    const el = document.querySelector(`.key[data-kb="${e.key.toLowerCase()}"]`);
    if (el) releaseNote(el);
});

function adjustOctave(delta) {
    const o = $('octave');
    o.value = Math.max(0, Math.min(9, (parseInt(o.value, 10) || 4) + delta));
}

// ---------- Device mappings / modules ----------

function renderDeviceButtons(mappings) {
    const wrap = $('deviceButtons');
    wrap.innerHTML = '';
    Object.keys(mappings).forEach((name) => {
        const b = document.createElement('button');
        b.textContent = name;
        b.title = JSON.stringify(mappings[name]);
        b.addEventListener('click', () => {
            send({ action: 'device_event', event: name, device: 'web_ui' });
        });
        wrap.appendChild(b);
    });
}

function renderModules(modules) {
    const wrap = $('modules');
    wrap.innerHTML = '';
    modules.forEach((m) => {
        const b = document.createElement('button');
        b.textContent = `${m.id}: ${m.name}`;
        b.addEventListener('click', () => {
            $('moduleName').value = m.name;
        });
        wrap.appendChild(b);
    });
}

// ---------- Wiring ----------

function wire() {
    $('connectBtn').addEventListener('click', () => {
        if (state.connected) disconnect();
        else connect();
    });

    // Simple action buttons
    document.querySelectorAll('button[data-action]').forEach((b) => {
        b.addEventListener('click', () => send({ action: b.dataset.action }));
    });

    $('volume').addEventListener('input', (e) => {
        $('volumeValue').textContent = (+e.target.value).toFixed(2);
    });
    $('volume').addEventListener('change', (e) => {
        send({ action: 'volume', value: parseFloat(e.target.value) });
    });

    $('velocity').addEventListener('input', (e) => {
        $('velocityValue').textContent = e.target.value;
    });

    $('playFileBtn').addEventListener('click', () => {
        send({ action: 'play_file', file: $('fileInput').value });
    });
    $('loadFileBtn').addEventListener('click', () => {
        send({ action: 'load_file', file: $('fileInput').value });
    });
    $('listModulesBtn').addEventListener('click', () => {
        send({ action: 'list_modules' });
    });

    $('moduleNoteBtn').addEventListener('click', () => {
        send({
            action: 'play_module_note',
            module: $('moduleName').value,
            note: $('moduleNote').value,
            duration: parseFloat($('moduleDuration').value),
            file: $('fileInput').value || undefined,
        });
    });

    $('listMappingsBtn').addEventListener('click', () => send({ action: 'list_mappings' }));
    $('sendDeviceBtn').addEventListener('click', () => {
        const name = $('deviceEvent').value.trim();
        if (name) send({ action: 'device_event', event: name, device: 'web_ui' });
    });

    $('sendRawBtn').addEventListener('click', () => {
        try {
            const obj = JSON.parse($('rawJson').value);
            send(obj);
        } catch (err) {
            log('err', `invalid JSON: ${err.message}`);
        }
    });

    $('clearLogBtn').addEventListener('click', () => { $('log').innerHTML = ''; });

    // Auto-connect if the URL contains ?autoconnect
    if (new URLSearchParams(location.search).has('autoconnect')) {
        connect();
    }
}

// ============================================================
// Procedural Flight — a gentle Tony-Ann-inspired piano companion
// ============================================================
//
// The scheduler drives three independent voices onto separate
// SunVox tracks so they can sustain polyphonically:
//
//   track 0  bass           — low sustained root / fifth
//   track 1..3  arpeggio    — rolling mid-register chord tones
//   track 4  melody         — sparse high motif with rubato
//   track 5  flutter        — rare grace-note ornaments
//
// Timing is phrase-based: a progression of chord "bars" is chosen,
// and each bar is subdivided into 8 sixteenth-note slots. Notes
// are picked probabilistically to avoid the feeling of a loop.

const FlightKeys = {
    // Each entry: degrees (scale) and a rotating chord progression.
    // Chords are [root letter, quality] — quality chooses triad notes.
    'F':  { scale: ['F','G','A','A#','C','D','E'],
            progressions: [
                [['F','maj'], ['A','min'], ['A#','maj'], ['C','maj']],
                [['F','maj'], ['C','maj'], ['D','min'], ['A#','maj']],
                [['D','min'], ['A#','maj'], ['F','maj'], ['C','maj']],
            ] },
    'C':  { scale: ['C','D','E','F','G','A','B'],
            progressions: [
                [['C','maj'], ['G','maj'], ['A','min'], ['F','maj']],
                [['A','min'], ['F','maj'], ['C','maj'], ['G','maj']],
                [['C','maj'], ['E','min'], ['F','maj'], ['G','maj']],
            ] },
    'D':  { scale: ['D','E','F#','G','A','B','C#'],
            progressions: [
                [['D','maj'], ['A','maj'], ['B','min'], ['G','maj']],
                [['B','min'], ['G','maj'], ['D','maj'], ['A','maj']],
                [['D','maj'], ['F#','min'], ['G','maj'], ['A','maj']],
            ] },
    'Am': { scale: ['A','B','C','D','E','F','G'],
            progressions: [
                [['A','min'], ['F','maj'], ['C','maj'], ['G','maj']],
                [['A','min'], ['E','min'], ['F','maj'], ['G','maj']],
                [['D','min'], ['A','min'], ['F','maj'], ['C','maj']],
            ] },
    'Dm': { scale: ['D','E','F','G','A','A#','C'],
            progressions: [
                [['D','min'], ['A#','maj'], ['F','maj'], ['C','maj']],
                [['G','min'], ['D','min'], ['A#','maj'], ['A','maj']],
                [['D','min'], ['F','maj'], ['C','maj'], ['A','maj']],
            ] },
};

// Convert "C", "F#", "A#" → the server's note-letter convention
// (lowercase letter = sharp, no explicit flats; "Bb" maps to "a"+... we use sharps).
function toServerLetter(pitchClass) {
    // pitchClass is like "C", "F#", "A#"; notes.py uses: upper = natural, lower = sharp
    const base = pitchClass[0];
    const sharp = pitchClass.includes('#');
    if (!sharp) return base;
    // Map sharps to the lowercase encoding used in notes.py
    // C#→c, D#→d, F#→f, G#→g, A#→a  (E# and B# do not exist in notes.py)
    return base.toLowerCase();
}

function noteName(pitchClass, octave) {
    return `${toServerLetter(pitchClass)}${octave}`;
}

// Triad pitch classes for a given root + quality.
function triad(root, quality) {
    const chromatic = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
    const idx = chromatic.indexOf(root);
    const intervals = quality === 'min' ? [0, 3, 7] : [0, 4, 7];
    return intervals.map(i => chromatic[(idx + i) % 12]);
}

// ---------- Scheduler ----------

const flight = {
    running: false,
    timeouts: new Set(),
    heldByTrack: new Map(),     // track -> true if a note is currently held
    barIndex: 0,
    progression: null,
    octaveDrift: 0,             // slowly wanders up/down over time
};

function flightSchedule(delay, fn) {
    const id = setTimeout(() => {
        flight.timeouts.delete(id);
        if (flight.running) fn();
    }, delay);
    flight.timeouts.add(id);
    return id;
}

function flightPlayNote(track, noteStr, velocity, durationMs) {
    if (!flight.running) return;
    const module = $('flightModule') ? $('flightModule').value.trim() : '';

    if (module) {
        // Route through a named module (e.g. "Piano") using play_module_note.
        // play_module_note handles both note-on and the scheduled note-off
        // server-side, so we don't track held state ourselves.
        send({
            action: 'play_module_note',
            module,
            note: noteStr,
            velocity,
            duration: durationMs / 1000,
            track,
        });
        return;
    }

    // Fallback: use the default generator track with manual note_off scheduling.
    if (flight.heldByTrack.get(track)) {
        send({ action: 'note_off', track });
    }
    send({ action: 'note', note: noteStr, velocity, track });
    flight.heldByTrack.set(track, true);
    flightSchedule(durationMs, () => {
        send({ action: 'note_off', track });
        flight.heldByTrack.set(track, false);
    });
}

function rand(min, max) { return Math.random() * (max - min) + min; }
function choose(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
function chance(p) { return Math.random() < p; }

// Humanize timing — small swing + slight rubato
function humanize(ms) { return ms + rand(-18, 18); }

function moodParams(mood) {
    switch (mood) {
        case 'soar':
            return { arpDensity: 0.85, melodyChance: 0.55, flutterChance: 0.18,
                     octaveBase: 4, velJitter: 15 };
        case 'flutter':
            return { arpDensity: 0.95, melodyChance: 0.35, flutterChance: 0.40,
                     octaveBase: 4, velJitter: 22 };
        case 'dream':
            return { arpDensity: 0.55, melodyChance: 0.30, flutterChance: 0.12,
                     octaveBase: 3, velJitter: 10 };
        case 'drift':
        default:
            return { arpDensity: 0.70, melodyChance: 0.40, flutterChance: 0.15,
                     octaveBase: 4, velJitter: 14 };
    }
}

function scheduleBar(chord, bpm, params) {
    if (!flight.running) return;

    const beatMs = 60000 / bpm;
    const barMs = beatMs * 4;
    const sixteenth = beatMs / 4;

    const [rootPC, quality] = chord;
    const chordPCs = triad(rootPC, quality);     // [root, third, fifth]
    const baseVel = parseInt($('flightVelocity').value, 10);
    const octave = params.octaveBase + flight.octaveDrift;

    const useBass    = $('flightBassEnabled').checked;
    const useArp     = $('flightArpEnabled').checked;
    const useMelody  = $('flightMelodyEnabled').checked;
    const useFlutter = $('flightFlutterEnabled').checked;

    // --- BASS (track 0) --- deep, sustained, slightly delayed
    if (useBass) {
        const bassNote = noteName(rootPC, Math.max(1, octave - 2));
        const bassVel = Math.max(20, baseVel - 25 + Math.floor(rand(-5, 5)));
        flightSchedule(humanize(30), () => {
            flightPlayNote(0, bassNote, bassVel, barMs * 0.95);
        });
        // Optional fifth on beat 3 for some bars
        if (chance(0.35)) {
            flightSchedule(humanize(beatMs * 2 + 20), () => {
                flightPlayNote(0, noteName(chordPCs[2], Math.max(1, octave - 2)),
                    Math.max(20, bassVel - 8), barMs * 0.5);
            });
        }
    }

    // --- ARPEGGIO (tracks 1..3) --- rolling chord tones across the bar
    if (useArp) {
        // Build a pattern of 8 sixteenth-slot positions, picking chord tones.
        // Skip some slots based on density to leave breathing room.
        const pattern = [0, 2, 4, 6, 1, 3, 5, 7]; // interleaved for flowing feel
        for (let i = 0; i < 8; i++) {
            if (!chance(params.arpDensity)) continue;
            const slot = pattern[i];
            const tone = chordPCs[i % chordPCs.length];
            const arpOct = octave + (i >= 4 ? 1 : 0) + (chance(0.15) ? 1 : 0);
            const track = 1 + (i % 3);
            const vel = Math.max(25, baseVel - 10 + Math.floor(rand(-params.velJitter, params.velJitter)));
            const when = humanize(slot * sixteenth);
            // Hold length: slightly longer than a sixteenth — lets notes bloom/overlap
            const hold = sixteenth * rand(1.4, 2.6);
            flightSchedule(when, () => {
                flightPlayNote(track, noteName(tone, arpOct), vel, hold);
            });
        }
    }

    // --- MELODY (track 4) --- sparse, lyrical, on strong beats with grace
    if (useMelody && chance(params.melodyChance)) {
        const key = $('flightKey').value;
        const scale = FlightKeys[key].scale;
        // Prefer chord tones but drift to nearby scale tones
        const candidate = chance(0.6)
            ? choose(chordPCs)
            : choose(scale);
        const beat = choose([0, 1, 2]);       // start on beat 1, 2 or 3
        const startMs = beat * beatMs + rand(-30, 80);
        const melOct = octave + 1 + (chance(0.3) ? 1 : 0);
        const vel = Math.min(120, baseVel + 10 + Math.floor(rand(-6, 10)));
        const hold = beatMs * rand(1.2, 2.5);

        flightSchedule(humanize(startMs), () => {
            // Occasional grace note a step above
            if (chance(0.35)) {
                const graceIdx = (scale.indexOf(candidate) + 1) % scale.length;
                const grace = scale[graceIdx] || candidate;
                flightPlayNote(4, noteName(grace, melOct), Math.max(30, vel - 25), 90);
                flightSchedule(110, () => {
                    flightPlayNote(4, noteName(candidate, melOct), vel, hold);
                });
            } else {
                flightPlayNote(4, noteName(candidate, melOct), vel, hold);
            }
        });
    }

    // --- FLUTTER (track 5) --- rapid ornamental triplet, airy
    if (useFlutter && chance(params.flutterChance)) {
        const key = $('flightKey').value;
        const scale = FlightKeys[key].scale;
        const startIdx = scale.indexOf(choose(chordPCs));
        const dir = chance(0.5) ? 1 : -1;
        const flutterStart = beatMs * choose([1, 2, 3]) + rand(-40, 40);
        const noteGap = sixteenth * 0.45;
        const flutterOct = octave + 2;
        const vel = Math.max(25, baseVel - 15);

        for (let n = 0; n < 3; n++) {
            const idx = ((startIdx + dir * n) + scale.length * 4) % scale.length;
            const pc = scale[idx];
            flightSchedule(humanize(flutterStart + n * noteGap), () => {
                flightPlayNote(5, noteName(pc, flutterOct), vel, noteGap * 2.2);
            });
        }
    }

    // Schedule next bar
    flightSchedule(barMs, () => {
        // Gentle octave drift to feel like altitude shifts
        if (chance(0.12)) {
            flight.octaveDrift = Math.max(-1, Math.min(1, flight.octaveDrift + choose([-1, 1])));
        }

        flight.barIndex += 1;
        let prog = flight.progression;

        // Occasionally hop to a different progression for variety
        if (flight.barIndex % (prog.length * 2) === 0 && chance(0.5)) {
            const keyData = FlightKeys[$('flightKey').value];
            flight.progression = choose(keyData.progressions);
            flight.barIndex = 0;
            prog = flight.progression;
        }

        const next = prog[flight.barIndex % prog.length];
        scheduleBar(next, parseInt($('flightTempo').value, 10), moodParams($('flightMood').value));
    });
}

function flightStart() {
    if (flight.running) return;
    if (!state.connected) {
        log('err', 'connect to the server before starting the flight');
        return;
    }
    flight.running = true;
    flight.barIndex = 0;
    flight.octaveDrift = 0;
    flight.heldByTrack.clear();

    const keyData = FlightKeys[$('flightKey').value];
    flight.progression = choose(keyData.progressions);

    $('flightStatus').textContent = 'soaring...';
    log('info', `flight started — key ${$('flightKey').value}, mood ${$('flightMood').value}`);

    scheduleBar(flight.progression[0],
                parseInt($('flightTempo').value, 10),
                moodParams($('flightMood').value));
}

function flightStop() {
    if (!flight.running) return;
    flight.running = false;

    // Cancel pending timeouts
    for (const id of flight.timeouts) clearTimeout(id);
    flight.timeouts.clear();

    // Silence every flight track. When routed through a module,
    // play_module_note schedules its own note-off server-side via
    // asyncio.sleep, so clearing client timeouts isn't enough —
    // we must proactively send NOTE_OFF to each track on the module.
    const module = $('flightModule') ? $('flightModule').value.trim() : '';
    const payload = { action: 'all_notes_off', tracks: [0, 1, 2, 3, 4, 5] };
    if (module) payload.module = module;
    send(payload);
    // Also a global fallback to catch anything routed to the default engine.
    send({ action: 'all_notes_off', tracks: [0, 1, 2, 3, 4, 5] });

    flight.heldByTrack.clear();

    $('flightStatus').textContent = 'idle';
    log('info', 'flight stopped');
}

function wireFlight() {
    $('flightStartBtn').addEventListener('click', flightStart);
    $('flightStopBtn').addEventListener('click', flightStop);
    $('flightTempo').addEventListener('input', (e) => {
        $('flightTempoValue').textContent = e.target.value;
    });
    $('flightVelocity').addEventListener('input', (e) => {
        $('flightVelocityValue').textContent = e.target.value;
    });
}

// ============================================================
// Instrument Lab
// ============================================================

const lab = {
    modules: [],           // [{id, name}]
    selectedModule: null,  // name
};

function refreshModuleList() {
    send({ action: 'list_modules' });
}

function renderModuleList(modules) {
    lab.modules = modules;
    const wrap = $('moduleList');
    wrap.innerHTML = '';
    modules.forEach((m) => {
        const b = document.createElement('button');
        b.textContent = `${m.id}: ${m.name}`;
        if (m.name === lab.selectedModule) b.classList.add('selected');
        b.addEventListener('click', () => {
            lab.selectedModule = m.name;
            send({ action: 'get_module_ctls', module: m.name });
            renderModuleList(lab.modules);
        });
        wrap.appendChild(b);
    });
    // Also mirror into the existing modules panel
    renderModules(modules);
}

function renderCtlInspector(payload) {
    const wrap = $('ctlInspector');
    wrap.innerHTML = '';
    const title = document.createElement('div');
    title.className = 'inspector-title';
    title.innerHTML = `<span>⚙ ${escapeHtml(payload.module)} · ${payload.ctls.length} controllers</span>
        <button class="tiny" id="removeModuleBtn">remove module</button>`;
    wrap.appendChild(title);

    payload.ctls.forEach((c) => {
        const row = document.createElement('div');
        row.className = 'ctl';
        // Display scaled value where possible; edit the raw value (0..32768 is typical).
        const maxRaw = 32768;
        const rawVal = Math.max(0, Math.min(maxRaw, c.raw));
        row.innerHTML = `
            <div class="ctl-name" title="${escapeHtml(c.name)}">${escapeHtml(c.name)}</div>
            <input class="ctl-slider" type="range" min="0" max="${maxRaw}" value="${rawVal}" />
            <div class="ctl-value">${c.scaled}</div>
        `;
        const slider = row.querySelector('.ctl-slider');
        const valEl = row.querySelector('.ctl-value');
        let throttleId = null;
        slider.addEventListener('input', (e) => {
            const v = parseInt(e.target.value, 10);
            valEl.textContent = v;
            if (throttleId) return;
            throttleId = setTimeout(() => {
                send({
                    action: 'set_module_ctl',
                    module: payload.module,
                    ctl: c.index,
                    value: parseInt(slider.value, 10),
                });
                throttleId = null;
            }, 30);
        });
        wrap.appendChild(row);
    });

    // Remove-module button
    const rm = wrap.querySelector('#removeModuleBtn');
    if (rm) rm.addEventListener('click', () => {
        if (!confirm(`Remove module "${payload.module}"?`)) return;
        send({ action: 'remove_module', module: payload.module });
        lab.selectedModule = null;
        setTimeout(refreshModuleList, 100);
    });
}

function populateModuleTypes(types) {
    const sel = $('newModuleType');
    sel.innerHTML = '';
    types.forEach((t) => {
        const opt = document.createElement('option');
        opt.value = t;
        opt.textContent = t;
        sel.appendChild(opt);
    });
    sel.value = 'FMX';
}

function wireLab() {
    $('buildPianoBtn').addEventListener('click', () => {
        send({ action: 'build_piano', name: 'Piano' });
    });
    $('refreshModulesBtn').addEventListener('click', refreshModuleList);
    $('loadInstrumentBtn').addEventListener('click', () => {
        const file = $('loadInstrumentPath').value.trim();
        if (!file) return;
        send({ action: 'load_module_file', file, connect_to_output: true });
    });
    $('createModuleBtn').addEventListener('click', () => {
        const type = $('newModuleType').value;
        const name = $('newModuleName').value.trim() || type;
        send({ action: 'create_module', type, name, connect_to_output: true });
    });
    $('connectBtn2').addEventListener('click', () => {
        const src = $('connectSrc').value.trim();
        const dst = $('connectDst').value.trim() || 'OUT';
        if (!src) return;
        send({ action: 'connect_modules', source: src, destination: dst });
    });
}

// Central incoming-message dispatcher. Keeps all render hooks in one place,
// so we can't miss a response due to listener-ordering races.
function handleIncoming(data) {
    if (!data || typeof data !== 'object') return;

    // Surface server-side errors prominently
    if (data.status === 'error') {
        log('err', `server error: ${data.message || JSON.stringify(data)}`);
    }

    if (data.action === 'list_mappings' && data.mappings) {
        renderDeviceButtons(data.mappings);
    }
    if (data.action === 'list_modules' && data.modules) {
        renderModuleList(data.modules);
    }
    if (data.action === 'get_module_ctls' && data.ctls) {
        renderCtlInspector(data);
    }
    if (data.action === 'list_module_types' && data.types) {
        populateModuleTypes(data.types);
    }

    // Anything that mutates the module graph → re-list modules so the UI reflects it.
    if (data.status === 'ok' && [
        'build_piano', 'create_module', 'remove_module',
        'load_module_file', 'connect_modules'
    ].includes(data.action)) {
        // Small delay to let SunVox settle before re-querying
        setTimeout(() => send({ action: 'list_modules' }), 80);
    }
}

buildKeyboard();
wire();
wireFlight();
wireLab();
