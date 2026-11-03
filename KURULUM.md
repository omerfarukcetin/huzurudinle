# Sesli Kitap Rafı — Giriş (e-posta + Google) kurulumu

Giriş yapılmadan da site çalışır; kaldığınız yer o tarayıcıda saklanır.
Giriş açılınca kaldığınız yer, yer imleri ve hız ayarı hesaba kaydedilir ve tüm cihazlarda senkron olur.
Bunun için ücretsiz bir Firebase projesi gerekir (~10 dakika).

## 1. Firebase projesi
1. https://console.firebase.google.com adresine Google hesabınızla girin → **Proje ekle** (ör. `sesli-kitap-rafi`). Google Analytics gerekmez.
2. Proje ana sayfasında **</>** (Web) simgesine tıklayın, bir ad verin → **Uygulamayı kaydet**.
3. Gösterilen `firebaseConfig = { ... }` nesnesini kopyalayıp **firebase-config.js** dosyasındaki `export default null;` satırının yerine yapıştırın:
   ```js
   export default {
     apiKey: "...",
     authDomain: "...",
     projectId: "...",
     storageBucket: "...",
     messagingSenderId: "...",
     appId: "..."
   };
   ```
   (Bu değerler gizli değildir; güvenliği aşağıdaki kurallar sağlar.)

## 2. Giriş yöntemleri
**Build → Authentication → Get started → Sign-in method**
- **Email/Password** → Etkinleştir → Kaydet
- **Google** → Etkinleştir → proje destek e-postasını seçin → Kaydet

**Authentication → Settings → Authorized domains**: siteyi yayınlayacağınız alan adını ekleyin
(ör. `kullaniciadi.github.io` veya kendi alan adınız). `localhost` zaten ekli gelir.

İsteğe bağlı: **Authentication → Templates** bölümünden şifre sıfırlama e-postasının dilini Türkçe yapabilirsiniz.

## 3. Veritabanı
**Build → Firestore Database → Create database** → konum: `eur3 (europe-west)` → **production mode**.
Ardından **Rules** sekmesine **firestore.rules** dosyasının içeriğini yapıştırıp **Publish** deyin.
Bu kural, herkesin yalnızca kendi kaydını okuyup yazabilmesini sağlar.

## 4. Yayınlama
Bütün klasörü (index.html, sync.js, firebase-config.js, books.js, covers/) bir statik barındırmaya yükleyin:
GitHub Pages, Netlify, Firebase Hosting veya kendi hostinginiz.

Not: Giriş, sayfa `http(s)://` ile açıldığında çalışır; `index.html` dosyasına çift tıklayarak açınca
site çalışır ama giriş kapalı kalır. Bilgisayarda denemek için klasörde şunu çalıştırıp
http://localhost:8765 adresini açabilirsiniz:

    python -m http.server 8765

## Uygulama olarak yükleme (PWA)
- Site **https** üzerinden yayınlandığında telefonda "Uygulama olarak yükle" kartı çıkar
  (Android/Chrome'da tek dokunuş; iPhone'da Safari > Paylaş > Ana Ekrana Ekle — site adımları gösterir).
- Simgeler `icons/` klasöründe, logo `logo.svg`. Logoyu değiştirmek için `logo_olustur.py` içindeki
  renkleri/ölçüleri düzenleyip `python logo_olustur.py` çalıştırın.
- Sayfa, betikler ve kitap listesi her açılışta önce internetten alınır (internet yoksa önbellekten);
  kapaklar ve simgeler önbellekten gelir. Kapak resimlerini değiştirdiyseniz `sw.js` dosyasının başındaki
  `VERSION = 'skr-v3'` değerini artırın (`skr-v4`…), böylece eski kapaklar silinir.

## Günlük hatırlatma — neyin nerede çalıştığı
| Cihaz | Durum |
|---|---|
| Android, Chrome, uygulama **yüklü** | Uygulama kapalıyken de hatırlatır (Chrome günde birkaç kez kontrol eder; tam dakikası garanti değildir). |
| Android/bilgisayar, yüklü değil | Yalnızca site açıkken hatırlatır. |
| iPhone (iOS 16.4+, ana ekrana eklenmiş) | Yalnızca uygulama açıkken hatırlatır; iOS arka plan kontrolüne izin vermiyor. |

Kapalı uygulamaya tam saatinde bildirim göndermek için sunucu tarafı gerekir
(Firebase Cloud Messaging + zamanlanmış Cloud Function; Firebase'in ücretli "Blaze" planı, bu kullanımda aylık birkaç kuruş).

## Nasıl çalışır?
- Her kullanıcının kaydı Firestore'da tek bir belgedir: `users/{kullanıcı-id}`.
- Dinlerken konum cihazda birkaç saniyede bir, hesapta en geç 15 saniyede bir kaydedilir; duraklatınca,
  sekmeyi kapatınca ya da uygulamadan çıkınca hemen kaydedilir.
- İki cihazda farklı bölümler dinlendiyse bölüm bölüm en yeni konum kazanır.
- Sekmeye geri dönüldüğünde (ör. telefondan sonra bilgisayara) hesaptaki son durum yeniden alınır.
- Ücretsiz Firebase kotası (günde 50.000 okuma / 20.000 yazma) birkaç yüz aktif dinleyici için yeterlidir.
