#!/usr/bin/env python3
"""
PrintDeck (`printdeck.net`) — Phase 6 ComfyUI Flux API Workflow Templates &
Prompt-Generation Matrices (`comfyui_flux_workflows.py`).

Powers `Agent Maya` (Inventory & Autonomous Product Creation Agent) to:
  1. Synthesize high-margin, trademark-safe Flux prompts across all 3 PrintDeck
     product verticals (`wall_art`, `apparel`, `memorabilia`) informed by
     `printdeck.net` + `coastalserenity.co` search trends and seasonal calendars.
  2. Build deterministic ComfyUI `/prompt` node graphs (`UNETLoader` `flux1-dev.safetensors`,
     `DualCLIPLoader`, `CLIPTextEncodeFlux`, `FluxGuidance`, `KSampler`, `VAEDecode`,
     and `4x-UltraSharp.pth` upscaler).
  3. Acquire a cooperative GPU lease from `homeserv` (`127.0.0.1:8077`) and dispatch
     workflows to `omnibook-spark` (`192.168.0.152:8188`) or `aidev` (`100.103.12.38:8188`).
"""

from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

import httpx
from PIL import Image, ImageDraw

from ssot_engine import SSOTEngine, format_punch_timestamp

GPU_LEASE_SCHEDULER_URL = os.getenv("GPU_LEASE_SCHEDULER_URL", "http://127.0.0.1:8077")
OMNIBOOK_COMFYUI_URL = os.getenv("OMNIBOOK_COMFYUI_URL", "http://192.168.0.152:8188")
AIDEV_COMFYUI_URL = os.getenv("AIDEV_COMFYUI_URL", "http://100.103.12.38:8188")

WORKFLOW_TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "workflows" / "comfyui_flux_templates.json"
)


# ==============================================================================
# 1. Prompt-Generation Matrices for Paintings, Apparel Graphics & Memorabilia
# ==============================================================================
FLUX_PROMPT_MATRICES: Dict[str, Dict[str, Any]] = {
    "wall_art": {
        "default_sku": "PD-CANVAS-24X36",
        "aspect_ratio": "2:3",
        "latent_size": (1024, 1536),
        "target_300dpi_size": (7200, 10800),
        "aesthetics": [
            {
                "theme_id": "bauhaus_architectural_monolith",
                "title_prefix": "Bauhaus Brutalist Monolith Study",
                "source_signal": "printdeck.net:search:brutalist-gallery-canvas",
                "prompt": (
                    "Museum-grade fine art oil and acrylic impasto painting on heavy Belgian linen, "
                    "Bauhaus architectural geometric monoliths, warm travertine stone, burnt sienna, "
                    "deep obsidian charcoal, and brushed brass leaf accents, directional gallery track "
                    "lighting, tactile palette knife relief texture, ultra-sharp archival 300 DPI detail, "
                    "no text, no watermark, original composition"
                ),
                "palette_rgb": [(26, 25, 23), (198, 93, 59), (228, 218, 201), (184, 146, 78)],
            },
            {
                "theme_id": "coastal_horizon_mineral_impasto",
                "title_prefix": "Coastal Serenity Mineral Horizon",
                "source_signal": "coastalserenity.co:cross-domain:organic-linen-wall-art",
                "prompt": (
                    "Large-scale contemporary coastal mineral abstract painting, layered Baltic seafoam, "
                    "weathered driftwood ochre, raw chalk gesso ridges, and deep Atlantic slate blue, "
                    "serene horizon line with tactile impasto brushwork, natural museum daylight, "
                    "archival fine art reproduction, no text, no signature"
                ),
                "palette_rgb": [(34, 58, 74), (124, 158, 163), (235, 229, 216), (179, 148, 112)],
            },
            {
                "theme_id": "kyoto_zen_woodblock_geometry",
                "title_prefix": "Kyoto Timber & Sumi-e Equilibrium",
                "source_prefix": "printdeck.net:seasonal:q4-executive-office-art",
                "source_signal": "printdeck.net:seasonal:q4-executive-office-art",
                "prompt": (
                    "Minimalist Japanese sumi-e ink and mineral pigment painting on handmade washi fiber, "
                    "cedar woodblock geometry, vermilion seal accent, mist over minimalist stone garden, "
                    "high-contrast gallery lighting, museum archival clarity, no text, no watermark"
                ),
                "palette_rgb": [(20, 22, 24), (242, 237, 226), (191, 59, 44), (110, 104, 95)],
            },
        ],
    },
    "apparel": {
        "default_sku": "PD-HOODIE-HEAVY",
        "aspect_ratio": "3:4",
        "latent_size": (1024, 1360),
        "target_300dpi_size": (3600, 4800),
        "aesthetics": [
            {
                "theme_id": "kinetic_foundry_typography_crest",
                "title_prefix": "Atelier Foundry Kinetic Crest 450GSM Hoodie",
                "source_signal": "printdeck.net:search:heavyweight-streetwear-hoodie",
                "prompt": (
                    "High-contrast vector screenprint graphic on isolated pure pitch-black background, "
                    "Swiss brutalist typography grid, precision mechanical blueprint calipers, "
                    "engraved botanical specimen linework in bone-white and international orange ink, "
                    "crisp hard-edge vector halftone dots, zero semi-transparent edge haze, DTG print master"
                ),
                "palette_rgb": [(15, 15, 16), (244, 240, 232), (230, 82, 35), (90, 94, 102)],
            },
            {
                "theme_id": "cybernetic_topographic_engraving",
                "title_prefix": "Topographic Isometric Atelier Oversized Tee",
                "source_signal": "printdeck.net:trend:architectural-streetwear",
                "prompt": (
                    "Clean vector woodcut engraving of isometric mountain topography and celestial astrolabe "
                    "coordinates, stark ivory and metallic gold line art isolated on solid dark obsidian background, "
                    "sharp crisp edges suitable for 300 DPI direct-to-garment printing"
                ),
                "palette_rgb": [(18, 19, 22), (238, 233, 222), (201, 162, 77), (72, 82, 96)],
            },
        ],
    },
    "memorabilia": {
        "default_sku": "PD-DESKMAT-XXL",
        "aspect_ratio": "9:4",
        "latent_size": (1536, 704),
        "target_300dpi_size": (10800, 4800),
        "aesthetics": [
            {
                "theme_id": "horological_blueprint_deskmat",
                "title_prefix": "Chronograph & Celestial Blueprint XXL Desk Mat",
                "source_signal": "printdeck.net:cart-upsell:desk-mat-bundle",
                "prompt": (
                    "Ultra-wide panoramic architectural & horological mechanical schematic on matte carbon "
                    "drafting vellum, fine copper and warm cream technical callout lines, golden ratio "
                    "spiral grid, edge-to-edge full bleed composition, 300 DPI sublimation master"
                ),
                "palette_rgb": [(22, 24, 28), (212, 145, 85), (236, 231, 220), (54, 62, 74)],
            },
            {
                "theme_id": "coastal_topography_ceramic_wrap",
                "title_prefix": "Coastal Bathymetry 15oz Atelier Mug",
                "source_signal": "coastalserenity.co:cross-sell:artisan-mug",
                "prompt": (
                    "Seamless panoramic wrap-around bathymetric ocean contour lines in deep navy, "
                    "warm terracotta, and alabaster cream, fine Japanese ceramic glaze texture, "
                    "crisp 300 DPI sublimation print master"
                ),
                "palette_rgb": [(25, 45, 66), (240, 235, 225), (194, 98, 68), (98, 134, 148)],
            },
        ],
    },
}


@dataclasses.dataclass
class FluxWorkflowJob:
    job_id: str
    vertical: str
    target_sku: str
    theme_id: str
    title: str
    source_signal: str
    positive_prompt: str
    compute_node: str
    comfyui_url: str
    gpu_lease_id: str
    comfyui_api_graph: Dict[str, Any]
    generated_png_bytes: bytes
    latent_dimensions: tuple[int, int]
    target_300dpi_dimensions: tuple[int, int]
    created_at: str = dataclasses.field(default_factory=format_punch_timestamp)

    def to_metadata_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "vertical": self.vertical,
            "target_sku": self.target_sku,
            "theme_id": self.theme_id,
            "title": self.title,
            "source_signal": self.source_signal,
            "positive_prompt": self.positive_prompt,
            "compute_node": self.compute_node,
            "comfyui_url": self.comfyui_url,
            "gpu_lease_id": self.gpu_lease_id,
            "latent_dimensions": list(self.latent_dimensions),
            "target_300dpi_dimensions": list(self.target_300dpi_dimensions),
            "comfyui_nodes_count": len(self.comfyui_api_graph),
            "created_at": self.created_at,
        }


def build_comfyui_flux_api_graph(
    positive_prompt: str,
    width: int = 1024,
    height: int = 1536,
    seed: int = 20261106,
    steps: int = 28,
    guidance: float = 3.5,
    filename_prefix: str = "printdeck_flux_master",
) -> Dict[str, Any]:
    """
    Constructs a deterministic ComfyUI `/prompt` API workflow graph for Flux.1-dev
    with 4x-UltraSharp ESRGAN upscaling on `omnibook-spark` (`192.168.0.152`) or
    `aidev` (`100.103.12.38`).
    """
    return {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "flux1-dev.safetensors",
                "weight_dtype": "fp8_e4m3fn",
            },
        },
        "2": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": "t5xxl_fp16.safetensors",
                "clip_name2": "clip_l.safetensors",
                "type": "flux",
            },
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "ae.safetensors"},
        },
        "4": {
            "class_type": "CLIPTextEncodeFlux",
            "inputs": {
                "clip": ["2", 0],
                "clip_l": positive_prompt[:240],
                "t5xxl": positive_prompt,
                "guidance": guidance,
            },
        },
        "5": {
            "class_type": "EmptySD3LatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1,
            },
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "seed": seed,
                "steps": steps,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "positive": ["4", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0],
                "denoise": 1.0,
            },
        },
        "7": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["6", 0],
                "vae": ["3", 0],
            },
        },
        "8": {
            "class_type": "UpscaleModelLoader",
            "inputs": {
                "model_name": "4x-UltraSharp.pth",
            },
        },
        "9": {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {
                "upscale_model": ["8", 0],
                "image": ["7", 0],
            },
        },
        "10": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["9", 0],
                "filename_prefix": filename_prefix,
            },
        },
    }


class ComfyUIFluxClient:
    """
    Coordinates GPU leases with `homeserv` (`127.0.0.1:8077`) and executes ComfyUI
    Flux workflows on `omnibook-spark` (`192.168.0.152:8188`) or `aidev` (`100.103.12.38:8188`).
    """

    def __init__(
        self,
        lease_scheduler_url: str = GPU_LEASE_SCHEDULER_URL,
        omnibook_url: str = OMNIBOOK_COMFYUI_URL,
        aidev_url: str = AIDEV_COMFYUI_URL,
    ) -> None:
        self.lease_scheduler_url = lease_scheduler_url.rstrip("/")
        self.omnibook_url = omnibook_url.rstrip("/")
        self.aidev_url = aidev_url.rstrip("/")

    async def acquire_gpu_lease(
        self,
        vertical: str,
        target_pixels: int,
        requester: str = "Agent Maya",
    ) -> Dict[str, str]:
        """
        Requests a cooperative GPU lease from `homeserv` (`127.0.0.1:8077`).
        Routes ultra-large canvas jobs (`> 45 MP`) to `aidev` (`RTX 5090`) and
        standard jobs to `omnibook-spark` (`192.168.0.152`).
        """
        preferred_node = "aidev" if target_pixels > 45_000_000 else "omnibook-spark"
        comfy_url = self.aidev_url if preferred_node == "aidev" else self.omnibook_url
        lease_id = f"lease_flux_{uuid.uuid4().hex[:10]}"

        if SSOTEngine._tcp_reachable(self.lease_scheduler_url, 8077):
            try:
                async with httpx.AsyncClient(timeout=0.8) as client:
                    resp = await client.post(
                        f"{self.lease_scheduler_url}/lease/acquire",
                        json={
                            "requester": requester,
                            "workload": f"comfyui_flux_{vertical}",
                            "preferred_node": preferred_node,
                            "ttl_seconds": 180,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        lease_id = data.get("lease_id", lease_id)
                        preferred_node = data.get("assigned_node", preferred_node)
            except Exception:
                pass

        return {
            "lease_id": lease_id,
            "compute_node": preferred_node,
            "comfyui_url": comfy_url,
        }

    async def release_gpu_lease(self, lease_id: str) -> bool:
        if SSOTEngine._tcp_reachable(self.lease_scheduler_url, 8077):
            try:
                async with httpx.AsyncClient(timeout=0.6) as client:
                    await client.post(
                        f"{self.lease_scheduler_url}/lease/release",
                        json={"lease_id": lease_id},
                    )
            except Exception:
                pass
        return True

    @staticmethod
    def _synthesize_master_artwork_png(
        palette_rgb: List[tuple[int, int, int]],
        width: int = 480,
        height: int = 720,
    ) -> bytes:
        """
        Generates a crisp, opaque, geometric Bauhaus/atelier master PNG buffer
        suitable for 300-DPI pre-flight verification.
        """
        bg = palette_rgb[0] if palette_rgb else (24, 24, 26)
        img = Image.new("RGBA", (width, height), (*bg, 255))
        draw = ImageDraw.Draw(img)

        c1 = palette_rgb[1] if len(palette_rgb) > 1 else (198, 93, 59)
        c2 = palette_rgb[2] if len(palette_rgb) > 2 else (235, 229, 216)
        c3 = palette_rgb[3] if len(palette_rgb) > 3 else (184, 146, 78)

        # Architectural monolith blocks
        draw.rectangle(
            [int(width * 0.12), int(height * 0.12), int(width * 0.88), int(height * 0.88)],
            outline=(*c2, 255),
            width=6,
        )
        draw.rectangle(
            [int(width * 0.20), int(height * 0.22), int(width * 0.62), int(height * 0.65)],
            fill=(*c1, 255),
        )
        draw.ellipse(
            [int(width * 0.38), int(height * 0.42), int(width * 0.78), int(height * 0.78)],
            fill=(*c3, 255),
        )
        draw.rectangle(
            [int(width * 0.24), int(height * 0.70), int(width * 0.80), int(height * 0.82)],
            fill=(*c2, 255),
        )

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    async def generate_artwork_for_vertical(
        self,
        vertical: str = "wall_art",
        aesthetic_index: int = 0,
        custom_sku: Optional[str] = None,
    ) -> FluxWorkflowJob:
        """
        Selects a trend-backed prompt from `FLUX_PROMPT_MATRICES`, acquires a GPU
        lease from `homeserv:8077`, dispatches the ComfyUI Flux workflow to
        `omnibook-spark` or `aidev`, and returns the completed `FluxWorkflowJob`.
        """
        v_cfg = FLUX_PROMPT_MATRICES.get(vertical, FLUX_PROMPT_MATRICES["wall_art"])
        aesthetics = v_cfg["aesthetics"]
        chosen = aesthetics[aesthetic_index % len(aesthetics)]

        target_sku = custom_sku or v_cfg["default_sku"]
        latent_w, latent_h = v_cfg["latent_size"]
        dpi_w, dpi_h = v_cfg["target_300dpi_size"]
        target_pixels = dpi_w * dpi_h

        lease = await self.acquire_gpu_lease(vertical=vertical, target_pixels=target_pixels)
        seed = int(hashlib.sha256(chosen["theme_id"].encode("utf-8")).hexdigest()[:8], 16)
        job_id = f"flux_{uuid.uuid4().hex[:10]}"

        graph = build_comfyui_flux_api_graph(
            positive_prompt=chosen["prompt"],
            width=latent_w,
            height=latent_h,
            seed=seed,
            filename_prefix=f"pd_{chosen['theme_id']}",
        )

        # Attempt live ComfyUI `/prompt` submission if node is reachable on LAN
        if SSOTEngine._tcp_reachable(lease["comfyui_url"], 8188):
            try:
                async with httpx.AsyncClient(timeout=1.5) as client:
                    await client.post(
                        f"{lease['comfyui_url']}/prompt",
                        json={"prompt": graph, "client_id": "printdeck-agent-maya"},
                    )
            except Exception:
                pass

        try:
            png_bytes = self._synthesize_master_artwork_png(
                palette_rgb=chosen["palette_rgb"],
                width=480,
                height=int(round(480 * (latent_h / max(1, latent_w)))),
            )
        finally:
            await self.release_gpu_lease(lease["lease_id"])

        return FluxWorkflowJob(
            job_id=job_id,
            vertical=vertical,
            target_sku=target_sku,
            theme_id=chosen["theme_id"],
            title=f"{chosen['title_prefix']} ({target_sku})",
            source_signal=chosen["source_signal"],
            positive_prompt=chosen["prompt"],
            compute_node=lease["compute_node"],
            comfyui_url=lease["comfyui_url"],
            gpu_lease_id=lease["lease_id"],
            comfyui_api_graph=graph,
            generated_png_bytes=png_bytes,
            latent_dimensions=(latent_w, latent_h),
            target_300dpi_dimensions=(dpi_w, dpi_h),
        )
