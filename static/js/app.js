(function () {
  const cfg = window.APP_CONFIG || { gstRate: 18, minItems: 2, quoteNote: "" };
  let cart = [];
  let searchTimer = null;

  const $ = (sel) => document.querySelector(sel);

  function showToast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.remove("hidden");
    setTimeout(() => el.classList.add("hidden"), 3500);
  }

  function getCustomer() {
    return {
      name: $("#custName").value.trim(),
      phone: $("#custPhone").value.trim(),
      email: $("#custEmail").value.trim(),
      address: $("#custAddress").value.trim(),
    };
  }

  function getCharges() {
    return {
      labour_charge: Number($("#labourCharge")?.value || 0),
      transport_charge: Number($("#transportCharge")?.value || 0),
      discount_amount: Number($("#discountAmount")?.value || 0),
    };
  }

  function validateCustomer() {
    if (!getCustomer().name) {
      showToast("Please enter customer name");
      return false;
    }
    return true;
  }

  function validateCart(minItems) {
    const min = minItems || cfg.minItems || 2;
    if (cart.length < min) {
      showToast(`Please add at least ${min} trees to the cart`);
      return false;
    }
    return true;
  }

  async function api(url, options = {}) {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Request failed");
    return data;
  }

  function calcTotals() {
    const subtotal = cart.reduce((s, i) => s + Number(i.rate || i.price || 0) * Number(i.qty || 0), 0);
    const gst = Math.round(subtotal * cfg.gstRate) / 100;
    const charges = getCharges();
    const total = Math.max(0, Math.round((subtotal + gst + charges.labour_charge + charges.transport_charge - charges.discount_amount) * 100) / 100);
    return { subtotal, gst, total, ...charges };
  }

  function renderCart() {
    const body = $("#cartBody");
    if (!cart.length) {
      body.innerHTML = '<tr class="empty-row"><td colspan="9">Add trees from search or quick add</td></tr>';
    } else {
      body.innerHTML = cart.map((i, idx) => {
        const rate = Number(i.rate || i.price || 0);
        const amount = rate * Number(i.qty || 0);
        return `
          <tr>
            <td>${idx + 1}</td>
            <td><strong>${escapeHtml(i.name)}</strong></td>
            <td>
              <div class="qty-control">
                <button type="button" data-action="dec" data-id="${i.id}">-</button>
                <span>${i.qty}</span>
                <button type="button" data-action="inc" data-id="${i.id}">+</button>
              </div>
            </td>
            <td><input class="inline-input" data-field="height" data-id="${i.id}" value="${escapeAttr(i.height || "")}" placeholder="Height" /></td>
            <td><input type="number" min="0" step="0.01" class="inline-input" data-field="rate" data-id="${i.id}" value="${rate.toFixed(2)}" /></td>
            <td>₹${amount.toFixed(2)}</td>
            <td><input class="inline-input" data-field="spacing" data-id="${i.id}" value="${escapeAttr(i.spacing || "")}" placeholder="Spacing" /></td>
            <td><input class="inline-input" data-field="remarks" data-id="${i.id}" value="${escapeAttr(i.remarks || "")}" placeholder="Remarks" /></td>
            <td><button type="button" class="remove-btn" data-id="${i.id}">🗑</button></td>
          </tr>`;
      }).join("");
    }

    const t = calcTotals();
    $("#subtotal").textContent = `₹${t.subtotal.toFixed(2)}`;
    $("#gst").textContent = `₹${t.gst.toFixed(2)}`;
    $("#labour").textContent = `₹${t.labour_charge.toFixed(2)}`;
    $("#transport").textContent = `₹${t.transport_charge.toFixed(2)}`;
    $("#discount").textContent = `₹${t.discount_amount.toFixed(2)}`;
    $("#total").textContent = `₹${t.total.toFixed(2)}`;
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = String(s || "");
    return d.innerHTML;
  }

  function escapeAttr(s) {
    return String(s || "").replace(/"/g, "&quot;");
  }

  async function loadCart() {
    const data = await api("/api/cart");
    cart = data.items || [];
    renderCart();
  }

  async function addTree(treeId) {
    const data = await api("/api/cart/add", {
      method: "POST",
      body: JSON.stringify({ tree_id: treeId }),
    });
    cart = data.items || [];
    renderCart();
    showToast(data.message || "Added");
    $("#searchResults").classList.add("hidden");
    $("#treeSearch").value = "";
  }

  async function updateCartItem(treeId, payload) {
    const data = await api("/api/cart/update", {
      method: "POST",
      body: JSON.stringify({ tree_id: treeId, ...payload }),
    });
    cart = data.items || [];
    renderCart();
  }

  async function searchTrees(q) {
    if (q.length < 1) {
      $("#searchResults").classList.add("hidden");
      return;
    }
    const results = await api(`/api/trees/search?q=${encodeURIComponent(q)}`);
    const ul = $("#searchResults");
    ul.innerHTML = results.length
      ? results.map((t) => `
          <li data-id="${t.id}">
            <div>
              <strong>${escapeHtml(t.name)}</strong>
              <div class="meta">${escapeHtml(t.scientific || "")}</div>
            </div>
            <div>
              <span class="price">₹${t.price}</span>
              <button type="button" class="btn btn-sm btn-add" data-add="${t.id}">+</button>
            </div>
          </li>`).join("")
      : '<li class="empty">No trees found</li>';
    ul.classList.remove("hidden");
  }

  async function createQuotation(opts) {
    return api("/api/quotations", {
      method: "POST",
      body: JSON.stringify({
        customer: getCustomer(),
        charges: getCharges(),
        quote_note: cfg.quoteNote,
        status: opts.status || "Draft",
        generate_pdf: !!opts.generatePdf,
        clear_cart: !!opts.clearCart,
        action: opts.action,
        min_items: opts.minItems || cfg.minItems,
      }),
    });
  }

  async function refreshQuotations() {
    const rows = await api("/api/quotations");
    const tbody = $("#quotationsBody");
    tbody.innerHTML = rows.length
      ? rows.map((q) => `
        <tr>
          <td>${escapeHtml(q.quotation_no)}</td>
          <td>${escapeHtml(q.customer_name || "")}</td>
          <td>₹${Number(q.total).toFixed(2)}</td>
          <td><span class="status status-${(q.status || "").toLowerCase()}">${q.status}</span></td>
          <td>${(q.created_at || "").slice(0, 10)}</td>
          <td class="actions">
            ${q.pdf_path ? `<a href="/quotations/${q.quotation_no}/pdf" title="PDF">⬇</a>` : ""}
            <button type="button" class="link-btn delete-q" data-no="${q.quotation_no}">🗑</button>
          </td>
        </tr>`).join("")
      : '<tr><td colspan="6">No quotations yet</td></tr>';
  }

  async function proceedPayment() {
    if (!validateCustomer() || !validateCart(1)) return;
    const order = await api("/api/payment/create", {
      method: "POST",
      body: JSON.stringify({ customer: getCustomer(), charges: getCharges(), quote_note: cfg.quoteNote }),
    });

    if (order.mode === "razorpay" && cfg.razorpayEnabled && window.Razorpay) {
      const rzp = new Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: "GreenFormula Landscape and Gardening Solution",
        description: `Payment for ${order.quotation_no}`,
        order_id: order.order_id,
        handler: async function (response) {
          await api("/api/payment/verify", {
            method: "POST",
            body: JSON.stringify({
              quotation_no: order.quotation_no,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            }),
          });
          showToast("Payment successful!");
          await loadCart();
          await refreshQuotations();
        },
      });
      rzp.open();
    } else if (confirm(`Demo payment mode\nPay ₹${(order.amount / 100).toFixed(2)} for ${order.quotation_no}?`)) {
      await api("/api/payment/verify", {
        method: "POST",
        body: JSON.stringify({
          quotation_no: order.quotation_no,
          demo: true,
          order_id: order.order_id,
          payment_id: `pay_demo_${order.quotation_no}`,
        }),
      });
      showToast("Demo payment recorded as Paid");
      cart = [];
      renderCart();
      await refreshQuotations();
    }
  }

  $("#treeSearch") && $("#treeSearch").addEventListener("input", function (e) {
    clearTimeout(searchTimer);
    const q = e.target.value.trim();
    searchTimer = setTimeout(function () { searchTrees(q); }, 250);
  });

  $("#searchResults") && $("#searchResults").addEventListener("click", function (e) {
    const btn = e.target.closest("[data-add]");
    const li = e.target.closest("li[data-id]");
    const id = (btn && btn.dataset.add) || (li && li.dataset.id);
    if (id) addTree(parseInt(id, 10));
  });

  document.addEventListener("click", async function (e) {
    if (e.target.matches(".btn-add[data-id]")) addTree(parseInt(e.target.dataset.id, 10));

    if (e.target.matches(".remove-btn")) {
      const data = await api("/api/cart/remove", {
        method: "POST",
        body: JSON.stringify({ tree_id: parseInt(e.target.dataset.id, 10) }),
      });
      cart = data.items || [];
      renderCart();
    }

    if (e.target.dataset.action === "inc" || e.target.dataset.action === "dec") {
      const id = parseInt(e.target.dataset.id, 10);
      const item = cart.find((i) => i.id === id);
      if (!item) return;
      const qty = e.target.dataset.action === "inc" ? item.qty + 1 : Math.max(1, item.qty - 1);
      await updateCartItem(id, { qty: qty });
    }

    if (e.target.matches(".delete-q") && confirm("Delete this quotation?")) {
      await api(`/api/quotations/${e.target.dataset.no}`, { method: "DELETE" });
      await refreshQuotations();
      showToast("Quotation deleted");
    }
  });

  document.addEventListener("change", function (e) {
    if (e.target.matches(".inline-input")) {
      const id = parseInt(e.target.dataset.id, 10);
      const field = e.target.dataset.field;
      const value = field === "rate" ? Number(e.target.value || 0) : e.target.value;
      updateCartItem(id, { qty: (cart.find((i) => i.id === id) || { qty: 1 }).qty, [field]: value }).catch(function (err) {
        showToast(err.message);
      });
    }
    if (e.target.matches("#labourCharge, #transportCharge, #discountAmount")) {
      renderCart();
    }
  });

  $("#clearCart") && $("#clearCart").addEventListener("click", async function () {
    await api("/api/cart/clear", { method: "POST" });
    cart = [];
    renderCart();
    showToast("Cart cleared");
  });

  $("#continueBtn") && $("#continueBtn").addEventListener("click", function () {
    if (!validateCustomer() || !validateCart()) return;
    const t = calcTotals();
    $("#confirmMessage").textContent = `You have ${cart.length} item(s) totaling ₹${t.total.toFixed(2)}. Generate a PDF quotation with company logo, address, and customer details?`;
    $("#confirmModal").classList.remove("hidden");
  });

  $("#confirmCancel") && $("#confirmCancel").addEventListener("click", function () {
    $("#confirmModal").classList.add("hidden");
  });

  $("#confirmOk") && $("#confirmOk").addEventListener("click", async function () {
    $("#confirmModal").classList.add("hidden");
    try {
      const result = await createQuotation({ status: "Sent", generatePdf: true, action: "generate" });
      if (result.pdf_url) window.open(result.pdf_url, "_blank");
      showToast(`Quotation ${result.quotation_no} generated`);
      await refreshQuotations();
    } catch (err) {
      showToast(err.message);
    }
  });

  $("#genPdf") && $("#genPdf").addEventListener("click", async function () {
    if (!validateCustomer() || !validateCart(1)) return;
    try {
      const result = await createQuotation({ status: "Sent", generatePdf: true, minItems: 1 });
      if (result.pdf_url) window.open(result.pdf_url, "_blank");
      showToast(`PDF ready: ${result.quotation_no}`);
      await refreshQuotations();
    } catch (err) {
      showToast(err.message);
    }
  });

  $("#payBtn") && $("#payBtn").addEventListener("click", function () {
    proceedPayment().catch(function (e) { showToast(e.message); });
  });

  $("#saveDraft") && $("#saveDraft").addEventListener("click", async function () {
    if (cart.length < 1) {
      showToast("Add items before saving draft");
      return;
    }
    try {
      const r = await createQuotation({ status: "Draft", minItems: 1 });
      showToast(`Draft saved: ${r.quotation_no}`);
      await refreshQuotations();
    } catch (err) {
      showToast(err.message);
    }
  });

  $("#clearAll") && $("#clearAll").addEventListener("click", async function () {
    await api("/api/cart/clear", { method: "POST" });
    cart = [];
    $("#custName").value = "";
    $("#custPhone").value = "";
    $("#custEmail").value = "";
    $("#custAddress").value = "";
    $("#labourCharge").value = "0";
    $("#transportCharge").value = "0";
    $("#discountAmount").value = "0";
    renderCart();
    showToast("Cart and customer cleared");
  });

  $("#saveCustomer") && $("#saveCustomer").addEventListener("click", async function () {
    if (!validateCustomer()) return;
    try {
      await api("/api/customers", { method: "POST", body: JSON.stringify(getCustomer()) });
      showToast("Customer details saved");
    } catch (e) {
      showToast(e.message);
    }
  });

  $("#menuToggle") && $("#menuToggle").addEventListener("click", function () {
    const side = document.querySelector(".sidebar");
    if (side) side.classList.toggle("open");
  });

  document.addEventListener("click", function (e) {
    if (!e.target.closest(".search-wrap")) {
      const r = $("#searchResults");
      if (r) r.classList.add("hidden");
    }
  });

  loadCart().then(refreshQuotations).catch(function () {});
})();
