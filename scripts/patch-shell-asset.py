"""Bake the reviewed device-control seating into iPhone_Duo_Render.usdc.

Official render alignment, baked once so runtime carries zero offsets:
- The upper right-rail key keeps the restrained +0.04x offset.
- The lower right-rail key returns flush to the official rail (0.00x).
- The two top caps keep the Apple-authored 0.00y height so both read clearly
  above the rail on one aligned baseline.
- Hinge seam tabs stay stock (flush) — v6.11 runtime protrusion reverted.

three.js USDComposer only honors the DEFAULT op name `xformOp:translate`
(custom-suffixed ops are skipped), so the translate is written as the default
op. Idempotent: an existing default translate with our value is left alone;
legacy `xformOp:translate:shellKey` entries are cleaned up.

Run after scripts/prepare-assets.py:
  uv run --no-project --python 3.12 --with usd-core python scripts/patch-shell-asset.py
"""
from pathlib import Path

from pxr import Usd, UsdGeom, Gf, Sdf

ASSET = Path(__file__).resolve().parents[1] / "assets" / "iPhone_Duo_Render.usdc"

# Right-rail key clusters: upper (main cap + its two side-wall/detail slices)
# and lower — onmyduo (same Apple USDZ) shows TWO keys on the right rail.
UPPER_KEY = ("UXtkILReLwCJaov", "fbvEqfwjsAMSDkr", "tkSBzAjLTdhANqx")
LOWER_KEY = ("AjfIgUpXxKaENDl", "VNIQJMrwFmXgrBf", "ejUvJHtjfcqjSvM")
TOP_KEY = ("YhaSRqOjDUQrQTc", "FcJBPLgEScWGyXd")
TARGET_TRANSLATIONS = {
    **{name: Gf.Vec3d(0.04, 0.0, 0.0) for name in UPPER_KEY},
    **{name: Gf.Vec3d(0.0, 0.0, 0.0) for name in LOWER_KEY},
    **{name: Gf.Vec3d(0.0, 0.0, 0.0) for name in TOP_KEY},
}
LEGACY_OP = "xformOp:translate:shellKey"


def main():
    stage = Usd.Stage.Open(str(ASSET))
    moved = skipped = cleaned = missing = 0
    by_name = {p.GetName(): p for p in stage.Traverse()}
    for name, target in TARGET_TRANSLATIONS.items():
        prim = by_name.get(name)
        if prim is None:
            print(f"MISSING {name}")
            missing += 1
            continue
        xf = UsdGeom.Xformable(prim)

        # Drop legacy custom-suffixed op (ignored by three.js loader).
        order_attr = prim.GetAttribute("xformOpOrder")
        order = list(order_attr.Get() or [])
        if LEGACY_OP in order:
            order.remove(LEGACY_OP)
            order_attr.Set(order)
            prim.RemoveProperty(LEGACY_OP)
            cleaned += 1

        ops = {op.GetOpName(): op for op in xf.GetOrderedXformOps()}
        op = ops.get("xformOp:translate")
        if op is not None:
            v = op.Get()
            if v and all(abs(v[index] - target[index]) < 1e-9 for index in range(3)):
                skipped += 1
                continue
            op.Set(target)
            moved += 1
            continue
        op = xf.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble)  # default: xformOp:translate
        op.Set(target)
        moved += 1
    stage.GetRootLayer().Save()
    print(f"baked: moved={moved} already={skipped} legacy_cleaned={cleaned} missing={missing} -> {ASSET.name}")


main()
