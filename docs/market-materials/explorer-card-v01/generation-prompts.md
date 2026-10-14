# 小 E 探索者收藏卡：完整生成记录

生成方式：内置 image_gen 工具；每面独立生成，再以同一工具调整印刷安全边距。无 CLI/API 回退，无程序绘制或修改插画像素。日期：2026-10-12。

## 参考文件

- `../../../hardware-prototypes/xiao-e-v01/previews/hero.png`：正面角色身份。
- `../../../hardware-prototypes/xiao-e-v01/previews/back.png`：背面造型。
- 背面生成时同时引用已完成的正面，以统一画风、线条和配色。

## 正面初稿

```text
Use case: illustration-story.
Asset: FRONT of a premium Xiao E explorer collectible printed card. Create ONE finished flat illustration, portrait aspect ratio EXACTLY 61:91, ideally 1952 x 2912 pixels. This is artwork to print, not a photograph of a card.
Reference image 1 is the exact Xiao E mascot identity seen from the front. Reference image 2 documents the back of the same mascot. Transform this reference character into 2D American comic pop art, while keeping the established physical design.

Scene: Xiao E bursts forward out of an interstellar comic scene, flying diagonally toward the viewer, with one foreshortened white mitten hand reaching out in front, the other arm swept back and TWO short legs in a dynamic airborne pose. Friendly, brave, energetic. White cape with turquoise edging streams backward. The character dominates the middle of the composition. Make the head, face, reaching hand and chest star immediately readable at the tiny final card size.

Identity: oversized off-white round/rounded-square helmet; glossy near-black rounded-rectangular visor; two cyan inward-facing chevron-shaped graphic eyes (as in the reference), no mouth; concentric circular white/turquoise ear modules; one short chunky curved turquoise crest on top, not long antennae. Short off-white robot body, dark joints and dark chunky boots; turquoise four-point compass star outline on the chest, circular turquoise neck clasp. Only two arms and two legs. Keep the white cape and teal border. No pedestal.

Style: striking American superhero comic pop art illustration, powerful varying bold black ink contours, clean angular cel shading, graphic halftone dots, confident controlled detail. Dominant deep midnight navy and vibrant turquoise/teal, warm off-white mascot; small flashes of bright yellow and coral red. Big diagonal comic-panel divisions and converging radial speed lines behind the character, dramatic foreshortening, a few distant planets, bold high-contrast silhouettes. Crisp polished print artwork, not a 3D render and not anime manga. Use large readable graphic shapes; retain the mascot's rounded friendly proportions.

Print composition: full bleed edge-to-edge background, NO visible card outline or border. Canvas represents 61 x 91 mm; finished trim is 55 x 85 mm centered with 3 mm bleed. Keep the ENTIRE character including crest, hands, boots and cape tips, all important identity marks at least 6 mm from canvas edges (x 10%-90%, y 7%-93%); let only background rays/panels extend through the bleed. Strong energetic composition without clipping the character. No crop or safe-area marks in the image.

Absolutely no text or typography anywhere: no words, letters, numbers, pseudo-writing, brand wordmark, signatures, watermark, sound effects, QR code, barcodes, codes, labels, blank information panels or speech bubbles. The graphic chevron eyes and four-point star insignia are allowed. Opaque rectangular artwork with square corners, no transparency, no mockup, no surrounding tabletop, no drop shadow.
```

## 正面安全边距调整（最终版）

```text
Use case: precise-object-edit. Refine this exact Xiao E collectible card FRONT illustration for print safety. Keep the character identity, expression, hand pose, TWO arms and TWO legs, cape, star on chest, diagonal movement, colors, bold comic inking and halftone style unchanged. Preserve the same complete interstellar scene and absolutely text-free artwork.

Change ONLY the composition scale: the character's leftmost reaching fingertip and rightmost cape tip are currently too close to the image edge for trimming. Uniformly reduce the entire character including all limbs and cape to approximately 78% of its present size, keep it around the same visual center, and seamlessly extend the existing cosmic comic background into the revealed area. Every part of the character must fit inside x=12% to 88% of the full canvas, y=10% to 90%, leaving visibly generous background on BOTH left and right sides of the reaching hand and cape. The entire mascot remains the dominant subject. Do not add a second character. Do not add foreground objects over it.

Produce one high-resolution portrait artwork with EXACT 61:91 aspect ratio, preferably 1952x2912. This canvas represents 61x91mm including 3mm bleed per edge for a 55x85mm card; important character details must remain at least 6mm from the outer canvas. No visible margins: the cosmic background remains full bleed edge-to-edge. No text, letters, numbers, pseudo-writing, watermark, QR code, crop marks, frames or card mockup; only the existing graphical chevron eyes and four-point insignia. Opaque square-cornered rectangular flat 2D illustration.
```

## 背面初稿

```text
Use case: illustration-story.
Asset: BACK of the same Xiao E explorer collectible card. Create ONE finished full-bleed flat illustration, portrait EXACT 61:91 aspect ratio, preferably 1952 x 2912 pixels.
Input references: image 1 is the APPROVED FRONT card, use its exact ink style, colors, comic halftone rendering and character design. Image 2 is the established REAR view of Xiao E and is the identity authority for the back of the helmet and cape. Image 3 is another identity reference showing the front; do NOT show a front face in this rear-view composition.

Scene/composition: a single small heroic Xiao E stands in the lower foreground on the curved surface of a small rocky planet, facing away from us toward an enormous luminous FOUR-POINT STAR shaped cosmic portal in the upper-middle distance. The portal is the dominant background focal point and its recognizable four compass points are fully visible. Use broad sweeping orbital arcs, a few teal and coral planets, geometric shards and converging comic rays to create deep perspective toward the portal. The atmosphere is awe, possibility, joyful exploration of a universe of knowledge, expressed only visually with abstract cosmos, no letters, books with writing or interface panels.

Place the rear-view character centrally in the lower portion, approximately x=28%-72%, y=51%-86%. Make it large enough that the turquoise four-point outlined compass-star on the white cape reads clearly at 55x85mm card size. Show exactly two short arms and two short legs, charcoal chunky boots planted on the planet. Big off-white rounded helmet with smooth unadorned rear shell, one short rounded turquoise crest on top, symmetric concentric white/turquoise ear disks at the sides. The white short cape has a clean turquoise edge and a single LARGE turquoise outlined four-point star centered on its back. No eyes or face visible through the back of the head. Rear anatomy matches reference 2. Do not show a pedestal.

The portal should be geometric and elegantly striking: a large pointed four-point star aperture with near-white light, bright cyan rim and restrained yellow highlights against very dark navy, no conventional five-point star. Keep its full tips inside x=16%-84%, y=10%-49%, so it is clear and safely inset. Orbit arcs wrap around it, leading the eye inward. Planet surface can fill the bottom and extend to the edges.

Style MUST match approved front: bold black variable line weight, high-impact American comic pop art, angular clean cel-shading, richly controlled printed halftone dots; predominantly midnight navy, turquoise/cyan, warm off-white, small coral-red and bright-yellow accents. Crisp 2D illustration, no realistic 3D render. No ornamental card frame.

Printing: full background art to all four edges. 61x91mm full canvas includes 3mm bleed around 55x85mm finished card; preserve critical character and portal detail at least 6mm from the outer canvas. Leave useful dark negative space around the portal for clear silhouette, but NO blank labels or fields. All critical character details fully inside safe area. No crop guides.

Absolutely NO typography: no words, no letters, no numbers, no pseudo-text, no logos with writing, no signature, no watermarks, no speech bubbles, no QR, barcode or redemption field. Only graphical stars and abstract cosmic elements. One opaque square-cornered rectangular illustration, not a card mockup, no surrounding tabletop, no cast shadow or transparent corners. Both this back and its paired front are upright in portrait.
```

## 背面门户安全边距调整（最终版）

```text
Use case: precise-object-edit. This is the final BACK card artwork. Make one precise print-safety correction: reduce and reposition ONLY the large four-point star portal in the upper center so that ALL FOUR portal points are fully visible, with the top point at about 10% of image height, left and right points at about 16% and 84% of image width, and the bottom point at about 40% of image height. Leave a clear narrow navy gap between the portal's bottom tip and the top of Xiao E's turquoise crest. The portal must remain a magnificent bright four-point compass/star aperture, not a five-point star. Seamlessly adjust the surrounding cosmic rays and halftone glow locally to suit the smaller portal. Keep all important portal points more than 6mm from outer edges of this 61x91mm canvas.

Preserve EVERYTHING ELSE: the entire character at its current position and scale; rear off-white helmet, turquoise crest and ring ears; two arms, two legs, dark boots, white cape with turquoise edge and the large four-point chest-style star on the cape; the small foreground planet; navy/turquoise with yellow and coral accents; all general orbit and planet composition; bold American comic inking, cel shading and halftone dots; exact 61:91 portrait aspect ratio. The character must be rear-view with no face. Full-bleed background right to every edge, square corners. No text, letters, numbers, symbols resembling writing, captions, watermarks, codes, borders, crop marks, blank labels or mockup. Prefer high resolution 1952x2912.
```

## 生成文件追溯

初稿与最终稿均保留在内置生成工具的原保存位置，最终图另复制到本目录：

- 正面初稿：`C:/Users/BX/.codex/generated_images/01a12f92-a87a-75e3-864b-c0d2946b2c7f/exec-8d98a5de-eb6b-4f24-8977-6e682efd950e.png`
- 正面最终：`C:/Users/BX/.codex/generated_images/01a12f92-a87a-75e3-864b-c0d2946b2c7f/exec-26c7d383-f422-49a0-bfef-ca74e20896b6.png`
- 背面初稿：`C:/Users/BX/.codex/generated_images/01a12f92-a87a-75e3-864b-c0d2946b2c7f/exec-c9b945e7-6ab2-46e8-bdcb-5ed75967bc01.png`
- 背面最终：`C:/Users/BX/.codex/generated_images/01a12f92-a87a-75e3-864b-c0d2946b2c7f/exec-9bcfb3ed-a483-4859-88ef-9a4a670c4472.png`

提示词中的 1952×2912 是请求分辨率；工具实际交付两图均为 **1027×1531 px**。按 61×91 mm 放置时横向 427.64 ppi、纵向 427.33 ppi，均高于 300 ppi。未插值放大，不以请求尺寸冒充实际尺寸。

