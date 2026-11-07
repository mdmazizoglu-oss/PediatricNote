const PEDINOT_STORAGE = 'pedinot-local-v1';
const profileStoreKey = `${PEDINOT_STORAGE}:profiles`;
const activeProfileKey = `${PEDINOT_STORAGE}:active-profile`;
const accountDialog = document.getElementById('account-dialog');
const libraryDialog = document.getElementById('library-dialog');
const accountForm = document.getElementById('account-form');
const accountLabel = document.getElementById('account-label');
const recentCount = document.getElementById('recent-count');
const generatedNoteElement = document.getElementById('generated-note');
const wordCountElement = document.getElementById('word-count');
const languageSelector = document.getElementById('language-selector');
let activeProfileId = localStorage.getItem(activeProfileKey) || '';

const interfaceCopy = {
  tr: { title: 'PediNot | Pediatrik Cerrahi Notları', eyebrow: 'ÇOCUK CERRAHİSİ AMELİYAT NOTU ÜRETİCİ', heading: 'Ameliyat <em>notu.</em>', newNote: 'Yeni ameliyat notu', recent: 'Son notlar', library: 'Not kütüphanem', anonymous: 'Kayıtsız kullanım', account: 'Yerel profil', create: 'Ameliyat notunu oluştur', clear: 'Temizle' },
  en: { title: 'PediNot | Paediatric Surgery Notes', eyebrow: 'PAEDIATRIC SURGERY OPERATIVE NOTE GENERATOR', heading: 'Operative <em>note.</em>', newNote: 'New operative note', recent: 'Recent notes', library: 'My note library', anonymous: 'Guest mode', account: 'Local profile', create: 'Generate operative note', clear: 'Clear' },
  it: { title: 'PediNot | Note di chirurgia pediatrica', eyebrow: 'GENERATORE DI NOTE OPERATORIE DI CHIRURGIA PEDIATRICA', heading: 'Nota <em>operatoria.</em>', newNote: 'Nuova nota operatoria', recent: 'Note recenti', library: 'Le mie note', anonymous: 'Modalità ospite', account: 'Profilo locale', create: 'Genera nota operatoria', clear: 'Pulisci' },
  es: { title: 'PediNot | Notas de cirugía pediátrica', eyebrow: 'GENERADOR DE NOTAS OPERATORIAS DE CIRUGÍA PEDIÁTRICA', heading: 'Nota <em>operatoria.</em>', newNote: 'Nueva nota operatoria', recent: 'Notas recientes', library: 'Mi biblioteca', anonymous: 'Modo invitado', account: 'Perfil local', create: 'Generar nota operatoria', clear: 'Limpiar' },
  fr: { title: 'PediNot | Notes de chirurgie pédiatrique', eyebrow: 'GÉNÉRATEUR DE NOTES OPÉRATOIRES DE CHIRURGIE PÉDIATRIQUE', heading: 'Note <em>opératoire.</em>', newNote: 'Nouvelle note opératoire', recent: 'Notes récentes', library: 'Ma bibliothèque', anonymous: 'Mode invité', account: 'Profil local', create: 'Générer la note', clear: 'Effacer' },
  ar: { title: 'PediNot | ملاحظات جراحة الأطفال', eyebrow: 'مُنشئ ملاحظات عمليات جراحة الأطفال', heading: 'ملاحظة <em>العملية.</em>', newNote: 'ملاحظة عملية جديدة', recent: 'الملاحظات الأخيرة', library: 'مكتبتي', anonymous: 'وضع الضيف', account: 'الملف المحلي', create: 'إنشاء ملاحظة العملية', clear: 'مسح' }
};

function applyLanguage(language) {
  const copy = interfaceCopy[language] || interfaceCopy.tr;
  document.documentElement.lang = language;
  document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
  document.title = copy.title;
  document.querySelector('header .eyebrow').textContent = copy.eyebrow;
  document.querySelector('header h1').innerHTML = copy.heading;
  document.querySelector('.nav-item[href="#vaka"]').lastChild.textContent = ` ${copy.newNote}`;
  document.getElementById('open-recents').childNodes[1].textContent = ` ${copy.recent} `;
  document.getElementById('open-library').lastChild.textContent = ` ${copy.library}`;
  document.getElementById('generate-button').childNodes[0].textContent = `${copy.create} `;
  document.getElementById('clear-form').lastChild.textContent = copy.clear;
  if (!currentProfile()) accountLabel.textContent = copy.anonymous;
  languageSelector.value = language;
  localStorage.setItem(`${PEDINOT_STORAGE}:language`, language);
  void window.setClinicalLanguage?.(language);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]);
}

function libraryToast(message) {
  const toastElement = document.getElementById('toast');
  toastElement.textContent = message;
  toastElement.classList.add('show');
  clearTimeout(toastElement.timer);
  toastElement.timer = setTimeout(() => toastElement.classList.remove('show'), 2800);
}

function profiles() {
  return JSON.parse(localStorage.getItem(profileStoreKey) || '[]');
}

function saveProfiles(items) {
  localStorage.setItem(profileStoreKey, JSON.stringify(items));
}

function currentProfile() {
  return profiles().find((profile) => profile.id === activeProfileId) || null;
}

function dataKey(profileId) {
  return `${PEDINOT_STORAGE}:profile:${profileId}`;
}

function profileData() {
  if (!activeProfileId) return { notes: [], templates: [], sources: [] };
  return JSON.parse(localStorage.getItem(dataKey(activeProfileId)) || '{"notes":[],"templates":[],"sources":[]}');
}

function saveProfileData(data) {
  localStorage.setItem(dataKey(activeProfileId), JSON.stringify(data));
}

function uniqueId() {
  return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function passwordHash(value) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

function updateProfileUi() {
  const profile = currentProfile();
  accountLabel.textContent = profile ? profile.name : 'Kayıtsız kullanım';
  const noteCount = profileData().notes.length;
  recentCount.textContent = String(noteCount);
}

function requireProfile() {
  if (currentProfile()) return true;
  accountDialog.showModal();
  libraryToast('Kişisel kütüphaneyi kullanmak için yerel profil oluşturun');
  return false;
}

function resourceItem(item, type) {
  const icon = type === 'notes' ? 'file-text' : type === 'templates' ? 'layout-template' : 'book-open-text';
  const detail = type === 'notes' ? `${item.procedure} · ${new Date(item.createdAt).toLocaleDateString('tr-TR')}` : item.content.slice(0, 130) || 'Metin eklenmedi';
  const action = type === 'notes' ? 'open-note' : type === 'templates' ? 'use-template' : 'use-source';
  return `<article class="library-item"><i data-lucide="${icon}"></i><div class="library-item-content"><h3 class="library-item-title">${escapeHtml(item.title)}</h3><p class="library-item-meta">${escapeHtml(detail)}</p></div><div class="library-item-actions"><button type="button" title="Kullan" data-action="${action}" data-id="${item.id}"><i data-lucide="arrow-up-right"></i></button><button type="button" title="Sil" data-action="delete-${type.slice(0, -1)}" data-id="${item.id}"><i data-lucide="trash-2"></i></button></div></article>`;
}

function renderLibrary() {
  const data = profileData();
  const groups = [['saved-notes-list', data.notes, 'notes'], ['templates-list', data.templates, 'templates'], ['sources-list', data.sources, 'sources']];
  groups.forEach(([elementId, entries, type]) => {
    const element = document.getElementById(elementId);
    element.innerHTML = entries.length ? entries.map((item) => resourceItem(item, type)).join('') : `<p class="empty-library">${currentProfile() ? 'Henüz kayıt yok.' : 'Bu alanı kullanmak için yerel profil oluşturun.'}</p>`;
  });
  if (window.lucide) window.lucide.createIcons();
}

function openLibrary(tab = 'notes') {
  libraryDialog.showModal();
  document.querySelectorAll('.tab-button').forEach((button) => button.classList.toggle('active', button.dataset.libraryTab === tab));
  document.querySelectorAll('.library-pane').forEach((pane) => pane.classList.toggle('hidden', pane.id !== `library-${tab}`));
  renderLibrary();
}

function saveGeneratedNote() {
  if (!requireProfile() || generatedNoteElement.classList.contains('empty-note')) return;
  const data = profileData();
  const patientChip = document.getElementById('patient-chip').textContent.trim();
  data.notes.unshift({ id: uniqueId(), title: patientChip || 'Ameliyat notu', procedure: patientChip || 'Taslak', content: generatedNoteElement.textContent, createdAt: new Date().toISOString() });
  saveProfileData(data);
  updateProfileUi();
  libraryToast('Not kişisel kütüphanenize kaydedildi');
}

function appendPersonalContext(label, content) {
  const extra = document.getElementById('extra');
  const prefix = extra.value.trim() ? '\n\n' : '';
  extra.value += `${prefix}${label}: ${content}`;
  window.scrollTo({ top: document.getElementById('fields-section').offsetTop - 20, behavior: 'smooth' });
  libraryToast('Seçilen kişisel içerik taslağa eklendi; klinik gerçeklerle doğrulayın');
}

function deleteEntry(kind, id) {
  if (!requireProfile()) return;
  const data = profileData();
  data[`${kind}s`] = data[`${kind}s`].filter((item) => item.id !== id);
  saveProfileData(data);
  updateProfileUi();
  renderLibrary();
}

function loadTextFile(input, target) {
  const [file] = input.files;
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    target.value = String(reader.result).slice(0, 12000);
    libraryToast(`${file.name} metni alındı`);
  };
  reader.readAsText(file);
}

const saveNoteButton = document.createElement('button');
saveNoteButton.type = 'button';
saveNoteButton.className = 'secondary-button';
saveNoteButton.innerHTML = '<i data-lucide="bookmark-plus"></i>Notu kaydet';
saveNoteButton.addEventListener('click', saveGeneratedNote);
document.getElementById('guide-actions').append(saveNoteButton);

document.getElementById('open-account').addEventListener('click', () => {
  const profile = currentProfile();
  document.getElementById('account-name').value = profile?.name || '';
  document.getElementById('account-email').value = profile?.email || '';
  document.getElementById('account-password').value = '';
  accountDialog.showModal();
});
document.getElementById('open-library').addEventListener('click', () => openLibrary('notes'));
document.getElementById('open-recents').addEventListener('click', () => openLibrary('notes'));
document.getElementById('close-library').addEventListener('click', () => libraryDialog.close());

accountForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const name = document.getElementById('account-name').value.trim();
  const email = document.getElementById('account-email').value.trim().toLocaleLowerCase('tr-TR');
  const password = document.getElementById('account-password').value;
  if (!name || !email || password.length < 4) return;
  const hashedPassword = await passwordHash(password);
  const items = profiles();
  let profile = items.find((item) => item.email === email);
  if (profile) {
    if (profile.passwordHash && profile.passwordHash !== hashedPassword) {
      libraryToast('Bu e-posta için yerel parola doğrulanamadı');
      return;
    }
    profile.name = name;
    profile.passwordHash = hashedPassword;
  } else {
    profile = { id: uniqueId(), name, email, passwordHash: hashedPassword, createdAt: new Date().toISOString() };
    items.push(profile);
  }
  saveProfiles(items);
  activeProfileId = profile.id;
  localStorage.setItem(activeProfileKey, activeProfileId);
  accountDialog.close();
  updateProfileUi();
  libraryToast('Yerel profil hazır; kişisel kütüphaneniz etkin');
});

document.querySelectorAll('.tab-button').forEach((button) => button.addEventListener('click', () => openLibrary(button.dataset.libraryTab)));
document.getElementById('template-file').addEventListener('change', (event) => loadTextFile(event.target, document.getElementById('template-content')));
document.getElementById('source-file').addEventListener('change', (event) => loadTextFile(event.target, document.getElementById('source-content')));

document.getElementById('template-form').addEventListener('submit', (event) => {
  event.preventDefault();
  if (!requireProfile()) return;
  const title = document.getElementById('template-name').value.trim();
  const content = document.getElementById('template-content').value.trim();
  if (!title || !content) return;
  const data = profileData();
  data.templates.unshift({ id: uniqueId(), title, content, createdAt: new Date().toISOString() });
  saveProfileData(data);
  event.target.reset();
  renderLibrary();
  libraryToast('Şablon kişisel kütüphanenize eklendi');
});

document.getElementById('source-form').addEventListener('submit', (event) => {
  event.preventDefault();
  if (!requireProfile()) return;
  const title = document.getElementById('source-title').value.trim();
  const content = document.getElementById('source-content').value.trim();
  if (!title || !content) return;
  const data = profileData();
  data.sources.unshift({ id: uniqueId(), title, content, createdAt: new Date().toISOString() });
  saveProfileData(data);
  event.target.reset();
  renderLibrary();
  libraryToast('Kaynak kişisel kütüphanenize eklendi');
});

libraryDialog.addEventListener('click', (event) => {
  const button = event.target.closest('button[data-action]');
  if (!button || !currentProfile()) return;
  const { action, id } = button.dataset;
  const data = profileData();
  if (action === 'open-note') {
    const note = data.notes.find((item) => item.id === id);
    if (!note) return;
    generatedNoteElement.classList.remove('empty-note');
    generatedNoteElement.textContent = note.content;
    wordCountElement.textContent = `${note.content.trim().split(/\s+/).length} kelime`;
    document.getElementById('guide-actions').classList.remove('hidden');
    libraryDialog.close();
    libraryToast('Kayıtlı not açıldı');
  }
  if (action === 'use-template') {
    const template = data.templates.find((item) => item.id === id);
    if (template) appendPersonalContext(`Kişisel şablon - ${template.title}`, template.content);
    libraryDialog.close();
  }
  if (action === 'use-source') {
    const source = data.sources.find((item) => item.id === id);
    if (source) appendPersonalContext(`Kullanıcının kaynak notu - ${source.title}`, source.content);
    libraryDialog.close();
  }
  if (action === 'delete-note') deleteEntry('note', id);
  if (action === 'delete-template') deleteEntry('template', id);
  if (action === 'delete-source') deleteEntry('source', id);
});

updateProfileUi();
applyLanguage(localStorage.getItem(`${PEDINOT_STORAGE}:language`) || 'tr');
languageSelector.addEventListener('change', () => applyLanguage(languageSelector.value));
if (window.lucide) window.lucide.createIcons();