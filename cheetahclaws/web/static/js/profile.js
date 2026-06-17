/* User profile — display name, email, avatar. Stored in config (persisted to
 * ~/.cheetahclaws/config.json in the single-user desktop app). Shows the
 * identity in the sidebar and an editable card in Settings. Depends on
 * updateConfig (settings.js). */

Object.assign(ChatApp.prototype, {

  // Instant sidebar render from the last-known profile (no network), called at
  // startup so the name/avatar show before any config fetch.
  _initProfile() {
    let cached = {};
    try { cached = JSON.parse(localStorage.getItem('cc-profile') || '{}'); } catch (_) {}
    this._renderAvatarEl(document.getElementById('su-avatar'),
                         cached.profile_name, cached.profile_avatar);
    const sn = document.getElementById('su-name');
    if (sn) sn.textContent = (cached.profile_name || '').trim() || 'Profile';
  },

  // Apply a config object to the profile UI (Settings inputs + sidebar) and
  // cache it for the next launch. Hooked from settings.js when config loads.
  _applyProfile(cfg) {
    if (!cfg) return;
    const name = String(cfg.profile_name || '').trim();
    const email = String(cfg.profile_email || '').trim();
    const avatar = cfg.profile_avatar || '';

    const ni = document.getElementById('profile-name');
    const ei = document.getElementById('profile-email');
    if (ni && document.activeElement !== ni) ni.value = name;
    if (ei && document.activeElement !== ei) ei.value = email;
    this._renderAvatarEl(document.getElementById('profile-avatar'), name, avatar);

    this._renderAvatarEl(document.getElementById('su-avatar'), name, avatar);
    const sn = document.getElementById('su-name');
    if (sn) sn.textContent = name || 'Profile';

    try {
      localStorage.setItem('cc-profile', JSON.stringify(
        { profile_name: name, profile_email: email, profile_avatar: avatar }));
    } catch (_) { /* avatar may exceed quota — sidebar still works this session */ }
  },

  // Render an avatar element: uploaded image if present, else a colored initial.
  _renderAvatarEl(el, name, avatar) {
    if (!el) return;
    if (avatar) {
      el.style.backgroundImage = `url("${String(avatar).replace(/"/g, '%22')}")`;
      el.textContent = '';
    } else {
      el.style.backgroundImage = '';
      el.textContent = (String(name || '').trim().charAt(0) || '?').toUpperCase();
    }
  },

  // Avatar upload → data URL → config (+ live re-render).
  async onAvatarFile(file) {
    if (!file) return;
    if (file.size > 512 * 1024) { alert('Please pick an image under 512 KB.'); return; }
    let dataUrl;
    try {
      dataUrl = await new Promise((res, rej) => {
        const r = new FileReader();
        r.onload = () => res(r.result);
        r.onerror = () => rej(r.error);
        r.readAsDataURL(file);
      });
    } catch (_) { alert('Could not read that image.'); return; }
    await this.updateConfig('profile_avatar', dataUrl);
    this._applyProfile({
      profile_name: (document.getElementById('profile-name') || {}).value,
      profile_email: (document.getElementById('profile-email') || {}).value,
      profile_avatar: dataUrl,
    });
  },

  // Re-sync the sidebar after a name edit (the input's onchange already saved).
  _afterProfileSave() {
    let cached = {};
    try { cached = JSON.parse(localStorage.getItem('cc-profile') || '{}'); } catch (_) {}
    this._applyProfile({
      profile_name: (document.getElementById('profile-name') || {}).value,
      profile_email: (document.getElementById('profile-email') || {}).value,
      profile_avatar: cached.profile_avatar || '',
    });
  },
});
