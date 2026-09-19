# Tokyo master assets

The production pair is bundled under `media/tokyo/` and is loaded only when
the page uses `?tokyo=1`. The ordinary Wallpaper and Launcher defaults remain
unchanged.

| Role | File | SHA-256 |
| --- | --- | --- |
| Reality A | `media/tokyo/reality-wikipedia.png` | `FC096FABE3C1A822F41B977119EFA3E460F8E69952D5C60D0940E24B6C564EBD` |
| RedBlack B | `media/tokyo/redblack-wikipedia.png` | `066CFAB3A18BA61B2EC0531C5F044514E236CEF7B3182A5FDAB96C28C2C28C6A` |

Both files are 2670×1878. The user supplied the source imagery and stated that
it originated from Wikipedia. This repository records that assertion; it does
not claim an independently reconstructed upstream URL or license chain.

## PixelLock decision

- Reality A is the immutable geometry and screen-projection authority.
- The selected B candidate is `T0B_final/B_open_2670x1878.png`. Its tower/spire
  anchor differs by approximately 1 px horizontally and 1 px vertically from
  A, within the 4 px production gate.
- Pixel-mask IoU and color/style checks differ substantially because B is an
  intentional global red/black grade. Those differences are not interpreted
  as geometry drift.
- `Tokyo_Tower_RedBlack_Final_2670x1878.png` was rejected: the measured tower
  anchor shift was approximately 108 px.

No generated image is allowed to replace or redraw the Duo shell, hinge,
panels, cameras, fold angle, or Screen UV.
