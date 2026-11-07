"use client";

/**
 * PrintDeck (printdeck.net) — Phase 3 Sub-Second Instant Cart Drawer &
 * 120-Minute Grace Window 1-Click Post-Purchase Upsell Funnel.
 *
 * Engineered with hardware-composited `translate3d` animations (`atelier-cart-drawer`)
 * to eliminate iOS Safari mobile drawer stutter (resolving ISS-0003).
 */

import React, { useState } from "react";
import type { CartLineItem, PostPurchaseGraceState } from "../types/catalog";

interface InstantCartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  items: CartLineItem[];
  onAddCrossSell: (item: CartLineItem) => void;
  onRemoveItem: (variantId: string) => void;
}

const FREE_SHIPPING_THRESHOLD_CENTS = 12000; // $120.00 USD

const COMPLETE_THE_AESTHETIC_CROSS_SELLS: CartLineItem[] = [
  {
    variant_id: "var_deskmat_xxl_std",
    variant_sku: "PD-DESKMAT-XXL-31X15",
    master_sku: "PD-DESKMAT-XXL",
    title: "XXL 31.5\"×15.5\" Stitched Studio Desk Mat (20% Bundle Off)",
    unit_price_cents: 3120,
    quantity: 1,
    customSummary: "AI-Curated Matching Surface • 9450×4650 px @ 300 DPI",
  },
  {
    variant_id: "var_mug_15oz_blk",
    variant_sku: "PD-MUG-15OZ-BLK-STD",
    master_sku: "PD-MUG-15OZ-BLK",
    title: "15oz Matte Black Collector Art Mug (20% Bundle Off)",
    unit_price_cents: 1920,
    quantity: 1,
    customSummary: "AI-Curated Companion • 2550×1050 px @ 300 DPI",
  },
];

export const InstantCartDrawer: React.FC<InstantCartDrawerProps> = ({
  isOpen,
  onClose,
  items,
  onAddCrossSell,
  onRemoveItem,
}) => {
  const [customerEmail, setCustomerEmail] = useState("collector@printdeck.net");
  const [customerZip, setCustomerZip] = useState("28202");
  const [walletMethod, setWalletMethod] = useState<"apple_pay" | "google_pay" | "link" | "card">(
    "apple_pay"
  );
  const [submitting, setSubmitting] = useState(false);
  const [graceOrder, setGraceOrder] = useState<PostPurchaseGraceState | null>(null);
  const [upsellConfirmMsg, setUpsellConfirmMsg] = useState<string>("");

  const subtotalCents = items.reduce((acc, item) => acc + item.unit_price_cents * item.quantity, 0);
  const remainingForFreeShipping = Math.max(0, FREE_SHIPPING_THRESHOLD_CENTS - subtotalCents);
  const progressPct = Math.min(100, Math.round((subtotalCents / FREE_SHIPPING_THRESHOLD_CENTS) * 100));

  const handleExpressCheckout = async () => {
    if (items.length === 0) return;
    setSubmitting(true);
    try {
      const resp = await fetch("/pay/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_address: {
            recipient_name: "Atelier Collector",
            email: customerEmail,
            line1: "400 S Tryon St",
            city: "Charlotte",
            state: "NC",
            postal_code: customerZip,
            country: "US",
          },
          items: items.map((i) => ({
            variant_id: i.variant_id,
            quantity: i.quantity,
            print_asset_id: i.print_asset_id,
          })),
          payment_gateway: "stripe",
          preferred_payment_method: walletMethod,
        }),
      });
      const data = await resp.json();
      if (resp.ok) {
        setGraceOrder({
          order_id: data.order_id,
          order_number: data.order_number,
          status: "PAID_GRACE_HOLD",
          expires_at_utc: new Date(Date.now() + 120 * 60 * 1000).toISOString(),
          remaining_seconds: 7200,
          selected_provider: data.arbitrage_preview?.selected_provider || "printify",
          upsell_accepted: false,
        });
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleAcceptOneClickUpsell = async () => {
    if (!graceOrder) return;
    const resp = await fetch(`/api/v2/orders/${graceOrder.order_id}/upsell`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        variant_id: "var_decal_6x6_std",
        quantity: 1,
        upsell_discount_bps: 2000,
      }),
    });
    if (resp.ok) {
      setGraceOrder({ ...graceOrder, upsell_accepted: true });
      setUpsellConfirmMsg(
        "Added 6\"×6\" Weatherproof Vinyl Art Decal ($9.60, 20% off) to your active 120-minute grace hold order!"
      );
    }
  };

  return (
    <>
      <div
        className={`atelier-cart-backdrop ${isOpen ? "is-open" : ""}`}
        onClick={onClose}
        aria-hidden={!isOpen}
      />
      <aside
        className={`atelier-cart-drawer ${isOpen ? "is-open" : ""}`}
        aria-label="PrintDeck Instant Cart & 1-Click Express Checkout Drawer"
      >
        <header
          style={{
            padding: "1.25rem 1.5rem",
            borderBottom: "1px solid var(--foundry-hairline)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--foundry-brass)" }}>
              INSTANT ATELIER CART • PARA-PAYGATE (:8790)
            </div>
            <h3 style={{ fontFamily: "var(--font-display)", fontSize: "1.4rem", fontWeight: 400 }}>
              Commissioned Editions ({items.reduce((sum, i) => sum + i.quantity, 0)})
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="foundry-pill"
            style={{ padding: "0.4rem 0.75rem" }}
          >
            CLOSE ✕
          </button>
        </header>

        {/* Free Shipping Progress Bar */}
        <div
          style={{
            padding: "0.85rem 1.5rem",
            background: "#0d0f13",
            borderBottom: "1px solid var(--foundry-hairline)",
            fontFamily: "var(--font-mono)",
            fontSize: "0.74rem",
          }}
        >
          {remainingForFreeShipping === 0 ? (
            <span style={{ color: "var(--foundry-emerald)" }}>
              ✓ UNLOCKED: Complimentary Priority Insured Shipping
            </span>
          ) : (
            <span>
              Add <strong>${(remainingForFreeShipping / 100).toFixed(2)}</strong> more for Free
              Insured Gallery Shipping
            </span>
          )}
          <div
            style={{
              height: "5px",
              background: "#1e2229",
              marginTop: "0.45rem",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${progressPct}%`,
                height: "100%",
                background: "var(--foundry-emerald)",
                transition: "width 0.25s ease",
              }}
            />
          </div>
        </div>

        {/* Cart Line Items & AI Cross-Sells */}
        <div style={{ flex: 1, overflowY: "auto", padding: "1.25rem 1.5rem" }}>
          {items.map((item) => (
            <div
              key={item.variant_id}
              style={{
                padding: "0.85rem 0",
                borderBottom: "1px solid var(--foundry-hairline)",
                display: "flex",
                justifyContent: "space-between",
                gap: "0.75rem",
              }}
            >
              <div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--foundry-brass)" }}>
                  {item.variant_sku}
                </div>
                <div style={{ fontWeight: 600, fontSize: "0.92rem" }}>{item.title}</div>
                {item.customSummary && (
                  <div style={{ fontSize: "0.75rem", color: "#9ca3af", marginTop: "0.2rem" }}>
                    {item.customSummary}
                  </div>
                )}
              </div>
              <div style={{ textAlign: "right", fontFamily: "var(--font-mono)" }}>
                <div>${((item.unit_price_cents * item.quantity) / 100).toFixed(2)}</div>
                <button
                  type="button"
                  onClick={() => onRemoveItem(item.variant_id)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#f87171",
                    fontSize: "0.7rem",
                    cursor: "pointer",
                    marginTop: "0.35rem",
                  }}
                >
                  Remove
                </button>
              </div>
            </div>
          ))}

          {/* AI-Curated "Complete the Aesthetic" 20% Off Cross-Sells */}
          <div style={{ marginTop: "1.4rem" }}>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.72rem",
                color: "var(--foundry-brass)",
                marginBottom: "0.6rem",
              }}
            >
              AI-CURATED • COMPLETE THE AESTHETIC (20% OFF BUNDLE)
            </div>
            {COMPLETE_THE_AESTHETIC_CROSS_SELLS.map((cs) => (
              <div
                key={cs.variant_id}
                style={{
                  padding: "0.75rem",
                  background: "#0b0c0e",
                  border: "1px solid var(--foundry-hairline)",
                  marginBottom: "0.5rem",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <div style={{ fontSize: "0.82rem", fontWeight: 600 }}>{cs.title}</div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--foundry-emerald)" }}>
                    ${(cs.unit_price_cents / 100).toFixed(2)} USD
                  </div>
                </div>
                <button
                  type="button"
                  className="foundry-pill"
                  onClick={() => onAddCrossSell(cs)}
                >
                  + ADD 20% OFF
                </button>
              </div>
            ))}
          </div>

          {/* Post-Purchase 1-Click Upsell Funnel inside the 120-Minute Grace Window */}
          {graceOrder && (
            <div
              style={{
                marginTop: "1.25rem",
                padding: "1rem",
                background: "rgba(232, 74, 39, 0.12)",
                border: "1px solid var(--foundry-vermilion)",
              }}
            >
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "#fb923c" }}>
                ORDER {graceOrder.order_number} • 120-MINUTE EDITABLE GRACE HOLD ACTIVE
              </div>
              <p style={{ fontSize: "0.82rem", margin: "0.45rem 0" }}>
                Routed to <strong>{graceOrder.selected_provider.toUpperCase()}</strong> via Smart
                Arbitrage. Add a matching 6&quot;×6&quot; Weatherproof Vinyl Art Decal for{" "}
                <strong>$9.60 (20% Off)</strong> with 1 click—ships in the same box with zero
                re-entry of payment details:
              </p>
              {!graceOrder.upsell_accepted ? (
                <button
                  type="button"
                  onClick={handleAcceptOneClickUpsell}
                  className="foundry-pill is-active"
                  style={{ width: "100%", textAlign: "center" }}
                >
                  ⚡ 1-CLICK ADD MATCHING DECAL ($9.60) TO ACTIVE ORDER
                </button>
              ) : (
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--foundry-emerald)" }}>
                  {upsellConfirmMsg}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Express 1-Click Checkout Footer (Apple Pay / Google Pay / Link / para-paygate) */}
        <footer
          style={{
            padding: "1.25rem 1.5rem",
            borderTop: "1px solid var(--foundry-hairline)",
            background: "#0d0f13",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1.3fr 0.7fr",
              gap: "0.5rem",
              marginBottom: "0.65rem",
            }}
          >
            <input
              type="email"
              value={customerEmail}
              onChange={(e) => setCustomerEmail(e.target.value)}
              placeholder="Email for 120m grace window link"
              style={{
                padding: "0.5rem",
                background: "#0b0c0e",
                border: "1px solid var(--foundry-hairline)",
                color: "#f5f2eb",
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
              }}
            />
            <input
              type="text"
              value={customerZip}
              onChange={(e) => setCustomerZip(e.target.value)}
              placeholder="ZIP Code"
              style={{
                padding: "0.5rem",
                background: "#0b0c0e",
                border: "1px solid var(--foundry-hairline)",
                color: "#f5f2eb",
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
              }}
            />
          </div>

          <div
            className="foundry-pill-group"
            style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: "0.75rem" }}
          >
            {(["apple_pay", "google_pay", "link", "card"] as const).map((wm) => (
              <button
                key={wm}
                type="button"
                className={`foundry-pill ${walletMethod === wm ? "is-active" : ""}`}
                onClick={() => setWalletMethod(wm)}
                style={{ textAlign: "center", padding: "0.45rem 0.25rem", fontSize: "0.68rem" }}
              >
                {wm.replace("_", " ").toUpperCase()}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={handleExpressCheckout}
            disabled={submitting || items.length === 0}
            style={{
              width: "100%",
              padding: "0.95rem",
              background: "var(--foundry-vermilion)",
              color: "#ffffff",
              border: "none",
              fontFamily: "var(--font-mono)",
              fontWeight: 700,
              fontSize: "0.84rem",
              cursor: "pointer",
            }}
          >
            {submitting
              ? "ROUTING DUAL-PROVIDER ARBITRAGE..."
              : `1-CLICK EXPRESS CHECKOUT • $${(subtotalCents / 100).toFixed(2)} USD`}
          </button>
        </footer>
      </aside>
    </>
  );
};
