#!/usr/bin/env python3
"""
Black Hole (stage 1): procedural generator for animated textures.

  python3 generate_textures.py [output_dir] [--preview preview.png]

Creates in output_dir (default: src/main/resources/assets/blackhole/textures/item):
  ring_a / ring_b / ring_c  (+ .png.mcmeta)  - animated accretion rings, 128x128 x 48 frames
  black_hole_icon           (+ .png.mcmeta)  - animated 32x32 inventory icon
  black_hole_core.png                        - black core

Every ring is a spiral pattern with m-fold symmetry that is rotated through
2*pi/m over 48 frames, so the loop is seamless. Different m values give
different rotation speeds, and `reverse` flips the direction.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

S = 128          # ring texture size (px)
FRAMES = 48      # frames in every animation (1 frame = 1 game tick)
SS = 2           # supersampling for anti-aliasing
ICON = 32        # inventory icon size

# ---------------------------------------------------------------- ring specs
RINGS = {
    # Model geometry (in model px, 16 = 1 block): radius, tilt axis and angle.
    "ring_a": dict(
        radius=8.0, axis=None, tilt=0, r_in=0.625, m=4, reverse=False, seed=3,
        spiral=5.0, a_lo=-0.55, a_hi=0.85, floor=0.22, decay=2.1, gain=1.55,
        fil=7.0, gamma=0.85, gaps=[(0.43, 0.030), (0.72, 0.022)], dash=None,
        palette=[(0.00, (14, 0, 22)), (0.18, (110, 14, 10)), (0.42, (235, 78, 8)),
                 (0.68, (255, 168, 40)), (0.88, (255, 232, 168)), (1.00, (255, 255, 255))]),
    "ring_b": dict(
        radius=7.0, axis="x", tilt=45, r_in=0.70, m=6, reverse=True, seed=11,
        spiral=-4.0, a_lo=-0.45, a_hi=0.80, floor=0.18, decay=1.5, gain=1.5,
        fil=5.0, gamma=0.9, gaps=[(0.52, 0.035)], dash=None,
        palette=[(0.00, (6, 0, 26)), (0.25, (62, 10, 128)), (0.50, (150, 40, 224)),
                 (0.76, (222, 120, 255)), (1.00, (255, 236, 255))]),
    "ring_c": dict(
        radius=6.2, axis="z", tilt=-45, r_in=0.80, m=3, reverse=False, seed=23,
        spiral=3.0, a_lo=-0.20, a_hi=0.75, floor=0.55, decay=0.5, gain=1.6,
        fil=3.0, gamma=0.8, gaps=[], dash=(0.10, 0.45),
        palette=[(0.00, (0, 10, 34)), (0.30, (0, 62, 146)), (0.60, (40, 172, 255)),
                 (0.85, (172, 236, 255)), (1.00, (255, 255, 255))]),
}
CORE_R = 3.9     # radius of the black core in model px (for the preview/icon)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def colormap(x, stops):
    xs = [s[0] for s in stops]
    cols = np.array([s[1] for s in stops], dtype=np.float32)
    out = np.empty(x.shape + (3,), dtype=np.float32)
    for c in range(3):
        out[..., c] = np.interp(x, xs, cols[:, c])
    return out


def ring_frames(spec):
    """Returns a list of FRAMES uint8 RGBA arrays (S, S, 4)."""
    n = S * SS
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float32)
    u = (xs + 0.5 - n / 2) / (n / 2)
    v = (ys + 0.5 - n / 2) / (n / 2)
    r = np.hypot(u, v)
    th = np.arctan2(v, u)
    t = (r - spec["r_in"]) / (1.0 - spec["r_in"])
    inside = ((t > 0) & (t < 1)).astype(np.float32)
    tc = np.clip(t, 0, 1)

    rng = np.random.default_rng(spec["seed"])
    nh = 6
    amps = np.array([1.0 / (j ** 0.85) for j in range(1, nh + 1)], dtype=np.float32)
    amps /= amps.sum()
    phs = rng.uniform(0, 2 * math.pi, nh)

    m = spec["m"]
    sign = -1.0 if spec["reverse"] else 1.0
    base = np.exp(-spec["decay"] * tc)

    mask0 = smoothstep(0.0, 0.025, t) * (1.0 - smoothstep(0.955, 1.0, t))
    for c, w in spec["gaps"]:
        mask0 = mask0 * (1.0 - np.exp(-(((t - c) / w) ** 4)))
    mask0 = mask0 * inside

    frames = []
    for k in range(FRAMES):
        phi = sign * (k / FRAMES) * (2 * math.pi / m)
        arg = m * (th - phi) + spec["spiral"] * tc
        ang = sum(amps[j - 1] * np.sin(j * arg + phs[j - 1]) for j in range(1, nh + 1))
        ang01 = smoothstep(spec["a_lo"], spec["a_hi"], ang)
        fil = 0.72 + 0.28 * np.sin(2 * math.pi * spec["fil"] * tc + 1.6 * np.sin(arg + 0.7))
        inten = (spec["floor"] + (1 - spec["floor"]) * ang01) * base * fil * spec["gain"]
        inten = np.clip(inten, 0, 1) ** spec["gamma"]
        rgb = colormap(inten, spec["palette"])
        alpha = mask0
        if spec["dash"]:
            alpha = alpha * smoothstep(spec["dash"][0], spec["dash"][1], ang01)
        # downsample with premultiplied alpha
        pre = rgb * alpha[..., None]
        pre = pre.reshape(S, SS, S, SS, 3).mean(axis=(1, 3))
        a = alpha.reshape(S, SS, S, SS).mean(axis=(1, 3))
        col = np.where(a[..., None] > 1e-4, pre / np.maximum(a[..., None], 1e-4),
                       np.array(spec["palette"][1][1], dtype=np.float32))
        out = np.dstack([np.clip(col, 0, 255), np.clip(a, 0, 1) * 255]).astype(np.uint8)
        frames.append(out)
    return frames


# ------------------------------------------------------------ mini renderer
def rot(axis, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float64)
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float64)
    if axis == "z":
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float64)
    return np.eye(3)


def render(ring_data, k, size, yaw, pitch, half=10.5, ss=3, halo=False):
    """Orthographic render of the 3-ring model (approximation of the in-game model)."""
    n = size * ss
    cam = rot("y", yaw) @ rot("x", -pitch)
    idx = (np.arange(n) + 0.5) / n * 2 * half - half
    px, py = np.meshgrid(idx, -idx)
    cam_pts = np.stack([px, py, np.full_like(px, 40.0)], axis=-1)
    origin = cam_pts @ cam.T
    d = cam @ np.array([0, 0, -1.0])

    best = np.full((n, n), np.inf)
    color = np.zeros((n, n, 3), dtype=np.float32)
    covered = np.zeros((n, n), dtype=bool)

    def put(s, valid, col):
        nonlocal best, color, covered
        better = valid & (s < best)
        best = np.where(better, s, best)
        color = np.where(better[..., None], col, color)
        covered = covered | better

    # photon halo (icon only): thin bright annulus facing the camera
    if halo:
        s = -(origin @ d) / (d @ d)
        p = origin + s[..., None] * d
        rr = np.sqrt((p ** 2).sum(-1))
        ring = (rr > CORE_R + 0.15) & (rr < CORE_R + 0.95)
        glow = 1.0 - (rr - CORE_R - 0.15) / 0.8
        col = np.stack([255 * np.clip(glow, 0.25, 1), 205 * np.clip(glow, 0.25, 1),
                        150 * np.clip(glow, 0.25, 1)], axis=-1)
        put(s, ring, col)

    # core sphere
    b = origin @ d
    c = (origin ** 2).sum(-1) - CORE_R ** 2
    disc = b * b - c
    hit = disc >= 0
    s = np.where(hit, -b - np.sqrt(np.maximum(disc, 0)), np.inf)
    put(s, hit, np.array([3, 2, 6], dtype=np.float32))

    # rings
    for name, spec in RINGS.items():
        rd = rot(spec["axis"], spec["tilt"])
        nrm = rd @ np.array([0, 1.0, 0])
        denom = nrm @ d
        if abs(denom) < 1e-6:
            continue
        s = -(origin @ nrm) / denom
        p = origin + s[..., None] * d
        loc = p @ rd              # = Rd^T p
        rr = spec["radius"]
        uu = (loc[..., 0] / rr + 1) / 2
        vv = (loc[..., 2] / rr + 1) / 2
        ok = (uu >= 0) & (uu < 1) & (vv >= 0) & (vv < 1)
        iu = np.clip((uu * S).astype(int), 0, S - 1)
        iv = np.clip((vv * S).astype(int), 0, S - 1)
        tex = ring_data[name][k % FRAMES][iv, iu]
        valid = ok & (tex[..., 3] >= 128)
        put(s, valid, tex[..., :3].astype(np.float32))

    rgba = np.dstack([color * covered[..., None], covered * 255.0])
    pre = rgba.copy()
    pre[..., :3] = rgba[..., :3] * (rgba[..., 3:4] / 255.0)
    pre = pre.reshape(size, ss, size, ss, 4).mean(axis=(1, 3))
    a = pre[..., 3:4]
    rgb = np.where(a > 0.5, pre[..., :3] / np.maximum(a / 255.0, 1e-4), 0)
    return np.dstack([np.clip(rgb, 0, 255), a]).astype(np.uint8)


def over(bg_rgb, rgba):
    a = rgba[..., 3:4].astype(np.float32) / 255.0
    return (rgba[..., :3] * a + np.array(bg_rgb, dtype=np.float32) * (1 - a)).astype(np.uint8)


# --------------------------------------------------------------------- main
def save_anim(path, frames, frametime=1, interpolate=False):
    stack = np.concatenate(frames, axis=0)
    Image.fromarray(stack, "RGBA").save(path, optimize=True)
    with open(path + ".mcmeta", "w") as f:
        json.dump({"animation": {"interpolate": interpolate, "frametime": frametime}}, f, indent=2)


def main():
    args = [a for a in sys.argv[1:]]
    preview = None
    if "--preview" in args:
        i = args.index("--preview")
        preview = args[i + 1]
        del args[i:i + 2]
    out = args[0] if args else "src/main/resources/assets/blackhole/textures/item"
    os.makedirs(out, exist_ok=True)

    ring_data = {}
    for name, spec in RINGS.items():
        print("ring", name)
        ring_data[name] = ring_frames(spec)
        save_anim(os.path.join(out, name + ".png"), ring_data[name])

    print("icon")
    icon_frames = [render(ring_data, k, ICON, yaw=22, pitch=36, half=10.2, ss=6, halo=True)
                   for k in range(FRAMES)]
    save_anim(os.path.join(out, "black_hole_icon.png"), icon_frames)

    rng = np.random.default_rng(5)
    core = np.zeros((16, 16, 4), dtype=np.uint8)
    core[..., 0] = rng.integers(2, 9, (16, 16))
    core[..., 1] = rng.integers(1, 6, (16, 16))
    core[..., 2] = rng.integers(4, 14, (16, 16))
    core[..., 3] = 255
    Image.fromarray(core, "RGBA").save(os.path.join(out, "black_hole_core.png"))

    if preview:
        bg = (14, 16, 26)
        views = [(30, 24), (110, 52), (-35, 8)]
        W = 360
        sheet = np.zeros((W * 2 + 150, W * 3, 3), dtype=np.uint8)
        sheet[:] = bg
        for i, (yw, pt) in enumerate(views):
            img = render(ring_data, 0, W, yw, pt, half=10.5, ss=3)
            sheet[0:W, i * W:(i + 1) * W] = over(bg, img)
        for i, k in enumerate([0, 12, 24]):
            img = render(ring_data, k, W, 30, 24, half=10.5, ss=3)
            sheet[W:2 * W, i * W:(i + 1) * W] = over(bg, img)
        # first frame of each texture + icon (x4)
        x = 10
        for name in RINGS:
            t = over((40, 40, 48), ring_data[name][0])
            sheet[2 * W + 10:2 * W + 10 + S, x:x + S] = t
            x += S + 10
        ic = over((60, 60, 70), icon_frames[0])
        ic = np.kron(ic, np.ones((4, 4, 1), dtype=np.uint8))
        sheet[2 * W + 10:2 * W + 10 + 128, x:x + 128] = ic
        Image.fromarray(sheet, "RGB").save(preview)
        print("preview", preview)


if __name__ == "__main__":
    main()
