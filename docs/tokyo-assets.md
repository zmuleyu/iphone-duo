# Tokyo asset authority

Tokyo V6.28 uses one fixed-camera 16:9 composition. The files below are the only current runtime image assets; earlier candidates and review-only images are retained in Git history, not in the current tree.

## Base pair

| Role | File | SHA-256 |
| --- | --- | --- |
| Original Reality reference | `media/tokyo/reality-wikipedia.png` | `FC096FABE3C1A822F41B977119EFA3E460F8E69952D5C60D0940E24B6C564EBD` |
| Original RedBlack reference | `media/tokyo/redblack-wikipedia.png` | `066CFAB3A18BA61B2EC0531C5F044514E236CEF7B3182A5FDAB96C28C2C28C6A` |

Both images are 2670×1878. The user supplied them and stated that the source imagery originated from Wikipedia. This repository records that assertion but does not claim an independently reconstructed upstream URL or license chain.

## V6.28 runtime plates

| Role | File | SHA-256 |
| --- | --- | --- |
| Clean Reality plate | `media/tokyo/candidates/reality-v6.22-clean-tower.png` | `59E85B1DB60C7134E1658541E87C0A5555E23A4A4DD98C4D0B59A9F0649751CC` |
| RedBlack weak state | `media/tokyo/candidates/redblack-v6.23-weak.png` | `42375D91E55321E9D01455BFB05FF99A58D75DCB6309A31F847F4CE97D23B786` |
| RedBlack strong state | `media/tokyo/candidates/redblack-v6.23-strong.png` | `C2FB37C7C410F45F8DA0E9B0ABB336196F9087F8EC175CA8255F5BAAC89842B1` |
| Geometry mask | `media/tokyo/candidates/layers-v6.22-mask.png` | `79DB5C068F33FFBEB6A30C0407BF25AF74ED2828210E7878B2C4D5C9B98A0B60` |
| Gold tower plate | `media/tokyo/candidates/tower-v6.22-gold-rgba.png` | `4D88DBEF13EC4C930F575BB224D2C79E20F6756D69F500E821F573B0F75C1EFA` |

## Geometry and device boundary

- Reality remains the geometry and screen-projection authority.
- The accepted RedBlack and tower plates change style and lighting without redefining the Tokyo Tower or skyline geometry.
- No generated image may replace or redraw the Duo shell, hinge, panels, cameras, fold angle, camera, Screen UV, or occlusion behavior.
- The Apple-derived device model is prepared locally, ignored by Git, and outside the repository's MIT license.
