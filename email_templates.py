#!/usr/bin/env python3
"""
PrintDeck (`printdeck.net`) — Phase 7 Transactional & 3-Stage Abandoned Cart Recovery
HTML / Plain-Text Email Templates (`email_templates.py`).

Enforces:
  - `A2 Deliverability` DKIM/SPF/DMARC header alignment (`From: PrintDeck Atelier <concierge@printdeck.net>`)
  - Mandatory RFC 8058 1-Click Unsubscribe headers wired to `para-paygate.service` (`/pay/optout`):
    `List-Unsubscribe: <https://printdeck.net/pay/optout?email=...&token=...>`
    `List-Unsubscribe-Post: List-Unsubscribe=One-Click`
"""

from __future__ import annotations

import dataclasses
import html
from typing import Dict
from urllib.parse import quote


@dataclasses.dataclass
class RenderedEmailPayload:
    template_id: str
    recipient_email: str
    subject: str
    html_body: str
    text_body: str
    headers: Dict[str, str]

    def to_dict(self) -> Dict[str, object]:
        return dataclasses.asdict(self)


def build_rfc8058_headers(
    recipient_email: str,
    unsubscribe_token: str,
    campaign_id: str,
) -> Dict[str, str]:
    encoded_email = quote(recipient_email.strip().lower())
    encoded_tok = quote(unsubscribe_token.strip())
    optout_url = f"https://printdeck.net/pay/optout?email={encoded_email}&token={encoded_tok}"
    return {
        "From": "PrintDeck Tactile Atelier <concierge@printdeck.net>",
        "Reply-To": "support@printdeck.net",
        "List-Unsubscribe": f"<{optout_url}>, <mailto:optout@printdeck.net?subject=unsubscribe>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        "X-PrintDeck-Campaign": campaign_id,
        "X-Para-DKIM-Domain": "printdeck.net",
        "X-Para-DMARC-Policy": "v=DMARC1; p=quarantine; pct=100",
    }


def render_abandoned_cart_stage(
    stage: str,  # 'T30M' | 'T6H' | 'T24H'
    recipient_email: str,
    customer_name: str,
    item_title: str,
    master_sku: str,
    resume_checkout_url: str,
    unsubscribe_token: str,
    promo_code: str = "ATELIER10",
) -> RenderedEmailPayload:
    """
    Renders the 3-Stage Abandoned Cart & Checkout Recovery sequence:
      - `T30M`: Helpful concierge check-in ("Did your custom preview render properly?")
      - `T6H`: Social proof + high-res room mockup preview of the exact item
      - `T24H`: Margin-approved dynamic incentive (free expedited shipping or 10% Stripe promo code)
    """
    headers = build_rfc8058_headers(
        recipient_email=recipient_email,
        unsubscribe_token=unsubscribe_token,
        campaign_id=f"abandoned_cart_{stage.lower()}",
    )
    optout_url = f"https://printdeck.net/pay/optout?email={quote(recipient_email)}&token={quote(unsubscribe_token)}"
    mockup_url = f"https://printdeck.net/assets/mockups/{master_sku.lower()}-gallery-preview.avif"

    if stage == "T30M":
        subject = f"Did your 300-DPI preview render properly, {customer_name}?"
        headline = "Did your custom preview render properly?"
        lead_copy = (
            f"Here is a direct link back to your exact canvas/studio configuration for "
            f"{item_title} ({master_sku}). Our WebGL Spatial Studio saved your lighting and frame settings."
        )
        cta_label = "Return to Your Exact Studio Configuration"
    elif stage == "T6H":
        subject = f"Your {item_title} in Modern Loft Gallery Lighting (Saved Preview)"
        headline = f"See how {item_title} anchors a room"
        lead_copy = (
            f"Every PrintDeck piece is soft-proofed at a strict 300 DPI and backed by our "
            f"120-minute post-checkout editable grace window. View your high-resolution room mockup below."
        )
        cta_label = "Resume 1-Click Express Checkout"
    else:  # T24H
        subject = f"Complimentary Expedited Shipping or 10% Atelier Privilege ({promo_code})"
        headline = f"Complete your {item_title} order with code {promo_code}"
        lead_copy = (
            f"We reserved blank inventory at our regional print hub for your {item_title}. "
            f"Use single-use Stripe code {promo_code} for 10% off (or complimentary expedited shipping) "
            f"within the next 24 hours."
        )
        cta_label = f"Apply {promo_code} at 1-Click Stripe Checkout"

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<body style="font-family: 'Inter', -apple-system, sans-serif; background:#0d0e11; color:#f4f0e8; padding:32px;">
  <div style="max-width:600px; margin:0 auto; background:#15171c; border:1px solid #2b2f3a; padding:28px;">
    <p style="font-size:12px; letter-spacing:0.12em; text-transform:uppercase; color:#c65d3b;">PrintDeck Tactile Atelier</p>
    <h1 style="font-size:22px; margin:8px 0 16px;">{html.escape(headline)}</h1>
    <p style="line-height:1.6; color:#d5d0c5;">{html.escape(lead_copy)}</p>
    <div style="margin:20px 0;">
      <img src="{html.escape(mockup_url)}" alt="{html.escape(item_title)} 300-DPI Room Mockup" style="max-width:100%; border:1px solid #2b2f3a;" />
    </div>
    <p style="margin:24px 0;">
      <a href="{html.escape(resume_checkout_url)}" style="background:#c65d3b; color:#ffffff; padding:12px 22px; text-decoration:none; font-weight:600;">{html.escape(cta_label)}</a>
    </p>
    <hr style="border:none; border-top:1px solid #2b2f3a; margin:24px 0;" />
    <p style="font-size:12px; color:#8e929f;">
      Prefer no further studio reminders? <a href="{html.escape(optout_url)}" style="color:#d5d0c5;">1-Click Unsubscribe</a>.
    </p>
  </div>
</body>
</html>"""

    text_body = (
        f"PrintDeck Tactile Atelier\n\n"
        f"{headline}\n\n"
        f"{lead_copy}\n\n"
        f"{cta_label}: {resume_checkout_url}\n\n"
        f"---\n"
        f"1-Click Unsubscribe: {optout_url}\n"
    )

    return RenderedEmailPayload(
        template_id=f"ABANDONED_CART_{stage}",
        recipient_email=recipient_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        headers=headers,
    )


def render_transactional_lifecycle_email(
    event_type: str,  # 'ORDER_CONFIRMATION' | 'SHIPMENT_TRACKING' | 'DAY14_REVIEW_WINBACK'
    recipient_email: str,
    customer_name: str,
    order_number: str,
    unsubscribe_token: str,
    tracking_url: str = "",
    carrier: str = "UPS Ground",
    repeat_reward_code: str = "COLLECTOR15",
) -> RenderedEmailPayload:
    headers = build_rfc8058_headers(
        recipient_email=recipient_email,
        unsubscribe_token=unsubscribe_token,
        campaign_id=f"lifecycle_{event_type.lower()}",
    )
    optout_url = f"https://printdeck.net/pay/optout?email={quote(recipient_email)}&token={quote(unsubscribe_token)}"

    if event_type == "ORDER_CONFIRMATION":
        subject = f"Order {order_number} Confirmed — Your 120-Minute Editable Grace Window is Active"
        headline = f"Thank you, {customer_name}. Order {order_number} is in its 2-Hour Grace Hold."
        body_text = (
            "Your artwork has passed 300-DPI pre-flight verification. For the next 120 minutes, "
            "you can freely edit your shipping address, swap sizes/frame finishes, or add a matching "
            "atelier piece at 20% off with zero reprint fee before our arbitrage router dispatches "
            "your order to production."
        )
        action_url = f"https://printdeck.net/orders/{order_number}/grace-edit"
        action_label = "View or Edit Order in 120-Minute Grace Window"
    elif event_type == "SHIPMENT_TRACKING":
        subject = f"Dispatched from Foundry: Order {order_number} has Shipped via {carrier}"
        headline = f"Your PrintDeck order {order_number} is on the move."
        body_text = (
            f"Your 300-DPI print has cleared final quality inspection and shipped via {carrier}. "
            f"Track your package in real time below."
        )
        action_url = tracking_url or f"https://printdeck.net/orders/{order_number}/track"
        action_label = f"Track {carrier} Shipment"
    else:  # DAY14_REVIEW_WINBACK
        subject = f"How does Order {order_number} look in your space? (+15% Collector Privilege)"
        headline = f"Share a photo of Order {order_number} & claim {repeat_reward_code}"
        body_text = (
            f"We hope your piece from Order {order_number} is anchoring your wall or desk. "
            f"Reply with a photo of your setup or leave a verified review to unlock {repeat_reward_code} "
            f"(15% off your next archival print)."
        )
        action_url = f"https://printdeck.net/orders/{order_number}/review?code={repeat_reward_code}"
        action_label = "Submit Photo Review & Claim Collector Reward"

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<body style="font-family: 'Inter', -apple-system, sans-serif; background:#0d0e11; color:#f4f0e8; padding:32px;">
  <div style="max-width:600px; margin:0 auto; background:#15171c; border:1px solid #2b2f3a; padding:28px;">
    <p style="font-size:12px; letter-spacing:0.12em; text-transform:uppercase; color:#c65d3b;">PrintDeck Order Concierge</p>
    <h1 style="font-size:20px; margin:8px 0 16px;">{html.escape(headline)}</h1>
    <p style="line-height:1.6; color:#d5d0c5;">{html.escape(body_text)}</p>
    <p style="margin:24px 0;">
      <a href="{html.escape(action_url)}" style="background:#c65d3b; color:#ffffff; padding:12px 22px; text-decoration:none; font-weight:600;">{html.escape(action_label)}</a>
    </p>
    <hr style="border:none; border-top:1px solid #2b2f3a; margin:24px 0;" />
    <p style="font-size:12px; color:#8e929f;">
      <a href="{html.escape(optout_url)}" style="color:#d5d0c5;">Manage email preferences / 1-Click Opt-Out</a>
    </p>
  </div>
</body>
</html>"""

    text_body = (
        f"{headline}\n\n{body_text}\n\n{action_label}: {action_url}\n\n"
        f"Unsubscribe: {optout_url}\n"
    )

    return RenderedEmailPayload(
        template_id=f"LIFECYCLE_{event_type}",
        recipient_email=recipient_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        headers=headers,
    )
