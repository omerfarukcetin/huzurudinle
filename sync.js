// Hesap (e-posta / Google) ve dinleme kaydı senkronu — Firebase Authentication + Cloud Firestore.
// Her kullanıcının kaydı tek bir belgede durur: users/{uid}. Ayar yoksa site hesapsız (yalnız bu cihazda) çalışır.
const SDK = 'https://www.gstatic.com/firebasejs/10.12.2';
const app = window.skrApp;

// Ayar dosyasını ayrı yükle: hatalı yapıştırılmışsa sessizce bozulmasın, hesap panelinde nedeni yazsın
let config = null;
try {
  config = (await import('./firebase-config.js?v=' + Date.now())).default;
  if (config && typeof config === 'object' && !config.apiKey) window.SKR_AUTH_ERROR = 'firebase-config.js içinde apiKey yok. Firebase Console > Proje ayarları > Web uygulaması bölümündeki firebaseConfig değerlerini eksiksiz yapıştırın.';
} catch (e) {
  console.error('firebase-config.js okunamadı:', e);
  window.SKR_AUTH_ERROR = 'firebase-config.js okunamadı (' + (e.message || e) + '). Dosyada yalnızca "export default { apiKey: ..., authDomain: ..., ... };" olmalı; Firebase\'in verdiği "import ..." ve "const app = initializeApp(...)" satırlarını silin.';
}
if (location.protocol === 'file:') window.SKR_AUTH_ERROR = 'Giriş, sayfa dosyadan (çift tıklayarak) açıldığında çalışmaz. Siteyi https adresinden açın.';

const ERRORS = {
  'auth/invalid-email': 'E-posta adresi geçerli görünmüyor.',
  'auth/missing-password': 'Şifreni yaz.',
  'auth/weak-password': 'Şifre en az 6 karakter olmalı.',
  'auth/email-already-in-use': 'Bu e-posta ile zaten bir hesap var. Giriş yapmayı dene.',
  'auth/invalid-credential': 'E-posta ya da şifre yanlış.',
  'auth/wrong-password': 'E-posta ya da şifre yanlış.',
  'auth/user-not-found': 'Bu e-posta ile kayıtlı hesap yok.',
  'auth/too-many-requests': 'Çok fazla deneme yapıldı. Biraz bekleyip tekrar dene.',
  'auth/network-request-failed': 'İnternet bağlantısı yok gibi görünüyor.',
  'auth/popup-closed-by-user': 'Google penceresi kapatıldı, giriş yapılmadı.',
  'auth/cancelled-popup-request': 'Google penceresi kapatıldı, giriş yapılmadı.',
  'auth/popup-blocked': 'Tarayıcı Google giriş penceresini engelledi. Adres çubuğundaki "açılır pencere engellendi" simgesinden bu siteye izin verip tekrar dene.',
  'auth/unauthorized-domain': `Bu site adresi (${location.hostname}) Firebase’de yetkili değil. Firebase Console > Authentication > Settings > Authorized domains bölümüne "${location.hostname}" ekleyin.`,
  'auth/operation-not-allowed': 'Bu giriş yöntemi Firebase’de açılmamış. Firebase Console > Authentication > Sign-in method bölümünden Google’ı (ve Email/Password’ü) etkinleştirin.',
  'auth/configuration-not-found': 'Firebase’de Authentication henüz başlatılmamış. Firebase Console > Authentication > "Get started" deyip Google’ı etkinleştirin.',
  'auth/invalid-api-key': 'firebase-config.js içindeki apiKey hatalı. Firebase Console’dan tekrar kopyalayın.',
  'auth/internal-error': 'Google girişinde Firebase iç hatası oluştu. Genellikle Google yöntemi açılmamış ya da destek e-postası seçilmemiştir (Authentication > Sign-in method > Google).',
  'auth/requires-recent-login': 'Güvenlik için yakın zamanda giriş yapmış olman gerekiyor. Çıkış yapıp tekrar giriş yap, sonra hesabını silmeyi yeniden dene.',
  'permission-denied': 'Firestore kuralları bu işleme izin vermedi. firestore.rules içeriğini Firebase Console > Firestore > Rules bölümüne yapıştırıp yayınlayın.',
  'auth/web-storage-unsupported': 'Tarayıcı çerezleri/site verisini engelliyor (gizli sekme?). Normal sekmede deneyin.'
};

if (!config || !config.apiKey || location.protocol === 'file:') {
  // Ayar girilmemiş ya da hatalı: hesap paneli nedenini söyler, ilerleme yerelde kalır
} else {
  try {
    const [{ initializeApp }, A, F] = await Promise.all([
      import(`${SDK}/firebase-app.js`),
      import(`${SDK}/firebase-auth.js`),
      import(`${SDK}/firebase-firestore.js`)
    ]);
    const fb = initializeApp(config);
    const auth = A.getAuth(fb);
    auth.languageCode = 'tr';
    const db = F.getFirestore(fb);

    let uid = null, timer = null, dirty = false;
    const ref = () => F.doc(db, 'users', uid);
    const time = () => new Date().toLocaleTimeString('tr', { hour: '2-digit', minute: '2-digit' });

    async function write() {
      if (!uid) return;
      clearTimeout(timer); timer = null; dirty = false;
      try {
        // JSON gidiş-dönüşü undefined alanları temizler (Firestore kabul etmez)
        await F.setDoc(ref(), JSON.parse(JSON.stringify(app.getState())));
        app.setSyncStatus(`Kaldığın yer hesabına kaydediliyor · son kayıt ${time()}`);
      } catch (e) {
        dirty = true;
        app.setSyncStatus('Şu an kaydedilemedi; bağlantı gelince tekrar denenecek.');
      }
    }
    async function pull() {
      if (!uid) return;
      try {
        const snap = await F.getDoc(ref());
        if (snap.exists()) app.merge(snap.data());
      } catch { /* çevrimdışı: yerel kayıtla devam */ }
    }

    window.skrSync = {
      // Çalarken her birkaç saniyede bir çağrılır; buluta en fazla 15 saniyede bir yazılır
      push() { if (!uid) return; dirty = true; if (!timer) timer = setTimeout(write, 15000); },
      flush() { if (uid && dirty) write(); },
      // Yalnızca açılır pencere: yönlendirmeli giriş, site firebaseapp.com dışında (ör. github.io) barınınca
      // tarayıcıların üçüncü taraf çerez engeli yüzünden sessizce başarısız oluyor
      async signInGoogle() {
        const provider = new A.GoogleAuthProvider();
        provider.setCustomParameters({ prompt: 'select_account' });
        await A.signInWithPopup(auth, provider);
      },
      signIn: (email, pass) => A.signInWithEmailAndPassword(auth, email, pass),
      async signUp(email, pass, name) {
        const cred = await A.createUserWithEmailAndPassword(auth, email, pass);
        if (name) { await A.updateProfile(cred.user, { displayName: name }); app.setUser(cred.user); }
      },
      resetPassword: email => A.sendPasswordResetEmail(auth, email),
      // Hesabı ve hesaptaki kaydı kalıcı olarak sil
      async deleteAccount() {
        const u = auth.currentUser; if (!u) return;
        const id = u.uid;
        const run = async () => {
          uid = null; clearTimeout(timer); timer = null; dirty = false; // silerken yeniden yazılmasın
          await F.deleteDoc(F.doc(db, 'users', id));
          await A.deleteUser(u);
        };
        try { await run(); }
        catch (e) {
          uid = id;
          if (e.code !== 'auth/requires-recent-login') throw e;
          // Güvenlik gereği yakın zamanda giriş istenir: Google hesabında pencereyle tekrar doğrula
          if (!u.providerData.some(p => p.providerId === 'google.com')) throw e;
          await A.reauthenticateWithPopup(u, new A.GoogleAuthProvider());
          await run();
        }
      },
      async signOut() { await write(); await A.signOut(auth); },
      // Bilinmeyen hatalarda kodu da göster: sorunu bulmayı kolaylaştırır
      errorText: e => ERRORS[e?.code]
        || (String(e?.code).startsWith('auth/api-key-not-valid') ? 'Firebase ayarı hatalı: firebase-config.js içindeki apiKey değerini kontrol edin.'
        : `Giriş yapılamadı${e?.code ? ` (hata kodu: ${e.code})` : ''}. Lütfen tekrar dene.`)
    };

    A.getRedirectResult(auth).catch(() => {});
    A.onAuthStateChanged(auth, async u => {
      uid = u?.uid || null;
      app.setUser(u ? { displayName: u.displayName, email: u.email, photoURL: u.photoURL } : null);
      if (u) {
        app.setSyncStatus('Hesabındaki kayıtlar getiriliyor…');
        await pull();   // önce hesaptakini al, bölüm bölüm birleştir
        await write();  // birleşmiş hâli geri yaz
      }
      app.authReady();
    });

    // Başka cihazda dinledikten sonra bu sekmeye dönülünce güncel kaydı al
    document.addEventListener('visibilitychange', () => { if (!document.hidden) pull(); });
    window.addEventListener('pagehide', () => window.skrSync.flush());
  } catch (e) {
    console.error(e);
    window.SKR_AUTH_ERROR = 'Giriş servisine bağlanılamadı. İnternet bağlantını kontrol edip sayfayı yenile.';
  }
}
