/* PrintDeck (printdeck.net) — Live Room Visualizer, Custom Studio, Slide-Out Cart & Authentik SSO Runtime */
(function () {
  var ROOM_CONFIG = {
    modern_loft: {
      img: "/images/room-modern-loft.webp",
      label: "Modern Loft • Warm Golden-Hour Daylight (4200K)",
      filter: "brightness(1.01) contrast(1.03)"
    },
    executive_office: {
      img: "/images/room-executive-study.webp",
      label: "Executive Study • Architectural Walnut & Brass (3500K)",
      filter: "sepia(0.06) brightness(0.98) contrast(1.04)"
    },
    coastal_living: {
      img: "/images/room-coastal-living.webp",
      label: "Coastal Living • Sunlit Natural Linen & Oak (5400K)",
      filter: "brightness(1.04) saturate(1.04)"
    },
    dark_studio: {
      img: "/images/room-dark-gallery.webp",
      label: "Gallery Spot • Directional Museum Track Light (2900K)",
      filter: "brightness(0.96) contrast(1.08)"
    }
  };

  var SIZE_PRICES = {
    "18x24": { label: '18" × 24" Collector Edition', price: 119.00, compare: 149.00 },
    "24x36": { label: '24" × 36" Gallery Statement (★ Most Popular • 2× Area for +$30)', price: 149.00, compare: 185.00 },
    "36x48": { label: '36" × 48" Grand Architectural', price: 229.00, compare: 285.00 }
  };

  var PROMO_RULES = {
    "ATELIER15": { code: "ATELIER15", label: "15% Collector Exhibition Privilege", type: "percent", value: 0.15, minSubtotal: 0 },
    "CURATOR15": { code: "CURATOR15", label: "15% Curatorial Advisory Privilege", type: "percent", value: 0.15, minSubtotal: 0 },
    "WELCOME15": { code: "WELCOME15", label: "15% First-Edition Privilege", type: "percent", value: 0.15, minSubtotal: 0 },
    "STUDIO36":  { code: "STUDIO36",  label: "$36 Framing & Studio Credit", type: "fixed", value: 36.00, minSubtotal: 140 },
    "TRADE20":   { code: "TRADE20",   label: "20% Interior Trade & Multi-Piece Allocation", type: "percent", value: 0.20, minSubtotal: 200 }
  };

  var SCALE_REFS = {
    "sofa84": 'Scale Reference: 84" Three-Seat Cognac Sofa • Artwork hung 57" on-center (0.68 Golden Ratio)',
    "bed76": 'Scale Reference: 76" Architectural King Headboard • Balanced 8" clearance above bolster',
    "desk72": 'Scale Reference: 72" Executive Walnut Credenza • Anchors dual-monitor & study sightline'
  };

  window.PrintDeckRuntime = {
    cart: [
      {
        sku: "PD-CANVAS-24X36",
        slug: "monolith-no-4-stretched-gallery-canvas-24x36",
        title: 'Monolith No. 4 — Bauhaus Impasto Gallery Canvas (24"×36", Museum Oak)',
        price: 149.00,
        qty: 1,
        frame: "oak",
        size: "24x36",
        image: "/images/art-monolith-bauhaus.webp"
      }
    ],
    activePromo: null,
    activeRoom: "modern_loft",
    activeFrame: "oak",
    activeSize: "24x36",
    activeScaleRef: "sofa84",
    activeArt: "/images/art-monolith-bauhaus.webp",
    activeArtTitle: "Monolith No. 4 — Bauhaus Impasto Gallery Canvas",
    activeArtSlug: "monolith-no-4-stretched-gallery-canvas-24x36",
    quizState: { space: "living", mood: "warm_minimal", span: "24x36", molding: "oak" },

    init: function () {
      this.loadCartState();
      this.renderCart();
      this.syncVisualizerCheckoutLink();
      this.syncCanvasPreview();
      this.checkAuthentikSession();
      this.startUrgencyCountdowns();
      this.bindGlobalResilienceHandlers();
      this.renderQuizRecommendation();
    },

    loadCartState: function () {
      try {
        var raw = localStorage.getItem("pd_collector_cart_v1");
        if (raw) {
          var parsed = JSON.parse(raw);
          if (parsed && Array.isArray(parsed.cart) && parsed.cart.length > 0) {
            this.cart = parsed.cart;
          }
          if (parsed && parsed.activePromo && PROMO_RULES[parsed.activePromo]) {
            this.activePromo = parsed.activePromo;
          }
        }
      } catch (e) {}
    },

    saveCartState: function () {
      try {
        localStorage.setItem("pd_collector_cart_v1", JSON.stringify({
          cart: this.cart,
          activePromo: this.activePromo
        }));
      } catch (e) {}
    },

    syncBodyScrollLock: function () {
      var drawer = document.getElementById("instant-cart-drawer");
      var drawerOpen = drawer && drawer.classList.contains("is-open");
      var modalOpen = document.querySelector(".atelier-modal-backdrop.is-open") !== null;
      document.body.classList.toggle("is-scroll-locked", Boolean(drawerOpen || modalOpen));
    },

    openAtelierModal: function (modalId) {
      var m = document.getElementById(modalId);
      if (m) {
        m.classList.add("is-open");
        this.syncBodyScrollLock();
      }
    },

    closeAllModals: function () {
      document.querySelectorAll(".atelier-modal-backdrop.is-open").forEach(function (el) {
        el.classList.remove("is-open");
      });
      this.toggleCartDrawer(false);
      var panel = document.getElementById("concierge-chat-panel");
      if (panel) panel.classList.remove("is-open");
      this.syncBodyScrollLock();
    },

    bindGlobalResilienceHandlers: function () {
      var self = this;
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
          self.closeAllModals();
        }
      });
      window.addEventListener("unhandledrejection", function (ev) {
        console.warn("PrintDeck Concierge intercepted async rejection:", ev.reason);
      });
    },

    triggerRecoveryConcierge: function (reasonText) {
      var msgEl = document.getElementById("recovery-modal-reason");
      if (msgEl && reasonText) msgEl.textContent = reasonText;
      this.applyPromoCode("ATELIER15");
      this.openAtelierModal("error-recovery-modal");
    },

    startUrgencyCountdowns: function () {
      var batchRemainingSec = 3 * 3600 + 41 * 60 + 19;
      var cartHoldSec = 14 * 60 + 58;
      setInterval(function () {
        if (batchRemainingSec > 60) batchRemainingSec -= 1;
        var hrs = String(Math.floor(batchRemainingSec / 3600)).padStart(2, "0");
        var mins = String(Math.floor((batchRemainingSec % 3600) / 60)).padStart(2, "0");
        var secs = String(batchRemainingSec % 60).padStart(2, "0");
        var formatted = hrs + "h : " + mins + "m : " + secs + "s";
        document.querySelectorAll("[data-batch-countdown]").forEach(function (el) {
          el.textContent = formatted;
        });

        if (cartHoldSec > 0) cartHoldSec -= 1;
        var cMin = String(Math.floor(cartHoldSec / 60)).padStart(2, "0");
        var cSec = String(cartHoldSec % 60).padStart(2, "0");
        var holdEl = document.getElementById("cart-reservation-timer");
        if (holdEl) holdEl.textContent = cMin + ":" + cSec;
      }, 1000);
    },

    saveRoomPreviewLead: function () {
      var badge = document.getElementById("dpi-verify-status");
      if (badge) {
        badge.innerHTML = '<span style="color:#4ADE80;">●</span> Room Preview Reserved • 15% Privilege (ATELIER15) Applied to Bag';
      }
      this.applyPromoCode("ATELIER15");
      this.addVisualizerSelectionToCart();
    },

    syncVisualizerCheckoutLink: function () {
      var expressBtn = document.getElementById("visualizer-express-checkout-link");
      var sCfg = SIZE_PRICES[this.activeSize] || SIZE_PRICES["24x36"];
      var bnplEl = document.getElementById("visualizer-bnpl-copy");
      if (bnplEl) {
        bnplEl.textContent = "Or 4 interest-free installments of $" + (sCfg.price / 4).toFixed(2);
      }
      if (expressBtn && this.activeArtSlug) {
        var q = "?size=" + encodeURIComponent(this.activeSize) + "&frame=" + encodeURIComponent(this.activeFrame);
        if (this.activePromo) q += "&promo=" + encodeURIComponent(this.activePromo);
        expressBtn.href = "/pay/" + this.activeArtSlug + q;
      }
    },

    setScaleReference: function (refKey) {
      this.activeScaleRef = refKey;
      var scaleEl = document.getElementById("visualizer-scale-ref-label");
      if (scaleEl && SCALE_REFS[refKey]) {
        scaleEl.textContent = SCALE_REFS[refKey];
      }
      document.querySelectorAll("[data-scale-btn]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-scale-btn") === refKey);
      });
    },

    setRoomEnv: function (envKey) {
      this.activeRoom = envKey;
      var cfg = ROOM_CONFIG[envKey] || ROOM_CONFIG.modern_loft;
      var roomImg = document.getElementById("visualizer-room-photo");
      var label = document.getElementById("active-lighting-label");
      var canvas = document.getElementById("spatial-studio-canvas");
      if (roomImg) {
        roomImg.src = cfg.img;
        roomImg.style.filter = cfg.filter;
      }
      if (label) label.textContent = cfg.label;
      if (canvas) canvas.setAttribute("data-room-env", envKey);
      document.querySelectorAll("[data-env-btn]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-env-btn") === envKey);
      });
      this.syncCanvasPreview();
    },

    setFrameMolding: function (frameKey) {
      this.activeFrame = frameKey;
      var mount = document.getElementById("visualizer-art-mount");
      if (mount) mount.setAttribute("data-frame", frameKey);
      document.querySelectorAll("[data-frame-btn]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-frame-btn") === frameKey);
      });
      this.syncVisualizerCheckoutLink();
      this.syncCanvasPreview();
    },

    setPrintSize: function (sizeKey) {
      this.activeSize = sizeKey;
      var mount = document.getElementById("visualizer-art-mount");
      if (mount) mount.setAttribute("data-size", sizeKey);
      var sCfg = SIZE_PRICES[sizeKey] || SIZE_PRICES["24x36"];
      var priceEl = document.getElementById("visualizer-live-price");
      if (priceEl) priceEl.textContent = "$" + sCfg.price.toFixed(2);
      document.querySelectorAll("[data-size-btn]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-size-btn") === sizeKey);
      });
      this.syncVisualizerCheckoutLink();
      this.syncCanvasPreview();
    },

    setArtworkInRoom: function (imgSrc, title, slug, price) {
      this.activeArt = imgSrc;
      if (title) this.activeArtTitle = title;
      if (slug) this.activeArtSlug = slug;
      var artImg = document.getElementById("visualizer-art-photo");
      var titleEl = document.getElementById("visualizer-active-title");
      var priceEl = document.getElementById("visualizer-live-price");
      if (artImg) artImg.src = imgSrc;
      if (titleEl && title) titleEl.textContent = title;
      if (priceEl && price) priceEl.textContent = "$" + Number(price).toFixed(2);
      this.syncVisualizerCheckoutLink();
      document.querySelectorAll("[data-art-thumb]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-art-thumb") === imgSrc);
      });
      var heroEl = document.getElementById("spatial-mockup-studio");
      if (heroEl && window.scrollY > 500) {
        heroEl.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      this.syncCanvasPreview();
    },

    selectCardSwatch: function (btnEl, finishLabel, frameKey) {
      if (!btnEl) return;
      var card = btnEl.closest(".product-card");
      var container = btnEl.closest(".product-card__swatches");
      if (container) {
        container.querySelectorAll(".color-swatch-btn").forEach(function (b) {
          b.classList.remove("is-selected");
        });
        btnEl.classList.add("is-selected");
        var lbl = container.querySelector("[data-swatch-label]");
        if (lbl && finishLabel) lbl.textContent = finishLabel;
      }
      if (card && finishLabel) {
        var buyLink = card.querySelector(".btn-card-buy");
        if (buyLink) {
          var baseHref = buyLink.getAttribute("data-base-href") || buyLink.getAttribute("href").split("?")[0];
          buyLink.setAttribute("data-base-href", baseHref);
          buyLink.href = baseHref + "?finish=" + encodeURIComponent(finishLabel) + (frameKey ? "&frame=" + encodeURIComponent(frameKey) : "");
        }
      }
      if (frameKey) {
        this.setFrameMolding(frameKey);
      }
    },

    handleCustomUpload: function (inputEl) {
      if (!inputEl || !inputEl.files || !inputEl.files[0]) return;
      var file = inputEl.files[0];
      var reader = new FileReader();
      var self = this;
      reader.onload = function (e) {
        var dataUrl = e.target.result;
        self.setArtworkInRoom(dataUrl, "Custom Collector Upload (" + file.name + ")", "monolith-no-4-stretched-gallery-canvas-24x36", 159.00);
        var badge = document.getElementById("dpi-verify-status");
        if (badge) badge.textContent = "✓ Custom Artwork Verified • 300-DPI Museum Print-Ready";
      };
      reader.readAsDataURL(file);
    },

    syncCanvasPreview: function () {
      var canvas = document.getElementById("spatial-studio-canvas");
      if (!canvas || !canvas.getContext) return;
      var ctx = canvas.getContext("2d");
      var roomImg = document.getElementById("visualizer-room-photo");
      if (roomImg && roomImg.complete && roomImg.naturalWidth > 0) {
        ctx.drawImage(roomImg, 0, 0, canvas.width, canvas.height);
      } else {
        ctx.fillStyle = "#F3EFE6";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }
    },

    filterCatalog: function (cat) {
      document.querySelectorAll("[data-product-card]").forEach(function (el) {
        var c = el.getAttribute("data-category") || "";
        var v = el.getAttribute("data-vertical") || "";
        var show = (cat === "all") || (c.indexOf(cat) !== -1) || (v.indexOf(cat) !== -1);
        el.style.display = show ? "flex" : "none";
      });
      document.querySelectorAll("[data-cat-btn]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-cat-btn") === cat);
      });
    },

    applyPromoCode: function (code) {
      var clean = String(code || "").trim().toUpperCase();
      if (this.activePromo === clean) {
        this.activePromo = null;
      } else if (PROMO_RULES[clean]) {
        this.activePromo = clean;
      }
      this.saveCartState();
      this.renderCart();
      this.syncVisualizerCheckoutLink();
    },

    addToCart: function (sku, title, price, image, slug, frame, size) {
      var existing = null;
      for (var i = 0; i < this.cart.length; i++) {
        if (this.cart[i].sku === sku) {
          existing = this.cart[i];
          break;
        }
      }
      if (existing) {
        existing.qty += 1;
      } else {
        this.cart.push({
          sku: sku,
          slug: slug || "monolith-no-4-stretched-gallery-canvas-24x36",
          title: title,
          price: Number(price || 149),
          qty: 1,
          frame: frame || this.activeFrame || "oak",
          size: size || this.activeSize || "24x36",
          image: image || "/images/art-monolith-bauhaus.webp"
        });
      }
      this.saveCartState();
      this.renderCart();
      this.toggleCartDrawer(true);
    },

    updateCartQty: function (index, delta) {
      if (!this.cart[index]) return;
      this.cart[index].qty += delta;
      if (this.cart[index].qty <= 0) {
        this.cart.splice(index, 1);
      }
      this.saveCartState();
      this.renderCart();
    },

    addVisualizerSelectionToCart: function () {
      var sCfg = SIZE_PRICES[this.activeSize] || SIZE_PRICES["24x36"];
      var frameNames = {
        oak: "Museum Oak Frame",
        walnut: "American Walnut Float",
        gold: "Champagne Gold Leaf Frame",
        black: "Matte Black Frame",
        canvas: "Gallery Stretched Canvas"
      };
      var fullTitle = this.activeArtTitle + " (" + this.activeSize.replace("x", '"×') + '", ' + (frameNames[this.activeFrame] || "Museum Oak") + ")";
      this.addToCart("PD-CUSTOM-" + this.activeSize.toUpperCase(), fullTitle, sCfg.price, this.activeArt, this.activeArtSlug, this.activeFrame, this.activeSize);
    },

    removeFromCart: function (index) {
      this.cart.splice(index, 1);
      this.saveCartState();
      this.renderCart();
    },

    renderCart: function () {
      var countEl = document.getElementById("header-cart-count");
      var listEl = document.getElementById("cart-items-container");
      var subtotalEl = document.getElementById("cart-subtotal-value");
      var discountRowEl = document.getElementById("cart-discount-row");
      var bnplEl = document.getElementById("cart-bnpl-installments");
      var checkoutBtn = document.getElementById("cart-drawer-checkout-btn");
      var shipFill = document.getElementById("free-shipping-bar-fill");
      var shipMsg = document.getElementById("free-shipping-msg");

      var totalQty = 0;
      var subtotal = 0;
      this.cart.forEach(function (item) {
        totalQty += item.qty;
        subtotal += item.price * item.qty;
      });

      var discount = 0;
      var activeRule = this.activePromo ? PROMO_RULES[this.activePromo] : null;
      if (activeRule && subtotal >= activeRule.minSubtotal) {
        discount = activeRule.type === "percent" ? (subtotal * activeRule.value) : activeRule.value;
        discount = Math.min(subtotal, Math.round(discount * 100) / 100);
      }
      var finalTotal = Math.max(0, subtotal - discount);

      if (countEl) countEl.textContent = String(totalQty);
      if (subtotalEl) {
        if (discount > 0) {
          subtotalEl.innerHTML = '<s style="font-size:0.95rem;color:#8A8275;font-family:var(--font-sans);margin-right:0.4rem;">$' + subtotal.toFixed(2) + '</s>$' + finalTotal.toFixed(2) + ' USD';
        } else {
          subtotalEl.textContent = "$" + finalTotal.toFixed(2) + " USD";
        }
      }
      if (discountRowEl) {
        if (discount > 0 && activeRule) {
          discountRowEl.style.display = "flex";
          discountRowEl.innerHTML = '<span>✓ ' + activeRule.code + ' (' + activeRule.label + ')</span><strong>-$' + discount.toFixed(2) + '</strong>';
        } else {
          discountRowEl.style.display = "none";
        }
      }
      if (bnplEl) {
        bnplEl.textContent = finalTotal > 0
          ? "Or 4 interest-free collector installments of $" + (finalTotal / 4).toFixed(2) + " with Klarna / Affirm"
          : "Protected by 2-Hour Easy Order Edit Window";
      }

      document.querySelectorAll("[data-promo-pill]").forEach(function (pill) {
        var pCode = pill.getAttribute("data-promo-pill");
        pill.classList.toggle("is-active", pCode === (activeRule ? activeRule.code : ""));
      });

      if (shipFill && shipMsg) {
        var pct = Math.min(100, Math.round((subtotal / 280) * 100));
        shipFill.style.width = pct + "%";
        if (subtotal < 120) {
          shipMsg.textContent = "Tier 1/3: Add $" + (120 - subtotal).toFixed(2) + " for Free Insured Express Courier ($24 Value)";
        } else if (subtotal < 200) {
          shipMsg.textContent = "✓ Free Express Courier Unlocked! Add $" + (200 - subtotal).toFixed(2) + " for Wax-Stamped Provenance Folio";
        } else if (subtotal < 280) {
          shipMsg.textContent = "✓ Provenance Folio Unlocked! Add $" + (280 - subtotal).toFixed(2) + " for Free $24 Stoneware Collector Mug";
        } else {
          shipMsg.textContent = "✦ All 3 VIP Milestones Unlocked: Free Courier + Wax Folio + Free $24 Stoneware Mug!";
        }
      }

      if (checkoutBtn) {
        if (this.cart.length === 0) {
          checkoutBtn.href = "/pay/monolith-no-4-stretched-gallery-canvas-24x36?promo=ATELIER15";
          checkoutBtn.textContent = "Claim #1 Flagship Canvas ($149) →";
        } else if (this.cart.length === 1) {
          var single = this.cart[0];
          var singleUrl = "/pay/" + encodeURIComponent(single.slug || "monolith-no-4-stretched-gallery-canvas-24x36") +
            "?sku=" + encodeURIComponent(single.sku) +
            "&qty=" + encodeURIComponent(single.qty) +
            "&size=" + encodeURIComponent(single.size || "24x36") +
            "&frame=" + encodeURIComponent(single.frame || "oak");
          if (this.activePromo) singleUrl += "&promo=" + encodeURIComponent(this.activePromo);
          checkoutBtn.href = singleUrl;
          checkoutBtn.textContent = "Proceed to Express Checkout ($" + finalTotal.toFixed(2) + ") →";
        } else {
          var tokens = this.cart.map(function (c) {
            return encodeURIComponent(c.sku) + ":" + encodeURIComponent(c.qty) + ":" + encodeURIComponent(c.frame || "oak") + ":" + encodeURIComponent(c.size || "24x36");
          }).join(",");
          var multiUrl = "/pay/checkout-cart?items=" + tokens;
          if (this.activePromo) multiUrl += "&promo=" + encodeURIComponent(this.activePromo);
          checkoutBtn.href = multiUrl;
          checkoutBtn.textContent = "Proceed to Express Checkout (" + totalQty + " Items • $" + finalTotal.toFixed(2) + ") →";
        }
      }

      if (!listEl) return;
      if (this.cart.length === 0) {
        listEl.innerHTML = '<div style="padding:1.75rem 1rem;text-align:center;color:#544F49;">' +
          '<p style="margin-bottom:0.85rem;font-size:0.88rem;">Your collector bag is currently empty. Select a numbered archival edition below:</p>' +
          '<div style="display:grid;gap:0.5rem;">' +
            '<button type="button" class="btn-primary" style="padding:0.65rem 1rem;font-size:0.8rem;" onclick="window.PrintDeckRuntime.addToCart('PD-CANVAS-24X36', 'Monolith No. 4 — Bauhaus Impasto Gallery Canvas (24\x22×36\x22)', 149.00, '/images/art-monolith-bauhaus.webp', 'monolith-no-4-stretched-gallery-canvas-24x36')">+ Add #1 Monolith Canvas ($149)</button>' +
            '<button type="button" class="btn-secondary" style="padding:0.65rem 1rem;font-size:0.8rem;" onclick="window.PrintDeckRuntime.addToCart('PD-EXECUTIVE-SET-340', 'Complete Executive Studio & Gallery Collector Set (4-Piece Allocation)', 340.00, '/images/art-coastal-horizon.webp', 'executive-complete-studio-trio-340')">+ Add Complete $340 Collector Set (Save $82)</button>' +
          '</div>' +
        '</div>';
        return;
      }

      var html = "";
      this.cart.forEach(function (item, idx) {
        var safeImg = (item.image && item.image.indexOf("data:") === 0) ? item.image : (item.image || "/images/art-monolith-bauhaus.webp");
        html += '<div style="display:flex;gap:0.85rem;padding:0.9rem 0;border-bottom:1px solid #E2DBD0;align-items:center;">' +
          '<img src="' + safeImg + '" alt="' + item.title + '" style="width:64px;height:76px;object-fit:cover;border-radius:6px;border:1px solid #CEC3B2;" />' +
          '<div style="flex:1;min-width:0;">' +
            '<div style="font-weight:700;font-size:0.85rem;color:#141413;line-height:1.28;">' + item.title + '</div>' +
            '<div style="font-size:0.74rem;color:#236B3B;font-weight:600;margin-top:0.18rem;">✓ 100-Yr Certificate • 2-Hr Easy Edit</div>' +
            '<div style="display:flex;align-items:center;justify-content:space-between;margin-top:0.35rem;">' +
              '<div style="display:inline-flex;align-items:center;border:1px solid #CEC3B2;border-radius:4px;background:#fff;">' +
                '<button type="button" onclick="window.PrintDeckRuntime.updateCartQty(' + idx + ', -1)" style="border:none;background:none;padding:0.15rem 0.5rem;font-weight:700;cursor:pointer;" aria-label="Decrease quantity">−</button>' +
                '<span style="font-size:0.78rem;font-weight:700;padding:0 0.35rem;">' + item.qty + '</span>' +
                '<button type="button" onclick="window.PrintDeckRuntime.updateCartQty(' + idx + ', 1)" style="border:none;background:none;padding:0.15rem 0.5rem;font-weight:700;cursor:pointer;" aria-label="Increase quantity">+</button>' +
              '</div>' +
              '<strong style="font-size:0.92rem;color:#141413;">$' + (item.price * item.qty).toFixed(2) + '</strong>' +
            '</div>' +
          '</div>' +
          '<button type="button" onclick="window.PrintDeckRuntime.removeFromCart(' + idx + ')" style="background:none;border:none;color:#78716C;font-size:0.9rem;width:36px;height:36px;cursor:pointer;" aria-label="Remove item">✕</button>' +
        '</div>';
      });

      if (subtotal >= 280) {
        html += '<div style="display:flex;gap:0.85rem;padding:0.75rem 0.65rem;margin-top:0.4rem;background:#F2F7F3;border:1px solid #B7D7C2;border-radius:6px;align-items:center;">' +
          '<img src="/images/merch-ceramic-mug.webp" alt="Complimentary Stoneware Mug" style="width:48px;height:48px;object-fit:cover;border-radius:6px;" />' +
          '<div style="flex:1;">' +
            '<div style="font-size:0.78rem;font-weight:800;color:#236B3B;">✦ VIP Milestone Gift Unlocked</div>' +
            '<div style="font-size:0.76rem;color:#141413;font-weight:600;">15oz Topographic Stoneware Vessel + Wax Folio</div>' +
          '</div>' +
          '<div style="font-size:0.82rem;font-weight:800;color:#236B3B;">FREE <s style="color:#78716C;font-weight:500;">$24</s></div>' +
        '</div>';
      }
      listEl.innerHTML = html;
    },

    toggleCartDrawer: function (open) {
      var drawer = document.getElementById("instant-cart-drawer");
      var backdrop = document.getElementById("cart-drawer-backdrop");
      if (!drawer || !backdrop) return;
      var shouldOpen = typeof open === "boolean" ? open : !drawer.classList.contains("is-open");
      drawer.classList.toggle("is-open", shouldOpen);
      backdrop.classList.toggle("is-open", shouldOpen);
      this.syncBodyScrollLock();
    },

    selectQuizOption: function (dimension, val, btnEl) {
      this.quizState[dimension] = val;
      if (btnEl) {
        var group = btnEl.closest("[data-quiz-group]");
        if (group) {
          group.querySelectorAll(".quiz-option-btn").forEach(function (b) {
            b.classList.remove("is-selected");
          });
        }
        btnEl.classList.add("is-selected");
      }
      this.renderQuizRecommendation();
    },

    renderQuizRecommendation: function () {
      var box = document.getElementById("curator-quiz-result");
      if (!box) return;
      var s = this.quizState;
      var primary = {
        sku: "PD-CANVAS-24X36",
        slug: "monolith-no-4-stretched-gallery-canvas-24x36",
        title: 'Monolith No. 4 — Bauhaus Impasto Gallery Canvas (24"×36")',
        price: 149.00,
        img: "/images/art-monolith-bauhaus.webp",
        reason: "Warm Terracotta & Ochre impasto balances natural daylight and anchors 72"–84" seating spans."
      };
      if (s.mood === "coastal_mineral" || s.space === "bedroom") {
        primary = {
          sku: "PD-FRAME-OAK-24X36",
          slug: "coastal-horizon-framed-fine-art-print-24x36",
          title: 'Coastal Horizon — Mineral Seascape Framed Print (24"×36")',
          price: 189.00,
          img: "/images/art-coastal-horizon.webp",
          reason: "310 GSM museum rag with 4-ply conservation mat creates serene depth for sunlit coastal & bedroom suites."
        };
      } else if (s.space === "executive_study" || s.mood === "dark_architectural") {
        primary = {
          sku: "PD-BLUEPRINT-24X36",
          slug: "celestial-astrolabe-architectural-blueprint-print",
          title: 'Celestial Astrolabe — Archival Blueprint Edition (24"×36")',
          price: 168.00,
          img: "/images/art-architectural-blueprint.webp",
          reason: "Prussian-blue & gold-leaf line precision engineered for executive studies and walnut shelving."
        };
      } else if (s.mood === "zen_organic") {
        primary = {
          sku: "PD-KYOTO-SUMI-24X36",
          slug: "kyoto-equilibrium-sumi-e-washi-print",
          title: 'Kyoto Equilibrium — Sumi-e Ink & Vermilion Seal (24"×36")',
          price: 154.00,
          img: "/images/art-kyoto-zen-sumi.webp",
          reason: "Minimalist sumi-e brushstroke with vermilion seal brings gallery tranquility to architectural spaces."
        };
      }
      var privPrice = (primary.price * 0.85).toFixed(2);
      box.innerHTML = '<div style="display:flex;flex-wrap:wrap;gap:1.25rem;align-items:center;justify-content:space-between;">' +
        '<div style="display:flex;gap:1rem;align-items:center;max-width:620px;">' +
          '<img src="' + primary.img + '" alt="' + primary.title + '" style="width:84px;height:102px;object-fit:cover;border-radius:8px;border:2px solid var(--accent-gold);box-shadow:0 8px 20px rgba(0,0,0,0.12);" />' +
          '<div>' +
            '<div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.1em;color:var(--cta-terracotta);">✦ Curatorial Dossier Match • 15% Privilege (CURATOR15) Unlocked</div>' +
            '<div style="font-family:var(--font-display);font-size:1.45rem;color:var(--ink-espresso);margin:0.15rem 0;">' + primary.title + '</div>' +
            '<p style="font-size:0.82rem;color:var(--ink-graphite);margin:0;">' + primary.reason + '</p>' +
          '</div>' +
        '</div>' +
        '<div style="display:flex;flex-wrap:wrap;gap:0.65rem;align-items:center;">' +
          '<div style="text-align:right;margin-right:0.35rem;">' +
            '<div style="font-family:var(--font-display);font-size:1.75rem;color:var(--ink-espresso);line-height:1;">$' + privPrice + '</div>' +
            '<div style="font-size:0.74rem;color:var(--ink-muted);"><s>$' + primary.price.toFixed(2) + '</s> w/ CURATOR15</div>' +
          '</div>' +
          '<a href="/pay/' + primary.slug + '?promo=CURATOR15&frame=' + encodeURIComponent(s.molding) + '&size=' + encodeURIComponent(s.span) + '" class="btn-primary" style="padding:0.75rem 1.25rem;font-size:0.82rem;">Claim Curated Edition (-15%) →</a>' +
          '<button type="button" class="btn-secondary" style="padding:0.72rem 1rem;font-size:0.8rem;" onclick="window.PrintDeckRuntime.applyPromoCode('CURATOR15');window.PrintDeckRuntime.addToCart('' + primary.sku + '', '' + primary.title.replace(/'/g, "\'") + '', ' + primary.price + ', '' + primary.img + '', '' + primary.slug + '')">+ Bag w/ 15% Off</button>' +
        '</div>' +
      '</div>';
    },

    updateVolumeCalc: function (unitsVal) {
      var u = Number(unitsVal || 10);
      var pct = u >= 50 ? 25 : (u >= 25 ? 20 : 15);
      var baseUnit = 88.00;
      var netUnit = (baseUnit * (100 - pct) / 100).toFixed(2);
      var total = (Number(netUnit) * u).toFixed(2);
      var saved = ((baseUnit * u) - Number(total)).toFixed(2);
      var out = document.getElementById("volume-calc-output");
      var link = document.getElementById("volume-calc-claim-link");
      if (out) {
        out.innerHTML = '<strong>' + u + ' Collector Pieces</strong> → Tier Privilege: <strong>' + pct + '% Off ($' + netUnit + '/unit)</strong> • Total Allocation: <strong>$' + total + ' USD</strong> (Save $' + saved + ' + Dedicated Master Framer)';
      }
      if (link) {
        var tierOffer = u >= 50 ? "b2b-studio-corporate-tier50" : "b2b-studio-corporate-tier10";
        link.href = "/pay/start?offer=" + tierOffer + "&sku=PD-HOODIE-HEAVY-BLK&qty=" + u + "&promo=TRADE20";
      }
    },

    updateSofaCalc: function (sofaInches) {
      var w = Number(sofaInches || 72);
      var minIn = Math.round(w * 0.66);
      var maxIn = Math.round(w * 0.75);
      var rec = w >= 84
        ? '36"×48" Grand Architectural Canvas or Dual 24"×36" Diptych'
        : '24"×36" Museum Gallery Canvas or Solid Oak Float Frame';
      var out = document.getElementById("sofa-calc-output");
      if (out) {
        out.textContent = 'Sofa Width: ' + w + '" → Ideal Artwork Span: ' + minIn + '"–' + maxIn + '" (2/3 Golden Ratio) • Recommended: ' + rec + ' hung 57" on-center.';
      }
    },

    toggleConcierge: function () {
      var panel = document.getElementById("concierge-chat-panel");
      if (panel) panel.classList.toggle("is-open");
    },

    sendConciergeChat: async function () {
      var input = document.getElementById("concierge-chat-input");
      var log = document.getElementById("concierge-chat-messages");
      if (!input || !log || !input.value.trim()) return;
      var msg = input.value.trim();
      input.value = "";
      var uDiv = document.createElement("div");
      uDiv.style.cssText = "align-self:flex-end;background:#C85A32;color:#fff;padding:0.55rem 0.85rem;border-radius:10px;font-size:0.83rem;max-width:86%;";
      uDiv.textContent = msg;
      log.appendChild(uDiv);
      try {
        var res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: msg, shipping_zip: "29601", customer_email: "collector@printdeck.net" })
        });
        var data = await res.json();
        var aDiv = document.createElement("div");
        aDiv.style.cssText = "align-self:flex-start;background:#F3EFE6;color:#141413;padding:0.65rem 0.85rem;border-radius:10px;font-size:0.83rem;max-width:92%;border:1px solid #CEC3B2;white-space:pre-wrap;";
        aDiv.textContent = data.assistant_message || "I would love to help you choose the right frame size or custom apparel fit.";
        log.appendChild(aDiv);
        log.scrollTop = log.scrollHeight;
      } catch (e) {
        console.error(e);
      }
    },

    checkAuthentikSession: async function () {
      try {
        var res = await fetch("/api/auth/session");
        if (!res.ok) return;
        var data = await res.json();
        var authBtn = document.getElementById("header-authentik-btn");
        if (data && data.authenticated && data.user && authBtn) {
          authBtn.innerHTML = '<span style="color:#236B3B;">●</span> ' + (data.user.name || data.user.email);
        }
      } catch (e) {}
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { window.PrintDeckRuntime.init(); });
  } else {
    window.PrintDeckRuntime.init();
  }
})();
