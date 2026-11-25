"""Build/compare Sèptryón's tab icons against the real Windows Chrome tab strip.

Requires Selenium, Pillow, numpy and pywin32. No input, desktop screenshots or
existing browser profiles: PrintWindow paints only the ChromeDriver-owned HWND.
"""
import argparse
import ctypes
from ctypes import wintypes
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
import struct
from tempfile import gettempdir
from threading import Thread
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

import numpy as np
from PIL import Image, ImageChops
from selenium import webdriver
import win32gui
import win32process
import win32ui


SITE = Path(__file__).resolve().parents[1]
ASSETS = SITE / "icons"
SCALES = (1, 1.25, 1.5, 1.75, 2)
PUBLIC = "https://thntx.github.io/Septryon/"


class Handler(SimpleHTTPRequestHandler):
    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, BrokenPipeError):
            pass

    def do_GET(self):
        if urlsplit(self.path).path == "/marker.html":
            body = (b'<title>&#8203;</title><link rel="icon" '
                    b'href="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' '
                    b'viewBox=\'0 0 16 16\'%3E%3Cpath fill=\'magenta\' '
                    b'd=\'M0 0h16v16H0z\'/%3E%3C/svg%3E">')
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def log_message(self, *args):
        pass


def strip(browser, scale, vertical=False):
    pid = browser.capabilities["goog:processID"]
    wins = []

    def collect(hwnd, _):
        if (win32process.GetWindowThreadProcessId(hwnd)[1] == pid
                and win32gui.GetClassName(hwnd) == "Chrome_WidgetWin_1"
                and win32gui.IsWindowVisible(hwnd)):
            wins.append(hwnd)

    win32gui.EnumWindows(collect, None)
    assert len(wins) == 1, wins
    hwnd, = wins
    dc = win32gui.GetWindowDC(hwnd)
    src = win32ui.CreateDCFromHandle(dc)
    mem = src.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    size = (round(360 * scale), round((220 if vertical else 42) * scale))
    bitmap.CreateCompatibleBitmap(src, *size)
    old = mem.SelectObject(bitmap)
    try:
        paint = ctypes.windll.user32.PrintWindow
        paint.argtypes = (wintypes.HWND, wintypes.HDC, wintypes.UINT)
        assert paint(hwnd, mem.GetSafeHdc(), 2)  # PW_RENDERFULLCONTENT
        return Image.frombytes("RGB", size, bitmap.GetBitmapBits(True), "raw", "BGRX")
    finally:
        mem.SelectObject(old)
        mem.DeleteDC()
        win32gui.DeleteObject(bitmap.GetHandle())
        win32gui.ReleaseDC(hwnd, dc)


def measure(image, size):
    a = np.asarray(image)
    ys, xs = np.where((a == (255, 0, 255)).all(axis=2))
    if not len(xs):
        return None
    x, y = int(xs.min()), int(ys.min())
    assert (xs.max() - x + 1, ys.max() - y + 1) == (size, size), (np.ptp(xs), np.ptp(ys))
    row = a[y + size // 2]
    bg = tuple(map(int, row[x + size + 3]))
    on_tab = (row == bg).all(axis=1)
    left = x - 1
    while left > 0 and on_tab[left - 1]:
        left -= 1
    # The label is blank. Skip the X itself, then take the first frame pixel;
    # in light vertical tabs the frame can be narrower than the favicon slot.
    close_start = x + 2*size + int(np.flatnonzero(~on_tab[x+2*size:])[0])
    after = close_start + 3*size//4
    right = after + int(np.flatnonzero(~on_tab[after:])[0]) - 1
    # Mirror around the two measured tab edges, not the cropped screenshot's midpoint.
    other = left + right - (x + size - 1)
    box = (x, y, x + size, y + size)
    mirror_box = (other, y, other + size, y + size)
    return box, mirror_box, left, right, bg


def transparent(patch, bg):
    pixels = list(patch.convert("RGB").get_flattened_data())
    # The farthest actual ink sample is the fully covered foreground.
    fg = max(pixels, key=lambda p: sum((c - b)**2 for c, b in zip(p, bg)))
    assert max(abs(f - b) for b, f in zip(bg, fg)) > 90, (bg, fg)
    # Invert the two quantization steps used by Skia's premultiplied source-over.
    def color(alpha):
        return tuple((f * alpha + 127) // 255 + (b * (256 - alpha) >> 8)
                     for b, f in zip(bg, fg))
    palette = [color(a) for a in range(256)]
    def alpha_for(p):
        if p == bg:
            return 0
        if p == fg:
            return 255
        ideal = sum((c-b)*(f-b) for c,b,f in zip(p,bg,fg)) * 255 / sum((f-b)**2 for f,b in zip(fg,bg))
        return min(range(256), key=lambda a: (sum((r-c)**2 for r,c in zip(palette[a],p)), abs(a-ideal)))
    values = {p: fg + (alpha_for(p),) for p in set(pixels)}
    result = Image.new("RGBA", patch.size)
    result.putdata([values[p] for p in pixels])
    return result


def png_bytes(image):
    stream = BytesIO()
    image.save(stream, format="PNG", optimize=True)
    return stream.getvalue()


def write_ico(path, frames):
    # ICO can carry independent lossless PNGs; never resize the 1x raster.
    payload = [(size, png_bytes(image)) for size, image in sorted(frames.items())]
    header = struct.pack("<HHH", 0, 1, len(payload))
    offset = len(header) + len(payload) * 16
    for size, data in payload:
        header += struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    path.write_bytes(header + b"".join(data for _, data in payload))
    with Image.open(path) as ico:
        for size, expected in frames.items():
            assert ico.ico.getimage((size, size)).convert("RGBA").tobytes() == expected.tobytes()


def fractional_input(native, target, bg):
    """Precompensate Chromium's separable 32px -> device Lanczos3 favicon resize."""
    size, n = native.width, target.width
    scale = n / size
    x = np.arange(size)[None, :] + .5 - (np.arange(n)[:, None] + .5) / scale
    d = x * scale
    weights = np.where(abs(d) < 3, np.sinc(d) * np.sinc(d / 3), 0)
    weights = np.trunc(weights / weights.sum(1)[:, None] * 16384)
    middle = (np.maximum(0, np.floor((np.arange(n) + .5 - 3) / scale))
              + np.minimum(size-1, np.ceil((np.arange(n) + .5 + 3) / scale)) + 1) // 2
    weights[np.arange(n), middle.astype(int)] += 16384 - weights.sum(1)
    weights /= 16384
    # Black/white premultiplied ink has only one channel to filter. It leaves
    # headroom for sharp fully covered strokes without baking in a background.
    endpoint = 255 if bg < 128 else 0
    def coverage(image):
        a = np.asarray(image, dtype=int)[:,:,3]
        f = np.asarray(image, dtype=int)[:,:,0]
        observed = (f*a + 127)//255 + ((bg * (256-a)) >> 8)
        return (observed-bg) * (255 / (endpoint-bg))
    a, wanted = coverage(native), coverage(target)
    v = a.copy()
    # Projected accelerated least squares; respect the horizontal and vertical
    # saturation of Skia's two passes, including its integer truncation bias.
    for i in range(800):
        h = v @ weights.T
        m = weights @ np.clip(h-.5, 0, 255)
        error = np.clip(m-.5, 0, 255) - wanted
        grad = weights.T @ (error * ((m >= .5) | (error < 0)) * ((m <= 255.5) | (error > 0)))
        grad = (grad * ((h >= .5) | (grad < 0)) * ((h <= 255.5) | (grad > 0))) @ weights
        nxt = np.clip(v - grad, 0, 255)
        v, a = nxt + i/(i+3)*(nxt-a), nxt
    image = Image.new("RGBA", native.size, (endpoint,)*3)
    image.putalpha(Image.fromarray(a.round().astype(np.uint8)))
    return image


def capture(scheme, scale, local, page, build, vertical, out):
    options = webdriver.ChromeOptions()
    for flag in ("--window-size=800,450", "--window-position=-3000,-1800",
                 "--disable-backgrounding-occluded-windows", f"--force-device-scale-factor={scale}"):
        options.add_argument(flag)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("prefs", {"browser.theme.color_scheme2": 2 if scheme == "dark" else 1,
                                              "vertical_tabs.enabled": vertical, "vertical_tabs.uncollapsed_width": 200})
    with webdriver.Chrome(options=options) as browser:
        browser.get(local + "marker.html")
        n = round(16 * scale)
        until = time.monotonic() + 12
        while time.monotonic() < until:
            marker = strip(browser, scale, vertical)
            geometry = measure(marker, n)
            if geometry:
                break
            time.sleep(.12)
        else:
            raise AssertionError("No calibration favicon in the native tab strip")
        box, other, left, right, bg = geometry
        assert (box[1] > 42*scale) == vertical, ("unexpected tab orientation", box)
        native = marker.crop(other)
        assert (sum(bg) < 3 * 128) == (scheme == "dark"), (scheme, bg)
        key = f"{'vertical-' if vertical else ''}{scheme}-{n}"
        if n == 16:
            png = ASSETS / f"chrome-close-{scheme}.png"
            if build:
                transparent(native, bg).save(png, optimize=True)
            else:
                with Image.open(png) as stored:
                    rendered = Image.alpha_composite(Image.new("RGBA", native.size, (*bg,255)), stored)
                    assert np.max(np.asarray(ImageChops.difference(rendered.convert("RGB"), native))) <= 1
        if build:
            mask = transparent(native, bg)
            print(f"source {key}: tab={left}..{right} favicon={box[:2]} close={other[:2]} bg={bg}", flush=True)
            return mask.transpose(Image.Transpose.FLIP_LEFT_RIGHT), bg[0]

        browser.get(page)
        assert browser.execute_script("return document.title") == "\u200b"
        assert browser.execute_script("return matchMedia('(prefers-color-scheme: dark)').matches") == (scheme == "dark")
        browser.execute_async_script("document.fonts.ready.then(arguments[0])")
        time.sleep(.65)  # Chrome animates its loading spinner back into the favicon.
        until = time.monotonic() + 15
        expected = native.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        previous = None
        while time.monotonic() < until:
            image = strip(browser, scale, vertical)
            icon = image.crop(box)
            diff = np.asarray(ImageChops.difference(expected, icon)).max(axis=2)
            if np.mean(diff) < 12 and previous == icon.tobytes():
                break
            previous = icon.tobytes()
            time.sleep(.15)
        else:
            raise AssertionError(f"No stable favicon for {key}")
        assert image.crop(other).tobytes() == native.tobytes(), "Tab geometry or close button changed"
        assert np.mean(diff) < 12, (key, np.mean(diff))
        image.crop((left-2, max(0,box[1]-round(12*scale)), right+3, box[3]+round(12*scale))).save(
            out / f"septryon-tab-{key}.png")
        native_ink = np.max(np.abs(np.asarray(expected, dtype=float) - bg), axis=2)
        favicon_ink = np.max(np.abs(np.asarray(icon, dtype=float) - bg), axis=2)
        yy, xx = np.indices(native_ink.shape)
        delta = [float(np.average(axis, weights=favicon_ink)-np.average(axis, weights=native_ink)) for axis in (xx, yy)]
        print(f"{key}: differing pixels={np.count_nonzero(diff)}/{n*n}, max RGB error={diff.max()}, "
              f"mean={diff.mean():.3f}, centroid delta=({delta[0]:.3f}, {delta[1]:.3f}) px", flush=True)
        if n in (16, 32):
            assert not diff.any(), (key, diff.max())
        elif n in (20, 24, 28):
            assert max(map(abs, delta)) < (.15 if vertical else .02), (key, delta)
            assert diff.mean() < (4.5 if vertical else 1), (key, diff.mean())


def reference(filename, out, write):
    # Coordinates are pixel indices in the author's unscaled 199x40 PNG.
    path = ASSETS / "chrome-close-reference.png"
    if filename:
        with Image.open(filename) as original:
            assert original.size == (199, 40)
            proof = original.copy()
            sample = original.crop((173,12,189,28))
            assert original.getpixel((120,20)) == (25,25,25,255)
        if write:
            sample.save(path, optimize=True)
    else:
        with Image.open(path) as stored:
            sample = stored.convert("RGBA")
    assert sample.size == (16,16) and sample.getchannel("A").getextrema() == (255,255)
    raw = np.asarray(sample)[:,:,0]
    bg, fg = int(raw.min()), int(raw.max())
    alpha = np.rint((raw.astype(float)-bg)*255/(fg-bg)).astype(np.uint8)
    mirror = Image.new("RGBA", sample.size, (fg,fg,fg))
    mirror.putalpha(Image.fromarray(alpha))
    mirror = mirror.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    matte = Image.new("RGBA", sample.size, (bg,bg,bg,255))
    composite = Image.alpha_composite(matte, mirror)
    assert composite.tobytes() == sample.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes()
    target = ASSETS / "tab-reference.png"
    if write:
        mirror.save(target, optimize=True)
    else:
        with Image.open(target) as stored:
            assert stored.convert("RGBA").tobytes() == mirror.tobytes()
    if filename:
        proof.paste((bg,bg,bg,255), (10,11,31,29))
        proof.paste(composite, (12,12))
        proof.save(out / "septryon-reference-mirror.png")
    print("author reference: axis x=100, 256/256 mirrored pixels identical", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate multi-density site assets")
    parser.add_argument("--reference", type=Path, help="also extract the author's original attached PNG")
    parser.add_argument("--published", action="store_true")
    parser.add_argument("--vertical", action="store_true", help="test the expanded vertical tab strip")
    parser.add_argument("--out", type=Path, default=Path(gettempdir()) / "septryon-favicon-qa")
    parser.add_argument("--scales", type=float, nargs="+", default=SCALES)
    args = parser.parse_args()
    if args.write and (args.published or args.vertical or tuple(args.scales) != SCALES):
        parser.error("--write requires the complete local density set")
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    args.out.mkdir(exist_ok=True, parents=True)
    if args.write:
        ASSETS.mkdir(exist_ok=True)
    reference(args.reference, args.out, args.write)
    if args.published:
        for asset in sorted(ASSETS.iterdir()):
            if asset.suffix in (".ico", ".png"):
                with urlopen(PUBLIC + "icons/" + asset.name, timeout=15) as response:
                    assert response.read() == asset.read_bytes(), asset.name
    with ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=SITE)) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        local = f"http://127.0.0.1:{server.server_port}/"
        try:
            for theme in ("dark", "light"):
                frames = {}
                for scale in args.scales:
                    frames[round(16*scale)] = capture(theme, scale, local, PUBLIC if args.published else local,
                                                      args.write, args.vertical, args.out)
                if args.write:
                    bg = frames[16][1]
                    assert all(color == bg for _, color in frames.values())
                    frames = {n: image for n, (image, _) in frames.items()}
                    write_ico(ASSETS / f"tab-{theme}.ico", frames)
                    for n in (20, 24, 28):
                        source = fractional_input(frames[32], frames[n], bg)
                        write_ico(ASSETS / f"tab-{theme}-{n*100//16}.ico", {**frames, 32: source})
        finally:
            server.shutdown()
            thread.join()


if __name__ == "__main__":
    main()
