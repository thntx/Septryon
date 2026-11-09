const { test } = require('node:test');
const assert = require('node:assert/strict');
const { segment } = require('./xsf-syllables.js');

const split = (text, mode) => segment(text, mode).parts.map(p => p.text);

test('the spaceless manuscript uses complete syllables and preserves its text', () => {
    const text = 'ilx4\u00e9+stxdxmxt\u00e9\u00f34+skxkrxwa+bx93xta+nx9ta+nxlfi4mxm\u00e9+9.';
    assert.deepEqual(split(text), ['i', 'lx', '4\u00e9+s', 'tx', 'dx', 'mx', 't\u00e9', '\u00f34+s',
        'kx', 'krx', 'wa+', 'bx9', '3x', 'ta+', 'nx9', 'ta+', 'nxl', 'fi4', 'mx', 'm\u00e9+9.']);
    assert.equal(split(text).join(''), text);
});

test('CV has priority over VC in KIB; BKK and KTB conservatively keep crossing ligatures', () => {
    assert.deepEqual(split('aka'), ['a', 'ka']);
    assert.deepEqual(split('[aka'), ['[aka']);
    assert.deepEqual(split(']aka'), [']aka']);
    assert.deepEqual(split('atka'), ['at', 'ka']);
    assert.deepEqual(split('ak+aka'), ['ak+a', 'ka']);
});

test('vowel nuclei, explicit glides, codas and complex onsets do not need Catalan words', () => {
    for (const [text, expected] of [
        ['ta+wla', ['ta+w', 'la']], ['xkstra+', ['xks', 'tra+']],
        ['a+kwa', ['a+', 'kwa']], ['a+t1a', ['a+', 't1a']],
        ['a+3ja', ['a+', '3ja']], ['a+pla', ['a+', 'pla']],
        ['a+9tra', ['a+9', 'tra']], ['po+éta', ['po+', '\u00e9', 'ta']],
        ['ma+y', ['ma+y']], ['a+6ka', ['a+6', 'ka']]
    ]) assert.deepEqual(split(text), expected, text);
});

test('quality accents and tonic marks stay with their glyph, byte for byte', () => {
    for (const [text, expected] of [
        ['k\u00e1ka', ['k\u00e1', 'ka']], ['ka\u0301ka', ['ka\u0301', 'ka']],
        ['x\u0300ka', ['x\u0300', 'ka']], ['k\u00b4aka', ['k\u00b4a', 'ka']],
        ['k`aka', ['k`a', 'ka']], ['ka+ka+', ['ka+', 'ka+']],
        ['a*ka', ['a*', 'ka']], ['ak+a', ['ak+a']]
    ]) { assert.deepEqual(split(text), expected); assert.equal(split(text).join(''), text); }
});

test('gemination and punctuation cannot be orphaned by a generated break', () => {
    assert.deepEqual(split('fx;la+s'), ['fx;', 'la+s']);
    assert.deepEqual(split('la:ma'), ['la:', 'ma']);
    assert.deepEqual(split('ka+ka+.,'), ['ka+', 'ka+.,']);
});

test('integrals, minimes, cedilla and palatal n keep their distinct identities', () => {
    assert.deepEqual(split('AKA'), ['A', 'KA']);
    assert.deepEqual(split('{aka'), ['{a', 'ka']);
    for (const text of ['\u00e7a\u00f1a', '\u00c7A\u00d1A', '/A!A', '?a\u00bfa'])
        assert.equal(split(text).join(''), text);
});

test('mode propagation, controls and double-space resets are preserved', () => {
    assert.equal(segment('[ka ka').mode, 'bkk');
    assert.equal(segment('[ka  ka').mode, 'kib');
    assert.deepEqual(split('aka', 'bkk'), ['aka']);
    assert.deepEqual(split('[aka  aka'), ['[aka', '  ', 'a', 'ka']);
    assert.deepEqual(split('[ka]ka{ka}1x'), ['[ka', ']ka', '{ka', '}1x']);
    assert.equal(segment('{ka ka').mode, 'minima');
    assert.equal(segment('{ka  ka').mode, 'kib');
    assert.deepEqual(split('['), ['[']);
});

test('numeral multipliers are never separated from their digit', () => {
    assert.deepEqual(split('}1x1a2c3v'), ['}1x', '1', 'a', '2c', '3v']);
    assert.equal(segment('}1x\u00a1cika').mode, 'kib');
});

test('whitespace, unknown text, emoji and empty input are lossless', () => {
    for (const text of ['', '  ', '\t\n', '\ud83e\uddea\u0301ka', '<script>&ka', '\u200b[ka+', '\u00a0ka\u00a0'])
        assert.equal(split(text).join(''), text);
});

test('large runs remain lossless with bounded onset analysis', () => {
    const text = 'ka+'.repeat(10000) + 'a' + 'w'.repeat(10000) + 'a';
    assert.equal(split(text).join(''), text);
});
