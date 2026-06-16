/* First-run onboarding — shown when no provider API key is configured yet.
 * Lets a non-technical user pick a provider and paste a key (or choose local
 * Ollama, no key) without touching the terminal. Reuses the existing
 * /api/config + setApiKey plumbing. Falls through to the welcome dashboard
 * once a key exists or the user skips. Depends only on _esc, _fetchAuth,
 * setApiKey, selectModel (settings.js) and _showWelcome (welcome.js). */

Object.assign(ChatApp.prototype, {

  // Entry point (called from init.js instead of _showWelcome directly):
  // decide whether the user still needs to set up a provider.
  async _maybeOnboard() {
    // Use /api/models (no session required, unlike /api/config?sid=…) so this
    // works at first paint before any session exists. has_api_key is reported
    // per provider; ollama with local models counts as already set up.
    let needsSetup = false;
    try {
      const r = await this._fetchAuth('/api/models');
      const data = await r.json();
      const providers = data.providers || [];
      const anyKey = providers.some(p => p.has_api_key);
      const ollamaReady = providers.some(
        p => p.provider === 'ollama' && (p.models || []).length);
      needsSetup = !anyKey && !ollamaReady;
    } catch (_) {
      // If we can't tell (network/auth), don't block — just show welcome.
    }
    if (needsSetup) this._showOnboarding();
    else this._showWelcome();
  },

  _showOnboarding() {
    const PROVIDERS = [
      { id: 'anthropic', name: 'Anthropic Claude', hint: 'Recommended — best for coding', key: true },
      { id: 'openai',    name: 'OpenAI GPT',       hint: 'GPT-4o / o-series',             key: true },
      { id: 'gemini',    name: 'Google Gemini',    hint: '',                              key: true },
      { id: 'deepseek',  name: 'DeepSeek',         hint: 'Low cost',                      key: true },
      { id: 'ollama',    name: 'Local (Ollama)',   hint: 'No API key — runs on your machine', key: false },
    ];

    const el = document.getElementById('messages');
    el.innerHTML = '';
    const card = document.createElement('div');
    card.style.cssText = 'max-width:560px;margin:0 auto;padding:32px 20px;';
    card.innerHTML = `
      <div style="text-align:center;margin-bottom:24px;">
        <div style="font-size:26px;font-weight:700;color:var(--accent);">Welcome to CheetahClaws</div>
        <div style="font-size:13px;color:var(--text-muted);margin-top:6px;">
          Pick a model provider to get started. You can change this anytime in Settings.</div>
      </div>
      <div id="ob-providers" style="display:flex;flex-direction:column;gap:10px;"></div>
      <div id="ob-key" style="display:none;margin-top:18px;">
        <label id="ob-key-label" style="display:block;font-size:13px;color:var(--text-muted);margin-bottom:6px;"></label>
        <input id="ob-key-input" type="password" autocomplete="off" spellcheck="false"
          placeholder="Paste your API key"
          style="width:100%;box-sizing:border-box;padding:10px 12px;border-radius:8px;
                 border:1px solid var(--border);background:var(--bg-input,#161b22);
                 color:var(--text);font-size:14px;">
        <button id="ob-save" style="margin-top:12px;width:100%;padding:10px;border:none;
          border-radius:8px;background:var(--accent);color:#fff;font-weight:600;cursor:pointer;">
          Save &amp; Start</button>
        <div id="ob-error" style="color:var(--red,#f85149);font-size:12px;margin-top:8px;min-height:1em;"></div>
      </div>
      <div style="text-align:center;margin-top:18px;">
        <a id="ob-skip" href="#" style="font-size:12px;color:var(--text-muted);">Skip for now</a>
      </div>`;
    el.appendChild(card);

    // Provider buttons (no inline handlers — wire by element to avoid injection).
    const list = card.querySelector('#ob-providers');
    for (const p of PROVIDERS) {
      const b = document.createElement('div');
      b.style.cssText = 'display:flex;align-items:center;justify-content:space-between;gap:12px;' +
        'padding:14px 16px;border:1px solid var(--border);border-radius:10px;cursor:pointer;' +
        'background:var(--bg-card,transparent);transition:border-color .15s;';
      b.onmouseenter = () => { b.style.borderColor = 'var(--accent)'; };
      b.onmouseleave = () => { b.style.borderColor = 'var(--border)'; };
      b.innerHTML =
        `<div><div style="font-weight:600;">${this._esc(p.name)}</div>` +
        (p.hint ? `<div style="font-size:12px;color:var(--text-muted);">${this._esc(p.hint)}</div>` : '') +
        `</div><div style="color:var(--text-muted);">${p.key ? '🔑' : '💻'}</div>`;
      b.onclick = () => this._onboardPick(p, card);
      list.appendChild(b);
    }

    card.querySelector('#ob-skip').onclick = (e) => { e.preventDefault(); this._showWelcome(); };
    this._obProvider = null;
  },

  _onboardPick(p, card) {
    if (!p.key) {            // local Ollama — no key needed
      this._onboardFinish('ollama', null);
      return;
    }
    this._obProvider = p.id;
    const keyBox = card.querySelector('#ob-key');
    card.querySelector('#ob-key-label').textContent = `Enter your ${p.name} API key`;
    keyBox.style.display = 'block';
    const input = card.querySelector('#ob-key-input');
    input.value = '';
    input.focus();
    const save = card.querySelector('#ob-save');
    const err = card.querySelector('#ob-error');
    const submit = async () => {
      const v = input.value.trim();
      if (!v) { err.textContent = 'Please paste a key, or pick Local (Ollama).'; return; }
      save.disabled = true; save.textContent = 'Saving…'; err.textContent = '';
      try {
        await this._onboardFinish(this._obProvider, v);
      } catch (e) {
        save.disabled = false; save.textContent = 'Save & Start';
        err.textContent = 'Could not save — ' + (e && e.message ? e.message : 'try again');
      }
    };
    save.onclick = submit;
    input.onkeydown = (e) => { if (e.key === 'Enter') { e.preventDefault(); submit(); } };
  },

  async _onboardFinish(provider, key) {
    // setApiKey persists via updateConfig, which needs a session — on a fresh
    // launch none exists yet, so create one first (newSession also lands us on
    // the welcome dashboard, the desired end state).
    if (!this.sessionId && this.newSession) await this.newSession();
    if (key) await this.setApiKey(provider, key);
    // Best-effort: select a default model for the chosen provider so the very
    // first message uses it (mirrors how Settings sets a model).
    try {
      const r = await this._fetchAuth('/api/models');
      const data = await r.json();
      const entry = (data.providers || []).find(x => x.provider === provider);
      const first = entry && entry.models && entry.models[0];
      if (first) await this.selectModel(`${provider}/${first}`);
    } catch (_) { /* keep the existing default model */ }
    this._showWelcome();
  },
});
