# 小 E 探索者收藏卡 v02：完整提示词

生成方式：内置 image_gen，图像编辑 / 风格调整。用户要求更清新的配色，并降低脏乱感。旧版保存在 `../explorer-card-v01/`，新版独立保存，不覆盖旧版。工具实际交付两张 1027×1532 px RGB 图像；按 61×91 mm 放置约 427.6 ppi，未插值放大。

## 正面配色与质感调整

编辑目标：`../explorer-card-v01/xiao-e-explorer-front.png`。

```text
Use case: style-transfer.
Edit the attached FRONT of the Xiao E explorer collectible card. The user finds the current dark, speckled art visually dirty and wants a much fresher, lighter palette. Rebuild its color and surface treatment into a bright, clean, airy comic illustration. This is a major palette-and-background simplification, not a brightness filter.

KEEP: the same friendly Xiao E mascot and forward-leaping pose, large rounded off-white helmet, dark blue-black visor with two turquoise inward chevron graphic eyes and no mouth, circular ring ears, one short rounded turquoise crest, white suit, four-point outlined teal chest insignia, short white cape with teal rim, exactly two arms and two legs, one foreshortened hand toward the viewer. Keep the entire character comfortably inside x=12%-88%, y=12%-85% of the canvas. Preserve its established proportions and recognizable face.

NEW ART DIRECTION:
- Beautiful fresh palette: creamy white #FFFDF5, pale mint #DCF4E9, soft sky blue #C5E5F7, clear turquoise #42BCAF, with just a little buttery yellow #F4DB83 and pale peach #F3BDAA.
- About TWO THIRDS of the canvas should read as light cream or very pale mint/sky, with lots of uninterrupted clean breathing room. Restrict very dark color to the face visor, boots and fine contour lines. No large navy background at all.
- Clean graphic 2D comic art, confident medium-weight deep-teal contour lines, simple two-tone cel shading, solid smooth color fills. Not a 3D render, not a glossy plastic toy photograph. Allow at most two tiny orderly halftone patches in pale blue, never across the face or white suit.
- Drastically simplify the space backdrop: only two small smooth pastel planets, one or two thin elegant orbit curves, a few well-spaced four-point sparkles, and two broad pale diagonal color areas suggesting flight. Use a simple pale curved planet horizon in the lower corner. No galaxy dust or star confetti, no asteroid debris, no black splatter, no scratched ink, no mottling, no dense radial bursts, no yellow/red racing stripes.
- Keep dynamism in the reaching hand and cape silhouette, balanced with generous open space. The character must be the clear focal point, with white helmet cleanly separated from a pale sky-blue area behind it. Refreshing, friendly, collectible stationery quality.

OUTPUT: One independent upright FRONT artwork, high resolution portrait, EXACT 61:91 aspect ratio, ideally 1952x2912 pixels. The rectangular canvas is 61x91mm including 3mm bleed per edge for a 55x85mm finished card. Background color extends to every edge. Every key character detail stays at least 6mm from canvas edges. No visible frame, cut line, tabletop, card mockup, perspective card, shadows outside card or rounded transparency.
ABSOLUTELY NO TEXT, no numbers, no letters, no pseudo-text, brand wordmark, speech bubbles, labels, blank form fields, watermarks, signatures, QR/barcodes or redemption codes. Only the existing graphical chevron eyes and four-point star insignia are allowed.
```

最终原文件：`C:/Users/BX/.codex/generated_images/01a12f92-a87a-75e3-864b-c0d2946b2c7f/exec-ad371d2c-baf4-4ae1-bd6d-f81ce535d4a8.png`。

## 背面配色与质感调整

编辑目标：`../explorer-card-v01/xiao-e-explorer-back.png`；色彩与画风参考：已完成的 v02 正面。

```text
Use case: style-transfer.
Edit the BACK illustration of the Xiao E explorer collectible card into the same fresh palette and clean drawing treatment as the new front.
Image 1 is the OLD BACK, the edit target: keep its rear-view Xiao E character, lower-foreground position, standing pose and four-point portal narrative.
Image 2 is the NEW FRONT: this is the strict color, line and surface-style reference for the new back. Match its creamy whites, mint, light sky-blue, delicate peach and buttery yellow, clean surfaces and uncluttered atmosphere.

Preserve the established identity of Xiao E: off-white oversized rounded helmet with smooth rear shell (no face on the back), one short rounded turquoise crest, white circular ears with turquoise rings, two short arms, two short legs, charcoal boots, short white cape with a turquoise edge and ONE large outlined turquoise four-point compass star centered on the back. Keep the full character at approximately x=28%-72%, y=48%-85%, with all parts safely inside the artwork.

Composition: rear-view Xiao E stands on a small gently curved mint/sky-blue planet at the bottom and gazes toward a single large, elegantly drawn FOUR-POINT STAR portal in the upper-middle. The star is creamy white with a soft butter-yellow inner accent and a crisp turquoise outline, readable against the light sky-blue area behind it. Keep the whole portal including its tips INSIDE x=20%-80%, y=13%-40%; leave a clean open gap between the portal and the mascot crest. It is a graphic star doorway, no explosive speckled energy and no dark hole. Two fine orbital curves and only two small pastel planets accompany it. A few widely spaced simple four-point sparkles are enough.

Art direction: bright, airy, clean modern comic illustration with smooth pale color fields, medium-weight deep-teal contours around the mascot, simple cel-shaded highlights matching the new front. Creamy white #FFFDF5, pale mint #DCF4E9, light sky-blue #C5E5F7, clear turquoise #42BCAF, very restrained butter yellow #F4DB83 and pale peach #F3BDAA. Most of the artwork is LIGHT, with generous uninterrupted areas and breathing room. Dark color only on boots, joints and thin contours. Background has one or two broad pale flowing/diagonal color areas, not busy fragments. Two small orderly pale halftone patches at most. The foreground planet has large, smooth abstract mint shapes; it is NOT cratered, dirty or speckled.
Remove the old navy galaxy background, all grunge, distressed ink, black speckles, dense tiny stars, asteroid shards, crosshatching, harsh saturated red and yellow rays. Make the white helmet and cape look clean and fresh. No photorealism, no 3D toy render.

Print output: one independent upright portrait BACK image, EXACT 61:91 aspect ratio, preferably high resolution 1952x2912. Canvas 61x91mm includes 3mm bleed around a finished 55x85mm card. Pale background fills edge-to-edge. Critical mascot features and star portal are at least 6mm from outer canvas edges. Flat opaque rectangular illustration, square corners, no border, no card mockup, no table, no crop or safety guides, no transparent corners.
Absolutely no text, letters, numbers, pseudo-writing, logo wordmarks, sound effects, captions, labels, QR codes, barcodes, blank information fields, watermarks or signatures. Pure illustration.
```

调整前原文件：`C:/Users/BX/.codex/generated_images/01a12f92-a87a-75e3-864b-c0d2946b2c7f/exec-313b81a1-1189-4f9f-b555-a15c52e750e3.png`。

## 背面星门留白调整（最终版）

```text
Use case: precise-object-edit.
Make one small composition refinement to this clean pastel Xiao E BACK card: uniformly shrink ONLY the large central four-point star portal to 80% of its current size, keeping the portal's center around x=50%, y=26% of the canvas. Its top and bottom points must end around y=12% and y=40%, respectively. Create a clearly visible gap of light blue background, at least 4% of the total image height, between the portal's bottom tip and Xiao E's turquoise crest. The portal must not touch the crest, appear attached to the helmet, or resemble an antenna. Smoothly fill the locally revealed area with the same clean pale sky-blue background. Keep the four-point shape, cream center, butter-yellow band and turquoise outline. Keep the whole portal prominent.

Everything else must be unchanged: exact Xiao E rear identity, pose and size; white helmet, ears, turquoise crest, white cape with turquoise border and outlined four-point star; two arms and two boots; planet and orbit composition; clean light palette, fresh cream/mint/sky-blue colors, sparse dots and stars; full-bleed square-cornered portrait canvas. No additional visual elements. Absolutely no text, no letters or numbers, no codes, signatures, watermark, frame or crop marks.
Keep EXACT 61:91 aspect ratio and original high image quality. Physical print canvas 61x91mm, 55x85mm finished trim, 3mm bleed each side. All critical character and portal details at least 6mm from the canvas edges.
```

最终原文件：`C:/Users/BX/.codex/generated_images/01a12f92-a87a-75e3-864b-c0d2946b2c7f/exec-4241f65b-608c-4188-afa3-fc511d07762e.png`。

