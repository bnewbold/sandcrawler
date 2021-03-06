
import json
import datetime
from typing import Optional

import psycopg2
import psycopg2.extras
import requests

class SandcrawlerPostgrestClient:

    def __init__(self, api_url="http://aitio.us.archive.org:3030", **kwargs):
        self.api_url = api_url

    def get_cdx(self, url):
        resp = requests.get(self.api_url + "/cdx", params=dict(url='eq.'+url))
        resp.raise_for_status()
        return resp.json() or None

    def get_grobid(self, sha1):
        resp = requests.get(self.api_url + "/grobid", params=dict(sha1hex='eq.'+sha1))
        resp.raise_for_status()
        resp = resp.json()
        if resp:
            return resp[0]
        else:
            return None

    def get_pdftrio(self, sha1):
        resp = requests.get(self.api_url + "/pdftrio", params=dict(sha1hex='eq.'+sha1))
        resp.raise_for_status()
        resp = resp.json()
        if resp:
            return resp[0]
        else:
            return None

    def get_pdf_meta(self, sha1):
        resp = requests.get(self.api_url + "/pdf_meta", params=dict(sha1hex='eq.'+sha1))
        resp.raise_for_status()
        resp = resp.json()
        if resp:
            return resp[0]
        else:
            return None

    def get_html_meta(self, sha1hex: str) -> Optional[dict]:
        resp = requests.get(
            self.api_url + "/html_meta",
            params=dict(sha1hex=f"eq.{sha1hex}"),
        )
        resp.raise_for_status()
        resp_json = resp.json()
        if resp_json:
            return resp_json[0]
        else:
            return None

    def get_file_meta(self, sha1):
        resp = requests.get(self.api_url + "/file_meta", params=dict(sha1hex='eq.'+sha1))
        resp.raise_for_status()
        resp = resp.json()
        if resp:
            return resp[0]
        else:
            return None

    def get_ingest_file_result(self, ingest_type: str, url: str) -> Optional[dict]:
        resp = requests.get(
            self.api_url + "/ingest_file_result",
            params=dict(ingest_type=f"eq.{ingest_type}", base_url=f"eq.{url}"),
        )
        resp.raise_for_status()
        resp_json = resp.json()
        if resp_json:
            return resp_json[0]
        else:
            return None

class SandcrawlerPostgresClient:

    def __init__(self, db_url, **kwargs):
        self.conn = psycopg2.connect(db_url)

    def cursor(self):
        return self.conn.cursor()

    def commit(self):
        return self.conn.commit()

    def _inserts_and_updates(self, resp, on_conflict):
        resp = [int(r[0]) for r in resp]
        inserts = len([r for r in resp if r == 0])
        if on_conflict == "update":
            updates = len([r for r in resp if r != 0])
        else:
            updates = 0
        return (inserts, updates)

    def insert_cdx(self, cur, batch, on_conflict="nothing"):
        sql = """
            INSERT INTO
            cdx (url, datetime, sha1hex, mimetype, warc_path, warc_csize, warc_offset)
            VALUES %s
            ON CONFLICT ON CONSTRAINT cdx_pkey DO
        """
        if on_conflict.lower() == "nothing":
            sql += " NOTHING"
        else:
            raise NotImplementedError("on_conflict: {}".format(on_conflict))
        sql += " RETURNING xmax;"

        batch = [d for d in batch if d.get('warc_path')]
        if not batch:
            return (0, 0)
        batch = [(d['url'],
                  d['datetime'],
                  d['sha1hex'],
                  d['mimetype'],
                  d['warc_path'],
                  int(d['warc_csize']),
                  int(d['warc_offset']))
                 for d in batch]
        # filter out duplicate rows by key (url, datetime)
        batch_dict = dict()
        for b in batch:
            batch_dict[(b[0], b[1])] = b
        batch = list(batch_dict.values())
        resp = psycopg2.extras.execute_values(cur, sql, batch, page_size=250, fetch=True)
        return self._inserts_and_updates(resp, on_conflict)

    def insert_file_meta(self, cur, batch, on_conflict="nothing"):
        sql = """
            INSERT INTO
            file_meta(sha1hex, sha256hex, md5hex, size_bytes, mimetype)
            VALUES %s
            ON CONFLICT (sha1hex) DO
        """
        if on_conflict.lower() == "nothing":
            sql += " NOTHING"
        elif on_conflict.lower() == "update":
            sql += """ UPDATE SET
                sha256hex=EXCLUDED.sha256hex,
                md5hex=EXCLUDED.md5hex,
                size_bytes=EXCLUDED.size_bytes,
                mimetype=EXCLUDED.mimetype
            """
        else:
            raise NotImplementedError("on_conflict: {}".format(on_conflict))
        sql += " RETURNING xmax;"
        batch = [(d['sha1hex'],
                  d['sha256hex'],
                  d['md5hex'],
                  int(d['size_bytes']),
                  d['mimetype'])
                 for d in batch]
        # filter out duplicate rows by key (sha1hex)
        batch_dict = dict()
        for b in batch:
            batch_dict[b[0]] = b
        batch = list(batch_dict.values())
        resp = psycopg2.extras.execute_values(cur, sql, batch, page_size=250, fetch=True)
        return self._inserts_and_updates(resp, on_conflict)

    def insert_grobid(self, cur, batch, on_conflict="nothing"):
        sql = """
            INSERT INTO
            grobid (sha1hex, grobid_version, status_code, status, fatcat_release, updated, metadata)
            VALUES %s
            ON CONFLICT (sha1hex) DO
        """
        if on_conflict.lower() == "nothing":
            sql += " NOTHING"
        elif on_conflict.lower() == "update":
            sql += """ UPDATE SET
                grobid_version=EXCLUDED.grobid_version,
                status_code=EXCLUDED.status_code,
                status=EXCLUDED.status,
                fatcat_release=EXCLUDED.fatcat_release,
                updated=EXCLUDED.updated,
                metadata=EXCLUDED.metadata
            """
        else:
            raise NotImplementedError("on_conflict: {}".format(on_conflict))
        sql += " RETURNING xmax;"
        for r in batch:
            if r.get('metadata'):
                # sometimes these are only in metadata; shouldn't pass through
                # though (to save database space)
                dupe_fields = ('fatcat_release', 'grobid_version')
                for k in dupe_fields:
                    if not k in r:
                        r[k] = r['metadata'].get(k)
                    r['metadata'].pop(k, None)
                r['metadata'] = json.dumps(r['metadata'], sort_keys=True)
        batch = [(d['key'],
                  d.get('grobid_version') or None,
                  d['status_code'],
                  d['status'],
                  d.get('fatcat_release') or None,
                  d.get('updated') or datetime.datetime.now(),
                  d.get('metadata') or None ,
                 )
                 for d in batch]
        # filter out duplicate rows by key (sha1hex)
        batch_dict = dict()
        for b in batch:
            batch_dict[b[0]] = b
        batch = list(batch_dict.values())
        resp = psycopg2.extras.execute_values(cur, sql, batch, page_size=250, fetch=True)
        return self._inserts_and_updates(resp, on_conflict)

    def insert_pdf_meta(self, cur, batch, on_conflict="nothing"):
        """
        batch elements are expected to have .to_sql_tuple() method
        """
        sql = """
            INSERT INTO
            pdf_meta (sha1hex, updated, status, has_page0_thumbnail, page_count, word_count, page0_height, page0_width, permanent_id, pdf_created, pdf_version, metadata)
            VALUES %s
            ON CONFLICT (sha1hex) DO
        """
        if on_conflict.lower() == "nothing":
            sql += " NOTHING"
        elif on_conflict.lower() == "update":
            sql += """ UPDATE SET
                updated=EXCLUDED.updated,
                status=EXCLUDED.status,
                has_page0_thumbnail=EXCLUDED.has_page0_thumbnail,
                page_count=EXCLUDED.page_count,
                word_count=EXCLUDED.word_count,
                page0_height=EXCLUDED.page0_height,
                page0_width=EXCLUDED.page0_width,
                permanent_id=EXCLUDED.permanent_id,
                pdf_created=EXCLUDED.pdf_created,
                pdf_version=EXCLUDED.pdf_version,
                metadata=EXCLUDED.metadata
            """
        else:
            raise NotImplementedError("on_conflict: {}".format(on_conflict))
        sql += " RETURNING xmax;"
        batch = [d.to_sql_tuple() for d in batch]
        # filter out duplicate rows by key (sha1hex)
        batch_dict = dict()
        for b in batch:
            batch_dict[b[0]] = b
        batch = list(batch_dict.values())
        resp = psycopg2.extras.execute_values(cur, sql, batch, page_size=250, fetch=True)
        return self._inserts_and_updates(resp, on_conflict)

    def insert_html_meta(self, cur, batch, on_conflict="nothing"):
        """
        batch elements are expected to have .to_sql_tuple() method
        """
        sql = """
            INSERT INTO
            html_meta (sha1hex, updated, status, scope, has_teixml, has_thumbnail, word_count, biblio, resources)
            VALUES %s
            ON CONFLICT (sha1hex) DO
        """
        if on_conflict.lower() == "nothing":
            sql += " NOTHING"
        elif on_conflict.lower() == "update":
            sql += """ UPDATE SET
                updated=EXCLUDED.updated,
                status=EXCLUDED.status,
                scope=EXCLUDED.scope,
                has_teixml=EXCLUDED.has_teixml,
                has_thumbnail=EXCLUDED.has_thumbnail,
                word_count=EXCLUDED.word_count,
                biblio=EXCLUDED.biblio,
                resources=EXCLUDED.resources
            """
        else:
            raise NotImplementedError("on_conflict: {}".format(on_conflict))
        sql += " RETURNING xmax;"
        batch = [d.to_sql_tuple() for d in batch]
        # filter out duplicate rows by key (sha1hex)
        batch_dict = dict()
        for b in batch:
            batch_dict[b[0]] = b
        batch = list(batch_dict.values())
        resp = psycopg2.extras.execute_values(cur, sql, batch, page_size=250, fetch=True)
        return self._inserts_and_updates(resp, on_conflict)

    def insert_pdftrio(self, cur, batch, on_conflict="nothing"):
        sql = """
            INSERT INTO
            pdftrio (sha1hex, updated, status_code, status, pdftrio_version,
                     models_date, ensemble_score, bert_score, linear_score,
                     image_score)
            VALUES %s
            ON CONFLICT (sha1hex) DO
        """
        if on_conflict.lower() == "nothing":
            sql += " NOTHING"
        elif on_conflict.lower() == "update":
            sql += """ UPDATE SET
                updated=EXCLUDED.updated,
                status_code=EXCLUDED.status_code,
                status=EXCLUDED.status,
                pdftrio_version=EXCLUDED.pdftrio_version,
                models_date=EXCLUDED.models_date,
                ensemble_score=EXCLUDED.ensemble_score,
                bert_score=EXCLUDED.bert_score,
                linear_score=EXCLUDED.linear_score,
                image_score=EXCLUDED.image_score
            """
        else:
            raise NotImplementedError("on_conflict: {}".format(on_conflict))
        sql += " RETURNING xmax;"
        batch = [
            (
                d['key'],
                d.get('updated') or datetime.datetime.now(),
                d['status_code'],
                d['status'],
                d.get('versions', {}).get('pdftrio_version') or None,
                d.get('versions', {}).get('models_date') or None,
                d.get('ensemble_score'),
                d.get('bert_score'),
                d.get('linear_score'),
                d.get('image_score'),
            )
            for d in batch]
        # filter out duplicate rows by key (sha1hex)
        batch_dict = dict()
        for b in batch:
            batch_dict[b[0]] = b
        batch = list(batch_dict.values())
        resp = psycopg2.extras.execute_values(cur, sql, batch, page_size=250, fetch=True)
        return self._inserts_and_updates(resp, on_conflict)

    def insert_ingest_request(self, cur, batch, on_conflict="nothing"):
        sql = """
            INSERT INTO
            ingest_request (link_source, link_source_id, ingest_type, base_url, ingest_request_source, release_stage, request)
            VALUES %s
            ON CONFLICT ON CONSTRAINT ingest_request_pkey DO
        """
        if on_conflict.lower() == "nothing":
            sql += " NOTHING"
        else:
            raise NotImplementedError("on_conflict: {}".format(on_conflict))
        sql += " RETURNING xmax;"
        for r in batch:
            # in case these fields were already packed into 'request'
            extra = r.get('request', {})
            for k in ('ext_ids', 'fatcat_release', 'edit_extra', 'rel'):
                if r.get(k):
                    extra[k] = r[k]
            if extra:
                r['extra'] = json.dumps(extra, sort_keys=True)
        batch = [(d['link_source'],
                  d['link_source_id'],
                  d['ingest_type'],
                  d['base_url'],
                  d.get('ingest_request_source'),
                  d.get('release_stage') or None,
                  d.get('extra') or None,
                 )
                 for d in batch]
        # filter out duplicate rows by key (link_source, link_source_id, ingest_type, base_url)
        batch_dict = dict()
        for b in batch:
            batch_dict[(b[0], b[1], b[2], b[3])] = b
        batch = list(batch_dict.values())
        resp = psycopg2.extras.execute_values(cur, sql, batch, page_size=250, fetch=True)
        return self._inserts_and_updates(resp, on_conflict)

    def insert_ingest_file_result(self, cur, batch, on_conflict="nothing"):
        sql = """
            INSERT INTO
            ingest_file_result (ingest_type, base_url, hit, status, terminal_url, terminal_dt, terminal_status_code, terminal_sha1hex)
            VALUES %s
            ON CONFLICT ON CONSTRAINT ingest_file_result_pkey DO 
        """
        if on_conflict.lower() == "nothing":
            sql += " NOTHING"
        elif on_conflict.lower() == "update":
            sql += """ UPDATE SET
                updated=now(),
                hit=EXCLUDED.hit,
                status=EXCLUDED.status,
                terminal_url=EXCLUDED.terminal_url,
                terminal_dt=EXCLUDED.terminal_dt,
                terminal_status_code=EXCLUDED.terminal_status_code,
                terminal_sha1hex=EXCLUDED.terminal_sha1hex
            """
        else:
            raise NotImplementedError("on_conflict: {}".format(on_conflict))
        sql += " RETURNING xmax;"
        batch = [(d['ingest_type'],
                  d['base_url'],
                  bool(d['hit']),
                  d['status'],
                  d.get('terminal_url'),
                  d.get('terminal_dt'),
                  d.get('terminal_status_code'),
                  d.get('terminal_sha1hex'),
                 )
                 for d in batch]
        # filter out duplicate rows by key (ingest_type, base_url)
        batch_dict = dict()
        for b in batch:
            batch_dict[(b[0], b[1])] = b
        batch = list(batch_dict.values())
        resp = psycopg2.extras.execute_values(cur, sql, batch, page_size=250, fetch=True)
        return self._inserts_and_updates(resp, on_conflict)
