(function () {
  const api = window.webApi;
  if (!api || !api.ensureAuthenticated || !api.ensureAuthenticated()) return;

  const $ = function (id) { return document.getElementById(id); };

  const dom = {
    error: $("price-error"),
    errorText: $("price-error-text"),
    avgSavings: $("avg-savings"),
    trackedProducts: $("tracked-products"),
    bestDeal: $("best-deal"),
    search: $("price-search"),
    market: $("market-filter"),
    cards: $("prices-cards"),
    topDeals: $("top-deals-list"),
    basketToggle: $("basket-add-toggle"),
    basketMenu: $("basket-add-menu"),
    basketSearch: $("basket-search"),
    basketOptions: $("basket-options"),
    basketItems: $("basket-items"),
    basketTotals: $("basket-totals"),
    basketTotalRegular: $("basket-total-regular"),
    basketTotalCheapest: $("basket-total-cheapest"),
    basketTotalSaving: $("basket-total-saving"),
    basketTotalSavingPct: $("basket-total-saving-pct"),
    projections: $("basket-projections"),
    projWeekly: $("proj-weekly"),
    projMonthly: $("proj-monthly"),
    projAnnual: $("proj-annual"),
    modal: $("price-modal"),
    modalCard: $("price-modal-card"),
    modalClose: $("price-modal-close"),
    modalHeader: $("price-modal-header"),
    modalMarket: $("price-modal-market"),
    modalVegetable: $("price-modal-vegetable"),
    modalAverage: $("price-modal-average"),
    modalUnit: $("price-modal-unit"),
    modalBest: $("price-modal-best"),
    modalBestQuality: $("price-modal-best-quality"),
    modalLocationsCount: $("price-modal-locations-count"),
    modalTabPrices: $("price-modal-tab-prices"),
    modalTabLocations: $("price-modal-tab-locations"),
    modalPrices: $("price-modal-prices"),
    modalLocations: $("price-modal-locations"),
    modalTip: $("price-modal-tip"),
    modalStorage: $("price-modal-storage"),
  };

  const supermarkets = [
    { id: "ntuc", name: "NTUC", fullName: "NTUC FairPrice", color: "bg-red-500", gradient: "from-red-500 to-red-600" },
    { id: "giant", name: "Giant", fullName: "Giant", color: "bg-blue-500", gradient: "from-blue-500 to-blue-600" },
    { id: "coldStorage", name: "Cold Storage", fullName: "Cold Storage", color: "bg-purple-500", gradient: "from-purple-500 to-purple-600" },
    { id: "shengSiong", name: "Sheng Siong", fullName: "Sheng Siong", color: "bg-orange-500", gradient: "from-orange-500 to-orange-600" },
  ];

  const state = {
    catalog: {},
    search: "",
    market: "all",
    basket: [],
    basketMenuOpen: false,
    selectedModal: null,
    modalTab: "prices",
  };

  function mountModalToViewport() {
    if (!dom.modal || !document.body) return;
    if (dom.modal.parentElement === document.body) return;
    document.body.appendChild(dom.modal);
  }

  function createIcons(root) {
    if (!window.lucide || typeof window.lucide.createIcons !== "function") return;
    window.lucide.createIcons({ icons: window.lucide.icons, nameAttr: "data-lucide", ...(root ? { root: root } : {}) });
  }

  function safe(value) { return api.escapeHtml ? api.escapeHtml(value) : String(value || ""); }
  function entries() { return Object.entries(state.catalog || {}); }

  function showError(message) {
    const msg = String(message || "").trim();
    if (!msg) {
      dom.error.classList.add("hidden");
      dom.error.classList.remove("flex");
      dom.errorText.textContent = "";
      return;
    }
    dom.error.classList.remove("hidden");
    dom.error.classList.add("flex");
    dom.errorText.textContent = msg;
  }

  function cheapest(prices) {
    const list = supermarkets.map(function (m) {
      return { id: m.id, name: m.name, price: Number((prices || {})[m.id] || 0) };
    });
    return list.reduce(function (best, current) { return current.price < best.price ? current : best; }, list[0]);
  }

  function average(prices) {
    const values = supermarkets.map(function (m) { return Number((prices || {})[m.id] || 0); });
    return values.length ? values.reduce(function (sum, v) { return sum + v; }, 0) / values.length : 0;
  }

  function activeVegetableEntries() {
    const query = String(state.search || "").trim().toLowerCase();
    const rows = entries().filter(function (entry) {
      const veg = entry[1] || {};
      if (!query) return true;
      const haystack = [
        veg.name,
        veg.scientificName,
        veg.category,
        veg.description,
        entry[0],
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });

    if (state.market === "all") {
      return rows;
    }

    return rows
      .filter(function (entry) {
        const veg = entry[1] || {};
        const price = Number(((veg.prices || {})[state.market]) || 0);
        return Number.isFinite(price) && price > 0;
      })
      .sort(function (a, b) {
        const priceA = Number((((a[1] || {}).prices || {})[state.market]) || 0);
        const priceB = Number((((b[1] || {}).prices || {})[state.market]) || 0);
        return priceA - priceB;
      });
  }

  function topDeals(sourceEntries) {
    const scope = Array.isArray(sourceEntries) ? sourceEntries : entries();
    return scope
      .map(function (entry) {
        const key = entry[0];
        const veg = entry[1];
        const low = cheapest(veg.prices);
        let savings = 0;
        if (state.market === "all") {
          const avg = average(veg.prices);
          savings = avg > 0 ? ((avg - low.price) / avg) * 100 : 0;
        } else {
          const selected = Number((veg.prices || {})[state.market] || 0);
          if (selected > 0) {
            savings = ((selected - low.price) / selected) * 100;
          }
        }
        return { key: key, veg: veg, cheapest: low, savings: savings };
      })
      .sort(function (a, b) { return b.savings - a.savings; })
      .slice(0, 3);
  }

  function filteredVegetables() {
    return activeVegetableEntries();
  }

  function updateStats(items) {
    const list = Array.isArray(items) ? items : activeVegetableEntries();
    let totalSavings = 0;
    list.forEach(function (entry) {
      const veg = entry[1];
      if (state.market === "all") {
        totalSavings += Math.max(0, average(veg.prices) - cheapest(veg.prices).price);
      } else {
        const selected = Number((veg.prices || {})[state.market] || 0);
        totalSavings += Math.max(0, selected - cheapest(veg.prices).price);
      }
    });
    const avgSaving = list.length ? totalSavings / list.length : 0;

    dom.avgSavings.textContent = `$${avgSaving.toFixed(2)}`;
    dom.trackedProducts.textContent = String(list.length);
    const deals = topDeals(list);
    dom.bestDeal.textContent = deals.length ? `${deals[0].savings.toFixed(0)}%` : "0%";
  }

  function openModal(veg, marketId) {
    const market = supermarkets.find(function (m) { return m.id === marketId; }) || supermarkets[0];
    const details = (veg.priceDetails && veg.priceDetails[marketId]) || { average: Number((veg.prices || {})[marketId] || 0), variations: [] };
    const vars = Array.isArray(details.variations) ? [...details.variations].sort(function (a, b) { return Number(a.price || 0) - Number(b.price || 0); }) : [];
    const best = vars.length ? vars[0] : { price: Number((veg.prices || {})[marketId] || 0), quality: "Standard", location: "N/A", lastUpdated: "Today" };

    state.selectedModal = { veg: veg, market: market, details: details, vars: vars, best: best };
    state.modalTab = "prices";

    dom.modalHeader.className = `bg-gradient-to-r ${market.gradient} p-6 text-white rounded-t-3xl`;
    dom.modalMarket.textContent = market.fullName;
    dom.modalVegetable.textContent = veg.name;
    dom.modalAverage.textContent = `$${Number(details.average || 0).toFixed(2)}`;
    dom.modalUnit.textContent = veg.unit || "per kg";
    dom.modalBest.textContent = `$${Number(best.price || 0).toFixed(2)}`;
    dom.modalBestQuality.textContent = best.quality || "Best value";
    dom.modalLocationsCount.textContent = String(new Set(vars.map(function (v) { return v.location; })).size || 1);

    renderModalContent();
    dom.modal.classList.remove("hidden");
    dom.modal.classList.add("flex");
    createIcons(dom.modal);
  }

  function closeModal() {
    dom.modal.classList.add("hidden");
    dom.modal.classList.remove("flex");
    state.selectedModal = null;
  }

  function renderModalContent() {
    if (!state.selectedModal) return;
    const data = state.selectedModal;
    const maxPrice = data.vars.length ? Math.max.apply(null, data.vars.map(function (v) { return Number(v.price || 0); })) : Number(data.best.price || 1);

    dom.modalTabPrices.className = `flex-1 py-3 px-4 rounded-xl font-medium transition-all ${state.modalTab === "prices" ? "bg-white/20 text-white" : "bg-white/5 text-white/70 hover:bg-white/10 hover:text-white"}`;
    dom.modalTabLocations.className = `flex-1 py-3 px-4 rounded-xl font-medium transition-all ${state.modalTab === "locations" ? "bg-white/20 text-white" : "bg-white/5 text-white/70 hover:bg-white/10 hover:text-white"}`;

    if (state.modalTab === "prices") {
      dom.modalPrices.classList.remove("hidden");
      dom.modalLocations.classList.add("hidden");
      dom.modalPrices.innerHTML = data.vars.map(function (v, idx) {
        const price = Number(v.price || 0);
        const isBest = price === Number(data.best.price || 0);
        return `
          <div class="group relative p-5 rounded-xl bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all">
            ${isBest ? '<div class="absolute -top-2 -right-2 w-8 h-8 bg-gradient-to-br from-yellow-400 to-yellow-500 rounded-full flex items-center justify-center shadow-lg"><i data-lucide="star" class="w-4 h-4 text-white fill-current"></i></div>' : ""}
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-4"><div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center text-white font-bold text-xl shadow-lg">$${price.toFixed(2)}</div><div><p class="font-bold text-lg text-gray-900 dark:text-white mb-1">${safe(v.quality || "Standard")}</p><p class="text-sm text-primary-600 dark:text-primary-400 flex items-center gap-1"><i data-lucide="map-pin" class="w-4 h-4"></i>${safe(v.location || "N/A")}</p></div></div>
              <span class="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-gray-200 dark:bg-gray-700 text-xs font-medium text-gray-700 dark:text-gray-300"><i data-lucide="clock" class="w-3 h-3"></i>${safe(v.lastUpdated || "Today")}</span>
            </div>
            <div class="relative h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden"><div class="h-full bg-gradient-to-r ${data.market.gradient}" style="width: ${maxPrice > 0 ? (price / maxPrice) * 100 : 0}%"></div></div>
            <div class="mt-2 flex items-center justify-between text-sm text-gray-600 dark:text-gray-400"><span class="font-medium">${isBest ? "Lowest price" : `+$${(price - Number(data.best.price || 0)).toFixed(2)} vs cheapest`}</span><span>${maxPrice > 0 ? ((price / maxPrice) * 100).toFixed(0) : 0}% of max price</span></div>
          </div>
        `;
      }).join("") || '<div class="text-sm text-gray-500 dark:text-gray-400">No price variations available.</div>';
    } else {
      dom.modalPrices.classList.add("hidden");
      dom.modalLocations.classList.remove("hidden");
      const grouped = {};
      (data.vars || []).forEach(function (v) {
        const key = v.location || "N/A";
        if (!grouped[key]) grouped[key] = [];
        grouped[key].push(v);
      });
      dom.modalLocations.innerHTML = Object.keys(grouped).map(function (location) {
        const vars = grouped[location];
        return `
          <div class="p-5 rounded-xl bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 border-2 border-gray-200 dark:border-gray-700">
            <h4 class="text-xl font-bold text-gray-900 dark:text-white mb-3 flex items-center gap-2"><i data-lucide="map-pin" class="w-5 h-5 text-primary-500"></i>${safe(location)}</h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              ${vars.map(function (v) {
                return `<div class="p-4 rounded-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700"><div class="flex items-center justify-between mb-2"><span class="text-sm font-semibold text-gray-700 dark:text-gray-300">${safe(v.quality || "Standard")}</span></div><div class="flex items-baseline justify-between"><span class="text-2xl font-bold text-primary-600 dark:text-primary-400">$${Number(v.price || 0).toFixed(2)}</span><span class="text-xs text-gray-500 dark:text-gray-400">${safe(v.lastUpdated || "Today")}</span></div></div>`;
              }).join("")}
            </div>
          </div>
        `;
      }).join("") || '<div class="text-sm text-gray-500 dark:text-gray-400">No location data available.</div>';
    }

    const maxVar = data.vars.length ? data.vars[data.vars.length - 1] : data.best;
    dom.modalTip.textContent = `Save $${(Number(maxVar.price || 0) - Number(data.best.price || 0)).toFixed(2)} ${data.veg.unit || "per unit"} by choosing the cheapest option at ${data.best.location || "best outlet"}.`;
    dom.modalStorage.textContent = `Storage: ${data.veg.storageLife || "N/A"} • Season: ${data.veg.seasonality || "Year-round"}`;
    createIcons(dom.modal);
  }

  function renderCards(items) {
    const rows = Array.isArray(items) ? items : filteredVegetables();
    if (!rows.length) {
      dom.cards.innerHTML = '<div class="card p-6 text-sm text-gray-500 dark:text-gray-400">No vegetables match current filters.</div>';
      return;
    }

    dom.cards.innerHTML = rows.map(function (entry) {
      const key = entry[0];
      const veg = entry[1];
      const low = cheapest(veg.prices || {});
      const avg = average(veg.prices || {});
      const savings = avg > 0 ? ((avg - low.price) / avg) * 100 : 0;
      const marketIds = state.market === "all" ? supermarkets.map(function (m) { return m.id; }) : [state.market];
      const gridClass = marketIds.length === 1 ? "grid-cols-1" : "grid-cols-2 md:grid-cols-4";
      const marketLabel =
        state.market === "all"
          ? "All supermarkets"
          : (supermarkets.find(function (m) { return m.id === state.market; }) || {}).fullName || state.market;
      return `
        <div class="card p-6 hover:shadow-xl transition-all bg-white dark:bg-gray-900">
          <div class="flex items-start justify-between mb-4">
            <div class="flex-1">
              <h3 class="text-xl font-bold text-gray-900 dark:text-white mb-1">${safe(veg.name || key)}</h3>
              <p class="text-sm text-gray-500 dark:text-gray-400 italic">${safe(veg.scientificName || "")}</p>
              <div class="flex items-center gap-2 mt-2"><span class="px-3 py-1 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-xs font-semibold">${safe(veg.seasonality || "Year-round")}</span><span class="text-xs text-gray-500 dark:text-gray-400">Storage: ${safe(veg.storageLife || "N/A")}</span></div>
              <p class="text-xs mt-2 text-gray-500 dark:text-gray-400">Filter: ${safe(marketLabel)}</p>
            </div>
            <div class="text-right"><div class="flex items-center gap-2 mb-1"><i data-lucide="trending-down" class="w-5 h-5 text-success-500"></i><span class="text-2xl font-bold text-success-600 dark:text-success-400">${savings.toFixed(0)}%</span></div><p class="text-xs text-gray-500">max savings</p></div>
          </div>
          <div class="grid ${gridClass} gap-3">
            ${marketIds.map(function (marketId) {
              const market = supermarkets.find(function (item) { return item.id === marketId; }) || supermarkets[0];
              const price = Number((veg.prices || {})[market.id] || 0);
              const isBest = low.id === market.id;
              return `<button type="button" data-open-price="${safe(key)}:${safe(market.id)}" class="group relative p-5 rounded-xl transition-all hover:scale-105 shadow-md hover:shadow-lg ${isBest ? `${market.color} text-white` : "bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700"}">${isBest ? '<div class="absolute -top-2 -right-2 w-7 h-7 bg-yellow-400 rounded-full flex items-center justify-center shadow-lg"><i data-lucide="award" class="w-4 h-4 text-white"></i></div>' : ""}<p class="text-xs font-bold mb-2 ${isBest ? "text-white" : "text-gray-600 dark:text-gray-400"}">${safe(market.name)}</p><p class="text-2xl font-bold mb-1 ${isBest ? "text-white" : "text-gray-900 dark:text-white"}">$${price.toFixed(2)}</p><p class="text-xs ${isBest ? "text-white/80" : "text-gray-500"}">${safe(veg.unit || "per kg")}</p></button>`;
            }).join("")}
          </div>
        </div>
      `;
    }).join("");

    createIcons(dom.cards);
  }

  function renderTopDeals(items) {
    const deals = topDeals(items);
    dom.topDeals.innerHTML = deals.map(function (deal) {
      const metricLabel = state.market === "all" ? "OFF" : "better";
      return `<div class="p-4 rounded-xl bg-gradient-to-r from-primary-50 to-accent-50 dark:from-primary-900/20 dark:to-accent-900/20 border border-primary-100 dark:border-primary-800"><div class="flex items-center justify-between mb-2"><p class="font-bold text-gray-900 dark:text-white">${safe(deal.veg.name || deal.key)}</p><span class="px-3 py-1 rounded-full bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300 text-xs font-bold">${deal.savings.toFixed(0)}% ${metricLabel}</span></div><div class="flex items-center justify-between"><p class="text-sm text-gray-600 dark:text-gray-400">at ${safe(deal.cheapest.name)}</p><p class="text-xl font-bold text-primary-600 dark:text-primary-400">$${deal.cheapest.price.toFixed(2)}</p></div></div>`;
    }).join("") || '<p class="text-sm text-gray-500 dark:text-gray-400">No deals available.</p>';
  }

  function renderAll() {
    const items = activeVegetableEntries();
    updateStats(items);
    renderCards(items);
    renderTopDeals(items);
  }

  async function loadPrices() {
    const payload = await api.apiRequest("/api/veggie/prices");
    const items = payload && payload.data ? payload.data.vegetables : [];
    const mapped = {};
    (items || []).forEach(function (item) {
      const key = String(item.key || item.name || "").toLowerCase().replace(/\s+/g, "_");
      mapped[key] = item;
    });
    state.catalog = mapped;
    renderAll();
  }
  function basketItemIndex(key) {
    return state.basket.findIndex(function (item) { return item.key === key; });
  }

  function addToBasket(key) {
    const veg = state.catalog[key];
    if (!veg) return;
    const index = basketItemIndex(key);
    if (index >= 0) state.basket[index].quantity += 1;
    else state.basket.push({ key: key, quantity: 1 });
    renderBasket();
  }

  function updateBasketQuantity(key, delta) {
    const index = basketItemIndex(key);
    if (index < 0) return;
    state.basket[index].quantity = Math.max(0, state.basket[index].quantity + delta);
    state.basket = state.basket.filter(function (item) { return item.quantity > 0; });
    renderBasket();
  }

  function removeBasketItem(key) {
    state.basket = state.basket.filter(function (item) { return item.key !== key; });
    renderBasket();
  }

  function basketTotals() {
    let regular = 0;
    let cheapestTotal = 0;
    state.basket.forEach(function (item) {
      const veg = state.catalog[item.key];
      if (!veg) return;
      const avg = average(veg.prices || {});
      const low = cheapest(veg.prices || {});
      regular += avg * item.quantity;
      cheapestTotal += low.price * item.quantity;
    });
    const savings = regular - cheapestTotal;
    return { regular: regular, cheapest: cheapestTotal, savings: savings, savingsPct: regular > 0 ? (savings / regular) * 100 : 0 };
  }

  function renderBasketOptions() {
    const query = String(dom.basketSearch.value || "").toLowerCase().trim();
    const options = entries().filter(function (entry) {
      return !query || String(entry[1].name || entry[0]).toLowerCase().includes(query);
    });
    dom.basketOptions.innerHTML = options.map(function (entry) {
      const key = entry[0];
      const veg = entry[1];
      const low = cheapest(veg.prices || {});
      return `<button type="button" data-add-basket="${safe(key)}" class="w-full px-3 py-2 text-left hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors"><div class="flex items-center justify-between"><div class="flex-1"><p class="font-semibold text-gray-900 dark:text-white text-sm">${safe(veg.name || key)}</p><p class="text-xs text-gray-500 dark:text-gray-400">from $${low.price.toFixed(2)} ${safe(veg.unit || "per kg")}</p></div><i data-lucide="plus" class="w-4 h-4 text-primary-600"></i></div></button>`;
    }).join("") || '<p class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">No vegetables found.</p>';
    createIcons(dom.basketOptions);
  }

  function renderBasket() {
    if (!state.basket.length) {
      dom.basketItems.innerHTML = '<div class="text-center py-8 text-gray-400 dark:text-gray-600"><i data-lucide="shopping-basket" class="w-12 h-12 mx-auto mb-2 opacity-50"></i><p class="text-sm">Your basket is empty</p><p class="text-xs">Add vegetables to see your savings</p></div>';
      dom.basketTotals.classList.add("hidden");
      dom.projections.classList.add("hidden");
      createIcons(dom.basketItems);
      return;
    }

    dom.basketItems.innerHTML = state.basket.map(function (item) {
      const veg = state.catalog[item.key];
      const low = cheapest(veg.prices || {});
      const avg = average(veg.prices || {});
      const savings = (avg - low.price) * item.quantity;
      return `<div class="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"><div class="flex items-start justify-between mb-2"><div class="flex-1"><p class="font-semibold text-gray-900 dark:text-white text-sm">${safe(veg.name || item.key)}</p><p class="text-xs text-gray-500 dark:text-gray-400">Best at ${safe(low.name)} • $${low.price.toFixed(2)} ${safe(veg.unit || "per kg")}</p></div><button type="button" data-remove-basket="${safe(item.key)}" class="p-1 hover:bg-red-100 dark:hover:bg-red-900/20 rounded text-red-500 transition-colors"><i data-lucide="x" class="w-4 h-4"></i></button></div><div class="flex items-center justify-between"><div class="flex items-center gap-2"><button type="button" data-qty-basket="${safe(item.key)}:-1" class="w-7 h-7 rounded-lg bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"><i data-lucide="minus" class="w-3 h-3"></i></button><span class="w-8 text-center font-bold text-gray-900 dark:text-white">${item.quantity}</span><button type="button" data-qty-basket="${safe(item.key)}:1" class="w-7 h-7 rounded-lg bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"><i data-lucide="plus" class="w-3 h-3"></i></button></div><div class="text-right"><p class="text-lg font-bold text-primary-600 dark:text-primary-400">$${(low.price * item.quantity).toFixed(2)}</p>${savings > 0 ? `<p class="text-xs text-success-600 dark:text-success-400">Save $${savings.toFixed(2)}</p>` : ""}</div></div></div>`;
    }).join("");
    createIcons(dom.basketItems);

    const totals = basketTotals();
    dom.basketTotals.classList.remove("hidden");
    dom.basketTotalRegular.textContent = `$${totals.regular.toFixed(2)}`;
    dom.basketTotalCheapest.textContent = `$${totals.cheapest.toFixed(2)}`;
    dom.basketTotalSaving.textContent = `$${totals.savings.toFixed(2)}`;
    dom.basketTotalSavingPct.textContent = `${totals.savingsPct.toFixed(1)}% discount`;

    if (totals.savings > 0) {
      dom.projections.classList.remove("hidden");
      dom.projWeekly.textContent = `$${totals.savings.toFixed(2)}`;
      dom.projMonthly.textContent = `$${(totals.savings * 4.33).toFixed(2)}`;
      dom.projAnnual.textContent = `$${(totals.savings * 4.33 * 12).toFixed(2)}`;
    } else {
      dom.projections.classList.add("hidden");
    }
  }

  function bindEvents() {
    dom.search.addEventListener("input", function () { state.search = dom.search.value.trim(); renderAll(); });
    dom.market.addEventListener("change", function () { state.market = dom.market.value; renderAll(); });

    dom.cards.addEventListener("click", function (event) {
      const button = event.target.closest("[data-open-price]");
      if (!button) return;
      const parts = (button.getAttribute("data-open-price") || "").split(":");
      const key = parts[0];
      const market = parts[1];
      const veg = state.catalog[key];
      if (veg) openModal(veg, market);
    });

    dom.modalClose.addEventListener("click", closeModal);
    dom.modal.addEventListener("click", function (event) { if (event.target === dom.modal) closeModal(); });
    dom.modalTabPrices.addEventListener("click", function () { state.modalTab = "prices"; renderModalContent(); });
    dom.modalTabLocations.addEventListener("click", function () { state.modalTab = "locations"; renderModalContent(); });

    dom.basketToggle.addEventListener("click", function () {
      state.basketMenuOpen = !state.basketMenuOpen;
      dom.basketMenu.classList.toggle("hidden", !state.basketMenuOpen);
      if (state.basketMenuOpen) renderBasketOptions();
    });

    dom.basketSearch.addEventListener("input", renderBasketOptions);
    dom.basketOptions.addEventListener("click", function (event) {
      const button = event.target.closest("[data-add-basket]");
      if (!button) return;
      addToBasket(button.getAttribute("data-add-basket"));
      state.basketMenuOpen = false;
      dom.basketMenu.classList.add("hidden");
      dom.basketSearch.value = "";
    });

    dom.basketItems.addEventListener("click", function (event) {
      const removeButton = event.target.closest("[data-remove-basket]");
      if (removeButton) {
        removeBasketItem(removeButton.getAttribute("data-remove-basket"));
        return;
      }
      const qtyButton = event.target.closest("[data-qty-basket]");
      if (!qtyButton) return;
      const parts = (qtyButton.getAttribute("data-qty-basket") || "").split(":");
      updateBasketQuantity(parts[0], Number(parts[1] || 0));
    });

    document.addEventListener("mousedown", function (event) {
      if (!state.basketMenuOpen) return;
      if (dom.basketMenu.contains(event.target) || dom.basketToggle.contains(event.target)) return;
      state.basketMenuOpen = false;
      dom.basketMenu.classList.add("hidden");
    });
  }

  async function init() {
    mountModalToViewport();
    createIcons();
    bindEvents();
    renderBasket();
    showError("");
    try {
      await loadPrices();
    } catch (error) {
      showError(error && error.message ? error.message : "Failed to load prices");
    }
  }

  init();
})();

