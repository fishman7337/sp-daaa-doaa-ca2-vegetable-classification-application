(function () {
  const api = window.webApi;
  if (!api || !api.ensureAuthenticated || !api.ensureAuthenticated()) return;

  const $ = function (id) {
    return document.getElementById(id);
  };

  const dom = {
    tabClassify: $("tab-classify"),
    tabHistory: $("tab-history"),
    panelClassify: $("panel-classify"),
    panelHistory: $("panel-history"),
    historyCount: $("history-count"),
    error: $("predict-error"),
    errorText: $("predict-error-text"),
    modelSelect: $("model-select"),
    modelMeta: $("model-meta"),
    dropzone: $("upload-dropzone"),
    dropEmpty: $("drop-empty"),
    dropEmptyIcon: $("drop-empty-icon"),
    dropEmptyTitle: $("drop-empty-title"),
    dropPreview: $("drop-preview"),
    selectedImage: $("selected-image"),
    imageCounter: $("image-counter"),
    resetImages: $("reset-images"),
    uploadInput: $("upload-image"),
    browseFilesBtn: $("browse-files-btn"),
    gallery: $("image-gallery"),
    initialActions: $("initial-actions"),
    activeActions: $("active-actions"),
    sampleButtons: Array.from(document.querySelectorAll(".sample-btn")),
    predictBtn: $("predict-btn"),
    predictIcon: $("predict-icon"),
    predictLoader: $("predict-loader"),
    predictLabel: $("predict-label"),
    analyzingOverlay: $("analyzing-overlay"),
    analyzingProgress: $("analyzing-progress"),
    analyzingText: $("analyzing-text"),
    resultEmpty: $("result-empty"),
    resultList: $("result-list"),
    historyTotal: $("history-total"),
    historyExport: $("history-export"),
    historyClear: $("history-clear"),
    historySearch: $("history-search"),
    historySearchClear: $("history-search-clear"),
    historyFilterToggle: $("history-filter-toggle"),
    historyFilterChevron: $("history-filter-chevron"),
    historyFilters: $("history-filters"),
    historyCategory: $("history-category"),
    historyModel: $("history-model"),
    historySort: $("history-sort"),
    historyOrderToggle: $("history-order-toggle"),
    historyOrderText: $("history-order-text"),
    historyOrderIcon: $("history-order-icon"),
    historyOverviewTableShell: $("history-overview-table-shell"),
    historyOverviewMeta: $("history-overview-meta"),
    historyOverviewTableBody: $("history-overview-table-body"),
    historyList: $("history-list"),
    historyEmpty: $("history-empty"),
    historyEmptyTitle: $("history-empty-title"),
    historyEmptyText: $("history-empty-text"),
    detailModal: $("history-detail-modal"),
    detailImage: $("history-detail-image"),
    detailBody: $("history-detail-body"),
    detailClose: $("history-detail-close"),
    deleteModal: $("history-delete-modal"),
    deleteCancel: $("history-delete-cancel"),
    deleteConfirm: $("history-delete-confirm"),
    clearModal: $("history-clear-modal"),
    clearCancel: $("history-clear-cancel"),
    clearConfirm: $("history-clear-confirm"),
    openCameraBtn: $("open-camera-btn"),
    cameraModal: $("camera-modal"),
    cameraCloseBtn: $("camera-close-btn"),
    cameraModeCapture: $("camera-mode-capture"),
    cameraModeLive: $("camera-mode-live"),
    cameraCloseBtnBottom: $("camera-close-btn-bottom"),
    cameraModeCaptureBottom: $("camera-mode-capture-bottom"),
    cameraModeLiveBottom: $("camera-mode-live-bottom"),
    cameraFlipBtn: $("camera-flip-btn"),
    cameraStage: $("camera-stage"),
    cameraVideo: $("camera-video"),
    cameraPreview: $("camera-preview"),
    cameraFocusBox: $("camera-focus-box"),
    cameraLiveScan: $("camera-live-scan"),
    cameraDetectionRegion: $("camera-detection-region"),
    cameraDetectionLabel: $("camera-detection-label"),
    cameraLiveResult: $("camera-live-result"),
    cameraDetectError: $("camera-detect-error"),
    cameraCanvas: $("camera-canvas"),
    cameraCaptureActions: $("camera-capture-actions"),
    cameraPreviewActions: $("camera-preview-actions"),
    cameraLiveActions: $("camera-live-actions"),
    cameraCaptureBtn: $("camera-capture-btn"),
    cameraRetakeBtn: $("camera-retake-btn"),
    cameraUseBtn: $("camera-use-btn"),
    cameraCaptureHint: $("camera-capture-hint"),
  };

  const state = {
    tab: "classify",
    models: [],
    selectedModel: "vegnet-23",
    images: [],
    currentImageIndex: 0,
    isAnalyzing: false,
    analyzingProgressValue: 0,
    analyzingProgressTimer: null,
    results: [],
    resultIndex: 0,
    history: [],
    filters: { search: "", category: "all", model: "all", sort: "relevance", order: "desc" },
    filtersOpen: false,
    pendingDeleteId: null,
    catalog: {},
    camera: {
      mode: "capture",
      facingMode: "environment",
      stream: null,
      capturedBlob: null,
      interval: null,
      inFlight: false,
    },
  };

  const fallbackCatalog = {
    tomato: { description: "A red, edible fruit from the nightshade family.", nutrients: ["Vitamin C", "Potassium", "Lycopene"] },
    carrot: { description: "A root vegetable rich in beta-carotene.", nutrients: ["Beta-carotene", "Fiber", "Vitamin K1"] },
    broccoli: { description: "A green plant in the cabbage family.", nutrients: ["Vitamin C", "Vitamin K", "Fiber"] },
    capsicum: { description: "A colorful pepper rich in vitamins.", nutrients: ["Vitamin C", "Vitamin A", "Folate"] },
    potato: { description: "A starchy tuberous crop.", nutrients: ["Potassium", "Vitamin C", "Fiber"] },
    pumpkin: { description: "A nutrient-rich squash.", nutrients: ["Vitamin A", "Vitamin C", "Fiber"] },
  };
  const SINGAPORE_TIME_ZONE = "Asia/Singapore";
  const SG_DATE_FORMATTER = new Intl.DateTimeFormat("en-SG", {
    timeZone: SINGAPORE_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  const SG_TIME_FORMATTER = new Intl.DateTimeFormat("en-SG", {
    timeZone: SINGAPORE_TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  function normalizeSearchText(value) {
    return String(value || "")
      .toLowerCase()
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[_/.-]+/g, " ")
      .replace(/[^a-z0-9:\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function parseTimestamp(value) {
    if (!value) return new Date();
    const raw = String(value).trim();
    if (!raw) return new Date();

    if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(raw)) {
      return new Date(raw.replace(" ", "T") + "Z");
    }
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
      return new Date(`${raw}T00:00:00Z`);
    }
    const parsed = new Date(raw);
    return Number.isNaN(parsed.getTime()) ? new Date() : parsed;
  }

  function formatSingaporeDate(value) {
    return SG_DATE_FORMATTER.format(parseTimestamp(value));
  }

  function formatSingaporeTime(value) {
    return SG_TIME_FORMATTER.format(parseTimestamp(value));
  }

  function parseSearchQuery(rawQuery) {
    const original = String(rawQuery || "").trim();
    if (!original) {
      return { rawText: "", freeText: "", terms: [], fields: {} };
    }

    const fields = {};
    const looseParts = [];
    original.split(/\s+/).forEach(function (token) {
      const match = /^([a-zA-Z_]+):(.*)$/.exec(token);
      if (!match) {
        looseParts.push(token);
        return;
      }
      const key = normalizeSearchText(match[1]);
      const value = normalizeSearchText(match[2]);
      if (!value) {
        looseParts.push(token);
        return;
      }
      if (["model", "category", "name", "scientific", "date"].includes(key)) {
        fields[key] = value;
        return;
      }
      looseParts.push(token);
    });

    const freeText = normalizeSearchText(looseParts.join(" "));
    return {
      rawText: original,
      freeText: freeText,
      terms: freeText ? freeText.split(" ").filter(Boolean) : [],
      fields: fields,
    };
  }

  function levenshteinDistance(left, right) {
    const a = String(left || "");
    const b = String(right || "");
    if (a === b) return 0;
    if (!a.length) return b.length;
    if (!b.length) return a.length;

    const rows = a.length + 1;
    const cols = b.length + 1;
    const matrix = Array.from({ length: rows }, function (_, rowIndex) {
      const row = new Array(cols).fill(0);
      row[0] = rowIndex;
      return row;
    });

    for (let col = 0; col < cols; col += 1) matrix[0][col] = col;

    for (let row = 1; row < rows; row += 1) {
      for (let col = 1; col < cols; col += 1) {
        const cost = a[row - 1] === b[col - 1] ? 0 : 1;
        matrix[row][col] = Math.min(
          matrix[row - 1][col] + 1,
          matrix[row][col - 1] + 1,
          matrix[row - 1][col - 1] + cost,
        );
      }
    }
    return matrix[rows - 1][cols - 1];
  }

  function toBigrams(value) {
    const text = ` ${String(value || "")} `;
    if (text.length < 2) return [];
    const grams = [];
    for (let i = 0; i < text.length - 1; i += 1) {
      grams.push(text.slice(i, i + 2));
    }
    return grams;
  }

  function diceCoefficient(left, right) {
    const a = toBigrams(left);
    const b = toBigrams(right);
    if (!a.length || !b.length) return 0;

    const counts = new Map();
    a.forEach(function (gram) {
      counts.set(gram, (counts.get(gram) || 0) + 1);
    });

    let matches = 0;
    b.forEach(function (gram) {
      const count = counts.get(gram) || 0;
      if (count > 0) {
        matches += 1;
        counts.set(gram, count - 1);
      }
    });

    return (2 * matches) / (a.length + b.length);
  }

  function fuzzyTokenScore(fieldValue, term) {
    const field = normalizeSearchText(fieldValue);
    const token = normalizeSearchText(term);
    if (!field || !token) return 0;

    if (field === token) return 15;
    if (field.startsWith(token)) return 12;
    if (field.includes(token)) return 9;

    const fieldTokens = field.split(" ").filter(Boolean);
    let bestSimilarity = 0;
    fieldTokens.forEach(function (candidate) {
      const maxLength = Math.max(candidate.length, token.length) || 1;
      const editSimilarity = 1 - (levenshteinDistance(candidate, token) / maxLength);
      const diceSimilarity = diceCoefficient(candidate, token);
      const similarity = Math.max(editSimilarity, diceSimilarity);
      if (similarity > bestSimilarity) bestSimilarity = similarity;
    });

    if (bestSimilarity >= 0.92) return 7;
    if (bestSimilarity >= 0.84) return 5;
    if (bestSimilarity >= 0.74) return 3;
    return 0;
  }

  function containsFuzzyField(fieldValue, expectedValue) {
    const direct = fuzzyTokenScore(fieldValue, expectedValue);
    return direct >= 5;
  }

  function historySearchScore(item, parsedDate, parsedQuery) {
    const normalized = {
      name: normalizeSearchText(item.vegetable),
      scientific: normalizeSearchText(item.scientificName),
      category: normalizeSearchText(item.category),
      model: normalizeSearchText(item.modelName),
      date: normalizeSearchText(formatSingaporeDate(parsedDate)),
      time: normalizeSearchText(formatSingaporeTime(parsedDate)),
    };

    if (parsedQuery.fields.model && !containsFuzzyField(normalized.model, parsedQuery.fields.model)) return 0;
    if (parsedQuery.fields.category && !containsFuzzyField(normalized.category, parsedQuery.fields.category)) return 0;
    if (parsedQuery.fields.name && !containsFuzzyField(normalized.name, parsedQuery.fields.name)) return 0;
    if (parsedQuery.fields.scientific && !containsFuzzyField(normalized.scientific, parsedQuery.fields.scientific)) return 0;
    if (parsedQuery.fields.date && !containsFuzzyField(normalized.date, parsedQuery.fields.date)) return 0;

    if (!parsedQuery.terms.length) return 1;

    let totalScore = 0;
    for (const term of parsedQuery.terms) {
      const weightedScore = Math.max(
        fuzzyTokenScore(normalized.name, term) * 1.2,
        fuzzyTokenScore(normalized.scientific, term),
        fuzzyTokenScore(normalized.category, term) * 0.9,
        fuzzyTokenScore(normalized.model, term) * 0.8,
        fuzzyTokenScore(normalized.date, term) * 0.7,
        fuzzyTokenScore(normalized.time, term) * 0.6,
      );
      if (weightedScore <= 0) return 0;
      totalScore += weightedScore;
    }

    return totalScore + (normalizeConfidence(item.confidence) * 0.01);
  }

  function createIcons(root) {
    if (!window.lucide || typeof window.lucide.createIcons !== "function") return;
    window.lucide.createIcons({ icons: window.lucide.icons, nameAttr: "data-lucide", ...(root ? { root: root } : {}) });
  }

  function safe(value) {
    return api.escapeHtml ? api.escapeHtml(value) : String(value || "");
  }

  function normalizeConfidence(value) {
    const numeric = Number(value || 0);
    if (!Number.isFinite(numeric)) return 0;
    const percent = numeric <= 1 ? numeric * 100 : numeric;
    return Math.max(0, Math.min(100, percent));
  }

  function formatConfidence(value) {
    return `${normalizeConfidence(value).toFixed(1)}%`;
  }

  function showError(message) {
    const msg = String(message || "").trim();
    if (!msg) {
      dom.error.classList.add("hidden");
      dom.error.classList.remove("flex");
      dom.errorText.textContent = "";
      return;
    }
    dom.errorText.textContent = msg;
    dom.error.classList.remove("hidden");
    dom.error.classList.add("flex");
  }

  function applyImageFallbacks(root) {
    if (!root) return;
    const fallbackImage = "/static/images/tomato.jpg";
    root.querySelectorAll("img[data-fallback-image]").forEach(function (imageNode) {
      if (imageNode.dataset.fallbackBound === "1") return;
      imageNode.dataset.fallbackBound = "1";
      imageNode.addEventListener("error", function () {
        if (imageNode.dataset.fallbackApplied === "1") return;
        imageNode.dataset.fallbackApplied = "1";
        imageNode.src = fallbackImage;
      });
    });
  }

  function isInteractionBlocked() {
    return state.isAnalyzing;
  }

  function setSelectionControlsEnabled(enabled) {
    const disabled = !enabled;

    dom.modelSelect.disabled = disabled;
    dom.uploadInput.disabled = disabled;
    dom.browseFilesBtn.disabled = disabled;
    dom.openCameraBtn.disabled = disabled;
    dom.resetImages.disabled = disabled;

    dom.dropzone.classList.toggle("pointer-events-none", disabled);
    dom.dropzone.classList.toggle("opacity-80", disabled);
    dom.gallery.classList.toggle("pointer-events-none", disabled);
    dom.gallery.classList.toggle("opacity-80", disabled);

    dom.sampleButtons.forEach(function (button) {
      button.disabled = disabled;
      button.classList.toggle("opacity-60", disabled);
      button.classList.toggle("cursor-not-allowed", disabled);
    });
  }

  function setTab(tab) {
    const tabBaseClass = "w-full flex items-center justify-center gap-2 px-4 sm:px-6 py-3 rounded-lg font-medium transition-all";
    state.tab = tab === "history" ? "history" : "classify";
    const classify = state.tab === "classify";
    dom.tabClassify.className = `${tabBaseClass} ${classify ? "bg-primary-500 text-white shadow-md" : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"}`;
    dom.tabHistory.className = `${tabBaseClass} ${classify ? "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700" : "bg-primary-500 text-white shadow-md"}`;
    dom.panelClassify.classList.toggle("hidden", !classify);
    dom.panelHistory.classList.toggle("hidden", classify);
    if (!classify) void loadHistory();
  }

  async function loadModels() {
    const fallback = [
      { name: "vegnet-23", label: "VegNet-23 (23x23)", inputSize: "23x23" },
      { name: "vegnet-101", label: "VegNet-101 (101x101)", inputSize: "101x101" },
    ];
    try {
      const payload = await api.apiRequest("/api/veggie/models");
      const data = payload && payload.data ? payload.data : {};
      state.models = Array.isArray(data.models) && data.models.length ? data.models : fallback;
      state.selectedModel = data.default_model || state.models[0].name;
    } catch (_) {
      state.models = fallback;
      state.selectedModel = "vegnet-23";
    }

    dom.modelSelect.innerHTML = state.models.map(function (m) {
      return `<option value="${safe(m.name)}">${safe(m.label || m.name)}</option>`;
    }).join("");
    dom.modelSelect.value = state.selectedModel;
    updateModelMeta();
  }

  function updateModelMeta() {
    const selected = state.models.find(function (m) {
      return m.name === state.selectedModel;
    });
    if (!selected) {
      dom.modelMeta.innerHTML = "";
      return;
    }
    dom.modelMeta.innerHTML = `
      <span class="px-2.5 py-1 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-300 font-medium">
        Input ${safe(selected.inputSize || "-")}
      </span>
      <span class="text-gray-500 dark:text-gray-400 truncate">${selected.endpoint ? "Remote endpoint configured" : "Local model profile"}</span>
    `;
  }

  async function loadCatalog() {
    try {
      const payload = await api.apiRequest("/api/veggie/catalog");
      const items = payload && payload.data ? payload.data.vegetables : [];
      const mapped = {};
      (items || []).forEach(function (item) {
        const key = String(item.key || item.name || "").toLowerCase().replace(/\s+/g, "_");
        mapped[key] = item;
      });
      state.catalog = mapped;
    } catch (_) {
      state.catalog = { ...fallbackCatalog };
    }
  }

  function makeImage(source, preview, blob, name) {
    return { id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`, source: source, preview: preview, blob: blob, name: name || "image.jpg" };
  }

  function findImageBySource(source) {
    return state.images.findIndex(function (item) {
      return item.source === source;
    });
  }

  function addImage(item) {
    state.images.push(item);
    if (state.images.length === 1) state.currentImageIndex = 0;
    renderImages();
  }

  function removeImage(index) {
    const item = state.images[index];
    if (!item) return;
    if (item.preview && item.preview.startsWith("blob:")) URL.revokeObjectURL(item.preview);
    state.images.splice(index, 1);
    if (state.currentImageIndex >= state.images.length) state.currentImageIndex = Math.max(0, state.images.length - 1);
    renderImages();
  }

  function resetImages() {
    state.images.forEach(function (item) {
      if (item.preview && item.preview.startsWith("blob:")) URL.revokeObjectURL(item.preview);
    });
    state.images = [];
    state.currentImageIndex = 0;
    state.results = [];
    state.resultIndex = 0;
    renderImages();
    renderResults();
    showError("");
  }

  async function fileToImage(file) {
    return makeImage(`file:${file.name}:${file.size}:${file.lastModified}`, URL.createObjectURL(file), file, file.name);
  }

  async function sampleToImage(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error("Unable to load sample image");
    const blob = await response.blob();
    return makeImage(`sample:${url}`, url, blob, url.split("/").pop() || "sample.jpg");
  }

  function updateSampleButtons() {
    dom.sampleButtons.forEach(function (button) {
      const sample = button.getAttribute("data-sample") || "";
      const selected = findImageBySource(`sample:${sample}`) >= 0;
      button.classList.toggle("ring-2", selected);
      button.classList.toggle("ring-primary-500", selected);
      const overlay = button.querySelector(".sample-overlay");
      if (overlay) overlay.classList.toggle("hidden", !selected);
    });
  }
  function renderGallery() {
    if (state.images.length <= 1) {
      dom.gallery.classList.add("hidden");
      dom.gallery.innerHTML = "";
      return;
    }

    dom.gallery.classList.remove("hidden");
    dom.gallery.innerHTML = state.images.map(function (item, index) {
      const active = state.currentImageIndex === index;
      return `
        <div class="relative aspect-square rounded-lg overflow-hidden cursor-pointer border-2 transition-all ${active ? "border-primary-500 ring-2 ring-primary-500/50" : "border-transparent hover:border-gray-300 dark:hover:border-gray-600"}" data-gallery-index="${index}">
          <img src="${safe(item.preview)}" alt="Selected ${index + 1}" class="w-full h-full object-cover" />
          <button type="button" data-gallery-remove="${index}" class="absolute top-1 right-1 p-1 rounded-full bg-black/70 text-white hover:bg-red-500 transition-colors">
            <i data-lucide="x" class="w-3 h-3"></i>
          </button>
          <div class="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/70 text-white text-xs font-medium">${index + 1}</div>
        </div>
      `;
    }).join("");

    createIcons(dom.gallery);
  }

  function renderImages() {
    const has = state.images.length > 0;
    dom.dropEmpty.classList.toggle("hidden", has);
    dom.dropPreview.classList.toggle("hidden", !has);
    dom.initialActions.classList.toggle("hidden", has);
    dom.activeActions.classList.toggle("hidden", !has);

    if (!has) {
      dom.dropzone.className = "relative aspect-square rounded-2xl border-2 border-dashed transition-all duration-300 cursor-pointer overflow-hidden border-gray-300 dark:border-gray-700 hover:border-primary-400 dark:hover:border-primary-500 hover:bg-gray-50 dark:hover:bg-gray-800/50";
      dom.imageCounter.classList.add("hidden");
      updateSampleButtons();
      renderGallery();
      return;
    }

    dom.dropzone.className = "relative aspect-square rounded-2xl border-2 border-dashed transition-all duration-300 cursor-pointer overflow-hidden border-transparent";
    const current = state.images[state.currentImageIndex];
    dom.selectedImage.src = current.preview;

    if (state.images.length > 1) {
      dom.imageCounter.classList.remove("hidden");
      dom.imageCounter.textContent = `${state.currentImageIndex + 1} / ${state.images.length}`;
    } else {
      dom.imageCounter.classList.add("hidden");
    }

    updateSampleButtons();
    renderGallery();
  }

  function keyFromPrediction(item) {
    const direct = String(item.key || "").trim();
    if (direct) return direct.toLowerCase();
    return String(item.vegetable || "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  }

  function bestPrice(prices) {
    const values = Object.values(prices || {}).map(function (v) {
      return Number(v || 0);
    });
    return values.length ? Math.min.apply(null, values) : null;
  }

  function renderResults() {
    const has = state.results.length > 0;
    dom.resultEmpty.classList.toggle("hidden", has);
    dom.resultList.classList.toggle("hidden", !has);

    if (!has) {
      dom.resultList.innerHTML = "";
      return;
    }

    const isBatch = state.results.length > 1;
    const activeIndex = isBatch ? Math.max(0, Math.min(state.resultIndex, state.results.length - 1)) : 0;
    state.resultIndex = activeIndex;
    const visibleResults = isBatch ? [state.results[activeIndex]] : state.results;
    const cards = visibleResults.map(function (result, visibleIndex) {
      const idx = isBatch ? activeIndex : visibleIndex;
      const key = keyFromPrediction(result);
      const info = state.catalog[key] || state.catalog[key.replace(/_/g, "")] || null;
      const nutrients = info && Array.isArray(info.nutrients) ? info.nutrients : [];
      const cheapest = bestPrice(result.prices || {});
      const confidence = normalizeConfidence(result.confidence);
      const resultDate = parseTimestamp(result.timestamp);
      const priceRows = Object.entries(result.prices || {}).filter(function (entry) {
        return Number(entry[1] || 0) > 0;
      }).sort(function (left, right) {
        return Number(left[1] || 0) - Number(right[1] || 0);
      }).slice(0, 3);

      return `
        <article class="prediction-batch-card card overflow-hidden w-full">
          <div class="relative">
            <img
              src="${safe(result.image || "")}"
              alt="${safe(result.vegetable || "Prediction image")}"
              data-fallback-image="1"
              class="w-full h-64 sm:h-72 md:h-80 lg:h-[22rem] object-cover"
            />
            <div class="absolute top-3 left-3" style="position:absolute; top:0.75rem; left:0.75rem; z-index:3; pointer-events:none;">
              <span class="inline-flex max-w-[70%] items-center truncate px-2.5 py-1 rounded-lg bg-black/55 text-white text-xs font-semibold backdrop-blur-sm">
                ${isBatch ? `Result ${idx + 1} / ${state.results.length}` : "Classification Result"}
              </span>
            </div>
            <div class="absolute top-3 right-3" style="position:absolute; top:0.75rem; right:0.75rem; z-index:4; pointer-events:none;">
              <div class="rounded-xl border border-white/25 bg-gradient-to-r from-emerald-500/95 to-green-600/95 px-3 py-2 text-right text-white shadow-lg shadow-emerald-950/30 backdrop-blur-sm">
                <p class="text-[10px] uppercase tracking-[0.2em] text-white/90">Confidence</p>
                <p class="text-lg sm:text-xl font-extrabold leading-none">${formatConfidence(confidence)}</p>
              </div>
            </div>
          </div>

          <div class="p-5 space-y-4">
            <div>
              <h2 class="text-2xl font-bold text-gray-900 dark:text-white">${safe(result.vegetable || "-")}</h2>
              <p class="text-gray-500 dark:text-gray-400 italic text-sm">${safe(result.scientificName || "")}</p>
            </div>

            <div class="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                class="h-full bg-gradient-to-r from-primary-500 to-accent-500 transition-all duration-1000"
                style="width: ${confidence}%"
              ></div>
            </div>

            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div class="p-3 rounded-xl bg-gray-50 dark:bg-gray-800">
                <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Category</p>
                <p class="font-semibold text-gray-900 dark:text-white">${safe(result.category || "-")}</p>
              </div>
              <div class="p-3 rounded-xl bg-gray-50 dark:bg-gray-800">
                <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Model</p>
                <p class="font-semibold text-gray-900 dark:text-white">${safe(result.modelName || state.selectedModel)}</p>
              </div>
              <div class="p-3 rounded-xl bg-gray-50 dark:bg-gray-800">
                <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Date (SGT)</p>
                <p class="font-semibold text-gray-900 dark:text-white">${safe(formatSingaporeDate(resultDate))}</p>
              </div>
              <div class="p-3 rounded-xl bg-gray-50 dark:bg-gray-800">
                <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Best Price</p>
                <p class="font-semibold text-gray-900 dark:text-white">${cheapest === null ? "-" : `$${cheapest.toFixed(2)}`}</p>
              </div>
            </div>

            ${priceRows.length
              ? `<div class="space-y-2">
                  <p class="text-sm font-semibold text-gray-900 dark:text-white">Price Snapshot</p>
                  <div class="space-y-1.5">
                    ${priceRows.map(function (entry) {
                      return `
                        <div class="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm">
                          <span class="text-gray-600 dark:text-gray-300">${safe(String(entry[0] || "-"))}</span>
                          <span class="font-semibold text-gray-900 dark:text-white">$${Number(entry[1] || 0).toFixed(2)}</span>
                        </div>
                      `;
                    }).join("")}
                  </div>
                </div>`
              : ""}

            ${info
              ? `<div class="space-y-3 pt-1">
                  <p class="text-sm text-gray-600 dark:text-gray-400">${safe(info.description || "")}</p>
                  ${nutrients.length
                    ? `<div class="flex flex-wrap gap-2">
                        ${nutrients.slice(0, 6).map(function (nutrient) {
                          return `<span class="px-2.5 py-1 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 text-xs">${safe(nutrient)}</span>`;
                        }).join("")}
                      </div>`
                    : ""}
                </div>`
              : ""}
          </div>
        </article>
      `;
    }).join("");

    const atFirst = !isBatch || activeIndex <= 0;
    const atLast = !isBatch || activeIndex >= state.results.length - 1;

    dom.resultList.innerHTML = `
      <div class="card p-4 sm:p-5 space-y-4">
        ${isBatch
          ? `<div class="flex items-center justify-between gap-3">
              <p class="text-sm font-medium text-gray-600 dark:text-gray-300">Result ${activeIndex + 1} of ${state.results.length}</p>
              <div class="flex items-center gap-2">
                <button id="batch-result-prev" type="button" class="btn-secondary px-3 py-2 ${atFirst ? "opacity-50 cursor-not-allowed" : ""}" aria-label="Previous result" ${atFirst ? "disabled" : ""}>
                  <i data-lucide="chevron-left" class="w-4 h-4"></i>
                </button>
                <button id="batch-result-next" type="button" class="btn-secondary px-3 py-2 ${atLast ? "opacity-50 cursor-not-allowed" : ""}" aria-label="Next result" ${atLast ? "disabled" : ""}>
                  <i data-lucide="chevron-right" class="w-4 h-4"></i>
                </button>
              </div>
            </div>`
          : ""}
        <div
          id="batch-result-track"
          class="space-y-4"
          tabindex="-1"
          role="none"
          aria-label="${isBatch ? "Batch prediction results" : "Prediction result"}"
        >
          ${cards}
        </div>
      </div>
      <button id="classify-another-btn" type="button" class="w-full btn-secondary">Classify Another</button>
    `;

    const button = document.getElementById("classify-another-btn");
    if (button) button.addEventListener("click", resetImages);

    createIcons(dom.resultList);
    applyImageFallbacks(dom.resultList);

    if (isBatch) {
      const prev = document.getElementById("batch-result-prev");
      const next = document.getElementById("batch-result-next");
      if (prev) prev.addEventListener("click", function () {
        if (state.resultIndex <= 0) return;
        state.resultIndex -= 1;
        renderResults();
      });
      if (next) next.addEventListener("click", function () {
        if (state.resultIndex >= state.results.length - 1) return;
        state.resultIndex += 1;
        renderResults();
      });
    }
  }

  function setAnalyzeState(loading, progress) {
    state.isAnalyzing = Boolean(loading);
    setSelectionControlsEnabled(!state.isAnalyzing);
    dom.predictBtn.disabled = state.isAnalyzing;
    dom.predictLoader.classList.toggle("hidden", !state.isAnalyzing);
    dom.predictIcon.classList.toggle("hidden", state.isAnalyzing);
    dom.predictLabel.textContent = state.isAnalyzing ? "Analyzing..." : "Classify Vegetable";
    dom.analyzingOverlay.classList.toggle("hidden", !state.isAnalyzing);
    dom.analyzingOverlay.classList.toggle("flex", state.isAnalyzing);
    const pct = Math.max(0, Math.min(100, Number(progress || 0)));
    dom.analyzingProgress.style.width = `${pct}%`;
    dom.analyzingText.textContent = `Analyzing... ${Math.round(pct)}%`;
  }

  function stopAnalyzeProgressTicker() {
    if (!state.analyzingProgressTimer) return;
    clearInterval(state.analyzingProgressTimer);
    state.analyzingProgressTimer = null;
  }

  function startAnalyzeProgressTicker(targetPercent) {
    const target = Math.max(0, Math.min(100, Number(targetPercent || 0)));
    stopAnalyzeProgressTicker();
    state.analyzingProgressTimer = setInterval(function () {
      const remaining = target - state.analyzingProgressValue;
      if (remaining <= 0.15) {
        state.analyzingProgressValue = target;
        setAnalyzeState(true, state.analyzingProgressValue);
        stopAnalyzeProgressTicker();
        return;
      }

      const step = Math.max(0.25, Math.min(2.1, remaining * 0.1));
      state.analyzingProgressValue = Math.min(target, state.analyzingProgressValue + step);
      setAnalyzeState(true, state.analyzingProgressValue);
    }, 110);
  }

  async function ensureBlob(item) {
    if (item.blob instanceof Blob) return item.blob;
    const response = await fetch(item.preview);
    if (!response.ok) throw new Error("Failed to read selected image");
    return response.blob();
  }

  async function classifyImages() {
    if (!state.images.length || state.isAnalyzing) return;

    showError("");
    state.results = [];
    state.resultIndex = 0;
    state.analyzingProgressValue = 0;
    stopAnalyzeProgressTicker();
    renderResults();
    setAnalyzeState(true, state.analyzingProgressValue);

    try {
      for (let i = 0; i < state.images.length; i += 1) {
        const segmentStart = (i / state.images.length) * 100;
        const segmentEnd = ((i + 1) / state.images.length) * 100;

        state.analyzingProgressValue = Math.max(state.analyzingProgressValue, segmentStart);
        setAnalyzeState(true, state.analyzingProgressValue);
        startAnalyzeProgressTicker(segmentStart + ((segmentEnd - segmentStart) * 0.88));

        const blob = await ensureBlob(state.images[i]);
        const file = new File([blob], state.images[i].name || `upload-${i + 1}.jpg`, { type: blob.type || "image/jpeg" });
        const form = new FormData();
        form.append("image", file);
        form.append("model_name", state.selectedModel);
        const payload = await api.apiRequest("/api/veggie/predict", { method: "POST", isForm: true, body: form });
        const prediction = payload && payload.data ? payload.data.prediction : null;
        if (!prediction) throw new Error("Prediction response was empty");

        state.results.push({
          id: prediction.id,
          image: prediction.image,
          key: prediction.key,
          vegetable: prediction.vegetable,
          confidence: normalizeConfidence(prediction.confidence),
          scientificName: prediction.scientificName,
          timestamp: prediction.timestamp,
          category: prediction.category,
          modelName: prediction.modelName || state.selectedModel,
          prices: prediction.prices || {},
        });

        stopAnalyzeProgressTicker();
        state.analyzingProgressValue = Math.max(
          state.analyzingProgressValue,
          segmentStart + ((segmentEnd - segmentStart) * 0.95),
        );
        setAnalyzeState(true, state.analyzingProgressValue);
      }

      startAnalyzeProgressTicker(100);
      await new Promise(function (resolve) { setTimeout(resolve, 260); });
      stopAnalyzeProgressTicker();
      state.analyzingProgressValue = 100;
      setAnalyzeState(true, state.analyzingProgressValue);
      renderResults();
      await loadHistory();
    } catch (error) {
      stopAnalyzeProgressTicker();
      showError(error && error.message ? error.message : "Classification failed.");
    } finally {
      stopAnalyzeProgressTicker();
      setTimeout(function () {
        state.analyzingProgressValue = 0;
        setAnalyzeState(false, 0);
      }, 280);
    }
  }

  function mapHistoryItem(item) {
    return {
      id: item.id,
      image: item.image,
      key: item.key,
      vegetable: item.vegetable,
      confidence: normalizeConfidence(item.confidence),
      scientificName: item.scientificName,
      timestamp: item.timestamp,
      category: item.category,
      modelName: item.modelName || "vegnet-23",
      prices: item.prices || {},
    };
  }

  function filteredHistory() {
    const parsedQuery = parseSearchQuery(state.filters.search);
    const category = normalizeSearchText(state.filters.category);
    const model = normalizeSearchText(state.filters.model);
    const hasSearch = Boolean(parsedQuery.rawText);

    const sorted = state.history.map(function (item) {
      const parsedDate = parseTimestamp(item.timestamp);
      return {
        ...item,
        _parsedDate: parsedDate,
        _searchScore: historySearchScore(item, parsedDate, parsedQuery),
      };
    }).filter(function (item) {
      if (category !== "all" && normalizeSearchText(item.category) !== category) return false;
      if (model !== "all" && normalizeSearchText(item.modelName) !== model) return false;
      if (hasSearch && item._searchScore <= 0) return false;
      return true;
    });

    sorted.sort(function (a, b) {
      let compare = 0;
      if (state.filters.sort === "confidence") {
        compare = a.confidence - b.confidence;
      } else if (state.filters.sort === "name") {
        compare = String(a.vegetable || "").localeCompare(String(b.vegetable || ""));
      } else if (state.filters.sort === "model") {
        compare = String(a.modelName || "").localeCompare(String(b.modelName || ""));
      } else if (state.filters.sort === "relevance") {
        compare = a._searchScore - b._searchScore;
      } else {
        compare = a._parsedDate.getTime() - b._parsedDate.getTime();
      }
      if (compare === 0) {
        compare = a._parsedDate.getTime() - b._parsedDate.getTime();
      }
      return state.filters.order === "asc" ? compare : -compare;
    });

    return sorted;
  }

  function updateCategoryOptions() {
    const categories = Array.from(new Set(state.history.map(function (item) { return String(item.category || "").trim(); }).filter(Boolean)));
    dom.historyCategory.innerHTML = ["all"].concat(categories).map(function (cat) {
      return `<option value="${safe(cat)}">${cat === "all" ? "All Categories" : safe(cat)}</option>`;
    }).join("");
    dom.historyCategory.value = state.filters.category;
    if (dom.historyCategory.value !== state.filters.category) {
      state.filters.category = "all";
      dom.historyCategory.value = "all";
    }
  }

  function updateModelOptions() {
    if (!dom.historyModel) return;
    const models = Array.from(new Set(state.history.map(function (item) { return String(item.modelName || "").trim(); }).filter(Boolean)));
    dom.historyModel.innerHTML = ["all"].concat(models).map(function (model) {
      return `<option value="${safe(model)}">${model === "all" ? "All Models" : safe(model)}</option>`;
    }).join("");
    dom.historyModel.value = state.filters.model;
    if (dom.historyModel.value !== state.filters.model) {
      state.filters.model = "all";
      dom.historyModel.value = "all";
    }
  }

  function renderHistoryOverviewTable(rows) {
    if (!dom.historyOverviewTableShell || !dom.historyOverviewTableBody) return;

    const hasRows = Array.isArray(rows) && rows.length > 0;
    dom.historyOverviewTableShell.classList.toggle("hidden", !hasRows);

    if (!hasRows) {
      dom.historyOverviewTableBody.innerHTML = "";
      if (dom.historyOverviewMeta) {
        dom.historyOverviewMeta.textContent = "Filtered rows: 0";
      }
      return;
    }

    const previewLimit = 12;
    const previewRows = rows.slice(0, previewLimit);
    dom.historyOverviewTableBody.innerHTML = previewRows.map(function (item, index) {
      const date = item._parsedDate || parseTimestamp(item.timestamp);
      const confidence = normalizeConfidence(item.confidence);
      return `
        <tr class="group transition-colors">
          <td class="px-4 py-2.5 text-xs text-gray-500 dark:text-gray-400">${index + 1}</td>
          <td class="px-4 py-2.5">
            <p class="font-medium text-gray-900 dark:text-white">${safe(item.vegetable || "-")}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400 italic truncate max-w-[16rem]">${safe(item.scientificName || "")}</p>
          </td>
          <td class="px-4 py-2.5 text-xs font-semibold text-gray-900 dark:text-gray-100">${formatConfidence(confidence)}</td>
          <td class="px-4 py-2.5 text-xs text-gray-600 dark:text-gray-300">${safe(item.modelName || "vegnet-23")}</td>
          <td class="px-4 py-2.5 text-xs text-gray-600 dark:text-gray-300">${safe(formatSingaporeDate(date))}</td>
          <td class="px-4 py-2.5 text-xs text-gray-600 dark:text-gray-300">${safe(formatSingaporeTime(date))}</td>
          <td class="px-4 py-2.5 text-right">
            <button type="button" class="px-2.5 py-1 rounded-md border border-gray-300 dark:border-gray-600 text-xs font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700" data-history-open="${safe(item.id)}">Open</button>
          </td>
        </tr>
      `;
    }).join("");

    if (dom.historyOverviewMeta) {
      dom.historyOverviewMeta.textContent = previewRows.length < rows.length
        ? `Showing ${previewRows.length} of ${rows.length} filtered rows`
        : `Filtered rows: ${rows.length}`;
    }
  }

  function renderHistory() {
    const rows = filteredHistory();
    renderHistoryOverviewTable(rows);
    dom.historyList.innerHTML = rows.map(function (item) {
      const date = item._parsedDate || parseTimestamp(item.timestamp);
      const confidence = normalizeConfidence(item.confidence);
      return `
        <div class="card card-hover cursor-pointer overflow-hidden group" data-history-id="${safe(item.id)}">
          <div class="aspect-video relative">
            <img src="${safe(item.image)}" alt="${safe(item.vegetable)}" data-fallback-image="1" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
            <div class="absolute top-2 right-2 flex gap-2"><span class="px-2 py-1 rounded-lg bg-black/50 backdrop-blur-sm text-white text-sm font-semibold">${formatConfidence(confidence)}</span></div>
            <button type="button" class="absolute top-2 left-2 p-2 rounded-lg bg-black/50 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500" data-history-delete="${safe(item.id)}"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
          </div>
          <div class="p-4">
            <h3 class="font-semibold text-gray-900 dark:text-white">${safe(item.vegetable || "-")}</h3>
            <p class="text-sm text-gray-500 dark:text-gray-400 italic mb-2">${safe(item.scientificName || "")}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">Model: ${safe(item.modelName || "vegnet-23")}</p>
            <div class="flex items-center justify-between text-xs text-gray-400">
              <span class="flex items-center gap-1"><i data-lucide="calendar" class="w-3 h-3"></i>${safe(formatSingaporeDate(date))}</span>
              <span class="flex items-center gap-1"><i data-lucide="clock" class="w-3 h-3"></i>${safe(formatSingaporeTime(date))} SGT</span>
            </div>
          </div>
        </div>
      `;
    }).join("");

    const has = rows.length > 0;
    dom.historyEmpty.classList.toggle("hidden", has);
    if (!has) {
      if (state.filters.search || state.filters.category !== "all" || state.filters.model !== "all") {
        dom.historyEmptyTitle.textContent = "No Results Found";
        dom.historyEmptyText.textContent = "Try adjusting your search or filters.";
      } else {
        dom.historyEmptyTitle.textContent = "No Predictions Yet";
        dom.historyEmptyText.textContent = "Start classifying vegetables to build your history.";
      }
    }

    createIcons(dom.historyList);
    applyImageFallbacks(dom.historyList);
  }

  async function loadHistory() {
    const payload = await api.apiRequest("/api/veggie/history?page=1&page_size=100");
    const items = payload && payload.data ? payload.data.items : [];
    state.history = Array.isArray(items) ? items.map(mapHistoryItem) : [];
    dom.historyCount.textContent = String(state.history.length);
    dom.historyCount.classList.toggle("hidden", state.history.length === 0);
    dom.historyTotal.textContent = `${state.history.length} total predictions`;
    dom.historyExport.disabled = state.history.length === 0;
    dom.historyClear.disabled = state.history.length === 0;
    updateCategoryOptions();
    updateModelOptions();
    renderHistory();
  }
  function openDetail(item) {
    const date = parseTimestamp(item.timestamp);
    const cheapest = bestPrice(item.prices || {});
    const confidence = normalizeConfidence(item.confidence);
    dom.detailImage.src = item.image;
    dom.detailImage.alt = item.vegetable || "Vegetable";
    dom.detailImage.setAttribute("data-fallback-image", "1");
    dom.detailImage.removeAttribute("data-fallback-applied");
    dom.detailBody.innerHTML = `
      <div class="flex items-start justify-between">
        <div>
          <span class="inline-block px-3 py-1 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 text-sm font-medium mb-2">${safe(item.category || "-")}</span>
          <h2 class="text-2xl font-bold text-gray-900 dark:text-white">${safe(item.vegetable || "-")}</h2>
          <p class="text-gray-500 dark:text-gray-400 italic">${safe(item.scientificName || "")}</p>
        </div>
        <div class="text-right"><div class="text-3xl font-bold text-primary-600 dark:text-primary-400">${formatConfidence(confidence)}</div><p class="text-sm text-gray-500">Confidence</p></div>
      </div>
      <div class="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden"><div class="h-full bg-gradient-to-r from-primary-500 to-accent-500" style="width: ${confidence}%"></div></div>
      <div class="grid grid-cols-1 sm:grid-cols-4 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div><p class="text-sm text-gray-500 dark:text-gray-400">Date (SGT)</p><p class="font-medium text-gray-900 dark:text-white">${safe(formatSingaporeDate(date))}</p></div>
        <div><p class="text-sm text-gray-500 dark:text-gray-400">Time (SGT)</p><p class="font-medium text-gray-900 dark:text-white">${safe(formatSingaporeTime(date))}</p></div>
        <div><p class="text-sm text-gray-500 dark:text-gray-400">Model</p><p class="font-medium text-gray-900 dark:text-white">${safe(item.modelName || "-")}</p></div>
        <div><p class="text-sm text-gray-500 dark:text-gray-400">Best Price</p><p class="font-medium text-gray-900 dark:text-white">${cheapest === null ? "-" : `$${cheapest.toFixed(2)}`}</p></div>
      </div>
      <button id="history-detail-delete" type="button" class="w-full btn-secondary text-red-600 dark:text-red-400 flex items-center justify-center gap-2"><i data-lucide="trash-2" class="w-4 h-4"></i>Delete Prediction</button>
    `;

    const del = document.getElementById("history-detail-delete");
    if (del) {
      del.addEventListener("click", function () {
        state.pendingDeleteId = item.id;
        dom.deleteModal.classList.remove("hidden");
        dom.deleteModal.classList.add("flex");
      });
    }

    dom.detailModal.classList.remove("hidden");
    dom.detailModal.classList.add("flex");
    createIcons(dom.detailModal);
    applyImageFallbacks(dom.detailModal);
  }

  function closeDetail() {
    dom.detailModal.classList.add("hidden");
    dom.detailModal.classList.remove("flex");
  }

  async function deleteHistoryItem(id) {
    await api.apiRequest(`/api/veggie/history/${encodeURIComponent(id)}`, { method: "DELETE" });
    state.pendingDeleteId = null;
    dom.deleteModal.classList.add("hidden");
    dom.deleteModal.classList.remove("flex");
    closeDetail();
    await loadHistory();
  }

  async function clearHistoryAll() {
    await api.apiRequest("/api/veggie/history", { method: "DELETE" });
    dom.clearModal.classList.add("hidden");
    dom.clearModal.classList.remove("flex");
    closeDetail();
    await loadHistory();
  }

  function exportHistory() {
    const data = JSON.stringify(state.history, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `vegetable-history-${new Date().toISOString().split("T")[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function setFiltersOpen(open) {
    state.filtersOpen = Boolean(open);
    dom.historyFilters.classList.toggle("hidden", !state.filtersOpen);
    dom.historyFilterChevron.classList.toggle("rotate-180", state.filtersOpen);
    dom.historyFilterToggle.classList.toggle("ring-2", state.filtersOpen);
    dom.historyFilterToggle.classList.toggle("ring-primary-500", state.filtersOpen);
  }

  async function startCamera() {
    try {
      if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") {
        throw new Error("Camera API is unavailable in this browser.");
      }

      state.camera.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: state.camera.facingMode, width: { ideal: 1920 }, height: { ideal: 1080 } },
      });
      dom.cameraVideo.srcObject = state.camera.stream;
      dom.cameraFlipBtn.disabled = false;
      dom.cameraDetectError.classList.add("hidden");
    } catch (error) {
      dom.cameraFlipBtn.disabled = true;
      const message = error && error.message ? error.message : "";
      const details = message ? ` (${message})` : "";
      dom.cameraDetectError.textContent = `Unable to access camera. Please check browser/site permissions and HTTPS/localhost.${details}`;
      dom.cameraDetectError.classList.remove("hidden");
    }
  }

  function stopCamera() {
    if (state.camera.stream) {
      state.camera.stream.getTracks().forEach(function (track) {
        track.stop();
      });
      state.camera.stream = null;
    }
    if (state.camera.interval) {
      clearInterval(state.camera.interval);
      state.camera.interval = null;
    }
    state.camera.inFlight = false;
  }

  function hideCameraDetectionRegion() {
    if (!dom.cameraDetectionRegion) return;
    dom.cameraDetectionRegion.classList.add("hidden");
  }

  function drawCameraDetectionRegion(detection) {
    if (!dom.cameraDetectionRegion || !dom.cameraStage || !dom.cameraVideo) return;

    const box = detection && typeof detection === "object" && detection.box && typeof detection.box === "object"
      ? detection.box
      : null;
    if (!box) {
      hideCameraDetectionRegion();
      return;
    }

    let x = Number(box.x);
    let y = Number(box.y);
    let width = Number(box.width);
    let height = Number(box.height);
    if (![x, y, width, height].every(Number.isFinite) || width <= 0 || height <= 0) {
      hideCameraDetectionRegion();
      return;
    }

    const videoWidth = Number(dom.cameraVideo.videoWidth || 0);
    const videoHeight = Number(dom.cameraVideo.videoHeight || 0);
    if (videoWidth <= 0 || videoHeight <= 0) {
      hideCameraDetectionRegion();
      return;
    }

    // Support both absolute pixel coordinates and normalized [0..1] coordinates.
    if (Math.max(Math.abs(x), Math.abs(y), Math.abs(width), Math.abs(height)) <= 1.2) {
      x *= videoWidth;
      y *= videoHeight;
      width *= videoWidth;
      height *= videoHeight;
    }

    const stageRect = dom.cameraStage.getBoundingClientRect();
    const stageWidth = stageRect.width;
    const stageHeight = stageRect.height;
    if (stageWidth <= 0 || stageHeight <= 0) {
      hideCameraDetectionRegion();
      return;
    }

    const videoAspect = videoWidth / videoHeight;
    const stageAspect = stageWidth / stageHeight;
    let renderedWidth = 0;
    let renderedHeight = 0;
    let offsetX = 0;
    let offsetY = 0;

    if (videoAspect > stageAspect) {
      renderedWidth = stageWidth;
      renderedHeight = renderedWidth / videoAspect;
      offsetY = (stageHeight - renderedHeight) / 2;
    } else {
      renderedHeight = stageHeight;
      renderedWidth = renderedHeight * videoAspect;
      offsetX = (stageWidth - renderedWidth) / 2;
    }

    const targetWidth = Math.max(24, (width / videoWidth) * renderedWidth);
    const targetHeight = Math.max(24, (height / videoHeight) * renderedHeight);
    const rawLeft = ((x - (width / 2)) / videoWidth) * renderedWidth + offsetX;
    const rawTop = ((y - (height / 2)) / videoHeight) * renderedHeight + offsetY;
    const clampedLeft = Math.max(0, Math.min(stageWidth - targetWidth, rawLeft));
    const clampedTop = Math.max(0, Math.min(stageHeight - targetHeight, rawTop));

    dom.cameraDetectionRegion.style.left = `${clampedLeft}px`;
    dom.cameraDetectionRegion.style.top = `${clampedTop}px`;
    dom.cameraDetectionRegion.style.width = `${targetWidth}px`;
    dom.cameraDetectionRegion.style.height = `${targetHeight}px`;
    dom.cameraDetectionRegion.classList.remove("hidden");

    if (dom.cameraDetectionLabel) {
      const label = String(detection.label || "Vegetable").replace(/_/g, " ");
      dom.cameraDetectionLabel.textContent = `${label} · ${formatConfidence(detection.confidence)}`;
    }
  }

  async function detectLiveFrame() {
    if (state.camera.mode !== "live" || state.camera.inFlight || !state.camera.stream) return;
    if (!dom.cameraVideo.videoWidth || !dom.cameraVideo.videoHeight) return;

    state.camera.inFlight = true;
    try {
      dom.cameraCanvas.width = dom.cameraVideo.videoWidth;
      dom.cameraCanvas.height = dom.cameraVideo.videoHeight;
      const ctx = dom.cameraCanvas.getContext("2d");
      if (!ctx) return;
      ctx.drawImage(dom.cameraVideo, 0, 0, dom.cameraCanvas.width, dom.cameraCanvas.height);
      const blob = await new Promise(function (resolve) { dom.cameraCanvas.toBlob(resolve, "image/jpeg", 0.85); });
      if (!blob) return;

      const form = new FormData();
      form.append("image", blob, "frame.jpg");
      const payload = await api.apiRequest("/api/veggie/detect", { method: "POST", isForm: true, body: form });
      const detection = payload && payload.data ? payload.data.detection : null;
      if (!detection) {
        dom.cameraLiveResult.classList.add("hidden");
        hideCameraDetectionRegion();
        return;
      }
      const confidence = normalizeConfidence(detection.confidence);
      drawCameraDetectionRegion(detection);

      dom.cameraLiveResult.innerHTML = `
        <div class="flex items-center gap-3 mb-3"><i data-lucide="scan" class="w-6 h-6 text-primary-400 animate-pulse"></i><div><p class="text-white font-bold text-xl capitalize">${safe(String(detection.label || "Unknown").replace(/_/g, " "))}</p><p class="text-gray-400 text-sm">Live Detection Active</p></div></div>
        <div class="space-y-2"><div class="flex items-center justify-between text-sm"><span class="text-gray-400">Confidence</span><span class="text-primary-400 font-bold">${formatConfidence(confidence)}</span></div><div class="h-2 bg-gray-700 rounded-full overflow-hidden"><div class="h-full bg-gradient-to-r from-primary-500 to-accent-500 transition-all duration-500" style="width: ${confidence}%"></div></div></div>
      `;
      dom.cameraLiveResult.classList.remove("hidden");
      dom.cameraDetectError.classList.add("hidden");
      createIcons(dom.cameraLiveResult);
    } catch (error) {
      dom.cameraLiveResult.classList.add("hidden");
      hideCameraDetectionRegion();
      const status = error && typeof error.status === "number" ? error.status : 0;
      const unavailable = status === 503;
      if (unavailable && state.camera.interval) {
        clearInterval(state.camera.interval);
        state.camera.interval = null;
      }
      dom.cameraDetectError.textContent = unavailable
        ? "Live Detect is unavailable right now. Configure backend .env with ROBOFLOW_API_KEY + ROBOFLOW_MODEL_ID, or ROBOFLOW_API_KEY + ROBOFLOW_WORKSPACE/ROBOFLOW_WORKFLOW_ID, then restart the server."
        : (error && error.message ? error.message : "Live detection failed");
      dom.cameraDetectError.classList.remove("hidden");
    } finally {
      state.camera.inFlight = false;
    }
  }

  function setCameraMode(mode) {
    state.camera.mode = mode === "live" ? "live" : "capture";
    const capture = state.camera.mode === "capture";
    dom.cameraModeCapture.className = `px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${capture ? "bg-primary-600 text-white" : "text-white/70 hover:text-white"}`;
    dom.cameraModeLive.className = `px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${capture ? "text-white/70 hover:text-white" : "bg-primary-600 text-white"}`;
    if (dom.cameraModeCaptureBottom) {
      dom.cameraModeCaptureBottom.className = `px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${capture ? "bg-primary-600 text-white" : "text-white/80 hover:text-white bg-white/10"}`;
    }
    if (dom.cameraModeLiveBottom) {
      dom.cameraModeLiveBottom.className = `px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${capture ? "text-white/80 hover:text-white bg-white/10" : "bg-primary-600 text-white"}`;
    }

    dom.cameraCaptureActions.classList.toggle("hidden", !capture || Boolean(state.camera.capturedBlob));
    dom.cameraPreviewActions.classList.toggle("hidden", !capture || !state.camera.capturedBlob);
    dom.cameraLiveActions.classList.toggle("hidden", capture);
    dom.cameraCaptureHint.classList.toggle("hidden", !capture || Boolean(state.camera.capturedBlob));
    dom.cameraLiveScan.classList.toggle("hidden", capture);
    if (dom.cameraFocusBox) {
      dom.cameraFocusBox.classList.toggle("hidden", !capture);
    }

    if (capture) {
      if (state.camera.interval) {
        clearInterval(state.camera.interval);
        state.camera.interval = null;
      }
      dom.cameraLiveResult.classList.add("hidden");
      hideCameraDetectionRegion();
    } else if (state.camera.stream) {
      if (state.camera.interval) {
        clearInterval(state.camera.interval);
      }
      hideCameraDetectionRegion();
      void detectLiveFrame();
      state.camera.interval = setInterval(function () {
        void detectLiveFrame();
      }, 2500);
    }
  }

  async function openCamera() {
    if (isInteractionBlocked()) return;
    document.body.classList.add("camera-open");
    hideCameraDetectionRegion();
    state.camera.capturedBlob = null;
    dom.cameraPreview.src = "";
    dom.cameraPreview.classList.add("hidden");
    dom.cameraVideo.classList.remove("hidden");
    dom.cameraModal.classList.remove("hidden");
    dom.cameraModal.classList.add("flex");
    await startCamera();
    setCameraMode("capture");
  }

  function closeCamera() {
    document.body.classList.remove("camera-open");
    stopCamera();
    dom.cameraModal.classList.add("hidden");
    dom.cameraModal.classList.remove("flex");
    dom.cameraPreview.src = "";
    dom.cameraPreview.classList.add("hidden");
    dom.cameraVideo.classList.remove("hidden");
    dom.cameraLiveResult.classList.add("hidden");
    dom.cameraDetectError.classList.add("hidden");
    hideCameraDetectionRegion();
    state.camera.capturedBlob = null;
  }

  async function captureFrame() {
    if (!dom.cameraVideo.videoWidth || !dom.cameraVideo.videoHeight) return;
    dom.cameraCanvas.width = dom.cameraVideo.videoWidth;
    dom.cameraCanvas.height = dom.cameraVideo.videoHeight;
    const ctx = dom.cameraCanvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(dom.cameraVideo, 0, 0, dom.cameraCanvas.width, dom.cameraCanvas.height);
    const blob = await new Promise(function (resolve) { dom.cameraCanvas.toBlob(resolve, "image/jpeg", 0.95); });
    if (!blob) return;

    state.camera.capturedBlob = blob;
    dom.cameraPreview.src = URL.createObjectURL(blob);
    dom.cameraPreview.classList.remove("hidden");
    dom.cameraVideo.classList.add("hidden");
    dom.cameraCaptureActions.classList.add("hidden");
    dom.cameraPreviewActions.classList.remove("hidden");
    dom.cameraCaptureHint.classList.add("hidden");
  }

  function retakeCapture() {
    if (dom.cameraPreview.src && dom.cameraPreview.src.startsWith("blob:")) URL.revokeObjectURL(dom.cameraPreview.src);
    state.camera.capturedBlob = null;
    dom.cameraPreview.src = "";
    dom.cameraPreview.classList.add("hidden");
    dom.cameraVideo.classList.remove("hidden");
    dom.cameraPreviewActions.classList.add("hidden");
    dom.cameraCaptureActions.classList.remove("hidden");
    dom.cameraCaptureHint.classList.remove("hidden");
  }

  function useCapture() {
    if (isInteractionBlocked()) return;
    if (!state.camera.capturedBlob) return;
    addImage(makeImage(`camera:${Date.now()}`, URL.createObjectURL(state.camera.capturedBlob), state.camera.capturedBlob, "camera-capture.jpg"));
    closeCamera();
  }

  function bindEvents() {
    dom.tabClassify.addEventListener("click", function () { setTab("classify"); });
    dom.tabHistory.addEventListener("click", function () { setTab("history"); });

    dom.modelSelect.addEventListener("change", function () { state.selectedModel = dom.modelSelect.value; updateModelMeta(); });

    dom.dropzone.addEventListener("click", function () {
      if (isInteractionBlocked()) return;
      if (!state.images.length) dom.uploadInput.click();
    });

    dom.dropzone.addEventListener("dragover", function (event) {
      if (isInteractionBlocked()) return;
      event.preventDefault();
      dom.dropzone.classList.add("border-primary-500", "bg-primary-50", "dark:bg-primary-900/20");
      dom.dropEmptyIcon.setAttribute("data-lucide", "image");
      dom.dropEmptyTitle.textContent = "Drop your image here";
      createIcons(dom.dropzone);
    });

    dom.dropzone.addEventListener("dragleave", function (event) {
      if (isInteractionBlocked()) return;
      event.preventDefault();
      dom.dropzone.classList.remove("border-primary-500", "bg-primary-50", "dark:bg-primary-900/20");
      dom.dropEmptyIcon.setAttribute("data-lucide", "upload");
      dom.dropEmptyTitle.textContent = "Upload vegetable image";
      createIcons(dom.dropzone);
    });

    dom.dropzone.addEventListener("drop", function (event) {
      if (isInteractionBlocked()) return;
      event.preventDefault();
      dom.dropzone.classList.remove("border-primary-500", "bg-primary-50", "dark:bg-primary-900/20");
      void processFiles(event.dataTransfer.files);
    });

    dom.uploadInput.addEventListener("change", function () {
      if (isInteractionBlocked()) return;
      void processFiles(dom.uploadInput.files);
      dom.uploadInput.value = "";
    });

    dom.browseFilesBtn.addEventListener("click", function () {
      if (isInteractionBlocked()) return;
      dom.uploadInput.click();
    });

    dom.resetImages.addEventListener("click", function (event) {
      if (isInteractionBlocked()) return;
      event.stopPropagation();
      resetImages();
    });

    dom.gallery.addEventListener("click", function (event) {
      if (isInteractionBlocked()) return;
      const removeButton = event.target.closest("[data-gallery-remove]");
      if (removeButton) {
        event.stopPropagation();
        removeImage(Number(removeButton.getAttribute("data-gallery-remove")));
        return;
      }
      const card = event.target.closest("[data-gallery-index]");
      if (!card) return;
      state.currentImageIndex = Number(card.getAttribute("data-gallery-index"));
      renderImages();
    });

    dom.sampleButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        if (isInteractionBlocked()) return;
        const sample = button.getAttribute("data-sample") || "";
        const key = `sample:${sample}`;
        const index = findImageBySource(key);
        if (index >= 0) {
          removeImage(index);
          return;
        }
        sampleToImage(sample).then(function (item) {
          addImage(item);
          showError("");
        }).catch(function (error) {
          showError(error && error.message ? error.message : "Unable to load sample image.");
        });
      });
    });

    dom.predictBtn.addEventListener("click", function () { void classifyImages(); });

    dom.historyExport.addEventListener("click", exportHistory);
    dom.historyClear.addEventListener("click", function () { dom.clearModal.classList.remove("hidden"); dom.clearModal.classList.add("flex"); });
    dom.historySearch.addEventListener("input", function () { state.filters.search = dom.historySearch.value.trim(); dom.historySearchClear.classList.toggle("hidden", !state.filters.search); renderHistory(); });
    dom.historySearchClear.addEventListener("click", function () { dom.historySearch.value = ""; state.filters.search = ""; dom.historySearchClear.classList.add("hidden"); renderHistory(); });
    dom.historyFilterToggle.addEventListener("click", function () { setFiltersOpen(!state.filtersOpen); });
    dom.historyCategory.addEventListener("change", function () { state.filters.category = dom.historyCategory.value; renderHistory(); });
    if (dom.historyModel) {
      dom.historyModel.addEventListener("change", function () { state.filters.model = dom.historyModel.value; renderHistory(); });
    }
    dom.historySort.addEventListener("change", function () { state.filters.sort = dom.historySort.value; renderHistory(); });
    dom.historyOrderToggle.addEventListener("click", function () {
      state.filters.order = state.filters.order === "asc" ? "desc" : "asc";
      const asc = state.filters.order === "asc";
      dom.historyOrderText.textContent = asc ? "Ascending" : "Descending";
      dom.historyOrderIcon.setAttribute("data-lucide", asc ? "sort-asc" : "sort-desc");
      createIcons(dom.historyOrderToggle);
      renderHistory();
    });

    dom.historyList.addEventListener("click", function (event) {
      const deleteButton = event.target.closest("[data-history-delete]");
      if (deleteButton) {
        event.stopPropagation();
        state.pendingDeleteId = deleteButton.getAttribute("data-history-delete");
        dom.deleteModal.classList.remove("hidden");
        dom.deleteModal.classList.add("flex");
        return;
      }
      const card = event.target.closest("[data-history-id]");
      if (!card) return;
      const id = card.getAttribute("data-history-id");
      const item = state.history.find(function (entry) { return entry.id === id; });
      if (item) openDetail(item);
    });
    if (dom.historyOverviewTableBody) {
      dom.historyOverviewTableBody.addEventListener("click", function (event) {
        const openButton = event.target.closest("[data-history-open]");
        if (!openButton) return;
        const id = openButton.getAttribute("data-history-open");
        const item = state.history.find(function (entry) { return entry.id === id; });
        if (item) openDetail(item);
      });
    }

    dom.detailClose.addEventListener("click", closeDetail);
    dom.detailModal.addEventListener("click", function (event) { if (event.target === dom.detailModal) closeDetail(); });

    dom.deleteCancel.addEventListener("click", function () { state.pendingDeleteId = null; dom.deleteModal.classList.add("hidden"); dom.deleteModal.classList.remove("flex"); });
    dom.deleteConfirm.addEventListener("click", function () {
      if (!state.pendingDeleteId) return;
      void deleteHistoryItem(state.pendingDeleteId).catch(function (error) { showError(error && error.message ? error.message : "Failed to delete prediction"); });
    });
    dom.deleteModal.addEventListener("click", function (event) { if (event.target === dom.deleteModal) { state.pendingDeleteId = null; dom.deleteModal.classList.add("hidden"); dom.deleteModal.classList.remove("flex"); } });

    dom.clearCancel.addEventListener("click", function () { dom.clearModal.classList.add("hidden"); dom.clearModal.classList.remove("flex"); });
    dom.clearConfirm.addEventListener("click", function () { void clearHistoryAll().catch(function (error) { showError(error && error.message ? error.message : "Failed to clear history"); }); });
    dom.clearModal.addEventListener("click", function (event) { if (event.target === dom.clearModal) { dom.clearModal.classList.add("hidden"); dom.clearModal.classList.remove("flex"); } });

    dom.openCameraBtn.addEventListener("click", function () { void openCamera(); });
    dom.cameraCloseBtn.addEventListener("click", closeCamera);
    dom.cameraModeCapture.addEventListener("click", function () { setCameraMode("capture"); });
    dom.cameraModeLive.addEventListener("click", function () { setCameraMode("live"); });
    if (dom.cameraCloseBtnBottom) dom.cameraCloseBtnBottom.addEventListener("click", closeCamera);
    if (dom.cameraModeCaptureBottom) dom.cameraModeCaptureBottom.addEventListener("click", function () { setCameraMode("capture"); });
    if (dom.cameraModeLiveBottom) dom.cameraModeLiveBottom.addEventListener("click", function () { setCameraMode("live"); });
    dom.cameraFlipBtn.addEventListener("click", function () {
      state.camera.facingMode = state.camera.facingMode === "user" ? "environment" : "user";
      stopCamera();
      void startCamera().then(function () { setCameraMode(state.camera.mode); });
    });
    dom.cameraModal.addEventListener("click", function (event) {
      const target = event.target;
      if (!target || typeof target.closest !== "function") {
        if (event.target === dom.cameraModal) closeCamera();
        return;
      }

      if (target.closest("#camera-close-btn")) {
        closeCamera();
        return;
      }

      if (target.closest("#camera-mode-capture")) {
        setCameraMode("capture");
        return;
      }

      if (target.closest("#camera-mode-live")) {
        setCameraMode("live");
        return;
      }

      if (target.closest("#camera-flip-btn")) {
        state.camera.facingMode = state.camera.facingMode === "user" ? "environment" : "user";
        stopCamera();
        void startCamera().then(function () { setCameraMode(state.camera.mode); });
        return;
      }

      if (event.target === dom.cameraModal) {
        closeCamera();
      }
    });
    document.addEventListener("keydown", function (event) {
      if (dom.cameraModal.classList.contains("hidden")) return;
      if (event.key === "Escape" || event.key === "Esc") {
        event.preventDefault();
        closeCamera();
      }
    });
    dom.cameraCaptureBtn.addEventListener("click", function () { void captureFrame(); });
    dom.cameraRetakeBtn.addEventListener("click", retakeCapture);
    dom.cameraUseBtn.addEventListener("click", useCapture);
  }

  async function processFiles(fileList) {
    if (isInteractionBlocked()) return;
    const files = Array.from(fileList || []).filter(function (f) { return f && f.type && f.type.startsWith("image/"); });
    if (!files.length) {
      showError("Please upload image files only.");
      return;
    }
    for (const file of files) addImage(await fileToImage(file));
    showError("");
  }

  async function init() {
    createIcons();
    bindEvents();
    renderImages();
    renderResults();
    setFiltersOpen(false);
    showError("");
    dom.historySort.value = state.filters.sort;
    dom.historyOrderText.textContent = "Descending";

    await Promise.all([loadModels(), loadCatalog(), loadHistory()]);

    const url = new URL(window.location.href);
    if ((url.searchParams.get("tab") || "").toLowerCase() === "history") setTab("history");
  }

  init().catch(function (error) {
    showError(error && error.message ? error.message : "Unable to initialize classify page.");
  });
})();
