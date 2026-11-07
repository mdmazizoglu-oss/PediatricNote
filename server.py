#!/usr/bin/env python3
import json
import os
import re
import ssl
import urllib.parse
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent

def load_env_file():
    env_file = ROOT / '.env'
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

load_env_file()
PORT = int(os.getenv('PORT', '8080'))
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

SOURCES = {
    'PubMed': {'env': 'NCBI_API_KEY', 'kind': 'live', 'url': 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'},
    'Scopus': {'env': 'SCOPUS_API_KEY', 'kind': 'disabled', 'enabled': False},
    'Web of Science': {'env': 'WOS_API_KEY', 'kind': 'disabled', 'enabled': False},
    'Embase': {'env': 'EMBASE_API_KEY', 'kind': 'disabled', 'enabled': False},
    'Google Scholar': {'env': 'SERPAPI_KEY', 'kind': 'provider'},
    'DOAJ': {'env': '', 'kind': 'live'},
}

# Curated pediatric-surgery subject vocabulary; it is intentionally maintained as
# concepts rather than copied book text so the search policy is transparent.
PEDIATRIC_SURGERY_TOPICS = (
    # General, neonatal and congenital surgery
    'pediatric surgery', 'paediatric surgery', 'neonatal surgery', 'fetal surgery',
    'congenital anomaly', 'congenital malformation', 'congenital disorder',
    'birth defect', 'prematurity', 'low birth weight', 'neonatal intensive care',
    'neonatal abdomen', 'neonatal sepsis', 'necrotizing enterocolitis',
    'intestinal perforation', 'spontaneous intestinal perforation',
    'umbilical anomaly', 'omphalitis', 'umbilical granuloma', 'umbilical hernia',
    'omphalocele', 'gastroschisis', 'body wall defect', 'amniotic band syndrome',
    'conjoined twins', 'twin pregnancy', 'thoracoabdominal duplication',

    # Esophagus, stomach, bowel and colorectal disease
    'esophageal atresia', 'oesophageal atresia', 'tracheoesophageal fistula',
    'gastroesophageal reflux', 'gastroesophageal reflux disease', 'esophageal stricture',
    'esophageal perforation', 'caustic ingestion', 'foreign body ingestion',
    'pyloric stenosis', 'hypertrophic pyloric stenosis', 'gastric volvulus',
    'gastric duplication', 'intestinal atresia', 'duodenal atresia',
    'jejunoileal atresia', 'meconium ileus', 'meconium plug', 'small bowel obstruction',
    'bowel obstruction', 'intestinal obstruction', 'malrotation', 'midgut volvulus',
    'intestinal duplication', 'enteric duplication', 'mesenteric cyst',
    'short bowel syndrome', 'intestinal failure', 'necrotizing enterocolitis surgery',
    'inflammatory bowel disease', 'crohn disease', 'ulcerative colitis',
    'appendicitis', 'appendiceal abscess', 'appendicitis perforation',
    'intussusception', 'pediatric constipation', 'fecal incontinence',
    'colonic inertia', 'colonic stricture', 'colorectal disease', 'colorectal surgery',
    'hirschsprung disease', 'hirschsprung', 'aganglionic megacolon',
    'anorectal malformation', 'imperforate anus', 'cloacal malformation',
    'cloaca', 'rectal prolapse', 'anal stenosis', 'anal fistula',

    # Liver, biliary, pancreas and spleen
    'biliary atresia', 'choledochal cyst', 'choledochal malformation',
    'biliary cyst', 'neonatal cholestasis', 'pediatric cholestasis',
    'pediatric liver disease', 'pediatric liver tumor', 'hepatoblastoma',
    'hepatocellular carcinoma child', 'liver transplantation', 'pediatric transplant',
    'portal hypertension', 'portal vein thrombosis', 'splenic injury',
    'splenectomy child', 'pediatric pancreatitis', 'pancreatic trauma child',
    'pancreatic pseudocyst', 'annular pancreas', 'pancreatic tumor child',

    # Thoracic, airway and chest wall surgery
    'pediatric thoracic surgery', 'paediatric thoracic surgery', 'pediatric airway',
    'tracheal stenosis', 'tracheomalacia', 'bronchomalacia', 'laryngotracheal stenosis',
    'vascular ring', 'double aortic arch', 'pulmonary sequestration',
    'congenital pulmonary airway malformation', 'cpam', 'cystic adenomatoid malformation',
    'congenital lobar emphysema', 'bronchogenic cyst', 'foregut duplication cyst',
    'esophageal lung', 'pediatric empyema', 'pediatric pneumothorax',
    'chylothorax', 'pectus excavatum', 'pectus carinatum', 'chest wall deformity',
    'funnel chest', 'rib deformity', 'thoracic outlet child', 'diaphragmatic hernia',
    'congenital diaphragmatic hernia', 'cdh', 'eventration of diaphragm',
    'hiatal hernia child', 'mediastinal mass child', 'thoracoscopy child',

    # Urology, genital and pelvic surgery
    'pediatric urology', 'paediatric urology', 'hypospadias', 'epispadias',
    'bladder exstrophy', 'cloacal exstrophy', 'posterior urethral valve',
    'urethral valve', 'vesicoureteral reflux', 'vesicoureteric reflux',
    'reflux nephropathy', 'hydronephrosis', 'ureteropelvic junction obstruction',
    'upj obstruction', 'ureterovesical junction obstruction', 'megaureter',
    'neurogenic bladder', 'bladder dysfunction', 'urinary tract anomaly',
    'duplicated collecting system', 'horseshoe kidney', 'renal ectopia',
    'undescended testis', 'cryptorchidism', 'orchidopexy', 'testicular torsion',
    'torsion of testis', 'hydrocele', 'varicocele child', 'inguinal hernia child',
    'inguinal hernia pediatric', 'labial adhesions', 'disorders of sex development',
    'ambiguous genitalia', 'micropenis', 'vaginal obstruction', 'urogenital sinus',
    'pediatric renal tumor', 'wilms tumor', 'nephroblastoma', 'bladder tumor child',

    # Oncology, tumors and vascular anomalies
    'pediatric oncology surgery', 'paediatric oncology surgery', 'childhood cancer surgery',
    'neuroblastoma', 'wilms tumor', 'hepatoblastoma', 'rhabdomyosarcoma child',
    'soft tissue sarcoma child', 'osteosarcoma child', 'ewing sarcoma child',
    'germ cell tumor child', 'teratoma child', 'sacrococcygeal teratoma',
    'lymphatic malformation', 'cystic hygroma', 'venous malformation',
    'vascular malformation', 'hemangioma child', 'kaposiform hemangioendothelioma',
    'neurofibromatosis surgery child', 'retroperitoneal tumor child',

    # Trauma, burns, wounds and critical care
    'pediatric trauma', 'paediatric trauma', 'child trauma', 'blunt abdominal trauma',
    'penetrating trauma child', 'pediatric head trauma', 'pediatric thoracic trauma',
    'pediatric abdominal trauma', 'solid organ injury child', 'liver injury child',
    'splenic injury child', 'renal trauma child', 'pelvic trauma child',
    'pediatric burns', 'paediatric burns', 'burn injury child', 'scald injury',
    'pediatric wound', 'pressure injury child', 'wound healing child',
    'foreign body child', 'nonaccidental trauma', 'child abuse injury',

    # Abdominal wall, endocrine and endocrine-related surgery
    'pediatric hernia', 'ventral hernia child', 'incisional hernia child',
    'abdominal wall defect', 'rectus diastasis child', 'pediatric endocrine surgery',
    'thyroid nodule child', 'thyroid cancer child', 'parathyroid child',
    'adrenal tumor child', 'pheochromocytoma child', 'neuroendocrine tumor child',

    # Techniques, outcomes and perioperative pediatric care
    'pediatric laparoscopy', 'paediatric laparoscopy', 'pediatric thoracoscopy',
    'robotic pediatric surgery', 'minimally invasive pediatric surgery',
    'single incision pediatric surgery', 'endoscopic pediatric surgery',
    'image guided pediatric surgery', 'enhanced recovery pediatric surgery',
    'pediatric surgical site infection', 'pediatric postoperative complication',
    'pediatric perioperative care', 'pediatric anesthesia surgery',
    'pediatric pain surgery', 'pediatric nutrition surgery', 'pediatric ostomy',
    'pediatric quality of life surgery', 'pediatric surgical outcomes',
    'pediatric clinical pathway', 'pediatric surgical education',
)
PEDIATRIC_AGE_TERMS = ('pediatric', 'paediatric', 'child', 'children', 'infant', 'neonate', 'adolescent', 'newborn', 'teenager')
ADULT_ONLY_TERMS = ('adult-only', 'adult only', 'adult population', 'adults only', 'geriatric')

def quoted_or_terms(terms):
    return '(' + ' OR '.join(f'"{term}"' for term in terms) + ')'

def pediatric_query(term):
    return f'({term}) AND {quoted_or_terms(PEDIATRIC_SURGERY_TOPICS)} AND {quoted_or_terms(PEDIATRIC_AGE_TERMS)} NOT {quoted_or_terms(ADULT_ONLY_TERMS)}'

def pediatric_record(record):
    text = f"{record.get('title', '')} {record.get('abstract', '')}".lower()
    has_age_signal = any(re.search(rf'\b{re.escape(term)}\w*\b', text) for term in PEDIATRIC_AGE_TERMS)
    has_adult_only_signal = any(term in text for term in ADULT_ONLY_TERMS)
    return has_age_signal and not has_adult_only_signal

def xml_value(block, tag):
    match = re.search(rf'<{tag}>(.*?)</{tag}>', block, re.S)
    return re.sub(r'<.*?>', '', match.group(1)).strip() if match else ''

def pubmed_search(term, limit=20):
    params = urllib.parse.urlencode({'db': 'pubmed', 'term': term, 'retmax': limit, 'retmode': 'json', 'sort': 'date'})
    with urllib.request.urlopen(f"{SOURCES['PubMed']['url']}?{params}", timeout=12, context=SSL_CONTEXT) as response:
        payload = json.loads(response.read().decode())
    ids = payload.get('esearchresult', {}).get('idlist', [])
    if not ids:
        return []
    fetch_params = urllib.parse.urlencode({'db': 'pubmed', 'id': ','.join(ids), 'retmode': 'xml'})
    with urllib.request.urlopen(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?{fetch_params}", timeout=12, context=SSL_CONTEXT) as response:
        xml = response.read().decode(errors='replace')
    records = []
    for block in re.findall(r'<PubmedArticle>(.*?)</PubmedArticle>', xml, re.S):
        title = xml_value(block, 'ArticleTitle')
        abstract = ' '.join(re.findall(r'<AbstractText[^>]*>(.*?)</AbstractText>', block, re.S))
        authors = ', '.join(re.findall(r'<LastName>(.*?)</LastName>', block, re.S)[:4])
        doi_match = re.search(r'<ArticleId IdType="doi">(.*?)</ArticleId>', block)
        date = xml_value(block, 'Year') or 'Tarih yok'
        records.append({'source': 'PubMed', 'title': title, 'abstract': re.sub(r'<.*?>', '', abstract), 'authors': authors, 'date': date, 'doi': doi_match.group(1) if doi_match else ''})
    return records

def scopus_search(term, limit=20):
    api_key = os.getenv('SCOPUS_API_KEY')
    if not api_key:
        return []
    query = f'TITLE-ABS-KEY({pediatric_query(term)})'
    params = urllib.parse.urlencode({'query': query, 'count': min(limit, 25), 'sort': '-coverDate'})
    request = urllib.request.Request(f"{SOURCES['Scopus']['url']}?{params}", headers={
        'Accept': 'application/json',
        'X-ELS-APIKey': api_key,
    })
    institution_token = os.getenv('SCOPUS_INST_TOKEN')
    if institution_token:
        request.add_header('X-ELS-Insttoken', institution_token)
    with urllib.request.urlopen(request, timeout=20, context=SSL_CONTEXT) as response:
        payload = json.loads(response.read().decode())
    entries = payload.get('search-results', {}).get('entry', [])
    records = []
    for item in entries:
        authors = item.get('dc:creator', '')
        records.append({
            'source': 'Scopus',
            'title': item.get('dc:title', ''),
            'abstract': item.get('dc:description', ''),
            'authors': authors,
            'date': item.get('prism:coverDate', 'Tarih yok'),
            'doi': item.get('prism:doi', ''),
            'url': item.get('prism:url', ''),
        })
    return records

def google_scholar_search(term, limit=20):
    api_key = os.getenv('SERPAPI_KEY')
    if not api_key:
        return []
    params = urllib.parse.urlencode({
        'engine': 'google_scholar',
        'q': pediatric_query(term),
        'num': min(limit, 20),
        'api_key': api_key,
    })
    with urllib.request.urlopen(f'https://serpapi.com/search.json?{params}', timeout=20, context=SSL_CONTEXT) as response:
        payload = json.loads(response.read().decode())
    records = []
    for item in payload.get('organic_results', []):
        publication = item.get('publication_info', {})
        records.append({
            'source': 'Google Scholar',
            'title': item.get('title', ''),
            'abstract': item.get('snippet', ''),
            'authors': publication.get('summary', ''),
            'date': publication.get('summary', '').split('-')[-1].strip() if publication.get('summary') else 'Tarih yok',
            'doi': item.get('result_id', ''),
            'url': item.get('link', ''),
        })
    return records

def doaj_search(term, limit=20):
    # DOAJ has a shorter query parser than PubMed/Scopus; enforce the full
    # pediatric topic and age policy again with pediatric_record below.
    doaj_term = f'{term} pediatric surgery'
    endpoint = f"https://doaj.org/api/search/articles/{urllib.parse.quote(doaj_term)}"
    params = urllib.parse.urlencode({'pageSize': min(limit, 100), 'page': 1})
    request = urllib.request.Request(f'{endpoint}?{params}', headers={'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=20, context=SSL_CONTEXT) as response:
        payload = json.loads(response.read().decode())
    records = []
    for item in payload.get('results', []):
        bibjson = item.get('bibjson', {})
        authors = ', '.join(author.get('name', '') for author in bibjson.get('author', []))
        identifiers = bibjson.get('identifier', [])
        doi = next((entry.get('id', '') for entry in identifiers if entry.get('type') == 'doi'), '')
        links = bibjson.get('link', [])
        records.append({
            'source': 'DOAJ',
            'title': bibjson.get('title', ''),
            'abstract': bibjson.get('abstract', ''),
            'authors': authors,
            'date': bibjson.get('year', 'Tarih yok'),
            'doi': doi,
            'url': links[0].get('url', '') if links else '',
        })
    return records

def source_status():
    statuses = {}
    for name, data in SOURCES.items():
        if data.get('enabled') is False:
            statuses[name] = 'disabled'
        elif data['kind'] == 'live':
            statuses[name] = 'connected' if data.get('env') and os.getenv(data['env']) else 'available'
        else:
            statuses[name] = 'connected' if os.getenv(data['env']) else 'credentials_required'
    return statuses

class Handler(BaseHTTPRequestHandler):
    def _send(self, payload, status=200, content_type='application/json'):
        body = json.dumps(payload, ensure_ascii=False).encode() if content_type == 'application/json' else payload
        self.send_response(status); self.send_header('Content-Type', f'{content_type}; charset=utf-8'); self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path, _, raw_query = self.path.partition('?')
        if path == '/api/status':
            self._send({'sources': source_status(), 'last_sync': datetime.now().isoformat(timespec='minutes'), 'schedule': '07:00 Europe/Istanbul'}); return
        if path == '/api/search':
            params = urllib.parse.parse_qs(raw_query); term = params.get('q', [''])[0].strip()
            if not term: self._send({'error': 'q parametresi gerekli'}, 400); return
            limit = min(int(params.get('limit', ['20'])[0]), 50)
            records = []
            errors = {}
            try: records.extend(pubmed_search(term, limit))
            except Exception as error: errors['PubMed'] = str(error)
            if os.getenv('SERPAPI_KEY'):
                try: records.extend(google_scholar_search(term, limit))
                except Exception as error: errors['Google Scholar'] = str(error)
            try: records.extend(doaj_search(term, limit))
            except Exception as error: errors['DOAJ'] = str(error)
            records = [record for record in records if pediatric_record(record)]
            self._send({'records': records, 'source_status': source_status(), 'errors': errors, 'filters': {'population': '<18', 'scope': 'pediatric surgery', 'adult_only_excluded': True}, 'note': 'Active sources: PubMed, Google Scholar and DOAJ. Scopus, Web of Science and Embase are disabled.'}); return
        if path == '/':
            self._send((ROOT / 'index.html').read_bytes(), content_type='text/html'); return
        file = ROOT / path.lstrip('/')
        if file.exists() and file.is_file() and file.parent == ROOT:
            content_type = 'text/css' if file.suffix == '.css' else 'application/javascript'
            self._send(file.read_bytes(), content_type=content_type); return
        self._send({'error': 'Not found'}, 404)
    def log_message(self, format, *args):
        print(f'[{self.log_date_time_string()}] {format % args}')

if __name__ == '__main__':
    print(f'Atlas literature radar: http://localhost:{PORT}')
    print('PubMed API: ready | Scopus/WoS/Embase/Scholar: credentials required')
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
