(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    else root.XSFSyllables = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
    'use strict';

    const ALPHABET = new Set("xaieuoy6w2\u00e7hsz1jk5gq\u00bat3dc\u00a1p8bfvlr74n09m\u00f1'");
    const SHIFT = Object.fromEntries(Object.entries({
        '\u00ba': '\u00aa', '1': '!', '2': '"', '3': '\u00b7', '4': '$',
        '5': '%', '6': '&', '7': '/', '8': '(', '9': ')', '0': '=',
        "'": '?', '\u00a1': '\u00bf'
    }).map(([a, b]) => [b, a]));
    const MODES = { '[': 'bkk', ']': 'ktb', '}': 'minima', '{': 'number' };
    const DIGITS = new Set('\u00ba1234567890qwertyuiopasdfghjkl\u00f1z');
    const GLIDES = new Set(['y', 'w', '6', '2']);
    const AFFRICATES = new Set(['t1', '3j', 'ts', '3z']);
    const MARK = /\p{M}/u;

    function letter(ch) {
        const base = SHIFT[ch] || ch.toLowerCase();
        const vowel = /^[aeioux][\u0300\u0301]*$/.test(base.normalize('NFD'));
        if (!vowel && !ALPHABET.has(base) && base !== ':' && base !== ';') return null;
        return { base: vowel ? base.normalize('NFD')[0] : base, vowel,
            lower: !SHIFT[ch] && ch === ch.toLowerCase() };
    }

    function onset(chars) {
        if (!chars.length) return true;
        if (chars.some(c => c === ':' || c === ';')) return false;
        if (chars.length === 1) return true;
        if (GLIDES.has(chars[chars.length - 1])) return onset(chars.slice(0, -1));
        if (chars.length !== 2) return false;
        const pair = chars.join('');
        if (AFFRICATES.has(pair)) return true;
        return 'p8bfvk5g'.includes(chars[0]) && 'lr'.includes(chars[1]) ||
            't3d'.includes(chars[0]) && chars[1] === 'r';
    }

    function runBreaks(tokens, mode) {
        if (tokens.length < 2) return [];
        if (mode === 'number') {
            const result = [];
            for (let i = 0; i < tokens.length; i++) {
                if (tokens[i].lower && DIGITS.has(tokens[i].base) &&
                    i + 1 < tokens.length && tokens[i + 1].lower &&
                    'xcv'.includes(tokens[i + 1].base) && !tokens[i].postfix) i++;
                if (i + 1 < tokens.length) result.push(tokens[i + 1].start);
            }
            return result;
        }

        // Mirror the font's CV-first / VC-second KIB lookups. BKK and KTB
        // instead match both directions in one left-to-right lookup.
        const group = tokens.map((_, i) => i);
        const paired = tokens.map(() => false);
        const pair = (i, inverse) => {
            const a = tokens[i], b = tokens[i + 1];
            if (!a.lower || !b.lower || a.postfix || paired[i] || paired[i + 1]) return;
            if (a.vowel === inverse && b.vowel !== inverse &&
                a.base !== ':' && a.base !== ';' && b.base !== ':' && b.base !== ';') {
                group[i + 1] = i;
                paired[i] = paired[i + 1] = true;
            }
        };
        if (mode === 'kib') {
            for (let i = 0; i + 1 < tokens.length; i++) pair(i, false);
            for (let i = 0; i + 1 < tokens.length; i++) pair(i, true);
        } else if (mode === 'bkk' || mode === 'ktb') {
            for (let i = 0; i + 1 < tokens.length; i++) pair(i, tokens[i].vowel);
        }

        const nuclei = tokens.flatMap((t, i) => t.vowel ? [i] : []);
        const result = [];
        for (let v = 1; v < nuclei.length; v++) {
            const left = nuclei[v - 1], right = nuclei[v];
            let start = right;
            for (let i = right - 1; i >= Math.max(left + 1, right - 3); i--) {
                if (onset(tokens.slice(i, right).map(t => t.base))) start = i;
            }
            // A source ligature can straddle a phonetic boundary (notably VC
            // in BKK/KTB). Keep both syllables together rather than cut a glyph.
            if (start > 0 && group[start] !== group[start - 1] &&
                tokens[start].base !== ':' && tokens[start].base !== ';') result.push(tokens[start].start);
        }
        return result;
    }

    function segment(text, initialMode = 'kib') {
        const parts = [];
        let mode = initialMode, runMode = mode, start = 0, i = 0, tokens = [];
        const push = (value, space = false) => { if (value) parts.push({ text: value, space }); };
        const flush = end => {
            const breaks = runBreaks(tokens, runMode);
            let from = start;
            for (const at of breaks) { push(text.slice(from, at)); from = at; }
            push(text.slice(from, end));
            tokens = []; start = end;
        };
        while (i < text.length) {
            let ch = String.fromCodePoint(text.codePointAt(i));
            if (ch in MODES) {
                if (tokens.length) flush(i);
                mode = MODES[ch]; runMode = mode;
                i += ch.length;
                continue;
            }
            let from = i;
            if ((ch === '`' || ch === '\u00b4') && i + 1 < text.length && letter(text[i + 1])?.vowel) {
                i++; ch = text[i];
            }
            const info = letter(ch);
            if (info) {
                i += ch.length;
                while (i < text.length && MARK.test(String.fromCodePoint(text.codePointAt(i))))
                    i += String.fromCodePoint(text.codePointAt(i)).length;
                const raw = text.slice(from, i);
                if (mode === 'number' && !(info.lower && raw === info.base &&
                    (DIGITS.has(info.base) || 'xcv:;'.includes(info.base)))) {
                    flush(from); mode = runMode = 'kib';
                }
                tokens.push({ ...info, start: from, end: i, postfix: false });
                continue;
            }
            if ((ch === '+' || ch === '*') && tokens.length) {
                i += ch.length;
                while (i < text.length && MARK.test(String.fromCodePoint(text.codePointAt(i))))
                    i += String.fromCodePoint(text.codePointAt(i)).length;
                tokens[tokens.length - 1].end = i;
                tokens[tokens.length - 1].postfix = true;
                continue;
            }
            flush(from);
            if (/\s/u.test(ch)) {
                const match = text.slice(i).match(/^\s+/u)[0];
                push(match, true); i += match.length;
                if (match.includes('  ') || /[\r\n\t]/.test(match)) mode = 'kib';
            } else {
                i += ch.length;
                while (i < text.length && MARK.test(String.fromCodePoint(text.codePointAt(i))))
                    i += String.fromCodePoint(text.codePointAt(i)).length;
                // Keep sentence punctuation with the preceding syllable.
                if (/[.,\u2026]/u.test(ch) && parts.length && !parts[parts.length - 1].space)
                    parts[parts.length - 1].text += ch;
                else push(text.slice(from, i));
                if (!'.,-_<>+*'.includes(ch)) mode = 'kib';
            }
            start = i; runMode = mode;
        }
        flush(text.length);
        return { parts, mode };
    }

    function decorate(block) {
        const document = block.ownerDocument;
        const walker = document.createTreeWalker(block, 4);
        const nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        let mode = 'kib';
        for (const node of nodes) {
            // Monospace Markdown syntax starts a separate font-shaping run.
            if (node.parentElement.closest('.md-syntax')) { mode = 'kib'; continue; }
            const result = segment(node.data, mode);
            mode = result.mode;
            if (!node.data || !result.parts.some(p => !p.space)) continue;
            const run = document.createElement('span');
            run.className = 'xsf-run';
            for (const part of result.parts) {
                if (part.space) run.append(document.createTextNode(part.text));
                else {
                    const syllable = document.createElement('span');
                    syllable.className = 'xsf-syllable';
                    syllable.textContent = part.text;
                    run.append(syllable);
                }
            }
            node.replaceWith(run);
        }
    }

    return { segment, decorate };
});
