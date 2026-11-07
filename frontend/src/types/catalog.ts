/**
 * PrintDeck (printdeck.net) — Phase 3 TypeScript Domain & Spatial Studio Models.
 */

export type ProductVertical =
  | "canvas_painting"
  | "framed_fine_art"
  | "dtg_apparel"
  | "aop_apparel"
  | "headwear"
  | "mug_drinkware"
  | "desk_mat"
  | "decal_sticker"
  | "custom_memorabilia"
  | "legacy_hardware";

export type StudioMode = "wall_art" | "apparel_memorabilia";

export type RoomEnvironmentId =
  | "modern_loft"
  | "executive_office"
  | "coastal_living"
  | "dark_studio";

export type FrameSubstrateId =
  | "stretched_canvas_15"
  | "matte_anodized_metal"
  | "museum_alder_frame";

export type TypographyPresetId =
  | "foundry_mono"
  | "atelier_serif"
  | "kinetic_grotesk"
  | "industrial_stencil";

export interface ProductVariant {
  variant_id: string;
  variant_sku: string;
  title?: string;
  size_code: string;
  color_name: string;
  color_hex: string;
  retail_price_cents: number;
  weight_grams?: number;
}

export interface PrintDeckProduct {
  product_id: string;
  master_sku: string;
  slug: string;
  title: string;
  description: string;
  vertical: ProductVertical;
  print_area_width_in: number;
  print_area_height_in: number;
  required_dpi: number;
  bleed_margin_in: number;
  requires_transparent_alpha: boolean;
  gallery_wrap_bleed: boolean;
  base_retail_price_cents: number;
  is_legacy_hardware: boolean;
  protected_route?: string | null;
  variants: ProductVariant[];
}

export interface LightingRigState {
  colorTempKelvin: number; // 2700K (Warm Gallery Halogen) -> 6500K (North Daylight)
  intensityPct: number;    // 25% -> 125%
  azimuthDeg: number;      // -60 deg -> +60 deg directional spotlight angle
  showTrueToScaleFurniture: boolean;
}

export interface CustomArtworkLayer {
  id: string;
  kind: "curated_art" | "custom_text" | "uploaded_image";
  label: string;
  text?: string;
  fontPreset?: TypographyPresetId;
  colorHex: string;
  normX: number; // 0.0 -> 1.0 across print area
  normY: number; // 0.0 -> 1.0 across print area
  scale: number; // 0.25 -> 2.0
  rotationDeg: number;
  imageDataUrl?: string;
  preflightVerified?: boolean;
  effectiveDpi?: number;
  upscaledByNode?: string;
  haloPixelsRemoved?: number;
}

export interface CartLineItem {
  variant_id: string;
  variant_sku: string;
  master_sku: string;
  title: string;
  unit_price_cents: number;
  quantity: number;
  print_asset_id?: string;
  customSummary?: string;
}

export interface PostPurchaseGraceState {
  order_id: string;
  order_number: string;
  status: "PAID_GRACE_HOLD" | "SENT_TO_PRODUCTION";
  expires_at_utc: string;
  remaining_seconds: number;
  selected_provider: string;
  upsell_accepted: boolean;
}
