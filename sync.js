// Hesap (e-posta / Google) ve dinleme kaydı senkronu — Firebase Authentication + Cloud Firestore.
// Her kullanıcının kaydı tek bir belgede durur: users/{uid}. Ayar yoksa site hesapsız (yalnız bu cihazda) çalışır.
import config from './firebase-config.js';

const SDK = 'https://www.gstatic.com/firebasejs/10.12.2';
const app = window.skrApp;

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
  'auth/unauthorized-domain': 'Bu site adresi Firebase’de yetkili değil. Firebase Console > Authentication > Settings > Authorized domains bölümüne ekleyin.',
  'auth/operation-not-allowed': 'Bu giriş yöntemi Firebase’de açılmamış. Firebase Console > Authentication > Sign-in method bölümünden açın.'
};

if (!config || !config.apiKey) {
  // Ayar girilmemiş: hesap paneli bunu söyler, ilerleme yerelde kalır
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
      async signInGoogle() {
        const provider = new A.GoogleAuthProvider();
        provider.setCustomParameters({ prompt: 'select_account' });
        try { await A.signInWithPopup(auth, provider); }
        catch (e) {
          if (e.code === 'auth/popup-blocked' || e.code === 'auth/operation-not-supported-in-this-environment') await A.signInWithRedirect(auth, provider);
          else throw e;
        }
      },
      signIn: (email, pass) => A.signInWithEmailAndPassword(auth, email, pass),
      async signUp(email, pass, name) {
        const cred = await A.createUserWithEmailAndPassword(auth, email, pass);
        if (name) { await A.updateProfile(cred.user, { displayName: name }); app.setUser(cred.user); }
      },
      resetPassword: email => A.sendPasswordResetEmail(auth, email),
      async signOut() { await write(); await A.signOut(auth); },
      errorText: e => ERRORS[e?.code]
        || (String(e?.code).startsWith('auth/api-key-not-valid') ? 'Firebase ayarı hatalı: firebase-config.js içindeki apiKey değerini kontrol edin.' : 'Bir sorun oluştu. Lütfen tekrar dene.')
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
