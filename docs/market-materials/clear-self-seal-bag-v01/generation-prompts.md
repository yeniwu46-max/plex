# 小 E 透明自粘包装袋：完整生成提示词

生成方式：内置 image_gen。图案使用真正透明背景；产品效果图使用浅灰摄影背景。两者分别交付，不把效果图当作印刷图。

## 透明贴纸图案

参考：`../explorer-card-v02/xiao-e-explorer-front.png`。

```text
Use case: illustration-story / identity-preserving packaging artwork.
Create a very minimal, elegant horizontal decorative print strip for a transparent self-adhesive collectible-card bag. This is the ACTUAL FLAT ARTWORK to print onto a clear label, NOT a bag photograph or mockup. Exact aspect ratio 3:1, ideally 3072x1024 pixels, intended physical label size 60x20 mm. Output a genuine transparent alpha background.

Reference image: the approved Xiao E collector card. Extract and preserve its mascot identity and clean fresh comic illustration style, but simplify drastically for a tiny clear packaging label. Match its creamy white, mint, sky blue, turquoise and restrained butter yellow; use neat deep teal ink outlines.

Composition within the transparent 3:1 rectangle:
- On the left quarter, one tiny friendly Xiao E bust (helmet, shoulders and two mitten hands only), peeking playfully above a single thin swooping turquoise orbit line. The mascot occupies approximately x=8%-30%, y=12%-88%. The head is off-white with a rounded shape, dark navy rounded visor, two cyan inward-pointing chevron-shaped graphic eyes, no mouth, circular ring ear modules, and one small rounded turquoise crest. Preserve this exact identity from the reference. Small clean cel-shaded shapes, no extra fingers, no other character. The white helmet must be OPAQUE CREAM; transparency is for the negative space outside the artwork, not holes within the helmet.
- A thin, graceful turquoise orbit line sweeps from beneath the little mascot across the lower third to the right; it must stay airy, not form a box or solid band.
- At the right, ONE medium four-point compass star with turquoise outline and cream center at about x=84%, y=55%, accompanied by one tiny butter-yellow sparkle. The star is simple and refined.
- Most of the strip is completely empty and TRANSPARENT. About 80% or more should remain clear. No other planets, no full background, no busy decorative elements. Do not fill the rectangle with white, cream, pastel or any other color. No visible strip boundary and no printed checkerboard.

Style: clean light comic drawing matching the attached card; confident medium-weight teal contours, very limited simple color fills, small charming mascot. No grunge, no distress, no speckles, no halftone texture, no dense stars, no glow, no gradients fading into a fake background, no shadows, no 3D or photography.
ABSOLUTELY NO TEXT OR LETTERS OR NUMBERS, no brand wordmark, no labels, no caption, no information fields, no QR/barcode, no watermark, no signature. The graphical chevron eyes and four-point insignia are allowed.
All printed shapes must be at least 2 mm from the label perimeter (x about 4%-96%, y about 10%-90%). Edges of the art remain crisp. Output exactly one horizontal transparent-background artwork rectangle, not a sheet of multiple designs.
```

原文件：`C:/Users/BX/.codex/generated_images/01a12f92-a87a-75e3-864b-c0d2946b2c7f/exec-9dedf8ab-5c03-4858-87a2-ee9d3d02337c.png`。

## 空袋与装卡效果图

参考 1：透明贴纸图案；参考 2：已确认的收藏卡 v02 正面。

```text
Use case: product-mockup.
Create a refined product-design visualization of a SIMPLE CLEAR SELF-ADHESIVE FLAP BAG for the Xiao E explorer collectible card. Show TWO bags side-by-side on one quiet pale warm-gray studio background: an EMPTY bag on the left with its clear adhesive flap open at the top, and a matching bag on the right containing the approved card with the flap folded onto the back. Both bag body bottoms align. Wide landscape composition, calm catalog lighting, subtle contact shadows, no extra props, no hands.

Reference image 1: the FINAL clear-label artwork, consisting of one tiny cream/teal Xiao E bust at left, a thin turquoise orbital curve and a four-point star at right, on a transparent background. Apply THIS graphic as a small clear label close to the bottom of BOTH bags, matching the original artwork. Do not repeat the mascot elsewhere on the bag. Clear label has no white rectangular base and should almost disappear around the colored artwork.
Reference image 2: the EXACT approved front collectible card artwork. The card inside the right bag must show this clean light-blue/mint Xiao E design, without adding typography or reinventing its illustration. It is an insert, NOT ink printed across the plastic.

Structure/proportions:
- Thin, flexible crystal-clear glossy polypropylene/OPP sleeve bag, portrait body 70mm wide x 110mm tall, an additional 30mm clear adhesive closure flap on the EMPTY bag. No zipper, no ziplock tracks, no drawstring, no handles, no hanging hole, no cardboard header, no gusset, no standing base. Straight small heat-sealed side and bottom seams.
- Very clear film with just a few fine edge reflections and gentle realistic creases near the seams. The studio background should be clearly visible through the EMPTY left bag. It must not look milky, frosted, tinted, rigid, glass, or opaque.
- The 60x20mm transparent decorative label sits 5mm from both side edges, 3mm above the bottom edge; the small mascot and star artwork lies within its bottom strip. Most of each bag is unprinted and transparent. The pale cream color exists ONLY inside the mascot/star artwork. Do not invent any overall pastel background for the bag itself.
- The right bag contains a single 55x85mm card, horizontally centered and about 5mm below the top of the bag body. Keep the card's main art entirely visible and recognizable; the tiny bag decoration lives in the clear space below the card, not over its face or main graphic.
- Keep the empty-left bag and filled-right bag at identical body scale, front-facing with very little perspective. Right bag may have slight realistic film reflections but never obscure the illustration.

Aesthetic: fresh mint, pale sky-blue and cream artwork, sparse graceful detailing, thoughtful affordable stationery packaging. The bag decoration should feel minimal and restrained. The hero is the transparent viewing area and the card inside, not a busy printed wrapper.
ABSOLUTELY no text, no lettering, no dimensions printed in image, no numbered labels, no logo wordmarks, no QR code or barcode, no watermark or signatures. No additional patterns, no repeated border stars, no large opaque lower band. The alpha transparency in the referenced label is clear film, never a black background or a printed checkerboard.
Output one high-resolution landscape design mockup, with both whole bags fully visible and generous air around them.
```

## 保持收藏卡直角裁切

```text
Use case: precise-object-edit.
Make ONLY one correction in this packaging visualization: the collectible card INSIDE THE RIGHT BAG must have clean SQUARE 90-DEGREE CORNERS, not rounded corners. The physical card was specified as a straight-cut rectangular 55x85mm card. Extend the card's existing pale sky-blue/mint artwork into its four small rounded corner gaps to make sharp rectangular corners. Do not round or redraw the card.

Preserve everything else exactly: both transparent peel-and-seal bags, open flap on the empty left bag, folded flap on the right, the tiny printed Xiao E and orbital line and four-point star at the bag bottoms, positions, lighting, pale warm-gray studio surface, film creases, and the existing artwork on the card. Do not add any labels, typography, dimensions, new images, borders, codes or watermarks. One photorealistic packaging concept image, same landscape composition.
```

最终效果图原文件：`C:/Users/BX/.codex/generated_images/01a12f92-a87a-75e3-864b-c0d2946b2c7f/exec-b6408470-b73e-40c5-a41d-dbb5483154ae.png`。

## 输出实测

- 图案：2172×724 px，RGBA，3:1；60×20 mm 使用时约 919 ppi。
- 图案 alpha 范围 0–255，约 87.8% 像素完全透明，不是白底或棋盘格假透明。
- 效果图：1536×1024 px，用于看包装外观；AI 产品示意图不作为精确的袋型工程图。
- 原始生成像素未做程序绘制、抠图、改色或插值放大，最终文件从内置工具目录复制保存。

