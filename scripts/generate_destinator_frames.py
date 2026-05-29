"""
Generate 360° rotation frames of the Mitsubishi Destinator using Nano Banana.
Strategy: pass all 4 user-provided reference images on every call + an explicit
camera-angle description so identity stays coherent across frames.

Usage:
    python generate_destinator_frames.py --start 0 --count 8 --step 45   # test batch
    python generate_destinator_frames.py --start 0 --count 60 --step 6   # full batch
"""
import argparse
import asyncio
import base64
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

load_dotenv("/app/backend/.env")

REF_DIR = Path("/tmp/destinator_refs")
OUT_DIR = Path("/app/frontend/public/destinator")
OUT_DIR.mkdir(parents=True, exist_ok=True)

REFS = [
    REF_DIR / "ref_front.jpg",      # full front, low-angle
    REF_DIR / "ref_front34.jpg",    # front three-quarter (driver side)
    REF_DIR / "ref_rear.jpg",       # rear three-quarter (passenger side)
    REF_DIR / "ref_top.jpg",        # aerial top-down
]

# Eye-level, locked-camera prompt. We describe both the constant scene and the
# per-frame yaw so the model produces a consistent rotation.
BASE_SCENE = (
    "Photorealistic studio product photography of the EXACT same white "
    "Mitsubishi Destinator SUV shown in the reference images. The car must "
    "keep identical identity: same body shape, same Mitsubishi 3-diamond "
    "grille with hexagonal mesh, same vertical LED headlights, same C-shaped "
    "tail lights, same two-tone wheel design, same 'DESTINATOR' badging, "
    "same body proportions, glossy pearl white paint. "
    "Setting: high-end luxury car showroom, polished dark concrete floor "
    "with subtle reflections, soft gradient grey-to-black walls, cinematic "
    "rim lighting from above and behind, softbox key light from the front-"
    "left, gentle reflections on the body panels. "
    "Camera: locked tripod at eye-level (around 1.4 meters), 50mm lens "
    "equivalent, car perfectly centered in frame, full vehicle visible with "
    "small margin, no people, no other objects. "
    "Background must be IDENTICAL across every frame in the sequence."
)


def yaw_description(deg: int) -> str:
    """Return a natural-language description of the camera yaw around the car.
    0° = looking at the front, 90° = right side, 180° = rear, 270° = left side.
    """
    deg = deg % 360
    if deg == 0:
        return "viewed from directly in front (front facing camera)"
    if 0 < deg < 90:
        return (
            f"viewed from the FRONT-RIGHT three-quarter angle, "
            f"camera rotated {deg} degrees clockwise around the car from the front "
            f"(front fascia mostly visible, right side partially visible)"
        )
    if deg == 90:
        return "viewed from the RIGHT side (full passenger side profile, driver door away from camera)"
    if 90 < deg < 180:
        return (
            f"viewed from the REAR-RIGHT three-quarter angle, "
            f"camera rotated {deg} degrees clockwise from the front "
            f"(right side and rear visible, taillights starting to show)"
        )
    if deg == 180:
        return "viewed from directly BEHIND (rear of car facing camera, tail lights and 'DESTINATOR' badge clearly visible)"
    if 180 < deg < 270:
        return (
            f"viewed from the REAR-LEFT three-quarter angle, "
            f"camera rotated {deg} degrees clockwise from the front "
            f"(rear and left side visible)"
        )
    if deg == 270:
        return "viewed from the LEFT side (full driver side profile)"
    # 270 < deg < 360
    return (
        f"viewed from the FRONT-LEFT three-quarter angle, "
        f"camera rotated {deg} degrees clockwise from the front "
        f"(front fascia and left side visible, headlights on left visible)"
    )


def load_reference_image_contents():
    contents = []
    for path in REFS:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
            contents.append(ImageContent(b64))
    return contents


async def generate_frame(api_key: str, frame_idx: int, deg: int, refs):
    out_path = OUT_DIR / f"frame_{frame_idx:02d}.png"
    if out_path.exists() and out_path.stat().st_size > 1000:
        print(f"[skip] frame {frame_idx:02d} ({deg:3d}°) already exists")
        return True

    yaw = yaw_description(deg)
    prompt = (
        f"{BASE_SCENE} For THIS frame specifically: the car is {yaw}. "
        f"This is frame {frame_idx+1} of a 360-degree turntable sequence — "
        f"the showroom background, lighting, car position in frame, and car "
        f"identity must be IDENTICAL to other frames; only the yaw of the "
        f"vehicle changes."
    )

    chat = LlmChat(
        api_key=api_key,
        session_id=f"destinator-frame-{frame_idx}",
        system_message="You are a photorealistic product photographer generating turntable frames for a 360 car spin.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])

    msg = UserMessage(text=prompt, file_contents=refs)
    try:
        text, images = await chat.send_message_multimodal_response(msg)
    except Exception as e:
        print(f"[FAIL] frame {frame_idx:02d} ({deg:3d}°): {e}")
        return False

    if not images:
        print(f"[FAIL] frame {frame_idx:02d} ({deg:3d}°): no image returned. text={text[:120]}")
        return False

    img_bytes = base64.b64decode(images[0]["data"])
    with open(out_path, "wb") as f:
        f.write(img_bytes)
    print(f"[ok]   frame {frame_idx:02d} ({deg:3d}°) -> {out_path.name} ({len(img_bytes)//1024} KB)")
    return True


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0, help="starting frame index (0-based)")
    parser.add_argument("--count", type=int, default=8, help="number of frames to generate")
    parser.add_argument("--step", type=int, default=45, help="angle step in degrees per frame")
    parser.add_argument("--frame-stride", type=int, default=None,
                        help="how many output frames each generated image covers "
                             "(used when generating a sparser test batch but writing to the full 60-frame grid)")
    args = parser.parse_args()

    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        print("EMERGENT_LLM_KEY missing from /app/backend/.env")
        sys.exit(1)

    refs = load_reference_image_contents()
    print(f"Loaded {len(refs)} reference images")
    print(f"Generating {args.count} frame(s) starting at index {args.start}, step={args.step}°")

    successes = 0
    for i in range(args.count):
        frame_idx = args.start + i
        deg = (frame_idx * args.step) % 360
        ok = await generate_frame(api_key, frame_idx, deg, refs)
        if ok:
            successes += 1
        # Small pause between calls to avoid rate-limit
        await asyncio.sleep(1.2)

    print(f"\nDone. {successes}/{args.count} frames generated.")
    print(f"Files in {OUT_DIR}:")
    for p in sorted(OUT_DIR.glob('frame_*.png')):
        print(f"  {p.name}  {p.stat().st_size//1024} KB")


if __name__ == "__main__":
    asyncio.run(main())
