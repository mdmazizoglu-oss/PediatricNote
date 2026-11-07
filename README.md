# Atlas Literature Radar

Beş akademik kaynağı tek arama deneyiminde birleştirmek için hazırlanmış başlangıç uygulaması.

## Çalıştırma

Node.js gerektirmez. Python 3 ile:

```bash
cd /Users/mdmazizoglu/literature-radar
python3 server.py
```

Sonra tarayıcıda http://localhost:8080 adresini açın.

## Veri kaynakları

- PubMed: `server.py` içinde gerçek NCBI E-utilities araması hazırdır.
- Scopus: disabled by configuration.
- Web of Science: disabled by configuration.
- Embase: disabled by configuration.
- Google Scholar: scraping yerine lisanslı SerpAPI sağlayıcısı (`SERPAPI_KEY`) kullanılmalıdır. SerpAPI panelinden bir hesap ve API key aldıktan sonra `.env` içine yazın. `/api/search?q=...` çağrısı Scholar sonuçlarını PubMed sonuçlarıyla birlikte döndürür.
- DOAJ: açık DOAJ API üzerinden API anahtarı olmadan aranır.

Bu anahtarlar olmadan arayüz kaynakları gizlemez; hangi bağlantının hazır olmadığını gösterir. Bu, sahte makale üretmek yerine erişim durumunu doğru raporlamak içindir.

### Google Scholar kurulumu

1. SerpAPI hesabı oluşturun ve dashboard'dan API key alın.
2. `.env` dosyasına `SERPAPI_KEY=...` ekleyin.
3. Sunucuyu yeniden başlatın: `python3 server.py`.
4. Test edin: `curl 'http://localhost:8080/api/search?q=pediatric%20surgery&limit=5'`.

Google Scholar'ın kendi resmi genel arama API'si olmadığı için uygulama Scholar sayfalarını scraping yapmaz; SerpAPI'nin lisanslı `google_scholar` motorunu kullanır.

### Pediatrik cerrahi kapsamı

Uygulama tüm kaynaklarda otomatik olarak geniş bir pediatrik cerrahi konu sözlüğü kullanır. Sözlük; yenidoğan ve fetal cerrahi, konjenital anomaliler, özofagus-mide-bağırsak, kolorektal, hepatobiliyer, pankreas, toraks ve hava yolu, çocuk ürolojisi, genital ve pelvik cerrahi, onkoloji, vasküler anomaliler, travma, yanık, karın duvarı, endokrin cerrahi, laparoskopi, robotik cerrahi ve perioperatif bakım başlıklarını; bunların hastalık, deformite, tümör ve işlem adlarını kapsar.

Her sorguya ayrıca çocuk/infant/neonate/adolescent yaş sinyalleri eklenir. `adult-only`, `adult population`, `adults only` ve `geriatric` sinyali bulunan kayıtlar son kontrolde elenir. Özet veya başlıkta <18 yaş sinyali bulunmayan kayıtlar da bilinçli olarak gösterilmez; bu yaklaşım erişkin makalelerin yanlışlıkla listeye girmesini önler.

### Scopus kurulumu

1. Elsevier Developer Portal'dan bir uygulama oluşturup `SCOPUS_API_KEY` alın.
2. Kurumunuzun Scopus erişimi proxy token istiyorsa `SCOPUS_INST_TOKEN` değerini de ekleyin.
3. `.env` dosyasına değerleri yazıp sunucuyu yeniden başlatın.
4. Test edin: `curl 'http://localhost:8080/api/search?q=pediatric%20surgery&limit=5'`.

Scopus sorgusu artık çalıştırılmaz ve kaynak devre dışıdır. Aktif arama kaynakları PubMed, Google Scholar ve DOAJ'dır.

## Güncelleme planı

Üretim ortamında worker/scheduler ile kayıtlı sorguların her sabah `07:00 Europe/Istanbul` saatinde çalıştırılması ve yeni DOI kayıtlarının deduplikasyonla PostgreSQL'e alınması gerekir. Yeni yayınları daha erken almak için aynı sorgular 15-30 dakikalık aralıklarla da çalıştırılabilir. API anahtarları tamamlandığında `server.py` içindeki kaynak adapter'ları aynı `records` şemasına dönüştürülür.

## Üretim için sonraki adımlar

1. PostgreSQL şeması: `articles`, `sources`, `saved_searches`, `sync_runs`, `notifications`.
2. DOI + PMID + başlık benzerliği ile deduplikasyon.
3. Redis/BullMQ veya Celery worker ile periyodik görevler.
4. E-posta bildirimleri ve kurum içi kimlik doğrulama.
5. Kaynak lisanslarının özet saklama ve yeniden sunma şartlarının doğrulanması.
