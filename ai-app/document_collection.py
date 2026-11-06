"""Controle local exclusivo e persistente. Nenhuma conexão ocorre na importação."""
import fcntl
import json
import os
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from document_policy import (
    Classification, ClassifiedChunk, ClassifiedContext, ClassifiedPackage,
    DocumentIntegrityError, eligible, payload_hash,
)


class ControlError(RuntimeError):
    pass


def atomic_json(path, value):
    # Mesmo filesystem, replace atômico e sincronização do estado antes do Qdrant.
    temp = path.with_suffix(".pending")
    with temp.open("w") as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.flush()
        os.fsync(out.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class DocumentControl:
    def __init__(self, state_dir, collection, endpoint, backend):
        if not collection.startswith("runbook_chunks_v2_"):
            raise ControlError("Somente coleções explicitamente V2")
        self.directory = Path(state_dir).resolve()
        if self.directory == Path('/tmp') or Path('/tmp') in self.directory.parents or Path('/private/tmp') in [self.directory, *self.directory.parents]:
            raise ControlError("Estado não pode ficar em /tmp")
        self.collection, self.endpoint, self.backend = collection, endpoint, backend
        self.handle = None

    def __enter__(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.handle = (self.directory / "executor.lock").open("a+")
        try:
            fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.handle.close()
            self.handle = None
            raise ControlError("Outro executor detém o lock; nenhuma operação permitida") from exc
        return self

    def __exit__(self, *args):
        if self.handle:
            self.handle.close()
            self.handle = None

    @property
    def path(self):
        return self.directory / "state.json"

    def read(self, allow_blocked=False):
        if self.handle is None:
            raise ControlError("Operação exige lock exclusivo")
        try:
            data = json.loads(self.path.read_text())
            if data['collection'] != self.collection or data['endpoint'] != self.endpoint:
                raise ValueError("Binding de coleção/endpoint divergente")
            if data['phase'] not in ('ready', 'blocked'):
                raise ValueError("Estado inválido")
            records = [Classification.model_validate(r) for r in data['records']]
            keys = [(r.document_id, r.document_version) for r in records]
            ids = [i for r in records for i in r.chunk_ids]
            if not records or len(keys) != len(set(keys)) or len(ids) != len(set(ids)):
                raise ValueError("Catálogo vazio ou duplicado")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ControlError("Estado persistente ausente/inválido; uso bloqueado") from exc
        if data['phase'] != 'ready' and not allow_blocked:
            raise ControlError("Classificação incompleta: reconciliação explícita necessária")
        return data, records

    def audit(self, records):
        chunks = self.backend.all()
        expected = {i for r in records for i in r.chunk_ids}
        ids = [c.get('chunk_id') for c in chunks]
        if len(ids) != len(set(ids)) or set(ids) != expected:
            raise DocumentIntegrityError("Chunks faltantes, extras ou duplicados na coleção")
        for chunk in chunks:
            eligible(chunk, records)
        return chunks

    def load(self, chunks, vectors, dimensions):
        if self.handle is None or self.path.exists() or self.backend.exists():
            raise ControlError("Carga exige lock, estado novo e coleção inexistente; não sobrescrever")
        chunks = [ClassifiedChunk.model_validate(c).model_dump() for c in chunks]
        if not chunks or len(chunks) != len(vectors) or dimensions < 1:
            raise ControlError("Carga vazia ou vetores incompatíveis")
        if any(len(v) != dimensions for v in vectors):
            raise ControlError("Dimensão de vetor inconsistente")
        groups = {}
        for c in chunks:
            groups.setdefault((c['document_id'], c['document_version']), []).append(c)
        records = []
        for (doc, version), values in groups.items():
            first = values[0]
            record = Classification(document_id=doc, document_version=version,
                document_status=first['document_status'], classified_by=first['classified_by'],
                classification_revision=first['classification_revision'],
                chunk_ids=[v['chunk_id'] for v in values],
                payload_hashes={v['chunk_id']: payload_hash(v) for v in values})
            for value in values:
                eligible(value, [record])
            records.append(record)
        all_ids = [c['chunk_id'] for c in chunks]
        if len(all_ids) != len(set(all_ids)):
            raise ControlError("IDs duplicados entre versões")
        state = dict(collection=self.collection, endpoint=self.endpoint, phase='blocked',
                     operation='load', records=[r.model_dump() for r in records])
        atomic_json(self.path, state)
        self.backend.create(dimensions)
        self.backend.upsert(chunks, vectors)
        self.audit(records)
        state['phase'] = 'ready'
        atomic_json(self.path, state)

    def reclassify(self, document_id, version, status, classified_by):
        data, records = self.read()
        self.audit(records)
        targets = [r for r in records if (r.document_id, r.document_version) == (document_id, version)]
        if len(targets) != 1:
            raise ControlError("Versão não catalogada")
        target = targets[0]
        new = Classification.model_validate({**target.model_dump(), 'document_status': status,
                'classified_by': classified_by, 'classification_revision': target.classification_revision + 1})
        records = [new if r == target else r for r in records]
        data.update(phase='blocked', operation='reclassify', previous_records=data['records'],
                    records=[r.model_dump() for r in records])
        atomic_json(self.path, data)
        self.reconcile()  # Qualquer exceção mantém blocked em disco.

    def reconcile(self):
        data, records = self.read(allow_blocked=True)
        if data['phase'] != 'blocked' or data['operation'] != 'reclassify':
            raise ControlError("Somente reclassificação interrompida admite reconciliação; carga exige investigação")
        previous = [Classification.model_validate(r) for r in data['previous_records']]
        chunks = self.backend.all()
        ids = [c.get('chunk_id') for c in chunks]
        expected = {i for r in records for i in r.chunk_ids}
        if len(ids) != len(set(ids)) or set(ids) != expected:
            raise DocumentIntegrityError("Reconciliação: inventário diverge, não reparar automaticamente")
        for r in records:
            for c in chunks:
                if c.get('chunk_id') in r.chunk_ids:
                    old = next(x for x in previous if (x.document_id, x.document_version) == (r.document_id, r.document_version))
                    current = (c.get('document_status'), c.get('classification_revision'), c.get('classified_by'))
                    permitted = [(x.document_status, x.classification_revision, x.classified_by) for x in (old, r)]
                    if current not in permitted:
                        raise DocumentIntegrityError('Classificação não pertence à transição registrada')
                    proposed = {**c, 'document_status': r.document_status,
                                'classification_revision': r.classification_revision, 'classified_by': r.classified_by}
                    eligible(proposed, [r])  # Não reparar conteúdo ou versão.
            self.backend.classify(r)
        self.audit(records)
        data['phase'] = 'ready'
        atomic_json(self.path, data)

    def search(self, vector):
        _, records = self.read()
        self.audit(records)
        active = [r for r in records if r.document_status == 'active']
        if not active:
            return []
        results = self.backend.search(vector, active, limit=3, threshold=0.50)
        for item in results:
            if not eligible(item['chunk'], records):
                raise DocumentIntegrityError("Busca devolveu documento inelegível apesar do filtro")
        return results

    def limits(self, document_id, version):
        _, records = self.read()
        chunks = self.audit(records)
        return [c for c in chunks if (c['document_id'], c['document_version'], c['section']) ==
                (document_id, version, 'Limites') and eligible(c, records)]

    def package(self, investigation):
        from llm_input_package import build_llm_input_package
        _, records = self.read()
        self.audit(records)
        if investigation.get('status') in ('manual_escalation_required', 'additional_data_required'):
            return build_llm_input_package(investigation)
        for chunk in ([i['chunk'] for i in investigation['documentation']] + investigation['document_limits']):
            if not eligible(chunk, records):
                raise DocumentIntegrityError("Contexto contém documento inelegível")
        docs = {(i['chunk']['document_id'], i['chunk']['document_version']) for i in investigation['documentation']}
        limits = {(c['document_id'], c['document_version']) for c in investigation['document_limits']}
        if investigation['analysis_code'] == 'CONTEXT_READY' and (not docs or not docs <= limits):
            raise DocumentIntegrityError("Contexto pronto sem Limites da mesma versão")
        # Reutiliza integralmente elegibilidade, política e instruções da V1.
        legacy = build_llm_input_package(investigation)
        if legacy.status != 'ready':
            return legacy
        evidence = ClassifiedContext.model_validate(investigation, strict=True)
        # A validação tipada mantém metadados que os modelos V1 ignoram.
        value = legacy.package.model_dump()
        value['evidence'] = evidence.model_dump()
        return ClassifiedPackage.model_validate(value, strict=True)


class QdrantBackend:
    def __init__(self, url, collection):
        self.url = url
        self.collection = collection
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from qdrant_client import QdrantClient
            self._client = QdrantClient(url=self.url, timeout=30)
        return self._client

    @client.setter
    def client(self, value):
        self._client = value

    def exists(self):
        return self.client.collection_exists(self.collection)

    def create(self, dimensions):
        from qdrant_client import models as m
        self.client.create_collection(self.collection, vectors_config=m.VectorParams(size=dimensions, distance=m.Distance.COSINE))

    def all(self):
        result, offset = [], None
        while True:
            points, offset = self.client.scroll(self.collection, limit=100, offset=offset, with_payload=True, with_vectors=False)
            result.extend(p.payload for p in points)
            if offset is None:
                return result

    def upsert(self, chunks, vectors):
        from qdrant_client import models as m
        points = [m.PointStruct(id=str(uuid5(NAMESPACE_URL, c['chunk_id'])), vector=v, payload=c) for c, v in zip(chunks, vectors)]
        self.client.upsert(self.collection, points=points, wait=True)

    def classify(self, record):
        ids = [str(uuid5(NAMESPACE_URL, i)) for i in record.chunk_ids]
        self.client.set_payload(self.collection, payload=dict(document_status=record.document_status,
            classified_by=record.classified_by, classification_revision=record.classification_revision), points=ids, wait=True)

    def search(self, vector, active, limit, threshold):
        from qdrant_client import models as m
        alternatives = [m.Filter(must=[m.FieldCondition(key=k, match=m.MatchValue(value=v)) for k,v in
            dict(document_id=r.document_id, document_version=r.document_version, document_status='active',
                 classification_revision=r.classification_revision).items()]) for r in active]
        response = self.client.query_points(self.collection, query=vector,
            query_filter=m.Filter(should=alternatives), limit=limit, score_threshold=threshold, with_payload=True)
        return [dict(score=p.score, chunk=p.payload) for p in response.points]
