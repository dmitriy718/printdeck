import React, { useEffect, useRef, useState } from "react";

export interface ConciergeCard {
  card_type:
    | "PRODUCT_CARD"
    | "CUSTOM_MOCKUP_CARD"
    | "SHIPPING_QUOTE_CARD"
    | "STRIPE_EXPRESS_CHECKOUT_CARD"
    | "ORDER_GRACE_MODIFIED_CARD";
  sku?: string;
  title?: string;
  price_usd?: number;
  gsm_spec?: string;
  preview_in_room_url?: string;
  preview_id?: string;
  blank_sku?: string;
  color?: string;
  custom_inscription?: string;
  live_studio_url?: string;
  svg_badge?: string;
  zip_code?: string;
  winning_provider?: string;
  shipping_usd?: number;
  estimated_delivery_window?: string;
  order_id?: string;
  paygate_checkout_url?: string;
  total_usd?: number;
  grace_window_minutes?: number;
  applied_changes?: string[];
}

export interface ChatTurnMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  cards?: ConciergeCard[];
  toolCalls?: string[];
  firewallBlocked?: boolean;
}

export const PrintDeckConciergeChat: React.FC = () => {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [input, setInput] = useState<string>("");
  const [shippingZip, setShippingZip] = useState<string>("29601");
  const [customerEmail, setCustomerEmail] = useState<string>("collector@printdeck.net");
  const [loading, setLoading] = useState<boolean>(false);
  const [messages, setMessages] = useState<ChatTurnMessage[]>([
    {
      id: "welcome_01",
      role: "assistant",
      text:
        "Welcome to the PrintDeck Atelier. I'm your 24/7 AI Interior & Custom Print Specialist (`printdeck-concierge-32b`). Ask me to size a canvas for your sofa, preview custom text on a 280 GSM tee, calculate shipping, or complete a 1-click checkout right inside this chat!",
      cards: [],
    },
  ]);

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    try {
      const ws = new WebSocket(`${proto}//${window.location.host}/ws/chat/concierge`);
      ws.onmessage = (evt) => {
        try {
          const payload = JSON.parse(evt.data);
          setMessages((prev) => [
            ...prev,
            {
              id: `msg_${Date.now()}`,
              role: "assistant",
              text: payload.assistant_message,
              cards: payload.ui_cards || [],
              toolCalls: payload.tool_calls_executed || [],
              firewallBlocked: Boolean(payload.price_firewall?.blocked),
            },
          ]);
          setLoading(false);
        } catch {
          setLoading(false);
        }
      };
      wsRef.current = ws;
      return () => ws.close();
    } catch {
      return;
    }
  }, []);

  const sendMessage = async (overridePrompt?: string) => {
    const promptText = (overridePrompt ?? input).trim();
    if (!promptText) return;
    setInput("");
    setMessages((prev) => [
      ...prev,
      { id: `usr_${Date.now()}`, role: "user", text: promptText },
    ]);
    setLoading(true);

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          message: promptText,
          customer_email: customerEmail,
          shipping_zip: shippingZip,
        })
      );
      return;
    }

    try {
      const res = await fetch("/api/v2/chat/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: promptText,
          customer_email: customerEmail,
          shipping_zip: shippingZip,
        }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          id: `ast_${Date.now()}`,
          role: "assistant",
          text: data.assistant_message,
          cards: data.ui_cards || [],
          toolCalls: data.tool_calls_executed || [],
          firewallBlocked: Boolean(data.price_firewall?.blocked),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <aside
      id="printdeck-concierge-chat"
      data-testid="printdeck-concierge-chat"
      style={{
        position: "fixed",
        right: "1.5rem",
        bottom: "1.5rem",
        zIndex: 9999,
        fontFamily: "var(--font-sans, Inter, sans-serif)",
      }}
    >
      {!isOpen ? (
        <button
          onClick={() => setIsOpen(true)}
          data-testid="concierge-launcher-btn"
          style={{
            background: "#141413",
            color: "#F6F3EC",
            border: "1px solid #C59B5F",
            padding: "0.85rem 1.35rem",
            borderRadius: "999px",
            cursor: "pointer",
            fontWeight: 600,
            boxShadow: "0 12px 32px rgba(0,0,0,0.35)",
          }}
        >
          ✦ Atelier AI Concierge (24/7 Design &amp; Instant Order)
        </button>
      ) : (
        <div
          style={{
            width: "420px",
            maxHeight: "660px",
            display: "flex",
            flexDirection: "column",
            background: "#141413",
            color: "#F6F3EC",
            border: "1px solid #C59B5F",
            borderRadius: "14px",
            overflow: "hidden",
            boxShadow: "0 20px 50px rgba(0,0,0,0.55)",
          }}
        >
          <header
            style={{
              padding: "0.9rem 1.1rem",
              borderBottom: "1px solid rgba(197,155,95,0.28)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontSize: "0.7rem", color: "#C59B5F", letterSpacing: "0.08em" }}>
                PRINTDECK-CONCIERGE-32B • RAG (:8084) • PRICE FIREWALL ACTIVE
              </div>
              <strong style={{ fontSize: "1rem" }}>Atelier Design &amp; In-Chat Checkout</strong>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              style={{
                background: "transparent",
                color: "#F6F3EC",
                border: "none",
                cursor: "pointer",
                fontSize: "1.1rem",
              }}
            >
              ✕
            </button>
          </header>

          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "1rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.85rem",
            }}
          >
            {messages.map((m) => (
              <div
                key={m.id}
                style={{
                  alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                  maxWidth: "92%",
                  background: m.role === "user" ? "#C65D3B" : "#1E1E1C",
                  padding: "0.75rem 0.95rem",
                  borderRadius: "10px",
                  border: m.firewallBlocked ? "1px solid #E5484D" : "1px solid rgba(255,255,255,0.08)",
                }}
              >
                <div style={{ fontSize: "0.88rem", lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                  {m.text}
                </div>

                {m.cards &&
                  m.cards.map((card, i) => (
                    <div
                      key={`${m.id}_card_${i}`}
                      data-card-type={card.card_type}
                      style={{
                        marginTop: "0.65rem",
                        padding: "0.75rem",
                        background: "#121211",
                        border: "1px solid rgba(197,155,95,0.45)",
                        borderRadius: "8px",
                      }}
                    >
                      {card.card_type === "PRODUCT_CARD" && (
                        <div>
                          <div style={{ fontSize: "0.72rem", color: "#C59B5F" }}>
                            {card.sku} • {card.gsm_spec}
                          </div>
                          <div style={{ fontWeight: 600, margin: "0.2rem 0" }}>
                            {card.title} — ${card.price_usd?.toFixed(2)}
                          </div>
                          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.45rem" }}>
                            <a
                              href={card.preview_in_room_url || "/studio"}
                              style={{
                                fontSize: "0.75rem",
                                padding: "0.35rem 0.65rem",
                                background: "#C59B5F",
                                color: "#141413",
                                borderRadius: "4px",
                                textDecoration: "none",
                                fontWeight: 600,
                              }}
                            >
                              Preview in Room
                            </a>
                            <button
                              onClick={() =>
                                sendMessage(`Instant checkout for ${card.sku} to ZIP ${shippingZip}`)
                              }
                              style={{
                                fontSize: "0.75rem",
                                padding: "0.35rem 0.65rem",
                                background: "#2A2A27",
                                color: "#F6F3EC",
                                border: "1px solid #C59B5F",
                                borderRadius: "4px",
                                cursor: "pointer",
                              }}
                            >
                              1-Click Buy in Chat
                            </button>
                          </div>
                        </div>
                      )}

                      {card.card_type === "CUSTOM_MOCKUP_CARD" && (
                        <div>
                          <div style={{ fontSize: "0.7rem", color: "#4CC38A" }}>{card.svg_badge}</div>
                          <div style={{ fontWeight: 600, margin: "0.25rem 0" }}>
                            Live Custom Mockup: {card.blank_sku} ({card.color})
                          </div>
                          <div style={{ fontSize: "0.8rem", color: "#D6D1C4" }}>
                            Inscription: &ldquo;{card.custom_inscription}&rdquo;
                          </div>
                          <a
                            href={card.live_studio_url || "/studio"}
                            style={{
                              display: "inline-block",
                              marginTop: "0.45rem",
                              fontSize: "0.75rem",
                              padding: "0.35rem 0.65rem",
                              background: "#C59B5F",
                              color: "#141413",
                              borderRadius: "4px",
                              textDecoration: "none",
                              fontWeight: 600,
                            }}
                          >
                            Open Interactive 3D Mockup
                          </a>
                        </div>
                      )}

                      {card.card_type === "SHIPPING_QUOTE_CARD" && (
                        <div>
                          <div style={{ fontSize: "0.72rem", color: "#C59B5F" }}>
                            SMART ARBITRAGE ROUTER • {card.winning_provider?.toUpperCase()}
                          </div>
                          <div style={{ fontSize: "0.84rem", marginTop: "0.2rem" }}>
                            ZIP {card.zip_code}: <strong>${card.shipping_usd?.toFixed(2)}</strong> • ETA{" "}
                            <strong>{card.estimated_delivery_window}</strong>
                          </div>
                        </div>
                      )}

                      {card.card_type === "STRIPE_EXPRESS_CHECKOUT_CARD" && (
                        <div>
                          <div style={{ fontSize: "0.72rem", color: "#4CC38A" }}>
                            STRIPE + PARA-PAYGATE (:8790) • 120-MIN GRACE HOLD INCLUDED
                          </div>
                          <div style={{ fontWeight: 600, margin: "0.25rem 0" }}>
                            Order {card.order_id} — Total: ${card.total_usd?.toFixed(2)} USD
                          </div>
                          <a
                            href={card.paygate_checkout_url || "/pay/printdeck"}
                            data-testid="in-chat-stripe-pay-btn"
                            style={{
                              display: "inline-block",
                              marginTop: "0.4rem",
                              padding: "0.45rem 0.85rem",
                              background: "#4CC38A",
                              color: "#141413",
                              borderRadius: "5px",
                              textDecoration: "none",
                              fontWeight: 700,
                              fontSize: "0.8rem",
                            }}
                          >
                            Pay ${card.total_usd?.toFixed(2)} Instantly (1-Click Stripe)
                          </a>
                        </div>
                      )}

                      {card.card_type === "ORDER_GRACE_MODIFIED_CARD" && (
                        <div>
                          <div style={{ fontSize: "0.72rem", color: "#4CC38A" }}>
                            120-MINUTE GRACE WINDOW EDIT CONFIRMED ({card.order_id})
                          </div>
                          <div style={{ fontSize: "0.8rem", marginTop: "0.2rem" }}>
                            {card.applied_changes?.join(" • ")}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            ))}
            {loading && (
              <div style={{ fontSize: "0.78rem", color: "#C59B5F" }}>
                printdeck-concierge-32b is consulting catalog &amp; arbitrage router...
              </div>
            )}
          </div>

          <footer
            style={{
              padding: "0.75rem",
              borderTop: "1px solid rgba(197,155,95,0.28)",
              display: "flex",
              gap: "0.5rem",
            }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Ask about sofa sizing, custom quotes, or 1-click order..."
              style={{
                flex: 1,
                background: "#1E1E1C",
                color: "#F6F3EC",
                border: "1px solid rgba(197,155,95,0.4)",
                borderRadius: "6px",
                padding: "0.55rem 0.75rem",
                fontSize: "0.84rem",
              }}
            />
            <button
              onClick={() => sendMessage()}
              style={{
                background: "#C59B5F",
                color: "#141413",
                border: "none",
                borderRadius: "6px",
                padding: "0.55rem 0.9rem",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Send
            </button>
          </footer>
        </div>
      )}
    </aside>
  );
};

export default PrintDeckConciergeChat;
